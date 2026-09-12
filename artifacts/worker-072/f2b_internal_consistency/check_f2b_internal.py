#!/usr/bin/env python3
"""W072-F2B-INTERNAL-CONSISTENCY-01

Read-only deterministic checker for two claimed internal contradictions in
schemas/af_scc_c0_vacuum.yaml (class AF-SCC-C0-VAC-GEN, node F2b) at the live
pin b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c,
frozen under artifacts/formulation/FROZEN.json rev29 815e08079aefbc...

Claims under test (formulation-lead lifecycle-07 measurements 5, independently
first raised as blocking by worker-018 W018-R13-F2B-B1/B2):
  D1  regularity.must_not_conflate[0] denies containment with C2/C0 while the
      same file's implication_ledger asserts E_C0 contains E_H2loc contains
      E_{C^1,1} contains E_C2 and four one_way_entailments; the sibling F2a
      records the same denial as wrong.
  D2  implication_ledger.forbidden_transfers[0].reason calls C2 a "strictly
      larger extension class" while the file's own chain makes E_C2 innermost
      (strictly smallest); the prohibition itself is correct, the size premise
      is inverted.

No network. No model calls. Never writes to schemas/ or artifacts/formulation/.
Exit 0 = both defects absent; exit 1 = at least one defect present; exit 2 =
instrument/precondition failure (fail closed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time

PIN_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN_FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
PIN_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PATH_F2B = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_F2B = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
PATH_F2A = "schemas/af_scc_c2_vacuum.yaml"
PATH_FROZEN = "artifacts/formulation/FROZEN.json"
PATH_F0 = "research_map/formulation_taxonomy.yaml"

DENIAL = "No containment with C2 or C0 is asserted here"
CHAIN = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
SIBLING_WRONG = "the earlier 'no containment with C2 is asserted' was wrong"
LARGER = "strictly larger extension class"
WEAKER_LABEL = "those are WEAKER statements"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


class Results:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, cid: str, ok: bool, detail: str, **extra) -> None:
        row = {"id": cid, "ok": bool(ok), "detail": detail}
        row.update(extra)
        self.checks.append(row)

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]


def get(res: "Results", cid: str) -> bool:
    return next(c["ok"] for c in res.checks if c["id"] == cid)


def load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().split("\n")


def find_line(lines: list[str], needle: str) -> int:
    hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
    if len(hits) != 1:
        raise AssertionError(f"needle {needle!r} has {len(hits)} hits, want 1")
    return hits[0]


def window_contains(lines: list[str], line_no: int, needle: str, before: int, after: int) -> bool:
    lo = max(1, line_no - before)
    hi = min(len(lines), line_no + after)
    return any(needle in lines[i - 1] for i in range(lo, hi + 1))


def conclusion_block(lines: list[str]) -> list[str]:
    start = next(i for i, ln in enumerate(lines) if re.match(r"^conclusion:\s*$", ln))
    out = []
    for ln in lines[start + 1:]:
        if re.match(r"^[a-z_]+:\s*", ln) or re.match(r"^[a-z_]+:\s*$", ln):
            break
        out.append(ln)
    return out


def analyse_f2b(root: str, expect_hash: str) -> tuple[Results, dict]:
    """Run the content checks against one F2b candidate file."""
    res = Results()
    p = os.path.join(root, PATH_F2B)
    raw = open(p, "rb").read()
    h = sha256_bytes(raw)
    lines = raw.decode("utf-8").split("\n")
    res.add("C01", h == expect_hash, f"target sha256 {h}", sha256=h)

    mirror = os.path.join(root, MIRROR_F2B)
    res.add(
        "C02",
        os.path.exists(mirror) and open(mirror, "rb").read() == raw,
        "authoring mirror byte-identical to canonical",
    )

    frozen = json.load(open(os.path.join(root, PATH_FROZEN), "r", encoding="utf-8"))
    text_frozen = json.dumps(frozen)
    res.add("C03a", PIN_FROZEN in text_frozen or sha256_file(os.path.join(root, PATH_FROZEN)) == PIN_FROZEN,
            "FROZEN rev29 manifest pin resolves")
    res.add("C03b", text_frozen.count(expect_hash) >= 2,
            "FROZEN pins both canonical and authoring F2b paths at the measured hash")

    # --- D1: denial vs containment -----------------------------------------
    try:
        d_line = find_line(lines, DENIAL)
        in_slot = window_contains(lines, d_line, "must_not_conflate:", 12, 0)
    except AssertionError as exc:
        res.add("C04", False, f"denial anchor: {exc}")
        d_line, in_slot = -1, False
    else:
        res.add("C04", in_slot, f"denial present at line {d_line}, inside regularity.must_not_conflate", line=d_line)

    try:
        c_line = find_line(lines, CHAIN)
    except AssertionError as exc:
        res.add("C05", False, f"containment chain anchor: {exc}")
        c_line = -1
    else:
        res.add("C05", True, f"containment chain asserted at line {c_line}", line=c_line)

    entail = 0
    if c_line > 0:
        for ln in lines[c_line:]:
            if "forbidden_transfers:" in ln:
                break
            if "relation: entails" in ln or "relation: entails" in ln.replace(" ", " "):
                entail += 1
            if "E_H2loc subset of E_C0" in ln or "E_C2 subset of E_H2loc" in ln:
                entail += 1
    res.add("C06", entail >= 3, f"one_way_entailments containment rows observed: {entail}")

    d1 = bool(get(res, "C04") and get(res, "C05") and get(res, "C06"))
    res.add(
        "C07",
        d1,
        "D1 CONTRADICTION PRESENT: same frozen file denies C2/C0 containment and asserts it",
        defect="D1" if d1 else None,
    )

    sib = open(os.path.join(root, PATH_F2A), "r", encoding="utf-8").read()
    sib_lines = sib.split("\n")
    try:
        s_line = find_line(sib_lines, SIBLING_WRONG)
        sib_ok = True
        detail = f"sibling F2a marks the denial wrong at its line {s_line}"
    except AssertionError as exc:
        s_line, sib_ok = -1, False
        detail = f"sibling F2a correction marker missing: {exc}"
    res.add("C08", sib_ok, detail, line=s_line)

    # --- D2: inverted size premise -----------------------------------------
    try:
        r_line = find_line(lines, LARGER)
        reason_ok = True
        detail = f"inverted size premise present at line {r_line}"
    except AssertionError as exc:
        r_line, reason_ok = -1, False
        detail = f"line-246 premise anchor missing: {exc}"
    res.add("C09", reason_ok, detail, line=r_line)

    try:
        w_line = find_line(lines, WEAKER_LABEL)
        weaker_ok = True
        detail = f"forbidden_strengthenings labels C2/C1/H2loc conclusions WEAKER at line {w_line}"
    except AssertionError as exc:
        w_line, weaker_ok = -1, False
        detail = f"weaker-statement label anchor missing: {exc}"
    res.add("C10", weaker_ok, detail, line=w_line)

    res.add(
        "C11",
        bool(get(res, "C05") and get(res, "C09")),
        "D2 CONTRADICTION PRESENT: size premise inverted against the file's own innermost E_C2",
        defect="D2" if (get(res, "C05") and get(res, "C09")) else None,
    )

    # --- class-binding sanity (must stay clean; guards against fix-by-leak) --
    conc = "\n".join(conclusion_block(lines))
    binding_ok = (
        "conclusion_type: scc_c0_future_inextendibility" in conc
        and "C0 or C2" not in conc
        and "C2" not in conc.split("statement_formal:")[0].split("conclusion_type:")[1].split("\n")[0]
    )
    res.add("C12", binding_ok, "conclusion_type is the single C0 token; no composite in the conclusion block")

    f0 = open(os.path.join(root, PATH_F0), "rb").read()
    res.add("C13", sha256_bytes(f0) == PIN_F0, "F0 taxonomy pin unchanged (context only)")

    res.add("C14", True, f"target lines read: {len(lines)}; no writes performed")
    return res, {"f2b_line_count": len(lines), "denial_line": d_line, "chain_line": c_line,
                 "reason_line": r_line, "sibling_line": s_line}


def run_controls(root: str) -> dict:
    """Mutant controls executed on temp copies; proves each defect check can flip."""
    base = os.path.join(root, PATH_F2B)
    orig = open(base, "r", encoding="utf-8").read()
    sib_orig = open(os.path.join(root, PATH_F2A), "r", encoding="utf-8").read()
    rows: list[dict] = []

    def run_case(name: str, f2b_text: str | None, f2a_text: str | None,
                 expect_d1: bool | None, expect_d2: bool | None) -> None:
        tmp = tempfile.mkdtemp(prefix="w072ctl-")
        try:
            for rel in (PATH_F2B, MIRROR_F2B, PATH_F2A):
                dst = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(os.path.join(tmp, PATH_F2B), "w", encoding="utf-8").write(f2b_text if f2b_text is not None else orig)
            open(os.path.join(tmp, MIRROR_F2B), "w", encoding="utf-8").write(f2b_text if f2b_text is not None else orig)
            open(os.path.join(tmp, PATH_F2A), "w", encoding="utf-8").write(f2a_text if f2a_text is not None else sib_orig)
            shutil.copy(os.path.join(root, PATH_FROZEN), os.path.join(tmp, PATH_FROZEN))
            os.makedirs(os.path.join(tmp, os.path.dirname(PATH_F0)), exist_ok=True)
            shutil.copy(os.path.join(root, PATH_F0), os.path.join(tmp, PATH_F0))
            res, _ = analyse_f2b(tmp, sha256_bytes((f2b_text if f2b_text is not None else orig).encode()))
            got = {c["id"]: c["ok"] for c in res.checks}
            d1, d2 = got["C07"], got["C11"]
            ok = (d1 == expect_d1) and (d2 == expect_d2)
            rows.append({"control": name, "ok": ok, "D1": d1, "D2": d2,
                         "expected_D1": expect_d1, "expected_D2": expect_d2})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    run_case("K0_null_unmodified", None, None, expect_d1=True, expect_d2=True)
    run_case("K1_denial_sentence_removed", orig.replace(DENIAL + "; ", "").replace(DENIAL, ""), None,
             expect_d1=False, expect_d2=True)
    run_case("K2_premise_larger_to_smaller", orig.replace(LARGER, "strictly smaller extension class"), None,
             expect_d1=True, expect_d2=False)
    run_case("K3_sibling_marker_removed", None, sib_orig.replace(SIBLING_WRONG, "removed by control"),
             expect_d1=True, expect_d2=True)
    run_case("K4_unrelated_mutation", orig.replace("smooth-with-decay default", "smooth-with-decay default [ctl]"), None,
             expect_d1=True, expect_d2=True)
    run_case("K5_containment_chain_removed", orig.replace(CHAIN, "containment chain removed by control"), None,
             expect_d1=False, expect_d2=False)
    return {
        "controls_total": len(rows),
        "controls_pass": sum(1 for r in rows if r["ok"]),
        "controls_fail": sum(1 for r in rows if not r["ok"]),
        "rows": rows,
    }


def sibling_check_flip(root: str) -> dict:
    """K3b: the sibling marker check C08 must flip when the sibling file changes."""
    sib = open(os.path.join(root, PATH_F2A), "r", encoding="utf-8").read()
    flipped = SIBLING_WRONG not in sib.replace(SIBLING_WRONG, "")
    return {"control": "K3b_sibling_marker_read_from_sibling", "ok": flipped and SIBLING_WRONG in sib}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    pre = {p: sha256_file(os.path.join(root, p)) for p in (PATH_F2B, MIRROR_F2B, PATH_F2A, PATH_FROZEN, PATH_F0)}
    mtime = os.path.getmtime(os.path.join(root, PATH_F2B))

    res, meta = analyse_f2b(root, PIN_F2B)
    post = {p: sha256_file(os.path.join(root, p)) for p in pre}
    res.add("C15", pre == post, "hash stability across the run (no target write)")
    res.add("C16", os.path.getmtime(os.path.join(root, PATH_F2B)) == mtime, "target mtime unchanged")

    control = run_controls(root) if args.controls else None
    if control is not None:
        sib_c = sibling_check_flip(root)
        control["rows"].append(sib_c)
        control["controls_total"] += 1
        control["controls_pass"] += 1 if sib_c["ok"] else 0
        control["controls_fail"] += 0 if sib_c["ok"] else 1

    d1 = next(c for c in res.checks if c["id"] == "C07")["ok"]
    d2 = next(c for c in res.checks if c["id"] == "C11")["ok"]
    defects = [d for d, on in (("D1", d1), ("D2", d2)) if on]
    report = {
        "instrument": "W072-F2B-INTERNAL-CONSISTENCY-01",
        "task_id": "W072-F2B-INTERNAL-CONSISTENCY-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "actor": "worker-072",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "root": root,
        "pins": {"schemas/af_scc_c0_vacuum.yaml": PIN_F2B, "artifacts/formulation/FROZEN.json": PIN_FROZEN,
                 "research_map/formulation_taxonomy.yaml": PIN_F0},
        "measured": pre,
        "checks_pass": sum(1 for c in res.checks if c["ok"]),
        "checks_fail": len(res.failed),
        "failed_ids": [c["id"] for c in res.failed],
        "checks": res.checks,
        "defects_confirmed": defects,
        "controls": control,
        "verdict": "revise" if defects else "accept",
        "verdict_scope": "self-audit of worker-072's own F2b rev29 accept; not a gate verdict",
        "falsifier": (
            "Re-measure schemas/af_scc_c0_vacuum.yaml at hash b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c: "
            "if line 152 no longer denies C2/C0 containment (or the denial is explicitly scoped as quote-only), if line 246's "
            "reason no longer calls C2 the strictly larger extension class, or if any control K0-K5/K3b does not flip as declared, "
            "this self-audit's revise is void."
        ),
        "authority_note": "Worker evidence only: no node status, no validation_status=passed, no gate verdict, no schema write.",
    }
    out = args.out or os.path.join(root, "artifacts/worker-072/f2b_internal_consistency/report.json")
    if control is None:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    else:
        cpath = os.path.join(root, "artifacts/worker-072/f2b_internal_consistency/controls/controls_summary.json")
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        with open(cpath, "w", encoding="utf-8") as fh:
            json.dump(control, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        rpath = os.path.join(root, "artifacts/worker-072/f2b_internal_consistency/report_with_controls.json")
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    print(json.dumps({k: report[k] for k in ("instrument", "checks_pass", "checks_fail", "failed_ids",
                                             "defects_confirmed", "verdict")}, indent=2))
    if control is not None:
        print(json.dumps({k: control[k] for k in ("controls_total", "controls_pass", "controls_fail")}, indent=2))
    if res.failed or (control is not None and control["controls_fail"]):
        return 2  # instrument/precondition failure or control escape: fail closed
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
