"""Exercise long-horizon retention through actual Mousa stdio MCP processes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time


class Client:
    def __init__(self, binary, store, receipts, writable, timeout):
        self.errors = tempfile.TemporaryFile()
        self.argv = [str(binary), "-store", str(store), "mcp", "--caller", "cli", "--source", "memory"]
        if writable:
            self.argv += ["--ingest-source", "memory"]
        self.process = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors, bufsize=0)
        self.receipts = receipts
        self.timeout = timeout
        self.pending = b""
        self.identifier = 0

    def request(self, method, params, notification=False):
        self.identifier += 1
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            message["id"] = self.identifier
        started = time.monotonic()
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        if notification:
            return None
        deadline = started + self.timeout
        while True:
            while b"\n" not in self.pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                    raise TimeoutError(f"MCP timeout: {method}")
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("MCP server closed stdout")
                self.pending += chunk
            line, self.pending = self.pending.split(b"\n", 1)
            response = json.loads(line)
            if response.get("id") != self.identifier:
                continue
            elapsed = time.monotonic() - started
            self.receipts.write(json.dumps({"request": message, "response": response, "seconds": elapsed}) + "\n")
            self.receipts.flush()
            if "error" in response:
                raise RuntimeError(response["error"])
            return response["result"], elapsed

    def initialize(self):
        _, elapsed = self.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "long_horizon_benchmark", "version": "1"}})
        self.request("notifications/initialized", {}, notification=True)
        return elapsed

    def call(self, name, arguments):
        envelope, elapsed = self.request("tools/call", {"name": name, "arguments": arguments})
        if envelope.get("isError"):
            raise RuntimeError(envelope)
        return envelope["structuredContent"]["result"], elapsed

    def query(self, text):
        return self.call("mousa_query", {"source": "memory", "query": text, "policy": "original", "budget_bytes": 4096})

    def close(self):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                code = self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                code = self.process.wait()
        self.process.stdout.close()
        self.errors.seek(0)
        errors = self.errors.read().decode()
        self.errors.close()
        return {"exit_code": code, "stderr": errors}


def grade(expected, result):
    evidence = result.get("evidence") or []
    reasons = []
    if {row["item"] for row in evidence} != {row["item"] for row in expected} or len(evidence) != len(expected):
        reasons.append("wrong_selected_items")
    for label in expected:
        matches = [row for row in evidence if row["item"] == label["item"]]
        if len(matches) != 1 or any(matches[0].get(key) != value for key, value in label.items()):
            reasons.append("wrong_provenance")
    for row in evidence:
        data = row["text"].encode()
        if hashlib.sha256(data).hexdigest() != row["content_sha256"] or len(data) != row["byte_end"] - row["byte_start"]:
            reasons.append("corrupt_released_bytes")
    return sorted(set(reasons))


def run(binary, dataset, store, output, timeout):
    if any(Path(str(store) + suffix).exists() for suffix in ("", "-wal", "-shm")):
        raise ValueError("refusing to overwrite an existing store")
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    store.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((dataset / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        data = (dataset / name).read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("changed input: " + name)
    plan = json.loads((dataset / "tasks.json").read_text())
    report = {"schema": plan["schema"], "documents": plan["documents"], "epochs": plan["epochs"], "dataset_manifest_sha256": hashlib.sha256((dataset / "manifest.json").read_bytes()).hexdigest(), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "epoch_observations": [], "queries": [], "processes": [], "status": "INCOMPLETE"}
    def save():
        (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    with (output / "mcp-receipts.jsonl").open("x") as receipts:
        writer = Client(binary, store, receipts, True, timeout)
        snapshot = None
        try:
            report["writer_startup_seconds"] = writer.initialize()
            with (dataset / "events.jsonl").open() as events:
                for line in events:
                    event = json.loads(line)
                    started = time.monotonic()
                    for offset in range(0, len(event["items"]), 128):
                        writer.call("mousa_sync", {"source": "memory", "items": event["items"][offset:offset + 128]})
                    state, _ = writer.call("mousa_status", {"source": "memory"})
                    expected_active = ((event["epoch"] + 1) * plan["documents"] + plan["epochs"] - 1) // plan["epochs"] - (event["epoch"] == plan["epochs"] - 1)
                    if state["active_items"] != expected_active or state["needs_recovery"]:
                        raise RuntimeError("incorrect epoch source state")
                    report["epoch_observations"].append({"epoch": event["epoch"], "ingest_events": len(event["items"]), "seconds": time.monotonic() - started})
                    if snapshot is None and event["epoch"] >= 9 * plan["epochs"] // plan["documents"]:
                        snapshot, elapsed = writer.query(plan["initial_snapshot"]["query"])
                        reasons = grade(plan["initial_snapshot"]["expected"], snapshot)
                        report["initial_snapshot"] = {"seconds": elapsed, "reasons": reasons, "packet_id": snapshot["packet_id"], "trail_id": snapshot["trail_id"]}
                        if reasons:
                            raise RuntimeError("initial snapshot failed")
                    save()
            for case in plan["cases"]:
                result, elapsed = writer.query(case["query"])
                report["queries"].append({"case": case["id"], "mode": "warm", "seconds": elapsed, "reasons": grade(case["expected"], result), "introduced_epoch": case["introduced_epoch"], "intervening_documents": case.get("intervening_documents")})
                save()
        finally:
            report["processes"].append(writer.close())
            save()
        reader = Client(binary, store, receipts, False, timeout)
        try:
            report["restart_startup_seconds"] = reader.initialize()
            status, _ = reader.call("mousa_status", {"source": "memory"})
            report["final_active_items"] = status["active_items"]
            if status["active_items"] != plan["active_items"] or status["needs_recovery"]:
                raise RuntimeError("incorrect final source state")
            for case in plan["cases"]:
                result, elapsed = reader.query(case["query"])
                report["queries"].append({"case": case["id"], "mode": "restarted", "seconds": elapsed, "reasons": grade(case["expected"], result), "introduced_epoch": case["introduced_epoch"], "intervening_documents": case.get("intervening_documents")})
                save()
            trail, elapsed = reader.call("mousa_trail", {"source": "memory", "trail_id": snapshot["trail_id"]})
            selected = [(row["segment_id"], row["content_sha256"], row["text_bytes"]) for row in trail["historical"]["candidates"] if row["selected"]]
            original = [(row["segment_id"], row["content_sha256"], len(row["text"].encode())) for row in snapshot["evidence"]]
            report["historical_snapshot"] = {"seconds": elapsed, "packet_matches": trail["historical"]["packet_id"] == snapshot["packet_id"], "selection_matches": selected == original}
        finally:
            report["processes"].append(reader.close())
            report["store_bytes"] = store.stat().st_size
            save()
    failures = [row for row in report["queries"] if row["reasons"]]
    report["passed_queries"] = len(report["queries"]) - len(failures)
    report["failed_queries"] = len(failures)
    report["status"] = "FAIL" if failures or any(row["exit_code"] != 0 for row in report["processes"]) or not all(report["historical_snapshot"][key] for key in ("packet_matches", "selection_matches")) else "PASS"
    save()
    print(json.dumps(report), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    result = run(args.mousa.resolve(), args.dataset.resolve(), args.store.resolve(), args.out.resolve(), args.timeout)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
