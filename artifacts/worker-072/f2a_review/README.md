# W072-F2A-REVIEW-01 — independent non-author review of F2a (AF-SCC-C2-VAC-GEN)

**Verdict: accept 4.5**, bound to `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3` (schema revision 13).
Worker evidence only: no gate verdict, no node `done`, no theorem, no mathematics or citation verdict.

## Why this task

At the pass-05 measurement (map `controller_gate_audit`, 2026-09-12T00:49:19+08:00) G-FORM was
pending with **F2a at 0 distinct accept reviewers** and F1/F2b at 1 each; the rev12 r2 review
verdicts were voided by the carded `astra-life05-evidence-binding-repair`. F2a was the open class
on the critical path (`astra-life05-verify-gform-r3` needs two independent non-author accepts per
class). This worker took one bounded class-bound task: an independently implemented conformance
review of F2a at the live bytes.

## Method

`check_f2a.py` is a from-scratch instrument (stdlib + PyYAML 6.0.3). It deliberately does **not**
import `research_map/class_separation.py`, `artifacts/formulation/tools/check_class_schema.py`, or
`artifacts/worker-06/spec_conformance_audit.py`, so a shared blind spot in those tools cannot be
inherited silently. Two design rules come from the CF-16 metalinguistic-mention findings:

* **Assertion sites only.** Class-id tokens and the `C0 or C2` composite are scanned only in the
  specification slots (`class_id`, `scope_statement`, quantifiers, domain definitions, conclusion
  statements). `anti_scope` / `forbidden_*` / `must_not_conflate` / `implication_ledger` are
  mention sites and are checked for the *required mention*, not flagged for containing the token.
* **Duplicate YAML keys are a hard defect** (PyYAML keeps the last silently); a tracking loader
  records them.

21 checks: mirror-pair byte identity; singular class id; no composite regularity; conclusion type
and family; I+/visibility roles; quantifier chain/order/negation; domain resolution; topology;
genericity and variants; extension predicate; F0 hash binding; contract pointers; consistency
evidence binding; falsifier completeness; forbidden strengthenings/weakenings; implication
direction; review hygiene; duplicate keys; F0 frozen stability; evidence-document shape (INFO);
and the rev12→rev13 semantic-invariance delta.

**Controls (9/9 trip, 0 escaped):** injected composite regularity, C0 conclusion type, F0 hash
mismatch, variant claiming to be the class, I+ moved into the conclusion, reversed quantifier
order, removed tier-1 falsifier, appended duplicate key, and a clean re-dump determinism control.

## Result

20 PASS / 0 FAIL / 1 INFO at `e9a27996dfd3`. Mutation controls 9/9. The rev12
(`5476a3f2c6bc`) → rev13 (`e9a27996dfd3`) change set is exactly the carded evidence-binding
refresh — `revision`, `revised_at`, `revision_history`,
`f0_binding.consistency_evidence_sha256`, `f0_binding.checked_at`, `f0_binding.binding_note` — with
**no class-semantics path moved**, and `declared_f0_sha256` still `0abb9ed8a961`.

Findings are in `report.json` and `../../reviews/F2a-review-worker-072-rev13.json`:
`W072F2A-03` records the residual, non-blocking weakness that the live consistency evidence
document pins the compared *paths* but not their *bytes* (worker-047 CB-2), outside the four items
of the revive repair and left to the A1/A0 layer; `W072F2A-04` states the structural/declarative
scope limit; `W072F2A-05` records that FROZEN.json is still revision 28, so the r3 round cannot yet
bind pins.

## Files

| file | role |
|---|---|
| `check_f2a.py` | the instrument (self-contained; `--controls` re-runs the mutation suite) |
| `report.json` | full run: measured hashes, 21 checks, controls, delta |
| `pins/af_scc_c2_vacuum.rev12.yaml` | pinned rev12 bytes (`5476a3f2c6bc`, the lead's declared pre-repair pin) |
| `controls/controls_summary.json` | 9 mutation controls, 0 escaped |
| `MANIFEST.json` | sha256 of every deliverable |
| `../../reviews/F2a-review-worker-072-rev13.json` | the discoverable review verdict |

## Falsifier

Re-measure `schemas/af_scc_c2_vacuum.yaml`: a hash other than `e9a27996dfd3`; any of the 20 checks
failing on a clean re-run; a rev12→rev13 changed path outside the six named non-semantic paths; or
a mutation-control escape. Re-run:

```bash
python3 artifacts/worker-072/f2a_review/check_f2a.py --controls \
  --json artifacts/worker-072/f2a_review/report.json
```

**Independence / authority.** Not an author of F2a, F0, the supplement, VARIANT_REGISTRY,
FROZEN.json or the rev29 repair tool. No other reviewer's F2a verdict text was read before this
verdict was formed. Worker evidence only; G-FORM coverage is adjudicated by the audit lead and
recorded by Astra.
