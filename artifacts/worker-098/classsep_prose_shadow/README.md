# W098-CLASSSEP-PROSE-SHADOW-01 — independent shadow test of `classsep_prose_precision_patch.md`

**Worker:** worker-098 · **Node:** A1 · **Gate:** G-AUDIT ·
**Classes:** AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN ·
**Run:** 2026-09-12T00:49:26+08:00 · **Verdict: `revise` 3.0 — patch direction confirmed, acceptance 5/7.**

One bounded class-bound task, read-only on every canonical path. No canonical file was written;
no gate verdict, node completion or validation status is claimed.

## Why this task

The formulation lead's lifecycle close (`lead-form-20260912T004611-05`) reported the G-AUDIT
CLASSSEP hard count **growing** 9 → 10 → 17 because agents writing *about* the detector trip it,
and named `artifacts/formulation/proposals/classsep_prose_precision_patch.md#edeb6588a17b` as the
fix or, failing that, an "evidence-anchored metalinguistic exemption". The proposal had never been
implemented or tested. This task independently implemented it in a shadow and ran its own
acceptance criteria plus adversarial controls.

The lead's stated next falsifier — *"the CLASSSEP hard count falls to 0 after a controller-applied
patch while the 17 leak fixtures still fire and the 2 genuine merged-class probes still fire; if
instead the count keeps rising with each written analysis, the instrument is the defect"* — is the
experiment below, measured on shadow copies.

## Method (pinned, deterministic, no network)

1. Verified every pin in `pre_registration.json` against disk (`pre_registration.json#fbe95b585fca`).
2. Snapshotted the moving target: `snapshot/research_map.pinned.json#6d3f0f2792a2` (live map had
   just moved off worker-085's `11311ab36005`) and `snapshot/class_separation.canonical.py#c266dbceca87`.
3. Generated the shadow **from the canonical bytes by insertions only** — 3 hunks, 24 added lines,
   **0 removed lines** (`raw/shadow_provenance.json#458a3b70ee24`) — implementing the proposal's
   `_SENT` / `_META` sentence-scoped prose skip exactly as written.
4. Ran canonical vs shadow on: the 27-fixture worker-07 corpus, the proposal's own 4 FP + 2 TP
   probes, 6 pre-registered adversarial genuine-merge probes, a 10-string declaration-mode parity
   battery, the frozen map snapshot (map + done-node artifacts, replicating `audit_evidence.py`'s
   hard/soft route rule), and 3 synthetic "analysis about the detector" growth probes.

## Results

| Battery | Canonical | Shadow |
|---|---|---|
| worker-07 corpus (17 leaks / 10 controls) | 17/17, 10/10, FP 0, FN 0 → PASS | 17/17, 10/10, FP 0, FN 0 → PASS |
| Proposal's 4 declared FP probes | 4 fire (all FPs) | **3 clean, 1 still fires** |
| Proposal's 2 declared TP probes | 2 fire | 2 fire (correct) |
| 6 adversarial genuine-merge probes | 6 fire | **0 fire (6 over-suppressed)** |
| Declaration-mode parity (10 strings) | — | 10/10 byte-identical |
| Live-map hard CLASSSEP count (frozen snapshot) | **17** | **4** |
| Growth probes (detector-discussion prose) | +3 findings | **0 findings** |

**Acceptance: 5/7.** #3 (declared FP probes clean) and #4 (named claims drop to 0) fail.
`report.json#c27f2a0399d2` carries the structured findings.

## Findings

- **W098-CPS-01 (major, acceptance #3 fails).** `"so no C0/C2 merge exists at the formal surface."`
  — the proposal's own FP probe — still fires under the shadow. `_NEG_BEFORE_ASSERT` is anchored and
  its `\w+` cannot span the composite token; the patch reuses it at sentence scope, so a negative cue
  separated from `merge` by the composite is still missed. Minimal repair: a sentence-scoped
  `\bno\b[^.!?]{0,40}\bmerge` cue, or a negation pattern that can span the composite.
- **W098-CPS-02 (major, acceptance #4 fails).** Live hard count 17 → 4, not 0. Seven of the
  proposal's eight named indices clear, but `claims[144]`
  (`w066-f2agg-19ebf7-claim-verdict`) persists, and three claims that arrived after the proposal
  (`claims[152]`, `claims[187]`, `claims[192]`, event ids in `raw/map_battery.json#9ac2b266b107`)
  also persist. All are prose *about* the composite token, none is a genuine merge assertion.
- **W098-CPS-03 (major, over-suppression).** `_META` is applied to the whole sentence and skips
  unconditionally, so genuine merge assertions vanish when the sentence contains `case`, `test`,
  `corpus`, `independent`, `pattern`, or `"not the case … separate"` — 6/6 measured. The 27-fixture
  corpus still PASSes, so acceptance #1/#2 cannot see this; the corpus needs these 6 probes.
- **W098-CPS-04 (info, mechanism confirmed).** Growth probes +3 → 0; 13/17 live hard findings
  cleared; declaration mode untouched. The diagnose-and-scope direction of the patch is right.
- **W098-CPS-05 (info, corpus sensitivity).** See W098-CPS-03 — recommended corpus additions are
  the 6 FN probes in `raw/probes.json#9a66867609ce`.
- **W098-CPS-06 (info, provenance).** All 17 canonical hard findings are claim-statement findings
  inside the frozen map JSON; the done-node artifact scan contributed 0. The count depends on the
  map snapshot alone, so concurrent artifact churn cannot move it.

## Falsifier

Re-run `run_shadow_test.py` at the pinned hashes. This record is falsified if the shadow clears the
`no <composite> merge` probe and all residual live claims while the 6 genuine-merge probes still
fire and declaration parity holds; or if `research_map/class_separation.py` moves off
`c266dbceca87`, the patch proposal moves off `edeb6588a17b`, or the map snapshot moves off its
recorded sha256.

## Non-claims

Not a gate verdict, not a node transition, not a canonical patch, no rule or schema edit, no claim
about cosmic censorship. The shadow module is a test double and must never be imported from a
production path.

## Files

| path | sha256 |
|---|---|
| `pre_registration.json` | `fbe95b585fcad5e0e020d56b82de466b17bc54426959ec0b98f44e3e5fe2021e` |
| `run_shadow_test.py` | `23f2411f15d2b57ab46241b99d92bc40f1b585792c63138f1483bffeeed902a0` |
| `finalize_report.py` | `0136de5a0c9088a6c3e9ffb15c4a873a9aa2409ae460231f6e692e54565fea00` |
| `shadow_class_separation.py` | `65c4fef0a89bdba1d360c40de5ff6fce4799eda15bdc0945081fcabffe07da6c` |
| `report.json` | `c27f2a0399d2efc220158d78fa0cf1bb1cc896ca117a9eb7be182a38bdcec8f0` |
| `snapshot/MANIFEST.json` | `bf1cb620f11bafa98feee647e629110ecf5d8d192e0385c6567fd8c7878337f4` |
| `snapshot/research_map.pinned.json` | `6d3f0f2792a2d52d4b9c4e2eacd3af6e543e10477c170288c6fd8dc1d8be1b0a` |
| `snapshot/class_separation.canonical.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `raw/probes.json` | `9a66867609ced74d86e57324d2aeef47c3306f959a8dcf9c21d4de992a95db3d` |
| `raw/map_battery.json` | `9ac2b266b1075461ae31f76881e0fd792b6e817c65e118f7d1187c192017a25e` |
| `raw/growth.json` | `0b46d77cf87c79005afb72fd64fb9af0c882821063656f7b7edae9aa5d69fdb6` |
| `raw/acceptance.json` | `e493891f8f76a2dc69f53c82c7ac9e212692c1a93cbe58fa4d1c4b6c0e255ae7` |
| `raw/shadow_provenance.json` | `458a3b70ee248ec4deba6b70f08b84c69f437dc1453d61223bf1d3e8c633eefc` |

Re-run: `python3 artifacts/worker-098/classsep_prose_shadow/run_shadow_test.py` (re-pins against
the live tree; the frozen evidence above is the 00:49:26 snapshot).
