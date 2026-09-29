# Declared-association context retrieval

A caller preparing the fixed SQLite backup checklist could not retrieve the
connection-context qualification with the initial `backup` query: the
qualification is documented in the separate `context.rst` excerpt, which shares
no term with the query, so it is absent from the lexical candidate set. This
result directory records a bounded product comparison of Mousa's established
retrieval against the new opt-in declared-association behavior on the same
frozen case set, same corpus, same budgets and same store configuration.

This is development evidence from fixed cases, not held-out evaluation,
assessor accuracy, or a general answerability or completeness claim.

## Correction (2026-09-17)

The first version of this directory described all six proposed cases as running
with the declaration file. The stored record only ever held the default path for
those six cases plus one declaration-enabled follow-up query, and the summary
table presented the default-path numbers as the proposed outcome. The two
misread rows were `complete` (3,397 bytes presented as the proposed result) and
`absent` / `absence_followup` (2,163 bytes presented as the proposed result);
with the declaration those cases release 3,970 bytes.

`raw/comparison.json` is the superseded record, preserved unchanged with its
original bytes. `raw/responses/`, `raw/commands.json` and
`raw/comparison-arms.json` are the corrected record:
`run.py` recorded three arms per case and `analyze.py` derived every number in
this document from those responses, failing if an arm labelled
declaration-enabled carries no association stage, if the default-path arms
disagree, or if a declaration displaced primary evidence.

## Mechanism under comparison

The caller supplies an author-declared relationship file
(`raw/declarations.json`, schema `mousa.association_declarations.v1`) whose
`from_item` is the procedure item and whose `to_item` is the item holding the
required qualification. Mousa honors a declaration only when the declaring item
contributed selected primary evidence; the target's current active passages are
then packed into the remaining byte budget after primary evidence, one
accounted row each, each hit carrying its own segment identity, byte
coordinates, content digest and the declaration's `from_item`/`to_item`/
`basis`/`author`. Depth is one, at most four distinct targets are applied per
query, at most 256 target passages are considered, and non-deliveries (unknown
or inactive target, fan-out cap, consideration bound, budget, duplicate) are
recorded as omissions. The stored trail records the complete association stage
under `mousa.source_trail.v3`.

The declaration is an input, not discovery. Its author and basis stay attached
to every released passage. A relationship is not an access grant: resolution
stays inside the one allowed source decision and only reaches the current
active revision of the target.

## Fixed method

- Product: same repository and corpus as
  [2026-09-17-backup-decision](../2026-09-17-backup-decision). Six frozen
  cases and budgets from `cases.json`, unchanged, with the declaration file
  above.
- Arms, each with its own fresh store over one prepared corpus directory:
  `before-default` (the pre-change binary without declarations),
  `after-default` (the post-change binary without declarations) and
  `after-declared` (the post-change binary with the declaration file). The
  declaration-enabled follow-up query is recorded as a fourth arm where the case
  defines one.
- `raw/commands.json` records every invocation, both binary hashes, the corpus,
  case and declaration hashes, and the corpus paths used.
- Packet identities bind the absolute corpus path. A rerun under a different
  path produces the same bytes, evidence and outcomes under different
  identities; the paths used here are recorded, while the superseded record's
  paths were not, so its packet identities cannot be reproduced even though its
  released bytes and passages can.

## Results

| Case (budget) | default before | default after | declared after | added bytes | associated passages |
|---|---|---|---|---|---|
| complete (8192) | 3,397 | 3,397 | 3,970 | +573 | 4 released, 3 duplicates of lexical hits |
| partial (180) | 0 | 0 | 0 | 0 | none (no primary passage selected) |
| followup (4096) | 2,163 | 2,163 | 3,970 | +1,807 | 7 released |
| absent (4096) | 2,163 | 2,163 | 3,970 | +1,807 | 7 released |
| absence_followup (4096) | 2,163 | 2,163 | 3,970 | +1,807 | 7 released |
| budget (1) | 0 | 0 | 0 | 0 | none (no primary passage selected) |

The two default-path arms agree on packet identity, released bytes, outcome and
the identity, coordinates, digest, rank and score of every released passage for
all six cases. The newer binary explicitly labels those hits `origin: "lexical"`;
the older binary omits that additive field.

With the declaration, `followup` releases all seven `context.rst` passages
(1,807 associated bytes), including the statement that the connection context
manager neither opens a transaction nor closes the connection. Each associated hit
carries `origin: "association"` and the declaration provenance. In `complete`
the query itself names the connection context, so three of the seven passages
were already released as lexical hits and are recorded as duplicate omissions
rather than released twice.

`absent` and `absence_followup` ask for a completion deadline that is absent
from both excerpts. The declaration still fires, because `backup.rst`
contributed selected primary evidence, and adds the same 1,807 closure bytes.
Those bytes cannot answer the deadline question; they are accounted, attributable
and inside the budget, and whether they are useful is the caller's judgment, not
an engine claim. Item-granularity declarations apply to every query in which the
declaring item contributes evidence, and this record shows that cost.

## Required-fact and qualification coverage

- Qualification coverage for the demonstrated `followup` case: 0/1 before,
  1/1 after the declaration is supplied, without a caller-authored follow-up
  query. The fixed follow-up query `context manager neither closes connection`
  is recorded separately as the fourth arm.
- `complete` already released the qualification note without the declaration,
  because its query names the connection context.
- Primary displacement: none. The default-path released passages appear in the
  declaration-enabled arm with identical items, coordinates and digests;
  `analyze.py` asserts this for every case.
- Released bytes and omissions: added bytes equal the sum of the associated
  passages' byte lengths; no associated passage was released outside the
  remaining budget, and small budgets omit with explicit reasons.

## Costs

Whole-consumer cost of the proposed path is the unassociated query plus
declaration decode and the declared target reads inside the same transaction.
The comparison run used fresh stores and one repetition per case, and its
timings are not reported here. The separately recorded
[bounds study](../2026-09-17-associated-bounds) measures that path with
repetitions on the same worker host: cost follows the number of target passages
considered (which is bounded per query) rather than the bytes that fit the
budget, and the earlier claim that the mechanism adds no additional queries is
withdrawn.

## Limits

- One development corpus, one declaration, fixed cases. No held-out claim, no
  assessor-accuracy claim.
- The negative cases (irrelevant declaration never fires; stale/deleted target
  omitted with a reason; self-references and duplicates rejected) are covered by
  product regression tests in the Mousa repository, not re-measured here.
- The 180-byte partial-context miss from the previous report remains a
  budget-omission result and is not evidence for or against association.
- Shared worker host: latency is descriptive, not a dedicated-host benchmark.
