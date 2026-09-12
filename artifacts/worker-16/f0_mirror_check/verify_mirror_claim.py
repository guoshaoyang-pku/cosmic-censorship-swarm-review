#!/usr/bin/env python3
"""Independent verification of F0-MIRROR-CONFLICT (leadform-blocker-0007).

Task: worker=016 bounded class-bound pass. Claim under test (evidence file
artifacts/formulation/evidence/f0_mirror_conflict.json, produced_by
astra-lead-formulation): research_map/formulation_taxonomy.yaml (276009f4, 35145 b)
and artifacts/formulation/formulation_taxonomy.yaml (c8e979a1, 20937 b) are two
different artifacts, not two trees of one artifact; a byte-identical publication in
either direction destroys a frozen input.

This script is READ-ONLY with respect to every repo artifact. The only writes are:
  - stage/<...>  (a scratch tree under this script's own directory, used to run the
    pinned consistency checker on substituted bytes without touching the repo copy;
    running the repo checker in place would rewrite the pinned evidence file),
  - the report paths passed on the command line (default verification.json + REPORT.md
    inside this directory).

Every input is hashed and printed, so the verdict binds to bytes.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUTDIR = Path(__file__).resolve().parent

CANON = ROOT / "research_map/formulation_taxonomy.yaml"
AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CHECKER = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
AUDIT = ROOT / "research_map/audit_evidence.py"
SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
CLAIMED = {
    "canonical_sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "canonical_bytes": 35145,
    "authoring_sha256": "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
    "authoring_bytes": 20937,
}

checks: list[dict] = []


def rec(check_id: str, verdict: str, detail: str, evidence: list[str] | None = None) -> None:
    checks.append({"id": check_id, "verdict": verdict, "detail": detail, "evidence": evidence or []})


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def fhash(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#sha256:{sha(p)[:12]}"


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text())


def resolve_fragment(doc: dict, fragment: str) -> tuple[bool, str]:
    node = doc
    try:
        for part in fragment.split("."):
            node = node[part]
        return True, type(node).__name__
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    run_at = subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip()
    inputs = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
              for p in [CANON, AUTHOR, CHECKER, ALIASES, CONSISTENCY, FROZEN, AUDIT, *SCHEMAS.values()]}

    # --- V1/V2 byte identity of the two artifacts against the claimed values ---------
    c_ok = sha(CANON) == CLAIMED["canonical_sha256"] and CANON.stat().st_size == CLAIMED["canonical_bytes"]
    a_ok = sha(AUTHOR) == CLAIMED["authoring_sha256"] and AUTHOR.stat().st_size == CLAIMED["authoring_bytes"]
    rec("V1", "PASS" if c_ok else "FAIL",
        f"canonical {sha(CANON)[:12]} / {CANON.stat().st_size} b vs claimed "
        f"{CLAIMED['canonical_sha256'][:12]} / {CLAIMED['canonical_bytes']} b",
        [fhash(CANON)])
    rec("V2", "PASS" if a_ok else "FAIL",
        f"authoring {sha(AUTHOR)[:12]} / {AUTHOR.stat().st_size} b vs claimed "
        f"{CLAIMED['authoring_sha256'][:12]} / {CLAIMED['authoring_bytes']} b",
        [fhash(AUTHOR)])
    rec("V3", "PASS" if sha(CANON) != sha(AUTHOR) else "FAIL",
        "the two paths are not byte-identical (the whole premise of the conflict)",
        [fhash(CANON), fhash(AUTHOR)])

    A = load_yaml(CANON)
    B = load_yaml(AUTHOR)
    ak, bk = set(A), set(B)

    # --- V4 load-bearing key sets and their disjointness -----------------------------
    req_a = {"class_ids", "classes", "transfer_rules"}
    req_b = {"class_contracts", "axis_registry", "implication_ledger"}
    v4 = (req_a <= ak) and (req_b <= bk) and ("class_contracts" not in ak) and ("class_ids" not in bk)
    rec("V4", "PASS" if v4 else "FAIL",
        f"canonical has {sorted(req_a)} and no class_contracts; authoring has {sorted(req_b)} and no class_ids. "
        f"|A|={len(ak)} |B|={len(bk)} shared={sorted(ak & bk)}",
        [fhash(CANON), fhash(AUTHOR)])
    rec("V5", "INFO",
        f"full top-level key sets: canonical={sorted(ak)}; authoring={sorted(bk)}",
        [fhash(CANON), fhash(AUTHOR)])

    # --- V6 schema pointers and f0 bindings ------------------------------------------
    ptr_ok, bind_ok = True, True
    ptr_detail = []
    for cid, sp in SCHEMAS.items():
        sd = load_yaml(sp)
        ptr = str(sd.get("class_contract_pointer", ""))
        want = f"artifacts/formulation/formulation_taxonomy.yaml#class_contracts.{cid}"
        ok_ptr = ptr == want and resolve_fragment(B, f"class_contracts.{cid}")[0] and \
            not resolve_fragment(A, f"class_contracts.{cid}")[0]
        ptr_ok &= ok_ptr
        ptr_detail.append(f"{sp.name}: {'ok' if ok_ptr else 'MISMATCH'} ({ptr})")
        fb = sd.get("f0_binding") or {}
        ok_bind = (str(fb.get("declared_f0_artifact")) == "research_map/formulation_taxonomy.yaml"
                   and str(fb.get("declared_f0_sha256")) == CLAIMED["canonical_sha256"]
                   and str(fb.get("class_contract_supplement")) == "artifacts/formulation/formulation_taxonomy.yaml"
                   and str(fb.get("consistency_evidence")) == "artifacts/formulation/evidence/taxonomy_consistency.json")
        bind_ok &= ok_bind
    rec("V6", "PASS" if ptr_ok else "FAIL",
        "all three class_contract_pointer values target the authoring supplement and resolve only there; " + "; ".join(ptr_detail),
        [fhash(p) for p in SCHEMAS.values()] + [fhash(AUTHOR), fhash(CANON)])
    rec("V7", "PASS" if bind_ok else "FAIL",
        "all three f0_binding records name canonical 276009f4 as declared F0 and the authoring file as supplement",
        [fhash(p) for p in SCHEMAS.values()])

    # --- V8 checker dependency proof (static) ----------------------------------------
    src = CHECKER.read_text().splitlines()
    def line(n: int) -> str:
        return src[n - 1]
    required = {
        'A["class_ids"]': any('A["class_ids"]' in line(n) for n in range(16, 20)),
        'A["classes"]': any('A["classes"]' in line(n) for n in range(16, 33)),
        'B["class_contracts"]': any('B["class_contracts"]' in line(n) for n in range(16, 40)),
        'B.axis_registry.genericity_axis': 'axis_registry' in line(32) and 'genericity_axis' in line(32),
        'B implication_ledger': any('B.get("implication_ledger")' in line(n) for n in range(66, 75)),
    }
    rec("V8", "PASS" if all(required.values()) else "FAIL",
        f"checker requires from canonical {[k for k in required if k.startswith('A')]} and from authoring "
        f"{[k for k in required if k.startswith('B')]}; all present={all(required.values())}",
        [f"{fhash(CHECKER)}:{n}" for n in (16, 17, 19, 32, 34, 37, 71, 72)])

    # --- V9 destructive-substitution simulation in a staged tree ---------------------
    stage = OUTDIR / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "research_map").mkdir(parents=True)
    (stage / "artifacts/formulation/tools").mkdir(parents=True)
    (stage / "artifacts/formulation/evidence").mkdir(parents=True)
    shutil.copy2(CHECKER, stage / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    shutil.copy2(ALIASES, stage / "artifacts/formulation/VOCAB_ALIASES.json")

    def stage_pair(canon_src: Path, author_src: Path) -> None:
        shutil.copy2(canon_src, stage / "research_map/formulation_taxonomy.yaml")
        shutil.copy2(author_src, stage / "artifacts/formulation/formulation_taxonomy.yaml")

    def run_staged() -> tuple[int, str, str, bool]:
        # delete the staged evidence first: on a crashing run the checker never writes it,
        # and a stale file from a previous staged run must not be read as this run's output.
        ev = stage / "artifacts/formulation/evidence/taxonomy_consistency.json"
        ev.unlink(missing_ok=True)
        p = subprocess.run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                           cwd=stage, capture_output=True, text=True)
        consistent = None
        if ev.exists():
            consistent = json.loads(ev.read_text()).get("consistent")
        return p.returncode, p.stdout.strip(), p.stderr.strip(), consistent

    stage_pair(CANON, AUTHOR)
    rc, so, se, consistent = run_staged()
    control_ok = rc == 0 and consistent is True and so.startswith("CONSISTENT")
    rec("V9-control", "PASS" if control_ok else "FAIL",
        f"unsubstituted staged pair: rc={rc} consistent={consistent} stdout={so!r}",
        [fhash(CHECKER), fhash(ALIASES)])

    stage_pair(CANON, CANON)  # authoring replaced by canonical
    rc, so, se, consistent = run_staged()
    keyerr_b = "KeyError" in se and "class_contracts" in se
    rec("V10", "PASS" if keyerr_b and rc != 0 else "FAIL",
        f"authoring<-canonical substitution: rc={rc} consistent={consistent} stderr_tail={se.splitlines()[-1] if se else ''!r} "
        f"(evidence claims KeyError on B['class_contracts'])",
        [fhash(CHECKER)])

    stage_pair(AUTHOR, AUTHOR)  # canonical replaced by authoring
    rc, so, se, consistent = run_staged()
    keyerr_a = "KeyError" in se and "class_ids" in se
    rec("V11", "PASS" if keyerr_a and rc != 0 else "FAIL",
        f"canonical<-authoring substitution: rc={rc} consistent={consistent} stderr_tail={se.splitlines()[-1] if se else ''!r} "
        f"(evidence claims KeyError on A['class_ids'])",
        [fhash(CHECKER)])

    # negative control: one-byte mutation of the canonical copy must be detectable by hash
    stage_pair(CANON, AUTHOR)
    mutated = bytearray((stage / "research_map/formulation_taxonomy.yaml").read_bytes())
    mutated[-2] = (mutated[-2] + 1) % 256 if mutated[-2] != 10 else (mutated[-2] + 2) % 256
    (stage / "research_map/formulation_taxonomy.yaml").write_bytes(bytes(mutated))
    mut_sha = sha(stage / "research_map/formulation_taxonomy.yaml")
    rec("V12-negative-control", "PASS" if mut_sha != sha(CANON) else "FAIL",
        "one-byte mutation changes the pinned hash, so the byte binding is sensitive (N1)",
        [fhash(CANON)])

    # --- V13 FROZEN manifest pins both sides ------------------------------------------
    fz = json.loads(FROZEN.read_text())
    files = fz.get("files") or {}
    e_canon = (files.get("research_map/formulation_taxonomy.yaml") or {}).get("sha256")
    e_author = (files.get("artifacts/formulation/formulation_taxonomy.yaml") or {}).get("sha256")
    frozen_ok = e_canon == sha(CANON) and e_author == sha(AUTHOR)
    rec("V13", "PASS" if frozen_ok else "FAIL",
        f"FROZEN rev{fz.get('revision')} (frozen_at {fz.get('frozen_at')}) pins canonical={str(e_canon)[:12]} and "
        f"authoring={str(e_author)[:12]}; both match measured bytes. logical_artifacts={'logical_artifacts' in fz}, "
        f"adjudication_request={'f0_mirror_adjudication_request' in fz}",
        [fhash(FROZEN), fhash(CANON), fhash(AUTHOR)])

    # --- V14 acceptance-test dual-tree finding, reproduced without running the writer --
    audit_src = AUDIT.read_text().splitlines()
    mirror_block = "\n".join(audit_src[118:140])
    f0_pair_listed = "research_map/formulation_taxonomy.yaml" in mirror_block and \
        "artifacts/formulation/formulation_taxonomy.yaml" in mirror_block
    rec("V14", "PASS" if f0_pair_listed else "INFO",
        f"audit_evidence.py MIRRORS includes the F0 pair={f0_pair_listed}; the soft dual-tree finding in the evidence "
        f"is therefore reproduced by construction (canonical {sha(CANON)[:12]} != authoring {sha(AUTHOR)[:12]}). "
        "This script does not run audit_evidence.py because that writer path was not exercised in this pass.",
        [f"{fhash(AUDIT)}:121-140", fhash(CANON), fhash(AUTHOR)])

    # --- V15 prior verdict supersession / accept coverage ------------------------------
    m = json.loads((ROOT / "research_map/research_map.json").read_text())
    gate_audit = m.get("controller_gate_audit") or {}
    g_f0 = gate_audit.get("G-F0") or {}
    f0_reviews = [r for r in (m.get("reviews") or []) if str(r.get("target_id")) == "F0"]
    by_verdict: dict[str, list[str]] = {}
    for r in f0_reviews:
        by_verdict.setdefault(str(r.get("verdict")), []).append(str(r.get("reviewer") or r.get("event_id")))
    accepts_at_hash_top = [r.get("event_id") for r in f0_reviews
                           if str(r.get("verdict")) == "accept"
                           and str(r.get("artifact_sha256")) == CLAIMED["canonical_sha256"]]
    accepts_at_hash_ref = [r.get("event_id") for r in f0_reviews
                           if str(r.get("verdict")) == "accept"
                           and CLAIMED["canonical_sha256"][:12] in json.dumps(r)
                           and str(r.get("artifact_sha256")) != CLAIMED["canonical_sha256"]]
    sup_hits = json.dumps(m).count("565a6e505188")
    rec("V15", "INFO",
        f"F0-targeted reviews by verdict: { {k: v for k, v in by_verdict.items()} }. "
        f"controller_gate_audit G-F0 (checked {g_f0.get('checked_at')}) reason={str(g_f0.get('reason'))[:260]!r}. "
        f"accepts with top-level artifact_sha256==276009f4: {accepts_at_hash_top}; accepts bound to 276009f4 only via "
        f"evidence_refs/conditions (not counted by that scan): {accepts_at_hash_ref}. "
        f"565a6e505188 appears {sup_hits}x in the map (superseded lineage). Adjudicating whether an evidence_refs-bound "
        f"accept counts is controller authority.",
        ["research_map/research_map.json"])

    overall = all(c["verdict"] in ("PASS", "INFO") for c in checks) and \
        all(c["verdict"] == "PASS" for c in checks if c["id"] in
            ("V1", "V2", "V3", "V4", "V6", "V7", "V8", "V9-control", "V10", "V11", "V13"))
    verdict = "CONFIRMED" if overall else "REFUTED"
    report = {
        "verification_id": "W16-F0-MIRROR-VERIFY-01",
        "task_id": "FORM-HELDOUT-08-followup-mirror-adjudication-evidence",
        "actor": "worker-16",
        "node_id": "F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "run_at_wall_clock": run_at,
        "target_evidence": "artifacts/formulation/evidence/f0_mirror_conflict.json#sha256:"
                           + sha(ROOT / "artifacts/formulation/evidence/f0_mirror_conflict.json")[:12],
        "target_blocker": "leadform-blocker-0007",
        "author_of_target": "astra-lead-formulation",
        "verifier_prior_work_disclosure": "worker-16 authored reviews/F0-review-16.json at canonical 276009f4 "
                                          "(schema-quality review). This pass verifies the separate publication/"
                                          "structure claim, not that review.",
        "verdict": verdict,
        "checks": checks,
        "inputs": inputs,
        "read_only_statement": "No repo artifact was modified. Substitution runs executed only in the staged tree at "
                               "artifacts/worker-16/f0_mirror_check/stage/ (the repo checker writes its evidence file "
                               "on every run, so running it in place would have rewritten the pinned file).",
        "caveats": [
            "The adjudication itself (REC-1 vs REC-2) is controller authority and is not decided here.",
            "audit_evidence.py was read, not executed, to avoid its writer paths in this bounded pass.",
            "The verdict binds to the input hashes above; any byte change retires it.",
        ],
        "falsifier": "Any of V1-V13 turning FAIL on a re-run at these hashes, or a substitution run that exits 0 "
                     "without an exception, refutes this confirmation. If a future revision makes the two paths "
                     "byte-identical while every frozen schema binding, the pinned consistency evidence, and the "
                     "F0 gate criteria still resolve, then the 'cannot be made identical' claim is refuted.",
        "next_falsifier": "Compute the closure of artifacts that reference the authoring #class_contracts fragment "
                          "(the three schemas, the checker, and FROZEN-pinned consistency evidence were checked here; "
                          "any additional consumer found later that could be repointed cheaply lowers REC-2's cost).",
    }
    vpath = OUTDIR / "verification.json"
    vpath.write_text(json.dumps(report, indent=2) + "\n")
    vsha = sha(vpath)
    (OUTDIR / "verification.sha256").write_text(f"{vsha}  verification.json\n")

    print(f"VERDICT: {verdict}")
    for c in checks:
        print(f"  {c['id']:>20} {c['verdict']:>5}  {c['detail'][:150]}")
    print(f"report: {vpath.relative_to(ROOT)} sha256={vsha}")
    return 0 if overall else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(3)
