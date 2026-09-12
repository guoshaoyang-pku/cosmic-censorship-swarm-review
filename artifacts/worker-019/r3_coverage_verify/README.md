# W019-GFORM-R3-VERIFY-01 — independent verification of the G-FORM r3 coverage adjudication

- **Node / gate:** F1, F2a, F2b / G-FORM (bounded independent measurement; no gate or node verdict claimed)
- **Actor:** worker-019 (self-selected; no assignment card existed in `comms/inbox/worker-019.jsonl`)
- **Object under test:** `reviews/G-FORM-final-verify-r3.json` @ `d94dd2d5b778` — the audit lead's CF-31
  coverage adjudication required by REC-39 (`astra-life05-verify-gform-r3`)
- **Pins re-measured at entry:** `artifacts/formulation/FROZEN.json` @ `815e08079aef`;
  `schemas/af_wcc_vacuum.yaml` @ `d9cebb9404b2`; `schemas/af_scc_c2_vacuum.yaml` @ `e9a27996dfd3`;
  `schemas/af_scc_c0_vacuum.yaml` @ `b2ab6acb2bbe`; `schemas/f1_falsifier_tests.jsonl` @ `56bcb4b3234b`;
  `artifacts/worker-066/f2b_accept_disposition/report.json` @ `a82623db025e`
- **Result artifact (machine):** `artifacts/worker-019/r3_coverage_verify/results.json` @ `0aa1ae695028`
  (self-digest `1ec4961950ae`, computed over the canonical payload excluding `run_at`)
- **Instrument:** `artifacts/worker-019/r3_coverage_verify/verify_r3_coverage.py` @ `b7b0c041a2fe`
- **Stream snapshot:** `research_map/events.jsonl` @ `102265f794059` (8 122 events, read once, append-only)

## Verdict

**revise, score 4.0 — one hash-bound hard failure (W019-R3-01), four findings.**
r3's overall direction (G-FORM NOT proposable at FROZEN rev29) is **corroborated** by every atomic fact
checked here; the hard failure concerns one basis sentence in the F2b section, not the adjudicated verdict.

## Check table

| # | check | status | measured at verification time |
|---|---|---|---|
| C0 | pinned inputs re-measured | MATCH | all 7 pins equal their declared sha256 |
| C1 | r3's declared FROZEN/schema pins vs live bytes | MATCH | `815e08079aef` / `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` |
| C2 | 8 declared full accepts, event channel | MATCH | 8/8 events exist; verdict accept; full flag true; 0 hard failures |
| C2 | 8 declared full accepts, live files | MATCH | 8/8 clean accepts bind the class pins (hashes below) |
| C3 | worker-052 full-schema flag | **MISMATCH** | event `true`; live file has no `counts_as_full_schema_verdict` key |
| C4 | F2b carriers | MATCH | `:152` denial and `:246` inverted premise present at frozen bytes |
| C5 | worker-072 self-supersede | MATCH | F2b accept 01:10:13 → revise 01:15:24, both binding `b2ab6acb2bbe` |
| C6 | worker-066 SILENT basis | **MISMATCH** | worker-052 is `AFFIRMATIVE_PASS_UNDISPOSED` on both carriers; `clean_accept_count=0` |
| C7 | F1 falsifier-corpus rebinding | MATCH | 25/25 rows bind rev12 `cce9c60146d6`; 0 bind frozen rev13 |
| C8 | F2a extension-category asymmetry | MATCH | F2a `extension_topology` lacks SMOOTH and has no `iota_regularity`; F2b has both |
| C9 | r3 aggregate counts reproducible | **MISMATCH** | none of live-strict / live-loose / event-pin-anywhere matches the declared triples |
| C10 | declared full-accept sets still live | **STALE** | F2a live full set is now 4 (worker-085, 01:19:45) vs r3's 3 |

## Findings

- **W019-R3-01 (hard).** r3's F2b `verdict_basis` says "accepting verdicts are measured SILENT on them
  (worker-066)". Worker-066's report classifies worker-052's live accept as
  `AFFIRMATIVE_PASS_UNDISPOSED` on both carriers (only worker-090 and worker-071 are SILENT). The
  operative measured fact is `clean_accept_count=0` — no accept disposes a carrier — which still
  supports the adjudicated `revise`; the basis sentence needs qualification.
- **W019-R3-02.** Worker-052's F2b accept **event** carries `counts_as_full_schema_verdict=true`; the
  live `reviews/F2b-review-rev13-052.json` (`c3f720292e47`) has no such key. r3's `full_schema: true`
  for that entry is verifiable from the event record only, not from the artifact it names. Any
  file-based coverage scan (e.g. worker-048's F2b = 2 full accepts) will therefore disagree with the
  event-based count (3).
- **W019-R3-07.** r3 declares aggregate `non_author_accepts_all` / `revises` (11/12, 8/12, 9/37)
  without stating their predicate. Three explicitly named rules applied to the live corpus at the same
  pins (live-strict primary binding, live-loose string binding, event-pin-anywhere) reproduce none of
  the three triples; only the per-class **full-accept sets** (2/3/3) are independently verified.
- **W019-R3-08 (staleness).** r3 is a point-in-time census (`created_at 01:18:00`). By 01:42 the F2a
  full-accept set has grown to 4 (`reviews/F2a-review-rev29-085.json` @ `b86ce67c4c0b`, event
  01:19:45, full flag true, 0 hard failures). REC-39's own rule applies: re-measure coverage from
  disk at use time. At rev30 every verdict is void anyway (REC-36).

## Verified live-file bindings (C2)

| class | reviewer | file | sha256 | full flag |
|---|---|---|---|---|
| F1 | worker-072 | `reviews/F1-review-worker-072-rev13.json` | `c656cc819381` | true |
| F1 | worker-075 | `reviews/F1-review-rev29-075.json` | `9276f4b41547` | true |
| F2a | worker-017 | `reviews/F2a-review-worker-017.json` | `61cbd185f982` | true |
| F2a | worker-072 | `reviews/F2a-review-worker-072-rev13.json` | `b7996e93e624` | true |
| F2a | worker-018 | `reviews/F2a-review-18-rev13.json` | `53ed7b7ab385` | true |
| F2b | worker-090 | `reviews/F2b-rev13-full-090.json` | `345f74bb73f4` | true |
| F2b | worker-071 | `reviews/F2b-review-rev13-worker-071.json` | `e5a313894f7c` | true |
| F2b | worker-052 | `reviews/F2b-review-rev13-052.json` | `c3f720292e47` | **key absent** |

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-019/r3_coverage_verify/verify_r3_coverage.py
# exit 0; results.json self_digest 1ec4961950ae; exit 2 (no output) if any pinned input moved
```

Live review-file states are cited at their measured sha256 and are expected to move; the pinned
inputs (r3, FROZEN, schemas, corpus, worker-066 report) are not.

## Falsifier

Any byte change of a pinned input voids this verification. Re-running the instrument and finding a
MATCH where this report records MISMATCH/STALE, or a changed value in C2–C10, falsifies the
corresponding finding. In particular: W019-R3-01 clears if worker-066's report is corrected or r3's
basis sentence is qualified; W019-R3-02 clears if the worker-052 file is regenerated with the flag or
r3 records the event-only provenance; C10 goes MATCH only if the live corpus returns to r3's declared
sets (which rev14 will not do — byte move voids every verdict).

## Not claimed

Gate verdict, node status, `validation_status`, re-adjudication of F1/F2a/F2b class semantics,
reproduction of r3's unstated aggregate-count predicate, and any mathematical or physical statement.
The F2b/F2a adjudicated direction is corroborated, not certified: worker events cannot move a gate.
