# Public evidence contract for the startup study

**PROPOSED / NOT IMPLEMENTED / NOT RATIFIED.** This document addresses
[issue #39](https://github.com/graydeon/mousa-benchmarks/issues/39); it does not
resolve it. Public export remains disabled. No new capture, protocol amendment,
capacity result or performance acceptance follows from this proposal.

## Recommendation and review boundary

Use a controlled, public-safe **future execution**, not a redacted historical
capture, for exact public trial evidence. Propose one new scoped contract,
`mousa.startup.public_evidence.v2`, with exact trial, host, build and correctness
bytes and a deterministic preparation record that omits preparation monitor
history. This hybrid addresses two different problems: execution controls reduce
privacy exposure; an explicit preparation scope removes a large class of evidence
from public acceptance. Neither solves archive feasibility by itself.

The proposed acceptance statement is: **public replay verifies the recorded
fixture construction inputs, outputs, state continuity and final fixture gates,
and verifies complete recorded trial/host/phase consistency; it does not verify
preparation monitoring or prove that the recorded execution happened.** Preparation
polling, cancellation, resource accounting and reuse provenance remain locally
reviewed, operator-attested facts. Their omission is a real reduction from v1,
not another encoding of complete evidence. Reviewers must accept that reduction
explicitly or reject v2. Until then, v1 remains authoritative and export refuses.

Do not apply v2 to the retained historical smoke. Its unsafe raw dependencies
cannot support the exact public claims above. A historical projection could be a
labelled diagnostic report, but would not qualify for this contract, complete
replay or collection acceptance. Do not build a general historical redactor.

The alternative is controlled future execution with **all** v1 evidence public.
That preserves the preparation-monitor claim, but requires an independently
reviewed storage/publication decision: existing complete evidence does not fit.
A derived-only historical format is smaller in scope of implementation, but
cannot verify withheld output, host or preparation assertions and therefore does
not satisfy the original complete-public-replay requirement. Hash inventories do
not bridge that gap. The recommended hybrid retains exact evidence where trial
claims depend on it, while isolating one proposed, reviewable claim reduction.

## Existing contract and source map

The accepted protocol is [protocol.json](protocol.json), SHA-256
`72fc39d6e8f46466ff39293f6246a44cd0409ba467b405046d2d23026f0169b2`, accepted
at [PR31](https://github.com/graydeon/mousa-benchmarks/pull/31), commit
`b45f720f9d0164b9dabfd5714a3cda32fa07073d`. Its historical proposal labels do
not change that acceptance. Its bytes remain unchanged. A future v2 amendment
must be a separate reviewed document with its own identity, never a replacement
of those bytes. Product commit remains `ff80838c607ab8cde5b89376b9a9f44c1deb13cf`,
tree `5c18c9d14248c693759f20c93d47d84da98b691f` unless separately amended.

Current producers and consumers are [prepare.py](prepare.py),
[run.py](run.py), [common.py](common.py), [analyze.py](analyze.py) and
[controls.py](controls.py). The field inventory below describes those actual
records; v2 names and behavior are proposals, not existing APIs.

- `prepare.execute` checks a clean product commit/tree, builds, records modules
  and build-info, invokes native preparation and freezes coherent seeds.
  `source_records` derives synthetic inputs; `fixture_gate` validates schema,
  source ancestry, declaration/event bytes and projections, rooted chains, final
  activation state, v4 decisions/candidates and suppression dispositions.
- `run.child` records exact streams, wait4 resources, timestamps and monitor
  events. `run.capture` binds schedule, host sampling and final seed/accounting
  checks; `run.smoke` records a separate unmeasured 40-call plan.
- `common.Objects` stores raw objects or losslessly reconstructed logical
  snapshots. A `{sha256,bytes}` reference binds reconstructed bytes, not merely a
  snapshot recipe. `snapshot` retains all user schema, column metadata and typed
  sorted rows. `pack`/`unpack` check transport membership, not truth of execution.
- `analyze.check_preparation` replays preparation inputs/outputs and state
  continuity; `check_entry` validates fixture, command, output and invariance;
  `check_monitor`, `check_host` and `check_phase` replay timing/resource/coverage
  relationships. `verify_controls` regenerates mutations and checks native
  control receipts. `pack_evidence` currently refuses unconditionally.

A current verifier sometimes only resolves a field's bytes (for example
`binary_buildinfo`), rather than interpreting or auditing their contents. The
proposal adds explicit public-safety and identity checks; it must not describe
those as current guarantees. The shared result verifier remains a separate
byte-integrity gate, not a semantic, privacy or performance verifier.

## Field contract

**E** means exact public bytes from an audited future capture. **D** means
explicitly derived public data with its transformation specified below. **L**
means local-only unchanged originals. An E requirement that cannot be met blocks
public release; it does not silently become D or L. Structured source fields
retain their original JSON types; equality uses canonical JSON, not Python's
boolean/integer equality. Exact output comparisons still compare raw bytes.

The last column states the public verification limit, even when all proposed
members are present. A digest of withheld data is a binding only for someone who
has the bytes; it is not public replay, proof of execution or proof of privacy.

| Actual fields or members; producer → consumer | Proposed public bytes and reason | Public assertion supported | Not independently checkable |
|---|---|---|---|
| `preparation.product_commit`, `product_tree`, `protocol_sha256`, `accepted_protocol_commit`; `capture.protocol_sha256`, `runner_commit`, `runner_tree`; `prepare.execute`/`run.capture` → `verify` | E identities, exact protocol and capture-time `sources` tool bytes; public repository revision/tree checked against independently obtained source | Pinned public source/tree/protocol and actual archived tool bytes agree; capture identity is distinct from publication/merge identity | Historical execution of those bytes, or clean checkout merely from a receipt; smoke lacks measured runner commit fields and must not acquire invented ones |
| `preparation.binary_identity` (`bytes`,`sha256`); seed copy/build comparison → `verify_prepared`, controls | E recorded executable identity and audited `binary_buildinfo`; executable remains L under existing no-binary-publication rule | Receipts consistently name one executable; independent rebuild can compare identity if reproducible | Recomputing executable digest from archive alone, or proving which executable ran; rebuilding is a separate check, not replay |
| `build_receipts['build.json']`: `argv`, `environment`, `exit`, `stdout_hex`, `stderr_hex`; `module-verification.json`: `exit`, `stdout_hex`, `stderr_hex`; `prepare.execute` → `check_preparation` | E future effective build values and exact decoded output bytes, including empty streams; no substitution of roles for paths | Build target/flags, exit and environment binding, raw output identity; v2 checks full declared command/cwd binding | Successful build/module execution solely from self-recorded exit/output; current build receipt has no cwd field, so future capture must add an exact public build cwd |
| `go_version`, `build_environment`, `module_files['go.mod'/'go.sum']`, `module_list`, `binary_buildinfo`, `python`, `sqlite`; `prepare.execute` → `check_preparation` | E complete public toolchain/module/build bytes, including build-info's first executable-path line; audited allowlisted versions/settings | Independent parsing of build settings, module consistency and target; full effective environment is visible | Cached dependency integrity or binary provenance from version strings alone; public module retrieval/rebuild needed separately |
| `preparation_start_ns`, `preparation_end_ns`, `peak_observed_workspace_bytes`, `new_native_invocations`, `not_run`; `prepare.execute` | D copied values in scoped preparation record; L original envelope | Preparation interval, reported peak and counts are labelled reported, not trial samples | Peak usage, preparation stopping rules or complete accounting without monitor observations; no measured startup inference |
| `fixtures[].key,S,E,T,counts,declarations,logical,physical,seed_identity,seed_path,derivation`; `source_records`/`fixture_gate` → `verify`, `_check_entry_binding` | E synthetic inputs and all logical state bytes; D public record rebinds logical references to public objects. `seed_path` E only for fixed public relative seed layout; L database files | Recompute schema/counts, source/content/representation identities, per-source chains, tip, v4 candidate/decision projections and exact suppression, and bind trial before-state to fixture | Seed physical hashes cannot be recomputed without L database files; coherent backup/checkpoint and native origin remain execution attestations |
| `preparation_invocations[]` rows: `phase,ordinal,command,before,after,before_physical,after_physical`; `prepare.invoke` → `check_preparation` | D one ordered scoped row per original invocation; E exact argv/cwd/environment, `stdin_hex`,`stdout_hex`,`stderr_hex`, their hashes, exit/signal and logical before/after bytes; retain no-history null reset state | Regenerate full expected native call sequence from S/E/T and compare exact payloads, canonical outputs, expected not-found errors and state continuity; final gates use all tables, not summary booleans | Full original compressed receipt equality and preparation monitor correctness; arbitrary query/sync extra output cannot be dropped just because current verifier selects a subset |
| Preparation `command.monitor`, PID/timing/resource/censor fields from `run.child`; → `check_monitor(control=True)` today | L complete original command and gzipped invocation, including every poll/deadline/storage event; D scoped row retains only exit/signal and a labelled local-review outcome, not a replacement monitor | Public correctness replay can reject bad inputs/output/exit or broken state continuity; local review outcome is explicitly attested | Preparation wait mechanism, cadence, exact-child reaping, CPU/RSS, cancellation/termination delays, workspace budget enforcement and readiness behavior; **v2 must not run v1 `check_monitor` against this row** |
| `reused_prefix` (`preparation,invocations,native_invocations,logical,unreused_invocations,original_failure`), fixture reuse `derivation`; `import_prefix` → `check_preparation` | L historical reuse graph. Initial v2 eligibility forbids reused prefixes entirely, including cross-version reuse; fresh future preparation only | No hidden historical dependency for a qualifying v2 preparation | Existing reused native origin/failures cannot become fresh v2 evidence; historical records stay readable locally, not rewritten |
| `schedule.json`, `schedule_sha256`, scheduled entries' `ordinal,phase,round,fixture,S,E,T,operation,order_key,order_sha256,argv,stdin_sha256,seed_identity,expected_output_sha256`; `run.schedule` → `verify` | E full expanded schedule with every listed key; smoke entries have a separate smaller schema, not invented schedule fields | Recompute deterministic 80/400 order, exact schedule keys, arguments, input and output expectations, attempted prefix and NOT RUN suffix | Execution order beyond recorded consistency; schedule digest alone is insufficient |
| `pidfd_preflight`, support `kind,product_invocations,command`, optional `error_class`; `preflight_execution` → `check_support` | E future API probe receipt and complete command object, explicitly zero product invocations; interpreter argv and error text must pass public audit | Replay binds empty probe streams, control phase, exact environment, mechanism and ≤1ms polls; missing support prevents eligible execution | API availability merely from receipt text, or treating interpreter-probe timing as product performance |
| Trial/smoke/control command `argv,cwd,environment,phase,pid,start_utc,end_utc,start_ns,end_ns,wall_ns,command_deadline_ns,phase_deadline_ns,exit,exit_code,signal,user_seconds,system_seconds,rss_kib` | E complete future `run.child` object → `check_entry`, `check_monitor`, `check_phase`; no time rebasing, PID anonymization or path rewriting | Recompute wall endpoints, typed exit/signal, per-child resource units and bindings; distinguish warmups/smoke/controls from measured entries | Actual clock/resource truth or causal attribution; RSS is not Go allocation count or process-tree memory |
| Trial `censor_reason,censor_event_ns,detected_ns,detection_delay_ns,termination_grace_ns,termination_delay_ns,deadline_overshoot_ns,descendants`; `run.child` → `check_monitor`, `failure_kind` | E all values, including null, zero and failures | Earliest recorded deadline, signal grace, censor classification, delay and failure coverage; descendants invalidate success | Undetected descendants or events outside captured observation; a censored value is not a completed latency |
| Trial `monitor.mechanism,wait4_calls,pidfd,pidfd_target_pid,wait4_pid,wait4_options,readiness_ns,reap_ns,polls,deadlines,storage,signals,interruptions`; optional `host_event,post_reap_cancel,invalid_reason` | E every original monitor event and nested field; `run.child` → `check_monitor`; `polls` retain `start_ns,end_ns,requested_ms,ready,events,overshoot_ns`, deadlines retain `edge,at_ns,command_due,phase_due`, storage retains `at_ns,bytes` plus due/delay when present | Recompute exact-child identity, single reap, requested ≤1ms cadence, readiness priority, two deadline checks per poll, 100ms storage cadence and recorded overshoot | Completeness/truth of kernel observations beyond receipts; no hard real-time guarantee |
| Entry `before,after,before_physical,after_physical`; `seed_after[].identity,physical,logical`; `snapshot`/`physical` → `check_invariance`, `verify` | E all logical schema/typed rows and lossless object dependencies; E recorded physical `{main,-wal,-shm,-journal}` identities or null; L actual SQLite/sidecar files | Recompute logical/canonical/schema equality; compare recorded main-file identities for get and seed immutability; allow status physical-only differences; retain reader sidecars | Rehashing actual physical files without their bytes; physical invariance remains comparison of recorded identities, not independently inspected file bytes |
| Logical `schema,application_id,user_version,tables.*.columns,rows,count,sha256`; trie `.ref` (`bytes,snapshot`), recipe `header,tables`, table `metadata,rows`, leaves `rows` or `children` | E exact reconstructed canonical bytes and every storage dependency; `Objects.get` → `validate_snapshot`, `fixture_gate` | Recompute sorted typed row/table digests, duplicate row retention, schema/column identities and fixture invariants | SQL integrity/foreign-key execution merely from snapshots; arbitrary text/blob hex may disclose information and must be audited, never scrubbed |
| `host.platform,cpuinfo,python,sqlite,cpu_count,filesystem,governors,mounts`; `run.capture` | E future full raw values, filesystem numeric fields and exact public mount/device/governor names; unknown/unavailable values explicit | Parse recorded platform/resources and public environment context | Exclusive host ownership, physical-host identity or native-host acceptance; Linux platform strings themselves may expose host names |
| Host samples `at_ns,utc,counters` (`stat,loadavg,meminfo,pressure/cpu,pressure/io`), `cgroup_membership,cgroups`, `process_inventory` | E full future raw counters/membership and hierarchy keys; `host_sample` → `idle_interval`, `new_throttling`, `concurrent_processes`, `check_host` | Recompute CPU busy/steal, MemAvailable and recorded pressure/throttle deltas using original values; process names retained because detector depends on them | Unobserved host workloads; missing counters cannot be invented as zero. Raw mountinfo is used to resolve cgroups but is not itself retained by current `host_sample`; future provenance must retain the public resolver input |
| `cgroups.*.{cpu.stat,cpu.pressure,io.pressure,memory.max,memory.high,cpu.max,io.max}`, optional `unresolved`; inventory `owner_pid,ancestors,processes,inaccessible`, process `pid,ppid,comm,cpu_ticks,start_ticks,state` | E all future names, values and explicit null/missing records; no hash or ordinal substitution for cgroup/process names | Recompute current detector with same ancestry, process-name predicates and cgroup keys | Private historical hierarchy/process names cannot be projected into an equivalent exact host claim; unresolved hierarchy is not complete resource provenance |
| Host `idle_samples,idle_passed,samples,sampler`; sample `sequence,terminal,kind,requested_interval_ns,sampling_start_ns,sampling_end_ns,sampling_overhead_ns,boottime_offset_interval_ns,contention,new_throttling,concurrent_workload,suspension,collector_stopped,window_start_ns` | E raw sampler JSONL, parsed fields and derived flags retained exactly; `start_sampler`/`finish_sampler` → `check_host` | Independently recompute flags, frame order/error offsets, one-second cadence, terminal/phase coverage and suspension indicators | Host activity between samples or truth beyond receipts; sampler overhead remains included/recorded, not subtracted |
| Sampler `pid,start_ns,shutdown_ns,end_ns,signals,polls,wait4_calls,interruptions,reaped,exit,user_seconds,system_seconds,rss_kib,raw,failure,samples,frame_error`; `measured_phase_start_ns,measured_phase_deadline_ns,measured_phase_end_ns,warmup_start_ns,warmup_end_ns,phase_storage,stop_before_spawn` when present; host `sampler_source` | E complete raw cleanup/frame/failure objects and phase accounting → `check_host`, `check_phase`; final checks remain inside sampler/phase lifetime; `phase_storage` retains `phase,stage,bytes,at_ns` | Recompute lifetime/command coverage, exact 1800-second phase deadline and partial finalization; native future controls must establish producer behavior | Merely accepting metadata does not independently prove correct cleanup; unknown extra exception fields block publication |
| All `stdin_hex,stdout_hex,stderr_hex` and `*_sha256`; raw build/module streams, capture `failure`, smoke failure `class,message`, sampler failure `reason`, control exception text | E future raw bytes/text only after schema and content audit; L unsafe historical bytes. Hex/gzip/embedded JSON are decoded before audit | Exact declaration bytes; strict typed status JSON; expected errors/failure classification and raw stream bindings | An error category or parsed subset cannot certify withheld raw-output equality; no assertion that arbitrary output is generally private-information-free |
| `kind,data_class,collection,stop_reason,remainder,smoke_remainder,failure`; `run.capture`/`smoke` → `verify` | E all attempted failures, explicit remaining NOT RUN entries and original unmeasured/synthetic labels | Replay coverage and fail-stop classification without promoting smoke/synthetic data to timings | An archive can be valid evidence of failure, not a successful study; replay-valid and study-successful are separate results |
| Controls `baseline`, `control-fixture.json`, `mutations.json`, `forbidden-write.json`, `main-file-write.json`, `reader-sidecars.json`, `native-controls.json`, wrapper references and analysis inputs | E actual control receipts, source, false conditions and deterministic mutation specifications; `verify_controls` regenerates copies from public baseline | Recompute expected detector after coherent rehashing; inspect real write/schema/censor controls separately from synthetic mutations | Mutation controls do not detect arbitrary coordinated fabrication or establish production rollback; synthetic inputs remain explicitly synthetic |
| Archive member `name,bytes,sha256`; source `sources` keys, error/inventory names and descriptor graph; `common.pack`/`unpack` | E v2 fixed public paths and exact size/hash manifest; D private provenance inventory uses public ordinal IDs only; L original names/path mappings and full original inventory | Recompute public transport integrity and complete public dependency closure | Withheld historical member names/bytes are not publicly replayable; even an inventory can disclose paths. Syntax-safe relative names are not automatically privacy-safe |

No unlisted field is implicitly public. Before implementation, turn this inventory
and the frozen producer key sets into closed schemas for each record kind,
including optional/error branches. Expanded scheduled entries include `round` and
order fields; smoke entries do not. Audit source keys, nested
JSON names, table metadata, hex text/blob values, compressed receipts and exception
messages. Free text requires review against the capture's public synthetic
allowlist, not a search for a few known private prefixes. Unknown schemas, fields,
encodings, unaudited streams or opaque payloads block export of the whole attempt.

## Controlled execution and derivation rules

Future capture needs a dedicated environment containing only public synthetic
inputs and approved public operational metadata. Fix public absolute build,
cache, toolchain, source, home and temporary paths **before execution**. Record
those actual values, the exact build cwd, complete environment and command, not
post-hoc path roles. Disable ambient environment inheritance. Verify source and
modules at the pinned versions without network during preparation/measurement.

Audit binary build-info, tool/module diagnostics, all process names, kernel/CPU
text, mount/device names, cgroup membership and every ancestor limit/pressure
stream. A public scratch root does not constrain any of these by itself. A private
or unresolved dependency refuses eligibility; do not mask it or fabricate an empty
counter. Retain missing optional counters explicitly, and reject missing required
ones. Isolation may limit visibility, so describe the visible environment without
claiming exclusive physical-host ownership. Host controls must preserve the actual
scope of CPU, memory and process/cgroup visibility; a namespace is not evidence of
host-wide isolation.

Use existing canonical JSON (UTF-8, sorted keys, compact separators, no nonfinite
numbers); new public JSON records add one LF. Preserve exact stream bytes,
including whitespace/newlines, separately within their E command records. Decode
hex only once under the closed schema, reject noncanonical/invalid hex, duplicate
JSON keys, wrong types, unsafe names, links and expansion/dependency cycles. Do
not normalize native output, arbitrary paths or errors. Privacy audit can refuse
publication; it cannot turn a failed or unsafe attempt into a successful one.
Full local evidence remains unchanged on every refusal.

The only scoped preparation transform is a fixed selection, not a configurable
redactor. In original ordinal order, copy `phase,ordinal,before,after,
before_physical,after_physical` and from `command` copy
`argv,cwd,environment,phase,stdin_hex,stdout_hex,stderr_hex,stdin_sha256,
stdout_sha256,stderr_sha256,exit,exit_code,signal`. Resolve and republish all exact
logical objects. Reject missing correctness fields. Do not include any other
command field. Record `representation: derived-preparation-correctness`,
`monitor_acceptance: operator-attested-only` in each public scoped envelope.
Recompute public references after transformation. The original command objects,
compressed receipts and monitor histories stay L; they are not public dependencies.
Any copied output is still exact output, but the scoped envelope is not an exact
copy of its original receipt. Do not give it the original receipt's hash.

Publish `provenance.json` with fixed public ordinal IDs, original byte lengths and
hashes only after those metadata are audited, the transform source identity,
input/output format identities, per-field E/D/L classification and fixed omission
reason codes. Never publish original path-bearing member names to claim a
complete inventory. The public mapping asserts which private originals were used;
without those bytes, its authenticity and correct derivation are operator-attested.
A reviewer with local originals can recompute the selection byte for byte. A
public-only reviewer can recompute public correctness gates, not the withheld-to-
public transformation. Private marker controls must cover inventory metadata too.

## Version, member layout and replay

v1 is the existing accepted complete-evidence contract. It has no new implicit
projection mode. Leave its protocol, reader and historical originals unchanged;
use the original source revision for source-bound historical replay. Keep old
failure and size/privacy labels visible. A v2 reader dispatches on an explicit
format identifier; absent/old identifiers select only the legacy reader, never
v2 fallback. An old reader must refuse v2, not interpret scoped rows as v1.
An unknown version refuses. No migration silently upgrades a failed v1 capture.

A proposed v2 result directory has exactly the following public layout. Angle
brackets describe constrained names, not literal filenames. All members are
regular files; no extra path is allowed.

| Public location | Contents and identity |
|---|---|
| `README.md` | Scope, limitations, attempted/success/censored/NOT RUN coverage, replay instructions and separate operator attestations |
| `protocol.json`, `publication-amendment.json`, `pins.json` | Exact accepted v1 protocol; separately ratified v2 requirements; product/runner/toolchain/binary identities and source pins |
| `capture.tar.gz`, `capture.tar.gz.members.json` | Package and sorted `{name,bytes,sha256}` manifest for every expanded member below; package size/hash recorded by outer manifest |
| `manifest.json` | Sorted size/hash inventory for every other outer file, excluding itself to avoid self-reference; publication commit/tree recorded separately after capture |
| `coverage.csv`, `samples.csv`, `fixtures.csv`, `summary.csv`, `observations.svg`, `resources.svg` | Recomputed outputs only; incomplete/censored/smoke labels retained; no synthetic performance claims |
| Inside package: `public.json` | Closed v2 envelope: `format`, `amendment_sha256`, `pins`, `capture`, `preparation`, `provenance`, `controls`; references use `{sha256,bytes}` |
| Inside package: `schedule.json`, `provenance.json`, `attestations.json` | Exact schedule; audited derivation inventory; fixed claim IDs and values for operator-attested execution/build/physical/preparation-monitor facts, never verifier PASS booleans |
| Inside package: `sources/<name>` | Exact frozen producer/verifier/control/transform/schema source; names drawn from an explicit source allowlist, identities bound in `pins` |
| Inside package: `objects/<64-lowercase-hex-sha256>` or `objects/<digest>.ref` | Exact trial/host/build/control/logical bytes or scoped preparation envelopes; existing lossless row-trie representation with full reachable closure and no ambiguous raw-plus-descriptor identity |

`public.json` references a v2 capture object and a scoped preparation object,
not an unchanged v1 `capture.json`. They retain the E capture/build/fixture fields
above; the only replacement is the D preparation invocation list and its scoped
metadata. This avoids accidentally feeding derived rows to v1 deep replay. Control
records and baseline references use the same object store; every required member
must be reachable from declared roots or explicitly listed as retained failure
evidence. Conversely every reference must resolve locally in the public package.
No private-file fetch, network fallback or private path mapping is permitted.
Ratification must freeze closed schemas and the exact allowlisted source filenames
before implementation; this document is not an executable schema.

Proposed public-only replay, in order:

1. Check package/member/outer manifest size limits and identities before bounded
   extraction. Reject duplicate, absolute/traversing, link, sparse, extension or
   unknown members. Enforce expanded workspace, per-member and graph-depth limits.
2. Dispatch version; verify amendment hash, protocol hash and externally expected
   product/tree/runner/source identities. A self-rehashed identity is not a trusted
   pin. Separate capture-time source, build, publication and merge identities.
3. Resolve every public dependency; verify raw/reconstructed byte lengths and
   hashes; validate closed schemas and representation tags. Missing dependencies
   are errors, not attested substitutes. Do not require any L original.
4. Regenerate preparation expected calls from public synthetic inputs. Compare
   raw argv/stdin/outputs/exits, full logical state continuity and fixture gates.
   Emit `preparation-correctness: recomputed` and
   `preparation-monitoring: not-publicly-replayable`, never complete-preparation
   PASS. Compare reported physical identities but label them as recorded facts.
5. Regenerate schedule; require exact attempted prefix and explicit NOT RUN
   remainder. Run unchanged trial output/logical/physical rules, monitor rules,
   host/phase/finalization rules on E evidence. Recompute all flags/summaries;
   reject `passed` booleans as authority. No lowering the ten-second deadline,
   1,800-second phase cap, one-second sampler cadence or resource limits.
6. Regenerate coherent rehashed mutation controls from public baselines and exact
   source specifications. Require the expected semantic detector, not merely a
   stale member hash. Compare native controls separately; controls cannot create
   historical native acceptance. Produce separate archive-integrity,
   public-replay, attestation-dependency and study-outcome results.

Changed acceptance claims versus v1 are exhaustive for this proposal:

- Preparation monitor/resource/cancellation/reuse replay is removed from public
  acceptance; fresh-only scoped preparation replaces full invocation receipts.
  Public correctness still requires every input/output and full logical state.
- Original preparation receipt names/bytes are not public. An audited derived
  inventory and operator attestation replace public original-member replay for
  those objects. Public inventory completeness means **v2 public closure**, not
  completeness of the local original archive.
- Public safety becomes a future-capture eligibility gate across all fields,
  not a claim inferred from relative native argv. This can refuse a capture that
  otherwise passes v1 semantic replay. Historical unsafe captures are ineligible.
- No other evidence reduction is authorized: trial/host/build/raw errors remain
  exact; logical snapshots retain every table/row; physical files and executable
  remain local with identities as in v1. Those existing identity-only limitations
  are not repaired or strengthened into proof of physical bytes/execution.
- Existing transport caps remain unchanged pending a separate decision. v2 does
  not claim complete-v1 replay or claim that it fits those caps.

## Archive feasibility and minimum evidence

Existing measurements, all tied to historical source
`adaab659998d6ff8b7b0b27c082cfe6b9efdb6ed`:

| Measurement | Bytes |
|---|---:|
| Complete retained archive | 329,622,720 |
| Frozen compressed cap | 4,194,304 |
| Object bytes, 31,909 members | 369,849,510 |
| Conservative preparation closure, 31,682 members | 344,971,872 |
| Gzipped preparation receipts | 308,367,185 |
| Decoded preparation receipts | 2,949,722,000 |
| Canonical preparation monitor payload | 2,937,140,016 |
| Bounded experiment: original 12 gzipped receipts | 1,407,199 |
| Bounded experiment: joint stream, excluding length index | 1,407,822 |
| Bounded experiment: additional length index | 101 |

The lossless experiment reconstructed original gzip bytes but saved nothing.
Only one 12,756-byte object lies outside the conservative capture closure;
pruning it cannot solve the overflow. Preparation closure overlaps other evidence,
so subtracting its size is not a prediction of a trial-only package. The retained
40-call smoke is not the future 480-entry schedule. No v2 archive-size measurement
exists. No new compression trial, capture or giant-archive regeneration is
proposed as part of this documentation revision.

Minimum evidence depends on the claim:

| Claim | Minimum public facts | Proposed scope |
|---|---|---|
| Fixture logical correctness and recorded native construction continuity | Every preparation input/argv/output/exit, reset boundary, complete before/after typed state, schema and final fixture identities | Retain E correctness bytes in D scoped rows; native origin/build truth remain attested |
| Preparation monitor compliance and budget/cancellation behavior | Every original monitor event, endpoints/resource/termination observations, complete reuse/failure graph | L; **not certified by v2 public replay** |
| Recorded trial cost/censoring and scheduling consistency | Every warmup/trial command, raw output, full monitor, wait4 resources, pre/post logical states, recorded physical identities, frozen schedule and failure suffix | E; no summaries-only substitute |
| Host/phase consistency | Raw idle/periodic/terminal frames, counters, full cgroup/process context, sampler cleanup, final seed/accounting interval | E; no path-redacted host summary substitute |
| Complete v1 public replay | All v1 raw dependencies including preparation monitors | Incompatible with measured archive and current cap; not satisfied by proposed v2 |

Reviewers must choose separately whether to accept scoped preparation claims or
require complete public preparation monitoring. If complete evidence remains
required, publication is blocked until a separately reviewed protocol/storage
decision supplies a feasible complete layout and measured size. Neither increasing
the cap, splitting into cap-sized pieces, removing fields nor changing capture
cadence is implicitly authorized. If the scoped proposal is ratified, its first
future package must still demonstrate all current caps, patch/blob limits and
combined workspace budget. Overflow preserves originals and refuses publication;
there is no automatic fallback to fewer fields or more favorable observations.

## Implementation checklist and acceptance matrix

Implementation requires a new bounded authorization after ratification:

1. Freeze v2 claim set, amendment identity, closed schemas, fresh-only eligibility,
   exact public member/source allowlists, privacy audit and attestation fields.
2. Implement controlled public build/host provenance and fixed preparation
   selection; preserve local originals before any transform/refusal. Keep v1
   paths/readers and the default export refusal until the whole new gate passes.
3. Implement bounded v2 packaging and separate public-only replay, external pin
   checks, graph/schema/privacy gates and explicit result labels.
4. Implement deterministic rehashed controls and behavioral cases below; check
   full public replay in an environment without private originals or network.
5. Under separate authorization, run fresh native acceptance at the reviewed
   public implementation revision; measure actual complete v2 package/patch/blob
   sizes. Review unresolved timeout, archive and privacy outcomes before any
   collection authorization. Do not promote synthetic tests to native acceptance.

Every case below is **NOT RUN**. Documentation consistency checking is not a pass
for any of these future behavioral or performance cases.

| Future acceptance case | Required result |
|---|---|
| Private markers in nested keys/values, hex UTF-8/blob rows, gzip receipts, embedded JSON, raw stderr/stdout, build-info, environment, member names and error/inventory text | Refuse public eligibility before export; retain originals unchanged. Literal-prefix scanning alone must not pass |
| Unknown fields, optional exception branches, unknown schema/version/encoding or unaudited raw stream | Fail closed; no drop-and-continue or opaque payload escape |
| Public replay with private originals removed and network unavailable | Recompute all declared public claims from package only; report preparation-monitor and execution attestations as non-recomputed, not missing-dependency PASS |
| Changed product commit/tree/protocol/executable identity, runner/helper/transform/build-info/module/build environment or source member | Reject against external expected pins and full binding checks; changing both reference and member must not bypass expected identity |
| Coherent rehashed mutations of outputs, status types, fixture S/E/T/chain/tip, logical state, monitor/censor/host/finalization metadata, schedule prefix/order/remainder | Expected semantic detector rejects even when all dependent hashes/manifests are updated; harmless status JSON key order passes, declaration byte change rejects |
| Missing object, row-trie leaf, source, preparation correctness state, sampler raw frame, failure or control dependency; cycles/expansion abuse/extra members | Refuse incomplete or unsafe public closure; no private lookup or summary fallback |
| Derived row labelled exact, old hash assigned to transformed row, original inventory name leaked, projection supplied as full preparation | Reject representation/identity/claim mismatch; exact streams remain byte-equal, D envelope is separately hashed |
| Public correctness data intact but preparation monitor withheld | Only ratified scoped result passes; complete v1/preparation-monitor acceptance explicitly unavailable |
| Archive/member/manifest/patch/blob/combined storage overflow | Refuse, preserve full local originals and failed packaging evidence; no pruning, silent split or cap increase |
| Historical 39/40 native smoke with final status timeout, unsafe provenance and oversized archive | Remains original-source failed/censored/local evidence; cannot become successful or eligible by transforming or relabelling it |
| Old v1 complete, failed, reused-prefix and source-bound records | Legacy reader remains available at original source; retained failures/limits labelled; no v2 fallback or rewritten original |
| Fresh native producer acceptance after implementation | Exact pins and 20 valid fixtures, fresh unmeasured 40-call smoke, ordinary/mutation/native cancellation/write/schema/sidecar controls; real sampler finalization across success/failure/interruption and cap boundaries; no collection implied |

## Decisions requiring ratification and retained holds

Review must explicitly decide: whether scoped preparation monitoring is acceptable
at all; whether future exact host/build/raw provenance can meet the privacy gate
without misrepresenting host visibility; the v2 schemas/layout/derivation and
attestation vocabulary; legacy dispatch/failure labels; and a feasible publication
policy if evidence still exceeds the cap. An unreviewed identifier or a useful
field inventory is not ratification. If the original complete claim is required,
reject the scoped contract rather than describe unavailable bytes as replayable.

After implementation, independent review and fresh native acceptance at the final
public source are still required. New native work needs separate authorization.
The retained smoke remains **39/40**, with final `s8-e257-t1` status censored at the
unchanged ten-second command deadline. The **329,622,720-byte archive hold**
remains. Neither is settled by this design. Historical observations remain tied
to their original source, not the eventual documentation or implementation commit.
No warmups, measured collection, timing, retrieval-quality, semantic,
authentication or native-host claim is made.

The [existing startup study context](README.md#question-and-evidence-boundary)
credits the distinct packing, rejected history-scan and 16,384-document startup
studies. This proposal introduces no new empirical result and does not pool their
measurements or claim their findings establish this contract's feasibility.
