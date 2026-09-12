# W037-REV12-FINDING-STATUS-01 — open hard findings re-measured at FROZEN rev28

**Worker:** worker-037 · **Gate:** G-FORM (evidence only) · **Nodes:** F1, F2a, F2b · **F0** companion
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Created:** 2026-09-12T00:49:20+08:00 · **Hours:** 0.5 · **Writes:** read-only on every canonical path

## Why this task

No inbox card exists for worker-037, and all live `audit-r2-*` blind-review slots at the current pins are
already dispatched to other workers (F1→071/085, F2a→046/091, F2b→015/035, F0→041/052, N0→012, A0→089).
Worker-037's standing lane is freeze/finding-status verification. This run re-measures the hard findings
that were originally bound to **superseded** revisions and adjudicates each one at the current pins, so the
lead's B/N triage does not have to carry stale findings into the gate round.

## Pins measured (sha256, T0 == T1, no drift)

| path | sha256 (first 12) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `55d0a1ea9bda` |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d9` |

48 files measured (all 44 `FROZEN.files` entries plus extras); **0 hash mismatches, 0 byte mismatches,
0 missing, T0 == T1**. F0 canonical/supplement remains the registered REC-3 **companion** pair (distinct
bytes, supplement pinned in `FROZEN.files`).

## Finding status

| finding | severity | status at rev28 | blocks G-FORM |
|---|---|---|---|
| **W037-F1** requested review pins superseded | critical | **resolved** — all 8 live `audit-r2` cards name pins that resolve to the measured bytes; each of F0/F1/F2a/F2b is covered by 2 cards | no |
| **W037-F5a** `(s,delta)` bound over a disjunctive D0 | major | **resolved (well-typedness)** — D0 is now a *tagged disjoint union*; the pair is scoped to `r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1)`; the smooth branch is a tag, the index is closed over D0, and the old disjunctive-pair pattern no longer matches | no |
| **W037-F5b** data domain is not a single branch | major | **live, interpretive** — the domain is still a two-branch tagged union. Decidable per datum, identical across F1/F2a/F2b. The literal card wording ("one decidable data class") is met; the strong reading ("one `(s,delta,norm)` triple") is not. **Lead B/N disposition requested** | conditional |
| **HF090-01** `class_contract_pointer` fragment unresolved | major | **resolved** — all three pointers resolve in the canonical taxonomy (`#classes.<CLASS>`), supplement pointer is a separate field | no |
| **HF090-02** duplicate / future-dated `revised_at` | major | **resolved** — exactly 1 top-level `revised_at` per schema (line 8), stamped `00:31:41`, not after mtime; no future timestamps; `FROZEN.frozen_at` 00:35:08 not future | no |
| **HF090-03** `AF_{I+}` used but undefined | major | **resolved** — F1 defines `i_plus.predicate_abbreviation` (line 193) covering the `statement_formal` use (line 244); F2a/F2b contain only the metalinguistic rev12 history note (CF-16 pattern) | no |

### The one open item, stated precisely

`quantifiers.domains.D0.definition` is identical (whitespace-normalised) in all three schemas:
`r = smooth (the smooth-with-decay default) or r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1)`,
"a tagged disjoint union", "the index r ranges over exactly D0". `data_class.regularity_class` carries
the same `default` / `s` / `delta` in all three; the only divergence is an F1-only gloss
(`(weighted Sobolev)`) in the `spaces` string, already classified gloss-only by worker-090 F-11 and now
reproduced here.

So: the rev12 **well-typedness defect is repaired**; what remains is a *criterion-reading* question, not a
machine defect. If the lead reads "one decidable data class" as *one tagged domain, decidable per datum,
identical across the three schemas*, W037-F5b is non-blocking. If the lead reads it as *exactly one branch*,
W037-F5b is blocking and the repair is a scope change, not a typing fix. The registered freeze decision
(`schemas/af_scc_regularities.yaml` rev11 note: smooth default + registered Sobolev variant) supports the
first reading but does not by itself discharge the second.

## Controls

`SELFTEST-CONTROLS-DISCRIMINATE` passes: the union-tag check flips when `tagged disjoint union` is mutated,
the AF_{I+} check flips when the abbreviation is removed, the revised_at check flips on an injected duplicate
top-level key, and the pointer check flips on a nonexistent fragment. The script is read-only, hashes at T0
and T1, and exits non-zero only on checker failure.

## Not claimed

Not a gate verdict; not a node completion; not one of the two required independent accepts; no authority to
edit canonical artifacts. Worker events cannot set `status`, `validation_status` or a gate verdict.

## Re-run / falsifier

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-037/rev12_finding_status/measure_findings.py
```

Falsified if any `ok=true` check flips to false at the same five canonical hashes, if any `audit-r2` card pin
resolves to no measured file, if a top-level `revised_at` count differs from 1, or if T0 != T1. Any canonical
byte change **voids** the run rather than falsifying it.
