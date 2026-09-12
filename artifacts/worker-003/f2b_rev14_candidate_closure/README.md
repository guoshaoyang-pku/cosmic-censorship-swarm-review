# W003-F2B-REV14-CANDIDATE-INDEPENDENT-CLOSURE-01

**Worker:** worker-003 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Task:** one bounded class-bound task, self-selected (no card exists in `comms/inbox/worker-003.jsonl`)
**Snapshot:** candidate composed at 2026-09-12T01:00:24+08:00; verification run 2026-09-12T01:12+08:00
**Verdict:** `CANDIDATE_NOT_ACCEPTANCE_READY` — 12/16 checks pass, 7/7 planted controls discriminate
**Authority:** worker measurement only. No gate verdict, node status, `validation_status=passed`, or
canonical byte is written by this task. Every canonical path was read-only.

## Question

The worker-044 composed F2b rev14 candidate claims
`COMPOSED_F2B_CANDIDATE_ACCEPTANCE_READY_ON_LIVE_BASE`
(`artifacts/worker-044/f2b_live_closure_01/closure_summary.json#7bd2b25cd6fa`) and pins C0 `48cadb72`,
C2 `d94d490d`, F1 `88871f8f`, evidence `675a99d0`, FROZEN `a57492cc`, KEY_MANIFEST `61b9d8c1`,
aggregator `601355e7`. Does that candidate independently close the five blocking families
{H1 false containment denial, H2 inverted size premise, A2 non-self-verifying evidence, A6 unbound
alias registry, SEP-6 stale aggregator component pins} on the live rev13 / FROZEN-rev29 base without a
structural, mirror, class-separation or freeze-pin regression?

This is the missing non-author check: worker-044 authored the candidate, worker-008/066/086/005
supplied its parts. Nobody independent had re-measured the union.

## Method (own instrument, not the author's harness)

`verify_f2b_rev14_candidate.py` is written by worker-003 from scratch and does **not** import the
author's `live_closure.py`. It

1. restores a private `sandbox/` from the byte-pinned pristine copy (`pinned/sandbox_pristine`, tree
   manifest `346d3465d34f`) so the project checkers, which write evidence files in-tree, cannot leak
   state between runs;
2. re-measures all seven declared candidate hashes, both schema mirrors, and all 50 `FROZEN.files`
   pins against the candidate bytes;
3. re-checks each of the five families with mention-aware semantics (bracketed erratum and quoted
   historical text ignored, per the project's assertion-vs-mention doctrine) plus ledger
   cross-consistency;
4. runs the project's own pinned black-box checkers (`check_class_schema.py`, `verify_frozen.py`,
   `check_variant_deltas.py`, `check_variant_registry.py`, the guarded taxonomy writer) inside the
   sandbox, and both class-separation detector revisions (frozen pin `c266dbec`, live `a8c04fc3`);
5. plants seven mutations (K1–K7) that must make the corresponding check fire.

## Result

| family | status | measurement |
|---|---|---|
| H1 false containment denial | **pass** | no unquoted denial; nested chain `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` present and ledger-consistent |
| H2 inverted size premise | **pass** | reason states C2 strictly smaller, `E_C2 ⊂ E_C0`, C2-inextendibility strictly weaker |
| A2 evidence self-verifying | **fail (durability)** | doc 675a99d0 carries input pins and all three schemas declare it, but the pinned writer recomputes 9e335e9b: its write path drops `map_taxonomy_sha256`, `lead_contract_sha256`, `measured_at` |
| A6 alias registry bound | **pass** | `extensions.vocabulary_binding` path resolves; declared sha256 = live `46cd9f1e` |
| SEP-6 aggregator pins | **pass** | 2/2 component pins fresh inside the candidate (aggregator revision 7) |

Hard failures (candidate-level, both reproducible from the candidate's own pinned tools):

- **W003-F2B14-H1 — A2 durability.** The declared evidence doc is not a fixpoint of its own pinned
  writer. The no-write guard does protect the on-disk doc (the author's durability claim holds for
  the no-write path only); with `--write` the pinned writer moves the evidence to `9e335e9b` and
  breaks the three `f0_binding` declarations plus the FROZEN evidence pin. The other pinned writer,
  `close_findings_rev27.py 0234cd3c`, adds the three fields but stamps `measured_at=now`, so it is
  non-deterministic by construction. Repair: make one pinned writer emit the enriched doc
  deterministically (derive `measured_at` from the inputs) and re-pin it.
- **W003-F2B14-H2 — variant deltas not re-based.** Moving F1/C0 to the candidate rev14 bytes without
  re-basing the deltas leaves `check_variant_deltas.py` INVALID: `CH base hash drift b2ab6acb2bbe ->
  48cadb72e507`, `SET base hash drift d9cebb9404b2 -> 88871f8f3d9b`. The FROZEN-pinned evidence
  `variant_delta_check.json fc6ee058` is the live VALID result; the candidate's own checker emits
  `aa183716` INVALID. This is the same mechanical re-base step the rev13 publication performed; the
  candidate's R1–R9 list omits it.

Non-blocking findings: **N1** candidate FROZEN reuses revision label 29, which already has two
byte-images (CF-27) — publish at the next free revision; **N2** aggregator C2 `revision_note` still
says "revision 11 … 0fcc6a19"; **N3** L-FORM-04 is not closed (suite pin `56bcb4b3` = F1 rev12);
**N4** the guarded tool replacement `cde1a165` (live `de356d99`) must be published atomically;
**N5** scope limits; **N6** the live aggregator `schemas/af_scc_regularities.yaml` moved during the
run (`94562101` → `fa74db62` → `27255e5b`, last write 01:11:13) — that path is not in `FROZEN.files`,
so this is not a freeze breach, but the candidate's aggregator fork is based on `94562101` and must
be reconciled by the owner.

## Falsifier

Falsified if any check reported pass measures fail on the same pinned bytes, if a re-run yields a
different candidate hash, if any K1–K7 control stops discriminating, if the live base drifts off the
recorded snapshot (voids live applicability, not the snapshot measurement), or if the candidate tree
is shown not to be byte-identical to the hashes declared in the author's closure summary.

## Reproduction

```bash
cd artifacts/worker-003/f2b_rev14_candidate_closure
python3 verify_f2b_rev14_candidate.py     # exit 0 iff CANDIDATE_CLOSURE_VERIFIED_ON_LIVE_BASE
cat report.json                           # full per-check evidence, controls, findings
```

## Authority limits

No gate verdict, node transition, or canonical write. Does not re-derive worker-066's containment
patch and does not adjudicate the CLASSSEP detector drift (CF-26); class-separation is reported at
both detector hashes and both returned zero composite findings on the candidate C0.
