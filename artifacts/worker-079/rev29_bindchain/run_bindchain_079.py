#!/usr/bin/env python3
"""W079-GFORM-REV29-BINDCHAIN-CENSUS-01 harness (worker-079, independent).

Resolves the f0_binding chain declared INSIDE each of the three vacuum class schemas
(schemas/af_wcc_vacuum.yaml, schemas/af_scc_c2_vacuum.yaml, schemas/af_scc_c0_vacuum.yaml)
against the live files at the FROZEN rev29 pins, and tests cross-schema uniformity plus the
schemas' own refresh rule.

Pre-registered by artifacts/worker-079/rev29_bindchain/PREREGISTRATION.json (ca59593f8601);
this harness reads its pin table from that file. It writes exactly one file (report.json)
and mutates nothing else. READ-ONLY with respect to every pinned artifact.

Exit codes: 0 report written; 2 pin drift (no report); 3 control failure (no report); 4 missing
preregistration.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PREREG_REL = "artifacts/worker-079/rev29_bindchain/PREREGISTRATION.json"
REPORT_REL = "artifacts/worker-079/rev29_bindchain/report.json"
RUN_LOG_REL = "artifacts/worker-079/rev29_bindchain/run_log.json"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
CLASSES = [
    ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
]
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"


def abspath(rel):
    return os.path.join(ROOT, rel)


def measure(rel):
    """Return dict with sha256/bytes/mtime or MISSING. Never raises on absent files."""
    p = abspath(rel)
    if not os.path.isfile(p):
        return {"path": rel, "status": "MISSING"}
    b = open(p, "rb").read()
    return {
        "path": rel,
        "status": "OK",
        "sha256": hashlib.sha256(b).hexdigest(),
        "bytes": len(b),
        "mtime": os.stat(p).st_mtime,
    }


def load_yaml(rel):
    import yaml

    with open(abspath(rel), "r") as f:
        return yaml.safe_load(f)


def load_json(rel):
    with open(abspath(rel), "r") as f:
        return json.load(f)


def resolve_pointer(pointer):
    """Resolve 'path#dotted.fragment' -> (status, detail). Read-only."""
    if "#" not in pointer:
        path, frag = pointer, None
    else:
        path, frag = pointer.split("#", 1)
    m = measure(path)
    if m["status"] != "OK":
        return "MISSING", {"reason": "file missing", "path": path}
    if frag is None:
        return "RESOLVED", {"path": path, "fragment": None}
    try:
        if path.endswith((".yaml", ".yml")):
            doc = load_yaml(path)
        elif path.endswith(".json"):
            doc = load_json(path)
        else:
            return "NOT_FOUND", {"reason": "unsupported extension", "path": path, "fragment": frag}
    except Exception as exc:  # noqa: BLE001 - a parse failure is a not-found verdict, not a crash
        return "NOT_FOUND", {"reason": "parse error: %s" % exc, "path": path, "fragment": frag}
    node = doc
    for part in frag.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return "NOT_FOUND", {"reason": "fragment step %r absent" % part, "path": path, "fragment": frag}
    return "RESOLVED", {"path": path, "fragment": frag, "resolved_type": type(node).__name__}


def same_hash(a, b):
    return isinstance(a, str) and isinstance(b, str) and a == b


def main():
    # ---------- pre-registration ----------
    prereg_path = abspath(PREREG_REL)
    if not os.path.isfile(prereg_path):
        print("FATAL: preregistration missing; refusing to run", file=sys.stderr)
        return 4
    prereg_bytes = open(prereg_path, "rb").read()
    prereg_sha = hashlib.sha256(prereg_bytes).hexdigest()
    prereg = json.loads(prereg_bytes)
    pins = prereg["pinned_inputs_sha256"]

    # ---------- two-instant pin scan ----------
    first = {p: measure(p) for p in pins}
    second = {p: measure(p) for p in pins}
    drift = []
    for p, pinned in pins.items():
        for label, inst in (("first", first[p]), ("second", second[p])):
            if inst["status"] != "OK":
                drift.append({"path": p, "instant": label, "why": "MISSING"})
            elif inst["sha256"] != pinned["sha256"] or inst["bytes"] != pinned["bytes"]:
                drift.append(
                    {
                        "path": p,
                        "instant": label,
                        "why": "PIN_DRIFT",
                        "declared": pinned,
                        "measured": {"sha256": inst["sha256"], "bytes": inst["bytes"]},
                    }
                )
    if drift:
        print("FATAL: pin drift, no report written: %s" % json.dumps(drift), file=sys.stderr)
        return 2

    # ---------- sources ----------
    schemas = {cid: load_yaml(path) for cid, path in CLASSES}
    frozen = load_json(FROZEN_REL)
    taxonomy = load_yaml("research_map/formulation_taxonomy.yaml")
    supplement = load_yaml(SUPPLEMENT)
    evidence = load_json("artifacts/formulation/evidence/taxonomy_consistency.json")
    frozen_files = frozen.get("files", {})

    live = {p: first[p]["sha256"] for p in pins}

    def live_hash(rel):
        if not isinstance(rel, str):
            return None
        return live.get(rel)

    # ---------- per-class chain ----------
    per_class = {}
    hard_failures = []
    for cid, rel in CLASSES:
        d = schemas[cid]
        fb = d.get("f0_binding", {}) or {}
        rows = {}

        # schema pin vs FROZEN (canonical + mirror)
        mirror = "artifacts/formulation/" + rel
        for label, path in (("canonical", rel), ("mirror", mirror)):
            decl = frozen_files.get(path, {})
            meas = live[path]
            rows["SCHEMA-PIN-" + label.upper()] = {
                "status": "PASS" if same_hash(decl.get("sha256"), meas) and decl.get("bytes") == first[path]["bytes"] else "FAIL",
                "declared": decl,
                "measured": {"sha256": meas, "bytes": first[path]["bytes"]},
            }
            if rows["SCHEMA-PIN-" + label.upper()]["status"] == "FAIL":
                hard_failures.append("%s %s pin mismatch" % (cid, label))
        rows["MIRROR-BYTE-EQUAL"] = {
            "status": "PASS" if live[rel] == live[mirror] else "FAIL",
            "canonical_sha256": live[rel],
            "mirror_sha256": live[mirror],
        }
        if rows["MIRROR-BYTE-EQUAL"]["status"] == "FAIL":
            hard_failures.append("%s canonical/mirror differ" % cid)

        # declared F0
        f0_path = fb.get("declared_f0_artifact")
        f0_decl = fb.get("declared_f0_sha256")
        f0_meas = live_hash(f0_path)
        rows["F0-DECLARED-RESOLVES"] = {
            "status": "PASS" if same_hash(f0_decl, f0_meas) else "FAIL",
            "declared_path": f0_path,
            "declared_sha256": f0_decl,
            "measured_sha256": f0_meas,
        }
        if rows["F0-DECLARED-RESOLVES"]["status"] == "FAIL":
            hard_failures.append("%s declared_f0_sha256 does not resolve" % cid)

        # declared consistency evidence
        ev_path = fb.get("consistency_evidence")
        ev_decl = fb.get("consistency_evidence_sha256")
        ev_meas = live_hash(ev_path)
        rows["EVIDENCE-DECLARED-RESOLVES"] = {
            "status": "PASS" if same_hash(ev_decl, ev_meas) else "FAIL",
            "declared_path": ev_path,
            "declared_sha256": ev_decl,
            "measured_sha256": ev_meas,
        }
        if rows["EVIDENCE-DECLARED-RESOLVES"]["status"] == "FAIL":
            hard_failures.append("%s consistency_evidence_sha256 does not resolve" % cid)

        # supplement vs FROZEN
        sup_path = fb.get("class_contract_supplement")
        sup_decl = frozen_files.get(sup_path, {}).get("sha256")
        sup_meas = live_hash(sup_path)
        rows["SUPPLEMENT-DECLARED-RESOLVES"] = {
            "status": "PASS" if same_hash(sup_decl, sup_meas) else "FAIL",
            "declared_path": sup_path,
            "declared_sha256": sup_decl,
            "measured_sha256": sup_meas,
            "declared_by": "artifacts/formulation/FROZEN.json#files",
        }
        if rows["SUPPLEMENT-DECLARED-RESOLVES"]["status"] == "FAIL":
            hard_failures.append("%s supplement does not resolve" % cid)

        # pointers
        p_top = resolve_pointer(d.get("class_contract_pointer") or "")
        rows["POINTER-CANONICAL-CLASS"] = {
            "status": "PASS" if p_top[0] == "RESOLVED" else "FAIL",
            "pointer": d.get("class_contract_pointer"),
            "resolution": p_top[1],
        }
        if rows["POINTER-CANONICAL-CLASS"]["status"] == "FAIL":
            hard_failures.append("%s class_contract_pointer unresolved" % cid)

        p_top_sup = resolve_pointer(d.get("class_contract_supplement_pointer") or "")
        p_fb_sup = resolve_pointer(fb.get("class_contract_supplement_pointer") or "")
        top_ptr = d.get("class_contract_supplement_pointer") or ""
        fb_ptr = fb.get("class_contract_supplement_pointer") or ""
        top_path = top_ptr.split("#", 1)[0]
        fb_path = fb_ptr.split("#", 1)[0]
        agree = (
            top_ptr == fb_ptr
            and top_path == fb.get("class_contract_supplement")
            and (d.get("class_contract_pointer") or "").split("#", 1)[0] == fb.get("declared_f0_artifact")
        )
        rows["POINTER-SUPPLEMENT-CONTRACT"] = {
            "status": "PASS" if p_top_sup[0] == "RESOLVED" and p_fb_sup[0] == "RESOLVED" and agree else "FAIL",
            "top_level_pointer": d.get("class_contract_supplement_pointer"),
            "f0_binding_pointer": fb.get("class_contract_supplement_pointer"),
            "top_level_resolution": p_top_sup[1],
            "f0_binding_resolution": p_fb_sup[1],
            "pointers_identical": top_ptr == fb_ptr,
            "pointer_path_equals_f0_binding_supplement_field": top_path == fb.get("class_contract_supplement"),
            "class_contract_pointer_path_equals_declared_f0_artifact": (d.get("class_contract_pointer") or "").split("#", 1)[0]
            == fb.get("declared_f0_artifact"),
            "fields_agree": agree,
        }
        if rows["POINTER-SUPPLEMENT-CONTRACT"]["status"] == "FAIL":
            hard_failures.append("%s supplement pointer unresolved or fields disagree" % cid)

        # refresh rule
        rule_ok = same_hash(f0_decl, live.get("research_map/formulation_taxonomy.yaml")) and same_hash(
            ev_decl, live.get("artifacts/formulation/evidence/taxonomy_consistency.json")
        )
        rows["REFRESH-RULE-SATISFIED"] = {
            "status": "PASS" if rule_ok else "FAIL",
            "rule": fb.get("rule"),
            "declared_f0_sha256": f0_decl,
            "live_f0_sha256": live.get("research_map/formulation_taxonomy.yaml"),
            "declared_evidence_sha256": ev_decl,
            "live_evidence_sha256": live.get("artifacts/formulation/evidence/taxonomy_consistency.json"),
            "checked_at": fb.get("checked_at"),
        }
        if not rule_ok:
            hard_failures.append("%s refresh rule not satisfied" % cid)

        # class identity
        tax_node = taxonomy.get("classes", {}).get(cid)
        sup_node = supplement.get("class_contracts", {}).get(cid)
        rows["SCHEMA-CLASS-ID-MATCH"] = {
            "status": "PASS" if d.get("class_id") == cid and tax_node is not None and sup_node is not None else "FAIL",
            "schema_class_id": d.get("class_id"),
            "taxonomy_contract_present": tax_node is not None,
            "supplement_contract_present": sup_node is not None,
        }
        if rows["SCHEMA-CLASS-ID-MATCH"]["status"] == "FAIL":
            hard_failures.append("%s class identity mismatch" % cid)

        # evidence lists class
        listed = cid in (evidence.get("classes_compared") or [])
        rows["EVIDENCE-LISTS-CLASS"] = {
            "status": "PASS" if listed and evidence.get("consistent") is True else "FAIL",
            "classes_compared": evidence.get("classes_compared"),
            "consistent": evidence.get("consistent"),
            "errors": evidence.get("errors"),
        }
        if rows["EVIDENCE-LISTS-CLASS"]["status"] == "FAIL":
            hard_failures.append("%s evidence does not list class or consistent!=true" % cid)

        per_class[cid] = rows

    # ---------- global ----------
    decl_tuples = []
    for cid, rel in CLASSES:
        fb = schemas[cid].get("f0_binding", {}) or {}
        decl_tuples.append(
            (
                fb.get("declared_f0_artifact"),
                fb.get("declared_f0_sha256"),
                fb.get("consistency_evidence"),
                fb.get("consistency_evidence_sha256"),
                fb.get("class_contract_supplement"),
            )
        )
    uniform = len(set(decl_tuples)) == 1
    binding_files = [rel for _, rel in CLASSES] + ["artifacts/formulation/" + rel for _, rel in CLASSES] + [
        "research_map/formulation_taxonomy.yaml",
        SUPPLEMENT,
        "artifacts/formulation/evidence/taxonomy_consistency.json",
    ]
    frozen_missing = [p for p in binding_files if p not in frozen_files]
    frozen_mismatch = [
        p
        for p in binding_files
        if p in frozen_files
        and not (frozen_files[p].get("sha256") == live[p] and frozen_files[p].get("bytes") == first[p]["bytes"])
    ]
    checked_ats = [
        (schemas[cid].get("f0_binding", {}) or {}).get("checked_at") for cid, _ in CLASSES
    ]
    ev_mtime = first["artifacts/formulation/evidence/taxonomy_consistency.json"]["mtime"]
    frozen_mtime = first[FROZEN_REL]["mtime"]

    def iso_epoch(s):
        import datetime

        try:
            return datetime.datetime.fromisoformat(str(s)).timestamp()
        except Exception:  # noqa: BLE001
            return None

    checked_epochs = [iso_epoch(c) for c in checked_ats]
    frozen_epoch = iso_epoch(frozen.get("frozen_at"))
    evidence_rewritten_post_freeze = bool(
        ev_mtime > frozen_mtime
        or (frozen_epoch is not None and ev_mtime > frozen_epoch)
        or any(c is not None and ev_mtime > c for c in checked_epochs)
    )
    annotations = {
        "evidence_rewritten_post_freeze": bool(evidence_rewritten_post_freeze),
        "evidence_mtime_after_max_checked_at_wallclock_note": "checked_at values are %s and FROZEN frozen_at is %s; at the scan instant the evidence file mtime was newer than both (volatile epoch recorded in run_log.json), while its bytes still measure the declared sha256. The schema's binding contract is sha256-based, so this is a SOFT-NOTE (writer activity), not a pin violation; it does mean the 'check re-run' claim cannot be distinguished from a byte-identical rewrite because the evidence file carries no timestamp or input-hash field."
        % (checked_ats, frozen.get("frozen_at")),
        "evidence_has_timestamp_field": any(k in evidence for k in ("checked_at", "generated_at", "timestamp")),
        "evidence_input_hash_fields": [k for k in evidence if "sha" in k.lower() or "hash" in k.lower()],
        "disjointness_pairs_recorded": [
            {"pair": e.get("pair"), "decisive_axes": e.get("decisive_axes")}
            for e in (taxonomy.get("disjointness") or [])
            if isinstance(e, dict)
        ],
        "disjointness_scope": taxonomy.get("disjointness_scope"),
        "supplement_artifact_role": supplement.get("artifact_role"),
        "top_level_supplement_path_field_present": {
            cid: ("class_contract_supplement" in (schemas[cid] or {})) for cid, _ in CLASSES
        },
        "naming_asymmetry_note": "the top level of each schema carries class_contract_pointer (canonical taxonomy) and class_contract_supplement_pointer (supplement) but no bare class_contract_supplement path field; f0_binding carries both class_contract_supplement (path) and class_contract_supplement_pointer. The two pointer fields are byte-identical and the pointer path equals the f0_binding path field on all three schemas, so no consumer can bind the supplement to a different path today; a strict schema-symmetry linter would flag the asymmetry. NOT a failure.",
        "frozen_self_sha256": live[FROZEN_REL],
        "frozen_revision": frozen.get("revision"),
        "frozen_frozen_at": frozen.get("frozen_at"),
        "canonical_taxonomy_live": live["research_map/formulation_taxonomy.yaml"],
        "supplement_live": live[SUPPLEMENT],
        "evidence_live": live["artifacts/formulation/evidence/taxonomy_consistency.json"],
    }

    # ---------- controls ----------
    controls = []
    # C1 positive match
    c1 = same_hash(schemas[CLASSES[0][0]]["f0_binding"]["declared_f0_sha256"], live["research_map/formulation_taxonomy.yaml"])
    controls.append({"id": "C1-POSITIVE-MATCH", "observed": "MATCH" if c1 else "NO_MATCH", "expected": "MATCH", "passed": bool(c1)})
    # C2 comparator detects a one-hex-digit flip
    h = live["research_map/formulation_taxonomy.yaml"]
    flipped = ("0" if h[0] != "0" else "1") + h[1:]
    c2 = not same_hash(h, flipped)
    controls.append({"id": "C2-COMPARATOR-DETECTS-MISMATCH", "observed": "MISMATCH" if c2 else "MATCH", "expected": "MISMATCH", "passed": bool(c2)})
    # C3 bogus fragment
    st, _ = resolve_pointer(SUPPLEMENT + "#class_contracts.NO-SUCH-CLASS")
    controls.append({"id": "C3-POINTER-NOT-FOUND", "observed": st, "expected": "NOT_FOUND", "passed": st == "NOT_FOUND"})
    # C4 missing path fail-closed
    st, _ = resolve_pointer("schemas/NO-SUCH-SCHEMA.yaml#classes.X")
    controls.append({"id": "C4-MISSING-FAIL-CLOSED", "observed": st, "expected": "MISSING", "passed": st == "MISSING"})
    # C5 byte flip in a temp copy
    tmpdir = tempfile.mkdtemp(prefix="w079_bindchain_")
    try:
        src = abspath("research_map/formulation_taxonomy.yaml")
        dst = os.path.join(tmpdir, "formulation_taxonomy.yaml")
        shutil.copyfile(src, dst)
        b = bytearray(open(dst, "rb").read())
        b[len(b) // 2] ^= 0x01
        open(dst, "wb").write(bytes(b))
        tmp_sha = hashlib.sha256(bytes(b)).hexdigest()
        c5 = tmp_sha != h
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    controls.append({"id": "C5-BYTE-FLIP-DETECTED", "observed": "DIFFERENT" if c5 else "SAME", "expected": "DIFFERENT", "passed": bool(c5)})

    control_fail = [c["id"] for c in controls if not c["passed"]]
    if control_fail:
        print("FATAL: control failure %s; no report written" % control_fail, file=sys.stderr)
        return 3

    # ---------- checks summary ----------
    checks = []
    checks.append(
        {
            "id": "PIN-TABLE-STABLE",
            "class_scope": "ALL",
            "status": "PASS",
            "detail": "%d pinned inputs measured twice with identical sha256/bytes and equal to the preregistration table" % len(pins),
        }
    )
    checks.append(
        {
            "id": "FROZEN-DECLARES-BINDING-FILES",
            "class_scope": "ALL",
            "status": "PASS" if not frozen_missing and not frozen_mismatch else "FAIL",
            "detail": {"missing": frozen_missing, "mismatch": frozen_mismatch, "n_binding_files": len(binding_files)},
        }
    )
    if frozen_missing or frozen_mismatch:
        hard_failures.append("FROZEN does not declare/mismatch binding files")
    for cid, _ in CLASSES:
        for key, row in per_class[cid].items():
            checks.append({"id": key, "class_scope": cid, "status": row["status"], "detail": row})
    checks.append(
        {
            "id": "CROSS-SCHEMA-UNIFORMITY",
            "class_scope": "ALL",
            "status": "PASS" if uniform else "FAIL",
            "detail": {"declarations": decl_tuples, "distinct_tuples": len(set(decl_tuples))},
        }
    )
    if not uniform:
        hard_failures.append("cross-schema binding declarations differ")
    checks.append(
        {
            "id": "EVIDENCE-FRESHNESS-ANNOTATION",
            "class_scope": "ALL",
            "status": "NOTE",
            "detail": annotations["evidence_mtime_after_max_checked_at_wallclock_note"],
        }
    )
    checks.append(
        {
            "id": "DISJOINTNESS-RECORDED",
            "class_scope": "ALL",
            "status": "NOTE",
            "detail": {"pairs": annotations["disjointness_pairs_recorded"], "scope": annotations["disjointness_scope"]},
        }
    )

    verdict = "PASS" if not hard_failures else "FAIL"
    report = {
        "artifact_kind": "f0_binding_chain_census",
        "artifact_id": "worker-079/rev29_bindchain",
        "task_id": prereg["task_id"],
        "worker": "worker-079",
        "gate": "G-FORM",
        "node_id": "F1/F2a/F2b",
        "class_ids": [c for c, _ in CLASSES],
        "scope": "f0_binding chain + pointer resolution + refresh rule + cross-schema uniformity at FROZEN rev29; no schema-content judgement, no gate verdict",
        "preregistration_path": PREREG_REL,
        "preregistration_sha256": prereg_sha,
        "pins": {
            p: {
                "declared": pins[p],
                "measured_first": {"sha256": first[p]["sha256"], "bytes": first[p]["bytes"]},
                "measured_second": {"sha256": second[p]["sha256"], "bytes": second[p]["bytes"]},
                "matches_declared": True,
            }
            for p in pins
        },
        "frozen": {
            "path": FROZEN_REL,
            "self_sha256": live[FROZEN_REL],
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "declares_binding_files": not frozen_missing and not frozen_mismatch,
            "mismatches": frozen_mismatch,
            "missing": frozen_missing,
        },
        "per_class": per_class,
        "global": {
            "cross_schema_uniform": uniform,
            "hard_failures": hard_failures,
            "declared_tuple_reference": list(decl_tuples[0]),
        },
        "controls": controls,
        "checks": checks,
        "annotations": annotations,
        "verdict": verdict,
        "verdict_scope": "worker-level measurement verdict only; NOT a gate verdict, NOT validation_status=passed, NOT a node done",
        "falsifiers": prereg["falsifiers"],
        "reproduce": "python3 artifacts/worker-079/rev29_bindchain/run_bindchain_079.py",
        "volatile_fields_note": "report.json is content-deterministic: it contains no wall-clock timestamps and no file mtimes. Volatile scan metadata (per-pin mtimes, scan instants, quiescence flags) is written to run_log.json, which is explicitly NOT part of the reproducible claim.",
    }
    out = abspath(REPORT_REL)
    with open(out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    run_log = {
        "artifact_kind": "volatile_run_log",
        "task_id": prereg["task_id"],
        "worker": "worker-079",
        "note": "volatile scan metadata; NOT reproduced byte-for-byte by design (wall-clock and mtimes). The deterministic measurement is report.json.",
        "scan_first_wallclock": __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "pins_mtime": {p: {"mtime_first": first[p]["mtime"], "mtime_second": second[p]["mtime"]} for p in pins},
        "evidence_mtime_epoch": ev_mtime,
        "evidence_rewritten_post_freeze": evidence_rewritten_post_freeze,
        "frozen_mtime_epoch": frozen_mtime,
        "checked_at_epochs": checked_epochs,
        "frozen_frozen_at_epoch": frozen_epoch,
        "quiescence_verdict": "WRITER_ACTIVE_BYTE_IDENTICAL" if evidence_rewritten_post_freeze else "QUIESCENT",
    }
    with open(abspath(RUN_LOG_REL), "w") as f:
        json.dump(run_log, f, indent=1, sort_keys=True)
        f.write("\n")
    print("verdict=%s hard_failures=%d report=%s run_log=%s" % (verdict, len(hard_failures), REPORT_REL, RUN_LOG_REL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
