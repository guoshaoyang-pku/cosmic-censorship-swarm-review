#!/usr/bin/env python3
"""GFORM-SYMDEF-057: normative-symbol definition consistency across F1/F2a/F2b.

Task (class-bound): AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN.
Nodes: F1, F2a, F2b.  Gate: G-FORM.  Actor: worker-057.  Lifecycle 2.

Question: the G-FORM criterion demands exact quantifiers and a full-schema
accept.  F1 already carries recorded hard failures for symbols used in the
normative conclusion but defined nowhere (AF_{I+}, complete).  This probe asks
whether the SAME rule, applied mechanically to the sibling class schemas at the
current canonical rev-11 hashes, fires there too -- i.e. whether the dangling-
symbol policy is applied uniformly across the three classes.

Probes (deterministic; canonical files only):
  P1  extract every call/function symbol from conclusion.statement_formal and
      quantifiers.negation_normal_form
  P2  for each symbol: local definition site (name/predicate_name + definition),
      binder, taxonomy-prose-only occurrence, or nowhere
  P3  realized binder names in conclusion.statement_formal vs
      quantifiers.ordered binder names
  P4  for the class-defining extension predicate: the argument role at the use
      site vs the first-class tuple named in the definition's first sentence

Controls: C1 visibility predicate resolves; C2 extension predicate resolves;
C3 mutant self-test (undefined outer / plain undefined / definitions-map
resolution / binder tokenizer / subscript-symbol capture).

Writes report.json next to itself and prints a summary.  Never mutates a
schema, the map, or another agent's artifact.  Exit 0 = the check ran; findings
are in the report.  Reproduce:
  python3 artifacts/worker-057/symdef_check/check_normative_symbols.py
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

INPUTS = [
    ("F1", "AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
]
TAXONOMY = "research_map/formulation_taxonomy.yaml"

KEYWORDS = {
    "forall", "exists", "not", "and", "or", "in", "iff", "if", "then", "such",
    "that", "is", "be", "the", "a", "an", "of", "with", "subset", "comeager",
    "non", "meager", "empty", "letting", "proper", "future", "past", "some",
    "any", "every", "no", "at", "on", "to", "for", "as", "by",
}
CALL_RE = re.compile(r"(?<![\w.{}^])([A-Za-z][A-Za-z_0-9']*(?:_\{[^}]{0,24}\})?(?:\^\{[^}]{0,24}\})?)\s*\(")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 0


def calls_in(text: str):
    out = []
    for m in CALL_RE.finditer(text):
        name = m.group(1)
        if name in KEYWORDS or "^" in name:
            continue
        i = m.end() - 1
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    out.append({"symbol": name, "arg_text": text[i + 1:j], "offset": m.start()})
                    break
    return out


def split_top(s: str):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def binder_symbols(binder: str):
    if not isinstance(binder, str):
        return []
    b = binder.strip()
    if b.startswith("(") and ")" in b:
        return [x.strip() for x in split_top(b[1:b.find(")")]) if x.strip()]
    m = re.match(r"([A-Za-z][A-Za-z_0-9']*)", b)
    return [m.group(1).rstrip("_")] if m else []


def realized_binders(statement: str):
    """[(kind, name)] for binders written after a quantifier keyword."""
    out = []
    for m in re.finditer(r"\b(forall|exists)\b", statement):
        before = statement[max(0, m.start() - 4):m.start()]
        kind = "not_exists" if before.rstrip().endswith("not") else m.group(1)
        rest = statement[m.end():]
        tok = re.match(r"\s*(\([^()]*\)|[A-Za-z][A-Za-z_0-9']*(?:_\{[^}]{0,24}\})?)", rest)
        if not tok:
            continue
        raw = tok.group(1)
        after = rest[tok.end():]
        if raw.startswith("("):
            names = [x for x in split_top(raw[1:-1]) if x]
        else:
            if raw in KEYWORDS or after.lstrip().startswith("("):
                continue  # logical word or a predicate call, not a binder
            names = [raw.split("_{")[0].rstrip("_")]
        for n in names:
            out.append({"kind": kind, "name": n})
    return out


def local_definitions(doc) -> dict:
    """symbol -> json-path of a dict carrying name/predicate_name + definition."""
    found = {}

    def walk(o, p):
        if isinstance(o, dict):
            for key in ("name", "predicate_name"):
                v = o.get(key)
                if isinstance(v, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", v.strip()):
                    if "definition" in o:
                        found.setdefault(v.strip(), f"{p}.{key}")
            for k, v in o.items():
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")

    walk(doc, "$")
    return found


def taxonomy_occurrence(sym: str, tax_text: str):
    """Line of a taxonomy occurrence of the symbol, if any.

    Symbols carrying braces must match exactly (AF_{I+}); plain symbols match
    as whole words (MGHD)."""
    if "{" in sym:
        rx = re.compile(re.escape(sym))
    else:
        if len(sym) < 2:
            return 0
        rx = re.compile(r"(?<![A-Za-z_])" + re.escape(sym) + r"(?![A-Za-z_0-9])")
    for i, line in enumerate(tax_text.splitlines(), 1):
        if rx.search(line):
            return i
    return 0


def file_prose_definition(doc, sym):
    """json-path of a definition-style key in the file naming the symbol, e.g.
    i_plus.completeness_definition for the predicate `complete`."""
    base = sym.split("_{")[0].split("^{")[0].lower()
    if len(base) < 5 or not re.fullmatch(r"[a-z][a-z_0-9']*", base):
        return None
    hits = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if isinstance(v, str) and len(v) > 10 and base in kl and ("definition" in kl or "meaning" in kl):
                    hits.append(f"{p}.{k}")
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")

    walk(doc, "$")
    return hits[0] if hits else None


def definition_first_tuples(definition: str):
    if not isinstance(definition, str):
        return None, None
    first = definition.split(" iff")[0]
    parsed = []
    for t in re.findall(r"\(([^()]*)\)", first):
        names = [x.strip() for x in split_top(t) if x.strip()]
        if names and all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9']*", n) for n in names):
            parsed.append(names)
    if not parsed:
        return None, None
    return parsed[0], (parsed[1] if len(parsed) > 1 else None)


def probe(tag: str, klass: str, rel: str, tax_text: str) -> dict:
    path = ROOT / rel
    raw = path.read_text()
    doc = yaml.safe_load(raw)
    st = path.stat()
    q = doc.get("quantifiers") if isinstance(doc.get("quantifiers"), dict) else {}
    ordered = q.get("ordered") if isinstance(q.get("ordered"), list) else []
    declared = []
    for row in ordered:
        if isinstance(row, dict):
            for n in binder_symbols(row.get("binder")):
                declared.append({"binder": row.get("binder"), "name": n,
                                 "kind": row.get("kind"), "domain_id": row.get("domain_id")})
    bound = {d["name"] for d in declared}
    defs = local_definitions(doc)
    concl = doc.get("conclusion") if isinstance(doc.get("conclusion"), dict) else {}

    sites = {
        "conclusion.statement_formal": concl.get("statement_formal"),
        "quantifiers.negation_normal_form": q.get("negation_normal_form"),
    }
    site_report = {}
    for site, text in sites.items():
        if not isinstance(text, str):
            site_report[site] = {"present": False}
            continue
        rows = []
        for c in calls_in(text):
            sym, args = c["symbol"], c["arg_text"]
            arg_ids = [a for a in re.findall(r"[A-Za-z_][A-Za-z_0-9']*", args)]
            if sym in defs:
                status, defsite = "local_definition", defs[sym]
            elif sym in bound:
                status, defsite = "bound_binder", None
            else:
                fpd = file_prose_definition(doc, sym)
                tl = taxonomy_occurrence(sym, tax_text)
                if fpd:
                    status, defsite = "file_prose_definition", fpd
                elif tl:
                    status, defsite = "external_acronym_prose", f"{TAXONOMY}:{tl}"
                else:
                    status, defsite = "no_definition_site", None
            row = {"symbol": sym, "arg_text": args, "arg_identifiers": arg_ids,
                   "status": status, "definition_site": defsite,
                   "line_hint": line_of(raw, text[:100])}
            if sym in defs:
                for container in ("extension_predicate", "visibility"):
                    d = doc.get(container)
                    if isinstance(d, dict) and d.get("name", d.get("predicate_name")) == sym:
                        subj, base = definition_first_tuples(d.get("definition"))
                        row["definition_subject_tuple"] = subj
                        row["definition_base_tuple"] = base
                        row["argument_matches_definition_subject"] = bool(subj and set(arg_ids) & set(subj))
                        row["argument_matches_definition_base"] = bool(base and set(arg_ids) & set(base))
            rows.append(row)
        entry = {"present": True, "text": text, "calls": rows}
        if site == "conclusion.statement_formal":
            rb = realized_binders(text)
            entry["realized_binders"] = rb
            entry["realized_binder_names"] = sorted({r["name"] for r in rb})
            entry["declared_binder_names"] = sorted(bound)
            entry["realized_not_declared"] = sorted({r["name"] for r in rb} - bound)
            entry["declared_not_realized"] = sorted(bound - {r["name"] for r in rb})
        site_report[site] = entry

    return {
        "node_id": tag, "class_id": klass, "path": rel,
        "sha256": sha256_file(path), "revision": doc.get("revision"),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(),
        "file_class_id": doc.get("class_id"), "file_node_id": doc.get("node_id"),
        "declared_binders": declared,
        "local_definitions": defs,
        "sites": site_report,
    }


def mutant_selftest() -> list:
    res = []

    def run(text, doc):
        defs = local_definitions(doc)
        return [{"symbol": c["symbol"], "defined": c["symbol"] in defs} for c in calls_in(text)]

    r = run("forall D in G: not exists bogus_pred(MGHD(D))", {})
    res.append({"mutant": "M1_undefined_outer", "got": r,
                "pass": any(x["symbol"] == "bogus_pred" and not x["defined"] for x in r)
                        and any(x["symbol"] == "MGHD" and not x["defined"] for x in r)})
    r = run("forall x in D: P(x)", {})
    res.append({"mutant": "M2_plain_undefined", "got": r,
                "pass": any(x["symbol"] == "P" and not x["defined"] for x in r)})
    r = run("forall x in D: P(x)", {"definitions": {"P": {"name": "P", "definition": "P(x) iff x is P"}}})
    res.append({"mutant": "M3_defined_resolves", "got": r,
                "pass": any(x["symbol"] == "P" and x["defined"] for x in r)})
    rb = realized_binders("forall (s,delta) in D0 exists G_{s,delta} comeager forall D in G_{s,delta}: not exists P(MGHD(D))")
    names = sorted({x["name"] for x in rb})
    res.append({"mutant": "M4_binder_names", "got": names,
                "pass": names == ["D", "G", "delta", "s"]})
    r = run("forall D in D0: AF_{I+}(M_D) and complete(I+_D)", {})
    res.append({"mutant": "M5_subscript_and_word_symbols", "got": r,
                "pass": any(x["symbol"] == "AF_{I+}" and not x["defined"] for x in r)
                        and any(x["symbol"] == "complete" and not x["defined"] for x in r)})
    return res


def main() -> int:
    started = datetime.now(CST)
    tax = ROOT / TAXONOMY
    tax_text = tax.read_text()
    schemas = [probe(*row, tax_text) for row in INPUTS]
    findings = []
    for s in schemas:
        for site, p in s["sites"].items():
            if not p.get("present"):
                continue
            for c in p["calls"]:
                if c["status"] in ("no_definition_site", "external_acronym_prose"):
                    findings.append({
                        "id": f"{s['node_id']}:" + ("undefined_normative_symbol"
                                                    if c["status"] == "no_definition_site"
                                                    else "acronym_prose_only_symbol"),
                        "node": s["node_id"], "class_id": s["class_id"], "site": site,
                        "symbol": c["symbol"], "arg_text": c["arg_text"], "status": c["status"],
                        "sha256": s["sha256"], "file": s["path"],
                        "detail": (f"normative site uses '{c['symbol']}({c['arg_text']})'; "
                                   f"no local definition site in the file; "
                                   + ("no occurrence in the canonical taxonomy either"
                                      if c["status"] == "no_definition_site"
                                      else f"canonical taxonomy occurrence at {c['definition_site']} (prose/acronym only, no definition_ref)")),
                        "severity": "major",
                    })
                if c.get("definition_subject_tuple") and c.get("argument_matches_definition_subject") is False:
                    findings.append({
                        "id": f"{s['node_id']}:predicate_argument_role",
                        "node": s["node_id"], "class_id": s["class_id"], "site": site,
                        "symbol": c["symbol"], "arg_text": c["arg_text"],
                        "definition_subject_tuple": c["definition_subject_tuple"],
                        "definition_base_tuple": c["definition_base_tuple"],
                        "matches_subject_by_name": c.get("argument_matches_definition_subject"),
                        "matches_base_by_name": c.get("argument_matches_definition_base"),
                        "sha256": s["sha256"], "file": s["path"],
                        "detail": (f"'{c['symbol']}' is defined on the extension tuple {c['definition_subject_tuple']} "
                                   f"of {c['definition_base_tuple']}, but is applied to '{c['arg_text']}' "
                                   f"(the development of the data), so the extension existential is implicit at the use site"),
                        "severity": "major",
                    })
            for nm in p.get("realized_not_declared", []):
                findings.append({
                    "id": f"{s['node_id']}:binder_alias_undeclared",
                    "node": s["node_id"], "class_id": s["class_id"], "site": site,
                    "binder_name": nm, "declared": p["declared_binder_names"],
                    "sha256": s["sha256"], "file": s["path"],
                    "detail": f"statement realizes binder '{nm}' that is not a quantifiers.ordered binder name (notational alias)",
                    "severity": "info",
                })

    # uniformity table: the same rule over the three classes
    uniformity = {}
    for s in schemas:
        syms = [c for p in s["sites"].values() if p.get("present") for c in p["calls"]]
        uniformity[s["node_id"]] = {
            "class_id": s["class_id"], "sha256": s["sha256"],
            "normative_symbols": sorted({c["symbol"] for c in syms}),
            "local_definition": sorted({c["symbol"] for c in syms if c["status"] == "local_definition"}),
            "file_prose_definition": sorted({c["symbol"] for c in syms if c["status"] == "file_prose_definition"}),
            "external_acronym_prose": sorted({c["symbol"] for c in syms if c["status"] == "external_acronym_prose"}),
            "no_definition_site": sorted({c["symbol"] for c in syms if c["status"] == "no_definition_site"}),
        }

    # dedupe findings that fire at more than one normative site
    merged = {}
    for f in findings:
        key = (f["node"], f["id"], f.get("symbol") or f.get("binder_name"))
        if key in merged:
            merged[key]["sites"].append(f["site"])
        else:
            f = dict(f)
            f["sites"] = [f.pop("site")]
            merged[key] = f
    findings = list(merged.values())

    report = {
        "task_id": "GFORM-SYMDEF-057",
        "actor": "worker-057", "lifecycle": 2, "role": "bounded execution worker",
        "gate": "G-FORM", "nodes": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": started.isoformat(),
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "measured_inputs": {s["path"]: {"sha256": s["sha256"], "revision": s["revision"],
                                        "bytes": s["bytes"], "mtime": s["mtime"]} for s in schemas},
        "taxonomy": {"path": TAXONOMY, "sha256": sha256_file(tax)},
        "uniformity_table": uniformity,
        "schemas": schemas,
        "findings": findings,
        "major_finding_count": len([f for f in findings if f["severity"] == "major"]),
        "controls": {
            "C1_visibility_predicate_resolves": any(
                c["symbol"] == "visible_singularity_from_I_plus" and c["status"] == "local_definition"
                for s in schemas if s["node_id"] == "F1"
                for p in s["sites"].values() if p.get("present") for c in p["calls"]),
            "C2_extension_predicate_resolves": all(
                any(c["symbol"] == "proper_future_extension_in_class" and c["status"] == "local_definition"
                    for p in s["sites"].values() if p.get("present") for c in p["calls"])
                for s in schemas if s["node_id"] in ("F2a", "F2b")),
            "C3_mutants": mutant_selftest(),
        },
        "known_overlaps": [
            {"ref": "reviews/F1-review-19.json#findings[1] (HF-06) + reviews/F1-review-090.json",
             "item": "F1 AF_{I+} and complete(...) as undefined/prose-only normative symbols at statement_formal; re-confirmed here, not claimed as new"},
            {"ref": "runtime/state/w57_checkpoint_1.json",
             "item": "previous worker-057 lifecycle measured quantifier KINDS (6 declared vs 4 realized in F1); this run measures symbol definitions and binder NAMES"},
            {"ref": "artifacts/worker-17/quantifier_nf/qnf_report.json",
             "item": "worker-17 typed D as a data-set alias and MGHD under context_vocabulary with C3_free_variable_capture=true; this run applies the strict definition-site rule used for F1's HF-06 and reports the resulting cross-class asymmetry for adjudication"},
        ],
        "adjudication_note": (
            "This report does not decide the policy.  Two readings are coherent: (strict) a normative statement bound into "
            "the class conclusion must use only symbols with a definition site, which makes F2a/F2b 'MGHD' the same defect "
            "class as F1's AF_{I+}; (lenient) an acronym expanded in prose in the canonical F0 taxonomy is an external "
            "definition, which clears MGHD while leaving P_WCC (F1 negation_normal_form, nowhere) as the only new "
            "undefined normative symbol.  The uniformity table is the evidence either way."
        ),
        "authority_note": "worker events cannot set status=done, validation_status=passed, or a gate verdict; unverified input to lead/reviewer adjudication",
        "falsifier": (
            "Re-hash the three schemas and the taxonomy and re-run this script: the report is falsified for the recorded "
            "hashes if any measured sha256 differs; if a definition site for MGHD or P_WCC appears in the same file (or a "
            "definition_ref binds the symbol); if the extension predicate is redefined to take the development as its "
            "first-class argument; or if the realized/declared binder-name sets change.  A control C1/C2 flipping to False "
            "or any C3 mutant failing falsifies the scanner."),
        "limits": [
            "structural/syntactic only; no mathematical or physical correctness is decided",
            "no citation-scope verification (L1 owns it); no gate verdict",
            "the 'taxonomy_prose_only' class is a keyword occurrence in prose, not a formal definition; it is deliberately reported as a separate class from 'nowhere'",
            "canonical paths only; the authoring tree is not read",
        ],
    }
    report["measurements_sha256"] = hashlib.sha256(
        json.dumps(report["measured_inputs"], sort_keys=True).encode()).hexdigest()
    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "task": report["task_id"],
        "inputs": {k: v["sha256"][:12] for k, v in report["measured_inputs"].items()},
        "uniformity": {k: {"local": v["local_definition"], "file_prose": v["file_prose_definition"],
                           "acronym_prose": v["external_acronym_prose"], "undefined": v["no_definition_site"]}
                       for k, v in uniformity.items()},
        "major_findings": [(f["node"], f["symbol"], f["id"].split(":")[1]) for f in findings if f["severity"] == "major"],
        "controls": {"C1": report["controls"]["C1_visibility_predicate_resolves"],
                     "C2": report["controls"]["C2_extension_predicate_resolves"],
                     "mutants": [m["pass"] for m in report["controls"]["C3_mutants"]]},
        "report_sha256": sha256_file(OUT / "report.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
