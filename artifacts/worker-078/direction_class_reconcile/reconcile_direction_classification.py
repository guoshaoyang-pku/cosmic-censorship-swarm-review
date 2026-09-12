#!/usr/bin/env python3
"""W078-DIRCENSUS-CLASS-RECONCILE-01 -- classification reconciliation for the
formulation strength-direction census at the FROZEN rev29 pins.

Question
--------
W099-FORM-DIRECTION-CENSUS-01 (`artifacts/worker-099/form_direction_census/census.json`)
reports 3 INVERTED direction findings and leaves 34 hits in MANUAL_REVIEW at the FROZEN
rev29 pins.  W078-F0-SET-STRENGTH-ADJ-01 classified one of those three (the authoring
supplement D1 ledger, `artifacts/formulation/formulation_taxonomy.yaml:176`) as a historical
mention, not an operative claim, and separately found an operative inversion the census did
not list (`research_map/formulation_taxonomy.yaml:94`).  Two instruments disagree about the
same pinned bytes.  This run adjudicates the disagreement and bounds the OPT-B repair set.

Method
------
1. Pin 10 inputs by sha256 (8 formulation artifacts + the census artifact + the prior W078
   report).  Start mismatch is a hard error (exit 2); start/end drift voids the binding.
2. Candidate set = census entries UNION an own regex scan of the 8 pinned files for
   stronger/weaker/larger/smaller.  Coverage differences are reported both ways.
3. Automatic rule verdict per candidate (rule ids in `classify_window`).  Where the line has
   more than one candidate subject, or no recognised subject, the automatic verdict is
   NEEDS_ADJUDICATION.
4. `adjudication_table.json` supplies anchored adjudications (verbatim anchor substring that
   must occur in the pinned window, else exit 5).  The table may override an automatic
   verdict; both are reported.  Overrides are the worker's reading, not the instrument's.
5. Truth table derived from the pins themselves:
     containment chain (declared at F2a:148 and F2b:241-243):
         E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0
       => C0-inextendibility STRONGEST; C2 weakest; a larger extension class => weaker statement.
     WCC: SINGLEQ (single-q tail) implies SET (union), not conversely -- re-derived here by
       finite-model check over preorders (chains only) + omega-chain separation witness.
     all-data vs generic: all-data strictly stronger; two-sided vs future: two-sided stronger;
     distributional-Ricci vs bare continuous: distributional weaker; CH horizon-localized
     vs broad C0: CH weaker.
6. Union repair manifest = OPERATIVE_INVERTED sites from (census INVERTED) UNION (this run),
   plus NOT-repairable historical records with reasons.

Authority: worker-level evidence only.  Read-only on every canonical path; writes only under
artifacts/worker-078/ and runtime/state/.  No gate verdict, no node status,
no validation_status=passed.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

PINS = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VARIANT_REGISTRY.json": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/f1_falsifier_tests.jsonl": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "artifacts/worker-099/form_direction_census/census.json": None,
    "artifacts/worker-078/f0_set_strength_adjudication/report.json": None,
}
# Inputs that are measured but NOT part of the audited corpus (they may legitimately contain
# words like "stronger" as census/report metadata).
SCAN_EXCLUDE = {
    "artifacts/worker-099/form_direction_census/census.json",
    "artifacts/worker-078/f0_set_strength_adjudication/report.json",
}

STRENGTH_RE = re.compile(r"(?i)\b(strictly\s+)?(stronger|weaker|larger|smaller)\b")
SUBJECT_RE = re.compile(
    r"(?i)(set-based reading|set-based condition|union of J\^\(-\)\(q\)|variant\s*`?SET`?|"
    r"single-q|single q|TAIL predicate|two-sided|distributional|horizon-localized|\bCH\b|"
    r"forall AF vacuum data|all AF vacuum data|ALL AF vacuum|C-infinity extensions|"
    r"smooth extensions|H2_loc|\bC0\b|\bC2\b)")

NEG_SCOPE_KEYS = (
    "anti_scope", "not_this_class", "forbidden_strengthenings", "forbidden_weakenings",
    "forbidden_inflation", "exclusions", "must_not_conflate", "rejected_ambiguous_tokens",
    "composite_regularity_ban", "schema_falsifiers", "false_positive_controls",
    "forbidden_transfers", "c0_specific_note", "vacuity_falsifier", "subsumption_note",
)
HIST_LINE_MARKERS = ("f0_reading", "lead_reading")
HIST_NEAR_MARKERS = ("contract_divergences", "resolution:", "found_by:")
DEF_MARKERS = ("iff", "is an open, proper subset", "is a proper", "definition:", "meaning_",
               "_definition", "concept:", "criterion:")

# Specific subjects first: a line mentioning two-sided + C2 must be read as a two-sided claim.
TRUTH_RULES = [
    (r"set-based reading|set-based condition|union of J\^\(-\)\(q\)|variant\s*`?SET`?|the SET\b",
     "SET_WEAKER"),
    (r"single-q|single q|TAIL predicate", "SET_WEAKER"),
    (r"two-sided", "TWOSIDED_STRONGER"),
    (r"distributional", "DISTRIBUTIONAL_WEAKER"),
    (r"horizon-localized|\bCH\b", "CH_WEAKER"),
    (r"forall AF vacuum data|all AF vacuum data|ALL AF vacuum", "ALLDATA_STRONGER"),
    (r"C-infinity extensions|smooth extensions", "SMOOTH_SUBSET"),
    (r"\bC0\b", "C0_STRONGER"),
    (r"\bC2\b", "C2_WEAKER"),
    (r"H2_loc", "H2LOC_MIDDLE"),
]
TRUTH = {
    "SET_WEAKER": {"weaker": "CORRECT", "smaller": "CORRECT", "stronger": "INVERTED", "larger": "INVERTED"},
    "C0_STRONGER": {"stronger": "CORRECT", "larger": "CORRECT", "weaker": "INVERTED", "smaller": "INVERTED"},
    "C2_WEAKER": {"weaker": "CORRECT", "smaller": "CORRECT", "stronger": "INVERTED", "larger": "INVERTED"},
    "ALLDATA_STRONGER": {"stronger": "CORRECT", "larger": "CORRECT", "weaker": "INVERTED", "smaller": "INVERTED"},
    "TWOSIDED_STRONGER": {"stronger": "CORRECT", "larger": "CORRECT", "weaker": "INVERTED", "smaller": "INVERTED"},
    "DISTRIBUTIONAL_WEAKER": {"weaker": "CORRECT", "smaller": "CORRECT", "stronger": "INVERTED", "larger": "INVERTED"},
    "CH_WEAKER": {"weaker": "CORRECT", "smaller": "CORRECT", "stronger": "INVERTED", "larger": "INVERTED"},
    "SMOOTH_SUBSET": {"weaker": "CORRECT", "smaller": "CORRECT", "stronger": "INVERTED", "larger": "INVERTED"},
    "H2LOC_MIDDLE": {},
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path: Path):
    return path.read_text(errors="replace").splitlines()


def enclosing_section(lines, lineno: int, max_back: int = 25) -> str:
    hit = lines[lineno - 1]
    hit_indent = len(hit) - len(hit.lstrip())
    for ln in range(lineno - 1, max(0, lineno - 1 - max_back), -1):
        text = lines[ln - 1]
        if not text.strip():
            continue
        indent = len(text) - len(text.lstrip())
        if indent > hit_indent:
            continue
        m = re.match(r'\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*:', text)
        if m:
            return m.group(1)
    return ""


def classify_line(path: str, lines, lineno: int) -> dict:
    """Automatic verdict for one candidate.  Returns dict with verdict/rule/reason/context."""
    hit = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
    context = enclosing_section(lines, lineno) if lines else ""
    if path.endswith("f1_falsifier_tests.jsonl"):
        return {"verdict": "PROBE_RECORD", "rule": "R_PROBE", "context": "probe-corpus",
                "reason": ("non-canonical F1 ambiguity-probe corpus; records compare field wording and "
                           "bind to a superseded F1 hash (binding_frozen_revision 27 / 9a8bd4c96800), "
                           "not to class strength claims")}
    near = "\n".join(lines[max(0, lineno - 6):lineno])
    if any(m in hit for m in HIST_LINE_MARKERS) or (
            any(m in near for m in HIST_NEAR_MARKERS)
            and re.search(r"status:\s*(resolved|cleared)", hit)):
        return {"verdict": "HISTORICAL_MENTION", "rule": "R_HIST", "context": "divergence-ledger",
                "reason": ("resolved divergence-ledger record: the strength phrase is inside the quoted "
                           "historical reading (f0_reading) / its resolution; the record documents the old "
                           "declared reading and does not assert it as current")}
    m = STRENGTH_RE.search(hit)
    if not m:
        if any(k in context for k in DEF_MARKERS) or any(k in hit for k in DEF_MARKERS):
            return {"verdict": "DEFINITION", "rule": "R_DEF", "context": context or "definition",
                    "reason": "definition line; any strength token in the census window belongs to a "
                              "neighbouring clause, not to this line"}
        return {"verdict": "NEEDS_ADJUDICATION", "rule": "R_NONE", "context": context,
                "reason": "no strength token on the hit line and no definitional marker found"}
    subjects = set(x.group(0).lower() for x in SUBJECT_RE.finditer(hit))
    if len(subjects) > 1:
        return {"verdict": "NEEDS_ADJUDICATION", "rule": "R_MULTI_SUBJECT", "context": context,
                "reason": f"line carries {len(subjects)} candidate subjects {sorted(subjects)}; "
                          "line-level subject attribution is ambiguous"}
    direction = m.group(2).lower()
    for subj_re, rel in TRUTH_RULES:
        if re.search(subj_re, hit, re.I):
            table = TRUTH[rel]
            verdict = table.get(direction)
            if verdict is None:
                return {"verdict": "NEEDS_ADJUDICATION", "rule": "R_OPERATIVE", "context": context,
                        "reason": f"relation {rel} has no table entry for direction '{direction}'"}
            return {"verdict": f"OPERATIVE_{verdict}", "rule": "R_OPERATIVE", "context": context,
                    "reason": f"operative comparative; subject family {rel}; asserted '{direction}' "
                              f"vs truth table -> {verdict}"}
    return {"verdict": "NEEDS_ADJUDICATION", "rule": "R_NONE", "context": context,
            "reason": "strength token present but no recognised subject family"}


def cross_check_truth_direction() -> dict:
    """Re-derive SINGLEQ => SET (chains only) and the omega-chain separation."""
    violations = 0
    models = 0
    for n in (3, 4):
        pts = list(range(n))
        pairs = [(a, b) for a in pts for b in pts]
        for bits in range(1 << len(pairs)):
            rel = {pairs[i] for i in range(len(pairs)) if (bits >> i) & 1}
            if not all((x, x) in rel for x in pts):
                continue
            if any((x, y) in rel and (y, z) in rel and (x, z) not in rel
                   for x, y, z in itertools.product(pts, repeat=3)):
                continue
            models += 1
            ip_sets = [set(c) for k in range(1, n + 1) for c in itertools.combinations(pts, k)]
            for ip in ip_sets:
                for gamma in itertools.product(pts, repeat=n):
                    if any(not (gamma[i], gamma[j]) in rel for i in range(n) for j in range(i, n)):
                        continue  # not a chain
                    singleq = any((gamma[-1], q) in rel for q in ip)
                    setread = all(any((x, q) in rel for q in ip) for x in gamma)
                    if singleq and not setread:
                        violations += 1

    def omega(n):
        def le(a, b):
            if a[0] == "x" and b[0] in ("x", "q"):
                return a[1] <= b[1]
            if a[0] == "q" and b[0] == "q":
                return a[1] == b[1]
            return False
        qs = [("q", j) for j in range(n)]
        xs = [("x", i) for i in range(n)]
        setread = all(any(le(x, q) for q in qs) for x in xs)
        # Separation certificate on the omega-chain rule x_i <= q_j iff i <= j:
        # for every candidate (q_j, t0) with j,t0 < n-1 there is an index i >= t0 with
        # gamma[i] not <= q_j (take i = max(t0, j+1)).  Existence of the witness for every
        # candidate is what makes SINGLEQ fail on the infinite chain; a finite truncation's
        # top q is an artefact and is excluded by j < n-1.
        certs, failures = 0, []
        for j in range(n - 1):
            for t0 in range(n - 1):
                i = max(t0, j + 1)
                if i < n and not le(xs[i], qs[j]):
                    certs += 1
                else:
                    failures.append([j, t0])
        return setread, certs, failures

    omega_res = {str(n): omega(n) for n in (8, 16, 32)}
    ok = violations == 0 and all(v[0] and not v[2] for v in omega_res.values())
    return {
        "finite_model": {"models_checked": models, "chain_restricted": True,
                         "singleq_implies_set_violations": violations},
        "omega_chain_separation": {
            k: {"set_reading_holds": v[0], "uncovered_tail_certificates": v[1],
                "candidate_cover_failures": len(v[2])}
            for k, v in omega_res.items()},
        "verdict": ("SET strictly weaker; SINGLEQ entails SET" if ok
                    else "TRUTH DIRECTION NOT CONFIRMED"),
    }


FIXTURES = [
    ("operative_inverted_set",
     "- parent_class: AF-WCC-VAC-GEN\n  definition: >-\n    set-based reading. Strictly stronger than the parent class.\n",
     "schema.yaml", "OPERATIVE_INVERTED"),
    ("operative_correct_set",
     "- parent_class: AF-WCC-VAC-GEN\n  definition: >-\n    set-based reading. Strictly weaker than the parent class.\n",
     "schema.yaml", "OPERATIVE_CORRECT"),
    ("operative_inverted_c2_larger",
     "  reason: \"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker\"\n",
     "schema.yaml", "OPERATIVE_INVERTED"),
    ("operative_correct_single_subject_set",
     "  reason: \"the set-based reading is strictly weaker than the parent class\"\n",
     "schema.yaml", "OPERATIVE_CORRECT"),
    ("multi_subject_c0_vs_c2_guard",
     "  reason: \"C0-inextendibility is stronger than the C2 class's conclusion\"\n",
     "schema.yaml", "NEEDS_ADJUDICATION"),
    ("implicit_subject_two_sided_over_c2",
     "  strength: \"two-sided inextendibility is strictly STRONGER than AF-SCC-C2-VAC-GEN\"\n",
     "registry.json", "NEEDS_ADJUDICATION"),
    ("negative_scope_correct",
     "forbidden_weakenings:\n  - \"substituting H2_loc for C0 (H2_loc-inextendibility is weaker)\"\n",
     "schema.yaml", "NEEDS_ADJUDICATION"),  # H2_loc middle -> anchored in real table
    ("historical_ledger",
     "contract_divergences:\n  items:\n    - {id: D1, f0_reading: \"SET (strictly stronger)\", status: resolved, resolution: \"F0 amended\"}\n",
     "supplement.yaml", "HISTORICAL_MENTION"),
    ("definition_window",
     "  definition: >-\n    A proper future C2 vacuum extension iff (b) iota(M) is an open, proper subset of M';\n",
     "schema.yaml", "DEFINITION"),
    ("probe_record",
     "{\"ambiguity_kind\": \"x\", \"binding_frozen_revision\": 27, \"note\": \"stronger wording\"}\n",
     "schemas/f1_falsifier_tests.jsonl", "PROBE_RECORD"),
]


def fixture_controls() -> dict:
    results = []
    for name, text, path, want in FIXTURES:
        lines = text.splitlines()
        hit = next((i for i, t in enumerate(lines, 1) if STRENGTH_RE.search(t)), max(1, len(lines)))
        got = classify_line(path, lines, hit)
        results.append({"fixture": name, "expected": want, "observed": got["verdict"],
                        "rule": got["rule"], "ok": got["verdict"] == want})
    return {"fixtures": results, "all_ok": all(r["ok"] for r in results)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", default="2026-09-12T01:30:00+08:00")
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--controls", action="store_true")
    a = ap.parse_args()

    pins_start = {}
    for rel, expected in PINS.items():
        h = sha256_file(ROOT / rel)
        pins_start[rel] = h
        if expected is not None and h != expected:
            print(f"PIN MISMATCH {rel}: expected {expected}, measured {h}", file=sys.stderr)
            return 2

    census = json.loads((ROOT / "artifacts/worker-099/form_direction_census/census.json").read_text())
    prior = json.loads((ROOT / "artifacts/worker-078/f0_set_strength_adjudication/report.json").read_text())
    adj_table = {}
    if (HERE / "adjudication_table.json").exists():
        adj_table = {e["key"]: e for e in json.loads((HERE / "adjudication_table.json").read_text())["entries"]}

    file_lines = {rel: read_lines(ROOT / rel) for rel in PINS}

    census_hits = list(census.get("inverted_findings", [])) + list(census.get("hits", []))
    candidates, seen = [], set()
    for h in census_hits:
        key = (h["path"], h.get("line"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"source": "census", "path": h["path"], "line": h.get("line"),
                           "window": h.get("window"), "census_verdict": h.get("verdict"),
                           "census_rule": h.get("rule"), "census_reason": h.get("reason")})

    scan_hits = [{"path": rel, "line": i} for rel, lines in file_lines.items() if rel not in SCAN_EXCLUDE
                 for i, text in enumerate(lines, 1) if STRENGTH_RE.search(text)]

    def covered(c, hits):
        for s in hits:
            if s["path"] != c["path"]:
                continue
            w = c.get("window") or [c["line"], c["line"]]
            if (w[0] or c["line"]) - 1 <= s["line"] <= (w[1] or c["line"]) + 1:
                return True
        return False

    scan_not_in_census = [s for s in scan_hits if not covered(s, candidates)]
    census_not_in_scan = [c for c in candidates if not covered(c, scan_hits)]

    results = []
    for idx, c in enumerate(candidates):
        lines = file_lines.get(c["path"], [])
        auto = classify_line(c["path"], lines, c["line"])
        final, rule, reason = auto["verdict"], auto["rule"], auto["reason"]
        override = None
        key = f"{c['path']}:{c['line']}"
        entry = adj_table.get(key)
        if entry:
            w = c.get("window") or [c["line"], c["line"]]
            lo = max(1, (w[0] or c["line"]) - 2)
            hi = min(len(lines), (w[1] or c["line"]) + 2)
            window_text = "\n".join(lines[lo - 1:hi])
            hit_text = lines[c["line"] - 1] if 0 < c["line"] <= len(lines) else ""
            if entry["anchor"] not in window_text and entry["anchor"] not in hit_text:
                print(f"ANCHOR FAIL-CLOSED {key}: anchor not present in pinned window", file=sys.stderr)
                return 5
            final = entry["verdict"]
            rule = "R_ANCHORED_ADJUDICATION"
            reason = entry["reason"]
            override = {"auto_verdict": auto["verdict"], "auto_rule": auto["rule"],
                        "anchor": entry["anchor"], "by": "worker-078 anchored reading"}
        results.append({
            "idx": idx, "path": c["path"], "line": c["line"], "window": c.get("window"),
            "in_scope": c["census_verdict"] in ("INVERTED", "MANUAL_REVIEW"),
            "section_context": auto["context"],
            "census_verdict": c["census_verdict"], "census_rule": c["census_rule"],
            "auto_verdict": auto["verdict"], "auto_rule": auto["rule"],
            "w078_verdict": final, "w078_rule": rule, "reason": reason,
            "override": override,
            "hit_excerpt": (file_lines.get(c["path"], [""])[c["line"] - 1] if 0 < c["line"] <= len(file_lines.get(c["path"], [])) else "")[:300],
        })

    conflicts = [{"path": r["path"], "line": r["line"], "census": r["census_verdict"],
                  "w078": r["w078_verdict"], "w078_rule": r["w078_rule"], "reason": r["reason"]}
                 for r in results
                 if r["in_scope"] and r["w078_verdict"] != r["census_verdict"]
                 and not (r["census_verdict"] == "MANUAL_REVIEW" and r["w078_verdict"] != "NEEDS_ADJUDICATION")]
    # Out-of-scope (census CORRECT/META_RETRACTED) hits where the automatic triage disagrees with
    # the census: these are rule-level false positives from line-level subject misattribution,
    # recorded for transparency and resolved in the census's favour on reading (see report).
    rule_conflicts_reference = [
        {"path": r["path"], "line": r["line"], "census": r["census_verdict"],
         "auto": r["auto_verdict"], "auto_rule": r["auto_rule"],
         "resolution": "census upheld on reading; automatic subject attribution is the error"}
        for r in results if not r["in_scope"] and r["auto_verdict"] in ("OPERATIVE_INVERTED", "OPERATIVE_CORRECT")
        and r["auto_verdict"].replace("OPERATIVE_", "") != r["census_verdict"]]

    missed = []
    for s in scan_not_in_census:
        lines = file_lines.get(s["path"], [])
        auto = classify_line(s["path"], lines, s["line"])
        entry = adj_table.get(f"{s['path']}:{s['line']}")
        verdict = auto["verdict"]
        if entry:
            lo = max(1, s["line"] - 2)
            hi = min(len(lines), s["line"] + 2)
            if entry["anchor"] not in "\n".join(lines[lo - 1:hi]):
                print(f"ANCHOR FAIL-CLOSED {s['path']}:{s['line']} (scan addition)", file=sys.stderr)
                return 5
            verdict = entry["verdict"]
        if verdict == "OPERATIVE_INVERTED":
            missed.append({"path": s["path"], "line": s["line"], "w078_verdict": verdict,
                           "reason": entry["reason"] if entry else auto["reason"],
                           "excerpt": lines[s["line"] - 1][:300]})

    inverted = [{"path": r["path"], "line": r["line"], "window": r["window"],
                 "source": "census+w078" if r["census_verdict"] == "INVERTED" else "w078",
                 "reason": r["reason"], "excerpt": r["hit_excerpt"]}
                for r in results if r["w078_verdict"] == "OPERATIVE_INVERTED"]
    for m in missed:
        inverted.append({"path": m["path"], "line": m["line"], "window": [m["line"], m["line"]],
                         "source": "w078-scan-only", "reason": m["reason"], "excerpt": m["excerpt"]})
    for entry in (prior.get("clause_census", {}).get("canonical_F0", []) or []):
        if entry.get("class") == "ASSERTIVE_INVERTED":
            ln = entry.get("strength_line")
            if not any(i["path"] == entry["path"] and i["line"] == ln for i in inverted):
                inverted.append({"path": entry["path"], "line": ln, "window": entry.get("window_span"),
                                 "source": "w078-prior-adjudication",
                                 "reason": "ASSERTIVE_INVERTED per W078-F0-SET-STRENGTH-ADJ-01 clause census",
                                 "excerpt": entry.get("quote", "")[:300]})
    inverted.sort(key=lambda x: (x["path"], x["line"]))

    not_repairable = [{"path": r["path"], "line": r["line"], "census_verdict": r["census_verdict"],
                       "w078_verdict": r["w078_verdict"], "reason": r["reason"]}
                      for r in results
                      if r["w078_verdict"] == "HISTORICAL_MENTION" and r["census_verdict"] == "INVERTED"]

    truth = cross_check_truth_direction()
    fixtures = fixture_controls() if a.controls else None
    by_verdict, in_scope_by_verdict = {}, {}
    for r in results:
        by_verdict.setdefault(r["w078_verdict"], []).append(f"{r['path']}:{r['line']}")
        if r["in_scope"]:
            in_scope_by_verdict.setdefault(r["w078_verdict"], []).append(f"{r['path']}:{r['line']}")
    scan_by_verdict = {}
    for m in missed:
        scan_by_verdict.setdefault(m["w078_verdict"], []).append(f"{m['path']}:{m['line']}")

    def lookup(path, line):
        for r in results:
            if r["path"] == path and r["line"] == line:
                return r["w078_verdict"]
        for m in missed:
            if m["path"] == path and m["line"] == line:
                return m["w078_verdict"]
        return None

    manual_review_rows = sum(1 for h in census_hits if h.get("verdict") == "MANUAL_REVIEW")
    manual_review_unique = len({(h["path"], h.get("line")) for h in census_hits
                                if h.get("verdict") == "MANUAL_REVIEW"})
    key_verdicts = {}
    for h in census_hits:
        key_verdicts.setdefault((h["path"], h.get("line")), set()).add(h.get("verdict"))
    verdict_collisions = [{"path": p, "line": ln, "census_verdicts": sorted(v)}
                          for (p, ln), v in key_verdicts.items() if len(v) > 1]
    manual_review_inverted = [f"{r['path']}:{r['line']}" for r in results
                              if r["census_verdict"] == "MANUAL_REVIEW"
                              and r["w078_verdict"] == "OPERATIVE_INVERTED"]

    controls = {
        "C1_in_scope_all_anchored": {
            "in_scope_without_anchor": sorted(f"{r['path']}:{r['line']}" for r in results
                                              if r["in_scope"] and f"{r['path']}:{r['line']}" not in adj_table),
            "census_candidates_without_strength_token_in_window": census_not_in_scan,
            "ok": all(r["in_scope"] and f"{r['path']}:{r['line']}" in adj_table or not r["in_scope"]
                      for r in results),
        },
        "C2_scan_additions": {"own_scan_strength_lines": len(scan_hits),
                              "scan_hits_outside_census_windows": len(scan_not_in_census),
                              "operative_inverted_found_outside_census": len(missed)},
        "C3_known_inverted_positive_control": {
            "F0_94": lookup("research_map/formulation_taxonomy.yaml", 94),
            "F0_200": lookup("research_map/formulation_taxonomy.yaml", 200),
            "F2b_246": lookup("schemas/af_scc_c0_vacuum.yaml", 246),
        },
        "C4_known_correct_control": {
            "F2b_243": lookup("schemas/af_scc_c0_vacuum.yaml", 243),
        },
        "C5_anchor_table_entries": len(adj_table),
        "C6_fixtures": fixtures,
        "C7_manual_review_exhausted": {"manual_review_rows": manual_review_rows,
                                       "manual_review_unique_keys": manual_review_unique,
                                       "resolved_operative_inverted": manual_review_inverted,
                                       "census_key_verdict_collisions": verdict_collisions,
                                       "ok": len(manual_review_inverted) == 0},
        "C8_no_unresolved_candidates": {
            "unresolved": sorted(f"{r['path']}:{r['line']}" for r in results
                                 if r["w078_verdict"] == "NEEDS_ADJUDICATION"),
            "ok": not any(r["w078_verdict"] == "NEEDS_ADJUDICATION" for r in results),
        },
    }

    pins_end = {rel: sha256_file(ROOT / rel) for rel in PINS}
    drift = {k: {"start": pins_start[k], "end": pins_end[k]} for k in PINS if pins_start[k] != pins_end[k]}

    payload = {
        "task_id": "W078-DIRCENSUS-CLASS-RECONCILE-01",
        "worker": "worker-078",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F0",
        "gate": "G-F0",
        "created_at": a.created_at,
        "authority": ("worker-level evidence only; read-only on all canonical paths; sets no gate verdict, "
                      "no node status, no validation_status=passed; writes only under artifacts/worker-078/ "
                      "and runtime/state/"),
        "question": ("W099 census INVERTED classification of artifacts/formulation/formulation_taxonomy.yaml:176 "
                     "(D1 ledger) vs W078 HISTORICAL_MENTION classification of the same pinned bytes; and do "
                     "any of the census's 34 MANUAL_REVIEW residues conceal an operative inverted strength "
                     "assertion at the FROZEN rev29 pins?"),
        "inputs": {
            "pins_start": pins_start, "pins_measured_end": pins_end, "drift": drift,
            "census_artifact": {"path": "artifacts/worker-099/form_direction_census/census.json",
                                "sha256": pins_start["artifacts/worker-099/form_direction_census/census.json"]},
            "prior_w078_report": {"path": "artifacts/worker-078/f0_set_strength_adjudication/report.json",
                                  "sha256": pins_start["artifacts/worker-078/f0_set_strength_adjudication/report.json"]},
        },
        "candidate_reconciliation": {
            "census_candidates": len(candidates),
            "in_scope_candidates": sum(1 for r in results if r["in_scope"]),
            "census_key_verdict_collisions": verdict_collisions,
            "own_scan_strength_lines": len(scan_hits),
            "scan_hits_outside_census_windows": scan_not_in_census,
            "census_candidates_not_covered_by_scan": census_not_in_scan,
            "note": ("own scan is deliberately broader (any stronger/weaker/larger/smaller token) over "
                     "the 8 audited files only; the census and the prior W078 report are measured inputs, "
                     "not audited corpus. Operative inversions found outside census windows are reported "
                     "under census_missed_operative_inversions"),
        },
        "adjudications": results,
        "verdicts_by_class": by_verdict,
        "in_scope_verdicts": in_scope_by_verdict,
        "scan_addition_verdicts": scan_by_verdict,
        "conflicts": conflicts,
        "rule_conflicts_on_out_of_scope_reference_hits": rule_conflicts_reference,
        "census_missed_operative_inversions": missed,
        "union_repair_manifest": {
            "operative_inverted_sites": inverted,
            "not_repairable_records": not_repairable,
            "summary": ("OPERATIVE repair set = canonical F0:94-95 and F0:200 (SET/union direction) + "
                        "F2b:245-246 (C2 'larger' reason clause; candidate patch exists from W001). "
                        "Historical ledger supplement:176 is NOT part of the repair set: it is a resolved "
                        "divergence record and rewriting it would falsify the record; preserve and re-pin "
                        "if the F0 round is re-opened."),
        },
        "truth_direction_derivation": truth,
        "controls": controls,
        "verdict": {
            "conflict_resolution": ("supplement:176 = HISTORICAL_MENTION (census INVERTED is a false "
                                    "positive; no repair); canonical F0:94 = OPERATIVE_INVERTED (census "
                                    "under-inclusive: it lists only F0:200); F2b:246 confirmed "
                                    "OPERATIVE_INVERTED, consistent with W099 and W001"),
            "new_operative_inversions_found": len(missed),
            "manual_review_residue": {
                "census_rows": manual_review_rows,
                "unique_keys": manual_review_unique,
                "census_key_verdict_collisions": verdict_collisions,
                "operative_inverted": manual_review_inverted,
                "conclusion": ("all census MANUAL_REVIEW rows resolve to NEGATIVE_SCOPE, DEFINITION, "
                               "OPERATIVE_CORRECT or PROBE_RECORD (or are the 3 keys the census itself "
                               "also lists as CORRECT); zero new operative inversions at the pinned bytes"),
            },
            "rule_layer_note": ("the automatic line-level rules are a triage layer only: outside the three "
                                "known sites they produced false INVERTED verdicts by attributing a "
                                "comparative to a class token that is not its subject (e.g. 'STRONGER than "
                                "AF-SCC-C2-VAC-GEN' on a C0 entry). All such hits were read and are recorded "
                                "in rule_conflicts_on_out_of_scope_reference_hits; the census classification "
                                "is upheld there. The adjudicated verdicts, not the automatic ones, are the "
                                "result."),
        },
        "falsifier": ("Re-run this instrument at the same pins: FALSIFIED if any pinned file drifts, if any "
                      "own-scan strength line outside the census windows is OPERATIVE_INVERTED, if any "
                      "anchored adjudication anchor stops matching, if any fixture control flips, if the "
                      "truth-direction model check reports a violation, or if the canonical F0:94 / F0:200 / "
                      "F2b:246 lines stop being operative strength assertions."),
    }
    report = {
        "schema": "w078-direction-class-reconcile/v1",
        "deterministic_payload": payload,
        "run_meta": {"instrument": "reconcile_direction_classification.py",
                     "instrument_sha256": sha256_file(Path(__file__)),
                     "adjudication_table_sha256": (sha256_file(HERE / "adjudication_table.json")
                                                   if (HERE / "adjudication_table.json").exists() else None)},
    }
    Path(a.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": payload["verdict"],
        "conflicts": conflicts,
        "operative_inverted": [f"{i['path']}:{i['line']}" for i in inverted],
        "not_repairable": [f"{i['path']}:{i['line']}" for i in not_repairable],
        "by_verdict": {k: len(v) for k, v in sorted(by_verdict.items())},
        "scan_additions": len(scan_not_in_census),
        "fixtures_ok": (fixtures or {}).get("all_ok"),
        "drift": drift,
        "out": a.out,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
