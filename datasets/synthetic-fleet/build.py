"""Build a fresh Mousa database and check synthetic evidence through real MCP."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time


def build(mousa, dataset, store, report, verify_only=False, rpc_timeout=300):
    manifest = json.loads((dataset / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        data = (dataset / name).read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("dataset input changed: " + name)
    if verify_only:
        if not store.is_file():
            raise ValueError("verification requires an existing database")
    elif any(Path(str(store) + suffix).exists() for suffix in ("", "-wal", "-shm")):
        raise ValueError("refusing to overwrite an existing database")
    os.umask(0o077)
    store.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    inputs = () if verify_only else (("fleet", "fleet.jsonl"), ("sealed", "sealed.jsonl"), ("fleet", "withdrawals.jsonl"))
    for source, name in inputs:
        argv = [str(mousa), "-store", str(store), "sync", "--source", source]
        started = time.monotonic()
        with (dataset / name).open("rb") as data:
            result = subprocess.run(argv, stdin=data, capture_output=True, timeout=600)
        commands.append({"argv": argv, "input": name, "exit_code": result.returncode, "wall_seconds": time.monotonic() - started, "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
        if result.returncode:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"commands": commands}, indent=2) + "\n")
            raise RuntimeError("database ingestion failed; see report")
    transcript = []
    with tempfile.TemporaryFile() as errors:
        argv = [str(mousa), "-store", str(store), "mcp", "--caller", "cli", "--source", "fleet"]
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, bufsize=0)
        pending = b""
        def request(identifier, method, params):
            nonlocal pending
            message = {"jsonrpc": "2.0", "method": method, "params": params}
            if identifier is not None:
                message["id"] = identifier
            process.stdin.write((json.dumps(message) + "\n").encode())
            if identifier is None:
                return None
            deadline = time.monotonic() + rpc_timeout
            while True:
                while b"\n" not in pending:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                        raise TimeoutError("MCP response timed out")
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise RuntimeError("MCP server closed stdout")
                    pending += chunk
                line, pending = pending.split(b"\n", 1)
                response = json.loads(line)
                if response.get("id") == identifier:
                    transcript.append({"request": message, "response": response})
                    return response
        def call(identifier, name, arguments):
            response = request(identifier, "tools/call", {"name": name, "arguments": arguments})
            if "error" in response:
                raise RuntimeError(response["error"])
            return response["result"]
        try:
            initialized = request(1, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "synthetic_fleet_build", "version": "1"}})
            assert "error" not in initialized, initialized
            request(None, "notifications/initialized", {})
            status = call(2, "mousa_status", {"source": "fleet"})["structuredContent"]["result"]
            assert status["active_items"] == manifest["active_fleet_items"] and not status["needs_recovery"], status
            query = call(3, "mousa_query", {"source": "fleet", "query": "SERVICE00000000", "policy": "original", "budget_bytes": 65536})["structuredContent"]["result"]
            expected_rows = {row["id"]: row["text"] for row in map(json.loads, (dataset / "fleet.jsonl").read_text().splitlines())}
            selected = query["evidence"]
            expected_ids = {"service-00000000-prod", "service-00000000-staging", "service-00000000-owner", "injection-note"}
            assert {row["item"] for row in selected} == expected_ids, query
            for evidence in selected:
                text = expected_rows[evidence["item"]].encode()
                assert evidence["text"].encode() == text
                assert evidence["content_sha256"] == hashlib.sha256(text).hexdigest()
                assert (evidence["byte_start"], evidence["byte_end"]) == (0, len(text))
            trail = call(4, "mousa_trail", {"source": "fleet", "trail_id": query["trail_id"]})["structuredContent"]["result"]
            assert trail["historical"]["packet_id"] == query["packet_id"]
            assert {(row["segment_id"], row["content_sha256"]) for row in trail["historical"]["candidates"] if row["selected"]} == {(row["segment_id"], row["content_sha256"]) for row in selected}
            absent = call(5, "mousa_query", {"source": "fleet", "query": "UNREGISTEREDZZSERVICE", "policy": "original", "budget_bytes": 65536})["structuredContent"]["result"]
            assert not absent["evidence"], absent
            sealed = call(6, "mousa_query", {"source": "fleet", "query": "SYNTHETIC_SEALED", "policy": "original", "budget_bytes": 65536})["structuredContent"]["result"]
            assert not sealed["evidence"], sealed
            sealed_source = request(9, "tools/call", {"name": "mousa_query", "arguments": {"source": "sealed", "query": "SYNTHETIC_SEALED", "policy": "original", "budget_bytes": 65536}})
            assert sealed_source.get("error") or sealed_source.get("result", {}).get("isError"), sealed_source
            denied = call(7, "mousa_sync", {"source": "fleet", "items": [{"id": "service-00000000-prod", "text": "unauthorized replacement"}]})
            assert denied.get("isError") and denied["structuredContent"]["error"]["code"] == "ingestion_not_permitted", denied
            unchanged = call(8, "mousa_query", {"source": "fleet", "query": "SERVICE00000000", "policy": "original", "budget_bytes": 65536})["structuredContent"]["result"]
            assert {(row["item"], row["content_sha256"]) for row in unchanged["evidence"]} == {(row["item"], row["content_sha256"]) for row in selected}
        finally:
            process.stdin.close()
            try:
                code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                code = process.wait(timeout=5)
            errors.seek(0)
            receipt = {"commands": commands, "mcp_argv": argv, "transcript": transcript, "mcp_exit_code": code, "mcp_stderr": errors.read().decode(), "dataset_manifest_sha256": hashlib.sha256((dataset / "manifest.json").read_bytes()).hexdigest(), "binary_sha256": hashlib.sha256(mousa.read_bytes()).hexdigest(), "store_bytes": store.stat().st_size}
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(receipt, indent=2) + "\n")
    assert code == 0
    print(json.dumps({"result": "PASS", "entities": manifest["entities"], "active_items": status["active_items"], "store_bytes": store.stat().st_size, "report": str(report)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true", help="Check an existing store without ingestion; retrieval still records audits")
    parser.add_argument("--rpc-timeout", type=float, default=300, help="Per-response timeout in seconds, including database startup")
    args = parser.parse_args()
    build(args.mousa.resolve(), args.dataset.resolve(), args.store.resolve(), args.report.resolve(), args.verify_only, args.rpc_timeout)


if __name__ == "__main__":
    main()
