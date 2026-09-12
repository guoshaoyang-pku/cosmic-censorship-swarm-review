# W044-GFORM-ACCEPT-SCOPE-AUDIT-01

Bounded class-bound worker task taken by `worker-044` (no inbox card existed for slot 044).
Classes **AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN** (F1 / F2a / F2b); gate
**G-FORM**. Read-only on every canonical path; writes only under this directory and
`runtime/state/`.

## Question

The live G-FORM coverage measurement counts "effective independent full-schema accept
clusters" per class (worker-087 `W087-GFORM-INDEP-04/r2`, `summary.json` sha256
`c12aa690c619`, `accepts_current` F1=6 / F2a=3 / F2b=1) and the controller's pass-06 table
records F1=4 / F2a=3 / F2b=0. Reviewers themselves qualify the gate criterion as "blind
full-schema" accepts. **Does each counted accept record declare full-schema coverage, or does
it declare a restricted scope that the counted-set harvest did not read?** Recount under the
pre-registered rule in `PREREGISTRATION.json` and report the corrected accept sets.

## Method

`scope_audit.py` (stdlib only, deterministic, fail-closed on pin drift) harvests every
review-typed accept record bound to the live pins from **both** channels — `reviews/*.json`
and `comms/outbox/*.jsonl` — classifies its declared coverage under the pre-registered
limitation / explicit-full / off-gate / non-schema-meta rules, clusters by reviewer, and
recounts per class. Ten controls (K1–K11) are shipped and were run before the measurement;
`python3 scope_audit.py --selftest` runs them alone.

Pre-registered rule plus four amendments made before the final run and disclosed in
`PREREGISTRATION.json` (`amendments`): A1 negation guard (a pilot run had misclassified
worker-011's explicit "NOT a full-schema verdict" as full-schema), A2 non-schema meta
exclusion, A3 off-gate exclusion, A4 post-hoc secondary observation declared as post-hoc.
Pilot outputs are preserved (`pilot_report.json`, `pilot_stdout.txt`).

## Result at the snapshot (pins: F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`,
FROZEN rev29 `815e08079aef`; no pin drift during the run)

| class | permissive | strict (explicit full-schema) | scope-disqualified | non-schema meta |
|---|---|---|---|---|
| F1 AF-WCC-VAC-GEN | 7 | **4** — worker-038, 052, 072, 075 | worker-011 (repair-scope, "NOT a full-schema verdict") | worker-082, worker-16 |
| F2a AF-SCC-C2-VAC-GEN | 4 | **3** — worker-017, 018, 072 | — | worker-082 |
| F2b AF-SCC-C0-VAC-GEN | 4 | **2** — worker-071, 090 | worker-061 (variant-CH axis only) | worker-082, worker-16 |

1. **Scope correction (pre-registered).** The F2b cluster counted by the live coverage
   measurement is worker-061's 00:54:27 verdict, whose own text reads: *"SCOPED: this verdict
   covers ONLY the variant-CH strictness axis on the CH record … not the full schema; the
   blind full-schema F2b round remains the binding coverage."* Under any reading it cannot be
   counted as a full-schema accept. F1 likewise loses worker-011's "visibility/strictness
   repair scope" accept, which declares itself *not* a full-schema verdict. worker-082's
   F1/F2a/F2b "A1 cross-target independence census" records and worker-16's G-AUDIT
   convergence-checklist closures are off-gate / non-schema and are excluded from G-FORM
   counting (they remain listed).
2. **The F2b count moved during the measurement window.** worker-071 (01:10:40), worker-090
   (01:08:56) and worker-072 (01:10:13) emitted accept verdicts bound to `b2ab6acb2bbe`;
   071 and 090 set `counts_as_full_schema_verdict=true`. worker-087's F2b=1 is therefore
   stale, and the pass-06 F2b=0 is superseded by traffic. Any gate arithmetic must cite the
   snapshot hash, not a revision label.
3. **Post-hoc secondary (declared amendment A4, observational): F2b accept–defect conflict.** At
   this same pin, 32 revise/reject records from 18 distinct reviewers name the
   `implication_ledger` / `forbidden_transfers` / containment axis; the two strict accepts
   name it nowhere in their own text (worker-071's 26/26 check list contains no
   forbidden-transfers direction check; worker-090's findings concern vocabulary aliases and
   Kerr topology). A count of accepts that never test the axis on which an independent revise
   wave records hard failures cannot dispose of those failures. **The r3 verifier
   (`astra-life05-verify-gform-r3`) must adjudicate accept-vs-defect at one hash; the
   criterion is not mechanically decidable by counting.**

Verdict string: `SCOPE_CORRECTIONS_FOUND+F2B_ACCEPT_DEFECT_CONFLICT`; verdict digest
`e46c255c4b1cb8f43ee987c8d63052249b8c8bc05954f872599bebb2cd568770`; 10/10 controls.

## Falsifier

Falsified if (a) any record classified SCOPED is shown to declare full-schema coverage
elsewhere in its own record, or a record counted strict is shown to carry a hard coverage
limitation the rule missed; (b) any live class pin differs from the recorded pin at end of run
(drift voids live applicability, not the snapshot measurement); (c) any control K1–K11 fails to
classify as pre-registered (K5's expectation was updated by amendment A2, disclosed);
(d) re-running `scope_audit.py` on the same snapshot yields a different verdict digest;
(e) a hash-bound accept at a live pin from a reviewer not in the harvested set is shown to
exist in either channel; (f) the F2b conflict is dissolved by exhibiting a strict accept whose
own text disposes of the containment hard failures.

## Non-claims / credit

Not a schema review, not a gate verdict, no node transition, no `validation_status=passed`, no
canonical write. The independence/dedup axes of worker-087's coverage ledger are taken as
given and not re-adjudicated; this task refines only the scope axis plus the declared post-hoc
observation. Credit: worker-087 (coverage ledger), worker-061/071/090/072/016/082 (records
classified), worker-097/018/017/034/053/066/075 and the other revise-wave reviewers (defect
axis), worker-052 and worker-075 (concurrent coverage traffic).

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-044/gform_accept_scope/scope_audit.py --selftest   # controls only
python3 artifacts/worker-044/gform_accept_scope/scope_audit.py              # report.json + stdout.txt
```
