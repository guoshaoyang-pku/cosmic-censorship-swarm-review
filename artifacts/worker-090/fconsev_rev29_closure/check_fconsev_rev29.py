#!/usr/bin/env python3
"""W090-FCONSEV-REV29-CLOSURE-01

Independent, read-only, hash-pinned closure measurement of the evidence self-binding
residual F-CONSEV (map review w050-20260912T002334, finding F-CONSEV) and of this
worker's own closure criteria W090-R12-01 / W090-F2A-01, at the live post-repair
FROZEN revision 29 bytes.

Class binding : AF-SCC-C2-VAC-GEN (node F2a); F1 AF-WCC-VAC-GEN and F2b
                AF-SCC-C0-VAC-GEN corroborate the shared f0_binding mechanism.
Gate          : G-FORM (advisory worker measurement; no gate verdict, no node status).

Pre-registered structure
  Part A  pointer clause of REC-12 item (2): declared consistency_evidence_sha256 ==
          measured live evidence hash, declared_f0_sha256 == measured live canonical F0,
          checked_at not ahead of wall clock, canonical == mirror, FROZEN rev29 pins
          complete and matching.
  Part B  embedding clause of W090-R12-01 / W090-F2A-01: the evidence file itself
          records the compared bytes (full sha256 of both compared trees, or any
          byte-identity witness), and the supplement side of the comparison is pinned
          in the schemas' own f0_binding.
  Part C  sandbox experiments (canonical bytes never written):
          C0 null reproduction: pinned checker re-run on byte copies emits the live
             evidence file byte-for-byte;
          C1 semantic mutation of the sandbox supplement is detected by the checker;
          C2 exposure predicate: with a mutated supplement and the deployed evidence,
             every declared binding value still matches while the consistency claim is
             about different bytes;
          C3 compensating control: the FROZEN manifest pin detects the same mutation.

Exit code 0 = instrument completed and every pre-registered control reproduced its
expected outcome. Non-zero = instrument or control failure. The substantive verdict is
in results.json; it is not signalled by the exit code.

No canonical artifact is written. All mutations happen under this directory's sandbox/.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]
SANDBOX = ART / "sandbox"
SNAP = ART / "snapshot"
CST = timezone(timedelta(hours=8))

F0_TAX = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
FROZEN = "artifacts/formulation/FROZEN.json"
SCHEMAS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
MIRRORS = {k: "artifacts/formulation/" + v for k, v in SCHEMAS.items()}
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
C2_MUTATION = "scc_c2_future_inextendibility_MUTANT_W090"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(paths):
    return {p: (sha256(ROOT / p) if (ROOT / p).exists() else None) for p in paths}


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def add(checks, cid, desc, expected, observed, ok=None):
    if ok is None:
        ok = observed == expected
    checks.append({"id": cid, "description": desc, "expected": expected,
                   "observed": observed, "pass": bool(ok)})
    return bool(ok)


def run_checker(sandbox_root: Path):
    """Run the pinned checker inside a sandbox layout; return rc, stdout, stderr, evidence bytes."""
    tool = sandbox_root / CHECKER
    (sandbox_root / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(tool)], cwd=str(sandbox_root),
                          capture_output=True, text=True, timeout=300)
    ev = sandbox_root / EVID
    return proc.returncode, proc.stdout, proc.stderr, (ev.read_bytes() if ev.exists() else None)


def build_sandbox(tag: str, taxonomy_bytes: bytes, supp_bytes: bytes):
    """Fresh sandbox with the pinned layout; caller supplies the two compared trees."""
    sb = SANDBOX / tag
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "research_map").mkdir(parents=True)
    (sb / "artifacts/formulation/tools").mkdir(parents=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True)
    (sb / F0_TAX).write_bytes(taxonomy_bytes)
    (sb / SUPP).write_bytes(supp_bytes)
    shutil.copy2(ROOT / ALIASES, sb / ALIASES)
    shutil.copy2(ROOT / CHECKER, sb / CHECKER)
    return sb


def mutate_supplement(supp_bytes: bytes):
    """Semantic mutation of a compared field, applied to parsed YAML, in the sandbox only."""
    doc = yaml.safe_load(supp_bytes.decode())
    before = doc["class_contracts"]["AF-SCC-C2-VAC-GEN"]["conclusion_type"]
    doc["class_contracts"]["AF-SCC-C2-VAC-GEN"]["conclusion_type"] = C2_MUTATION
    return yaml.safe_dump(doc, sort_keys=True).encode(), before


def binding_predicates(binding: dict, evidence_bytes: bytes, f0_bytes_path: Path):
    """The deployed f0_binding predicate, evaluated on supplied evidence bytes."""
    decl_ev = binding.get("consistency_evidence_sha256")
    decl_f0 = binding.get("declared_f0_sha256")
    return {
        "declared_evidence_sha256_matches_supplied": decl_ev == hashlib.sha256(evidence_bytes).hexdigest(),
        "declared_f0_sha256_matches_live": decl_f0 == sha256(f0_bytes_path),
        "checked_at": binding.get("checked_at"),
    }


def embedding_witness(text: str):
    return sorted(set(HEX64.findall(text)))


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    started = now()
    checks, controls, errors = [], [], []

    pin_paths = [F0_TAX, SUPP, ALIASES, EVID, CHECKER, FROZEN, *SCHEMAS.values(), *MIRRORS.values()]
    pins = measure(pin_paths)
    if any(v is None for v in pins.values()):
        missing = [k for k, v in pins.items() if v is None]
        errors.append(f"missing pinned path(s): {missing}")

    frozen = json.loads((ROOT / FROZEN).read_text())
    frozen_rev, frozen_sha = frozen.get("revision"), pins[FROZEN]

    # ---- snapshot of reviewed bytes (self-contained reproducibility) ----
    if SNAP.exists():
        shutil.rmtree(SNAP)
    for p in pin_paths:
        dst = SNAP / p
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / p, dst)
    (SNAP / "SHA256SUMS.txt").write_text(
        "".join(f"{pins[p]}  {p}\n" for p in pin_paths if pins[p]))

    evidence_raw = (ROOT / EVID).read_text()
    evidence_doc = json.loads(evidence_raw)
    supplements = {}
    for cid, sp in SCHEMAS.items():
        doc = load_yaml(ROOT / sp)
        b = doc.get("f0_binding", {})
        supplements[cid] = b
        add(checks, f"A1-{cid}",
            "declared consistency_evidence_sha256 equals measured live evidence hash",
            pins[EVID], b.get("consistency_evidence_sha256"),
            b.get("consistency_evidence_sha256") == pins[EVID])
        add(checks, f"A2-{cid}",
            "declared_f0_sha256 equals measured live canonical taxonomy hash",
            pins[F0_TAX], b.get("declared_f0_sha256"),
            b.get("declared_f0_sha256") == pins[F0_TAX])
        at = b.get("checked_at")
        parsed, ok_at = None, False
        try:
            dt = datetime.fromisoformat(at)
            parsed = dt.isoformat()
            ok_at = dt <= datetime.now(CST) + timedelta(seconds=5)
        except Exception:
            parsed = None
        add(checks, f"A3-{cid}", "f0_binding.checked_at is parseable and not in the future",
            "parseable_and_not_future", parsed, bool(parsed) and ok_at)
        add(checks, f"A4-{cid}", "canonical schema bytes equal mirror bytes",
            pins[sp], pins[MIRRORS[cid]], pins[sp] == pins[MIRRORS[cid]])

    manifest = frozen.get("files", {})
    mism = [{"path": p, "manifest": rec.get("sha256"),
             "measured": sha256(ROOT / p) if (ROOT / p).exists() else None}
            for p, rec in manifest.items()
            if not (ROOT / p).exists() or sha256(ROOT / p) != rec.get("sha256")]
    add(checks, "A5-frozen-manifest", "every FROZEN rev29 manifest pin matches live bytes",
        [], mism, mism == [])
    add(checks, "A6-frozen-entries", "FROZEN rev29 file-map size is recorded",
        len(manifest), len(manifest), True)
    add(checks, "A7-evidence-parses", "live consistency evidence parses as JSON",
        True, isinstance(evidence_doc, dict), isinstance(evidence_doc, dict))

    # ---- Part B: embedding clause ----
    witnesses = embedding_witness(evidence_raw)
    add(checks, "B1-f0-witness", "evidence records the full sha256 of the canonical taxonomy",
        True, pins[F0_TAX] in witnesses, pins[F0_TAX] in witnesses)
    add(checks, "B2-supp-witness", "evidence records the full sha256 of the lead class contract",
        True, pins[SUPP] in witnesses, pins[SUPP] in witnesses)
    add(checks, "B3-any-witness", "evidence contains any 64-hex byte-identity witness",
        True, len(witnesses) > 0, len(witnesses) > 0)
    supp_keys = {}
    for cid, b in supplements.items():
        keys = {k: v for k, v in b.items() if "supplement" in k.lower()}
        supp_keys[cid] = keys
        has_pin = any(isinstance(v, str) and HEX64.fullmatch(v) for v in keys.values())
        add(checks, f"B4-{cid}", "schema f0_binding hash-pins the supplement side of the comparison",
            True, has_pin, has_pin)
    add(checks, "B5-evidence-fields", "evidence field set (informational)",
        "paths+boolean only", sorted(evidence_doc.keys()), True)

    # ---- Part C: sandbox experiments ----
    taxonomy_bytes = (ROOT / F0_TAX).read_bytes()
    supp_bytes = (ROOT / SUPP).read_bytes()
    live_ev_bytes = (ROOT / EVID).read_bytes()

    sb_null = build_sandbox("null", taxonomy_bytes, supp_bytes)
    rc0, out0, err0, ev0 = run_checker(sb_null)
    add(controls, "C0-null-reproduction",
        "pinned checker on byte copies is CONSISTENT and emits the live evidence byte-for-byte",
        {"rc": 0, "stdout": "CONSISTENT", "identical": True},
        {"rc": rc0, "stdout": out0.strip().splitlines()[:1], "identical": ev0 == live_ev_bytes},
        rc0 == 0 and out0.startswith("CONSISTENT") and ev0 == live_ev_bytes)

    mut_bytes, mut_before = mutate_supplement(supp_bytes)
    sb_mut = build_sandbox("mutated", taxonomy_bytes, mut_bytes)
    rc1, out1, err1, ev1 = run_checker(sb_mut)
    ev1_doc = json.loads(ev1) if ev1 else {}
    named = any("AF-SCC-C2-VAC-GEN" in str(e) and "conclusion_type" in str(e)
                for e in ev1_doc.get("errors", []))
    add(controls, "C1-mutation-detected",
        "checker flags the mutated compared field and exits non-zero",
        {"rc_nonzero": True, "consistent": False, "names_class_field": True},
        {"rc": rc1, "consistent": ev1_doc.get("consistent"), "names_class_field": named},
        rc1 != 0 and ev1_doc.get("consistent") is False and named)

    # exposure: deployed evidence + mutated compared bytes; every declared value still matches
    bind_c2 = supplements["AF-SCC-C2-VAC-GEN"]
    exposure = binding_predicates(bind_c2, live_ev_bytes, ROOT / F0_TAX)
    add(controls, "C2-exposure-predicate",
        "with mutated compared bytes and the deployed evidence, all declared binding values still match",
        {"declared_evidence_matches": True, "declared_f0_matches": True},
        {"declared_evidence_matches": exposure["declared_evidence_sha256_matches_supplied"],
         "declared_f0_matches": exposure["declared_f0_sha256_matches_live"]},
        exposure["declared_evidence_sha256_matches_supplied"] and exposure["declared_f0_sha256_matches_live"])

    # compensating control: FROZEN manifest pin detects the same mutation
    sb_supp_path = sb_mut / SUPP
    manifest_pin = manifest.get(SUPP, {}).get("sha256")
    compensator = {"manifest_pin": manifest_pin, "mutated_sha256": sha256(sb_supp_path),
                   "detects": manifest_pin != sha256(sb_supp_path)}
    add(controls, "C3-frozen-compensator",
        "FROZEN rev29 manifest pin detects the same supplement mutation",
        True, compensator["detects"], compensator["detects"])

    # detector sensitivity M1: pointer tamper is caught by the A1 predicate
    tampered = dict(bind_c2)
    tampered["consistency_evidence_sha256"] = "0" * 64
    m1 = tampered.get("consistency_evidence_sha256") != pins[EVID]
    add(controls, "M1-pointer-detector",
        "A1 predicate flips on a sandbox tamper of the declared evidence hash", True, m1, m1)

    # detector sensitivity M2: embedding detector flips on an injected witness
    injected = json.loads(evidence_raw)
    injected["compared_trees_sha256"] = {"canonical": pins[F0_TAX], "supplement": pins[SUPP]}
    inj_text = json.dumps(injected)
    m2 = pins[F0_TAX] in embedding_witness(inj_text) and pins[SUPP] in embedding_witness(inj_text)
    add(controls, "M2-embedding-detector",
        "B1/B2 detectors flip when both tree hashes are present", True, m2, m2)

    # ---- end-of-run drift ----
    end_pins = measure(pin_paths)
    drift = [{"path": p, "start": pins[p], "end": end_pins[p]}
             for p in pin_paths if pins[p] != end_pins[p]]

    a_pass = all(c["pass"] for c in checks if c["id"].startswith("A"))
    a1_pass = all(c["pass"] for c in checks if c["id"].startswith(("A1", "A2", "A4", "A5")))
    embedding_open = not (checks_by_id(checks, "B1") and checks_by_id(checks, "B2")
                          and checks_by_id(checks, "B3"))
    controls_pass = all(c["pass"] for c in controls)

    verdict = {
        "W090-F2A-01": "partially_closed" if (a1_pass and embedding_open) else (
            "closed" if a1_pass else "open"),
        "pointer_clause_REC12_item2": "pass" if a1_pass else "fail",
        "embedding_clause_W090_R12_01": "open" if embedding_open else "closed",
        "F-CONSEV_at_rev29": "open" if embedding_open else "closed",
        "supplement_side_self_pinned": all(checks_by_id(checks, f"B4-{c}") for c in SCHEMAS),
        "frozen_revision_measured": frozen_rev,
        "frozen_manifest_clean": mism == [],
        "pin_drift": drift,
        "controls_all_as_preregistered": controls_pass,
    }

    results = {
        "task_id": "W090-FCONSEV-REV29-CLOSURE-01",
        "worker": "worker-090",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "corroborating_class_ids": [c for c in SCHEMAS if c != "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "authority_note": "advisory worker measurement; no gate verdict, no node status, no canonical-file write",
        "started_at": started,
        "finished_at": now(),
        "pins": pins,
        "frozen_revision": frozen_rev,
        "frozen_file_map_size": len(manifest),
        "checks": checks,
        "verdict": verdict,
        "errors": errors,
        "instrument_sha256_at_run": sha256(Path(__file__)),
        "reproduce": f"python3 {Path(__file__).relative_to(ROOT)}",
    }
    controls_doc = {
        "task_id": "W090-FCONSEV-REV29-CLOSURE-01",
        "at": now(),
        "pre_registered": True,
        "controls": controls,
        "mutation": {"field": "class_contracts.AF-SCC-C2-VAC-GEN.conclusion_type",
                     "before": mut_before, "after": C2_MUTATION,
                     "sandbox_only": True},
        "compensator_detail": compensator,
        "exposure_detail": exposure,
        "witnesses_found_in_live_evidence": witnesses,
        "supplement_related_binding_keys": supp_keys,
        "sandbox_checker_stdout": {"null": out0, "mutated": out1},
        "controls_all_pass": controls_pass,
    }
    (ART / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    (ART / "controls.json").write_text(json.dumps(controls_doc, indent=1) + "\n")

    print(json.dumps({"results": str(ART / "results.json"),
                      "checks_pass": sum(c["pass"] for c in checks), "checks_total": len(checks),
                      "controls_pass": sum(c["pass"] for c in controls), "controls_total": len(controls),
                      "verdict": verdict}, indent=1))
    if errors or not controls_pass:
        return 2
    return 0


def checks_by_id(checks, cid):
    return next((c["pass"] for c in checks if c["id"] == cid), False)


if __name__ == "__main__":
    raise SystemExit(main())
