#!/usr/bin/env python3
"""W16-REV14-LANDING-FORENSICS-01 — independent read-only verification of the
rev14 / FROZEN rev30 fold landing (successor to W16-REC36-FOLD-INDEP-01).

Object under measurement:
  * runtime/state/controller_verification/astra-lifecycle-08-decisions.json#REC-36
    (the authorized fold list, 7 items, deadline 02:15)
  * the live formulation bytes: the rev14 fold moved 8 FROZEN-pinned files at
    2026-09-12T01:25:42+08:00 while artifacts/formulation/FROZEN.json still
    declared revision 29 (frozen_at 00:57:26).

The instrument is READ-ONLY on every canonical path; it writes only inside its
own artifact directory.  It never executes artifacts/formulation/tools/run_acceptance.py
(that tool regenerates pinned evidence, i.e. a canonical write); the acceptance
item is measured from pinned bytes and pinned tool source.

Exit codes: 0 VALID, 2 PIN DRIFT DURING RUN (re-read), 3 FROZEN-vs-LIVE MISMATCH
(freeze inconsistency), 4 internal control failure.
"""
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

FROZEN = "artifacts/formulation/FROZEN.json"
F1 = "schemas/af_wcc_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
F1M = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F2AM = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F2BM = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
VREG = "artifacts/formulation/VARIANT_REGISTRY.json"
SETDELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CHECKVREG = "artifacts/formulation/tools/check_variant_registry.py"
RUNACC = "artifacts/formulation/tools/run_acceptance.py"
ACCREP = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
SEMESC = "artifacts/formulation/evidence/semantic_escape_rebased.json"
F1SUITE = "schemas/f1_falsifier_tests.jsonl"
W029 = "artifacts/worker-029/f1_suite_materiality/report.json"
DECISIONS = "runtime/state/controller_verification/astra-lifecycle-08-decisions.json"
EVENTS = "research_map/events.jsonl"
LEADOUT = "comms/outbox/astra-lead-formulation.jsonl"

# The 8 FROZEN rev29 pins observed stale at T0 (live measured 2026-09-12T01:25:42+08:00).
MOVED_AT = "2026-09-12T01:25:42+08:00"
MOVED = [F2B, F2BM, F2A, F2AM, VREG, SETDELTA, F1SUITE, CHECKVREG]

CARRIER_152 = "No containment with C2 or C0 is asserted here"
CARRIER_246_OLD = "strictly larger extension class"
CARRIER_246_NEW = "strictly stronger regularity requirement"
CARRIER_246_NEW_ALT = "C2 is a strictly stronger regularity requirement"

REC36_ITEMS = [
    ("E1", "F2b must_not_conflate[0] containment denial -> F2a-corrected nested-extension wording"),
    ("E2", "F2b 'C2 is a strictly larger extension class' -> 'C2 is a strictly stronger regularity requirement (E_C2 subset E_C0)'"),
    ("E3", "F2a extension-manifold category pinned or a pinned category-independence rebuttal"),
    ("E4", "per REC-37 the scc_* canonical / strong_* alias crosswalk + assertion-correct consistency check"),
    ("E5", "SET predicate-vs-class strength label in VARIANT_REGISTRY.json + SET delta + check_variant_registry.py"),
    ("E6", "f1_falsifier_tests.jsonl rebind of 25 rows + F1-AMB-25 f0 pin + re-observation of F1-AMB-11/17/23 (worker-029 e95e0908a864)"),
    ("E7", "acceptance-corpus rebind (CF-32)"),
]


def p(rel):
    return os.path.join(ROOT, rel)


def sha256_path(rel):
    h = hashlib.sha256()
    with open(p(rel), "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def read(rel, text=True):
    with open(p(rel), "r" if text else "rb", encoding=None if not text else "utf-8", errors=None if not text else "replace") as f:
        return f.read()


def exists(rel):
    return os.path.exists(p(rel))


def mtime(rel):
    return os.path.getmtime(p(rel))


def main(stamp):
    out = {"task_id": "W16-REV14-LANDING-FORENSICS-01", "actor": "worker-016",
           "generated_at": stamp,
           "authority": ("worker read-only measurement; no gate verdict, no node status, "
                         "no validation_status, no canonical write, no repair adopted"),
           "instrument_sha256": sha256_path(os.path.relpath(os.path.abspath(__file__), ROOT))}

    # ---------------------------------------------------------------- T0 pins
    watched = [FROZEN, F1, F1M, F2A, F2AM, F2B, F2BM, F0, VOCAB, VREG, SETDELTA, CHECKVREG,
               RUNACC, ACCREP, SEMESC, F1SUITE, W029, DECISIONS]
    t0 = {rel: (sha256_path(rel) if exists(rel) else None) for rel in watched}
    t0_mtime = {rel: (mtime(rel) if exists(rel) else None) for rel in watched}
    out["pins_t0"] = {rel: {"sha256": t0[rel], "mtime": t0_mtime[rel]} for rel in watched}

    # ---------------------------------------------- A. FROZEN declared vs live
    frozen = json.loads(read(FROZEN))
    declared = frozen["files"]
    frozen_rows, mismatches = [], []
    for rel, v in declared.items():
        d = v.get("sha256") if isinstance(v, dict) else v
        live = sha256_path(rel) if exists(rel) else None
        ok = live is not None and str(live).startswith(str(d)[:12])
        frozen_rows.append({"path": rel, "declared": d, "measured": live, "match": ok})
        if not ok:
            mismatches.append({"path": rel, "declared": str(d)[:12],
                               "measured": (live or "")[:12],
                               "mtime": t0_mtime.get(rel)})
    out["A_freeze_state"] = {
        "frozen_path": FROZEN, "frozen_revision": frozen.get("revision"),
        "frozen_frozen_at": frozen.get("frozen_at"), "frozen_sha256": t0[FROZEN],
        "frozen_pins_total": len(frozen_rows), "frozen_pins_mismatch_count": len(mismatches),
        "frozen_pins_mismatch": mismatches,
        "live_moved_at_claim": MOVED_AT,
        "verdict": ("FREEZE_INCONSISTENT" if mismatches else "FREEZE_CONSISTENT"),
    }

    # ---------------------------------------------- B. landed-content checks
    f2b, f2a, vreg, setdelta, chk = read(F2B), read(F2A), read(VREG), read(SETDELTA), read(CHK)
    items = {}

    # E1 scoped to the must_not_conflate list block containing the repaired wording (line ~152)
    denial_scoped = CARRIER_152 in f2b and "[R2 major: the earlier" not in f2b
    denial_mentions = f2b.count(CARRIER_152)
    nested_wording = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in f2b
    items["E1"] = {"item": REC36_ITEMS[0][1], "old_denial_live_assertions": 0 if not denial_scoped else 1,
                   "old_denial_file_mentions": denial_mentions,
                   "nested_extension_wording_present": nested_wording,
                   "state": "CLOSED" if (not denial_scoped and nested_wording) else "OPEN"}

    # E2 scoped: live reason rows must not invert; whole-file mentions counted separately
    reason_rows = [l for l in f2b.splitlines() if "forbidden_transfers" not in l and "reason:" in l]
    live_reason = None
    ft_block = f2b.split("forbidden_transfers:", 1)[1].split("cross_family:", 1)[0] if "forbidden_transfers:" in f2b else ""
    for line in ft_block.splitlines():
        if "reason:" in line:
            live_reason = line.strip()
            break
    items["E2"] = {"item": REC36_ITEMS[1][1],
                   "forbidden_transfers_0_reason": (live_reason or "")[:220],
                   "old_inverted_phrase_in_live_reason": bool(live_reason and CARRIER_246_OLD in live_reason),
                   "new_wording_in_live_reason": bool(live_reason and CARRIER_246_NEW in live_reason),
                   "old_phrase_whole_file_mentions": f2b.count(CARRIER_246_OLD),
                   "state": "CLOSED" if (live_reason and CARRIER_246_NEW in live_reason
                                         and CARRIER_246_OLD not in live_reason) else "OPEN"}

    # E3 extension category pin
    ext_line = next((l.strip() for l in f2a.splitlines() if l.strip().startswith("extension_topology:")), "")
    cat_forbidden = bool(re.search(r"assuming a manifold category other than smooth", f2a))
    iota_present = bool(re.search(r"iota_regularity", f2a))
    items["E3"] = {"item": REC36_ITEMS[2][1],
                   "extension_topology_pins_smooth": ("SMOOTH" in ext_line.upper() and "PINNED" in ext_line.upper()),
                   "category_assumption_in_forbidden": cat_forbidden,
                   "iota_regularity_slot_present": iota_present,
                   "residual": None if iota_present else "HF-047 iota_regularity sub-field not addressed by the landed item",
                   "state": "CLOSED" if ("SMOOTH" in ext_line.upper() and cat_forbidden) else "OPEN"}

    # E4 token crosswalk state
    f0_allowed, canonical, schema_ct = [], [], {}
    try:
        import yaml  # type: ignore
        f0y = yaml.safe_load(read(F0))
        f0_allowed = list((((f0y.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed")) or [])
    except Exception:
        pass
    va = json.loads(read(VOCAB)).get("conclusion_type") or {}
    if isinstance(va, dict):
        canonical = [v.get("canonical") if isinstance(v, dict) else v for v in va.values()]
        canonical = [c for c in canonical if c]
    for key, rel in (("F1", F1), ("F2a", F2A), ("F2b", F2B)):
        m = re.search(r"conclusion_type:\s*([A-Za-z0-9_]+)", read(rel))
        schema_ct[key] = m.group(1) if m else None
    crosswalk = None
    for cand in ("artifacts/worker-047/rec37_token_crosswalk/crosswalk.json",
                 "artifacts/formulation/TOKEN_CROSSWALK.json"):
        if exists(cand):
            crosswalk = {"path": cand, "sha256": sha256_path(cand)}
            break
    items["E4"] = {"item": REC36_ITEMS[3][1], "f0_allowed": f0_allowed, "vocab_canonical": canonical,
                   "schema_conclusion_type": schema_ct, "crosswalk_artifact": crosswalk,
                   "state": "MEASURED_CROSSWALK_ARTIFACT_PRESENT" if crosswalk else "OPEN_OR_EXTERNAL"}

    # E5 SET level label + checker
    reg_level = "LEVEL-QUALIFIED" in vreg
    delta_level = ("LEVEL-QUALIFIED" in setdelta) or ("class-level" in setdelta and "predicate-level" in setdelta)
    chk_level_asserts = ("WEAKER" in chk and "STRONGER" in chk and "sset[pi:ci]" in chk)
    chk_old_vacuity_gone = "if \"STRONGER\" not in tw.get" not in chk
    items["E5"] = {"item": REC36_ITEMS[4][1], "registry_level_qualified": reg_level,
                   "set_delta_level_qualified": delta_level,
                   "checker_level_scoped_assertions": chk_level_asserts,
                   "checker_old_substring_test_gone": chk_old_vacuity_gone,
                   "state": "CLOSED" if (reg_level and delta_level and chk_level_asserts) else "PARTIAL"}

    # E6 falsifier rebind
    suite = [json.loads(l) for l in read(F1SUITE).splitlines() if l.strip()]
    live_f1 = t0[F1]
    bound = sum(1 for r in suite if str(r.get("binding_sha256", "")).startswith(live_f1[:12]))
    frozen_rev = sorted({r.get("binding_frozen_revision") for r in suite if r.get("binding_frozen_revision") is not None})
    items["E6"] = {"item": REC36_ITEMS[5][1], "row_count": len(suite), "rows_bound_to_live_f1": bound,
                   "binding_frozen_revisions": frozen_rev,
                   "worker029_report_present": exists(W029),
                   "worker029_report_sha256": sha256_path(W029) if exists(W029) else None,
                   "state": "CLOSED" if (suite and bound == len(suite)) else "OPEN"}

    # E7 acceptance corpus rebind
    semesc = json.loads(read(SEMESC))
    stated_base = str(semesc.get("base_sha256") or "")
    acc_ok = False
    try:
        acc = json.loads(read(ACCREP))
        acc_ok = json.dumps(acc)[:4000].find(stated_base[:12]) >= 0 or acc.get("canonical") == "3/3"
    except Exception:
        pass
    items["E7"] = {"item": REC36_ITEMS[6][1], "semantic_escape_base_sha256": stated_base[:16],
                   "live_c0_sha256": t0[F2B],
                   "base_stale_vs_live_c0": bool(stated_base and not t0[F2B].startswith(stated_base[:12])),
                   "acceptance_report_mentions_stale_base": acc_ok,
                   "run_acceptance_sha256_unchanged_since_rev29": t0[RUNACC] == (
                       (declared.get(RUNACC) or {}).get("sha256") if isinstance(declared.get(RUNACC), dict) else declared.get(RUNACC)),
                   "tool_not_executed_reason": "run_acceptance.py regenerates pinned evidence; execution would be a canonical write",
                   "state": "OPEN" if (stated_base and not t0[F2B].startswith(stated_base[:12])) else "CLOSED"}
    out["B_items"] = items

    # --------------------------------- C. announcement + mirror + clock checks
    moved_prefixes = [t0[r][:12] for r in MOVED if t0[r]]
    events, announced = [], []
    with open(p(EVENTS), encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            events.append(d)
            recv = str(d.get("_received_at") or "")
            s = json.dumps(d)
            if recv >= MOVED_AT and any(pre in s for pre in moved_prefixes):
                announced.append({"received_at": recv, "event_id": d.get("event_id"),
                                  "actor": d.get("actor"), "event_type": d.get("event_type")})
    out["C_announcement"] = {
        "moved_file_prefixes": moved_prefixes,
        "accepted_stream_events_naming_new_bytes_since_move": len(announced),
        "events": announced[:10],
        "announcement_state": "ANNOUNCED" if announced else "UNANNOUNCED_AT_MEASUREMENT",
    }
    out["C_mirror_alignment"] = {"F1": t0[F1] == t0[F1M], "F2a": t0[F2A] == t0[F2AM],
                                 "F2b": t0[F2B] == t0[F2BM]}
    hist = re.search(r'at: "([0-9T:+\-]+)", unused: false, notes: \["rev14 delta', f2b)
    out["C_clock_observation"] = {
        "rev14_revision_history_declared_at": hist.group(1) if hist else None,
        "wall_clock_at_measurement": stamp,
        "declared_ahead_of_wall_clock": bool(hist and hist.group(1) > stamp),
        "note": "CF-6/CF-14 clock-discipline pattern inside a frozen artifact; ordering uses _received_at",
    }

    # -------------------------------------------------------------- controls
    controls = []
    tmp = os.path.join(HERE, "_tmp_controls")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    controls.append({"id": "K1_missing_path", "pass": not exists("artifacts/worker-016/__no_such__.yaml")})
    hb = sha256_path(F2B)
    cp = os.path.join(tmp, "f2b.yaml")
    shutil.copyfile(p(F2B), cp)
    data = open(cp, "rb").read()
    open(cp, "wb").write(data.replace(b"containment", b"containmentx", 1))
    hm = hashlib.sha256(open(cp, "rb").read()).hexdigest()
    controls.append({"id": "K2_hash_sensitivity", "pass": hm != hb, "orig": hb[:16], "mut": hm[:16]})
    # K3 assertion-vs-mention discrimination (the E2 trap): naive whole-file test false-positives
    # on the revision_history mention; the scoped live-reason test must not.
    synth = ["must_not_conflate:", '  - "x"', "  forbidden_transfers:",
             '    - {from: "a", to: "b", reason: "C2 is a strictly stronger regularity requirement (E_C2 subset of E_C0)"}',
             "revision_history:", '  - {notes: ["corrected from \'C2 is a strictly larger extension class\'"]}']
    synth_txt = "\n".join(synth)
    naive = CARRIER_246_OLD in synth_txt
    blk = synth_txt.split("forbidden_transfers:", 1)[1].split("revision_history:", 1)[0]
    scoped = any(CARRIER_246_OLD in l for l in blk.splitlines() if "reason:" in l)
    controls.append({"id": "K3_assertion_vs_mention", "pass": naive and not scoped,
                     "naive_whole_file": naive, "scoped_live_reason": scoped})
    # K4 omission detector against REC-36 verbatim
    rec = json.dumps([r for r in json.loads(read(DECISIONS))["decisions"] if r["id"] == "REC-36"])
    om = {"must_not_conflate": "must_not_conflate" in rec, "strictly larger": "strictly larger" in rec,
          "extension-manifold": "extension-manifold" in rec, "crosswalk": "crosswalk" in rec,
          "check_variant_registry": "check_variant_registry" in rec,
          "f1_falsifier_tests": "f1_falsifier_tests" in rec, "acceptance-corpus": "acceptance-corpus" in rec}
    controls.append({"id": "K4_omission_detector", "pass": all(om.values()), "checks": om})
    # K5 decision-record reader: REC-36 must be present and name 7 items
    controls.append({"id": "K5_rec36_present", "pass": bool(rec) and rec.count("(") >= 7})
    shutil.rmtree(tmp, ignore_errors=True)
    out["controls"] = controls
    out["controls_all_pass"] = all(c["pass"] for c in controls)

    # ------------------------------------------------------------- T1 drift
    t1 = {rel: (sha256_path(rel) if exists(rel) else None) for rel in watched}
    drift = [rel for rel in watched if t0[rel] != t1[rel]]
    out["pins_t1"] = {rel: t1[rel] for rel in watched}
    out["drift"] = drift
    if drift:
        fz = json.loads(read(FROZEN))
        out["post_drift_frozen_revision"] = fz.get("revision")
        out["post_drift_frozen_sha256"] = sha256_path(FROZEN)

    out["falsifier"] = ("Re-run at the same pins: falsified if (a) a file this instrument reports as "
                        "moved is byte-identical to its FROZEN rev29 pin; (b) the FROZEN manifest at the "
                        "measurement instant declares a revision whose pins all match live bytes (then the "
                        "freeze state is consistent and section A is void); (c) an accepted-stream event "
                        "naming the new bytes exists at or before the measurement instant (then the "
                        "unannounced state is void); (d) the scoped live-reason detector and the naive "
                        "whole-file detector agree on the synthetic K3 fixture; (e) any control stops "
                        "discriminating.")
    out["open_items"] = sorted(k for k, v in items.items() if isinstance(v, dict) and v.get("state", "").startswith(("OPEN", "PARTIAL")))

    if mismatches:
        code = 3
    elif drift:
        code = 2
    elif not out["controls_all_pass"]:
        code = 4
    else:
        code = 0
    out["exit_code"] = code

    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "controls.json"), "w", encoding="utf-8") as f:
        json.dump({"controls": controls, "all_pass": out["controls_all_pass"]}, f, indent=1)
    ev = {k: out[k] for k in ("task_id", "generated_at", "A_freeze_state", "B_items",
                              "C_announcement", "C_mirror_alignment", "C_clock_observation",
                              "pins_t0", "pins_t1", "drift", "controls_all_pass",
                              "open_items", "exit_code")}
    with open(os.path.join(HERE, "evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=1, sort_keys=True)

    print(json.dumps({"exit_code": code,
                      "frozen_revision": out["A_freeze_state"]["frozen_revision"],
                      "frozen_mismatch_count": len(mismatches),
                      "mismatch_paths": [m["path"] for m in mismatches],
                      "open_items": out["open_items"],
                      "announcement": out["C_announcement"]["announcement_state"],
                      "mirror_alignment": out["C_mirror_alignment"],
                      "declared_ahead": out["C_clock_observation"]["declared_ahead_of_wall_clock"],
                      "drift": drift,
                      "controls_all_pass": out["controls_all_pass"]}, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "runtime"))
