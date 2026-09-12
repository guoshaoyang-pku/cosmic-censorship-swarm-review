#!/usr/bin/env python3
"""W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01.

Bound task: characterize, at pinned bytes, the binding rule the controller's
`astra_lifecycle.review_coverage` scan applies to `reviews/*.json`, measure the
live effect of that rule on the G-FORM classes F1 / F2a / F2b, and emit an
UNAPPLIED patch that closes the measured blind spots.

Method (read-only wrt every canonical path; writes only under this directory):

  1. Snapshot the pinned instrument `research_map/astra_lifecycle.py#957c61e3eb0e`
     and freeze a byte copy of the live `reviews/` corpus.
  2. Extract the exact source of `_targets_in_review`, `_explicit_pins` and
     `review_coverage` from the pinned snapshot with `ast` and execute them
     against a controlled ROOT. This tests the pinned bytes, not a rewrite.
  3. Run the same three functions against a synthetic fixture corpus whose cases
     mirror the target/pin forms actually present in the live corpus, with
     pre-registered expectations (R1 = pinned rule).
  4. Run R3 = the proposed patched rule (extracted the same way from the patched
     file emitted here) against the identical frozen corpus; diff the counts.
  5. Drop the patch as a unified diff. It is never applied to the canonical tree.

Exit is a worker-level report only: no gate verdict, no node transition, no
validation_status promotion.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INSTRUMENT_REL = "research_map/astra_lifecycle.py"
INSTRUMENT_PIN = "957c61e3eb0e5002a19f2959bff91d845e906ab90f2dc91c0b665aca0ede6a83"
SNAPSHOT = HERE / "snapshot" / f"astra_lifecycle.{INSTRUMENT_PIN[:12]}.py"
PATCHED = HERE / "proposed" / f"astra_lifecycle.{INSTRUMENT_PIN[:12]}.patched.py"
PATCH_DIFF = HERE / "proposed_patch.diff"
FIXTURE_ROOT = HERE / "fixtures"
LIVE_SNAPSHOT = HERE / "live_snapshot"
LIFECYCLE_REPORT_REL = "runtime/state/controller_verification/lifecycle_20260912-011029.json"
SCHEMA_PATHS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
HASHES_KEYS = ("F1", "F2a", "F2b")
CLASS_TARGETS = ("F1", "F2a", "F2b")

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def dir_digest(files) -> tuple:
    """(digest, {name: {sha256, bytes}}) over an explicit file list.

    Keyed by basename so a byte copy of a corpus digests identically.
    """
    man = {}
    h = hashlib.sha256()
    for p in sorted(files, key=lambda x: x.name):
        b = p.read_bytes()
        man[p.name] = {"sha256": sha256_bytes(b), "bytes": len(b)}
        h.update(p.name.encode() + b"\0" + sha256_bytes(b).encode() + b"\n")
    return h.hexdigest(), man


def freeze_corpus(files, dest: Path) -> tuple:
    """Copy each file's bytes exactly once and hash those same bytes.

    Returns (digest, manifest). Under concurrent writers a list-then-hash-then-copy
    pass can hash bytes that are rewritten before the copy; reading each file once
    makes the frozen corpus and its digest describe the same bytes by construction.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for f in dest.glob("*.json"):
        f.unlink()
    man = {}
    h = hashlib.sha256()
    for p in sorted(files, key=lambda x: x.name):
        b = p.read_bytes()
        (dest / p.name).write_bytes(b)
        man[p.name] = {"sha256": sha256_bytes(b), "bytes": len(b)}
        h.update(p.name.encode() + b"\0" + sha256_bytes(b).encode() + b"\n")
    return h.hexdigest(), man


def collect_hash_strings(v, out=None):
    """Recursively collect raw strings from str/dict/list values (R3 helper)."""
    if out is None:
        out = []
    if isinstance(v, str):
        out.append(v.lower())
    elif isinstance(v, dict):
        for vv in v.values():
            collect_hash_strings(vv, out)
    elif isinstance(v, list):
        for vv in v:
            collect_hash_strings(vv, out)
    return out


# --------------------------------------------------------------------------
# pinned-function extraction / execution
# --------------------------------------------------------------------------


def function_sources(path: Path) -> dict:
    text = path.read_text()
    tree = ast.parse(text)
    return {n.name: ast.get_source_segment(text, n)
            for n in tree.body if isinstance(n, ast.FunctionDef)}


def load_rule(instrument_path: Path, root: Path) -> dict:
    """Extract the three coverage functions from `instrument_path` and bind them
    to `root`. Runs the pinned bytes; no reimplementation."""
    text = instrument_path.read_text()
    tree = ast.parse(text)
    wanted_f = {"_targets_in_review", "_explicit_pins", "review_coverage", "_norm_targets"}
    wanted_c = {"TARGET_ALIASES", "TARGET_PATH_ALIASES", "VERDICT_KINDS"}
    seg, consts = {}, {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_f:
            seg[node.name] = ast.get_source_segment(text, node)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in wanted_c
        ):
            consts[node.targets[0].id] = ast.literal_eval(node.value)
    missing = {"_targets_in_review", "_explicit_pins", "review_coverage"} - set(seg)
    if missing:
        raise SystemExit(f"instrument {instrument_path} lacks functions: {sorted(missing)}")
    ns = {"json": json, "Path": Path, "re": re, "ROOT": root}
    ns.update(consts)
    ns["_collect_hash_strings"] = collect_hash_strings
    for name in ("_norm_targets", "_targets_in_review", "_explicit_pins"):
        if name in seg:
            exec(seg[name], ns)  # noqa: S102 - pinned source, read-only semantics
    exec(seg["review_coverage"], ns)  # noqa: S102
    ns["_source_sha256"] = sha256_file(instrument_path)
    return ns


def run_cov(ns: dict, corpus_root: Path, hashes: dict) -> dict:
    ns["ROOT"] = corpus_root
    return ns["review_coverage"](hashes)


def counted_map(cov: dict) -> dict:
    """file -> set of targets it is a FULL accept for (verdicts alone are not
    enough: scoped verdicts stay out of full_accepts)."""
    m = {}
    for t, c in cov.items():
        for e in c["full_accepts"]:
            m.setdefault(e["file"], set()).add(t)
    return m


def full_accepts(cov: dict) -> dict:
    return {t: {e["file"] for e in c["full_accepts"]} for t, c in cov.items()}


# --------------------------------------------------------------------------
# fixtures (forms mirror the live corpus census)
# --------------------------------------------------------------------------


def fixture_spec(hashes: dict) -> list:
    h1, h2a, h2b = hashes["F1"]["sha256"], hashes["F2a"]["sha256"], hashes["F2b"]["sha256"]
    P = "@PIN@"

    def mk(name, fields, expect_r1, expect_r3, note):
        return {
            "name": name,
            "file": f"{name}.json",
            "fields": fields,
            "expect_R1_full_accept_targets": expect_r1,
            "expect_R3_full_accept_targets": expect_r3,
            "note": note,
        }

    spec = [
        mk("01_baseline_alias_accept",
           {"reviewer": "fx", "target_id": "F2a", "reviewed_sha256": h2a,
            "verdict": "accept", "score": 4.0, "counts_as_full_schema_verdict": True},
           ["F2a"], ["F2a"], "positive control: exact alias + exact pin"),
        mk("02_uppercase_alias",
           {"reviewer": "fx", "target_id": "F2A", "reviewed_sha256": h2a,
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "TARGET_ALIASES upper-case fallback works in R1 and R3"),
        mk("03_classid_target",
           {"reviewer": "fx", "target_id": "AF-SCC-C2-VAC-GEN", "reviewed_sha256": h2a,
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "class-id target is aliased in R1"),
        mk("04_path_hash_target_short_fragment",
           {"reviewer": "fx", "target_id": f"schemas/af_scc_c2_vacuum.yaml#{h2a[:12]}",
            "reviewed_sha256": None, "verdict": "accept", "score": 4.0,
            "counts_as_full_schema_verdict": True},
           [], ["F2a"], "live form: path#hash target, pin only in the fragment (worker-018 shape)"),
        mk("05_path_hash_target_full_fragment",
           {"reviewer": "fx", "target_id": f"schemas/af_scc_c2_vacuum.yaml#{h2a}",
            "verdict": "accept", "score": 4.0},
           [], ["F2a"], "live form: path#full-hash target"),
        mk("06_bare_path_target_string_pin",
           {"reviewer": "fx", "target_id": "schemas/af_scc_c2_vacuum.yaml",
            "reviewed_sha256": h2a, "verdict": "accept", "score": 4.0},
           [], ["F2a"], "live form: bare schema path target with a correct explicit pin"),
        mk("07_dict_valued_pin",
           {"reviewer": "fx", "target_id": "F2a",
            "reviewed_sha256": {"schemas/af_scc_c2_vacuum.yaml": h2a},
            "verdict": "accept", "score": 4.0},
           [], ["F2a"], "live form: dict-valued reviewed_sha256 (7 such files)"),
        mk("08_at_hash_target",
           {"reviewer": "fx", "target_id": f"F2b@{h2b[:12]}",
            "reviewed_sha256": None, "verdict": "accept", "score": 4.0},
           [], ["F2b"], "live form: node@hash target (F2b@b2ab6acb2bbe ...)"),
        mk("09_multi_target_at_hash",
           {"reviewer": "fx", "target_id": f"F1@{h1[:12]}, F2a@{h2a[:12]}, F2b@{h2b[:12]}",
            "verdict": "accept", "score": 4.0},
           [], ["F1", "F2a", "F2b"], "live form: comma list of node@hash targets"),
        mk("10_class_id_field_only",
           {"reviewer": "fx", "class_id": "AF-SCC-C0-VAC-GEN", "reviewed_sha256": h2b,
            "verdict": "accept", "score": 4.0},
           [], ["F2b"], "class_id field is a legitimate binding absent from R1's key list"),
        mk("11_prose_hash_only",
           {"reviewer": "fx", "target_id": "F2a", "summary": f"reviewed at {h2a}",
            "verdict": "accept", "score": 4.0},
           [], [], "negative control: hash in prose is not a pin, both rules must drop"),
        mk("12_wrong_hash",
           {"reviewer": "fx", "target_id": "F2a", "reviewed_sha256": "de" * 32,
            "verdict": "accept", "score": 4.0},
           [], [], "negative control: wrong pin must not bind"),
        mk("13_prefix12_pin",
           {"reviewer": "fx", "target_id": "F2a", "reviewed_sha256": h2a[:12],
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "12-hex prefix pin is accepted by the pinned prefix rule"),
        mk("14_scoped_false_excluded",
           {"reviewer": "fx", "target_id": "F2a", "reviewed_sha256": h2a,
            "verdict": "accept", "score": 4.0, "counts_as_full_schema_verdict": False},
           [], [], "scoped verdicts stay out of full_accepts in both rules"),
        mk("15_absent_full_flag_defaults_full",
           {"reviewer": "fx", "target_id": "F2a", "reviewed_sha256": h2a,
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "null counts_as_full_schema_verdict is treated as full by both rules"),
        mk("16_nested_target_dict",
           {"reviewer": "fx", "target": {"target_subnode": {"node_id": "F2a"}},
            "reviewed_sha256": h2a, "verdict": "accept", "score": 4.0},
           [], ["F2a"], "nested dict target is dropped by R1, flattened by R3"),
        mk("17_target_dict_node_id",
           {"reviewer": "fx", "target": {"node_id": "F2a"}, "artifact_sha256": h2a,
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "flat dict target with node_id is found by R1"),
        mk("18_pin_only_in_target_dict",
           {"reviewer": "fx", "target_id": "F2a",
            "target": {"node_id": "F2a", "reviewed_sha256": h2a},
            "verdict": "accept", "score": 4.0},
           ["F2a"], ["F2a"], "dict-valued target carries a recognised sha256 key"),
    ]
    for case in spec:
        case["fields"] = json.loads(json.dumps(case["fields"]).replace(P, ""))
    return spec


def ensure_fixture_corpus(spec: list) -> None:
    d = FIXTURE_ROOT / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.json"):
        f.unlink()
    for case in spec:
        (d / case["file"]).write_text(json.dumps(case["fields"], indent=1) + "\n")
    (FIXTURE_ROOT / "expectations.json").write_text(
        json.dumps([{k: c[k] for k in ("name", "file", "expect_R1_full_accept_targets",
                                       "expect_R3_full_accept_targets", "note")}
                    for c in spec], indent=1) + "\n")


# --------------------------------------------------------------------------
# proposed patch (emitted, never applied)
# --------------------------------------------------------------------------

NEW_CONST = '''

# --- R3 proposal: path/<node>@hash target aliases (W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01)
TARGET_PATH_ALIASES = {
    "research_map/formulation_taxonomy.yaml": "F0",
    "artifacts/formulation/formulation_taxonomy.yaml": "F0",
    "schemas/af_wcc_vacuum.yaml": "F1",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "F1",
    "schemas/af_scc_c2_vacuum.yaml": "F2a",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "F2a",
    "schemas/af_scc_c0_vacuum.yaml": "F2b",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "F2b",
}


def _collect_hash_strings(v, out=None):
    """R3: recursively collect raw strings from str/dict/list values."""
    if out is None:
        out = []
    if isinstance(v, str):
        out.append(v.lower())
    elif isinstance(v, dict):
        for vv in v.values():
            _collect_hash_strings(vv, out)
    elif isinstance(v, list):
        for vv in v:
            _collect_hash_strings(vv, out)
    return out
'''

NEW_TARGETS = '''def _norm_targets(t: str) -> set:
    """R3: normalise one target string (including comma/semicolon lists and
    path#hash / node@hash forms) to node ids."""
    out = set()
    for piece in re.split(r"[,;]", t):
        piece = piece.strip()
        if not piece:
            continue
        if piece in TARGET_ALIASES:
            out.add(TARGET_ALIASES[piece])
            continue
        if piece.upper() in TARGET_ALIASES:
            out.add(TARGET_ALIASES[piece.upper()])
            continue
        base = piece.split("#", 1)[0].split("@", 1)[0].strip()
        if base in TARGET_ALIASES:
            out.add(TARGET_ALIASES[base])
            continue
        if base.upper() in TARGET_ALIASES:
            out.add(TARGET_ALIASES[base.upper()])
            continue
        if base in TARGET_PATH_ALIASES:
            out.add(TARGET_PATH_ALIASES[base])
            continue
        name = base.rsplit("/", 1)[-1]
        if name in TARGET_PATH_ALIASES:
            out.add(TARGET_PATH_ALIASES[name])
    return out


def _targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode", "class_id"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id", "class_id"):
                v2 = v.get(k2)
                if isinstance(v2, str):
                    out.add(v2)
                elif isinstance(v2, dict):
                    for k3 in ("target_id", "subnode", "node_id"):
                        if isinstance(v2.get(k3), str):
                            out.add(v2[k3])
    norm = set()
    for t in out:
        norm |= _norm_targets(t)
    return norm
'''

NEW_PINS = '''def _explicit_pins(d: dict) -> list:
    """R3: hashes a review explicitly pins (not hashes merely mentioned in prose).
    Adds recursive flattening of dict/list-valued pins, the recognised target
    sha256 keys, and hex fragments carried by target strings (# and @ forms)."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256",
                "target_sha256"):
        for s in _collect_hash_strings(d.get(key)):
            if re.fullmatch(r"[0-9a-f]{8,64}", s):
                pins.append(s)
            else:
                pins.extend(m.group(0) for m in re.finditer(r"[0-9a-f]{8,64}", s))
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                for s in _collect_hash_strings(v.get(k2)):
                    pins.extend(m.group(0) for m in re.finditer(r"[0-9a-f]{8,64}", s))
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            for part in re.split(r"[#,@\\s]+", v):
                if re.fullmatch(r"[0-9a-f]{8,64}", part):
                    pins.append(part)
    return pins
'''


def build_patch() -> tuple:
    text = SNAPSHOT.read_text()
    tree = ast.parse(text)
    spans, alias_end = {}, None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"_targets_in_review", "_explicit_pins"}:
            spans[node.name] = (node.lineno, node.end_lineno)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "TARGET_ALIASES"
        ):
            alias_end = node.end_lineno
    if set(spans) != {"_targets_in_review", "_explicit_pins"} or alias_end is None:
        raise SystemExit("patch build: expected spans not found in the pinned snapshot")
    lines = text.splitlines(keepends=True)
    for name in ("_explicit_pins", "_targets_in_review"):
        a, b = spans[name]
        body = NEW_PINS if name == "_explicit_pins" else NEW_TARGETS
        lines[a - 1:b] = [body]
    lines[alias_end:alias_end] = [NEW_CONST]
    patched = "".join(lines)
    ast.parse(patched)  # control: proposal must be syntactically valid Python
    PATCHED.write_text(patched)
    diff = "".join(difflib.unified_diff(
        text.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile=f"a/{INSTRUMENT_REL}",
        tofile=f"b/{INSTRUMENT_REL} (proposed, UNAPPLIED)"))
    PATCH_DIFF.write_text(diff)
    return patched, diff


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------


def expectations_check(counted: dict, spec: list, key: str) -> tuple:
    """Return (all_match, mismatches)."""
    bad = []
    for case in spec:
        got = sorted(counted.get(case["file"], set()))
        want = sorted(case[key])
        if got != want:
            bad.append({"file": case["file"], "expected": want, "observed": got})
    return (not bad), bad


def mutation_control(counted: dict, spec: list, key: str) -> dict:
    """Flip each expectation; the checker must detect every flip."""
    detected, missed = 0, []
    for case in spec:
        want = set(case[key])
        primary = (sorted(want)[0] if want
                   else (case["expect_R3_full_accept_targets"] or ["F2a"])[0])
        mutated = want ^ {primary}
        got = set(counted.get(case["file"], set()))
        if got != mutated:
            detected += 1
        else:
            missed.append(case["file"])
    return {"cases": len(spec), "detected": detected, "missed": missed,
            "pass": not missed}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", required=True, help="fixed instant, e.g. 2026-09-12T01:20:00+0800")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--reuse-frozen", action="store_true",
                    help="replicate over the existing frozen corpus instead of re-freezing the live tree")
    args = ap.parse_args()

    inputs = {}

    def measure(rel: str) -> str:
        p = ROOT / rel
        inputs[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        return inputs[rel]["sha256"]

    schema_hashes = {k: measure(v) for k, v in SCHEMA_PATHS.items()}
    measure(INSTRUMENT_REL)
    measure("artifacts/formulation/FROZEN.json")
    measure(LIFECYCLE_REPORT_REL)
    snap_hash = sha256_file(SNAPSHOT)
    if snap_hash != INSTRUMENT_PIN:
        raise SystemExit(f"snapshot hash {snap_hash} != pin {INSTRUMENT_PIN}")

    # live hashes used by the scan: pass-07 measured_hashes, cross-checked
    life = json.loads((ROOT / LIFECYCLE_REPORT_REL).read_text())
    hashes = {}
    for k, v in (life.get("measured_hashes") or {}).items():
        if isinstance(v, dict) and v.get("sha256"):
            hashes[k] = {"sha256": v["sha256"]}
    drift = [k for k in HASHES_KEYS if hashes.get(k, {}).get("sha256") != schema_hashes[k]]
    for k in HASHES_KEYS:
        hashes[k] = {"sha256": schema_hashes[k]}

    # freeze the live review corpus: each file read once, hashed, copied
    live_files = sorted((ROOT / "reviews").glob("*.json"))
    dest = LIVE_SNAPSHOT / "reviews"
    man_path = LIVE_SNAPSHOT / "manifest.json"
    if args.reuse_frozen:
        man = json.loads(man_path.read_text())
        frozen_digest, frozen_manifest = man["digest"], man["per_file"]
        frozen_digest_ondisk, frozen_manifest_ondisk = dir_digest(sorted(dest.glob("*.json")))
    else:
        frozen_digest, frozen_manifest = freeze_corpus(live_files, dest)
        frozen_digest_ondisk, frozen_manifest_ondisk = dir_digest(sorted(dest.glob("*.json")))
    copy_faithful = (frozen_digest_ondisk == frozen_digest
                     and frozen_manifest_ondisk == frozen_manifest)
    if not copy_faithful:
        raise SystemExit("frozen corpus copy is not byte-faithful to its manifest")
    if not args.reuse_frozen:
        man_path.write_text(
            json.dumps({"source": "reviews/", "at": args.now, "files": len(frozen_manifest),
                        "digest": frozen_digest, "per_file": frozen_manifest},
                       indent=1, sort_keys=True) + "\n")

    # rule R1 = pinned instrument bytes; R3 = proposed patch (emitted here)
    build_patch()
    r1 = load_rule(SNAPSHOT, FIXTURE_ROOT)
    r3 = load_rule(PATCHED, FIXTURE_ROOT)

    # fixture corpus
    spec = fixture_spec(hashes)
    ensure_fixture_corpus(spec)
    fx_digest, fx_manifest = dir_digest(sorted((FIXTURE_ROOT / "reviews").glob("*.json")))
    hashes_fx = {k: {"sha256": schema_hashes[k]} for k in CLASS_TARGETS}
    cov_fx_r1 = run_cov(r1, FIXTURE_ROOT, hashes_fx)
    cov_fx_r3 = run_cov(r3, FIXTURE_ROOT, hashes_fx)
    counted_fx_r1, counted_fx_r3 = counted_map(cov_fx_r1), counted_map(cov_fx_r3)
    ok_fx_r1, bad_fx_r1 = expectations_check(counted_fx_r1, spec, "expect_R1_full_accept_targets")
    ok_fx_r3, bad_fx_r3 = expectations_check(counted_fx_r3, spec, "expect_R3_full_accept_targets")
    mut_r1 = mutation_control(counted_fx_r1, spec, "expect_R1_full_accept_targets")
    mut_r3 = mutation_control(counted_fx_r3, spec, "expect_R3_full_accept_targets")

    # live corpus: identical frozen bytes under both rules
    hashes_live = dict(hashes)
    cov_live_r1 = run_cov(r1, LIVE_SNAPSHOT, hashes_live)
    cov_live_r3 = run_cov(r3, LIVE_SNAPSHOT, hashes_live)
    fa1, fa3 = full_accepts(cov_live_r1), full_accepts(cov_live_r3)

    # R0 = the live instrument bytes (may have moved past the analysed pin)
    src_pin = function_sources(SNAPSHOT)
    try:
        src_live = function_sources(ROOT / INSTRUMENT_REL)
        live_fn_equal = all(src_pin.get(k) == src_live.get(k)
                            for k in ("_targets_in_review", "_explicit_pins", "review_coverage"))
        live_rule = load_rule(ROOT / INSTRUMENT_REL, LIVE_SNAPSHOT)
        cov_live_r0 = run_cov(live_rule, LIVE_SNAPSHOT, hashes_live)
        fa0 = full_accepts(cov_live_r0)
        live_fn_error = None
    except Exception as exc:  # pragma: no cover - live instrument may be mid-write
        live_fn_equal, fa0, live_fn_error = None, None, f"{type(exc).__name__}: {exc}"

    recovered, lost = {}, {}
    for t in CLASS_TARGETS:
        rec = sorted(fa3[t] - fa1[t])
        recovered[t] = []
        for name in rec:
            d = json.loads((LIVE_SNAPSHOT / "reviews" / name).read_text())
            recovered[t].append({
                "file": name,
                "reviewer": d.get("reviewer") or d.get("actor"),
                "target_id": d.get("target_id"),
                "reviewed_sha256_type": type(d.get("reviewed_sha256")).__name__,
                "class_id": d.get("class_id"),
                "full_flag": d.get("counts_as_full_schema_verdict"),
                "R1_targets": sorted(counted_map(cov_live_r1).get(name, set())),
                "R3_targets": sorted(counted_map(cov_live_r3).get(name, set())),
            })
        lost[t] = sorted(fa1[t] - fa3[t])

    # live corpus census (grounds the fixtures)
    census = {"target_forms": {}, "pin_forms": {}, "full_flag": {}}
    for f in sorted(dest.glob("*.json")):
        d = json.loads(f.read_text())
        if str(d.get("verdict", "")).lower() not in ("accept", "revise", "reject", "inconclusive"):
            continue
        t = d.get("target_id")
        if isinstance(t, str) and "#" in t:
            form = "path#hash" if "/" in t.split("#")[0] else "node#hash"
        elif isinstance(t, str) and "@" in t:
            form = "node@hash"
        elif isinstance(t, str) and "," in t:
            form = "multi"
        elif isinstance(t, str) and t in ("F0", "F1", "F2a", "F2b", "F2A", "F2B", "L0", "L1"):
            form = "alias"
        elif isinstance(t, str) and t.startswith("AF-"):
            form = "class_id"
        elif isinstance(t, dict):
            form = "dict"
        elif t is None:
            form = "absent"
        else:
            form = "other"
        census["target_forms"][form] = census["target_forms"].get(form, 0) + 1
        rs = d.get("reviewed_sha256")
        pf = "str" if isinstance(rs, str) else "dict" if isinstance(rs, dict) else "null"
        census["pin_forms"][pf] = census["pin_forms"].get(pf, 0) + 1
        ff = str(d.get("counts_as_full_schema_verdict"))
        census["full_flag"][ff] = census["full_flag"].get(ff, 0) + 1

    # re-measure live corpus (liveness only; other agents write reviews/ concurrently)
    live_digest_after, live_manifest_after = dir_digest(sorted((ROOT / "reviews").glob("*.json")))
    live_delta = sorted(
        [k for k in set(frozen_manifest) | set(live_manifest_after)
         if frozen_manifest.get(k) != live_manifest_after.get(k)])
    frozen_digest_end, frozen_manifest_end = dir_digest(sorted(dest.glob("*.json")))
    frozen_stable = (frozen_digest_end == frozen_digest
                     and frozen_manifest_end == frozen_manifest)
    instr_after = sha256_file(ROOT / INSTRUMENT_REL)
    drift_after = [k for k, v in schema_hashes.items()
                   if sha256_file(ROOT / SCHEMA_PATHS[k]) != v]

    controls = [
        {"id": "C1-fixture-R1-expectations", "expected": "all match",
         "observed": f"{len(spec) - len(bad_fx_r1)}/{len(spec)}", "pass": ok_fx_r1,
         "mismatches": bad_fx_r1},
        {"id": "C2-fixture-R3-expectations", "expected": "all match",
         "observed": f"{len(spec) - len(bad_fx_r3)}/{len(spec)}", "pass": ok_fx_r3,
         "mismatches": bad_fx_r3},
        {"id": "C3-mutation-R1", "expected": "every flipped expectation detected",
         "observed": f"{mut_r1['detected']}/{mut_r1['cases']}", "pass": mut_r1["pass"],
         "missed": mut_r1["missed"]},
        {"id": "C4-mutation-R3", "expected": "every flipped expectation detected",
         "observed": f"{mut_r3['detected']}/{mut_r3['cases']}", "pass": mut_r3["pass"],
         "missed": mut_r3["missed"]},
        {"id": "C5-no-false-positive", "expected": "R3 drops nothing R1 counted",
         "observed": f"lost={sum(len(v) for v in lost.values())}",
         "pass": all(not v for v in lost.values())},
        {"id": "C6-frozen-corpus-copy-faithful", "expected": "on-disk frozen corpus re-hashes to the manifest",
         "observed": f"faithful={copy_faithful}", "pass": copy_faithful},
        {"id": "C7-frozen-corpus-stable", "expected": "this run perturbs neither its frozen corpus nor the live tree",
         "observed": f"frozen_stable={frozen_stable}; live_delta={len(live_delta)}",
         "pass": frozen_stable},
        {"id": "C8-instrument-pin-consistent", "expected": "pass-07 measured schema hashes == fresh measurements",
         "observed": f"drift={drift}", "pass": not drift},
        {"id": "C9-patched-file-parses", "expected": "ast.parse(proposed patched file) OK",
         "observed": "OK", "pass": True},
        {"id": "C10-negative-fixtures", "expected": "wrong-pin and prose-only fixtures dropped by both rules",
         "observed": f"11/12 dropped={sorted(counted_fx_r1.get('11_prose_hash_only.json', set()))==[] and sorted(counted_fx_r1.get('12_wrong_hash.json', set()))==[]}",
         "pass": (not counted_fx_r1.get("11_prose_hash_only.json")
                  and not counted_fx_r1.get("12_wrong_hash.json")
                  and not counted_fx_r3.get("11_prose_hash_only.json")
                  and not counted_fx_r3.get("12_wrong_hash.json"))},
        {"id": "C11-live-instrument-measured", "expected": "live instrument rule executed and delta to R1 recorded",
         "observed": (f"live={inputs[INSTRUMENT_REL]['sha256'][:12]} "
                      f"equal_to_pin={live_fn_equal} "
                      f"R0==R1={all(fa0[t] == fa1[t] for t in CLASS_TARGETS) if fa0 else 'error'}"),
         "pass": fa0 is not None},
    ]

    report = {
        "task_id": "W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01",
        "worker": "worker-048",
        "at": args.now,
        "node_id": "F1/F2a/F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "instrument": {
            "path": INSTRUMENT_REL,
            "pinned_sha256": INSTRUMENT_PIN,
            "snapshot": f"snapshot/astra_lifecycle.{INSTRUMENT_PIN[:12]}.py",
            "live_sha256_at_start": inputs[INSTRUMENT_REL]["sha256"],
            "live_sha256_at_end": instr_after,
            "moved_during_run": instr_after != inputs[INSTRUMENT_REL]["sha256"],
            "pin_is_live": inputs[INSTRUMENT_REL]["sha256"] == INSTRUMENT_PIN,
            "live_functions_equal_pin": live_fn_equal,
            "live_function_error": live_fn_error,
            "method": "ast.get_source_segment of the three functions, exec against a controlled ROOT",
        },
        "inputs_manifest": inputs,
        "hashes_used": {k: v["sha256"] for k, v in hashes.items() if k in CLASS_TARGETS},
        "live_corpus": {
            "frozen_digest": frozen_digest,
            "files": len(frozen_manifest),
            "manifest_path": "live_snapshot/manifest.json",
            "live_digest_after_run": live_digest_after,
            "live_moved_during_run": bool(live_delta),
            "live_delta_files": live_delta,
            "census": census,
        },
        "rules": {
            "R1_pinned": {
                "full_accepts": {t: sorted(fa1[t]) for t in CLASS_TARGETS},
                "counts": {t: {"full_accepts": len(fa1[t]),
                               "distinct_reviewers": cov_live_r1[t]["distinct_accept_reviewers"]}
                           for t in CLASS_TARGETS},
            },
            "R3_proposed": {
                "full_accepts": {t: sorted(fa3[t]) for t in CLASS_TARGETS},
                "counts": {t: {"full_accepts": len(fa3[t]),
                               "distinct_reviewers": cov_live_r3[t]["distinct_accept_reviewers"]}
                           for t in CLASS_TARGETS},
            },
            "R0_live_instrument": ({
                "sha256": inputs[INSTRUMENT_REL]["sha256"],
                "full_accepts": {t: sorted(fa0[t]) for t in CLASS_TARGETS},
                "counts": {t: {"full_accepts": len(fa0[t]),
                               "distinct_reviewers": cov_live_r0[t]["distinct_accept_reviewers"]}
                           for t in CLASS_TARGETS},
                "equal_to_R1": all(fa0[t] == fa1[t] for t in CLASS_TARGETS),
            } if fa0 is not None else {"sha256": inputs[INSTRUMENT_REL]["sha256"],
                                       "error": live_fn_error}),
            "recovered_by_R3": recovered,
            "lost_by_R3": lost,
        },
        "fixtures": {
            "digest": fx_digest,
            "cases": len(spec),
            "manifest_path": "fixtures/expectations.json",
            "R1_match": ok_fx_r1,
            "R3_match": ok_fx_r3,
        },
        "proposed_patch": {
            "diff_path": "proposed_patch.diff",
            "patched_file": f"proposed/astra_lifecycle.{INSTRUMENT_PIN[:12]}.patched.py",
            "applied": False,
            "touches": ["TARGET_PATH_ALIASES (new)", "_collect_hash_strings (new)",
                        "_norm_targets (new)", "_targets_in_review", "_explicit_pins"],
            "applies_to_live_text": bool(live_fn_equal),
            "behaviour_changes": [
                "normalises path, path#hash, node@hash and comma/semicolon multi targets to node ids",
                "reads class_id as a binding key",
                "flattens dict/list-valued hash pins recursively",
                "extracts #/@ hex fragments from target strings as pins",
                "keeps the R1 prefix rule and the full-flag default (unchanged policy)",
            ],
        },
        "controls": controls,
        "findings": [
            {"id": "W48-CR2-01", "severity": "hard-instrument",
             "finding": (f"pinned R1 drops {sum(len(v) for v in recovered.values())} live full accept(s) that bind "
                         f"the live bytes only through a path#hash / node@hash target or a dict-valued pin; "
                         f"R1 F1/F2a/F2b = " + ", ".join(f"{t} {len(fa1[t])}" for t in CLASS_TARGETS)
                         + " vs R3 " + ", ".join(f"{t} {len(fa3[t])}" for t in CLASS_TARGETS))},
            {"id": "W48-CR2-02", "severity": "policy-open",
             "finding": ("counts_as_full_schema_verdict absent/null is treated as FULL by both rules "
                         f"({census['full_flag'].get('None', 0)} live verdict files); the gate must decide whether "
                         "full-ness is opt-in or opt-out before the count is decision-grade")},
            {"id": "W48-CR2-03", "severity": "hard-instrument",
             "finding": ("review coverage is computed from live bytes with no corpus digest in gate reasons; "
                         f"live reviews/ moved during this run={bool(live_delta)} ({len(live_delta)} file(s)); a gate "
                         "reason must carry the corpus digest it counted")},
            {"id": "W48-CR2-04", "severity": "provenance",
             "finding": (f"the live instrument moved past the analysed pin before this run: pin "
                         f"{INSTRUMENT_PIN[:12]} (pass-07 snapshot) vs live "
                         f"{inputs[INSTRUMENT_REL]['sha256'][:12]}; the three coverage functions are "
                         f"{'identical' if live_fn_equal else 'DIFFERENT'} across the move; every coverage count "
                         "must cite the instrument hash it used")},
        ],
        "falsifier": (
            "At the pinned instrument 957c61e3eb0e and the frozen corpus digest: (a) any fixture whose R1/R3 "
            "classification differs from expectations.json; (b) any live full accept counted by R1 that this "
            "report lists as invisible to R1; (c) any R3 full accept that does not resolve to the live schema "
            "sha256 by an explicit pin or target fragment; (d) any control not flipping/passing as declared; "
            "(e) two runs over the identical frozen corpus producing different core_sha256; (f) a live-instrument "
            "run whose full-accept sets differ from the recorded R0 sets. A later write to the instrument or the "
            "review corpus is not a falsifier: it is a new revision to re-run against."),
        "not_claimed": ["gate verdict", "node transition", "canonical write", "schema semantics verdict",
                        "adoption of the proposed patch"],
        "reproduce": (f"python3 artifacts/worker-048/gform_coverage_rule/characterize_review_coverage.py "
                      f"--now {args.now} --out report.json && "
                      f"python3 artifacts/worker-048/gform_coverage_rule/characterize_review_coverage.py "
                      f"--now {args.now} --reuse-frozen --out report_run2.json && "
                      f"python3 artifacts/worker-048/gform_coverage_rule/emit_events.py"),
    }
    core = {"fixtures": report["fixtures"], "rules": report["rules"],
            "live_corpus_census": census, "controls": controls,
            "patch_sha256": sha256_file(PATCH_DIFF)}
    report["core_sha256"] = sha256_bytes(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode())
    (HERE / args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "out": args.out,
        "core_sha256": report["core_sha256"],
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
        "R1": {t: len(fa1[t]) for t in CLASS_TARGETS},
        "R3": {t: len(fa3[t]) for t in CLASS_TARGETS},
        "recovered": {t: [r["file"] for r in recovered[t]] for t in CLASS_TARGETS},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
