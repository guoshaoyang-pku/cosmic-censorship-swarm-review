# W077-CLASSSEP-PINRECON-01 — class-separation baseline pin provenance

**Worker:** worker-077 · **Node:** A1 · **Gate:** G-AUDIT · **Classes:** AF-WCC-VAC-GEN;
AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN
**Status:** worker-level measurement complete (`unverified`); **no gate verdict, no canonical write.**

## Why this task

The class-separation detector (`research_map/class_separation.py`) is the gate instrument for
G-AUDIT/G-FORM, and its pin was already the subject of two controller findings (CF-16, CF-26) and
one forensics ruling (CF-29). The open adjudication round
(`astra-life07-classsep-adjudication-review`, deadline 02:30) is instructed to review "at the
frozen hashes", and the operative controller text says the active frozen pin "stays
`c266dbecaa87`". This task asked one bounded, class-bound question that no other worker had
measured end-to-end: **which digest is the byte-attested baseline, and which records cite a
digest that no bytes satisfy?**

This is a provenance/bookkeeping measurement. It does not re-litigate detector quality and does
not touch the contested FN/FP arms.

## Method

Deterministic, read-only checker: `reconcile_classsep_pin.py` (stdlib only). It writes nothing
outside its own directory. Its design rule was forced by its own subject matter: **no hex prefix
of the disputed digest is trusted as a literal.** The only constants are the shared 6-char stem
`c266db` and two pre-registered digests used as hypotheses; every prefix, match and
classification is derived from measured bytes or from the pinned records themselves.

1. Census every file in the tree whose name contains `class_separation` (306 at run pins),
   grouped by measured sha256; the pre-move family is every copy carrying the stem `c266db`.
2. Resolve the attested digest from bytes by intersecting the family digests with the token
   cited by the primary freeze event `astra-w07adj-00` (created_at == `frozen_artifacts.frozen_at`).
3. Check the authoritative records: current `frozen_artifacts` entry, `entry_hashes.json`,
   CF-29 forensics, handoff prose, accepted `events.jsonl`, and the live comms/review corpus.
4. Classify every cited token as resolvable to an on-disk digest or orphan, distinguishing the
   transcription prefix, orphan full digests, and unresolved fragments.
5. Sweep the repository (30,921 files / 688 MB, ≤2 MB per file, no cap hit) for any file measuring
   the pre-registered unattested digest.
6. Controls K1–K7 (content-sensitive matcher, prefix separation, freeze locator, sweep
   sensitivity, pre-registration, non-empty census) and an in-run T0/T1 pin-drift check.

## Headline result

| quantity | value |
|---|---|
| byte-attested baseline | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| on-disk pre-move copies | 85 files, **1** distinct digest (the attested one) |
| primary freeze event citation | `c266dbceca87` (prefix) at `astra-w07adj-00`, 23:30:20 == `frozen_at` |
| current `frozen_artifacts` + `entry_hashes.json` | both equal the attested digest |
| files measuring the cited-but-orphan digest | **0** (sweep of 30,921 files / 688 MB) |
| citation sites not resolvable to any bytes | **110** sites across **36** records (live corpus) |

## Findings

- **F1 — the baseline is unambiguous.** `c266dbceca87fb99…` is attested by 85 independent
  on-disk copies, the 23:30:20 freeze event, the current `frozen_artifacts` entry and
  `entry_hashes.json`. No competing byte identity exists anywhere in the swept domain.
- **F2 — transcription A, spread through the accepted stream.** `c266dbecaa87` (and its 8-char
  truncation `c266dbec`) differs from the attested digest at hex characters 7–9
  (`c266dbceca87` vs `c266dbecaa87`). It appears at 103 live sites, including
  `controller_findings` CF-16/CF-26/CF-29 action text, `ASTRA_HANDOFF.md:51`,
  `runtime/state/controller_verification/cf29-detector-write-forensics.json:/ruling`, the r3
  `reviews/CLASSSEP-calibration-adjudication.json`, the audit-lead lifecycle-08 events, and
  worker messages that quote them. It matches no file.
- **F3 — transcription B, an orphan full digest.** worker-036's review declares
  `target_sha256 = c266dbceca87b8b0…`, which shares its first **13** hex characters with the
  attested digest and then diverges; it matches no file. worker-080 already flagged the hash
  hygiene of that review (00:51), so this is corroboration of a recurrent transcription failure
  mode, not a new discovery.
- **F4 — prefix collision hazard.** 292 live citation sites use prefixes ≤13 hex characters
  (`c266dbceca87`, `c266dbce`), which are prefixes of *both* the attested digest and orphan B.
  A reviewer who writes a 12-char prefix for the baseline cannot discriminate the two with it
  alone; only ≥14 hex characters separate them.
- **F5 — one unresolved fragment.** a single 11-char `c266dbeca87` citation matches no digest
  (neither attested, nor orphan B, nor transcription A).

## Impact / needed to unblock

The operative instruction "the active frozen pin stays `c266dbecaa87`" (CF-16 action, restated in
CF-26/CF-29 and the handoff) **cannot be executed as written**: it names bytes that do not exist,
and `research_map/audit_evidence.py:154` would print that prefix as the baseline in any
frozen-drift message. The controller owns its own finding text (CF-4) and must correct the four
cited prose sites to the attested digest; the 02:30 independent classsep review must cite
`c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920`, and any prefix it quotes
should be ≥14 hex characters to avoid the F4 collision.

## Falsifier

Any file in the swept domain measuring
`c266dbecaa87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920`; any primary event before the
00:52 move citing a token that is not a prefix of the attested digest; the freeze event's token
failing to resolve to a single on-disk digest; a pre-move copy set that is not byte-identical; or
drift of any pinned stable input during the run (voids the run).

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-077/classsep_pin_provenance/reconcile_classsep_pin.py \
        --out artifacts/worker-077/classsep_pin_provenance/report.json
python3 artifacts/worker-077/classsep_pin_provenance/reconcile_classsep_pin.py \
        --out artifacts/worker-077/classsep_pin_provenance/report.run2.json
python3 artifacts/worker-077/classsep_pin_provenance/reconcile_classsep_pin.py \
        --compare artifacts/worker-077/classsep_pin_provenance/report.json \
                  artifacts/worker-077/classsep_pin_provenance/report.run2.json
```

Exit 0 = instrument ok and pins stable; 2 = control/pre-registration failure; 3 = in-run pin
drift. Two runs at the pinned inputs produce the identical content digest
`969393d34da8afbff25f8efd89e01e7cef17e2bedf4fda22e9dd57bf74c4f45a`.

## Files and pins

| file | role |
|---|---|
| `reconcile_classsep_pin.py` | deterministic read-only reconciler (this is the instrument) |
| `report.json` | machine report: census, citations, checks, controls, verdict, falsifier |
| `report.run2.json` | second run for determinism |
| `determinism.json` | two-run content-digest comparison |
| `entry_hashes.json` | sha256 of every artifact in this directory |
| `README.md` | this document |

Pinned at the run: `research_map/research_map.json#66ada65f6027`,
`research_map/events.jsonl#3c913d0bcdb0`,
`runtime/state/controller_verification/cf29-detector-write-forensics.json#b573dcfdcc20`,
`research_map/ASTRA_HANDOFF.md#bd2c2eeaf11d`. `entry_hashes.json` records its own outputs'
hashes and lists those five run pins (it is not cited by hash here, to avoid a circular
reference). The tree is live: copies are rewritten and records
appended while the tool runs, which is why the determinism digest covers the pinned-record
measurement core and the substantive sweep result rather than live file counts.

## Non-claims

- Not a gate verdict; cannot pass or fail G-AUDIT and does not adopt any detector revision.
- Does not adjudicate detector quality, the contested FN/FP arms, or the e36b0d644ca window.
- Does not edit controller findings or any other agent's text (CF-4); the correction is *reported*.
- The "no bytes satisfy it" claim is scoped to the enumerated sweep domain (30,921 files,
  688 MB, ≤2 MB/file, no cap hit).
- No canonical path was written by this worker.
