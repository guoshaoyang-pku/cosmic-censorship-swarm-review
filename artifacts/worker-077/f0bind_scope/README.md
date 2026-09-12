# W077-F0BIND-SCOPE-01 — scope audit of the declared `f0_binding` consistency evidence

**Worker-level artifact-and-checker measurement, unverified.** Not a gate verdict, not a node status,
not a mathematics claim. One bounded class-bound task, read-only; no canonical byte written.

* **Node / gate:** F1 / G-FORM (findings bear on the open G-FORM F1 blocker `audit-l09-b3-f1-crossart`
  and on the ESC-2 F0-vs-F1 direction escalation).
* **Classes:** `AF-WCC-VAC-GEN` (primary), `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
* **Verdict:** `SCOPE_GAP_CONFIRMED` — the consistency evidence declared by all three vacuum class
  schemas resolves and reproduces byte-for-byte, but its check domain **cannot see** the live
  F0↔F1 visibility strength contradiction it is relied upon to certify.
* **Report:** `report.json#sha256:d6fc3913f23f6df64b2d91510daa9ac72b7fdb9e702400f31ab7b74a13f1748d`
  (content digest `ab4ac42543f1a845fd0cabcead4489b6e5fb1aaada2d2a4456a83380d53a6fe7`).
* **Falsifier:** a pinned artifact in the formulation acceptance pipeline whose compared-field set
  covers the visibility strength relation between F0's SET variant text and the class schemas' SET
  relation; or a live F0 revision whose direction statements agree with F1 rev13; or a sandbox control
  handled contrary to H5.

## Pins (measured at entry and exit, no in-run drift)

| path | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | `de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |

Full pin table (12 pins incl. supplement, aliases, registry, SET delta, variant-registry checker):
`PREREGISTRATION.json#sha256:` in `entry_hashes.json`.

## What was measured

1. **The binding blocks.** All three schemas declare the same `f0_binding.consistency_evidence`
   (`artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9b`) against the same declared F0
   bytes (`0abb9ed8a961`), `checked_at` 2026-09-12T00:53:20/00:53:41. F1's `binding_note` records the
   rev13 refresh: *"consistency_evidence_sha256 refreshed to the live taxonomy_consistency.json
   9e335e9b1bf after a clean check_taxonomy_consistency.py run … the declared F0 bytes 0abb9ed8a961 are
   untouched."*
2. **The declared evidence reproduces.** The exact canonical checker bytes were run inside a sandbox
   ROOT with copies of its declared inputs: exit 0, `CONSISTENT (4 classes, 0 contract-text
   divergences)`, and the sandbox-produced evidence is **byte-identical** to the live evidence. The
   hash-level chain is intact (consistent with `artifacts/worker-079/rev29_bindchain/report.json`,
   36 PASS at the same pins).
3. **The checker's domain.** From its source and from mutation controls, the checker opens only
   `research_map/formulation_taxonomy.yaml`, `artifacts/formulation/formulation_taxonomy.yaml` and
   `artifacts/formulation/VOCAB_ALIASES.json`; it **never opens a `schemas/*` file** and never compares
   the F0 top-level `variants` block. Its only direction-sensitive probe (line 45) is the lexical test
   `"J-(I+)" in wcc.replace(" ","") or "J^-(I+)" in wcc` on the `AF-WCC-VAC-GEN` conclusion text.
4. **The live contradiction.** F0 rev5 asserts SET is *strictly stronger* at two live sites:
   `variants[0].definition` line 94 and `classes.AF-WCC-VAC-GEN.conclusion.text` line 200. F1 rev13
   asserts *strictly WEAKER* at `class_identity_variants[SET].relation` line 235 and discloses the
   correction. The D1 probe token `J-(I+)`/`J^-(I+)` is **absent** from the live conclusion text (it
   now reads "the union of J^-(q) over all q in I+"), so the probe does not fire and the evidence
   reports `consistent: true`. **Coverage of the two live superseded-direction sites: 0/2.**
5. **Reliance.** 89 files under `reviews/` cite the declared evidence hash or path; e.g.
   `reviews/F1-review-worker-089.json#sha256:9a4bb3f3268cec2b4966a0115a5f14a6890b954e620a8a2a966996456af6a96c`
   records the rev13 refresh as resolving via `consistency_evidence.consistent=true`. Under the
   declared rule ("if the declared F0 artifact changes hash, this binding must be refreshed and the
   consistency check re-run before any gate verdict"), that reading treats the evidence as F0↔schema
   consistency, which is precisely what it does not check.

## Mutation controls (5/5 preregistered, all PASS)

| control | mutation (sandbox only) | observed |
|---|---|---|
| M1a | inject probe token `J-(I+)` into the WCC conclusion text | exit 1, divergence **D1** emitted → the probe is alive but token-keyed |
| M1b | flip live `variants[0].definition` "Strictly stronger …" → "Strictly weaker …" | exit 0, `consistent: true` → variants block is **outside** the domain |
| M1c | flip live conclusion prose "is strictly stronger …" → "is strictly weaker …" | exit 0, `consistent: true` → the live opposite-direction prose is outside the probe |
| M2 | set lead-contract `regularity_token` of WCC to `C2` (in-domain field) | exit 1, regularity error → harness catches in-domain mutations |
| M3 | flip F1 schema SET relation `strictly WEAKER` → `strictly STRONGER` | exit 0, evidence byte-unchanged → schemas are outside the domain |

## Findings

* **W077-FBS-01 (major).** The declared `consistency_evidence` is hash-valid and semantically
  non-covering on the bound direction axis: it is a map-taxonomy-vs-lead-contract checker (tokens,
  axes, class-id sets, three lexical contract-text probes) that reads no schema and no F0 `variants`
  block. A gate acceptance that checks `f0_binding.consistency_evidence.consistent == true` — the
  reading recorded in the review corpus — cannot detect the ESC-2 F0↔F1 contradiction.
* **W077-FBS-02 (minor).** The checker's own dormant D1 record (line 49) states *"the F0 condition is
  strictly STRONGER"*, i.e. the superseded label; if D1 fires at a future hash the emitted evidence
  would record that direction as the tool's ruling, while the independent direction proof
  (`artifacts/worker-004/f1_strictness_direction/report.json#sha256:c70cdbb306aa`) finds SET weaker.

Observations (not findings): the live `check_variant_registry.py#sha256:8c7ef46f11db` (rev14 item 5)
already encodes a level-split SET label (predicate-level strictly WEAKER, class-level strictly
STRONGER) for `VARIANT_REGISTRY.json`; it too is outside the declared evidence's domain, and no schema
declares its output as `f0_binding` evidence at these pins.

## Decision inputs (for the controller / ESC-2; no option is chosen here)

* **A — evidence-scope repair:** compare the F0 SET relation/variants text against the schemas'
  `class_identity_variants` relation, and key the D1 probe on the union wording rather than the
  literal token; then re-run and re-stamp all three `consistency_evidence_sha256`.
* **B — F0 erratum/revision:** correct or explicitly scope the two live F0 sites; a write to
  `research_map/formulation_taxonomy.yaml` voids G-F0 and requires fresh accepts.
* **C — record binding scope:** state in `binding_note`/`rule` that the declared evidence certifies
  map↔supplement token/axis consistency only and is not direction evidence; no byte moves.

## Reproduction

```bash
cd artifacts/worker-077/f0bind_scope
W077_MEASURED_AT=2026-09-12T01:25:00+08:00 python3 check_f0bind_scope.py   # exit 0, SCOPE_GAP_CONFIRMED
```

Two runs are byte-identical (`determinism.json`); the sandbox ROOT is rebuilt per control and removed
after the run, and every canonical pin is re-measured at exit (drift ⇒ exit 3).

## Post-run drift (addendum; measured after the determinism runs)

The authorized rev14 landed **21 s after** this measurement closed (report mtime 01:25:21; rev14
writes 01:25:42): `schemas/af_scc_c2_vacuum.yaml` `e9a27996dfd3` → `c1013e486988` (rev14),
`schemas/af_scc_c0_vacuum.yaml` `b2ab6acb2bbe` → `c4d17fe6ac59` (rev14),
`VARIANT_REGISTRY.json` `6bac9adea19e` → `08afa6910406`, SET delta `64b8d6394a04` → `518cab5d139f`.
The declared evidence file was re-emitted at 01:25:55 with **byte-identical** content
(`9e335e9b`, mtime moved, hash did not). F0 `0abb9ed8a961`, F1 `d9cebb9404b2`, the checker
`de356d99` and the evidence bytes are unchanged, so the scope-gap finding persists at its run-window
pins while the F2a/F2b binding-block hashes are superseded. The new rev14 F2a/F2b schemas still
declare `taxonomy_consistency.json#9e335e9b` (with `checked_at` still 00:53:20), and the registry now
carries a level-qualified SET label (predicate-level strictly WEAKER / class-level strictly STRONGER)
that the declared evidence — and the schemas' flat rev13 relation — still do not check. Details:
`drift_observation.json`. Next falsifier: re-run this instrument at the settled rev14 pins once
FROZEN moves, under a fresh pre-registration.

## Non-claims

* Not a gate verdict and not a node status; workers cannot set `status=done`,
  `validation_status=passed`, or a gate verdict.
* Not a mathematics claim about which direction is true — the direction proof already exists at
  `artifacts/worker-004/f1_strictness_direction/report.json`.
* Not a demand that F0 be rewritten; the disposition belongs to the controller / ESC-2.
* Not a review of the rev14 window; any byte move after these pins voids this measurement.
