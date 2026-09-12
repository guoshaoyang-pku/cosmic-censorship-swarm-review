# W060-F2B-VERDICT-01 — independent hash-pinned verification of F2b

- **Worker:** worker-060 (bounded execution worker; one task, then exit)
- **Node / class / gate:** F2b / `AF-SCC-C0-VAC-GEN` / G-FORM
- **Canonical artifact:** `schemas/af_scc_c0_vacuum.yaml`
- **Reviewed sha256 (stable across the review window):**
  `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`
- **Verdict: PASS** (no failed checks). Evidence: `artifacts/worker-060/f2b_independent_verdict/evidence.json`
  (`sha256 524c0f59a8bb3efa48a1b0d8982077a7506b1a334459f6407a332c106e366549`).
- **Snapshot binding the review:** `snapshots/af_scc_c0_vacuum.1bb78ce9b357.yaml`
  (`sha256 1bb78ce9…355508`, byte-identical to the reviewed canonical file).
- **Reproduce:**
  `python3 artifacts/worker-060/f2b_independent_verdict/verify_f2b.py --pin 1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`

No assignment card existed in `comms/inbox/worker-060.jsonl` (fleet launched 00:12:29).
Following the launch prompt ("if no assignment exists, inspect the immediate queue and propose one
artifact-backed task without claiming completion") this is a self-proposed, bounded, class-bound
verification. It claims no node completion and issues no gate verdict.

## What was checked at the pinned hash

| Check | Result |
|---|---|
| G-FORM criterion field presence (exact quantifiers, topology, regularity, genericity, I+, visibility, conclusion_type) | PASS — 32/32 required fields present, 0 missing |
| Class identity (`class_id`, `regularity_token=C0`, `sibling_disjoint_from`, `conclusion_type=scc_c0_future_inextendibility`, anti-scope sibling row) | PASS |
| Class separation via canonical `research_map/class_separation.py` | PASS — 0 hard findings |
| **HF-B1** (composite "C0/C2" outside a prohibition context; `reviews/F2b-review-18.json`) | PASS at this hash — 2 composite occurrences total, both non-assertive: line 157 denial context ("No containment with C2 or C0 is asserted here"), line 283 quoted mention under `anti_scope.phrases_that_are_not_this_class` |
| **HF-B2** (artifact `node_id` vs map node label) | PASS at this hash — artifact declares `node_id: F2b`; the map now has an F2b node; the old `F2b` vs `F2` mismatch is closed structurally (see advisory) |
| VARIANT_REGISTRY consistency (7 variants, all parents frozen; no variant id in any `class_id`/`class_ids` surface) | PASS |
| Canonical ↔ authoring byte identity (`schemas/` vs `artifacts/formulation/schemas/`) | PASS — byte-identical |
| Detector negative controls (injected merge flags; prohibition / quoted mention / C0-vs-C2 stay clean; SCC-conclusion-on-WCC and WCC-conclusion-on-SCC both flag) | PASS |
| Hash stability during window (start measure = final measure) | PASS — no drift |

Detector regression against the worker-07 falsification corpus at run time: **tp=17, fn=0, tn=10,
fp=0, verdict=PASS** (27 fixtures).

## Advisories (not gate failures; no verdict authority)

1. **W060-ADV-MAP-PIN-PLACEHOLDER (minor, owner astra).** Map node F2b `artifact_sha256` is the
   zero-padded placeholder `a2aef5ac7fe377a8` + 48 zeros, so `declared_hash_matches_measured=false`
   while the file on disk measures `1bb78ce9…355508`. The map pin must be re-measured; a placeholder
   is not a declared hash.
2. **W060-ADV-ANTISCOPE-SELF-ID (info, owner lead-formulation).** Two
   `anti_scope.not_this_class` rows reuse this class's own `class_id` for variant readings
   (`parent_class`/`variant_id` only in prose). Matches the non-blocking N-A4 labelling
   recommendation already recorded by reviewer 18.
3. **W060-ADV-DETECTOR-CONSERVATIVE (info, owner lead-audit).** `class_separation.py` flags a
   prohibition sentence that also carries an assertion phrase (e.g. "never write 'C0 or C2' as a
   single class"). This is documented by-design in the module docstring; recorded as calibration
   input for A1-REBIND-01, not as a defect in F2b.

## Falsifier (this verdict dies if)

At `1bb78ce9…355508`: (a) a composite "C0 or C2" token asserted as one class, or a bare composite
outside a prohibition/denial/quoted-mention context; (b) a `conclusion_type` or conclusion prose
importing the C2 family; (c) any missing G-FORM criterion block; (d) a VARIANT_REGISTRY variant
with a non-frozen parent, or a variant id in a `class_ids` surface; (e) canonical/authoring
divergence; (f) any hash change of the canonical path. **This verdict does not transfer across
hashes** — re-run with the new pin. During this window the file was republished repeatedly
(F2b observed at a2aef5ac by the map at 00:17:46 → 962f33c6 at 00:18:37 → 1bb78ce9 at review
time), so hash-pinned verdicts from earlier windows are void for the current revision.

## Limits / no-completion claim

Structural and detector-level verification only. This does **not** validate the mathematical
content of the class (quantifier semantics, genericity claims, citation scope, non-vacuity), does
not adjudicate the C0/C2 transfer blocker, and does not resolve the open citation items. It is not
one of the two named independent reviewer verdicts required by G-FORM; it must not be counted as
one. Worker events cannot set `status=done`, `validation_status=passed`, or a gate verdict.

## Duplication declaration

Not a repeat of peer work seen in `comms/outbox` / `artifacts/`: worker-059 verified F1
(`af_wcc_vacuum.yaml`) against a frozen hash by diff; worker-065 measured data-class concordance
across F1/F2a/F2b; worker-09/07 worked the literature ledger; this task independently verifies F2b
only, disposes HF-B1/HF-B2 at the current canonical hash, and adds the map-pin placeholder finding.
