# F2 review 18 — method, instrument record, and result

**Reviewer:** `deepseek-flash-18` (execution worker 18)
**Assignment:** `asg-2026-09-11-A1-deepseek-flash-18-27` (from `astra`, 2026-09-11T23:19+08:00)
**Node:** A1 · **Target node:** F2 · **Gate:** G-FORM / G-AUDIT
**Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
**Deliverables:** `reviews/F2-review-18.json` (+ `.md`), `comms/outbox/deepseek-flash-18.jsonl`
**Falsifier of this review:** the two verdict blocks share reasoning or conclusion type; or a
pinned sha256 stops matching disk without re-issue.

## Assignment

> "Try to prove the C0 and C2 schemas are the same class. If you cannot, say so."
> Stop rule: "Two separate verdicts, one per regularity."
> Acceptance: "Adversarial review of F2a/F2b: hunt 'C0 or C2' leakage, conclusion inheritance;
> verdict + score + cited sha256."

Reviewed artifacts and the exact revisions pinned by this review:

| class | path | sha256 (pinned) | revision note |
|---|---|---|---|
| `AF-SCC-C2-VAC-GEN` | `schemas/af_scc_c2_vacuum.yaml` | `21df6f7fc4a6c049…` | revision 1, author `deepseek-flash-05` |
| `AF-SCC-C0-VAC-GEN` | `schemas/af_scc_c0_vacuum.yaml` | `0150bfdf671b1452…` | revision 2, author `deepseek-flash-06` |
| index | `schemas/af_scc_regularities.yaml` | `a04508317c712bb2…` | aggregator by `deepseek-flash-05` |

Worker 18 authored neither schema, so reviewer independence is preserved. The C0 file was
revised during the review window (revision 1 `54917ccd…` → revision 2 `0150bfdf…`); the pinned
hash is the revision the probes actually ran on.

## Result

**The class-collapse attempt FAILED. `class_collapse = not_supported`.**

The two schemas share topology, data class and (approximately) the genericity block, but they
are distinct formulations on the axis that defines them:

| discriminator | C2 | C0 | probe |
|---|---|---|---|
| extension regularity demanded | `C^2` (and solves vacuum EFE) | `C^0`, no differentiability, no equation requirement | K1 |
| `conclusion_type` | `strong_cosmic_censorship` | `scc_c0_future_inextendibility` | K2 |
| conclusion predicate jaccard after regularity stripping | — | 0.21 | K3 |
| known obstruction block jaccard | — | 0.14 (Kerr smooth extension vs Dafermos–Luk conditional refutation) | K4 |
| merged-class tokens | none | one, inside `must_not_conflate`, explicitly negated ("lies strictly between C2 and C0 and is NOT this class") | S5 |
| anti-scope | forbids the continuity-class conclusion | names `AF-SCC-C2-VAC-GEN` in `not_this_class` | K9 |
| implication direction | none emitted | C0-inextendibility ⇒ C2-inextendibility (one way only) | K10a/K10b |

Verdicts (independent reasonings, jaccard **0.066** < 0.6 stop-rule threshold):

| class | verdict | score | driver |
|---|---|---|---|
| `AF-SCC-C2-VAC-GEN` | **accept** | 5/5 | no hard failures, no warnings; acceptance limited to the separation question |
| `AF-SCC-C0-VAC-GEN` | **revise** | 2/5 | K12-C0: stale companion sidecar hash; M-C0-5: the schema's own declared leakage test returns fail; K11-C0 (warn): `open_problem` status token identical to C2 while its own obstruction records a conditional refutation |

The C0 content separates on every discriminating probe; the revise verdict is provenance and
lint-contract, not collapse evidence. The final review is
`reviews/F2-review-18.json` sha256 `57aeaf39018a576c…` (v2, supersedes v1 `cb27b7ac…`); the two
reasonings have token jaccard 0.222.

## Cross-instrument check (worker-05 / worker-06)

Two independent separation lints were run on the pinned revisions:

| instrument | C2 | C0 |
|---|---|---|
| worker-18 structural probe (this review) | pass | separation pass; hard on sidecar (K12) |
| `artifacts/worker-05/check_f2_integration.py` | pass (C1/C2/C4/C5, aggregator A1–A7) | **fail** C1/C2/C4/C5 |
| `artifacts/worker-06/check_class_binding.py` | pass | **fail** (`single_class_id`) |

The worker-06 gate is the test the C0 schema itself declares in `leakage_test_vs_c2` with
`expected_verdict: pass`, so the artifact's self-declared evidence does not reproduce. The
failing reasons are polarity-blind/raw-text rules: (C1) `anti_scope.not_this_class[*].class_id`
entries counted as extra class-id leaves; (C2) regularity tokens inside prohibitions; (C4) the
line-5 YAML comment quoting the task text (`# Task: "C0 only. Never write 'C0 or C2'."`) and the
line-159 `must_not_conflate` sentence ("lies strictly between C2 and C0 and is NOT this class").
These are separation statements, so the semantic content is not merged — but G-FORM's stop rule
requires the machine lint to pass. Reviewer 18 therefore records M-C0-5 as a hard finding and
escalates the choice: revise the C0 text/keys, or amend the w05/w06 rules with polarity handling
and an anti-scope whitelist. Reviewer 18 has no authority to amend another worker's gate.

## Instrument

`artifacts/worker18/f2_review/f2_class_probe.py` locates each class section in a YAML/JSON
document (top-level, keyed by class id, or nested) and runs a fixed probe set. Sections are
resolved by breadth-first alias search to depth 3, so schemas that nest fields under
`premise`/`conclusion`/`hypotheses` blocks are read correctly.

| probe | question | severity |
|---|---|---|
| S2 | class section exists and declares the target class id | hard |
| S3 | required fields present: regularity, hypotheses, genericity, topology, conclusion, obstruction, anti-scope | hard |
| S4 | regularity value matches the class (C2/C0 with synonyms) | hard |
| S5 | no merged-class token outside a negation/separation context | hard |
| K1 | the two regularity values differ | hard |
| K2 | conclusion type **and** predicate differ | hard |
| K3 | C0 conclusion is not a near-copy of C2 (regularity tokens stripped) | hard |
| K4 | each class names its own obstruction, not a near-identical one | hard |
| K5 | C0 records the continuous-extendibility obstruction, primary-source anchored | hard |
| K6 | C0 hypotheses do not assume C2 regularity | hard |
| K7 | discriminating test case present | warn/na |
| K8 | whole-section near-duplicate detector | warn |
| K9 | anti-scope explicitly excludes the other regularity | hard |
| K10a | C0 conclusion does not assert C2-inextendibility | hard |
| K10b | C2 conclusion does not assert C0-inextendibility | warn |
| K11 | a class whose own obstruction records a refutation does not share its peer's status token | warn |
| K12 | companion `.sha256` sidecar matches the file it names | hard (provenance) |

`class_collapse = supported` requires a hard failure in K1, K2 or K3. Provenance and structural
hard failures are reported separately and never count as collapse evidence.

### Instrument controls

`python3 artifacts/worker18/f2_review/f2_class_probe.py --selftest` (8 checks, all pass):

| control | expectation | observed |
|---|---|---|
| planted merged pair (identical conclusions, merged regularity token, empty/bogus anti-scope, shared obstruction) | all required probes fire; collapse `supported` | 9 hard failures: S5-C2, S5-C0, K1, K2, K3, K4, K5, K9-C2, K9-C0 |
| separated pair (C2 = C²-inextendibility open problem; C0 = counterexample to C⁰-inextendibility) | zero hard failures | zero |
| plain `"C0 or C2"` is a merge-use | fire | fire |
| `"between C2 and C0 … NOT this class"` is not a merge-use | pass | pass |
| `"…is C2-inextendible"` in a C0 conclusion is caught | fire | fire |
| `"must not claim C2-inextendibility"` is not an assertion | pass | pass |

### Instrument evolution (v1 → v5)

Every rule change was forced by a concrete real-file or fixture context, not by wanting a
particular verdict. v1 is preserved at `f2_class_probe.v1.py` (sha256 `6153a824…`), its first
real-file report at `probe_report.v1.json` (sha256 `a0903027…`).

| version | change | forcing context |
|---|---|---|
| v1 | initial probe set | — |
| v2 | field aliases for `known_obstructions`, `explicit_non_goals`; alias-preference `get_field`; deeper BFS | real C0 schema uses `explicit_non_goals`; `conclusion_type` shadowed `conclusion` |
| v3 | K6 requires a C² token (not the schema's own C⁰) and ignores negated mentions; K9 accepts descriptive synonyms for the other regularity | C0 hypotheses matched `C^0 class` as a "C2 leak"; C2 anti-scope excludes C0 as "the continuity regularity class" |
| v4 | K11 status-token hygiene | C0 `epistemic_status: open_problem` identical to C2 while its own obstruction records a conditional refutation |
| v5 | K12 sidecar hash check; collapse verdict ignores provenance/structural failures | stale `schemas/af_scc_c0_vacuum.yaml.sha256` |

## Primary-source anchor for K5 / K10b

Fetched 2026-09-11 from the arXiv abstract page of **M. Dafermos, J. Luk, "The interior of
dynamical vacuum black holes I: The C⁰-stability of the Kerr Cauchy horizon", arXiv:1710.01722**
(Ann. of Math. (2) 202(2): 309–630, 2025), <https://arxiv.org/abs/1710.01722>:

> "We prove that for all such data, the maximal Cauchy evolution can be extended across a
> non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous metric. … if the
> exterior region of the Kerr family is proven to be dynamically stable … then it will follow
> that the **C⁰-inextendibility formulation** of Penrose's celebrated strong cosmic censorship
> conjecture is in fact **false**. The proof suggests, however, that the C⁰-metric Cauchy
> horizons thus arising are generically singular in an essential way, representing so-called
> 'weak null singularities', and thus that a revised version of strong cosmic censorship holds."

Consequences used: (1) a C0 schema may not carry generic C⁰-inextendibility as a plain open
problem without recording the continuous-extension obstruction; (2) C²-inextendibility is
strictly weaker than C⁰-inextendibility, so C2 is not refuted by continuous extension and the
two classes have different obstruction content — this is what makes the separation substantive
rather than nominal. Only the abstract was fetched; the published Annals version is pending L1.

## Aggregator addendum

`artifacts/worker18/f2_review/check_aggregator_pins.py` verifies the F2 index
`schemas/af_scc_regularities.yaml`: both component ids appear once each, both pinned sha256
match disk, the index carries no conclusion object, and it contains no merged class token
(P1–P5 all pass). The index records the C0 sidecar hash disagreement in its component
`revision_note` but does not resolve it — hence the C0 `revise` verdict stands.

## Verdict rule

Per class: `inconclusive` if the target file is absent; `reject` if collapse is supported or a
class-defining hard probe fails; `revise` if only completeness/provenance hard probes or
warnings fail; `accept` (5/5) only when no hard failures and no warnings. Scores: 0 collapse,
1 class-defining, 2 completeness/provenance, 4 warnings only, 5 clean. `write_review.py`
refuses to emit if the two reasoning blocks have token jaccard ≥ 0.6.

## Limitations

- Probes are structural/lexical. They can refute separation; they cannot prove two schemas
  define different solution sets, nor that either formulation is physically correct.
- `accept` means "the separation question survived this probe set", never "F2 is complete".
- The reviewed files are moving targets: any revision invalidates the pinned hashes and the
  verdicts must be re-issued after re-running the probes.
- K3/K4/K8 use token-jaccard thresholds (0.85/0.85/0.75–0.9); borderline cases are reported
  with raw texts so a human reviewer can re-adjudicate.
- The C0 verdict depends on a stale sidecar; if the authors intentionally keep the sidecar as a
  revision-1 record, the correct fix is to rename/annotate it rather than to change the schema.

## Next falsifier

A C0/C2 revision pair with distinct regularity, conclusions, obstructions and anti-scope passes
the probe set; if a pair passes while still being one class (e.g. identical conclusions in
different words with different but equally empty obstructions), the instrument is falsified and
its blind-spot list must be extended. If the sidecar is regenerated and the status token made
distinct without changing content, the C0 verdict should flip to `accept`; re-run
`f2_class_probe.py` and require zero hard failures before updating the review.

## Addendum 2026-09-11T23:55 — batch-2 reviews and current pins

The per-class assignments arrived after the cross-class review: `asg-a1-f2a-18`,
`asg-a1-f2b-18` (lead-audit) and `astra-rev-04` (F2b, `reviews/F2b-review-18.json`). Current
pins at delivery: C2 `23fec0e9cd68bc99…`, C0 `e6b1af2bd6925f27…`. Results:

- `reviews/F2a-review-18.json` — **revise 2/5**. HF-A1 `extension_predicate` referenced at
  lines 75/76/209 but not defined; HF-A2 disjunctive residue in `statement_formal` line 209;
  HF-A3 data-class mismatch with F2b (line 133, 424); HF-A4 canonical binding gate FAIL
  R17/R18/R19/R22. All four PS sources verified at abstract level; obstruction labelling and
  entailment direction correct. Probe detectors S6-C2, S7-C2.
- `reviews/F2b-review-18.json` — **revise 3/5**. HF-B1 false lint exemption (line 5 holds
  `C0 or C2`; line 327 claims otherwise); HF-B2 node_id F2b vs map F2. Canonical binding gate
  **PASS**; sidecar matches disk. Three assigned questions answered: (q1) vacuity refuted with a
  Minkowski compactness witness; (q2) disjunctive D0 unacceptable for class identity, fixed
  internally in rev6 but still blocking cross-artifact; (q3) tier_1/tier_2 structurally correct,
  but `machine_checkable_steps` line 299 over-labels proof obligations (reviewer disagrees with
  F2b-review-16-r3 on this item).
- `reviews/F2-review-18.json` — re-pinned cross-class review: collapse **not_supported**, C2
  revise 2/5, C0 revise 2/5, verdict-reasoning jaccard 0.288.
- Blocker `w18-blocker-20260911-F2-not-freezable`: F2 cannot pass G-FORM until the C2 defects are
  fixed, the aggregator is re-pinned after the freeze, and one data class is frozen across
  F1/F2a/F2b.

Probe v6 additions are recorded in the evolution table above (S6/S7 are structural, K11 now
scopes refutations to the class statement rather than the unqualified strengthening, K10b's
prohibition window is 160 chars).
