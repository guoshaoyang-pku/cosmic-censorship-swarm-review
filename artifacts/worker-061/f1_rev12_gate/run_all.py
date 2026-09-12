#!/usr/bin/env python3
"""W061-F1-REV12-GATE-03 driver.

Builds the fixture set from the frozen F1 rev12 bytes (sha256 cce9c601...), runs the proposed
predicate-consistency rule and the binding canonical structural gate on every fixture, and
writes a machine-readable probe summary.  Read-only with respect to every artifact outside
artifacts/worker-061/f1_rev12_gate/.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = REPO / "artifacts/worker-061/f1_rev12_gate"
PIN = TASK / "pinned"
FIX = TASK / "fixtures"
RULE = TASK / "rule/check_predicate_consistency.py"
GATE = REPO / "artifacts/formulation/tools/check_class_schema.py"
CST = timezone(timedelta(hours=8))

PINS = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def sub_once(text: str, old: str, new: str, what: str) -> str:
    n = text.count(old)
    assert n == 1, f"{what}: expected exactly 1 occurrence, found {n}"
    return text.replace(old, new, 1)


def drop_revision_history(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out, i, dropped = [], 0, 0
    while i < len(lines):
        if re.match(r"^revision_history:\s*$", lines[i]):
            i += 1
            dropped += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].strip() == ""):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    assert dropped == 1, f"revision_history blocks dropped: {dropped}"
    return "".join(out)


def keyfix(text: str) -> str:
    t = drop_revision_history(text)
    t2 = re.sub(r"^\s*predicate_abbreviation:.*\n", "", t, count=1, flags=re.M)
    assert t2 != t, "predicate_abbreviation not removed"
    t = t2
    t2 = re.sub(r"^class_contract_supplement_pointer:.*\n", "", t, count=1, flags=re.M)
    assert t2 != t, "top-level class_contract_supplement_pointer not removed"
    t = t2
    t2 = re.sub(r',\s*class_contract_supplement_pointer:\s*"[^"]*"', "", t, count=1)
    assert t2 != t, "inline class_contract_supplement_pointer not removed"
    t = t2
    t2 = re.sub(r',\s*consistency_evidence_sha256:\s*"[^"]*"', "", t, count=1)
    assert t2 != t, "inline consistency_evidence_sha256 not removed"
    return t2


def replace_d5_line(text: str, new_def: str) -> str:
    lines = text.splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines)
            if l.strip().startswith("definition:") and "pairs (q,t0) with q a point of I+" in l]
    assert len(hits) == 1, f"D5 definition line hits: {len(hits)}"
    indent = lines[hits[0]][: len(lines[hits[0]]) - len(lines[hits[0]].lstrip())]
    lines[hits[0]] = f'{indent}definition: "{new_def}"\n'
    return "".join(lines)


def build_fixtures():
    FIX.mkdir(parents=True, exist_ok=True)
    src = (PIN / "af_wcc_vacuum.rev12.yaml").read_text()
    made = {}

    def emit(name, text):
        p = FIX / name
        p.write_text(text)
        made[name] = sha256_bytes(text.encode())

    emit("POS_rev12_canonical.yaml", src)
    kf = keyfix(src)
    emit("CTL_rev12_keyfix.yaml", kf)
    emit("NEG_M0_b_containment.yaml", sub_once(
        kf,
        "    not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
        "    not exists q in I+ with gamma subset B.",
        "M0 formal"))
    emit("NEG_M1_variant_set_reading.yaml", sub_once(
        kf,
        "iff there exists q in I+ AND t0 in [0,T) such that the TAIL gamma([t0,T)) is contained in J^-(q) intersect M.",
        "iff gamma([0,T)) is contained in the union of J^-(q) over all q in I+ intersected with M.",
        "M1 visibility definition"))
    emit("NEG_M2_partial_repair_d5_stale.yaml", replace_d5_line(
        kf,
        "the pairs (q) with q a point of I+ such that gamma([0,T)) is contained "
        "in the causal past J^-(q) intersected with M"))
    emit("NEG_M4_negation_whole_curve.yaml", sub_once(
        kf,
        "has a tail visible from I+.",
        "has no q in I+ with gamma subset J^-(q) (whole-curve B reading).",
        "M4 negation"))
    emit("CTL_cosmetic.yaml", kf + "# cosmetic control W061-F1-REV12-GATE-03: comment only, no semantic change\n")
    return made


def run_rule(fixture: Path, label: str, class_id="AF-WCC-VAC-GEN"):
    out = TASK / "rule_reports" / f"{label}.json"
    cmd = [sys.executable, str(RULE), str(fixture), "--json", str(out), "--label", label]
    if class_id:
        cmd += ["--class-id", class_id]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    (TASK / "rule_reports" / f"{label}.stdout.txt").write_text(proc.stdout)
    (TASK / "rule_reports" / f"{label}.stderr.txt").write_text(proc.stderr)
    report = json.loads(out.read_text()) if out.exists() else {}
    return {"exit_code": proc.returncode, "verdict": report.get("verdict"),
            "failed_rules": report.get("failed_rules", []), "sha256": report.get("sha256"),
            "applicable": report.get("applicable")}


def run_gate(fixture: Path, label: str):
    proc = subprocess.run([sys.executable, str(GATE), str(fixture), "--json"],
                          capture_output=True, text=True, cwd=str(REPO))
    (TASK / "canonical_gate" / f"{label}.stdout.txt").write_text(proc.stdout)
    (TASK / "canonical_gate" / f"{label}.stderr.txt").write_text(proc.stderr)
    try:
        gate = json.loads(proc.stdout)
    except json.JSONDecodeError:
        gate = {"verdict": "unparseable", "failed_rules": [], "raw": proc.stdout[:400]}
    (TASK / "canonical_gate" / f"{label}.json").write_text(json.dumps(gate, indent=2) + "\n")
    return {"exit_code": proc.returncode, "verdict": gate.get("verdict"),
            "failed_rules": gate.get("failed_rules", []),
            "failures": [{"rule": f.get("rule"), "msg": str(f.get("msg"))[:300]}
                         for f in gate.get("failures", [])][:4]}


def run_gate_replay(fixture: Path, label: str, manifest: str):
    """Run the binding gate with a pinned manifest state (rev27 pre-fix vs rev28)."""
    tool = TASK / "gate_replay" / manifest / "tool" / "check_class_schema.py"
    proc = subprocess.run([sys.executable, str(tool), str(fixture), "--json"],
                          capture_output=True, text=True, cwd=str(REPO))
    outdir = TASK / "canonical_gate" / f"replay_{manifest}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{label}.stdout.txt").write_text(proc.stdout)
    (outdir / f"{label}.stderr.txt").write_text(proc.stderr)
    try:
        gate = json.loads(proc.stdout)
    except json.JSONDecodeError:
        gate = {"verdict": "unparseable", "failed_rules": []}
    (outdir / f"{label}.json").write_text(json.dumps(gate, indent=2) + "\n")
    return {"exit_code": proc.returncode, "verdict": gate.get("verdict"),
            "failed_rules": gate.get("failed_rules", [])}


def repair_checks():
    text = (PIN / "af_wcc_vacuum.rev12.yaml").read_text()
    data = yaml.safe_load(text)

    def dup(node, path=""):
        out = []
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for k, v in node.value:
                kk = getattr(k, "value", str(k))
                if kk in seen:
                    out.append(path + "/" + kk)
                seen.add(kk)
                out += dup(v, path + "/" + kk)
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                out += dup(v, path + f"[{i}]")
        return out

    def get(d, dotted, default=None):
        cur = d
        for k in dotted.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    canon_tax = PIN / "formulation_taxonomy.canonical.yaml"
    tax = yaml.safe_load(canon_tax.read_text())
    pointer = str(get(data, "class_contract_pointer", ""))
    ptr_file, _, ptr_frag = pointer.partition("#")
    ptr_path = REPO / ptr_file
    ptr_ok = ptr_path.exists()
    if ptr_ok and ptr_frag:
        cur = yaml.safe_load(ptr_path.read_text())
        for seg in ptr_frag.split("."):
            cur = cur.get(seg) if isinstance(cur, dict) else None
        ptr_ok = isinstance(cur, dict)
    f0_declared = get(data, "f0_binding.declared_f0_sha256")
    frozen = json.loads((PIN / "FROZEN.rev27.json").read_text())
    frozen_declared = {k: v.get("sha256") for k, v in frozen["files"].items() if k in PINS}
    ordered = get(data, "quantifiers.ordered", [])
    binders = [e.get("binder") for e in ordered if isinstance(e, dict)]
    return {
        "revision": get(data, "revision"),
        "revised_at": get(data, "revised_at"),
        "class_id": get(data, "class_id"),
        "duplicate_top_level_keys": dup(yaml.compose(text)),
        "class_contract_pointer": pointer,
        "class_contract_pointer_resolves_in_canonical_tree": bool(ptr_ok),
        "canonical_taxonomy_classes_present": sorted(list((tax.get("classes") or {}).keys())),
        "f0_declared_sha256": f0_declared,
        "f0_measured_sha256": sha256_path(canon_tax),
        "f0_binding_matches": f0_declared == sha256_path(canon_tax),
        "binders": binders,
        "binder0_is_tagged_regularity_index": bool(binders) and binders[0] == "r",
        "formal_has_tail_t0": "gamma([t0,T))" in str(get(data, "quantifiers.formal", "")),
        "D5_has_tail_t0": "gamma([t0,T))" in str(get(data, "quantifiers.domains.D5.definition", "")),
        "negation_has_tail": "tail visible from I+" in str(get(data, "quantifiers.negation", "")),
        "visibility_predicate_name": get(data, "visibility.predicate_name"),
        "AF_I_plus_defined": "predicate_abbreviation" in text or text.count("AF_{I+}") > 1,
        "frozen_declared_matches_measured": {
            k: (frozen_declared.get(k) == sha256_path(REPO / k)) for k in PINS},
    }


def main():
    TASK.mkdir(parents=True, exist_ok=True)
    (TASK / "pinned").mkdir(exist_ok=True)
    (TASK / "rule_reports").mkdir(exist_ok=True)
    (TASK / "canonical_gate").mkdir(exist_ok=True)

    # pinned copies + independent hash verification of the live canonical bytes
    live_pins = {k: sha256_path(REPO / k) for k in PINS}
    pin_ok = {k: live_pins[k] == v for k, v in PINS.items()}

    made = build_fixtures()

    matrix = {}
    for label, path in sorted((p.name, p) for p in FIX.glob("*.yaml")):
        matrix[label] = {"sha256": sha256_path(path),
                         "rule": run_rule(path, label),
                         "canonical_gate": run_gate(path, label)}

    # Binding-gate replay: same tool bytes (000e09e4) under the manifest frozen at rev27
    # (fce91948, 00:32:59) and the manifest after the 00:34 in-place fix (014e2d30, rev28).
    replay = {}
    for label, path in sorted((p.name, p) for p in FIX.glob("*.yaml")):
        replay[label] = {
            "manifest_rev27_fce91948": run_gate_replay(path, label, "rev27"),
            "manifest_rev28_014e2d30": run_gate_replay(path, label, "rev28"),
        }

    # SCC sibling controls (rule must be not_applicable, gate has its own R22 story)
    scc = {}
    for label, rel in (("CTL_F2a_rev12", "schemas/af_scc_c2_vacuum.yaml"),
                       ("CTL_F2b_rev12", "schemas/af_scc_c0_vacuum.yaml")):
        p = REPO / rel
        scc[label] = {"source": rel, "sha256": sha256_path(p),
                      "rule": run_rule(p, label, class_id=None),
                      "canonical_gate": run_gate(p, label)}

    summary = {
        "task_id": "W061-F1-REV12-GATE-03",
        "worker": "worker-061",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "measured_at": datetime.now(CST).isoformat(timespec="seconds"),
        "pins": {k: {"sha256_expected": v, "sha256_measured": live_pins[k], "match": pin_ok[k]}
                 for k, v in PINS.items()},
        "repair_checks_rev12": repair_checks(),
        "fixtures": made,
        "rule_set": "W061-PREDICATE-CONSISTENCY-V1",
        "rule_matrix": {k: v["rule"] for k, v in matrix.items()},
        "canonical_gate_matrix": {k: v["canonical_gate"] for k, v in matrix.items()},
        "canonical_gate_replay_matrix": replay,
        "scc_sibling_controls": scc,
        "process_timeline": {
            "note": ("the canonical gate reads artifacts/formulation/KEY_MANIFEST.json at run time; "
                     "the rev27 freeze (FROZEN self 2554e276, 00:32:59) declared manifest fce91948 "
                     "which did not allow the six new rev12 keys, so the same F1 bytes cce9c601 "
                     "returned fail R22; the manifest was edited in place to 014e2d30 and FROZEN "
                     "was bumped to rev28 (self 2f358f67, 00:35:08), after which the same bytes pass. "
                     "The replay under gate_replay/ reproduces both states with the frozen tool bytes."),
            "observations": [
                {"at": "2026-09-12T00:33:53+08:00", "f1_sha256": PINS["schemas/af_wcc_vacuum.yaml"],
                 "key_manifest_sha256": "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
                 "gate_verdict": "fail", "failed_rules": ["R22"]},
                {"at": "2026-09-12T00:35:16+08:00", "f1_sha256": PINS["schemas/af_wcc_vacuum.yaml"],
                 "key_manifest_sha256": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
                 "gate_verdict": "pass", "failed_rules": []},
            ],
        },
        "pinned_ledger": {
            "f1_rev12": sha256_path(PIN / "af_wcc_vacuum.rev12.yaml"),
            "taxonomy_canonical": sha256_path(PIN / "formulation_taxonomy.canonical.yaml"),
            "frozen_rev27": sha256_path(PIN / "hist/FROZEN.rev27.json"),
            "frozen_rev28": sha256_path(PIN / "FROZEN.rev28.json"),
            "key_manifest_rev27": sha256_path(PIN / "hist/KEY_MANIFEST.rev27.json"),
            "key_manifest_rev28": sha256_path(PIN / "KEY_MANIFEST.rev28.json"),
            "rule_spec": sha256_path(PIN / "rule_spec.json"),
        },
    }
    (TASK / "probe_rev12_output.json").write_text(json.dumps(summary, indent=2) + "\n")

    # console summary
    print("pins match:", all(pin_ok.values()))
    print("rule matrix:")
    for k, v in summary["rule_matrix"].items():
        print(f"  {k:38s} rule={v['verdict']:>13s} failed={v['failed_rules']}")
    print("canonical gate matrix:")
    for k, v in summary["canonical_gate_matrix"].items():
        print(f"  {k:38s} gate={v['verdict']:>8s} failed={v['failed_rules']} exit={v['exit_code']}")
    print("scc controls:")
    for k, v in scc.items():
        print(f"  {k:20s} rule={v['rule']['verdict']} gate={v['canonical_gate']['verdict']} "
              f"{v['canonical_gate']['failed_rules']}")
    print("gate replay (manifest rev27 -> rev28):")
    for k, v in summary["canonical_gate_replay_matrix"].items():
        a, b = v["manifest_rev27_fce91948"], v["manifest_rev28_014e2d30"]
        print(f"  {k:38s} rev27={a['verdict']}/{a['failed_rules']} rev28={b['verdict']}/{b['failed_rules']}")
    print("summary:", TASK / "probe_rev12_output.json",
          sha256_path(TASK / "probe_rev12_output.json")[:16])


if __name__ == "__main__":
    main()
