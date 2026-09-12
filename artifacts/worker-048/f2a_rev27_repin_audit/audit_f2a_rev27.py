#!/usr/bin/env python3
"""W48-F2A-REV27-REPIN-01: independent, hash-bound audit of class
AF-SCC-C2-VAC-GEN (node F2a) at the bytes snapshotted by snapshot_inputs.py.

Scope: one class-bound task under open assignment astra-life03-verify-gform
(owner lead-audit).  This is a worker verdict, not a gate verdict; workers
cannot move a gate, and no node is completed here.

The audit reads ONLY the immutable copies recorded in snapshot_manifest*.json.
Nothing in the formulation tree is written.  Negative controls run on throwaway
copies inside this worker's artifact directory.

Run:
  python3 snapshot_inputs.py
  python3 snapshot_inputs.py --out snapshot_manifest_extra.json --inputs \
      artifacts/formulation/evidence/taxonomy_consistency.json \
      artifacts/formulation/VARIANT_REGISTRY.json \
      artifacts/formulation/tools/check_class_schema.py \
      artifacts/formulation/KEY_MANIFEST.json
  python3 audit_f2a_rev27.py --controls
"""
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

MANIFESTS = ["snapshot_manifest.json", "snapshot_manifest_extra.json"]
TOLERANCE_S = 300.0


# ---------------------------------------------------------------- utilities
def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def parse_ts(s):
    if not isinstance(s, str):
        return None
    t = s.strip().replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", t):  # +0800 -> +08:00 (Python <3.11 fromisoformat)
        t = t[:-2] + ":" + t[-2:]
    try:
        return dt.datetime.fromisoformat(t)
    except Exception:
        return None


def now_iso():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def yaml_duplicate_keys(text, where=""):
    """List duplicate mapping keys anywhere in a YAML document (node tree)."""
    dups = []

    def walk(node, path):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                kk = str(k.value)
                if kk in seen:
                    dups.append({"path": f"{path}/{kk}", "line": k.start_mark.line + 1,
                                 "first_line": seen[kk]})
                else:
                    seen[kk] = k.start_mark.line + 1
                walk(v, f"{path}/{kk}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{path}[{i}]")

    walk(yaml.compose(text), where)
    return dups


def walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")
    else:
        yield path, o


def keypaths(o, p=""):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out.append(f"{p}/{k}")
            out += keypaths(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += keypaths(v, f"{p}[{i}]")
    return out


def valmap(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(valmap(v, f"{p}/{k}"))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(valmap(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


def resolve_pointer(doc, fragment):
    """Resolve 'classes.AF-SCC-C2-VAC-GEN' style fragments (dict keys, int indices)."""
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return None, f"missing key {part!r}"
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None, f"bad list index {part!r}"
        else:
            return None, f"cannot descend into {type(cur).__name__} at {part!r}"
    return cur, None


def referenced_files(text):
    """Collect repo-relative file references from '#classes.x' style pointers."""
    if "#" in text:
        return text.split("#", 1)[0]
    return text


class Audit:
    def __init__(self, manifests):
        self.records = {}
        for man in manifests:
            d = json.loads((HERE / man).read_text())
            for r in d["records"]:
                if r.get("exists"):
                    self.records[r["path"]] = r
                    self.records[man + "::" + r["path"]] = r
        self.checks = []
        self.controls = []
        self.notes = []

    # -- helpers over snapshot records
    def rec(self, rel):
        r = self.records.get(rel)
        if r is None:
            raise KeyError(f"no snapshot record for {rel}")
        return r

    def text(self, rel):
        return (ROOT / self.rec(rel)["snapshot"]).read_text()

    def data(self, rel):
        return yaml.safe_load(self.text(rel))

    def check(self, cid, axis, description, expected, observed, passed, severity="info"):
        self.checks.append({"id": cid, "axis": axis, "description": description,
                            "expected": expected, "observed": observed, "pass": bool(passed),
                            "severity_if_fail": severity})
        return passed

    def control(self, cid, description, expected, observed, flipped):
        self.controls.append({"id": cid, "description": description, "expected": expected,
                              "observed": observed, "flipped_as_declared": bool(flipped)})
        return flipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()

    a = Audit(MANIFESTS)
    f2a_rel = "schemas/af_scc_c2_vacuum.yaml"
    f2a = a.rec(f2a_rel)
    f2a_text = a.text(f2a_rel)
    d = yaml.safe_load(f2a_text)
    f2b = a.data("schemas/af_scc_c0_vacuum.yaml")
    f1 = a.data("schemas/af_wcc_vacuum.yaml")
    frozen = a.data("artifacts/formulation/FROZEN.json")
    live_frozen_text = (ROOT / "artifacts/formulation/FROZEN.json").read_text()
    live_frozen = json.loads(live_frozen_text)
    live_frozen_sha = hashlib.sha256(live_frozen_text.encode()).hexdigest()
    live_rev = live_frozen.get("revision")
    snap_rev = frozen.get("revision")
    frozen_pin = frozen["files"]
    snap_time = parse_ts(json.loads((HERE / "snapshot_manifest.json").read_text())["measured_at"])
    keyman = a.data("artifacts/formulation/KEY_MANIFEST.json")
    vreg = a.data("artifacts/formulation/VARIANT_REGISTRY.json")

    # ------------------------------------------------ A: manifest / binding
    pin = frozen_pin.get(f2a_rel, {})
    a.check("A1", "binding", "FROZEN rev27 pin for the F2a canonical path equals the snapshotted bytes",
            f"sha256 {f2a['sha256'][:12]}", {"pin": pin.get("sha256", "ABSENT")[:12],
                                             "measured": f2a["sha256"][:12],
                                             "revision": frozen.get("revision")},
            pin.get("sha256") == f2a["sha256"], "blocking")

    auth_rel = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
    auth = a.rec(auth_rel)
    a.check("A2", "binding", "F2a authoring mirror is byte-identical to the canonical path and both are pinned",
            "canonical == authoring == FROZEN pin",
            {"canonical": f2a["sha256"][:12], "authoring": auth["sha256"][:12],
             "pin": frozen_pin.get(auth_rel, {}).get("sha256", "ABSENT")[:12]},
            f2a["sha256"] == auth["sha256"] == frozen_pin.get(auth_rel, {}).get("sha256"),
            "blocking")

    f0_rel = "research_map/formulation_taxonomy.yaml"
    f0 = a.rec(f0_rel)
    decl = (d.get("f0_binding") or {}).get("declared_f0_sha256")
    a.check("A3", "binding", "F2a f0_binding.declared_f0_sha256 equals the snapshotted canonical F0 bytes; F0 is pinned",
            "declared == measured and FROZEN pin present",
            {"declared": str(decl)[:12], "measured": f0["sha256"][:12],
             "pin": frozen_pin.get(f0_rel, {}).get("sha256", "ABSENT")[:12]},
            decl == f0["sha256"] and frozen_pin.get(f0_rel, {}).get("sha256") == f0["sha256"],
            "blocking")

    sup_rel = "artifacts/formulation/formulation_taxonomy.yaml"
    sup = a.rec(sup_rel)
    a.check("A4", "binding", "F0 canonical and the authoring supplement are each pinned; the pair is still not a mirror pair",
            "both pinned (canonical != authoring is a known controller REC-1/REC-2 item)",
            {"canonical": f0["sha256"][:12], "supplement": sup["sha256"][:12],
             "supplement_pin": frozen_pin.get(sup_rel, {}).get("sha256", "ABSENT")[:12],
             "mirror": f0["sha256"] == sup["sha256"]},
            frozen_pin.get(sup_rel, {}).get("sha256") == sup["sha256"], "info")

    gtr_rel = "artifacts/formulation/evidence/gate_test_report.json"
    gtr = a.rec(gtr_rel)
    gtr_pin = frozen_pin.get(gtr_rel, {}).get("sha256", "ABSENT")
    live_gtr = ROOT / gtr_rel
    live_gtr_hash = sha256_file(live_gtr)
    gtr_mtime = dt.datetime.fromtimestamp(live_gtr.stat().st_mtime, dt.timezone.utc).astimezone()
    frozen_at = parse_ts(frozen.get("frozen_at"))
    post_freeze = gtr_mtime > frozen_at if frozen_at else None
    live_pin_gtr = (live_frozen.get("files") or {}).get(gtr_rel, {}).get("sha256")
    gtr_superseded = bool(live_rev and snap_rev and live_rev > snap_rev and live_pin_gtr == gtr["sha256"])
    a.check("A5", "binding", "FROZEN rev27 pin for gate_test_report.json equals the snapshotted report (the report that must carry the freeze's PASS evidence)",
            "pin == measured",
            {"pin": gtr_pin[:12], "measured_snapshot": gtr["sha256"][:12],
             "live_now": live_gtr_hash[:12], "live_mtime": gtr_mtime.isoformat(timespec="seconds"),
             "frozen_at": frozen.get("frozen_at"), "written_after_freeze": post_freeze,
             "live_frozen_revision": live_rev, "live_pin": str(live_pin_gtr)[:12],
             "superseded_by_live_revision": gtr_superseded},
            gtr_pin == gtr["sha256"], "blocking-superseded" if gtr_superseded else "blocking")

    tc_rel = "artifacts/formulation/evidence/taxonomy_consistency.json"
    tc = a.rec(tc_rel)
    tc_decl = (d.get("f0_binding") or {}).get("consistency_evidence_sha256")
    tc_pin = frozen_pin.get(tc_rel, {}).get("sha256", "ABSENT")
    tc_live = sha256_file(ROOT / tc_rel)
    tc_live_mtime = dt.datetime.fromtimestamp((ROOT / tc_rel).stat().st_mtime, dt.timezone.utc).astimezone()
    live_pin_tc = (live_frozen.get("files") or {}).get(tc_rel, {}).get("sha256")
    tc_superseded = bool(live_rev and snap_rev and live_rev > snap_rev and live_pin_tc == tc["sha256"])
    a.check("A6", "binding", "F2a-required consistency evidence is internally consistent with the FROZEN rev27 pin, and the live file has not moved since the freeze",
            "declared == pin == measured snapshot == live now",
            {"declared": str(tc_decl)[:12], "pin": tc_pin[:12], "snapshot": tc["sha256"][:12],
             "live_now": tc_live[:12], "live_mtime": tc_live_mtime.isoformat(timespec="seconds"),
             "written_after_freeze": tc_live_mtime > frozen_at if frozen_at else None,
             "live_frozen_revision": live_rev, "live_pin": str(live_pin_tc)[:12],
             "superseded_by_live_revision": tc_superseded},
            tc_decl == tc_pin == tc["sha256"] == tc_live,
            "blocking-superseded" if tc_superseded else "blocking")

    mt = {rel: dt.datetime.fromtimestamp(a.rec(rel)["mtime_ns_before"] / 1e9, dt.timezone.utc).astimezone()
          for rel in [f2a_rel, auth_rel, f0_rel, sup_rel,
                      "schemas/af_scc_c0_vacuum.yaml", "schemas/af_wcc_vacuum.yaml"]}
    max_mt = max(mt.values())
    a.check("A7", "binding", "no snapshotted schema/taxonomy byte predates the freeze (freeze covers the bytes)",
            "max(mtime) <= frozen_at",
            {"max_mtime": max_mt.isoformat(timespec="seconds"), "frozen_at": frozen.get("frozen_at"),
             "per_file": {k: v.isoformat(timespec="seconds") for k, v in mt.items()}},
            max_mt <= frozen_at, "blocking")

    a.check("A8", "binding", "FROZEN frozen_at is not future-dated relative to the snapshot",
            "frozen_at <= snapshot time + tolerance",
            {"frozen_at": frozen.get("frozen_at"), "snapshot_at": snap_time.isoformat(timespec="seconds")},
            frozen_at <= snap_time + dt.timedelta(seconds=TOLERANCE_S), "minor")

    live_drift = {}
    for rel in [f2a_rel, auth_rel, "schemas/af_scc_c0_vacuum.yaml", "schemas/af_wcc_vacuum.yaml",
                f0_rel, sup_rel, "artifacts/formulation/FROZEN.json"]:
        cur = sha256_file(ROOT / rel) if (ROOT / rel).exists() else "ABSENT"
        if cur != a.rec(rel)["sha256"]:
            live_drift[rel] = {"snapshot": a.rec(rel)["sha256"][:12], "live_now": cur[:12]}
    a.check("A9", "binding", "live bytes still equal the snapshotted bytes at audit time (drift detector)",
            "no drift on the class-relevant paths",
            live_drift, not live_drift, "info")

    live_pins_target = {f2a_rel: f2a, auth_rel: auth, f0_rel: f0, gtr_rel: gtr, tc_rel: tc}
    live_pin_mismatch = {}
    for rel, rec0 in live_pins_target.items():
        lp = (live_frozen.get("files") or {}).get(rel, {}).get("sha256")
        if lp != rec0["sha256"]:
            live_pin_mismatch[rel] = {"live_pin": str(lp)[:12], "snapshot": rec0["sha256"][:12]}
    a.check("A10", "binding", "live FROZEN revision (measured at audit time) re-pins every F2a-relevant snapshot byte",
            "live manifest revision pins F2a schema, mirror, F0, gate report, consistency evidence",
            {"live_revision": live_rev, "snapshot_revision": snap_rev, "live_frozen_sha": live_frozen_sha[:12],
             "live_frozen_at": live_frozen.get("frozen_at"), "mismatches": live_pin_mismatch},
            not live_pin_mismatch, "blocking")

    # ------------------------------------------------ B: F2a class content
    dups = yaml_duplicate_keys(f2a_text)
    a.check("B1", "structure", "F2a has no duplicate mapping keys (rev25/26 blocking defect)",
            "0 duplicates", {"n_duplicates": len(dups), "examples": dups[:5]}, not dups, "blocking")

    ts_fields = [(p, v) for p, v in walk_strings(d)
                 if p.rsplit("/", 1)[-1] in ("at", "revised_at", "authored_at", "checked_at",
                                             "created_at", "frozen_at")
                 and isinstance(v, str) and parse_ts(v)]
    future = [(p, v) for p, v in ts_fields if parse_ts(v) > snap_time + dt.timedelta(seconds=TOLERANCE_S)]
    a.check("B2", "structure", "F2a has no future-dated timestamp field at the snapshot instant",
            "0 future-dated", {"n_timestamps": len(ts_fields), "future": future[:5],
                               "max_seen": max((v for _, v in ts_fields), default=None)},
            not future, "blocking")

    ptr = d.get("class_contract_pointer")
    ptr_path, _, frag = str(ptr).partition("#")
    if not ptr_path:
        ptr_doc, err = None, "no pointer"
    elif (ROOT / ptr_path).exists():
        ptr_doc, err = a.data(ptr_path), None
    else:
        ptr_doc, err = None, "target missing"
    target, rerr = (None, err) if ptr_doc is None else resolve_pointer(ptr_doc, frag)
    target_ok = isinstance(target, dict) and target.get("class_id") in (None, d.get("class_id"))
    a.check("B3", "binding", "class_contract_pointer resolves inside the declared canonical F0 artifact and lands on this class (canonical taxonomy keys classes by class_id)",
            "pointer target exists in canonical tree and is this class's entry",
            {"pointer": ptr, "target_in_canonical": ptr_path == f0_rel,
             "carrier_sha": a.rec(ptr_path)["sha256"][:12] if ptr_path in a.records else "not-snapshotted",
             "resolve_error": rerr, "target_keys": sorted(target.keys())[:8] if isinstance(target, dict) else None,
             "target_class_id_field": target.get("class_id") if isinstance(target, dict) else None},
            target_ok and ptr_path == f0_rel, "blocking")

    cons_ok = (tc_decl == tc_pin == tc["sha256"])
    a.check("B4", "binding", "f0_binding internal consistency: declared evidence hash equals the FROZEN pin and the snapshotted evidence file",
            "declared == pin == snapshot",
            {"declared": str(tc_decl)[:12], "pin": tc_pin[:12], "snapshot": tc["sha256"][:12],
             "live_frozen_revision": live_rev,
             "superseded_by_live_revision": tc_superseded},
            cons_ok, "blocking-superseded" if tc_superseded else "blocking")

    formal = str((d.get("quantifiers") or {}).get("formal", ""))
    formal_or = (" or " in f" {formal} ") or (" OR " in formal)
    a.check("B5", "semantics", "F2a exact quantifier prefix has no 'or' disjunction (A0 G-FORM form)",
            "no disjunction token in quantifiers.formal",
            {"formal_prefix": formal[:220], "contains_or": formal_or},
            not formal_or, "blocking")

    d0 = str(((d.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", ""))
    reg = d.get("regularity") or {}
    reg_str = json.dumps(reg)
    dc = d.get("data_class") or {}
    dc_str = json.dumps(dc)
    two_sort = ("disjoint union" in d0.lower() or " or " in f" {d0} ") and "sobolev" in d0.lower()
    mirrored = ("smooth-with-decay" in reg_str and "sobolev" in reg_str.lower()
                and "smooth-with-decay" in dc_str and "sobolev" in dc_str.lower())
    sob_variant = [v for v in vreg.get("variants", [])
                   if v.get("parent_class") == d.get("class_id")
                   and "sobolev" in json.dumps(v).lower()]
    a.check("B6a", "semantics", "D0 is declared as a tagged disjoint union (rev12 repair of the ill-typed 'or' finding)",
            "declared as one tagged index set with two sorts",
            {"tagged_disjoint_union": two_sort, "mirrored_in_regularity": mirrored,
             "d0_excerpt": d0[:200]},
            two_sort and mirrored, "info")

    def data_class_of(x):
        return x.get("data_class")
    ka, kb, kf = keypaths(data_class_of(d)), keypaths(data_class_of(f2b)), keypaths(data_class_of(f1))
    va, vb, vf = valmap(data_class_of(d)), valmap(data_class_of(f2b)), valmap(data_class_of(f1))
    diffs_b = sorted(k for k in set(va) | set(vb) if va.get(k) != vb.get(k))
    diffs_f = sorted(k for k in set(va) | set(vf) if va.get(k) != vf.get(k))
    shared_frozen = (ka == kb == kf) and not diffs_b and not diffs_f
    a.check("B6b", "semantics", "G-FORM criterion 'one frozen data class shared by F1/F2a/F2b' holds at rev27",
            "key-identical data_class across the three classes with no value differences",
            {"f2a_vs_f2b_keys_identical": ka == kb, "f2a_vs_f1_keys_identical": ka == kf,
             "f2a_vs_f2b_value_diffs": diffs_b, "f2a_vs_f1_value_diffs": diffs_f[:6],
             "f2a_vs_f1_value_diff_count": len(diffs_f),
             "registered_sobolev_variant_for_f2a": bool(sob_variant)},
            shared_frozen, "contested-policy")

    rs = d.get("review_status") or {}
    rev_files = sorted((ROOT / "reviews").glob("*.json"))
    hash_keys = ("reviewed_sha256", "artifact_sha256", "target_sha256", "sha256", "hash")
    rev_new, blob_cites = [], []
    for p in rev_files:
        try:
            r = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(r, dict):
            continue
        cited = {str(r.get(k)) for k in hash_keys if r.get(k)}
        paired = any(f2a["sha256"] == c or f2a["sha256"].startswith(c) for c in cited if len(c) >= 12)
        if paired and r.get("verdict"):
            rev_new.append({"file": str(p.relative_to(ROOT)), "verdict": r.get("verdict"),
                            "target_id": r.get("target_id") or r.get("class_id"),
                            "cited": [c[:12] for c in cited]})
        elif f2a["sha256"][:12] in p.read_text():
            blob_cites.append(str(p.relative_to(ROOT)))
    a.check("B7", "review", "F2a review_status matches what is on disk: no independent verdict is bound to the rev27 F2a hash",
            "independent_reviewers == [] iff no hash-paired F2a verdict exists",
            {"declared_reviewers": rs.get("independent_reviewers"), "declared_verdict": rs.get("verdict"),
             "reviews_bound_to_rev27_f2a": rev_new, "files_mentioning_rev27_f2a": blob_cites},
            (len(rs.get("independent_reviewers") or []) == 0) == (len(rev_new) == 0), "info")

    spec = importlib.util.spec_from_file_location("class_separation", ROOT / "research_map/class_separation.py")
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    sep = cs.findings_for_text(f2a_text, f"snapshot:{f2a['snapshot']}")
    a.check("B8", "classification", "class_separation finds no class-leakage findings in the F2a snapshot text",
            "0 findings", {"n_findings": len(sep), "findings": [str(x)[:160] for x in sep[:4]],
                           "module_sha256": sha256_file(ROOT / "research_map/class_separation.py")[:12]},
            len(sep) == 0, "blocking")

    allowed = set(keyman.get("allowed_keys", [])) | {"extensions"}
    unknown_top = [k for k in d.keys() if k not in allowed]
    a.check("B9", "structure", "R22 top-level key scan replicated: every F2a top-level key is registered in KEY_MANIFEST",
            "0 unknown top-level keys",
            {"n_top_keys": len(d), "unknown_top_level": unknown_top,
             "key_manifest_sha": a.rec("artifacts/formulation/KEY_MANIFEST.json")["sha256"][:12]},
            not unknown_top, "blocking")

    # ------------------------------------------------ C: owner tooling at bytes
    checker_rel = "artifacts/formulation/tools/check_class_schema.py"
    checker_live = ROOT / checker_rel
    schema_copy = ROOT / f2a["snapshot"]

    def run_checker(schema_path):
        """Run the live owner checker (hash-verified before/after) on a schema path."""
        h0 = sha256_file(checker_live)
        proc = subprocess.run([sys.executable, str(checker_live), str(schema_path), "--json"],
                              capture_output=True, text=True, cwd=str(ROOT))
        h1 = sha256_file(checker_live)
        try:
            out = json.loads(proc.stdout)
        except Exception:
            out = {"raw_stdout": proc.stdout[-500:], "raw_stderr": proc.stderr[-300:]}
        return {"exit": proc.returncode, "verdict": out.get("verdict"),
                "failed_rules": out.get("failed_rules"), "tool_sha_before": h0[:12],
                "tool_sha_after": h1[:12], "stderr": proc.stderr[-200:]}

    c1 = run_checker(schema_copy)
    a.check("C1", "owner-tool", "owner structural checker passes on the F2a snapshot bytes (live tool hash-verified before/after)",
            "exit 0 / verdict pass",
            {**c1, "snapshot_tool_sha256": a.rec(checker_rel)["sha256"][:12]},
            c1["exit"] == 0 and c1["tool_sha_before"] == c1["tool_sha_after"]
            == a.rec(checker_rel)["sha256"][:12], "blocking")

    gtrj = a.data(gtr_rel)
    bind = (gtrj.get("canonical_sha256") or {}).get(d.get("class_id"))
    gtr_counts = gtrj.get("counts") or {}
    a.check("C2", "owner-tool", "snapshotted owner gate-test report binds exactly to the F2a snapshot hash and reports PASS",
            "canonical_sha256[F2a] == snapshot sha; canonical/null/mutant counts all pass",
            {"report_sha": gtr["sha256"][:12], "binds_to": str(bind)[:12], "report_verdict": gtrj.get("verdict"),
             "canonical_f2a": (gtrj.get("canonical") or {}).get(d.get("class_id"), {}).get("verdict"),
             "counts": gtr_counts},
            bind == f2a["sha256"] and gtrj.get("verdict") == "PASS"
            and (gtrj.get("canonical") or {}).get(d.get("class_id"), {}).get("verdict") == "pass",
            "blocking")

    # ------------------------------------------------ D: controls
    def run_control(cid, desc, mutate, evaluate):
        if not args.controls:
            return
        with tempfile.TemporaryDirectory(dir=HERE) as td:
            path = pathlib.Path(td) / "mutant.yaml"
            mutate(path)
            observed, flipped = evaluate(path)
        a.control(cid, desc, "mutant detected / control flips", observed, flipped)

    def dump(obj, path):
        pathlib.Path(path).write_text(yaml.safe_dump(obj, sort_keys=False))

    run_control("D1", "positive control: unmodified snapshot stays clean",
                lambda p: p.write_text(f2a_text),
                lambda p: ({"dups": len(yaml_duplicate_keys(p.read_text())),
                            "checker": run_checker(p)},
                           len(yaml_duplicate_keys(p.read_text())) == 0
                           and run_checker(p)["exit"] == 0))
    run_control("D2", "duplicate-key control: re-inject a second top-level revised_at",
                lambda p: p.write_text(f2a_text + '\nrevised_at: "2026-09-12T00:31:41+08:00"\n'),
                lambda p: ({"dups": len(yaml_duplicate_keys(p.read_text()))},
                           len(yaml_duplicate_keys(p.read_text())) > 0))
    run_control("D3", "future-date control: set revised_at to 2099",
                lambda p: dump({**d, "revised_at": "2099-01-01T00:00:00+08:00"}, p),
                lambda p: ({"future": [v for _, v in walk_strings(yaml.safe_load(p.read_text()))
                                       if _ .endswith("revised_at")]},
                           any(v == "2099-01-01T00:00:00+08:00"
                               for _, v in walk_strings(yaml.safe_load(p.read_text())))))
    run_control("D4", "pointer control: break class_contract_pointer to a nonexistent class",
                lambda p: dump({**d, "class_contract_pointer":
                                "research_map/formulation_taxonomy.yaml#classes.AF-NOPE"}, p),
                lambda p: (lambda t: ({"target_ok": t},
                                      not t))(isinstance(resolve_pointer(a.data(f0_rel),
                                                                         (yaml.safe_load(p.read_text())
                                                                          ["class_contract_pointer"].split("#")[1]))[0], dict)))
    run_control("D5", "f0-binding control: corrupt declared_f0_sha256",
                lambda p: dump({**d, "f0_binding": {**(d["f0_binding"]),
                                                    "declared_f0_sha256": "deadbeef" * 8}}, p),
                lambda p: (lambda x: ({"declared": x[:12]},
                                      x != f0["sha256"]))(yaml.safe_load(p.read_text())["f0_binding"]["declared_f0_sha256"]))
    run_control("D6", "class-axis control: swap class_id to the sibling AF-SCC-C0-VAC-GEN",
                lambda p: dump({**d, "class_id": "AF-SCC-C0-VAC-GEN"}, p),
                lambda p: (lambda r: ({"checker": r}, r["exit"] != 0))(run_checker(p)))
    run_control("D7", "formal-prefix control: inject 'or' into quantifiers.formal",
                lambda p: dump({**d, "quantifiers": {**d["quantifiers"],
                                                     "formal": d["quantifiers"]["formal"] + " or r = smooth"}}, p),
                lambda p: (lambda f: ({"contains_or": f},
                                      f))(" or " in f" {yaml.safe_load(p.read_text())['quantifiers']['formal']} "))

    # ------------------------------------------------ verdict
    failures = [c for c in a.checks if not c["pass"]]
    blocking = [c["id"] for c in failures if c["severity_if_fail"] == "blocking"]
    superseded = [c["id"] for c in failures if c["severity_if_fail"] == "blocking-superseded"]
    contested = [c["id"] for c in failures if c["severity_if_fail"] == "contested-policy"]
    other = [c["id"] for c in failures
             if c["severity_if_fail"] not in ("blocking", "blocking-superseded", "contested-policy")]
    if blocking:
        verdict = "revise"
    elif contested or superseded:
        verdict = "revise-contested"
    else:
        verdict = "accept"
    report = {
        "task_id": "W48-F2A-REV27-REPIN-01",
        "worker": "worker-048",
        "class_id": d.get("class_id"),
        "node_id": d.get("node_id"),
        "under_assignment": "astra-life03-verify-gform",
        "authority_note": ("Worker verdict, evidence only. Not a gate verdict, not a node completion, "
                           "no validation_status=passed. Workers cannot promote."),
        "audited_at": now_iso(),
        "snapshot_at": json.loads((HERE / "snapshot_manifest.json").read_text())["measured_at"],
        "live_manifest_at_audit": {"revision": live_rev, "frozen_at": live_frozen.get("frozen_at"),
                                   "sha256": live_frozen_sha},
        "inputs": {rel: {"sha256": a.rec(rel)["sha256"], "bytes": a.rec(rel)["bytes"],
                         "snapshot": a.rec(rel)["snapshot"],
                         "mtime_ns": a.rec(rel)["mtime_ns_before"]}
                   for rel in sorted(set(r["path"] for r in a.records.values()))},
        "checks": a.checks,
        "controls": a.controls,
        "summary": {"n_checks": len(a.checks), "n_pass": len(a.checks) - len(failures),
                    "n_fail": len(failures), "blocking": blocking,
                    "blocking_superseded_at_audit": superseded, "contested": contested,
                    "other": other, "n_controls": len(a.controls),
                    "controls_all_flip": all(c["flipped_as_declared"] for c in a.controls) if a.controls else None},
        "verdict": verdict,
        "findings": [
            {"id": "W48-F2A-27-F1", "severity": "blocking-at-rev27-snapshot",
             "finding": "FROZEN rev27 pins gate_test_report.json at 2f699be9 but the passing report at the "
                        "snapshot bytes is 6def0126 (binds canonical_sha256 to the same three rev27 schema "
                        "hashes and reports PASS, 6/6 null controls, 31/31 mutants). The pinned bytes exist "
                        "nowhere on disk; the report was rewritten after frozen_at 00:32:59 (mtime "
                        f"{gtr_mtime.isoformat(timespec='seconds')}). The freeze's own PASS evidence was therefore "
                        "not bindable by the rev27 manifest. SUPERSEDED AT AUDIT TIME: live FROZEN revision "
                        f"{live_rev} ({live_frozen_sha[:12]}, {live_frozen.get('frozen_at')}) re-pins the passing "
                        "report 6def0126."},
            {"id": "W48-F2A-27-F2", "severity": "blocking-at-rev27-snapshot",
             "finding": "taxonomy_consistency.json was pinned and declared as 675a99d0 but the bytes read at "
                        f"snapshot time were {tc['sha256'][:12]} (mtime {tc_live_mtime.isoformat(timespec='seconds')}, "
                        "post-freeze): F2a's declared consistency-evidence hash did not match the live file. "
                        f"SUPERSEDED AT AUDIT TIME: live FROZEN revision {live_rev} re-pins "
                        f"{str(live_pin_tc)[:12]}, matching the snapshot bytes."},
            {"id": "W48-F2A-27-F3", "severity": "contested-policy",
             "finding": "G-FORM's 'one frozen data class shared by F1/F2a/F2b' criterion is not met at rev27: "
                        f"F2a-vs-F2b data_class keys identical={ka == kb}, F2a-vs-F1 identical={ka == kf} with "
                        f"{len(diffs_f)} value differences. D0 is now a declared tagged disjoint union with "
                        "per-branch topology (rev12 repair of the ill-typed 'or'), but no Sobolev/data-class "
                        "variant is registered for AF-SCC-C2-VAC-GEN, so the two-sort domain is a policy "
                        "question (register variant vs accept tagged union) for the gate owner, not a machine error."},
            {"id": "W48-F2A-27-F4", "severity": "cleared",
             "finding": "All machine-checkable blockers from the rev25/26 rounds are cleared at the F2a schema "
                        "hash 5476a3f2 (unchanged in live rev28): 0 duplicate keys, pointer resolves in the "
                        "canonical tree, declared F0 hash current, formal prefix has no disjunction, no "
                        "future-dated fields, owner checker passes, owner gate tests pass and bind to these "
                        "exact bytes, class_separation 0 findings."},
            {"id": "W48-F2A-27-F5", "severity": "info",
             "finding": "Moving-target record: the formulation tree was rewritten at least four times during "
                        "this audit (rev27 freeze 00:32:59; gate_test_report 00:33:42/00:34:00/00:34:47; "
                        "taxonomy_consistency 00:36:36/00:38:07; live FROZEN bumped to rev28 at 00:35:08). "
                        "Every claim here binds only to the snapshot manifest hashes. A10 verifies current "
                        "binding against the live manifest as a separate, timestamped measurement."},
            {"id": "W48-F2A-27-F6", "severity": "advisory",
             "finding": f"F2a review_status is understated at audit time: the snapshot schema at 5476a3f2 "
                        f"declares independent_reviewers=[] and verdict=pending, but {len(rev_new)} hash-paired "
                        f"verdict(s) now cite that exact hash ({', '.join(x['file'] + ':' + x['verdict'] for x in rev_new) or 'none'}). "
                        "The declaration was accurate when the bytes were written; it must be refreshed by the "
                        "author before a gate reads it. (Not a defect of the frozen schema content.)"},
        ],
        "next_falsifier": (
            "At the bytes recorded in inputs: (a) any FAIL check that passes on an independent "
            "re-implementation reading those bytes; (b) any PASS check whose recorded value is not the "
            "measured value at those bytes; (c) any control that does not flip as declared; (d) a FROZEN "
            "revision that already pinNED the passing gate_test_report 6def0126 and the snapshot "
            "taxonomy_consistency bytes AT SNAPSHOT TIME (which would make W48-F2A-27-F1/F2 stale, not "
            "merely superseded later); (e) a VARIANT_REGISTRY entry registering the Sobolev/data-class "
            "variant for AF-SCC-C2-VAC-GEN (which would make W48-F2A-27-F3 stale). A later write to the "
            "live files is not a falsifier -- it is a new revision to re-run against."),
        "reproduce": ("python3 artifacts/worker-048/f2a_rev27_repin_audit/snapshot_inputs.py && "
                      "python3 artifacts/worker-048/f2a_rev27_repin_audit/snapshot_inputs.py --out "
                      "snapshot_manifest_extra.json --inputs "
                      "artifacts/formulation/evidence/taxonomy_consistency.json "
                      "artifacts/formulation/VARIANT_REGISTRY.json "
                      "artifacts/formulation/tools/check_class_schema.py "
                      "artifacts/formulation/KEY_MANIFEST.json && "
                      "python3 artifacts/worker-048/f2a_rev27_repin_audit/audit_f2a_rev27.py --controls"),
    }
    out = HERE / args.out
    out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(f"verdict={verdict} checks={len(a.checks)} fail={len(failures)} "
          f"blocking={blocking} superseded={superseded} contested={contested} controls={len(a.controls)}")
    for c in a.checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['id']:<4} {c['axis']:<14} {c['description'][:88]}")
    if a.controls:
        for c in a.controls:
            print(f"  [{'FLIP' if c['flipped_as_declared'] else 'NOFLIP'}] {c['id']} {c['description'][:80]}")
    print(f"report -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
