# Checkpoint 05 — literature group (L0/L1) — near-final

- Time: 2026-09-11T23:49+08:00 (elapsed ~32 min wall clock)
- Counts: 93 sources (all locator-resolved; 3 explicitly not-assessed with reasons), 62 entries (49 accepted, 12 provisional, 1 rejected-as-superseded)
- Canonical hashes: L0 `9040d8c74335cba0…` · L1 `5833958ac1f816a1…` (deterministic build verified)
- Reviews: A, B, C2 complete and adjudicated; reviewer C (citation integrity) and reviewer D (dossier consistency) running

## Completed since checkpoint 04

| Item | Result |
|---|---|
| Astra directive `astra-w07adj-02` | 0 class tokens outside the four frozen classes; extension labels moved to `ledger_tags` (`tag_index.md`) |
| Astra directive `astra-fetch-07` | All orphan sources closed or explicitly marked `not_assessed_in_this_run` with reasons; `MANIFEST.counts.unassessed_sources` lists them |
| L0/L1 assignment acceptance | `tools/check_acceptance.py` PASS: 62 rows ≥ 15 with all required fields; 93 audit rows for 93 sources with locator/resolver/exact-locator/class-mapping/assessment/verdict/reviewer |
| Lead DOI integrity sweep | 33 Crossref checks, 33/33 match; closed Christodoulou 2009 monograph DOI (10.4171/068); located Chruściel 1992 SCC paper (10.1090/conm/132/1188443) |
| Genericity mapping | `GENERICITY_MAP.md`: only Luk-Oh (`dense_open`) and Li-Liu (meager exceptional set) reach beyond open-set/special-family/numerical language |
| F1/F2 binding | `ASTRA_COMPLIANCE.md` binds the ledger's four class IDs to the FROZEN.json rev 5 schema hashes and states the exact class conclusions |
| Evidence graph | `EVIDENCE_GRAPH.md`: per-class S / S-sub / R / N mapping for the four classes |
| C2 fixes | All five hard failures fixed (T-518 pages, T-515/T-301/T-206 stale status, T-510/T-506/T-501 contradictions, T-514 SRC-086 linkage, T-101 regularity); T-505 model-mismatch warning added |

## Self-check suite (all green)

1. `tools/build_literature.py` — fail-closed build passes; deterministic hashes.
2. `tools/check_acceptance.py` — exit 0.
3. `research_map/validate_map.py comms/outbox/lead-literature.events.jsonl` — VALID.
4. Four-class token check — 0 violations.
5. All batch JSONL files parse; MANIFEST and proposal JSON valid.

## Open at freeze

1. Reviewer C citation-integrity report and any findings.
2. Reviewer D dossier-consistency report and any findings.
3. G-F0 not passed; F1/F2 frozen but class semantics provisional.
4. Peer review of the 2026 vacuum SCC/Kerr preprints (T-526/T-527/T-528).
5. Paywalled full texts (Christodoulou 1994/1999 bodies; Chruściel 1992 content; Penrose 1969 wording).
