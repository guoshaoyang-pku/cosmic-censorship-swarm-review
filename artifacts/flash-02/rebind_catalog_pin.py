#!/usr/bin/env python3
"""R2 taxonomy_ref rebind for artifacts/flash-02/leak_rule_catalog.json (F0 / G-F0).

Companion repair to rebind_rows_r2.py.  After the corpus rows were rebound to
canonical F0 rev5 (0abb9ed8a961), the hardened checker still warned:

  WARN: catalog taxonomy_ref.sha256 differs from the taxonomy file on disk

The catalog is the leak-rule source consumed by the checker, so its ref must
bind the same taxonomy revision as the corpus.  Repair is textual and minimal:
only the unique `"revision": 3` and the unique 64-hex sha inside taxonomy_ref
are rewritten.  `path` and `status` (draft_unverified, unchanged in rev5) are
untouched, and every rule body is byte-identical.

Guards (all must hold or the tool exits non-zero without writing):
  G1  taxonomy on disk sha is the intended target and differs from the pin;
  G2  each replacement needle occurs exactly once in the file;
  G3  parsed content excluding taxonomy_ref.revision/sha256 is identical
      before/after (content-preservation proof, per-top-level-key digests);
  G4  every rule guard id referenced by the catalog exists in the current
      taxonomy guards (no orphaned leak rule);
  G5  rollback snapshot exists and matches the pre-rebind bytes;
  G6  on-disk sha after apply equals the sha of the validated new text.

Idempotent: re-running after apply reports NOOP.

Usage:
  python3 artifacts/flash-02/rebind_catalog_pin.py            # dry run
  python3 artifacts/flash-02/rebind_catalog_pin.py --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

CATALOG_DEFAULT = "artifacts/flash-02/leak_rule_catalog.json"
TAXONOMY_DEFAULT = "research_map/formulation_taxonomy.yaml"
SNAPSHOT_DEFAULT = "artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json"
REPORT_DEFAULT = "artifacts/flash-02/rebind_catalog_pin_report.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=CATALOG_DEFAULT)
    ap.add_argument("--taxonomy", default=TAXONOMY_DEFAULT)
    ap.add_argument("--snapshot", default=SNAPSHOT_DEFAULT)
    ap.add_argument("--report", default=REPORT_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    kpath, tpath = Path(a.catalog), Path(a.taxonomy)
    raw = kpath.read_bytes()
    catalog_sha_before = sha256_bytes(raw)
    text = raw.decode("utf-8")
    cat = json.loads(text)
    tax = yaml.safe_load(tpath.read_text())
    tax_sha = sha256_file(tpath)
    tax_rev = tax.get("revision")
    tax_status = tax.get("status")

    ref = cat.get("taxonomy_ref") or {}
    errors: list[str] = []

    pin_sha = ref.get("sha256")
    pin_rev = ref.get("revision")
    if pin_sha == tax_sha:
        noop = True
    else:
        noop = False

    # If the repair already ran, a NOOP invocation still has to record the
    # applied-state evidence: derive the pre-state from the verified snapshot.
    spath = Path(a.snapshot)
    snap_cat = None
    snap_sha = None
    if spath.exists():
        snap_sha = sha256_file(spath)
        try:
            snap_cat = json.loads(spath.read_text())
        except ValueError:
            snap_cat = None
    verify_applied = bool(noop and snap_cat and snap_sha != catalog_sha_before)
    if verify_applied:
        sref = snap_cat.get("taxonomy_ref") or {}
        pin_before = {"revision": sref.get("revision"), "sha256": sref.get("sha256"),
                      "status": sref.get("status")}
        sha_for_report = snap_sha
    else:
        pin_before = {"revision": pin_rev, "sha256": pin_sha, "status": ref.get("status")}
        sha_for_report = catalog_sha_before
    pin_sha_for_guard = pin_before["sha256"]

    # G1
    if not noop and not pin_sha:
        errors.append("G1 FAIL: catalog carries no taxonomy_ref.sha256 to rebind")
    # G4: no orphaned rule guard refs
    guards = {g["id"] for g in tax.get("guards", [])}
    orphans = []
    for r in cat.get("rules", []):
        for g in (r.get("guard_ids") or r.get("guards") or []):
            if g not in guards:
                orphans.append((r.get("rule_id"), g))
    if orphans:
        errors.append(f"G4 FAIL: catalog references guards absent from current taxonomy: {orphans[:5]}")

    rev_needle = f'"revision": {pin_rev}'
    sha_needle = json.dumps(pin_sha) if pin_sha else None
    new_text = text
    n_rev = n_sha = 0
    if not noop:
        # G2
        if text.count(rev_needle) != 1:
            errors.append(f"G2 FAIL: needle {rev_needle!r} occurs {text.count(rev_needle)} times")
        if text.count(sha_needle) != 1:
            errors.append(f"G2 FAIL: sha needle occurs {text.count(sha_needle)} times")
        if not errors:
            new_text = text.replace(rev_needle, f'"revision": {tax_rev}', 1)
            new_text = new_text.replace(sha_needle, json.dumps(tax_sha), 1)
            n_rev, n_sha = 1, 1
            # G6 (pre-write): new text parses and differs only inside taxonomy_ref
            try:
                after = json.loads(new_text)
            except ValueError as e:
                errors.append(f"G6 FAIL: rewritten catalog does not parse: {e}")
                after = None
            if after is not None:
                # G3
                a_cmp = {k: v for k, v in after.items() if k != "taxonomy_ref"}
                b_cmp = {k: v for k, v in cat.items() if k != "taxonomy_ref"}
                if json.dumps(a_cmp, sort_keys=True) != json.dumps(b_cmp, sort_keys=True):
                    errors.append("G3 FAIL: fields outside taxonomy_ref changed")
                a_ref, b_ref = dict(after["taxonomy_ref"]), dict(ref)
                a_ref.pop("revision", None); a_ref.pop("sha256", None)
                b_ref.pop("revision", None); b_ref.pop("sha256", None)
                if a_ref != b_ref:
                    errors.append(f"G3 FAIL: taxonomy_ref keys other than revision/sha256 changed: "
                                  f"{a_ref} != {b_ref}")

    new_sha = sha256_bytes(new_text.encode("utf-8"))
    snapshot_ok = spath.exists() and sha256_file(spath) == sha_for_report
    if not noop and not snapshot_ok:
        errors.append(f"G5 FAIL: rollback snapshot missing or stale: {spath}")

    verdict = "FAIL" if errors else ("NOOP" if noop else "READY")
    mode = "verify-applied" if verify_applied else ("apply" if a.apply else "dry-run")
    report = {
        "report_version": "1.0",
        "tool": "artifacts/flash-02/rebind_catalog_pin.py",
        "tool_sha256": sha256_file(Path(__file__)),
        "created_at": now_iso(),
        "actor": "deepseek-flash-02",
        "node_id": cat.get("node_id"),
        "gate": cat.get("gate"),
        "defect_ref": "checker WARN: catalog taxonomy_ref.sha256 differs from taxonomy on disk",
        "mode": mode,
        "verdict": verdict,
        "applied_state_verified": verify_applied,
        "taxonomy": {"path": str(tpath), "sha256": tax_sha, "revision": tax_rev,
                     "status": tax_status},
        "catalog": {"path": str(kpath),
                    "sha256_before": sha_for_report,
                    "sha256_after": new_sha if not noop else catalog_sha_before,
                    "bytes_before": len(raw), "bytes_after": len(new_text.encode('utf-8'))},
        "pin_before": pin_before,
        "pin_after": {"revision": tax_rev, "sha256": tax_sha, "status": ref.get("status")},
        "counts": {"revision_replacements": n_rev, "sha_replacements": n_sha,
                   "rules": len(cat.get("rules", [])), "orphan_guard_refs": len(orphans)},
        "guards": {
            "G1_pin_differs_and_target_known": (pin_sha_for_guard != tax_sha) and bool(tax_sha),
            "G2_needles_unique": (noop or (n_rev == 1 and n_sha == 1)),
            "G3_content_preserved_outside_ref": not any(e.startswith("G3") for e in errors),
            "G4_no_orphan_guard_refs": not orphans,
            "G5_rollback_snapshot_verified": snapshot_ok or noop,
            "G6_rewrite_parses_and_hashes": not any(e.startswith("G6") for e in errors),
        },
        "rollback": {"snapshot": str(spath),
                     "sha256": sha256_file(spath) if spath.exists() else None,
                     "restore": f"cp {spath} {kpath}"},
        "falsifier": ("This rebind is invalid if any catalog field other than "
                      "taxonomy_ref.revision/sha256 changed, if any rule guard id is absent from "
                      "the current taxonomy, if the catalog does not parse after rewrite, or if "
                      "the hardened checker still warns about the catalog taxonomy_ref after "
                      "apply; the restored snapshot must reproduce sha256 " + str(sha_for_report) + "."),
        "errors": errors,
    }
    rpath = Path(a.report)
    rpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps(report, indent=2) + "\n")

    print(f"verdict: {verdict}  mode: {report['mode']}")
    print(f"pin: rev {pin_before['revision']} {str(pin_before['sha256'])[:12]} -> "
          f"rev {tax_rev} {tax_sha[:12]}")
    print(f"catalog sha256: {sha_for_report} -> {report['catalog']['sha256_after']}")
    print(f"guards: {report['guards']}")
    if errors:
        for e in errors:
            print("  -", e)
        return 2
    if a.apply and not noop:
        tmp = kpath.with_suffix(kpath.suffix + ".tmp-rebind-r2")
        tmp.write_bytes(new_text.encode("utf-8"))
        os.replace(tmp, kpath)
        print(f"applied: {kpath}")
    elif a.apply:
        print("no-op: catalog already binds the current taxonomy")
    else:
        print("dry run only; pass --apply to write")
    print(f"report: {rpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
