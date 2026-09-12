#!/usr/bin/env python3
"""W027-F2A-HASHBIND-CENSUS-01 -- independent census of hash-binding comparison
sites on the G-FORM / F2a closure toolchain, plus sandbox validation of a minimal
B7 repair patch.

Question
--------
The F2a/F1/F2b HF-B1 closure (worker-05) rests on `check_class_binding_drift.py`
returning "all hard checks pass". Its B7 check binds the consistency-evidence
record to the schema's declared revision with a substring test
(`declared in blob or declared[:16] in blob`). Two blind spots were reported by
worker-027 in W027-F2A-HB1-INDEP-01 (W027-HB1-F2/F3). This instrument:

  (1) statically censuses every comparison site in the pinned FROZEN rev29
      toolchain (plus the two worker-05 verifier files) that compares
      hash-named operands, and classifies each site EXACT / PREFIX / SUBSTRING;
  (2) dynamically probes the B7 site with four sandbox trees at the live pins
      (prefix-preserving forged record; supplement drift; stale declared hash;
      unbound live record) and its HF-B1 candidate control;
  (3) validates a minimal four-hunk B7/B8 patch (B7 becomes exact full-string
      canonical binding; B8 adds exact full-string supplement binding; the
      author's fixture writer is updated so its selftest matches the strengthened
      contract) against the author's own selftest and the same four sandboxes,
      and verifies the diff applies with `patch -p1`.

Read-only with respect to all canonical artifacts: the checker is executed on
private sandbox roots under scratch/; nothing outside artifacts/worker-027/ is
written. Exit 0 measurement complete, 2 input drift (void), 3 unexpected
measurement result, 4 patch does not apply.

Falsifier (pre-registered)
--------------------------
FALSIFIED if (a) any pinned input drifts T0->T1 (void, exit 2); (b) the census
classifies the B7 site as anything other than SUBSTRING, or finds no EXACT site
in verify_frozen.py; (c) the unpatched checker does NOT return verdict=pass for
the prefix-forged evidence record, or does NOT return verdict=pass for the
supplement-drift tree (blind spots not reproduced); (d) the unpatched checker
does not reject the stale-declared tree; (e) the patched checker fails the
author's selftest, fails the HF-B1 candidate tree, or does not reject the
prefix-forged / supplement-drift / stale-declared trees; (f) the diff does not
apply with `patch -p1` or does not reproduce the patched bytes; (g) any
pre-registered control misses its expectation; (h) any pin fails to resolve.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SCRATCH = HERE.parent / "scratch"
PATCHED_DIR = HERE.parent / "patched"
REPORT = HERE.parent / "report.json"

SCHEMA_VERSION = "0.1"
TASK_ID = "W027-F2A-HASHBIND-CENSUS-01"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
NODE_ID = "F2a"
GATE = "G-FORM"

DRIFT_CHECKER = "artifacts/worker-05/verify/check_class_binding_drift.py"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
CANON_REL = "research_map/formulation_taxonomy.yaml"
SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
CANDIDATE_REL = "artifacts/worker-05/verify/taxonomy_consistency_hashbound.json"

# Hard pins, measured 2026-09-12 ~01:17 +08:00 at FROZEN rev29 815e08079aef.
PINS = {
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    EVIDENCE_REL: "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    CANDIDATE_REL: "4c4803c540a1e8947deacba8f2302712e49a84a5264051b6e42d4df19f2719ce",
    DRIFT_CHECKER: "bde270d3886a1a27f669698567328c669f12067503c065658a36294226acac3c",
    "artifacts/worker-05/verify/gen_hashbound_consistency_evidence.py": "3df4abfc7c49763b86e5b017633d46f3a0a3aa6f32ae8b646b634f63b9dd98b3",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/f1_falsifier_tests.jsonl": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
}

# All 14 tools listed in FROZEN rev29, pinned to the rev29 manifest values.
TOOL_PINS = {
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "artifacts/formulation/tools/check_variant_deltas.py": "d33d8f57f4dd244e5beb7a981103e6a113a9673c1d831f99b24960b6e61753c4",
    "artifacts/formulation/tools/close_findings_rev27.py": "0234cd3cbda491ae353e4972dda8a8fe95ae39d2fe2b4968639dc2fcad845371",
    "artifacts/formulation/tools/evidence_binding_repair_rev29.py": "2f6c4f7d8f30b04d97f87e623c03ca3b45e913e31d133474c1abcd75b9bb2965",
    "artifacts/formulation/tools/make_key_manifest.py": "449dd621ccf6756624e2536c86ef4eb0f109ce35ced3129b66e7850f980bcb6e",
    "artifacts/formulation/tools/measure_semantic_escape.py": "c6e4f9ccce7f68e472338c72dab6d3b84cb85b7ccfa3dd69416b384cdea11272",
    "artifacts/formulation/tools/monitor_cycle.py": "8b44659f756499149b691869164e5c331d3d0711bf38215eb0c5249db1f62c5e",
    "artifacts/formulation/tools/regenerate_frozen.py": "57dbc69e389db4ed0fd31903f2c6db6279065f7d371ea08359c4d404ce56c49b",
    "artifacts/formulation/tools/run_acceptance.py": "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/formulation/tools/run_gate_tests.py": "78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa",
    "artifacts/formulation/tools/variant_rebase_rev29.py": "e9521823b8bbeb92cb7342c003de270b30beff42cda0f332dca2e37f6a6bdb22",
    "artifacts/formulation/tools/verify_frozen.py": "0a65b657e4988bcbfa2a91072c9615cd9c317fd81f7cf9e37b636c9c0bd663d5",
}
PINS.update(TOOL_PINS)

# A FROZEN rev29 file observed to move during the measurement window (01:21:56).
# Excluded from the pinned set: it carries no hash-comparison site on the B7 path,
# and a moving pin cannot anchor a measurement. Recorded as an observation instead.
OBSERVED_UNPINNED = {
    "path": "artifacts/formulation/tools/check_variant_registry.py",
    "frozen_rev29_sha256": "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
}

CENSUS_FILES = sorted(TOOL_PINS) + [DRIFT_CHECKER,
                                    "artifacts/worker-05/verify/gen_hashbound_consistency_evidence.py"]

HASHISH = re.compile(r"(?i)(sha|hash|digest|checksum)")
HASHISH_NAME = re.compile(r"(?i)(sha256|_sha$|^sha|sha_|hash|digest|checksum)")
DIGEST_CALL = re.compile(r"\b(sha256_file|sha256_bytes|sha_bytes|hashlib|hexdigest|sha)\s*\(|\bdigest\s*\(")
DIGEST_RHS = re.compile(r"\b(sha256_file|sha256_bytes|sha_bytes|hashlib|hexdigest)\b|\bdigest\s*\(|\bsha\s*\(")
HASH_GET = re.compile(r"""(?i)(\.get\(\s*["'][^"']*(sha256|sha|hash|digest|checksum)[^"']*["']|\[\s*["'][^"']*(sha256|sha|hash|digest|checksum)[^"']*["']\s*\])""")
TRUNC = re.compile(r"\[:\s*\d+\]")

PATCH_HUNKS = [
    (
        "  B7 consistency_evidence is hash-bound to the declared revision [hard]\n"
        "     (B7 fails when the evidence records no sha256 / declared hash at all,\n"
        "      so it cannot discharge the artifact's own refresh rule)",
        "  B7 consistency_evidence binds the declared revision by exact full string [hard]\n"
        "  B8 consistency_evidence binds the measured supplement revision full-string [hard]\n"
        "     (B7/B8 fail when the evidence records no full sha256 for that input, so it\n"
        "      cannot discharge the artifact's own refresh rule)"
    ),
    (
        'HARD_CHECKS = ("B1", "B3", "B4", "B6", "B7")',
        'HARD_CHECKS = ("B1", "B3", "B4", "B6", "B7", "B8")'
    ),
    (
        "        except Exception as exc:  # noqa: BLE001\n"
        "            ev_doc = None\n"
        '            add("B7", False, f"evidence unparseable: {exc}", True)\n'
        "        else:\n"
        "            blob = json.dumps(ev_doc)\n"
        "            bound = bool(declared) and (declared in blob or declared[:16] in blob)\n"
        '            add("B7", bound,\n'
        '                f"evidence_sha256={ev_sha} records_declared_revision={bound} "\n'
        '                f"(unbound evidence cannot discharge the f0_binding refresh rule)",\n'
        "                True)\n"
        "    else:\n"
        '        add("B7", False, "no evidence file to bind", True)',
        "        except Exception as exc:  # noqa: BLE001\n"
        "            ev_doc = None\n"
        '            add("B7", False, f"evidence unparseable: {exc}", True)\n'
        '            add("B8", False, f"evidence unparseable: {exc}", True)\n'
        "        else:\n"
        "            blob = json.dumps(ev_doc)\n"
        "            bound = bool(declared) and (declared in blob)\n"
        '            add("B7", bound,\n'
        '                f"evidence_sha256={ev_sha} full_canonical_revision={bound} "\n'
        '                f"(exact full-string match required)",\n'
        "                True)\n"
        "            supp_bound = bool(supp_sha) and (supp_sha in blob)\n"
        '            add("B8", supp_bound,\n'
        '                f"measured_supplement={supp_sha} recorded={supp_bound}", True)\n'
        "    else:\n"
        '        add("B7", False, "no evidence file to bind", True)\n'
        '        add("B8", False, "no evidence file to bind", True)'
    ),
    (
        '    ev.write_text(json.dumps({"declared_sha256": declared if bound else None}),\n'
        '                  encoding="utf-8")',
        "    supp_sha = sha256_file(root / SUPPLEMENT_F0)\n"
        '    ev.write_text(json.dumps({"declared_sha256": declared if bound else None,\n'
        '                              "input_sha256": {SUPPLEMENT_F0: supp_sha}}),\n'
        '                  encoding="utf-8")'
    ),
]

FALSIFIER = (
    "FALSIFIED if (a) any pinned input drifts T0->T1 (void, exit 2); (b) the census classifies the B7 site "
    "as anything other than SUBSTRING, or finds no EXACT site in verify_frozen.py; (c) the unpatched checker "
    "does NOT return verdict=pass for the prefix-forged evidence record, or does NOT return verdict=pass for "
    "the supplement-drift tree; (d) the unpatched checker does not reject the stale-declared tree; (e) the "
    "patched checker fails the author's selftest, fails the HF-B1 candidate tree, or does not reject the "
    "prefix-forged / supplement-drift / stale-declared trees; (f) the diff does not apply with `patch -p1` or "
    "does not reproduce the patched bytes; (g) any pre-registered control misses its expectation; (h) any pin "
    "fails to resolve."
)

NON_CLAIMS = [
    "not a gate verdict; worker events cannot set status=done, validation_status=passed, or any gate verdict",
    "does not publish the HF-B1 candidate or the proposed patch; canonical writes and re-pins are lead decisions",
    "does not adjudicate the F2b rev30 direction dispute or any schema content",
    "does not claim the substring blind spot affected any past verdict; it shows the checker would accept a "
    "record that does not bind the declared revision, which is an instrument property",
    "author-level independence only: deepseek-flash-05 authored check_class_binding_drift.py; worker-027 did not",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def check_pins(repo: Path, pins: dict) -> list:
    drift = []
    for rel, expected in sorted(pins.items()):
        p = repo / rel
        if not p.is_file():
            drift.append({"path": rel, "expected": expected, "measured": "MISSING"})
            continue
        got = sha256_file(p)
        if got != expected:
            drift.append({"path": rel, "expected": expected, "measured": got})
    return drift


# ---------------------------------------------------------------- static census
def _src(src: str, node: ast.AST) -> str:
    try:
        seg = ast.get_source_segment(src, node)
    except Exception:  # noqa: BLE001
        seg = None
    return seg or ""


def _is_hash_value(src: str, node: ast.AST, tainted: set) -> bool:
    """Strict operand test: 64-hex literal, direct digest computation, hash-key
    access, a hash-named identifier, or a name bound to any of those."""
    seg = _src(src, node)
    if re.search(r"\b[0-9a-f]{64}\b", seg):
        return True
    if DIGEST_CALL.search(seg) or HASH_GET.search(seg):
        return True
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and (sub.id in tainted or HASHISH_NAME.search(sub.id)):
            return True
        if isinstance(sub, ast.Attribute) and (sub.attr in tainted or HASHISH_NAME.search(sub.attr)):
            return True
    return False


def _walk_no_funcs(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        yield child
        yield from _walk_no_funcs(child)


def _tainted_names(scope: ast.AST, src: str) -> set:
    """Names bound to a digest computation, a hash-key access, or a hash-ish name.
    Walks only the given scope's own statements, not nested function bodies."""
    t = set()
    for node in _walk_no_funcs(scope):
        if isinstance(node, ast.Assign):
            val = _src(src, node.value)
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and (HASHISH_NAME.search(tgt.id) or DIGEST_RHS.search(val)
                                                  or HASH_GET.search(val)
                                                  or re.search(r"\b[0-9a-f]{64}\b", val)):
                    t.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            val = _src(src, node.value) if node.value is not None else ""
            if HASHISH_NAME.search(node.target.id) or DIGEST_RHS.search(val) or HASH_GET.search(val):
                t.add(node.target.id)
        elif isinstance(node, ast.arg) and HASHISH_NAME.search(node.arg):
            t.add(node.arg)
    return t


def _functions(tree: ast.AST) -> list:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node.lineno, node.end_lineno or node.lineno, node.name))
    return out


def _enclosing(funcs: list, line: int):
    best = None
    for lo, hi, name in funcs:
        if lo <= line <= hi and (best is None or lo >= best[0]):
            best = (lo, hi, name)
    return best[2] if best else "<module>"


def _func_source(lines: list, funcs: list, line: int) -> str:
    for lo, hi, _ in funcs:
        if lo <= line <= hi:
            return "\n".join(lines[lo - 1:hi])
    return ""


def _fail_surface(func_src: str) -> bool:
    return any(tok in func_src for tok in
               ("hard_failures", "fail(", "sys.exit", "SystemExit", "raise ", "return False"))


def census_source(name: str, src: str) -> dict:
    """Classify comparison sites with hash-named operands. Deterministic, no I/O."""
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return {"file": name, "parse_error": f"{exc.__class__.__name__}: {exc}", "sites": []}
    lines = src.splitlines()
    funcs = _functions(tree)
    module_taint = _tainted_names(tree, src)
    taint_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            taint_ranges.append((node.lineno, node.end_lineno or node.lineno,
                                 module_taint | _tainted_names(node, src)))

    def tainted_at(line: int) -> set:
        t = set(module_taint)
        for lo, hi, names in taint_ranges:
            if lo <= line <= hi:
                t |= names
        return t

    sites = []
    for node in ast.walk(tree):
        rec = None
        if isinstance(node, ast.Compare):
            tainted = tainted_at(node.lineno)
            operands = [node.left] + list(node.comparators)
            hashed = [o for o in operands if _is_hash_value(src, o, tainted)]
            op = node.ops[0]
            if hashed and isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq)):
                seg = _src(src, node)
                if isinstance(op, (ast.In, ast.NotIn)):
                    kind = "SUBSTRING"
                else:
                    sliced = any(isinstance(o, ast.Subscript) and isinstance(o.slice, ast.Slice)
                                 and o.slice.upper is not None for o in hashed)
                    kind = "PREFIX" if (sliced or TRUNC.search(seg)) else "EXACT"
                rec = {"kind": kind, "code": seg.strip()}
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                node.func.attr in {"startswith", "endswith", "find", "index", "__contains__"} and \
                _is_hash_value(src, node.func.value, tainted_at(node.lineno)):
            rec = {"kind": "SUBSTRING_METHOD", "code": _src(src, node).strip()}
        if rec is None:
            continue
        func_src = _func_source(lines, funcs, node.lineno)
        rec.update({
            "file": name,
            "lineno": node.lineno,
            "function": _enclosing(funcs, node.lineno),
            "fail_surface": _fail_surface(func_src),
        })
        sites.append(rec)
    sites.sort(key=lambda r: (r["file"], r["lineno"], r["kind"]))
    return {"file": name, "bytes": len(src.encode("utf-8")),
            "sha256": sha256_bytes(src.encode("utf-8")), "sites": sites}


def run_census(repo: Path) -> dict:
    records = []
    for rel in CENSUS_FILES:
        p = repo / rel
        if not p.is_file():
            records.append({"file": rel, "parse_error": "MISSING", "sites": []})
            continue
        records.append(census_source(rel, p.read_text(encoding="utf-8")))
    counts = {}
    for r in records:
        for s in r["sites"]:
            counts[s["kind"]] = counts.get(s["kind"], 0) + 1
    return {"files": records, "counts": counts,
            "site_count": sum(len(r["sites"]) for r in records)}


# ------------------------------------------------------------------- sandboxes
REAL = {}


def build_sandbox(name: str, *, canon: bytes, supp: bytes, schemas: dict, evidence: bytes) -> Path:
    root = SCRATCH / name
    if root.exists():
        shutil.rmtree(root)
    (root / "research_map").mkdir(parents=True)
    (root / "artifacts/formulation/evidence").mkdir(parents=True)
    (root / "schemas").mkdir(parents=True)
    (root / CANON_REL).write_bytes(canon)
    (root / SUPP_REL).write_bytes(supp)
    for sname, data in schemas.items():
        (root / "schemas" / sname).write_bytes(data)
    (root / EVIDENCE_REL).write_bytes(evidence)
    return root


def run_checker(checker: Path, root: Path, selftest: bool = False) -> dict:
    cmd = [sys.executable, str(checker), "--selftest"] if selftest else \
        [sys.executable, str(checker), "--root", str(root)]
    cp = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    out = {}
    text = cp.stdout.strip()
    if text.startswith("{"):
        try:
            out = json.loads(text)
        except Exception:  # noqa: BLE001
            out = {}
    classes = {}
    for rec in out.get("schemas", []):
        b7 = next((c for c in rec.get("checks", []) if c.get("check") == "B7"), {})
        classes[rec.get("class_id")] = {
            "verdict": rec.get("verdict"),
            "b7": b7.get("status"),
            "hard_failures": rec.get("hard_failures", []),
        }
    return {"exit": cp.returncode, "verdict": out.get("verdict"),
            "classes": classes, "selftest_out": text if selftest else "",
            "stderr_tail": cp.stderr.strip()[-200:]}


def payload_marker(evidence: bytes, key: str):
    try:
        d = json.loads(evidence.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return d.get(key)


# ------------------------------------------------------------------ main flow
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    PATCHED_DIR.mkdir(parents=True, exist_ok=True)

    drift = check_pins(repo, PINS)
    if drift:
        report = {"schema_version": SCHEMA_VERSION, "task_id": TASK_ID, "worker": "worker-027",
                  "verdict": "INPUT_DRIFT", "pin_drift": drift, "falsifier": FALSIFIER,
                  "created_at": datetime.now().astimezone().isoformat()}
        REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"verdict": "INPUT_DRIFT", "drift": drift}, indent=1))
        return 2

    obs_path = repo / OBSERVED_UNPINNED["path"]
    obs_live = sha256_file(obs_path) if obs_path.is_file() else "MISSING"
    observed_drift = dict(OBSERVED_UNPINNED)
    observed_drift.update({
        "observed_sha256": obs_live,
        "observed_mtime": datetime.fromtimestamp(obs_path.stat().st_mtime).astimezone().isoformat()
        if obs_path.is_file() else None,
        "drifted_at_measurement": obs_live != OBSERVED_UNPINNED["frozen_rev29_sha256"],
        "excluded_from_pinned_set": True,
        "note": "not adjudicated here; FROZEN.json was not re-pinned during the window",
    })

    for rel in (CANON_REL, SUPP_REL, DRIFT_CHECKER, CANDIDATE_REL):
        REAL[rel] = (repo / rel).read_bytes()
    schemas = {n: (repo / "schemas" / n).read_bytes()
               for n in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")}
    live_evidence = (repo / EVIDENCE_REL).read_bytes()
    candidate = (repo / CANDIDATE_REL).read_bytes()

    declared = None
    m = re.search(rb'declared_f0_sha256:\s*"?([0-9a-f]{64})', schemas["af_scc_c2_vacuum.yaml"])
    declared = m.group(1).decode() if m else None

    census = run_census(repo)

    # --- patch construction (exact-anchor hunks, applied sequentially)
    checker_src = REAL[DRIFT_CHECKER].decode("utf-8")
    patched_src = checker_src
    hunk_anchors = []
    for i, (old, new) in enumerate(PATCH_HUNKS, 1):
        cnt = patched_src.count(old)
        hunk_anchors.append({"hunk": i, "anchor_occurrences": cnt})
        if cnt == 1:
            patched_src = patched_src.replace(old, new)
    patch_ok = all(h["anchor_occurrences"] == 1 for h in hunk_anchors)
    patched_path = PATCHED_DIR / "check_class_binding_drift.patched.py"
    if patch_ok:
        patched_path.write_text(patched_src, encoding="utf-8")
        diff = "".join(difflib.unified_diff(
            checker_src.splitlines(keepends=True), patched_src.splitlines(keepends=True),
            fromfile="a/" + DRIFT_CHECKER, tofile="b/" + DRIFT_CHECKER, n=3))
        (HERE.parent / "proposed_patch_B7B8.diff").write_text(diff, encoding="utf-8")
        # dry-run + real apply in an isolated tree
        apply_root = SCRATCH / "patch_apply"
        if apply_root.exists():
            shutil.rmtree(apply_root)
        (apply_root / Path(DRIFT_CHECKER).parent).mkdir(parents=True)
        target = apply_root / DRIFT_CHECKER
        target.write_bytes(REAL[DRIFT_CHECKER])
        dry = subprocess.run(["patch", "-p1", "--dry-run", "-i",
                              str(HERE.parent / "proposed_patch_B7B8.diff")],
                             cwd=str(apply_root), capture_output=True, text=True)
        real = subprocess.run(["patch", "-p1", "-i", str(HERE.parent / "proposed_patch_B7B8.diff")],
                              cwd=str(apply_root), capture_output=True, text=True)
        applied_sha = sha256_file(target)
    else:
        dry = real = None
        applied_sha = "PATCH_ANCHOR_NOT_FOUND"

    patch_rec = {
        "anchor_found": patch_ok,
        "hunks": hunk_anchors,
        "diff_sha256": sha256_file(HERE.parent / "proposed_patch_B7B8.diff")
        if (HERE.parent / "proposed_patch_B7B8.diff").is_file() else None,
        "patched_sha256": sha256_file(patched_path) if patched_path.is_file() else None,
        "dry_run_exit": None if dry is None else dry.returncode,
        "apply_exit": None if real is None else real.returncode,
        "applied_sha256": applied_sha,
        "applies_cleanly": bool(dry is not None and dry.returncode == 0 and real is not None
                                and real.returncode == 0 and applied_sha == sha256_file(patched_path)),
        "patched_selftest": None,
    }

    # --- probe trees
    supp_drift = REAL[SUPP_REL] + b"\n# post-freeze drift probe (sandbox only)\n"
    canon_stale = REAL[CANON_REL] + b"\n# stale-declared probe (sandbox only)\n"
    prefix_forged = json.dumps({"declared_sha256": declared[:16] + "f" * 48}).encode()
    unbound_live = live_evidence

    trees = {
        "T_candidate": dict(canon=REAL[CANON_REL], supp=REAL[SUPP_REL], schemas=schemas, evidence=candidate),
        "T_prefix_forged": dict(canon=REAL[CANON_REL], supp=REAL[SUPP_REL], schemas=schemas, evidence=prefix_forged),
        "T_supp_drift": dict(canon=REAL[CANON_REL], supp=supp_drift, schemas=schemas, evidence=candidate),
        "T_stale_declared": dict(canon=canon_stale, supp=REAL[SUPP_REL], schemas=schemas, evidence=candidate),
        "T_unbound_live": dict(canon=REAL[CANON_REL], supp=REAL[SUPP_REL], schemas=schemas, evidence=unbound_live),
    }
    roots = {k: build_sandbox(k, **v) for k, v in trees.items()}

    probes = {}
    checks = []

    def expect(cid, ok, detail):
        checks.append({"check": cid, "status": "pass" if ok else "fail", "detail": detail})

    # live baseline
    live_unpatched = run_checker(repo / DRIFT_CHECKER, repo)
    live_patched = run_checker(patched_path, repo) if patch_ok else None
    probes["live_unpatched"] = live_unpatched
    probes["live_patched"] = live_patched
    expect("P0_live_unpatched_exit1",
           live_unpatched["exit"] == 1 and live_unpatched["verdict"] == "fail"
           and all(c["b7"] == "fail" for c in live_unpatched["classes"].values()),
           f"exit={live_unpatched['exit']} verdict={live_unpatched['verdict']} b7={[c['b7'] for c in live_unpatched['classes'].values()]}")

    pre = {
        "T_candidate": ("pass", "pass"),
        "T_prefix_forged": ("pass", "fail"),
        "T_supp_drift": ("pass", "fail"),
        "T_stale_declared": ("fail", "fail"),
        "T_unbound_live": ("fail", "fail"),
    }
    for name, (exp_un, exp_pa) in pre.items():
        root = roots[name]
        un = run_checker(repo / DRIFT_CHECKER, root)
        pa = run_checker(patched_path, root) if patch_ok else None
        probes[name] = {"unpatched": un, "patched": pa,
                        "expected_unpatched": exp_un, "expected_patched": exp_pa}
        expect(f"{name}_unpatched={exp_un}",
               un["verdict"] == exp_un and un["exit"] == (0 if exp_un == "pass" else 1),
               f"exit={un['exit']} verdict={un['verdict']} b7={[c['b7'] for c in un['classes'].values()]}")
        if patch_ok:
            expect(f"{name}_patched={exp_pa}",
                   pa["verdict"] == exp_pa and pa["exit"] == (0 if exp_pa == "pass" else 1),
                   f"exit={pa['exit']} verdict={pa['verdict']} b7={[c['b7'] for c in pa['classes'].values()]}")

    if patch_ok:
        st_un = run_checker(repo / DRIFT_CHECKER, repo, selftest=True)
        st_pa = run_checker(patched_path, repo, selftest=True)
        patch_rec["patched_selftest"] = st_pa["exit"]
        probes["selftest_unpatched"] = st_un
        probes["selftest_patched"] = st_pa
        expect("selftest_unpatched_pass", st_un["exit"] == 0, st_un["selftest_out"][:120])
        expect("selftest_patched_pass", st_pa["exit"] == 0, st_pa["selftest_out"][:120])
        expect("patch_applies_cleanly", patch_rec["applies_cleanly"],
               f"dry={patch_rec['dry_run_exit']} apply={patch_rec['apply_exit']} sha={applied_sha[:12]}")
    else:
        expect("patch_anchor_found", False, "a patch hunk anchor was not found exactly once")

    # instrument controls
    b7_hits = [s for r in census["files"] for s in r["sites"]
               if s["file"] == DRIFT_CHECKER and "declared[:16]" in s["code"]]
    expect("K1_census_B7_SUBSTRING",
           bool(b7_hits) and all(s["kind"] == "SUBSTRING" for s in b7_hits),
           f"hits={[(s['lineno'], s['kind']) for s in b7_hits]}")
    exact_vf = [s for r in census["files"] for s in r["sites"]
                if s["file"] == "artifacts/formulation/tools/verify_frozen.py" and s["kind"] == "EXACT"]
    expect("K2_census_verify_frozen_EXACT", bool(exact_vf),
           f"exact_sites={[s['lineno'] for s in exact_vf]}")
    probe_src = ("def f(declared_sha256, blob):\n"
                 "    a = declared_sha256 == blob\n"
                 "    b = declared_sha256[:16] == blob[:16]\n"
                 "    c = declared_sha256 in blob\n")
    probe = census_source("<selftest>", probe_src)
    kinds = sorted(s["kind"] for s in probe["sites"])
    expect("K3_census_classifier_selftest",
           kinds == ["EXACT", "PREFIX", "SUBSTRING"], f"kinds={kinds}")
    bad = census_source("<bad>", "def f(:\n")
    expect("K4_census_fail_closed", "parse_error" in bad and not bad["sites"], str(bad.get("parse_error"))[:80])
    fake_pins = dict(PINS)
    fake_pins[DRIFT_CHECKER] = "0" * 64
    expect("K5_pin_drift_detected", bool(check_pins(repo, fake_pins)),
           f"drift_entries={len(check_pins(repo, fake_pins))}")
    expect("K6_pin_check_clean", not drift, f"drift={len(drift)}")
    expect("K7_repeat_hash_stable",
           sha256_file(repo / DRIFT_CHECKER) == PINS[DRIFT_CHECKER], "checker hash stable across run")

    findings = [
        {"id": "W027-HBC-F1", "severity": "major", "status": "CONFIRMED" if
         probes["T_prefix_forged"]["unpatched"]["verdict"] == "pass" else "REFUTED",
         "statement": "check_class_binding_drift.py B7 accepts an evidence record that contains only the "
                      "16-hex prefix of the declared revision; a prefix-preserving forged record passes all "
                      "hard checks (blind spot reproduced in T_prefix_forged)"},
        {"id": "W027-HBC-F2", "severity": "major", "status": "CONFIRMED" if
         probes["T_supp_drift"]["unpatched"]["verdict"] == "pass" else "REFUTED",
         "statement": "no hard check binds the class-contract supplement input; supplement drift after the "
                      "evidence was generated still yields verdict=pass (T_supp_drift)"},
        {"id": "W027-HBC-F3", "severity": "info", "status": "CENSUS",
         "statement": f"census of {census['site_count']} hash-comparison sites in {len(census['files'])} pinned "
                      f"toolchain files: counts={census['counts']}"},
        {"id": "W027-HBC-F4", "severity": "info", "status": "VALIDATED" if
         patch_rec["applies_cleanly"] and patch_rec["patched_selftest"] == 0 else "NOT_VALIDATED",
         "statement": "minimal four-hunk B7/B8 patch (B7 exact full-string canonical binding; new hard B8 "
                      "exact full-string supplement binding; author fixture writer updated so the strengthened "
                      "selftest is coherent) applies cleanly with patch -p1, passes the patched selftest, keeps "
                      "the HF-B1 candidate passing, and rejects the prefix-forged / supplement-drift / "
                      "stale-declared trees (unpatched keeps the stale-declared rejection only)"},
        {"id": "W027-HBC-F5", "severity": "info", "status":
         "OBSERVED" if observed_drift["drifted_at_measurement"] else "NOT_REPRODUCED",
         "statement": f"FROZEN rev29 declares {observed_drift['path']} = "
                      f"{observed_drift['frozen_rev29_sha256'][:12]}; live bytes measured "
                      f"{observed_drift['observed_sha256'][:12]} at {observed_drift['observed_mtime']} "
                      f"with FROZEN.json unchanged at 815e08079aef (excluded from the pinned set)"},
    ]

    controls_passed = sum(1 for c in checks if c["status"] == "pass")
    all_ok = controls_passed == len(checks)
    by_id = {f["id"]: f for f in findings}
    success = (all_ok and by_id["W027-HBC-F1"]["status"] == "CONFIRMED"
               and by_id["W027-HBC-F2"]["status"] == "CONFIRMED"
               and by_id["W027-HBC-F3"]["status"] == "CENSUS"
               and by_id["W027-HBC-F4"]["status"] == "VALIDATED")
    verdict = "CENSUS_AND_PATCH_VALIDATED" if success else \
        ("MEASUREMENT_MISS" if not all_ok else "FINDINGS_INCOMPLETE")

    report = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "worker": "worker-027",
        "agent_slot": "worker-027",
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": datetime.now().astimezone().isoformat(),
        "verdict": verdict,
        "pins": PINS,
        "pin_drift": drift,
        "observed_drift": observed_drift,
        "census": census,
        "patch": patch_rec,
        "probes": probes,
        "checks": checks,
        "controls_passed": controls_passed,
        "controls_total": len(checks),
        "findings": findings,
        "falsifier": FALSIFIER,
        "non_claims": NON_CLAIMS,
        "reproduce": "python3 artifacts/worker-027/hashbind_census/verify_hashbind_census.py",
    }
    REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": verdict, "controls": f"{controls_passed}/{len(checks)}",
        "counts": census["counts"], "site_count": census["site_count"],
        "patch_applies": patch_rec["applies_cleanly"],
        "unpatched": {k: v["unpatched"]["verdict"] for k, v in probes.items() if isinstance(v, dict) and "unpatched" in v},
        "patched": {k: v["patched"]["verdict"] for k, v in probes.items() if isinstance(v, dict) and v.get("patched")},
    }, indent=1))
    if not success:
        for c in checks:
            if c["status"] != "pass":
                print("MISS:", c["check"], "--", c["detail"], file=sys.stderr)
        for f in findings:
            print("FINDING:", f["id"], f["status"], file=sys.stderr)
    return 0 if success else 3


if __name__ == "__main__":
    sys.exit(main())
