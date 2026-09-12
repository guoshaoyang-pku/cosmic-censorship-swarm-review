# W043G-F2B-HISTORY-CLOSURE-01 — F2b audit-trail closure frontier

Worker: `worker-043` (bounded instance, 2026-09-12, no inbox card exists for this slot).
Node: **F2b**. Class: **AF-SCC-C0-VAC-GEN**. Gate: **G-FORM**.
Instrument: `check_f2b_history_closure.py` (self-contained, read-only on canonical paths).

## Question

At the live pins (`schemas/af_scc_c0_vacuum.yaml` `b2ab6acb2bbe`, FROZEN rev29 `815e0807`),
does the staged containment repair close the whole audit trail, or does the next revision
still carry the worker-035 **F-035-01** `revision_history` defect family? Which staged
candidate leaves the `{revision, revised_at, revision_history, f0_binding}` quadruple
coherent, and what minimal edit set closes both the containment carriers and the history
invariants?

## Result (measured, not asserted)

Live rev13 fails three history invariants, reproduced mechanically:

| invariant | live rev13 observation |
|---|---|
| H1 timestamps non-decreasing | row 8 `00:30:00` precedes row 9 `23:30:35` of the previous day |
| H3 newest row names live declared F0 hash | newest hash named anywhere is `565a6e50`; live `declared_f0_sha256` is `0abb9ed8a961` |
| H4 unused row carries no active delta | `index: 9` is `unused: true` and carries two delta notes (rev11, rev8) |

Candidate census (all hash-pinned in `raw/history_frontier_raw.json`):

| candidate | sha256 | containment | history |
|---|---|---|---|
| live | `b2ab6acb2bbe` | **2 defects** | H1, H3, H4 fail |
| worker-002 2-edit `84b5d3fa` | `84b5d3fa29a6` | clean | **H1, H3, H4 fail — untouched** |
| worker-022 CD `a110f8e8` | `a110f8e875af` | clean | **H1, H3, H4 fail — untouched** |
| worker-044 rev13-integration `48cadb72` | `48cadb72e507` | clean | H1, H2, H3, H4, **H6** fail |

`48cadb72` is worse than a no-op on the trail: it sets `revision: 14` while the newest
history row still names rev13 (H2), and it re-declares the **pre-rev13** consistency-evidence
hash `675a99d0` in `f0_binding` while its own `binding_note` states the rev13 refresh to
`9e335e9b` — landing it as-is would regress the rev13 evidence binding (H6).

## Minimal closure

`closure_variants` builds and measures two edits on top of the containment-clean candidate:

- **V1** `472fcfaa98d6` — append a rev14 row + bump `revision`/`revised_at`: clears H2, H3, H5;
  leaves H1, H4 (purely historical ordering / unused-row notes).
- **V2** `28dc0d3df53d` — V1 + move the unused row into chronological position and clear its
  active delta notes: **closes all seven invariants and both containment carriers**, and the
  canonical structural gate returns `verdict: pass` on it.

V2 is stored only as a worker candidate:
`scratch/candidate_rev14_closed.yaml` (`28dc0d3df53d82543a1a3dcc6b0029b61bbb764d54a6049c0ca2b3e8d45c01fc`).
It rewrites historical ordering (row 9 moves), so the owner should decide between V2 and an
explicit disposition of the historical rows.

## Authority and falsifier

Worker measurement and review evidence only. No canonical file, map, gate verdict,
`validation_status`, or node status was modified. Falsified if the live F2b hash is not
`b2ab6acb2bbe`; if the live file does not carry the three history defects; if any listed
candidate is shown to carry a rev14 history row or a refresh of the declared-F0 reference;
if `48cadb72` does not carry `revision: 14` with a rev13-newest row; if V2 fails any invariant
or fires the containment detectors; if a pre-registered control departs from its expectation;
or if a rule/FROZEN-protocol clause is produced under which revision-history coherence is not
required for a class-schema revision.

## Checks

- 9/9 pre-registered controls matched (K1–K9).
- 14/14 pins stable entry→exit; no canonical byte written.
- Checker re-runs deterministically from the pinned hashes.
