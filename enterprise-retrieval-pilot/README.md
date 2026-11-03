# EnterpriseRAG lexical pilot: preparation failed

**This is an executed preparation failure, not a completed retrieval-quality
comparison.** The frozen gold-enriched reduced corpus contains 500 documents and
4,970,133 normalized UTF-8 bytes. The protocol allows at most 4,194,304 bytes.
Preparation returned exit 2 in both independent-cache passes, before ingestion or
retrieval. All 20 enrolled questions remain in the population; every enterprise
arm is NOT RUN. Scores and packed coverage are unavailable, not zero.

[Results and per-question outcomes](../results/2026-11-03-enterprise-retrieval-pilot)
retain the fixed membership, original question lines, binary relevance labels,
physical mappings, failure receipts and source identities. No source documents,
product binaries, databases or downloaded dependencies are redistributed.

## Data and selection

[EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench) describes
a generated/simulated company, Redwood Inference, not private production company
data. The public [dataset card](https://huggingface.co/datasets/onyx-dot-app/EnterpriseRAG-Bench/blob/69916e31c68aa5963c00248fd7f0bc12d04fd235/README.md)
declares MIT. The [Git license](https://github.com/onyx-dot-app/EnterpriseRAG-Bench/blob/d36685e273713975ee20299bbf1ab64165575b3c/LICENSE)
is MIT, copyright 2026 DanswerAI, Inc.; its exact text is retained with the results.
Attribution: Yuhong Sun, Joachim Rahmfeld, Chris Weaver, Roshan Desai, Wenxi Huang,
and Mark H. Butler, *EnterpriseRAG-Bench: A RAG Benchmark for Company Internal
Knowledge* (2026), [arXiv:2605.05253](https://arxiv.org/abs/2605.05253).

The release `v1.0.0` is mutable. [protocol.json](protocol.json) pins the three
asset IDs, sizes, update timestamps, URLs and SHA256 digests, not just the tag.
The downloaded release questions match the raw questions at Git commit
`d36685e273713975ee20299bbf1ab64165575b3c` byte-for-byte. The two Confluence archives
contain 5,189 regular UTF-8 text members. Only these slices and questions were
fetched; no full corpus, large Parquet, model or reranker was downloaded.

Eligibility requires category `basic` or `semantic`, `source_types` exactly
`["confluence"]` and nonempty `expected_doc_ids`. The actual counts are 19 basic
and 15 semantic. Select 10 of each by ascending SHA256 of UTF-8
`mousa-enterprise-pilot-v1`, NUL, then question ID; ties use ID. Category order is
basic then semantic. All 500 question-line identities and eligibility decisions
are retained. Selected question lines include the original fields and exact bytes;
reference answers are retained as data but never used for generation or judging.

Each physical identity is `asset_filename:exact_member_path`; its adapter item ID
is `p_` plus the SHA256 of that UTF-8 identity. Raw logical IDs, source asset hash,
member raw hash and rendered hash remain separate. All 20 selected labels map to
exactly one physical document. No selected version ambiguity or missing evidence
was observed. Distinct physical versions would be retained, and a logical ID with
different raw hashes would make its question unscorable, without replacement.

Include every matching gold physical document, then hash-sort remaining physical
identities with the same salt and fill to 500. Freeze the entire membership before
checking the text bound. **This is a gold-enriched reduced corpus that removes most
full-benchmark distractors and will generally be easier than the official corpus.**
Its results must not be compared with 500-question/full-corpus or answer-quality
leaderboard scores. This attempt produced no retrieval scores at all.

Rendering uses the complete `.txt` body, which already begins with its title:
Go-compatible outer whitespace trimming, initial BOM removal, CRLF/CR folding to
LF, no other filtering or truncation. BEIR receives empty `title` and the complete
rendered `text`, avoiding a duplicated title. The adapter manifest retains the
original member/range, title and raw/rendered byte counts and hashes; original
bodies remain in the source-download cache. Archive members are read as data,
never executed or extracted. Traversal, links, duplicate member paths and
unsupported layouts are rejected; all reads have declared size bounds.

## Intended comparison and observed limits

The unchanged product evaluation seam is `cmd/beir` at
`db03c841c0491ac505be8289e08fa60f78eae738`, built with `CGO_ENABLED=0 GOAMD64=v1`.
The frozen plan names original/dedup expression policies, verified candidate
rankings, and traced engine packing at 1024/4096 bytes, with limit 100 and a
30-second query deadline. The whole measured pilot, including ingestion, is capped
at 30 minutes. Builds, dependency preparation and replay are outside query latency.
No enterprise index was created because the input failed preparation.

The independent control is standard-library SQLite FTS5 with
`unicode61 remove_diacritics 2`, one whole-document row per physical item,
OR-connected quoted ASCII alphanumeric query terms, ascending `bm25(search)`,
then ascending physical item ID for ties. Repeated document hits are collapsed to
the first occurrence before top-k cutoffs. This differs from Mousa's segmentation,
query preparation and candidate limit: it is a route comparison, not an
equal-feature causal ablation. Only its synthetic smoke was executed.

Candidate metrics are document Recall@10/100, binary-gain nDCG@10 and MRR@10.
Relevant IDs come only from the original expected labels and resolved physical
mapping. Unjudged documents consume rank positions but are not asserted to be
negative relevance labels. Binary nDCG uses gains 1, discount `1/log2(rank+1)` and
ideal top-10 positives. MRR is the first relevant reciprocal rank within 10.
Packed coverage is a separate fraction of gold documents appearing in actual
engine-selected context, not a substitute ranking or semantic support measure.
Legitimate empty retrieval scores zero; preparation/run failures do not.

The optional QMD arm was NOT RUN because global corpus preparation failed, not
because QMD installation was attempted and failed. Setup budget used: 0 seconds,
0 downloaded bytes; the existing comparison lockfile remains unchanged. There
were no benchmark inference/provider, embedding, generation, judge or paid API
calls. API usage/billing is 0; local CPU/electricity is not literally free.

## Reproduce the failure

Use Python 3 with standard-library SQLite FTS5 and a separate checkout of this
repository. Run from its root; use new owned output/cache directories. These
commands are for a preparation-failure reproduction, not a full benchmark runner:

```sh
python3 enterprise-retrieval-pilot/prepare.py download --cache /tmp/enterprise-source
python3 enterprise-retrieval-pilot/prepare.py prepare --cache /tmp/enterprise-source --out /tmp/preparation.json.gz
# Expected exit 2: preparation_bound_failure, exactly 4,970,133 normalized bytes.
python3 enterprise-retrieval-pilot/prepare.py verify --cache /tmp/enterprise-source --capture results/2026-11-03-enterprise-retrieval-pilot/preparation.json.gz
python3 tools/verify_results.py
```

The downloader enforces streaming sizes and digests. Three source assets total
24,202,130 bytes, below the 64 MiB compressed cap. Decompressed source text totals
51,191,526 bytes, below the 512 MiB cache cap. It never substitutes new content
when an asset pin fails. Keep a 30-minute outer process limit when reproducing
preparation; the recorded attempt used `timeout 1800s`.

For the separate tiny synthetic adapter smoke, build the exact anonymous product
checkout without editing it, then run:

```sh
CGO_ENABLED=0 GOAMD64=v1 go build -o /tmp/beir ./cmd/beir
# Run the following from this companion repository, not the product checkout.
python3 enterprise-retrieval-pilot/sanity.py --beir /tmp/beir --out /tmp/enterprise-sanity
python3 enterprise-retrieval-pilot/checks.py --capture results/2026-11-03-enterprise-retrieval-pilot/preparation.json.gz --sanity /tmp/enterprise-sanity --out /tmp/controls.json
```

The synthetic smoke has two documents and two queries. It exercises six Mousa
arms, native policy/mode/budget ranking comparisons and a real SQLite query;
checks the engine's oversized-passage omission and larger-budget selection; and
cross-checks metric aggregates against the binary's metric conventions.
Hand-computed fixtures independently test discounts, cutoffs, repeated-document
normalization, empty retrieval and rendering. Four controls rewrite archives and
recompute every outer/member hash before testing changed enrollment despite equal
counts, wrong logical/physical mapping, changed ranking and changed packed evidence.
The latter two are **synthetic controls only**, not enterprise retrieval checks.

At this product pin the native `-report coverage` command returns exit 1:
`traced run without pack coverage`. Its reports contain per-question coverage,
but no aggregate `pack_coverage`, which the helper requires. Both raw reports and
refusals are retained. The smoke explicitly records that refusal; it does not
repair the report, replace the packer or count the helper as passing. Product
source is unchanged. A future comparison needs independent triage of that helper
before relying on its coverage-curve output.

To inspect a lossless capture, import `prepare` from this directory and call
`prepare.wire.load_capture(path)`. The existing shared archive codec validates
all interned object-member hashes and stream bytes. `prepare.py verify` additionally
recomputes selection and mappings from pinned raw sources, so replacing a label or
question ID with equal counts is not accepted. Timing fields stay separate from
stable preparation facts. The result manifest registers every public file; no
historical result, dependency, lockfile, workflow or product source was changed.

## Interpretation

The largest observed loss stage is corpus preparation: all 20 questions are
blocked, before candidate retrieval or packing. There are no paired enterprise
quality/packing numbers and no evidence for changing a retrieval or packing policy.
The concrete next step is to reconcile the fixed 500-document enrollment with the
4 MiB limit in a separately approved, refrozen protocol. This report does not
choose a lower count, raise the cap or cherry-pick smaller documents. The pilot is
inconclusive about retrieval quality; reserve untouched data and a preregistered
comparison before making confirmatory claims. No general superiority, energy,
model-window, long-horizon memory or vendor-system-equivalence claim is made.
