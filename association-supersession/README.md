# Supersession-safe lexical supporting context

This frozen synthetic schedule observes byte-only lexical queries that combine
caller-declared supporting passages with explicit revision-pinned supersession.
It uses public native directory/JSONL commands and configured stdio MCP, with no
SQL, product-package imports, database/binary export, model calls or paid inference.
The exact product head/tree and runner/helper hashes are in `protocol.json`.

## Schedule and binding

Each fresh store executes 24 native commands and one 13-frame MCP session.
Native administration records exact predecessor/successor declaration and
activation pins discovered through authorized `vector inputs`; no vectors are
imported and all queries stay lexical. Both native source forms and both packers
run two query texts, each followed by history inspection:

- `instruction` selects only the primary item. Its associations consider the
  pinned old passage, an unsuppressed byte-equal twin and a nonmatching supporting
  qualification. The old target is `superseded`; twin and qualification survive.
- `needle` additionally matches old and twin. Old primary is withheld and cannot
  fire its own declaration. Twin is retained primary evidence; its associated
  occurrence is a duplicate, not an extra release. The qualification survives.

Configured MCP repeats both texts/packers and opted-in history, then inspects
one history without the supersession opt-in and explicitly refuses the token
triple. Tool discovery validates each response against its closed output schema.
Supporting attribution is not semantic sufficiency. Explicit replacement is not
truth inference, and the successor is never retrieved as a fallback.

The replay regenerates the complete native command/stdin and MCP request
populations from frozen fixture bytes and prior producing results, including
all strict JSON types. It checks actual responses, exact exported pins, body
bytes/digests/coordinates, primary and associated suppression facts, attribution,
selection, byte totals and producing history identities. It retains raw argv,
stdin/stdout/stderr, process exits, all frames and send completion. Partial
attempts are saved before execution; failures stop rather than disappear or retry.
No accepted final capture contains an unrecorded failed attempt.

The two independent runs use fresh databases. The synthetic directory pathname
`/tmp/mousa-public-composed-notes` is intentionally fixed so source identity and
all producing pins can be compared without normalization. Capture creates it
exclusively, refuses an existing path and removes only its own fixture. Run the
two captures sequentially. Their temporary store paths remain in raw argv.
Comparison excludes only per-call request/decision/trail/authorization identities
and evaluation/latency timing. Packet IDs, declaration/activation pins, retained
bytes, ordering, scores, all safe history facts and omission reasons are compared.

Three controls retain self-consistent stream/archive hashes while changing an
association request's exact type, recorded suppression facts, or returned support
text/digests/coordinates. Replays must reject at `scheduled-request-bytes`,
`history-suppression-binding` and `evidence-content-binding` respectively, not at
an outer checksum. Mutated archives and receipts are retained.

## Reproduce

Build the product from the exact clean public `product_head` in `protocol.json`,
using `CGO_ENABLED=0 GOAMD64=v1 go build -o /tmp/mousa-composed ./cmd/mousa` inside
that checkout. From this repository, pass the resulting binary and checkout:

```sh
python3 association-supersession/capture.py capture --mousa /tmp/mousa-composed \
  --product-source /tmp/mousa-public-source --output /tmp/composed-first
python3 association-supersession/capture.py capture --mousa /tmp/mousa-composed \
  --product-source /tmp/mousa-public-source --output /tmp/composed-second
python3 association-supersession/capture.py verify --capture /tmp/composed-first/capture.json.gz
python3 association-supersession/capture.py verify --capture /tmp/composed-second/capture.json.gz
python3 association-supersession/capture.py compare --capture /tmp/composed-first/capture.json.gz \
  --other /tmp/composed-second/capture.json.gz
python3 association-supersession/capture.py controls --capture /tmp/composed-first/capture.json.gz \
  --output /tmp/composed-controls
python3 tools/verify_results.py
```

Ordinary native/MCP capture needs no Python tokenizer backend. Python here drives
public clients and verifies archives, not a second canonical store. Use new output
directories. Stored archives replay offline through the same `verify`, `compare`
and `controls` modes; runner/helper hashes prevent silently changing the protocol.

## Evidence limits

Replay proves internal consistency with the frozen schedule, not authenticity of
execution or protection against rewriting the whole archive and protocol. Small
paired runs are deterministic client observations, not statistical estimates,
semantic quality, authenticated authorship, temporal truth, universal absence,
model quality, performance or cross-platform acceptance.

Internal snapshot ordering, cancellation/fault rollback, lifecycle-rejected mixed
ancestry, resealed canonical corruption, missing parents/startup refusal, capacity
boundaries and unavailable retired bytes remain product-test claims. Ordinary
public clients cannot establish them, and matching outputs are not credited as
that proof. No historical result/protocol/helper bytes are replaced by this addition.
