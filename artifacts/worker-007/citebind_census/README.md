# W007-CITEBIND-CENSUS-01 — independent adjudication of `citation_status: verified_by_L1` at F1/F2a/F2b rev12

**Worker:** worker-007 (slot 007) · **Node:** L1 · **Gates:** G-LIT (primary), G-FORM (secondary)
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Mode:** one bounded class-bound task taken from the immediate queue; no card was issued for
worker-007 in this lifecycle. Worker artifact + worker verdict only — no gate verdict, no node
status, no `validation_status=passed`.

## Why this task

Worker-077 filed `W077-HF-03` (reviews/F2b-f0-binding-077.json) as a major hard finding: five
F2b `l1_ledger_refs` rows claim `citation_status: verified_by_L1` while the pinned ledger records
`verification_status=abstract-read` and `review_status=not_independently_reviewed`, and the token
is absent from the ledger. It was reported for **F2b only**, self-verified, and its own falsifier
names a decisive branch that had not been executed:

> "…or a project definition equating `verified_by_L1` with `citation_audit.csv` verdict=`verified`
> on abstract/API evidence only."

This packet executes that falsifier, extends the census to **all three** rev12 class schemas
(F1 and F2a included), and binds every claim to FROZEN-pinned bytes.

## Pins (all measured, all live==snapshot, FROZEN rev28 pins all match)

| input | sha256 (12) | status |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev12) | `cce9c60146d6` | FROZEN pin match |
| `schemas/af_scc_c2_vacuum.yaml` (rev12) | `5476a3f2c6bc` | FROZEN pin match |
| `schemas/af_scc_c0_vacuum.yaml` (rev12) | `55d0a1ea9bda` | FROZEN pin match |
| `ledger/theorems.jsonl` | `a1674f094979` | live == snapshot (62 rows) |
| `ledger/citation_audit.csv` | `315c19145065` | live == snapshot (97 rows) |
| `artifacts/formulation/rule_spec.json` (FORM-RULE-SPEC v1.2) | `40f9bb9e657b` | FROZEN pin match |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` | FROZEN pin match |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d9` | read-only context |
| `research_map/formulation_taxonomy.yaml` (rev5) | `0abb9ed8a961` | read-only context |

Read-only copies live in `snapshot/`; the checker re-hashes every input before and after the run
(C6 PASS). No canonical artifact was modified.

## Result

**Verdict: `CONFIRMED_VOCABULARY_VIOLATION` / `REFUTED_VERIFICATION_OVERCLAIM`.**

1. **Confirmed (token level).** `rule_spec.json` is FROZEN-pinned with
   `vocabularies.citation_status = [unverified, unresolved, verified]`. Across the three rev12
   schemas, **11** `l1_ledger_refs` entries (F1: T-204, T-208; F2a: T-401, T-402, T-514, T-520;
   F2b: D-002, T-301, T-515, T-528, T-302) carry `citation_status: verified_by_L1` — a token that
   is **not in the vocabulary and not registered as an alias** (C1 FAIL). The literal token occurs
   **0 times** in the ledger, the citation audit, the rule spec, `VOCAB_ALIASES.json`, the
   taxonomy and `FROZEN.json` (C2). All 62 ledger rows carry
   `review_status=not_independently_reviewed` (C4); 61 are `verification_status=abstract-read`,
   1 is `unverified`. R15 (`applies_to: all`) requires `citation_status in vocabulary`; the
   same schema's `provenance.citation_status: unverified` **is** in-vocabulary and honest.
2. **Refuted (overclaim level).** Every one of the 11 refs resolves through
   `citation_audit.csv:used_by_theorems` to audit rows for **all** of its ledger `source_ids`
   (0 missing, 0 bad): `verdict=verified`, `resolver_result=resolved` in every case — 11/11 refs,
   and the audit as a whole is 97/97 `verdict=verified` (C3 PASS). The evidence level recorded
   there is abstract/metadata, which is exactly the branch worker-077's falsifier names and which
   the pass-04 ruling (CF-18b) treats as sufficient for G-LIT when `verification_status` is honest.
3. **Residual (non-blocking, lead-owned).**
   - `provenance.citation_status: unverified` next to per-ref `verified_by_L1` reads as a
     self-contradiction unless the fields' scopes are documented.
   - F2a `T-401` pairs `l1_status: provisional` with `citation_status: verified_by_L1`.
   - F1 `D-001` has no `citation_status` field at all.
   - 9 further `citation_status: n/a` tokens in `transfer_relations` witnesses (3 per schema) are
     also outside the frozen vocabulary.
4. **Repair (advisory, not a content downgrade).** The lead decides one of: register
   `verified_by_L1` as an alias of `verified` in `VOCAB_ALIASES.json` with an explicit
   abstract/API-level scope note; or rename the per-ref leaf (e.g. `l1_citation_audit_status`) so
   it cannot be read as independent review; or substitute the in-vocabulary `verified` plus a
   scope note. The source-level facts do not require F1/F2a/F2b content changes.

**Effect on the gate question:** `W077-HF-03` should be re-scoped from "citation overclaim"
(blocking, content) to "out-of-vocabulary token in a leaf named `citation_status`" (blocking for a
*clean* accept, one-line repair). The distinction matters because it decides whether rev13 must
downgrade citations (it need not) or only fix vocabulary (it should).

## Controls (7/7 PASS)

| id | mutation | expectation | result |
|---|---|---|---|
| M1 | downgrade one audit verdict | resolution count drops | PASS (11→9; SRC-037 is shared by 2 refs) |
| M2 | delete one audit row | resolution count drops | PASS (11→9) |
| M3 | register token as alias | OOV count drops to 0 | PASS (11→0) |
| M4 | extend frozen vocabulary | OOV count drops to 0 | PASS (0) |
| M5 | mark a ledger row independently reviewed | falsifier-branch counter 0→1 | PASS (1) |
| M6 | negative control on `unresolved` refs | never counted as vbL1 | PASS |
| M7 | determinism | two fresh runs byte-identical | PASS |

M1/M2 also measure source coupling: a single citation-audit row (`SRC-037`) is cited by two
`verified_by_L1` refs, so per-source mutations move the count by more than one.

## Falsifier

This census is falsified by any of:

- (a) a `verified_by_L1` ref whose ledger `source_ids` include an audit row that is missing, or
  has `verdict != verified` or `resolver_result != resolved`;
- (b) a FROZEN-pinned definition of `verified_by_L1` requiring independent review
  (`review_status != not_independently_reviewed`), or a vocabulary/alias registration of the token;
- (c) any referenced ledger row recording `verification_status=verified` or a `review_status`
  other than `not_independently_reviewed`;
- (d) any of the nine pins no longer re-hashing to the values above.

A re-pin of any input **supersedes** (does not falsify) this packet. The checker can be re-run
against later revisions by replacing `snapshot/` files and re-pinning.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-007/citebind_census/verify_citebind.py   # writes report.json
python3 artifacts/worker-007/citebind_census/emit_w007_events.py  # emits outbox events
```

## Non-claims

- Not a gate verdict or node transition; worker events cannot set `done`/`passed` or move a gate.
- All findings are about artifact tokens, hash resolution and vocabulary membership — no physics
  or mathematics is asserted.
- Does not adjudicate worker-077 `W077-HF-01` (quantifier-domain divergence) or `W077-HF-02`
  (consistency-evidence hash drift).
- Does not certify that abstract-level citation verification is sufficient beyond quoting the
  existing rule; it only measures that the audit is resolved and verified at that level.
