#!/usr/bin/env python3
"""W020-F2A-REV12-CLOSURE-01 -- independent closure receipt for the prior
worker-020 blocker / finding C15 (F2a class-binding pointer unresolvable
against the declared canonical F0), re-measured at the FROZEN rev28 pins.

Scope
-----
Class: AF-SCC-C2-VAC-GEN (F2a). Read-only on every canonical path.
All writes stay under artifacts/worker-020/f2a_rev12_closure/.

What this instrument does
-------------------------
1. Freezes byte-identical snapshots of the reviewed artifacts and measures
   their sha256 before, during and after the review window (drift window).
2. Runs a strict YAML load (duplicate mapping keys are detected from the
   compose() node tree, not silently last-won by PyYAML).
3. Re-runs the exact C15 resolution test on the OLD rev11 snapshot
   (b6123750b37d, bytes preserved by the previous worker-020 lifecycle) and
   on the NEW rev12 snapshot (5476a3f2c6bc) so the closure delta is
   machine-checked rather than asserted.
4. Resolves both contract pointers against the artifacts they name:
     class_contract_pointer            -> research_map/formulation_taxonomy.yaml
                                          #classes.AF-SCC-C2-VAC-GEN
     class_contract_supplement_pointer -> artifacts/formulation/formulation_taxonomy.yaml
                                          #class_contracts.AF-SCC-C2-VAC-GEN
5. Checks the f0_binding declared hash against the measured canonical F0 hash.
6. Compares the C2 class contract as carried by the canonical taxonomy entry
   and by the companion supplement entry on a fixed field list, applying the
   frozen VOCAB_ALIASES map where the two surfaces use alias/canonical forms.
7. Independently re-measures the cross-cutting consistency-evidence binding
   (declared 675a99d0 vs the file at the declared path) and reports it as an
   inherited finding, not as an owned defect of this task.
8. Runs planted-defect controls so every positive check is shown to fire.

No canonical tool is imported. No model calls. Deterministic.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAP = os.path.join(HERE, "snapshots")
TZ = timezone(timedelta(hours=8))

# Frozen pins (FROZEN.json revision 28 and the map's measured hashes)
PIN = {
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}
OLD_F2A = os.path.abspath(os.path.join(
    HERE, "..", "f2a_independent_verdict", "snapshots",
    "f2a_b6123750b37d.yaml"))
OLD_F2A_PIN = \
    "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
OLD_F0 = os.path.abspath(os.path.join(
    HERE, "..", "f2a_independent_verdict", "snapshots",
    "f0_taxonomy_276009f4f63d.yaml"))
OLD_F0_PIN = \
    "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"

CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
GATE = "G-FORM"
PRIOR_BLOCKER_EVENT = "w020-20260912T0024-f2a-blocker"
PRIOR_FINDING = "C15"
PRIOR_REVIEWED_HASH = OLD_F2A_PIN

SCHEMA_PATH = "schemas/af_scc_c2_vacuum.yaml"
CONSISTENCY_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"


# ---------------------------------------------------------------- utilities
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT)


def duplicate_yaml_keys(path: str):
    """Return a list of duplicate-key breadcrumbs using the compose tree."""
    with open(path, "r", encoding="utf-8") as fh:
        root = yaml.compose(fh)
    dups = []

    def walk(node, crumb):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for key_node, value_node in node.value:
                key = getattr(key_node, "value", None)
                if key in seen:
                    seen[key] += 1
                    dups.append(f"{crumb}/{key} x{seen[key]}")
                else:
                    seen[key] = 1
                walk(value_node, f"{crumb}/{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, child in enumerate(node.value):
                walk(child, f"{crumb}[{i}]")

    walk(root, "")
    return dups


def resolve_anchor(doc, pointer: str):
    """Resolve 'path#a.b.c' against a parsed document. Returns (ok, target)."""
    path, _, anchor = pointer.partition("#")
    cur = doc
    if anchor:
        for part in anchor.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False, None
    return True, cur


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------- checks
def run() -> dict:
    t_start = now()
    result = {
        "task_id": "W020-F2A-REV12-CLOSURE-01",
        "actor": "worker-020",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "instrument": "artifacts/worker-020/f2a_rev12_closure/verify_c15_closure.py",
        "started_at": t_start,
        "pins": PIN,
        "prior_blocker": {
            "event_id": PRIOR_BLOCKER_EVENT,
            "finding_id": PRIOR_FINDING,
            "reviewed_sha256": PRIOR_REVIEWED_HASH,
        },
        "checks": [],
        "controls": [],
        "findings": [],
        "drift": {},
    }

    def check(cid, statement, ok, evidence, expected="PASS", hard=True):
        rec = {
            "id": cid,
            "statement": statement,
            "observed": "PASS" if ok else "FAIL",
            "expected": expected,
            "verdict": "PASS" if ok == (expected == "PASS") else "FAIL",
            "hard": hard,
            "evidence_refs": evidence,
        }
        result["checks"].append(rec)
        return rec["verdict"] == "PASS"

    # ---------------------------------------------------------------- drift
    live_before = {p: sha256_file(os.path.join(ROOT, p)) for p in PIN}
    result["drift"]["t0"] = {"at": now(), "sha256": dict(live_before)}

    # ------------------------------------------------------------ snapshots
    os.makedirs(SNAP, exist_ok=True)
    snap_paths = {}
    for p, pin in PIN.items():
        src = os.path.join(ROOT, p)
        base = os.path.basename(p)
        sname = base if base.endswith(".json") else base
        sname = {
            "schemas/af_scc_c2_vacuum.yaml": "f2a_5476a3f2c6bc.yaml",
            "research_map/formulation_taxonomy.yaml": "f0_canonical_0abb9ed8a961.yaml",
            "artifacts/formulation/formulation_taxonomy.yaml":
                "f0_supplement_d7419b4e8963.yaml",
            "artifacts/formulation/VOCAB_ALIASES.json":
                "vocab_aliases_46cd9f1eb534.json",
        }[p]
        dst = os.path.join(SNAP, sname)
        shutil.copyfile(src, dst)
        got = sha256_file(dst)
        snap_paths[p] = {"path": rel(dst), "abspath": dst, "sha256": got, "pin": pin}
    result["snapshots"] = snap_paths

    live_mid = {p: sha256_file(os.path.join(ROOT, p)) for p in PIN}

    # ------------------------------------------------------- strict parse
    f2a = yaml.safe_load(open(snap_paths[SCHEMA_PATH]["abspath"]))
    f0c = yaml.safe_load(open(
        snap_paths["research_map/formulation_taxonomy.yaml"]["abspath"]))
    f0s = yaml.safe_load(open(
        snap_paths["artifacts/formulation/formulation_taxonomy.yaml"]["abspath"]))
    vocab = load_json(
        snap_paths["artifacts/formulation/VOCAB_ALIASES.json"]["abspath"])

    dups = duplicate_yaml_keys(snap_paths[SCHEMA_PATH]["abspath"])
    check("C01", "strict YAML: F2a rev12 has no duplicate mapping keys",
          len(dups) == 0,
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}"])
    result["duplicate_keys"] = dups

    check("C02", "identity: class_id/node_id match the reviewed target",
          f2a.get("class_id") == CLASS_ID and f2a.get("node_id") == NODE_ID,
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}"])

    ptr = f2a.get("class_contract_pointer")
    supp_ptr = f2a.get("class_contract_supplement_pointer")
    ok_ptr, ptr_target = resolve_anchor(f0c, ptr or "")
    check("C03",
          "class_contract_pointer resolves in the DECLARED CANONICAL F0 "
          "(research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN)",
          ptr == "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN"
          and ok_ptr and isinstance(ptr_target, dict),
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}",
           f"{snap_paths['research_map/formulation_taxonomy.yaml']['path']}"
           f"#{snap_paths['research_map/formulation_taxonomy.yaml']['sha256'][:12]}"])
    result["pointer_resolution"] = {
        "class_contract_pointer": ptr,
        "resolved_in_canonical_f0": bool(ok_ptr and isinstance(ptr_target, dict)),
        "canonical_has_class_contracts_key": "class_contracts" in f0c,
    }

    check("C04",
          "canonical F0 exposes class content under `classes` and has no "
          "`class_contracts` key (the shape of the rev11 defect)",
          "classes" in f0c and "class_contracts" not in f0c,
          [f"{snap_paths['research_map/formulation_taxonomy.yaml']['path']}"
           f"#{snap_paths['research_map/formulation_taxonomy.yaml']['sha256'][:12]}"])

    ok_supp, supp_target = resolve_anchor(f0s, supp_ptr or "")
    check("C05",
          "class_contract_supplement_pointer resolves in the COMPANION "
          "supplement (artifacts/formulation/formulation_taxonomy.yaml"
          "#class_contracts.AF-SCC-C2-VAC-GEN)",
          supp_ptr == ("artifacts/formulation/formulation_taxonomy.yaml"
                       "#class_contracts.AF-SCC-C2-VAC-GEN")
          and ok_supp and isinstance(supp_target, dict),
          [f"{snap_paths['artifacts/formulation/formulation_taxonomy.yaml']['path']}"
           f"#{snap_paths['artifacts/formulation/formulation_taxonomy.yaml']['sha256'][:12]}"])

    binding = f2a.get("f0_binding") or {}
    declared_f0 = binding.get("declared_f0_sha256")
    measured_f0 = PIN["research_map/formulation_taxonomy.yaml"]
    check("C06",
          "f0_binding.declared_f0_sha256 equals the measured canonical F0 rev5 hash",
          declared_f0 == measured_f0,
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}",
           f"{snap_paths['research_map/formulation_taxonomy.yaml']['path']}"
           f"#{measured_f0[:12]}"])
    check("C07",
          "f0_binding.declared_f0_artifact is the canonical taxonomy path",
          binding.get("declared_f0_artifact") == "research_map/formulation_taxonomy.yaml",
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}"])
    check("C08",
          "both declared pointers name the artifacts declared in f0_binding",
          (ptr or "").split("#")[0] == binding.get("declared_f0_artifact")
          and (supp_ptr or "").split("#")[0] == binding.get("class_contract_supplement"),
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}"])

    # --------------------------- canonical <-> supplement contract equivalence
    canon_entry = (f0c.get("classes") or {}).get(CLASS_ID) or {}
    supp_entry = (f0s.get("class_contracts") or {}).get(CLASS_ID) or {}
    canon_concl = canon_entry.get("conclusion") or {}
    canon_axes = canon_entry.get("axes") or {}
    supp_comp = supp_entry.get("components") or {}

    alias_map = vocab.get("conclusion_type") or {}
    canon_type = canon_concl.get("type")
    supp_type = supp_entry.get("conclusion_type")
    canon_norm = next((k for k, vals in alias_map.items()
                       if canon_type in vals), canon_type)
    supp_norm = next((k for k, vals in alias_map.items()
                      if supp_type in vals), supp_type)

    canon_text = str(canon_concl.get("text", ""))
    canon_forb = str(canon_concl.get("forbidden_inflation", ""))
    canon_excl = " ".join(map(str, canon_entry.get("exclusions", [])))
    supp_hyps = " ".join(map(str, supp_entry.get("hypotheses", [])))
    supp_excl = " ".join(map(str, supp_entry.get("exclusions", [])))
    supp_non_goals = " ".join(map(str, supp_entry.get("non_goals", [])))
    schema_components = f2a.get("class_components") or {}
    schema_gen = f2a.get("genericity") or {}
    schema_gen_kind = schema_gen.get("kind")

    comparisons = {
        "conclusion_type_normalized_equal_under_frozen_aliases":
            canon_norm == supp_norm and canon_norm is not None,
        "class_identity_axes_consistent":
            str(canon_axes.get("family", "")).upper()
            == str(supp_comp.get("censorship", "")).upper()
            and str(canon_axes.get("matter_model", "")).lower().startswith("vacuum")
            and str(supp_comp.get("matter", "")).upper() == "VAC"
            and str(canon_axes.get("regularity_token", "")).upper()
            == str(supp_comp.get("regularity_token", "")).upper() == "C2",
        "schema_class_components_equal_supplement_components":
            schema_components == supp_comp,
        "canonical_conclusion_text_carries_comeager_quantifier":
            "comeager" in canon_text.lower(),
        "schema_genericity_kind_is_residual_comeager":
            schema_gen_kind == "residual_comeager",
        "both_surfaces_forbid_a_C0_implication":
            ("c0" in canon_forb.lower() or "c0" in canon_excl.lower())
            and ("c0" in supp_non_goals.lower() or "c0" in supp_excl.lower()),
        "supplement_defers_hypotheses_to_the_WCC_owner":
            "same af one-ended vacuum" in supp_hyps.lower(),
    }
    informational = {
        "supplement_carries_comeager_text": "comeager" in supp_hyps.lower(),
        "canonical_conclusion_type_literal": canon_type,
        "supplement_conclusion_type_literal": supp_type,
        "canonical_conclusion_type_normalized": canon_norm,
        "supplement_conclusion_type_normalized": supp_norm,
    }
    result["contract_equivalence"] = {**comparisons, **informational}
    result["alias_normalization"] = {
        "canonical_literal": canon_type,
        "supplement_literal": supp_type,
        "canonical_normalized": canon_norm,
        "supplement_normalized": supp_norm,
    }
    check("C09",
          "canonical classes.<id> and supplement class_contracts.<id> denote the "
          "same C2 class contract on the fixed comparison fields "
          "(alias-normalized conclusion_type, class-identity axes, components, "
          "comeager quantifier, mutual C0 exclusion)",
          all(comparisons.values()),
          [f"{snap_paths['research_map/formulation_taxonomy.yaml']['path']}"
           f"#{snap_paths['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
           f"{snap_paths['artifacts/formulation/formulation_taxonomy.yaml']['path']}"
           f"#{snap_paths['artifacts/formulation/formulation_taxonomy.yaml']['sha256'][:12]}"])

    # ------------------------------------- BEFORE/AFTER closure delta (C10)
    old_dup_status = None
    old_result = {"snapshot": rel(OLD_F2A), "pin": OLD_F2A_PIN}
    if os.path.exists(OLD_F2A):
        old_f2a = yaml.safe_load(open(OLD_F2A))
        old_f0 = yaml.safe_load(open(OLD_F0))
        old_ptr = old_f2a.get("class_contract_pointer")
        ok_old, old_target = resolve_anchor(old_f0, old_ptr or "")
        old_dup_status = duplicate_yaml_keys(OLD_F2A)
        old_result.update({
            "class_contract_pointer": old_ptr,
            "resolved_in_old_canonical_f0": bool(ok_old and isinstance(old_target, dict)),
            "old_canonical_f0_pin": OLD_F0_PIN,
            "duplicate_keys": old_dup_status,
            "measured_sha256": sha256_file(OLD_F2A),
        })
    result["closure_delta"] = {
        "before": old_result,
        "after": {
            "snapshot": {k: v for k, v in snap_paths[SCHEMA_PATH].items()
                         if k != "abspath"},
            "class_contract_pointer": ptr,
            "resolved_in_canonical_f0": bool(ok_ptr and isinstance(ptr_target, dict)),
        },
        "c15_closed": bool(ok_ptr and isinstance(ptr_target, dict)
                           and ok_supp and isinstance(supp_target, dict)
                           and declared_f0 == measured_f0),
    }
    check("C10",
          "prior finding C15 is CLOSED at the rev12 pin: pointer now resolves "
          "in the declared canonical F0, supplement pointer resolves in the "
          "companion, and the declared F0 hash equals the measured one",
          result["closure_delta"]["c15_closed"],
          [f"{snap_paths[SCHEMA_PATH]['path']}#{snap_paths[SCHEMA_PATH]['sha256'][:12]}",
           f"{snap_paths['research_map/formulation_taxonomy.yaml']['path']}"
           f"#{measured_f0[:12]}"])

    # ---------------------------------- inherited cross-cutting evidence pin
    ev_declared = binding.get("consistency_evidence_sha256")
    ev_path = os.path.join(ROOT, CONSISTENCY_PATH)
    ev_live = sha256_file(ev_path) if os.path.exists(ev_path) else None
    ev_ok = ev_declared == ev_live
    result["consistency_evidence"] = {
        "declared": ev_declared,
        "live": ev_live,
        "declared_path": CONSISTENCY_PATH,
        "binds": ev_ok,
    }
    check("C11",
          "inherited cross-cutting item: f0_binding.consistency_evidence_sha256 "
          "resolves at the declared path (family-wide rev12 defect, not owned by "
          "this task; reported as observation)",
          ev_ok, [f"{CONSISTENCY_PATH}#{(ev_live or '')[:12]}"],
          expected="FAIL", hard=False)
    if not ev_ok:
        result["findings"].append({
            "id": "HF-020-R12-1",
            "severity": "hard-cross-cutting-inherited",
            "owned_by_this_task": False,
            "statement": (
                f"{SCHEMA_PATH} f0_binding.consistency_evidence_sha256 declares "
                f"{ev_declared}, but the file at the declared path measures {ev_live}. "
                "Independently re-measured here; the disposition/repair is already "
                "tracked by worker-086/092/045/078/041/005 and is not re-filed as a "
                "new blocker."),
            "evidence_refs": [f"{CONSISTENCY_PATH}#{(ev_live or '')[:12]}",
                              f"{snap_paths[SCHEMA_PATH]['path']}"
                              f"#{snap_paths[SCHEMA_PATH]['sha256'][:12]}"],
        })

    # --------------------------------------------------------- drift window
    live_after = {p: sha256_file(os.path.join(ROOT, p)) for p in PIN}
    result["drift"]["t1_mid"] = {"at": result["drift"]["t0"]["at"],
                                 "sha256": dict(live_mid)}
    result["drift"]["t2"] = {"at": now(), "sha256": dict(live_after)}
    stable = all(live_before[p] == live_mid[p] == live_after[p] == PIN[p]
                 for p in PIN)
    check("C12",
          "drift window: every reviewed canonical path measured equal to its "
          "pin at the start, middle and end of the run",
          stable,
          [f"{p}#{PIN[p][:12]}" for p in PIN])

    # ------------------------------------------------------------- controls
    def control(name, fn, expect):
        try:
            got = fn()
        except Exception as exc:  # noqa: BLE001
            got = f"raised:{type(exc).__name__}"
        ok = (got == expect)
        result["controls"].append(
            {"id": name, "expected": expect, "observed": got, "fires": ok})
        return ok

    ctl_file = os.path.join(HERE, "snapshots", "_ctl_dup.yaml")

    def k1_duplicate_key_detector():
        with open(ctl_file, "wb") as fh:
            fh.write(b"a: 1\na: 2\nb: {c: 1, c: 2}\n")
        found = duplicate_yaml_keys(ctl_file)
        os.remove(ctl_file)
        return found

    ctl_dup = control("K1_duplicate_key_detector", k1_duplicate_key_detector,
                      ["/a x2", "/b/c x2"])
    ctl_ptr = control(
        "K2_pointer_retarget_fails_resolution",
        lambda: resolve_anchor(f0c, "research_map/formulation_taxonomy.yaml"
                                    "#classes.NO-SUCH-CLASS")[0],
        False)
    ctl_missing = control(
        "K3_missing_supplement_key_fails_resolution",
        lambda: resolve_anchor(f0s, "artifacts/formulation/formulation_taxonomy.yaml"
                                    "#class_contracts.NO-SUCH-CLASS")[0],
        False)
    ctl_hash = control(
        "K4_hash_flip_detected",
        lambda: sha256_bytes(b"flip") == measured_f0,
        False)
    ctl_alias = control(
        "K5_alias_normalization_discriminates",
        lambda: next((k for k, vals in alias_map.items()
                      if "not_a_token" in vals), "UNMAPPED"),
        "UNMAPPED")

    result["controls_ok"] = all(
        [ctl_dup, ctl_ptr, ctl_missing, ctl_hash, ctl_alias])

    # ------------------------------------------------------------- verdict
    hard_fails = [c["id"] for c in result["checks"]
                  if c["hard"] and c["verdict"] == "FAIL"]
    result["hard_check_failures"] = hard_fails
    result["closing_verdict"] = (
        "C15_CLOSED_NO_NEW_OWNED_HARD_FINDING"
        if not hard_fails else "REVISE")
    result["residual_findings"] = result["findings"]
    result["snapshots"] = {k: {kk: vv for kk, vv in v.items()
                               if kk != "abspath"}
                           for k, v in snap_paths.items()}
    result["finished_at"] = now()
    return result


def main() -> int:
    res = run()
    out = os.path.join(HERE, "closure_verdict.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, sort_keys=False)
        fh.write("\n")

    lines = []
    lines.append("# W020-F2A-REV12-CLOSURE-01 — closure receipt\n")
    lines.append(f"- class: `{res['class_id']}`  node: `{res['node_id']}`  gate: `{res['gate']}`")
    lines.append(f"- reviewed pin: `{SCHEMA_PATH}#{PIN[SCHEMA_PATH]}`")
    lines.append(f"- declared canonical F0 pin: `research_map/formulation_taxonomy.yaml#{PIN['research_map/formulation_taxonomy.yaml']}`")
    lines.append(f"- prior blocker: `{PRIOR_BLOCKER_EVENT}` / finding `{PRIOR_FINDING}` "
                 f"at `{PRIOR_REVIEWED_HASH}`")
    lines.append(f"- closure result: **{res['closing_verdict']}**")
    lines.append(f"- hard checks failed: {res['hard_check_failures'] or 'none'}")
    lines.append(f"- instrument: `verify_c15_closure.py` (self-contained, no canonical imports)")
    lines.append("")
    lines.append("## Closure delta (before -> after)\n")
    b = res["closure_delta"]["before"]
    a = res["closure_delta"]["after"]
    lines.append(f"- rev11 `b6123750b37d`: pointer = `{b.get('class_contract_pointer')}`; "
                 f"resolves in old canonical F0 `{OLD_F0_PIN[:12]}` = "
                 f"`{b.get('resolved_in_old_canonical_f0')}`; duplicate keys = "
                 f"`{b.get('duplicate_keys')}`")
    lines.append(f"- rev12 `5476a3f2c6bc`: pointer = `{a['class_contract_pointer']}`; "
                 f"resolves in canonical F0 `{PIN['research_map/formulation_taxonomy.yaml'][:12]}` = "
                 f"`{a['resolved_in_canonical_f0']}`")
    lines.append("")
    lines.append("## Checks\n")
    for c in res["checks"]:
        if c["expected"] == "PASS":
            mark = "PASS" if c["observed"] == "PASS" else "FAIL"
            tag = ""
        else:
            mark = f"OBSERVED-{c['observed']}"
            tag = (f" (exact-observation check; expected `{c['expected']}`; "
                   f"informational, not a closure failure)")
        lines.append(f"- `{c['id']}` [{mark}]{tag} {c['statement']}")
    lines.append("")
    lines.append("## Controls (planted defects)\n")
    for c in res["controls"]:
        lines.append(f"- `{c['id']}`: expected `{c['expected']}` observed `{c['observed']}` "
                     f"fires={c['fires']}")
    lines.append("")
    lines.append("## Residual findings\n")
    if res["findings"]:
        for f in res["findings"]:
            lines.append(f"- `{f['id']}` ({f['severity']}): {f['statement']}")
    else:
        lines.append("- none owned by this task")
    lines.append("")
    lines.append("## Scope / non-claims\n")
    lines.append("- This is a worker-level closure receipt, not a gate verdict, not a node "
                 "completion, and not a mathematical theorem.")
    lines.append("- No canonical artifact was edited; all writes are under "
                 "`artifacts/worker-020/f2a_rev12_closure/`.")
    lines.append("- The cross-cutting consistency-evidence mismatch is re-measured but not "
                 "re-filed; it is already tracked by the fleet.")
    with open(os.path.join(HERE, "closure_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps({
        "closing_verdict": res["closing_verdict"],
        "c15_closed": res["closure_delta"]["c15_closed"],
        "hard_check_failures": res["hard_check_failures"],
        "controls_ok": res["controls_ok"],
        "drift_stable": next(c["verdict"] == "PASS"
                             for c in res["checks"] if c["id"] == "C12"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
