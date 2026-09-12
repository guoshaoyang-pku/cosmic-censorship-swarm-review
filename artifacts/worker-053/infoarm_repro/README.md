# W053-GCLASSBIND-INFOARM-REPRO-01 — third-party reproduction of the held-out informative-arm escape

**Worker:** worker-053 · **Node:** A1 · **Gate:** G-CLASSBIND · **Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-VAC-GEN`
**Status:** worker measurement complete; **no** gate verdict, **no** node transition, **no** canonical write.
**Verdict:** `REPRODUCED_INFORMATIVE_ARM_ESCAPE_1.0` (7/7 controls pass, 0 pin drift).

## Why this task

No assignment card existed in `comms/inbox/worker-053.jsonl` (relaunched slot). Self-taken from
the live G-CLASSBIND queue. `lead-formulation-lifecycle-08` (`measurement_8`, evidence
`artifacts/formulation/evidence/lead_formulation_lifecycle_08_independent_verify.json`) records
the informative C2+C0 union escape **1.0** (0/24 and 0/26) as the substantive G-CLASSBIND
blocker and states that the R03 binder defect is *not* its cause. `worker-084` re-ran its own
corpus (`artifacts/heldout/heldout-10/verify/`), but the lead records that as process-level
independence only ("the verifier shares the worker-084 id ... not third-party"). This is the
missing third-party reproduction: worker-053 authored neither corpus, neither stage tool, nor
any class schema.

## Method

`repro_infoarm_053.py` replicates the `run_acceptance.py::run` stage contract byte-for-byte
(stage A `check_class_schema.py --json <f>`, verdict from the JSON body; stage B
`spec_conformance_audit.py <f>`, body verdict `accept|pass|ok` → pass) with a 60 s per-process
timeout, and runs **both stages on every fixture** of both preserved corpora:
29 mutants + 4 controls (heldout-09) and 33 mutants + 4 controls (heldout-10), i.e. 140
subprocess verdicts plus canonical/determinism reruns. `union_caught` = stage A fail OR stage B
fail; `union_escape` = accepted by **both** stages. Criteria were pre-registered in
`PREREGISTRATION.json` before the first fixture run.

Frame (all hashes in `report.json.frame_sha256`): stage A `000e09e46b2f`, stage B `c79d8ab8440a`,
F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, F0 `0abb9ed8a961`, FROZEN rev29
`815e08079aef`; heldout-09 manifest `0ccdfc37dc79`, heldout-10 manifest `d026fec40fe4`.

## Result

| corpus | informative C2+C0 | union caught | union escape | declared | equal | W arm | controls |
|---|---|---:|---:|---:|---|---|---|
| FORM-HELDOUT-09 | 24 (12 C2 + 12 C0) | **0** | **1.0** | 0/24, 1.0 | yes | 5/5 caught (stage B) | 4/4 accepted by both |
| FORM-HELDOUT-10 | 26 (13 C2 + 13 C0) | **0** | **1.0** | 0/26, 1.0 | yes | 7/7 caught (stage B) | 4/4 accepted by both |

All 13 escape families reproduce in both corpora at 2/2 fixtures each: conclusion-content-erasure,
conclusion-polarity-inversion, containment-reversal, development-topology-weakened,
end-structure-contradiction, equivalence-inflation, extension-predicate-weakened,
known-obstruction-erased, natural-language-inversion, schema-falsifier-erasure,
sobolev-threshold-lowered, source-status-flip (heldout-10 additionally
f0-binding-stale-hash). In the informative arms **no rule of either stage fires at all**
(stage A `pass` 50/50, stage B `accept` 50/50); the 12 W-arm mutants are all caught by stage B
and none by stage A. The frozen WCC canonical is stage-A pass / stage-B reject `R03`, exactly as
pre-registered.

## Controls (all pass, `controls.json`)

- **K1** canonical C2 and C0 accepted by both stages; **K2** WCC canonical stage-B reject `R03`
  (pre-registered known calibration defect) — proves stage B was actually exercised.
- **K3** determinism: 4 fixtures re-run twice, identical verdicts.
- **K4/K5** every fixture sha256 equals its manifest entry; both manifest hashes equal the
  `manifest_sha256_before_run` declared by the corpus reports.
- **K6** parser contract: a conforming copy under this directory is accepted by both stages; an
  unparseable YAML stub is not.
- **K7** no frame pin moved across the run.

## What this establishes, and what it does not

It establishes that the informative-arm 1.0 number is not a worker-084 artifact or a reporting
error: an independent worker reproduces 0/24 and 0/26 at pinned bytes with all controls green.
It does **not** adjudicate the cause, does not re-open or settle R03, does not evaluate a
repair, and issues no gate verdict — the G-CLASSBIND disposition stays with the lead/controller.

## Files

`PREREGISTRATION.json`, `repro_infoarm_053.py`, `report.json`, `mutants.json` (per-fixture raw
verdicts), `per_fixture.json` (controls), `controls.json`, `drift.json`, `frame.json`,
`run.log`, `SHA256SUMS.txt`, `snapshot/`.

**Falsifier:** any informative C2/C0 mutant in heldout-09/10 caught by a stage at these pinned
tool hashes; measured aggregates differing from the declared reports; any K1–K7 control failing;
any frame hash moving; or a re-run of `repro_infoarm_053.py` producing different per-fixture
verdicts.
