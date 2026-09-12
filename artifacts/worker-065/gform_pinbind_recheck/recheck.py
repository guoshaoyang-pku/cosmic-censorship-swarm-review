#!/usr/bin/env python3
"""W065-GFORM-PINBIND-RECHECK-05 driver (bounded class-bound worker measurement).

Question
--------
At the current G-FORM r3 verification window, does every declared hash side-pin
that a re-binding reviewer or tool would follow to reach a G-FORM class schema
(F1 / F2a / F2b) resolve to the live bytes?  Which classes are pin-bound and
which are not?  Did the 8 gate-relevant defects measured by
W065-CANON-SIDEPIN-CENSUS-04 repair?  And which landed reviews declare a stale
advertised pin instead of the live class bytes?

The checker is NOT re-implemented.  It is the byte-identical census-04
instrument (sha256 88b19be6...) copied into pinned/ and hash-verified on every
run; this driver only orchestrates it, rolls its per-pin output up per class,
and adds a fresh control set plus a review citation-hazard census.

Read-only on every canonical path.  Writes only under this artifact directory.
Exit codes: 0 = recheck completed (measurement is a result, not a pass/fail of
the gate), 1 = instrument error, 2 = window unstable or control failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-065/gform_pinbind_recheck"
PINNED_CHECKER = ART / "pinned/check_sidepins.pinned.py"
CHECKER_SHA = "88b19be6d9a7761b281f34dc3b8b162efe42ab6951f790e62ff962788eb47d43"
CENSUS04 = ROOT / "artifacts/worker-065/canon_sidepin_census"
CENSUS04_REPORT_SHA = "5b864c3c3339cb39d8440f966e81725fdf803ec27fc1a24d0b92fe1fbe26e97c"
CENSUS04_SHADOW_MANIFEST_SHA = "31b2c7ac93f1859489207960ccedaab29a2a9dc54e25c3a1891224b7a7c77882"
CENSUS04_CONTROLS_SHA = "6eee484b05d265450fc1448d461be2dac4300710ff7ffcb92674c5a60179611f"

CLASS_SCHEMAS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
WINDOW_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml.sha256",
    "schemas/af_scc_regularities.yaml",
    "entry_hashes.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/worker-065/canon_sidepin_census/check_sidepins.py",
    "artifacts/worker-065/canon_sidepin_census/sidepin_census.json",
    "artifacts/worker-065/canon_sidepin_census/control_results.json",
    "artifacts/worker-065/canon_sidepin_census/repair_shadow/MANIFEST.json",
    "runtime/state/worker-065_canon_sidepin_census_checkpoint.json",
]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX_ANY = re.compile(r"\b[0-9a-f]{64}\b")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def window_reading() -> dict:
    out = {}
    for rel in WINDOW_PATHS:
        p = ROOT / rel
        if not p.exists():
            out[rel] = {"exists": False}
            continue
        st = p.stat()
        out[rel] = {
            "exists": True,
            "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
            "sha256": sha256_file(p),
        }
    return out


def run_checker(registry_root: Path, targets_root: Path, out_path: Path):
    cmd = [
        sys.executable,
        str(PINNED_CHECKER),
        "--root", str(registry_root),
        "--targets", str(targets_root),
        "--json-out", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    data = None
    if out_path.exists():
        try:
            data = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            data = None
    return {"cmd": [str(x) for x in cmd], "rc": proc.returncode,
            "stderr": proc.stderr.strip()[-800:], "data": data}


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def defect_key(d: dict) -> tuple:
    """Identity of a pin defect. census-04 records no `category` key, so the
    identity is (source, target, advertised, live_sha256) and category is
    compared separately via the counts table."""
    return (d.get("source"), d.get("target"), d.get("advertised"), d.get("live_sha256"))


def build_base_shadow() -> tuple[Path, list]:
    """Copy census-04 repair shadow into this artifact dir, hash-verified."""
    shadow = ART / "shadow/base"
    if shadow.exists():
        shutil.rmtree(shadow)
    (shadow / "schemas").mkdir(parents=True)
    manifest = json.loads((CENSUS04 / "repair_shadow/MANIFEST.json").read_text())
    verifications = []
    for entry in manifest["files"]:
        src = CENSUS04 / "repair_shadow" / entry["shadow"]
        dst = shadow / entry["shadow"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        got = sha256_file(dst)
        verifications.append({
            "path": entry["shadow"],
            "census04_shadow_sha256": entry["shadow_sha256"],
            "copied_sha256": got,
            "match": got == entry["shadow_sha256"],
        })
    return shadow, verifications


def copy_shadow(tag: str) -> Path:
    dst = ART / "controls" / tag
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ART / "shadow/base", dst)
    return dst


def mutate_json(path: Path, mutate) -> None:
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def write_sidecar(path: Path, digest: str, target: str) -> None:
    path.write_text(f"{digest}  {target}\n")


def run_controls() -> dict:
    controls = []

    def check(cid, description, registry_root, expected_rc, expected_target=None, expected_category=None):
        out = ART / "controls" / f"{cid}_result.json"
        res = run_checker(Path(registry_root), ROOT, out)
        data = res["data"] or {}
        defects = list(data.get("gate_relevant_defects", [])) + list(data.get("advisory_defects", []))
        hit = None
        if expected_target is not None:
            for d in defects:
                tgt = str(d.get("target") or d.get("resolved_path") or "")
                if expected_target in tgt and (expected_category is None or d.get("category") == expected_category):
                    hit = d
                    break
        ok = res["rc"] == expected_rc and (expected_target is None or hit is not None)
        controls.append({
            "id": cid,
            "description": description,
            "registry_root": str(Path(registry_root).relative_to(ROOT)) if str(registry_root).startswith(str(ROOT)) else str(registry_root),
            "expected_rc": expected_rc,
            "observed_rc": res["rc"],
            "expected_target": expected_target,
            "expected_category": expected_category,
            "detected": hit,
            "pass": ok,
        })

    # C1: census-04 repaired shadow -> clean.
    check("C1", "census-04 repair shadow, hash-verified copy -> checkpoint clean (rc 0)",
          ART / "shadow/base", 0)

    # C2: revert the F1 entry pin to the stale advertised hash.
    c2 = copy_shadow("C2_f1_entry_superseded")
    mutate_json(c2 / "entry_hashes.json",
                lambda d: d.__setitem__("schemas/af_wcc_vacuum.yaml",
                                        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"))
    check("C2", "repaired shadow with F1 entry reverted to stale 9a8bd4c9 -> STALE detected",
          c2, 2, "schemas/af_wcc_vacuum.yaml", "STALE")

    # C3: revert the F2b (C0) sidecar to the stale advertised hash.
    c3 = copy_shadow("C3_sidecar_superseded")
    write_sidecar(c3 / "schemas/af_scc_c0_vacuum.yaml.sha256",
                  "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
                  "af_scc_c0_vacuum.yaml")
    check("C3", "repaired shadow with F2b sidecar reverted to stale 1bb78ce9 -> STALE detected",
          c3, 2, "af_scc_c0_vacuum.yaml", "STALE")

    # C4: format-invariance / no-false-positive control: byte change, same pins.
    c4 = copy_shadow("C4_format_only")
    raw = json.loads((c4 / "entry_hashes.json").read_text())
    (c4 / "entry_hashes.json").write_text(json.dumps(raw, indent=4, sort_keys=False) + "\n\n")
    check("C4", "repaired shadow reserialised (bytes differ, pin values identical) -> still clean (no format false positive)",
          c4, 0)

    # C5: aggregator component pin reverted.
    c5 = copy_shadow("C5_aggregator_superseded")
    text = (c5 / "schemas/af_scc_regularities.yaml").read_text()
    text = text.replace("b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
                        "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508")
    (c5 / "schemas/af_scc_regularities.yaml").write_text(text)
    check("C5", "repaired shadow with aggregator C0 component pin reverted -> STALE detected",
          c5, 2, "schemas/af_scc_c0_vacuum.yaml", "STALE")

    return {
        "controls": controls,
        "all_pass": all(c["pass"] for c in controls),
        "n_controls": len(controls),
        "n_pass": sum(1 for c in controls if c["pass"]),
    }


def per_class_binding(live_data: dict) -> dict:
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_files = frozen.get("files", {})
    agg = None
    agg_path = ROOT / "schemas/af_scc_regularities.yaml"
    agg_text = agg_path.read_text()
    comp = {}
    for m in re.finditer(r"role:\s*(c2_component|c0_component)\b[\s\S]{0,600}?sha256:\s*\"?([0-9a-f]{64})", agg_text):
        comp[m.group(1)] = m.group(2)
    out = {}
    for cls, schema in CLASS_SCHEMAS.items():
        live = sha256_file(ROOT / schema)
        pins = []
        for p in live_data.get("pins", []):
            rp = str(p.get("resolved_path") or "")
            tgt = str(p.get("target") or "")
            if rp == schema or rp.endswith("/" + Path(schema).name) or tgt == schema or tgt.endswith("/" + Path(schema).name):
                pins.append({
                    "source": p.get("source"),
                    "target": p.get("target"),
                    "resolved_path": p.get("resolved_path"),
                    "advertised": p.get("advertised"),
                    "category": p.get("category"),
                    "gate_relevant": p.get("gate_relevant"),
                    "matches_live": p.get("advertised") == live,
                })
        frozen_pin = frozen_files.get(schema) or frozen_files.get(schema.replace("schemas/", ""))
        if isinstance(frozen_pin, dict):
            frozen_pin = frozen_pin.get("sha256") or frozen_pin.get("sha")
        agg_key = "c2_component" if cls == "AF-SCC-C2-VAC-GEN" else ("c0_component" if cls == "AF-SCC-C0-VAC-GEN" else None)
        agg_pin = comp.get(agg_key) if agg_key else None
        bad = [p for p in pins if p["category"] not in ("OK_LIVE", "OK_FROZEN_AND_LIVE")]
        hazards = []
        for p in bad:
            hazards.append({"kind": "declared_pin_stale", "source": p["source"], "target": p["target"],
                            "advertised": p["advertised"], "category": p["category"]})
        if frozen_pin != live:
            hazards.append({"kind": "frozen_pin_mismatch", "frozen_pin": frozen_pin, "live_sha256": live})
        if agg_key and agg_pin != live:
            hazards.append({"kind": "aggregator_component_pin_mismatch", "component": agg_key,
                            "aggregator_pin": agg_pin, "live_sha256": live})
        out[cls] = {
            "schema": schema,
            "live_sha256": live,
            "declared_pins": pins,
            "declared_pin_count": len(pins),
            "stale_declared_pins": len(bad),
            "frozen_rev29_pin": frozen_pin,
            "frozen_pin_matches_live": frozen_pin == live,
            "aggregator_component": agg_key,
            "aggregator_pin": agg_pin,
            "aggregator_pin_matches_live": (agg_pin == live) if agg_key else None,
            "hazards": hazards,
            "verdict": "PIN_BOUND" if not hazards else "PIN_HAZARD",
        }
    return out


def review_citation_census(live_data: dict) -> dict:
    """Count landed top-level reviews declaring a live vs stale-advertised class hash."""
    reviews_dir = ROOT / "reviews"
    files = sorted(p for p in reviews_dir.glob("*.json") if p.is_file())
    snapshot = [{"path": p.name, "sha256": sha256_file(p)} for p in files]
    snapshot_digest = hashlib.sha256(canonical(snapshot).encode()).hexdigest()

    live = {cls: sha256_file(ROOT / schema) for cls, schema in CLASS_SCHEMAS.items()}
    # advertised (stale) pins that resolve to each class schema, from the live run
    stale_advertised = {cls: set() for cls in CLASS_SCHEMAS}
    for p in live_data.get("pins", []):
        if p.get("category") != "STALE":
            continue
        rp = str(p.get("resolved_path") or "")
        tgt = str(p.get("target") or "")
        for cls, schema in CLASS_SCHEMAS.items():
            if rp == schema or rp.endswith("/" + Path(schema).name) or tgt == schema or tgt.endswith("/" + Path(schema).name):
                stale_advertised[cls].add(p.get("advertised"))

    per_class = {cls: {"buckets": {"live_only": 0, "stale_advertised_only": 0, "both_live_and_stale": 0,
                                   "other_hashes_only": 0, "no_64hex": 0},
                       "live_records": [], "stale_advertised_records": []}
                 for cls in CLASS_SCHEMAS}
    unparseable = []
    total_reviews = 0
    for p in files:
        try:
            doc = json.loads(p.read_text())
        except Exception as exc:  # noqa: BLE001 - record, never abort the census
            unparseable.append({"path": p.name, "error": str(exc)[:120]})
            continue
        total_reviews += 1
        strings = []
        stack = [doc]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
            elif isinstance(cur, str):
                strings.append(cur)
        hashes = set()
        for s in strings:
            for m in HEX_ANY.findall(s):
                hashes.add(m)
        reviewer = doc.get("reviewer") if isinstance(doc, dict) else None
        verdict = doc.get("verdict") if isinstance(doc, dict) else None
        for cls in CLASS_SCHEMAS:
            is_live = live[cls] in hashes
            stale_hits = sorted(hashes & stale_advertised[cls])
            is_stale = bool(stale_hits)
            if is_live and is_stale:
                per_class[cls]["buckets"]["both_live_and_stale"] += 1
            elif is_live:
                per_class[cls]["buckets"]["live_only"] += 1
            elif is_stale:
                per_class[cls]["buckets"]["stale_advertised_only"] += 1
            elif hashes:
                per_class[cls]["buckets"]["other_hashes_only"] += 1
            else:
                per_class[cls]["buckets"]["no_64hex"] += 1
            if is_live:
                per_class[cls]["live_records"].append(
                    {"reviewer": reviewer, "file": p.name, "verdict": verdict})
            if is_stale:
                per_class[cls]["stale_advertised_records"].append(
                    {"reviewer": reviewer, "file": p.name, "verdict": verdict, "declared": stale_hits})

    return {
        "reviews_dir": "reviews",
        "reviews_total": len(files),
        "reviews_parsed": total_reviews,
        "snapshot_digest_sha256": snapshot_digest,
        "snapshot_rule": "sha256 of canonical JSON of sorted [{path, sha256}] over top-level reviews/*.json at census time",
        "per_class": per_class,
        "unparseable": unparseable,
        "scope_note": ("declared-hash scan over string values of each review record; a record may declare "
                       "several hashes (target pin, instrument, cited evidence), so counts are per review per "
                       "class and are an upper bound on citation binding. Reviewer independence and verdict "
                       "merit remain the audit lead's adjudication."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", default=None, help="created_at stamp for the report")
    args = ap.parse_args(argv)
    stamp = args.stamp or time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # instrument integrity (fail closed before measuring)
    got_checker = sha256_file(PINNED_CHECKER)
    if got_checker != CHECKER_SHA:
        print(json.dumps({"error": "pinned checker hash mismatch", "got": got_checker, "want": CHECKER_SHA}))
        return 1
    got_c04 = sha256_file(CENSUS04 / "sidepin_census.json")
    got_c04_shadow = sha256_file(CENSUS04 / "repair_shadow/MANIFEST.json")
    got_c04_controls = sha256_file(CENSUS04 / "control_results.json")
    if (got_c04, got_c04_shadow, got_c04_controls) != (CENSUS04_REPORT_SHA, CENSUS04_SHADOW_MANIFEST_SHA, CENSUS04_CONTROLS_SHA):
        print(json.dumps({"error": "census-04 comparison pins mismatch",
                          "got": [got_c04, got_c04_shadow, got_c04_controls]}))
        return 1

    window_pre = window_reading()

    live_out = ART / "live_checker_run.json"
    live = run_checker(ROOT, ROOT, live_out)
    live2_out = ART / "live_checker_run_repeat.json"
    live2 = run_checker(ROOT, ROOT, live2_out)
    deterministic = canonical(live["data"]) == canonical(live2["data"]) and live["rc"] == live2["rc"]

    shadow, shadow_verifications = build_base_shadow()
    controls = run_controls()

    per_class = per_class_binding(live["data"] or {})
    citations = review_citation_census(live["data"] or {})

    window_post = window_reading()
    moved = [k for k in WINDOW_PATHS
             if window_pre.get(k, {}).get("sha256") != window_post.get(k, {}).get("sha256")]
    window = {
        "pre": window_pre,
        "post": window_post,
        "status": "STABLE" if not moved else "UNSTABLE",
        "moved_paths": moved,
    }

    c04 = json.loads((CENSUS04 / "sidepin_census.json").read_text())
    c04_defects = c04.get("gate_relevant_defects", [])
    c04_keys = {defect_key(d) for d in c04_defects}
    now_keys = {defect_key(d) for d in (live["data"] or {}).get("gate_relevant_defects", [])}
    comparison = {
        "census_04_counts": c04.get("category_counts"),
        "recheck_counts": (live["data"] or {}).get("counts"),
        "counts_equal": c04.get("category_counts") == (live["data"] or {}).get("counts"),
        "census_04_n_pins": c04.get("n_pins_measured"),
        "recheck_n_pins": (live["data"] or {}).get("n_pins"),
        "n_pins_equal": c04.get("n_pins_measured") == (live["data"] or {}).get("n_pins"),
        "defect_set_equal": c04_keys == now_keys,
        "defects_repaired_since_census_04": sorted(list(c04_keys - now_keys)),
        "defects_new_since_census_04": sorted(list(now_keys - c04_keys)),
        "census_04_gate_relevant_defect_count": len(c04_keys),
        "recheck_gate_relevant_defect_count": len(now_keys),
    }

    report = {
        "schema": "w065-gform-pinbind-recheck/1",
        "task_id": "W065-GFORM-PINBIND-RECHECK-05",
        "actor": "worker-065",
        "created_at": stamp,
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "primary_class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": list(CLASS_SCHEMAS),
        "question": ("Do all declared hash side-pins leading to the three G-FORM class schemas bind to live "
                     "bytes at the r3 verification window; did the census-04 defect set repair; which landed "
                     "reviews declare a stale advertised pin?"),
        "authority_note": ("worker measurement only; sets no node status, no validation_status=passed, no gate "
                           "verdict, and writes no canonical path. Reviewer independence/verdict merit is the "
                           "audit lead's adjudication."),
        "instrument": {
            "checker_path": "artifacts/worker-065/gform_pinbind_recheck/pinned/check_sidepins.pinned.py",
            "checker_sha256": got_checker,
            "checker_is_census_04_instrument": got_checker == CHECKER_SHA,
            "driver": "artifacts/worker-065/gform_pinbind_recheck/recheck.py",
            "driver_sha256": sha256_file(Path(__file__).resolve()),
            "deterministic_two_runs": deterministic,
            "census_04_comparison_pins": {
                "sidepin_census.json": got_c04,
                "repair_shadow/MANIFEST.json": got_c04_shadow,
                "control_results.json": got_c04_controls,
            },
        },
        "window": window,
        "live_run": {
            "rc": live["rc"],
            "verdict": (live["data"] or {}).get("verdict"),
            "n_pins": (live["data"] or {}).get("n_pins"),
            "counts": (live["data"] or {}).get("counts"),
            "gate_relevant_defects": (live["data"] or {}).get("gate_relevant_defects"),
            "mirror_alignment": (live["data"] or {}).get("mirror_alignment"),
        },
        "census_04_comparison": comparison,
        "shadow_base_verification": {
            "source": "artifacts/worker-065/canon_sidepin_census/repair_shadow",
            "files": shadow_verifications,
            "all_match": all(v["match"] for v in shadow_verifications),
            "local_copy": "artifacts/worker-065/gform_pinbind_recheck/shadow/base",
        },
        "per_class_binding": per_class,
        "per_class_verdicts": {cls: v["verdict"] for cls, v in per_class.items()},
        "citation_hazard_census": citations,
        "controls": controls,
        "falsifier": ("Falsified if (a) any reviewed pin is shown to resolve correctly under a declared "
                      "resolution rule (FROZEN path_policy redirect or a documented alias); or (b) any pinned "
                      "path's bytes moved between the window pre and post readings (window UNSTABLE voids the "
                      "measurement at the newer revision); or (c) a declared pin this recheck calls STALE is "
                      "shown byte-equal to its target under any declared resolution rule; or (d) re-running the "
                      "pinned checker at the recorded window does not reproduce the reported defect set."),
        "result_summary": {
            "window_status": window["status"],
            "live_checker_rc": live["rc"],
            "gate_relevant_defects": len(now_keys),
            "defect_set_unchanged_since_census_04": comparison["defect_set_equal"],
            "per_class_verdicts": {cls: v["verdict"] for cls, v in per_class.items()},
            "controls_pass": f"{controls['n_pass']}/{controls['n_controls']}",
            "reviews_snapshot": {
                "total": citations["reviews_total"],
                "digest_sha256": citations["snapshot_digest_sha256"],
                "stale_advertised_only": {cls: citations["per_class"][cls]["buckets"]["stale_advertised_only"]
                                          for cls in CLASS_SCHEMAS},
                "live_only": {cls: citations["per_class"][cls]["buckets"]["live_only"]
                              for cls in CLASS_SCHEMAS},
                "both_live_and_stale": {cls: citations["per_class"][cls]["buckets"]["both_live_and_stale"]
                                        for cls in CLASS_SCHEMAS},
            },
        },
    }

    (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (ART / "controls.json").write_text(json.dumps({
        "task_id": "W065-GFORM-PINBIND-RECHECK-05",
        "created_at": stamp,
        "controls": controls["controls"],
        "all_pass": controls["all_pass"],
        "n_pass": controls["n_pass"],
        "n_controls": controls["n_controls"],
    }, indent=1, sort_keys=True) + "\n")

    print(json.dumps(report["result_summary"], indent=1))
    if window["status"] != "STABLE":
        return 2
    if not controls["all_pass"] or not deterministic or not report["shadow_base_verification"]["all_match"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
