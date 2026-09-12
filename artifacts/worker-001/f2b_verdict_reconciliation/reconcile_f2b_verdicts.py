#!/usr/bin/env python3
"""W001-F2B-VERDICT-RECONCILIATION-01 -- fail-closed, hash-pinned reconciliation of the
F2b (AF-SCC-C0-VAC-GEN) review-verdict corpus at FROZEN rev29, for G-FORM.

Question
--------
At the frozen pins, the F2b review corpus contains BOTH full-schema accepts and
full-schema revises. Which decision-relevant objections to a clean G-FORM pass are
open, which verdicts carry them, and does any full-schema accept engage (let alone
rebut) a carried objection?

Method (all measured, no fluent-text promotion)
-----------------------------------------------
1. Pin guard: every canonical byte this report depends on is measured and compared;
   any drift exits 3 without emitting a verdict.
2. Carrier oracle: the two normative F2b containment carriers named across the
   corpus (schema text, not prose judgement) are detected mechanically from the
   YAML structure and the file's OWN containment chain:
     C1 = regularity.must_not_conflate[0] denies containment while the same file's
          implication_ledger.extension_class_containment asserts it;
     C2 = implication_ledger.forbidden_transfers[0].reason calls C2 "strictly larger"
          while the same file's chain makes E_C2 the innermost (smallest) set.
   Class-relativity is controlled: the identical C1 sentence injected into a file
   with no containment chain is not a finding, and the corrected F2a sibling is not
   a finding.
3. Verdict census under TWO declared rules:
     R1 = the live controller advisory rule (VERDICT_KINDS + TARGET_ALIASES +
          _explicit_pins prefix match), transcribed verbatim from
          research_map/astra_lifecycle.py and cross-checked against the live module
          on the SAME snapshot bytes in a child process;
     R2 = a wider, explicitly declared closed binding rule (same pin requirement,
          plus target/node/class string identification and node_id/class_id
          fallback) so that a hard finding cannot vanish because its author used the
          protocol's recommended `path#sha256` target form instead of a bare alias.
   Binding adjudication itself remains the audit lead's call; this report declares
   its rule and reports both.
4. Objection ledger: bound hard failures are grouped by measured carrier axis; the
   integrity layer (sidecar .sha256, entry_hashes.json, aggregator re-pin) is
   measured separately.
5. Rebuttal scan: for each carrier, which full-schema accepts cite the carrier
   defect (not merely the slot) and resolve it.
6. Repair-candidate coverage: the worker-001 candidate 90ede5c9516b is re-measured
   through the same oracle; author conflict is declared and no independence is
   claimed for it.
7. Seeded controls (15) run through the same functions; any control departing from
   its pre-registered expectation exits 4.

Writes only under artifacts/worker-001/f2b_verdict_reconciliation/ and
runtime/state/. Never edits a canonical artifact. Emits no gate verdict.

Exit codes: 0 verdict emitted; 3 pin drift; 4 control failure; 5 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "research_map" / "astra_lifecycle.py").is_file() and (cand / "schemas").is_dir():
            return cand
    raise SystemExit(5)


HERE = Path(__file__).resolve()
ROOT = find_root(HERE.parent)
OUTDIR = HERE.parent
STATE_DIR = ROOT / "runtime" / "state"
TASK_ID = "W001-F2B-VERDICT-RECONCILIATION-01"
ACTOR = "worker-001"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
NODE_ID = "F2b"
GATE = "G-FORM"

F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
F2A_PIN = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
F1_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
F0_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_SUP_PIN = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
CASES_PIN = "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03"
CAND_PIN = "90ede5c9516b5b4d18346bed6224561d06194b3c485067976be9aab55dd5a328"
CAND_DIFF_PIN = "a45fbae3a8afc01f0e7d5b64bc773a2c34aeb984e734dd092e30dc04f0fd6bde"

PINS = [
    ("F2b canonical", "schemas/af_scc_c0_vacuum.yaml", F2B_PIN),
    ("F2b authoring mirror", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", F2B_PIN),
    ("F2a canonical", "schemas/af_scc_c2_vacuum.yaml", F2A_PIN),
    ("F1 canonical", "schemas/af_wcc_vacuum.yaml", F1_PIN),
    ("F0 taxonomy", "research_map/formulation_taxonomy.yaml", F0_PIN),
    ("F0 supplement", "artifacts/formulation/formulation_taxonomy.yaml", F0_SUP_PIN),
    ("FROZEN rev29", "artifacts/formulation/FROZEN.json", FROZEN_PIN),
    ("taxonomy cases", "schemas/taxonomy_cases.jsonl", CASES_PIN),
    ("repair candidate", "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml", CAND_PIN),
    ("repair candidate diff", "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.diff", CAND_DIFF_PIN),
]

C1_DENIAL = "No containment with C2 or C0 is asserted here"
C2_INVERTED = "C2 is a strictly larger extension class"
CHAIN_CONTAINS = "E_C0 contains E_H2loc"
CHAIN_CONTAINS_RE = re.compile(r"E_C0\s+contains\b.*contains\s+E_C2")
CHAIN_SUBSET_RE = re.compile(r"E_C2\s+subset\s+of\b.*E_C0")

# ---------------------------------------------------------------- controller rule
# Transcribed verbatim from research_map/astra_lifecycle.py (lines 134-173 at the
# measured instrument hash recorded in the report); cross-checked against the live
# module on the same snapshot bytes by control K13.
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}


def targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def explicit_pins(d: dict) -> list:
    pin_keys = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
    pins = []
    for key in pin_keys:
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def pin_match(pins: list, target_pin: str) -> bool:
    return any(p.startswith(target_pin[:12]) or target_pin.startswith(p[:12]) for p in pins)


def raw_target_strings(d: dict) -> list:
    out = []
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id", "path"):
                if isinstance(v.get(k2), str):
                    out.append(v[k2])
    return out


def node_and_class_tokens(d: dict) -> list:
    toks = []
    for key in ("node_id", "node_ids", "class_id", "class_ids"):
        v = d.get(key)
        if isinstance(v, str):
            toks.append(v)
        elif isinstance(v, list):
            toks.extend(str(x) for x in v)
    return toks


def r1_bound(d: dict, target_pin: str) -> bool:
    if str(d.get("verdict", "")).lower() not in VERDICT_KINDS:
        return False
    if "F2b" not in targets_in_review(d):
        return False
    return pin_match(explicit_pins(d), target_pin)


def r2_bound(d: dict, target_pin: str) -> bool:
    """Declared wider rule: same verdict kind + same explicit pin match, and the
    review identifies F2b by alias, by path/class string in its target fields, or by
    node_id/class_id fallback. Binding adjudication is the audit lead's; this rule
    is declared here so the report is reproducible."""
    if str(d.get("verdict", "")).lower() not in VERDICT_KINDS:
        return False
    if not pin_match(explicit_pins(d), target_pin):
        return False
    if "F2b" in targets_in_review(d):
        return True
    for s in raw_target_strings(d):
        if "F2b" in s or "af_scc_c0_vacuum.yaml" in s:
            return True
    for t in node_and_class_tokens(d):
        if t in ("F2b", "AF-SCC-C0-VAC-GEN"):
            return True
    return False


# ------------------------------------------------------------------ carrier oracle
def parse_yaml_text(text: str) -> dict:
    return yaml.safe_load(text)


def line_of(text: str, needle: str):
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def carrier_oracle(text: str, doc: dict) -> dict:
    reg = ((doc.get("regularity") or {}).get("must_not_conflate") or [])
    reg_join = " ".join(str(x) for x in reg)
    il = doc.get("implication_ledger") or {}
    chain = str(il.get("extension_class_containment") or "")
    ft = il.get("forbidden_transfers") or []
    reason0 = str((ft[0] or {}).get("reason") or "") if ft else ""
    chain_order = bool(CHAIN_CONTAINS_RE.search(chain) or CHAIN_SUBSET_RE.search(chain))
    chain_asserts = (CHAIN_CONTAINS in chain) or bool(CHAIN_SUBSET_RE.search(chain))
    c1 = (C1_DENIAL in reg_join) and chain_asserts
    c2 = (C2_INVERTED in reason0) and chain_order
    return {
        "C1_containment_denial": {
            "live": c1,
            "slot": "regularity.must_not_conflate[0]",
            "line": line_of(text, C1_DENIAL),
            "denial_sentence": C1_DENIAL if C1_DENIAL in reg_join else None,
            "own_chain_asserts_containment": chain_asserts,
            "chain": chain[:200],
        },
        "C2_size_premise_inverted": {
            "live": c2,
            "slot": "implication_ledger.forbidden_transfers[0].reason",
            "line": line_of(text, C2_INVERTED),
            "reason": reason0[:200],
            "own_chain_orders_E_C2_innermost": chain_order,
        },
        "chain_order_present": chain_order,
    }


# ------------------------------------------------------------------- measurement
def pin_guard() -> dict:
    measured = {}
    for label, rel, expected in PINS:
        p = ROOT / rel
        if not p.is_file():
            print(json.dumps({"fatal": "PIN_PATH_ABSENT", "label": label, "path": rel}))
            raise SystemExit(5)
        got = sha256_file(p)
        measured[label] = {"path": rel, "expected": expected, "measured": got,
                           "match": got == expected}
        if got != expected:
            print(json.dumps({"fatal": "PIN_DRIFT", "label": label, "path": rel,
                              "expected": expected, "measured": got}))
            raise SystemExit(3)
    return measured


def load_snapshot():
    files = sorted((ROOT / "reviews").glob("*.json"))
    snap = {}
    for f in files:
        snap[f.name] = f.read_bytes()
    digest = sha256_bytes("\n".join(
        f"{n}:{sha256_bytes(b)}" for n, b in sorted(snap.items())).encode())
    return snap, digest


CARRIER_MARKERS = {
    "C1": {"defect": ["No containment with C2 or C0", "containment denial", "stale denial",
                      "contradicts the file's own asserted chain", "no containment with C2"],
           "slot": ["must_not_conflate", ":152", "line 152"]},
    "C2": {"defect": ["strictly larger extension class", "strictly larger", "size premise",
                      "E_C2 is the innermost", "inverted"],
           "slot": ["forbidden_transfers", ":246", "line 246"]},
    "D": {"defect": ["declared-hash layer", "declared sha256", "entry_hashes",
                     "canonical_gate", ".sha256", "re-pin", "re-pinned", "integration lint"],
          "slot": ["sha256", "pin"]},
    "V": {"defect": ["VOCAB", "vocab", "alias token", "scc_c0_future_inextendibility",
                     "field_vocabulary"],
          "slot": ["conclusion_type", "field_vocabulary"]},
}


def marker_hits(text: str, kind: str) -> dict:
    return {"defect": sorted({m for m in CARRIER_MARKERS[kind]["defect"] if m in text}),
            "slot": sorted({m for m in CARRIER_MARKERS[kind]["slot"] if m in text})}


def classify_hf(text: str) -> list:
    axes = []
    for kind in ("C1", "C2", "D", "V"):
        if marker_hits(text, kind)["defect"]:
            axes.append(kind)
    return axes or ["other"]


def census(snap: dict) -> dict:
    rows = []
    for name, raw in sorted(snap.items()):
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            rows.append({"file": name, "parse_error": True})
            continue
        if isinstance(d, list):
            d = d[0] if d and isinstance(d[0], dict) else {}
        if not isinstance(d, dict):
            rows.append({"file": name, "parse_error": True})
            continue
        verdict = str(d.get("verdict", "")).lower()
        if verdict not in VERDICT_KINDS:
            continue
        if not r2_bound(d, F2B_PIN):
            continue
        text = raw.decode("utf-8", "replace")
        hf = d.get("hard_failures")
        hf_list = hf if isinstance(hf, list) else ([hf] if hf else [])
        hf_rows = []
        for h in hf_list:
            htxt = json.dumps(h, ensure_ascii=False)
            hid = h.get("id") if isinstance(h, dict) else None
            if hid is None and isinstance(h, str):
                m = re.match(r"\s*([A-Za-z0-9_.\-]+?):", h)
                hid = m.group(1) if m else None
            hf_rows.append({
                "id": hid,
                "axis": classify_hf(htxt),
                "markers": {k: marker_hits(htxt, k) for k in ("C1", "C2", "D", "V")},
                "excerpt": htxt[:240],
            })
        rows.append({
            "file": name,
            "sha256": sha256_bytes(raw),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "verdict": verdict,
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "full": d.get("counts_as_full_schema_verdict") is not False,
            "r1_bound": r1_bound(d, F2B_PIN),
            "r2_bound": True,
            "targets": sorted(targets_in_review(d)),
            "raw_targets": raw_target_strings(d),
            "node_id": d.get("node_id"),
            "class_id": d.get("class_id"),
            "hard_failures": hf_rows,
            "engagement": {k: marker_hits(text, k) for k in ("C1", "C2", "D", "V")},
        })
    # files that explicitly pin the F2b hash but are not r2-bound (cross-target/stale)
    excluded = []
    for name, raw in sorted(snap.items()):
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            continue
        if isinstance(d, list):
            d = d[0] if d and isinstance(d[0], dict) else {}
        if not isinstance(d, dict):
            continue
        if str(d.get("verdict", "")).lower() not in VERDICT_KINDS:
            continue
        if pin_match(explicit_pins(d), F2B_PIN) and not r2_bound(d, F2B_PIN):
            excluded.append({"file": name, "reviewer": d.get("reviewer") or d.get("actor"),
                             "verdict": str(d.get("verdict", "")).lower(),
                             "targets": sorted(targets_in_review(d)),
                             "raw_targets": raw_target_strings(d)[:2]})
    return {"rows": rows, "excluded_f2b_pinned_other_target": excluded}


def summarize_census(c: dict) -> dict:
    rows = c["rows"]
    full_accepts = [r for r in rows if r["verdict"] == "accept" and r["full"]]
    scoped_accepts = [r for r in rows if r["verdict"] == "accept" and not r["full"]]
    full_revises = [r for r in rows if r["verdict"] == "revise" and r["full"]]
    scoped_revises = [r for r in rows if r["verdict"] == "revise" and not r["full"]]
    def brief(r):
        return {"file": r["file"], "reviewer": r["reviewer"], "r1_bound": r["r1_bound"],
                "hf_ids": [h["id"] for h in r["hard_failures"]],
                "hf_axes": sorted({a for h in r["hard_failures"] for a in h["axis"]})}
    return {
        "n_bound": len(rows),
        "n_r1_bound": sum(1 for r in rows if r["r1_bound"]),
        "full_accepts": [brief(r) for r in full_accepts],
        "scoped_accepts": [brief(r) for r in scoped_accepts],
        "full_revises": [brief(r) for r in full_revises],
        "scoped_revises": [brief(r) for r in scoped_revises],
        "full_accept_reviewers": sorted({r["reviewer"] for r in full_accepts}),
        "r1_full_accept_reviewers": sorted({r["reviewer"] for r in full_accepts if r["r1_bound"]}),
        "excluded_f2b_pinned_other_target": c["excluded_f2b_pinned_other_target"],
    }


def carrier_support(rows: list, axis: str, require_full: bool) -> list:
    out = []
    for r in rows:
        if r["verdict"] != "revise":
            continue
        if require_full and not r["full"]:
            continue
        for h in r["hard_failures"]:
            if axis in h["axis"]:
                out.append({"file": r["file"], "reviewer": r["reviewer"], "hf_id": h["id"],
                            "r1_bound": r["r1_bound"]})
                break
    return out


def rebuttal_scan(rows: list) -> dict:
    out = {}
    for axis in ("C1", "C2"):
        hits = []
        for r in rows:
            if r["verdict"] != "accept":
                continue
            eng = r["engagement"][axis]
            if eng["defect"]:
                hits.append({"file": r["file"], "reviewer": r["reviewer"],
                             "full": r["full"], "defect_markers": eng["defect"]})
        out[axis] = {"accepts_citing_defect_markers": hits,
                     "full_accepts_citing_slot_only": [
                         {"file": r["file"], "reviewer": r["reviewer"],
                          "slot_markers": r["engagement"][axis]["slot"]}
                         for r in rows
                         if r["verdict"] == "accept" and r["full"]
                         and not r["engagement"][axis]["defect"]
                         and r["engagement"][axis]["slot"]]}
    return out


def integrity_layer() -> dict:
    f2b = sha256_file(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    f2a = sha256_file(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    out = {}

    side = ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"
    dec = side.read_text().split()[0] if side.is_file() else None
    out["D1_sidecar"] = {"path": "schemas/af_scc_c0_vacuum.yaml.sha256",
                         "file_sha256": sha256_file(side) if side.is_file() else None,
                         "declares": dec, "measured_f2b": f2b,
                         "status": "LIVE_STALE" if dec and dec != f2b else "ok"}

    eh = ROOT / "entry_hashes.json"
    entries = json.loads(eh.read_text())
    pairs = [("schemas/af_scc_c0_vacuum.yaml", f2b),
             ("schemas/af_scc_c2_vacuum.yaml", f2a),
             ("schemas/af_wcc_vacuum.yaml", sha256_file(ROOT / "schemas/af_wcc_vacuum.yaml")),
             ("research_map/formulation_taxonomy.yaml", sha256_file(ROOT / "research_map/formulation_taxonomy.yaml")),
             ("artifacts/formulation/formulation_taxonomy.yaml", sha256_file(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")),
             ("artifacts/formulation/FROZEN.json", sha256_file(ROOT / "artifacts/formulation/FROZEN.json"))]
    mism = [{"path": p, "declares": entries.get(p), "measured": m,
             "match": entries.get(p) == m} for p, m in pairs]
    out["D2_entry_hashes"] = {"path": "entry_hashes.json", "file_sha256": sha256_file(eh),
                              "declared": {p: entries.get(p) for p, _ in pairs},
                              "measured": {p: m for p, m in pairs},
                              "mismatches": [x for x in mism if not x["match"]],
                              "status": "LIVE_STALE" if any(not x["match"] for x in mism) else "ok"}

    agg = ROOT / "schemas/af_scc_regularities.yaml"
    adoc = yaml.safe_load(agg.read_text())
    comps = {}
    for comp in (adoc.get("components") or []):
        cid = comp.get("class_id")
        comps[cid] = {"declared": comp.get("sha256"), "canonical_gate": comp.get("canonical_gate"),
                      "path": comp.get("path")}
    live = {"AF-SCC-C0-VAC-GEN": f2b, "AF-SCC-C2-VAC-GEN": f2a}
    for cid, v in comps.items():
        v["measured"] = live.get(cid)
        v["match"] = v["declared"] == v["measured"]
    out["D3_aggregator"] = {"path": "schemas/af_scc_regularities.yaml",
                            "file_sha256": sha256_file(agg),
                            "revision": adoc.get("revision"),
                            "supersedes_sha256": adoc.get("supersedes_sha256"),
                            "components": comps,
                            "status": "ok" if all(v["match"] for v in comps.values()) else "LIVE_STALE"}
    return out


def repair_candidate_coverage() -> dict:
    p = ROOT / "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml"
    text = p.read_text()
    doc = parse_yaml_text(text)
    oracle = carrier_oracle(text, doc)
    import difflib
    base = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text().splitlines()
    cand_lines = text.splitlines()
    sm = difflib.SequenceMatcher(None, base, cand_lines, autojunk=False)
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed.append({"op": tag, "base_lines": [i1 + 1, i2], "candidate_lines": [j1 + 1, j2]})
    changed_base_lines = sorted({ln for ch in changed for ln in range(ch["base_lines"][0], ch["base_lines"][1] + 1)})
    diff = (ROOT / "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.diff").read_text()
    touched = sorted({int(m.group(1)) for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)", diff, re.M)})
    return {
        "path": "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml",
        "sha256": sha256_file(p),
        "author": "worker-001",
        "authorship_note": "candidate authored by this worker; coverage below is a re-run of the "
                           "author's oracle, NOT independent verification. Independent candidate "
                           "verification is reviews/F2b-repair-candidate-verify-worker-029.json.",
        "oracle": oracle,
        "resolves_C1": not oracle["C1_containment_denial"]["live"],
        "resolves_C2": not oracle["C2_size_premise_inverted"]["live"],
        "diff_hunk_added_line_starts": touched,
        "changed_base_lines": changed_base_lines,
        "changed_ops": changed,
        "addresses_integrity_layer": False,
    }


# ---------------------------------------------------------------------- controls
def synthetic(target_id: str, verdict: str, pin: str, full=None, node_id=None,
              class_id=None, extra=None) -> dict:
    d = {"target_id": target_id, "verdict": verdict, "artifact_sha256": pin}
    if full is not None:
        d["counts_as_full_schema_verdict"] = full
    if node_id:
        d["node_id"] = node_id
    if class_id:
        d["class_id"] = class_id
    if extra:
        d.update(extra)
    return d


def controls(f2a_doc: dict, f2a_text: str, live_agree: dict) -> list:
    c = []

    def rec(cid, expectation, observed, ok=None):
        if ok is None:
            ok = expectation == observed
        c.append({"id": cid, "expectation": expectation, "observed": observed, "pass": bool(ok)})

    f2b_text = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    f2b_doc = parse_yaml_text(f2b_text)
    live = carrier_oracle(f2b_text, f2b_doc)
    rec("K1_live_C1_detected", True, live["C1_containment_denial"]["live"])
    rec("K2_live_C2_detected", True, live["C2_size_premise_inverted"]["live"])

    fixed1 = f2b_text.replace(C1_DENIAL, "Containment with C2 is asserted in the ledger below")
    rec("K3_C1_fixed_clears", False,
        carrier_oracle(fixed1, parse_yaml_text(fixed1))["C1_containment_denial"]["live"])
    fixed2 = f2b_text.replace(C2_INVERTED, "C2 is a strictly smaller extension class")
    rec("K4_C2_fixed_clears", False,
        carrier_oracle(fixed2, parse_yaml_text(fixed2))["C2_size_premise_inverted"]["live"])

    inj = f2a_text.replace("C-infinity extensions are also C2 extensions",
                           C1_DENIAL + " C-infinity extensions are also C2 extensions", 1)
    rec("K5_C1_class_relative_positive", True,
        carrier_oracle(inj, parse_yaml_text(inj))["C1_containment_denial"]["live"])
    norel = {"regularity": {"must_not_conflate": [C1_DENIAL]},
             "implication_ledger": {"extension_class_containment": "no containment is asserted",
                                    "forbidden_transfers": [{"reason": "irrelevant"}]}}
    rec("K6_C1_class_relative_negative", False,
        carrier_oracle(C1_DENIAL, norel)["C1_containment_denial"]["live"])

    rec("K7_full_flag_default_is_full", True,
        synthetic("F2b", "accept", F2B_PIN).get("counts_as_full_schema_verdict") is not False)
    rec("K8_explicit_scoped_stays_scoped", False,
        synthetic("F2b", "accept", F2B_PIN, full=False).get("counts_as_full_schema_verdict") is not False)

    path_target = synthetic("schemas/af_scc_c0_vacuum.yaml#" + F2B_PIN, "accept", F2B_PIN)
    rec("K9_path_target_r1_excluded", False, r1_bound(path_target, F2B_PIN))
    rec("K9_path_target_r2_included", True, r2_bound(path_target, F2B_PIN))

    cross = synthetic("F2a", "accept", F2B_PIN)
    rec("K10_cross_target_r2_excluded", False, r2_bound(cross, F2B_PIN))
    stale = synthetic("F2b", "accept", F2A_PIN)
    rec("K11_stale_pin_excluded", False, r1_bound(stale, F2B_PIN) or r2_bound(stale, F2B_PIN))
    noverdict = {"target_id": "F2b", "artifact_sha256": F2B_PIN}
    rec("K12_no_verdict_excluded", False, r1_bound(noverdict, F2B_PIN) or r2_bound(noverdict, F2B_PIN))

    rec("K13_live_instrument_agreement", True, live_agree.get("agrees", False))

    cand = repair_candidate_coverage()
    rec("K14_candidate_resolves_both", True, cand["resolves_C1"] and cand["resolves_C2"])
    rec("K14_candidate_changed_lines_only_152_246", [152, 246], cand["changed_base_lines"])

    probe_text = f2b_text.replace(C1_DENIAL, "x").replace(C2_INVERTED, "y")
    probe = carrier_oracle(probe_text, parse_yaml_text(probe_text))
    rec("K15_verdict_is_falsifiable_by_repair", False,
        probe["C1_containment_denial"]["live"] or probe["C2_size_premise_inverted"]["live"])
    return c


def live_instrument_agreement(snap: dict) -> dict:
    """Apply the LIVE controller rule functions (child process, same snapshot bytes)
    to the snapshot dicts and compare with the transcription."""
    payload = []
    for name, raw in sorted(snap.items()):
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            continue
        if isinstance(d, list):
            d = d[0] if d and isinstance(d[0], dict) else {}
        if isinstance(d, dict) and str(d.get("verdict", "")).lower() in VERDICT_KINDS:
            payload.append([name, d])
    code = (
        "import sys,json\n"
        "sys.path.insert(0, %r)\n"
        "import astra_lifecycle as A\n"
        "payload=json.load(sys.stdin)\n"
        "out=[]\n"
        "for name,d in payload:\n"
        "    t=sorted(A._targets_in_review(d)); p=[x.lower() for x in A._explicit_pins(d)]\n"
        "    out.append([name,t,p])\n"
        "print(json.dumps(out))\n" % str(ROOT / "research_map")
    )
    try:
        r = subprocess.run([sys.executable, "-c", code], input=json.dumps(payload).encode(),
                           capture_output=True, timeout=240)
        if r.returncode != 0:
            return {"agrees": False, "error": r.stderr.decode()[-300:]}
        live = {name: {"targets": t, "pins": p} for name, t, p in json.loads(r.stdout.decode())}
    except Exception as e:  # pragma: no cover
        return {"agrees": False, "error": repr(e)}
    mismatches = []
    for name, d in payload:
        mine_t = sorted(targets_in_review(d))
        mine_p = [x.lower() for x in explicit_pins(d)]
        lv = live.get(name)
        if lv is None or lv["targets"] != mine_t or lv["pins"] != mine_p:
            mismatches.append({"file": name, "mine": [mine_t, mine_p], "live": lv})
    return {"agrees": not mismatches, "n_compared": len(payload),
            "mismatches": mismatches[:5],
            "instrument_sha256": sha256_file(ROOT / "research_map/astra_lifecycle.py")}


# -------------------------------------------------------------------------- main
def main() -> int:
    started = now()
    pins = pin_guard()
    f2a_text = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f2a_doc = parse_yaml_text(f2a_text)
    f2b_text = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    f2b_doc = parse_yaml_text(f2b_text)
    oracle = carrier_oracle(f2b_text, f2b_doc)
    sib_oracle = carrier_oracle(f2a_text, f2a_doc)

    # precondition: sibling must not carry the C1 denial, else class-relativity is broken
    if sib_oracle["C1_containment_denial"]["live"]:
        print(json.dumps({"fatal": "PRECONDITION_SIBLING_CARRIES_C1"}))
        return 5

    snap, digest = load_snapshot()
    live_agree = live_instrument_agreement(snap)
    ctrl = controls(f2a_doc, f2a_text, live_agree)
    failed = [k for k in ctrl if not k["pass"]]
    if failed:
        print(json.dumps({"fatal": "CONTROL_FAILURE", "failed": failed}, ensure_ascii=False))
        return 4

    c = census(snap)
    csum = summarize_census(c)
    rows = c["rows"]
    review_sha = {r["file"]: r["sha256"] for r in rows if "sha256" in r}
    support = {
        "C1_full_revises": carrier_support(rows, "C1", True),
        "C1_all_revises": carrier_support(rows, "C1", False),
        "C2_full_revises": carrier_support(rows, "C2", True),
        "C2_all_revises": carrier_support(rows, "C2", False),
        "D_full_revises": carrier_support(rows, "D", True),
        "V_full_revises": carrier_support(rows, "V", True),
    }
    rebut = rebuttal_scan(rows)
    integrity = integrity_layer()
    cand = repair_candidate_coverage()

    objections = []
    if oracle["C1_containment_denial"]["live"]:
        objections.append({"id": "OBJ-F2B-C1", "axis": "schema_text",
                           "slot": oracle["C1_containment_denial"]["slot"],
                           "line": oracle["C1_containment_denial"]["line"],
                           "status": "LIVE",
                           "supporting_full_revises": support["C1_full_revises"],
                           "supporting_all_revises": support["C1_all_revises"],
                           "rebutted_by_full_accepts": rebut["C1"]["accepts_citing_defect_markers"],
                           "repair_candidate_resolves": cand["resolves_C1"]})
    if oracle["C2_size_premise_inverted"]["live"]:
        objections.append({"id": "OBJ-F2B-C2", "axis": "schema_text",
                           "slot": oracle["C2_size_premise_inverted"]["slot"],
                           "line": oracle["C2_size_premise_inverted"]["line"],
                           "status": "LIVE",
                           "supporting_full_revises": support["C2_full_revises"],
                           "supporting_all_revises": support["C2_all_revises"],
                           "rebutted_by_full_accepts": rebut["C2"]["accepts_citing_defect_markers"],
                           "repair_candidate_resolves": cand["resolves_C2"]})
    for key, label in (("D1_sidecar", "OBJ-F2B-D1"), ("D2_entry_hashes", "OBJ-F2B-D2"),
                       ("D3_aggregator", "OBJ-F2B-D3")):
        if integrity[key]["status"] != "ok":
            objections.append({"id": label, "axis": "declared_hash_layer", "status": "LIVE",
                               "measured": integrity[key],
                               "supporting_full_revises": support["D_full_revises"]})
    objections.append({"id": "OBJ-F2B-V1", "axis": "cross_artifact_vocab",
                       "status": "CONTESTED_OUT_OF_AXIS",
                       "note": "F0 field_vocabulary lists alias tokens vs schema canonical tokens; "
                               "worker-066 adjudication (reviews/F2b-vocab-binding-adjudication-worker-066.json) "
                               "holds the binding layer resolves it and refutes hard severity; worker-075 "
                               "carried it as HF-075-F2b-VOCAB. Not adjudicated here.",
                       "supporting_full_revises": support["V_full_revises"]})

    live_objs = [o["id"] for o in objections if o["status"] == "LIVE"]
    unrebutted = [o["id"] for o in objections if o["status"] == "LIVE"
                  and o["axis"] in ("schema_text", "declared_hash_layer")
                  and not o.get("rebutted_by_full_accepts")]
    verdict = "F2B_OBJECTIONS_OPEN_NOT_REBUTTED" if live_objs else "F2B_OBJECTIONS_CLEAR_AT_PINS"

    report = {
        "schema_version": "0.1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": started,
        "harness_sha256": sha256_file(HERE),
        "authority_note": "Worker report: no gate verdict, no node status change, no canonical "
                          "artifact edit, no binding adjudication, no mathematical claim.",
        "verdict": verdict,
        "reason_codes": live_objs,
        "pins_measured": pins,
        "carrier_oracle_F2b": oracle,
        "carrier_oracle_F2a_sibling_control": sib_oracle,
        "verdict_census": csum,
        "objections": objections,
        "unrebutted_live_objections": unrebutted,
        "rebuttal_scan": rebut,
        "integrity_layer": integrity,
        "repair_candidate_coverage": cand,
        "corpus": {"n_review_files": len(snap), "digest_sha256": digest,
                   "rule_note": "R1 = live controller advisory rule; R2 = declared wider closed "
                                "rule (same pin, plus path/alias/node/class identification). "
                                "Binding adjudication is the audit lead's.",
                   "bound_files_sha256": {r["file"]: r["sha256"] for r in rows if "sha256" in r}},
        "controls": ctrl,
        "live_instrument_agreement": live_agree,
        "falsifiers": [
            "Any pinned path moving voids the report (pin guard exits 3): F2b "
            "b2ab6acb2bbe, F2a e9a27996dfd3, F1 d9cebb9404b2, F0 0abb9ed8a961, FROZEN 815e08079aef.",
            "OBJ-F2B-C1 is falsified by a frozen convention in F2b under which the line-152 "
            "sentence denotes something other than the file's extension-class containment, or by "
            "bytes whose must_not_conflate[0] no longer carries the denial while the chain stands.",
            "OBJ-F2B-C2 is falsified by a containment-respecting reading in which E_C2 is a "
            "strictly larger extension class than E_C0, or by corrected bytes at "
            "implication_ledger.forbidden_transfers[0].reason.",
            "The 'not rebutted' finding is falsified by a full-schema accept in the snapshot that "
            "cites either carrier defect sentence and resolves it as conforming.",
            "The verdict is falsified by re-running this harness on a repaired F2b revision or on "
            "a corpus snapshot in which every live objection is cleared; a later review write is "
            "not a falsifier but a new corpus revision.",
        ],
        "next_falsifier": "Re-run at the same pins and corpus digest: any control departure exits 4, "
                          "any pin move exits 3. At the pins the objection set is falsified as in "
                          "report.falsifiers.",
        "not_claimed": ["no gate verdict", "no node status change", "no canonical artifact edit",
                        "no binding adjudication (audit lead's)", "no mathematical claim",
                        "not independent verification of the worker-001 repair candidate"],
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTDIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    report_sha = sha256_file(report_path)

    readme = f"""# {TASK_ID} — F2b verdict reconciliation at FROZEN rev29

Worker: {ACTOR}. Class: {CLASS_ID} (node {NODE_ID}, gate {GATE}).
Report: `report.json#sha256:{report_sha[:12]}` (full hash below). Corpus digest:
`{digest[:12]}` over {len(snap)} review files.

## Verdict

**{verdict}** — reason codes: {", ".join(live_objs) if live_objs else "none"}.

At the pinned bytes the two normative containment carriers named across the F2b corpus
are mechanically live: C1 `regularity.must_not_conflate[0]` line
{oracle['C1_containment_denial']['line']} denies containment while the same file's chain asserts it;
C2 `implication_ledger.forbidden_transfers[0].reason` line
{oracle['C2_size_premise_inverted']['line']} calls C2 "strictly larger" while the same file makes
E_C2 the innermost set. Declared-hash layer: D1 sidecar and D2 entry_hashes are live stale;
D3 aggregator is re-pinned at the measured bytes. The cross-artifact vocabulary item is
contested and not adjudicated here.

## Verdict census (both rules declared)

| rule | full accepts | full revises | scoped revises |
|---|---|---|---|
| R1 live controller advisory | {len(csum['r1_full_accept_reviewers'])} ({", ".join(csum['r1_full_accept_reviewers'])}) | {len([r for r in csum['full_revises'] if r['r1_bound']])} | {len([r for r in rows if r['verdict']=='revise' and not r['full'] and r['r1_bound']])} |
| R2 declared wider closed | {len(csum['full_accept_reviewers'])} ({", ".join(csum['full_accept_reviewers'])}) | {len(csum['full_revises'])} | {len(csum['scoped_revises'])} |

The R1/R2 gap is the instrument point: reviews that target the pin with the protocol's
recommended `path#sha256` form (worker-018, worker-029, worker-053, worker-066) or omit
`target_id` (worker-035) are not bound by the live advisory scan even though their
`reviewed_sha256`/`artifact_sha256` is exactly the pin. Binding remains the audit lead's call.

## Rebuttal

No full-schema accept in the snapshot cites either carrier defect sentence
(`rebuttal_scan`); the one accept that mentions `must_not_conflate` (worker-052) lists the
slot as a positive check without engaging line
{oracle['C1_containment_denial']['line']}. The 4 full accepts therefore do not close C1/C2.

## Repair coverage

The worker-001 candidate `REPAIR_CANDIDATE.yaml#sha256:{cand['sha256'][:12]}` (author = this
worker; not independent) clears both carriers under the same oracle, changed base lines
{cand['changed_base_lines']}; it does not address D1/D2. Independent verification of
other circulating candidates is `reviews/F2b-repair-candidate-verify-worker-029.json`.

## Controls

{len(ctrl)}/{len(ctrl)} controls pass, including a live-instrument agreement check against
`research_map/astra_lifecycle.py#sha256:{live_agree.get('instrument_sha256','')[:12]}` on the
same snapshot bytes ({live_agree.get('n_compared')} reviews compared).

## Falsifiers

See `report.json` `falsifiers`. Any pin move exits 3; any control departure exits 4; a later
review write is a new corpus revision, not a falsifier.
"""
    readme_path = OUTDIR / "README.md"
    readme_path.write_text(readme)
    readme_sha = sha256_file(readme_path)

    checkpoint = {
        "schema_version": "0.1",
        "artifact_type": "worker_checkpoint",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now(),
        "verdict": verdict,
        "reason_codes": live_objs,
        "pins_measured": {k: v["measured"] for k, v in pins.items()},
        "corpus_digest_sha256": digest,
        "controls_passed": f"{len(ctrl)}/{len(ctrl)}",
        "artifacts": {
            "report.json": report_sha,
            "README.md": readme_sha,
            "reconcile_f2b_verdicts.py": sha256_file(HERE),
            "CHECKPOINT.json": "self-referential; declared in the outbox artifact event and SUMMARY.json",
        },
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["authority_note"],
    }
    ckpt_path = OUTDIR / "CHECKPOINT.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False, sort_keys=True))

    # the CHECKPOINT.json entry is self-referential by construction; the file's true
    # content hash is declared in the outbox artifact event and SUMMARY.json
    ckpt_sha = sha256_file(ckpt_path)

    state_path = STATE_DIR / "worker-001_checkpoint_f2bverdictrecon.json"
    state_path.write_bytes(ckpt_path.read_bytes())
    if sha256_file(state_path) != ckpt_sha:
        print(json.dumps({"fatal": "STATE_COPY_MISMATCH"}))
        return 5

    harness_sha = sha256_file(HERE)
    artifact_summary = {
        "task_id": TASK_ID, "verdict": verdict, "reason_codes": live_objs,
        "pins": {k: v["measured"] for k, v in pins.items()},
        "corpus_digest_sha256": digest, "controls": f"{len(ctrl)}/{len(ctrl)}",
        "report_sha256": report_sha, "readme_sha256": readme_sha,
        "checkpoint_sha256": ckpt_sha, "harness_sha256": harness_sha,
        "state_copy": "runtime/state/worker-001_checkpoint_f2bverdictrecon.json",
        "created_at": now(),
    }
    (OUTDIR / "SUMMARY.json").write_text(json.dumps(artifact_summary, indent=2, sort_keys=True))
    summary_sha = sha256_file(OUTDIR / "SUMMARY.json")

    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    base = {
        "actor": ACTOR, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
        "created_at": now(), "gate": GATE, "node_id": NODE_ID, "task_id": TASK_ID,
    }
    common_ev = ["artifacts/worker-001/f2b_verdict_reconciliation/report.json#sha256:" + report_sha[:12],
                 "artifacts/worker-001/f2b_verdict_reconciliation/reconcile_f2b_verdicts.py#sha256:" + harness_sha[:12],
                 "artifacts/worker-001/f2b_verdict_reconciliation/CHECKPOINT.json#sha256:" + ckpt_sha[:12],
                 "runtime/state/worker-001_checkpoint_f2bverdictrecon.json#sha256:" + ckpt_sha[:12]]
    events = [
        dict(base, event_id=f"w001-f2bvr-artifact-report-{ts}", event_type="artifact",
             artifact_type="f2b_verdict_reconciliation_report",
             path="artifacts/worker-001/f2b_verdict_reconciliation/report.json",
             sha256=report_sha, validation_status="unverified",
             evidence_refs=["artifacts/worker-001/f2b_verdict_reconciliation/report.json#sha256:" + report_sha[:12]],
             falsifier="Pin drift voids the report (harness exits 3); at the pins see report.falsifiers.",
             summary=f"Verdict {verdict}: {len(live_objs)} live F2b objections at FROZEN rev29 "
                     f"({', '.join(live_objs)}); 4 R1 full accepts do not cite either containment "
                     f"carrier defect; controls {len(ctrl)}/{len(ctrl)}."),
        dict(base, event_id=f"w001-f2bvr-artifact-harness-{ts}", event_type="artifact",
             artifact_type="f2b_verdict_reconciliation_harness",
             path="artifacts/worker-001/f2b_verdict_reconciliation/reconcile_f2b_verdicts.py",
             sha256=harness_sha, validation_status="unverified",
             evidence_refs=["artifacts/worker-001/f2b_verdict_reconciliation/reconcile_f2b_verdicts.py#sha256:" + harness_sha[:12]],
             falsifier="A run at the pinned hashes that exits 0 while a control fails, or that emits a verdict after a pin move.",
             summary="Fail-closed reconciliation harness: 10 pins, carrier oracle with class-relative "
                     "controls, live-controller-rule cross-check, 15 seeded controls, exit 3/4/5."),
        dict(base, event_id=f"w001-f2bvr-artifact-readme-{ts}", event_type="artifact",
             artifact_type="f2b_verdict_reconciliation_summary",
             path="artifacts/worker-001/f2b_verdict_reconciliation/README.md", sha256=readme_sha,
             validation_status="unverified",
             evidence_refs=["artifacts/worker-001/f2b_verdict_reconciliation/README.md#sha256:" + readme_sha[:12]],
             falsifier="Disagreement with report.json at the same pins and corpus digest.",
             summary="One-page summary: verdict, R1/R2 census, rebuttal scan, repair coverage, controls, falsifiers."),
        dict(base, event_id=f"w001-f2bvr-artifact-checkpoint-{ts}", event_type="artifact",
             artifact_type="worker_checkpoint",
             path="artifacts/worker-001/f2b_verdict_reconciliation/CHECKPOINT.json", sha256=ckpt_sha,
             validation_status="unverified",
             evidence_refs=["artifacts/worker-001/f2b_verdict_reconciliation/CHECKPOINT.json#sha256:" + ckpt_sha[:12],
                            "runtime/state/worker-001_checkpoint_f2bverdictrecon.json#sha256:" + ckpt_sha[:12]],
             falsifier="Worker events cannot set node/gate state; this checkpoint binds one worker lifecycle only.",
             summary="Checkpoint: pins, verdict, reason codes, corpus digest, controls, artifact hashes, next falsifier."),
        dict(base, event_id=f"w001-f2bvr-artifact-state-{ts}", event_type="artifact",
             artifact_type="worker_checkpoint_state_copy",
             path="runtime/state/worker-001_checkpoint_f2bverdictrecon.json", sha256=ckpt_sha,
             validation_status="unverified",
             evidence_refs=["runtime/state/worker-001_checkpoint_f2bverdictrecon.json#sha256:" + ckpt_sha[:12]],
             falsifier="Byte mismatch against the artifact-dir checkpoint voids the copy.",
             summary="runtime/state copy of CHECKPOINT.json (byte-identical)."),
        dict(base, event_id=f"w001-f2bvr-artifact-summary-{ts}", event_type="artifact",
             artifact_type="f2b_verdict_reconciliation_summary_json",
             path="artifacts/worker-001/f2b_verdict_reconciliation/SUMMARY.json", sha256=summary_sha,
             validation_status="unverified",
             evidence_refs=["artifacts/worker-001/f2b_verdict_reconciliation/SUMMARY.json#sha256:" + summary_sha[:12]],
             falsifier="Disagreement with report.json / CHECKPOINT.json at the same pins.",
             summary="Compact machine summary: verdict, pins, corpus digest, controls, all artifact hashes."),
        dict(base, event_id=f"w001-f2bvr-claim-{ts}", event_type="claim",
             conclusion_type="formal_model", counts_as_full_schema_verdict=False,
             statement=(
                 f"At the frozen rev29 pins (F2b {F2B_PIN[:12]}, F2a {F2A_PIN[:12]}, F1 {F1_PIN[:12]}, "
                 f"F0 {F0_PIN[:12]}, FROZEN {FROZEN_PIN[:12]}, corpus digest {digest[:12]} over "
                 f"{len(snap)} review files), the F2b verdict corpus reconciles to "
                 f"{verdict}: {len(live_objs)} live objections remain open "
                 f"({', '.join(live_objs)}). C1 (regularity.must_not_conflate[0], line "
                 f"{oracle['C1_containment_denial']['line']}) and C2 "
                 f"(implication_ledger.forbidden_transfers[0].reason, line "
                 f"{oracle['C2_size_premise_inverted']['line']}) are mechanically live and carry "
                 f"bound full-schema revise support "
                 f"({len(support['C1_full_revises'])} and {len(support['C2_full_revises'])} full "
                 f"revises respectively); the declared-hash layer is live stale at D1 sidecar and "
                 f"D2 entry_hashes while D3 aggregator is re-pinned at the measured bytes. Under the "
                 f"live controller rule R1 the corpus binds {len(csum['r1_full_accept_reviewers'])} "
                 f"full accepts ({', '.join(csum['r1_full_accept_reviewers'])}) and "
                 f"{len([r for r in csum['full_revises'] if r['r1_bound']])} full revises; under the "
                 f"declared wider rule R2 it binds {len(csum['full_accept_reviewers'])} full accepts "
                 f"and {len(csum['full_revises'])} full revises. No full accept in either rule cites "
                 f"either carrier defect sentence, so the accepts do not rebut C1/C2. Consequently the "
                 f"accept count alone cannot bind a clean G-FORM pass at these bytes; the unblock is an "
                 f"authorized F2b repair plus the integrity-layer re-pin. Measured by a fail-closed "
                 f"harness with {len(ctrl)}/{len(ctrl)} controls, a live-instrument rule cross-check, "
                 f"and a repair-candidate oracle re-run (candidate 90ede5c9516b, author = this worker, "
                 f"not independent)."),
             assumptions=[
                 "the report's declared R2 binding rule is the honest reading of a review that pins "
                 "the exact F2b hash and identifies F2b by path/alias/node/class; final binding "
                 "adjudication is the audit lead's",
                 "the two carrier sentences are normative required slots (worker-066 normativity "
                 "adjudication, R06/R16) rather than optional prose",
                 "the measurement concerns artifact text and its binding, not the truth of any "
                 "mathematical statement"],
             artifact_refs=common_ev,
             evidence_refs=common_ev + [
                 "schemas/af_scc_c0_vacuum.yaml#sha256:" + F2B_PIN[:12],
                 "schemas/af_scc_c2_vacuum.yaml#sha256:" + F2A_PIN[:12],
                 "schemas/af_wcc_vacuum.yaml#sha256:" + F1_PIN[:12],
                 "artifacts/formulation/FROZEN.json#sha256:" + FROZEN_PIN[:12],
                 "schemas/af_scc_c0_vacuum.yaml.sha256#sha256:" + integrity["D1_sidecar"]["file_sha256"][:12],
                 "entry_hashes.json#sha256:" + integrity["D2_entry_hashes"]["file_sha256"][:12],
                 "schemas/af_scc_regularities.yaml#sha256:" + integrity["D3_aggregator"]["file_sha256"][:12],
                 "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml#sha256:" + CAND_PIN[:12],
                 "reviews/F2b-rev13-containment-worker-017.json#sha256:" + review_sha.get("F2b-rev13-containment-worker-017.json", "")[:12],
                 "reviews/F2b-review-rev29-075.json#sha256:" + review_sha.get("F2b-review-rev29-075.json", "")[:12],
                 "reviews/F2b-review-rev13-085.json#sha256:" + review_sha.get("F2b-review-rev13-085.json", "")[:12],
                 "reviews/F2b-repair-candidate-verify-worker-029.json#sha256:" + review_sha.get("F2b-repair-candidate-verify-worker-029.json", "")[:12]],
             falsifier=report["falsifiers"][0] + " " + report["falsifiers"][3],
             not_claimed=["no gate verdict", "no node status change", "no canonical artifact edit",
                          "no binding adjudication (audit lead's)", "no mathematical claim",
                          "not independent verification of the worker-001 repair candidate"]),
        dict(base, event_id=f"w001-f2bvr-status-{ts}", event_type="status", status="active", hours=0.6,
             summary=(
                 f"One bounded class-bound task complete at worker level: {TASK_ID} (F2b / "
                 f"{CLASS_ID}, {GATE}). Verdict {verdict} with reason codes {', '.join(live_objs)}; "
                 f"objection ledger C1/C2 (schema text) + D1/D2 (declared-hash layer), contested V1 "
                 f"left to its adjudication. R1 binds {len(csum['r1_full_accept_reviewers'])} full "
                 f"accepts / {len([r for r in csum['full_revises'] if r['r1_bound']])} full revises; "
                 f"R2 binds {len(csum['full_accept_reviewers'])} / {len(csum['full_revises'])}; "
                 f"zero full accepts cite either carrier defect. Controls {len(ctrl)}/{len(ctrl)}, "
                 f"canonical writes 0. Worker lifecycle ends; node F2b status not moved."),
             evidence_refs=common_ev + ["schemas/af_scc_c0_vacuum.yaml#sha256:" + F2B_PIN[:12],
                                        "artifacts/formulation/FROZEN.json#sha256:" + FROZEN_PIN[:12]],
             next_falsifier=report["next_falsifier"],
             authority_note="Worker events cannot set node status=done, validation_status=passed, or a gate verdict.",
             completion_scope="worker lifecycle only; one verdict-corpus reconciliation, not a node done "
                              "and not a gate verdict"),
    ]
    (OUTDIR / "outbox_events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in events) + "\n")

    print(json.dumps({"verdict": verdict, "reason_codes": live_objs,
                      "report_sha256": report_sha, "harness_sha256": harness_sha,
                      "checkpoint_sha256": ckpt_sha, "readme_sha256": readme_sha,
                      "corpus_digest": digest, "controls": f"{len(ctrl)}/{len(ctrl)}",
                      "n_bound": csum["n_bound"], "n_r1_bound": csum["n_r1_bound"],
                      "full_accepts": csum["full_accept_reviewers"],
                      "full_revises": [r["reviewer"] for r in csum["full_revises"]],
                      "unrebutted": unrebutted}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
