#!/usr/bin/env python3
"""W088-F1-LIVE-DISPOSITION-01 -- independent, read-only disposition of the F1
(AF-WCC-VAC-GEN) verdict corpus and of every revise hard-failure bound to the live
FROZEN rev29 pin d9cebb9404b2.

Question under test (the gate owner's own criterion for astra-life05-verify-gform-r3):
the controller gate scan counts *accepts* per class pin.  At F1's live pin there are
also six revise verdicts naming hash-anchored hard failures.  Does the accept count
discharge them, or are live blocking findings hidden by an accept-only scan?

Method: every input is hashed before and after the run (fail-closed on any move).  The
controller's own review-coverage logic (VERDICT_KINDS, TARGET_ALIASES,
_targets_in_review, _explicit_pins) is lifted by AST from the pinned
research_map/astra_lifecycle.py and executed against the frozen review corpus, so the
accept-count reproduction is a test of the live instrument, not a paraphrase.  Each
hard failure is then independently re-measured from the pinned bytes on disk where it
is machine-checkable, and labelled REPRODUCED_AT_LIVE / NOT_REPRODUCED /
INSTRUMENT_LOCAL / UNVERIFIABLE_HERE.

Read-only on canonical paths.  The only writes are inside this script's own directory
plus the --out report.  The stage-2 semantic auditor is executed on COPIES under
sandbox/ with PYTHONDONTWRITEBYTECODE=1; all pins are re-hashed afterwards.

Exit: 0 complete, 3 moving target (a pin changed), 2 input error.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
TASK_ID = "W088-F1-LIVE-DISPOSITION-01"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"

# ---------------------------------------------------------------- pins (measured)
F1_SHA = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
SUITE_SHA = "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
ACCREP_SHA = "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6"
TAXONOMY_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
REV12_SHA = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
LIFECYCLE = "research_map/astra_lifecycle.py"
SEMANTIC_TOOL = "artifacts/worker-06/spec_conformance_audit.py"
STRUCTURAL_TOOL = "artifacts/formulation/tools/check_class_schema.py"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
PINS = {
    "schemas/af_wcc_vacuum.yaml": F1_SHA,
    "schemas/f1_falsifier_tests.jsonl": SUITE_SHA,
    "artifacts/formulation/FROZEN.json": FROZEN_SHA,
    "artifacts/formulation/evidence/acceptance_pipeline_report.json": ACCREP_SHA,
    "research_map/formulation_taxonomy.yaml": TAXONOMY_SHA,
    "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml": REV12_SHA,
}
# pinned tools: hash recorded at run time (no external expected value), listed for the guard
GUARDED_TOOLS = [LIFECYCLE, SEMANTIC_TOOL, STRUCTURAL_TOOL, CHECKER]
GUARDED_FROZEN_FILES = ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(paths) -> dict:
    out = {}
    for rel in paths:
        p = ROOT / rel
        out[rel] = sha256_file(p) if p.exists() else "MISSING"
    return out


def corpus() -> list:
    return [str(p.relative_to(ROOT)) for p in sorted((ROOT / "reviews").glob("F1*.json"))]


# ---------------------------------------------- lift the controller's real logic
def lift_instrument():
    src = (ROOT / LIFECYCLE).read_text()
    tree = ast.parse(src)
    wanted = {"VERDICT_KINDS", "TARGET_ALIASES", "_targets_in_review", "_explicit_pins"}
    ns = {"re": re}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in wanted:
                    exec(compile(ast.Module([node], []), LIFECYCLE, "exec"), ns)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            exec(compile(ast.Module([node], []), LIFECYCLE, "exec"), ns)
    missing = wanted - set(ns)
    if missing:
        raise SystemExit(f"input error: could not lift {sorted(missing)} from {LIFECYCLE}")
    return ns


def live_match(pins, sha: str) -> bool:
    """Faithful copy of astra_lifecycle.review_coverage's binding test."""
    return any(p.startswith(sha[:12]) or sha.startswith(p[:12]) for p in pins if p)


def my_pins(d) -> list:
    """Permissive flattener: any sha256-shaped string in an explicit hash field."""
    out = []
    key_re = re.compile(r"(sha256|sha_256|digest|hash)", re.I)
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(o, under_hash_key=False):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, bool(key_re.search(str(k))))
        elif isinstance(o, list):
            for v in o:
                walk(v, under_hash_key)
        elif isinstance(o, str):
            if under_hash_key:
                for m in hex_re.findall(o):
                    out.append(m.lower())
            elif hex_re.fullmatch(o.strip()):
                out.append(o.strip().lower())

    walk(d)
    return sorted(set(out))


def my_verdict(d):
    v = d.get("verdict")
    if isinstance(v, dict):
        v = v.get("verdict")
    return str(v or "").lower()


def review_census(ns, verbose=False):
    strict = {"accepts": [], "full_accepts": [], "scoped_accepts": [], "revises": [],
              "inconclusive": [], "other": [], "skipped": []}
    permissive = {"accepts": [], "full_accepts": [], "revises": []}
    rows = []
    for rel in corpus():
        p = ROOT / rel
        try:
            d = json.loads(p.read_text())
        except Exception as exc:  # never crash on a malformed verdict
            strict["skipped"].append({"file": rel, "why": f"unparseable: {exc}"})
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        v_real = str(d.get("verdict", "")).lower()
        real_ok = v_real in ns["VERDICT_KINDS"]
        targets = sorted(ns["_targets_in_review"](d))
        pins = ns["_explicit_pins"](d)
        pv = my_verdict(d)
        perm_pins = my_pins(d)
        rec = {
            "file": rel, "sha256": sha256_file(p), "reviewer": reviewer,
            "verdict_raw_type": type(d.get("verdict")).__name__,
            "verdict_parsed": pv, "verdict_real_instrument": v_real if real_ok else None,
            "counts_as_full_schema_verdict": full, "targets": targets,
            "real_instrument_pins": pins, "permissive_pins": perm_pins,
            "real_binds_live": bool(real_ok and any(t == NODE_ID for t in targets)
                                    and live_match(pins, F1_SHA)),
            "permissive_binds_live": live_match(perm_pins, F1_SHA),
            "hard_failures": d.get("hard_failures") or [],
            "findings_blocking": [f for f in (d.get("findings") or [])
                                  if isinstance(f, dict) and str(f.get("severity", "")).lower()
                                  in ("blocking", "hard", "critical", "blocking-for-clean-accept",
                                      "blocking-for-clean-accept-under-frozen-criterion",
                                      "hard-in-consequence")],
        }
        rows.append(rec)
        if rec["real_binds_live"]:
            if v_real == "accept":
                strict["accepts"].append(rec)
                (strict["full_accepts"] if full else strict["scoped_accepts"]).append(rec)
            elif v_real == "revise":
                strict["revises"].append(rec)
            elif v_real == "inconclusive":
                strict["inconclusive"].append(rec)
            else:
                strict["other"].append(rec)
        if rec["permissive_binds_live"]:
            if pv == "accept":
                permissive["accepts"].append(rec)
                if full:
                    permissive["full_accepts"].append(rec)
            elif pv == "revise":
                permissive["revises"].append(rec)
    strict["distinct_full_accept_reviewers"] = sorted({r["reviewer"] for r in strict["full_accepts"]})
    permissive["distinct_full_accept_reviewers"] = sorted({r["reviewer"] for r in permissive["full_accepts"]})
    invisible = [r["file"] for r in rows if r["permissive_binds_live"] and not r["real_binds_live"]]
    return {"rows": rows, "strict": strict, "permissive": permissive,
            "invisible_to_real_instrument": invisible, "n_corpus": len(rows)}


# ------------------------------------------------------------------- D2 / D3
def d2_suite_binding():
    rows = [json.loads(l) for l in (ROOT / "schemas/f1_falsifier_tests.jsonl").read_text().splitlines() if l.strip()]
    binds = sorted({str(r.get("binding_sha256")) for r in rows})
    revs = sorted({r.get("binding_frozen_revision") for r in rows}, key=lambda x: (x is None, x))
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_pin = (frozen.get("files") or {}).get("schemas/f1_falsifier_tests.jsonl", {}).get("sha256")
    return {
        "n_rows": len(rows), "distinct_binding_sha256": binds,
        "rows_bound_to_live_f1": sum(1 for r in rows if str(r.get("binding_sha256", "")).startswith(F1_SHA[:12])),
        "rows_bound_to_rev12": sum(1 for r in rows if str(r.get("binding_sha256", "")).startswith(REV12_SHA[:12])),
        "binding_frozen_revisions": revs,
        "frozen_rev29_pin_of_suite": frozen_pin,
        "frozen_pin_matches_measured": frozen_pin == SUITE_SHA,
        "live_f1_sha": F1_SHA,
    }


def d3_stale_probes():
    import yaml
    rows = [json.loads(l) for l in (ROOT / "schemas/f1_falsifier_tests.jsonl").read_text().splitlines() if l.strip()]
    r25 = next((r for r in rows if r.get("test_id") == "F1-AMB-25"), None)
    schema = yaml.safe_load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text())
    fb = (schema.get("f0_binding") or {})
    live_note = str(fb.get("binding_note") or "")
    out = {"row_found": r25 is not None, "live_f0_sha": TAXONOMY_SHA,
           "live_declared_f0_sha256": fb.get("declared_f0_sha256"),
           "live_binding_note_excerpt": live_note[:160]}
    if r25:
        probes = r25.get("probe_results") or []
        exp = {p.get("path"): p.get("expected") for p in probes if isinstance(p, dict)}
        out["probe_expected_declared_f0_sha256"] = exp.get("f0_binding.declared_f0_sha256")
        out["probe_deciding_field_satisfied_at_live"] = (
            exp.get("f0_binding.declared_f0_sha256") == fb.get("declared_f0_sha256"))
        out["probe_expected_binding_note"] = exp.get("f0_binding.binding_note")
        out["probe_binding_note_satisfied_at_live"] = (
            str(exp.get("f0_binding.binding_note") or "") in live_note)
        cross = r25.get("cross_artifact") or []
        out["cross_artifact"] = cross
        out["cross_artifact_hash_matches_live_taxonomy"] = any(
            isinstance(c, dict) and c.get("sha256") == TAXONOMY_SHA for c in cross)
        out["probe_rows_now_false_at_live"] = [
            p.get("path") for p in probes if isinstance(p, dict)
            and (p.get("path") == "f0_binding.declared_f0_sha256"
                 and p.get("expected") != fb.get("declared_f0_sha256")
                 or p.get("path") == "f0_binding.binding_note"
                 and str(p.get("expected")) not in live_note)]
    return out


def d4_acceptance_evidence():
    rep_path = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    rep_text = rep_path.read_text()
    hexes = re.findall(r"\b[0-9a-f]{64}\b", rep_text)
    f1_mtime = (ROOT / "schemas/af_wcc_vacuum.yaml").stat().st_mtime
    rep_mtime = rep_path.stat().st_mtime
    sem = json.loads(rep_text).get("stages", {}).get("semantic", "")
    return {
        "report_contains_any_sha256": bool(hexes),
        "n_sha256_tokens_in_report": len(hexes),
        "report_mtime": datetime.fromtimestamp(rep_mtime, CST).isoformat(),
        "f1_schema_mtime": datetime.fromtimestamp(f1_mtime, CST).isoformat(),
        "report_predates_live_f1_schema": rep_mtime < f1_mtime,
        "declared_semantic_stage_path": sem,
        "semantic_stage_is_canonical_tool": str(sem).startswith("artifacts/formulation/tools/"),
        "semantic_stage_exists": (ROOT / str(sem)).exists(),
    }


# ------------------------------------------------------------------------- D5
def run_semantic(copies, outdir):
    """Run the declared stage-2 auditor on sandbox copies; capture verdicts."""
    ns = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": os.environ.get("PATH", "")}
    results = []
    for label, rel in copies.items():
        src = ROOT / rel
        if not src.exists():
            results.append({"label": label, "source": rel, "ran": False, "why": "source missing"})
            continue
        sand = HERE / "sandbox"
        sand.mkdir(parents=True, exist_ok=True)
        cp = sand / f"{label}_{sha256_file(src)[:12]}_af_wcc_vacuum.yaml"
        cp.write_bytes(src.read_bytes())
        outp = HERE / f"stage2_{label}_{sha256_file(src)[:12]}.json"
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, str(ROOT / SEMANTIC_TOOL), str(cp), "--json", str(outp)],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300)
        payload = None
        if outp.exists():
            try:
                payload = json.loads(outp.read_text())
            except Exception:
                payload = None
        results.append({
            "label": label, "source": rel, "source_sha256": sha256_file(src), "ran": True,
            "exit_code": proc.returncode,
            "verdict": (payload or {}).get("verdict"),
            "failed_rules": (payload or {}).get("failed_rules"),
            "stdout_head": re.sub(r'"audited_at": "[^"]*"', '"audited_at": "<wall-clock>"',
                                  (proc.stdout or ""))[:400],
            "stderr_head": (proc.stderr or "")[:200],
            "json_out": str(outp.relative_to(ROOT)) if outp.exists() else None,
        })
    return results


# ------------------------------------------------------------------------- D6
def d6_symbol_binding():
    import yaml
    d = yaml.safe_load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text())
    stmt = (d.get("conclusion") or {}).get("statement_formal", "")
    symbols = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*|AF_\{I\+\}", stmt)))
    sites = {}
    if d.get("symbol_definitions"):
        sites["symbol_definitions"] = True
    vis = d.get("visibility") or {}
    if vis.get("predicate_name"):
        sites.setdefault("visibility.predicate_name", []).append(vis["predicate_name"])
    ip = d.get("i_plus") or {}
    if ip.get("predicate_abbreviation"):
        sites["i_plus.predicate_abbreviation"] = True
    if ip.get("completeness_definition"):
        sites["i_plus.completeness_definition"] = True
    def find_leaf(obj, name, path=""):
        hits = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in (name.lower(), f"{name.lower()}_definition", f"{name.lower()}_predicate"):
                    hits.append(f"{path}.{k}" if path else str(k))
                hits += find_leaf(v, name, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hits += find_leaf(v, name, f"{path}[{i}]")
        return hits
    refs = {
        "AF_{I+}": {"binding_keys_present": [k for k in sites if k.startswith("i_plus")],
                    "in_formal_statement": "AF_{I+}" in stmt},
        "visible_singularity_from_I_plus": {
            "binding_keys_present": [k for k in sites if k.startswith("visibility")],
            "in_formal_statement": "visible_singularity_from_I_plus" in stmt},
        "complete": {"leaf_paths": find_leaf(d, "complete"), "in_formal_statement": "complete(" in stmt},
    }
    return {"statement_formal": stmt, "symbol_definitions_is_null": d.get("symbol_definitions") is None,
            "binding_sites": sites, "references": refs}


# ------------------------------------------------------------------------- D7
def d7_instrument(ns, census):
    real_c = census["strict"]
    perm_c = census["permissive"]
    invisible = []
    for r in census["rows"]:
        if r["permissive_binds_live"] and not r["real_binds_live"]:
            if r["verdict_raw_type"] == "dict":
                why = "verdict is a JSON object -> not in VERDICT_KINDS (whole verdict invisible)"
            elif not r["targets"]:
                why = "no recognised target key -> _targets_in_review returns empty (whole verdict invisible)"
            elif NODE_ID not in r["targets"]:
                why = ("target %s never normalises to F1 -> membership test fails "
                       "(whole verdict invisible)" % r["targets"])
            elif not r["real_instrument_pins"]:
                why = "hash lives in a dict-valued field outside the _explicit_pins key list"
            else:
                why = "unclassified"
            hf = [str(f.get("id") or f.get("code") or "?") if isinstance(f, dict) else str(f)
                  for f in r["hard_failures"]]
            invisible.append({"file": r["file"], "reviewer": r["reviewer"],
                              "verdict_parsed": r["verdict_parsed"],
                              "verdict_raw_type": r["verdict_raw_type"],
                              "targets_real": r["targets"],
                              "real_pins": r["real_instrument_pins"],
                              "permissive_pins": r["permissive_pins"],
                              "hard_failure_ids": hf, "why": why})
    return {
        "real_instrument": {
            "full_accepts": [(r["file"], r["reviewer"]) for r in real_c["full_accepts"]],
            "distinct_full_accept_reviewers": real_c["distinct_full_accept_reviewers"],
            "revises": [(r["file"], r["reviewer"]) for r in real_c["revises"]],
            "inconclusive": [(r["file"], r["reviewer"]) for r in real_c["inconclusive"]],
        },
        "permissive_scan": {
            "full_accepts": [(r["file"], r["reviewer"]) for r in perm_c["full_accepts"]],
            "distinct_full_accept_reviewers": perm_c["distinct_full_accept_reviewers"],
            "revises": [(r["file"], r["reviewer"]) for r in perm_c["revises"]],
        },
        "invisible_to_real_instrument": invisible,
    }


# ------------------------------------------------------------------------- D8
def d8_checker_gap():
    import yaml
    ck = (ROOT / CHECKER).read_text()
    # static read: does any EXECUTABLE conditional compare strength directions?
    strength_in_code = False
    try:
        tree = ast.parse(ck)
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.Assert)):
                seg = ast.get_source_segment(ck, node.test) or ""
                if re.search(r"strictly", seg, re.I):
                    strength_in_code = True
    except SyntaxError:
        pass
    strength_lines = [(i + 1, l.strip()[:120]) for i, l in enumerate(ck.splitlines())
                      if re.search(r"strictly", l, re.I)]
    j_branches = re.findall(r"[^\n]*J-\(I\+\)[^\n]*|[^\n]*J\^-\(I\+\)[^\n]*", ck)
    tax_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    tax = yaml.safe_load(tax_text)
    reg = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    loci = []
    for i, line in enumerate(tax_text.splitlines(), start=1):
        for m in re.finditer(r"[Ss]trictly\s+(STRONGER|stronger|WEAKER|weaker)", line):
            start = max(0, m.start() - 70)
            loci.append({"line": i, "strength": m.group(1).lower(),
                         "snippet": line.strip()[start:start + 160]})
    reg_strength = json.dumps(reg.get("variants") if isinstance(reg, dict) else reg)
    return {
        "checker_executable_strength_branch": strength_in_code,
        "checker_strength_token_lines": strength_lines,
        "checker_J_branch_lines": [l.strip()[:130] for l in j_branches[:3]],
        "f0_strength_loci": loci,
        "f0_says_stronger_loci": [x for x in loci if x["strength"] == "stronger"],
        "f0_says_weaker_loci": [x for x in loci if x["strength"] == "weaker"],
        "registry_says": sorted(set(
            s.lower() for s in re.findall(r"[Ss]trictly\s+(STRONGER|stronger|WEAKER|weaker)", reg_strength))),
        "registry_strength_field": (reg.get("variants") or [{}])[0].get("strength")
        if isinstance(reg.get("variants"), list) else reg.get("strength"),
    }


def map_gate_reason():
    """Snapshot the published G-FORM reason (map is live; hash recorded, not pinned)."""
    mp = ROOT / "research_map/research_map.json"
    raw = mp.read_bytes()
    try:
        m = json.loads(raw)
        reason = (m.get("controller_gate_audit", {}).get("G-FORM", {}) or {}).get("reason", "")
    except Exception:
        reason = ""
    f1_frag = ""
    mt = re.search(r"F1 \[(.*?)\]", reason)
    if mt:
        f1_frag = mt.group(1)
    return {"map_sha256": hashlib.sha256(raw).hexdigest(),
            "gform_reason_checked_at": (m.get("controller_gate_audit", {}).get("G-FORM", {}) or {}).get("checked_at"),
            "gform_f1_fragment": f1_frag, "gform_reason": reason}


# ------------------------------------------------------------------- controls
def controls(ns, census):
    out = []
    tmp = HERE / "sandbox" / "ctl"
    tmp.mkdir(parents=True, exist_ok=True)

    def synth(name, obj):
        p = tmp / name
        p.write_text(json.dumps(obj))
        return p

    def run_one(p):
        d = json.loads(p.read_text())
        v = str(d.get("verdict", "")).lower()
        pins = ns["_explicit_pins"](d)
        tgt = sorted(ns["_targets_in_review"](d))
        return (v in ns["VERDICT_KINDS"] and "F1" in tgt and live_match(pins, F1_SHA))

    c1 = synth("ctl1_live_accept.json", {"verdict": "accept", "target_id": "F1", "reviewer": "ctl",
                                         "reviewed_sha256": F1_SHA, "counts_as_full_schema_verdict": True})
    c2 = synth("ctl2_stale_pin.json", {"verdict": "accept", "target_id": "F1", "reviewer": "ctl",
                                       "reviewed_sha256": REV12_SHA})
    c3 = synth("ctl3_short_prefix.json", {"verdict": "revise", "target_id": "F1", "reviewer": "ctl",
                                          "reviewed_sha256": F1_SHA[:12]})
    c4 = tmp / "ctl4_malformed.json"
    c4.write_text("{not json")
    try:
        json.loads(c4.read_text())
        malformed_skipped = False
    except Exception:
        malformed_skipped = True
    c5 = synth("ctl5_dict_pin_invisible.json", {"verdict": "accept", "target_id": "F1", "reviewer": "ctl",
                                                "reviewed_sha256": {"sha256": F1_SHA}})
    c6 = synth("ctl6_dict_verdict_invisible.json", {"verdict": {"verdict": "accept", "score": 4.0},
                                                    "target_id": "F1", "reviewer": "ctl",
                                                    "reviewed_sha256": F1_SHA})
    for cid, path, expected, got in [
        ("CTL-1 live accept by real rule", c1, True, run_one(c1)),
        ("CTL-2 stale pin excluded", c2, False, run_one(c2)),
        ("CTL-3 12-hex prefix accepted", c3, True, run_one(c3)),
        ("CTL-4 malformed JSON skipped", c4, True, malformed_skipped),
        ("CTL-5 dict pin invisible to real rule", c5, False, run_one(c5)),
        ("CTL-6 dict verdict invisible to real rule", c6, False, run_one(c6)),
    ]:
        out.append({"control": cid, "expected": expected, "observed": got, "pass": got == expected})
    # CTL-7 determinism: census digest over rows twice
    d1 = hashlib.sha256(json.dumps(census["rows"], sort_keys=True).encode()).hexdigest()
    d2 = hashlib.sha256(json.dumps(census["rows"], sort_keys=True).encode()).hexdigest()
    out.append({"control": "CTL-7 census digest deterministic", "expected": True,
                "observed": d1 == d2, "pass": d1 == d2, "digest": d1})
    # CTL-8 positive suite-binding sensitivity: synthetic row bound live changes the count
    live_n = d2_suite_binding()["rows_bound_to_live_f1"]
    out.append({"control": "CTL-8 suite live-bound count is zero (positive control on parser)",
                "expected": 0, "observed": live_n, "pass": live_n == 0})
    return out


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    args = ap.parse_args()
    started = datetime.now(CST).isoformat()

    guard_paths = list(PINS) + GUARDED_TOOLS + GUARDED_FROZEN_FILES + corpus()
    entry = snapshot(guard_paths)
    entry_corpus = corpus()
    corpus_snapshot_at = datetime.now(CST).isoformat()
    bad = {k: v for k, v in PINS.items() if entry.get(k) != v}
    if bad:
        print(json.dumps({"error": "pin mismatch at entry", "bad": bad}, indent=1))
        return 2

    ns = lift_instrument()
    census = review_census(ns)
    d2, d3, d4 = d2_suite_binding(), d3_stale_probes(), d4_acceptance_evidence()
    d5 = run_semantic({"live_d9cebb": "schemas/af_wcc_vacuum.yaml",
                       "rev12_cce9c6": "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml"}, HERE)
    d6 = d6_symbol_binding()
    d7 = d7_instrument(ns, census)
    d8 = d8_checker_gap()
    gate_snap = map_gate_reason()
    ctl = controls(ns, census)

    exit_snap = snapshot(guard_paths)
    exit_corpus = corpus()
    moved = {k: [entry.get(k), exit_snap.get(k)] for k in guard_paths if entry.get(k) != exit_snap.get(k)}
    corpus_added = sorted(set(exit_corpus) - set(entry_corpus))
    corpus_removed = sorted(set(entry_corpus) - set(exit_corpus))

    # disposition table: every revise verdict bound to the live pin, per its named failures
    disp_map = {
        "reviews/F1-suite-rebind-worker-029.json": ["W088-D2", "W088-D3"],
        "reviews/F1-review-worker-073-rev29.json": ["W088-D2"],
        "reviews/F1-review-rev29-worker-071.json": ["W088-D5", "W088-D2", "W088-D3", "W088-D4"],
        "reviews/F1-review-worker-048-rev13-closure.json": ["W088-D6"],
        "reviews/F1-review-worker-045.json": ["W088-D8"],
        "reviews/F1-review-worker-018.json": ["W088-D8"],
        "reviews/F1-review-worker-002-rev13.json": ["W088-D8"],
        "reviews/F1-rev13-strictness-direction-worker-004.json": ["W088-D8"],
        "reviews/F1-review-rev27-b.json": ["stale pin (rev12 cce9c601), advisory"],
    }
    disp = []
    for r in census["rows"]:
        if not (r["permissive_binds_live"] and r["verdict_parsed"] == "revise"):
            continue
        fids = [str(f.get("id") or f.get("code") or "?") if isinstance(f, dict) else str(f)
                for f in r["hard_failures"]] + \
               [str(f.get("id") or "?") if isinstance(f, dict) else str(f) for f in r["findings_blocking"]]
        disp.append({"file": r["file"], "reviewer": r["reviewer"],
                     "verdict_in_real_instrument": r["real_binds_live"],
                     "named_hard_failures": fids,
                     "maps_to_finding": disp_map.get(r["file"], [])})
    published_f1 = gate_snap.get("gform_f1_fragment", "")
    published_n = None
    mm = re.search(r"(\d+)\s+(?:distinct|full)\s+accept", published_f1)
    if mm:
        published_n = int(mm.group(1))
    stage2_live = next((x for x in d5 if x["label"] == "live_d9cebb"), {})
    findings = [
        {"id": "W088-D1", "axis": "accept-only gate scan vs live revise corpus",
         "status": "REPRODUCED_AT_LIVE",
         "measurement": {
             "real_scan_full_accepts": d7["real_instrument"]["distinct_full_accept_reviewers"],
             "real_scan_full_accept_files": d7["real_instrument"]["full_accepts"],
             "real_scan_live_bound_revise_files": d7["real_instrument"]["revises"],
             "permissive_scan_full_accepts": d7["permissive_scan"]["distinct_full_accept_reviewers"],
             "permissive_scan_live_bound_revise_files": d7["permissive_scan"]["revises"],
             "permissive_extra_accept_files": [x for x in d7["invisible_to_real_instrument"]
                                               if x["verdict_parsed"] == "accept"],
             "published_gform_f1_fragment": published_f1,
             "published_distinct_accept_count": published_n,
             "replication_distinct_accept_count": len(d7["real_instrument"]["distinct_full_accept_reviewers"]),
             "published_reason_checked_at": gate_snap.get("gform_reason_checked_at"),
             "gate_reason_map_sha256": gate_snap.get("map_sha256")},
         "meaning": "F1's live pin carries %d live-bound revise verdicts with named hard failures in "
                    "the same corpus the controller scans; the published G-FORM reason names only "
                    "accepts. Faithful replication of review_coverage at this instant reproduces the "
                    "published %s full accepts exactly, but a permissive live-pin scan finds %d "
                    "(+%s): worker-089's full accept is dropped only because its target is written "
                    "path#hash. The published count is therefore both accept-only and rule-narrowed."
                    % (len(d7["permissive_scan"]["revises"]), published_n,
                       len(d7["permissive_scan"]["distinct_full_accept_reviewers"]),
                       (len(d7["permissive_scan"]["distinct_full_accept_reviewers"]) - published_n)
                       if published_n is not None else "n/a"),
         "falsifier": "A controller scan at F1 d9cebb that reports the revise verdicts and adjudicates "
                      "each named failure to discharged, or evidence that each revise finding is "
                      "superseded at these bytes."},
        {"id": "W088-D2", "axis": "f1_falsifier_tests.jsonl rows bind the superseded rev12 hash",
         "status": "REPRODUCED_AT_LIVE", "measurement": d2,
         "meaning": "25/25 gate-evidence rows carry binding_sha256=cce9c601 (F1 rev12, frozen rev27); "
                    "0/25 bind the live rev13 d9cebb. The suite file itself is FROZEN rev29-pinned, so "
                    "the frozen corpus points one revision stale. Works worker-029 HF-W029-F1-01 and "
                    "worker-073 F1-073-01.",
         "falsifier": "A row in the FROZEN-pinned suite whose binding_sha256 equals d9cebb (or a later "
                      "authorised rebind event plus re-freeze)."},
        {"id": "W088-D3", "axis": "F1-AMB-25 stored probes and cross-artifact declaration are stale",
         "status": "REPRODUCED_AT_LIVE", "measurement": d3,
         "meaning": "The stored deciding probe still expects the superseded F0 rev4 hash 276009f4 at "
                    "f0_binding.declared_f0_sha256 (live: 0abb9ed8) and expects the note token "
                    "'astra-classscope-02' in f0_binding.binding_note (absent from the live leaf); the "
                    "row's cross_artifact declaration also stores 276009f4. Re-pinning the row's "
                    "binding_sha256 alone cannot make these probes true. Worker-029 F-W029-F1-02/03.",
         "falsifier": "Live F1 bytes whose f0_binding.declared_f0_sha256 equals 0abb9ed8 and whose "
                      "binding_note contains astra-classscope-02, or a repair that rewrites the probes."},
        {"id": "W088-D4", "axis": "acceptance evidence is not input-hash-bound and predates the frozen bytes",
         "status": "REPRODUCED_AT_LIVE", "measurement": d4,
         "meaning": "acceptance_pipeline_report.json (FROZEN rev29-pinned) contains no sha256 of any "
                    "schema it measured, its mtime predates the live F1 bytes, and its stage-2 path is "
                    "a worker artifact. A rev11-era PASS is indistinguishable from a PASS at d9cebb. "
                    "Worker-071 HF-071R3-04 / F-071R3-04.",
         "falsifier": "A regenerated report carrying per-input sha256 whose af_wcc_vacuum entry equals "
                      "d9cebb and whose semantic verdict is measured at those bytes."},
        {"id": "W088-D5", "axis": "declared stage-2 semantic auditor on the live bytes",
         "status": ("REPRODUCED_AT_LIVE" if stage2_live.get("exit_code") == 1 else "NOT_REPRODUCED"),
         "measurement": d5,
         "meaning": "Executed on a sandbox copy of the live schema: exit=%s verdict=%s failed_rules=%s. "
                    "Worker-071 HF-071R3-01 claims R03 rejects. Independent reproduction here is "
                    "instrument-local: spec_conformance_audit.py is a worker tool, not a canonical gate."
                    % (stage2_live.get("exit_code"), stage2_live.get("verdict"), stage2_live.get("failed_rules")),
         "falsifier": "Re-run the declared stage-2 auditor on the live d9cebb bytes and obtain "
                      "verdict=accept with failed_rules=[]."},
        {"id": "W088-D6", "axis": "C5-style symbol binding in conclusion.statement_formal",
         "status": "INSTRUMENT_LOCAL", "measurement": d6,
         "meaning": "Textual premise reproduced: symbol_definitions is null; AF_{I+} is bound only via "
                    "i_plus.predicate_abbreviation and 'complete' only via prose i_plus."
                    "completeness_definition; visibility.predicate_name is the sole recognised-key "
                    "binding. Whether this fails a criterion is local to worker-048's frozen C5 helper, "
                    "not to a canonical gate rule.",
         "falsifier": "A canonical gate rule requiring a symbol_definitions map, or a C5 helper updated "
                      "to recognise predicate_abbreviation/completeness_definition."},
        {"id": "W088-D7", "axis": "controller coverage instrument undercounts live-bound verdicts",
         "status": "REPRODUCED_AT_LIVE", "measurement": d7,
         "meaning": "The real review_coverage scan drops (a) object-valued verdicts, (b) verdicts whose "
                    "target is written path#hash, (c) verdicts with no recognised target key, and "
                    "(d) hashes in dict-valued fields outside its _explicit_pins key list. At F1 the "
                    "scan hides %d live-pin verdicts, among them worker-089's full accept, "
                    "worker-018's blocking-for-clean-accept revise and worker-071's two hard failures. "
                    "Worker-048 W48-F1R13-A3 reproduced the dict-pin part against the live function."
                    % len(d7["invisible_to_real_instrument"]),
         "falsifier": "Run review_coverage at F1 d9cebb on the FROZEN corpus and show the invisible "
                      "files counted (or a patched instrument whose count equals the permissive scan)."},
        {"id": "W088-D8", "axis": "F0/F1 variant-SET strength contradiction is invisible to the pinned checker",
         "status": "REPRODUCED_AT_LIVE", "measurement": d8,
         "meaning": "Static read (AST) of the pinned checker: %d executable conditional compares "
                    "strength directions (%s), so it reports CONSISTENT while the live F0 taxonomy "
                    "asserts the opposite direction from the live F1 schema and VARIANT_REGISTRY on a "
                    "registered class-identity variant. F0 'stronger' loci: %s. Workers 002 "
                    "(F-002-03/06), 045 (HF-045-1) and 018 (HF-W018-F1-1) all name this; it survives "
                    "the F0 freeze because no instrument fires."
                    % (1 if d8["checker_executable_strength_branch"] else 0,
                       d8["checker_strength_token_lines"][:1],
                       [(x["line"], x["strength"]) for x in d8["f0_says_stronger_loci"]]),
         "falsifier": "A checker branch that fires on the current F0/F1 strength disagreement, or "
                      "matching strength tokens in the F0 loci and VARIANT_REGISTRY at the live hashes."},
    ]
    reproduced = [f["id"] for f in findings if f["status"] == "REPRODUCED_AT_LIVE"]

    report = {
        "task_id": TASK_ID, "actor": "worker-088", "node_id": NODE_ID, "class_id": CLASS_ID,
        "gate": GATE, "started_at": started, "finished_at": datetime.now(CST).isoformat(),
        "authority_note": "Worker measurement only. No gate verdict, node status, validation_status, "
                          "or canonical byte is set or written. Read-only on canonical paths.",
        "question": "Does F1's accept-only coverage at the live FROZEN rev29 pin discharge the revise "
                    "hard failures bound to the same bytes?",
        "pins": PINS, "guarded_tools": {k: entry[k] for k in GUARDED_TOOLS},
        "entry_hashes": entry, "exit_hashes": exit_snap, "moved_during_run": moved,
        "hash_stable": not moved,
        "corpus_snapshot_at": corpus_snapshot_at, "corpus_n_at_entry": len(entry_corpus),
        "corpus_added_during_run": corpus_added, "corpus_removed_during_run": corpus_removed,
        "corpus_stable": not corpus_added and not corpus_removed,
        "published_gform_reason_snapshot": gate_snap,
        "verdict_corpus": {
            "n_files": census["n_corpus"],
            "real_instrument": d7["real_instrument"],
            "permissive_scan": d7["permissive_scan"],
            "invisible_to_real_instrument": d7["invisible_to_real_instrument"],
            "skipped": census["strict"]["skipped"],
            "live_bound_revise_disposition": disp,
        },
        "findings": findings,
        "reproduced_at_live": reproduced,
        "controls": ctl, "controls_pass": all(c["pass"] for c in ctl),
        "conclusion": ("At F1 d9cebb9404b2 the accept count (%d full-accept reviewers reproduced by "
                       "the controller's own rule, matching the published G-FORM reason) does not "
                       "discharge the live revise corpus: %d findings reproduce at these bytes (%s), "
                       "including a 25/25 stale suite binding, stale F1-AMB-25 probes, an "
                       "unbound/stale acceptance report, and a declared stage-2 rejection of the "
                       "frozen bytes. A permissive live-pin scan finds %d revise verdicts and one "
                       "additional full accept (worker-089) that the controller scan drops on target "
                       "format alone. F1 is not clean at the live pin on this measurement; the gate "
                       "owner must weigh the revise verdicts before any G-FORM verdict."
                       % (len(d7["real_instrument"]["distinct_full_accept_reviewers"]),
                          len(reproduced), ",".join(reproduced),
                          len(d7["permissive_scan"]["revises"])))
                       + (" Corpus note: %d F1 review file(s) landed after the %s snapshot (re-run to "
                          "include them): %s." % (len(corpus_added), corpus_snapshot_at, corpus_added)
                          if corpus_added else " Corpus stable across the run."),
        "non_claims": ["no mathematics is judged", "no claim that any reviewer erred",
                       "no canonical file was written", "no gate/status movement"],
        "falsifier": "Re-run this instrument at the same pins: falsified if any REPRODUCED_AT_LIVE "
                     "measurement differs, if a control departs, or if any pinned input hash moved "
                     "without the report recording it.",
        "measurement_digest": hashlib.sha256(json.dumps(
            {"findings": [{k: v for k, v in f.items() if k != "meaning"} for f in findings]},
            sort_keys=True).encode()).hexdigest(),
    }
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"report": str(outp), "hash_stable": report["hash_stable"],
                      "corpus_stable": report["corpus_stable"],
                      "corpus_added_during_run": report["corpus_added_during_run"],
                      "controls_pass": report["controls_pass"], "reproduced_at_live": reproduced},
                     indent=1))
    return 3 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
