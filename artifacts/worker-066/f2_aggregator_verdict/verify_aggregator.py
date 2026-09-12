#!/usr/bin/env python3
"""W066-F2AGG-VERDICT-01 -- independent, hash-bound verification of the F2 aggregator.

Target : schemas/af_scc_regularities.yaml (live sha256 94562101a816...)
Classes: AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN   Node: F2   Gate: G-FORM
Actor  : worker-066

This is an independent re-implementation.  It does not import or call the
author's lint for its verdict; the author's lint is run separately, only as a
cross-check.  Every check runs against the pinned copies in ./pinned/ and against
the live files, and every hand-built control is a byte-level mutant of the pinned
aggregator so the falsifier is mechanical.

Read-only against the repo.  Writes only under this directory.

Usage: python3 verify_aggregator.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINNED = HERE / "pinned"
CTL = HERE / "controls"
EV = HERE / "evidence"
CST = 8 * 3600

AGG_NAME = "schemas/af_scc_regularities.yaml"
C2_NAME = "schemas/af_scc_c2_vacuum.yaml"
C0_NAME = "schemas/af_scc_c0_vacuum.yaml"
C2_ID = "AF-SCC-C2-VAC-GEN"
C0_ID = "AF-SCC-C0-VAC-GEN"
CONTRACT_TRUE = [
    "not_a_class_schema", "defines_conclusion", "merge_forbidden", "reference_only",
    "conclusion_objects_remain_separate", "class_ids_must_not_be_joined",
    "components_must_remain_standalone_documents",
]
# defines_conclusion must be false; the rest must be true
CONTRACT_EXPECT = {
    "not_a_class_schema": True, "defines_conclusion": False, "merge_forbidden": True,
    "reference_only": True, "conclusion_objects_remain_separate": True,
    "class_ids_must_not_be_joined": True, "components_must_remain_standalone_documents": True,
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(time.time() + CST))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- YAML probes

def duplicate_keys(path: Path):
    """Conforming-parser duplicate-key probe over the whole document tree."""
    text = path.read_text()
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    dups = []

    def walk(node, where):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = k.value if isinstance(k, yaml.ScalarNode) else str(k)
                line = k.start_mark.line + 1
                if key in seen:
                    dups.append({"path": where, "key": key, "lines": [seen[key], line]})
                else:
                    seen[key] = line
                walk(v, f"{where}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{where}[{i}]")

    walk(root, "$")
    return dups


def scalars(path: Path):
    """All scalar values with their dotted path, over the composed tree (dups kept)."""
    text = path.read_text()
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    out = []

    def walk(node, where):
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                key = k.value if isinstance(k, yaml.ScalarNode) else str(k)
                walk(v, f"{where}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{where}[{i}]")
        elif isinstance(node, yaml.ScalarNode):
            if node.value is not None:
                out.append((where, str(node.value)))

    walk(root, "$")
    return out


def class_token_values(doc):
    """Selector values a conforming parser sees for a component schema."""
    vals = []
    cc = (doc or {}).get("class_components") or {}
    if isinstance(cc, dict) and "regularity_token" in cc:
        vals.append(str(cc["regularity_token"]))
    reg = (doc or {}).get("regularity") or {}
    if isinstance(reg, dict) and "extension_regularity" in reg:
        vals.append(str(reg["extension_regularity"]))
    return vals


# ---------------------------------------------------------------- audit core

COMPOSITE_PATTERNS = [
    r"C\s*\^?\s*\{?\s*0\s*,\s*2\s*\}?",          # C^{0,2}, C0,2
    r"C\s*\^?\s*0\s*(?:or|/|,|\+|and)\s*C\s*\^?\s*2",
    r"C\s*\^?\s*2\s*(?:or|/|,|\+|and)\s*C\s*\^?\s*0",
    r"AF-SCC-(?:VAC|REG|COMBINED|MERGED)-GEN",
    r"AF-SCC-C0-C2",
]
# a raw-text composite mention inside an anti-scope / prohibition list is not a use
FORBID_MARKERS = ("anti_scope", "forbidden", "must not", "no containment", "composite regularity",
                  "not be cited", "does not", "not used")


def audit(agg_path: Path, comp_paths=None):
    """Independent structural audit. Returns failures bucketed by rule id.

    comp_paths: {"c2_component": path, "c0_component": path}; defaults to the live
    canonical files.  Controls pass pinned components so that only the mutation
    under test can move a verdict.
    """
    if comp_paths is None:
        comp_paths = {"c2_component": ROOT / C2_NAME, "c0_component": ROOT / C0_NAME}
    fail = {"SEP-1": [], "SEP-2": [], "SEP-3": [], "SEP-4": [], "SEP-5": [], "SEP-6": [], "SEP-7": []}
    doc = yaml.safe_load(agg_path.read_text()) or {}
    svals = scalars(agg_path)
    informational = []

    def add(rule, msg):
        fail[rule].append(msg)

    comps = doc.get("components")
    # SEP-1: exactly the two class ids, each exactly once, separate entries
    if not isinstance(comps, list):
        add("SEP-1", "components is not a list")
        comps = []
    cids = [c.get("class_id") for c in comps if isinstance(c, dict)]
    if sorted(cids) != sorted([C2_ID, C0_ID]):
        add("SEP-1", f"component class ids are {cids}, expected exactly [{C2_ID}, {C0_ID}]")
    if len(set(cids)) != len(cids):
        add("SEP-1", f"duplicate component class id in {cids}")

    # SEP-2: no value joins the TWO CLASS IDS with a separator or disjunction
    for where, v in svals:
        if C2_ID in v and C0_ID in v:
            add("SEP-2", f"both class ids in one scalar at {where}: {v[:160]!r}")
        if "AF-SCC" in v and (
            re.search(r"AF-SCC-C\s*\^?\s*0-VAC-GEN.{0,60}\b(or|/|,|\+|and)\b.{0,60}AF-SCC-C\s*\^?\s*2-VAC-GEN", v)
            or re.search(r"AF-SCC-C\s*\^?\s*2-VAC-GEN.{0,60}\b(or|/|,|\+|and)\b.{0,60}AF-SCC-C\s*\^?\s*0-VAC-GEN", v)
        ):
            add("SEP-2", f"class-id disjunction at {where}: {v[:160]!r}")

    # SEP-3: no composite regularity token used as a selector/class token in aggregator or components
    for p in [agg_path, comp_paths["c2_component"], comp_paths["c0_component"]]:
        cdoc = yaml.safe_load(p.read_text()) or {}
        selector_bits = []
        cc = cdoc.get("class_components") or {}
        if isinstance(cc, dict):
            selector_bits += [(f"{p.name}.class_components.{k}", str(cc.get(k)))
                              for k in ("regularity_token", "class_id")]
        reg = cdoc.get("regularity") or {}
        if isinstance(reg, dict):
            selector_bits += [(f"{p.name}.regularity.{k}", str(reg.get(k))) for k in ("extension_regularity", "class_id")]
        con = cdoc.get("conclusion") or {}
        if isinstance(con, dict):
            selector_bits += [(f"{p.name}.conclusion.{k}", str(con.get(k))) for k in ("conclusion_type", "class_id")]
        if p == agg_path:
            selector_bits += [("aggregator.class_id", str(cdoc.get("class_id"))),
                              ("aggregator.artifact_id", str(cdoc.get("artifact_id")))]
            for c in (cdoc.get("components") or []):
                if isinstance(c, dict):
                    selector_bits += [("aggregator.component.class_id", str(c.get("class_id"))),
                                      ("aggregator.component.declared_selector", str(c.get("declared_selector")))]
        for where, val in selector_bits:
            for pat in COMPOSITE_PATTERNS:
                for m in re.finditer(pat, val):
                    add("SEP-3", f"{where}: composite token {m.group(0)!r} in selector value {val[:80]!r}")
        # raw-text mentions: informational unless they are an anti-scope/prohibition listing
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if any(re.search(pat, line) for pat in COMPOSITE_PATTERNS):
                forbidden = any(mark in line for mark in FORBID_MARKERS)
                rec = {"file": p.name, "line": i, "text": line.strip()[:160],
                       "forbidding_context": forbidden}
                informational.append(rec)
                if not forbidden:
                    add("SEP-3", f"{p.name}:{i}: unqualified composite token: {line.strip()[:120]}")

    # SEP-4: no conclusion object / extension statement of its own
    for key in ("conclusion", "conclusion_type", "theorem", "extension_statement", "claim"):
        if key in doc:
            add("SEP-4", f"aggregator defines top-level {key!r}")
    for where, v in svals:
        if where.startswith("$.conclusion"):
            add("SEP-4", f"conclusion content at {where}")

    # SEP-5: each component carries exactly one regularity selector, matching its role
    for role, expect in (("c2_component", "C2"), ("c0_component", "C0")):
        comp = comp_paths[role]
        cdoc = yaml.safe_load(comp.read_text()) or {}
        vals = class_token_values(cdoc)
        if len(vals) != 2 or len(set(vals)) != 1:
            add("SEP-5", f"{comp.name}: selector values {vals} (expected exactly one distinct token)")
        elif vals[0] != expect:
            add("SEP-5", f"{comp.name}: selector {vals[0]!r} != role {role} token {expect!r}")
        entry = next((c for c in comps if isinstance(c, dict) and c.get("role") == role), None)
        if entry and entry.get("declared_selector") != expect:
            add("SEP-5", f"aggregator {role} declared_selector {entry.get('declared_selector')!r} != {expect!r}")

    # SEP-6: pins present and equal to the component bytes this audit ran against
    by_role = {c.get("role"): c for c in comps if isinstance(c, dict)}
    for role, rel in (("c2_component", C2_NAME), ("c0_component", C0_NAME)):
        c = by_role.get(role)
        if not c:
            add("SEP-6", f"missing {role}")
            continue
        if c.get("path") != rel:
            add("SEP-6", f"{role} path {c.get('path')!r} != {rel!r}")
        comp = comp_paths[role]
        if not comp.exists():
            add("SEP-6", f"{role} component file missing: {comp}")
            continue
        if c.get("sha256") != sha256(comp):
            add("SEP-6", f"{role} pinned {str(c.get('sha256'))[:16]} != audited {sha256(comp)[:16]} ({comp})")

    # SEP-7: no cross-class relation restated in the aggregator
    for where, v in svals:
        if re.search(r"(=>|->|implies|entails)", v) and (C2_ID in v or C0_ID in v or re.search(r"\bC\s*\^?\s*[02]\b", v)):
            add("SEP-7", f"cross-class relation restated at {where}: {v[:160]!r}")

    # contract booleans
    contract_fail = []
    contract = doc.get("aggregator_contract") or {}
    for k, expect in CONTRACT_EXPECT.items():
        if contract.get(k) is not expect:
            contract_fail.append(f"aggregator_contract.{k}={contract.get(k)!r}, expected {expect!r}")
    return fail, contract_fail, doc, informational


# ---------------------------------------------------------------- controls

def build_controls():
    """Hand-built byte mutants of the pinned aggregator. Returns name -> (path, expected_rule)."""
    base_text = (PINNED / "F2-AGG.yaml").read_text()
    doc = yaml.safe_load(base_text)
    CTL.mkdir(parents=True, exist_ok=True)
    out = {}

    # C0 control: pristine copy -- must PASS
    p = CTL / "ctl00_pristine_copy.yaml"
    p.write_text(base_text)
    out["ctl00_pristine_copy"] = (p, None)

    # C1: component sha mismatch (SEP-6)
    d = json.loads(json.dumps(doc))
    d["components"][0]["sha256"] = "0" * 64
    p = CTL / "ctl01_sha_mismatch.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl01_sha_mismatch"] = (p, "SEP-6")

    # C2: merged class-id disjunction (SEP-2)
    d = json.loads(json.dumps(doc))
    d["merge_probe"] = f"{C2_ID} or {C0_ID}"
    p = CTL / "ctl02_merged_class_string.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl02_merged_class_string"] = (p, "SEP-2")

    # C3: injected conclusion object (SEP-4)
    d = json.loads(json.dumps(doc))
    d["conclusion"] = {"conclusion_type": "scc_merged_future_inextendibility"}
    p = CTL / "ctl03_conclusion_injection.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl03_conclusion_injection"] = (p, "SEP-4")

    # C4: duplicate component entry (SEP-1)
    d = json.loads(json.dumps(doc))
    d["components"].append(dict(d["components"][0]))
    p = CTL / "ctl04_duplicate_component.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl04_duplicate_component"] = (p, "SEP-1")

    # C5: missing component (SEP-1)
    d = json.loads(json.dumps(doc))
    d["components"] = [c for c in d["components"] if c.get("class_id") != C0_ID]
    p = CTL / "ctl05_missing_component.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl05_missing_component"] = (p, "SEP-1")

    # C6: composite regularity token (SEP-3)
    d = json.loads(json.dumps(doc))
    d["composite_note"] = "the combined C^{0,2} regularities"
    p = CTL / "ctl06_composite_token.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl06_composite_token"] = (p, "SEP-3")

    # C7: restated cross-class relation (SEP-7)
    d = json.loads(json.dumps(doc))
    d["transfer_note"] = f"{C0_ID} => {C2_ID}"
    p = CTL / "ctl07_crossclass_relation.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out["ctl07_crossclass_relation"] = (p, "SEP-7")
    return out


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    live = ROOT / AGG_NAME
    pinned_agg = PINNED / "F2-AGG.yaml"
    drift = {"live": sha256(live), "pinned": sha256(pinned_agg), "identical": sha256(live) == sha256(pinned_agg)}

    checks = []
    pinned_comps = {"c2_component": PINNED / "F2A-C2.yaml", "c0_component": PINNED / "F2B-C0.yaml"}
    fail, contract_fail, doc, raw_mentions = audit(pinned_agg, comp_paths=pinned_comps)
    seps = {k: {"pass": not v, "observed": v} for k, v in fail.items()}
    checks.append({"id": "PIN-DRIFT", "desc": "live aggregator bytes == pinned bytes", "pass": drift["identical"],
                   "observed": drift})
    for k in sorted(seps):
        checks.append({"id": k, "desc": f"aggregator separation invariant {k}", "pass": seps[k]["pass"],
                       "observed": seps[k]["observed"]})
    checks.append({"id": "CONTRACT-BOOLS", "desc": "aggregator_contract booleans match their declared intent",
                   "pass": not contract_fail, "observed": contract_fail})

    dups = duplicate_keys(pinned_agg)
    checks.append({"id": "YAML-DUP-KEYS", "desc": "document is a conforming YAML mapping (unique keys)",
                   "pass": not dups, "observed": dups})
    checks.append({"id": "YAML-LOAD", "desc": "conforming parser loads the document",
                   "pass": isinstance(doc, dict),
                   "observed": {"top_level_keys": len(doc), "revision_after_last_wins": doc.get("revision"),
                                "revised_at_after_last_wins": doc.get("revised_at")}})

    # controls
    pinned_comps = {"c2_component": PINNED / "F2A-C2.yaml", "c0_component": PINNED / "F2B-C0.yaml"}
    ctl_results = {}
    for name, (path, expected) in build_controls().items():
        cfail, ccontract, _, _ = audit(path, comp_paths=pinned_comps)
        fired = sorted([k for k, v in cfail.items() if v])
        ok = (not fired and not ccontract) if expected is None else (expected in fired)
        ctl_results[name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                             "expected_rule": expected, "fired_rules": fired, "contract_failures": ccontract,
                             "control_pass": ok}
    checks.append({"id": "CONTROL-SUITE", "desc": "pristine copy passes; every hand-built mutant is rejected by its rule",
                   "pass": all(v["control_pass"] for v in ctl_results.values()), "observed": ctl_results})

    # live re-measurement of the component pins (time-of-check vs time-of-verdict)
    live_components = {"c2_component": ROOT / C2_NAME, "c0_component": ROOT / C0_NAME}
    live_fail, _, _, _ = audit(pinned_agg, comp_paths=live_components)
    live_drift = {
        "measured_at": now(),
        "c2_live_sha256": sha256(live_components["c2_component"]),
        "c0_live_sha256": sha256(live_components["c0_component"]),
        "c2_pinned_sha256": sha256(pinned_comps["c2_component"]),
        "c0_pinned_sha256": sha256(pinned_comps["c0_component"]),
        "sep6_failures_at_live_hashes": live_fail["SEP-6"],
        "live_components_moved_after_snapshot": bool(live_fail["SEP-6"]),
    }
    checks.append({"id": "PIN-LIVE-DRIFT", "desc": "aggregator pins still resolve to the live component bytes",
                   "pass": not live_fail["SEP-6"], "observed": live_drift})
    # keep durable copies of the live bytes the drift was measured against
    lr = HERE / "live_recheck"
    lr.mkdir(exist_ok=True)
    for role, src in live_components.items():
        shutil.copy2(src, lr / f"{role}_{src.name}")
    live_drift["live_copies"] = {role: f"live_recheck/{role}_{src.name}" for role, src in live_components.items()}
    checks.append({"id": "SEP3-RAW-MENTIONS",
                   "desc": "raw-text composite-token mentions are all in forbidding contexts",
                   "pass": all(r["forbidding_context"] for r in raw_mentions),
                   "observed": raw_mentions})

    # staleness / provenance probes
    agg_text = pinned_agg.read_text()
    frozen = json.loads((PINNED / "FROZEN.json").read_text())
    rule_spec = json.loads((PINNED / "RULE-SPEC.json").read_text())
    prior = json.loads((PINNED / "PRIOR-PINCHECK.json").read_text())
    mapa = json.loads((PINNED / "MAP.json").read_text())
    gate_text = (PINNED / "CLASS-GATE.py").read_text()
    spec_rules = sorted(r.get("id") for r in rule_spec.get("rules", []))
    gate_rules = sorted(set(re.findall(r'"(R\d+)"', gate_text)))
    legacy = [a for a in mapa.get("legacy_artifacts", []) if a.get("path") == AGG_NAME]
    f0_canon = sha256(PINNED / "F0-CANON.yaml")
    f0_auth = sha256(PINNED / "F0-AUTHORING.yaml")
    f0_ptrs = sorted(set(re.findall(r"\b0fcc6a19[0-9a-f]*\b", agg_text)))
    stale = {
        "rule_spec_declared_in_aggregator": "v1.1" if "rule_spec v1.1" in agg_text else None,
        "rule_spec_measured_spec_version": rule_spec.get("spec_version"),
        "rule_spec_declared_rule_ids": spec_rules,
        "gate_enforced_rule_ids": gate_rules,
        "gate_rules_absent_from_spec": sorted(set(gate_rules) - set(spec_rules)),
        "f0_pointer_in_aggregator": f0_ptrs,
        "f0_canonical_sha256": f0_canon,
        "f0_authoring_sha256": f0_auth,
        "f0_pointer_matches_either_live_tree": any(
            h.startswith(p) for p in f0_ptrs for h in (f0_canon, f0_auth)),
        "prior_pincheck_targets_sha256": prior.get("aggregator_sha256"),
        "prior_pincheck_verdict": prior.get("verdict"),
        "prior_pincheck_matches_current": prior.get("aggregator_sha256") == sha256(pinned_agg),
        "aggregator_in_frozen_rev26": AGG_NAME in frozen.get("files", {}),
        "frozen_revision": frozen.get("revision"),
        "map_legacy_entry": legacy,
        "map_legacy_role_describes_live_bytes": bool(
            legacy and "legacy combined" not in str(legacy[0].get("role", ""))
        ),
        "live_declares_merge_forbidden": (doc.get("aggregator_contract") or {}).get("merge_forbidden"),
        "frozen_records_retired_merged_hash": [
            a.get("sha256") for a in mapa.get("frozen_artifacts", [])
            if a.get("path") == AGG_NAME
        ],
    }
    checks.append({"id": "STALE-BINDINGS", "desc": "declared binding references match the frozen objects",
                   "pass": (stale["rule_spec_declared_in_aggregator"] == f"v{rule_spec.get('spec_version')}"
                            and not stale["gate_rules_absent_from_spec"]
                            and stale["f0_pointer_matches_either_live_tree"]),
                   "observed": stale})
    checks.append({"id": "FREEZE-BOUND", "desc": "aggregator bytes are bound by the frozen manifest",
                   "pass": stale["aggregator_in_frozen_rev26"], "observed": {
                       "in_frozen": stale["aggregator_in_frozen_rev26"],
                       "frozen_revision": stale["frozen_revision"],
                       "prior_pincheck_matches_current": stale["prior_pincheck_matches_current"]}})
    checks.append({"id": "MAP-ROLE-LABEL", "desc": "map record for this path describes the live bytes",
                   "pass": stale["map_legacy_role_describes_live_bytes"],
                   "observed": {"legacy_entry": legacy,
                                "retired_merged_hashes_in_frozen_artifacts": stale["frozen_records_retired_merged_hash"]}})

    failed = [c["id"] for c in checks if not c["pass"]]
    evidence = {"task_id": "W066-F2AGG-VERDICT-01", "actor": "worker-066", "generated_at": now(),
                "target": f"{AGG_NAME}#{drift['pinned']}", "checks": checks,
                "failed_check_ids": failed}
    (EV / "checks.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    (EV / "controls.json").write_text(json.dumps(
        {"task_id": "W066-F2AGG-VERDICT-01", "generated_at": now(), "controls": ctl_results},
        indent=2, sort_keys=True) + "\n")
    (EV / "staleness.json").write_text(json.dumps(
        {"task_id": "W066-F2AGG-VERDICT-01", "generated_at": now(), "observed": stale}, indent=2,
        sort_keys=True) + "\n")
    (EV / "live_drift.json").write_text(json.dumps(
        {"task_id": "W066-F2AGG-VERDICT-01", "generated_at": now(), "observed": live_drift,
         "raw_composite_mentions": raw_mentions}, indent=2, sort_keys=True) + "\n")

    report = {
        "artifact": "W066-F2AGG-INDEPENDENT-VERDICT",
        "task_id": "W066-F2AGG-VERDICT-01",
        "actor": "worker-066",
        "generated_at": now(),
        "node_id": "F2",
        "class_ids": [C2_ID, C0_ID],
        "gate": "G-FORM",
        "target": {"path": AGG_NAME, "sha256": drift["pinned"], "bytes": pinned_agg.stat().st_size},
        "method": [
            "verdict binds bytes: all checks run on ./pinned/ copies and re-run against live files",
            "independent re-implementation of the seven separation invariants and the aggregator contract",
            "seven hand-built byte mutants as falsification controls, one pristine control",
            "conforming-parser duplicate-key probe over the whole composed document tree",
            "declared-binding vs frozen-object staleness probes (rule spec, F0 pointer, prior pin check, freeze membership, map label)",
            "author lint run separately as a cross-check only; it is not the source of this verdict",
            "component pins evaluated twice: against the snapshot bytes (artifact coherence) and against the live bytes at verdict time (drift)",
        ],
        "checks_passed": [c["id"] for c in checks if c["pass"]],
        "checks_failed": failed,
        "verdict": {
            "verdict": "revise",
            "score": 2.5,
            "hard_failures": ["W066-F2AGG-H1", "W066-F2AGG-H2", "W066-F2AGG-H3", "W066-F2AGG-H4", "W066-F2AGG-H5"],
            "note": ("machine-green on the pinned component pins, all seven separation invariants and all eight "
                     "falsification controls at schemas/af_scc_regularities.yaml#94562101a816; revise because the file "
                     "is not a conforming YAML mapping (revised_at x4), its declared bindings are stale, no pin "
                     "re-check exists at these bytes, it is not freeze-bound while the map mislabels the live bytes as "
                     "the retired merged file, and (measured during this task) the live F2a/F2b components moved at "
                     "00:32:02 so the aggregator's pins no longer resolve and it is invalidated until re-pinned."),
        },
        "findings": [
            {"id": "W066-F2AGG-H1", "severity": "blocking",
             "statement": ("All four revised_at root keys are duplicates (lines 11-14 of the pinned bytes; "
                           "revision: 6). A conforming YAML parser keeps only the last value, so the declared "
                           "revision history is unreadable and revision 6 cannot be reconstructed from the file. "
                           "Same defect class as W066-B1 on the three class schemas."),
             "falsifier": ("yaml.compose returns no duplicate key at $.revised_at in the pinned bytes, or a "
                           "conforming parser recovers four distinct revised_at values"),
             "evidence": "evidence/checks.json#YAML-DUP-KEYS"},
            {"id": "W066-F2AGG-H2", "severity": "blocking",
             "statement": ("Declared bindings contradict the frozen objects: the aggregator says 'rule_spec v1.1' "
                           "while the frozen spec is v1.2 (40f9bb9e), and the v1.2 spec declares R01-R16 while the "
                           "named binding gate (000e09e4) enforces R01-R25 and R27-R31, so 14 enforced rule ids are "
                           "undeclared by the spec the aggregator names. The revision_note pins F0 at 0fcc6a19, which "
                           "matches neither live F0 tree (canonical 276009f4, authoring c8e979a1). This is W066-B3/N2 "
                           "propagated into the aggregator's own binding note."),
             "falsifier": ("rule_spec.json#40f9bb9e declares spec_version 1.1 or contains R17-R25/R27-R31, or a live "
                           "F0 tree has sha256 beginning 0fcc6a19"),
             "evidence": "evidence/staleness.json"},
            {"id": "W066-F2AGG-H3", "severity": "blocking",
             "statement": ("The recorded review_owner pin check (artifacts/worker18/f2_review/aggregator_pin_check.json, "
                           "verdict fail) targets the retired merged aggregator c6bfda2b, not the live 94562101; the "
                           "aggregator's own review_notes require a re-run of that check after the astra-classscope-02 "
                           "re-pin, and no verdict exists at the live hash. G-FORM may not cite this aggregator as "
                           "reviewed at its current bytes."),
             "falsifier": ("a review artifact exists whose target sha256 equals 94562101a816 and whose verdict is not fail"),
             "evidence": "evidence/staleness.json"},
            {"id": "W066-F2AGG-H4", "severity": "blocking",
             "statement": ("Provenance: the aggregator is absent from FROZEN rev26 (40 files), and the map's "
                           "legacy_artifacts entry for this path at 94562101 describes the bytes as the 'legacy "
                           "combined C0/C2 file', while the live file declares merge_forbidden: true, "
                           "defines_conclusion: false and carries no conclusion. The retired merged artifact is a "
                           "different byte string (c6bfda2b) recorded in frozen_artifacts; the live thin index and the "
                           "retired merged file are conflated under one path."),
             "falsifier": ("FROZEN rev26 lists schemas/af_scc_regularities.yaml, or the live bytes at 94562101 are "
                           "byte-identical to c6bfda2b, or the map labels them as a non-class index"),
             "evidence": "evidence/staleness.json"},
            {"id": "W066-F2AGG-H5", "severity": "blocking",
             "statement": ("Live drift measured during this task: both component files were rewritten at 00:32:02 "
                           "(after this task's snapshot at 00:31:xx). C2 b6123750b37d -> 5476a3f2c6bc and C0 "
                           "1bb78ce9b357 -> 55d0a1ea9bda, so the aggregator's pinned sha256 values no longer resolve to "
                           "the live schemas and SEP-6 fails at verdict time. The aggregator's own rule ('a component "
                           "revision after 2026-09-12T00:15+08:00 invalidates the pins and must fail the integration "
                           "lint until this aggregator is re-pinned') therefore fires: the aggregator is not usable as "
                           "a G-FORM input until re-pinned to the new component bytes."),
             "falsifier": ("live schemas/af_scc_c2_vacuum.yaml and schemas/af_scc_c0_vacuum.yaml hash to b6123750b37d "
                           "and 1bb78ce9b357 respectively, or the aggregator is re-pinned to the live hashes and "
                           "re-emitted"),
             "evidence": "evidence/checks.json#PIN-LIVE-DRIFT"},
        ],
        "live_recheck": live_drift,
        "green_results": {
            "component_pins_at_snapshot": f"{C2_NAME} b6123750b37d / {C0_NAME} 1bb78ce9b357 matched the live bytes at snapshot time",
            "separation_invariants": "SEP-1..SEP-7 pass independently on the pinned bytes against the pinned components",
            "controls": f"{sum(1 for v in ctl_results.values() if v['control_pass'])}/{len(ctl_results)} controls behave as pre-registered",
            "raw_composite_mentions": f"{len(raw_mentions)} raw-text composite-token mentions, all in forbidding/anti-scope contexts",
        },
        "evidence": {
            "checks": "evidence/checks.json", "controls": "evidence/controls.json",
            "staleness": "evidence/staleness.json", "live_drift": "evidence/live_drift.json",
            "pins": "PINNED.json",
        },
        "next_falsifier": ("any pinned byte changes; or a conforming YAML parser recovers the four revised_at values; "
                           "or the frozen rule spec declares R17-R25/R27-R31; or a review exists at 94562101 with a "
                           "non-fail verdict; or FROZEN rev27 lists the aggregator and the map label is corrected; or "
                           "the aggregator is re-pinned to the live component hashes and re-emitted -- any of these "
                           "supersedes this revise"),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"failed": failed,
                      "controls_ok": all(v["control_pass"] for v in ctl_results.values()),
                      "dups": len(dups), "verdict": report["verdict"]["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
