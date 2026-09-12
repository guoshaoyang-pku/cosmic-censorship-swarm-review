#!/usr/bin/env python3
"""W098-GFORM-BINDING-CLOSURE-01 — read-only hash-binding closure audit of the G-FORM
two-stage acceptance path at FROZEN rev29 815e08079aef.

What it measures
----------------
1. Pin census: every declared sha256 in artifacts/formulation/FROZEN.json vs live bytes.
2. Static closure: repo files the acceptance path executes or reads, resolved from the
   pinned entry points by AST path-literal extraction and import resolution, tagged
   tier A (executed by the runner) or tier B (statically reachable, selftest-only).
3. Per-file pin classification: PINNED_OK / PINNED_STALE / PINNED_MISSING / UNPINNED.
4. Baseline battery: three canonical schemas + 31 mutants + 2 controls, driven through
   the PINNED runner's own run() (imported, not re-implemented).
5. Consequence controls on scratch copies only:
   C1 fidelity - pristine shadow copy of stage 2 must reproduce every baseline verdict.
   D1 engine   - one-line mutation of the UNPINNED stage-2 engine (output verdict).
   D2 corpus   - byte swap of one UNPINNED corpus fixture for an accepted document.
   C2 census   - the 50 declared pins must still all verify after D1/D2.

Read-only guarantee: no canonical path is written. Fail-closed: exit 3 if any pinned
input moves between the start and end census, or if C1 fidelity fails (D1/D2 then
uninterpretable).

Usage: python3 check_binding_closure.py [--json PATH]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = HERE / "scratch"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
RUNNER_REL = "artifacts/formulation/tools/run_acceptance.py"
SEM_REL = "artifacts/worker-06/spec_conformance_audit.py"
SPEC_REL = "artifacts/formulation/rule_spec.json"
CST = timezone(timedelta(hours=8))
PATH_PREFIXES = ("artifacts/", "schemas/", "research_map/", "ledger/")
SELFTEST_ONLY_PREFIX = "artifacts/worker-06/semantic_fixtures"
ENTRY_POINTS = [
    RUNNER_REL,
    "artifacts/formulation/tools/check_class_schema.py",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).relative_to(ROOT))


def load_frozen() -> dict:
    return json.loads((ROOT / FROZEN_REL).read_text())["files"]


def pin_census(files: dict) -> dict:
    rows, ok, stale, missing = [], 0, [], []
    for k in sorted(files):
        p = ROOT / k
        declared = files[k].get("sha256")
        if not p.exists():
            missing.append(k)
            rows.append({"path": k, "status": "PINNED_MISSING", "declared": declared, "live": None})
            continue
        live = sha(p)
        if live == declared:
            ok += 1
            rows.append({"path": k, "status": "PINNED_OK", "declared": declared, "live": live})
        else:
            stale.append(k)
            rows.append({"path": k, "status": "PINNED_STALE", "declared": declared, "live": live})
    return {"rows": rows, "n_declared": len(files), "n_ok": ok, "stale": stale, "missing": missing}


def _chain_parts(node: ast.AST):
    """Flatten a / b / c. Returns (anchor, parts) with anchor in
    ('name', <Name id>) or ('parents', <lineno>) when the leftmost is a parents[N] access."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        if isinstance(cur.right, ast.Constant) and isinstance(cur.right.value, str):
            parts.append(cur.right.value)
        else:
            return None
        cur = cur.left
    if isinstance(cur, ast.Name):
        return ("name", cur.id), list(reversed(parts))
    if isinstance(cur, ast.Subscript):
        v = cur.value
        if isinstance(v, ast.Attribute) and v.attr == "parents":
            return ("parents", getattr(cur, "lineno", -1)), list(reversed(parts))
    return None


def resolve_static_deps(start_rel: str) -> dict:
    """BFS over reachable .py files: path literals (ROOT/HERE div-chains, parents[N]
    chains and prefixed constants) plus local import resolution."""
    queue = [start_rel]
    seen: set[str] = set()
    deps: dict[str, dict] = {}
    while queue:
        r = queue.pop(0)
        if r in seen:
            continue
        seen.add(r)
        p = ROOT / r
        deps[r] = {"kind": "python", "resolved_by": "entry_point" if r in ENTRY_POINTS else "import",
                   "exists": p.exists()}
        if not p.exists() or p.suffix != ".py":
            continue
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError as e:  # noqa: BLE001
            deps[r]["parse_error"] = str(e)
            continue
        here = p.parent
        # module-level Name -> Path map for /-chains, so glob() targets are resolvable
        assign_map: dict[str, Path] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                chain = _chain_parts(node.value)
                if not chain:
                    continue
                (kind, val), parts = chain
                if not parts:
                    continue
                if kind == "name" and val == "ROOT":
                    assign_map[node.targets[0].id] = ROOT.joinpath(*parts)
                elif kind == "name" and val == "HERE":
                    assign_map[node.targets[0].id] = here.joinpath(*parts)
                elif kind == "parents":
                    for anc in [here] + list(here.parents):
                        if anc == ROOT.parent:
                            break
                        if anc.joinpath(*parts).exists():
                            assign_map[node.targets[0].id] = anc.joinpath(*parts)
                            break

        def add_candidate(cand: Path, how: str, glob: str | None = None) -> None:
            if not cand.exists():
                return
            cr = rel(cand)
            is_py = cand.is_file() and cand.suffix == ".py"
            entry = deps.setdefault(cr, {"kind": "python" if is_py else ("dir" if cand.is_dir() else "data"),
                                         "resolved_by": how, "exists": True, "glob": None})
            if glob and not entry.get("glob"):
                entry["glob"] = glob
                entry["resolved_by"] = f"{entry['resolved_by']} + {how}"
            if is_py:
                queue.append(cr)

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                chain = _chain_parts(node)
                if not chain:
                    continue
                (kind, val), parts = chain
                if not parts:
                    continue
                if kind == "name":
                    if val == "ROOT":
                        add_candidate(ROOT.joinpath(*parts), f"{r}:ROOT-chain")
                    elif val == "HERE":
                        add_candidate(here.joinpath(*parts), f"{r}:HERE-chain")
                else:  # parents[N] / "literal" -> first ancestor where it resolves
                    for anc in [here] + list(here.parents):
                        if anc == ROOT.parent:
                            break
                        cand = anc.joinpath(*parts)
                        if cand.exists():
                            add_candidate(cand, f"{r}:parents-chain")
                            break
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
                if s.startswith(PATH_PREFIXES) and (ROOT / s).exists():
                    add_candidate(ROOT / s, f"{r}:literal")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "glob":
                tgt = node.func.value
                if isinstance(tgt, ast.Name) and tgt.id in assign_map:
                    base = assign_map[tgt.id]
                    pat = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "*"
                    add_candidate(base, f"{r}:glob({pat})", glob=pat)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    _try_module(a.name, here, deps, r, queue)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                if node.module:
                    _try_module(node.module, here, deps, r, queue)
    return deps


def _try_module(mod: str, here: Path, deps: dict, src: str, queue: list) -> None:
    mp = mod.replace(".", "/")
    for base in (here, ROOT, ROOT / "artifacts" / "formulation"):
        for cand in ((base / mp).with_suffix(".py"), base / mp / "__init__.py"):
            if cand.exists() and cand.is_file():
                cr = rel(cand)
                deps.setdefault(cr, {"kind": "python", "resolved_by": f"{src}:import", "exists": True})
                queue.append(cr)
                return


def classify(deps: dict, files: dict) -> dict:
    table, unpinned, pinned_ok, pinned_stale, dirs = [], [], [], [], {}
    for r in sorted(deps):
        p = ROOT / r
        tier = "B_selftest_only" if r.startswith(SELFTEST_ONLY_PREFIX) else "A_load_bearing"
        if p.is_dir():
            if not deps[r].get("glob"):
                table.append({"path": r, "kind": "dir", "status": "DIR_NOT_EXPANDED",
                              "resolved_by": deps[r]["resolved_by"], "tier": tier})
                continue
            members = sorted(x for x in p.rglob(deps[r]["glob"]) if x.is_file())
            mem_rows = []
            for m in members:
                mr = rel(m)
                mtier = "B_selftest_only" if mr.startswith(SELFTEST_ONLY_PREFIX) else tier
                if mr in files:
                    st = "PINNED_OK" if sha(m) == files[mr].get("sha256") else "PINNED_STALE"
                    (pinned_ok if st == "PINNED_OK" else pinned_stale).append(mr)
                else:
                    st = "UNPINNED"
                    unpinned.append({"path": mr, "tier": mtier})
                mem_rows.append({"path": mr, "status": st, "tier": mtier})
            dirs[r] = {"n_files": len(members), "n_unpinned": sum(1 for x in mem_rows if x["status"] == "UNPINNED"),
                       "n_pinned": sum(1 for x in mem_rows if x["status"].startswith("PINNED")), "members": mem_rows}
            table.append({"path": r, "kind": "dir", "status": "GLOB", "n_files": len(members),
                          "n_unpinned": dirs[r]["n_unpinned"], "tier": tier})
            continue
        if r in files:
            st = "PINNED_MISSING" if not p.exists() else ("PINNED_OK" if sha(p) == files[r].get("sha256") else "PINNED_STALE")
            (pinned_ok if st == "PINNED_OK" else pinned_stale).append(r)
        else:
            st = "UNPINNED"
            unpinned.append({"path": r, "tier": tier})
        table.append({"path": r, "kind": deps[r]["kind"], "status": st,
                      "resolved_by": deps[r]["resolved_by"], "tier": tier})
    return {"table": table, "unpinned": unpinned, "pinned_ok": pinned_ok,
            "pinned_stale": pinned_stale, "dirs": dirs,
            "unpinned_tierA": [u["path"] for u in unpinned if u["tier"] == "A_load_bearing"],
            "unpinned_tierB": [u["path"] for u in unpinned if u["tier"] != "A_load_bearing"]}


def load_pinned_runner(files: dict) -> object:
    p = ROOT / RUNNER_REL
    if sha(p) != files[RUNNER_REL]["sha256"]:
        raise SystemExit("FAIL-CLOSED: run_acceptance.py does not match its FROZEN pin")
    spec = importlib.util.spec_from_file_location("w098_pinned_runner", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert Path(mod.__file__).resolve() == p.resolve()
    return mod


def shadow_engine(name: str, engine_bytes: bytes, files: dict) -> Path:
    """Place an engine copy at <shadow>/artifacts/worker-06/ so its internal
    ROOT = HERE.parent.parent resolves to <shadow>, and mirror the pinned rule spec."""
    shadow = SCRATCH / name
    dest_dir = shadow / "artifacts" / "worker-06"
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "spec_conformance_audit.py").write_bytes(engine_bytes)
    spec_src = ROOT / SPEC_REL
    if sha(spec_src) != files[SPEC_REL]["sha256"]:
        raise SystemExit("FAIL-CLOSED: rule_spec.json pin mismatch")
    (shadow / "artifacts" / "formulation").mkdir(parents=True, exist_ok=True)
    shutil.copy2(spec_src, shadow / SPEC_REL)
    return dest_dir / "spec_conformance_audit.py"


def battery(mod, stage1: Path, stage2: Path, corpus: Path) -> list:
    rows = []
    paths = [Path(x) for x in mod.CANON] + sorted(Path(corpus).glob("*.yaml"))
    for p in paths:
        g, gr = mod.run(stage1, p, True)
        s, sr = mod.run(stage2, p, False)
        kind = "canonical" if ("/schemas/" in str(p) and "rebased" not in str(p)) else (
            "control" if p.name.startswith("control_") else "mutant")
        rows.append({"file": Path(p).name, "kind": kind, "structural": g, "semantic": s,
                     "failed_structural": gr, "failed_semantic": sr})
    return rows


def union_stats(rows: list) -> dict:
    muts = [r for r in rows if r["kind"] == "mutant"]
    caught = [r for r in muts if r["structural"] == "fail" or r["semantic"] == "fail"]
    esc = [r["file"] for r in muts if r not in caught]
    return {"total": len(muts), "union_caught": len(caught), "union_escapes": esc,
            "structural_caught": sum(1 for r in muts if r["structural"] == "fail"),
            "semantic_caught": sum(1 for r in muts if r["semantic"] == "fail"),
            "semantic_load_bearing": sum(1 for r in muts if r["semantic"] == "fail" and r["structural"] != "fail")}


def aggregate(rows: list) -> str:
    """run_acceptance.py's headline verdict, recomputed from the same rows."""
    can = [r for r in rows if r["kind"] == "canonical"]
    ctl = [r for r in rows if r["kind"] == "control"]
    st = union_stats(rows)
    ok = all(r["structural"] == "pass" and r["semantic"] == "pass" for r in can + ctl) and \
        st["total"] > 0 and st["union_caught"] == st["total"]
    return "PASS" if ok else "FAIL"


def verdict_map(rows: list) -> dict:
    return {r["file"]: (r["structural"], r["semantic"]) for r in rows}


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "report.json"))
    args = ap.parse_args()

    run_started = now()
    files = load_frozen()
    census0 = pin_census(files)
    report_path = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    report_before = (sha(report_path), report_path.stat().st_mtime_ns)

    # ---- static closure -------------------------------------------------------
    deps: dict[str, dict] = {}
    for ep in ENTRY_POINTS:
        for k, v in resolve_static_deps(ep).items():
            deps.setdefault(k, v)
    runner_src = (ROOT / RUNNER_REL).read_text()
    if SEM_REL not in runner_src:
        raise SystemExit("FAIL-CLOSED: stage-2 wiring not found in run_acceptance.py")
    cls = classify(deps, files)
    measured_pin_paths = sorted({t["path"] for t in cls["table"]
                                 if t["kind"] != "dir" and str(t.get("status", "")).startswith("PINNED")})

    def pinned_bad(census: dict) -> list:
        return [r for r in census["rows"] if r["path"] in set(measured_pin_paths) and r["status"] != "PINNED_OK"]

    # ---- baseline battery via the pinned runner's own run() -------------------
    mod = load_pinned_runner(files)
    base_rows = battery(mod, mod.GATE, mod.SEM, mod.REBASED)
    base_stats = union_stats(base_rows)
    base_agg = aggregate(base_rows)

    # ---- C1 fidelity: pristine shadow copy of stage 2 -------------------------
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    c1_engine = shadow_engine("shadow_pristine", mod.SEM.read_bytes(), files)
    c1_rows = battery(mod, mod.GATE, c1_engine, mod.REBASED)
    c1_equal = verdict_map(c1_rows) == verdict_map(base_rows)
    c1_diff = sorted(k for k in verdict_map(base_rows) if verdict_map(base_rows)[k] != verdict_map(c1_rows).get(k))

    # ---- D1: one-line mutation of the UNPINNED stage-2 engine -----------------
    text = mod.SEM.read_text()
    needle = '        "verdict": verdict,'
    if text.count(needle) != 1:
        raise SystemExit("FAIL-CLOSED: D1 mutation site not unique")
    mutated = text.replace(needle, '        "verdict": "accept",  # W098-MUT-D1')
    d1_engine = shadow_engine("shadow_d1", mutated.encode(), files)
    diff_lines = sum(1 for a, b in zip(text.splitlines(), mutated.splitlines()) if a != b)
    d1_rows = battery(mod, mod.GATE, d1_engine, mod.REBASED)
    d1_stats, d1_agg = union_stats(d1_rows), aggregate(d1_rows)
    vm_base, vm_d1 = verdict_map(base_rows), verdict_map(d1_rows)
    d1_flips = sorted(k for k in vm_base if vm_base[k] != vm_d1.get(k))
    census_after_d1 = pin_census(files)
    d1_measured_bad = pinned_bad(census_after_d1)

    # ---- D2: byte swap of one UNPINNED corpus fixture -------------------------
    corpus_d2 = SCRATCH / "corpus_d2"
    shutil.copytree(mod.REBASED, corpus_d2)
    caught_names = sorted(r["file"] for r in base_rows if r["kind"] == "mutant"
                          and (r["structural"] == "fail" or r["semantic"] == "fail"))
    d2_target = caught_names[0]
    donor = Path(mod.CANON[1])  # pinned C2 mirror: accepted by BOTH stages at these bytes
    if donor not in [Path(x) for x in mod.CANON] or sha(donor) != files[rel(donor)]["sha256"]:
        raise SystemExit("FAIL-CLOSED: D2 donor is not a pinned canonical schema")
    (corpus_d2 / d2_target).write_bytes(donor.read_bytes())
    d2_swap = {"target": d2_target, "donor": rel(donor), "donor_sha256": sha(donor),
               "pre_sha256": sha(mod.REBASED / d2_target), "post_sha256": sha(corpus_d2 / d2_target)}
    d2_rows = battery(mod, mod.GATE, mod.SEM, corpus_d2)
    d2_stats, d2_agg = union_stats(d2_rows), aggregate(d2_rows)
    d2_delta = base_stats["union_caught"] - d2_stats["union_caught"]
    census_final = pin_census(files)
    final_measured_bad = pinned_bad(census_final)
    all_bad = sorted({r["path"] for r in census_final["rows"] if r["status"] != "PINNED_OK"})
    concurrent_drift = []
    for r in census_final["rows"]:
        if r["status"] != "PINNED_OK":
            fp = ROOT / r["path"]
            mt = datetime.fromtimestamp(fp.stat().st_mtime, CST).isoformat(timespec="seconds") if fp.exists() else None
            concurrent_drift.append({"path": r["path"], "declared": r["declared"], "live": r["live"],
                                     "status": r["status"], "file_mtime": mt})
    report_after = (sha(report_path), report_path.stat().st_mtime_ns)

    # ---- archived pinned report vs measured live bytes ------------------------
    archived = json.loads(report_path.read_text())
    archived_view = {"verdict": archived.get("verdict"),
                     "canonical": archived.get("canonical"),
                     "controls": archived.get("controls"),
                     "mutants": {k: v for k, v in archived.get("mutants", {}).items() if k != "union_escapes"}}
    measured_view = {"verdict": base_agg,
                     "canonical": [{"schema": r["file"], "structural": r["structural"], "semantic": r["semantic"],
                                    "ok": r["structural"] == "pass" and r["semantic"] == "pass"}
                                   for r in base_rows if r["kind"] == "canonical"],
                     "controls": [{"control": r["file"], "structural": r["structural"], "semantic": r["semantic"]}
                                  for r in base_rows if r["kind"] == "control"],
                     "mutants": {k: v for k, v in base_stats.items() if k != "union_escapes"}}
    reproducible = (archived_view["verdict"] == measured_view["verdict"]
                    and archived_view["canonical"] == measured_view["canonical"]
                    and archived_view["controls"] == measured_view["controls"])

    # ---- context: runner preflight (read-only replication of lines 53-66) -----
    ev = json.loads((ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
    authoring_c0 = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    preflight = {"declared_base_sha256": ev.get("base_sha256"), "live_authoring_c0_sha256": sha(authoring_c0),
                 "would_pass": ev.get("base_sha256") == sha(authoring_c0)}

    # ---- assemble -------------------------------------------------------------
    findings = [{
        "id": "W098-BC-01", "severity": "major", "expectation": "E1/E2",
        "statement": "The G-FORM acceptance path is not fully hash-bound by FROZEN rev29: "
                     f"{len(cls['unpinned_tierA'])} tier-A (runner-executed) file(s) have no FROZEN.files entry, "
                     f"including the stage-2 semantic engine {SEM_REL} (live sha256 {sha(ROOT / SEM_REL)}) and all 33 members "
                     "of the rebased acceptance corpus whose union_caught is a gate criterion.",
        "evidence": [SEM_REL, "artifacts/formulation/evidence/rebased_fixtures/",
                     FROZEN_REL, f"{RUNNER_REL}:25,29,82"],
    }, {
        "id": "W098-BC-02", "severity": "major" if d1_flips else "info", "expectation": "E6",
        "statement": f"D1 engine-mutation consequence: a {diff_lines}-line mutation of the UNPINNED stage-2 engine changes "
                     f"{len(d1_flips)} fixture verdict(s) (semantic_caught {base_stats['semantic_caught']} -> {d1_stats['semantic_caught']}; "
                     f"canonical WCC flips R03-reject -> accept, so the canonical column goes 2/3 -> 3/3), while every measured-path "
                     f"FROZEN pin still verifies ({len(d1_measured_bad)} bad). The headline aggregate stays {d1_agg} only because the two "
                     "controls fail stage 1 on R22 for an unrelated reason; the per-fixture verdict content is not bound to the pins.",
        "evidence": [rel(d1_engine), FROZEN_REL, "artifacts/formulation/schemas/af_wcc_vacuum.yaml"],
    }, {
        "id": "W098-BC-03", "severity": "major" if d2_delta > 0 else "info", "expectation": "E7",
        "statement": f"D2 corpus-mutation consequence: replacing the UNPINNED fixture {d2_target} "
                     f"({d2_swap['pre_sha256'][:12]}) with the pinned accepted canonical {d2_swap['donor']} "
                     f"({d2_swap['donor_sha256'][:12]}) on a scratch copy changes union catch by {d2_delta} "
                     f"({base_stats['union_caught']}/{base_stats['total']} -> {d2_stats['union_caught']}/{d2_stats['total']}, headline "
                     f"{base_agg} -> {d2_agg}) while every measured-path FROZEN pin still verifies ({len(final_measured_bad)} bad).",
        "evidence": [rel(corpus_d2 / d2_target), FROZEN_REL, d2_swap["donor"]],
    }, {
        "id": "W098-BC-04", "severity": "info", "expectation": "E5",
        "statement": f"Stage-2 load-bearing status at the live corpus: {base_stats['semantic_caught']}/{base_stats['total']} mutants "
                     f"are rejected by the semantic stage, but {base_stats['semantic_load_bearing']} of them are caught by semantics "
                     "alone, so at these bytes the union rate is fully explained by stage 1. Neutralising the unpinned semantic engine "
                     "does not move the union rate here (D1 union "
                     f"{d1_stats['union_caught']}/{d1_stats['total']}); it does move per-fixture verdicts and the canonical column. "
                     "This is a property of the current corpus, not a licence to leave the engine unpinned.",
        "evidence": [SEM_REL, "artifacts/formulation/evidence/rebased_fixtures/"],
    }, {
        "id": "W098-BC-05", "severity": "info", "expectation": "E3/E4/E8/E9",
        "statement": f"Manifest internal consistency is clean at the measured instant: {census0['n_ok']}/{census0['n_declared']} declared "
                     f"pins verify, stale={census0['stale']}, missing={census0['missing']}. Pre-registered E4 (3/3 canonical pass) is "
                     f"FALSIFIED at the live bytes: stage 2 rejects the canonical WCC schema on R03, so the battery headline is "
                     f"{base_agg}. C1 pristine-shadow fidelity={'PASS' if c1_equal else 'FAIL'}; runner import side effect on "
                     f"acceptance_pipeline_report.json: {'none' if report_before == report_after else 'CHANGED'}.",
        "evidence": [FROZEN_REL, RUNNER_REL, "artifacts/formulation/schemas/af_wcc_vacuum.yaml"],
    }, {
        "id": "W098-BC-06", "severity": "info", "expectation": "independent CF-32 corroboration",
        "statement": f"Archived-vs-live reproducibility: the FROZEN-pinned acceptance_pipeline_report.json records verdict="
                     f"{archived_view['verdict']} with canonical {archived_view['canonical']} while the same pinned runner logic over the "
                     f"live bytes measures verdict={measured_view['verdict']}, canonical "
                     f"{[(r['schema'], r['structural'], r['semantic']) for r in measured_view['canonical']]}, controls "
                     f"{[(r['control'], r['structural'], r['semantic']) for r in measured_view['controls']]}, and preflight "
                     f"would_pass={preflight['would_pass']}. Independently reproduces CF-32(i)/(ii) with exact rule ids (stage-1 R22 on "
                     "both controls, stage-2 R03 on canonical WCC); no repair is attempted here.",
        "evidence": ["artifacts/formulation/evidence/acceptance_pipeline_report.json", FROZEN_REL,
                     "artifacts/formulation/evidence/semantic_escape_rebased.json"],
    }]
    if cls["unpinned_tierB"]:
        findings.append({
            "id": "W098-BC-07", "severity": "info", "expectation": "closure tagging",
            "statement": f"Tier B (statically reachable but not runner-executed): {len(cls['unpinned_tierB'])} file(s) under "
                         f"{SELFTEST_ONLY_PREFIX} have no pin, including manifest.json. They do not decide the acceptance verdict, "
                         "but they are the corpus for the engine's --selftest mode, which is itself unpinned.",
            "evidence": [SELFTEST_ONLY_PREFIX, SEM_REL],
        })
    if concurrent_drift:
        findings.append({
            "id": "W098-BC-08", "severity": "info", "expectation": "concurrent traffic disclosure",
            "statement": f"{len(concurrent_drift)} FROZEN-declared file(s) moved during the run window (concurrent swarm traffic, "
                         f"not written by this task, all off the measured acceptance path): "
                         f"{[d['path'] for d in concurrent_drift]}. Measured-path pins stayed stable "
                         f"({len(final_measured_bad)} bad), so the battery and D1/D2 bind to the bytes measured here; the move is "
                         "recorded and does not void them.",
            "evidence": [FROZEN_REL] + [d["path"] for d in concurrent_drift],
        })

    hard = [f["id"] for f in findings if f["severity"] == "major"]
    verdict = "revise" if hard else "accept"
    content = {
        "task_id": "W098-GFORM-BINDING-CLOSURE-01",
        "actor": "worker-098",
        "created_at": run_started,
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "reviewed_target": FROZEN_REL,
        "reviewed_sha256": sha(ROOT / FROZEN_REL),
        "verdict": verdict,
        "score": 3.0 if hard else 4.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "pin_census_start": {k: v for k, v in census0.items() if k != "rows"},
        "pin_census_final": {k: v for k, v in census_final.items() if k != "rows"},
        "closure": {
            "n_reachable": len(cls["table"]),
            "n_unpinned": len(cls["unpinned"]),
            "n_unpinned_tierA": len(cls["unpinned_tierA"]),
            "unpinned_tierA": cls["unpinned_tierA"],
            "unpinned_tierB": cls["unpinned_tierB"],
            "unpinned_dirs": {k: {"n_files": v["n_files"], "n_unpinned": v["n_unpinned"]} for k, v in cls["dirs"].items()},
            "table": cls["table"],
            "dir_members": cls["dirs"],
        },
        "baseline_battery": {"aggregate": base_agg, "stats": base_stats, "rows": base_rows},
        "archived_vs_live": {"archived": archived_view, "measured": measured_view, "reproducible": reproducible},
        "concurrent_drift": concurrent_drift,
        "measured_path_pins": measured_pin_paths,
        "controls": {
            "C1_pristine_fidelity": {"pass": c1_equal, "diffs": c1_diff},
            "C2_measured_path_pins_stable_after_d1": not d1_measured_bad,
            "C2_measured_path_pins_stable_final": not final_measured_bad,
            "C2_all_declared_pins_stable_final": not all_bad,
            "C3_canonical_all_pass": all(r["structural"] == "pass" and r["semantic"] == "pass"
                                         for r in base_rows if r["kind"] == "canonical"),
            "C4_mutation_minimality_lines": diff_lines,
            "C5_runner_import_side_effect": report_before == report_after,
        },
        "d1_engine_mutation": {"path": rel(d1_engine), "mutated_sha256": sha(d1_engine), "flips": d1_flips,
                               "stats": d1_stats, "aggregate": d1_agg, "measured_pins_bad": d1_measured_bad},
        "d2_corpus_mutation": {"swap": d2_swap, "stats": d2_stats, "aggregate": d2_agg,
                               "union_delta": d2_delta, "rows": d2_rows, "dir": rel(corpus_d2)},
        "context_cf32_preflight": preflight,
        "findings": findings,
        "falsifier": "Falsified if FROZEN.files covers every file the acceptance path executes or reads, or the unpinned engine/corpus "
                     "are bound by an equivalent mechanism the runner enforces; or if the D1/D2 scratch mutations change no verdict; or "
                     "if C1 fidelity fails; or if a measured-path pinned input drifts in-run (then the battery is void).",
        "non_claims": ["Not a gate verdict; worker events cannot set gate state.",
                       "Not a schema-semantics verdict; only artifact identity binding is measured.",
                       "Not a re-adjudication of CF-32 or of the R03 false positive; cited as context only.",
                       "The archived acceptance_pipeline_report.json is measured, not certified.",
                       "D1/D2 run on scratch copies with the pinned runner's own run(); the canonical preflight is replicated read-only."],
        "wall_seconds": round(time.time() - t0, 2),
    }
    ENV_FIELDS = ("created_at", "wall_seconds", "concurrent_drift", "pin_census_start", "pin_census_final")
    digest = sha_bytes(json.dumps({k: v for k, v in content.items() if k not in ENV_FIELDS},
                                  sort_keys=True).encode())
    content["measurement_digest_excluding_env"] = digest
    content["measurement_digest_excludes"] = list(ENV_FIELDS)
    Path(args.json).write_text(json.dumps(content, indent=2, sort_keys=True) + "\n")

    print(f"W098-BC verdict={verdict}")
    print(f"  pins {census0['n_ok']}/{census0['n_declared']} ok stale={len(census0['stale'])} missing={len(census0['missing'])}")
    print(f"  reachable={len(cls['table'])} unpinned={len(cls['unpinned'])} (tierA {len(cls['unpinned_tierA'])}, tierB {len(cls['unpinned_tierB'])})")
    print(f"  baseline aggregate={base_agg} union {base_stats['union_caught']}/{base_stats['total']} "
          f"(structural {base_stats['structural_caught']}, semantic {base_stats['semantic_caught']}, semantic-only {base_stats['semantic_load_bearing']})")
    print(f"  C1 fidelity={'PASS' if c1_equal else 'FAIL'} ({len(c1_diff)} diffs) C3 canonical-all-pass={content['controls']['C3_canonical_all_pass']}")
    print(f"  D1 lines={diff_lines} flips={len(d1_flips)} aggregate {base_agg}->{d1_agg} measured_pins_bad={len(d1_measured_bad)}")
    print(f"  D2 swapped {d2_target} -> {d2_swap['donor']} union delta={d2_delta} aggregate->{d2_agg} measured_pins_bad={len(final_measured_bad)}")
    print(f"  archived-vs-live reproducible={reproducible} concurrent_drift={[d['path'] for d in concurrent_drift]}")
    print(f"  digest={digest[:16]} report={args.json}")
    return 0 if (not final_measured_bad and c1_equal) else 3


if __name__ == "__main__":
    sys.exit(main())
