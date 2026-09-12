# W083-REV13-REPAIR-PACKET-01 — apply-ready repair packet for L-FORM-01 + L-FORM-02

**Worker** `worker-083` · **nodes** F1, F2a, F2b · **classes** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN` · **gate context** G-FORM · **base** FROZEN rev28 `2f358f6722d9`

**Authority.** Worker evidence only. No canonical path was written; no gate verdict, node status or
`validation_status` is claimed. Applying the packet to canonical bytes requires controller
authorization (REC-9 freeze-hold). All validation ran inside `sandbox*/` mirrors under this
directory.

## What this is

Two G-FORM blockers are open at the frozen rev28 pins and were independently adjudicated elsewhere:

| blocker | defect | repair source |
|---|---|---|
| **L-FORM-01** | `schemas/af_scc_c0_vacuum.yaml` `implication_ledger.forbidden_transfers[0]` says "C2 is a strictly **larger** extension class" while the same file's chain is `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2` | worker-058 HF-1, worker-060 CS-01, lead-form `lead-form-20260912T004452-02` |
| **L-FORM-02** | all three schemas declare `f0_binding.consistency_evidence_sha256 = 675a99d0…` while the canonical evidence path holds the checker summary `9e335e9b…` | worker-096 adjudication **O3**, worker-086 root cause |

This artifact integrates both into one apply-ready packet, validates the **combined** result in an
isolated mirror, and measures exactly which pinned entries move. It does not re-derive either
repair and does not re-open the freeze.

## Result — `PACKET_VALIDATED`, 36/36 checks

| family | checks | outcome |
|---|---:|---|
| P01 pins + FROZEN rev28 | 7 | 44/44 manifest pins match disk |
| B baseline mirror | 4 | `verify_frozen.py` exit 0; canonical gate pass on F1/F2a/F2b; the unpatched checker reproduces the summary evidence `9e335e9b` |
| A L-FORM-01 | 5 | exactly 1 word changed in both mirrored copies; gate still passes; directional audit clean after, flagged before |
| B L-FORM-02 (O3) | 6 | enriched `675a99d0` restored; default checker run is a dry-run; `--write` emits tree hashes; diff applies with GNU `patch --dry-run` |
| B candidate rev29 | 5 | re-freeze exit 0; `verify_frozen.py` exit 0 at rev29; exactly 4 pinned entries move; declarations match the re-pinned evidence |
| C mutants/controls | 6 | 6/6 mutants caught, incl. drift-free re-freeze and dry-run write protection |
| V verdict census | 1 | 27 review files cite the voided F2b hash; F1/F2a hashes do not move |
| X confinement | 1 | all 12 canonical hashes unchanged at exit |

**Measured hash moves (expected and only these four):**

| path | rev28 | candidate rev29 |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda…` | `3cdcaa44e6f1…` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | `55d0a1ea9bda…` | `3cdcaa44e6f1…` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf…` | `675a99d0d25b…` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | `de356d999ea3…` | `5094870c7f74…` |

F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, canonical F0 `0abb9ed8a961`, supplement `d7419b4e8963` are
byte-unchanged, so verdicts bound to those hashes are **not** voided by this packet. F2b verdicts
bound to `55d0a1ea` are void; the census (file-citation level, coarse) lists 27 review files citing
that prefix — re-verification must follow the hash move. Candidate rev29 manifest:
`work_repair/artifacts/formulation/FROZEN.json` = `714f4683015a…` (verify_frozen exit 0, 44 files,
0 problems). It is a **candidate**: only a re-freeze on canonical bytes makes it the manifest.

## Apply steps (from `packet.json`, all commands at repo root)

```bash
python3 artifacts/formulation/tools/verify_frozen.py                      # step 1: rev28 intact
patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/af_scc_c0_vacuum--LFORM01.patch.diff
patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff
cp artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json \
   artifacts/formulation/evidence/taxonomy_consistency.json                # step 3: restore 675a99d0
patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/check_taxonomy_consistency--O3-guard.patch.diff
python3 artifacts/formulation/tools/regenerate_frozen.py --revision 29 \
   --delta "L-FORM-01 wording repair (F2b) + L-FORM-02 O3 evidence restore/guard" --at <ISO8601>
python3 artifacts/formulation/tools/verify_frozen.py
python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_scc_c0_vacuum.yaml
python3 artifacts/formulation/tools/check_taxonomy_consistency.py           # DRY-RUN + CONSISTENT
```

Recommended ordering matches the lead: **repair before** spending the 02:15
`astra-life04-verify-gform-r2` F2b budget, because the F2b re-verification target hash changes.

## Why O3 rather than refreshing the three declarations (O2)

The lead's L-FORM-02 note proposed folding a `consistency_evidence_sha256` refresh into the same
rev13 — that moves all three schema hashes and voids every F1/F2a/F2b verdict. O3 instead makes the
canonical path hold the **already existing enriched bytes** the declarations name, patches the
checker so no default run can destroy them again, and re-freezes one manifest revision. Measured
consequence: 2 schema hashes move instead of 6, and the F1/F2a verdict population survives. This
packet implements O3 and records the alternative as a documented falsifier.

## Controls (all in `evidence.json`; each has an expected/observed and a falsifier)

- `C01` flipped chain → `DIR-3` finding; `C01b` `weaker`→`stronger` → `DIR-2` finding.
- `C02` half-applied repair (one mirrored copy only) → mirror-equality check fails.
- `C03` summary evidence left in place → declaration-vs-measured check fails.
- `C04` mutated taxonomy (empty `exclusions`) → repaired checker exits 1 **and** writes nothing.
- `C05` drift-free re-freeze of an untouched mirror → 0 entries drift, key set unchanged.
- `B04` the unpatched checker on the frozen tree reproduces exactly `9e335e9b` (defect reproduction).
- `X01` all canonical hashes unchanged across the run (read-only proof).

## Falsifiers

Re-run `build_and_validate.py`; the packet is falsified if any of: the repaired F2b still contains
"strictly larger" or fails the directional audit; a default patched-checker run changes the evidence
bytes; candidate rev29 `verify_frozen.py` is non-zero; more or fewer than the four intended entries
move; any F1/F2a/F0 byte changes; an extension-set reading exists in which `E_C2` strictly contains
`E_C0`; the emitted diffs stop applying to the pinned bytes.

## Limits

- The directional grammar (`DIR-1/2/3`) is a packet-internal check over ledger reason strings; it is
  not a re-derivation of the worker-058/worker-060 containment checkers. It exists to make the
  L-FORM-01 before/after measurable, and is itself control-tested.
- The verdict census counts review **files that cite** a hash prefix, not adjudicated verdict rows;
  a review citing several hashes appears in several lists. It is a scope bound, not a verdict count.
- Candidate rev29 is built only in the mirror and carries the build timestamp; a canonical re-freeze
  at a different `--at` yields a different manifest hash but the same 44 file pins.
- No mathematics, no physical claim, no gate verdict, no node transition.
