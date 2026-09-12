#!/usr/bin/env python3
"""W003-CLASSSEP-D0-COVERAGE-01: does the standing class-separation detector
(research_map/class_separation.py + its 27-fixture corpus) provide any coverage
for the live D0 data-regularity disjunction in the three G-FORM schemas?

Read-only. Deterministic. Stdlib only.

The failure mode probed (documented independently as W037-F5,
artifacts/worker-037/gform_freeze_verification/report.json):
    quantifiers.domains.D0.definition =
      "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1),
       or the smooth-with-decay default"
i.e. the formal class statement quantifies over a two-branch regularity domain,
one branch of which supplies no (s,delta) pair, so the "single frozen data class"
precondition of G-FORM is arguably unmet.

This script measures only the DETECTOR-COVERAGE question:
  (1) reproduce the corpus baseline (expect 17/10/0/0 PASS),
  (2) count corpus fixtures exercising a D0-style regularity-setting disjunction,
  (3) score the three canonical schema texts at pinned hashes,
  (4) run calibrated controls that isolate *why* the detector is silent,
  (5) sensitivity: does removing the disjunction change any detector output at all?
It sets no gate verdict and is not a review of F2a/F2b/F1.

Exit codes: 0 = all expected outcomes reproduce; 2 = unexpected/assertion failure;
            3 = input drift during the run (void, re-run).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

DETECTOR = ROOT / "research_map/class_separation.py"
CORPUS_DIR = ROOT / "artifacts/worker-07/class_separation_falsification"
CORPUS_RESULTS = CORPUS_DIR / "results.json"
SCHEMAS = {
    "F1": ROOT / "schemas/af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
W037 = ROOT / "artifacts/worker-037/gform_freeze_verification/report.json"
RUBRIC = ROOT / "evaluation_rubric.yaml"

# --- controls ---------------------------------------------------------------
# P1: C0/C2 shorthand merge placed inside the D0 definition slot. If the detector
#     is alive in that text region this must be flagged (prose mode scans all text).
P1_SHORTHAND_IN_D0 = (
    "quantifiers:\n"
    "  domains:\n"
    "    D0:\n"
    '      definition: "C0 or C2 are one class"\n'
    "      definition_ref: regularity.data_regularity\n"
)
# P2: the live D0 sentence with the disjunction removed (benign rewrite).
P2_SINGLE_BRANCH = "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1)"
# P3: prohibition phrasing (same shape as corpus fixture C03) must stay unflagged.
P3_PROHIBITION = "Forbidden: never write 'C0 or C2' in a schema."
# P4: full known class-id disjunction, same slot (secondary observation: is the
#     shorthand the only recognized vocabulary?).
P4_CLASSID_DISJUNCTION_IN_D0 = (
    "quantifiers:\n"
    "  domains:\n"
    "    D0:\n"
    '      definition: "AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN are one class"\n'
    "      definition_ref: regularity.data_regularity\n"
)
# P5: shorthand merge under a declaration-scanned key (positive control for R1).
P5_SCANNED_KEY = 'regularity: "C0 or C2 are one class"'


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_detector():
    spec = importlib.util.spec_from_file_location("cs_measured", DETECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def d0_line(text: str):
    """Return (lineno, line) of the D0 definition line."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*D0:\s*$", line):
            for j in range(i + 1, min(i + 6, len(lines))):
                if re.match(r"^\s*definition:", lines[j]):
                    return j + 1, lines[j].strip()
    return None, None


def d0_style_disjunction(text: str) -> bool:
    """D0-style = a regularity-SETTING disjunction ('X, or the Y default'),
    distinct from a class-token disjunction ('C0 or C2')."""
    t = re.sub(r"\s+", " ", text)
    return bool(re.search(r"admissible regularity pairs[^.]*\bor\b", t)) or bool(
        re.search(r"regularity[^.]{0,80}\bor\b[^.]{0,80}(smooth-with-decay|Sobolev)", t)
    )


def corpus_scan(cs, results: dict):
    """Per-fixture: does any text in the fixture exercise a D0-style disjunction?"""
    rows = []
    for fx in results["fixtures"]:
        fp = ROOT / fx["fixture_path"]
        texts = []
        if fp.is_file():
            texts.append(fp.read_text(errors="replace"))
            try:
                m = json.loads(fp.read_text())
            except Exception:
                m = None
            if isinstance(m, dict):
                for g in m.get("groups", []):
                    for n in g.get("nodes", []):
                        art = n.get("artifact")
                        ap = ROOT / art if isinstance(art, str) else None
                        if ap and ap.is_file():
                            texts.append(ap.read_text(errors="replace"))
        hits = sum(1 for t in texts if d0_style_disjunction(t))
        try:
            det = bool(cs.findings_for_map(json.loads(fp.read_text()))) if fp.is_file() else False
        except Exception as e:  # pragma: no cover - malformed fixture
            det = f"error: {e}"
        rows.append(
            {
                "id": fx["id"],
                "is_class_merge": bool(fx["is_class_merge"]),
                "fixture_path": fx["fixture_path"],
                "d0_style_disjunction_texts": hits,
                "detected": det,
            }
        )
    return rows


def main() -> int:
    ran_at = datetime.now(CST).isoformat(timespec="seconds")

    # ---- T0 hashes ---------------------------------------------------------
    t0 = {str(p.relative_to(ROOT)): sha256_file(p) for p in [DETECTOR, CORPUS_RESULTS, *SCHEMAS.values(), W037, RUBRIC]}
    cs = load_detector()
    results = json.loads(CORPUS_RESULTS.read_text())

    # ---- (1) corpus baseline ----------------------------------------------
    baseline = cs.regression()
    baseline["expected"] = {"tp": 17, "tn": 10, "fp": 0, "fn": 0, "verdict": "PASS", "corpus_size": 27}
    baseline["matches_expected"] = all(
        baseline[k] == v for k, v in baseline["expected"].items()
    )

    # ---- (2) corpus coverage of the D0 failure mode ------------------------
    rows = corpus_scan(cs, results)
    d0_fixtures = [r for r in rows if r["d0_style_disjunction_texts"] > 0]

    # ---- detector rule facts (mechanism, measured not asserted) ------------
    rule_facts = {
        "merge_pat": getattr(cs, "_MERGE_PAT").pattern,
        "asserted_line_keys": sorted(getattr(cs, "ASSERTED_LINE_KEYS")),
        "definition_key_scanned_in_declaration_mode": "definition" in getattr(cs, "ASSERTED_LINE_KEYS"),
        "known_classes_arity": sorted({len(t.split("-")) for t in getattr(cs, "KNOWN_CLASSES")}),
    }

    # ---- (3) canonical schemas --------------------------------------------
    schema_scan = {}
    for name, path in SCHEMAS.items():
        text = path.read_text()
        lineno, line = d0_line(text)
        full = cs.findings_for_text(text, f"schemas/{path.name}")
        d0_findings = [f for f in full if "smooth-with-decay" in f or "admissible regularity" in f]
        single = text.replace(
            "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1), or the smooth-with-decay default",
            P2_SINGLE_BRANCH,
        ).replace(
            "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1), or the smooth-with-decay default; the class is fixed at these values and does not range over 'suitable' regularity",
            P2_SINGLE_BRANCH + "; the class is fixed at these values and does not range over 'suitable' regularity",
        )
        single_findings = cs.findings_for_text(single, f"single-branch-rewrite/{path.name}")
        schema_scan[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": t0[str(path.relative_to(ROOT))],
            "d0_lineno": lineno,
            "d0_definition": line,
            "d0_line_findings": cs.findings_for_text(line or "", f"{name}:D0"),
            "full_text_findings": full,
            "full_text_findings_mentioning_d0": d0_findings,
            "single_branch_rewrite_findings": single_findings,
            "sensitivity_findings_delta": len(full) - len(single_findings),
        }

    # ---- (4) calibrated controls ------------------------------------------
    c1 = cs.findings_for_text(P1_SHORTHAND_IN_D0, "control-P1-shorthand-in-D0-slot")
    c2 = cs.findings_for_text(P2_SINGLE_BRANCH, "control-P2-single-branch")
    c3 = cs.findings_for_text(P3_PROHIBITION, "control-P3-prohibition")
    c4 = cs.findings_for_text(P4_CLASSID_DISJUNCTION_IN_D0, "control-P4-classid-disjunction-in-D0-slot")
    c5 = cs.findings_for_text(P5_SCANNED_KEY, "control-P5-scanned-key-shorthand")
    controls = {
        "P1_shorthand_in_D0_slot_flagged": {"text": P1_SHORTHAND_IN_D0, "findings": c1, "flagged": len(c1) > 0},
        "P2_single_branch_silent": {"text": P2_SINGLE_BRANCH, "findings": c2, "flagged": len(c2) > 0},
        "P3_prohibition_silent": {"text": P3_PROHIBITION, "findings": c3, "flagged": len(c3) > 0},
        "P4_classid_disjunction_in_D0_slot_flagged": {"text": P4_CLASSID_DISJUNCTION_IN_D0, "findings": c4, "flagged": len(c4) > 0},
        "P5_scanned_key_shorthand_flagged": {"text": P5_SCANNED_KEY, "findings": c5, "flagged": len(c5) > 0},
    }

    # ---- (5) expectation checks -------------------------------------------
    checks = {
        "C1_baseline_reproduces": baseline["matches_expected"],
        "C2_no_corpus_d0_fixture": len(d0_fixtures) == 0,
        "C3_canonical_d0_silent": all(
            len(s["full_text_findings_mentioning_d0"]) == 0 for s in schema_scan.values()
        ),
        "C4_d0_line_silent": all(len(s["d0_line_findings"]) == 0 for s in schema_scan.values()),
        "C5_detector_alive_in_d0_slot": controls["P1_shorthand_in_D0_slot_flagged"]["flagged"],
        "C6_zero_sensitivity": all(s["sensitivity_findings_delta"] == 0 for s in schema_scan.values()),
        "C7_prohibition_control_clean": not controls["P3_prohibition_silent"]["flagged"],
    }
    all_pass = all(checks.values())

    # ---- T1 drift check ----------------------------------------------------
    t1 = {str(p.relative_to(ROOT)): sha256_file(p) for p in [DETECTOR, CORPUS_RESULTS, *SCHEMAS.values(), W037, RUBRIC]}
    drift = sorted(k for k in t0 if t0[k] != t1.get(k))

    rubric_lines = RUBRIC.read_text().splitlines()
    no_or = next((f"{i+1}: {l.strip()}" for i, l in enumerate(rubric_lines) if 'no "roughly"' in l), None)

    payload = {
        "task_id": "W003-CLASSSEP-D0-COVERAGE-01",
        "worker": "worker-003",
        "generated_at": ran_at,
        "method": "read-only: measured-hash pin -> import measured detector -> corpus baseline -> "
                  "per-fixture D0 scan -> canonical schema scoring -> calibrated controls -> "
                  "single-branch sensitivity rewrite -> T1 re-hash",
        "inputs": {
            "detector": {"path": "research_map/class_separation.py", "sha256": t0["research_map/class_separation.py"]},
            "corpus_results": {"path": "artifacts/worker-07/class_separation_falsification/results.json",
                               "sha256": t0["artifacts/worker-07/class_separation_falsification/results.json"]},
            "schemas": {k: {"path": str(v.relative_to(ROOT)), "sha256": t0[str(v.relative_to(ROOT))]} for k, v in SCHEMAS.items()},
            "w037_f5_source": {"path": "artifacts/worker-037/gform_freeze_verification/report.json",
                               "sha256": t0["artifacts/worker-037/gform_freeze_verification/report.json"]},
            "a0_gform_criterion_line": {"path": "evaluation_rubric.yaml", "sha256": t0["evaluation_rubric.yaml"], "quote": no_or},
        },
        "detector_rule_facts": rule_facts,
        "baseline_regression": baseline,
        "corpus_rows": rows,
        "corpus_d0_style_fixtures": [r["id"] for r in d0_fixtures],
        "schema_scan": schema_scan,
        "controls": controls,
        "secondary_observations": {
            "known_classid_disjunction_flagged": controls["P4_classid_disjunction_in_D0_slot_flagged"]["flagged"],
            "reading": "R1 fires on the bare C0/C2 shorthand (P1, P5) but not on a full known class-id "
                       "disjunction (P4: silent) and not on the regularity-setting disjunction (canonical D0: silent). "
                       "P4 is an adjacent observation for the detector owner (cf. W027-CLASSSEP-ARITY-01); it is not "
                       "needed for the D0 coverage claim.",
        },
        "checks": checks,
        "all_checks_pass": all_pass,
        "drift_T0_vs_T1": drift,
        "scope": {
            "is": "detector-coverage measurement for one failure mode",
            "is_not": ["a review verdict", "a gate verdict", "a claim that W037-F5 is correct",
                       "an edit to the detector or the corpus"],
        },
        "claim": (
            "At the measured hashes above, the standing class-separation detector reproduces its "
            "27-fixture baseline (17/10/0/0 PASS) and is silent on the live D0 data-regularity "
            "disjunction in all three G-FORM schemas. Three mechanisms are measured, not asserted: "
            "(i) R1's merge pattern matches only bare C0/C2 composites, so 'Sobolev variant ... or the "
            "smooth-with-decay default' is outside its vocabulary; (ii) the D0 key 'definition' is not in "
            "ASSERTED_LINE_KEYS, so the D0 definition is never declaration-scanned (the detector is alive "
            "in that text region: the same slot carrying 'C0 or C2 are one class' is flagged); (iii) no "
            "corpus fixture exercises a D0-style regularity-setting disjunction, so the PASS cannot cover "
            "it. Sensitivity is zero: replacing the live disjunction with a single branch changes no "
            "detector output. Therefore classsep PASS is not coverage for the G-FORM single-frozen-data-class "
            "criterion and is neither evidence for nor against W037-F5."
        ),
        "falsifier": (
            "Re-run this script with the same input hashes. Falsified if (a) any canonical D0 line or "
            "D0 mention produces a class-separation finding, (b) a corpus fixture contains a D0-style "
            "regularity-setting disjunction, (c) the P1 shorthand-in-D0-slot control fails to produce a "
            "finding (detector not alive in that region), or (d) the single-branch rewrite changes any "
            "finding. Any hash drift voids the run (re-run) rather than falsifying it."
        ),
    }
    body = json.dumps(payload, indent=1, sort_keys=True)
    payload["report_payload_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    out = OUT / "report.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "task_id": payload["task_id"],
        "report": str(out.relative_to(ROOT)),
        "report_sha256": sha256_file(out),
        "baseline": {k: baseline[k] for k in ("tp", "tn", "fp", "fn", "verdict", "corpus_size")},
        "checks": checks,
        "all_checks_pass": all_pass,
        "drift": drift,
        "secondary": payload["secondary_observations"],
        "d0_definitions": {k: v["d0_definition"] for k, v in schema_scan.items()},
    }, indent=1))
    if drift:
        return 3
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
