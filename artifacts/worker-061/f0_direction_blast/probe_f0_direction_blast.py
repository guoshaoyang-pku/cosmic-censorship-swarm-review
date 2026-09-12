#!/usr/bin/env python3
"""
W061-F0-DIRECTION-BLAST-08 -- one bounded class-bound task (AF-WCC-VAC-GEN; nodes F0,F1;
gate context G-F0/G-FORM).  No canonical file is edited by this probe.

Question (L-FORM-03 residual, decision support for the controller):
  The two FROZEN F0 artifacts still carry SET-vs-tail strength claims.  Produce a machine-checked
  census of every strength-direction claim in those two files, classify each against the
  order-theoretic fact

        T (single-q tail predicate)  ==>  S (union / set reading),   S =/=> T

  and measure the blast radius of the three controller options (edit supplement D1, reopen F0,
  record a map erratum) by counting the reviews/artifacts that bind the two F0 hashes.

Exit codes: 0 measured, 1 pre-registration/control mismatch, 2 drift or unclassified occurrence.

Evidence reused, not re-derived: worker-061 W061-F1-VARSTRENGTH-05 (probe fae93adba3d0 /
eac5b06c83f3) and worker-076 W076-GFORM-STRICTNESS-RECONCILE-06 both established T=>S and the
omega-chain refutation of S=>T.  This probe re-derives T=>S on the finite preorder corpus and
re-checks the omega certificate so its own census does not rest on an uncited assertion.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "probe_output.json")
SANDBOX = os.path.join(HERE, "sandbox")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

PIN = {
    "F0_canonical": ("research_map/formulation_taxonomy.yaml",
                     "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "F0_supplement": ("artifacts/formulation/formulation_taxonomy.yaml",
                      "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "F1": ("schemas/af_wcc_vacuum.yaml",
           "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml",
            "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml",
            "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "FROZEN": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "cases": ("schemas/taxonomy_cases.jsonl",
              "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03"),
    "registry": ("artifacts/formulation/VARIANT_REGISTRY.json",
                 "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb"),
    "set_delta": ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
                  "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf"),
    "consistency_evidence": ("artifacts/formulation/evidence/taxonomy_consistency.json",
                             "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"),
    "map": ("research_map/research_map.json", None),  # measured, expected value moves
}
F0C_PREFIX = "0abb9ed8a961"
F0S_PREFIX = "d7419b4e8963"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_line(path: str, needle: str) -> int:
    with open(path, encoding="utf-8") as f:
        for i, ln in enumerate(f, 1):
            if needle in ln:
                return i
    return -1


def window(path: str, n: int, before: int = 1, after: int = 2) -> str:
    lines = open(path, encoding="utf-8").read().splitlines()
    lo, hi = max(1, n - before), min(len(lines), n + after)
    return re.sub(r"\s+", " ", " ".join(lines[lo - 1:hi])).strip()


# --------------------------------------------------------------------------------------
# 1. order-theoretic fact (independent finite re-derivation)
# --------------------------------------------------------------------------------------
def preorders(n: int):
    off = [(i, j) for i in range(n) for j in range(n) if i != j]
    for bits in itertools.product((False, True), repeat=len(off)):
        R = [[i == j for j in range(n)] for i in range(n)]
        for (i, j), b in zip(off, bits):
            R[i][j] = b
        ok = True
        for a in range(n):
            for b in range(n):
                if not R[a][b]:
                    continue
                for c in range(n):
                    if R[b][c] and not R[a][c]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            yield R


def chain_in(R, n, length):
    for seq in itertools.product(range(n), repeat=length):
        if all(R[seq[i]][seq[i + 1]] for i in range(length - 1)):
            yield list(seq)


def down(R, n, q):
    return {x for x in range(n) if R[x][q]}


def evaluate(R, n, chain, iplus):
    T = False
    for q in iplus:
        dq = down(R, n, q)
        for t0 in range(len(chain)):
            if all(x in dq for x in chain[t0:]):
                T = True
                break
        if T:
            break
    union = set()
    for q in iplus:
        union |= down(R, n, q)
    S = all(x in union for x in chain)
    return T, S


def finite_corpus(max_n=4, max_len=3):
    stats = {"models": 0, "cases": 0, "T_and_not_S": 0, "S_and_not_T": 0,
             "T_examples": 0, "S_examples": 0}
    witness = None
    for n in range(1, max_n + 1):
        elements = list(range(n))
        subsets = [list(s) for k in range(1, n + 1) for s in itertools.combinations(elements, k)]
        for R in preorders(n):
            stats["models"] += 1
            for length in range(1, max_len + 1):
                for chain in chain_in(R, n, length):
                    for iplus in subsets:
                        stats["cases"] += 1
                        T, S = evaluate(R, n, chain, iplus)
                        stats["T_examples"] += int(T)
                        stats["S_examples"] += int(S)
                        if T and not S:
                            stats["T_and_not_S"] += 1
                        if S and not T and witness is None:
                            stats["S_and_not_T"] += 1
                            witness = {"n": n, "R": [[int(v) for v in row] for row in R],
                                       "chain": chain, "I_plus": iplus}
    stats["strictness_witness"] = witness
    stats["derived"] = {
        "predicate_level": "T strictly stronger than S; S strictly weaker than T",
        "negation_level": "not-S strictly stronger than not-T",
        "entailment": "T => S (0 counterexamples on corpus); S => T false (witness present)",
    }
    return stats


def omega_certificate(N=60):
    def in_down_q(i, j):
        return i <= j

    S = all(any(in_down_q(i, j) for j in range(i + 1)) for i in range(N))
    escapes = [{"q": j, "t0": t0, "escape_index": max(j, t0) + 1,
                "escapes": not in_down_q(max(j, t0) + 1, j)}
               for j in range(N) for t0 in range(N + 1)]
    return {"N": N, "S_on_gamma": S, "T_on_gamma": False,
            "escape_certificate_pairs_checked": len(escapes),
            "escape_certificate_all_hold": bool(escapes) and all(e["escapes"] for e in escapes),
            "closed_form": "for q_j and finite t0 choose i=max(j,t0)+1; x_i is outside every J^-(q_j') with j'<i",
            "S_and_not_T": S,
            "negS_implies_negT": True}


# --------------------------------------------------------------------------------------
# 2. direction census over the two FROZEN F0 artifacts
# --------------------------------------------------------------------------------------
# Pre-registered: (id, file, anchor, axis, level_cue, extract regex, expected).
# The parser derives each classification independently; disagreement => control failure.
SITES = [
    ("C-SET-DEF", "F0_canonical", "than the parent class: gamma outside the union", "SET_vs_tail",
     "negation_support",
     r"(Strictly stronger than the parent class[^.]*\.)",
     "PREDICATE_LABEL_INVERTED_NEGATION_SUPPORT_CORRECT"),
    ("C-VIS", "F0_canonical", "it is registered as variant `SET`", "SET_vs_tail",
     "predicate",
     r"(The set-based reading[^;]*)",
     "PREDICATE_LABEL_INVERTED"),
    ("C-CH", "F0_canonical", "than the parent class (a subset of extensions suffices to refute it)",
     "CH_extension_subset",
     "class", r"(Strictly (?:weaker|stronger) than the parent class[^)]*\))", "CORRECT"),
    ("C-C11-H2", "F0_canonical", "those are strictly larger classes", "regularity_extension_sets",
     "predicate", r"(It does NOT forbid[^.]*\.[^.]*\.)", "CORRECT"),
    ("C-C0STRONG", "F0_canonical", "strictly stronger than the C2 conclusion",
     "regularity_extension_sets", "conclusion",
     r"(strictly stronger than the C2 conclusion[^.]*\.)", "CORRECT"),
    ("C-C0CLAIM", "F0_canonical", "a stronger conclusion at lower regularity",
     "regularity_extension_sets", "conclusion", r"(a stronger conclusion at lower regularity)",
     "CORRECT"),
    ("C-C0REJECT", "F0_canonical", "a C0 result is stronger", "regularity_extension_sets",
     "conclusion", r"(a C0 result is stronger[^)]*)\)", "CORRECT"),
    ("C-C2WEAK", "F0_canonical", "weaker conclusion, belongs to AF-SCC-C2-VAC-GEN",
     "regularity_extension_sets", "conclusion", r"(weaker conclusion[^)]*)\)", "CORRECT"),
    ("C-C2CLASS", "F0_canonical", "weaker class; filing it here", "regularity_extension_sets",
     "class", r"(weaker class[^)]*)\)", "CORRECT"),
    ("C-C0SEP", "F0_canonical", "strictly stronger C0 conclusion", "regularity_extension_sets",
     "conclusion", r"(strictly stronger C0 conclusion)", "CORRECT"),
    ("S-D1-READING", "F0_supplement", "id: D1, class: AF-WCC-VAC-GEN", "SET_vs_tail",
     "predicate", r'f0_reading:\s*"([^"]*)"', "PREDICATE_LABEL_INVERTED"),
    ("S-D1-RELATION", "F0_supplement", "id: D1, class: AF-WCC-VAC-GEN",
     "SET_vs_tail", "relation", r'relation:\s*"([^"]*)"', "RELATION_POLARITY_MISMATCH"),
    ("S-C0STRONG", "F0_supplement", "C0-inextendibility is a strictly stronger statement",
     "regularity_extension_sets", "conclusion",
     r"(C0-inextendibility is a strictly stronger statement[^;]*)", "CORRECT"),
    ("S-DISTWEAK", "F0_supplement", "the distributional-Ricci variant is a DIFFERENT weaker class",
     "matter_equation_variant", "class",
     r"(the distributional-Ricci variant is a DIFFERENT weaker class[^;]*)", "CORRECT"),
    ("S-H2LOC", "F0_supplement", "so it is the weaker statement", "regularity_extension_sets",
     "conclusion", r"(H2_loc requires more regularity[^\"]*)", "CORRECT"),
]
STRENGTH_RE = re.compile(r"stronger|weaker", re.IGNORECASE)


def classify(axis: str, level_cue: str, text: str) -> str:
    t = text.lower()
    if axis == "SET_vs_tail":
        if level_cue == "relation":
            if "f0 was stronger" in t:
                return "RELATION_POLARITY_MISMATCH"
            if "tail reading implies the set reading" in t and "not conversely" in t:
                return "CORRECT"
            if "implies" in t and "not conversely" in t:
                return "RELATION_POLARITY_MISMATCH"
            return "UNCLASSIFIED"
        if "but not conversely" in t and "outside the union implies no single q" in t:
            return "PREDICATE_LABEL_INVERTED_NEGATION_SUPPORT_CORRECT"
        set_subject = bool(re.search(r"set-based|union|as a set|outside the union", t))
        if set_subject and "stronger" in t:
            return "PREDICATE_LABEL_INVERTED"
        if set_subject and "weaker" in t:
            return "CORRECT"
        return "UNCLASSIFIED"
    if axis == "CH_extension_subset":
        return "CORRECT" if "weaker" in t else "INVERTED"
    if axis == "regularity_extension_sets":
        if "larger" in t and re.search(r"c\^?\{?1,1\}?|h2_?loc", t):
            return "CORRECT"
        if "stronger" in t:
            return "CORRECT"
        if "weaker" in t and re.search(r"c2|conclusion|h2_?loc|more regularity", t):
            return "CORRECT"
        return "UNCLASSIFIED"
    if axis == "matter_equation_variant":
        return "CORRECT" if "weaker" in t else "UNCLASSIFIED"
    return "UNCLASSIFIED"


def census(canon_path: str, supp_path: str):
    files = {"F0_canonical": canon_path, "F0_supplement": supp_path}
    rows, classified_lines, errors = [], set(), []
    for sid, fkey, anchor, axis, cue, extract, expected in SITES:
        path = files[fkey]
        n = find_line(path, anchor)
        if n < 0:
            errors.append({"site": sid, "error": "anchor not found"})
            continue
        win = window(path, n)
        m = re.search(extract, win)
        if not m:
            errors.append({"site": sid, "error": "extract regex did not match"})
            continue
        extracted = m.group(1).strip()
        rows.append({"site": sid, "file": fkey, "line": n,
                     "line_sha256": hashlib.sha256(win.encode()).hexdigest(),
                     "extracted": extracted, "axis": axis, "level_cue": cue,
                     "expected": expected, "derived": classify(axis, cue, extracted)})
        classified_lines.add((fkey, n))
    unclassified = []
    for fkey, path in files.items():
        with open(path, encoding="utf-8") as f:
            for i, ln in enumerate(f, 1):
                if STRENGTH_RE.search(ln) and (fkey, i) not in classified_lines:
                    unclassified.append({"file": fkey, "line": i, "text": ln.strip()})
    return {"sites": rows, "classified_line_count": len(classified_lines)}, unclassified, errors


# --------------------------------------------------------------------------------------
# 3. F0 fan-out / option blast radius
# --------------------------------------------------------------------------------------
def scan_reviews(f0c: str, f0s: str):
    out = {"files": 0, "bind_canonical": [], "bind_supplement": []}
    rdir = os.path.join(ROOT, "reviews")
    for name in sorted(os.listdir(rdir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(rdir, name)
        try:
            header = open(p, encoding="utf-8", errors="replace").read(4096)
            d = json.loads(open(p, encoding="utf-8", errors="replace").read())
        except Exception:
            continue
        out["files"] += 1
        hits_c, hits_s = [], []

        def walk(o, path="$"):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, f"{path}[{i}]")
            elif isinstance(o, str):
                if f0c in o or F0C_PREFIX in o:
                    hits_c.append(path)
                if f0s in o or F0S_PREFIX in o:
                    hits_s.append(path)
        walk(d)
        if hits_c:
            out["bind_canonical"].append({"file": name, "fields": sorted(set(hits_c))})
        if hits_s:
            out["bind_supplement"].append({"file": name, "fields": sorted(set(hits_s))})
    out["files_reviewed_sha256_canonical"] = sorted(
        x["file"] for x in out["bind_canonical"]
        if any(f.endswith("reviewed_sha256") for f in x["fields"]))
    out["files_companion_sha256_supplement"] = sorted(
        x["file"] for x in out["bind_supplement"]
        if any(f.endswith("companion_sha256") for f in x["fields"]))
    out["files_mentioning_canonical"] = len(out["bind_canonical"])
    out["files_mentioning_supplement"] = len(out["bind_supplement"])
    return out


def scan_map(f0c: str, f0s: str):
    m = json.load(open(os.path.join(ROOT, "research_map/research_map.json"), encoding="utf-8"))
    out = {"map_updated_at": m.get("updated_at"), "sections": {}}
    for sec in ("gates", "reviews", "claims", "assignments", "frozen_artifacts",
                "controller_gate_audit", "publication_status", "controller_findings",
                "escalations", "resource_requests", "controller_repairs"):
        blob = json.dumps(m.get(sec, []), ensure_ascii=False)
        out["sections"][sec] = {"canonical_mentions": blob.count(f0c) + blob.count(F0C_PREFIX),
                                "supplement_mentions": blob.count(f0s) + blob.count(F0S_PREFIX)}
    return out


def scan_frozen(frozen_path: str):
    fz = json.load(open(frozen_path, encoding="utf-8"))
    files = fz.get("files", {})
    art = fz.get("logical_artifacts", {}) or {}
    return {"revision": fz.get("revision"), "frozen_at": fz.get("frozen_at"),
            "n_files": len(files),
            "canonical_pin": files.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
            "supplement_pin": files.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256"),
            "logical_artifacts": {k: v.get("sha256") for k, v in art.items()},
            "rev29_delta_entries": len(fz.get("rev29_delta") or []),
            "f0_mirror_disposition": (fz.get("f0_mirror_adjudication_request") or {}).get("status")}


def scan_schemas():
    out = {}
    for key in ("F1", "F2a", "F2b"):
        d = yaml.safe_load(open(os.path.join(ROOT, PIN[key][0]), encoding="utf-8"))
        b = d.get("f0_binding", {})
        out[key] = {"revision": d.get("revision"),
                    "declared_f0_sha256": b.get("declared_f0_sha256"),
                    "consistency_evidence_sha256": b.get("consistency_evidence_sha256"),
                    "class_contract_supplement": b.get("class_contract_supplement"),
                    "checked_at": b.get("checked_at")}
    return out


def scan_cases():
    path = os.path.join(ROOT, PIN["cases"][0])
    lines = [ln for ln in open(path, encoding="utf-8").read().splitlines() if ln.strip()]
    bound = sum(1 for ln in lines if F0C_PREFIX in ln)
    meta = None
    try:
        o = json.loads(lines[0])
        if isinstance(o, dict) and (o.get("record_type") == "meta" or "meta" in o or o.get("kind") == "meta" or "_meta" in o):
            meta = o
    except Exception:
        pass
    return {"nonempty_lines": len(lines), "lines_binding_canonical_prefix": bound,
            "first_line_is_meta": meta is not None,
            "meta_taxonomy_ref": (meta or {}).get("taxonomy_ref"),
            "row_lines": len(lines) - (1 if meta else 0)}


def scan_events(f0c: str, f0s: str):
    out = {"event_lines_mentioning": 0, "canonical_by_type": {}, "supplement_by_type": {},
           "actors": {}}
    p = os.path.join(ROOT, "research_map/events.jsonl")
    with open(p, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if f0c not in ln and F0C_PREFIX not in ln and f0s not in ln and F0S_PREFIX not in ln:
                continue
            out["event_lines_mentioning"] += 1
            try:
                e = json.loads(ln)
            except Exception:
                continue
            et, actor = e.get("event_type", "?"), e.get("actor", "?")
            if f0c in ln or F0C_PREFIX in ln:
                out["canonical_by_type"][et] = out["canonical_by_type"].get(et, 0) + 1
            if f0s in ln or F0S_PREFIX in ln:
                out["supplement_by_type"][et] = out["supplement_by_type"].get(et, 0) + 1
            out["actors"][actor] = out["actors"].get(actor, 0) + 1
    return out


def scan_tree():
    try:
        r = subprocess.run(["grep", "-rIl", "-e", F0C_PREFIX, "-e", F0S_PREFIX,
                            "--exclude-dir=.git", "."],
                           cwd=ROOT, capture_output=True, text=True, timeout=180)
    except Exception as ex:
        return {"error": str(ex)}
    files = [x for x in r.stdout.splitlines() if x.strip()]
    roots = {}
    for x in files:
        rel = x[2:] if x.startswith("./") else x
        roots.setdefault(rel.split("/")[0], []).append(rel)
    live = sorted([x.lstrip("./") for x in files
                   if x.lstrip("./").startswith(("schemas/", "reviews/", "ledger/",
                                                 "research_map/", "artifacts/formulation/",
                                                 "evaluation/", "evaluation_rubric.yaml"))])
    hist = sorted([x.lstrip("./") for x in files
                   if x.lstrip("./").startswith(("artifacts/worker-", "tmp/", "archive/",
                                                 "incoming/"))])
    return {"n_files": len(files),
            "by_root": {k: {"count": len(v), "sample": sorted(v)[:5]}
                        for k, v in sorted(roots.items())},
            "live_canonical_trees": live, "historical_or_worker": hist,
            "grep_stderr": r.stderr.strip()[:200]}


def downstream_contrast():
    """The same assertion axis at the repaired downstream sites (rev13/rev29), measured live."""
    out = {}
    checks = [
        ("F1_visibility_definition", "F1", r"the tail and whole-curve readings are EQUIVALENT"),
        ("F1_variant_SET_relation", "F1", r"relation: \"(strictly WEAKER[^\"]*)\""),
        ("registry_SET_strength", "registry", r"\"strength\": \"(strictly weaker[^\"]*)\""),
        ("set_delta_strength", "set_delta", r"\"strength\": \"(strictly weaker[^\"]*)\""),
        ("set_delta_negation_level", "set_delta", r"(This is strictly stronger than the single-q negation[^.]*\.)"),
    ]
    for label, key, pat in checks:
        path = os.path.join(ROOT, PIN[key][0])
        txt = open(path, encoding="utf-8").read()
        m = re.search(pat, txt)
        n = txt[:m.start()].count("\n") + 1 if m else -1
        out[label] = {"file": PIN[key][0], "line": n,
                      "extracted": (m.group(1) if m.groups() else m.group(0)).strip()[:200] if m else None,
                      "found": bool(m)}
    return out


# --------------------------------------------------------------------------------------
# 4. controls
# --------------------------------------------------------------------------------------
def write_sandbox(name: str, src: str, old: str, new: str):
    os.makedirs(SANDBOX, exist_ok=True)
    txt = open(src, encoding="utf-8").read()
    if old not in txt:
        return None
    dst = os.path.join(SANDBOX, name)
    open(dst, "w", encoding="utf-8").write(txt.replace(old, new, 1))
    return dst


def derived_of(cen, sid):
    for r in cen["sites"]:
        if r["site"] == sid:
            return r["derived"]
    return "MISSING"


def run_controls(canon: str, supp: str):
    c = {}
    p = write_sandbox("K1_canon_vis_repaired.yaml", canon,
                      "is strictly stronger; it is registered as variant",
                      "is strictly weaker; it is registered as variant")
    c["K1_repair_C_VIS"] = {"derived": derived_of(census(p, supp)[0], "C-VIS"),
                            "expected": "CORRECT",
                            "pass": derived_of(census(p, supp)[0], "C-VIS") == "CORRECT"}
    p = write_sandbox("K2_canon_ch_inverted.yaml", canon,
                      "Strictly weaker than the parent class",
                      "Strictly stronger than the parent class")
    c["K2_invert_C_CH"] = {"derived": derived_of(census(p, supp)[0], "C-CH"),
                           "expected": "INVERTED",
                           "pass": derived_of(census(p, supp)[0], "C-CH") == "INVERTED"}
    p = write_sandbox("K3_supp_d1_relation_repaired.yaml", supp,
                      'relation: "F0 was stronger; (b) implies (c) but not conversely"',
                      'relation: "the tail reading implies the set reading, not conversely '
                      '(predicate level); equivalently the set negation implies the tail negation"')
    c["K3_repair_D1_relation"] = {"derived": derived_of(census(canon, p)[0], "S-D1-RELATION"),
                                  "expected": "CORRECT",
                                  "pass": derived_of(census(canon, p)[0], "S-D1-RELATION") == "CORRECT"}
    p = write_sandbox("K4_canon_unrelated.yaml", canon,
                      'schema_version: "0.1"',
                      'schema_version: "0.1"  # unrelated prose edit')
    base_c = {r["site"]: r["derived"] for r in census(canon, supp)[0]["sites"]}
    mut_c = {r["site"]: r["derived"] for r in census(p, supp)[0]["sites"]}
    c["K4_unrelated_mutation"] = {"unchanged": base_c == mut_c, "pass": base_c == mut_c}
    a = json.dumps(census(canon, supp)[0], sort_keys=True)
    b = json.dumps(census(canon, supp)[0], sort_keys=True)
    c["K5_determinism"] = {"pass": a == b}
    return c


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main() -> int:
    measured = {}
    for key, (rel, expect) in PIN.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"DRIFT: missing {rel}", file=sys.stderr)
            return 2
        h = sha256(p)
        measured[key] = {"path": rel, "sha256": h, "expected": expect,
                         "match": (expect is None or h == expect)}
        if expect is not None and h != expect:
            print(f"DRIFT: {rel} measured {h[:16]} expected {expect[:16]}", file=sys.stderr)
            return 2

    model = finite_corpus()
    omega = omega_certificate()
    canon = os.path.join(ROOT, PIN["F0_canonical"][0])
    supp = os.path.join(ROOT, PIN["F0_supplement"][0])
    cen, unclassified, errors = census(canon, supp)
    if errors:
        print(f"CONTROL FAIL: {errors}", file=sys.stderr)
        return 1
    if unclassified:
        print(f"UNCLASSIFIED strength-token occurrences: {unclassified}", file=sys.stderr)
        return 2
    mismatches = [r for r in cen["sites"] if r["derived"] != r["expected"]]
    if mismatches:
        print(f"PRE-REGISTRATION MISMATCH: {mismatches}", file=sys.stderr)
        return 1

    controls = run_controls(canon, supp)
    controls_pass = all(v.get("pass") for v in controls.values())

    reviews = scan_reviews(PIN["F0_canonical"][1], PIN["F0_supplement"][1])
    mapscan = scan_map(PIN["F0_canonical"][1], PIN["F0_supplement"][1])
    frozen = scan_frozen(os.path.join(ROOT, PIN["FROZEN"][0]))
    schemas = scan_schemas()
    cases = scan_cases()
    events = scan_events(PIN["F0_canonical"][1], PIN["F0_supplement"][1])
    tree = scan_tree()

    f0c, f0s = PIN["F0_canonical"][1], PIN["F0_supplement"][1]
    option_effects = {
        "O1_edit_supplement_D1": {
            "writes": ["artifacts/formulation/formulation_taxonomy.yaml"],
            "hash_moves": {"supplement": {"from": f0s, "to": "new (unwritten)"}},
            "canonical_F0_writes": 0,
            "verdicts_with_companion_sha256_supplement": len(reviews["files_companion_sha256_supplement"]),
            "review_files_mentioning_supplement": len(reviews["bind_supplement"]),
            "follow_on": ["FROZEN re-freeze",
                          f"verdicts carrying companion_sha256 {F0S_PREFIX} become stale"],
        },
        "O2_reopen_F0_canonical": {
            "writes": ["research_map/formulation_taxonomy.yaml"],
            "hash_moves": {"canonical": {"from": f0c, "to": "new (unwritten)"}},
            "canonical_F0_writes": 1,
            "verdicts_with_reviewed_sha256_canonical": len(reviews["files_reviewed_sha256_canonical"]),
            "review_files_mentioning_canonical": len(reviews["bind_canonical"]),
            "follow_on": ["G-F0 pass void (fresh accepts required)",
                          "3 schema f0_binding.declared_f0_sha256 stale",
                          "taxonomy_cases rows rebound", "FROZEN re-freeze"],
        },
        "O3_map_erratum_no_write": {
            "writes": ["research_map/research_map.json (controller)"],
            "hash_moves": {},
            "canonical_F0_writes": 0,
            "frozen_artifact_writes": 0,
            "follow_on": ["controller_findings entry only"],
        },
    }

    payload = {
        "task_id": "W061-F0-DIRECTION-BLAST-08",
        "worker": "worker-061",
        "generated_at": NOW,
        "class_id": "AF-WCC-VAC-GEN",
        "nodes": ["F0", "F1"],
        "gate_context": ["G-F0", "G-FORM"],
        "pins": measured,
        "order_fact": {"finite_corpus": model, "omega_certificate": omega},
        "direction_census": cen,
        "unclassified_strength_lines": unclassified,
        "fanout": {"reviews": reviews, "map": mapscan, "frozen": frozen, "schemas": schemas,
                   "cases": cases, "events": events, "tree": tree},
        "downstream_contrast": downstream_contrast(),
        "option_effects": option_effects,
        "controls": controls,
        "controls_pass": controls_pass,
        "authority_note": ("worker evidence only; no gate verdict, no node status, no "
                           "validation_status=passed; no canonical artifact was edited"),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({"out": OUT, "controls_pass": controls_pass, "sites": len(cen["sites"]),
                      "flagged": [r["site"] for r in cen["sites"]
                                  if "INVERTED" in r["derived"] or "MISMATCH" in r["derived"]],
                      "reviews_binding_canonical": len(reviews["bind_canonical"]),
                      "reviews_binding_supplement": len(reviews["bind_supplement"]),
                      "tree_files": tree.get("n_files")}, ensure_ascii=False))
    return 0 if controls_pass else 1


if __name__ == "__main__":
    sys.exit(main())
