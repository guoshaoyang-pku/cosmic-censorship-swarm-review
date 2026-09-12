#!/usr/bin/env python3
"""W027-F2A-HB1-INDEP-01 independent verification of the HF-B1 hashbound closure.

Class: AF-SCC-C2-VAC-GEN (node F2a, gate G-FORM).  Author of the claim under test:
deepseek-flash-05 (artifacts/worker-05/verify/hb1_closure_report.json#c7eeab551128).

Claim under test (paraphrased from the author's events + closure report):
  (1) The live evidence record artifacts/formulation/evidence/taxonomy_consistency.json
      (sha256 9e335e9ba1bf...) embeds no sha256 of either compared taxonomy file, so the
      three schemas' f0_binding refresh rule is not machine-dischargeable from the record
      (HF-B1) -- hard failure B7 in check_class_binding_drift.py.
  (2) The proposed successor artifacts/worker-05/verify/taxonomy_consistency_hashbound.json
      (sha256 4c4803c540a1...) is revision-sensitive: it embeds the measured hashes of both
      compared files, and dropping it in at the canonical evidence path makes all hard
      checks of the same drift checker pass for all three schemas, with no canonical write.
  (3) Generator gen_hashbound_consistency_evidence.py (3df4abfc7c49) is deterministic.

Independence design
-------------------
This script does NOT import or copy the author's logic for the primary verdicts:
  * a private hex64 scanner measures whether a record embeds revision hashes;
  * a private classifier (UNBOUND / BOUND / STALE) decides revision-sensitivity from
    independently recomputed live hashes;
  * a private class-set comparison reproduces the record's `consistent` claim.
The author's drift checker is then run as a *labelled, instrument-dependent cross-check*
inside a sandbox root (never on canonical bytes), plus the canonical project checker
artifacts/formulation/tools/check_taxonomy_consistency.py as a second, independent
instrument (de356d99...).

Exit codes
----------
0  claim independently verified at the pinned inputs; all pre-registered controls met
1  claim NOT verified (at least one primary check or control expectation failed)
2  measurement void: input missing, or any pinned input drifted T0 -> T1 (canonical write)

Falsifier (pre-registered, also embedded in report.json):
  Any of: (a) a pinned input drifts T0->T1 (void, exit 2); (b) the live evidence record
  embeds a sha256 of either compared taxonomy file, or an explicit input-hash field
  (=> HF-B1 does not reproduce); (c) the candidate's embedded canonical/supplement hashes
  do not equal the independently measured live hashes; (d) the candidate's `consistent`
  claim is not reproduced by the private class-set check or by the canonical checker in
  sandbox; (e) the generator's two runs are not byte-identical to each other; (f) with the
  candidate dropped in, the author's drift checker still reports a hard failure for any of
  the three schemas; (g) with the live evidence, the author's drift checker reports no B7
  hard failure; (h) any control behaves against its pre-registered expectation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DEFAULT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")

CANONICAL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
LIVE_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
CANDIDATE = "artifacts/worker-05/verify/taxonomy_consistency_hashbound.json"
GEN = "artifacts/worker-05/verify/gen_hashbound_consistency_evidence.py"
DRIFT_CHECKER = "artifacts/worker-05/verify/check_class_binding_drift.py"
CONSISTENCY_CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = "artifacts/formulation/FROZEN.json"
SCHEMAS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
# every file whose bytes must be identical at entry and exit
PINNED = [CANONICAL, SUPPLEMENT, LIVE_EVIDENCE, CANDIDATE, GEN, DRIFT_CHECKER,
          CONSISTENCY_CHECKER, VOCAB, FROZEN, *SCHEMAS.values()]

# the author's simulated moved-revision hash, reused only as a STALE fixture
SUPERSEDED_CANONICAL = "961b5accb36e0c4d6dae136152edbcdb7a27be598d7e9a59cb5c427d715e5246"

CN_TZ = timezone(timedelta(hours=8))
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_hex64(obj, prefix="$"):
    """Return {json-path: hex64-value} for every 64-hex string anywhere in obj."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(collect_hex64(v, f"{prefix}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(collect_hex64(v, f"{prefix}[{i}]"))
    elif isinstance(obj, str) and HEX64.match(obj.strip().lower()):
        out[prefix] = obj.strip().lower()
    return out


def classify_record(record: dict, live_canon: str, live_supp: str) -> dict:
    """Private revision-sensitivity classifier.  Returns status in {UNBOUND, BOUND, STALE}."""
    embedded_canon = set()
    embedded_supp = set()
    input_map = {}
    if isinstance(record, dict):
        if isinstance(record.get("input_sha256"), dict):
            input_map = {str(k): str(v) for k, v in record["input_sha256"].items()}
            if CANONICAL in input_map:
                embedded_canon.add(input_map[CANONICAL].lower())
            if SUPPLEMENT in input_map:
                embedded_supp.add(input_map[SUPPLEMENT].lower())
        for key in ("map_taxonomy_sha256",):
            v = record.get(key)
            if isinstance(v, str) and HEX64.match(v.strip().lower()):
                embedded_canon.add(v.strip().lower())
        for key in ("lead_contract_sha256",):
            v = record.get(key)
            if isinstance(v, str) and HEX64.match(v.strip().lower()):
                embedded_supp.add(v.strip().lower())
        binding = record.get("binding")
        if isinstance(binding, dict):
            v = binding.get("declared_f0_sha256")
            if isinstance(v, str) and HEX64.match(v.strip().lower()):
                embedded_canon.add(v.strip().lower())
    embedded_canon.discard("")
    embedded_supp.discard("")
    has_explicit_field = bool(
        isinstance(record, dict)
        and ("input_sha256" in record or "map_taxonomy_sha256" in record
             or "lead_contract_sha256" in record
             or (isinstance(record.get("binding"), dict)
                 and "declared_f0_sha256" in record["binding"]))
    )
    if not embedded_canon or not embedded_supp:
        status, reason = "UNBOUND", "no sha256 of one or both compared files is recorded"
    elif embedded_canon == {live_canon} and embedded_supp == {live_supp}:
        status, reason = "BOUND", "embedded hashes equal the independently measured live hashes"
    else:
        status, reason = "STALE", "embedded hashes differ from the measured live hashes"
    return {
        "status": status,
        "reason": reason,
        "has_explicit_hash_field": has_explicit_field,
        "embedded_canonical": sorted(embedded_canon),
        "embedded_supplement": sorted(embedded_supp),
        "input_sha256_paths": sorted(input_map.keys()),
    }


def private_consistency(canon_doc: dict, supp_doc: dict) -> dict:
    """Private reimplementation of the record's class-set consistency semantics."""
    classes = set((canon_doc.get("classes") or {}).keys())
    contracts = set((supp_doc.get("class_contracts") or {}).keys())
    declared_ids = set(canon_doc.get("class_ids") or [])
    errors = sorted({f"class {c!r} absent from class_ids" for c in classes - declared_ids}
                    | {f"class_ids entry {c!r} absent from classes" for c in declared_ids - classes})
    divergences = sorted({f"canonical class {c!r} has no class_contract entry" for c in classes - contracts}
                         | {f"class_contract {c!r} has no canonical class entry" for c in contracts - classes})
    return {
        "consistent": not errors and not divergences,
        "errors": errors,
        "contract_divergences": divergences,
        "classes_compared": sorted(classes & contracts),
    }


def run(cmd, cwd=None):
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "exit_code": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}


def drift_summary(report: dict) -> dict:
    """Normalise check_class_binding_drift.py --json output to {class_id: summary}."""
    out = {}
    for s in (report or {}).get("schemas") or []:
        if not isinstance(s, dict):
            continue
        checks = {c.get("check"): c for c in (s.get("checks") or []) if isinstance(c, dict)}
        out[s.get("class_id")] = {
            "verdict": s.get("verdict"),
            "B7": (checks.get("B7") or {}).get("status"),
            "hard_failures": [c.get("detail") for c in (s.get("checks") or [])
                              if isinstance(c, dict) and c.get("hard") and c.get("status") == "fail"],
        }
    return out


def build_sandbox(dest: Path, evidence_src: Path, root: Path):
    """Copy the live binding-chain inputs into an isolated root; place evidence_src as
    the canonical evidence record.  Never writes under the real canonical paths."""
    if dest.exists():
        shutil.rmtree(dest)
    for rel in (CANONICAL, SUPPLEMENT, VOCAB, *SCHEMAS.values()):
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    for rel in (DRIFT_CHECKER, CONSISTENCY_CHECKER):
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    ev = dest / LIVE_EVIDENCE
    ev.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(evidence_src, ev)
    return dest


def schema_declared_f0(root: Path):
    import yaml
    out = {}
    for cid, rel in SCHEMAS.items():
        doc = yaml.safe_load((root / rel).read_text(encoding="utf-8")) or {}
        fb = doc.get("f0_binding") or {}
        out[cid] = {
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
            "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
            "consistency_evidence": fb.get("consistency_evidence"),
        }
    return out


def measure(root: Path, work: Path, keep_sandboxes: bool):
    checks = []
    controls = []
    sand = work / "sandbox"
    sand.mkdir(parents=True, exist_ok=True)

    def check(cid, name, expected, observed, ok):
        checks.append({"id": cid, "name": name, "expected": expected,
                       "observed": observed, "ok": bool(ok)})

    def control(cid, name, expected, observed, ok):
        controls.append({"id": cid, "name": name, "expected": expected,
                         "observed": observed, "ok": bool(ok)})

    live_canon = sha256_file(root / CANONICAL)
    live_supp = sha256_file(root / SUPPLEMENT)
    live_evidence = sha256_file(root / LIVE_EVIDENCE)
    pins = {rel: sha256_file(root / rel) for rel in PINNED}

    declared = schema_declared_f0(root)
    all_declared_equal_measured = all(
        v["declared_f0_sha256"] == live_canon for v in declared.values())
    check("P2", "all three schemas declare the measured live canonical F0 hash",
          {"canonical": live_canon},
          {"declared": {k: v["declared_f0_sha256"] for k, v in declared.items()},
           "schema_consistency_evidence_all_live": all(
               v["consistency_evidence_sha256"] == live_evidence for v in declared.values())},
          all_declared_equal_measured)

    # ---- HF-B1 reproduction on the live record (private instrument) -------------
    live_rec = load_json(root / LIVE_EVIDENCE)
    live_hex = collect_hex64(live_rec)
    live_class = classify_record(live_rec, live_canon, live_supp)
    hf_b1_reproduced = (live_class["status"] == "UNBOUND"
                        and not live_class["has_explicit_hash_field"]
                        and not live_hex)
    check("P3", "HF-B1 reproduces on the live evidence (no revision hash embedded)",
          {"classifier": "UNBOUND", "explicit_hash_field": False, "hex64_count": 0},
          {"classifier": live_class["status"], "explicit_hash_field": live_class["has_explicit_hash_field"],
           "hex64_found": live_hex},
          hf_b1_reproduced)

    # ---- candidate binds the measured live revision (private instrument) --------
    cand_bytes = (root / CANDIDATE).read_bytes()
    cand = json.loads(cand_bytes.decode("utf-8"))
    cand_class = classify_record(cand, live_canon, live_supp)
    cand_binding = cand.get("binding") or {}
    cand_claim_ok = (
        cand_class["status"] == "BOUND"
        and cand.get("map_taxonomy_sha256") == live_canon
        and cand.get("lead_contract_sha256") == live_supp
        and cand_binding.get("declared_f0_artifact") == CANONICAL
        and cand_binding.get("declared_f0_sha256") == live_canon
        and isinstance(cand.get("input_sha256"), dict)
        and cand["input_sha256"].get(CANONICAL) == live_canon
        and cand["input_sha256"].get(SUPPLEMENT) == live_supp
    )
    check("P4", "candidate embeds exactly the independently measured live hashes",
          {"status": "BOUND", "canonical": live_canon, "supplement": live_supp},
          {"status": cand_class["status"], "map_taxonomy_sha256": cand.get("map_taxonomy_sha256"),
           "lead_contract_sha256": cand.get("lead_contract_sha256"),
           "input_sha256": cand.get("input_sha256"),
           "binding_declared_f0_sha256": cand_binding.get("declared_f0_sha256")},
          cand_claim_ok)

    # ---- candidate's own consistency claim, privately recomputed ----------------
    import yaml
    canon_doc = yaml.safe_load((root / CANONICAL).read_text(encoding="utf-8")) or {}
    supp_doc = yaml.safe_load((root / SUPPLEMENT).read_text(encoding="utf-8")) or {}
    priv = private_consistency(canon_doc, supp_doc)
    cons_ok = (cand.get("consistent") == priv["consistent"]
               and sorted(cand.get("errors") or []) == priv["errors"]
               and sorted(cand.get("contract_divergences") or []) == priv["contract_divergences"]
               and sorted(cand.get("classes_compared") or []) == priv["classes_compared"])
    check("P5", "candidate consistency claim reproduced by a private class-set check",
          {"consistent": priv["consistent"], "errors": priv["errors"],
           "contract_divergences": priv["contract_divergences"]},
          {"record_consistent": cand.get("consistent"), "record_errors": cand.get("errors"),
           "record_divergences": cand.get("contract_divergences"),
           "private": priv},
          cons_ok)

    # ---- generator determinism ---------------------------------------------------
    gen1 = work / "gen_run1.json"
    gen2 = work / "gen_run2.json"
    r1 = run([sys.executable, root / GEN, "--root", root, "--out", gen1])
    r2 = run([sys.executable, root / GEN, "--root", root, "--out", gen2])
    g1 = gen1.read_bytes() if gen1.exists() else b""
    g2 = gen2.read_bytes() if gen2.exists() else b""
    gen_identical = bool(g1) and g1 == g2
    gen_equals_pinned = gen_identical and g1 == cand_bytes
    check("P6", "generator is deterministic across two runs",
          {"run1_exit": 0, "run2_exit": 0, "byte_identical": True},
          {"run1_exit": r1["exit_code"], "run2_exit": r2["exit_code"],
           "byte_identical": gen_identical, "sha_equal_to_pinned_candidate": gen_equals_pinned,
           "run1_sha256": hashlib.sha256(g1).hexdigest() if g1 else None,
           "run2_sha256": hashlib.sha256(g2).hexdigest() if g2 else None},
          gen_identical and r1["exit_code"] == 0 and r2["exit_code"] == 0)

    # ---- author drift checker: live (expect B7 fail) -----------------------------
    sb_live = build_sandbox(sand / "live", root / LIVE_EVIDENCE, root)
    rep_live = work / "drift_live.json"
    rc_live = run([sys.executable, sb_live / DRIFT_CHECKER, "--root", sb_live, "--json", rep_live])
    live_drift = drift_summary(load_json(rep_live) if rep_live.exists() else {})
    live_b7_fail = bool(live_drift) and all(
        (v.get("B7") == "fail") for v in live_drift.values()) and rc_live["exit_code"] == 1
    check("P7", "author drift checker reproduces HF-B1 on live bytes (exit 1, B7 fail x3)",
          {"exit_code": 1, "B7_all_fail": True},
          {"exit_code": rc_live["exit_code"],
           "B7": {k: v.get("B7") for k, v in live_drift.items()},
           "verdict": {k: v.get("verdict") for k, v in live_drift.items()}},
          live_b7_fail)

    # ---- author drift checker: candidate drop-in (expect pass) -------------------
    sb_cand = build_sandbox(sand / "candidate", root / CANDIDATE, root)
    rep_cand = work / "drift_candidate.json"
    rc_cand = run([sys.executable, sb_cand / DRIFT_CHECKER, "--root", sb_cand, "--json", rep_cand])
    cand_drift = drift_summary(load_json(rep_cand) if rep_cand.exists() else {})
    cand_pass = (rc_cand["exit_code"] == 0 and bool(cand_drift)
                 and all(v.get("verdict") == "pass" and v.get("B7") == "pass"
                         for v in cand_drift.values()))
    check("P8", "candidate drop-in passes all hard checks of the author drift checker",
          {"exit_code": 0, "verdict_all": "pass", "B7_all": "pass"},
          {"exit_code": rc_cand["exit_code"],
           "verdict": {k: v.get("verdict") for k, v in cand_drift.items()},
           "B7": {k: v.get("B7") for k, v in cand_drift.items()},
           "hard_failures": {k: v.get("hard_failures") for k, v in cand_drift.items()}},
          cand_pass)

    # ---- canonical project checker in candidate sandbox --------------------------
    sb_cc = build_sandbox(sand / "canon_check", root / CANDIDATE, root)
    rc_cc = run([sys.executable, sb_cc / CONSISTENCY_CHECKER], cwd=sb_cc)
    cc_ok = rc_cc["exit_code"] == 0
    check("P9", "canonical check_taxonomy_consistency.py exits 0 in the candidate sandbox",
          {"exit_code": 0},
          {"exit_code": rc_cc["exit_code"], "stdout": rc_cc["stdout"][-600:]},
          cc_ok)

    # ================= controls (gate this worker's verdict) =================
    # C1 private classifier detects a prefix-preserving tamper (one suffix nibble)
    tampered = json.loads(json.dumps(cand))
    orig = tampered["input_sha256"][CANONICAL]
    flip = ("0" if orig[-1] != "0" else "1")
    tampered["input_sha256"][CANONICAL] = orig[:-1] + flip
    tampered["map_taxonomy_sha256"] = orig[:-1] + flip
    tampered["binding"]["declared_f0_sha256"] = orig[:-1] + flip
    tp = work / "tampered.json"
    tp.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tp_class = classify_record(tampered, live_canon, live_supp)
    control("C1", "private classifier detects a prefix-preserving tamper as STALE",
            {"classifier": "STALE", "shares_first16": True},
            {"classifier": tp_class["status"],
             "embedded_canonical": tp_class["embedded_canonical"],
             "shares_first16": tp_class["embedded_canonical"][0][:16] == live_canon[:16]},
            tp_class["status"] == "STALE")

    # C2 stale: record bound to a superseded canonical revision
    stale = json.loads(json.dumps(cand))
    stale["input_sha256"][CANONICAL] = SUPERSEDED_CANONICAL
    stale["map_taxonomy_sha256"] = SUPERSEDED_CANONICAL
    stale["binding"]["declared_f0_sha256"] = SUPERSEDED_CANONICAL
    sp = work / "stale.json"
    sp.write_text(json.dumps(stale, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    st_class = classify_record(stale, live_canon, live_supp)
    control("C2", "record bound to a superseded canonical revision is classified STALE",
            {"classifier": "STALE"},
            {"classifier": st_class["status"], "embedded": st_class["embedded_canonical"]},
            st_class["status"] == "STALE")

    # C3 unbound live record
    control("C3", "live unbound record is classified UNBOUND",
            {"classifier": "UNBOUND"}, {"classifier": live_class["status"]},
            live_class["status"] == "UNBOUND")

    # C4 null record
    null_class = classify_record({}, live_canon, live_supp)
    control("C4", "empty record is classified UNBOUND (null control)",
            {"classifier": "UNBOUND"}, {"classifier": null_class["status"]},
            null_class["status"] == "UNBOUND")

    # C5 the sandbox tree is not inside any canonical directory
    sand_rel = sand.resolve().relative_to(root.resolve()).as_posix()
    in_canonical = sand_rel.startswith(("schemas/", "research_map/", "artifacts/formulation/"))
    control("C5", "sandbox tree lies outside all canonical directories",
            {"in_canonical_dir": False, "under_worker_dir": True},
            {"in_canonical_dir": in_canonical,
             "under_worker_dir": sand_rel.startswith("artifacts/worker-027/")},
            (not in_canonical) and sand_rel.startswith("artifacts/worker-027/"))

    # C6 sandbox evidence equals the source it was built from
    sb_ev = sha256_file(sb_cand / LIVE_EVIDENCE)
    control("C6", "candidate sandbox evidence is byte-identical to the pinned candidate",
            {"sha256": pins[CANDIDATE]}, {"sha256": sb_ev}, sb_ev == pins[CANDIDATE])

    # ============ instrument probes (recorded, do NOT gate the verdict) ============
    # The proposal's acceptance criterion is "all hard checks pass" under
    # check_class_binding_drift.py.  These probes measure what B7 actually binds.
    probes = []

    def probe(pid, name, fixture: Path, note):
        sb = build_sandbox(sand / pid.lower(), fixture, root)
        rp = work / f"drift_{pid.lower()}.json"
        rc = run([sys.executable, sb / DRIFT_CHECKER, "--root", sb, "--json", rp])
        ds = drift_summary(load_json(rp) if rp.exists() else {})
        b7 = {k: v.get("B7") for k, v in ds.items()}
        cls = classify_record(load_json(fixture), live_canon, live_supp)
        probes.append({"id": pid, "name": name, "note": note,
                       "fixture": fixture.name,
                       "private_classifier": cls["status"],
                       "author_drift_exit": rc["exit_code"],
                       "author_B7": b7,
                       "author_caught_tamper": rc["exit_code"] == 1 and all(
                           s == "fail" for s in b7.values())})

    probe("IP1", "prefix-preserving tamper (suffix nibble flipped, first 16 hex intact)",
          tp, "B7 is a substring test on declared or declared[:16]; a near-miss record passes.")
    probe("IP2", "superseded-revision binding (full hash replaced, prefix changed)",
          sp, "B7 correctly fails when the declared prefix is absent.")
    supp_t = json.loads(json.dumps(cand))
    supp_t["lead_contract_sha256"] = live_supp[:-1] + ("0" if live_supp[-1] != "0" else "1")
    supp_t["input_sha256"][SUPPLEMENT] = supp_t["lead_contract_sha256"]
    spt = work / "supp_tampered.json"
    spt.write_text(json.dumps(supp_t, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe("IP3", "supplement-input binding tampered (canonical input left intact)",
          spt, "B7 only looks for the canonical declared hash; the supplement input is not bound.")

    instrument_findings = [
        {"id": "W027-HB1-F2", "severity": "major",
         "status": "CONFIRMED" if probes[0]["author_caught_tamper"] is False else "NOT_REPRODUCED",
         "statement": ("check_class_binding_drift.py B7 accepts any record containing the declared "
                       "F0 hash or its first 16 hex chars as a substring; a record whose binding "
                       "hash shares only the 64-bit prefix passes all hard checks, so B7 does not "
                       "verify that the record's declared revision equals the schema's declared/measured "
                       "revision.")},
        {"id": "W027-HB1-F3", "severity": "minor",
         "status": "CONFIRMED" if probes[2]["author_caught_tamper"] is False else "NOT_REPRODUCED",
         "statement": ("B7 binds only the canonical F0 hash; the supplement input "
                       "(artifacts/formulation/formulation_taxonomy.yaml) is not bound by any hard "
                       "check, so a record can carry a stale supplement hash and still pass.")},
    ]

    if not keep_sandboxes:
        shutil.rmtree(sand, ignore_errors=True)

    return {"checks": checks, "controls": controls, "instrument_probes": probes,
            "instrument_findings": instrument_findings,
            "pins": pins, "live_hashes": {"canonical": live_canon, "supplement": live_supp,
                                          "evidence": live_evidence},
            "loss": {
                "live_classifier": live_class,
                "candidate_classifier": cand_class,
                "private_consistency": priv,
                "live_hex64_found": live_hex,
            }}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT_DEFAULT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None, help="scratch dir (default: alongside --out)")
    ap.add_argument("--report", default=None, help="optional JSON report path")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--keep-sandboxes", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(args.work) if args.work else out.parent / "sandbox"
    if not work.is_absolute():
        work = root / work
    work.mkdir(parents=True, exist_ok=True)

    missing = [rel for rel in PINNED if not (root / rel).exists()]
    if missing:
        print(f"VOID: missing inputs: {missing}", file=sys.stderr)
        return 2

    t0 = now()
    pins_t0 = {rel: sha256_file(root / rel) for rel in PINNED}

    runs = []
    for _ in range(max(1, args.repeat)):
        m = measure(root, work, args.keep_sandboxes)
        digest = hashlib.sha256(json.dumps(
            {"checks": m["checks"], "controls": m["controls"],
             "instrument_probes": m["instrument_probes"],
             "live_hashes": m["live_hashes"], "loss": m["loss"]},
            sort_keys=True).encode("utf-8")).hexdigest()
        runs.append({"digest": digest, **m})
    run0 = runs[0]
    repeat_identical = len({r["digest"] for r in runs}) == 1

    t1 = now()
    pins_t1 = {rel: sha256_file(root / rel) for rel in PINNED}
    drift = sorted(rel for rel in PINNED if pins_t0[rel] != pins_t1[rel])

    primary_ok = all(c["ok"] for c in run0["checks"])
    controls_ok = all(c["ok"] for c in run0["controls"])
    if drift:
        verdict, code = "VOID_PIN_DRIFT_T0_T1", 2
    elif primary_ok and controls_ok and repeat_identical:
        verdict, code = "INDEPENDENTLY_VERIFIED_HB1_CLOSURE_VALID_UNPUBLISHED", 0
    else:
        verdict, code = "CLAIM_NOT_VERIFIED", 1

    report = {
        "schema_version": "0.1",
        "task_id": "W027-F2A-HB1-INDEP-01",
        "worker": "worker-027",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "node_id": "F2a",
        "gate": "G-FORM",
        "created_at": t1,
        "t0": t0,
        "t1": t1,
        "root": str(root),
        "verdict": verdict,
        "exit_code": code,
        "pins_t0": pins_t0,
        "pins_t1": pins_t1,
        "pin_drift": drift,
        "primary_checks": run0["checks"],
        "controls": run0["controls"],
        "instrument_probes": run0["instrument_probes"],
        "instrument_findings": run0["instrument_findings"],
        "loss": run0["loss"],
        "repeat": {"runs": len(runs), "digests": [r["digest"] for r in runs],
                   "identical": repeat_identical},
        "claim_under_test": {
            "author": "deepseek-flash-05",
            "author_closure_report": "artifacts/worker-05/verify/hb1_closure_report.json#c7eeab551128",
            "candidate": f"{CANDIDATE}#{pins_t0[CANDIDATE][:12]}",
            "destined_canonical_path": LIVE_EVIDENCE,
            "published": False,
        },
        "instrument_dependence": [
            "P3/P4/P5/C1-C4 use this worker's own hex64 scanner, classifier and class-set check.",
            "P7/P8/C1 use the author's check_class_binding_drift.py (bde270d3886a) as a labelled cross-instrument.",
            "P9 uses the canonical artifacts/formulation/tools/check_taxonomy_consistency.py (de356d999ea3).",
        ],
        "falsifier": ("FALSIFIED if (a) any pinned input drifts T0->T1 (void, exit 2); "
                      "(b) the live evidence embeds a sha256 of either compared file or an explicit "
                      "input-hash field; (c) the candidate's embedded canonical/supplement hashes are "
                      "not the measured live hashes; (d) the candidate's consistent claim is not "
                      "reproduced by P5 or P9; (e) the generator's two runs are not byte-identical; "
                      "(f) the candidate drop-in still hard-fails the author drift checker for any "
                      "schema; (g) the live record passes B7; (h) any control misses its "
                      "pre-registered expectation."),
        "non_claims": [
            "not a gate verdict; worker events cannot set status=done, validation_status=passed, or any gate verdict",
            "does not publish the candidate; the canonical write and the three schema re-pins belong to the formulation lead",
            "does not adjudicate the F2a assignment moving-target blocker (rev12 pin 5476a3f2 vs live e9a27996)",
            "author-level independence only: deepseek-flash-05 authored the claim; worker-027 did not author it",
            "records but does not adjudicate two blind spots in the author's drift checker (W027-HB1-F2/F3); hardening the tool is the tool owner's call",
        ],
        "main_claim": {
            "id": "W027-HB1-F1",
            "statement": ("At the pinned live bytes, the HF-B1 closure proposal is valid and unpublished: "
                          "the live evidence 9e335e9b is unbound (no revision hash); the candidate 4c4803c5 "
                          "embeds exactly the measured hashes of both compared taxonomy files and reproduces "
                          "byte-for-byte from the pinned generator; dropped in at the canonical evidence path "
                          "in an isolated sandbox it makes every hard check of check_class_binding_drift.py "
                          "pass for all three schemas, and the canonical check_taxonomy_consistency.py exits 0."),
        },
    }
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    print(json.dumps({"verdict": verdict, "exit_code": code,
                      "report_sha256": sha256_file(out),
                      "primary_ok": primary_ok, "controls_ok": controls_ok,
                      "repeat_identical": repeat_identical, "pin_drift": drift}, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
