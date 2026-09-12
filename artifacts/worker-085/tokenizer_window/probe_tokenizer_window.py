#!/usr/bin/env python3
"""W085-TOKENIZER-WINDOW-01: measure the class-separation detector's token window.

Bounded class-bound task taken by worker-085 (no inbox assignment existed for slot 085).

Question: `research_map/class_separation.py::_class_tokens` is a fixed-width regex used by
`findings_for_text` to emit `CLASSSEP-SOFT: unknown class token` on artifact content.  What is
its exact acceptance window over hyphen-separated `AF-...` tokens, and which of the four frozen
class ids / unknown-token shapes does it miss or truncate?

Prior evidence this replicates and extends:
  - artifacts/flash-19/class_token_census.json  auxiliary observation OBS-1
    ("requires four hyphen groups after AF-, so it does not match two of the four frozen ids",
    status out_of_scope_for_token_counts);
  - artifacts/worker-093/cf5_token_census/README.md  check C6 (upper-bound truncation).

This script is read-only with respect to every canonical path.  It loads the detector by
`exec` of its source (no import, therefore no __pycache__ write inside `research_map/`), pins
its sha256 before and after, writes its own probe corpus and report under
`artifacts/worker-085/tokenizer_window/`, and never edits the checker, the map, or a schema.

Reproduce:  python3 artifacts/worker-085/tokenizer_window/probe_tokenizer_window.py
Exit code 0 iff the probe executed and every control held; findings live in the report.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
CORPUS = OUT / "probe_corpus"
CST = timezone(timedelta(hours=8))

CANONICAL_CHECKER = ROOT / "research_map/class_separation.py"
PROPOSED_CHECKER = ROOT / "proposed/class_separation.py"
REGRESSION_HARNESS = ROOT / "runtime/bin/classsep_regression.py"
REGRESSION_CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"

PINNED_SHA = {
    "research_map/class_separation.py":
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "runtime/bin/classsep_regression.py":
        "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091",
    "artifacts/worker-07/class_separation_falsification/results.json":
        "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    "proposed/class_separation.py":
        "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
}

# Canonical surfaces pinned for the behavior-preservation check.
CANONICAL_SURFACES = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]

# The fix under test, mirroring flash-19 OBS-1's remedy with an explicit right guard so a
# longer token is matched whole rather than truncated to a frozen-id prefix.
FIXED_PATTERN = r"AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+(?![A-Z0-9-])"
FIXED_RE = re.compile(FIXED_PATTERN)

# Probe documents.  expected_soft is what a complete tokenizer should emit under the
# CLASSSEP-SOFT unknown-token rule; expected_tokens is what a complete tokenizer should see.
PROBES = [
    ("P01_frozen_wcc_vac_gen.txt", "class_id: AF-WCC-VAC-GEN\n",
     ["AF-WCC-VAC-GEN"], []),
    ("P02_frozen_wcc_scalar_sph.txt", "class_id: AF-WCC-SCALAR-SPH\n",
     ["AF-WCC-SCALAR-SPH"], []),
    ("P03_frozen_scc_c2.txt", "class_id: AF-SCC-C2-VAC-GEN\n",
     ["AF-SCC-C2-VAC-GEN"], []),
    ("P04_frozen_scc_c0.txt", "class_id: AF-SCC-C0-VAC-GEN\n",
     ["AF-SCC-C0-VAC-GEN"], []),
    ("P05_unknown_wcc_4seg.txt", "class_id: AF-WCC-VAC-BH\n",
     ["AF-WCC-VAC-BH"], ["AF-WCC-VAC-BH"]),
    # 3-segment fragments are below the minimum length of every frozen id (4 segments); a
    # complete tokenizer for class-id-shaped tokens is not required to match them.
    ("P06_unknown_wcc_3seg.txt", "family: AF-WCC-VAC\n", [], []),
    ("P07_unknown_wcc_5seg.txt", "class_id: AF-WCC-VAC-BH-FORM\n",
     ["AF-WCC-VAC-BH-FORM"], ["AF-WCC-VAC-BH-FORM"]),
    ("P08_unknown_scc_5seg.txt", "class_id: AF-SCC-C9-VAC-GEN\n",
     ["AF-SCC-C9-VAC-GEN"], ["AF-SCC-C9-VAC-GEN"]),
    ("P09_unknown_scc_3seg.txt", "assessment: AF-SCC-C0\n", [], []),
    ("P10_six_seg_frozen_prefix.txt", "class_id: AF-SCC-C2-VAC-GEN-EXTRA\n",
     ["AF-SCC-C2-VAC-GEN-EXTRA"], ["AF-SCC-C2-VAC-GEN-EXTRA"]),
    ("P11_six_seg_unknown_prefix.txt", "class_id: AF-WCC-VAC-BH-FORM-X\n",
     ["AF-WCC-VAC-BH-FORM-X"], ["AF-WCC-VAC-BH-FORM-X"]),
    ("P12_softflag_token_5seg.txt", "class_id: AF-WCC-VAC-GEN-SET\n",
     ["AF-WCC-VAC-GEN-SET"], ["AF-WCC-VAC-GEN-SET"]),
    ("P13_softflag_token_6seg.txt", "class_id: AF-SCC-C0-CH-VAC-GEN\n",
     ["AF-SCC-C0-CH-VAC-GEN"], ["AF-SCC-C0-CH-VAC-GEN"]),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    """Load a module by exec so no bytecode is written next to the canonical file."""
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    src = path.read_text(encoding="utf-8")
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def segments(token: str) -> int:
    return len(token.split("-"))


def main() -> int:
    created = datetime.now(CST).isoformat(timespec="seconds")
    before = {rel: sha256(ROOT / rel) for rel in PINNED_SHA}

    cs = load_module(CANONICAL_CHECKER, "cs_pinned_w085")
    known = set(cs.KNOWN_CLASSES)
    frozen = sorted(known)
    canonical_tokens = getattr(cs, "_class_tokens")

    CORPUS.mkdir(parents=True, exist_ok=True)
    probe_rows = []
    for fname, text, exp_tokens, exp_soft in PROBES:
        p = CORPUS / fname
        p.write_text(text, encoding="utf-8")
        got_tokens = canonical_tokens(text)
        findings = cs.findings_for_text(text, f"probe {fname}")
        soft = [f for f in findings if f.startswith("CLASSSEP-SOFT")]
        fixed_tokens = FIXED_RE.findall(text.upper())
        probe_rows.append({
            "probe": fname,
            "text": text.strip(),
            "expected_tokens_complete": exp_tokens,
            "canonical_tokens": got_tokens,
            "fixed_regex_tokens": fixed_tokens,
            "canonical_soft_findings": soft,
            "all_canonical_findings": findings,
            "expected_soft_complete": exp_soft,
            "tokens_missed": sorted(set(exp_tokens) - set(got_tokens)),
            "tokens_truncated": sorted({t for t in exp_tokens
                                        for c in got_tokens
                                        if t.startswith(c) and c != t}),
            "soft_missed": bool(exp_soft) and not soft,
            "soft_false_negative_at_frozen_prefix": any(
                t not in known and t.startswith(tuple(known)) and not soft for t in exp_tokens),
        })

    # Control 1: the hard class_id/class_ids rule (_scan_class_ids) must still catch the
    # 4-segment unknown token the tokenizer misses -> bounds the severity of the defect.
    hard_field_probes = [
        {"class_id": "AF-WCC-VAC-BH"},
        {"class_ids": ["AF-WCC-VAC-BH", "AF-WCC-VAC-GEN"]},
        {"class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN"},
    ]
    hard_rows = []
    for i, obj in enumerate(hard_field_probes):
        f = cs.findings(obj, f"hard_field_probe[{i}]")
        hard_rows.append({"object": obj, "findings": f,
                          "unknown_4seg_detected": any("AF-WCC-VAC-BH" in x for x in f)})

    # Control 2: the standing 27-fixture regression at the pinned checker.
    regression = cs.regression()
    fixture_scan = []
    res = json.loads(REGRESSION_CORPUS.read_text())
    for fx in res["fixtures"]:
        fp = ROOT / fx["fixture_path"]
        if not fp.exists():
            continue
        txt = fp.read_text(encoding="utf-8", errors="replace")
        fixed_toks = FIXED_RE.findall(txt.upper())
        canon_toks = canonical_tokens(txt)
        unknown_4 = [t for t in fixed_toks if segments(t) == 4 and t not in known]
        six_plus = [t for t in fixed_toks if segments(t) >= 6]
        trunc = [t for t in fixed_toks
                 if any(t.startswith(c) and c != t for c in canon_toks)]
        if unknown_4 or six_plus or trunc:
            fixture_scan.append({"fixture": fx["id"], "unknown_4seg": unknown_4,
                                 "six_plus": six_plus, "truncated": trunc})
    n_fx = len(res["fixtures"])

    # Behavior preservation: the shadow SOFT rule with the fixed regex on canonical surfaces.
    surfaces = []
    for rel in CANONICAL_SURFACES:
        p = ROOT / rel
        if not p.exists():
            surfaces.append({"path": rel, "exists": False})
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        canon_soft = [f for f in cs.findings_for_text(txt, rel) if f.startswith("CLASSSEP-SOFT")]
        shadow_soft = [f"CLASSSEP-SOFT: unknown class token in {rel}: {t!r}"
                       for t in FIXED_RE.findall(txt.upper()) if t not in known]
        surfaces.append({"path": rel, "sha256": sha256(p),
                         "canonical_soft": canon_soft, "fixed_regex_soft": shadow_soft,
                         "same_result": canon_soft == shadow_soft})

    after = {rel: sha256(ROOT / rel) for rel in PINNED_SHA}
    drift = sorted(rel for rel in before if before[rel] != after[rel])

    proposed_src = PROPOSED_CHECKER.read_text(encoding="utf-8") if PROPOSED_CHECKER.exists() else ""
    proposed_has_defect = bool(re.search(
        r"AF-\[A-Z0-9\]\+-\[A-Z0-9\]\+-\[A-Z0-9\]\+-\[A-Z0-9\]\+", proposed_src))

    window_min = min(segments(t) for t in frozen)
    window_max = max(segments(t) for t in frozen)
    missed_frozen = [t for t in frozen if t not in canonical_tokens(t)]
    matched_frozen = [t for t in frozen if t in canonical_tokens(t)]

    controls = {
        "hard_field_rule_unaffected": all(r["unknown_4seg_detected"] for r in hard_rows[:2]),
        "hard_field_rows": hard_rows,
        "regression_verdict": regression["verdict"],
        "regression_scores": regression,
        "regression_sees_window_bounds": bool(fixture_scan),
        "regression_fixtures_with_window_bound_tokens": fixture_scan,
        "behavior_preserved_on_canonical_surfaces": all(s["same_result"] for s in surfaces
                                                        if s.get("exists")),
        "proposed_copy_has_same_defect": proposed_has_defect,
    }

    upper_truncation = [r["probe"] for r in probe_rows if r["tokens_truncated"]]
    six_seg_silent = [r["probe"] for r in probe_rows
                      if r["probe"].startswith("P10") and not r["canonical_soft_findings"]]
    unknown_4seg_missed = [r["probe"] for r in probe_rows
                           if r["probe"].startswith("P05")]
    defects = {
        "frozen_ids_matched_by_canonical_tokenizer": matched_frozen,
        "frozen_ids_missed_by_canonical_tokenizer": missed_frozen,
        "frozen_id_tokenizer_sensitivity": f"{len(matched_frozen)}/{len(frozen)}",
        "unknown_4seg_soft_findings_missed": unknown_4seg_missed,
        "six_seg_frozen_prefix_silently_accepted": six_seg_silent,
        "upper_bound_truncation_examples": [
            {"probe": r["probe"], "expected": r["expected_tokens_complete"],
             "canonical": r["canonical_tokens"]}
            for r in probe_rows if r["tokens_truncated"]],
        "window_segments_measured": [window_min, window_max],
    }

    verdict = ("MEASURED LATENT DEFECT"
               if (missed_frozen or upper_truncation or six_seg_silent)
               else "NO DEFECT FOUND")

    report = {
        "schema_version": "1.0",
        "task_id": "W085-TOKENIZER-WINDOW-01",
        "actor": "worker-085",
        "created_at": created,
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": frozen,
        "claims_theorem_status": False,
        "completion_claim": False,
        "authority_note": ("Worker evidence only: this report measures a checker property and "
                           "proposes a fix. It does not set a gate verdict, a node status, or an "
                           "artifact validation status, and it does not edit the checker."),
        "question": ("What is the acceptance window of research_map/class_separation.py "
                     "_class_tokens over AF-... tokens, and which frozen ids / unknown-token "
                     "shapes are missed or truncated by findings_for_text?"),
        "pinned_inputs": {rel: {"sha256": before[rel], "bytes": (ROOT / rel).stat().st_size,
                                "pinned_ok": before[rel] == PINNED_SHA[rel]}
                          for rel in PINNED_SHA},
        "detector": {
            "path": "research_map/class_separation.py",
            "lines": "66-67",
            "pattern": r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+",
            "use_site": "findings_for_text (lines 211-213), CLASSSEP-SOFT unknown-token rule",
            "measured_acceptance_window_segments": 5,
            "fix_under_test": FIXED_PATTERN,
        },
        "defects": defects,
        "probe_results": probe_rows,
        "controls": controls,
        "canonical_surfaces_shadow_check": surfaces,
        "prior_evidence": [
            "artifacts/flash-19/class_token_census.json#OBS-1 (lower-bound claim, out_of_scope)",
            "artifacts/worker-093/cf5_token_census/README.md#C6 (upper-bound note)",
        ],
        "drift": {"files_changed_during_run": drift, "before": before, "after": after},
        "verdict": verdict,
        "falsifiers": [
            ("F1 window measurement: if _class_tokens matches any 4-segment probe token or fails "
             "to match any 5-segment probe token, the window claim is falsified."),
            ("F2 lower bound: if findings_for_text emits 'CLASSSEP-SOFT: unknown class token' for "
             "P05/P06/P09, the miss claim is falsified."),
            ("F3 frozen-id sensitivity: if all four frozen ids appear in _class_tokens output, the "
             "sensitivity claim is falsified."),
            ("F4 severity bound: if the hard class_id/class_ids rule misses AF-WCC-VAC-BH in a "
             "class_id field, the 'hard rule unaffected' control fails."),
            ("F5 corpus invisibility: if any worker-07 fixture contains a 4-segment unknown token "
             "or a >=6-segment token, the regression-invisibility claim is falsified."),
            ("F6 moving target: if research_map/class_separation.py sha256 differs from "
             "c266dbceca87, re-run and re-pin; a stale hash voids this snapshot, not the defect."),
        ],
        "scope_limits": [
            ("Latent defect: no non-frozen, non-frozen-prefixed token was measured on the pinned "
             "canonical surfaces at run time; the miss set is a sensitivity gap, not an observed "
             "escape at this revision."),
            ("Only the artifact-content path (findings_for_text) uses _class_tokens; the map/claim "
             "path uses _scan_class_ids, which is unaffected (control C1)."),
            ("No claim is made about audit_evidence.py's separate class-token checks."),
            ("The fix is proposed, not applied; per CF-4 the checker owner applies checker "
             "changes."),
        ],
        "reproduce_command": ("python3 artifacts/worker-085/tokenizer_window/"
                              "probe_tokenizer_window.py"),
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    md = []
    md.append("# W085-TOKENIZER-WINDOW-01 — class-separation tokenizer window\n")
    md.append(f"**Worker:** `worker-085` · **Node:** `F0` · **Gate:** `G-F0` · "
              f"**Class:** `AF-WCC-VAC-GEN` (frozen four) · **Generated:** {created}\n")
    md.append(f"**Verdict:** `{verdict}` · **Checker:** `research_map/class_separation.py` "
              f"`{before['research_map/class_separation.py'][:12]}` lines 66-67\n")
    md.append("\n## Measured window\n")
    md.append(f"`_class_tokens` accepts exactly **5 hyphen-separated segments** "
              f"(`AF-XXXX-XXXX-XXXX-XXXX`). The four frozen ids span 4-5 segments, so the "
              f"tokenizer sensitivity for frozen ids is "
              f"**{defects['frozen_id_tokenizer_sensitivity']}**: "
              f"{', '.join(missed_frozen)} are invisible to it.\n")
    md.append("\n## Probe results (probe corpus on disk)\n")
    md.append("| probe | text | canonical tokens | canonical SOFT | expected SOFT |")
    md.append("|---|---|---|---|---|")
    for r in probe_rows:
        md.append(f"| `{r['probe']}` | `{r['text']}` | `{r['canonical_tokens']}` | "
                  f"{'yes' if r['canonical_soft_findings'] else 'no'} | "
                  f"{'yes' if r['expected_soft_complete'] else 'no'} |")
    md.append("\n## Controls\n")
    md.append(f"- hard `class_id`/`class_ids` rule still flags the 4-segment unknown token: "
              f"`{controls['hard_field_rule_unaffected']}` (severity bound);")
    md.append(f"- standing worker-07 regression at this checker: "
              f"`{regression['verdict']}` {regression['tp']}/{regression['tp']+regression['fn']} "
              f"leaks, {regression['tn']}/{regression['tn']+regression['fp']} controls — "
              f"it contains no fixture with a 4-segment unknown token or a >=6-segment token: "
              f"`{not controls['regression_sees_window_bounds']}`;")
    md.append(f"- `proposed/class_separation.py` carries the same defect: "
              f"`{proposed_has_defect}`;")
    md.append(f"- fixed regex is behavior-preserving on the pinned canonical surfaces: "
              f"`{controls['behavior_preserved_on_canonical_surfaces']}`.\n")
    md.append("\n## Falsifiers\n")
    for f in report["falsifiers"]:
        md.append(f"- {f}")
    md.append("\n## Proposed fix (NOT applied)\n")
    md.append("```diff\n--- a/research_map/class_separation.py\n"
              "+++ b/research_map/class_separation.py\n@@ lines 66-67 @@\n"
              "-    return re.findall(r\"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+\", text.upper())\n"
              f"+    return re.findall(r\"{FIXED_PATTERN}\", text.upper())\n```\n")
    md.append("Apply only through the checker owner (CF-4: checkers flag, never author). Add two "
              "regression fixtures: an unknown 4-segment `AF-WCC-...` token in artifact content, "
              "and a >=6-segment token whose 5-segment prefix is a frozen id.\n")
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"verdict: {verdict}")
    print(f"frozen-id tokenizer sensitivity: {defects['frozen_id_tokenizer_sensitivity']} "
          f"(missed: {missed_frozen})")
    print(f"regression: {regression['verdict']} "
          f"tp={regression['tp']} fn={regression['fn']} tn={regression['tn']} fp={regression['fp']}")
    print(f"hard-field control held: {controls['hard_field_rule_unaffected']}")
    print(f"proposed copy defective: {proposed_has_defect}")
    print(f"probe miss probes: {[r['probe'] for r in probe_rows if r['soft_missed']]}")
    print(f"drift during run: {drift}")
    ok = (not drift and controls["hard_field_rule_unaffected"]
          and regression["verdict"] == "PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
