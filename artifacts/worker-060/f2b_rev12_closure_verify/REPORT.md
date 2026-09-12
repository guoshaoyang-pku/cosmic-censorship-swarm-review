# W060-F2B-REV12-CLOSURE-VERIFY-01

Independent, hash-pinned closure verification of the canonical F2b class schema
`schemas/af_scc_c0_vacuum.yaml` (class **AF-SCC-C0-VAC-GEN**) at the revision published with
FROZEN.json revision 27/28 (`revised_at 2026-09-12T00:31:41+08:00`, internal `revision: 12`).

- **Reviewed sha256:** `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6`
- **Verdict:** `REVISE` — 6 of 8 closure checks pass, **1 hard finding survives**, 1 minor
  binding defect survives.
- **Authority:** worker evidence only. No gate verdict, no node completion, no
  `validation_status` promotion. This is not one of the two named reviewer accepts G-FORM
  requires; whether the surviving hard finding blocks the gate is the audit lead's and the
  controller's call.

## Inputs (measured at review time)

| input | sha256 (12) |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (canonical, reviewed) | `55d0a1ea9bda` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (authoring) | `55d0a1ea9bda` (byte-identical) |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a961` |
| `schemas/af_scc_c2_vacuum.yaml` (sibling F2a) | `5476a3f2c6bc` |
| `artifacts/formulation/FROZEN.json` | revision 28, `frozen_at 2026-09-12T00:35:08+08:00` |
| `schemas/af_scc_c0_vacuum.yaml` measured again after all probes | `55d0a1ea9bda` (stable) |

Snapshot preserved at `snapshots/af_scc_c0_vacuum.55d0a1ea9bda.yaml` (sha256 equals the pin).

## Closure matrix (findings recorded against rev11 `1bb78ce9b357`)

| id | previous finding | status at `55d0a1ea` |
|---|---|---|
| CL1 | duplicate top-level YAML keys `revised_at` x7 + `revised_at_unused` x2 (silent last-wins loss of revision stamps) | **CLOSED** — strict `yaml.compose` root-map scan finds 0 duplicate keys; exactly one `revised_at`, zero `revised_at_unused`; history now in `revision_history` |
| CL2 | effective `revised_at 00:30:00` future-dated at review | **CLOSED** — `revised_at 00:31:41` ≤ `FROZEN.frozen_at 00:35:08` ≤ run wall clock |
| CL3 | `class_contract_pointer` resolved into the authoring tree with no hash pin | **CLOSED** — pointer is `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN`, resolves; `f0_binding.declared_f0_sha256` equals the measured canonical taxonomy hash `0abb9ed8a961`; the authoring-tree supplement is now a separately named field (`class_contract_supplement_pointer`) that also resolves |
| CL4 | `implication_ledger.forbidden_transfers[0].reason`: "C2 is a strictly larger extension class" | **SURVIVES** — see HF-060-F2B-1 below |
| CL5 | composite `C0/C2` token / class-separation soft flags | **CLOSED** — `class_separation.py` findings = 0, standing regression PASS 17tp/0fn/10tn/0fp; the two composite occurrences (lines 151, 277) are a denial and an `anti_scope.phrases_that_are_not_this_class` quoted mention |
| CL6 | G-FORM criterion completeness / C0-only conclusion | **CLOSED** — all 37 required paths present across quantifiers (incl. `D0`–`D3`, negation, quantifier class), topology, regularity, genericity, I+, visibility, `conclusion_type: scc_c0_future_inextendibility`, extension predicate, data class, non-vacuity; no asserted composite |
| CL7 | canonical/authoring/FROZEN divergence | **CLOSED** — canonical == authoring == FROZEN manifest entry |
| CL8 | consistency-evidence binding | **SURVIVES (minor)** — see HF-060-F2B-2 below |

## Surviving findings

### HF-060-F2B-1 (hard) — inverted premise in the C0/C2 containment reason

`schemas/af_scc_c0_vacuum.yaml:245`

```yaml
implication_ledger:
  extension_class_containment: "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; ..."
  forbidden_transfers:
    - {from: "no proper future C2 extension", to: "this class",
       reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
```

`E_C2 ⊆ E_C0` (a C2 metric extension is a continuous metric extension), so the C2 extension
class is strictly **smaller**, as this file's own `extension_class_containment` line and the
sibling C2 schema (`schemas/af_scc_c2_vacuum.yaml:236`, "E_C2 subset of ... E_C0") both state.
The sentence's conclusion — *C2-inextendibility is strictly weaker* — is correct; its stated
**premise is inverted**. The defect survived the rev12 closure pass (it was the worker-058 /
worker-008 finding against rev11, then at line 251).

- **Repair (one token):** `strictly larger` → `strictly smaller`.
- **Falsifier:** exhibit an extension-set reading under which the C2 extension class strictly
  contains the C0 extension class, with the file's own definitions of C0/C2 metric extensions.
- **Why it is gate-relevant:** `implication_ledger` is the asserted transfer surface the class
  split rests on; an inverted containment premise on the forbidden C2→C0 transfer is exactly
  the surface the G-FORM "no C0/C2 merge / no conclusion inheritance" criterion audits.

### HF-060-F2B-2 (minor) — stale consistency-evidence pin

`f0_binding.consistency_evidence_sha256` declares `675a99d0d25b…`; the file it names,
`artifacts/formulation/evidence/taxonomy_consistency.json`, measured `9e335e9ba1bf…` at the
check instant (mtime `00:36:36+08:00`, after the schema's `revised_at 00:31:41`). The target
file is itself regenerated by the formulation pipeline, so any pin to it is single-instant; at
this instant the declared pin does not resolve. Repair by re-running the consistency check at
the current schema hash and refreshing the declared hash — not by relaxing the check.

## Controls

7/7 mutation controls behave as pre-registered, on copies only; the canonical file was never
modified:

| control | expectation | observed |
|---|---|---|
| M1 inject duplicate `revised_at` | CL1 fails | ✓ |
| M2 set `revised_at` to 2099 | CL2 fails | ✓ |
| M3 repoint `class_contract_pointer` to the authoring tree | CL3 fails | ✓ |
| M4 change the containment reason to "strictly smaller" | CL4 passes | ✓ |
| M5 inject `scc_c0_or_c2_future_inextendibility` | CL6 fails | ✓ |
| M6 drop the `visibility` block | CL6 fails | ✓ |
| M7 set the consistency pin to the measured hash | CL8 passes | ✓ |

Positive control P0 is the reviewed file itself: CL1, CL2, CL3, CL5, CL6, CL7 all pass on it.

## Limits and falsifiers

- Scope is this one canonical file at one hash; nothing here adjudicates mathematics, physics,
  non-vacuity, or the F2a/F2b data-space transfer question (worker-060's earlier
  `xclass_dataclass_adjudication` covers that separately).
- The closure matrix binds only `55d0a1ea9bda`. A re-run with a different `--pin` returns exit 2
  and makes no claim; this verdict does not transfer across a hash move.
- Global falsifier: any check listed under `checks` in `evidence.json` whose `ok` is false at the
  reviewed hash refutes the corresponding closure claim; the two surviving items are refuted
  exactly by the falsifiers stated above.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-060/f2b_rev12_closure_verify/verify_f2b_rev12.py \
  --pin 55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6
# exit 1 = hard finding survives; evidence.json, snapshots/ and this report are rewritten
```
