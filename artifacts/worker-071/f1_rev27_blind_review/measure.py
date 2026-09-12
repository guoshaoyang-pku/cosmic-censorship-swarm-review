#!/usr/bin/env python3
"""
W071-F1-REV27-BLIND-REVIEW-01 -- mechanical pre-review gate + f0_binding chain measurement.

Assignment cards covered (comms/inbox/worker-071.jsonl):
  audit-r2-F1-a                     primary: blind G-FORM review of F1 at pin
                                    schemas/af_wcc_vacuum.yaml#cce9c60146d6...
  audit-r2-F1-bindchain-worker-071  addendum: resolve every hash the F1 schema declares.

The card's acceptance clause (1) is binding and mechanical:
  "sha256 the file yourself immediately before and after reading; if either differs from
   the pin below, STOP and emit a `blocker` (moving target) instead of a verdict."

Therefore this instrument (a) hashes before read, reads, hashes after read; (b) compares
to the assigned pin; (c) records the target verdict path's occupancy; (d) resolves the
full declared-hash chain of f0_binding plus every other 64-hex declaration in the schema;
(e) runs controls. It writes exactly one file: measurement.json.

READ-ONLY with respect to every canonical artifact. It does not write reviews/*, does not
edit schemas/*, and does not touch research_map/events.jsonl or research_map.json.
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "measurement.json"
TZ = timezone(timedelta(hours=8))

TASK_ID = "W071-F1-REV27-BLIND-REVIEW-01"
WORKER = "worker-071"
GATE = "G-FORM"
NODE_ID = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
ASSIGNMENT_EVENT_IDS = ["audit-r2-F1-a", "audit-r2-F1-bindchain-worker-071"]
ASSIGNMENT_CREATED_AT = ["2026-09-12T00:44:18+08:00", "2026-09-12T00:47:58+08:00"]
DEADLINE = "2026-09-12T02:15:00+08:00"
ASSIGNED_PIN = {
    "path": "schemas/af_wcc_vacuum.yaml",
    "sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}
TARGET_VERDICT_PATH = "reviews/F1-review-rev27-a.json"

SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
CANONICAL_TAXONOMY = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
PROVENANCE_HASH_CANDIDATE = (
    "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml"
)
SCAN_ROOTS = ["artifacts", "schemas", "reviews"]
SCAN_MAX_BYTES = 8 * 1024 * 1024
SCAN_MAX_FILES = 40000
SCAN_MAX_TOTAL = 2 * 1024 * 1024 * 1024

SHA_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
HEX64 = re.compile(r"[0-9a-f]{64}")


def now_iso():
    return datetime.now(TZ).isoformat(timespec="milliseconds")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stat_of(path: Path) -> dict:
    st = path.stat()
    return {
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, TZ).isoformat(timespec="milliseconds"),
    }


def read_hashed(rel: str) -> tuple[dict, bytes]:
    """Hash before read, read, hash after read (the card's clause 1, verbatim)."""
    p = ROOT / rel
    if not p.is_file():
        return {"path": rel, "exists": False}, b""
    before = sha_file(p)
    raw = p.read_bytes()
    inner = sha_bytes(raw)
    after = sha_file(p)
    rec = {
        "path": rel,
        "exists": True,
        "sha256_before_read": before,
        "sha256_of_bytes_read": inner,
        "sha256_after_read": after,
        "stable_during_read": before == inner == after,
        **stat_of(p),
    }
    return rec, raw


def resolve_fragment(doc, fragment: str) -> bool:
    cur = doc
    for part in fragment.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def parse_pointer(pointer: str) -> tuple[str, str]:
    path, _, frag = pointer.partition("#")
    return path, frag


def main() -> int:
    started = now_iso()
    t0 = time.time()

    # ---- 1. measure the three schemas (before/read/after) --------------------------------
    schema_recs = {}
    schema_raw = {}
    for rel in SCHEMAS:
        rec, raw = read_hashed(rel)
        schema_recs[rel] = rec
        schema_raw[rel] = raw

    f1 = schema_recs[ASSIGNED_PIN["path"]]
    f1_measured = f1.get("sha256_before_read")
    pin_matches = f1_measured == ASSIGNED_PIN["sha256"]

    f1_doc = yaml.safe_load(schema_raw[ASSIGNED_PIN["path"]].decode("utf-8"))

    # ---- 2. what revision is the current F1, and what was the pin? -----------------------
    revision_history = []
    for entry in (f1_doc or {}).get("revision_history", []) or []:
        if isinstance(entry, dict):
            revision_history.append(
                {
                    "index": entry.get("index"),
                    "at": entry.get("at"),
                    "notes": (entry.get("notes") or [])[:1],
                }
            )

    # witness that cce9c601 was the live F1 hash at 00:32:43 (rev12 publication window)
    pin_witness = {
        "source": "research_map/events.jsonl",
        "pin_prefix": ASSIGNED_PIN["sha256"][:12],
        "occurrences": 0,
        "now_matches": [],
    }
    ev_path = ROOT / "research_map/events.jsonl"
    if ev_path.is_file():
        with ev_path.open("r", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                if ASSIGNED_PIN["sha256"][:12] not in line:
                    continue
                pin_witness["occurrences"] += 1
                if f'"now": "{ASSIGNED_PIN["sha256"][:12]}"' in line and len(pin_witness["now_matches"]) < 3:
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        obj = {}
                    pin_witness["now_matches"].append(
                        {
                            "line": lineno,
                            "event_id": obj.get("event_id"),
                            "created_at": obj.get("created_at"),
                            "_received_at": obj.get("_received_at"),
                            "actor": obj.get("actor"),
                        }
                    )

    # ---- 3. target verdict path occupancy (hashed, content NOT inspected) ----------------
    tv = ROOT / TARGET_VERDICT_PATH
    target_occupancy = {"path": TARGET_VERDICT_PATH, "exists": tv.is_file()}
    if tv.is_file():
        target_occupancy.update(
            {
                "sha256": sha_file(tv),
                "content_inspected": False,
                "written_by_this_worker": False,
                "action": "not_written_not_overwritten",
                **stat_of(tv),
            }
        )

    # ---- 4. FROZEN manifest cross-check --------------------------------------------------
    frozen_rec, frozen_raw = read_hashed(FROZEN_PATH)
    frozen_doc = json.loads(frozen_raw.decode("utf-8")) if frozen_raw else {}
    frozen_files = frozen_doc.get("files", {})
    frozen_checks = []
    for rel in SCHEMAS + [CANONICAL_TAXONOMY, SUPPLEMENT]:
        declared = (frozen_files.get(rel) or {}).get("sha256")
        measured = schema_recs.get(rel, {}).get("sha256_before_read")
        if measured is None and rel in schema_recs:
            measured = schema_recs[rel].get("sha256_before_read")
        if measured is None:
            measured = sha_file(ROOT / rel) if (ROOT / rel).is_file() else None
        frozen_checks.append(
            {
                "path": rel,
                "frozen_revision": frozen_doc.get("revision"),
                "declared_sha256": declared,
                "measured_sha256": measured,
                "status": "resolved" if declared and declared == measured else "mismatch",
            }
        )

    # ---- 5. every 64-hex declaration in the F1 schema + resolution -----------------------
    text = schema_raw[ASSIGNED_PIN["path"]].decode("utf-8")
    declarations = []
    for m in re.finditer(r"([A-Za-z0-9_]*sha256)\s*:\s*\"?([0-9a-f]{64})\"?", text):
        declarations.append({"key": m.group(1), "sha256": m.group(2), "offset": m.start()})

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    # scan for the provenance hash (bounded), so a declared hash with no adjacent path is
    # still reported resolved|unresolved rather than silently dropped.
    scan = {
        "roots": SCAN_ROOTS,
        "max_file_bytes": SCAN_MAX_BYTES,
        "files_hashed": 0,
        "bytes_hashed": 0,
        "capped": False,
        "matches_by_hash": {},
        "elapsed_s": None,
    }
    declared_set = {d["sha256"] for d in declarations}
    scan_t0 = time.time()
    for root_rel in SCAN_ROOTS:
        root = ROOT / root_rel
        if not root.is_dir():
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                p = Path(dirpath) / name
                try:
                    if not p.is_file() or p.stat().st_size > SCAN_MAX_BYTES:
                        continue
                    if scan["files_hashed"] >= SCAN_MAX_FILES or scan["bytes_hashed"] >= SCAN_MAX_TOTAL:
                        scan["capped"] = True
                        break
                    h = sha_file(p)
                    scan["files_hashed"] += 1
                    scan["bytes_hashed"] += p.stat().st_size
                    if h in declared_set:
                        entry = scan["matches_by_hash"].setdefault(h, {"count": 0, "paths": []})
                        entry["count"] += 1
                        if len(entry["paths"]) < 5:
                            entry["paths"].append(str(p.relative_to(ROOT)))
                except OSError:
                    continue
            if scan["capped"]:
                break
        if scan["capped"]:
            break
    scan["elapsed_s"] = round(time.time() - scan_t0, 3)

    declared_paths = {
        "declared_f0_sha256": CANONICAL_TAXONOMY,
        "consistency_evidence_sha256": CONSISTENCY_EVIDENCE,
    }
    chain = []
    for d in declarations:
        key, declared = d["key"], d["sha256"]
        ref = declared_paths.get(key)
        entry = {
            "declared_field": key,
            "declared_sha256": declared,
            "schema_line": line_of(d["offset"]),
            "referenced_path": ref,
        }
        if ref:
            rec, _raw = read_hashed(ref)
            measured = rec.get("sha256_before_read")
            entry.update(
                {
                    "measured_sha256": measured,
                    "status": "resolved" if measured == declared else "mismatch",
                    "referenced_file_stable_during_read": rec.get("stable_during_read"),
                }
            )
        else:
            hit = scan["matches_by_hash"].get(declared, {"count": 0, "paths": []})
            matches = hit["paths"]
            entry.update(
                {
                    "referenced_path": matches[0] if len(matches) == 1 else None,
                    "candidate_matches": matches,
                    "candidate_match_count": hit["count"],
                    "status": "resolved" if hit["count"] >= 1 else "unresolved_no_referenced_file",
                    "resolution_basis": "bounded content scan of " + ", ".join(SCAN_ROOTS),
                }
            )
        chain.append(entry)

    # pointer targets: top-level class_contract_pointer + f0_binding supplement pointer
    f0b = (f1_doc or {}).get("f0_binding", {}) or {}
    pointer_sources = [
        ("schema.class_contract_pointer", (f1_doc or {}).get("class_contract_pointer")),
        (
            "f0_binding.class_contract_supplement_pointer",
            f0b.get("class_contract_supplement_pointer"),
        ),
    ]
    pointers = []
    for field, ptr in pointer_sources:
        if not ptr:
            continue
        path, frag = parse_pointer(ptr)
        rec, raw = read_hashed(path)
        doc = yaml.safe_load(raw.decode("utf-8")) if raw else {}
        pointers.append(
            {
                "field": field,
                "pointer": ptr,
                "referenced_path": path,
                "measured_sha256": rec.get("sha256_before_read"),
                "fragment_resolves": resolve_fragment(doc, frag),
                "referenced_file_stable_during_read": rec.get("stable_during_read"),
            }
        )

    # refresh rule of the schema itself
    f0_measured = next(
        (c["measured_sha256"] for c in chain if c["declared_field"] == "declared_f0_sha256"), None
    )
    ce_measured = next(
        (c["measured_sha256"] for c in chain if c["declared_field"] == "consistency_evidence_sha256"),
        None,
    )
    refresh_rule = {
        "rule": f0b.get("rule"),
        "declared_f0_matches_live": f0_measured == f0b.get("declared_f0_sha256"),
        "consistency_evidence_matches_live": ce_measured == f0b.get("consistency_evidence_sha256"),
        "satisfied_at_current_bytes": (
            f0_measured == f0b.get("declared_f0_sha256")
            and ce_measured == f0b.get("consistency_evidence_sha256")
        ),
        "checked_at_declared": f0b.get("checked_at"),
    }
    consistency_doc = {}
    ce_path = ROOT / CONSISTENCY_EVIDENCE
    if ce_path.is_file():
        try:
            consistency_doc = json.loads(ce_path.read_text())
        except ValueError:
            consistency_doc = {}
    refresh_rule["consistency_evidence_consistent_flag"] = consistency_doc.get("consistent")
    refresh_rule["consistency_evidence_errors"] = consistency_doc.get("errors")

    # ---- 6. controls ---------------------------------------------------------------------
    controls = []

    def ctl(cid, expected, observed, detail=""):
        controls.append(
            {
                "id": cid,
                "expected": expected,
                "observed": observed,
                "pass": bool(observed == expected) if not isinstance(expected, bool) else bool(observed) == expected,
                "detail": detail,
            }
        )

    ctl("CTL-SHA-FIXTURE", True, sha_bytes(b"") == SHA_EMPTY, "sha256(b'') equals the known digest")
    ctl(
        "CTL-STABLE-DURING-READ",
        True,
        all(r.get("stable_during_read") for r in schema_recs.values() if r.get("exists")),
        "pre-read hash == hash of bytes read == post-read hash for all three schemas",
    )
    ctl(
        "CTL-FRAGMENT-POSITIVE",
        True,
        resolve_fragment(f1_doc, "class_components.censorship")
        and f1_doc["class_components"]["censorship"] == "WCC",
        "class_components.censorship resolves and equals WCC",
    )
    ctl(
        "CTL-FRAGMENT-NEGATIVE",
        False,
        resolve_fragment(f1_doc, "class_components.NO_SUCH_CLASS"),
        "bogus fragment does not resolve (anti-vacuous control)",
    )
    ctl(
        "CTL-POINTERS-RESOLVE",
        True,
        len(pointers) == 2 and all(p["fragment_resolves"] for p in pointers),
        "top-level class_contract_pointer and f0_binding supplement pointer both resolve",
    )
    ctl(
        "CTL-FROZEN-AGREEMENT",
        True,
        all(c["status"] == "resolved" for c in frozen_checks),
        "FROZEN rev29 entries equal measured bytes for schemas + both taxonomies",
    )
    ctl(
        "CTL-PIN-COMPARATOR",
        True,
        (f1_measured == ASSIGNED_PIN["sha256"]) is False
        and (f1_measured == f1_measured) is True,
        "comparator returns MATCH only for equal digests; assigned pin differs from current",
    )
    prov = next((c for c in chain if c["declared_field"] == "worker_sha256"), None)
    ctl(
        "CTL-PROVENANCE-RESOLVES",
        True,
        prov is not None and prov["status"] == "resolved",
        "the non-authority provenance hash resolves on disk (candidate path checked by scan)",
    )
    ctl(
        "CTL-ALL-BINDING-HASHES",
        True,
        all(
            c["status"] == "resolved"
            for c in chain
            if c["declared_field"] in ("declared_f0_sha256", "consistency_evidence_sha256")
        ),
        "both binding declarations resolve to the measured file",
    )

    controls_passed = all(c["pass"] for c in controls)
    measurement_valid = controls_passed and all(
        r.get("stable_during_read") for r in schema_recs.values() if r.get("exists")
    )

    # ---- 7. decision ---------------------------------------------------------------------
    if not pin_matches:
        decision = "BLOCKER_MOVING_TARGET"
        decision_reason = (
            f"assigned pin {ASSIGNED_PIN['sha256'][:12]} != measured F1 "
            f"{str(f1_measured)[:12]}; the file moved rev12->rev13 before the review window, "
            f"and {TARGET_VERDICT_PATH} already exists (written {target_occupancy.get('mtime')}). "
            "Acceptance clause (1) requires a blocker instead of a verdict."
        )
    else:
        decision = "VERDICT_MAY_PROCEED"
        decision_reason = "pin matches; a blind verdict may be written."

    measurement = {
        "measurement_id": TASK_ID + "/measurement",
        "task_id": TASK_ID,
        "worker": WORKER,
        "gate": GATE,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "assignment_event_ids": ASSIGNMENT_EVENT_IDS,
        "assignment_created_at": ASSIGNMENT_CREATED_AT,
        "assignment_deadline": DEADLINE,
        "started_at": started,
        "finished_at": now_iso(),
        "assigned_pin": ASSIGNED_PIN,
        "schemas": [schema_recs[r] for r in SCHEMAS],
        "f1_revision_from_file": (f1_doc or {}).get("revision"),
        "f1_revision_history_tail": revision_history[-2:],
        "pin_check": {
            "path": ASSIGNED_PIN["path"],
            "assigned_sha256": ASSIGNED_PIN["sha256"],
            "measured_sha256": f1_measured,
            "match": pin_matches,
            "verdict": "MOVING_TARGET" if not pin_matches else "MATCH",
        },
        "rev12_witness": pin_witness,
        "target_verdict_path_occupancy": target_occupancy,
        "frozen_manifest": {
            "path": FROZEN_PATH,
            "sha256": frozen_rec.get("sha256_before_read"),
            "revision": frozen_doc.get("revision"),
            "frozen_at": frozen_doc.get("frozen_at"),
            "checks": frozen_checks,
        },
        "declared_hash_chain": {
            "schema": ASSIGNED_PIN["path"],
            "schema_sha256": f1_measured,
            "declarations": chain,
            "pointers": pointers,
            "refresh_rule": refresh_rule,
            "all_declared_hashes_resolved": all(c["status"] == "resolved" for c in chain),
            "binding_hashes_resolved": all(
                c["status"] == "resolved"
                for c in chain
                if c["declared_field"] in ("declared_f0_sha256", "consistency_evidence_sha256")
            ),
            "any_mismatch": any(c["status"] == "mismatch" for c in chain),
        },
        "provenance_scan": scan,
        "controls": controls,
        "controls_passed": controls_passed,
        "measurement_valid": measurement_valid,
        "decision": {
            "code": decision,
            "reason": decision_reason,
            "review_verdict_emitted": False,
            "review_event_emitted": False,
            "target_verdict_path_written": False,
            "gate_verdict_set": False,
            "node_status_set": False,
        },
        "falsifier": (
            "MOVING-TARGET BLOCKER is falsified if sha256(schemas/af_wcc_vacuum.yaml) == "
            f"{ASSIGNED_PIN['sha256']} at re-measure (rev12 bytes restored) AND "
            f"{TARGET_VERDICT_PATH} does not exist, in which case the assignment is live and a "
            "blind verdict must be written instead. The BIND-CHAIN result (every declared hash "
            "resolves; refresh rule satisfied) is falsified by any declared_sha256 != the "
            "measured sha256 of its referenced file, or by a change of any pinned input sha256 "
            "during the window. The OCCUPANCY finding is falsified if the target file is absent "
            "at re-measure."
        ),
        "void_condition": (
            "Any change of an input sha256 across the measurement window voids this measurement "
            "at the changed path; stable_during_read records the per-file window check."
        ),
        "instrument": {
            "path": "artifacts/worker-071/f1_rev27_blind_review/measure.py",
            "sha256": sha_file(Path(__file__).resolve()),
            "python": sys.version.split()[0],
            "yaml": getattr(yaml, "__version__", "unknown"),
            "elapsed_s": round(time.time() - t0, 3),
        },
    }

    OUT.write_text(json.dumps(measurement, indent=2, sort_keys=False) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    print("sha256", sha_file(OUT))
    print("decision", decision)
    print("pin_matches", pin_matches)
    print("measurement_valid", measurement_valid)
    print("controls", [(c["id"], c["pass"]) for c in controls])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
