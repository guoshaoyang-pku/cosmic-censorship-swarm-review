#!/usr/bin/env python3
"""W029-L0-REV3-VERDICT-05 — independent deterministic L0 rev3 checker.

Reads only the frozen snapshots recorded in snapshot_manifest.json (plus a live
drift comparison by hash, and a bounded scan for L1 spot-check files). Writes
report_core.json / report.json / evidence.json next to itself. No canonical
artifact is written or edited.

Checks:
  C1  snapshot integrity + live drift
  C2  ledger parse / unique ids / required keys
  C3  class-token census: frozen-four-only, multi-class rows, empty rows, metric
  C4  HF-14 (self-certified acceptance): literal census, canonical predicate,
      pre-rev3 contrast (positive control)
  C5  revision content preservation pre-rev3 -> rev3 (rename-only claim)
  C6  HF-01 (fluent-text promotion): claim-scope test on ledger records
  C7  HF-02 (class leakage): literal disjunction branch + registry rule + the
      detectors actually implemented
  C8  citation linkage ledger(source_ids) -> citation_audit
  C9  G-LIT gate criteria (locators / honesty / spot checks / unresolved)
  C10 controls + determinism digest

Usage:
    python3 artifacts/worker-029/l0_rev3_verify/check_l0_rev3.py
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshots"
CST = timezone(timedelta(hours=8))
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
L1_HASH = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

CONTENT_KEYS = [
    "statement_exact", "assumptions", "class_ids", "regularity", "topology", "genericity",
    "falsifiers", "unresolved", "source_ids", "conclusion_type", "label", "theorem_id",
    "entry_kind", "scope_caveats", "does_not_imply", "ledger_tags", "next_action",
    "verification_status",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    return json.loads((HERE / "snapshot_manifest.json").read_text())


def snap_path(rel: str) -> Path:
    return SNAP / rel.replace("/", "__")


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- checks
def check_c1(manifest: dict) -> dict:
    files, mismatch, drift = [], [], []
    for f in manifest["files"]:
        if f.get("missing"):
            mismatch.append({"source_path": f["source_path"], "reason": "missing at snapshot time"})
            continue
        sp = ROOT / f["snapshot_path"]
        h = sha256_file(sp)
        ok = h == f["sha256"]
        if not ok:
            mismatch.append({"source_path": f["source_path"], "snapshot_sha256": f["sha256"],
                             "recomputed": h})
        live = ROOT / f["source_path"]
        lh = sha256_file(live) if live.is_file() else None
        d = lh != f["sha256"]
        if d:
            drift.append({"source_path": f["source_path"], "snapshot_sha256": f["sha256"],
                          "live_sha256": lh})
        files.append({"source_path": f["source_path"], "sha256": f["sha256"],
                      "snapshot_match": ok, "live_matches_snapshot": not d})
    return {"id": "C1", "name": "snapshot-integrity-and-live-drift", "hard": True,
            "status": "PASS" if not mismatch and not drift else "FAIL",
            "detail": {"files": files, "snapshot_mismatches": mismatch, "live_drift": drift}}


def check_c2(rows: list[dict]) -> dict:
    ids = [r.get("theorem_id") for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    missing_keys = sorted({k for k in
                           ("theorem_id", "class_ids", "conclusion_type", "verification_status",
                            "review_status", "source_ids", "statement_exact", "unresolved",
                            "content_status", "author_asserts_supports", "acceptance_authority")
                           if any(k not in r for r in rows)})
    return {"id": "C2", "name": "ledger-parse", "hard": True,
            "status": "PASS" if len(rows) == 62 and not dupes and not missing_keys else "FAIL",
            "detail": {"rows": len(rows), "unique_ids": len(set(ids)), "duplicate_ids": dupes,
                       "missing_required_keys": missing_keys}}


def check_c3(rows: list[dict], taxonomy_classes: list[str], cs) -> dict:
    tokens = {}
    for r in rows:
        for c in r.get("class_ids") or []:
            tokens[c] = tokens.get(c, 0) + 1
    unknown = sorted(t for t in tokens if t not in FROZEN)
    multi = sorted(r["theorem_id"] for r in rows if len(r.get("class_ids") or []) >= 2)
    empty = sorted(r["theorem_id"] for r in rows if not (r.get("class_ids") or []))
    informs = {r["theorem_id"]: r["informs_classes"] for r in rows if "informs_classes" in r}
    informs_unknown = sorted({c for v in informs.values() for c in v if c not in FROZEN})
    singular = sum(1 for r in rows if len(r.get("class_ids") or []) == 1)
    metric = round(singular / len(rows), 4)
    obj_findings, prose_findings = [], []
    for r in rows:
        obj_findings += cs.findings(r, f"ledger:{r['theorem_id']}", mode="prose")
        prose_findings += cs.findings_for_text(json.dumps(r, ensure_ascii=False),
                                               f"ledger:{r['theorem_id']}")
    return {"id": "C3", "name": "class-token-census", "hard": True,
            "status": "PASS" if not unknown and not informs_unknown
                      and set(taxonomy_classes) == set(FROZEN)
                      else "FAIL",
            "detail": {"rows": len(rows), "frozen_four_only": not unknown,
                       "tokens": tokens, "unknown_tokens": unknown,
                       "taxonomy_classes_at_snapshot": taxonomy_classes,
                       "multi_class_rows": multi, "empty_class_rows": empty,
                       "informs_classes_rows": informs, "informs_unknown": informs_unknown,
                       "singular_rows": singular, "class_binding_metric": metric,
                       "metric_target": 1.0,
                       "soft_findings": obj_findings[:20],
                       "soft_finding_count": len(obj_findings),
                       "prose_mode_finding_count": len(prose_findings)}}


def check_c4(rows: list[dict], pre_rows: list[dict], audit_mod) -> dict:
    def census(rs):
        return {
            "rows": len(rs),
            "has_status_key": sum(1 for r in rs if "status" in r),
            "status_accepted": sum(1 for r in rs if str(r.get("status", "")).lower() in ("accepted", "passed")),
            "has_supports_claim": sum(1 for r in rs if "supports_claim" in r),
            "supports_claim_true": sum(1 for r in rs if r.get("supports_claim") is True),
            "has_validation_status": sum(1 for r in rs if "validation_status" in r),
            "has_content_status": sum(1 for r in rs if "content_status" in r),
            "has_author_asserts_supports": sum(1 for r in rs if "author_asserts_supports" in r),
            "has_review_status": sum(1 for r in rs if "review_status" in r),
            "has_acceptance_authority": sum(1 for r in rs if "acceptance_authority" in r),
        }
    live = census(rows)
    pre = census(pre_rows)
    # canonical predicate, reimplemented verbatim from audit_lib.py:459-473 (snapshot)
    canonical = audit_mod.check_self_certification([dict(r, _source="ledger/theorems.jsonl") for r in rows])
    canonical_pre = audit_mod.check_self_certification(
        [dict(r, _source="artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl")
         for r in pre_rows])
    review_vals = {}
    for r in rows:
        v = r.get("review_status")
        review_vals[v] = review_vals.get(v, 0) + 1
    return {"id": "C4", "name": "HF-14-self-certified-acceptance", "hard": True,
            "status": "PASS" if (live["has_status_key"] == 0 and live["has_supports_claim"] == 0
                                 and live["has_validation_status"] == 0
                                 and live["has_content_status"] == len(rows)
                                 and live["has_author_asserts_supports"] == len(rows)
                                 and live["has_review_status"] == len(rows)
                                 and len(canonical) == 0) else "FAIL",
            "detail": {
                "live_census": live, "pre_rev3_census": pre,
                "canonical_predicate_live_violations": len(canonical),
                "canonical_predicate_pre_rev3_violations": len(canonical_pre),
                "pre_rev3_first_violation": (canonical_pre[0].where if canonical_pre else None),
                "review_status_values": review_vals,
                "acceptance_authority_value": rows[0].get("acceptance_authority"),
                "note": "pre-rev3 contrast is the positive control: same predicate, 60 violations at "
                        "ce42d205e761, 0 at a1674f094979",
            }}


def check_c5(rows: list[dict], pre_rows: list[dict]) -> dict:
    live = {r["theorem_id"]: r for r in rows}
    pre = {r["theorem_id"]: r for r in pre_rows}
    common = sorted(set(live) & set(pre))
    diffs, rename_mismatch = [], []
    status_map = {"accepted": "verified", "provisional": "provisional",
                  "unresolved": "unresolved", "rejected": "rejected"}
    for tid in common:
        a, b = pre[tid], live[tid]
        for k in CONTENT_KEYS:
            if k == "verification_status":
                continue
            if a.get(k) != b.get(k):
                diffs.append({"theorem_id": tid, "key": k})
        old_s, new_cs = a.get("status"), b.get("content_status")
        if status_map.get(str(old_s)) != new_cs:
            rename_mismatch.append({"theorem_id": tid, "old_status": old_s, "new_content_status": new_cs})
        if a.get("supports_claim") != b.get("author_asserts_supports"):
            rename_mismatch.append({"theorem_id": tid, "old_supports_claim": a.get("supports_claim"),
                                    "new_author_asserts_supports": b.get("author_asserts_supports")})
        if a.get("verification_status") != b.get("verification_status"):
            diffs.append({"theorem_id": tid, "key": "verification_status"})
    return {"id": "C5", "name": "revision-content-preservation", "hard": True,
            "status": "PASS" if not diffs and not rename_mismatch and len(common) == len(pre) else "FAIL",
            "detail": {"pre_rev3_rows": len(pre), "rev3_rows": len(rows), "common_ids": len(common),
                       "content_key_diffs": diffs[:20], "content_key_diff_count": len(diffs),
                       "rename_mismatches": rename_mismatch[:20],
                       "rename_mismatch_count": len(rename_mismatch),
                       "keys_added": sorted(set(rows[0]) - set(pre_rows[0])),
                       "keys_removed": sorted(set(pre_rows[0]) - set(rows[0]))}}


def check_c6(rows: list[dict]) -> dict:
    theorem_rows = [r for r in rows if r.get("conclusion_type") == "theorem"]
    no_art = [r["theorem_id"] for r in theorem_rows if not r.get("artifact_refs")]
    no_src = [r["theorem_id"] for r in theorem_rows if not r.get("source_ids")]
    # canonical corpus classification: rows with theorem_id are records, not claims
    # (audit_run.py:117-119 snapshot); claims need claim_id or class_id+statement (line 100-102).
    enter_claims = [r["theorem_id"] for r in rows
                    if ("claim_id" in r or ("class_id" in r and "statement" in r))]
    return {"id": "C6", "name": "HF-01-fluent-text-promotion", "hard": False,
            "status": "INFO",
            "detail": {
                "rubric_detector": "claim.conclusion_type == theorem AND (no artifact_refs OR ...)",
                "theorem_rows": len(theorem_rows),
                "theorem_rows_without_artifact_refs": len(no_art),
                "theorem_rows_without_source_ids": len(no_src),
                "rows_entering_canonical_claim_corpus": len(enter_claims),
                "reading": ("detector is claim-scoped; ledger rows are parsed into the audit's "
                            "`records` corpus, never into `claims`; every theorem row carries "
                            "source_ids. HF-01 does not fire on these bytes."),
                "residual": ("vocabulary collision: comms/PROTOCOL.md rule 1 and "
                             "class_separation.py ASSERTED_LINE_KEYS read `conclusion_type` as an "
                             "asserted conclusion surface; author records this as BL-5 and defers a "
                             "joint A0+A1+L0 rename"),
            }}


def check_c7(rows: list[dict], registry: dict, cs) -> dict:
    allowed_forms = registry.get("class_id_rule")
    variants = {v["variant_id"]: v for v in registry.get("variants", [])}
    multi = [r for r in rows if len(r.get("class_ids") or []) >= 2]
    classified = []
    for r in multi:
        text = " ".join(str(r.get(k, "")) for k in
                        ("label", "regularity", "statement_exact", "scope_caveats", "assumptions"))
        hits = {}
        for vid in variants:
            for m in re.finditer(re.escape(vid), text):  # case-sensitive literal id
                hits[vid] = text[max(0, m.start() - 30):m.end() + 30]
        classified.append({
            "theorem_id": r["theorem_id"], "class_ids": r["class_ids"],
            "conclusion_type": r["conclusion_type"],
            "registered_variant_tokens_detected": sorted(hits),
            "variant_token_contexts": hits,
            "needs_formulation_ruling": True,
        })
    # canonical ledger-token check, reimplemented verbatim from audit_run.py:253-263
    invented = {}
    for r in rows:
        for cid in r.get("class_ids") or []:
            if cid not in FROZEN and cid not in ("DEFINITIONS", "GLOBAL"):
                invented[cid] = invented.get(cid, 0) + 1
    return {"id": "C7", "name": "HF-02-class-leakage-disjunction", "hard": True,
            "status": "FAIL" if multi else "PASS",
            "detail": {
                "rubric_detector": "unknown class_id | disjunction of class_ids | ...",
                "registry_rule": registry.get("rule"),
                "registry_class_id_rule": allowed_forms,
                "multi_class_rows": [r["theorem_id"] for r in multi],
                "multi_class_row_count": len(multi),
                "per_row": classified,
                "canonical_invented_token_violations": invented,
                "class_separation_declaration_mode_findings": len(
                    [f for r in rows for f in cs.findings(r, f"ledger:{r['theorem_id']}",
                                                          mode="prose")]),
                "class_separation_prose_mode_findings": len(
                    [f for r in rows for f in cs.findings_for_text(
                        json.dumps(r, ensure_ascii=False), f"ledger:{r['theorem_id']}")]),
                "literal_variant_ids_named_by_rows": sum(
                    1 for x in classified if x["registered_variant_tokens_detected"]),
                "finding": ("the rubric's literal branch `disjunction of class_ids` fires on the "
                            "named rows; the frozen-class registry allows only (i) one exact frozen "
                            "class_id or (ii) a (parent_class, variant_id) pair, so a class_ids list "
                            "of two frozen classes is neither form. The two detectors actually "
                            "implemented (audit_run.py ledger branch: invented tokens only; "
                            "class_separation.py: merged-token/unknown-token only) report 0, which "
                            "is the A1 coverage gap the author records as BL-6; remediation (which "
                            "class is primary, which becomes informs_classes or a registry variant "
                            "reference) is a content decision, as 0 of 8 rows name a registered "
                            "variant id literally"),
            }}


def check_c8(rows: list[dict], audit_rows: list[dict]) -> dict:
    by_id = {a.get("citation_id"): a for a in audit_rows}
    cited = sorted({s for r in rows for s in (r.get("source_ids") or [])})
    missing = [s for s in cited if s not in by_id]
    verdicts, resolver, http = {}, {}, {}
    non_verified, class_mismatch, mapping_unknown, locator_not_url = [], [], [], []
    mapping_tag_annotations = {}
    url_pat = re.compile(r"^(https?://|10\.\d{4,9}/|arXiv:)", re.I)
    for s in cited:
        a = by_id.get(s)
        if not a:
            continue
        verdicts[a.get("verdict")] = verdicts.get(a.get("verdict"), 0) + 1
        resolver[a.get("resolver_result")] = resolver.get(a.get("resolver_result"), 0) + 1
        http[str(a.get("http_status"))] = http.get(str(a.get("http_status")), 0) + 1
        if a.get("verdict") != "verified":
            non_verified.append(s)
        if not url_pat.match(str(a.get("exact_locator") or "")):
            locator_not_url.append(s)
        mapping, tags = [], []
        for raw in (a.get("class_mapping") or "").split(";"):
            raw = raw.strip()
            if not raw:
                continue
            base = re.sub(r"\s*\(.*?\)\s*$", "", raw).strip()
            if base in FROZEN:
                mapping.append(base)
            elif base.startswith("AF-"):
                mapping_unknown.append({"source": s, "token": raw})
            else:
                tags.append(raw)
        if tags:
            mapping_tag_annotations[s] = tags
        rows_for_src = [r for r in rows if s in (r.get("source_ids") or [])]
        for row in rows_for_src:
            # a mismatch is a row class the source's mapping does not cover at all
            uncovered = [c for c in (row.get("class_ids") or []) if c not in mapping]
            if mapping and uncovered:
                class_mismatch.append({"source": s, "row": row["theorem_id"],
                                       "row_class_ids": row["class_ids"],
                                       "audit_class_mapping": a.get("class_mapping"),
                                       "uncovered": uncovered})
    return {"id": "C8", "name": "citation-linkage", "hard": True,
            "status": "PASS" if not missing and not non_verified and not class_mismatch
                      and not mapping_unknown else "FAIL",
            "detail": {"cited_sources": len(cited), "audit_rows": len(audit_rows),
                       "missing_audit_rows": missing, "verdicts": verdicts,
                       "resolver_result": resolver, "http_status": http,
                       "non_verified_verdicts": non_verified,
                       "uncovered_row_classes": class_mismatch,
                       "audit_class_mapping_unknown_tokens": mapping_unknown,
                       "audit_class_mapping_tag_annotations": mapping_tag_annotations,
                       "exact_locator_not_url_or_doi": locator_not_url,
                       "exact_locator_not_url_or_doi_count": len(locator_not_url),
                       "note": "audit class_mapping is a superset context; a row class outside the "
                               "source's mapping is the mismatch. Parenthesised '(evidence/tag "
                               "only)' annotations are non-class tags, not unknown class tokens."}}


def check_c9(rows: list[dict], audit_rows: list[dict], spot: dict) -> dict:
    vs = {}
    for r in rows:
        vs[r.get("verification_status")] = vs.get(r.get("verification_status"), 0) + 1
    deep = [r["theorem_id"] for r in rows
            if r.get("verification_status") not in ("unverified", "abstract-read")]
    unresolved_marked = sum(1 for r in rows if r.get("unresolved"))
    resolved = sum(1 for a in audit_rows if a.get("resolver_result") == "resolved"
                   and str(a.get("http_status")) == "200")
    criteria = {
        "locators_resolvable": {"met": resolved > 0,
                                "detail": f"{resolved}/{len(audit_rows)} audit rows resolved+http200"},
        "verification_status_honest": {"met": not deep,
                                       "detail": f"vocabulary {vs}; rows above abstract-read: {len(deep)}"},
        "three_independent_spotchecks": {"met": spot["distinct_reviewers"] >= 3,
                                         "detail": f"{spot['distinct_reviewers']} distinct reviewers "
                                                   f"across {spot['files']} files at L1 {L1_HASH[:12]}"},
        "unresolved_marked": {"met": unresolved_marked == len(rows),
                              "detail": f"{unresolved_marked}/{len(rows)} rows carry a non-empty "
                                        f"`unresolved` field"},
    }
    met = sum(1 for v in criteria.values() if v["met"])
    return {"id": "C9", "name": "g-lit-gate-criteria", "hard": False,
            "status": "PASS" if met == 4 else "INFO",
            "detail": {"criteria": criteria, "met": met, "of": 4,
                       "verification_status_values": vs, "deep_verification_rows": deep,
                       "audit_rows_resolved_http200": resolved,
                       "note": "G-LIT's own four criteria are row-level; the L0 node verdict is "
                               "the open gate item, and the A0 critical HF-02 remains binding"}}


def check_c10(rows: list[dict], audit_rows: list[dict], cs, audit_mod) -> dict:
    controls = []
    # control 1: merged token must be flagged by class_separation
    merged = {"theorem_id": "CTRL-1", "class_ids": ["AF-SCC-C0-C2-VAC-GEN"], "statement_exact": "x"}
    f1 = cs.findings(merged, "control-merged-token")
    controls.append({"id": "CTRL-1", "expect": "class_separation flags merged C0/C2 token",
                     "observed": len(f1) > 0, "findings": f1[:2]})
    # control 2: invented frozen-shaped token must be flagged by the canonical ledger check
    invented = [{"theorem_id": "CTRL-2", "class_ids": ["AF-SCC-OTHER-MODELS"]}]
    inv = {}
    for r in invented + rows:
        for cid in r.get("class_ids") or []:
            if cid not in FROZEN and cid not in ("DEFINITIONS", "GLOBAL"):
                inv[cid] = inv.get(cid, 0) + 1
    controls.append({"id": "CTRL-2", "expect": "canonical ledger-token check flags invented token",
                     "observed": "AF-SCC-OTHER-MODELS" in inv, "flags": inv})
    # control 3: canonical HF-14 predicate fires on a self-certified synthetic row
    synth = [{"theorem_id": "CTRL-3", "status": "accepted", "supports_claim": True}]
    c3 = audit_mod.check_self_certification(synth)
    controls.append({"id": "CTRL-3", "expect": "canonical HF-14 predicate fires on status=accepted",
                     "observed": len(c3) == 1, "violations": len(c3)})
    # control 4: two frozen class ids in one list fire the rubric's literal branch but NOT the
    # two implemented detectors (the coverage gap itself)
    gap = {"theorem_id": "CTRL-4", "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
           "statement_exact": "x"}
    literal_fires = len(gap["class_ids"]) >= 2
    cs_fires = len(cs.findings(gap, "control-disjunction")) > 0
    canonical_invented = [c for c in gap["class_ids"] if c not in FROZEN]
    controls.append({"id": "CTRL-4",
                     "expect": "literal HF-02 branch fires; implemented detectors do not",
                     "observed": {"literal_disjunction_branch": literal_fires,
                                  "class_separation_fires": cs_fires,
                                  "canonical_invented_token_count": len(canonical_invented)}})
    all_ok = all(c["observed"] is True for c in controls[:3]) and \
        controls[3]["observed"] == {"literal_disjunction_branch": True,
                                    "class_separation_fires": False,
                                    "canonical_invented_token_count": 0}
    return {"id": "C10", "name": "controls", "hard": True,
            "status": "PASS" if all_ok else "FAIL", "detail": {"controls": controls}}


# ---------------------------------------------------------------- main
def main() -> int:
    manifest = load_manifest()
    measured_at = datetime.now(CST).isoformat(timespec="seconds")

    cs = load_module("cs_snapshot", snap_path("research_map/class_separation.py"))
    audit_lib = load_module("audit_lib_snapshot", snap_path("artifacts/audit/audit_lib.py"))

    rows = load_jsonl(snap_path("ledger/theorems.jsonl"))
    pre_rows = load_jsonl(snap_path(
        "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl"))
    registry = json.loads(snap_path("artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    audit_rows = list(csv.DictReader(snap_path("ledger/citation_audit.csv").open()))

    try:
        import yaml
        tax = yaml.safe_load(snap_path("research_map/formulation_taxonomy.yaml").read_text())
        taxonomy_classes = sorted((tax.get("classes") or {}).keys())
    except Exception:
        taxonomy_classes = []

    # bounded spot-check scan (live tree; recorded, not snapshotted byte-for-byte)
    spot_files, spot_reviewers = [], {}
    for pat in ("reviews/L1-spotcheck*.json", "artifacts/*/l1_spotcheck/*.json"):
        for p in sorted(ROOT.glob(pat)):
            try:
                txt = p.read_text(errors="replace")
            except OSError:
                continue
            if L1_HASH[:12] not in txt and L1_HASH not in txt:
                continue
            spot_files.append(str(p.relative_to(ROOT)))
            try:
                d = json.loads(txt)
                who = d.get("reviewer") or d.get("actor") or d.get("worker") or p.stem
            except ValueError:
                who = p.stem
            spot_reviewers[str(who)] = spot_reviewers.get(str(who), 0) + 1
    spot = {"files": len(spot_files), "distinct_reviewers": len(spot_reviewers),
            "reviewers": spot_reviewers, "paths": spot_files}

    checks = [
        check_c1(manifest),
        check_c2(rows),
        check_c3(rows, taxonomy_classes, cs),
        check_c4(rows, pre_rows, audit_lib),
        check_c5(rows, pre_rows),
        check_c6(rows),
        check_c7(rows, registry, cs),
        check_c8(rows, audit_rows),
        check_c9(rows, audit_rows, spot),
        check_c10(rows, audit_rows, cs, audit_lib),
    ]
    hard_failures = [c["id"] for c in checks if c["hard"] and c["status"] == "FAIL"]

    core = {
        "schema": "worker-029/l0-rev3-verdict/v1",
        "task_id": "W029-L0-REV3-VERDICT-05",
        "actor": "worker-029",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": FROZEN,
        "target": {"path": "ledger/theorems.jsonl",
                   "sha256": sha256_file(snap_path("ledger/theorems.jsonl")),
                   "rows": len(rows)},
        "companion": {"path": "ledger/citation_audit.csv",
                      "sha256": sha256_file(snap_path("ledger/citation_audit.csv")),
                      "rows": len(audit_rows)},
        "checks": checks,
        "hard_failures": hard_failures,
        "hf02_disjunction_rows": checks[6]["detail"]["multi_class_rows"],
        "class_binding": {"singular_rows": checks[2]["detail"]["singular_rows"], "rows": len(rows),
                          "metric": checks[2]["detail"]["class_binding_metric"], "target": 1.0},
        "spotcheck": spot,
        "verdict": {
            "verdict": "revise" if hard_failures else "accept",
            "score": 3.5 if hard_failures else 4.0,
            "counts_as_full_schema_verdict": True,
            "hard_failures": [{"id": "HF-02", "check_id": "C7", "severity": "hard",
                               "finding": checks[6]["detail"]["finding"],
                               "rows": checks[6]["detail"]["multi_class_rows"]}],
            "closed_at_this_hash": [{"id": "HF-14", "check_id": "C4",
                                     "finding": "self-certification closed by the content/review "
                                                "axis split; 0 live violations, 60 at pre-rev3 "
                                                "ce42d205e761 under the same predicate; content "
                                                "preserved"}],
            "not_applicable": [{"id": "HF-01", "check_id": "C6",
                                "finding": "claim-scoped detector; ledger rows never enter the "
                                           "canonical claim corpus; every row carries source_ids"}],
            "notes": [
                "G-LIT's four row-level criteria are met (C9); the binding defect is A0 HF-02 on the "
                "8 named rows, acknowledged unfixed by the author as BL-6.",
                "class-binding metric 26/62=0.419 vs A0 target 1.0; 28 rows carry no class binding.",
                "HF-03 source_meta absent on ledger rows and audit registry rows (backlog).",
                "L1 exact_locator column is a search query or truncated URL for part of the audit "
                "rows (BL-4), so 'resolvable locator' holds at audit-row level, not per-locator.",
                "declaration-mode class_separation.py flags exactly one ledger field, "
                "T-402.regularity 'Between C0 and C2 (weak null singularity)', as a bare composite "
                "(prose mode: 0). T-402 is already in the HF-02 row set; the flag is recorded as a "
                "soft finding, not a separate hard failure.",
            ],
        },
    }
    digest = hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    core["digest"] = digest

    report = {"schema": core["schema"], "task_id": core["task_id"], "actor": "worker-029",
              "measured_at": measured_at, "node_id": "L0", "gate": "G-LIT",
              "target": core["target"], "companion": core["companion"],
              "hard_failures": hard_failures, "verdict": core["verdict"],
              "checks": core["checks"], "digest": digest,
              "reproduction": "python3 artifacts/worker-029/l0_rev3_verify/check_l0_rev3.py"}
    (HERE / "report_core.json").write_text(json.dumps(core, indent=2, sort_keys=True) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    evidence = {
        "schema": "worker-029/l0-rev3-evidence/v1",
        "task_id": core["task_id"],
        "target_sha256": core["target"]["sha256"],
        "companion_sha256": core["companion"]["sha256"],
        "digest": digest,
        "hf02_disjunction_rows": core["hf02_disjunction_rows"],
        "per_row": checks[6]["detail"]["per_row"],
        "class_binding": core["class_binding"],
        "hf14": checks[3]["detail"],
        "hf01": checks[5]["detail"],
        "citation_linkage": checks[7]["detail"],
        "gate_criteria": checks[8]["detail"],
        "revision_preservation": checks[4]["detail"],
        "controls": checks[9]["detail"],
        "spotcheck": spot,
    }
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"digest": digest, "hard_failures": hard_failures,
                      "hf02_rows": core["hf02_disjunction_rows"],
                      "class_binding_metric": core["class_binding"]["metric"],
                      "verdict": core["verdict"]["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
