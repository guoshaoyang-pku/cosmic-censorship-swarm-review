# W087-GFORM-INDEP-04 — G-FORM accept independence and rev-13/rev-29 freeze-state audit

Worker `worker-087` (instance `worker-087-20260912T004520-968807`), bounded execution worker,
one class-bound task then exit. No assignment card existed in `comms/inbox/worker-087.jsonl`,
so the task was self-assigned from the live controller gate audit (G-FORM coverage) before
measurement, with pre-registered criteria and fail-closed controls. Read-only against every
canonical input; all writes are under this directory.

- **Nodes / gate:** F1, F2a, F2b / `G-FORM`
- **Classes:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b)
- **Instrument:** `audit_gform_independence.py` (standalone, stdlib only)
- **Report:** `report.json` (valid JSON; 34 top-level keys; verdict digest
  `ad86594f7aaf0a5a68a040d2299e550714438751f2a5aaec341164309eced7d6`)
- **Verdict status:** `REPINNED_ANNOUNCEMENT_PENDING` (exit 3)

## Question

(A) Does the G-FORM criterion *"two independent accepts per schema"* hold at the FROZEN
rev-28 pins after reviewer-identity, verdict-text and evidence-channel dedup — i.e. is the
accept coverage real, or carried by fewer than two genuinely independent reviews?
(B) Do the canonical schema bytes still match the FROZEN manifest pins at run start and end,
and is any post-freeze write announced by its owner in the accepted stream?

## Method (deterministic, fail-closed)

1. **Pins.** Measure the three canonical schemas and `artifacts/formulation/FROZEN.json` at
   run start and run end; exit 2 if anything moves during the run (`MOVING_TARGET`).
2. **Corpus.** Harvest every record with a verdict from `research_map/events.jsonl`, every
   `comms/outbox/**/*.jsonl|*.json`, and every `reviews/*.json`; dedup by `event_id`
   (richest copy wins). Snapshot sizes are recorded with per-source sha256 in `report.json`.
3. **Target binding.** A record counts for a schema only if a *target* field names it
   (`target_id`/`node_id`/node/class token/schema path; artifact path group only if no
   explicit target; context `class_ids` only if neither exists) — so an F0 review that lists
   all four class ids is not counted as an F1/F2a/F2b review.
4. **Hash binding.** A record binds a pin only if its *primary* declared hash
   (`reviewed_sha256`/`artifact_sha256`/`target_sha256`/`target_id#…`) prefix-matches that
   pin; prose mentions of another revision do not bind. This is what keeps a rev-13 review
   from being harvested as a rev-28 verdict.
5. **One verdict per reviewer** (latest `created_at` wins), then full-schema accepts are
   separated from advisory/secondary accepts (reviews of another review or of a derived
   checkpoint, or `counts_as_full_schema_verdict: false`).
6. **Clustering.** Full-schema accepts merge when findings-text character-5-gram Jaccard
   >= 0.6 or when a non-empty evidence-channel signature (instruments/scripts/review
   documents, target pins excluded) intersects. Cluster count = effective independent accepts.
7. **Freeze state.** Manifest entry vs disk for both trees, mirror equality, declared
   revision/`revised_at`, each schema's `f0_binding.consistency_evidence_sha256` against the
   measured evidence file, and accepted-stream artifact events that announce each measured
   canonical hash.
8. **Controls (8/8 pass):** identical text collapses; distinct reviews stay separate;
   superseded-hash record not counted; revise not counted as accept; cross-target hash
   excluded; secondary-document accept not full-schema; announcement requires an artifact
   event; determinism (two analyses, equal digest). Exit 4 on any control failure.

## Result

### Freeze state — `REPINNED_AWAITING_ANNOUNCEMENT`

The three canonical schemas moved after the rev-28 freeze and were re-pinned in
**FROZEN revision 29** (`artifacts/formulation/FROZEN.json`, frozen_at
`2026-09-12T00:55:02+08:00`, sha `3d9e3d77fd87…`):

| node | rev-28 pin | measured rev-13 bytes | mtime / revised_at | manifest entry |
|---|---|---|---|---|
| F1 | `cce9c60146d6` | `d9cebb9404b2` | 00:53:40 / 00:53:20 | matches disk |
| F2a | `5476a3f2c6bc` | `e9a27996dfd3` | 00:53:20 / 00:53:20 | matches disk |
| F2b | `55d0a1ea9bda` | `b2ab6acb2bbe` | 00:53:20 / 00:53:20 | matches disk |

- Manifest internal consistency: **0** canonical and **0** authoring entry mismatches.
- Authoring mirrors: **aligned** for all three (byte-identical to canonical).
- `f0_binding.consistency_evidence_sha256` refreshed to the measured evidence sha
  `9e335e9ba1bf…` in all three (closes the binding gap worker-047 measured at rev 12).
- **Owner artifact event announcing each new canonical hash in the accepted stream: 0/3.**
  The re-pin is recorded only inside the manifest (`rev29_delta`). Under
  `comms/PROTOCOL.md` rule 2 and the CF-19 precedent (an unannounced write on a canonical
  path), the accepted-stream artifact event is the hash-bound publication act; until it
  exists the rev-13 bytes are not announced for gate binding.

### Accept independence

| node | at rev-28 pins (now void) | full-schema accepts | advisory accepts | clusters | at rev-13 pins (current) | clusters |
|---|---|---|---|---|---|---|
| F1 | `cce9c60146d6` | worker-061 | — | **1** | 0 accept | **0** |
| F2a | `5476a3f2c6bc` | worker-089 | worker-031 | **1** | worker-017, worker-072 | **2** |
| F2b | `55d0a1ea9bda` | worker-089, worker-098 | worker-003, worker-007 | **2** | worker-061 | **1** |

- At the rev-28 pins the two-independent-accepts criterion was **not met** (F1 1, F2a 1,
  F2b 2). Note the controller's 00:43 audit credited F1 to worker-088; worker-088's own
  amended review at 00:39:02 is a **revise** (3.5), so under one-verdict-per-reviewer the
  only rev-28 F1 accept is worker-061.
- All of those rev-28 verdicts are now **void**: they bind bytes that were superseded at
  00:53. At the rev-13 bytes the criterion is also not yet met (F1 0, F2b 1; F2a 2).
- 4,947 corpus records and 159 review documents were harvested; every source sha256 is in
  `report.json.corpus.sources`.

## Findings (IDs in `report.json.findings`)

- `W087-FREEZE-01` (major) — rev-28 → rev-13 schema transition and rev-29 re-pin; manifest
  consistent, mirrors aligned, evidence pins refreshed, **accepted-stream announcement
  absent**; all rev-28-bound verdicts void.
- `W087-FREEZE-02-{F1,F2a,F2b}` (major until announced) — per-target transition detail.
- `W087-STATE-01` (info) — freeze state and both coverage censuses in one line.
- `W087-INDEP-{F1,F2a,F2b}-{GAP,OK}` — per-target rev-28 coverage, with cluster members,
  scores, `target_match` strings and review documents listed in the report.

## Falsifier

Re-run `audit_gform_independence.py`. The transition/announcement finding is void if every
measured canonical hash matches its entry in the current FROZEN revision **and** an owner
artifact event in the accepted stream announces each hash. The coverage finding is
falsified if any schema reported >= 2 effective accept clusters falls below 2 under the
declared clustering rule; two counted clusters share an identical instrument, review
document or verdict text; an excluded hash-bound verdict is shown to name the schema
directly at the reported revision; a control does not reproduce; or a re-run on the same
corpus yields a different verdict digest. A later file write alone is not a falsifier.

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-087/gform_independence/audit_gform_independence.py; echo $?
```

## Scope and authority

Worker measurement evidence only. No gate verdict, node status, `validation_status=passed`
or review verdict on the schemas is claimed; this audit consumes recorded verdicts and
re-issues none. Not duplicative of `worker-074/f2a_verdict_independence` (F2a at the
superseded `b6123750b37d` bytes only), `worker-095/freeze_hold_binding_integrity_r3`
(event-shadow/binding probe whose own R1 reported the manifest clean and whose R6
probe-drift criterion failed), or `research_map#controller_gate_audit` (distinct reviewer
ids only, no text/channel dedup, no manifest-versus-disk re-measure).
