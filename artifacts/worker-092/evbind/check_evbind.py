#!/usr/bin/env python3
"""W092-EVBIND-01: independent binding-regression determination + repair-direction adjudication.

Question under test (G-FORM, classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN):
the three rev12 schemas declare f0_binding.consistency_evidence_sha256 = 675a99d0..., while the
canonical evidence path artifacts/formulation/evidence/taxonomy_consistency.json measures
9e335e9b...  Which revision is the *bound* one, what caused the divergence, and which of the two
repairs recorded in the review record (re-stamp the schemas to the live hash vs restore the
declared document) preserves the F0/lead-contract binding chain?

Method (all deterministic, no network, no writes to any live gate-bound path):
  P1  measure live F0 / lead-contract / evidence / schema / FROZEN hashes;
  P2  verify each schema's declared f0 and evidence hashes against the live bytes;
  P3  verify the declared document exists byte-exactly at the worker-086 pinned copy and read its
      embedded input-tree digests (map_taxonomy_sha256, lead_contract_sha256, measured_at);
  P4  staged replay of the FROZEN-pinned checker on pinned inputs (live inputs): confirm the live
      document is exactly that tool's output and that the output omits the three binding fields;
  P5  determinism control (same input -> same bytes) and negative control (class mutation ->
      INCONSISTENT, exit 1), so a PASS on P4 is meaningful;
  P6  restore simulation: the pinned 675a99d0 bytes resolve the schemas' declared citation at the
      canonical path in a staged tree, with zero schema-byte change;
  P7  verdict-retirement census: review files binding the live schema hashes, with verdicts;
  P8  entry==exit hash guard over every live artifact measured.

Exit 0 iff every check is PASS and the verdict is regression_confirmed; any drift is a
MISMATCH/FAIL and a non-zero exit.  Worker output only: no gate verdict, no node status.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # <repo>/artifacts/worker-092/evbind -> <repo>
PIN = HERE / "pinned"
STAGE = HERE / "stage"
REPORT = HERE / "report.json"

# Expectations frozen at authoring time (2026-09-12T00:40+08:00). A live byte move -> MISMATCH.
E = {
    "F0_canonical": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "lead_contract": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "evidence_live": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "evidence_declared": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    "schema_F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schema_F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schema_F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "frozen_rev": 28,
    "frozen_evidence_pin": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "frozen_lead_contract_pin": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}

SCHEMAS = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "schema_F1"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "schema_F2a"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "schema_F2b"),
}
LIVE_PATHS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
BINDING_FIELDS = ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


class Audit:
    def __init__(self) -> None:
        self.checks: dict[str, dict] = {}
        self.notes: list[str] = []

    def check(self, cid: str, observed, expected, ok: bool | None = None) -> None:
        ok = (observed == expected) if ok is None else ok
        self.checks[cid] = {
            "observed": observed,
            "expected": expected,
            "status": "PASS" if ok else "MISMATCH",
        }

    def note(self, cid: str, status: str, text: str, **extra) -> None:
        self.checks[cid] = {"status": status, "note": text, **extra}

    @property
    def failed(self) -> list[str]:
        return [k for k, v in self.checks.items() if v["status"] in ("MISMATCH", "FAIL")]


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text())


def stage_tree(base: Path, tool_src: Path, taxonomy_src: Path, contract_src: Path, vocab_src: Path) -> Path:
    """Build an isolated tree whose parents[3] is `base` for the pinned checker."""
    for sub in ("research_map", "artifacts/formulation/tools", "artifacts/formulation/evidence"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(taxonomy_src, base / "research_map/formulation_taxonomy.yaml")
    shutil.copy2(contract_src, base / "artifacts/formulation/formulation_taxonomy.yaml")
    shutil.copy2(vocab_src, base / "artifacts/formulation/VOCAB_ALIASES.json")
    shutil.copy2(tool_src, base / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    return base / "artifacts/formulation/tools/check_taxonomy_consistency.py"


def run_stage(tool: Path) -> tuple[int, str, Path]:
    out = tool.parents[1] / "evidence/taxonomy_consistency.json"
    if out.exists():
        out.unlink()
    pr = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=120)
    return pr.returncode, (pr.stdout + pr.stderr).strip(), out


def census_reviews() -> dict:
    """Count reviews/*.json that bind each live schema hash, with their verdicts."""
    current = {v[0]: E[v[1]] for v in SCHEMAS.values()}
    hits: dict[str, dict] = {p: {} for p in current}

    def walk(o, found: set):
        if isinstance(o, dict):
            if set(o) >= {"path", "sha256"} and str(o["path"]) in current:
                if str(o["sha256"]) == current[str(o["path"])]:
                    found.add(str(o["path"]))
            for v in o.values():
                walk(v, found)
        elif isinstance(o, list):
            for v in o:
                walk(v, found)

    for f in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        found: set = set()
        walk(d, found)
        full = f.read_text()
        for p, h in current.items():
            if p in found:
                hits[p][f.name] = {"verdict": d.get("verdict"),
                                   "counts_as_independent": d.get("counts_as_independent"),
                                   "binding": "structural"}
            elif h[:24] in full:
                hits[p].setdefault(f.name, {"verdict": d.get("verdict"),
                                            "counts_as_independent": d.get("counts_as_independent"),
                                            "binding": "text_only"})
    clean = {}
    union: dict[str, dict] = {}
    for p, rows in hits.items():
        structural = {k: v for k, v in rows.items() if v["binding"] == "structural"}
        text_only = {k: v for k, v in rows.items() if v["binding"] == "text_only"}
        union.update(structural)
        verdicts = [r["verdict"] for r in structural.values()]
        clean[p] = {"files_structural": sorted(structural), "n_structural": len(structural),
                    "verdicts_structural": verdicts,
                    "n_accept": verdicts.count("accept"), "n_revise": verdicts.count("revise"),
                    "n_independent": sum(1 for r in structural.values() if r.get("counts_as_independent")),
                    "files_text_only_reference": sorted(text_only), "n_text_only": len(text_only)}
    uv = [r["verdict"] for r in union.values()]
    clean["_dedup_union"] = {"files": sorted(union), "n_files": len(union),
                             "n_accept": uv.count("accept"), "n_revise": uv.count("revise")}
    return clean


def main() -> int:
    a = Audit()
    live_before = {p: sha(ROOT / p) for p in LIVE_PATHS}
    created = now()

    # ---- P1/P2: live measurements and schema declarations -------------------------------
    a.check("P1_F0_canonical", live_before["research_map/formulation_taxonomy.yaml"], E["F0_canonical"])
    a.check("P1_lead_contract", live_before["artifacts/formulation/formulation_taxonomy.yaml"], E["lead_contract"])
    live_ev = live_before["artifacts/formulation/evidence/taxonomy_consistency.json"]
    a.check("P1_evidence_live", live_ev, E["evidence_live"])
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    a.check("P1_frozen_rev", frozen.get("revision"), E["frozen_rev"])
    a.check("P1_frozen_evidence_pin", frozen["files"]["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"], E["frozen_evidence_pin"])
    a.check("P1_frozen_lead_contract_pin", frozen["files"]["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"], E["frozen_lead_contract_pin"])

    declared = {}
    for node, (rel, _) in SCHEMAS.items():
        sch = load_yaml(ROOT / rel)
        fb = sch["f0_binding"]
        declared[node] = {
            "declared_f0_sha256": fb["declared_f0_sha256"],
            "consistency_evidence": fb["consistency_evidence"],
            "consistency_evidence_sha256": fb["consistency_evidence_sha256"],
            "checked_at": fb.get("checked_at"),
        }
        a.check(f"P2_{node}_f0_matches_live", fb["declared_f0_sha256"], E["F0_canonical"])
        a.check(f"P2_{node}_evidence_declared", fb["consistency_evidence_sha256"], E["evidence_declared"])
        a.check(f"P2_{node}_evidence_mismatch_confirmed",
                fb["consistency_evidence_sha256"] != live_ev, True,
                ok=(fb["consistency_evidence_sha256"] == E["evidence_declared"] and live_ev == E["evidence_live"]))
        a.note(f"P2_{node}_defect", "DEFECT",
               "declared consistency evidence hash does not resolve at the canonical path",
               declared=fb["consistency_evidence_sha256"], live=live_ev)
    a.check("P2_declarations_uniform", len({v["consistency_evidence_sha256"] for v in declared.values()}), 1)

    # ---- P3: declared document survives at the worker-086 pinned copy -------------------
    oldp = PIN / "taxonomy_consistency.675a99d0.json"
    a.check("P3_declared_doc_pinned_hash", sha(oldp), E["evidence_declared"])
    old = json.loads(oldp.read_text())
    a.check("P3_old_binds_live_F0", old.get("map_taxonomy_sha256"), E["F0_canonical"])
    a.check("P3_old_binds_lead_contract", old.get("lead_contract_sha256"), E["lead_contract"])
    a.check("P3_old_binds_frozen_lead_contract", old.get("lead_contract_sha256"), E["frozen_lead_contract_pin"])
    a.check("P3_old_measured_at", old.get("measured_at"), "2026-09-12T00:32:02+08:00")
    a.check("P3_old_consistent", old.get("consistent"), True)
    live_json = json.loads((ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text())
    dropped = [f for f in BINDING_FIELDS if f in old and f not in live_json]
    a.check("P3_live_dropped_binding_fields", sorted(dropped), sorted(BINDING_FIELDS))
    a.check("P3_semantic_payload_unchanged",
            {k: live_json.get(k) for k in ("consistent", "errors", "contract_divergences", "classes_compared")},
            {k: old.get(k) for k in ("consistent", "errors", "contract_divergences", "classes_compared")})

    # ---- P4: staged replay of the FROZEN-pinned checker ---------------------------------
    tool_live = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    a.check("P4_pinned_tool_copy", sha(PIN / "check_taxonomy_consistency.py"), sha(tool_live))
    a.check("P4_frozen_tool_pin", frozen["files"]["artifacts/formulation/tools/check_taxonomy_consistency.py"]["sha256"], sha(tool_live))
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    tool = stage_tree(STAGE / "replay_live", PIN / "check_taxonomy_consistency.py",
                      PIN / "formulation_taxonomy.yaml", PIN / "formulation_taxonomy.lead_contract.yaml",
                      PIN / "VOCAB_ALIASES.json")
    rc1, out1, ev1 = run_stage(tool)
    a.check("P4_replay_exit", rc1, 0)
    a.check("P4_replay_stdout_consistent", out1.splitlines()[0][:10] if out1 else "", "CONSISTENT")
    a.check("P4_replay_bytes_equal_live_evidence", sha(ev1), live_ev)
    replay_json = json.loads(ev1.read_text())
    a.check("P4_replay_keys", sorted(replay_json), sorted(live_json))
    a.check("P4_replay_has_no_binding_fields", [f for f in BINDING_FIELDS if f in replay_json], [])
    # determinism
    rc2, out2, ev2 = run_stage(tool)
    a.check("P5_determinism_same_bytes", sha(ev2), sha(ev1))
    a.check("P5_determinism_same_exit", rc2, rc1)
    # negative control: mutate one class family in an isolated copy
    stage_tree(STAGE / "ctl_mutant", PIN / "check_taxonomy_consistency.py",
               PIN / "formulation_taxonomy.yaml", PIN / "formulation_taxonomy.lead_contract.yaml",
               PIN / "VOCAB_ALIASES.json")
    mut = STAGE / "ctl_mutant/research_map/formulation_taxonomy.yaml"
    import yaml as _yaml
    mut_doc = _yaml.safe_load(mut.read_text())
    before_family = mut_doc["classes"]["AF-WCC-VAC-GEN"]["axes"]["family"]
    mut_doc["classes"]["AF-WCC-VAC-GEN"]["axes"]["family"] = "SCC"
    mut.write_text(_yaml.safe_dump(mut_doc, sort_keys=True))
    a.note("P5_ctl_mutation_applied", "PASS" if before_family != "SCC" else "MISMATCH",
           "AF-WCC-VAC-GEN axes.family WCC->SCC in isolated copy", before=before_family, after="SCC")
    ctl_tool = STAGE / "ctl_mutant/artifacts/formulation/tools/check_taxonomy_consistency.py"
    rc3, out3, ev3 = run_stage(ctl_tool)
    a.check("P5_negative_control_exit", rc3, 1)
    a.check("P5_negative_control_inconsistent", json.loads(ev3.read_text()).get("consistent"), False)

    # ---- P6: restore simulation (no schema bytes change) --------------------------------
    stage_tree(STAGE / "restore", PIN / "check_taxonomy_consistency.py",
               PIN / "formulation_taxonomy.yaml", PIN / "formulation_taxonomy.lead_contract.yaml",
               PIN / "VOCAB_ALIASES.json")
    restored = STAGE / "restore/artifacts/formulation/evidence/taxonomy_consistency.json"
    shutil.copy2(oldp, restored)
    a.check("P6_restore_resolves_declared_hash", sha(restored), E["evidence_declared"])
    a.check("P6_restore_keeps_schema_bytes",
            {n: sha(ROOT / rel) for n, (rel, _) in SCHEMAS.items()},
            {"F1": E["schema_F1"], "F2a": E["schema_F2a"], "F2b": E["schema_F2b"]})

    # ---- P7: verdict-retirement census --------------------------------------------------
    census = census_reviews()
    a.note("P7_verdict_census", "PASS", "reviews/*.json structurally binding the live rev12 schema hashes",
           per_schema=census,
           totals={"n_structural": sum(v["n_structural"] for k, v in census.items() if not k.startswith("_")),
                   "n_accept": sum(v["n_accept"] for k, v in census.items() if not k.startswith("_")),
                   "n_revise": sum(v["n_revise"] for k, v in census.items() if not k.startswith("_")),
                   "n_text_only": sum(v["n_text_only"] for k, v in census.items() if not k.startswith("_"))},
           totals_dedup=census["_dedup_union"])

    # ---- P8: entry==exit guard ----------------------------------------------------------
    live_after = {p: sha(ROOT / p) for p in LIVE_PATHS}
    a.check("P8_entry_exit_live_hashes_unchanged", live_after, live_before)

    # ---- verdict + adjudication ---------------------------------------------------------
    core = [v["status"] for k, v in a.checks.items()
            if k.startswith(("P1_", "P2_", "P3_", "P4_", "P5_", "P6_")) and v["status"] != "DEFECT"]
    verdict = "regression_confirmed" if all(s == "PASS" for s in core) else "inconclusive"
    adjudication = {
        "question": "which recorded repair preserves the F0/lead-contract binding chain at least cost?",
        "R1_restamp_schemas_to_live": {
            "action": "edit consistency_evidence_sha256 in all three schemas to 9e335e9b",
            "closes_hash_mismatch": True,
            "loses_binding_fields": sorted(dropped),
            "changes_schema_bytes": True,
            "retires_bound_reviews": census["_dedup_union"],
            "recurrence_addressed": False,
            "assessment": "rejected: discards the only document that binds F0 rev5 and the lead contract, "
                          "forces a FROZEN bump plus re-review of all three schemas, and leaves the destructive "
                          "writer in place",
        },
        "R2_restore_declared_document": {
            "action": "restore the 675a99d0 bytes at the canonical evidence path; bump only the FROZEN "
                      "evidence-path pin (schema bytes and their verdicts survive)",
            "source_bytes": "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json",
            "source_hash_verified": E["evidence_declared"],
            "changes_schema_bytes": False,
            "schema_reviews_survive": True,
            "frozen_paths_to_repin": ["artifacts/formulation/evidence/taxonomy_consistency.json"],
            "recurrence_addressed": False,
            "required_companion": "guard the writer: the FROZEN-pinned checker writes the canonical evidence "
                                  "path on every run, so any later execution reverts the restore",
            "assessment": "conditionally_recommended: minimum rework and recovers the binding; durable only "
                          "with the writer guard",
        },
        "R3_deterministic_generator": {
            "action": "patch the checker to emit map_taxonomy_sha256 + lead_contract_sha256 and drop the "
                      "wall-clock measured_at, then re-run, re-freeze and re-stamp the schemas",
            "changes_schema_bytes": True,
            "retires_bound_reviews": True,
            "recurrence_addressed": True,
            "assessment": "durable but costs a FROZEN bump plus re-review of all three schemas; choose only if "
                          "the current rev12 verdicts are to be re-opened anyway",
        },
        "recommended": "R2 + writer guard, unless the owner intends to re-open the rev12 verdicts (then R3)",
        "authority": "adjudication is advisory measurement; only the controller and group leads move gates",
    }
    report = {
        "task_id": "W092-EVBIND-01",
        "worker": "worker-092",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "kind": "independent binding-regression determination + repair-direction adjudication",
        "created_at": created,
        "verdict": verdict,
        "summary": ("the declared 675a99d0 evidence document is the bound revision: it embeds the live F0 rev5 "
                    "hash and the FROZEN-pinned lead-contract hash; the live 9e335e9b document is the exact "
                    "deterministic output of the FROZEN-pinned checker and drops those three fields. Re-stamping "
                    "the schemas to the live document would lose the binding and retire the reviews bound to the "
                    "rev12 schema hashes; restoring the declared bytes costs no schema change."),
        "declared_vs_live": {
            "per_schema": declared,
            "live_evidence_sha256": live_ev,
            "declared_evidence_sha256": E["evidence_declared"],
            "declared_binding_fields": {k: old.get(k) for k in BINDING_FIELDS},
            "live_present_binding_fields": [f for f in BINDING_FIELDS if f in live_json],
        },
        "mechanism": {
            "writer": "artifacts/formulation/tools/check_taxonomy_consistency.py (sha256 de356d999ea3...)",
            "writer_line": "out = ROOT/artifacts/formulation/evidence/taxonomy_consistency.json; out.write_text(...)",
            "augmenter": "artifacts/formulation/tools/close_findings_rev27.py (sha256 0234cd3cbda4...) sets "
                         "map_taxonomy_sha256 / lead_contract_sha256 / measured_at on the same path",
            "consequence": "the declared document is produced only by the augmenter; every execution of the "
                           "checker overwrites it with a document that cannot bind either input tree",
        },
        "checks": a.checks,
        "repair_adjudication": adjudication,
        "falsifiers": [
            "exhibit bytes at the canonical evidence path whose sha256 is 675a99d0... after this run "
            "(then the mismatch is closed and this verdict is retired)",
            "show the pinned checker output differs from the live evidence document (mechanism refuted)",
            "show a schema declaration other than 675a99d0... or a declared_f0 hash other than the live "
            "F0 rev5 hash (declaration set changed)",
            "produce a 675a99d0 document whose map_taxonomy_sha256 / lead_contract_sha256 do not match the "
            "live F0 and lead-contract bytes (binding claim refuted)",
            "show that re-stamping the three schemas leaves their sha256 values unchanged (retirement cost "
            "refuted)",
        ],
        "next_falsifier": "re-run this checker at the pinned hashes; it exits non-zero on any byte drift and "
                          "records entry==exit live hashes.",
        "authority": "measurement only; worker events cannot set node status, validation_status=passed, or a gate verdict",
        "inputs_pinned": {p: live_before[p] for p in LIVE_PATHS},
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"VERDICT {verdict}")
    print(f"CHECKS {sum(1 for v in a.checks.values() if v['status'] == 'PASS')}/{len(a.checks)} PASS")
    for k in a.failed:
        print("  MISMATCH", k, a.checks[k])
    print(f"REPORT {REPORT} sha256={sha(REPORT)[:16]}")
    return 0 if verdict == "regression_confirmed" and not a.failed else 1


if __name__ == "__main__":
    sys.exit(main())
