# W082-A1-F0-INDEP-REV5-01 — F0 rev5 review-independence census

**Worker:** worker-082 (bounded execution worker) · **Node:** F0 · **Gate:** G-F0 (A1 criterion evidence)
**Observed artifact:** `research_map/formulation_taxonomy.yaml` rev5
sha256 `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
(FROZEN rev28 `2f358f6722d92062`, supplement `d7419b4e8963cb71`)
**Observation window:** 2026-09-12T00:48:17+08:00 .. 00:48:20+08:00 · pinned hash drift during run: **none**

## Question

At the pinned canonical F0 rev5 bytes, how many *mutually independent* reviewer verdicts exist
after (a) collapsing re-emitted channel copies to one verdict per reviewer, (b) applying the
protocol same-text dedup rule ("two reviews that agree because they are the same text count as
one"), and (c) excluding authors? Does G-F0's "two independent reviewer verdicts" hold?

## Result (audit evidence; not a gate verdict)

| measure | value |
|---|---|
| distinct accept reviewers | **6** (deepseek-flash-18, deepseek-flash-19, worker-025, worker-038, worker-078, worker-087) |
| channel copies collapsed | 52 |
| distinct non-accept reviewers | 5 (astra-lead-audit, worker-047, worker-048, worker-073, worker-094 — all `revise`) |
| mean / max pairwise 5-gram Jaccard | **0.0038 / 0.0122** |
| Kish-style ESS `n/(1+(n-1)r̄)` | **5.889** |
| accept components at τ=0.30 / 0.50 | **6 / 6** |
| accepts declaring `counts_as_full_schema_verdict=true` | **4** (worker-025, -038, -078, -087) |
| accepts with live-store or ingested copy | 6/6 |
| pairs at the protocol dedup threshold 0.50 | **0** |
| author reviewers in accept set | none (authors excluded: astra-lead-formulation, deepseek-flash-01) |
| worker review verdict | **accept**, score 4.0, `counts_as_full_schema_verdict=false` |

Controls: exact-clone pair 0.9956, seeded random-token null mean 0.0 / max 0.0,
accept-vs-non-accept mean 0.0023, re-measurement of the frozen harvest deterministic (identical
digest). The corpus is live: a second harvest during the run saw the same verdict set, and later
verdicts are out of this window.

Findings: (01) 6 text-independent accepts; (02) 4/6 declare the full-schema flag, review-store
copy of worker-087's accept carries no primary hash field (only its ingested event binds);
(03) channel-copy hygiene — worker-038 alone has 18 copies with two text variants; coverage
should bind reviewer ids, not event ids; (04) self-declared headline exposure exists inside the
accept set — this measures text/authorship independence, **not** statistical error independence;
(05) the unresolved scalar-class genericity item is independently reported by four accepts
(one open content item, four reads); (06) instrument controls.

## Files

| file | sha256 |
|---|---|
| `evidence.json` | `0608854eb3c6b6973c477a1e3d7689639f99e035331eed4700dd91b43304fe1d` |
| `REVIEW-F0-INDEP-082.json` | `c6bb0eca51d29e13c5da9926f5c3940f4c950edee91d6516c0078c4914f33619` |
| `harvest_f0_independence.py` | `42485e7a103bdd93896922913b13d54366f442ea3e9a863349d9b5f544d03d4a` |
| `REPORT.md` | `387166c43f11f0432d7dc50cc153c1f2e49ff9f1b40ab249cb03722c6eaa91de` |
| `emit_w082_events.py` | `b89ae98ca06846023c3de539b6e5755ae284ab0288fbe8032cfad033747cefdb` |

Reproduce: `python3 artifacts/worker-082/f0_indep_rev5/harvest_f0_independence.py` (read-only,
prints the summary); `--write` regenerates `evidence.json`, `REVIEW-F0-INDEP-082.json`,
`REPORT.md`. Checkpoint: `runtime/state/w082_f0_indep_rev5_checkpoint.json`.

## Known minor defects (self-reported)

- W082-F0I-02 prose parenthetical in the frozen `REVIEW-F0-INDEP-082.json` / `REPORT.md` enumerates
  three of the four full-schema accept reviewers (omits worker-078). The authoritative structured
  data is `evidence.json` `measurement.accepts[*].counts_as_full_schema_verdict` and the REPORT
  accept table: worker-025, worker-038, worker-078, worker-087 are true. The frozen artifacts were
  not regenerated to avoid invalidating the emitted event hashes; the defect is recorded in the
  worker checkpoint `known_minor_defects`.

## Event idempotency incident (self-reported)

The first emitter keyed idempotency on the exact `event_id`, which embedded a wall-clock stamp, so
a second run re-emitted the delivery under stamps `004927` and `005005`. Both sets are
content-identical (same artifact sha256, same review_id `W082-A1-F0-INDEP-REV5-01`, same scoped
verdict). The emitter is fixed to content-keyed idempotency, and a stable-id correction event
`w082-f0-indep-dedup-note` instructs downstream consumers to count the delivery **once** by
review_id / artifact path. Neither set is a full-schema accept (`counts_as_full_schema_verdict=false`),
so no F0 coverage is inflated either way.

## Falsifier

Re-run the instrument at the pinned F0 bytes. This record is void if a primary-hash-bound accept
reviewer is missed, if any two accept reviewers score Jaccard ≥ 0.50 on reviewer-authored text, or
if an accepting reviewer is an author of the taxonomy.

## Authority / non-duplication

Worker evidence only: no gate verdict, no node status `done`, no `validation_status=passed`, no
canonical file edit. Not duplicative of `artifacts/worker-002/review-ess/` (binds F0 `276009f4`,
superseded) or `artifacts/worker-074/f2a_verdict_independence/` (F2a `b6123750`, superseded):
this census binds the rev5/rev12 generation at `0abb9ed8` and collapses reviewer-level copies
rather than event records.
