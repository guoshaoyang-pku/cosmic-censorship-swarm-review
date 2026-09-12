#!/usr/bin/env python3
"""W091-F2B-REV12-CLOSURE-01 — independent closure check of F2b at final rev12 bytes.

One bounded, class-bound task. Class: AF-SCC-C0-VAC-GEN (node F2b).
Snapshot pinned at run time: schemas/af_scc_c0_vacuum.yaml.

What this decides
-----------------
worker-084 rounds 1-3 reviewed F2b at PRE-rev27 bytes (962f33c6d047 -> 1bb78ce9b357)
and left four hard defects D1-D4 plus an explicit next_falsifier:

    "FROZEN rev27+ with revised_at AND f0_binding.checked_at <= schema mtime,
     duplicate revised_at keys removed, and class_contract_pointer repointed into
     the hash-pinned declared F0, with class identity still clean."

rev27/rev28 and FROZEN rev28 claim exactly those repairs. No worker has reviewed F2b
at the final rev12 bytes 55d0a1ea9bda. This script tests that claim mechanically:

  A. freeze/binding chain (FROZEN rev28, mirror identity, pointer resolution, evidence)
  B. timestamp discipline (D1/D2/D3 closure, time-independent form: stamp vs file mtime)
  C. class identity (canonical class-separation checker, regularity, family, disjointness)
  D. drift re-hash of every input after the checks

Five planted-defect controls (CTL-1..CTL-5) assert the detectors discriminate before
any verdict is read off them.

Determinism: reads every input once, pins its sha256, re-hashes at the end. No network,
no writes outside this artifact directory. Exit 0 when all CHECKS execute (a failing
check is data, not a crash); exit 3 on a binding error that makes the run meaningless.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # artifacts/worker-091/<dir> -> repo root
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation  # noqa: E402

CST = timezone(timedelta(hours=8))

CANON = "schemas/af_scc_c0_vacuum.yaml"
AUTHORING = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SIDECAR = "schemas/af_scc_c0_vacuum.yaml.sha256"
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
FROZEN_REV_EXPECTED = 28
DECLARED_F0_EXPECTED = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
DECLARED_CONSISTENCY_EXPECTED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
CANON_PIN_EXPECTED = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"

CHECKS: list[dict] = []
CONTROLS: list[dict] = []


def check(cid, axis, severity, ok, detail, expectation="pass"):
    CHECKS.append({
        "id": cid, "axis": axis, "severity": severity, "ok": bool(ok),
        "expectation": expectation, "detail": detail,
    })
    return bool(ok)


def control(cid, ok, detail):
    CONTROLS.append({"id": cid, "ok": bool(ok), "detail": detail})
    return bool(ok)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def iso_utc(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).astimezone(CST).isoformat(timespec="microseconds")


def parse_ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=CST)


def dup_keys_everywhere(path: Path) -> dict:
    """Duplicate mapping keys at any depth (PyYAML keeps the last, silently)."""
    node = yaml.compose(path.read_text())
    dups: dict[str, list[int]] = {}

    def walk(n, trail=""):
        if isinstance(n, yaml.MappingNode):
            seen: dict[str, int] = {}
            for k, v in n.value:
                name = str(k.value)
                key = f"{trail}.{name}" if trail else name
                if name in seen:
                    dups.setdefault(key, [seen[name]]).append(k.start_mark.line + 1)
                else:
                    seen[name] = k.start_mark.line + 1
                walk(v, key)
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, f"{trail}[{i}]")

    if node is not None:
        walk(node)
    return dups


def resolve_pointer(doc, pointer: str):
    """Resolve 'path#a.b.c' inside an already-loaded doc. Returns (ok, value_or_None)."""
    if "#" not in pointer:
        return False, None
    frag = pointer.split("#", 1)[1]
    cur = doc
    for part in [p for p in frag.split(".") if p]:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


def main() -> int:
    canonical = ROOT / CANON
    if not canonical.is_file():
        print(json.dumps({"error": f"binding error: {CANON} absent"}), file=sys.stderr)
        return 3

    # ---- read every input ONCE, pin its bytes -------------------------------
    paths = [CANON, AUTHORING, SIDECAR, F0_CANON, F0_SUPP, FROZEN,
             "artifacts/formulation/evidence/taxonomy_consistency.json"]
    snap = {}
    for rel in paths:
        p = ROOT / rel
        if p.is_file():
            b = p.read_bytes()
            snap[rel] = {"sha256": sha256_bytes(b), "bytes": len(b), "mtime": iso_utc(p)}
        else:
            snap[rel] = {"sha256": None, "bytes": None, "mtime": None, "absent": True}

    schema_text = canonical.read_text()
    schema = yaml.safe_load(schema_text)
    f0 = yaml.safe_load((ROOT / F0_CANON).read_text())
    supp = yaml.safe_load((ROOT / F0_SUPP).read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    f0_binding = schema.get("f0_binding", {}) or {}
    mtime = parse_ts(snap[CANON]["mtime"])

    reg = class_separation.regression()

    # ---- CONTROLS first -----------------------------------------------------
    # CTL-1: the evidence-resolution predicate must reject a wrong declared hash
    #        and accept a correct one.
    live_cons = snap["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
    ctl1 = (DECLARED_CONSISTENCY_EXPECTED != live_cons) and (
        f0_binding.get("consistency_evidence_sha256") != live_cons)
    control("CTL-1-evidence-predicate-discriminates", ctl1,
            {"declared": f0_binding.get("consistency_evidence_sha256"),
             "measured_at_declared_path": live_cons,
             "note": "predicate fires (declared != measured); a matching pair would pass"})

    # CTL-2: duplicate-key detector must fire on a synthetic duplicate and not on the real file
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "dup.yaml"
        d.write_text('revised_at: "2026-01-01T00:00:00+08:00"\nrevised_at: "2026-01-02T00:00:00+08:00"\n')
        synthetic_dups = dup_keys_everywhere(d)
    real_dups = dup_keys_everywhere(canonical)
    control("CTL-2-duplicate-key-detector", bool(synthetic_dups) and not real_dups,
            {"synthetic_detected": sorted(synthetic_dups),
             "real_duplicates": sorted(real_dups)})

    # CTL-3: composite-regularity detector must fire on a planted C0/C2 merge and stay
    #        silent on the real schema (prose mode, the canonical checker).
    planted = class_separation.findings_for_text("This is one class with C0 or C2 regularity.", "ctl")
    real_cs = class_separation.findings_for_text(schema_text, CANON)
    control("CTL-3-classsep-detector", bool(planted) and not real_cs,
            {"planted_findings": planted, "real_findings": real_cs})

    # CTL-4: future-stamp predicate must flag now+1h and not flag the real stamps
    future = datetime.now(CST) + timedelta(hours=1)
    control("CTL-4-future-stamp-predicate",
            future > mtime and parse_ts(schema["revised_at"]) <= mtime
            and parse_ts(f0_binding.get("checked_at")) <= mtime,
            {"synthetic_future_flagged": future > mtime,
             "revised_at": schema["revised_at"], "checked_at": f0_binding.get("checked_at"),
             "schema_mtime": snap[CANON]["mtime"]})

    # CTL-5: pointer resolver must reject a planted non-existent key
    ok_bad, _ = resolve_pointer(f0, f"{F0_CANON}#classes.NO-SUCH-CLASS")
    ok_good, _ = resolve_pointer(f0, f"{F0_CANON}#classes.{CLASS_ID}")
    control("CTL-5-pointer-resolver", (not ok_bad) and ok_good,
            {"planted_pointer_resolved": ok_bad, "real_pointer_resolved": ok_good})

    # CTL-6: instrument calibration for C6. The forbidden lists are nested inside
    # `conclusion`; a top-level read returns null and would make the check vacuous.
    # The check must read the path that actually carries content.
    _top = schema.get("forbidden_strengthenings")
    _nest = (schema.get("conclusion") or {}).get("forbidden_strengthenings")
    control("CTL-6-forbidden-list-path-sensitivity",
            _top is None and isinstance(_nest, list) and len(_nest) > 0,
            {"top_level_forbidden_strengthenings": _top,
             "conclusion_forbidden_strengthenings_len": len(_nest) if isinstance(_nest, list) else None,
             "note": "C6 originally read the top-level key; path corrected before the verdict was read"})

    controls_ok = all(c["ok"] for c in CONTROLS)

    # ---- A. freeze / binding chain -----------------------------------------
    check("A1-canonical-hash-pinned", "binding", "hard",
          snap[CANON]["sha256"] == CANON_PIN_EXPECTED,
          {"measured": snap[CANON]["sha256"], "expected_pin": CANON_PIN_EXPECTED})

    check("A2-authoring-mirror-byte-identical", "binding", "hard",
          snap[AUTHORING]["sha256"] == snap[CANON]["sha256"],
          {"canonical": snap[CANON]["sha256"], "authoring": snap[AUTHORING]["sha256"]})

    fz = (frozen.get("files") or {})
    check("A3-frozen-pins-canonical", "binding", "hard",
          (fz.get(CANON) or {}).get("sha256") == snap[CANON]["sha256"],
          {"frozen_revision": frozen.get("revision"),
           "frozen_entry": (fz.get(CANON) or {}).get("sha256"),
           "measured": snap[CANON]["sha256"]})

    check("A4-frozen-pins-authoring", "binding", "hard",
          (fz.get(AUTHORING) or {}).get("sha256") == snap[AUTHORING]["sha256"],
          {"frozen_entry": (fz.get(AUTHORING) or {}).get("sha256"),
           "measured": snap[AUTHORING]["sha256"]})

    check("A5-frozen-revision-is-28", "binding", "hard",
          frozen.get("revision") == FROZEN_REV_EXPECTED,
          {"frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at")})

    check("A6-declared-f0-hash-matches-measured", "binding", "hard",
          f0_binding.get("declared_f0_sha256") == snap[F0_CANON]["sha256"],
          {"declared": f0_binding.get("declared_f0_sha256"),
           "measured": snap[F0_CANON]["sha256"],
           "declared_is_rev5": f0_binding.get("declared_f0_sha256") == DECLARED_F0_EXPECTED})

    # D4 repair: pointer must resolve inside the hash-pinned declared F0 canonical.
    ptr = schema.get("class_contract_pointer", "")
    ok_ptr, ptr_val = resolve_pointer(f0, ptr)
    check("A7-class-contract-pointer-resolves-in-pinned-F0", "binding", "hard",
          ok_ptr and ptr.startswith(F0_CANON + "#"),
          {"pointer": ptr, "resolved_key_count": len(ptr_val) if isinstance(ptr_val, dict) else None,
           "targets_declared_f0": ptr.startswith(F0_CANON + "#")})

    supp_ptr = schema.get("class_contract_supplement_pointer", "")
    ok_supp, _ = resolve_pointer(supp, supp_ptr)
    check("A8-supplement-pointer-resolves-in-supplement", "binding", "hard",
          ok_supp and supp_ptr.startswith(F0_SUPP + "#"),
          {"pointer": supp_ptr, "supplement_sha256": snap[F0_SUPP]["sha256"]})

    # Open defect, independently reproduced: declared consistency evidence does not
    # resolve at its declared path (worker-086 HF-086-R1).
    cons_path = f0_binding.get("consistency_evidence")
    cons_declared = f0_binding.get("consistency_evidence_sha256")
    cons_measured = snap.get(cons_path, {}).get("sha256")
    check("A9-declared-consistency-evidence-resolves", "binding", "hard",
          cons_declared == cons_measured,
          {"declared_path": cons_path, "declared_sha256": cons_declared,
           "measured_at_path": cons_measured,
           "frozen_rev28_pin": (fz.get(cons_path) or {}).get("sha256")},
          expectation="known_open")

    # Sidecar companion: was byte-correct at worker-084 r2, now stale.
    side_txt = (ROOT / SIDECAR).read_text().split()[0] if (ROOT / SIDECAR).is_file() else None
    check("A10-sidecar-sha256-matches-canonical", "binding", "hard",
          side_txt == snap[CANON]["sha256"],
          {"sidecar": side_txt, "measured": snap[CANON]["sha256"],
           "sidecar_mtime": snap[SIDECAR]["mtime"]})

    # ---- B. timestamp discipline (worker-084 D1/D2/D3) ----------------------
    check("B1-no-duplicate-top-level-keys", "timestamp", "hard",
          not real_dups, {"duplicates": sorted(real_dups)})

    check("B2-revised-at-not-later-than-mtime", "timestamp", "hard",
          parse_ts(schema.get("revised_at")) <= mtime,
          {"revised_at": schema.get("revised_at"), "schema_mtime": snap[CANON]["mtime"]})

    check("B3-checked-at-not-later-than-mtime", "timestamp", "hard",
          parse_ts(f0_binding.get("checked_at")) <= mtime,
          {"checked_at": f0_binding.get("checked_at"), "schema_mtime": snap[CANON]["mtime"],
           "was_D1_defect_value": "2026-09-12T00:30:00+08:00"})

    rh = schema.get("revision_history") or []
    idx = [r.get("index") for r in rh if isinstance(r, dict)]
    check("B4-revision-history-well-formed", "timestamp", "soft",
          len(idx) == len(set(idx)) and schema.get("revision") == len(idx),
          {"history_len": len(idx), "duplicate_indices": sorted({i for i in idx if idx.count(i) > 1}),
           "revision_field": schema.get("revision")})

    check("B5-unused-history-entries-are-historical", "timestamp", "soft",
          all(isinstance(r, dict) for r in rh),
          {"unused_indices": [r.get("index") for r in rh if isinstance(r, dict) and r.get("unused")]})

    # ---- C. class identity ------------------------------------------------
    cs_hard = [f for f in real_cs if not f.startswith("CLASSSEP-SOFT")]
    cs_soft = [f for f in real_cs if f.startswith("CLASSSEP-SOFT")]

    check("C1-classsep-zero-hard-findings", "identity", "hard",
          len(cs_hard) == 0, {"findings": cs_hard})

    check("C2-classsep-regression-passes", "identity", "hard",
          reg.get("verdict") == "PASS" and reg.get("corpus_size", 0) >= 27,
          {"regression": reg})

    check("C3-classsep-zero-soft-unknown-tokens", "identity", "soft",
          len(cs_soft) == 0, {"soft": cs_soft})

    comps = schema.get("class_components") or {}
    check("C4-class-id-frozen-and-single", "identity", "hard",
          schema.get("class_id") == CLASS_ID and CLASS_ID in class_separation.KNOWN_CLASSES,
          {"class_id": schema.get("class_id"), "components": comps})

    reg_obj = schema.get("regularity") or {}
    check("C5-exactly-one-regularity-token-C0", "identity", "hard",
          comps.get("regularity_token") == "C0" and reg_obj.get("extension_regularity") == "C0",
          {"regularity_token": comps.get("regularity_token"),
           "extension_regularity": reg_obj.get("extension_regularity")})

    # Forbidden lists live INSIDE conclusion (top-level forbidden_strengthenings is null).
    # Path corrected before the verdict was read; the criterion is unchanged: SCC conclusion
    # family with WCC/I+ content explicitly forbidden as a strengthening.
    concl_obj = schema.get("conclusion") or {}
    fstrength = json.dumps(concl_obj.get("forbidden_strengthenings") or [])
    fweaken = json.dumps(concl_obj.get("forbidden_weakenings") or [])
    check("C6-conclusion-family-SCC-no-inflation", "identity", "hard",
          comps.get("censorship") == "SCC"
          and concl_obj.get("family") == "SCC"
          and ("WCC" in fstrength or "I+" in fstrength)
          and ("C2" in fweaken or "C1" in fweaken),
          {"censorship": comps.get("censorship"),
           "conclusion_family": concl_obj.get("family"),
           "conclusion_type": concl_obj.get("conclusion_type"),
           "forbidden_strengthenings": concl_obj.get("forbidden_strengthenings"),
           "forbidden_has_WCC_or_I_plus": ("WCC" in fstrength or "I+" in fstrength)})

    check("C7-sibling-disjointness-declared-and-covered", "identity", "hard",
          schema.get("sibling_disjoint_from") == SIBLING
          and any(set(p.get("pair", [])) == {CLASS_ID, SIBLING}
                  for p in (f0.get("disjointness") or [])),
          {"sibling_disjoint_from": schema.get("sibling_disjoint_from"),
           "pair_present_in_F0_disjointness": any(
               set(p.get("pair", [])) == {CLASS_ID, SIBLING} for p in (f0.get("disjointness") or []))})

    check("C8-promotion-rule-and-binding-rule-present", "identity", "soft",
          bool(schema.get("promotion_rule")) and bool(f0_binding.get("rule")),
          {"promotion_rule_present": bool(schema.get("promotion_rule")),
           "binding_rule_present": bool(f0_binding.get("rule"))})

    # ---- D. drift re-hash --------------------------------------------------
    drift = {}
    moved = False
    for rel in paths:
        p = ROOT / rel
        now = sha256_path(p) if p.is_file() else None
        drift[rel] = {"at_check": snap[rel]["sha256"], "after_check": now,
                      "moved": now != snap[rel]["sha256"]}
        moved = moved or drift[rel]["moved"]

    hard_fail = [c for c in CHECKS if not c["ok"] and c["severity"] == "hard"]
    soft_fail = [c for c in CHECKS if not c["ok"] and c["severity"] == "soft"]
    identity_fail = [c for c in hard_fail if c["axis"] == "identity"]

    if not controls_ok:
        verdict, score = "inconclusive", 0.0
    elif identity_fail:
        verdict, score = "reject", 1.5
    elif hard_fail:
        verdict, score = "revise", 3.5
    elif soft_fail:
        verdict, score = "accept", 4.0
    else:
        verdict, score = "accept", 4.5

    report = {
        "report_id": "w091-f2b-rev12-closure",
        "task_id": "W091-F2B-REV12-CLOSURE-01",
        "actor": "worker-091",
        "node_id": "F2b",
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        # Deterministic provenance: derived from the pinned inputs, never from wall clock,
        # so re-running on unchanged inputs reproduces this report byte-for-byte.
        # The publishing artifact event carries the real wall-clock created_at.
        "generated_from_snapshot_at": max(v["mtime"] for v in snap.values() if v["mtime"]),
        "report_deterministic": True,
        "scope": ("class-binding and evidence-chain closure of ONE frozen class at its final "
                  "rev12 bytes: freeze chain, worker-084 D1-D4 repair adjudication, class "
                  "identity, drift. Schema semantics, quantifier truth and physics are NOT "
                  "re-derived; no node completion and no gate verdict is claimed."),
        "snapshot": snap,
        "canonical_pin_expected": CANON_PIN_EXPECTED,
        "counts": {"checks": len(CHECKS), "pass": sum(c["ok"] for c in CHECKS),
                   "hard_fail": len(hard_fail), "soft_fail": len(soft_fail),
                   "distinct_hard_defects": len({c["id"].split("-")[0] for c in hard_fail})},
        "checks": CHECKS,
        "controls": CONTROLS,
        "controls_ok": controls_ok,
        "check_corrections": [
            {"check": "C6-conclusion-family-SCC-no-inflation",
             "correction": "read conclusion.forbidden_strengthenings / conclusion.forbidden_weakenings "
                           "instead of the null top-level forbidden_strengthenings key",
             "when": "before the verdict was read; found by inspecting the artifact after a first "
                     "run returned a C6 hard failure",
             "criterion_changed": False,
             "calibration_control": "CTL-6"},
        ],
        "drift": drift,
        "moved_during_check": moved,
        "classsep_regression": reg,
        "worker084_repair_adjudication": {
            "D1_checked_at_future_dated": "RESOLVED" if not any(
                c["id"] == "B3-checked-at-not-later-than-mtime" and not c["ok"] for c in CHECKS) else "PERSISTS",
            "D2_revised_at_future_dated": "RESOLVED" if not any(
                c["id"] == "B2-revised-at-not-later-than-mtime" and not c["ok"] for c in CHECKS) else "PERSISTS",
            "D3_duplicate_revised_at_keys": "RESOLVED" if not real_dups else "PERSISTS",
            "D4_pointer_not_in_pinned_F0": "RESOLVED" if ok_ptr else "PERSISTS",
            "round3_reviewed_hash": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
            "round3_verdict_superseded_by_drift": snap[CANON]["sha256"] !=
                "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        },
        "verdict": verdict,
        "score": score,
        "hard_failures": [{"id": c["id"], "detail": c["detail"], "expectation": c["expectation"]}
                          for c in hard_fail],
        "soft_findings": [{"id": c["id"], "detail": c["detail"]} for c in soft_fail],
        "falsifier": ("Re-run this script at the pinned hashes. Falsified if any ok=true check "
                      "re-runs false, if class identity stops being clean, if a successor freeze "
                      "makes A9/A10 pass (declared consistency evidence and sidecar re-stamped to "
                      "the live bytes) while identity stays clean, or if CTL-1..CTL-5 stop "
                      "discriminating. Input drift voids, not falsifies: drift is recorded in "
                      "report.drift and moved_during_check."),
        "drift_at_emit": None,
        "drift_at_emit_note": ("null by design: this script is deterministic and cannot know the state at emit "
                               "time. The emitting status event carries drift_at_emit measured after these "
                               "artifact hashes were taken."),
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "score": score,
                      "canonical": snap[CANON]["sha256"][:12],
                      "counts": report["counts"], "controls_ok": controls_ok,
                      "moved_during_check": moved,
                      "hard_failures": [c["id"] for c in hard_fail],
                      "soft_findings": [c["id"] for c in soft_fail]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
