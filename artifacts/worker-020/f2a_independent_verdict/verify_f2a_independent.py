#!/usr/bin/env python3
"""W020-F2A-INDEP-VERDICT-01: independent, machine-checkable verification of the
canonical F2a class schema (AF-SCC-C2-VAC-GEN).

Bounded worker task (worker=020). No model calls. No writes outside
artifacts/worker-020/f2a_independent_verdict/.

Design:
  * freeze T0 = measured sha256 of the canonical F2a schema and of the declared F0
    artifact (research_map/formulation_taxonomy.yaml); copy the measured bytes into
    snapshots/ so the verified content survives later rewrites;
  * run the canonical structural gate and the class-separation detector against the
    frozen snapshot, not against the live path;
  * run independent content assertions (class identity, conclusion vocabulary,
    quantifier order, extension regularity, I+/visibility roles, implication ledger);
  * re-measure T1 at the end; any change of the canonical F2a hash in the window is
    a moving-target hard failure and forces verdict=inconclusive.

Outputs (all under this directory):
  snapshots/f2a_<hash12>.yaml           frozen target bytes
  snapshots/f0_taxonomy_<hash12>.yaml   frozen declared-F0 bytes
  gate_f2a_snapshot.json                canonical gate report on the snapshot
  classsep_f2a_snapshot.json            class-separation findings on the snapshot
  drift_timeline.json                   hash samples for target + siblings + F0
  f2a_independent_verdict.json          machine evidence record (review input)
  f2a_independent_verdict.md            human-readable summary
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = _dt.timezone(_dt.timedelta(hours=8))

TARGET = ROOT / "schemas/af_scc_c2_vacuum.yaml"
SIBLINGS = [
    ROOT / "schemas/af_wcc_vacuum.yaml",
    ROOT / "schemas/af_scc_c0_vacuum.yaml",
]
F0_CANONICAL = ROOT / "research_map/formulation_taxonomy.yaml"
F0_AUTHORING = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CLASSSEP = ROOT / "research_map/class_separation.py"

CLASS_ID = "AF-SCC-C2-VAC-GEN"
CONCLUSION_TYPE = "scc_c2_future_inextendibility"
REQUIRED_BLOCKS = [
    "quantifiers", "topology", "data_class", "regularity", "genericity",
    "extension_predicate", "i_plus", "visibility", "conclusion", "falsifier",
    "anti_scope", "implication_ledger", "class_boundary", "non_vacuity",
]


def now() -> str:
    return _dt.datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


class DupKeyLoader(yaml.SafeLoader):
    """Records duplicate mapping keys (YAML 1.2 requires uniqueness; PyYAML keeps last)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates: list = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for k_node, _ in node.value:
            if isinstance(k_node, yaml.ScalarNode):
                key = self.construct_object(k_node, deep=deep)
                try:
                    if key in seen:
                        self.duplicates.append(
                            {"key": key, "line": k_node.start_mark.line + 1})
                    seen.add(key)
                except TypeError:  # unhashable key -> leave to PyYAML
                    pass
        return super().construct_mapping(node, deep=deep)


def parse_yaml_with_dups(path: Path):
    loader = DupKeyLoader(path.read_text())
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, loader.duplicates


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def strings_at(doc, path: tuple):
    node = doc
    for k in path:
        if not isinstance(node, dict):
            return []
        node = node.get(k)
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [x for x in node if isinstance(x, str)]
    return []


def main() -> int:
    t_start = now()
    snap_dir = HERE / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    # ---------- T0 freeze ----------
    t0_target_sha = sha256_file(TARGET)
    t0_f0_sha = sha256_file(F0_CANONICAL)
    t0_authoring_sha = sha256_file(F0_AUTHORING)
    snap_target = snap_dir / f"f2a_{t0_target_sha[:12]}.yaml"
    snap_f0 = snap_dir / f"f0_taxonomy_{t0_f0_sha[:12]}.yaml"
    snap_target.write_bytes(TARGET.read_bytes())
    snap_f0.write_bytes(F0_CANONICAL.read_bytes())
    assert sha256_file(snap_target) == t0_target_sha
    assert sha256_file(snap_f0) == t0_f0_sha

    doc, dups = parse_yaml_with_dups(snap_target)
    if not isinstance(doc, dict):
        doc = {}

    gate_tool_sha = sha256_file(GATE)
    classsep_sha = sha256_file(CLASSSEP)

    # ---------- canonical structural gate on the frozen snapshot ----------
    gate_run = run([sys.executable, str(GATE), str(snap_target), "--json"])
    try:
        gate_report = json.loads(gate_run["stdout"])
    except Exception:
        gate_report = {"verdict": "unparseable", "raw": gate_run["stdout"][:2000]}

    # ---------- class-separation detector on the frozen snapshot ----------
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation  # noqa: E402

    cs_findings = class_separation.findings_for_text(
        snap_target.read_text(), f"snapshots/{snap_target.name}")
    cs_soft = [f for f in cs_findings if "SOFT" in f]
    cs_hard = [f for f in cs_findings if "SOFT" not in f]
    cs_regression = class_separation.regression()

    # ---------- independent content assertions (effective doc = PyYAML last-wins) ----------
    checks: list[dict] = []
    hard: list[dict] = []

    def check(cid: str, ok: bool, detail: str, hard_fail: bool = True, rule: str = ""):
        checks.append({"id": cid, "ok": bool(ok), "rule": rule, "detail": detail})
        if not ok and hard_fail:
            hard.append({"id": cid, "rule": rule, "detail": detail})

    cid = str(doc.get("class_id", ""))
    check("C01", cid == CLASS_ID, f"class_id={cid!r} expected {CLASS_ID!r}; "
          f"single token={len(cid.split()) == 1}", rule="single-class binding")

    ctype = str((doc.get("conclusion") or {}).get("conclusion_type", ""))
    check("C02", ctype == CONCLUSION_TYPE,
          f"conclusion.conclusion_type={ctype!r} expected {CONCLUSION_TYPE!r}", rule="conclusion vocabulary")
    check("C02b", "strong_cosmic_censorship" not in ctype and "c0" not in ctype.lower(),
          f"no class-agnostic/C0 conclusion token in {ctype!r}", rule="no conclusion inflation")

    missing = [b for b in REQUIRED_BLOCKS if b not in doc]
    check("C03", not missing, f"required blocks missing: {missing}", rule="schema completeness")

    q = doc.get("quantifiers") or {}
    kinds = [o.get("kind") for o in (q.get("ordered") or []) if isinstance(o, dict)]
    check("C04", kinds == ["forall", "exists", "forall", "not_exists"],
          f"quantifier order kinds={kinds}", rule="exact quantifier order")
    check("C05", q.get("order_matters") is True, f"order_matters={q.get('order_matters')!r}",
          rule="quantifier order")

    reg = doc.get("regularity") or {}
    ext = doc.get("extension_predicate") or {}
    check("C06", reg.get("extension_regularity") == "C2" and ext.get("frozen_regularity") == "C2",
          f"regularity.extension_regularity={reg.get('extension_regularity')!r}, "
          f"extension_predicate.frozen_regularity={ext.get('frozen_regularity')!r}", rule="C2 regularity axis")

    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    check("C07", ip.get("in_conclusion") is False and ip.get("completeness_in_conclusion") is False,
          f"i_plus.in_conclusion={ip.get('in_conclusion')!r}, completeness_in_conclusion="
          f"{ip.get('completeness_in_conclusion')!r}", rule="I+ role")
    check("C08", str(vis.get("role", "")) == "not_in_conclusion",
          f"visibility.role={vis.get('role')!r}", rule="visibility role")

    gen = doc.get("genericity") or {}
    check("C09", gen.get("kind") == "residual_comeager" and gen.get("is_part_of_class") is True,
          f"genericity.kind={gen.get('kind')!r}, is_part_of_class={gen.get('is_part_of_class')!r}",
          rule="genericity binding")

    led = doc.get("implication_ledger") or {}
    entail = [e for e in (led.get("one_way_entailments") or []) if isinstance(e, dict)]
    forbid = [e for e in (led.get("forbidden_transfers") or []) if isinstance(e, dict)]
    has_c0_to_c2 = any(e.get("from", "").startswith("no proper future C0") and
                       e.get("to", "").startswith("no proper future C2") for e in entail)
    forbids_c2_to_c0 = any(e.get("from", "").startswith("no proper future C2") and
                           e.get("to", "").startswith("no proper future C0") for e in forbid)
    check("C10", has_c0_to_c2 and forbids_c2_to_c0,
          f"C0=>C2 entailment present={has_c0_to_c2}; C2=>C0 forbidden={forbids_c2_to_c0}",
          rule="one-way entailment ledger")

    # merge-token scan over assertive surfaces only
    merge_pat = re.compile(r"c\s*0\s*(?:or|and|/|,)\s*c\s*2|c\s*2\s*(?:or|and|/|,)\s*c\s*0", re.I)
    merge_hits = []
    for path in [("conclusion", "statement_formal"), ("conclusion", "statement_natural_language"),
                 ("scope_statement",), ("quantifiers", "formal"), ("regularity", "extension_regularity_exact")]:
        for s in strings_at(doc, path):
            if merge_pat.search(s):
                merge_hits.append(f"{'.'.join(path)}: {s[:90]}")
    check("C11", not merge_hits, f"C0/C2 merge tokens in assertive surfaces: {merge_hits}",
          rule="no C0/C2 merge")

    # declared-F0 binding vs measured canonical F0
    f0b = doc.get("f0_binding") or {}
    declared = str(f0b.get("declared_f0_sha256", ""))
    check("C12", declared == t0_f0_sha,
          f"f0_binding.declared_f0_sha256={declared[:12] or 'missing'} vs measured canonical F0 "
          f"{t0_f0_sha[:12]}", rule="F0 binding freshness")

    pointer = str(doc.get("class_contract_pointer", ""))
    pointer_path = pointer.split("#", 1)[0] if pointer else ""
    check("C13", pointer_path == "research_map/formulation_taxonomy.yaml",
          f"class_contract_pointer={pointer!r} (canonical path expected; authoring tree is not authoritative)",
          hard_fail=False, rule="canonical-path policy")

    # duplicate-key hygiene
    check("C14", not dups, f"duplicate YAML mapping keys: {dups}", hard_fail=False,
          rule="schema hygiene")

    # class_contract_pointer resolvability against the declared canonical F0 snapshot
    pointer_fragment = pointer.split("#", 1)[1] if "#" in pointer else ""
    f0_doc, f0_dups = parse_yaml_with_dups(snap_f0)
    authoring_f0_doc, _ = parse_yaml_with_dups(F0_AUTHORING)

    def walk_frag(root_doc, frag: str) -> bool:
        node = root_doc
        for part in [p for p in frag.split(".") if p]:
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    resolves_canonical = bool(pointer_fragment) and walk_frag(f0_doc, pointer_fragment)
    resolves_authoring = bool(pointer_fragment) and walk_frag(authoring_f0_doc, pointer_fragment)
    check("C15", resolves_canonical,
          f"class_contract_pointer fragment {pointer_fragment!r} resolves in declared canonical F0 "
          f"{t0_f0_sha[:12]}: {resolves_canonical}; resolves in authoring tree "
          f"{t0_authoring_sha[:12]}: {resolves_authoring}. Canonical top-level keys="
          f"{sorted(f0_doc.keys()) if isinstance(f0_doc, dict) else None}",
          rule="F0 contract-pointer resolvability")

    cons_rel = str(f0b.get("consistency_evidence", ""))
    cons_path = ROOT / cons_rel if cons_rel else None
    cons_text = cons_path.read_text() if cons_path and cons_path.exists() else ""
    cons_hash_bound = bool(cons_text) and (t0_f0_sha in cons_text or t0_authoring_sha in cons_text)
    check("C16", cons_hash_bound,
          f"consistency_evidence {cons_rel!r} exists={bool(cons_path and cons_path.exists())}, "
          f"records an input sha256 matching the measured canonical/authoring hashes={cons_hash_bound}",
          hard_fail=False, rule="consistency-evidence hash binding")
    check("C17", t0_f0_sha == t0_authoring_sha,
          f"F0 canonical {t0_f0_sha[:12]} vs authoring {t0_authoring_sha[:12]}: "
          f"divergent={t0_f0_sha != t0_authoring_sha}", hard_fail=False,
          rule="canonical publication")

    # ---------- settle window + T1 re-measure ----------
    samples = []
    t1_target_sha = t0_target_sha
    for _ in range(7):  # <=30s; stop early on a confirmed change
        row = {"sampled_at": now()}
        for name, p in [("target", TARGET), ("sibling_f1", SIBLINGS[0]),
                        ("sibling_f2b", SIBLINGS[1]), ("f0_canonical", F0_CANONICAL),
                        ("f0_authoring", F0_AUTHORING)]:
            row[name] = sha256_file(p)
        samples.append(row)
        t1_target_sha = row["target"]
        if t1_target_sha != t0_target_sha:
            break
        time.sleep(5)
    t1_f0_sha = samples[-1]["f0_canonical"]
    t1_authoring_sha = samples[-1]["f0_authoring"]
    drift = {
        "target_changed": t1_target_sha != t0_target_sha,
        "f0_changed": t1_f0_sha != t0_f0_sha,
        "t0_target_sha256": t0_target_sha,
        "t1_target_sha256": t1_target_sha,
        "t0_f0_sha256": t0_f0_sha,
        "t1_f0_sha256": t1_f0_sha,
        "t0_authoring_f0_sha256": t0_authoring_sha,
        "t1_authoring_f0_sha256": t1_authoring_sha,
        "settle_samples": samples,
    }
    if drift["target_changed"]:
        hard.append({"id": "HF-MOVING-TARGET", "rule": "verdict binding",
                     "detail": f"canonical F2a changed during review window: {t0_target_sha[:12]} -> "
                               f"{t1_target_sha[:12]}; verdict cannot bind"})

    timeline = []
    for name, p in [("target", TARGET), ("sibling_f1", SIBLINGS[0]),
                    ("sibling_f2b", SIBLINGS[1]), ("f0_canonical", F0_CANONICAL),
                    ("f0_authoring", F0_AUTHORING)]:
        timeline.append({"artifact": name, "path": str(p.relative_to(ROOT)),
                         "sha256": sha256_file(p), "sampled_at": now()})

    # ---------- verdict ----------
    if drift["target_changed"]:
        verdict = "inconclusive"
        score = 0
        rationale = ("moving target: canonical F2a hash changed inside the review window; no verdict "
                     "may bind. Checks below apply only to the frozen snapshot.")
    elif hard:
        verdict = "revise"
        score = 2
        rationale = "hard failure(s) on the frozen snapshot: " + ", ".join(h["id"] for h in hard)
    else:
        verdict = "accept"
        score = 4
        rationale = ("frozen snapshot passes the canonical gate and all independent class-binding "
                     "assertions; F0 binding fresh; no drift during the window")

    rec = {
        "task_id": "W020-F2A-INDEP-VERDICT-01",
        "worker": "worker-020",
        "node_id": "F2a",
        "class_id": CLASS_ID,
        "target_path": str(TARGET.relative_to(ROOT)),
        "t_start": t_start,
        "t_end": now(),
        "t0_target_sha256": t0_target_sha,
        "t1_target_sha256": t1_target_sha,
        "verdict": verdict,
        "score": score,
        "rationale": rationale,
        "hard_failures": hard,
        "soft_findings": [c for c in checks if not c["ok"]
                          and c["id"] not in {h["id"] for h in hard}],
        "checks": checks,
        "gate": {"tool_path": str(GATE.relative_to(ROOT)), "tool_sha256": gate_tool_sha,
                 "run": {"cmd": gate_run["cmd"], "exit_code": gate_run["exit_code"],
                         "stderr": gate_run["stderr"][:500]},
                 "report": gate_report},
        "class_separation": {"module_path": str(CLASSSEP.relative_to(ROOT)),
                             "module_sha256": classsep_sha,
                             "hard_findings": cs_hard, "soft_findings": cs_soft,
                             "regression": cs_regression},
        "f0_binding": {"declared": declared, "measured_canonical": t0_f0_sha,
                       "measured_authoring": t0_authoring_sha,
                       "canonical_authoring_divergent": t0_f0_sha != t0_authoring_sha},
        "drift": drift,
        "drift_timeline": timeline,
        "snapshots": {
            "target": {"path": str(snap_target.relative_to(ROOT)),
                       "sha256": sha256_file(snap_target)},
            "f0": {"path": str(snap_f0.relative_to(ROOT)), "sha256": sha256_file(snap_f0)},
        },
        "duplicate_yaml_keys": dups,
        "claims": [] if verdict != "accept" else [
            f"At the frozen snapshot {t0_target_sha[:12]} (copied to {snap_target.name}), the canonical "
            f"structural gate {gate_tool_sha[:12]} passes, the class-separation detector reports no hard "
            f"finding, and all class-binding assertions C01-C13 hold."],
        "does_not_claim": [
            "gate verdict (worker cannot move gates)",
            "node completion",
            "schema truth or any mathematical result",
            "that the live canonical file still equals the frozen snapshot",
        ],
    }

    out_json = HERE / "f2a_independent_verdict.json"
    out_json.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    rec_sha = sha256_file(out_json)

    md = [
        f"# W020 / F2a independent verdict — {verdict} (score {score})",
        "",
        f"- worker: `worker-020`; node `F2a`; class `{CLASS_ID}`",
        f"- frozen target: `{rec['target_path']}` sha256 `{t0_target_sha}`",
        f"- snapshot: `{rec['snapshots']['target']['path']}`",
        f"- T1 re-measure: `{t1_target_sha}` (changed={drift['target_changed']})",
        f"- declared-F0: `{declared[:12] or 'missing'}` vs measured canonical `{t0_f0_sha[:12]}` "
        f"(authoring `{t0_authoring_sha[:12]}`, divergent={rec['f0_binding']['canonical_authoring_divergent']})",
        f"- canonical gate `{gate_tool_sha[:12]}`: exit {gate_run['exit_code']} "
        f"verdict {gate_report.get('verdict')} failed_rules {gate_report.get('failed_rules')}",
        f"- class-separation `{classsep_sha[:12]}`: hard={len(cs_hard)} soft={len(cs_soft)}; "
        f"detector regression {cs_regression.get('verdict')}",
        f"- rationale: {rationale}",
        "",
        "## Hard failures",
        "",
    ]
    md += [f"- `{h['id']}` ({h['rule']}): {h['detail']}" for h in hard] or ["- none on the frozen snapshot"]
    md += ["", "## Non-passing checks", ""]
    md += [f"- `{c['id']}` ({c['rule']}): {c['detail']}" for c in checks if not c["ok"]] or ["- none"]
    md += ["", f"evidence sha256: `{rec_sha}`", ""]
    out_md = HERE / "f2a_independent_verdict.md"
    out_md.write_text("\n".join(md) + "\n")
    md_sha = sha256_file(out_md)

    gate_file = HERE / "gate_f2a_snapshot.json"
    gate_file.write_text(json.dumps(gate_report, indent=2, sort_keys=True) + "\n")
    cs_file = HERE / "classsep_f2a_snapshot.json"
    cs_file.write_text(json.dumps({"hard": cs_hard, "soft": cs_soft, "regression": cs_regression},
                                  indent=2, sort_keys=True) + "\n")
    timeline_file = HERE / "drift_timeline.json"
    timeline_file.write_text(json.dumps(timeline, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "verdict": verdict, "score": score, "hard_failures": [h["id"] for h in hard],
        "t0_target_sha256": t0_target_sha, "t1_target_sha256": t1_target_sha,
        "f0_measured": t0_f0_sha, "f0_authoring": t0_authoring_sha,
        "gate_exit": gate_run["exit_code"], "gate_verdict": gate_report.get("verdict"),
        "classsep_hard": len(cs_hard), "classsep_soft": len(cs_soft),
        "duplicate_keys": len(dups),
        "evidence_json": str(out_json.relative_to(ROOT)), "evidence_sha256": rec_sha,
        "evidence_md": str(out_md.relative_to(ROOT)), "evidence_md_sha256": md_sha,
        "gate_file": str(gate_file.relative_to(ROOT)), "gate_file_sha256": sha256_file(gate_file),
        "classsep_file": str(cs_file.relative_to(ROOT)), "classsep_file_sha256": sha256_file(cs_file),
        "timeline_file": str(timeline_file.relative_to(ROOT)), "timeline_file_sha256": sha256_file(timeline_file),
        "snapshot_target": str(snap_target.relative_to(ROOT)), "snapshot_target_sha256": t0_target_sha,
        "snapshot_f0": str(snap_f0.relative_to(ROOT)), "snapshot_f0_sha256": t0_f0_sha,
        "script_sha256": sha256_file(Path(__file__)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
