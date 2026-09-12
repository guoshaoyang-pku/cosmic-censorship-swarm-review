# W007-CLAIM42-INDEP-VERIFY-01 — independent verification of map claim `w072-20260912T001917-claim-conclusion-poor`

Actor: `worker-007` (bounded execution worker).  Class: `AF-WCC-SCALAR-SPH`.  Node: `L1`.
Gate context: G-LIT / G-FORM evidence only — **no gate verdict, no node transition**.

## Task

Take one class-bound task: independently verify (or falsify) the open map claim

> `w072-20260912T001917-claim-conclusion-poor` — at `research_map/formulation_taxonomy.yaml#276009f4f63d`,
> `ledger/theorems.jsonl#ce42d205e761`, `ledger/citation_audit.csv#315c19145065`: no entry bound to
> `AF-WCC-SCALAR-SPH` discharges the class's WCC conclusion and no bound entry names the class's
> genericity notion (H4); 5/10 are mechanically in-class (H1-H3).

The claim's own falsifier: a class-bound entry passing H1-H3 that names an explicit genericity notion
with topology, carrying `conclusion_type=weak_cosmic_censorship`; or a class-conforming WCC entry
omitted from the bound set.

The prior evidence for this claim was its author's own report
(`artifacts/worker-072/scalar_sph_class_audit/spotcheck_report.json#4d931de7b4de`).  This bundle is
the independent check: written from scratch, importing none of worker-072's code.

## Verdict at the pinned bytes: **CONFIRMED**

| measurement | result | worker-072 | agree |
|---|---:|---:|---|
| ledger entries bound to the class | 10 | 10 | yes |
| bound entries with `conclusion_type=weak_cosmic_censorship` | **0** | 0 | yes |
| bound entries naming a positive genericity notion (strict H4, any topology rule) | **0** | 0 | yes |
| falsifier witnesses in the full 62-entry ledger | **0** | — | — |
| unbound class-conforming WCC omission candidates | **0** | — | — |
| bound entries H1-H3 under the reconstructed worker-072 rule | 5 | 5 | yes |
| bound entries H1-H3 under a strict rule (3+1 ∧ Einstein ∧ scalar, non-negated spherical, AF) | 0 | — | rule-dependent |

Two rule-quality findings about the claim's *sub-assertion* "5/10 mechanically in-class", neither of
which changes the verdict:

1. **H1 is vacuous for bound entries.** Worker-072's H1 column ("scalar token") is satisfied by the
   class id `AF-WCC-SCALAR-SPH` itself for all 10 bound entries; the strict H1 count (explicit
   3+1 + Einstein/Lambda=0 + massless-scalar content) is 0/10.
2. **H2 is a substring hazard.** Its "spherical token" test passes `T-105` and `T-106`, whose only
   occurrences are inside `non-spherical` (`T-106`'s ledger tag is literally `NON-SPHERICAL`). A
   negation-guarded H2 excludes both.

The reconstructed worker-072 rule reproduces its published per-entry H1/H2/H3 table exactly
(`per_entry_mismatches: []`); the disagreement is about rule semantics, not about the data.

**Secondary observation:** both pinned inputs had already drifted when this task ran (F0 taxonomy
live `0abb9ed8a961`, ledger live `a1674f094979` at finish; the ledger moved `ce42d205e761` →
`3e3d3553…` → `a1674f09…` within minutes). Re-running the same scan on the live ledger gives the same
counts (bound 10, H1-H3 5 under the reconstructed rule, genericity 0, WCC 0, witnesses 0). The claim
survives the revision; the claim itself still binds only to `ce42d205e761`.

## Files

| file | role |
|---|---|
| `verify_claim42.py` | independent checker (stdlib + PyYAML only, no worker-072 code) |
| `report.json` | machine-readable report: pins, per-record classification, controls, cross-checks, verdict |
| `snapshot/formulation_taxonomy.276009f4f63d.yaml` | pinned F0 taxonomy (hash-verified copy) |
| `snapshot/theorems.ce42d205e761.jsonl` | pinned ledger (hash-verified copy; pre-rev3 archive) |
| `snapshot/citation_audit.315c19145065.csv` | pinned citation audit (hash-verified copy) |
| `SHA256SUMS.txt` | hashes of this bundle |

## Controls (all pass)

* positive fixture (spherical + massless scalar + 3+1 + AF + comeager/Baire topology + WCC
  conclusion) qualifies as a falsifier witness — true;
* six mutation fixtures (drop scalar / drop spherical / drop AF / drop genericity / wrong conclusion
  type / unbound-but-conforming) behave exactly as specified;
* determinism: two independent classification passes give identical digests;
* binding: all three snapshot hashes equal the pinned values (fail-closed `SystemExit(2)` otherwise);
* the unbound-but-conforming fixture is flagged as an omission candidate, which is exactly the
  claim falsifier's second clause.

## Falsifier (what would overturn this verification)

Re-run `verify_claim42.py` against a later pinned revision: this verification is falsified if any
ledger entry passes H1-H3, names a positive genericity notion with a topology in its genericity or
statement fields, and carries `conclusion_type=weak_cosmic_censorship`; or if an unbound
class-conforming WCC entry exists.  A revision change alone supersedes — it does not falsify — this
verification.

## Non-claims

Worker evidence only: not a node `done`, not a gate verdict, no `validation_status` upgrade, no
canonical artifact edited.  Classification is token-mechanical over entry metadata and asserts
nothing about the physics of cosmic censorship; it cannot certify that a named genericity notion is
coherent (F0 records H4 as `machine_checkable: false`).
