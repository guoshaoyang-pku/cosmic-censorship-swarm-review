# W092-PUBCONF-01 — publication & class-binding verification (worker-092)

**Verdict: FAIL on 1 of 21 hard checks** — the three schema pairs are published aligned and
gate-green; the F0 taxonomy pair is not byte-identical, and the publication window was raced by
its own freeze manifest.

- Actor: `worker-092` · Node: `F0/F1/F2a/F2b` · Gates: `G-F0`, `G-FORM`
- Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- Authority: measurement only. No gate verdict set, no shared artifact edited.
- Report: `artifacts/worker-092/pubconf/report.json`
- Falsifier: re-run `verify_pubconf.py` against the same `pinned_run/` copies; the report is
  falsified if a hard check recorded pass fails on those copies (or a recorded fail passes).

## Snapshot (all verdicts bind these hashes, never a path alone)

| artifact | sha256 (snapshot B, 2026-09-12T00:21:37+08:00) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1) | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| `research_map/formulation_taxonomy.yaml` (F0 canonical) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 authoring) | `c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f` |
| `artifacts/formulation/FROZEN.json` | `af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b` (rev 25) |

Schema tooling pin: `check_class_schema.py` = `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff`
(live tool hash re-verified equal to the pinned copy at run time).

## What passes (machine-checked)

- **F1/F2a/F2b canonical == authoring, byte-identical** (H1).
- **FROZEN rev25 pins all 12 checked entries to the measured bytes** (H2); `verify_frozen.py`
  exit 0 (S1).
- **Canonical structural gate accepts all three pinned schemas**, `verdict=pass`,
  `failed_rules=[]` (H3); `class_separation.findings` empty on all three (H4).
- **Class binding**: every `class_id` is one of the frozen four and is present in the canonical
  taxonomy class set; the C2/C0 sibling declarations are reciprocal (H5).
- **`f0_binding.declared_f0_sha256` = the canonical taxonomy snapshot hash** in all three
  schemas (H7); `class_components` reproduce each `class_id` (H8).
- `run_acceptance.py` **PASS** on live canonical paths: 3/3 canonical schemas pass both stages,
  union caught 31/31 mutants, 2/2 controls accepted (S7; log pinned by sha256).
  `check_taxonomy_consistency.py` exit 0, "CONSISTENT (4 classes, 0 contract-text divergences)" (S2).

## Findings

1. **W092-H1-F0 (major, standing).** The F0 pair is not byte-identical: canonical
   `276009f4f63dbf83` (35129 B) vs authoring `c8e979a1eb48969b` (20921 B). The canonical-path
   policy requires the authoring tree to be published byte-identically before review verdicts
   bind, and the controller's own `publication_status` records this pair as `divergent` (CF-13).
   Counter-consideration, recorded honestly: the two files are structurally different
   (canonical has `class_ids`/`classes`; authoring has `class_contracts`), and
   `check_taxonomy_consistency.py` compares them field-by-field and exits 0. If the gate owner
   rules they are distinct artifacts rather than a mirror pair, H1-F0 should be reclassified —
   that is a policy decision, not a measurement this tool can make.
2. **W092-H6 (info, ×3).** Each schema's `class_contract_pointer` targets
   `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<CLASS>`. The dotted key
   dereferences in the authoring tree only; the canonical taxonomy has **no** `class_contracts`
   key, so the class contract is not reachable from the canonical artifact under the declared
   path. Combined with finding 1, class identity is machine-checkable at the *authoring* tree
   and only field-comparable at the canonical one.
3. **W092-S3 (major, process).** `leadform-blocker-0005` asks for verification at
   `68392dd82050…` (F1), `4f97273ef440…` (F2a), `a2aef5ac7fe3…` (F2b), `0fcc6a1928fd…` (F0).
   None is on disk now; all four were superseded by the 00:18:26–00:19:14 rewrites. The request
   was written after its own "final" hashes had already been replaced. (The blocker's
   `created_at` is future-stamped; see finding 4.)
4. **W092-S5 (minor, clock).** FROZEN rev25 declares `frozen_at 2026-09-12T00:42:00+08:00` but
   was written at `00:19:46` — skew 1334 s. Consistent with controller finding CF-14; a
   "binding at measured_at" claim cannot rest on declared timestamps.
5. **W092-S6 (major, window).** Snapshot A (00:19:1x) caught FROZEN **rev24 stale for 8 files**
   against the bytes then on disk; rev25 was regenerated during this verification window and now
   matches (H2/S1 pass). The interval in which "frozen" did not denote the published bytes is
   pinned in `pinned/` and in `report.json` check S6.

## Limits

- Binds mathematical content not at all: this is hash identity, dereferenceability, and the two
  project gates' own machine verdicts. It is **not** the independent mathematical review the
  gates still need, and it claims no gate verdict.
- The publication window was live; S4 re-hashes the canonical paths after the checks and reports
  any write. A future rewrite retires this report for the affected artifact and requires a re-run
  on fresh bytes.
