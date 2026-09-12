#!/usr/bin/env python3
"""W049-CLASSSEP-DETECTOR-RECORD-05 -- recorded-copy reconstructability census.

Read-only, fail-closed, deterministic. Enumerates every `class_separation*.py`
file under the repository root by the pre-registered rule, hashes each, and
reports for each of the three candidate detector hashes whether a byte-exact
recorded copy exists on disk. Supplies the first acceptance clause and the
stop rule of assignment astra-classsep-stabilize-0118; decides nothing.

Exit codes (pre-registered):
  0 census complete, pins + controls pass
  2 PIN_MISMATCH (fixed input moved / control failed)
  3 NONDETERMINISTIC (two in-process census passes differ)
  4 IMMUTABILITY_VIOLATION (pinned input changed during the run)
  5 HARNESS_ERROR

No repo module is imported. Nothing outside this packet directory is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # <root>/artifacts/worker-049/classsep_detector_record -> <root>

CANDIDATES = {
    "active_frozen_pin": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "live_adjudicated": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "voided_write": "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
}
CANDIDATE_LABEL_BY_HASH = {v: k for k, v in CANDIDATES.items()}

LIVE_PATH = ROOT / "research_map/class_separation.py"
LIVE_EXPECTED = CANDIDATES["live_adjudicated"]
EVIDENCE_PATH = ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py"
EVIDENCE_EXPECTED = CANDIDATES["voided_write"]
MAP_PATH = ROOT / "research_map/research_map.json"
MAP_PIN_EXPECTED = CANDIDATES["active_frozen_pin"]
REGRESSION_PATH = ROOT / "runtime/bin/classsep_regression.py"
REGRESSION_EXPECTED = "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091"

OTHER_KNOWN_PREFIXES = {"e2d24b927ee8": "staged_candidate", "dc8aa0de3869": "staged_prosefix"}

FREEZE_AT = datetime.fromisoformat("2026-09-11T23:30:20+08:00")
DRIFT_AT = datetime.fromisoformat("2026-09-12T01:06:12+08:00")
ROLLBACK_AT = datetime.fromisoformat("2026-09-12T01:08:14+08:00")


def now() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def temporal_bin(dt: datetime) -> str:
    if dt < FREEZE_AT:
        return "before_freeze"
    if dt < DRIFT_AT:
        return "freeze_to_drift"
    if dt <= ROLLBACK_AT:
        return "drift_window"
    return "after_rollback"


def provenance_class(rel: str) -> str:
    if rel == "research_map/class_separation.py":
        return "canonical_live"
    if rel.startswith("runtime/state/controller_verification/"):
        return "runtime_evidence"
    if rel.startswith("artifacts/worker-049/"):
        return "worker049_own"
    if rel.startswith("artifacts/"):
        return "third_party_pinned"
    if rel.startswith("tmp/"):
        return "sandbox_mirror"
    return "other"


def exactness(digest: str) -> str:
    if digest in CANDIDATE_LABEL_BY_HASH:
        return "EXACT:" + CANDIDATE_LABEL_BY_HASH[digest]
    for prefix, label in OTHER_KNOWN_PREFIXES.items():
        if digest.startswith(prefix):
            return "OTHER_KNOWN:" + label
    return "OTHER"


def census() -> list[dict]:
    """Pre-registered enumeration: class_separation*.py, no __pycache__, no symlinks."""
    rows = []
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", "__pycache__"})
        for name in sorted(filenames):
            if not name.startswith("class_separation") or not name.endswith(".py"):
                continue
            full = Path(dirpath) / name
            if full.is_symlink():
                continue
            rel = str(full.relative_to(ROOT))
            st = full.stat()
            digest = sha256_file(full)
            text = full.read_text(encoding="utf-8", errors="replace")
            rows.append({
                "path": rel,
                "sha256": digest,
                "size_bytes": st.st_size,
                "lines": text.count("\n") + (0 if text.endswith("\n") else 1),
                "mtime": datetime.fromtimestamp(st.st_mtime, TZ).replace(microsecond=0).isoformat(),
                "exactness": exactness(digest),
                "provenance_class": provenance_class(rel),
                "temporal_bin": temporal_bin(datetime.fromtimestamp(st.st_mtime, TZ)),
            })
    rows.sort(key=lambda r: r["path"])
    return rows


def map_active_pin() -> str | None:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    for entry in data.get("frozen_artifacts", []):
        if entry.get("path") == "research_map/class_separation.py" and entry.get("active") is True:
            return entry.get("sha256")
    return None


def main() -> int:
    problems: list[str] = []
    controls: list[dict] = []
    started = now()

    def control(cid: str, ok: bool, detail: str) -> None:
        controls.append({"id": cid, "pass": bool(ok), "detail": detail})
        if not ok:
            problems.append(f"{cid}: {detail}")

    live_start = sha256_file(LIVE_PATH) if LIVE_PATH.exists() else None
    evidence_start = sha256_file(EVIDENCE_PATH) if EVIDENCE_PATH.exists() else None
    pin_measured = map_active_pin()
    regression_measured = sha256_file(REGRESSION_PATH) if REGRESSION_PATH.exists() else None

    # --- pin gates (exit 2) -------------------------------------------------
    if live_start != LIVE_EXPECTED:
        problems.append(f"PIN live_detector measured {live_start} expected {LIVE_EXPECTED}")
    if evidence_start != EVIDENCE_EXPECTED:
        problems.append(f"PIN void_evidence measured {evidence_start} expected {EVIDENCE_EXPECTED}")
    if pin_measured != MAP_PIN_EXPECTED:
        problems.append(f"PIN map_active_pin measured {pin_measured} expected {MAP_PIN_EXPECTED}")

    # --- controls -----------------------------------------------------------
    control("C3-live-pin", live_start == LIVE_EXPECTED, f"research_map/class_separation.py -> {live_start}")
    control("C4-map-pin", pin_measured == MAP_PIN_EXPECTED, f"frozen_artifacts active pin -> {pin_measured}")
    control("C2-truncation-negative",
            hashlib.sha256(LIVE_PATH.read_bytes()[:-1]).hexdigest() != LIVE_EXPECTED,
            "one-byte-truncated live bytes do not digest to the live constant")

    pass1 = census()
    pass2 = census()

    control("C5-no-pyc", all(not r["path"].endswith(".pyc") and "__pycache__" not in r["path"] for r in pass1),
            f"{len(pass1)} rows, none .pyc / __pycache__")
    deterministic = json.dumps(pass1, sort_keys=True) == json.dumps(pass2, sort_keys=True)
    control("C-determinism", deterministic, "two in-process census passes byte-identical")
    control("C1-positive", len(pass1) > 0, f"enumeration found {len(pass1)} class_separation*.py files")

    # --- immutability re-measure (exit 4) -----------------------------------
    live_end = sha256_file(LIVE_PATH)
    evidence_end = sha256_file(EVIDENCE_PATH)
    immutable = (live_end == live_start) and (evidence_end == evidence_start)
    control("C6-immutability", immutable, f"live {live_end[:12]} evidence {evidence_end[:12]} unchanged during run")

    # --- verdicts -----------------------------------------------------------
    verdicts = {}
    for label, digest in CANDIDATES.items():
        copies = [r for r in pass1 if r["sha256"] == digest]
        primary = [r for r in copies if r["temporal_bin"] in {"before_freeze", "freeze_to_drift"}]
        verdicts[label] = {
            "expected_sha256": digest,
            "copies": len(copies),
            "paths": [r["path"] for r in copies],
            "primary_pre_drift_copies": len(primary),
            "primary_paths": [r["path"] for r in primary],
            "verdict": "BYTE_EXACT_COPIES_PRESENT" if copies else "NO_BYTE_EXACT_COPY",
            "primary_copy": "PRIMARY_PRE_DRIFT_COPY_PRESENT" if primary else "NO_PRIMARY_PRE_DRIFT_COPY",
        }
    missing = [k for k, v in verdicts.items() if v["copies"] == 0]
    if not missing:
        stop_rule = "NOT_TRIGGERED: all three candidates have >=1 byte-exact recorded copy"
    elif len(missing) == len(CANDIDATES):
        stop_rule = "GLOBALLY_TRIGGERED: no candidate has a byte-exact recorded copy"
    else:
        stop_rule = "TRIGGERED_FOR:" + ",".join(sorted(missing))

    result = {
        "schema": "worker-049/detector-record-census/v1",
        "task_id": "W049-CLASSSEP-DETECTOR-RECORD-05",
        "actor": "worker-049",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "authority_note": "worker evidence only; no adoption, no detector-of-record, no gate verdict",
        "runner": {
            "path": "artifacts/worker-049/classsep_detector_record/run_detector_record_049.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "pre_registration": "artifacts/worker-049/classsep_detector_record/pre_registration.json",
        "started_at": started,
        "finished_at": now(),
        "repo_root": str(ROOT),
        "pins": {
            "live_detector": {"path": "research_map/class_separation.py", "measured": live_start, "expected": LIVE_EXPECTED, "match": live_start == LIVE_EXPECTED},
            "void_evidence": {"path": "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py", "measured": evidence_start, "expected": EVIDENCE_EXPECTED, "match": evidence_start == EVIDENCE_EXPECTED},
            "map_active_pin": {"path": "research_map/research_map.json#frozen_artifacts", "measured": pin_measured, "expected": MAP_PIN_EXPECTED, "match": pin_measured == MAP_PIN_EXPECTED},
            "regression_runner": {"path": "runtime/bin/classsep_regression.py", "measured": regression_measured, "expected": REGRESSION_EXPECTED, "match": regression_measured == REGRESSION_EXPECTED},
        },
        "enumeration": {
            "rule": "class_separation*.py under repo root, .git/__pycache__ pruned, symlinks skipped",
            "files_enumerated": len(pass1),
            "deterministic_double_pass": deterministic,
        },
        "verdicts": verdicts,
        "stop_rule_0118": stop_rule,
        "census": pass1,
        "controls": controls,
        "problems": problems,
        "exit_code": 0,
    }

    (HERE / "results.json").write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    if problems:
        code = 4 if any(p.startswith("C6") for p in problems) else 2
    elif not deterministic:
        code = 3
    else:
        code = 0
    result["exit_code"] = code
    (HERE / "results.json").write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "exit_code": code,
        "files_enumerated": len(pass1),
        "verdicts": {k: (v["verdict"], v["copies"], v["primary_copy"]) for k, v in verdicts.items()},
        "stop_rule_0118": stop_rule,
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
        "problems": problems,
    }, indent=1))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # harness error, never a silent pass
        print(json.dumps({"exit_code": 5, "error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(5)
