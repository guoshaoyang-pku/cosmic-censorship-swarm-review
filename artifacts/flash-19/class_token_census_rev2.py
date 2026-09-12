#!/usr/bin/env python3
"""Revision-2 machine census of class tokens in the L0 literature ledger.

Assignment : astra-indep-1-CF5-ledger-verify (node L0, gate G-LIT)
             class scope AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH
Actor      : deepseek-flash-19 (bounded execution worker 19, independent lifecycle)
Deliverable: artifacts/flash-19/class_token_census_rev2.json

Why a revision exists
---------------------
rev1 (artifacts/flash-19/class_token_census.json, sha256 f7b1b0df14a5...) measured
ledger/theorems.jsonl at ce42d205e761. That file was rewritten at 2026-09-12T00:35:19
to a1674f094979 (controller finding CF-19, freeze breach on L0), so the rev1 counts no
longer bind the live bytes. This driver re-runs the byte-identical rev1 census method
(pinned by sha256, verified before import) over the current inputs and reports the
token-level delta. It overwrites nothing: rev1 and its event evidence stay on disk.

Honesty / independence
----------------------
The method is the worker's own rev1 method (the worker is not a ledger author), reused
byte-identically, not copied from another reviewer. The only new logic is: input
stability probing, supersession provenance, and the delta computation.

Determinism
-----------
Same inputs -> same content digest (except generated_at / content_digest_sha256, which
are excluded from the digest). The driver re-hashes both inputs after the run and exits
non-zero if they moved, so a stale artifact is never silently emitted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "flash-19" / "class_token_census_rev2.json"
REV1_GENERATOR = ROOT / "artifacts" / "flash-19" / "class_token_census.py"
REV1_ARTIFACT = ROOT / "artifacts" / "flash-19" / "class_token_census.json"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
CITATIONS = ROOT / "ledger" / "citation_audit.csv"
MAP = ROOT / "research_map" / "research_map.json"
CST = timezone(timedelta(hours=8))

# Pins: verified before use; a mismatch aborts rather than producing a mixed-method census.
PIN_REV1_GENERATOR = "d7808a705168d655b3cfb0b6367292ded0833d7bce8735e40f3b4866f79b9b44"
PIN_REV1_ARTIFACT = "f7b1b0df14a5d8fecc19e25e706284db2cc607f23c74673f4f6e1ce5321bab1b"
PIN_REV1_THEOREMS = "ce42d205e761"  # stored on the rev1 artifact; full hash compared there
PIN_REV1_CITATIONS = "315c19145065"

EXCLUDE_FROM_DIGEST = ("generated_at", "content_digest_sha256")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_rev1():
    got = sha256_path(REV1_GENERATOR)
    if got != PIN_REV1_GENERATOR:
        raise SystemExit(f"FATAL: rev1 generator hash {got} != pinned {PIN_REV1_GENERATOR}")
    spec = importlib.util.spec_from_file_location("class_token_census_rev1", REV1_GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def delta_vs_rev1(rev1: dict, rev2: dict) -> dict:
    old = {e["token"]: e for e in rev1.get("census", [])}
    new = {e["token"]: e for e in rev2.get("census", [])}
    per_token = []
    for tok in sorted(set(old) | set(new)):
        o, n = old.get(tok), new.get(tok)
        o_occ = o["occurrences"] if o else 0
        n_occ = n["occurrences"] if n else 0
        o_cls = o["classification"] if o else None
        n_cls = n["classification"] if n else None
        if o_occ != n_occ or o_cls != n_cls:
            per_token.append({
                "token": tok,
                "rev1_classification": o_cls,
                "rev2_classification": n_cls,
                "rev1_occurrences": o_occ,
                "rev2_occurrences": n_occ,
                "occurrence_delta": n_occ - o_occ,
                "rev1_by_file": o["by_file"] if o else {},
                "rev2_by_file": n["by_file"] if n else {},
            })
    old_v = {v["token"] for v in rev1.get("violations", [])}
    new_v = {v["token"] for v in rev2.get("violations", [])}
    return {
        "rev1_input_pins": {i["path"]: i["sha256"] for i in rev1.get("inputs", [])},
        "tokens_changed": per_token,
        "violations_resolved": sorted(old_v - new_v),
        "violations_added": sorted(new_v - old_v),
        "violations_remaining": sorted(new_v & old_v),
        "rev1_falsifier_status": rev1.get("assertions", {}).get("falsifier_status"),
        "rev2_falsifier_status": rev2.get("assertions", {}).get("falsifier_status"),
        "interpretation": (
            "A violation token present in rev1 and absent from rev2 is resolved by the "
            "post-freeze rewrite only if rev1_occurrences > 0 and rev2_occurrences == 0 "
            "across both files; a token with rev2_occurrences == 0 in one file but not the "
            "other is a partial repair."
        ),
    }


def main() -> int:
    if OUT.exists():
        # Never silently clobber a previous revision-2 artifact.
        raise SystemExit(f"FATAL: {OUT.relative_to(ROOT)} already exists; refusing to overwrite")
    if sha256_path(REV1_ARTIFACT) != PIN_REV1_ARTIFACT:
        raise SystemExit("FATAL: rev1 artifact hash mismatch")
    rev1 = json.loads(REV1_ARTIFACT.read_text())
    rev1_pins = {i["path"]: i["sha256"] for i in rev1.get("inputs", [])}
    if not rev1_pins.get("ledger/theorems.jsonl", "").startswith(PIN_REV1_THEOREMS):
        raise SystemExit("FATAL: rev1 artifact does not carry the expected theorems pin")
    if not rev1_pins.get("ledger/citation_audit.csv", "").startswith(PIN_REV1_CITATIONS):
        raise SystemExit("FATAL: rev1 artifact does not carry the expected citation pin")

    mod = load_rev1()
    mod.OUT = OUT  # redirect the pinned method to the revision-2 path

    before = {"ledger/theorems.jsonl": sha256_path(THEOREMS),
              "ledger/citation_audit.csv": sha256_path(CITATIONS),
              "research_map/research_map.json": sha256_path(MAP)}
    mod.main()  # writes OUT using the byte-identical rev1 census logic
    after = {"ledger/theorems.jsonl": sha256_path(THEOREMS),
             "ledger/citation_audit.csv": sha256_path(CITATIONS),
             "research_map/research_map.json": sha256_path(MAP)}
    stable = before == after

    payload = json.loads(OUT.read_text())
    payload["artifact_version"] = "2.0"
    payload["revision"] = 2
    payload["task"]["actor"] = "deepseek-flash-19"
    payload["task"]["worker_slot"] = "19"
    payload["task"]["controller_finding"] = "CF-5 (ledger class-token vocabulary); CF-19 (post-freeze rewrite)"
    payload["supersedes"] = {
        "artifact": str(REV1_ARTIFACT.relative_to(ROOT)),
        "artifact_sha256": PIN_REV1_ARTIFACT,
        "artifact_input_pins": rev1_pins,
        "reason": "ledger/theorems.jsonl moved after rev1; rev1 remains valid evidence for its own pinned bytes",
        "rev1_events": ["flash19-L0-01-artifact-class-token-census-20260912T001301",
                        "flash19-L0-01-cp1-20260912T001301"],
    }
    payload["input_stability"] = {
        "before": before,
        "after": after,
        "stable": stable,
        "note": "map hash included only as run context; it is not a census input",
    }
    payload["delta_vs_rev1"] = delta_vs_rev1(rev1, payload)
    payload["generator"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256_path(Path(__file__).resolve()),
        "reproduce_command": "python3 artifacts/flash-19/class_token_census_rev2.py",
        "reused_method": {"path": str(REV1_GENERATOR.relative_to(ROOT)), "sha256": PIN_REV1_GENERATOR},
    }
    payload["falsifier"] = (
        "A rerun on the same input sha256s (theorems "
        f"{before['ledger/theorems.jsonl'][:12]}, citations {before['ledger/citation_audit.csv'][:12]}) "
        "that finds an AF-prefixed token not classified here, classifies a token differently, "
        "or reports a different occurrence count falsifies this revision. Input drift during the "
        "run makes it void (input_stability.stable=false)."
    )
    payload["reopen_rule"] = (
        "If either ledger input sha256 changes, this census is stale: regenerate before citing "
        "any count. The rev1 finding is superseded only for the bytes measured here."
    )

    content = {k: v for k, v in payload.items() if k not in EXCLUDE_FROM_DIGEST}
    payload["content_digest_sha256"] = sha256_bytes(
        json.dumps(content, ensure_ascii=False, sort_keys=True).encode())
    payload["generated_at"] = datetime.now(CST).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    summary = {
        "artifact": str(OUT.relative_to(ROOT)),
        "artifact_sha256": sha256_path(OUT),
        "content_digest_sha256": payload["content_digest_sha256"],
        "input_sha256": {k: v[:16] for k, v in before.items()},
        "input_stable": stable,
        "falsifier_status": payload["assertions"]["falsifier_status"],
        "non_frozen_af_tokens": payload["assertions"]["non_frozen_af_tokens"],
        "non_frozen_af_occurrences": payload["assertions"]["non_frozen_af_occurrences"],
        "frozen_ids_present": payload["assertions"]["frozen_ids_present"],
        "violations_resolved": payload["delta_vs_rev1"]["violations_resolved"],
        "violations_added": payload["delta_vs_rev1"]["violations_added"],
        "violations_remaining": payload["delta_vs_rev1"]["violations_remaining"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if stable else 3


if __name__ == "__main__":
    sys.exit(main())
