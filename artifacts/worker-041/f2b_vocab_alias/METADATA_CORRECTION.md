# W041-F2B-VOCAB-ALIAS-01 — self-caught metadata correction

- Measured write window (this file): 2026-09-12T01:17:50.190231+08:00
- Defect: `reviews/F2b-vocab-alias-041.json` carries internal `created_at` = `2026-09-12T01:26:00+08:00`, ~8.5 minutes FUTURE-DATED relative to its measured write window (`2026-09-12T01:17:2x+08:00`, instance start `01:11:43`). Cause: a projected timestamp was typed into the verdict template instead of measuring the clock.
- Scope: timestamp metadata only. No measurement, pin, check, verdict, score, finding, evidence ref, or the reviewed sha256 `b2ab6acb2bbe...` is affected. The alias adjudication in `report.json` and the review event `w041-f2bvocab-20260912T0126-review` (created_at `2026-09-12T01:17:21+08:00`) are unaffected.
- Deliberately NOT rewritten: the review file's sha256 `d24fec07c87cfbf4...` is cited by the two already-ingested events `w041-f2bvocab-20260912T0126-artifact-report` and `w041-f2bvocab-20260912T0126-review`; editing the bytes would dangle those accepted-stream evidence refs and trip the artifact-hash audit. Bytes stay frozen; this note is the record.
- Next authorized editor of that file: correct `created_at` to the measured write window and re-pin the review hash through the normal revision route, never by in-place edit under a live citation.
