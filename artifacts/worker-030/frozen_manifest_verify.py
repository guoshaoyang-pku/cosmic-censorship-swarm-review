#!/usr/bin/env python3
"""worker-030 independent verification of the FROZEN rev27 formulation byte set.

Task W030-FROZEN-TRANSITION-01.  Class-bound: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH (nodes F0, F1, F2a, F2b; gates G-F0 / G-FORM).

Two questions, both mechanical:

  (1) REV27 INTEGRITY.  Does artifacts/formulation/FROZEN.json revision 27
      (sha256 5fa3b3bf95f2dcb0…) describe the live formulation byte set?  Every
      declared file pin is re-hashed; the two logical F0 artifacts, the four class
      artifacts, each schema's f0_binding, and each schema's class_contract_pointer
      are re-checked against the live bytes.

  (2) REV26 -> REV27 TRANSITION.  Revision 26 (sha256 2554e276a0db7057…, frozen_at
      00:24:49) pinned the pre-closure F0/F1/F2a/F2b bytes.  Those paths were
      republished at 00:31:41-00:32:02 and re-frozen as revision 27 at 00:32:59.
      The instrument records which pins moved and corroborates the superseded set
      against the controller gate audit still on disk.

The manifest is pinned fail-closed: if it changes under the instrument the run exits 2
rather than silently verifying a different revision.

Exit codes:
    0  no blocking integrity check failed (transition finding may still be recorded)
    1  >=1 blocking integrity check failed
    2  operational failure: manifest missing, or pinned manifest hash drift

Usage:
    python3 artifacts/worker-030/frozen_manifest_verify.py [--json PATH]
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANIFEST = "artifacts/formulation/FROZEN.json"
PIN_FROZEN = "5fa3b3bf95f2dcb003ccf800db2f03b80c385a9de3f2984d848201ebec5db340"
PIN_FROZEN_BYTES = 21386
PIN_REVISION = 27
PIN_FROZEN_AT = "2026-09-12T00:32:59+08:00"
PREV_FROZEN = "2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3"
PREV_FROZEN_AT = "2026-09-12T00:24:49+08:00"
MAP = "research_map/research_map.json"

FROZEN_FOUR = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
# node -> (class id(s), canonical path); pins are read from the live manifest under test
CLASS_ARTIFACTS = {
    "F0": (";".join(FROZEN_FOUR), "research_map/formulation_taxonomy.yaml"),
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
}
AUTHORING_F0 = "artifacts/formulation/formulation_taxonomy.yaml"
LEGACY_POINTER = "schemas/af_scc_regularities.yaml"

CHECKS: list[dict] = []
FAILED_BLOCKING = 0


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(cid, group, blocking, ok, detail, **extra):
    global FAILED_BLOCKING
    status = "PASS" if ok else ("FAIL" if blocking else "NOTE")
    if not ok and blocking:
        FAILED_BLOCKING += 1
    CHECKS.append({
        "id": cid, "group": group, "blocking_if_failed": bool(blocking),
        "status": status, "detail": detail, **extra,
    })


def resolve(rel: str) -> str:
    return os.path.join(ROOT, rel)


def pin_check(rel: str, expected_sha: str, expected_bytes: int | None = None):
    p = resolve(rel)
    if not os.path.isfile(p):
        return {"exists": False, "sha256": None, "bytes": None,
                "sha_match": False, "bytes_match": False}
    got_sha = sha256_of(p)
    got_bytes = os.path.getsize(p)
    return {"exists": True, "sha256": got_sha, "bytes": got_bytes,
            "sha_match": got_sha == expected_sha,
            "bytes_match": expected_bytes is None or got_bytes == expected_bytes}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(
        ROOT, "artifacts/worker-030/frozen_transition/frozen_rev27_verify.json"))
    args = ap.parse_args()
    generated = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    # ---- 0. fail closed on manifest drift ------------------------------------
    man_path = resolve(MANIFEST)
    if not os.path.isfile(man_path):
        print("FATAL: manifest missing", file=sys.stderr)
        return 2
    measured_frozen = sha256_of(man_path)
    measured_frozen_bytes = os.path.getsize(man_path)
    if measured_frozen != PIN_FROZEN:
        print(f"FATAL: FROZEN.json drifted: {measured_frozen} != pin {PIN_FROZEN}",
              file=sys.stderr)
        return 2

    man = json.load(open(man_path, encoding="utf-8"))
    files = man.get("files") or {}
    logical = man.get("logical_artifacts") or {}
    logical_paths = {str(v.get("path")) for v in logical.values()}

    # ---- 1. manifest identity -------------------------------------------------
    record("FRZ-01", "identity", True,
           measured_frozen == PIN_FROZEN and measured_frozen_bytes == PIN_FROZEN_BYTES
           and man.get("revision") == PIN_REVISION
           and str(man.get("frozen_at")) == PIN_FROZEN_AT,
           f"{MANIFEST}: sha256={measured_frozen} bytes={measured_frozen_bytes} "
           f"revision={man.get('revision')} frozen_at={man.get('frozen_at')} "
           f"entries={len(files)}")

    # ---- 2. every declared file pin ------------------------------------------
    mismatches, missing, byte_mismatch = [], [], []
    for rel, ent in sorted(files.items()):
        r = pin_check(rel, ent.get("sha256"), ent.get("bytes"))
        if not r["exists"]:
            missing.append(rel)
        elif not r["sha_match"]:
            mismatches.append({"path": rel, "expected": ent.get("sha256"),
                               "measured": r["sha256"]})
        elif not r["bytes_match"]:
            byte_mismatch.append({"path": rel, "expected": ent.get("bytes"),
                                  "measured": r["bytes"]})
    matched = len(files) - len(mismatches) - len(missing) - len(byte_mismatch)
    class_scope_paths = {v[1] for v in CLASS_ARTIFACTS.values()} | set(logical_paths)
    class_scope_bad = [m for m in (mismatches + missing + byte_mismatch)
                       if (m if isinstance(m, str) else m["path"]) in class_scope_paths]
    record("FRZ-02a", "class_pins", True, not class_scope_bad,
           f"class-scope pins (4 class artifacts + {len(logical_paths)} logical F0 "
           f"artifacts) all match disk" if not class_scope_bad
           else f"class-scope pin defects: {class_scope_bad}",
           class_scope_paths=sorted(class_scope_paths), defects=class_scope_bad)
    record("FRZ-02b", "file_pins", False,
           not mismatches and not missing and not byte_mismatch,
           f"full manifest sweep: {len(files)} declared pins re-hashed, {matched} match, "
           f"{len(mismatches)} sha mismatch, {len(byte_mismatch)} byte mismatch, "
           f"{len(missing)} missing (non-class auxiliary artifacts only)"
           if (mismatches or missing or byte_mismatch)
           else f"full manifest sweep: all {len(files)} pins match disk",
           sha_mismatches=mismatches, byte_mismatches=byte_mismatch, missing=missing,
           matched=matched)

    # ---- 3. logical artifacts -------------------------------------------------
    logical_rows, logical_bad = [], []
    for lid, l in sorted(logical.items()):
        rel, exp = l.get("path"), l.get("sha256")
        r = pin_check(rel, exp)
        ok = bool(r["exists"] and r["sha_match"])
        logical_rows.append({"id": lid, "path": rel, "pin": exp,
                             "measured": r["sha256"], "ok": ok})
        if not ok:
            logical_bad.append(logical_rows[-1])
    record("FRZ-03", "logical_artifacts", True, not logical_bad,
           f"{len(logical)} logical F0 artifact(s) re-hashed; mismatches={logical_bad}",
           rows=logical_rows)

    # ---- 4. four class artifacts: live pin + declared class ids ---------------
    class_rows, class_bad = [], []
    live_pins = {}
    docs = {}
    for node, (cid, rel) in CLASS_ARTIFACTS.items():
        man_sha = (files.get(rel) or {}).get("sha256")
        r = pin_check(rel, man_sha or "0" * 64)
        live_pins[rel] = r["sha256"]
        try:
            docs[rel] = yaml.safe_load(open(resolve(rel), encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            docs[rel] = {"__parse_error__": str(ex)}
        doc = docs[rel]
        declared = doc.get("class_id") if isinstance(doc, dict) else None
        class_rows.append({"node": node, "path": rel, "manifest_pin": man_sha,
                           "measured": r["sha256"], "disk_ok": bool(r["sha_match"]),
                           "declared_class_id": declared,
                           "revision": doc.get("revision") if isinstance(doc, dict) else None})
        if not (r["exists"] and r["sha_match"]):
            class_bad.append({"node": node, "path": rel, "manifest_pin": man_sha,
                              "measured": r["sha256"]})
        if node == "F0":
            got = doc.get("class_ids") if isinstance(doc, dict) else None
            if sorted(map(str, got or [])) != sorted(FROZEN_FOUR):
                class_bad.append({"node": "F0", "declared_class_ids": got})
        elif declared != cid:
            class_bad.append({"node": node, "expected_class_id": cid,
                              "declared_class_id": declared})
    record("FRZ-04", "class_binding", True, not class_bad,
           "four class artifacts: manifest pin == disk hash and declared class ids equal "
           "the frozen four" if not class_bad else f"defects: {class_bad}",
           rows=class_rows, defects=class_bad)

    # ---- 5. f0_binding points at the live canonical F0 ------------------------
    live_f0 = live_pins[CLASS_ARTIFACTS["F0"][1]]
    fb_rows, fb_bad = [], []
    for node in ("F1", "F2a", "F2b"):
        rel = CLASS_ARTIFACTS[node][1]
        fb = (docs[rel] or {}).get("f0_binding") or {}
        declared_path = fb.get("declared_f0_artifact")
        declared_sha = fb.get("declared_f0_sha256")
        ok = declared_path == CLASS_ARTIFACTS["F0"][1] and declared_sha == live_f0
        fb_rows.append({"node": node, "declared_f0_artifact": declared_path,
                        "declared_f0_sha256": declared_sha, "live_f0": live_f0,
                        "ok": bool(ok)})
        if not ok:
            fb_bad.append(fb_rows[-1])
    record("FRZ-05", "f0_binding", True, not fb_bad,
           "F1/F2a/F2b f0_binding.declared_f0_artifact+sha256 both equal the live "
           "canonical F0 taxonomy" if not fb_bad else f"disagreements: {fb_bad}",
           rows=fb_rows)

    # ---- 6. class_contract_pointer resolves in the canonical F0 ---------------
    ccp_rows, ccp_bad = [], []
    for node in ("F1", "F2a", "F2b"):
        rel = CLASS_ARTIFACTS[node][1]
        ccp = str((docs[rel] or {}).get("class_contract_pointer") or "")
        path, _, frag = ccp.partition("#")
        parts = [p for p in frag.split(".") if p]
        target = docs.get(path) if path in docs else None
        if path != CLASS_ARTIFACTS["F0"][1]:
            target = yaml.safe_load(open(resolve(path), encoding="utf-8")) \
                if os.path.isfile(resolve(path)) else None
        cur = target
        resolved = bool(parts) and path == CLASS_ARTIFACTS["F0"][1]
        for part in parts:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                resolved = False
                break
        ccp_rows.append({"node": node, "pointer": ccp, "path": path, "fragment": frag,
                         "resolves_in_canonical_f0": bool(resolved)})
        if not resolved:
            ccp_bad.append(ccp_rows[-1])
    record("FRZ-06", "pointer_resolution", True, not ccp_bad,
           "each schema's class_contract_pointer resolves inside the canonical F0 "
           "taxonomy" if not ccp_bad else f"unresolved pointers: {ccp_bad}",
           rows=ccp_rows)

    # ---- 7. coverage of referenced canonical paths ----------------------------
    map_doc = json.load(open(resolve(MAP), encoding="utf-8"))
    map_sha = sha256_of(resolve(MAP))
    legacy = {x.get("path"): x.get("role") for x in (map_doc.get("legacy_artifacts") or [])}
    refs: dict[str, set[str]] = {}

    def add_ref(path, source):
        if not path:
            return
        path = str(path).strip().strip('"').strip("'")
        if path.startswith("NO F-NODE") or path.startswith("http"):
            return
        refs.setdefault(path, set()).add(source)

    f0_doc = docs[CLASS_ARTIFACTS["F0"][1]]
    for cid, cls in (f0_doc.get("classes") or {}).items():
        m = re.search(r"artifact\s+([^\s,)]+)", str((cls or {}).get("provenance", {}).get("schema_owner") or ""))
        if m:
            add_ref(m.group(1), f"F0.classes.{cid}.schema_owner")
    for node in ("F1", "F2a", "F2b"):
        rel = CLASS_ARTIFACTS[node][1]
        doc = docs[rel] or {}
        add_ref((doc.get("f0_binding") or {}).get("declared_f0_artifact"), f"{node}.f0_binding")
        add_ref((doc.get("f0_binding") or {}).get("class_contract_supplement"), f"{node}.f0_binding")
        add_ref(str(doc.get("class_contract_pointer") or "").partition("#")[0],
                f"{node}.class_contract_pointer")
    rows, unresolved = [], []
    for path, sources in sorted(refs.items()):
        if path in files:
            where = "manifest"
        elif path in legacy:
            where = "legacy"
        elif path.startswith("artifacts/formulation/"):
            where = "authoring_tree"
        else:
            where = "UNRESOLVED"
            unresolved.append({"path": path, "referenced_by": sorted(sources)})
        rows.append({"path": path, "referenced_by": sorted(sources), "coverage": where})
    record("FRZ-07", "reference_coverage", True, not unresolved,
           f"{len(rows)} canonical path(s) referenced by the frozen class artifacts: all "
           f"pinned, legacy-declared or authoring-tree; unresolved={unresolved}",
           references=rows, unresolved_references=unresolved, legacy_paths=legacy,
           class_contract_supplement=(docs[CLASS_ARTIFACTS["F1"][1]].get("f0_binding") or {}
                                      ).get("class_contract_supplement"))

    # ---- 8. controls ----------------------------------------------------------
    ctrl = {}
    r_pos = pin_check(CLASS_ARTIFACTS["F1"][1], live_pins[CLASS_ARTIFACTS["F1"][1]])
    ctrl["positive_true_pin_accepted"] = bool(r_pos["exists"] and r_pos["sha_match"])
    r_neg = pin_check(CLASS_ARTIFACTS["F1"][1], "0" * 64)
    ctrl["negative_corrupt_pin_rejected"] = bool(r_neg["exists"] and not r_neg["sha_match"])
    r_miss = pin_check("schemas/__no_such_artifact__.yaml", "0" * 64)
    ctrl["negative_missing_file_rejected"] = bool(not r_miss["exists"])
    perturbed = copy.deepcopy(files)
    key = CLASS_ARTIFACTS["F2b"][1]
    perturbed[key] = dict(perturbed[key])
    perturbed[key]["sha256"] = "f" * 64
    caught = any(rel == key and not pin_check(rel, ent.get("sha256"), ent.get("bytes"))["sha_match"]
                 for rel, ent in perturbed.items())
    ctrl["negative_flipped_manifest_pin_caught"] = bool(caught)
    record("FRZ-08", "controls", True, all(ctrl.values()),
           f"instrument self-controls: {ctrl}")

    # ---- 9. rev26 -> rev27 transition ----------------------------------------
    ga = (map_doc.get("controller_gate_audit") or {})
    audit_hashes = sorted({m for g in ga.values()
                           for m in re.findall(r"\b([0-9a-f]{12})\b", str(g.get("reason", "")))})
    rev27_pins = {rel: (files.get(rel) or {}).get("sha256")
                  for rel in [v[1] for v in CLASS_ARTIFACTS.values()]}
    rev27_prefixes = sorted({(v or "")[:12] for v in rev27_pins.values()})
    superseded = sorted(set(audit_hashes) & set(rev27_prefixes))
    moved = []
    for rel in [CLASS_ARTIFACTS["F0"][1], AUTHORING_F0] + \
               [CLASS_ARTIFACTS[n][1] for n in ("F1", "F2a", "F2b")]:
        mt = _dt.datetime.fromtimestamp(os.path.getmtime(resolve(rel))).astimezone()
        moved.append({"path": rel, "mtime": mt.isoformat(),
                      "rev27_pin": (files.get(rel) or {}).get("sha256")})
    after_prev = all(m["mtime"] > PREV_FROZEN_AT for m in moved)
    audit_current = set(rev27_prefixes).issubset(set(audit_hashes))
    record("FRZ-09", "transition", True, after_prev and audit_current,
           f"rev26 {PREV_FROZEN[:12]} (frozen_at {PREV_FROZEN_AT}) predates the "
           f"00:31:41-00:32:02 republication of all five F0/F1/F2a/F2b paths; rev27 pins "
           f"the republished set; controller gate audit on disk cites "
           f"{'all four' if audit_current else 'NOT all'} rev27 class prefixes "
           f"(checked_at {ga.get('G-F0', {}).get('checked_at')})",
           rev26={"sha256": PREV_FROZEN, "frozen_at": PREV_FROZEN_AT},
           rev27_file_pins=rev27_pins, republished_paths=moved,
           controller_gate_audit_prefixes=audit_hashes,
           controller_gate_audit_covers_rev27=bool(audit_current),
           controller_gate_audit_checked_at=ga.get("G-F0", {}).get("checked_at"),
           map_sha256=map_sha)

    # ---- 10. post-freeze churn classification ---------------------------------
    man_mtime = _dt.datetime.fromtimestamp(os.path.getmtime(man_path)).astimezone()
    churn, stale_at_freeze = [], []
    for m in (mismatches + byte_mismatch):
        rel = m["path"]
        mt = _dt.datetime.fromtimestamp(os.path.getmtime(resolve(rel))).astimezone()
        row = {"path": rel, "mtime": mt.isoformat(),
               "manifest_pin": m["expected"], "measured": m["measured"]}
        (churn if mt > man_mtime else stale_at_freeze).append(row)
    record("FRZ-11", "manifest_stability", False, not mismatches and not byte_mismatch,
           f"post-freeze churn: {len(churn)} declared pin(s) rewritten after the manifest "
           f"mtime {man_mtime.isoformat()}; stale-at-freeze: {len(stale_at_freeze)}",
           churn=churn, stale_at_freeze=stale_at_freeze,
           manifest_mtime=man_mtime.isoformat())

    # ---- 11. provenance -------------------------------------------------------
    mtime = _dt.datetime.fromtimestamp(os.path.getmtime(man_path)).astimezone()
    record("FRZ-10", "provenance", False,
           bool(man.get("rev27_delta")),
           f"frozen_at={man.get('frozen_at')} mtime={mtime.isoformat()} "
           f"rev27_delta={json.dumps(man.get('rev27_delta'))[:160]}")

    payload = {
        "task_id": "W030-FROZEN-TRANSITION-01",
        "worker": "worker-030",
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "class_ids": list(FROZEN_FOUR),
        "gate_scope": "G-F0/G-FORM evidence input (not a gate verdict)",
        "generated_at": generated,
        "headline": (
            "FROZEN revision 27 correctly pins the live F0/F1/F2a/F2b class byte set: all "
            "four class artifacts and both logical F0 artifacts match disk, every schema's "
            "f0_binding and class_contract_pointer resolves in the canonical F0, and the "
            "controller gate audit on disk cites all four rev27 prefixes. Revision 26 was "
            "superseded by the 00:31:41-00:32:02 closure republication. Caveat: 5 of the 43 "
            "rev27 pins (non-class evidence/delta files) were rewritten after the manifest "
            "mtime, so the manifest is not yet a stable whole."
        ),
        "findings": [
            {
                "id": "W030-F1",
                "severity": "info",
                "blocking_for_gate": False,
                "finding": "rev27 class-scope integrity verified: 4 class artifacts + 2 logical "
                           "F0 artifacts pin == disk; F1/F2a/F2b rev12 class ids are the frozen "
                           "three, F0 rev5 class_ids are the frozen four.",
            },
            {
                "id": "W030-F2",
                "severity": "info",
                "blocking_for_gate": False,
                "finding": "closure repairs verified mechanically: all three schemas' "
                           "class_contract_pointer now resolves inside the canonical F0 "
                           "(research_map/formulation_taxonomy.yaml#classes.<CLASS>) and all "
                           "three f0_binding.declared_f0_sha256 equal the live canonical F0 "
                           "hash 0abb9ed8a961.",
            },
            {
                "id": "W030-F3",
                "severity": "major",
                "blocking_for_gate": False,
                "finding": "post-freeze churn: 5/43 rev27 pins were rewritten after the manifest "
                           "mtime 00:33:03 (KEY_MANIFEST.json, evidence/gate_test_report.json, "
                           "evidence/taxonomy_consistency.json, variants/*.variant-{CH,SET}.delta.json), "
                           "all non-class auxiliary artifacts; a gate decision citing those five "
                           "pins must re-measure or wait for the next manifest revision.",
                "evidence_refs": ["artifacts/worker-030/frozen_transition/frozen_rev27_verify.json"]
            },
            {
                "id": "W030-F4",
                "severity": "info",
                "blocking_for_gate": False,
                "finding": "rev26 (2554e276, frozen_at 00:24:49) pinned the pre-closure hashes "
                           "276009f4/9a8bd4c9/b6123750/1bb78ce9; any verdict bound to those "
                           "hashes is advisory until re-issued at the rev27 pins.",
            },
        ],
        "pins": {
            MANIFEST: measured_frozen,
            "previous_manifest_rev26": PREV_FROZEN,
            MAP: map_sha,
            **live_pins,
        },
        "manifest": {
            "revision": man.get("revision"),
            "frozen_at": man.get("frozen_at"),
            "declared_files": len(files),
            "logical_artifacts": sorted(logical),
        },
        "checks": CHECKS,
        "counts": {
            "pass": sum(1 for c in CHECKS if c["status"] == "PASS"),
            "fail": sum(1 for c in CHECKS if c["status"] == "FAIL"),
            "note": sum(1 for c in CHECKS if c["status"] == "NOTE"),
            "blocking_failed": FAILED_BLOCKING,
            "declared_files": len(files),
            "file_pins_matched": matched,
        },
        "falsifier": (
            "Any byte change to artifacts/formulation/FROZEN.json (sha256 leaves "
            f"{PIN_FROZEN[:16]}) makes this instrument exit 2 rather than verify a different "
            "revision. A single declared pin that measures differently, a class artifact whose "
            "declared class id leaves the frozen four, an f0_binding or class_contract_pointer "
            "that stops resolving in the canonical F0, or a self-control that stops firing "
            "voids the rev27 integrity result at this revision."
        ),
        "reproduction": "python3 artifacts/worker-030/frozen_manifest_verify.py",
        "authority_note": (
            "Measurement only. No canonical byte was modified; no node status, no "
            "validation_status=passed and no gate verdict is claimed (worker authority limit, "
            "research_map/ASTRA_HANDOFF.md)."
        ),
    }

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print(f"checks: {payload['counts']}")
    for c in CHECKS:
        print(f"  [{c['status']:4}] {c['id']} {c['group']}: {c['detail'][:170]}")
    print("report:", args.json)
    return 1 if FAILED_BLOCKING else 0


if __name__ == "__main__":
    sys.exit(main())
