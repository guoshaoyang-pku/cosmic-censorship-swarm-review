# W063-F2B-BIND-CHAIN-01 — F2b rev12 f0_binding chain audit

Bounded class-bound worker task taken from the live G-FORM criterion (no inbox card exists for
worker-063). One class only: **AF-SCC-C0-VAC-GEN** (node **F2b**, gate **G-FORM**), subject
`schemas/af_scc_c0_vacuum.yaml` at revision 12.

- Subject pin: `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6`
- Frozen manifest: `artifacts/formulation/FROZEN.json` revision 28, `2f358f6722d92062…`
- Instrument: `run_f2b_bind_chain_063.py`, `4d37f642377e63d8…` (frozen before measurement)
- Report: `report.json` (checks C01–C10, controls M1–M8, T0/T1 entry hashes)
- Review: `reviews/w063-f2b-rev12-bindchain.json`

## Verdict

**revise, score 3.0.** Two hash-bound hard failures block a clean accept at this hash; the
structure and pointers themselves are clean.

| check | hard | result | measured |
|---|---|---|---|
| C01 subject == FROZEN rev28 pin | yes | PASS | 55d0a1ea9bda |
| C02 strict parse / one revised_at / no future stamp | yes | PASS | 1 revised_at, 0 future |
| C03 declared F0 hash == measured F0 | yes | PASS | 0abb9ed8a961 |
| C04 canonical `class_contract_pointer` resolves (top-level key) | yes | PASS | `classes.AF-SCC-C0-VAC-GEN`, C0 axes |
| C05 supplement pointer resolves, separate field | yes | PASS | `class_contracts.AF-SCC-C0-VAC-GEN` |
| C06 consistency-evidence hash binding | yes | **FAIL** | declared `675a99d0d25b`; measured/pinned `9e335e9ba1bf` |
| C07 evidence records compared-tree hashes | no | **FAIL** | no input sha256 in the evidence JSON |
| C08 conclusion_type strict / alias / R11 | no | PASS (alias, R11) | strict off-list, alias-equivalent |
| C09 declared structural gate on canonical bytes | yes | PASS | verdict=pass, failed_rules=[] |
| C10 two-stage acceptance preflight | yes | **FAIL** | corpus base `1bb78ce9b357` vs current C0 `55d0a1ea9bda` |

Controls: **8/8** mutation controls moved their detectors. Drift during the window: **none**
(13 pinned inputs byte-identical at T0 and T1).

## The two hard failures

**HF-W063-01 (blocking).** `f0_binding.consistency_evidence_sha256` declares `675a99d0d25b…`,
but the file at the declared path measures and is pinned at `9e335e9ba1bf…`. The declared hash
exists on disk only as a worker-086 snapshot of a superseded evidence revision
(`artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json`). The schema's
own rule — refresh the binding and re-run the consistency check before any gate verdict —
is violated at the verdict hash. The same family-wide defect is independently on record for the
siblings (F2a: HF-034-F2A-3 / HF-069R-3; F1: HF-040-05); this report measures it inside F2b's
own bytes at F2b's own pin.

**HF-W063-02 (blocking-for-clean-accept).** `semantic_escape_rebased.json` binds
`base_sha256 = 1bb78ce9b357…` (rev11 C0) while the authoring C0 measures `55d0a1ea9bda…`
(rev12). The declared `run_acceptance.py` PREFLIGHT fails, so the two-stage acceptance criterion
cannot be reproduced at the current hash. Family-wide, and already reported for F2a as
HF-069R-2.

## Findings that are not hard failures

- **F-W063-C07 (major):** the consistency evidence records no sha256 of either compared tree, so
  even a refreshed pin stays content-unbound until the generator is changed.
- **F-W063-C08 (adjudication):** `conclusion_type = scc_c0_future_inextendibility` is off the
  strict F0 allow-list but alias-equivalent under the owner-declared `VOCAB_ALIASES.json` policy
  and exactly the `rule_spec` R11 value. The direction of the alias policy (F0 uses alias forms;
  the policy says aliases must not appear in new canonical artifacts) needs one owner
  adjudication note; this is recorded, not scored as a hard failure.

## Scope, independence, limitations

- Not a full semantic re-read: `counts_as_full_schema_verdict: false`. It therefore does **not**
  count as one of the two full-schema verdicts G-FORM requires; it establishes that a clean
  accept at this hash is blocked.
- Independent: worker-063 authored none of the reviewed artifacts or tools. The existing accept
  at this hash (`reviews/F2b-repair-verify-worker-098.json`, 4.5) did not test C06/C10; the two
  reviews are complementary.
- Limitations: single class, single hash, one measurement window (00:42:09 +08:00); read-only, no
  network; the C10 preflight logic was replicated from `run_acceptance.py` rather than executed,
  to avoid writing shared evidence.
- Instrument calibration (disclosed): a pre-freeze draft read `class_contract_pointer` from
  inside `f0_binding` and produced a false C04 FAIL; the key is top-level (line 29). The scoping
  and control M4 were repaired before the frozen run recorded here.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-063/f2b_bind_chain/run_f2b_bind_chain_063.py --json
```

## Authority

Worker artifact and verdict only. No canonical artifact was edited; no node status,
`validation_status`, or gate verdict was set. F2b/G-FORM disposition remains with
astra-lead-formulation and the controller.
