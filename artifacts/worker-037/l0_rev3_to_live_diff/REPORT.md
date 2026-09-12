# W037-L0-REVDIFF-01 / W037-L0-CONTENT-BAR-01 — independent L0 reconciliation evidence

**Worker** `worker-037` (bounded execution worker, fleet instance `worker-037-20260912T003532-968807`).
**Node** L0 · **Gate** G-LIT · **Classes** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.
**Authority**: worker measurement only. No gate verdict, no node status, no ledger write, no
canonical artifact edited. Emitted so the controller/literature lead can adjudicate REC-10 (CF-19)
from bytes rather than prose.

Trigger: controller pass-04 ruling **REC-10 / CF-19** — the live `ledger/theorems.jsonl` measured
`a1674f094979` after the announced L4 exit hash `3e3d35531421`, with no artifact event at the time.
REC-10 asks the owner to adopt the live bytes *with a content-preservation/claim-lowering diff*, or
publish the intended revision back. This directory supplies that diff plus an independent check of
the content bar behind the new `content_status` tokens.

## Pinned inputs (measured 2026-09-12T00:50+08:00, stable across the run)

| path | sha256 (16) | role |
|---|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cf` | live canonical (candidate rev3) |
| `artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl` | `3e3d35531421388a` | announced L4 exit (interim hand-patch) |
| `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e7617e3a` | pre-rev3 lineage |
| `artifacts/literature/tools/build_literature.py` | (pinned in `content_bar_report.json`) | bar definition |
| `artifacts/literature/sources/batch-*.jsonl` + `registry.jsonl` | 97 sources, 0 registry/batch conflicts | bar inputs |

Reproduce:

```bash
python3 artifacts/worker-037/l0_rev3_to_live_diff/diff_l0_revisions.py --now <ISO> --out /tmp/diff.json
python3 artifacts/worker-037/l0_rev3_to_live_diff/verify_content_bar.py --now <ISO> --out /tmp/bar.json
```

Both scripts are deterministic (fixed `--now` replays are byte-identical) and read-only.

## 1. Diff against the announced exit (`3e3d3553` → `a1674f09`)

`diff_report.json#7671f999be9c`:

- **62/62 rows compared, 0 content-key changes.** Every `statement_exact`, `class_ids`,
  `conclusion_type`, `entry_kind`, `evidence_level`, `regularity`, `topology`, `genericity`,
  `assumptions`, `falsifiers`, `scope_caveats`, `source_ids`, `unresolved`, `review_status`,
  `acceptance_authority`, `verification_status`, `next_action` is unchanged row-for-row.
- **62/62 rows changed only in the claim-status family.** The four archive keys
  `status` / `status_note` / `supports_claim` / `supports_claim_basis` are replaced by
  `content_status` / `author_asserts_supports` (HF-14 guard: no row carries `status`,
  `validation_status` or `supports_claim` any more).
- **Token direction against this baseline is strengthening, not lowering**: 50 rows map
  `included_unreviewed → verified`; 60 rows map `supports_claim: null → author_asserts_supports: true`
  (the other 2 stay `false → false`). Under the pre-registered strength order this fails the strict
  "claim-lowering" test (`R3`/`R4` false), and 50 rows show `content_status: verified` while
  `review_status: not_independently_reviewed` and `verification_status: abstract-read` (`R5` false).
- Per class (rows per class assignment; rows with several classes are counted once per class):
  `AF-WCC-VAC-GEN` 11, `AF-SCC-C0-VAC-GEN` 11, `AF-SCC-C2-VAC-GEN` 10, `AF-WCC-SCALAR-SPH` 10,
  28 rows carry no frozen class token.

**Lineage context matters for this reading.** The pre-rev3 bytes (`ce42d205`) carried
`status: accepted` (50) with `supports_claim: true` (60). The interim hand-patch (`3e3d3553`) was a
safety stopgap that collapsed those to `included_unreviewed` / `null`. The live bytes restore the
old *content* tier as `content_status: verified` **and** record the review axis separately and
truthfully as `not_independently_reviewed`. So:

- against the **announced exit** (REC-10's requested baseline): token-level strengthening, explained;
- against the **pre-rev3 lineage**: an axis split (accepted → content-verified + review-unreviewed),
  not an increase in the total claim.

The lead's §10 mapping narrative ("`accepted`→`verified` on the 9 build inputs", 62 rows) is
consistent with the bytes measured here; the `included_unreviewed` token in the announced exit was
the interim stopgap, not the build-input vocabulary.

## 2. Is the new `verified` token earned? (`content_bar_report.json#2ba1d3d1c290`)

The bar quoted from `build_literature.py`: `content_status=verified` requires (B1) non-empty
`source_ids`, (B2) every cited source in `{verified-primary, verified-api}`, (B3) at least one cited
source with `evidence_type != metadata`, (B4) `author_asserts_supports is True`.

Result on the live bytes: **50/50 verified rows satisfy B1–B4; 0 violations**; no unknown source
ids; no `sources/batch-*` vs `registry.jsonl` status/evidence-type conflicts across 97 sources.
Controls CTL-1…CTL-5 pass (bar-pass fixture; metadata-only fails B3; missing author assertion fails
B4; unknown source fails B2; conflict detector wired).

Fragility/limits recorded, not hidden:

- 39 of the 50 rows rest on **abstract-only** evidence (`evidence_type: abstract`); 0 use the single
  `full-text` source.
- 10 rows rest on a **single** cited source (`T-104, T-202, T-203, T-205, T-207, T-303, T-503,
  T-512, D-008, T-522`).
- All 50 remain `verification_status: abstract-read`, and the source status/evidence fields are
  maintainer assertions from the same pipeline: passing the bar is **internal consistency with the
  documented predicate, not independent evidence of support**. Independent re-fetch evidence for
  L1 (97/97 rows) is separate and untouched (`315c19145065` unchanged). This matches REC-5's
  abstract-level sufficiency reading.

## 3. Findings for adjudication

1. **Content preservation: PASS.** No statement, class binding, conclusion type, evidence level or
   source list changed between the announced exit and the live bytes.
2. **Claim-lowering relative to the announced exit: FAIL at token level, explained.** The
   strengthening `included_unreviewed → verified` is the stopgap being superseded by the durable
   two-axis model; it is documented (`L0-rev3-adjudication-20260912T0035.md`,
   `rev3-axis-split.json`) and the review axis is now explicit.
3. **Content bar: PASS mechanically** (50/50), with the evidence-depth caveats above.
4. **Residual token hazard (non-blocking, documentation).** `content_status: verified` coexists on
   the same rows with `verification_status: abstract-read` and `review_status:
   not_independently_reviewed`. A reader scanning only `content_status` can over-read it. If a
   post-verdict metadata patch is authorized (REC-4 territory), a non-certifying token
   (`author_assessed` / `content_checked`) would remove the collision without moving any claim.
   This is a naming recommendation, not a blocker for adopting the live bytes for review.
5. **Baseline for the blind L0 review is the live hash `a1674f094979`**, as the lead's checkpoint-08
   blocker and REC-10 already state; verdicts bound to `3e3d3553` or `ce42d205` do not transfer.

## 4. Falsifiers and supersession

- If `ledger/theorems.jsonl` is not `a1674f094979` at review time, both reports are superseded and
  must be re-run (hashes are re-measured T0/T1 inside each report; drift within run was 0).
- If any content key differs row-for-row between the two revisions, finding 1 is falsified for that
  row (the report lists the exact witness keys).
- If any `content_status: verified` row lacks a verified non-metadata source or
  `author_asserts_supports != true`, finding 3 is falsified for that row.
- If a cited source's status differs between `sources/batch-*.jsonl` and `registry.jsonl`, the
  source-of-truth map is ambiguous for that id (currently 0 such conflicts).
