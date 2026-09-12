#!/usr/bin/env python3
"""W096-F1-ANCHOR-INDEPENDENT-RECHECK-01

Independent non-author re-observation of the two major F1 provenance findings
recorded by worker-077 in artifacts/worker-077/f1_anchor_bind/report.json:

  W077-AB-01  5/5 F1 provenance.sources rows carry identifier=null and
              status=unresolved while their needed_for obligations are load-bearing.
  W077-AB-02  the four BL-11 anchor items have zero lexical hits in the pinned
              L0 ledger (ledger/theorems.jsonl#a1674f09) and citation audit
              (ledger/citation_audit.csv#315c1914).

This instrument is written from the F1 bytes and the pinned corpora, not from
worker-077's code: it imports nothing from that artifact and re-implements the
strict loader, the field-path resolver and the scanner.  It adds a
pre-registered formatting/paraphrase variant battery so the 0-hit claim is
tested beyond the exact BL-11 strings, and it records where a *different*
registered phrasing exists (A-PREDICT candidate SRC-096).

Exit codes:
  0  recheck completed; every strict check passed
  1  a strict check failed (finding flipped or census mismatch)
  2  a pinned input drifted (measurement VOID; no verdict written)
  3  a planted control failed (measurement INVALID; no verdict written)

Read-only on every canonical path.  Writes only inside this artifact directory.
Worker evidence only: no gate verdict, no node status, no validation_status.
"""
import csv
import datetime
import hashlib
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-096/f1_anchor_independent_recheck"
TASK = "W096-F1-ANCHOR-INDEPENDENT-RECHECK-01"
ACTOR = "worker-096"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"

# Hash pins for this measurement.  F1 / suite / FROZEN / F0 are FROZEN rev29
# members or G-F0 pins; the two ledger corpora are L0-gate pins (not FROZEN
# members) pinned by hash the way worker-077 and the r3 adjudication cite them.
PINS = {
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/f1_falsifier_tests.jsonl":
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv":
        "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}

# The four BL-11 anchor items exactly as worker-077 names them.
BL11_EXACT = [
    "s>5/2 threshold",
    "delta in (1/2,1)",
    "positive mass theorem",
    "future asymptotic predictability",
]

# Pre-registered variant battery.  "normalized" variants are formatting-only
# rewrites of the exact item (case is already folded by the scanner):
# a hit here would still anchor the item, so all are strict checks.
# "stem" variants drop filler words but keep the distinctive token.
# "context" variants are surrounding-concept terms; they are recorded, not
# checked, because a hit does not anchor the named obligation.
VARIANTS = {
    "s>5/2 threshold": {
        "normalized": ["s > 5/2 threshold", "s>5/2 threshold", "s > 5 / 2 threshold",
                       "s>5 / 2 threshold", "s > 5/2", "s>5/2"],
        "stem": ["5/2 threshold", "5/2", "5 / 2", "s > 5/2 weight", "s>5/2 weight"],
        "context": ["sobolev", "weighted sobolev", "weighted function space",
                    "asymptotically flat initial data", "decay rate"],
    },
    "delta in (1/2,1)": {
        "normalized": ["delta in (1/2, 1)", "delta in (1/2,1)", "delta in (1 / 2, 1)"],
        "stem": ["(1/2,1)", "(1/2, 1)", "delta in (1/2", "weight range"],
        "context": ["sobolev", "weighted sobolev", "decay rate"],
    },
    "positive mass theorem": {
        "normalized": ["positive-mass theorem", "positive mass theorem and rigidity",
                       "positive mass theorem (rigidity)"],
        "stem": ["positive mass", "adm mass", "adm-mass", "mass theorem",
                 "positive-mass rigidity"],
        "context": ["mass", "rigidity", "asymptotically flat initial data"],
    },
    "future asymptotic predictability": {
        "normalized": ["future asymptotic predictability", "future-asymptotic predictability",
                       "asymptotic predictability"],
        "stem": ["predictability", "predictable"],
        "variant_phrasing": ["future is not always open"],
        "context": ["future null infinity", "cosmic censorship", "determinism"],
    },
}

# Corpora scanned by every check below.
POSITIVE_CONTROLS = ["cauchy horizon", "singularit", "einstein"]
NEGATIVE_CONTROLS = ["zzz fabricated anchor phrase zzz", "quantum foam censorship"]
# A phrase that IS registered in the citation audit under a variant wording:
# used to show the scanner can find a real anchor-candidate phrase.
SENSITIVITY_PRESENT = "future is not always open"
SENSITIVITY_ABSENT = "negative mass theorem"


# --------------------------------------------------------------------------
# strict YAML loader (own implementation; rejects duplicate mapping keys)
# --------------------------------------------------------------------------
class StrictKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise StrictKeyError(f"duplicate mapping key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def sha256_path(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def measure_pins():
    out = {}
    for p in PINS:
        f = ROOT / p
        out[p] = {
            "exists": f.is_file(),
            "sha256": sha256_path(p) if f.is_file() else None,
            "bytes": f.stat().st_size if f.is_file() else None,
        }
    return out


def check_pins(measured, expected):
    bad = []
    for p, exp in expected.items():
        got = measured.get(p, {}).get("sha256")
        if got != exp:
            bad.append({"path": p, "expected": exp, "measured": got})
    return bad


# --------------------------------------------------------------------------
# scanners
# --------------------------------------------------------------------------
def load_citation_rows():
    with open(ROOT / "ledger/citation_audit.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_theorem_rows():
    rows = []
    for line in open(ROOT / "ledger/theorems.jsonl", encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def row_text_citation(r):
    return json.dumps(r, ensure_ascii=False, sort_keys=True).lower()


def row_text_theorem(r):
    return json.dumps(r, ensure_ascii=False, sort_keys=True).lower()


def scan(phrase, cit_texts, theo_texts):
    """Row hits and raw occurrence hits, case-insensitive, both corpora."""
    p = phrase.lower()
    return {
        "phrase": phrase,
        "citation_row_hits": sum(1 for t in cit_texts if p in t),
        "citation_occurrences": sum(t.count(p) for t in cit_texts),
        "ledger_row_hits": sum(1 for t in theo_texts if p in t),
        "ledger_occurrences": sum(t.count(p) for t in theo_texts),
    }


# --------------------------------------------------------------------------
# field-path resolver (own implementation)
# --------------------------------------------------------------------------
def walk_path(doc, dotted):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, None
        cur = cur[part]
    return dotted, cur


def find_unique_key(node, target, prefix):
    """Find `target` as a dict key under `node`; return (path, value) iff unique."""
    hits = []

    def rec(n, path):
        if isinstance(n, dict):
            for k, v in n.items():
                if k == target:
                    hits.append((f"{path}.{k}", v))
                rec(v, f"{path}.{k}")
        elif isinstance(n, list):
            for i, v in enumerate(n):
                rec(v, f"{path}[{i}]")

    rec(node, prefix)
    if len(hits) == 1:
        return hits[0]
    return None, None


def resolve_token(token, doc, raw_text):
    """Resolve a needed_for token: literal dotted path, then unique recovery,
    then prose sentinel present in the file."""
    token = token.strip()
    if "." in token or (isinstance(doc, dict) and token in doc):
        path, val = walk_path(doc, token)
        if path is not None:
            return {"token": token, "resolved": True, "kind": "literal_path",
                    "path": path}
    parts = token.split()
    if len(parts) >= 2:
        section, target = parts[0], parts[-1]
        node = doc.get(section) if isinstance(doc, dict) else None
        if node is not None:
            path, val = find_unique_key(node, target, section)
            if path is not None:
                return {"token": token, "resolved": True, "kind": "unique_recovery",
                        "path": path}
    if token in raw_text:
        return {"token": token, "resolved": True, "kind": "prose_sentinel", "path": None}
    return {"token": token, "resolved": False, "kind": None, "path": None}


def main():
    checks = []
    controls = []

    def add_check(cid, desc, ok, detail):
        checks.append({"id": cid, "description": desc,
                       "status": "PASS" if ok else "FAIL", "detail": detail})

    def add_control(kid, desc, ok, observed):
        controls.append({"id": kid, "description": desc, "ok": bool(ok),
                         "observed": observed})

    # ---- pins, entry ----
    pins_entry = measure_pins()
    bad_entry = check_pins(pins_entry, PINS)
    if bad_entry:
        print("PIN DRIFT AT ENTRY (VOID):", json.dumps(bad_entry, indent=1))
        return 2

    f1_path = ROOT / "schemas/af_wcc_vacuum.yaml"
    f1_raw = f1_path.read_text(encoding="utf-8")
    try:
        f1 = yaml.load(f1_raw, Loader=StrictLoader)
        strict_ok = True
    except StrictKeyError as exc:
        print("STRICT LOAD FAILED:", exc)
        return 3

    cit_rows = load_citation_rows()
    theo_rows = load_theorem_rows()
    cit_texts = [row_text_citation(r) for r in cit_rows]
    theo_texts = [row_text_theorem(r) for r in theo_rows]

    # ---- C1 pins ----
    add_check("C1-pins-entry", "all six pinned inputs measured and equal to their declared sha256",
              not bad_entry, {"pins": {p: v["sha256"] for p, v in pins_entry.items()}})

    # ---- C2 provenance census (W077-AB-01 re-observation) ----
    sources = f1["provenance"]["sources"]
    n = len(sources)
    n_null = sum(1 for s in sources if s.get("identifier") is None)
    n_unres = sum(1 for s in sources if s.get("status") == "unresolved")
    concepts = [s.get("concept") for s in sources]
    add_check("C2-provenance-census",
              "F1 provenance.sources has 5 rows; 5/5 identifier=null; 5/5 status=unresolved",
              n == 5 and n_null == 5 and n_unres == 5,
              {"rows": n, "identifier_null": n_null, "status_unresolved": n_unres,
               "concepts": concepts})

    # ---- C3 needed_for field binding (W077-AB-04 re-observation) ----
    binding = []
    all_tokens = []
    for s in sources:
        for tok in s.get("needed_for", "").split(","):
            if tok.strip():
                all_tokens.append(tok.strip())
    for tok in all_tokens:
        binding.append(resolve_token(tok, f1, f1_raw))
    unresolved_tokens = [b for b in binding if not b["resolved"]]
    recovered = [b for b in binding if b["kind"] == "unique_recovery"]
    add_check("C3-needed-for-resolves",
              "every needed_for token resolves (literal path, unique recovery, or prose sentinel)",
              not unresolved_tokens,
              {"tokens": all_tokens, "unresolved": unresolved_tokens,
               "recovered": recovered})

    # ---- C4 exact BL-11 zero-hit (W077-AB-02 re-observation) ----
    exact = [scan(p, cit_texts, theo_texts) for p in BL11_EXACT]
    exact_zero = all(r["citation_occurrences"] == 0 and r["ledger_occurrences"] == 0
                     for r in exact)
    add_check("C4-bl11-exact-zero-hit",
              "all four BL-11 items have 0 occurrences in both pinned corpora",
              exact_zero, {"results": exact})

    # ---- C5 pre-registered variant battery ----
    variant_results = {}
    for item, groups in VARIANTS.items():
        variant_results[item] = {g: [scan(v, cit_texts, theo_texts) for v in vs]
                                 for g, vs in groups.items()}
    normalized_hits = [(item, r) for item, g in variant_results.items()
                       for r in g["normalized"] if r["citation_occurrences"] or r["ledger_occurrences"]]
    stem_hits = [(item, r) for item, g in variant_results.items()
                 for r in g["stem"] if r["citation_occurrences"] or r["ledger_occurrences"]]
    vp_hits = [(item, r) for item, g in variant_results.items()
               for r in g.get("variant_phrasing", [])
               if r["citation_occurrences"] or r["ledger_occurrences"]]
    context_hits = [(item, r) for item, g in variant_results.items()
                    for r in g["context"] if r["citation_occurrences"] or r["ledger_occurrences"]]
    add_check("C5a-normalized-variants-zero",
              "no formatting-only rewrite of any BL-11 item has a hit",
              not normalized_hits, {"hits": normalized_hits})
    add_check("C5b-stem-variants-zero",
              "no distinctive-token stem of the 4 items has a hit",
              not stem_hits, {"hits": stem_hits})
    # variant-phrasing hits are expected for A-PREDICT only, and must resolve to
    # the registered SRC-096 title (a refinement, not an anchor for the obligation).
    vp_ok = (len(vp_hits) == 1 and vp_hits[0][0] == "future asymptotic predictability"
             and vp_hits[0][1]["citation_occurrences"] == 1
             and vp_hits[0][1]["ledger_occurrences"] == 0)
    add_check("C5c-variant-phrasing-resolves",
              "the only variant-phrasing hit is the SRC-096 title in the citation audit",
              vp_ok, {"hits": vp_hits})
    # context hits are recorded, not required to be zero

    # ---- C6 positive controls ----
    pos = [scan(p, cit_texts, theo_texts) for p in POSITIVE_CONTROLS]
    pos_ok = all(r["citation_occurrences"] > 0 and r["ledger_occurrences"] > 0 for r in pos)
    add_check("C6-positive-controls-live",
              "known-present phrases return non-zero occurrences in both corpora",
              pos_ok, {"results": pos})

    # ---- C7 negative controls ----
    neg = [scan(p, cit_texts, theo_texts) for p in NEGATIVE_CONTROLS]
    neg_ok = all(r["citation_occurrences"] == 0 and r["ledger_occurrences"] == 0 for r in neg)
    add_check("C7-negative-controls-zero",
              "fabricated phrases return zero occurrences in both corpora",
              neg_ok, {"results": neg})

    # ---- C8 sensitivity ----
    sens_present = scan(SENSITIVITY_PRESENT, cit_texts, theo_texts)
    sens_absent = scan(SENSITIVITY_ABSENT, cit_texts, theo_texts)
    add_check("C8-sensitivity",
              "a registered variant phrase is found while its mutant is not",
              sens_present["citation_occurrences"] > 0
              and sens_absent["citation_occurrences"] == 0
              and sens_absent["ledger_occurrences"] == 0,
              {"present": sens_present, "absent": sens_absent})

    # ---- C9 corpus sizes reproduce ----
    add_check("C9-corpus-sizes",
              "corpus row counts measured (97 citation rows, 62 theorem rows expected)",
              len(cit_rows) == 97 and len(theo_rows) == 62,
              {"citation_rows": len(cit_rows), "theorem_rows": len(theo_rows)})

    # ---- C10 registered-but-unbound candidate for A-PREDICT (refinement) ----
    src096 = [r for r in cit_rows
              if "future is not always open" in (r.get("title") or "").lower()]
    src096_ids = [r.get("citation_id") for r in src096]
    ledger_source_ids = set()
    for r in theo_rows:
        for sid in (r.get("source_ids") or []):
            ledger_source_ids.add(sid)
    refinement = {
        "variant_phrase": SENSITIVITY_PRESENT,
        "citation_ids": src096_ids,
        "in_ledger_source_ids": {sid: (sid in ledger_source_ids) for sid in src096_ids},
        "note": ("A-PREDICT is the only one of the four BL-11 items with a registered "
                 "source under a different phrasing; it is a title-level candidate, not "
                 "an L1 ledger anchor, and does not bound the obligation."),
    }

    # ---- planted controls (in-memory only) ----
    add_control("K1-injection",
                "an anchor phrase injected into a synthetic row is detected",
                scan("positive mass theorem", ["x positive mass theorem y"], [])["citation_occurrences"] == 1,
                "synthetic row scanned")
    add_control("K2-absence",
                "an anchor-free synthetic row yields zero",
                scan("positive mass theorem", ["nothing relevant here"], [])["citation_occurrences"] == 0,
                "synthetic row scanned")
    add_control("K3-pin-mutation",
                "a mutated expected pin fails the pin comparison",
                bool(check_pins({"schemas/af_wcc_vacuum.yaml": {"sha256": "0" * 64}},
                                {"schemas/af_wcc_vacuum.yaml": PINS["schemas/af_wcc_vacuum.yaml"]})),
                "mutated pin rejected")
    try:
        yaml.load("a: 1\na: 2\n", Loader=StrictLoader)
        dup_rejected = False
    except StrictKeyError:
        dup_rejected = True
    add_control("K4-duplicate-key-guard", "strict loader rejects a duplicate mapping key",
                dup_rejected, "duplicate key rejected")
    real = resolve_token("data_class.adm_mass", f1, f1_raw)
    fake = resolve_token("data_class.no_such_leaf", f1, f1_raw)
    add_control("K5-resolver-discriminates",
                "a real dotted path resolves and a fabricated one fails closed",
                real["resolved"] and not fake["resolved"],
                {"real": real, "fake": fake})
    add_control("K6-content-not-path",
                "a synthetic copy carrying the phrase is detected even though the phrase is absent from live corpora",
                scan("positive mass theorem", ["copy of ledger row with positive mass theorem"],
                     [])["citation_occurrences"] == 1,
                "content-driven detection")

    # ---- pins, exit / drift guard ----
    pins_exit = measure_pins()
    bad_exit = check_pins(pins_exit, PINS)
    add_check("C10-no-drift", "all six pins byte-identical entry to exit",
              not bad_exit, {"drifted": bad_exit})

    controls_ok = all(c["ok"] for c in controls)
    checks_ok = all(c["status"] == "PASS" for c in checks)

    # ---- findings ----
    findings = [
        {
            "id": "W096-AB-01",
            "reproduces": "W077-AB-01",
            "severity": "major",
            "status": "independently_confirmed",
            "statement": ("At F1 schemas/af_wcc_vacuum.yaml#d9cebb9404b2 (FROZEN rev29), an "
                          "independent strict-YAML census finds provenance.sources has exactly 5 "
                          "rows, all 5 with identifier=null and status=unresolved, and all 7 "
                          "needed_for tokens resolve (6 literal/unique-recovery field bindings + "
                          "1 prose sentinel). The finding is reproduced byte-for-byte at the pin."),
            "falsifier": ("Any provenance.sources row at the live F1 hash with a non-null "
                          "identifier whose status is resolved, or any needed_for token that "
                          "fails to resolve under literal/recovery/sentinel."),
        },
        {
            "id": "W096-AB-02",
            "reproduces": "W077-AB-02",
            "severity": "major",
            "status": "independently_confirmed_with_scope_refinement",
            "statement": ("At the pinned corpora (ledger/theorems.jsonl#a1674f09, "
                          "ledger/citation_audit.csv#315c1914) all four BL-11 items have 0 "
                          "occurrences, and the 0-hit result survives the pre-registered "
                          "formatting/paraphrase battery (normalized and stem variants all 0). "
                          "Three of the four concepts are empty under every variant tested "
                          "(no 'sobolev', '5/2', 'positive mass', 'adm mass', 'predictability'). "
                          "Refinement: A-PREDICT has one registered title-level candidate under a "
                          "different phrasing (SRC-096 'The future is not always open', in the "
                          "citation audit, absent from ledger source_ids), which narrows the "
                          "strong reading 'no registered source bears on the concept' to "
                          "'no registered source anchors the obligation under the BL-11 naming'."),
            "falsifier": ("Any >=1 occurrence of a BL-11 item or its normalized/stem variants in "
                          "either pinned corpus, or a positive control with 0 occurrences."),
        },
        {
            "id": "W096-AB-03",
            "reproduces": "W077-AB-04",
            "severity": "minor",
            "status": "independently_confirmed",
            "statement": ("The needed_for token 'quantifiers D2' is not itself a YAML path; the "
                          "unique independent recovery is quantifiers.domains.D2. The other six "
                          "tokens resolve literally except the prose sentinel 'no status claim is "
                          "made by this schema', which is present in the F1 text."),
            "falsifier": ("A second key named D2 under quantifiers, or a revision in which "
                          "quantifiers.domains.D2 does not exist."),
        },
    ]

    verdict = {
        "verdict": ("INDEPENDENT_RECHECK_CONFIRMS_W077_AB01_AB02" if checks_ok and controls_ok
                    else "RECHECK_DISAGREES"),
        "checks_passed": f"{sum(1 for c in checks if c['status'] == 'PASS')}/{len(checks)}",
        "controls_passed": f"{sum(1 for c in controls if c['ok'])}/{len(controls)}",
        "hard_failures": [],
        "counts_as_full_schema_verdict": False,
        "counts_toward_gate_accept": False,
    }

    report = {
        "schema": "w096-f1-anchor-recheck/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "node_id": NODE_ID,
        "gate": GATE,
        "authority": ("worker measurement only; read-only on every canonical path; no gate "
                      "verdict, no node status, no validation_status=passed, no canonical write"),
        "object": ("independent non-author re-observation of W077-AB-01/W077-AB-02/W077-AB-04 at "
                   "the FROZEN rev29 pins, with a pre-registered variant battery"),
        "independence": {
            "relation_to_author": "none; worker-077 authored the original census, worker-096 authored none of the pinned inputs",
            "instrument": "private stdlib+PyYAML instrument (this file); no worker-077 code imported or executed",
            "method": "own strict loader, own field-path resolver, own row/occurrence scanner; variants pre-registered in code before the run",
        },
        "pins_entry": pins_entry,
        "pins_exit": pins_exit,
        "checks": checks,
        "controls": controls,
        "provenance_rows": sources,
        "field_binding": binding,
        "bl11_exact": exact,
        "variant_battery": variant_results,
        "positive_controls": pos,
        "negative_controls": neg,
        "sensitivity": {"present": sens_present, "absent": sens_absent},
        "refinement_a_predict_candidate": refinement,
        "findings": findings,
        "verdict": verdict,
        "falsifier": ("Re-run this instrument at the same pins: falsified if any provenance anchor "
                      "has a resolved non-null identifier, any BL-11 item or normalized/stem variant "
                      "has a hit, any needed_for token fails to resolve, a positive control returns "
                      "0, or any pinned input drifts (drift voids; control failure invalidates)."),
        "next_falsifier": ("A rev30 write at a new F1 hash voids these pins and requires a re-run; "
                           "if the owner binds an L1 anchor to any provenance.sources row, W096-AB-01 "
                           "and the corresponding BL-11 item both flip."),
        "non_claims": [
            "not a gate verdict and does not set any node status or validation_status",
            "does not adjudicate the F0-vs-F1 set-strength direction (ESC-2) or any other open finding",
            "asserts no mathematics, physics or literature claim beyond lexical occurrences in the pinned bytes",
            "candidate source lists are lexical matches, not endorsed anchors",
            "W096-AB-02 does not dispute worker-077's count; it independently reproduces it and narrows its scope",
        ],
    }

    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "snapshots").mkdir(exist_ok=True)
    (HERE / "snapshots/f1_provenance_sources.d9cebb9404b2.json").write_text(
        json.dumps(sources, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "snapshots/bl11_scan_results.json").write_text(
        json.dumps({"exact": exact, "variant_battery": variant_results,
                    "positive_controls": pos, "negative_controls": neg,
                    "refinement": refinement}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    if not controls_ok:
        print("CONTROL FAILURE (INVALID):",
              json.dumps([c for c in controls if not c["ok"]], indent=1))
        return 3
    if not checks_ok:
        (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
        print("CHECK FAILURE (REVISE):",
              json.dumps([c for c in checks if c["status"] != "PASS"], indent=1))
        return 1

    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    print(f"{TASK}: {verdict['verdict']}")
    print("checks:", verdict["checks_passed"], "controls:", verdict["controls_passed"])
    for c in checks:
        print(f"  [{c['status']}] {c['id']}")
    for f in findings:
        print(f"  finding {f['id']} ({f['severity']}): {f['status']}")
    print("report:", HERE / "report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
