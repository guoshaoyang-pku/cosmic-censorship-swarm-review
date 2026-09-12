# W083-F2B-CANDIDATE-ADJUDICATION-01

**Class:** `AF-SCC-C0-VAC-GEN` · **Node:** F2b · **Gate:** G-FORM · **Actor:** worker-083
**Scope:** independent, hash-bound adjudication between the two apply-ready rev29 F2b text-carrier
repair candidates for the blocking defects `W018-R13-F2B-B1` (line 152) and `W018-R13-F2B-B2`
(line 246). Read-only with respect to canonical artifacts. No gate verdict, no node status, no
`validation_status`, no canonical write.

## Why this task

Two candidates for the same two-line repair now exist and both are advertised as apply-ready:

| id | path | sha256 | changed live lines | added bytes |
|---|---|---|---|---|
| C024 | `artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml` | `679ab7bc8746…` | 152, 246 | 511 |
| C083 | `artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml` | `1315427fbc92…` | 152, 246 | 126 |

The formulation owner must apply exactly one before G-FORM r3 can be re-reviewed; nothing on the
map adjudicates between them. This artifact does that mechanically and records the residual owner
choice.

## Pinned inputs (all verified equal to their declared pins; drift voids)

| artifact | sha256 (prefix) | pin source |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` | FROZEN rev29 |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` | mirror |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` | rev29 manifest |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` | FROZEN rev29 |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` | FROZEN rev29 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | G-F0 pass pin |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` | FROZEN rev29 |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` | FROZEN rev29 |
| `C024` / `C083` | `679ab7bc8746` / `1315427fbc92` | declared candidate hashes |

FROZEN revision 29, `frozen_at 2026-09-12T00:57:26+08:00`.

## Findings

1. **Both candidates resolve B1 and B2, and only those two lines move.** Measured changed-line sets
   are exactly `{152, 246}` for both; line counts unchanged; C024 vs C083 differ only at those two
   lines. No conclusion token, statement, genericity slot or any other field moved. `conclusion_type`
   is identical in live, C024 and C083 — so the D3 vocabulary conflict is untouched by both, as
   intended.
2. **B1 (line 152).** Live asserts *"No containment with C2 or C0 is asserted here"* while the same
   file's `implication_ledger.extension_class_containment` (line 238) asserts the strict chain
   `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`. Both candidates remove the asserted denial and state the
   nesting in the ledger's order; the `must_not_conflate` list keeps all 5 entries.
3. **B2 (line 246).** Live asserts *"C2 is a strictly larger extension class, so C2-inextendibility
   is strictly weaker"*, which inverts the chain. Both candidates state the correct direction
   (`strictly weaker`) with a correct set-size / regularity-strength attribution; neither retains the
   inversion.
4. **Support is verified, not assumed.** The added nesting assertion in both candidates is
   byte-derivable from live line 238. C024 additionally cites `VARIANT_REGISTRY.json`; the registry is
   FROZEN-pinned at `6bac9adea19e`, contains exactly one `H2LOC` entry with
   `parent_class = AF-SCC-C0-VAC-GEN`, status `registered_variant_not_written` — so that citation is
   true at the pins. C083 cites nothing new; its claim is internal to the artifact.
5. **The canonical checker does not adjudicate this.** `check_class_schema.py --json` returns
   `pass`/exit 0 on live, C024 and C083. It is a structural gate and (by its own documented blind
   spot) does not decide the semantic contradictions. It is used here as a control, not as the
   decision procedure.
6. **Instrument note (assertion vs mention).** The first harness run flagged C083 as still asserting
   the denial. That was a false positive: C083 *quotes* the old sentence inside a repair note
   (`the earlier 'no containment…' was wrong`). The detectors now strip quoted/bracketed spans before
   matching, and control N6 pins that behaviour. This is the same assertion-vs-mention failure mode
   that CLASSSEP is currently adjudicating; an adjudication instrument that cannot tell them apart
   would have produced the wrong recommendation here.

## Recommendation (pre-registered rule, applied mechanically)

Pre-registered before measurement: **Q1** correctness (resolve B1/B2, zero undeclared changes,
checker pass) → **Q2** every added assertion entailed by FROZEN-pinned bytes → **Q3** fewest changed
lines, then fewest added bytes → **Q4** fewest added external artifact references.

Both candidates pass Q1 and Q2. Q3/Q4 select **C083** (`added_bytes 126` vs `511`;
no external reference added vs one). Because this worker authored C083, the selection carries an
**author conflict**: the mechanical checks are reproducible from the pins, but the owner or an
independent reviewer must confirm before applying. The counter-argument is recorded: C024 is strictly
more traceable (it cites `W018-R13-F2B-B1/B2` and the H2LOC registry entry) and is equally correct
and checker-clean; if the owner values repair-ID traceability over minimal delta, applying C024 is
not falsified by anything measured here.

This is a worker measurement. **It is not a review verdict on either candidate, not gate evidence,
and not an instruction to apply.** The owner still owes: revision bump, FROZEN refresh, corpus
rebind (D4), and independent re-review at the new hash.

## Checks and controls

- **37/37 checks PASS** (`evidence.json`), including: live pin equality, FROZEN entries, declared
  delta equality, line counts, B1/B2 live reproduction, B1/B2 resolution, D3 token invariance,
  support checks, and the canonical checker control.
- **8/8 controls PASS** (`controls.json`): P1/P2 positive (detectors fire on live), N1/N2 (reinserted
  denial/inversion caught), N3 (spurious line widens measured delta), N4 (truncation caught), N5
  (altered registry parent breaks the support check), N6 (quoted denial is a mention, not an
  assertion).

## Falsifier

Re-run `adjudicate.py` at the pins: any FAIL, any pin movement, or any **undeclared** line difference
between live and either candidate voids this adjudication. If the live F2b bytes move before the
owner applies a repair, this document is void and must be re-run.

## Non-claims

No gate verdict; no node status; no `validation_status=passed`; no canonical artifact edited; no D3
token adjudication; no D4 corpus rebind; no numerics/N1 work.
