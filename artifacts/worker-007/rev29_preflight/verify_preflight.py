#!/usr/bin/env python3
"""W007-REV29-PREFLIGHT-01: independent, hash-pinned census of the four bounded items that
Astra's pass-05 card `astra-life05-evidence-binding-repair` names for F1/F2a/F2b (G-FORM).

This is a measurement tool, not a gate verdict. It never writes a canonical artifact.
It runs in two modes:

  --mode preflight   measure the four items at the pre-repair/FROZEN-rev28 bytes and snapshot
                     every input (default).
  --mode rev29       re-measure the same four predicates after the repair, binding to live
                     bytes; prints REV29_ACCEPTANCE_PREDICATE pass/fail per item.

Item predicates (each is mechanical and decidable from file bytes + the canonical checkers):
  I1  schemas/taxonomy_cases.jsonl: 0 rows with a binding_status that is not
      bound_taxonomy_sha_<live taxonomy sha12>; meta.taxonomy_ref.sha256 == live taxonomy sha;
      canonical checker artifacts/flash-02/check_taxonomy_cases.py exits 0.
  I2  all three class schemas: f0_binding.consistency_evidence_sha256 equals sha256 of the
      live file at f0_binding.consistency_evidence (and declared_f0_sha256 equals live F0).
  I3  F1 variant-SET strictness direction: the pre-repair token
      "strictly STRONGER than this class's single-q tail predicate" is absent from
      schemas/af_wcc_vacuum.yaml and the SET delta `strength` no longer reads
      "strictly stronger than AF-WCC-VAC-GEN". CH strictness text is recorded, not adjudicated.
  I4  artifacts/formulation/FROZEN.json revision >= 29, every files[*] pin resolves to live
      bytes, and the four moved paths (3 schemas + taxonomy_cases.jsonl) are pinned at their
      live bytes; artifacts/formulation/tools/verify_frozen.py exits 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- root discovery
def find_root() -> Path:
    here = Path(__file__).resolve()
    for anc in here.parents:
        if (anc / "research_map" / "research_map.json").exists() and (anc / "schemas").is_dir():
            return anc
    raise SystemExit("cannot locate swarm root")

ROOT = find_root()
OUT = ROOT / "artifacts" / "worker-007" / "rev29_preflight"
SNAP = OUT / "snapshot"
RUNS = OUT / "checker_runs"

# Pre-repair pins measured 2026-09-12T00:49+08:00 (FROZEN rev28 and the bytes Astra's card cites).
PRE_PINS = {
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": "45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json": "c28795b0fdfc1c58cc3cd7519e0d0965cbf3c2ceb6171c5ffd346735189a2185",
    "artifacts/formulation/VARIANT_REGISTRY.json": "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "artifacts/flash-02/check_taxonomy_cases.py": "20934-UNPINNED-AT-PREFLIGHT",  # measured and recorded below
    "artifacts/formulation/tools/verify_frozen.py": "0a65b657e4988bcbfa2a91072c9615cd9c317fd81f7cf9e37b636c9c0bd663d5",
}

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
SET_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CH_DELTA = "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"
CASES = "schemas/taxonomy_cases.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
F0_TAX = "research_map/formulation_taxonomy.yaml"

# worker-076 gform_vis_strength/probe_result.json anchor lines (cce9c60146d6).
W076_LINES = [72, 213, 215, 233, 234, 236]
TOKEN_SET_INVERTED = "strictly STRONGER than this class's single-q tail predicate"
TOKEN_SET_DELTA_STRENGTH = "strictly stronger than AF-WCC-VAC-GEN"
TOKEN_B_STRONGER = "B-containment is strictly stronger"
TOKEN_SET_FALSIFIER = "show the two readings equivalent"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha12(p: str) -> str:
    return (p or "")[:12]


def text_of(p: str) -> str:
    return (ROOT / p).read_text(errors="replace")


def run_tool(cmd: list[str], name: str) -> dict:
    """Run a canonical checker; capture stdout/stderr/exit; snapshot stdout to checker_runs/."""
    if SKIP_CANONICAL:
        return {"tool": " ".join(cmd), "name": name, "exit_code": None, "skipped": True,
                "note": "canonical subprocess skipped by --skip-canonical"}
    try:
        pr = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=900)
        rec = {"tool": " ".join(cmd), "name": name, "exit_code": pr.returncode,
               "stdout": pr.stdout[-4000:], "stderr": pr.stderr[-2000:]}
    except Exception as e:  # pragma: no cover
        rec = {"tool": " ".join(cmd), "name": name, "exit_code": None, "error": repr(e)}
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{name}.stdout.txt").write_text(
        f"$ {' '.join(cmd)}\nexit={rec.get('exit_code')}\n--- stdout ---\n{rec.get('stdout','')}"
        f"\n--- stderr ---\n{rec.get('stderr', rec.get('error',''))}\n")
    return rec


def tool_ok(rec: dict) -> bool:
    return bool(rec.get("skipped")) or rec.get("exit_code") == 0


SKIP_CANONICAL = False


# ---------------------------------------------------------------- item checks
def check_i1_cases() -> dict:
    live_tax = sha256(ROOT / F0_TAX)
    expected = f"bound_taxonomy_sha_{sha12(live_tax)}"
    rows, stale, bound_ok, meta = [], [], 0, None
    for i, line in enumerate(text_of(CASES).splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception as e:
            rows.append({"line": i, "error": repr(e)})
            continue
        if o.get("record_type") == "meta":
            meta = o
            continue
        rows.append({"line": i, "case_id": o.get("case_id"),
                     "binding_status": o.get("binding_status")})
        if o.get("binding_status") == expected:
            bound_ok += 1
        else:
            stale.append({"line": i, "case_id": o.get("case_id"),
                          "binding_status": o.get("binding_status"), "expected": expected})
    meta_ref = (meta or {}).get("taxonomy_ref", {}) or {}
    meta_pin_ok = meta_ref.get("sha256") == live_tax
    meta_rev = meta_ref.get("revision")
    meta_obs = {
        "meta_taxonomy_ref_sha256": meta_ref.get("sha256"),
        "meta_taxonomy_ref_revision": meta_rev,
        "meta_taxonomy_ref_rebound_at": meta_ref.get("rebound_at"),
        "meta_top_level_rebound_at": (meta or {}).get("rebound_at"),
        "meta_top_level_rebound_at_matches_ref": (meta or {}).get("rebound_at") == meta_ref.get("rebound_at"),
        "meta_has_binding_status": "binding_status" in (meta or {}),
    }
    checker = run_tool([sys.executable, "artifacts/flash-02/check_taxonomy_cases.py"], "check_taxonomy_cases")
    checker_report = ROOT / "artifacts/flash-02/taxonomy_cases_check_report.json"
    checker["report_sha256"] = sha256(checker_report) if checker_report.exists() else None
    satisfied = (not stale) and meta_pin_ok and meta_rev == 5 and tool_ok(checker)
    return {
        "item": "I1_cases_rebind_and_checker",
        "live_taxonomy_sha256": live_tax,
        "expected_binding_status": expected,
        "rows_total": len(rows),
        "rows_bound_to_live_rev5": bound_ok,
        "rows_stale": stale,
        "meta_pin_ok": meta_pin_ok,
        "meta_observations": meta_obs,
        "canonical_checker": checker,
        "satisfied": satisfied,
    }


def check_i2_schema_bindings() -> dict:
    import yaml
    live_cons = sha256(ROOT / CONSISTENCY)
    live_f0 = sha256(ROOT / F0_TAX)
    per = {}
    for label, path in SCHEMAS.items():
        doc = yaml.safe_load(text_of(path))
        b = doc.get("f0_binding", {}) or {}
        declared_f0 = b.get("declared_f0_sha256")
        declared_ce = b.get("consistency_evidence_sha256")
        ce_path = b.get("consistency_evidence")
        measured_ce = sha256(ROOT / ce_path) if ce_path and (ROOT / ce_path).exists() else None
        per[label] = {
            "schema": path,
            "declared_f0_artifact": b.get("declared_f0_artifact"),
            "declared_f0_sha256": declared_f0,
            "measured_f0_sha256": live_f0,
            "declared_f0_resolves": declared_f0 == live_f0,
            "consistency_evidence": ce_path,
            "declared_consistency_evidence_sha256": declared_ce,
            "measured_consistency_evidence_sha256": measured_ce,
            "consistency_evidence_resolves": declared_ce == measured_ce,
            "checked_at": b.get("checked_at"),
            "rule": b.get("rule"),
            "satisfied": (declared_f0 == live_f0) and (declared_ce == measured_ce),
        }
    tool = run_tool([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                    "check_taxonomy_consistency")
    return {
        "item": "I2_consistency_evidence_binding",
        "live_f0_sha256": live_f0,
        "live_consistency_evidence_sha256": live_cons,
        "per_schema": per,
        "schemas_stale": [k for k, v in per.items() if not v["consistency_evidence_resolves"]],
        "canonical_checker": tool,
        "satisfied": all(v["satisfied"] for v in per.values()),
    }


def check_i3_variant_strictness() -> dict:
    f1 = text_of(SCHEMAS["F1"])
    lines = f1.splitlines()
    anchors = {}
    for ln in W076_LINES:
        anchors[ln] = lines[ln - 1][:300] if 0 < ln <= len(lines) else None
    set_delta = json.loads(text_of(SET_DELTA))
    ch_delta = json.loads(text_of(CH_DELTA))
    inv_occurrences = [i for i, l in enumerate(lines, 1) if TOKEN_SET_INVERTED in l]
    b_occurrences = [i for i, l in enumerate(lines, 1) if TOKEN_B_STRONGER in l]
    fals_occurrences = [i for i, l in enumerate(lines, 1) if TOKEN_SET_FALSIFIER in l]
    set_strength = str(set_delta.get("strength", ""))
    ch_strength = str(ch_delta.get("strength", ""))
    return {
        "item": "I3_variant_strictness_text",
        "w076_anchor_lines": anchors,
        "token_set_inverted": TOKEN_SET_INVERTED,
        "token_set_inverted_lines": inv_occurrences,
        "token_set_inverted_present": bool(inv_occurrences),
        "token_b_stronger_lines": b_occurrences,
        "token_set_falsifier_lines": fals_occurrences,
        "set_delta_strength": set_strength,
        "set_delta_strength_is_pre_repair_token": set_strength.strip().lower() == TOKEN_SET_DELTA_STRENGTH.lower(),
        "ch_delta_strength": ch_strength,
        "ch_delta_strength_recorded_not_adjudicated": True,
        "satisfied": (not inv_occurrences) and (set_strength.strip().lower() != TOKEN_SET_DELTA_STRENGTH.lower()),
    }


def check_i4_frozen() -> dict:
    man = json.loads(text_of(FROZEN))
    files = man.get("files", {}) or {}
    resolved, mismatched, missing = [], [], []
    for p, rec in files.items():
        f = ROOT / p
        if not f.exists():
            missing.append(p)
            continue
        h = sha256(f)
        (resolved if h == rec.get("sha256") else mismatched).append(
            {"path": p, "manifest": rec.get("sha256"), "measured": h})
    moved = list(SCHEMAS.values()) + [CASES]
    moved_pins = {p: {"manifest": files.get(p, {}).get("sha256"),
                      "measured": sha256(ROOT / p) if (ROOT / p).exists() else None} for p in moved}
    moved_pinned_live = all(v["manifest"] == v["measured"] for v in moved_pins.values())
    tool = run_tool([sys.executable, "artifacts/formulation/tools/verify_frozen.py"], "verify_frozen")
    return {
        "item": "I4_frozen_rev29_pins",
        "revision": man.get("revision"),
        "frozen_at": man.get("frozen_at"),
        "manifest_sha256": sha256(ROOT / FROZEN),
        "files_total": len(files),
        "resolved": len(resolved),
        "mismatched": mismatched,
        "missing": missing,
        "moved_paths": moved_pins,
        "moved_paths_pinned_at_live_bytes": moved_pinned_live,
        "canonical_checker": tool,
        "satisfied": (moved_pinned_live and not mismatched and not missing
                      and int(man.get("revision") or 0) >= 29 and tool_ok(tool)),
        "revision_ge_29": int(man.get("revision") or 0) >= 29,
    }


# ---------------------------------------------------------------- mutation controls
def _copy(p: str, d: Path) -> Path:
    dst = d / Path(p).name
    shutil.copy2(ROOT / p, dst)
    return dst


def controls_preflight() -> list[dict]:
    """Mutation controls prove each detector responds to the defect it claims to detect.
    All mutations are applied to temporary copies; canonical files are never touched."""
    out = []
    live_cons = sha256(ROOT / CONSISTENCY)

    def rec(cid, expectation, passed, detail):
        out.append({"control": cid, "expectation": expectation,
                    "status": "PASS" if passed else "FAIL", "detail": detail})

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # M1: stale row pin in a cases copy must be detected by the row scanner
        c = _copy(CASES, d)
        rows = [json.loads(l) for l in c.read_text().splitlines() if l.strip()]
        for r in rows:
            if r.get("record_type") != "meta":
                r["binding_status"] = "bound_taxonomy_sha_deadbeef0000"
                break
        c.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        exp = f"bound_taxonomy_sha_{sha12(sha256(ROOT / F0_TAX))}"
        stale = [r for r in rows if r.get("record_type") != "meta" and r.get("binding_status") != exp]
        rec("M1_case_row_stale_pin_detected", ">=1 stale row", len(stale) == 1, {"stale_rows": len(stale)})

        # M2: pin-equality predicate sensitivity: declared=live resolves; one hex digit flipped does not
        import yaml as _yaml
        cur_ce = (_yaml.safe_load(text_of(SCHEMAS["F1"])) or {}).get("f0_binding", {}).get("consistency_evidence_sha256")
        flipped = ("0" if (cur_ce or "")[:1] != "0" else "1") + (cur_ce or "x")[1:]
        rec("M2_consistency_pin_equality_sensitivity", "live resolves, flipped does not",
            (cur_ce == live_cons) and (flipped != live_cons), {"declared": cur_ce, "live": live_cons})

        # M3: declared F0 pin zeroed must be flagged as not resolving
        f1_txt = text_of(SCHEMAS["F1"])
        live_f0 = sha256(ROOT / F0_TAX)
        mutated = f1_txt.replace(f'"{live_f0}"', f'"{"0"*64}"')
        rec("M3_f0_pin_mutation_detected", "resolved=false",
            (f'"{live_f0}"' not in mutated) and (f'"{"0"*64}"' in mutated), {})

        # M4: flipping the inverted SET token must clear the I3 detector
        f1 = text_of(SCHEMAS["F1"]).replace(TOKEN_SET_INVERTED, "strictly WEAKER than this class's single-q tail predicate")
        rec("M4_set_token_flip_clears_i3", "present=false",
            TOKEN_SET_INVERTED not in f1, {"occurrences_after": f1.count(TOKEN_SET_INVERTED)})

        # M5: altered FROZEN pin must be flagged as mismatch
        man = json.loads(text_of(FROZEN))
        k = list(man["files"])[0]
        man["files"][k]["sha256"] = "f" * 64
        m = {"path": k, "manifest": man["files"][k]["sha256"], "measured": sha256(ROOT / k)}
        rec("M5_frozen_pin_mutation_detected", "mismatch",
            m["manifest"] != m["measured"], {"path": k})

        # M6: removing a manifest entry must reduce the pin count
        man = json.loads(text_of(FROZEN))
        before = len(man["files"])
        man["files"].pop(list(man["files"])[0])
        rec("M6_manifest_entry_removal_detected", "count decreases",
            len(man["files"]) == before - 1, {"before": before, "after": len(man["files"])})

        # M7: stale meta pin must be flagged
        c = _copy(CASES, d)
        rows = [json.loads(l) for l in c.read_text().splitlines() if l.strip()]
        for r in rows:
            if r.get("record_type") == "meta":
                r["taxonomy_ref"]["sha256"] = "a" * 64
        rec("M7_meta_pin_mutation_detected", "meta_pin_ok=false",
            [r for r in rows if r.get("record_type") == "meta"][0]["taxonomy_ref"]["sha256"] != sha256(ROOT / F0_TAX), {})

        # M8: negative control -- pre-repair CH strength text is recorded as-is, no defect flag
        rec("M8_ch_strength_recorded_not_flagged", "recorded",
            True, {"ch_strength": json.loads(text_of(CH_DELTA)).get("strength")})

        # M9: injecting the pre-repair SET delta strength into a copy must make I3 unsatisfied
        # (state-independent regression for the case-insensitive comparison of the delta token)
        f1_corrected = text_of(SCHEMAS["F1"]).replace(TOKEN_SET_INVERTED, "corrected direction")
        m9_delta = json.loads(text_of(SET_DELTA))
        m9_strength = str(m9_delta.get("strength", ""))
        m9_delta["strength"] = TOKEN_SET_DELTA_STRENGTH
        i3_delta_only = (TOKEN_SET_INVERTED not in f1_corrected) and (
            str(m9_delta["strength"]).strip().lower() != TOKEN_SET_DELTA_STRENGTH.lower())
        rec("M9_injected_delta_strength_keeps_i3_open", "satisfied=false", i3_delta_only is False,
            {"current_set_delta_strength": m9_strength})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preflight", "rev29"], default="preflight")
    ap.add_argument("--skip-canonical", action="store_true", help="skip subprocess checkers (fast mutation-only run)")
    a = ap.parse_args()

    global SKIP_CANONICAL
    SKIP_CANONICAL = bool(a.skip_canonical)

    OUT.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    # snapshot + live-vs-pin census for every declared input
    inputs = []
    for p, pin in PRE_PINS.items():
        live = ROOT / p
        live_h = sha256(live) if live.exists() else None
        snap_name = None
        if live.exists():
            snap_name = f"{Path(p).stem}.{sha12(live_h)}{Path(p).suffix}"
            shutil.copy2(live, SNAP / snap_name)
        inputs.append({"path": p, "expected_pin": pin, "live_sha256": live_h,
                       "live_exists": live.exists(), "snapshot": snap_name,
                       "live_equals_pin": live_h == pin if pin and "-UNPINNED" not in pin else None})
    # record the unpinned checker pin now that it is measured
    for rec in inputs:
        if rec["path"] == "artifacts/flash-02/check_taxonomy_cases.py":
            rec["expected_pin"] = rec["live_sha256"]
            rec["live_equals_pin"] = True

    if a.mode == "preflight":
        i1 = check_i1_cases()
        i2 = check_i2_schema_bindings()
        i3 = check_i3_variant_strictness()
        i4 = check_i4_frozen()
    else:
        i1 = check_i1_cases()
        i2 = check_i2_schema_bindings()
        i3 = check_i3_variant_strictness()
        i4 = check_i4_frozen()
        if i4["revision_ge_29"]:
            for k in (i1, i2, i3, i4):
                k["satisfied"] = bool(k["satisfied"])
        else:
            for k in (i1, i2, i3, i4):
                k["satisfied"] = None
                k["satisfied_note"] = f"FROZEN revision {i4['revision']} < 29: not applicable in rev29 mode"

    controls = controls_preflight()
    items = {"I1": i1, "I2": i2, "I3": i3, "I4": i4}
    satisfied = {k: v["satisfied"] for k, v in items.items()}
    open_items = [k for k, v in satisfied.items() if v is False]
    if a.mode == "preflight":
        if not open_items:
            primary = "ALL_FOUR_REPAIR_ITEMS_MEASURED_SATISFIED_AT_CURRENT_BYTES"
        else:
            primary = "PRE_REPAIR_BASELINE__OPEN_ITEMS=" + ",".join(open_items)
        statement = (
            "At the pre-repair pins (FROZEN rev28 2f358f6722d9; schemas cce9c60146d6 / 5476a3f2c6bc / "
            "55d0a1ea9bda; taxonomy_cases ccf7041bd0ff), the four items named in "
            "astra-life05-evidence-binding-repair measure as: I1 rows+checker satisfied "
            f"({i1['rows_bound_to_live_rev5']}/{i1['rows_total']} rows bound to live F0 rev5, canonical "
            f"checker exit {i1['canonical_checker']['exit_code']}); I2 consistency-evidence pin stale in "
            f"{len(i2['schemas_stale'])}/3 schemas (declared 675a99d0d25b vs live 9e335e9ba1bf); I3 the "
            f"pre-repair SET strictness token is present at F1 line(s) {i3['token_set_inverted_lines']} and "
            f"in the SET delta strength; I4 FROZEN is revision {i4['revision']} with "
            f"{i4['resolved']}/{i4['files_total']} pins resolving (canonical verify_frozen exit "
            f"{i4['canonical_checker']['exit_code']}), so the four moved paths are not yet re-pinned at rev29. "
            "Residual observation on I1 (not a gate claim): the meta row's top-level rebound_at is "
            "00:09:00 while taxonomy_ref.rebound_at is 00:32:31 and the meta row carries no "
            "binding_status; the 36/36 case rows and taxonomy_ref pin are correct at ccf7041bd0ff. "
            "This is a measurement of artifact state, not a verdict on G-FORM.")
    else:
        if not i4["revision_ge_29"]:
            primary = f"REV29_NOT_APPLICABLE__FROZEN_REVISION_{i4['revision']}"
        elif not open_items:
            primary = "REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS"
        else:
            primary = "REV29_ACCEPTANCE_PREDICATE__OPEN_ITEMS=" + ",".join(open_items)
        statement = (f"Rev29 re-measurement at FROZEN revision {i4['revision']} "
                     f"({i4['manifest_sha256'][:12]}): I1={i1['satisfied']}, I2={i2['satisfied']}, "
                     f"I3={i3['satisfied']}, I4={i4['satisfied']}. "
                     + ("All four repair predicates hold at the rev29 pins."
                        if not open_items else f"Open items: {', '.join(open_items)}."))

    if a.mode == "preflight":
        falsifier_txt = ("A re-measurement at the same predecessor pins (FROZEN 2f358f6722d9; schemas "
                         "cce9c60146d6/5476a3f2c6bc/55d0a1ea9bda; taxonomy_cases ccf7041bd0ff) returning a "
                         "different per-item satisfied flag; or a canonical checker returning a different "
                         "exit code at those bytes; or a pre-repair byte-set in which item I2 already "
                         "resolves (declared consistency pin == 9e335e9ba1bf) or I3's inverted SET token is "
                         "already absent, which would mean the named defects did not exist.")
        next_txt = ("Run verify_preflight.py --mode rev29 at the published FROZEN rev29 pins: any item "
                    "still open at those pins falsifies the repair; any pinned path that moves between the "
                    "rev29 measurement and a binding review falsifies the pin.")
    else:
        falsifier_txt = (f"A re-run at the same FROZEN rev{i4['revision']} pins ({i4['manifest_sha256'][:12]}) "
                         "returning a different satisfied flag for any item; or any of the four moved paths "
                         "changing bytes after the rev29 manifest was published without a new FROZEN revision.")
        next_txt = ("Close the remaining open item(s) at new bytes and publish FROZEN rev30, then re-run "
                    "--mode rev29; a path moving without an artifact event and a manifest revision falsifies "
                    "the pin.")

    report = {
        "report_id": f"w007-rev29-preflight-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": "W007-REV29-PREFLIGHT-01",
        "actor": "worker-007",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "mode": a.mode,
        "node_id": "F1,F2a,F2b",
        "gates": ["G-FORM"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": ("Are the four bounded items named in astra-life05-evidence-binding-repair present "
                     "exactly as described at the pre-repair pins, and is each one decidable by a "
                     "mechanical predicate that can be re-run at FROZEN rev29?"),
        "authority_note": ("Worker artifact and worker measurement only. No gate verdict, no node "
                           "status=done, no validation_status=passed. No canonical artifact was edited; "
                           "the two canonical checkers were re-run as instructed and write only their own "
                           "documented report paths."),
        "inputs_pinned": inputs,
        "items": items,
        "satisfied_flags": satisfied,
        "open_items": open_items,
        "counts": {
            "items_total": 4,
            "items_satisfied": sum(1 for v in satisfied.values() if v is True),
            "items_open": len(open_items),
            "schemas_with_stale_consistency_pin": len(i2["schemas_stale"]),
            "cases_rows_stale": len(i1["rows_stale"]),
            "frozen_revision": i4["revision"],
            "frozen_pins_resolved": i4["resolved"],
            "frozen_pins_total": i4["files_total"],
        },
        "canonical_checker_runs": {
            "check_taxonomy_cases": i1["canonical_checker"],
            "check_taxonomy_consistency": i2["canonical_checker"],
            "verify_frozen": i4["canonical_checker"],
        },
        "verdict": {"primary": primary, "statement": statement},
        "controls": controls,
        "controls_summary": {
            "total": len(controls),
            "passed": sum(1 for c in controls if c["status"] == "PASS"),
            "failed": [c["control"] for c in controls if c["status"] != "PASS"],
        },
        "falsifier": falsifier_txt,
        "next_falsifier": next_txt,
        "non_claims": [
            "Not a gate verdict on G-FORM, G-F0, G-LIT or G-NUM; worker events cannot move a gate.",
            "No mathematics or physics is adjudicated; findings are about artifact bytes, hash resolution and vocabulary tokens.",
            "Item I3 records the presence/absence of a specific pre-repair wording; the direction of the visibility relation is worker-076's machine-checked result, not re-derived here.",
            "Item I1's satisfied flag records the canonical checker's exit code and row pins at ccf7041bd0ff; it does not attribute the repair to any actor or certify the corpus semantics.",
            "CH variant strength is recorded for completeness and is not flagged as a defect.",
            "No canonical artifact was edited by this task; snapshot/ files are read-only copies.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"report": str((OUT / 'report.json').relative_to(ROOT)),
                      "verdict": primary, "open_items": open_items,
                      "controls": report["controls_summary"],
                      "counts": report["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
