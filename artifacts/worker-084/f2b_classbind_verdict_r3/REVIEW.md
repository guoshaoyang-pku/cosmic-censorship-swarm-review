# W084-F2B-CLASSBIND-03 — class-binding review of AF-SCC-C0-VAC-GEN (round 3)

Worker: `worker-084`. Node: `F2b`. Class: `AF-SCC-C0-VAC-GEN`. Gate: `G-FORM`.
Snapshot (read once, re-hashed after the check, no drift):

| input | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (canonical) | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (authoring mirror) | same bytes (`1bb78ce9b357`) |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `artifacts/formulation/formulation_taxonomy.yaml` (class-contract supplement) | `c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f` |
| `artifacts/formulation/FROZEN.json` (rev 26) | `2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3` |
| report | see `report.json` (49 checks: 40 pass / 7 hard / 2 soft) |

## Round-2 falsifier adjudication — NOT falsified

Round 2 named the successor test: "FROZEN rev26+ with frozen_at <= wall clock AND
`f0_binding.checked_at` re-stamped from observed wall clock, plus a write-time
future-stamp lint demonstrated on a synthetic fixture. Canonical move past
`1bb78ce9b357` voids the verdict."

- **Canonical did not move** — `1bb78ce9b357` is unchanged. Round-2's snapshot is still
  live, so its verdict is not void.
- **`frozen_at` is fixed at rev26** (`2026-09-12T00:24:49+08:00` == FROZEN.json mtime
  `00:24:49.43`). HF-3 **RESOLVED**. This is a real repair.
- **`f0_binding.checked_at` is byte-identical** to rounds 1/2 (`00:30:00`). The declared
  re-stamp never happened. HF-4 **PERSISTS**.
- **No write-time stamp lint exists** in the repo (searched `artifacts/formulation/tools/`
  and `research_map/`; `regenerate_frozen.py --at` still takes its stamp as an argument).
  Clause (d) is unmet, so "the generator, not the instance, is unfixed" stands.

Round 2's `revise` therefore stands, and this round extends it.

## Class semantics are CLEAN (unchanged from rounds 1–2)

- Canonical class-separation scan on the snapshot bytes: **0 hard findings, 0 unknown
  class tokens**; checker regression **PASS** (27 cases: 17/17 leaks, 10/10 controls,
  0 FP / 0 FN).
- Exactly one regularity token, `C0`, across `class_components`, the declared-F0 contract
  axes and `regularity.extension_regularity`; no composite `C0/C2`.
- Conclusion family `SCC`, C0 conclusion type; WCC/I+ content listed in
  `forbidden_strengthenings`; no theorem-status claim.
- Sibling disjointness declared vs `AF-SCC-C2-VAC-GEN`, present in the taxonomy
  disjointness list, `anti_scope` covers all three siblings.
- Falsifier tier-1 is present, names a witness type and carries proof obligations.
- `f0_binding.declared_f0_sha256` equals the measured declared-F0 hash; FROZEN rev26
  binds canonical == authoring for F2b and both F0 artifacts; the sidecar matches.

**The `revise` verdict is not about class semantics. It is about the evidence chain.**

## Four distinct defects (7 hard checks, 2 soft)

- **D1 — `f0_binding.checked_at` future-dated (PERSISTS from round 2).**
  `00:30:00` vs schema mtime `00:19:14` (future by ~11 min), still future at run time
  `00:27:54`. Time-independent check added this round: a stamp later than the file's own
  write must fail regardless of when it is read.
- **D2 — effective `revised_at` future-dated (NEW detection).**
  The last top-level `revised_at` is `2026-09-12T00:30:00+08:00`, later than the file's
  own mtime `00:19:14`. Same clock-discipline defect as D1 in a second field; also
  present in all three canonical schemas.
- **D3 — duplicate top-level YAML keys (NEW detection).**
  8 top-level `revised_at` keys. PyYAML silently keeps the last (`00:30:00`); a strict
  parser errors or keeps the first (`2026-09-11T23:34:10+08:00`). The artifact's declared
  revision time is therefore **parser-dependent**, which is a decidability defect in a
  frozen artifact that reviewers bind to by hash.
- **D4 — `class_contract_pointer` does not resolve at the declared F0 (independent
  reproduction).**
  `class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN`.
  The fragment resolves in the authoring supplement (`c8e979a1`), but the declared,
  hash-pinned F0 canonical (`276009f4`) has **no `class_contracts` key at all**. So the
  class core the schema points at lives outside the artifact its `f0_binding` pins. The
  chain is only closed by FROZEN rev26, which does pin the supplement (measured match);
  inside the schema the pointer is path-only with no inline hash (soft C12.5), and the
  F0 publication pair is `divergent` (soft C12.6, `f0_mirror_conflict.json` REC-1/REC-2,
  status blocked-pending-controller-adjudication).

**Corroboration, not discovery.** D2/D3 and D4 are already open in the controller's
pass-03 state: assignment `astra-life03-close-findings` items (a) and (b), and the
pass-03 gate reason for F2b ("4 accepts + 1 revise; quantifier domain, F0 pointer does
not resolve"). This round pins them to hashes with machine checks and gives them a
falsifier.

## Verdict

`revise`, score **2.5**. Worker verdict only: it does **not** set node status, gate
verdict, or `validation_status`; Astra / the leads own those. No claim is made about
cosmic censorship itself.

## Falsifier (round 3)

Re-run `verify_f2b_classbind_r3.py` at the pinned hashes. Falsified if: (a) any recorded
pass re-runs false; (b) the canonical/authoring copies diverge or the canonical file
moves past `1bb78ce9b357` (drift voids the verdict, it is not falsification); (c) a
successor freeze sets `revised_at` **and** `f0_binding.checked_at` <= the schema's own
mtime, removes the duplicate `revised_at` keys, and repoints `class_contract_pointer` at
a fragment resolving inside the hash-pinned declared F0, with class identity still
clean; or (d) a write-time lint rejects future-dated and duplicate revision stamps on
synthetic fixtures.
