# W033-F2B-COVERAGE-ADJUDICATION-01

Bounded, read-only worker task by `worker-033` on class `AF-SCC-C0-VAC-GEN` (node F2b,
gate routing G-FORM, review gate G-AUDIT). It adjudicates **CF-31**: the divergence between
the published G-FORM F2b review-coverage counts at canonical hash
`b2ab6acb2bbe…b4501c` (FROZEN rev29 `815e08079aef`).

Worker-level bookkeeping measurement only. **No gate verdict, no node completion, no write to
any canonical schema, review file, detector, map, or inbound channel.**

## Question

Four F2b coverage counts were in circulation for the same hash:

| source | count |
|---|---|
| CF-31 finding text | 4 accepts: worker-052, worker-071, worker-072, worker-090 |
| `controller_gate_audit.G-FORM` at 01:16:26 | 3 accepts: worker-052, worker-071, worker-090 |
| formulation lead (lead-form-20260912T0113-107, repeated in CF-31) | 0 accept / 7 revise |
| worker-048 W048-GFORM-COVERAGE-RECOUNT-01 | 2 accepts: worker-090, worker-072 |

Which, if any, is reproducible from the bytes?

## Method

`f2b_coverage_adjudication.py` freezes the live `reviews/*.json` corpus (239 files), a
review-event slice of `research_map/events.jsonl` (455 events), the FROZEN manifest, the
controller sources and the published evidence into `pinned/`, then measures **only from the
frozen copy**:

1. **file channel** — every review record whose explicit pin field
   (`artifact_sha256`/`reviewed_sha256`/`sha256`/`cited_sha256`, incl. nested pins) binds the
   F2b hash, with reviewer, verdict, flags, availability mtime, in-place-amendment delta and
   independence facts;
2. **controller scan** — an exact re-implementation of
   `astra_lifecycle.review_coverage()` (target aliases, 12-hex prefix pin rule);
3. **lead method** — the lead's stated rule ("every `reviews/*.json`; verdict counted only when
   `artifact_sha256`/`reviewed_sha256` starts with the live hash") in five variants
   (live/stale corpus × literal/target-filtered keys);
4. **event channel** — accepted-stream review events binding the F2b hash, with
   same-reviewer/later-verdict supersession;
5. **temporal grid** and the implied stale-corpus window.

Fail-closed synthetic mutation controls: `controls.json` (15/15 PASS). Corpus integrity checks:
`report.json` `integrity_checks` (IC-01…IC-07, all PASS). `verify` mode recomputes the payload
digest from the pinned bytes and matches the recorded digest.

## Result (freeze `W033-F2B-COV-20260912T012215p0800`, 2026-09-12T01:22:15+08:00)

- **Reproducible file-channel count: 3 full-schema hash-bound accepts**
  `worker-052` (`reviews/F2b-review-rev13-052.json`), `worker-071`
  (`reviews/F2b-review-rev13-worker-071.json`), `worker-090`
  (`reviews/F2b-rev13-full-090.json`); 12 bound revise records; all three accept pins are
  exact-64 (no accept binds only by the 12-hex prefix rule).
- **Controller scan reproduces the same 3** (052, 071, 090) at the frozen bytes — matching the
  map reason at 01:16:26.
- **CF-31's 4-count was correct only before 01:14:54**: `worker-072`'s accept
  (`w072-2026-09-12T01:10:13+08:00-review-f2b`) was amended in place to revise at
  `F2b-review-worker-072-rev29.json` mtime 01:14:54, self-superseded by event
  `w072-f2b-selfsupersede-review-20260912T011524` at 01:15:24.
- **The lead's 0 accept / 7 revise is not reproducible at its stated live 01:10 measurement.**
  `worker-090`'s accept file (mtime 01:08:56, exact-64 pin) already existed. The published
  7-revise set is reproduced *exactly* only by restricting the corpus to records available
  before the first accept: implied boundary interval
  `(2026-09-12T01:05:46+08:00, 2026-09-12T01:08:56+08:00]` — i.e. a pre-01:08 corpus snapshot
  mislabelled as live. No single pin key explains the 7 set either
  (`artifact_sha256`-only 5/7, `reviewed_sha256`-only 6/7).
- **Independent cross-check:** worker-017's concurrently written CF-31 binding table (pinned in
  this freeze) reports the same live accept set {052, 071, 090}.

Adjudication (worker level, verdict `revise`, score 2.5): at the frozen hash the reproducible
coverage is **3 full-schema accepts / 12 revise**; the lead's 0/7 must not be used as the live
F2b count, and any count must name its instant and binding rule because review files are
rewritten under fixed names. Coverage ≥ 2 is met at the file channel, but **this does not move
G-FORM**: the lead's own measurement_5 confirms two internal content defects in the same F2b
bytes (D1 containment denial line 152 vs line 239; D2 "C2 strictly larger" inversion line 246),
and independence/blind sufficiency (worker-090 blind=false with disclosure; worker-052
`reviewer_is_author` flag and absent full-schema flag; worker-071 explicit independence) is the
audit lead's ruling, not this instrument's.

## Files

| file | content |
|---|---|
| `f2b_coverage_adjudication.py` | instrument (`freeze`/`run`/`verify`/`controls`) |
| `report.json` | full payload + `payload_digest` |
| `binding_table.csv` | per-file table for all 239 review records |
| `reconciliation.json` | published counts vs measured, stale window, cross-check |
| `review.json` | exactly one verdict (`revise`) with findings + falsifier |
| `controls.json` | 15 fail-closed mutation controls |
| `pinned/` | frozen reviews corpus, event slice, `MANIFEST.json`, `freeze.json` |
| `SHA256SUMS` | artifact hashes |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-033/f2b_coverage_adjudication/f2b_coverage_adjudication.py controls
python3 artifacts/worker-033/f2b_coverage_adjudication/f2b_coverage_adjudication.py verify
# optional re-freeze against a later corpus: ... freeze && ... run
```

## Falsifier

Re-run the instrument on the pinned snapshot. The adjudication is falsified if any of: the
three accept files' pin fields do not equal `b2ab6acb2bbe…`; worker-090/071/052 did not exist
at their recorded mtimes; the lead's 7-revise set is not exactly the F2b records available
≤ 01:05:46 (or equality also holds at a post-01:08:56 boundary); a later same-reviewer F2b
verdict supersedes 052/071/090; the live F2b/FROZEN hashes differ from the pinned constants; or
the controller-scan reproduction disagrees with `astra_lifecycle.review_coverage()` at the
pinned source hash.
