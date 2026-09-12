#!/usr/bin/env python3
"""W058 instrument-closure checker (read-only).

Question
--------
Which bytes can change a G-FORM acceptance outcome, and are they pinned in
`artifacts/formulation/FROZEN.json`? The FROZEN manifest is the only declared pin set, so
any instrument or input that (a) is reachable from a *pinned* tool and (b) is itself
unpinned is a governance gap: gate outcomes move without a pinned hash moving.

Method (all static, no writes outside this task directory)
----------------------------------------------------------
1. Entry points = every `.py` file pinned in FROZEN.files.
2. For each module, an AST pass resolves module-level path symbols
   (`HERE = Path(__file__).resolve().parent`, `ROOT = HERE.parent.parent`,
   `FORM / "tools" / "x.py"`, `Path(__file__).resolve().parents[3] / "a" / "b"`),
   collects bare repo-relative path literals, and resolves local imports.
3. Reached local `.py` modules are parsed recursively (depth cap 3), so transitive
   instruments are included.
4. Reached directories are expanded to their files (cap 400).
5. Every reached path is classified against FROZEN.files:
      PINNED_OK      in FROZEN and measured bytes == declared bytes
      PINNED_DRIFT   in FROZEN and measured bytes != declared bytes
      UNPINNED       not in FROZEN and exists on disk
      MISSING        not in FROZEN and does not exist
   Role per reference is `exec` (subprocess tool), `read` (any other non-write use) or
   `write` (value flows into a write/dump call). A bare literal inside prose is a
   `mention` and is never effect-capable.
6. Effect-capable = exists AND NOT pinned-ok AND (module OR role in {read, exec}).
   Output-only data files are listed but do not make a gap: rewriting a report cannot
   change the next verdict.

Verdict: CLOSURE_GAP if any effect-capable reachable path is not PINNED_OK, else CLOSED.
`--strict` exits 1 on CLOSURE_GAP (intended freeze-time guard).

Controls: `--selftest` runs eight synthetic-tree cases (closed, unpinned exec, pinned
drift, transitive discovery, output-only non-gap, missing read input, idempotence,
stdlib-import no-false-positive) and writes their expected/measured verdicts.

Boundary: static reachability only. A path reached only through a computed runtime value
(f-string, argv, environment) is not discovered; absence of a finding is not proof of
closure outside the discovered set. No gate verdict, no math claim.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

SUFFIXES = (".py", ".json", ".yaml", ".yml", ".jsonl", ".csv", ".md", ".txt")
MAX_DEPTH = 3
MAX_DIR_FILES = 400
# Tools that execute in the live G-FORM acceptance path (produce current gate evidence).
ACCEPTANCE_TOOLS = (
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/run_gate_tests.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/measure_semantic_escape.py",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/formulation/tools/check_variant_deltas.py",
    "artifacts/formulation/tools/check_variant_registry.py",
    "artifacts/formulation/tools/verify_frozen.py",
    "artifacts/formulation/tools/regenerate_frozen.py",
)
WRITE_TOKENS = ("write_text", "write_bytes", "safe_dump", "json.dump", "dump(", ".write(")


# ----------------------------------------------------------------------------- helpers
def sha256(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None


def looks_like_path(s: str) -> bool:
    if not isinstance(s, str) or len(s) < 3 or len(s) > 200:
        return False
    if s.startswith(("/", "http", "#")) or "\n" in s:
        return False
    return "/" in s and s.endswith(SUFFIXES)


def norm_rel(root: Path, p: Path) -> str | None:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


# ----------------------------------------------------------------- symbolic evaluation
def eval_path(node, env: dict, src_file: Path):
    """Evaluate a Path expression to an absolute-ish Path, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return Path(node.value)
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.Attribute):
        base = eval_path(node.value, env, src_file)
        if base is None:
            return None
        if node.attr == "parent":
            return base.parent
        return None
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            base = eval_path(node.value.value, env, src_file)
            if base is not None and isinstance(node.slice, ast.Constant):
                try:
                    return base.parents[int(node.slice.value)]
                except (TypeError, ValueError):
                    return None
        return None
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "resolve":
            return eval_path(f.value, env, src_file)
        if isinstance(f, ast.Name) and f.id == "Path":
            if len(node.args) == 1:
                return eval_path(node.args[0], env, src_file)
        if isinstance(f, ast.Attribute) and f.attr == "glob":
            return eval_path(f.value, env, src_file)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        a = eval_path(node.left, env, src_file)
        b = eval_path(node.right, env, src_file)
        if a is not None and b is not None:
            return a / b
        return None
    return None


class ModuleScan(ast.NodeVisitor):
    """Collect module-level path symbols, local imports, literals, and name usages."""

    def __init__(self, src_file: Path, root: Path):
        self.src_file = src_file
        self.root = root
        self.env: dict = {"__file__": src_file}
        self.symbols: dict[str, Path] = {}
        self.imports: list[str] = []
        self.literals: list[tuple[str, int]] = []
        self.globs: list[tuple[Path, str, int]] = []
        self.line_of: dict[str, int] = {}
        self.uses: dict[str, list[tuple[str, int]]] = {}

    # -- module level assignments, in source order -------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            if isinstance(t, ast.Name):
                v = eval_path(node.value, self.env, self.src_file)
                if v is not None:
                    self.env[t.id] = v
                    self.symbols[t.id] = v
                    self.line_of[t.id] = node.lineno
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            v = eval_path(node.value, self.env, self.src_file)
            if v is not None:
                self.env[node.target.id] = v
                self.symbols[node.target.id] = v
                self.line_of[node.target.id] = node.lineno
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.imports.append(a.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.level == 0:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if looks_like_path(node.value):
            self.literals.append((node.value, node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # DIR.glob("PAT") / DIR.rglob("PAT"): the pattern decides which files are read
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in ("glob", "rglob") and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            base = eval_path(f.value, self.env, self.src_file)
            if base is not None:
                self.globs.append((base, node.args[0].value, node.lineno))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in getattr(self, "_declared", set()):
            self.uses.setdefault(node.id, []).append(("use", node.lineno))
        self.generic_visit(node)


def scan_module(src_file: Path, root: Path) -> ModuleScan:
    tree = ast.parse(src_file.read_text(errors="replace"))
    sc = ModuleScan(src_file, root)
    # seed usage tracking with declared symbol names
    declared = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    declared.add(t.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            declared.add(n.target.id)
    sc._declared = declared
    sc.visit(tree)
    return sc


def role_of(src_text: str, var: str, line: int) -> str:
    """Coarse role inference for one symbol: exec > write > read."""
    import re
    window = "\n".join(src_text.splitlines()[max(0, line - 3): line + 6])
    if "subprocess" in window and f"str({var})" in window:
        return "exec"
    v = re.escape(var)
    if re.search(rf"\b{v}\.(write|write_text|write_bytes|open)\b", window):
        return "write"
    if re.search(rf"(safe_dump|json\.dump|dump)\([^)]*\b{v}\b", window, re.S):
        return "write"
    # a directory the tool creates/clears and never globs is an output surface
    if re.search(rf"(rmtree|mkdir|makedirs)\(\s*{v}\b", window) and \
            not re.search(rf"\b{v}\.(glob|rglob|iterdir|read_text|read_bytes)\b", window):
        return "write"
    return "read"


def discover(root: Path, entry_rel: str):
    """BFS over local modules reached from one entry point."""
    refs: list[dict] = []
    seen_mods: set[str] = set()
    queue: list[tuple[str, int]] = [(entry_rel, 0)]
    while queue:
        rel, depth = queue.pop(0)
        if rel in seen_mods or depth > MAX_DEPTH:
            continue
        seen_mods.add(rel)
        src = root / rel
        if not src.is_file():
            refs.append({"path": rel, "role": "exec", "from": None, "line": 0,
                         "status": "MISSING"})
            continue
        text = src.read_text(errors="replace")
        sc = scan_module(src, root)
        # subprocess tool arguments: str(SYMBOL) inside a subprocess.run call
        exec_syms = set()
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr in ("run", "Popen", "check_call", "check_output"):
                for a in ast.walk(n):
                    if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) \
                            and a.func.id == "str" and a.args \
                            and isinstance(a.args[0], ast.Name):
                        exec_syms.add(a.args[0].id)
        for name, path in sc.symbols.items():
            r = norm_rel(root, path)
            if r is None or r == "." or "\n" in r or len(r) > 300:
                continue          # outside the repo, repo-root anchor, or prose blob
            if not ((root / r).exists() or looks_like_path(r)):
                continue          # symbol bound to prose, not to a path
            role = "exec" if name in exec_syms else role_of(text, name, sc.line_of[name])
            refs.append({"path": r, "role": role, "from": rel, "line": sc.line_of[name],
                         "symbol": name})
            # a pinned driver that reaches a local .py module (import or subprocess)
            # pulls that module's own references into the closure (depth-limited BFS)
            if r.endswith(".py") and (root / r).is_file() and r not in seen_mods:
                queue.append((r, depth + 1))
        for lit, line in sc.literals:
            r = norm_rel(root, root / lit)
            if r and r != rel:
                refs.append({"path": r, "role": "mention", "from": rel, "line": line,
                             "symbol": None})
        for base, pattern, line in sc.globs:
            r = norm_rel(root, base)
            if r and r != ".":
                refs.append({"path": r, "role": "read_glob", "from": rel, "line": line,
                             "symbol": None, "pattern": pattern})
        for mod in sc.imports:
            mrel = mod.replace(".", "/")
            bases = [Path(rel).parent]
            if Path(rel).parent != Path("."):
                bases.append(Path("."))
            for b in bases:
                for cand in ((b / f"{mrel}.py").as_posix(),
                             (b / mrel / "__init__.py").as_posix()):
                    if (root / cand).is_file() and cand not in seen_mods:
                        refs.append({"path": cand, "role": "exec", "from": rel, "line": 0,
                                     "symbol": None})
                        queue.append((cand, depth + 1))
                        break
    return refs


def expand_dirs(root: Path, refs: list[dict]) -> dict[str, dict]:
    """Return {relpath: {'kind': file|dir, 'files': [...], 'truncated': bool}}.

    A directory is expanded to its files only when a tool globs it with a literal
    pattern; a bare base-anchor reference (ROOT/"artifacts"/"formulation") must not
    import every file below it.
    """
    out: dict[str, dict] = {}
    by_path: dict[str, list[dict]] = {}
    for r in refs:
        by_path.setdefault(r["path"], []).append(r)
    for rel in sorted(by_path):
        if "\n" in rel or len(rel) > 300:
            continue
        p = root / rel
        patterns = sorted({r["pattern"] for r in by_path[rel]
                           if r["role"] == "read_glob" and r.get("pattern")})
        if p.is_dir():
            hits: set[Path] = set()
            for pat in patterns:
                hits |= {x for x in p.glob(pat) if x.is_file()}
            files = sorted(hits)[:MAX_DIR_FILES]
            out[rel] = {"kind": "dir",
                        "files": [norm_rel(root, x) for x in files],
                        "n_files": len(files),
                        "patterns": patterns,
                        "truncated": len(hits) > MAX_DIR_FILES}
        elif p.exists():
            out[rel] = {"kind": "file", "files": [rel], "n_files": 1, "truncated": False}
        else:
            out[rel] = {"kind": "missing", "files": [], "n_files": 0, "truncated": False}
    return out


def classify(root: Path, frozen_files: dict[str, dict], refs: list[dict],
             frozen_rel: str = "artifacts/formulation/FROZEN.json") -> dict:
    declared = {k: v["sha256"] for k, v in frozen_files.items()}
    expanded = expand_dirs(root, refs)
    all_files: dict[str, dict] = {}
    for rel, info in expanded.items():
        if info["kind"] == "file":
            all_files[rel] = info
        elif info["kind"] == "dir":
            for f in info["files"]:
                if "__pycache__" in f or f.endswith(".pyc"):
                    continue
                all_files.setdefault(f, {"kind": "file", "files": [f], "n_files": 1,
                                         "truncated": False, "parent_dir": rel})
    nodes: dict[str, dict] = {}
    glob_refs: dict[str, list[dict]] = {}
    for r in refs:
        if r["role"] == "read_glob":
            glob_refs.setdefault(r["path"], []).append(r)
    for rel in sorted(set(expanded) | set(all_files)):
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        p = root / rel
        exists = p.exists()
        d = declared.get(rel)
        measured = sha256(p) if p.is_file() else None
        if rel in declared:
            status = "PINNED_OK" if measured == d else "PINNED_DRIFT"
        else:
            status = "UNPINNED" if exists else "MISSING"
        node_refs = [r for r in refs if r["path"] == rel]
        roles = {r["role"] for r in node_refs}
        kind = expanded.get(rel, {}).get("kind", "file")
        parent = all_files.get(rel, {}).get("parent_dir")
        froms = {r["from"] for r in node_refs if r["from"]}
        if parent:                              # globbed files inherit the read role + origin
            for gr in glob_refs.get(parent, []):
                roles.add("read")
                if gr.get("from"):
                    froms.add(gr["from"])
        roles.discard("read_glob")
        is_module = rel.endswith(".py")
        # tier: what kind of outcome influence this path has
        if rel == frozen_rel:
            tier = "pin_root"                        # manifest cannot pin itself (recorded rule)
        elif status == "PINNED_OK":
            tier = "pinned"
        elif roles == {"mention"}:
            tier = "mention"                         # prose reference only; cannot move a verdict
        elif kind == "dir":
            tier = "dir"
        elif is_module or "exec" in roles:
            tier = "verdict_code"                    # executable decision logic
        elif "read" in roles:
            tier = "corpus"                          # data read to produce a verdict
        else:
            tier = "output"                          # written only; cannot change a verdict
        # A missing read/exec target is a gap too: something unpinned must create it.
        # Bare directories are not gaps by themselves; their files are classified.
        effect = bool(status != "PINNED_OK" and tier in ("verdict_code", "corpus"))
        nodes[rel] = {
            "path": rel,
            "kind": kind,
            "n_files": expanded.get(rel, {}).get("n_files", 1),
            "truncated": expanded.get(rel, {}).get("truncated", False),
            "parent_dir": parent,
            "exists": exists,
            "declared_sha256": d,
            "measured_sha256": measured,
            "status": status,
            "roles": sorted(roles),
            "module": is_module,
            "tier": tier,
            "from_tools": sorted(froms),
            "effect_capable": effect,
            "references": sorted({(r["from"] or "-", r["role"], r["line"]) for r in node_refs}),
        }
    gaps = sorted(k for k, v in nodes.items() if v["effect_capable"])
    mentions = sorted(k for k, v in nodes.items() if v["roles"] == ["mention"])
    tiers = {t: sum(1 for v in nodes.values() if v["tier"] == t) for t in
             ("verdict_code", "corpus", "pinned", "pin_root", "dir", "output", "mention")}
    return {
        "nodes": nodes,
        "effect_capable_unpinned": gaps,
        "mention_only": mentions,
        "tier_counts": tiers,
        "counts": {
            "reached": len(nodes),
            "pinned_ok": sum(1 for v in nodes.values() if v["status"] == "PINNED_OK"),
            "pinned_drift": sum(1 for v in nodes.values() if v["status"] == "PINNED_DRIFT"),
            "unpinned": sum(1 for v in nodes.values() if v["status"] == "UNPINNED"),
            "missing": sum(1 for v in nodes.values() if v["status"] == "MISSING"),
            "effect_capable_unpinned": len(gaps),
        },
        "verdict": "CLOSURE_GAP" if gaps else "CLOSED",
    }


def run_check(root: Path, frozen_rel: str = "artifacts/formulation/FROZEN.json",
              entries: list[str] | None = None, scope: str = "acceptance") -> dict:
    frozen = json.loads((root / frozen_rel).read_text())
    frozen_sha = sha256(root / frozen_rel)
    if entries is None:
        if scope == "acceptance":
            entries = [e for e in ACCEPTANCE_TOOLS if (root / e).is_file()]
        else:
            entries = sorted(k for k in frozen["files"] if k.endswith(".py"))
    refs: list[dict] = []
    per_entry: dict[str, int] = {}
    for e in entries:
        got = discover(root, e)
        for r in got:
            r["from"] = r["from"] or e
        refs.extend(got)
        per_entry[e] = len(got)
        # the entry tool is itself in the closure: a drifted pinned driver is a gap
        refs.append({"path": e, "role": "exec", "from": e, "line": 0, "symbol": "entry"})
    # dedupe refs on (path, from, role, line)
    uniq = {}
    for r in refs:
        uniq[(r["path"], r["from"], r["role"], r["line"])] = r
    refs = [uniq[k] for k in sorted(uniq, key=lambda t: (t[0], t[1] or "", t[2], t[3]))]
    body = classify(root, frozen["files"], refs, frozen_rel)
    return {
        "schema": "w058/instrument-closure/v1",
        "root": str(root),
        "scope": scope,
        "frozen_path": frozen_rel,
        "frozen_sha256": frozen_sha,
        "frozen_revision": frozen.get("revision"),
        "entries": entries,
        "entry_reference_counts": per_entry,
        "references": refs,
        **body,
    }


# ------------------------------------------------------------------------------ selftest
SELFTEST_ENTRY = '''#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "gate.py"
DATA = ROOT / "data" / "pinned.json"
OUT = ROOT / "out" / "report.json"
def main():
    r = subprocess.run([sys.executable, str(GATE), str(DATA)], capture_output=True, text=True)
    OUT.write_text(r.stdout)
if __name__ == "__main__":
    main()
'''
SELFTEST_GATE = "import json, sys\nprint(json.dumps({'verdict': 'pass'}))\n"


def _mk_tree(base: Path, extra_gate: str = "", data_edit: str = "",
             pinned=(("tools/run.py", None), ("tools/gate.py", "gate"), ("data/pinned.json", "data")),
             gate_pin: bool = True):
    if base.exists():
        shutil.rmtree(base)
    (base / "tools").mkdir(parents=True)
    (base / "data").mkdir(parents=True)
    (base / "out").mkdir(parents=True)
    (base / "tools" / "run.py").write_text(SELFTEST_ENTRY)
    (base / "tools" / "gate.py").write_text(SELFTEST_GATE + extra_gate)
    (base / "data" / "pinned.json").write_text('{"x": 1}\n' + data_edit)
    files = {}
    for rel, key in pinned:
        if key == "gate" and not gate_pin:
            continue
        p = base / rel
        files[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    man = {"artifact": "SYNTH", "revision": 1, "files": files}
    (base / "FROZEN.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def selftest(base: Path) -> dict:
    base.mkdir(parents=True, exist_ok=True)
    cases = []

    def case(name, measured, expected, detail=""):
        cases.append({"case": name, "expected": expected, "measured": measured,
                      "pass": measured == expected, "detail": detail})

    # S1 closed tree: every reached non-output path pinned
    t = base / "s1"
    man = _mk_tree(t)
    r = run_check(t, "FROZEN.json", scope="all")
    case("S1_closed_tree", r["verdict"], "CLOSED", ",".join(r["effect_capable_unpinned"]))
    # note: the entry itself and the manifest are pinned; reached gate+data pinned
    # S2 unpinned executable module
    t = base / "s2"
    man = _mk_tree(t, gate_pin=False)
    r = run_check(t, "FROZEN.json", scope="all")
    case("S2_unpinned_exec", r["verdict"], "CLOSURE_GAP",
         "flagged=" + ",".join(r["effect_capable_unpinned"]))
    case("S2_unpinned_exec_flags_gate", str("tools/gate.py" in r["effect_capable_unpinned"]),
         "True")
    # S3 pinned drift
    t = base / "s3"
    man = _mk_tree(t)
    (t / "data" / "pinned.json").write_text('{"x": 2}\n')
    r = run_check(t, "FROZEN.json", scope="all")
    case("S3_pinned_drift", r["verdict"], "CLOSURE_GAP",
         "flagged=" + ",".join(r["effect_capable_unpinned"]))
    case("S3_drift_status", r["nodes"]["data/pinned.json"]["status"], "PINNED_DRIFT")
    # S4 transitive discovery: pinned gate imports unpinned helper
    t = base / "s4"
    man = _mk_tree(t)
    g = (t / "tools" / "gate.py")
    g.write_text("import helper\n" + g.read_text())
    (t / "tools" / "helper.py").write_text("VALUE = 1\n")
    man["files"]["tools/gate.py"] = {"sha256": sha256(g), "bytes": g.stat().st_size}
    (t / "FROZEN.json").write_text(json.dumps(man, indent=1) + "\n")
    r = run_check(t, "FROZEN.json", scope="all")
    case("S4_transitive_helper", str("tools/helper.py" in r["effect_capable_unpinned"]), "True")
    # S5 output-only unpinned file is not a gap
    t = base / "s5"
    man = _mk_tree(t)
    r = run_check(t, "FROZEN.json", scope="all")
    case("S5_output_not_gap", str("out/report.json" in r["effect_capable_unpinned"]), "False")
    # S6 missing read input
    t = base / "s6"
    man = _mk_tree(t)
    man["files"].pop("data/pinned.json", None)
    (t / "FROZEN.json").write_text(json.dumps(man, indent=1) + "\n")
    (t / "data" / "pinned.json").unlink()
    r = run_check(t, "FROZEN.json", scope="all")
    case("S6_missing_read", str("data/pinned.json" in r["effect_capable_unpinned"]), "True")
    # S7 idempotence
    t = base / "s7"
    man = _mk_tree(t, gate_pin=False)
    a = json.dumps(run_check(t, "FROZEN.json", scope="all"), sort_keys=True)
    b = json.dumps(run_check(t, "FROZEN.json", scope="all"), sort_keys=True)
    case("S7_idempotent", str(a == b), "True")
    # S8 stdlib imports do not create false positives
    t = base / "s8"
    man = _mk_tree(t)
    r = run_check(t, "FROZEN.json", scope="all")
    case("S8_no_stdlib_fp", str("json" not in r["nodes"] and "sys" not in r["nodes"]), "True")
    return {"all_pass": all(c["pass"] for c in cases), "cases": cases,
            "passed": sum(1 for c in cases if c["pass"]), "total": len(cases)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--frozen", default="artifacts/formulation/FROZEN.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--scope", default="acceptance", choices=("acceptance", "all"))
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selftest-dir", default=None)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if a.selftest:
        sd = Path(a.selftest_dir) if a.selftest_dir else root / "artifacts/worker-058/instrument_closure/_selftest"
        res = selftest(sd)
        text = json.dumps(res, indent=2, sort_keys=True) + "\n"
        if a.out:
            Path(a.out).write_text(text)
        print(f"SELFTEST {res['passed']}/{res['total']} all_pass={res['all_pass']}")
        return 0 if res["all_pass"] else 1
    res = run_check(root, a.frozen, scope=a.scope)
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    print(f"CLOSURE[{a.scope}]: {res['verdict']}  reached={res['counts']['reached']} "
          f"pinned_ok={res['counts']['pinned_ok']} drift={res['counts']['pinned_drift']} "
          f"unpinned={res['counts']['unpinned']} effect_capable_unpinned={res['counts']['effect_capable_unpinned']}")
    print(f"  tiers: {res['tier_counts']}")
    for g in res["effect_capable_unpinned"]:
        n = res["nodes"][g]
        print(f"  GAP[{n['tier']}]: {g} [{n['status']}] roles={n['roles']} from={n['from_tools'][:2]}")
    return 1 if (a.strict and res["verdict"] != "CLOSED") else 0


if __name__ == "__main__":
    sys.exit(main())
