#!/usr/bin/env python3
"""W092-A0-SCOPE-INDEP-01 - independent, blind, hash-bound verification of
evaluation/A0_detector_scope_adjudication.json#a26be4b85706.

Task (bounded worker task; no gate verdict, no node status, no validation_status):
  Independently re-derive the A0 detector-scope artifact's central claims from raw
  bytes and the rubric text, under the card's own falsifier:
    "A scope change that hides a live-artifact hit; an exclusion list that includes
     any canonical ledger or build input."

Independence contract:
  * imports NO author code (neither artifacts/audit/a0_detector_scope.py nor
    artifacts/audit/audit_lib.py / audit_run.py);
  * re-implements the HF-14 and HF-03 predicates and the scope taxonomy from the
    rubric text and the artifact's own taxonomy strings;
  * pins every input by sha256 at entry, re-measures at exit, fails closed on drift;
  * read-only: writes only under artifacts/worker-092/a0_scope_verify/.

Exit codes: 0 = all hard checks pass; 1 = hard check failure; 2 = moving target
(input hash drift); 3 = missing pinned input.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))

ARTIFACT = "evaluation/A0_detector_scope_adjudication.json"
RUBRIC = "evaluation_rubric.yaml"
DETECTOR = "artifacts/audit/a0_detector_scope.py"
ARTIFACT_PIN = "a26be4b857068d2608387848035b6ddb5fda746447bf5750d6a7527ce5e2d24c"
RUBRIC_PIN = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"

SCAN_ROOTS = ("artifacts", "comms/outbox", "ledger")
CANONICAL = ("ledger/theorems.jsonl", "ledger/citation_audit.csv")
LIVE_BUILD_INPUT_PREFIXES = (
    "artifacts/literature/sources/",
    "artifacts/literature/theorems/",
    "artifacts/literature/tools/",
)
LIVE_EMITTED = (
    "artifacts/literature/registry.jsonl",
    "artifacts/literature/unresolved.jsonl",
    "artifacts/literature/MANIFEST.json",
    "artifacts/literature/falsifiers.md",
    "artifacts/literature/tag_index.md",
)
HISTORICAL_SEGMENTS = {"archive", "incoming"}
SNAPSHOT_SEGMENTS = {"snapshot", "snapshots", "probe", "proposed", "staging", "scratch", "prev"}
HISTORICAL_BASENAME_TOKENS = (".pre-", ".prev-", "_snapshot.", ".snapshot-", ".bak")
SCOPE_KEYS = ("matter_model", "cosmological_constant", "dimension", "symmetry")

hard_failures: list[str] = []
soft_findings: list[str] = []
checks: list[dict] = []


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def check(cid: str, ok: bool, hard: bool, detail) -> None:
    checks.append({"id": cid, "ok": bool(ok), "hard": bool(hard), "detail": detail})
    if not ok:
        (hard_failures if hard else soft_findings).append(f"{cid}: {detail}")


def load_rows(p: Path) -> list[dict]:
    """Own JSON/JSONL reader (dict rows only)."""
    rows: list[dict] = []
    text = p.read_text(errors="replace")
    stripped = text.strip()
    if not stripped:
        return rows
    try:
        doc = json.loads(stripped)
        if isinstance(doc, dict):
            return [doc]
        if isinstance(doc, list):
            return [d for d in doc if isinstance(d, dict)]
    except ValueError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


# --------------------------------------------------------------------------------------
# Scope taxonomy - independent implementations of BOTH readings
# --------------------------------------------------------------------------------------
def classify_live_first(rel: str) -> str:
    """Reading A (author's evaluation order, corroborated by must_keep): live classes
    are decided before historical/snapshot exclusion."""
    if rel in CANONICAL:
        return "canonical"
    if any(rel.startswith(p) for p in LIVE_BUILD_INPUT_PREFIXES):
        return "live_build_input"
    if rel in LIVE_EMITTED:
        return "live_emitted"
    parts = rel.split("/")
    base = parts[-1]
    if any(seg in HISTORICAL_SEGMENTS for seg in parts[:-1]) or \
       any(tok in base for tok in HISTORICAL_BASENAME_TOKENS):
        return "historical"
    if any(seg in SNAPSHOT_SEGMENTS for seg in parts[:-1]) or "snapshot" in base:
        return "snapshot_copy"
    if "ledger_contribution" in parts or rel.startswith("artifacts/worker-07/ledger"):
        return "staging_unresolved"
    return "live_other"


def exclusion_matches(rel: str) -> bool:
    """Reading B: the artifact's `exact_predicate` string applied literally, with no
    stated precedence over the must_keep classes."""
    parts = rel.split("/")
    base = parts[-1]
    if any(seg in HISTORICAL_SEGMENTS for seg in parts[:-1]):
        return True
    if any(seg in SNAPSHOT_SEGMENTS for seg in parts[:-1]):
        return True
    if any(tok in base for tok in HISTORICAL_BASENAME_TOKENS):
        return True
    return "snapshot" in base


def excluded_live_first(rel: str) -> bool:
    return classify_live_first(rel) in ("historical", "snapshot_copy")


LIVE_CLASSES = ("canonical", "live_build_input", "live_emitted")


# --------------------------------------------------------------------------------------
# Independent detector re-implementations (rubric text + shared audit semantics)
# --------------------------------------------------------------------------------------
def is_ledger_record(r: dict) -> bool:
    """scan_corpus record filter, re-derived."""
    return "theorem_id" in r or ("class_ids" in r and "statement_exact" in r)


def is_citation(r: dict) -> bool:
    return bool(r.get("resolution_status") or r.get("status")) and \
        bool(r.get("cite_key") or r.get("source_id"))


def hf14_hit(r: dict, artifact_hash_exempt: bool = False) -> bool:
    """HF-14 self_certified_acceptance.
    V2 (artifact_hash_exempt=False) mirrors the shared audit semantics: accepted-ish
    AND no reviewer-verdict field. V1 additionally exempts records that carry an
    artifact hash, per the rubric's literal 'and no artifact hash' clause."""
    accepted = (str(r.get("status", "")).lower() in ("accepted", "passed")
                or r.get("supports_claim") is True
                or str(r.get("validation_status", "")).lower() == "passed")
    has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))
    if accepted and not has_review:
        if artifact_hash_exempt:
            has_hash = bool(r.get("artifact_sha256") or r.get("artifact_hash")
                            or r.get("artifact_refs"))
            return not has_hash
        return True
    return False


def hf03_hit(r: dict) -> bool:
    """HF-03 unsupported_citation (scope-metadata form): citation row lacks any of
    matter_model / cosmological_constant / dimension / symmetry in source_meta, or
    formulation in either source_meta or the row."""
    meta = r.get("source_meta") or {}
    for k in SCOPE_KEYS:
        if k not in meta:
            return True
    if not meta.get("formulation") and not r.get("formulation"):
        return True
    return False


def main() -> int:
    started = datetime.now(CST).isoformat(timespec="seconds")
    art_path, rub_path = ROOT / ARTIFACT, ROOT / RUBRIC
    for p in (art_path, rub_path):
        if not p.is_file():
            print(f"MISSING INPUT {p}", file=sys.stderr)
            sys.exit(3)

    pin_before = {ARTIFACT: sha256_file(art_path), RUBRIC: sha256_file(rub_path)}
    check("C1_artifact_pin", pin_before[ARTIFACT] == ARTIFACT_PIN, True,
          {"declared": ARTIFACT_PIN, "measured": pin_before[ARTIFACT]})
    check("C1_rubric_pin", pin_before[RUBRIC] == RUBRIC_PIN, True,
          {"declared": RUBRIC_PIN, "measured": pin_before[RUBRIC]})

    art = json.loads(art_path.read_text())
    pins = art["measured"]["file_pins"]
    hf14_before = art["measured"]["_hf14_before"]
    hf03_before = art["measured"]["_hf03_before"]
    hf14, hf03 = art["measured"]["hf14"], art["measured"]["hf03"]

    # ---- C2: every declared file pin resolves and re-classifies identically -----------
    bad = []
    for rel, d in sorted(pins.items()):
        p = ROOT / rel
        if not p.is_file():
            bad.append({"path": rel, "problem": "missing"})
            continue
        h = sha256_file(p)
        cls = classify_live_first(rel)
        if h != d.get("sha256") or cls != d.get("class") or d.get("exists") is not True:
            bad.append({"path": rel, "declared_sha": d.get("sha256"), "measured_sha": h,
                        "declared_class": d.get("class"), "measured_class": cls})
    check("C2_file_pins_resolve", not bad, True,
          {"n_pins": len(pins), "mismatches": bad})

    # ---- C3: reproduce HF-14 per-file counts ------------------------------------------
    hf14_v2, hf14_v1, hf14_bad = {}, {}, []
    for rel, declared in sorted(hf14_before.items()):
        rows = load_rows(ROOT / rel)
        recs = [r for r in rows if is_ledger_record(r)]
        n2 = sum(1 for r in recs if hf14_hit(r, False))
        n1 = sum(1 for r in recs if hf14_hit(r, True))
        hf14_v2[rel], hf14_v1[rel] = n2, n1
        if n2 != declared:
            hf14_bad.append({"path": rel, "declared": declared, "independent_v2": n2,
                             "independent_v1": n1, "rows": len(rows), "records": len(recs)})
    check("C3_hf14_counts_reproduced", not hf14_bad, True,
          {"files": len(hf14_before), "total_declared": sum(hf14_before.values()),
           "total_independent_v2": sum(hf14_v2.values()), "mismatches": hf14_bad,
           "v1_equals_v2": hf14_v1 == hf14_v2})

    # ---- C4: reproduce HF-03 per-file counts ------------------------------------------
    hf03_ind, hf03_bad = {}, []
    for rel, declared in sorted(hf03_before.items()):
        rows = load_rows(ROOT / rel)
        n = sum(1 for r in rows if is_citation(r) and hf03_hit(r))
        hf03_ind[rel] = n
        if n != declared:
            hf03_bad.append({"path": rel, "declared": declared, "independent": n,
                             "rows": len(rows)})
    check("C4_hf03_counts_reproduced", not hf03_bad, True,
          {"files": len(hf03_before), "total_declared": sum(hf03_before.values()),
           "total_independent": sum(hf03_ind.values()), "mismatches": hf03_bad})

    # ---- C5: re-derive I1-I5 from the artifact's own maps -----------------------------
    i1_bad = [s for s in pins if classify_live_first(s) in LIVE_CLASSES and excluded_live_first(s)]
    i2_bad = [s for s in pins if excluded_live_first(s)
              and classify_live_first(s) not in ("historical", "snapshot_copy")]
    recon = {}
    for hf_name, before, split in (("hf14", hf14_before, hf14), ("hf03", hf03_before, hf03)):
        kept = {k: v["records"] for k, v in split["kept"].items()}
        exc = {k: v["records"] for k, v in split["excluded"].items()}
        stg = {k: v["records"] for k, v in split["staging_unresolved"].items()}
        per_file = all(
            sum(1 for d in (kept, exc, stg) if k in d) == 1
            and kept.get(k, 0) + exc.get(k, 0) + stg.get(k, 0) == before.get(k, 0)
            for k in set(kept) | set(exc) | set(stg))
        recon[hf_name] = {
            "kept": sum(kept.values()), "excluded": sum(exc.values()),
            "staging_unresolved": sum(stg.values()), "before": sum(before.values()),
            "per_file_reconciles": per_file,
            "declared_after_total": split["after_total_records"],
            "derived_after_total": sum(kept.values()),
        }
    i3_ok = all(v["per_file_reconciles"]
                and v["before"] == v["kept"] + v["excluded"] + v["staging_unresolved"]
                and v["derived_after_total"] == v["declared_after_total"]
                for v in recon.values())
    i4_ok = excluded_live_first("artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl") \
        and not excluded_live_first("artifacts/literature/sources/batch-01.jsonl")
    stg_paths = set(hf14["staging_unresolved"]) | set(hf03["staging_unresolved"])
    i5_ok = bool(stg_paths) and all(not excluded_live_first(s) for s in stg_paths)
    check("C5_I1_no_live_pin_excluded", not i1_bad, True, {"counterexamples": i1_bad})
    check("C5_I2_excluded_are_historical", not i2_bad, True, {"counterexamples": i2_bad})
    check("C5_I3_reconciliation", i3_ok, True, recon)
    check("C5_I4_controls", i4_ok, True,
          {"archive_pre_rev3_excluded": excluded_live_first(
              "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl"),
           "sources_batch01_kept": not excluded_live_first(
               "artifacts/literature/sources/batch-01.jsonl")})
    check("C5_I5_staging_surfaced", i5_ok, True, {"staging": sorted(stg_paths)})

    # ---- C6: scope predicate safety over the LIVE tree --------------------------------
    live_excluded, excluded_total, live_hazard = [], 0, []
    for root in SCAN_ROOTS:
        rp = ROOT / root
        if not rp.exists():
            continue
        for p in rp.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(ROOT))
            cls = classify_live_first(rel)
            if excluded_live_first(rel):
                excluded_total += 1
                if cls in LIVE_CLASSES:
                    live_excluded.append({"path": rel, "class": cls})
            if cls in LIVE_CLASSES and exclusion_matches(rel):
                live_hazard.append({"path": rel, "class": cls})
    check("C6_no_live_path_excluded", not live_excluded, True,
          {"excluded_files_in_scan": excluded_total, "live_class_excluded": live_excluded})
    check("C6_no_live_path_matches_exclusion_naive", not live_hazard, False,
          {"live_class_matching_literal_exclusion": live_hazard[:20],
           "count": len(live_hazard)})
    check("C6_ledger_never_excluded", not any(excluded_live_first(s) for s in
          [p for p in CANONICAL] + [str(p.relative_to(ROOT)) for p in (ROOT / "ledger").rglob("*") if p.is_file()]),
          True, {"canonical": list(CANONICAL)})

    # ---- C7: pre-registered precedence controls ---------------------------------------
    ctl = {
        "CTL-A_live_build_input_kept": not excluded_live_first("artifacts/literature/sources/batch-01.jsonl"),
        "CTL-B_archive_excluded": excluded_live_first("artifacts/literature/archive/x.pre-y.jsonl"),
        "CTL-C_snapshot_excluded": excluded_live_first("artifacts/worker-007/foo/snapshot/theorems.jsonl"),
        "CTL-D_staging_surfaced": classify_live_first(
            "artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl") == "staging_unresolved"
            and not excluded_live_first("artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl"),
        "CTL-E_hazard_live_under_snapshot": (classify_live_first(
            "artifacts/literature/sources/snapshot/batch-01.jsonl") == "live_build_input"
            and not excluded_live_first("artifacts/literature/sources/snapshot/batch-01.jsonl")
            and exclusion_matches("artifacts/literature/sources/snapshot/batch-01.jsonl")),
        "CTL-F_hf14_fires": hf14_hit({"theorem_id": "T-X", "status": "accepted"}),
        "CTL-G_hf14_reviewer_suppresses": not hf14_hit(
            {"theorem_id": "T-X", "status": "accepted", "reviewed_by": "worker-000"}),
        "CTL-H_hf03_missing_meta_fires": hf03_hit({"source_id": "SRC-X", "status": "verified-primary"}),
        "CTL-I_hf03_full_meta_clean": not hf03_hit(
            {"source_id": "SRC-X", "status": "verified-primary",
             "source_meta": {"matter_model": "vacuum", "cosmological_constant": 0,
                              "dimension": 4, "symmetry": "none", "formulation": "EFE"}}),
    }
    check("C7_precedence_controls", all(ctl.values()), True, ctl)

    # ---- C8: excluded files are not live inputs / current canonical bytes -------------
    canonical_hashes = {sha256_file(ROOT / c) for c in CANONICAL if (ROOT / c).is_file()}
    excluded_paths = sorted(set(hf14["excluded"]) | set(hf03["excluded"]))
    c8_bad, copied = [], []
    for rel in excluded_paths:
        h = sha256_file(ROOT / rel)
        if h in canonical_hashes:
            c8_bad.append({"path": rel, "reason": "byte-identical to a canonical ledger file"})
        if h == "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72":
            copied.append(rel)
    refs = []
    live_lit = [ROOT / "artifacts/literature/MANIFEST.json",
                ROOT / "artifacts/literature/registry.jsonl"]
    live_lit += sorted((ROOT / "artifacts/literature/tools").glob("*")) if \
        (ROOT / "artifacts/literature/tools").is_dir() else []
    blob = ""
    for p in live_lit:
        if p.is_file() and p.suffix in (".json", ".jsonl", ".py", ".md"):
            blob += p.read_text(errors="replace")
    for rel in excluded_paths:
        if rel in blob:
            refs.append(rel)
    check("C8_excluded_not_canonical_bytes", not c8_bad, True,
          {"excluded": excluded_paths, "canonical_byte_matches": c8_bad,
           "pre_rev3_copies_ce42d205": len(copied)})
    check("C8_excluded_not_referenced_by_live_literature", not refs, True,
          {"references": refs, "referenced_files": [str(p.relative_to(ROOT)) for p in live_lit
                                                     if p.is_file()]})

    # ---- C9: canonical ledger is genuinely clean at the pinned bytes ------------------
    canon_rows = load_rows(ROOT / "ledger/theorems.jsonl")
    canon_recs = [r for r in canon_rows if is_ledger_record(r)]
    canon_hf14 = sum(1 for r in canon_recs if hf14_hit(r, False))
    check("C9_canonical_hf14_zero", canon_hf14 == 0, True,
          {"records": len(canon_recs), "hf14_hits": canon_hf14,
           "sha256": sha256_file(ROOT / "ledger/theorems.jsonl")[:12]})

    # ---- C10: detector tool precedence corroboration (textual, non-semantic) ----------
    det_text = (ROOT / DETECTOR).read_text(errors="replace") if (ROOT / DETECTOR).is_file() else ""
    order_ok = det_text.find('return "canonical"') < det_text.find('return "historical"') \
        if det_text else False
    check("C10_detector_live_first_order", order_ok, False,
          {"detector": DETECTOR, "sha256": sha256_file(ROOT / DETECTOR)[:12] if det_text else None,
           "has_excluded_fn": "def excluded(" in det_text})

    # ---- drift re-pin ------------------------------------------------------------------
    pin_after = {ARTIFACT: sha256_file(art_path), RUBRIC: sha256_file(rub_path)}
    moved = []
    for rel, d in sorted(pins.items()):
        p = ROOT / rel
        if not p.is_file() or sha256_file(p) != d.get("sha256"):
            moved.append(rel)
    check("C11_no_input_drift", pin_before == pin_after and not moved, True,
          {"artifact_rubric_stable": pin_before == pin_after, "file_pins_moved": moved})

    hard_ok = not hard_failures
    verdict = "ACCEPT_SCOPE_LIMITED" if hard_ok else "REVISE"
    report = {
        "artifact": "W092-A0-SCOPE-INDEP-01",
        "task_id": "W092-A0-SCOPE-INDEP-01",
        "actor": "worker-092",
        "node_id": "A0",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "target": f"{ARTIFACT}#{ARTIFACT_PIN[:12]}",
        "target_sha256": ARTIFACT_PIN,
        "rubric_sha256": RUBRIC_PIN,
        "created_at": started,
        "verdict_recommendation": verdict,
        "authority": ("Worker measurement and one independent review verdict. Cannot set node "
                      "status=done, validation_status=passed or any gate verdict; sets none."),
        "checks": checks,
        "hard_failures": hard_failures,
        "soft_findings": soft_findings,
        "independent_detector_counts": {
            "hf14_v2_per_file": hf14_v2, "hf14_v1_per_file": hf14_v1,
            "hf03_per_file": hf03_ind,
        },
        "live_tree_scope_scan": {
            "scan_roots": list(SCAN_ROOTS),
            "excluded_files": excluded_total,
            "live_class_excluded": live_excluded,
            "live_class_matching_literal_exclusion": live_hazard[:50],
        },
        "controls": ctl,
        "falsifier": ("Re-run verify_a0_scope.py at the pinned hashes: this verdict is falsified if any "
                      "declared file pin no longer resolves to its declared sha256, if any per-file HF-14/HF-03 "
                      "count differs from the independent reproduction, if any canonical ledger or live build "
                      "input path is classified excluded, if any excluded path is a live input of the current "
                      "literature build or is byte-identical to a canonical ledger file, if the I1-I5 "
                      "reconciliation fails, or if any pre-registered control departs from its expectation. "
                      "A write to the scope artifact or the rubric voids this verdict."),
        "not_claimed": [
            "not a gate verdict; G-AUDIT state is unchanged",
            "does not re-adjudicate the HF-03 live finding or the required repair",
            "does not license adopting the predicate into audit_run.py",
            "does not verify the whole-corpus counts at 00:53:51 (corpus has grown); only the "
            "27 declared file pins and their per-file detector counts are re-measured",
        ],
    }
    return 0 if hard_ok else 1, report


if __name__ == "__main__":
    rc, rep = main()
    text = json.dumps(rep, indent=2, sort_keys=True) + "\n"
    out = HERE / "report.json"
    out.write_text(text)
    print(json.dumps({"verdict": rep["verdict_recommendation"],
                      "hard_failures": rep["hard_failures"],
                      "soft_findings": rep["soft_findings"],
                      "checks_failed": [c["id"] for c in rep["checks"] if not c["ok"]],
                      "report_sha256": sha256_text(text)}, indent=1))
    sys.exit(rc)
