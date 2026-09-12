# W090-FCONSEV-REV29-CLOSURE-01

Bounded, class-bound worker audit by **worker-090**. Independent, read-only, hash-pinned
closure measurement of the evidence self-binding residual **F-CONSEV**
(`research_map/research_map.json`, review `w050-20260912T002334`, finding F-CONSEV,
severity minor) and of this worker's own closure criteria **W090-R12-01 / W090-F2A-01**,
at the live post-repair **FROZEN revision 29** bytes.

| field | value |
|---|---|
| node | F2a |
| class | `AF-SCC-C2-VAC-GEN` (corroborating: `AF-WCC-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) |
| gate | G-FORM |
| authority | advisory worker measurement; **no** gate verdict, **no** node status, **no** canonical write |
| task origin | no inbox card existed for worker-090; task taken from the open map residual F-CONSEV plus the worker's own open W090-F2A-01 |
| verdict | **revise** (minor residual open; no class-semantics failure) |

## Question

Astra's `astra-life05-evidence-binding-repair` (REC-12) item (2) required the three class
schemas' `f0_binding.consistency_evidence_sha256` to be refreshed to the live
`artifacts/formulation/evidence/taxonomy_consistency.json` after a clean checker run. That
is the *pointer* clause. Worker-090's rev12 verdict and worker-050's F-CONSEV finding state
a stronger *embedding* clause: the evidence file must itself record the measured hashes of
the two trees it compared, so the `consistent: true` claim is self-binding.

This audit measures, at the post-repair bytes, which clause is closed and which is not.

## Method

`check_fconsev_rev29.py` is an own implementation (no other worker's checker imported). It

1. captures the sha256 pins of every reviewed path and snapshots the reviewed bytes under
   `snapshot/` (canonical files are opened read-only; nothing canonical is written);
2. evaluates the **pointer clause**: declared evidence hash vs measured live evidence hash,
   declared F0 hash vs measured live canonical taxonomy, `checked_at` future-stamp guard,
   canonical-vs-mirror byte equality, and every FROZEN rev29 manifest pin against live bytes;
3. evaluates the **embedding clause**: scans the live evidence text for full 64-hex
   byte-identity witnesses and the schemas' `f0_binding` for any supplement-side hash pin;
4. runs a **sandbox** reproduction and exposure experiment (below);
5. re-measures every pin at the end and reports drift.

Sandbox layout copies the pinned checker, both compared trees, and `VOCAB_ALIASES.json`
into `sandbox/<tag>/` at the path depth the checker expects, so the checker's own
`ROOT` resolves inside the sandbox. The checker writes evidence only there.

## Result (at the pins below)

**Pointer clause: CLOSED.** All of A1–A5 pass: for all three schemas
`declared consistency_evidence_sha256 == measured 9e335e9ba1bf`,
`declared_f0_sha256 == measured 0abb9ed8a961`, `checked_at` is not future-stamped,
canonical bytes == mirror bytes for all three pairs, and all **50/50** FROZEN rev29
manifest pins match live bytes (0 problems). Zero pin drift across the run.

**Embedding clause: OPEN.** 6 of 22 checks fail, all in Part B:

- `artifacts/formulation/evidence/taxonomy_consistency.json` contains **0** 64-hex
  byte-identity witnesses. It records paths (`map_taxonomy`, `lead_contract`), a boolean
  `consistent: true`, and field lists — but not which bytes were compared. Field set:
  `alias_policy, classes_compared, consistent, contract_divergences, errors,
  lead_contract, map_taxonomy, notes`.
- No schema's `f0_binding` hash-pins the supplement side. All three carry only
  `class_contract_supplement: artifacts/formulation/formulation_taxonomy.yaml` and
  `class_contract_supplement_pointer: ...#class_contracts.<class>` — path and key, no
  `*_sha256`.

So **W090-F2A-01 = partially closed** (pointer clause pass, embedding clause open) and
**F-CONSEV = open at FROZEN rev29**. REC-12 item (2) as written did not require the
embedding, so this is not a fault of the bounded repair; it is an unassigned residual
outside that repair's scope.

## Sandbox controls (6/6 as pre-registered)

| id | control | observed |
|---|---|---|
| C0 | unmutated sandbox checker run | rc 0, `CONSISTENT (4 classes, 0 contract-text divergences)`, emitted evidence **byte-identical** to the live evidence |
| C1 | semantic mutation `class_contracts.AF-SCC-C2-VAC-GEN.conclusion_type` → `..._MUTANT_W090` | rc 1, `consistent: false`, error names `AF-SCC-C2-VAC-GEN` + `conclusion_type` |
| C2 | exposure: mutated compared bytes + deployed evidence | declared evidence hash matches the deployed evidence **and** declared F0 hash matches live → every declared binding value still satisfied |
| C3 | compensating control | FROZEN rev29 manifest pin `d7419b4e8963` ≠ mutated sha256 `724e9897ab52` → manifest detects the mutation |
| M1 | pointer-tamper detector | A1 predicate flips on a sandbox `consistency_evidence_sha256` tamper |
| M2 | embedding detector | B1/B2 detectors flip when both tree hashes are injected into a sandbox evidence copy |

C2 is a simulation; no canonical byte was edited. It shows the residual's concrete shape:
with the evidence file left in place, a semantic change to `formulation_taxonomy.yaml`
leaves all three schemas' declared binding values satisfied while the `consistent: true`
claim silently describes different bytes. C3 shows the gap is compensated whenever the
FROZEN manifest verification is run — which is why the residual is scoped **minor** and
is not asserted here to block G-FORM.

## Pins (measured at run; all re-measured unchanged at exit)

| path | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| `schemas/af_wcc_vacuum.yaml` (F1, rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | `de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd` |
| `artifacts/formulation/FROZEN.json` (rev **29** @ 2026-09-12T00:57:26+08:00) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |

Mirrors `artifacts/formulation/schemas/af_*.yaml` are byte-identical to their canonical
counterparts at these hashes.

## Falsifier

Falsified if, at the same pins, (a) the live evidence at `9e335e9ba1bf` contains a full
sha256 of either compared tree or any other byte-identity witness for both; (b) any
schema `f0_binding` contains a 64-hex supplement pin; (c) any A1–A5 pointer/metadata/
manifest check fails; or (d) any of the six controls does not reproduce its pre-registered
outcome. Any canonical byte change after this run makes the measurement historical: re-run
`check_fconsev_rev29.py` and treat this report as superseded.

## Non-claims

- Not a full-schema verdict: quantifiers, topology, physics, vocabulary and class
  semantics are out of scope (`counts_as_full_schema_verdict: false`).
- No gate verdict, no node status, no validation_status promotion.
- No canonical artifact was written or edited; all mutations are under `sandbox/`.
- The audit does not decide whether the embedding clause is *required* for G-FORM; it
  measures that the property is absent and leaves the requirement call to the controller.
- C2/C3 are simulations, not observations of a live edit.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-090/fconsev_rev29_closure/check_fconsev_rev29.py   # exit 0, controls 6/6
```

Outputs: `results.json` (22 checks, verdict), `controls.json` (6 controls + mutation and
exposure detail), `snapshot/` (reviewed bytes + `SHA256SUMS.txt`).
