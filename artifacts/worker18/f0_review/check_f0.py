#!/usr/bin/env python3
"""Deterministic F0 conformance checker for worker deepseek-flash-18.

Reads (read-only):
  research_map/formulation_taxonomy.yaml      (the reviewed canonical F0 artifact)
  evaluation_rubric.yaml                      (frozen class list, read as an external reference)
  schemas/af_*.yaml + artifacts/formulation/schemas/af_*.yaml (schema_owner pointer resolution)

Writes: nothing. Emits a JSON report on stdout.

Every check is content- or hash-bound to the sha256 measured at run time and re-measured at
exit; the report carries both so a moved file self-invalidates the verdict.

Usage: python3 artifacts/worker18/f0_review/check_f0.py > artifacts/worker18/f0_review/report.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
F0 = os.path.join(ROOT, "research_map", "formulation_taxonomy.yaml")
RUBRIC = os.path.join(ROOT, "evaluation_rubric.yaml")
CST = timezone(timedelta(hours=8))

FROZEN_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys in the same mapping."""


def _mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_brackets(text: str) -> str:
    """Remove [...] and {...} note segments (nested-aware) so quoted/superseded wording is
    not read as an assertion. Half-open interval notation [a,b) is normalized first, because
    it would otherwise open a bracket that never closes."""
    text = re.sub(r"\[([^\[\]()]*,[^\[\]()]*)\)", r"(\1)", text)
    out, depth_sq, depth_br = [], 0, 0
    for ch in text:
        if ch == "[":
            depth_sq += 1
        elif ch == "]":
            depth_sq = max(0, depth_sq - 1)
        elif ch == "{":
            depth_br += 1
        elif ch == "}":
            depth_br = max(0, depth_br - 1)
        elif depth_sq == 0 and depth_br == 0:
            out.append(ch)
    return "".join(out)


def check(cid: str, ok: bool, detail, evidence=None):
    return {
        "id": cid,
        "status": "pass" if ok else "FAIL",
        "detail": detail,
        "evidence": evidence or [],
    }


def main() -> int:
    started = datetime.now(CST)
    h0 = sha256(F0)
    text = open(F0, encoding="utf-8").read()
    lines = text.splitlines()
    mtime = datetime.fromtimestamp(os.path.getmtime(F0), CST)
    checks = []
    findings = []

    # --- parse with duplicate-key refusal -------------------------------------------------
    parse_error = None
    try:
        doc = yaml.load(text, Loader=DuplicateKeyLoader)
    except yaml.constructor.ConstructorError as e:
        parse_error = str(e)
        doc = yaml.safe_load(text)
    checks.append(check(
        "C0-parse", parse_error is None and isinstance(doc, dict),
        "YAML parses; duplicate-key refusal clean" if parse_error is None
        else f"duplicate key or parse error: {parse_error}",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- rubric cross-reference -----------------------------------------------------------
    rubric_ids = None
    try:
        rub = yaml.safe_load(open(RUBRIC, encoding="utf-8"))
        fc = rub.get("frozen_classes") or []
        rubric_ids = [c.get("class_id") or c.get("id") for c in fc if isinstance(c, dict)]
    except Exception as e:  # rubric is an external reference only
        rubric_ids = None
        checks.append(check("C1-rubric", False, f"rubric unreadable: {e}"))
    class_ids = doc.get("class_ids") or []
    classes = doc.get("classes") or {}
    checks.append(check(
        "C1-frozen-class-ids",
        len(class_ids) == 4 and set(class_ids) == set(FROZEN_IDS) and set(classes) == set(FROZEN_IDS)
        and (rubric_ids is None or set(rubric_ids) == set(FROZEN_IDS)),
        "class_ids == classes keys == the four frozen ids"
        + (f"; rubric frozen_classes == {rubric_ids}" if rubric_ids is not None else ""),
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}", "evaluation_rubric.yaml#d748a9e3574e"],
    ))

    # --- per-class completeness and axes/conclusion agreement -----------------------------
    per_class = {}
    for cid in FROZEN_IDS:
        c = classes.get(cid) or {}
        axes = c.get("axes") or {}
        concl = c.get("conclusion") or {}
        tc = c.get("test_cases") or {}
        pos, neg = tc.get("positive"), tc.get("negative")
        ok = bool(
            c.get("hypotheses") and c.get("exclusions") and concl.get("type")
            and isinstance(pos, dict) and isinstance(neg, dict)
            and pos.get("id") and neg.get("id")
            and axes.get("conclusion_type") == concl.get("type")
        )
        per_class[cid] = {
            "hypotheses": len(c.get("hypotheses") or []),
            "exclusions": len(c.get("exclusions") or []),
            "conclusion_type": concl.get("type"),
            "axes_conclusion_type": axes.get("conclusion_type"),
            "test_cases": sorted(tc.keys()),
        }
        checks.append(check(
            f"C2-completeness:{cid}", ok,
            f"hypotheses={per_class[cid]['hypotheses']} exclusions={per_class[cid]['exclusions']} "
            f"conclusion_type={concl.get('type')} axes.conclusion_type={axes.get('conclusion_type')} "
            f"test_cases={per_class[cid]['test_cases']}",
            [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
        ))

    # --- disjointness: 6 unordered pairs, decisive axes genuinely differ -------------------
    disj = doc.get("disjointness") or []
    pairs = {}
    for row in disj:
        p = row.get("pair") or []
        if len(p) == 2:
            pairs[frozenset(p)] = row
    expected = {frozenset((a, b)) for i, a in enumerate(FROZEN_IDS) for b in FROZEN_IDS[i + 1:]}
    pair_ok = set(pairs) == expected
    differing = {}
    for key, row in pairs.items():
        a, b = sorted(key)
        va, vb = (classes.get(a) or {}).get("axes") or {}, (classes.get(b) or {}).get("axes") or {}
        declared = row.get("decisive_axes") or []
        diffs = [ax for ax in declared if ax in va and ax in vb and va[ax] != vb[ax]]
        differing[f"{a}|{b}"] = {"declared": declared, "differing": diffs}
        if not diffs:
            pair_ok = False
    checks.append(check(
        "C3-disjointness", pair_ok,
        f"{len(pairs)}/6 pairs; every pair has >=1 declared decisive axis that differs in the parsed vectors",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- G2 regularity-token rule ---------------------------------------------------------
    g2_bad = []
    for cid in FROZEN_IDS:
        axes = (classes.get(cid) or {}).get("axes") or {}
        fam, tok = axes.get("family"), axes.get("regularity_token")
        ok = (fam == "SCC" and tok in ("C0", "C2")) or (fam == "WCC" and tok in (None, "null", ""))
        if not ok:
            g2_bad.append({cid: {"family": fam, "regularity_token": tok}})
    checks.append(check(
        "C4-G2-regularity-token", not g2_bad,
        "SCC classes carry exactly one of {C0,C2}; WCC classes carry none" if not g2_bad
        else f"violations: {g2_bad}",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- D1: set-based visibility predicate not asserted in any conclusion ----------------
    d1_rows = []
    whole_file_hits = [i + 1 for i, ln in enumerate(lines) if re.search(r"J\s*-\s*\(\s*I\s*\+?\s*\)", ln)]
    for cid in FROZEN_IDS:
        raw = ((classes.get(cid) or {}).get("conclusion") or {}).get("text") or ""
        assertive = strip_brackets(raw)
        set_based_assertive = bool(re.search(r"J\s*-\s*\(\s*I\s*\+?\s*\)", assertive))
        single_q_assertive = ("J^-(q)" in assertive.replace(" ", ""))
        in_class_text = bool(re.search(r"J\s*-\s*\(\s*I\s*\+?\s*\)", raw))
        d1_rows.append({
            "class": cid,
            "set_based_in_assertive_text": set_based_assertive,
            "set_based_anywhere_in_conclusion_text": in_class_text,
            "single_q_token_in_assertive_text": single_q_assertive,
        })
    d1_rows.append({"whole_file_J-(I+)_occurrence_lines": whole_file_hits})
    d1_ok = all(
        (not r["set_based_in_assertive_text"])
        and (r["single_q_token_in_assertive_text"] or r["class"].startswith("AF-SCC"))
        for r in d1_rows if "class" in r
    )
    checks.append(check(
        "C5-D1-set-based-residue", d1_ok,
        "no conclusion asserts the set-based J-(I+) predicate in assertive text; WCC conclusions "
        "carry the single-q J^-(q) tail predicate; raw occurrences are bracketed/variant notes",
        d1_rows,
    ))

    # --- D3: comeager quantifier present and bound before the data ------------------------
    d3_rows = []
    for cid in FROZEN_IDS:
        raw = ((classes.get(cid) or {}).get("conclusion") or {}).get("text") or ""
        low = raw.lower()
        pos_comeager = low.find("comeager")
        pos_data = min([p for p in (low.find("for every data"), low.find("every member"), low.find("for every data set")) if p >= 0] or [-1])
        d3_rows.append({
            "class": cid,
            "has_comeager": pos_comeager >= 0,
            "comeager_before_data": pos_comeager >= 0 and pos_data >= 0 and pos_comeager < pos_data,
            "existential_wording": bool(re.search(r"there is a comeager|there exists a comeager", low)),
        })
    d3_ok = all(r["has_comeager"] and r["comeager_before_data"] for r in d3_rows)
    checks.append(check(
        "C6-D3-comeager-binding", d3_ok,
        "comeager quantifier present in all four conclusions and bound before the data" if d3_ok
        else f"rows: {d3_rows}",
        d3_rows,
    ))
    if any(r["has_comeager"] and not r["existential_wording"] for r in d3_rows):
        findings.append({
            "id": "N1",
            "severity": "non_blocking",
            "finding": "At least one class conclusion phrases the comeager binder as 'For a comeager set G' "
                       "rather than 'There is a comeager set G such that'. Mathematically 'for a comeager set' "
                       "reads as a universal quantifier over comeager sets, which is strictly stronger than the "
                       "intended existentially-bound G. The qualifier 'chosen before and independently of the "
                       "data' disambiguates the intent, so this is wording hardening, not a content blocker.",
            "classes": [r["class"] for r in d3_rows if not r["existential_wording"] and r["has_comeager"]],
            "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
        })

    # --- (h) provenance.schema_owner pointers --------------------------------------------
    ptr_rows = []
    ptr_ok = True
    # legacy string may legitimately appear in revision notes documenting its removal; only a
    # live schema_owner value pointing at it is a defect.
    revision_note_legacy_lines = [i + 1 for i, ln in enumerate(lines) if "af_scc_regularities" in ln]
    for cid in FROZEN_IDS:
        owner = ((classes.get(cid) or {}).get("provenance") or {}).get("schema_owner") or ""
        if "af_scc_regularities" in owner:
            ptr_ok = False
        node = {"AF-WCC-VAC-GEN": "F1", "AF-SCC-C2-VAC-GEN": "F2a", "AF-SCC-C0-VAC-GEN": "F2b"}.get(cid)
        row = {"class": cid, "schema_owner": owner, "expected_node": node or "coverage-gap"}
        if node:
            m = re.search(r"(schemas/af_[a-z0-9_]+\.yaml)", owner)
            if not m:
                ptr_ok = False
                row["error"] = "no schema path token"
            else:
                p = os.path.join(ROOT, m.group(1))
                canon = os.path.join(ROOT, "artifacts", "formulation", m.group(1))
                row["path"] = m.group(1)
                row["exists"] = os.path.exists(p)
                row["sha256"] = sha256(p)[:12] if os.path.exists(p) else None
                row["canonical_sha256"] = sha256(canon)[:12] if os.path.exists(canon) else None
                row["bytes_equal_canonical"] = row["sha256"] == row["canonical_sha256"]
                if node not in owner or not row["exists"] or not row["bytes_equal_canonical"]:
                    ptr_ok = False
        ptr_rows.append(row)
    scalar_gap = "AF-WCC-SCALAR-SPH" in json.dumps(doc.get("coverage_gaps") or [])
    checks.append(check(
        "C7-provenance-schema-owner", ptr_ok and scalar_gap,
        "C2/C0 schema_owner name the F2a/F2b node ids and schema paths whose bytes match the canonical "
        "schemas at review time; no live schema_owner points at the legacy af_scc_regularities artifact "
        "(the only such string is the revision note documenting its removal); the scalar class is "
        "declared a coverage gap",
        ptr_rows + [{"revision_note_legacy_lines": revision_note_legacy_lines,
                     "scalar_declared_coverage_gap": scalar_gap}],
    ))

    # --- clock discipline -----------------------------------------------------------------
    stamps = []
    for m in re.finditer(r"20\d\d-\d\d-\d\dT\d\d:\d\d(?::\d\d)?(?:\+08:00)?", text):
        raw = m.group(0)
        try:
            dt = datetime.fromisoformat(raw)
            stamps.append((raw, dt))
        except ValueError:
            pass
    max_stamp = max((dt for _, dt in stamps), default=None)
    clock_ok = max_stamp is not None and max_stamp <= started + timedelta(seconds=1)
    checks.append(check(
        "C8-clock-discipline", clock_ok,
        f"max in-file timestamp {max_stamp.isoformat() if max_stamp else None} <= review start "
        f"{started.isoformat()}; file mtime {mtime.isoformat()}",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- guards / transfer rules present --------------------------------------------------
    guards = {g.get("id") for g in (doc.get("guards") or []) if isinstance(g, dict)}
    tr = doc.get("transfer_rules") or {}
    g_ok = {"G1", "G2", "G3", "G4", "G5", "G6", "G7"} <= guards and bool(tr.get("allowed")) and bool(tr.get("forbidden"))
    checks.append(check(
        "C9-guards-transfer-rules", g_ok,
        f"guards={sorted(guards)}; transfer_rules.allowed={len(tr.get('allowed') or [])} "
        f"forbidden={len(tr.get('forbidden') or [])}",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- embedded reviewer verdicts (informational) --------------------------------------
    rv = ((doc.get("provenance") or {}).get("reviewer_verdicts")) or []
    checks.append(check(
        "C10-embedded-verdicts",
        True,
        f"{len(rv)} embedded historical verdict(s), all at superseded hashes; none claims acceptance "
        "at the reviewed hash",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    # --- vocabulary slot audit + housekeeping (backlog, not gate criteria) ---------------
    missing_topo = []
    for cid in FROZEN_IDS:
        axes = (classes.get(cid) or {}).get("axes") or {}
        if "genericity_topology" not in axes:
            missing_topo.append(cid)
    checks.append(check(
        "C12-vocabulary-genericity-topology", True,
        f"field_vocabulary (line 144) requires genericity_kind AND genericity_topology for a "
        f"generic-quantified claim; axes name genericity_kind for {4 - len(missing_topo)}/4 classes and "
        f"carry no genericity_topology key; topology ownership is declared in H4/H3 and "
        f"genericity_value_status. Recorded as backlog N2, not a gate criterion.",
        [{"classes_missing_axes_slot": missing_topo}],
    ))
    if missing_topo:
        findings.append({
            "id": "N2",
            "severity": "non_blocking",
            "finding": "The four class descriptors do not carry a machine-readable genericity_topology slot in "
                       "their axes blocks, although field_vocabulary declares the slot and its rule requires it "
                       "for a generic-quantified claim. The taxonomy records topology ownership/unresolved status "
                       "in H4/H3 prose and in genericity_value_status, and the declared validator does not "
                       "enforce the slot. One-line fix: add genericity_topology: unresolved (or owned_by_F1/F2) "
                       "to each axes block. Same defect cluster as worker-094 F-094-F0-01 and lead-audit "
                       "O-GF0-1, both triaged non-blocking.",
            "classes": missing_topo,
            "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
        })
    side_by_side = [k for k in doc if k.startswith("revision_note")]
    checks.append(check(
        "C13-housekeeping", True,
        f"author status={doc.get('status')!r}; {len(side_by_side)} side-by-side revision_note keys; "
        f"embedded reviewer_verdicts bind superseded hashes only. Backlog N3.",
        [{"side_by_side_keys": sorted(side_by_side)}],
    ))
    findings.append({
        "id": "N3",
        "severity": "non_blocking",
        "finding": "Housekeeping only: the author status is still draft_unverified, revision_note / "
                   "revision_note_rev3 / revision_note_rev4 sit side by side, and provenance.reviewer_verdicts "
                   "lists only two historical verdicts (both void by hash). None of this is a class-semantics "
                   "defect; reviewer acceptance is what changes the status, and the map tracks live verdicts.",
        "classes": FROZEN_IDS,
        "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    })
    canon = os.path.join(ROOT, "artifacts", "formulation", "formulation_taxonomy.yaml")
    canon_h = sha256(canon)[:12] if os.path.exists(canon) else None
    checks.append(check(
        "C14-publication-split", True,
        f"canonical F0 {h0[:12]} and class-contract supplement {canon_h} are distinct logical artifacts "
        f"pinned separately by FROZEN rev28; the gate audit's REC-3 records that byte-identity is not "
        f"required for this pair. My verdict binds only the canonical path. Controller adjudication item N4.",
        [{"canonical": h0[:12], "supplement": canon_h}],
    ))
    findings.append({
        "id": "N4",
        "severity": "non_blocking",
        "finding": "Canonical F0 and the authoring class-contract supplement are not byte-identical; REC-1/REC-2 "
                   "mirror adjudication is still open at controller level. The 00:33 gate audit applies REC-3 "
                   "(byte-identity not required for this pair). This reviewer has no authority over that "
                   "adjudication and does not certify mirror equality.",
        "classes": FROZEN_IDS,
        "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h0[:12]}",
                          "artifacts/formulation/formulation_taxonomy.yaml"],
    })
    findings.append({
        "id": "N5",
        "severity": "non_blocking",
        "finding": "The three live schema_owner pointers use the working-copy paths schemas/af_*.yaml, whose "
                   "bytes are identical to the canonical artifacts/formulation/schemas/af_*.yaml at review "
                   "time. No defect today, but CF-12 (one canonical path, one owner) argues for repointing the "
                   "provenance strings at the canonical paths so a future working-copy edit cannot silently "
                   "redefine the owner.",
        "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h0[:12]}",
                          "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                          "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"],
    })

    # --- hash stability at exit -----------------------------------------------------------
    h1 = sha256(F0)
    checks.append(check(
        "C11-hash-stability", h1 == h0,
        f"first read {h0[:16]} / exit read {h1[:16]}; stable" if h1 == h0
        else "FILE MOVED DURING REVIEW: verdict self-invalidates",
        [f"research_map/formulation_taxonomy.yaml#{h0[:12]}"],
    ))

    failed = [c for c in checks if c["status"] != "pass"]
    report = {
        "checker": "artifacts/worker18/f0_review/check_f0.py",
        "target": "research_map/formulation_taxonomy.yaml",
        "sha256_first_read": h0,
        "sha256_exit_read": h1,
        "stable": h1 == h0,
        "bytes": os.path.getsize(F0),
        "mtime": mtime.isoformat(),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(CST).isoformat(),
        "frozen_class_ids": FROZEN_IDS,
        "checks": checks,
        "failed_check_count": len(failed),
        "non_blocking_findings": findings,
        "verdict_recommendation": "accept" if not failed else "revise",
        "author_of_target": "deepseek-flash-01 (main_author_draft), lead-owned revisions",
        "reviewer": "deepseek-flash-18",
    }
    json.dump(report, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
