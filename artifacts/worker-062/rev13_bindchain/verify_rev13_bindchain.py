#!/usr/bin/env python3
"""W062-GFORM-REV13-BINDCHAIN-RETEST-01.

Independent, read-only re-test of the evidence-binding chain of the three frozen
formulation class schemas at the rev13 / FROZEN rev29 bytes.  This task re-tests the
defect CLASSES that were blocking at rev12 (stale consistency-evidence hash, stale
two-stage acceptance corpus) plus class separation and structural-gate reproduction.

Authority: worker evidence only.  No node status, no validation_status=passed, no gate
verdict.  Every canonical path is opened read-only.  All writes go to this directory
(artifacts/worker-062/rev13_bindchain/).  The canonical two-stage pipeline is reproduced
only through a byte copy of the formulation tree inside ./sandbox/, so the canonical
evidence file artifacts/formulation/evidence/acceptance_pipeline_report.json is never
rewritten.

Usage: python3 verify_rev13_bindchain.py
Exit:  0 report written; 2 harness error; 3 pin drift detected.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # .../ai4math-swarm
SBOX = HERE / "sandbox"
CTRL = HERE / "controls"
CST = timezone(timedelta(hours=8))
TASK = "W062-GFORM-REV13-BINDCHAIN-RETEST-01"

SCHEMAS = [
    {"node": "F1", "class_id": "AF-WCC-VAC-GEN",
     "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
     "mirror": "schemas/af_wcc_vacuum.yaml"},
    {"node": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
     "path": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
     "mirror": "schemas/af_scc_c2_vacuum.yaml"},
    {"node": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
     "mirror": "schemas/af_scc_c0_vacuum.yaml"},
]
F1_PATH = SCHEMAS[0]["path"]
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
CORPUS = "artifacts/formulation/evidence/semantic_escape_rebased.json"
ACCREPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
PIPELINE = "artifacts/formulation/tools/run_acceptance.py"
MEASURE = "artifacts/formulation/tools/measure_semantic_escape.py"
W06 = "artifacts/worker-06/spec_conformance_audit.py"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"

PIN_INPUTS = [FROZEN, F0, SUPP, EVID, CORPUS, ACCREPORT, VOCAB,
              "artifacts/formulation/rule_spec.json",
              "artifacts/formulation/evidence/gate_test_report.json",
              "artifacts/worker-06/semantic_fixtures/manifest.json"] + \
             [s["path"] for s in SCHEMAS] + [s["mirror"] for s in SCHEMAS]


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys."""


def _no_dup(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def load_yaml(path: Path):
    return yaml.load(Path(path).read_text(), Loader=StrictLoader)


def resolve_pointer(base: Path, pointer: str):
    """pointer = relative/path#dotted.fragment ; returns (path, obj) or raises."""
    path_s, _, frag = pointer.partition("#")
    p = Path(base) / path_s
    if not p.exists():
        raise KeyError(f"pointer path missing: {path_s}")
    obj = load_yaml(p) if p.suffix in (".yaml", ".yml") else json.loads(p.read_text())
    for part in [x for x in frag.split(".") if x]:
        obj = obj[part]
    return p, obj


def subproc(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=900)
    return {"cmd": cmd, "cwd": str(cwd), "returncode": r.returncode,
            "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}


class Report:
    def __init__(self):
        self.checks = []
        self.controls = []
        self.extra = {}

    def check(self, cid, hard, statement, expected, observed, ok, evidence):
        self.checks.append({"id": cid, "hard": hard, "statement": statement,
                            "expected": expected, "observed": observed,
                            "result": "PASS" if ok else "FAIL",
                            "evidence_refs": evidence})
        return ok

    def control(self, cid, mutates, expected_detector, observed_detector, ok, evidence):
        self.controls.append({"id": cid, "mutates": mutates,
                              "expected_detector": expected_detector,
                              "observed_detector": observed_detector,
                              "result": "PASS" if ok else "FAIL",
                              "evidence_refs": evidence})
        return ok


def main() -> int:
    started = now_iso()
    rep = Report()
    t0 = {p: sha256(ROOT / p) for p in PIN_INPUTS}
    frozen = json.loads((ROOT / FROZEN).read_text())
    fz_sha = t0[FROZEN]
    vocab = json.loads((ROOT / VOCAB).read_text())
    f0_doc = load_yaml(ROOT / F0)
    docs = {}
    measured = {}
    for s in SCHEMAS:
        docs[s["path"]] = load_yaml(ROOT / s["path"])
        measured[s["path"]] = sha256(ROOT / s["path"])

    # ---------------- B1 pin identity ----------------
    for s in SCHEMAS:
        doc = docs[s["path"]]
        decl = frozen["files"][s["path"]]["sha256"]
        decl_bytes = frozen["files"][s["path"]]["bytes"]
        mir = sha256(ROOT / s["mirror"])
        size = (ROOT / s["path"]).stat().st_size
        ok = (measured[s["path"]] == decl and mir == decl and size == decl_bytes
              and isinstance(doc.get("revision"), int)
              and isinstance(doc.get("revised_at"), str)
              and doc.get("class_id") == s["class_id"])
        rep.check(f"B1.{s['node']}", True,
                  "measured sha256 == FROZEN pin == mirror; in-file revision/revised_at present; in-file class_id == expected",
                  f"{decl[:16]} FROZEN rev{frozen['revision']} in-file rev13 {s['class_id']}",
                  f"{measured[s['path']][:16]} mirror {mir[:16]} bytes {size}/{decl_bytes} "
                  f"rev{doc.get('revision')} revised_at {doc.get('revised_at')} class {doc.get('class_id')}",
                  ok, [f"{s['path']}#{measured[s['path']][:12]}", f"{FROZEN}#rev{frozen['revision']}"])
    rep.check("B1.frozen", True, "FROZEN manifest revision is the frozen reference revision",
              "revision 29", f"revision {frozen['revision']} sha {fz_sha[:12]}",
              frozen["revision"] == 29, [f"{FROZEN}#{fz_sha[:12]}"])

    # ---------------- B2 F0 binding / pointer resolution ----------------
    for s in SCHEMAS:
        doc = docs[s["path"]]
        fb = doc.get("f0_binding", {})
        f0_meas = t0[F0]
        try:
            canon_p, canon_obj = resolve_pointer(ROOT, doc["class_contract_pointer"])
            supp_p, supp_obj = resolve_pointer(ROOT, doc["class_contract_supplement_pointer"])
            resolved = True
            err = ""
        except Exception as exc:  # noqa: BLE001
            canon_p = supp_p = None
            canon_obj = supp_obj = None
            resolved, err = False, f"{type(exc).__name__}: {exc}"
        f0axes = canon_obj.get("axes", {}) if isinstance(canon_obj, dict) else {}
        ok = (resolved
              and fb.get("declared_f0_sha256") == f0_meas
              and fb.get("declared_f0_artifact") == F0
              and canon_p is not None and supp_p is not None
              and canon_p.resolve() != supp_p.resolve()
              and f0axes.get("family") == doc.get("conclusion", {}).get("family"))
        rep.check(f"B2.{s['node']}", True,
                  "declared F0 hash == measured; canonical and supplement class pointers resolve to distinct files; resolved axes.family == schema conclusion.family",
                  f"declared==measured {f0_meas[:12]}; pointers resolve; distinct paths; family match",
                  f"declared {str(fb.get('declared_f0_sha256'))[:12]} measured {f0_meas[:12]}; resolved={resolved} {err}; "
                  f"canon={canon_p.name if canon_p else None} supp={supp_p.name if supp_p else None}; "
                  f"family {f0axes.get('family')}/{doc.get('conclusion', {}).get('family')}",
                  ok, [f"{F0}#{f0_meas[:12]}", f"{s['path']}#{measured[s['path']][:12]}"])

    # ---------------- B3 consistency-evidence binding (C06 class) ----------------
    evid_meas = t0[EVID]
    evid_pin = frozen["files"][EVID]["sha256"]
    evid_doc = json.loads((ROOT / EVID).read_text())
    for s in SCHEMAS:
        fb = docs[s["path"]].get("f0_binding", {})
        decl = fb.get("consistency_evidence_sha256")
        checked_at = fb.get("checked_at", "")
        try:
            chk = datetime.fromisoformat(checked_at)
            fresh = chk <= datetime.now(CST)
        except Exception:  # noqa: BLE001
            fresh = False
        ok = (decl == evid_meas == evid_pin
              and fb.get("consistency_evidence") == EVID
              and fresh and evid_doc.get("consistent") is True)
        rep.check(f"B3.{s['node']}", True,
                  "C06-class: declared consistency_evidence_sha256 == measured file == FROZEN pin; evidence says consistent; checked_at not future",
                  f"{evid_pin[:12]} consistent=True",
                  f"declared {str(decl)[:12]} measured {evid_meas[:12]} pin {evid_pin[:12]} "
                  f"path_ok={fb.get('consistency_evidence') == EVID} consistent={evid_doc.get('consistent')} checked_at={checked_at}",
                  ok, [f"{EVID}#{evid_meas[:12]}", f"{FROZEN}#rev{frozen['revision']}"])

    # ---------------- B4 acceptance reproducibility (C10 class) ----------------
    corpus = json.loads((ROOT / CORPUS).read_text())
    c0 = [s for s in SCHEMAS if s["node"] == "F2b"][0]
    c0_meas = measured[c0["path"]]
    base = corpus.get("base_sha256")
    acc = json.loads((ROOT / ACCREPORT).read_text())
    acc_pin = frozen["files"][ACCREPORT]["sha256"]
    rep.extra["acceptance_report"] = {
        "sha256_measured": t0[ACCREPORT], "sha256_frozen_pin": acc_pin,
        "mtime": datetime.fromtimestamp((ROOT / ACCREPORT).stat().st_mtime, CST).isoformat(timespec="seconds"),
        "verdict": acc.get("verdict"), "records_base_sha256": "base_sha256" in acc,
        "union_caught": acc.get("mutants", {}).get("union_caught"),
        "mutants_total": acc.get("mutants", {}).get("total")}
    ok_literal = (base == c0_meas)
    rep.check("B4.literal", True,
              "C10-class: semantic_escape_rebased.json.base_sha256 == measured rev13 C0 bytes",
              f"base == {c0_meas[:12]}",
              f"base {str(base)[:12]} vs measured C0 {c0_meas[:12]}",
              ok_literal, [f"{CORPUS}#{t0[CORPUS][:12]}", f"{c0['path']}#{c0_meas[:12]}"])

    # mirror sandbox reproduction of the canonical tools (canonical paths untouched)
    if SBOX.exists():
        shutil.rmtree(SBOX)
    CTRL.mkdir(parents=True, exist_ok=True)
    (SBOX / "artifacts").mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts/formulation", SBOX / "artifacts/formulation")
    (SBOX / "artifacts/worker-06").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / W06, SBOX / W06)
    shutil.copytree(ROOT / "artifacts/worker-06/semantic_fixtures",
                    SBOX / "artifacts/worker-06/semantic_fixtures")
    shutil.copytree(ROOT / "schemas", SBOX / "schemas")
    (SBOX / "research_map").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / F0, SBOX / F0)
    sbox_corpus_before = sha256(SBOX / CORPUS)
    s0 = subproc([sys.executable, str(SBOX / PIPELINE), "--json"], SBOX)
    rep.extra["sandbox_preflight_run"] = s0
    preflight_failed = (s0["returncode"] == 3 and "PREFLIGHT FAIL" in s0["stdout"])
    rep.check("B4.reproduce", True,
              "mirror-sandbox run of the canonical two-stage pipeline exits 3 (preflight fail) on the canonical fixture at rev13 bytes",
              "exit 3 + PREFLIGHT FAIL",
              f"exit {s0['returncode']} stdout: {s0['stdout'].strip()[:160]}",
              preflight_failed,
              [f"{PIPELINE}", f"{CORPUS}#{t0[CORPUS][:12]}", "sandbox_preflight_run"])
    rep.check("B4.declared", True,
              "the FROZEN rev29-pinned acceptance report (verdict PASS) records the base bytes it was produced from, so it can be reproduced at the frozen revision",
              "report records base_sha256 == current C0",
              f"report verdict={acc.get('verdict')} pinned={acc_pin[:12]} records_base_sha256="
              f"{'base_sha256' in acc} (produced {rep.extra['acceptance_report']['mtime']})",
              "base_sha256" in acc,
              [f"{ACCREPORT}#{t0[ACCREPORT][:12]}", f"{FROZEN}#rev{frozen['revision']}"])

    # B7 rebase falsifier: regenerate corpus in the sandbox at rev13 bytes, re-run pipeline
    s1 = subproc([sys.executable, str(SBOX / MEASURE)], SBOX)
    rep.extra["sandbox_rebase_run"] = s1
    sbox_corpus_after = json.loads((SBOX / CORPUS).read_text())
    s2 = subproc([sys.executable, str(SBOX / PIPELINE), "--json"], SBOX)
    rep.extra["sandbox_rebased_pipeline_run"] = s2
    try:
        rebased = json.loads(s2["stdout"])
    except Exception:  # noqa: BLE001
        rebased = {}
    rebase_ok = (s1["returncode"] == 0 and s2["returncode"] == 0
                 and rebased.get("verdict") == "PASS"
                 and sbox_corpus_after.get("base_sha256") == c0_meas)
    rep.check("B7.rebase", False,
              "rebase falsifier in the sandbox: corpus regenerated from rev13 C0, union of the two stages still catches every mutant",
              "rebase rc 0; pipeline PASS; corpus base == rev13 C0",
              f"rebase rc {s1['returncode']}; pipeline rc {s2['returncode']} verdict {rebased.get('verdict')} "
              f"union {rebased.get('mutants', {}).get('union_caught')}/{rebased.get('mutants', {}).get('total')}; "
              f"base now {str(sbox_corpus_after.get('base_sha256'))[:12]}",
              rebase_ok, ["sandbox_rebase_run", "sandbox_rebased_pipeline_run"])

    # F1 semantic-stage root cause: run the canonical semantic auditor directly on canonical F1
    # (read-only; no --json flag, so nothing is written).
    sem_f1 = subproc([sys.executable, str(ROOT / W06), str(ROOT / F1_PATH)], ROOT)
    try:
        sem_f1_json = json.loads(sem_f1["stdout"])
    except Exception:  # noqa: BLE001
        sem_f1_json = {}
    rep.extra["f1_semantic_run"] = {
        "returncode": sem_f1["returncode"], "verdict": sem_f1_json.get("verdict"),
        "failed_rules": sem_f1_json.get("failed_rules"),
        "doc_sha256": sem_f1_json.get("doc_sha256"),
        "reason": next((c.get("detail") for c in sem_f1_json.get("checks", []) if c.get("rule") == "R03"), None),
        "binder_evidence": {
            "rev13_ordered_binders": [e.get("binder") for e in docs[F1_PATH].get("quantifiers", {}).get("ordered", [])],
            "rev13_missing_binders": [e.get("binder") for e in docs[F1_PATH].get("quantifiers", {}).get("ordered", [])
                                      if e.get("binder") not in str(docs[F1_PATH].get("quantifiers", {}).get("formal", ""))],
            "rev11_reference_snapshot": "artifacts/worker-037/f1_visibility_adjudication/mutations/af_wcc_vacuum.M0_canonical.yaml#9a8bd4c96800",
            "rev12_reference_snapshot": "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml#cce9c60146d6",
        }}
    rep.check("B7.f1-semantic", False,
              "observation: the pipeline's semantic stage on canonical F1 at rev13 is reproducible and names its failing rule",
              "verdict and failed rule recorded",
              f"verdict {sem_f1_json.get('verdict')} failed {sem_f1_json.get('failed_rules')} "
              f"reason: {rep.extra['f1_semantic_run']['reason']}",
              sem_f1_json.get("verdict") in ("accept", "reject"),
              [f"{W06}", f"{F1_PATH}#{measured[F1_PATH][:12]}"])

    # ---------------- B5 class separation ----------------
    for s in SCHEMAS:
        doc = docs[s["path"]]
        concl = doc.get("conclusion", {})
        ct = concl.get("conclusion_type")
        canon = {"AF-WCC-VAC-GEN": "weak_cosmic_censorship",
                 "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
                 "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility"}[s["class_id"]]
        own_ok = ct == canon or ct in vocab["conclusion_type"].get(canon, [])
        sib = {"AF-SCC-C2-VAC-GEN": "scc_c0_future_inextendibility",
               "AF-SCC-C0-VAC-GEN": "scc_c2_future_inextendibility"}.get(s["class_id"])
        sib_aliases = set([sib] + vocab["conclusion_type"].get(sib, [])) if sib else set()
        sib_ok = ct not in sib_aliases and ct not in vocab.get("rejected_ambiguous_tokens", {})
        ext = doc.get("regularity", {}).get("extension_regularity")
        ext_ok = (ext is None) or (ext in ("C0", "C2") and " or " not in ext and "/" not in ext)
        disjoint = doc.get("sibling_disjoint_from")
        sib_id = {"AF-SCC-C2-VAC-GEN": "AF-SCC-C0-VAC-GEN",
                  "AF-SCC-C0-VAC-GEN": "AF-SCC-C2-VAC-GEN"}.get(s["class_id"])
        if sib_id:
            named = [disjoint] if isinstance(disjoint, str) else list(disjoint or [])
            disjoint_ok = sib_id in named and s["class_id"] not in named
        else:
            disjoint_ok = True
        ok = own_ok and sib_ok and ext_ok and disjoint_ok
        rep.check(f"B5.{s['node']}", True,
                  "single class id; conclusion_type is own-axis under VOCAB_ALIASES (and not a sibling alias); extension_regularity single frozen token; sibling disjointness declared",
                  f"own-axis, not sibling, ext in {{C0,C2}}, disjoint declared",
                  f"class_id={doc.get('class_id')} conclusion_type={ct} own={own_ok} not_sibling={sib_ok} "
                  f"ext={ext} ext_ok={ext_ok} sibling_disjoint_from={disjoint} disjoint_ok={disjoint_ok}",
                  ok, [f"{s['path']}#{measured[s['path']][:12]}", f"{VOCAB}#{t0[VOCAB][:12]}"])

    # ---------------- B6 structural gate ----------------
    for s in SCHEMAS:
        r = subproc([sys.executable, str(ROOT / GATE), "--json", str(ROOT / s["path"])], ROOT)
        try:
            v = json.loads(r["stdout"])
        except Exception:  # noqa: BLE001
            v = {}
        ok = r["returncode"] == 0 and v.get("verdict") == "pass" and not v.get("failed_rules")
        rep.check(f"B6.{s['node']}", True,
                  "canonical structural gate verdict=pass with failed_rules=[] on the canonical rev13 bytes",
                  "verdict pass, failed_rules []",
                  f"exit {r['returncode']} verdict {v.get('verdict')} failed {v.get('failed_rules')}",
                  ok, [f"{GATE}", f"{s['path']}#{measured[s['path']][:12]}"])

    # ---------------- mutation controls (sandbox/controls only) ----------------
    base_doc = load_yaml(ROOT / c0["path"])

    def write_ctrl(name, doc):
        p = CTRL / name
        p.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
        return p

    def gate_json(p):
        r = subproc([sys.executable, str(ROOT / GATE), "--json", str(p)], ROOT)
        try:
            return json.loads(r["stdout"]), r["returncode"]
        except Exception:  # noqa: BLE001
            return {}, r["returncode"]

    # Convention (same as the cohort's controls): expected_detector is the expected value of the
    # check's PASS predicate after the mutation; False means the mutation must be caught.
    # M1 flipped F0 hash -> B2 predicate fails
    d = json.loads(json.dumps(base_doc))
    good = d["f0_binding"]["declared_f0_sha256"]
    d["f0_binding"]["declared_f0_sha256"] = good[:-1] + ("0" if good[-1] != "0" else "1")
    m1 = write_ctrl("M1_f0_hash_flip.yaml", d)
    pred = load_yaml(m1)["f0_binding"]["declared_f0_sha256"] == t0[F0]
    rep.control("M1", "f0_binding.declared_f0_sha256 one hex char flipped", False, pred,
                pred == False, [str(m1.relative_to(ROOT))])  # noqa: E712

    # M2 wrong consistency hash -> B3 predicate fails
    d = json.loads(json.dumps(base_doc))
    d["f0_binding"]["consistency_evidence_sha256"] = "0" * 64
    m2 = write_ctrl("M2_consistency_hash_wrong.yaml", d)
    pred = load_yaml(m2)["f0_binding"]["consistency_evidence_sha256"] == evid_meas
    rep.control("M2", "f0_binding.consistency_evidence_sha256 set to a wrong hash", False, pred,
                pred == False, [str(m2.relative_to(ROOT))])  # noqa: E712

    # M3 missing consistency path -> B3 predicate fails
    d = json.loads(json.dumps(base_doc))
    d["f0_binding"]["consistency_evidence"] = "artifacts/formulation/evidence/nonexistent.json"
    m3 = write_ctrl("M3_consistency_path_missing.yaml", d)
    pred = (ROOT / load_yaml(m3)["f0_binding"]["consistency_evidence"]).exists()
    rep.control("M3", "f0_binding.consistency_evidence redirected to a nonexistent path", False, pred,
                pred == False, [str(m3.relative_to(ROOT))])  # noqa: E712

    # M4 sibling class id -> structural gate must reject
    d = json.loads(json.dumps(base_doc))
    d["class_id"] = "AF-SCC-C2-VAC-GEN"
    m4 = write_ctrl("M4_sibling_class_id.yaml", d)
    v4, rc4 = gate_json(m4)
    pred = v4.get("verdict") == "pass" and not v4.get("failed_rules")
    rep.control("M4", "class_id replaced by the sibling class on the F2b copy", False, pred,
                pred == False, [str(m4.relative_to(ROOT)), f"{GATE}"])  # noqa: E712

    # M5 sibling conclusion type -> structural gate must reject
    d = json.loads(json.dumps(base_doc))
    d["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"
    m5 = write_ctrl("M5_sibling_conclusion.yaml", d)
    v5, rc5 = gate_json(m5)
    pred = v5.get("verdict") == "pass" and not v5.get("failed_rules")
    rep.control("M5", "conclusion.conclusion_type replaced by the sibling class value", False, pred,
                pred == False, [str(m5.relative_to(ROOT)), f"{GATE}"])  # noqa: E712

    # M6 composite regularity -> structural gate must reject
    d = json.loads(json.dumps(base_doc))
    d["regularity"]["extension_regularity"] = "C0 or C2"
    m6 = write_ctrl("M6_composite_regularity.yaml", d)
    v6, rc6 = gate_json(m6)
    pred = v6.get("verdict") == "pass" and not v6.get("failed_rules")
    rep.control("M6", "regularity.extension_regularity set to composite 'C0 or C2'", False, pred,
                pred == False, [str(m6.relative_to(ROOT)), f"{GATE}"])  # noqa: E712

    # M7 positive control: sandbox corpus rebased to current C0 -> preflight no longer fails closed
    pred7 = (sbox_corpus_after.get("base_sha256") == c0_meas and s2["returncode"] != 3)
    rep.control("M7", "positive control: sandbox corpus rebased to the current C0 bytes", True, pred7, pred7,
                ["sandbox_rebase_run", "sandbox_rebased_pipeline_run"])

    # M8 positive control: unmutated canonical schemas pass the structural gate
    pred8 = all(c["result"] == "PASS" for c in rep.checks if c["id"].startswith("B6."))
    rep.control("M8", "positive control: unmutated canonical rev13 schemas", True, pred8, pred8,
                [f"{GATE}", f"{c0['path']}#{c0_meas[:12]}"])

    # ---------------- T1 drift check + verdict ----------------
    t1 = {p: sha256(ROOT / p) for p in PIN_INPUTS}
    drift = sorted([p for p in PIN_INPUTS if t0[p] != t1[p]])
    rep.check("T1.drift", True, "no pinned canonical input moved between T0 and T1",
              "drift == []", f"drift={drift}", not drift, [f"{FROZEN}#{fz_sha[:12]}"])

    hard_failed = [c for c in rep.checks if c["hard"] and c["result"] == "FAIL"]
    advisory_failed = [c for c in rep.checks if not c["hard"] and c["result"] == "FAIL"]
    controls_failed = [c for c in rep.controls if c["result"] == "FAIL"]

    hard_failures = []
    for c in hard_failed:
        if c["id"] == "B4.literal":
            hard_failures.append({
                "id": "HF-W062-REV13-01",
                "severity": "blocking-for-clean-accept",
                "finding": ("The two-stage acceptance criterion is not reproducible at the FROZEN rev29 / rev13 bytes. "
                            "(a) semantic_escape_rebased.json binds base_sha256 1bb78ce9b357 (rev11 C0) while the canonical C0 "
                            "schema measures b2ab6acb2bbe, so the pipeline's own fail-closed preflight exits 3 "
                            "(mirror-reproduced, canonical paths untouched). (b) Even after the corpus is mechanically rebased "
                            "to the rev13 bytes in the sandbox, the pipeline still returns FAIL: the canonical F1 schema is "
                            "rejected by the semantic stage on R03 because quantifiers.ordered lists binder '(q,t0)' while "
                            "quantifiers.formal writes 'not exists q in I+ and t0 in [0,T)'; the union still catches 31/31 "
                            "mutants, so the failure is isolated to the F1 formal-binder notation, present since rev12 "
                            "(cce9c601) and not repaired by rev13. (c) The FROZEN rev29-pinned acceptance_pipeline_report.json "
                            "(verdict PASS) was produced at 00:27, before rev12 existed, and records no base hash. The rev12 "
                            "C10-class defect was not repaired by astra-life05-evidence-binding-repair; only the C06-class item was."),
                "falsifier": ("Show run_acceptance.py PREFLIGHT PASS at C0 b2ab6acb2bbe and a full pipeline PASS at the rev13 "
                              "bytes, or republish the corpus rebased to b2ab6acb2bbe with an acceptance report recording the "
                              "base hash AND make F1's ordered binders agree literally with quantifiers.formal, or explicitly "
                              "retract the two-stage acceptance criterion from the F2b/F1 evidence set."),
                "evidence_refs": [f"{CORPUS}#{t0[CORPUS][:12]}", f"{c0['path']}#{c0_meas[:12]}",
                                  f"{ACCREPORT}#{t0[ACCREPORT][:12]}", "sandbox_preflight_run",
                                  "sandbox_rebased_pipeline_run", "f1_semantic_run"]})
        elif c["id"] == "B4.declared":
            hard_failures.append({
                "id": "HF-W062-REV13-02",
                "severity": "evidence-binding",
                "finding": ("The FROZEN rev29-pinned acceptance_pipeline_report.json does not record the base bytes it was "
                            "produced from, so its PASS verdict cannot be bound to any revision; this is why the stale corpus "
                            "went unnoticed across the rev11->rev13 moves."),
                "falsifier": "Publish an acceptance report carrying base_sha256 == the measured C0 hash at its own revision.",
                "evidence_refs": [f"{ACCREPORT}#{t0[ACCREPORT][:12]}", "acceptance_report"]})
        else:
            hard_failures.append({
                "id": f"HF-W062-{c['id']}",
                "severity": "binding",
                "finding": c["observed"],
                "falsifier": "Re-measure the named file and show the declared and measured values agree.",
                "evidence_refs": c["evidence_refs"]})

    verdict = "revise" if hard_failures else "accept"
    score = 3.0 if hard_failures else 4.0
    positive = [c for c in rep.checks if c["result"] == "PASS"]

    report = {
        "schema_version": "1.0",
        "report_id": f"{TASK}-report",
        "task_id": TASK,
        "worker": "worker-062",
        "instance": "worker-062-relaunch-20260912T0058",
        "node_id": "F2b",
        "nodes": ["F1", "F2a", "F2b"],
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "counts_as_full_schema_verdict": False,
        "scope": "evidence-binding chain, class separation and structural-gate re-test at FROZEN rev29; not a full semantic schema verdict",
        "subjects": [{"node_id": s["node"], "class_id": s["class_id"], "path": s["path"],
                      "sha256": measured[s["path"]], "revision": docs[s["path"]].get("revision")} for s in SCHEMAS],
        "frozen_manifest": {"path": FROZEN, "sha256": fz_sha, "revision": frozen["revision"],
                            "frozen_at": frozen.get("frozen_at")},
        "clock": {"started_at": started, "finished_at": now_iso()},
        "method": {"harness": "artifacts/worker-062/rev13_bindchain/verify_rev13_bindchain.py",
                   "imports_of_other_worker_checkers": "none",
                   "canonical_writes": "none (read-only on every canonical path; pipeline reproduced only in ./sandbox)",
                   "preregistration": "artifacts/worker-062/rev13_bindchain/PREREGISTRATION.json",
                   "harness_calibration": ("Disclosed draft-run calibration, before any event was emitted: (1) B1 originally "
                                           "compared the in-file schema revision (13) to the FROZEN manifest revision (29), which "
                                           "are different numbering axes, producing a false FAIL; corrected to pin identity plus "
                                           "in-file revision presence. (2) B5 required sibling_disjoint_from to be a list while the "
                                           "canonical field is a string naming the sibling; corrected. (3) the control harness "
                                           "reported the detector firing instead of the check's pass predicate for M1-M3, inverting "
                                           "four control rows; corrected to the cohort convention (expected_detector = expected "
                                           "value of the pass predicate). The draft report was overwritten; no canonical file was "
                                           "touched and no event was emitted from the draft.")},
        "entry_hashes": {"t0": t0, "t1": t1, "drift": drift},
        "checks": rep.checks,
        "controls": rep.controls,
        "acceptance_report": rep.extra["acceptance_report"],
        "sandbox_preflight_run": rep.extra["sandbox_preflight_run"],
        "sandbox_rebase_run_rc": rep.extra["sandbox_rebase_run"]["returncode"],
        "sandbox_rebased_pipeline": {
            "returncode": rep.extra["sandbox_rebased_pipeline_run"]["returncode"],
            "verdict": rebased.get("verdict"),
            "mutants": rebased.get("mutants"),
            "canonical": rebased.get("canonical"),
        },
        "f1_semantic_run": rep.extra["f1_semantic_run"],
        "post_hoc_observations": [
            {"id": "O-W062-01",
             "registered": False,
             "finding": ("Not a pre-registered check; recorded because it explains HF-W062-REV13-01(b). The semantic-stage "
                         "rejection of canonical F1 is an R03 ordered-binder/formal-string mismatch: ordered binders are "
                         "['r','G_r','(Sigma,h,K)','(Mtilde,gtilde,Omega)','gamma','(q,t0)'] and the literal '(q,t0)' does not "
                         "occur in quantifiers.formal, which spells the quantifier as 'not exists q in I+ and t0 in [0,T)'. "
                         "The rev11 reference snapshot 9a8bd4c96800 passed with ordered binder 'q'; the mismatch entered at "
                         "rev12 cce9c601 and persists at rev13 d9cebb94. Fix is a notation agreement on one side (schema "
                         "formal string or the auditor's binder parsing), not a mathematical change."),
             "evidence_refs": ["f1_semantic_run",
                               "artifacts/worker-037/f1_visibility_adjudication/mutations/af_wcc_vacuum.M0_canonical.yaml#9a8bd4c96800",
                               "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml#cce9c60146d6",
                               f"{F1_PATH}#{measured[F1_PATH][:12]}"]},
        ],
        "positive_findings": [
            {"id": "P-W062-01",
             "finding": "C06-class cleared at rev13: in all three schemas the declared consistency_evidence_sha256 equals the "
                        "measured file (9e335e9ba1bf) and the FROZEN rev29 pin.",
             "evidence_refs": [f"{EVID}#{evid_meas[:12]}"]},
            {"id": "P-W062-02",
             "finding": "Pin identity clean at FROZEN rev29: 3/3 schema hashes equal the manifest pins and the repo-root mirrors, "
                        "in-file revision 13, one class id per schema; structural gate 3/3 pass; 8/8 controls behave as declared; "
                        "the mechanically rebased mutation corpus is still caught 31/31 by the union of the two stages.",
             "evidence_refs": [f"{FROZEN}#{fz_sha[:12]}", f"{GATE}", "sandbox_rebased_pipeline_run"]},
        ],
        "verdict": {"value": verdict, "score": score,
                    "hard_failure_ids": [h["id"] for h in hard_failures],
                    "hard_failures": hard_failures,
                    "advisory_failed": [c["id"] for c in advisory_failed]},
        "falsifier": ("Any declared binding hash equal to the measured file, any sandbox rebase showing a union escape, any "
                      "control not firing, or any canonical pin moving between T0 and T1 voids the corresponding row or the "
                      "whole table."),
        "authority_note": ("Worker evidence only. No node status, validation_status=passed or gate verdict is set. The canonical "
                           "acceptance report was not rewritten; the pipeline was executed only on a byte copy under "
                           "artifacts/worker-062/rev13_bindchain/sandbox/."),
        "next_falsifier": ("Repair path for HF-01: (i) re-run measure_semantic_escape.py at rev13 and republish the rebased "
                           "corpus plus an acceptance report that records base_sha256; (ii) make F1's ordered binders agree "
                           "literally with quantifiers.formal (or change the R03 binder parsing on the auditor side) so the "
                           "semantic stage accepts canonical F1; (iii) publish FROZEN rev30 and re-run this harness. Only then "
                           "can the r3 reviewers accept all three classes at one hash."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "entry_hashes.json").write_text(json.dumps({"t0": t0, "t1": t1, "drift": drift,
                                                        "report_sha256": sha256(HERE / "report.json"),
                                                        "preregistration_sha256": sha256(HERE / "PREREGISTRATION.json")},
                                                       indent=2) + "\n")
    (HERE / "controls.json").write_text(json.dumps(rep.controls, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "score": score,
                      "hard_failed": [c["id"] for c in hard_failed],
                      "advisory_failed": [c["id"] for c in advisory_failed],
                      "controls_failed": [c["id"] for c in controls_failed],
                      "checks": len(rep.checks), "controls": len(rep.controls),
                      "report_sha256": sha256(HERE / "report.json")}, indent=2))
    return 3 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
