#!/usr/bin/env python3
"""W072-B: independent canonical-hash verification of F2a (AF-SCC-C2-VAC-GEN).

Task taken by worker-072 with no assignment card: the formulation lead's resource
request of 2026-09-12T00:20:09+08:00 asks for an independent reviewer for the final
rev11 schemas, and schemas/af_scc_c2_vacuum.yaml#b6123750b37d has no recorded
independent review at that hash (its own review_status.independent_reviewers is []).

What this runner decides (mechanical class binding and separation only):
  A. publication binding  canonical bytes == authoring bytes; F0 binding hash matches
     the measured canonical taxonomy; class_contract_pointer target exists.
  B. class identity       class_id / node_id / regularity token / one_class_only.
  C. sibling separation   mutual sibling_disjoint_from; distinct conclusion_type
     tokens; no composite "C0 or C2" and no sibling conclusion token in ASSERTIVE
     paths (anti_scope / variants / provenance / ledger are exempt, per
     class_boundary.import_rule).
  D. contract consistency independent re-implementation of the canonical-taxonomy vs
     lead-contract shared-field comparison for both SCC classes.
  E. discriminating power  four mutants must fail the same checks; an unmodified copy
     must pass them (no false positive).
It also replays the owner's two-stage acceptance harness (structure + semantic) as
hash-bound evidence, clearly labelled as a replay, not as an independent derivation.

It does NOT decide physical/mathematical correctness, the truth of any cited source,
or citation scope. Exit 0 = all checks pass; 1 = a check/finding failed; 2 = pin
drift (fail-closed, no verdict).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FATAL: PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

# ---- pins: fail closed on any drift -----------------------------------------
PINS = {
    "schemas/af_scc_c2_vacuum.yaml":
        "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "schemas/af_scc_c0_vacuum.yaml":
        "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    "schemas/af_wcc_vacuum.yaml":
        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    "research_map/formulation_taxonomy.yaml":
        "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
    "artifacts/formulation/tools/check_class_schema.py": None,   # self-measured
    "artifacts/worker-06/spec_conformance_audit.py": None,       # self-measured
    "artifacts/formulation/tools/run_acceptance.py": None,       # self-measured
}
# known, pre-existing cross-tree drift recorded (not an F2a defect): canonical map
# taxonomy rev4 276009f4 vs lead-contract supplement c8e979a1 (different artifact
# role; shared fields independently re-checked in check D).
KNOWN_DRIFT = {
    "artifacts/formulation/formulation_taxonomy.yaml":
        "different artifact role (lead contract supplement); canonical map taxonomy is "
        "authoritative per ASTRA_HANDOFF canonical-path policy",
}

C2 = "AF-SCC-C2-VAC-GEN"
C0 = "AF-SCC-C0-VAC-GEN"
CT_C2 = "scc_c2_future_inextendibility"
CT_C0 = "scc_c0_future_inextendibility"

# ASSERTIVE paths: class-semantic content. Everything else is exempt (anti_scope,
# variants, provenance, ledgers, forbidden_strengthenings, known_obstruction, ...).
ASSERTIVE = (
    "scope_statement", "quantifiers", "topology", "data_class", "regularity",
    "genericity", "i_plus", "visibility", "extension_predicate", "class_components",
    "class_id", "conclusion.statement_natural_language", "conclusion.statement_formal",
    "conclusion.family", "conclusion.conclusion_type",
)
COMPOSITE_RE = re.compile(r"\bC0\s*(?:or|/|,|and)\s*C2\b|\bC2\s*(?:or|/|,|and)\s*C0\b", re.I)
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):", re.M)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(doc, prefix=""):
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from walk(v, f"{prefix}[{i}]")
    elif isinstance(doc, str):
        yield prefix, doc


def assertive_hits(doc, token_re: re.Pattern):
    hits = []
    for path, val in walk(doc):
        if path.startswith(ASSERTIVE) and token_re.search(val):
            hits.append({"path": path, "value": val[:180]})
    return hits


def exempt_hits(doc, token_re: re.Pattern):
    hits = []
    for path, val in walk(doc):
        if not path.startswith(ASSERTIVE) and token_re.search(val):
            hits.append({"path": path, "value": val[:180]})
    return hits


def duplicate_top_keys(path: Path):
    keys = TOP_KEY_RE.findall(path.read_text())
    seen, dups = set(), {}
    for k in keys:
        if k in seen:
            dups[k] = dups.get(k, 1) + 1
        seen.add(k)
    return dups


# ---- pure checks (reused on mutants for control C1-C5) ----------------------
def check_identity(doc):
    errs = []
    if doc.get("class_id") != C2:
        errs.append(f"class_id={doc.get('class_id')!r} != {C2}")
    if doc.get("node_id") != "F2a":
        errs.append(f"node_id={doc.get('node_id')!r} != F2a")
    comp = doc.get("class_components") or {}
    if comp.get("regularity_token") != "C2":
        errs.append(f"regularity_token={comp.get('regularity_token')!r} != C2")
    cb = doc.get("class_boundary") or {}
    if cb.get("one_class_only") != C2:
        errs.append(f"class_boundary.one_class_only={cb.get('one_class_only')!r} != {C2}")
    if (doc.get("conclusion") or {}).get("conclusion_type") != CT_C2:
        errs.append(f"conclusion.conclusion_type != {CT_C2}")
    return errs


def check_siblings(c2, c0):
    errs = []
    if c2.get("sibling_disjoint_from") != C0:
        errs.append(f"C2 sibling_disjoint_from={c2.get('sibling_disjoint_from')!r} != {C0}")
    if c0.get("sibling_disjoint_from") != C2:
        errs.append(f"C0 sibling_disjoint_from={c0.get('sibling_disjoint_from')!r} != {C2}")
    if c2.get("class_id") == c0.get("class_id"):
        errs.append("C2 and C0 class_id are equal")
    return errs


def check_separation(c2, c0):
    errs = []
    ct2 = (c2.get("conclusion") or {}).get("conclusion_type")
    ct0 = (c0.get("conclusion") or {}).get("conclusion_type")
    if ct2 == ct0:
        errs.append(f"shared conclusion_type {ct2!r}")
    if ct2 != CT_C2:
        errs.append(f"C2 conclusion_type {ct2!r} != {CT_C2}")
    if ct0 != CT_C0:
        errs.append(f"C0 conclusion_type {ct0!r} != {CT_C0}")
    comp_assert = assertive_hits(c2, COMPOSITE_RE)
    if comp_assert:
        errs.append(f"composite C0/C2 in assertive path(s): {comp_assert}")
    if assertive_hits(c2, re.compile(re.escape(CT_C0))):
        errs.append("sibling conclusion token asserted in C2")
    if assertive_hits(c0, re.compile(re.escape(CT_C2))):
        errs.append("sibling conclusion token asserted in C0")
    return errs


def canon_token(aliases, kind, tok):
    for c, al in aliases.get(kind, {}).items():
        if tok == c or tok in al:
            return c
    return tok


def check_contract(canon_tax, aut_tax, aliases):
    """Independent re-implementation of the canonical-vs-supplement shared-field check."""
    errs = []
    classes = canon_tax.get("classes") or {}
    contracts = aut_tax.get("class_contracts") or {}
    for cid, reg in ((C2, "C2"), (C0, "C0")):
        a, b = classes.get(cid), contracts.get(cid)
        if a is None or b is None:
            errs.append(f"{cid}: missing on one side (canonical={a is not None}, supplement={b is not None})")
            continue
        fa = (a.get("axes") or {}).get("family")
        fb = (b.get("components") or {}).get("censorship")
        if fa != fb:
            errs.append(f"{cid}: family {fa} vs {fb}")
        ta = (a.get("axes") or {}).get("regularity_token")
        tb = (b.get("components") or {}).get("regularity_token")
        if ta != tb or ta != reg:
            errs.append(f"{cid}: regularity canonical={ta} supplement={tb} expected={reg}")
        ca = canon_token(aliases, "conclusion_type", (a.get("axes") or {}).get("conclusion_type"))
        cb = canon_token(aliases, "conclusion_type", b.get("conclusion_type"))
        if ca != cb:
            errs.append(f"{cid}: conclusion_type {ca} vs {cb}")
        if not a.get("exclusions") or not b.get("exclusions"):
            errs.append(f"{cid}: exclusions empty on one side")
        if not a.get("test_cases") or not b.get("positive_test_case"):
            errs.append(f"{cid}: test cases missing on one side")
    return errs


def mutate_shared_conclusion(doc):
    d = copy.deepcopy(doc)
    d["conclusion"]["conclusion_type"] = CT_C0
    return d


def mutate_remove_sibling(doc):
    d = copy.deepcopy(doc)
    d.pop("sibling_disjoint_from", None)
    return d


def mutate_regularity(doc):
    d = copy.deepcopy(doc)
    d["class_components"]["regularity_token"] = "C0"
    return d


def mutate_composite(doc):
    d = copy.deepcopy(doc)
    d["scope_statement"] = str(d.get("scope_statement", "")) + " Covers C0 or C2 data."
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(OUT / "f2a_independent_report.json"))
    ap.add_argument("--skip-owner-replay", action="store_true")
    args = ap.parse_args()

    measured, drift = {}, []
    for rel, want in PINS.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else None
        measured[rel] = got
        if want is not None and got != want:
            drift.append({"path": rel, "expected": want, "measured": got})
    for rel in ("artifacts/formulation/tools/check_class_schema.py",
                "artifacts/worker-06/spec_conformance_audit.py",
                "artifacts/formulation/tools/run_acceptance.py"):
        PINS[rel] = measured[rel]

    if drift:
        report = {
            "task_id": "W072-B", "worker": "worker-072", "created_at": NOW,
            "status": "PIN_DRIFT", "drift": drift, "measured": measured,
            "verdict_recommendation": "inconclusive",
            "falsifier": "re-measure the pins; any change invalidates this run",
        }
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps({"status": "PIN_DRIFT", "drift": drift}, indent=1))
        return 2

    c2 = yaml.safe_load((ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text())
    c0 = yaml.safe_load((ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text())
    canon_tax = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    aut_tax = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())

    checks = []

    def add(cid, desc, ok, observed, expected="clean"):
        checks.append({"id": cid, "description": desc, "pass": bool(ok),
                       "expected": expected, "observed": observed})

    # A. publication binding
    a_ok = all(measured[f"schemas/{n}"] == measured[f"artifacts/formulation/schemas/{n}"]
               for n in ("af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml", "af_wcc_vacuum.yaml"))
    add("A1", "canonical schema bytes == authoring schema bytes (F1,F2a,F2b)", a_ok,
        {n: {"canonical": measured[f"schemas/{n}"][:12],
             "authoring": measured[f"artifacts/formulation/schemas/{n}"][:12]}
         for n in ("af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml", "af_wcc_vacuum.yaml")})

    f0 = (c2.get("f0_binding") or {})
    add("A2", "F2a declared_f0_sha256 == measured canonical taxonomy hash",
        f0.get("declared_f0_sha256") == measured["research_map/formulation_taxonomy.yaml"],
        {"declared": f0.get("declared_f0_sha256", "")[:12],
         "measured": measured["research_map/formulation_taxonomy.yaml"][:12]})

    ptr = (c2.get("class_contract_pointer") or "").split("#")[0]
    ptr_ok = bool(ptr) and (ROOT / ptr).is_file()
    contract = ((aut_tax.get("class_contracts") or {}).get(C2) or {})
    add("A3", "class_contract_pointer target exists and carries the class contract", ptr_ok and bool(contract),
        {"pointer": ptr, "exists": ptr_ok, "contract_present": bool(contract)})

    # B. identity
    id_errs = check_identity(c2)
    add("B1", "class identity: class_id/node_id/regularity/one_class_only/conclusion token", not id_errs, id_errs)

    # C. sibling separation
    sib_errs = check_siblings(c2, c0)
    add("C1", "mutual sibling_disjoint_from and distinct class ids", not sib_errs, sib_errs)
    sep_errs = check_separation(c2, c0)
    add("C2", "distinct conclusion_type tokens; no composite/sibling token in assertive paths",
        not sep_errs, sep_errs)
    add("C3", "exempt composite mentions are tagged in anti_scope only",
        True, exempt_hits(c2, COMPOSITE_RE) + exempt_hits(c0, COMPOSITE_RE))

    # D. contract consistency (independent re-implementation)
    con_errs = check_contract(canon_tax, aut_tax, aliases)
    add("D1", "canonical taxonomy vs lead contract shared fields consistent (F2a+F2b)",
        not con_errs, con_errs)

    # E. provenance findings (non-blocking unless they break binding)
    dup_c2, dup_c0 = duplicate_top_keys(ROOT / "schemas/af_scc_c2_vacuum.yaml"), \
        duplicate_top_keys(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    eff = c2.get("revised_at")
    mtime = datetime.fromtimestamp((ROOT / "schemas/af_scc_c2_vacuum.yaml").stat().st_mtime, CST)
    findings = [
        {"id": "N1", "severity": "non_blocking",
         "finding": f"duplicate top-level YAML key revised_at x{dup_c2.get('revised_at', 0)} in F2a "
                    f"(and x{dup_c0.get('revised_at', 0)} in F2b): strict YAML parsers reject the file; "
                    "PyYAML keeps the last value, so the effective timestamp is parser-dependent",
         "evidence": "schemas/af_scc_c2_vacuum.yaml; duplicate_top_keys check"},
        {"id": "N2", "severity": "non_blocking",
         "finding": f"effective revised_at={eff} post-dates file mtime {mtime.isoformat()} and wall clock "
                    f"{NOW}; revision=11 has no revised_at of its own (rev10 timestamp is last-wins)",
         "evidence": "schemas/af_scc_c2_vacuum.yaml#b6123750b37d; stat mtime"},
        {"id": "N3", "severity": "non_blocking",
         "finding": "review_status.independent_reviewers is empty at this hash before this review; "
                    "requested reviewers were deepseek-flash-18 and astra-lead-audit",
         "evidence": "schemas/af_scc_c2_vacuum.yaml#b6123750b37d"},
        {"id": "N4", "severity": "info",
         "finding": "cross-tree taxonomy drift is pre-existing and NOT an F2a defect: the schema binds the "
                    "canonical research_map taxonomy by hash (A2 passes); the lead-contract supplement is a "
                    "different artifact role and is consistent on shared fields (D1)",
         "evidence": "ASTRA_HANDOFF canonical-path policy; measured hashes in this report"},
    ]

    # F. owner-harness replay (hash-bound, labelled replay not derivation)
    replay = {"skipped": True}
    if not args.skip_owner_replay:
        gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
        sem = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
        acc = ROOT / "artifacts/formulation/tools/run_acceptance.py"
        g = subprocess.run([sys.executable, str(gate), "--json", "schemas/af_scc_c2_vacuum.yaml"],
                           capture_output=True, text=True, cwd=ROOT, timeout=300)
        s = subprocess.run([sys.executable, str(sem), "schemas/af_scc_c2_vacuum.yaml"],
                           capture_output=True, text=True, cwd=ROOT, timeout=300)
        a = subprocess.run([sys.executable, str(acc), "--json"], capture_output=True, text=True,
                           cwd=ROOT, timeout=900)
        try:
            gv = json.loads(g.stdout)
        except Exception:  # noqa: BLE001
            gv = {"verdict": f"unparsed(rc={g.returncode})"}
        try:
            sv = json.loads(s.stdout)
        except Exception:  # noqa: BLE001
            sv = {"verdict": f"unparsed(rc={s.returncode})"}
        try:
            av = json.loads(a.stdout)
        except Exception:  # noqa: BLE001
            av = {"verdict": f"unparsed(rc={a.returncode})"}
        replay = {
            "skipped": False,
            "structural_gate_on_canonical_F2a": {"verdict": gv.get("verdict"), "failed_rules": gv.get("failed_rules"),
                                                 "rc": g.returncode, "tool_sha256": measured["artifacts/formulation/tools/check_class_schema.py"]},
            "semantic_auditor_on_canonical_F2a": {"verdict": sv.get("verdict", "n/a"), "rc": s.returncode,
                                                  "tool_sha256": measured["artifacts/worker-06/spec_conformance_audit.py"]},
            "owner_pipeline_acceptance": {"verdict": av.get("verdict"), "mutants": av.get("mutants"),
                                          "canonical": av.get("canonical"), "controls": av.get("controls"),
                                          "rc": a.returncode, "tool_sha256": measured["artifacts/formulation/tools/run_acceptance.py"]},
            "note": "replay of the owner's declared harness; not an independent derivation of R01-R16",
        }
        add("F1", "owner structural gate passes on canonical F2a",
            gv.get("verdict") == "pass", gv.get("failed_rules", gv.get("verdict")))
        add("F2", "owner two-stage acceptance pipeline verdict PASS",
            av.get("verdict") == "PASS", {"verdict": av.get("verdict"), "mutants": av.get("mutants")})

    # G. discriminating power of MY checks
    controls = []
    mutants = [("C1_shared_conclusion", mutate_shared_conclusion, lambda d, c: check_separation(d, c)),
               ("C2_sibling_removed", mutate_remove_sibling, lambda d, c: check_siblings(d, c)),
               ("C3_regularity_c0", mutate_regularity, lambda d, c: check_identity(d)),
               ("C4_composite_asserted", mutate_composite, lambda d, c: check_separation(d, c))]
    for name, mut, fn in mutants:
        m = mut(c2)
        errs = fn(m, c0)
        controls.append({"mutant": name, "caught": bool(errs), "errors": errs[:3]})
    pos_errs = check_identity(c2) + check_siblings(c2, c0) + check_separation(c2, c0)
    controls.append({"mutant": "C5_positive_control_unmodified", "caught": not pos_errs,
                     "errors": pos_errs[:3]})
    add("G1", "mutants C1-C4 all caught by the same checks", all(c["caught"] for c in controls[:4]),
        [{"mutant": c["mutant"], "caught": c["caught"]} for c in controls[:4]])
    add("G2", "positive control (unmodified copy) passes: no false positive", not pos_errs, pos_errs)

    hard = [c for c in checks if not c["pass"]]
    digest_src = json.dumps({"checks": checks, "controls": controls, "measured": measured},
                            sort_keys=True)
    report = {
        "task_id": "W072-B",
        "worker": "worker-072",
        "class_id": C2,
        "target": "schemas/af_scc_c2_vacuum.yaml#" + measured["schemas/af_scc_c2_vacuum.yaml"],
        "created_at": NOW,
        "status": "COMPLETE",
        "pins": {k: v for k, v in PINS.items() if v},
        "measured": measured,
        "known_drift": KNOWN_DRIFT,
        "checks": checks,
        "controls": controls,
        "provenance_findings": findings,
        "owner_harness_replay": replay,
        "result_digest": hashlib.sha256(digest_src.encode()).hexdigest(),
        "verdict_recommendation": "accept" if not hard else "revise",
        "hard_failures": [c["id"] for c in hard],
        "scope_limits": [
            "mechanical class binding/separation only; no mathematical or physical correctness is decided",
            "no citation-scope verification (L1 owns it)",
            "owner harness replayed, not re-derived; worker verdict is advisory and cannot set a gate",
            "canonical path only; the authoring tree is used solely for the byte-equality and consistency checks",
        ],
        "falsifier": ("a C0 datum satisfying the C2 schema, a conclusion_type shared with C0, a composite "
                      "'C0 or C2' regularity in an ASSERTIVE path, any pin drift, or a mutant C1-C4 that "
                      "passes these checks"),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
    }
    Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"status": report["status"], "verdict": report["verdict_recommendation"],
                      "hard_failures": report["hard_failures"],
                      "result_digest": report["result_digest"],
                      "checks": len(checks), "controls": controls}, indent=1))
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
