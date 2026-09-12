# W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01

- **Task**: one bounded class-bound task, self-claimed (no open worker-016 inbox card;
  FORM-HELDOUT-08 closed 00:15 and was superseded by FORM-HELDOUT-09).
- **Class / sibling control**: `AF-SCC-C0-VAC-GEN` / `AF-SCC-C2-VAC-GEN`
- **Node / gate**: `F2b` / `G-FORM`
- **Actor**: worker-016 (slot worker-016)
- **Generated**: 2026-09-12T01:15:15+08:00 (run timestamp in `results.json.generated_at`)
- **Authority**: worker measurement and adjudication evidence only. No node completion, no
  theorem, no gate verdict, no canonical write, no adoption of any repair candidate.

## Question

The pass-07 controller notice records F2b at the frozen rev29 pin with 2 full accepts
(worker-072, worker-090) **and** late adverse verdicts, and leaves
`astra-life05-verify-gform-r3` to "weigh the late revise verdicts". This task independently
adjudicates the recurring adverse carriers **on the pinned bytes**, and tests whether the
circulating repairs are landable.

Pinned inputs (all measured == declared before any check, `results.json.pins_all_match=true`):

| artifact | sha256 (prefix) |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b canonical) | `b2ab6acb2bbe` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | `b2ab6acb2bbe` |
| `schemas/af_scc_c2_vacuum.yaml` (sibling control) | `e9a27996dfd3` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |

## Findings at the frozen pin

### H1 — CONFIRMED (blocking for a clean accept)

`implication_ledger.forbidden_transfers[0].reason` (line 246):

> "C2 is a strictly **larger** extension class, so C2-inextendibility is strictly weaker"

The same file's `extension_class_containment` (line 239) declares
`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`, i.e. **E_C2 is the smallest extension set**. The sibling
C2 artifact (`e9a27996dfd3`) states the canonical ordering explicitly
(`E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`, "the earlier revision had the H2_loc ordering wrong").
The transfer row's *direction* is right; its stated premise is inverted.

Falsifier: a frozen revision in which `forbidden_transfers[0].reason` calls C2 the smaller
extension class (or states `E_C2 subset of E_C0`).

### H2 — CONFIRMED (blocking for a clean accept)

`regularity.must_not_conflate[0]` (line 152):

> "No containment with C2 or C0 is asserted here"

while the same file asserts containment with H2_loc in `extension_class_containment` and in the
`one_way_entailments` rows, and the sibling C2 artifact marks that exact denial as a corrected
error ("the earlier 'no containment with C2 is asserted' was **wrong**").

Disclosure: the frozen entry cites worker-16 `F2b-16-02`. At the rev29 canonical ordering that
earlier accepted wording is superseded; this is recorded as a worker-16 **self-correction**, not
a third-party accusation.

Falsifier: a frozen revision whose `must_not_conflate` list no longer denies H2_loc containment.

### H3 — CONFIRMED IN THE CIRCULATING REPAIRS (blocks landing them, not the frozen pin)

Both circulating candidates replace the H2 denial with:

> "...so **H2_loc-inextendibility ENTAILS this class's conclusion**"

In the C0 file that is the wrong direction: `conclusion.forbidden_weakenings` states
"H2_loc-inextendibility is weaker and entails the C2 sibling, **not this class**", and
`one_way_entailments` runs C0 ⇒ H2_loc. The identical sentence is *true in the C2 sibling*
(`E_C2 ⊂ E_H2loc`) — a class-relativity control: same sentence, accepted under own=C2, rejected
under own=C0. Independently reproduces worker-029's `W029-R7-H2` (raised first in
`reviews/F2b-repair-candidate-verify-worker-029.json`).

Falsifier: a candidate whose H2_loc replacement keeps the entailment direction C0 ⇒ H2_loc, or
makes no entailment claim.

### V1 — CONFIRMED DIVERGENCE (non-blocking; already adjudicated)

`conclusion.conclusion_type = scc_c0_future_inextendibility` is an accepted VOCAB alias of
`strong_cosmic_censorship_C0`, but is absent from the F0 allowed list. VOCAB policy forbids alias
tokens in a new canonical artifact. Severity was adjudicated non-blocking by worker-066; the
schema cannot satisfy both frozen rule R11 and literal F0 membership, so this is the separate
single-sourcing conflict recorded as `w017-20260912-vocab-source-blocker`. Not charged here.

Falsifier: an F0/VOCAB revision that re-stamps the alias as canonical, or a frozen artifact using
an F0 allowed token.

## Repair adequacy (independent re-test of four candidates)

| candidate | producer | closes H1 | closes H2 | introduces H3 | closes V1 | landable |
|---|---|:--:|:--:|:--:|:--:|:--:|
| `84b5d3fa` (circulating) | worker-080 | yes | yes | **yes** | no | **no** |
| `98f9ec83` (rev12) | worker-066 | yes | yes | **yes** | no | **no** |
| `51c253c4` (corrected) | worker-029 | yes | yes | no | no | **yes** |
| `4951cc96` (nesting, makes no entailment claim) | worker-029 | yes | yes | no | no | **yes** |

All four change only prose/ledger leaves in this checker's structural diff (no formal-field
change: conclusion text, topology, genericity and regularity tokens untouched). None re-stamps
the V1 token, so a landing revision should either re-stamp it or record an explicit waiver.

## Controls (pre-registered, all held; run exit code 0)

| evaluation | H1 | H2 | H3 | expectation |
|---|:--:|:--:|:--:|---|
| frozen `b2ab6acb2bbe` | fire | fire | clean | as registered |
| byte-identical null copy | fire | fire | clean | as registered |
| `84b5d3fa` | clean | clean | **fire** | as registered |
| `98f9ec83` | clean | clean | **fire** | as registered |
| `51c253c4` | clean | clean | clean | as registered |
| `4951cc96` | clean | clean | clean | as registered |
| synthetic re-inversion of the repaired reason | fire | — | — | as registered |
| synthetic re-insertion of the denial | — | fire | — | as registered |
| synthetic entailment flip of `84b5d3fa` | clean | clean | clean | as registered |

## Cluster census

`cluster_table.json`: 18 adverse verdicts bound to `b2ab6acb2bbe` in the window from
2026-09-12T00:50, keyword-mapped to carrier families (lower bound; ids-only entries map to
none): H1 6, V1 4, H3 3, H2 1.

## Disposition for the audit lead (worker-level recommendation, not a verdict)

1. H1 and H2 are real at the frozen pin; F2b at `b2ab6acb2bbe` should not be *cleanly* accepted
   without a metadata/prose repair.
2. The two circulating repairs are not landable as-is (H3); use `51c253c4` or `4951cc96`, or flip
   the entailment clause as in the synthetic control.
3. Landing any repaired revision bumps FROZEN and voids rev29-bound verdicts; reviewers must
   re-pin FROZEN bytes + per-file pins (CF-27 moving-target rule).
4. V1 needs the separate single-sourcing ruling before any new canonical revision re-stamps it.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-016/f2b_rev29_containment_adjudication/adjudicate_f2b_containment.py
# exit 0; writes results.json + cluster_table.json; read-only on all canonical artifacts
```

Limitations: the checker is lexical/structural over the frozen YAML and adjudicates entailment
direction against the file's own declared ledger and the corrected sibling; it does not prove the
underlying PDE statements. Worker-016 contributed an earlier F2b repair (disclosed at H2); this
task adopts no candidate and moves no gate.
