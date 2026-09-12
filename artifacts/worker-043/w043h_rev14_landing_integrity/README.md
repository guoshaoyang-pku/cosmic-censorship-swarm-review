# W043H — F2b rev14 pre-landing atomic-integrity audit (worker-043)

**Class:** `AF-SCC-C0-VAC-GEN` (node F2b), gate G-FORM. **Verdict: revise 3.5** (advisory worker
evidence, not a full-schema verdict, not a gate verdict). **Canonical bytes written: none.**
Sandbox only: `tmp/w043h_sandbox/`.

## Why this task

Three staged F2b rev14 candidates are on the landing path. Their **direction** axis is already
verified by worker-100 (`9ab32ee39d00` 4.5), worker-080/029 (`51c253c46306`, `4951cc969803`) and
others. What no review had measured is whether a candidate can be **landed atomically**: does its
own declared hash chain resolve, is it revision-ready, does the canonical gate pass on its bytes,
and which declared pointers go stale if only the schema file is written.

## Method

`check_landing_integrity.py` (deterministic; fixed `STAMP`; read-only on canonical paths):

| check | question |
|---|---|
| C01 | YAML parses, `class_id`/`node_id` consistent |
| C02 | D1: is an assertive containment denial present in `regularity.must_not_conflate[0]` while the same document asserts the nesting chain? (mention-aware: bracketed historical notes are stripped) |
| C02b | entailment direction in the assertive clause: INVERTED / LICENSED / NEUTRAL_POINTER |
| C03 | D2: any `C2 is a strictly larger extension class` premise, and is a direction-correct replacement present? |
| C04 | implication ledger runs C0 ⇒ H2_loc ⇒ C2 |
| C05 | every declared `f0_binding` hash resolves against live bytes |
| C06 | revision landing readiness: revision 13 → 14, `revised_at` bump, rev14 `revision_history` row (W043G H1–H4) |
| C07 | canonical structural gate `artifacts/formulation/tools/check_class_schema.py` at the candidate bytes |
| C08 | taxonomy consistency in sandbox (`check_taxonomy_consistency.py`) |
| C09 | complete atomic write set: declared pointers that name the superseded F2b hash |

**Controls (pre-registered, 100% matched):** M1 live rev13 → D1/D2 FAIL; M2 base `84b5d3fa` → D1
PASS, D2 PASS, entailment INVERTED (independently reproduces worker-080 HF1); M3
`smaller→larger` mutation → D2 FAIL; M4 declared-hash tamper → chain FAIL; M5 second run
byte-identical. Entry == exit pins 10/10, zero drift.

## Result

| candidate | sha256 | D1 | D2 | direction | declared chain | gate | rev14 row | stale pointers |
|---|---|---|---|---|---|---|---|---|
| cand023_v2 | `9ab32ee39d00` | pass | pass | LICENSED | 3/3 | exit 0 | no | 4 |
| cand080_51c253c4 | `51c253c46306` | pass | pass | LICENSED | 3/3 | exit 0 | no | 4 |
| cand080_4951cc96 | `4951cc969803` | pass | pass | NEUTRAL_POINTER | 3/3 | exit 0 | no | 4 |

All three are content-clean, gate-passing and chain-resolving. **None is landing-ready as staged
bytes**, and the landing is not a one-file write:

1. **Revision/history**: every candidate still declares `revision: 13` with no rev14 history row and
   the rev13 `revised_at`. The W043G history defects persist in all three (non-monotone rows 8–9;
   row 9 `unused:true`). Landing needs revision 13→14, a wall-clock `revised_at`, and a rev14 row
   appended in order.
2. **Atomic write set** (C09): `artifacts/formulation/FROZEN.json` (b2ab6acb) and
   `schemas/af_scc_regularities.yaml` (b2ab6acb, re-pinned 01:11) must move with the schema;
   `entry_hashes.json` and `schemas/af_scc_c0_vacuum.yaml.sha256` are *already* stale at
   `1bb78ce9` (rev11) and should be refreshed in the same revision. The canonical/mirror pair is
   byte-identical at b2ab6acb and must be written together.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-043/w043h_rev14_landing_integrity/check_landing_integrity.py
# exit 0 = measurement complete, 2 = pin drift (void, no verdict)
```

## Falsifier

Re-run the instrument at unchanged pins. Void on any entry-pin drift. Falsified if: any candidate
carries an assertive containment denial or an inverted size premise; any declared hash fails to
resolve; a candidate is shown landing-ready as staged bytes; the canonical gate or
taxonomy-consistency check fails at a candidate byte set; or the atomic write set is shown
incomplete (a further gate-relevant pointer names the superseded F2b hash).

## Non-claims

Not a full-schema content verdict; not a gate verdict; does not re-adjudicate the direction axis
owned by workers 100/080/029; does not choose which candidate the owner lands; no canonical byte
written.
