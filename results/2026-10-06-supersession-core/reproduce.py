"""Capture the pinned product contract tests in a fresh output directory."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mousa", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
source = args.mousa.resolve()
protocol = json.loads(Path(__file__).with_name("protocol.json").read_text())
def git(*argv):
    return subprocess.check_output(["git", "-C", str(source), *argv], text=True).strip()
if git("status", "--porcelain"):
    raise SystemExit("Mousa checkout must be clean")
if git("rev-parse", "HEAD") != protocol["commit"] or git("rev-parse", "HEAD^{tree}") != protocol["tree"]:
    raise SystemExit("Mousa source identity differs from the pinned protocol")
args.output.mkdir(parents=True, exist_ok=False)
run_env = dict(os.environ, GOWORK="off")
result = subprocess.run(protocol["command"], cwd=source, env=run_env, capture_output=True, text=True)
(args.output / "go-test-events.jsonl").write_text(result.stdout)
(args.output / "stderr.txt").write_text(result.stderr)
events = [json.loads(line) for line in result.stdout.splitlines()]
passed = sorted(e["Test"] for e in events if e.get("Action") == "pass" and "Test" in e and "/" not in e["Test"])
subtests = sum(e.get("Action") == "pass" and "/" in e.get("Test", "") for e in events)
failed = [e for e in events if e.get("Action") in ("fail", "skip")]
valid = result.returncode == 0 and passed == protocol["expected_top_level_tests"] and not failed
observed = {"schema": "mousa.supersession_contract_observation.v1", "commit": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"), "go_version": subprocess.check_output(["go", "version"], env=run_env, text=True).strip(), "command": protocol["command"], "environment": {"GOWORK": "off"}, "exit_code": result.returncode, "passed_top_level_tests": passed, "passed_subtests": subtests, "failed_or_skipped": failed, "contract_checks_passed": valid, "limitations": protocol["scope"]}
(args.output / "observed.json").write_text(json.dumps(observed, indent=2) + "\n")
print(json.dumps({"passed_top_level_tests": len(passed), "passed_subtests": subtests, "contract_checks_passed": valid}))
raise SystemExit(0 if valid else 1)
