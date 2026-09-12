#!/usr/bin/env python3
"""W083-FROZEN-TOOLCHAIN-WRITE-HAZARD-CENSUS-01 -- read-only census of the FROZEN rev29
pinned Python toolchain.

Question: which pinned tools, when invoked with DEFAULT arguments to verify the freeze,
silently rewrite FROZEN-pinned canonical artifacts?

Two independent lines of evidence:
  (A) static AST analysis: every write primitive, its statically-resolved target, whether the
      target is one of the 50 FROZEN rev29 pinned paths, and whether the write is opt-in
      (enclosing condition requires a CLI flag that defaults to off) or reachable by default;
  (B) dynamic sandbox measurement: each pinned tool is run with default arguments inside a
      byte-copy sandbox of the pinned tree while sha256 + mtime_ns of every mirrored pinned
      path is measured before/after.  A second sentinel sandbox pre-seeds each statically
      resolved pinned target with one extra line: if the tool replaces the sentinel, the
      default invocation demonstrably mutates a frozen path's bytes.

No canonical path is written by this instrument.  The canonical 50-pin state is measured
before and after the dynamic phase as a containment control.
"""
import argparse
import ast
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = "W083-FROZEN-TOOLCHAIN-WRITE-HAZARD-CENSUS-01"
OUTDIR = ROOT / "artifacts/worker-083/frozen_toolchain_write_hazard"
SANDBOX_ROOT = ROOT / "tmp/w083_write_hazard"
FROZEN = "artifacts/formulation/FROZEN.json"
SENTINEL = b"\n# W083_SENTINEL_PROBE\n"
TIMEOUT = 180
WRITE_ATTRS = {"write_text", "write_bytes", "touch", "unlink", "rename", "replace", "mkdir"}
WRITE_FUNCS = {"os.remove", "os.unlink", "os.rename", "os.replace", "shutil.copy",
               "shutil.copyfile", "shutil.copy2", "shutil.move", "shutil.rmtree",
               "os.makedirs", "os.mkdir"}
DUMP_FUNCS = {"json.dump", "yaml.dump", "yaml.safe_dump", "csv.writer"}


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canonical_digest(obj):
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


# ---------------------------------------------------------------- static analysis
class Resolver(ast.NodeVisitor):
    """Collect name -> repo-relative path bindings, in source order, with a simple evaluator."""

    def __init__(self):
        self.env = {}          # global bindings
        self.func_env = {}     # function name -> local bindings (best effort)

    @staticmethod
    def strip_resolve_chain(node):
        """Return the innermost Name/Constant of a Path(...).resolve().parents[N] chain."""
        while isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in ("resolve", "absolute", "parent", "parents"):
                node = f.value
                continue
            if isinstance(f, ast.Name) and f.id == "Path" and len(node.args) == 1:
                node = node.args[0]
                continue
            break
        return node

    def eval_path(self, node, env):
        if node is None:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            l = self.eval_path(node.left, env)
            r = self.eval_path(node.right, env)
            if l is None or r is None:
                return None
            return posixpath.join(l, r) if l else r
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    return None
            return "".join(parts)
        if isinstance(node, ast.Subscript):
            # Path(__file__).resolve().parents[3]  ->  Subscript(value=Attribute(attr='parents'), slice=3)
            base = node.value
            if isinstance(base, ast.Attribute) and base.attr == "parents" \
                    and isinstance(node.slice, ast.Constant):
                n = node.slice.value
                inner = self.strip_resolve_chain(base.value)
                if isinstance(inner, ast.Name) and inner.id == "__file__" and n == 3:
                    return ""
                p = self.eval_path(base.value, env)
                if p is not None:
                    for _ in range(n):
                        p = posixpath.dirname(p)
                    return p
            return None
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "Path" and len(node.args) == 1:
                return self.eval_path(node.args[0], env)
            if isinstance(f, ast.Attribute):
                if f.attr in ("resolve", "absolute"):
                    return self.eval_path(f.value, env)
                if f.attr == "parent":
                    p = self.eval_path(f.value, env)
                    return posixpath.dirname(p) if p is not None else None
                if f.attr == "joinpath" and len(node.args) == 1:
                    p = self.eval_path(f.value, env)
                    q = self.eval_path(node.args[0], env)
                    if p is not None and q is not None:
                        return posixpath.join(p, q)
                    return None
                if f.attr == "parents" and len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                    n = node.args[0].value
                    inner = self.strip_resolve_chain(f.value)
                    if isinstance(inner, ast.Name) and inner.id == "__file__" and n == 3:
                        return ""  # repo root
                    p = self.eval_path(f.value, env)
                    if p is not None:
                        for _ in range(n):
                            p = posixpath.dirname(p)
                        return p
                    return None
        return None

    def collect(self, tree):
        for node in tree.body:
            if isinstance(node, ast.Assign):
                v = self.eval_path(node.value, self.env)
                if v is not None:
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.env[t.id] = v
            elif isinstance(node, ast.FunctionDef):
                local = dict(self.env)
                for st in node.body:
                    if isinstance(st, ast.Assign):
                        v = self.eval_path(st.value, local)
                        if v is not None:
                            for t in st.targets:
                                if isinstance(t, ast.Name):
                                    local[t.id] = v
                # fallback map: every resolvable assignment anywhere in the function body
                deep = dict(self.env)
                for st in ast.walk(node):
                    if isinstance(st, ast.Assign):
                        v = self.eval_path(st.value, deep)
                        if v is not None:
                            for t in st.targets:
                                if isinstance(t, ast.Name):
                                    deep[t.id] = v
                self.func_env[node.name] = local
                self.func_env[node.name + "\x00deep"] = deep


def argparse_flags(tree):
    """dest -> (default_value_repr, default_truthy, required)."""
    flags = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "add_argument" and node.args:
            a0 = node.args[0]
            if not (isinstance(a0, ast.Constant) and isinstance(a0.value, str)):
                continue
            opt = a0.value
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            dest = None
            if "dest" in kw and isinstance(kw["dest"], ast.Constant):
                dest = kw["dest"].value
            elif opt.startswith("--"):
                dest = opt[2:].replace("-", "_")
            if not dest:
                continue
            action = kw.get("action")
            action = action.value if isinstance(action, ast.Constant) else None
            required = bool(isinstance(kw.get("required"), ast.Constant) and kw["required"].value)
            if required:
                default, truthy = "<required>", False
            elif "default" in kw:
                dv = kw["default"]
                if isinstance(dv, ast.Constant):
                    default, truthy = repr(dv.value), bool(dv.value)
                else:
                    default, truthy = "<expr>", True
            elif action == "store_true":
                default, truthy = "False", False
            elif action == "store_false":
                default, truthy = "True", True
            elif action in ("count", "append"):
                default, truthy = "None", False
            else:
                default, truthy = "None", False
            flags[dest] = {"option": opt, "default": default, "default_truthy": truthy,
                           "required": required, "action": action}
    return flags


def argparse_result_vars(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr == "parse_args":
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
    return names


def flag_gate_status(test, flags, avars):
    """Return True if this test, when it passes, REQUIRES a flag that defaults to off.

    Handles `if args.apply:`, `if not args.dry_run:` (with dry_run default), and simple
    and/or combinations.  Returns False when the truthy branch is the default path.
    """
    def flag_of(n):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and (n.value.id in avars or n.value.id == "args"):
            return n.attr
        if isinstance(n, ast.Name) and n.id in flags:
            return n.id
        return None

    def walk_cond(n):
        f = flag_of(n)
        if f and f in flags:
            fl = flags[f]
            # truthy required by `if flag:`; guarded iff flag defaults off
            return (not fl["default_truthy"]) and (not fl["required"])
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            f = flag_of(n.operand)
            if f and f in flags:
                fl = flags[f]
                # requires flag falsy; guarded iff flag defaults on
                return bool(fl["default_truthy"])
            return False
        if isinstance(n, ast.BoolOp):
            vals = [walk_cond(v) for v in n.values]
            return any(vals) if isinstance(n.op, ast.And) else all(v for v in vals if v)
        return False

    return bool(walk_cond(test))


def main_guard_calls(tree):
    """Function names called directly from the `if __name__ == '__main__':` block."""
    names = set()
    for node in tree.body:
        if isinstance(node, ast.If):
            t = ast.unparse(node.test).replace('"', "'")
            if "__name__" in t and "__main__" in t:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        names.add(sub.func.id)
    return names


def write_sites(tree):
    """Yield (node, kind) for every write-primitive call."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute):
            if f.attr in WRITE_ATTRS:
                yield node, f"Path.{f.attr}"
            elif f.attr in ("dump",) and isinstance(f.value, ast.Name) and f.value.id in ("json", "yaml"):
                yield node, f"{f.value.id}.{f.attr}"
            elif f.attr in ("safe_dump",) and isinstance(f.value, ast.Name) and f.value.id == "yaml":
                yield node, f"yaml.{f.attr}"
        elif isinstance(f, ast.Name):
            if f.id == "open":
                mode = None
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for k in node.keywords:
                    if k.arg == "mode" and isinstance(k.value, ast.Constant):
                        mode = k.value.value
                if isinstance(mode, str) and any(c in mode for c in "wax+"):
                    yield node, "open(write)"
            elif f.id in ("print",):
                pass
        # fully-qualified calls: os.remove(...), shutil.copy(...)
        qual = ast.unparse(f)
        if qual in WRITE_FUNCS:
            yield node, qual


def resolve_write_target(node, kind, env):
    """Best-effort resolution of the mutated path."""
    if kind.startswith("Path.") or kind == "open(write)":
        recv = node.func.value if kind.startswith("Path.") else (node.args[0] if node.args else None)
        r = Resolver().eval_path(recv, env)
        return r
    if kind in ("json.dump", "yaml.dump", "yaml.safe_dump"):
        if len(node.args) >= 2:
            return Resolver().eval_path(node.args[1], env)
        return None
    if kind in WRITE_FUNCS:
        if node.args:
            return Resolver().eval_path(node.args[0], env)
    return None


def analyze_tool(relpath):
    src = (ROOT / relpath).read_text()
    tree = ast.parse(src)
    flags = argparse_flags(tree)
    avars = argparse_result_vars(tree)
    calls_from_main = main_guard_calls(tree)
    res = Resolver()
    res.collect(tree)
    env = dict(res.env)

    # map: node -> enclosing If tests, function name
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    enclosing = {}
    func_of = {}
    for node in ast.walk(tree):
        chain = []
        cur = parents.get(node)
        fn = None
        while cur is not None:
            if isinstance(cur, ast.If):
                chain.append(cur.test)
            if isinstance(cur, ast.FunctionDef):
                fn = cur.name
            cur = parents.get(cur)
        enclosing[node] = chain
        func_of[node] = fn

    sites = []
    for node, kind in write_sites(tree):
        # local env: nearest FunctionDef locals collected above the call line
        fn_name = func_of.get(node)
        local_env = dict(env)
        if fn_name and fn_name in res.func_env:
            for k, v in res.func_env.get(fn_name + "\x00deep", {}).items():
                local_env.setdefault(k, v)
            for k, v in res.func_env[fn_name].items():
                local_env.setdefault(k, v)
        target = resolve_write_target(node, kind, local_env)
        target = posixpath.normpath(target) if target else None
        site_tests = enclosing.get(node, [])
        flag_guarded = any(flag_gate_status(t, flags, avars) for t in site_tests)
        callsite_guarded = None
        if fn_name and fn_name not in calls_from_main:
            callers = [c for c in ast.walk(tree) if isinstance(c, ast.Call)
                       and isinstance(c.func, ast.Name) and c.func.id == fn_name]
            if callers:
                statuses = []
                for c in callers:
                    ct = enclosing.get(c, [])
                    statuses.append(any(flag_gate_status(t, flags, avars) for t in ct))
                callsite_guarded = all(statuses)
            else:
                callsite_guarded = False
        required_args = any(f["required"] for f in flags.values())
        src_line = ast.get_source_segment(src, node) or ""
        sites.append({
            "line": node.lineno,
            "kind": kind,
            "source": " ".join(src_line.split())[:220],
            "resolved_target": target,
            "flag_guarded": bool(flag_guarded),
            "callsite_guarded": callsite_guarded,
            "function": fn_name,
            "required_args_present": required_args,
        })
    # classification needs the pinned set -> filled by caller
    return {
        "tool": relpath,
        "sha256": sha256_file(ROOT / relpath),
        "has_main_guard": bool(calls_from_main),
        "argparse_flags": flags,
        "required_args_present": any(f["required"] for f in flags.values()),
        "write_sites": sites,
    }


def classify(tool, pinned):
    AMBIG = {"Path.replace", "Path.rename", "Path.touch", "Path.unlink", "Path.mkdir"}
    # dedupe: a dump call nested in the args of a Path.write_* call is the same write site
    byline = {}
    for s in tool["write_sites"]:
        key = (s["line"], s["resolved_target"])
        prev = byline.get(key)
        if prev is None or (s["kind"] in AMBIG and prev["kind"] not in AMBIG):
            byline[key] = s
    sites = list(byline.values())
    sites.sort(key=lambda s: (s["line"], s["kind"]))
    for s in sites:
        t = s["resolved_target"]
        s["target_pinned"] = bool(t and t in pinned)
        if t and (t.startswith("tmp/") or "/tmp" in t or "mkdtemp" in s["source"]):
            s["classification"] = "TEMP"
        elif s["required_args_present"] and not s["flag_guarded"] and not s["callsite_guarded"]:
            s["classification"] = "REQUIRES_ARGS_UNREACHABLE_BY_DEFAULT"
        elif s["target_pinned"]:
            s["classification"] = ("GUARDED_PINNED" if (s["flag_guarded"] or s["callsite_guarded"])
                                   else "UNGUARDED_PINNED")
        elif t is None and s["kind"] in AMBIG:
            s["classification"] = "AMBIGUOUS_UNRESOLVED"
        elif t is None:
            s["classification"] = "UNRESOLVED"
        else:
            s["classification"] = ("GUARDED_UNPINNED" if (s["flag_guarded"] or s["callsite_guarded"])
                                   else "UNGUARDED_UNPINNED")
    tool["write_sites"] = sites
    return tool


# ---------------------------------------------------------------- dynamic sandbox
MIRROR_SETS = [("artifacts/formulation", "artifacts/formulation"),
               ("artifacts/worker-06", "artifacts/worker-06"),
               ("schemas", "schemas")]


def build_sandbox(name, sentinel_targets=()):
    sb = SANDBOX_ROOT / name
    if sb.exists():
        shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for src, dst in MIRROR_SETS:
        s = ROOT / src
        if s.exists():
            shutil.copytree(s, sb / dst,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    rm = sb / "research_map"
    rm.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "research_map/formulation_taxonomy.yaml", rm / "formulation_taxonomy.yaml")
    # only the pinned FROZEN.json revision is copied (already inside artifacts/formulation)
    for t in sentinel_targets:
        p = sb / t
        if p.exists():
            p.write_bytes(p.read_bytes() + SENTINEL)
    return sb


def snapshot(sb, pinned):
    snap = {}
    for rel in pinned:
        p = sb / rel
        if p.exists():
            st = p.stat()
            snap[rel] = {"sha256": sha256_file(p), "mtime_ns": st.st_mtime_ns, "ino": st.st_ino}
    return snap


def diff_snapshots(before, after):
    out = {"mutated_bytes": [], "rewritten_identical": [], "deleted": [], "created": [],
           "unchanged": 0}
    for rel, b in before.items():
        a = after.get(rel)
        if a is None:
            out["deleted"].append(rel)
        elif a["sha256"] != b["sha256"]:
            out["mutated_bytes"].append(rel)
        elif (a["mtime_ns"] != b["mtime_ns"]) or (a["ino"] != b["ino"]):
            out["rewritten_identical"].append(rel)
        else:
            out["unchanged"] += 1
    for rel in after:
        if rel not in before:
            out["created"].append(rel)
    return out


def run_tool(sb, reltool):
    tool = sb / reltool
    if not tool.exists():
        return {"exit": None, "note": "tool missing in sandbox", "stdout_tail": "", "stderr_tail": ""}
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run([sys.executable, str(tool)], cwd=str(sb), capture_output=True,
                           text=True, timeout=TIMEOUT, env=env)
        return {"exit": r.returncode,
                "stdout_tail": r.stdout[-400:], "stderr_tail": r.stderr[-400:]}
    except subprocess.TimeoutExpired:
        return {"exit": "timeout", "stdout_tail": "", "stderr_tail": f"timeout>{TIMEOUT}s"}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all", choices=["static", "dynamic", "all"])
    ap.add_argument("--tools", default=None, help="comma list of tool basenames to run dynamically")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    frozen = json.loads((ROOT / FROZEN).read_text())
    pinned = {k: v["sha256"] for k, v in frozen["files"].items()}
    pinned_tools = sorted(p for p in pinned if p.startswith("artifacts/formulation/tools/")
                          and p.endswith(".py"))

    # ---- canonical containment: before
    canon_before = {p: (sha256_file(ROOT / p) if (ROOT / p).exists() else None) for p in pinned}

    result = {"task": TASK, "frozen_manifest": FROZEN, "frozen_revision": frozen["revision"],
              "frozen_sha256": sha256_file(ROOT / FROZEN), "frozen_at": frozen["frozen_at"],
              "pinned_count": len(pinned), "pinned_tool_count": len(pinned_tools),
              "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    if args.phase in ("static", "all"):
        tools = [classify(analyze_tool(t), pinned) for t in pinned_tools]
        # determinism control: analyze twice
        tools2 = [classify(analyze_tool(t), pinned) for t in pinned_tools]
        result["static"] = tools
        result["static_determinism_equal"] = canonical_digest(tools) == canonical_digest(tools2)
        result["static_digest"] = canonical_digest(tools)
        unguarded = [(t["tool"], s["line"], s["resolved_target"]) for t in tools for s in t["write_sites"]
                     if s["classification"] == "UNGUARDED_PINNED"]
        result["static_unguarded_pinned_sites"] = unguarded
        result["static_unguarded_pinned_tools"] = sorted({u[0] for u in unguarded})
        (OUTDIR / "census.json").write_text(json.dumps(result, indent=1) + "\n")

    if args.phase in ("dynamic", "all"):
        if "static" not in result:
            result["static"] = json.loads((OUTDIR / "census.json").read_text())["static"]
        tools_meta = {t["tool"]: t for t in result["static"]}
        run_list = pinned_tools
        if args.tools:
            wanted = {x.strip() for x in args.tools.split(",")}
            run_list = [t for t in pinned_tools if Path(t).stem in wanted or t in wanted]
        dyn = {"task": TASK, "timeout_s": TIMEOUT, "runs": [], "sentinel": []}
        for rel in run_list:
            stem = Path(rel).stem
            meta = tools_meta[rel]
            resolved_pinned = sorted({s["resolved_target"] for s in meta["write_sites"]
                                      if s["target_pinned"]})
            # A: pristine sandbox
            sbA = build_sandbox(f"A_{stem}")
            snapA0 = snapshot(sbA, pinned)
            rA = run_tool(sbA, rel)
            snapA1 = snapshot(sbA, pinned)
            dA = diff_snapshots(snapA0, snapA1)
            dyn["runs"].append({"tool": rel, "mode": "pristine_default", "sandbox": str(sbA.relative_to(ROOT)),
                                "run": rA, "diff": dA})
            # B: sentinel sandbox (only for tools with statically resolved pinned targets)
            if resolved_pinned:
                sbB = build_sandbox(f"B_{stem}", sentinel_targets=resolved_pinned)
                sent0 = {t: sha256_file(sbB / t) for t in resolved_pinned if (sbB / t).exists()}
                rB = run_tool(sbB, rel)
                sent1 = {t: (sha256_file(sbB / t) if (sbB / t).exists() else None) for t in resolved_pinned}
                replaced = [t for t in sent0 if sent1.get(t) != sent0[t]]
                dyn["sentinel"].append({"tool": rel, "targets": resolved_pinned,
                                        "sentinel_sha": sent0, "post_sha": sent1,
                                        "sentinel_replaced": replaced,
                                        "sentinel_kept": [t for t in sent0 if t not in replaced],
                                        "run": rB})
        # ---- canonical containment: after
        canon_after = {p: (sha256_file(ROOT / p) if (ROOT / p).exists() else None) for p in pinned}
        drift = [p for p in pinned if canon_before[p] != canon_after[p]]
        dyn["canonical_pins_before"] = canon_before
        dyn["canonical_pins_after"] = canon_after
        dyn["canonical_drift"] = drift
        dyn["canonical_containment_ok"] = not drift
        dyn["digest"] = canonical_digest({k: dyn[k] for k in ("runs", "sentinel", "canonical_drift")})
        (OUTDIR / "dynamic.json").write_text(json.dumps(dyn, indent=1) + "\n")

    if args.phase in ("controls", "all"):
        if "static" not in result:
            result["static"] = json.loads((OUTDIR / "census.json").read_text())["static"]
        ctl = {"task": TASK, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        # CT5 known-answer: the classifier must find the two documented unguarded writers,
        # must find no write primitive in the read-only verifier, and must see required args.
        ka = {Path(t["tool"]).name: t for t in result["static"]}
        ct5 = {
            "check_variant_deltas_L33_unguarded": any(
                s["line"] == 33 and s["classification"] == "UNGUARDED_PINNED"
                for s in ka.get("check_variant_deltas.py", {}).get("write_sites", [])),
            "check_taxonomy_consistency_L80_unguarded": any(
                s["line"] == 80 and s["classification"] == "UNGUARDED_PINNED"
                for s in ka.get("check_taxonomy_consistency.py", {}).get("write_sites", [])),
            "verify_frozen_zero_write_sites": len(ka.get("verify_frozen.py", {}).get("write_sites", [])) == 0,
            "regenerate_frozen_requires_args": bool(ka.get("regenerate_frozen.py", {}).get("required_args_present")),
        }
        ct5["pass"] = all(v for k, v in ct5.items() if k != "pass")
        ctl["CT5_known_answer_static"] = ct5
        # CT2 detector false positive: no run -> nothing changes
        sb = build_sandbox("CTL_noop")
        d = diff_snapshots(snapshot(sb, pinned), snapshot(sb, pinned))
        ctl["CT2_false_positive_no_run"] = {"mutated": d["mutated_bytes"],
                                            "rewritten": d["rewritten_identical"],
                                            "pass": not d["mutated_bytes"] and not d["rewritten_identical"]}
        # CT3 detector true positive: a one-byte mutation in a mirrored pinned path is caught
        victim = "artifacts/formulation/KEY_MANIFEST.json"
        sb = build_sandbox("CTL_touch")
        s0 = snapshot(sb, pinned)
        (sb / victim).write_bytes((sb / victim).read_bytes() + b"#CTL\n")
        d = diff_snapshots(s0, snapshot(sb, pinned))
        ctl["CT3_true_positive_mutation"] = {"victim": victim, "mutated": d["mutated_bytes"],
                                             "pass": victim in d["mutated_bytes"]}
        # CT6 negative tool control: the read-only verifier runs clean in a pristine sandbox
        sb = build_sandbox("CTL_verify_frozen")
        s0 = snapshot(sb, pinned)
        r = run_tool(sb, "artifacts/formulation/tools/verify_frozen.py")
        d = diff_snapshots(s0, snapshot(sb, pinned))
        ctl["CT6_readonly_tool_verify_frozen"] = {
            "exit": r["exit"], "mutated": d["mutated_bytes"], "rewritten": d["rewritten_identical"],
            "pass": r["exit"] == 0 and not d["mutated_bytes"] and not d["rewritten_identical"]}
        # CT7 sentinel persistence without a run (the probe does not self-trigger)
        sb = build_sandbox("CTL_sentinel", sentinel_targets=[victim])
        ctl["CT7_sentinel_persists_without_run"] = {
            "victim": victim, "ends_with_sentinel": (sb / victim).read_bytes().endswith(SENTINEL),
            "pass": (sb / victim).read_bytes().endswith(SENTINEL)}
        # CT1 canonical containment around the control phase
        ca = {p: (sha256_file(ROOT / p) if (ROOT / p).exists() else None) for p in pinned}
        ctl["CT1_canonical_containment"] = {"drift": [p for p in pinned if canon_before[p] != ca[p]],
                                            "pass": all(canon_before[p] == ca[p] for p in pinned)}
        ctl["all_pass"] = all(v.get("pass") for k, v in ctl.items() if isinstance(v, dict) and "pass" in v)
        (OUTDIR / "controls.json").write_text(json.dumps(ctl, indent=1) + "\n")

    print("census done", result.get("static_digest", ""),
          len(result.get("static_unguarded_pinned_sites", [])), "unguarded pinned sites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
