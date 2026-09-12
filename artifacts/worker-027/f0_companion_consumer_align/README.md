# W027-F0-COMPANION-CONSUMER-ALIGN-01 — REC-3 companion-pair alignment audit

**Worker:** worker-027 · **Node:** F0 (controls on F1/F2a/F2b) · **Gate surface:** G-AUDIT / G-F0
**Class:** AF-WCC-VAC-GEN (`class_ids`: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN)
**Verdict:** `REC3_CONSUMER_ALIGNMENT_GAP_CONFIRMED` · 14/14 controls · exit 0
**Artifacts:** `report.json`, `controls.json`, `verify_companion_consumers.py`, `PROPOSED_PATCHES.md`,
`proposed_patches.json`, `snapshots/`, `sandbox/`

## The question

The controller ruled (astra-life04 **REC-3**, recorded as CF-17) that the two F0 artifacts —
`research_map/formulation_taxonomy.yaml` (declared taxonomy) and
`artifacts/formulation/formulation_taxonomy.yaml` (class-contract supplement) — are **two distinct
pinned artifacts**, a *companion* pair, for which byte-identity is **not** required. A *mirror* pair
(F1/F2a/F2b) still must be byte-identical in both trees.

This audit asks, read-only: **which gate-surface consumers still apply the pre-REC-3 byte-identity
rule to the F0 pair, what verdict do they emit, and does a REC-3-aware predicate still enforce the
three real mirror pairs?**

## What was measured

Seven consumers were classified by re-reading their source at a hard-pinned sha; five were executed
as predicates against the measured revision (rev13 schemas + FROZEN rev29, all pins matching disk at
snapshot).

| consumer | role | verdict | REC-3 aware |
|---|---|---|---|
| `research_map/astra_lifecycle.py` | controller `publication_status`, gate reasons | COMPANION_AWARE | yes |
| `research_map/audit_evidence.py` | canonical evidence auditor | COMPANION_AWARE | yes |
| `artifacts/audit/audit_r2_verdicts.py` | audit-lead r2 verdict emitter | COMPANION_AWARE | yes |
| `runtime/bin/dispatch_audit_r2.py` | audit-lead r2 dispatcher | COMPANION_AWARE | yes |
| `artifacts/audit/final_gate_verify.py` | audit gate verification | **MIRROR_HARDCODED** | **no** |
| `artifacts/audit/a1_rebind_coverage.py` | A1 coverage matrix | **MIRROR_INVERTED** | **no** |
| `artifacts/audit/emit_final_verdicts.py` | verdict/blocker emitter | **STALE_RULING_PROSE** | **no** |

The audit lead's newest r2 tools are companion-aware; the three older consumers are not. The gap is
in the **published outputs those older tools produced and that the map still cites as gate evidence**:

* `artifacts/audit/final_gate_verify_20260912T004428.json` (snapshot sha `57a0732f3660`) contains
  `HASH-F0-mirror = fail` — 1 of its 13 fails — for a pair the controller records as
  `companion-pinned`. Under the tool's own accounting a REC-3-aware predicate removes exactly that
  fail (projection 30 pass / 12 fail / 1 note; the three mirror rows are unchanged).
* `reviews/A1-rebind-coverage.json` (snapshot sha `d845701c454f`) carries blocker
  `canonical_authoring_divergence` — "mirror-equality policy breached" — at `reviews/…:1991`, a file
  the map snapshot cites in the evidence_refs of **G-AUDIT, G-F0, G-FORM and G-LIT**.
* The same tool has the mirror rule **inverted**: its F1/F2a/F2b predicate requires
  `mirror_equal == True`, so a *real* mirror divergence produces **no** blocker (control CTRL-9).
* `emit_final_verdicts.py` / `reviews/G-F0-final-verify.json` still record REC-1/REC-2 as open and
  the `canonical == authoring` criterion as unconfirmable, while `reviews/F0-review-18.json` and
  `reviews/F0-review-025.json` already apply REC-3 — the review surface disagrees with itself about
  which ruling is operative.

## Controls (14/14)

Executed, not asserted:

* CTRL-1/2 — canonical `audit_evidence.py` on the live F0 pair: no dual-tree divergence, no
  "companion pair incomplete".
* CTRL-3/4 — positive/negative mutation in an isolated sandbox: simulated F1 divergence **is** caught
  (`dual-tree divergence: schemas/af_wcc_vacuum.yaml d9cebb9404b2 != d0ed65ab69fc`); a missing F0
  supplement **is** flagged `companion pair incomplete`.
* CTRL-5/6 — the shipped `final_gate_verify` predicate reproduces `HASH-F0-mirror=fail`; the
  REC-3-aware predicate flips only that row, leaving every F1/F2a/F2b mirror-pin verdict identical.
* CTRL-7 — a simulated F1 divergence still fails `HASH-F1-pin` under both predicates.
* CTRL-8/9/10 — the A1 coverage predicate emits the F0 blocker at the measured revision, emits no F1
  blocker for a simulated F1 divergence, and the REC-3-aware variant drops the F0 blocker and adds
  the F1 divergence blocker.
* CTRL-11/12 — the published output snapshots really do carry the `HASH-F0-mirror=fail` row and the
  F0 blocker; the map snapshot really does cite the A1 file in four gates.
* CTRL-13/14 — the three hard-pinned audit-tool sources did not move; every context input was
  snapshotted at read time (no post-read movement in this run).

## Pins and moving-target behaviour

The audit is **fail-closed**: two earlier runs exited 2/void because the controller moved the map and
`astra_lifecycle.py`, and the rev13 repair republished the three schemas mid-audit. The final run
hard-pins only the three audit-tool *sources* the finding is about, and snapshots (with shas) the
controller files, class artifacts, FROZEN, map and published outputs. Measured context at snapshot:
F0 `0abb9ed8a961` / supplement `d7419b4e8963` (unchanged), F1 `d9cebb9404b2`, F2a `e9a27996dfd3`,
F2b `b2ab6acb2bbe`, FROZEN **rev29** `3d9e3d77fd87` with all three mirror pins matching disk, map
`56478e3f1d19` showing **G-F0 = pass**.

## Falsifier (pre-registered)

FALSIFIED if (a) any of the three named audit-surface consumers is in fact REC-3-aware at its
hard-pinned sha; (b) the F0 canonical and supplement paths are byte-identical in the snapshot;
(c) `HASH-F0-mirror` is not `fail` in the final_gate_verify output snapshot; (d) the A1-rebind
snapshot lacks the F0 `canonical_authoring_divergence` blocker; (e) the map snapshot does not cite
`reviews/A1-rebind-coverage.json` in any gate evidence_refs; (f) the simulated F1 mirror divergence
is not caught by the canonical auditor; (g) the REC-3-aware predicate changes any F1/F2a/F2b
mirror-pin verdict; (h) any hard-pinned consumer source drifts between entry and exit (exit 2 =
void, not falsified).

## Reproduction

```bash
python3 artifacts/worker-027/f0_companion_consumer_align/verify_companion_consumers.py
# exit 0 = gap reproduced; 10 = falsified; 2 = hard-pin drift (void)
```

## Non-claims

Not a gate verdict; a worker lifecycle cannot set node done, `validation_status=passed`, or any gate
verdict. Does not re-adjudicate REC-3 (the controller ruling is taken as given). Does not modify any
canonical artifact, review, map, audit tool or controller tool. The proposed patches are **not
applied** — the tools belong to the audit lead. Does not dispute the substance of the audit lead's
findings, only the conformance of these three predicates to REC-3.
