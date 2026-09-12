#!/usr/bin/env python3
"""W041-F1-CORPUS-REBIND-01 instrument.

Deterministic, read-only. Measures whether the F1 rev12->rev13 edits touch any
field exercised by the 25 rows of schemas/f1_falsifier_tests.jsonl, i.e. whether
blocker L-FORM-04's falsifier fires. Rules are frozen in PREREGISTRATION.md.

Exit codes: 0 analysis complete; 3 pin drift (fail-closed); 4 control failure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PINS = {
    "rev13": ("schemas/af_wcc_vacuum.yaml",
              "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "rev12_a": ("artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml",
                "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "rev12_b": ("artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml",
                "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "corpus": ("schemas/f1_falsifier_tests.jsonl",
               "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"),
    "frozen": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
}

METADATA_PREFIXES = ("revision", "revised_at", "revision_history", "f0_binding.checked_at")
CHANGED_NAME_TOKENS = ("visibility.definition", "class_identity_variants",
                       "quantifiers.domains.D5", "f0_binding.binding_note")
EXPECTED_SEMANTIC_CHANGED = ("visibility.definition",
                             "quantifiers.domains.D5.definition",
                             "class_identity_variants[0].relation")

TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\])?(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\])?)*"
)
SEG_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[([0-9]+)\])?")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_path(path: str):
    segs = []
    for part in path.split("."):
        m = SEG_RE.fullmatch(part)
        if not m:
            return None
        segs.append(m.group(1))
        if m.group(2) is not None:
            segs.append(int(m.group(2)))
    return segs


def resolve(obj, segs):
    cur = obj
    for s in segs:
        if isinstance(s, int):
            if not isinstance(cur, list) or s >= len(cur):
                return None, False
            cur = cur[s]
        else:
            if not isinstance(cur, dict) or s not in cur:
                return None, False
            cur = cur[s]
    return cur, True


def flatten(obj, prefix=""):
    """Yield (leaf_path, value) for every leaf; containers are not leaves."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def leaves_under(leaf_map, path: str):
    segs = parse_path(path)
    if segs is None:
        return set()
    exact = path
    if exact in leaf_map:
        return {exact}
    pre = path + "."
    pre_b = path + "["
    hit = {p for p in leaf_map if p == path or p.startswith(pre) or p.startswith(pre_b)}
    return hit


def run_probe(kind, expected, value, resolved):
    if kind == "contains":
        return expected in str(value) if resolved else False
    if kind == "equals":
        return resolved and expected == value
    if kind == "is_none":
        return resolved and value is None
    if kind == "is_true":
        return resolved and value is True
    if kind == "path_exists":
        return resolved
    if kind == "nonnull":
        return resolved and value is not None
    raise ValueError(f"unknown probe kind {kind!r}")


def analyse(rev12, rev13, rows):
    l12 = dict(flatten(rev12))
    l13 = dict(flatten(rev13))
    changed = {}
    for k in sorted(set(l12) | set(l13)):
        a, b = l12.get(k, "<absent>"), l13.get(k, "<absent>")
        if a != b:
            changed[k] = {"rev12": a, "rev13": b}

    row_reports = []
    touched_rows = []
    for idx, row in enumerate(rows):
        exercised = set()
        for pr in row.get("probe_results", []) or []:
            if isinstance(pr, dict) and pr.get("path"):
                exercised.add(pr["path"])
        for field in ("deciding_field", "deciding_field_contract"):
            val = row.get(field)
            if isinstance(val, str):
                exercised |= set(TOKEN_RE.findall(val))
        for val in row.get("deciding_field_alternates", []) or []:
            if isinstance(val, str):
                exercised.add(val)
        exercised = {p for p in exercised
                     if resolve(rev12, parse_path(p) or [])[1]
                     or resolve(rev13, parse_path(p) or [])[1]
                     or leaves_under(l12, p) or leaves_under(l13, p)}

        overlap = {}
        for p in sorted(exercised):
            lv = leaves_under(l12, p) | leaves_under(l13, p)
            hit = sorted(lv & set(changed))
            if hit:
                overlap[p] = hit
        touched = bool(overlap)
        nonmeta = sorted({h for hits in overlap.values() for h in hits
                          if not h.startswith(METADATA_PREFIXES)})

        probes = []
        for pi, pr in enumerate(row.get("probe_results", []) or []):
            if not isinstance(pr, dict) or not pr.get("path"):
                continue
            segs = parse_path(pr["path"])
            v12, r12 = resolve(rev12, segs)
            v13, r13 = resolve(rev13, segs)
            p12 = run_probe(pr.get("kind"), pr.get("expected"), v12, r12)
            p13 = run_probe(pr.get("kind"), pr.get("expected"), v13, r13)
            recorded = bool(pr.get("pass"))
            # Diagnostic only, never the primary rule: the corpus excerpts are
            # JSON-shaped, so a contains probe may also be read against
            # json.dumps(value). Labelled decomposition of calibration misses.
            diag = None
            if p12 != recorded and pr.get("kind") == "contains" and r12:
                jform = json.dumps(v12, default=str)
                if isinstance(pr.get("expected"), str) and pr["expected"] in jform:
                    diag = "json_representation_artifact"
                elif recorded and not p12:
                    diag = "stale_expectation_at_bound_revision"
            elif p12 != recorded:
                diag = "stale_expectation_at_bound_revision"
            probes.append({
                "index": pi,
                "path": pr["path"],
                "kind": pr.get("kind"),
                "recorded_pass": recorded,
                "reexec_pass_rev12": p12,
                "reexec_pass_rev13": p13,
                "calibrated": p12 == recorded,
                "outcome_changed": p12 != p13,
                "value_changed": (r12, v12) != (r13, v13),
                "uncalibrated_diagnosis": diag,
            })

        text_blob = json.dumps({k: v for k, v in row.items()
                                if k not in ("probe_results",)}, default=str)
        tier2 = sorted({t for t in CHANGED_NAME_TOKENS
                        if t in text_blob or t.replace(".", r"\.") in text_blob})

        rec = {
            "row_index": idx,
            "test_id": row.get("test_id"),
            "class_id": row.get("class_id"),
            "binding_ref": row.get("binding_ref"),
            "binding_sha256": row.get("binding_sha256"),
            "rebound_at": row.get("rebound_at"),
            "exercised_paths": sorted(exercised),
            "touched": touched,
            "overlap": overlap,
            "nonmetadata_overlap": nonmeta,
            "tier2_text_mentions": tier2,
            "probes": probes,
            "probes_calibrated": sum(1 for p in probes if p["calibrated"]),
            "probes_total": len(probes),
            "probe_outcomes_changed": sorted(
                p["path"] for p in probes if p["calibrated"] and p["outcome_changed"]),
        }
        row_reports.append(rec)
        if touched:
            touched_rows.append(idx)

    return changed, row_reports, touched_rows


def controls(rev12, rev13, rows, changed, touched_rows, l12):
    c = {}
    c["C1_rev12_copies_pinned"] = True  # enforced before analysis
    c["C2_hashes_rechecked_after"] = "recheck"  # filled by caller
    c["C3_positive_expected_semantic_changed"] = all(
        any(k == e or k.startswith(e + ".") or k.startswith(e + "[")
            for k in changed) for e in EXPECTED_SEMANTIC_CHANGED)
    c["C3_changed_leaf_count"] = len(changed)

    # C4 negative control: mutate a leaf under no exercised path -> no row touched
    exercised_all = set()
    for r in rows:
        for pr in r.get("probe_results", []) or []:
            if isinstance(pr, dict) and pr.get("path"):
                exercised_all |= leaves_under(l12, pr["path"])
        for field in ("deciding_field", "deciding_field_contract"):
            v = r.get(field)
            if isinstance(v, str):
                for t in TOKEN_RE.findall(v):
                    exercised_all |= leaves_under(l12, t)
        for v in r.get("deciding_field_alternates", []) or []:
            if isinstance(v, str):
                exercised_all |= leaves_under(l12, v)
    free = [k for k in sorted(l12) if k not in exercised_all]
    if free:
        target = free[0]
        mut = copy.deepcopy(rev12)
        segs = parse_path(target)
        cur = mut
        for s in segs[:-1]:
            cur = cur[s]
        cur[segs[-1]] = "__W041_NEGATIVE_CONTROL__"
        _, _, touched_after = analyse(rev12, mut, rows)
        c["C4_negative_control_path"] = target
        c["C4_negative_control_changes_touched_rows"] = bool(touched_after)
    else:
        c["C4_negative_control_path"] = None
        c["C4_negative_control_changes_touched_rows"] = None
    return c


def main():
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    pre = {k: sha256(ROOT / p) for k, (p, _) in PINS.items()}
    drift = {k: {"path": PINS[k][0], "expected": PINS[k][1], "measured": pre[k]}
             for k in PINS if pre[k] != PINS[k][1]}
    if drift:
        print(json.dumps({"status": "PIN_DRIFT", "drift": drift}, indent=2)[:4000])
        return 3
    if pre["rev12_a"] != pre["rev12_b"]:  # unreachable, same pin
        return 3

    import yaml
    rev12 = yaml.safe_load((ROOT / PINS["rev12_a"][0]).read_text())
    rev13 = yaml.safe_load((ROOT / PINS["rev13"][0]).read_text())
    rows = [json.loads(l) for l in (ROOT / PINS["corpus"][0]).read_text().splitlines() if l.strip()]

    changed, row_reports, touched_rows = analyse(rev12, rev13, rows)
    l12 = dict(flatten(rev12))
    ctl = controls(rev12, rev13, rows, changed, touched_rows, l12)

    post = {k: sha256(ROOT / p) for k, (p, _) in PINS.items()}
    ctl["C2_hashes_rechecked_after"] = {k: post[k] == pre[k] for k in PINS}

    # C6 determinism: two in-process runs, compare analysis payloads
    changed2, rows2, touched2 = analyse(rev12, rev13, rows)
    payload = json.dumps({"changed": changed, "rows": row_reports, "touched": touched_rows},
                         sort_keys=True, default=str)
    payload2 = json.dumps({"changed": changed2, "rows": rows2, "touched": touched2},
                          sort_keys=True, default=str)
    ctl["C6_deterministic"] = payload == payload2

    control_fail = (
        not ctl["C3_positive_expected_semantic_changed"]
        or ctl["C4_negative_control_changes_touched_rows"] is not False
        or not all(ctl["C2_hashes_rechecked_after"].values())
        or not ctl["C6_deterministic"]
    )

    calib_total = sum(r["probes_total"] for r in row_reports)
    calib_ok = sum(r["probes_calibrated"] for r in row_reports)
    semantic_touched = [r for r in row_reports if r["touched"] and r["nonmetadata_overlap"]]
    outcome_changed_rows = [r["row_index"] for r in row_reports if r["probe_outcomes_changed"]]

    falsifier_fires = bool(touched_rows)
    uncal = [{"row_index": r["row_index"], "test_id": r["test_id"], "path": p["path"],
              "kind": p["kind"], "recorded_pass": p["recorded_pass"],
              "reexec_pass_rev12": p["reexec_pass_rev12"],
              "diagnosis": p["uncalibrated_diagnosis"]}
             for r in row_reports for p in r["probes"] if not p["calibrated"]]
    stale = [u for u in uncal if u["diagnosis"] == "stale_expectation_at_bound_revision"]
    verdict = {
        "falsifier_status": "FALSIFIER_FIRES" if falsifier_fires else "FALSIFIER_DOES_NOT_FIRE",
        "severity": "semantic" if (semantic_touched or outcome_changed_rows) else
                    ("metadata_only" if falsifier_fires else "none"),
        "touched_row_count": len(touched_rows),
        "touched_row_indices": touched_rows,
        "rows_with_nonmetadata_overlap": [r["row_index"] for r in semantic_touched],
        "rows_with_changed_probe_outcome": outcome_changed_rows,
        "calibrated_probes": f"{calib_ok}/{calib_total}",
        "uncalibrated_probes": uncal,
        "stale_expectation_at_bound_revision_count": len(stale),
    }

    report = {
        "task_id": "W041-F1-CORPUS-REBIND-01",
        "instrument": "run_f1_corpus_rebind.py",
        "created_at": now,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN",
        "subject_blocker": "L-FORM-04",
        "authority_note": "worker measurement only; no gate verdict, no node status, no canonical file edited",
        "pins": {k: {"path": p, "sha256": PINS[k][1]} for k, (p, _) in PINS.items()},
        "changed_leaf_count": len(changed),
        "changed_leaves": changed,
        "row_reports": row_reports,
        "verdict": verdict,
        "controls": ctl,
        "control_failed": control_fail,
        "falsifier": ("L-FORM-04 falsifier: a reviewer shows the rev13 edits change a field any of the 25 tests "
                      "exercises, or the corpus is re-bound and the staleness disappears. This report tests the "
                      "first disjunct at pinned rev12 cce9c60146d6 vs rev13 d9cebb9404b2; "
                      "falsified if any exercised path has an unchanged value across the two revisions, if the "
                      "rev12 baseline copies do not both hash to the pin, or if the negative control fires."),
        "next_falsifier": ("Re-run at the same pins: the verdict is void if sha256(schemas/af_wcc_vacuum.yaml) != "
                           "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d, if "
                           "sha256(schemas/f1_falsifier_tests.jsonl) != "
                           "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e, or if the corpus is "
                           "re-bound so binding_sha256 no longer equals cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3."),
    }

    outdir = Path(__file__).resolve().parent
    (outdir / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"verdict": verdict, "controls": ctl, "control_failed": control_fail},
                     indent=2, default=str))
    return 4 if control_fail else 0


if __name__ == "__main__":
    sys.exit(main())
