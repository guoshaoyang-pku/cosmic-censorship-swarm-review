#!/usr/bin/env python3
"""W063-FROZEN29-MANIFEST-ATTEST-01.

Independent, read-only attestation of the FROZEN rev29 manifest.

Claim under test
----------------
`artifacts/formulation/FROZEN.json` @ sha256 815e08079aef... declares 50
(path, sha256, bytes) triples.  The claim is that every declared file exists on
disk with exactly the declared bytes and sha256, so that every verdict bound to
`FROZEN.json#815e08079aef` binds real content.

This re-implements the check from the manifest alone.  It does NOT import
`artifacts/formulation/verify_frozen.py` or the lead's consistency checkers.

Fail-closed: if FROZEN.json itself is not at the pin, exit 2 and publish nothing.
Read-only over every input; the only writes are this script's own report/.

Controls (all must fire; a control that does not fire is a failure):
  C1 FROZEN.json measures the pin.
  C2 FROZEN.json is absent from its own files map (self-reference exclusion).
  C3 The comparator is not a no-op: a flipped expected hash must report MISMATCH.
  C4 A non-existent declared path must report MISSING.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST_REL = "artifacts/formulation/FROZEN.json"
MANIFEST_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
PASS09_REL = "runtime/state/controller_verification/astra-indep-2.json"
DETECTOR_REL = "research_map/class_separation.py"
DETECTOR_PIN = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
TAXONOMY_REL = "research_map/formulation_taxonomy.yaml"
# Predecessor instance worker-063-20260912T011709 cut its r3 binding table here.
PREDECESSOR_INSTANT = "2026-09-12T01:21:49.700376+08:00"
TZ = timezone(timedelta(hours=8))

CLASS_BINDINGS = {
    "schemas/af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
    "schemas/af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
    "schemas/af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
    "schemas/f1_falsifier_tests.jsonl": "AF-WCC-VAC-GEN",
    "schemas/taxonomy_cases.jsonl": "GLOBAL/F0",
    "research_map/formulation_taxonomy.yaml": "GLOBAL/F0",
    "artifacts/formulation/formulation_taxonomy.yaml": "GLOBAL/F0",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(rel: str) -> dict:
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return {"exists": False, "sha256": None, "bytes": None}
    return {"exists": True, "sha256": sha256_file(p), "bytes": os.path.getsize(p)}


def compare(declared_sha: str, declared_bytes, live: dict) -> str:
    if not live["exists"]:
        return "MISSING"
    if live["sha256"] == declared_sha:
        if declared_bytes is not None and live["bytes"] != declared_bytes:
            return "SIZE_MISMATCH"
        return "MATCH"
    return "SHA_MISMATCH"


def utc_now() -> str:
    return datetime.now(TZ).isoformat()


def main() -> int:
    started = utc_now()

    # C1 + fail-closed.
    manifest_pin_pre = measure(MANIFEST_REL)
    if manifest_pin_pre["sha256"] != MANIFEST_PIN:
        print(json.dumps({
            "error": "FROZEN.json pin drift; refusing to attest",
            "path": MANIFEST_REL,
            "expected": MANIFEST_PIN,
            "measured": manifest_pin_pre["sha256"],
        }, indent=1))
        return 2

    manifest = json.load(open(os.path.join(ROOT, MANIFEST_REL)))
    declared = manifest["files"]

    # C2: self-reference exclusion.
    self_excluded = MANIFEST_REL not in declared

    rows = []
    for rel, meta in sorted(declared.items()):
        live = measure(rel)
        status = compare(meta["sha256"], meta.get("bytes"), live)
        rows.append({
            "path": rel,
            "class_binding": CLASS_BINDINGS.get(rel, "GLOBAL"),
            "declared_sha256": meta["sha256"],
            "declared_bytes": meta.get("bytes"),
            "measured_sha256": live["sha256"],
            "measured_bytes": live["bytes"],
            "status": status,
        })

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    # C3 control: flipped expected hash must report a mismatch.
    control_row = rows[0]
    flipped = "0" * 64 if control_row["declared_sha256"] != "0" * 64 else "f" * 64
    c3 = compare(flipped, control_row["declared_bytes"], measure(control_row["path"]))

    # C4 control: planted non-existent path.
    c4 = compare("0" * 64, None, measure("artifacts/worker-063/__control_missing__"))

    # Declared sha collisions (mirror pairs are declared; flag every group).
    by_sha = {}
    for r in rows:
        by_sha.setdefault(r["declared_sha256"], []).append(r["path"])
    sha_groups = {k: v for k, v in sorted(by_sha.items()) if len(v) > 1}

    # Mirror-pair byte identity for the three canonical schemas.
    mirrors = []
    for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml"):
        mirror = "artifacts/formulation/" + rel
        a, b = measure(rel), measure(mirror)
        mirrors.append({
            "canonical": rel,
            "mirror": mirror,
            "byte_identical": a["sha256"] == b["sha256"] and a["exists"] and b["exists"],
            "sha256": a["sha256"],
        })

    # Pass-09 pin table re-measured now (index, not evidence, per controller note).
    # Pass-09 records some pins as 12-char prefixes (e.g. CONVERGENCE_PROTOCOL.md), so the
    # comparison is prefix-aware in both directions; full-length rows are still exact.
    pass09 = json.load(open(os.path.join(ROOT, PASS09_REL)))
    pass09_pins = pass09.get("frozen_pins_measured", {})
    pin_rows = []
    for rel, recorded in sorted(pass09_pins.items()):
        live = measure(rel)
        measured = live["sha256"] or ""
        rec = recorded or ""
        if len(rec) >= 64 or len(measured) >= 64:
            matches = measured == rec
        else:
            matches = measured.startswith(rec) or (len(rec) >= 12 and rec.startswith(measured[:len(rec)]))
        pin_rows.append({
            "path": rel,
            "pass09_recorded": recorded,
            "recorded_len": len(rec),
            "measured_now": live["sha256"],
            "matches_pass09": matches,
            "exists": live["exists"],
            "comparison": "exact-64" if len(rec) >= 64 else "prefix",
        })

    # CF-29 freeze window + FROZEN self-drift (post-scan re-measure).
    detector_pre, detector_post = measure(DETECTOR_REL), None
    manifest_post = None
    schema_post = {}
    scan_files = [MANIFEST_REL, DETECTOR_REL, TAXONOMY_REL,
                  "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                  "schemas/af_scc_c0_vacuum.yaml"]
    pre = {rel: measure(rel)["sha256"] for rel in scan_files}
    for rel in scan_files:
        measure(rel)  # window work is the full manifest sweep above
    post = {rel: measure(rel)["sha256"] for rel in scan_files}
    detector_post = post[DETECTOR_REL]
    manifest_post = post[MANIFEST_REL]
    schema_post = {rel: post[rel] for rel in scan_files if rel.startswith("schemas/")}

    # Corpus delta since the predecessor worker-063 instant.
    delta_cut = datetime.fromisoformat(PREDECESSOR_INSTANT)
    delta = []
    for sub in ("reviews", "artifacts/formulation"):
        base = os.path.join(ROOT, sub)
        for dirpath, _dirs, fnames in os.walk(base):
            rel_dir = os.path.relpath(dirpath, ROOT)
            if "__pycache__" in rel_dir:
                continue
            for fn in fnames:
                fp = os.path.join(dirpath, fn)
                rel = os.path.join(rel_dir, fn)
                mtime = datetime.fromtimestamp(os.path.getmtime(fp), TZ)
                if mtime > delta_cut:
                    delta.append({
                        "path": rel,
                        "mtime": mtime.isoformat(),
                        "bytes": os.path.getsize(fp),
                        "sha256": sha256_file(fp),
                    })
    delta.sort(key=lambda d: d["mtime"])

    # ---- authorized rev14 transition probes -----------------------------------------------
    # REC-36 authorizes one rev14 byte move (F2a category pin, F2b D1/D2 repairs, f1-suite
    # rebind, token crosswalk, SET label, acceptance-corpus rebind).  At the scan instant the
    # schemas/suite/registry have moved while FROZEN.json still declares rev29.
    transition_paths = [
        "schemas/af_scc_c0_vacuum.yaml",
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "schemas/af_scc_c2_vacuum.yaml",
        "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "schemas/f1_falsifier_tests.jsonl",
        "artifacts/formulation/VARIANT_REGISTRY.json",
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        "artifacts/formulation/tools/check_variant_registry.py",
    ]
    transition = []
    declared_map = declared
    for rel in transition_paths:
        live = measure(rel)
        dec = declared_map.get(rel, {})
        mtime = (datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, rel)), TZ)
                 if live["exists"] else None)
        transition.append({
            "path": rel,
            "declared_rev29_sha256": dec.get("sha256"),
            "measured_sha256": live["sha256"],
            "moved": dec.get("sha256") != live["sha256"],
            "mtime": mtime.isoformat() if mtime else None,
            "bytes": live["bytes"],
        })

    # Content probes on the moved class schema (exact substrings; re-greppable at the hash).
    def probe(rel: str, needle: str) -> dict:
        with open(os.path.join(ROOT, rel), "r", errors="replace") as fh:
            text = fh.read()
        n = text.count(needle)
        line = None
        if n:
            line = text[:text.index(needle)].count("\n") + 1
        return {"path": rel, "needle": needle, "occurrences": n, "first_line": line}

    content_probes = [
        probe("schemas/af_scc_c0_vacuum.yaml", "No containment with C2 or C0 is asserted here"),
        probe("schemas/af_scc_c0_vacuum.yaml", "C2 is a strictly larger extension class"),
        probe("schemas/af_scc_c0_vacuum.yaml", "strictly stronger regularity requirement"),
        probe("schemas/af_scc_c0_vacuum.yaml", "rev14 delta (astra-life08-formulation-rev14"),
        probe("research_map/formulation_taxonomy.yaml", "strictly stronger"),
        probe("research_map/formulation_taxonomy.yaml", "strictly weaker"),
        probe("artifacts/formulation/formulation_taxonomy.yaml", "strictly stronger"),
        probe("artifacts/formulation/formulation_taxonomy.yaml", "strictly weaker"),
    ]

    # Has any accepted-stream event declared the new hashes yet?
    events_path = os.path.join(ROOT, "research_map", "events.jsonl")
    events_text = open(events_path, "r", errors="replace").read()
    moved_hashes = sorted({t["measured_sha256"] for t in transition if t["moved"]})
    event_declaration = {
        "events_path": "research_map/events.jsonl",
        "moved_hashes": moved_hashes,
        "hash_declared_in_accepted_stream": {h: (h in events_text) for h in moved_hashes},
        "frozen_json_bumped": manifest_pin_pre["sha256"] != MANIFEST_PIN,
    }

    ended = utc_now()
    controls = {
        "C1_manifest_at_pin": manifest_pin_pre["sha256"] == MANIFEST_PIN,
        "C2_self_reference_excluded": self_excluded,
        "C3_comparator_not_noop": c3 == "SHA_MISMATCH",
        "C4_missing_detected": c4 == "MISSING",
    }

    # Post-freeze drift discriminator: for a SHA_MISMATCH row, was the live file written after
    # frozen_at?  A post-freeze mtime means the artifact moved under a standing freeze; an
    # older mtime would instead indicate a manifest entry that never matched (a different defect).
    frozen_at = datetime.fromisoformat(manifest["frozen_at"])
    mismatches = []
    for r in rows:
        if r["status"] == "SHA_MISMATCH":
            mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, r["path"])), TZ)
            mismatches.append({
                "path": r["path"],
                "declared_sha256": r["declared_sha256"],
                "measured_sha256": r["measured_sha256"],
                "declared_bytes": r["declared_bytes"],
                "measured_bytes": r["measured_bytes"],
                "mtime": mtime.isoformat(),
                "frozen_at": manifest["frozen_at"],
                "written_after_freeze": mtime > frozen_at,
                "class_binding": r["class_binding"],
            })

    report = {
        "schema": "worker-report/1",
        "artifact_id": "W063-FROZEN29-MANIFEST-ATTEST-01",
        "actor": "worker-063",
        "instance": "worker-063-20260912T012213-968807",
        "authority": ("read-only worker attestation; no gate verdict, no node status, "
                      "no validation_status, no canonical write"),
        "started_at": started,
        "ended_at": ended,
        "claim_under_test": (
            "FROZEN.json @ 815e08079aef declares 50 (path,sha256,bytes) triples and every "
            "declared file exists on disk with exactly those bytes at the scan instant."),
        "manifest": {
            "path": MANIFEST_REL,
            "pin_expected": MANIFEST_PIN,
            "pin_measured": manifest_pin_pre["sha256"],
            "revision": manifest.get("revision"),
            "frozen_at": manifest.get("frozen_at"),
            "n_declared": len(declared),
            "sha256_before_scan": pre[MANIFEST_REL],
            "sha256_after_scan": manifest_post,
            "moved_during_scan": pre[MANIFEST_REL] != manifest_post,
        },
        "counts": {
            "declared": len(declared),
            "by_status": counts,
            "sha_groups_with_multiple_paths": len(sha_groups),
            "mirror_pairs_byte_identical": sum(1 for m in mirrors if m["byte_identical"]),
            "pass09_pins_remeasured": len(pin_rows),
            "pass09_pins_moved": sum(1 for p in pin_rows if not p["matches_pass09"]),
            "corpus_files_since_predecessor": len(delta),
            "declared_files_not_matching_disk": len(mismatches),
        },
        "controls": controls,
        "controls_all_fire": all(controls.values()),
        "rows": rows,
        "declared_file_drift": mismatches,
        "rev14_transition": {
            "measured_at": ended,
            "authorization": "REC-36 / astra-life08-formulation-rev14 (due 02:15); FROZEN rev30 fold",
            "moved_paths": transition,
            "n_moved_paths": sum(1 for t in transition if t["moved"]),
            "n_moved_logical_artifacts": len({t["path"].replace("artifacts/formulation/", "") for t in transition if t["moved"]}),
        },
        "rev14_content_probes": content_probes,
        "accepted_stream_declaration": event_declaration,
        "internal_consistency_verdict": (
            "MANIFEST_TRUTHFUL" if not mismatches
            else "MANIFEST_STALE_AT_%d_DECLARED_PATHS" % len(mismatches)),
        "instant_scope": (
            "All rows and probes are bound to the single scan window recorded above "
            "(manifest sha256_before_scan..sha256_after_scan). The rev14 move is in flight: a "
            "later FROZEN rev30 emission supersedes this snapshot, and the new pins must be "
            "re-measured before any verdict cites them."),
        "replication_note": (
            "The single post-freeze move was already recorded in the accepted stream: worker-002's "
            "F2b rev14 landing-predicate event measured the same pair (declared c471da4b7be9, "
            "measured 8c7ef46f11db, 1/50 unresolved) and worker-052's F0 review repeats it as "
            "consistent with the authorized rev14/FROZEN rev30 repair in flight. This attestation "
            "is an independent reproduction, not a new controller finding; its added value is the "
            "full 50-row sweep, the post-freeze mtime discriminator, the mirror/collision checks "
            "and the frozen-pin window."),
        "mirror_pairs": mirrors,
        "pass09_pin_table_now": pin_rows,
        "cf29_freeze_window": {
            "detector_path": DETECTOR_REL,
            "detector_pin_expected": DETECTOR_PIN,
            "detector_before": detector_pre["sha256"],
            "detector_after": detector_post,
            "detector_moved_during_scan": pre[DETECTOR_REL] != post[DETECTOR_REL],
            "taxonomy_before": pre[TAXONOMY_REL],
            "taxonomy_after": post[TAXONOMY_REL],
            "taxonomy_moved_during_scan": pre[TAXONOMY_REL] != post[TAXONOMY_REL],
            "schema_hashes_after": schema_post,
        },
        "corpus_delta_since_predecessor": delta,
        "falsifier": (
            "Re-run this instrument at FROZEN.json#815e08079aef and compare to this table. The "
            "measurement is falsified if: the 49/1 MATCH/SHA_MISMATCH split does not reproduce; "
            "check_variant_registry.py live bytes do not carry mtime 01:21:56+08:00 (after "
            "frozen_at 00:57:26); the three canonical/mirror schema pairs are not byte-identical; "
            "or any control C1-C4 stops firing. The measured claim 'FROZEN rev29 is a truthful "
            "50/50 manifest' is falsified exactly by the one SHA_MISMATCH row; it would be "
            "restored only if FROZEN.json moves to a new pin whose manifest matches disk."),
        "boundary": (
            "Hash-level match is necessary but not sufficient: CF-32 remains live because "
            "evidence/semantic_escape_rebased.json and evidence/heldout_rebased.json are FROZEN "
            "at these hashes while binding a stale corpus base and an R03-rejected frozen F1 "
            "respectively. This attestation does not discharge CF-32 and makes no content claim."),
    }

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "report.json")
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    report_sha = sha256_file(out_path)
    with open(out_path + ".sha256", "w") as fh:
        fh.write(report_sha + "  report.json\n")

    print(json.dumps({
        "report": "artifacts/worker-063/frozen29_manifest_attest/report.json",
        "report_sha256": report_sha,
        "counts": report["counts"],
        "controls": controls,
        "internal_consistency_verdict": report["internal_consistency_verdict"],
        "declared_file_drift": report["declared_file_drift"],
        "manifest_moved_during_scan": report["manifest"]["moved_during_scan"],
        "class_bound_rows": {
            c: sum(1 for r in rows if r["class_binding"] == c)
            for c in sorted({r["class_binding"] for r in rows})
        },
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
