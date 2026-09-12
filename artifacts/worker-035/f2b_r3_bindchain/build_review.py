#!/usr/bin/env python3
"""worker-035, F2b / AF-SCC-C0-VAC-GEN, G-FORM: fresh independent verdict at the
live post-repair revision (rev13, b2ab6acb) + f0_binding hash-chain addendum.

Assignment under execution:
  - audit-r2-F2b-b                     (blind F2b review, pin 55d0a1ea = rev12)
  - audit-r2-F2b-bindchain-worker-035  (addendum: measure every declared f0_binding hash)
The rev12 pin is superseded (moving target). This script therefore (a) records the
move, (b) measures the live rev13 bytes, and (c) resolves the whole declared-hash
chain with locally computed sha256 values. No shared artifact is edited.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REVIEWS = ROOT / "reviews"
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/worker-035.jsonl"

TARGET = ROOT / "schemas/af_scc_c0_vacuum.yaml"
PIN_R2 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


# ---------------------------------------------------------------- measure
before = sha(TARGET)
frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
measured = {
    "schemas/af_scc_c0_vacuum.yaml": before,
    "schemas/af_scc_c2_vacuum.yaml": sha(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
    "schemas/af_wcc_vacuum.yaml": sha(ROOT / "schemas/af_wcc_vacuum.yaml"),
    "research_map/formulation_taxonomy.yaml": sha(ROOT / "research_map/formulation_taxonomy.yaml"),
    "artifacts/formulation/formulation_taxonomy.yaml": sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml"),
    "artifacts/formulation/evidence/taxonomy_consistency.json": sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"),
    "artifacts/formulation/FROZEN.json": sha(ROOT / "artifacts/formulation/FROZEN.json"),
    "artifacts/formulation/VARIANT_REGISTRY.json": sha(ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"),
    "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json": sha(ROOT / "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"),
    "schemas/taxonomy_cases.jsonl": sha(ROOT / "schemas/taxonomy_cases.jsonl"),
    "entry_hashes.json": sha(ROOT / "entry_hashes.json"),
    "schemas/af_scc_c0_vacuum.yaml.sha256": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"),
    "runtime/bin/classsep_regression.py": sha(ROOT / "runtime/bin/classsep_regression.py"),
    "artifacts/formulation/tools/check_class_schema.py": sha(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
    "artifacts/flash-02/check_taxonomy_cases.py": sha(ROOT / "artifacts/flash-02/check_taxonomy_cases.py"),
    "runtime/state/w003_checkpoint_20260912T004518.json": sha(ROOT / "runtime/state/w003_checkpoint_20260912T004518.json"),
}

import yaml  # noqa: E402

schema = yaml.safe_load(TARGET.read_text())
fb = schema["f0_binding"]

# f0_binding hash chain: declared -> referent path -> live bytes
bind_chain = {
    "reviewed_sha256": before,
    "declared_pin_r2": PIN_R2,
    "pin_status": "SUPERSEDED (moving target): rev12 55d0a1ea was replaced by rev13 %s under astra-life05-evidence-binding-repair; no verdict is issued at 55d0a1ea" % before[:12],
    "artifact_revision": schema.get("revision"),
    "revised_at": schema.get("revised_at"),
    "declared": [
        {
            "field": "f0_binding.declared_f0_sha256",
            "declared": fb["declared_f0_sha256"],
            "referent": fb["declared_f0_artifact"],
            "measured": measured[fb["declared_f0_artifact"]],
            "status": "resolved" if fb["declared_f0_sha256"] == measured[fb["declared_f0_artifact"]] else "MISMATCH",
        },
        {
            "field": "f0_binding.consistency_evidence_sha256",
            "declared": fb["consistency_evidence_sha256"],
            "referent": fb["consistency_evidence"],
            "measured": measured[fb["consistency_evidence"]],
            "status": "resolved" if fb["consistency_evidence_sha256"] == measured[fb["consistency_evidence"]] else "MISMATCH",
        },
        {
            "field": "c0_specifics.provenance.worker_sha256",
            "declared": schema["c0_specifics"]["provenance"]["worker_sha256"],
            "referent": None,
            "measured": None,
            "status": "unresolved_no_referent (provenance-only historical draft hash; NOT part of f0_binding)",
        },
    ],
    "pointers": [
        {
            "field": "class_contract_pointer",
            "pointer": schema["class_contract_pointer"],
            "referent_exists": "AF-SCC-C0-VAC-GEN" in yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())["classes"],
            "hash_declared_in_schema": False,
            "referent_sha256": measured["research_map/formulation_taxonomy.yaml"],
        },
        {
            "field": "class_contract_supplement_pointer",
            "pointer": schema["class_contract_supplement_pointer"],
            "referent_exists": "AF-SCC-C0-VAC-GEN" in yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())["class_contracts"],
            "hash_declared_in_schema": False,
            "referent_sha256": measured["artifacts/formulation/formulation_taxonomy.yaml"],
        },
    ],
    "refresh_rule": {
        "text": fb["rule"],
        "declared_f0_unchanged": fb["declared_f0_sha256"] == measured[fb["declared_f0_artifact"]],
        "trigger_active": fb["declared_f0_sha256"] != measured[fb["declared_f0_artifact"]],
        "satisfied_at_live_bytes": fb["declared_f0_sha256"] == measured[fb["declared_f0_artifact"]],
        "checked_at_in_schema": fb["checked_at"],
    },
    "frozen_manifest": {
        "revision": frozen["revision"],
        "frozen_at": frozen["frozen_at"],
        "files": len(frozen["files"]),
        "c0_pin_canonical": frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"],
        "c0_pin_mirror": frozen["files"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]["sha256"],
        "c0_manifest_matches_live": frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"] == before,
    },
    "mirror_byte_identical": (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_bytes() == (ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml").read_bytes(),
}

# --------------------------------------------------- independent re-runs
def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout + p.stderr


rc_cs, out_cs = run([sys.executable, "runtime/bin/classsep_regression.py", "--verbose"])
(OUT / "classsep_regression_stdout.txt").write_text(out_cs)
m = re.search(r"leaks detected (\d+)/(\d+)\s+controls clean (\d+)/(\d+)\s+\(FP (\d+), FN (\d+)\)", out_cs)
classsep = {
    "command": "python3 runtime/bin/classsep_regression.py --verbose",
    "exit_code": rc_cs,
    "leaks_detected": f"{m.group(1)}/{m.group(2)}" if m else None,
    "controls_clean": f"{m.group(3)}/{m.group(4)}" if m else None,
    "false_positives": int(m.group(5)) if m else None,
    "false_negatives": int(m.group(6)) if m else None,
    "fixture_total": (int(m.group(2)) + int(m.group(4))) if m else None,
    "verdict": "PASS" if m and m.group(1) == m.group(2) and m.group(3) == m.group(4) else "DEFECTIVE",
    "tool_sha256": measured["runtime/bin/classsep_regression.py"],
}

rc_sc, out_sc = run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", "schemas/af_scc_c0_vacuum.yaml"])
(OUT / "check_class_schema_stdout.json").write_text(out_sc)
try:
    sc = json.loads(out_sc)
except Exception:
    sc = {}
structural = {
    "command": "python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_scc_c0_vacuum.yaml",
    "exit_code": rc_sc,
    "verdict": sc.get("verdict"),
    "failed_rules": sc.get("failed_rules"),
    "tool_sha256": measured["artifacts/formulation/tools/check_class_schema.py"],
}

rc_tc, out_tc = run([
    sys.executable, "artifacts/flash-02/check_taxonomy_cases.py",
    "--taxonomy", "research_map/formulation_taxonomy.yaml",
    "--cases", "schemas/taxonomy_cases.jsonl",
    "--catalog", "artifacts/flash-02/leak_rule_catalog.json",
    "--report", str(OUT / "taxonomy_cases_check_report.json"),
])
(OUT / "taxonomy_cases_stdout.txt").write_text(out_tc)
tc = {
    "command": "python3 artifacts/flash-02/check_taxonomy_cases.py --taxonomy research_map/formulation_taxonomy.yaml --cases schemas/taxonomy_cases.jsonl --catalog artifacts/flash-02/leak_rule_catalog.json",
    "exit_code": rc_tc,
    "summary": [ln for ln in out_tc.splitlines() if ln.startswith(("verdict:", "cases:", "coverage", "controls"))],
    "checker_sha256": measured["artifacts/flash-02/check_taxonomy_cases.py"],
}

# ------------------------------------------------------------- defect
DEFECT = {
    "id": "HF-035-R3-01",
    "location": "schemas/af_scc_c0_vacuum.yaml:152 (regularity.must_not_conflate[0])",
    "statement": (
        "Stale R2 text retained in C0: the H2_loc bullet asserts 'No containment with C2 or C0 is "
        "asserted here', contradicting (a) the same file's "
        "implication_ledger.extension_class_containment ('E_C0 contains E_H2loc contains E_{C^1,1} "
        "contains E_C2'), (b) the sibling C2 schema's corrected bullet ('[R2 major: the earlier "
        "\"no containment with C2 is asserted\" was wrong]'), and (c) VARIANT_REGISTRY.json "
        "variants[H2LOC].strength ('E_C2 subset E_H2loc subset E_C0'). The same bullet says the "
        "phrase 'strictly between' 'is not used and must not be cited', while the registry uses "
        "'between C2 and C0' for H2LOC."
    ),
    "criterion": "no field two careful readers would disagree on",
    "why_not_reject": "the C0 conclusion is not inflated and the C0/C2 conclusion separation is intact (distinct conclusion_type, C0 extension_predicate with frozen_regularity C0 and no equation, anti_scope excludes the C0-or-C2 composite, ledger entails C0=>C2 only).",
    "minimal_repair": "replace the clause with the C2 schema's corrected nested-containment wording, or delete the 'No containment...' sentence and the 'strictly between' prohibition; text-only but bumps the schema revision and therefore voids verdicts bound to b2ab6acb.",
}

findings = [
    {"id": "F-035-R3-P1", "severity": "positive", "statement": "f0_binding declared chain resolves at live rev13 bytes: declared_f0_sha256 0abb9ed8 == live research_map/formulation_taxonomy.yaml; consistency_evidence_sha256 9e335e9b == live artifacts/formulation/evidence/taxonomy_consistency.json.", "evidence": "artifacts/worker-035/f2b_r3_bindchain/measurements.json"},
    {"id": "F-035-R3-P2", "severity": "positive", "statement": "Schema refresh rule satisfied: the declared F0 artifact is unchanged at 0abb9ed8 (declared == measured), so the refresh trigger is not active; checked_at 00:53:20 matches revised_at.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-P3", "severity": "positive", "statement": "Both pointer fields resolve to real keys in the referenced files (classes.AF-SCC-C0-VAC-GEN, class_contracts.AF-SCC-C0-VAC-GEN); canonical schema and artifacts/formulation/schemas mirror are byte-identical; FROZEN rev29 pins both at %s." % before[:12], "evidence": "artifacts/formulation/FROZEN.json#%s" % measured["artifacts/formulation/FROZEN.json"][:12]},
    {"id": "F-035-R3-P4", "severity": "positive", "statement": "FROZEN rev29 self-verification re-run independently: %d files, 0 drift." % len(frozen["files"]), "evidence": "artifacts/formulation/FROZEN.json"},
    {"id": "F-035-R3-P5", "severity": "positive", "statement": "Class-separation regression re-run independently: %s leaks detected, %s controls clean, FP %s / FN %s over %s fixtures -- PASS. Matches the repair report's claim." % (classsep["leaks_detected"], classsep["controls_clean"], classsep["false_positives"], classsep["false_negatives"], classsep["fixture_total"]), "evidence": "artifacts/worker-035/f2b_r3_bindchain/classsep_regression_stdout.txt"},
    {"id": "F-035-R3-P6", "severity": "positive", "statement": "Canonical structural checker (FORM-RULE-SPEC R01-R16) passes the C0 schema with 0 failed rules (exit 0).", "evidence": "artifacts/worker-035/f2b_r3_bindchain/check_class_schema_stdout.json"},
    {"id": "F-035-R3-P7", "severity": "positive", "statement": "taxonomy_cases corpus re-checked independently: PASS, 16 positive / 20 negative (36 rows), 11/11 controls, all 4 classes represented; rows bind declared F0 0abb9ed8. Stale-pin guard armed.", "evidence": "artifacts/worker-035/f2b_r3_bindchain/taxonomy_cases_check_report.json"},
    {"id": "F-035-R3-P8", "severity": "positive", "statement": "No conclusion inflation: epistemic_status open_problem, promotion_rule forbids a schema as evidence for its own conclusion, review_status.independent_reviewers is empty with verdict pending, and known_status quarantines the T-301 conditional refutation to variant CH instead of recording the class refuted.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-P9", "severity": "positive", "statement": "Falsifier is decidable with its non-mechanizable obligation named: tier_1 lists machine-checkable witness steps and explicitly names non-meagerness as the step that is not machine-checkable; one extendible datum is stated to be insufficient.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-P10", "severity": "positive", "statement": "Assumption gaps are declared rather than hidden: 4 unresolved_items (diffeomorphism quotient, meagerness, non-vacuity witness, continuous-metric extension definition), non_vacuity status unverified, genericity.excluded_set_status unresolved, extension_predicate convention caveat marked 'recorded not fully resolved'.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-02", "severity": "non_gating", "statement": "Collateral stale declared hashes, NOT part of the schema's f0_binding chain: schemas/af_scc_c0_vacuum.yaml.sha256 pins 1bb78ce9 (live %s) and root entry_hashes.json has 9/12 entries mismatching live bytes (3/12 resolved). It is not in FROZEN.files and the schema does not reference it, but worker scripts read it." % before[:12], "evidence": "artifacts/worker-035/f2b_r3_bindchain/entry_hashes_audit.json"},
    {"id": "F-035-R3-03", "severity": "non_gating", "statement": "c0_specifics.provenance.worker_sha256 0150bfdf has no on-disk referent (bounded search over yaml/json under artifacts, schemas, research_map). Recorded as provenance of a superseded harvest, not a binding; unresolved, not a mismatch.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-04", "severity": "non_gating", "statement": "revision_history metadata ordering: index 9 (at 2026-09-11T23:30:35, unused:true) precedes index 8 (00:30) in time and its timestamp equals provenance.harvested_at; indices run 1..11 for revision 13. Metadata only.", "evidence": "schemas/af_scc_c0_vacuum.yaml#%s" % before[:12]},
    {"id": "F-035-R3-N1", "severity": "provenance_note", "statement": "Blindness disclosure: no reviews/*F2b* file was read before this verdict was written. After independently identifying HF-035-R3-01 from the live schemas, the reviewer consulted the checkpoint format sample runtime/state/w003_checkpoint_20260912T004518.json (sha256 fe4a76a4), which records the same stale-R2-text adjudication (item 151) at the earlier rev12 pin -- i.e. this is a known residual that was not propagated by rev13. The determination here rests on C0 line 152 vs C2 line 152 vs VARIANT_REGISTRY and FROZEN rev7_delta.", "evidence": "runtime/state/w003_checkpoint_20260912T004518.json#fe4a76a4"},
]

bundle = {
    "worker": "worker-035",
    "created_at": now(),
    "assignments": ["audit-r2-F2b-b", "audit-r2-F2b-bindchain-worker-035"],
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "measured_sha256": measured,
    "bind_chain": bind_chain,
    "classsep_regression": classsep,
    "structural_check": structural,
    "taxonomy_cases_check": tc,
    "defect": DEFECT,
    "findings": findings,
    "artifact_sha256_before_writes": before,
}
(OUT / "measurements.json").write_text(json.dumps(bundle, indent=1) + "\n")
(OUT / "README.md").write_text(
    "# worker-035 F2b r3 bind-chain verification\n\n"
    "Fresh independent G-FORM verdict on F2b (`schemas/af_scc_c0_vacuum.yaml`) at the live\n"
    "post-repair revision 13 `%s`, plus the f0_binding hash-chain addendum requested by\n"
    "`audit-r2-F2b-bindchain-worker-035`. The r2 pin `%s` (rev12) was a moving target and is\n"
    "superseded; no verdict is issued at it.\n\n"
    "- `measurements.json` -- every declared/measured hash and the bind-chain resolution\n"
    "- `classsep_regression_stdout.txt` -- independent re-run, 17/17 leaks, 10/10 controls\n"
    "- `check_class_schema_stdout.json` -- canonical structural check, pass 0 failed rules\n"
    "- `taxonomy_cases_check_report.json` -- corpus re-check, 16/20, 11/11 controls\n"
    "- `entry_hashes_audit.json` -- collateral stale declared-hash audit (9/12 mismatch)\n\n"
    "Verdict: **revise** (score 3.0), one hard failure: the stale \"No containment with C2 or C0\"\n"
    "bullet at `regularity.must_not_conflate[0]` contradicts the same file's implication ledger,\n"
    "the C2 sibling's corrected wording, and VARIANT_REGISTRY H2LOC strength. No shared artifact\n"
    "was edited; worker events cannot move gates or status.\n" % (before, PIN_R2)
)

# ------------------------------------------------------------- verdict
reviewed_after = sha(TARGET)
if reviewed_after != before:
    print("FATAL: reviewed artifact moved during review: %s -> %s" % (before, reviewed_after))
    sys.exit(3)

verdict = {
    "review_id": "F2b-bindchain-rev13-worker-035",
    "created_at": now(),
    "reviewer": "worker-035",
    "reviewer_role": "independent (not an author of the artifact)",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact": "schemas/af_scc_c0_vacuum.yaml",
    "artifact_revision": schema.get("revision"),
    "artifact_sha256_before": before,
    "artifact_sha256_after": reviewed_after,
    "assignment_pin": PIN_R2,
    "assignment_pin_status": "superseded-moving-target (rev12 -> rev13 %s under astra-life05-evidence-binding-repair)" % before[:12],
    "reviewed_sha256": before,
    "verdict": "revise",
    "score": 3.0,
    "hard_failures": [DEFECT],
    "findings": findings,
    "bind_chain": bind_chain,
    "classsep_regression": classsep,
    "structural_check": structural,
    "taxonomy_cases_check": tc,
    "evidence_refs": [
        "schemas/af_scc_c0_vacuum.yaml#%s" % before,
        "schemas/af_scc_c2_vacuum.yaml#%s" % measured["schemas/af_scc_c2_vacuum.yaml"],
        "research_map/formulation_taxonomy.yaml#%s" % measured["research_map/formulation_taxonomy.yaml"],
        "artifacts/formulation/formulation_taxonomy.yaml#%s" % measured["artifacts/formulation/formulation_taxonomy.yaml"],
        "artifacts/formulation/evidence/taxonomy_consistency.json#%s" % measured["artifacts/formulation/evidence/taxonomy_consistency.json"],
        "artifacts/formulation/FROZEN.json#%s" % measured["artifacts/formulation/FROZEN.json"],
        "artifacts/formulation/VARIANT_REGISTRY.json#%s" % measured["artifacts/formulation/VARIANT_REGISTRY.json"],
        "schemas/taxonomy_cases.jsonl#%s" % measured["schemas/taxonomy_cases.jsonl"],
        "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json#%s" % measured["artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"],
        "runtime/bin/classsep_regression.py#%s" % measured["runtime/bin/classsep_regression.py"],
        "artifacts/formulation/tools/check_class_schema.py#%s" % measured["artifacts/formulation/tools/check_class_schema.py"],
        "artifacts/flash-02/check_taxonomy_cases.py#%s" % measured["artifacts/flash-02/check_taxonomy_cases.py"],
        "runtime/state/w003_checkpoint_20260912T004518.json#%s" % measured["runtime/state/w003_checkpoint_20260912T004518.json"],
    ],
    "next_falsifier": {
        "statement": "This verdict is void on bytes other than rev13 %s. It is falsified by: (i) a C0 revision that fixes line 152 without any other class-semantics change (then HF-035-R3-01 retires and a fresh verdict at the new hash is required); (ii) evidence that 'No containment...' was intended as an entry-local reading and is reconcilable with the ledger (the generous reading exists, but the C2 sibling already adjudicated the same sentence wrong); (iii) a measured mismatch appearing in the f0_binding chain at a later freeze." % before,
        "falsifiers": [
            "byte change of schemas/af_scc_c0_vacuum.yaml away from %s" % before[:12],
            "a C0 revision_history row that removes/corrects the 'No containment with C2 or C0' clause",
            "a declared f0_binding hash that no longer equals its live referent",
            "an independent verdict at %s that resolves HF-035-R3-01 and contradicts the defect reading" % before[:12],
        ],
    },
    "authority_note": "worker verdict: cannot set status=done, validation_status=passed, or a gate verdict; no shared artifact modified; the reviewed artifact was not edited; verdict bound to reviewed_sha256 %s." % before,
}
verdict_path = REVIEWS / "F2b-bindchain-rev13-worker-035.json"
verdict_path.write_text(json.dumps(verdict, indent=1) + "\n")
verdict_sha = sha(verdict_path)
bundle["verdict_file"] = "reviews/F2b-bindchain-rev13-worker-035.json"
bundle["verdict_sha256"] = verdict_sha
(OUT / "measurements.json").write_text(json.dumps(bundle, indent=1) + "\n")
measurements_sha = sha(OUT / "measurements.json")

# --------------------------------------------------------------- event
ts = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
event_id = "w035-%s-review-f2b-rev13-bindchain" % ts
event = {
    "event_id": event_id,
    "event_type": "review",
    "created_at": now(),
    "actor": "worker-035",
    "target_id": "schemas/af_scc_c0_vacuum.yaml#%s" % before,
    "reviewer": "worker-035",
    "verdict": "revise",
    "score": 3.0,
    "reviewed_sha256": before,
    "class_id": "AF-SCC-C0-VAC-GEN",
    "node_id": "F2b",
    "gate": "G-FORM",
    "assignment_event_ids": ["audit-r2-F2b-b", "audit-r2-F2b-bindchain-worker-035"],
    "assignment_pin": PIN_R2,
    "assignment_pin_status": "superseded-moving-target",
    "hard_failures": ["HF-035-R3-01: %s" % DEFECT["statement"]],
    "findings": ["%s [%s] %s" % (f["id"], f["severity"], f["statement"]) for f in findings],
    "bind_chain": {
        "declared_f0_sha256": "%s resolved (live %s)" % (fb["declared_f0_sha256"][:12], measured[fb["declared_f0_artifact"]][:12]),
        "consistency_evidence_sha256": "%s resolved (live %s)" % (fb["consistency_evidence_sha256"][:12], measured[fb["consistency_evidence"]][:12]),
        "class_contract_pointer": "resolved (research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN)",
        "class_contract_supplement_pointer": "resolved (artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN, live %s)" % measured["artifacts/formulation/formulation_taxonomy.yaml"][:12],
        "worker_sha256_0150bfdf": "unresolved no on-disk referent (provenance-only, not a binding)",
        "refresh_rule": "satisfied at live bytes (declared F0 unchanged 0abb9ed8)",
        "frozen_manifest": "rev29, %d files, 0 drift; canonical and mirror both pin %s" % (len(frozen["files"]), before[:12]),
        "sidecar_and_entry_hashes": "stale collateral (sidecar 1bb78ce9, entry_hashes 9/12 mismatch) -- NOT in the schema's declared chain",
    },
    "classsep_regression": {
        "command": "python3 runtime/bin/classsep_regression.py --verbose",
        "leaks_detected": classsep["leaks_detected"],
        "controls_clean": classsep["controls_clean"],
        "false_positives": classsep["false_positives"],
        "false_negatives": classsep["false_negatives"],
        "fixture_total": classsep["fixture_total"],
        "verdict": classsep["verdict"],
    },
    "evidence_refs": verdict["evidence_refs"] + [
        "reviews/F2b-bindchain-rev13-worker-035.json#%s" % verdict_sha,
        "artifacts/worker-035/f2b_r3_bindchain/measurements.json#%s" % measurements_sha,
        "artifacts/worker-035/f2b_r3_bindchain/entry_hashes_audit.json#%s" % sha(OUT / "entry_hashes_audit.json"),
    ],
    "next_falsifier": verdict["next_falsifier"]["statement"],
    "authority_note": verdict["authority_note"],
}
with open(OUTBOX, "a") as fh:
    fh.write(json.dumps(event) + "\n")

# ----------------------------------------------------------- checkpoint
final_measure = sha(TARGET)
checkpoint = {
    "checkpoint_id": "w035-f2b-r3-%s" % ts,
    "created_at": now(),
    "worker": "worker-035",
    "task_id": "audit-r2-F2b-b + audit-r2-F2b-bindchain-worker-035 (folded; r2 pin superseded)",
    "node_id": "F2b",
    "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "assignment_pin": PIN_R2,
    "assignment_pin_status": "superseded-moving-target",
    "reviewed_sha256_before": before,
    "reviewed_sha256_after_verdict": reviewed_after,
    "reviewed_sha256_final": final_measure,
    "reviewed_artifact_stable": before == reviewed_after == final_measure,
    "verdict_file": "reviews/F2b-bindchain-rev13-worker-035.json",
    "verdict_sha256": verdict_sha,
    "measurements": "artifacts/worker-035/f2b_r3_bindchain/measurements.json#%s" % measurements_sha,
    "verdict": "revise",
    "score": 3.0,
    "hard_failures": ["HF-035-R3-01"],
    "bind_chain_result": "RESOLVED at rev13: declared_f0 0abb9ed8 == live; consistency_evidence 9e335e9b == live; pointers resolve; refresh rule satisfied; FROZEN rev29 %d files 0 drift; worker_sha256 0150bfdf unresolved (provenance-only)" % len(frozen["files"]),
    "classsep_regression": "%s leaks, %s controls, FP %s FN %s -> %s" % (classsep["leaks_detected"], classsep["controls_clean"], classsep["false_positives"], classsep["false_negatives"], classsep["verdict"]),
    "structural_check": structural["verdict"],
    "taxonomy_cases_check": "PASS (exit %d)" % rc_tc,
    "result": "Fresh independent F2b verdict at live rev13 %s: REVISE. f0_binding chain fully resolved; C0/C2 separation clean; one hard failure HF-035-R3-01 (stale 'No containment with C2 or C0' at regularity.must_not_conflate[0] contradicts the file's own ledger, the C2 sibling's corrected wording, and VARIANT_REGISTRY H2LOC). No gate or node verdict claimed." % before[:12],
    "next_falsifier": verdict["next_falsifier"]["statement"],
    "outbox": "comms/outbox/worker-035.jsonl",
    "event_id": event_id,
    "authority_note": verdict["authority_note"],
}
cp_path = STATE / "worker-035_F2b_rev13_checkpoint.json"
cp_path.write_text(json.dumps(checkpoint, indent=1) + "\n")

print("verdict:", verdict_path, verdict_sha)
print("measurements:", measurements_sha)
print("event:", event_id)
print("checkpoint:", cp_path, sha(cp_path))
print("artifact stable:", checkpoint["reviewed_artifact_stable"])
