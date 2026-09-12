#!/usr/bin/env python3
"""W082-F0-INDEP-VERDICT-01: independent machine checks for F0 (G-F0).

This checker is authored by worker-082, NOT by the F0 author or the class-binding
tooling authors. It re-implements the acceptance-relevant checks independently
(PyYAML parse, axis-vector disjointness, namespace scan, quantifier audit,
provenance audit, cross-artifact binding) and separately *runs* the repository
tooling as corroboration only (recorded under tool_corroboration, never counted
as worker-082 evidence).

Read-only with respect to every artifact except this directory.

Usage:
  python3 artifacts/worker-082/f0_independent_verdict/run_checks.py \
      --json artifacts/worker-082/f0_independent_verdict/evidence.json
Exit 0 = no blocking (critical/major) worker-082 check failed; 1 = a blocking check
failed; minor/info failures are recorded but do not change the exit code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "research_map/formulation_taxonomy.yaml"
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
REQUIRED_CLASS_KEYS = ["label", "axes", "hypotheses", "exclusions", "conclusion",
                       "test_cases", "provenance"]
SCHEMA_BINDINGS = {
    "F1": ROOT / "schemas/af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
CONTAM = re.compile(
    r"cubic\s+graph|minimum\s+degree|2\^?k\s*cycle|cap\s*set|funsearch|erdos|"
    r"weakly\s+connected|strongly\s+connected", re.I)
MERGE_PAT = re.compile(r"C0\s*(?:or|and|/|,|\+)\s*C2|C2\s*(?:or|and|/|,|\+)\s*C0|C0C2|C2C0", re.I)
SUP = {"\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3"}
NEG_EQUIV = re.compile(r"(?:not|no|never|without|nor)\s+(?:\w+\s+){0,2}(?:asserted\s+)?equivalen", re.I)


def asserts_equivalence(text: str) -> bool:
    """True only for an affirmative 'equivalently'/'equivalence', not for
    negated meta-statements such as 'not an asserted equivalence (review HF-06)'."""
    if re.search(r"\bequivalently\b", text, re.I):
        return True
    for m in re.finditer(r"\bequivalence\b", text, re.I):
        window = text[max(0, m.start() - 45):m.end()]
        if not NEG_EQUIV.search(window):
            return True
    return False


def now() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm_reg(s: str) -> str:
    for k, v in SUP.items():
        s = s.replace(k, v)
    return re.sub(r"[\^_{}\s]", "", s)


def read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def run_cmd(cmd: list[str]) -> dict:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        return {"cmd": " ".join(cmd), "exit_code": r.returncode,
                "stdout_tail": r.stdout.strip().splitlines()[-3:],
                "stderr_tail": r.stderr.strip().splitlines()[-3:]}
    except Exception as e:  # noqa: BLE001
        return {"cmd": " ".join(cmd), "exit_code": None, "error": repr(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "artifacts/worker-082/f0_independent_verdict/evidence.json"))
    ap.add_argument("--expect-sha256", default=None)
    args = ap.parse_args()

    t0 = now()
    raw_b = read_bytes(TARGET)
    sha = sha256_bytes(raw_b)
    frozen_copy = ROOT / "artifacts/worker-082/f0_independent_verdict" / f"reviewed_f0_{sha[:12]}.yaml"
    frozen_copy.write_bytes(raw_b)
    frozen_sha = sha256_bytes(read_bytes(frozen_copy))
    tax = yaml.safe_load(raw_b.decode())
    checks: list[dict] = []

    def ck(cid, name, ok, detail, evidence=None, severity="major"):
        checks.append({"id": cid, "name": name, "result": "pass" if ok else "fail",
                       "severity": severity, "detail": detail, "evidence": evidence or []})
        return ok

    # --- A. identity -------------------------------------------------------
    ids = tax.get("class_ids") or []
    ck("W082-A1", "exactly the four frozen class ids",
       isinstance(ids, list) and sorted(ids) == sorted(FROZEN) and len(ids) == 4,
       f"class_ids={ids}")
    ck("W082-A2", "class_ids key list is duplicate-free",
       len(ids) == len(set(ids)), f"n={len(ids)} distinct={len(set(ids))}")

    # --- B. per-class structural completeness ------------------------------
    missing = {}
    for cid in FROZEN:
        c = (tax.get("classes") or {}).get(cid)
        if not isinstance(c, dict):
            missing[cid] = ["<class block missing>"]
            continue
        miss = [k for k in REQUIRED_CLASS_KEYS if k not in c]
        tc = c.get("test_cases") or {}
        if not tc.get("positive") or not tc.get("negative"):
            miss.append("test_cases.positive/negative")
        if not isinstance(c.get("hypotheses"), list) or not c["hypotheses"]:
            miss.append("hypotheses")
        if miss:
            missing[cid] = miss
    ck("W082-B1", "per-class required structure", not missing,
       "all four classes carry axes/hypotheses/exclusions/conclusion/test_cases/provenance"
       if not missing else json.dumps(missing))

    # --- C. axis + guard consistency (independent G2/G6 analogue) ----------
    fam_err, reg_err, conc_err = [], [], []
    for cid in FROZEN:
        c = tax["classes"][cid]
        ax = c["axes"]
        fam = ax.get("family")
        reg = ax.get("regularity_token")
        ct = (c.get("conclusion") or {}).get("type")
        if fam == "SCC" and reg not in ("C0", "C2"):
            reg_err.append(f"{cid}: SCC regularity_token={reg!r}")
        if fam == "WCC" and reg not in (None, "null"):
            reg_err.append(f"{cid}: WCC regularity_token={reg!r}")
        if fam == "SCC" and not str(ct).lower().startswith("strong_cosmic_censorship"):
            conc_err.append(f"{cid}: family SCC but conclusion_type={ct!r}")
        if fam == "WCC" and ct != "weak_cosmic_censorship":
            conc_err.append(f"{cid}: family WCC but conclusion_type={ct!r}")
    ck("W082-C1", "G2 analogue: SCC carry exactly one regularity token, WCC none",
       not reg_err, "; ".join(reg_err) or "ok")
    ck("W082-C2", "G6 analogue: conclusion family matches class family",
       not conc_err, "; ".join(conc_err) or "ok")

    # --- D. independent disjointness over axis vectors ---------------------
    axes = {cid: tax["classes"][cid]["axes"] for cid in FROZEN}
    declared = {}
    for row in tax.get("disjointness") or []:
        p = tuple(row.get("pair") or [])
        if len(p) == 2:
            declared[tuple(sorted(p))] = row.get("decisive_axes") or []
    import itertools
    pair_fail, pair_report = [], {}
    for a, b in itertools.combinations(sorted(FROZEN), 2):
        key = tuple(sorted((a, b)))
        differing = [k for k in set(axes[a]) | set(axes[b]) if axes[a].get(k) != axes[b].get(k)]
        dec = declared.get(key)
        ok = bool(dec) and bool(set(dec) & set(differing))
        pair_report[f"{a} | {b}"] = {"declared": dec, "actual_differing": sorted(differing),
                                     "separated_by_declared_axis": ok}
        if not ok:
            pair_fail.append(f"{a}|{b}: declared={dec} differing={differing}")
    ck("W082-D1", "all 6 pairs declared and separated on a named decisive axis",
       len(declared) == 6 and not pair_fail,
       f"{len(declared)}/6 pairs declared; " + ("; ".join(pair_fail) or "each pair intersects its declared axes"),
       [json.dumps(pair_report)])

    # --- E. merged-regularity scan over the semantic subset (own impl) -----
    semantic_texts = [str(tax.get("scope_statement") or "")]
    for cid in FROZEN:
        c = tax["classes"][cid]
        semantic_texts += [str(c.get("label") or ""), json.dumps(c.get("axes") or {}),
                           json.dumps(c.get("conclusion") or {}),
                           json.dumps(c.get("exclusions") or [])]
    merge_hits = []
    for i, t in enumerate(semantic_texts):
        for m in MERGE_PAT.finditer(norm_reg(t)):
            merge_hits.append({"surface": i, "match": m.group(0)})
    ck("W082-E1", "no merged C0/C2 regularity asserted in class surfaces (own impl)",
       not merge_hits, "no merged-regularity assertion outside guard/prohibition sections"
       if not merge_hits else json.dumps(merge_hits))

    # --- F. quantifier / genericity / equivalence audit --------------------
    quant = {}
    for cid in FROZEN:
        c = tax["classes"][cid]
        text = str((c.get("conclusion") or {}).get("text") or "")
        gk = c["axes"].get("genericity_kind")
        quant[cid] = {
            "genericity_kind": gk,
            "explicit_comeager": bool(re.search(r"comeager", text, re.I)),
            "explicit_admissible_quantifier": bool(re.search(r"for every admissible", text, re.I)),
            "asserts_equivalence": asserts_equivalence(text),
            "uses_bare_generic": bool(re.search(r"\bfor generic data\b", text, re.I)),
        }
    scalar = quant["AF-WCC-SCALAR-SPH"]
    ck("W082-F1", "every class conclusion binds an explicit genericity quantifier",
       all(v["explicit_comeager"] and v["explicit_admissible_quantifier"]
           for k, v in quant.items() if k != "AF-WCC-SCALAR-SPH"),
       "three vacuum classes carry 'For every admissible (s,delta) ... comeager set G'; "
       f"AF-WCC-SCALAR-SPH: comeager={scalar['explicit_comeager']} "
       f"admissible={scalar['explicit_admissible_quantifier']} bare_generic={scalar['uses_bare_generic']}",
       [json.dumps(quant)])
    ck("W082-F2", "unresolved-genericity classes do not quantify a conclusion with bare 'generic data'",
       not (str(scalar["genericity_kind"]).startswith("unresolved") and scalar["uses_bare_generic"]),
       f"AF-WCC-SCALAR-SPH genericity_kind={scalar['genericity_kind']} "
       f"conclusion says 'For generic data in the class'={scalar['uses_bare_generic']}")
    ck("W082-F3", "no unsourced 'equivalently' in a class conclusion (HF-06 analogue)",
       not any(v["asserts_equivalence"] for v in quant.values()),
       "asserting classes: " + (", ".join(k for k, v in quant.items() if v["asserts_equivalence"]) or "none"),
       [json.dumps(quant)])

    # --- G. namespace hygiene (class-shaped tokens) ------------------------
    toks = sorted(set(re.findall(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)+", raw_b.decode().upper())))
    foreign = [t for t in toks if t not in FROZEN]
    ck("W082-G1", "no class-shaped token outside the frozen four",
       not foreign, f"distinct class-shaped tokens={toks}; foreign={foreign}")

    # --- H. contamination + self-certification -----------------------------
    contam = sorted({m.group(0).lower() for m in CONTAM.finditer(raw_b.decode())})
    ck("W082-H1", "HF-13 cross-project contamination tokens absent", not contam,
       "none" if not contam else str(contam))
    selfcert = []
    if tax.get("claims_theorem_status") is not False:
        selfcert.append(f"claims_theorem_status={tax.get('claims_theorem_status')!r}")
    if str(tax.get("status")) != "draft_unverified":
        selfcert.append(f"status={tax.get('status')!r}")
    if re.search(r"validation_status:\s*[\"']?passed", raw_b.decode()):
        selfcert.append("file sets validation_status=passed")
    if re.search(r"conclusion_type:\s*[\"']?theorem", raw_b.decode()):
        selfcert.append("file asserts conclusion_type=theorem")
    if tax.get("provenance", {}).get("claims_theorem_status") is not False:
        selfcert.append("provenance.claims_theorem_status not False")
    ck("W082-H2", "HF-14 analogue: no self-certified pass / theorem claim", not selfcert,
       "draft_unverified, claims_theorem_status false, no validation_status=passed"
       if not selfcert else "; ".join(selfcert))

    # --- I. provenance / timestamp audit -----------------------------------
    written = str(tax.get("written_at") or "")
    decided = str((tax.get("class_scope_adjudication") or {}).get("decided_at") or "")
    rev = tax.get("revision")
    prov = []
    if rev == 4 and decided and written and decided > written:
        prov.append(f"revision 4 content decided_at={decided} postdates written_at={written}")
    if rev == 4 and "revision_note_rev4" not in tax:
        prov.append("revision 4 without revision_note_rev4")
    ck("W082-I1", "written_at describes the revision it ships with",
       not prov, "; ".join(prov) or f"revision={rev} written_at={written} decided_at={decided}",
       [f"supersedes={json.dumps(tax.get('class_scope_adjudication', {}).get('supersedes'))[:300]}"],
       severity="minor")

    # --- J. cross-artifact binding to canonical F1/F2a/F2b -----------------
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    ct_alias = aliases.get("conclusion_type", {})
    canon_of = {}
    for canon, alist in ct_alias.items():
        for a in alist:
            canon_of[a] = canon
    bind_report, bind_fail = {}, []
    for node, p in SCHEMA_BINDINGS.items():
        if not p.is_file():
            bind_fail.append(f"{node}: schema missing at {p}")
            continue
        s = yaml.safe_load(p.read_text())
        declared = (s.get("f0_binding") or {}).get("declared_f0_sha256")
        ct = (s.get("conclusion") or {}).get("conclusion_type")
        bind_report[node] = {"schema": str(p.relative_to(ROOT)),
                             "class_id": s.get("class_id"),
                             "declared_f0_sha256": declared,
                             "declares_current_f0": declared == sha,
                             "conclusion_type": ct,
                             "conclusion_type_canonical": canon_of.get(ct, ct)}
        if declared != sha:
            bind_fail.append(f"{node}: declared_f0_sha256={str(declared)[:16]} != measured {sha[:16]}")
    ck("W082-J1", "F1/F2a/F2b bind the measured F0 hash", not bind_fail,
       "all three canonical schemas declare the measured F0 hash" if not bind_fail
       else "; ".join(bind_fail), [json.dumps(bind_report)])
    tax_cts = {cid: (tax["classes"][cid]["conclusion"].get("type")) for cid in FROZEN}
    alias_used = [f"{cid}:{ct}" for cid, ct in tax_cts.items() if ct != canon_of.get(ct, ct)]
    ck("W082-J2", "F0 conclusion_type tokens are canonical per VOCAB_ALIASES (info-level)",
       not alias_used,
       "F0 uses alias tokens equivalent-under-VOCAB_ALIASES: " + ", ".join(alias_used)
       if alias_used else "all tokens canonical",
       [json.dumps({"f0": tax_cts, "canonical": {k: canon_of.get(v, v) for k, v in tax_cts.items()}})],
       severity="info")

    # --- K. does the authoring consistency gate cover the D3 claim it certifies?
    cons_tool = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    d3_lines = []
    if cons_tool.is_file():
        for i, line in enumerate(cons_tool.read_text().splitlines(), 1):
            if "for every data set in the class" in line or "comeager" in line:
                d3_lines.append(f"{i}: {line.strip()}")
    covers_all = any("SCALAR" in ln for ln in d3_lines)
    ck("W082-K1", "authoring consistency gate covers the 'comeager in each class' (D3) claim",
       covers_all,
       "gate predicate does NOT mention AF-WCC-SCALAR-SPH: it only tests the two SCC texts plus the "
       "legacy C0 phrase, so it reports CONSISTENT while AF-WCC-SCALAR-SPH carries no comeager quantifier"
       if not covers_all else "gate predicate covers all four classes",
       d3_lines or ["consistency tool missing"], severity="major")

    # --- L. tool corroboration (NOT worker-082 evidence) -------------------
    tool = {}
    tool["validate_taxonomy"] = run_cmd([sys.executable, str(ROOT / "artifacts/worker-01/validate_taxonomy.py")])
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import class_separation as cs  # type: ignore
        flags = cs.findings_for_text(raw_b.decode(), "canonical F0")
        tool["class_separation_flags"] = {"n": len(flags), "flags": flags}
        tool["class_separation_regression"] = cs.regression()
    except Exception as e:  # noqa: BLE001
        tool["class_separation_flags"] = {"error": repr(e)}

    # --- drift re-measure --------------------------------------------------
    sha_after = sha256_bytes(read_bytes(TARGET))
    checks.append({"id": "W082-Z1", "name": "target hash stable across the check window",
                   "result": "pass" if sha_after == sha else "fail", "severity": "critical",
                   "detail": f"t0={sha[:16]} t1={sha_after[:16]}", "evidence": []})

    failed = [c["id"] for c in checks if c["result"] == "fail"]
    blocking = [c["id"] for c in checks if c["result"] == "fail" and c["severity"] in ("critical", "major")]
    nonblocking = [c["id"] for c in checks if c["result"] == "fail" and c["severity"] in ("minor", "info")]
    out = {
        "schema_version": "0.1",
        "artifact": "artifacts/worker-082/f0_independent_verdict/evidence.json",
        "task_id": "W082-F0-INDEP-VERDICT-01",
        "worker": "worker-082",
        "created_at": now(),
        "measurement_window": {"t0": t0, "t1": now()},
        "target": {
            "path": "research_map/formulation_taxonomy.yaml",
            "sha256_measured": sha,
            "bytes": len(raw_b),
            "mtime": dt.datetime.fromtimestamp(TARGET.stat().st_mtime).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "revision": rev,
            "frozen_copy": str(frozen_copy.relative_to(ROOT)),
            "frozen_copy_sha256": frozen_sha,
            "class_ids": ids,
        },
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["result"] == "pass"),
        "checks_failed": len(failed),
        "failed_check_ids": failed,
        "blocking_failed_check_ids": blocking,
        "nonblocking_failed_check_ids": nonblocking,
        "disjointness_matrix": pair_report,
        "quantifier_audit": quant,
        "binding_report": bind_report,
        "tool_corroboration": tool,
        "commands": {"run_checks": "python3 artifacts/worker-082/f0_independent_verdict/run_checks.py --json <this file>"},
        "no_completion_claim": "worker-082 cannot set done/passed or any gate verdict; this is evidence for controller/lead adjudication.",
    }
    if args.expect_sha256 and args.expect_sha256 != sha:
        out["expected_sha256"] = args.expect_sha256
        out["expected_sha256_match"] = False
    Path(args.json).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("checks_passed", "checks_failed", "failed_check_ids",
                                          "blocking_failed_check_ids", "target")}, indent=2))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
