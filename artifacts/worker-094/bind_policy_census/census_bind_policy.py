#!/usr/bin/env python3
"""W094H-BIND-POLICY-01 - binding-field policy sensitivity of review coverage.

Class-bound task (primary class AF-SCC-C0-VAC-GEN, the CF-31 carrier; F2b/rev29
pin b2ab6acb2bbe). Read-only census of reviews/**/*.json at one decision instant.

Question: CF-31 proved that the F2b accept count at one pin flips between 3 and 0
depending on whether a review's pin is read from `reviewed_sha256` or from
`artifact_sha256`. Does the same carrier-policy dependence cross any *declared*
coverage threshold at the other frozen gate pins (F0, F1, F2a, L0, G-NUM
protocol)?

Method
------
1. Snapshot every reviews/**/*.json with sha256 + mtime; corpus digest is the
   sha256 of the sorted "path\0sha256\n" stream (mtime recorded, not hashed).
2. Extract every string leaf in each review JSON that *contains* a pin's 12-hex
   prefix, with its JSON path. Binding carriers are then named leaf-key classes:
     P_REVIEWED : reviewed_sha256
     P_ARTIFACT : artifact_sha256
     P_TARGET   : target_id | artifact | reviewed_artifact   (path#hash form)
     P_FROZEN   : reviewed_frozen_sha256 | frozen_sha256 | frozen_artifact_sha256
     P_BIND     : union of the four named carriers (the "any binding carrier" policy)
     P_MENTION  : any string leaf anywhere (UPPER BOUND: includes prose mentions and
                  cross-target evidence quotes; diagnostic only, never a coverage count)
3. Coverage per (pin, policy) = distinct reviewers with >=1 accept file bound under
   that policy, with raw, latest-per-reviewer (latest-wins) and non-author
   full-schema variants. An accept is independent iff reviewer != author_of_record
   and its file does not declare counts_as_independent=false.
4. Threshold crossing is decided on the declared criterion using the non-author
   full-schema accept count, compared across P_REVIEWED / P_ARTIFACT / P_BIND.

Determinism: pure read-only over the corpus + pins; no network, no writes outside
this artifact directory. C10 re-runs the census in-process; C11 re-hashes the
corpus at exit.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REVIEW_ROOT = os.path.join(ROOT, "reviews")
OUT_DIR = os.path.join(ROOT, "artifacts", "worker-094", "bind_policy_census", "run")

PINS = {
    "F0": {
        "path": "research_map/formulation_taxonomy.yaml",
        "sha256": "0abb9ed8a961",
        "class": "GLOBAL",
        "criterion": "G-F0: >=2 distinct independent accepts bind the canonical bytes",
        "threshold": 2,
        "author_of_record": "astra-lead-formulation",
    },
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "sha256": "d9cebb9404b2",
        "class": "AF-WCC-VAC-GEN",
        "criterion": "G-FORM: >=2 independent full-schema accepts per class",
        "threshold": 2,
        "author_of_record": "astra-lead-formulation",
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "e9a27996dfd3",
        "class": "AF-SCC-C2-VAC-GEN",
        "criterion": "G-FORM: >=2 independent full-schema accepts per class",
        "threshold": 2,
        "author_of_record": "astra-lead-formulation",
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "b2ab6acb2bbe",
        "class": "AF-SCC-C0-VAC-GEN",
        "criterion": "G-FORM: >=2 independent full-schema accepts per class",
        "threshold": 2,
        "author_of_record": "astra-lead-formulation",
    },
    "L0": {
        "path": "ledger/theorems.jsonl",
        "sha256": "a1674f094979",
        "class": "GLOBAL",
        "criterion": "G-LIT: L0 >=2 independent accepts at the frozen hash",
        "threshold": 2,
        "author_of_record": "astra-lead-literature",
    },
    "GNUM_PROTOCOL": {
        "path": "numerics/CONVERGENCE_PROTOCOL.md",
        "sha256": "1e6cdf04d7a2",
        "class": "AF-WCC-SCALAR-SPH",
        "criterion": "G-NUM protocol C8: >=1 accept (standing accept 4.5)",
        "threshold": 1,
        "author_of_record": "astra-lead-numerics",
    },
}

NAMED_POLICIES = ("P_REVIEWED", "P_ARTIFACT", "P_TARGET", "P_FROZEN")
POLICIES = NAMED_POLICIES + ("P_BIND", "P_MENTION")
THRESHOLD_POLICIES = ("P_REVIEWED", "P_ARTIFACT", "P_BIND")
PIN_PREFIX_LEN = 12
FULL_EXPLICIT_FALSE = "explicit_false"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_strings(obj, path="$", depth=0, out=None):
    """Yield (json_path, string_value) for every string leaf, depth-limited."""
    if out is None:
        out = []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_strings(v, f"{path}.{k}", depth + 1, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_strings(v, f"{path}[{i}]", depth + 1, out)
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def load_review_files():
    files = []
    for dirpath, _dirnames, filenames in os.walk(REVIEW_ROOT):
        for fn in sorted(filenames):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT)
            try:
                d = json.load(open(p))
            except Exception as exc:  # unparseable: recorded, not silently skipped
                files.append({"path": rel, "parse_error": repr(exc)})
                continue
            if not isinstance(d, dict):
                files.append({"path": rel, "non_object": True})
                continue
            files.append({"path": rel, "doc": d})
    return files


def corpus_digest(entries):
    h = hashlib.sha256()
    for e in sorted(entries, key=lambda x: x["path"]):
        h.update(e["path"].encode())
        h.update(b"\0")
        h.update(e.get("sha256", "").encode())
        h.update(b"\n")
    return h.hexdigest()


def build_snapshot():
    files = load_review_files()
    snap = []
    for e in files:
        if "doc" not in e:
            snap.append({"path": e["path"], "sha256": sha256_file(os.path.join(ROOT, e["path"])),
                         "not_review_json": True, "reason": e.get("parse_error") or "non_object"})
            continue
        p = os.path.join(ROOT, e["path"])
        d = e["doc"]
        leaves = walk_strings(d)
        full = d.get("counts_as_full_schema_verdict")
        if full is True:
            full_cat = "explicit_true"
        elif full is False:
            full_cat = FULL_EXPLICIT_FALSE
        elif "counts_as_full_schema_verdict" in d:
            full_cat = "present_nonbool"
        else:
            full_cat = "absent_default_full"
        snap.append({
            "path": e["path"],
            "sha256": sha256_file(p),
            "mtime": os.path.getmtime(p),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "verdict": d.get("verdict"),
            "full_category": full_cat,
            "counts_as_full_schema_verdict": full,
            "counts_as_independent": d.get("counts_as_independent"),
            "blind": d.get("blind"),
            "node_id": d.get("node_id"),
            "target_id": d.get("target_id"),
            "task_id": d.get("task_id"),
            "leaves": leaves,
        })
    return snap


def carrier_key(policy: str, leaf_path: str):
    key = leaf_path.rsplit(".", 1)[-1].split("[")[0]
    if policy == "P_REVIEWED":
        return key == "reviewed_sha256"
    if policy == "P_ARTIFACT":
        return key == "artifact_sha256"
    if policy == "P_TARGET":
        return key in ("target_id", "artifact", "reviewed_artifact")
    if policy == "P_FROZEN":
        return key in ("reviewed_frozen_sha256", "frozen_sha256", "frozen_artifact_sha256")
    return False


def policy_match(rec, pin_prefix, policy):
    """Return list of json paths under which this review binds the pin."""
    hits = []
    for lp, val in rec.get("leaves", []):
        if pin_prefix not in val:
            continue
        if policy == "P_MENTION":
            hits.append(lp)
        elif policy == "P_BIND":
            if any(carrier_key(p, lp) for p in NAMED_POLICIES):
                hits.append(lp)
        elif carrier_key(policy, lp):
            hits.append(lp)
    return hits


def compute_pin(snap, pin):
    res = {}
    prefix = pin["sha256"][:PIN_PREFIX_LEN]
    for policy in POLICIES:
        bound = []
        for rec in snap:
            hits = policy_match(rec, prefix, policy)
            if hits:
                bound.append({**{k: rec.get(k) for k in
                                 ("path", "sha256", "mtime", "reviewer", "verdict",
                                  "full_category", "counts_as_full_schema_verdict",
                                  "counts_as_independent", "blind", "node_id", "target_id")},
                              "hit_paths": hits})
        accepts = [b for b in bound if b["verdict"] == "accept"]
        revises = [b for b in bound if b["verdict"] == "revise"]
        by_rev = defaultdict(list)
        for b in bound:
            by_rev[b["reviewer"] or "?"].append(b)
        latest_accepts = []
        for _rev, items in by_rev.items():
            items_sorted = sorted(items, key=lambda x: (x["mtime"], x["path"]))
            if items_sorted[-1]["verdict"] == "accept":
                latest_accepts.append(items_sorted[-1])

        def independent(b):
            return (b["reviewer"] or "?") != pin["author_of_record"] and b["counts_as_independent"] is not False

        full_accepts = [a for a in accepts if a["full_category"] != FULL_EXPLICIT_FALSE]
        indep_full = [a for a in full_accepts if independent(a)]
        field_census = Counter()
        for b in bound:
            for hp in b["hit_paths"]:
                field_census[hp.rsplit(".", 1)[-1].split("[")[0]] += 1
        res[policy] = {
            "bound_files": len(bound),
            "accept_reviewers_raw": sorted({b["reviewer"] or "?" for b in accepts}),
            "revise_reviewers_raw": sorted({b["reviewer"] or "?" for b in revises}),
            "accept_reviewers_latest": sorted({b["reviewer"] or "?" for b in latest_accepts}),
            "full_schema_accept_reviewers": sorted({b["reviewer"] or "?" for b in full_accepts}),
            "independent_full_schema_accept_reviewers": sorted({b["reviewer"] or "?" for b in indep_full}),
            "explicitly_scoped_accepts": sorted({b["reviewer"] or "?" for b in accepts
                                                 if b["full_category"] == FULL_EXPLICIT_FALSE}),
            "binding_field_census": dict(sorted(field_census.items())),
            "bound": sorted(bound, key=lambda x: x["path"]),
        }
    primary = {p: len(res[p]["independent_full_schema_accept_reviewers"]) for p in POLICIES}
    rawc = {p: len(res[p]["accept_reviewers_raw"]) for p in POLICIES}
    met = {p: primary[p] >= pin["threshold"] for p in THRESHOLD_POLICIES}
    res["_summary"] = {
        "pin": pin["sha256"],
        "path": pin["path"],
        "declared_threshold": pin["threshold"],
        "criterion": pin["criterion"],
        "independent_full_schema_accept_counts": primary,
        "raw_accept_counts": rawc,
        "threshold_policies": list(THRESHOLD_POLICIES),
        "criterion_met_by_policy": met,
        "policy_crosses_criterion": len(set(met.values())) > 1,
        "policy_changes_count": len(set(primary[p] for p in THRESHOLD_POLICIES)) > 1,
    }
    return res


def run_controls(pins):
    """Synthetic fixtures exercised through the same policy_match code path (pin=F2b)."""
    base = {"sha256": "0" * 64, "mtime": 0.0, "reviewer": "control", "verdict": "accept",
            "full_category": "explicit_true", "counts_as_full_schema_verdict": True,
            "counts_as_independent": True, "blind": True, "node_id": "F2b", "target_id": "x"}
    pin = pins["F2b"]["sha256"]
    px = pin[:PIN_PREFIX_LEN]
    fixtures = {
        "C1_artifact_only": ({**base, "path": "ctl/C1.json",
                              "leaves": [("$.artifact_sha256", pin)]},
                             {"P_REVIEWED": False, "P_ARTIFACT": True, "P_TARGET": False,
                              "P_FROZEN": False, "P_BIND": True, "P_MENTION": True}),
        "C2_reviewed_only": ({**base, "path": "ctl/C2.json",
                              "leaves": [("$.reviewed_sha256", pin)]},
                             {"P_REVIEWED": True, "P_ARTIFACT": False, "P_TARGET": False,
                              "P_FROZEN": False, "P_BIND": True, "P_MENTION": True}),
        "C3_unrelated": ({**base, "path": "ctl/C3.json",
                          "leaves": [("$.reviewed_sha256", "f" * 64)]},
                         {"P_REVIEWED": False, "P_ARTIFACT": False, "P_TARGET": False,
                          "P_FROZEN": False, "P_BIND": False, "P_MENTION": False}),
        "C4_revise_bound": ({**base, "path": "ctl/C4.json", "verdict": "revise",
                             "leaves": [("$.reviewed_sha256", pin)]},
                            {"P_REVIEWED": True, "P_BIND": True}),
        "C5_scoped_accept": ({**base, "path": "ctl/C5.json", "full_category": FULL_EXPLICIT_FALSE,
                              "counts_as_full_schema_verdict": False,
                              "leaves": [("$.artifact_sha256", pin)]},
                             {"P_REVIEWED": False, "P_ARTIFACT": True, "P_BIND": True}),
        "C6_author_accept": ({**base, "path": "ctl/C6.json", "reviewer": "astra-lead-formulation",
                              "leaves": [("$.reviewed_sha256", pin)]},
                             {"P_REVIEWED": True, "P_BIND": True}),
        "C7_frozen_only": ({**base, "path": "ctl/C7.json",
                            "leaves": [("$.reviewed_frozen_sha256", pin)]},
                           {"P_REVIEWED": False, "P_ARTIFACT": False, "P_TARGET": False,
                            "P_FROZEN": True, "P_BIND": True, "P_MENTION": True}),
        "C8_target_path_hash": ({**base, "path": "ctl/C8.json",
                                 "leaves": [("$.target_id", f"schemas/af_scc_c0_vacuum.yaml#{pin}")]},
                                {"P_REVIEWED": False, "P_ARTIFACT": False, "P_TARGET": True,
                                 "P_FROZEN": False, "P_BIND": True, "P_MENTION": True}),
        "C9_prose_mention_only": ({**base, "path": "ctl/C9.json",
                                   "leaves": [("$.summary", f"cites {px} in prose"),
                                              ("$.findings[0]", f"mentions {pin} as evidence")]},
                                  {"P_REVIEWED": False, "P_ARTIFACT": False, "P_TARGET": False,
                                   "P_FROZEN": False, "P_BIND": False, "P_MENTION": True}),
        "C10_nested_bind": ({**base, "path": "ctl/C10.json",
                             "leaves": [("$.evidence.pins[0].reviewed_sha256", pin)]},
                            {"P_REVIEWED": True, "P_ARTIFACT": False, "P_TARGET": False,
                             "P_FROZEN": False, "P_BIND": True, "P_MENTION": True}),
        "C11_not_independent_flag": ({**base, "path": "ctl/C11.json", "counts_as_independent": False,
                                      "leaves": [("$.reviewed_sha256", pin)]},
                                     {"P_REVIEWED": True, "P_BIND": True,
                                      "_independent": False}),
    }
    results = {}
    for name, (rec, expected) in fixtures.items():
        row = {p: bool(policy_match(rec, px if p != "P_MENTION" else px, p)) for p in POLICIES}
        indep = ((rec["reviewer"] or "?") != "astra-lead-formulation"
                 and rec["counts_as_independent"] is not False)
        exp = {k: v for k, v in expected.items() if not k.startswith("_")}
        ok = all(row.get(k) == v for k, v in exp.items())
        if "_independent" in expected:
            ok = ok and (indep == expected["_independent"])
        results[name] = {"observed_binding": row, "observed_independent": indep,
                         "expected": exp, "pass": ok}
    return results


def main():
    pins_measured = {}
    for name, pin in PINS.items():
        h = sha256_file(os.path.join(ROOT, pin["path"]))
        pins_measured[name] = {"path": pin["path"], "expected_prefix": pin["sha256"],
                               "measured_sha256": h, "resolves": h.startswith(pin["sha256"])}

    snap_pre = build_snapshot()
    digest_pre = corpus_digest(snap_pre)
    per_pin = {name: compute_pin(snap_pre, pin) for name, pin in PINS.items()}
    controls = run_controls(PINS)

    # Oracle: two independent censuses on record (worker-017 CF31 binding table,
    # worker-018 census) count F2b rev29 as reviewed_sha256 -> 3, artifact_sha256 -> 0.
    f2b = per_pin["F2b"]["_summary"]
    controls["C12_f2b_oracle"] = {
        "expected": {"P_REVIEWED": 3, "P_ARTIFACT": 0},
        "observed": {p: f2b["independent_full_schema_accept_counts"].get(p)
                     for p in ("P_REVIEWED", "P_ARTIFACT")},
        "pass": (f2b["independent_full_schema_accept_counts"].get("P_REVIEWED") == 3
                 and f2b["independent_full_schema_accept_counts"].get("P_ARTIFACT") == 0),
    }
    per_pin_rerun = {name: compute_pin(snap_pre, pin) for name, pin in PINS.items()}
    controls["C13_rerun_identical"] = {
        "pass": json.dumps(per_pin, sort_keys=True) == json.dumps(per_pin_rerun, sort_keys=True)}

    snap_post = build_snapshot()
    digest_post = corpus_digest(snap_post)
    pre_paths = {r["path"]: r.get("sha256") for r in snap_pre}
    post_paths = {r["path"]: r.get("sha256") for r in snap_post}
    moved = sorted(p for p in pre_paths if p in post_paths and pre_paths[p] != post_paths[p])
    added = sorted(set(post_paths) - set(pre_paths))
    removed = sorted(set(pre_paths) - set(post_paths))
    controls["C14_corpus_stable"] = {
        "digest_pre": digest_pre, "digest_post": digest_post,
        "moved_files": moved, "added_files": added, "removed_files": removed,
        "pass": not moved and not added and not removed,
    }

    report = {
        "task_id": "W094H-BIND-POLICY-01",
        "actor": "worker-094",
        "generated_at_local": subprocess.run(
            ["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
        "primary_class": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_ids": ["F2b", "F0", "F1", "F2a", "L0", "N0"],
        "gate": "G-FORM",
        "scope": ("Read-only binding-carrier policy sensitivity of review coverage at the pass-09 measured pins. "
                  "CF-31 (F2b b2ab6acb2bbe: 3 accepts under reviewed_sha256, 0 under artifact_sha256) is the "
                  "primary carrier; F0/F1/F2a/L0/G-NUM-protocol are comparators in the same measurement."),
        "policy_definitions": {
            "P_REVIEWED": "leaf key exactly 'reviewed_sha256' contains the pin",
            "P_ARTIFACT": "leaf key exactly 'artifact_sha256' contains the pin",
            "P_TARGET": "leaf key in {target_id, artifact, reviewed_artifact} contains the pin (path#hash form)",
            "P_FROZEN": "leaf key in {reviewed_frozen_sha256, frozen_sha256, frozen_artifact_sha256} contains the pin",
            "P_BIND": "union of the four named carriers = the 'any binding carrier' policy",
            "P_MENTION": "any string leaf anywhere (depth<=6) contains the 12-hex pin prefix; UPPER BOUND only, "
                         "contaminated by prose mentions and cross-target evidence quotes",
        },
        "pin_resolution": pins_measured,
        "corpus": {
            "root": "reviews/",
            "review_json_files": sum(1 for r in snap_pre if "leaves" in r),
            "non_review_json_files": sum(1 for r in snap_pre if "leaves" not in r),
            "digest_pre": digest_pre, "digest_post": digest_post,
            "decision_instant_note": "per-file sha256 and mtime are in corpus_manifest.json; the digest covers paths+sha256 only",
        },
        "per_pin": per_pin,
        "controls": controls,
        "all_controls_pass": all(v.get("pass") for v in controls.values()),
        "threshold_crossings": {
            name: {
                "criterion": PINS[name]["criterion"],
                "threshold": PINS[name]["threshold"],
                "independent_full_schema_accept_counts_by_policy": per_pin[name]["_summary"]["independent_full_schema_accept_counts"],
                "raw_accept_counts_by_policy": per_pin[name]["_summary"]["raw_accept_counts"],
                "criterion_met_by_policy": per_pin[name]["_summary"]["criterion_met_by_policy"],
                "policy_crosses_criterion": per_pin[name]["_summary"]["policy_crosses_criterion"],
                "policy_changes_count": per_pin[name]["_summary"]["policy_changes_count"],
            }
            for name in PINS
        },
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    with open(os.path.join(OUT_DIR, "policy_table.json"), "w") as fh:
        json.dump({n: per_pin[n]["_summary"] for n in PINS}, fh, indent=1, sort_keys=True)
    with open(os.path.join(OUT_DIR, "corpus_manifest.json"), "w") as fh:
        json.dump({
            "digest_pre": digest_pre, "digest_post": digest_post,
            "files": [{k: r.get(k) for k in ("path", "sha256", "mtime", "reviewer", "verdict",
                                             "full_category", "counts_as_full_schema_verdict",
                                             "counts_as_independent", "blind", "node_id", "target_id")}
                      for r in snap_pre],
        }, fh, indent=1, sort_keys=True)
    with open(os.path.join(OUT_DIR, "controls.json"), "w") as fh:
        json.dump(controls, fh, indent=1, sort_keys=True)

    print(json.dumps({
        "all_controls_pass": report["all_controls_pass"],
        "corpus_digest": digest_pre,
        "independent_full_schema_accepts": {
            n: report["threshold_crossings"][n]["independent_full_schema_accept_counts_by_policy"]
            for n in PINS},
        "criterion_met_by_policy": {
            n: report["threshold_crossings"][n]["criterion_met_by_policy"] for n in PINS},
        "policy_crosses_criterion": {
            n: report["threshold_crossings"][n]["policy_crosses_criterion"] for n in PINS},
    }, indent=1, sort_keys=True))
    return 0 if report["all_controls_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
