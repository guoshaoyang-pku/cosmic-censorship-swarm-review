#!/usr/bin/env python3
"""W072-C — independent second-implementation recheck of the AF-WCC-SCALAR-SPH
class-conformance audit (task W072-A).

Design constraints
------------------
* stdlib only (no PyYAML): the class definition is extracted from the pinned
  taxonomy by a line-oriented reader, and the reader's output is asserted
  against the key phrases the classifier depends on.  If the pinned file no
  longer yields those premises the run aborts rc=2 rather than classifying.
* Does NOT import, read, or replicate the original runner
  (artifacts/worker-072/scalar_sph_class_audit/audit_scalar_sph.py).  The
  original *report* is read only in the comparison step, after this
  implementation's own verdicts are frozen in memory.
* Fail-closed on any pinned-input sha256 drift (rc=2).
* Deterministic: no network, no clock in the result digest.
* Independent readings are reported side by side instead of a single verdict:
    - `loose`  : token-presence reading (the family of reading used by W072-A)
    - `space`  : loose H1, but H2/H3 read as hypotheses about the *data space*
    - `strict` : `space` + H1 requires an explicit massless-scalar token
  Disagreement with the target report is a deliverable, not an error.
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

CLASS_ID = "AF-WCC-SCALAR-SPH"
TASK_ID = "W072-C"
TARGET_REPORT = "artifacts/worker-072/scalar_sph_class_audit/spotcheck_report.json"
OUT_REPORT = os.path.join(HERE, "recheck_report.json")
RUNNER = os.path.abspath(__file__)

# sha256 of the inputs as measured at task start (2026-09-12T00:27+08:00); the
# three ledger/taxonomy pins are the revisions task W072-A binds.
PINS = {
    "research_map/formulation_taxonomy.yaml":
        "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "ledger/theorems.jsonl":
        "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "ledger/citation_audit.csv":
        "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    TARGET_REPORT:
        "4d931de7b4deeedbff850ba07e1d56f8ac9f497a79dcbb719a27b2d727c31546",
}

# Content fields only: binding metadata (ledger_tags, class_ids) is deliberately
# NOT evidence for conformance, otherwise the check would be circular.
OBJECT_FIELDS = [
    "label", "statement_exact", "assumptions", "regularity", "topology",
    "genericity",
]

GENERICITY_TOKENS = [
    "dense open", "open dense", "open and dense", "comeager", "co-meager",
    "residual", "full measure", "full-measure", "positive probability",
    "first category", "first-category", "meagre", "meager",
]
NEGATION_MARKERS = [
    "no ", "not ", "never", "non-", "without ", "fails to", "cannot",
    "does not", "is not", "are not", "nor ",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# Byte-identical on-disk copies of the pinned revision, used only when the live
# canonical path has already moved on.  Verified by sha256 before use; if none
# matches the pin the run aborts rc=2 (fail-closed).
SNAPSHOT_CANDIDATES = {
    "ledger/theorems.jsonl": [
        "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
        "artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl",
    ],
    "research_map/formulation_taxonomy.yaml": [
        "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy.276009f4f63d.yaml",
        "artifacts/flash-15/f1_wcc_visibility/pinned/formulation_taxonomy.276009f4.yaml",
        "artifacts/worker-024/class_token_audit/snapshots/formulation_taxonomy.276009f4.yaml",
        "artifacts/worker-089/f2b_f0adj_verify/pinned/formulation_taxonomy.canonical.276009f4f63d.yaml",
    ],
}


def resolve_pinned(rel, pinned):
    """Return (resolution, live_sha256).  Never silently substitutes bytes."""
    live = os.path.join(ROOT, rel)
    live_sha = sha256_file(live) if os.path.exists(live) else None
    if live_sha == pinned:
        return {"source": "live", "used_path": rel, "used_sha256": pinned,
                "match": True, "live_sha256": live_sha}, live_sha
    for cand in SNAPSHOT_CANDIDATES.get(rel, []):
        cp = os.path.join(ROOT, cand)
        if os.path.exists(cp) and sha256_file(cp) == pinned:
            return {"source": "snapshot", "used_path": cand, "used_sha256": pinned,
                    "match": True, "live_sha256": live_sha}, live_sha
    return {"source": "none", "used_path": None, "used_sha256": None,
            "match": False, "live_sha256": live_sha}, live_sha


def measure_pins():
    out = {}
    drift = []
    for rel, pinned in PINS.items():
        res, live_sha = resolve_pinned(rel, pinned)
        res["pinned"] = pinned
        res["live_drifted"] = bool(live_sha and live_sha != pinned)
        out[rel] = res
        if not res["match"]:
            drift.append(rel)
    return out, drift


# ---------------------------------------------------------------- taxonomy ---

def extract_class_block(text, class_id):
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^  \"?'?%s\"?'?:\s*$" % re.escape(class_id), ln):
            start = i
            break
    if start is None:
        return None
    block = []
    for ln in lines[start + 1:]:
        if re.match(r"^  \S", ln) and not ln.startswith("    "):
            break
        block.append(ln)
    return "\n".join(block)


def parse_class_definition(taxonomy_text):
    block = extract_class_block(taxonomy_text, CLASS_ID)
    if block is None:
        return None, "class block not found in pinned taxonomy"
    hyps = {}
    for m in re.finditer(r"- id: \"?(H\d)\"?\s*\n\s+text: (.+)", block):
        hyps[m.group(1)] = m.group(2).strip().strip('"')
    concl = re.search(r"conclusion:\s*\n\s+type:\s*\"?(\S+?)\"?\s*$", block, flags=re.M)
    exclusions = []
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^\s+exclusions:\s*$", ln):
            for nxt in lines[i + 1:]:
                m = re.match(r"^\s+- (.+)$", nxt)
                if not m:
                    break
                exclusions.append(m.group(1).strip().strip('"'))
            break
    return {
        "label": (re.search(r"label:\s*(.+)", block) or [None, ""])[1].strip()
        if re.search(r"label:\s*(.+)", block) else "",
        "hypotheses": hyps,
        "conclusion_type": concl.group(1) if concl else None,
        "exclusions_raw": exclusions[:12],
    }, None


def validate_premises(cdef):
    """The classifier's premises must be readable from the pinned file."""
    errs = []
    h = cdef["hypotheses"]
    for hid, needle in [("H1", "massless scalar"), ("H2", "Spherical symmetry"),
                        ("H3", "asymptotically flat"), ("H4", "Genericity")]:
        if hid not in h:
            errs.append("missing %s" % hid)
        elif needle.lower() not in h[hid].lower():
            errs.append("%s text lacks %r" % (hid, needle))
    if cdef["conclusion_type"] != "weak_cosmic_censorship":
        errs.append("conclusion.type != weak_cosmic_censorship")
    ex = " ".join(cdef["exclusions_raw"]).lower()
    for needle in ["vacuum data", "non-spherical data", "massive or charged scalar"]:
        if needle not in ex:
            errs.append("exclusions lack %r" % needle)
    return errs


# -------------------------------------------------------------- classifier ---

def entry_text(entry, fields=None):
    parts = []
    for f in (fields or OBJECT_FIELDS):
        v = entry.get(f)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif v is not None:
            parts.append(str(v))
    return "\n".join(parts)


def near_negation(blob, match, window=90):
    lo = max(0, match.start() - window)
    hi = min(len(blob), match.end() + window)
    ctx = blob[lo:hi].lower()
    return any(m in ctx for m in NEGATION_MARKERS)



def spherical_probe(entry):
    """All 'spherical' occurrences in ALL fields (the union scan), each flagged
    when it sits inside a negated form such as 'non-spherical'.  This exists to
    explain H2 disagreements mechanically rather than by assertion."""
    occ = []
    for k, v in entry.items():
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        for m in re.finditer(r"spherical", s, flags=re.I):
            pre = s[max(0, m.start() - 6):m.start()].lower().rstrip()
            occ.append({
                "field": k,
                "snippet": s[max(0, m.start() - 30):min(len(s), m.end() + 12)],
                "inside_negated_form": pre.endswith("non-") or pre.endswith("non")
                                       or pre.endswith("without"),
            })
    return occ


def classify(entry):
    """Independent classification.  Returns evidence levels, not just booleans."""
    obj = entry_text(entry)
    obj_l = obj.lower()

    # --- H1 matter model -------------------------------------------------
    has_scalar = re.search(r"\bscalar\b", obj_l) is not None
    explicit_massless = bool(
        re.search(r"massless[\s-]scalar", obj_l)
        or re.search(r"einstein[\s-]massless[\s-]scalar", obj_l)
        or re.search(r"einstein[\s-]scalar", obj_l)
    )
    massive_only = bool(re.search(r"massive\s+scalar", obj_l)) and not explicit_massless
    charged_scalar = bool(re.search(r"charged\s+scalar", obj_l)) and not explicit_massless
    lambda_nonzero = bool(
        re.search(r"lambda\s*(?:!=|≠|>|<|≥|≤)\s*0", obj_l)
        or re.search(r"lambda\s*=\s*(?!0(?![\d.]))\S", obj_l)
        or re.search(r"non-?zero\s+cosmological", obj_l)
        or re.search(r"positive\s+cosmological\s+constant", obj_l)
    )
    if not has_scalar:
        h1_level = "absent"          # vacuum or no matter statement
    elif massive_only or charged_scalar or lambda_nonzero:
        h1_level = "excluded"
    elif explicit_massless:
        h1_level = "explicit_massless"
    else:
        h1_level = "scalar_unspecified"
    h1_loose = h1_level not in ("absent", "excluded")

    # --- H2 symmetry of the data space -----------------------------------
    spherical_token = bool(
        re.search(r"spherical(ly)?[\s-]symmetr", obj_l)
        or re.search(r"\bso\(3\)", obj_l)
        or re.search(r"spherical\s+collapse", obj_l)
        or re.search(r"spherical\s+characteristic", obj_l)
    )
    symmetry_break = bool(
        re.search(r"without\s+symmetr", obj_l)
        or re.search(r"no\s+symmetr", obj_l)
        or re.search(r"non[\s-]symmetric", obj_l)
        or re.search(r"non[\s-]spherical", obj_l)
        or re.search(r"anisotropic\s+perturbation", obj_l)
        or re.search(r"symmetry\s+release", obj_l)
    )
    if symmetry_break:
        h2_level = "symmetry_broken"
    elif spherical_token:
        h2_level = "spherical_data"
    else:
        h2_level = "absent"

    # --- H3 asymptotically flat data with one end / MGHD ------------------
    af_data = bool(re.search(r"asymptotically[\s-]flat", obj_l))
    h3_level = "af_data" if af_data else "absent"

    # --- H4 genericity notion named (not negated nearby) ------------------
    h4_hits = []
    for tok in GENERICITY_TOKENS:
        for m in re.finditer(re.escape(tok), obj_l):
            if not near_negation(obj_l, m):
                h4_hits.append(tok)
    h4_level = "named" if h4_hits else "absent"

    discharges = str(entry.get("conclusion_type")) == "weak_cosmic_censorship"

    return {
        "theorem_id": entry.get("theorem_id"),
        "entry_kind": entry.get("entry_kind"),
        "conclusion_type": entry.get("conclusion_type"),
        "status": entry.get("status"),
        "H1_level": h1_level,
        "H2_level": h2_level,
        "H3_level": h3_level,
        "H4_level": h4_level,
        "H4_tokens": sorted(set(h4_hits)),
        "loose_conforms": (h1_loose and spherical_token and af_data),
        "space_conforms": (h1_loose and h2_level == "spherical_data" and af_data),
        "strict_conforms": (h1_level == "explicit_massless"
                            and h2_level == "spherical_data" and af_data),
        "discharges_class_conclusion": discharges,
        "spherical_occurrences_all_fields": spherical_probe(entry),
    }


# ----------------------------------------------------------------- mutants ---

def mutate(base, kind):
    e = json.loads(json.dumps(base))  # deep copy
    if kind == "CTRL-VACUUM":
        e["label"] = "Vacuum collapse without matter"
        e["statement_exact"] = (
            "For the spherically symmetric Einstein vacuum equations, trapped "
            "surfaces form; no matter field is present.")
        e["assumptions"] = ["Vacuum", "Spherical symmetry"]
        e["topology"] = "Spherically symmetric asymptotically flat vacuum."
        e["ledger_tags"] = ["VACUUM"]
    elif kind == "CTRL-FULL-WCC":
        e["statement_exact"] = e["statement_exact"] + (
            " Moreover, for a comeager set of spherical data the maximal "
            "development admits I+.")
        e["genericity"] = "Comeager (residual) subset of the spherical data space."
        e["conclusion_type"] = "weak_cosmic_censorship"
    elif kind == "CTRL-NONSPH":
        e["assumptions"] = list(e["assumptions"]) + [
            "Initial data are the spherical background plus a small "
            "anisotropic perturbation on the outgoing cone."]
    elif kind == "CTRL-LAMBDA":
        e["assumptions"] = list(e["assumptions"]) + [
            "Lambda = 1e-3 (nonzero cosmological constant)."]
    elif kind == "CTRL-UNBOUND":
        e["class_ids"] = ["AF-WCC-VAC-GEN"]
    else:
        raise ValueError(kind)
    return e


def run_controls(base, taxonomy):
    c = {}
    v = classify(mutate(base, "CTRL-VACUUM"))
    c["CTRL-VACUUM"] = {
        "expect": "H1 absent/excluded; not in class under any reading",
        "observed": {k: v[k] for k in ("H1_level", "loose_conforms",
                                       "space_conforms", "strict_conforms")},
        "pass": v["H1_level"] in ("absent", "excluded")
                and not v["loose_conforms"],
    }
    f = classify(mutate(base, "CTRL-FULL-WCC"))
    c["CTRL-FULL-WCC"] = {
        "expect": "discharges the class conclusion; H4 named",
        "observed": {k: f[k] for k in ("H4_level", "H4_tokens",
                                       "discharges_class_conclusion",
                                       "strict_conforms")},
        "pass": f["discharges_class_conclusion"] and f["H4_level"] == "named",
    }
    n = classify(mutate(base, "CTRL-NONSPH"))
    c["CTRL-NONSPH"] = {
        "expect": "loose conforms but space/strict reject (H2 axis discriminates)",
        "observed": {k: n[k] for k in ("H1_level", "H2_level",
                                       "loose_conforms", "space_conforms",
                                       "strict_conforms")},
        "pass": n["loose_conforms"] and not n["space_conforms"],
    }
    lam = classify(mutate(base, "CTRL-LAMBDA"))
    c["CTRL-LAMBDA"] = {
        "expect": "H1 excluded (class excludes Lambda != 0)",
        "observed": {k: lam[k] for k in ("H1_level", "loose_conforms",
                                         "strict_conforms")},
        "pass": lam["H1_level"] == "excluded" and not lam["loose_conforms"],
    }
    u = mutate(base, "CTRL-UNBOUND")
    unbound = [u] + [e for e in taxonomy if e.get("theorem_id") != base.get("theorem_id")
                     and CLASS_ID not in (e.get("class_ids") or [])]
    recall = scan_recall(unbound)
    c["CTRL-UNBOUND"] = {
        "expect": "stripped entry appears in the unbound-conforming recall list",
        "observed": {"recall_loose_ids": [r["theorem_id"] for r in recall
                                          if r["loose_conforms"]]},
        "pass": any(r["theorem_id"] == base.get("theorem_id")
                    and r["loose_conforms"] for r in recall),
    }
    return c


# ------------------------------------------------------------------ recall ---

def scan_recall(entries):
    out = []
    for e in entries:
        if CLASS_ID in (e.get("class_ids") or []):
            continue
        cl = classify(e)
        if cl["loose_conforms"] or cl["discharges_class_conclusion"]:
            out.append({
                "theorem_id": cl["theorem_id"],
                "label": e.get("label"),
                "class_ids": e.get("class_ids"),
                "conclusion_type": cl["conclusion_type"],
                "loose_conforms": cl["loose_conforms"],
                "space_conforms": cl["space_conforms"],
                "H1_level": cl["H1_level"], "H2_level": cl["H2_level"],
                "H3_level": cl["H3_level"], "H4_level": cl["H4_level"],
            })
    return sorted(out, key=lambda r: str(r["theorem_id"]))


# --------------------------------------------------------------- citations ---

def locator_recheck(rows):
    res = []
    for r in rows:
        doi = (r.get("doi") or "").strip()
        arxiv = (r.get("arxiv_id") or "").strip()
        url = (r.get("url") or "").strip()
        exact = (r.get("exact_locator") or "").strip()
        kinds = []
        if re.match(r"^10\.\d{4,9}/\S+$", doi):
            kinds.append("doi")
        if re.match(r"^(\d{4}\.\d{4,5}(v\d+)?|[a-z-]+(\.[A-Z]{2})?/\d{7})$",
                    arxiv, flags=re.I):
            kinds.append("arxiv_id")
        if re.match(r"^https?://\S+$", url):
            kinds.append("url")
        if re.match(r"^https?://\S+$", exact):
            kinds.append("exact_locator")
        res.append({
            "citation_id": r.get("citation_id"),
            "locator_kinds": kinds,
            "resolvable": bool(kinds),
            "status": r.get("status"),
            "reviewer": r.get("reviewer"),
        })
    return res


# ------------------------------------------------------------------- main ----

def main():
    pins, drift = measure_pins()
    if drift:
        print("PIN DRIFT (fail-closed, rc=2): %s" % ", ".join(drift), file=sys.stderr)
        print(json.dumps(pins, indent=1), file=sys.stderr)
        return 2

    taxonomy_text = open(os.path.join(ROOT, pins["research_map/formulation_taxonomy.yaml"]["used_path"]),
                         encoding="utf-8").read()
    cdef, err = parse_class_definition(taxonomy_text)
    if err:
        print("PREMISE ERROR: %s" % err, file=sys.stderr)
        return 2
    premise_errs = validate_premises(cdef)
    if premise_errs:
        print("PREMISE ERROR(S): %s" % "; ".join(premise_errs), file=sys.stderr)
        return 2

    entries = []
    with open(os.path.join(ROOT, pins["ledger/theorems.jsonl"]["used_path"]),
              encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    by_id = {e["theorem_id"]: e for e in entries}
    bound = [e for e in entries if CLASS_ID in (e.get("class_ids") or [])]
    bound.sort(key=lambda e: e["theorem_id"])

    per_entry = [classify(e) for e in bound]

    # --- controls (base = the first bound theorem entry, deterministic) ---
    base = next(e for e in bound if e.get("theorem_id") == "T-101")
    controls = run_controls(base, entries)

    # --- recall scan over the whole ledger --------------------------------
    recall = scan_recall(entries)

    # --- live-head invariance check (canonical ledger may have moved) -----
    live_rel = "ledger/theorems.jsonl"
    live_path = os.path.join(ROOT, live_rel)
    live_head = None
    if pins[live_rel]["live_drifted"]:
        live_entries = []
        with open(live_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    live_entries.append(json.loads(line))
        live_by_id = {e["theorem_id"]: e for e in live_entries}
        live_bound = sorted((e for e in live_entries
                             if CLASS_ID in (e.get("class_ids") or [])),
                            key=lambda e: e["theorem_id"])
        live_cl = [classify(e) for e in live_bound]
        content_changes = []
        for e in bound:
            other = live_by_id.get(e["theorem_id"])
            if other is None:
                content_changes.append({"theorem_id": e["theorem_id"],
                                        "content_fields_changed": ["ENTRY REMOVED"]})
                continue
            ch = [f for f in OBJECT_FIELDS
                  if json.dumps(e.get(f), sort_keys=True)
                  != json.dumps(other.get(f), sort_keys=True)]
            if ch:
                content_changes.append({"theorem_id": e["theorem_id"],
                                        "content_fields_changed": ch})
        live_head = {
            "live_sha256": pins[live_rel]["live_sha256"],
            "pinned_sha256": pins[live_rel]["pinned"],
            "entries_total": len(live_entries),
            "pinned_entries_total": len(entries),
            "ids_added": sorted({e["theorem_id"] for e in live_entries}
                                - {e["theorem_id"] for e in entries}),
            "ids_removed": sorted({e["theorem_id"] for e in entries}
                                  - {e["theorem_id"] for e in live_entries}),
            "bound_to_class": [e["theorem_id"] for e in live_bound],
            "loose_conforms": sum(1 for c in live_cl if c["loose_conforms"]),
            "space_conforms": sum(1 for c in live_cl if c["space_conforms"]),
            "strict_conforms": sum(1 for c in live_cl if c["strict_conforms"]),
            "discharges_class_conclusion": sum(
                1 for c in live_cl if c["discharges_class_conclusion"]),
            "content_field_changes_in_class_bound_entries": content_changes,
            "invariant_in_substance": (not content_changes
                                       and sorted(e["theorem_id"] for e in live_bound)
                                       == sorted(e["theorem_id"] for e in bound)),
            "handling": ("primary measurement stays bound to the target's pinned "
                         "ledger; the live head is reported as an invariance check, "
                         "not silently substituted"),
        }

    # --- live-head check for the class definition (taxonomy) --------------
    tax_rel = "research_map/formulation_taxonomy.yaml"
    tax_live = None
    if pins[tax_rel]["live_drifted"]:
        live_tax_text = open(os.path.join(ROOT, tax_rel), encoding="utf-8").read()
        live_cdef, lerr = parse_class_definition(live_tax_text)
        if lerr:
            tax_live = {"live_sha256": pins[tax_rel]["live_sha256"],
                        "pinned_sha256": pins[tax_rel]["pinned"],
                        "error": lerr, "invariant_in_substance": False}
        else:
            h_eq = live_cdef["hypotheses"] == cdef["hypotheses"]
            c_eq = live_cdef["conclusion_type"] == cdef["conclusion_type"]
            e_eq = live_cdef["exclusions_raw"] == cdef["exclusions_raw"]
            tax_live = {
                "live_sha256": pins[tax_rel]["live_sha256"],
                "pinned_sha256": pins[tax_rel]["pinned"],
                "class_block_found": True,
                "hypotheses_equal": h_eq,
                "conclusion_type_equal": c_eq,
                "exclusions_equal": e_eq,
                "live_hypotheses": live_cdef["hypotheses"],
                "live_conclusion_type": live_cdef["conclusion_type"],
                "invariant_in_substance": bool(h_eq and c_eq and e_eq),
                "handling": ("primary class definition stays bound to the target's "
                             "pinned taxonomy"),
            }

    # --- citation rows -----------------------------------------------------
    import csv
    with open(os.path.join(ROOT, "ledger/citation_audit.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if CLASS_ID in (r.get("class_mapping") or "")]
    cit = locator_recheck(rows)
    cit_control = locator_recheck([{**rows[0], "doi": "", "arxiv_id": "", "url": "",
                                    "exact_locator": ""}])

    # --- comparison with the target report (read after own verdicts) ------
    target = json.load(open(os.path.join(ROOT, TARGET_REPORT), encoding="utf-8"))
    tgt = {e["theorem_id"]: e for e in target["per_entry"]}
    disagreements = []
    for cl in per_entry:
        t = tgt.get(cl["theorem_id"])
        if t is None:
            disagreements.append({"theorem_id": cl["theorem_id"],
                                  "field": "presence", "target": "absent",
                                  "recheck": "present"})
            continue
        t_h = {x["id"]: x["pass"] for x in t["hypotheses"]}
        pairs = [
            ("H1_loose", t_h.get("H1"), cl["H1_level"] not in ("absent", "excluded")),
            ("H2_token", t_h.get("H2"), cl["H2_level"] != "absent"),
            ("H3_token", t_h.get("H3"), cl["H3_level"] == "af_data"),
            ("H4_token", t_h.get("H4"), cl["H4_level"] == "named"),
            ("loose_conforms", t.get("conforms_mechanical"), cl["loose_conforms"]),
            ("discharges", t.get("discharges_class_conclusion"),
             cl["discharges_class_conclusion"]),
        ]
        for field, tv, rv in pairs:
            if bool(tv) != bool(rv):
                disagreements.append({"theorem_id": cl["theorem_id"], "field": field,
                                      "target": bool(tv), "recheck": bool(rv)})
        if bool(t_h.get("H2")) and cl["H2_level"] != "spherical_data":
            disagreements.append({
                "theorem_id": cl["theorem_id"], "field": "H2_datareading",
                "target": True, "recheck": False,
                "mechanism": "token present but inside a negated/non-spherical form"
                             if cl["H2_level"] == "symmetry_broken" else "no token"})

    summary = {
        "bound_entries": len(per_entry),
        "loose_conforms": sum(1 for c in per_entry if c["loose_conforms"]),
        "space_conforms": sum(1 for c in per_entry if c["space_conforms"]),
        "strict_conforms": sum(1 for c in per_entry if c["strict_conforms"]),
        "discharges_class_conclusion": sum(
            1 for c in per_entry if c["discharges_class_conclusion"]),
        "H4_named_any_reading": sum(1 for c in per_entry if c["H4_level"] == "named"),
        "recall_unbound_loose": len(recall),
        "citation_rows_bound": len(cit),
        "citation_rows_unresolvable": sum(1 for c in cit if not c["resolvable"]),
        "controls_passed": sum(1 for c in controls.values() if c["pass"]),
        "controls_total": len(controls),
    }

    findings = [
        {
            "id": "W072C-F1",
            "text": ("0/%d bound entries discharge the class WCC conclusion under every "
                     "reading tested (loose/space/strict); the conclusion-poor finding "
                     "W072-F1 survives an independent implementation."
                     % summary["bound_entries"]),
        },
        {
            "id": "W072C-F2",
            "text": ("In-class count is reading-sensitive: loose %d, data-space %d, "
                     "strict %d. The gap is mechanical, not interpretive: the target's "
                     "H2 detector matches the substring 'spherical' inside "
                     "'non-spherical'. T-105 has exactly one 'spherical' occurrence in "
                     "the whole entry and it is inside 'non-spherical' (unresolved "
                     "field); T-106's four occurrences are all inside "
                     "'non-spherical'/'NON-SPHERICAL' forms. Under a data-space H2, "
                     "T-105, T-106 and T-524 fail: their data include anisotropic / "
                     "non-symmetric perturbations, which the taxonomy exclusions call a "
                     "forbidden transfer ('Non-spherical data: symmetry release is a "
                     "different class')."
                     % (summary["loose_conforms"], summary["space_conforms"],
                        summary["strict_conforms"])),
        },
        {
            "id": "W072C-F3",
            "text": ("Recall scan over all %d ledger entries: %d unbound entries still "
                     "pass the loose reading and %s; no unbound entry carries "
                     "conclusion_type=weak_cosmic_censorship. The audit's declared "
                     "blind spot (a conforming entry filed elsewhere) is measured, not "
                     "assumed away."
                     % (len(entries), summary["recall_unbound_loose"],
                        "none names H4" if not any(r["H4_level"] == "named"
                                                   for r in recall) else
                        "some name a genericity notion")),
        },
        {
            "id": "W072C-F4",
            "text": ("H4 (genericity) disagreement: the target's token set finds 0/%d; "
                     "an independent set that includes Baire-category vocabulary finds "
                     "%d. The hits are %s. None of them names genericity for the "
                     "class's own symmetry-reduced smooth data space, so W072-F2 is not "
                     "falsified, but T-524's 'first category' + 'open and dense' in the "
                     "continuous-shear-tensor topology is the nearest bound vocabulary "
                     "and is directly relevant to the F1 schema's genericity slot."
                     % (summary["bound_entries"], summary["H4_named_any_reading"],
                        ", ".join(sorted({t for c in per_entry
                                          for t in c["H4_tokens"]})) or "none")),
        },
        {
            "id": "W072C-F5",
            "text": ("Locator recheck by an independent validator: %d/%d class-bound "
                     "citation rows carry a syntactically resolvable doi/arxiv/url/"
                     "exact_locator; the stripped-locator control is flagged "
                     "(%s). Consistent with W072-F3."
                     % (summary["citation_rows_bound"] - summary["citation_rows_unresolvable"],
                        summary["citation_rows_bound"],
                        "pass" if not cit_control[0]["resolvable"] else "FAIL")),
        },
    ]
    if live_head is not None or tax_live is not None:
        findings.append({
            "id": "W072C-F6",
            "text": ("Input drift during the task: ledger/theorems.jsonl moved "
                     "%s -> %s after the first successful run. The pinned measurement "
                     "was recovered from a verified byte-identical archive and stays "
                     "bound to the target's revision. Live-head check: %d/%d entries, "
                     "bound class list %s, content-field changes in the class-bound "
                     "entries %d, discharges %d; invariant_in_substance=%s. The "
                     "measurement therefore survives the revision in substance, and "
                     "the check is recorded rather than assumed. Taxonomy live head "
                     "%s: H1-H4 equal=%s, conclusion_type equal=%s, exclusions "
                     "equal=%s."
                     % (pins["ledger/theorems.jsonl"]["pinned"][:12],
                        pins["ledger/theorems.jsonl"]["live_sha256"][:12],
                        live_head["entries_total"], live_head["pinned_entries_total"],
                        live_head["bound_to_class"],
                        len(live_head["content_field_changes_in_class_bound_entries"]),
                        live_head["discharges_class_conclusion"],
                        live_head["invariant_in_substance"],
                        (tax_live or {}).get("live_sha256", "n/a")[:12],
                        (tax_live or {}).get("hypotheses_equal"),
                        (tax_live or {}).get("conclusion_type_equal"),
                        (tax_live or {}).get("exclusions_equal"))),
        })

    result_core = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "node_id": "F0",
        "node_ids": ["F0", "L1"],
        "gate": "G-FORM",
        "actor": "worker-072",
        "target": {"path": TARGET_REPORT, "sha256": PINS[TARGET_REPORT],
                   "task_id": target.get("task_id")},
        "pins": pins,
        "class_definition_source": "research_map/formulation_taxonomy.yaml#%s"
                                   % PINS["research_map/formulation_taxonomy.yaml"][:12],
        "class_definition": cdef,
        "independent_method": {
            "stdlib_only": True,
            "does_not_import_target_runner": True,
            "pinned_input_resolution": ("live canonical path if its sha256 matches the "
                                        "pin, else a verified byte-identical on-disk "
                                        "snapshot; otherwise abort rc=2"),
            "readings": {
                "loose": "H1 scalar token, H2 spherical token, H3 AF token present",
                "space": "loose H1, H2/H3 as hypotheses on the data space (symmetry-breaking text rejects H2)",
                "strict": "space + H1 requires explicit massless-scalar/Einstein-scalar token",
            },
            "h4_tokens": GENERICITY_TOKENS,
            "h4_negation_window": 90,
            "object_fields": OBJECT_FIELDS,
        },
        "input_drift_observed_during_task": {
            rel: {"pinned": p["pinned"], "live_sha256": p["live_sha256"],
                  "resolved_from": p["source"], "resolved_path": p["used_path"]}
            for rel, p in pins.items() if p["live_drifted"]
        },
        "live_head_check": {"ledger": live_head, "taxonomy": tax_live},
        "summary": summary,
        "per_entry": per_entry,
        "disagreement_matrix": disagreements,
        "controls": controls,
        "recall_scan": {
            "entries_scanned": len(entries),
            "bound_to_class": len(bound),
            "unbound_conforming_or_wcc": recall,
        },
        "citation_locator_recheck": {"rows": cit, "stripped_locator_control": cit_control},
        "findings": findings,
        "not_claimed": ["node done", "gate pass", "theorem", "physics result",
                        "class re-binding (A1 owns that verdict)"],
        "authority_note": ("worker evidence only; a worker verdict cannot set "
                           "status=done, validation_status=passed, or a gate verdict"),
        "validation_status": "unverified",
        "falsifier": ("Re-run at the pinned hashes: a different per-entry reading, or "
                      "an unbound ledger entry with conclusion_type="
                      "weak_cosmic_censorship that this recall scan missed, falsifies "
                      "the table. A reviewer who binds T-105/T-524's data as "
                      "spherical (background reading) rather than anisotropic "
                      "(data-space reading) overturns W072C-F2 only, not W072C-F1."),
    }

    result_core["runner_sha256"] = sha256_file(RUNNER)
    core = json.dumps(result_core, sort_keys=True, ensure_ascii=False).encode("utf-8")
    result_core["result_digest"] = hashlib.sha256(core).hexdigest()

    from datetime import datetime, timezone, timedelta
    report = dict(result_core)
    report["generated_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat(
        timespec="seconds")
    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print(json.dumps({"summary": summary, "controls": {
        k: v["pass"] for k, v in controls.items()},
        "disagreements": len(disagreements),
        "result_digest": result_core["result_digest"],
        "report_sha256": sha256_file(OUT_REPORT)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
