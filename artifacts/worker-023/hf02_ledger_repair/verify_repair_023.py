#!/usr/bin/env python3
"""Independent verification of W023-L0-HF02-LEDGER-01.

Re-derives every assertion in report.json from raw bytes with its own parser,
its own HF-02 predicate (written from the rubric sentence, importing neither the
builder nor the 093 module), and re-executes the frozen runner scenarios from
the retained sandboxes. Adds a mutation control that reintroduces a dual-class
row into V8 and confirms the patched runner fires while the canonical one does
not.

Exit codes: 0 all checks pass; 2 a pinned input moved; 3 a check failed.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ART = REPO / "artifacts/worker-023/hf02_ledger_repair"
WORK = REPO / "tmp/w023_hf02_ledger_repair"
FROZEN4 = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
DISJ_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def dump(o: dict) -> str:
    return json.dumps(o, ensure_ascii=False, sort_keys=True)


def rows_of(raw: bytes) -> list[dict]:
    return [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]


def rid(r: dict) -> str:
    return r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"


def my_hf02(rows: list[dict]) -> list[str]:
    """Rubric sentence: classes 'must never be disjoined in a single class_ids'."""
    frozen = set(FROZEN4)
    out = []
    for r in rows:
        cids = [c for c in (r.get("class_ids") or []) if c in frozen]
        if len(set(cids)) >= 2:
            out.append(rid(r))
    return sorted(out)


def my_violation_key(v: dict) -> str:
    return json.dumps({"hf": v["hf"], "severity": v["severity"], "where": v["where"],
                       "detail": v["detail"]}, sort_keys=True)


def run(sb: Path, tag: str) -> dict:
    out = sb / "artifacts/audit" / f"verify_reports_{tag}"
    cmd = [sys.executable, str(sb / "artifacts/audit/audit_run.py"),
           "--map", str(sb / "research_map/research_map_trimmed.json"),
           "--scan", str(sb / "ledger"), "--out", str(out), "--quiet",
           "--kind", "findings", "--fail-on-critical"]
    p = subprocess.run(cmd, cwd=str(sb), capture_output=True, text=True)
    rp = out / "LATEST.json"
    if not rp.is_file():
        raise RuntimeError(f"{tag}: no report; exit={p.returncode} stderr={p.stderr[-400:]}")
    rep = json.loads(rp.read_text())
    vs = rep["violations"]
    disj = sorted(v["where"].split("ledger/", 1)[1] for v in vs
                  if v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids"))
    return {"exit_code": p.returncode, "violations_total": len(vs), "hf02_disjunction_rows": disj,
            "digest": sha_bytes(json.dumps(sorted(my_violation_key(v) for v in vs)).encode()),
            "gates": rep["gates"]}


def main() -> int:
    checks: list[dict] = []

    def check(name, expected, observed, ok=None):
        if ok is None:
            ok = expected == observed
        checks.append({"check": name, "expected": expected, "observed": observed, "pass": bool(ok)})

    report = json.loads((ART / "report.json").read_text())

    # V1: pinned inputs re-measured.
    moved = []
    for rel, want in report["pins"]["pins"].items():
        p = REPO / rel
        got = sha_file(p) if p.is_file() else None
        if got != want:
            moved.append({"path": rel, "expected": want, "measured": got})
    check("V1_pins_hold", [], moved)
    if moved:
        (ART / "verification.json").write_text(json.dumps(
            {"verdict": "VOID_MOVING_TARGET", "checks": checks}, indent=2, sort_keys=True) + "\n")
        return 2

    orig_raw = (REPO / "ledger/theorems.jsonl").read_bytes()
    v7_raw = (ART / "proposed_ledger_v7.jsonl").read_bytes()
    v8_raw = (ART / "proposed_ledger_v8.jsonl").read_bytes()
    check("V2_v7_hash_matches_report", report["variants"]["v7"]["sha256"], sha_bytes(v7_raw))
    check("V3_v8_hash_matches_report", report["variants"]["v8"]["sha256"], sha_bytes(v8_raw))

    rows = rows_of(orig_raw)
    v7, v8 = rows_of(v7_raw), rows_of(v8_raw)

    # V4: writer convention roundtrips byte-exactly on all three files.
    rt = []
    for name, raw in (("orig", orig_raw), ("v7", v7_raw), ("v8", v8_raw)):
        for i, l in enumerate(raw.decode("utf-8").splitlines()):
            if not l.strip():
                continue
            if dump(json.loads(l)) != l:
                rt.append({"file": name, "line": i + 1})
    check("V4_roundtrip_format", [], rt)

    # V5: independent row/field diff re-derivation.
    def my_diffs(a, b):
        out = []
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra == rb:
                continue
            keys = sorted(set(ra) | set(rb))
            out.append({"line": i + 1, "row_id": rid(ra),
                        "fields": {k: [ra.get(k), rb.get(k)] for k in keys if ra.get(k) != rb.get(k)}})
        return out

    for tag, rws, raw in (("v7", v7, v7_raw), ("v8", v8, v8_raw)):
        d_rep = report["variants"][tag]["row_diffs"]
        d_my = my_diffs(rows, rws)
        check(f"V5_{tag}_row_diffs", d_rep, d_my)
        la = orig_raw.decode("utf-8").splitlines()
        lb = raw.decode("utf-8").splitlines()
        check(f"V6_{tag}_changed_lines", report["variants"][tag]["changed_lines"],
              [i + 1 for i, (x, y) in enumerate(zip(la, lb)) if x != y])
        check(f"V7_{tag}_untouched_lines_identical", True,
              all(x == y for i, (x, y) in enumerate(zip(la, lb))
                  if i + 1 not in report["variants"][tag]["changed_lines"]))

    # V8: independent HF-02 predicate counts.
    counts = {"orig": len(my_hf02(rows)), "v7": len(my_hf02(v7)), "v8": len(my_hf02(v8))}
    check("V8_independent_hf02_counts", {"orig": 8, "v7": 1, "v8": 0}, counts)
    check("V9_disjunction_sets", {"orig": sorted(DISJ_ROWS), "v7": ["T-526"], "v8": []},
          {"orig": my_hf02(rows), "v7": my_hf02(v7), "v8": my_hf02(v8)})

    # V10: ids/order, vocabulary, binding channels.
    check("V10_ids_order", [rid(r) for r in rows], [rid(r) for r in v8])
    vocab = []
    channel = []
    for tag, rws in (("orig", rows), ("v7", v7), ("v8", v8)):
        by = {rid(r): r for r in rws}
        for r in rws:
            for f in ("class_ids", "informs_classes"):
                for c in (r.get(f) or []):
                    if c not in FROZEN4:
                        vocab.append({"variant": tag, "row": rid(r), "token": c})
        if tag != "orig":
            for row_id in report["variants"][tag]["changed_rows"]:
                r = by[row_id]
                if not (r.get("class_ids") or r.get("informs_classes")):
                    channel.append({"variant": tag, "row": row_id})
    check("V11_frozen_vocabulary", [], vocab)
    check("V12_binding_channel", [], channel)

    # V13: re-execute the six frozen scenarios and compare with the report.
    sandboxes = report["sandboxes"]
    reruns = {}
    for key in ("canon_orig", "canon_v7", "canon_v8", "patch_orig", "patch_v7", "patch_v8"):
        sb = Path(sandboxes[key]["sandbox"])
        got = run(sb, key)
        reruns[key] = got
        exp = report["scenarios"][key]
        check(f"V13_{key}_digest", exp["violations_digest"], got["digest"])
        check(f"V14_{key}_disjunction_rows", exp["hf02_disjunction_rows"], got["hf02_disjunction_rows"])
        check(f"V15_{key}_violations_total", exp["violations_total"], got["violations_total"])

    # V16: mutation control -- put one dual-class row back into V8; patched runner must
    # fire exactly once, canonical runner must stay blind.
    mut_src = Path(sandboxes["patch_v8"]["sandbox"])
    mut_dir = WORK / "verify_patch_v8_mut"
    if mut_dir.exists():
        shutil.rmtree(mut_dir)
    shutil.copytree(mut_src, mut_dir)
    mut_rows = copy.deepcopy(v8)
    idx = [rid(r) for r in mut_rows].index("D-004")
    mut_rows[idx]["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    (mut_dir / "ledger/theorems.jsonl").write_text(
        "\n".join(dump(r) for r in mut_rows) + "\n", encoding="utf-8")
    mut = run(mut_dir, "patch_v8_mut")
    check("V16_mutation_patched_fires_once", ["D-004"], mut["hf02_disjunction_rows"])
    canon_src = Path(sandboxes["canon_v8"]["sandbox"])
    canon_mut = WORK / "verify_canon_v8_mut"
    if canon_mut.exists():
        shutil.rmtree(canon_mut)
    shutil.copytree(canon_src, canon_mut)
    shutil.copy2(mut_dir / "ledger/theorems.jsonl", canon_mut / "ledger/theorems.jsonl")
    cm = run(canon_mut, "canon_v8_mut")
    check("V17_mutation_canonical_blind", 0, len(cm["hf02_disjunction_rows"]))

    # V18: canonical inputs unwritten by this verifier.
    check("V18_ledger_unwritten", report["ledger_sha256_before"], sha_file(REPO / "ledger/theorems.jsonl"))
    check("V19_audit_lib_unwritten", report["pins"]["pins"]["artifacts/audit/audit_lib.py"],
          sha_file(REPO / "artifacts/audit/audit_lib.py"))
    check("V20_audit_run_unwritten", report["pins"]["pins"]["artifacts/audit/audit_run.py"],
          sha_file(REPO / "artifacts/audit/audit_run.py"))

    ok = all(c["pass"] for c in checks)
    out = {
        "schema": "w023_hf02_ledger_repair_verification/1",
        "task_id": report["task_id"],
        "verifier": "worker-023 (independent re-derivation; own parser and predicate)",
        "created_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_report_sha256": sha_file(ART / "report.json"),
        "inputs": {"ledger": report["ledger_sha256_before"],
                   "v7": sha_bytes(v7_raw), "v8": sha_bytes(v8_raw)},
        "checks": checks,
        "reruns": reruns,
        "summary": {"checks_pass": sum(1 for c in checks if c["pass"]), "checks_total": len(checks),
                    "verdict": "PASS" if ok else "FAIL"},
        "verdict": "PASS" if ok else "FAIL",
    }
    (ART / "verification.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    (ART / "verification.json.sha256").write_text(sha_file(ART / "verification.json") + "  verification.json\n")
    print(json.dumps(out["summary"], indent=2))
    for c in checks:
        if not c["pass"]:
            print("FAIL:", json.dumps(c)[:500])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
