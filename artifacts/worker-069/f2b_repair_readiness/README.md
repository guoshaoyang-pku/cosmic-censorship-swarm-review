# W069-F2B-REPAIR-READINESS-01 — independent F2b repair triage

**Verdict: `REPAIR_PARTIAL_RESIDUALS_LIVE`** · node `F2b` · class `AF-SCC-C0-VAC-GEN` · gate `G-FORM`
· run_digest `8476a8fa248ab34e…` · controls **8/8** · worker-level measurement only.

## Question

worker-066 announced an F2b repair as *ready, not landed*: live rev13 C0 plus two
reference edits hashes to `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`
and "clears both defects". At the same time F2b has **0 of the ≥2 accepts** G-FORM
needs. This task measures, independently and at the live pins, **which of the
recorded F2b hard-failure predicates the candidate actually clears, and which
survive it** — so the owner can see whether landing the two-edit repair is
sufficient, and if not, what else must move.

This is a measurement, not an adjudication. No gate verdict, node status or
`validation_status` is set.

## Method

* Candidate reconstructed from the **live** canonical bytes plus the two
  byte-exact `-`/`+` pairs parsed out of the pinned patch
  (`artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff`,
  sha256 `d777a8cb84aa7689`). Reconstruction hash equals the announced
  `84b5d3fa29a677ad…`; nothing was copied from worker-066's tooling.
* Predicates re-implemented from the recorded finding texts (worker-008, -015,
  -017, -018, -034, -035, -038, -044, -047, -058, -062, -066, -069, -075, -081,
  -090, -095, -097, -100). Each is evaluated on live bytes, on candidate bytes,
  and on pre-registered mutation controls.
* The containment-denial predicate is evaluated **twice** — naive, and
  assertion-aware (bracketed repair notes and quoted spans removed) — because
  the candidate keeps the old denial as a *quoted mention* inside its bracketed
  R2 repair note. This is the project's known CF-16 mention-vs-assertion
  pattern; both readings are reported rather than one being tuned to a
  preferred answer.
* P9 reads the accepted stream, which grows with traffic, so the stream is
  snapshotted to `raw/events.snapshot.jsonl` (sha256 `561c90a7fee6727a…`,
  6708 lines) and the report records its hash. Re-running with
  `--events-snapshot raw/events.snapshot.jsonl` reproduces run_digest
  `8476a8fa248ab34e…` exactly; a later live run legitimately produces a new
  snapshot hash and therefore a new digest, while the F2b predicates and pins
  stay reproducible.

### Pins (all re-measured, stable entry→exit; control C8)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86…` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd…` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79e…` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c9…` |
| `artifacts/formulation/FROZEN.json` (rev29, frozen 00:57:26) | `815e08079aefbc16…` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df73…` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77…` |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `7e44de0e3906dc74…` |
| `artifacts/formulation/tools/run_acceptance.py` | `e544c36d2d168fdf…` |
| candidate (reconstructed) | `84b5d3fa29a677ad…` |

## Results

| # | predicate | live | candidate | disposition |
|---|---|---|---|---|
| P1a | containment denial, **naive** text scan | fires | **fires** | `MENTION_RESIDUE` |
| P1b | containment denial, **assertion-aware** | fires | clears | `CLEARED_BY_CANDIDATE` |
| P2 | inverted size premise (`strictly larger`) | fires | clears | `CLEARED_BY_CANDIDATE` |
| P3 | conclusion token ∉ F0 `allowed` (literal) | fires | fires | `SURVIVES_CANDIDATE` |
| P4 | no `vocabulary_aliases_ref` pointer (F1 has one) | fires | fires | `SURVIVES_CANDIDATE` |
| P5 | `genericity.kind` ∉ F0 `allowed` (literal) | fires | fires | `SURVIVES_CANDIDATE` |
| P6 | acceptance preflight: corpus base ≠ live C0 | fires | fires | `NON_SCHEMA_BLOCKER` |
| P7 | consistency evidence embeds no compared-tree digest | fires | fires | `NON_SCHEMA_BLOCKER` |
| P8 | `schemas/af_scc_c0_vacuum.yaml.sha256` pins rev11 | fires | fires | `NON_SCHEMA_BLOCKER` |
| P9 | FROZEN rev29 pins with no declaring artifact event | — | — | `BASELINE_OK` |
| P10 | parses, no duplicate mapping keys | — | — | `STRUCTURAL_BASELINE_OK` |

### What the candidate clears

The **containment cluster** — the only schema-content defects recorded against F2b
at rev13 — is cleared:

* **P1b** `regularity.must_not_conflate[0]`: the denial is removed from assertion
  position and recorded as a scoped historical mention in the R2 note. This
  matches worker-017's own falsifier ("the :152 denial is **scoped or deleted**"
  flips B17-R13-01/02 closed). Recorded by worker-066 H1, -035 HF-035-R3-01,
  -018 B1, -044 H1, -058, -008 HF-CD-02, -097 HF3b, -100 (analogous candidate).
* **P2** `implication_ledger.forbidden_transfers[0].reason`: `strictly larger` →
  `strictly smaller (E_C2 subset of E_C0)`. Recorded by worker-066 H2, -075
  LARGER, -047 W047-LFORM01-1, -058 L-FORM-01, -097 HF3, -044 H2, -018 B2,
  -008 HF-CD-01, -034 HF-W034R2-F2B-1.

**Residue P1a:** a detector that does not separate mention from assertion still
fires on the candidate, because the repair note quotes the old denial verbatim
(`… the earlier 'no containment with C2 or C0 is asserted here' was wrong]`).
Any reviewer or instrument that uses a naive cue scan — the same failure mode
class as the CF-16 / class-separation detector family — will still report a
containment denial at line 152. worker-100 already flagged a *different*
candidate (`a110f8e8`) for a related wording deficiency; this one is clean
assertion-wise but not naive-detector-wise.

### What survives the candidate

**Vocabulary (P3/P4/P5).** The schema uses the `VOCAB_ALIASES.json` **canonical**
tokens (`scc_c0_future_inextendibility`, `residual_comeager`) while F0
`field_vocabulary.allowed` lists their **aliases**
(`strong_cosmic_censorship_C0`, `provisional_baire_residual`). Measured both ways:
literal membership fails (worker-075 `HF-075-F2b-VOCAB`, worker-090 `W090-VOCAB-01`);
alias-aware membership passes under the FROZEN-pinned registry whose policy is
"canonical token first; accepted aliases are equivalent for consistency checks
only and must never appear in a new canonical artifact" (sha `46cd9f1eb534`).
F1's conclusion token passes literal membership, its `genericity.kind` does not —
control C5 shows the test discriminates. F2a/F2b also declare no
`vocabulary_aliases_ref` while F1 does (worker-090 `W090-VOCAB-04`).

This reproduces, at the rev13 pins, worker-017's independent
`vocab_source_adjudication` (rev12 pins, same F0/registry/rule_spec bytes):
the governing chain is `rule_spec` R11/R07 + registry canonical keys, the
schemas are conformant on that chain, F0's allowed lists are the inconsistent
source, and only a controller single-sourcing ruling (its **D-A**) clears the
literal-membership hard failures without moving any frozen hash. **The two-edit
repair does not touch this axis.**

**Evidence / freeze pipeline (P6–P8).** No schema edit can clear these:

* P6 — `run_acceptance.py:62` preflight compares the rebased corpus base
  `1bb78ce9b357` against the live C0 `b2ab6acb2bbe` and exits 3; the corpus must
  be regenerated and re-pinned (worker-069 `HF-069RC-1/B4`, worker-062
  `HF-W062-REV13`, worker-081 stale-corpus materiality). Replacing the C0 text
  with the candidate does not move the corpus base.
* P7 — `taxonomy_consistency.json` (FROZEN-pinned `9e335e9b`) has zero
  digest keys and zero 64-hex values: it names the two trees but pins neither.
  The schema-side `f0_binding.consistency_evidence_sha256` *does* equal measured
  at rev13 (the R4 repair), so only the self-verification half remains
  (worker-069 `HF-069RC-2/B2`, worker-044 A2, worker-038 R2LT-F1).
* P8 — `schemas/af_scc_c0_vacuum.yaml.sha256` still pins rev11 `1bb78ce9` and is
  absent from the FROZEN rev29 file list (worker-015 F-015-05, worker-054).

### Supersessions recorded at this instant

* **P9** — worker-095 `HF-05-01` ("3/5 held paths have a manifest pin no artifact
  event carries") no longer holds: all four FROZEN rev29 pins
  (F1/F2a/F2b/F0) are each declared by at least one `artifact` event whose
  `sha256` field equals the pin. Raw text mentions were counted separately and
  are not treated as declarations.
* P10 confirms the candidate parses with no duplicate mapping keys.

## Consequence (for the owner; not a ruling)

Landing candidate `84b5d3fa` removes F2b's schema-content blockers. F2b reaching
**≥2 accepts** still depends on (i) the vocabulary disposition (a controller /
audit-lead D-A-style single-sourcing ruling, or an F0 re-freeze that voids
current hashes — worker-017's D-B/D-C trade-offs) and (ii) the evidence-pipeline
repairs P6–P8. A reviewer using a naive containment cue will additionally need
P1a dispositioned as a mention, not an assertion.

## Controls (8/8)

C1 live fires P1b+P2 · C2 candidate fires P1a but clears P1b+P2 · C3 asserted
re-insertion re-fires P1b · C4 inverted-premise re-insertion re-fires P2 ·
C5 membership test discriminates F1 vs F2a/F2b · C6 both patch pairs unique in
live bytes · C7 assertion-aware stripping non-vacuous on live · C8 all pins
byte-identical at exit.

## Falsifier

Re-run `check_repair_readiness.py` at the same pins. Falsified if: (a) the
reconstructed candidate does not hash to
`84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`;
(b) P1b or P2 fires on the candidate, or a mutation control stops
discriminating; (c) any predicate recorded `cleared_by_candidate=true` fires on
the candidate at re-run; (d) the vocabulary status is shown to be
literal-membership-binding by a governing text, or `VOCAB_ALIASES.json` shown
non-authoritative; (e) `run_acceptance.py` passes with `base_sha256 ==` live C0,
or `taxonomy_consistency.json` is regenerated carrying both compared-tree
digests, or the C0 sidecar is refreshed, or an artifact event declaring each
FROZEN rev29 schema pin is absent; or (f) any pinned input hash moves. Event-stream
growth alone is not a falsification: it changes the recorded snapshot hash and
therefore the run digest, but the P9 census is re-measured from the new snapshot.

## Non-claims / limits

* Not a full-schema F2b verdict, not a gate verdict, not a node status, not a
  theorem, not a physics claim. `counts_as_full_schema_verdict = false`.
* Only `84b5d3fa` is tested. worker-022's candidate `a110f8e8` (different
  wording, worker-100's `HF-W100-02`) is out of scope.
* The six `P6`–`P8` pipeline rows are measured from the artifacts' own declared
  fields; the tools were not re-executed end-to-end in this task (my
  `W069-LIFE05-REC12-REPAIR-COVERAGE-01` already sandbox-replayed the acceptance
  pipeline and reached the same P6/P7 findings).

## Files

| file | content |
|---|---|
| `check_repair_readiness.py` | independent checker (stdlib + PyYAML) |
| `report.json` | full machine verdict, run_digest `8476a8fa248ab34e…` |
| `raw/predicates.json` | predicate table |
| `raw/controls.json` | 8 controls |
| `raw/pins_before.json` | measured pins |
| `raw/af_scc_c0_vacuum.repair-candidate.yaml` | reconstructed candidate `84b5d3fa` |
| `raw/events.snapshot.jsonl` | accepted-stream snapshot used by P9 (`561c90a7fee6727a…`) |
| `CHECKPOINT.json` | bounded-lifecycle checkpoint |
| `SHA256SUMS` | artifact hashes |
