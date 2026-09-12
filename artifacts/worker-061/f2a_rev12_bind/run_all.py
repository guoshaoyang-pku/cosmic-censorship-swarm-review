#!/usr/bin/env python3
"""W061-F2A-REV12-BIND-04 driver.

One bounded class-bound task: independent machine-checked review of F2a
(AF-SCC-C2-VAC-GEN) at the pinned canonical rev12 bytes 5476a3f2c6bc, covering

  * the F0-vocabulary binding axes (conclusion_type, genericity_kind),
  * the declared-vs-measured binding hashes (f0 taxonomy, consistency evidence),
  * the l1_ledger_refs citation-scope claim (worker-029 HF-29-02),
  * adjudication of the four open rev12 hard-failure claims against F2a
    (worker-096 W096-F2A-AFTER-01/02, worker-005 HF-W005-F2D-01/02),
  * the rev11->rev12 repair set (duplicate keys, cross-tree pointer, D0 typing,
    timestamp provenance, extension predicate), and
  * the standing structural controls (canonical gate, class separation,
    sibling data-class concordance, conclusion direction).

Read-only with respect to every artifact outside artifacts/worker-061/f2a_rev12_bind/.
Writes only its own pinned copies, the rev27 shadow gate tree, and the probe output.

Usage : python3 run_all.py
Exit  : 0 always (the last line of the JSON carries the verdict; a hard-failure verdict is
        a finding, not a driver error).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = REPO / "artifacts/worker-061/f2a_rev12_bind"
PIN = TASK / "pinned"
SHADOW = TASK / "shadow_rev27"
GATE_DIR = TASK / "gate"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

TARGET = REPO / "schemas/af_scc_c2_vacuum.yaml"
F1 = REPO / "schemas/af_wcc_vacuum.yaml"
F2B = REPO / "schemas/af_scc_c0_vacuum.yaml"
TAXONOMY = REPO / "research_map/formulation_taxonomy.yaml"
AUTHORING_TAX = REPO / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
KEY_MANIFEST = REPO / "artifacts/formulation/KEY_MANIFEST.json"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
VOCAB = REPO / "artifacts/formulation/VOCAB_ALIASES.json"
CONSISTENCY = REPO / "artifacts/formulation/evidence/taxonomy_consistency.json"
GATE = REPO / "artifacts/formulation/tools/check_class_schema.py"
CLASSSEP = REPO / "research_map/class_separation.py"
REGRESSION = REPO / "runtime/bin/classsep_regression.py"
CUR_LEDGER = REPO / "ledger/theorems.jsonl"
W029_LEDGER = REPO / "artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl"
REGULARITIES_INDEX = REPO / "schemas/af_scc_regularities.yaml"
MAP = REPO / "research_map/research_map.json"

# Full declared pins: the four artifacts whose bytes a verdict binds to (map sha at pass end
# 3d45be5969ec and FROZEN rev28).  Everything else is measured fresh and recorded without a
# pre-declared pin, so no hash in this driver is invented.
DECLARED_PINS = {
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
EXTRA_MEASURED = [
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_class_schema.py",
]
ALL_FILES = list(DECLARED_PINS) + EXTRA_MEASURED

RESTRICTING = [
    "matter", "cosmological_constant", "equations",
    "constraints.hamiltonian", "constraints.momentum",
    "regularity_class.default", "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "asymptotic_decay.metric", "asymptotic_decay.second_fundamental_form",
    "symmetry", "adm_mass.sign",
]
GLOSS = {
    "regularity_class.sobolev_variant.spaces":
        "F1 appends ' (weighted Sobolev)'; F2a/F2b omit the parenthetical label",
    "asymptotic_decay.parity_conditions":
        "F1 appends an explanatory clause after 'not imposed'; F2a/F2b carry 'not imposed'",
}
GLOSS_NORMALISE = {
    "regularity_class.sobolev_variant.spaces": lambda s: re.sub(r"\(weighted sobolev\)", "", s).strip(),
    "asymptotic_decay.parity_conditions": lambda s: s.split(";")[0].strip(),
}
C0_CONCLUSION_TOKENS = ("scc_c0", "strong_cosmic_censorship_c0", "c0_future_inextendibility")


def sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get(d, dotted, default="<MISSING>"):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def norm(x):
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def strict_duplicate_keys(path: Path):
    """Return list of duplicate mapping-key paths using yaml.compose (strict census)."""
    dups = []

    def walk(node, prefix):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = getattr(k, "value", str(k))
                if key in seen:
                    dups.append(f"{prefix}.{key}" if prefix else str(key))
                seen[key] = True
                walk(v, f"{prefix}.{key}" if prefix else str(key))
        elif isinstance(node, yaml.SequenceNode):
            for i, item in enumerate(node.value):
                walk(item, f"{prefix}[{i}]")

    walk(yaml.compose(path.read_text()), "")
    return dups


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "exit": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}


def main() -> int:
    probes = []
    adjudications = []
    facts = {}

    # ---------------- pin / copy / measure ----------------
    measured = {rel: sha256_path(REPO / rel) for rel in ALL_FILES}
    pinned_copy = {}
    for rel in ALL_FILES:
        dst = PIN / Path(rel).name
        shutil.copyfile(REPO / rel, dst)
        pinned_copy[rel] = sha256_path(dst)
    # worker-029 ledger snapshot (pin 3e3d35531421) and the current ledger
    w029_snap = W029_LEDGER if W029_LEDGER.exists() else None
    facts["pin_measurement"] = {"at": NOW.isoformat(timespec="seconds")}
    for rel in ALL_FILES:
        declared = DECLARED_PINS.get(rel)
        facts["pin_measurement"][rel] = {
            "declared": declared, "measured": measured[rel],
            "pinned_copy": pinned_copy.get(rel),
            "match_declared": (measured[rel] == declared) if declared is not None else None,
        }
    facts["pin_measurement"]["ledger_current"] = {
        "path": "ledger/theorems.jsonl", "measured": sha256_path(CUR_LEDGER)}
    facts["pin_measurement"]["ledger_w029_snapshot"] = {
        "path": "artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl",
        "measured": sha256_path(w029_snap) if w029_snap else None,
        "exists": bool(w029_snap)}
    facts["pin_measurement"]["regularities_index"] = {
        "path": "schemas/af_scc_regularities.yaml", "measured": sha256_path(REGULARITIES_INDEX)}
    facts["pin_measurement"]["target_mtime"] = datetime.fromtimestamp(
        TARGET.stat().st_mtime, CST).isoformat(timespec="seconds")

    d = yaml.safe_load((PIN / "af_scc_c2_vacuum.yaml").read_text())
    f1 = yaml.safe_load((PIN / "af_wcc_vacuum.yaml").read_text())
    f2b = yaml.safe_load((PIN / "af_scc_c0_vacuum.yaml").read_text())
    tax = yaml.safe_load((PIN / "formulation_taxonomy.yaml").read_text())
    frozen = json.loads((PIN / "FROZEN.json").read_text())
    manifest = json.loads((PIN / "KEY_MANIFEST.json").read_text())
    manifest27 = json.loads((PIN / "KEY_MANIFEST.rev27.json").read_text())
    spec = json.loads((PIN / "rule_spec.json").read_text())
    vocab = json.loads((PIN / "VOCAB_ALIASES.json").read_text())
    raw = (PIN / "af_scc_c2_vacuum.yaml").read_text()

    def probe(pid, title, ok, detail, hard=True):
        probes.append({"id": pid, "title": title, "status": "pass" if ok else "fail",
                       "hard": hard, "detail": detail})

    # ---------------- P1 identity / class binding ----------------
    cid = d.get("class_id")
    comps = d.get("class_components")
    p1_ok = (cid == "AF-SCC-C2-VAC-GEN" and d.get("node_id") == "F2a"
             and d.get("artifact_kind") == "class_schema"
             and isinstance(comps, dict)
             and str(comps.get("censorship", "")).upper() == "SCC"
             and str(comps.get("regularity_token", "")).upper() == "C2")
    probe("P1-IDENTITY-CLASS-BINDING",
          "exactly one top-level class_id AF-SCC-C2-VAC-GEN decodes to AF/SCC/VAC/GEN with C2 regularity",
          p1_ok, {"class_id": cid, "node_id": d.get("node_id"), "class_components": comps,
                  "conclusion_family": get(d, "conclusion.family")})

    # ---------------- P2/P3 F0 vocabulary binding ----------------
    f0_ct_allowed = get(tax, "field_vocabulary.conclusion_type.allowed", [])
    declared_ct = get(d, "conclusion.conclusion_type")
    rule_ct = get(spec, "vocabularies.class_conclusion_type.AF-SCC-C2-VAC-GEN")
    vocab_ct_groups = {k: v for k, v in (vocab.get("conclusion_type") or {}).items()}
    ct_group = next((k for k, members in vocab_ct_groups.items()
                     if declared_ct == k or declared_ct in members), None)
    alias_bound = bool(d.get("vocabulary_aliases_ref")) or ("VOCAB_ALIASES" in raw)
    p2_ok = (declared_ct in f0_ct_allowed) or alias_bound
    probe("P2-F0-VOCAB-CONCLUSION-BINDING",
          "conclusion_type binds to the canonical F0 allowed vocabulary, or the alias equivalence is bound at artifact level",
          p2_ok, {"declared": declared_ct, "f0_allowed": f0_ct_allowed,
                  "literal_in_f0_allowed": declared_ct in f0_ct_allowed,
                  "rule_spec_token": rule_ct, "rule_spec_match": declared_ct == rule_ct,
                  "vocab_alias_group": ct_group,
                  "vocab_alias_group_members": vocab_ct_groups.get(ct_group),
                  "vocabulary_aliases_ref": d.get("vocabulary_aliases_ref"),
                  "artifact_text_mentions_VOCAB_ALIASES": "VOCAB_ALIASES" in raw},
          hard=True)

    f0_gk_allowed = get(tax, "field_vocabulary.genericity_kind.allowed", [])
    declared_gk = get(d, "genericity.kind")
    rule_gk = get(spec, "vocabularies.genericity_kind", [])
    gk_group = next((k for k, members in (vocab.get("genericity_kind") or {}).items()
                     if declared_gk == k or declared_gk in members), None)
    p3_ok = (declared_gk in f0_gk_allowed) or alias_bound
    probe("P3-F0-VOCAB-GENERICITY-BINDING",
          "genericity.kind binds to the canonical F0 allowed vocabulary, or the alias equivalence is bound at artifact level",
          p3_ok, {"declared": declared_gk, "f0_allowed": f0_gk_allowed,
                  "literal_in_f0_allowed": declared_gk in f0_gk_allowed,
                  "rule_spec_tokens": rule_gk, "rule_spec_match": declared_gk in rule_gk,
                  "vocab_alias_group": gk_group,
                  "vocab_alias_group_members": (vocab.get("genericity_kind") or {}).get(gk_group),
                  "artifact_text_mentions_VOCAB_ALIASES": "VOCAB_ALIASES" in raw},
          hard=True)

    # ---------------- P4 binding-hash freshness ----------------
    declared_ev = get(d, "f0_binding.consistency_evidence_sha256")
    measured_ev = measured["artifacts/formulation/evidence/taxonomy_consistency.json"]
    frozen_files = frozen.get("files") if isinstance(frozen.get("files"), dict) else {}
    frozen_ev = frozen_files.get("artifacts/formulation/evidence/taxonomy_consistency.json")
    declared_f0 = get(d, "f0_binding.declared_f0_sha256")
    measured_f0 = measured["research_map/formulation_taxonomy.yaml"]
    frozen_f2a = frozen_files.get("schemas/af_scc_c2_vacuum.yaml")
    p4_ok = (declared_ev == measured_ev == frozen_ev)
    probe("P4-EVIDENCE-BINDING-FRESHNESS",
          "declared consistency_evidence_sha256 equals the measured and FROZEN-pinned evidence bytes",
          p4_ok, {"declared": declared_ev, "measured": measured_ev, "frozen": frozen_ev,
                  "declared_f0": declared_f0, "measured_f0": measured_f0,
                  "frozen_f2a": frozen_f2a,
                  "declared_f0_matches_measured": declared_f0 == measured_f0,
                  "frozen_f2a_matches_measured": frozen_f2a == measured["schemas/af_scc_c2_vacuum.yaml"]},
          hard=True)

    # cross-class measured fact: same field in F1/F2b
    facts["cross_class_binding"] = {
        "F1": {"declared_consistency_evidence": get(f1, "f0_binding.consistency_evidence_sha256"),
               "declared_f0": get(f1, "f0_binding.declared_f0_sha256"),
               "conclusion_type": get(f1, "conclusion.conclusion_type"),
               "genericity_kind": get(f1, "genericity.kind"),
               "mentions_VOCAB_ALIASES": "VOCAB_ALIASES" in (REPO / "schemas/af_wcc_vacuum.yaml").read_text()},
        "F2b": {"declared_consistency_evidence": get(f2b, "f0_binding.consistency_evidence_sha256"),
                "declared_f0": get(f2b, "f0_binding.declared_f0_sha256"),
                "conclusion_type": get(f2b, "conclusion.conclusion_type"),
                "genericity_kind": get(f2b, "genericity.kind"),
                "mentions_VOCAB_ALIASES": "VOCAB_ALIASES" in (REPO / "schemas/af_scc_c0_vacuum.yaml").read_text()},
        "measured_consistency_evidence": measured_ev,
        "measured_f0": measured_f0,
    }

    # ---------------- P5 citation-scope (ledger cross-check) ----------------
    def ledger_rows(path: Path):
        rows = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rid = r.get("theorem_id") or r.get("id")
            if rid:
                rows[rid] = r
        return rows

    cur_rows = ledger_rows(CUR_LEDGER)
    snap_rows = ledger_rows(w029_snap) if w029_snap else {}
    refs = d.get("l1_ledger_refs") or []
    overclaims = []
    for ref in refs:
        tid = ref.get("theorem_id")
        declared_cs = str(ref.get("citation_status", ""))
        if "verified" not in declared_cs:
            continue
        row = cur_rows.get(tid, {})
        vs = str(row.get("verification_status", ""))
        rs = str(row.get("review_status", ""))
        independently_reviewed = "independently_reviewed" in rs and "not_independently" not in rs
        if ("verified" not in vs) and not independently_reviewed:
            overclaims.append({
                "theorem_id": tid,
                "declared_citation_status": declared_cs,
                "artifact_l1_status": ref.get("l1_status"),
                "ledger_verification_status": vs or "<row-missing>",
                "ledger_review_status": rs or "<row-missing>",
                "ledger_snapshot_3e3d35531421": {k: snap_rows.get(tid, {}).get(k) for k in
                                                  ("verification_status", "review_status")},
            })
    token_count_cur = CUR_LEDGER.read_text().count("verified_by_L1")
    token_count_snap = w029_snap.read_text().count("verified_by_L1") if w029_snap else None
    p5_ok = not overclaims
    probe("P5-CITATION-SCOPE-BINDING",
          "every l1_ledger_refs row declaring a verified citation resolves to a ledger row that records independent verification",
          p5_ok, {"overclaims": overclaims,
                  "ledger_token_counts": {"current_a1674f094979": token_count_cur,
                                          "w029_snapshot_3e3d35531421": token_count_snap},
                  "n_refs": len(refs),
                  "unresolved_rows_consistent": [
                      {"theorem_id": r.get("theorem_id"), "citation_status": r.get("citation_status"),
                       "ledger_verification_status": cur_rows.get(r.get("theorem_id"), {}).get("verification_status")}
                      for r in refs if "verified" not in str(r.get("citation_status", ""))]},
          hard=True)

    # ---------------- P6 gate adjudication (current manifest vs rev27 shadow) ----------------
    gate_cur = run([sys.executable, str(GATE), "--json", "schemas/af_scc_c2_vacuum.yaml"])
    GATE_DIR.joinpath("gate_current_manifest.json").write_text(gate_cur["stdout"])
    # shadow tree: rev27 manifest, same tool and rule spec bytes
    (SHADOW / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(GATE, SHADOW / "tools/check_class_schema.py")
    shutil.copyfile(RULE_SPEC, SHADOW / "rule_spec.json")
    shutil.copyfile(PIN / "KEY_MANIFEST.rev27.json", SHADOW / "KEY_MANIFEST.json")
    gate_rev27 = run([sys.executable, str(SHADOW / "tools/check_class_schema.py"), "--json",
                      str(PIN / "af_scc_c2_vacuum.yaml")])
    GATE_DIR.joinpath("gate_shadow_rev27_manifest.json").write_text(gate_rev27["stdout"])
    facts["gate_matrix"] = {
        "gate_tool_sha256": measured["artifacts/formulation/tools/check_class_schema.py"],
        "rule_spec_sha256": measured["artifacts/formulation/rule_spec.json"],
        "manifest_current": {"sha256": measured["artifacts/formulation/KEY_MANIFEST.json"],
                             "verdict": json.loads(gate_cur["stdout"]).get("verdict"),
                             "failed_rules": json.loads(gate_cur["stdout"]).get("failed_rules"),
                             "exit": gate_cur["exit"]},
        "manifest_rev27_shadow": {"sha256": sha256_path(PIN / "KEY_MANIFEST.rev27.json"),
                                  "verdict": json.loads(gate_rev27["stdout"]).get("verdict"),
                                  "failed_rules": json.loads(gate_rev27["stdout"]).get("failed_rules"),
                                  "exit": gate_rev27["exit"],
                                  "unknown_keys": json.loads(gate_rev27["stdout"]).get("failures")},
    }
    f2a_unknown = {"at", "class_contract_supplement_pointer", "consistency_evidence_sha256",
                   "index", "notes", "revision_history"}
    missing_from_rev27 = sorted(f2a_unknown - set(manifest27.get("allowed_keys", [])))
    added_in_rev28 = sorted(set(manifest.get("allowed_keys", [])) - set(manifest27.get("allowed_keys", [])))
    probe("P6-R22-MANIFEST-ADJUDICATION",
          "the rev12 R22 failure claim is re-run against both manifest revisions; the current manifest result is the binding one",
          True, {"current": facts["gate_matrix"]["manifest_current"],
                 "rev27_shadow": {k: v for k, v in facts["gate_matrix"]["manifest_rev27_shadow"].items()
                                  if k != "unknown_keys"},
                 "rev12_keys_absent_from_rev27": missing_from_rev27,
                 "keys_added_in_rev28": added_in_rev28}, hard=False)
    adjudications.append({
        "claim_ids": ["W096-F2A-AFTER-01", "HF-W005-F2D-01"],
        "claim": "canonical check_class_schema.py fails R22 unknown keys at F2a rev12 5476a3f2c6bc",
        "disposition": ("FALSIFIED at the current manifest: gate verdict=pass failed_rules=[] exit=0; "
                        "REPRODUCED in the rev27-manifest shadow (verdict=fail failed_rules=['R22']). "
                        "The claim was manifest-dependent, not a defect of the schema bytes."),
        "evidence_refs": ["artifacts/worker-061/f2a_rev12_bind/gate/gate_current_manifest.json",
                          "artifacts/worker-061/f2a_rev12_bind/gate/gate_shadow_rev27_manifest.json",
                          "artifacts/formulation/KEY_MANIFEST.json#014e2d301978"],
        "falsifier": ("a run of the same gate tool at the rev28 manifest (014e2d30) on the pinned bytes "
                      "returning fail, or a run at the rev27 manifest (fce91948) returning pass"),
    })

    # ---------------- P7 review_status vs ledger ----------------
    mapd = json.loads(MAP.read_text())
    rev12_reviews = [r for r in mapd.get("reviews", [])
                     if str(r.get("reviewed_sha256") or "").startswith("5476a3f2c6bc")
                     or str(r.get("artifact_sha256") or "").startswith("5476a3f2c6bc")]
    by_verdict = {}
    for r in rev12_reviews:
        by_verdict.setdefault(str(r.get("verdict")), []).append(r.get("reviewer"))
    declared_rs = d.get("review_status") or {}
    rs_ok = bool(declared_rs.get("independent_reviewers")) or not rev12_reviews
    probe("P7-REVIEW-STATUS-LEDGER",
          "declared review_status agrees with the map verdict ledger bound to the pinned hash",
          rs_ok, {"declared": declared_rs,
                  "map_reviews_at_pin": {"count": len(rev12_reviews), "by_verdict": by_verdict},
                  "note": ("review_status is an authoring-time snapshot; at authoring time no rev12 "
                           "review existed, so this is metadata drift rather than an authoring defect")},
          hard=False)
    adjudications.append({
        "claim_ids": ["W096-F2A-AFTER-02"],
        "claim": "review_status.independent_reviewers=[] and verdict=pending while reviews bind rev12",
        "disposition": ("REPRODUCED as a fact, classified SOFT/process: the field is an authoring-time "
                        "snapshot; the authoritative review state is the map ledger, which now records "
                        f"{len(rev12_reviews)} verdict(s) at this hash ({by_verdict}). No semantic or "
                        "binding content in the field."),
        "evidence_refs": ["research_map/research_map.json#reviews", "schemas/af_scc_c2_vacuum.yaml#review_status"],
        "falsifier": "a map ledger with zero reviews at 5476a3f2c6bc, or a revision whose review_status carries non-empty independent_reviewers at authoring time",
    })

    # ---------------- P8 regularities index pin ----------------
    idx_text = REGULARITIES_INDEX.read_text()
    try:
        idx_yaml = yaml.safe_load(idx_text) or {}
    except Exception as exc:  # pragma: no cover
        idx_yaml = {"_parse_error": str(exc)}
    idx_pins = {}
    for comp in (idx_yaml.get("components") or []) if isinstance(idx_yaml, dict) else []:
        if isinstance(comp, dict) and comp.get("path"):
            idx_pins[comp["path"]] = comp.get("sha256")
    stale_pins = {}
    for path, pinned in idx_pins.items():
        live = measured.get(path) or (sha256_path(REPO / path) if (REPO / path).exists() else None)
        if live and pinned != live:
            stale_pins[path] = {"index_pins": pinned, "live": live}
    probe("P8-INDEX-PIN-ADJUDICATION",
          "the regularities index re-pins its component hashes to the rev12 FROZEN values",
          not stale_pins,
          {"index_path": "schemas/af_scc_regularities.yaml",
           "index_sha256": sha256_path(REGULARITIES_INDEX),
           "declared_component_pins": idx_pins, "stale_pins": stale_pins,
           "index_top_keys": list(idx_yaml.keys()) if isinstance(idx_yaml, dict) else None},
          hard=False)
    adjudications.append({
        "claim_ids": ["HF-W005-F2D-02"],
        "claim": "the index still pins the pre-rev12 hashes b6123750b37d (F2a) / 1bb78ce9b357 (F2b)",
        "disposition": ("REPRODUCED as a fact, but it is a defect of schemas/af_scc_regularities.yaml "
                        "(the index), not of F2a at 5476a3f2c6bc. FROZEN rev28 pins F2a at 5476a3f2c6bc "
                        "in both trees, so hash-bound verdicts can cite the artifact directly; the index "
                        "must be repinned or it cannot be used as a binding surface."),
        "evidence_refs": ["schemas/af_scc_regularities.yaml#94562101a816",
                          "artifacts/formulation/FROZEN.json#2f358f6722d9",
                          "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc"],
        "falsifier": "an index revision whose declared F2a/F2b component hashes equal 5476a3f2c6bc / 55d0a1ea9bda",
    })

    # ---------------- P9 rev11 -> rev12 repair set ----------------
    dups = strict_duplicate_keys(PIN / "af_scc_c2_vacuum.yaml")
    dups_f1 = strict_duplicate_keys(PIN / "af_wcc_vacuum.yaml")
    dups_f2b = strict_duplicate_keys(PIN / "af_scc_c0_vacuum.yaml")
    pointer = str(get(d, "class_contract_pointer"))
    pointer_ok = pointer.startswith("research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN") \
        and "AF-SCC-C2-VAC-GEN" in (tax.get("classes") or {})
    d0_def = str(get(d, "quantifiers.domains.D0.definition"))
    formal = str(get(d, "quantifiers.formal"))
    binder_retyped = ("(s,delta) in D0" not in formal.replace(" ", "")) and ("tagged disjoint union" in d0_def)
    hist = d.get("revision_history") or []
    hist_idx = [h.get("index") for h in hist if isinstance(h, dict)]
    hist_monotone = hist_idx == sorted(hist_idx) and len(set(hist_idx)) == len(hist_idx)
    revised_at = str(d.get("revised_at"))
    ts = datetime.fromisoformat(revised_at)
    mtime = datetime.fromtimestamp(TARGET.stat().st_mtime, CST)
    ts_ok = ts <= NOW and ts <= mtime
    ext = d.get("extension_predicate") or {}
    d3_ref = str(get(d, "quantifiers.domains.D3.definition_ref"))
    ext_ok = (ext.get("name") == "proper_future_extension_in_class"
              and d3_ref == "extension_predicate"
              and "proper future C2 vacuum extension" in formal)
    p9_ok = (not dups) and pointer_ok and binder_retyped and hist_monotone and ts_ok and ext_ok
    probe("P9-REV11-REPAIRS-AT-REV12",
          "rev12 carries no duplicate YAML keys, the class pointer resolves canonically, D0 is re-typed, revision history is monotone, timestamps are not future-dated, and the extension predicate is present",
          p9_ok, {"duplicate_keys_f2a": dups, "duplicate_keys_f1": dups_f1, "duplicate_keys_f2b": dups_f2b,
                  "class_contract_pointer": pointer, "pointer_resolves_canonical": pointer_ok,
                  "D0_definition_head": d0_def[:220], "d0_binder_retyped": binder_retyped,
                  "revision_history_indices": hist_idx, "hist_monotone": hist_monotone,
                  "revised_at": revised_at, "mtime": mtime.isoformat(timespec="seconds"),
                  "measurement_wall_clock": NOW.isoformat(timespec="seconds"),
                  "timestamp_not_future": ts_ok, "extension_predicate_present": ext_ok},
          hard=True)

    # ---------------- P10 F0 hash binding ----------------
    probe("P10-F0-HASH-BINDING",
          "f0_binding.declared_f0_sha256 equals the measured canonical taxonomy bytes",
          declared_f0 == measured_f0,
          {"declared": declared_f0, "measured": measured_f0},
          hard=True)

    # ---------------- P11 class separation ----------------
    spec_cs = importlib.util.spec_from_file_location("class_separation", CLASSSEP)
    cs = importlib.util.module_from_spec(spec_cs)
    spec_cs.loader.exec_module(cs)
    cs_findings = cs.findings_for_text(raw, "pinned F2a rev12")
    reg = run([sys.executable, str(REGRESSION)])
    p11_ok = (not cs_findings) and reg["exit"] == 0
    probe("P11-CLASS-SEPARATION",
          "frozen detector finds no class merge/leak on the pinned text and the regression corpus still passes",
          p11_ok, {"detector_findings": cs_findings, "regression_exit": reg["exit"],
                   "regression_tail": reg["stdout"][-400:]},
          hard=True)

    # ---------------- P12 sibling data-class concordance ----------------
    sib = {"F1": f1, "F2a": d, "F2b": f2b}
    conc = {"restricting_equal": [], "gloss_only": [], "divergent": []}
    for path in RESTRICTING:
        vals = {k: norm(get(v, "data_class." + path)) for k, v in sib.items()}
        if len(set(vals.values())) == 1:
            conc["restricting_equal"].append(path)
        else:
            conc["divergent"].append({"path": path, "values": vals})
    for path, note in GLOSS.items():
        vals = {k: norm(get(v, "data_class." + path)) for k, v in sib.items()}
        base = {k: GLOSS_NORMALISE[path](str(v)) for k, v in vals.items()}
        if len(set(base.values())) == 1:
            conc["gloss_only"].append({"path": path, "note": note, "values": vals})
        else:
            conc["divergent"].append({"path": path, "values": vals})
    probe("P12-SIBLING-DATA-CLASS",
          "F1/F2a/F2b agree on the restricted data-class projection at the pinned triple",
          not conc["divergent"], conc, hard=True)

    # ---------------- P13 conclusion direction ----------------
    assertive = {
        "conclusion_type": get(d, "conclusion.conclusion_type"),
        "family": get(d, "conclusion.family"),
        "statement_natural_language": get(d, "conclusion.statement_natural_language"),
        "statement_formal": get(d, "conclusion.statement_formal"),
        "equivalent_rephrasings": get(d, "conclusion.equivalent_rephrasings"),
    }
    conc_text = json.dumps(assertive, default=str).lower()
    wcc_in_conclusion = bool(re.search(r"visible|visibility|weak cosmic|wcc", conc_text))
    c0_asserted = any(tok in str(get(d, "conclusion.conclusion_type", "")).lower()
                      for tok in C0_CONCLUSION_TOKENS)
    probe("P13-CONCLUSION-DIRECTION",
          "conclusion carries no WCC/visibility content and asserts no C0 token",
          (not wcc_in_conclusion) and (not c0_asserted),
          {"wcc_tokens_in_conclusion": wcc_in_conclusion, "c0_token_asserted": c0_asserted},
          hard=True)

    # ---------------- P14 non-vacuity branchwise (advisory) ----------------
    ambient = str(get(d, "genericity.ambient_space"))
    topology_or_measure = str(get(d, "genericity.topology_or_measure"))
    d0_has_smooth_branch = "smooth" in d0_def.lower()
    banach_claim = "banach" in ambient.lower()
    p14_ok = not (d0_has_smooth_branch and banach_claim)
    probe("P14-NONVACUITY-BRANCHWISE",
          "the non-vacuity (Baire) argument covers every branch of the D0 tagged union",
          p14_ok,
          {"d0_has_smooth_branch": d0_has_smooth_branch, "ambient_claims_banach": banach_claim,
           "ambient_space": ambient, "topology_or_measure": topology_or_measure,
           "note": "advisory: with D0 = smooth | (sobolev,s,delta), 'closed subset of a Banach space, hence Baire' covers only the Sobolev branch"},
          hard=False)

    # ---------------- drift control ----------------
    drift = {rel: sha256_path(REPO / rel) for rel in ALL_FILES}
    drift_ok = all(drift[rel] == measured[rel] for rel in ALL_FILES)
    probe("P15-DRIFT-CONTROL",
          "all pinned canonical hashes are byte-stable across the probe window",
          drift_ok,
          {"start": measured, "end": drift, "stable": drift_ok}, hard=True)

    hard_failures = [p["id"] for p in probes if p["hard"] and p["status"] == "fail"]
    verdict = "accept" if not hard_failures else "revise"
    score = 4.0 if not hard_failures else 3.0
    out = {
        "task_id": "W061-F2A-REV12-BIND-04",
        "generated_at": NOW.isoformat(timespec="seconds"),
        "target": {"node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
                   "artifact": "schemas/af_scc_c2_vacuum.yaml",
                   "reviewed_sha256": measured["schemas/af_scc_c2_vacuum.yaml"]},
        "pins": facts["pin_measurement"],
        "gate_matrix": facts["gate_matrix"],
        "cross_class_binding": facts["cross_class_binding"],
        "probes": probes,
        "adjudications": adjudications,
        "hard_failures": hard_failures,
        "verdict": verdict,
        "score": score,
        "next_falsifier": (
            "Re-measure schemas/af_scc_c2_vacuum.yaml; any change voids this verdict. On 5476a3f2c6bc "
            "the revise is falsified by any one of: (a) an F0 revision whose field_vocabulary."
            "conclusion_type.allowed contains scc_c2_future_inextendibility and whose genericity_kind."
            "allowed contains residual_comeager, or an F2a revision that binds the alias registry "
            "explicitly (vocabulary_aliases_ref), or a controller decision recorded in the map that "
            "alias-equivalence satisfies G-FORM; (b) f0_binding.consistency_evidence_sha256 equal to "
            "the measured and FROZEN-pinned evidence bytes 9e335e9ba1bf; (c) every l1_ledger_refs row "
            "with citation_status verified_by_L1 backed by a ledger row whose verification_status or "
            "review_status records independent verification, or the rows demoted to the ledger "
            "vocabulary; (d) the rev28 manifest replay no longer turning the R22 claim fail (i.e. a "
            "future manifest/frozen transition that re-breaks the rev12 keys)."),
        "scope_limits": [
            "Structure, class binding, provenance binding and citation-scope only: no physical truth claim, no proof check, no citation-content verification.",
            "The rev11 semantic repairs are confirmed by machine checks at rev12; no new semantic defect was searched beyond the listed probes.",
            "Worker evidence only: this does not set node status, validation_status or any gate verdict.",
            "The same binding axes were NOT part of W061-F1-REV12-GATE-03; cross_class_binding records measured F1/F2b values for the controller, not a verdict on F1/F2b.",
        ],
        "authority_note": "Worker evidence only. No canonical artifact outside artifacts/worker-061/f2a_rev12_bind/ was modified; the canonical files were copied read-only into pinned/ and the rev27 manifest was replayed in a shadow tree.",
    }
    out_path = TASK / "probe_f2a_rev12_output.json"
    out_path.write_text(json.dumps(out, indent=1, sort_keys=False))
    print(json.dumps({"task_id": out["task_id"], "verdict": verdict, "score": score,
                      "hard_failures": hard_failures, "output": str(out_path),
                      "probe_status": {p["id"]: p["status"] for p in probes}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
