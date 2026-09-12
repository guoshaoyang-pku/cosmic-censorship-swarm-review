# W054-GFORM-LIVE-ACCEPT-CENSUS-01 (read-only worker measurement)

Frozen at 2026-09-12T01:23:00+08:00; pins: F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, FROZEN rev29 `815e08079aef`.

## Counted live full-schema accepts per leg

| leg | live+accept (any full) | strict full | strict full + live FROZEN | strict full + live FROZEN + non-author | live revise |
|---|---:|---:|---:|---:|---:|
| F1 | 7 | 2 | 2 | 2 | 7 |
| F2a | 4 | 4 | 2 | 2 | 4 |
| F2b | 4 | 2 | 2 | 2 | 13 |

Counts are machine measurements under the pre-registered rules in `report.json.rules`; they are not gate verdicts and do not adjudicate which verdicts are correct.

### F1 — live-bound accept files

- `reviews/F1-review-011-rev13-visibility-repair.json` reviewer=worker-011 full=false frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T01:04:02+08:00)
- `reviews/F1-review-rev13-052.json` reviewer=worker-052 full=absent frozen_live=True frozen_genA=False nonauthor=True blind=True stale=[] (2026-09-12T01:03:00+08:00)
- `reviews/F1-review-rev13-085.json` reviewer=worker-085 full=absent frozen_live=True frozen_genA=True nonauthor=True blind=None stale=[] ()
- `reviews/F1-review-rev29-075.json` reviewer=worker-075 full=true frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T01:03:36+08:00)
- `reviews/F1-review-worker-072-rev13.json` reviewer=worker-072 full=true frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T01:01:14+08:00)
- `reviews/F1-review-worker-089.json` reviewer=worker-089 full=absent frozen_live=True frozen_genA=True nonauthor=True blind=None stale=[] (2026-09-12T01:00:42+08:00)
- `reviews/G-FORM-visdir-residual-086.json` reviewer=worker-086 full=false frozen_live=True frozen_genA=False nonauthor=True blind=None stale=['9dc536368aea22cdc56f57948814562f61cf2e4791274c9fade50f8ddb4f3c58'] (2026-09-12T01:00:38+08:00)

### F2a — live-bound accept files

- `reviews/F2a-review-18-rev13.json` reviewer=worker-018 full=true frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T01:10:43+08:00)
- `reviews/F2a-review-rev29-085.json` reviewer=worker-085 full=true frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] ()
- `reviews/F2a-review-worker-017.json` reviewer=worker-017 full=true frozen_live=False frozen_genA=True nonauthor=True blind=No F2a verdict content was read before this file was written. Exposure was limited to (a) the controller's aggregate gate-reason sentence at research_map.json#controller_gate_audit, (b) filenames under reviews/ that contain the target token, and (c) the formulation lead's L-FORM-02 blocker text, which is an author-side finding, not a reviewer verdict. stale=[] (2026-09-12T00:57:30+08:00)
- `reviews/F2a-review-worker-072-rev13.json` reviewer=worker-072 full=true frozen_live=False frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T00:55:52+08:00)

### F2b — live-bound accept files

- `reviews/F2b-remedy-crossverify-worker-100.json` reviewer=worker-100 full=false frozen_live=True frozen_genA=False nonauthor=True blind=None stale=['9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17'] (2026-09-12T01:16:00+08:00)
- `reviews/F2b-rev13-full-090.json` reviewer=worker-090 full=true frozen_live=True frozen_genA=False nonauthor=True blind=False stale=[] (2026-09-12T01:08:56.691317+08:00)
- `reviews/F2b-review-rev13-052.json` reviewer=worker-052 full=absent frozen_live=True frozen_genA=False nonauthor=True blind=True stale=[] (2026-09-12T01:10:49+08:00)
- `reviews/F2b-review-rev13-worker-071.json` reviewer=worker-071 full=true frozen_live=True frozen_genA=False nonauthor=True blind=None stale=[] (2026-09-12T01:10:40+08:00)

## Live churn: worker-072 F2b self-supersession

`reviews/F2b-review-worker-072-rev29.json` current sha256 `5db91bb0781d`, verdict `revise`, supersedes accept `7487f310d208` at 2026-09-12T01:14:51+08:00; superseded bytes present in reviews/ = False. Hard failures: W072-F2B-HF-01, W072-F2B-HF-02.

## HF-059-FROZEN-01 check: F2a worker-017

`reviews/F2a-review-worker-017.json` sha256 `61cbd185f982`, verdict `accept`, reviewed_sha256==live F2a = True, declares FROZEN live = False, declares FROZEN genA = True, created_at 2026-09-12T00:57:30+08:00.

## Controls and drift

- controls all as declared: **True**
- drift detected during run: **False**
- review files added/removed while running: 0/0 
- files scanned: 230; in scope per leg: {'F1': 50, 'F2a': 27, 'F2b': 41}

## Non-claims

- No gate verdict, no node status, no `validation_status=passed`, no canonical file written, no repair adopted, no schema review verdict authored.
- Independence is the objective author-set test only; the audit lead owns the final independence/blind-status call, and the audit lead owns adjudication of competing revise verdicts.

Falsifier: Re-run checker.py at the recorded --created-at against an unchanged reviews/ tree. Falsified if any counted file changes classification at unchanged bytes, if the recorded per-file sha256 does not measure, if any control stops behaving as declared, or if any input hash differs from the recorded start/end pair. A later write to a review file is not a falsifier of the measurement at its recorded hash; it is a new revision to re-census.

