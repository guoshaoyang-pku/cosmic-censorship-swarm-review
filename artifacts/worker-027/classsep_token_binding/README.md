# W027-CLASSSEP-ARITY-01 — class_separation three-group token blind spot

**Worker:** `worker-027` (instance `worker-027-20260912T001656-968807`, relaunch of `worker-027-20260912T001230-897883`)
**Node:** `A1` (audit) · **Gate:** `G-AUDIT` (class-binding calibration evidence; `G-CLASSBIND` was not adopted as a separate gate and is folded into `G-AUDIT`)
**Classes:** `AF-WCC-VAC-GEN`; `AF-SCC-C2-VAC-GEN`; `AF-SCC-C0-VAC-GEN`; `AF-WCC-SCALAR-SPH`
**Snapshot:** 2026-09-12T00:20+08:00, checker `research_map/class_separation.py` sha256 `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920`
**Authority:** worker evidence only — no gate verdict, no `done`/`passed` transition, and **no repository source file was modified**. The proposed patch was evaluated by in-process monkeypatch.

## Finding W027-F1 (CONFIRMED)

`class_separation._class_tokens` (line 67) is

```python
return re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())
```

which matches only `AF-` tokens with **exactly four hyphen groups**. Two of the four frozen
class ids — `AF-WCC-VAC-GEN` and `AF-WCC-SCALAR-SPH` — have **three** groups and are not
matched at all. Consequently `findings_for_text`'s unknown-token rule
(`CLASSSEP-SOFT: unknown class token …`) is blind to any unknown three-group `AF-` token in
*artifact text*, e.g. `AF-WCC-VAC-REG` or `AF-SCC-REG-GEN`.

Measured facts:

| probe | hyphen groups | `_class_tokens` (unpatched) | `findings_for_text` (unpatched) |
|---|---|---|---|
| `AF-WCC-VAC-GEN` (frozen) | 3 | — | — |
| `AF-WCC-SCALAR-SPH` (frozen) | 3 | — | — |
| `AF-SCC-C2-VAC-GEN` (frozen) | 4 | matched | — (known) |
| `AF-SCC-C0-VAC-GEN` (frozen) | 4 | matched | — (known) |
| `AF-WCC-VAC-REG` (unknown) | 3 | — | **nothing** ← blind spot |
| `AF-SCC-REG-GEN` (unknown) | 3 | — | **nothing** ← blind spot |
| `AF-SCC-REG-VAC-GEN` (unknown) | 4 | matched | `CLASSSEP-SOFT: unknown class token` |
| `AF-WCC-VAC-BH-FORM` (unknown) | 4 | matched | `CLASSSEP-SOFT: unknown class token` |

## Scope and impact (deliberately not inflated)

* The blind spot is in the **soft** channel only. Map-level declarations go through
  `_scan_class_ids`, a set-membership test that is arity-independent; a node with
  `class_id: AF-WCC-VAC-REG` **is** detected (measurement C: `detected=True`).
  `audit_evidence.py` routes `CLASSSEP-SOFT:` items to its soft list.
* What is left unmonitored: an unknown three-group `AF-` token introduced inside an
  artifact *body* (a schema line such as `regularity: AF-WCC-VAC-REG`, a note, a README) is
  invisible to the class-separation detector.
* The standing gate evidence is out of distribution for this input class: the worker-07
  27-fixture corpus contains 22 occurrences of frozen three-group tokens and 2 occurrences
  of unknown **four**-group tokens, but **zero** unknown three-group tokens. Its verdict
  (`17/17` leaks, `10/10` controls, FP 0, FN 0) therefore does not cover it.
* Secondary fidelity issue: for tokens longer than four groups the old regex matches only
  the first four groups, so a finding would name a truncated token. No scanned artifact in
  this snapshot exercises that case (measurement H: 0 identity deltas).

## Repair verified in-process (proposed, not applied)

`proposed_patch.diff` changes the extractor to:

```python
return re.findall(r"AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+", text.upper())
```

Measured with the patch monkeypatched in (repository bytes unchanged):

| corpus | unpatched | patched |
|---|---|---|
| worker-07 standing 27-fixture | `17/17` leaks, `10/10` controls, FP 0, FN 0 → PASS | `17/17`, `10/10`, FP 0, FN 0 → PASS |
| worker-027 OOD (`ood_corpus/`, 1 leak + 1 control) | tp 0, **fn 1**, tn 1 → **DEFECTIVE** | tp 1, fn 0, tn 1 → **PASS** |
| repository artifacts (11 scanned) | — | 0 newly flagged, 0 identity deltas |

The OOD fixture `X01` is a node whose artifact body declares `regularity: AF-WCC-VAC-REG`;
it is missed unpatched and caught patched. `X02` is the control (`AF-WCC-VAC-GEN` in an
artifact body) and stays clean in both. The OOD corpus is **not** merged into the frozen
worker-07 corpus; integration is an audit-lead decision.

## Falsifier

Re-run at the pinned checker sha256. The finding is **FALSIFIED** if (a) `_class_tokens`
matches every frozen id listed as unmatched; or (b) `findings_for_text` emits no
`CLASSSEP-SOFT` for any unknown three-group probe; or (c) the standing corpus contains at
least one unknown three-group `AF-` token (scope covered); or (d) the official runner does
not read `17/17` leaks, `10/10` controls, FP 0, FN 0 at the pinned corpus sha256; or (e) the
patched extractor changes any standing-corpus fixture classification, or flags a repository
artifact the unpatched extractor did not flag. Any edit to `class_separation.py` voids the
measurement (the sha256 is pinned in the report).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-027/classsep_token_binding/verify_token_binding.py
```

Artifacts in this directory:

| path | role |
|---|---|
| `verify_token_binding.py` | deterministic measurement script (stdlib only, writes only the report) |
| `token_binding_report.json` | machine-readable report: inputs+hashes, measurements A–H, finding, falsifier |
| `run_stdout.txt` | captured stdout of the run |
| `proposed_patch.diff` | exact one-line patch, dry-run-verified to apply with `patch -p1` |
| `ood_corpus/` | proposed OOD regression corpus (results.json + 2 fixtures + 2 artifact bodies) |
