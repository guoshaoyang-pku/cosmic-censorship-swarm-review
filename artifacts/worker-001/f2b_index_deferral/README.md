# W001-F2B-INDEX-DEFERRAL-ADJUDICATION-01

Bounded execution worker `worker-001` · class `AF-SCC-C0-VAC-GEN` · node `F2b` · gate `G-FORM` ·
one class-bound task, then exit. No assignment card existed in `comms/inbox/worker-001.jsonl`;
the task was proposed from the live G-FORM blocker list and from findings W077-HF-01 / W015-HF-01.

## Question

The declared F0 taxonomy's C0 conclusion reads *"For every admissible (s,delta) there is a comeager
set G_{s,delta} …"*, while the F2b class schema quantifies *"forall r in D0"* with
`D0 = r = smooth | r = (sobolev,s,delta)`. Is that a **semantic contradiction between two frozen
statements of the same class**, or a **documentation gap licensed by F0's own deferral**? The answer
decides the price of closing it: a controller adjudication record (zero canonical hash moves) versus
an F0 edit (hash cascade through three schema bindings and every verdict bound to them).

## Verdict — `LICENSED_DEFERRAL` (7/7 mutation controls pass)

Measured at **FROZEN revision 29** (manifest re-issued 00:57:26; class pins unchanged from the
00:55:02 manifest): F0 canonical taxonomy
`0abb9ed8a961…`, supplement `d7419b4e8963…`, F2b `schemas/af_scc_c0_vacuum.yaml` revision 13
`b2ab6acb2bbe…`, F2a `e9a27996dfd3…`, F1 `d9cebb9404b2…`, consistency evidence `9e335e9ba1bf…`,
checker `de356d999ea3…`. All eight deferral-license conditions hold:

| id | condition | measured |
|---|---|---|
| L1 | F0 scope_statement delegates provisional fields to the downstream schema nodes, naming F2 for the two AF-SCC classes | present |
| L2 | F0 C0 hypothesis H3: `owned_by: F2`, `unresolved: true`, names topology **and** data spaces | present |
| L3 | F0 C0 `provenance.schema_owner` names `F2b` / `schemas/af_scc_c0_vacuum.yaml` | present |
| L4 | frozen supplement C0 `data_class_freeze`: smooth-with-decay default + Sobolev variant (s > 5/2, delta in (1/2,1)) | present |
| L5 | F2b D0 tagged union with smooth and Sobolev branches; both formal statements bind `forall r in D0` | present |
| L6 | F2b `f0_binding.declared_f0_sha256` equals the measured taxonomy hash | equal |
| L7 | no clause of the F0 C0 contract freezes the index domain as final/authoritative | none found |

The divergence is therefore **real as text** (O1: the F0 conclusion never names the smooth branch;
O2: it carries no deferral clause) but **not a semantic contradiction**: F0 explicitly cedes the
topology and data spaces to F2 as unresolved, names F2b as schema owner, and its own scope_statement
says provisional values "must be replaced, not inherited silently"; the frozen supplement freezes
exactly the data class F2b implements. The operative index domain is F2b's D0.

### Disposition (advisory to the controller / lead-formulation)

- **Zero-hash-move path:** a controller adjudication record at these pins discharges W077-HF-01 as
  documentation staleness — no canonical artifact changes, no verdicts voided.
- **If textual hygiene is preferred instead**, the cascade block measures a representative minimal
  F0 edit: 1 taxonomy entry + 1 FROZEN logical entry move, **3 schema re-binds**, and a
  time-dependent at-risk review-record count (**50** at snapshot 00:58:11 over 163 files, **54** at
  the final re-verification over 166 files; `report.json` carries the final snapshot and the corpus
  grows during the run).
- **New minor findings:** F2b names the supplement but pins no supplement hash, while the license
  depends on supplement `d7419b4e8963…` (O3 — recommend `class_contract_supplement_sha256` at the
  next revision); the canonical consistency checker compares taxonomy vs supplement only and
  presence-checks `data_class_freeze`, so `consistent: true` cannot certify the index domain (O5/O6).
- **Scope:** W077-HF-02 is **closed** by the rev13 repair (declared evidence hash now equals the
  measured `9e335e9ba1bf…`, O8). W077-HF-03 (`citation_status=verified_by_L1` on five ledger rows)
  is **still open** at rev13 (O10) and is not adjudicated here.
- **Caveat:** the supplement's "identical across F1/F2a/F2b" is annotation-level (W060 measured
  15/15 data-space-core keys equal on the licensed pair, two annotation paths differing); the
  license needs only the two regularity branches, which both carry.

## Falsifier

Re-run `adjudicate_index_deferral.py` (exit 3 without a verdict on any pin drift, exit 4 on control
failure). At the pinned hashes the verdict is falsified by: a clause in the F0 C0 contract that
freezes the index domain; the supplement lacking the smooth-with-decay freeze; F2b D0 lacking the
smooth branch; a pinned definition of "admissible (s,delta)" that already includes the smooth
branch; or FROZEN not pinning the supplement as a logical artifact.

## Provenance note (drift caught live)

The task was first pinned at 00:55:19 against FROZEN rev28 / F2b rev12 (`55d0a1ea9bda…`). The
pass-05 evidence-binding repair landed at 00:53:20 (F2b rev13, FROZEN rev29), so the harness's
start-of-run drift guard rejected the stale pins and exited 3 without emitting anything. The whole
run was re-anchored to rev29; `report.json` binds only to the rev29 hashes above.

A second manifest rewrite followed: `artifacts/formulation/FROZEN.json` changed bytes
(`3d9e3d77fd87…` → `815e08079aef…`) at 00:57:26 **while keeping the revision label 29**, adding the
life05 repair reports (50 files). All seven substantive class/F0 pins were unchanged, so the
adjudication was re-anchored once to the rewritten manifest and the report re-issued
(`b244f1750736…`). Downstream citations should bind to the class pins, which are the stable anchor,
not to the manifest bytes.

## Files

| file | role |
|---|---|
| `adjudicate_index_deferral.py` | fail-closed harness: pre-registered decision rule, 7 mutation controls, cascade measurement, canonical writes = 0 |
| `PINNED.json` | the 12 input pins (re-anchored to rev29) |
| `report.json` | checks L1–L7 + O1–O10, controls CT1–CT7, cascade, disposition, falsifiers |
| `sandbox/patched_formulation_taxonomy.yaml` | representative F0 edit used only for the cascade count (not a proposal; never applied) |
| `CHECKPOINT.json` | worker checkpoint |
| `reviews/F2b-index-deferral-worker-001.json` | review record: W077-HF-01 accepted as fact, dispositioned advisory |

## Non-claims

No theorem, no counterexample, no numerical result, no node completion, no gate verdict. This is a
worker measurement and adjudication bound to the pinned hashes only. Worker events cannot set
`status=done`, `validation_status=passed`, or a gate verdict.
