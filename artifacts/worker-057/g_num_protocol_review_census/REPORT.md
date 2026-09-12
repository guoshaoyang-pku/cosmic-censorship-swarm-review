# W057-GNUM-PROTOCOL-REVIEW-CENSUS-01 — independent census of the pinned protocol-review counter

- **Worker:** worker-057 (self-selected; no card in `comms/inbox/worker-057.jsonl`)
- **Class binding:** `AF-WCC-SCALAR-SPH` — node `N0`, gate `G-NUM` (flat-space calibration only; `numerics_lock` stays LOCKED, no N1 work)
- **Verdict:** `CENSUS_CONFIRMED` (advisory worker evidence; **no gate verdict, no node status**)
- **Scope:** read-only measurement of `numerics/gates.py::_protocol_review` at the pinned bytes. No canonical file was modified.
- **Falsifier:** re-run `census_protocol_review.py` at the same pins — the census block is falsified if any channel disagrees, if any expectation or control fails, if the binding accept/dissent sets differ from the listed `event_id`s, or if a fresh run of the pinned `gates.py` at these bytes reports a different `protocol_review` block. A moved `numerics/gates.py` or `numerics/CONVERGENCE_PROTOCOL.md` hash voids the census for the new bytes; the review stream is live, so an appended review event re-binds the census for the new stream bytes.

## Pins (measured)

| path | sha256 |
|---|---|
| `numerics/gates.py` | `fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e` |
| `numerics/CONVERGENCE_PROTOCOL.md` (protocol of record) | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `research_map/events.jsonl` (at census instant) | `8c40b8b9e0781a00f2516acf975c8f2eb81ba93d96221ca914db3afef3fc5d65` |
| census digest (content-stable) | `46dd3c17ad39f2ace73df3c4966b223fe627ec0ade50c395388cb44b1636f4c6` |

## Method — three channels, same question

- **A.** independent stdlib re-implementation of the documented rule (no author code imported) over a frozen snapshot of the stream (`research_map/events.jsonl` + sorted `comms/outbox/**` + sorted `comms/inbox/**`, exactly the source set/order of `load_event_stream`);
- **B.** the pinned module itself (`numerics.gates._protocol_review`) executed in a subprocess on the same snapshot, its own live re-read, and a 14-fixture matrix;
- **C.** the pinned CLI (`python3 numerics/gates.py --pretty`) end to end, with every stream source byte-hashed immediately before and after the call.

**Channel agreement: A = B (snapshot) = B (live re-read) = CLI; stream bytes stable around the CLI call.** All 14 fixtures and all 8 fail-closed controls pass.

## Result — live census at protocol `1e6cdf04d7a2`

`reviewed = true`, `contest = true`.

**Binding accepts (4):** `audit-review-gnum-protocol-final-20260912T0027` (astra-lead-audit 4.5), `w012-c3-review-0001-adjudication` (deepseek-flash-12 4.0), `w081-20260912T002140-c8-review` (worker-081 4.0), `w081-20260912T0042050800-adj2-review` (worker-081 4.0).

**Standing binding dissents (4):**

| event_id | reviewer | verdict | created_at |
|---|---|---|---|
| `w067-review-gnum-protocol-r3-20260912T002256` | worker-067 | revise 4.0 | 00:22:56 |
| `w081-2026-09-12T00:29:19+0800-f1-review` | worker-081 | revise 3.5 | 00:29:19 |
| `w067-provledger-20260912T005149-20-review` | worker-067 | revise 3.5 | 00:51:49 |
| `w042-n0-stoprule-01-review` | worker-042 | revise 3.5 | 00:52:59 |

**Advisory (stale/uncited, do not contest):** `audit-review-20260912T0009-gnum-protocol` (revise at `01b2072434cd`, superseded hash) and `audit-r2-review-n0` (revise, no cited protocol hash).

## Findings

1. **B-N0-R2-2 / F-042-N0-2 are confirmed at event level.** worker-081 holds both a binding revise (F1′, 00:29:19) and a later binding accept (adj2, 00:42:05) for the same protocol revision, under two spellings of the same target (`G-NUM-protocol` vs `numerics/CONVERGENCE_PROTOCOL.md#<hash>`). The pinned counter has no `(reviewer,target,hash)` supersession: both stand, and `contest = bool(dissents)` stays true. The older w081 accept (00:21:40) also remains counted. Fixtures F2/F3 (accept→revise and revise→accept by one reviewer) both report `reviewed=true, contest=true`; fixture F13 shows an explicit `withdrawal`-type event is not counted at all.
2. **Supersession alone would not clear the contest at this hash.** Counterfactuals over the same binding set: latest-per-reviewer (V1) and latest-per-(reviewer, normalized target) (V2n) drop the w081 F1′ revise **and** worker-067’s 00:22 revise, but keep worker-067’s 00:51 revise and worker-042’s 00:52 revise → `contest` remains true. Exact-target supersession (V2e) drops only w081 F1′ → contest remains true with 3 dissents. Any disposition of the protocol contest must therefore address the standing worker-067 and worker-042 dissents, not just supersession semantics.
3. **Binding semantics measured.** A review binds only with a cited hash in `reviewed_sha256` / `artifact_sha256` / `reviewed_protocol_hash` or an `evidence_refs` pin of the form `numerics/CONVERGENCE_PROTOCOL.md#<hash>` (≥12 chars; a 12-char prefix binds). A `target_id` pin such as `N0#<hash>` does **not** by itself supply a cited hash (fixture F8b). `astra-lead-numerics` self-reviews are excluded. Duplicate `event_id`s are de-duplicated once, in source order (accepted stream first, then sorted outbox, then sorted inbox). The `#sha256:` / `#` parse has no `break`, so a long `#sha256:` pin can also append a second, non-matching `sha256:…` reading — harmless here, but it is a real property of the pinned parser.
4. **The census is instant-bound and the stream is moving fast.** Three protocol-targeting reviews landed during this session (00:50:36 accept, 00:51:49 revise, 00:52:59 revise); `events.jsonl` moved `b0ce9a8e → 8c40b8b9`. The binding set above is exactly the set in the pinned snapshot; a later accept by the same author does not withdraw it under the pinned rule.
5. **Relation to existing work.** This is an independent measurement, not a duplicate: worker-042 stated the supersession defect qualitatively in `w042-n0-stoprule-01-review`; this census supplies the event-level, three-channel, hash-pinned quantification and the counterfactual table. worker-067/worker-081 review texts are inputs, not re-adjudicated here.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-057/g_num_protocol_review_census/census_protocol_review.py
# exit 0 iff 14/14 expectations and 8/8 controls hold; writes report.json + census.json
```

## Non-claims / authority

Worker evidence only. This report does **not** set a gate verdict or node status, does not adjudicate whether the worker-067/worker-081/worker-042 findings are correct, does not propose or apply any change to `numerics/gates.py`, and does not release `numerics_lock` or authorize N1.
