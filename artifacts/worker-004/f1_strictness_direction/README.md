# W004-F1-STRICTNESS-DIRECTION-INDEP-01

Independent, hash-bound verification of the **F1 rev13 visibility strictness-direction
correction** (`schemas/af_wcc_vacuum.yaml#d9cebb9404b2`), plus a direction-consistency scan
of the pinned class corpus.

| field | value |
|---|---|
| actor / instance | `worker-004` / `worker-004-20260912T005206-968807` |
| class binding | `AF-WCC-VAC-GEN` (primary; cross-refs `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) |
| node / gate | `F1` / `G-FORM` (cross-ref `F0`/`G-F0`) |
| axis verdict on F1 rev13 direction | **accept** |
| overall verdict | **revise** (carried by finding `W004-DIR-01`, not by the F1 text) |
| instrument exit | `0` — 13/13 pre-registered expectations held, 6/6 controls fired |
| no canonical writes | yes; every write is under `artifacts/worker-004/`, `reviews/`, `runtime/state/` |

## Question

F1 rev13 replaced three semantic leaves at once (the rev12→rev13 delta is *not* binding-only):
the variant `SET` relation, `quantifiers.domains.D5.definition`, and `visibility.definition`.
The new text claims (a) the whole-curve and tail readings in `J^-(q)` are **equivalent** for
causal geodesics by past-closedness, and (b) the set/union reading is **strictly weaker** than
the single-q tail predicate, the direction having been stated as "strictly STRONGER" at rev12.
This task verifies those two claims independently and asks whether the rest of the pinned
corpus agrees.

## Method (deterministic, stdlib-only; `verify_f1_strictness_direction.py#dcc1e6f628d8`)

1. **Pins** — sha256 every pinned input at start and exit; any mismatch fails closed (exit 3).
   Also checks F1's `f0_binding.declared_f0_sha256` resolves to the pinned F0 canonical file.
2. **Whole/tail equivalence** — exhaustive enumeration of all 355 reflexive-transitive
   relations (preorders) on 4 labelled points × all causal chains × all `q`; counts
   (chain, q) pairs where a proper tail is in `J^-(q)` but the whole chain is not.
   Positive control: the same count over all 4096 reflexive-only relations, where
   transitivity is absent.
3. **Direction of SET vs single-q** — over the same exhaustive model set:
   violations of `single-q ⇒ SET`; violations of `SET ⇒ single-q` for chains with a causal
   maximum; and an explicit ω-chain witness (index rule `p_i ⪯ p_j ⇔ i ≤ j`, `p_i ⪯ q_m ⇔ i ≤ m`,
   `q` maximal) checked on a representative window: SET holds, no `q_m` contains the infinite
   tail (witness index `max(k, m+1)`), and the chain has no causal maximum.
4. **Corpus direction scan** — polarity- and subject-aware scan of the pinned corpus for live
   statements asserting SET is *stronger* (opposite direction), with historical/quoted
   annotations classified separately.
5. **Controls** — C1 pin drift fails closed; C2 planted live inversion flagged; C3 planted F0
   repair clears the contradiction; C4 non-transitive positive control; C5 determinism;
   C6 exhaustive count = 355.

## Result

Independent reproduction of the direction mathematics (`report.json#771778055243`, `direction_analysis`):

| quantity | measured | expected |
|---|---|---|
| preorders on 4 points | **355** | 355 (matches W076 T1 count) |
| whole/tail separations (transitive) | **0** | 0 |
| `single-q ⇒ SET` violations | **0** | 0 |
| `SET ⇒ single-q` violations at a causal maximum | **0** | 0 |
| ω-chain: SET holds / single-q fails / no causal maximum | **true / true / true** | strict separation |
| non-transitive relations with a whole/tail separation (positive control) | **3741** | ≥1 |

So: **the F1 rev13 direction text is mathematically correct** — the whole/tail equivalence is
exactly past-closedness + transitivity, and SET is strictly weaker, separated only by a curve
without a causal maximum. F1's rev13 revision note discloses the correction, and the
`VARIANT_REGISTRY#6bac9ade` and `AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d639` agree with it.

## Finding `W004-DIR-01` (major, open) — frozen F0 canonical asserts the opposite direction

`research_map/formulation_taxonomy.yaml#0abb9ed8a961` (F0 rev5, the gate-passed F0 artifact, and
the exact hash F1's `f0_binding` declares) carries **two live statements of the superseded
direction**:

- **line 94** (variants block, `AF-WCC-VAC-GEN` variant `SET`): *"… contained in the union of
  J^-(q) over all q in I+ (intersected with M). **Strictly stronger** than the parent class:
  gamma outside the union implies no single q sees a tail of gamma, but not conversely."*
  The label contradicts its own justification — the quoted implication is the one that holds
  when SET is **weaker**.
- **line 200** (class `AF-WCC-VAC-GEN` conclusion text): *"The set-based reading (gamma
  contained in the union of J^-(q) over all q in I+) **is strictly stronger**; it is registered
  as variant `SET` …"*

F1 rev13 (which binds that F0 hash), the registry and the SET delta all now say **weaker**.
Since F0 is frozen and `G-F0` passed on it, the contradiction cannot be fixed by a worker:
it needs an owner/controller disposition — an authorized F0 revision (which voids the G-F0
accepts and requires re-verification) or an explicit erratum recording the F0 direction label
as a known residual. The F0 companion supplement's D1 history line ("F0 was stronger") is
classified historical by the scanner and is not counted as a live contradiction, but it repeats
the false label as a fact (`W004-DIR-02` candidate, not raised as a separate finding).

## Moving input (deliberately not bound)

`artifacts/formulation/FROZEN.json` was rewritten at least three times inside a five-minute
window while the rev13 repair was landing (`2f358f6722d9` rev28 → `e1a8aaa394eb` → `3d9e3d77fd87`
→ `815e08079aef` rev29; see `frozen_drift_observed.json#37aa350dac91`). No verdict here is bound
to it. All pinned inputs were stable across the instrument run (`pin_drift_at_exit = []`).

## Evidence layout (sha256 prefixes)

| file | sha256 | role |
|---|---|---|
| `PREREGISTRATION.json` | `03b029253e69` | predictions E1–E10 + controls, written before measurement |
| `verify_f1_strictness_direction.py` | `f77a6ae30025` | fail-closed instrument (v2) |
| `report.json` | `c70cdbb306aa` | pins, checks, direction analysis, corpus scan, findings |
| `controls.json` | `e4767937ee95` | C1–C6 results |
| `frozen_drift_observed.json` | `37aa350dac91` | FROZEN.json churn observation |
| `run_stdout.txt` | `3962d2c7baab` | instrument console transcript |
| `emit_events.py` | `6645dbe3aa81` | event emitter (re-verifies every manifest entry before emitting) |
| `reviews/F1-rev13-strictness-direction-worker-004.json` | `0ffc03a58b28` | scoped axis verdict |
| `MANIFEST.json` | bundle index (rev3) | lists sha256 for every file above plus both checkpoints |

### Harness correction (v2, no measurement change)

The v1 C1 pin-drift control re-invoked the full instrument, which then ran its own control
battery and recursed into nested sandbox directories (166 levels, terminated only by path
length). v2 passes `--no-controls` to the C1 child and skips the battery outright on pin drift.
`controls.json` and `run_stdout.txt` are **byte-identical** across the two batches; the first
batch's instrument/report hashes are superseded by the erratum event
`w004-f1dir-20260912T0145-status-harness-erratum`, and all measurements, controls and verdicts
are unchanged.

## Reproduction

```bash
cd <repo root>
python3 artifacts/worker-004/f1_strictness_direction/verify_f1_strictness_direction.py
# exit 0 = all expectations held; 2 = refuted; 3 = pin drift (fail closed). ~4.5 min: exhaustive
# model enumeration dominates. report.json and controls.json are rewritten deterministically.
```

## Falsifier

Any pinned input hashing differently; a whole/tail separation among transitive preorders; a
`single-q ⇒ SET` violation; a `SET ⇒ single-q` violation in a causal-maximum model; failure of
the ω-chain witness; a live "SET is stronger" statement inside F1 rev13, the registry or the
SET delta; absence of the disclosure note in `revision_history[11]`; any control that does not
fire. Re-running the instrument on moved bytes fails closed.

## Non-claims

Not a gate verdict, not a node completion, not `validation_status=passed`. Only the visibility
strictness-direction axis of F1 is adjudicated — not a full-schema F1 acceptance, not R03
binder calibration, not CF-21 genericity, not any literature/citation question. No canonical
file was modified.
