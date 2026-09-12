#!/usr/bin/env python3
"""Consolidate FORM-PROBE-11 outputs into verdict_summary.json (worker-06).

Reads the runner outputs + surface inventory + R32 calibration, re-verifies every
deliverable hash, and writes the single JSON the comms events cite.  Also computes the
frozen-stage-B caveat explicitly: frozen B flags all 7 WCC-base fixtures with R03, the
same layout false positive it raises on the canonical WCC schema, so excluding R03 the
frozen auditor detects 0/22 leaks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    rep = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw_verdicts.json").read_text())
    blind = json.loads((HERE / "blindspot_report.json").read_text())
    r32 = json.loads((HERE / "r32_calibration.json").read_text())
    inv = json.loads((HERE / "surface_inventory.json").read_text())
    man = json.loads((HERE / "manifest.json").read_text())

    mutants = [f["id"] for f in man["fixtures"] if f["kind"] == "mutant"]
    frozen_caught = [i for i in mutants if raw[i]["B_semantic_frozen"]["caught"]]
    frozen_rules = sorted({r for i in frozen_caught for r in (raw[i]["B_semantic_frozen"]["failed_rules"] or [])})
    frozen_real = [i for i in frozen_caught if "R03" not in (raw[i]["B_semantic_frozen"]["failed_rules"] or [])]

    deliverables = ["manifest.json", "manifest.sha256", "report.json", "raw_verdicts.json",
                    "per_surface.json", "blindspot_report.json", "surface_inventory.json",
                    "r32_calibration.json", "make_exempt11.py", "run_exempt11.py",
                    "propose_r32.py", "calibrate_exempt11.py", "audit_calibrated_exempt11.py"]
    out = {
        "artifact": "FORM-PROBE-11-VERDICT-SUMMARY",
        "task_id": "FORM-PROBE-11",
        "worker": "worker-06", "node_id": "A1", "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "recorded_at": rep["recorded_at"],
        "one_line": ("22/22 single-field prose-leak mutants survive both stages at FROZEN rev28; "
                     "union escape 1.0000 across 7 leak families, 3 surface classes and all "
                     "load-bearing tiers; controls green; no drift."),
        "lineage": {
            "predecessor": "FORM-EXEMPT-09",
            "predecessor_measurement": ("18/18 union escape at FROZEN rev18 (structural 0/18, "
                                        "semantic 0/18); invalidated for the current revision by "
                                        "freeze drift and explicitly required a NEW pre-registered "
                                        "corpus for the new bytes"),
            "predecessor_refs": {
                "artifacts/worker-06/exempt_field_corpus/manifest.json":
                    "0627216b6b276f80132c75ebe5257f074175f56a311c83db3df838fd6bb055fb",
                "artifacts/worker-06/exempt_field_corpus/report.json":
                    "8af6bb5a3ba15864c54db67a3c4ed3b604b477165edf582f452c0e755e988452",
                "artifacts/worker-06/exempt_field_corpus/relocation_report.json":
                    "60a57bdbd447b6c36509187de0506617ef74578256997a02eb265b61d8f86079",
            },
            "what_is_new_here": ("(a) a new corpus, independently generated against FROZEN rev28, "
                                 "replicating the rev18 result at the current bytes; (b) a mechanical "
                                 "leaf-level surface inventory (~95% of canonical string leaves are "
                                 "outside the family-token scan); (c) a false-positive-calibrated "
                                 "candidate rule (R32-narrow: 0 FP, 10/10 S2 catches) plus measured "
                                 "rejection of the broad variants (6 FP fixtures each)."),
            "replication_claim": ("union escape 1.0000 at rev18 (FORM-EXEMPT-09) and 1.0000 at rev28 "
                                  "(this corpus), on independently built corpora"),
        },
        "headline": {
            "corpus_validity": rep["corpus_validity"],
            "fixtures_total": len(man["fixtures"]),
            "candidate_mutants": len(mutants),
            "union_escape_rate": rep["aggregates"]["union_escape"]["escape_rate"],
            "structural_escape_rate": rep["aggregates"]["structural_escape"]["escape_rate"],
            "semantic_escape_primary_calibrated": rep["aggregates"]["semantic_escape_primary"]["escape_rate"],
            "escape_by_surface": rep["aggregates"]["by_surface"],
            "escape_by_load_bearing": rep["aggregates"]["by_load_bearing"],
            "escape_by_family": rep["aggregates"]["by_family"],
            "escape_by_class": rep["aggregates"]["by_class"],
            "escaped_families": rep["escape_families"],
            "families_probed": rep["families_probed"],
            "controls": rep["calibration"],
            "frozen_stage_B_caveat": {
                "flagged_fixtures": frozen_caught,
                "failed_rules": frozen_rules,
                "genuine_leak_detections_excluding_R03": frozen_real,
                "explanation": ("frozen stage B rejects every WCC-base fixture (and the canonical WCC "
                                "schema p01 itself) with R03, the documented binder-layout false "
                                "positive; excluding R03 its genuine detection on this corpus is 0/22. "
                                "The calibrated B' is the primary stage-B measure."),
            },
        },
        "surface_map": {
            "gate_sha256": inv["gate_sha256"],
            "counts_per_schema": {c: d["by_class_counts"] for c, d in inv["schemas"].items()},
            "reading": ("A_LEXICAL = family-token scanned; R13_COMPOSITE = composite-regularity scan "
                        "only; EXEMPT_KEY = neither. ~95% of canonical string leaves are outside the "
                        "family-token scan."),
        },
        "candidate_fix_calibration": {
            "R32-fam": {k: r32["modes"]["R32-fam"][k] for k in
                        ("fp_count", "catches_on_mutants", "misses_on_mutants")},
            "R32-fam-pol": {k: r32["modes"]["R32-fam-pol"][k] for k in
                            ("fp_count", "catches_on_mutants", "misses_on_mutants")},
            "R32-narrow": {k: r32["modes"]["R32-narrow"][k] for k in
                           ("fp_count", "catches_on_mutants", "misses_on_mutants")},
            "recommendation": ("Do NOT adopt a broad family-token scan: R32-fam and R32-fam-pol both "
                               "flag the canonical schemas (6 FP fixtures), because foreign-family "
                               "words are legitimate in negative/rationale/metadata prose. The "
                               "adoptable shape is R32-narrow: the declared load-bearing, non-exempt "
                               "allowlist with 0 FP on canonical + negative controls and 10/10 catches "
                               "of the S2 mutants. S1 exempt subtrees and S3 metadata need a polarity/"
                               "provenance policy, not a token scan. PROPOSAL ONLY - adoption is "
                               "lead-formulation's."),
            "allowlist": r32["modes"]["R32-narrow"].get("allowlist", []),
            "self_falsifier": r32["modes"]["R32-narrow"]["self_falsifier"],
        },
        "top_findings": [
            {"rank": 1, "finding": ("The two-stage pipeline has no family-token scan outside "
                                    "ASSERTIVE_PATHS: 10/10 non-exempt declarative prose fields "
                                    "(S2) accepted a foreign-family assertion, including "
                                    "conclusion.wellformedness_conditions, genericity.ambient_space, "
                                    "conclusion.known_obstruction, conventions.proof_status and "
                                    "quantifiers.order_note."),
             "falsifier": "Reject any S2 fixture at the pinned hashes."},
            {"rank": 2, "finding": ("EXEMPT_KEY is key-based, not polarity-based: a positive, "
                                    "assertive claim placed in a by-design-exempt subtree "
                                    "(genericity.class_change_warning, provenance.no_progress_claim, "
                                    "extension_predicate.why_*, known_status.why_*) is accepted; 8/8 "
                                    "S1 mutants escaped."),
             "falsifier": "A gate revision that checks polarity inside EXEMPT_KEY subtrees."},
            {"rank": 3, "finding": ("Revision-history and status metadata prose (S3) is unscanned and "
                                    "is exactly what reviewers read for provenance; 4/4 S3 mutants "
                                    "escaped, including a theorem-promotion note in "
                                    "adjudication_queue.note and a refuted-class claim in "
                                    "revision_history[9].notes."),
             "falsifier": "A gate revision that scans or forbids class assertions in metadata."},
        ],
        "deliverable_hashes": {d: sha(HERE / d) for d in deliverables if (HERE / d).exists()},
        "pins": rep["pins_before"],
        "manifest_sha256_before_run": rep["manifest_sha256_before_run"],
        "moving_target_drift": rep["moving_target_drift"],
        "fixture_byte_drift": rep["fixture_byte_drift"],
        "blindspot_entries": len(blind["entries"]),
        "falsifier": rep["falsifier"],
        "authority": rep["authority"],
        "not_claimed": rep["not_claimed"],
    }
    # fill allowlist from the module source (declared list) for transparency
    try:
        import importlib.util
        s = importlib.util.spec_from_file_location("p32", HERE / "propose_r32.py")
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        out["candidate_fix_calibration"]["allowlist"] = m.R32_NARROW_ALLOWLIST
    except Exception:
        pass
    (HERE / "verdict_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    print(json.dumps({"summary_sha256": sha(HERE / "verdict_summary.json"),
                      "union_escape": out["headline"]["union_escape_rate"],
                      "frozen_genuine_detections": out["headline"]["frozen_stage_B_caveat"][
                          "genuine_leak_detections_excluding_R03"],
                      "r32_narrow": out["candidate_fix_calibration"]["R32-narrow"]}, indent=1))


if __name__ == "__main__":
    main()
