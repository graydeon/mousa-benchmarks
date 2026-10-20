# Native directory supersession example

`capture.py` runs the built Mousa executable against two ordinary Markdown/text
files in a fresh temporary directory and SQLite store. It submits explicit existing
native declaration and activation records, without reading or modifying the database.
Python 3 is only the example driver; it is not a Mousa runtime dependency.

The [2026-10-20 capture and fresh-store reproduction](../results/2026-10-20-directory-supersession)
use public [Mousa PR80](https://github.com/graydeon/mousa/pull/80) head
`f98bcb227075ba716b5b82324bcb19c3266e8007`, tree
`c2dec63f24dfd78b036f43cdd57462313b75c46a`. The product PR is submitted,
not claimed merged or available on main.

## Reproduce

From this repository, with Git, Go 1.25 or newer and Python 3:

```sh
git clone https://github.com/graydeon/mousa.git /tmp/mousa-directory-reproduction-source
git -C /tmp/mousa-directory-reproduction-source checkout --detach f98bcb227075ba716b5b82324bcb19c3266e8007
(cd /tmp/mousa-directory-reproduction-source && GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-directory-reproduction ./cmd/mousa)
python3 directory-supersession/capture.py \
  --mousa /tmp/mousa-directory-reproduction \
  --product-source /tmp/mousa-directory-reproduction-source \
  --output /tmp/mousa-directory-reproduction-receipts
python3 tools/verify_results.py
```

Use absent output and checkout paths. The capture creates a deliberately public
`/tmp/mousa-public-directory-supersession-*` directory identity from the start,
keeps that path unchanged in raw output, and removes the temporary input/store after
capture. Each reproduction has a different absolute source path and therefore
different source, revision, declaration, activation and packet identities. Request,
decision and trail identities are also invocation-specific. Compare producing-run
relationships and observed behavior, not cross-run identity equality.

## Observed workflow

The files have equal synthetic text, `cedar directory evidence`, but distinct item
and representation identities. The caller explicitly declares that the first-ranked
baseline revision is replaced by the other revision; equal bytes do not infer that
relationship. Query evidence supplies both exact revision pins. Source preparation
uses the existing length-prefixed tuple encoding for the `mousa-local` namespace and
absolute directory path, not the separate `mousa-jsonl` namespace. The native
administration commands validate those identities and their stored ancestry, and
`supersession activation state` confirms the current source and selection. This
small preparation routine is not an independent correctness proof of the identity
codec or an identity-free administration builder.

The driver checks:

- No history and declaration alone preserve the default packet.
- After explicit activation, default and `--supersession=false` preserve the prior
  selection under both `original` and `exact-v1` packing.
- Opt-in with a one-passage byte budget withholds the exact first-ranked predecessor
  and lets the rank-two survivor fit. The v4 trail records the producing activation,
  declaration and both exact item/representation pins; its candidate membership
  agrees with the released evidence.
- Updating and resyncing the predecessor creates a different representation that the
  old pin does not suppress. A later subprocess inspecting the original trail keeps
  the producing consultation and reports the retired predecessor as no longer indexed.

Every native invocation records its actual argv, stdin, stdout, stderr and exit in
`commands.json`; the file is saved before evaluating that invocation. `inputs.json`
retains initial and update text, `product.json` records source/tree and binary digest,
and `summary.json` records the producing pins after the checks pass. The public
absolute temporary paths are part of the source identity, not redacted or rewritten
output. Do not use private directory names for a public capture.

## Limits

This is one synthetic native capability demonstration and one independent fresh-store
reproduction, not relevance, semantic truth, authentication, performance, model-window
or model-driven acceptance evidence. The capture does not prove concurrent snapshot
ordering or corrupt-store transaction rollback; those remain product regressions.
The shared archive verifier checks retained file membership, sizes and hashes, not
runtime semantics. Reproduction runs the executable and the bounded behavior checks.
No databases, binaries, model calls, remote inference or startup-study measurements
are exported. Association-plus-supersession and MCP administration remain unsupported;
semantic/hybrid retrieval and core token-aware packing remain future capabilities.
