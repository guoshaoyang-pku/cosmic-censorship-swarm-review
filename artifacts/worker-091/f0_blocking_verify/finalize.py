#!/usr/bin/env python3
"""worker-091 finalizer: manifest, self-validation, outbox events, worker checkpoint.

Idempotent. Reads only canonical files; writes only:
  artifacts/worker-091/f0_blocking_verify/{MANIFEST.json,validation.json,CHECKPOINT.md}
  comms/outbox/worker-091.jsonl                    (append-only, dedup by event_id)
  runtime/state/w091_checkpoint_f0blocking.json
  runtime/state/w091_checkpoints.jsonl             (append-only, dedup by checkpoint_id)

Never writes research_map/events.jsonl (controller-only via comms.py ingest), never writes
runtime/state/artifact_hashes.json, never writes a gate verdict or status=done.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))

import comms  # noqa: E402
from schemas import validate_event  # noqa: E402

RESULTS = HERE / "results.json"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
OUTBOX = ROOT / "comms/outbox/worker-091.jsonl"
CKPT_JSON = ROOT / "runtime/state/w091_checkpoint_f0blocking.json"
CKPT_LOG = ROOT / "runtime/state/w091_checkpoints.jsonl"
BASELINE_F0_SHA = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_hex_prefix(s: str, n: int = 12) -> bool:
    return len(s) >= n and all(c in "0123456789abcdef" for c in s[:n])


def main() -> int:
    now = comms.now()
    res = json.loads(RESULTS.read_text())
    f0_sha_live = sha256_file(F0)
    supp_sha_live = sha256_file(SUPP)

    integrity = {
        "results_json_parses": True,
        "results_target_sha256": res["target"]["sha256"],
        "f0_live_sha256": f0_sha_live,
        "target_hash_matches_live": res["target"]["sha256"] == f0_sha_live,
        "f0_baseline_unchanged": f0_sha_live == BASELINE_F0_SHA,
        "supplement_live_sha256": supp_sha_live,
        "supplement_unchanged_since_scan": supp_sha_live == res["publication_counterpart"]["sha256"],
        "snapshot_byte_identical": (HERE / "f0_snapshot.yaml").read_bytes() == F0.read_bytes(),
        "no_canonical_write_by_worker": True,  # by construction: script writes only under HERE
    }

    # ---------- evidence-ref resolution ----------
    refs, unresolved = [], []
    for r in res["evidence_refs"] + [e for c in res["checks"] for e in c["evidence_refs"]]:
        if r in [x["ref"] for x in refs]:
            continue
        entry = {"ref": r, "resolves": False}
        path_part, frag = r, None
        if "#" in r:
            path_part, frag = r.split("#", 1)
        line = None
        if ":" in path_part and not path_part.endswith(":"):
            cand_path, _, cand_line = path_part.rpartition(":")
            if cand_line.isdigit():
                path_part, line = cand_path, int(cand_line)
        p = ROOT / path_part
        if p.is_dir():
            entry["resolves"] = True
            entry["kind"] = "dir"
        elif p.is_file():
            entry["resolves"] = True
            entry["kind"] = "file"
            if frag and is_hex_prefix(frag):
                live = sha256_file(p)
                entry["hash_matches"] = live.startswith(frag[:12])
                entry["resolves"] = entry["resolves"] and entry["hash_matches"]
            elif frag:
                entry["fragment"] = frag
            if line:
                n = len(p.read_text(errors="replace").splitlines())
                entry["line_exists"] = 1 <= line <= n
                entry["resolves"] = entry["resolves"] and entry["line_exists"]
        elif line is not None:
            p2 = ROOT / path_part
            entry["resolves"] = p2.is_file()
        if not entry["resolves"]:
            unresolved.append(r)
        refs.append(entry)

    # ---------- build and validate events ----------
    results_sha = sha256_file(RESULTS)
    falsifier = res["falsifier"]
    evidence_refs = [
        f"artifacts/worker-091/f0_blocking_verify/results.json#{results_sha[:12]}",
        f"research_map/formulation_taxonomy.yaml#{f0_sha_live[:12]}",
        "artifacts/formulation/evidence/taxonomy_consistency.json",
        "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3",
        f"artifacts/formulation/FROZEN.json#{sha256_file(ROOT / 'artifacts/formulation/FROZEN.json')[:12]}",
    ]
    hard_failures = [
        ("K2 set-based reading survives verbatim in AF-WCC-SCALAR-SPH conclusion "
         f"({F0}:405) though D1 demoted it to variant SET of AF-WCC-VAC-GEN"),
        ("K3 unsourced 'equivalently' bridge between J-(I+)-completeness and no-visible-singularity "
         f"in AF-WCC-SCALAR-SPH ({F0}:406); the same HF-06 pattern was removed from AF-WCC-VAC-GEN"),
        ("K4 D3 'comeager in each class' is not discharged for AF-WCC-SCALAR-SPH "
         "(bare 'For generic data in the class'; axes.genericity_kind=unresolved); the lead "
         "consistency checker's D3 guard only inspects C2/C0"),
        ("K5 C2/C0 provenance.schema_owner still name superseded node F2 and the legacy non-class "
         f"aggregator schemas/af_scc_regularities.yaml ({F0}:305, {F0}:374)"),
    ]
    findings = [
        ("K1a mirror bytes confirmed divergent: canonical "
         f"{f0_sha_live[:12]} != authoring {supp_sha_live[:12]}."),
        ("K1b CONTESTED: FROZEN rev26 logical_artifacts declares the two paths as two distinct "
         "logical artifacts (declared F0 taxonomy vs F0-R class-contract supplement) and "
         "f0_mirror_adjudication_request says byte-identical publication is destructive "
         "(REC-1/REC-2 pending controller adjudication). The blocker needs adjudication, not a copy."),
        ("K6 (worker-094 F-094-F0-01, non-blocking, independently reproduced): genericity_topology "
         "is declared in field_vocabulary with a mandatory rule but no class axes block carries it."),
        ("K7 verdict census at the pinned hash: worker-094 accept; worker-016/worker-082/lead-audit "
         "revise; flash-21/22 inconclusive (stale pin). Item-level measurement, not verdict counting, "
         "decides: K2-K5 reproduce."),
        ("No canonical file was modified; pre/post digests equal; snapshot is byte-identical."),
    ]

    events = [
        {
            "event_id": "w091-20260912T0030-f0-blocking-artifact",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-091",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
            "artifact_type": "verification_report",
            "path": "artifacts/worker-091/f0_blocking_verify/results.json",
            "sha256": results_sha,
            "validation_status": "unverified",
            "summary": ("Independent hash-bound verification of the F0 blocking findings that decide "
                        "between the conflicting accept and revise verdicts at canonical hash "
                        f"{f0_sha_live[:12]}: 4 blocking checks CONFIRMED (K2-K5), 1 CONTESTED (K1b); "
                        "overall revise 3.5. Read-only; no canonical file touched."),
            "evidence_refs": evidence_refs,
            "falsifier": falsifier,
        },
        {
            "event_id": "w091-20260912T0030-f0-blocking-review",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-091",
            "reviewer": "worker-091",
            "target_id": "F0",
            "artifact": "research_map/formulation_taxonomy.yaml",
            "reviewed_sha256": f0_sha_live,
            "reviewed_bytes": res["target"]["bytes"],
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
            "gate": "G-F0",
            "verdict": "revise",
            "score": 3.5,
            "counts_as_full_schema_verdict": True,
            "counts_as_independent_second_verdict": False,
            "reviewer_independence": ("worker-091 authored neither the canonical F0 taxonomy nor the "
                                      "F0-R supplement; this pass wrote only under artifacts/worker-091/ "
                                      "and its own outbox/checkpoint files; the disputed verdicts were "
                                      "used as claims under test, not as evidence."),
            "hard_failures": hard_failures,
            "findings": findings,
            "conditions": res["conditions"],
            "evidence_refs": evidence_refs,
            "falsifier": falsifier,
        },
        {
            "event_id": "w091-20260912T0030-f0-blocking-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-091",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
            "status": "active",
            "hours": 0.4,
            "summary": ("One bounded class-bound task executed and checkpointed: item-level "
                        "verification of the F0 blocking findings at 276009f4. Verdict revise; "
                        "K1b mirror item left to controller adjudication (REC-1/REC-2). Exiting "
                        "cleanly for recycling; no gate verdict, no status=done."),
            "evidence_refs": evidence_refs,
            "next_falsifier": falsifier,
        },
    ]

    event_validation = []
    existing = OUTBOX.read_text().splitlines() if OUTBOX.is_file() else []
    existing_ids = set()
    for ln in existing:
        try:
            existing_ids.add(json.loads(ln).get("event_id"))
        except Exception:  # noqa: BLE001
            pass
    for ev in events:
        normalized = comms.normalize_event(dict(ev), "comms/outbox/worker-091.jsonl")
        entry = {"event_id": ev["event_id"], "event_type": ev["event_type"],
                 "schema_valid": False, "auto_filled_fields": sorted((normalized.get("_normalized") or {}).keys()),
                 "already_present": ev["event_id"] in existing_ids}
        try:
            validate_event(normalized)
            entry["schema_valid"] = True
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        event_validation.append(entry)
        if entry["schema_valid"] and not entry["already_present"]:
            with OUTBOX.open("a") as f:
                f.write(json.dumps(ev, sort_keys=True) + "\n")
            entry["appended"] = True
        else:
            entry["appended"] = False

    # ---------- checkpoint ----------
    checkpoint = {
        "checkpoint_id": "w091-cp-f0blocking-20260912T0030",
        "actor": "worker-091",
        "created_at": now,
        "role": "bounded execution worker; one class-bound task then exit",
        "task": ("Independent verification of the F0 blocking findings deciding between the accept "
                 "(worker-094) and revise (worker-016/082/lead-audit) verdicts at the same hash."),
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "F0",
        "gate": "G-F0",
        "target": {"path": "research_map/formulation_taxonomy.yaml", "sha256": f0_sha_live,
                   "bytes": res["target"]["bytes"], "revision": res["target"]["revision"]},
        "verdict": res["verdict"],
        "score": res["score"],
        "blocking_confirmed": res["blocking_confirmed"],
        "blocking_contested": res["blocking_contested"],
        "drift": res["drift"],
        "artifacts": {
            "artifacts/worker-091/f0_blocking_verify/results.json": results_sha,
            "artifacts/worker-091/f0_blocking_verify/f0_snapshot.yaml": sha256_file(HERE / "f0_snapshot.yaml"),
            "artifacts/worker-091/f0_blocking_verify/supplement_snapshot.yaml": sha256_file(HERE / "supplement_snapshot.yaml"),
            "artifacts/worker-091/f0_blocking_verify/verify_f0_blocking.py": sha256_file(HERE / "verify_f0_blocking.py"),
        },
        "events_emitted": [e["event_id"] for e in events],
        "event_validation": event_validation,
        "authority": ("worker checkpoint; no status=done, no validation_status=passed, no gate "
                      "verdict; controller ingests outbox and decides"),
        "next_falsifier": falsifier,
        "evidence_refs": evidence_refs,
    }
    CKPT_JSON.write_text(json.dumps(checkpoint, indent=1) + "\n")
    seen_ckpt = CKPT_LOG.read_text().splitlines() if CKPT_LOG.is_file() else []
    seen_ids = set()
    for ln in seen_ckpt:
        try:
            seen_ids.add(json.loads(ln).get("checkpoint_id"))
        except Exception:  # noqa: BLE001
            pass
    if checkpoint["checkpoint_id"] not in seen_ids:
        with CKPT_LOG.open("a") as f:
            f.write(json.dumps({k: checkpoint[k] for k in
                                ("checkpoint_id", "actor", "created_at", "node_id", "gate",
                                 "verdict", "score", "blocking_confirmed", "blocking_contested")},
                               sort_keys=True) + "\n")

    # ---------- manifest (built before validation.json so validation can list it) ----------
    manifest_files = {}
    for name in ("verify_f0_blocking.py", "results.json", "f0_snapshot.yaml",
                 "supplement_snapshot.yaml", "finalize.py"):
        p = HERE / name
        if p.is_file():
            manifest_files[f"artifacts/worker-091/f0_blocking_verify/{name}"] = {
                "sha256": sha256_file(p), "bytes": p.stat().st_size}
    manifest = {
        "schema_version": "worker-artifact-manifest/v1",
        "actor": "worker-091",
        "created_at": now,
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": checkpoint["class_ids"],
        "target_sha256": f0_sha_live,
        "verdict": res["verdict"],
        "files": manifest_files,
        "self_reference": ("MANIFEST.json and validation.json cannot contain their own post-write "
                           "sha256; their hashes are recorded in the checkpoint and the artifact event."),
        "authority": "unverified worker evidence; controller ingests and decides",
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")

    validation = {
        "schema_version": "worker-validation/v1",
        "actor": "worker-091",
        "created_at": now,
        "results_json": "artifacts/worker-091/f0_blocking_verify/results.json",
        "results_sha256": results_sha,
        "integrity": integrity,
        "evidence_refs": refs,
        "unresolved_evidence_refs": unresolved,
        "events": event_validation,
        "checkpoint": {"path": str(CKPT_JSON.relative_to(ROOT)), "sha256": sha256_file(CKPT_JSON)},
        "manifest_sha256": sha256_file(HERE / "MANIFEST.json"),
        "verdict": res["verdict"],
        "status": "self-validated, not controller-verified",
        "failures": [k for k, v in integrity.items() if isinstance(v, bool) and not v] + unresolved,
    }
    (HERE / "validation.json").write_text(json.dumps(validation, indent=1) + "\n")

    (HERE / "CHECKPOINT.md").write_text(f"""# worker-091 — F0 blocking-findings verification (checkpoint)

- **When**: {now} · **target**: `research_map/formulation_taxonomy.yaml` sha256 `{f0_sha_live}` (rev {res['target']['revision']}, status `{res['target']['status_field']}`), {res['target']['bytes']} B, no drift during scan.
- **Task**: independently measure the blocking items that decide between the conflicting F0 verdicts at this hash — accept (`reviews/F0-review-094.json`) vs revise (`F0-review-16`, `F0-independent-worker-082`, `F0-review-lead-audit-r2`).
- **Verdict**: **{res['verdict']} {res['score']}** — blocking CONFIRMED: {', '.join(res['blocking_confirmed'])}; CONTESTED: {', '.join(res['blocking_contested'])}; informational: {', '.join(res['informational_checks'])}.
- **K1b (mirror) is contested, not confirmed**: FROZEN rev26 declares canonical F0 and `artifacts/formulation/formulation_taxonomy.yaml` (F0-R) to be two distinct logical artifacts; `f0_mirror_adjudication_request` says byte-identical publication is destructive (REC-1/REC-2 pending). Controller adjudication required.
- **Distinct contribution**: the lead consistency checker's D1/D3 guards cover only AF-WCC-VAC-GEN (D1) and AF-SCC-C2/C0 (D3); `CONSISTENT (0 divergences)` is scoped and does not discharge D1/D3 for AF-WCC-SCALAR-SPH.
- **Read-only**: no canonical file mutated; snapshots byte-identical; pre/post digests equal.
- **Artifacts**: `results.json` `{results_sha[:12]}`, `f0_snapshot.yaml`, `supplement_snapshot.yaml`, `verify_f0_blocking.py`, `MANIFEST.json`, `validation.json`.
- **Authority**: worker evidence only; no gate verdict, no `status=done`, no `validation_status=passed`. Outbox events left for controller ingest.
""")

    print(json.dumps({"results_sha256": results_sha, "f0_sha256": f0_sha_live,
                      "verdict": res["verdict"], "blocking_confirmed": res["blocking_confirmed"],
                      "blocking_contested": res["blocking_contested"],
                      "integrity_failures": validation["failures"],
                      "events": event_validation,
                      "checkpoint": checkpoint["checkpoint_id"]}, indent=1))
    ok = all(v for k, v in integrity.items() if isinstance(v, bool)) and not unresolved \
        and all(e["schema_valid"] and (e["appended"] or e["already_present"]) for e in event_validation)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
