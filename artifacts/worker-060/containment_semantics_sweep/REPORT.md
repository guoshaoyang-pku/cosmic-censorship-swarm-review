# W060-CONTAINMENT-SEMANTICS-SWEEP-01

- **Worker:** worker-060 (bounded execution worker; one task, then exit)
- **Nodes / classes:** F2a, F2b, F0 / `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **Gate of record:** G-FORM (context only — this artifact issues **no gate verdict**)
- **Root pin:** `artifacts/formulation/FROZEN.json` revision 28, sha256 `2f358f6722d9…`
- **Reviewed bytes (all equal to their FROZEN rev28 entries):**

| artifact | sha256 (12) |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `55d0a1ea9bda` |
| `research_map/formulation_taxonomy.yaml` (declared F0, rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |

- **Evidence:** `artifacts/worker-060/containment_semantics_sweep/evidence.json`
  (`sha256 8f177b1e2fad0506…`), 40 checks, 1 failed.
- **Verdict: `HARD_FINDING`** — the previously reported inverted containment premise survives at the
  frozen bytes, and the canonical structural gate cannot see it. No node completion is claimed.

## Task taken

No assignment card existed in `comms/inbox/worker-060.jsonl`. Following the launch prompt and the
formulation lead's closing status ("Open: two independent accepts per class at the new hashes;
heldout-09 run"), this is a self-proposed, bounded, class-bound *measurement*: sweep every
containment / transfer-strength assertion in the FROZEN rev28 formulation artifacts against the
declared extension-set chain

```
E_C2  ⊆  E_{C^1,1}  ⊆  E_H2loc  ⊆  E_C0          (rank 0,1,2,3)
```

and measure whether the structural gate `check_class_schema.py` (R16) can distinguish the canonical
file from a file whose containment premise is inverted. It extends, without duplicating,
W060-F2B-REV12-CLOSURE-VERIFY-01, which checked eight named closure findings on F2b alone.

## Method

`verify_containment_semantics.py` is deterministic and fails closed:

1. **Pins.** Every reviewed input must equal its FROZEN rev28 manifest entry, else exit 2.
2. **Machine rows.** All `implication_ledger.one_way_entailments`, `forbidden_transfers` and
   `extension_class_containment` strings in F2a/F2b, plus the supplement's `axis_registry`
   containment strings and 7-row implication ledger, are parsed and evaluated against the chain.
   Entailment from `no X-extension` to `no Y-extension` is licensed iff `E_Y ⊆ E_X` (rank(Y) ≤ rank(X)).
3. **Curated prose rows.** 14 pinned sentences (exact substring + file hash) are evaluated against
   the chain; a missing substring returns exit 2 rather than a silent pass.
4. **Generalised detector CS-01/CS-02.** A token-anchored set-size comparative rule and an explicit
   `X-inextendibility is stronger/weaker than Y` rule, with comparator resolution from the same
   sentence and the row target as fallback. Controls: canonical fires once, repaired copy silent,
   the true taxonomy sentence ("those are strictly larger classes", relative to C2) silent.
5. **Coverage recall probe.** The detector is additionally run over **every string** of all five
   documents (1495 strings): 1 hit — the same defect — 0 new hits, 0 unresolved.
6. **Gate sensitivity.** `check_class_schema.py --json` is run on four copies in a temp dir; the
   canonical file is never modified (verified by re-hash).

## Result

**40 checks, 39 pass, 1 fails** — `PR-F2B-245`, the inverted premise in
`schemas/af_scc_c0_vacuum.yaml:245`:

```yaml
forbidden_transfers:
  - {from: "no proper future C2 extension", to: "this class",
     reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
```

The conclusion ("C2-inextendibility is strictly weaker") is correct; the **premise is inverted**.
`E_C2 ⊆ E_C0`, so C2 is a strictly *smaller* extension class, exactly as this file's own
`extension_class_containment` line and the sibling C2 schema state. This reproduces
HF-060-F2B-1 (W060-F2B-REV12-CLOSURE-VERIFY-01) at the same hash by an independent route.

Everything else is clean at these pins: all F2a/F2b entailment and forbidden-transfer rows are
licensed by the chain; both containment strings plus the supplement's axis-registry containment and
7-row ledger agree with the chain; the 13 other pinned prose sentences agree; nothing else in 1495
strings inverts a set-size comparative.

### Gate coverage gap (measured, not inferred)

| gate run on a copy | exit | meaning |
|---|---|---|
| canonical F2b (defect present) | 0 | PASS — premise inversion invisible |
| M-A, reason repaired `larger` → `smaller` | 0 | PASS — repair invisible |
| M-B, `E_C0 contains … contains E_C2` → `E_C2 contains E_C0` | 0 | PASS — a flipped containment string is invisible |
| M-C, assert the forbidden C2 ⇒ C0 converse as an entailment | 1 | FAIL — gate is alive for the token-level violation |

R16 checks presence of the ledger, token-level direction of `from`/`to`, and a verb-list prose
regex; it never evaluates the premise semantics of `extension_class_containment` or of a transfer
`reason`. This is a coverage gap, not a false gate: G-FORM's "no C0/C2 merge" criterion depends on
the asserted transfer surface, and a one-token inversion there passes every structural test.

### Proposed minimal repair and detection

- Repair (one token, owner `astra-lead-formulation`; HOLD forbids worker edits):
  `strictly larger` → `strictly smaller` at line 245.
- Detection rule CS-01 as implemented: for a sentence naming a regularity token as subject and a
  set-size comparative, "larger" is true iff the subject's rank exceeds the comparator's rank.
  On this corpus it has precision 1/1 and recall 1/1 against the full-text scan, with the four
  controls above; it is a candidate R16 extension, not a gate change made here.

## Limits and falsifiers

- **Scope:** structure/semantics of asserted containment only. Nothing here adjudicates the
  mathematics, non-vacuity, citation scope, the F2a/F2b data-space transfer, or the F0 supplement
  adjudication. The reviewed files were not modified; no gate verdict, `validation_status` or node
  status is set.
- **Per-check falsifiers** are in `evidence.json` (`checks[*].falsifier`); the two headline ones:
  - the hard finding is refuted by any extension-set reading under which `E_C2` strictly contains
    `E_C0` given the file's own definitions;
  - the gate-gap finding is refuted by a rule in `check_class_schema.py` that rejects M-B.
- **Hash binding:** the verdict binds `55d0a1ea9bda…`. A re-run at a different pin returns exit 2
  and makes no claim; nothing transfers across a byte change.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-060/containment_semantics_sweep/verify_containment_semantics.py
# exit 1 = hard finding survives; rewrites evidence.json and snapshots/ and re-measures every pin
```
