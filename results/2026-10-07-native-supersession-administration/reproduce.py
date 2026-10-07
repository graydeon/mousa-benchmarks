#!/usr/bin/env python3
"""Capture the native supersession declaration and activation lifecycle through the public CLI.

The runner builds one clean pinned public Mousa checkout and then drives only the native CLI, in
separate processes, against fresh synthetic SQLite stores. Every expectation comes from the frozen
input bytes, this protocol, or independent read-only inspection of the store; nothing is taken from
the command being observed. The runner imports no Mousa code, uses no product acceptance helper and
never opens an accepted or live store.

Usage:
    python3 reproduce.py --mousa /path/to/pinned-mousa --output /path/to/new-capture

The output directory must not exist. It receives observed.json (the UTC capture time, the executed
runner and protocol hashes, every argv, stdin identity, exit, stdout and stderr) and assertions.json
(each expectation with the value the run actually observed). Administration reads and expected
rejections are bracketed by store fingerprints taken immediately before and after the command; query
commands are excluded because they legitimately write policy decisions and trails. --work keeps the
throwaway build and stores in a named new directory instead of a temporary one, which makes a
failing run inspectable.

Exit status: 0 every assertion passed; 1 at least one assertion failed; 2 the capture never ran
because a precondition failed (dirty or wrong checkout, changed frozen input, failed build, or an
existing output directory).
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RUN_DIR = Path(__file__).resolve().parent
BINARY_PLACEHOLDER = "<binary>"
WORK_PLACEHOLDER = "<work>"
INPUT_ORDER = (
    "items.jsonl",
    "declaration-first.json",
    "declaration-second.json",
    "activation-initial.json",
    "activation-replacement.json",
    "activation-deactivation.json",
    "activation-reactivation.json",
)
# The frozen transition order: each event names the one before it as its expected predecessor.
TRANSITIONS = (
    ("activation-initial.json", "initial selection", "declaration-first.json"),
    ("activation-replacement.json", "replacement", "declaration-second.json"),
    ("activation-deactivation.json", "deactivation with an explicit null declaration", None),
    ("activation-reactivation.json", "reactivation", "declaration-first.json"),
)


class Precondition(Exception):
    """The capture cannot start: checkout, environment or frozen input is wrong."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def row_summary(connection, query):
    """Count the rows of one ordered query and digest every projected value."""
    digest = hashlib.sha256()
    rows = 0
    for row in connection.execute(query):
        for value in row:
            if value is None:
                digest.update(b"\x00")
            else:
                digest.update(b"%d:" % len(value))
                digest.update(value)
        rows += 1
    return {"rows": rows, "sha256": digest.hexdigest()}


def store_fingerprint(path):
    """Read-only summary of one store: schema version, canonical records and supersession rows.

    This reads the database file with the SQLite library instead of through the CLI, so the
    "unchanged" and "not created" assertions do not depend on the command under observation. The
    canonical digest covers the same record tables earlier Mousa administration checks digested.
    """
    if not path.exists():
        return None
    connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        canonical = hashlib.sha256()
        for table in ("sources", "observations", "artifacts", "representations", "segments"):
            for id_value, record_json in connection.execute("SELECT id, record_json FROM %s ORDER BY id" % table):
                canonical.update(id_value or b"")
                canonical.update(record_json or b"")
        for table in ("representation_inputs", "local_items", "segment_lexical_rows"):
            count = connection.execute("SELECT count(*) FROM %s" % table).fetchone()[0]
            canonical.update(("%s:%d\n" % (table, count)).encode())
        sources = {}
        for record_json, in connection.execute("SELECT record_json FROM sources ORDER BY id"):
            record = json.loads(record_json)
            sources[record["external_source_id"]] = {"id": record["id"], "namespace": record["namespace"]}
        return {
            "schema_version": connection.execute(
                "SELECT coalesce(max(version), 0) FROM schema_migrations"
            ).fetchone()[0],
            "canonical_records_sha256": canonical.hexdigest(),
            "sources": sources,
            "declarations": row_summary(connection, "SELECT id, record_json FROM supersession_declarations ORDER BY id"),
            "activations": row_summary(
                connection,
                "SELECT id, source_id, expected_previous_activation_id, declaration_id, record_json "
                "FROM supersession_activations ORDER BY id",
            ),
            "current_state": row_summary(
                connection,
                "SELECT source_id, current_activation_id, active_declaration_id "
                "FROM supersession_activation_state ORDER BY source_id",
            ),
            "file": {"bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())},
        }
    finally:
        connection.close()


def load_protocol():
    """Read the protocol next to this script and verify every frozen input byte."""
    protocol = json.loads((RUN_DIR / "protocol.json").read_text())
    frozen = {}
    for name in INPUT_ORDER:
        path = RUN_DIR / "inputs" / name
        if not path.is_file():
            raise Precondition("missing frozen input: inputs/%s" % name)
        data = path.read_bytes()
        if sha256(data) != protocol["inputs"][name]:
            raise Precondition("frozen input differs from the protocol: inputs/%s" % name)
        frozen[name] = data
    protocol["frozen"] = frozen
    return protocol


def check_frozen_lifecycle(protocol):
    """Check the frozen records against each other before any command runs.

    These comparisons only use the frozen inputs and the frozen item texts: no expectation here is
    derived from the CLI under observation. A disagreement means the fixture itself is unusable.
    """
    frozen = protocol["frozen"]

    def fail(reason):
        raise Precondition("frozen inputs disagree: %s" % reason)

    items = {}
    for line in frozen["items.jsonl"].decode("utf-8").splitlines():
        record = json.loads(line)
        if record["id"] in items:
            fail("items.jsonl repeats item %r" % record["id"])
        items[record["id"]] = record["text"]

    def load(name):
        try:
            return json.loads(frozen[name])
        except ValueError as error:
            fail("inputs/%s is not JSON (%s)" % (name, error))

    declarations = {name: load(name) for name in INPUT_ORDER if name.startswith("declaration-")}
    activations = {name: load(name) for name in INPUT_ORDER if name.startswith("activation-")}

    pins = {}
    for name, declaration in sorted(declarations.items()):
        if declaration.get("schema") != "mousa.supersession_declaration.v1":
            fail("%s has schema %r" % (name, declaration.get("schema")))
        for role in ("predecessor", "successor"):
            item = declaration["%s_item_id" % role]
            representation = declaration["%s_representation_id" % role]
            if item not in items:
                fail("%s pins item %r outside items.jsonl" % (name, item))
            if pins.setdefault(item, representation) != representation:
                fail("item %r carries conflicting representation pins" % item)
    for name, event in sorted(activations.items()):
        if event.get("schema") != "mousa.supersession_activation.v1":
            fail("%s has schema %r" % (name, event.get("schema")))
    for position, (name, _, selected) in enumerate(TRANSITIONS):
        event = activations[name]
        predecessor = activations[TRANSITIONS[position - 1][0]]["id"] if position else None
        if event["expected_previous_activation_id"] != predecessor:
            fail("%s does not name its predecessor as expected" % name)
        if (event["declaration_id"] is None) != (selected is None):
            fail("%s disagrees with the declared transition shape" % name)
        if selected is not None and event["declaration_id"] != declarations[selected]["id"]:
            fail("%s selects %s instead of %s" % (name, event["declaration_id"], selected))
    sources = {record["source_id"] for record in declarations.values()} | {
        event["source_id"] for event in activations.values()
    }
    if len(sources) != 1:
        fail("the frozen records cover %d sources" % len(sources))
    protocol["items"] = items
    protocol["pins"] = pins
    protocol["declarations"] = declarations
    protocol["activations"] = activations
    protocol["source_id"] = sources.pop()


def check_checkout(mousa, protocol):
    """A dirty checkout, or any commit or tree other than the pinned one, stops the capture."""
    def git(*argv):
        completed = subprocess.run(["git", "-C", str(mousa), *argv], capture_output=True, text=True)
        if completed.returncode != 0:
            raise Precondition("git %s failed in %s: %s" % (" ".join(argv), mousa, completed.stderr.strip()))
        return completed.stdout.strip()

    if git("status", "--porcelain"):
        raise Precondition("Mousa checkout is not clean: %s" % mousa)
    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    if head != protocol["commit"] or tree != protocol["tree"]:
        raise Precondition("Mousa checkout is %s tree %s, not the pinned %s tree %s"
                           % (head, tree, protocol["commit"], protocol["tree"]))
    return head, tree


def baseline_core(report):
    """The part of one query report that supersession administration must not change."""
    return {
        "query": report["query"],
        "expression": report["expression"],
        "outcome": report["outcome"],
        "matched_candidates": report["matched_candidates"],
        "used_bytes": report["used_bytes"],
        "budget_bytes": report["budget_bytes"],
        "packet_id": report["packet_id"],
        "evidence": [
            {key: hit[key] for key in ("item", "representation_id", "content_sha256", "byte_length", "rank", "text")}
            for hit in report["evidence"]
        ],
    }


class Capture:
    """One capture run: observations, assertions and the throwaway paths behind them."""

    def __init__(self, protocol, binary, work, env):
        self.binary = binary
        self.work = work
        self.env = env
        self.store = work / "store" / "local.sqlite"
        self.expectations = protocol["expectations"]
        self.items = protocol["items"]
        self.pins = protocol["pins"]
        self.declarations = protocol["declarations"]
        self.activations = protocol["activations"]
        self.source_id = protocol["source_id"]
        self.store_argv = ["-store", "<work>/store/local.sqlite"]
        self.observations = []
        self.assertions = []
        self.fingerprints = {}
        self.failed = 0

    # Recording -------------------------------------------------------------

    def check(self, ident, passed, expected, observed, note):
        self.assertions.append(
            {"id": ident, "check": note, "expected": expected, "observed": observed, "passed": bool(passed)}
        )
        if not passed:
            self.failed += 1

    def expect(self, ident, expected, observed, note):
        self.check(ident, expected == observed, expected, observed, note)

    def expect_true(self, ident, condition, note):
        """Record a boolean check as the observation it actually made.

        A false condition is recorded as observed false and fails; recording the expectation twice
        would hide which value the run saw.
        """
        observed = bool(condition)
        self.check(ident, observed is True, True, observed, note)

    def expect_stderr(self, ident, expected, observation, note):
        self.check(ident, expected in observation["stderr"]["text"], expected, observation["stderr"]["text"], note)

    def expect_bytes(self, ident, expected, observation, note):
        """Compare emitted stdout with expected bytes without a decode round trip."""
        self.check(ident, observation["stdout"]["sha256"] == sha256(expected), sha256(expected),
                   observation["stdout"]["sha256"], note)

    def cli(self, step, purpose, argv, stdin_path=None):
        """Run one CLI process and record its argv, stdin identity, exit, stdout and stderr."""
        resolved = [
            token.replace(BINARY_PLACEHOLDER, str(self.binary)).replace(WORK_PLACEHOLDER, str(self.work))
            for token in argv
        ]
        payload = Path(stdin_path).read_bytes() if stdin_path else b""
        completed = subprocess.run(resolved, input=payload, cwd=str(self.work), env=self.env, capture_output=True)
        observation = {
            "step": step,
            "purpose": purpose,
            "argv": list(argv),
            "stdin": {
                "source": "inputs/%s" % Path(stdin_path).name if stdin_path else "empty",
                "bytes": len(payload),
                "sha256": sha256(payload),
            },
            "exit": completed.returncode,
            "stdout": {
                "bytes": len(completed.stdout),
                "sha256": sha256(completed.stdout),
                "text": completed.stdout.decode("utf-8", "replace"),
            },
            "stderr": {
                "bytes": len(completed.stderr),
                "sha256": sha256(completed.stderr),
                "text": completed.stderr.decode("utf-8", "replace"),
            },
        }
        self.observations.append(observation)
        return observation

    def parsed(self, observation):
        """The parsed JSON report of one command, or None when it emitted none."""
        text = observation["stdout"]["text"]
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            return None

    def fingerprint(self, label):
        current = store_fingerprint(self.store)
        self.fingerprints[label] = current
        return current

    def expect_unchanged(self, ident, before, after, note):
        """A read-only or rejected command must leave the stored state unchanged.

        The compared fingerprint covers the schema version, the canonical record tables
        (sources, observations, artifacts, representations, segments), the supersession
        declaration, activation-event and current-projection rows, and the bytes of the main
        database file. The row digest is read through SQLite, so it includes committed
        transactions wherever they currently live; the database file hash is a bounded addition
        and does not by itself prove that nothing was written, because a WAL sidecar may hold
        committed transactions before a checkpoint.
        """
        keys = ("schema_version", "canonical_records_sha256", "sources", "declarations",
                "activations", "current_state", "file")
        expected = {key: before[key] for key in keys} if before else None
        observed = {key: after[key] for key in keys} if after else None
        self.check(ident, expected == observed, expected, observed, note)

    def bracket(self, step, purpose, argv, note, stdin_path=None):
        """Run one command that must not change stored state and bracket it with fingerprints.

        Used for administration reads and for expected rejections. The fingerprints are taken
        immediately before and after the command with nothing in between, so any committed write
        by the command or by an injected step changes the compared values. Query commands are
        excluded: they legitimately write policy decisions and trails.
        """
        before = self.fingerprint("%s:before" % step)
        observation = self.cli(step, purpose, argv, stdin_path=stdin_path)
        after = self.fingerprint("%s:after" % step)
        self.expect_unchanged("%s-store-unchanged" % step, before, after, note)
        return observation


def read_pins_and_baseline(capture, protocol):
    """Read the revision pins through the pinned CLI and run the pre-activation baseline query."""
    for spec in protocol["pin_queries"]:
        token = slug(spec["query"])
        query = capture.cli(
            "pin-query-%s" % token, "read the revision pin the pinned CLI reports for one frozen item",
            [BINARY_PLACEHOLDER, *capture.store_argv, "query", "--source", protocol["source_external_id"], spec["query"]],
        )
        capture.expect("pin-query-%s-exit" % token, 0, query["exit"], "querying one frozen item succeeds")
        report = capture.parsed(query)
        hits = report["evidence"] if report else []
        capture.expect("pin-query-%s-hits" % token, 1, len(hits), "the frozen item is the single lexical hit")
        if len(hits) != 1:
            continue
        hit, item = hits[0], spec["item"]
        capture.expect("pin-query-%s-item" % token, item, hit["item"], "the hit is the frozen item")
        capture.expect("pin-query-%s-representation" % token, capture.pins[item], hit["representation_id"],
                       "the reported revision equals the pin frozen in the declaration inputs")
        capture.expect("pin-query-%s-content" % token, sha256(capture.items[item].encode()), hit["content_sha256"],
                       "the reported content digest is the digest of the frozen item text")
        capture.expect("pin-query-%s-text" % token, capture.items[item], hit["text"],
                       "the released text is the frozen item text")


def run_capture(capture, protocol):
    baseline_spec = protocol["baseline_query"]
    expected_bytes = sum(len(capture.items[item].encode()) for item in baseline_spec["items"])

    def baseline(index, when):
        observation = capture.cli(
            "baseline-query-%d" % index, "same synthetic query %s" % when,
            [BINARY_PLACEHOLDER, *capture.store_argv, "query", "--source", protocol["source_external_id"],
             "--budget-bytes", str(baseline_spec["budget_bytes"]), baseline_spec["text"]],
        )
        capture.expect("baseline-%d-exit" % index, 0, observation["exit"], "the synthetic query succeeds")
        report = capture.parsed(observation)
        core = baseline_core(report) if report else {}
        capture.expect("baseline-%d-outcome" % index, "evidence", core.get("outcome"), "the query releases evidence")
        capture.expect("baseline-%d-matches" % index, len(baseline_spec["items"]), core.get("matched_candidates"),
                       "both synthetic current items match")
        capture.expect("baseline-%d-bytes" % index, expected_bytes, core.get("used_bytes"),
                       "released bytes equal the frozen item text bytes")
        capture.expect("baseline-%d-evidence" % index,
                       {item: {"representation_id": capture.pins[item], "content_sha256": sha256(capture.items[item].encode()),
                               "byte_length": len(capture.items[item].encode()), "text": capture.items[item]}
                        for item in baseline_spec["items"]},
                       {hit["item"]: {key: hit[key] for key in
                                      ("representation_id", "content_sha256", "byte_length", "text")}
                        for hit in core.get("evidence", [])},
                       "the released evidence is the frozen predecessor and successor revisions")
        return core

    # The pinned CLI must still expose the administration commands this capture drives.
    usage = capture.cli("cli-usage", "confirm the pinned CLI exposes the supersession administration commands",
                        [BINARY_PLACEHOLDER])
    capture.expect("cli-usage-exit", capture.expectations["usage_exit"], usage["exit"],
                   "a missing command is an invalid invocation")
    for spelling in capture.expectations["usage_command_spellings"]:
        capture.expect_stderr("cli-usage-lists-%s" % slug(spelling), spelling, usage,
                              "the pinned usage text still documents %r" % spelling)

    # Populate one fresh synthetic store through the supported JSONL ingress.
    capture.expect_true("store-absent-before-sync", not capture.store.exists(),
                        "the synthetic store does not exist before the first write")
    sync = capture.cli(
        "sync", "populate the fresh synthetic store from the frozen JSONL items",
        [BINARY_PLACEHOLDER, *capture.store_argv, "sync", "--source", protocol["source_external_id"]],
        stdin_path=RUN_DIR / "inputs" / "items.jsonl",
    )
    capture.expect("sync-exit", 0, sync["exit"], "JSONL sync of the frozen items succeeds")
    after_sync = capture.fingerprint("after-sync")
    capture.expect("store-schema-version", capture.expectations["store_schema_version"], after_sync["schema_version"],
                   "the store ends at the pinned schema version")
    capture.expect("store-source-record",
                   {"id": capture.source_id, "namespace": capture.expectations["source_namespace"]},
                   after_sync["sources"].get(protocol["source_external_id"]),
                   "the store's own source record carries the frozen canonical identity and namespace")

    read_pins_and_baseline(capture, protocol)
    baseline_zero = baseline(0, "before the initial activation")

    # Declarations: put, get and exact retry.
    for name in ("declaration-first.json", "declaration-second.json"):
        token = name[: -len(".json")]
        put = capture.cli(
            "put-%s" % token, "append one frozen canonical declaration",
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "declaration", "put"],
            stdin_path=RUN_DIR / "inputs" / name,
        )
        capture.expect("put-%s-exit" % token, 0, put["exit"], "the declaration is accepted")
        capture.expect_bytes("put-%s-canonical-bytes" % token, protocol["frozen"][name], put,
                             "put prints exactly the frozen canonical declaration bytes")
        get = capture.bracket(
            "get-%s" % token, "read the stored declaration by identity",
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "declaration", "get", capture.declarations[name]["id"]],
            "the declaration read changes no stored row and no database file byte",
        )
        capture.expect("get-%s-exit" % token, 0, get["exit"], "the stored declaration is readable")
        capture.expect_bytes("get-%s-canonical-bytes" % token, protocol["frozen"][name], get,
                             "a get returns the frozen canonical bytes")
        if token == "declaration-first":
            declaration_read_sha = get["stdout"]["sha256"]
    after_declarations = capture.fingerprint("after-declarations")
    capture.expect("declarations-stored", 2, after_declarations["declarations"]["rows"],
                   "both frozen declarations are stored")
    retry = capture.cli(
        "retry-declaration-first", "exact retry of one stored declaration",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "declaration", "put"],
        stdin_path=RUN_DIR / "inputs" / "declaration-first.json",
    )
    capture.expect("retry-declaration-first-exit", 0, retry["exit"], "an exact retry is idempotent")
    capture.expect_bytes("retry-declaration-first-canonical-bytes",
                         protocol["frozen"]["declaration-first.json"], retry,
                         "the retry prints the same canonical bytes")
    after_retry = capture.fingerprint("after-declaration-retry")
    capture.expect("retry-declaration-first-no-new-row", after_declarations["declarations"],
                   after_retry["declarations"], "the retry appends no declaration row")

    # A source with stored declarations but no activation history is a not-found error, not
    # fabricated null state.
    no_history = capture.bracket(
        "state-no-history", "read current state for a source that has stored declarations but no activation history",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "state", capture.source_id],
        "the not-found read changes no stored row and no database file byte",
    )
    capture.expect("state-no-history-exit", capture.expectations["storage_error_exit"], no_history["exit"],
                   "a source without activation history reports a storage error")
    capture.expect("state-no-history-empty-stdout", "", no_history["stdout"]["text"],
                   "the read fabricates no null state object")
    capture.expect_stderr("state-no-history-classification", capture.expectations["stderr"]["state_no_history"],
                          no_history, "the documented not-found classification is reported")

    # A named expected predecessor that does not exist is rejected, and creates no history.
    pre_history = capture.bracket(
        "stale-predecessor-no-history",
        "submit a replacement whose expected predecessor does not exist, with both declarations stored",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "put"],
        "the rejected transition appends no event and changes no database file byte",
        stdin_path=RUN_DIR / "inputs" / "activation-replacement.json",
    )
    capture.expect("stale-predecessor-no-history-exit", capture.expectations["rejection_exit"], pre_history["exit"],
                   "a missing expected predecessor is rejected")
    capture.expect("stale-predecessor-no-history-empty-stdout", "", pre_history["stdout"]["text"],
                   "the rejected transition prints nothing")
    capture.expect_stderr("stale-predecessor-no-history-classification",
                          capture.expectations["stderr"]["pre_history_expectation"], pre_history,
                          "the documented conflict classification is reported")
    still_absent = capture.bracket(
        "state-still-absent", "re-read current state after the rejected transition",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "state", capture.source_id],
        "the read after the rejected transition changes no stored row and no database file byte",
    )
    capture.expect_stderr("state-still-absent-classification", capture.expectations["stderr"]["state_no_history"],
                          still_absent, "the rejected transition created no history")

    # Activation transitions: initial selection, replacement, deactivation and reactivation.
    index = 1
    previous_view = None
    for position, (name, purpose, selected) in enumerate(TRANSITIONS):
        label = name[len("activation-"):-len(".json")]
        event, frozen_bytes = capture.activations[name], protocol["frozen"][name]
        put = capture.cli(
            "put-%s" % label, "apply the frozen %s transition" % purpose,
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "put"],
            stdin_path=RUN_DIR / "inputs" / name,
        )
        capture.expect("put-%s-exit" % label, 0, put["exit"], "the %s transition is accepted" % purpose)
        capture.expect_bytes("put-%s-canonical-bytes" % label, frozen_bytes, put,
                             "the applied event prints the frozen canonical bytes")
        state = capture.bracket(
            "state-%s" % label, "read current state after the %s transition" % purpose,
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "state", capture.source_id],
            "the state read after the %s changes no stored row and no database file byte" % purpose,
        )
        capture.expect("state-%s-exit" % label, 0, state["exit"], "current state is readable after the transition")
        view = capture.parsed(state)
        capture.expect("state-%s-view" % label,
                       {"source_id": capture.source_id, "current_activation_id": event["id"],
                        "active_declaration_id": None if selected is None else capture.declarations[selected]["id"]},
                       view, "the verified state matches the submitted current event")
        if selected is None:
            capture.expect_true("state-%s-explicit-null" % label,
                                '"active_declaration_id": null' in state["stdout"]["text"],
                                "a deactivated source prints an explicit JSON null declaration")
        get = capture.bracket(
            "get-%s" % label, "read the stored event by identity",
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "get", event["id"]],
            "the event read after the %s changes no stored row and no database file byte" % purpose,
        )
        capture.expect("get-%s-exit" % label, 0, get["exit"], "the stored event is readable")
        capture.expect_bytes("get-%s-canonical-bytes" % label, frozen_bytes, get,
                             "a get returns the frozen canonical bytes")
        if position == 0:
            # An exact retry succeeds only while its event is still current.
            before_retry = capture.fingerprint("before-initial-retry")
            retry_initial = capture.cli(
                "retry-initial-current", "exact retry of the initial event while it is still current",
                [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "put"],
                stdin_path=RUN_DIR / "inputs" / name,
            )
            capture.expect("retry-initial-current-exit", 0, retry_initial["exit"],
                           "an exact retry of the current event succeeds")
            capture.expect_bytes("retry-initial-current-canonical-bytes", frozen_bytes, retry_initial,
                                 "the retry prints the same canonical event bytes")
            capture.expect("retry-initial-current-no-new-row", before_retry["activations"],
                           capture.fingerprint("after-initial-retry")["activations"],
                           "the retry appends no activation event")
        previous_view = view
        state_read_sha = state["stdout"]["sha256"]
        baseline(index, "after the %s transition" % purpose)
        index += 1

    after_transitions = capture.fingerprint("after-transitions")
    capture.expect("activations-stored", 4, after_transitions["activations"]["rows"],
                   "all four transitions are stored as immutable events")
    capture.expect("current-state-rows", 1, after_transitions["current_state"]["rows"],
                   "one source carries one verified current projection")

    # The uncurated baseline: administration must not change which evidence is released.
    cores = {}
    for entry in capture.observations:
        if entry["step"].startswith("baseline-query-"):
            report = capture.parsed(entry)
            if report:
                cores[entry["step"]] = baseline_core(report)
    capture.expect("baseline-runs-complete",
                   ["baseline-query-%d" % number for number in range(len(TRANSITIONS) + 1)], sorted(cores),
                   "every scheduled baseline query produced a readable report")
    for step, core in sorted(cores.items()):
        if step == "baseline-query-0":
            continue
        number = step.rsplit("-", 1)[1]
        capture.expect("baseline-%s-packet-unchanged" % number, baseline_zero["packet_id"], core["packet_id"],
                       "the packet identity of unchanged released bytes is unchanged")
        capture.expect("baseline-%s-evidence-unchanged" % number, baseline_zero["evidence"], core["evidence"],
                       "the same evidence identities and bytes are still released")
        capture.expect_true("baseline-%s-predecessor-released" % number,
                            any(hit["item"] == "doc" and hit["representation_id"] == capture.pins["doc"]
                                for hit in core["evidence"]),
                            "activation administration does not yet withhold the declared predecessor revision")

    # Historical reads stay byte-identical, and repeated readbacks in another process agree.
    historical = capture.bracket(
        "get-historical-initial", "read the initial event after later transitions advanced the current state",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "get",
         capture.activations["activation-initial.json"]["id"]],
        "the historical event read changes no stored row and no database file byte",
    )
    capture.expect("get-historical-initial-exit", 0, historical["exit"], "a historical event stays readable")
    capture.expect_bytes("get-historical-initial-canonical-bytes",
                         protocol["frozen"]["activation-initial.json"], historical,
                         "the historical event still reads its own canonical bytes")
    repeat_state = capture.bracket(
        "state-repeat", "repeat the current-state readback in another process",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "state", capture.source_id],
        "the repeated state read changes no stored row and no database file byte",
    )
    repeat_declaration = capture.bracket(
        "get-repeat-declaration", "repeat a stored declaration readback in another process",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "declaration", "get",
         capture.declarations["declaration-first.json"]["id"]],
        "the repeated declaration read changes no stored row and no database file byte",
    )
    capture.expect("state-repeat-identical-bytes", state_read_sha, repeat_state["stdout"]["sha256"],
                   "the repeated current-state read emits identical bytes")
    capture.expect("get-repeat-declaration-identical-bytes", declaration_read_sha,
                   repeat_declaration["stdout"]["sha256"],
                   "the repeated declaration read emits identical bytes")

    # Replaying a superseded event, including a stale expectation, is a conflict that changes nothing.
    for name in ("activation-initial.json", "activation-replacement.json", "activation-deactivation.json"):
        label = name[len("activation-"):-len(".json")]
        replay = capture.bracket(
            "replay-%s" % label, "replay a superseded event after the current state advanced",
            [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "put"],
            "the rejected replay appends no event and changes no database file byte",
            stdin_path=RUN_DIR / "inputs" / name,
        )
        capture.expect("replay-%s-exit" % label, capture.expectations["rejection_exit"], replay["exit"],
                       "a superseded event is rejected")
        capture.expect("replay-%s-empty-stdout" % label, "", replay["stdout"]["text"],
                       "the rejected replay prints nothing")
        capture.expect_stderr("replay-%s-classification" % label, capture.expectations["stderr"]["historical_retry"],
                              replay, "the documented conflict classification is reported")
    state_after = capture.bracket(
        "state-after-rejections", "confirm current state is unchanged after the rejected replays",
        [BINARY_PLACEHOLDER, *capture.store_argv, "supersession", "activation", "state", capture.source_id],
        "the read after the rejected replays changes no stored row and no database file byte",
    )
    capture.expect("state-after-rejections-unchanged", previous_view.get("current_activation_id"),
                   (capture.parsed(state_after) or {}).get("current_activation_id"),
                   "the rejected replays left the current activation unchanged")

    # Reads never create a store.
    for command, identity in (("state", capture.source_id),
                              ("get", capture.activations["activation-initial.json"]["id"])):
        absent_path = capture.work / "store" / ("absent-%s.sqlite" % command)
        absent = capture.cli(
            "absent-store-%s" % command, "read against a store path that does not exist",
            [BINARY_PLACEHOLDER, "-store", "<work>/store/absent-%s.sqlite" % command,
             "supersession", "activation", command, identity],
        )
        capture.expect("absent-store-%s-exit" % command, capture.expectations["storage_error_exit"], absent["exit"],
                       "an absent store is a storage error")
        capture.expect("absent-store-%s-empty-stdout" % command, "", absent["stdout"]["text"],
                       "the read prints nothing")
        capture.expect_stderr("absent-store-%s-classification" % command,
                              capture.expectations["stderr"]["absent_store"], absent,
                              "the read reports the storage open failure")
        capture.expect_true("absent-store-%s-not-created" % command, not absent_path.exists(),
                            "the read did not create the store file")
    capture.fingerprint("final")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mousa", required=True, type=Path,
                        help="clean checkout of the pinned public Mousa commit")
    parser.add_argument("--output", required=True, type=Path,
                        help="new output directory for observed.json and assertions.json")
    parser.add_argument("--work", type=Path, default=None,
                        help="keep the throwaway build and stores in this new directory")
    args = parser.parse_args(argv)

    temporary = args.work is None
    work = None
    try:
        protocol = load_protocol()
        check_frozen_lifecycle(protocol)
        mousa = args.mousa.resolve()
        if not mousa.is_dir():
            raise Precondition("Mousa checkout does not exist: %s" % mousa)
        commit, tree = check_checkout(mousa, protocol)
        if args.output.exists():
            raise Precondition("output directory already exists: %s" % args.output)
        work = Path(tempfile.mkdtemp(prefix="mousa-native-supersession-")) if temporary else args.work.resolve()
        if not temporary and work.exists():
            raise Precondition("work directory already exists: %s" % work)
        (work / "store").mkdir(parents=True)
        env = dict(os.environ, GOWORK="off", CGO_ENABLED="0")
        build = protocol["build"]["command"]
        binary = work / "mousa"
        completed = subprocess.run([build[0], *build[1:-2], str(binary), build[-1]],
                                   cwd=str(mousa), env=env, capture_output=True)
        if completed.returncode != 0:
            raise Precondition("build failed: %s" % completed.stderr.decode("utf-8", "replace").strip())

        def goenv(*argv):
            return subprocess.run(("go",) + argv, env=env, capture_output=True, text=True).stdout.strip()

        capture = Capture(protocol, binary, work, env)
        run_capture(capture, protocol)
        capture.expect_true("output-directory-untouched", not args.output.exists(),
                            "the capture wrote nothing outside its work directory before these records")
        source_binding = {
            "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "protocol": {
                "file": "protocol.json",
                "sha256": sha256((RUN_DIR / "protocol.json").read_bytes()),
                "collected": protocol["collected"],
            },
            "runner": {
                "file": "reproduce.py",
                "sha256": sha256(Path(__file__).read_bytes()),
            },
        }
        observed = {
            "schema": "mousa.native_supersession_cli_observation.v1",
            **source_binding,
            "mousa": {"repository": protocol["repository"], "commit": commit, "tree": tree,
                      "clean_before_capture": True},
            "build": {
                "command": protocol["build"]["command"],
                "environment": protocol["build"]["environment"],
                "go_version": goenv("version"),
                "go_platform": {key: goenv("env", key) for key in ("GOOS", "GOARCH", "GOAMD64", "GOTOOLCHAIN")},
                "binary": {"sha256": sha256(binary.read_bytes()), "bytes": binary.stat().st_size, "archived": False},
            },
            "store_fingerprints": capture.fingerprints,
            "observations": capture.observations,
            "assertions": {"total": len(capture.assertions), "failed": capture.failed},
        }
        report = {
            "schema": "mousa.native_supersession_cli_assertions.v1",
            **source_binding,
            "scope": protocol["scope"],
            "limitations": protocol["limitations"],
            "assertions": capture.assertions,
            "total": len(capture.assertions),
            "failed": capture.failed,
            "passed": capture.failed == 0,
        }
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "observed.json").write_text(json.dumps(observed, indent=2) + "\n")
        (args.output / "assertions.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({
            "observations": len(capture.observations),
            "assertions": len(capture.assertions),
            "failed": capture.failed,
            "packet_id": next((baseline_core(capture.parsed(entry))["packet_id"]
                               for entry in capture.observations if entry["step"] == "baseline-query-0"), None),
            "work_directory": None if temporary else str(work),
        }))
        return 0 if capture.failed == 0 else 1
    except Precondition as failure:
        print("error: %s" % failure, file=sys.stderr)
        return 2
    finally:
        if temporary and work is not None:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
