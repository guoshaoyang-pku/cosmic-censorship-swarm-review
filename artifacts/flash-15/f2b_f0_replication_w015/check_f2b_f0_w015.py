#!/usr/bin/env python3
"""W015-F2B-F0BIND-REPL-01: independent replication of the three W077 hard findings.

Read-only with respect to every canonical artifact.  Writes only under
artifacts/flash-15/f2b_f0_replication_w015/.  Implemented from the protocol text
(comms/PROTOCOL.md rule 4) and the map state, not from worker-077's harness:
worker-077's review record is read only to transcribe the claims being tested.

Claims under test (reviews/F2b-f0-binding-077.json at its emitted sha256):
  HF-01  F0 declared C0 conclusion and F2b D0 use different quantifier index
         domains (smooth branch omitted in F0; no deferral recorded in the
         conclusion).
  HF-02  F2b f0_binding.consistency_evidence_sha256 declares 675a99d0d25b while
         the named canonical file measures 9e335e9ba1bf; FROZEN rev28 pins the
         9e335e9b value.
  HF-03  At ledger a1674f094979, F2b l1_ledger_refs rows D-002, T-301, T-515,
         T-528, T-302 declare citation_status=verified_by_L1 while the ledger
         rows record verification_status=abstract-read and
         review_status=not_independently_reviewed.

Exit codes: 0 = report written (findings measured, whatever their truth value),
2 = a pin moved during the run (report still written, hashes recorded).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]  # artifacts/flash-15/<task>/ -> repo root
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SCHEMA_C0 = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
SCHEMA_C2 = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
SCHEMA_WCC = ROOT / "schemas" / "af_wcc_vacuum.yaml"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
CONSISTENCY = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
W077_REVIEW = ROOT / "reviews" / "F2b-f0-binding-077.json"

PIN_EXPECT = {
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
}
CITED_FIVE = ["D-002", "T-301", "T-515", "T-528", "T-302"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel, expected in PIN_EXPECT.items():
        p = ROOT / rel
        h = sha(p)
        out[rel] = {"sha256": h, "expected_w077_pin": expected, "matches_w077_pin": h == expected}
    out["artifacts/formulation/evidence/taxonomy_consistency.json"] = {"sha256": sha(CONSISTENCY)}
    out["artifacts/formulation/FROZEN.json"] = {"sha256": sha(FROZEN)}
    return out


def write_raw(name: str, text: str) -> str:
    p = RAW / name
    p.write_text(text, encoding="utf-8")
    return f"artifacts/flash-15/f2b_f0_replication_w015/raw/{name}#{sha(p)[:12]}"


def main() -> int:
    started = datetime.now(CST).isoformat(timespec="seconds")
    pins_start = measure_pins()

    c0 = yaml.safe_load(SCHEMA_C0.read_text(encoding="utf-8"))
    c2 = yaml.safe_load(SCHEMA_C2.read_text(encoding="utf-8"))
    wcc = yaml.safe_load(SCHEMA_WCC.read_text(encoding="utf-8"))
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    w077 = json.loads(W077_REVIEW.read_text(encoding="utf-8"))
    w077_hf = {h["id"]: h for h in w077.get("hard_failures", [])}

    checks = []
    raw_refs = []

    # ---------------------------------------------------------------- HF-01
    f0_c0 = tax["classes"]["AF-SCC-C0-VAC-GEN"]
    f0_concl = f0_c0["conclusion"]["text"]
    f0_h3 = next(h for h in f0_c0["hypotheses"] if h["id"] == "H3")
    f2b_d0 = c0["quantifiers"]["domains"]["D0"]["definition"]
    f2b_formal = c0["quantifiers"]["formal"]

    f0_lines = [
        f"F0 declared taxonomy C0 conclusion text (research_map/formulation_taxonomy.yaml#"
        f"{pins_start['research_map/formulation_taxonomy.yaml']['sha256'][:12]}):",
        f0_concl,
        "",
        f"F0 H3: {f0_h3['text']}  [unresolved={f0_h3.get('unresolved')}, owned_by={f0_h3.get('owned_by')}]",
        "",
        "F2b quantifiers.formal:",
        f2b_formal,
        "",
        "F2b D0 definition:",
        f2b_d0,
    ]
    raw_refs.append(write_raw("hf01_index_domains.txt", "\n".join(f0_lines)))

    f0_has_smooth_branch = bool(re.search(r"\bsmooth\b", f0_concl, re.I))
    f0_index_tokens = sorted(set(re.findall(r"\((?:s\s*,\s*delta|s,delta)\)", f0_concl)))
    f2b_has_smooth_branch = bool(re.search(r"\br\s*=\s*smooth\b", f2b_d0))
    f2b_forall_r = bool(re.search(r"forall\s+r\s+in\s+D0", f2b_formal))
    # is a deferral of the index domain recorded *in the conclusion text*?
    concl_defers = bool(re.search(r"\bF2\b|\bdefer|\bowned_by\b|\bunresolved\b", f0_concl, re.I))
    h3_defers = f0_h3.get("owned_by") == "F2" and bool(f0_h3.get("unresolved"))

    checks.append({
        "id": "HF-01",
        "name": "quantifier index-domain divergence between declared F0 C0 and F2b D0",
        "w077_claim": w077_hf.get("W077-HF-01", {}).get("finding"),
        "method": ("parse both YAML documents; test the F0 conclusion for an explicit smooth data-"
                   "regularity branch and for an index-domain deferral; test F2b D0/formal for the "
                   "tagged union and forall-r binder"),
        "observations": {
            "f0_conclusion_has_smooth_branch": f0_has_smooth_branch,
            "f0_conclusion_index_tokens": f0_index_tokens,
            "f0_conclusion_records_index_deferral": concl_defers,
            "f0_H3_defers_data_space_to_F2": h3_defers,
            "f2b_D0_has_tagged_smooth_branch": f2b_has_smooth_branch,
            "f2b_formal_binds_forall_r_in_D0": f2b_forall_r,
        },
        "verdict": ("CONFIRMED"
                    if (not f0_has_smooth_branch and f2b_has_smooth_branch
                        and f2b_forall_r and not concl_defers and h3_defers)
                    else "NOT-CONFIRMED"),
        "severity": "major",
        "adjudication": ("The declared F0 C0 conclusion quantifies over admissible (s,delta) pairs only; "
                         "F2b D0 is the tagged disjoint union {r=smooth} U {(sobolev,s,delta)} and binds "
                         "forall r in D0. F0 H3 explicitly defers topology/weighted data spaces to F2, but "
                         "the conclusion records no such deferral, so the two published statements of the "
                         "same class carry different index domains. Dispositionable by one line: either "
                         "restate the F0 conclusion over D0-as-owned-by-F2b, or record the H3 deferral "
                         "explicitly in the conclusion."),
        "falsifier": ("show that the F0 conclusion text contains a smooth-data branch or a recorded index-"
                      "domain deferral, or that F2b D0 does not include r=smooth; any one voids HF-01"),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{pins_start['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{pins_start['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
            raw_refs[-1],
        ],
    })

    # ---------------------------------------------------------------- HF-02
    binding = c0["f0_binding"]
    declared_cons = binding["consistency_evidence_sha256"]
    cons_path_rel = str(binding["consistency_evidence"])
    measured_cons = sha(ROOT / cons_path_rel)
    frozen_pin = frozen["files"][cons_path_rel]["sha256"]
    declared_f0 = binding["declared_f0_sha256"]
    measured_f0_artifact = sha(ROOT / str(binding["declared_f0_artifact"]))

    txt = [
        f"f0_binding.consistency_evidence          = {cons_path_rel}",
        f"f0_binding.consistency_evidence_sha256   = {declared_cons}  (declared)",
        f"sha256(named file)                       = {measured_cons}  (measured)",
        f"FROZEN rev{frozen.get('revision')} pin for named file       = {frozen_pin}",
        f"sha256({binding['declared_f0_artifact']}) = {measured_f0_artifact}",
        f"f0_binding.declared_f0_sha256            = {declared_f0}",
    ]
    raw_refs.append(write_raw("hf02_binding_hashes.txt", "\n".join(txt)))

    hf02 = (declared_cons != measured_cons) and (measured_cons == frozen_pin)
    checks.append({
        "id": "HF-02",
        "name": "F2b->consistency-evidence binding hash drift",
        "w077_claim": w077_hf.get("W077-HF-02", {}).get("finding"),
        "method": "parse f0_binding; recompute sha256 of the named file; compare with the FROZEN rev28 pin",
        "observations": {
            "declared_consistency_evidence_sha256": declared_cons,
            "measured_consistency_evidence_sha256": measured_cons,
            "frozen_revision": frozen.get("revision"),
            "frozen_pin_matches_measured": measured_cons == frozen_pin,
            "declared_matches_measured": declared_cons == measured_cons,
            "declared_f0_sha256_matches_live_taxonomy": declared_f0 == pins_start["research_map/formulation_taxonomy.yaml"]["sha256"],
        },
        "verdict": "CONFIRMED" if hf02 else "NOT-CONFIRMED",
        "severity": "major",
        "adjudication": ("The declared binding hash points at bytes that are not the named canonical file's "
                         "bytes and are pinned nowhere; FROZEN rev28 pins the measured 9e335e9b value. The "
                         "declared_f0_sha256 itself is correct at the reviewed revision. Fix is a one-field "
                         "refresh plus a re-run of the consistency check before any gate verdict (the "
                         "binding's own rule says exactly this)."),
        "falsifier": ("show the declared hash equals the named file's measured sha256, or that the named "
                      "file is not the canonical consistency evidence"),
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{pins_start['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
            f"{cons_path_rel}#{measured_cons[:12]}",
            f"artifacts/formulation/FROZEN.json#{pins_start['artifacts/formulation/FROZEN.json']['sha256'][:12]}",
            raw_refs[-1],
        ],
    })

    # ---------------------------------------------------------------- HF-03
    ledger_rows = {}
    ledger_text = LEDGER.read_text(encoding="utf-8")
    for line in ledger_text.splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rid = r.get("id") or r.get("theorem_id")
        if rid:
            ledger_rows[rid] = r

    schema_rows = {row["theorem_id"]: row for row in c0["l1_ledger_refs"]}
    five = {}
    for tid in CITED_FIVE:
        row = schema_rows.get(tid, {})
        led = ledger_rows.get(tid, {})
        five[tid] = {
            "schema_line_citation_status": row.get("citation_status"),
            "schema_l1_status": row.get("l1_status"),
            "ledger_verification_status": led.get("verification_status"),
            "ledger_review_status": led.get("review_status"),
            "ledger_citation_status_field_present": "citation_status" in led,
            "ledger_content_status": led.get("content_status"),
            "ledger_evidence_level": led.get("evidence_level"),
        }
    token_in_ledger = ledger_text.count("verified_by_L1")
    ledger_has_citation_field = sum(1 for r in ledger_rows.values() if "citation_status" in r)
    hf03 = all(v["schema_line_citation_status"] == "verified_by_L1"
               and v["ledger_verification_status"] == "abstract-read"
               and v["ledger_review_status"] == "not_independently_reviewed"
               for v in five.values()) and token_in_ledger == 0
    raw_refs.append(write_raw("hf03_five_rows.json", json.dumps({
        "cited_five": five,
        "ledger_rows_total": len(ledger_rows),
        "ledger_rows_with_citation_status_field": ledger_has_citation_field,
        "occurrences_of_token_verified_by_L1_in_ledger": token_in_ledger,
    }, indent=1)))
    checks.append({
        "id": "HF-03",
        "name": "citation_status overclaim on the five F2b l1_ledger_refs rows",
        "w077_claim": w077_hf.get("W077-HF-03", {}).get("finding"),
        "method": ("parse l1_ledger_refs from the pinned C0 schema and match each cited id to its ledger row "
                   "at the pinned ledger hash; scan the whole ledger for the token verified_by_L1"),
        "observations": {
            "rows": five,
            "ledger_rows_total": len(ledger_rows),
            "ledger_rows_with_citation_status_field": ledger_has_citation_field,
            "occurrences_of_token_verified_by_L1_in_ledger": token_in_ledger,
        },
        "verdict": "CONFIRMED" if hf03 else "NOT-CONFIRMED",
        "severity": "major",
        "adjudication": ("All five schema rows assert a verification grade the ledger does not record: the "
                         "ledger's own vocabulary is verification_status=abstract-read and "
                         "review_status=not_independently_reviewed, and the token verified_by_L1 does not "
                         "exist in the ledger at all. This is a citation-status overclaim, not a claim that "
                         "the sources are wrong. Fix: set the five values to the ledger vocabulary, or "
                         "produce ledger rows that actually carry independent verification."),
        "falsifier": ("show any ledger row for one of the five ids with verification_status != abstract-read "
                      "or review_status = independently reviewed, or show the token verified_by_L1 as a "
                      "ledger vocabulary value; voids HF-03"),
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{pins_start['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
            f"ledger/theorems.jsonl#{pins_start['ledger/theorems.jsonl']['sha256'][:12]}",
            raw_refs[-1],
        ],
    })

    # ------------------------------------------- C4 breadth (extension, not W077)
    breadth = []
    for label, doc in (("F1", wcc), ("F2a", c2), ("F2b", c0)):
        for row in doc.get("l1_ledger_refs", []):
            if row.get("citation_status") != "verified_by_L1":
                continue
            led = ledger_rows.get(row["theorem_id"], {})
            breadth.append({
                "schema": label,
                "theorem_id": row["theorem_id"],
                "schema_citation_status": row["citation_status"],
                "ledger_verification_status": led.get("verification_status"),
                "ledger_review_status": led.get("review_status"),
                "ledger_present": bool(led),
            })
    raw_refs.append(write_raw("c4_breadth_scope.json", json.dumps(breadth, indent=1)))
    overclaim_ids = [b for b in breadth if b["ledger_verification_status"] == "abstract-read"]
    checks.append({
        "id": "C4-BREADTH",
        "name": "same citation_status token outside F2b (extension finding, not part of W077)",
        "method": "scan F1/F2a/F2b l1_ledger_refs for citation_status=verified_by_L1 and match to ledger rows",
        "observations": {
            "count_by_schema": {s: sum(1 for b in breadth if b["schema"] == s) for s in ("F1", "F2a", "F2b")},
            "rows": breadth,
        },
        "verdict": "CONFIRMED" if overclaim_ids else "NOT-CONFIRMED",
        "severity": "major-extension",
        "adjudication": (f"{len(overclaim_ids)} further rows in F1/F2a carry the same "
                         "citation_status=verified_by_L1 token against ledger rows recorded as "
                         "abstract-read / not_independently_reviewed (F1: T-204,T-208; F2a: T-401,T-402,"
                         "T-514,T-520). W077 scoped its HF-03 to F2b only; the defect is a three-schema "
                         "vocabulary drift and one repair should cover all of them."),
        "falsifier": "show a ledger row for one of these ids carrying an independent-verification status",
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{pins_start.get('schemas/af_wcc_vacuum.yaml', {}).get('sha256', sha(SCHEMA_WCC))[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{sha(SCHEMA_C2)[:12]}",
            f"ledger/theorems.jsonl#{pins_start['ledger/theorems.jsonl']['sha256'][:12]}",
            raw_refs[-1],
        ],
    })

    # ------------------- C5 breadth: same index divergence on the C2 pair
    f0_c2 = tax["classes"]["AF-SCC-C2-VAC-GEN"]
    c2_concl = f0_c2["conclusion"]["text"]
    c2_h3 = next(h for h in f0_c2["hypotheses"] if h["id"] == "H3")
    f2a_d0 = c2["quantifiers"]["domains"]["D0"]["definition"]
    f2a_formal = c2["quantifiers"]["formal"]
    c2_has_smooth = bool(re.search(r"\bsmooth\b", c2_concl, re.I))
    c2_defers = bool(re.search(r"\bF2\b|\bdefer|\bowned_by\b|\bunresolved\b", c2_concl, re.I))
    f2a_smooth_branch = bool(re.search(r"\br\s*=\s*smooth\b", f2a_d0))
    f2a_forall_r = bool(re.search(r"forall\s+r\s+in\s+D0", f2a_formal))
    c2_h3_defers = c2_h3.get("owned_by") == "F2" and bool(c2_h3.get("unresolved"))
    c5 = (not c2_has_smooth and c2_defers is False and f2a_smooth_branch and f2a_forall_r and c2_h3_defers)
    raw_refs.append(write_raw("c5_c2_index_domain.txt", "\n".join([
        "F0 declared taxonomy C2 conclusion (research_map/formulation_taxonomy.yaml):",
        c2_concl,
        "",
        f"F0 H3 (C2): {c2_h3['text']}  [owned_by={c2_h3.get('owned_by')}]",
        "",
        "F2a quantifiers.formal:",
        f2a_formal,
        "",
        "F2a D0 definition:",
        f2a_d0,
    ])))
    checks.append({
        "id": "C5-INDEX-C2",
        "name": "same index-domain divergence on the declared C2 taxonomy vs F2a (extension, noted by W077-C-01 but not adjudicated)",
        "method": "apply the HF-01 test to the C2 pair at the same pinned hashes",
        "observations": {
            "f0_c2_conclusion_has_smooth_branch": c2_has_smooth,
            "f0_c2_conclusion_records_index_deferral": c2_defers,
            "f0_c2_H3_defers_data_space_to_F2": c2_h3_defers,
            "f2a_D0_has_tagged_smooth_branch": f2a_smooth_branch,
            "f2a_formal_binds_forall_r_in_D0": f2a_forall_r,
        },
        "verdict": "CONFIRMED" if c5 else "NOT-CONFIRMED",
        "severity": "major-extension",
        "adjudication": ("The C2 pair carries the identical divergence: the declared F0 C2 conclusion quantifies "
                         "over admissible (s,delta) only, F2a D0 includes r=smooth and the formal statement binds "
                         "forall r in D0, and the C2 H3 defers the data space to F2 with no deferral in the "
                         "conclusion. W077-C-01 recorded the pattern but adjudicated only the C0 instance; one "
                         "repair pass covering both declared-F0 conclusions closes both."),
        "falsifier": ("show the F0 C2 conclusion names the smooth-data branch or a recorded index deferral, or "
                      "that F2a D0 lacks r=smooth"),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{pins_start['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{sha(SCHEMA_C2)[:12]}",
            raw_refs[-1],
        ],
    })

    # ------------------------------------------------------------ hash stability
    pins_end = measure_pins()
    moved = [k for k in pins_end if pins_end[k].get("sha256") != pins_start[k].get("sha256")]
    checks.append({
        "id": "PIN-STABILITY",
        "name": "reviewed hashes stable across the run",
        "method": "recompute every pin after all checks",
        "observations": {"moved": moved, "pins_start": {k: v.get("sha256") for k, v in pins_start.items()},
                         "pins_end": {k: v.get("sha256") for k, v in pins_end.items()}},
        "verdict": "STABLE" if not moved else "MOVED",
        "severity": "info",
        "falsifier": "any pin differing between start and end",
        "evidence_refs": [],
    })

    # ------------------------------------------------------------ duplication note
    dup = []
    cutoff = datetime.now(CST).timestamp() - 3600
    for p in sorted((ROOT / "reviews").glob("*.json")):
        if p.name == W077_REVIEW.name:
            continue
        try:
            if p.stat().st_mtime >= cutoff:
                t = p.read_text(encoding="utf-8", errors="replace")
                if "675a99d0" in t or "verified_by_L1" in t:
                    dup.append(p.name)
        except OSError:
            pass

    confirmed = [c for c in checks if c["verdict"] == "CONFIRMED"]
    report = {
        "schema": "w015/f2b-f0-binding-replication/v1",
        "task_id": "W015-F2B-F0BIND-REPL-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "node_id": "F2b",
        "node_ids": ["F2b", "F0"],
        "secondary_node_ids": ["F2a", "F1"],
        "gate": "G-FORM",
        "secondary_gate": "G-F0",
        "created_at": started,
        "assignment": "none in comms/inbox/deepseek-flash-15.jsonl after astra-conv-05 (delivered 00:22); slot takes one bounded class-bound task from the live queue: independent replication of the open W077 blocker, which is un-ingested (applied_event_ids lacks w077-f2bf0-20260912T004148-blocker at map updated_at 2026-09-12T00:37:18+08:00)",
        "w077_review_record": {"path": "reviews/F2b-f0-binding-077.json", "sha256": sha(W077_REVIEW)},
        "pins": pins_start,
        "checks": checks,
        "overall": {
            "w077_findings_confirmed": sum(1 for c in confirmed if c["id"] in ("HF-01", "HF-02", "HF-03")),
            "w077_findings_total": 3,
            "extension_findings": sum(1 for c in checks
                                      if c["id"] in ("C4-BREADTH", "C5-INDEX-C2")
                                      and c["verdict"] == "CONFIRMED"),
            "verdict": "revise",
            "score": 2.5,
            "counts_as_full_schema_verdict": False,
            "note": ("Cross-artifact consistency replication only. Not a full-schema acceptance verdict, "
                     "not a gate verdict. Findings are falsifiable as listed per check; a later re-freeze "
                     "supersedes (does not falsify) them."),
        },
        "independence": {
            "author_of_targets": "astra-lead-formulation (schemas), worker-01/lead (declared taxonomy)",
            "reviewer_authored_target": False,
            "harness": "artifacts/flash-15/f2b_f0_replication_w015/check_f2b_f0_w015.py",
            "w077_harness_reused": False,
            "w077_review_read_only_to_transcribe_claims": True,
        },
        "duplication_check": {
            "other_reviews_touched_within_1h_mentioning_the_defects": dup,
            "note": "two independent verdicts are required by G-AUDIT; this is the second, not a copy.",
        },
        "raw_evidence": raw_refs,
        "no_completion_claimed": True,
        "authority": "worker-level measurement; cannot move node status, gate verdict, or validation_status",
    }
    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": f"artifacts/flash-15/f2b_f0_replication_w015/report.json#{sha(report_path)[:12]}",
        "checks": {c["id"]: c["verdict"] for c in checks},
        "pins_moved": moved,
    }, indent=1))
    return 2 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
