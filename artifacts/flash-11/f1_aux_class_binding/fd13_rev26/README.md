# FD-13 rebase across FROZEN rev26 → rev28 — measurement addendum

**Status: unverified draft / measurement only. No node completion, no theorem, no physics result.**
Task `assign-FORM-DIFF-02-20260911T2331` — node **F1**, gate **G-CLASSBIND**, class_ids
`AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`.
The canonical tool is lead-owned and was **not modified**; everything here is a byte copy plus
read-only measurement against preserved snapshots.

## Question

`fd13/` established the R12 field-global geodesic exemption on FROZEN **rev19**. FROZEN moved
three times during this rebase (rev26 → rev27 → rev28, all 00:24–00:35). Does FD-13 still
reproduce at the revision now frozen, and does the proposed clause-local fix still behave?

## States measured (each bound to recorded sha256s)

| state | binding | result |
|---|---|---|
| **rev26** `rev26_snapshot/rev26_results.json` | schemas `9a8bd4c9`/`b6123750`/`1bb78ce9`, tool `000e09e4`, KEY_MANIFEST `fce91948` (FROZEN rev26) | **FD-13 OPEN**: leak accepted by base; patch + independent gate reject R12, 0 FP |
| **rev27 transient** `diskhead_results.json` | schemas rev12 `cce9c601`/`5476a3f2`/`55d0a1ea`, tool `000e09e4`, KEY_MANIFEST `fce91948` (FROZEN rev27) | **MASKED BY R22**: the frozen gate rejects all three of its own frozen schemas at R22; leak and controls equally → R12 not readable |
| **rev28 repaired** `rev28fix_results.json` | schemas rev12 `cce9c601`/`5476a3f2`/`55d0a1ea`, tool `000e09e4`, KEY_MANIFEST `014e2d30` (FROZEN rev28) | **FD-13 OPEN**: leak accepted by base; patch + independent gate reject R12, 0 FP; all controls accepted |

`rev28fix_results.json` is the actionable state: leak fixture `leak_rev28fix.yaml`
`e27d0727a494` = schema rev12 `cce9c601` + one appended sentence *"The maximal development is
C^2-inextendible."* inside `non_vacuity.condition`; control `control_rev28fix.yaml`
`e9cb5434f8b4` uses a legitimate future-inextendible **causal geodesic** sentence. Head
interpretation recorded as `FD13_OPEN`; `key_manifest_stable_during_run` and
`measured_schemas_equal_live_disk` are both true.

## Transient R22 regression and the repair (deterministic A/B)

At rev27 the R22 key whitelist did not yet contain the keys introduced by the rev12
`revision_history` rewrite and the F0-binding fields; the frozen gate therefore rejected its
own frozen schemas (`unknown keys: at, class_contract_supplement_pointer,
consistency_evidence_sha256, index, notes, predicate_abbreviation`). Because the live
`KEY_MANIFEST.json` moved while this was being measured (`fce91948` → `014e2d30`),
`rev27_r22_repro.json` re-creates both environments offline from preserved bytes:

| KEY_MANIFEST | WCC | SCC-C2 | SCC-C0 |
|---|---|---|---|
| `fce91948` (rev26/27) | reject R22 | reject R22 | reject R22 |
| `014e2d30` (rev28) | accept | accept | accept |

So the rev27 window was a transient manifest lag, repaired in rev28. Consequence for the
differential harness: **always place the KEY_MANIFEST the gate should use beside the tool
copy**, and treat a run where base rejects the canonical schemas themselves as `MASKED`, not
as evidence about R12.

## FD-13 proposal (unchanged, still a proposal)

`fd13/r12_proposal.diff` (`5eaab3f8f031`) applies the geodesic exemption per clause instead of
per field. Run with the rev28 KEY_MANIFEST it catches the rev26/rev12 leaks on R12 with 0 false
positives; `fd13/fd13_results.json` remains the rev19 collateral sweep (57/57 identical,
0 verdict changes) and stays valid only for rev19-era fixtures.

## Falsifiers

* Rebase falsifier (`rev28fix_results.json`): **NOT fired**. It fires if the measured canonical
  gate rejects the leak (FD-13 closed), rejects a control/canonical schema, the independent
  gate misses a leak or rejects a control, or an asserted tool/rule_spec/KEY_MANIFEST/gate hash
  moves (abort before measurement).
* Proposal falsifier: **NOT fired** under the rev28 manifest; it *would have* fired in the
  rev27 `fce91948` environment (R22 on every rev26+ fixture) — an environment defect, not R12.
* Honest caveat against over-reading: at rev27 the base "rejected" the leak via R22, so a naive
  pass/fail read would have declared FD-13 closed. It is not closed.

## Caveats that must travel with this

1. **Format-dominated rejections.** The canonical gate rejects non-canonical layouts at R01/R02
   before R12; corpus-level agreement is not semantic agreement. These fixtures keep canonical
   layout.
2. **Lexical, not semantic.** Even patched, R12 is a token scan; a leak phrased without
   `inextendib`/`extension`/`horizon` tokens is expected to escape (worker-06 owns the corpus).
3. **Moving head.** FROZEN advanced rev26 → rev28 in ~10 minutes during this measurement; the
   hashes in each results file are the binding, not the revision number.
4. The patch is a **proposal only**; the schema owner must review, apply, and re-run
   `run_gate_tests.py` before any gate verdict moves.
5. No node completion, no theorem, no physics result; the schema owner binds interpretation.

## rev29 addendum — FD-13 still open at FROZEN rev29 (2026-09-12T01:07+08:00)

FROZEN moved to **rev29** (`815e08079aefbc`, frozen_at 00:57:26; schemas rev13
`d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`, tool `000e09e4`, rule_spec `40f9bb9e`,
KEY_MANIFEST `014e2d30`). All asserted pins verified byte-exact before measurement
(`frozen_manifest_stale = false`, `measured_schemas_equal_live_disk = true`).

| state | binding | result |
|---|---|---|
| **rev29** `rev29_results.json` | schemas rev13 `d9cebb9404b2`/`e9a27996dfd3`/`b2ab6acb2bbe`, tool `000e09e4`, KEY_MANIFEST `014e2d30`, FROZEN rev29 | **FD-13 OPEN**: leak `leak_rev29.yaml` `90ae1b59` accepted by base (no rules); control `control_rev29.yaml` `052f61ae` accepted by base; all three canonical schemas accepted; patched `5eaab3f8` and independent flash11 `a89b221c` reject the leak (R12) with 0 false positives |

`targeted_effect` is byte-for-byte the same vector as rev28fix: `leaks_base_escape 1/1`,
`leaks_patched_catch 1/1`, `leaks_flash11_catch 1/1`, all false-positive counters 0.
Rebase falsifier **NOT fired**; proposal falsifier **NOT fired**;
`head_interpretation = FD13_OPEN`. Reproduce with
`python3 build_and_run.py --label rev29 --schema-dir rev13_snapshot`.

The rev19-era historical comparators are still rejected at R22 in this environment
(`../fd13/leak_rev19.yaml`, `../fd13/control_rev19.yaml`) — a stale-manifest artifact, excluded
from `targeted_effect` and from the falsifier, exactly as at rev28. The rev29 addendum does not
change the proposal status: the patch remains a proposal; the schema owner binds interpretation.

## Reproduction

```bash
cd artifacts/flash-11/f1_aux_class_binding/fd13_rev26
python3 build_and_run.py --label rev28fix --schema-dir rev12_snapshot  # rev28 state
python3 build_and_run.py --label rev29 --schema-dir rev13_snapshot    # rev29 state (current head)
python3 verify_r22.py                                                 # rev27 R22 A/B
```
