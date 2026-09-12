# W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01

Bounded class-bound task taken by `worker-048` (no inbox card existed). Scope:
G-FORM review coverage for **F1 / F2a / F2b**
(`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`).

Question: what exactly does the controller's `astra_lifecycle.review_coverage`
scan count as a hash-bound full accept, what does that rule silently drop on the
live review corpus, and what is the minimal unapplied patch that closes the gap?

## Method (read-only wrt every canonical path)

- Analysed pin: `research_map/astra_lifecycle.py#957c61e3eb0e` (pass-07 snapshot).
- The three functions `_targets_in_review`, `_explicit_pins`, `review_coverage`
  are extracted from the byte snapshot with `ast.get_source_segment` and
  executed against a controlled `ROOT`. The pinned bytes are tested, not a
  rewrite.
- A byte-frozen copy of the live `reviews/` corpus (`live_snapshot/`, digest
  `42e9cee5…`, 225 files) is analysed by three rules: **R1** = pinned rule,
  **R3** = the proposed patched rule extracted the same way from
  `proposed/astra_lifecycle.<pin>.patched.py`, and **R0** = the live instrument
  bytes, executed as a provenance check.
- An 18-case synthetic fixture corpus (`fixtures/`) reproduces every target/pin
  form actually present in the live corpus, with pre-registered expectations;
  11 controls include per-case mutation flips, negative controls (wrong pin,
  prose-only hash) and copy-fidelity/stability checks.
- Writes only under `artifacts/worker-048/gform_coverage_rule/` and
  `runtime/state/w048_*`. The patch is **not applied**; no `reviews/` file is
  written, so the audit does not perturb the corpus it measures.

## Result (frozen corpus `42e9cee5…`, 225 files)

| rule | F1 full accepts | F2a | F2b |
|---|---:|---:|---:|
| R1 pinned controller scan | 4 | 2 | 3 |
| R3 proposed | **5** | **3** | 3 |
| R0 live instrument | 4 | 2 | 3 |

Recovered by R3 (each genuinely binds the live schema sha256):

- `reviews/F1-review-worker-089.json` — `target_id` is
  `schemas/af_wcc_vacuum.yaml#d9cebb9404b2` plus a matching explicit
  `reviewed_sha256`; R1 never maps the path form to node `F1`.
- `reviews/F2a-review-18-rev13.json` — `target_id` is
  `schemas/af_scc_c2_vacuum.yaml#e9a27996…` with `artifact_sha256` equal to the
  live F2a bytes and `counts_as_full_schema_verdict: true`; R1 drops it for the
  same reason.

No lost accepts: R3 drops nothing R1 counted (control C5).

Live corpus census: 22 `path#hash` and 1 `node#hash` targets, 2 `node@hash`, 5
multi-target, 9 `class_id`-only targets, 7 dict-valued `reviewed_sha256`, 76
null pins, and **87 verdict files whose `counts_as_full_schema_verdict` is null**
(64 true, 52 false) — null is treated as **full** by both rules.

## Findings

- **W48-CR2-01 (hard, instrument).** The pinned scan undercounts: two live full
  accepts bind the live bytes only through a `path#hash` target or a dict pin.
  Both are recoverable with no semantic change to the gate criterion.
- **W48-CR2-02 (policy-open).** `counts_as_full_schema_verdict` absent/null is
  read as full (`is not False`), covering 87 of the 203 verdict files in the
  frozen corpus. The gate must decide opt-in vs opt-out before the count is
  decision-grade; the patch deliberately does not change this.
- **W48-CR2-03 (hard, instrument).** Coverage is computed from live bytes with
  no corpus digest carried into gate reasons; the corpus moved repeatedly during
  the preceding counts (F2b 0 → 2 → 3 within ~10 minutes; one new review file
  landed between two freezes of this task).
- **W48-CR2-04 (provenance).** The live instrument moved past the pass-07 pin
  (`957c61e3eb0e` → `548329414083`, 66 820 → 70 789 bytes) before this run. The
  three coverage functions are byte-identical across the move, so R0 == R1 and
  the pinned characterization still describes live semantics; every coverage
  count must nevertheless cite the instrument hash it used.

## Proposed patch (unapplied)

`proposed_patch.diff` adds `TARGET_PATH_ALIASES`, `_collect_hash_strings`,
`_norm_targets`, and rewrites `_targets_in_review` / `_explicit_pins` to:
normalise path / `path#hash` / `node@hash` / comma-semicolon multi targets to
node ids; read `class_id` as a binding key; flatten dict/list-valued pins
recursively; and take `#`/`@` hex fragments as pins. It keeps the existing
12-hex prefix rule and the full-flag default. The patched file parses (control
C9), applies to the live text (the two rewritten functions are unchanged live),
and introduces no false positive on the frozen corpus.

## Controls

11/11 pass (see `report.json` `controls`): fixture R1/R3 expectations, per-case
mutation detection for both rules, no-false-positive, faithful copy,
frozen-corpus stability, pinned-hash cross-check against pass-07
`measured_hashes`, patched-file parse, negative fixtures, live-instrument
measurement. Two runs over the identical frozen corpus are **byte-identical**
(`core_sha256` `d831f13ae27883d8dcb5766ec9b6ec89b90c9d114571fa1a5d4692eac9373240`).

## Falsifier

At the pinned instrument `957c61e3eb0e` and the frozen corpus digest: (a) any
fixture whose R1/R3 classification differs from `fixtures/expectations.json`;
(b) any live full accept counted by R1 that this report lists as invisible to
R1; (c) any R3 full accept not resolving to the live schema sha256 by an
explicit pin or target fragment; (d) any control not flipping/passing as
declared; (e) two runs over the identical frozen corpus producing different
`core_sha256`; (f) a live-instrument run whose full-accept sets differ from the
recorded R0 sets. A later write to the instrument or the review corpus is not a
falsifier — it is a new revision to re-run against.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-048/gform_coverage_rule/characterize_review_coverage.py \
  --now 2026-09-12T01:20:00+0800 --out report.json
python3 artifacts/worker-048/gform_coverage_rule/characterize_review_coverage.py \
  --now 2026-09-12T01:20:00+0800 --reuse-frozen --out report_run2.json
python3 artifacts/worker-048/gform_coverage_rule/emit_events.py
```

## Authority

Worker-level report only. No gate verdict, no node transition, no
`validation_status=passed`, no canonical write, no patch adoption. Worker events
cannot promote any of those.
