#!/usr/bin/env python3
"""W096-F2B-INDEP-REVIEW-01: independent, hash-bound review of the canonical F2b schema.

Target : schemas/af_scc_c0_vacuum.yaml  (class AF-SCC-C0-VAC-GEN, node F2b)
Author : worker-096   (not the schema author; schema authored_by astra-lead-formulation)

This is a REVIEW artifact, not a completion claim. It checks the G-FORM structural
criteria for exactly one frozen class against the schema bytes measured in this run,
using a re-implementation that does NOT import the canonical checker for its own
verdicts. The canonical checker is run only as corroboration and its exit code is
recorded.

Design rules honoured:
  * every verdict is bound to a measured sha256; if the file changes during the run the
    report is marked ADVISORY (drift voids the binding);
  * findings carry explicit falsifiers;
  * a duplicate-key YAML defect and a declared-timestamp/mtime skew are recorded even
    though yaml.safe_load hides them (last-key-wins).

USAGE
  python3 run_review.py [--root ROOT] [--out report.json]
Exit: 0 = no critical failure and no drift; 1 = critical failure or drift; 2 = usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
SCHEMA_REL = "schemas/af_scc_c0_vacuum.yaml"
AUTHORING_REL = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
TAXONOMY_REL = "research_map/formulation_taxonomy.yaml"
LEDGER_REL = "ledger/theorems.jsonl"
ALIASES_REL = "artifacts/formulation/VOCAB_ALIASES.json"
CHECKER_REL = "artifacts/formulation/tools/check_class_schema.py"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
REVIEW_ID = "W096-F2B-INDEP-REVIEW-01"

WCC_TOKENS = re.compile(r"weak[\s_-]*cosmic|naked[\s_-]*singularit|visible\s+singularit|"
                        r"completeness\s+of\s+I\+|I\+\s+completeness", re.I)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys (which last-wins hides)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicate_keys: list = []

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        seen = []
        for key_node, _ in node.value:
            try:
                key = self.construct_object(key_node, deep=True)
            except Exception:
                key = None
            if key in seen:
                self.duplicate_keys.append(
                    {"key": str(key), "line": key_node.start_mark.line + 1}
                )
            else:
                seen.append(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml_recording_dups(path: Path):
    loader = DupKeyLoader(path.read_text(encoding="utf-8"))
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, loader.duplicate_keys


def check(cid: str, name: str, ok: bool, severity: str, detail, falsifier: str):
    return {
        "check_id": cid,
        "name": name,
        "status": "pass" if ok else "fail",
        "severity": severity if not ok else "none",
        "detail": detail,
        "falsifier": falsifier,
    }


def note(cid: str, name: str, detail, falsifier: str):
    return {
        "check_id": cid,
        "name": name,
        "status": "note",
        "severity": "info",
        "detail": detail,
        "falsifier": falsifier,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    args = ap.parse_args()
    root = Path(args.root).resolve()

    schema_path = root / SCHEMA_REL
    reviewed_at = datetime.now(CST).isoformat(timespec="seconds")
    sha_before = sha256_file(schema_path)
    mtime = datetime.fromtimestamp(schema_path.stat().st_mtime, CST).isoformat(timespec="seconds")

    doc, dup_keys = load_yaml_recording_dups(schema_path)
    schema_text = schema_path.read_text(encoding="utf-8")

    checks: list[dict] = []
    findings: list[dict] = []

    # ---- C1 single class binding -------------------------------------------------
    cid = doc.get("class_id")
    unknown_tokens = set(re.findall(r"AF-[A-Z0-9-]+", schema_text)) - {
        CLASS_ID, "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH",
    }
    checks.append(check(
        "C1-single-class-binding", "exactly one frozen class_id, no unknown class tokens",
        cid == CLASS_ID and not unknown_tokens, "critical",
        {"class_id": cid, "unknown_class_shaped_tokens": sorted(unknown_tokens)},
        "any class_id != AF-SCC-C0-VAC-GEN, or any unknown AF-* token outside the frozen four, falsifies this check",
    ))

    # ---- C2 quantifier prefix ----------------------------------------------------
    q = doc.get("quantifiers", {})
    kinds = [o.get("kind") for o in q.get("ordered", [])]
    formal = str(q.get("formal", ""))
    expect = ["forall", "exists", "forall", "not_exists"]
    q_ok = kinds == expect and q.get("order_matters") is True and "comeager" in formal
    checks.append(check(
        "C2-quantifier-order", "ordered quantifier prefix forall-exists(comeager)-forall-not_exists",
        q_ok, "critical",
        {"ordered_kinds": kinds, "expected": expect, "order_matters": q.get("order_matters"),
         "negation_normal_form_present": bool(q.get("negation_normal_form"))},
        "a reordering or a dropped comeager quantifier in the frozen prefix falsifies this check",
    ))

    # ---- C3 data class -----------------------------------------------------------
    dc = doc.get("data_class", {})
    topo = doc.get("topology", {})
    data_ok = (dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
               and "vacuum" in str(dc.get("equations", "")).lower()
               and "hamiltonian" in dc.get("constraints", {}) and "momentum" in dc.get("constraints", {})
               and dc.get("regularity_class", {}).get("default")
               and topo.get("spacetime_dimension") == 4
               and "one AF end" in str(topo.get("end_structure", "")))
    checks.append(check(
        "C3-data-class", "vacuum, Lambda=0, 4d, one AF end, both constraints, regularity named",
        bool(data_ok), "critical",
        {"matter": dc.get("matter"), "cosmological_constant": dc.get("cosmological_constant"),
         "dimension": topo.get("spacetime_dimension"), "end_structure": topo.get("end_structure"),
         "regularity_default": dc.get("regularity_class", {}).get("default")},
        "a non-vacuum matter entry, Lambda != 0, dimension != 4 or a missing constraint falsifies this check",
    ))

    # ---- C4 genericity token and topology ----------------------------------------
    aliases = json.loads((root / ALIASES_REL).read_text())
    gen = doc.get("genericity", {})
    canon_gen = aliases["genericity_kind"].get(gen.get("kind")) is not None
    checks.append(check(
        "C4-genericity-token", "genericity kind is a canonical alias-registry token, topology named",
        bool(canon_gen and gen.get("topology_or_measure") and gen.get("is_part_of_class") is True
             and gen.get("class_change_warning")),
        "major",
        {"kind": gen.get("kind"), "canonical_per_alias_registry": canon_gen,
         "topology_named": bool(gen.get("topology_or_measure")),
         "is_part_of_class": gen.get("is_part_of_class"),
         "no_silent_strengthening_warning": bool(gen.get("class_change_warning"))},
        "changing genericity.kind to a token absent from VOCAB_ALIASES.json, or dropping the topology, falsifies this check",
    ))

    # ---- C5 conclusion token, family, no WCC content -----------------------------
    concl = doc.get("conclusion", {})
    con_token = concl.get("conclusion_type")
    con_canon = con_token in aliases["conclusion_type"]
    asserted = " ".join(str(concl.get(k, "")) for k in ("statement_natural_language", "statement_formal"))
    asserted_wcc = WCC_TOKENS.findall(asserted)
    ip, vis = doc.get("i_plus", {}), doc.get("visibility", {})
    roles_ok = (ip.get("in_conclusion") is False and vis.get("role") == "not_in_conclusion"
                and "not" in str(vis.get("forbidden_falsifier", "")).lower())
    checks.append(check(
        "C5-conclusion-family", "SCC-C0 conclusion token, no WCC content in the asserted statement",
        bool(con_canon and not asserted_wcc and roles_ok), "critical",
        {"conclusion_type": con_token, "canonical_per_alias_registry": con_canon,
         "wcc_tokens_in_asserted_statement": asserted_wcc,
         "i_plus_in_conclusion": ip.get("in_conclusion"), "visibility_role": vis.get("role")},
        "a WCC predicate (visibility / I+ completeness) inside conclusion.*, or a conclusion_type outside the alias registry, falsifies this check",
    ))

    # ---- C6 implication direction (C0 => C2, never reverse) ----------------------
    impl = doc.get("implication_ledger", {})
    rows = impl.get("one_way_entailments", [])
    has_c0_to_c2 = any("C0" in str(r.get("from")) and "C2" in str(r.get("to")) for r in rows)
    forb = " ".join(str(r.get("reason", "")) for r in impl.get("forbidden_transfers", []))
    forb_ok = "strictly larger extension class" in forb or "C2" in forb
    checks.append(check(
        "C6-implication-direction", "C0 => C2 recorded and the converse forbidden",
        bool(has_c0_to_c2 and forb_ok and impl.get("cross_family")), "critical",
        {"has_c0_to_c2_row": has_c0_to_c2, "forbidden_transfers_present": bool(impl.get("forbidden_transfers")),
         "cross_family_rule": impl.get("cross_family")},
        "a transfer row from C2 (or H2_loc) to C0, or a removed C0=>C2 row, falsifies this check",
    ))

    # ---- C7 falsifier structure --------------------------------------------------
    fal = doc.get("falsifier", {})
    t1, t2 = fal.get("tier_1", {}), fal.get("tier_2", {})
    tier2_label = t2.get("labelling_required") or t2.get("labelled_required")
    fals_ok = (t1.get("refutes") == CLASS_ID and t1.get("witness_type")
               and t1.get("machine_checkable_steps")
               and tier2_label == "refutes_strengthening_only"
               and fal.get("schema_falsifiers"))
    checks.append(check(
        "C7-falsifier-tiers", "tier-1 refutes exactly this class; tier-2 labelled strengthening-only",
        bool(fals_ok), "critical",
        {"tier_1_refutes": t1.get("refutes"), "tier_2_labelling": tier2_label,
         "machine_checkable_steps": len(t1.get("machine_checkable_steps", []) or []),
         "schema_falsifiers": len(fal.get("schema_falsifiers", []) or [])},
        "a tier-1 falsifier that refutes a different class, or an unlabelled tier-2 strengthening refutation, falsifies this check",
    ))

    # ---- C8 extension predicate frozen at C0, no equation ------------------------
    ep = doc.get("extension_predicate", {})
    ep_ok = ep.get("frozen_regularity") == "C0" and ep.get("frozen_equation_concept") == "none"
    checks.append(check(
        "C8-extension-predicate", "extension frozen at C0 with no equation requirement",
        bool(ep_ok), "critical",
        {"frozen_regularity": ep.get("frozen_regularity"),
         "frozen_equation_concept": ep.get("frozen_equation_concept")},
        "an H2_loc/C2 regularity or a distributional-Ricci equation requirement in extension_predicate falsifies this check",
    ))

    # ---- C9 declared F0 binding matches measured F0 hash -------------------------
    f0 = doc.get("f0_binding", {})
    taxonomy_path = root / str(f0.get("declared_f0_artifact", TAXONOMY_REL))
    taxonomy_sha = sha256_file(taxonomy_path) if taxonomy_path.is_file() else None
    f0_ok = taxonomy_sha is not None and f0.get("declared_f0_sha256") == taxonomy_sha
    checks.append(check(
        "C9-f0-binding", "declared F0 sha256 equals the measured canonical F0 sha256",
        bool(f0_ok), "critical",
        {"declared_f0_artifact": str(f0.get("declared_f0_artifact")),
         "declared_f0_sha256": f0.get("declared_f0_sha256"),
         "measured_f0_sha256": taxonomy_sha},
        "a declared_f0_sha256 that no longer equals the measured canonical F0 hash falsifies this binding (drift, not a schema defect)",
    ))

    # ---- C10 ledger refs exist with matching status ------------------------------
    ledger: dict[str, str] = {}
    for line in (root / LEDGER_REL).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        tid = row.get("theorem_id") or row.get("id") or row.get("key")
        if tid:
            ledger[tid] = row.get("status")
    refs = doc.get("l1_ledger_refs", [])
    mismatches = []
    for r in refs:
        tid, want = r.get("theorem_id"), r.get("l1_status")
        got = ledger.get(tid, "<absent>")
        if got != want:
            mismatches.append({"theorem_id": tid, "schema_l1_status": want, "ledger_status": got})
    checks.append(check(
        "C10-ledger-refs", "every l1_ledger_refs theorem_id exists and its status matches the ledger",
        not mismatches and bool(refs), "critical",
        {"refs": len(refs), "mismatches": mismatches},
        "any theorem_id absent from ledger/theorems.jsonl, or any status disagreement, falsifies this check",
    ))

    # ---- C11 publication pair byte-identical -------------------------------------
    authoring_path = root / AUTHORING_REL
    authoring_sha = sha256_file(authoring_path) if authoring_path.is_file() else None
    checks.append(check(
        "C11-publication-pair", "canonical schema is byte-identical to the authoring-tree copy",
        authoring_sha == sha_before, "major",
        {"canonical": sha_before, "authoring": authoring_sha},
        "any byte difference between schemas/af_scc_c0_vacuum.yaml and artifacts/formulation/schemas/af_scc_c0_vacuum.yaml falsifies this check",
    ))

    # ---- C12 duplicate YAML keys (hidden by last-wins) ---------------------------
    if dup_keys:
        findings.append({
            "finding_id": "W096-F2B-F01",
            "severity": "minor",
            "title": "duplicate top-level YAML keys in the canonical schema",
            "detail": dup_keys,
            "impact": ("yaml.safe_load resolves duplicates last-wins, so the effective revised_at is the "
                       "last entry; strict YAML parsers reject the document. Revision history is encoded "
                       "as repeated keys, not as a sequence."),
            "falsifier": "a strict duplicate-key parser run on the same bytes that exits 0, or a revision of the file with unique keys",
        })
        checks.append(check(
            "C12-duplicate-keys", "no duplicate top-level YAML keys",
            False, "minor", {"duplicate_count": len(dup_keys), "duplicates": dup_keys},
            "a strict YAML parser accepting these bytes falsifies the finding",
        ))
    else:
        checks.append(check("C12-duplicate-keys", "no duplicate top-level YAML keys", True, "minor",
                            {"duplicate_count": 0},
                            "any duplicate key in a later revision falsifies the previous pass"))

    # ---- C13 timestamp discipline ------------------------------------------------
    declared = [l for l in re.findall(r'^revised_at:\s*"([^"]+)"', schema_text, re.M)]
    declared_ts = datetime.fromisoformat(declared[-1]) if declared else None
    mtime_dt = datetime.fromtimestamp(schema_path.stat().st_mtime, CST)
    now_dt = datetime.now(CST)
    skew_mtime = (declared_ts - mtime_dt).total_seconds() if declared_ts else None
    skew_now = (declared_ts - now_dt).total_seconds() if declared_ts else None
    if skew_now is not None and skew_now > 60:
        findings.append({
            "finding_id": "W096-F2B-F02",
            "severity": "minor",
            "title": "declared revised_at is ahead of wall-clock and of the file mtime",
            "detail": {"declared_revision_ts": declared_ts.isoformat(), "file_mtime": mtime_dt.isoformat(),
                       "review_wall_clock": now_dt.isoformat(timespec="seconds"),
                       "skew_vs_mtime_seconds": skew_mtime, "skew_vs_now_seconds": skew_now},
            "impact": ("the header's own timestamp_provenance records a prior ahead-of-clock correction; "
                       "this recurrence makes the declared revision time unusable as evidence and interacts "
                       "with the project-wide clock-discipline finding (future_dated events)."),
            "falsifier": "a restored/rewritten file whose declared revised_at is <= its mtime and <= wall clock",
        })
        checks.append(check(
            "C13-timestamp-discipline", "declared revised_at is not in the future relative to mtime/wall clock",
            False, "minor",
            {"declared": declared, "mtime": mtime_dt.isoformat(), "skew_vs_now_seconds": skew_now},
            "a file whose declared revised_at is not ahead of wall clock falsifies this finding",
        ))
    else:
        checks.append(check("C13-timestamp-discipline", "declared revised_at is not in the future relative to mtime/wall clock",
                            True, "minor", {"declared": declared},
                            "a future-dated revised_at in a later revision falsifies this pass"))

    # ---- C14 class-separation scan ----------------------------------------------
    sys.path.insert(0, str(root / "research_map"))
    try:
        import class_separation  # type: ignore
        sep = class_separation.findings_for_text(schema_text, SCHEMA_REL)
    except Exception as exc:  # pragma: no cover
        sep = [f"class_separation import/run failed: {exc!r}"]
    checks.append(check(
        "C14-class-separation", "class-separation scanner reports no WCC/SCC merge on this schema",
        not sep, "critical", {"findings": sep},
        "a class-separation finding on these exact bytes falsifies this check",
    ))

    # ---- C15 corroboration: canonical checker ------------------------------------
    checker_cmd = [sys.executable, str(root / CHECKER_REL), "--json", str(schema_path)]
    checker_sha = sha256_file(root / CHECKER_REL) if (root / CHECKER_REL).is_file() else None
    proc = subprocess.run(checker_cmd, capture_output=True, text=True, cwd=str(root), timeout=120)
    checker_json = None
    try:
        checker_json = json.loads(proc.stdout)
    except json.JSONDecodeError:
        checker_json = {"raw": proc.stdout[:2000]}
    checks.append(check(
        "C15-canonical-checker", "canonical structural checker accepts this schema (corroboration only)",
        proc.returncode == 0 and checker_json.get("verdict") == "pass", "major",
        {"command": " ".join(checker_cmd), "checker_sha256": checker_sha, "exit_code": proc.returncode,
         "verdict": checker_json.get("verdict"), "failed_rules": checker_json.get("failed_rules")},
        "canonical checker exit != 0 or verdict != pass on these bytes falsifies this corroboration",
    ))

    # ---- cross-artifact note: F0 vocabulary uses alias tokens --------------------
    try:
        tax = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
        fv = tax.get("field_vocabulary", {})
        alias_tokens = {
            "conclusion_type.allowed": fv.get("conclusion_type", {}).get("allowed"),
            "genericity_kind.allowed": fv.get("genericity_kind", {}).get("allowed"),
        }
        findings.append({
            "finding_id": "W096-F2B-F03",
            "severity": "info",
            "title": "canonical F0 vocabulary lists alias tokens rather than canonical alias-registry tokens",
            "detail": {"f0_allowed_tokens": alias_tokens,
                       "alias_registry_canonical_conclusion": sorted(aliases["conclusion_type"].keys()),
                       "alias_registry_canonical_genericity": sorted(aliases["genericity_kind"].keys()),
                       "f2b_uses_canonical": {"conclusion_type": con_token, "genericity_kind": gen.get("kind")}},
            "impact": ("F2b itself uses the canonical tokens; the inversion is in the declared F0 binding artifact, "
                       "so it is recorded here as a cross-artifact note for F0, not as an F2b failure."),
            "falsifier": "a canonical F0 revision whose field_vocabulary.allowed lists the alias-registry canonical tokens first",
        })
    except Exception as exc:
        findings.append({"finding_id": "W096-F2B-F03", "severity": "info",
                         "title": "F0 vocabulary note not computed", "detail": repr(exc),
                         "falsifier": "n/a"})

    # ---- drift re-measure --------------------------------------------------------
    sha_after = sha256_file(schema_path)
    drift = sha_after != sha_before
    if drift:
        findings.append({
            "finding_id": "W096-F2B-F04",
            "severity": "major",
            "title": "target drifted during the review window",
            "detail": {"sha256_before": sha_before, "sha256_after": sha_after},
            "impact": "hash-bound verdicts below are ADVISORY only; they bind to the before-hash snapshot.",
            "falsifier": "a re-run on the new bytes that yields the same verdicts at the new hash",
        })

    critical_failed = [c for c in checks if c["status"] == "fail" and c["severity"] == "critical"]
    major_failed = [c for c in checks if c["status"] == "fail" and c["severity"] == "major"]
    minor_failed = [c for c in checks if c["status"] == "fail" and c["severity"] == "minor"]

    if critical_failed:
        verdict, score = "reject", 1
    elif major_failed:
        verdict, score = "revise", 3
    elif minor_failed:
        verdict, score = "accept", 4
    else:
        verdict, score = "accept", 5
    if drift and verdict == "accept":
        verdict = "inconclusive"

    report = {
        "report_id": REVIEW_ID,
        "reviewer": "worker-096",
        "reviewer_independence": ("worker-096 authored none of the reviewed artifact, its checker, or its "
                                  "class contracts; review is machine-checked from a re-implementation"),
        "kind": "independent_class_bound_review",
        "target": {
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "path": SCHEMA_REL,
            "sha256_before": sha_before,
            "sha256_after": sha_after,
            "drift_during_review": drift,
            "bytes": schema_path.stat().st_size,
            "file_mtime": mtime,
            "revision_declared": doc.get("revision"),
        },
        "checked_at": reviewed_at,
        "gate_criteria_checked": "G-FORM structural criteria for a single frozen class",
        "checks": checks,
        "findings": findings,
        "critical_failures": [c["check_id"] for c in critical_failed],
        "major_failures": [c["check_id"] for c in major_failed],
        "minor_failures": [c["check_id"] for c in minor_failed],
        "verdict": verdict,
        "score_0_5": score,
        "hard_failures": [],
        "binding_rule": ("this verdict binds only to sha256_before; if the file hash changed before a gate "
                         "verdict is recorded, the verdict is advisory and must be re-run"),
        "falsifier": ("Re-run this script against the same sha256. The review is falsified if (a) any check "
                      "recorded pass fails on identical bytes; (b) the class-separation scan or the canonical "
                      "checker disagrees with the recorded verdicts; (c) the F2b file's declared f0_binding "
                      "hash no longer equals the measured canonical F0 hash; (d) any ledger ref status "
                      "changes; or (e) a strict duplicate-key parse of the same bytes exits 0 while F01 is "
                      "recorded. A revision after sha256_before is drift, not a falsifier of the snapshot."),
        "reproduce_command": (f"cd {root} && python3 {Path(__file__).resolve().relative_to(root)} "
                              f"--root {root} --out {Path(args.out)}"),
        "environment": {"python": sys.version.split()[0], "pyyaml": yaml.__version__,
                        "platform": platform.platform()},
        "no_completion_claim": ("worker-096 cannot set status=done, validation_status=passed, or any gate "
                                "verdict; this is a reviewer input, not a node transition"),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    print(json.dumps({k: report[k] for k in
                      ("report_id", "verdict", "score_0_5", "critical_failures", "major_failures",
                       "minor_failures", "checked_at")}, indent=1))
    print("target sha256_before:", sha_before)
    print("target sha256_after :", sha_after, "(drift)" if drift else "(stable)")
    print("report:", out)
    if critical_failed or drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
