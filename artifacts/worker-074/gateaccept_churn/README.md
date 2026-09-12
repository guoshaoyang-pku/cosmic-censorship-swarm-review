# W074-GATEACCEPT-CHURN-01 — same-instant control on W036-GATE-REPRO-01

**Worker:** worker-074 · **Class binding:** AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN
**Nodes:** F0, F1, F2a, F2b, A0 · **Gates:** G-F0, G-FORM, G-AUDIT
**Question:** the controller's 2026-09-12T00:24:40 gate reasons record N distinct full-schema
accept reviewers per target; worker-036 re-ran the same rule at 00:28:52, got different counts
(F0 0→1, F1 1→0, F2a 2→1, F2b 4→2), and filed the missing accepts as "phantom"
(`artifacts/worker-036/gaudit_accept_repro_report.json`, F-PHANTOM-F1/F2a/F2b). Is the recorded
count a controller-scan defect, or an artifact of review files being rewritten in place after
the scan?

**Answer: churn, not fabrication — but the churn exposes a real provenance defect.**

## Method

Read-only. The instrument re-implements the documented scan rule
(`research_map/astra_lifecycle.py:160-198`) over a manifest of the current `reviews/` corpus,
and compares it against two records written by the *same* controller lifecycle invocation that
produced the disputed reasons:

- `runtime/state/controller_verification/lifecycle_20260912-002440.json#review_coverage`
  (file + reviewer + verdict actually scanned at 00:24:40);
- `runtime/state/checkpoints/ckpt-20260912-002440.json#artifact_registry`
  (sha256 of each review file **at the scan instant**), with
  `ckpt-20260912-002548.json` as the after-rewrite control.

Files: `audit_gateaccept_churn.py` (instrument), `report.json` (full table),
`raw/` (corpus manifest, registry timeline, scanner stdout, stability check).
Corpus digest was stable across the run (`675c5c5cf55d…`, 93 files).

## The decisive table

Every recorded full accept that worker-036 could not reproduce changed bytes **after** the scan:

| target | recorded accept file | reviewer | sha256 @00:24:40 | sha256 after | verdict now | classification |
|---|---|---|---|---|---|---|
| F1 | F1-review-lead-audit-r2.json | astra-lead-audit | `22ff0c1c3f60` | `df6114bc7c80` | revise | superseded in place 00:25:15 |
| F2a | F2a-review-lead-audit-r2.json | astra-lead-audit | `16c38e5b2873` | `76149eb039b5` | revise | superseded in place 00:25:15 |
| F2b | F2b-review-lead-audit-r2.json | astra-lead-audit | `b2a936d2b87f` | `7a93c45833c0` | revise | superseded in place 00:25:15 |
| F2b | F2b-review-07.json | deepseek-flash-07 | `41efb9545ec6` | `a04d4137f338` | revise | superseded in place 00:26:33 |
| A0 | A0-review-lead-audit-r2.json | astra-lead-audit | `7df2904783b5` | `86f08af1ea75` | revise | superseded in place 00:25:15 |
| L0 | L0-review-lead-audit-r2.json | astra-lead-audit | `b90d2acc4218` | `2801a0d34b09` | revise | superseded in place 00:25:15 |

The five `…-lead-audit-r2.json` writes share mtime `00:25:15.335434` — one batch write,
**35 seconds after the scan**. The current files each carry
`"My 00:22 accept is withdrawn"` in their findings and `event_id …lead-audit-r3-20260912T0025`;
the ingested supersession events are `audit-review-<T>-lead-audit-final-20260912T0027`
(`comms/outbox/astra-lead-audit.jsonl`, created_at 00:26:00).

The F0 `0→1` is the same mechanism in the other direction: worker-094 wrote an **accept** at
00:27:38 (`8c06325ed035`, checkpoint 00:28:02–00:28:47), worker-036 scanned at 00:28:52 inside
that window, and worker-094 withdrew it to revise at 00:29:05 (`f81049942475`, checkpoint
00:29:22 onward). Also L0-review-worker-006.json: `9d1fd2aae2` @00:24:40 → `50ad1d9d0ff5`
(revise, 00:25:24) → `98a42d274162` (accept again, 00:32:33).

**Recorded vs re-run (same corpus, recorded target hashes):**

| target | recorded 00:24:40 | re-run now | reproduces? |
|---|---|---|---|
| F0 | 0 | 1 (worker-038, written after the scan) | no — post-scan write |
| F1 | 1 (astra-lead-audit) | 0 | no — in-place supersession |
| F2a | 2 (astra-lead-audit, worker-047) | 1 (worker-047) | no — in-place supersession |
| F2b | 4 (astra-lead-audit, flash-07, flash-17, worker-030) | 2 (flash-17, worker-030) | no — two supersessions |
| A0 | 1 (astra-lead-audit) | 0 | no — in-place supersession |
| L0 | 3 (astra-lead-audit, worker-006, worker-011) | 1 (worker-011) | no — supersessions + rewrites |

Three recorded accepts were never touched and still reproduce: F2a worker-047, F2b worker-030,
F2b deepseek-flash-17.

## Findings

- **W074-CHURN-F1 (info, resolved).** All four W036 recorded-vs-rerun divergences are explained by
  post-scan review-file rewrites, not by a defective controller scan. At 00:24:40 the controller's
  own records are internally consistent: it recorded the pre-rewrite bytes in the same
  invocation's checkpoint.
- **W074-CHURN-F2 (major, open).** Provenance gap: gate reasons and `review_coverage` identify
  review evidence by **file name only** — no sha256, no mtime — while the protocol permits
  in-place overwrite of `reviews/*.json`. The pre-rewrite accept bytes
  (`22ff0c1c3f60…`, `16c38e5b2873…`, `b2a936d2b87f…`, `7df2904783b5…`, `b90d2acc4218…`) exist
  in no snapshot on disk; `artifacts/worker-042/gate_scan_gap/snapshot/reviews/` already holds the
  post-rewrite bytes. A recorded accept is therefore unverifiable the moment its author rewrites
  the file. **Fix:** put a per-file sha256 (or corpus digest) in the scan record and gate reason,
  and require supersession via a new file/event rather than in-place overwrite.
- **W074-CHURN-F3 (major, open).** The 00:24:40 reasons were stale within 35 s (five accepts
  withdrawn at 00:25:15; L0-worker-006 00:25:24; F2b-07 00:26:33; F0-094 00:29:05). The
  controller correctly withheld verdicts, but a gate reason must carry the corpus digest it was
  computed over so that "not older than the cited corpus" is checkable.
- **W074-CHURN-F4 (minor, open).** W036's `F-PHANTOM-*` wording is true only of the post-rewrite
  corpus; the correct statement is temporal non-reproducibility. W036's churn evidence also cites
  event ids that exist only **inside** the rewritten review files, not in the ingested event
  stream; the ingested supersession ids are `…-final-20260912T0027`.
- **W074-CHURN-F5 (info, recorded).** Moving target: by this run the closure revision had replaced
  all four canonical formulation artifacts (F0 `276009f4`→`0abb9ed8`, F1 `9a8bd4c9`→`cce9c601`,
  F2a `b6123750`→`5476a3f2`, F2b `1bb78ce9`→`55d0a1ea`; L0 `ce42d205`→`3e3d3553`; A0 unchanged).
  A re-scan at the **current** hashes yields near-zero full accepts (only L0 worker-006 at the new
  L0 hash). The next lifecycle pass must not carry the recorded coverage forward.

## Falsifier

Falsified if any of: (a) a file classified `superseded_in_place_after_scan` has the same sha256 in
`ckpt-20260912-002440.json#artifact_registry` and on disk now; (b) the recorded `review_coverage`
does not list that file as a full accept at 00:24:40; (c) the 00:24:40 registry has no sha256 for
that path; (d) a full accept still on disk at the recorded target hash has a sha256 equal to the
at-scan registry value (accept bytes survived); or (e) re-running this instrument on the same
pinned inputs yields a different classification.

## Authority

Worker-authored evidence only. This report sets no node status, no `validation_status=passed`,
and no gate verdict; it is an input to the controller's next gate-audit pass and to lead-audit.

## Pinned files

| path | sha256 |
|---|---|
| `artifacts/worker-074/gateaccept_churn/audit_gateaccept_churn.py` | `e3028ba1d8e647025c575066907ec77112fd97da6c2ed6170f2687c8bd2cfc07` |
| `artifacts/worker-074/gateaccept_churn/report.json` | `c4f23df10949028d21a591aac6f9e1a78a3885742f112ec69baca45acf4d074b` |
| `artifacts/worker-074/gateaccept_churn/raw/scan_output.txt` | `fa03469876ae8ac9616ca8af0600a66e880ad4be354bd046ad6cee4b69537b2b` |
| `artifacts/worker-074/gateaccept_churn/raw/current_corpus_manifest.json` | `41ce0b88997f47668b3aa77d21f32e9629619c0e5a2bbcd462e3c9dc195a14ff` |
| `artifacts/worker-074/gateaccept_churn/raw/registry_timeline.json` | `aade02bcb4852e9c0027bbad08115fafdd07c1bbbab6bab22b568b532e00b6a2` |
| `artifacts/worker-074/gateaccept_churn/raw/corpus_stability.txt` | `311c0eb8a1e4cf76d467f2061da6d3f27121aa433136720c81d04d9345ea5b28` |
| `runtime/state/checkpoints/ckpt-20260912-002440.json` (scan-instant control) | pinned in `report.json#pinned_inputs` |
| `runtime/state/controller_verification/lifecycle_20260912-002440.json` (recorded scan) | pinned in `report.json#pinned_inputs` |
