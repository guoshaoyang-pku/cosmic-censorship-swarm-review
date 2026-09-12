# W002-REVIEW-ESS-01 — review-independence (Kish ESS) census

Bounded, class-bound, read-only worker task taken by `worker-002` (fleet launched
2026-09-12T00:22:01+08:00). Deliverable directory:
`artifacts/worker-002/review-ess/`.

## Why this task

`comms/PROTOCOL.md` rule 2 and `reviews/INDEX.md` require **two independent reviewer
verdicts** per target, and INDEX.md promises "Kish ESS is reported for any set of reviews
that share a text or a template". The map carries ~195 review records and the base
HANDOFF's central measurement is that many nominally independent LLM judges collapse to
an effective sample size of ~2.2. No instrument in this repository measured that collapse
on the live review corpus, so this task adds one. It is the class-bound audit-side
counterpart to the per-target review verdicts the rest of the fleet is producing.

## What it does

1. Loads the review corpus: `research_map/research_map.json#reviews` plus review events
   in `comms/outbox/*.jsonl` that are not yet ingested into the map snapshot
   (`pending_ingest`).
2. Extracts, per review, the reviewer identity (`reviewer` field, parenthetical stripped,
   else `actor`), the cited hashes, and the substantive text
   (statement/summary/note/findings/hard_failures/does_not_claim/next_falsifier/...).
3. Normalizes text (lowercase; hex and numeric literals → placeholders), builds 4-gram
   word shingles, and clusters reviews by Jaccard similarity (single linkage).
4. Reports per target (F0, F1, F2a, F2b, L0, L1, A0): raw event counts, distinct
   reviewer identities, verdicts bound to the **live** canonical sha256, and the Kish
   ESS `(Σn_c)²/Σn_c²` after reviewer-dedup and text clustering. This is the effective
   number of independent verdicts, not the number of events.
5. Fails closed on drift: every target hash is measured before and after the scan; if
   any changed, `binding_valid=false` and the process exits 2.

## Outputs

| file | content |
|---|---|
| `census_review_ess.py` | deterministic stdlib-only instrument |
| `review_corpus_snapshot.json` | full corpus + map sha + pre/post target hashes + outbox file hashes |
| `ess_report.json` | per-target census, clusters, sweep, controls summary, headline |
| `controls.json` | 7 synthetic controls (known ESS) + threshold sweep + determinism digest |
| `SUMMARY.md` | one-page generated headline table |
| `manifest.json` | sha256 of every output + input pins (does not hash itself) |

## Controls

C1 identical text → ESS 1; C2 disjoint text → ESS 4; C3 number-only differences → ESS 1;
C4 hash-only differences → ESS 1; C5 actor aliasing under one reviewer identity → ESS 1;
C6 two duplicated texts → ESS 2; C7 empty-text degenerate case documented. Plus a
threshold sweep (0.3–0.7) and an in-process re-run determinism digest.

## Authority and limits

Measurement only. A worker event cannot set node status, `validation_status`, or a gate
verdict; the controller and group leads adjudicate independence and acceptance. Hash
binding is permissive (any cited 8–64-hex prefix of the live hash counts as bound).
Reviewer exposure is not observable here. See `SUMMARY.md` for the falsifier and the
reproduce command.
