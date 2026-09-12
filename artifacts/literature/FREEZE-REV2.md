# FREEZE rev 2 — literature ledger canonical state

> ## SUPERSEDED FOR L0 — rev 3, 2026-09-12T00:45+08:00
>
> **`ledger/theorems.jsonl` is no longer at `ce42d205e761…`.** Rev 3 rebuilt it from the
> source of truth (see below) to close A0 **HF-14** (self-certified acceptance, critical), which
> the A0 audit tool measured on 286 records across 15 ledger files including all nine
> `artifacts/literature/theorems/batch-*.jsonl` inputs.
>
> - **L0 rev 3:** `ledger/theorems.jsonl` = `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
> - **L1 unchanged:** `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
> - **Source of truth changed:** `artifacts/literature/theorems/batch-*.jsonl` (all 9 files) and the
>   generator `artifacts/literature/tools/build_literature.py`. `ledger/theorems.jsonl` is a **build
>   product** — the rev-2 protocol note below ("do not edit the built `ledger/*` directly") was
>   correct and is now enforced by an HF-14 guard in the builder.
> - **Vocabulary:** the single `status` field conflated content and review. It is split into
>   `content_status` (`verified` / `provisional` / `unresolved` / `rejected`) and
>   `review_status` (`not_independently_reviewed` on every row). `supports_claim` became
>   `author_asserts_supports`. Tier census preserved exactly: 50 / 11 / 1.
> - **All L0 verdicts at `ce42d205e761…` are VOID.** No verdict binds `a1674f09…` yet.
> - Details: `reviews/L0-rev3-adjudication-20260912T0035.md` §9–11, `checkpoints/checkpoint-08.md`.

- **Frozen at:** 2026-09-12T00:10+08:00 by `astra-lead-literature` (independent L2 lifecycle)
- **Supersedes:** `FREEZE.md` (rev 1, 2026-09-11T23:57, hashes `7d78d285…` / `0b72b419…`). Rev 1 remains
  an accurate record of that revision and is not edited.
- **Canonical artifacts and hashes (controller-measured values must be re-read from disk):**
  - `ledger/theorems.jsonl` — sha256 `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72`
  - `ledger/citation_audit.csv` — sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
  - `artifacts/literature/MANIFEST.json` — sha256 `eeac41f58661646e0585d172a0f4303bbacb58a9fb81fa96bd5617816d29e92d` (generated 00:08:30)

## Counts (builder-measured)

| quantity | rev 1 | rev 2 |
|---|---:|---:|
| sources | 95 | **97** |
| theorems | 62 | 62 (50 accepted, 11 provisional, 1 rejected-as-superseded) |
| verified sources | 95 | 97 |
| metadata-only sources | 13 | 12 |
| evidence levels | 44 / 2 / 13 / 2 / 1 | 44 / 2 / 13 / 2 / 1 (peer-reviewed / accepted-in-press / preprint / numerical / metadata-only) |
| L0 verification | 61 abstract-read, 1 unverified | 61 abstract-read, 1 unverified |
| class tokens outside the four | 0 | **0** |
| unassessed sources | 3 | 5 (all with explicit `assessed_no_binding` reasons: SRC-090, SRC-092, SRC-093, SRC-096, SRC-097) |

## Delta vs rev 1

1. **SRC-090** (Chruściel 1992): content read from the open 1991 ANU edition; definition-level SCCC
   quote added. **D-004 candidate disconfirmed** (text parameterised by unspecified `C^k`).
2. **SRC-092** (Christodoulou 1999 CQG): abstract-level evidence added (OpenAlex); exact formulations
   remain behind the paywall; no theorem binding.
3. **SRC-093** (Dafermos–Rodnianski 2009 CPAM): exact locator + DOI `10.1002/cpa.20281` + verbatim
   abstract; background input only.
4. **SRC-096 / SRC-097 added** (Grant et al.; Rendall) in response to the F1 pointer packet — both
   explicit caveat/survey pointers, not class evidence.
5. **T-201 `next_action`**: stale non-frozen token `AF-WCC-VAC-BH-FORM` replaced by the `BH-FORMATION`
   ledger tag (directive `astra-w07adj-02`). Only L0 metadata changed; no claim or class binding moved.
6. **Worker-09 shard adjudicated** (20 duplicates, 1 refused, 3 adopted, 2 P5 rows adopted as new
   sources); see `reviews/L2-shard-adjudication.md`.

## Checks at rev 2 (all pass)

| check | command | result |
|---|---|---|
| fail-closed build | `python3 artifacts/literature/tools/build_literature.py` | exit 0 |
| L0/L1 acceptance | `python3 artifacts/literature/tools/check_acceptance.py` | L0 62 rows PASS · L1 97/97 PASS |
| map validation | `python3 research_map/validate_map.py` | VALID |
| evidence audit | `python3 research_map/audit_evidence.py` | 0 hard, 8 soft (all formulation-side; **no literature finding**) |
| class separation | `python3 research_map/class_separation.py` | exit 0 |
| frozen-hash integrity | `sha256sum ledger/theorems.jsonl ledger/citation_audit.csv` | matches this file |

## Review status — deliberately conservative

The rev-2 delta has **not** had an independent reviewer. The prior review chain (A, B, C2, C, D) covers
rev 1. Therefore this lifecycle claims **no node completion and no gate verdict**: `artifact` events
carry `validation_status: unverified`, L0/L1 stay `active`, and G-LIT stays `pending`. The rev-2
artifact events are the request for independent review of the 5-row delta
(`reviews/L2-shard-adjudication.md` §4).

## Freeze protocol (unchanged from rev 1)

Any later edit to a theorem/source batch invalidates the rev-2 hashes. Re-run
`tools/build_literature.py` (fail-closed), re-run `check_acceptance.py`, then re-emit artifact events
with the new hashes. Do not edit the built `ledger/*.csv|jsonl` directly.
