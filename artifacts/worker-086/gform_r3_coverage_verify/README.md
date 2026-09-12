# W086-GFORM-R3-COVERAGE-VERIFY-01 — does the r3 coverage adjudication bind?

Worker `worker-086` · nodes `F1,F2a,F2b` · classes `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`
· gate `G-FORM` · read-only on every canonical path. Self-issued: no inbox card exists for this
worker slot; the target is the 01:19:18 `reviews/G-FORM-final-verify-r3.json` that REC-39 names and
that had no independent review.

## One-line result

At the live FROZEN rev29 pins, **all eight counted accepts in the r3 coverage table independently
re-bind** (verdict accept, full-schema true, hard_failures empty, declared hash = pin, non-author,
no strict same-target later flip) — but **the artifact does not carry the REC-39 minimum content**:
0/8 counted rows and 0/101 pin-bound verdicts have the seven-column per-file binding row
(`filename/reviewer/verdict/reviewed_sha256/verdict mtime/full-schema flag/independence basis`), and
there is no statement of which of the two divergent counts is correct and why the other is wrong.
Coverage also keeps moving at the same pins after the artifact's own `measured_at` (F2a gains one
full accept at 01:19:45). Verdict on the target: **revise**; the missing table is additive.

## Live pins (measured T0 and T1 of the run; 0 drift)

| path | sha256 |
|---|---|
| `reviews/G-FORM-final-verify-r3.json` (target) | `d94dd2d5b7784b29d2aebe4d8d47391f51d00790ae08fa0458eed5a8805ff657` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |

## Hypotheses (pre-registered in `PREREGISTRATION.json`)

| # | question | result |
|---|---|---|
| H1 | target-cited pins equal live bytes at T0/T1 | **true** (0/4 moved) |
| H2 | every counted accept binds at the live pin | **true** (8/8; verdict accept, `counts_as_full_schema_verdict=true`, `hard_failures=[]`, declared hash = pin) |
| H3 | no counted accept's reviewer is an author | **true** (reviewers `worker-072/075/017/018/090/071/052` vs `authored_by=astra-lead-formulation`, target author `astra-lead-audit`) |
| H4 | no counted accept is self-superseded by a later same-target revise | **true** (the one candidate, `w072-f2b-selfsupersede-review-20260912T011524`, declares `node_id=F2b` and voids only worker-072's F2b accept, which r3 already excludes; it does not void the F2a accept it merely cites) |
| H5 | REC-39 minimum content present | **PARTIAL** (see below) |

## H5 — the REC-39 gap (major finding `W086-R3V-REC39`)

REC-39 ruled that `astra-life05-verify-gform-r3` must publish *"filename / reviewer / verdict /
reviewed_sha256 / verdict mtime / full-schema flag / independence basis for every verdict at the
measured hash, state which count is correct and why the other is wrong, and re-measure coverage from
disk at use time."*

Measured on the artifact:

- counted rows with all seven columns: **0/8**; pin-bound verdicts with all seven: **0/101** (F1 0/27, F2a 0/21, F2b 0/53);
- columns present anywhere in the counted rows: `reviewer`, `verdict`, `created_at`, `full_schema`;
  absent: `filename`, per-row `reviewed_sha256`, `independence basis`;
- reconciliation vocabulary: `census` appears only inside `stable_since_census` / `"census-time bytes"`;
  `scan`, `CF-31`, `controller_gate_audit`, `which count`, `per-file` are all absent ⇒
  `reconciliation_statement = false`.

The artifact's `gate_result` reaches the right *direction* (`NOT proposable at rev29`) on named hard
findings, but the coverage half is exactly what the controller withheld G-FORM for (CF-31): a count
without a per-file binding row cannot be re-measured at use time.

## Coverage is still moving at the same pins (minor finding `W086-R3V-DRIFT`)

Windowed census under this instrument's declared rule (all pin-bound verdicts, `created_at <=
target.measured_at` vs all-time):

| node | full accepts as-of 01:18 | all-time | revises as-of | all-time |
|---|---|---|---|---|
| F1 | 2 | 2 | 13 | 16 |
| F2a | 3 | **4** | 10 | 13 |
| F2b | 3 | 3 | 39 | 44 |

The F2a fourth full accept is `w085-f2arev29-20260912T0119-review` (worker-085, 01:19:45) — one
minute after the target's `measured_at`. Target revise counts also differ from this census rule
(F1 12↔13, F2a 12↔10, F2b 37↔39); the rules differ and the artifact does not declare its counting
rule or per-row identity, which is why the divergence cannot be adjudicated from the artifact alone.

## Controls (all PASS; `run_valid: true`)

K1 target parses · K2 bound-hash mutant flagged · K3 `counts_as_full_schema_verdict=false` flagged ·
K4 non-empty `hard_failures` flagged · K5 verdict flip to revise flagged · K6 known revise
(`w072-f2b-selfsupersede-…`) not counted as accept · K7 two core runs identical digest
(`f9201a43ba25a77087208ee332c8bb885a899bf6fa82bad5549e4a1c77e1bd15`) · K8 all pins + target + map
re-measured after the run, 0 writes outside this directory / checkpoint / outbox.

## Falsifier

Any counted accept failing H2 at the live pin; an author-reviewer hit; a strict same-target later
flip by the accept's own reviewer; a target-cited pin ≠ measured live bytes; or an escaped K2–K6
mutant / K7 digest split. **H5 PARTIAL is a content finding, not a falsifier of this task.**

## Limitations

Worker evidence only — not a gate verdict, not a node status, not an adoption, no claim about schema
semantics. H3 is name equality, not a full authorship graph. H4's rule is declared-field strict:
a pin named only in another target's evidence does not void a verdict. Timestamps are normalized to
second precision, ignoring offsets. An unrecorded in-place edit of a review file under a fixed name
is out of reach of a read-only pass — that is precisely what CF-31 flags.

## Files

`PREREGISTRATION.json` · `verify_r3_coverage.py` (deterministic instrument) · `report.json` (full
measurement) · `SHA256SUMS` · checkpoint `runtime/state/worker-086_gform_r3_coverage_checkpoint.json`.
