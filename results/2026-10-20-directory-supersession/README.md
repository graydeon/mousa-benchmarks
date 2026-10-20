# Directory supersession native observations — 2026-10-20

Two fresh-store runs passed the [bounded directory workflow](../../directory-supersession):
19 native subprocess invocations per run, all exit 0. A fresh CGo-free binary was
built from public [Mousa PR80](https://github.com/graydeon/mousa/pull/80) head
`f98bcb227075ba716b5b82324bcb19c3266e8007`, tree
`c2dec63f24dfd78b036f43cdd57462313b75c46a`, after that revision was published.
The product PR is not claimed merged or available on main.

Both runs observed unchanged default/false selection after explicit declaration and
activation. With the fixture's one-passage byte budget, opt-in suppressed the exact
predecessor and selected the rank-two survivor under
both packing policies. The v4 trail member matched each producing run's declaration,
activation and exact revision pins. After predecessor update/resync, the new revision
survived and historical inspection retained the producing consultation.

- `capture/`: first complete native capture, fixture/update text, product identity and
  resulting pins.
- `reproduction/`: second capture using a new directory identity and fresh store.
- `build.json`: actual fresh public-source build argv, environment, output and exit.
- `runner.json`: capture runner path and SHA-256 at observation time.
- `manifest.json`: existing archive-format member sizes and SHA-256 hashes.

Raw `commands.json` members include real argv, stdin, stdout, stderr and exit. Their
synthetic public `/tmp` identities were chosen before capture and were not rewritten.
No database or binary is included. See the workflow README for reproduction commands,
identity preparation, exact checks and limits. These observations demonstrate native
behavior only, not relevance, semantic truth, authentication, performance or
model-driven acceptance. Historical results and startup-study holds are unchanged.
