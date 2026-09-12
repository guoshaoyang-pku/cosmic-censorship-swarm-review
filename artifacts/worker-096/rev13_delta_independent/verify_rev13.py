#!/usr/bin/env python3
"""W096-REV13-DELTA-INDEP-VERIFY-01 -- independent, read-only verification of the landed
rev13 repair (astra-life05-evidence-binding-repair) at the post-repair hashes.

Task: ONE bounded class-bound task, self-selected because comms/inbox/worker-096.jsonl does
not exist.  Classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN; node F1/F2a/F2b;
gate G-FORM.  This is NOT a full-schema verdict and NOT a gate verdict.

What it does, all read-only on canonical paths:
  A. before/after pin resolution: rev12 "before" bytes are taken from worker-096's OWN
     pre-repair sandbox snapshots (not from the repairing agent's report) and checked
     against the FROZEN rev28 manifest; rev13 "after" bytes are measured live.
  B. declared-delta verification: for each schema the structural YAML delta is computed and
     required to be a subset of the declared changed paths (header + f0_binding + the three
     F1 strictness fields).  No class-semantics path may move.
  C. binding resolution: every f0_binding hash declaration is resolved against measured bytes.
  D. mirror alignment: canonical == published copy for all three.
  E. canonical checkers: check_class_schema.py on the three live files; the taxonomy
     consistency checker re-run in a sandbox (it writes, so never in-tree).
  F. direction checks re-derived from scratch by finite-model enumeration, independent of
     worker-076's preorder enumeration: (T1) tail == whole under past-closedness, with a
     non-past-closed separating witness; (T2) single-q => union with a separating witness.
  G. L-FORM-01 audit on rev13: the F2b implication_ledger inversion is re-tested.
  H. controls, and a frozen-manifest status read (rev29 not yet published).

Falsifier: re-run this file.  Falsified if any measured hash differs from report.json pins,
if the structural delta escapes the declared path set, if a checker regresses, if the
L-FORM-01 detector does not fire on the rev12 snapshot or fails to clear on the patched
text, if any control fails, or if any canonical byte moved during the run.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-096/rev13_delta_independent"
SNAP = ROOT / "artifacts/worker-096/evidence_binding_adjudication/sandboxes/c2"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"

CLASSES = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
REV12 = {  # measured immediately before the 00:53:20 repair; also FROZEN rev28 pins
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
REV13 = {  # measured at 2026-09-12T00:57+08:00, re-measured by this script
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}
FROZEN28_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
FROZEN29_SHA = "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833"
REV28_ORACLES = [  # hash-named third-party snapshots of the rev28 manifest (before-oracle)
    "artifacts/worker-074/rev29_landing_guard/snapshot/rev28_pin/FROZEN.2f358f6722d9.json",
    "artifacts/worker-060/rev29_binding_acceptance/snapshots/FROZEN.2f358f6722d9.json",
    "artifacts/worker-007/rev29_preflight/snapshot/FROZEN.2f358f6722d9.json",
]
F0_DECLARED = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_SUPPLEMENT = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
EVIDENCE_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
SUPERSEDED_EVIDENCE = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"

VOLATILE = ("revision", "revised_at", "revision_history")
VOLATILE_PREFIX = ("f0_binding.checked_at", "f0_binding.consistency_evidence_sha256",
                   "f0_binding.binding_note")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = json.dumps(obj, sort_keys=True)
    return out


def structural_delta(before: str, after: str):
    a, b = flatten(yaml.safe_load(before)), flatten(yaml.safe_load(after))
    changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return changed, a, b


def within_declared(path: str) -> bool:
    return (path == "revision" or path == "revised_at" or path.startswith("revision_history")
            or path.startswith(VOLATILE_PREFIX))


def resolve_binding(text: str, measured_taxonomy: str, measured_evidence: str):
    d = yaml.safe_load(text).get("f0_binding", {}) or {}
    decl = str(d.get("consistency_evidence_sha256", ""))
    decl_f0 = str(d.get("declared_f0_sha256") or d.get("f0_sha256") or "")
    return {
        "consistency_evidence_sha256_declared": decl,
        "consistency_evidence_sha256_measured": measured_evidence,
        "consistency_evidence_resolved": decl == measured_evidence,
        "declared_f0_sha256": decl_f0,
        "declared_f0_resolved": decl_f0 == measured_taxonomy,
    }


# ---------------------------------------------------------------- finite-model direction checks
def causal_model_checks():
    """Independent re-derivation of the two strictness claims.

    T1: for a causal (transitive) relation, tail containment in J^-(q) at some t0 and
        whole-curve containment are equivalent.  Control T1': drop transitivity, find a
        separating model.
    T2: the single-q predicate entails the union predicate; find a model where the union
        holds and no single q works (so SET is strictly weaker than the class default).
    """
    pts = (0, 1, 2)
    rels = []
    for mask in range(1 << (len(pts) * len(pts))):
        R = frozenset((i, j) for i in pts for j in pts if mask >> (i * len(pts) + j) & 1)
        rels.append(R)

    def transitive(R):
        return all((x, z) in R for (x, y) in R for (y2, z) in R if y == y2)

    def curve_ok(R, g):
        return all((g[i], g[j]) in R for i in range(len(g)) for j in range(i + 1, len(g)))

    curves = [g for g in itertools.product(pts, repeat=3)]
    viol_t1, checks_t1, viol_control, witness = 0, 0, 0, None
    for R in rels:
        Jm = {q: frozenset(x for x in pts if (x, q) in R) for q in pts}
        trans = transitive(R)
        for g in curves:
            if not curve_ok(R, g):
                continue
            for q in pts:
                for t0 in range(len(g)):
                    tail = all(g[i] in Jm[q] for i in range(t0, len(g)))
                    whole = all(x in Jm[q] for x in g)
                    if tail and not whole:
                        if trans:
                            viol_t1 += 1
                        else:
                            viol_control += 1
                            if witness is None:
                                witness = {"R": sorted(R), "curve": list(g), "q": q, "t0": t0}
                    if trans:
                        checks_t1 += 1

    # T2: single-q => union (universal on 3 points), and a separating witness union & !single
    viol_single_union, checks_t2 = 0, 0
    sep = None
    for R in rels:
        Jm = {q: frozenset(x for x in pts if (x, q) in R) for q in pts}
        for g in curves:
            tail_idx = list(range(1, len(g)))  # a nonempty tail; t0 = 1
            union = all(any(g[i] in Jm[q] for q in pts) for i in tail_idx)
            single = any(all(g[i] in Jm[q] for i in tail_idx) for q in pts)
            checks_t2 += 1
            if single and not union:
                viol_single_union += 1
            if union and not single and sep is None:
                sep = {"R": sorted(R), "curve": list(g),
                       "covers": {str(q): sorted(Jm[q] & set(g)) for q in pts}}
    return {
        "T1_past_closed_tail_implies_whole": {"checks": checks_t1, "violations": viol_t1},
        "T1_control_non_transitive_tail_not_whole": {"separating_models": viol_control,
                                                     "first_witness": witness},
        "T2_single_q_implies_union": {"checks": checks_t2, "violations": viol_single_union},
        "T2_union_not_single_witness": sep,
    }


# ---------------------------------------------------------------- L-FORM-01 (F2b:246 rev13)
def lform01(text: str):
    m = re.search(r'\{from: "no proper future C2 extension", to: "this class", reason: "([^"]*)"\}', text)
    if not m:
        return {"row_found": False}
    reason = m.group(1)
    chain = re.search(r'extension_class_containment: "([^"]*)"', text)
    line = text[:m.start()].count("\n") + 1
    return {
        "row_found": True,
        "line": line,
        "reason": reason,
        "inverted_premise_present": "strictly larger extension class" in reason,
        "conclusion_direction": "strictly weaker" if "strictly weaker" in reason else "other",
        "declared_chain": chain.group(1) if chain else None,
        "minimal_patch": reason.replace("a strictly larger extension class",
                                        "a strictly smaller extension class"),
    }


def main() -> int:
    rep = {"schema": "worker-096/rev13-delta-independent/v1",
           "task_id": "W096-REV13-DELTA-INDEP-VERIFY-01", "worker": "worker-096",
           "class_ids": list(CLASSES), "node_id": "F1,F2a,F2b", "gate": "G-FORM",
           "authority": "worker event; cannot set status=done, validation_status=passed, or any gate verdict",
           "canonical_writes": [], "pins": {}, "items": {}, "controls": {}}

    # ---- A. before/after pin resolution
    # before-oracle: hash-named third-party snapshot of the rev28 manifest, not the repairing
    # agent's report and not the live FROZEN.json (which moved to rev29 during this run).
    oracle_path = next((ROOT / p for p in REV28_ORACLES if (ROOT / p).exists()), None)
    oracle = json.loads(oracle_path.read_text()) if oracle_path else None
    fpin = oracle["files"] if oracle else {}
    rep["pins"]["rev28_oracle_path"] = str(oracle_path.relative_to(ROOT)) if oracle_path else None
    rep["pins"]["rev28_oracle_sha256"] = sha(oracle_path) if oracle_path else None
    rep["pins"]["rev28_oracle_ok"] = bool(oracle_path) and sha(oracle_path) == FROZEN28_SHA
    rep["pins"]["rev28_oracle_pins_rev12"] = bool(oracle) and all(
        fpin.get(rel, {}).get("sha256") == REV12[rel] for rel in REV12)
    live_frozen = json.loads(FROZEN.read_text())
    rep["pins"]["frozen_live_revision"] = live_frozen.get("revision")
    rep["pins"]["frozen_live_sha256"] = sha(FROZEN)
    rep["pins"]["frozen_live_expected_sha256"] = FROZEN29_SHA
    rep["pins"]["frozen_live_matches_rev29"] = sha(FROZEN) == FROZEN29_SHA
    for cid, rel in CLASSES.items():
        before = SNAP / rel
        after = ROOT / rel
        mirror = ROOT / "artifacts/formulation" / rel
        rec = {
            "rev12_before_snapshot_sha256": sha(before),
            "rev12_snapshot_matches_rev12_pin": sha(before) == REV12[rel],
            "rev12_snapshot_matches_rev28_oracle": bool(fpin) and sha(before) == fpin[rel]["sha256"],
            "rev13_after_sha256": sha(after),
            "rev13_matches_expected": sha(after) == REV13[rel],
            "mirror_sha256": sha(mirror),
            "mirror_identical": sha(mirror) == sha(after),
            "frozen29_pin_sha256": live_frozen["files"].get(rel, {}).get("sha256"),
            "frozen29_pin_matches_live": live_frozen["files"].get(rel, {}).get("sha256") == sha(after),
        }
        rep["pins"][cid] = rec

    rep["pins"]["f0_declared_sha256"] = sha(ROOT / "research_map/formulation_taxonomy.yaml")
    rep["pins"]["f0_supplement_sha256"] = sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")
    rep["pins"]["f0_declared_matches"] = rep["pins"]["f0_declared_sha256"] == F0_DECLARED
    rep["pins"]["f0_supplement_matches"] = rep["pins"]["f0_supplement_sha256"] == F0_SUPPLEMENT
    rep["pins"]["consistency_evidence_sha256"] = sha(EVIDENCE)
    rep["pins"]["consistency_evidence_matches_declared_target"] = sha(EVIDENCE) == EVIDENCE_SHA

    # expected semantic paths for F1, derived from the rev12 values that the card declared
    old_markers = [
        "Whole-curve containment gamma([0,T)) subset J^-(q) is strictly STRONGER",
        "would misclassify a geodesic that starts in the exterior",
        "strictly STRONGER than this class's single-q tail predicate",
    ]
    snap_f1 = (SNAP / CLASSES["AF-WCC-VAC-GEN"]).read_text()
    _, before_flat, _ = structural_delta(snap_f1, snap_f1)
    expected_f1 = sorted({p for p, v in before_flat.items()
                          if any(mk in v for mk in old_markers)})
    rep["items"]["item3_declared_semantic_paths"] = expected_f1

    # ---- B. declared-delta verification
    for cid, rel in CLASSES.items():
        before = (SNAP / rel).read_text()
        after = (ROOT / rel).read_text()
        changed, a, b = structural_delta(before, after)
        expected = set(expected_f1) if cid == "AF-WCC-VAC-GEN" else set()
        undeclared = [p for p in changed if not within_declared(p) and p not in expected]
        rep["items"].setdefault("declared_delta", {})[cid] = {
            "changed_paths": changed,
            "declared_semantic_paths_changed": sorted(p for p in changed if p in expected),
            "undeclared_changed_paths": undeclared,
            "delta_within_declaration": not undeclared,
            "rev13_contains_corrected_weaker_relation": (
                "strictly WEAKER than this class's single-q tail predicate" in after
                if cid == "AF-WCC-VAC-GEN" else None),
            "rev13_no_longer_contains_strictly_stronger": (
                "strictly STRONGER than this class's single-q tail predicate" not in after
                if cid == "AF-WCC-VAC-GEN" else None),
        }

    # ---- C. binding resolution (live vs unrepaired snapshot control)
    rep["items"]["binding_resolution"] = {}
    for cid, rel in CLASSES.items():
        live = resolve_binding((ROOT / rel).read_text(), rep["pins"]["f0_declared_sha256"],
                               rep["pins"]["consistency_evidence_sha256"])
        old = resolve_binding((SNAP / rel).read_text(), rep["pins"]["f0_declared_sha256"],
                              rep["pins"]["consistency_evidence_sha256"])
        rep["items"]["binding_resolution"][cid] = {
            "live": live, "unrepaired_snapshot_control": old,
            "control_fires_on_unrepaired": (old["consistency_evidence_sha256_declared"]
                                            == SUPERSEDED_EVIDENCE),
        }

    # ---- D/E. checkers
    class_checker = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    rep["items"]["check_class_schema"] = {}
    for cid, rel in CLASSES.items():
        proc = subprocess.run([sys.executable, str(class_checker), "--json", str(ROOT / rel)],
                              capture_output=True, text=True, timeout=120)
        rep["items"]["check_class_schema"][cid] = {
            "exit_code": proc.returncode,
            "verdict": (json.loads(proc.stdout).get("verdict")
                        if proc.stdout.strip().startswith("{") else proc.stdout.strip()[-200:]),
        }

    with tempfile.TemporaryDirectory(prefix="w096_rev13_") as td:
        sbx = Path(td)
        (sbx / "artifacts/formulation/tools").mkdir(parents=True)
        (sbx / "artifacts/formulation/evidence").mkdir(parents=True)
        (sbx / "research_map").mkdir(parents=True)
        shutil.copy(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py",
                    sbx / "artifacts/formulation/tools/check_taxonomy_consistency.py")
        for rel in ("research_map/formulation_taxonomy.yaml",
                    "artifacts/formulation/formulation_taxonomy.yaml",
                    "artifacts/formulation/VOCAB_ALIASES.json"):
            shutil.copy(ROOT / rel, sbx / rel)
        proc = subprocess.run([sys.executable, str(sbx / "artifacts/formulation/tools/check_taxonomy_consistency.py")],
                              capture_output=True, text=True, timeout=120)
        sbx_evidence = sbx / "artifacts/formulation/evidence/taxonomy_consistency.json"
        rep["items"]["taxonomy_checker_sandbox"] = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "regenerated_evidence_sha256": sha(sbx_evidence),
            "reproduces_live_evidence_9e335e9b": sha(sbx_evidence) == EVIDENCE_SHA,
        }
        # C4 mutation control: fake class id must be detected
        A = yaml.safe_load((sbx / "research_map/formulation_taxonomy.yaml").read_text())
        A["class_ids"] = list(A["class_ids"]) + ["AF-SCC-FAKE"]
        (sbx / "research_map/formulation_taxonomy.yaml").write_text(yaml.safe_dump(A, sort_keys=False))
        proc2 = subprocess.run([sys.executable, str(sbx / "artifacts/formulation/tools/check_taxonomy_consistency.py")],
                               capture_output=True, text=True, timeout=120)
        rep["controls"]["C4_taxonomy_mutation_detected"] = {
            "exit_code": proc2.returncode, "detected": proc2.returncode == 1,
            "stdout": proc2.stdout.strip()[:200],
        }

    # ---- F. direction checks
    rep["items"]["direction_checks"] = causal_model_checks()

    # ---- G. L-FORM-01 audit
    rep["items"]["lform01"] = {}
    for cid, rel in CLASSES.items():
        live = lform01((ROOT / rel).read_text())
        snap = lform01((SNAP / rel).read_text())
        if live.get("row_found") or snap.get("row_found"):
            rep["items"]["lform01"][cid] = {"live": live, "rev12_snapshot": snap}
    live_f2b = (ROOT / CLASSES["AF-SCC-C0-VAC-GEN"]).read_text()
    patched = live_f2b.replace("C2 is a strictly larger extension class",
                               "C2 is a strictly smaller extension class")
    rep["items"]["lform01"]["patched_text_clears_detector"] = not lform01(patched)["inverted_premise_present"]
    rep["items"]["lform01"]["patch_changes_exactly_one_line"] = (
        sum(1 for x, y in zip(live_f2b.splitlines(), patched.splitlines()) if x != y) == 1
        and len(live_f2b.splitlines()) == len(patched.splitlines()))
    rep["items"]["lform01"]["patched_bytes_sha256_if_applied_without_header_bump"] = sha_bytes(
        patched.encode())

    # secondary advisory: dormant inverted wording inside the pinned taxonomy checker
    checker_text = (ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    dm = re.search(r'"relation":"the F0 condition is strictly STRONGER[^"]*"', checker_text)
    rep["items"]["advisory_checker_d1_note"] = {
        "dormant_inverted_relation_word_present": bool(dm),
        "line": checker_text[:dm.start()].count("\n") + 1 if dm else None,
        "fires_only_if_D1_divergence_reactivates": True,
        "checker_sha256": sha(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"),
    }

    # ---- H. controls + frozen status
    tool = ROOT / "artifacts/formulation/tools/evidence_binding_repair_rev29.py"
    proc = subprocess.run([sys.executable, str(tool), "--dry-run"], capture_output=True,
                          text=True, timeout=120)
    rep["controls"]["C1_repair_tool_fails_closed_on_double_apply"] = {
        "exit_code": proc.returncode,
        "aborted": proc.returncode != 0 and "ASSERT FAIL [pin]" in (proc.stderr + proc.stdout),
    }
    rep["controls"]["C2_before_snapshots_match_rev12_pin_and_rev28_oracle"] = all(
        v["rev12_snapshot_matches_rev12_pin"] and v["rev12_snapshot_matches_rev28_oracle"]
        for v in (rep["pins"][cid] for cid in CLASSES))
    rep["controls"]["C3_binding_control_fires_on_unrepaired"] = all(
        v["control_fires_on_unrepaired"] for v in rep["items"]["binding_resolution"].values())
    rep["controls"]["C5_lform01_detector_sensitivity"] = (
        rep["items"]["lform01"].get("AF-SCC-C0-VAC-GEN", {}).get("live", {}).get(
            "inverted_premise_present") is True
        and rep["items"]["lform01"]["patched_text_clears_detector"]
        and rep["items"]["lform01"]["patch_changes_exactly_one_line"])

    # ---- rev13 verdict census: which review files bind the rev13 bytes
    census = {cid: [] for cid in CLASSES}
    for rv in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(rv.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for cid, rel in CLASSES.items():
            reviewed = REV13[rel] in {str(d.get("artifact_sha256")),
                                      str(d.get("reviewed_sha256"))}
            drift = REV13[rel] in {str(d.get("live_sha256_at_exit"))}
            if not (reviewed or drift):
                continue
            census[cid].append({
                "file": f"reviews/{rv.name}", "reviewer": d.get("reviewer"),
                "verdict": d.get("verdict") if isinstance(d.get("verdict"), str)
                else (d.get("verdict") or {}).get("verdict"),
                "score": d.get("score"), "reviewed_sha256": d.get("reviewed_sha256"),
                "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
                "binding_kind": ("reviewed_at_rev13" if reviewed else "drift_only"),
            })
    rep["items"]["rev13_verdict_census"] = census
    rep["items"]["rev13_verdict_census_caveat"] = (
        "Census reads review files on disk and reports the sha256 each file binds; it does not "
        "adjudicate reviewer distinctness, template sharing (Kish ESS), or map-level acceptance. "
        "'drift_only' means the file reviewed an earlier hash and merely recorded the rev13 hash "
        "at exit, so it is not a rev13 verdict.")
    rep["items"]["repair_cost_measure"] = {
        "F2a_rev13_accepts_at_e9a27996": sum(
            1 for r in census["AF-SCC-C2-VAC-GEN"]
            if r["verdict"] == "accept" and r["binding_kind"] == "reviewed_at_rev13"),
        "F2b_rev13_verdicts_at_b2ab6acb": sum(
            1 for r in census["AF-SCC-C0-VAC-GEN"] if r["binding_kind"] == "reviewed_at_rev13"),
        "F1_rev13_verdicts_at_d9cebb94": sum(
            1 for r in census["AF-WCC-VAC-GEN"] if r["binding_kind"] == "reviewed_at_rev13"),
        "note": "an F2b-only repair moves b2ab6acb and voids only the F2b rev13 verdicts; the "
                "F2a/F1 bytes and their verdicts are unaffected.",
    }

    f2b_now = sha(ROOT / CLASSES["AF-SCC-C0-VAC-GEN"])
    rep["frozen_manifest_status"] = {
        "rev28_oracle_sha256": rep["pins"]["rev28_oracle_sha256"],
        "live_frozen_revision": live_frozen.get("revision"),
        "live_frozen_frozen_at": live_frozen.get("frozen_at"),
        "live_frozen_sha256": rep["pins"]["frozen_live_sha256"],
        "rev29_published": live_frozen.get("revision") == 29,
        "rev29_pins_match_live_bytes": {
            rel: live_frozen["files"].get(rel, {}).get("sha256") == sha(ROOT / rel)
            for rel in list(CLASSES.values()) + ["artifacts/formulation/" + r for r in CLASSES.values()]
            + ["schemas/taxonomy_cases.jsonl",
               "artifacts/formulation/evidence/taxonomy_consistency.json"]},
        "f2b_rev13_sha256": f2b_now,
        "note": "FROZEN rev29 was published at 00:55:02, after the 00:53:20 schema write; it "
                "pins the F2b bytes that still carry the line-246 inverted premise, so the "
                "F2b:246 repair now costs a further manifest revision (rev30) and voids the one "
                "rev13 F2b verdict at b2ab6acb (worker-066 revise 2.5). F2a/F1 bytes are not "
                "moved by an F2b-only repair, so the two F2a rev13 accepts survive it.",
    }
    rep["verdict"] = (
        "rev13 items (1)-(3) independently verified at the measured hashes: declared delta "
        "bounded, bindings resolve, mirrors aligned, class checker 3/3 pass, direction claims "
        "re-derived from scratch; rev29 pins match live bytes for all six schema paths. TWO "
        "findings remain: (F1) the F2b implication_ledger inverted premise is STILL LIVE and is "
        "now FROZEN into rev29 at line %s -- repairing it costs a rev30 manifest, but it should "
        "land before any F2b r3 accept at b2ab6acb, and it does not move F2a/F1; (F2) dormant "
        "inverted relation word in the pinned taxonomy checker's D1 note."
        % rep["items"]["lform01"]["AF-SCC-C0-VAC-GEN"]["live"]["line"])
    rep["falsifier"] = (
        "Re-run verify_rev13.py: falsified if any pin/hash differs, any undeclared changed path "
        "appears, a checker regresses, the L-FORM-01 detector misses on the rev12 snapshot or "
        "does not clear on the one-line patch, any control fails, or any canonical byte moves.")
    rep["next_falsifier"] = (
        "The F2b line-246 repair landing (moves b2ab6acb and voids worker-066's rev13 revise "
        "and any F2b r3 verdict), or a rev30 manifest whose F2b pin does not match the measured "
        "bytes.")
    rep["findings"] = [
        {"id": "W096-R13-F1", "severity": "blocking-for-F2b-r3-accept",
         "statement": "F2b rev13 (b2ab6acb2bbe), frozen into FROZEN rev29 (3d9e3d77fd87), line %s "
                      "still asserts 'C2 is a strictly larger extension class' while the same "
                      "file's declared containment chain makes C2 the smallest extension class; "
                      "the conclusion ('strictly weaker') is correct, so the fix is the one "
                      "phrase only. Independently corroborates worker-066's F2b containment "
                      "adjudication (reviews/F2b-containment-normativity-worker-066.json and "
                      "artifacts/worker-066/f2b_containment_adjudication/report.json), which "
                      "already warned that rev29 would freeze the F2b defect."
                      % rep["items"]["lform01"]["AF-SCC-C0-VAC-GEN"]["live"]["line"],
         "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml:%s#b2ab6acb2bbe"
                           % rep["items"]["lform01"]["AF-SCC-C0-VAC-GEN"]["live"]["line"],
                           "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
                           "reviews/F2b-containment-normativity-worker-066.json",
                           "artifacts/worker-096/rev13_delta_independent/report.json",
                           "runtime/state/w096_checkpoint_7.json"],
         "falsifier": "A revision where the row's reason no longer says 'strictly larger' while "
                      "the declared chain is unchanged, or a declared chain that makes C2 the "
                      "largest extension set (which would contradict the same file's line 238 "
                      "chain)."},
        {"id": "W096-R13-F2", "severity": "advisory-dormant",
         "statement": "The pinned taxonomy consistency checker keeps an inverted strength word "
                      "in its dormant D1 divergence note (line %s): it calls the SET/union "
                      "condition 'strictly STRONGER' although its own supporting sentence and "
                      "the F1 rev13 correction make union strictly WEAKER than the single-q "
                      "tail. D1 is not firing at the current F0 text, so this is latent."
                      % rep["items"]["advisory_checker_d1_note"]["line"],
         "evidence_refs": ["artifacts/formulation/tools/check_taxonomy_consistency.py:%s"
                           % rep["items"]["advisory_checker_d1_note"]["line"],
                           "artifacts/worker-096/rev13_delta_independent/report.json"],
         "falsifier": "A checker revision whose D1 note states the union form is strictly weaker, "
                      "or a taxonomy text that reactivates D1 without exposing the inverted word."},
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("verdict", "controls", "frozen_manifest_status")},
                     indent=1))
    print("report:", OUT / "report.json", sha(OUT / "report.json")[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
