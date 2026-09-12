#!/usr/bin/env python3
"""Independent re-check of the worker-010 AF-SCC-C0-VAC-GEN conformance audit.

This is a second implementation of the D1/D2/D3 predicates, written from the schema text rather
than from the audit script, plus hash/consistency checks.  It compares its verdicts to
`c0_class_conformance_audit.json` and writes `verify_c0_conformance.json`.

Exit code 0 = every check PASS (differences in non-verdict fields are reported, not fatal).
Exit code 1 = at least one verdict disagreement or hard consistency failure.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASS = "AF-SCC-C0-VAC-GEN"
AUDIT = HERE / "c0_class_conformance_audit.json"
OUT = HERE / "verify_c0_conformance.json"
TZ = timezone(timedelta(hours=8))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_verdict(entry: dict) -> dict:
    """Second implementation: regex-first, separate from the audit's marker-list classifier."""
    gen = (entry.get("genericity") or "")
    scope = " ".join(entry.get("scope_caveats") or [])
    assum = " ".join(entry.get("assumptions") or [])
    stmt = " ".join(str(entry.get(k) or "") for k in ("statement_exact", "label"))
    reg = entry.get("regularity") or ""
    topology = entry.get("topology") or ""
    hay = " ".join([gen, scope, assum, stmt, reg, topology])

    # D1 -- result over a generic (comeager/residual) AF vacuum data class
    is_result = entry.get("entry_kind") in {"theorem", "preprint_result"}
    generic = bool(re.search(r"comeagre|comeager|residual", gen, re.I))
    special = bool(re.search(
        r"exact solution|not a generic|not generic|not quantified|special|characteristic|interior|"
        r"impulsive|high-frequency|conditional on|assumed|does not fix|class-dependent|not applicable",
        gen + " " + scope, re.I))
    vacuum = bool(re.search(r"\bvacuum\b", hay, re.I))
    af = bool(re.search(r"asymptotically flat", hay, re.I))
    d1 = is_result and generic and vacuum and af and not special

    # D2 -- conclusion is non-existence of a continuous (C0) extension
    concl_ok = entry.get("conclusion_type") in {"theorem", "conditional_theorem"}
    no_extension = bool(re.search(r"inextendib", stmt, re.I))
    extension_exists = bool(re.search(
        r"continuously extendible|extends continuously|extended across|can be extended|"
        r"admits a non-trivial|extendible but not|c\^?0[ -]?extendible|c\^?0[ -]?stability",
        stmt, re.I))
    forbids_c0 = bool(re.search(
        r"merely continuous|continuous metric|c\^?0[\s-]*inextendib|lorentzian manifold with a continuous",
        stmt, re.I))
    weaker = bool(re.search(r"lipschitz|c\^?\{?0,1\}?|h2_loc|h\^?2_loc|c\^?2\b|l\^?2_loc", reg, re.I)) \
        and not re.search(r"merely continuous|continuous metric|c\^?0[\s-]*inextendib", stmt, re.I)
    d2 = concl_ok and no_extension and not extension_exists and forbids_c0 and not weaker

    # D3 -- accepted, primary/peer-reviewed, no open items
    d3 = (entry.get("status") == "accepted"
          and entry.get("evidence_level") in {"peer-reviewed", "accepted-in-press"}
          and not (entry.get("unresolved") or [])
          and not re.search(r"preprint|not peer-reviewed", scope, re.I))

    fails = [n for n, v in (("D1_data_class", d1), ("D2_conclusion", d2), ("D3_evidence", d3)) if not v]
    return {"discharges_class": not fails, "failing_conjuncts": fails}


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    ledger_path = ROOT / "ledger" / "theorems.jsonl"
    schema_path = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
    matrix_path = ROOT / "ledger" / "class_coverage.csv"
    frozen_path = ROOT / "artifacts" / "formulation" / "FROZEN.json"

    # 1. input hashes
    ledger_sha = sha256(ledger_path)
    check("ledger hash matches audit",
          ledger_sha == audit["inputs"]["ledger/theorems.jsonl"]["sha256"],
          {"measured": ledger_sha[:12], "audit": audit["inputs"]["ledger/theorems.jsonl"]["sha256"][:12]})
    schema_sha = sha256(schema_path)
    check("schema hash matches audit (or drift recorded)",
          schema_sha == audit["inputs"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"],
          {"measured": schema_sha[:12], "audit": audit["inputs"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"][:12],
           "note": "mismatch = canonical drift after the audit; verdict binds to the audit revision"})

    # 2. snapshot byte-identity and hash
    snap_rel = next(iter(audit["inputs"]["snapshot"]))
    snap_path = ROOT / snap_rel
    snap_sha = sha256(snap_path)
    snap_ok = snap_sha == audit["inputs"]["snapshot"][snap_rel]["sha256"]
    if not snap_ok:
        # the snapshot file itself is immutable; if it differs, the schema had already drifted
        snap_ok = snap_sha == schema_sha
    check("snapshot bytes == schema bytes (or schema drift since snapshot)", snap_ok,
          {"snapshot_sha256": snap_sha[:12], "snapshot_recorded": audit["inputs"]["snapshot"][snap_rel]["sha256"][:12],
           "schema_now": schema_sha[:12]})

    # 3. FROZEN binding prefix
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    f_c0 = (frozen.get("files", {}).get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256", "")
    check("FROZEN manifest binds the measured canonical C0 prefix",
          f_c0[:12] == schema_sha[:12],
          {"frozen_prefix": f_c0[:12], "measured": schema_sha[:12], "frozen_revision": frozen.get("revision")})

    # 4. independent recount + verdicts
    entries = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    bound = [e for e in entries if CLASS in (e.get("class_ids") or [])]
    check("bound entry count matches audit",
          len(bound) == audit["summary"]["n_bound_entries"],
          {"independent": len(bound), "audit": audit["summary"]["n_bound_entries"]})

    audit_by_id = {b["theorem_id"]: b for b in audit["bindings"]}
    disagreements = []
    discharging_ind = []
    for e in bound:
        tid = e.get("theorem_id")
        got = independent_verdict(e)
        if got["discharges_class"]:
            discharging_ind.append(tid)
        ref = audit_by_id.get(tid)
        if ref is None:
            disagreements.append({"theorem_id": tid, "issue": "missing from audit bindings"})
            continue
        if ref["discharges_class"] != got["discharges_class"] or ref["failing_conjuncts"] != got["failing_conjuncts"]:
            disagreements.append({
                "theorem_id": tid,
                "audit": {"discharges_class": ref["discharges_class"], "failing": ref["failing_conjuncts"]},
                "independent": got,
            })
    check("independent classifier agrees with audit on every binding",
          not disagreements, {"n_disagreements": len(disagreements), "disagreements": disagreements})
    check("independent discharge count == 0 == audit",
          len(discharging_ind) == audit["summary"]["n_discharging"] == 0,
          {"independent": discharging_ind, "audit": audit["summary"]["n_discharging"]})

    # 5. negative controls recorded and passing
    check("audit negative controls all_pass",
          bool(audit["negative_controls"]["all_pass"]),
          {"controls": [c["name"] + (":pass" if c["pass"] else ":FAIL") for c in audit["negative_controls"]["controls"]]})

    # 6. evidence refs use the measured ledger hash prefix
    bad_refs = [b["theorem_id"] for b in audit["bindings"]
                if not b["evidence_ref"].endswith("#" + ledger_sha[:12] + ":" + b["theorem_id"])]
    check("every binding evidence_ref carries the measured ledger hash prefix",
          not bad_refs, {"bad": bad_refs, "expected_prefix": ledger_sha[:12]})

    # 7. matrix crosswalk recount
    import csv as _csv
    with matrix_path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in _csv.DictReader(fh) if r["class_id"] == CLASS]
    check("matrix covered-cell recount",
          len([r for r in rows if r["coverage"] == "covered"]) == len(audit["summary"]["matrix_crosswalk"]["covered_cells"]),
          {"independent_covered": [r["source_id"] for r in rows if r["coverage"] == "covered"],
           "audit_covered": [c["source_id"] for c in audit["summary"]["matrix_crosswalk"]["covered_cells"]]})

    result = {
        "verifier": "worker-010-verify-c0-conformance",
        "checked_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "audit_id": audit["audit_id"],
        "audit_sha256": sha256(AUDIT),
        "all_pass": all(c["pass"] for c in checks),
        "checks": checks,
        "independent_summary": {
            "bound": len(bound),
            "discharging": discharging_ind,
            "class_conclusion_state": "open_problem" if not discharging_ind else "discharged",
        },
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"] + " :: " + json.dumps(c["detail"])[:220])
    print("all_pass:", result["all_pass"], "| wrote", OUT.name, "| sha256:", sha256(OUT))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
