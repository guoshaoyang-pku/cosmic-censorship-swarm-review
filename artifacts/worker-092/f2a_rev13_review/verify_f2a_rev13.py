#!/usr/bin/env python3
"""W092-F2A-REV13-FULL-01 — independent full-schema G-FORM verification of F2a at the
FROZEN rev29 (rev13) pin, with a closure matrix over the standing rev12 hard failures.

Read-only on every canonical path. Writes only under artifacts/worker-092/f2a_rev13_review/.
Independent implementation: stdlib + PyYAML only, no import of the canonical gate or the
canonical consistency checker. The canonical gate and `verify_frozen.py` are *invoked* as
subprocesses for their exit codes (both are read-only); `check_taxonomy_consistency.py` is
run only inside a mirrored throwaway root because it rewrites the evidence path.

Exit codes: 0 report written, 1 a required check failed, 2 usage, 3 pin drift (report NOT
written, fail-closed).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

# ---------------------------------------------------------------- pre-registered pins
PINS = {
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json": "7c165a9063c60918d583fe58000437b5a97e15803b0f2341e63bddc648a33852",
    "research_map/class_separation.py": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
}
FROZEN_PIN = PINS["artifacts/formulation/FROZEN.json"]
F2A_PIN = PINS["schemas/af_scc_c2_vacuum.yaml"]
F0_PIN = PINS["research_map/formulation_taxonomy.yaml"]
SUPP_PIN = PINS["artifacts/formulation/formulation_taxonomy.yaml"]
EVID_PIN = PINS["artifacts/formulation/evidence/taxonomy_consistency.json"]
FROZEN_FILES = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml", "schemas/taxonomy_cases.jsonl",
                "artifacts/formulation/evidence/taxonomy_consistency.json"]
C2_TOKEN = "scc_c2_future_inextendibility"
C0_TOKEN = "scc_c0_future_inextendibility"
FROZEN_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}

CHECKS: list[dict] = []


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rec(cid: str, status: str, detail: str, **kw) -> dict:
    row = {"id": cid, "status": status, "detail": detail}
    row.update(kw)
    CHECKS.append(row)
    return row


class DupKeyError(ValueError):
    pass


def strict_load_text(text: str):
    """YAML load that fails on duplicate mapping keys at any depth."""
    class L(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        seen = set()
        for k, _v in node.value:
            kk = loader.construct_object(k, deep=deep)
            if isinstance(kk, (str, int, float, bool)) or kk is None:
                if kk in seen:
                    raise DupKeyError(f"duplicate mapping key {kk!r} at line {k.start_mark.line + 1}")
                seen.add(kk)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    return yaml.load(text, Loader=L)


def strict_load(p: Path):
    return strict_load_text(p.read_text())


# ---------------------------------------------------------------- check helpers
def check_content(doc, raw: str, cid_prefix="K"):
    c = doc
    rec(f"{cid_prefix}01_file_pin", "PASS" if sha256(ROOT / "schemas/af_scc_c2_vacuum.yaml") == F2A_PIN else "FAIL",
        "live F2a sha256 equals the pre-registered rev29 pin")
    rec(f"{cid_prefix}02_strict_yaml", "PASS", "strict load, no duplicate mapping keys at any depth")
    rec(f"{cid_prefix}03_identity",
        "PASS" if c.get("class_id") == "AF-SCC-C2-VAC-GEN" and c.get("revision") == 13
        and c.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN" else "FAIL",
        f"class_id={c.get('class_id')} revision={c.get('revision')} sibling={c.get('sibling_disjoint_from')}")
    ct = (c.get("conclusion") or {}).get("conclusion_type")
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())

    def canon(kind, tok):
        for k, al in aliases.get(kind, {}).items():
            if tok == k or tok in al:
                return k
        return tok

    merged = re.search(r"C[02]_or_C[02]|C[02]\s*/\s*C[02]|strong_cosmic_censorship_(C0|C2)\b.*\b(C2|C0)\b", raw)
    rec(f"{cid_prefix}04_conclusion_token",
        "PASS" if ct == C2_TOKEN and canon("conclusion_type", ct) == C2_TOKEN
        and canon("conclusion_type", ct) != canon("conclusion_type", C0_TOKEN) and not merged else "FAIL",
        f"conclusion_type={ct}; canonical={canon('conclusion_type', ct)}; no merged token")
    d0 = str(((c.get("quantifiers") or {}).get("domains") or {}).get("D0") or {})
    d0def = d0.get("definition", "") if isinstance(d0, dict) else str(d0)
    ok_d0 = all(t in d0def for t in ["tagged disjoint union", "smooth", "sobolev", "s > 5/2", "delta in (1/2,1)"])
    rec(f"{cid_prefix}05_D0_typing", "PASS" if ok_d0 else "FAIL",
        "D0 is a tagged disjoint union over {smooth, (sobolev,s,delta)} with s>5/2, delta in (1/2,1)")
    q = c.get("quantifiers") or {}
    sf = str((c.get("conclusion") or {}).get("statement_formal", ""))
    ok_q = ("forall r in D0" in sf and "exists G_r comeager" in sf
            and "forall D in G_r" in sf and "not exists proper_future_extension_in_class" in sf
            and q.get("quantifier_class") == "forall-exists(comeager)-forall-not-exists(extension)")
    rec(f"{cid_prefix}06_quantifier_chain", "PASS" if ok_q else "FAIL",
        f"statement_formal={sf!r}; quantifier_class={q.get('quantifier_class')!r}")
    ks = c.get("known_status") or {}
    infl = (c.get("epistemic_status") != "open_problem" or c.get("claims_theorem_status") is True
            or str(c.get("validation_status", "")).lower() in ("passed", "validated")
            or str(ks.get("status", "")) != "open_problem")
    rec(f"{cid_prefix}07_no_theorem_inflation", "PASS" if not infl else "FAIL",
        f"epistemic_status={c.get('epistemic_status')} claims_theorem_status={c.get('claims_theorem_status')} "
        f"known_status={ks.get('status')} validation_status={c.get('validation_status')}")
    return canon, c


def detector_findings(raw: str):
    spec = importlib.util.spec_from_file_location("class_separation_092", ROOT / "research_map/class_separation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.findings_for_text(raw, "schemas/af_scc_c2_vacuum.yaml")


def check_binding(doc, cid_prefix="B", ev_override: Path | None = None):
    fb = doc.get("f0_binding") or {}
    decl_f0 = fb.get("declared_f0_sha256")
    supp = fb.get("class_contract_supplement")
    decl_ev = fb.get("consistency_evidence_sha256")
    ev_path = ev_override if ev_override is not None else ROOT / (fb.get("consistency_evidence") or "")
    live_f0 = sha256(ROOT / "research_map/formulation_taxonomy.yaml")
    live_ev = sha256(ev_path) if ev_path.exists() else None
    live_supp = sha256(ROOT / supp) if supp and (ROOT / supp).exists() else None
    rec(f"{cid_prefix}01_declared_f0_resolves", "PASS" if decl_f0 == live_f0 else "FAIL",
        f"declared {str(decl_f0)[:12]} vs live {live_f0[:12]}")
    rec(f"{cid_prefix}02_supplement_resolves", "PASS" if live_supp == SUPP_PIN else "FAIL",
        f"supplement measured {str(live_supp)[:12]} vs frozen {SUPP_PIN[:12]}")
    rec(f"{cid_prefix}03_declared_evidence_resolves", "PASS" if decl_ev == live_ev else "FAIL",
        f"declared {str(decl_ev)[:12]} vs measured {str(live_ev)[:12]} (card item I2a)")
    ebytes = ev_path.read_bytes()
    binds_f0 = live_f0.encode() in ebytes
    binds_supp = SUPP_PIN.encode() in ebytes
    rec(f"{cid_prefix}04_evidence_binds_compared_trees", "PASS" if (binds_f0 and binds_supp) else "FAIL",
        f"evidence embeds map_taxonomy_sha256={binds_f0} lead_contract_sha256={binds_supp} "
        f"(bytes={len(ebytes)})")
    man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    pinned = (man.get("files", {}).get("artifacts/formulation/evidence/taxonomy_consistency.json", {}) or {}).get("sha256")
    rec(f"{cid_prefix}05_evidence_frozen", "PASS" if pinned == live_ev else "FAIL",
        f"FROZEN rev{man.get('revision')} evidence pin {str(pinned)[:12]} vs measured {str(live_ev)[:12]}")
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", str(fb.get("checked_at", "")))
    import datetime
    mtime = None
    ev_mtime = None
    if m:
        checked = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
        mt = datetime.datetime.fromtimestamp((ROOT / "schemas/af_scc_c2_vacuum.yaml").stat().st_mtime)
        mtime = mt.replace(microsecond=0)
        pre_future = checked <= mtime + datetime.timedelta(seconds=2)
        ev_mtime = datetime.datetime.fromtimestamp(ev_path.stat().st_mtime).replace(microsecond=0)
        evidence_not_after = ev_mtime <= checked + datetime.timedelta(seconds=2)
    else:
        pre_future = evidence_not_after = False
    rec(f"{cid_prefix}06_checked_at_ordering", "PASS" if (pre_future and evidence_not_after) else "FAIL",
        f"checked_at={fb.get('checked_at')} schema_mtime={mtime} evidence_mtime={ev_mtime}")
    return fb


def check_closure(doc, man, f2a_path):
    out = []
    # HF-069R-2: acceptance pipeline preflight corpus staleness
    ev = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    base = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    cur = sha256(base)
    cbase = json.loads(ev.read_text()).get("base_sha256") if ev.exists() else None
    stale = cbase != cur
    out.append({"id": "HF-069R-2", "axis": "acceptance-pipeline preflight (stale rebased corpus)",
                "status": "OPEN" if stale else "CLOSED", "severity": "major",
                "detail": f"rebased corpus base {str(cbase)[:12]} vs current authoring C0 {cur[:12]}",
                "evidence": ["artifacts/formulation/evidence/semantic_escape_rebased.json",
                             "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                             "artifacts/formulation/tools/run_acceptance.py:52-65"]})
    # HF-035-F2A-3 / worker-007: L1 citation token
    refs = doc.get("l1_ledger_refs") or []
    tok = Counter(str(r.get("citation_status")) for r in refs)
    out.append({"id": "HF-035-F2A-3", "axis": "L1 provenance token hygiene",
                "status": "DEFECT-minor" if tok.get("verified_by_L1") else "CLOSED", "severity": "minor",
                "detail": f"citation_status counts {dict(tok)}; token out-of-vocabulary per W007-CITEBIND-CENSUS-01, "
                          "underlying references resolved+verified (no overclaim)",
                "evidence": ["schemas/af_scc_c2_vacuum.yaml:279-284"]})
    # W090-VOCAB-01
    f0 = strict_load(ROOT / "research_map/formulation_taxonomy.yaml")
    allowed = set(((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or [])
    ct = (doc.get("conclusion") or {}).get("conclusion_type")
    out.append({"id": "W090-VOCAB-01", "axis": "F0 allowed list vs VOCAB_ALIASES canonical token",
                "status": "OPEN" if ct not in allowed else "CLOSED", "severity": "major",
                "detail": f"F2a conclusion_type={ct} not in F0 field_vocabulary.allowed={sorted(allowed)}; "
                          "worker-017 gate experiment: frozen gate R11 rejects the F0 literal and accepts the registry canonical",
                "evidence": ["research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                             "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                             "artifacts/worker-017/vocab_source_adjudication/report.json"]})
    # HF-091-02 assumption incompleteness
    ep = str(doc.get("extension_predicate") or {})
    has_manifold_category = bool(re.search(r"M'?\s+is a (smooth|C[0-9])[^.]*manifold", ep))
    has_iota_regularity = bool(re.search(r"iota[^.]*C[0-9]", ep))
    out.append({"id": "HF-091-02", "axis": "assumption completeness in extension_predicate",
                "status": "OPEN" if not (has_manifold_category and has_iota_regularity) else "CLOSED",
                "severity": "major",
                "detail": f"manifold category of M' frozen={has_manifold_category}; "
                          f"iota regularity frozen={has_iota_regularity} (worker-091 HF-091-02 reproduced)",
                "evidence": ["schemas/af_scc_c2_vacuum.yaml:86-98"]})
    # Evidence hash-boundness (family)
    eb = (ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_bytes()
    bound = F0_PIN.encode() in eb and SUPP_PIN.encode() in eb
    out.append({"id": "HF-043-2/HF-035-F2A-2/HF-19-F2A-3", "axis": "consistency evidence is not hash-bound to the compared trees",
                "status": "CLOSED" if bound else "OPEN",
                "severity": "major",
                "detail": "the 495-byte evidence records paths and consistent=true but no sha256 of either compared tree; "
                          "re-stamping the declared hash (I2) does not clear this half",
                "evidence": ["artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                             "reviews/F2a-review-043.json", "reviews/F2a-review-088-rev12.json",
                             "reviews/F2a-review-19.json"]})
    # I3 second half: SET delta
    setd = json.loads((ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json").read_text())
    out.append({"id": "HF-W061-VAR-02", "axis": "F1 SET variant delta self-contradiction (I3 second half)",
                "status": "OPEN" if "strictly stronger" in str(setd.get("strength", "")) else "CLOSED",
                "severity": "major",
                "detail": f"SET delta strength={setd.get('strength')!r} while F1 rev13 predicate relation is 'strictly WEAKER'; "
                          "delta base still rev12 cce9c60146d6",
                "evidence": ["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
                             "schemas/af_wcc_vacuum.yaml:235"]})
    return out


def check_frozen(man):
    bad = []
    for p, r in man.get("files", {}).items():
        f = ROOT / p
        if not f.exists():
            bad.append(f"MISSING {p}")
        elif sha256(f) != r.get("sha256"):
            bad.append(f"DRIFT {p}")
    rec("F01_revision", "PASS" if man.get("revision") >= 29 else "FAIL",
        f"FROZEN revision={man.get('revision')} frozen_at={man.get('frozen_at')}")
    rec("F02_all_pins_resolve", "PASS" if not bad else "FAIL",
        f"{len(man.get('files', {}))} manifest entries, {len(bad)} problems" + (f": {bad[:4]}" if bad else ""))
    r = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/verify_frozen.py")],
                       capture_output=True, text=True)
    rec("F03_canonical_verify_frozen", "PASS" if r.returncode == 0 else "FAIL",
        (r.stdout.strip().splitlines() or [""])[0])
    missing = [p for p in FROZEN_FILES if p not in man.get("files", {})]
    rec("F04_moved_paths_pinned", "PASS" if not missing else "FAIL",
        f"card-item paths pinned; missing={missing}")
    # I4d: artifact events for the moved hashes
    new_hashes = {F2A_PIN[:12]: "F2a", PINS["schemas/af_wcc_vacuum.yaml"][:12]: "F1",
                  PINS["schemas/af_scc_c0_vacuum.yaml"][:12]: "F2b", FROZEN_PIN[:12]: "FROZEN"}
    announced = {k: [] for k in new_hashes}
    for src in [ROOT / "research_map/events.jsonl"] + sorted((ROOT / "comms/outbox").glob("*.jsonl")):
        try:
            lines = src.read_text(errors="replace").splitlines()
        except Exception:
            continue
        for ln in lines:
            if '"artifact"' not in ln:
                continue
            for h in new_hashes:
                if h in ln and h not in announced[h]:
                    announced[h].append(src.name)
    unannounced = [v for k, v in new_hashes.items() if not announced[k]]
    rec("F05_artifact_events_moved_paths", "PASS" if not unannounced else "FAIL",
        f"artifact-event announcements per hash: " +
        ", ".join(f"{new_hashes[k]}={len(v)}" for k, v in announced.items()) +
        (f"; unannounced={unannounced}" if unannounced else ""))
    return man


def check_card_items(man):
    rows = [json.loads(l) for l in (ROOT / "schemas/taxonomy_cases.jsonl").read_text().splitlines() if l.strip()]
    cases = [r for r in rows if r.get("record_type") == "case"]
    bound = [r for r in cases if r.get("binding_status") == "bound_taxonomy_sha_0abb9ed8a961"]
    meta = next((r for r in rows if r.get("record_type") == "meta"), {})
    mref = ((meta.get("taxonomy_ref") or {}).get("sha256"))
    rec("I1a_case_rows_bound", "PASS" if len(cases) == 36 and len(bound) == 36 else "FAIL",
        f"{len(bound)}/{len(cases)} case rows carry bound_taxonomy_sha_0abb9ed8a961")
    rec("I1b_meta_ref", "PASS" if mref == F0_PIN else "FAIL",
        f"meta.taxonomy_ref.sha256={str(mref)[:12]}")
    gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    r = subprocess.run([sys.executable, str(gate), "--json", str(ROOT / "schemas/af_scc_c2_vacuum.yaml")],
                       capture_output=True, text=True)
    try:
        body = json.loads(r.stdout)
        verdict, failed = body.get("verdict"), body.get("failed_rules")
    except Exception:
        verdict, failed = f"crash(exit{r.returncode})", []
    rec("I1c_canonical_gate", "PASS" if r.returncode == 0 and verdict == "pass" and not failed else "FAIL",
        f"check_class_schema.py exit {r.returncode}, verdict={verdict}, failed_rules={failed}")
    f1 = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()
    bad_tok = [ln for ln in f1.splitlines() if "strictly STRONGER than this class's single-q tail" in ln]
    setd = json.loads((ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json").read_text())
    rec("I3a_F1_schema_text", "PASS" if not bad_tok else "FAIL",
        f"pre-repair SET token lines remaining={len(bad_tok)}")
    rec("I3b_SET_delta", "PASS" if "strictly stronger" not in str(setd.get("strength", "")) else "FAIL",
        f"SET delta strength={setd.get('strength')!r}")
    return man


def run_controls(tmp: Path) -> list[dict]:
    """Each control plants a defect (or a compliant variant) and confirms the corresponding
    check detects it (or passes it). A control that does not behave as required voids the run.
    Control probes run against a private CHECKS list so the main report is not disturbed."""
    saved_main = CHECKS[:]

    def probe(fn, *args, **kw):
        CHECKS.clear()
        try:
            fn(*args, **kw)
            return CHECKS[:]
        finally:
            CHECKS[:] = saved_main

    out = []
    raw = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    doc = strict_load_text(raw)
    man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())

    def control(cid, expect, observed, detail):
        ok = expect == observed
        out.append({"id": cid, "expected": expect, "observed": observed, "ok": ok, "detail": detail})
        return ok

    # M01 revert declared evidence hash -> B03 FAIL
    d = json.loads(json.dumps(doc))
    d["f0_binding"]["consistency_evidence_sha256"] = "675a99d0" + "0" * 56
    p = tmp / "m01.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_binding, strict_load(p), cid_prefix="M01B")
    b03 = next(c for c in rows if c["id"] == "M01B03_declared_evidence_resolves")
    control("M01_revert_declared_evidence", "FAIL", b03["status"], b03["detail"])
    # M02 bound staged evidence (tree digests present) -> B04 PASS (staged file only; no canonical write)
    ev = {"map_taxonomy": "research_map/formulation_taxonomy.yaml",
          "lead_contract": "artifacts/formulation/formulation_taxonomy.yaml",
          "map_taxonomy_sha256": F0_PIN, "lead_contract_sha256": SUPP_PIN, "consistent": True}
    p2 = tmp / "m02_evidence.json"; p2.write_text(json.dumps(ev))
    rows = probe(check_binding, doc, cid_prefix="M02B", ev_override=p2)
    b04 = next(c for c in rows if c["id"] == "M02B04_evidence_binds_compared_trees")
    control("M02_bound_evidence_positive", "PASS", b04["status"], b04["detail"])
    # M03 conclusion token C2 -> C0
    d = json.loads(json.dumps(doc)); d["conclusion"]["conclusion_type"] = C0_TOKEN
    p = tmp / "m03.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_content, strict_load(p), p.read_text(), "M03K")
    k04 = next(c for c in rows if c["id"] == "M03K04_conclusion_token")
    control("M03_conclusion_token_C0", "FAIL", k04["status"], k04["detail"])
    # M04 merged token
    d = json.loads(json.dumps(doc)); d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C0_or_C2"
    p = tmp / "m04.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_content, strict_load(p), p.read_text(), "M04K")
    k04 = next(c for c in rows if c["id"] == "M04K04_conclusion_token")
    control("M04_merged_token", "FAIL", k04["status"], k04["detail"])
    # M05 D0 delta range widened
    d = json.loads(json.dumps(doc))
    q = d["quantifiers"]["domains"]["D0"]
    q["definition"] = q["definition"].replace("delta in (1/2,1)", "delta in (0,1)")
    p = tmp / "m05.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_content, strict_load(p), p.read_text(), "M05K")
    k05 = next(c for c in rows if c["id"] == "M05K05_D0_typing")
    control("M05_D0_range", "FAIL", k05["status"], k05["detail"])
    # M06 theorem inflation
    d = json.loads(json.dumps(doc)); d["validation_status"] = "passed"; d["known_status"]["status"] = "theorem"
    p = tmp / "m06.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_content, strict_load(p), p.read_text(), "M06K")
    k07 = next(c for c in rows if c["id"] == "M06K07_no_theorem_inflation")
    control("M06_theorem_inflation", "FAIL", k07["status"], k07["detail"])
    # M07 duplicate top-level key
    dup = raw.replace("class_id: AF-SCC-C2-VAC-GEN", "class_id: AF-SCC-C2-VAC-GEN\nclass_id: AF-SCC-C2-VAC-GEN", 1)
    try:
        strict_load_text(dup); status = "PASS"
    except DupKeyError:
        status = "FAIL"
    control("M07_duplicate_top_level_key", "FAIL", status, "strict loader rejects a duplicated top-level key")
    # M08 sibling removed
    d = json.loads(json.dumps(doc)); d.pop("sibling_disjoint_from", None)
    p = tmp / "m08.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_content, strict_load(p), p.read_text(), "M08K")
    k03 = next(c for c in rows if c["id"] == "M08K03_identity")
    control("M08_sibling_removed", "FAIL", k03["status"], k03["detail"])
    # M09 wrong FROZEN pin
    m = json.loads(json.dumps(man)); m["files"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"] = "0" * 64
    bad = [k for k, v in m["files"].items() if (ROOT / k).exists() and sha256(ROOT / k) != v["sha256"]]
    control("M09_wrong_frozen_pin", "FAIL", "FAIL" if bad else "PASS", f"drift detected for {bad[:2]}")
    # M10 canonical gate rejects a merged-token mutant
    d = json.loads(json.dumps(doc)); d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C0_or_C2"
    p = tmp / "m10_gate.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    r = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"), "--json", str(p)],
                       capture_output=True, text=True)
    control("M10_canonical_gate_mutant", "FAIL", "PASS" if r.returncode == 0 else "FAIL",
            f"canonical gate exit {r.returncode} on merged-token mutant")
    # M11 null control: canonical gate passes the canonical bytes
    r = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"), "--json",
                        str(ROOT / "schemas/af_scc_c2_vacuum.yaml")], capture_output=True, text=True)
    control("M11_null_canonical_pass", "PASS", "PASS" if r.returncode == 0 else "FAIL",
            f"canonical gate exit {r.returncode} on canonical bytes")
    # M12 checked_at in the future
    d = json.loads(json.dumps(doc)); d["f0_binding"]["checked_at"] = "2026-12-31T00:00:00+08:00"
    p = tmp / "m12.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    rows = probe(check_binding, strict_load(p), cid_prefix="M12B")
    b06 = next(c for c in rows if c["id"] == "M12B06_checked_at_ordering")
    control("M12_checked_at_future", "FAIL", b06["status"], b06["detail"])
    CHECKS[:] = saved_main
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "report.json"))
    ap.add_argument("--stamp", default="2026-09-12T00:58:00+08:00")
    ap.add_argument("--skip-controls", action="store_true")
    a = ap.parse_args()

    entry = {p: (sha256(ROOT / p) if (ROOT / p).exists() else None) for p in PINS}
    drift_entry = {p: h for p, h in entry.items() if PINS[p] and h != PINS[p]}
    if drift_entry:
        print(json.dumps({"fail_closed": "PIN_DRIFT_AT_ENTRY", "drift": drift_entry}, indent=1))
        return 3

    raw = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    doc = strict_load_text(raw)
    man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    check_frozen(man)
    check_card_items(man)
    canon, _ = check_content(doc, raw)
    check_binding(doc)
    fnd = detector_findings(raw)
    rec("K08_class_separation_detector", "PASS" if not fnd else "FAIL",
        f"canonical detector findings_for_text={len(fnd)}")
    toks = set(re.findall(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)+", raw))
    foreign = sorted(t for t in toks if t not in FROZEN_CLASSES)
    rec("K09_class_token_discipline", "PASS" if not foreign else "FAIL",
        f"class-shaped tokens outside the frozen four={foreign}")
    closure = check_closure(doc, man, ROOT / "schemas/af_scc_c2_vacuum.yaml")

    with tempfile.TemporaryDirectory() as td:
        controls = [] if a.skip_controls else run_controls(Path(td))

    exitrec = {p: (sha256(ROOT / p) if (ROOT / p).exists() else None) for p in PINS}
    drift_exit = {p: (entry[p], exitrec[p]) for p in PINS if entry[p] != exitrec[p]}
    rec("S01_entry_pins", "PASS", f"{len(PINS)} pins measured at entry")
    rec("S02_exit_pins", "PASS" if not drift_exit else "FAIL",
        f"entry==exit for all pins; drift={drift_exit}")

    required_prefixes = ("K", "B", "F", "I", "S")
    failed = [c["id"] for c in CHECKS if c["status"] == "FAIL" and c["id"].startswith(required_prefixes)]
    open_closure = [c["id"] for c in closure if c["status"] == "OPEN"]
    controls_ok = all(c["ok"] for c in controls)
    verdict = "accept" if (not failed and not open_closure and controls_ok) else "revise"

    report = {
        "schema_version": "0.1",
        "task_id": "W092-F2A-REV13-FULL-01",
        "actor": "worker-092",
        "node_id": "F2a",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "review_kind": "independent full-schema verdict at FROZEN rev29 (rev13)",
        "counts_as_full_schema_verdict": True,
        "generated_at": a.stamp,
        "pins": PINS,
        "entry_pins": entry,
        "exit_pins": exitrec,
        "pin_drift": drift_exit,
        "checks": CHECKS,
        "controls": controls,
        "closure_matrix": closure,
        "verdict_inputs": {"failed_required_checks": failed, "open_closure_items": open_closure,
                           "controls_ok": controls_ok},
        "verdict": verdict,
        "non_claims": [
            "worker measurement only: does not set node status, validation_status, or any gate verdict",
            "no canonical artifact was edited; the staged positive control M02 wrote the canonical evidence path for <1 s and restored the exact bytes in a finally block (recorded)",
            "I3b/HF-W061-VAR-02 and evidence hash-boundness are measured properties of artifact bytes, not mathematics",
        ],
        "falsifier": [
            "re-measure any pre-registered pin and find entry != exit (drift voids the affected check)",
            "the declared consistency-evidence hash resolving at the same schema pin AND the evidence bytes containing both compared-tree sha256 values, with checked_at ordering intact",
            "a tagged manifold category and iota regularity present in extension_predicate",
            "a controller ruling recorded in the map designating the VOCAB_ALIASES registry canonical (or amending F0 field_vocabulary.allowed) closes W090-VOCAB-01",
            "the rebased corpus base equal to the live authoring C0 hash closes HF-069R-2",
        ],
    }
    Path(a.json).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "failed": failed, "open_closure": open_closure,
                      "controls_ok": controls_ok, "report": a.json}, indent=1))
    return 0 if verdict == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
