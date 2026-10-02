"""Normalize native client receipts and apply the same evidence grading rules."""

import argparse
import json
from pathlib import Path
import re

from run_codex import evaluate


def parse_answer(text):
    text = text.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def score(harness, case, output, exit_code):
    path = output / (case["id"] + "-events.jsonl")
    events = [json.loads(line) for line in path.read_text().splitlines() if line.startswith("{")]
    normalized = []
    text = ""
    models = set()
    usage = []
    if harness == "omp":
        for event in events:
            message = event.get("message") or {}
            if event.get("type") == "message_end" and message.get("role") == "assistant":
                pieces = [part["text"] for part in message.get("content", []) if part.get("type") == "text"]
                if pieces:
                    text = "\n".join(pieces)
                if message.get("model"):
                    models.add(message["model"])
                if message.get("usage"):
                    usage.append(message["usage"])
            if event.get("type") == "tool_execution_end":
                match = re.search(r"mousa_(query|trail|status|sync)$", event.get("toolName", ""))
                if match:
                    normalized.append({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "mousa", "tool": "mousa_" + match.group(1), "result": event.get("result")}})
                else:
                    normalized.append({"type": "item.completed", "item": {"type": "command_execution"}})
    else:
        for event in events:
            if event.get("type") == "system" and event.get("model"):
                models.add(event["model"])
            if event.get("type") == "result":
                text = event.get("text", "")
                usage.append(event.get("tokens"))
        receipt = output / (case["id"] + "-mcp.jsonl")
        if receipt.exists():
            for row in map(json.loads, receipt.read_text().splitlines()):
                payload = json.loads(row["result"])
                if isinstance(payload.get("result"), str):
                    payload = json.loads(payload["result"])
                result = {"structuredContent": payload}
                normalized.append({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": row["server"], "tool": row["tool"], "result": result}})
    answer = parse_answer(text)
    reasons, tools = evaluate(case, normalized, answer)
    if exit_code != 0:
        reasons.append("cli_failure" if exit_code is not None else "timeout")
    return {"status": "FAIL" if reasons else "PASS", "reasons": sorted(set(reasons)), "tools": tools, "harness_reported_models": sorted(models), "usage": usage}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("omp", "hermes"), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cases = {row["id"]: row for row in map(json.loads, (args.dataset / "tasks.jsonl").read_text().splitlines())}
    rows = json.loads((args.out / "invocations.json").read_text())
    for row in rows:
        row.update(score(args.harness, cases[row["case"]], args.out, row["exit_code"]))
    (args.out / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2))
    raise SystemExit(1 if any(row["status"] != "PASS" for row in rows) else 0)


if __name__ == "__main__":
    main()
