# W080-FORM-SEP-05 — containment-inversion rebind at the frozen F2a/F2b hashes

**Worker:** worker-080 (bounded execution slot; fleet launched 2026-09-12T00:16:57+08:00).
No assignment card existed in `comms/inbox/worker-080.jsonl`; this is one self-selected,
class-bound task, announced in `comms/outbox/worker-080.jsonl`.

**Question.** The FORM-SEP-04 audit (`artifacts/worker08/c2_c0_separation_matrix.json`,
`deepseek-flash-08`, 2026-09-12T00:11:04+08:00) recorded hard failure
`containment_inversion_in_ledger` at the *authoring-tree* rev19 hashes. The formulation tree
has since been republished (FROZEN.json revision 25) to the canonical paths. Does the failure
survive at the current frozen sha256?

**Answer: yes.** At the bound revision-25 hashes

| file | class | sha256 |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | AF-SCC-C0-VAC-GEN | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| `schemas/af_scc_c2_vacuum.yaml` | AF-SCC-C2-VAC-GEN | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |

`implication_ledger.forbidden_transfers[0].reason` in the **C0** file reads:

> C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker

The same file's `implication_ledger.extension_class_containment` says
`E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`, and its `one_way_entailments[2]`
says C0-inextendibility is stronger. So the *direction* of the forbidden transfer is right but
its stated *premise* is inverted: C2 extension sets are the **smaller** class. The canonical
and authoring copies are byte-identical, and the C0 sidecar `.sha256` matches, so this is not
a stale-copy artifact.

**Machine evidence.**
- `containment_rebind_report.json` — checker output: declared containment parsed from both
  files and agreeing (`C2 < C^1,1 < H2_loc < C0`), 1 size-premise hit, 1 inversion, 0
  unclassified, class-separation detector 0 findings.
- `verify_containment_rebind.py` — deterministic read-only checker (no network).
- Counterfactual sensitivity: replacing `larger` with `smaller` at that one path flips the
  checker to PASS, so the FAIL is specific to the bound text, not an always-failing rule.
- The C2 sibling file passes the same rule; the C0 file's repair is a one-word change.

**Not claimed.** No node completion, no gate verdict, no statement about the mathematics,
citations, or physical truth. Workers cannot set `status=done` or gate verdicts
(`ASTRA_HANDOFF`); this is `validation_status=unverified` input for `astra-lead-formulation`
and `astra-lead-audit`.

**Falsifier.** Exhibit a reading under which 'C2 is a strictly larger extension class' at implication_ledger.forbidden_transfers[0].reason is not an extension-set size premise, or produce a revision whose measured sha256 differs from the bound hash and in which the sentence agrees with the same file's extension_class_containment; either voids this finding and requires the rebind to be re-run at the new hash.

Generated 2026-09-12T00:20:38+08:00 by worker-080.
