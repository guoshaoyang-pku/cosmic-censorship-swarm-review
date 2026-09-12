# W057-GFORM-F2B-VERDICT-SENSITIVITY-01 — worker-057

**Task (self-selected; no card in `comms/inbox/worker-057.jsonl`).** Class-bound:
`AF-SCC-C0-VAC-GEN`; node `F2b`; gate `G-FORM`. One bounded, read-only measurement:
*at the live F2b bytes, do the accept verdicts and the blocking revise findings exercise the
same carriers?*

This is a worker measurement. It issues **no review verdict on the schema, no node status, no
`validation_status`, and no gate verdict**. Coverage adjudication belongs to the audit lead
(`astra-life05-verify-gform-r3`) and the controller.

## Question and why it matters

G-FORM is pending on F2b coverage: the gate needs **≥2 independent full accepts at one stable
hash**, and the controller's own fresh scan
(`runtime/state/controller_verification/lifecycle_20260912-011029.json#717a7bb370fe`) already
reports `F2b two_distinct_accepts = true` with accept reviewers `[worker-071, worker-072,
worker-090]`. At the same bytes, several revise verdicts name two live text carriers:

| id | carrier | line | text |
|---|---|---|---|
| **HC1** | `regularity.must_not_conflate[0]` | 152 | "No containment with C2 or C0 is asserted here" |
| **HC2** | `implication_ledger.forbidden_transfers[0].reason` | 246 | "C2 is a strictly larger extension class" |

Both contradict the same file's chain at line 239:
`E_C0 contains E_H2loc contains E_{C^{1,1}} contains E_C2`.

An accept and a revise can coexist at one hash only if the accept instrument and the revise
instrument are sensitive to **different** properties. This artifact measures that difference
directly, from the instruments' own sources.

## Method (pre-registered, deterministic)

1. **Pin** the live F2b schema `b2ab6acb2bbe…4501c` (and its mirror), F2a, F1, FROZEN rev29
   `815e08079aef…`, F0 taxonomy `0abb9ed8a961…`, and the controller scan above. A moved byte
   aborts the run.
2. **Harvest** every F2b schema verdict that *binds* the live hash through a binding field
   (`reviewed_sha256`, `artifact_sha256`, `reviewed_pins.F2b.sha256`,
   `frozen_pin.pins_target_at`, `target_id`), from `reviews/*.json` and the accepted review
   records in `research_map.json`. Merely citing the hash in evidence is a citation, not a
   binding, and is excluded. Duplicate emissions of one verdict are collapsed.
3. **Resolve** each verdict's declared instrument sources on disk and count seven pre-registered
   literal probes in each source: the two carrier texts, the two containing blocks, the
   contradicted chain field and two chain literals.
4. **Classify**: `targeted_defect_text` (names a carrier text), `block_referencing_only`
   (touches a block but never the defect text), `blind_to_both_blocks`,
   `instrument_unresolved`. A verdict is **carrier-capable** iff at least one of its resolved
   instruments names a carrier text *and* reads the chain it contradicts — a necessary
   condition for having exercised that carrier.
5. **Liveness check**: for accepted-event rows with no file of their own, record what the
   same-`review_id` review file on disk says **now**.

## Verdict

> `LIVE_F2B_CENSUS_AT_b2ab6acb2bbe__7_ACCEPT_32_REVISE__0_OF_7_ACCEPT_INSTRUMENTS_CARRIER_CAPABLE__1_ACCEPT_ROW(S)_FLIPPED_TO_REVISE_ON_DISK`

All twelve controls pass (C1–C12), including two real-instrument positive controls
(worker-017, worker-018) and three synthetic classifier controls.

| population | n | carrier-capable | reads the chain | names HC1 | names HC2 |
|---|---:|---:|---:|---:|---:|
| accept | 7 | **0** | **0** | 0 | 0 |
| revise | 32 | **13** | 16 | 11 | 14 |
| controller-counted full accepts `[071, 072, 090]` | 3 | **0** | 0 | 0 | 0 |

The accepted and rejected verdicts are **disjoint in what they can see**. Every accept
instrument is `block_referencing_only` or unresolved: none contains either carrier text and
none reads `extension_class_containment` (or an equivalent chain literal). The revise side is
carried by instruments that do.

## Findings

- **F2BS-01 (confirmed).** Both carriers are live at the pinned bytes: HC1 line 152, HC2 line
  246, contradicted by the chain at line 239.
- **F2BS-02 (confirmed).** At one hash the verdict set is split 7 accept / 32 revise (a
  reviewer may appear on both sides at different times at the same bytes; each dated verdict is
  kept).
- **F2BS-03 (confirmed).** **0 of 7** live-hash accept instruments name either carrier text and
  **0 of 7** read the contradicted chain field. Their accepts cannot have discharged the
  HC1/HC2 revise findings at these bytes.
- **F2BS-04 (confirmed).** **13 of 32** revise instruments are carrier-capable (HC1 10, HC2 13).
  The blocking findings are carried by instruments that can see the carriers, not by the accept
  instruments.
- **F2BS-05 (confirmed).** The controller's 01:10 scan counts F2b `two_distinct_accepts=true`
  for `[worker-071, worker-072, worker-090]` at the same bytes that carry both carriers.
- **F2BS-06 (confirmed).** **0 of 3** controller-counted accepts has any resolved instrument that
  names a carrier text and reads the contradicted chain (`worker-090` block-only,
  `worker-072` block-only, `worker-071` block-only).
- **F2BS-07 (confirmed).** **1 accept row has flipped on disk inside the measurement window.**
  The accepted event `w072-2026-09-12T01:10:13+08:00-review-f2b` (worker-072, accept 4.0) has a
  same-`review_id` review file `reviews/F2b-review-worker-072-rev29.json` that now carries
  `verdict=revise, score=3.0` with blocking finding `W072-F2B-HF-01` on line 152 and its own
  disclosure `F-06` that its earlier 33-check instrument "had no internal cross-field
  co[ntradiction check]" and `F-07` that it "is no longer an accept for F2b". The accepted map
  event and the current file therefore disagree at the same bytes; a coverage count taken before
  the rewrite is stale for the current corpus. (worker-061 shows the same accept→carrier-capable
  revise evolution at a later minute.)

## Reading

The ≥2-accept coverage criterion is numerically met at `b2ab6acb2bbe`, but every counted accept
rests on an instrument that neither reads the two live carriers nor the chain they contradict,
and one of the three counted accepts has already been withdrawn on disk by its own author. The
accept count and the blocking findings do not discharge each other. Whether the carriers are
material to a gate pass is an adjudication for the audit lead; this artifact supplies the
sensitivity table that adjudication needs.

## Controls (12/12)

| id | control | result |
|---|---|---|
| C1 | all seven live pins match | pass |
| C2 | synthetic targeted instrument → `targeted_defect_text` | pass |
| C3 | synthetic empty instrument → `blind_to_both_blocks` | pass |
| C4 | block-reading-only instrument is not detect-capable | pass |
| C5 | two in-memory repairs remove both carriers (2 → 0) | pass |
| C6 | two independent full builds hash identically | pass |
| C7 | canonical inputs unchanged during the run | pass |
| C8 | worker-017's real revise instrument is carrier-capable | pass |
| C9 | worker-018's real C17/C18 instrument is carrier-capable | pass |
| C10 | no live-hash accept instrument is carrier-capable | pass |
| C11 | none of the controller-counted accepts is carrier-capable | pass |
| C12 | accept→revise on-disk flip recorded | pass |

## Falsifier

Re-hash the pinned inputs and the review corpus and re-run
`audit_f2b_verdict_sensitivity.py`. The report is falsified for the recorded hashes if any pin
differs, if any harvested review source hash differs (corpus digest
`review_corpus.corpus_sha256`), if a live-hash accept instrument is shown to name HC1/HC2 text
**and** read the contradicted chain, if either carrier is absent from the live F2b bytes, if the
controller scan pin no longer reports F2b accepts, or if any control C1–C12 flips. A moved byte
or a rewritten review file voids the report for the new corpus.

## Evidence

- Inputs: `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`, mirror
  `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`,
  `artifacts/formulation/FROZEN.json#815e08079aef`,
  `research_map/formulation_taxonomy.yaml#0abb9ed8a961`,
  `runtime/state/controller_verification/lifecycle_20260912-011029.json#717a7bb370fe`.
- Verdict sources and instrument hashes: `report.json` → `verdict_inventory[]`
  (`source_sha256`, `instruments[].sha256`, `probe_counts`, `sensitivity`).
- Artifacts: `report.json` (deterministic machine report), `REPORT.md` (this file),
  `audit_f2b_verdict_sensitivity.py` (instrument), `manifest.json` (authoritative hashes; a file
  cannot contain its own hash).

## Scope and honesty

- No gate verdict, node status or `validation_status` is claimed; `claims_completion: false`.
- No claim that any accept instrument is *incorrect*. The claim is narrower and deductive: an
  instrument whose source never contains the carrier text cannot have exercised that carrier.
  The only escape is generic re-derivation without those tokens; the full probe table is in
  `report.json` so a reader can check that.
- No canonical artifact was written or edited. Writes are confined to
  `artifacts/worker-057/f2b_live_verdict_sensitivity/` and the worker's own checkpoint/outbox.
- This does not decide whether the cosmic-censorship formulation is mathematically adequate.
