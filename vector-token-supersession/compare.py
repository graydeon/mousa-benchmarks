"""Compare complete native/MCP results after explicit fresh identity exclusions."""
import argparse
import copy
import json
from pathlib import Path

import capture

TOP_LEVEL = ("decision_id", "trail_id", "request_id", "authorization_decision_id",
             "evaluated_at_usec", "elapsed_seconds")
HISTORICAL = ("id", "decision_id", "request_id")


def rows(report):
    observed = []
    for event in report["events"]:
        if event["kind"] in ("start", "stop") or event.get("method") == "notifications/initialized":
            continue
        value = capture.composition.result_from(event)
        if event["kind"] == "rpc" and event["method"] == "tools/call":
            value = value["structuredContent"]["result"]
        value = copy.deepcopy(value)
        for key in TOP_LEVEL:
            value.pop(key, None)
        if "historical" in value:
            for key in HISTORICAL:
                value["historical"].pop(key, None)
        observed.append(dict(label=event["label"], result=value))
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    encoder = capture.composition.tokens.ordinary_encoder(args.cache)
    reports = [json.loads((path / "capture.json").read_text()) for path in (args.left, args.right)]
    for report in reports:
        capture.verify(report, encoder)
    left, right = map(rows, reports)
    capture.equal(left, right, "fresh-store-result-comparison")
    print(json.dumps(dict(result="PASS", compared_result_rows=len(left),
        normalized_top_level_fields=list(TOP_LEVEL), normalized_historical_fields=list(HISTORICAL),
        all_other_properties_equal=True, within_run_identity_bindings="Verified before exclusions; raw values retained.")))


if __name__ == "__main__":
    main()
