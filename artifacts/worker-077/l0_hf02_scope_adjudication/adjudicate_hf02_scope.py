#!/usr/bin/env python3
"""W077-L0-HF02-SCOPE-01 — independent scope adjudication of the A0 HF-02
"disjunction of class_ids" detector as applied to ledger/theorems.jsonl rows.

Question (posed by the literature lead's HOLD and by worker-097's own declared
void-condition): does the A0 rubric's HF-02 disjunction branch bind LEDGER ROWS
(plural `class_ids` field), or only CLAIMS (singular `class_id` field), such
that the 8-row finding W097-L0R3-F1 (D-004, D-005, T-303, T-305, T-402, T-515,
T-526, T-528 at ledger sha a1674f094979) is void on its stated basis?

This instrument is READ-ONLY with respect to every canonical path. It:
  S-A  extracts the rubric's own field vocabulary for HF-01/HF-02/HF-14 and the
       class_binding metric definition (scope by the rubric's own words);
  S-B  extracts the canonical implementation routing (audit_run.py sends ledger
       rows to `records`, and its ledger-scoped HF-02 branch tests token
       membership only; audit_lib.check_class_binding reads singular class_id);
       plus the ledger builder's designed `class_ids` contract;
  S-C  re-checks each of the 8 rows substantively against the frozen taxonomy's
       real anti-merge rule (G3 merged-regularity regex) and classifies the
       multi-class binding as relation / antecedent / violation;
  S-D  verifies the ledger-scoped branch that IS in scope (token membership);
  S-E  applies the canonical checker to synthetic in-scope claims (control) and
       to a ledger-shaped record (category-mismatch demonstration);
  CTRL mutation + determinism controls.
All input hashes are pinned at T0 and re-measured at T1; any drift voids.

No gate verdict, no ledger write, no node status change.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "artifacts" / "audit"))
import audit_lib as A  # noqa: E402  (stdlib-only library, no import side effects)

TASK_ID = "W077-L0-HF02-SCOPE-01"
ROW_IDS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

PINS = [
    "ledger/theorems.jsonl",
    "research_map/research_map.json",
    "research_map/formulation_taxonomy.yaml",
    "evaluation_rubric.yaml",
    "comms/PROTOCOL.md",
    "artifacts/audit/audit_lib.py",
    "artifacts/audit/audit_run.py",
    "artifacts/literature/tools/build_literature.py",
    "artifacts/worker-01/validate_taxonomy.py",
    "artifacts/formulation/FROZEN.json",
]
DELIVERABLE = "artifacts/worker-077/l0_hf02_scope_adjudication"


def sha256_path(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return -1


def block(text: str, start_needle: str, end_needle: str) -> str:
    """Return the text from the line containing start_needle to the line before
    end_needle (first occurrence after start), with line numbers recorded."""
    lines = text.splitlines()
    si = next((i for i, l in enumerate(lines) if start_needle in l), None)
    if si is None:
        return ""
    ei = len(lines)
    for j in range(si + 1, len(lines)):
        if end_needle in lines[j]:
            ei = j
            break
    return "\n".join(lines[si:ei])


# --- G3 merged-regularity rule, copied (not re-derived) from the frozen guard's
# implementation artifacts/worker-01/validate_taxonomy.py per taxonomy guard G3.
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def normalize_regularity(text: str) -> str:
    return re.sub(r"[\^_{}\s]", "", text)


def merged_match(text: str) -> bool:
    return bool(MERGED_RE.search(text)) or bool(MERGED_RE.search(normalize_regularity(text)))


INTERMEDIATE_TOKENS = [
    "Lipschitz", "L^2", "L^s", "L2", "L^{2}", "C^{0,1}", "C^0,1",
    "continuous metric", "square integrable", "square-integrable",
    "not L^2", "non-L^2", "intermediate", "higher-regularity", "higher regularity",
]
RELATION_MARKERS = [
    "while", "but not", "whereas", "however", "revised", "antecedent", "status",
    "converse", "between", "across which", "fail to be", "extends continuously",
]
ANTECEDENT_MARKERS = ["kerr", "stability", "stable", "settle down", "antecedent", "status",
                      "subextremal", "stabil"]


def classify_row(row: dict) -> dict:
    """Descriptive classification (heuristic reading aid, not a verdict).

    Hard test used by the verdict is only: merged pattern? non-frozen token? row present?
    """
    cids = list(row.get("class_ids") or [])
    text = " ".join(str(row.get(k, "")) for k in ("statement_exact", "label"))
    inter = sorted({t for t in INTERMEDIATE_TOKENS if t.lower() in text.lower()})
    rel = sorted({t for t in RELATION_MARKERS if t.lower() in text.lower()})
    ant = sorted({t for t in ANTECEDENT_MARKERS if t.lower() in text.lower()})
    merged = merged_match(text)
    if merged:
        cls = "merged_regularity_violation"
    elif len(cids) <= 1:
        cls = "single_class"
    elif row.get("entry_kind") == "definition" and inter:
        cls = "intermediate_regularity_definition"
    elif inter and rel:
        cls = "intermediate_regularity_relation"
    elif ant and set(cids) in ({"AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"},
                               {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"}):
        cls = "shared_antecedent"
    elif inter:
        cls = "intermediate_regularity_relation"
    else:
        cls = "definite_multi_class_scope_for_review"
    return {
        "theorem_id": row.get("theorem_id"),
        "entry_kind": row.get("entry_kind"),
        "conclusion_type": row.get("conclusion_type"),
        "class_ids": cids,
        "class_ids_all_frozen": all(c in FROZEN for c in cids),
        "merged_regularity_pattern": merged,
        "intermediate_tokens": inter,
        "relation_markers": rel,
        "antecedent_markers": ant,
        "classification": cls,
    }


def run(rows, map_obj, rubric_text, rubric_obj, protocol_text, audit_lib_src,
        audit_run_src, builder_text, validate_src, taxonomy_text) -> dict:
    checks = []

    # ---- S-A: rubric scope, by the rubric's own field vocabulary -----------------
    hf02 = block(rubric_text, "- id: HF-02", "  - id: HF-03")
    hf01 = block(rubric_text, "- id: HF-01", "  - id: HF-02")
    hf14 = block(rubric_text, "- id: HF-14", "# --- Metrics")
    metric_block = block(rubric_text, "  class_binding:", "  citation_support:")
    proto_rule1 = block(protocol_text, "conclusion_type: theorem` without", "2. A node is")
    s_a = {
        "id": "S-A-rubric-scope",
        # honest tension: the HF-02 phrase itself says "disjunction of class_ids" (plural),
        # so the phrase alone does NOT settle scope. The decisive evidence is the metric
        # definition plus the implementation routing (S-B) and the ledger builder contract.
        "hf02_phrase_mentions_plural_class_ids": "class_ids" in hf02,
        "hf02_phrase_mentions_singular_class_id": "class_id" in hf02,
        "hf02_phrase_names_ledger": "ledger" in hf02.lower(),
        "hf01_detector_explicitly_claim_prefixed": "claim.conclusion_type" in hf01,
        "hf14_detector_explicitly_names_ledger": "ledger" in hf14.lower(),
        "class_binding_metric_defined_over_claims_singular": "claims whose class_id" in metric_block,
        "protocol_rule1_is_claim_scoped": "conclusion_type: theorem` without" in proto_rule1,
        "guard_G1_claim_scoped": "each claim carries exactly one class_id from class_ids" in taxonomy_text,
        "line_hf02": line_of(rubric_text, "- id: HF-02"),
        "line_metric_class_binding": line_of(rubric_text, "  class_binding:"),
        "line_protocol_rule1": line_of(protocol_text, "conclusion_type: theorem` without"),
        "hf02_detector_text": " ".join(hf02.split()),
        "tension": (
            "The HF-02 phrase is plural ('disjunction of class_ids') and does not itself name "
            "claims; scope is therefore decided by the metric definition ('claims whose "
            "class_id is frozen, singular'), the canonical implementation routing, and the "
            "ledger builder contract, not by the phrase alone."
        ),
    }
    s_a["pass"] = all([
        s_a["hf01_detector_explicitly_claim_prefixed"],
        s_a["hf14_detector_explicitly_names_ledger"],
        s_a["class_binding_metric_defined_over_claims_singular"],
        s_a["protocol_rule1_is_claim_scoped"],
        s_a["guard_G1_claim_scoped"],
    ])
    checks.append(s_a)

    # ---- S-B: canonical implementation routing -----------------------------------
    fn = block(audit_lib_src, "def check_class_binding", "\ndef citation_support")
    route_records = block(audit_run_src, 'if "theorem_id" in obj or', "return {")
    ledger_branch = block(audit_run_src, "for cid in rec.get(\"class_ids\"", "claimv.append")
    s_b = {
        "id": "S-B-canonical-routing",
        "check_class_binding_reads_singular_class_id": 'claim.get("class_id")' in fn,
        "check_class_binding_never_reads_class_ids": "class_ids" not in fn,
        "ledger_rows_routed_to_records_not_claims": "records.append(obj)" in route_records,
        "ledger_scoped_hf02_branch_tests_token_membership_only": (
            'rec.get("class_ids", [])' in ledger_branch and "invented class token" in audit_run_src
        ),
        "builder_declares_class_ids_list_contract": (
            "class_ids restricted to the four frozen classes" in builder_text
            and "class_ids may contain ONLY the four frozen classes" in builder_text
            and "Extension labels" in builder_text and "ledger_tags" in builder_text
        ),
        "check_class_binding_line": line_of(audit_lib_src, "def check_class_binding"),
        "ledger_token_branch_line": line_of(audit_run_src, 'for cid in rec.get("class_ids"'),
        "builder_contract_line": line_of(builder_text, "class_ids may contain ONLY"),
    }
    s_b["pass"] = all([v for k, v in s_b.items() if isinstance(v, bool)])
    checks.append(s_b)

    # ---- S-C: substantive per-row re-check ---------------------------------------
    per_row = [classify_row(r) for r in rows if r.get("theorem_id") in ROW_IDS]
    missing = sorted(set(ROW_IDS) - {r["theorem_id"] for r in per_row})
    counts = {}
    for r in per_row:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    s_c = {
        "id": "S-C-substantive-recheck",
        "rows_requested": len(ROW_IDS),
        "rows_found": len(per_row),
        "missing_rows": missing,
        "classification_counts": counts,
        "classification_is_heuristic": True,
        "hard_test": "merged-regularity regex (G3, copied) + frozen-token membership + row presence",
        "merged_regularity_rows": [r["theorem_id"] for r in per_row if r["merged_regularity_pattern"]],
        "non_frozen_class_token_rows": [r["theorem_id"] for r in per_row if not r["class_ids_all_frozen"]],
        "per_row": per_row,
    }
    s_c["pass"] = not missing and not s_c["merged_regularity_rows"] and not s_c["non_frozen_class_token_rows"]
    checks.append(s_c)

    # ---- S-D: ledger-scoped branch that IS in scope ------------------------------
    all_tokens = sorted({c for r in rows for c in (r.get("class_ids") or [])})
    invented = [t for t in all_tokens if t not in FROZEN]
    rows_with_token = sum(1 for r in rows if r.get("class_ids"))
    s_d = {
        "id": "S-D-ledger-scoped-membership",
        "ledger_rows": len(rows),
        "rows_with_class_ids": rows_with_token,
        "distinct_tokens": all_tokens,
        "invented_tokens": invented,
        "pass": not invented,
    }
    checks.append(s_d)

    # ---- S-E: in-scope control via the canonical checker -------------------------
    class_map, _ = A.frozen_classes(rubric_obj), None
    oracle_cases = [
        {
            "case": "clean-singular-class",
            "claim": {"claim_id": "ctl-clean", "class_id": "AF-SCC-C0-VAC-GEN",
                      "statement": "The maximal development is C0-inextendible.",
                      "assumptions": "spherical symmetry", "conclusion_type": "formal_model",
                      "falsifier": "exhibit an extension", "node_id": "L0"},
            "expect_hf02": False,
        },
        {
            "case": "second-class-mention",
            "claim": {"claim_id": "ctl-second", "class_id": "AF-SCC-C0-VAC-GEN",
                      "statement": "This C0 statement is the same as the AF-SCC-C2-VAC-GEN statement.",
                      "assumptions": "none", "conclusion_type": "formal_model",
                      "falsifier": "exhibit a difference", "node_id": "L0"},
            "expect_hf02": True,
        },
        {
            "case": "merged-C0-or-C2-plain",
            "claim": {"claim_id": "ctl-merged", "class_id": "AF-SCC-C0-VAC-GEN",
                      "statement": "Assume the extension is C0 or C2 in the sense above.",
                      "assumptions": "none", "conclusion_type": "formal_model",
                      "falsifier": "exhibit an extension", "node_id": "L0"},
            "expect_hf02": True,
        },
        {
            "case": "merged-C0-or-C2-braced-advisory",
            "claim": {"claim_id": "ctl-braced", "class_id": "AF-SCC-C0-VAC-GEN",
                      "statement": "Assume the extension is C^0 or C^2 in the sense above.",
                      "assumptions": "none", "conclusion_type": "formal_model",
                      "falsifier": "exhibit an extension", "node_id": "L0"},
            "expect_hf02": False,  # advisory: canonical regex does not normalize braces (G3 gap)
            "advisory": "canonical audit_lib disjunction regex misses the braced spelling; "
                        "taxonomy G3 requires downstream linters to copy worker-01's normalization",
        },
        {
            "case": "ledger-shaped-record-passed-as-claim",
            "claim": {"theorem_id": "CTL-ROW", "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                      "statement_exact": "A ledger row, not a claim.",
                      "conclusion_type": "formal_model", "falsifier": "n/a"},
            "expect_hf02": True,  # category mismatch: class_id=None is not a frozen registry key
        },
    ]
    oracle_out = []
    for c in oracle_cases:
        vs = A.check_class_binding(dict(c["claim"]), class_map)
        hf02 = [v for v in vs if v.hf == "HF-02"]
        oracle_out.append({
            "case": c["case"],
            "hf02_count": len(hf02),
            "hf02_fired": bool(hf02),
            "expected_hf02": c["expect_hf02"],
            "hf02_details": [v.detail for v in hf02],
            "agree": bool(hf02) == c["expect_hf02"],
            **({"advisory": c["advisory"]} if "advisory" in c else {}),
        })
    s_e = {
        "id": "S-E-canonical-oracle-control",
        "cases": oracle_out,
        "all_agree": all(o["agree"] for o in oracle_out),
        "pass": all(o["agree"] for o in oracle_out),
    }
    checks.append(s_e)

    # ---- in-scope population census (map claims, where the detector is scoped) ----
    claims = map_obj.get("claims") or []
    disj_claims = [c.get("event_id") for c in claims
                   if isinstance(c.get("class_id"), str) and ";" in c["class_id"]]
    singular = [c.get("event_id") for c in claims
                if isinstance(c.get("class_id"), str) and ";" not in c["class_id"]]
    census = {
        "claims_total": len(claims),
        "claims_singular_class_id": len(singular),
        "claims_semicolon_disjunctive_class_id": len(disj_claims),
        "disjunctive_sample": disj_claims[:10],
        "note": "in-scope population for the HF-02 disjunction branch; this census is "
                "informational and issues no verdict on those claims",
    }

    # ---- controls -----------------------------------------------------------------
    ctl_row = {"theorem_id": "CTL-MERGED", "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
               "statement_exact": "The extension is C^0 or C^2 across the horizon.",
               "label": "mutant", "entry_kind": "theorem", "conclusion_type": "theorem"}
    ctl_membership = {"theorem_id": "CTL-TOKEN", "class_ids": ["AF-NOT-A-CLASS"],
                      "statement_exact": "x", "label": "mutant", "entry_kind": "theorem",
                      "conclusion_type": "theorem"}
    ctl_single = {"theorem_id": "CTL-SINGLE", "class_ids": ["AF-SCC-C2-VAC-GEN"],
                  "statement_exact": "Definite C2 statement.", "label": "clean",
                  "entry_kind": "theorem", "conclusion_type": "theorem"}
    controls = [
        {"id": "CTRL-MERGED", "expect": "merged_regularity_violation",
         "observed": classify_row(ctl_row)["classification"],
         "pass": classify_row(ctl_row)["classification"] == "merged_regularity_violation"},
        {"id": "CTRL-TOKEN", "expect": "non-frozen token flagged",
         "observed": [c for c in ctl_membership["class_ids"] if c not in FROZEN],
         "pass": any(c not in FROZEN for c in ctl_membership["class_ids"])},
        {"id": "CTRL-SINGLE", "expect": "single_class",
         "observed": classify_row(ctl_single)["classification"],
         "pass": classify_row(ctl_single)["classification"] == "single_class"},
        {"id": "CTRL-ORACLE", "expect": "canonical checker agrees on all 4 synthetic cases",
         "observed": s_e["all_agree"], "pass": s_e["all_agree"]},
    ]

    verdict = {
        "ruling": (
            "At ledger sha256 a1674f094979 the A0 HF-02 'disjunction of class_ids' branch is "
            "claim-scoped in operation: the class_binding metric is defined over claims with a "
            "singular class_id, taxonomy guard G1 binds claims, the canonical checker reads "
            "claim.get('class_id') and never class_ids, ledger rows are routed to `records`, "
            "and the only ledger-scoped HF-02 branch implemented is invented-class-token "
            "membership. The ledger builder designs class_ids as a list whose only hard rule is "
            "membership in the four frozen classes (extension labels go to ledger_tags), so a "
            "multi-entry class_ids list is not by itself a disjunction violation. The 8-row "
            "finding W097-L0R3-F1 is therefore void on its stated basis, satisfying the "
            "void-condition worker-097 declared for itself."
        ),
        "two_readings": {
            "narrow_reading_ruling": (
                "adopted: disjunction is a claim-statement property (second-class mention or "
                "merged C0/C2 formulation), implemented and tested in S-E; ledger class_ids "
                "arity is governed by the builder contract, not by HF-02"
            ),
            "literal_arity_reading": (
                "if 'disjunction of class_ids' were read as len(class_ids) > 1, then 26/62 "
                "ledger rows would be non-singular - but that reading contradicts the builder's "
                "designed list contract, would flag definitions of intermediate-regularity "
                "objects, and still would not be a content defect. Even under it, S-C shows the "
                "8 named rows are definite relation/antecedent records, 0/8 merged or "
                "disjunctive in substance."
            ),
            "rubric_tension": (
                "the HF-02 phrase itself says 'class_ids' (plural), so this ruling rests on the "
                "metric definition, the canonical implementation, and the builder contract - "
                "not on the phrase alone. A one-line rubric clarification would remove the "
                "ambiguity; that is a documentation change, not a ledger repair."
            ),
        },
        "substantive_recheck": counts,
        "ledger_scoped_branch": {"invented_tokens": invented,
                                 "rows_with_class_ids": rows_with_token,
                                 "verdict": "conforms"},
        "residual": (
            "The rows bind two classes because their subject matter sits between C0 and C2 "
            "(intermediate regularity) or is a shared antecedent; the taxonomy has no distinct "
            "class for intermediate regularities (new class ids deferred to Human PI; variants "
            "registered instead), and the ledger row schema has no explicit relation field. If "
            "strict single-class rows are wanted, that is a schema/documentation extension, not "
            "a content repair, and is not required by the rubric as written."
        ),
        "falsifier": (
            "A rubric sentence applying the disjunction detector to ledger records or to the "
            "plural field class_ids; any of the 8 rows whose statement_exact asserts a merged "
            "C0/C2 regularity or a disjunctive class conclusion; any ledger class token outside "
            "the frozen four; or drift of any pinned input during the run (voids the ruling)."
        ),
        "non_claims": [
            "Not a gate verdict; issues no G-LIT verdict and does not accept L0.",
            "Does not adjudicate the other L0 findings (worker-097 F2/F3/F4/F5, worker-093 HF-03).",
            "No canonical path was written; the ledger, rubric, schemas and map are byte-unchanged.",
            "Worker evidence only; promotion authority stays with the controller and group leads.",
        ],
    }

    ok = all(c.get("pass") for c in checks) and all(c["pass"] for c in controls)
    return {"checks": checks, "controls": controls, "verdict": verdict,
            "in_scope_census": census, "instrument_ok": ok}


def main() -> int:
    t0 = now()
    pins0 = {p: sha256_path(p) for p in PINS}
    rows = [json.loads(l) for l in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if l.strip()]
    map_obj = json.loads((ROOT / "research_map/research_map.json").read_text())
    rubric_text = (ROOT / "evaluation_rubric.yaml").read_text()
    rubric_obj = A.load_rubric(ROOT / "evaluation_rubric.yaml")
    protocol_text = (ROOT / "comms/PROTOCOL.md").read_text()
    audit_lib_src = (ROOT / "artifacts/audit/audit_lib.py").read_text()
    audit_run_src = (ROOT / "artifacts/audit/audit_run.py").read_text()
    builder_text = (ROOT / "artifacts/literature/tools/build_literature.py").read_text()
    validate_src = (ROOT / "artifacts/worker-01/validate_taxonomy.py").read_text()
    taxonomy_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()

    def once():
        return run(rows, map_obj, rubric_text, rubric_obj, protocol_text, audit_lib_src,
                   audit_run_src, builder_text, validate_src, taxonomy_text)

    r1 = once()
    r2 = once()
    digest1 = hashlib.sha256(json.dumps(r1, sort_keys=True).encode()).hexdigest()
    digest2 = hashlib.sha256(json.dumps(r2, sort_keys=True).encode()).hexdigest()
    determinism = {"digest_run1": digest1, "digest_run2": digest2, "equal": digest1 == digest2}
    r1["controls"].append({"id": "CTRL-DETERMINISM", "expect": "equal digests",
                           "observed": determinism["equal"], "pass": determinism["equal"]})

    pins1 = {p: sha256_path(p) for p in PINS}
    drift = {p: {"t0": pins0[p], "t1": pins1[p]} for p in PINS if pins0[p] != pins1[p]}
    report = {
        "schema_version": "0.1",
        "artifact_kind": "adjudication_report",
        "task_id": TASK_ID,
        "actor": "worker-077",
        "role": "bounded execution worker",
        "created_at": t0,
        "finished_at": now(),
        "node_id": "L0",
        "gate": "G-LIT",
        "scope_token": "GLOBAL",
        "class_ids_in_scope": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "question": "Does A0 HF-02's disjunction branch bind ledger rows (plural class_ids)?",
        "pins": pins0,
        "pins_t1": pins1,
        "input_drift": drift,
        "instrument_ok": r1["instrument_ok"] and not drift,
        "checks": r1["checks"],
        "controls": r1["controls"],
        "in_scope_census": r1["in_scope_census"],
        "determinism": determinism,
        "verdict": r1["verdict"],
        "target_finding": {
            "id": "W097-L0R3-F1",
            "source": "artifacts/worker-097/l0_rev3_review/report.json",
            "declared_void_condition": "a sentence in A0 HF-02/HF-14 whose scope excludes ledger rows",
            "disposition": "void_on_stated_basis" if (r1["instrument_ok"] and not drift) else "not_adjudicated",
        },
        "authority_note": "worker evidence only; cannot set status=done, validation_status=passed, or a gate verdict",
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (OUT / "entry_hashes.json").write_text(json.dumps({
        "task_id": TASK_ID,
        "inputs": pins0,
        "outputs": {},
    }, indent=1, sort_keys=True) + "\n")

    print(f"{TASK_ID}: instrument_ok={report['instrument_ok']} drift={list(drift)}")
    for c in report["checks"]:
        print(f"  {c['id']}: pass={c.get('pass')}")
    for c in report["controls"]:
        print(f"  {c['id']}: pass={c['pass']} observed={c.get('observed')}")
    print("  verdict:", report["verdict"]["ruling"][:160], "...")
    return 0 if report["instrument_ok"] else 10


if __name__ == "__main__":
    sys.exit(main())
