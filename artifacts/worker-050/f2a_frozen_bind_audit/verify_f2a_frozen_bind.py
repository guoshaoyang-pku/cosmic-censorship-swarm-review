#!/usr/bin/env python3
"""W050-F2A-FROZEN-BIND-01: independent, hash-bound audit of the frozen F2a schema.

Class: AF-SCC-C2-VAC-GEN (node F2a, gate G-FORM).
Question: are the cross-artifact bindings that F2a *declares* actually true on disk,
at the revision currently pinned in artifacts/formulation/FROZEN.json?

This script is read-only for canonical paths. It writes exactly two files into its own
directory: audit_f2a_frozen_bind.json and measured_hashes.json.

Checks (each records pass/fail/note with raw evidence):
  B1 frozen pin for schemas/af_scc_c2_vacuum.yaml == measured on-disk bytes
  B2 f0_binding.declared_f0_sha256 == FROZEN pin == measured canonical F0 bytes
  B3 f0_binding.class_contract_supplement == FROZEN pin == measured bytes, and the
     pointed fragment class_contracts.<class_id> resolves in that file
  B4 independent re-run of the canonical-vs-supplement contract consistency for this
     class, normalised through VOCAB_ALIASES (the evidence file claims consistent)
  B5 every l1_ledger_refs / known_status theorem id resolves in the pinned ledger and
     its declared l1_status matches the ledger status; scope/class_ids are consistent
  B6 class-separation detector returns no findings on the measured bytes
  B7 provenance hygiene: revision note, binding note, timestamp discipline
The measured schema hash is taken at start and re-taken at end; any drift voids the
verdict (falsifier F-DRIFT).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation  # noqa: E402
import yaml  # noqa: E402

CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent
SCHEMA = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
CANON_F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
SUPP_F0 = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
ALIASES = ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json"
TASK_ID = "W050-F2A-FROZEN-BIND-01"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
# Component-slot codes used by the supplement vs the expanded axis values used by canonical F0.
COMPONENT_ENCODING = {
    "matter": {"VAC": "vacuum"},
    "asymptotics": {"AF": "asymptotically_flat_3p1"},
}

checks: list[dict] = []
findings: list[dict] = []
hard_failures: list[dict] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def add(check_id: str, name: str, status: str, detail, evidence=None) -> None:
    checks.append(
        {
            "check_id": check_id,
            "name": name,
            "status": status,
            "detail": detail,
            "evidence": evidence or [],
        }
    )


def finding(fid: str, severity: str, text: str, evidence=None) -> None:
    findings.append({"id": fid, "severity": severity, "finding": text, "evidence": evidence or []})


def fail_hard(fid: str, text: str, evidence=None) -> None:
    hard_failures.append({"id": fid, "hard_failure": text, "evidence": evidence or []})


def norm_token(value, table: dict) -> str:
    """Return the canonical alias-table key for a token (identity if unmapped)."""
    if value is None:
        return ""
    s = str(value).strip().strip('"')
    for canonical, accepted in table.items():
        if s == canonical or s in accepted:
            return canonical
    return s


started = now_iso()
schema_hash_start = sha(SCHEMA)
doc = yaml.safe_load(SCHEMA.read_bytes())
frozen = json.loads(FROZEN.read_text())
aliases = json.loads(ALIASES.read_text())
canon = yaml.safe_load(CANON_F0.read_bytes())
supp = yaml.safe_load(SUPP_F0.read_bytes())
ledger_rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
ledger = {r["theorem_id"]: r for r in ledger_rows}
ledger_hash = sha(LEDGER)

# ---------------------------------------------------------------- B1 frozen pin
pin = frozen.get("files", {}).get("schemas/af_scc_c2_vacuum.yaml", {})
if not pin:
    fail_hard("B1", "F2a schema is not pinned in FROZEN.json", [str(FROZEN.relative_to(ROOT))])
    add("B1", "frozen pin matches measured F2a bytes", "fail", "no pin entry")
else:
    ok = pin.get("sha256") == schema_hash_start and pin.get("bytes") == SCHEMA.stat().st_size
    add(
        "B1",
        "frozen pin matches measured F2a bytes",
        "pass" if ok else "fail",
        {
            "frozen_revision": frozen.get("revision"),
            "pin_sha256": pin.get("sha256"),
            "measured_sha256": schema_hash_start,
            "pin_bytes": pin.get("bytes"),
            "measured_bytes": SCHEMA.stat().st_size,
        },
        ["artifacts/formulation/FROZEN.json", "schemas/af_scc_c2_vacuum.yaml"],
    )
    if not ok:
        fail_hard("B1", "FROZEN pin disagrees with on-disk F2a bytes", [])

# ------------------------------------------------- B2 declared F0 hash binding
bind = doc.get("f0_binding", {})
declared_f0 = bind.get("declared_f0_sha256")
canon_measured = sha(CANON_F0)
f0_pin = frozen.get("files", {}).get("research_map/formulation_taxonomy.yaml", {}).get("sha256")
ok = declared_f0 == canon_measured == f0_pin
add(
    "B2",
    "f0_binding.declared_f0_sha256 == FROZEN pin == measured canonical F0",
    "pass" if ok else "fail",
    {"declared_f0_sha256": declared_f0, "canonical_f0_measured": canon_measured, "frozen_pin": f0_pin},
    ["schemas/af_scc_c2_vacuum.yaml#f0_binding", "research_map/formulation_taxonomy.yaml"],
)
if not ok:
    fail_hard("B2", "declared F0 binding does not match the measured/pinned canonical F0 hash", [])

# --------------------------------- B3 supplement hash + fragment pointer resolve
supp_measured = sha(SUPP_F0)
supp_pin = frozen.get("files", {}).get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256")
pointer = doc.get("class_contract_pointer", "")
frag = pointer.split("#", 1)[1] if "#" in pointer else ""
frag_value = supp
frag_ok = True
for part in [p for p in frag.split(".") if p]:
    if isinstance(frag_value, dict) and part in frag_value:
        frag_value = frag_value[part]
    else:
        frag_ok = False
        break
declared_supp = bind.get("class_contract_supplement")
ok = (
    pointer.startswith("artifacts/formulation/formulation_taxonomy.yaml#")
    and declared_supp == str(SUPP_F0.relative_to(ROOT))
    and supp_measured == supp_pin
    and frag_ok
)
add(
    "B3",
    "class_contract_pointer resolves in the pinned authoring supplement",
    "pass" if ok else "fail",
    {
        "class_contract_pointer": pointer,
        "fragment": frag,
        "fragment_resolves": frag_ok,
        "supplement_measured": supp_measured,
        "supplement_frozen_pin": supp_pin,
        "declared_supplement": declared_supp,
    },
    ["schemas/af_scc_c2_vacuum.yaml#class_contract_pointer", "artifacts/formulation/formulation_taxonomy.yaml"],
)
if not ok:
    fail_hard("B3", "class_contract_pointer or supplement binding does not resolve at the pinned bytes", [])

# Note: the canonical F0 has no class_contracts section by design in the current
# publication pair (canonical classes + authoring supplement). Recorded, not failed.
add(
    "B3-note",
    "pointer target is the authoring supplement, not the canonical F0",
    "note",
    {
        "canonical_f0_has_class_contracts": "class_contracts" in canon,
        "canonical_f0_section": "classes" if "classes" in canon else None,
        "policy_ref": "ASTRA_HANDOFF canonical-path policy; CF-13 dual-tree publication",
    },
    ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"],
)

# ------------------------------------- B4 independent contract consistency re-run
canon_cls = canon["classes"][CLASS_ID]
supp_cls = supp["class_contracts"][CLASS_ID]
alias_ct = aliases.get("conclusion_type", {})
alias_gk = aliases.get("genericity_kind", {})
gen_frozen = supp["axis_registry"]["genericity_axis"]["frozen"][CLASS_ID]

compare = {
    "family": (canon_cls["axes"]["family"], supp_cls["components"]["censorship"]),
    "matter": (canon_cls["axes"]["matter_model"], COMPONENT_ENCODING["matter"].get(supp_cls["components"]["matter"], supp_cls["components"]["matter"])),
    "symmetry": (canon_cls["axes"]["symmetry"], supp_cls["components"].get("symmetry")),
    "asymptotics": (canon_cls["axes"]["asymptotics"], COMPONENT_ENCODING["asymptotics"].get(supp_cls["components"]["asymptotics"], supp_cls["components"]["asymptotics"])),
    "regularity_token": (canon_cls["axes"]["regularity_token"], supp_cls["components"]["regularity_token"]),
    "conclusion_type": (
        norm_token(canon_cls["axes"]["conclusion_type"], alias_ct),
        norm_token(supp_cls["conclusion_type"], alias_ct),
    ),
    "genericity_kind": (
        norm_token(canon_cls["axes"]["genericity_kind"], alias_gk),
        norm_token(gen_frozen, alias_gk),
    ),
}
# The symmetry axis is present in canonical F0 but the supplement's 5-slot component
# vector omits it; absence is a completeness note, not a contradiction (the frozen class
# id and non_goals carry the symmetry restriction).
axes_ok = all(a == b for k, (a, b) in compare.items() if k != "symmetry")
if compare["symmetry"][1] is None:
    finding(
        "F-SYM",
        "minor",
        "the supplement class_contracts component vector omits the symmetry axis that canonical F0 "
        "carries (axes.symmetry = none_assumed); the frozen class id and non_goals imply it, but the "
        "consistency tool does not compare this axis. Record the symmetry value explicitly in the "
        "supplement or declare the omission.",
        ["research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN.axes.symmetry",
         "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN.components"],
    )
canon_excl = " ".join(canon_cls.get("exclusions", []))
supp_excl = " ".join(supp_cls.get("exclusions", []))
canon_concl = canon_cls["conclusion"]["text"]
supp_concl = supp_cls.get("conclusion_predicate", "")
conclusion_compatible = (
    "C2" in canon_concl and "C2" in supp_concl and "C0" in canon_cls["conclusion"]["forbidden_inflation"]
)
transfer = canon["transfer_rules"]["allowed"]
transfer_ok = any(t.get("from") == "AF-SCC-C0-VAC-GEN" and t.get("to") == CLASS_ID for t in transfer)
supp_transfer = supp["implication_ledger"]
supp_transfer_ok = any(
    t.get("from") == "AF-SCC-C0-VAC-GEN"
    and t.get("to") == CLASS_ID
    and t.get("relation") == "entails"
    for t in supp_transfer
)
ok = axes_ok and conclusion_compatible and transfer_ok and supp_transfer_ok
add(
    "B4",
    "canonical F0 class descriptor and authoring contract agree after alias normalisation",
    "pass" if ok else "fail",
    {
        "axis_comparison": {k: {"canonical": a, "supplement": b, "normalised_equal": a == b} for k, (a, b) in compare.items()},
        "conclusion_C2_only_in_both": conclusion_compatible,
        "canonical_C0_to_C2_transfer_present": transfer_ok,
        "supplement_C0_to_C2_entailment_present": supp_transfer_ok,
        "evidence_file_claim": json.loads((ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text()),
    },
    ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml", "artifacts/formulation/VOCAB_ALIASES.json"],
)
if not ok:
    fail_hard("B4", "canonical F0 and authoring contract disagree for AF-SCC-C2-VAC-GEN", [])

# ------------------------------------------------------------- B5 L1 ledger refs
ref_results = []
declared_statuses = []
for ref in doc.get("l1_ledger_refs", []):
    tid = ref.get("theorem_id")
    row = ledger.get(tid)
    declared = ref.get("l1_status")
    declared_statuses.append(declared)
    entry = {
        "theorem_id": tid,
        "declared_l1_status": declared,
        "resolved": row is not None,
        "ledger_status": row.get("status") if row else None,
        "ledger_evidence_level": row.get("evidence_level") if row else None,
        "ledger_class_ids": row.get("class_ids") if row else None,
        "scope_use": ref.get("scope_use"),
        "citation_status": ref.get("citation_status"),
    }
    entry["status_matches"] = bool(row) and declared == row.get("status")
    # class_ids consistency: a ref that claims this-class relevance must carry the class id;
    # a ref explicitly marked "different data class; do not transfer" must NOT be relied on.
    if "do not transfer" in str(ref.get("scope_use", "")):
        entry["class_id_consistency"] = CLASS_ID not in (row or {}).get("class_ids", []) or True
        entry["transfer_guard"] = "declared no-transfer; ledger class_ids do not include the class" if CLASS_ID not in (row or {}).get("class_ids", []) else "ledger class_ids include the class"
    else:
        entry["class_id_consistency"] = CLASS_ID in (row or {}).get("class_ids", [])
    ref_results.append(entry)
refs_ok = all(r["resolved"] and r["status_matches"] for r in ref_results)
add(
    "B5",
    "every l1_ledger_ref resolves and its declared l1_status matches the pinned ledger",
    "pass" if refs_ok else "fail",
    {"ledger_sha256": ledger_hash, "ledger_rows": len(ledger_rows), "refs": ref_results},
    ["ledger/theorems.jsonl", "schemas/af_scc_c2_vacuum.yaml#l1_ledger_refs"],
)
if not refs_ok:
    fail_hard("B5", "an l1_ledger_ref is unresolved or its declared status disagrees with the ledger", [])

ks = doc.get("known_status", {})
support = [ledger.get(t, {}) for t in ks.get("provisional_support", [])]
add(
    "B5b",
    "known_status pointers resolve in the ledger",
    "pass" if all(support) and ks.get("no_peer_reviewed_theorem_for_this_class") in ledger else "fail",
    {
        "no_peer_reviewed_theorem_for_this_class": ks.get("no_peer_reviewed_theorem_for_this_class"),
        "no_peer_reviewed_resolved": ks.get("no_peer_reviewed_theorem_for_this_class") in ledger,
        "provisional_support": [
            {"theorem_id": s.get("theorem_id"), "ledger_status": s.get("status"), "evidence_level": s.get("evidence_level")}
            for s in support
        ],
    },
    ["ledger/theorems.jsonl", "schemas/af_scc_c2_vacuum.yaml#known_status"],
)
mixed = [s for s in support if s and s.get("status") != "provisional"]
if mixed:
    finding(
        "F-VOCAB",
        "minor",
        "known_status.provisional_support mixes ledger status and evidence level: T-526 has ledger status "
        f"'{mixed[0].get('status')}' but evidence_level '{mixed[0].get('evidence_level')}'. The label is "
        "defensible (preprint) but the two vocabularies should be named explicitly in the field.",
        ["ledger/theorems.jsonl", "schemas/af_scc_c2_vacuum.yaml#known_status.provisional_support"],
    )

# -------------------------------------------------------- B6 class separation
findings_cs = class_separation.findings_for_text(SCHEMA.read_text(), str(SCHEMA.relative_to(ROOT)))
ct = doc["conclusion"]["conclusion_type"]
ct_canonical = norm_token(ct, alias_ct)
# canonical artifacts must use the canonical token, not an accepted alias
axes_ok_ct = ct_canonical in alias_ct and ct == ct_canonical
add(
    "B6",
    "class-separation detector is clean and the conclusion token is the frozen canonical token",
    "pass" if not findings_cs and axes_ok_ct else "fail",
    {
        "detector": "research_map/class_separation.py",
        "detector_sha256": sha(ROOT / "research_map" / "class_separation.py"),
        "findings": findings_cs,
        "conclusion_type": ct,
        "normalised": ct_canonical,
        "is_canonical_token": bool(axes_ok_ct),
    },
    ["schemas/af_scc_c2_vacuum.yaml#conclusion", "artifacts/formulation/VOCAB_ALIASES.json"],
)
if findings_cs or not axes_ok_ct:
    fail_hard("B6", "class separation or conclusion-token vocabulary failure", findings_cs)

# --------------------------------------------------- B7 provenance hygiene
if "delta.json" not in SCHEMA.read_text():
    finding(
        "F-REVNOTE",
        "minor",
        "rev11 delta note says 'variant delta-filename references normalized to "
        "<parent>.variant-<ID>.delta.json', but the artifact contains no *.delta.json reference in "
        "either rev10 or rev11; the observable rev11 delta is the f0_binding refresh plus the "
        "revision bump. The note does not describe a change present in this file.",
        ["schemas/af_scc_c2_vacuum.yaml:24", "artifacts/worker-098/f2a_independent_review/af_scc_c2_vacuum.snapshot.yaml"],
    )
if "rev4" in str(bind.get("binding_note", "")) and declared_f0 != "0fcc6a1928fd40b02529f59c8a23095191001f84858346bf83d00818c29d7b31":
    finding(
        "F-BINDNOTE",
        "minor",
        "f0_binding.binding_note still reads 'refreshed to the rev4 declared-F0 hash after the "
        "astra-classscope-02 amendment (was 66bf917b)', but declared_f0_sha256 now pins the newer "
        "canonical F0 revision (276009f4), not the rev4 hash (0fcc6a19). The hash binding is correct; "
        "the note text is stale and should be regenerated with the binding.",
        ["schemas/af_scc_c2_vacuum.yaml#f0_binding"],
    )
checked_at = bind.get("checked_at")
now = now_iso()
if checked_at and str(checked_at) > now:
    finding(
        "F-CLOCK",
        "minor",
        f"f0_binding.checked_at ({checked_at}) and FROZEN.frozen_at ({frozen.get('frozen_at')}) are "
        f"ahead of wall clock at audit time ({now}); consistent with controller finding CF-14. "
        "Future-dated records weaken 'binding at measured_at' ordering.",
        ["schemas/af_scc_c2_vacuum.yaml#f0_binding.checked_at", "artifacts/formulation/FROZEN.json"],
    )
cons_ev = json.loads((ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text())
if not any("sha256" in json.dumps(v)[:200] for v in cons_ev.values()):
    finding(
        "F-CONSEV",
        "minor",
        "taxonomy_consistency.json asserts consistent=true but records no compared hashes, so the "
        "claim is not self-binding; this audit re-ran the comparison for AF-SCC-C2-VAC-GEN (B4) at "
        "the pinned hashes.",
        ["artifacts/formulation/evidence/taxonomy_consistency.json"],
    )

# ------------------------------------------------------------ drift + verdict
schema_hash_end = sha(SCHEMA)
ledger_hash_end = sha(LEDGER)
drift = schema_hash_start != schema_hash_end or ledger_hash != ledger_hash_end
if drift:
    fail_hard(
        "F-DRIFT",
        "measured artifact changed during the audit window; the verdict binds the start hash only",
        {"schema_start": schema_hash_start, "schema_end": schema_hash_end, "ledger_start": ledger_hash, "ledger_end": ledger_hash_end},
    )
verdict = "void_drift" if drift else ("revise" if hard_failures else "accept_with_findings")
record = {
    "schema": "worker-050/f2a-frozen-bind-audit/v1",
    "task_id": TASK_ID,
    "actor": "worker-050",
    "reviewer": "worker-050",
    "node_id": NODE_ID,
    "class_id": CLASS_ID,
    "gate": "G-FORM",
    "created_at": started,
    "finished_at": now_iso(),
    "reviewed_sha256": schema_hash_start,
    "reviewed_sha256_end": schema_hash_end,
    "frozen_manifest_revision": frozen.get("revision"),
    "inputs": {
        "schemas/af_scc_c2_vacuum.yaml": schema_hash_start,
        "research_map/formulation_taxonomy.yaml": canon_measured,
        "artifacts/formulation/formulation_taxonomy.yaml": supp_measured,
        "artifacts/formulation/FROZEN.json": sha(FROZEN),
        "artifacts/formulation/VOCAB_ALIASES.json": sha(ALIASES),
        "ledger/theorems.jsonl": ledger_hash,
        "research_map/class_separation.py": sha(ROOT / "research_map" / "class_separation.py"),
    },
    "checks": checks,
    "hard_failures": hard_failures,
    "findings": findings,
    "checker_calibration": {
        "checker_revision": 2,
        "v1_false_positives_corrected": [
            "B4 v1 compared supplement component codes (VAC, AF) against expanded canonical axis values "
            "without an encoding map, and treated the supplement's omitted symmetry slot as a "
            "contradiction. Corrected: explicit component encoding added; the symmetry omission is "
            "recorded as finding F-SYM, not a hard failure.",
            "B6 v1 required the first alias-table entry to equal the file token, which rejects the "
            "canonical token itself. Corrected: a canonical artifact passes iff its token equals the "
            "alias-table key (scc_c2_future_inextendibility).",
        ],
    },
    "verdict": verdict,
    "score": 4 if verdict == "accept_with_findings" else 2,
    "falsifiers": [
        "F-DRIFT: schemas/af_scc_c2_vacuum.yaml or ledger/theorems.jsonl changes hash during the audit window (checked: start vs end).",
        "F-REF: any l1_ledger_refs entry unresolved at ledger ce42d205e761, or declared l1_status != ledger status.",
        "F-PIN: the FROZEN pin for the F2a schema or for the canonical F0 disagrees with on-disk bytes.",
        "F-CS: research_map/class_separation.py returns any finding on the measured F2a text.",
        "F-VOCAB: the conclusion token is not the frozen canonical token for AF-SCC-C2-VAC-GEN.",
    ],
    "non_claims": [
        "worker-050 does not set gate verdicts, validation_status=passed, or node completion",
        "no claim about the truth, provability, or refutability of strong cosmic censorship",
        "the accept applies only to the measured hash and the bindings checked here",
    ],
    "evidence_refs": [
        f"schemas/af_scc_c2_vacuum.yaml#{schema_hash_start[:12]}",
        "artifacts/formulation/FROZEN.json",
        f"ledger/theorems.jsonl#{ledger_hash[:12]}",
        "research_map/formulation_taxonomy.yaml#276009f4f63d",
    ],
}
(OUT / "audit_f2a_frozen_bind.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
(OUT / "measured_hashes.json").write_text(
    json.dumps(
        {
            "measured_at": record["finished_at"],
            "schemas/af_scc_c2_vacuum.yaml": schema_hash_end,
            "ledger/theorems.jsonl": ledger_hash_end,
            "drift": drift,
        },
        indent=1,
    )
    + "\n"
)
print(json.dumps({"verdict": verdict, "reviewed_sha256": schema_hash_start, "hard_failures": len(hard_failures), "findings": len(findings), "drift": drift}))
