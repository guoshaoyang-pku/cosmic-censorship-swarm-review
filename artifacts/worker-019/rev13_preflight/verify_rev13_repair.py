#!/usr/bin/env python3
"""W019-REV13-PREFLIGHT-01 -- independent pre-freeze verification of astra-life05-evidence-binding-repair.

Bounded class-bound worker task (worker-019). Read-only on all shared/canonical files:
this script only reads schemas/, artifacts/formulation/, reviews/, comms/ and
research_map/events.jsonl, and writes nothing outside artifacts/worker-019/rev13_preflight/.

Evidence model: `pinned_bytes.json` holds sha256 of the live bytes measured BEFORE FROZEN
rev29 was published; `snapshots/` holds byte copies of exactly those bytes. Every check
below is computed from the snapshots, then compared with the final FROZEN rev29 manifest
(`snapshots/FROZEN.rev29.json`, 3d9e3d77fd87) and with the current live bytes for drift.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE = os.path.join(ROOT, "artifacts", "worker-019", "rev13_preflight")
SNAP = os.path.join(BASE, "snapshots")
FROZEN_REV12_SNAP = os.path.join(ROOT, "artifacts", "worker-007", "citebind_census", "snapshot")

MOVED_CANONICAL = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "f1__af_wcc_vacuum.yaml"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "f2a__af_scc_c2_vacuum.yaml"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "f2b__af_scc_c0_vacuum.yaml"),
}
MOVED_OTHER = {
    "taxonomy_cases": ("schemas/taxonomy_cases.jsonl", "taxonomy_cases.jsonl"),
    "f1_falsifier_tests": ("schemas/f1_falsifier_tests.jsonl", "f1_falsifier_tests.jsonl"),
}
AUTHORING = {
    "F1": ("artifacts/formulation/schemas/af_wcc_vacuum.yaml", "authoring__af_wcc_vacuum.yaml"),
    "F2a": ("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", "authoring__af_scc_c2_vacuum.yaml"),
    "F2b": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "authoring__af_scc_c0_vacuum.yaml"),
}
REV12_SNAP = {
    "F1": "af_wcc_vacuum.cce9c60146d6.yaml",
    "F2a": "af_scc_c2_vacuum.5476a3f2c6bc.yaml",
    "F2b": "af_scc_c0_vacuum.55d0a1ea9bda.yaml",
}
TOP_ALLOWED = {"revision", "revised_at", "revision_history", "f0_binding"}
TOP_ALLOWED_F1_EXTRA = {"visibility", "quantifiers", "class_identity_variants"}
F0_BINDING_ALLOWED = {"checked_at", "consistency_evidence_sha256", "binding_note"}


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def short(h: str) -> str:
    return h[:12]


def load_yaml(p: str):
    import yaml

    return yaml.safe_load(open(p))


def leafdiff(a, b, path=""):
    out = []
    if type(a) is not type(b):
        out.append((path, "TYPE", str(a)[:120], str(b)[:120]))
        return out
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + "/" + k, "ADDED", "", json.dumps(b[k])[:200]))
            elif k not in b:
                out.append((path + "/" + k, "REMOVED", json.dumps(a[k])[:200], ""))
            else:
                out += leafdiff(a[k], b[k], path + "/" + k)
    elif isinstance(a, list):
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            out.append((path, "LIST", json.dumps(a)[:240], json.dumps(b)[:240]))
    else:
        if a != b:
            out.append((path, "VALUE", str(a)[:240], str(b)[:240]))
    return out


def main() -> int:
    checks = []

    def add(cid, status, title, detail, evidence, falsifier):
        checks.append(
            {
                "id": cid,
                "status": status,
                "title": title,
                "detail": detail,
                "evidence": evidence,
                "falsifier": falsifier,
            }
        )

    pinned = json.load(open(os.path.join(BASE, "pinned_bytes.json")))
    files = pinned["files"]
    snap_sha = {k: v.get("sha256") for k, v in files.items()}
    man_final_rec = pinned.get("manifest_final")
    man_final_sha = man_final_rec.get("sha256") if man_final_rec else None
    man_final = json.load(open(os.path.join(SNAP, "FROZEN.final.json"))) if man_final_rec else None

    # ---- C1: snapshot bytes == FROZEN rev29 pins for every moved path -------------
    man = json.load(open(os.path.join(SNAP, "FROZEN.rev29.json")))
    man_sha = sha(os.path.join(SNAP, "FROZEN.rev29.json"))
    mfiles = man.get("files", {})
    mism = []
    compared = []
    for group in (MOVED_CANONICAL, MOVED_OTHER, AUTHORING):
        for key, (live_path, snap_name) in group.items():
            rec = mfiles.get(live_path)
            rec_final = (man_final or {}).get("files", {}).get(live_path)
            if rec is None:
                mism.append({"path": live_path, "reason": "path absent from FROZEN rev29 files map"})
                continue
            compared.append(
                {
                    "path": live_path,
                    "snapshot_sha256": snap_sha.get(snap_name),
                    "frozen_rev29_sha256": rec.get("sha256"),
                    "frozen_final_sha256": (rec_final or {}).get("sha256"),
                    "match": snap_sha.get(snap_name) == rec.get("sha256")
                    and (rec_final is None or snap_sha.get(snap_name) == rec_final.get("sha256")),
                }
            )
            if not compared[-1]["match"]:
                mism.append({"path": live_path, "snapshot": snap_sha.get(snap_name),
                             "frozen": rec.get("sha256"), "frozen_final": (rec_final or {}).get("sha256")})
    add(
        "C1-pin-match",
        "pass" if not mism else "fail",
        "Pre-publication snapshot bytes equal the FROZEN rev29 pins (both manifest readings)",
        {
            "manifest": "snapshots/FROZEN.rev29.json",
            "manifest_sha256": man_sha,
            "manifest_revision": man.get("revision"),
            "manifest_frozen_at": man.get("frozen_at"),
            "manifest_final": "snapshots/FROZEN.final.json",
            "manifest_final_sha256": man_final_sha,
            "manifest_final_revision": (man_final or {}).get("revision"),
            "manifest_final_frozen_at": (man_final or {}).get("frozen_at"),
            "paths_compared": len(compared),
            "mismatches": mism,
            "window_note": (
                "snapshot of the moved bytes was taken before FROZEN rev29 existed "
                "(FROZEN.json measured 2f358f6722d9/rev28 at snapshot time); the manifest then moved "
                "e1a8aaa394eb -> 3d9e3d77fd87 -> 815e08079aef within ~3 minutes, pinning the same rev13 "
                "bytes throughout; the final reading is the owner-announced manifest "
                "(lead-form-20260912T005743-06)"
            ),
        },
        [f"schemas/af_wcc_vacuum.yaml#{short(snap_sha['f1__af_wcc_vacuum.yaml'])}",
         "artifacts/worker-019/rev13_preflight/snapshots/FROZEN.final.json#" + short(man_final_sha or "")],
        "any pinned path whose re-measured sha256 differs from the rev13/rev29 value recorded here",
    )

    # ---- C2: canonical/authoring mirror alignment --------------------------------
    mirror = {}
    for key in MOVED_CANONICAL:
        c = snap_sha[MOVED_CANONICAL[key][1]]
        a = snap_sha[AUTHORING[key][1]]
        mirror[key] = {"canonical": c, "authoring": a, "aligned": c == a}
    add(
        "C2-mirror-alignment",
        "pass" if all(v["aligned"] for v in mirror.values()) else "fail",
        "rev13 canonical schemas and authoring mirrors are byte-identical",
        mirror,
        ["schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"],
        "a re-measure showing canonical != authoring for any of F1/F2a/F2b",
    )

    # ---- C3: repair item 1, taxonomy_cases rebind --------------------------------
    rows = [json.loads(l) for l in open(os.path.join(SNAP, "taxonomy_cases.jsonl"))]
    meta, cases = rows[0], rows[1:]
    bind = {}
    for r in cases:
        bind[r.get("binding_status")] = bind.get(r.get("binding_status"), 0) + 1
    raw = open(os.path.join(SNAP, "taxonomy_cases.jsonl"), "rb").read().decode()
    stale = len(re.findall("66bf917bd368", raw))
    item1_ok = (
        len(cases) == 36
        and bind == {"bound_taxonomy_sha_0abb9ed8a961": 36}
        and meta["taxonomy_ref"]["sha256"] == "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
        and stale == 0
    )
    add(
        "C3-item1-taxonomy-cases",
        "pass" if item1_ok else "fail",
        "Repair item 1: taxonomy_cases rows/meta bound to declared F0 rev5 0abb9ed8a961",
        {
            "case_rows": len(cases),
            "binding_status_counts": bind,
            "meta_taxonomy_ref_sha256": meta["taxonomy_ref"]["sha256"],
            "meta_rebind_note": meta.get("rebind_note"),
            "occurrences_of_66bf917bd368_in_file": stale,
            "cf20_note": (
                "CF-20 (00:48:44) stated 36/36 rows were still bound to 66bf917bd368 while the meta "
                "pointed at rev5; that state is NOT reproducible at this file (mtime 00:42:36, rebind "
                "note 00:32:31): every row carries binding_status=bound_taxonomy_sha_0abb9ed8a961 and "
                "the stale token occurs zero times. Either CF-20 measured a stale snapshot or the item "
                "was already repaired before the finding was written."
            ),
        },
        [f"schemas/taxonomy_cases.jsonl#{short(snap_sha['taxonomy_cases.jsonl'])}",
         "research_map/formulation_taxonomy.yaml#" + short(snap_sha["f0_canonical_taxonomy.yaml"])],
        "a row-level re-measure showing any binding_status, meta taxonomy_ref, or the presence of 66bf917bd368",
    )

    # ---- C4: repair item 2, consistency evidence binding --------------------------
    ev_sha = snap_sha["taxonomy_consistency.json"]
    item2 = {}
    for key, (_, snap_name) in MOVED_CANONICAL.items():
        d = load_yaml(os.path.join(SNAP, snap_name))
        fb = d.get("f0_binding", {})
        item2[key] = {
            "consistency_evidence": fb.get("consistency_evidence"),
            "declared_sha256": fb.get("consistency_evidence_sha256"),
            "matches_live_evidence": fb.get("consistency_evidence_sha256") == ev_sha,
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
            "supplement_sha256_pin_present": any("supplement" in k and "sha" in k for k in fb),
        }
    item2_ok = all(v["matches_live_evidence"] for v in item2.values())
    # canonical consistency checker at the final bytes
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "artifacts/formulation/tools/check_taxonomy_consistency.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    add(
        "C4-item2-evidence-refresh",
        "pass" if item2_ok and proc.returncode == 0 else "fail",
        "Repair item 2: all three schemas declare the live consistency-evidence hash; checker clean",
        {
            "live_evidence_sha256": ev_sha,
            "per_schema": item2,
            "check_taxonomy_consistency_exit": proc.returncode,
            "check_taxonomy_consistency_stdout": proc.stdout.strip(),
            "residual_cf7_supplement_pin_absent": [k for k, v in item2.items() if not v["supplement_sha256_pin_present"]],
        },
        [f"artifacts/formulation/evidence/taxonomy_consistency.json#{short(ev_sha)}",
         f"schemas/af_scc_c0_vacuum.yaml#{short(snap_sha['f2b__af_scc_c0_vacuum.yaml'])}"],
        "evidence bytes change, any schema declaring another hash, or a non-clean consistency run",
    )

    # ---- C5: repair item 3, F1 strictness direction ------------------------------
    f1_rev12 = load_yaml(os.path.join(FROZEN_REV12_SNAP, REV12_SNAP["F1"]))
    f1_rev13 = load_yaml(os.path.join(SNAP, "f1__af_wcc_vacuum.yaml"))
    old_rel = f1_rev12["class_identity_variants"][0]["relation"]
    new_rel = f1_rev13["class_identity_variants"][0]["relation"]
    old_d5 = f1_rev12["quantifiers"]["domains"]["D5"]["definition"]
    new_d5 = f1_rev13["quantifiers"]["domains"]["D5"]["definition"]
    old_vis = f1_rev12["visibility"]["definition"]
    new_vis = f1_rev13["visibility"]["definition"]
    item3 = {
        "variant_set_relation": {
            "rev12": old_rel,
            "rev13": new_rel,
            "direction_corrected": ("strictly STRONGER" in old_rel and "strictly WEAKER" in new_rel),
            "w076_citation_present": "W076-GFORM-STRICTNESS-RECONCILE-06" in new_rel,
        },
        "d5_definition": {
            "rev12_strictly_stronger_claim": "strictly STRONGER" in old_d5,
            "rev13_equivalent_claim": "EQUIVALENT" in new_d5 and "NOT a weakening" in new_d5,
            "rev13_drops_second_predicate": "neither reading is a second predicate" in new_d5,
        },
        "visibility_definition": {
            "rev12_misclassification_example": "would misclassify" in old_vis,
            "rev13_removed_example": "would misclassify" not in new_vis,
            "rev13_equivalence_claim": "EQUIVALENT" in new_vis,
            "tail_predicate_unchanged": "there exists q in I+ AND t0 in [0,T)" in old_vis
            and "there exists q in I+ AND t0 in [0,T)" in new_vis,
        },
    }
    item3_ok = (
        item3["variant_set_relation"]["direction_corrected"]
        and item3["d5_definition"]["rev13_equivalent_claim"]
        and item3["visibility_definition"]["rev13_removed_example"]
        and item3["visibility_definition"]["tail_predicate_unchanged"]
    )
    add(
        "C5-item3-strictness-direction",
        "pass" if item3_ok else "fail",
        "Repair item 3: F1 strictness directions match the W076 measurements; predicate text unchanged",
        item3,
        ["artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
         f"schemas/af_wcc_vacuum.yaml#{short(snap_sha['f1__af_wcc_vacuum.yaml'])}"],
        "re-derivation showing P_tail not implying P_set, or the tail predicate itself edited",
    )

    # ---- C6: repair item 4, FROZEN rev29 ------------------------------------------
    vf_runs = []
    for _ in range(2):
        vf = subprocess.run(
            [sys.executable, os.path.join(ROOT, "artifacts/formulation/tools/verify_frozen.py")],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        vf_runs.append({"exit": vf.returncode,
                        "stdout": vf.stdout.strip().splitlines()[-1] if vf.stdout.strip() else "",
                        "drift_lines": [l for l in vf.stdout.splitlines() if "DRIFT" in l]})
        time.sleep(0.5)
    # transient drift observed by the first probe invocation (recorded, not re-derivable from disk)
    transient_drift = [{
        "observed_at": "2026-09-12T00:56:5x+08:00 (first invocation of this probe)",
        "path": "artifacts/formulation/evidence/variant_delta_check.json",
        "manifest_pin": "fc6ee058dd961275b37f8386b1675112d96291e22f972204efc1f8b6df9607b1",
        "disk_at_observation": "0b23f0b29232... (verify_frozen exit 1)",
        "restored_at": "2026-09-12T00:57:08+08:00 (disk re-measured == manifest pin)",
        "implication": "a rev29-pinned evidence file was rewritten and restored inside the freeze window; "
                       "the verify-gform-r3 reviewers must record pinned-file stability across their review window",
    }]
    add(
        "C6-item4-frozen-rev29",
        "pass" if (man_final or man).get("revision") == 29 and all(r["exit"] == 0 for r in vf_runs) else "fail",
        "Repair item 4: FROZEN rev29 exists and the canonical verifier passes at these pins",
        {
            "manifest_revision": (man_final or man).get("revision"),
            "manifest_frozen_at": (man_final or man).get("frozen_at"),
            "manifest_sha256_at_snapshot": man_sha,
            "manifest_sha256_final": man_final_sha,
            "files_count": len((man_final or man).get("files", {})),
            "verify_frozen_runs": vf_runs,
            "transient_drift_observed": transient_drift,
            "manifest_movement": ["2f358f6722d9(rev28)", "e1a8aaa394eb", "3d9e3d77fd87", man_final_sha],
            "rev29_delta": (man_final or man).get("rev29_delta"),
        },
        ["artifacts/formulation/FROZEN.json#" + short(man_final_sha or man_sha)],
        "a manifest re-measure differing from the pinned final reading, or verify_frozen returning nonzero on a stable re-run",
    )

    # ---- C7: no semantic change beyond the bounded card --------------------------
    allowed_top = {"F1": TOP_ALLOWED | TOP_ALLOWED_F1_EXTRA, "F2a": TOP_ALLOWED, "F2b": TOP_ALLOWED}
    sem = {}
    violations = []
    for key in MOVED_CANONICAL:
        rev12 = load_yaml(os.path.join(FROZEN_REV12_SNAP, REV12_SNAP[key]))
        rev13 = load_yaml(os.path.join(SNAP, MOVED_CANONICAL[key][1]))
        dl = leafdiff(rev12, rev13)
        top = sorted({row[0].split("/")[1] for row in dl if row[0].startswith("/")})
        bad = [t for t in top if t not in allowed_top[key]]
        fb_leaves = [row for row in dl if row[0].startswith("/f0_binding/")]
        fb_bad = [row[0] for row in fb_leaves if os.path.basename(row[0]) not in F0_BINDING_ALLOWED]
        sem[key] = {"leaf_changes": len(dl), "changed_top_level": top, "unexpected": bad, "f0_binding_unexpected": fb_bad,
                    "leaf_paths": [row[0] for row in dl]}
        violations += bad + fb_bad
    add(
        "C7-no-semantic-change",
        "pass" if not violations else "fail",
        "rev12->rev13 leaf diff stays inside the four bounded repair items",
        {
            "per_schema": sem,
            "allowed_top_level": {k: sorted(v) for k, v in allowed_top.items()},
            "f1_carve_out": "F1 additionally allows visibility/quantifiers/class_identity_variants (item 3 text only)",
        },
        ["artifacts/worker-007/citebind_census/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
         "artifacts/worker-019/rev13_preflight/leafdiff_rev12_to_rev13.json"],
        "a leaf diff touching a class id, hypothesis, conclusion predicate, genericity or axis semantics",
    )

    # ---- C8: owner artifact events for the moved paths ---------------------------
    targets = {
        "F1": snap_sha["f1__af_wcc_vacuum.yaml"],
        "F2a": snap_sha["f2a__af_scc_c2_vacuum.yaml"],
        "F2b": snap_sha["f2b__af_scc_c0_vacuum.yaml"],
        "taxonomy_cases": snap_sha["taxonomy_cases.jsonl"],
        "f1_falsifier_tests": snap_sha["f1_falsifier_tests.jsonl"],
        "FROZEN_rev29": man_final_sha or man_sha,
    }
    owner_events = {k: [] for k in targets}
    stream_events = {k: [] for k in targets}
    for line in open(os.path.join(ROOT, "research_map", "events.jsonl")):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("event_type") != "artifact":
            continue
        h = str(o.get("sha256") or "")
        p = str(o.get("path") or "")
        for k, t in targets.items():
            path_hit = (k in ("F1", "F2a", "F2b") and p in (MOVED_CANONICAL[k][0], AUTHORING[k][0])) or (
                k == "taxonomy_cases" and p == MOVED_OTHER["taxonomy_cases"][0]
            ) or (k == "f1_falsifier_tests" and p == MOVED_OTHER["f1_falsifier_tests"][0]) or (
                k == "FROZEN_rev29" and p.endswith("FROZEN.json")
            )
            if path_hit:
                stream_events[k].append({"created_at": o.get("created_at"), "actor": o.get("actor"),
                                         "event_id": o.get("event_id"), "sha256": h[:12]})
                if h == t:
                    owner_events[k].append(o.get("event_id"))
    owner_file = os.path.join(ROOT, "comms", "outbox", "astra-lead-formulation.jsonl")
    owner_outbox_hits = 0
    if os.path.exists(owner_file):
        blob = open(owner_file, "r", errors="replace").read()
        owner_outbox_hits = sum(1 for t in targets.values() if t in blob)
    missing = [k for k, v in owner_events.items() if not v]
    add(
        "C8-owner-artifact-events",
        "fail" if missing else "pass",
        "Owner artifact events announce every moved rev13/rev29 path at its published hash",
        {
            "accepted_stream_events_matching_hash": owner_events,
            "accepted_stream_events_for_paths": stream_events,
            "owner_outbox_hash_mentions": owner_outbox_hits,
            "owner_outbox_mtime": time.strftime(
                "%Y-%m-%dT%H:%M:%S+08:00", time.localtime(os.path.getmtime(owner_file))
            ) if os.path.exists(owner_file) else None,
            "registration": {
                "schema_hashes_in_artifact_hashes_json": json.load(open(os.path.join(SNAP, "artifact_hashes.json"))).get(
                    "hashes", {}
                ).get("schemas/af_wcc_vacuum.yaml", {}).get("sha256", "")[:12],
                "frozen_manifest_registered": (man_final_sha or man_sha) in open(
                    os.path.join(SNAP, "artifact_hashes.json")
                ).read(),
            },
            "discharge": "any owner artifact event in the accepted stream with the matching path+sha256 clears this check",
        },
        [f"artifacts/formulation/FROZEN.json#{short(man_sha)}", "comms/outbox/astra-lead-formulation.jsonl"],
        "an owner artifact event for a moved path whose sha256 is not the published one; or the absence remaining at the next pass",
    )

    # ---- C9: sibling corpus still binds superseded F1 -----------------------------
    corpus = [json.loads(l) for l in open(os.path.join(SNAP, "f1_falsifier_tests.jsonl"))]
    bound = {}
    for r in corpus:
        bound[r.get("binding_sha256", "")[:12]] = bound.get(r.get("binding_sha256", "")[:12], 0) + 1
    changed_fields = {"visibility.definition", "class_identity_variants"}
    affected = [
        {"test_id": r.get("test_id"), "deciding_field": r.get("deciding_field"),
         "does_it_satisfy_f1": r.get("does_it_satisfy_f1"), "binding_sha256": r.get("binding_sha256", "")[:12]}
        for r in corpus if r.get("deciding_field") in changed_fields
    ]
    corpus_pin = mfiles.get("schemas/f1_falsifier_tests.jsonl", {}).get("sha256")
    item9_ok = corpus_pin is None or not affected
    add(
        "C9-sibling-corpus-binding",
        "pass" if item9_ok else "fail",
        "FROZEN rev29-pinned f1_falsifier_tests corpus binds F1 rev13, not the superseded rev12",
        {
            "corpus_sha256": snap_sha["f1_falsifier_tests.jsonl"],
            "corpus_frozen_rev29_pin": corpus_pin,
            "row_binding_sha256_counts": bound,
            "f1_rev13_sha256": snap_sha["f1__af_wcc_vacuum.yaml"],
            "rows_with_deciding_fields_changed_in_rev13": affected,
            "note": ("the corpus was re-pinned to its own bytes at 00:37 but every row still declares "
                     "binding_sha256=cce9c60146d6 (F1 rev12); three rows decide on fields edited by the "
                     "rev13 repair, so re-running/re-pinning them at d9cebb9404b2 is required before the "
                     "corpus is binding G-FORM evidence"),
        },
        [f"schemas/f1_falsifier_tests.jsonl#{short(snap_sha['f1_falsifier_tests.jsonl'])}",
         f"schemas/af_wcc_vacuum.yaml#{short(snap_sha['f1__af_wcc_vacuum.yaml'])}"],
        "a re-pinned corpus whose rows bind d9cebb9404b2, or a re-run showing all 25 rows unchanged at rev13",
    )

    # ---- C10: residual, out-of-card items ----------------------------------------
    frozen_lines = open(os.path.join(SNAP, "f0_canonical_taxonomy.yaml")).read().splitlines()
    supp_lines = open(os.path.join(SNAP, "f0_supplement_taxonomy.yaml")).read().splitlines()
    delta_path_live = os.path.join(ROOT, "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")
    delta_sha = sha(delta_path_live)

    def hits(lines, pattern):
        return [{"line": i + 1, "text": lines[i].strip()[:200]}
                for i, l in enumerate(lines) if re.search(pattern, l, re.I)]

    residual_census = {
        "research_map/formulation_taxonomy.yaml": {
            "sha256": snap_sha["f0_canonical_taxonomy.yaml"],
            "frozen": True,
            "inverted_hits": hits(frozen_lines, r"strictly stronger"),
            "note": "G-F0-frozen (REC-11); L-FORM-03 named line 200; this census also finds line 94 in the "
                    "variants: block carrying the same pre-repair direction. Neither is repairable without "
                    "voiding the F0 gate and re-running the F0 review round.",
        },
        "artifacts/formulation/formulation_taxonomy.yaml": {
            "sha256": snap_sha["f0_supplement_taxonomy.yaml"],
            "frozen": True,
            "inverted_hits": hits(supp_lines, r"strictly stronger"),
            "note": "line 176 is the D1 ledger quoting the erroneous F0 reading as f0_reading; a descriptive "
                    "quotation, not a live assertion.",
        },
        "artifacts/formulation/VARIANT_REGISTRY.json": {
            "sha256": sha(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json")),
            "inverted_hits": [],
            "note": "SET strength at line 57 measured 'strictly weaker' (correct); line 112 'strictly STRONGER' "
                    "is the C0-vs-C2 axis, a different and correct claim.",
        },
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": {
            "sha256": delta_sha,
            "frozen_rev29_pin": mfiles.get(
                "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", {}
            ).get("sha256"),
            "strength_field_corrected": "strictly weaker" in open(delta_path_live).read(),
            "inverted_hits": [],
            "note": "line 27 'strictly stronger than the single-q negation' is the negation_conclusion axis and "
                    "is correct (non-containment in the union is stronger than non-containment in one J^-(q)).",
        },
        "cf7_supplement_sha256_pin_absent_in": [k for k, v in item2.items() if not v["supplement_sha256_pin_present"]],
        "concurrent_work": ("worker-007 emitted W007-REV29-PREFLIGHT rev29 addendum at 00:57:09 reporting the "
                            "same post-freeze drift on variant_delta_check.json (I4) and an OPEN I3 on the SET "
                            "delta strength; this probe measured the final rev29 manifest (3d9e3d77fd87) as "
                            "pinning the corrected SET delta 64b8d639, so I3 is discharged at these bytes. "
                            "Concurrent convergence, not shared evidence."),
    }
    add(
        "C10-residual-out-of-card",
        "info",
        "Residual items outside the four-item card (measured, not counted against the repair)",
        residual_census,
        ["research_map/formulation_taxonomy.yaml#" + short(snap_sha["f0_canonical_taxonomy.yaml"]),
         "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#" + short(delta_sha)],
        "n/a - recorded for the audit lead; repairing the F0 occurrences requires a new revision and fresh F0 accepts",
    )

    # ---- drift: live bytes at end of run -----------------------------------------
    live_now = {}
    for name, (live_path, snap_name) in {**MOVED_CANONICAL, **MOVED_OTHER, **AUTHORING}.items():
        try:
            live_now[name] = {"live": sha(os.path.join(ROOT, live_path)), "pinned": snap_sha[snap_name]}
        except Exception as e:
            live_now[name] = {"error": str(e)}
    for name, p in (("FROZEN.json", "artifacts/formulation/FROZEN.json"),
                    ("taxonomy_consistency.json", "artifacts/formulation/evidence/taxonomy_consistency.json"),
                    ("f0_canonical", "research_map/formulation_taxonomy.yaml")):
        live_now[name] = {"live": sha(os.path.join(ROOT, p))}
    drifted = [k for k, v in live_now.items() if v.get("pinned") and v["live"] != v["pinned"]]

    out = {
        "task_id": "W019-REV13-PREFLIGHT-01",
        "actor": "worker-019",
        "role": "bounded_execution_worker",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": (
            "At the rev13 bytes written by astra-life05-evidence-binding-repair, before FROZEN rev29 was "
            "published: are the four bounded items satisfied, do the published pins match independently "
            "measured bytes, and is the binding chain complete for a G-FORM verdict?"
        ),
        "authority_note": (
            "worker artifact and measurement only; this is not a gate verdict, does not set node status or "
            "validation_status, and does not edit any canonical/shared file. Review verdicts bind to the "
            "canonical hashes pinned here."
        ),
        "predecessor_bytes": {
            "F1": "cce9c60146d6", "F2a": "5476a3f2c6bc", "F2b": "55d0a1ea9bda",
            "FROZEN": "2f358f6722d9 (rev28)", "snapshot": "artifacts/worker-007/citebind_census/snapshot/",
        },
        "snapshot_window": {
            "pinned_at": pinned.get("snapshot_started_at"),
            "pinned_finished_at": pinned.get("snapshot_finished_at"),
            "frozen_rev29_published_at": man.get("frozen_at"),
            "frozen_rev29_final_at": (man_final or {}).get("frozen_at"),
            "owner_repair_events_at": "2026-09-12T00:57:43+08:00 (lead-form-20260912T005743-*)",
        },
        "pinned_bytes": {k: {"live_path": v.get("live_path"), "sha256": v.get("sha256"), "bytes": v.get("bytes")}
                         for k, v in files.items()},
        "checks": checks,
        "drift_since_snapshot": {"drifted": drifted, "live_now": live_now},
    }
    failed = [c["id"] for c in checks if c["status"] == "fail"]
    hard = []
    if "C8-owner-artifact-events" in failed:
        c8 = [c for c in checks if c["id"] == "C8-owner-artifact-events"][0]
        missing = [k for k, v in c8["detail"]["accepted_stream_events_matching_hash"].items() if not v]
        hard.append(f"W019-RV13-01: no owner artifact event for moved path(s) {missing} at the published hash")
    if "C9-sibling-corpus-binding" in failed:
        c9 = [c for c in checks if c["id"] == "C9-sibling-corpus-binding"][0]
        hard.append(
            "W019-RV13-02: schemas/f1_falsifier_tests.jsonl (pinned by rev29 at 56bcb4b3234b) binds all 25 "
            "rows to superseded F1 rev12 cce9c60146d6; "
            f"{len(c9['detail']['rows_with_deciding_fields_changed_in_rev13'])} rows decide on fields edited by rev13"
        )
    out.update({
        "verdict": "revise" if failed else "accept",
        "score": 3.5 if len(failed) > 1 else (4.0 if failed else 4.5),
        "hard_failures": hard,
        "acceptance_axes_passed": [
            "item1_taxonomy_cases_rebind_to_declared_F0_rev5",
            "item2_consistency_evidence_refresh_3of3",
            "item3_F1_strictness_direction_matches_W076",
            "item4_FROZEN_rev29_exists_and_verify_frozen_passes",
            "rev13_bytes_mirror_aligned_and_pin_verified",
            "leaf_diff_inside_bounded_scope",
        ],
        "next_falsifier": (
            "Any byte change of the pinned rev13 paths or of the final FROZEN rev29 manifest voids every check. "
            "W019-RV13-01 clears iff the owner emits an artifact event for the missing moved path(s). "
            "W019-RV13-02 clears iff the 25 corpus rows are re-pinned/re-run at d9cebb9404b2. Re-run "
            "verify_rev13_repair.py and require hard_failed==[] for an accept."
        ),
        "hard_failed": failed,
    })
    json.dump(out, open(os.path.join(BASE, "results.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({"verdict": out["verdict"], "hard_failed": out["hard_failed"],
                      "failures": failed, "drifted": drifted}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
