#!/usr/bin/env python3
"""W066-F2B-REV30-PREFLIGHT-01 -- read-only pre-flight of the controller-ruled
(REC-36 items 1-2) F2b rev14 repair wording at the FROZEN rev29 pins.

Class: AF-SCC-C0-VAC-GEN (node F2b, gate G-FORM).  No canonical path is written.
Every measurement is taken on byte copies pinned at run start under PINNED/.

Pre-registered direction rules (chain: E_C0 contains E_H2loc contains E_{C^1,1}
contains E_C2; inexistence in a LARGER extension set is the STRONGER statement,
so C0-inextendibility entails H2_loc-inextendibility entails C2-inextendibility):

  H1_INVERTED : implication_ledger.forbidden_transfers[0].reason says C2 is a
                "strictly larger extension class"        [live defect, line 246]
  H1_OK       : the reason states the E_C2 subset E_C0 order / C2 is the
                strictly stronger regularity requirement (or strictly smaller
                extension class)
  H2_DENIAL   : regularity.must_not_conflate[0] says no containment is asserted
                for a class whose own chain asserts it      [live defect, line 152]
  H2_INVERTED : the clause asserts "H2_loc-inextendibility entails this class's
                conclusion" in the C0 file (false converse); the same sentence is
                CORRECT in the C2 sibling and must not be flagged there
  H2_NESTING  : the clause states the nested extension sets
  H2_OK       : not denial, not inverted, and (nesting or correct direction)
  LANDABLE    : yaml_ok AND structural gate 0 failed rules AND class-separation
                scan clean AND dual checker PASS AND H1_OK AND H2_OK AND the
                variant changes only the two intended leaf lines relative to live
                (externally staged candidates are exempt from the last item)

Bracketed historical notes ("[R2 major: the earlier 'no containment ...' was
wrong]") are stripped before classification, so a repaired candidate that quotes
the old denial is not misread as still asserting it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PINNED = HERE / "PINNED"
SANDBOX = HERE / "sandbox"
EVIDENCE = HERE / "evidence"
TOOL_OUT = EVIDENCE / "tool_runs"

INPUTS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "research_map/class_separation.py":
        "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml":
        "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml":
        "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml":
        "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/worker-080/f2b_hf1_direction_census/report.json":
        "cea4e04add08503b9eef847242f3656d5cbb210f52a984cb84a64ed6e00185ee",
    "artifacts/worker-053/f2b_rev30_h2_direction/report.json":
        "f4ef320a3e2ff7c1660436abe152660fe95d7f196d649dc8614d5a74a389d1e7",
    "artifacts/worker-058/rev30_freeze_rehearsal/report.json":
        "1e31bbe5e9336e688d3668850d4fdcd1f8bc28ee80baf064c1095cf847c1930c",
    "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py":
        "99b7a01ddfa62ef05ac80a973c13ea32ffcc93554fd39336d378b0c33a40ed7f",
    "runtime/state/controller_verification/astra-lifecycle-08-decisions.json":
        "8f6f3cf8218758deacc0d828b15c018f446a38071de25d680d5e9af257f7aebc",
}
EXTERNAL = {"CAND_84b5d3fa_REHEARSED", "CAND_51c253c4_CORRECTED",
            "CAND_4951cc96_NESTING_ONLY", "CTRL_C2_SIBLING"}

H1_PREFIX = '    - {from: "no proper future C2 extension", to: "this class", '
REC36_H1_REASON = ("C2 is a strictly stronger regularity requirement "
                   "(E_C2 subset E_C0), so C2-inextendibility does not establish this class")
REC36_H2_ADAPTED = (
    "H2_loc (locally square-integrable curvature) is a distinct regularity-axis "
    "value, not a rival of C0: the extension sets are nested E_C0 contains E_H2loc "
    "contains E_{C^1,1} contains E_C2, so this class's inexistence statement is the "
    "strongest and C0-inextendibility entails H2_loc-inextendibility; the converse "
    "is false and must not be used. See implication_ledger."
)
H2_REVERSED = ("H2_loc-inextendibility ENTAILS this class's conclusion "
               "(C0-inextendibility); see implication_ledger.")
H2_NONSENSE = "purple monkey dishwasher."

CONTROL_EXPECT = {
    "LIVE": {"h1_inverted": True, "h2_denial": True, "landable": False},
    "REC36_H1_ONLY": {"h1_ok": True, "h2_denial": True, "landable": False},
    "REC36_LITERAL_F2A": {"h1_ok": True, "h2_inverted": True, "landable": False},
    "REC36_ADAPTED_NESTED": {"h1_ok": True, "h2_ok": True, "landable": True},
    "CTRL_H2_REVERSED": {"h2_inverted": True, "gate_failed": 0, "landable": False},
    "CTRL_H2_NONSENSE": {"h2_ok": False, "gate_failed": 0, "landable": False},
    "CTRL_H2_EMPTY": {"gate_failed": 0, "h2_ok": False, "landable": False},
    "CTRL_H2_LIST_EMPTY": {"gate_rules_include": "R06", "landable": False},
    "CTRL_H1_UNCHANGED": {"h1_inverted": True, "h2_ok": True, "landable": False},
    "CAND_84b5d3fa_REHEARSED": {"h1_ok": True, "h2_inverted": True, "landable": False},
    "CAND_51c253c4_CORRECTED": {"h1_ok": True, "h2_ok": True, "landable": True},
    "CAND_4951cc96_NESTING_ONLY": {"h2_ok": True, "landable": True},
    "CTRL_C2_SIBLING": {"h2_inverted": False, "h2_ok": True},
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pin_name(rel: str) -> str:
    return rel.replace("/", "__")


def pin_inputs() -> dict:
    """Pin every input as a flat copy AND in a mirror tree that preserves the
    relative layout, so tools whose behaviour depends on siblings (the structural
    gate reads parents[1]/rule_spec.json and KEY_MANIFEST.json) run on pinned
    bytes with their real rule set rather than degrading on a flat copy."""
    PINNED.mkdir(parents=True, exist_ok=True)
    pins = {}
    for rel, expected in INPUTS.items():
        src = ROOT / rel
        if not src.is_file():
            raise SystemExit(f"PIN FAIL: missing {rel}")
        raw = src.read_bytes()
        got = sha256_bytes(raw)
        if got != expected:
            raise SystemExit(f"PIN FAIL: {rel} measured {got[:12]} expected {expected[:12]}")
        flat = PINNED / pin_name(rel)
        flat.write_bytes(raw)
        mirror = PINNED / "mirror" / rel
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_bytes(raw)
        pins[rel] = {"sha256": got, "bytes": len(raw),
                     "pinned_copy": str(flat.relative_to(ROOT)),
                     "mirror_copy": str(mirror.relative_to(ROOT))}
    return pins


def mirror(rel: str) -> Path:
    return PINNED / "mirror" / rel


def find_line(lines, needle: str) -> int:
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    if len(hits) != 1:
        raise SystemExit(f"EDIT FAIL: {needle!r} matched {len(hits)} lines")
    return hits[0]


def h1_line(reason: str) -> str:
    return H1_PREFIX + f'reason: "{reason}"' + "}"


def h2_line(text: str) -> str:
    return '    - "' + text + '"'


def strip_notes(s: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", s or "")


def build_variants(live_text: str, c2_text: str) -> tuple:
    import yaml
    live = live_text.splitlines()
    i_h1 = find_line(live, "C2 is a strictly larger extension class")
    i_h2 = find_line(live, "No containment with C2 or C0 is asserted here")
    c2 = c2_text.splitlines()
    j = find_line(c2, "so H2_loc-inextendibility ENTAILS this class")
    literal = c2[j].strip()
    assert literal.startswith('- "') and literal.endswith('"')
    h2_literal = literal[3:-1]

    def variant(h1=None, h2=None):
        out = list(live)
        if h1 is not None:
            out[i_h1] = h1_line(h1)
        if h2 is not None:
            out[i_h2] = h2_line(h2)
        return "\n".join(out) + ("\n" if live_text.endswith("\n") else "")

    v = {
        "LIVE": live_text,
        "REC36_H1_ONLY": variant(h1=REC36_H1_REASON),
        "REC36_LITERAL_F2A": variant(h1=REC36_H1_REASON, h2=h2_literal),
        "REC36_ADAPTED_NESTED": variant(h1=REC36_H1_REASON, h2=REC36_H2_ADAPTED),
        "CTRL_H2_REVERSED": variant(h1=REC36_H1_REASON, h2=H2_REVERSED),
        "CTRL_H2_NONSENSE": variant(h1=REC36_H1_REASON, h2=H2_NONSENSE),
        "CTRL_H2_EMPTY": variant(h1=REC36_H1_REASON, h2=""),
        "CTRL_H1_UNCHANGED": variant(h2=REC36_H2_ADAPTED),
    }
    ext = {
        "CAND_84b5d3fa_REHEARSED":
            "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
        "CAND_51c253c4_CORRECTED":
            "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
        "CAND_4951cc96_NESTING_ONLY":
            "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
    }
    for name, rel in ext.items():
        v[name] = (PINNED / pin_name(rel)).read_text()
    doc = yaml.safe_load(live_text)
    doc["regularity"]["must_not_conflate"] = []
    v["CTRL_H2_LIST_EMPTY"] = yaml.safe_dump(doc, sort_keys=False)
    v["CTRL_C2_SIBLING"] = c2_text
    meta = {"live_line_h1": i_h1 + 1, "live_line_h2": i_h2 + 1,
            "c2_literal_source_line": j + 1,
            "rec36_item1_literal_source": f"schemas/af_scc_c2_vacuum.yaml:{j + 1}"}
    return v, meta


def load_yaml(text: str):
    import yaml
    try:
        return yaml.safe_load(text), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def classify(text: str) -> dict:
    doc, err = load_yaml(text)
    out = {"yaml_ok": err is None, "yaml_error": err, "class_id": None,
           "h1_reason": None, "h2_clause": None, "h2_clause_classified": None,
           "h1_inverted": False, "h1_ok": False, "h2_denial": False,
           "h2_inverted": False, "h2_nesting": False,
           "h2_correct_direction": False, "h2_ok": False}
    if not isinstance(doc, dict):
        return out
    cid = str(doc.get("class_id") or "")
    out["class_id"] = cid
    try:
        h1 = doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    except Exception:  # noqa: BLE001
        h1 = ""
    try:
        bullets = doc["regularity"]["must_not_conflate"]
    except Exception:  # noqa: BLE001
        bullets = []
    if isinstance(bullets, list):
        strs = [b for b in bullets if isinstance(b, str)]
        hits = [b for b in strs if re.search(r"containment|H2_?loc|nested|subset|contains E_", b, re.I)]
        h2 = hits[0] if hits else (strs[0] if strs else "")
        h2_all = " | ".join(strs)
    else:
        h2 = h2_all = bullets if isinstance(bullets, str) else ""
    h2c = strip_notes(h2_all)
    out["h1_reason"], out["h2_clause"], out["h2_clause_classified"] = h1, h2, h2c
    out["h1_inverted"] = bool(re.search(r"strictly\s+larger\s+extension\s+class", h1, re.I))
    out["h1_ok"] = (not out["h1_inverted"]) and bool(
        re.search(r"strictly\s+stronger\s+regularity|E_?C2\s*(?:subset|⊂|\\subset)|strictly\s+smaller",
                  h1, re.I))
    out["h2_denial"] = bool(re.search(r"no\s+containment[^.]*\basserted", h2c, re.I))
    inverted = bool(re.search(r"H2_?loc[-\s]*inextendibility\s+ENTAILS\s+this\s+class", h2c, re.I))
    out["h2_inverted"] = inverted and cid.upper().endswith("C0-VAC-GEN")
    out["h2_correct_direction"] = bool(re.search(r"entails\s+H2_?loc", h2c, re.I))
    if cid.upper().endswith("C2-VAC-GEN") and inverted:
        out["h2_correct_direction"] = True
    out["h2_nesting"] = bool(re.search(r"nested|subset|contains\s+E_", h2c, re.I))
    out["h2_ok"] = (not out["h2_denial"]) and (not out["h2_inverted"]) and (
        out["h2_nesting"] or out["h2_correct_direction"])
    return out


def load_classsep():
    import importlib.util
    path = mirror("research_map/class_separation.py")
    spec = importlib.util.spec_from_file_location("w066_classsep_pinned", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_json_tool(cmd: list, expect_json_path: Path | None = None) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    parsed = None
    if expect_json_path is not None and expect_json_path.is_file():
        try:
            parsed = json.loads(expect_json_path.read_text())
        except Exception:  # noqa: BLE001
            parsed = None
    if parsed is None:
        try:
            parsed = json.loads(p.stdout[p.stdout.index("{"):]) if "{" in p.stdout else None
        except Exception:  # noqa: BLE001
            parsed = None
    return {"exit_code": p.returncode, "stdout_tail": p.stdout[-400:],
            "stderr_tail": p.stderr[-400:], "json": parsed}


def diff_lines(live_text: str, text: str) -> list:
    a, b = live_text.splitlines(), text.splitlines()
    d = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(a) != len(b):
        d.append("length:%d->%d" % (len(a), len(b)))
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-at", default="2026-09-12T01:35:00+08:00")
    args = ap.parse_args()

    for d in (SANDBOX, EVIDENCE, TOOL_OUT):
        d.mkdir(parents=True, exist_ok=True)
    pins = pin_inputs()
    live_text = (PINNED / pin_name("schemas/af_scc_c0_vacuum.yaml")).read_text()
    c2_text = (PINNED / pin_name("schemas/af_scc_c2_vacuum.yaml")).read_text()
    variants, vmeta = build_variants(live_text, c2_text)
    cls = load_classsep()

    gate = str(mirror("artifacts/formulation/tools/check_class_schema.py"))
    dual = str(mirror("artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"))
    c2_path = str(mirror("schemas/af_scc_c2_vacuum.yaml"))
    c0_path = str(mirror("schemas/af_scc_c0_vacuum.yaml"))
    leaf = {vmeta["live_line_h1"], vmeta["live_line_h2"]}

    axes, tool_evidence, controls = {}, {}, {}
    for name, text in variants.items():
        vpath = SANDBOX / f"{name}.yaml"
        vpath.write_text(text)
        g = run_json_tool([sys.executable, gate, str(vpath), "--json"])
        gj = g.get("json") or {}
        gfailed = gj.get("failed_rules") if isinstance(gj, dict) else None
        c0_arg, c2_arg = (c2_path, c0_path) if name == "CTRL_C2_SIBLING" else (str(vpath), c2_path)
        djson = TOOL_OUT / f"{name}.dual.json"
        d = run_json_tool([sys.executable, dual, "--c0", c0_arg, "--c2", c2_arg,
                           "--json", str(djson), "--label", name], expect_json_path=djson)
        dj = d.get("json") or {}
        kinds = sorted({f.get("kind") for f in (dj.get("findings") or []) if isinstance(f, dict)})
        csf = cls.findings_for_text(text, f"{name}.yaml")
        c = classify(text)
        changed = diff_lines(live_text, text)
        delta_ok = name in EXTERNAL or set(changed) <= leaf
        dual_clean = d["exit_code"] == 0 and (dj or {}).get("verdict") == "PASS"
        landable = bool(c["yaml_ok"] and not gfailed and not csf and dual_clean
                        and c["h1_ok"] and c["h2_ok"] and delta_ok)
        axes[name] = {
            **{k: c[k] for k in ("yaml_ok", "class_id", "h1_inverted", "h1_ok", "h2_denial",
                                 "h2_inverted", "h2_nesting", "h2_correct_direction", "h2_ok")},
            "h1_reason": c["h1_reason"], "h2_clause": c["h2_clause"],
            "gate_exit": g["exit_code"], "gate_verdict": (gj or {}).get("verdict"),
            "gate_failed_rules": gfailed, "gate_failed": len(gfailed or []),
            "dual_exit": d["exit_code"], "dual_verdict": (dj or {}).get("verdict"),
            "dual_clean": dual_clean, "dual_finding_kinds": kinds,
            "classsep_findings": csf, "changed_lines_vs_live": changed, "delta_ok": delta_ok,
            "sha256": sha256_bytes(text.encode()), "bytes": len(text.encode()),
            "landable": landable,
        }
        tool_evidence[name] = {"gate": g, "dual": d}
        exp = CONTROL_EXPECT.get(name)
        if exp is not None:
            obs = {"h1_ok": c["h1_ok"], "h1_inverted": c["h1_inverted"],
                   "h2_denial": c["h2_denial"], "h2_inverted": c["h2_inverted"],
                   "h2_ok": c["h2_ok"], "gate_failed": len(gfailed or []),
                   "gate_failed_rules": list(gfailed or []), "landable": landable}
            checks = {}
            for k, want in exp.items():
                if k == "gate_failed_gt":
                    checks[k] = {"expected": f">{want}", "observed": obs["gate_failed"],
                                 "match": obs["gate_failed"] > want}
                elif k == "gate_rules_include":
                    checks[k] = {"expected": f"includes {want}",
                                 "observed": obs["gate_failed_rules"],
                                 "match": want in obs["gate_failed_rules"]}
                else:
                    checks[k] = {"expected": want, "observed": obs.get(k),
                                 "match": obs.get(k) == want}
            controls[name] = {"checks": checks,
                              "match": all(v["match"] for v in checks.values()),
                              "observed": obs}

    a = axes
    cross = {
        "literal_asserts_inverted_entailment": a["REC36_LITERAL_F2A"]["h2_inverted"],
        "rehearsed_84b5d3fa_asserts_inverted_entailment": a["CAND_84b5d3fa_REHEARSED"]["h2_inverted"],
        "literal_leaf_equals_rehearsed_leaf":
            (a["REC36_LITERAL_F2A"]["h2_clause"] == a["CAND_84b5d3fa_REHEARSED"]["h2_clause"]),
        "literal_sha256": a["REC36_LITERAL_F2A"]["sha256"],
        "rehearsed_84b5d3fa_sha256": a["CAND_84b5d3fa_REHEARSED"]["sha256"],
        "adapted_nested_sha256": a["REC36_ADAPTED_NESTED"]["sha256"],
        "corrected_51c253c4_sha256": a["CAND_51c253c4_CORRECTED"]["sha256"],
        "adapted_leaf_equals_corrected_leaf":
            (a["REC36_ADAPTED_NESTED"]["h2_clause"] == a["CAND_51c253c4_CORRECTED"]["h2_clause"]),
        "inverted_candidates_passing_gate":
            [n for n in ("REC36_LITERAL_F2A", "CAND_84b5d3fa_REHEARSED")
             if a[n]["gate_failed"] == 0],
        "inverted_candidates_passing_dual":
            [n for n in ("REC36_LITERAL_F2A", "CAND_84b5d3fa_REHEARSED")
             if a[n]["dual_clean"]],
        "worker053_filed_report_sha256":
            pins["artifacts/worker-053/f2b_rev30_h2_direction/report.json"]["sha256"],
        "worker080_census_report_sha256":
            pins["artifacts/worker-080/f2b_hf1_direction_census/report.json"]["sha256"],
        "rehearsal_report_sha256":
            pins["artifacts/worker-058/rev30_freeze_rehearsal/report.json"]["sha256"],
    }

    all_controls_match = (all(v["match"] for v in controls.values())
                          and len(controls) == len(CONTROL_EXPECT))
    landable = sorted([n for n, x in axes.items() if x["landable"]])
    live_recheck = {}
    for rel, expected in INPUTS.items():
        got = sha256_bytes((ROOT / rel).read_bytes())
        live_recheck[rel] = {"sha256_at_pin": expected, "sha256_at_end": got, "drift": got != expected}
    pin_drift = sorted([r for r, v in live_recheck.items() if v["drift"]])
    instruments = {
        "structural_gate": {"source": "artifacts/formulation/tools/check_class_schema.py",
                            "sha256": INPUTS["artifacts/formulation/tools/check_class_schema.py"],
                            "run_from": "pinned mirror (siblings rule_spec.json + KEY_MANIFEST.json)"},
        "dual_checker": {"source": "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
                         "sha256": INPUTS["artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"],
                         "run_from": "pinned mirror"},
        "class_separation": {"source": "research_map/class_separation.py",
                             "sha256": INPUTS["research_map/class_separation.py"],
                             "run_from": "pinned mirror, module import, read-only"},
        "direction_classifier": {"source": "this file (preflight.py)",
                                 "run_from": "in-process pre-registered rules"},
    }
    report = {
        "schema": "w066-f2b-rev30-preflight/v1",
        "task_id": "W066-F2B-REV30-PREFLIGHT-01",
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "generated_at": args.generated_at,
        "authority": ("worker measurement only; no gate verdict, node status, validation_status, "
                      "canonical write or schema-semantics decision is claimed"),
        "pins": pins,
        "live_pin_recheck_at_end": live_recheck,
        "pin_drift": pin_drift,
        "instruments": instruments,
        "variant_meta": vmeta,
        "axes": axes,
        "controls": controls,
        "controls_all_match": all_controls_match,
        "landable_set": landable,
        "not_landable_set": sorted([n for n, x in axes.items() if not x["landable"]]),
        "cross_checks": cross,
        "headline": (
            "REC-36 item (1) is under-specified. Its literal reading -- copying the F2a "
            "sibling's must_not_conflate[0] sentence verbatim into F2b -- carries the same "
            "false converse entailment ('H2_loc-inextendibility ENTAILS this class's "
            "conclusion') as the rehearsed rev30 candidate %s; both are H2-inverted "
            "and both PASS the structural gate and the dual checker. The direction-correct "
            "C0-adapted nested wording (sha %s) and the independently staged 51c253c4 (sha %s) "
            "are the only landable F2b repair carriers measured here." % (
                cross["rehearsed_84b5d3fa_sha256"][:12],
                cross["adapted_nested_sha256"][:12],
                cross["corrected_51c253c4_sha256"][:12])),
        "falsifier": (
            "Re-run preflight.py at the same pins. Falsified if: any pinned byte differs "
            "(verdict void); the dual checker does not report the live denial+inversion at "
            "LIVE; 84b5d3fa does not reproduce as H1_ok+H2_inverted; the literal F2a copy is "
            "direction-clean; REC36_ADAPTED_NESTED or 51c253c4 is not landable; the structural "
            "gate detects the reversed/nonsense wording (gate_failed>0 for CTRL_H2_REVERSED or "
            "CTRL_H2_NONSENSE) or fails to reject the emptied must_not_conflate list (R06); "
            "the emptied single bullet is NOT a falsifier -- the gate is measured to pass it; "
            "the C2 sibling is flagged H2_inverted; or any pre-registered control departs "
            "from expectation."),
        "limits": [
            "landable is a conjunction of machine instruments at the pinned bytes; it is not a "
            "mathematics claim and not a gate verdict",
            "the direction classifier is this worker's own pre-registered rule set; it is "
            "consistent with the filed worker-053/080/088 classifications but their instruments "
            "were not re-executed here",
            "the structural gate and the dual checker are blind to the H2 entailment direction "
            "(measured: both PASS the inverted literal and the inverted rehearsed candidate)",
            "the structural gate shows a vacuity boundary: it rejects an emptied "
            "must_not_conflate LIST (R06) but passes a list whose single bullet is the empty "
            "string, so slot presence is checked and bullet non-vacuity is not",
            "the H2 clause sits at must_not_conflate[0] in C0 but at [1] in the C2 sibling; "
            "this instrument classifies over all bullets, so the class-relative C2 control "
            "does not false-positive",
            "bracketed historical notes are stripped before classification; an unbracketed quote "
            "of the old denial would be classified as a live denial",
            "external staged candidates are measured as-is; their own diffs vs live are not "
            "constrained by this instrument",
        ],
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (EVIDENCE / "axes.json").write_text(json.dumps(axes, indent=1, sort_keys=True) + "\n")
    (EVIDENCE / "controls.json").write_text(json.dumps(controls, indent=1, sort_keys=True) + "\n")
    (EVIDENCE / "pins.json").write_text(json.dumps(
        {"inputs": pins, "variant_meta": vmeta}, indent=1, sort_keys=True) + "\n")
    (EVIDENCE / "tool_runs.json").write_text(json.dumps(tool_evidence, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"controls_all_match": all_controls_match, "landable": landable,
                      "pin_drift": pin_drift, "headline": report["headline"]}, indent=1))
    return 0 if (all_controls_match and not pin_drift) else 3


if __name__ == "__main__":
    raise SystemExit(main())
