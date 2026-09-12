#!/usr/bin/env python3
"""W023-L0-HF02-LEDGER-01 -- byte-exact repaired-ledger candidate for the HF-02
ledger class-disjunction (8 rows at ledger a1674f094979), plus independent
measurement of the canonical and 093-patched audit runners on it.

Worker-level artifact only: writes NOTHING to canonical paths. The canonical
ledger, rubric, audit tooling and map are opened read-only; all candidate bytes
and sandboxes live under artifacts/worker-023/hf02_ledger_repair/ and
tmp/w023_hf02_ledger_repair/.

Two variants are built, because one op (T-526) is explicitly conditioned on an
F1 membership ruling in the prior adjudication packet
(artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json):
  V7 = the 7 unqualified ops; T-526 left dual-class (HF-02 count 8 -> 1)
  V8 = all 8 ops; T-526 rebound as proposed (HF-02 count 8 -> 0, conditional)

Exit codes: 0 pass; 2 a pinned input moved (verdict void, not wrong); 3 a
check or control failed.
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

PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "artifacts/audit/audit_run.py":
        "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff":
        "0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a",
    "artifacts/worker-093/l0_rev3_review/patched_audit_lib.py":
        "9c8def1b50379e7cb5b6414cdf73c31e891276b2cf1bf8635a25aad7b4b1de8e",
}
EXPECTED_PATCHED_LIB = PINS["artifacts/worker-093/l0_rev3_review/patched_audit_lib.py"]

# The 8 ordered ops, verbatim from the prior adjudication packet's proposed_patch.
OPS = [
    {"row_id": "D-004", "class_ids": [], "informs_classes": ["AF-SCC-C0-VAC-GEN"],
     "ledger_tags_add": ["L2CONN"]},
    {"row_id": "D-005", "class_ids": [], "informs_classes": ["AF-SCC-C0-VAC-GEN"],
     "ledger_tags_add": ["LIP"]},
    {"row_id": "T-303", "class_ids": [], "informs_classes": ["AF-SCC-C0-VAC-GEN"],
     "ledger_tags_add": ["L2CONN"]},
    {"row_id": "T-305", "class_ids": [], "informs_classes": ["AF-SCC-C0-VAC-GEN"],
     "ledger_tags_add": ["LIP"]},
    {"row_id": "T-402", "class_ids": [],
     "informs_classes": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
     "ledger_tags_add": ["H2LOC"]},
    {"row_id": "T-515", "class_ids": ["AF-WCC-VAC-GEN"], "informs_classes": [],
     "ledger_tags_add": []},
    {"row_id": "T-526", "class_ids": [], "informs_classes": ["AF-SCC-C2-VAC-GEN"],
     "ledger_tags_add": ["LIP"]},
    {"row_id": "T-528", "class_ids": ["AF-WCC-VAC-GEN"], "informs_classes": [],
     "ledger_tags_add": []},
]
CONDITIONAL_ROW = "T-526"
DISJ_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

WIRING_LINE = '    claimv += A.check_ledger_class_disjunction(corpus["records"], classes)'
WIRING_ANCHOR = "    # HF-13: cross-project contamination in text artifacts"


# ---------------------------------------------------------------- utilities
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode())


def dump_line(o: dict) -> str:
    """The ledger's writer convention: sorted keys, default separators, literal UTF-8."""
    return json.dumps(o, ensure_ascii=False, sort_keys=True)


def load_rows(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def row_id(r: dict) -> str:
    return r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"


def disjunction_ids(rows: list[dict]) -> list[str]:
    frozen = set(FROZEN4)
    return [row_id(r) for r in rows if len({c for c in (r.get("class_ids") or []) if c in frozen}) >= 2]


def check_pins() -> dict:
    measured, moved = {}, []
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha256_file(p) if p.is_file() else None
        measured[rel] = got
        if got != want:
            moved.append({"path": rel, "expected": want, "measured": got})
    return {"pins": measured, "moved": moved}


def check(name: str, expected, observed, ok: bool | None = None) -> dict:
    if ok is None:
        ok = expected == observed
    return {"check": name, "expected": expected, "observed": observed, "pass": bool(ok)}


def violation_key(v: dict) -> str:
    return json.dumps({"hf": v["hf"], "severity": v["severity"],
                       "where": v["where"], "detail": v["detail"]}, sort_keys=True)


# ---------------------------------------------------------------- build
def build_variant(rows: list[dict], ops: list[dict]) -> tuple[list[dict], list[dict]]:
    out = copy.deepcopy(rows)
    index = {row_id(r): i for i, r in enumerate(out)}
    ops_applied = []
    for op in ops:
        i = index[op["row_id"]]
        r = out[i]
        before = copy.deepcopy(r)
        r["class_ids"] = list(op["class_ids"])
        r["informs_classes"] = list(op["informs_classes"])
        if op["ledger_tags_add"]:
            r["ledger_tags"] = sorted(set(r.get("ledger_tags") or []) | set(op["ledger_tags_add"]))
        ops_applied.append({"row_id": op["row_id"], "before": before, "after": copy.deepcopy(r)})
    return out, ops_applied


def row_diffs(a: list[dict], b: list[dict]) -> list[dict]:
    diffs = []
    for i, (ra, rb) in enumerate(zip(a, b)):
        if ra == rb:
            continue
        keys = sorted(set(ra) | set(rb))
        field_diffs = {k: [ra.get(k), rb.get(k)] for k in keys if ra.get(k) != rb.get(k)}
        diffs.append({"line": i + 1, "row_id": row_id(ra), "fields": field_diffs})
    return diffs


def line_diffs(raw_a: bytes, raw_b: bytes) -> list[int]:
    la = raw_a.decode("utf-8").splitlines()
    lb = raw_b.decode("utf-8").splitlines()
    return [i + 1 for i, (x, y) in enumerate(zip(la, lb)) if x != y]


def coverage(rows: list[dict], field: str) -> dict:
    cov = {c: 0 for c in FROZEN4}
    for r in rows:
        for c in (r.get(field) or []):
            if c in cov:
                cov[c] += 1
    return cov


def coverage_delta(a: dict, b: dict) -> dict:
    return {c: [a[c], b[c]] for c in a if a[c] != b[c]}


# ---------------------------------------------------------------- sandboxes
def build_sandbox(name: str, ledger_src: Path, patched: bool, map_src: Path) -> dict:
    sb = WORK / name
    if sb.exists():
        shutil.rmtree(sb)
    for d in ("artifacts/audit", "research_map", "ledger", "runtime/state"):
        (sb / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "artifacts/audit/audit_lib.py", sb / "artifacts/audit/audit_lib.py")
    shutil.copy2(REPO / "artifacts/audit/audit_run.py", sb / "artifacts/audit/audit_run.py")
    shutil.copy2(REPO / "evaluation_rubric.yaml", sb / "artifacts/audit/evaluation_rubric.yaml")
    shutil.copy2(ledger_src, sb / "ledger/theorems.jsonl")
    if (REPO / "runtime/state/started_at").is_file():
        shutil.copy2(REPO / "runtime/state/started_at", sb / "runtime/state/started_at")
    shutil.copy2(map_src, sb / "research_map/research_map_trimmed.json")

    info = {"sandbox": str(sb), "ledger_sha256": sha256_file(sb / "ledger/theorems.jsonl"),
            "lib_before": sha256_file(sb / "artifacts/audit/audit_lib.py"),
            "runner_before": sha256_file(sb / "artifacts/audit/audit_run.py")}
    if not patched:
        info.update(lib_after=info["lib_before"], runner_after=info["runner_before"],
                    patch_apply=None, wiring=None)
        return info

    diff = REPO / "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff"
    dry = subprocess.run(["patch", "-p1", "--dry-run", "-i", str(diff)], cwd=str(sb),
                         capture_output=True, text=True)
    real = subprocess.run(["patch", "-p1", "-i", str(diff)], cwd=str(sb),
                          capture_output=True, text=True)
    lib_after = sha256_file(sb / "artifacts/audit/audit_lib.py")
    info["patch_apply"] = {"dry_run_exit": dry.returncode, "apply_exit": real.returncode,
                           "apply_stdout": real.stdout.strip(), "lib_after": lib_after,
                           "matches_declared_patched_bytes": lib_after == EXPECTED_PATCHED_LIB}
    runner = (sb / "artifacts/audit/audit_run.py").read_text()
    n = runner.count(WIRING_ANCHOR)
    if n != 1:
        raise RuntimeError(f"{name}: wiring anchor occurs {n} times, expected 1")
    runner = runner.replace(WIRING_ANCHOR, WIRING_LINE + "\n\n" + WIRING_ANCHOR)
    (sb / "artifacts/audit/audit_run.py").write_text(runner)
    info["runner_after"] = sha256_file(sb / "artifacts/audit/audit_run.py")
    info["wiring"] = {"anchor": WIRING_ANCHOR, "inserted_line": WIRING_LINE,
                      "insertions": 1, "runner_after": info["runner_after"]}
    return info


def run_scenario(sb: Path, tag: str) -> dict:
    out = sb / "artifacts/audit" / f"reports_{tag}"
    cmd = [sys.executable, str(sb / "artifacts/audit/audit_run.py"),
           "--map", str(sb / "research_map/research_map_trimmed.json"),
           "--scan", str(sb / "ledger"),
           "--out", str(out), "--quiet", "--kind", "findings", "--fail-on-critical"]
    proc = subprocess.run(cmd, cwd=str(sb), capture_output=True, text=True)
    rp = out / "LATEST.json"
    if not rp.is_file():
        raise RuntimeError(f"scenario {tag}: no report; exit={proc.returncode} stderr={proc.stderr[-400:]}")
    report = json.loads(rp.read_text())
    vs = report["violations"]
    hf_counts: dict[str, int] = {}
    for v in vs:
        hf_counts[v["hf"]] = hf_counts.get(v["hf"], 0) + 1
    disj = sorted(v["where"].split("ledger/", 1)[1] for v in vs
                  if v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids"))
    digest = sha256_text(json.dumps(sorted(violation_key(v) for v in vs)))
    return {"tag": tag, "exit_code": proc.returncode, "stderr": proc.stderr.strip()[-300:],
            "summary": report["summary"], "gates": report["gates"],
            "violations_total": len(vs), "hf_counts": hf_counts,
            "hf02_disjunction_rows": disj, "hf02_disjunction_n": len(disj),
            "violations_digest": digest, "report_latest_sha256": sha256_file(rp),
            "violation_keys": sorted(violation_key(v) for v in vs)}


def keyset_delta(base: dict, var: dict) -> dict:
    b, v = set(base["violation_keys"]), set(var["violation_keys"])
    return {"added": sorted(v - b), "removed": sorted(b - v), "n_added": len(v - b), "n_removed": len(b - v)}


# ---------------------------------------------------------------- main
def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "schema": "w023_hf02_ledger_repair/1",
        "task_id": "W023-L0-HF02-LEDGER-01",
        "actor": "worker-023",
        "created_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "authority": "worker-level artifact; no canonical file written; applied=false; no node status or gate verdict",
        "validation_status": "unverified",
        "applied": False,
        "conditional_row": CONDITIONAL_ROW,
        "falsifier": (
            "Re-run build_repair_023.py at the pinned inputs. Falsified if: (a) any pinned hash differs "
            "(verdict void, exit 2); (b) V7/V8 do not differ from the original ledger on exactly the "
            "expected row sets or any unchanged line is not byte-identical; (c) any patched row loses both "
            "binding channels; (d) the rubric-literal HF-02 count is not 8/1/0 on original/V7/V8; "
            "(e) the 093-patched runner does not report exactly the expected disjunction rows, or the "
            "canonical runner reports any; (f) any non-HF-02 violation changes between variants; "
            "(g) any control fails."
        ),
        "reproduction": "python3 artifacts/worker-023/hf02_ledger_repair/build_repair_023.py",
    }

    pins = check_pins()
    report["pins"] = pins
    if pins["moved"]:
        report["verdict"] = "VOID_MOVING_TARGET"
        (WORK / "report_void.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("PIN MOVED -> verdict void (exit 2):", json.dumps(pins["moved"]))
        return 2

    checks: list[dict] = []
    ledger_raw = (REPO / "ledger/theorems.jsonl").read_bytes()
    report["ledger_sha256_before"] = sha256_bytes(ledger_raw)
    rows = load_rows(ledger_raw)
    lines = ledger_raw.decode("utf-8").splitlines()

    # C0: writer-convention roundtrip is byte-exact for every line.
    rt_bad = [i + 1 for i, l in enumerate(lines) if dump_line(json.loads(l)) != l]
    checks.append(check("C0_roundtrip_format", [], rt_bad))
    if rt_bad:
        report["checks"] = checks
        (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 3

    # C1: the 8 target rows are present, in the pre-repair dual-class state.
    present = [r for r in rows if row_id(r) in DISJ_ROWS]
    checks.append(check("C1_disj_rows_present", 8, len(present)))
    checks.append(check("C2_pre_repair_disjunction_ids", sorted(DISJ_ROWS), sorted(disjunction_ids(rows))))

    ops_v7 = [o for o in OPS if o["row_id"] != CONDITIONAL_ROW]
    ops_v8 = list(OPS)
    rows_v7, applied_v7 = build_variant(rows, ops_v7)
    rows_v8, applied_v8 = build_variant(rows, ops_v8)
    raw_v7 = ("\n".join(dump_line(r) for r in rows_v7) + "\n").encode("utf-8")
    raw_v8 = ("\n".join(dump_line(r) for r in rows_v8) + "\n").encode("utf-8")
    p_v7 = ART / "proposed_ledger_v7.jsonl"
    p_v8 = ART / "proposed_ledger_v8.jsonl"
    p_v7.write_bytes(raw_v7)
    p_v8.write_bytes(raw_v8)

    variants = {}
    for tag, raw, rws, applied in (("v7", raw_v7, rows_v7, applied_v7),
                                   ("v8", raw_v8, rows_v8, applied_v8)):
        d = row_diffs(rows, rws)
        ld = line_diffs(ledger_raw, raw)
        variants[tag] = {
            "ops_applied": [o["row_id"] for o in applied],
            "ops_n": len(applied),
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "rows": len(rws),
            "changed_rows": sorted(x["row_id"] for x in d),
            "changed_lines": ld,
            "row_diffs": d,
            "disjunction_ids_after": sorted(disjunction_ids(rws)),
            "disjunction_n_after": len(disjunction_ids(rws)),
            "class_ids_coverage": coverage(rws, "class_ids"),
            "informs_coverage": coverage(rws, "informs_classes"),
        }
    report["variants"] = variants

    checks.append(check("C3_v7_changed_rows", sorted(set(DISJ_ROWS) - {CONDITIONAL_ROW}),
                        variants["v7"]["changed_rows"]))
    checks.append(check("C4_v8_changed_rows", sorted(DISJ_ROWS), variants["v8"]["changed_rows"]))
    checks.append(check("C5_v7_v8_diff_rows_only_conditional", [CONDITIONAL_ROW],
                        sorted(set(variants["v8"]["changed_rows"]) - set(variants["v7"]["changed_rows"]))))
    allowed_fields = {"class_ids", "informs_classes", "ledger_tags"}
    bad_fields = []
    for tag in ("v7", "v8"):
        for d in variants[tag]["row_diffs"]:
            extra = set(d["fields"]) - allowed_fields
            if extra:
                bad_fields.append({"variant": tag, "row": d["row_id"], "fields": sorted(extra)})
    checks.append(check("C6_only_allowed_fields_changed", [], bad_fields))

    # C7: byte-identical except the changed lines.
    for tag in ("v7", "v8"):
        la = ledger_raw.decode("utf-8").splitlines()
        lb = (raw_v7 if tag == "v7" else raw_v8).decode("utf-8").splitlines()
        same_other = all(x == y for i, (x, y) in enumerate(zip(la, lb))
                         if i + 1 not in variants[tag]["changed_lines"])
        checks.append(check(f"C7_{tag}_untouched_lines_byte_identical", True, same_other))

    # C8: ids and order preserved; frozen-token-only vocabulary.
    ids_a = [row_id(r) for r in rows]
    checks.append(check("C8_v7_ids_order", ids_a, [row_id(r) for r in rows_v7]))
    checks.append(check("C9_v8_ids_order", ids_a, [row_id(r) for r in rows_v8]))
    off_vocab = []
    for tag, rws in (("orig", rows), ("v7", rows_v7), ("v8", rows_v8)):
        for r in rws:
            for f in ("class_ids", "informs_classes"):
                for c in (r.get(f) or []):
                    if c not in FROZEN4:
                        off_vocab.append({"variant": tag, "row": row_id(r), "field": f, "token": c})
    checks.append(check("C10_frozen_token_vocabulary_only", [], off_vocab))

    # C11: every patched row keeps a binding channel.
    no_channel = []
    for tag, rws in (("v7", rows_v7), ("v8", rows_v8)):
        idx = {row_id(r): r for r in rws}
        for rid in ([r for r in variants[tag]["changed_rows"]]):
            r = idx[rid]
            if not (r.get("class_ids") or r.get("informs_classes")):
                no_channel.append({"variant": tag, "row": rid})
    checks.append(check("C11_patched_rows_keep_binding_channel", [], no_channel))

    # C12: coverage deltas confined to the changed rows.
    cov_delta = {}
    for tag, rws in (("v7", rows_v7), ("v8", rows_v8)):
        cov_delta[tag] = {"class_ids": coverage_delta(coverage(rows, "class_ids"), coverage(rws, "class_ids")),
                          "informs_classes": coverage_delta(coverage(rows, "informs_classes"),
                                                            coverage(rws, "informs_classes"))}
    report["coverage_deltas"] = cov_delta

    # C13: the ledger's own disjunction predicate (re-implemented from the 093 patch logic).
    def literal_disjunction(rws: list[dict]) -> list[str]:
        frozen = set(FROZEN4)
        out = []
        for r in rws:
            cids = {c for c in (r.get("class_ids") or []) if c in frozen}
            if len(cids) >= 2:
                out.append(row_id(r))
        return sorted(out)

    lit = {"orig": literal_disjunction(rows), "v7": literal_disjunction(rows_v7),
           "v8": literal_disjunction(rows_v8)}
    report["literal_hf02"] = {k: {"n": len(v), "rows": v} for k, v in lit.items()}
    checks.append(check("C13_literal_hf02_counts", {"orig": 8, "v7": 1, "v8": 0},
                        {k: len(v) for k, v in lit.items()}))

    # C14: extended policy predicate imported from the declared patched bytes.
    sys.path.insert(0, str(REPO / "artifacts/worker-093/l0_rev3_review"))
    import patched_audit_lib as pal  # noqa: E402
    classes = {c: {} for c in FROZEN4}
    imported = {}
    for tag, rws in (("orig", rows), ("v7", rows_v7), ("v8", rows_v8)):
        vs = pal.check_ledger_class_disjunction(rws, classes)
        imported[tag] = sorted(v.where.split("ledger/", 1)[1] for v in vs)
    report["imported_checker_hf02"] = {k: {"n": len(v), "rows": v} for k, v in imported.items()}
    checks.append(check("C14_imported_checker_counts", {"orig": 8, "v7": 1, "v8": 0},
                        {k: len(v) for k, v in imported.items()}))

    # ------------------------------------------------------------ runners
    map_src = REPO / "research_map/research_map.json"
    report["research_map_snapshot_sha256"] = sha256_file(map_src)
    full = json.loads(map_src.read_text())
    trimmed = {"schema_version": full.get("schema_version", "0.1"),
               "project": full.get("project", {}), "groups": []}
    (WORK / "research_map_trimmed.json").write_text(json.dumps(trimmed, indent=2, sort_keys=True) + "\n")

    sandboxes, scenarios = {}, {}
    for tooling, patched in (("canon", False), ("patch", True)):
        for tag, src in (("orig", REPO / "ledger/theorems.jsonl"), ("v7", p_v7), ("v8", p_v8)):
            key = f"{tooling}_{tag}"
            sandboxes[key] = build_sandbox(key, src, patched, WORK / "research_map_trimmed.json")
            scenarios[key] = run_scenario(WORK / key, tag)
            scenarios[key + "_rerun"] = run_scenario(WORK / key, tag + "_rerun")
    report["sandboxes"] = sandboxes
    report["scenarios"] = {k: {kk: vv for kk, vv in v.items() if kk != "violation_keys"}
                           for k, v in scenarios.items()}

    # C15: patch application is byte-faithful; canonical bytes untouched.
    for tooling in ("canon", "patch"):
        for tag in ("orig", "v7", "v8"):
            key = f"{tooling}_{tag}"
            sb = sandboxes[key]
            if tooling == "patch":
                checks.append(check(f"C15_{key}_patch_faithful", True,
                                    sb["patch_apply"]["apply_exit"] == 0 and
                                    sb["patch_apply"]["matches_declared_patched_bytes"] and
                                    sb["wiring"]["insertions"] == 1))
            else:
                checks.append(check(f"C15_{key}_canonical_lib_unchanged", sb["lib_before"], sb["lib_after"]))

    # C16: canonical runner is blind to the branch in all three variants.
    for tag in ("orig", "v7", "v8"):
        s = scenarios[f"canon_{tag}"]
        checks.append(check(f"C16_canon_{tag}_no_hf02_disjunction", 0, s["hf02_disjunction_n"]))
    checks.append(check("C17_canon_digest_stable_orig_v7",
                        scenarios["canon_orig"]["violations_digest"],
                        scenarios["canon_v7"]["violations_digest"]))
    checks.append(check("C18_canon_digest_stable_orig_v8",
                        scenarios["canon_orig"]["violations_digest"],
                        scenarios["canon_v8"]["violations_digest"]))

    # C19: patched runner reports exactly the expected rows per variant.
    checks.append(check("C19_patch_orig_rows", sorted(DISJ_ROWS),
                        scenarios["patch_orig"]["hf02_disjunction_rows"]))
    checks.append(check("C20_patch_v7_rows", [CONDITIONAL_ROW],
                        scenarios["patch_v7"]["hf02_disjunction_rows"]))
    checks.append(check("C21_patch_v8_rows", [], scenarios["patch_v8"]["hf02_disjunction_rows"]))

    # C22: the patch-attributable delta is exactly the HF-02 disjunction set.
    deltas = {}
    for tooling in ("canon", "patch"):
        for tag in ("v7", "v8"):
            deltas[f"{tooling}_{tag}"] = keyset_delta(scenarios[f"{tooling}_orig"], scenarios[f"{tooling}_{tag}"])
    report["deltas_vs_orig"] = deltas
    for tooling in ("canon", "patch"):
        for tag in ("v7", "v8"):
            adds = deltas[f"{tooling}_{tag}"]["added"]
            non_hf02 = [k for k in adds if not k.startswith('{"detail": "disjunction of class_ids')]
            checks.append(check(f"C22_{tooling}_{tag}_only_hf02_added", [], non_hf02))
    checks.append(check("C23_patch_orig_vs_canon_added_n", 8,
                        len(deltas["patch_orig"]["added"]) if "patch_orig" in deltas
                        else len(keyset_delta(scenarios["canon_orig"], scenarios["patch_orig"])["added"])))
    report["deltas_vs_orig"]["patch_orig"] = keyset_delta(scenarios["canon_orig"], scenarios["patch_orig"])

    # C24: every violation removed by a repair variant is an HF-02 disjunction entry;
    # nothing else may disappear (the repair can only clear disjunctions).
    other_changes = []
    for key in ("canon_v7", "canon_v8", "patch_v7", "patch_v8"):
        for k in deltas[key]["removed"]:
            if not k.startswith('{"detail": "disjunction of class_ids'):
                other_changes.append({"scenario": key, "key": k})
    checks.append(check("C24_only_hf02_disjunctions_removed", [], other_changes))

    # C25: derived gate verdict trajectory.
    gate_traj = {k: {kk: vv for kk, vv in scenarios[k]["gates"].items()} for k in
                 ("canon_orig", "canon_v8", "patch_orig", "patch_v7", "patch_v8")}
    report["gate_trajectory"] = gate_traj

    # ------------------------------------------------------------ controls
    controls: list[dict] = []

    def control(name: str, expected, observed):
        controls.append(check(name, expected, observed))

    control("K1_mutation_control_dual_class_fires", 1,
            len(literal_disjunction([dict(rows_v8[[row_id(r) for r in rows_v8].index("D-004")],
                                          class_ids=["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"])])))
    syn = [{"theorem_id": "SYN-3", "class_ids": FROZEN4[:3]},
           {"theorem_id": "SYN-1", "class_ids": [FROZEN4[0]]},
           {"theorem_id": "SYN-0", "class_ids": []},
           {"theorem_id": "SYN-X", "class_ids": ["AF-NOT-FROZEN"]},
           {"theorem_id": "SYN-MIX", "class_ids": [FROZEN4[0], "AF-NOT-FROZEN"]}]
    control("K2_synthetic_only_multi_frozen_fires", ["SYN-3"], literal_disjunction(syn))
    control("K3_v7_v8_delta_is_conditional_only", [CONDITIONAL_ROW],
            sorted(set(variants["v8"]["changed_rows"]) - set(variants["v7"]["changed_rows"])))
    idx8 = {row_id(r): r for r in rows_v8}
    control("K4_T526_v8_rebound", ([], ["AF-SCC-C2-VAC-GEN"]),
            (idx8[CONDITIONAL_ROW]["class_ids"], idx8[CONDITIONAL_ROW]["informs_classes"]))
    idx7 = {row_id(r): r for r in rows_v7}
    control("K5_T526_v7_unchanged", (sorted(["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]), None),
            (sorted(idx7[CONDITIONAL_ROW]["class_ids"]), idx7[CONDITIONAL_ROW].get("informs_classes")))
    # idempotency: applying the ops twice yields identical bytes
    rows_v8_twice, _ = build_variant(rows_v8, ops_v8)
    control("K6_idempotent_apply", sha256_bytes(raw_v8),
            sha256_bytes(("\n".join(dump_line(r) for r in rows_v8_twice) + "\n").encode("utf-8")))
    # determinism of runner scenarios
    control("K7_determinism_canon_v8", scenarios["canon_v8"]["violations_digest"],
            scenarios["canon_v8_rerun"]["violations_digest"])
    control("K8_determinism_patch_v8", scenarios["patch_v8"]["violations_digest"],
            scenarios["patch_v8_rerun"]["violations_digest"])
    control("K9_determinism_patch_v7", scenarios["patch_v7"]["violations_digest"],
            scenarios["patch_v7_rerun"]["violations_digest"])
    report["controls"] = controls

    # ------------------------------------------------------------ close
    ledger_after = sha256_file(REPO / "ledger/theorems.jsonl")
    checks.append(check("C26_canonical_ledger_unwritten", report["ledger_sha256_before"], ledger_after))
    checks.append(check("C27_canonical_audit_lib_unwritten", PINS["artifacts/audit/audit_lib.py"],
                        sha256_file(REPO / "artifacts/audit/audit_lib.py")))
    checks.append(check("C28_canonical_audit_run_unwritten", PINS["artifacts/audit/audit_run.py"],
                        sha256_file(REPO / "artifacts/audit/audit_run.py")))
    pins_end = check_pins()
    checks.append(check("C29_pins_stable_end", [], pins_end["moved"]))

    report["checks"] = checks
    report["summary"] = {
        "variants": {tag: {"sha256": variants[tag]["sha256"], "changed_rows": variants[tag]["changed_rows"],
                           "disjunction_after": variants[tag]["disjunction_ids_after"]}
                     for tag in ("v7", "v8")},
        "literal_hf02_counts": {k: len(v) for k, v in lit.items()},
        "patched_runner_hf02_counts": {tag: scenarios[f"patch_{tag}"]["hf02_disjunction_n"]
                                       for tag in ("orig", "v7", "v8")},
        "canonical_runner_hf02_counts": {tag: scenarios[f"canon_{tag}"]["hf02_disjunction_n"]
                                         for tag in ("orig", "v7", "v8")},
        "checks_pass": sum(1 for c in checks if c["pass"]), "checks_total": len(checks),
        "controls_pass": sum(1 for c in controls if c["pass"]), "controls_total": len(controls),
        "conditional_row": CONDITIONAL_ROW,
        "scope_dependency": ("V7/V8 are required only if the A0 detector-scope ruling covers ledger "
                             "records; if HF-02 is ruled claim-scoped (worker-077 reading), this "
                             "artifact is a reference proposal, not a required repair."),
        "authority": "worker-level; applied=false; no node status; no gate verdict",
    }
    ok = all(c["pass"] for c in checks) and all(c["pass"] for c in controls)
    report["verdict"] = "PASS" if ok else "FAIL"
    (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (ART / "report.json.sha256").write_text(sha256_file(ART / "report.json") + "  report.json\n")
    print(json.dumps(report["summary"], indent=2))
    print("checks:", report["summary"]["checks_pass"], "/", report["summary"]["checks_total"],
          "controls:", report["summary"]["controls_pass"], "/", report["summary"]["controls_total"],
          "verdict:", report["verdict"])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
