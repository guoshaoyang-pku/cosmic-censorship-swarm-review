# W039-REV13-BINDCHAIN-01 — independent evidence-binding-chain verification for the G-FORM repair

Worker-039, bounded execution worker. One class-bound task taken from the open critical path at
intake (no inbox card existed for worker-039).

- **Classes:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b)
- **Node / gate:** F1,F2a,F2b / `G-FORM`
- **Controller basis:** `CF-20` (stale evidence-binding chain), `REC-12`
  (`astra-life05-evidence-binding-repair`, four bounded items), `CF-24` (F0 frozen)
- **Authority note:** worker verdict. Sets no node status, no `validation_status`, no gate
  verdict, and edits no canonical artifact. Its only writes are in this directory.

## Result at a glance

| state | bytes | verdict |
|---|---|---|
| pre-repair, 2026-09-12T00:52 | F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, F2b `55d0a1ea9bda`, FROZEN rev28 `2f358f6722d9` | `PENDING_REPAIR` — 29 checks, 23 pass, 0 fail, 2 recognised CF-20 defects, 4 info |
| repaired, 2026-09-12T00:59 | F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, FROZEN rev29 `815e08079aef` | `CONSISTENT_WITH_FINDINGS` — 32 checks, 26 pass, **0 fail**, 2 findings, 4 info |

The binding chain is **complete at the repaired bytes**: every declared hash equals the live file,
the consistency evidence is a fresh reproducible product of its checker, the case corpus is bound
to the declared F0 hash, the FROZEN rev29 manifest matches every listed file and logical artifact,
the key manifest covers every schema key, and the binding gate exits 0 on all three schemas.

Two findings survive, both reported rather than silently promoted:

- **`I` — the F1 strict-core digest moved, and the move is confined to `quantifiers.D5`.** That is
  the REC-12 item (3) assertion-direction correction (`strictly STRONGER` → `EQUIVALENT` for the
  whole-curve reading of a causal geodesic), not an unlicensed semantics drift. F2a and F2b cores
  are byte-identical to rev12. Audited by checks **J** (F1 document-internally consistent, PASS) and
  **K** below.
- **`K` — the G-F0-frozen declared taxonomy still asserts the opposite direction.** F1 rev13 says
  the whole-curve and single-q tail readings are EQUIVALENT for causal geodesics; the frozen
  `research_map/formulation_taxonomy.yaml` still calls the set-based reading "strictly stronger" at
  two live lines (94, 200). The FROZEN rev29 note itself records this as residual blocker
  L-FORM-03. `check_taxonomy_consistency.py` returns CONSISTENT because it compares
  family / regularity / conclusion_type / genericity and **not** predicate strength, so a clean
  consistency report does not clear this. The F0 bytes are G-F0-frozen, so the divergence cannot be
  repaired without voiding G-F0 — it needs lead/Human-PI adjudication, not a worker edit.

## Why this task

CF-20 says the binding chain at the frozen rev12 bytes is self-contradictory: the case corpus was
bound to the superseded taxonomy `66bf917bd368` and all three schemas declared consistency-evidence
`675a99d0…` while the live evidence measured `9e335e9ba1bf`; the schemas' own binding rule forbids a
gate verdict until that is refreshed. REC-12 authorizes a four-item repair; `astra-life05-verify-gform-r3`
re-reviews at the repaired pins.

What did not exist was a machine, independent of the repair author, that measures the whole chain
end to end and reads REC-12's own falsifier — *"any change to a class definition, hypothesis,
conclusion predicate or axis semantics"* — off the bytes rather than off the author's report. This
artifact is that machine, plus the two audits the repair's item (3) needs.

## The tools

| file | role |
|---|---|
| `verify_binding_chain.py` | fail-closed chain verifier (checks A–K); exit 0 `CONSISTENT`/`CONSISTENT_WITH_FINDINGS`, 3 `PENDING_*`, 1 `BROKEN`; writes only its `--out` report |
| `schema_fingerprint.py` | partitions every top-level schema key into structural core / allowed prose / metadata and hashes each; the cross-revision digest is taken over the keys the pre-repair baseline measured |
| `recover_rev12_baseline.py` | recovers the exact rev12 bytes from six independently written, hash-verified snapshots and recomputes the baseline; refuses any candidate that does not match the rev12 pin |
| `check_f1_strictness.py` | check J: the F1 document is internally consistent with the direction it now asserts (tail predicate stated; WEAKER asserted; old direction absent outside a revision note; witness + falsifier present; no conclusion inflation; identity unchanged) |
| `check_f0_f1_direction.py` | check K: per-target live-vs-historical polarity of the set-based reading against repaired F1, citing line numbers |

Checks (each records declared / measured / status — never a bare boolean):

| id | what it measures |
|---|---|
| A | each schema's `declared_f0_sha256` and `class_contract_supplement` hash to the live files; one and the same F0 pair across all three |
| B | all three schemas declare one and the same consistency-evidence path and sha |
| C | that declared sha is the live evidence bytes; evidence `consistent: true`, no errors/divergences; names the declared taxonomy and supplement; class set covers the three schema classes and equals the declared taxonomy's |
| D | the evidence file is a fresh deterministic product of `check_taxonomy_consistency.py` (re-run must reproduce the declared bytes; original restored and hash-verified) |
| E | `taxonomy_cases.jsonl`: 1 meta + 36 case rows; meta and every row-status token carry the declared F0 sha; the stale predecessor appears nowhere |
| F | `FROZEN.json`: every listed file and logical artifact exists and hashes/sizes to its declared value; manifest pins equal measured schema pins |
| G | `KEY_MANIFEST.json` covers every key used by the three schemas (R22 regression guard) |
| H | `check_class_schema.py` exits 0 on each schema at the measured bytes |
| I | strict-core semantics vs the recovered rev12 baseline, with a field-level diff for any move |
| J | F1 visibility strictness correction is document-internally consistent |
| K | F0/supplement/registry/variant-delta direction polarity vs repaired F1 |

Reproduce (read-only except for this bundle):

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-039/rev13_binding_chain/recover_rev12_baseline.py     # exit 0, rewrites the baseline
python3 artifacts/worker-039/rev13_binding_chain/verify_binding_chain.py \
    --label rev13 --out artifacts/worker-039/rev13_binding_chain/report_rev13.json
```

## Result 1 — pre-repair run (rev12 / FROZEN rev28): `PENDING_REPAIR`

29 checks: 23 pass, 0 fail, 2 recognised-pre-repair, 4 informational. Item (1) of the repair (the
corpus rebind) had already landed; item (2) (the schema evidence pins) had not:

| link | declared | measured | status |
|---|---|---|---|
| F1 / F2a / F2b | — | `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda` | pins |
| F0 declared taxonomy | `0abb9ed8a961…` | `0abb9ed8a961…` | PASS |
| corpus meta + 36/36 rows | `0abb9ed8a961…` | `0abb9ed8a961…` | PASS |
| stale `66bf917bd368` in corpus | — | 0 occurrences | PASS |
| schema `consistency_evidence_sha256` | `675a99d0d25b…` | live `9e335e9ba1bf…` | KNOWN_PRE_REPAIR |
| checker re-run reproduces evidence | declared `675a99d0…` | reproduced `9e335e9b…` | KNOWN_PRE_REPAIR |
| FROZEN rev28, 44 files + 2 logical artifacts | — | all present and hash-matching | PASS |
| `KEY_MANIFEST` key coverage | — | 0 uncovered | PASS |
| `check_class_schema.py` F1/F2a/F2b | — | exit 0 / 0 / 0 | PASS |

## Result 2 — repaired run (rev13 / FROZEN rev29 `815e08079aef`): `CONSISTENT_WITH_FINDINGS`

32 checks: 26 pass, **0 fail**, 2 findings, 4 informational (supplement declared without its own sha
— by design, it is covered by the FROZEN `logical_artifacts` block).

Full mechanical result: all six binding links above now measure declared == live, the evidence
reproduces byte-identically, `taxonomy_cases.jsonl` hashes `ccf7041bd0ff`, FROZEN rev29 lists 44
files + 2 logical artifacts all matching, `KEY_MANIFEST` has 0 uncovered keys, and the gate exits 0
on all three schemas. Check J passes 5/5. Check K finds the two F0 lines above.

**Baseline recovery.** The first baseline was captured live while the repair was in flight, so the
raw rev12 bytes were not archived. `recover_rev12_baseline.py` re-verifies and re-reads the exact
rev12 files from snapshots six other agents had written under hash-verified names
(`artifacts/worker-060/rev29_binding_acceptance/snapshots/`, `artifacts/worker-007/rev29_preflight/snapshot/`,
`artifacts/worker-080/semct_rebase/stage/`, `artifacts/worker-032/f1amb25/pinned/`), and refuses any
candidate whose sha256 does not equal the rev12 pin recorded in `report_pre_repair.json`. The
recovery record is `rev12_recovery.json`; F2a/F2b recovered strict cores are byte-identical to the
repaired ones, which is the control that the recovery is sound.

## Falsifier (this artifact)

- One hash-pinned link where a declared value differs from the measured live bytes at the bytes the
  report names — re-running the tool flips the verdict.
- A strict-core field other than F1 `quantifiers` moving between the recovered rev12 baseline and
  the live bytes — check I reports it as FAIL, not as an authorized correction.
- `K` is falsified by showing the two F0 lines are historical or non-operative, or that the F0 text
  has been amended (which re-opens G-F0).
- The tool's own re-run is the falsifier: it re-measures everything from disk and reads no prose
  claim, no README and no repair report.

## Bounds and non-claims

Read-only w.r.t. canonical artifacts. The only write outside this directory is the checker's own
deterministic rewrite of `artifacts/formulation/evidence/taxonomy_consistency.json` during check D,
restored byte-identically and hash-verified (`D.evidence_bytes_restored`). No gate verdict, no node
status, no claim promotion, no ledger edit, no F0 or schema edit. This artifact does not assert that
the repaired schemas are mathematically correct, that variant SET is or is not a separate class, or
that G-FORM should pass — only what the binding chain measures and where the direction text still
disagrees.
