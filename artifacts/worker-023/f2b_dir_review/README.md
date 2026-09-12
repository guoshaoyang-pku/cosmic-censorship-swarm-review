# W023-F2B-DIR-REVIEW-01 — F2b containment repair: the replacement clause inverts the entailment direction

Bounded independent review at FROZEN rev29 of the *ready* F2b (`AF-SCC-C0-VAC-GEN`)
containment repair. Read-only on every canonical path; worker-level evidence only.

## Why this review exists

Two F2b defects are open and acknowledged (lead-formulation L-FORM-01; worker-008/066):

- **H1** `regularity.must_not_conflate[0]` (:152) denies containment — "No containment with
  C2 or C0 is asserted here" — contradicting the same file's own chain.
- **H2** `implication_ledger.forbidden_transfers[0].reason` (:246) calls C2 "a strictly
  **larger** extension class" while the file's chain makes E_C2 the **smallest**.

The standing repair is worker-066's `f2b_repair_prereg/proposed_patch.diff` (candidate
`84b5d3fa29a6`), rebased from worker-008's `98f9ec83`, and worker-044 has composed it into a
rev14 candidate (`48cadb72e507`) declared "acceptance ready". This review tested whether the
repair is *semantically* finding-free, not merely whether it reproduces and passes the
canonical gate.

## Method

`reproduce_023.py` pins ten inputs (fail-closed on any hash move), reconstructs the 066
candidate by two independent application paths (hunk-block splice and single-line splice),
rebuilds the repair from the published patch with the system `patch` tool, and probes the
replacement sentence against the document's **own** declared entailment graph
(`implication_ledger.one_way_entailments`, transitive closure) and against the declared
extension-set ranks parsed from `extension_class_containment`. The probe is class-relative:
two sentence forms are recognised and each is judged by whether the corresponding edge is
declared. `verify_direction_023.py` re-derives everything through separate code paths.

## Result — verdict `revise` 2.0; hard failure `W023-F2B-DIR1`

The replacement sentence copied verbatim from the C2 sibling reads:

> … so **H2_loc-inextendibility ENTAILS this class's conclusion**; …

For the C2 file that is true (E_C2 ⊆ E_H2loc). For the C0 file it is false and is the
reverse of the document's own declarations:

- `one_way_entailments` declares `no proper future C0 metric extension -> no proper future
  H2_loc extension` — the opposite direction;
- `forbidden_weakenings[2]`: "substituting H2_loc for C0 (H2_loc-inextendibility is weaker
  and entails the C2 sibling, **not this class**)";
- `subsumption_note`: "This direction runs C0 => H2loc => C2, **never the reverse**";
- set ranks: E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2 — absence of the smaller H2_loc extension set
  cannot entail absence of the larger C0 set.

So the H1 repair, as written, licenses exactly the substitution the file forbids; the two
reviewed candidates (`84b5d3fa`, `48cadb72`) are **not** direction-finding-free. All three
carriers of the sentence (worker-008 `98f9ec83`, worker-066 `84b5d3fa`, worker-044
`48cadb72`) share the clause byte-for-byte.

Machine context: the canonical structural gate (`check_class_schema.py`, R06) returns
`pass` for the defective candidates, for a direction-reversed mutant, for a nonsense clause
and for an emptied single item; it fails only when the whole `must_not_conflate` list is
emptied. The gate cannot certify this slot's content.

## Corrected variant (proposed, not applied)

`proposed_af_scc_c0_vacuum_v2_corrected.yaml` — sha256 `9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17`
(`proposed_patch_v2_corrected.diff`), same two repair lines as v1, with the sentence
direction corrected to the document's own order:

> … so **this class's conclusion ENTAILS H2_loc-inextendibility and
> C2-inextendibility, never the reverse**; …

plus the same H2 size-premise fix (`strictly larger` → `strictly smaller (E_C2 subset of
E_C0)`). It passes every probe (Form B valid by declared graph and by ranks), keeps the
live→variant diff confined to lines 152/246 (0-based 151/245), and passes the canonical gate.

## Evidence

| file | sha256 (prefix) |
|---|---|
| `report.json` | `b1d5387663d2` (32/32 checks) |
| `verification.json` | `92b4a18b9a99` (37/37 independent checks) |
| `proposed_af_scc_c0_vacuum_v1_066.yaml` | `84b5d3fa29a6` (= worker-066 declared hash) |
| `proposed_af_scc_c0_vacuum_v2_corrected.yaml` | `9ab32ee39d00` |
| `proposed_patch_v2_corrected.diff` | see `runtime/state/artifact_hashes.json` |
| `reproduce_023.py` / `verify_direction_023.py` | see report |

## Consequence / blocker

Do **not** land `84b5d3fa` or the composed `48cadb72` as the F2b rev14 containment repair.
Land the direction-corrected variant (or an equivalent wording), then re-run the F2b
reviewers at the new hash. Recommended gate hardening: R16-style checks currently verify
that a forbidden transfer is *marked* forbidden; they do not check the entailment direction
of `must_not_conflate` claims against the declared graph, which is how this repair-induced
inversion passed both `84b5d3fa` and the composed candidate.

## Limits and falsifier

Worker-level review only: no node status, no `validation_status`, no gate verdict; landing
is lead-formulation's call. Not a claim about C0/C2 physics beyond the document-internal
entailment direction, and not a claim that the other open F2b families (A2/A6/SEP-6) are
closed. Falsified if: any pinned input moves (verdict void at any other hash); the 066
candidate does not reproduce to `84b5d3fa`; the C0 document is shown to declare the
H2_loc → C0 edge; the C2 sibling sentence is shown invalid; the corrected variant fails the
canonical gate; the diff is not confined to the two repair lines; or any control departs
from expectation. Re-run: `python3 reproduce_023.py && python3 verify_direction_023.py`.
