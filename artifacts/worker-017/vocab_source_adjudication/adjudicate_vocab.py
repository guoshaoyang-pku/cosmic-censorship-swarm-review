#!/usr/bin/env python3
"""W017-VOCAB-SOURCE-01: independent adjudication of the conclusion_type / genericity_kind
vocabulary-source conflict that blocks G-FORM accepts for F2a and F2b.

Class-bound: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN.

What it does (all deterministic, from byte snapshots taken at run entry):
  1. Census of every vocabulary source that governs `conclusion.conclusion_type` and
     `genericity.kind`, with exact paths, line refs and sha256.
  2. Gate experiments with an independent driver around the FROZEN structural gate
     (artifacts/formulation/tools/check_class_schema.py): canonical bytes + controls that
     substitute the F0 field_vocabulary literals and a wrong-class token.
  3. Repair-direction consequences:
       D-A zero artifact churn (single-sourcing ruling),
       D-B F0 taxonomy aligned to the frozen rule_spec vocabulary (staged sandbox run of the
           frozen consistency checker; new F0 hash and verdict-voiding census),
       D-C schema retokenisation to the F0 field_vocabulary literals (gate experiment shows
           whether the frozen gate accepts it).
  4. report.json + README.md; nothing outside artifacts/worker-017/ is written.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repo root: .../ai4math-swarm
SNAP = HERE / "snapshots"
CTRL = HERE / "controls"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CONSISTENCY_TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"

CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SCHEMA_SNAP = {
    "AF-WCC-VAC-GEN": SNAP / "schemas_af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": SNAP / "schemas_af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": SNAP / "schemas_af_scc_c0_vacuum.yaml",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def line_of(path: Path, needle: str) -> int | None:
    for i, ln in enumerate(path.read_text().splitlines(), 1):
        if needle in ln:
            return i
    return None


def run_gate(path: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(GATE), "--json", str(path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    try:
        d = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        d = {"verdict": f"crash(exit{r.returncode})", "failed_rules": [], "stdout": r.stdout[-400:], "stderr": r.stderr[-400:]}
    d["exit_code"] = r.returncode
    return d


def mutate(new_name: str, src: Path, repls: list[tuple[str, str]]) -> dict:
    """Copy src to controls/new_name and apply literal line replacements, recording each."""
    CTRL.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    applied = []
    for old, new in repls:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"control {new_name}: pattern {old!r} occurs {n} times, refusing")
        text = text.replace(old, new)
        applied.append({"old": old, "new": new})
    out = CTRL / new_name
    out.write_bytes(text.encode())
    return {"path": str(out.relative_to(ROOT)), "sha256": sha(out), "replacements": applied}


def sandbox_consistency(f0_text: str) -> dict:
    """Run the FROZEN consistency checker in a sandbox with a modified F0 taxonomy.

    Layout mirrors the repo so the tool's ROOT=parents[3] resolves inside the sandbox.
    """
    sb = HERE / "sandbox_d_b"
    for sub in ("research_map", "artifacts/formulation/tools", "artifacts/formulation/evidence"):
        (sb / sub).mkdir(parents=True, exist_ok=True)
    (sb / "research_map/formulation_taxonomy.yaml").write_text(f0_text)
    (sb / "artifacts/formulation/formulation_taxonomy.yaml").write_bytes(
        (SNAP / "artifacts_formulation_formulation_taxonomy.yaml").read_bytes()
    )
    (sb / "artifacts/formulation/VOCAB_ALIASES.json").write_bytes((SNAP / "artifacts_formulation_VOCAB_ALIASES.json").read_bytes())
    (sb / "artifacts/formulation/tools/check_taxonomy_consistency.py").write_bytes(CONSISTENCY_TOOL.read_bytes())
    r = subprocess.run(
        [sys.executable, str(sb / "artifacts/formulation/tools/check_taxonomy_consistency.py")],
        capture_output=True, text=True, cwd=str(sb),
    )
    ev = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"
    return {
        "exit_code": r.returncode,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip()[-300:],
        "evidence_sha256": sha(ev) if ev.exists() else None,
        "new_f0_sha256": sha_bytes(f0_text.encode()),
    }


def main() -> dict:
    import yaml

    A = yaml.safe_load((SNAP / "research_map_formulation_taxonomy.yaml").read_text())
    R = json.loads((SNAP / "artifacts_formulation_rule_spec.json").read_text())
    V = json.loads((SNAP / "artifacts_formulation_VOCAB_ALIASES.json").read_text())
    S = {cid: yaml.safe_load(p.read_text()) for cid, p in SCHEMA_SNAP.items()}
    SUP = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())

    f0_line = {ax: line_of(SNAP / "research_map_formulation_taxonomy.yaml", f"{ax}:") for ax in ("conclusion_type", "genericity_kind")}
    conc_lines = {cid: line_of(p, "  conclusion_type:") for cid, p in SCHEMA_SNAP.items()}
    gen_line = line_of(SCHEMA_SNAP["AF-SCC-C2-VAC-GEN"], "  kind: residual_comeager")

    sources = {
        "S1_f0_field_vocabulary": {
            "path": "research_map/formulation_taxonomy.yaml",
            "sha256": sha(SNAP / "research_map_formulation_taxonomy.yaml"),
            "conclusion_type_allowed": A["field_vocabulary"]["conclusion_type"]["allowed"],
            "genericity_kind_allowed": A["field_vocabulary"]["genericity_kind"]["allowed"],
            "line_hint": {"conclusion_type_allowed": line_of(SNAP / "research_map_formulation_taxonomy.yaml", "conclusion_type:")},
        },
        "S2_f0_class_axes": {
            cid: {
                "conclusion_type": A["classes"][cid]["axes"].get("conclusion_type"),
                "genericity_kind": A["classes"][cid]["axes"].get("genericity_kind"),
            } for cid in A["classes"]
        },
        "S3_rule_spec_frozen_binding": {
            "path": "artifacts/formulation/rule_spec.json",
            "sha256": sha(SNAP / "artifacts_formulation_rule_spec.json"),
            "spec_version": R.get("spec_version"),
            "class_conclusion_type": R["vocabularies"]["class_conclusion_type"],
            "genericity_kind": R["vocabularies"]["genericity_kind"],
            "rule_R11": next((r for r in R["rules"] if r.get("id") == "R11"), None),
        },
        "S4_alias_policy": {
            "path": "artifacts/formulation/VOCAB_ALIASES.json",
            "sha256": sha(SNAP / "artifacts_formulation_VOCAB_ALIASES.json"),
            "policy": V["policy"],
            "conclusion_type": V["conclusion_type"],
            "genericity_kind": V["genericity_kind"],
        },
        "S5_canonical_schemas": {
            cid: {
                "path": f"schemas/{'af_wcc_vacuum' if cid=='AF-WCC-VAC-GEN' else 'af_scc_c2_vacuum' if cid=='AF-SCC-C2-VAC-GEN' else 'af_scc_c0_vacuum'}.yaml",
                "sha256": sha(p),
                "conclusion_type": S[cid]["conclusion"]["conclusion_type"],
                "conclusion_type_line": conc_lines[cid],
                "genericity_kind": S[cid]["genericity"]["kind"],
                "genericity_kind_line": line_of(p, f"  kind: {S[cid]['genericity']['kind']}"),
            } for cid, p in SCHEMA_SNAP.items()
        },
        "S6_gate_rule": {
            "path": "artifacts/formulation/tools/check_class_schema.py",
            "sha256": sha(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
            "line_44": "CONC = SPEC_D[\"vocabularies\"][\"class_conclusion_type\"]",
            "line_300_301": "if c.get(\"conclusion_type\") != CONC[cid]: self.fail(\"R11\", ...)",
            "comparison": "literal equality, no alias resolution",
        },
        "S7_taxonomy_consistency_checker": {
            "path": "artifacts/formulation/tools/check_taxonomy_consistency.py",
            "sha256": sha(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"),
            "lines_11_14": "canon(kind, tok): for c, al in AL[kind].items(): if tok == c or tok in al: return c",
            "direction": "canon() returns the ALIAS-MAP KEY, i.e. scc_c2_/scc_c0_future_inextendibility and residual_comeager; the frozen cross-check therefore treats the schemas' tokens as the canonical form",
        },
    }

    def classify_conclusion(tok: str) -> dict:
        keys = set(V["conclusion_type"].keys())
        aliases = {a for al in V["conclusion_type"].values() for a in al}
        return {
            "token": tok,
            "in_f0_allowed_literal": tok in A["field_vocabulary"]["conclusion_type"]["allowed"],
            "is_alias_policy_canonical_key": tok in keys,
            "is_alias_policy_alias_value": tok in aliases,
            "in_rule_spec_class_conclusion_type_values": tok in set(R["vocabularies"]["class_conclusion_type"].values()),
        }

    census = {cid: classify_conclusion(S[cid]["conclusion"]["conclusion_type"]) for cid in CLASSES}
    census_genericity = {}
    for cid in CLASSES:
        tok = S[cid]["genericity"]["kind"]
        keys = set(V["genericity_kind"].keys())
        aliases = {a for al in V["genericity_kind"].values() for a in al}
        census_genericity[cid] = {
            "token": tok,
            "in_f0_allowed_literal": tok in A["field_vocabulary"]["genericity_kind"]["allowed"],
            "is_alias_policy_canonical_key": tok in keys,
            "is_alias_policy_alias_value": tok in aliases,
            "in_rule_spec_genericity_kind": tok in set(R["vocabularies"]["genericity_kind"]),
        }

    # ---- gate experiments -------------------------------------------------------------
    experiments = []
    for cid, p in SCHEMA_SNAP.items():
        g = run_gate(p)
        experiments.append({"id": f"CANON-{cid}", "kind": "canonical", "path": str(p.relative_to(ROOT)),
                            "sha256": sha(p), "verdict": g.get("verdict"), "failed_rules": g.get("failed_rules"), "exit_code": g.get("exit_code")})

    m_f2a_alias = mutate("f2a__f0_literal_token.yaml", SCHEMA_SNAP["AF-SCC-C2-VAC-GEN"], [
        ("  conclusion_type: scc_c2_future_inextendibility", "  conclusion_type: strong_cosmic_censorship_C2")])
    g = run_gate(ROOT / m_f2a_alias["path"])
    experiments.append({"id": "CTRL-F2a-f0literal", "kind": "control", "mutant": m_f2a_alias,
                        "why": "substitute the literal token that S1 field_vocabulary.allowed names",
                        "verdict": g.get("verdict"), "failed_rules": g.get("failed_rules"), "exit_code": g.get("exit_code")})

    m_f2a_wrong = mutate("f2a__wrong_class_token.yaml", SCHEMA_SNAP["AF-SCC-C2-VAC-GEN"], [
        ("  conclusion_type: scc_c2_future_inextendibility", "  conclusion_type: scc_c0_future_inextendibility")])
    g = run_gate(ROOT / m_f2a_wrong["path"])
    experiments.append({"id": "CTRL-F2a-wrongclass", "kind": "control", "mutant": m_f2a_wrong,
                        "why": "same-family wrong regularity token; proves R11 is not family-only",
                        "verdict": g.get("verdict"), "failed_rules": g.get("failed_rules"), "exit_code": g.get("exit_code")})

    m_f2a_gen = mutate("f2a__f0_genericity_token.yaml", SCHEMA_SNAP["AF-SCC-C2-VAC-GEN"], [
        ("  kind: residual_comeager", "  kind: provisional_baire_residual")])
    g = run_gate(ROOT / m_f2a_gen["path"])
    experiments.append({"id": "CTRL-F2a-f0genericity", "kind": "control", "mutant": m_f2a_gen,
                        "why": "substitute the S1/S2 genericity literal",
                        "verdict": g.get("verdict"), "failed_rules": g.get("failed_rules"), "exit_code": g.get("exit_code")})

    m_f1_scc = mutate("f1__scc_conclusion.yaml", SCHEMA_SNAP["AF-WCC-VAC-GEN"], [
        ("  conclusion_type: weak_cosmic_censorship", "  conclusion_type: scc_c2_future_inextendibility")])
    g = run_gate(ROOT / m_f1_scc["path"])
    experiments.append({"id": "CTRL-F1-scc", "kind": "control", "mutant": m_f1_scc,
                        "why": "cross-family conclusion under a WCC class (the CAL-01 pattern, applied to the token itself)",
                        "verdict": g.get("verdict"), "failed_rules": g.get("failed_rules"), "exit_code": g.get("exit_code")})

    # ---- repair direction D-B: F0 taxonomy aligned to the frozen rule_spec vocabulary --
    f0_text = (SNAP / "research_map_formulation_taxonomy.yaml").read_text()
    f0_new = f0_text
    for old, new in (
        ('      - "strong_cosmic_censorship_C2"', '      - "scc_c2_future_inextendibility"'),
        ('      - "strong_cosmic_censorship_C0"', '      - "scc_c0_future_inextendibility"'),
        ('      conclusion_type: "strong_cosmic_censorship_C2"', '      conclusion_type: "scc_c2_future_inextendibility"'),
        ('      conclusion_type: "strong_cosmic_censorship_C0"', '      conclusion_type: "scc_c0_future_inextendibility"'),
        ('      type: "strong_cosmic_censorship_C2"', '      type: "scc_c2_future_inextendibility"'),
        ('      type: "strong_cosmic_censorship_C0"', '      type: "scc_c0_future_inextendibility"'),
        ('    allowed: ["baire_residual", "dense_open", "measure_one", "provisional_baire_residual", "unresolved"]',
         '    allowed: ["residual_comeager", "full_measure", "open_dense_escape", "finite_codimension_complement", "none", "unresolved"]'),
        ('      genericity_kind: "provisional_baire_residual"', '      genericity_kind: "residual_comeager"'),
    ):
        n = f0_new.count(old)
        want = 3 if old.startswith('      genericity_kind:') else 1
        if n != want:
            raise SystemExit(f"D-B staging: pattern {old!r} count {n}, expected {want}")
        f0_new = f0_new.replace(old, new)
    d_b = sandbox_consistency(f0_new)
    d_b["staged_f0_bytes"] = len(f0_new.encode())
    d_b["changes"] = [
        "field_vocabulary.conclusion_type.allowed: strong_cosmic_censorship_C2/_C0 -> scc_c2_/scc_c0_future_inextendibility",
        "field_vocabulary.genericity_kind.allowed -> rule_spec vocabulary (residual_comeager, full_measure, open_dense_escape, finite_codimension_complement, none, unresolved)",
        "classes.{AF-SCC-C2-VAC-GEN,AF-SCC-C0-VAC-GEN}.axes.conclusion_type -> canonical scc_* tokens",
        "class conclusion.type for the two SCC classes -> canonical scc_* tokens",
        "classes.*.axes.genericity_kind (x3) -> residual_comeager",
    ]
    d_b["consequence"] = {
        "f0_hash_moves": d_b["new_f0_sha256"] != sources["S1_f0_field_vocabulary"]["sha256"],
        "voids_G_F0_accepts_at_0abb9ed8a961": 4,
        "requires_schema_f0_binding_refresh": True,
        "voids_F1_F2a_F2b_verdicts_at_current_hashes": True,
        "note": "schemas' own f0_binding.rule requires an f0_binding refresh whenever the declared F0 artifact hash changes, so all three schema hashes move and every current verdict is superseded",
    }

    # ---- repair direction D-C: retokenise schemas to the S1 literals -------------------
    d_c = {
        "description": "keep F0 field_vocabulary.allowed as-is; rewrite F2a/F2b conclusion_type to strong_cosmic_censorship_C2/_C0",
        "gate_evidence": [e for e in experiments if e["id"] == "CTRL-F2a-f0literal"],
        "also_violates": {
            "S4_policy": "aliases must never appear in a new canonical artifact",
            "S3_R11": "token must equal rule_spec.vocabularies.class_conclusion_type[class_id]",
        },
        "conclusion": "invalid under the frozen gate and alias policy: the S1 literal is rejected by R11",
    }

    d_a = {
        "description": "controller single-sourcing ruling: the schema-governing vocabulary is S3 rule_spec.vocabularies + S4 alias-policy canonical keys; S1/S2 are F0 documentation lag",
        "artifact_churn": "none",
        "effect": "the HF-088-F2a-VOC / W090-F2A-02 / worker-005-P4 hard failures, which test literal membership in S1, are source-selection errors and can be dispositioned without moving any frozen hash",
        "requires": "controller/Astra finding + audit-lead disposition; no worker may record it (authority rule)",
    }

    contradictions = [
        {
            "id": "VOC-1",
            "axis": "conclusion_type",
            "statement": "F0 field_vocabulary.allowed (S1) lists strong_cosmic_censorship_C2/_C0; VOCAB_ALIASES (S4) declares those strings ALIASES whose canonical keys are scc_c2_/scc_c0_future_inextendibility, and forbids aliases in new canonical artifacts; rule_spec R11 + gate line 300 require the canonical scc_* tokens; the three schemas carry the canonical scc_* tokens.",
            "pinned_refs": [
                f"research_map/formulation_taxonomy.yaml#0abb9ed8a961 (S1 allowed list)",
                f"artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534 (S4)",
                f"artifacts/formulation/rule_spec.json#40f9bb9e657b R11",
                f"artifacts/formulation/tools/check_taxonomy_consistency.py#canon returns S4 keys (S7)",
                f"schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc:{conc_lines['AF-SCC-C2-VAC-GEN']}",
                f"schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda:{conc_lines['AF-SCC-C0-VAC-GEN']}",
            ],
            "who_is_outlier": "S1 (and S2 axes), on the rule chain S3 -> S4 -> S6, because the gate compares literally against S3 and the alias policy makes the schemas' tokens canonical",
        },
        {
            "id": "VOC-2",
            "axis": "genericity_kind",
            "statement": "F0 axes (S2) and allowed list (S1) use provisional_baire_residual; rule_spec.genericity_kind (S3) has no provisional_* member at all and the gate R07 checks membership in it; the schemas use residual_comeager, which is the S4 canonical key.",
            "pinned_refs": [
                "research_map/formulation_taxonomy.yaml#0abb9ed8a961 (S2 axes + S1 genericity allowed)",
                "artifacts/formulation/rule_spec.json#40f9bb9e657b (genericity_kind vocabulary, no provisional_*)",
                f"schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc:{gen_line}",
            ],
            "who_is_outlier": "S1/S2; the gate cannot accept a schema carrying the F0 literal",
        },
    ]

    report = {
        "schema_version": "0.1",
        "artifact_kind": "vocabulary_source_adjudication",
        "task_id": "W017-VOCAB-SOURCE-01",
        "event_id": "w017-20260912-vocab-source-adjudication",
        "created_at": now(),
        "actor": "worker-017",
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": CLASSES,
        "scope": "which frozen source governs conclusion.conclusion_type and genericity.kind for the three class schemas, and what each repair direction costs. No schema/taxonomy/rule content is re-derived; no canonical file is modified.",
        "snapshots": {p.name: sha(p) for p in sorted(SNAP.glob("*"))},
        "sources": sources,
        "census": {"conclusion_type": census, "genericity_kind": census_genericity},
        "affected_classes": {
            "conclusion_type_conflict": [cid for cid in CLASSES if not census[cid]["in_f0_allowed_literal"]],
            "genericity_kind_conflict": [cid for cid in CLASSES if not census_genericity[cid]["in_f0_allowed_literal"]],
            "note": "AF-WCC-VAC-GEN's weak_cosmic_censorship is simultaneously key and alias value in S4, so the conclusion conflict is confined to the two SCC classes; the genericity conflict affects all three schemas (residual_comeager vs provisional_baire_residual), which no current G-FORM hard-failure list charges.",
        },
        "gate_experiments": experiments,
        "contradictions": contradictions,
        "repair_directions": {"D-A_zero_churn_single_sourcing_ruling": d_a, "D-B_align_F0_to_rule_spec": d_b, "D-C_retokenise_schemas": d_c},
        "verdict": "revise",
        "verdict_statement": "The binding chain for the frozen bytes is S3 rule_spec (R11/R07, literal comparison) + S4 canonical keys; on that chain the three schemas are conformant and S1/S2 (F0 field_vocabulary + axes) are the inconsistent source. The literal-membership hard failures against S1 are therefore source-selection errors, but only a controller single-sourcing ruling (D-A) can clear them without moving F0 and all three schema hashes (D-B). D-C is invalid: the frozen gate rejects the S1 literal.",
        "falsifier": "Any of the following falsifies this adjudication: (a) the controller designates research_map/formulation_taxonomy.yaml field_vocabulary.allowed as the binding schema vocabulary (then the schemas are non-conformant and the reviewers' VOC hard failures stand); (b) a re-run of the gate experiments at the pinned hashes changes any verdict or failed-rule list; (c) the alias policy is amended so strong_cosmic_censorship_C2/_C0 become canonical keys (then D-B is unnecessary and the direction inverts); (d) any pinned snapshot hash drifts.",
        "non_claims": [
            "No gate verdict, no node completion, no validation_status change, no theorem.",
            "No canonical artifact, map, ledger, rule, or review by another worker was modified.",
            "Not a full-schema acceptance verdict: quantifiers, physics and the separate f0_binding evidence-hash defect are out of scope.",
            "D-A is a recommendation to the controller/audit lead, who own the ruling.",
        ],
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "report": str((HERE / "report.json").relative_to(ROOT)),
        "report_sha256": sha(HERE / "report.json"),
        "experiments": [{e["id"]: (e["verdict"], e["failed_rules"])} for e in experiments],
        "d_b": {"exit_code": d_b["exit_code"], "stdout": d_b["stdout"], "new_f0_sha256": d_b["new_f0_sha256"], "evidence_sha256": d_b["evidence_sha256"]},
    }, indent=2))
    return report


if __name__ == "__main__":
    main()
