#!/usr/bin/env python3
"""W021-A0-HF03-REPL-01 -- independent read-only replication of the A0 HF-03 live finding.

Object under test (audit lead, 2026-09-12T00:59:26):
  * blocker audit-l06-b2-hf03-live-20260912T005926: "HF-03 survives the A0 scope correction as a
    REAL finding: 194 citation rows across the 11 declared live build inputs
    artifacts/literature/sources/batch-*.jsonl plus the emitted artifacts/literature/registry.jsonl
    lack class-scope metadata".
  * blocker audit-l06-b3-staging-20260912T005926: the two worker-07 staging files carry
    "12 HF-14 records and 1 HF-03 record".
  * artifact evaluation/A0_detector_scope_adjudication.json#a26be4b8 (measured at 00:53:51,
    rubric evaluation_rubric.yaml#d748a9e3).

This instrument imports NO author code. It re-implements, from the documented routing rule and the
rubric text only:
  - corpus enumeration over the declared scan roots (artifacts, comms/outbox, ledger);
  - the citation/record routing predicate;
  - the implemented HF-03 predicate "citation lacks source_meta scope keys" (audit_lib
    check_ledger_scope, severity major) AND the literal rubric HF-03 predicate
    (resolution_status in {unresolved, contradicted} OR class metadata mismatches the claim's class,
    severity critical) as a separate, independently reported arm;
  - the implemented HF-14 predicate (self-certified acceptance without a reviewer verdict);
  - the scope taxonomy (canonical / live_build_input / live_emitted / historical / snapshot_copy /
    staging_unresolved / live_other).

Read-only on every canonical path: this script writes only under its own --outdir (default:
artifacts/worker-021/a0_hf03_replication). It is deterministic and fail-closed on input drift.

Exit codes: 0 = run complete and controls pass; 2 = VOID (declared pin drift); 3 = control failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-021/a0_hf03_replication -> repo root
SCAN_ROOTS = ("artifacts", "comms/outbox", "ledger")

ADJUDICATION = "evaluation/A0_detector_scope_adjudication.json"
AUDIT_OUTBOX = "comms/outbox/astra-lead-audit.jsonl"
RUBRIC = "evaluation_rubric.yaml"
B3_EVENT_ID = "audit-l06-b3-staging-20260912T005926"

# --- independent re-implementation of the routing rule (audit_run.scan_corpus) -------------
FIXTURE_TOKENS = ("/fixtures/", "/corpus/", "/selftest/", "repaired_inputs")
FIXTURE_SUFFIXES = ("EXPECTATIONS.json", "manifest.json")
SKIP_PATH_TOKENS = ("audit/reports", "audit/checkpoints")

# --- independent re-implementation of audit_lib.check_ledger_scope --------------------------
IMPL_SCOPE_KEYS = ("matter_model", "cosmological_constant", "dimension", "symmetry")

# --- rubric vocabulary (evaluation_rubric.yaml HF-03 branch + citation status vocabulary) ---
STATUS_TABLE = {
    "verified_primary": "verified_primary",
    "verified_api": "verified_secondary",
    "verified_secondary": "verified_secondary",
    "partial": "partial",
    "unresolved": "unresolved",
    "contradicted": "contradicted",
}
CONTRADICTED_OR_UNRESOLVED = ("unresolved", "contradicted")

# --- scope taxonomy (re-implemented from the adjudication artifact's declared taxonomy) -----
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
HISTORICAL_SEGMENTS = ("/archive/", "/incoming/")
SNAPSHOT_SEGMENTS = ("/snapshot/", "/snapshots/", "/probe/", "/proposed/", "/staging/",
                     "/scratch/", "/prev/")
HISTORICAL_BASENAME_TOKENS = (".pre-", ".prev-", "_snapshot.", ".snapshot-", ".bak")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _author_context(p: Path):
    """Independent context probe for a newly-live file: (a) does the author's own task directory
    describe the file in its report/controls text, and (b) does the author's SHA256SUMS pin its
    hash?  Used only to classify a file's *role*; the firing count is measured independently."""
    if not p.exists():
        return False, None
    task = p.parents[1]
    rel = str(p.relative_to(ROOT))
    declares = False
    for name in ("REPORT.md", "report.json", "controls.json", "README.md"):
        q = task / name
        if q.exists():
            t = q.read_text(errors="replace")
            if p.name in t or rel in t:
                declares = True
                break
    pin = None
    for sums in sorted(task.glob("SHA256SUMS*")):
        for line in sums.read_text(errors="replace").splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].strip().lstrip("*") == rel:
                pin = parts[0]
    return declares, pin


def classify(rel: str) -> str:
    if rel in CANONICAL:
        return "canonical"
    if any(rel.startswith(p) for p in LIVE_BUILD_INPUT_PREFIXES):
        return "live_build_input"
    if rel in LIVE_EMITTED:
        return "live_emitted"
    base = rel.rsplit("/", 1)[-1]
    if any(seg in "/" + rel for seg in HISTORICAL_SEGMENTS) or \
       any(tok in base for tok in HISTORICAL_BASENAME_TOKENS):
        return "historical"
    if any(seg in "/" + rel for seg in SNAPSHOT_SEGMENTS) or "snapshot" in base:
        return "snapshot_copy"
    if "/ledger_contribution/" in "/" + rel or rel.startswith("artifacts/worker-07/ledger"):
        return "staging_unresolved"
    return "live_other"


def excluded(rel: str) -> bool:
    """The adjudication's proposed scope predicate: historical + snapshot copies only."""
    return classify(rel) in ("historical", "snapshot_copy")


def is_citation(rel: str, obj: dict) -> bool:
    is_fixture = any(t in rel for t in FIXTURE_TOKENS) or rel.endswith(FIXTURE_SUFFIXES)
    status = obj.get("resolution_status") or obj.get("status")
    return bool(status and ("cite_key" in obj or "source_id" in obj) and not is_fixture)


def iter_objects(path: Path):
    """Independent JSON-object iterator: .jsonl lines, .json whole documents / top-level lists."""
    text = path.read_text(errors="replace")
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    elif path.suffix == ".json":
        try:
            obj = json.loads(text)
        except ValueError:
            return
        if isinstance(obj, list):
            for o in obj:
                if isinstance(o, dict):
                    yield o
        elif isinstance(obj, dict):
            yield obj


def enumerate_corpus(roots=SCAN_ROOTS):
    files, citations, records = [], [], []
    for r in roots:
        d = ROOT / r
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix not in (".json", ".jsonl"):
                continue
            rel = str(p.resolve().relative_to(ROOT.resolve()))
            if any(tok in rel for tok in SKIP_PATH_TOKENS):
                continue
            files.append(rel)
            for obj in iter_objects(p):
                if is_citation(rel, obj):
                    o = dict(obj)
                    o["_src"] = rel
                    citations.append(o)
                if ("theorem_id" in obj or ("class_ids" in obj and "statement_exact" in obj)) \
                        and not (any(t in rel for t in FIXTURE_TOKENS) or rel.endswith(FIXTURE_SUFFIXES)):
                    o = dict(obj)
                    o["_src"] = rel
                    records.append(o)
    return {"files": files, "citations": citations, "records": records}


def normalize_status(s: str) -> str:
    key = str(s).strip().lower().replace("-", "_").replace(" ", "_")
    return STATUS_TABLE.get(key, "unresolved")  # unknown -> unresolved, fail closed


def hf03_impl_flags(citations):
    """Implemented predicate (audit_lib.check_ledger_scope): missing scope metadata."""
    flags = []
    for c in citations:
        meta = c.get("source_meta") or {}
        missing = [k for k in IMPL_SCOPE_KEYS if k not in meta]
        if not meta.get("formulation") and not c.get("formulation"):
            missing.append("formulation")
        if missing:
            flags.append({"file": c.get("_src", "ledger"),
                          "key": c.get("cite_key") or c.get("source_id") or c.get("title"),
                          "missing": missing})
    return flags


def hf03_rubric_flags(citations):
    """Literal rubric branch: resolution_status in {unresolved, contradicted} OR an evaluable
    class-metadata mismatch against the citing claim's class. Absence of metadata is NOT a
    mismatch; such rows are reported separately as non-evaluable."""
    contradiction, mismatch, absent = [], [], []
    for c in citations:
        st = normalize_status(c.get("resolution_status") or c.get("status"))
        if st in CONTRADICTED_OR_UNRESOLVED:
            contradiction.append({"file": c.get("_src"), "key": c.get("cite_key") or c.get("source_id"),
                                  "status": st})
            continue
        meta = c.get("source_meta") or {}
        have_any = any(k in meta for k in IMPL_SCOPE_KEYS)
        claim_scope = c.get("_claim_scope")  # not present in the corpus surface today
        if not have_any:
            absent.append({"file": c.get("_src"), "key": c.get("cite_key") or c.get("source_id"),
                           "status": st})
        elif claim_scope is not None and any(meta.get(k) != claim_scope.get(k) for k in IMPL_SCOPE_KEYS):
            mismatch.append({"file": c.get("_src"), "key": c.get("cite_key") or c.get("source_id")})
    return {"contradicted_or_unresolved": contradiction, "class_mismatch": mismatch,
            "absent_metadata_non_evaluable": absent}


def hf14_fires(r: dict) -> bool:
    accepted = (str(r.get("status", "")).lower() in ("accepted", "passed")
                or r.get("supports_claim") is True
                or str(r.get("validation_status", "")).lower() == "passed")
    has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))
    return bool(accepted and not has_review)


def hf14_impl_flags(records):
    """Implemented predicate (audit_lib.check_self_certification)."""
    flags = []
    for r in records:
        if hf14_fires(r):
            flags.append({"file": r.get("_src", ""),
                          "key": r.get("theorem_id") or r.get("claim_id") or "<record>"})
    return flags


def per_file(flags):
    out = {}
    for f in flags:
        out[f["file"]] = out.get(f["file"], 0) + 1
    return dict(sorted(out.items()))


def split_scope(counts):
    kept, dropped, staging = {}, {}, {}
    for src, n in counts.items():
        cls = classify(src)
        if cls in ("historical", "snapshot_copy"):
            dropped[src] = {"records": n, "class": cls}
        elif cls == "staging_unresolved":
            staging[src] = {"records": n, "class": cls}
        else:
            kept[src] = {"records": n, "class": cls}
    return {"kept": kept, "excluded": dropped, "staging_unresolved": staging}


def totals_by_scope(counts):
    out = {"kept": 0, "excluded": 0, "staging_unresolved": 0}
    for src, n in counts.items():
        cls = classify(src)
        if cls in ("historical", "snapshot_copy"):
            out["excluded"] += n
        elif cls == "staging_unresolved":
            out["staging_unresolved"] += n
        else:
            out["kept"] += n
    return out


# --- controls (synthetic, in-memory) -------------------------------------------------------
def controls() -> list[dict]:
    res = []

    def check(cid, desc, got, want):
        res.append({"id": cid, "desc": desc, "pass": got == want, "got": got, "want": want})

    # HF-03 implemented predicate
    cite_missing = {"source_id": "X1", "status": "verified-primary"}
    cite_full = {"source_id": "X2", "status": "verified-primary",
                 "source_meta": {"matter_model": "vacuum", "cosmological_constant": 0,
                                 "dimension": "3+1", "symmetry": "none_required",
                                 "formulation": "WCC"}}
    cite_form_only = {"source_id": "X3", "status": "verified-primary",
                      "source_meta": {"matter_model": "vacuum", "cosmological_constant": 0,
                                      "dimension": "3+1", "symmetry": "none_required"}}
    check("K1", "HF-03(impl) fires on citation with no source_meta",
          len(hf03_impl_flags([dict(cite_missing, _src="f")])), 1)
    check("K2", "HF-03(impl) is silent on complete source_meta",
          len(hf03_impl_flags([dict(cite_full, _src="f")])), 0)
    check("K3", "HF-03(impl) fires when only formulation is absent",
          len(hf03_impl_flags([dict(cite_form_only, _src="f")])), 1)

    # HF-14 implemented predicate
    rec_bad = {"theorem_id": "T-1", "status": "accepted"}
    rec_ok = {"theorem_id": "T-2", "validation_status": "passed", "review_verdict": "accept"}
    rec_ok2 = {"theorem_id": "T-3", "supports_claim": True, "reviewed_by": "w-000"}
    rec_named = {"theorem_id": "T-4", "status": "accepted", "reviewer_verdict": "accept"}
    check("K4", "HF-14(impl) fires on self-certified acceptance without a review field",
          len(hf14_impl_flags([dict(rec_bad, _src="f")])), 1)
    check("K5", "HF-14(impl) is silent with review_verdict (the field name the impl recognizes)",
          len(hf14_impl_flags([dict(rec_ok, _src="f")])), 0)
    check("K6", "HF-14(impl) is silent with reviewed_by",
          len(hf14_impl_flags([dict(rec_ok2, _src="f")])), 0)
    check("K6b", "FIELD-NAME SENSITIVITY: reviewer_verdict is NOT recognized by the impl, so a row "
                 "carrying it still fires (measured false-positive channel)",
          len(hf14_impl_flags([dict(rec_named, _src="f")])), 1)

    # routing
    check("K7", "routing: status + source_id routes as a citation",
          is_citation("artifacts/literature/sources/batch-01.jsonl", cite_missing), True)
    check("K8", "routing: same object under /fixtures/ is fixture-excluded",
          is_citation("artifacts/x/fixtures/sources.jsonl", cite_missing), False)
    check("K8b", "routing: citation-shaped object with no status is not routed",
          is_citation("artifacts/literature/sources/batch-01.jsonl",
                      {"source_id": "X9", "title": "t"}), False)

    # scope taxonomy
    check("K9", "classify: archive -> historical", classify("artifacts/literature/archive/a.jsonl"), "historical")
    check("K10", "classify: sources -> live_build_input", classify("artifacts/literature/sources/batch-01.jsonl"), "live_build_input")
    check("K11", "classify: registry -> live_emitted", classify("artifacts/literature/registry.jsonl"), "live_emitted")
    check("K12", "classify: worker-07 ledger_contribution -> staging_unresolved",
          classify("artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl"),
          "staging_unresolved")
    check("K13", "classify: ledger/theorems.jsonl -> canonical", classify("ledger/theorems.jsonl"), "canonical")

    # rubric predicate arm
    cite_unres = {"source_id": "X4", "resolution_status": "unresolved"}
    r = hf03_rubric_flags([dict(cite_unres, _src="f")])
    check("K14", "HF-03(rubric) fires on resolution_status=unresolved",
          len(r["contradicted_or_unresolved"]), 1)
    r2 = hf03_rubric_flags([dict(cite_missing, _src="f")])
    check("K15", "HF-03(rubric) does NOT fire on verified_primary with absent metadata "
                 "(reported as non-evaluable absence instead)",
          (len(r2["contradicted_or_unresolved"]), len(r2["class_mismatch"]),
           len(r2["absent_metadata_non_evaluable"])), (0, 0, 1))
    return res


def load_declared():
    adj = json.loads((ROOT / ADJUDICATION).read_text())
    b3_text = ""
    for line in (ROOT / AUDIT_OUTBOX).read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("event_id") == B3_EVENT_ID:
            b3_text = e.get("description", "")
            break
    return adj, b3_text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(HERE))
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    adj, b3_text = load_declared()
    declared_pins = adj["measured"]["file_pins"]

    # --- drift guard (fail closed) ---------------------------------------------------------
    pins_start = {rel: (sha256_file(ROOT / rel) if (ROOT / rel).exists() else None)
                  for rel in declared_pins}
    drift = {rel: {"declared": v.get("sha256"), "now": pins_start[rel]}
             for rel, v in declared_pins.items() if v.get("sha256") != pins_start[rel]}

    inputs_hash_before = {r: sha256_file(ROOT / r) for r in (ADJUDICATION, AUDIT_OUTBOX, RUBRIC)
                          if (ROOT / r).exists()}

    corpus = enumerate_corpus()
    cites = corpus["citations"]
    recs = corpus["records"]

    impl_flags = hf03_impl_flags(cites)
    impl_counts = per_file(impl_flags)
    impl_split = split_scope(impl_counts)

    rub = hf03_rubric_flags(cites)
    rub_counts = {
        "contradicted_or_unresolved": per_file(rub["contradicted_or_unresolved"]),
        "class_mismatch": per_file(rub["class_mismatch"]),
        "absent_metadata_non_evaluable": per_file(rub["absent_metadata_non_evaluable"]),
    }

    hf14_flags = hf14_impl_flags(recs)
    hf14_counts = per_file(hf14_flags)
    hf14_split = split_scope(hf14_counts)

    # field-name census: which review-ish fields the corpus actually carries, and whether rows
    # carrying them still fire HF-14 because the implementation does not recognize the name
    review_fields = ("reviewer_verdicts", "review_verdict", "reviewed_by", "reviewer_verdict",
                     "reviewer", "review_status")
    hf14_field_census = {}
    for fld in review_fields:
        present = [r for r in recs if fld in r]
        hf14_field_census[fld] = {
            "records_with_field": len(present),
            "of_which_fire_under_impl": sum(1 for r in present if hf14_fires(r)),
        }

    # live HF-03 under the implemented predicate
    live_impl = impl_split["kept"]
    live_total = sum(v["records"] for v in live_impl.values())
    live_sources = sum(v["records"] for k, v in live_impl.items()
                       if k.startswith("artifacts/literature/sources/"))
    live_registry = sum(v["records"] for k, v in live_impl.items()
                        if k == "artifacts/literature/registry.jsonl")

    # staging (worker-07) facts -- the b3 discrepancy
    staging_sources = "artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl"
    staging_theorems = "artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl"
    staging_facts = {
        "hf03_records_batch-w07-sources": impl_counts.get(staging_sources, 0),
        "hf03_files_with_hits_in_staging": sum(1 for k in impl_counts if classify(k) == "staging_unresolved"),
        "hf14_records_batch-w07-theorems": hf14_counts.get(staging_theorems, 0),
        "hf14_files_with_hits_in_staging": sum(1 for k in hf14_counts if classify(k) == "staging_unresolved"),
        "b3_claims": "12 HF-14 records and 1 HF-03 record",
        "b3_event_found": bool(b3_text),
        "b3_text_excerpt": re.sub(r"\s+", " ", b3_text)[:400],
    }

    # declared-vs-measured comparison
    dm = adj["measured"]

    # --- new live-scope HF-14 hits that did not exist at the adjudication instant -------------
    declared_hf14_files = (set(dm["hf14"]["kept"]) | set(dm["hf14"]["excluded"])
                           | set(dm["hf14"]["staging_unresolved"]))
    outbox_blob = "\n".join(p.read_text(errors="replace")
                            for p in sorted((ROOT / "comms/outbox").glob("*.jsonl"))
                            if p.name != "worker-021.jsonl")  # exclude the measuring worker's own traffic
    new_live_hf14 = {}
    for f, v in hf14_split["kept"].items():
        if f in declared_hf14_files:
            continue
        rows_f = [r for r in recs if r.get("_src") == f]
        firing = [r for r in rows_f if hf14_fires(r)]
        status_census = {}
        for r in rows_f:
            s = str(r.get("status", "<none>"))
            status_census[s] = status_census.get(s, 0) + 1
        has_artifact_hash = sum(1 for r in firing
                                if r.get("artifact_sha256") or r.get("artifact_refs")
                                or r.get("artifact_hash"))
        p = ROOT / f
        new_live_hf14[f] = {
            "records_in_file": len(rows_f),
            "hf14_firing_records": len(firing),
            "class": classify(f),
            "excluded_by_predicate": excluded(f),
            "sha256": sha256_file(p) if p.exists() else None,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            if p.exists() else None,
            "status_census": status_census,
            "firing_rows_with_artifact_hash": has_artifact_hash,
            "all_firing_rows_carry_reviewer_verdict_field":
                all(bool(r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))
                    for r in firing),
            "named_in_other_agent_outbox": f in outbox_blob,
            "author_task_dir": str(p.parents[1].relative_to(ROOT)) if p.exists() else None,
            "author_declares_role": _author_context(p)[0],
            "author_checksums_pin": _author_context(p)[1],
        }
    comparison = {
        "hf03_kept": {"declared": dm["hf03"]["kept"], "measured": impl_split["kept"],
                      "agree": dm["hf03"]["kept"] == impl_split["kept"]},
        "hf03_excluded": {"declared": dm["hf03"]["excluded"], "measured": impl_split["excluded"],
                          "agree": dm["hf03"]["excluded"] == impl_split["excluded"]},
        "hf03_staging": {"declared": dm["hf03"]["staging_unresolved"],
                         "measured": impl_split["staging_unresolved"],
                         "agree": dm["hf03"]["staging_unresolved"] == impl_split["staging_unresolved"]},
        "hf03_totals": {"declared": [dm["hf03"]["before_total_records"],
                                     dm["hf03"]["after_total_records"]],
                        "measured": [sum(impl_counts.values()), live_total]},
        "hf14_excluded": {"declared": dm["hf14"]["excluded"], "measured": hf14_split["excluded"],
                          "agree": dm["hf14"]["excluded"] == hf14_split["excluded"]},
        "hf14_staging": {"declared": dm["hf14"]["staging_unresolved"],
                         "measured": hf14_split["staging_unresolved"],
                         "agree": dm["hf14"]["staging_unresolved"] == hf14_split["staging_unresolved"]},
        "hf14_totals": {"declared": [dm["hf14"]["before_total_records"],
                                     dm["hf14"]["after_total_records"]],
                        "measured": [sum(hf14_counts.values()), sum(v["records"] for v in hf14_split["kept"].values())]},
    }
    comparison["hf03_totals"]["agree"] = comparison["hf03_totals"]["declared"] == comparison["hf03_totals"]["measured"]
    comparison["hf14_totals"]["agree"] = comparison["hf14_totals"]["declared"] == comparison["hf14_totals"]["measured"]

    # determinism control: re-enumerate and re-measure
    corpus2 = enumerate_corpus()
    det = (per_file(hf03_impl_flags(corpus2["citations"])) == impl_counts and
           per_file(hf14_impl_flags(corpus2["records"])) == hf14_counts)

    ctl = controls()
    ctl.append({"id": "K16", "desc": "determinism: second enumeration reproduces HF-03 and HF-14 counts",
                "pass": det, "got": det, "want": True})
    ctl.append({"id": "K17", "desc": "declared-pin drift = 0",
                "pass": not drift, "got": len(drift), "want": 0})
    ctl.append({"id": "K18",
                "desc": "every new live-scope HF-14 file is kept (not excluded) by the declared "
                        "scope predicate",
                "pass": all(not v["excluded_by_predicate"] and v["class"] != "staging_unresolved"
                            for v in new_live_hf14.values()),
                "got": {f: v["class"] for f, v in new_live_hf14.items()}, "want": "live, not excluded"})
    ctl.append({"id": "K19",
                "desc": "every new live-scope HF-14 firing row sets status=accepted with no reviewer "
                        "verdict field and no artifact hash (literal rubric HF-14)",
                "pass": all(v["status_census"].get("accepted", 0) == v["hf14_firing_records"]
                            and not v["all_firing_rows_carry_reviewer_verdict_field"]
                            and v["firing_rows_with_artifact_hash"] == 0
                            for v in new_live_hf14.values()),
                "got": {f: {"accepted": v["status_census"].get("accepted", 0),
                            "firing": v["hf14_firing_records"]}
                        for f, v in new_live_hf14.items()}, "want": "accepted==firing, no review field"})
    new_live_drift = {f: {"measured": v["sha256"],
                          "now": sha256_file(ROOT / f) if (ROOT / f).exists() else None}
                      for f, v in new_live_hf14.items()}
    ctl.append({"id": "K20",
                "desc": "new live-scope HF-14 files stable across the run",
                "pass": all(v["measured"] == v["now"] for v in new_live_drift.values()),
                "got": {f: (v["now"] or "ABSENT")[:12] for f, v in new_live_drift.items()},
                "want": {f: (v["measured"] or "ABSENT")[:12] for f, v in new_live_drift.items()}})
    author_pin_ok = all((v["author_checksums_pin"] is None)
                        or (v["author_checksums_pin"] == v["sha256"])
                        for v in new_live_hf14.values())
    ctl.append({"id": "K21",
                "desc": "where the author's SHA256SUMS pins a new live-scope HF-14 file, the pinned "
                        "hash equals the independently measured hash",
                "pass": author_pin_ok,
                "got": {f: v["author_checksums_pin"] for f, v in new_live_hf14.items()},
                "want": {f: v["sha256"] for f, v in new_live_hf14.items()}})

    pins_end = {rel: (sha256_file(ROOT / rel) if (ROOT / rel).exists() else None)
                for rel in declared_pins}
    inputs_hash_after = {r: sha256_file(ROOT / r) for r in inputs_hash_before}
    end_drift = {rel: pins_end[rel] for rel in pins_start if pins_start[rel] != pins_end[rel]}
    controls_all_pass = all(c["pass"] for c in ctl)
    void = bool(drift or end_drift) or inputs_hash_before != inputs_hash_after

    artifact_agree = all(v["agree"] for v in comparison.values() if "agree" in v)
    b3_discrepancy = staging_facts["hf03_records_batch-w07-sources"] != 1
    new_live = bool(new_live_hf14)
    discrepancies = []
    if b3_discrepancy:
        discrepancies.append(
            f"staging HF-03 record count: blocker b3 claims 1; measured "
            f"{staging_facts['hf03_records_batch-w07-sources']} records in "
            f"{staging_sources} (matching the adjudication artifact's own staging_unresolved=7)")
    if new_live:
        ctx = "; ".join(
            f"{f}: class={v['class']}, author_declares_role={v['author_declares_role']}, "
            f"author_checksums_pin={str(v['author_checksums_pin'])[:12]}"
            for f, v in new_live_hf14.items())
        discrepancies.append(
            f"HF-14 after-scope total is not stable: {sum(v['hf14_firing_records'] for v in new_live_hf14.values())} "
            f"HF-14 records in {len(new_live_hf14)} file(s) written after the 00:53:51 measurement are "
            f"classified live_other and kept by the declared predicate (declared after_total_records=0); "
            f"context probe: {ctx}")
    if not artifact_agree:
        discrepancies.append("one or more declared per-file counts differ from the re-measurement")
    if void:
        verdict = "VOID"
    elif not controls_all_pass:
        verdict = "CONTROL_FAILURE"
    elif not discrepancies:
        verdict = "REPLICATED"
    else:
        verdict = "REPLICATED_WITH_DISCREPANCIES"

    results = {
        "task_id": "W021-A0-HF03-REPL-01",
        "instrument": "artifacts/worker-021/a0_hf03_replication/replicate_a0_hf03.py",
        "scan_roots": list(SCAN_ROOTS),
        "corpus": {"files": len(corpus["files"]), "citations": len(cites), "records": len(recs)},
        "inputs_sha256_before": inputs_hash_before,
        "inputs_sha256_after": inputs_hash_after,
        "declared_pin_drift": drift,
        "end_pin_drift": end_drift,
        "hf03_impl": {
            "per_file": impl_counts,
            "split": impl_split,
            "live_total": live_total,
            "live_sources_batches": live_sources,
            "live_registry": live_registry,
        },
        "hf03_rubric": rub_counts,
        "hf03_rubric_totals": {arm: totals_by_scope(counts) for arm, counts in rub_counts.items()},
        "hf14_impl": {"per_file": hf14_counts, "split": hf14_split,
                      "review_field_census": hf14_field_census},
        "hf14_new_live_since_adjudication": new_live_hf14,
        "new_live_pin_check": new_live_drift,
        "discrepancies": discrepancies,
        "staging_facts": staging_facts,
        "declared_vs_measured": comparison,
        "controls": ctl,
        "controls_all_pass": controls_all_pass,
        "void": void,
    }
    (outdir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")

    controls_obj = {
        "task_id": "W021-A0-HF03-REPL-01",
        "controls": ctl,
        "all_pass": controls_all_pass,
        "drift_zero": not drift and not end_drift,
        "void": void,
    }
    (outdir / "controls.json").write_text(json.dumps(controls_obj, indent=2, sort_keys=True) + "\n")

    report = {
        "task_id": "W021-A0-HF03-REPL-01",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "role": "independent read-only replication of the A0 HF-03 live finding + staging count",
        "pins": inputs_hash_before,
        "declared_pin_drift": len(drift),
        "end_pin_drift": len(end_drift),
        "void": void,
        "controls_all_pass": controls_all_pass,
        "controls_total": len(ctl),
        "hf03_impl_live_total": live_total,
        "hf03_impl_live_sources_batches": live_sources,
        "hf03_impl_live_registry": live_registry,
        "hf03_impl_excluded_total": sum(v["records"] for v in impl_split["excluded"].values()),
        "hf03_impl_staging_total": sum(v["records"] for v in impl_split["staging_unresolved"].values()),
        "hf03_rubric_by_scope": results["hf03_rubric_totals"],
        "hf14_impl_before_total": sum(hf14_counts.values()),
        "hf14_impl_after_total": sum(v["records"] for v in hf14_split["kept"].values()),
        "hf14_new_live_since_adjudication": {
            "files": {f: {"firing_records": v["hf14_firing_records"], "class": v["class"],
                          "sha256": v["sha256"], "mtime": v["mtime"],
                          "named_in_other_agent_outbox": v["named_in_other_agent_outbox"],
                          "author_task_dir": v["author_task_dir"],
                          "author_declares_role": v["author_declares_role"],
                          "author_checksums_pin": v["author_checksums_pin"]}
                      for f, v in new_live_hf14.items()},
            "total_records": sum(v["hf14_firing_records"] for v in new_live_hf14.values()),
        },
        "discrepancies": discrepancies,
        "staging_facts": staging_facts,
        "declared_agreement": {k: v["agree"] for k, v in comparison.items() if "agree" in v},
        "artifact_agreement_all": artifact_agree,
        "b3_record_count_discrepancy": b3_discrepancy,
        "verdict": verdict,
        "falsifier": ("Re-run at the same pins: the replication is FALSIFIED if the live HF-03 "
                      "count is not 194 (97 registry + 97 across the 11 sources batches), if the "
                      "worker-07 staging HF-03 record count is not 7, or if any control K1-K17 "
                      "fails. It is VOID if any of the 27 declared file pins or the rubric / "
                      "adjudication / outbox inputs move."),
    }
    (outdir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    raw = {"declared_pins": {k: v.get("sha256") for k, v in declared_pins.items()},
           "start": pins_start, "end": pins_end}
    (outdir / "raw" / "inputs_sha256.json").write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"verdict": verdict, "void": void, "controls_all_pass": controls_all_pass,
                      "hf03_live": live_total, "hf03_sources": live_sources,
                      "hf03_registry": live_registry,
                      "hf03_staging_records": staging_facts["hf03_records_batch-w07-sources"],
                      "hf14_staging_records": staging_facts["hf14_records_batch-w07-theorems"],
                      "rubric_by_scope": results["hf03_rubric_totals"]}, indent=2))
    if void:
        return 2
    return 0 if controls_all_pass else 3


if __name__ == "__main__":
    sys.exit(main())
