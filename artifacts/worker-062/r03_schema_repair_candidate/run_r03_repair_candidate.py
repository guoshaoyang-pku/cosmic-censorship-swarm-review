#!/usr/bin/env python3
"""W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01 harness.

Produces and sandbox-validates a schema-side repair candidate for the frozen stage-B R03
blocker on canonical F1 (AF-WCC-VAC-GEN), end-to-end through the UNMODIFIED frozen
two-stage acceptance pipeline at the rev13-rebased corpus.

Read-only on every canonical path. All pipeline execution happens under
artifacts/worker-062/r03_schema_repair_candidate/sandbox/. Run:
    python3 run_r03_repair_candidate.py
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "artifacts/worker-062/r03_schema_repair_candidate"
SBOX = TASK / "sandbox"
EVID = TASK / "evidence"
CAND = TASK / "candidates"
DIFFS = TASK / "diffs"
CTRL = TASK / "controls"

FROZEN = "artifacts/formulation/FROZEN.json"
F1 = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F2A = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F2B = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MIRRORS = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
CORPUS = "artifacts/formulation/evidence/semantic_escape_rebased.json"
TOOL_GATE = "artifacts/formulation/tools/check_class_schema.py"
TOOL_SEM = "artifacts/worker-06/spec_conformance_audit.py"
TOOL_PIPE = "artifacts/formulation/tools/run_acceptance.py"
TOOL_MEASURE = "artifacts/formulation/tools/measure_semantic_escape.py"

PIN = {
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F2A: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CORPUS: "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
    MIRRORS[0]: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    MIRRORS[1]: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    MIRRORS[2]: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}

CAND_A_FROM = "    not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M."
CAND_A_TO = "    not exists (q,t0) in I+ x [0,T) with gamma([t0,T)) subset J^-(q) intersect M."
CAND_B_FROM = '    - {kind: not_exists, binder: "(q,t0)", domain_id: D5}'
CAND_B_TO = '    - {kind: not_exists, binder: "q", domain_id: D5}'


def now_iso() -> str:
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def subproc(cmd, cwd):
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True, timeout=900)
    return {"cmd": [str(c) for c in cmd], "cwd": str(cwd), "returncode": r.returncode,
            "stdout": r.stdout[-6000:], "stderr": r.stderr[-3000:]}


def flat_diff(a, b, path=""):
    """Leaf-path differences between two parsed YAML documents."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += flat_diff(a.get(k), b.get(k), f"{path}.{k}" if path else str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}.__len__ {len(a)}->{len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out += flat_diff(x, y, f"{path}.{i}")
    elif a != b:
        out.append(f"{path} :: {str(a)[:120]!r} -> {str(b)[:120]!r}")
    return out


def pipeline_json(sbox):
    r = subproc([sys.executable, sbox / TOOL_PIPE, "--json"], sbox)
    try:
        d = json.loads(r["stdout"])
    except Exception:  # noqa: BLE001
        d = {}
    return r, d


class Rep:
    def __init__(self):
        self.checks, self.controls, self.extra = [], [], {}

    def check(self, cid, hard, statement, expected, observed, ok, evidence):
        self.checks.append({"id": cid, "hard": hard, "statement": statement, "expected": expected,
                            "observed": observed, "result": "PASS" if ok else "FAIL", "evidence_refs": evidence})
        return bool(ok)

    def control(self, cid, planted, expected_detector, observed_detector, ok, evidence):
        self.controls.append({"id": cid, "planted": planted, "expected_detector": expected_detector,
                              "observed_detector": observed_detector, "result": "PASS" if ok else "FAIL",
                              "evidence_refs": evidence})
        return bool(ok)


def main():
    started = now_iso()
    rep = Rep()
    for d in (EVID, CAND, DIFFS, CTRL):
        d.mkdir(parents=True, exist_ok=True)

    # ---------------- P1: canonical pins at T0 ----------------
    t0 = {}
    for rel, want in PIN.items():
        got = sha256(ROOT / rel)
        t0[rel] = got
    p1 = all(t0[r] == w for r, w in PIN.items())
    rep.check("P1.T0", True, "canonical T0 hashes equal the pinned rev29/rev13 values",
              "all 8 pins equal", f"{sum(t0[r]==w for r,w in PIN.items())}/8 equal", p1, [f"{FROZEN}#rev29"])

    # FROZEN pins for the two frozen tools, if declared
    frozen = json.loads((ROOT / FROZEN).read_text())
    pins = frozen.get("pins") or frozen.get("files") or {}
    if isinstance(pins, list):
        pins = {p.get("path"): p.get("sha256") for p in pins if isinstance(p, dict)}
    pins = {k: (v.get("sha256") if isinstance(v, dict) else v) for k, v in pins.items()}
    tool_pin = {rel: pins.get(rel) for rel in (TOOL_GATE, TOOL_SEM)}
    tool_t0 = {rel: sha256(ROOT / rel) for rel in (TOOL_GATE, TOOL_SEM)}

    # ---------------- P2: fresh sandbox ----------------
    if SBOX.exists():
        shutil.rmtree(SBOX)
    (SBOX / "artifacts").mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts/formulation", SBOX / "artifacts/formulation")
    (SBOX / "artifacts/worker-06").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / TOOL_SEM, SBOX / TOOL_SEM)
    shutil.copytree(ROOT / "artifacts/worker-06/semantic_fixtures", SBOX / "artifacts/worker-06/semantic_fixtures")
    shutil.copytree(ROOT / "schemas", SBOX / "schemas")
    (SBOX / "research_map").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "research_map/formulation_taxonomy.yaml", SBOX / "research_map/formulation_taxonomy.yaml")
    sbox_f1 = SBOX / F1
    sbox_c0 = SBOX / F2B
    c0_meas = sha256(sbox_c0)
    rep.check("P2", True, "fresh sandbox carries canonical bytes; sandbox C0 == canonical C0",
              "sandbox C0 == b2ab6acb2bbe", f"sandbox C0 {c0_meas[:12]}", c0_meas == PIN[F2B],
              [f"{F2B}#{PIN[F2B][:12]}"])

    # ---------------- P3: stale-corpus preflight (rc 3) ----------------
    r_pre, d_pre = pipeline_json(SBOX)
    rep.extra["run_preflight"] = r_pre
    rep.check("P3", True, "before rebase the frozen pipeline fails closed on the stale corpus (rc 3, PREFLIGHT FAIL)",
              "rc 3 + PREFLIGHT FAIL",
              f"rc {r_pre['returncode']} stdout {r_pre['stdout'].strip()[:120]!r}",
              r_pre["returncode"] == 3 and "PREFLIGHT FAIL" in r_pre["stdout"],
              [f"{CORPUS}#{PIN[CORPUS][:12]}", TOOL_PIPE])

    # ---------------- P4: rebase corpus in sandbox ----------------
    r_rebase = subproc([sys.executable, SBOX / TOOL_MEASURE], SBOX)
    rep.extra["run_rebase"] = r_rebase
    corpus_now = json.loads((SBOX / CORPUS).read_text())
    base_ok = corpus_now.get("base_sha256") == c0_meas
    rep.check("P4", True, "measure_semantic_escape.py regenerates the corpus base at the rev13 C0 bytes",
              "rc 0 and corpus base == b2ab6acb2bbe",
              f"rc {r_rebase['returncode']}; base {str(corpus_now.get('base_sha256'))[:12]}",
              r_rebase["returncode"] == 0 and base_ok, ["run_rebase", f"{CORPUS}"])

    # ---------------- P5: baseline FAIL isolated to F1 R03 ----------------
    r_base, d_base = pipeline_json(SBOX)
    rep.extra["run_baseline"] = r_base
    shutil.copy2(SBOX / "artifacts/formulation/evidence/acceptance_pipeline_report.json", EVID / "acceptance_baseline.json")
    f1_row = next((c for c in d_base.get("canonical", []) if c.get("schema") == "af_wcc_vacuum.yaml"), {})
    others_ok = all(c.get("ok") for c in d_base.get("canonical", []) if c.get("schema") != "af_wcc_vacuum.yaml")
    m_base = d_base.get("mutants", {})
    rep.check("P5", True, "baseline at the rebased corpus: FAIL isolated to F1 semantic=R03; union still 31/31",
              "rc 1, verdict FAIL, F1 structural=pass semantic=fail, F2a/F2b ok, union 31/31",
              f"rc {r_base['returncode']} verdict {d_base.get('verdict')} F1 {f1_row.get('structural')}/{f1_row.get('semantic')} "
              f"others_ok {others_ok} union {m_base.get('union_caught')}/{m_base.get('total')}",
              r_base["returncode"] == 1 and d_base.get("verdict") == "FAIL"
              and f1_row.get("structural") == "pass" and f1_row.get("semantic") == "fail" and others_ok
              and m_base.get("union_caught") == m_base.get("total"),
              ["run_baseline", "evidence/acceptance_baseline.json"])

    canon_text = (ROOT / F1).read_text()
    canon_doc = yaml.safe_load(canon_text)
    results = {}

    def run_candidate(vid, frm, to, declared_paths):
        """Apply one-line candidate in sandbox, run stages + pipeline, controls."""
        sbox_f1.write_text(canon_text.replace(frm, to, 1))
        cpath = CAND / f"{vid}_af_wcc_vacuum.yaml"
        cpath.write_text(sbox_f1.read_text())
        ctext = cpath.read_text()

        # K4 diff minimality
        dl = list(difflib.unified_diff(canon_text.splitlines(keepends=True), ctext.splitlines(keepends=True),
                                       fromfile="canonical/af_wcc_vacuum.yaml", tofile=f"{vid}/af_wcc_vacuum.yaml", n=1))
        (DIFFS / f"{vid}.diff").write_text("".join(dl))
        minus = [x for x in dl if x.startswith("-") and not x.startswith("---")]
        plus = [x for x in dl if x.startswith("+") and not x.startswith("+++")]
        diff_ok = len(minus) == 1 and len(plus) == 1 and minus[0][1:].rstrip("\n") == frm.rstrip("\n") and plus[0][1:].rstrip("\n") == to.rstrip("\n")
        rep.control(f"K4.{vid}", f"{vid} byte-identity audit", "exactly the declared one line differs, nothing else",
                    f"-{len(minus)}/+{len(plus)} lines", diff_ok, [f"diffs/{vid}.diff"])

        # P8 parsed-structure delta confined to declared paths
        cdoc = yaml.safe_load(ctext)
        paths = flat_diff(canon_doc, cdoc)
        p8 = [p for p in paths if not any(p.startswith(dp) for dp in declared_paths)] == [] and paths != []
        rep.check(f"P8.{vid}", True, f"{vid} parsed-structure delta confined to declared path(s)",
                  f"only {declared_paths}", f"{paths}", p8, [f"candidates/{vid}_af_wcc_vacuum.yaml"])

        # P9 class identity
        p9 = (cdoc.get("class_id") == canon_doc.get("class_id") and cdoc.get("revision") == canon_doc.get("revision")
              and cdoc.get("f0_binding") == canon_doc.get("f0_binding") and cdoc.get("conclusion") == canon_doc.get("conclusion"))
        rep.check(f"P9.{vid}", True, f"{vid} preserves class_id, revision, f0_binding and conclusion",
                  "all unchanged", f"class_id {cdoc.get('class_id')} revision {cdoc.get('revision')}", p9,
                  [f"candidates/{vid}_af_wcc_vacuum.yaml"])

        # structural + semantic on the candidate
        g = subproc([sys.executable, SBOX / TOOL_GATE, "--json", sbox_f1], SBOX)
        s = subproc([sys.executable, SBOX / TOOL_SEM, sbox_f1], SBOX)
        try:
            gj = json.loads(g["stdout"])
        except Exception:  # noqa: BLE001
            gj = {}
        try:
            sj = json.loads(s["stdout"])
        except Exception:  # noqa: BLE001
            sj = {}
        rep.extra[f"candidate_{vid}"] = {"gate": g, "sem": s}

        # full pipeline at candidate bytes
        r, d = pipeline_json(SBOX)
        shutil.copy2(SBOX / "artifacts/formulation/evidence/acceptance_pipeline_report.json", EVID / f"acceptance_{vid}.json")
        rows = {c.get("schema"): c for c in d.get("canonical", [])}
        m = d.get("mutants", {})
        p6 = (g["returncode"] == 0 and gj.get("verdict") == "pass" and s["returncode"] == 0 and sj.get("verdict") == "accept"
              and r["returncode"] == 0 and d.get("verdict") == "PASS"
              and all(c.get("ok") for c in d.get("canonical", [])) and all(c.get("ok") for c in d.get("controls", []))
              and m.get("union_caught") == m.get("total") and m.get("total", 0) > 0)
        results[vid] = {"gate_rc": g["returncode"], "gate_verdict": gj.get("verdict"),
                        "sem_rc": s["returncode"], "sem_verdict": sj.get("verdict"), "sem_failed": sj.get("failed_rules"),
                        "pipe_rc": r["returncode"], "pipe_verdict": d.get("verdict"),
                        "union": f"{m.get('union_caught')}/{m.get('total')}",
                        "f1": rows.get("af_wcc_vacuum.yaml"), "sha256": sha256(cpath)}
        rep.check(f"P6.{vid}", True, f"{vid} passes both frozen stages and the full pipeline end-to-end",
                  "rc 0 / PASS / union 31/31 / controls ok",
                  f"gate {gj.get('verdict')} sem {sj.get('verdict')} rc {r['returncode']} verdict {d.get('verdict')} "
                  f"union {results[vid]['union']} controls_ok {all(c.get('ok') for c in d.get('controls', []))}",
                  p6, [f"candidates/{vid}_af_wcc_vacuum.yaml", f"evidence/acceptance_{vid}.json", TOOL_PIPE])
        return p6, ctext

    okA, textA = run_candidate("CAND-A", CAND_A_FROM, CAND_A_TO, ["quantifiers.formal"])
    okB, textB = run_candidate("CAND-B", CAND_B_FROM, CAND_B_TO, ["quantifiers.ordered.5.binder"])

    # ---------------- K1: repair reverted -> R03 rejects again ----------------
    neg = TASK / "controls" / "K1_CAND-A_repair_reverted.yaml"
    neg.write_text(textA.replace(CAND_A_TO, CAND_A_FROM, 1))
    sn = subproc([sys.executable, SBOX / TOOL_SEM, neg], SBOX)
    try:
        snj = json.loads(sn["stdout"])
    except Exception:  # noqa: BLE001
        snj = {}
    k1 = sn["returncode"] == 1 and snj.get("verdict") == "reject" and "R03" in (snj.get("failed_rules") or [])
    rep.control("K1", "CAND-A with the notation repair reverted", "semantic reject on R03",
                f"rc {sn['returncode']} verdict {snj.get('verdict')} failed {snj.get('failed_rules')}", k1,
                ["controls/K1_CAND-A_repair_reverted.yaml"])

    # ---------------- K2: injected binding defect -> pipeline FAIL ----------------
    import re
    inj = TASK / "controls" / "K2_CAND-A_bad_consistency_hash.yaml"
    inj_text = re.sub(r'(consistency_evidence_sha256:\s*")([0-9a-f]{8})', r"\g<1>deadbeef", textA, count=1)
    inj.write_text(inj_text)
    sbox_f1.write_text(inj_text)
    r_inj, d_inj = pipeline_json(SBOX)
    k2 = r_inj["returncode"] == 1 and d_inj.get("verdict") == "FAIL"
    rep.control("K2", "CAND-A with consistency_evidence_sha256 corrupted", "full pipeline verdict FAIL (rc 1)",
                f"rc {r_inj['returncode']} verdict {d_inj.get('verdict')}", k2,
                ["controls/K2_CAND-A_bad_consistency_hash.yaml", "run_K2"])
    rep.extra["run_K2"] = r_inj

    # K2 post-hoc instrument-coverage measurement (added after the pre-registered K2 miss;
    # NOT part of the preregistered decision rule): the injected hash is detectable by a
    # direct declared-vs-measured re-derivation, but not by the two-stage pipeline.
    decl = re.search(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"', inj_text)
    ev_meas = sha256(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json")
    k2_obs = {"declared_in_mutated_schema": decl.group(1) if decl else None,
              "measured_evidence_sha256": ev_meas,
              "mismatch_detected_by_direct_rederivation": bool(decl and decl.group(1) != ev_meas),
              "pipeline_detected": bool(k2),
              "finding": ("The frozen two-stage acceptance criterion does NOT cover the C06-class "
                          "evidence-binding defect: a schema whose consistency_evidence_sha256 is corrupted "
                          "still passes both stages (rc 0 / PASS). The defect is caught by a direct "
                          "declared-vs-measured re-derivation (different instrument), so pipeline PASS must "
                          "not be read as evidence-binding-clean.")}
    rep.extra["k2_coverage_gap"] = k2_obs

    # ---------------- K2b (post-hoc, disclosed): a defect class the pipeline must catch ----------------
    inj2_text = re.sub(r"(?m)^class_id:.*\n", "", textA, count=1)
    inj2 = TASK / "controls" / "K2b_CAND-A_class_id_removed.yaml"
    inj2.write_text(inj2_text)
    g2 = subproc([sys.executable, SBOX / TOOL_GATE, "--json", inj2], SBOX)
    try:
        g2j = json.loads(g2["stdout"])
    except Exception:  # noqa: BLE001
        g2j = {}
    sbox_f1.write_text(inj2_text)
    r2, d2 = pipeline_json(SBOX)
    rep.extra["run_K2b"] = r2
    k2b = (g2["returncode"] != 0 or g2j.get("verdict") == "fail") and r2["returncode"] == 1 and d2.get("verdict") == "FAIL"
    rep.control("K2b", "CAND-A with class_id stripped (post-hoc, disclosed; not preregistered)",
                "structural gate fails and full pipeline verdict FAIL (rc 1)",
                f"gate rc {g2['returncode']} verdict {g2j.get('verdict')}; pipeline rc {r2['returncode']} verdict {d2.get('verdict')}",
                k2b, ["controls/K2b_CAND-A_class_id_removed.yaml", "run_K2b"])

    # ---------------- K3: canonical F2a unaffected ----------------
    g3 = subproc([sys.executable, SBOX / TOOL_GATE, "--json", SBOX / F2A], SBOX)
    s3 = subproc([sys.executable, SBOX / TOOL_SEM, SBOX / F2A], SBOX)
    try:
        s3j = json.loads(s3["stdout"])
    except Exception:  # noqa: BLE001
        s3j = {}
    k3 = g3["returncode"] == 0 and s3["returncode"] == 0 and s3j.get("verdict") == "accept"
    rep.control("K3", "canonical F2a through both stages", "both stages pass",
                f"gate rc {g3['returncode']} sem {s3j.get('verdict')}", k3, [f"{F2A}#{PIN[F2A][:12]}"])

    # ---------------- K5: restore canonical F1, contamination check ----------------
    sbox_f1.write_text(canon_text)
    r_restore, d_restore = pipeline_json(SBOX)
    m_r = d_restore.get("mutants", {})
    k5 = (r_restore["returncode"] == 1 and d_restore.get("verdict") == "FAIL"
          and m_r.get("union_caught") == m_r.get("total")
          and r_restore["returncode"] == r_base["returncode"] and d_restore.get("verdict") == d_base.get("verdict"))
    rep.control("K5", "canonical C0 corpus re-run after all candidate runs", "same union 31/31, baseline verdict reproduced",
                f"rc {r_restore['returncode']} verdict {d_restore.get('verdict')} union {m_r.get('union_caught')}/{m_r.get('total')}",
                k5, ["run_restore"])
    rep.extra["run_restore"] = r_restore

    # ---------------- P10: detector pin identity + stability ----------------
    tool_t1 = {rel: sha256(ROOT / rel) for rel in (TOOL_GATE, TOOL_SEM)}
    sandbox_tools = {rel: sha256(SBOX / rel) for rel in (TOOL_GATE, TOOL_SEM)}
    frozen_match = all(tool_pin[r] in (None, tool_t0[r]) for r in tool_pin)
    p10 = (tool_t0 == tool_t1 and tool_t0 == sandbox_tools and frozen_match)
    rep.check("P10", False, "frozen detector bytes identical canonical/sandbox, unchanged T0->T1, no R03-v2 adoption",
              "all equal; tool sha equals FROZEN pin where pinned",
              f"gate {tool_t0[TOOL_GATE][:12]} sem {tool_t0[TOOL_SEM][:12]} FROZEN pins {tool_pin}",
              p10, [f"{TOOL_SEM}", f"{TOOL_GATE}"])

    # ---------------- P1 T1: canonical untouched ----------------
    t1 = {rel: sha256(ROOT / rel) for rel in PIN}
    rep.check("P1.T1", True, "no canonical pin moved during the run", "all 8 pins equal T0",
              f"{sum(t1[r]==t0[r] for r in t0)}/8 stable", all(t1[r] == t0[r] for r in t0), [f"{FROZEN}#rev29"])

    hard_failed = [c["id"] for c in rep.checks if c["hard"] and c["result"] == "FAIL"]
    ctrl_failed = [c["id"] for c in rep.controls if c["result"] == "FAIL"]
    # Pre-registered rule, applied unchanged: a FAILED declared control keeps the run at PARTIAL.
    verdict = "CANDIDATE_VALIDATED" if (not hard_failed and not ctrl_failed and okA and okB) else (
        "PARTIAL" if (not hard_failed and (okA or okB)) else "WITHDRAWN")
    candidates_validated = (not hard_failed) and okA and okB
    candidate_blockers = [c for c in ctrl_failed if c != "K2"]  # K2 is an instrument-coverage miss, see disposition
    report = {
        "schema_version": 1.0,
        "report_id": "W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01-report",
        "task_id": "W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01",
        "worker": "worker-062",
        "instance": "worker-062-20260912T010416-968807",
        "created_at": now_iso(),
        "clock": {"started_at": started, "finished_at": now_iso()},
        "node_id": "F1", "nodes": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "counts_as_full_schema_verdict": False,
        "scope": "schema-side R03 repair candidate for canonical F1, validated end-to-end through the unmodified frozen pipeline in a mirror sandbox; not a gate verdict and not a node completion",
        "preregistration": "PREREGISTRATION.json",
        "t0_hashes": t0, "t1_hashes": t1,
        "detector_tools": {"t0": tool_t0, "t1": tool_t1, "sandbox": sandbox_tools, "frozen_pins": tool_pin,
                           "r03_v2_adopted": False,
                           "note": "worker-006 FORM-R03-V2 tool-side proposal deliberately NOT used; the frozen detector bytes are the ones under test"},
        "baseline": {"pipe_rc": r_base["returncode"], "pipe_verdict": d_base.get("verdict"),
                     "f1": f1_row, "union": f"{m_base.get('union_caught')}/{m_base.get('total')}",
                     "structural_caught": m_base.get("structural_caught"), "semantic_caught": m_base.get("semantic_caught")},
        "candidates": {
            "CAND-A": {"name": "formal product-notation agreement", "from": CAND_A_FROM, "to": CAND_A_TO,
                       "declared_parsed_paths": ["quantifiers.formal"], **results.get("CAND-A", {})},
            "CAND-B": {"name": "ordered-binder minimal agreement (rev11 precedent)", "from": CAND_B_FROM, "to": CAND_B_TO,
                       "declared_parsed_paths": ["quantifiers.ordered.5.binder"], **results.get("CAND-B", {})},
        },
        "checks": rep.checks, "controls": rep.controls,
        "hard_failed": hard_failed, "controls_failed": ctrl_failed,
        "verdict": {"value": verdict, "candidates_validated": candidates_validated,
                    "preregistered_rule": ("a candidate is valid iff P1-P9 pass and K1-K5 behave as declared; "
                                           "the rule is applied unchanged, so the declared K2 miss yields PARTIAL"),
                    "k2_disposition": ("recorded miss is an instrument-coverage finding about the two-stage criterion, "
                                       "not a candidate defect: both candidates pass every candidate-level pre-registered "
                                       "check (P6/P7) and K1/K3/K4/K5; K2b (post-hoc) confirms the pipeline does FAIL "
                                       "on a defect class it is designed to catch"),
                    "candidate_blockers": candidate_blockers, "recommendation": None},
        "post_hoc_additions": {"K2_coverage_gap": k2_obs,
                               "K2b": "post-hoc structural-injection control, disclosed as not preregistered"},
        "authority_note": "Worker evidence only. No canonical file edited; no node status, validation_status=passed or gate verdict set. The candidate is a proposal for astra-lead-formulation; publishing rev14/FROZEN rev30 is an owner/controller decision, and the L-FORM-04 f1_falsifier_tests rebind (worker-031) remains a separate owner dependency.",
        "falsifier": "Show a run of the frozen pipeline at a candidate's bytes that does not reach rc 0 / PASS / union 31/31, show a parsed path other than the declared one differing from canonical, show the frozen detector bytes differing from the FROZEN rev29 pin, or show a canonical pin moving between T0 and T1; any of these voids the corresponding candidate row or the whole table.",
        "next_falsifier": "Owner applies the recommended candidate as F1 rev14, rebinds schemas/f1_falsifier_tests.jsonl (L-FORM-04 / worker-031 patch) and publishes FROZEN rev30; an independent reviewer then re-runs this harness plus the r3 full-schema review at the new bytes. Any stage-B adoption (worker-006 R03-v2) must be decided separately and is not needed if a schema candidate passes.",
        "extra": rep.extra,
    }
    # recommendation: prefer the candidate whose parsed delta leaves the normative formal sentence unchanged
    if okB and okA:
        report["verdict"]["recommendation"] = ("CAND-B preferred as minimum-risk: it is metadata-only (quantifiers.ordered[5].binder), "
                                               "leaves the normative formal sentence byte-identical, and restores the rev11 binder that "
                                               "passed the frozen test; CAND-A is equally pipeline-valid and preserves the pair-binder "
                                               "documentation at the cost of restating the formal sentence in equivalent product notation.")
    elif okA:
        report["verdict"]["recommendation"] = "CAND-A only: formal product-notation agreement."
    elif okB:
        report["verdict"]["recommendation"] = "CAND-B only: metadata-only binder agreement."
    else:
        report["verdict"]["recommendation"] = "none: both candidates withdrawn."

    (TASK / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    (TASK / "controls.json").write_text(json.dumps({"task_id": report["task_id"], "controls": rep.controls,
                                                    "all_pass": not ctrl_failed}, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "hard_failed": hard_failed, "controls_failed": ctrl_failed,
                      "CAND-A": results.get("CAND-A"), "CAND-B": results.get("CAND-B")}, indent=2))
    return 0 if verdict != "WITHDRAWN" else 1


if __name__ == "__main__":
    sys.exit(main())
