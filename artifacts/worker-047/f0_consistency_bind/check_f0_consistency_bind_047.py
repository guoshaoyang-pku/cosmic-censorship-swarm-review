#!/usr/bin/env python3
"""W047-F0-CONSISTENCY-BIND-03 -- independent, read-only verification of the F0 companion-pair
consistency evidence at the rev12/rev28 pins.

Scope (class-bound): AF-WCC-VAC-GEN (F1), AF-SCC-C2-VAC-GEN (F2a), AF-SCC-C0-VAC-GEN (F2b);
the F0 companion pair is research_map/formulation_taxonomy.yaml (declared taxonomy) vs
artifacts/formulation/formulation_taxonomy.yaml (class-contract supplement), per FROZEN.json
logical_artifacts (REC-3).

What this instrument does NOT do: it does not set gate verdicts, node status, or
validation_status. It is a measurement bound to the bytes it snapshots.

Pre-registered criteria (fixed before measurement):
  C01 evidence-pin binding: each class schema's f0_binding.consistency_evidence_sha256 equals the
      measured sha256 of the consistency-evidence file.
  C02 evidence binds the compared trees: the evidence artifact contains the measured sha256 of
      BOTH compared artifacts (or an equivalent comparison-time pin).
  C03 declared-F0 binding: each schema's declared_f0_sha256 equals the measured taxonomy sha256;
      declared/supplement paths exist.
  C04 owner-checker replay: replaying artifacts/formulation/tools/check_taxonomy_consistency.py on
      a byte-identical sandbox reproduces the committed evidence document.
  C05 read-only: no canonical input's sha256 changes across the run.
  C06 binder-axis content agreement: for each class with a canonical schema, the regularity binder
      in the canonical taxonomy's conclusion.text agrees in form with the schema quantifier binder.
  C07 owner-checker sensitivity: mutating ONLY the binder axis pair->r in the taxonomy text flips
      the owner checker to INCONSISTENT (if not, the owner verdict is blind to that axis).
  C08 owner-checker calibration: mutating a field the owner checker DOES test
      (axes.regularity_token C2->C0) flips it to INCONSISTENT.
  C09 evidence class coverage: the evidence artifact lists exactly the classes shared by both trees.

Exit codes: 0 = all criteria PASS and controls calibrated; 1 = >=1 criterion FAIL;
2 = missing/unreadable/mutated-hard-pin input; 3 = canonical drift during the run;
4 = controls mis-calibrated (instrument not trustworthy).

No network. Fail closed. All mutations happen in throwaway sandbox copies under this task dir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
TASK = "W047-F0-CONSISTENCY-BIND-03"
WORKER = "worker-047"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-047/f0_consistency_bind -> repo root

TAX = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EV = "artifacts/formulation/evidence/taxonomy_consistency.json"
OWNER_TOOL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}
REQUIRED = [TAX, SUPP, EV, OWNER_TOOL, ALIASES] + list(SCHEMAS.values())

PAIR_RE = re.compile(r"G_\{s,?\s*delta\}|\(\s*s\s*,\s*delta\s*\)")
R_RE = re.compile(r"\br\s+in\s+D0\b|\bG_r\b|X\^r|X\^\{r\}")


class StrictLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys (silent last-wins is a defect)."""


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate mapping key: {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_yaml(path: Path):
    return yaml.load(path.read_text(), Loader=StrictLoader)


def binder_form(text: str) -> str:
    """Classify the regularity binder form of a statement text."""
    t = str(text or "")
    pair = bool(PAIR_RE.search(t))
    r = bool(R_RE.search(t))
    if pair and not r:
        return "pair_(s,delta)"
    if r and not pair:
        return "index_r"
    if pair and r:
        return "mixed"
    return "other"


def hex_tokens(raw: bytes, minlen: int = 12):
    return set(re.findall(rb"[0-9a-f]{%d,64}" % minlen, raw.lower()))


def evidence_binds(ev_doc, raw: bytes, tax_sha: str, supp_sha: str) -> bool:
    """True iff the evidence artifact pins both compared artifacts by measured hash."""
    toks = {t.decode() for t in hex_tokens(raw)}
    a = any(tax_sha.startswith(t) or t.startswith(tax_sha) for t in toks)
    b = any(supp_sha.startswith(t) or t.startswith(supp_sha) for t in toks)
    return bool(a and b)


def build_sandbox(dest: Path):
    (dest / "research_map").mkdir(parents=True, exist_ok=True)
    (dest / "artifacts/formulation/tools").mkdir(parents=True, exist_ok=True)
    (dest / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / TAX, dest / TAX)
    shutil.copyfile(ROOT / SUPP, dest / SUPP)
    shutil.copyfile(ROOT / ALIASES, dest / ALIASES)
    shutil.copyfile(ROOT / OWNER_TOOL, dest / OWNER_TOOL)


def run_owner(sandbox: Path):
    proc = subprocess.run(
        [sys.executable, str(sandbox / OWNER_TOOL)],
        cwd=str(sandbox),
        capture_output=True,
        text=True,
        timeout=120,
    )
    ev_path = sandbox / EV
    doc = None
    if ev_path.is_file():
        try:
            doc = json.loads(ev_path.read_text())
        except Exception:
            doc = None
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip()[-2000:],
        "evidence": doc,
        "evidence_sha256": sha256_file(ev_path) if ev_path.is_file() else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    snap = out / "snapshot"
    raw_dir = out / "raw"
    snap.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    criteria: list[dict] = []
    controls: list[dict] = []
    findings: list[dict] = []

    def crit(cid, desc, status, detail, evidence=None):
        criteria.append(
            {"id": cid, "description": desc, "status": status, "detail": detail,
             "evidence": evidence or []}
        )

    # ---- input snapshot and hard-pin check -----------------------------------------------
    pins = {}
    missing = []
    for rel in REQUIRED:
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        pins[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size, "mtime": mtime_iso(p)}
    if missing:
        (out / "report.json").write_text(json.dumps(
            {"task": TASK, "worker": WORKER, "exit_code": 2, "missing_inputs": missing},
            indent=2) + "\n")
        print(f"FAIL-CLOSED: missing inputs: {missing}")
        return 2

    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED:
        dst = snap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    for rel in REQUIRED:
        if sha256_file(snap / rel) != pins[rel]["sha256"]:
            print(f"FAIL-CLOSED: snapshot mismatch for {rel}")
            return 2
    (snap / "PINS.json").write_text(json.dumps(pins, indent=2) + "\n")

    A = load_yaml(snap / TAX)
    B = load_yaml(snap / SUPP)
    ev_raw = (snap / EV).read_bytes()
    ev_doc = json.loads(ev_raw)
    tax_sha = pins[TAX]["sha256"]
    supp_sha = pins[SUPP]["sha256"]
    ev_sha = pins[EV]["sha256"]
    schemas = {k: load_yaml(snap / v) for k, v in SCHEMAS.items()}

    # ---- C01 declared consistency-evidence pin matches measured bytes -------------------
    c01_rows = []
    for node, doc in schemas.items():
        declared = str((doc.get("f0_binding") or {}).get("consistency_evidence_sha256", ""))
        c01_rows.append({"node": node, "class": CLASS_OF[node], "declared": declared,
                         "measured": ev_sha, "match": declared == ev_sha})
    ok01 = all(r["match"] for r in c01_rows)
    crit("C01", "each schema's declared consistency_evidence_sha256 equals the measured evidence sha256",
         "PASS" if ok01 else "FAIL",
         "; ".join(f"{r['node']}: declared {r['declared'][:12]} vs measured {r['measured'][:12]}"
                   for r in c01_rows),
         [f"{SCHEMAS[row['node']]}#{row['declared'][:12] or 'none'}" for row in c01_rows]
         + [f"{EV}#{ev_sha[:12]}"])

    # ---- C02 evidence artifact binds both compared trees --------------------------------
    bound = evidence_binds(ev_doc, ev_raw, tax_sha, supp_sha)
    crit("C02", "evidence artifact pins both compared artifacts by measured sha256",
         "PASS" if bound else "FAIL",
         f"hex tokens >=12 chars in evidence bytes: {len(hex_tokens(ev_raw))}; "
         f"taxonomy {tax_sha[:12]} present={any(t.startswith(tax_sha) or tax_sha.startswith(t) for t in {x.decode() for x in hex_tokens(ev_raw)})}; "
         f"supplement {supp_sha[:12]} present={any(t.startswith(supp_sha) or supp_sha.startswith(t) for t in {x.decode() for x in hex_tokens(ev_raw)})}",
         [f"{EV}#{ev_sha[:12]}", f"{TAX}#{tax_sha[:12]}", f"{SUPP}#{supp_sha[:12]}"])

    # ---- C03 declared-F0 binding ---------------------------------------------------------
    c03_rows = []
    for node, doc in schemas.items():
        fb = doc.get("f0_binding") or {}
        declared_f0 = str(fb.get("declared_f0_sha256", ""))
        paths_ok = (ROOT / str(fb.get("declared_f0_artifact", ""))).is_file() and \
                   (ROOT / str(fb.get("class_contract_supplement", ""))).is_file()
        c03_rows.append({"node": node, "declared_f0": declared_f0, "taxonomy": tax_sha,
                         "match": declared_f0 == tax_sha, "paths_exist": paths_ok})
    ok03 = all(r["match"] and r["paths_exist"] for r in c03_rows)
    crit("C03", "each schema's declared_f0_sha256 equals measured taxonomy sha256 and both paths exist",
         "PASS" if ok03 else "FAIL",
         "; ".join(f"{r['node']}: {r['declared_f0'][:12]}=={r['taxonomy'][:12]}? {r['match']}, paths {r['paths_exist']}"
                   for r in c03_rows),
         [f"{TAX}#{tax_sha[:12]}"])

    # ---- C04 owner-checker replay reproduces committed evidence --------------------------
    sb1 = out / "sandbox_replay"
    if sb1.exists():
        shutil.rmtree(sb1)
    build_sandbox(sb1)
    rep1 = run_owner(sb1)
    (raw_dir / "owner_replay_stdout.txt").write_text(
        f"exit={rep1['exit_code']}\nstdout={rep1['stdout']}\nstderr={rep1['stderr']}\n")
    same = rep1["evidence"] == ev_doc
    consistent_flag = bool(ev_doc.get("consistent"))
    flag_consistent = rep1["exit_code"] == (0 if consistent_flag else 1)
    ok04 = bool(same and flag_consistent)
    crit("C04", "owner checker replay on byte-identical sandbox reproduces the committed evidence document",
         "PASS" if ok04 else "FAIL",
         f"replay exit={rep1['exit_code']}, stdout={rep1['stdout']!r}, document_equal={same}, "
         f"exit_matches_consistent_flag={flag_consistent}",
         [f"{OWNER_TOOL}#{pins[OWNER_TOOL]['sha256'][:12]}", f"{EV}#{ev_sha[:12]}"])

    # ---- C06 binder-axis content agreement (taxonomy text vs schema quantifiers) ---------
    c06_rows = []
    for node, cls in CLASS_OF.items():
        a_text = str(((A.get("classes", {}).get(cls) or {}).get("conclusion") or {}).get("text", ""))
        s_q = schemas[node].get("quantifiers") or {}
        s_text = json.dumps({"formal": s_q.get("formal"), "ordered": s_q.get("ordered")})
        fa, fs = binder_form(a_text), binder_form(s_text)
        diverges = (fa == "pair_(s,delta)" and fs == "index_r")
        c06_rows.append({"node": node, "class": cls, "taxonomy_binder": fa, "schema_binder": fs,
                         "diverges": diverges})
    ok06 = not any(r["diverges"] for r in c06_rows)
    crit("C06", "canonical taxonomy conclusion.text binder form agrees with the class schema quantifier binder form",
         "PASS" if ok06 else "FAIL",
         "; ".join(f"{r['node']}/{r['class']}: taxonomy={r['taxonomy_binder']} schema={r['schema_binder']}"
                   for r in c06_rows),
         [f"{TAX}#{tax_sha[:12]}"] + [f"{SCHEMAS[r['node']]}#{pins[SCHEMAS[r['node']]]['sha256'][:12]}"
                                      for r in c06_rows])

    # ---- C07 owner checker sensitivity to the binder axis (all three pair classes) -------
    sb2 = out / "sandbox_mut_binder"
    if sb2.exists():
        shutil.rmtree(sb2)
    build_sandbox(sb2)
    Am = load_yaml(snap / TAX)
    mutated = []
    for node, cls in CLASS_OF.items():
        c = Am["classes"][cls]["conclusion"]
        before = str(c.get("text", ""))
        after = PAIR_RE.sub(lambda m: "r in D0" if "(" in m.group(0) else "G_r", before)
        if after != before:
            c["text"] = after
            mutated.append(cls)
    (sb2 / TAX).write_text(yaml.safe_dump(Am, sort_keys=False, allow_unicode=True))
    rep2 = run_owner(sb2)
    (raw_dir / "owner_binder_mutation_stdout.txt").write_text(
        f"mutated_classes={mutated}\nexit={rep2['exit_code']}\nstdout={rep2['stdout']}\nstderr={rep2['stderr']}\n")
    ok07 = rep2["exit_code"] != 0
    crit("C07", "owner checker flips to INCONSISTENT when only the binder axis is mutated pair->r",
         "PASS" if ok07 else "FAIL",
         f"mutated {len(mutated)} class texts {mutated}; replay exit={rep2['exit_code']}, stdout={rep2['stdout']!r}"
         + ("" if ok07 else " -> BLIND SPOT: owner 'consistent: true' does not cover the binder axis"),
         [f"{OWNER_TOOL}#{pins[OWNER_TOOL]['sha256'][:12]}"])

    # ---- C08 owner checker calibration on a field it does test ---------------------------
    sb3 = out / "sandbox_mut_regularity"
    if sb3.exists():
        shutil.rmtree(sb3)
    build_sandbox(sb3)
    A3 = load_yaml(snap / TAX)
    A3["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["regularity_token"] = "C0"
    (sb3 / TAX).write_text(yaml.safe_dump(A3, sort_keys=False, allow_unicode=True))
    rep3 = run_owner(sb3)
    (raw_dir / "owner_regularity_mutation_stdout.txt").write_text(
        f"exit={rep3['exit_code']}\nstdout={rep3['stdout']}\nstderr={rep3['stderr']}\n")
    ok08 = rep3["exit_code"] != 0
    crit("C08", "owner checker flips to INCONSISTENT on a mutated tested axis (regularity_token C2->C0)",
         "PASS" if ok08 else "FAIL",
         f"replay exit={rep3['exit_code']}, stdout={rep3['stdout']!r}",
         [f"{OWNER_TOOL}#{pins[OWNER_TOOL]['sha256'][:12]}"])

    # ---- C09 evidence class coverage ------------------------------------------------------
    shared = sorted(set(A.get("class_ids", [])) & set(B.get("class_contracts", {})))
    listed = sorted(ev_doc.get("classes_compared", []))
    ok09 = listed == shared
    crit("C09", "evidence artifact lists exactly the classes shared by both trees",
         "PASS" if ok09 else "FAIL",
         f"evidence classes_compared={listed}; shared class set={shared}",
         [f"{EV}#{ev_sha[:12]}"])

    # ---- C05 read-only: canonical inputs unchanged ----------------------------------------
    after = {rel: sha256_file(ROOT / rel) for rel in REQUIRED}
    drift = [rel for rel in REQUIRED if after[rel] != pins[rel]["sha256"]]
    crit("C05", "no canonical input changed during the run (read-only measurement)",
         "PASS" if not drift else "FAIL",
         "all canonical input sha256 unchanged" if not drift else f"drifted: {drift}",
         [f"{rel}#{pins[rel]['sha256'][:12]}" for rel in REQUIRED[:3]])

    # ---- own controls K1-K8 ----------------------------------------------------------------
    def ctl(cid, desc, expect, observed):
        ok = expect == observed
        controls.append({"id": cid, "description": desc, "expect": expect,
                         "observed": observed, "status": "PASS" if ok else "FAIL"})
        return ok

    ctl("K1", "pair-binder detector fires on pair-typed synthetic text", True,
        binder_form("For every admissible (s,delta) there is a comeager set G_{s,delta}") == "pair_(s,delta)")
    ctl("K2", "binder detector reports index_r on r-typed synthetic text", True,
        binder_form("forall r in D0: exists G_r subset X^r_vac(AF)") == "index_r")
    ctl("K3", "evidence-binds detector true on synthetic evidence containing both hashes", True,
        evidence_binds({}, f'{{"a":"{tax_sha}","b":"{supp_sha}"}}'.encode(), tax_sha, supp_sha))
    ctl("K4", "evidence-binds detector false on evidence containing neither hash", False,
        evidence_binds({}, b'{"consistent": true}', tax_sha, supp_sha))
    ctl("K5", "hash equality helper true on equal inputs", True, (tax_sha == tax_sha))
    ctl("K6", "hash equality helper false on unequal inputs", False, (tax_sha == supp_sha))
    try:
        yaml.load("a: 1\na: 2\n", Loader=StrictLoader)
        k7 = False
    except yaml.constructor.ConstructorError:
        k7 = True
    ctl("K7", "strict YAML loader rejects a duplicate-key document", True, k7)
    ctl("K8", "class-set comparator detects a missing class", True,
        (sorted(set(A.get("class_ids", [])) & set(B.get("class_contracts", {}))) != sorted(
            set(A.get("class_ids", [])) & set(list(B.get("class_contracts", {}))[:-1]))))
    controls_ok = all(c["status"] == "PASS" for c in controls)

    # ---- findings --------------------------------------------------------------------------
    if not ok01:
        findings.append({
            "id": "CB-1", "severity": "critical",
            "detail": "All three rev12 schemas declare f0_binding.consistency_evidence_sha256 = "
                      f"{c01_rows[0]['declared'][:12]} but the on-disk {EV} measures {ev_sha[:12]}; "
                      "every f0_binding therefore points at bytes that are not the bytes on disk, and the "
                      "declared pin was invalidated without a new artifact event for the evidence file.",
            "falsifier": "Re-pin f0_binding.consistency_evidence_sha256 to the measured sha256 of the "
                         "current evidence bytes (and register the evidence file as an artifact) so that "
                         "declared == measured on a fresh read; then CB-1 is void.",
            "evidence_refs": [f"{SCHEMAS[r['node']]}#{pins[SCHEMAS[r['node']]]['sha256'][:12]}" for r in c01_rows]
                             + [f"{EV}#{ev_sha[:12]}"],
        })
    if not bound:
        findings.append({
            "id": "CB-2", "severity": "critical",
            "detail": f"{EV}#{ev_sha[:12]} asserts consistent=true for the companion pair but contains no "
                      f"sha256 of either compared tree ({tax_sha[:12]} / {supp_sha[:12]}) and no "
                      "comparison-time pin. The consistency claim is unbound: it cannot be attributed to "
                      "the pinned rev5 taxonomy and the current supplement, so it is not evidence for the "
                      "G-F0 companion-pair criterion.",
            "falsifier": "Publish an evidence schema that records the measured sha256 of both compared "
                         "trees and a comparator that fails when either mismatches; a re-run on the same "
                         "bytes then voids CB-2.",
            "evidence_refs": [f"{EV}#{ev_sha[:12]}", f"{TAX}#{tax_sha[:12]}", f"{SUPP}#{supp_sha[:12]}"],
        })
    if not ok06 or not ok07:
        findings.append({
            "id": "CB-3", "severity": "critical",
            "detail": "Content divergence on the regularity-domain axis: the canonical taxonomy's "
                      "conclusion.text for F1/F2a/F2b still binds the pair (s,delta) with G_{s,delta}, while "
                      "the rev12 class schemas bind the tagged index r in D0 with G_r / X^r_vac(AF). The "
                      "owner consistency checker reports consistent=true because it never compares this "
                      "axis (C07 mutation control: rewriting the taxonomy text to the schema form leaves "
                      "the owner verdict CONSISTENT).",
            "falsifier": "A canonical taxonomy revision whose conclusion.text binds r in D0 (or a schema "
                         "revert to pair typing), or an owner checker that fails on this divergence, voids "
                         "CB-3; a later file write alone is not a falsifier.",
            "evidence_refs": [f"{TAX}#{tax_sha[:12]}"] + [f"{SCHEMAS[r['node']]}#{pins[SCHEMAS[r['node']]]['sha256'][:12]}"
                                                           for r in c06_rows],
        })
    if ok01 and bound and ok06:
        findings.append({"id": "CB-none", "severity": "info",
                         "detail": "No binding/typing defect reproduced at the pinned bytes.",
                         "falsifier": "n/a", "evidence_refs": []})

    # ---- report ----------------------------------------------------------------------------
    failed = [c["id"] for c in criteria if c["status"] == "FAIL"]
    exit_code = 0
    if failed:
        exit_code = 1
    if drift:
        exit_code = 3
    if not controls_ok:
        exit_code = 4

    report = {
        "task_id": TASK,
        "worker": WORKER,
        "generated_at": now_iso(),
        "root": str(ROOT),
        "task_dir": str(out),
        "scope": {
            "node_ids": ["F0", "F1", "F2a", "F2b"],
            "class_ids": sorted(set(CLASS_OF.values())),
            "pins": pins,
            "authority_note": "worker measurement only; cannot set gate verdicts, node status or validation_status",
        },
        "criteria": criteria,
        "controls": controls,
        "findings": findings,
        "summary": {
            "PASS": sum(1 for c in criteria if c["status"] == "PASS"),
            "FAIL": len(failed),
            "INFO": sum(1 for c in criteria if c["status"] == "INFO"),
            "failed_ids": failed,
            "controls_pass": f"{sum(1 for c in controls if c['status'] == 'PASS')}/{len(controls)}",
        },
        "owner_tool_replay": {
            "tool": f"{OWNER_TOOL}#{pins[OWNER_TOOL]['sha256'][:12]}",
            "exit_code": rep1["exit_code"],
            "stdout": rep1["stdout"],
        },
        "canonical_stability": {"drift": drift, "stable": not drift},
        "exit_code": exit_code,
        "overall_falsifier": "Falsified if, at the pins recorded in snapshot/PINS.json: (a) any schema's "
                             "consistency_evidence_sha256 equals the measured evidence sha256; (b) the "
                             "evidence artifact contains the measured sha256 of both compared trees; "
                             "(c) the taxonomy conclusion.text binder form matches the schema quantifier "
                             "binder form for F1/F2a/F2b; or (d) the owner checker flips on a pair->r "
                             "binder-axis mutation. A later file write is not a falsifier.",
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{TASK}: " + " ".join(f"{c['id']}={c['status']}" for c in criteria)
          + f" | controls {report['summary']['controls_pass']} | exit={exit_code}")
    for f in findings:
        print(f"  [{f['severity']}] {f['id']}: {f['detail'][:160]}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
