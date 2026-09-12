#!/usr/bin/env python3
"""W098-F2B-REPAIR-VERIFY-01 -- independent repair verification for F2b.

Task:  re-test the W098-F2B-BLOCKER-ADJ-01 falsifier (B1 duplicate revised_at keys,
       B2 ill-typed D0 pair binder over a disjunctive domain, B3 class_contract_pointer
       resolving only in the authoring supplement) against the newly published
       canonical F2b bytes, and emit a binding verdict at the measured hash.

Scope: AF-SCC-C0-VAC-GEN / node F2b / gate G-FORM.  Read-only with respect to every
       canonical file.  Worker evidence only: this script never sets a gate verdict,
       node status, validation_status or completion flag.

Determinism: no network, no clock-dependent content beyond recorded timestamps;
             every check is a pure function of the pinned input bytes.

Usage:
  python3 verify_f2b_repair_098.py --out report.json --snapshot-dir snapshot
  python3 verify_f2b_repair_098.py --check-only     # no files written
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]  # artifacts/worker-098/f2b_repair_verify/<file> -> repo root
CST = dt.timezone(dt.timedelta(hours=8))
SKEW_TOL = dt.timedelta(seconds=120)

SUBJECT = "schemas/af_scc_c0_vacuum.yaml"
SUBJECT_EXPECT = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
CANON_F0 = "research_map/formulation_taxonomy.yaml"
CANON_F0_EXPECT = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SIBLINGS = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN", "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN", "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "F2b": (SUBJECT, "AF-SCC-C0-VAC-GEN", SUBJECT_EXPECT),
}
GATE_TOOL = "artifacts/formulation/tools/check_class_schema.py"

AXIS_MAP = {
    "AF": "asymptotically_flat_3p1",
    "SCC": "SCC",
    "WCC": "WCC",
    "VAC": "vacuum",
    "C0": "C0",
    "C2": "C2",
}


def norm_token(v) -> str:
    """Null regularity tokens are spelled None (taxonomy) or 'none' (class schema)."""
    s = "" if v is None else str(v).strip().lower()
    return "NONE" if s in ("", "none", "null", "~") else s


# ---------------------------------------------------------------- yaml helpers
def load_with_dups(text: str):
    """Parse YAML, collecting duplicate mapping keys instead of silently last-winning."""
    dups: list[str] = []

    class L(yaml.SafeLoader):
        pass

    def cm(loader, node, deep=False):
        seen: dict[str, int] = {}
        for k, _ in node.value:
            kk = loader.construct_object(k, deep=deep)
            seen[str(kk)] = seen.get(str(kk), 0) + 1
        for kk, c in seen.items():
            if c > 1:
                dups.append(kk)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
    doc = yaml.load(text, Loader=L)
    return doc, dups


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_cst() -> dt.datetime:
    return dt.datetime.now(CST)


def parse_ts(v):
    try:
        t = dt.datetime.fromisoformat(str(v))
    except Exception:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=CST)
    return t


# ---------------------------------------------------------------- check helpers
class Ctx:
    """Carries one pinned snapshot through all checks."""

    def __init__(self, path: str, expect: str, class_id: str):
        self.path = path
        self.expect = expect
        self.class_id = class_id
        self.raw = (ROOT / path).read_bytes()
        self.text = self.raw.decode()
        self.sha = sha256_bytes(self.raw)
        self.doc, self.dups = load_with_dups(self.text)
        self.checks: list[dict] = []

    def add(self, cid, status, expected, observed):
        self.checks.append(
            {"id": cid, "status": status, "expected": expected, "observed": observed}
        )

    def result(self, cid):
        for c in self.checks:
            if c["id"] == cid:
                return c["status"]
        return None


def check_identity(c: Ctx):
    d = c.doc if isinstance(c.doc, dict) else {}
    ok = (
        c.sha == c.expect
        and isinstance(d, dict)
        and d.get("artifact_kind") == "class_schema"
        and d.get("class_id") == c.class_id
    )
    c.add(
        "P0_pinned_identity",
        "PASS" if ok else "FAIL",
        f"sha256={c.expect[:12]} artifact_kind=class_schema class_id={c.class_id}",
        f"sha256={c.sha[:12]} artifact_kind={d.get('artifact_kind')} class_id={d.get('class_id')}",
    )


def check_dup_keys(c: Ctx):
    """B1a: no duplicate mapping keys anywhere; strict reader must parse cleanly."""
    n_top = len(re.findall(r"(?m)^revised_at:", c.text))
    status = "PASS" if (not c.dups and n_top == 1) else "FAIL"
    c.add(
        "P1_no_duplicate_keys",
        status,
        "0 duplicate mapping keys; 1 top-level revised_at",
        f"dups={sorted(set(c.dups))} top_level_revised_at={n_top}",
    )


def check_revision_history(c: Ctx):
    """B1b: revision history must live in a list, not in repeated scalar keys."""
    d = c.doc if isinstance(c.doc, dict) else {}
    hist = d.get("revision_history")
    ok = isinstance(hist, list) and len(hist) >= 1 and all(isinstance(h, dict) for h in hist)
    detail = f"present={isinstance(hist, list)} entries={len(hist) if isinstance(hist, list) else 'n/a'}"
    status = "PASS" if ok else "FAIL"
    if ok:
        ats = [parse_ts(h.get("at")) for h in hist]
        if all(ats) and parse_ts(d.get("revised_at")):
            last = max(t for t in ats if t)
            top = parse_ts(d.get("revised_at"))
            if last != top:
                status = "WARN"
                detail += f"; last_history_at={last.isoformat()} != revised_at={top.isoformat()}"
            else:
                detail += f"; last_history_at==revised_at=={last.isoformat()}"
    c.add("P2_revision_history_list", status, "revision_history list, last entry == revised_at", detail)


def check_timestamps_not_future(c: Ctx, clock: dt.datetime):
    """B1c: top-level revised_at and f0_binding.checked_at must not run ahead of wall clock."""
    d = c.doc if isinstance(c.doc, dict) else {}
    vals = {
        "revised_at": d.get("revised_at"),
        "f0_binding.checked_at": (d.get("f0_binding") or {}).get("checked_at"),
    }
    hist = d.get("revision_history") or []
    hist_ats = [parse_ts(h.get("at")) for h in hist if isinstance(h, dict)]
    hist_ats = [t for t in hist_ats if t]
    if hist_ats:
        vals["max(revision_history.at)"] = max(hist_ats).isoformat()
    bad = []
    shown = {}
    for k, v in vals.items():
        t = parse_ts(v)
        shown[k] = v
        if t is None:
            bad.append(f"{k}=unparseable({v!r})")
        elif t > clock + SKEW_TOL:
            bad.append(f"{k}={t.isoformat()} > now+{SKEW_TOL}")
    c.add(
        "P3_no_future_timestamps",
        "PASS" if not bad else "FAIL",
        f"all timestamps <= review clock {clock.isoformat()} (+{SKEW_TOL})",
        f"values={shown}" + ("; violations=" + "; ".join(bad) if bad else ""),
    )


def check_binder_typed(c: Ctx):
    """B2a: D0 binder is the tagged index r, never a pair (s,delta)."""
    d = c.doc if isinstance(c.doc, dict) else {}
    q = d.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    doms = q.get("domains") or {}
    binders = [(o.get("kind"), str(o.get("binder")), o.get("domain_id")) for o in ordered if isinstance(o, dict)]
    pair_binders = [b for b in binders if re.search(r"s\s*,\s*delta", b[1])]
    r_binder = [b for b in binders if b[0] == "forall" and b[1] == "r" and b[2] == "D0"]
    ok = bool(r_binder) and not pair_binders and "D0" in doms
    c.add(
        "P4_binder_ranges_over_tagged_index",
        "PASS" if ok else "FAIL",
        "exactly one `forall r in D0`; no pair-typed binder",
        f"r_in_D0={bool(r_binder)} pair_binders={pair_binders} D0_present={'D0' in doms}",
    )


def check_d0_tagged_union(c: Ctx):
    """B2b: D0 is a tagged disjoint union with a declared ambient object per branch."""
    d = c.doc if isinstance(c.doc, dict) else {}
    q = d.get("quantifiers") or {}
    d0 = str(((q.get("domains") or {}).get("D0") or {}).get("definition") or "")
    gen = json.dumps((d.get("genericity") or {}))
    needed = {
        "tagged disjoint union": "tagged disjoint union" in d0,
        "tag r=smooth": "r = smooth" in d0,
        "tag r=(sobolev,s,delta)": "(sobolev,s,delta)" in d0,
        "ambient X^r_vac(AF)": "X^r_vac(AF)" in d0,
        "smooth topology Frechet": "Frechet for r = smooth" in d0 or ("Frechet" in d0 and "smooth" in d0),
        "sobolev weight H^s_delta": "H^s_delta" in d0,
        "genericity names Frechet smooth": "Frechet" in gen and "smooth" in gen,
    }
    missing = [k for k, v in needed.items() if not v]
    c.add(
        "P5_D0_tagged_union_typed",
        "PASS" if not missing else "FAIL",
        "both D0 branches carry an ambient object and a topology",
        f"missing={missing}",
    )


def check_no_pair_indexed_residue(c: Ctx):
    """B2c: no pair-indexed G/X objects survive the retyping."""
    d = c.doc if isinstance(c.doc, dict) else {}
    surfaces = json.dumps(
        {
            "quantifiers": d.get("quantifiers"),
            "conclusion": d.get("conclusion"),
            "genericity": d.get("genericity"),
            "data_class": d.get("data_class"),
        }
    )
    pats = {
        "G_{s,delta}": r"G_\{?\s*s\s*,\s*delta",
        "X^{s,delta}": r"X\^\{?\s*s\s*,\s*delta",
        "forall (s,delta)": r"forall\s*\(\s*s\s*,\s*delta\s*\)",
    }
    hits = {k: len(re.findall(p, surfaces)) for k, p in pats.items()}
    c.add(
        "P6_no_pair_indexed_residue",
        "PASS" if sum(hits.values()) == 0 else "FAIL",
        "0 pair-indexed objects in quantifiers/conclusion/genericity/data_class",
        f"hits={hits}",
    )


def resolve_pointer(ptr: str, class_id: str):
    """Resolve `<path>#classes.<class_id>` against the canonical taxonomy; return (ok, detail)."""
    if "#" not in ptr:
        return False, "pointer has no #anchor"
    path, anchor = ptr.split("#", 1)
    f = ROOT / path
    if not f.exists():
        return False, f"pointer path absent: {path}"
    try:
        tax = yaml.safe_load(f.read_text())
    except Exception as e:
        return False, f"pointer path unparseable: {type(e).__name__}"
    cur = tax
    for part in anchor.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, f"anchor {anchor!r} does not resolve (stops at {part!r})"
    return True, {"path": path, "anchor": anchor, "target_label": (cur or {}).get("label") if isinstance(cur, dict) else None, "target": cur}


def check_pointer_canonical(c: Ctx):
    """B3a: class_contract_pointer resolves in the controller-authoritative canonical taxonomy."""
    d = c.doc if isinstance(c.doc, dict) else {}
    ptr = str(d.get("class_contract_pointer") or "")
    ok, detail = resolve_pointer(ptr, c.class_id)
    canonical_path = ptr.split("#", 1)[0] == CANON_F0 if ptr else False
    axes_ok, axes_detail = False, "not evaluated"
    if ok and isinstance(detail, dict) and isinstance(detail.get("target"), dict):
        axes = (detail["target"] or {}).get("axes") or {}
        comp = d.get("class_components") or {}
        selftest = (
            norm_token(None) == "NONE"
            and norm_token("none") == "NONE"
            and norm_token("null") == "NONE"
            and norm_token("C0") == "c0"
        )
        checks = {
            "family": norm_token(axes.get("family")) == norm_token(AXIS_MAP.get(str(comp.get("censorship")))),
            "matter_model": norm_token(axes.get("matter_model")) == norm_token(AXIS_MAP.get(str(comp.get("matter")))),
            "asymptotics": norm_token(axes.get("asymptotics")) == norm_token(AXIS_MAP.get(str(comp.get("asymptotics")))),
            "regularity_token": norm_token(axes.get("regularity_token")) == norm_token(comp.get("regularity_token")),
        }
        axes_ok = all(checks.values()) and selftest
        axes_detail = {
            "checks": checks,
            "axis_norm_selftest": selftest,
            "taxonomy_axes": axes,
            "class_components": comp,
            "conclusion_type": (detail["target"] or {}).get("conclusion", {}).get("type")
            if isinstance((detail["target"] or {}).get("conclusion"), dict)
            else None,
        }
    status = "PASS" if (ok and canonical_path and axes_ok) else "FAIL"
    c.add(
        "P7_pointer_resolves_canonical",
        status,
        "pointer resolves under canonical taxonomy `classes.<class_id>` with matching axes",
        f"pointer={ptr!r} resolves={ok} canonical_path={canonical_path} axes_match={axes_ok} detail={detail if not ok else axes_detail}",
    )


def check_f0_binding(c: Ctx):
    """B3b: declared F0 hash equals the live canonical taxonomy hash."""
    d = c.doc if isinstance(c.doc, dict) else {}
    b = d.get("f0_binding") or {}
    declared_path = b.get("declared_f0_artifact")
    declared = str(b.get("declared_f0_sha256") or "")
    live = sha256_file(ROOT / CANON_F0)
    ok = declared == live and declared_path == CANON_F0
    c.add(
        "P8_f0_hash_binding_fresh",
        "PASS" if ok else "FAIL",
        f"declared_f0_artifact={CANON_F0} declared_f0_sha256={live[:12]}",
        f"declared_artifact={declared_path} declared_sha256={declared[:12]} live_sha256={live[:12]}",
    )


def check_pointer_separation(c: Ctx):
    """B3c: canonical pointer and authoring supplement pointer are distinct fields/trees."""
    d = c.doc if isinstance(c.doc, dict) else {}
    canon = str(d.get("class_contract_pointer") or "")
    supp = str(d.get("class_contract_supplement_pointer") or "")
    supp_in_binding = str((d.get("f0_binding") or {}).get("class_contract_supplement") or "")
    ok = (
        canon.startswith(CANON_F0 + "#classes.")
        and supp.startswith("artifacts/formulation/")
        and supp != canon
        and supp_in_binding.startswith("artifacts/formulation/")
    )
    c.add(
        "P9_pointer_separation",
        "PASS" if ok else "FAIL",
        "canonical pointer -> canonical taxonomy; supplement pointer -> authoring tree; fields distinct",
        f"canonical={canon!r} supplement={supp!r} binding_supplement={supp_in_binding!r}",
    )


def check_classsep(c: Ctx):
    """Class-separation: the class-bound schema must not merge the frozen classes."""
    sys.path.insert(0, str(ROOT / "research_map"))
    try:
        import class_separation  # type: ignore
        found = class_separation.findings(c.doc, c.path, mode="declaration")
    except Exception as e:  # fail closed
        c.add("P10_classsep_clean", "FAIL", "0 class-separation findings", f"checker error: {type(e).__name__}: {e}")
        return
    c.add(
        "P10_classsep_clean",
        "PASS" if not found else "FAIL",
        "0 class-separation findings",
        f"findings={found[:3]}" if found else "findings=[]",
    )


def run_canonical_gate(c: Ctx):
    """Canonical stage evidence: parse the gate's JSON verdict (its exit code is always 0)."""
    try:
        p = subprocess.run(
            [sys.executable, str(ROOT / GATE_TOOL), c.path, "--json"],
            capture_output=True, text=True, timeout=180, cwd=str(ROOT),
        )
        try:
            out = json.loads(p.stdout)
        except Exception:
            out = {"verdict": "unparseable", "stdout_head": p.stdout[:200], "stderr_head": p.stderr[:200]}
        return {"tool": GATE_TOOL, "exit_code": p.returncode, **out}
    except Exception as e:
        return {"tool": GATE_TOOL, "exit_code": None, "verdict": "error", "error": f"{type(e).__name__}: {e}"}


def run_checks(c: Ctx, clock: dt.datetime):
    check_identity(c)
    check_dup_keys(c)
    check_revision_history(c)
    check_timestamps_not_future(c, clock)
    check_binder_typed(c)
    check_d0_tagged_union(c)
    check_no_pair_indexed_residue(c)
    check_pointer_canonical(c)
    check_f0_binding(c)
    check_pointer_separation(c)
    check_classsep(c)
    return c


# ---------------------------------------------------------------- controls
def mutate(text: str, old: str, new: str, count: int = 1) -> str:
    if old not in text:
        raise RuntimeError(f"control mutation target not found: {old[:80]!r}")
    return text.replace(old, new, count)


def control_mutants(c: Ctx) -> list[tuple[str, str, list[str]]]:
    """(id, description, [checks that must FAIL on the mutant])"""
    t = c.text
    return [
        (
            "K1_duplicate_revised_at",
            "duplicate the top-level revised_at key",
            ["P1_no_duplicate_keys"],
            mutate(
                t,
                'revised_at: "2026-09-12T00:31:41+08:00"',
                'revised_at: "2026-09-12T00:31:41+08:00"\nrevised_at: "2026-09-12T00:31:42+08:00"',
                1,
            ),
        ),
        (
            "K2_binder_retyped_to_pair",
            "retype the D0 binder back to (s,delta)",
            ["P4_binder_ranges_over_tagged_index", "P6_no_pair_indexed_residue"],
            mutate(
                mutate(t, 'forall r in D0', 'forall (s,delta) in D0'),
                'binder: "r", domain_id: D0',
                'binder: "(s,delta)", domain_id: D0',
            ),
        ),
        (
            "K3_smooth_ambient_removed",
            "remove the smooth branch ambient/topology clause",
            ["P5_D0_tagged_union_typed"],
            mutate(t, "Frechet for r = smooth; ", "", 1),
        ),
        (
            "K4_pointer_bad_class",
            "point class_contract_pointer at a non-existent class",
            ["P7_pointer_resolves_canonical"],
            mutate(t, "#classes.AF-SCC-C0-VAC-GEN", "#classes.AF-NOPE-VAC-GEN", 1),
        ),
        (
            "K5_pointer_missing_file",
            "point class_contract_pointer at a missing file",
            ["P7_pointer_resolves_canonical"],
            mutate(
                t,
                "research_map/formulation_taxonomy.yaml#classes.",
                "research_map/no_such_taxonomy.yaml#classes.",
                1,
            ),
        ),
        (
            "K6_f0_hash_stale",
            "declare a stale F0 hash",
            ["P8_f0_hash_binding_fresh"],
            mutate(t, CANON_F0_EXPECT, "0" * 64, 1),
        ),
        (
            "K7_future_revised_at",
            "stamp a future revised_at",
            ["P3_no_future_timestamps"],
            mutate(t, '"2026-09-12T00:31:41+08:00"', '"2099-01-01T00:00:00+08:00"', 1),
        ),
        (
            "K8_pair_indexed_residue",
            "reintroduce a pair-indexed object",
            ["P6_no_pair_indexed_residue"],
            mutate(t, "exists G_r comeager", "exists G_{s,delta} comeager", 1),
        ),
        (
            "K9_pointer_conflated_with_supplement",
            "conflate the canonical pointer with the authoring supplement",
            ["P7_pointer_resolves_canonical", "P9_pointer_separation"],
            mutate(
                t,
                "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
                "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN",
                1,
            ),
        ),
    ]


def run_controls(c: Ctx, clock: dt.datetime):
    out = []
    for cid, desc, must_fail, text in control_mutants(c):
        m = Ctx.__new__(Ctx)
        m.path, m.expect, m.class_id = c.path, c.expect, c.class_id
        m.raw = text.encode()
        m.text = text
        m.sha = sha256_bytes(m.raw)
        m.doc, m.dups = load_with_dups(m.text)
        m.checks = []
        run_checks(m, clock)
        observed = {k: m.result(k) for k in must_fail}
        detected = all(observed[k] == "FAIL" for k in must_fail)
        out.append(
            {
                "id": cid,
                "description": desc,
                "mutated_sha256": m.sha,
                "must_fail": must_fail,
                "observed": observed,
                "status": "PASS" if detected else "FAIL",
            }
        )
    return out


# ---------------------------------------------------------------- sibling scan
def sibling_table(clock: dt.datetime):
    rows = {}
    for node, (path, class_id, expect) in SIBLINGS.items():
        c = Ctx(path, expect, class_id)
        run_checks(c, clock)
        rows[node] = {
            "path": path,
            "class_id": class_id,
            "sha256": c.sha,
            "sha_matches_pin": c.sha == expect,
            "checks": {ch["id"]: ch["status"] for ch in c.checks},
            "failed": [ch["id"] for ch in c.checks if ch["status"] == "FAIL"],
        }
    # F0 is a taxonomy, not a class_schema: identity check does not apply
    f0 = ROOT / CANON_F0
    f0raw = f0.read_bytes()
    f0doc, f0dups = load_with_dups(f0raw.decode())
    rows["F0"] = {
        "path": CANON_F0,
        "class_id": "ALL-FOUR",
        "sha256": sha256_bytes(f0raw),
        "sha_matches_pin": sha256_bytes(f0raw) == CANON_F0_EXPECT,
        "revision": f0doc.get("revision") if isinstance(f0doc, dict) else None,
        "duplicate_keys": sorted(set(f0dups)),
        "classes_present": sorted((f0doc.get("classes") or {}).keys()) if isinstance(f0doc, dict) else [],
        "has_class_contracts_key": bool(isinstance(f0doc, dict) and f0doc.get("class_contracts")),
    }
    return rows


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "report.json"))
    ap.add_argument("--snapshot-dir", default=str(HERE.parent / "snapshot"))
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    clock = now_cst()
    subject = Ctx(SUBJECT, SUBJECT_EXPECT, "AF-SCC-C0-VAC-GEN")
    run_checks(subject, clock)
    canonical = run_canonical_gate(subject)
    controls = run_controls(subject, clock)
    siblings = sibling_table(clock)

    p_fail = [c for c in subject.checks if c["status"] == "FAIL"]
    k_fail = [k for k in controls if k["status"] != "PASS"]
    canonical_pass = str(canonical.get("verdict", "")).lower() == "pass"

    report = {
        "schema_version": "0.1",
        "task_id": "W098-F2B-REPAIR-VERIFY-01",
        "actor": "worker-098",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "generated_at": clock.isoformat(),
        "question": "Does the newly published canonical F2b revision falsify the W098 B1/B2/B3 blocking findings at the measured hash?",
        "subject": {
            "path": SUBJECT,
            "sha256": subject.sha,
            "sha_matches_w098_pin": subject.sha == SUBJECT_EXPECT,
            "bytes": len(subject.raw),
            "lines": subject.text.count("\n") + 1,
            "revision": (subject.doc or {}).get("revision") if isinstance(subject.doc, dict) else None,
            "declared_revised_at": (subject.doc or {}).get("revised_at") if isinstance(subject.doc, dict) else None,
        },
        "inputs": {
            p: sha256_file(ROOT / p)
            for p in [SUBJECT, CANON_F0, "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", GATE_TOOL]
        },
        "checks": subject.checks,
        "canonical_stage": canonical,
        "controls": controls,
        "sibling_cross_check": siblings,
        "falsifier": (
            "Re-measure schemas/af_scc_c0_vacuum.yaml and research_map/formulation_taxonomy.yaml against the "
            "hashes recorded in this report. The repair claim is falsified if: (a) any P-check FAILs on a live "
            "snapshot whose subject hash equals the pinned 55d0a1ea...; (b) any control K1-K9 is not detected "
            "(instrument failure); (c) class_contract_pointer stops resolving under canonical taxonomy key "
            "`classes`; or (d) the canonical gate tool at artifacts/formulation/tools/check_class_schema.py "
            "returns a verdict other than pass on the pinned bytes. A later file write is not a falsifier: the "
            "verdict binds only to the pinned bytes."
        ),
        "limitations": [
            "Structural / machine-conformance verification only; no truth claim about cosmic censorship.",
            "Scope is the pinned F2b bytes; sibling and F0 columns are evidence context, not verdicts on those nodes.",
            "The canonical gate is reproduced as cited stage evidence, not as this worker's independent verdict.",
            "Worker events cannot set a gate verdict, node status or validation_status.",
        ],
        "authority": "worker evidence only; no gate verdict, no node completion, no canonical-file edit",
        "summary": {
            "checks_total": len(subject.checks),
            "checks_failed": [c["id"] for c in p_fail],
            "checks_warned": [c["id"] for c in subject.checks if c["status"] == "WARN"],
            "controls_total": len(controls),
            "controls_failed": [k["id"] for k in k_fail],
            "canonical_gate_verdict": canonical.get("verdict"),
            "b1_duplicate_keys_closed": subject.result("P1_no_duplicate_keys") == "PASS",
            "b2_d0_typing_closed": subject.result("P4_binder_ranges_over_tagged_index") == "PASS"
            and subject.result("P5_D0_tagged_union_typed") == "PASS"
            and subject.result("P6_no_pair_indexed_residue") == "PASS",
            "b3_pointer_resolved": subject.result("P7_pointer_resolves_canonical") == "PASS"
            and subject.result("P8_f0_hash_binding_fresh") == "PASS"
            and subject.result("P9_pointer_separation") == "PASS",
        },
    }

    ok = not p_fail and not k_fail and canonical_pass
    report["overall"] = "PASS" if ok else "FAIL"
    report["review_verdict_recommendation"] = "accept" if ok else "revise"

    if not args.check_only:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        snap = Path(args.snapshot_dir)
        snap.mkdir(parents=True, exist_ok=True)
        for p in [SUBJECT, CANON_F0, "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml"]:
            shutil.copy2(ROOT / p, snap / Path(p).name)
        manifest = {
            "task_id": report["task_id"],
            "generated_at": report["generated_at"],
            "snapshots": {Path(p).name: sha256_file(snap / Path(p).name) for p in [SUBJECT, CANON_F0, "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml"]},
        }
        (snap / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"wrote {out} ({sha256_file(out)[:12]}) and {snap}/MANIFEST.json")
    else:
        print(json.dumps(report["summary"], indent=2))

    print(
        "OVERALL", report["overall"],
        "| checks_failed", report["summary"]["checks_failed"],
        "| controls_failed", report["summary"]["controls_failed"],
        "| canonical_gate", report["summary"]["canonical_gate_verdict"],
        "| B1", report["summary"]["b1_duplicate_keys_closed"],
        "B2", report["summary"]["b2_d0_typing_closed"],
        "B3", report["summary"]["b3_pointer_resolved"],
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
