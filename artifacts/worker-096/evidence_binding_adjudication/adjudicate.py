#!/usr/bin/env python3
"""W096-F1-EVIDENCE-BINDING-ADJUDICATION-01 — independent, read-only adjudication of the
consistency-evidence binding defect on the frozen F1 class schema AF-WCC-VAC-GEN.

Question: all three frozen class schemas declare
    f0_binding.consistency_evidence_sha256 = 675a99d0d25b...
while the canonical evidence path
    artifacts/formulation/evidence/taxonomy_consistency.json
measures 9e335e9ba1bf... and FROZEN revision 28 pins 9e335e9b.
Which repair ordering closes the defect without voiding the revision-12 verdicts?

Method: measure the declarations, pins and both candidate evidence formats; reproduce the
mechanism in isolated sandbox mirrors (the canonical checker writes its output file
unconditionally and its output format carries no tree hashes); machine-check the consequences
of each repair option with the project's own verify_frozen.py; propose a minimal checker patch.

Safety: the canonical tree is never written. The script snapshots every canonical hash before
the experiments and fails closed (exit 2) if any of them moved by the end. All sandboxes live
under this artifact directory. Deterministic except for wall-clock timestamps in the report.

Usage: python3 adjudicate.py
"""
import hashlib
import json
import shutil
import subprocess
import sys
import difflib
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
# script sits at <root>/artifacts/worker-096/evidence_binding_adjudication/adjudicate.py
ROOT = Path(__file__).resolve().parents[3]
OUT = HERE
NOW = lambda: datetime.now().astimezone().isoformat(timespec="seconds")

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
VERIFY = "artifacts/formulation/tools/verify_frozen.py"
FROZEN = "artifacts/formulation/FROZEN.json"
ENRICHED_COPY = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd=None):
    r = subprocess.run([sys.executable] + cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return {"cmd": " ".join([sys.executable] + cmd), "cwd": str(cwd) if cwd else None,
            "exit": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}


def mirror(dst, rels, evidence_bytes=None, frozen_edit=None):
    """Copy rel paths from the canonical tree into an isolated sandbox root."""
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    for rel in rels:
        s = ROOT / rel
        d = dst / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
    if evidence_bytes is not None:
        (dst / EVIDENCE).parent.mkdir(parents=True, exist_ok=True)
        (dst / EVIDENCE).write_bytes(evidence_bytes)
    if frozen_edit is not None:
        man = json.loads((dst / FROZEN).read_text())
        for path, rec in frozen_edit.items():
            man["files"][path] = rec
        (dst / FROZEN).write_text(json.dumps(man, indent=2) + "\n")
    return dst


report = {
    "task_id": "W096-F1-EVIDENCE-BINDING-ADJUDICATION-01",
    "worker": "worker-096",
    "created_at": NOW(),
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN"],
    "node_id": "F1",
    "gate": "G-FORM",
    "scope": "F1 AF-WCC-VAC-GEN is the bound class; F2a/F2b are measured for defect scope only and no verdict is claimed for them",
    "does_not_claim": [
        "no canonical file edited; no node status, validation_status or gate verdict",
        "no mathematical-semantics adjudication",
        "repair options are proposals for the path owner (lead-formulation) and gate owner (lead-audit)",
    ],
}

start = {rel: sha256(ROOT / rel) for rel in
         [CHECKER, EVIDENCE, FROZEN, VERIFY, F0_CANON, F0_SUPP] + list(SCHEMAS.values())}

# ---------------------------------------------------------------- measurement
measured = {
    "schemas": {},
    "frozen_revision": json.loads((ROOT / FROZEN).read_text()).get("revision"),
    "frozen_frozen_at": json.loads((ROOT / FROZEN).read_text()).get("frozen_at"),
    "evidence_canonical_sha256": sha256(ROOT / EVIDENCE),
    "evidence_canonical_bytes": (ROOT / EVIDENCE).stat().st_size,
    "checker_sha256": sha256(ROOT / CHECKER),
    "f0_canonical_sha256": sha256(ROOT / F0_CANON),
    "f0_supplement_sha256": sha256(ROOT / F0_SUPP),
    "enriched_candidate_sha256": sha256(ROOT / ENRICHED_COPY),
}
for node, rel in SCHEMAS.items():
    d = yaml.safe_load((ROOT / rel).read_text())
    fb = d.get("f0_binding", {})
    measured["schemas"][node] = {
        "path": rel,
        "sha256": sha256(ROOT / rel),
        "declared_consistency_evidence": fb.get("consistency_evidence"),
        "declared_consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "checked_at": fb.get("checked_at"),
    }
frozen = json.loads((ROOT / FROZEN).read_text())
measured["frozen_evidence_pin"] = frozen["files"].get(EVIDENCE)
measured["frozen_checker_pin"] = frozen["files"].get(CHECKER)
measured["frozen_manifest_file_count"] = len(frozen["files"])
canon_ev = json.loads((ROOT / EVIDENCE).read_text())
enr_ev = json.loads((ROOT / ENRICHED_COPY).read_text())
measured["canonical_evidence_fields"] = sorted(canon_ev.keys())
measured["enriched_evidence_fields"] = sorted(enr_ev.keys())
measured["enriched_embedded_tree_hashes"] = {
    "map_taxonomy_sha256": enr_ev.get("map_taxonomy_sha256"),
    "lead_contract_sha256": enr_ev.get("lead_contract_sha256"),
    "matches_measured_map": enr_ev.get("map_taxonomy_sha256") == measured["f0_canonical_sha256"],
    "matches_measured_supplement": enr_ev.get("lead_contract_sha256") == measured["f0_supplement_sha256"],
}
report["measured"] = measured

decl_all = {n: measured["schemas"][n]["declared_consistency_evidence_sha256"] for n in SCHEMAS}
report["defect"] = {
    "statement": "All three frozen class schemas declare the consistency evidence at 675a99d0, "
                 "the canonical path measures 9e335e9b, and FROZEN rev28 pins 9e335e9b. The declared "
                 "hash is the enriched evidence format (tree hashes + measured_at); the canonical "
                 "bytes are the checker's hash-less summary format.",
    "declarations_all_equal_675a99d0": all(v == DECLARED for v in decl_all.values()),
    "declarations": decl_all,
    "declared_equals_canonical": measured["evidence_canonical_sha256"] == DECLARED,
    "canonical_equals_frozen_pin": measured["evidence_canonical_sha256"] == measured["frozen_evidence_pin"]["sha256"],
    "enriched_copy_equals_declared": measured["enriched_candidate_sha256"] == DECLARED,
    "canonical_format_lacks_tree_hashes": "map_taxonomy_sha256" not in canon_ev,
    "checked_at": measured["schemas"]["F1"]["checked_at"],
}

# ---------------------------------------------------------------- root cause
checker_text = (ROOT / CHECKER).read_text()
write_block = 'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\nout.write_text(json.dumps(rep, indent=2)+"\\n")'
report["root_cause"] = {
    "checker_lines": [i + 1 for i, l in enumerate(checker_text.splitlines()) if "out.write_text" in l],
    "unconditional_write_block_present": write_block in checker_text,
    "output_dict_has_hash_fields": ("map_taxonomy_sha256" in checker_text.split("out.write_text")[0]),
    "explanation": "check_taxonomy_consistency.py ends by writing its summary dict unconditionally to the "
                   "canonical evidence path; the summary dict contains no sha256 of either compared tree, so any "
                   "run overwrites the enriched evidence (which carried map_taxonomy_sha256 / lead_contract_sha256 / "
                   "measured_at) with the weaker format. The three schemas still declare the enriched hash.",
}

# ---------------------------------------------------------------- experiment A: clobber + determinism
sbox = HERE / "sandboxes"
mirror(sbox / "a", [F0_CANON, F0_SUPP, "artifacts/formulation/VOCAB_ALIASES.json", CHECKER],
       evidence_bytes=(ROOT / ENRICHED_COPY).read_bytes())
exp_a = {"pre_hash": sha256(sbox / "a" / EVIDENCE)}
exp_a["run1"] = run([str(sbox / "a" / CHECKER)])
exp_a["post_hash_run1"] = sha256(sbox / "a" / EVIDENCE)
exp_a["clobbered"] = exp_a["post_hash_run1"] != exp_a["pre_hash"]
exp_a["post_equals_canonical_summary"] = exp_a["post_hash_run1"] == measured["evidence_canonical_sha256"]
exp_a["run2_idempotent"] = run([str(sbox / "a" / CHECKER)])
exp_a["post_hash_run2"] = sha256(sbox / "a" / EVIDENCE)
exp_a["idempotent"] = exp_a["post_hash_run2"] == exp_a["post_hash_run1"]
post_fields = sorted(json.loads((sbox / "a" / EVIDENCE).read_text()).keys())
exp_a["fields_after"] = post_fields
exp_a["enriched_fields_lost"] = sorted(set(measured["enriched_evidence_fields"]) - set(post_fields))
# sensitivity control M1: corrupt a compared token, checker must fail and record inconsistent
good_map = (sbox / "a" / F0_CANON).read_bytes()
bad = good_map.replace(b'family: "WCC"', b'family: "SCC"', 1)
(sbox / "a" / F0_CANON).write_bytes(bad)
exp_a["mutation_control"] = run([str(sbox / "a" / CHECKER)])
exp_a["mutation_evidence"] = json.loads((sbox / "a" / EVIDENCE).read_text())
exp_a["mutation_detected"] = (exp_a["mutation_control"]["exit"] != 0
                              and exp_a["mutation_evidence"].get("consistent") is False)
(sbox / "a" / F0_CANON).write_bytes(good_map)  # restore sandbox only
report["experiment_a_clobber_and_determinism"] = exp_a

# ---------------------------------------------------------------- experiment P: minimal checker patch
patched = checker_text.replace(
    "import json, sys, yaml",
    "import json, sys, yaml, hashlib\nfrom datetime import datetime, timezone",
)
new_block = (
    'rep["map_taxonomy_sha256"] = hashlib.sha256((ROOT/"research_map/formulation_taxonomy.yaml").read_bytes()).hexdigest()\n'
    'rep["lead_contract_sha256"] = hashlib.sha256((ROOT/"artifacts/formulation/formulation_taxonomy.yaml").read_bytes()).hexdigest()\n'
    'rep["measured_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")\n'
    'if "--write" in sys.argv:\n'
    '    out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
    '    out.write_text(json.dumps(rep, indent=2)+"\\n")'
)
patched_ok = write_block in patched
patched = patched.replace(write_block, new_block)
mirror(sbox / "p", [F0_CANON, F0_SUPP, "artifacts/formulation/VOCAB_ALIASES.json", CHECKER],
       evidence_bytes=(ROOT / ENRICHED_COPY).read_bytes())
(sbox / "p" / CHECKER).write_text(patched)
exp_p = {"patch_applied": patched_ok and patched != checker_text}
before = sha256(sbox / "p" / EVIDENCE)
exp_p["dry_run"] = run([str(sbox / "p" / CHECKER)])           # no --write
exp_p["dry_run_hash_unchanged"] = sha256(sbox / "p" / EVIDENCE) == before
exp_p["write_run"] = run([str(sbox / "p" / CHECKER), "--write"])
after = json.loads((sbox / "p" / EVIDENCE).read_text())
exp_p["written_hash"] = sha256(sbox / "p" / EVIDENCE)
exp_p["write_adds_tree_hashes"] = (
    after.get("map_taxonomy_sha256") == measured["f0_canonical_sha256"]
    and after.get("lead_contract_sha256") == measured["f0_supplement_sha256"]
    and bool(after.get("measured_at"))
)
exp_p["patched_evidence_still_consistent"] = after.get("consistent") is True
diff = "".join(difflib.unified_diff(
    checker_text.splitlines(keepends=True), patched.splitlines(keepends=True),
    fromfile="a/" + CHECKER, tofile="b/" + CHECKER))
(HERE / "proposed_checker_patch.diff").write_text(diff)
exp_p["patch_file"] = "proposed_checker_patch.diff"
report["experiment_p_checker_patch"] = exp_p

# ---------------------------------------------------------------- experiment C: restore-enriched option
frozen_rels = list(frozen["files"].keys()) + [VERIFY, FROZEN]
mirror(sbox / "c", frozen_rels, evidence_bytes=(ROOT / ENRICHED_COPY).read_bytes())
exp_c = {"verify_rev28_with_restored_evidence": run([str(sbox / "c" / VERIFY)])}
exp_c["restore_drift_count"] = exp_c["verify_rev28_with_restored_evidence"]["stdout"].count("DRIFT")
exp_c["restore_missing_count"] = exp_c["verify_rev28_with_restored_evidence"]["stdout"].count("MISSING")
# simulate the one-file re-freeze (revision 29): re-pin only the evidence entry
rec = dict(frozen["files"][EVIDENCE])
rec["sha256"] = DECLARED
rec["bytes"] = (ROOT / ENRICHED_COPY).stat().st_size
mirror(sbox / "c2", frozen_rels, evidence_bytes=(ROOT / ENRICHED_COPY).read_bytes(),
       frozen_edit={EVIDENCE: rec})
exp_c["verify_after_one_file_repin"] = run([str(sbox / "c2" / VERIFY)])
exp_c["schema_hashes_after_restore"] = {n: sha256(sbox / "c2" / rel) for n, rel in SCHEMAS.items()}
exp_c["schema_hashes_unchanged_by_restore"] = all(
    exp_c["schema_hashes_after_restore"][n] == measured["schemas"][n]["sha256"] for n in SCHEMAS)
report["experiment_c_restore_enriched"] = exp_c

# ---------------------------------------------------------------- experiment B: refresh-declaration option
mirror(sbox / "b", frozen_rels, evidence_bytes=(ROOT / EVIDENCE).read_bytes())
p = sbox / "b" / SCHEMAS["F1"]
txt = p.read_text()
exp_b = {"declaration_occurrences": txt.count(DECLARED)}
p.write_text(txt.replace(DECLARED, measured["evidence_canonical_sha256"]))
exp_b["new_f1_sha256"] = sha256(p)
exp_b["new_f1_moved"] = exp_b["new_f1_sha256"] != measured["schemas"]["F1"]["sha256"]
exp_b["verify_rev28_after_refresh"] = run([str(sbox / "b" / VERIFY)])
exp_b["refresh_drift_paths"] = [l.strip() for l in exp_b["verify_rev28_after_refresh"]["stdout"].splitlines() if "DRIFT" in l]
report["experiment_b_refresh_declaration"] = exp_b

# ---------------------------------------------------------------- options matrix
report["options"] = [
    {"id": "O1-restore-enriched-and-repin",
     "action": "put the enriched bytes (675a99d0) back at the canonical evidence path; re-freeze with a manifest "
               "revision that re-pins only that entry",
     "schema_hashes_move": False,
     "verdicts_voided": "none from the schema hash move; only the evidence-pin hard failures close",
     "machine_checked": {
         "restore_causes_exactly_one_frozen_drift": exp_c["restore_drift_count"] == 1 and exp_c["restore_missing_count"] == 0,
         "one_file_repin_gives_zero_problems": "0 problems" in exp_c["verify_after_one_file_repin"]["stdout"],
         "schema_hashes_unchanged": exp_c["schema_hashes_unchanged_by_restore"],
     },
     "residual_risk": "recurrence: the next run of the unguarded checker re-clobbers the file"},
    {"id": "O2-refresh-declarations",
     "action": "edit the three schemas' f0_binding.consistency_evidence_sha256 to 9e335e9b and re-freeze",
     "schema_hashes_move": True,
     "verdicts_voided": "all rev12 verdicts for F1/F2a/F2b (3 schema hashes move)",
     "machine_checked": {
         "f1_hash_moves": exp_b["new_f1_moved"],
         "rev28_manifest_reports_schema_drift": any(SCHEMAS["F1"] in l for l in exp_b["refresh_drift_paths"]),
     },
     "residual_risk": "evidence keeps the weaker hash-less format; the binding remains uninformative"},
    {"id": "O3-patch-checker-then-O1",
     "action": "apply the minimal guard patch (write only with --write; add tree hashes + measured_at), then O1: "
               "restore the EXISTING enriched bytes 675a99d0 at the canonical path (do not regenerate) and re-pin the "
               "evidence entry plus the patched-checker entry in one manifest revision",
     "schema_hashes_move": False,
     "verdicts_voided": "none from the schema hash move",
     "machine_checked": {
         "dry_run_does_not_write": exp_p["dry_run_hash_unchanged"],
         "write_adds_tree_hashes": exp_p["write_adds_tree_hashes"],
         "patch_applies_cleanly": exp_p["patch_applied"],
     },
     "residual_risk": "checker bytes change -> FROZEN checker pin must be re-pinned in the same re-freeze. A --write "
                      "regeneration produces a NEW enriched hash (measured_at is wall-clock; observed 2728cf474774 in "
                      "the sandbox), which would require refreshing the three declarations (O2) and voiding the rev12 "
                      "verdicts - so regenerate only if that cost is accepted"},
    {"id": "O4-keep-summary-and-drop-declaration",
     "action": "remove/neutralize the consistency_evidence_sha256 declaration in the three schemas and record the "
               "hash-less evidence as non-binding",
     "schema_hashes_move": True,
     "verdicts_voided": "all rev12 verdicts (schemas move) and the binding loses its hash anchor by design",
     "machine_checked": None,
     "residual_risk": "weakest evidence; reviewers have treated the hash-bound declaration as a gate criterion"},
]
report["recommendation"] = (
    "O3 (patch the checker guard, then O1 with the existing bytes): restore the existing enriched evidence 675a99d0 at "
    "the canonical path, re-pin that entry and the patched checker in one re-freeze. It closes the false declaration "
    "without moving any class-schema hash, so the rev12 verdict binding survives, and the guard prevents recurrence. "
    "The key ordering constraint: do NOT regenerate the evidence with --write unless you are prepared to refresh the "
    "three declarations, because a regenerated file carries a new measured_at and therefore a new hash. O2 is strictly "
    "more expensive (3 schema hashes move, all rev12 verdicts void) and leaves the weaker evidence format. Owner: "
    "lead-formulation (freeze-hold card); review re-issue: lead-audit."
)

# ---------------------------------------------------------------- controls + drift
report["controls"] = [
    {"id": "C-A1", "check": "enriched sandbox pre-hash equals declared 675a99d0", "pass": exp_a["pre_hash"] == DECLARED},
    {"id": "C-A2", "check": "checker exits 0 on consistent inputs", "pass": exp_a["run1"]["exit"] == 0},
    {"id": "C-A3", "check": "post-run evidence is byte-identical to the canonical summary", "pass": exp_a["post_equals_canonical_summary"]},
    {"id": "C-A4", "check": "second checker run is idempotent", "pass": exp_a["idempotent"]},
    {"id": "C-A5", "check": "enriched-only fields are gone after the clobber", "pass": bool(exp_a["enriched_fields_lost"])},
    {"id": "C-M1", "check": "mutated taxonomy is detected (exit != 0, consistent=false)", "pass": exp_a["mutation_detected"]},
    {"id": "C-P1", "check": "patched checker without --write does not touch the evidence file", "pass": exp_p["dry_run_hash_unchanged"]},
    {"id": "C-P2", "check": "patched --write emits tree hashes matching measured trees", "pass": exp_p["write_adds_tree_hashes"]},
    {"id": "C-C1", "check": "restored enriched evidence yields exactly one rev28 drift and no missing files",
     "pass": exp_c["restore_drift_count"] == 1 and exp_c["restore_missing_count"] == 0},
    {"id": "C-C2", "check": "re-pinning that single entry gives a clean manifest",
     "pass": "0 problems" in exp_c["verify_after_one_file_repin"]["stdout"]},
    {"id": "C-B1", "check": "refreshing the F1 declaration moves the F1 schema hash", "pass": exp_b["new_f1_moved"]},
    {"id": "C-B2", "check": "rev28 manifest detects the refreshed schema as drift", "pass": bool(exp_b["refresh_drift_paths"])},
]
report["controls_all_pass"] = all(c["pass"] for c in report["controls"])

end = {rel: sha256(ROOT / rel) for rel in start}
report["canonical_drift"] = {rel: {"before": start[rel], "after": end[rel], "moved": start[rel] != end[rel]}
                             for rel in start}
report["canonical_untouched"] = all(not v["moved"] for v in report["canonical_drift"].values())
report["falsifier"] = (
    "Re-run this script. Falsified if: (a) the declared evidence hash equals the canonical evidence hash at the three "
    "schemas and the FROZEN pin; (b) a checker run on consistent inputs changes nothing at the evidence path or emits "
    "tree hashes; (c) a mutated taxonomy is not detected; (d) restoring the enriched bytes does not produce exactly one "
    "rev28 drift with no missing files; (e) re-pinning that entry does not yield a clean manifest; (f) any canonical "
    "hash moved during the run."
)
report["finished_at"] = NOW()

# ---------------------------------------------------------------- emit
OUT.mkdir(parents=True, exist_ok=True)
rep_path = OUT / "report.json"
rep_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")

# pinned snapshots of the two evidence formats for byte-level evidence
snap = OUT / "snapshots"
snap.mkdir(exist_ok=True)
(snap / "taxonomy_consistency.enriched.675a99d0.json").write_bytes((ROOT / ENRICHED_COPY).read_bytes())
(snap / "taxonomy_consistency.canonical.9e335e9b.json").write_bytes((ROOT / EVIDENCE).read_bytes())

hashes = {
    "report.json": sha256(rep_path),
    "adjudicate.py": sha256(HERE / "adjudicate.py"),
    "proposed_checker_patch.diff": sha256(HERE / "proposed_checker_patch.diff"),
    "snapshots/taxonomy_consistency.enriched.675a99d0.json": sha256(snap / "taxonomy_consistency.enriched.675a99d0.json"),
    "snapshots/taxonomy_consistency.canonical.9e335e9b.json": sha256(snap / "taxonomy_consistency.canonical.9e335e9b.json"),
}
checkpoint = {
    "task_id": report["task_id"], "worker": "worker-096", "at": NOW(),
    "class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "gate": "G-FORM",
    "target": {"path": SCHEMAS["F1"], "sha256": measured["schemas"]["F1"]["sha256"],
               "frozen_revision": measured["frozen_revision"]},
    "verdict": "revise (evidence-binding criterion)",
    "controls_all_pass": report["controls_all_pass"],
    "canonical_untouched": report["canonical_untouched"],
    "artifacts": hashes,
    "recommendation": report["recommendation"],
    "falsifier": report["falsifier"],
}
(OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
hashes["CHECKPOINT.json"] = sha256(OUT / "CHECKPOINT.json")
print(json.dumps({"controls_all_pass": report["controls_all_pass"],
                  "canonical_untouched": report["canonical_untouched"],
                  "target_f1": measured["schemas"]["F1"]["sha256"][:12],
                  "declared": DECLARED[:12], "canonical": measured["evidence_canonical_sha256"][:12],
                  "frozen_pin": measured["frozen_evidence_pin"]["sha256"][:12],
                  "artifacts": hashes}, indent=2))
sys.exit(0 if report["controls_all_pass"] and report["canonical_untouched"] else 2)
