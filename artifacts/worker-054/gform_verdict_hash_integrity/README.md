# W054-GFORM-VERDICT-HASH-INTEGRITY-01 — worker-054

**Class-bound task (self-selected; no inbox card existed for worker-054).**
Bind: nodes `F0`, `F1`, `F2a`, `F2b`; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`; gates `G-FORM` / `G-F0` / `G-AUDIT`.

## Question

For every review verdict in the accepted event stream that could count toward `G-FORM` /
`G-F0`: is the verdict bound to bytes that still exist at the canonical path, and is that
binding attributable to exactly one target? A verdict that cites no target hash, cites several
canonical artifacts at once, or cites a superseded revision cannot count toward a gate
criterion phrased as "two distinct independent accepts at the hash".

## Method (`integrity.py`, read-only on canonical paths)

1. Freeze the inputs once at run start (`frozen_inputs/`): `research_map/events.jsonl`,
   `research_map/research_map.json`, `artifacts/formulation/FROZEN.json`, plus byte copies of
   the four canonical artifacts. The live swarm keeps writing; all analysis runs on the frozen
   copies, which are re-hashed at the end (`frozen_copies_byte_stable`).
2. For every `review` event, collect hashes from `target_id`, `target_sha256`, `cited_sha256`
   and every `evidence_refs` entry, keeping the ref path that carried each hash.
3. Attribute a target binding (strict, single target only):
   - `TARGET_FIELD` — the target fields carry a hash and the target path is canonical (or
     exactly one canonical artifact is cited);
   - `TARGET_PATH` — `target_id` is a canonical artifact path;
   - `SINGLE_CANONICAL_EVIDENCE_REF` — no target-side hash, and exactly one canonical artifact
     path is cited among the evidence refs;
   - `AMBIGUOUS_TARGET` — several canonical artifacts cited at once (cross-target / ledger
     reviews): not attributable, not counted;
   - `NO_HASH_ANYWHERE` → `UNBOUND`.
4. Classify target-side hashes against the canonical snapshot: `VERIFIED_BOUND` (equals the
   snapshot bytes), `STALE_BOUND` (only archived copies of a superseded revision carry it),
   `UNRESOLVED_BOUND` (no live copy carries it), `EVIDENCE_ONLY_HASH` / `AMBIGUOUS_TARGET`
   (no attributable target binding).
5. Per target, count distinct reviewers whose **verdict is bound to the bytes measured at the
   canonical path in this run**.

Falsifier: re-run `integrity.py` on an unchanged tree — any classification change, any frozen
copy that is not byte-stable, or a cited prefix resolving to non-matching bytes falsifies the
corresponding row. Valid only while `drift.run_void == false`.

## Result (measured 2026-09-12T00:58:08+08:00; worker report only, no gate verdict)

Canonical bytes at run start vs the FROZEN pin and the hash the map declares for the node:

| artifact | sha256 (16) | FROZEN rev29 pin | map-declared node hash | map fresh? |
|---|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a96135c9` | equal | `0abb9ed8a96135c9` | yes |
| `schemas/af_wcc_vacuum.yaml` (F1) | `d9cebb9404b2e79e` | equal | `cce9c60146d6a907` | **NO** |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `e9a27996dfd308bd` | equal | `5476a3f2c6bc7196` | **NO** |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `b2ab6acb2bbe7f86` | equal | `55d0a1ea9bda96b8` | **NO** |

484 review events classified:

| classification | count |
|---|---|
| `VERIFIED_BOUND` (target hash = measured canonical bytes) | 19 |
| `STALE_BOUND` (target hash = superseded revision, archived copy only) | 4 |
| `UNRESOLVED_BOUND` (cited hash has no live copy) | 98 |
| `EVIDENCE_ONLY_HASH` (hashes cite support files, not the target) | 185 |
| `AMBIGUOUS_TARGET` (several canonical artifacts cited at once) | 65 |
| `UNBOUND` (no hash cited anywhere) | 113 |

Distinct reviewers with a verdict **bound to the measured canonical bytes**:

| target | accept (bound) | revise (bound) | criterion (≥2 distinct bound accepts) |
|---|---|---|---|
| F0 | deepseek-flash-18, worker-025, worker-038, worker-041, worker-067, worker-087 | astra-lead-audit, worker-003, worker-047, worker-048, worker-067 | **met (6)** |
| F1 | — | worker-018, worker-095 | **not met (0 bound accepts at `d9cebb9404b2`)** |
| F2a | worker-017, worker-072 | worker-066 | **met (2)** |
| F2b | — | worker-044 | **not met (0 bound accepts at `b2ab6acb2bbe`)** |

Measured facts that matter for the gate:

1. **The map's node hashes for F1/F2a/F2b are stale relative to the artifacts and relative to
   FROZEN rev29.** `FROZEN.json` revision 29 (frozen 00:55:02) pins the revision-13 schemas
   `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`, and those are the bytes now at the
   canonical paths; `research_map/research_map.json` still declares
   `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`. The map's own `controller_gate_audit`
   ("F1 [1 accept], F2a [0], F2b [1]") is therefore computed against hashes that no longer
   exist at the canonical paths.
2. **At this snapshot the G-FORM accept criterion is met for F0 and F2a, not for F1 and F2b.**
   F1 has 0 bound accepts at `d9cebb9404b2` and F2b has 0 at `b2ab6acb2bbe`; their bound
   verdicts are revises. The revision-13 wave needs independent accepts for those two schemas.
3. **Self-contradictory bound verdicts at one hash.** `worker-067` has an accept
   (`w067-n0rebind-20260912T003805-20-review`) and a revise
   (`w067-provledger-20260912T005149-20-review`) both bound to the same F0 hash
   `0abb9ed8a961`; `worker-038` filed three accepts at that same hash. A same-hash
   accept/revise pair from one reviewer needs adjudication before either verdict counts as
   independent.
4. **Only 19/484 verdicts are target-bound to current bytes.** 113 cite no hash anywhere and
   65 cite several canonical artifacts at once, so they cannot be attributed to one target;
   185 cite hashes only on support files. A gate scan that counts these rows inflates the
   reviewer count.
5. **Freeze coverage gap for auxiliary gate inputs.** 404 review events cite at least one live
   path that is not covered by the FROZEN pin set. In particular the review files themselves,
   `KEY_MANIFEST`, `rule_spec.json`, the semantic-contract suite
   (`schemas/semantic_contract_tests/manifest.json`, its runner, `observed_verdicts.json`,
   the control/fixture corpus), `schemas/f1_falsifier_tests.jsonl`,
   `schemas/taxonomy_cases.jsonl` and the `schemas/af_scc_c0_vacuum.yaml.sha256` sidecar are
   gate inputs but are not pinned. The sidecar is already stale (revision-11 hash
   `1bb78ce9b357` against current `b2ab6acb2bbe`), which is the freeze-first failure mode the
   audit direction names; this is the measured list of what is still outside the freeze.

Scope: worker report only. No gate verdict, no node status, no `validation_status=passed`, no
canonical artifact modified; every write is under `artifacts/worker-054/`.

## Artifacts (hash-pinned in the emitted events)

- `report.json` — full per-event classification, hash resolutions, per-target counts, flags.
- `summary.json` / `summary.md` — counts, per-target matrix, problem event ids, drift flags.
- `frozen_inputs/` — the exact input bytes analysed (event stream, map, manifest, canonical copies).
- `integrity.py` — reproduce:
  `python3 artifacts/worker-054/gform_verdict_hash_integrity/integrity.py`;
  `emit_events.py` re-pins and re-emits the events/checkpoint from the fresh report.
