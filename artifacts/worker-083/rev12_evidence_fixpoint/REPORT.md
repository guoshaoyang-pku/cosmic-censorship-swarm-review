# W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01 — does the pinned closure evidence bind the frozen rev12 bytes?

**Worker:** `worker-083` (bounded execution worker; no assignment card existed for this slot)
**Node / gate / classes:** `F0,F1,F2a,F2b` / `G-FORM` closure evidence (input to `G-F0`) / `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`
**Task taken:** the standing `G-FORM` requirement that closure/thereom evidence be *hash-bound* — narrowed to the one machine-decidable question nobody had measured: at the FROZEN rev28 pins, does the closure record `close_findings_rev27_report.json` (and the procedure that produced it) actually bind the frozen rev12 bytes?
**Status of deliverable:** measured artifact + 7 controls, all passing. **No gate verdict, no node status, no validation_status, no edit to any canonical or frozen artifact.**
**Reproduce:** `python3 check_rev12_evidence_fixpoint.py --write` (exit 0 iff every control passes; read-only unless `--write`).

---

## 1. Result

Four questions, answered at the FROZEN rev28 pins (`artifacts/formulation/FROZEN.json#2f358f6722d9`, revision 28, 44 declared files):

| # | question | measured | answer |
|---|---|---|---|
| Q1 | does FROZEN rev28 match disk? | 44/44 pins match, 0 drift | **YES** |
| Q2 | does the pinned closure evidence bind the frozen rev12 bytes? | 7 of 8 declared post-write hashes are intermediates that match neither the frozen pins nor disk | **NO** |
| Q3 | is the closure reproducible from the pinned (evidence, tool, bytes) triple? | the pinned tool exits 1 with `ASSERT FAIL [F0 scalar-sph conclusion]` in dry-run at the frozen bytes | **NO** |
| Q4 | is the frozen outcome nevertheless bound elsewhere? | `gate_test_report.json#6def01264a1d` (pinned, disk-matching) contains all three frozen schema hashes; FROZEN rev28 pins them directly | **YES** |

So this is a **stage-2 evidence-binding defect, not a schema-content defect**: the rev12 bytes are frozen and independently bound, but the *record and procedure that claim to have produced them* are stale and not re-runnable against those bytes.

## 2. The defect in one table

`artifacts/formulation/evidence/close_findings_rev27_report.json` (pin `dab1d49b9985`, on disk unchanged) declares these post-write hashes:

| report entry | report declares | FROZEN rev28 pin | disk now | class |
|---|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | `0abb9ed8a961` | `0abb9ed8a961` | MATCHES_PIN |
| `schemas/af_wcc_vacuum.yaml` | `b474fbc49cdd` | `cce9c60146d6` | `cce9c60146d6` | **STALE_INTERMEDIATE** |
| `schemas/af_scc_c2_vacuum.yaml` | `a7ccae4d5dec` | `5476a3f2c6bc` | `5476a3f2c6bc` | **STALE_INTERMEDIATE** |
| `schemas/af_scc_c0_vacuum.yaml` | `b71ec02c601d` | `55d0a1ea9bda` | `55d0a1ea9bda` | **STALE_INTERMEDIATE** |
| `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | `b474fbc49cdd` | `cce9c60146d6` | `cce9c60146d6` | **STALE_INTERMEDIATE** |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `a7ccae4d5dec` | `5476a3f2c6bc` | `5476a3f2c6bc` | **STALE_INTERMEDIATE** |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `b71ec02c601d` | `55d0a1ea9bda` | `55d0a1ea9bda` | **STALE_INTERMEDIATE** |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `f3c119a8825d` | `9e335e9ba1bf` | `9e335e9ba1bf` | **STALE_INTERMEDIATE** |

Three of the stale entries (the canonical schemas) declare **`revision: 12`** — the same declared revision as the frozen bytes, with different bytes. So the same declared revision spans at least two byte strings (report's intermediate, frozen final), and the report is the only pinned artifact that describes what rev12 changed.

## 3. Why the intermediates cannot be recovered

- **No archived copy exists.** All 12,570 scannable files under the workspace were hashed (cap 4 MiB): **0** files hash to any of `b474fbc4…`, `a7ccae4d…`, `b71ec02c…`, `f3c119a8…`. The intermediate bytes are gone; only their hashes survive as text in the pinned report.
- **No revision delta records the second write.** No `*_delta` in FROZEN rev28 mentions the intermediate hashes or a schema byte change between the report write (`00:31:41`) and the schema mtimes (`00:32:02`). rev27/rev28 deltas describe the closure and the re-pin, not a post-report rewrite.
- **The pinned tool is one-shot.** `close_findings_rev27.py#0234cd3c` (pinned, disk-matching) asserts the pre-closure F0 scalar-class wording; at the frozen rev5 taxonomy that pattern is gone, so the run fails closed before emitting anything. The 5 audited canonical inputs were hashed before and after the run: unchanged (read-only control C5).

## 4. Consequence and suggested remedy (for the gate owner, not applied here)

A reviewer who follows the lead's own evidence chain (`astra-lead-formulation` status `lead-form-20260912T003626-00` cites this report as the evidence for the F1 rev12 publication) reaches hashes that exist nowhere. The repair narrative cannot be re-derived from the pinned evidence+tool+bytes triple.

Minimum fix, one measure-only addendum owned by the formulation lead (no frozen byte change):
1. re-emit the closure record as a new addendum file that states the **frozen** post-closure hashes (`cce9c60146d6`, `5476a3f2c6bc`, `55d0a1ea9bda`, `9e335e9ba1bf`) and marks the four intermediate values as unrecoverable intermediates;
2. state explicitly that `close_findings_rev27.py` is a one-shot migration script and is **not** a verifier at the frozen revision, so reviewers must not run it as one;
3. reviewers cite the addendum + `gate_test_report.json`, not the stale table.

## 5. Controls (7/7 pass)

| id | control | result |
|---|---|---|
| C1 | a synthetic report whose declared hashes all equal the pins yields 0 stale | pass |
| C2 | a synthetic report with one mutated hash is flagged (1 stale) | pass |
| C3 | a synthetic FROZEN with one wrong pin is detected by the pin sweep | pass |
| C4 | determinism: two independent builds give the same canonical digest `237863c8ff25` | pass |
| C5 | the tool dry-run wrote nothing to the five audited canonical inputs | pass |
| C6 | the audited report's measured hash equals its FROZEN pin (`dab1d49b9985`) | pass |
| C7 | no archived file hashes to an intermediate value | pass |

## 6. Falsifiers

- **F1 (binding):** exhibit a FROZEN revision (≤28) whose closure report cites the frozen post-closure hashes for the schemas and `taxonomy_consistency`; or an archived file whose bytes hash to one of the four intermediates and which is the canonical rev12 artifact → Q2 would flip to YES.
- **F2 (reproducibility):** show `close_findings_rev27.py --dry-run` exiting 0 with `changed: false` on every audited path at the frozen bytes → Q3 would flip to YES.
- **F3 (moving target):** any canonical byte change voids this measurement; re-run and compare `canonical_digest_sha256 237863c8ff25` (covers every input hash, the per-entry classification, the tool transcript and the cross-binding map, not wall clock).
- **F4 (scope):** exhibit a pinned artifact, other than `gate_test_report.json`, that already binds the frozen rev12 hashes in the form reviewers are told to use → the consequence narrows (Q4 was already YES).

## 7. Not claimed

No gate verdict (`G-FORM`/`G-F0` stay pending), no node status, no `validation_status`, no class-id change, no claim that the frozen pins or the rev12 schema content are wrong, and no mathematics or physics claim. The finding is advisory to the gate owner; the remedy is deliberately not applied, because the audited report is itself a frozen (pinned) artifact and editing it would breach FROZEN rev28.

## 8. Pins

| role | path | sha256 |
|---|---|---|
| manifest | `artifacts/formulation/FROZEN.json` | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` |
| closure record | `artifacts/formulation/evidence/close_findings_rev27_report.json` | `dab1d49b9985416504239154fa8af0ec94147ee4ebae0cd7732001ccead69972` |
| closure procedure | `artifacts/formulation/tools/close_findings_rev27.py` | `0234cd3cbda491ae353e4972dda8a8fe95ae39d2fe2b4968639dc2fcad845371` |
| F1 rev12 | `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| F2a rev12 | `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| F2b rev12 | `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| F0 rev5 | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| cross-binding | `artifacts/formulation/evidence/gate_test_report.json` | `6def01264a1dcbced0f698e951d1b200ffe35abfae01b184673c59741f364894` |
