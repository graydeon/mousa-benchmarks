# Native supersession administration lifecycle

This record captures the native Mousa CLI lifecycle for revision-pinned supersession declarations and
activations: declaration put/get/retry, activation put/get/state through an initial selection, a
replacement, a deactivation and a reactivation, historical reads, rejected stale or superseded
expectations, read-only store behavior, and one unchanged query baseline.

It is behavior and contract evidence for the pinned revision only. It is not a retrieval-quality,
performance, semantic-contradiction or agent-acceptance result, and it does not demonstrate
suppression: the product revision under test records which declaration is active for a source and
enforces nothing in retrieval yet, which is exactly what the repeated query baseline shows.

* Product observed: `https://github.com/graydeon/mousa` commit `18c26c7ae3f083bc62af489addefa9e5e042b476`,
  tree `741aa7b6e47f32274fa0a5de1b6fcced1e9f6826` (published main).
* Result directory collected 2026-10-07 on `linux/amd64`, `go1.27.1`, `CGO_ENABLED=0`, `GOWORK=off`.
  The recorded capture runs are bound to their own UTC start time (`captured_at_utc` in `observed.json`
  and `assertions.json`) and to the hashes of the executed runner and protocol, so a later reproduction
  cannot be mistaken for this one.
* 40 CLI invocations in separate processes, 158 assertions, 0 failed.
* `protocol.json` freezes the revision, build command, environment, input hashes, expectations and
  limitations; `observed.json` records every argv, stdin identity, exit, stdout, stderr and store
  fingerprint; `assertions.json` records each expectation with the value the run actually observed.

## Frozen inputs and their provenance

`inputs/` holds fixed synthetic bytes: one JSONL item file (three items), two canonical
`mousa.supersession_declaration.v1` records, and the four canonical `mousa.supersession_activation.v1`
events that form the transition chain. They were prepared earlier through the product codecs at product
tree `8e0099ae8745fa26d3f20ed2fa7b025b90c4c396` (the native current activation-state administration
slice, published as public head `72ab3157`) and are frozen here unchanged; `protocol.json` records that
preparation separately from this capture.

That preparation is not this observation. This capture exercises the same bytes afresh against a fresh
synthetic store through the public CLI at the pinned commit, checks the revision pins the declarations
carry against that CLI's query output, and compares every stored readback with the frozen canonical
records. The runner contains no identity hash, imports no Mousa code and uses no product acceptance
helper. Before running anything it re-checks every input hash and the internal consistency of the frozen
chain (one source, each event naming its predecessor, every selected declaration present, every pinned
item present in the JSONL text).

## What the runner checks

* A clean checkout at the pinned commit and tree, and a successful `CGO_ENABLED=0` build with
  `GOWORK=off`; the executable is hashed and never archived.
* Required CLI commands: the pinned usage output must still document declaration put/get and
  activation put/get/state.
* Revision pins: each frozen item is queried, and the reported `item`, `representation_id`,
  `content_sha256` (recomputed from the frozen item text) and released `text` must equal the pins the
  frozen declarations carry.
* Canonical bytes: every accepted put/get must emit exactly the frozen input bytes.
* Current state: each transition's projection must equal exactly
  `{source_id, current_activation_id, active_declaration_id}` for the event just submitted, including
  an explicit JSON `null` declaration while deactivated.
* Rejections: every rejected command must exit 1, print nothing on stdout and report the documented
  storage classification. An assertion failure fails the run; a nonzero exit expected by the protocol
  is recorded as the observation, not as success.

### Per-command store brackets

Each administration read and each expected rejected administration write is bracketed by a store
fingerprint taken immediately before and after that single command, with nothing in between. The
fingerprint covers the schema version, the canonical record tables (`sources`, `observations`,
`artifacts`, `representations`, `segments`), the supersession declaration, activation-event and
current-projection rows, and the bytes of the main database file. The row digests are read through
SQLite, so they include committed transactions wherever they currently live. The database file hash is a
bounded addition: a WAL sidecar may hold committed transactions before a checkpoint, and neither part
proves the absence of every possible write, so this is evidence about the compared values rather than a
general integrity check.

Sixteen read brackets: `get-declaration-first`, `get-declaration-second`, `state-no-history`,
`state-still-absent`, `state-initial`, `get-initial`, `state-replacement`, `get-replacement`,
`state-deactivation`, `get-deactivation`, `state-reactivation`, `get-reactivation`,
`get-historical-initial`, `state-repeat`, `get-repeat-declaration`, `state-after-rejections`.
Four rejected-write brackets: `stale-predecessor-no-history`, `replay-initial`, `replay-replacement`,
`replay-deactivation`.

Query commands are deliberately not bracketed: a query legitimately writes policy decision and trail
rows. Accepted administration writes are checked by their own state assertions instead (the exact
stored row counts and the frozen canonical bytes), not by an unchanged-store assertion.

## Observed lifecycle

| Case | Invocation | Exit | Result |
| --- | --- | --- | --- |
| JSONL sync | `sync --source fixture/state` (frozen items on stdin) | 0 | 3 added items, store ends at schema 14 |
| Revision pins | `query --source fixture/state oldterm\|newterm\|amended` | 0 | one hit each; `item`/`representation_id`/`content_sha256`/`text` equal the frozen pins and item bytes |
| No activation history | `supersession activation state <source>` | 1 | `sqlite not_found: … no rows in result set`; no fabricated state object; bracketed store unchanged |
| Stale expectation before history | `supersession activation put` (replacement event, both declarations stored) | 1 | `sqlite conflict: apply supersession activation: expected previous activation does not exist`; bracketed store unchanged; state still not found |
| Declaration put/get | `supersession declaration put\|get` for both frozen declarations | 0 | stored and read back byte-identical to the frozen canonical records; both reads bracketed |
| Declaration exact retry | `supersession declaration put` (first declaration again) | 0 | byte-identical output, no declaration row added |
| Initial selection | `supersession activation put` then `get` then `state` | 0 | event `bcdb055a…` selects declaration `75471ea8…`; state matches the submitted event; get and state bracketed |
| Exact retry while current | `supersession activation put` (initial event again) | 0 | byte-identical output, no activation row added |
| Replacement | `supersession activation put` then `get` then `state` | 0 | event `a87e9356…` selects declaration `cad04473…`; get and state bracketed |
| Deactivation | `supersession activation put` then `get` then `state` | 0 | event `2637b748…` with `declaration_id: null`; state prints an explicit JSON `null` declaration |
| Reactivation | `supersession activation put` then `get` then `state` | 0 | event `b11aeb41…` selects declaration `75471ea8…` again |
| Historical read | `supersession activation get <initial-event>` | 0 | still byte-identical to the frozen initial event after three later transitions; read bracketed |
| Repeated readbacks | `state` and `declaration get` in new processes | 0 | byte-identical to the earlier reads; both bracketed |
| Superseded replay | `supersession activation put` (initial, replacement and deactivation events) | 1 | `sqlite conflict: … identical activation is no longer current` each time; each replay bracketed and unchanged |
| Absent store | `activation state` and `activation get` against a path that does not exist | 1 | `sqlite internal: open sqlite database: unable to open database file (14)`; stdout empty; the file was not created |

After the four accepted transitions the store holds two declaration rows, four immutable activation
events and one verified current projection (495,616 database file bytes); the digests, the file hash and
the per-command brackets are in `observed.json`.

## Uncurated query baseline

The same query (`oldterm newterm`, `--budget-bytes 8192`) ran five times in separate processes: before
the initial selection and after each of the four transitions. Every run released the same two
passages — the successor revision `b5198ea9…` (rank 1) and the predecessor revision `446eefbd…`
(rank 2), 54 released bytes — and reported the same packet identity
`5bfaf39601fb1fb3c8c4af1ae7d8d62af4348f16e7202c3b28a9620daf11fce9`. Trail identities differ between
runs because the policy request and decision identities a trail binds include the request time, while the
released bytes and their packet identity do not.

This is a deliberately uncurated baseline: it shows that activation administration at this revision
records a selection and withholds nothing, not that suppression is safe or finished.

## Reproductions and negative controls

The corrected runner was executed twice into fresh stores and build directories on 2026-10-07
(`captured_at_utc` 18:57:10Z and 18:57:20Z): both runs passed all 158 assertions with identical
expectation sets, exit statuses, released evidence and packet identity. Neither run requires the other's
timestamps, trail identities or binary bytes to match.

`negative-controls.json` records four disposable controls that show the expectations are load-bearing:

* A one-byte change to a frozen input stops the capture before any command runs (exit 2, no output
  directory).
* Incorrect expected values in a copied protocol fail five named assertions (exit 1).
* A deliberately false boolean check is recorded as `expected true, observed false, passed false` and
  fails the run (exit 1). Before the correction the runner recorded the expectation twice and only the
  pass flag differed, so a failing boolean check could not be read back as an observation.
* A valid query write injected between the `get-declaration-first` read and its after-fingerprint fails
  that read's unchanged assertion (exit 1). The compared database file bytes changed; the canonical and
  administration row digests did not, because that write stores policy decision and trail rows outside
  the tables this bounded fingerprint covers. The control demonstrates that the bracket detects writes
  which change the compared values, not that it detects every possible write.

## Reproduction

Check out the public commit in `protocol.json`, install Go, and run:

```sh
python3 reproduce.py --mousa /path/to/pinned-mousa --output /path/to/new-capture
```

The checkout must be clean and at the pinned commit and tree, the output directory must not exist, and
the frozen input hashes must match. Add `--work <new-directory>` to keep the throwaway binary and the
synthetic stores for inspection. The new capture records its own UTC time and the hashes of the runner
and protocol it executed. Nothing outside the work directory is written, and no accepted or live store is
opened; the runner uses real temporary SQLite files instead.

## Limits

Not measured or not exercised: retrieval quality, semantic handling of contradictory evidence, latency
or resource cost, model or agent acceptance, MCP administration, accepted or live stores, migration of
older stores, damaged-store handling, multi-source isolation, and any enforcement of supersession in
queries. The synthetic single source, three items and four transitions are a fixed fixture, not a sample
of curation workloads. Actor, time and reason fields are recorded evidence, not authenticated authorship.
The store brackets compare only the values listed above; they are bounded per-command evidence and not a
general write detector or integrity proof. `manifest.json` binds every archive member by size and
SHA-256; that integrity check proves file membership, not these conclusions.
