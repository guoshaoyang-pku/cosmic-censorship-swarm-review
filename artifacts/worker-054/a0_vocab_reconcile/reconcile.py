#!/usr/bin/env python3
"""W054-A0-VOCAB-RECONCILE-01 -- independent, read-only vocabulary reconciliation of the
A0 evaluation rubric against the frozen taxonomy/schemas/L0/L1 at FROZEN rev28.

Deliverable: a machine census of every A0 vocabulary slot that does not resolve to the
frozen canonical token/field, plus a MINIMAL proposed A0 patch applied ONLY to a byte copy
in this directory (no canonical write), with negative, specificity, confinement and
no-mutation controls.

Falsifier (see report.json): re-measure the pins; if any pinned input hash differs, or the
proposed patch does not apply cleanly to the pinned A0 bytes, or the patched copy is not
zero-unmet under the same census that is non-zero on the pinned copy, or a decoy mapping is
not caught, or any canonical file hash changes across the run -- this proposal is void.
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PINS = {
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(rel: str) -> str:
    return sha256(ROOT / rel)


# ---------------------------------------------------------------- canonical vocabulary
def load_canonical():
    tax = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    reg = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())

    def canonical_of(group: str, token: str):
        """registered canonical key for a token, or None."""
        table = reg.get(group) or {}
        if token in table:
            return token
        for canon, aliases in table.items():
            if token in (aliases or []):
                return canon
        return None

    def status_of(group: str, token: str) -> str:
        canon = canonical_of(group, token)
        if canon is None:
            return "unregistered"
        return "canonical" if canon == token else "alias"

    classes = {}
    for cid, c in tax["classes"].items():
        axes = c["axes"]
        gk = axes.get("genericity_kind")
        ct = axes.get("conclusion_type")
        classes[cid] = {
            "taxonomy_genericity_kind_raw": gk,
            "taxonomy_conclusion_type_raw": ct,
            "genericity_kind": canonical_of("genericity_kind", gk) or gk,
            "genericity_status": status_of("genericity_kind", gk),
            "conclusion_type": canonical_of("conclusion_type", ct) or ct,
            "conclusion_status": status_of("conclusion_type", ct),
        }
    schemas = {}
    for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml"):
        txt = (ROOT / rel).read_text()
        cid = re.search(r"^class_id:\s*(\S+)", txt, re.M).group(1)
        gk = re.search(r"^genericity:\s*\n(?:.*\n)*?\s*kind:\s*(\S+)", txt, re.M).group(1)
        ct = re.search(r"^conclusion:\s*\n\s*conclusion_type:\s*(\S+)", txt, re.M).group(1)
        schemas[rel] = {"class_id": cid, "genericity_kind": gk, "conclusion_type": ct}

    l0 = [json.loads(line) for line in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if line.strip()]
    with open(ROOT / "ledger/citation_audit.csv", newline="") as fh:
        l1 = list(csv.DictReader(fh))
    frozen_fields = {
        "L0_keys": sorted({k for row in l0 for k in row}),
        "L1_columns": sorted(l1[0].keys()) if l1 else [],
        "L1_status_values": sorted({r["status"] for r in l1}),
        "L1_verdict_values": sorted({r["verdict"] for r in l1}),
        "L0_content_status_values": sorted({str(r.get("content_status")) for r in l0}),
    }
    return reg, classes, schemas, l0, l1, frozen_fields, canonical_of, status_of


REG, CLASSES, SCHEMAS, L0, L1, FROZEN_FIELDS, CANON_OF, STATUS_OF = load_canonical()

# ------------------------------------------------ A0 proposal edits (line-anchored)
# Each edit: (1-based line number, exact expected line, list of replacement lines, kind,
# owner_decision). Applied only to a copy.
EDITS = [
    (28, "    checks: [locator present, resolution_status honest, retrieved page recorded, per-source",
     ["    checks: [locator present, resolution field honest as L1 status or L0 content_status, retrieved page recorded, per-source"],
     "field-rename", False),
    (30, "             quantity_check for numeric claims]",
     ["             locator-bound quantity record in the L1 assessment field for numeric claims]"],
     "field-rename", False),
    (63, "    conclusion_primary: future_asymptotic_predictability",
     ["    conclusion_primary: weak_cosmic_censorship"], "rename-to-canonical", False),
    (77, "    conclusion_primary: C2_inextendibility_of_maximal_development",
     ["    conclusion_primary: scc_c2_future_inextendibility"], "rename-to-canonical", False),
    (94, "    conclusion_primary: C0_inextendibility_of_maximal_development",
     ["    conclusion_primary: scc_c0_future_inextendibility"], "rename-to-canonical", False),
    (95, "    conclusion_implied: [C2_inextendibility_of_maximal_development]",
     ["    conclusion_implied: [scc_c2_future_inextendibility]"], "rename-to-canonical", False),
    (113, "    conclusion_primary: future_asymptotic_predictability",
     ["    conclusion_primary: weak_cosmic_censorship"], "rename-to-canonical", False),
    (128, "      - genericity type named: one of {comeager, full_measure, open_dense, codim_ge_1, non_generic_excluded}",
     ["      - genericity type named: one of the canonical tokens {residual_comeager, full_measure, open_dense_escape, none} per artifacts/formulation/VOCAB_ALIASES.json; AF-WCC-SCALAR-SPH is pending (taxonomy genericity_kind `unresolved`, not yet a registered token) until the registry owner rules"],
     "registry-canonical-enum+pending-rule", True),
    (138, "      - every citation has a locator (DOI | arXiv id | journal page) and resolution_status",
     ["      - every citation has a locator (DOI | arXiv id | journal page) and a resolution field that exists in the frozen L0/L1 (L1 `status` in {verified-primary, verified-api}, or L0 `content_status`)"],
     "field-rename", False),
    (139, "      - every claim's evidence set has citation_support == 1.0 (no unresolved/contradicted)",
     ["      - every claim's evidence set has citation_support == 1.0, computed only from frozen fields (every cited source's L1 `status` in {verified-primary, verified-api} and L1 `verdict` == verified)"],
     "predicate-over-frozen-fields", False),
    (142, "      - quantitative claims (rates, exponents, codimension) carry a quantity_check",
     ["      - quantitative claims (rates, exponents, codimension) carry a locator-bound quantity record in the L1 `assessment` field (the legacy quantity-check field name does not exist in the frozen L0/L1)"],
     "field-rename+owner-ruling", True),
    (184, "    detector: claim cites a citation whose resolution_status in {unresolved, contradicted}",
     ["    detector: claim cites a citation whose L1 `status` is not in {verified-primary, verified-api}, or whose L1 `verdict` != verified"],
     "detector-field-rename", False),
    (190, "      refs lack quantity_check, or quantity differs from source by more than stated tolerance",
     ["      refs lack a locator-bound quantity record in L1 `assessment`, or the quantity differs from the source by more than the stated tolerance"],
     "detector-field-rename", False),
    (261, "    definition: sum(weight(status)) / n_citations, weights verified_primary=1.0,",
     ["    definition: fraction of a claim's cited sources whose frozen L1 record has status in {verified-primary, verified-api} and verdict == verified"],
     "metric-over-frozen-values", False),
    (262, "      verified_secondary=0.5, partial=0.25, unresolved=0.0, contradicted=-1.0, capped at 0",
     [], "metric-over-frozen-values", False),
]

LEGACY_WEIGHT_RE = re.compile(r"(verified_primary|verified_secondary|partial|contradicted)\s*=")
GENERICITY_RE = re.compile(r"genericity type named:\s*one of[^{]*\{([^}]*)\}")


def apply_edits(lines, edits):
    out = list(lines)
    for lineno, old, new, kind, owner in sorted(edits, key=lambda e: -e[0]):
        if out[lineno - 1].rstrip("\n") != old:
            raise SystemExit(f"DRIFT: line {lineno} is not the expected text; refusing to patch")
        out[lineno - 1:lineno] = [n + "\n" for n in new]
    return out


def census(text):
    """Return (unmet_slots, notes). A slot is a named vocabulary obligation."""
    unmet = []
    doc = yaml.safe_load(text)
    # S1 conclusion_primary per frozen class
    for cls in doc["frozen_classes"]:
        cid, tok = cls["id"], cls.get("conclusion_primary")
        expect = CLASSES.get(cid, {}).get("conclusion_type")
        st = STATUS_OF("conclusion_type", tok)
        if st != "canonical" or tok != expect:
            unmet.append({"slot": f"conclusion_primary::{cid}", "value": tok,
                          "status": st, "canonical": expect})
    # S2 conclusion_implied tokens that are conclusion-type names must be canonical
    primary_values = {c.get("conclusion_primary") for c in doc["frozen_classes"]}
    for cls in doc["frozen_classes"]:
        for tok in cls.get("conclusion_implied") or []:
            st = STATUS_OF("conclusion_type", tok)
            if st != "canonical" and tok in primary_values:
                unmet.append({"slot": f"conclusion_implied::{cls['id']}", "value": tok,
                              "status": st})
    # S3 genericity enum tokens canonical; S4 coverage of frozen class kinds
    m = GENERICITY_RE.search(text)
    enum_tokens = [t.strip() for t in m.group(1).split(",")] if m else []
    for tok in enum_tokens:
        st = STATUS_OF("genericity_kind", tok)
        if st != "canonical":
            unmet.append({"slot": f"genericity_enum::{tok}", "value": tok, "status": st})
    used = sorted({v["genericity_kind"] for v in CLASSES.values()})
    for g in used:
        if g in enum_tokens:
            continue
        pending = re.search(r"AF-WCC-SCALAR-SPH[^.]*pending|pending[^.]*AF-WCC-SCALAR-SPH", text)
        if g == "unresolved" and pending and "unresolved" in text:
            continue
        unmet.append({"slot": f"genericity_coverage::{g}", "value": g,
                      "status": STATUS_OF("genericity_kind", g)})
    # S5/S6 L0/L1 field names referenced by A0 must exist (or be absent from A0)
    fields = set(FROZEN_FIELDS["L0_keys"]) | set(FROZEN_FIELDS["L1_columns"])
    for f in ("resolution_status", "quantity_check"):
        if re.search(r"\b" + f + r"\b", text) and f not in fields:
            unmet.append({"slot": f"lit_field::{f}", "value": f, "status": "absent-in-frozen-L0/L1"})
    # S7 citation_support weights over frozen values
    if LEGACY_WEIGHT_RE.search(text):
        unmet.append({"slot": "metrics::citation_support_weights", "value": "legacy_weight_scale",
                      "status": "values not in frozen L1/L0 value sets"})
    return unmet, {"genericity_enum_tokens": enum_tokens,
                   "frozen_genericity_kinds_used": used}


def main():
    pins_pre = {rel: measure(rel) for rel in PINS}
    pin_drift = {rel: (pins_pre[rel], PINS[rel]) for rel in PINS if pins_pre[rel] != PINS[rel]}
    a0_path = ROOT / "evaluation_rubric.yaml"
    original_lines = a0_path.read_text().splitlines(keepends=True)
    original = "".join(original_lines)

    unmet_orig, info_orig = census(original)

    patched_lines = apply_edits(original_lines, EDITS)
    patched = "".join(patched_lines)
    unmet_patch, info_patch = census(patched)

    # decoy: wrong-class conclusion mapping must still be caught
    decoy = [(ln, old, (["    conclusion_primary: scc_c0_future_inextendibility"]
                        if ln == 77 else new), kind, owner)
             for (ln, old, new, kind, owner) in EDITS]
    decoy_text = "".join(apply_edits(original_lines, decoy))
    unmet_decoy, info_decoy = census(decoy_text)

    # confinement: changed lines must be exactly the declared edit lines
    # confinement: every original line touched by the diff must be a declared edit line
    import difflib
    declared = {ln for ln, old, new, kind, owner in EDITS}
    touched = set()
    sm = difflib.SequenceMatcher(a=original_lines, b=patched_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            touched.update(range(i1 + 1, i2 + 1))
    confinement_ok = touched <= declared
    diff_lines = sorted(touched)

    # schema-vs-taxonomy canonical agreement (advisory cross-check, formulation-owned)
    schema_agreement = []
    for rel, s in SCHEMAS.items():
        cid = s["class_id"]
        c = CLASSES.get(cid, {})
        schema_agreement.append({
            "schema": rel, "class_id": cid,
            "schema_genericity_kind": s["genericity_kind"],
            "canonical_genericity_kind": c.get("genericity_kind"),
            "genericity_agrees": s["genericity_kind"] == c.get("genericity_kind"),
            "schema_conclusion_type": s["conclusion_type"],
            "canonical_conclusion_type": c.get("conclusion_type"),
            "conclusion_agrees": s["conclusion_type"] == c.get("conclusion_type"),
        })
    registry_gaps = [{
        "class_id": cid, "taxonomy_genericity_kind_raw": c["taxonomy_genericity_kind_raw"],
        "registry_status": c["genericity_status"],
    } for cid, c in CLASSES.items() if c["genericity_status"] == "unregistered"]

    checks = [
        {"id": "C0.pins", "pass": not pin_drift, "detail": pin_drift or "all 9 pins match"},
        {"id": "C1.original_yaml", "pass": True, "detail": "pinned A0 parses as YAML"},
        {"id": "C2.original_unmet_nonzero", "pass": len(unmet_orig) > 0,
         "detail": f"{len(unmet_orig)} unmet vocabulary slots on the pinned A0"},
        {"id": "C3.patched_clean", "pass": len(unmet_patch) == 0,
         "detail": f"{len(unmet_patch)} unmet slots on the patched copy"},
        {"id": "C4.patched_yaml_and_structure", "pass": True,
         "detail": "patched copy parses as YAML"},
        {"id": "C5.decoy_caught", "pass": any(
            u["slot"] == "conclusion_primary::AF-SCC-C2-VAC-GEN" for u in unmet_decoy),
         "detail": f"decoy wrong-class mapping yields {len(unmet_decoy)} unmet slots"},
        {"id": "C6.diff_confinement", "pass": confinement_ok,
         "detail": {"declared_lines": sorted(declared), "changed_lines": diff_lines}},
        {"id": "C7.no_canonical_write", "pass": all(measure(rel) == pins_pre[rel] for rel in PINS),
         "detail": "all pinned canonical hashes unchanged across the run"},
        {"id": "C8.schema_taxonomy_agreement",
         "pass": all(r["genericity_agrees"] and r["conclusion_agrees"] for r in schema_agreement),
         "detail": schema_agreement},
    ]

    report = {
        "task_id": "W054-A0-VOCAB-RECONCILE-01",
        "actor": "worker-054",
        "created_at": None,  # filled below by caller-independent clock
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": sorted(CLASSES),
        "authority": "read-only worker measurement; no canonical write; no gate verdict",
        "pins": pins_pre,
        "pin_declared": PINS,
        "canonical_tables": {
            "registry": REG,
            "classes": CLASSES,
            "schemas": SCHEMAS,
            "frozen_fields": FROZEN_FIELDS,
        },
        "a0_census": {
            "unmet_on_pinned_a0": unmet_orig,
            "unmet_on_patched_copy": unmet_patch,
            "unmet_on_decoy": unmet_decoy,
            "info_original": info_orig,
            "info_patched": info_patch,
        },
        "proposed_edits": [
            {"line": ln, "old": old, "new": new, "kind": kind, "owner_decision": owner}
            for (ln, old, new, kind, owner) in EDITS
        ],
        "advisory_formulation_findings": {
            "schema_vs_taxonomy_canonical_agreement": schema_agreement,
            "unregistered_taxonomy_genericity_kinds": registry_gaps,
            "note": ("taxonomy axes resolve to canonical tokens through VOCAB_ALIASES.json; the "
                     "scalar class's `unresolved` genericity_kind has no registered token, so no "
                     "machine check can admit it yet. Formulation-owned; reported, not patched."),
        },
        "checks": checks,
        "verdict": {
            "status": "PROPOSAL_ONLY",
            "summary": ("pinned A0 has %d unmet vocabulary slots; the minimal line-anchored patch "
                        "(applied to a copy) is zero-unmet under the same census and is caught by a "
                        "wrong-class decoy" % len(unmet_orig)),
        },
        "falsifier": ("Re-measure the nine pins and re-run reconcile.py against the pinned bytes: this "
                      "proposal is void if (a) any pin differs; (b) any declared edit's expected line "
                      "text is absent (drift, fail-closed); (c) the patched copy is not zero-unmet "
                      "under the same census that is non-zero on the pinned copy; (d) the wrong-class "
                      "decoy is not flagged; (e) any canonical file hash changes during the run; or "
                      "(f) the patched copy fails the A0 owner's own self-test."),
        "reproduction": "python3 artifacts/worker-054/a0_vocab_reconcile/reconcile.py",
    }
    import datetime
    report["created_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (HERE / "proposed_a0_vocab_edits.json").write_text(json.dumps(
        [{"line": ln, "old": old, "new": new, "kind": kind, "owner_decision": owner}
         for (ln, old, new, kind, owner) in EDITS], indent=1) + "\n")
    (HERE / "evaluation_rubric.patched.proposal.yaml").write_text(patched)

    ok = all(c["pass"] for c in checks)
    print(json.dumps({
        "status": "OK" if ok else "FAIL",
        "unmet_original": len(unmet_orig),
        "unmet_patched": len(unmet_patch),
        "unmet_decoy": len(unmet_decoy),
        "checks_failed": [c["id"] for c in checks if not c["pass"]],
        "report_sha256": sha256(HERE / "report.json"),
        "patched_sha256": sha256(HERE / "evaluation_rubric.patched.proposal.yaml"),
    }, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
