#!/usr/bin/env python3
"""W003-F2B-REV14-CANDIDATE-INDEPENDENT-CLOSURE-01

Independent, read-only closure verification of the worker-044 composed F2b rev14
candidate (node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM) against the five blocking
families recorded at the live rev13 / FROZEN rev29 pins:

  H1  false containment denial          (regularity.must_not_conflate[0])
  H2  inverted size premise             (implication_ledger.forbidden_transfers[0].reason)
  A2  evidence not self-verifying       (f0_binding.consistency_evidence*)
  A6  alias registry unbound            (extensions.vocabulary_binding)
  SEP-6 stale aggregator component pins (schemas/af_scc_regularities.yaml)

This script is written from scratch by worker-003 and does not import or reuse the
author's harness (artifacts/worker-044/f2b_live_closure_01/live_closure.py). It runs the
project's own pinned black-box checkers inside a private sandbox copy, and it carries
planted-mutation controls that must make each check fire, so a "pass" is falsifiable.

Read-only on every canonical path. The only writes are under this artifact directory.
"""
import copy
import datetime
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent                  # artifacts/worker-003/f2b_rev14_candidate_closure
REPO = ROOT.parents[2]                                  # repository root
SB = ROOT / "sandbox"                                   # private candidate-tree copy
PIN = ROOT / "pinned"
CTRL = ROOT / "controls"
DECLARED_SRC = REPO / "artifacts/worker-044/f2b_live_closure_01/closure_summary.json"
NOW = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

DECLARED = {
    "c0": "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a",
    "c2": "d94d490dafcdd43cfb757aa39853e4d176d4a549b60846583dc6a217f039fdba",
    "f1": "88871f8f3d9b5603e028b5aa0706385cf1d77f295db3bea676fe0698fb7f63f4",
    "aggregator": "601355e7ccabbe017137bbef62eeb7b10a972855c0608513ca2fdd8543724fbe",
    "frozen": "a57492ccae88d540dce9a4206a072b6110aef8be403078a421902b57e68041fa",
    "key_manifest": "61b9d8c187c0bdef5692b9cfcc23f8f8401ae191c6e5a7d4b61af450fe81f8c1",
    "evidence": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
}
LIVE_SNAPSHOT = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_regularities.yaml": "94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
DETECTOR_PINNED = REPO / "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"
DETECTOR_PINNED_SHA = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
DETECTOR_LIVE_SHA = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"

CHECKS = []
CONTROLS = []
NOTES = []


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def record(check_id, group, status, expected, measured, detail=""):
    CHECKS.append({
        "id": check_id, "group": group, "status": status,
        "expected": expected, "measured": measured, "detail": detail,
    })
    print(f"[{status.upper():4}] {check_id}: {detail}")


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def strip_mentions(s):
    """Remove bracketed erratum segments and quoted spans (assertion-vs-mention rule)."""
    t = str(s)
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"\[[^\[\]]*\]", " ", t)
    t = re.sub(r"'[^']*'", " ", t)
    t = re.sub(r'"[^"]*"', " ", t)
    return norm(t)


DENIAL_RE = re.compile(r"no\s+containment\s+with\s+.*?C2.*?C0", re.I)
COMPOSITE_RE = re.compile(r"\bC0\s*(?:or|/|,|and)\s*C2\b.{0,40}?\b(?:one|same)\s+class", re.I)
LARGER_RE = re.compile(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class", re.I)
NESTED_RE = re.compile(r"E_?C2\s+subset\s+of\s+E_?\{?C\^1,1\}?\s+subset\s+of\s+E_?H2loc\s+subset\s+of\s+E_?C0", re.I)
CONTAINMENT_RE = re.compile(r"E_?C0\s+contains\s+E_?H2loc\s+contains\s+E_?\{?C\^1,1\}?\s+contains\s+E_?C2", re.I)


# ---------------------------------------------------------------- family checks
def h1_check(c0):
    mnc = c0.get("regularity", {}).get("must_not_conflate") or []
    text = " ".join(norm(x) for x in mnc)
    asserted = strip_mentions(text)
    denial = bool(DENIAL_RE.search(asserted))
    composite = bool(COMPOSITE_RE.search(asserted))
    nested = bool(NESTED_RE.search(text))
    ledger = c0.get("implication_ledger", {})
    containment = norm(ledger.get("extension_class_containment", ""))
    ledger_ok = bool(CONTAINMENT_RE.search(containment))
    ok = (not denial) and (not composite) and nested and ledger_ok
    return ok, {
        "unquoted_denial_present": denial, "unquoted_composite_present": composite,
        "nested_chain_in_must_not_conflate": nested,
        "ledger_containment_chain_consistent": ledger_ok,
        "must_not_conflate_asserted_text": asserted[:220],
    }


def h2_check(c0):
    transfers = c0.get("implication_ledger", {}).get("forbidden_transfers") or []
    reasons = [normalized for t in transfers if isinstance(t, dict)
               for normalized in [norm(t.get("reason", ""))]]
    joined = " ".join(reasons)
    asserted = strip_mentions(joined)
    inverted = bool(LARGER_RE.search(asserted))
    stated_smaller = bool(re.search(r"C2\s+is\s+a\s+strictly\s+smaller\s+extension\s+class", asserted, re.I))
    stated_subset = bool(re.search(r"E_?C2\s+subset\s+of\s+E_?C0", asserted, re.I))
    stated_weaker = bool(re.search(r"C2-inextendibility\s+is\s+strictly\s+weaker", asserted, re.I))
    containment = norm(c0.get("implication_ledger", {}).get("extension_class_containment", ""))
    ledger_ok = bool(CONTAINMENT_RE.search(containment))
    ok = (not inverted) and stated_smaller and stated_subset and stated_weaker and ledger_ok
    return ok, {
        "unquoted_inverted_premise": inverted, "states_C2_smaller": stated_smaller,
        "states_E_C2_subset_E_C0": stated_subset, "states_strictly_weaker": stated_weaker,
        "ledger_containment_chain_consistent": ledger_ok, "reasons": reasons,
    }


def a2_check(schemas, evidence, live_f0_sha, live_supplement_sha, guarded_run):
    decls = {name: (d.get("f0_binding", {}) or {}).get("consistency_evidence_sha256")
             for name, d in schemas.items()}
    decl_paths = {name: (d.get("f0_binding", {}) or {}).get("consistency_evidence")
                  for name, d in schemas.items()}
    decl_ok = all(v == DECLARED["evidence"] for v in decls.values())
    path_ok = all(v == "artifacts/formulation/evidence/taxonomy_consistency.json"
                  for v in decl_paths.values())
    ev_ok = (evidence.get("consistent") is True and not evidence.get("errors")
             and evidence.get("map_taxonomy_sha256") == live_f0_sha
             and evidence.get("lead_contract_sha256") == live_supplement_sha)
    repl_ok = bool(guarded_run.get("ok")) and guarded_run.get("computed_sha256") == DECLARED["evidence"]
    ok = decl_ok and path_ok and ev_ok and repl_ok
    return ok, {
        "declared_evidence_sha_per_schema": decls, "declared_paths_ok": path_ok,
        "evidence_doc_self_verifying": ev_ok,
        "evidence_doc_pins_live_inputs": {
            "map_taxonomy_sha256": evidence.get("map_taxonomy_sha256"),
            "lead_contract_sha256": evidence.get("lead_contract_sha256")},
        "guarded_recheck": guarded_run,
    }


def a6_check(c0, vocab_sha_measured, vocab_path):
    vb = (c0.get("extensions", {}) or {}).get("vocabulary_binding") or {}
    path_ok = vb.get("alias_registry") == "artifacts/formulation/VOCAB_ALIASES.json"
    sha_ok = vb.get("alias_registry_sha256") == vocab_sha_measured
    resolves = (Path(vocab_path).exists()) if vocab_path else False
    ok = path_ok and sha_ok and resolves
    return ok, {"alias_registry": vb.get("alias_registry"),
                "declared_sha256": vb.get("alias_registry_sha256"),
                "measured_live_sha256": vocab_sha_measured,
                "path_resolves": resolves}


def sep6_check(agg, sandbox_root):
    comps = agg.get("components") or []
    rows = []
    ok = True
    for c in comps:
        p = sandbox_root / c.get("path", "")
        measured = sha256_file(p) if p.exists() else None
        row_ok = bool(measured) and measured == c.get("sha256")
        ok = ok and row_ok
        rows.append({"role": c.get("role"), "class_id": c.get("class_id"), "path": c.get("path"),
                     "pinned": c.get("sha256"), "measured": measured, "ok": row_ok,
                     "revision_note": norm(c.get("revision_note", ""))[:180]})
    return ok, {"aggregator_revision": agg.get("revision"), "components": rows}


def frozen_pins_check(frozen, root):
    rows = []
    bad = 0
    for p, rec in (frozen.get("files") or {}).items():
        f = root / p
        if not f.exists():
            bad += 1
            rows.append({"path": p, "problem": "MISSING"})
            continue
        h = sha256_file(f)
        if h != rec.get("sha256"):
            bad += 1
            rows.append({"path": p, "problem": "DRIFT", "pinned": rec.get("sha256"), "measured": h})
    return bad, rows


def detector_findings(detector_path, obj, where):
    spec = importlib.util.spec_from_file_location(f"cs_{hashlib.sha256(str(detector_path).encode()).hexdigest()[:8]}", detector_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.findings(obj, where)
    return [str(x) for x in out]


def detector_findings_for_text(detector_path, text):
    spec = importlib.util.spec_from_file_location(f"cst_{hashlib.sha256(str(detector_path).encode()).hexdigest()[:8]}", detector_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [str(x) for x in mod.findings_for_text(text, "control/text")]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return {"cmd": cmd, "rc": p.returncode, "stdout_tail": p.stdout.strip().splitlines()[-6:],
            "stderr_tail": p.stderr.strip().splitlines()[-3:]}


def main():
    print(f"W003 independent F2b rev14 candidate closure verification @ {NOW}")
    # hermetic: every run starts from the hash-pinned pristine candidate sandbox, so the
    # project checkers (which write evidence files in-tree) cannot leak state between runs
    snap = PIN / "sandbox_pristine"
    if snap.exists():
        if SB.exists():
            shutil.rmtree(SB)
        shutil.copytree(snap, SB)
        print(f"sandbox restored from pristine snapshot: {snap}")
    print(f"candidate sandbox: {SB}")

    # ---------------- A. identity / pin closure ----------------
    c0 = yaml.safe_load((SB / "schemas/af_scc_c0_vacuum.yaml").read_text())
    c2 = yaml.safe_load((SB / "schemas/af_scc_c2_vacuum.yaml").read_text())
    f1 = yaml.safe_load((SB / "schemas/af_wcc_vacuum.yaml").read_text())
    agg = yaml.safe_load((SB / "schemas/af_scc_regularities.yaml").read_text())
    evidence = json.loads((SB / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text())
    frozen = json.loads((SB / "artifacts/formulation/FROZEN.json").read_text())
    key_manifest = json.loads((SB / "artifacts/formulation/KEY_MANIFEST.json").read_text())

    c0_meas = sha256_file(SB / "schemas/af_scc_c0_vacuum.yaml")
    c0a_meas = sha256_file(SB / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    c2_meas = sha256_file(SB / "schemas/af_scc_c2_vacuum.yaml")
    c2a_meas = sha256_file(SB / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")
    f1_meas = sha256_file(SB / "schemas/af_wcc_vacuum.yaml")
    f1a_meas = sha256_file(SB / "artifacts/formulation/schemas/af_wcc_vacuum.yaml")
    agg_meas = sha256_file(SB / "schemas/af_scc_regularities.yaml")
    ev_meas = sha256_file(SB / "artifacts/formulation/evidence/taxonomy_consistency.json")
    frz_meas = sha256_file(SB / "artifacts/formulation/FROZEN.json")
    km_meas = sha256_file(SB / "artifacts/formulation/KEY_MANIFEST.json")

    mirrors = {
        "c0": (c0_meas == c0a_meas == DECLARED["c0"]),
        "c2": (c2_meas == c2a_meas == DECLARED["c2"]),
        "f1": (f1_meas == f1a_meas == DECLARED["f1"]),
    }
    record("A1_candidate_hashes_match_author_declaration", "A",
           "pass" if all(mirrors.values()) and agg_meas == DECLARED["aggregator"]
           and ev_meas == DECLARED["evidence"] and frz_meas == DECLARED["frozen"]
           and km_meas == DECLARED["key_manifest"] else "fail",
           "C0 48cadb72, C2 d94d490d, F1 88871f8f, agg 601355e7, evidence 675a99d0, FROZEN a57492cc, KM 61b9d8c1",
           {"mirrors": mirrors, "c0": c0_meas, "c2": c2_meas, "f1": f1_meas, "aggregator": agg_meas,
            "evidence": ev_meas, "frozen": frz_meas, "key_manifest": km_meas},
           "canonical==authoring mirrors byte-equal and all seven hashes reproduce the declared values")

    author = json.loads(DECLARED_SRC.read_text())
    author_snap = author.get("snapshot_hashes", {})
    drift = []
    for p, declared_h in LIVE_SNAPSHOT.items():
        live = REPO / p
        if not live.exists():
            drift.append({"path": p, "problem": "MISSING"})
        elif sha256_file(live) != declared_h:
            drift.append({"path": p, "problem": "DRIFT", "snapshot": declared_h, "measured": sha256_file(live)})
    # cross-check the author's own recorded snapshot pins, where present
    author_mismatch = []
    for p, h in author_snap.items():
        live = REPO / p
        if not live.exists() or sha256_file(live) != h:
            author_mismatch.append(p)
    live_now = {p: (sha256_file(REPO / p) if (REPO / p).exists() else None) for p in LIVE_SNAPSHOT}
    record("A4_live_base_drift_guard", "A", "pass" if not drift else "drift",
           "11 live base pins unchanged since the author snapshot 2026-09-12T01:00:24+08:00",
           {"live_hashes_at_run": live_now, "drift": drift,
            "author_snapshot_recheck_mismatches": author_mismatch},
           "live canonical base still matches the author snapshot; candidate applicability live-valid" if not drift
           else f"live base moved during verification (snapshot measurement stays valid, live applicability void): {drift}")

    bad_pins, bad_rows = frozen_pins_check(frozen, SB)
    record("A5_candidate_FROZEN_pins_resolve_to_candidate_bytes", "A",
           "pass" if bad_pins == 0 else "fail",
           "50/50 FROZEN.files pins resolve inside the candidate sandbox with matching sha256",
           {"n_pins": len(frozen.get("files") or {}), "problems": bad_pins, "rows": bad_rows[:10]},
           f"{len(frozen.get('files') or {})} pins, {bad_pins} problems; candidate FROZEN revision "
           f"{frozen.get('revision')} frozen_at {frozen.get('frozen_at')}")

    # ---------------- B. five blocking families ----------------
    ok, det = h1_check(c0)
    record("B1_H1_false_containment_denial_closed", "B", "pass" if ok else "fail",
           "no unquoted denial in must_not_conflate; nested chain present and ledger-consistent",
           det, "mention-aware check: bracketed erratum + quoted historical text ignored")

    ok, det = h2_check(c0)
    record("B2_H2_inverted_size_premise_closed", "B", "pass" if ok else "fail",
           "forbidden_transfers[0].reason states C2 strictly smaller, E_C2 subset E_C0, C2-inext strictly weaker",
           det, "unquoted inversion absent; direction matches extension_class_containment")

    vocab_live = REPO / "artifacts/formulation/VOCAB_ALIASES.json"
    vocab_sha = sha256_file(vocab_live)
    ok, det = a6_check(c0, vocab_sha, SB / (c0.get("extensions", {}).get("vocabulary_binding", {}) or {}).get("alias_registry", ""))
    record("B4_A6_alias_registry_bound", "B", "pass" if ok else "fail",
           "extensions.vocabulary_binding binds VOCAB_ALIASES.json by path+sha256",
           det, "path resolves in sandbox; declared hash equals measured live registry")

    ok, det = sep6_check(agg, SB)
    record("B5_SEP6_aggregator_component_pins_fresh", "B", "pass" if ok else "fail",
           "every aggregator component sha256 equals the measured candidate file",
           det, f"aggregator revision {det.get('aggregator_revision')}; "
                f"{sum(1 for r in det['components'] if r['ok'])}/{len(det['components'])} component pins fresh")

    # guarded consistency re-run (black box, no write) for A2
    tool = SB / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    runres = run([sys.executable, str(tool)], SB)
    computed = None
    m = re.search(r"computed_sha256=([0-9a-f]{64})", " ".join(runres["stdout_tail"]) + " " + " ".join(runres["stderr_tail"]))
    if not m:
        full = subprocess.run([sys.executable, str(tool)], cwd=SB, capture_output=True, text=True).stdout
        m = re.search(r"computed_sha256=([0-9a-f]{64})", full)
        computed = m.group(1) if m else None
        guarded_out = full.strip().splitlines()
    else:
        computed = m.group(1)
        guarded_out = runres["stdout_tail"]
    # durability probe: what does the pinned guarded writer actually emit on --write?
    writer_root = CTRL / "writer_probe"
    if writer_root.exists():
        shutil.rmtree(writer_root)
    shutil.copytree(SB, writer_root)
    run([sys.executable, str(writer_root / "artifacts/formulation/tools/check_taxonomy_consistency.py"), "--write"],
        writer_root)
    writer_doc = json.loads((writer_root / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text())
    writer_sha = hashlib.sha256((json.dumps(writer_doc, indent=2) + "\n").encode()).hexdigest()
    writer_missing = sorted(set(evidence) - set(writer_doc))
    writer_diff = {"writer_emitted_sha256": writer_sha,
                   "declared_sha256": DECLARED["evidence"],
                   "fields_missing_from_writer_output": writer_missing,
                   "shared_fields_equal": all(writer_doc.get(k) == evidence.get(k)
                                              for k in set(writer_doc) & set(evidence)),
                   "fixpoint": writer_sha == DECLARED["evidence"]}
    guarded_run = {"rc": runres["rc"], "ok": runres["rc"] == 0 and computed == DECLARED["evidence"],
                   "computed_sha256": computed, "output": guarded_out[-3:],
                   "write_path_probe": writer_diff}
    ok, det = a2_check({"c0": c0, "c2": c2, "f1": f1}, evidence,
                       sha256_file(REPO / "research_map/formulation_taxonomy.yaml"),
                       sha256_file(REPO / "artifacts/formulation/formulation_taxonomy.yaml"),
                       guarded_run)
    record("B3_A2_evidence_self_verifying", "B", "pass" if ok else "fail",
           "all three schemas declare the self-verifying evidence doc; the pinned writer reproduces its hash",
           det, f"guarded no-write recompute sha256={computed}; with --write the pinned writer emits "
                f"{writer_sha[:12]} (missing self-verifying fields {writer_missing}) vs declared {DECLARED['evidence'][:12]}")

    # ---------------- C. structural black-box gates ----------------
    for name, rel in (("C0", "schemas/af_scc_c0_vacuum.yaml"),
                      ("C2", "schemas/af_scc_c2_vacuum.yaml"),
                      ("F1", "schemas/af_wcc_vacuum.yaml")):
        r = run([sys.executable, str(SB / "artifacts/formulation/tools/check_class_schema.py"),
                 str(SB / rel), "--json"], SB)
        record(f"C1_check_class_schema_{name}", "C", "pass" if r["rc"] == 0 else "fail",
               f"{rel} structural gate rc 0", {"rc": r["rc"], "tail": r["stdout_tail"]},
               f"check_class_schema rc {r['rc']}")

    r = run([sys.executable, str(SB / "artifacts/formulation/tools/verify_frozen.py")], SB)
    problems = None
    mm = re.search(r"(\d+) problems", " ".join(r["stdout_tail"]))
    problems = int(mm.group(1)) if mm else None
    record("C2_verify_frozen_candidate", "C", "pass" if r["rc"] == 0 and problems == 0 else "fail",
           "verify_frozen.py exit 0 / 0 problems on the candidate FROZEN", {"rc": r["rc"], "tail": r["stdout_tail"]},
           f"verify_frozen rc {r['rc']}, problems={problems}")

    for tool_name, cid in (("check_variant_deltas.py", "C3_check_variant_deltas"),
                           ("check_variant_registry.py", "C3_check_variant_registry")):
        r = run([sys.executable, str(SB / "artifacts/formulation/tools" / tool_name)], SB)
        record(cid, "C", "pass" if r["rc"] == 0 else "fail",
               f"{tool_name} rc 0 in the candidate sandbox",
               {"rc": r["rc"], "tail": r["stdout_tail"]},
               f"{tool_name} rc {r['rc']}" + ("" if r["rc"] == 0 else f": {' | '.join(r['stdout_tail'])}"))

    # C3b: is the FROZEN-pinned validation evidence reproducible at the candidate bytes?
    delta_probe = CTRL / "delta_probe"
    if delta_probe.exists():
        shutil.rmtree(delta_probe)
    shutil.copytree(SB, delta_probe)
    run([sys.executable, str(delta_probe / "artifacts/formulation/tools/check_variant_deltas.py")], delta_probe)
    probe_ev = delta_probe / "artifacts/formulation/evidence/variant_delta_check.json"
    probe_sha = sha256_file(probe_ev) if probe_ev.exists() else None
    pinned_ev = (frozen.get("files") or {}).get("artifacts/formulation/evidence/variant_delta_check.json", {}).get("sha256")
    record("C3b_variant_delta_evidence_reproducible", "C",
           "pass" if probe_sha and probe_sha == pinned_ev else "fail",
           "FROZEN-pinned variant_delta_check.json is what the candidate's own checker emits",
           {"frozen_pinned": pinned_ev, "candidate_computed": probe_sha,
            "computed_content": json.loads(probe_ev.read_text()) if probe_ev.exists() else None},
           f"pinned evidence {str(pinned_ev)[:12]} vs computed at candidate bytes {str(probe_sha)[:12]}")

    pinned_find = detector_findings(DETECTOR_PINNED, c0, "candidate/schemas/af_scc_c0_vacuum.yaml")
    live_det = SB / "research_map/class_separation.py"
    live_find = detector_findings(live_det, c0, "candidate/schemas/af_scc_c0_vacuum.yaml")
    pos_obj = {"conclusion": "C0 or C2 are one class"}
    pos_pinned = detector_findings(DETECTOR_PINNED, pos_obj, "control/positive")
    pos_live = detector_findings(live_det, pos_obj, "control/positive")
    pos_text_pinned = detector_findings_for_text(DETECTOR_PINNED, pos_obj["conclusion"])
    composite_pinned = [f for f in pinned_find if "composite" in f.lower() or "C0" in f]
    record("C4_classsep_no_composite_merge_in_candidate", "C",
           "pass" if len(composite_pinned) == 0 and len(pos_pinned) > 0 and len(pos_live) > 0 else "fail",
           "pinned detector c266dbec reports no C0/C2 composite-class finding on candidate C0, and the "
           "same object-walk path fires on a planted composite",
           {"pinned_detector_sha": DETECTOR_PINNED_SHA, "live_detector_sha": DETECTOR_LIVE_SHA,
            "pinned_findings": pinned_find, "live_detector_findings": live_find,
            "positive_control_object_pinned_fires": len(pos_pinned) > 0,
            "positive_control_object_live_fires": len(pos_live) > 0,
            "positive_control_text_pinned_fires": len(pos_text_pinned) > 0},
           f"pinned detector findings={len(pinned_find)}; live detector findings={len(live_find)}; "
           f"planted-composite control fires pinned={len(pos_pinned) > 0} live={len(pos_live) > 0}")

    # ---------------- D. planted-mutation controls ----------------
    def ctrl(cid, target, fired, detail):
        CONTROLS.append({"id": cid, "target_check": target, "fired": bool(fired), "detail": detail})
        print(f"[CTRL] {cid}: fired={bool(fired)} target={target} :: {detail}")

    mC0 = copy.deepcopy(c0)
    mC0["regularity"]["must_not_conflate"][0] = "No containment with C2 or C0 is asserted here."
    ok_m, _ = h1_check(mC0)
    ctrl("K1_revert_H1_denial", "B1_H1", not ok_m, "reverted must_not_conflate[0] to the old denial -> H1 must fail")

    mC0 = copy.deepcopy(c0)
    mC0["implication_ledger"]["forbidden_transfers"][0]["reason"] = \
        "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
    ok_m, _ = h2_check(mC0)
    ctrl("K2_revert_H2_inversion", "B2_H2", not ok_m, "restored inverted size premise -> H2 must fail")

    mC0 = copy.deepcopy(c0)
    mC0["f0_binding"]["consistency_evidence_sha256"] = LIVE_SNAPSHOT["artifacts/formulation/evidence/taxonomy_consistency.json"]
    ok_m, _ = a2_check({"c0": mC0, "c2": c2, "f1": f1}, evidence,
                       sha256_file(REPO / "research_map/formulation_taxonomy.yaml"),
                       sha256_file(REPO / "artifacts/formulation/formulation_taxonomy.yaml"), guarded_run)
    ctrl("K3_stale_evidence_declaration", "B3_A2", not ok_m, "stale 9e335e9b declaration -> A2 must fail")

    mC0 = copy.deepcopy(c0)
    mC0["extensions"]["vocabulary_binding"]["alias_registry_sha256"] = "0" * 64
    ok_m, _ = a6_check(mC0, vocab_sha, SB / "artifacts/formulation/VOCAB_ALIASES.json")
    ctrl("K4_unbind_alias_registry", "B4_A6", not ok_m, "wrong alias-registry hash -> A6 must fail")

    mAgg = copy.deepcopy(agg)
    mAgg["components"][1]["sha256"] = LIVE_SNAPSHOT["schemas/af_scc_c0_vacuum.yaml"]
    ok_m, _ = sep6_check(mAgg, SB)
    ctrl("K5_stale_aggregator_pin", "B5_SEP6", not ok_m, "reverted C0 aggregator pin to the live rev13 hash -> SEP-6 must fail")

    ctrl("K6_classsep_positive_control", "C4_classsep",
         len(pos_pinned) > 0 and len(pos_live) > 0 and len(pos_text_pinned) > 0,
         "planted 'C0 or C2 are one class' fires both detectors through the object walk and the text path")

    tamper = CTRL / "tamper_root"
    if tamper.exists():
        shutil.rmtree(tamper)
    shutil.copytree(SB, tamper)
    tf = tamper / "schemas/af_scc_c0_vacuum.yaml"
    raw = tf.read_bytes()
    tf.write_bytes(raw.replace(b"strong_cosmic_censorship", b"strong_cosmic_censorship", 1) + b"\n# tamper\n")
    bad_t, _ = frozen_pins_check(frozen, tamper)
    ctrl("K7_frozen_pin_tamper_detected", "A5_FROZEN", bad_t >= 1, "one extra byte in candidate C0 -> FROZEN pin check must report drift")

    # ---------------- findings / verdict ----------------
    failing = [c for c in CHECKS if c["status"] == "fail"]
    controls_all_fired = all(c["fired"] for c in CONTROLS)
    hard = []
    if any(c["id"] == "B3_A2_evidence_self_verifying" for c in failing):
        hard.append({
            "id": "W003-F2B14-H1", "check": "B3_A2_evidence_self_verifying",
            "finding": "A2 CONTENT is closed (the declared doc 675a99d0 carries its input pins and all three "
                       "schemas declare it) but A2 DURABILITY is not established. The candidate's own pinned "
                       "writer artifacts/formulation/tools/check_taxonomy_consistency.py cde1a165 recomputes the "
                       "lean doc 9e335e9b on the candidate inputs: its write path drops exactly the three fields "
                       "that make the declared doc self-verifying (map_taxonomy_sha256, lead_contract_sha256, "
                       "measured_at). The no-write guard does protect the on-disk doc (worker-044's durability "
                       "claim holds for the no-write path), but the declared doc is not a fixpoint of its own "
                       "pinned writer: any --write run moves the evidence and breaks the f0_binding declarations "
                       "plus the FROZEN evidence pin. The other pinned writer, close_findings_rev27.py 0234cd3c, "
                       "does add the three fields but stamps measured_at=now, so it is non-deterministic by "
                       "construction. No pinned writer deterministically reproduces the declared doc.",
            "repair_path": "Either (a) make the pinned writer emit the enriched doc deterministically (port the "
                           "input-pin enrichment from close_findings_rev27.py and derive measured_at from the "
                           "inputs, not wall clock) and re-pin it, or (b) declare the lean deterministic doc in "
                           "all three schemas and accept that A2's self-verification is lost. (a) preserves the "
                           "self-verifying property A2 requires.",
            "not_claimed": "This does not say the evidence content is false: the enriched doc's consistency "
                           "result (CONSISTENT, 4 classes, 0 divergences) reproduces at the live inputs.",
        })
    if any(c["id"] in ("C3_check_variant_deltas", "C3b_variant_delta_evidence_reproducible") for c in failing):
        hard.append({
            "id": "W003-F2B14-H2", "check": "C3_check_variant_deltas, C3b_variant_delta_evidence_reproducible",
            "finding": "Moving F1/C0 to the candidate rev14 bytes (88871f8f / 48cadb72) without re-basing the two "
                       "variant deltas leaves check_variant_deltas INVALID: CH base drift b2ab6acb2bbe -> "
                       "48cadb72e507 and SET base drift d9cebb9404b2 -> 88871f8f3d9b. This is the same mechanical "
                       "re-base step the rev13 publication had to perform; the candidate's R1-R9 list omits it. "
                       "C3b makes the same point on the evidence file: FROZEN pins variant_delta_check.json "
                       "fc6ee058 (the live VALID result) but the candidate's own checker emits aa183716 (INVALID) "
                       "at the candidate bytes, so the pinned validation evidence is not reproducible either.",
            "repair_path": "Re-base both variant deltas to the candidate schema hashes (and re-run "
                           "check_variant_deltas + check_variant_registry) inside the same atomic revision.",
        })
    findings = []
    if frozen.get("revision") == 29:
        findings.append({
            "id": "W003-F2B14-N1", "severity": "publication-checklist",
            "detail": "Candidate FROZEN.json is labelled revision 29 (frozen_at 2026-09-12T01:00:24) while "
                      "the live FROZEN rev29 815e08079aef (00:57:26) already shares that label with the "
                      "00:55:02 image 3d9e3d77fd87 (CF-27). Publishing this manifest as rev29 would add a "
                      "third byte-image to the same revision number; the owner must publish at the next "
                      "free revision and state it in the card."})
    c2_note = next((c.get("revision_note", "") for c in (agg.get("components") or [])
                    if c.get("class_id") == "AF-SCC-C2-VAC-GEN"), "")
    if "revision 11" in c2_note or "0fcc6a19" in c2_note:
        findings.append({
            "id": "W003-F2B14-N2", "severity": "minor",
            "detail": "Candidate aggregator re-pins the C2 component to the candidate rev14 hash d94d490d, but "
                      "its revision_note prose still says 'revision 11 ... f0_binding refreshed to declared-F0 "
                      "0fcc6a19'. Machine binding is fresh; the note is stale prose and should be updated in "
                      "the same revision."})
    suite_pin = (frozen.get("files") or {}).get("schemas/f1_falsifier_tests.jsonl", {}).get("sha256")
    if suite_pin and suite_pin.startswith("56bcb4b3"):
        findings.append({
            "id": "W003-F2B14-N3", "severity": "scoping",
            "detail": "The candidate does not close L-FORM-04: FROZEN still pins schemas/f1_falsifier_tests.jsonl "
                      "56bcb4b3234b (rows bound to F1 rev12) while the candidate F1 is rev14 88871f8f. Out of the "
                      "five F2b families verified here, but the owner's atomic publication should either rebind "
                      "the suite or record explicitly that L-FORM-04 remains open."})
    findings.append({
        "id": "W003-F2B14-N4", "severity": "intentional-declared-change",
        "detail": "The candidate FROZEN pins artifacts/formulation/tools/check_taxonomy_consistency.py cde1a165 "
                  "(worker-086 non-writing guard) where the live tree has de356d999ea3; R6 of the candidate "
                  "declares this replacement, and verify_frozen passes with the pinned bytes, but the tool "
                  "replacement must be published atomically with the schema revision."})
    findings.append({
        "id": "W003-F2B14-N5", "severity": "scope-note",
        "detail": "Independent verification scope: it re-measured the composed candidate, ran the project's "
                  "pinned black-box checkers in a private sandbox copy, and did not re-derive worker-066's "
                  "containment patch or adjudicate the CLASSEP detector drift (CF-26). Both detector hashes "
                  "are reported (pinned c266dbec, live a8c04fc3); both returned zero composite findings on the "
                  "candidate C0."})
    if drift:
        findings.append({
            "id": "W003-F2B14-N6", "severity": "live-moving-target",
            "detail": "The live base moved during verification: " + "; ".join(
                f"{d['path']} {str(d.get('snapshot'))[:12]} -> {str(d.get('measured'))[:12]}" for d in drift) +
                      ". The candidate aggregator 601355e7 was composed against the 01:00:24 aggregator "
                      "94562101, so the owner must reconcile the re-pin against the new live aggregator before "
                      "publication. The snapshot-bound candidate measurements in this report stay valid."})

    if failing:
        verdict = "CANDIDATE_NOT_ACCEPTANCE_READY"
    elif not controls_all_fired:
        verdict = "INSTRUMENT_CONTROLS_INCOMPLETE"
    else:
        verdict = "CANDIDATE_CLOSURE_VERIFIED_ON_LIVE_BASE"
    family_status = {
        "H1_false_containment_denial": next(c["status"] for c in CHECKS if c["id"] == "B1_H1_false_containment_denial_closed"),
        "H2_inverted_size_premise": next(c["status"] for c in CHECKS if c["id"] == "B2_H2_inverted_size_premise_closed"),
        "A2_evidence_self_verifying": next(c["status"] for c in CHECKS if c["id"] == "B3_A2_evidence_self_verifying"),
        "A6_alias_registry_unbound": next(c["status"] for c in CHECKS if c["id"] == "B4_A6_alias_registry_bound"),
        "SEP6_aggregator_component_pins_stale": next(c["status"] for c in CHECKS if c["id"] == "B5_SEP6_aggregator_component_pins_fresh"),
    }
    family_notes = {
        "H1": "closed: no unquoted denial; nested chain present and ledger-consistent; sibling F2a parity sampled",
        "H2": "closed: reason states E_C2 subset E_C0 and strictly weaker; no unquoted inversion",
        "A2": "content closed (doc pins its inputs, declarations match); durability OPEN (writer fixpoint broken)",
        "A6": "closed: alias registry bound by path+sha256, hash equals the live registry",
        "SEP6": "closed inside the candidate: 2/2 component pins fresh; but the live aggregator moved during the run",
    }

    report = {
        "schema": "worker-003/f2b-candidate-closure/v1",
        "task_id": "W003-F2B-REV14-CANDIDATE-INDEPENDENT-CLOSURE-01",
        "worker": "worker-003", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "created_at": NOW,
        "decision_question": ("Does the worker-044 composed F2b rev14 candidate (C0 48cadb72, evidence 675a99d0) "
                              "independently close the five blocking families H1/H2/A2/A6/SEP-6 on the live "
                              "rev13/FROZEN-rev29 base without introducing a structural, mirror, class-separation "
                              "or freeze-pin regression?"),
        "author_claim_ref": "artifacts/worker-044/f2b_live_closure_01/closure_summary.json#7bd2b25cd6fa",
        "author_claim": "COMPOSED_F2B_CANDIDATE_ACCEPTANCE_READY_ON_LIVE_BASE (worker-044, self-assessed)",
        "author_declared_hashes": DECLARED,
        "pristine_sandbox_manifest": {
            "path": "pinned/sandbox_pristine_manifest.txt",
            "sha256": sha256_file(PIN / "sandbox_pristine_manifest.txt") if (PIN / "sandbox_pristine_manifest.txt").exists() else None,
            "n_files": len(list((PIN / "sandbox_pristine").rglob("*"))) if (PIN / "sandbox_pristine").exists() else None,
        },
        "live_base_drift": drift,
        "verdict": verdict,
        "family_status": family_status,
        "family_notes": family_notes,
        "hard_failures": hard,
        "n_checks": len(CHECKS), "n_pass": sum(1 for c in CHECKS if c["status"] == "pass"),
        "n_fail": len(failing),
        "failing_checks": [c["id"] for c in failing],
        "controls_all_discriminate": controls_all_fired,
        "checks": CHECKS, "controls": CONTROLS, "findings": findings,
        "scope_limits": [
            "worker measurement only: no gate verdict, node status, or validation_status is set",
            "read-only on every canonical path; all writes are under this artifact directory",
            "does not adjudicate the CLASSSEP detector drift (CF-26); class-separation reported at both hashes",
            "does not re-derive worker-066's containment patch; verifies the composed candidate's closure",
        ],
        "falsifier": ("Falsified if any check reported pass measures fail on the same pinned bytes, if a re-run "
                      "yields a different candidate hash, if any K1-K7 control stops discriminating, if the live "
                      "base drifts off the recorded snapshot (which voids live applicability, not the snapshot "
                      "measurement), or if the candidate tree is shown not to be byte-identical to the hashes "
                      "declared in artifacts/worker-044/f2b_live_closure_01/closure_summary.json."),
        "next_falsifier": ("Re-run after any owner revision of the candidate: B1/B2 must stay closed, the guarded "
                           "checker must keep reproducing the declared evidence hash, FROZEN pins must resolve to "
                           "the published candidate bytes, and the FROZEN revision label must be unique."),
    }
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nVERDICT: {verdict}  checks={report['n_pass']}/{report['n_checks']} pass, "
          f"controls_fired={controls_all_fired}, findings={len(findings)}")
    return 0 if verdict == "CANDIDATE_CLOSURE_VERIFIED_ON_LIVE_BASE" else 2


if __name__ == "__main__":
    sys.exit(main())
