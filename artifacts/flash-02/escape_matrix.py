#!/usr/bin/env python3
"""Independent tiered-gate simulation over schemas/taxonomy_cases.jsonl.

Deliberately does NOT import check_taxonomy_cases.py: this is a second implementation used
to replicate the axis classification and to measure the escape rate of weaker gates.

Tiers
  T1 axis+vocabulary: exact 7-axis match against the taxonomy + field_vocabulary membership.
  T2 T1 + lexical: also applies every catalog rule of kind 'lexical' as a regex on the statement.
  T3 T2 + semantic adjudication: assumes a reviewer catches every remaining semantic leak.

Output: artifacts/flash-02/escape_matrix.json (counts + escaped case ids per tier).
"""
import json
import re
from pathlib import Path

import yaml

AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]

tax = yaml.safe_load(Path("research_map/formulation_taxonomy.yaml").read_text())
classes = {cid: {k: cls["axes"].get(k) for k in AXES} for cid, cls in tax["classes"].items()}
vocab = {k: v.get("allowed", []) for k, v in tax["field_vocabulary"].items()}
catalog = json.loads(Path("artifacts/flash-02/leak_rule_catalog.json").read_text())
lexical_rules = [(r["rule_id"], r["pattern"]) for r in catalog["rules"]
                 if r.get("kind") == "lexical" and r.get("pattern")]

# taxonomy rev2 G3 semantics: strip ^ { } _ and whitespace, then match
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def merged_match(text):
    return bool(MERGED_RE.search(text)) or bool(MERGED_RE.search(re.sub(r"[\^_{}\s]", "", text)))

cases = [json.loads(l) for l in Path("schemas/taxonomy_cases.jsonl").read_text().splitlines()
         if l.strip()]
cases = [c for c in cases if c.get("record_type") == "case"]


def axis_ok(av):
    if av is None:
        return False
    for k in AXES:
        if k not in av or av[k] not in vocab.get(k, []):
            return False
    return True


def resolve(av):
    return sorted(cid for cid, a in classes.items() if all(a.get(k) == av.get(k) for k in AXES))


def t1_reject(c):
    """Return True if the axis+vocabulary gate rejects this case."""
    av = c.get("axis_vector")
    if not axis_ok(av):
        return True
    r = resolve(av)
    filed = c.get("as_filed_class_id")
    if filed not in classes:
        return True          # composite / unclassifiable filing
    return r != [filed]


def t2_reject(c):
    if t1_reject(c):
        return True
    stmt = c.get("statement", "")
    for rid, pat in lexical_rules:
        if rid == "G3-MERGED-REG-LITERAL":
            if merged_match(stmt):
                return True
        elif re.search(pat, stmt):
            return True
    if c.get("text_pattern") and re.search(c["text_pattern"], stmt):
        return True
    return False


rows = []
for c in cases:
    pol = c["polarity"]
    exp_accept = pol == "positive"
    r1 = not t1_reject(c)          # gate accepts
    r2 = not t2_reject(c)
    r3 = exp_accept                # perfect semantic gate: rejects every negative
    ok1 = (r1 == exp_accept)
    ok2 = (r2 == exp_accept)
    ok3 = (r3 == exp_accept)
    rows.append({"case_id": c["case_id"], "polarity": pol,
                 "filed": c.get("as_filed_class_id"), "leak_kind": c.get("leak_kind"),
                 "expected_resolution": c.get("expected_resolution"),
                 "T1_accept": r1, "T1_correct": ok1,
                 "T2_accept": r2, "T2_correct": ok2, "T3_correct": ok3})

summary = {}
for tier in ("T1", "T2", "T3"):
    key = f"{tier}_correct"
    neg_escaped = [r["case_id"] for r in rows if r["polarity"] == "negative" and not r[key]]
    pos_wrong = [r["case_id"] for r in rows if r["polarity"] == "positive" and not r[key]]
    n_neg = sum(1 for r in rows if r["polarity"] == "negative")
    summary[tier] = {
        "positives_correct": sum(1 for r in rows if r["polarity"] == "positive" and r[key]),
        "positives_total": sum(1 for r in rows if r["polarity"] == "positive"),
        "negatives_rejected": n_neg - len(neg_escaped),
        "negatives_total": n_neg,
        "escaped_negatives": neg_escaped,
        "wrongly_rejected_positives": pos_wrong,
        "escape_rate": round(len(neg_escaped) / n_neg, 4),
    }

out = {
    "artifact_id": "artifacts/flash-02/escape_matrix.json",
    "implementation": "independent of check_taxonomy_cases.py",
    "gate_tiers": {
        "T1": "axis + field_vocabulary",
        "T2": "T1 + catalog lexical patterns",
        "T3": "T2 + semantic adjudication (upper bound)",
    },
    "summary": summary,
    "rows": rows,
    "interpretation": "T1/T2 escape lists are the measured blind spots of purely mechanical gates; "
                      "they must be routed to a semantic gate plus reviewer. T3 is an upper bound, "
                      "not an implemented gate.",
}
Path("artifacts/flash-02/escape_matrix.json").write_text(json.dumps(out, indent=2) + "\n")

for tier, s in summary.items():
    print(f"{tier}: positives {s['positives_correct']}/{s['positives_total']}, "
          f"negatives rejected {s['negatives_rejected']}/{s['negatives_total']}, "
          f"escape_rate {s['escape_rate']}")
    if s["escaped_negatives"]:
        print(f"    escaped: {s['escaped_negatives']}")
    if s["wrongly_rejected_positives"]:
        print(f"    wrongly rejected positives: {s['wrongly_rejected_positives']}")
