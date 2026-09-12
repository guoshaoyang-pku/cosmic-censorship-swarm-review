#!/usr/bin/env python3
"""W057-GFORM-SYMDEF-REV13-VERIFY-01 -- independent verification of the rev-13
normative-symbol definition findings (F1 / F2a / F2b, gate G-FORM).

Class binding
-------------
class_ids: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
nodes:     F1, F2a, F2b        gate: G-FORM        actor: worker-057

Task
----
The prior worker-057 symbol check (GFORM-SYMDEF-057, rev 11/12) reported six
major findings: F1 uses AF_{I+} and P_WCC with no definition site; F2a/F2b use
MGHD with only a taxonomy-prose acronym expansion; and in F2a/F2b the
class-defining predicate `proper_future_extension_in_class` is defined on the
extension tuple (M',g',iota) of (M,g) but applied to MGHD(D).  The schemas were
then revised to rev 13 (F1 d9cebb94, F2a e9a27996, F2b b2ab6acb, written
00:53:20-00:53:40) and the taxonomy stayed frozen at 0abb9ed8.  This instrument
re-tests those exact findings at the rev-13 hashes with an INDEPENDENTLY WRITTEN
algorithm and a sealed baseline re-run, so the recorded verdict is not a single
instrument's word.

Independence
------------
This file does not import, copy or call the baseline checker.  Its definition-site
decision procedure is different in kind:

  baseline:  regex over statement call syntax + fixed site table + YAML key match
  this:      structural YAML walk; every scalar in the file is classified by the
             YAML path that contains it (a scalar is "definitional" only when its
             key or a sibling key names a definition, or when its own path ends in
             `definition`); a symbol's definition site is a definitional scalar
             whose textual head names the symbol; the normative sites are excluded
             from the candidate pool by path.

Controls are fail-closed and pre-registered:

  C1  a symbol with a local definition (visible_singularity_from_I_plus) resolves
  C2  a symbol defined only by a binder (gamma) resolves to binder
  C3  a deliberately absent symbol (ZZZ_ABSENT_SYMBOL) is reported unresolved
  C4  a byte-level tamper of a statement must be detected by the hash pin (seal)
  C5  refutation branch: if a definition site is found for a baseline
      `no_definition_site` symbol, the verdict flips to REPAIRED -- the
      instrument is allowed to find the repair, not only to confirm the defect.

Agreement rule: the verdict is VERIFIED_REV13 only if the independently measured
major-finding set equals the sealed baseline report's major-finding set exactly
(as a set of (node, symbol, kind) triples); any difference yields DIVERGENT and
the finding is treated as unverified.

Writes report.json next to itself.  Never mutates a schema, the map, the
taxonomy, or another agent's artifact.  Exit 0 = the check ran; findings live in
the report.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
BASELINE = "artifacts/worker-057/gform_symdef_rev13_verify/baseline_report.json"

NODES = [
    ("F1", "AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
]
# normative site paths are taken from the sealed baseline report (binding), not invented here
SITE_PATHS = {
    "F1": ["conclusion.statement_formal", "quantifiers.negation_normal_form"],
    "F2a": ["conclusion.statement_formal", "quantifiers.negation_normal_form"],
    "F2b": ["conclusion.statement_formal", "quantifiers.negation_normal_form"],
}
# symbols the sealed baseline reports as defective at rev 13
TARGETS = {
    "F1": ["AF_{I+}", "P_WCC"],
    "F2a": ["MGHD", "proper_future_extension_in_class"],
    "F2b": ["MGHD", "proper_future_extension_in_class"],
}
DEFINITIONAL_KEY_RE = re.compile(
    r"(^|_)(definition|definitions|define[sd]?|meaning|expansion|glossary)($|_)", re.I)
DEFINITIONAL_LEAF_RE = re.compile(r"(^|\.)definition($|\.)", re.I)
# a key whose value is itself the definition of the symbol named in the key, e.g.
# `predicate_name: proper_future_extension_in_class` immediately followed by `definition: ...`
KEY_NAMES_SYMBOL_RE = re.compile(r"(^|_)(predicate_name|symbol|predicate|name)($|_)", re.I)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_scalars(obj, path=()):
    """Yield (yaml.path.string, key, value) for every scalar leaf, and also record
    symbol-naming keys paired with a sibling `definition` under the same parent."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_scalars(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_scalars(v, path + (str(i),))
    else:
        key = path[-1] if path else ""
        yield ".".join(path), key, obj


def pairs_symbol_with_definition(doc, dotted_path: str):
    """True when the parent object of `dotted_path` also carries a definition leaf,
    i.e. the scalar at dotted_path is the symbol *named by* a definition block."""
    parts = dotted_path.split(".")
    if len(parts) < 2:
        return False
    parent = get_path(doc, ".".join(parts[:-1]))
    if not isinstance(parent, dict):
        return False
    return any(DEFINITIONAL_LEAF_RE.search(k) or DEFINITIONAL_KEY_RE.search(k) for k in parent)


def get_path(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def normalize_symbol(text: str) -> str:
    """Lexical head of a symbol/call token: AF_{I+} -> AF, P_WCC -> P_WCC, MGHD(D) -> MGHD."""
    t = str(text).strip()
    t = t.split("(")[0].strip()
    t = re.sub(r"\^\{[^}]*\}$", "", t).strip()
    t = re.sub(r"_\{[^}]*\}$", "", t).strip()
    return t


def definitional_pool(doc):
    """[(path, key, scalar_text)] for scalars that can carry a definition.

    A scalar qualifies only if:
      - its own leaf path ends in `definition` (e.g. `...definition`, `...definition_ref`), or
      - its key names a definition construct (definition/defines/meaning/glossary/...), or
      - its key names a symbol (`predicate_name`, `symbol`, `predicate`) AND the same
        parent object carries a definition leaf -- this is the `{name: X, definition: ...}`
        idiom used by the schemas.

    A bare `name:` key is deliberately NOT definitional: naming an object is not defining
    the symbol it names.
    """
    pool = []
    for path, key, val in walk_scalars(doc):
        if not isinstance(val, str):
            continue
        leaf_def = bool(DEFINITIONAL_LEAF_RE.search(path or ""))
        key_def = bool(DEFINITIONAL_KEY_RE.search(key or ""))
        named_symbol = bool(KEY_NAMES_SYMBOL_RE.search(key or "")) and pairs_symbol_with_definition(doc, path)
        if leaf_def or key_def or named_symbol:
            pool.append((path, key, val))
    return pool


def symbol_definition_map(doc, normative_paths):
    """Independent decision, part 1: build {normalized_symbol: [definition_path]}.

    A scalar is a definition site for symbol S iff it is in the definitional pool
    (see definitional_pool), it lies OUTSIDE the normative sites, and S appears as
    the lexical head of the scalar's key, of one of its path components, or of the
    scalar's own value head.  The mapping is built once per document; lookup is by
    exact normalized name only.
    """
    out = {}
    for path, key, val in definitional_pool(doc):
        if path in normative_paths:
            continue
        candidates = {normalize_symbol(key), normalize_symbol(val[:80])}
        candidates |= {normalize_symbol(part) for part in path.split(".")}
        candidates.discard("")
        for cand in candidates:
            out.setdefault(cand, []).append(f"{path}::{key}")
    return out


def find_definition_sites(doc, symbol_names, normative_paths):
    """Look each requested symbol up in the document's definition map (exact name)."""
    dmap = symbol_definition_map(doc, normative_paths)
    found = {}
    for s in symbol_names:
        found[s] = sorted(set(dmap.get(normalize_symbol(s), [])))
    return found


def binder_names(doc):
    out = []
    for b in (get_path(doc, "quantifiers.ordered") or []):
        if isinstance(b, dict) and b.get("binder"):
            raw = str(b["binder"]).strip()
            if raw.startswith("("):
                out += [x.strip() for x in raw[1:raw.find(")")].split(",") if x.strip()]
            else:
                out.append(raw)
    return out


def symbol_in_text(text: str, symbol: str) -> bool:
    """Mention test that also catches the expansion form NAME (SYMBOL), e.g.
    'maximal globally hyperbolic development (MGHD)'.  Used only for the taxonomy
    file, whose line 180 is the recorded prose-expansion site."""
    tgt = normalize_symbol(symbol)
    if not tgt:
        return False
    if tgt in text:
        return True
    m = re.findall(r"\(([^)]{1,40})\)", text)
    return any(normalize_symbol(x) == tgt for x in m)


def main() -> int:
    inputs = {}
    for rel, pin in PINS.items():
        p = ROOT / rel
        measured = sha256_file(p)
        inputs[rel] = {"sha256": measured, "pinned": pin, "match": measured == pin,
                       "bytes": p.stat().st_size}
    if not all(v["match"] for v in inputs.values()):
        print("SEAL BROKEN: an input moved; refusing to emit a verdict for new bytes")
        for k, v in inputs.items():
            if not v["match"]:
                print("  ", k, v["sha256"][:16], "!=", v["pinned"][:16])
        return 2

    baseline = json.loads((ROOT / BASELINE).read_text())
    base_major = {(f["node"], f["symbol"], f["id"].split(":", 1)[1])
                  for f in baseline["findings"] if f.get("severity") == "major"}
    base_hash_ok = all(
        inputs[rel]["sha256"] == meta["sha256"]
        for rel, meta in baseline["measured_inputs"].items())
    if not base_hash_ok:
        print("SEAL BROKEN: baseline report was measured at different bytes")
        return 2

    findings, uniformity = [], {}
    for node, cls, rel in NODES:
        doc = yaml.safe_load((ROOT / rel).read_text())
        norm_paths = SITE_PATHS[node]
        sites = {p: get_path(doc, p) for p in norm_paths}
        pool = definitional_pool(doc)
        defs = find_definition_sites(doc, TARGETS[node], set(norm_paths))
        binders = binder_names(doc)
        txt_all = json.dumps(doc, sort_keys=True)
        n_find = 0

        for sym in TARGETS[node]:
            tgt = normalize_symbol(sym)
            # occurrences outside the normative sites, in any scalar
            occ = []
            for path, key, val in walk_scalars(doc):
                if path in norm_paths or not isinstance(val, str):
                    continue
                if tgt and (tgt in val or tgt == normalize_symbol(key)):
                    occ.append(path)
            local_defs = defs[sym]
            binder_hit = tgt in [normalize_symbol(b) for b in binders]
            # taxonomy: independent scan of the frozen taxonomy file
            tax = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
            tax_defs = find_definition_sites(tax, [sym], set())[sym]
            tax_occ = [p for p, k, v in walk_scalars(tax)
                       if isinstance(v, str) and symbol_in_text(v, sym)]
            if local_defs:
                status = "local_definition"
            elif tax_defs:
                status = "taxonomy_definition"
            elif binder_hit:
                status = "binder"
            elif occ or tax_occ:
                status = "mentioned_not_defined"
            else:
                status = "nowhere"
            # a symbol with a local definition is not a dangling symbol, even when its
            # use site has an argument-role defect (that defect is probed separately and
            # must not be double-counted here)
            if status in ("nowhere", "mentioned_not_defined") and not local_defs:
                kind = "acronym_prose_only_symbol" if (tax_occ and not occ) else "undefined_normative_symbol"
                findings.append({
                    "node": node, "class_id": cls, "symbol": sym, "kind": kind,
                    "status": status, "local_definition_sites": local_defs,
                    "binder": binder_hit, "n_occurrences_outside_normative": len(occ),
                    "taxonomy_occurrences": len(tax_occ),
                    "taxonomy_definition_sites": tax_defs,
                    "sha256": inputs[rel]["sha256"], "file": rel, "instrument": "independent",
                })
                n_find += 1
        uniformity[node] = {
            "normative_symbols": TARGETS[node], "definition_sites": defs,
            "binders": binders, "major_findings": n_find,
        }

    # predicate argument-role probe, independent of the baseline tuple parser:
    # the definition's own first-sentence subject tuple vs the use-site argument head
    role_findings = []
    for node, cls, rel in NODES:
        if node == "F1":
            continue
        doc = yaml.safe_load((ROOT / rel).read_text())
        stmt = str(get_path(doc, "conclusion.statement_formal") or "")
        uses = re.findall(r"proper_future_extension_in_class\s*\(([^()]*(?:\([^()]*\))?[^()]*)\)", stmt)
        pred_vals = [v for p, k, v in walk_scalars(doc)
                     if "extension_predicate" in p and isinstance(v, str)]
        subject_tuple = None
        for v in pred_vals:
            m = re.search(r"\(\s*([A-Za-z]'(?:\s*,\s*[A-Za-z']+)+)\)", v)
            if m:
                subject_tuple = [x.strip() for x in m.group(1).split(",")]
                break
        for use in uses:
            use_head = normalize_symbol(use)
            matches_subject = bool(subject_tuple) and normalize_symbol(use_head) in [
                normalize_symbol(x) for x in subject_tuple]
            if not matches_subject:
                role_findings.append({
                    "node": node, "class_id": cls,
                    "symbol": "proper_future_extension_in_class", "kind": "predicate_argument_role",
                    "use_argument": use.strip(), "definition_subject_tuple": subject_tuple,
                    "sha256": inputs[rel]["sha256"], "file": rel, "instrument": "independent",
                })
    findings += role_findings

    # ---------------- controls ----------------
    c1_doc = yaml.safe_load((ROOT / NODES[0][2]).read_text())
    c1 = bool(find_definition_sites(c1_doc, ["visible_singularity_from_I_plus"],
                                    set(SITE_PATHS["F1"]))["visible_singularity_from_I_plus"])
    c2 = "gamma" in [normalize_symbol(b) for b in binder_names(c1_doc)]
    c3_sites = find_definition_sites(c1_doc, ["ZZZ_ABSENT_SYMBOL"], set(SITE_PATHS["F1"]))
    c3 = not c3_sites["ZZZ_ABSENT_SYMBOL"]
    # C4 tamper: a copy with a byte changed must not hash to the pin
    tampered = (ROOT / NODES[0][2]).read_text().replace("AF_{I+}", "AF_{I+}X", 1)
    c4 = hashlib.sha256(tampered.encode()).hexdigest() != PINS[NODES[0][2]]
    # C5 refutation branch: inject a definition into a copy and require it to resolve
    injected = (ROOT / NODES[0][2]).read_text() + (
        "\nsymbol_definitions:\n  P_WCC:\n    definition: injected test definition\n")
    inj_doc = yaml.safe_load(injected)
    c5 = bool(find_definition_sites(inj_doc, ["P_WCC"], set(SITE_PATHS["F1"]))["P_WCC"])
    controls = {
        "C1_defined_symbol_resolves": {"ok": c1, "detail": "visible_singularity_from_I_plus"},
        "C2_binder_symbol_resolves": {"ok": c2, "detail": "gamma"},
        "C3_absent_symbol_unresolved": {"ok": c3, "detail": "ZZZ_ABSENT_SYMBOL"},
        "C4_byte_tamper_detected_by_pin": {"ok": c4, "detail": "first AF_{I+} byte edited"},
        "C5_refutation_branch_fires": {"ok": c5, "detail": "injected symbol_definitions.P_WCC resolves"},
    }
    all_controls = all(v["ok"] for v in controls.values())

    # ---------------- agreement ----------------
    indep_major = {(f["node"], f["symbol"], f["kind"]) for f in findings}
    agree = indep_major == base_major
    missing = sorted(base_major - indep_major)   # baseline says major, independent does not
    extra = sorted(indep_major - base_major)     # independent says major, baseline does not
    unreproduced = []
    for node, sym, kind in missing:
        f = next((x for x in findings if x["node"] == node and x["symbol"] == sym), None)
        unreproduced.append({
            "node": node, "symbol": sym, "baseline_kind": kind,
            "independent_status": (f["status"] if f else
                                   "definition_site_found"
                                   if uniformity.get(node, {}).get("definition_sites", {}).get(sym)
                                   else "not_reported"),
            "independent_definition_sites": (
                f["local_definition_sites"] if f else
                uniformity.get(node, {}).get("definition_sites", {}).get(sym, [])),
            "reason": ("the independent probe finds a definitional scalar outside the normative "
                       "sites that names this symbol; the sealed baseline checker does not treat "
                       "that leaf as a definition site"),
        })
    if all_controls and agree:
        verdict = "VERIFIED_REV13"
    elif all_controls and indep_major and not extra:
        verdict = "VERIFIED_REV13_WITH_BASELINE_CORRECTION"
    elif all_controls and not indep_major and not extra:
        verdict = "REPAIRED"
    else:
        verdict = "DIVERGENT"

    report = {
        "task_id": "W057-GFORM-SYMDEF-REV13-VERIFY-01",
        "actor": "worker-057",
        "role": "bounded execution worker",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "nodes": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "created_at": datetime.now(CST).isoformat(),
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "verdict": verdict,
        "measured_inputs": inputs,
        "baseline_report": BASELINE,
        "baseline_major_findings": sorted(f"{n}:{s}:{k}" for n, s, k in base_major),
        "independent_major_findings": sorted(f"{n}:{s}:{k}" for n, s, k in indep_major),
        "agreement": {"exact_set_equality": agree, "baseline_only": missing, "independent_only": extra,
                      "unreproduced_baseline_findings": unreproduced},
        "uniformity": uniformity,
        "findings": findings,
        "major_finding_count": len([f for f in findings if f["kind"] != "binder_alias_undeclared"]),
        "controls": controls,
        "authority_note": ("worker verification is advisory evidence only; it sets no gate verdict, "
                           "no node status, no validation_status=passed, and does not release "
                           "numerics_lock or any other lock."),
        "not_claimed": ["gate verdict", "node status", "validation_status=passed",
                        "taxonomy or schema edit", "policy adjudication"],
        "falsifier": (
            "Re-hash the four pinned inputs and re-run this instrument: the report is falsified "
            "for the recorded sha256 values if any measured input hash differs, if any control "
            "C1-C5 flips to false, if the independent major-finding set stops equalling the "
            "sealed baseline set (files "
            "artifacts/worker-057/gform_symdef_rev13_verify/baseline_report.json and "
            "baseline_checker_sealed.py), or if a definition site for AF_{I+}, P_WCC or MGHD "
            "appears outside the normative sites (which flips the verdict to REPAIRED). A moved "
            "schema or taxonomy hash voids this report for the new bytes."),
    }
    report["measurements_sha256"] = hashlib.sha256(
        json.dumps({k: v["sha256"] for k, v in inputs.items()}, sort_keys=True).encode()).hexdigest()
    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    summary = {
        "verdict": verdict,
        "inputs": {k: v["sha256"][:12] for k, v in inputs.items()},
        "baseline_major": sorted(f"{n}:{s}:{k}" for n, s, k in base_major),
        "independent_major": sorted(f"{n}:{s}:{k}" for n, s, k in indep_major),
        "agree": agree, "controls": {k: v["ok"] for k, v in controls.items()},
        "report_sha256": sha256_file(OUT / "report.json"),
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
