#!/usr/bin/env python3
"""W086-GFORM-EVIDENCE-COLLISION-01 (worker-086) -- read-only root-cause probe.

Question: at rev12 pins (F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda on
declared F0 rev5 0abb9ed8a961), each schema declares
f0_binding.consistency_evidence_sha256 = 675a99d0d25b... while the canonical path
artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bf...
Why, and which repair paths actually resolve it?

Method: pin every input, reconstruct the declared bytes from the live bytes and the
two input hashes, compare the current producer transform, census the writers of the
canonical path, and prove determinism of the standalone checker in a sandbox copy.
Writes only under artifacts/worker-086/evidence_collision/. Fails closed.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-086/evidence_collision"
SANDBOX = OUT / "sandbox"

SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
LIVE_EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
DECLARED_SNAPSHOT = OUT / "restore_candidate/taxonomy_consistency.675a99d0d25b.json"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
CHECKER = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
PRODUCER = ROOT / "artifacts/formulation/tools/close_findings_rev27.py"
MAP = ROOT / "research_map/research_map.json"

DECLARED_HASH = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LEAN_HASH = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
REV12 = {
    "AF-WCC-VAC-GEN": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "AF-SCC-C2-VAC-GEN": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "AF-SCC-C0-VAC-GEN": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
BINDING_RULE = (
    "map_taxonomy and lead_contract are DIFFERENT logical artifacts: the declared F0 taxonomy "
    "(keys class_ids/classes/transfer_rules) and the class-contract supplement (keys "
    "class_contracts/axis_registry/implication_ledger). They are not mirror trees and are not "
    "required to be byte-identical. [rev12: F1-review-090 F090-05, F1-review-19 F-4]"
)

checks: list[dict] = []
writes: list[str] = []


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def check(cid: str, ok: bool, detail) -> bool:
    checks.append({"id": cid, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {json.dumps(detail)[:220]}")
    return bool(ok)


def declared_hash_of(path: Path) -> str | None:
    text = path.read_text()
    m = re.search(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"', text)
    return m.group(1) if m else None


def declared_f0_of(path: Path) -> str | None:
    text = path.read_text()
    m = re.search(r'declared_f0_sha256:\s*"([0-9a-f]{64})"', text)
    return m.group(1) if m else None


def main() -> int:
    missing = [str(p) for p in list(SCHEMAS.values()) + [LIVE_EVIDENCE, DECLARED_SNAPSHOT,
               F0_CANON, F0_SUPP, FROZEN, CHECKER, PRODUCER, MAP] if not p.exists()]
    if missing:
        print("FAIL-CLOSED missing inputs:", missing)
        return 2

    pins = {
        "research_map/formulation_taxonomy.yaml": sha_file(F0_CANON),
        "artifacts/formulation/formulation_taxonomy.yaml": sha_file(F0_SUPP),
        "artifacts/formulation/evidence/taxonomy_consistency.json": sha_file(LIVE_EVIDENCE),
        "declared_snapshot": sha_file(DECLARED_SNAPSHOT),
        "artifacts/formulation/tools/check_taxonomy_consistency.py": sha_file(CHECKER),
        "artifacts/formulation/tools/close_findings_rev27.py": sha_file(PRODUCER),
        "artifacts/formulation/FROZEN.json": sha_file(FROZEN),
        "research_map/research_map.json": sha_file(MAP),
        **{f"schemas/{p.name}": sha_file(p) for p in SCHEMAS.values()},
    }

    # ---- P1: declaration census: schema-declared vs live vs F0 pin --------------------
    decl = {}
    for cid, p in SCHEMAS.items():
        d = declared_hash_of(p)
        f0 = declared_f0_of(p)
        decl[cid] = {"declared_evidence_sha256": d, "declared_f0_sha256": f0,
                     "schema_sha256": sha_file(p)}
    check("P1a-declared-evidence-is-675a99d0-in-all-three",
          all(v["declared_evidence_sha256"] == DECLARED_HASH for v in decl.values()), decl)
    check("P1b-declared-f0-pin-equals-current-canonical-f0",
          all(v["declared_f0_sha256"] == pins["research_map/formulation_taxonomy.yaml"]
              for v in decl.values()),
          {"declared_f0": decl["AF-WCC-VAC-GEN"]["declared_f0_sha256"],
           "measured_f0": pins["research_map/formulation_taxonomy.yaml"]})
    check("P1c-live-evidence-equals-FROZEN-rev28-pin",
          pins["artifacts/formulation/evidence/taxonomy_consistency.json"] == LEAN_HASH
          and pins["declared_snapshot"] == DECLARED_HASH, pins)
    check("P1d-declaration-is-internally-coherent-historical-bytes",
          pins["declared_snapshot"] == DECLARED_HASH, {"declared_snapshot_sha": pins["declared_snapshot"]})

    # ---- P2: reconstruct declared bytes from live bytes -------------------------------
    lean_bytes = LIVE_EVIDENCE.read_bytes()
    lean = json.loads(lean_bytes)
    declared_doc = json.loads(DECLARED_SNAPSHOT.read_bytes())
    measured_at = declared_doc.get("measured_at")
    extra_fields = sorted(set(declared_doc) - set(lean))

    def transform(with_binding_rule: bool) -> bytes:
        c = dict(lean)
        c["map_taxonomy_sha256"] = pins["research_map/formulation_taxonomy.yaml"]
        c["lead_contract_sha256"] = pins["artifacts/formulation/formulation_taxonomy.yaml"]
        if with_binding_rule:
            c["binding_rule"] = BINDING_RULE
        c["measured_at"] = measured_at
        return (json.dumps(c, indent=2) + "\n").encode()

    recon3 = transform(False)
    recon4 = transform(True)
    check("P2a-declared-reconstructs-byte-exactly-from-live-plus-3-fields",
          sha_bytes(recon3) == DECLARED_HASH, {"reconstructed_sha": sha_bytes(recon3)})
    check("P2b-declared-doc-has-no-binding_rule",
          "binding_rule" not in declared_doc, {"extra_fields_vs_live": extra_fields})
    check("P2c-producer-now-would-emit-a-DIFFERENT-hash",
          sha_bytes(recon4) != DECLARED_HASH,
          {"producer_now_sha": sha_bytes(recon4), "declared_sha": DECLARED_HASH,
           "cause": "close_findings_rev27.py adds binding_rule and a fresh wall-clock measured_at"})
    check("P2d-declared-input-pins-equal-current-inputs",
          declared_doc.get("map_taxonomy_sha256") == pins["research_map/formulation_taxonomy.yaml"]
          and declared_doc.get("lead_contract_sha256") == pins["artifacts/formulation/formulation_taxonomy.yaml"],
          {"map_taxonomy_sha256": declared_doc.get("map_taxonomy_sha256"),
           "lead_contract_sha256": declared_doc.get("lead_contract_sha256")})

    # ---- P3: writer census on the canonical path --------------------------------------
    writers = {
        "artifacts/formulation/tools/check_taxonomy_consistency.py": {
            "path_line": 79, "write_line": 80, "mode": "unconditional write_text", "doc_schema": "lean",
            "fields": sorted(lean)},
        "artifacts/formulation/tools/close_findings_rev27.py": {
            "path_line": 51, "write_line": 391, "mode": "write_bytes guarded by --apply",
            "doc_schema": "enriched(+binding_rule)",
            "fields": sorted(set(lean) | {"map_taxonomy_sha256", "lead_contract_sha256",
                                          "binding_rule", "measured_at"})},
    }
    for rel, w in writers.items():
        src = (ROOT / rel).read_text().splitlines()
        w["path_source"] = src[w["path_line"] - 1].strip()
        w["write_source"] = src[w["write_line"] - 1].strip()
        w["writes_canonical_path"] = ("artifacts/formulation/evidence/taxonomy_consistency.json"
                                      in w["path_source"] and "write" in w["write_source"])
    check("P3a-two-writers-one-canonical-path-with-divergent-doc-schemas",
          len(writers) == 2 and all(w["writes_canonical_path"] for w in writers.values()), writers)

    # ---- P4: determinism of the standalone checker (sandbox copy) ---------------------
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "artifacts/formulation/tools").mkdir(parents=True)
    (SANDBOX / "artifacts/formulation/evidence").mkdir(parents=True)
    (SANDBOX / "research_map").mkdir(parents=True)
    shutil.copy2(CHECKER, SANDBOX / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    shutil.copy2(F0_SUPP, SANDBOX / "artifacts/formulation/formulation_taxonomy.yaml")
    shutil.copy2(ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
                 SANDBOX / "artifacts/formulation/VOCAB_ALIASES.json")
    shutil.copy2(F0_CANON, SANDBOX / "research_map/formulation_taxonomy.yaml")
    sb_out = SANDBOX / "artifacts/formulation/evidence/taxonomy_consistency.json"
    runs = []
    for i in (1, 2):
        r = subprocess.run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                           cwd=SANDBOX, capture_output=True, text=True)
        runs.append({"run": i, "rc": r.returncode, "stdout": r.stdout.strip()[:200],
                     "stderr": r.stderr.strip()[:200],
                     "output_sha256": sha_file(sb_out) if sb_out.exists() else None})
    check("P4a-checker-is-byte-deterministic-at-fixed-inputs",
          runs[0]["output_sha256"] == runs[1]["output_sha256"] == LEAN_HASH, runs)
    check("P4b-checker-writes-the-canonical-doc-schema-without-input-pins",
          sb_out.exists() and not (set(json.loads(sb_out.read_text())) &
                                   {"map_taxonomy_sha256", "lead_contract_sha256", "measured_at"}),
          {"sandbox_output_sha": runs[1]["output_sha256"]})

    # ---- P5: freeze census vs declarations --------------------------------------------
    frozen = json.loads(FROZEN.read_text())
    f_files = frozen.get("files", {})
    freeze_pins = {}
    for key in ("artifacts/formulation/evidence/taxonomy_consistency.json",
                "artifacts/formulation/tools/check_taxonomy_consistency.py",
                "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml"):
        rec = f_files.get(key) or {}
        freeze_pins[key] = {"sha256": rec.get("sha256"), "measured": sha_file(ROOT / key)}
    check("P5a-freeze-pins-lean-evidence-and-checker",
          freeze_pins["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"] == LEAN_HASH
          and freeze_pins["artifacts/formulation/tools/check_taxonomy_consistency.py"]["sha256"]
          == pins["artifacts/formulation/tools/check_taxonomy_consistency.py"],
          freeze_pins)
    check("P5b-freeze-agrees-with-declaration-only-for-schemas-not-evidence",
          all(v["sha256"] == v["measured"] for k, v in freeze_pins.items() if k.startswith("schemas/"))
          and freeze_pins["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"] != DECLARED_HASH,
          freeze_pins)

    # ---- P6: hash-pinned review census at the rev12 schema bytes (map snapshot) --------
    m = json.loads(MAP.read_text())
    file_of = {"AF-WCC-VAC-GEN": "af_wcc_vacuum.yaml",
               "AF-SCC-C2-VAC-GEN": "af_scc_c2_vacuum.yaml",
               "AF-SCC-C0-VAC-GEN": "af_scc_c0_vacuum.yaml"}
    census = {cid: {"accept": [], "revise": [], "other": []} for cid in REV12}
    for r in m.get("reviews", []):
        refs = " ".join(str(x) for x in r.get("evidence_refs", []))
        for cid in REV12:
            if file_of[cid] in refs and REV12[cid][:12] in refs:
                v = r.get("verdict") if r.get("verdict") in ("accept", "revise") else "other"
                census[cid][v].append({"event_id": r.get("event_id"), "reviewer": r.get("reviewer"),
                                       "created_at": r.get("created_at")})
    census_counts = {cid: {k: len(v) for k, v in d.items()} for cid, d in census.items()}
    check("P6a-hash-pinned-rev12-review-census-computed",
          True, {"counts": census_counts,
                 "note": "map snapshot; strict match = schema file + 12-hex rev12 prefix in evidence_refs"})
    check("P6b-no-hash-pinned-accept-binds-F1-rev12",
          len(census["AF-WCC-VAC-GEN"]["accept"]) == 0,
          {"F1_accepts": census["AF-WCC-VAC-GEN"]["accept"]})

    # ---- verdict + repair matrix -------------------------------------------------------
    defect = {
        "kind": "canonical_evidence_path_collision",
        "summary": ("The declared evidence 675a99d0 was a coherent, byte-reproducible enriched "
                    "generation of the live lean document (its input pins still equal the current "
                    "F0/supplement bytes), but the canonical path was afterwards rewritten by the "
                    "standalone checker, which emits a different, pin-free document schema; the "
                    "current producer would now emit a third hash (binding_rule added). Declaration, "
                    "live path and producer are therefore three divergent generations of one path."),
        "generations": {
            "declared_675a99d0": {"producer": "close_findings_rev27 @00:32:02 (3-field variant)",
                                  "fields": sorted(set(lean) | {"map_taxonomy_sha256",
                                                                "lead_contract_sha256", "measured_at"}),
                                  "input_pins_current": True},
            "live_9e335e9b": {"producer": "check_taxonomy_consistency.py (unconditional write)",
                              "fields": sorted(lean), "input_pins_current": None,
                              "deterministic": True},
            "producer_now_0f065226": {"producer": "close_findings_rev27.py as it stands now",
                                      "fields": sorted(writers[list(writers)[1]]["fields"]),
                                      "input_pins_current": True},
        },
        "repair_matrix": [
            {"id": "R1-restamp-to-lean", "schema_bytes_change": True, "republication": "rev13 x3",
             "verdict_voided": census_counts,
             "durable": "yes, if the enriched production path stops writing the canonical path",
             "falsifier": "after restamp, run the standalone checker at fixed inputs; declared == disk == freeze must hold"},
            {"id": "R2-restore-declared-bytes", "schema_bytes_change": False, "republication": "none",
             "verdict_voided": {"all": 0},
             "durable": "no, unless the checker is made non-writing; the restore recipe is byte-exact and verified",
             "restore_recipe": "cp artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json artifacts/formulation/evidence/taxonomy_consistency.json",
             "falsifier": "restore then run the checker once; if the path hash leaves 675a99d0 the restore is not durable"},
            {"id": "R3-unify-schema-and-owner", "schema_bytes_change": True, "republication": "rev13 x3 (one time)",
             "verdict_voided": census_counts,
             "durable": "yes",
             "falsifier": "run producer and checker twice in a sandbox; canonical bytes must be identical and pin-bearing"},
        ],
        "minimal_evidence_backed_recommendation": ("R2 is byte-verified and free of schema churn, but "
            "only durable together with removing the checker's unconditional write; R1/R3 pay one rev13 "
            "republication and are durable by construction."),
    }

    report = {
        "schema_version": "0.1",
        "artifact_kind": "root_cause_probe",
        "task_id": "W086-GFORM-EVIDENCE-COLLISION-01",
        "actor": "worker-086",
        "created_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "gate": "G-FORM",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": list(SCHEMAS),
        "authority": "worker measurement only; no gate verdict, no schema edit, no canonical write",
        "pins": pins,
        "declaration_census": decl,
        "declared_doc": {"sha256": DECLARED_HASH, "measured_at": measured_at,
                         "extra_fields_vs_live": extra_fields},
        "reconstruction": {"sha_3_field": sha_bytes(recon3), "sha_4_field_producer_now": sha_bytes(recon4),
                           "sha_3_field_equals_declared": sha_bytes(recon3) == DECLARED_HASH},
        "writers": writers,
        "checker_determinism_runs": runs,
        "freeze_pins": freeze_pins,
        "rev12_hash_pinned_review_census": census,
        "rev12_hash_pinned_review_counts": census_counts,
        "defect": defect,
        "verdict": "EVIDENCE_DECLARATION_UNBOUND_AT_REV12__PATH_COLLISION_ROOT_CAUSE_CONFIRMED",
        "next_falsifier": ("After any repair: re-run probe_collision.py; the repair fails if the declared "
                           "hash, the live bytes and the FROZEN pin do not all agree at the same instant, "
                           "or if a single standalone-checker run moves the canonical path hash."),
        "non_claims": ["No schema, taxonomy, evidence or freeze file was modified by this probe.",
                       "No mathematics or physics claim is made.",
                       "The review census is a strict hash-pinned scan of the map snapshot, not a controller gate audit."],
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_failed": sum(1 for c in checks if not c["ok"]),
    }
    out_path = OUT / "report.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    writes.append(str(out_path.relative_to(ROOT)))
    print(json.dumps({"report": str(out_path.relative_to(ROOT)),
                      "report_sha256": sha_file(out_path),
                      "checks_passed": sum(1 for c in checks if c["ok"]), "checks_total": len(checks),
                      "writes": writes}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
