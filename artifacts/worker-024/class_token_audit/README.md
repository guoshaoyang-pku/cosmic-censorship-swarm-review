# W024 — independent class-token audit (canonical four + detector probe)

**Actor:** `worker-024` · **task_id:** `W024-CLASS-TOKEN-AUDIT-01` · **node:** `A1` · **gate context:** `G-AUDIT` / `G-FORM` / `G-F0`
**Authority:** worker event. This is evidence and a falsifiable claim only. It sets **no** gate verdict, **no**
`validation_status=passed`, and **no** node `status=done`.

## 1. What was done

One bounded class-bound task, no writes to shared state (the four canonical artifacts were read, copied into
`snapshots/`, and re-hashed; the project's `audit_evidence.py` was imported, never run with its `--write-hashes` CLI
path). Two independent things were measured at one pinned instant:

1. **Canonical token audit.** Every class-shaped token in the four canonical artifacts, extracted with an
   independent maximal-match scanner (`AF-` followed by greedy hyphen groups, so nothing is silently truncated),
   classified against the frozen `class_ids` that `research_map/formulation_taxonomy.yaml` declares *itself*
   (read at the same instant — not a hardcoded list). The same bytes were then run through the project checker
   `research_map/class_separation.py:findings_for_text`, and the two unknown-token sets were compared.
2. **Detector representational probe.** A labelled six-token probe corpus that asks whether the checker's
   unknown-token detector can even *represent* the token shapes it is asked to police.

Reproduce: `python3 artifacts/worker-024/class_token_audit/independent_token_scan.py` (reads only; rewrites
`report.json` and `snapshots/`). Exit 1 means this report's verdict is `DEFECTIVE_TOKEN_REPRESENTATION` or a
canonical file moved mid-audit.

## 2. Pinned inputs (any later edit voids the corresponding line)

| node | canonical path | sha256 (read) | bytes | mtime | stable in window | snapshot |
|---|---|---|---|---|---|---|
| F0 | `research_map/formulation_taxonomy.yaml` | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` | 35145 | 00:18:26 | yes | `snapshots/formulation_taxonomy.276009f4.yaml` |
| F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894…` | 33642 | 00:18:37 | yes | `snapshots/af_wcc_vacuum.9a8bd4c9.yaml` |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92…` | 28268 | 00:18:37 | yes | `snapshots/af_scc_c2_vacuum.b6123750.yaml` |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229…` | 33276 | 00:18:37 | yes | `snapshots/af_scc_c0_vacuum.1bb78ce9.yaml` |

Full 64-hex hashes are in `report.json` (`canonical_files[*].read.sha256`); every snapshot copy was byte-verified
against the bytes that were read (`byte_identical_to_read: true`). Tool hashes at read time (in `report.json`):
`research_map/class_separation.py` `c266dbceca87…`, `research_map/audit_evidence.py` `bebec0843f10…`,
`artifacts/formulation/tools/check_class_schema.py` `000e09e46b2f…`,
`artifacts/formulation/tools/verify_frozen.py` `0a65b657e498…`, `artifacts/formulation/FROZEN.json` `af24e9c39606…`.
No tool hash drifted during the audit window.

## 3. Finding A (primary, durable) — the unknown-token detector has a blind spot and truncates

`research_map/class_separation.py` lines 66–67:
`_class_tokens = re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())`
(`findings_for_text`, lines 211–213, soft-flags tokens not in `KNOWN_CLASSES`).

That pattern matches an `AF-` token with **exactly four** hyphen groups after `AF` (five dash-components). The
frozen class ids are not uniform in that dimension: `AF-SCC-C2-VAC-GEN` and `AF-SCC-C0-VAC-GEN` have four groups
(they match by luck), while `AF-WCC-VAC-GEN` and `AF-WCC-SCALAR-SPH` have three (they can never match). Probe
results at the pinned tool hash:

| probe | token | canonical? | expected | checker regex hits | outcome |
|---|---|---|---|---|---|
| P1 | `AF-WCC-VAC-GEN` | yes | unflagged | `[]` | unflagged (by non-match, not by recognition) |
| P2 | `AF-WCC-VAC-NONGEN` | no | **flagged** | `[]` | **MISSED — 4-component unknown token is invisible** |
| P3 | `AF-SCC-C0-CH-VAC-GEN` | no | flagged whole | `['AF-SCC-C0-CH-VAC']` | **TRUNCATED to a 5-component prefix** |
| P4 | `AF-AAA-BBB-CCC-DDD-EEE` | no | flagged whole | `['AF-AAA-BBB-CCC-DDD']` | **TRUNCATED** |
| P5 | `AF-WCC-VAC-GEN-SET` | no | flagged | `['AF-WCC-VAC-GEN-SET']` | flagged correctly |
| P6 | `af-scc-c2-vac-gen` | yes | unflagged | `['AF-SCC-C2-VAC-GEN']` | unflagged (case-folded) |

Consequences that a downstream gate would feel: (i) any unknown WCC-shaped class id (`AF-WCC-…-…`, the shape of the
frozen WCC classes) is not observable by this detector; (ii) a longer unknown token is reported under a *different
string than the one on disk*, so a review that cites the reported token cites a token that does not exist in the
artifact. The checker's own regression corpus still reads `PASS` (`tp=17, fn=0, tn=10, fp=0`, size 27) — the corpus
does not exercise 4-component or ≥6-component unknown tokens. Minimal fix direction (not applied by this worker;
the module is owned by the formulation/audit groups): replace the pattern with a maximal match, e.g.
`AF-[A-Z0-9]+(?:-[A-Z0-9]+)*`, plus additive fixtures for P2/P3/P4.

## 4. Finding B (snapshot) — canonical state at the pinned revision

- **F1, F2a, F2b: clean under both scanners.** Zero unknown class-shaped tokens (independent maximal scan and the
  project checker agree, `unknown_set_agreement: true`), and `check_class_schema.py --json` exits 0 with
  `verdict: pass`, `failed_rules: []` for all three. The variant tokens that were live at the 00:16 revision
  (`AF-WCC-VAC-GEN-SET`, `AF-SCC-C0-CH-VAC`) are **no longer present** on disk at this revision.
- **F0: one divergence.** The independent scan finds one non-frozen class-shaped token, `AF-SCC`, once, at line 37:
  `"two AF-SCC classes) and must be replaced, not inherited silently."` It is a prose family reference, not a class
  id — the frozen `class_ids` list has exactly the four canonical ids. The project checker reports **nothing** for
  it (Finding A's regex cannot match a 2-component token). Whether a bare family label is acceptable in F0 prose is
  a reviewer/controller adjudication, not a worker call; what is machine-checkable is the disagreement between the
  two scanners on the same bytes.
- **Project green-path cross-checks at the same instant:** `verify_frozen.py` exit 0 (FROZEN revision 25, 40 files,
  0 problems); `audit_evidence.audit()` 1 hard + 1 soft — the hard flag is against `claims[36].statement` in
  `research_map.json` (not a canonical file), the soft flag is the known dual-tree divergence
  `research_map/formulation_taxonomy.yaml (276009f4) != artifacts/formulation/formulation_taxonomy.yaml (c8e979a1)`,
  i.e. the canonical publish policy was not satisfied at the pinned instant.

## 5. Falsifier

- **Finding A is falsified** if, at the pinned `class_separation.py` hash, `findings_for_text('AF-WCC-VAC-NONGEN', …)`
  is non-empty (blind spot false) **or** any ≥6-component probe is reported with its full token string (truncation
  false). Both are one-line reproductions; `report.json.detector_probe` stores the labelled rows.
- **Finding B is void for any file** whose current sha256 differs from the `read.sha256` above; the audit makes no
  claim about later revisions. The `snapshots/` copies remain the exact bytes analysed.
- The `PASS` regression result is *not* a counter-argument to Finding A: it is the evidence that the corpus does not
  cover the shapes P2–P4.

## 6. Secondary observation (not part of the claim)

`artifacts/formulation/FROZEN.json` revision 25 declares `frozen_at = 2026-09-12T00:42:00+08:00` while its file
mtime is 00:19:46 and this audit's wall clock was 00:20:22 — a declared freeze time 22 minutes *after* the file was
written. If `frozen_at` means "freeze deadline / validity end", no issue; if it means "time of freezing", the field
is wrong. Author adjudication needed; not used in any claim above and not a class-binding matter.

## 7. Boundaries

- No gate verdict, no `done`, no `validation_status=passed`, no theorem, no physics claim.
- No shared state was written: no edit to `research_map/**`, `schemas/**`, `reviews/**`, or
  `runtime/state/artifact_hashes.json`.
- Fingerprint of the claim: `research_map/formulation_taxonomy.yaml#276009f4`, `schemas/af_wcc_vacuum.yaml#9a8bd4c9`,
  `schemas/af_scc_c2_vacuum.yaml#b6123750`, `schemas/af_scc_c0_vacuum.yaml#1bb78ce9`,
  `research_map/class_separation.py#c266dbce`.
