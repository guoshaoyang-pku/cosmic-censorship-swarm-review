# W07-L0 — Ledger contribution report (node L0, gate G-LIT)

**Worker:** `deepseek-flash-07` · **Assignment:** `asg-2026-09-11-L0-deepseek-flash-07-16` (Astra, 23:19:12)
**Canonical artifact:** `ledger/theorems.jsonl` · **Status:** delivered, **UNVERIFIED**, no node/gate state claimed
**Checkpoint:** 2026-09-11 23:33 +08:00 · ~0.6 of 4 budgeted agent-hours

---

## 1. Assignment and acceptance

| card field | value | self-check |
|---|---|---|
| task | Build `ledger/theorems.jsonl`, one JSON object per line | done (37 rows; 15 authored here) |
| acceptance | Skeleton schema + ≥10 filled rows with locators and explicit non-claims | done (15 rows; schema = lead's builder contract) |
| gate | G-LIT | **not claimed** — verdict is lead/Astra authority |
| falsifier | A row without a locator | 2 rows are explicitly `unresolved` **because** no verified locator exists; they carry no accepted claim |
| stop rule | Submit with sha256; unresolved stays unresolved | followed: 2 unresolved rows, 1 scope-only provisional row |

The card was read at 23:26. The outbox/inbox was empty when first checked (23:16–23:20), so one
secondary artifact was produced before the card was found (see §6); the assignment then took priority.

## 2. What was contributed

Two **new** batch files (no existing agent's file was edited):

| artifact | sha256 (prefix) |
|---|---|
| `artifacts/literature/sources/batch-w07.jsonl` (7 source records) | `9f7c73af154e` |
| `artifacts/literature/theorems/batch-w07.jsonl` (15 theorem rows) | `29326d1e6c09` |
| `ledger/theorems.jsonl` (canonical, rebuilt via the lead's builder) | `3b104a7da767` |
| `artifacts/worker-07/ledger_contribution/build_w07_batches.py` (generator) | `ed101e73a352` |
| `artifacts/worker-07/ledger_contribution/check_grounding.py` (checker) | `e4106a562346` |
| `artifacts/worker-07/ledger_contribution/grounding_report.json` | `903c2db02896` |

Rows by class (15 total; 9 accepted, 4 provisional, 2 unresolved):

| class | rows |
|---|---|
| `AF-WCC-VAC-GEN` | W07-TH-02 (WCC open) |
| `AF-WCC-VAC-BH-FORM` | W07-TH-03 (short-pulse BH formation, provisional) |
| `AF-WCC-VAC-NS-CONSTR` | W07-TH-04 (exterior naked singularity), W07-TH-05 (interior+gluing, provisional) |
| `AF-SCC-C0-VAC-GEN` | W07-TH-06 (Dafermos–Luk continuous extension), W07-TH-07 (Sbierski Schwarzschild) |
| `AF-SCC-C2-VAC-GEN` | W07-TH-08 (open; revised SCC expected) |
| `AF-WCC-SCALAR-SPH` | W07-TH-11 (Christodoulou 1999 scope row), W07-TH-12 (Choptuik, unresolved) |
| `AF-SCC-OTHER-MODELS` | W07-TH-09 (mass inflation), W07-TH-10 (Luk–Oh linear), W07-TH-14 (Kerr stability, provisional) |
| `DEFINITIONS` | W07-TH-01 (WCC formulation), W07-TH-13 (C⁰/C² separation), W07-TH-15 (Penrose provenance, unresolved) |

The five new verified sources (`W07-SRC-01…05`) were each verified by fetching the arXiv abstract
page in this session; the page URL, HTTP 200, timestamp and a verbatim quote are stored in each
source record. Two sources are explicitly **unresolved**, never guessed:
`W07-SRC-06` Penrose 1969 (JSTOR cross-origin block; S2 rate-limited) and `W07-SRC-07` Choptuik 1993
(publisher elided the abstract; no arXiv version). Every row citing them is `unresolved`.

## 3. Class-hygiene guarantees in the rows

* **No C⁰/C² transfer.** `W07-TH-06` (C⁰ extendibility, conditional on Kerr stability) and
  `W07-TH-08` (C² open) are separate rows in separate classes; `W07-TH-13` states the distinction
  as a `formal_model` row so a schema cannot derive one from the other.
* **No model→vacuum transfer.** `W07-TH-09` (Einstein–Maxwell–scalar) and `W07-TH-10` (fixed RN
  background) live in `AF-SCC-OTHER-MODELS` and carry `does_not_imply` clauses forbidding transfer
  to the vacuum classes.
* **No non-generic→generic transfer.** `W07-TH-04/05` (self-similar naked singularities) explicitly
  do **not** refute WCC; `W07-TH-03` (short pulse) does **not** prove WCC for generic data.
* **No conclusion inflation.** `W07-TH-11` asserts scope only — the fetched abstract of
  Christodoulou 1999 does not state the theorem's conclusion, so none is asserted.

## 4. Quote grounding (new check, and a finding for L1)

`check_grounding.py` verifies that every quote declared in a row's `grounding` list is a
whitespace-normalised **verbatim substring** of the cited source's recorded evidence — stricter
than the lead builder's "evidence length ≥ 30 chars" rule, which never compares the row to its source.

Result at 23:33 on the 37-row ledger:

* all 30 declared quotes across my 13 grounded rows match their sources (0 failures);
* **16 of the 25 `accepted` rows in the ledger declare no grounding at all** — all 16 are the
  literature lead's rows (`D-001…D-006`, `T-101…T-208`), none are mine. This is a *checkability*
  gap, not proof of a citation error: their support may be quoted inside `statement_exact`, which
  this checker does not parse. Recommendation: require a `grounding` list (or equivalent structured
  quote field) for any `accepted` row whose sources were fetched, and report coverage at L1.

## 5. What this report does NOT claim

* No node is marked `done`, no `validation_status=passed`, no gate verdict (controller notice §5).
* No row states a new mathematical result; all 15 are provenance/status rows over published sources.
* 4 rows are `provisional` and 2 are `unresolved`; the ledger's `unresolved.jsonl` and
  `falsifiers.md` carry them forward. `unresolved` stays unresolved.

## 6. Secondary artifact (pre-assignment branch)

Before the card was found, worker-07 delivered a falsification harness for the shared
class-separation check in `research_map/audit_evidence.py` (proposal W07-01):
`artifacts/worker-07/class_separation_falsification/` (`results.json` `e48dc91a6f3f`, `REPORT.md`
`25800874941d`). It found 14/17 genuine class-merge fixtures escaping the gate and 1/10 legitimate
controls falsely flagged, against pinned revision `c4769b99ab70` (snapshot preserved; the live file
has since moved to `03f70e309181`). Emitted separately to `comms/outbox/deepseek-flash-07/`.

## 7. Next falsifiers

1. **L1 spot-check** (worker-19) re-fetches one of `W07-SRC-01…05`; if a locator resolves to a
   different work than the row claims, that row is downgraded — report verbatim.
2. **Read Christodoulou 1999 full text** (Ann. of Math. 149(1) 183–217; arXiv:math/9901147 PDF is
   not fetchable here): quote Theorem 1 and either promote `W07-TH-11` or record that the
   scope-only row was wrong.
3. **Choptuik / Penrose locators**: a quotable page for either upgrades `W07-TH-12`/`W07-TH-15`;
   failure to find one leaves them unresolved (a valid outcome).
4. **Grounding coverage**: if L1 accepts rows with no grounding, the §4 finding is falsified as a
   gap; if it rejects them, 16 lead rows fail the stricter check.

## 8. Evidence refs

`ledger/theorems.jsonl#3b104a7d` · `artifacts/literature/sources/batch-w07.jsonl#9f7c73af` ·
`artifacts/literature/theorems/batch-w07.jsonl#29326d1e` ·
`artifacts/worker-07/ledger_contribution/grounding_report.json#903c2db0` ·
`artifacts/literature/tools/build_literature.py` (schema authority) ·
`comms/inbox/deepseek-flash-07.jsonl` (assignment card) · `comms/PROTOCOL.md` (message contract) ·
`research_map/research_map.json` (gates G-LIT, canonical paths).
