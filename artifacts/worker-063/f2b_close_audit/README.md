# W063-F2B-CLOSE-AUDIT-01 — does the containment-only F2b rev14 close F2b?

**Actor:** worker-063 · **Class:** `AF-SCC-C0-VAC-GEN` · **Node:** F2b · **Gate:** G-FORM
**Measured:** 2026-09-12 ~01:10–01:14 +08:00 at FROZEN rev29 `815e08079aef`, canonical F2b
`b2ab6acb2bbe`, canonical F2a `e9a27996dfd3`, canonical F1 `d9cebb9404b2`.
**Authority:** worker measurement only — no gate verdict, no node status, no
`validation_status`, no canonical byte change. Interpretation is owned by
`astra-lead-formulation` / `astra-lead-audit`.

## Question

The owner has a validated two-edit F2b repair candidate (`regularity.must_not_conflate[0]`
stale containment denial; `implication_ledger.forbidden_transfers[0].reason` inverted size
premise). Lead-formulation's L-FORM-01 recommended folding it into a rev14 *before*
spending the r3 F2b review budget. This audit measures what such a rev14 would and would
not close.

## Method (frozen before measurement)

1. **Pins.** 21 inputs (schemas, FROZEN, taxonomy, vocabulary registry, acceptance
   evidence, both published candidates, 7 review files, 2 frozen evidence snapshots) are
   hashed; any drift exits 3. End-of-run re-measure catches movement during the run.
2. **Candidate diff.** Both candidates are line-diffed against canonical F2b with an
   independent indentation-aware YAML path tracker. Both change exactly 2 lines and exactly
   the two containment leaves.
3. **Finding record.** Every hard-failure record for F2b at rev13/rev29 is extracted from
   the pinned review files plus a byte-verbatim snapshot of accepted-stream review/blocker
   events (each event carries its source line and a canonical sha256). 25 records, 8
   sources.
4. **Join.** Each record is normalised to one of eight declared carrier families; a family
   is *touched* iff a candidate changed leaf path is a prefix of (or equal to) its anchor.
5. **Measured liveness.** For each untouched family the runner measures the defect directly
   in the frozen bytes (token lists, embedded hashes, binding fields, base hashes,
   aggregator pins, stream stamps) and names the actor that can close it.
6. **Controls.** K1 candidate minimality + join, K2 join sensitivity, K3 determinism,
   K4 fail-closed pin drift, K5 extraction non-vacuity, K6 negative control — all pass.

## Result

| family | HF records | reviewers | touched by candidate | live at bytes | closing actor |
|---|---:|---:|---|---|---|
| C_H1 containment denial | 5 | 4 | **yes** (both) | yes | schema owner — candidate carries it |
| C_H2 inverted size premise | 6 | 5 | **yes** (both) | yes | schema owner — candidate carries it |
| C_VOCAB conclusion token | 3 | 3 | no | **yes** | gate-owner ruling |
| C_A2 evidence self-verification | 1 | 1 | no | **yes** | owner edit or evidence-standard ruling |
| C_A6 alias-registry binding | 1 | 1 | no | **yes** | owner edit (subsumed by C_VOCAB ruling) |
| C_PIPE acceptance base binding | 2 | 2 | no | **yes** | owner edit + re-freeze |
| C_SEP6 aggregator pins | 1 | 1 | no | **closed mid-audit** | owner (aggregator rev7) |
| C_STREAM ordering shadow | 1 | 1 | no | **yes** | controller stream hygiene |

**Verdict.** A containment-only rev14 closes **2 of 8** carrier families and leaves **5
live** (`C_VOCAB`, `C_A2`, `C_A6`, `C_PIPE`, `C_STREAM`). On the frozen bytes it is
therefore predicted to attract further revise verdicts from the same sources unless those
families are edited or ruled out before re-freeze.

Key measured facts:

- **C_VOCAB (ruling).** F2b declares `conclusion_type: scc_c0_future_inextendibility` and
  `genericity.kind: residual_comeager`, both VOCAB_ALIASES canonical keys, while the
  G-F0-passed canonical taxonomy's `field_vocabulary` allows only the aliases
  (`strong_cosmic_censorship_C0`, `provisional_baire_residual`). The registry policy says
  canonical-first and "aliases ... must never appear in a new canonical artifact"; F2b
  mentions `VOCAB_ALIASES` nowhere. No single schema edit satisfies both frozen artifacts.
- **C_PIPE (owner edit).** FROZEN rev29 pins `semantic_escape_rebased.json` whose declared
  base `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` is `1bb78ce9b357` (rev11)
  while the live base is `b2ab6acb2bbe`; `acceptance_pipeline_report.json` records a PASS
  verdict with no base bytes/revision at all. The formulation lead independently filed the
  same defect at 01:13 (`lead-form-20260912T0113-106`).
- **C_A2/C_A6 (owner edit).** `taxonomy_consistency.json` is 495 bytes, contains zero
  64-hex hashes and pins neither input it evaluated; F2b's `f0_binding` has no
  alias-registry field even though `VOCAB_ALIASES.json` is itself FROZEN-pinned.
- **C_SEP6 (closed mid-audit).** At frame time the aggregator pinned rev11 components
  (`1bb78ce9b357` / `b6123750b37d`, evidenced by the pinned w044 review). During the audit
  the owner published aggregator **revision 7** (`27255e5b34f3`), whose declared
  `supersedes_sha256` equals this audit's frame-time pin and whose component pins now match
  live rev13 bytes. C_SEP6 is excluded from the live set on that evidence.
- **C_STREAM (controller).** Event `w06-20260912T0115-f2b-rev6` carries
  `created_at 01:15:00` (future at measure), `_received_at: null`, pins a stale C0 hash
  `e6b1af2bd692`, and sits in the accepted stream at line 712 while still in
  `comms/outbox/worker-06.jsonl:38` with no receipt stamp; no ordering rule is declared.

## Files

| path | sha256 |
|---|---|
| `report.json` | `b32211ef1c40d644db2d6520afa65c925f35ba9eb1748047d3fdd9014902682f` |
| `matrix.tsv` | `09b3ece2b48bf8b21f44d12872c194cc03436006298f2374a914ff89a55297e1` |
| `run_close_audit_063.py` | `8586f1890d3083f3a659b6460d0da02c5b5b2aa7908142bf1ea0e93030158e08` |
| `evidence/review_events_snapshot.json` | `d9767b63dbc6d7da2f0f2a7fc290052cfb5e8e94a780443032ee352d31c8973d` |
| `evidence/owner_blocker_snapshot.json` | `cb5f277e9208d04a53423fbba6311a04cc782b6b2485c0dc3dcb48e8ed3cea88` |

## Limits and falsifier

The join is path-based on the current YAML layout; the instrument does not re-adjudicate
whether each reviewer's hard failure is correct, only whether the defect is still present
at the pinned bytes and whether the candidate edits its carrier. C_A2/C_A6/C_SEP6/C_STREAM
rest on single advisory sources at frame time; C_VOCAB and C_H1/C_H2 are multi-reviewer.
The review frame closes at 01:09–01:13 (later reviews, e.g. worker-085 at 01:11:45, are not
in the record). Applicability is bounded by the pinned hashes; the runner exits 3 on drift.

**Falsifier.** A pinned input differs from its recorded hash; the join misclassifies a
carrier; any family recorded live is shown closed at the pinned bytes by a frozen
adjudication or corrected bytes; a rev14 lands that already carries C_VOCAB/C_A2/C_A6/
C_PIPE/C_SEP6 edits or a ruling closes them; or the frozen review record contains a
hard-failure family not enumerated here.
