# W037-L0-HF02-CLASSBIND-EVIDENCE-01

Bounded class-bound worker task (worker-037), read-only on every canonical path.
Advisory input to the controller/A0 ruling requested by literature blocker **BL-7**
(`comms/outbox/astra-lead-literature.jsonl`, 2026-09-12T00:56:20+08:00).

**Class IDs:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-VAC-GEN`
**Node:** L0 · **Gate:** G-LIT (adjacent: G-AUDIT)
**Verdict:** `REPAIR_CANDIDATE_VALIDATED_ADVISORY` — 16/16 declared checks pass, 8/8 controls behave as declared, exit 0.

## Question

8 L0 rows carry two frozen class ids in `class_ids` (`D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528`).
`evaluation_rubric.yaml` frozen_classes says classes "must never be disjoined in a statement".
Worker-063 (`artifacts/worker-063/l0_scope_adjudication/`) ruled the question is a scope
decision for the controller/A0 and priced a change that keeps the *first-listed* id. What was
missing is the row-level evidence for **which single class each row actually binds** — the
content decision the owner needs before choosing a repair.

This task supplies that evidence, quote-verifiable against the row bytes, and emits two
candidate ledgers (never applied to canonical).

## Pins

Hard (run void on drift; measured at start and end, unchanged):

| path | sha256 | bytes |
|---|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` | 151521 |
| `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` | 13969 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | — |

Context (measured at run time and recorded; the owner repair wave was rewriting these during
the run — rev12→rev13 schemas, FROZEN rev28→rev29, detector patch — so a mid-run move is
recorded as context drift, not as a void): `schemas/af_wcc_vacuum.yaml`,
`schemas/af_scc_c2_vacuum.yaml`, `schemas/af_scc_c0_vacuum.yaml`,
`research_map/class_separation.py`, `artifacts/formulation/FROZEN.json`.
Exact measured values are in `report.json` (`context_pins_measured_at_start`,
`context_drift_during_run`).

## Result — evidence-driven rebinding (variant B, preferred)

| row | live `class_ids` | variant B `class_ids` | variant B `informs_classes` | decisive row text (verbatim) |
|---|---|---|---|---|
| D-004 | C2, C0 | `[]` | C2, C0 | "Not the C^2 formulation (L^2 connection is weaker than C^1, hence much weaker than C^2)." / "Not the C^0 formulation (which forbids even continuous extensions)." |
| D-005 | C0, C2 | `[]` | C2, C0 | "These formulations are strictly between the C^0 and C^2 formulations in strength." |
| T-303 | C2, C0 | `[]` | C2, C0 | "Does not decide C^0 SCC." / "the data class is special (high-frequency/impulsive), not generic AF collapse data" |
| T-305 | C0, C2 | **C2** | C0 | "Lipschitz-inextendibility (metric C^{0,1})." / "Does not prove C^0 SCC." |
| T-402 | C2, C0 | **C2** | C0 | "the strongest available pointer for why the C^2 formulation might survive while the C^0 one fails" |
| T-515 | WCC, C0 | **WCC** | C0 | "Does not by itself decide any SCC formulation." / "Kerr stability status as of 2026-09" |
| T-526 | C2, C0 | **C2** | C0 | "C^0 extendible; NOT C^{0,1}_loc (Lipschitz) extendible." / "Does not prove C^0-inextendibility" |
| T-528 | WCC, C0 | **WCC** | C0 | "Does not by itself prove C^0 SCC false; combined with Dafermos-Luk it discharges the antecedent" |

Direction of the rebinding follows the frozen class contracts: the C2 class forbids the
*smaller* extension set (`E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`), so a lower-regularity
inextendibility result (Lipschitz, non-Lipschitz) bears on C2, while it cannot establish C0
(matching `evaluation_rubric.yaml` "SCC-C0 implies SCC-C2; the converse does not hold").
Definitions of intermediate formulations that explicitly exclude both frozen regularities
(D-004, D-005) and the special non-generic construction (T-303) assert no frozen-class
conclusion at all; they get `class_ids: []` — an existing ledger state (28/62 rows) — with
both ids in `informs_classes` (multi-element informs is a **new usage flagged for the owner**).

Variant A (convention-minimal: keep first-listed id, move the rest to `informs_classes`) is
also emitted and validated, but its first-listed bindings disagree with the row evidence for
D-004, D-005, T-303, T-305, T-515; it is reported for comparison only.

| variant | candidate sha256 | literal disjunctions after | unknown tokens | other-key changes |
|---|---|---|---|---|
| A (first-listed) | `969c9bef8a63bf7e062df914000c163c4bde1010672b6025af948453355a5d6b` | 0 (was 8) | 0 | 0 |
| **B (evidence-driven)** | `b2a27c9cf49b5d9806d576173d5baa96a094d9fec2bb5790a53fd871ce7e231e` | 0 (was 8) | 0 | 0 |

Both variants: 62/62 rows, only the 8 ruled rows changed, canonical `ledger/theorems.jsonl`
byte-identical before/after.

## Checks and controls

Declared checks (all pass): parse 62 unique rows; live disjunction census = the 8 ruled rows;
rule expectations match live ids; **every evidence quote verified present in the named field**;
canonical detector baseline = the single pre-existing T-402 finding; both variants clear the
literal disjunction; no unknown tokens; no other key mutated; no detector finding added;
byte-determinism across two builds; idempotence; no canonical writes; context file set complete.

Controls (all behave as declared): M1 positive live-8; M2 under-repair detected; M3 unknown
token detected; M4 deleted quote detected; M5 non-target key mutation detected; M6 injected
bare composite detected; M7 pin drift fails closed; M8 empty binding (no primary and no
informs) rejected.

## Adjacent findings left to the owner (not repaired)

- **W037-HF02-ADJ-01** — `T-402.regularity` free text "Between C0 and C2 (weak null
  singularity)." is flagged by the canonical declaration-mode detector as a bare composite.
  It is a *separate* defect from the `class_ids` disjunction and is not cleared by moving ids
  (worker-063 measured the same residual). A text-only rewrite is left to the owner.
- **W037-HF02-ADJ-02** — C0-bound rows typed `conclusion_type: theorem` (T-302) sit against
  the `AF-SCC-C0-VAC-GEN` rubric `status_risk`: "never `open_conjecture` and never `theorem`".
  Under variant B, T-303 and T-526 are rebound to C2; **T-302** (single-class C0 theorem on
  exact Schwarzschild) remains and needs an owner/A0 typing ruling.

## Falsifier

Re-run `build_candidate.py` at the hard pins above. Falsified if: any of the 8 live rows no
longer disjoins two frozen class ids; any declared check flips to false; any evidence quote no
longer occurs in its named field; a variant leaves a disjunction or an unknown token; or a
canonical path is modified by the run. Input drift in the three hard pins **voids** the run
(exit 3) rather than falsifying it; context drift is recorded, and the checks are re-runnable
at the new context bytes.

## Does not claim

Gate verdict (G-LIT/G-AUDIT), node status, `validation_status` promotion, authority to edit
the canonical ledger, an A0/rubric scope ruling, a class-binding repair as landed, any theorem,
any physics or mathematics result, or one of the two independent accepts. The candidate
ledgers are advisory artifacts under `artifacts/worker-037/` only.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-037/l0_hf02_classbind_candidate/build_candidate.py   # exit 0
python3 artifacts/worker-037/l0_hf02_classbind_candidate/emit_events.py      # writes outbox + SHA256SUMS
```

Artifacts: `report.json` (machine record), `CANDIDATE.json` (per-row decisions + evidence),
`candidate_ledger_variant{A,B}.jsonl`, `binding_rules.json` (decision table with quotes),
`SHA256SUMS`, checkpoint at `runtime/state/w037_l0_hf02_classbind_checkpoint.json`.
