# W004 — F1 R03 adjudication and rule repair

- **worker**: worker-004 (bounded execution worker, instance `worker-004-<stamp>`)
- **class binding**: `AF-WCC-VAC-GEN`
- **node / gate routing**: `F1` / `G-FORM`, with calibration evidence routed to `G-AUDIT`
- **task source**: self-selected from the live queue (no inbox card for `worker-004` at
  2026-09-12T00:45+08:00; the 23:19 F1 card was already delivered at 00:27). Complements
  `worker-080`'s R03 lexical probe (`artifacts/worker-080/semct_rebase/`), which classified the
  failure but produced no repaired rule and no end-to-end re-measurement.
- **authority**: worker measurement + repair proposal only. No gate verdict, no node status, no
  `validation_status=passed`, and **no canonical file written**. Owners: auditor =
  `worker-06` / `astra-lead-audit`; canonical schema = `astra-lead-formulation`.

## 1. The defect

At the frozen bytes `schemas/af_wcc_vacuum.yaml#cce9c60146d6` the binding structural stage
(`artifacts/formulation/tools/check_class_schema.py#000e09e46b2f`) passes, but the adopted
semantic stage (`artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a`, baseline **and**
hardened) rejects on R03 alone:

> `binder '(q,t0)' absent from formal sentence`

The formal sentence spells the final quantifier out as `not exists q in I+ and t0 in [0,T) with
gamma([t0,T)) subset J^-(q) intersect M.` while `quantifiers.ordered[5].binder` is the tuple
`"(q,t0)"`. R03's implementation is a literal substring test (`if b not in formal`), so a
conforming schema is rejected by punctuation.

Measured decomposition (report `adjudication`):

| # | kind | binder | literal in formal | identifier components present |
|---:|---|---|---|---|
| 0 | forall | `r` | yes | r |
| 1 | exists | `G_r` | yes | G_r |
| 2 | forall | `(Sigma,h,K)` | yes | Sigma, h, K |
| 3 | exists | `(Mtilde,gtilde,Omega)` | yes | Mtilde, gtilde, Omega |
| 4 | forall | `gamma` | yes | gamma |
| 5 | not_exists | `(q,t0)` | **no** | q, t0 (both present) |

The formal quantifier sequence is `forall, exists, forall, exists, forall, not_exists` — exactly
the ordered kind sequence. **At these bytes the R03 rejection is a literal-token (lexical) false
positive, not a missing quantifier.**

Unpatched stage table (all at the pinned hashes): F1 → structural pass, semantic baseline reject
`[R03]`, semantic hardened reject `[R03]`; C2 → pass/accept/accept; C0 → pass/accept/accept.

## 2. The repair (proposal, artifact-local)

`patched/r03_binder_token_aware.patch` — **one hunk**, source `c79d8ab8440a` → patched
`645eb16a0060` (`patched/spec_conformance_audit.py`). Composite binders are split into identifier
components and each component must occur in `quantifiers.formal` as a whole word; a genuinely
absent component (or an extra component absent from formal) is still reported as R03.

- unified diff: `patched/r03_binder_token_aware.patch#b7457b0151d3`
- patched auditor: `patched/spec_conformance_audit.py#645eb16a0060`
- the auditor's own selftest battery is **identical** before/after: 32 fixtures, baseline 11
  caught / 21 missed, hardened 32 / 0, positive controls 3/3 accept.

## 3. Controls (no weakening)

Rule-level battery (patched rule, baseline and hardened; YAML/raw-text mutants under
`tmp/mutants/`):

| mutant | defect | patched rule | unpatched rule |
|---|---|---|---|
| M-A drop quantifiers | structural | reject R03 | reject R03 |
| M-B unresolved domain | structural | reject R03 | reject R03 |
| M-C drop final not-exists clause | missing q,t0 | **reject R03** | reject R03 |
| M-D rename t0 → t9 in formal | missing t0 | **reject R03** | reject R03 |
| M-E extra binder component `(q,t0,t1)` | t1 absent | **reject R03** | reject R03 |
| M-F empty formal | content absent | reject R03 | reject R03 |
| M-G swap components `(t0,q)` | boundary, not a truth defect | accept (order-insensitive) | reject |

Per-rule before/after vectors: F1 changes only `R03` (18 rules compared); C2/C0 change nothing
(19 rules each), baseline and hardened. Boundary disclosed: the repaired rule is still a lexical
presence check; component **order** inside a composite binder is not enforced (M-G). Binding
*structure* is out of scope for R03 either way.

### End-to-end shadow suite (semantic-contract tests)

Two artifact-local shadow repos, identical in every byte except the auditor; live canonical
schemas pinned as the conforming-canonical controls and the rebased controls from
W004-SEMCT-CONTROL-REBASE-02. Harness-only input is disclosed: the KEY_MANIFEST union allowlist
(272 keys = rev27 ∪ rev28) holds the structural stage fixed, because rev27 alone rejects the live
schemas (R22) and rev28 alone rejects the rebased controls (R22).

| run | auditor | controls | canonical | mutants S/B/H | exit | valid |
|---|---|---|---:|---:|---:|---|
| `unpatched_rebased_live` | `c79d8ab8440a` | 3/3 | **2/3** (F1 rejected R03 by both semantic stages) | 32/11/32 | 3 | **false** |
| `patched_rebased_live` | `645eb16a0060` | 3/3 | **3/3** | 32/11/32 | **0** | **true** |
| `patched_rebased_live_rerun` | `645eb16a0060` | 3/3 | 3/3 | 32/11/32 | 0 | true |
| `patched_stale_live` (negative) | `645eb16a0060` | **0/3** (structural R28) | 3/3 | 32/11/32 | 3 | false |

0 adopted-stage escapes in every run. The stale-control run confirms the repair does not rescue
control staleness (that is a structural R28 issue).

## 4. Recommendation

1. **Adopt the token-aware R03 check** in `artifacts/worker-06/spec_conformance_audit.py`
   (owner `worker-06` / `astra-lead-audit`) and re-run the suite at the pinned bytes.
2. **Do not** edit the frozen F1 formal sentence to satisfy a lexical tool (per CF-4): that would
   bump FROZEN and re-void hash-bound verdicts, and the sentence is mathematically correct.
3. The runner records `blocking_adjudication: []` for a rejected conforming-canonical control;
   extending that list would have routed this failure automatically.
4. The separate KEY_MANIFEST revision instability still needs the owner decision reported in
   `W004-SEMCT-CONTROL-REBASE-02` / `worker-080`.

## 5. Reproduction and falsifiers

```bash
python3 artifacts/worker-004/f1_r03_repair/verify_r03_repair.py   # exit 0 iff all 13 expectations hold; exit 2 on pin drift
```

Artifacts and measured hashes:

| artifact | sha256 |
|---|---|
| `r03_repair_report.json` | `f14484821a74` |
| `verify_r03_repair.py` | `63610f047348` |
| `patched/spec_conformance_audit.py` | `645eb16a0060` |
| `patched/r03_binder_token_aware.patch` | `b7457b0151d3` |
| `runtime/state/w04_checkpoint_f1_r03_repair.json` | see checkpoint log line |

**Falsifiers** (any one voids the corresponding claim): a stage-2 accept at
`F1#cce9c60146d6` with the unpatched auditor; a patched-auditor accept on M-A…M-F; any
rule-verdict change outside `F1/R03`; suite mutant counts ≠ structural 32 / baseline 11 /
hardened 32; a `valid_for_calibration=false` run at the pinned bytes under the patch; or any byte
change to a canonical input (the harness fails closed on input drift). Selftest drift between the
patched and unpatched tool also voids the no-weakening claim.
