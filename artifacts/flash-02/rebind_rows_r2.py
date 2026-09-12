#!/usr/bin/env python3
"""R2 row-pin rebind for schemas/taxonomy_cases.jsonl (F0 / G-F0).

Defect being repaired (worker-094 review, HF-094C-1):
  The corpus meta was rebound to canonical F0 rev5 (0abb9ed8a961) at 00:32:31,
  but all 36 case rows still carry binding_status
  "bound_taxonomy_sha_66bf917bd368" (the pre-closure rev2 pin).  The corpus is
  internally self-contradictory and cannot serve as hash-bound gate evidence.

This tool performs the *minimal* repair: replace exactly the 36 row-level
binding_status pins so that every row binds the taxonomy file measured on disk.
It is deliberately not a re-serialisation: only the exact pin substring is
rewritten, so every other byte of every line is preserved.

Guards (all must hold or the tool exits non-zero without writing):
  G1  the taxonomy file measured on disk equals the hash recorded in the
      corpus meta.taxonomy_ref.sha256 (no silent revision drift);
  G2  every case row carries a binding_status of the form
      bound_taxonomy_sha_<12 hex>; anything malformed is refused;
  G3  every rewritten row, parsed, is identical to its pre-rebind parse in
      every field except binding_status (content-preservation proof), and the
      non-binding content digest is recorded per row;
  G4  the meta line and every non-case line are byte-identical after the edit;
  G5  replacement count equals the measured stale-pin count; no partial apply
      (the file is written atomically from the fully validated new text).

Idempotence: running again after a successful apply makes 0 replacements, all
rows already equal the current pin, and the tool exits 0 with mode="noop".

Usage:
  python3 artifacts/flash-02/rebind_rows_r2.py                    # dry run
  python3 artifacts/flash-02/rebind_rows_r2.py --apply            # write
  python3 artifacts/flash-02/rebind_rows_r2.py --report <path>    # default below
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

TAXONOMY_DEFAULT = "research_map/formulation_taxonomy.yaml"
CASES_DEFAULT = "schemas/taxonomy_cases.jsonl"
SNAPSHOT_DEFAULT = "artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl"
REPORT_DEFAULT = "artifacts/flash-02/rebind_rows_r2_report.json"
PIN_PREFIX = "bound_taxonomy_sha_"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def content_digest(row: dict) -> str:
    """Digest of a case row with the binding pin removed (content only)."""
    body = {k: v for k, v in row.items() if k != "binding_status"}
    return sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", default=TAXONOMY_DEFAULT)
    ap.add_argument("--cases", default=CASES_DEFAULT)
    ap.add_argument("--snapshot", default=SNAPSHOT_DEFAULT)
    ap.add_argument("--report", default=REPORT_DEFAULT)
    ap.add_argument("--apply", action="store_true",
                    help="write the repaired corpus (default: dry run)")
    a = ap.parse_args()

    tpath, cpath = Path(a.taxonomy), Path(a.cases)
    taxonomy_sha = sha256_file(tpath)
    taxonomy_pin = PIN_PREFIX + taxonomy_sha[:12]
    raw = cpath.read_bytes()
    cases_sha_before = sha256_bytes(raw)
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)

    meta = None
    rows = []           # (line_idx, parsed, line_text)
    parse_errors = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except ValueError as e:
            parse_errors.append(f"line {i + 1}: invalid JSON: {e}")
            continue
        if obj.get("record_type") == "meta":
            meta = obj
        else:
            rows.append((i, obj, line))

    errors = list(parse_errors)
    if meta is None:
        errors.append("no meta record found")
    if not rows:
        errors.append("no case rows found")

    # G1: taxonomy on disk must equal the meta declaration
    meta_sha = ((meta or {}).get("taxonomy_ref") or {}).get("sha256")
    if meta_sha != taxonomy_sha:
        errors.append(
            f"G1 FAIL: meta.taxonomy_ref.sha256={meta_sha!r} != taxonomy on disk {taxonomy_sha}")

    # G2: well-formed pins on every row
    stale, current, malformed = [], [], []
    for i, obj, line in rows:
        pin = obj.get("binding_status")
        if not isinstance(pin, str) or not pin.startswith(PIN_PREFIX):
            malformed.append((obj.get("case_id"), pin))
        elif pin == taxonomy_pin:
            current.append(obj.get("case_id"))
        else:
            stale.append((i, obj, line, pin))
            if len(pin) != len(PIN_PREFIX) + 12:
                malformed.append((obj.get("case_id"), pin))

    if malformed:
        errors.append(f"G2 FAIL: malformed binding_status: {malformed[:5]}")

    # Build the repaired text with exact substring replacement only.
    new_lines = list(lines)
    row_records = []
    n_replaced = 0
    for i, obj, line, pin in stale:
        needle = json.dumps(pin)  # exact quoted JSON string, e.g. "bound_..._66bf917bd368"
        if line.count(needle) != 1:
            errors.append(f"G5 FAIL: {obj.get('case_id')}: expected exactly 1 pin occurrence, "
                          f"found {line.count(needle)}")
            continue
        new_line = line.replace(needle, json.dumps(taxonomy_pin))
        try:
            after = json.loads(new_line.strip())
        except ValueError as e:
            errors.append(f"G3 FAIL: {obj.get('case_id')}: rewritten line does not parse: {e}")
            continue

        # G3: content preservation
        before_d, after_d = content_digest(obj), content_digest(after)
        diff_keys = sorted(set(obj) ^ set(after)) + \
            sorted(k for k in set(obj) & set(after) if obj[k] != after[k])
        if diff_keys != ["binding_status"] or before_d != after_d:
            errors.append(f"G3 FAIL: {obj.get('case_id')}: changed fields {diff_keys}")
            continue
        new_lines[i] = new_line
        n_replaced += 1
        row_records.append({
            "line": i + 1,
            "case_id": obj.get("case_id"),
            "class_id": obj.get("class_id"),
            "pin_before": pin,
            "pin_after": taxonomy_pin,
            "content_sha256_before": before_d,
            "content_sha256_after": after_d,
            "content_preserved": before_d == after_d,
        })

    new_text = "".join(new_lines)
    cases_sha_after = sha256_bytes(new_text.encode("utf-8"))
    noop = n_replaced == 0 and not stale

    # G4: everything except the rewritten rows is byte-identical
    if not noop:
        old_iter, new_iter = iter(lines), iter(new_lines)
        changed = [i for i, (o, n) in enumerate(zip(old_iter, new_iter)) if o != n]
        expected_changed = sorted(i for i, *_ in stale)
        if changed != expected_changed:
            errors.append(f"G4 FAIL: changed lines {changed} != expected {expected_changed}")
    else:
        if not meta:
            pass

    # snapshot must exist and match the pre-rebind bytes
    spath = Path(a.snapshot)
    snapshot_ok = spath.exists() and sha256_file(spath) == cases_sha_before
    if not noop and not snapshot_ok:
        errors.append(f"G6 FAIL: rollback snapshot missing or stale: {spath}")

    verdict = "FAIL" if errors else ("NOOP" if noop else "READY")
    report = {
        "report_version": "1.0",
        "tool": "artifacts/flash-02/rebind_rows_r2.py",
        "tool_sha256": sha256_file(Path(__file__)),
        "created_at": now_iso(),
        "actor": "deepseek-flash-02",
        "node_id": (meta or {}).get("node_id"),
        "gate": (meta or {}).get("gate"),
        "assignment_event_id": (meta or {}).get("assignment_event_id"),
        "defect_ref": "HF-094C-1 (reviews/closefind-verify-094.json)",
        "mode": "apply" if a.apply else "dry-run",
        "verdict": verdict,
        "taxonomy": {"path": str(tpath), "sha256": taxonomy_sha,
                     "pin_expected_new": taxonomy_pin},
        "corpus": {"path": str(cpath),
                   "sha256_before": cases_sha_before,
                   "sha256_after": cases_sha_after if not noop else cases_sha_before,
                   "bytes_before": len(raw),
                   "bytes_after": len(new_text.encode('utf-8'))},
        "counts": {"rows_total": len(rows), "rows_stale": len(stale),
                   "rows_already_current": len(current), "rows_replaced": n_replaced},
        "pin_before_observed": sorted({p for _, _, _, p in stale}) or None,
        "pin_after": taxonomy_pin,
        "rows": row_records,
        "guards": {
            "G1_taxonomy_matches_meta": meta_sha == taxonomy_sha,
            "G2_pins_well_formed": not malformed,
            "G3_content_preserved": all(r["content_preserved"] for r in row_records)
                                     and n_replaced == len(stale),
            "G4_only_target_rows_changed": not any(e.startswith("G4") for e in errors),
            "G5_exact_replacement_count": (n_replaced == len(stale)) if not noop else True,
            "G6_rollback_snapshot_verified": snapshot_ok or noop,
        },
        "rollback": {
            "snapshot": str(spath),
            "sha256": sha256_file(spath) if spath.exists() else None,
            "restore": f"cp {spath} {cpath}",
        },
        "falsifier": ("This rebind is invalid if any row's content digest (all fields except "
                      "binding_status) differs before/after, if the rewritten corpus does not "
                      "parse, if the count of replaced pins is not exactly the measured stale-pin "
                      "count, if any non-target line changes, or if the hardened checker "
                      "(stale-pin guard + control C11) does not PASS at the post-rebind hash and "
                      "the restored snapshot does not reproduce sha256 " + cases_sha_before + "."),
        "content_preservation_digest": sha256_bytes(json.dumps(
            {r["case_id"]: r["content_sha256_after"] for r in row_records},
            sort_keys=True, separators=(",", ":")).encode()),
        "errors": errors,
    }

    rpath = Path(a.report)
    rpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps(report, indent=2) + "\n")

    print(f"verdict: {verdict}  mode: {report['mode']}")
    print(f"stale rows: {len(stale)}  replaced: {n_replaced}  already current: {len(current)}")
    print(f"corpus sha256: {cases_sha_before} -> {report['corpus']['sha256_after']}")
    print(f"guards: {report['guards']}")
    if errors:
        print("errors:")
        for e in errors[:20]:
            print("  -", e)
        return 2

    if a.apply and not noop:
        tmp = cpath.with_suffix(cpath.suffix + ".tmp-rebind-r2")
        tmp.write_bytes(new_text.encode("utf-8"))
        os.replace(tmp, cpath)
        print(f"applied: {cpath}")
    elif not a.apply:
        print("dry run only; pass --apply to write")
    else:
        print("no-op: corpus already bound to the current taxonomy")
    print(f"report: {rpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
