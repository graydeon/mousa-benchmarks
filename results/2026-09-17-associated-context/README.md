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
query, and non-deliveries (unknown or inactive target, fan-out cap, budget,
duplicate) are recorded as omissions. The stored trail records the complete
association stage under `mousa.source_trail.v3`.

The declaration is an input, not discovery. Its author and basis stay attached
to every released passage. A relationship is not an access grant: resolution
stays inside the one allowed source decision and only reaches the current
active revision of the target.

## Fixed method

- Product: same repository and corpus as
  [2026-09-17-backup-decision](../2026-09-17-backup-decision). Six frozen
  cases and budgets from `cases.json` are unchanged.
- Baseline: retrieval without `--associations`, captured before the association
  change. Proposed: the same queries with the declaration file above.
- Case set, budgets and declarations were fixed before any comparison run.
- The demonstrated development case is `followup` (query `backup`, 4096 bytes).
  The `partial` (180 bytes) and `budget` (1 byte) cases remain predeclared
  budget-omission observations; the association mechanism does not fire when no
  primary passage is selected, so they are unchanged by construction and by
  measurement.

## Results

| Case (budget) | Baseline outcome | Proposed outcome | Released bytes baseline → proposed | New items released |
|---|---|---|---|---|
| complete (8192) | evidence | evidence | 3,397 → 3,397 | none (selection identical) |
| partial (180) | budget_omitted | budget_omitted | 0 → 0 | none |
| followup (4096) | evidence, no qualification | evidence, 7 associated passages incl. the qualification | 2,163 → 3,970 | `context.rst` via declaration |
| absent (4096) | evidence | evidence | 2,163 → 2,163 | none |
| absence_followup (4096) | evidence | evidence | 2,163 → 2,163 | none |
| budget (1) | budget_omitted | budget_omitted | 0 → 0 | none |

`followup` with the declaration releases all seven `context.rst` passages
(1,807 associated bytes) including the note that the connection context manager
neither opens a transaction nor closes the connection. Each associated hit
carries `origin: "association"` and the declaration provenance; the packet
identity, trail identity and used-byte accounting bind the added bytes. The
follow-up query `context manager neither closes connection` with the
declaration returns `context.rst` content directly (`raw/followup-query-associated.json`).

The caller-authored judgment that the returned note supports the closure
requirement remains a caller judgment, recorded as such; the engine adds no
semantic-support claim.

## Required-fact and qualification coverage

- Qualification coverage without a caller-authored follow-up query: 0/1 before
  (closure partial on the initial packet), 1/1 after the declaration is supplied
  for the demonstrated case.
- No caller-authored follow-up was needed in the proposed run; the baseline run
  required the fixed follow-up to reach the same note.
- Unrelated added context: the association releases the target item's passages
  in document order. In this corpus, 1,807 associated bytes include the note
  (about 300 bytes) plus the surrounding connection-context section. The rubric
  records this as the declared cost of item-granularity association: the caller
  reviews the whole declared target, and every associated byte is separately
  attributable and accounted.
- Displacement of previously useful evidence: none. Primary evidence is packed
  first under the existing policy and keeps its exact selection; associated
  passages only use the remaining budget. Measured: identical primary selection
  and packet bytes for all four unchanged cases, and identical `backup.rst`
  passages for the associated run.
- Released bytes and omissions: 1,807 additional accounted bytes in the
  demonstrated case; no budget omissions at 4,096 bytes. Small-budget cases
  omit with explicit reasons and unchanged accounting.

## Costs

Whole-consumer cost of the proposed path is the unassociated query plus
declaration-file decode and at most four target-item reads inside the same
transaction. No additional queries, stores, passes or network access are
involved. The comparison run used fresh stores and one repetition per case;
timings are not reported because the host is shared and the mechanism adds no
separate execution step worth measuring in isolation.

## Limits

- One development corpus, one declaration, fixed cases. No held-out claim.
- The negative cases (irrelevant declaration never fires; stale/deleted target
  omitted with a reason; self-references and duplicates rejected) are covered by
  product regression tests in the Mousa repository, not re-measured here.
- The 180-byte partial-context miss from the previous report remains a
  budget-omission result and is not evidence for or against association.
