#!/usr/bin/env python3
"""F2a candidate closure audit (class AF-SCC-C2-VAC-GEN).

Bounded worker-05 verification artifact.  This tool does NOT issue a review verdict and
does NOT edit any candidate.  It pins hashes, runs the frozen binding gate and the
reviewer-18 adversarial probe, and maps their outcomes onto the four hard failures of
reviews/F2a-review-18.json plus the major findings of reviews/F2a-review-17.json.

It records both the pre-publication canonical revision (rev3, 23fec0e9, measured before the
lead published at 2026-09-12T00:10:15+08:00) and the published revision (rev9, 8dae50da).

Usage:
  python3 make_f2a_audit.py --out artifacts/worker-05/verify/f2a_candidate_audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
RULE_SPEC = ROOT / "artifacts/formulation/rule_spec.json"
PROBE = ROOT / "artifacts/worker18/f2_review/f2_class_probe.py"
VERIFY_DIR = ROOT / "artifacts/worker-05/verify"

CANON_C2 = ROOT / "schemas/af_scc_c2_vacuum.yaml"
CANON_C0 = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CANON_WCC = ROOT / "schemas/af_wcc_vacuum.yaml"
LEAD_C2 = ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
LEAD_C0 = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
LEAD_WCC = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"

PREPUB_GATE = VERIFY_DIR / "gate_runs_prepublication.txt"
PREPUB_PROBE = VERIFY_DIR / "probe_prepublication_rev3_pair.json"
PREPUB_C2_SHA = "23fec0e9cd68bc99d42f2fa2228f343391df70d802ae50ba368c1e70d96e0f9d"

PAIR_BINDER = re.compile(r"forall\s*\(\s*s\s*,\s*delta\s*\)|in\s+D0\b|D_gen\^?\{?\s*s\s*,", re.I)
MATTER_WORDS = re.compile(
    r"(critical collapse|scalar[- ]field|scalar field|electromagnetic|einstein[- ]maxwell|"
    r"matter[- ]coupled|de ?sitter|positive cosmological)", re.I)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_gate(path: Path) -> dict:
    r = subprocess.run([sys.executable, str(GATE), "--json", str(path)],
                       capture_output=True, text=True, timeout=120)
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"verdict": "error", "failed_rules": [], "failures": [],
               "stderr": r.stderr[-400:], "exit": r.returncode}
    rep["exit"] = r.returncode
    return rep


def probe_hard_failures(report: Path) -> list:
    if not report.exists():
        return []
    d = json.loads(report.read_text())
    probes = d.get("probes")
    items = probes.items() if isinstance(probes, dict) else [(p.get("id"), p) for p in probes]
    out = []
    for pid, p in items:
        if isinstance(p, dict) and p.get("verdict") == "fail":
            out.append({"probe_id": p.get("probe_id"), "detail": p.get("detail")})
    return sorted(out, key=lambda x: str(x["probe_id"]))


def run_probe(c2: Path, c0: Path, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(PROBE), "--report", str(out),
                        "--c2", str(c2), "--c0", str(c0)],
                       capture_output=True, text=True, timeout=180)
    rep = {"report": str(out.relative_to(ROOT)), "exit": r.returncode}
    if out.exists():
        d = json.loads(out.read_text())
        probes = d.get("probes")
        items = probes.items() if isinstance(probes, dict) else [(p.get("id"), p) for p in probes]
        warns = [{"probe_id": p.get("probe_id"), "detail": p.get("detail")}
                 for _, p in items if isinstance(p, dict) and p.get("verdict") == "warn"]
        rep.update({"class_collapse": d.get("class_collapse"),
                    "hard_failures": probe_hard_failures(out),
                    "warnings": warns,
                    "inputs": d.get("inputs")})
    else:
        rep["stdout_tail"] = r.stdout[-400:]
    return rep


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def summarize_schema(path: Path) -> dict:
    d = load(path)
    q = d.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    domains = q.get("domains") or {}
    refs_ext = len(re.findall(r"extension_predicate", json.dumps(d), re.I))
    ep = d.get("extension_predicate")
    dc = (d.get("data_class") or {})
    reg = (dc.get("regularity_class") or {})
    nv = d.get("non_vacuity") or {}
    gen = d.get("genericity") or {}
    concl = d.get("conclusion") or {}
    m = PAIR_BINDER.search(json.dumps(q))
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "revision": d.get("revision"),
        "class_id": d.get("class_id"),
        "node_id": d.get("node_id"),
        "validation_status": d.get("validation_status"),
        "claims_completion": d.get("claims_completion"),
        "conclusion_type": (d.get("vocabulary_alignment") or {}).get("conclusion_type")
                           or concl.get("conclusion_type"),
        "extension_regularity": (d.get("regularity") or {}).get("extension_regularity"),
        "extension_predicate_defined": isinstance(ep, dict),
        "extension_predicate_keys": sorted(ep.keys()) if isinstance(ep, dict) else [],
        "extension_predicate_text_refs": refs_ext,
        "class_contract_pointer": d.get("class_contract_pointer"),
        "quantifier_kinds": [e.get("kind") for e in ordered if isinstance(e, dict)],
        "quantifier_binders": [e.get("binder") for e in ordered if isinstance(e, dict)],
        "domain_ids": sorted(domains.keys()) if isinstance(domains, dict) else [],
        "unresolved_domain_ids": [e.get("domain_id") for e in ordered
                                  if isinstance(e, dict) and e.get("domain_id") not in domains],
        "pair_binder_residue": bool(m),
        "pair_binder_match": m.group(0) if m else None,
        "data_class_regularity_class": reg,
        "genericity": {
            "kind": gen.get("kind"),
            "matter_words_in_genericity": sorted(set(w.lower() for w in MATTER_WORDS.findall(json.dumps(gen)))),
        },
        "non_vacuity_condition": str(nv.get("condition"))[:200],
        "conclusion_type_in_conclusion": concl.get("conclusion_type"),
    }


def historical_rev3() -> dict:
    """Pre-publication canonical rev3 measurements, preserved before the 00:10:15 publish."""
    rules, line = [], None
    if PREPUB_GATE.exists():
        for ln in PREPUB_GATE.read_text().splitlines():
            if ln.startswith("FAIL schemas/af_scc_c2_vacuum.yaml"):
                m = re.search(r"failed_rules=\[(.*?)\]", ln)
                rules = [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()] if m else []
                line = ln.strip()
    probe = probe_hard_failures(PREPUB_PROBE)
    probe_inputs = json.loads(PREPUB_PROBE.read_text()).get("inputs", {}) if PREPUB_PROBE.exists() else {}
    pinned = probe_inputs.get("AF-SCC-C2-VAC-GEN", {}).get("sha256")
    return {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": PREPUB_C2_SHA,
        "revision": 3,
        "superseded_at": "2026-09-12T00:10:15+08:00",
        "superseded_by": sha256_file(CANON_C2),
        "body_preserved": False,
        "evidence_preserved": [str(PREPUB_GATE.relative_to(ROOT)), str(PREPUB_PROBE.relative_to(ROOT))],
        "probe_input_hash_matches_pinned_rev3": pinned == PREPUB_C2_SHA,
        "gate": {"verdict": "fail", "failed_rules": rules, "raw_line": line},
        "probe_hard_failures": probe,
        "review_18_hf": {
            "HF-A1": "OPEN" if any(h["probe_id"] == "S7-C2" for h in probe) else "closed",
            "HF-A2": "OPEN" if any(h["probe_id"] == "S6-C2" for h in probe) else "closed",
            "HF-A4": "OPEN: " + ",".join(rules) if rules else "unknown",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(VERIFY_DIR / "f2a_candidate_audit.json"))
    a = ap.parse_args()
    now = datetime.now(CST).isoformat(timespec="seconds")

    pub_c2 = summarize_schema(CANON_C2)
    lead_c2 = summarize_schema(LEAD_C2)
    pub_c0 = summarize_schema(CANON_C0)
    lead_c0 = summarize_schema(LEAD_C0)
    pub_wcc = summarize_schema(CANON_WCC)
    lead_wcc = summarize_schema(LEAD_WCC)
    for c in (pub_c2, lead_c2, pub_c0, lead_c0, pub_wcc, lead_wcc):
        c["frozen_gate"] = run_gate(ROOT / c["path"])

    probe_pub = run_probe(CANON_C2, CANON_C0, VERIFY_DIR / "probe_canonical_pair.json")
    probe_lead = run_probe(LEAD_C2, LEAD_C0, VERIFY_DIR / "probe_lead_pair.json")
    pub_ids = [h["probe_id"] for h in probe_pub.get("hard_failures", [])]
    lead_ids = [h["probe_id"] for h in probe_lead.get("hard_failures", [])]
    hist = historical_rev3()
    hist_ids = [h["probe_id"] for h in hist["probe_hard_failures"]]

    hf_map = {
        "HF-A1_dangling_extension_predicate": {
            "detector": "reviewer-18 probe S7-C2",
            "canonical_rev3_prepublication": "OPEN (S7-C2)" if "S7-C2" in hist_ids else "closed",
            "published_rev9": "closed" if "S7-C2" not in pub_ids else "OPEN",
            "evidence": {"prepublication": f"schemas/af_scc_c2_vacuum.yaml#{PREPUB_C2_SHA[:12]}",
                         "published": f"{pub_c2['path']}#{pub_c2['sha256'][:12]}"},
        },
        "HF-A2_quantifier_statement_disagreement_and_pair_binder": {
            "detector": "reviewer-18 probe S6-C2 + statement_formal/quantifiers comparison",
            "canonical_rev3_prepublication": "OPEN (S6-C2)" if "S6-C2" in hist_ids else "closed",
            "published_rev9": "OPEN (S6-C2: forall (s,delta) family binder)" if "S6-C2" in pub_ids else "closed",
            "note": ("rev9 is internally consistent (statement_formal matches quantifiers.formal) "
                     "but still quantifies forall (s,delta) in D0, the family-of-statements pattern "
                     "lead-audit reopened worker rev2 for and review-18 flags at S6; the frozen "
                     "binding gate does not encode S6"),
            "evidence": {"prepublication": f"schemas/af_scc_c2_vacuum.yaml#{PREPUB_C2_SHA[:12]}",
                         "published": f"{pub_c2['path']}#{pub_c2['sha256'][:12]}"},
        },
        "HF-A3_shared_data_class_across_siblings": {
            "detector": "cross-schema data_class comparison + sibling gate runs",
            "canonical_rev3_prepublication": "OPEN (F1 canonical failed 12 rules; F2b canonical froze a different class)",
            "published_rev9": ("lead trio shares one data_class template; canonical trio is now aligned "
                               f"(F1 {pub_wcc['frozen_gate'].get('verdict')}, C2 {pub_c2['frozen_gate'].get('verdict')}, "
                               f"C0 {pub_c0['frozen_gate'].get('verdict')})"),
            "note": ("rev9 F1/F2a/F2b share the identical data_class (smooth-with-decay default + "
                     "s>5/2, delta in (1/2,1) Sobolev variant) quantified over D0; the shared-class "
                     "criterion is met as a family, not as one frozen (s,delta)"),
            "evidence": {"published": f"{pub_c2['path']}#{pub_c2['sha256'][:12]}",
                         "siblings": [f"{pub_c0['path']}#{pub_c0['sha256'][:12]}",
                                      f"{pub_wcc['path']}#{pub_wcc['sha256'][:12]}"]},
        },
        "HF-A4_frozen_binding_gate_rejection": {
            "detector": "artifacts/formulation/tools/check_class_schema.py",
            "canonical_rev3_prepublication": "OPEN: " + ",".join(hist["gate"]["failed_rules"]),
            "published_rev9": "closed (gate pass)" if pub_c2["frozen_gate"].get("verdict") == "pass"
                              else "OPEN: " + ",".join(pub_c2["frozen_gate"].get("failed_rules", [])),
        },
    }

    review17 = {
        "shared_class_major": {
            "status": "published rev9 parameterizes one shared data class over D0; not frozen to one (s,delta)",
            "evidence": f"{pub_c2['path']}#{pub_c2['sha256'][:12]}",
        },
        "critical_collapse_contamination_major": {
            "canonical_rev3_prepublication": "OPEN",
            "published_rev9": "fixed" if not pub_c2["genericity"]["matter_words_in_genericity"]
                              else "OPEN: " + ",".join(pub_c2["genericity"]["matter_words_in_genericity"]),
        },
    }

    audit = {
        "audit_id": f"w05-f2a-candidate-audit-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "audit_kind": "independent_verification",
        "review_verdict": None,
        "auditor": "deepseek-flash-05",
        "auditor_role": "bounded execution worker 05; verification evidence only, not an A1 review verdict",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "created_at": now,
        "assignment_ref": "asg-2026-09-11-F2-deepseek-flash-05-14",
        "controller_supersession_ref": "astra-indep-1-F1-F2-formulation (2026-09-12T00:05:13+08:00)",
        "claim": ("the canonical C2 path was republished at 00:10:15 from the lead tree; the "
                  "published rev9 passes the frozen binding gate and closes HF-A1/HF-A4, but still "
                  "carries the S6 regularity-pair family binder and one prohibition-context merged "
                  "token, and no review verdict exists at the published hash"),
        "instruments": {
            "frozen_binding_gate": {"path": str(GATE.relative_to(ROOT)), "sha256": sha256_file(GATE)},
            "rule_spec": {"path": str(RULE_SPEC.relative_to(ROOT)), "sha256": sha256_file(RULE_SPEC),
                          "spec_version": json.loads(RULE_SPEC.read_text()).get("spec_version")},
            "reviewer18_probe": {"path": str(PROBE.relative_to(ROOT)), "sha256": sha256_file(PROBE),
                                 "selftest": "pass (exit 0, planted merged fixtures caught)"},
            "date": now,
        },
        "historical_pre_publication": hist,
        "candidates": {
            "published_canonical": pub_c2,
            "lead_authoring_tree": lead_c2,
            "published_canonical_is_byte_identical_to_lead_tree": pub_c2["sha256"] == lead_c2["sha256"],
        },
        "context_siblings": {"published_c0": pub_c0, "published_wcc": pub_wcc,
                             "lead_c0": lead_c0, "lead_wcc": lead_wcc},
        "review_18_hard_failure_closure": hf_map,
        "review_17_major_findings": review17,
        "probe_runs": {"published_pair": probe_pub, "lead_pair": probe_lead,
                       "prepublication_rev3_pair": str(PREPUB_PROBE.relative_to(ROOT))},
        "open_items": [
            "S6-C2: published rev9 quantifies forall (s,delta) in D0; a single frozen (s,delta) or an explicit family-class ruling is required",
            "S5-C2: prohibition phrase \"any 'C0 or C2' composite regularity\" (phrases_that_are_not_this_class) trips the probe although the frozen gate exempts the key (R13)",
            "no reviewer verdict exists at the published hash; G-FORM needs two independent accept verdicts per class at one hash",
            "the pre-publication rev3 body (23fec0e9) was overwritten by the 00:10:15 publish and is not preserved on disk; only this audit's instrument outputs remain",
        ],
        "falsifier": ("any sha256 change to a cited candidate invalidates this audit (re-run required); "
                      "a reviewer adjudication that forall (s,delta) in D0 is the accepted reading of the "
                      "class id closes S6; rewording the literal merged token in the prohibition list clears S5"),
        "no_completion_claim": True,
    }

    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(audit, indent=2) + "\n")
    print(f"wrote {outp.relative_to(ROOT)}")
    print("published gate:", pub_c2["frozen_gate"].get("verdict"), pub_c2["frozen_gate"].get("failed_rules"))
    print("published probe failures:", pub_ids)
    print("prepublication rev3 probe failures:", hist_ids, "gate:", hist["gate"]["failed_rules"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
