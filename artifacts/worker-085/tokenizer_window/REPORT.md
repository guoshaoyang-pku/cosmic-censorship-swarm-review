# W085-TOKENIZER-WINDOW-01 — class-separation tokenizer window

**Worker:** `worker-085` · **Node:** `F0` · **Gate:** `G-F0` · **Class:** `AF-WCC-VAC-GEN` (frozen four) · **Generated:** 2026-09-12T00:22:49+08:00

**Verdict:** `MEASURED LATENT DEFECT` · **Checker:** `research_map/class_separation.py` `c266dbceca87` lines 66-67


## Measured window

`_class_tokens` accepts exactly **5 hyphen-separated segments** (`AF-XXXX-XXXX-XXXX-XXXX`). The four frozen ids span 4-5 segments, so the tokenizer sensitivity for frozen ids is **2/4**: AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN are invisible to it.


## Probe results (probe corpus on disk)

| probe | text | canonical tokens | canonical SOFT | expected SOFT |
|---|---|---|---|---|
| `P01_frozen_wcc_vac_gen.txt` | `class_id: AF-WCC-VAC-GEN` | `[]` | no | no |
| `P02_frozen_wcc_scalar_sph.txt` | `class_id: AF-WCC-SCALAR-SPH` | `[]` | no | no |
| `P03_frozen_scc_c2.txt` | `class_id: AF-SCC-C2-VAC-GEN` | `['AF-SCC-C2-VAC-GEN']` | no | no |
| `P04_frozen_scc_c0.txt` | `class_id: AF-SCC-C0-VAC-GEN` | `['AF-SCC-C0-VAC-GEN']` | no | no |
| `P05_unknown_wcc_4seg.txt` | `class_id: AF-WCC-VAC-BH` | `[]` | no | yes |
| `P06_unknown_wcc_3seg.txt` | `family: AF-WCC-VAC` | `[]` | no | no |
| `P07_unknown_wcc_5seg.txt` | `class_id: AF-WCC-VAC-BH-FORM` | `['AF-WCC-VAC-BH-FORM']` | yes | yes |
| `P08_unknown_scc_5seg.txt` | `class_id: AF-SCC-C9-VAC-GEN` | `['AF-SCC-C9-VAC-GEN']` | yes | yes |
| `P09_unknown_scc_3seg.txt` | `assessment: AF-SCC-C0` | `[]` | no | no |
| `P10_six_seg_frozen_prefix.txt` | `class_id: AF-SCC-C2-VAC-GEN-EXTRA` | `['AF-SCC-C2-VAC-GEN']` | no | yes |
| `P11_six_seg_unknown_prefix.txt` | `class_id: AF-WCC-VAC-BH-FORM-X` | `['AF-WCC-VAC-BH-FORM']` | yes | yes |
| `P12_softflag_token_5seg.txt` | `class_id: AF-WCC-VAC-GEN-SET` | `['AF-WCC-VAC-GEN-SET']` | yes | yes |
| `P13_softflag_token_6seg.txt` | `class_id: AF-SCC-C0-CH-VAC-GEN` | `['AF-SCC-C0-CH-VAC']` | yes | yes |

## Controls

- hard `class_id`/`class_ids` rule still flags the 4-segment unknown token: `True` (severity bound);
- standing worker-07 regression at this checker: `PASS` 17/17 leaks, 10/10 controls — it contains no fixture with a 4-segment unknown token or a >=6-segment token: `True`;
- `proposed/class_separation.py` carries the same defect: `True`;
- fixed regex is behavior-preserving on the pinned canonical surfaces: `True`.


## Falsifiers

- F1 window measurement: if _class_tokens matches any 4-segment probe token or fails to match any 5-segment probe token, the window claim is falsified.
- F2 lower bound: if findings_for_text emits 'CLASSSEP-SOFT: unknown class token' for P05/P06/P09, the miss claim is falsified.
- F3 frozen-id sensitivity: if all four frozen ids appear in _class_tokens output, the sensitivity claim is falsified.
- F4 severity bound: if the hard class_id/class_ids rule misses AF-WCC-VAC-BH in a class_id field, the 'hard rule unaffected' control fails.
- F5 corpus invisibility: if any worker-07 fixture contains a 4-segment unknown token or a >=6-segment token, the regression-invisibility claim is falsified.
- F6 moving target: if research_map/class_separation.py sha256 differs from c266dbceca87, re-run and re-pin; a stale hash voids this snapshot, not the defect.

## Proposed fix (NOT applied)

```diff
--- a/research_map/class_separation.py
+++ b/research_map/class_separation.py
@@ lines 66-67 @@
-    return re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())
+    return re.findall(r"AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+(?![A-Z0-9-])", text.upper())
```

Apply only through the checker owner (CF-4: checkers flag, never author). Add two regression fixtures: an unknown 4-segment `AF-WCC-...` token in artifact content, and a >=6-segment token whose 5-segment prefix is a frozen id.

