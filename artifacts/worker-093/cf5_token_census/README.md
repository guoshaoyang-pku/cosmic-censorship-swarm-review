# W093-CF5-VERIFY-01 — independent class-token hygiene census (CF-5 disposition evidence)

**Worker:** `worker-093` · **Task:** `W093-CF5-VERIFY-01` · **Node:** `F1` · **Classes:** frozen four
**Generated:** 2026-09-12T00:20:20+08:00 · **Verdict:** `PASS` (6/6 checks)
**Scanner:** `census.py` sha256 `1e4ea48a2e9f3c94d3b9a81dd53c7d7d2b053784ab31ce2abb6bb12d10337e3e`
**Machine output:** `census.json` sha256 `fe5dc5213811e7b4bec092cd582912e64f99081c668877f7213aef383e3216e6`

## What was asked

The CF-5 class-token soft flag (`CLASSSEP-SOFT: unknown class token`) recurred in F0 and F1 because
candidate readings (`AF-WCC-VAC-GEN-SET`, `AF-SCC-C0-CH-VAC-GEN`) were written in class-id shape even
after controller adjudication `astra-classscope-02` restricted every `class_id`/`class_ids` field to the
frozen four and required variants to be `{parent_class, variant_id}`. This census independently asks:
**at the pinned revision, do the canonical class-bound surfaces and their registries obey that rule?**

## What was measured (all read-only)

| check | question | result |
|---|---|---|
| C1 | every `AF-…`-shaped token on F0/F1/F2a/F2b (+legacy aggregator), classified by enclosing key | **PASS** — 94 token rows (91 canonical + 3 legacy), **0 non-frozen** |
| C2 | `class_separation.findings_for_text` on byte-identical input (two-checker agreement) | **PASS** — 0 findings on all five surfaces |
| C3 | variant registry: parents frozen, `variant_id` not class-id shaped, 19 evidence paths resolve | **PASS** |
| C4 | on-disk variant delta filenames carry no class-id-shaped token | **PASS** — names are `{parent}.variant-{ID}.delta.json` |
| C5 | recursive walk of `research_map.json` `class_id`/`class_ids` values (290 fields) | **PASS** — 0 violations (frozen four + documented `GLOBAL` + normalizer provenance only) |
| C6 | checker blind spot: 5-segment tokens truncated by the 4-block regex | **PASS** — moot at this revision (no such token on canonical surfaces) |

C6 is recorded because it explains the asymmetric pre-fix report: `AF-WCC-VAC-GEN-SET` (4 blocks) was
matched whole, while `AF-SCC-C0-CH-VAC-GEN` (5 blocks) was truncated to `AF-SCC-C0-CH-VAC` by
`class_separation`'s fixed-width token regex. Any future 5-segment token would be reported under a
name that does not exist on disk.

## Pinned revision

| node | path | sha256 (16) |
|---|---|---|
| F0 | `research_map/formulation_taxonomy.yaml` | `276009f4f63dbf83` |
| F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a4` |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee` |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cda` |
| registry | `artifacts/formulation/VARIANT_REGISTRY.json` | `5eb42f9a384a2bb3` (v2.0) |
| manifest | `artifacts/formulation/FROZEN.json` | `af24e9c396060e6b` |
| map | `research_map/research_map.json` | `a8a73f983baa28d1` |

Version 2.0 of the registry carries exactly the frozen four parents and seven variants (SET, CH,
DISTRIBUTIONAL, H2LOC, TWOSIDED, L2CONN, LIP); all 19 evidence paths resolve.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-093/cf5_token_census/census.py    # exit 0 iff overall PASS
```

## Falsifier

Any non-frozen class-id-shaped token on a canonical checker-scanned surface whose enclosing key is
`class_id`/`class_ids`; or any FAIL in C1–C5; or a registry evidence path that no longer resolves.
A file move after the pinned hashes voids the snapshot, not the finding — re-run and re-pin.

## Scope limits (what this does NOT say)

- `PASS` is a statement about **these bytes at these hashes**, not proof of checker sensitivity in general.
- Historical logs, checkpoints, events, reviews and fixture corpora that quote the pre-fix token names
  (100+ files, e.g. `artifacts/audit/**`, `artifacts/worker-0*/**`, `research_map/events.jsonl`) are
  records/fixtures, not declarations, and are out of scope. The C1 classification is what separates the two.
- The pre-existing hard flag on `claims[36]` (composite C0/C2 prose already adjudicated by
  `astra-classscope-02`) and the canonical-vs-authoring dual-tree divergence are **not** re-adjudicated here.
- No gate verdict is claimed. Gate verdicts are controller/lead authority; this is evidence for
  `astra-life02-softflag-f0f1` (F0/F1 disposition) and for G-FORM review, nothing more.
