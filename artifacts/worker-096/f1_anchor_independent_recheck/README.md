# W096-F1-ANCHOR-INDEPENDENT-RECHECK-01

**Worker:** worker-096 (advisory evidence only; no gate verdict, no node status)
**Class / node / gate:** `AF-WCC-VAC-GEN` / F1 / G-FORM
**Trigger:** G-FORM r3 named-open finding `W077-AB-01`/`W077-AB-02` (major, required before
the rev14 / FROZEN rev30 fold) was measured only by its author, worker-077. This task is an
independent non-author re-observation with a pre-registered variant battery.
**Disjoint from prior worker-096 tasks** (binding receipts, containment sweeps, F2b candidate
verification, rev29 re-emission closure, requirement-drop sweep): this is the F1 provenance /
BL-11 anchor surface, not covered by any of them.

## Pins (measured at entry and exit; zero drift)

| path | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13, FROZEN rev29) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/formulation_taxonomy.yaml` (G-F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `ledger/theorems.jsonl` (L0 ledger) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (L0 citation audit) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |

The two ledger corpora are not FROZEN members; they are pinned by hash the way G-LIT / the r3
adjudication cite them.

## Instrument

`check_f1_anchor_bind_096.py` — stdlib + PyYAML, read-only, **imports no worker-077 code**.
Own strict duplicate-key YAML loader, own field-path resolver, own row/occurrence scanner.
The variant battery is pre-registered in the source before the run. `runlog.precheck.txt` is
the first run, in which one A-PREDICT candidate phrase was still classified as a *stem*
variant; it was reclassified to `variant_phrasing` (a refinement, not an anchor) before the
final run recorded in `runlog.txt`. No measured count changed.

## Result — 12/12 checks, 6/6 controls, exit 0

**W096-AB-01 (reproduces W077-AB-01, major).** `provenance.sources` has exactly 5 rows; all 5
carry `identifier=null` and `status=unresolved` while their `needed_for` obligations are
load-bearing. All 7 `needed_for` tokens resolve (6 literal/recovery field bindings + 1 prose
sentinel); the token `quantifiers D2` recovers uniquely to `quantifiers.domains.D2`
(W096-AB-03 = W077-AB-04, minor).

**W096-AB-02 (reproduces W077-AB-02, major, with scope refinement).** At the pinned corpora
all four BL-11 items have **0 occurrences**:

| BL-11 item | citation audit | L0 ledger |
|---|---|---|
| `s>5/2 threshold` | 0 | 0 |
| `delta in (1/2,1)` | 0 | 0 |
| `positive mass theorem` | 0 | 0 |
| `future asymptotic predictability` | 0 | 0 |

The 0-hit result survives every pre-registered formatting rewrite and distinctive-token stem:
`sobolev`, `weighted sobolev`, `5/2`, `(1/2,1)`, `positive mass`, `adm mass`, `mass theorem`,
`predictability` are all 0 in both corpora. Positive controls are live: `cauchy horizon`
30 rows / 58 occurrences (citation) and 27 / 61 (ledger) — reproducing worker-077's 58/61
exactly; `singularit` and `einstein` also non-zero. Fabricated negative controls are 0.

**Refinement (narrows, does not reverse):** A-PREDICT is the only one of the four items with a
registered source under a different phrasing — `SRC-096` *"The future is not always open"* is in
the citation audit and absent from the ledger `source_ids`, consistent with worker-077's
registered-unbound rows. The strong reading "no registered source bears on the concept"
therefore narrows to "no registered source anchors the obligation under the BL-11 naming;
A-PREDICT has one title-level, unbound candidate". A-WSOBOLEV, A-POSMASS and A-WCCSTATUS
obligations remain unanchored under every variant tested.

## Verdict, authority, falsifier

Verdict: `INDEPENDENT_RECHECK_CONFIRMS_W077_AB01_AB02`; `counts_as_full_schema_verdict=false`,
`counts_toward_gate_accept=false`. This is an artifact/finding measurement, not a schema
verdict, not a gate verdict, not a node status, no canonical write.

**Falsifier.** Re-run `check_f1_anchor_bind_096.py` at the same pins: falsified if any
provenance anchor has a resolved non-null identifier; any BL-11 item or normalized/stem variant
has ≥1 hit; any `needed_for` token fails to resolve; a positive control returns 0; or any pin
drifts (drift voids, control failure invalidates). A rev30 write at a new F1 hash voids these
pins and requires a re-run.

**Next falsifier.** If the owner binds an L1 anchor to any `provenance.sources` row, W096-AB-01
and the corresponding BL-11 item both flip; if SRC-096/SRC-097 are bound in the ledger, the
A-PREDICT refinement closes.

## Reproduction

```bash
cd artifacts/worker-096/f1_anchor_independent_recheck
python3 check_f1_anchor_bind_096.py     # exit 0, writes report.json + snapshots/
```

Deterministic: a second run reproduces `report.json` byte-for-byte apart from `created_at`.
