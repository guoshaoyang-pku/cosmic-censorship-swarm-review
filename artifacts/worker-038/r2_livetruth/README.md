# W038-GFORM-R2LIVETRUTH-01 — independent live-truth check of the R2 consistency-evidence repair

**Worker:** worker-038 · **Gate:** G-FORM · **Nodes:** F1, F2a, F2b
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Authority:** measurement only. No canonical write, no gate verdict, no promotion.
**Instrument:** `check_r2_livetruth.py` · **Result:** `report.json` (8/8 pre-registered checks pass)

## What was already established (not re-done here)

The rev12 schemas declare `f0_binding.consistency_evidence_sha256 = 675a99d0d25b`, while the
canonical evidence path measures `9e335e9b` — a two-writer collision (worker-086). Worker-043's R2
repair restores the declared 728 B document and redirects the owner checker's write to
`taxonomy_consistency_report.json`. Worker-043 measured reconstruction (E1) and durability against
the clobber (E2/E4/E5). Workers 041/094/034/038 diagnosed the staleness itself.

## What this task adds (three untested questions)

| id | question | result |
|---|---|---|
| C1 | do the two independently preserved candidates equal the declared pin? | PASS — both 728 B, both `675a99d0`, byte-identical |
| C2 | is the restored document's verdict still true of the **current** inputs? | PASS — canonical checker re-derives `CONSISTENT (4 classes, 0 divergences)`, output equals the restored core keys |
| C3 | do the embedded input hashes equal the **live** inputs? | PASS — A `0abb9ed8`, B `d7419b4e` both match |
| C4 | is the patched checker deterministic and non-clobbering? | PASS — two runs → identical report hash; pinned bytes `675a99d0` unchanged |
| C5 | sensitivity control: is a **compared** field edit caught? | PASS — `censorship: SCC→WCC` → exit 1, error emitted |
| C6 | **drift visibility**: is an **uncompared but load-bearing** field edit caught? | NO SIGNAL — `positive_test_case.description` edit → both checkers exit 0; embedded `lead_contract_sha256` is stale but only measurable by hand |
| C7 | timestamp order inside the frozen pair R2 would create | `checked_at` 00:31:41 < `measured_at` 00:32:02 — the pinned evidence postdates its own declared check time |
| C8 | controls | 9/9 guard files unmoved; sandbox mutations confined; live evidence still `9e335e9b`, FROZEN still rev28 |

## Residual finding (not a defect of the patched bytes)

R2 stops the clobber and the restored claim is true **today**, but it does not make the pin
self-enforcing. The evidence document now embeds `lead_contract_sha256`, yet no pinned artifact and
no refresh rule requires a consumer to re-measure it; the schema refresh rule still names only the
declared F0 artifact. C6 shows the concrete failure: an edit to a semantically load-bearing field
the consistency checker does not compare leaves both checkers at exit 0 while the pinned document's
embedded hash silently goes stale. The detection data exists (the embedded hash); the obligation
and the consumer-side check do not.

## Falsifier

Any of: two runs of the patched checker on identical inputs differ; the restored document's core
keys differ from a fresh canonical re-derivation; A or B hashes differ from the embedded values; a
compared-field edit is not caught (instrument dead); the C6 drift edit **is** signalled by either
checker; or any canonical guard file moves during the run.
