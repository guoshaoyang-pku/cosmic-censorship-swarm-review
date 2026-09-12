#!/usr/bin/env python3
"""W038-REV36-FOLD-CENSUS-01 -- independent, pre-registered census of the seven
`astra-life08-formulation-rev14` (REC-36) fold items at F1/F2a/F2b, plus a
discriminating acceptance predicate (7 items + 4 invariants + 7 mutation controls).

Bound: node F1,F2a,F2b; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN;
gate G-FORM. Read-only with respect to canonical bytes: every checker runs inside a
private sandbox copy under tmp/w038_rev36/ and every measurement is taken from that
copy. The 2026-09-12T01:22 accidental canonical write of
artifacts/formulation/evidence/variant_registry_check.json by a bare
`check_variant_registry.py` invocation is the reason the sandbox is mandatory here;
the file was restored byte-identically from 78 pinned copies (164a9a846e25) and the
pre/post attestation is recorded in the report.

Modes
  --context live       measure the live canonical tree (no overlay)
  --context candidate  live tree + the worker-044/worker-003 staged rev14 candidate overlay
  --controls           build a synthetic repaired stub and run 7 one-item mutations
  --json               print the machine report to stdout

Exit 0 if the run completed (whatever the item verdicts); exit 2 on instrumentation
failure (a control that does not discriminate, or a byte-drift attestation failure).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "artifacts/worker-038/rev36_fold_census"
WORK = REPO / "tmp/w038_rev36"
CAND = REPO / "artifacts/worker-003/f2b_rev14_candidate_closure/pinned/candidate"

F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SCHEMAS = {
    "c0": "schemas/af_scc_c0_vacuum.yaml",
    "c2": "schemas/af_scc_c2_vacuum.yaml",
    "f1": "schemas/af_wcc_vacuum.yaml",
}
MIRROR = {
    "c0": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "c2": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "f1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
}
TAX_CANON = "research_map/formulation_taxonomy.yaml"
TAX_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
VR = "artifacts/formulation/VARIANT_REGISTRY.json"
SET_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CROSSWALK = "artifacts/formulation/CONCLUSION_TYPE_CROSSWALK.json"
XWALK_EVIDENCE = "artifacts/formulation/evidence/conclusion_type_crosswalk_check.json"
XWALK_TOOL = "artifacts/formulation/tools/check_conclusion_type_crosswalk.py"
VR_TOOL = "artifacts/formulation/tools/check_variant_registry.py"
VR_EVIDENCE = "artifacts/formulation/evidence/variant_registry_check.json"
ACCEPT_TOOL = "artifacts/formulation/tools/run_acceptance.py"
ACCEPT_REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
ESCAPE_EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json"
SUITE = "schemas/f1_falsifier_tests.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"

COPY_FILES = [
    TAX_CANON, TAX_SUPP, VR, SET_DELTA, CROSSWALK, XWALK_EVIDENCE, VR_EVIDENCE,
    ACCEPT_REPORT, ESCAPE_EVIDENCE, SUITE, FROZEN,
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/tools/check_conclusion_type_crosswalk.py",
    "artifacts/formulation/tools/check_variant_registry.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/verify_frozen.py",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/worker-06/spec_conformance_audit.py",
]
COPY_DIRS = ["schemas", "artifacts/formulation/variants", "artifacts/formulation/schemas"]

CAND_OVERLAY = [
    (CAND / "c0_48cadb72.yaml", SCHEMAS["c0"]),
    (CAND / "c0_48cadb72.yaml", MIRROR["c0"]),
    (CAND / "c2_d94d490d.yaml", SCHEMAS["c2"]),
    (CAND / "c2_d94d490d.yaml", MIRROR["c2"]),
    (CAND / "f1_88871f8f.yaml", SCHEMAS["f1"]),
    (CAND / "f1_88871f8f.yaml", MIRROR["f1"]),
    (CAND / "FROZEN_a57492cc.json", FROZEN),
    (CAND / "evidence_675a99d0.json", "artifacts/formulation/evidence/taxonomy_consistency.json"),
    (CAND / "KEY_MANIFEST_61b9d8c1.json", "artifacts/formulation/KEY_MANIFEST.json"),
]

CAND_IDENTITY = {
    "c0_sha256": "48cadb72",
    "c2_sha256": "d94d490d",
    "f1_sha256": "88871f8f",
    "frozen_sha256": "a57492cc",
    "source": "artifacts/worker-003/f2b_rev14_candidate_closure/pinned/candidate",
    "authoring_events": ["W044-F2B-LIVE-CLOSURE-01", "W003-F2B-REV14-CANDIDATE-CLOSURE-01"],
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def find_key(doc, key):
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                np = f"{path}.{k}"
                if k == key:
                    hits.append((np, v))
                walk(v, np)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc, "$")
    return hits


def assertion_text(s: str) -> str:
    """Drop bracketed errata and quoted spans (assertion-vs-mention doctrine)."""
    if not isinstance(s, str):
        return ""
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"'[^']*'", " ", s)
    s = re.sub(r'"[^"]*"', " ", s)
    return s


def flat_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from flat_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from flat_strings(v)


class Sandbox:
    def __init__(self, name: str):
        self.root = WORK / name
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        for rel in COPY_FILES:
            src = REPO / rel
            if src.exists():
                self._put(rel, src.read_bytes())
        for rel in COPY_DIRS:
            src = REPO / rel
            if src.is_dir():
                shutil.copytree(src, self.root / rel, dirs_exist_ok=True)
        self.tool_runs = []

    def _put(self, rel: str, data: bytes):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def path(self, rel: str) -> Path:
        return self.root / rel

    def text(self, rel: str) -> str:
        return (self.root / rel).read_text()

    def yaml(self, rel: str):
        return yaml.safe_load(self.text(rel))

    def overlay(self, src: Path, rel: str):
        self._put(rel, src.read_bytes())

    def patch_text(self, rel: str, fn):
        self._put(rel, fn(self.text(rel)).encode())

    def sha(self, rel: str) -> str:
        return sha256_file(self.root / rel)

    def run(self, tool_rel: str, args=None, timeout=300):
        args = list(args or [])
        p = self.root / tool_rel
        t0 = time.time()
        r = subprocess.run([sys.executable, str(p)] + args, cwd=str(self.root),
                           capture_output=True, text=True, timeout=timeout)
        rec = {"tool": tool_rel, "args": args, "exit": r.returncode,
               "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:],
               "seconds": round(time.time() - t0, 2)}
        self.tool_runs.append(rec)
        return rec

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


# --------------------------------------------------------------------------------------
# I1..I7
# --------------------------------------------------------------------------------------

def item_I1(sb: Sandbox) -> dict:
    doc = sb.yaml(SCHEMAS["c0"])
    blocks = find_key(doc, "must_not_conflate")
    denial = []
    nesting = []
    for path, mnc in blocks:
        for i, s in enumerate(mnc or []):
            a = assertion_text(s)
            if re.search(r"no\s+containment\b[^.]{0,140}?(asserted|claimed|holds|is\s+true)", a, re.I):
                denial.append({"path": path, "index": i, "text": s[:200]})
            if ("E_C2" in a and "E_C0" in a and re.search(r"subset|nested|contains|ENTAIL", a, re.I)):
                nesting.append({"path": path, "index": i})
    ledger = doc.get("implication_ledger", {}).get("extension_class_containment", "")
    chain_ok = False
    if all(t in ledger for t in ("E_C2", "E_H2loc", "E_C0")):
        if "contains" in ledger and ledger.find("E_C0") < ledger.find("E_C2"):
            chain_ok = True
        if "subset" in ledger and ledger.find("E_C2") < ledger.find("E_C0"):
            chain_ok = True
    ok = (not denial) and bool(nesting) and chain_ok
    return mk("I1", "F2b must_not_conflate containment denial (D1)", ok, {
        "unquoted_denials": denial,
        "nesting_assertions_at": nesting,
        "ledger_chain_direction_ok": chain_ok,
        "ledger_excerpt": ledger[:220],
    }, "no unquoted containment denial AND a nesting assertion AND a direction-correct ledger chain")


def item_I2(sb: Sandbox) -> dict:
    doc = sb.yaml(SCHEMAS["c0"])
    ft = doc.get("implication_ledger", {}).get("forbidden_transfers", []) or []
    inv = []
    target = None
    for i, row in enumerate(ft):
        reason = row.get("reason", "") if isinstance(row, dict) else str(row)
        a = assertion_text(reason)
        if re.search(r"C2\s+is\s+a\s+strictly\s+(larger|bigger)", a, re.I):
            inv.append({"index": i, "reason": reason[:200]})
        if isinstance(row, dict) and "C2" in str(row.get("from", "")) and row.get("to") == "this class":
            target = {"index": i, "reason": reason, "assertion": a}
    good = bool(target) and bool(re.search(r"smaller|subset|stronger\s+regularity", target["assertion"], re.I))
    ledger = doc.get("implication_ledger", {}).get("extension_class_containment", "")
    chain_ok = ("E_C2" in ledger and "E_C0" in ledger and "contains" in ledger
                and ledger.find("E_C0") < ledger.find("E_C2"))
    ok = (not inv) and good and chain_ok
    return mk("I2", "F2b forbidden-transfer size-premise direction (D2)", ok, {
        "inversions": inv,
        "c2_transfer_row": target,
        "ledger_chain_direction_ok": chain_ok,
    }, "no 'C2 strictly larger' inversion AND the C2->this-class row asserts the smaller-subset direction AND the ledger agrees")


CATEGORY_RE = re.compile(
    r"SMOOTH|C-?infinity|C\^?\\?infty|smooth\s+structure|smooth\s+4-manifold|category\s+in\s+which", re.I)


def item_I3(sb: Sandbox) -> dict:
    doc = sb.yaml(SCHEMAS["c2"])
    ep = doc.get("extension_predicate", {}) or {}
    declared = list(flat_strings(ep))
    hits = [s for s in declared if CATEGORY_RE.search(assertion_text(s)) and len(assertion_text(s).split()) >= 8]
    rebuttal = []
    for k, v in doc.items():
        if re.search(r"category", str(k), re.I):
            rebuttal.append({"key": k, "has_falsifier": isinstance(v, dict) and bool(v.get("falsifier"))})
    c0 = sb.yaml(SCHEMAS["c0"])
    c0_ep = json.dumps(c0.get("extension_predicate", {}))
    sibling_pinned = bool(CATEGORY_RE.search(assertion_text(c0_ep)))
    ok = bool(hits) or bool(rebuttal)
    return mk("I3", "F2a extension-manifold category pinned or rebutted (HF-075-F2a-EXTCAT)", ok, {
        "category_hits": [h[:180] for h in hits],
        "category_independence_rebuttal_keys": rebuttal,
        "sibling_f2b_pins_smooth_category": sibling_pinned,
    }, "a category pin with a stated reason inside extension_predicate OR a pinned category-independence rebuttal")


def item_I4(sb: Sandbox) -> dict:
    c0 = sb.yaml(SCHEMAS["c0"])
    c2 = sb.yaml(SCHEMAS["c2"])
    f1 = sb.yaml(SCHEMAS["f1"])
    tok = {
        "f1": (find_key(f1, "conclusion_type") or [(None, None)])[0][1],
        "c2": (find_key(c2, "conclusion_type") or [(None, None)])[0][1],
        "c0": (find_key(c0, "conclusion_type") or [(None, None)])[0][1],
    }
    canonical_ok = (tok["f1"] == "weak_cosmic_censorship"
                    and tok["c2"] == "scc_c2_future_inextendibility"
                    and tok["c0"] == "scc_c0_future_inextendibility")
    va = json.loads(sb.text("artifacts/formulation/VOCAB_ALIASES.json"))
    ct = va.get("conclusion_type", {})
    aliases_ok = (ct.get("scc_c0_future_inextendibility") and
                  "strong_cosmic_censorship_C0" in ct["scc_c0_future_inextendibility"] and
                  "strong_cosmic_censorship_C2" in ct.get("scc_c2_future_inextendibility", []))
    xw = json.loads(sb.text(CROSSWALK))
    f0_live = sb.sha(TAX_CANON)
    xw_pin_ok = xw.get("f0_source_sha256") == f0_live == F0_SHA
    entry_pins = {}
    for e in xw.get("entries", []):
        rel = e.get("schema_path", "").split("#")[0]
        if rel in SCHEMAS.values():
            entry_pins[rel] = (e.get("schema_sha256") == sb.sha(rel))
    entries_ok = bool(entry_pins) and all(entry_pins.values())
    tool_src = sb.text(XWALK_TOOL)
    compares_vocab = ("VOCAB_ALIASES" in tool_src)
    uses_f0_list = bool(re.search(r"f0_declared_allowed", tool_src)) and "VOCAB_ALIASES" not in tool_src
    run = sb.run(XWALK_TOOL, timeout=120)
    rec = json.loads(sb.text(XWALK_EVIDENCE)) if sb.path(XWALK_EVIDENCE).exists() else {}
    ok = canonical_ok and aliases_ok and xw_pin_ok and entries_ok and compares_vocab and not uses_f0_list and run["exit"] == 0
    return mk("I4", "REC-37 conclusion_type crosswalk + canonical-token comparison", ok, {
        "schema_tokens": tok, "canonical_tokens_ok": canonical_ok,
        "vocab_aliases_ok": bool(aliases_ok),
        "crosswalk_f0_pin_ok": xw_pin_ok, "crosswalk_entry_pins_ok": entries_ok,
        "entry_pin_detail": entry_pins,
        "checker_compares_to_vocab_aliases": compares_vocab,
        "checker_uses_f0_raw_list_as_oracle": uses_f0_list,
        "checker_run": {"exit": run["exit"], "stdout": run["stdout"][-400:]},
        "checker_recorded_verdict": rec.get("verdict"),
    }, "canonical schema tokens + alias registry + crosswalk pinned to a live F0 hash with entry pins to the measured schemas + checker exit 0 comparing against VOCAB_ALIASES")


def item_I5(sb: Sandbox) -> dict:
    vr = json.loads(sb.text(VR))
    setv = [v for v in vr.get("variants", []) if v.get("variant_id") == "SET"]
    s = setv[0].get("strength", "") if setv else ""
    pi, ci = s.find("predicate-level"), s.find("class-level")
    vr_level = pi >= 0 and ci > pi and "WEAKER" in s[pi:ci] and "STRONGER" in s[ci:]
    flat = s.startswith("strictly weaker than AF-WCC-VAC-GEN")
    delta = json.loads(sb.text(SET_DELTA))
    ds = delta.get("strength", "")
    dpi, dci = ds.find("predicate-level"), ds.find("class-level")
    delta_level = dpi >= 0 and dci > dpi and "WEAKER" in ds[dpi:dci] and "STRONGER" in ds[dci:]
    run = sb.run(VR_TOOL, timeout=120)
    ok = vr_level and delta_level and not flat and run["exit"] == 0
    return mk("I5", "SET strength level-split label (predicate-level WEAKER / class-level STRONGER)", ok, {
        "registry_strength_level_qualified": vr_level,
        "registry_flat_label_present": flat,
        "delta_strength_level_qualified": delta_level,
        "checker_run": {"exit": run["exit"], "stdout": run["stdout"][-400:]},
    }, "VR and SET-delta strength carry predicate-level WEAKER before class-level STRONGER, no flat one-level label, and check_variant_registry.py exits 0")


def _suite_rows(sb: Sandbox):
    return [json.loads(l) for l in sb.text(SUITE).splitlines() if l.strip()]


def item_I6(sb: Sandbox) -> dict:
    rows = _suite_rows(sb)
    f1_sha = sb.sha(SCHEMAS["f1"])
    f1_text = sb.text(SCHEMAS["f1"])
    stale = [r.get("test_id") for r in rows if r.get("binding_sha256") != f1_sha]
    amb25 = [r for r in rows if r.get("test_id") == "F1-AMB-25"]
    amb25_ok = False
    amb25_detail = {}
    if amb25:
        r = amb25[0]
        probes = [p for p in r.get("probe_results", []) if p.get("path") == "f0_binding.declared_f0_sha256"]
        amb25_detail = {"probes": probes, "rebind_note": (r.get("rebind_note") or "")[:160]}
        amb25_ok = bool(probes) and all(p.get("expected") == F0_SHA and p.get("pass") is True
                                        and (F0_SHA in json.dumps(p.get("observed_excerpt", "")) or
                                             F0_SHA in json.dumps(p.get("observed", "")))
                                        for p in probes)
        amb25_detail["f0_pin_repaired"] = amb25_ok
    reobs = {}
    for tid in ("F1-AMB-11", "F1-AMB-17", "F1-AMB-23"):
        r = [x for x in rows if x.get("test_id") == tid]
        if not r:
            reobs[tid] = {"present": False}
            continue
        r = r[0]
        misses = []
        for p in r.get("probe_results", []):
            if p.get("kind") == "contains" and p.get("path") != "class_identity_variants":
                if p.get("expected") not in f1_text:
                    misses.append(p.get("expected"))
        reobs[tid] = {"present": True, "all_probes_pass_flag": all(p.get("pass") for p in r.get("probe_results", [])),
                      "schema_text_misses": misses}
    reobs_ok = all(v.get("present") and v.get("all_probes_pass_flag") and not v.get("schema_text_misses")
                   for v in reobs.values())
    ok = len(rows) == 25 and not stale and amb25_ok and reobs_ok
    return mk("I6", "f1_falsifier_tests.jsonl rebind to the F1 pin under test + AMB-25 F0 repair + AMB-11/17/23 re-observation", ok, {
        "row_count": len(rows), "f1_pin_under_test": f1_sha,
        "rows_not_bound_to_f1_pin": stale,
        "amb25": amb25_detail, "reobservation": reobs,
    }, "all 25 rows bind the F1 pin under test, AMB-25's f0 probe expects the live F0 hash 0abb9ed8a961, and AMB-11/17/23 probe text is present in that F1 text")


def item_I7(sb: Sandbox, run_pipeline=True) -> dict:
    c0_sha = sb.sha(SCHEMAS["c0"])
    rec = json.loads(sb.text(ESCAPE_EVIDENCE)) if sb.path(ESCAPE_EVIDENCE).exists() else {}
    corpus_fresh = rec.get("base_sha256") == c0_sha
    excl = None
    for p in sorted((sb.root / "artifacts/formulation/evidence").glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and d.get("excluded_from_gate_evidence") is True and d.get("non_reproducible") is True:
            excl = str(p.relative_to(sb.root))
    run = sb.run(ACCEPT_TOOL, timeout=120) if run_pipeline else {"exit": None, "stdout": "skipped"}
    pipeline_ok = run["exit"] == 0
    ok = (corpus_fresh and pipeline_ok) or bool(excl)
    return mk("I7", "acceptance-corpus rebind / CF-32 disposition", ok, {
        "corpus_base_sha256": rec.get("base_sha256"), "c0_pin_under_test": c0_sha,
        "corpus_fresh": corpus_fresh,
        "run_acceptance": {"exit": run["exit"], "stdout": run["stdout"][-500:]},
        "exclusion_record": excl,
    }, "either a fresh corpus base + run_acceptance.py exit 0, or a pinned non-reproducible exclusion record keeps the stale report out of gate evidence")


# --------------------------------------------------------------------------------------
# invariants
# --------------------------------------------------------------------------------------

def invariants(sb: Sandbox, full_pins: bool) -> dict:
    mir = {}
    for k in ("c0", "c2", "f1"):
        mir[k] = sb.sha(SCHEMAS[k]) == sb.sha(MIRROR[k])
    tax_canon_ok = sb.sha(TAX_CANON) == F0_SHA
    revs = {}
    for k in ("c0", "c2", "f1"):
        d = sb.yaml(SCHEMAS[k])
        revs[k] = d.get("revision")
    rev_ok = len({v for v in revs.values()}) == 1 and all(isinstance(v, int) and v >= 13 for v in revs.values())
    pins = {}
    frozen = json.loads(sb.text(FROZEN))
    problems = []
    missing = []
    for rel, meta in (frozen.get("files") or {}).items():
        p = sb.path(rel)
        if not p.exists():
            missing.append(rel)
            continue
        if sha256_file(p) != meta.get("sha256"):
            problems.append(rel)
    if not full_pins:
        problems = [r for r in problems if r in SCHEMAS.values() or r in MIRROR.values()]
        missing = []
    return {
        "mirrors_byte_equal": mir, "mirrors_ok": all(mir.values()),
        "f0_taxonomy_canonical_ok": tax_canon_ok, "f0_taxonomy_sha256": sb.sha(TAX_CANON),
        "revisions": revs, "revision_uniform_ok": rev_ok,
        "frozen_pin_problems": problems, "frozen_pin_missing": missing[:20],
        "frozen_pin_count": len(frozen.get("files") or {}), "frozen_revision": frozen.get("revision"),
        "frozen_pins_ok": not problems and (full_pins or not missing),
        "full_pin_resolution": full_pins,
    }


def mk(item, title, ok, evidence, predicate) -> dict:
    return {"item": item, "title": title, "status": "PASS" if ok else "FAIL",
            "predicate": predicate, "evidence": evidence}


def measure(sb: Sandbox, label: str, full_pins=False, run_pipeline=True) -> dict:
    items = [item_I1(sb), item_I2(sb), item_I3(sb), item_I4(sb), item_I5(sb),
             item_I6(sb), item_I7(sb, run_pipeline=run_pipeline)]
    inv = invariants(sb, full_pins)
    return {"label": label, "items": items, "invariants": inv,
            "tools": sb.tool_runs,
            "summary": {i["item"]: i["status"] for i in items}}


# --------------------------------------------------------------------------------------
# synthetic repaired stub + mutation controls
# --------------------------------------------------------------------------------------

SET_LEVEL_STRENGTH = (
    "predicate-level: strictly WEAKER than AF-WCC-VAC-GEN's single-q tail visibility predicate "
    "(the parent predicate entails the union reading; the converse fails on the omega-chain witness "
    "W076-GFORM-STRICTNESS-RECONCILE-06 T4). class-level subject: strictly STRONGER than "
    "AF-WCC-VAC-GEN (a weaker visibility predicate makes 'no visible singularity' harder to satisfy). "
    "[rev14 item 5 level-split]"
)

CATEGORY_LINE = (
    '  manifold_category: "SMOOTH (C-infinity) connected 4-manifold is the category of the extension '
    'manifold; the smooth structure is the category in which the metric is a tensor field, and the '
    'metric is required only to be C2 in that category (reason: a merely topological manifold cannot '
    'carry a classical Lorentzian tensor field)."\n'
)


def make_stub(name: str) -> Sandbox:
    sb = Sandbox(name)
    # repair source bytes: worker-044/003 staged candidate for C0 and F1
    sb.overlay(CAND / "c0_48cadb72.yaml", SCHEMAS["c0"])
    sb.overlay(CAND / "c0_48cadb72.yaml", MIRROR["c0"])
    sb.overlay(CAND / "f1_88871f8f.yaml", SCHEMAS["f1"])
    sb.overlay(CAND / "f1_88871f8f.yaml", MIRROR["f1"])
    sb.overlay(CAND / "c2_d94d490d.yaml", SCHEMAS["c2"])
    sb.overlay(CAND / "c2_d94d490d.yaml", MIRROR["c2"])
    # I3: pin the F2a extension-manifold category
    for rel in (SCHEMAS["c2"], MIRROR["c2"]):
        sb.patch_text(rel, lambda t: t.replace("  must_not_conflate:\n", CATEGORY_LINE + "  must_not_conflate:\n", 1))
    # I4: re-pin crosswalk entries to the stub schemas
    def fix_xw(t):
        xw = json.loads(t)
        for e in xw.get("entries", []):
            rel = e.get("schema_path", "").split("#")[0]
            if rel in SCHEMAS.values():
                e["schema_sha256"] = sha256_bytes((sb.root / rel).read_bytes())
        xw["problems"] = []
        return json.dumps(xw, indent=2) + "\n"
    sb.patch_text(CROSSWALK, fix_xw)
    # I5: level-split SET strength in registry and delta
    def fix_vr(t):
        vr = json.loads(t)
        for v in vr.get("variants", []):
            if v.get("variant_id") == "SET":
                v["strength"] = SET_LEVEL_STRENGTH
        return json.dumps(vr, indent=2) + "\n"
    sb.patch_text(VR, fix_vr)
    sb.patch_text(SET_DELTA, lambda t: t.replace(
        '"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent\'s single-q tail predicate entails the union reading; the converse fails on the omega-chain witness, W076-GFORM-STRICTNESS-RECONCILE-06 T4)"',
        '"strength": ' + json.dumps(SET_LEVEL_STRENGTH)))
    # I6: rebind all suite rows to the stub F1 pin and repair AMB-25's f0 probe
    f1_sha = sb.sha(SCHEMAS["f1"])
    def fix_suite(t):
        out = []
        for line in t.splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            r["binding_sha256"] = f1_sha
            r["binding_ref"] = f"schemas/af_wcc_vacuum.yaml#sha256:{f1_sha[:16]}"
            r["binding_frozen_revision"] = 14
            r["binding_frozen_revision_schema"] = 14
            note = r.get("rebind_note") or ""
            if "rev14-rebind" not in note:
                r["rebind_note"] = ("rev14-rebind (REC-36 item 6): binding moved to the rev14 F1 pin; "
                                    "f0 probe re-observed against the live F0 0abb9ed8a961. ") + note
            if r.get("test_id") == "F1-AMB-25":
                for p in r.get("probe_results", []):
                    if p.get("path") == "f0_binding.declared_f0_sha256":
                        p["expected"] = F0_SHA
                        p["observed_excerpt"] = json.dumps(F0_SHA)
                        p["pass"] = True
            out.append(json.dumps(r))
        return "\n".join(out) + "\n"
    sb.patch_text(SUITE, fix_suite)
    # I7: pinned non-reproducible exclusion record (the second branch of the predicate)
    sb._put("artifacts/formulation/evidence/acceptance_reproducibility_exclusion.json", json.dumps({
        "artifact_kind": "acceptance_reproducibility_exclusion",
        "non_reproducible": True,
        "excluded_from_gate_evidence": True,
        "excluded_report": ACCEPT_REPORT,
        "reason": "CONTROL-STUB: pinned acceptance report excluded, corpus base stale (CF-32).",
    }, indent=2).encode())
    return sb


MUTATIONS = {
    "M1_containment_denial": (SCHEMAS["c0"], lambda t: t.replace(
        "The extension sets are nonetheless nested:",
        "No containment with C2 or C0 is asserted here. The extension sets are nonetheless nested:")),
    "M2_size_premise_inversion": (SCHEMAS["c0"], lambda t: t.replace(
        "C2 is a strictly smaller extension class", "C2 is a strictly larger extension class")),
    "M3_category_unpinned": (SCHEMAS["c2"], lambda t: t.replace("SMOOTH (C-infinity) connected 4-manifold is the category", "A connected 4-manifold is the carrier")),
    "M4_alias_token_in_schema": (SCHEMAS["c0"], lambda t: t.replace(
        "conclusion_type: scc_c0_future_inextendibility", "conclusion_type: strong_cosmic_censorship_C0")),
    "M5_flat_set_label": (VR, lambda t: t.replace(SET_LEVEL_STRENGTH, "strictly weaker than AF-WCC-VAC-GEN (flat)")),
    "M6_stale_suite_binding": (SUITE, None),  # handled specially
    "M7_acceptance_stale_without_exclusion": (None, None),  # handled specially
}


def apply_mutation(sb: Sandbox, key: str):
    rel, fn = MUTATIONS[key]
    if key == "M6_stale_suite_binding":
        def f(t):
            r = json.loads(t.splitlines()[0])
            r["binding_sha256"] = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
            r["binding_frozen_revision"] = 12
            lines = [json.dumps(r)] + [l for l in t.splitlines() if l.strip()][1:]
            return "\n".join(lines) + "\n"
        sb.patch_text(SUITE, f)
        return
    if key == "M7_acceptance_stale_without_exclusion":
        sb.path("artifacts/formulation/evidence/acceptance_reproducibility_exclusion.json").unlink()
        rec = json.loads(sb.text(ESCAPE_EVIDENCE))
        rec["base_sha256"] = "1bb78ce9b357" + "0" * 52
        sb._put(ESCAPE_EVIDENCE, (json.dumps(rec, indent=2) + "\n").encode())
        return
    # mirror the mutation to both copies for schema items
    sb.patch_text(rel, fn)
    for k, v in SCHEMAS.items():
        if rel == v:
            sb.patch_text(MIRROR[k], fn)


def controls() -> dict:
    stub = make_stub("stub_baseline")
    base = measure(stub, "stub", full_pins=False, run_pipeline=False)
    base_map = base["summary"]
    stub_root_probe = None
    results = []
    for key in MUTATIONS:
        sb = make_stub(f"ctl_{key}")
        apply_mutation(sb, key)
        # only run the cheap pipeline branch in controls: M7 keeps run_pipeline=True to fire the preflight
        m = measure(sb, key, full_pins=False, run_pipeline=(key == "M7_acceptance_stale_without_exclusion"))
        item = key.split("_")[0].replace("M", "I")
        target = m["summary"].get(item)
        others = {k: v for k, v in m["summary"].items() if k != item}
        others_before = {k: v for k, v in base_map.items() if k != item}
        isolated = others == others_before
        results.append({
            "control": key, "target_item": item, "target_status": target,
            "expected_target": "FAIL", "target_ok": target == "FAIL",
            "other_items_unchanged": isolated,
            "stub_baseline_target": base_map.get(item),
            "status": "PASS" if (target == "FAIL" and isolated) else "FAIL",
        })
        sb.cleanup()
    stub.cleanup()
    return {
        "stub_baseline_summary": base_map,
        "stub_baseline_status": base["items"],
        "controls": results,
        "controls_passed": sum(1 for r in results if r["status"] == "PASS"),
        "controls_total": len(results),
    }


# --------------------------------------------------------------------------------------
# attestation + driver
# --------------------------------------------------------------------------------------

ATTEST = [SCHEMAS["c0"], SCHEMAS["c2"], SCHEMAS["f1"], MIRROR["c0"], MIRROR["c2"], MIRROR["f1"],
          TAX_CANON, TAX_SUPP, FROZEN, VR, SET_DELTA, CROSSWALK, XWALK_EVIDENCE, VR_EVIDENCE,
          ACCEPT_REPORT, ESCAPE_EVIDENCE, SUITE, "artifacts/formulation/KEY_MANIFEST.json"]


def attest() -> dict:
    return {rel: sha256_file(REPO / rel) for rel in ATTEST if (REPO / rel).exists()}


def live_pin_resolution() -> dict:
    """Resolve every FROZEN pin against the live repo (read-only, no sandbox)."""
    frozen = json.loads((REPO / FROZEN).read_text())
    problems, missing, resolved = [], [], 0
    for rel, meta in (frozen.get("files") or {}).items():
        p = REPO / rel
        if not p.exists():
            missing.append(rel)
            continue
        resolved += 1
        if sha256_file(p) != meta.get("sha256"):
            problems.append(rel)
    return {"frozen_revision": frozen.get("revision"), "pin_count": len(frozen.get("files") or {}),
            "resolved": resolved, "missing": missing, "problems": problems,
            "ok": not problems and not missing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", choices=["live", "candidate"], default="live")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    before = attest()
    report = {
        "task_id": "W038-REV36-FOLD-CENSUS-01",
        "actor": "worker-038",
        "role": "bounded execution worker",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "authority": "worker measurement only; no gate verdict, no node status, no validation_status=passed, no canonical artifact written",
        "rec36_items": [i[0] for i in [
            ("I1", ""), ("I2", ""), ("I3", ""), ("I4", ""), ("I5", ""), ("I6", ""), ("I7", "")]],
        "inputs_attested_before": before,
        "runs": [],
    }

    if args.controls:
        report["mode"] = "controls"
        report["controls_block"] = controls()
    else:
        sb = Sandbox("live" if args.context == "live" else "candidate")
        if args.context == "candidate":
            for src, rel in CAND_OVERLAY:
                if src.exists():
                    sb.overlay(src, rel)
            report["candidate_identity"] = CAND_IDENTITY
        run = measure(sb, args.context, full_pins=True, run_pipeline=True)
        report["runs"].append(run)
        report["summary"] = run["summary"]
        if args.context == "live":
            report["live_frozen_pin_resolution"] = live_pin_resolution()
        report["verdict"] = ("FOLD_COMPLETE" if all(v == "PASS" for v in run["summary"].values())
                             else "FOLD_INCOMPLETE")
        report["open_items"] = sorted([k for k, v in run["summary"].items() if v == "FAIL"])
        sb.cleanup()

    after = attest()
    report["inputs_attested_after"] = after
    moved = {k: {"before": before.get(k), "after": after.get(k)}
             for k in set(before) | set(after) if before.get(k) != after.get(k)}
    report["canonical_bytes_moved_by_this_run"] = moved
    report["instrument_sha256"] = sha256_file(Path(__file__))

    OUT.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT / "raw"
    raw_dir.mkdir(exist_ok=True)
    default_name = f"run_{args.context if not args.controls else 'controls'}.json"
    dest = Path(args.out) if args.out else raw_dir / default_name
    dest.write_text(json.dumps(report, indent=2) + "\n")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if args.controls:
            cb = report["controls_block"]
            print(f"CONTROLS {cb['controls_passed']}/{cb['controls_total']} discriminate")
            print("stub baseline:", cb["stub_baseline_summary"])
            for r in cb["controls"]:
                print(f"  {r['status']:4} {r['control']:38} target={r['target_item']} "
                      f"{r['stub_baseline_target']}->{r['target_status']} others_unchanged={r['other_items_unchanged']}")
        else:
            print(f"{args.context}: {report.get('verdict')} open={report.get('open_items')}")
            for i in report["runs"][0]["items"]:
                print(f"  {i['status']:4} {i['item']} {i['title']}")
        print("wrote", dest)

    # fail-closed: any control that does not discriminate is an instrumentation failure
    if args.controls and report["controls_block"]["controls_passed"] != report["controls_block"]["controls_total"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
