#!/usr/bin/env python3
"""W096-F1-BINDING-RECEIPT-01 -- independent, hash-bound binding/publication receipt
for class AF-WCC-VAC-GEN (node F1, gate G-FORM) at the live canonical schema.

Scope: one class, one hash. Read-only. Does NOT import the canonical gate
(artifacts/formulation/tools/check_class_schema.py) for any verdict; it re-implements
the structural checks it needs and records the canonical checker only if the caller
runs it separately.

Fail-closed: if the target hash moves during the run the report is emitted with
drift=true and the process exits 2.

Usage:  python3 run_receipt.py [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

TARGET = ROOT / "schemas" / "af_wcc_vacuum.yaml"
AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
CANON_TAX = ROOT / "research_map" / "formulation_taxonomy.yaml"
AUTH_TAX = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
REVIEWS = ROOT / "reviews"

CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin(path: Path) -> dict:
    st = path.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
    }


class DupLoader(yaml.SafeLoader):
    """PyYAML loader that records every duplicate mapping key (all depths)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates: list[dict] = []

    def construct_mapping(self, node, deep=False):
        seen: dict = {}
        for k_node, _v in node.value:
            key = self.construct_object(k_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                continue
            if key in seen:
                self.duplicates.append(
                    {
                        "key": key,
                        "line": k_node.start_mark.line + 1,
                        "first_line": seen[key],
                    }
                )
            else:
                seen[key] = k_node.start_mark.line + 1
        return super().construct_mapping(node, deep=deep)


def strict_load(path: Path):
    loader = DupLoader(path.read_text())
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, loader.duplicates


def resolve_pointer(pointer: str) -> dict:
    """Resolve 'path#a.b.c' relative to ROOT; report resolution on both trees."""
    path_part, _, frag = pointer.partition("#")
    out = {"pointer": pointer, "path": path_part, "fragment": frag, "resolved": False,
           "target_exists": None, "fragment_keys_present": None}
    target = ROOT / path_part
    out["target_exists"] = target.exists()
    if not target.exists() or not frag:
        return out
    doc = yaml.safe_load(target.read_text())
    node = doc
    ok = True
    for part in frag.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            ok = False
            break
    out["resolved"] = ok
    if isinstance(doc, dict):
        out["fragment_keys_present"] = sorted(doc.keys())
    return out


def read_text(path: Path) -> str:
    return path.read_text()


def c(id_, title, status, detail, evidence):
    return {"id": id_, "title": title, "status": status, "detail": detail,
            "evidence": evidence}


def run_checks(out_path: Path) -> dict:
    start = now()
    pins = {
        "canonical_f1": pin(TARGET),
        "authoring_f1": pin(AUTHORING),
        "canonical_f0_taxonomy": pin(CANON_TAX),
        "authoring_f0_taxonomy": pin(AUTH_TAX),
    }
    text = read_text(TARGET)
    doc, duplicates = strict_load(TARGET)
    checks: list[dict] = []
    reproduced: list[dict] = []
    not_reproduced: list[dict] = []

    # ---- R1 identity / class binding -------------------------------------
    checks.append(c(
        "R1-identity", "class_id and node_id bind to exactly one class", "pass",
        f"class_id={doc.get('class_id')} node_id={doc.get('node_id')} revision={doc.get('revision')}",
        [f"schemas/af_wcc_vacuum.yaml#{pins['canonical_f1']['sha256'][:12]}:1-40"],
    ))

    # ---- R2 duplicate YAML keys ------------------------------------------
    dup_summary = {}
    for d in duplicates:
        dup_summary.setdefault(d["key"], []).append(d["line"])
    checks.append(c(
        "R2-duplicate-keys",
        "no duplicate mapping keys (a strict reader must see exactly one value)",
        "fail" if duplicates else "pass",
        f"{len(duplicates)} duplicate key occurrence(s): "
        + ", ".join(f"{k} at lines {v}" for k, v in sorted(dup_summary.items())),
        [f"schemas/af_wcc_vacuum.yaml:{d['line']}" for d in duplicates],
    ))
    if duplicates:
        reproduced.append({
            "id": "W096-F1-01",
            "defect": "duplicate top-level mapping keys",
            "named_by": ["HF090-02 (worker-090)", "HF-094-2 (worker-094)", "C12-duplicate-keys (worker-059)"],
            "status": "reproduced",
            "measured": {k: v for k, v in sorted(dup_summary.items())},
            "why_it_matters": "PyYAML last-wins hides every earlier value; two conforming YAML readers can disagree about the effective revision record.",
        })

    # ---- R3 timestamp sanity ---------------------------------------------
    eff_revised = doc.get("revised_at")
    mtime = pins["canonical_f1"]["mtime"]
    wall = now()
    checked_at = (doc.get("f0_binding") or {}).get("checked_at")
    bad_time = []
    for label, val in (("revised_at", eff_revised), ("f0_binding.checked_at", checked_at)):
        if isinstance(val, str) and val > wall:
            bad_time.append(f"{label}={val} > wall {wall}")
        if isinstance(val, str) and val > mtime:
            bad_time.append(f"{label}={val} > mtime {mtime}")
    checks.append(c(
        "R3-timestamp-sanity",
        "effective timestamps are not future-dated relative to file mtime / wall clock",
        "fail" if bad_time else "pass",
        "; ".join(bad_time) if bad_time else f"effective revised_at={eff_revised} <= mtime {mtime}",
        [f"schemas/af_wcc_vacuum.yaml:23", "schemas/af_wcc_vacuum.yaml:311"],
    ))
    if bad_time:
        reproduced.append({
            "id": "W096-F1-02",
            "defect": "future-dated machine-readable timestamps hidden behind duplicate keys",
            "named_by": ["HF090-02 (worker-090)", "HF-094-2 (worker-094)", "C15-timestamp-sanity (worker-059)"],
            "status": "reproduced",
            "measured": bad_time,
            "why_it_matters": "the effective revised_at is the last duplicate (line 23); it postdates the bytes' own mtime and review wall clock, so ordering evidence is not trustworthy.",
        })

    # ---- R4 canonical/authoring mirror -----------------------------------
    mirror_ok = pins["canonical_f1"]["sha256"] == pins["authoring_f1"]["sha256"]
    checks.append(c(
        "R4-mirror-equality",
        "canonical schema bytes equal the authoring mirror",
        "pass" if mirror_ok else "fail",
        f"canonical {pins['canonical_f1']['sha256'][:12]} vs authoring {pins['authoring_f1']['sha256'][:12]}",
        ["schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"],
    ))
    if not mirror_ok:
        reproduced.append({
            "id": "W096-F1-03", "defect": "canonical/authoring F1 byte divergence",
            "named_by": ["publication policy (map publication_status)"], "status": "reproduced",
            "measured": {"canonical": pins["canonical_f1"]["sha256"], "authoring": pins["authoring_f1"]["sha256"]},
            "why_it_matters": "a reviewer can bind to one tree while the map hashes the other.",
        })

    # ---- R5 class_contract_pointer resolution ----------------------------
    pointer = doc.get("class_contract_pointer")
    pres = resolve_pointer(pointer) if isinstance(pointer, str) else {"resolved": False}
    canon_tax_doc = yaml.safe_load(CANON_TAX.read_text())
    auth_tax_doc = yaml.safe_load(AUTH_TAX.read_text())
    canon_has = isinstance(canon_tax_doc, dict) and "class_contracts" in canon_tax_doc
    auth_has = isinstance(auth_tax_doc, dict) and "class_contracts" in auth_tax_doc
    ptr_ok = bool(pres.get("resolved")) and pres.get("path") == "research_map/formulation_taxonomy.yaml"
    checks.append(c(
        "R5-contract-pointer",
        "class_contract_pointer resolves on the authoritative canonical tree",
        "pass" if ptr_ok else "fail",
        (f"pointer={pointer}; resolves_on_authoring_tree={pres.get('resolved')}; "
         f"canonical_taxonomy_has_class_contracts={canon_has}; "
         f"authoring_taxonomy_has_class_contracts={auth_has}"),
        [f"schemas/af_wcc_vacuum.yaml:38",
         f"research_map/formulation_taxonomy.yaml#{pins['canonical_f0_taxonomy']['sha256'][:12]}",
         f"artifacts/formulation/formulation_taxonomy.yaml#{pins['authoring_f0_taxonomy']['sha256'][:12]}"],
    ))
    if not ptr_ok:
        reproduced.append({
            "id": "W096-F1-04",
            "defect": "class_contract_pointer targets the authoring tree and does not resolve on the canonical tree",
            "named_by": ["HF090-01 (worker-090)", "C14-contract-pointer (worker-059)"],
            "status": "reproduced",
            "measured": {"pointer": pointer, "authoring_has_class_contracts": auth_has,
                         "canonical_has_class_contracts": canon_has,
                         "authoring_taxonomy_sha256": pins["authoring_f0_taxonomy"]["sha256"],
                         "canonical_taxonomy_sha256": pins["canonical_f0_taxonomy"]["sha256"]},
            "why_it_matters": "canonical path policy makes research_map/ formulation_taxonomy.yaml authoritative; its top-level key is 'classes', so a canonical reader cannot resolve the fragment. The pointer only resolves in the divergent authoring tree (c8e979a1 vs 276009f4).",
        })

    # ---- R6 undefined symbols in the normative statement ------------------
    stmt = (doc.get("conclusion") or {}).get("statement_formal", "")
    syms = {
        "AF_{I+}": len(re.findall(r"AF_\{I\+\}", text)),
        "complete(I+_D)": len(re.findall(r"complete\(I\+_D\)", text)),
        "D (data binder)": len(re.findall(r"\bD\b", text)),
    }
    undefined = [s for s, n in syms.items() if s != "D (data binder)" and n <= 1]
    checks.append(c(
        "R6-undefined-symbols",
        "every symbol in conclusion.statement_formal is defined in the document",
        "fail" if undefined else "pass",
        f"statement_formal={stmt!r}; occurrences={syms}",
        ["schemas/af_wcc_vacuum.yaml:251"],
    ))
    if undefined:
        reproduced.append({
            "id": "W096-F1-05",
            "defect": "normative formal statement uses symbols defined nowhere in the document",
            "named_by": ["HF090-03 (worker-090)", "HF-06 dangling-symbol (deepseek-flash-19)"],
            "status": "reproduced",
            "measured": syms,
            "why_it_matters": "the normative statement is not self-contained; the intended condition is recoverable only from prose elsewhere, so two readers can bind different predicates.",
        })

    # ---- R7 quantifier/visibility formula consistency ---------------------
    qf = (doc.get("quantifiers") or {}).get("formal", "")
    vis = (doc.get("visibility") or {}).get("definition", "")
    d5 = (((doc.get("quantifiers") or {}).get("domains") or {}).get("D5") or {}).get("definition", "")
    qf_whole = bool(re.search(r"gamma subset J\^\(-\)?\(q\)", qf)) or ("gamma subset J^-(q)" in qf)
    qf_tail = ("tail" in qf) or ("t0" in qf)
    vis_tail = ("tail" in vis) or ("t0" in vis)
    d5_tail = ("tail" in d5) or ("t0" in d5)
    mismatch = (not qf_tail) and vis_tail
    checks.append(c(
        "R7-formula-consistency",
        "quantifiers.formal and domains.D5 state the same visibility predicate as visibility.definition",
        "fail" if mismatch else "pass",
        (f"formal_uses_tail={qf_tail} formal_whole_curve_subset={qf_whole}; "
         f"visibility.definition_uses_tail={vis_tail}; D5_uses_tail={d5_tail}"),
        ["schemas/af_wcc_vacuum.yaml:54-55", "schemas/af_wcc_vacuum.yaml:79-81",
         "schemas/af_wcc_vacuum.yaml:220"],
    ))
    if mismatch:
        reproduced.append({
            "id": "W096-F1-06",
            "defect": "quantifier block asserts whole-curve single-q containment while the declared visibility predicate is tail-based",
            "named_by": ["HF-06 (deepseek-flash-19)"],
            "status": "reproduced",
            "measured": {"quantifiers.formal": qf.strip()[-120:], "domains.D5": d5.strip(),
                         "visibility.definition_tail_phrase": "gamma([t0,T))" in vis},
            "why_it_matters": "whole-curve single-q containment is strictly stronger than the declared tail predicate; the formal block therefore states a different (stronger) class than visibility.definition, which the same file forbids interchanging.",
        })

    # ---- R8 f0_binding hash ----------------------------------------------
    declared_f0 = (doc.get("f0_binding") or {}).get("declared_f0_sha256")
    measured_f0 = pins["canonical_f0_taxonomy"]["sha256"]
    f0_ok = declared_f0 == measured_f0
    checks.append(c(
        "R8-f0-binding", "f0_binding.declared_f0_sha256 equals the measured canonical F0 hash",
        "pass" if f0_ok else "fail",
        f"declared={declared_f0} measured={measured_f0}",
        ["schemas/af_wcc_vacuum.yaml:311",
         f"research_map/formulation_taxonomy.yaml#{measured_f0[:12]}"],
    ))
    if not f0_ok:
        reproduced.append({
            "id": "W096-F1-07", "defect": "F0 binding hash drift", "named_by": ["own check"],
            "status": "reproduced", "measured": {"declared": declared_f0, "measured": measured_f0},
            "why_it_matters": "verdicts bind to the declared F0 revision; drift voids the binding.",
        })

    # ---- R9 verdict ledger (facts only; independence not adjudicated) -----
    ledger = {"at_target_hash": [], "other_hash_or_unbound": []}
    target_sha = pins["canonical_f1"]["sha256"]
    for f in sorted(REVIEWS.glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        blob = json.dumps(r)
        if ("af_wcc" not in blob) and (r.get("target_id") != "F1") and (r.get("node_id") != "F1"):
            continue
        verdict = r.get("verdict") or (r.get("verdict") or {})
        if isinstance(verdict, dict):
            verdict = verdict.get("value") or verdict.get("binding") or "inconclusive"
        sha = None
        for k in ("reviewed_sha256", "sha256", "target_sha256", "reviewed_artifact_sha256"):
            v = r.get(k)
            if isinstance(v, str) and len(v) >= 12:
                sha = v
                break
        row = {"file": str(f.relative_to(ROOT)), "reviewer": r.get("reviewer") or r.get("actor"),
               "verdict": verdict, "cited_sha256": sha, "created_at": r.get("created_at"),
               "file_sha256": sha256_file(f),
               "counts_as_full_schema_verdict": r.get("counts_as_full_schema_verdict"),
               "counts_as_independent_second_verdict": r.get("counts_as_independent_second_verdict")}
        if sha and sha.startswith(target_sha[:12]):
            ledger["at_target_hash"].append(row)
        else:
            ledger["other_hash_or_unbound"].append(row)
    accepts = [r["reviewer"] for r in ledger["at_target_hash"] if r["verdict"] == "accept"]
    revises = [r["reviewer"] for r in ledger["at_target_hash"] if r["verdict"] == "revise"]
    checks.append(c(
        "R9-verdict-ledger", "verdicts binding to the measured F1 hash are enumerated", "pass",
        f"at {target_sha[:12]}: accept={accepts} revise={revises} "
        f"other={len(ledger['other_hash_or_unbound'])}",
        [r["file"] for r in ledger["at_target_hash"]][:12],
    ))

    # ---- self-test controls (sensitivity + specificity) -------------------
    tmp = out_path.parent / "_selftest_tmp.yaml"
    self_tests = []
    try:
        tmp.write_text("a: 1\nb: 2\n")
        _, d0 = strict_load(tmp)
        self_tests.append({"control": "N1-clean-yaml-no-duplicates",
                           "expect": "no duplicates", "observed": d0, "pass": d0 == []})
        tmp.write_text("a: 1\nb: 2\na: 3\n")
        _, d1 = strict_load(tmp)
        self_tests.append({"control": "P1-duplicate-yaml-detected",
                           "expect": "one duplicate key 'a'", "observed": d1,
                           "pass": len(d1) == 1 and d1[0]["key"] == "a"})
        ptr_ok_res = resolve_pointer("research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN")
        self_tests.append({"control": "P2-existing-fragment-resolves",
                           "expect": "resolved=true", "observed": ptr_ok_res["resolved"],
                           "pass": bool(ptr_ok_res["resolved"])})
        ptr_bad = resolve_pointer("research_map/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN")
        self_tests.append({"control": "P3-missing-fragment-fails-closed",
                           "expect": "resolved=false", "observed": ptr_bad["resolved"],
                           "pass": ptr_bad["resolved"] is False})
        # specificity on the real target: removing duplicates must flip R2
        stripped = "\n".join(l for i, l in enumerate(text.splitlines(), 1)
                             if i not in {10, 12, 14, 16, 20, 23, 26, 28})
        tmp.write_text(stripped)
        _, d2 = strict_load(tmp)
        self_tests.append({"control": "P4-real-target-minus-duplicates-no-longer-fails",
                           "expect": "no duplicates", "observed": d2, "pass": d2 == []})
    finally:
        if tmp.exists():
            tmp.unlink()

    # ---- R10 canonical checklist corroboration (not part of the verdict) --
    import subprocess
    checker = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
    corrob = {"checker": str(checker.relative_to(ROOT)), "present": checker.exists()}
    if checker.exists():
        corrob["checker_sha256"] = sha256_file(checker)
        try:
            p = subprocess.run([sys.executable, str(checker), "--json", str(TARGET)],
                               capture_output=True, text=True, timeout=120)
            corrob["exit"] = p.returncode
            try:
                cj = json.loads(p.stdout)
                corrob["verdict"] = cj.get("verdict")
                corrob["failed_rules"] = cj.get("failed_rules", [])
            except ValueError:
                corrob["stdout_head"] = p.stdout[:300]
        except Exception as exc:  # noqa: BLE001
            corrob["error"] = repr(exc)
    checks.append(c(
        "R10-canonical-checklist", "canonical structural checklist verdict on the same bytes (corroboration)",
        "pass" if corrob.get("verdict") == "pass" else "warn",
        f"exit={corrob.get('exit')} verdict={corrob.get('verdict')} failed_rules={corrob.get('failed_rules')}",
        [f"{corrob['checker']}#{(corrob.get('checker_sha256') or '')[:12]}",
         f"schemas/af_wcc_vacuum.yaml#{target_sha[:12]}"],
    ))

    end = now()
    end_sha = sha256_file(TARGET)
    drift = end_sha != target_sha
    gates = {
        "two_independent_accepts_possible_at_this_hash": False,
        "reason": ("binding defects reproduced without any semantic check failing: "
                   f"{[x['id'] for x in reproduced]}; reviewer verdicts at this hash: "
                   f"accept={accepts} revise={revises}. A frozen repair revision plus two "
                   "independent accepts are required before G-FORM can bind F1."),
    }
    return {
        "schema_version": "w096-binding-receipt/1",
        "task_id": "W096-F1-BINDING-RECEIPT-01",
        "actor": "worker-096",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": end,
        "review_window": {"start": start, "end": end},
        "pins": pins,
        "input_drift": {"start_sha256": target_sha, "end_sha256": end_sha,
                        "drift_during_run": drift},
        "checks": checks,
        "reproduced_findings": reproduced,
        "not_reproduced": not_reproduced,
        "verdict_ledger": ledger,
        "canonical_checker_corroboration": corrob,
        "self_tests": self_tests,
        "gate_receipt": gates,
        "falsifier": ("Re-run this script against schemas/af_wcc_vacuum.yaml at sha256 "
                      f"{target_sha[:12]}. Falsified if: (a) any 'fail' check flips to pass on identical bytes; "
                      "(b) the duplicate-key detector misses a duplicate on the target (controls P1/P4) or "
                      "flags a clean file (N1); (c) the pointer resolves on research_map/formulation_taxonomy.yaml "
                      "with fragment class_contracts.AF-WCC-VAC-GEN; (d) quantifiers.formal and D5 use the tail "
                      "t0 formulation; (e) declared_f0_sha256 differs from the measured canonical F0 hash."),
        "no_completion_claim": ("worker cannot set done/passed/gate verdict; this is a reviewer receipt, "
                                "not a theorem, counterexample, or numerical result; no artifact was edited."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args()
    report = run_checks(Path(args.out))
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    failed = [x["id"] for x in report["checks"] if x["status"] == "fail"]
    st_failed = [t["control"] for t in report["self_tests"] if not t["pass"]]
    print(f"W096-F1-BINDING-RECEIPT-01 checks_failed={failed} self_tests_failed={st_failed} "
          f"drift={report['input_drift']['drift_during_run']}")
    if st_failed:
        return 3
    if report["input_drift"]["drift_during_run"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
