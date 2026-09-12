#!/usr/bin/env python3
"""Independent re-derivation of the R2 F0 binding-chain repair (no imports from
rebind_rows_r2.py / rebind_catalog_pin.py).

Reads the pre-rebind snapshots, the live corpus/catalog/taxonomy and the
hardened checker report, then re-checks the repair from first principles:
the live rows must be content-identical to the snapshot rows, the only changed
field must be binding_status, every pin must equal the taxonomy measured on
disk, and the checker verdict at the live hashes must be PASS with all
controls detected.

Usage: python3 artifacts/flash-02/verify_rebind_r2.py [--report <path>]
Exit 0 = all checks pass.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

import yaml

CORPUS_SNAP = Path("artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl")
CATALOG_SNAP = Path("artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json")
CORPUS = Path("schemas/taxonomy_cases.jsonl")
CATALOG = Path("artifacts/flash-02/leak_rule_catalog.json")
TAXONOMY = Path("research_map/formulation_taxonomy.yaml")
CHECKER_REPORT = Path("artifacts/flash-02/taxonomy_cases_check_report.json")
REPORT = Path("artifacts/flash-02/rebind_r2_independent_check.json")
EXPECTED_CORPUS_BEFORE = "f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8"
EXPECTED_CATALOG_BEFORE = "215f6e228250827a3f80a6155fd9a71c0ed0548e347e1d7ec3332275f1fb6f17"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_corpus(p: Path):
    meta, rows = None, []
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        o = json.loads(s)
        if o.get("record_type") == "meta":
            meta = o
        else:
            rows.append(o)
    return meta, rows


def content(row: dict) -> str:
    body = {k: v for k, v in row.items() if k != "binding_status"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(REPORT))
    a = ap.parse_args()

    checks = []
    tax_sha = sha256_file(TAXONOMY)
    tax_doc = yaml.safe_load(TAXONOMY.read_text())
    tax_pin = "bound_taxonomy_sha_" + tax_sha[:12]
    meta, rows = parse_corpus(CORPUS)
    snap_meta, snap_rows = parse_corpus(CORPUS_SNAP)

    # C0: snapshots reproduce the declared pre-repair hashes
    c0 = (sha256_file(CORPUS_SNAP) == EXPECTED_CORPUS_BEFORE
          and sha256_file(CATALOG_SNAP) == EXPECTED_CATALOG_BEFORE)
    checks.append(("C0_snapshots_reproduce_pre_repair_hashes", c0,
                   {"corpus_snapshot": sha256_file(CORPUS_SNAP),
                    "catalog_snapshot": sha256_file(CATALOG_SNAP)}))

    # C1: live meta binds the taxonomy on disk (hash + revision)
    c1 = bool(meta) and meta["taxonomy_ref"]["sha256"] == tax_sha \
        and meta["taxonomy_ref"].get("revision") == tax_doc.get("revision")
    checks.append(("C1_meta_binds_live_taxonomy", c1,
                   {"meta_sha": (meta or {}).get("taxonomy_ref", {}).get("sha256"),
                    "disk_sha": tax_sha, "disk_revision": tax_doc.get("revision")}))

    # C2: all 36 row pins equal the live taxonomy pin
    bad_pins = [r.get("case_id") for r in rows if r.get("binding_status") != tax_pin]
    c2 = len(rows) == 36 and not bad_pins
    checks.append(("C2_all_rows_pin_live_taxonomy", c2,
                   {"rows": len(rows), "expected_pin": tax_pin, "bad": bad_pins[:5]}))

    # C3: row content (everything except binding_status) unchanged vs snapshot
    live_by_id = {r["case_id"]: r for r in rows}
    snap_by_id = {r["case_id"]: r for r in snap_rows}
    changed = [cid for cid in snap_by_id
               if cid not in live_by_id or content(live_by_id[cid]) != content(snap_by_id[cid])]
    c3 = not changed and set(live_by_id) == set(snap_by_id)
    checks.append(("C3_row_content_identical_to_snapshot", c3,
                   {"rows_compared": len(snap_by_id), "content_changed": changed[:5]}))

    # C4: only binding_status differs per row (field-level)
    field_diffs = {}
    for cid, srow in snap_by_id.items():
        lrow = live_by_id.get(cid, {})
        d = sorted(k for k in set(srow) | set(lrow) if srow.get(k) != lrow.get(k))
        if d != ["binding_status"]:
            field_diffs[cid] = d
    c4 = not field_diffs
    checks.append(("C4_only_binding_status_field_changed", c4,
                   {"rows_with_other_diffs": field_diffs}))

    # C5: meta record byte-identical to snapshot meta
    c5 = json.dumps(meta, sort_keys=True) == json.dumps(snap_meta, sort_keys=True)
    checks.append(("C5_meta_record_unchanged", c5, {}))

    # C6: catalog ref binds live taxonomy, rules intact, no orphan guards
    cat, cat_snap = json.loads(CATALOG.read_text()), json.loads(CATALOG_SNAP.read_text())
    guards = {g["id"] for g in tax_doc.get("guards", [])}
    orphans = [(r.get("rule_id"), g) for r in cat.get("rules", [])
               for g in (r.get("guard_ids") or r.get("guards") or []) if g not in guards]
    cat_ref = cat.get("taxonomy_ref", {})
    cat_body_same = ({k: v for k, v in cat.items() if k != "taxonomy_ref"}
                     == {k: v for k, v in cat_snap.items() if k != "taxonomy_ref"})
    c6 = (cat_ref.get("sha256") == tax_sha and cat_ref.get("revision") == tax_doc.get("revision")
          and not orphans and cat_body_same and len(cat.get("rules", [])) == 18)
    checks.append(("C6_catalog_ref_and_rules_valid", c6,
                   {"catalog_ref": cat_ref, "rules": len(cat.get("rules", [])),
                    "orphans": orphans[:5], "body_unchanged": cat_body_same}))

    # C7: hardened checker report matches live hashes and passed all controls
    rep = json.loads(CHECKER_REPORT.read_text())
    c7 = (rep.get("verdict") == "PASS"
          and rep.get("cases", {}).get("sha256") == sha256_file(CORPUS)
          and rep.get("taxonomy", {}).get("sha256") == tax_sha
          and rep.get("catalog", {}).get("sha256") == sha256_file(CATALOG)
          and rep.get("controls_all_detected") is True
          and len(rep.get("controls", [])) == 11
          and not rep.get("errors"))
    checks.append(("C7_checker_pass_at_live_hashes", c7,
                   {"verdict": rep.get("verdict"),
                    "controls": len(rep.get("controls", [])),
                    "controls_all_detected": rep.get("controls_all_detected"),
                    "errors": rep.get("errors", [])[:3]}))

    all_pass = all(ok for _, ok, _ in checks)
    report = {
        "report_version": "1.0",
        "tool": "artifacts/flash-02/verify_rebind_r2.py",
        "generated_for_task": "flash02-f0rebindr2-20260912T004453",
        "deterministic": True,
        "actor": "deepseek-flash-02",
        "node_id": (meta or {}).get("node_id"),
        "gate": (meta or {}).get("gate"),
        "verdict": "PASS" if all_pass else "FAIL",
        "checks": [{"id": i, "pass": ok, "detail": d} for i, ok, d in checks],
        "live_hashes": {"corpus": sha256_file(CORPUS), "catalog": sha256_file(CATALOG),
                        "taxonomy": tax_sha, "checker_report": sha256_file(CHECKER_REPORT)},
        "pre_repair_hashes": {"corpus": EXPECTED_CORPUS_BEFORE, "catalog": EXPECTED_CATALOG_BEFORE},
        "falsifier": ("Any single check false falsifies the repair: e.g. a live row whose content "
                      "differs from the snapshot, a pin unequal to the live taxonomy prefix, a "
                      "changed meta record, an orphaned catalog guard, or a checker report not "
                      "bound to the live corpus/catalog/taxonomy hashes."),
    }
    Path(a.report).write_text(json.dumps(report, indent=2) + "\n")
    for i, ok, d in checks:
        print(("PASS " if ok else "FAIL ") + i)
    print(f"verdict: {report['verdict']}")
    print(f"live corpus {report['live_hashes']['corpus']}")
    print(f"live catalog {report['live_hashes']['catalog']}")
    print(f"report: {a.report}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
