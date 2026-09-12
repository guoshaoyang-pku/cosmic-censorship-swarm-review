#!/usr/bin/env python3
"""W047-LFORM01-C2-ORDER-VERIFY-01 -- independent verification of L-FORM-01.

Claim under test (posted by astra-lead-formulation 2026-09-12T00:44:52+08:00,
blocker lead-form-20260912T004452-02):
    schemas/af_scc_c0_vacuum.yaml (pin 55d0a1ea9bda) line ~245 states
    "C2 is a strictly larger extension class" while the same file's line ~238
    declares E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2 (C2 is the
    SMALLER extension class).  The sibling F2a states the analogue row correctly.

What this instrument does:
  A. Pins: measure sha256 of every canonical/mirror input against frozen pins.
     Any mismatch -> exit 2 (moving target / drift); no verdict is produced.
  B. Containment order: parse `extension_class_containment` from
     schemas/af_scc_c0_vacuum.yaml, schemas/af_scc_c2_vacuum.yaml and the F0
     class-contract supplement, normalise to a largest-extension-set-first order
     O, and require all three to agree with the hand-derived order
     ["C0", "H2loc", "C1,1", "C2"].
  C. Size claims: every "X is a strictly larger|smaller extension class" claim
     must agree with O.  "X is a strictly larger extension class [than this
     class]" holds iff index(X) < index(this class) in O.
  D. Strength claims: every "S_X is stronger|weaker than S_Y" /
     "X-inextendibility is the stronger statement" / "implication runs X => Y"
     claim must agree with O.  S_X is stronger than S_Y iff index(X) < index(Y)
     (a larger extension set makes "no X extension" a stronger requirement).
  E. Analogue row: the forbidden transfer row `from: no proper future C2
     extension, to: this class` must be present in the C0 ledger.
  F. Mirror: artifacts/formulation/schemas/af_scc_c0_vacuum.yaml must be
     byte-identical to the canonical path.
  G. Taxonomy: research_map/formulation_taxonomy.yaml `meaning_C2` may call
     C^{1,1}/H^2_loc "strictly larger classes" only relative to C2 (correct);
     it must not claim C2 is larger than C0.

Controls (private copies under controls/, never a canonical path):
  C1 baseline reproduces the defect; C2 a one-token repair flips the size claim;
  C3 reversing the containment string flips the size verdict (order-sensitive,
  not keyword-sensitive); C4 deleting the analogue row is flagged; C5 the same
  inversion injected into F2a is flagged there; C6 a byte appended without pin
  update exits 2; C7 a fully consistent synthetic root reports the defect absent.

Exit codes: 0 = finding verified at pins (>=1 hard defect), 4 = no defect at
pins (finding falsified / repaired), 2 = pin drift, 3 = control failure,
5 = internal error.  Read-only outside its own directory.  Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TZ = timezone(timedelta(hours=8))

TASK_ID = "W047-LFORM01-C2-ORDER-VERIFY-01"
WORKER = "worker-047"

C0 = "schemas/af_scc_c0_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
SUP = "artifacts/formulation/formulation_taxonomy.yaml"
C0_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F2A_MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F1_MIRROR = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"

PINS = {
    C0: "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    F2A: "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    F1: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    TAX: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    SUP: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    C0_MIRROR: "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    F2A_MIRROR: "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    F1_MIRROR: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}

EXPECTED_ORDER = ["C0", "H2loc", "C1,1", "C2"]
CLASS_ALIASES = {
    "C0": "C0", "C2": "C2",
    "H2loc": "H2loc", "H2_loc": "H2loc", "H^2_loc": "H2loc", "H2LOC": "H2loc",
    "C1,1": "C1,1", "C^1,1": "C1,1", "C^{1,1}": "C1,1", "C11": "C1,1",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def norm_class(tok: str):
    if tok is None:
        return None
    t = tok.strip().strip('"').strip("'")
    t = t.replace("E_", "", 1) if t.startswith("E_") else t
    t = t.replace("\\", "").replace("{", "").replace("}", "").replace("^", "")
    t = t.replace(" ", "").strip(",.;:")
    return CLASS_ALIASES.get(t, CLASS_ALIASES.get(t.replace("_", ""), t))


def read_lines(root: str, rel: str):
    with open(os.path.join(root, rel), "r", encoding="utf-8") as fh:
        return fh.read().splitlines()


TOKEN_RE = re.compile(r"E_[A-Za-z0-9^{},_]+")


def parse_containment(root: str, rel: str, line_hint=None):
    """Return (order_largest_first, line_no, raw).  order is a list of canonical
    class names from largest extension set to smallest."""
    lines = read_lines(root, rel)
    candidates = []
    for i, line in enumerate(lines, 1):
        if "extension_class_containment:" in line:
            raw = line.split("extension_class_containment:", 1)[1].strip().strip('"')
            candidates.append((i, raw))
        elif "containment:" in line and "E_" in line and ("subset of" in line or "contains" in line):
            raw = line.split("containment:", 1)[1].strip().strip('"')
            candidates.append((i, raw))
    for i, raw in candidates:
            toks = [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(raw)]
            if len(toks) < 2:
                continue
            classes = [norm_class(t[0]) for t in toks]
            relations = []
            for a, b in zip(toks, toks[1:]):
                between = raw[a[2]:b[1]]
                if "contains" in between:
                    relations.append(">")
                elif "subset of" in between:
                    relations.append("<")
                else:
                    relations.append("?")
            if "?" in relations:
                continue
            order = [classes[0]]
            for rel, cls in zip(relations, classes[1:]):
                if rel == ">":
                    order.append(cls)
                else:  # "<": next token is a superset -> prepend
                    order.insert(0, cls)
            # collapse duplicates preserving order (insert may duplicate)
            seen, uniq = set(), []
            for c in order:
                if c not in seen:
                    seen.add(c)
                    uniq.append(c)
            return uniq, i, raw
    return None, None, None


SIZE_RE = re.compile(
    r"(?P<cls>[A-Za-z0-9^{},_\\]+)\s+is\s+a\s+strictly\s+(?P<dir>larger|smaller)\s+extension\s+class"
)
STRONG_RE = re.compile(
    r"(?P<a>[A-Za-z0-9^{},_\\]+)\s*-\s*inextendibility\s+is\s+(?:the\s+)?(?P<dir>stronger|weaker)\s+than\s+(?:the\s+)?(?P<b>[A-Za-z0-9^{},_\\]+)"
)
IMPLIES_RE = re.compile(
    r"(?:implication|containment)\s+runs\s+(?P<a>[A-Za-z0-9^{},_\\]+)\s*=>\s*(?P<b>[A-Za-z0-9^{},_\\]+)\s+only"
)
ENTAILS_CHAIN_RE = re.compile(
    r"(?P<a>[A-Za-z0-9^{},_\\]+)\s*-\s*inextendibility\s+entails\s+(?P<b>[A-Za-z0-9^{},_\\]+)\s*-\s*inextendibility\s+entails\s+(?P<c>[A-Za-z0-9^{},_\\]+)\s*-\s*inextendibility"
)
STATEMENT_STRONGER_RE = re.compile(
    r"(?P<a>[A-Za-z0-9^{},_\\]+)\s*-\s*inextendibility\s+is\s+the\s+(?P<dir>stronger|weaker)\s+statement"
)


def idx(order, cls):
    c = norm_class(cls)
    return order.index(c) if c in order else None


def check_order_and_claims(root: str, order: list):
    """Family B/C/D: every size/strength/entailment claim vs the derived order."""
    checks, seen_claims = [], []
    targets = {
        C0: "AF-SCC-C0-VAC-GEN",
        F2A: "AF-SCC-C2-VAC-GEN",
        F1: "AF-WCC-VAC-GEN",
        SUP: None,
        TAX: None,
    }
    for rel in (C0, F2A, F1, SUP, TAX):
        lines = read_lines(root, rel)
        for i, line in enumerate(lines, 1):
            for m in SIZE_RE.finditer(line):
                cls = norm_class(m.group("cls"))
                this = "C0" if rel in (C0, C0_MIRROR) else ("C2" if rel in (F2A, F2A_MIRROR) else None)
                if cls is None or this is None:
                    continue
                want = "larger" if idx(order, cls) < idx(order, this) else "smaller"
                ok = (m.group("dir") == want)
                checks.append({
                    "id": "SIZE_CLAIM", "file": rel, "line": i,
                    "text": line.strip()[:240], "class": cls, "target_class": this,
                    "claimed": m.group("dir"), "required_by_order": want,
                    "status": "PASS" if ok else "FAIL", "severity": "hard" if not ok else "info",
                })
                seen_claims.append(("SIZE_CLAIM", rel, i))
            for m in STRONG_RE.finditer(line):
                a, b, d = norm_class(m.group("a")), norm_class(m.group("b")), m.group("dir")
                if a is None or b is None or idx(order, a) is None or idx(order, b) is None:
                    continue
                want = "stronger" if idx(order, a) < idx(order, b) else "weaker"
                ok = (d == want)
                checks.append({
                    "id": "STRENGTH_CLAIM", "file": rel, "line": i,
                    "text": line.strip()[:240], "a": a, "b": b,
                    "claimed": d, "required_by_order": want,
                    "status": "PASS" if ok else "FAIL", "severity": "hard" if not ok else "info",
                })
                seen_claims.append(("STRENGTH_CLAIM", rel, i))
            for m in IMPLIES_RE.finditer(line):
                a, b = norm_class(m.group("a")), norm_class(m.group("b"))
                if a is None or b is None or idx(order, a) is None or idx(order, b) is None:
                    continue
                ok = idx(order, a) < idx(order, b)  # X => Y iff S_X stronger
                checks.append({
                    "id": "IMPLICATION_DIRECTION", "file": rel, "line": i,
                    "text": line.strip()[:240], "a": a, "b": b,
                    "required_by_order": f"S_{a} stronger than S_{b}",
                    "status": "PASS" if ok else "FAIL", "severity": "hard" if not ok else "info",
                })
                seen_claims.append(("IMPLICATION_DIRECTION", rel, i))
            for m in ENTAILS_CHAIN_RE.finditer(line.replace("*", "")):
                a, b, c = (norm_class(m.group(k)) for k in ("a", "b", "c"))
                if None in (a, b, c) or any(idx(order, x) is None for x in (a, b, c)):
                    continue
                ok = idx(order, a) < idx(order, b) < idx(order, c)
                checks.append({
                    "id": "ENTAILMENT_CHAIN", "file": rel, "line": i,
                    "text": line.strip()[:240], "chain": [a, b, c],
                    "status": "PASS" if ok else "FAIL", "severity": "hard" if not ok else "info",
                })
                seen_claims.append(("ENTAILMENT_CHAIN", rel, i))
            for m in STATEMENT_STRONGER_RE.finditer(line):
                a, d = norm_class(m.group("a")), m.group("dir")
                this = "C0" if rel in (C0, C0_MIRROR) else ("C2" if rel in (F2A, F2A_MIRROR) else None)
                # "X-inextendibility is the stronger statement" compares X with
                # the other class named on the same line if there is one,
                # otherwise with this file's own class.
                others = [norm_class(t) for t in re.findall(r"[A-Za-z0-9^{},_\\]+", line)
                          if norm_class(t) in EXPECTED_ORDER and norm_class(t) != a]
                target = others[0] if others else this
                if a is None or target is None or idx(order, a) is None or idx(order, target) is None:
                    continue
                ok = (idx(order, a) < idx(order, target)) if d == "stronger" else (idx(order, a) > idx(order, target))
                checks.append({
                    "id": "STATEMENT_STRENGTH", "file": rel, "line": i,
                    "text": line.strip()[:240], "a": a, "target_class": target,
                    "claimed": d, "required_by_order": "stronger" if idx(order, a) < idx(order, target) else "weaker",
                    "status": "PASS" if ok else "FAIL", "severity": "hard" if not ok else "info",
                })
                seen_claims.append(("STATEMENT_STRENGTH", rel, i))
    return checks, seen_claims


def check_analogue_row(root: str):
    lines = read_lines(root, C0)
    hit = None
    for i, line in enumerate(lines, 1):
        if "no proper future C2 extension" in line and "to: \"this class\"" in line:
            hit = i
            break
    if hit is None:
        return [{
            "id": "ANALOGUE_ROW_PRESENT", "file": C0, "line": None,
            "status": "FAIL", "severity": "hard",
            "detail": "no forbidden_transfers row from 'no proper future C2 extension' to 'this class'",
        }]
    return [{
        "id": "ANALOGUE_ROW_PRESENT", "file": C0, "line": hit,
        "status": "PASS", "severity": "info",
        "detail": "forbidden-transfer row present; its reason is checked by SIZE_CLAIM/STRENGTH_CLAIM",
    }]


def check_mirror(root: str):
    out = []
    for canon, mirror in ((C0, C0_MIRROR), (F2A, F2A_MIRROR), (F1, F1_MIRROR)):
        a = sha256_file(os.path.join(root, canon))
        b = sha256_file(os.path.join(root, mirror))
        out.append({
            "id": "MIRROR_EQUAL", "canonical": canon, "mirror": mirror,
            "status": "PASS" if a == b else "FAIL",
            "severity": "info" if a == b else "hard",
            "canonical_sha256": a, "mirror_sha256": b,
        })
    return out


def check_taxonomy(root: str, order: list):
    lines = read_lines(root, TAX)
    checks = []
    for i, line in enumerate(lines, 1):
        if "meaning_C2" in line and "strictly larger classes" in line:
            names = [norm_class(x) for x in re.findall(r"C\^\{1,1\}|H\^2_loc|H2_loc|C\^1,1", line)]
            good = (all(n in ("C1,1", "H2loc") for n in names) and "C2" in line
                    and all(idx(order, n) is not None and idx(order, n) < idx(order, "C2")
                            for n in names))
            checks.append({
                "id": "TAXONOMY_RELATIVE_SIZE", "file": TAX, "line": i,
                "named_larger_than_C2": names,
                "status": "PASS" if good else "FAIL",
                "severity": "info" if good else "hard",
                "detail": "'strictly larger classes' must refer to C^{1,1}/H^2_loc relative to C2, not C2 relative to C0",
            })
    return checks


def run_checks(root: str, pin_check: bool = True, expected_order=None):
    if expected_order is None:
        expected_order = EXPECTED_ORDER
    checks = []
    pins_measured = {}
    drift = []
    for rel, pin in PINS.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            drift.append({"path": rel, "error": "missing"})
            continue
        m = sha256_file(p)
        pins_measured[rel] = m
        if m != pin:
            drift.append({"path": rel, "expected": pin, "measured": m})
    if drift and pin_check:
        return {"status": "DRIFT", "pins": pins_measured, "drift": drift, "checks": []}

    orders = {}
    for rel in (C0, F2A, SUP):
        order, line_no, raw = parse_containment(root, rel)
        orders[rel] = {"order": order, "line": line_no, "raw": raw}
        if order is None:
            checks.append({"id": "CONTAINMENT_PARSE", "file": rel, "line": line_no,
                           "status": "FAIL", "severity": "hard", "detail": "chain not parsed", "raw": raw})
        elif order != expected_order:
            checks.append({"id": "CONTAINMENT_ORDER", "file": rel, "line": line_no,
                           "status": "FAIL", "severity": "hard",
                           "expected": expected_order, "parsed": order, "raw": raw})
        else:
            checks.append({"id": "CONTAINMENT_ORDER", "file": rel, "line": line_no,
                           "status": "PASS", "severity": "info",
                           "expected": expected_order, "parsed": order})
    if any(c["id"] == "CONTAINMENT_ORDER" and c["status"] == "FAIL" for c in checks):
        return {"status": "UNPARSED", "pins": pins_measured, "orders": orders, "checks": checks}
    order = orders[C0]["order"]

    claim_checks, seen = check_order_and_claims(root, order)
    checks.extend(claim_checks)
    checks.extend(check_analogue_row(root))
    checks.extend(check_mirror(root))
    checks.extend(check_taxonomy(root, expected_order))
    hard = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "hard"]
    return {
        "status": "DEFECT" if hard else "CLEAN",
        "pins": pins_measured, "orders": orders,
        "checks": checks, "hard_defects": len(hard),
        "claim_count": len(seen),
    }


# ---------------------------------------------------------------- controls ---

MUT_SIZE = ("C2 is a strictly larger extension class",
            "C2 is a strictly smaller extension class")
MUT_CONTAIN = (
    'extension_class_containment: "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2;',
    'extension_class_containment: "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0;',
)
MUT_CONTAIN_F2A = (
    '"E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0',
    '"E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2',
)
MUT_CONTAIN_SUP = (
    'containment: "extension sets are nested E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0,',
    'containment: "extension sets are nested E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2,',
)
MUT_F2A = (
    '"the converse containment is false; C2-inextendibility is weaker than H2_loc-inextendibility"',
    '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"',
)
ROW_MARK = 'from: "no proper future C2 extension", to: "this class"'


def copy_root(root: str, dst: str, rels):
    for rel in rels:
        s = os.path.join(root, rel)
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)


def mutate(path: str, old: str, new: str):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if old not in text:
        raise RuntimeError("mutation anchor not found: %r" % old[:60])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))


def controls(root: str):
    """Run the instrument on private mutated roots; return list of control rows."""
    ctrl_root = os.path.join(HERE, "controls")
    os.makedirs(ctrl_root, exist_ok=True)
    base = tempfile.mkdtemp(prefix="w047-ctrl-", dir=ctrl_root)
    results = []
    script = os.path.abspath(__file__)
    rels = list(PINS.keys())

    def run(rootdir, extra=(), pin_check=True):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        outdir = os.path.join(rootdir, "_out")
        os.makedirs(outdir, exist_ok=True)
        args = [sys.executable, script, "--root", rootdir, "--out-dir", outdir, "--json-stdout"]
        if not pin_check:
            args.append("--no-pin-check")
        args.extend(extra)
        proc = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
        try:
            payload = json.loads(proc.stdout)
        except Exception:
            payload = {}
        return proc.returncode, payload

    def mk(name):
        d = os.path.join(base, name)
        copy_root(root, d, rels)
        return d

    mirror_of = {C0: C0_MIRROR, F2A: F2A_MIRROR, F1: F1_MIRROR}

    def mutate_both(rootdir, rel, old, new):
        """Apply the same repair/mutation to the canonical path and its mirror,
        as a real revision would have to."""
        mutate(os.path.join(rootdir, rel), old, new)
        if rel in mirror_of:
            mutate(os.path.join(rootdir, mirror_of[rel]), old, new)

    def fails(payload, file=None, cid=None):
        return [c for c in payload.get("checks", [])
                if c.get("status") == "FAIL"
                and (file is None or c.get("file") == file)
                and (cid is None or c.get("id") == cid)]

    # C1 baseline on the canonical root (pin check active): finding reproduced.
    rc, payload = run(root, pin_check=True)
    results.append({"control": "C1_baseline", "expect": "exit 0 and exactly 1 SIZE_CLAIM FAIL in C0",
                    "exit": rc, "hard_defects": payload.get("hard_defects"),
                    "size_fail": len(fails(payload, C0, "SIZE_CLAIM")),
                    "pass": rc == 0 and payload.get("hard_defects") == 1
                            and len(fails(payload, C0, "SIZE_CLAIM")) == 1})

    # C2 one-token repair -> defect absent.
    d = mk("C2_size_repair")
    try:
        mutate_both(d, C0, *MUT_SIZE)
        rc, payload = run(d, pin_check=False)
        results.append({"control": "C2_size_repair", "expect": "exit 4, 0 SIZE_CLAIM FAIL",
                        "exit": rc, "size_fail": len(fails(payload, None, "SIZE_CLAIM")),
                        "pass": rc == 4 and len(fails(payload, None, "SIZE_CLAIM")) == 0})
    except RuntimeError as exc:
        results.append({"control": "C2_size_repair", "expect": "exit 4", "exit": None, "error": str(exc), "pass": False})

    # C3 order reversal in all three files: the same sentence becomes consistent
    # with its own file's declared order; other claims flip to FAIL.
    d = mk("C3_order_reversed")
    try:
        mutate_both(d, C0, *MUT_CONTAIN)
        mutate_both(d, F2A, *MUT_CONTAIN_F2A)
        mutate(os.path.join(d, SUP), *MUT_CONTAIN_SUP)
        rc, payload = run(d, extra=["--expected-order", "C2;C1,1;H2loc;C0"], pin_check=False)
        other_fail = [c for c in fails(payload, C0) if c.get("id") != "SIZE_CLAIM"]
        results.append({"control": "C3_order_reversed",
                        "expect": "C0 SIZE_CLAIM consistent under reversed order; >=1 other C0 claim FAIL",
                        "exit": rc, "c0_size_fail": len(fails(payload, C0, "SIZE_CLAIM")),
                        "other_c0_fail": len(other_fail),
                        "pass": rc != 3 and len(fails(payload, C0, "SIZE_CLAIM")) == 0 and len(other_fail) >= 1})
    except RuntimeError as exc:
        results.append({"control": "C3_order_reversed", "expect": "order-sensitive", "exit": None, "error": str(exc), "pass": False})

    # C4 analogue row removed -> flagged, never a silent pass.
    d = mk("C4_row_removed")
    try:
        for rel in (C0, C0_MIRROR):
            path = os.path.join(d, rel)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            line = [ln for ln in text.splitlines() if ROW_MARK in ln][0]
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace(line + "\n", ""))
        rc, payload = run(d, pin_check=False)
        results.append({"control": "C4_row_removed", "expect": "ANALOGUE_ROW_PRESENT FAIL",
                        "exit": rc, "row_fail": len(fails(payload, None, "ANALOGUE_ROW_PRESENT")),
                        "pass": len(fails(payload, None, "ANALOGUE_ROW_PRESENT")) == 1})
    except (RuntimeError, IndexError) as exc:
        results.append({"control": "C4_row_removed", "expect": "row flagged", "exit": None, "error": str(exc), "pass": False})

    # C5 same inversion injected into the F2a sibling -> flagged there.
    d = mk("C5_f2a_inversion")
    try:
        mutate_both(d, F2A, *MUT_F2A)
        rc, payload = run(d, pin_check=False)
        results.append({"control": "C5_f2a_inversion", "expect": "F2a claim FAIL",
                        "exit": rc, "f2a_fail": len(fails(payload, F2A)),
                        "pass": len(fails(payload, F2A)) >= 1})
    except RuntimeError as exc:
        results.append({"control": "C5_f2a_inversion", "expect": "F2a claim flagged", "exit": None, "error": str(exc), "pass": False})

    # C6 byte drift without a pin update -> exit 2, no verdict.
    d = mk("C6_drift")
    with open(os.path.join(d, C0), "a", encoding="utf-8") as fh:
        fh.write("\n# drift\n")
    rc, payload = run(d, pin_check=True)
    results.append({"control": "C6_drift", "expect": "exit 2",
                    "exit": rc, "status": payload.get("status"), "pass": rc == 2})

    # C7 repaired root reports the defect absent (clean).
    d = mk("C7_repaired")
    try:
        mutate_both(d, C0, *MUT_SIZE)
        rc, payload = run(d, pin_check=False)
        results.append({"control": "C7_repaired", "expect": "exit 4 clean",
                        "exit": rc, "hard_defects": payload.get("hard_defects"),
                        "pass": rc == 4 and payload.get("hard_defects") == 0})
    except RuntimeError as exc:
        results.append({"control": "C7_repaired", "expect": "exit 4", "exit": None, "error": str(exc), "pass": False})

    # C8 false-positive control: a correct paraphrase that avoids the flagged
    # phrase must NOT be reported as a defect.
    d = mk("C8_paraphrase_ok")
    try:
        mutate_both(d, C0, MUT_SIZE[0],
                    "the converse containment is false; C2-inextendibility is weaker than this class's conclusion")
        rc, payload = run(d, pin_check=False)
        results.append({"control": "C8_paraphrase_ok", "expect": "exit 4 clean (no false positive)",
                        "exit": rc, "hard_defects": payload.get("hard_defects"),
                        "pass": rc == 4 and payload.get("hard_defects") == 0})
    except RuntimeError as exc:
        results.append({"control": "C8_paraphrase_ok", "expect": "exit 4", "exit": None, "error": str(exc), "pass": False})

    with open(os.path.join(base, "control_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    return base, results


def main():
    argv = sys.argv[1:]
    root = DEFAULT_ROOT
    if "--root" in argv:
        root = os.path.abspath(argv[argv.index("--root") + 1])
    out_dir = HERE
    if "--out-dir" in argv:
        out_dir = os.path.abspath(argv[argv.index("--out-dir") + 1])
    json_stdout = "--json-stdout" in argv
    run_controls = "--controls" in argv
    pin_check = "--no-pin-check" not in argv
    expected_order = EXPECTED_ORDER
    if "--expected-order" in argv:
        raw_order = argv[argv.index("--expected-order") + 1]
        parts = raw_order.split(";") if ";" in raw_order else raw_order.split(",")
        expected_order = [norm_class(x) for x in parts]

    result = run_checks(root, pin_check=pin_check, expected_order=expected_order)
    result["task_id"] = TASK_ID
    result["worker"] = WORKER
    result["root"] = root
    result["at"] = now_iso()
    result["pin_check"] = pin_check
    result["expected_order"] = expected_order

    exit_code = 5
    if result["status"] == "DRIFT":
        exit_code = 2
    elif result["status"] == "UNPARSED":
        exit_code = 5
    elif result["hard_defects"] >= 1:
        exit_code = 0
    else:
        exit_code = 4

    if run_controls:
        ctrl_dir, ctrl_rows = controls(root)
        result["controls_dir"] = ctrl_dir
        result["controls"] = ctrl_rows
        if not all(c["pass"] for c in ctrl_rows):
            exit_code = 3
        result["controls_pass"] = all(c["pass"] for c in ctrl_rows)

    result["exit_code"] = exit_code
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)

    raw_dir = os.path.join(out_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "run_stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(result, indent=1, sort_keys=True))
        fh.write("\n")

    if json_stdout:
        print(json.dumps(result, sort_keys=True))
    else:
        print("status=%s exit=%d hard_defects=%s report=%s"
              % (result["status"], exit_code, result.get("hard_defects"), out))
        for c in result.get("checks", []):
            if c["status"] == "FAIL":
                print("  FAIL %-24s %s:%s  %s" % (c["id"], c.get("file"), c.get("line"),
                                                  str(c.get("text") or c.get("detail"))[:160]))
        if run_controls:
            for c in result.get("controls", []):
                print("  control %-18s pass=%s exit=%s" % (c["control"], c["pass"], c.get("exit")))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
