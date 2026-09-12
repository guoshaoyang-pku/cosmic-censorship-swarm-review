# W084-C2C0-ESCAPE-MECHANISM-01 — mechanism adjudication of the FORM-HELDOUT-10 escape

**Task.** `W084-C2C0-ESCAPE-MECHANISM-01`, node A1, gate G-CLASSBIND, classes
`AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`.
**Question.** FORM-HELDOUT-10 reports `union_escape = 1.0` (0/26 caught) on its informative C2+C0
arms. Is each escape (a) **SILENT**: the stage's entire reported rule surface is byte-identical on
base and mutant, or (b) **OBSERVED**: the stage's output changes but the verdict stays accept?

**Answer (measured, valid=true).** All 26/26 informative-arm escapes are **SILENT in both frozen
stages**. On the pre-registered class-contract surface alone (20 mutants, 10 families) the strict
union escape is still **1.0, silent 20/20**. The escape is therefore *field-blindness at the
reported rule surface*, not a threshold or tolerance call that went the wrong way. This makes the
substance of FORM-HELDOUT-10 stronger, not weaker — but it does **not** lift its strict-H5
`valid=false`, which is a separate, pre-registered instrument defect (stage B R03 on the untouched
WCC canonical).

## Method (pre-registered before the first probe run)

- `PREREGISTRATION.json` `c695110cdfd7…` was written and hashed **before** any probe run;
  one append-only amendment `AMEND-1` (`PREREGISTRATION_AMENDMENT_1.json`, adding two omitted
  prefix keys, no method/control/decision change) was declared before the amended run. The v1 run
  is preserved under `v1/` with its `valid=false` (UNMAPPED) reason reported.
- For each of the 33 preserved mutants, both frozen stages were re-invoked as fresh subprocesses on
  the **preserved base** and on the **mutant**:
  - stage A `artifacts/formulation/tools/check_class_schema.py --json <f>` `000e09e46b2f`
  - stage B `artifacts/worker-06/spec_conformance_audit.py <f>` `c79d8ab8440a`
- Normalization deletes only volatile/path-bearing keys (stage A `schema`; stage B `audited_at`,
  `source`, `doc_sha256`); everything else — verdicts, failed rules, and every per-rule
  verdict+detail string — must match exactly.
- Classification per stage: `CAUGHT` (not accept/pass), `SILENT` (accept + identical normalized
  output), `OBSERVED` (accept + differing output).
- Contract relevance: a pre-registered longest-prefix block map over the recursive leaf diff of
  parsed base vs mutant. CONTRACT = what class is claimed / on what data; META = status, citation,
  self-guard or documentation text.

## Results

| aggregate | mutants | caught | escape-silent | escape-observed | union escape |
|---|---:|---:|---:|---:|---:|
| all 33 mutants | 33 | 7 | 26 | 0 | 0.7879 |
| informative C2+C0 arms | 26 | 0 | **26** | 0 | **1.0** |
| C2+C0, CONTRACT paths only (strict) | 20 | 0 | **20** | 0 | **1.0** |
| C2+C0, META paths only | 6 | 0 | 6 | 0 | 1.0 |

Per stage: stage A caught 0 / silent 26 / observed 0; stage B caught 0 / silent 26 / observed 0 on
the informative arms. The 7 catches in the full corpus are the W-arm mutants, all stage-B R03-only
(the pre-registered instrument defect), none informative.

Per family (all 13 informative families, 2 mutants each, all `escape_silent=2`):
`conclusion-content-erasure`, `conclusion-polarity-inversion`, `containment-reversal`,
`development-topology-weakened`, `end-structure-contradiction`, `equivalence-inflation`,
`extension-predicate-weakened`, `f0-binding-stale-hash`, `natural-language-inversion`,
`sobolev-threshold-lowered` are CONTRACT; `known-obstruction-erased`,
`schema-falsifier-erasure`, `source-status-flip` are META.

## Controls (all pass; the run is `valid=true`)

| control | result |
|---|---|
| K1 base acceptance | C2/C0 bases hash-equal live canonical pins and are accepted by both stages; W base rejects stage B on R03 (pre-registered) |
| K2 format control | comment-only copy of the C2 base: normalized output `identical` for both stages |
| K3 sensitivity positive | planted foreign `conclusion.conclusion_type`: both stages `differs`, both reject R11 — the differential can see a real violation |
| K4 determinism | C2 base run twice: identical normalized hashes both stages |
| K5 integrity | 49/49 fixture/pin/stage checks match the FORM-HELDOUT-10 manifest |
| K6 no drift | all pins and stage-tool hashes unchanged after the run |
| K7 raw-verdict agreement | 33/33 re-run verdicts equal `raw_verdicts.json` |
| K8 fail-closed | 0 UNMAPPED paths, 0 crashes, 0 undecidable classifications |

## What this does and does not say

- **Does:** the reported rule surfaces of both frozen stages are provably unresponsive to every
  informative-arm mutant, including all 20 mutants whose changed paths lie on the class-contract
  surface. Any repair must add *observation* of those fields to a stage, not merely tighten a
  threshold in a rule that already reads them.
- **Does not:** assign a rule repair, edit any canonical byte, change any verdict, set
  `status=done` / `validation_status=passed`, or issue a gate verdict. It does not lift
  FORM-HELDOUT-10's strict-H5 `valid=false` (R03) and does not certify an escape number for the
  gate; it certifies the *mechanism* of the escapes at the pinned bytes.
- **Independence:** AUTHOR-ADJACENT, declared. worker-084 built FORM-HELDOUT-10 in a previous
  instance; this is an author-side mechanism audit of preserved bytes, not a third-party audit.
  Every number is a fresh subprocess re-run and is re-runnable.

## Reproduce / falsify

```bash
cd <repo>
python3 artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py          # re-measure
python3 artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py --verify # reproduce stored raw
```

**Falsifier.** Any of: a K2/K3/K4 control failing; a re-run verdict disagreeing with
`raw_verdicts.json`; a live pin or stage-tool hash changing during the run; a claim of SILENT for a
mutant whose normalized stage output actually differs; UNMAPPED changed paths > 0; or the strict
contract-only escape rate reported without its per-mutant raw verdicts.

**Not claimed.** No node completion, no gate verdict, no theorem, no rule repair. Worker measurement
evidence only.
