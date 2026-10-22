# Native token-aware context example

This small driver invokes the Mousa executable on synthetic directory and JSONL
sources. It exercises lexical, supplied-vector and hybrid token-aware packing
with both original/exact-v1 policies. A separate direct official tokenizer call
counts each expected rendering; the driver does not import product code or open
SQLite. No model or provider service runs.

## Prepare and reproduce

Read the exact public product head in the dated result's `build.json`. Build it
in a clean anonymous checkout, not a later main:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-native-token ./cmd/mousa
```

Prepare an isolated local Python environment and vocabulary cache explicitly.
This step may download public packages/vocabulary; the captures themselves are
offline. Do not use an environment with provider credentials or private data.

```sh
python3 -m venv /tmp/mousa-token-runtime
/tmp/mousa-token-runtime/bin/python -m pip install 'tiktoken==0.12.0'
TIKTOKEN_CACHE_DIR=/tmp/mousa-token-cache /tmp/mousa-token-runtime/bin/python -c \
  'import tiktoken; print(tiktoken.get_encoding("o200k_base").name)'
```

From this repository, with the clean product checkout and recorded head:

```sh
/tmp/mousa-token-runtime/bin/python native-tokens/capture.py \
  --mousa /tmp/mousa-native-token \
  --product-source /tmp/mousa-token-product \
  --product-head PUBLIC_HEAD \
  --python /tmp/mousa-token-runtime/bin/python \
  --cache /tmp/mousa-token-cache \
  --output /tmp/mousa-token-reproduction
python3 tools/verify_results.py
```

Replace `PUBLIC_HEAD` with the exact recorded revision. `--output` must not exist.
Each run creates fresh stores; every command starts a new executable and reopens
its store. Raw command inputs, stdout, stderr and exits are saved before
assertions. The supplied executable's digest and declared build command are
recorded, not cryptographic proof of how that binary was built. Package version,
Python version, encoding and vocabulary hashes are retained; no runtime, cache,
database, executable or model is exported.

## What the driver checks

The three passages contain multilingual/combining Unicode, a tab, DEL, a trailing
LF and a literal special-token-looking string. Two passages are byte-equal but
have distinct item/segment identities. Exported normalized passage bytes must
match the fixture. Synthetic `[1,0]` vectors cover all initial passages; no
embedding inference or quality claim is involved.

The byte-only query selects all three. For each retrieval mode, original token
packing selects three with a 10000-token cap, while exact-v1 selects two unique
byte strings. The driver reconstructs headers and separators independently from
exported source/segment/content pins and the selected fixture bytes. It compares
the exact returned context, its UTF-8 digest and byte size, text-only released
bytes and full ordinary-text token IDs/count from official
`tiktoken==0.12.0`/`o200k_base`.

A second exact-v1 query caps context at the largest independently counted single
passage rendering. It selects one whole passage, not a truncated packet, and
fits the cap. This single-passage allowance is not used to sum a multi-passage
count: every returned multi-passage context is independently encoded as a whole.
A hybrid exact-boundary query also uses the full rendering's exact count.

Hybrid restart preserves its packet/context. Native history exposes the accepted
token release view and explicit retained-text recount succeeds. The corrected
view aligns `candidate_ids` with compact proposed-count facts (and lexical facts
in lexical mode); it is not the canonical v7 record. Replacing all items excludes
stale vectors from current hybrid selection without rewriting recorded facts.
Normal old history reports retired text unavailable; explicit recount refuses
rather than inventing original text. Fresh deny releases no context, candidates,
measured source count or hybrid coverage, and hides history.

Each run contains 48 native calls and 20 independently counted contexts. The
paired capture/reproduction use different fresh stores and directory roots;
source/segment/packet identities and header token costs can therefore differ.
Expected within-run relationships are asserted rather than treating those
volatile identities as cross-run goldens.

## Limits

These are finite native protocol/counting observations, not performance,
retrieval quality, semantic truth, authentication or answer-generation evidence.
The named encoding is not asserted to be the tokenizer of an unverified model.
Only the returned context is counted; arbitrary application, tool/JSON or final
model prompt framing is outside that guarantee. Reservations are caller
declarations, not authenticated model-window facts.

The capture does not repeat the product's process-fault, reservation/overflow,
writer-ordering or corruption suite. Historical counts remain recorded producer
evidence on ordinary reads; independent recount requires original retained bytes.
Mixed-ancestry lifecycle-rejected candidates are outside this fixture; it does
not establish that their aligned token-history facts are filtered.
Earlier consumer/vector/hybrid archives retain their exact producing pins.
The [corrected-head observations](../results/2026-10-22-native-tokens-corrected)
validate ordinary native compatibility after issue #85's projection correction.
The product's real SQLite regression establishes that internal mixed-source graph
case; this driver neither copies that harness nor adds public derivation ingress.
The [original observations](../results/2026-10-22-native-tokens) retain their
`50a1b43` pin and all capture bytes; they predate the correction.
The [final-pin observations](../results/2026-10-22-native-tokens-lifecycle-outcome)
target the subsequent issue #86 lifecycle-outcome correction while preserving
issue #85. Single-source captures do not prove the all-rejected ancestry outcome;
the product's graph and native serializer regressions establish it.
Startup study holds and failed historical observations are unchanged.
