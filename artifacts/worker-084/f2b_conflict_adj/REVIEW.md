# W084-F2B-CONFLICT-ADJ-01 — review note

Worker: `worker-084` · node: F2b · class: `AF-SCC-C0-VAC-GEN` · gate routing: G-FORM
Canonical subject: `schemas/af_scc_c0_vacuum.yaml` sha256 `55d0a1ea9bda…` (revision 12, revised_at
`2026-09-12T00:31:41+08:00`, FROZEN rev 28 `2f358f6722d9`).
Authority: worker evidence only — no node status, no `validation_status`, no gate verdict.

## What was asked

One bounded class-bound question: **two independent verdicts exist at the same pinned F2b hash and
disagree — `worker-098` ACCEPT 4.5 (`reviews/F2b-repair-verify-worker-098.json`) and `worker-060`
REVISE with HF-060-F2B-1 (hard, inverted containment premise) plus HF-060-F2B-2 (minor, stale
consistency pin). Which reading do the bytes support, and does either finding meet the A0
hard-failure taxonomy?**

## Confirmed facts (deterministic; `report.json` → `facts`)

1. **The inverted premise is real, at line 245.**
   `implication_ledger.forbidden_transfers[0].reason` reads *“C2 is a strictly larger extension
   class, so C2-inextendibility is strictly weaker”*. The same file, 7 lines earlier, states
   `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`; the F2a sibling states
   `E_C2 subset of … E_C0` and justifies the parallel forbidden transfer with *“the converse
   containment is false”*; A0's own `implication_note` says *“SCC-C0 implies SCC-C2; the converse
   does not hold”*; and `c0_specifics.conclusion_relation_to_sibling` says the same. **Four
   independent statements contradict the one premise.**
2. **Model theory, not prose.** Exhaustive enumeration over a 2-element universe (9
   containment-respecting configurations): `E_C2 strictly larger than E_C0` holds in **0** models;
   `I_C0 ⟹ I_C2` fails in **0**; the strictness witness `I_C2 ∧ ¬I_C0` exists in **3**. So the
   *conclusion* “C2-inextendibility is strictly weaker” is correct and only the premise is inverted.
3. **A second, previously unflagged defect: the published sidecar is stale.**
   `schemas/af_scc_c0_vacuum.yaml.sha256` (mtime `00:19:14`) still declares rev11 `1bb78ce9b357`
   while the canonical file measures rev12 `55d0a1ea9bda`. Any consumer running `sha256sum -c` on
   the published sidecar gets a false mismatch. F1/F2a carry no sidecar, so this is F2b-specific.
   *Neither worker-060 (CL7 checks canonical/authoring/FROZEN only) nor worker-098 checked it.*
4. **Consistency declaration stale (reproduces worker-060 HF-060-F2B-2).** Declared
   `675a99d0d25b` vs measured `9e335e9ba1bf`; FROZEN rev 28 pins the measured value. The named file
   is regenerated unconditionally by `check_taxonomy_consistency.py`, so the pin is single-instant.

## Why the two verdicts are not actually in contradiction

`worker-098`'s serialized review contains **none** of `implication_ledger`, `forbidden_transfers`,
`extension_class_containment`, `containment`, `sidecar`, `consistency_evidence`. Its accept covers
the B1/B2/B3 repair, strict parsing, pointer resolution, class-separation and gate reproduction.
`worker-060` covers the closure surface and found facts 1 and 4 but not 3. The accept is
**incomplete**, not refuted. The two can be reconciled by re-running one review at the union scope.

## The instrument gap (the finding that outlives this conflict)

The canonical binding gate `check_class_schema.py` is run on the pinned bytes and **exits 0 /
`pass`** despite fact 1. Its own docstring declares it does not decide mathematical correctness
(“no check that the mathematics in a definition is correct, only that it is present”), and its
`EXEMPT_KEY` regex contains `forbidden_transfers`. A0's enumerated `HF-01…HF-14` taxonomy has no
binary detector that fact 1 or fact 3 matches (detector scan in `facts.C4.3`). So a real
correctness defect on the transfer surface and a stale published hash record are invisible to
*both* instruments. **Whether G-FORM counts them is the audit lead's call; this note only measures
that the current instruments cannot.**

## Adjudication

| id | subject | severity | enumerated A0 HF | blocking recommendation |
|---|---|---|---|---|
| W084-ADJ-1 | inverted premise, line 245 | major | no | yes — one token: `strictly larger` → `strictly smaller` |
| W084-ADJ-2 | stale sidecar hash | major | no | yes — regenerate sidecar from measured bytes |
| W084-ADJ-3 | consistency pin stale at pin instant | minor | no | no — refresh at pin or freeze a copy |

Worker verdict **revise (3.0)**. Class semantics themselves are clean at this hash: identity,
C0 regularity token, SCC conclusion family, sibling disjointness, anti-scope, F0/class-contract
binding (pointer now resolves in the canonical F0), revision stamps (no future-dating, no duplicate
keys) and the canonical class-separation regression (PASS) all hold — 16/18 conformance checks pass.

## Checks

18 conformance checks + 11 adjudication facts + 1 gate run, no drift during the window. FAILs are
`C5.1_no_stale_published_sidecar_hash` (hard) and `C5.2_consistency_declaration_matches_measured_at_pin`
(major). The instrument deliberately classifies by *enumerated A0 detector* rather than by the word
“hard”, because that is the classification question the controller actually has to decide.

## Limitations

- This is not a mathematical verdict on cosmic censorship and accepts/rejects no revision content
  beyond the three named fields.
- The consistency pin is single-instant by construction; its measured value moves with the
  generator, so only the *relationship* declared-vs-measured-at-pin is claimed.
- `det_hits` is a keyword scan over one reason string, not a semantic evaluation of the whole
  schema; it establishes non-membership in the enumerated detectors, not absence of every defect.
- Worker-084 authored no part of F2b, F2a, F0, A0, the gate, or either verdict under adjudication.

## Falsifier (short form)

Re-run `verify_f2b_conflict_adj.py` at the same pins. Falsified if the reason no longer inverts the
containment, the sidecar equals the canonical hash, and the declared consistency hash equals the
measured file (repairs landed); if any fact re-runs false; if a containment-respecting model makes
E_C2 strictly larger than E_C0 or has C0-inextendibility without C2-inextendibility; or if
worker-098's review is shown to cover the fields in §“Why the two verdicts are not actually in
contradiction”. Hash drift voids the verdict, it does not falsify the finding.
