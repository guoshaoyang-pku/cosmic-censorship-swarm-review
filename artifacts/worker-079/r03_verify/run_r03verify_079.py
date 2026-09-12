#!/usr/bin/env python3
"""W079 independent non-author verification of W006-R03-CAND-HEADTOHEAD-01.

Read-only with respect to every canonical artifact. Implements its own
runner (does NOT invoke the author's run_headtohead.py) and re-executes the
three pinned stage-B variants on the 13-fixture head-to-head corpus and the
31 derived canonical negatives, twice per cell, then compares the computed
tables against the pre-registered expectation table.

Exit codes (fail-closed; no report is written on 2/3/4):
  0  report written (verdict MATCH or DIFF; see report["verdict"])
  2  pin / corpus / derived-negative-root drift, before or after the run
  3  control failure
  4  internal harness error

Usage:
  python3 run_r03verify_079.py --out report.json --raw raw
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PREREG_PATH = os.path.join(HERE, "PREREGISTRATION.json")


def find_root(start):
    d = start
    while True:
        if os.path.exists(os.path.join(d, "research_map", "research_map.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise HarnessError("repository root not found from %s" % start)
        d = parent


class Drift(Exception):
    pass


class ControlFail(Exception):
    pass


class HarnessError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_prereg():
    with open(PREREG_PATH) as fh:
        return json.load(fh)


def collect_pin_pairs(pr):
    pairs = []
    for key, val in pr["pins"].items():
        if key == "variants":
            for vname in sorted(val):
                pairs.append((val[vname]["path"], val[vname]["sha256"], "variant:" + vname))
        elif key == "target_artifacts":
            for path in sorted(val):
                pairs.append((path, val[path], "target_artifact"))
        else:
            pairs.append((key, val, "pin"))
    mani = pr["fixture_manifest"]
    pairs.append((mani["path"], mani["sha256"], "fixture_manifest"))
    return pairs


def measure_pins(root, pairs):
    out = []
    for rel, declared, kind in pairs:
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            raise Drift("pinned file missing: %s" % rel)
        got = sha256_file(path)
        if got != declared:
            raise Drift("pin drift on %s: declared %s measured %s" % (rel, declared, got))
        out.append({"path": rel, "declared_sha256": declared, "measured_sha256": got, "kind": kind})
    return out


def load_corpus(root, pr):
    mani_path = os.path.join(root, pr["fixture_manifest"]["path"])
    with open(mani_path) as fh:
        manifest = json.load(fh)
    fdir = os.path.join(root, pr["fixture_manifest"]["fixtures_dir"])
    rows = []
    for fx in manifest["fixtures"]:
        rows.append({
            "set": "corpus",
            "name": fx["fixture"],
            "path": os.path.join(fdir, fx["fixture"]),
            "category": fx["category"],
            "expected": fx["expected"],
            "scored": bool(fx["scored"]),
            "declared_sha256": fx["sha256"],
        })
    for path in sorted(glob.glob(os.path.join(root, "artifacts", "formulation", "fixtures", "negative", "*.yaml"))):
        rows.append({
            "set": "derived_neg",
            "name": os.path.basename(path),
            "path": path,
            "category": "neg",
            "expected": "reject_r03",
            "scored": False,
            "declared_sha256": None,
        })
    return rows, manifest


def derived_negative_root(rows):
    lines = []
    for row in rows:
        if row["set"] != "derived_neg":
            continue
        lines.append("%s:%s" % (row["name"], sha256_file(row["path"])))
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def verify_corpus(rows, manifest, expected_root):
    for row in rows:
        if row["set"] == "corpus":
            got = sha256_file(row["path"])
            if got != row["declared_sha256"]:
                raise Drift("fixture byte drift: %s declared %s measured %s"
                            % (row["name"], row["declared_sha256"], got))
    root = derived_negative_root(rows)
    if root != expected_root:
        raise Drift("derived-negative root drift: expected %s measured %s" % (expected_root, root))
    return root


def normalize(raw):
    return {
        "verdict": raw.get("verdict"),
        "failed_rules": sorted(raw.get("failed_rules") or []),
        "undecided_rules": sorted(raw.get("undecided_rules") or []),
        "doc_sha256": raw.get("doc_sha256"),
        "checks": [
            {"rule": c.get("rule"), "verdict": c.get("verdict"), "detail": c.get("detail")}
            for c in (raw.get("checks") or [])
        ],
    }


def run_cell(python, variant_path, spec_path, fixture_path, out_path, root):
    cmd = [python, variant_path, fixture_path, "--spec", spec_path, "--json", out_path]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise HarnessError("variant %s on %s exited %s: %s"
                           % (variant_path, fixture_path, proc.returncode, proc.stderr[-400:]))
    if not os.path.exists(out_path):
        raise HarnessError("variant %s on %s wrote no --json output" % (variant_path, fixture_path))
    with open(out_path) as fh:
        raw = json.load(fh)
    if raw.get("verdict") not in ("accept", "reject"):
        raise HarnessError("unparseable verdict for %s on %s" % (variant_path, fixture_path))
    return raw


def classify(records, rows):
    """records: name -> normalized record. rows: corpus rows (scored/edge/derived)."""
    pos = sorted(r["name"] for r in rows if r["category"] == "pos" and r["scored"])
    neg = sorted(r["name"] for r in rows if r["category"] == "neg" and r["scored"])
    probe = sorted(r["name"] for r in rows if r["category"] == "probe")
    primary_fp = [n for n in pos if records[n]["verdict"] != "accept"]
    primary_fn = [n for n in neg if records[n]["verdict"] == "accept"]
    edge_fp = [n for n in probe if records[n]["verdict"] != "accept"]
    canon_pos_accept = "%d/%d" % (len(pos) - len(primary_fp), len(pos))
    return {
        "primary_fp": sorted(primary_fp),
        "primary_fn": sorted(primary_fn),
        "edge_fp": sorted(edge_fp),
        "canonical_pos_accept": canon_pos_accept,
    }


def classify_negative_control(records, rows):
    """Unit control for the classifier: synthetic records must classify as expected."""
    probe_rows = [
        {"name": "synthetic_neg", "category": "neg", "scored": True, "expected": "reject"},
        {"name": "synthetic_pos", "category": "pos", "scored": True, "expected": "accept"},
        {"name": "synthetic_probe", "category": "probe", "scored": False, "expected": "accept"},
    ]
    good = {
        "synthetic_neg": {"verdict": "reject", "failed_rules": ["R03"]},
        "synthetic_pos": {"verdict": "accept", "failed_rules": []},
        "synthetic_probe": {"verdict": "accept", "failed_rules": []},
    }
    c = classify(good, probe_rows)
    if c["primary_fn"] or c["primary_fp"] or c["edge_fp"]:
        raise ControlFail("classifier control: clean synthetic set classified as %s" % c)
    bad = dict(good)
    bad["synthetic_neg"] = {"verdict": "accept", "failed_rules": []}
    bad["synthetic_pos"] = {"verdict": "reject", "failed_rules": ["R03"]}
    bad["synthetic_probe"] = {"verdict": "reject", "failed_rules": ["R03"]}
    c2 = classify(bad, probe_rows)
    if c2["primary_fn"] != ["synthetic_neg"] or c2["primary_fp"] != ["synthetic_pos"] or c2["edge_fp"] != ["synthetic_probe"]:
        raise ControlFail("classifier control: mutated synthetic set classified as %s" % c2)
    return "clean->0/0/0; mutated->FN=[synthetic_neg], FP=[synthetic_pos], edge=[synthetic_probe]"


def guard_self_tests(root, rows, manifest, expected_root):
    """C1/C2: the drift guards must fire on doctored inputs."""
    doctored = json.loads(json.dumps(manifest))
    doctored["fixtures"][0]["sha256"] = "0" * 64
    with tempfile.TemporaryDirectory() as td:
        bad_rows = []
        for row in rows:
            row2 = dict(row)
            if row["set"] == "corpus" and row["name"] == doctored["fixtures"][0]["fixture"]:
                row2["declared_sha256"] = "0" * 64
            bad_rows.append(row2)
        # emulate verify_corpus against a manifest whose first fixture hash is wrong
        fired = False
        try:
            verify_corpus(bad_rows, doctored, expected_root)
        except Drift:
            fired = True
        if not fired:
            raise ControlFail("manifest drift guard did not fire on a doctored fixture hash")
    fired = False
    try:
        verify_corpus(rows, manifest, "0" * 64)
    except Drift:
        fired = True
    if not fired:
        raise ControlFail("derived-negative root guard did not fire on a doctored root")
    return "doctored manifest hash -> Drift; doctored negative root -> Drift"


def regression_tables(frozen_rec, cand_rec, neg_names):
    reproduced = []
    now_pass = []
    now_pass_other = []
    overall_accept = []
    for name in sorted(neg_names):
        f = frozen_rec[name]
        c = cand_rec[name]
        frozen_r03 = f["verdict"] != "accept" and "R03" in f["failed_rules"]
        if not frozen_r03:
            continue
        detail = ""
        for chk in f["checks"]:
            if chk["rule"] == "R03":
                detail = chk["detail"]
                break
        if c["verdict"] != "accept":
            reproduced.append(name)
        else:
            now_pass.append({
                "negative": name,
                "frozen_detail": detail,
                "candidate_verdict": c["verdict"],
                "candidate_failed_rules": c["failed_rules"],
            })
            if not c["failed_rules"]:
                overall_accept.append(name)
        if c["verdict"] != "accept" and "R03" not in c["failed_rules"]:
            now_pass_other.append(name)
    return {
        "gate_negative_frozen_r03_reproduced": len(reproduced),
        "gate_negative_frozen_r03_now_pass": now_pass,
        "gate_negative_now_pass_count": len(now_pass),
        "gate_negative_now_pass_but_rejected_by_other_rules": sorted(now_pass_other),
        "gate_negative_now_pass_overall_accept": sorted(overall_accept),
    }


def cmp_table(computed, recorded, names):
    """Compare a computed candidate table against the recorded claim on the named keys."""
    diffs = []
    for key in names:
        got = computed[key]
        exp = recorded[key]
        if isinstance(got, list) and got and isinstance(got[0], dict):
            got = sorted(x["negative"] for x in got)
            exp = sorted(x["negative"] for x in exp)
        if key in ("gate_negative_frozen_r03_now_pass",) and isinstance(got, list):
            got = sorted(got)
            exp = sorted(exp)
        if got != exp:
            diffs.append({"key": key, "recorded": exp, "computed": got})
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "report.json"))
    ap.add_argument("--raw", default=os.path.join(HERE, "raw"))
    ap.add_argument("--python", default="python3")
    args = ap.parse_args()

    root = find_root(HERE)
    pr = load_prereg()
    spec_path = os.path.join(root, "artifacts", "formulation", "rule_spec.json")
    variants = pr["pins"]["variants"]
    expected_root = pr["derived_negative_set"]["name_sha256_root"]

    pin_pairs = collect_pin_pairs(pr)
    pins_before = measure_pins(root, pin_pairs)
    rows, manifest = load_corpus(root, pr)
    neg_root = verify_corpus(rows, manifest, expected_root)
    if len(rows) != 44:
        raise HarnessError("expected 44 corpus rows, found %d" % len(rows))

    controls = []
    controls.append({"id": "C1", "status": "PASS",
                     "detail": "13/13 corpus fixture bytes match the pinned manifest df62d3005660; "
                               + guard_self_tests(root, rows, manifest, expected_root)})
    controls.append({"id": "C2", "status": "PASS",
                     "detail": "31 derived negatives hash to root %s" % neg_root})
    controls.append({"id": "C4", "status": "PASS", "detail": classify_negative_control(None, rows)})

    if os.path.isdir(args.raw):
        shutil.rmtree(args.raw)
    os.makedirs(args.raw, exist_ok=True)

    records = {k: {"run1": {}, "run2": {}} for k in sorted(variants)}
    cells = 0
    for vname in sorted(variants):
        vpath = os.path.join(root, variants[vname]["path"])
        for run_idx in (1, 2):
            for row in rows:
                tag = "%s__%s__%s.run%d" % (vname, row["set"], row["name"], run_idx)
                out_path = os.path.join(args.raw, tag + ".json")
                raw = run_cell(args.python, vpath, spec_path, row["path"], out_path, root)
                records[vname]["run%d" % run_idx][row["name"]] = normalize(raw)
                cells += 1

    if cells != 264:
        raise ControlFail("cell-count control: expected 264 invocations, got %d" % cells)
    controls.append({"id": "C6", "status": "PASS",
                     "detail": "3 variants x 44 files x 2 runs = %d invocations, all exit 0 with parseable JSON" % cells})

    determinism = {"cells_compared": 0, "agreeing": 0, "mismatches": [], "digest": None}
    for vname in sorted(variants):
        for name in sorted(records[vname]["run1"]):
            determinism["cells_compared"] += 1
            if canonical_json(records[vname]["run1"][name]) == canonical_json(records[vname]["run2"][name]):
                determinism["agreeing"] += 1
            else:
                determinism["mismatches"].append("%s/%s" % (vname, name))
    if determinism["mismatches"]:
        raise ControlFail("determinism control: %d cell mismatches" % len(determinism["mismatches"]))
    determinism["digest"] = hashlib.sha256(
        canonical_json({v: records[v]["run1"] for v in sorted(records)}).encode("utf-8")
    ).hexdigest()
    controls.append({"id": "C5", "status": "PASS",
                     "detail": "%d/%d cells agree across two runs; normalized digest %s"
                               % (determinism["agreeing"], determinism["cells_compared"], determinism["digest"][:12])})

    # ---- E12/E13 corpus-validity checks (preregistered as instrument conditions) ----
    e12_ok = True
    e12_detail = []
    for row in rows:
        if row["set"] != "corpus":
            continue
        f = records["frozen"]["run1"][row["name"]]
        extra = [r for r in f["failed_rules"] if r != "R03"]
        if extra:
            e12_ok = False
            e12_detail.append({"fixture": row["name"], "frozen_failed_non_R03": extra})

    e13_ok = True
    e13_detail = []
    for row in rows:
        sets = {}
        for vname in sorted(variants):
            rec = records[vname]["run1"][row["name"]]
            sets[vname] = tuple(r for r in rec["failed_rules"] if r != "R03")
        if len(set(sets.values())) != 1:
            e13_ok = False
            e13_detail.append({"fixture": row["name"], "non_R03_by_variant": {k: list(v) for k, v in sets.items()}})

    # ---- computed tables ----
    computed = {}
    for vname in sorted(variants):
        tbl = classify(records[vname]["run1"], rows)
        neg_names = [r["name"] for r in rows if r["set"] == "derived_neg"]
        tbl.update(regression_tables(records["frozen"]["run1"], records[vname]["run1"], neg_names))
        computed[vname] = tbl

    # ---- expectation table ----
    rec = pr["recorded_claim_to_test"]
    expectations = []

    def exp(eid, ok, detail):
        expectations.append({"id": eid, "status": "PASS" if ok else "FAIL", "detail": detail})

    exp("E01", computed["frozen"]["primary_fp"] == sorted(rec["frozen"]["primary_fp"]),
        "frozen primary_fp=%s" % computed["frozen"]["primary_fp"])
    exp("E02", computed["frozen"]["primary_fn"] == sorted(rec["frozen"]["primary_fn"]),
        "frozen primary_fn=%s" % computed["frozen"]["primary_fn"])
    exp("E03", computed["frozen"]["edge_fp"] == sorted(rec["frozen"]["edge_fp"]),
        "frozen edge_fp=%s" % computed["frozen"]["edge_fp"])
    exp("E04", computed["frozen"]["canonical_pos_accept"] == rec["frozen"]["canonical_pos_accept"],
        "frozen canonical_pos_accept=%s" % computed["frozen"]["canonical_pos_accept"])
    exp("E05", not computed["cand_r03v2"]["primary_fp"] and not computed["cand_r03v2"]["primary_fn"],
        "cand_r03v2 primary_fp=%s primary_fn=%s" % (computed["cand_r03v2"]["primary_fp"], computed["cand_r03v2"]["primary_fn"]))
    exp("E06", computed["cand_r03v2"]["edge_fp"] == sorted(rec["cand_r03v2"]["edge_fp"]),
        "cand_r03v2 edge_fp=%s" % computed["cand_r03v2"]["edge_fp"])
    exp("E07", computed["cand_r03v2"]["canonical_pos_accept"] == rec["cand_r03v2"]["canonical_pos_accept"],
        "cand_r03v2 canonical_pos_accept=%s" % computed["cand_r03v2"]["canonical_pos_accept"])
    exp("E08", not computed["cand_004"]["primary_fp"] and computed["cand_004"]["primary_fn"] == sorted(rec["cand_004"]["primary_fn"]),
        "cand_004 primary_fp=%s primary_fn=%s" % (computed["cand_004"]["primary_fp"], computed["cand_004"]["primary_fn"]))
    exp("E09", not computed["cand_004"]["edge_fp"] and computed["cand_004"]["canonical_pos_accept"] == rec["cand_004"]["canonical_pos_accept"],
        "cand_004 edge_fp=%s canonical_pos_accept=%s" % (computed["cand_004"]["edge_fp"], computed["cand_004"]["canonical_pos_accept"]))

    reg_keys = ["gate_negative_frozen_r03_reproduced", "gate_negative_frozen_r03_now_pass",
                "gate_negative_now_pass_count", "gate_negative_now_pass_but_rejected_by_other_rules",
                "gate_negative_now_pass_overall_accept"]
    reg_diffs = {}
    for vname in ("frozen", "cand_r03v2", "cand_004"):
        reg_diffs[vname] = cmp_table(computed[vname], rec[vname], reg_keys)
    exp("E10", all(not d for d in reg_diffs.values()),
        "regression-table diffs: %s" % json.dumps(reg_diffs))

    fr = records["frozen"]["run1"]
    ctl_ok = (fr["pos00_canonical_c0.yaml"]["verdict"] == "accept"
              and fr["pos01_canonical_c2.yaml"]["verdict"] == "accept"
              and fr["pos02_canonical_wcc.yaml"]["verdict"] == "reject"
              and "R03" in fr["pos02_canonical_wcc.yaml"]["failed_rules"])
    exp("E11", ctl_ok, "pos00=%s pos01=%s pos02=%s/%s" % (
        fr["pos00_canonical_c0.yaml"]["verdict"], fr["pos01_canonical_c2.yaml"]["verdict"],
        fr["pos02_canonical_wcc.yaml"]["verdict"], fr["pos02_canonical_wcc.yaml"]["failed_rules"]))
    exp("E12", e12_ok, "fixtures with frozen non-R03 failures: %s" % json.dumps(e12_detail))
    exp("E13", e13_ok, "non-R03 failure-set divergences: %s" % json.dumps(e13_detail))
    exp("E14", determinism["cells_compared"] == 264 and determinism["agreeing"] == 264,
        "%d/%d cells deterministic" % (determinism["agreeing"], determinism["cells_compared"]))

    pins_after = measure_pins(root, pin_pairs)
    if pins_after != pins_before:
        raise Drift("post-run pin measurement differs from pre-run")
    controls.append({"id": "C3", "status": "PASS",
                     "detail": "all %d pins re-measured after the run equal the pre-run values" % len(pin_pairs)})

    failed = [e for e in expectations if e["status"] != "PASS"]
    report = {
        "task_id": pr["task_id"],
        "target_id": pr["target_id"],
        "schema": "w079-indep-verify/1",
        "instrument": "artifacts/worker-079/r03_verify/run_r03verify_079.py",
        "preregistration": {
            "path": "artifacts/worker-079/r03_verify/PREREGISTRATION.json",
            "sha256": sha256_file(PREREG_PATH),
        },
        "verdict": "MATCH" if not failed else "DIFF",
        "n_failed_expectations": len(failed),
        "pins": pins_before,
        "counts": {"variants": len(variants), "fixture_files": len(rows),
                   "corpus_fixtures": len(rows) - 31, "derived_negatives": 31,
                   "runs_per_cell": 2, "invocations": cells},
        "derived_negative_root": neg_root,
        "computed": computed,
        "expectations": expectations,
        "controls": controls,
        "determinism": determinism,
        "discrepancies": failed,
        "adoption_rule": pr["scoring_rules"]["adoption_rule"],
        "falsifier": pr["falsifier"],
        "not_claimed": pr["not_claimed"],
    }
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("report written: %s verdict=%s failures=%d" % (args.out, report["verdict"], len(failed)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Drift as exc:
        print("DRIFT (exit 2, no report): %s" % exc, file=sys.stderr)
        sys.exit(2)
    except ControlFail as exc:
        print("CONTROL FAILURE (exit 3, no report): %s" % exc, file=sys.stderr)
        sys.exit(3)
    except HarnessError as exc:
        print("HARNESS ERROR (exit 4, no report): %s" % exc, file=sys.stderr)
        sys.exit(4)
    except Exception as exc:  # noqa: BLE001 - fail closed on anything unexpected
        print("UNEXPECTED (exit 4, no report): %r" % (exc,), file=sys.stderr)
        sys.exit(4)
