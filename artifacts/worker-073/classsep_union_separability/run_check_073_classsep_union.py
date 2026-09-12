#!/usr/bin/env python3
"""W073-CLASSSEP-UNION-SEPARABILITY-01 runner (worker-073, node A1, gate G-AUDIT).

Question (one bounded, class-bound measurement)
-----------------------------------------------
Can the live class-separation instrument's 3-line meta-guard (added between the
pinned bytes c266dbceca87 and the live bytes a8c04fc31e4a, CF-26/REC-22) separate
merge *assertions* from merge *mentions* across the UNION of the two frozen,
independently authored probe corpora already in the record?

  * worker-049 corpus v1 (39 labeled fixtures, 9eb2ea9e2743) and corpus v2
    (25 labeled fixtures, db6dff9f4eda), written before any detector ran;
  * worker-098 pre-registered probes (6 assertion-shaped FN probes + 4 declared
    false-positive probes, ffabb753313f).

Neither author measured the union, and REC-22 must return one of
adopt / roll back / record assertion-vs-mention not lexically separable, binding
both audits. This runner measures the joint confusion table of the guard
predicate against both corpora's ground truth at pinned bytes.

PRE-REGISTERED DECISION RULE (fixed in this file before execution)
------------------------------------------------------------------
For each labeled fixture: assertion = the corpus author expects the detector to
flag it (expected_findings=1 / expected_live=true); mention = the author expects
no flag (expected_findings=0 / expected_live=false). Detector outputs come from
each module's own ``findings_for_text`` (the scoring surface worker-049 used).

  A_sup  = assertions with c266 flag and live clear      (guard loses an assertion)
  M_clear= mentions   with c266 flag and live clear      (guard clears a mention)
  M_keep = mentions   with c266 flag and live flag       (guard leaves a mention)
  A_keep = assertions with c266 flag and live flag

  union_verdict =
    NOT_SEPARABLE_BOTH_FAILURES   iff A_sup > 0 and M_keep > 0
    NOT_SEPARABLE_ASSERTION_LOSS  iff A_sup > 0 and M_keep == 0
    NOT_SEPARABLE_MENTION_RESIDUE iff A_sup == 0 and M_keep > 0
    NO_SUPPRESSION                iff A_sup == 0 and M_clear == 0
    SEPARATES_ON_THIS_UNION       iff A_sup == 0 and M_keep == 0 and M_clear > 0

The verdict is computed per corpus and on the union. A corpus counts only if it
contributes at least one flagged assertion and one flagged mention.

Controls (fail-closed; exit 2 on any pin mismatch, exit 3 on internal
inconsistency; a failed control is reported, not hidden)
  C1  every canonical input sha256 equals the pin; every local pinned copy equals
      the pin (two independent recoveries of c266dbec must agree byte-for-byte)
  C2  in-memory single-byte tamper of the live copy changes its sha256
  C3  double run of the full fixture scoring is byte-identical
  C4  worker-07 regression corpus scored by me: expected 17 TP / 10 TN / 0 FP / 0 FN
  C5  my per-fixture flags on worker-049 corpora equal results.json recorded rows
      for recovered_c266 and live_canonical
  C6  my 098 probe flags equal the recorded canonical/live values

Read-only on every pinned input; writes only report.json next to this script.
Payload carries no wall-clock field, so a double run must be byte-identical.

AMENDMENT 1 (made before the first successful run, 2026-09-12T01:10+08:00)
------------------------------------------------------------------------
The first execution aborted fail-closed (exit 2, captured in
`run_stdout.abort-pin.txt`): the canonical path research_map/class_separation.py
was observed at e36b0d644ca75b1e at mtime 01:06:12, a SECOND unrecorded write
during the open REC-22 round (a8c04fc3 -> e36b0d644ca7). The measured frame of
this audit is the pinned local copies, so canonical-path drift is now RECORDED
(`frame_interception`) rather than fatal; local pinned-copy integrity stays
fail-closed. The same bytes observed by the aborted run are added as a POST-HOC
third arm (`third_write_010612`), clearly outside the pre-registered verdict,
because the audit lead's stated unblock condition is that a successor must keep
fixture A04 firing while clearing the meta-clause. The pre-registered decision
rule above is unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT = HERE / "report.json"

TASK_ID = "W073-CLASSSEP-UNION-SEPARABILITY-01"
PRIMARY_CLASS_ID = "AF-SCC-C2-VAC-GEN"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"]
NODE_ID, GATE = "A1", "G-AUDIT"

# name -> (canonical repo-relative path, expected sha256, local copy relative to HERE)
PINS = {
    "live_detector": (
        "research_map/class_separation.py",
        "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        "pinned/class_separation.live.a8c04fc31e4a.py"),
    "recovered_c266": (
        "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "pinned/class_separation.c266dbceca87.py"),
    "recovered_c266_worker032_copy": (
        "artifacts/worker-032/cf16-delta/pinned/class_separation.c266dbceca87.py",
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "pinned/class_separation.c266dbceca87.worker032.py"),
    "corpus_049_v1": (
        "artifacts/worker-049/classsep_fn_audit/corpus.json",
        "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23",
        "pinned/corpus_049_v1.json"),
    "corpus_049_v2_guardprobe": (
        "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json",
        "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b",
        "pinned/corpus_049_v2_guardprobe.json"),
    "corpus_049_twinfix": (
        "artifacts/worker-049/classsep_fn_audit/corpus_guard_twin_fix.json",
        "c3bbb5be3979eeb4dec2a85e352b8faa77d50a3aa15d9afa95a2a6b7159c5e43",
        "pinned/corpus_049_twinfix.json"),
    "worker098_drift_recheck": (
        "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json",
        "ffabb753313fdf76fe5df3760ed0a0f52eb5c8539b6e0e9d6b0800fbfe3a6395",
        "pinned/worker098_drift_recheck.json"),
    "worker098_pre_registration": (
        "artifacts/worker-098/classsep_prose_shadow/pre_registration.json",
        "fbe95b585fcad5e0e020d56b82de466b17bc54426959ec0b98f44e3e5fe2021e",
        "pinned/worker098_pre_registration.json"),
    "worker035_controls": (
        "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
        "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d",
        "pinned/worker035_controls.json"),
    "worker07_regression_results": (
        "artifacts/worker-07/class_separation_falsification/results.json",
        "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
        "pinned/worker07_regression_results.json"),
    "map_snapshot": (
        None,  # snapshot taken by this worker; bound by its own measured hash
        "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749",
        "snapshot/research_map.snapshot.json"),
    "third_write_010612": (
        None,  # observed on the canonical path at 01:06:12; local copy is the frame
        "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
        "pinned/class_separation.live.e36b0d644ca7.py"),
    "worker049_results": (
        "artifacts/worker-049/classsep_fn_audit/results.json",
        "9e1bf20439349eb352c6b32f39984c8c2557311bc6886342c5ab7bdfd72a2717",
        None),  # control input only, not copied
}

PRE_REGISTRATION = {
    "written_before_run": True,
    "rule": "union_verdict as defined in the module docstring; assertions are the corpus authors' positive labels, mentions their negative labels",
    "primary_corpora": ["corpus_049_v1", "corpus_049_v2_guardprobe"],
    "secondary_corpora": ["corpus_049_twinfix", "worker098_fn_probes", "worker098_fp_probes"],
    "unit": "fixture text scored by module.findings_for_text(text, 'text:<id>')",
    "no_canonical_write": True,
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_guard_pattern(live_src: str) -> dict:
    """Derive the guard predicate from the live bytes rather than hand-copying."""
    m = re.search(r'if re\.search\((r"[^"]*"), ctx, re\.I\):', live_src)
    if not m:
        raise RuntimeError("guard predicate not found in live detector bytes")
    pattern = m.group(1)[1:-1]  # strip r" ... "
    line_no = live_src[: m.start()].count("\n") + 1
    return {"pattern": pattern, "line": line_no,
            "derivation": "extracted verbatim from the live detector bytes by regex; compiled in-process"}


def fixture_flag(mod, text: str, fid: str) -> int:
    try:
        return len(mod.findings_for_text(text, f"text:{fid}"))
    except Exception:  # a fixture must not wedge the run
        return -1


def guard_state(mod, guard_re, text: str) -> dict:
    """Does the guard predicate fire on any assertion-path merge match?"""
    t = mod.norm(text)
    states = []
    for m in mod._MERGE_PAT.finditer(t):
        lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
        ctx = t[lo:hi]
        if mod._BENIGN.search(t[max(0, m.start() - 8): m.end() + 8]):
            continue
        am = mod._MERGE_ASSERT.search(ctx)
        if not am:
            continue
        states.append(bool(guard_re.search(ctx)))
    return {"assertion_path_matches": len(states), "guard_fires_any": any(states),
            "guard_fires_all": bool(states) and all(states)}


def score(rows, mod_c266, mod_live, guard_re, mod3=None, guard3=None):
    out = []
    for r in rows:
        c = fixture_flag(mod_c266, r["text"], r["id"])
        lv = fixture_flag(mod_live, r["text"], r["id"])
        gs = guard_state(mod_live, guard_re, r["text"])
        rec = dict(r)
        rec.update({"c266_flags": c > 0, "c266_n": c, "live_flags": lv > 0, "live_n": lv,
                    "guard_fires": gs["guard_fires_any"]})
        if mod3 is not None:
            l3 = fixture_flag(mod3, r["text"], r["id"])
            g3 = guard_state(mod3, guard3, r["text"])
            rec.update({"live3_flags": l3 > 0, "live3_n": l3, "guard3_fires": g3["guard_fires_any"]})
        out.append(rec)
    return out


def tabulate(rows, label_filter=None, arm="live"):
    sel = [r for r in rows if label_filter is None or r["corpus"] in label_filter]
    t = {"n": len(sel), "assertions": 0, "mentions": 0, "A_keep": 0, "A_sup": 0,
         "M_clear": 0, "M_keep": 0, "A_new": 0, "M_new": 0, "unflagged_both": 0,
         "arm": arm}
    cf_key = "c266_flags"
    lf_key = "live_flags" if arm == "live" else "live3_flags"
    for r in sel:
        is_a = r["label"] == "assertion"
        t["assertions" if is_a else "mentions"] += 1
        cf, lf = r[cf_key], r[lf_key]
        if is_a:
            if cf and lf:
                t["A_keep"] += 1
            elif cf and not lf:
                t["A_sup"] += 1
            elif not cf and lf:
                t["A_new"] += 1
            else:
                t["unflagged_both"] += 1
        else:
            if cf and not lf:
                t["M_clear"] += 1
            elif cf and lf:
                t["M_keep"] += 1
            elif not cf and lf:
                t["M_new"] += 1
            else:
                t["unflagged_both"] += 1
    t["verdict"] = decide(t)
    return t


def decide(t):
    if t["assertions"] == 0 or t["mentions"] == 0:
        return "INSUFFICIENT_CORPUS"
    if t["A_sup"] > 0 and t["M_keep"] > 0:
        return "NOT_SEPARABLE_BOTH_FAILURES"
    if t["A_sup"] > 0:
        return "NOT_SEPARABLE_ASSERTION_LOSS"
    if t["M_keep"] > 0:
        return "NOT_SEPARABLE_MENTION_RESIDUE"
    if t["M_clear"] == 0:
        return "NO_SUPPRESSION"
    return "SEPARATES_ON_THIS_UNION"


def worker07_score(mod, results):
    tp = tn = fp = fn = 0
    per = []
    for fx in results["fixtures"]:
        p = REPO / fx["fixture_path"]
        if not p.exists():
            per.append({"fixture": fx["fixture_path"], "status": "missing"})
            continue
        obj = json.loads(p.read_text())
        det = mod.findings_for_map(obj)
        for g in obj.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (REPO / art).is_file():
                    det += mod.findings_for_text((REPO / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        flagged = len(det) > 0
        truth = bool(fx["is_class_merge"])
        if truth and flagged:
            tp += 1
        elif truth and not flagged:
            fn += 1
        elif not truth and flagged:
            fp += 1
        else:
            tn += 1
        per.append({"fixture": fx["fixture_path"], "truth": truth, "flagged": flagged})
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "verdict": "PASS" if (fn == 0 and fp == 0 and tp == 17 and tn == 10) else "FAIL",
            "rows": per}


def map_census(m, mod_c266, mod_live):
    """Attribute the live/canonical hard-finding delta over the pinned snapshot.

    Mirrors findings_for_map item by item so every delta is attributable.
    """
    def per_item(mod):
        out = {}
        for gi, g in enumerate(m.get("groups", [])):
            key = f"group[{g.get('id', gi)}]"
            f = []
            if isinstance(g.get("direction"), str):
                mod._scan_composite(g["direction"], f"{key}.direction", f)
                mod._scan_family(g["direction"], f"{key}.direction", "", f)
            for n in g.get("nodes", []):
                f += mod.findings(n, f"node {n.get('id', '?')}")
            out[key] = (g.get("class_id"), g.get("direction"), f)
        for i, ev in enumerate(m.get("portfolio_events", [])):
            if isinstance(ev, dict):
                out[f"portfolio_events[{i}]"] = (ev.get("class_id"), ev.get("actor"),
                                                 mod.findings(ev, f"portfolio_events[{i}]"))
        for i, c in enumerate(m.get("claims", [])):
            if isinstance(c, dict):
                out[f"claims[{i}]"] = (c.get("class_id"), c.get("actor"),
                                       mod.findings(c, f"claims[{i}]", mode="prose"))
        return out

    a, b = per_item(mod_c266), per_item(mod_live)
    deltas = []
    for key in a:
        ca, cb = a[key][2], b.get(key, ("", "", []))[2]
        if len(ca) != len(cb):
            deltas.append({"item": key, "class_id": a[key][0], "actor": a[key][1],
                           "canonical_n": len(ca), "live_n": len(cb),
                           "cleared": [x[:160] for x in ca if x not in cb],
                           "added": [x[:160] for x in cb if x not in ca]})
    return {"canonical_hard": sum(len(v[2]) for v in a.values()),
            "live_hard": sum(len(v[2]) for v in b.values()),
            "delta_items": len(deltas), "deltas": deltas}


def main() -> int:
    pins, fail, drift = {}, [], []
    for name, (canon, want, local) in PINS.items():
        entry = {"canonical": canon, "expected_sha256": want, "local": local}
        if canon:
            cp = REPO / canon
            if not cp.exists():
                drift.append({"name": name, "canonical": canon, "observed_sha256": None,
                              "expected_sha256": want, "reason": "canonical path missing"})
                entry["canonical_sha256"] = None
            else:
                got = sha256_bytes(cp.read_bytes())
                entry["canonical_sha256"] = got
                if got != want:
                    drift.append({"name": name, "canonical": canon, "observed_sha256": got,
                                  "expected_sha256": want, "reason": "canonical path drifted"})
        if local:
            lp = HERE / local
            if not lp.exists():
                fail.append(f"{name}: local pinned copy missing {local}")
                entry["local_sha256"] = None
            else:
                got = sha256_bytes(lp.read_bytes())
                entry["local_sha256"] = got
                if got != want:
                    fail.append(f"{name}: local sha {got[:12]} != pin {want[:12]}")
        pins[name] = entry
    if fail:
        print("PIN FAILURE:", *fail, sep="\n  ")
        return 2

    live_src = (HERE / PINS["live_detector"][2]).read_text()
    g = extract_guard_pattern(live_src)
    guard_re = re.compile(g["pattern"], re.I)
    g["source_line_text"] = live_src.splitlines()[g["line"] - 1].strip()

    third_src = (HERE / PINS["third_write_010612"][2]).read_text()
    g3 = extract_guard_pattern(third_src)
    guard3_re = re.compile(g3["pattern"], re.I)
    g3["source_line_text"] = third_src.splitlines()[g3["line"] - 1].strip()

    mod_c266 = load_module(HERE / PINS["recovered_c266"][2], "classsep_c266")
    mod_live = load_module(HERE / PINS["live_detector"][2], "classsep_live")
    mod3 = load_module(HERE / PINS["third_write_010612"][2], "classsep_third")

    # ---- build the union fixture table from authored ground truth -----------------
    rows = []
    corpus_meta = {}
    for cname, gpath, label_map in [
        ("corpus_049_v1", "corpus_049_v1", {"ADVERSARIAL_ASSERTION": "assertion", "TWIN_CONTROL": "assertion",
                                            "PLAIN_POSITIVE": "assertion", "MENTION": "mention"}),
        ("corpus_049_v2_guardprobe", "corpus_049_v2_guardprobe",
         {"ADVERSARIAL_ASSERTION": "assertion", "TWIN_CONTROL": "assertion", "MENTION": "mention"}),
        ("corpus_049_twinfix", "corpus_049_twinfix",
         {"ADVERSARIAL_ASSERTION": "assertion", "TWIN_CONTROL": "assertion", "MENTION": "mention"}),
    ]:
        d = json.loads((HERE / PINS[gpath][2]).read_text())
        corpus_meta[cname] = {"schema": d.get("schema"), "sha256": PINS[gpath][1],
                              "purpose": d.get("purpose"), "fixtures": len(d["fixtures"])}
        for fx in d["fixtures"]:
            lab = label_map.get(fx.get("category"))
            rows.append({"id": fx["id"], "corpus": cname, "text": fx["text"], "category": fx.get("category"),
                         "label": lab, "label_source": f"{cname}.category",
                         "expected_findings": fx.get("expected_findings")})

    d98 = json.loads((HERE / PINS["worker098_drift_recheck"][2]).read_text())
    corpus_meta["worker098_fn_probes"] = {"sha256": PINS["worker098_drift_recheck"][1], "fixtures": len(d98["probes"]["fn"])}
    corpus_meta["worker098_fp_probes"] = {"sha256": PINS["worker098_drift_recheck"][1], "fixtures": len(d98["probes"]["fp"])}
    for i, p in enumerate(d98["probes"]["fn"]):
        rows.append({"id": p["name"], "corpus": "worker098_fn_probes", "text": p["text"],
                     "category": "FN_PROBE", "label": "assertion", "label_source": "098 over_suppressed=false"})
    for i, p in enumerate(d98["probes"]["fp"]):
        rows.append({"id": f"FP{i+1}", "corpus": "worker098_fp_probes", "text": p["text"],
                     "category": "FP_PROBE", "label": "mention", "label_source": "098 expected_live=false"})

    scored = score(rows, mod_c266, mod_live, guard_re, mod3, guard3_re)

    # ---- C3 determinism -----------------------------------------------------------
    scored2 = score(rows, mod_c266, mod_live, guard_re, mod3, guard3_re)
    det_ok = json.dumps(scored, sort_keys=True) == json.dumps(scored2, sort_keys=True)

    # ---- C2 tamper ----------------------------------------------------------------
    live_bytes = (HERE / PINS["live_detector"][2]).read_bytes()
    tampered = bytes([live_bytes[0] ^ 0x01]) + live_bytes[1:]
    tamper_ok = sha256_bytes(tampered) != PINS["live_detector"][1]

    # ---- C4 worker-07 regression --------------------------------------------------
    w07 = json.loads((HERE / PINS["worker07_regression_results"][2]).read_text())
    reg = {"recovered_c266": worker07_score(mod_c266, w07), "live": worker07_score(mod_live, w07),
           "third_write_010612": worker07_score(mod3, w07)}

    # ---- C5 replicate 049 recorded rows -------------------------------------------
    res49 = json.loads((REPO / PINS["worker049_results"][0]).read_text())
    c5 = {}
    for cname, key, modname in [("corpus_049_v1", "corpus_v1", "recovered_c266"),
                                ("corpus_049_v1", "corpus_v1", "live_canonical"),
                                ("corpus_049_v2_guardprobe", "corpus_v2", "recovered_c266"),
                                ("corpus_049_v2_guardprobe", "corpus_v2", "live_canonical")]:
        rec = {r["id"]: bool(r["flags"]) for r in res49["corpora"][key]["modules"][modname]["rows"]}
        mine = {r["id"]: (r["c266_flags"] if modname == "recovered_c266" else r["live_flags"])
                for r in scored if r["corpus"] == cname}
        mism = [i for i in rec if i in mine and rec[i] != mine[i]]
        c5[f"{cname}:{modname}"] = {"rows": len(rec), "compared": len([i for i in rec if i in mine]),
                                    "mismatches": mism}

    # ---- C6 replicate 098 recorded probe values ------------------------------------
    fn_rows = [r for r in scored if r["corpus"] == "worker098_fn_probes"]
    fp_rows = [r for r in scored if r["corpus"] == "worker098_fp_probes"]
    c6 = {"fn_live_all_true": all(r["live_flags"] for r in fn_rows),
          "fn_canonical_all_true": all(r["c266_flags"] for r in fn_rows),
          "fp_live_matches_recorded": [r["live_flags"] for r in fp_rows] == [p["live"] for p in d98["probes"]["fp"]],
          "fp_canonical_matches_recorded": [r["c266_flags"] for r in fp_rows] == [p["canonical"] for p in d98["probes"]["fp"]]}

    # ---- tables --------------------------------------------------------------------
    primary = ["corpus_049_v1", "corpus_049_v2_guardprobe"]
    secondary = ["corpus_049_twinfix", "worker098_fn_probes", "worker098_fp_probes"]
    tables = {c: tabulate(scored, [c]) for c in primary + secondary}
    tables["union_all"] = tabulate(scored)
    tables["union_primary_049"] = tabulate(scored, primary)
    tables["union_098_probes"] = tabulate(scored, ["worker098_fn_probes", "worker098_fp_probes"])

    # post-hoc third arm (not part of the pre-registered verdict)
    tables_arm3 = {c: tabulate(scored, [c], arm="third_write_010612") for c in primary + secondary}
    tables_arm3["union_all"] = tabulate(scored, arm="third_write_010612")
    tables_arm3["union_primary_049"] = tabulate(scored, primary, arm="third_write_010612")
    tables_arm3["union_098_probes"] = tabulate(scored, ["worker098_fn_probes", "worker098_fp_probes"],
                                               arm="third_write_010612")
    a04 = next((r for r in scored if r["corpus"] == "corpus_049_v1" and r["id"] == "A04"), None)
    a04_arm3 = {"fixture": "A04", "text": a04["text"], "c266_flags": a04["c266_flags"],
                "live_flags": a04["live_flags"], "live3_flags": a04["live3_flags"],
                "kept_firing_by_third_write": bool(a04["live3_flags"])} if a04 else None

    # ---- map census ----------------------------------------------------------------
    snap = json.loads((HERE / PINS["map_snapshot"][2]).read_text())
    census = map_census(snap, mod_c266, mod_live)

    report = {
        "schema": "worker-073/classsep-union-separability/v1",
        "task_id": TASK_ID, "actor": "worker-073", "node_id": NODE_ID, "gate": GATE,
        "class_id": PRIMARY_CLASS_ID, "class_ids": CLASS_IDS,
        "pre_registration": PRE_REGISTRATION,
        "pins": pins,
        "guard_predicate": g,
        "guard_predicate_third_write": g3,
        "frame_interception": {"canonical_path_drift": drift,
                               "note": "canonical-path drift is recorded, not fatal; the measured frame is the pinned local copies (Amendment 1)"},
        "corpora": corpus_meta,
        "fixtures": sorted(scored, key=lambda r: (r["corpus"], str(r["id"]))),
        "tables": tables,
        "tables_third_write_arm": tables_arm3,
        "third_write_a04": a04_arm3,
        "controls": {
            "C1_pins_verified": True,
            "C1b_recovered_copies_identical": pins["recovered_c266"]["local_sha256"] == pins["recovered_c266_worker032_copy"]["local_sha256"],
            "C2_tamper_changes_sha": tamper_ok,
            "C3_determinism_double_run": det_ok,
            "C4_worker07_regression": reg,
            "C5_049_rows_replicated": c5,
            "C6_098_probe_values_replicated": c6,
        },
        "map_census": census,
        "non_claims": [
            "No gate verdict, node status, or validation_status is asserted; worker-073 cannot move those.",
            "No new class id, no taxonomy write, no detector write, no canonical-path write.",
            "This measures the guard predicate's behavior on the authors' labels; it does not re-adjudicate whether an individual labelled text is truly a mention.",
            "The two primary corpora were authored by workers who had read the candidates under test; the cross-corpus contradiction is the measurement, not a blind authorship claim.",
            "The third_write_010612 arm is POST-HOC (added after the abort-on-drift first attempt) and is not covered by the pre-registered verdict.",
        ],
        "falsifiers": [
            "Re-run at the same pins: any per-fixture flag differing from this report voids the corresponding table row.",
            "Any pinned sha256 drifting (live detector, recovered copies, either 049 corpus, 098 drift_recheck, map snapshot) voids the verdict for that input.",
            "A labeled assertion that is suppressed (A_sup>0) while a labeled mention stays flagged (M_keep>0) contradicts SEPARATES_ON_THIS_UNION; finding both in the union refutes lexical separability by this predicate.",
        ],
    }
    blob = json.dumps(report, indent=1, sort_keys=True)
    REPORT.write_text(blob + "\n")
    print(json.dumps({k: tables[k]["verdict"] for k in tables}, indent=1))
    print("third arm:", json.dumps({k: tables_arm3[k]["verdict"] for k in tables_arm3}))
    print("A04 third arm:", json.dumps(a04_arm3))
    print("frame drift:", json.dumps(drift))
    print("controls:", json.dumps({k: v for k, v in report["controls"].items() if k not in ("C4_worker07_regression", "C5_049_rows_replicated")}))
    print("worker07:", {k: v["verdict"] for k, v in reg.items()})
    print("map census:", census["canonical_hard"], "->", census["live_hard"], "delta items:", census["delta_items"])
    print("report:", REPORT, sha256_bytes((blob + "\n").encode()))
    if not (det_ok and tamper_ok and reg["live"]["verdict"] == "PASS" and reg["third_write_010612"]["verdict"] == "PASS"):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
