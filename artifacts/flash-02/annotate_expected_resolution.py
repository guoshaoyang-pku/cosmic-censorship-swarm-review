#!/usr/bin/env python3
"""One-off annotator: add `expected_resolution` and `open` to every case in
schemas/taxonomy_cases.jsonl so that each case has exactly ONE intended gate action.

Resolution vocabulary:
  unique_class:<class_id>              positive: accept and classify to exactly this class
  reject_misfiled:target=<class_id>    negative: reject the filing; evidence supports <class_id>
  reject_new_class_required            negative: reject; no class in the taxonomy accepts the record
  reject_split_required                negative: reject; the record must be split into >=2 class records
  reject_leak:<rule_id>                negative: reject with the named leak rule (textual/semantic)

`open: true` marks cases whose correct handling exposes an OPEN taxonomy gap (CG2) or a
required split; they are decidable gate inputs but the taxonomy cannot absorb them, so the
formulation lead must adjudicate. They are reported as open cases, not silently resolved.
"""
import json
from pathlib import Path

P = Path("schemas/taxonomy_cases.jsonl")
lines = [l for l in P.read_text().splitlines() if l.strip()]
out = []
n_open = 0
for line in lines:
    c = json.loads(line)
    if c.get("record_type") != "case":
        out.append(json.dumps(c, ensure_ascii=False))
        continue
    if c["polarity"] == "positive":
        c["open"] = False
        c["expected_resolution"] = f"unique_class:{c['class_id']}"
    else:
        kind = c["leak_kind"]
        exp = c.get("expected_classification")
        if kind == "axis":
            if exp == "NO_CLASS_IN_TAXONOMY":
                c["open"], c["expected_resolution"] = True, "reject_new_class_required"
            else:
                c["open"] = False
                c["expected_resolution"] = f"reject_misfiled:target={exp}"
        elif kind == "out_of_vocabulary":
            c["open"], c["expected_resolution"] = True, "reject_new_class_required"
        elif kind == "lexical":
            c["open"] = False
            c["expected_resolution"] = f"reject_leak:{c['expected_leak_rule']}"
        elif kind == "semantic":
            if str(exp).startswith("AMBIGUOUS"):
                c["open"], c["expected_resolution"] = True, "reject_split_required"
            else:
                c["open"] = False
                c["expected_resolution"] = f"reject_leak:{c['expected_leak_rule']}"
        else:
            raise SystemExit(f"unknown leak_kind {kind!r} in {c['case_id']}")
    n_open += 1 if c["open"] else 0
    out.append(json.dumps(c, ensure_ascii=False))
P.write_text("\n".join(out) + "\n")
print(f"annotated {len(out) - 1} cases; open={n_open}")
