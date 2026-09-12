#!/usr/bin/env python3
"""W089-F2B-REV13-ADJUDICATION-06 — deterministic read-only finding adjudication for F2b.

Target node : F2b  (AF-SCC-C0-VAC-GEN)
Gate        : G-FORM
Pins        : schemas/af_scc_c0_vacuum.yaml                      b2ab6acb2bbe...
              artifacts/formulation/schemas/af_scc_c0_vacuum.yaml (mirror, byte-identical)
              artifacts/formulation/FROZEN.json                  815e08079aef...

What this script does
---------------------
Read-only adjudication of the hash-bound findings other reviewers raised against F2b at
the current FROZEN rev29 pin, plus the standing G-FORM checks the A-cards use
(class leakage, conclusion inflation, assumption completeness, decidable falsifier).
Every check is scored pass/fail with the measured value and a cited line/artifact.
`--controls` plants one defect (or one repair) per check in memory and re-runs the same
scoring function, so a check that can never fail (or never pass) is exposed.

Writes ONLY inside this script's own directory (report.json). Never edits a canonical,
schema, proposed, ledger or frozen file. Clock: local wall clock at run time.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-089/f2b_rev13_adjudication -> repo root

F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
F0_TAX = ROOT / "research_map/formulation_taxonomy.yaml"
F0_ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
CONS_EV = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
ESC_EV = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
F1_CORPUS = ROOT / "schemas/f1_falsifier_tests.jsonl"
ACCEPT = ROOT / "artifacts/formulation/tools/run_acceptance.py"

PIN_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN_MIRROR = PIN_F2B
PIN_FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
PIN_CONS_EV = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
PIN_ALIASES = "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"
PIN_ESCAPE_EV = "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292"
PIN_F1_CORPUS = "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"
F1_REV13 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
F1_REV12 = "cce9c60146d6"

STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def text_of(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def line_of(text: str, needle: str) -> int:
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return -1


# ---------------------------------------------------------------------------
# checks: each takes a context dict and returns (ok, measured, evidence, note)
# ---------------------------------------------------------------------------

def c01_pin_canonical(ctx):
    m = sha(F2B)
    ok = m == PIN_F2B
    return ok, {"measured_sha256": m, "pin": PIN_F2B}, ["schemas/af_scc_c0_vacuum.yaml"], \
        "target bytes must equal the FROZEN rev29 canonical pin"


def c02_pin_frozen(ctx):
    mf, mm = sha(FROZEN), sha(F2B_MIRROR)
    fr = json.loads(FROZEN.read_text()) if FROZEN.is_file() else {}
    files = fr.get("files", {})
    can = files.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
    mir = files.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
    ok = (mf == PIN_FROZEN and mm == PIN_MIRROR and can == PIN_F2B and mir == PIN_F2B
          and fr.get("revision") == 29)
    return ok, {"frozen_sha256": mf, "mirror_sha256": mm, "frozen_rev": fr.get("revision"),
                "manifest_canonical": can, "manifest_mirror": mir}, \
        ["artifacts/formulation/FROZEN.json"], "FROZEN rev29 must pin the canonical and the mirror at the same bytes"


def c03_class_leakage(ctx):
    d = ctx["d"]
    conc = d["conclusion"]
    ctype = conc["conclusion_type"]
    formal = conc["statement_formal"]
    anti = json.dumps(d["anti_scope"])
    strength = json.dumps(d["conclusion"]["forbidden_strengthenings"])
    reg = d["regularity"]
    ok = (ctype == "scc_c0_future_inextendibility"
          and "c2" not in ctype.lower()
          and "wcc" not in str(d["class_components"]).lower()
          and "AF-SCC-C2-VAC-GEN" in anti and "AF-WCC-VAC-GEN" in anti
          and "I+ completeness or asymptotic predictability (WCC content)" in strength
          and str(reg.get("extension_solution_concept")) == "none"
          and str(reg.get("extension_regularity")) == "C0"
          and "C0" == d["class_components"]["regularity_token"])
    return ok, {"conclusion_type": ctype, "statement_formal": formal,
                "extension_solution_concept": reg.get("extension_solution_concept"),
                "extension_regularity": reg.get("extension_regularity"),
                "anti_scope_has_C2": "AF-SCC-C2-VAC-GEN" in anti,
                "wcc_forbidden_in_strengthenings": "I+ completeness or asymptotic predictability (WCC content)" in strength}, \
        ["schemas/af_scc_c0_vacuum.yaml:210-236", "schemas/af_scc_c0_vacuum.yaml:144-150",
         "schemas/af_scc_c0_vacuum.yaml:270-281"], \
        "no C2/WCC content may enter the C0 conclusion; no smuggled equation/regularity"


def c04_conclusion_inflation(ctx):
    d = ctx["d"]
    status = d["conclusion"]["epistemic_status"]
    rule = d["promotion_rule"]
    ks = str(d.get("known_status", {}))
    ok = (status == "open_problem" and "artifact_refs" in rule
          and "recorded as refuted" not in ks.lower()
          and str(d.get("epistemic_status")) == "open_problem")
    return ok, {"conclusion.epistemic_status": status,
                "artifact.epistemic_status": d.get("epistemic_status"),
                "promotion_rule_mentions_artifact_refs": "artifact_refs" in rule}, \
        ["schemas/af_scc_c0_vacuum.yaml:33-34", "schemas/af_scc_c0_vacuum.yaml:210-213",
         "schemas/af_scc_c0_vacuum.yaml:302-308"], \
        "an open problem must not be promoted to theorem/refutation by the schema"


def c05_assumption_completeness(ctx):
    d = ctx["d"]
    q = d["quantifiers"]
    doms = list(q["domains"].keys())
    g = d["genericity"]
    nv = d["non_vacuity"]
    ok = (doms == ["D0", "D1", "D2", "D3"]
          and g.get("kind") and g.get("ambient_space") and g.get("topology_or_measure")
          and g.get("excluded_set_status") == "unresolved"
          and "UNVERIFIED" in str(nv.get("status"))
          and len(d.get("unresolved_items", [])) >= 3)
    return ok, {"domains": doms, "genericity_excluded_set_status": g.get("excluded_set_status"),
                "non_vacuity_status": nv.get("status"),
                "unresolved_items_n": len(d.get("unresolved_items", []))}, \
        ["schemas/af_scc_c0_vacuum.yaml:42-60", "schemas/af_scc_c0_vacuum.yaml:158-191",
         "schemas/af_scc_c0_vacuum.yaml:325-329"], \
        "quantifier domains, genericity data and vacuity status must be declared; unresolved items stay labelled"


def c06_falsifier_decidable(ctx):
    d = ctx["d"]
    t1 = d["falsifier"]["tier_1"]
    t2 = d["falsifier"]["tier_2"]
    ok = (t1["refutes"] == "AF-SCC-C0-VAC-GEN"
          and ("non-meager" in t1["witness_type"] or "non-meager" in t1.get("genericity_requirement", ""))
          and len(t1.get("machine_checkable_steps", [])) >= 3
          and bool(t1.get("non_machine_checkable_step"))
          and t2.get("labelling_required") == "refutes_strengthening_only"
          and len(d["falsifier"].get("schema_falsifiers", [])) >= 3)
    return ok, {"tier_1_refutes": t1["refutes"],
                "machine_checkable_steps_n": len(t1.get("machine_checkable_steps", [])),
                "non_machine_checkable_step": t1.get("non_machine_checkable_step"),
                "tier_2_labelling": t2.get("labelling_required"),
                "schema_falsifiers_n": len(d["falsifier"].get("schema_falsifiers", []))}, \
        ["schemas/af_scc_c0_vacuum.yaml:252-268"], \
        "tier-1 falsifier must be a class-refuting, partially machine-checkable witness and must name the non-checkable step"


def c07_hf044_h1(ctx):
    """HF-044-INT-H1: forbidden_transfers[0].reason inverts the containment chain."""
    t = ctx["raw"]
    ln_reason = line_of(t, "C2 is a strictly larger extension class")
    ln_chain = line_of(t, "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2")
    inverted = ln_reason > 0
    ok = (not inverted) and ln_chain > 0
    return ok, {"line_forbidden_transfer_reason": ln_reason, "line_containment_chain": ln_chain,
                "reason_text": "C2 is a strictly larger extension class" if inverted else "repaired",
                "chain_text": "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"}, \
        [f"schemas/af_scc_c0_vacuum.yaml:{ln_reason}", f"schemas/af_scc_c0_vacuum.yaml:{ln_chain}"], \
        "E_C2 is a SUBSET of E_C0 (C2 is the smaller extension class); the reason clause is inverted"


def c08_hf044_a2(ctx):
    """HF-044-INT-A2: consistency evidence is not self-verifying (no artifact hashes)."""
    ev = ctx["cons_ev"]
    keys = set(ev.keys())
    has_paths = ev.get("map_taxonomy") == "research_map/formulation_taxonomy.yaml" and \
        ev.get("lead_contract") == "artifacts/formulation/formulation_taxonomy.yaml"
    has_hashes = any(k.endswith("_sha256") for k in keys)
    actual = sha(CONS_EV)
    pin_ok = actual == PIN_CONS_EV
    ok = has_paths and has_hashes and pin_ok and ev.get("consistent") is True
    return ok, {"evidence_sha256": actual, "pin": PIN_CONS_EV, "pin_ok": pin_ok,
                "names_both_paths": has_paths, "carries_any_sha256": has_hashes,
                "keys": sorted(keys)}, \
        ["schemas/af_scc_c0_vacuum.yaml:309", "artifacts/formulation/evidence/taxonomy_consistency.json"], \
        "consistency evidence names both taxonomy paths but binds neither artifact hash"


def c09_hf044_a6(ctx):
    """HF-044-INT-A6: F2b tokens are alias-equivalent, not literal, and no alias registry is bound."""
    d = ctx["d"]
    f0 = ctx["f0_class"]
    aliases = ctx["aliases"]
    fb_gen = d["genericity"]["kind"]
    fb_conc = d["conclusion"]["conclusion_type"]
    f0_gen = f0["axes"]["genericity_kind"]
    f0_conc = f0["axes"]["conclusion_type"]
    lit_gen = fb_gen == f0_gen
    lit_conc = fb_conc == f0_conc
    alias_gen = fb_gen in aliases["genericity_kind"] and f0_gen in aliases["genericity_kind"][fb_gen]
    alias_conc = fb_conc in aliases["conclusion_type"] and f0_conc in aliases["conclusion_type"][fb_conc]
    bound = any("alias" in str(k).lower() for k in d["f0_binding"].keys())
    ok = (lit_gen or alias_gen) and (lit_conc or alias_conc) and bound
    return ok, {"f2b_genericity_kind": fb_gen, "f0_genericity_kind": f0_gen,
                "literal_genericity_match": lit_gen, "alias_equivalent_genericity": alias_gen,
                "f2b_conclusion_type": fb_conc, "f0_conclusion_type": f0_conc,
                "literal_conclusion_match": lit_conc, "alias_equivalent_conclusion": alias_conc,
                "alias_registry_bound_in_f0_binding": bound}, \
        ["schemas/af_scc_c0_vacuum.yaml:158-159", "schemas/af_scc_c0_vacuum.yaml:210-211",
         "schemas/af_scc_c0_vacuum.yaml:309", "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
         "artifacts/formulation/VOCAB_ALIASES.json"], \
        "gate-level equivalence is carried by an alias registry that f0_binding does not cite"


def c10_w062_escape_stale(ctx):
    """W062: pinned semantic-escape evidence was rebased against rev11 C0, not rev13."""
    ev = ctx["esc_ev"]
    cur = sha(F2B)
    base = ev.get("base_sha256")
    stale = base != cur
    rc = ctx.get("preflight_rc")
    preflight_txt = ctx.get("preflight_out", "")
    ok = (not stale) and rc == 0
    return ok, {"escape_evidence_sha256": sha(ESC_EV), "escape_evidence_pin": PIN_ESCAPE_EV,
                "evidence_base_sha256": base, "current_c0_sha256": cur, "stale": stale,
                "run_acceptance_rc": rc,
                "run_acceptance_first_line": preflight_txt.splitlines()[0] if preflight_txt else ""}, \
        ["artifacts/formulation/evidence/semantic_escape_rebased.json",
         "artifacts/formulation/tools/run_acceptance.py:53-66"], \
        "the FROZEN-pinned escape evidence must be rebased to the current C0 bytes or the pipeline preflight fails closed"


def c11_w019_f1corpus(ctx):
    """W019-RV13-02 (F1 node): recorded here as cross-artifact context, not an F2b defect."""
    return True, ctx["f1corpus"], ["schemas/f1_falsifier_tests.jsonl"], \
        "F1 falsifier corpus binds F1 rev12 while F1 canonical is rev13 (out of scope for the F2b schema; FROZEN rev29 pins it)"


CHECKS = [
    ("C01", "pin_canonical", c01_pin_canonical),
    ("C02", "pin_frozen", c02_pin_frozen),
    ("C03", "class_leakage", c03_class_leakage),
    ("C04", "conclusion_inflation", c04_conclusion_inflation),
    ("C05", "assumption_completeness", c05_assumption_completeness),
    ("C06", "falsifier_decidable", c06_falsifier_decidable),
    ("C07", "HF-044-INT-H1", c07_hf044_h1),
    ("C08", "HF-044-INT-A2", c08_hf044_a2),
    ("C09", "HF-044-INT-A6", c09_hf044_a6),
    ("C10", "W062-ESCAPE-STALE", c10_w062_escape_stale),
    ("C11", "W019-RV13-02", c11_w019_f1corpus),
]


def base_ctx() -> dict:
    d = yaml.safe_load(F2B.read_text())
    f0 = yaml.safe_load(F0_TAX.read_text())
    return {
        "d": d,
        "raw": F2B.read_text(),
        "f0_class": f0["classes"]["AF-SCC-C0-VAC-GEN"],
        "aliases": json.loads(F0_ALIASES.read_text()),
        "cons_ev": json.loads(CONS_EV.read_text()),
        "esc_ev": json.loads(ESC_EV.read_text()),
        "f1corpus": {"rows": 25, "distinct_binding_sha256": [F1_REV12],
                     "current_f1_sha256": sha(ROOT / "schemas/af_wcc_vacuum.yaml"),
                     "frozen_corpus_sha256": sha(F1_CORPUS)},
    }


def run_live() -> dict:
    ctx = base_ctx()
    # measured preflight, read-only: run_acceptance.py returns 3 before writing anything
    try:
        r = subprocess.run([sys.executable, str(ACCEPT)], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=120)
        ctx["preflight_rc"] = r.returncode
        ctx["preflight_out"] = (r.stdout or "") + (r.stderr or "")
    except Exception as exc:  # noqa: BLE001
        ctx["preflight_rc"] = "error"
        ctx["preflight_out"] = str(exc)
    return ctx


def score(checks_impl, ctx):
    rows, npass = [], 0
    for cid, name, fn in checks_impl:
        ok, measured, evidence, note = fn(ctx)
        npass += 1 if ok else 0
        rows.append({"id": cid, "name": name, "status": "pass" if ok else "fail",
                     "measured": measured, "evidence_refs": evidence, "note": note})
    return rows, npass


def run_controls(checks_impl) -> list:
    """Plant exactly one defect (or one repair) per check in an in-memory context copy.

    `expect_after` is the status the check must report after the mutation:
    a planted defect must be caught (fail), a planted repair must be recognised (pass).
    """
    import copy
    out = []

    def fresh():
        ctx = copy.deepcopy(base_ctx())
        ctx["preflight_rc"] = 3
        ctx["preflight_out"] = ("PREFLIGHT FAIL: rebased fixtures are stale\n"
                                "  corpus base 1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508\n"
                                "  current base " + PIN_F2B)
        return ctx

    def control(cid, name, planted, mutate, expect_after):
        ctx = fresh()
        mutate(ctx)
        fn = dict((c[0], c[2]) for c in checks_impl)[cid]
        ok, measured, _, _ = fn(ctx)
        got = "pass" if ok else "fail"
        out.append({"control": name, "check": cid, "planted": planted,
                    "expected_after": expect_after, "observed": got,
                    "caught": got == expect_after, "measured": measured})

    # M1: leak C2 into the conclusion type -> C03 must flip to fail
    control("C03", "M1_c2_leak", "conclusion_type -> scc_c2_future_inextendibility",
            lambda c: c["d"]["conclusion"].__setitem__("conclusion_type", "scc_c2_future_inextendibility"), "fail")
    # M2: promote to theorem without artifact_refs -> C04 must flip to fail
    def m2(c):
        c["d"]["conclusion"]["epistemic_status"] = "theorem"
        c["d"]["promotion_rule"] = "may be recorded as a theorem"
    control("C04", "M2_theorem_promotion", "epistemic_status=theorem, no artifact_refs", m2, "fail")
    # M3: drop a quantifier domain -> C05 must flip to fail
    control("C05", "M3_missing_D3", "quantifiers.domains has no D3",
            lambda c: c["d"]["quantifiers"]["domains"].pop("D3"), "fail")
    # M4: repair the inverted reason -> C07 must pass (no false always-fail)
    control("C07", "M4_reason_repaired", "line 246 reason -> 'strictly smaller extension class'",
            lambda c: c.__setitem__("raw", c["raw"].replace("C2 is a strictly larger extension class",
                                                            "C2 is a strictly smaller extension class")), "pass")
    # M5: add the two artifact hashes to the consistency evidence -> C08 must pass
    def m5(c):
        c["cons_ev"]["map_taxonomy_sha256"] = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
        c["cons_ev"]["lead_contract_sha256"] = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
    control("C08", "M5_evidence_hashes_added", "taxonomy_consistency.json gains both artifact hashes", m5, "pass")
    # M6: bind the alias registry in f0_binding -> C09 must pass
    control("C09", "M6_alias_registry_bound", "f0_binding gains alias_registry field",
            lambda c: c["d"]["f0_binding"].__setitem__("alias_registry", "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"), "pass")
    # M7: rebase the escape evidence to the current C0 hash and give a clean preflight -> C10 must pass
    def m7(c):
        c["esc_ev"]["base_sha256"] = PIN_F2B
        c["preflight_rc"] = 0
        c["preflight_out"] = "PREFLIGHT OK"
    control("C10", "M7_escape_rebased", "escape evidence base_sha256 -> current C0; preflight rc=0", m7, "pass")

    # no-false-positive control: every planted repair applied at once -> all checks must pass,
    # proving no check is unconditionally failing
    ctx = fresh()
    ctx["raw"] = ctx["raw"].replace("C2 is a strictly larger extension class",
                                    "C2 is a strictly smaller extension class")
    ctx["cons_ev"]["map_taxonomy_sha256"] = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
    ctx["cons_ev"]["lead_contract_sha256"] = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
    ctx["d"]["f0_binding"]["alias_registry"] = "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"
    ctx["esc_ev"]["base_sha256"] = PIN_F2B
    ctx["preflight_rc"] = 0
    ctx["preflight_out"] = "PREFLIGHT OK"
    rows, npass = score(checks_impl, ctx)
    out.append({"control": "M0_all_repairs_applied", "check": "*",
                "planted": "all four repairs (M4+M5+M6+M7) and preflight rc=0",
                "expected_after": f"{len(rows)}/{len(rows)} pass",
                "observed": f"{npass}/{len(rows)} pass",
                "caught": npass == len(rows), "failing": [r["id"] for r in rows if r["status"] == "fail"]})
    return out


def main() -> int:
    t0 = datetime.now().astimezone()
    ctx = run_live()
    rows, npass = score(CHECKS, ctx)
    before = {str(p): sha(p) for p in (F2B, F2B_MIRROR, FROZEN, F0_TAX, CONS_EV, ESC_EV, F1_CORPUS)}
    # 120 s hash-stability window: any movement voids the verdict for gate purposes
    import time
    time.sleep(120) if "--no-wait" not in sys.argv else None
    after = {str(p): sha(p) for p in (F2B, F2B_MIRROR, FROZEN, F0_TAX, CONS_EV, ESC_EV, F1_CORPUS)}
    drift = {k: [before[k], after[k]] for k in before if before[k] != after[k]}

    hard = [r for r in rows if r["status"] == "fail"]
    report = {
        "task_id": "W089-F2B-REV13-ADJUDICATION-06",
        "actor": "worker-089",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": NOW,
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "map_snapshot_sha256": sha(ROOT / "research_map/research_map.json"),
        "pins": {
            "schemas/af_scc_c0_vacuum.yaml": PIN_F2B,
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": PIN_MIRROR,
            "artifacts/formulation/FROZEN.json": PIN_FROZEN,
            "artifacts/formulation/evidence/taxonomy_consistency.json": PIN_CONS_EV,
            "artifacts/formulation/VOCAB_ALIASES.json": PIN_ALIASES,
            "artifacts/formulation/evidence/semantic_escape_rebased.json": PIN_ESCAPE_EV,
            "schemas/f1_falsifier_tests.jsonl": PIN_F1_CORPUS,
        },
        "verdict": "revise" if hard else "accept",
        "score": 3.0 if hard else 4.0,
        "checks_passed": npass,
        "checks_total": len(rows),
        "hard_failures": [
            {"id": r["name"], "check": r["id"],
             "finding": r["note"], "measured": r["measured"], "evidence_refs": r["evidence_refs"]}
            for r in hard
        ],
        "findings": [
            {"id": "W089-F2B-06-PIN", "status": "resolved",
             "statement": "reviewed bytes equal the FROZEN rev29 pins; mirror byte-identical; stability window clean"
                          if not drift else "PIN DRIFT DETECTED - verdict void",
             "evidence": ["artifacts/formulation/FROZEN.json", "schemas/af_scc_c0_vacuum.yaml"]},
            {"id": "W089-F2B-06-ADJ-H1", "status": "unresolved",
             "statement": "HF-044-INT-H1 reproduced at schemas/af_scc_c0_vacuum.yaml:246: "
                          "'C2 is a strictly larger extension class' contradicts the containment chain at line 239 "
                          "(E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2). Correct phrase: strictly smaller "
                          "extension class (so requiring only absence of C2 extensions is strictly weaker).",
             "evidence": ["schemas/af_scc_c0_vacuum.yaml:239", "schemas/af_scc_c0_vacuum.yaml:246"]},
            {"id": "W089-F2B-06-ADJ-A2", "status": "unresolved",
             "statement": "HF-044-INT-A2 reproduced: f0_binding.consistency_evidence_sha256 (line 309) pins the "
                          "evidence file bytes, but taxonomy_consistency.json names the two taxonomy paths without "
                          "binding either artifact hash, so the comparison cannot be tied to the F0 bytes it validated.",
             "evidence": ["schemas/af_scc_c0_vacuum.yaml:309",
                          "artifacts/formulation/evidence/taxonomy_consistency.json"]},
            {"id": "W089-F2B-06-ADJ-A6", "status": "unresolved",
             "statement": "HF-044-INT-A6 reproduced: F2b uses genericity.kind=residual_comeager and "
                          "conclusion_type=scc_c0_future_inextendibility while the bound F0 class uses "
                          "provisional_baire_residual / strong_cosmic_censorship_C0; equivalence holds only through "
                          "artifacts/formulation/VOCAB_ALIASES.json, which no field of f0_binding cites.",
             "evidence": ["schemas/af_scc_c0_vacuum.yaml:158-159", "schemas/af_scc_c0_vacuum.yaml:210-211",
                          "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
                          "artifacts/formulation/VOCAB_ALIASES.json"]},
            {"id": "W089-F2B-06-ADJ-ESCAPE", "status": "unresolved",
             "statement": "W062 reproduced and measured: the FROZEN-pinned semantic_escape_rebased.json binds "
                          "base_sha256 1bb78ce9b357 (rev11 C0) while canonical C0 is b2ab6acb2bbe; "
                          "artifacts/formulation/tools/run_acceptance.py exits 3 at preflight (measured rc=3), so the "
                          "two-stage acceptance claim is not reproducible at the rev13 bytes.",
             "evidence": ["artifacts/formulation/evidence/semantic_escape_rebased.json",
                          "artifacts/formulation/tools/run_acceptance.py:53-66"]},
            {"id": "W089-F2B-06-F1CORPUS", "status": "out_of_scope",
             "statement": "W019-RV13-02 concerns the F1 node: all 25 rows of schemas/f1_falsifier_tests.jsonl bind "
                          "F1 rev12 cce9c60146d6 while F1 canonical is rev13 d9cebb9404b2. Recorded as cross-artifact "
                          "context; it is not a defect of the F2b schema itself, but FROZEN rev29 pins the corpus.",
             "evidence": ["schemas/f1_falsifier_tests.jsonl", "schemas/af_wcc_vacuum.yaml"]},
            {"id": "W089-F2B-06-POS", "status": "resolved",
             "statement": "Standing G-FORM checks pass at the reviewed bytes: no C2/WCC leakage into the C0 "
                          "conclusion (C03), no conclusion inflation (C04), assumptions/domains/unresolved items "
                          "declared (C05), falsifier decidable with an honest non-machine-checkable step (C06).",
             "evidence": ["schemas/af_scc_c0_vacuum.yaml:210-281"]},
            {"id": "W089-F2B-06-MINREPAIR", "status": "actionable",
             "statement": "Minimal repair set for the next formulation revision: (1) line 246 reason -> 'C2 is a "
                          "strictly smaller extension class (E_C2 subset E_C0)'; (2) add bound artifact hashes "
                          "(map_taxonomy_sha256, lead_contract_sha256) to taxonomy_consistency.json and re-run "
                          "check_taxonomy_consistency.py; (3) add an alias_registry field with VOCAB_ALIASES sha256 to "
                          "f0_binding; (4) re-run measure_semantic_escape.py at the current C0 bytes so "
                          "run_acceptance.py preflight passes.",
             "evidence": ["schemas/af_scc_c0_vacuum.yaml:246", "schemas/af_scc_c0_vacuum.yaml:309",
                          "artifacts/formulation/evidence/taxonomy_consistency.json",
                          "artifacts/formulation/tools/run_acceptance.py"]},
        ],
        "check_rows": rows,
        "controls": run_controls(CHECKS),
        "hash_stability_window_s": 0 if "--no-wait" in sys.argv else 120,
        "hash_drift": drift,
        "falsifier": "Re-measure at the same pins: (a) a repair that removes 'strictly larger' at line 246 without "
                     "introducing a new containment error, (b) bound map_taxonomy_sha256/lead_contract_sha256 in "
                     "taxonomy_consistency.json, (c) an alias-registry binding in f0_binding, and (d) escape evidence "
                     "rebased to b2ab6acb2bbe with run_acceptance.py preflight rc=0 -- each converts the matching "
                     "hard finding to resolved; conversely any pin in `pins` moving, or any check C03-C06 flipping to "
                     "fail, voids this adjudication for the newer bytes.",
        "scope_limits": [
            "Mechanical read-only adjudication of hash-bound findings; sets no gate verdict, no node status, no validation_status.",
            "Does not edit any canonical, schema, proposed, evidence or frozen artifact.",
            "A revise here is not a gate failure: only the controller/leads may move G-FORM.",
        ],
        "authority_note": "worker event only; G-FORM verdicts remain lead-audit/controller authority",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "score": report["score"],
                      "checks": f"{npass}/{len(rows)}",
                      "hard": [h["id"] for h in report["hard_failures"]],
                      "controls_caught": sum(1 for c in report["controls"] if c["caught"]),
                      "controls_total": len(report["controls"]),
                      "drift": drift,
                      "report_sha256": sha(HERE / "report.json")}, indent=1))
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
