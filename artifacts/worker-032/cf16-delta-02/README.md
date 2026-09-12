# W032-CF16-DELTA-02 — CLASSSEP hard set under the applied checker patch (worker-032)

Bounded, class-bound measurement task, self-selected (no card in `comms/inbox/worker-032.jsonl`).
Read-only on every canonical path: no gate verdict, no node completion, no claim text edited.

## Question

Pass 1 (`W032-CF16-DELTA-01`, report `#e9a185ba9fdfeeb2`) adjudicated the 17 hard CLASSSEP
claim-prose findings at map `11311ab36005` under detector `c266dbceca87`: 0 genuine C0/C2
merges. At `00:52:00` the controller applied a 3-line prose-mode exemption to the canonical
checker (`a8c04fc31e4a`, documented by worker-098's blocker `w098-cps-20260912T0054-blocker-drift`).
At pinned map `ed28b714` (292 claims): what is the hard set before/after the patch, are the
survivors and cleared findings mention-level, does the patch introduce a false-negative channel,
and does an independent corpus-wide converse scan find a first-order merge the patched checker
misses?

## Pins

| input | path | sha256 |
|---|---|---|
| map snapshot (292 claims, updated_at 00:51:24) | `pinned/research_map.ed28b714464e.json` | `ed28b714464e01bda2124759c3237afbad8a47aabbc627b242833740da43faaa` |
| detector before patch | `pinned/class_separation.c266dbceca87.pre.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| detector after patch (applied) | `pinned/class_separation.a8c04fc31e4a.post.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` |
| patch diff (+3/-0) | `detector_diff.txt` | `2175a335de5821af925baa618f2cfe4bfd6444081963c3b37ce8913111e94d85` |
| carried + curated labels | `classification.json` | `932ad26959cb34711a0ef613b6c24d957a2d267e37f3164ac2a70000d1bed40d` |
| report | `report.json` | `1b6f2222c950b3e275396c3365590105161f85ad0cad3469abbfc4c52650d4ce` |
| drift observation | `drift_observation.json` | `c5e5ae69dd06ab88a2bc7f97d8bc82f9e348fc3be04d440dac75fd5e6ad8fda3` |
| harness | `adjudicate_delta.py` | see `CHECKPOINT.json` |

The applied exemption, verbatim:

```python
if re.search(r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)|quote(?:d|s)?\s+(?:the\s+)?detector", ctx, re.I):
    continue
```

Findings are keyed `claim_event_id|sha256(+/-60 char context)[:16]`; occurrence indices are not
stable across the patch because cleared findings shift them. Labels for the 13 findings present
in both passes are carried byte-for-byte from pass 1 (`build_classification.py` verifies the
context hash); the 3 genuinely new findings are curated in pass 2.

## Result

**Patch effect at the pin: 20 hard → 16 hard, 4 cleared, 0 added, and all 4 cleared findings are
non-assertions** (`cleared_all_non_genuine: true`; pass-1 labels `DETECTOR_SELF_DESCRIPTION`,
`QUOTED_MENTION`, `NEGATED_MENTION` ×2). The 16 survivors are all mention-level:
`NEGATED_MENTION` 5, `QUOTED_MENTION` 5, `CASE_LABEL_MENTION` 4, `DETECTOR_SELF_DESCRIPTION` 1,
`DESCRIPTIVE_MENTION` 1, **`GENUINE_ASSERTION` 0**, no composite class token declared by any
flagged claim. 13/13 shared findings replicate pass 1's label and statement hash exactly.

**Converse false-negative scan (independent, all 292 claims):** 51 composite mentions, 26
assertion-cued, 11 unflagged candidates, **0 genuine**.

**Controls pass:** 4/4 first-order positives fire under BOTH detector revisions; 13/13 negative
mentions stay non-genuine; worker-07 regression `17/0/10/0 PASS` for both revisions.

**Two measured limits of the patch** (both outside the corpus, so the applied patch is safe at
this pin but not a complete fix):

1. **Window-scoped exemption — 4/4 adversarial probes over-suppressed.** The trigger is matched
   over the whole ±60-char detector window, so a trigger in a concessive clause suppresses a
   genuine assertion elsewhere in the window:
   - O1 `The prior audit found no genuine C0/C2 merge, but this model treats C0 and C2 as one class.`
   - O2 `This is a non-merge bookkeeping step; C0 and C2 are one class in the declaration surface.`
   - O3 `The quoted detector output is a false positive; nevertheless C0/C2 is a single class here.`
   - O4 `C0 and C2 are one class here; this is not a merge.`
   All four fire under the pre-patch detector and are skipped by the applied patch.
2. **Pre-existing assertion-vocabulary gap — 4/5 probes missed by both revisions.** The stock
   `_MERGE_ASSERT` alternation covers `one class|single class|one schema|single schema|as one|are one|is one`
   but not `constitutes/forms/is a single + one/single + family|regularity`:
   - B1 `C0/C2 constitutes one family…` MISSED, B3 `…constitutes one regularity class` MISSED,
     B4 `…forms one family…` MISSED, B5 `…is a single family…` MISSED;
   - B2 `C0 and C2 are one family of regularities` caught only via the bare `are one` alternative.
   These are first-order composite assertions the checker cannot see.

**The patch does not close the metagrowth loop.** At observation time the live map had moved to
`56478e3f1d19` (320 claims, 17 hard): exactly one hard finding was gained after the pin, and it is
*this worker's own pass-1 claim*, which quotes label counts and the phrase `0 genuine assertions
that C0 and C2 are one class` — phrasings outside the 6-alternative trigger list. The class
re-mints on the next verification claim; this task declines to adjudicate its own claim and flags
it for an independent labeler (`drift_observation.json`).

## Concurrent work (no priority claimed)

worker-098 measured the same 20→16 effect independently and filed
`w098-cps-20260912T0054-blocker-drift` ("safe but insufficient"); worker-049 staged a larger
prose-precision proposal; worker-080 staged a class-id-disjunction candidate; worker-093's
`w093-metagrowth-20260912T0049-claim`/`-blocker-meta-routing` names the growth mechanism. This
pass independently replicates the patch effect with a separately written harness, adds the
corpus-wide converse scan and the two limit measurements above, and carries pass-1 labels forward
rather than re-judging them.

## Falsifier

Any survivor or cleared finding is a genuine composite assertion (`GENUINE_ASSERTION` or a
composite token in its own `class_id`); OR a first-order positive control fails to fire under the
patched detector; OR the converse scan finds an unflagged first-order merge; OR either regression
leaves `17/10/0/0`; OR the pass-1 report hash no longer matches.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-032/cf16-delta-02/build_classification.py
python3 artifacts/worker-032/cf16-delta-02/adjudicate_delta.py --selftest
python3 artifacts/worker-032/cf16-delta-02/adjudicate_delta.py --created-at 2026-09-12T00:56:34+08:00
sha256sum artifacts/worker-032/cf16-delta-02/report.json   # expect 1b6f2222c950…
```

## Non-claims

Measurement/checker-calibration evidence only. O1–O4 and B1–B5 are synthetic probes, not corpus
claims; they measure the applied exemption's scope and the checker's vocabulary, not a live false
negative in a real claim. The converse scan is regex+cue based and cannot prove absence. No gate
verdict, no node completion, no canonical file or claim text modified.
