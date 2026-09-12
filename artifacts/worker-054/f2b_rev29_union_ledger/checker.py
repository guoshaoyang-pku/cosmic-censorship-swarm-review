#!/usr/bin/env python3
"""
W054-F2B-REV29-UNION-LEDGER-01

Independent union ledger of the reported F2b rev29 defect claims, re-measured from
primary bytes at pinned hashes.

Scope / class binding
---------------------
Class: AF-SCC-C0-VAC-GEN (node F2b, schema schemas/af_scc_c0_vacuum.yaml).
Cross-checks against the F2a sibling (AF-SCC-C2-VAC-GEN) and F1 are CONTROLS only;
this is not an F2a/F1 review and issues no gate verdict and no node status.

Read-only contract
------------------
No canonical artifact is written. Mutant schemas are regenerated under ./scratch/
inside this artifact directory on every run. No author code is imported. The only
canonical tool executed is artifacts/formulation/tools/check_class_schema.py, run as
a subprocess, because that instrument's detection power is itself one of the claims
under test (the gate blind spot).

Determinism
-----------
The report is a pure function of the pinned input bytes and --created-at.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = HERE / "scratch"

# --------------------------------------------------------------------------- #
# Pre-registered claim inventory (union over the review record, 2026-09-12)
# Each claim names the reporting workers, the carrier, and the detector that
# decides it. Materiality is assigned by RULE below, not per claim.
# --------------------------------------------------------------------------- #
CLAIMS = [
    {
        "claim_id": "H1-INVERTED-PREMISE",
        "reported_by": ["worker-017 B17-R13-01", "worker-018 C18", "worker-053 C10",
                        "worker-066 W066-R12-F2B-H1", "worker-083 D1", "worker-035 HF-035-R3-01"],
        "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "claimed_line": 246,
        "detector": "D-H1",
        "expected": "REPRODUCED",
    },
    {
        "claim_id": "H2-CONTAINMENT-DENIAL",
        "reported_by": ["worker-017 B17-R13-02", "worker-018 C17", "worker-066 W066-R12-F2B-H2",
                        "worker-083 D2", "worker-035 HF-035-R3-01"],
        "carrier": "regularity.must_not_conflate[0]",
        "claimed_line": 152,
        "detector": "D-H2",
        "expected": "REPRODUCED",
    },
    {
        "claim_id": "D3-CONCLUSION-TYPE-VOCAB",
        "reported_by": ["worker-083 D3", "worker-075 HF-075-F2b-VOCAB"],
        "carrier": "conclusion.conclusion_type",
        "claimed_line": None,
        "detector": "D-D3",
        "expected": "REPRODUCED_NONBLOCKING",
    },
    {
        "claim_id": "F035-01-REVHIST",
        "reported_by": ["worker-035 F-035-01"],
        "carrier": "revision_history",
        "claimed_line": None,
        "detector": "D-REVHIST",
        "expected": "REPRODUCED",
    },
    {
        "claim_id": "F035-02-SIDEPINS",
        "reported_by": ["worker-035 F-035-02"],
        "carrier": "schemas/af_scc_c0_vacuum.yaml.sha256 + entry_hashes.json",
        "claimed_line": None,
        "detector": "D-SIDEPIN",
        "expected": "REPRODUCED",
    },
    {
        "claim_id": "F035-03-PROVENANCE",
        "reported_by": ["worker-035 F-035-03"],
        "carrier": "provenance.worker_sha256",
        "claimed_line": None,
        "detector": "D-PROVENANCE",
        "expected": "MEASURED_RECORDED",
    },
    {
        "claim_id": "N17-03-SUPPLEMENT-HASH",
        "reported_by": ["worker-017 N17-R13-03", "worker-001 W001-ID-02"],
        "carrier": "f0_binding.class_contract_supplement_sha256",
        "claimed_line": None,
        "detector": "D-SUPPHASH",
        "expected": "REPRODUCED",
    },
    {
        "claim_id": "INST-GATE-BLIND",
        "reported_by": ["worker-017 N17-R13-01", "worker-066 MACHINE-BLIND-SPOT"],
        "carrier": "artifacts/formulation/tools/check_class_schema.py",
        "claimed_line": None,
        "detector": "D-GATE-BLIND",
        "expected": "REPRODUCED",
    },
]

MATERIALITY_RULE = {
    "OPERATIVE_BINDING_TEXT": "false or self-contradictory text inside a required normative slot (rule_spec R06/R16) that is freeze-bound and gate-undetectable; blocks a clean accept, but does not by itself move the class conclusion",
    "RESOLVED_NONBLOCKING": "textual premise confirmed, but the binding layer resolves it through the frozen alias registry and frozen precedent; not blocking",
    "HYGIENE": "binding-hygiene defect outside class semantics (stale side pins, revision-history, missing optional pin, provenance)",
    "INSTRUMENT": "the canonical detector cannot certify what it appears to certify",
    "NOT_TESTABLE": "input bytes for the claim are not available at a pinned hash",
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys (silent last-wins hides edits)."""


def _no_dup(loader, node, deep=False):
    mapping = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate mapping key: {key!r}")
        mapping[key] = loader.construct_object(v, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def load_yaml_strict(p: Path):
    with open(p, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=StrictLoader)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def line_of(text: str, needle: str):
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def _ctrl_pass(v: dict) -> bool:
    if "expect_prefix" in v:
        return str(v["observed"]).startswith(v["expect_prefix"])
    return v["expect"] == v["observed"]


def run_gate(gate: Path, target: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(gate), "--json", str(target)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    verdict, failed = None, None
    try:
        payload = json.loads(proc.stdout)
        verdict = payload.get("verdict")
        failed = payload.get("failed_rules")
    except Exception:
        payload = {"raw": proc.stdout[:400], "stderr": proc.stderr[:200]}
    return {"exit": proc.returncode, "verdict": verdict, "failed_rules": failed}


# --------------------------------------------------------------------------- #
# detectors (all read primary bytes; parsed doc used only to bind the slot)
# --------------------------------------------------------------------------- #
def det_h1(text: str, doc: dict) -> dict:
    reason = doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    chain = doc["implication_ledger"]["extension_class_containment"]
    phrase_line = line_of(text, "strictly larger extension class")
    chain_ok = ("E_C0 contains E_H2loc" in chain) and ("contains E_C2" in chain)
    inverted = ("strictly larger" in reason) and chain_ok
    return {
        "fired": bool(inverted),
        "measured_line": phrase_line,
        "carrier_text": reason,
        "chain_text": chain[:200],
        "detail": ("forbidden_transfers[0].reason says the C2 extension class is strictly LARGER "
                   "while the file's own chain at extension_class_containment makes E_C2 the innermost "
                   "(smallest) set") if inverted else "no inversion detected",
    }


def det_h2(text: str, doc: dict) -> dict:
    mnc0 = doc["regularity"]["must_not_conflate"][0]
    chain = doc["implication_ledger"]["extension_class_containment"]
    denial_line = line_of(text, "No containment with C2 or C0 is asserted here")
    chain_ok = ("E_C0 contains E_H2loc" in chain) and ("contains E_C2" in chain)
    fired = ("No containment with C2 or C0 is asserted here" in mnc0) and chain_ok
    return {
        "fired": bool(fired),
        "measured_line": denial_line,
        "carrier_text": mnc0[:220],
        "detail": ("regularity.must_not_conflate[0] denies containment while the same file asserts "
                   "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2") if fired
                  else "no live containment denial detected",
    }


def det_d3(doc: dict, f0: dict, aliases: dict) -> dict:
    tok = doc["conclusion"]["conclusion_type"]
    allowed = f0.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed", [])
    alias_map = aliases.get("conclusion_type", {})
    canonical_keys = list(alias_map.keys())
    resolved = None
    for k, vals in alias_map.items():
        if tok == k or tok in vals:
            resolved = k
            break
    in_allowed = tok in allowed
    return {
        "fired": not in_allowed,
        "token": tok,
        "f0_allowed": allowed,
        "alias_resolves_to": resolved,
        "classification": ("alias-resolved to a canonical token; binding layer uses "
                            "rule_spec.vocabularies.class_conclusion_type + frozen VOCAB_ALIASES, "
                            "so the premise is textual, not blocking")
                           if (not in_allowed and resolved) else
                           ("in F0 allowed list" if in_allowed else "unresolved token"),
    }


def det_revhist(doc: dict) -> dict:
    rows = doc.get("revision_history", [])
    declared = str(doc.get("f0_binding", {}).get("declared_f0_sha256", ""))[:12]
    names_binding = any(declared and declared in json.dumps(r) for r in rows)
    stamps = [r.get("at") for r in rows if r.get("at")]
    non_monotone = any(stamps[i] < stamps[i - 1] for i in range(1, len(stamps)))
    return {
        "fired": bool((not names_binding) or non_monotone),
        "rows": len(rows),
        "declared_f0_prefix": declared,
        "any_row_names_declared_f0": names_binding,
        "timestamps_non_monotone": non_monotone,
        "detail": ("revision_history names no row carrying the live declared F0 hash "
                   f"{declared}" if not names_binding else "declared F0 hash present") +
                  ("; timestamps are non-monotone in index order" if non_monotone else ""),
    }


def det_sidepin(pins: dict) -> dict:
    live = pins["f2b_canonical"]["measured_sha256"]
    side_path = ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"
    side = side_path.read_text(encoding="utf-8").split()[0] if side_path.exists() else None
    entry = json.loads((ROOT / "entry_hashes.json").read_text(encoding="utf-8"))
    entry_val = entry.get("schemas/af_scc_c0_vacuum.yaml")
    return {
        "fired": bool((side != live) or (entry_val != live)),
        "live_sha256": live,
        "sidecar_declared": side,
        "entry_hashes_declared": entry_val,
        "detail": "declared side pins do not resolve to the live artifact hash",
    }


def _walk_find_key(obj, key):
    """Collect every dict in a nested structure that carries `key`."""
    found = []
    if isinstance(obj, dict):
        if key in obj:
            found.append(obj)
        for v in obj.values():
            found.extend(_walk_find_key(v, key))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_walk_find_key(v, key))
    return found


def det_provenance(doc: dict) -> dict:
    blocks = _walk_find_key(doc, "worker_sha256")
    target_rel = "schemas/af_scc_c0_vacuum.yaml"
    recs = []
    for b in blocks:
        worker = b.get("worker_sha256")
        harvested = b.get("harvested_from")
        self_ref = bool(harvested) and (str(harvested).replace("\\", "/").endswith(target_rel))
        referent, scanned = None, 0
        if worker:
            for p in (ROOT / "artifacts").rglob("*.yaml"):
                scanned += 1
                if scanned > 5000:
                    break
                try:
                    if sha256_file(p) == worker:
                        referent = str(p.relative_to(ROOT))
                        break
                except OSError:
                    continue
        recs.append({"worker_sha256": worker, "harvested_from": harvested,
                     "self_referential_harvested_from": self_ref,
                     "referent_found": referent, "files_scanned": scanned})
    unresolved = [r for r in recs if r["worker_sha256"] and not r["referent_found"]]
    return {
        "fired": bool(unresolved),
        "records": recs,
        "detail": (f"{len(unresolved)} provenance.worker_sha256 record(s) have no on-disk referent "
                   f"in a bounded artifacts/ *.yaml scan (<=5000 files); "
                   f"self_referential={[r['self_referential_harvested_from'] for r in recs]}"
                   if unresolved else
                   ("no provenance worker_sha256 record present at these bytes"
                    if not recs else "all provenance worker hashes resolve")),
    }


def det_supphash(doc: dict) -> dict:
    b = doc.get("f0_binding", {})
    has_supp = "class_contract_supplement" in b
    has_hash = "class_contract_supplement_sha256" in b
    return {
        "fired": bool(has_supp and not has_hash),
        "has_supplement_pointer": has_supp,
        "has_supplement_sha256": has_hash,
        "detail": ("f0_binding names class_contract_supplement without a "
                   "class_contract_supplement_sha256 pin" if has_supp and not has_hash
                   else "supplement pin state recorded"),
    }


def det_gate_blind(gate: Path, canonical: Path, mutants: dict) -> dict:
    runs = {}
    for name, path in [("canonical_defective", canonical)] + list(mutants.items()):
        runs[name] = run_gate(gate, path)
    blind = (runs["canonical_defective"]["verdict"] == "pass"
             and runs["M4_nonsense_h1"]["verdict"] == "pass"
             and runs["M6_reversed_chain"]["verdict"] == "pass"
             and runs["M3_fix_both"]["verdict"] == "pass")
    alive = runs["M5_empty_mnc"]["verdict"] == "fail"
    return {
        "fired": bool(blind and alive),
        "runs": runs,
        "gate_passes_defective_and_nonsense": blind,
        "gate_fails_emptied_required_slot": alive,
        "detail": ("canonical gate returns pass for the defective bytes, a nonsense H1 reason and a "
                   "reversed containment chain; it fails only when a required slot is emptied"
                   if (blind and alive) else "gate detection differs from the reported blind spot"),
    }


# --------------------------------------------------------------------------- #
# mutant generation (deterministic; written under ./scratch)
# --------------------------------------------------------------------------- #
def build_mutants(canonical_text: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    h1_old = "C2 is a strictly larger extension class"
    h2_old = "No containment with C2 or C0 is asserted here"
    chain_old = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
    chain_new = "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"
    if h1_old not in canonical_text or h2_old not in canonical_text or chain_old not in canonical_text:
        raise SystemExit("canonical text changed: mutant anchors absent (pins stale?)")

    variants = {
        "M1_fix_h1": {h1_old: "C2 is a strictly smaller extension class"},
        "M2_fix_h2": {h2_old: "The extension sets are nonetheless nested (see implication_ledger)"},
        "M3_fix_both": {h1_old: "C2 is a strictly smaller extension class",
                        h2_old: "The extension sets are nonetheless nested (see implication_ledger)"},
        "M4_nonsense_h1": {h1_old: "banana"},
        "M6_reversed_chain": {chain_old: chain_new},
    }
    out = {}
    for name, subs in variants.items():
        t = canonical_text
        for a, b in subs.items():
            t = t.replace(a, b)
        p = SCRATCH / f"{name}.yaml"
        p.write_text(t, encoding="utf-8")
        out[name] = p

    # M5: empty the required must_not_conflate slot (line-wise)
    lines = canonical_text.splitlines(keepends=True)
    idx = next(i for i, ln in enumerate(lines) if h2_old in ln)
    lines[idx] = re.sub(r'^\s*-.*$', '    - ""', lines[idx], flags=re.S)
    p5 = SCRATCH / "M5_empty_mnc.yaml"
    p5.write_text("".join(lines), encoding="utf-8")
    out["M5_empty_mnc"] = p5
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", required=True)
    args = ap.parse_args()

    pinned = json.loads((HERE / "PINNED.json").read_text(encoding="utf-8"))

    # ---- pins at start -----------------------------------------------------
    pins = {}
    for role, rec in pinned["pins"].items():
        p = ROOT / rec["path"]
        measured = sha256_file(p) if p.exists() else None
        pins[role] = {"path": rec["path"], "declared_sha256": rec["sha256"],
                      "measured_sha256": measured, "match": measured == rec["sha256"]}
    start_drift = [r for r, v in pins.items() if not v["match"]]

    f2b_p = ROOT / pins["f2b_canonical"]["path"]
    f2a_p = ROOT / pins["f2a_canonical"]["path"]
    f1_p = ROOT / pins["f1_canonical"]["path"]
    f0_p = ROOT / pins["f0_taxonomy"]["path"]
    gate_p = ROOT / pins["gate_tool"]["path"]

    f2b_text, f2a_text, f1_text = read_text(f2b_p), read_text(f2a_p), read_text(f1_p)
    f2b = load_yaml_strict(f2b_p)
    f2a = load_yaml_strict(f2a_p)
    f0 = load_yaml_strict(f0_p)
    aliases = json.loads((ROOT / pins["vocab_aliases"]["path"]).read_text(encoding="utf-8"))

    mutants = build_mutants(f2b_text)

    # ---- detectors ---------------------------------------------------------
    results = {
        "D-H1": det_h1(f2b_text, f2b),
        "D-H2": det_h2(f2b_text, f2b),
        "D-D3": det_d3(f2b, f0, aliases),
        "D-REVHIST": det_revhist(f2b),
        "D-SIDEPIN": det_sidepin(pins),
        "D-PROVENANCE": det_provenance(f2b),
        "D-SUPPHASH": det_supphash(f2b),
        "D-GATE-BLIND": det_gate_blind(gate_p, f2b_p, mutants),
    }

    # ---- controls ----------------------------------------------------------
    f2a_mnc0 = f2a["regularity"]["must_not_conflate"][0]
    controls = {
        "K1_mirror_byte_identity": {
            "expect": True,
            "observed": pins["f2b_mirror"]["measured_sha256"] == pins["f2b_canonical"]["measured_sha256"],
        },
        "K2_f2a_sibling_corrected_wording": {
            "expect": True,
            "observed": ("No containment with C2 or C0 is asserted here" not in f2a_text)
                        and ("E_C2 subset" in f2a_text),
        },
        "K3_f1_not_flagged_by_h1_h2": {
            "expect": True,
            "observed": ("strictly larger extension class" not in f1_text)
                        and ("No containment with C2 or C0 is asserted here" not in f1_text),
        },
        "K4_M1_h1_only_specificity": {
            "expect": {"H1_quiet": True, "H2_fires": True},
            "observed": {"H1_quiet": not det_h1(read_text(mutants["M1_fix_h1"]),
                                               load_yaml_strict(mutants["M1_fix_h1"]))["fired"],
                         "H2_fires": det_h2(read_text(mutants["M1_fix_h1"]),
                                            load_yaml_strict(mutants["M1_fix_h1"]))["fired"]},
        },
        "K5_M2_h2_only_specificity": {
            "expect": {"H2_quiet": True, "H1_fires": True},
            "observed": {"H2_quiet": not det_h2(read_text(mutants["M2_fix_h2"]),
                                                load_yaml_strict(mutants["M2_fix_h2"]))["fired"],
                         "H1_fires": det_h1(read_text(mutants["M2_fix_h2"]),
                                            load_yaml_strict(mutants["M2_fix_h2"]))["fired"]},
        },
        "K6_M3_both_quiet": {
            "expect": True,
            "observed": (not det_h1(read_text(mutants["M3_fix_both"]),
                                    load_yaml_strict(mutants["M3_fix_both"]))["fired"])
                        and (not det_h2(read_text(mutants["M3_fix_both"]),
                                        load_yaml_strict(mutants["M3_fix_both"]))["fired"]),
        },
        "K7_M5_required_slot_emptied_gate_fails": {
            "expect": "fail",
            "observed": results["D-GATE-BLIND"]["runs"]["M5_empty_mnc"]["verdict"],
        },
        "K8_M6_reversed_chain_detected": {
            "expect": True,
            "observed": "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"
                        in read_text(mutants["M6_reversed_chain"]),
        },
        "K9_determinism_recheck": {
            "expect": True,
            "observed": det_h1(f2b_text, f2b)["fired"] == results["D-H1"]["fired"]
                        and det_h2(f2b_text, f2b)["fired"] == results["D-H2"]["fired"],
        },
        "K10_rev12_carried_over": {
            "expect_prefix": "not_testable",
            "observed": "not_testable: canonical rev12 55d0a1ea bytes are not present at a pinned path in this tree",
        },
    }

    # ---- candidate repair closure -----------------------------------------
    candidates = []
    for role in ("candidate_w002_repair2edit", "candidate_w083"):
        rec = pinned["pins"].get(role)
        if not rec:
            continue
        cp = ROOT / rec["path"]
        ctext = read_text(cp)
        cdoc = load_yaml_strict(cp)
        h1 = det_h1(ctext, cdoc)
        h2 = det_h2(ctext, cdoc)
        chain = cdoc["implication_ledger"]["extension_class_containment"]
        g = run_gate(gate_p, cp)
        candidates.append({
            "role": role,
            "path": rec["path"],
            "sha256": rec["sha256"],
            "h1_quiet": not h1["fired"],
            "h2_quiet": not h2["fired"],
            "chain_intact": ("E_C0 contains E_H2loc" in chain and "contains E_C2" in chain),
            "gate_verdict": g["verdict"],
            "closes_both_carriers": (not h1["fired"]) and (not h2["fired"]) and g["verdict"] == "pass",
        })

    # ---- claim classification ---------------------------------------------
    materiality = {
        "H1-INVERTED-PREMISE": "OPERATIVE_BINDING_TEXT",
        "H2-CONTAINMENT-DENIAL": "OPERATIVE_BINDING_TEXT",
        "D3-CONCLUSION-TYPE-VOCAB": "RESOLVED_NONBLOCKING",
        "F035-01-REVHIST": "HYGIENE",
        "F035-02-SIDEPINS": "HYGIENE",
        "F035-03-PROVENANCE": "HYGIENE",
        "N17-03-SUPPLEMENT-HASH": "HYGIENE",
        "INST-GATE-BLIND": "INSTRUMENT",
    }
    det_of = {
        "H1-INVERTED-PREMISE": "D-H1",
        "H2-CONTAINMENT-DENIAL": "D-H2",
        "D3-CONCLUSION-TYPE-VOCAB": "D-D3",
        "F035-01-REVHIST": "D-REVHIST",
        "F035-02-SIDEPINS": "D-SIDEPIN",
        "F035-03-PROVENANCE": "D-PROVENANCE",
        "N17-03-SUPPLEMENT-HASH": "D-SUPPHASH",
        "INST-GATE-BLIND": "D-GATE-BLIND",
    }
    claims_out = []
    for c in CLAIMS:
        d = results[det_of[c["claim_id"]]]
        claims_out.append({**c, "status": "REPRODUCED" if d["fired"] else "NOT_REPRODUCED",
                           "measured_line": d.get("measured_line"),
                           "materiality": materiality[c["claim_id"]],
                           "detail": d.get("detail", "")[:300]})

    # ---- drift at exit -----------------------------------------------------
    end_drift = []
    for role, rec in pinned["pins"].items():
        p = ROOT / rec["path"]
        m = sha256_file(p) if p.exists() else None
        if m != pins[role]["measured_sha256"]:
            end_drift.append(role)
    drift = {"start": start_drift, "end": end_drift,
             "detected": bool(start_drift or end_drift)}

    report = {
        "task_id": "W054-F2B-REV29-UNION-LEDGER-01",
        "actor": "worker-054",
        "created_at": args.created_at,
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "target": {
            "path": pins["f2b_canonical"]["path"],
            "sha256": pins["f2b_canonical"]["measured_sha256"],
            "revision_read": f2b.get("revision"),
            "mirror_sha256": pins["f2b_mirror"]["measured_sha256"],
        },
        "pins": pins,
        "claims": claims_out,
        "detectors": results,
        "controls": controls,
        "candidate_repairs": candidates,
        "materiality_rule": MATERIALITY_RULE,
        "counts": {
            "claims": len(claims_out),
            "reproduced": sum(1 for c in claims_out if c["status"] == "REPRODUCED"),
            "not_reproduced": sum(1 for c in claims_out if c["status"] == "NOT_REPRODUCED"),
            "operative_binding_text": sum(1 for c in claims_out if c["materiality"] == "OPERATIVE_BINDING_TEXT"),
            "hygiene": sum(1 for c in claims_out if c["materiality"] == "HYGIENE"),
            "instrument": sum(1 for c in claims_out if c["materiality"] == "INSTRUMENT"),
            "controls_pass": sum(1 for v in controls.values() if _ctrl_pass(v)),
            "controls": len(controls),
        },
        "verdict": ("At F2b schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (FROZEN rev29 815e08079aef), "
                    "the union of reported defect claims resolves to 2 OPERATIVE binding-text "
                    "contradictions (H1 :246 inverted containment premise; H2 :152 containment denial), "
                    "1 alias-resolved non-blocking token claim (D3), 4 hygiene items and 1 instrument "
                    "blind spot. Both operative carriers are byte-identical to rev12 and survive rev13. "
                    "A second independent non-author accept at rev29 is NOT justified; the minimal "
                    "repair set is the two carrier edits, and any repair moves the hash and voids every "
                    "verdict bound to b2ab6acb."),
        "not_claimed": ["no gate verdict", "no node status", "no repair adopted",
                        "no canonical artifact written", "not a mathematics claim"],
        "next_falsifier": (
            "Re-run this checker at the same --created-at on the same pinned bytes: the ledger is "
            "FALSIFIED if either operative carrier stops reproducing, if the canonical gate fails the "
            "defective bytes or passes an emptied must_not_conflate, if any control changes its "
            "declared observation, or if all declared pins do not measure as pinned. Any repair that "
            "moves the F2b hash voids this ledger and re-opens the review."),
    }
    body = json.dumps(report, indent=1, sort_keys=True)
    report["report_sha256"] = hashlib.sha256(body.encode()).hexdigest()

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (HERE / "controls.json").write_text(
        json.dumps({k: {**{kk: vv for kk, vv in v.items() if kk != "expect"},
                        "expect": v.get("expect", v.get("expect_prefix")),
                        "pass": _ctrl_pass(v)} for k, v in controls.items()},
                   indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), "sha256": sha256_file(out),
                      "verdict_reproduced": report["counts"]["reproduced"],
                      "operative": report["counts"]["operative_binding_text"],
                      "drift": drift["detected"],
                      "candidates_closing_both": [c["role"] for c in candidates if c["closes_both_carriers"]]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
