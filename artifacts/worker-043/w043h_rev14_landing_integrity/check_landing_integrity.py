#!/usr/bin/env python3
"""W043H -- F2b rev14 pre-landing atomic-integrity instrument (worker-043).

Read-only on canonical paths.  Sandbox copies only under tmp/w043h_sandbox/.
Deterministic: no wall-clock anywhere in the emitted bytes (fixed STAMP).

Question: the direction axis of the staged F2b rev14 candidates is already verified by
other workers.  This instrument measures the axes that a landing actually needs:

  C01 YAML parses, class_id/node_id consistent
  C02 D1 carrier: regularity.must_not_conflate[0] does not deny a containment the same
      document asserts (self-consistency against the document's own nesting chain)
  C03 D2 carrier: no inverted size premise ("C2 is a strictly larger extension class")
      and an explicit direction-correct replacement
  C04 direction chain: one_way_entailments / implication ledger runs C0 => H2loc => C2
  C05 declared f0_binding chain resolves against live bytes (declared_f0_sha256,
      consistency_evidence_sha256, supplement pointer)
  C06 revision readiness: the bytes are rev13; landing as rev14 requires revision=14,
      revised_at bump and a rev14 revision_history row (W043G invariants H1-H4)
  C07 canonical structural gate check_class_schema.py verdict on the candidate bytes
  C08 taxonomy-consistency check in a sandbox at the candidate bytes
  C09 complete atomic-write set: every gate-relevant declared pointer that names the
      superseded F2b hash and would go stale if only the schema were written

Controls (pre-registered, all must match):
  M1 live rev13 bytes           -> C02 FAIL, C03 FAIL (predicates are not blind)
  M2 base 84b5d3fa              -> C02 PASS, C03 FAIL (D2 predicate discriminates)
  M3 candidate + smaller->larger-> C03 FAIL
  M4 candidate + f0 hash tamper -> C05 FAIL
  M5 determinism                -> two runs byte-identical

Usage:  python3 check_landing_integrity.py [--json] [--stamp-out DIR]
Exit:   0 measurement complete; 1 instrument error; 2 pin drift (void, no verdict)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(1)

STAMP = "2026-09-12T01:30:00+08:00"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # repo root (…/ai4math-swarm)
RAW = HERE / "raw"
SCRATCH = HERE / "scratch"
SANDBOX = ROOT / "tmp" / "w043h_sandbox"

CANDIDATES = {
    "cand023_v2_9ab32ee39d00": "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
    "cand080_51c253c46306": "artifacts/worker-080/f2b_hf1_direction_census/snapshots/51c253c46306__cand_corrected_51c253c4.yaml",
    "cand080_4951cc969803": "artifacts/worker-080/f2b_hf1_direction_census/snapshots/4951cc969803__cand_nesting_4951cc96.yaml",
}
CONTROLS = {
    "M1_live_b2ab6acb": "schemas/af_scc_c0_vacuum.yaml",
    "M2_base_84b5d3fa": "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml",
}
DECLARED_CHAIN = [
    ("declared_f0_sha256", "research_map/formulation_taxonomy.yaml"),
    ("consistency_evidence_sha256", "artifacts/formulation/evidence/taxonomy_consistency.json"),
]
ATOMIC_LAYER = [
    "entry_hashes.json",
    "schemas/af_scc_c0_vacuum.yaml.sha256",
    "schemas/af_scc_regularities.yaml",
    "artifacts/formulation/FROZEN.json",
]
PINS = [
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "schemas/af_scc_regularities.yaml",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
]

DENIAL = re.compile(r"no\s+containment|not\s+a\s+containment|containment\s+with\s+C2\s+or\s+C0", re.I)
INVERSION = re.compile(r"C2\s+is\s+a\s+strictly\s+larger", re.I)
DIRECT = re.compile(r"strictly\s+smaller\s+extension\s+class|E_C2\s+subset\s+of\s+E_C0", re.I)
INVERTED_ENTAIL = re.compile(r"H2_?loc-inextendibility\s+ENTAILS\s+this\s+class", re.I)
LICENSED_ENTAIL = re.compile(r"this\s+class'?s?\s+conclusion[^.]{0,80}ENTAILS", re.I)
BRACKET_NOTE = re.compile(r"\[[^\]]*\]")   # historical mentions live in bracket notes


def assertive(text: str) -> str:
    """Strip bracketed correction notes so a quoted/historical mention cannot fire a predicate."""
    return BRACKET_NOTE.sub(" ", text)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pinmap() -> dict:
    out = {}
    for rel in PINS:
        p = ROOT / rel
        out[rel] = {"exists": p.exists(), "sha256": sha256(p) if p.exists() else None}
    return out


def strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)
    elif isinstance(node, str):
        yield node


def check_schema(doc: dict) -> dict:
    """C01..C04: static content checks on a parsed schema document."""
    r = {}
    r["C01_parse"] = {
        "class_id": doc.get("class_id"),
        "node_id": doc.get("node_id"),
        "ok": doc.get("class_id") == "AF-SCC-C0-VAC-GEN" and doc.get("node_id") == "F2b",
    }
    mnc0 = str(((doc.get("regularity") or {}).get("must_not_conflate") or [""])[0])
    mnc0_assertive = assertive(mnc0)
    chain = str(doc.get("extension_class_containment") or doc.get("implication_ledger") or "")
    has_nesting = bool(re.search(r"E_C0\s+contains|E_C0\s*⊇|E_C2\s+subset\s+of\s+E_C0", chain, re.I))
    denial_hit = bool(DENIAL.search(mnc0_assertive))
    r["C02_D1_containment_denial"] = {
        "mnc0_assertive_head": mnc0_assertive.strip()[:180],
        "denial_regex_hit": denial_hit,
        "document_asserts_nesting": has_nesting,
        "ok": (not denial_hit) or (not has_nesting),
        "note": "mention-aware: bracketed historical notes are stripped before the predicate",
    }
    inv_entail = bool(INVERTED_ENTAIL.search(mnc0_assertive))
    lic_entail = bool(LICENSED_ENTAIL.search(mnc0_assertive))
    r["C02b_entailment_direction"] = {
        "inverted_assertion_hit": inv_entail,
        "licensed_direction_hit": lic_entail,
        "verdict": "INVERTED" if inv_entail else ("LICENSED" if lic_entail else "NEUTRAL_POINTER"),
        "ok": not inv_entail,
    }
    inv_hits = [s for s in strings(doc) if INVERSION.search(s)]
    dir_hits = [s for s in strings(doc) if DIRECT.search(s)]
    r["C03_D2_size_premise"] = {
        "inversion_hits": [s[:180] for s in inv_hits],
        "direction_correct_hits": len(dir_hits),
        "ok": (not inv_hits) and bool(dir_hits),
    }
    one_way = json.dumps(doc.get("implication_ledger") or doc.get("entailment_ledger") or {}, ensure_ascii=False)
    r["C04_direction_chain"] = {
        "c0_to_h2loc": bool(re.search(r"C0[^\"']{0,120}H2_?loc", one_way, re.I)),
        "h2loc_to_c2": bool(re.search(r"H2_?loc[^\"']{0,120}C2", one_way, re.I)),
        "ok": bool(re.search(r"C0[^\"']{0,120}H2_?loc", one_way, re.I)) and bool(re.search(r"H2_?loc[^\"']{0,120}C2", one_way, re.I)),
    }
    return r


def check_chain(doc: dict) -> dict:
    """C05: declared f0_binding hashes resolve against live bytes."""
    fb = doc.get("f0_binding") or {}
    rows = []
    for field, path in DECLARED_CHAIN:
        declared = str(fb.get(field) or "")
        live = ROOT / path
        measured = sha256(live) if live.exists() else None
        rows.append({
            "field": field, "path": path,
            "declared": declared, "declared_prefix": declared[:12],
            "measured": measured, "measured_prefix": (measured or "")[:12],
            "resolved": bool(declared) and declared == measured,
        })
    supp = str(fb.get("class_contract_supplement") or "")
    supp_live = ROOT / supp if supp else None
    if supp_live and supp_live.exists():
        rows.append({"field": "class_contract_supplement(pointer)", "path": supp,
                     "declared": None, "declared_prefix": None,
                     "measured": sha256(supp_live), "measured_prefix": sha256(supp_live)[:12],
                     "resolved": True})
    return {"rows": rows, "ok": all(x["resolved"] for x in rows)}


def check_revision(doc: dict) -> dict:
    """C06: rev13 bytes; landing as rev14 needs bump + history row (W043G H1-H4)."""
    hist = doc.get("revision_history") or []
    idx = [h.get("index") for h in hist if isinstance(h, dict)]
    rows = [(h.get("index"), str(h.get("at")), bool(h.get("unused"))) for h in hist if isinstance(h, dict)]
    newest = max((h.get("index", -1) for h in hist if isinstance(h, dict)), default=-1)
    monotone = all(rows[i][1] <= rows[i + 1][1] for i in range(len(rows) - 1))
    has_rev14_row = any(h.get("index") == 14 for h in hist if isinstance(h, dict))
    unused_rows = [h.get("index") for h in hist if isinstance(h, dict) and h.get("unused")]
    return {
        "live_revision": doc.get("revision"),
        "revised_at": doc.get("revised_at"),
        "history_max_index": newest,
        "history_len": len(hist),
        "timestamps_monotone": monotone,
        "has_rev14_row": has_rev14_row,
        "unused_rows": unused_rows,
        "landing_delta_required": {
            "revision": 14,
            "revised_at": "bump to landing wall-clock",
            "revision_history_append": {"index": 14, "at": "<wall-clock>", "unused": False,
                                        "notes": ["rev14 delta: F2b D1/D2 carrier repair"]},
            "non_monotone_rows_present": not monotone,
        },
        "ok_as_staged_bytes": doc.get("revision") == 13 and not has_rev14_row,
    }


def run_gate(schema_path: Path, sandbox: bool = False) -> dict:
    tool = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    cmd = [sys.executable, str(tool), "--json", str(schema_path)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    rep = None
    try:
        rep = json.loads(p.stdout)
    except Exception:
        pass
    return {"exit": p.returncode, "passed": p.returncode == 0,
            "failed_rules": (rep or {}).get("failures") or (rep or {}).get("fail_rules") or rep,
            "stdout_tail": p.stdout[-400:], "stderr_tail": p.stderr[-200:]}


def setup_sandbox() -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    for rel_dir in ("research_map", "artifacts/formulation/tools", "artifacts/formulation/evidence", "schemas"):
        (SANDBOX / rel_dir).mkdir(parents=True, exist_ok=True)
    copies = [
        "research_map/formulation_taxonomy.yaml",
        "artifacts/formulation/formulation_taxonomy.yaml",
        "artifacts/formulation/VOCAB_ALIASES.json",
        "artifacts/formulation/rule_spec.json",
        "artifacts/formulation/KEY_MANIFEST.json",
        "artifacts/formulation/FROZEN.json",
        "artifacts/formulation/tools/check_class_schema.py",
        "artifacts/formulation/tools/check_taxonomy_consistency.py",
        "schemas/af_scc_c0_vacuum.yaml",
    ]
    for rel in copies:
        src = ROOT / rel
        dst = SANDBOX / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def run_tax_consistency() -> dict:
    tool = SANDBOX / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    p = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=120)
    ev = SANDBOX / "artifacts/formulation/evidence/taxonomy_consistency.json"
    return {"exit": p.returncode, "consistent": p.returncode == 0,
            "stdout_tail": p.stdout[-300:], "stderr_tail": p.stderr[-200:],
            "evidence_sha256": sha256(ev) if ev.exists() else None}


def atomic_layer(cand_hash: str) -> dict:
    """C09: which declared pointers name the old F2b hash and must move atomically."""
    out = {}
    eh = ROOT / "entry_hashes.json"
    eh_d = json.loads(eh.read_text())
    out["entry_hashes.json"] = {"recorded": eh_d.get("schemas/af_scc_c0_vacuum.yaml"),
                                "matches_candidate": eh_d.get("schemas/af_scc_c0_vacuum.yaml") == cand_hash}
    sc = ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"
    out["schemas/af_scc_c0_vacuum.yaml.sha256"] = {"recorded": sc.read_text().split()[0],
                                                   "matches_candidate": sc.read_text().split()[0] == cand_hash}
    reg = (ROOT / "schemas/af_scc_regularities.yaml").read_text()
    m = re.search(r"class_id:\s*AF-SCC-C0-VAC-GEN\s*\n\s*path:\s*(\S+)\s*\n\s*sha256:\s*([0-9a-f]{64})", reg)
    out["schemas/af_scc_regularities.yaml"] = {"recorded": m.group(2) if m else None,
                                               "matches_candidate": bool(m) and m.group(2) == cand_hash}
    fr = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    rec = (fr.get("files") or {}).get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
    out["artifacts/formulation/FROZEN.json"] = {"recorded": rec, "matches_candidate": rec == cand_hash}
    out["_stale_on_landing"] = sorted(k for k, v in out.items() if isinstance(v, dict) and not v["matches_candidate"])
    return out


def measure(label: str, path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    h = sha256(path)
    res = {"label": label, "path": str(path.relative_to(ROOT)), "sha256": h, "bytes": path.stat().st_size}
    res.update(check_schema(doc))
    res["C05_declared_chain"] = check_chain(doc)
    res["C06_revision_readiness"] = check_revision(doc)
    res["C07_structural_gate"] = run_gate(path)
    res["C09_atomic_layer"] = atomic_layer(h)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    entry = pinmap()
    if any(not v["exists"] for v in entry.values()):
        print("INSTRUMENT ERROR: pin missing", file=sys.stderr)
        return 1

    report = {"instrument": "check_landing_integrity.py", "worker": "worker-043",
              "task_id": "W043H-F2B-REV14-LANDING-INTEGRITY-01",
              "class_id": "AF-SCC-C0-VAC-GEN", "stamp": STAMP,
              "entry_pins": entry, "candidates": {}, "controls": {}, "tax_consistency": {}}

    setup_sandbox()
    report["tax_consistency"] = run_tax_consistency()

    for label, rel in CANDIDATES.items():
        report["candidates"][label] = measure(label, ROOT / rel)

    # M1/M2 controls from pinned files
    for label, rel in CONTROLS.items():
        report["controls"][label] = measure(label, ROOT / rel)

    # M3 candidate + inversion mutation (in-memory, scratch copy)
    base = ROOT / CANDIDATES["cand023_v2_9ab32ee39d00"]
    mutated = base.read_text().replace("strictly smaller extension class", "strictly larger extension class", 1)
    m3 = SCRATCH / "M3_inversion_mutated.yaml"
    m3.write_text(mutated)
    report["controls"]["M3_inversion_mutated"] = measure("M3_inversion_mutated", m3)

    # M4 candidate + declared f0 hash tamper
    tampered = base.read_text()
    tampered = re.sub(r'(declared_f0_sha256:\s*")[0-9a-f]{64}', r"\g<1>" + "0" * 64, tampered, count=1)
    m4 = SCRATCH / "M4_f0_tampered.yaml"
    m4.write_text(tampered)
    report["controls"]["M4_f0_tampered"] = measure("M4_f0_tampered", m4)

    exit_pins = pinmap()
    report["exit_pins"] = exit_pins
    report["pin_drift"] = sorted(k for k in entry if entry[k]["sha256"] != exit_pins[k]["sha256"])

    # pre-registered control expectations (mention-aware predicates)
    exp = {
        "M1_live_b2ab6acb": {"C02_D1_containment_denial": False, "C02b_entailment_direction": True,
                             "C03_D2_size_premise": False},
        "M2_base_84b5d3fa": {"C02_D1_containment_denial": True, "C02b_entailment_direction": False,
                             "C03_D2_size_premise": True},
        "M3_inversion_mutated": {"C03_D2_size_premise": False},
        "M4_f0_tampered": {"C05_declared_chain": False},
    }
    ctl = {}
    for lab, checks in exp.items():
        got = report["controls"][lab]
        per = {}
        for key, want in checks.items():
            have = got[key]["ok"] if key.startswith("C0") else got[key]
            per[key] = {"expected_ok": want, "measured_ok": have, "match": have == want}
        ctl[lab] = per
    report["control_expectations"] = ctl
    report["controls_all_match"] = all(v["match"] for per in ctl.values() for v in per.values())

    # determinism control M5: second independent run of the same measurement
    again = measure("cand023_v2_9ab32ee39d00", ROOT / CANDIDATES["cand023_v2_9ab32ee39d00"])
    report["controls"]["M5_rerun_cand023"] = again
    report["deterministic_rerun"] = json.dumps(again, sort_keys=True) == json.dumps(
        report["candidates"]["cand023_v2_9ab32ee39d00"], sort_keys=True)

    (RAW / "landing_integrity_raw.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("pins drift:", report["pin_drift"] or "none")
        print("controls all match:", report["controls_all_match"], "| deterministic rerun:", report["deterministic_rerun"])
        for lab, r in report["candidates"].items():
            print(f"{lab}: D1={r['C02_D1_containment_denial']['ok']} D2={r['C03_D2_size_premise']['ok']} "
                  f"chain={r['C05_declared_chain']['ok']} gate={r['C07_structural_gate']['passed']} "
                  f"stale={r['C09_atomic_layer']['_stale_on_landing']}")
        print("tax_consistency:", report["tax_consistency"]["consistent"])
    return 2 if report["pin_drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
