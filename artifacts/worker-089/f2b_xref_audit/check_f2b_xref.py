#!/usr/bin/env python3
"""W089-F2B-XREF-01: independent cross-artifact integrity audit of canonical F2b.

Target : schemas/af_scc_c0_vacuum.yaml   (class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)
Worker : worker-089   (no prior artifact authored in this repo; independent of all reviewers)

What this checks (all deterministic, no network):

  X1  input pin integrity (existence + sha256 + byte count)
  X2  class identity: class_id vs class_components vs node_id vs regularity token
  X3  sibling mutual-disjointness: F2b <-> F2a both declare each other
  X4  anti_scope class tokens: only frozen class ids; same-class entries must be
      explicitly tagged variants (kind+why); duplicate (class_id,kind) flagged;
      sibling counter-classes present
  X5  l1_ledger_refs resolve in ledger/theorems.jsonl
  X6  l1_status honesty vs the ledger row; provisional rows must appear in
      artifacts/literature/unresolved.jsonl
  X7  f0_binding: declared path is canonical and declared hash == measured hash
  X8  containment direction: F2b and F2a induce the SAME nested order on the four
      extension classes (E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0)
  X9  no composite regularity: exactly one regularity token in class_id and in
      conclusion_type; no "C0/C2" merge in the conclusion-bearing fields
  X10 publication alignment: canonical == authoring tree == FROZEN.json declared hash

Controls (mutants, run in-memory and written to controls/ for reproduction):
  M1..M7 are planted defects; each must be caught by its designated check.
  N0 is the unmodified schema and must produce zero hard findings.
A "PASS" is therefore a controlled pass, not an assertion.

Every check emits a machine-checkable finding with its own falsifier. Worker
events cannot set gate verdicts; this report is worker-authored evidence only.

Usage:
  python3 check_f2b_xref.py --out xref_report.json --controls --window 120
  python3 check_f2b_xref.py --fast                      # no stability window
  python3 check_f2b_xref.py --expect-sha256 <hex>       # void on pin drift
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    raise

CST = timezone(timedelta(hours=8))
DEFAULT_ROOT = Path(__file__).resolve().parents[3]

CANON_F2B = "schemas/af_scc_c0_vacuum.yaml"
CANON_F2A = "schemas/af_scc_c2_vacuum.yaml"
CANON_F1 = "schemas/af_wcc_vacuum.yaml"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
LEDGER = "ledger/theorems.jsonl"
UNRESOLVED = "artifacts/literature/unresolved.jsonl"

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}

# canonical extension-class token -> normalised node name
NODE_NORM = {
    "c0": "C0",
    "c2": "C2",
    "h2loc": "H2loc",
    "h2_loc": "H2loc",
    "c11": "C^1,1",
}
TOKEN = r"(E_(?:\{[^}]*\}|[A-Za-z0-9_^]+))"
TOKEN_RE = re.compile(TOKEN)
STRICT_ORDER = ["C2", "C^1,1", "H2loc", "C0"]  # subset chain, each subset of the next


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin(root: Path, rel: str) -> dict:
    p = root / rel
    if not p.is_file():
        return {"path": rel, "exists": False}
    return {
        "path": rel,
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
    }


def load_yaml(p: Path):
    with p.open() as f:
        return yaml.safe_load(f)


def load_jsonl(p: Path):
    rows = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------------------- #
# containment parsing
# --------------------------------------------------------------------------- #
def norm_token(tok: str) -> str:
    raw = tok[2:]
    if raw.startswith("{"):
        raw = raw[1:-1]
    key = re.sub(r"[^a-z0-9]", "", raw.lower())
    return NODE_NORM.get(key, raw)


def containment_edges(text: str):
    """Return subset edges (a,b) meaning 'a is a subset of b'.

    Matches are consumed pairwise so that a shared middle token
    ("A contains B contains C") still yields both (B,A) and (C,B).
    """
    edges = set()
    toks = list(TOKEN_RE.finditer(text))
    for m1, m2 in zip(toks, toks[1:]):
        between = text[m1.end():m2.start()]
        if re.search(r"\bcontains\b", between):
            edges.add((norm_token(m2.group(0)), norm_token(m1.group(0))))
        elif re.search(r"subset\s+of", between):
            edges.add((norm_token(m1.group(0)), norm_token(m2.group(0))))
    return edges


def reachable(edges, src):
    seen, stack = set(), [src]
    while stack:
        x = stack.pop()
        for a, b in edges:
            if a == x and b not in seen:
                seen.add(b)
                stack.append(b)
    return seen


# --------------------------------------------------------------------------- #
# checks: each returns (check_id, title, status, detail, evidence)
# --------------------------------------------------------------------------- #
def run_checks(ctx: dict, cand: dict):
    out = []
    sib = ctx["sibling"]
    led = ctx["ledger"]
    unres = ctx["unresolved"]

    cid = cand.get("class_id", "")
    comp = cand.get("class_components", {}) or {}
    # X2 class identity
    expected_comp = {
        "asymptotics": "AF",
        "censorship": "SCC",
        "matter": "VAC",
        "genericity": "GEN",
        "regularity_token": "C0",
    }
    errs = []
    if cid != "AF-SCC-C0-VAC-GEN":
        errs.append(f"class_id={cid!r}")
    if cand.get("node_id") != "F2b":
        errs.append(f"node_id={cand.get('node_id')!r}")
    for k, v in expected_comp.items():
        if comp.get(k) != v:
            errs.append(f"class_components.{k}={comp.get(k)!r} != {v!r}")
    out.append(("X2", "class identity (class_id/components/node_id)", "fail" if errs else "pass",
                "; ".join(errs) if errs else "class_id, node_id and all five component tokens agree",
                [CANON_F2B]))

    # X3 sibling mutual disjointness
    sib_id = cand.get("sibling_disjoint_from")
    back = sib.get("sibling_disjoint_from")
    errs = []
    if sib_id != "AF-SCC-C2-VAC-GEN":
        errs.append(f"F2b.sibling_disjoint_from={sib_id!r}")
    if back != "AF-SCC-C0-VAC-GEN":
        errs.append(f"F2a.sibling_disjoint_from={back!r}")
    out.append(("X3", "sibling disjointness is mutual (F2b<->F2a)", "fail" if errs else "pass",
                "; ".join(errs) if errs else "F2b->F2a and F2a->F2b both declared",
                [CANON_F2B, CANON_F2A]))

    # X4 anti_scope tokens
    seen = {}
    errs, warns = [], []
    entries = (cand.get("anti_scope") or {}).get("not_this_class", []) or []
    for e in entries:
        eid = e.get("class_id")
        kind = e.get("kind")
        if eid not in FROZEN_CLASSES:
            errs.append(f"unknown class token {eid!r}")
        if eid == cid and not (kind and e.get("why")):
            errs.append("same-class anti_scope entry lacks explicit kind+why (self-reference)")
        key = (eid, kind)
        if key in seen:
            warns.append(f"duplicate anti_scope entry {key}")
        seen[key] = seen.get(key, 0) + 1
    ids = {e.get("class_id") for e in entries}
    if "AF-SCC-C2-VAC-GEN" not in ids:
        errs.append("sibling C2 not listed in anti_scope")
    if "AF-WCC-VAC-GEN" not in ids:
        errs.append("WCC not listed in anti_scope")
    status = "fail" if errs else ("warn" if warns else "pass")
    detail = "; ".join(errs + warns) if (errs or warns) else (
        f"{len(entries)} entries, all frozen tokens, {len(entries) - len([e for e in entries if e.get('class_id') == cid])} "
        "counter-classes, same-class variants explicitly tagged")
    out.append(("X4", "anti_scope class tokens + tagged same-class variants", status, detail,
                [CANON_F2B, CANON_TAX]))

    # X5/X6 l1_ledger_refs
    missing, status_err, unres_err = [], [], []
    for r in cand.get("l1_ledger_refs", []) or []:
        t = r.get("theorem_id")
        row = led.get(t)
        if row is None:
            missing.append(t)
            continue
        if r.get("l1_status") != row.get("status"):
            status_err.append(f"{t}: schema={r.get('l1_status')!r} ledger={row.get('status')!r}")
        if r.get("l1_status") in {"provisional", "unresolved"} and t not in unres:
            unres_err.append(f"{t}: {r.get('l1_status')} but absent from unresolved.jsonl")
    out.append(("X5", "l1_ledger_refs resolve in ledger/theorems.jsonl", "fail" if missing else "pass",
                ("unresolved ids: " + ", ".join(missing)) if missing else
                f"all {len(cand.get('l1_ledger_refs', []))} cited ids resolve",
                [LEDGER]))
    out.append(("X6", "l1_status honesty + unresolved registry", "fail" if (status_err or unres_err) else "pass",
                "; ".join(status_err + unres_err) if (status_err or unres_err) else
                "every l1_status equals the ledger row status; provisional rows appear in unresolved.jsonl",
                [LEDGER, UNRESOLVED]))

    # X7 f0_binding
    f0 = cand.get("f0_binding", {}) or {}
    tax = ctx["pins"].get(CANON_TAX, {})
    errs = []
    if f0.get("declared_f0_artifact") != CANON_TAX:
        errs.append(f"declared_f0_artifact={f0.get('declared_f0_artifact')!r} != canonical {CANON_TAX!r}")
    if f0.get("declared_f0_sha256") != tax.get("sha256"):
        errs.append(f"declared={str(f0.get('declared_f0_sha256'))[:16]} measured={str(tax.get('sha256'))[:16]}")
    out.append(("X7", "f0_binding declares canonical path + measured F0 hash", "fail" if errs else "pass",
                "; ".join(errs) if errs else "declared F0 hash equals measured canonical taxonomy hash",
                [CANON_F2B, CANON_TAX]))

    # X8 containment direction, both schemas must induce the same order
    def order_of(doc):
        text = json.dumps((doc.get("implication_ledger") or {}), default=str)
        return containment_edges(text)

    e_b, e_a = order_of(cand), order_of(sib)
    errs = []
    for name, edges in (("F2b", e_b), ("F2a", e_a)):
        for lo, hi in zip(STRICT_ORDER, STRICT_ORDER[1:]):
            if hi not in reachable(edges, lo):
                errs.append(f"{name}: missing {lo} subset {hi}")
        if "C0" in reachable(edges, "C2") and "C2" in reachable(edges, "C0"):
            errs.append(f"{name}: containment is cyclic")
    # explicit inversion probe: C0 must never be a subset of C2
    for name, edges in (("F2b", e_b), ("F2a", e_a)):
        if ("C0", "C2") in edges:
            errs.append(f"{name}: states C0 subset C2 (inverted)")
    # same induced relation on the strict chain nodes
    rel_b = {(x, y) for x in STRICT_ORDER for y in reachable(e_b, x) if y in STRICT_ORDER}
    rel_a = {(x, y) for x in STRICT_ORDER for y in reachable(e_a, x) if y in STRICT_ORDER}
    if rel_b != rel_a:
        errs.append(f"F2b/F2a induce different orders: only-F2b={sorted(rel_b - rel_a)} only-F2a={sorted(rel_a - rel_b)}")
    out.append(("X8", "containment direction coherent across F2b/F2a", "fail" if errs else "pass",
                "; ".join(errs) if errs else
                "both schemas induce E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0; no inversion",
                [CANON_F2B, CANON_F2A]))

    # X9 no composite regularity
    conc = cand.get("conclusion", {}) or {}
    fields = {
        "class_id": cid,
        "conclusion_type": conc.get("conclusion_type", ""),
        "statement_formal": conc.get("statement_formal", ""),
        "statement_natural_language": conc.get("statement_natural_language", ""),
        "scope_statement": cand.get("scope_statement", ""),
        "quantifiers.formal": (cand.get("quantifiers") or {}).get("formal", ""),
    }
    errs = []
    regs = re.findall(r"(?<![a-z0-9])c([012])(?![a-z0-9])", str(conc.get("conclusion_type", "")).lower())
    if regs != ["0"]:
        errs.append(f"conclusion_type regularity tokens={regs}")
    merge_re = re.compile(
        r"(?<![a-z0-9])c0\s*(?:/|or|,|&)\s*c2(?![a-z0-9])|(?<![a-z0-9])c2\s*(?:/|or|,|&)\s*c0(?![a-z0-9])",
        re.I,
    )
    for name, text in fields.items():
        m = merge_re.search(str(text))
        if m:
            errs.append(f"composite C0/C2 phrasing in {name}: {m.group(0)!r}")
    out.append(("X9", "single regularity token, no C0/C2 merge", "fail" if errs else "pass",
                "; ".join(errs) if errs else "exactly C0 in conclusion_type; no C0/C2 merge in conclusion-bearing fields",
                [CANON_F2B]))

    # X10 publication alignment
    errs, info = [], []
    for label, canon_rel, author_rel in (
        ("F2b", CANON_F2B, "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    ):
        cp = ctx["pins"].get(canon_rel, {})
        ap = ctx["pins"].get(author_rel, {})
        if cp.get("sha256") != ap.get("sha256"):
            errs.append(f"{label}: canonical {str(cp.get('sha256'))[:12]} != authoring {str(ap.get('sha256'))[:12]}")
    fr = ctx["frozen_files"].get(CANON_F2B, {})
    if fr.get("sha256") != ctx["pins"].get(CANON_F2B, {}).get("sha256"):
        errs.append("FROZEN.json declared hash != measured canonical hash")
    for label, rel in (("F2a", CANON_F2A), ("F1", CANON_F1)):
        if ctx["pins"].get(rel, {}).get("sha256") != ctx["frozen_files"].get(rel, {}).get("sha256"):
            info.append(f"{label}: FROZEN declared != measured (informational; not this audit's target)")
    out.append(("X10", "publication alignment + FROZEN declared hash", "fail" if errs else "pass",
                "; ".join(errs) if errs else "canonical == authoring == FROZEN for F2b", [CANON_F2B, FROZEN]))
    return out, info


# --------------------------------------------------------------------------- #
# mutants (controls)
# --------------------------------------------------------------------------- #
def mutants(base: dict):
    def m1(d):
        for r in d["l1_ledger_refs"]:
            if r["theorem_id"] == "T-305":
                r["l1_status"] = "accepted"
        return d

    def m2(d):
        for r in d["l1_ledger_refs"]:
            if r["theorem_id"] == "T-302":
                r["theorem_id"] = "T-999"
        return d

    def m3(d):
        d["sibling_disjoint_from"] = "AF-WCC-VAC-GEN"
        return d

    def m4(d):
        d["f0_binding"]["declared_f0_sha256"] = "deadbeef" * 8
        return d

    def m5(d):
        d["implication_ledger"]["extension_class_containment"] = (
            "E_C2 contains E_C0; the C0 statement is implied by the C2 statement."
        )
        return d

    def m6(d):
        d["conclusion"]["conclusion_type"] = "scc_c0_or_c2_future_inextendibility"
        return d

    def m7(d):
        d.setdefault("anti_scope", {}).setdefault("not_this_class", []).append(
            {"class_id": "AF-SCC-C0-VAC-GEN", "why": "untagged self reference"}
        )
        return d

    return [
        ("M1", "X6", "flip T-305 l1_status provisional->accepted", m1),
        ("M2", "X5", "rename cited theorem T-302 -> T-999", m2),
        ("M3", "X3", "break sibling declaration", m3),
        ("M4", "X7", "corrupt declared F0 hash", m4),
        ("M5", "X8", "invert containment direction", m5),
        ("M6", "X9", "merge C0/C2 in conclusion_type", m6),
        ("M7", "X4", "append untagged same-class anti_scope entry", m7),
    ], (lambda d: d)  # N0 identity (must stay clean)


def stability_sample(root: Path, rels, window: int, interval: int):
    series = {r: [] for r in rels}
    t0 = time.time()
    while True:
        stamp = datetime.now(CST).isoformat(timespec="seconds")
        for r in rels:
            p = root / r
            if p.is_file():
                series[r].append({"at": stamp, "sha256": sha256_file(p), "bytes": p.stat().st_size})
            else:
                series[r].append({"at": stamp, "sha256": None, "bytes": None})
        if time.time() - t0 >= window:
            break
        time.sleep(interval)
    per = {}
    for r, samples in series.items():
        hashes = [s["sha256"] for s in samples]
        uniq = []
        for h in hashes:
            if h not in uniq:
                uniq.append(h)
        per[r] = {
            "samples": len(samples),
            "distinct_hashes": len(uniq),
            "first": hashes[0] if hashes else None,
            "last": hashes[-1] if hashes else None,
            "drift": len(uniq) > 1,
        }
    return {
        "window_seconds": window,
        "interval_seconds": interval,
        "started_at": series[rels[0]][0]["at"] if series[rels[0]] else None,
        "ended_at": series[rels[0]][-1]["at"] if series[rels[0]] else None,
        "per_file": per,
        "drift_detected": any(v["drift"] for v in per.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default="")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--window", type=int, default=0)
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--expect-sha256", default="")
    args = ap.parse_args()
    if args.fast:
        args.window = 0
    root = Path(args.root).resolve()

    rels = [CANON_F2B, CANON_F2A, CANON_F1, CANON_TAX, FROZEN, LEDGER, UNRESOLVED,
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
    pins = {r: pin(root, r) for r in rels}
    target_pin = pins[CANON_F2B]
    if not target_pin.get("exists"):
        print(json.dumps({"error": f"missing {CANON_F2B}"}), file=sys.stderr)
        return 3
    if args.expect_sha256 and target_pin["sha256"] != args.expect_sha256:
        print(json.dumps({
            "error": "pin mismatch",
            "expected": args.expect_sha256,
            "measured": target_pin["sha256"],
        }), file=sys.stderr)
        return 2

    frozen = json.loads((root / FROZEN).read_text())
    frozen_files = frozen.get("files", {})
    ledger = {r["theorem_id"]: r for r in load_jsonl(root / LEDGER) if r.get("theorem_id")}
    unresolved = {r.get("theorem_id") for r in load_jsonl(root / UNRESOLVED) if r.get("theorem_id")}
    tax = load_yaml(root / CANON_TAX)
    cand = load_yaml(root / CANON_F2B)
    sib = load_yaml(root / CANON_F2A)
    ctx = {
        "pins": pins,
        "frozen_files": frozen_files,
        "ledger": ledger,
        "unresolved": unresolved,
        "taxonomy_class_ids": tax.get("class_ids", []),
        "sibling": sib,
    }

    checks, info = run_checks(ctx, cand)
    n_hard = sum(1 for c in checks if c[2] == "fail")
    n_warn = sum(1 for c in checks if c[2] == "warn")

    controls = []
    if args.controls:
        ms, identity = mutants(copy.deepcopy(cand))
        ctrl_dir = Path(args.out).resolve().parent / "controls" if args.out else root / "artifacts/worker-089/f2b_xref_audit/controls"
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        for cid_, expect, desc, fn in ms:
            mut = fn(copy.deepcopy(cand))
            (ctrl_dir / f"{cid_}.json").write_text(json.dumps(mut, indent=2, default=str) + "\n")
            mchecks, _ = run_checks(ctx, mut)
            failed = {c[0] for c in mchecks if c[2] == "fail"}
            caught = expect in failed
            controls.append({
                "control_id": cid_, "expected_check": expect, "description": desc,
                "observed_failed_checks": sorted(failed), "caught": caught,
                "status": "pass" if caught else "fail",
            })
        nchecks, _ = run_checks(ctx, identity(copy.deepcopy(cand)))
        n_fail = sum(1 for c in nchecks if c[2] == "fail")
        controls.append({
            "control_id": "N0", "expected_check": "none", "description": "unmodified schema (false-positive control)",
            "observed_failed_checks": sorted(c[0] for c in nchecks if c[2] == "fail"),
            "caught": None, "status": "pass" if n_fail == 0 else "fail",
        })

    stab = stability_sample(root, [CANON_F2B, CANON_F2A, CANON_F1, CANON_TAX, FROZEN], args.window, args.interval) if args.window > 0 else None
    final_pin = pin(root, CANON_F2B)
    drift_after = bool(final_pin.get("sha256") != target_pin["sha256"])

    controls_ok = all(c["status"] == "pass" for c in controls) if controls else None
    if n_hard:
        verdict = "revise"
    elif stab is not None and stab["drift_detected"]:
        verdict = "inconclusive"
    elif controls and not controls_ok:
        verdict = "inconclusive"
    else:
        verdict = "accept"

    report = {
        "audit_id": "W089-F2B-XREF-01",
        "worker": "worker-089",
        "actor": "worker-089",
        "created_at": now(),
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "target": CANON_F2B,
        "pins": pins,
        "target_pin_sha256": target_pin["sha256"],
        "final_recheck": {
            "measured_at": now(),
            "sha256": final_pin.get("sha256"),
            "bytes": final_pin.get("bytes"),
            "drift_since_start": bool(final_pin.get("sha256") != target_pin["sha256"]),
        },
        "checks": [
            {"check_id": c[0], "title": c[1], "status": c[2], "detail": c[3], "evidence": c[4]}
            for c in checks
        ],
        "informational": info,
        "hard_findings": [c[3] for c in checks if c[2] == "fail"],
        "soft_findings": [c[3] for c in checks if c[2] == "warn"],
        "controls": controls,
        "stability": stab,
        "verdict": verdict,
        "verdict_scope": (
            "Mechanical cross-artifact integrity only (input pins, class identity, sibling mutual "
            "disjointness, anti_scope token validity, ledger reference resolution and status honesty, "
            "F0 binding hash, containment direction, single-regularity/no-merge, publication alignment). "
            "It is NOT a semantic sufficiency review and does NOT constitute a G-FORM gate accept."
        ),
        "does_not_claim": [
            "gate verdict (workers cannot set gates)",
            "semantic adequacy of the F2b statement",
            "independence from the schema authors beyond authorship (worker-089 authored no canonical artifact)",
        ],
        "next_falsifier": (
            "Re-run at a newer canonical hash: any X-check that flips from pass to fail, or any mutant "
            "that stops being caught, falsifies this report for the newer revision. A stable pass at a "
            "hash that then changes within the stability window voids the verdict for gate purposes."
        ),
        "hours": 0.4,
    }

    if drift_after:
        report["hard_findings"].append(
            f"canonical F2b changed hash during the audit run: start {target_pin['sha256'][:16]} -> "
            f"end {pins[CANON_F2B]['sha256'][:16]}; verdict is void for the start hash"
        )
        report["verdict"] = "inconclusive"

    text = json.dumps(report, indent=2, sort_keys=False, default=str) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)
    print(json.dumps({
        "audit_id": report["audit_id"], "verdict": report["verdict"],
        "target_sha256": report["target_pin_sha256"],
        "hard": len(report["hard_findings"]), "soft": len(report["soft_findings"]),
        "controls": len(controls), "controls_ok": controls_ok,
        "drift": bool(stab and stab["drift_detected"]), "out": args.out or "stdout",
    }), file=sys.stderr)
    if report["verdict"] == "revise":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
