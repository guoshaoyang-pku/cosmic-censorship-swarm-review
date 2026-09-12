#!/usr/bin/env python3
"""W084-R03V2-SCOPE-INDEP-01 independent driver.

Re-executes the 88 cells of W006-R03-SCOPE-01 from preserved bytes and compares
them to the published raw_verdicts.json. Imports no worker-006 code: every tool
is invoked as a subprocess, and the labels/oracle come from PREREGISTRATION.json
written by this verifier before any tool was run.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TASK = os.path.join(ROOT, "artifacts/worker-084/r03v2_scope_indep")
PUB = os.path.join(ROOT, "artifacts/worker-06/r03scope")
SPEC = os.path.join(ROOT, "artifacts/formulation/rule_spec.json")
PY = "/usr/bin/python3"
TIMEOUT = 60


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str):
    print("FATAL:", msg)
    sys.exit(2)


def flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = d
    return out


def main():
    os.makedirs(os.path.join(TASK, "raw"), exist_ok=True)
    pre_path = os.path.join(TASK, "PREREGISTRATION.json")
    pre = json.load(open(pre_path))
    pre_sha = sha256(pre_path)

    # C1 (before): pins
    pin_before = {p: sha256(os.path.join(ROOT, p)) for p in pre["pins"]}
    pin_ok_before = {p: (pin_before[p] == pre["pins"][p]) for p in pre["pins"]}
    if not all(pin_ok_before.values()):
        fail(f"pin drift before run: {[p for p, v in pin_ok_before.items() if not v]}")

    # fixtures + manifest binding
    man_path = os.path.join(PUB, "fixture_manifest.json")
    man = json.load(open(man_path))
    published = json.load(open(os.path.join(PUB, "raw_verdicts.json")))
    fixture_dir = os.path.join(PUB, "fixtures")
    fixture_hashes = {}
    for f in man["fixtures"]:
        fp = os.path.join(fixture_dir, f["fixture"])
        fixture_hashes[f["fixture"]] = sha256(fp)
    fixture_hash_ok = {k: (v == next(x["sha256"] for x in man["fixtures"] if x["fixture"] == k)) for k, v in fixture_hashes.items()}

    # C3: label agreement
    labels = {k: v["label"] for k, v in pre["independent_labels"].items()}
    man_category = {f["fixture"]: f["category"] for f in man["fixtures"]}
    label_agreement = {k: (labels[k] == man_category[k]) for k in labels}

    # C5: mutation target (recursive diff vs declared base)
    import yaml
    bases = {}
    for f in man["fixtures"]:
        b = f["base"]
        if b not in bases:
            bases[b] = yaml.safe_load(open(os.path.join(ROOT, b)))
    mutation_target = {}
    for f in man["fixtures"]:
        doc = yaml.safe_load(open(os.path.join(fixture_dir, f["fixture"])))
        fb, fd = flatten(bases[f["base"]]), flatten(doc)
        keys = set(fb) | set(fd)
        changed = sorted(k for k in keys if fb.get(k) != fd.get(k))
        mutation_target[f["fixture"]] = changed

    # C4: frozen literal oracle
    oracle_accept = set(pre["frozen_literal_oracle_prediction"]["accept"])
    oracle_pred = {f["fixture"]: ("accept" if f["fixture"] in oracle_accept else "reject") for f in man["fixtures"]}

    # execute cells
    candidates = pre["method"]["candidates"]
    canon = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
    cells = []  # fixture cells only; canonicals are controls
    canonical_cells = []
    for cname, tool in candidates.items():
        for f in man["fixtures"]:
            cells.append((cname, tool, f["fixture"], os.path.join(fixture_dir, f["fixture"])))
        for cp in canon:
            canonical_cells.append((cname, tool, "canonical__" + os.path.basename(cp), os.path.join(ROOT, cp)))

    measured = {}
    raw_stdout = {}
    for cname, tool, key, doc in cells + canonical_cells:
        out_json = os.path.join(TASK, "raw", f"{cname}__{key}.json")
        cmd = [PY, os.path.join(ROOT, tool), doc, "--spec", SPEC, "--json", out_json]
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        raw_stdout[f"{cname}__{key}"] = {
            "cmd": " ".join(cmd), "returncode": pr.returncode,
            "stdout": pr.stdout[-4000:], "stderr": pr.stderr[-2000:], "json_written": os.path.exists(out_json),
        }
        if not os.path.exists(out_json):
            fail(f"no json output for {cname} {key}")
        d = json.load(open(out_json))
        measured[f"{cname}__{key}"] = {
            "returncode": pr.returncode,
            "verdict": d.get("verdict"),
            "failed_rules": d.get("failed_rules", []),
            "doc_sha256": d.get("doc_sha256"),
            "rule_verdicts": {c.get("rule"): c.get("verdict") for c in d.get("checks", [])},
            "failed_detail": {c.get("rule"): c.get("detail") for c in d.get("checks", []) if c.get("verdict") == "fail"},
        }

    # C2: compare to published (all 88 cells)
    mismatches = []
    for cname in candidates:
        for f in man["fixtures"]:
            key = f["fixture"]
            pub = published[cname][key]
            m = measured[f"{cname}__{key}"]
            for field in ("returncode", "verdict", "doc_sha256"):
                if pub.get(field) != m[field]:
                    mismatches.append({"candidate": cname, "cell": key, "field": field, "published": pub.get(field), "measured": m[field]})
            if list(pub.get("failed_rules", [])) != list(m["failed_rules"]):
                mismatches.append({"candidate": cname, "cell": key, "field": "failed_rules", "published": pub.get("failed_rules"), "measured": m["failed_rules"]})
        for cp in canon:
            key = "canonical__" + os.path.basename(cp)
            pub = published[cname][key]
            m = measured[f"{cname}__{key}"]
            for field in ("returncode", "verdict", "doc_sha256"):
                if pub.get(field) != m[field]:
                    mismatches.append({"candidate": cname, "cell": key, "field": field, "published": pub.get(field), "measured": m[field]})
            if list(pub.get("failed_rules", [])) != list(m["failed_rules"]):
                mismatches.append({"candidate": cname, "cell": key, "field": "failed_rules", "published": pub.get("failed_rules"), "measured": m["failed_rules"]})

    total_cells = len(cells) + len(canonical_cells)

    # C4 check
    oracle_check = {}
    for f in man["fixtures"]:
        m = measured[f"frozen__{f['fixture']}"]
        oracle_check[f["fixture"]] = {"predicted": oracle_pred[f["fixture"]], "measured": m["verdict"], "agree": oracle_pred[f["fixture"]] == m["verdict"]}

    # C6 canonical control
    canonical_check = {}
    for cname in candidates:
        canonical_check[cname] = {}
        for cp in canon:
            key = "canonical__" + os.path.basename(cp)
            m = measured[f"{cname}__{key}"]
            canonical_check[cname][os.path.basename(cp)] = {"verdict": m["verdict"], "failed_rules": m["failed_rules"]}

    # C7 counts under the verifier's independent labels
    counts = {}
    for cname in candidates:
        fp = [f["fixture"] for f in man["fixtures"] if labels[f["fixture"]] == "pos" and measured[f"{cname}__{f['fixture']}"]["verdict"] != "accept"]
        fn = [f["fixture"] for f in man["fixtures"] if labels[f["fixture"]] == "neg" and measured[f"{cname}__{f['fixture']}"]["verdict"] == "accept"]
        ctrl = measured[f"{cname}__ctrl_canonical_wcc.yaml"]["verdict"]
        edges = {f["fixture"]: measured[f"{cname}__{f['fixture']}"]["verdict"] for f in man["fixtures"] if labels[f["fixture"]] == "edge"}
        non_r03 = {k: v["failed_rules"] for k, v in measured.items() if k.startswith(cname + "__") and [r for r in v["failed_rules"] if r != "R03"]}
        counts[cname] = {"fp": len(fp), "fp_fixtures": fp, "fn": len(fn), "fn_fixtures": fn,
                         "control_verdict": ctrl, "scope_safe": len(fp) == 0 and len(fn) == 0 and ctrl == "accept",
                         "edge_verdicts": edges, "non_R03_failed_rules": non_r03}

    # C8 over-reject residue
    over_reject = {}
    for name in ("edge_comma_coordinated.yaml", "edge_long_span.yaml"):
        over_reject[name] = {c: measured[f"{c}__{name}"]["verdict"] for c in candidates}

    # pin check after
    pin_after = {p: sha256(os.path.join(ROOT, p)) for p in pre["pins"]}
    pin_ok_after = {p: (pin_after[p] == pre["pins"][p]) for p in pre["pins"]}

    out = {
        "task_id": pre["task_id"],
        "preregistration_sha256": pre_sha,
        "total_cells": total_cells,
        "pin_check_before": pin_ok_before,
        "pin_check_after": pin_ok_after,
        "fixture_hash_ok": fixture_hash_ok,
        "label_agreement_with_manifest": label_agreement,
        "mutation_targets": mutation_target,
        "oracle_check": oracle_check,
        "canonical_check": canonical_check,
        "recomputed_counts": counts,
        "over_reject_residue": over_reject,
        "cell_mismatches_vs_published": mismatches,
        "mismatch_count": len(mismatches),
        "raw_stdout": raw_stdout,
    }
    json.dump(out, open(os.path.join(TASK, "reproduction.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({
        "mismatches": len(mismatches),
        "label_disagreements": [k for k, v in label_agreement.items() if not v],
        "oracle_disagreements": [k for k, v in oracle_check.items() if not v["agree"]],
        "mutation_path_violations": {k: v for k, v in mutation_target.items() if k != "ctrl_canonical_wcc.yaml" and v != ["quantifiers.formal"]},
        "counts": {c: {"fp": counts[c]["fp"], "fn": counts[c]["fn"], "scope_safe": counts[c]["scope_safe"]} for c in counts},
        "non_r03": {c: counts[c]["non_R03_failed_rules"] for c in counts if counts[c]["non_R03_failed_rules"]},
        "pins_after_ok": all(pin_ok_after.values()),
    }, indent=1))
    return 0 if (len(mismatches) == 0 and all(pin_ok_after.values())) else 1


if __name__ == "__main__":
    sys.exit(main())
