# W013-F2B-BINDING-CENSUS-01 — result

Independent read-only per-file census of F2b (`AF-SCC-C0-VAC-GEN`) review verdicts at the live
measured hash, run to adjudicate controller finding **CF-31 / REC-39** (hash-bound scan: 4 full
accepts; formulation-lead per-file census: 0 accept / 7 revise).

- **Target pin**: `schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
  (re-measured at run start and end; equals the FROZEN rev29 canonical copy `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`).
- **Authority**: measurement only. No gate verdict, no node transition, no canonical/pinned write.
- **Corpus**: `reviews/*.json` at run time (115 F2b-candidate rows); every row carries the file's
  own sha256 so each classification can be re-checked from pinned bytes. Corpus drift t0→t1: none.

## Counts (rules fixed in `PRE_REGISTRATION.md` before execution)

| rule | meaning | reviewers | n |
|---|---|---:|---:|
| **S (controller scan, re-implemented)** | accept + full-flag ≠ false + declared pin prefix-matches live | worker-052, worker-071, worker-090 | 3 |
| **S + self-superseded accept** | S plus reviewers whose own `revision_history` records a prior accept at this pin | worker-052, worker-071, **worker-072**, worker-090 | **4** |
| **B (strict binding)** | accept + exact live pin + explicit full-schema claim + reviewer-latest + no blocking failure | worker-071 | 1 |
| **B sensitivity** | B with "latest" over full-schema rows only | worker-071, worker-090 | 2 |
| **B2 (defect-aware)** | B rows whose own text addresses W075R-D1/D2 | — | **0** |
| **L (revise-live)** | revise at an exact/prefix-bound live pin | 017, 018, 029, 035, 041, 053, 066, 072, 075, 085, 090 | 11 |

Rule S + self-supersession reproduces the controller's historical accept set
**{052, 071, 072, 090} exactly**, so the scan was not wrong at scan time. Rule L contains all
seven reviewers the formulation lead counted as revise (066, 035, 017, 075, 018, 053 — plus 072).

## Adjudication of CF-31

The two published counts are not competing measurements of the same files; they diverge by
timing and by scope convention, and both are reproducible from bytes:

1. **Timing.** `reviews/F2b-review-worker-072-rev29.json` self-superseded accept→revise at
   `2026-09-12T01:14:51+08:00` (recorded in its own `revision_history`; note: the accept
   instrument had no internal cross-field consistency test, and
   `W072-F2B-INTERNAL-CONSISTENCY-01` then confirmed D1/D2). The pass-08 scan predates the flip,
   so it saw 4; the live scan sees 3.
2. **Scope convention.** `reviews/F2b-review-rev13-052.json` is a 56/56-check, 10-axis,
   blind, non-author review explicitly bound to the FROZEN rev29 bytes
   (`card_pin_note`, `reviewed_path`, `reviewed_bytes`), but it carries **no**
   `counts_as_full_schema_verdict` flag. The controller scan defaults an absent flag to full and
   counts it; a strict rule requires the explicit claim and does not. This single default is the
   difference between the scan's count and the strict count.
3. **Disjoint sets.** The scan's accepts and the lead's revises are disjoint reviewer sets
   ({052,071,072,090} vs {066,035,017,075,018,053,...}), not two verdicts on the same files.
4. **Defect coverage (the substantive result).** None of the live accepts addresses the confirmed
   internal contradictions W075R-D1 (`implication_ledger.forbidden_transfers[*].reason`:
   "C2 is a strictly larger extension class" vs line 239's containment chain) or W075R-D2
   (`regularity.must_not_conflate[0]`: "No containment with C2 or C0 is asserted here").
   `F2b-review-rev13-052.json` mentions `must_not_conflate` only as a positive property;
   071 and 090 do not mention either carrier. Rule B2 = **0**. So while 1–2 strict full-schema
   accepts exist at the exact live bytes, **no accept binds those bytes as defect-free**.

Conclusion (measurement, not a gate verdict): coverage counts at `b2ab6acb2bbe` cannot support
G-FORM movement. The count divergence is resolved in favour of a *timing + scope* explanation,
and the operative blocker is the unaddressed D1/D2 content defect, which rev14 is chartered to
fold. This is consistent with the G-FORM unmet text ("No gate movement on counts alone") and
supplies the per-file table it asks for, without superseding the lead-audit's binding-table task
`astra-life05-verify-gform-r3`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-013/f2b_binding_census/census_f2b_binding.py
# printout: live b2ab6acb2bbe..., frozen_match=true, rows=N,
#           rule_S=[052,071,090], rule_S_hist=[052,071,072,090], rule_B=[071],
#           rule_B2=[], rule_L_n=11, corpus_drift=[]
```

Outputs: `binding_table.json` (per-row), `report.json` (counts + adjudication + drift),
`corpus_snapshot_t0.json` / `corpus_snapshot_t1.json`.

## Artifact hashes (sha256, full)

| artifact | sha256 |
|---|---|
| `PRE_REGISTRATION.md` | `823cd14ca6b7e0f9314555360001229472fe6c0a98a16a9b819c9eb7badaa781` |
| `census_f2b_binding.py` | `b1349db8245ede06455600f8a8253918e1a5c3c22de4b10b53bbb701fde3706c` |
| `binding_table.json` | `8a4b6f9769a2065d354f125ee54e4b56b70a883148f9ac2a3cff13137cf92e0b` |
| `report.json` | `aee89e6047bec14b2f561733ed14b136d66f02f0e0b74d89b1c1b9e05b92bc58` |
| `corpus_snapshot_t0.json` | `a78ca770861f02b2ab7945f32f30ec8b843fc4c2cdc7c11588fd426ec7458dc7` |
| `corpus_snapshot_t1.json` | `a78ca770861f02b2ab7945f32f30ec8b843fc4c2cdc7c11588fd426ec7458dc7` (identical to t0; no drift during the run) |

## Corrections made before publication (self-caught, rules unchanged)

- `rule_B2` was first implemented reviewer-scoped; inspection showed a carrier mention in a
  different file by the same reviewer could transfer. Fixed to row-scoped. Details in
  `report.json.corrections_after_inspection`.
- Rule B's `reviewer_latest` flag marks worker-090's full accept superseded by a later
  **A1-scoped** detector-pin file that merely cites the F2b pin; the sensitivity row reports the
  alternative without altering Rule B.

## Falsifier

Re-run `census_f2b_binding.py` at the cited pins: any rule count differing from `report.json`,
any Rule S accept whose declared hash differs from the live schema hash, any row changing on a
re-read of the same bytes, or unreported t0/t1 drift flips this census.
