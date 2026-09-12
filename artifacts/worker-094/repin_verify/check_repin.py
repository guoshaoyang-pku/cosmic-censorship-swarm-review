#!/usr/bin/env python3
"""W094D-REPIN-VERIFY-01 — independent, re-runnable verification of the
astra-life03-repin-claims completion claim and the astra-life04-freeze-hold,
at the canonical bytes present when the run starts.

Task binding (class-bound):
  node F0, gate G-F0 / G-FORM
  class_ids AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH

Claims under test (from research_map/events.jsonl, ingested copy):
  * lead-form-20260912T003722-01  "corpus re-pins DONE
    (schemas/taxonomy_cases.jsonl f0c20b96f76d;
     schemas/f1_falsifier_tests.jsonl 56bcb4b3234b, 25 rows)"
  * lead-form-20260912T003800-01  "astra-life04-freeze-hold executed. Five
    canonical pins confirmed against FROZEN rev28 ..."
  * lead-form-lifecycle-close-final  lifecycle complete

Design rules (paid for in this project):
  * every check is a byte measurement, never a reading of prose;
  * the falsifier is executed, not described;
  * the pinned bytes are re-hashed at the end of the run: any in-run drift =>
    VOID_MOVING_TARGET and no verdict may bind;
  * a prior snapshot (--prior) is diffed so movement *between* verifications is
    reported instead of silently absorbed; the claim under test is judged at its
    own timestamp, not only at review time;
  * a synthetic negative control (--self-test) proves the stale-binding
    extractor fires before it is used on the live corpus.

Usage:
  python3 check_repin.py --json
  python3 check_repin.py --out report.json --pin-out PINNED.json [--prior PINNED_OLD.json]
  python3 check_repin.py --self-test
Exit status: 0 = all hard checks pass, 3 = hard failure(s), 4 = moving target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CN_TZ = timezone(timedelta(hours=8))

DECLARED_F0 = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
TAX_CASES = "schemas/taxonomy_cases.jsonl"
F1_TESTS = "schemas/f1_falsifier_tests.jsonl"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
PINNED_FILES = [DECLARED_F0, SUPPLEMENT, CONSISTENCY, FROZEN, TAX_CASES, F1_TESTS] + SCHEMAS

REPIN_CLAIM_EVENT = "lead-form-20260912T003722-01"
FREEZE_CLAIM_EVENT = "lead-form-20260912T003800-01"
CLOSE_EVENT = "lead-form-lifecycle-close-final"


# ----------------------------------------------------------------- utilities


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_cn() -> str:
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


def snapshot() -> dict:
    out = {}
    for p in PINNED_FILES:
        f = ROOT / p
        st = f.stat()
        out[p] = {
            "sha256": sha256(f),
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CN_TZ).isoformat(timespec="seconds"),
        }
    return out


def read_jsonl(path: Path):
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        out.append((i, json.loads(line)))
    return out


def extract_yaml_binding(path: Path) -> dict:
    """Line-based extraction of the f0_binding mapping (no YAML dependency)."""
    txt = path.read_text(encoding="utf-8")
    out = {}
    for key in (
        "declared_f0_artifact",
        "declared_f0_sha256",
        "consistency_evidence",
        "consistency_evidence_sha256",
        "checked_at",
    ):
        m = re.search(rf'{key}:\s*"([^"]*)"', txt)
        out[key] = m.group(1) if m else None
    return out


def binding_token(row: dict) -> str | None:
    """Return the 12-hex token asserted by a taxonomy_cases case row."""
    m = re.search(r"bound_taxonomy_sha_([0-9a-f]{12})", str(row.get("binding_status") or ""))
    return m.group(1) if m else None


def claim_source_events() -> dict:
    wanted = {REPIN_CLAIM_EVENT, FREEZE_CLAIM_EVENT, CLOSE_EVENT}
    found = {}
    for i, row in read_jsonl(ROOT / "research_map/events.jsonl"):
        if row.get("event_id") in wanted:
            found[row["event_id"]] = {"line": i, "event": row}
    return found


def event_time(ev: dict) -> str:
    return str(ev.get("created_at") or ev.get("_received_at") or "")


def load_prior(path: Path) -> dict:
    """Accept either a PINNED.json ({"files":{p:{sha256..}}}) or a report
    ({"measured_sha256":{p:sha}}). Returns {path: sha256}."""
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    if isinstance(d.get("files"), dict):
        for p, v in d["files"].items():
            out[p] = v.get("sha256") if isinstance(v, dict) else v
    elif isinstance(d.get("measured_sha256"), dict):
        out = dict(d["measured_sha256"])
    elif isinstance(d.get("pinned_snapshot"), dict):
        out = {p: v.get("sha256") for p, v in d["pinned_snapshot"].items()}
    else:
        raise SystemExit(f"--prior: unrecognised snapshot format: {path}")
    return {k: v for k, v in out.items() if isinstance(v, str)}


# ------------------------------------------------------------------- checks


class Report:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, cid, desc, ok, expected, observed, severity="hard"):
        self.checks.append(
            {
                "check_id": cid,
                "description": desc,
                "status": "PASS" if ok else "FAIL",
                "severity": severity,
                "expected": expected,
                "observed": observed,
            }
        )
        return ok

    def failed(self, severity="hard"):
        return [c for c in self.checks if c["status"] == "FAIL" and c["severity"] == severity]


def run_checks(prior: dict | None) -> dict:
    rep = Report()
    snap0 = snapshot()
    measured = {p: v["sha256"] for p, v in snap0.items()}
    f1_sha = measured["schemas/af_wcc_vacuum.yaml"]
    declared_f0 = measured[DECLARED_F0]

    # ---- FROZEN rev28 freeze-hold -------------------------------------
    frozen = json.loads((ROOT / FROZEN).read_text(encoding="utf-8"))
    frev = frozen.get("revision")
    rep.add("R01", "FROZEN manifest parses and is revision 28", frev == 28,
            "revision == 28", f"revision == {frev}")
    freeze_pins = {
        "R02": DECLARED_F0,
        "R03": SUPPLEMENT,
        "R04": "schemas/af_wcc_vacuum.yaml",
        "R05": "schemas/af_scc_c2_vacuum.yaml",
        "R06": "schemas/af_scc_c0_vacuum.yaml",
        "R07": CONSISTENCY,
    }
    freeze_ok = True
    for cid, path in freeze_pins.items():
        entry = (frozen.get("files") or {}).get(path)
        ok = bool(entry) and entry.get("sha256") == measured[path]
        freeze_ok = freeze_ok and ok
        rep.add(cid, f"FROZEN rev28 entry for {path} equals measured bytes", ok,
                measured[path][:16], (entry or {}).get("sha256", "MISSING")[:16])

    # ---- astra-life03-repin-claims: taxonomy corpus -------------------
    tc_rows = read_jsonl(ROOT / TAX_CASES)
    meta = next((d for _, d in tc_rows if d.get("record_type") == "meta"), None)
    cases = [d for _, d in tc_rows if d.get("record_type") != "meta"]
    meta_sha = ((meta or {}).get("taxonomy_ref") or {}).get("sha256")
    rep.add("R08", "taxonomy_cases meta binds the measured declared-F0 sha", meta_sha == declared_f0,
            declared_f0[:16], str(meta_sha)[:16] if meta_sha else "MISSING")
    tokens = [binding_token(d) for d in cases]
    stale = [t for t in tokens if t and t != declared_f0[:12]]
    rep.add("R09", "all taxonomy_cases case rows assert the declared-F0 sha", not stale,
            f"0/{len(cases)} stale", f"{len(stale)}/{len(cases)} stale (token {sorted(set(stale))})")
    tax_ref = (meta or {}).get("taxonomy_ref") or {}
    rep.add("R10", "taxonomy_cases meta records a rebind (note + timestamp)",
            bool(tax_ref.get("rebind_note")) and bool(tax_ref.get("rebound_at")),
            "rebind_note and rebound_at present", str(tax_ref.get("rebound_at")), severity="soft")

    # ---- astra-life03-repin-claims: F1 falsifier corpus ---------------
    f1s = [d for _, d in read_jsonl(ROOT / F1_TESTS)]
    bad_f1 = [d for d in f1s if d.get("binding_sha256") != f1_sha]
    rep.add("R11", "all f1_falsifier_tests rows bind the measured F1 schema sha", not bad_f1,
            f"25/25 == {f1_sha[:16]}", f"{len(bad_f1)}/{len(f1s)} mismatch")
    bad_rev = [d for d in f1s if str(d.get("binding_frozen_revision")) != str(frev)]
    rep.add("R12", "f1_falsifier_tests frozen-revision label equals current FROZEN revision",
            not bad_rev, str(frev),
            f"{len(bad_rev)}/{len(f1s)} label 27" if bad_rev else "ok", severity="soft")
    rep.add("R13", "f1_falsifier_tests records the rebind movement",
            all(d.get("rebind_note") and d.get("rebound_at") for d in f1s),
            "rebind_note+rebound_at on all rows",
            "present" if all(d.get("rebind_note") for d in f1s) else "missing", severity="soft")

    # ---- class schemas: f0_binding ------------------------------------
    for cid, path in (("R14", SCHEMAS[0]), ("R15", SCHEMAS[1]), ("R16", SCHEMAS[2])):
        b = extract_yaml_binding(ROOT / path)
        rep.add(cid, f"{path} declared_f0_sha256 equals measured declared F0",
                b["declared_f0_sha256"] == declared_f0,
                declared_f0[:16], str(b["declared_f0_sha256"])[:16])
    cons_measured = measured[CONSISTENCY]
    stale_cons = []
    for cid, path in (("R17", SCHEMAS[0]), ("R18", SCHEMAS[1]), ("R19", SCHEMAS[2])):
        b = extract_yaml_binding(ROOT / path)
        ok = b["consistency_evidence_sha256"] == cons_measured
        if not ok:
            stale_cons.append(path)
        rep.add(cid, f"{path} consistency_evidence_sha256 equals measured {CONSISTENCY}",
                ok, cons_measured[:16], str(b["consistency_evidence_sha256"])[:16])
    mirror_detail, mirror_ok = {}, True
    for path in SCHEMAS:
        mirror = "artifacts/formulation/" + path
        mp = ROOT / mirror
        h = sha256(mp) if mp.is_file() else None
        mirror_detail[mirror] = h[:16] if h else "MISSING"
        mirror_ok = mirror_ok and h == measured[path]
    rep.add("R20", "schemas/ and artifacts/formulation/schemas/ trees are byte-identical",
            mirror_ok, "3/3 mirror pairs equal", mirror_detail)

    # ---- FROZEN coverage of the two corpora ---------------------------
    listed = [p for p in (TAX_CASES, F1_TESTS) if p in (frozen.get("files") or {})]
    rep.add("R21", "both gate-evidence corpora are listed in the FROZEN manifest",
            len(listed) == 2, f"2/2 listed ({TAX_CASES}, {F1_TESTS})",
            f"{len(listed)}/2 listed; missing {[p for p in (TAX_CASES, F1_TESTS) if p not in listed]}")

    # ---- the claim under test, judged at its own timestamp ------------
    events = claim_source_events()
    repin_ev = (events.get(REPIN_CLAIM_EVENT) or {}).get("event") or {}
    claim_text = str(repin_ev.get("summary") or repin_ev.get("statement") or "")
    claim_t = event_time(repin_ev)
    cited = re.findall(r"\b([0-9a-f]{12})\b", claim_text)
    tax_now = measured[TAX_CASES]
    f1_now = measured[F1_TESTS]
    cited_superseded = [c for c in cited if c not in (tax_now[:12], f1_now[:12])]
    rep.add("R22", f"{REPIN_CLAIM_EVENT} cites only current corpus hashes",
            bool(cited) and not cited_superseded,
            f"cited subset of {{{tax_now[:12]}, {f1_now[:12]}}}",
            f"cited={cited}; superseded={cited_superseded}")
    mtime_after_claim = snap0[TAX_CASES]["mtime"] > claim_t
    rep.add("R23", "taxonomy_cases bytes predate the 're-pins DONE' claim (claim not premature)",
            not mtime_after_claim, f"mtime <= {claim_t}",
            f"mtime={snap0[TAX_CASES]['mtime']} > claim={claim_t}" if mtime_after_claim
            else f"mtime={snap0[TAX_CASES]['mtime']}")
    rep.add("R24", "claim substance holds at current bytes (both corpora bind current canonicals)",
            not stale and not bad_f1, "0 stale case rows, 0 mismatched F1 rows",
            f"case stale={len(stale)}, f1 mismatch={len(bad_f1)}")
    rep.add("R25", f"freeze-hold claim {FREEZE_CLAIM_EVENT} present and bound to FROZEN rev28",
            bool(events.get(FREEZE_CLAIM_EVENT)) and frev == 28,
            "event present and revision 28",
            f"present={bool(events.get(FREEZE_CLAIM_EVENT))}, revision={frev}", severity="soft")

    # ---- movement against the caller's prior snapshot -----------------
    movement = []
    if prior:
        for p in PINNED_FILES:
            old = prior.get(p)
            new = measured[p]
            if old and old != new:
                movement.append({"path": p, "prior_sha256": old, "current_sha256": new,
                                 "current_mtime": snap0[p]["mtime"], "claim_time": claim_t})
    rep.add("R26", "no pinned file moved since the prior snapshot", not movement,
            "0 moved", f"{len(movement)} moved: {[m['path'] for m in movement]}", severity="move")

    # ---- in-run drift guard -------------------------------------------
    snap1 = snapshot()
    drift = [p for p in PINNED_FILES if snap1[p]["sha256"] != snap0[p]["sha256"]]
    rep.add("R27", "no pinned byte changed during this run (in-run moving-target guard)",
            not drift, "0 drifted", f"{len(drift)} drifted: {drift}")

    hard = rep.failed("hard")
    soft = rep.failed("soft")
    verdict = "void_moving_target" if drift else ("revise" if hard else "accept")
    return {
        "task_id": "W094D-REPIN-VERIFY-01",
        "actor": "worker-094",
        "generated_at": now_cn(),
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "claims_under_test": [REPIN_CLAIM_EVENT, FREEZE_CLAIM_EVENT, CLOSE_EVENT],
        "measured_sha256": measured,
        "pinned_snapshot": snap0,
        "prior_snapshot_used": prior is not None,
        "movement": movement,
        "claim_under_test": {
            "event_id": REPIN_CLAIM_EVENT,
            "created_at": claim_t,
            "cited_hashes": cited,
            "cited_superseded": cited_superseded,
            "taxonomy_cases_mtime": snap0[TAX_CASES]["mtime"],
            "premature": mtime_after_claim,
        },
        "checks": rep.checks,
        "summary": {
            "total": len(rep.checks),
            "pass": sum(1 for c in rep.checks if c["status"] == "PASS"),
            "fail_hard": len(hard),
            "fail_soft": len(soft),
            "hard_failure_ids": [c["check_id"] for c in hard],
            "finding_ids": [c["check_id"] for c in soft],
            "moved_files": [m["path"] for m in movement],
            "verdict": verdict,
            "repin_claim_citation_superseded": bool(cited_superseded),
            "repin_claim_premature": mtime_after_claim,
            "repin_substance_holds_now": not stale and not bad_f1,
            "consistency_binding_still_stale": stale_cons,
            "freeze_hold_verified": freeze_ok,
        },
        "next_falsifier": (
            "Repin consistency_evidence_sha256 to " + cons_measured[:16] + " in all three"
            " schemas (both trees), list " + TAX_CASES + " and " + F1_TESTS + " in the FROZEN"
            " manifest, and re-emit an artifact event carrying " + tax_now[:12] + "; then re-run"
            " this checker with --prior on the PINNED.json of this run. If all hard checks pass"
            " and the declared-F0 sha " + declared_f0[:12] + " is unchanged, this revise is"
            " superseded by an accept. Any change to the declared-F0 sha voids this verification."
        ),
        "non_claims": [
            "not a node completion",
            "not a gate verdict",
            "not a theorem",
            "advisory review evidence only; binds only the snapshot above",
        ],
    }


# -------------------------------------------------------------- self-test


def self_test() -> int:
    """Negative control: the stale-binding extractor must fire on a synthetic
    stale corpus and stay silent on a synthetic fresh one; the hash helper must
    pass a known-answer test."""
    ok = True
    stale_row = {"record_type": "case", "binding_status": "bound_taxonomy_sha_66bf917bd368"}
    fresh_row = {"record_type": "case", "binding_status": "bound_taxonomy_sha_0abb9ed8a961"}
    t = binding_token(stale_row)
    if t != "66bf917bd368":
        print("SELFTEST FAIL: stale token not extracted:", t)
        ok = False
    if t == "0abb9ed8a961":
        print("SELFTEST FAIL: extractor conflates stale and fresh")
        ok = False
    if binding_token(fresh_row) != "0abb9ed8a961":
        print("SELFTEST FAIL: fresh token not extracted")
        ok = False
    if binding_token({}) is not None:
        print("SELFTEST FAIL: missing binding_status should yield None")
        ok = False
    import tempfile

    with tempfile.NamedTemporaryFile("wb", delete=False) as fh:
        fh.write(b"w094d-control\n")
        tmp = Path(fh.name)
    try:
        if sha256(tmp) != hashlib.sha256(b"w094d-control\n").hexdigest():
            print("SELFTEST FAIL: sha256 known-answer mismatch")
            ok = False
    finally:
        tmp.unlink()
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--pin-out")
    ap.add_argument("--prior")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    prior = load_prior(Path(args.prior)) if args.prior else None
    report = run_checks(prior)
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.pin_out:
        pin = {
            "task_id": report["task_id"],
            "snapshot_at": report["generated_at"],
            "note": "byte pins for this verification run; any later change voids the verdict",
            "files": report["pinned_snapshot"],
        }
        Path(args.pin_out).write_text(json.dumps(pin, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    if args.json or not args.out:
        print(text)
    s = report["summary"]
    print(
        f"[W094D] {s['pass']}/{s['total']} pass | hard {s['fail_hard']} | soft {s['fail_soft']}"
        f" | moved {len(s['moved_files'])} | verdict {s['verdict']}",
        file=sys.stderr,
    )
    if s["verdict"] == "void_moving_target":
        return 4
    return 0 if s["fail_hard"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
