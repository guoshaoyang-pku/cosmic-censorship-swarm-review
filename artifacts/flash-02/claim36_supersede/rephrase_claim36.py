#!/usr/bin/env python3
"""W002/F0 bounded task: author-side supersession of claims[36] (CF-16 / astra-life03-repin-claims item 3).

Measurement only. This instrument does NOT write any canonical file, does NOT move the map,
and does NOT claim a gate verdict, node status or validation_status.

What it does
------------
1. Loads `research_map/research_map.json` and locates the claim authored by `deepseek-flash-02`
   with event_id `flash02-opencase-claim-0010b-20260912T0015` (the claim audit_evidence.py
   reports as `claims[N].statement`, hard CLASSSEP, CF-16).
2. Rephrases the one clause that reproduces the composite-class token so the metalinguistic
   mention no longer parses as a composite-class assertion, and re-binds it to the post-rebind
   canonical bytes (F0 rev5 `0abb9ed8a961`, corpus `ccf7041bd0ff`).
3. Runs the LIVE detector (`research_map/class_separation.py`) and the STAGED candidate
   (`proposed/class_separation.py`, worker-085 `e2d24b927ee8`) on the old and the new claim.
4. Measures the CF-16 counterfactual: how much of the live hard count an author-side
   supersession can remove, with and without a claims-retirement policy, and whether the
   staged candidate removes the rest.
5. Fails closed on live-map drift (hash re-measured at end) and on missing evidence inputs.

Falsifier for the whole run: any check `false`, any cited input hash mismatch, or the map
sha256 changing between T0 and T1.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
MAP = ROOT / "research_map/research_map.json"
LIVE_DET = ROOT / "research_map/class_separation.py"
CAND_DET = ROOT / "proposed/class_separation.py"
OLD_EID = "flash02-opencase-claim-0010b-20260912T0015"

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0)
RUN_ID = NOW.strftime("%Y%m%dT%H%M%S")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hard_only(fs):
    # same routing as research_map/audit_evidence.py section 3
    return [f for f in fs if not str(f).startswith("CLASSSEP-SOFT:")]


def total_findings(cs, m: dict, retire_ids=frozenset(), extra_claims=()) -> list:
    """Replicates findings_for_map over a map copy; `retire_ids` simulates a claims-retirement
    policy by withholding superseded claim texts from the detector."""
    mm = dict(m)
    mm["claims"] = [c for c in m.get("claims", []) if c.get("event_id") not in retire_ids]
    mm["claims"] = list(mm["claims"]) + list(extra_claims)
    return cs.findings_for_map(mm)


def per_claim_findings(cs, m: dict) -> dict:
    out = {}
    for i, c in enumerate(m.get("claims", [])):
        f = cs.findings(c, f"claims[{i}]", mode="prose")
        if f:
            out[str(i)] = {"event_id": c.get("event_id"), "actor": c.get("actor"), "findings": f}
    return out


def synthetic_claim(statement: str) -> dict:
    return {
        "actor": "synthetic-control",
        "event_id": "synthetic-control",
        "event_type": "claim",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "conclusion_type": "stability_result",
        "statement": statement,
    }


NEW_STATEMENT = (
    "Artifact-and-checker result (not a mathematics or physics claim), re-bound to the "
    "post-rebind canonical bytes: the 9 open=true cases in schemas/taxonomy_cases.jsonl "
    "(sha256 ccf7041bd0ff) map bijectively to exactly one disposition each under the pinned "
    "taxonomy research_map/formulation_taxonomy.yaml (rev5, sha256 0abb9ed8a961) - 7 deferred "
    "new-class requests and 2 SPLIT_REQUIRED dispositions - with 0 new class ids introduced and "
    "0/9 rows matching a frozen class on recomputation. The 7 deferred requests are blocked on "
    "Human PI by class_scope_adjudication.directive=astra-classscope-02. The 2 SPLIT_REQUIRED "
    "rows TC-F0-N14 and TC-F0-N15 propose groupings that cross the frozen regularity pair and "
    "the frozen family pair respectively; each is decidable by the formulation lead now without "
    "a new class id, and neither row asserts class identity between any two frozen classes. "
    "This claim supersedes event flash02-opencase-claim-0010b-20260912T0015: the disposition "
    "matrix is unchanged, and only the binding hashes and the wording of the two metalinguistic "
    "case labels are updated."
)

NEXT_FALSIFIER = (
    "Re-run artifacts/flash-02/claim36_supersede/rephrase_claim36.py after any map movement. "
    "This supersession is VOID if (a) the rephrased statement or the emitted claim object yields "
    "any class_separation finding under the live detector; (b) the live hard total does not drop "
    "by exactly the findings attributed to retired claims once a retirement policy withholds the "
    "superseded text; (c) a reviewer shows the rephrasing changes the 9-case disposition matrix "
    "or the 7-deferred/2-SPLIT split; or (d) the cited canonical hashes (0abb9ed8a961, "
    "ccf7041bd0ff) move and are not re-pinned in a further supersession."
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, expected, observed):
        ok = expected == observed
        checks.append({"check": name, "expected": expected, "observed": observed, "pass": ok})
        return ok

    # ---- inputs
    required = [MAP, LIVE_DET, CAND_DET,
                ROOT / "artifacts/flash-02/open_case_disposition.json",
                ROOT / "artifacts/flash-02/open_case_disposition_check_report.json",
                ROOT / "artifacts/flash-02/rebind_rows_r2_report.json",
                ROOT / "schemas/taxonomy_cases.jsonl",
                ROOT / "research_map/formulation_taxonomy.yaml"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print(json.dumps({"verdict": "FAIL", "missing_inputs": missing}, indent=1))
        return 2

    map_t0 = sha256_file(MAP)
    m = json.loads(MAP.read_text())
    live = load_mod("live_classsep", LIVE_DET)
    cand = load_mod("cand_classsep", CAND_DET)

    # ---- locate the authored claim by event_id, not by index
    idxs = [i for i, c in enumerate(m.get("claims", [])) if c.get("event_id") == OLD_EID]
    if len(idxs) != 1:
        print(json.dumps({"verdict": "FAIL", "reason": f"expected exactly 1 claim with {OLD_EID}, found {idxs}"}, indent=1))
        return 2
    idx = idxs[0]
    old_claim = m["claims"][idx]
    old_stmt = old_claim.get("statement", "")

    # ---- deep-copy the claim and rephrase
    new_claim = json.loads(json.dumps(old_claim))
    new_claim["event_id"] = f"flash02-claim36supersede-claim-{RUN_ID}"
    new_claim["created_at"] = NOW.isoformat()
    new_claim["statement"] = NEW_STATEMENT
    new_claim["supersedes"] = [OLD_EID]
    new_claim["supersedes_event_id"] = OLD_EID
    new_claim["supersedes_index_at_emission"] = idx
    new_claim["falsifier"] = NEXT_FALSIFIER
    new_claim["next_falsifier"] = NEXT_FALSIFIER
    new_claim["does_not_claim"] = [
        "no mathematics or physics claim; this is an artifact-and-checker statement",
        "no change to the 9-case disposition matrix, the 7-deferred/2-SPLIT split, or any class semantics",
        "no gate verdict, no node status, and no validation_status (worker authority limit)",
        "no claim that author-side rewording alone clears CF-16; the measured counterfactual is in report.json",
    ]
    new_claim["retirement_request"] = (
        "Controller/audit-lead action (CF-16 / astra-life05-classsep-calibration), not a worker action: "
        "withhold the superseded claim event_id from class_separation.findings_for_map when scanning claims, "
        "so a retirement replaces rather than appends. This instrument measures the exact effect at the "
        "emission revision; it does not move the map."
    )
    # canonical binding update from the rebind-r2 repair (content-preserving)
    new_claim["artifact_refs"] = [
        "artifacts/flash-02/open_case_disposition.json#ee05eb8e7cde",
        "artifacts/flash-02/open_case_disposition_check_report.json#546cc707c4d2",
        "artifacts/flash-02/rebind_rows_r2_report.json#6feb810fa22d",
        "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
    ]
    new_claim["evidence_refs"] = [
        "artifacts/flash-02/open_case_disposition.json#ee05eb8e7cde",
        "artifacts/flash-02/open_case_disposition_check_report.json#546cc707c4d2",
        "artifacts/flash-02/rebind_rows_r2_report.json#6feb810fa22d",
        "artifacts/flash-02/rebind_r2_independent_check.json#26346a2a55bf",
        "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    ]
    new_claim["assumptions"] = [
        "The 9-case disposition matrix was computed at corpus b9699119 / taxonomy rev3; the rebind-r2 repair changed only binding fields and preserved row content (rebind report guards G3/G4 plus independent checks C1-C7), so the matrix carries over to corpus ccf7041bd0ff / taxonomy rev5.",
        "The corpus open=true flags are the authoritative list of undispositioned cases; the gate text's '9 taxonomy cases remain open' matches that list.",
        "A worker may propose dispositions but may not adjudicate them or create class ids (comms/PROTOCOL.md rule 5, astra-classscope-02); a worker event cannot set status=done, validation_status=passed or a gate verdict.",
        "Class separation is measured only with research_map/class_separation.py at its live sha256 c266dbceca87; proposed/class_separation.py e2d24b927ee8 is measured as a staged candidate, not adopted.",
    ]

    # ---- detector measurements
    old_f = live.findings(old_claim, f"claims[{idx}]", mode="prose")
    new_f = live.findings(new_claim, f"claims[{idx}]", mode="prose")
    old_f_cand = cand.findings(old_claim, f"claims[{idx}]", mode="prose")
    new_f_cand = cand.findings(new_claim, f"claims[{idx}]", mode="prose")

    pos_stmt = "The two surfaces are treated as one class: the C0/C2 merge is the working object."
    neg_vs_stmt = ("The two case labels 'C0 vs C2' and 'WCC vs SCC' name distinct frozen classes; "
                   "no class identity is asserted.")
    neg_guard_stmt = "This text does not assert merged C0 or C2 classes; it quotes the flagged form."
    pos_f = live.findings(synthetic_claim(pos_stmt), "synthetic[positive]", mode="prose")
    pos_f_cand = cand.findings(synthetic_claim(pos_stmt), "synthetic[positive]", mode="prose")
    neg_vs_f = live.findings(synthetic_claim(neg_vs_stmt), "synthetic[vs-form]", mode="prose")
    neg_guard_f = live.findings(synthetic_claim(neg_guard_stmt), "synthetic[negated]", mode="prose")

    live_total = live.findings_for_map(m)
    live_hard = hard_only(live_total)
    cand_hard = hard_only(cand.findings_for_map(m))
    by_claim = per_claim_findings(live, m)
    old_attributed = by_claim.get(str(idx), {}).get("findings", [])

    retire = {OLD_EID}
    after_retire = hard_only(total_findings(live, m, retire_ids=retire))
    after_retire_plus_new = hard_only(total_findings(live, m, retire_ids=retire, extra_claims=[new_claim]))
    append_only_plus_new = hard_only(total_findings(live, m, extra_claims=[new_claim]))
    cand_after_retire_plus_new = hard_only(total_findings(cand, m, retire_ids=retire, extra_claims=[new_claim]))

    check("C1_old_claim_flags_live", True, len(old_f) >= 1)
    check("C2_new_claim_clean_live", 0, len(new_f))
    check("C3_new_claim_clean_candidate", 0, len(new_f_cand))
    check("C4_old_claim_flags_candidate", True, len(old_f_cand) >= 1)
    check("C5_positive_control_flags", True, len(pos_f) >= 1 and len(pos_f_cand) >= 1)
    check("C6_vs_form_benign", 0, len(neg_vs_f))
    check("C7_negation_guard_benign", 0, len(neg_guard_f))
    check("C8_attribution_is_one_finding", 1, len(old_attributed))
    check("C9_retire_removes_exactly_attributed", len(live_hard) - len(old_attributed), len(after_retire))
    check("C10_append_only_no_reduction", len(live_hard), len(append_only_plus_new))
    check("C11_retire_plus_rephrase_stable", len(after_retire), len(after_retire_plus_new))
    check("C12_candidate_total_recorded", True, isinstance(cand_hard, list))
    check("C13_statement_changed", True, sha256_text(old_stmt) != sha256_text(NEW_STATEMENT))
    check("C14_binding_updated", True, "0abb9ed8a961" in NEW_STATEMENT and "ccf7041bd0ff" in NEW_STATEMENT)

    # ---- write frozen payloads (proposed_claim.json is the payload sans post-hoc self-refs)
    snapshot = {
        "captured_at": NOW.isoformat(),
        "map_sha256": map_t0,
        "claim_index": idx,
        "claim": old_claim,
        "attributed_findings": old_attributed,
    }
    (OUT / "snapshot_claim36.json").write_text(json.dumps(snapshot, indent=1, sort_keys=True) + "\n")
    (OUT / "proposed_claim.json").write_text(json.dumps(new_claim, indent=1, sort_keys=True) + "\n")
    proposed_sha = sha256_file(OUT / "proposed_claim.json")

    map_t1 = sha256_file(MAP)
    check("C15_map_unchanged_T0_T1", map_t0, map_t1)

    report = {
        "artifact_id": "artifacts/flash-02/claim36_supersede/report.json",
        "task": "W002-F0-CLAIM36-SUPERSEDE (astra-life03-repin-claims item 3; CF-16 author-side action)",
        "run_id": RUN_ID,
        "at": NOW.isoformat(),
        "actor": "worker-002",
        "agent_id": "deepseek-flash-02",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "authority_note": "Worker measurement only: sets no gate verdict, no node status, no validation_status; edits no canonical file.",
        "inputs": {
            "research_map/research_map.json": map_t0,
            "research_map/class_separation.py": sha256_file(LIVE_DET),
            "proposed/class_separation.py": sha256_file(CAND_DET),
            "schemas/taxonomy_cases.jsonl": sha256_file(ROOT / "schemas/taxonomy_cases.jsonl"),
            "research_map/formulation_taxonomy.yaml": sha256_file(ROOT / "research_map/formulation_taxonomy.yaml"),
            "artifacts/flash-02/open_case_disposition.json": sha256_file(ROOT / "artifacts/flash-02/open_case_disposition.json"),
            "artifacts/flash-02/open_case_disposition_check_report.json": sha256_file(ROOT / "artifacts/flash-02/open_case_disposition_check_report.json"),
            "artifacts/flash-02/rebind_rows_r2_report.json": sha256_file(ROOT / "artifacts/flash-02/rebind_rows_r2_report.json"),
        },
        "old_claim": {
            "event_id": OLD_EID,
            "index_at_emission": idx,
            "statement_sha256": sha256_text(old_stmt),
            "live_findings": old_f,
            "candidate_findings": old_f_cand,
        },
        "new_claim": {
            "event_id": new_claim["event_id"],
            "supersedes": [OLD_EID],
            "statement_sha256": sha256_text(NEW_STATEMENT),
            "live_findings": new_f,
            "candidate_findings": new_f_cand,
            "proposed_claim_sha256": proposed_sha,
        },
        "controls": {
            "positive_merge_assertion_live": pos_f,
            "positive_merge_assertion_candidate": pos_f_cand,
            "benign_vs_form": neg_vs_f,
            "negation_guarded_mention": neg_guard_f,
            "statement_texts": {
                "positive": pos_stmt, "benign_vs": neg_vs_stmt, "negation_guarded": neg_guard_stmt,
            },
        },
        "counterfactual": {
            "live_hard_total": len(live_hard),
            "candidate_hard_total": len(cand_hard),
            "candidate_clears_live": len(cand_hard) < len(live_hard),
            "findings_attributed_to_claim36": len(old_attributed),
            "findings_by_claim_index": by_claim,
            "after_retire_claim36_only": len(after_retire),
            "after_retire_plus_rephrased_claim": len(after_retire_plus_new),
            "append_only_plus_rephrased_claim": len(append_only_plus_new),
            "candidate_after_retire_plus_rephrased_claim": len(cand_after_retire_plus_new),
            "acceptance_of_astra-life03-repin-claims": (
                "NOT met by this event alone: author-side supersession removes exactly "
                f"{len(old_attributed)} of {len(live_hard)} live hard findings because the map ledger appends "
                "claims and findings_for_map scans retired text too; the remaining "
                f"{len(after_retire_plus_new)} need the CF-16 claims-retirement policy / detector calibration "
                "(astra-life05-classsep-calibration, audit lead)."
            ),
        },
        "checks": checks,
        "verdict": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "falsifier": NEXT_FALSIFIER,
        "next_falsifier": NEXT_FALSIFIER,
        "rollback": "Delete artifacts/flash-02/claim36_supersede/ and the matching outbox events; no canonical file was written.",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    report_sha = sha256_file(OUT / "report.json")

    # emitted_claim.json is the exact payload the outbox emitter appends; the two post-hoc
    # self-references are added only here, after both referenced files are frozen.
    emitted_claim = json.loads(json.dumps(new_claim))
    emitted_claim["evidence_refs"] = list(new_claim["evidence_refs"]) + [
        f"artifacts/flash-02/claim36_supersede/proposed_claim.json#{proposed_sha[:12]}",
        f"artifacts/flash-02/claim36_supersede/report.json#{report_sha[:12]}",
    ]
    (OUT / "emitted_claim.json").write_text(json.dumps(emitted_claim, indent=1, sort_keys=True) + "\n")
    emitted_sha = sha256_file(OUT / "emitted_claim.json")

    # ---- hashes for the bundle
    hlines = []
    for p in sorted(OUT.glob("*")):
        if p.name in ("SHA256SUMS",) or not p.is_file():
            continue
        hlines.append(f"{sha256_file(p)}  {p.name}")
    (OUT / "SHA256SUMS").write_text("\n".join(hlines) + "\n")

    print(json.dumps({
        "verdict": report["verdict"],
        "run_id": RUN_ID,
        "old_event_id": OLD_EID,
        "new_event_id": new_claim["event_id"],
        "live_hard_total": len(live_hard),
        "candidate_hard_total": len(cand_hard),
        "claim36_attributed": len(old_attributed),
        "after_retire": len(after_retire),
        "after_retire_plus_rephrase": len(after_retire_plus_new),
        "append_only_plus_rephrase": len(append_only_plus_new),
        "map_sha256": map_t0,
        "report_sha256": sha256_file(OUT / "report.json"),
        "emitted_claim_sha256": emitted_sha,
    }, indent=1))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
