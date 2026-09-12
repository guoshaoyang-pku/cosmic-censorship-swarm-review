# W045-OPENCASE-REBIND-TRANSFER-01 — does the 9-open-case disposition survive the F0 corpus repair?

**Worker:** worker-045 (bounded lifecycle; no inbox card existed for this slot)
**Class binding:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH` (F0 / G-F0)
**Verdict:** `TRANSFER_VERIFIED_BINDING_STALE` — the 7+2 disposition content transfers to the repaired
corpus bytes, but every binding that carries it still points at superseded bytes.
**Authority:** worker measurement only. No canonical artifact was edited; no node status, no
`validation_status=passed`, no gate verdict is claimed.

## Why this task

`schemas/taxonomy_cases.jsonl` (the F0 class-leakage fixture corpus) was repaired at
2026-09-12T00:42 to rebind all 36 row pins to canonical F0 rev5. The repair moved the corpus
`f0c20b96f76d -> ccf7041bd0ff`. The only disposition of the nine `open=true` cases is
`artifacts/flash-02/open_case_disposition.json` (`ee05eb8e7cde`), carried by the operative claim
`flash02-opencase-claim-0010b-supersede-20260912T003552`. At the time of measurement that matrix
still pinned corpus `b9699119bbab` and taxonomy `565a6e505188` (rev3), and the claim pinned corpus
`f0c20b96f76d` — all superseded. Pin-repair verification of the corpus itself existed
(worker-076/094); whether the *disposition content* transfers to the new bytes did not.

## Method (deterministic, read-only)

`run_opencase_rebind_transfer.py` (stdlib + PyYAML, no network) measures, at the pins below:

| pin | sha256 | note |
|---|---|---|
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` | live, post-repair |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | live rev5 |
| `artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl` | `f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8` | claim-pinned snapshot |
| `artifacts/flash-02/open_case_disposition.json` | `ee05eb8e7cdef44e6ab028652185c80f0737603a4d2c5a26c2de3008cb511bcf` | disposition matrix |
| `artifacts/worker-083/f0_open_case_disposition/dispositions.json` | measured in report | independent second matrix |
| `artifacts/flash-02/leak_rule_catalog.json` | `ccec815ea61d5eb235461abb7d829be4a420ea70ba339d9c23221db262fa7fb3` | repaired catalog |

Checks: **B** open-set identity; **C** pin-only repair delta (claim-pinned snapshot vs live, with
declared `CONTENT_KEYS` — any content-key difference is a hard failure); **D** open-row axis vectors
vs every frozen class axis; **E** matrix coverage/token/`CG2` validity; **F** cross-source agreement
with worker-083; **G** binding staleness.

## Result

- **B** live open set = `{N01,N02,N04,N09,N10,N11,N14,N15,N16}` (9) = matrix row set exactly; no
  missing, extra, or duplicate rows.
- **C** across all 36 case rows the repaired corpus differs from the claim-pinned snapshot in exactly
  one key, `binding_status` (36/36); **zero** `CONTENT_KEYS` differences, identical case-id set.
  The repair is a pure pin restamp.
- **D** 0/9 open-row axis vectors equal any frozen class axis vector (nearest: 6/7 keys to
  `AF-WCC-VAC-GEN` for N01/N02/N11, to `AF-WCC-SCALAR-SPH` for N10; N04/N14/N15/N16 overlap only in
  the invariant fields). The new-class / split classifications are not collapse artifacts.
- **E** matrix = 7 `NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI` (all with `coverage_gaps.CG2`) + 1
  `SPLIT_REQUIRED` (N14) + 1 `SPLIT_AND_BRIDGE_REQUIRED` (N15); all tokens declared;
  `frozen_class_ids` equals the four taxonomy class ids.
- **F** worker-083's independently derived matrix reports the same 7 new-class / 2 split split on the
  same 9 open cases (aggregate-level agreement; that artifact carries no per-case array).
- **G** stale: matrix corpus ref `b9699119bbab` != live `ccf7041bd0ff`; matrix taxonomy ref and all
  row taxonomy pins `565a6e505188` != live `0abb9ed8a961`; operative claim corpus pin
  `f0c20b96f76d` != live and the claim has no superseder in the map snapshot.

Controls K1 determinism, K2 open-flag mutation detected, K3 case-id tamper detected, K4 pin-only
restamp invariance, K5 zero drift on all fixed pins — 5/5 pass. The live map moved during the run by
design and is excluded from the drift guard (its measured snapshot hash is recorded).

## Findings

- **F3 (major, owner action):** the disposition matrix and the operative claim are unbound from the
  live corpus. Re-pin the matrix `corpus_ref`/taxonomy refs and the claim's `evidence_refs` to
  `schemas/taxonomy_cases.jsonl#ccf7041bd0ff` + `research_map/formulation_taxonomy.yaml#0abb9ed8a961`,
  then re-review at the new bytes. No disposition verdict changes.
- The corpus-level G-F0 unmet item "9 taxonomy cases remain open and were never dispositioned" is
  satisfied by content (7+2, cross-verified) but not by binding; the corpus rows intentionally still
  carry `open=true` and the matrix remains the disposition of record.

## Falsifier

Any live `open=true` case missing or duplicated in the matrix; any `CONTENT_KEY` difference between
the claim-pinned snapshot and the live corpus; any open-row axis vector equal to a frozen class
vector; a disposition token outside `disposition_tokens`; a `frozen_class_ids` mismatch; or K2/K3/K4
failing to fire. On any of these the transfer claim is void and the matrix must be re-derived.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-045/opencase_rebind_transfer/run_opencase_rebind_transfer.py
# exit 0 iff verdict starts with TRANSFER_VERIFIED; report.json is rewritten deterministically
```

## Limitations

- Measurement is at one instant; if the corpus, taxonomy, or matrix moves, re-measure (pins are
  recorded in `report.json`, check A fails closed on expected-pin mismatch).
- Worker-083's artifact is aggregate-only, so cross-source agreement is at the family-count level.
- Matrix axis vectors were compared as recorded; the script does not re-derive them from prose.
