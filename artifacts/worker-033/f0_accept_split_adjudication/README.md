# W033-F0-ACCEPT-SPLIT-ADJ-01 — independent adjudication of the F0 accept/revise split

worker-033, 2026-09-12. Class-bound to all four frozen classes.

## Why this task

At the canonical F0 hash `276009f4f63d` two independent reviewers disagreed, and G-F0 requires two
independent accepts at the published hash:

| reviewer | time | verdict | consequence |
|---|---|---|---|
| worker-040 | 00:22:41 | accept (4.0) | would be the first accept |
| worker-082 | 00:23:10 | revise | W082-F-01, W082-F-02 blocking |

The 00:21:55 controller gate audit recorded **0 distinct accepts** at this hash. Voting does not
settle it, so this worker re-derived each contested claim from the primary bytes.

## Verdict

**revise** at `276009f4f63d`, score 3.0. Not a gate verdict, not a done-status, no promotion.

- **W082-F-01 confirmed** (content-critical). `AF-WCC-SCALAR-SPH.conclusion` (lines 404–407)
  quantifies *"For generic data in the class"* while its own H4 (lines 397–401) is
  `unresolved: true` and says the genericity notion *"must be named before any claim is filed"*.
  Both canonical F0 and the authoring mirror record `genericity_kind: unresolved` for this class.
  The three vacuum classes bind *"For every admissible (s,delta) there is a comeager set
  G_{s,delta}"* (lines 184, 265, 337). The same conclusion also asserts an **unsourced
  "equivalently"**.
- **W082-F-02 confirmed, mechanism corrected.** `resolved_divergences[D3]` claims the comeager
  quantifier is explicit in *"each class conclusion text"*, but only 3 of 4 classes satisfy that.
  The D3 detector in `check_taxonomy_consistency.py` reads only the two SCC classes and never names
  `AF-WCC-SCALAR-SPH`. Correction to worker-082: the checker *does* compare that class's
  genericity **axis label** in its generic loop, so "without inspecting that class" is imprecise —
  it inspects the label, never the conclusion text.
- **W033-F0-01/02 (new).** `VOCAB_ALIASES.json#46cd9f1eb534` declares
  `scc_c2_future_inextendibility` / `scc_c0_future_inextendibility` **registry-canonical** and
  `strong_cosmic_censorship_C2/C0` their **aliases**. Canonical F0's allowed list uses the alias
  tokens, while the registry policy says aliases *"must never appear in a new canonical artifact"*.
  Only F1 carries `vocabulary_aliases_ref`; F2a/F2b use canonical tokens but carry no pointer, and
  the registry lives in `artifacts/formulation/**`, which the canonical-path policy has not yet
  published byte-identically. So G-FORM's "exact conclusion_type" is not decidable from canonical
  artifacts alone.

## Self-correction (recorded deliberately)

My own earlier review `w033-2026-09-12T002305-review-F2a` graded this vocabulary difference as
**HF-02 "class_leakage; critical" against F2a**. That attribution is **withdrawn**: F2a's token is
the registry-*canonical* one, so the nonconformance sits with F0's allowed list and the missing
pointer — not with F2a's class identity. Direction survives; target and severity do not.

## Falsifier

Republish F0 at a new hash with (i) an explicit named genericity set in the SCALAR-SPH conclusion,
(ii) D3 scoped to the classes actually checked, (iii) registry-canonical tokens in the allowed list
**or** a canonical `vocabulary_aliases_ref` in F0. Update `PINNED` and re-run the checker:
ADJ-04/05/06/07/10/12 must flip to `refuted`. A repaired document that still fails means the
checker is defective and the verdict is void. Any byte edit to `276009f4f63d`, or drift of
`VOCAB_ALIASES.json` off `46cd9f1eb534`, also voids the affected findings.

## Files

| file | role |
|---|---|
| `check_f0_accept_split.py` | independent checker, 12 checks, deterministic/offline/read-only |
| `report.json` | machine report: per-check status, observed values, pinned hashes, the split |
| `mutation_controls.py` / `mutation_controls.json` | falsifier: 6 planted repairs + 2 negative controls, **8/8 pass** |
| `review.json` | the review verdict event payload |
| `pinned/SHA256SUMS` | hashes of every input and output |
| `run.log` | reproduction transcript |

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-033/f0_accept_split_adjudication/check_f0_accept_split.py
python3 artifacts/worker-033/f0_accept_split_adjudication/mutation_controls.py
sha256sum -c artifacts/worker-033/f0_accept_split_adjudication/pinned/SHA256SUMS
```

Independence: this checker shares no code with worker-040, worker-082, or the authoring tools; it
reads only canonical bytes plus the review events, and it fails when a repair is planted.
