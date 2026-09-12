# W058-REV29-DELTA-05 — independent certificate for the rev29 freeze break

Worker `worker-058`, node `F1,F2a,F2b`, class binding
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`, gate context `G-FORM`.
Worker evidence only: no canonical path was written, no node status, no `validation_status`,
no gate verdict.

## Why this task

The intended task was an independent audit of the W083 rev13 repair packet against the rev28
pins. Mid-authoring the freeze broke: `schemas/*.yaml` moved at 00:53:20–00:53:40 and
`artifacts/formulation/FROZEN.json` was republished as revision 29 (`astra-life05-evidence-binding-repair`).
The aborted pass is preserved at `../rev13_packet_audit/audit_report.json` (measured FROZEN
`e1a8aaa394eb` at 00:55:01). This certificate re-binds to the rev29 bytes and certifies the delta.

## Result

| Check | Result |
|---|---|
| rev29 canonical pins (3 schemas + mirrors + evidence + checker + F0 pair) | match |
| `verify_frozen.py` at report time | exit 0, 50/50 (**but see generations note**) |
| `f0_binding` resolves in all three schemas (declared == measured, both pointers) | true |
| **L-FORM-01** inverted class-size premise at F2b `b2ab6acb` | **STILL LIVE (hard)** |
| **F2b stale containment denial** C0:152 (strict reading hard / steelman advisory) | **LIVE** |
| strength-bucket mislabel C0 (advisory) | live |
| **L-FORM-03** predicate-strength inversion at F0 taxonomy `conclusion.text` | **LIVE (hard wording)** |
| W083 L-FORM-01 diff vs rev29 bytes | applies cleanly, declared target `3cdcaa44` **stale** |
| F1 rev13 direction repairs (anchors 72/213/234) | verified; delta confined to 12 lines incl. history |
| **L-FORM-02 recurrence** with an input moved (no O3 guard) | **demonstrated: silent rewrite, declared hash goes stale** |
| Sensitivity selftest | 7/7 expectations met |
| Post-run drift guard | no drift during the run |

### Headline

1. **The rev29 freeze moved all three schema hashes without closing the one hard F2b content
   defect.** At F2b `b2ab6acb`, an independent sweep still returns
   `class_size_predicate_inverted` (C0:245, "C2 is a strictly larger extension class" against the
   file's own chain `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`). The hash move therefore voided the only
   full-schema accepts that existed (F1 3, F2a 2, F2b 3 at the predecessor pins, substring census)
   while F2b stays un-acceptable. F2b's single live-hash `accept` (worker-061) is explicitly scoped
   to the variant-CH axis and is not a full-schema verdict.
2. **rev29 is not one frozen object.** Three byte-distinct `FROZEN.json` generations were observed;
   the last two both declare `revision 29` with different `frozen_at` (00:55:02, 48 files;
   00:57:26, 50 files). A citation of "FROZEN rev29" without the manifest sha256 + `frozen_at` is
   ambiguous. An intermediate generation failed `verify_frozen` (1 drift:
   `evidence/variant_delta_check.json`), measured by this worker and independently recorded by
   worker-007 at 00:56:06; the later generation is self-consistent.
3. **L-FORM-02 was closed in letter by the refresh direction, not by the guard.** The declared
   `consistency_evidence_sha256` now equals the live `9e335e9b`; the checker is still unguarded
   (`de356d99`). D8 shows that moving one compared taxonomy input silently rewrites the frozen
   evidence path and leaves the declared hash stale with no `--write` flag and no signal. W083's O3
   guard (dry-run default) would stop exactly this.
4. **L-FORM-03 is partially repaired and still open.** During the audit the variant registry and
   SET delta `strength`/`visibility.definition` sites changed from "stronger" to
   predicate-scoped "weaker" (see `state_race`); the declared F0 taxonomy
   `classes.AF-WCC-VAC-GEN.conclusion.text` still says the set-based reading "is strictly stronger"
   — inverted if read as the predicate, charitably correct if read as the class conclusion. Because
   `research_map/formulation_taxonomy.yaml` is the G-F0-frozen artifact, repairing it voids G-F0 and
   needs controller handling.

## Formal relation used by the L-FORM-03 classifier

`P_tail(γ) ⇒ P_set(γ)` (past-closedness of `J⁻(q)`). Therefore the SET **predicate** is strictly
weaker, the SET **negation** is strictly stronger, and the SET **class conclusion**
(`no P_set`) is strictly stronger. Sites are judged by which of the three a sentence is about;
the certificate reports both the strict verdict and the charitable reading.

## Files

| file | sha256 (16) | role |
|---|---|---|
| `audit_rev29_delta.py` | see report `artifacts` map | deterministic checker (read-only on canonical paths) |
| `rev29_delta_report.json` | see report `artifacts` map | full certificate, all sub-checks |
| `sensitivity_selftest.json` | see report `artifacts` map | 7 mutants/controls |
| `pinned/` | recorded in report | provenance copies of the audited bytes |
| `sandbox/` | — | disposable mutant workspaces |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-058/rev29_delta_audit/audit_rev29_delta.py
# exit 0 = certificate recomputed; any canonical byte change is reported in .drift
```

## Falsifier

Falsified by: (a) the F2b inverted premise being absent at `b2ab6acb`; (b) `verify_frozen.py`
exiting 0 *and* the manifest generation being unique at revision 29; (c) the SET sites being
predicate-consistent; (d) a canonical byte written by this audit. None of these was observed.

## Next falsifier

Re-run after the next freeze: exit requires `verify_frozen` rc=0, F2b sweep hard=0 at the new hash,
L-FORM-03 sites scoped explicitly, and the W083 L-FORM-01 diff re-pinned to the new bytes.
