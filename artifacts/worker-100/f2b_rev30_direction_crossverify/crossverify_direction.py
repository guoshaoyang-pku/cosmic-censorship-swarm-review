#!/usr/bin/env python3
"""W100-F2B-REV30-DIRECTION-CROSSVERIFY-01 independent instrument.

Read-only on canonical paths. Reads only the pinned snapshots under ./pinned plus the
live target files (hash-checked against the declared pins). Writes only inside its own
artifact directory: report.json, run_record.txt, controls/.

Deterministic; stdlib + PyYAML only. Exit codes: 0 = verdict produced, 2 = INSTRUMENT_VOID.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

PINNED = os.path.join(HERE, "pinned")
CHECKER_NAME = "check_class_schema.000e09e46b2f.py"
CHECKER_PINNED = os.path.join(PINNED, CHECKER_NAME)
# The checker resolves its spec relative to __file__, so the live canonical tool is used;
# the pinned copy is hash-verified evidence only.
CHECKER = os.path.join(ROOT, "artifacts", "formulation", "tools", "check_class_schema.py")

SHARED_PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
}
TARGETS = {
    "base_84b5d3fa": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
        "sha256": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
        "snapshot": "cand084.84b5d3fa.yaml",
    },
    "cand080_corrected": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
        "sha256": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
        "snapshot": "cand080corrected.51c253c46306.yaml",
    },
    "cand080_nesting": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
        "sha256": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
        "snapshot": "cand080nesting.4951cc969803.yaml",
    },
    "cand023_v2": {
        "path": "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
        "sha256": "9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17",
        "snapshot": "cand023v2.9ab32ee39d00.yaml",
    },
}
CANON_SNAPSHOT = "canonical_f2b.rev13.b2ab6acb2bbe.yaml"
CHAIN_SUBSET = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
RANK = {"E_C0": 0, "E_H2loc": 1, "E_{C^1,1}": 2, "E_C2": 3}
SELF = "E_C0"
DIST = "E_C0DIST"

SKIP_KEYS = set()  # no key exclusions: the delta must be exact


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def leaf_delta(a, b):
    fa, fb = flatten(a), flatten(b)
    keys = sorted(set(fa) | set(fb))
    return {k: {"a": fa.get(k, "<<absent>>"), "b": fb.get(k, "<<absent>>")}
            for k in keys if fa.get(k, "<<absent>>") != fb.get(k, "<<absent>>")}


def strip_notes_and_quotes(s: str) -> str:
    """Remove [bracketed correction notes] and quoted spans; what remains is assertion text.

    Apostrophe-aware: a ' only opens a quoted span when preceded by whitespace/opening
    punctuation, so possessives (class's, conclusion's) are not mistaken for quote pairs.
    """
    s = re.sub(r"\[[^\]]*\]", " ", s)
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "'":
            prev = s[i - 1] if i > 0 else " "
            if prev in " \t([{\"'":
                j = s.find("'", i + 1)
                if j != -1:
                    i = j + 1
                    continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_inext(s):
    if not isinstance(s, str):
        return None
    t = s
    if "AF-WCC-VAC-GEN" in t or "AF-WCC" in t:
        return ("cross", None)
    if "distributional-vacuum" in t:
        return ("dist", DIST)
    if re.search(r"\bthis class\b", t):
        return ("self", SELF)
    if "H2_loc" in t:
        return ("tok", "E_H2loc")
    if "C^{1,1}" in t or "C1,1" in t:
        return ("tok", "E_{C^1,1}")
    if re.search(r"\bC2\b", t):
        return ("tok", "E_C2")
    if re.search(r"\bC0 metric\b", t) or re.search(r"\bC0\b", t):
        return ("tok", "E_C0")
    return None


def licensed(kind_from, tok_from, kind_to, tok_to, self_tok=SELF):
    if kind_from == "cross" or kind_to == "cross":
        return False
    if kind_to == "dist":
        return tok_from == self_tok or kind_from == "self"
    if kind_from == "self":
        tok_from = self_tok
    return RANK[tok_to] >= RANK[tok_from]


def unlicensed_direction_claims(stripped: str):
    """Claims of the form 'X-inextendibility ENTAILS this class' (or this class's conclusion)."""
    hits = []
    pat = re.compile(
        r"(H2_loc|C2|C\^\{1,1\})[-\s]?inextendibility\b[^.;]{0,90}?\b(?:ENTAILS|entails)\b([^.;]{0,90})",
        re.IGNORECASE)
    for m in pat.finditer(stripped):
        rest = m.group(2)
        pos = rest.find("this class")
        if pos < 0:
            continue
        before = rest[:pos]
        if re.search(r"\bnot\s+$", before) or re.search(r"\bnot\s+this\s*$", before):
            continue  # explicit prohibition, not a claim
        hits.append({"x": m.group(1), "text": m.group(0).strip()})
    return hits


def licensed_direction_claims(stripped: str):
    hits = []
    pat = re.compile(
        r"this class'?s?\s+conclusion[^.;]{0,70}?\b(?:ENTAILS|entails)\b[^.;]{0,70}?(H2_loc|C\^\{1,1\}|C2)",
        re.IGNORECASE)
    for m in pat.finditer(stripped):
        hits.append({"target": m.group(1), "text": m.group(0).strip()})
    return hits


def check_structure(data, label):
    """S1-S7 semantic/structural checks on parsed candidate data. Returns list of finding dicts."""
    f = []
    if not isinstance(data, dict):
        return [{"check": "S1_identity", "ok": False, "detail": "not a mapping"}]
    if data.get("class_id") != "AF-SCC-C0-VAC-GEN":
        f.append({"check": "S1_identity", "ok": False, "detail": f"class_id={data.get('class_id')!r}"})
    ct = (data.get("conclusion") or {}).get("conclusion_type")
    if ct != "scc_c0_future_inextendibility":
        f.append({"check": "S1_identity", "ok": False, "detail": f"conclusion_type={ct!r}"})
    reg = data.get("regularity") or {}
    mnc = reg.get("must_not_conflate") or []
    bullet = mnc[0] if mnc else ""
    stripped = strip_notes_and_quotes(bullet)
    # S2 chain
    if CHAIN_SUBSET not in bullet:
        f.append({"check": "S2_chain", "ok": False,
                  "detail": "required subset-form chain not present in must_not_conflate[0]"})
    # S3 denial assertion
    if re.search(r"no containment with c2 or c0 is asserted", stripped, re.IGNORECASE):
        f.append({"check": "S3_no_denial_assertion", "ok": False,
                  "detail": "unquoted denial 'no containment with C2 or C0 is asserted' present"})
    # S4 prohibited phrase use
    if "strictly between" in stripped:
        f.append({"check": "S4_no_prohibited_phrase_use", "ok": False,
                  "detail": "'strictly between' used as assertion (outside notes/quotes)"})
    # S5 unlicensed direction
    bad = unlicensed_direction_claims(stripped)
    if bad:
        f.append({"check": "S5_no_unlicensed_direction", "ok": False,
                  "detail": f"{len(bad)} unlicensed claim(s): " + "; ".join(h["text"] for h in bad)})
    # S6 direction coverage
    good = licensed_direction_claims(stripped)
    pointer = bool(re.search(r"direction of the induced entailments", bullet)) and \
        bool(re.search(r"implication_ledger", bullet))
    if not good and not pointer:
        f.append({"check": "S6_direction_coverage", "ok": False,
                  "detail": "no licensed positive direction statement and no explicit ledger direction pointer"})
    # S7 internal consistency
    led = data.get("implication_ledger") or {}
    ft = led.get("forbidden_transfers") or []
    r0 = (ft[0] or {}).get("reason", "") if ft else ""
    if not (re.search(r"strictly smaller", r0) and "E_C2 subset of E_C0" in r0
            and "larger" not in r0):
        f.append({"check": "S7_internal_consistency", "ok": False,
                  "detail": f"forbidden_transfers[0].reason not the corrected smaller-class form: {r0[:120]!r}"})
    flat = flatten(data)
    fw_paths = [p for p, v in flat.items()
                if isinstance(v, str) and "substituting H2_loc for C0" in v]
    if not fw_paths:
        f.append({"check": "S7_internal_consistency", "ok": False,
                  "detail": "forbidden_weakenings row 'substituting H2_loc for C0' absent"})
    else:
        fw = flat[fw_paths[0]]
        if "not this class" not in fw:
            f.append({"check": "S7_internal_consistency", "ok": False,
                      "detail": f"forbidden_weakenings row lacks 'not this class': {fw[:140]!r}"})
    if len(mnc) > 2 and "does not establish this class" not in (mnc[2] or ""):
        f.append({"check": "S7_internal_consistency", "ok": False,
                  "detail": "must_not_conflate[2] does not say C2-inextendibility 'does not establish this class'"})
    sub = led.get("subsumption_note", "") or ""
    if "never the reverse" not in sub:
        f.append({"check": "S7_internal_consistency", "ok": False,
                  "detail": "implication_ledger.subsumption_note lacks 'never the reverse'"})
    cont = led.get("extension_class_containment", "") or ""
    if not (re.search(r"STRONGEST", cont) and re.search(r"entails the others", cont)):
        f.append({"check": "S7_internal_consistency", "ok": False,
                  "detail": "extension_class_containment lacks STRONGEST/entails-the-others"})
    # ledger row direction adjudication
    for i, row in enumerate(led.get("one_way_entailments") or []):
        pf = parse_inext(row.get("from")); pt = parse_inext(row.get("to"))
        if not pf or not pt:
            f.append({"check": "S7_internal_consistency", "ok": False,
                      "detail": f"one_way_entailments[{i}] unparseable: {row}"})
            continue
        if not licensed(pf[0], pf[1], pt[0], pt[1]):
            f.append({"check": "S7_internal_consistency", "ok": False,
                      "detail": f"one_way_entailments[{i}] is not a licensed edge: {row.get('from')} -> {row.get('to')}"})
    for i, row in enumerate(ft):
        pf = parse_inext(row.get("from")); pt = parse_inext(row.get("to"))
        if not pf or not pt:
            f.append({"check": "S7_internal_consistency", "ok": False,
                      "detail": f"forbidden_transfers[{i}] unparseable: {row}"})
            continue
        if licensed(pf[0], pf[1], pt[0], pt[1]):
            f.append({"check": "S7_internal_consistency", "ok": False,
                      "detail": f"forbidden_transfers[{i}] is actually a licensed edge: {row.get('from')} -> {row.get('to')}"})
    return f


def run_gate(path: str):
    """Run the canonical structural checker; returns (ok, detail, method)."""
    attempts = [("direct", path)]
    tmp = None
    try:
        tmp = tempfile.mkdtemp(prefix="w100gate_", dir=os.path.join(HERE, "controls"))
        tdir = os.path.join(tmp, "schemas")
        os.makedirs(tdir, exist_ok=True)
        tcopy = os.path.join(tdir, "af_scc_c0_vacuum.yaml")
        with open(path, "rb") as src, open(tcopy, "wb") as dst:
            dst.write(src.read())
        attempts.append(("canonical_basename_copy", tcopy))
    except OSError:
        pass
    last = ""
    for method, p in attempts:
        try:
            r = subprocess.run([sys.executable, CHECKER, "--json", p],
                               capture_output=True, text=True, timeout=120)
        except Exception as e:  # pragma: no cover
            last = f"runner error: {e}"
            continue
        out = r.stdout.strip()
        try:
            j = json.loads(out[out.index("{"):])
        except Exception:
            last = f"non-JSON output (exit {r.returncode}): {(out or r.stderr)[:200]}"
            continue
        ok = r.returncode == 0 and j.get("verdict") == "pass" and not j.get("failed_rules")
        return ok, {"exit": r.returncode, "verdict": j.get("verdict"),
                    "failed_rules": j.get("failed_rules"), "method": method}, method
    return False, {"error": last}, "failed"


def main():
    rd = {"schema_version": "w100-crossverify-report/v1",
          "task_id": "W100-F2B-REV30-DIRECTION-CROSSVERIFY-01",
          "actor": "worker-100", "generated_at": NOW,
          "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
          "authority": "Worker measurement only. No canonical path written; no node status, no validation_status=passed, no gate verdict.",
          "instrument_sha256": sha256_file(os.path.abspath(__file__)),
          "preregistration_sha256": sha256_file(os.path.join(HERE, "preregistration.json")),
          "pins": {}, "targets": {}, "controls": {}, "verdict": None}

    # ---- shared pin verification -------------------------------------------------
    void = []
    for rel, want in SHARED_PINS.items():
        p = os.path.join(ROOT, rel)
        got = sha256_file(p) if os.path.exists(p) else "<<missing>>"
        rd["pins"][rel] = {"declared": want, "measured": got, "match": got == want}
        if got != want:
            void.append(rel)
    if not os.path.exists(CHECKER) or \
            sha256_file(CHECKER) != SHARED_PINS["artifacts/formulation/tools/check_class_schema.py"]:
        void.append("live checker")
    if not os.path.exists(CHECKER_PINNED) or \
            sha256_file(CHECKER_PINNED) != SHARED_PINS["artifacts/formulation/tools/check_class_schema.py"]:
        void.append("pinned checker copy")
    rd["shared_pins_ok"] = not void
    rd["shared_pin_failures"] = void
    if void:
        rd["verdict"] = "INSTRUMENT_VOID"
        emit(rd)
        return 2

    # ---- load canonical + base for deltas ---------------------------------------
    canon = yaml.safe_load(open(os.path.join(PINNED, CANON_SNAPSHOT)))
    base = yaml.safe_load(open(os.path.join(PINNED, TARGETS["base_84b5d3fa"]["snapshot"])))

    # ---- per-target checks -------------------------------------------------------
    for name, meta in TARGETS.items():
        live = os.path.join(ROOT, meta["path"])
        snap = os.path.join(PINNED, meta["snapshot"])
        live_hash = sha256_file(live) if os.path.exists(live) else "<<missing>>"
        stale = live_hash != meta["sha256"]
        rec = {"declared": meta["sha256"], "live_measured": live_hash, "stale": stale,
               "snapshot_sha256": sha256_file(snap)}
        data = yaml.safe_load(open(snap))
        findings = check_structure(data, name)
        rec["findings"] = findings
        mnc = ((data.get("regularity") or {}).get("must_not_conflate") or [""])[0]
        stripped = strip_notes_and_quotes(mnc)
        rec["metrics"] = {
            "bullet_len": len(mnc),
            "raw_old_denial_occurrences": len(re.findall(
                r"no containment with c2 or c0 is asserted", mnc, re.IGNORECASE)),
            "has_explicit_licensed_direction": bool(licensed_direction_claims(stripped)),
            "has_explicit_reverse_prohibition": bool(
                re.search(r"never the reverse", mnc) or re.search(r"not this class", mnc)),
            "has_R3_correction_record": "R3 major" in mnc,
            "has_ledger_direction_pointer": bool(
                re.search(r"direction of the induced entailments", mnc)) and
                bool(re.search(r"implication_ledger", mnc)),
        }
        # S8 gate
        if stale:
            rec["gate"] = {"ran": False, "reason": "target stale; not scored"}
            findings.append({"check": "S8_structural_gate", "ok": False, "detail": "target stale"})
        else:
            ok, det, _ = run_gate(snap)
            rec["gate"] = {"ran": True, "ok": ok, "detail": det}
            if not ok:
                findings.append({"check": "S8_structural_gate", "ok": False, "detail": json.dumps(det)})
        # S9/S10 deltas
        if data is not None and base is not None:
            d_base = leaf_delta(base, data)
            d_canon = leaf_delta(canon, data)
            rec["delta_vs_base"] = sorted(d_base.keys())
            rec["delta_vs_canonical"] = sorted(d_canon.keys())
            if name != "base_84b5d3fa" and rec["delta_vs_base"] != ["regularity.must_not_conflate[0]"]:
                findings.append({"check": "S9_delta_vs_base", "ok": False,
                                 "detail": f"delta={rec['delta_vs_base']}"})
            if name == "base_84b5d3fa":
                rec["delta_vs_base_note"] = "not applicable: target is the base"
            if rec["delta_vs_canonical"] != ["implication_ledger.forbidden_transfers[0].reason",
                                             "regularity.must_not_conflate[0]"]:
                findings.append({"check": "S10_delta_vs_canonical", "ok": False,
                                 "detail": f"delta={rec['delta_vs_canonical']}"})
        rec["clean"] = not findings
        rd["targets"][name] = rec

    # ---- controls -----------------------------------------------------------------
    ctrl = {}
    base_data = yaml.safe_load(open(os.path.join(PINNED, TARGETS["base_84b5d3fa"]["snapshot"])))
    v2 = yaml.safe_load(open(os.path.join(PINNED, TARGETS["cand023_v2"]["snapshot"])))
    nest = yaml.safe_load(open(os.path.join(PINNED, TARGETS["cand080_nesting"]["snapshot"])))
    canon_data = canon

    def mutate(d, fn):
        import copy
        c = copy.deepcopy(d)
        fn(c)
        return c

    def bullet_mut(text_pairs):
        def fn(d):
            b = d["regularity"]["must_not_conflate"][0]
            for old, new in text_pairs:
                assert old in b, f"mutation anchor missing: {old[:40]}"
                b = b.replace(old, new)
            d["regularity"]["must_not_conflate"][0] = b
        return fn

    def ledger_mut(fn):
        def f(d):
            fn(d["implication_ledger"])
        return f

    POS = "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse"
    cases = {}
    cases["M1_reinvert_023v2"] = (mutate(v2, bullet_mut([(POS, "so H2_loc-inextendibility ENTAILS this class's conclusion, never the reverse")])),
                                  "S5_no_unlicensed_direction")
    cases["M2_drop_direction_023v2"] = (mutate(v2, bullet_mut([(POS, ""), (" (see implication_ledger)", "")])),
                                        "S6_direction_coverage")
    cases["M3_larger_reason"] = (mutate(v2, ledger_mut(
        lambda L: L["forbidden_transfers"][0].__setitem__("reason", "C2 is a strictly larger extension class"))),
        "S7_internal_consistency")
    def drop_fw(d):
        fws = d["conclusion"]["forbidden_weakenings"]
        d["conclusion"]["forbidden_weakenings"] = [x for x in fws if "substituting H2_loc for C0" not in x]
    cases["M4_drop_forbidden_weakenings"] = (mutate(v2, drop_fw), "S7_internal_consistency")
    cases["M5_invert_chain"] = (mutate(v2, bullet_mut(
        [(CHAIN_SUBSET, "E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2")])), "S2_chain")
    cases["M6_unquoted_denial"] = (mutate(v2, bullet_mut(
        [("never the reverse;", "never the reverse; no containment with C2 or C0 is asserted here;")])),
        "S3_no_denial_assertion")
    cases["M7_identity_023v2"] = (mutate(v2, lambda d: None), None)  # all must pass
    def drop_nest_pointer(d):
        b = d["regularity"]["must_not_conflate"][0]
        seg = "the direction of the induced entailments among the corresponding inextendibility statements is recorded there"
        assert seg in b
        d["regularity"]["must_not_conflate"][0] = b.replace(seg, "")
    cases["M8_nesting_pointer_removed"] = (mutate(nest, drop_nest_pointer), "S6_direction_coverage")

    for name, (data, expect) in cases.items():
        f = check_structure(data, name)
        failed = sorted({x["check"] for x in f})
        if expect is None:
            ok = not f
            detail = "all mandatory checks pass" if ok else f"unexpected failures {failed}"
        else:
            ok = expect in failed
            detail = f"expected {expect}; failed={failed}"
        ctrl[name] = {"ok": ok, "expected_failure": expect, "failed_checks": failed,
                      "detail": detail}
    # negative controls: canonical + base must exhibit their declared defects
    fc = check_structure(canon_data, "canonical")
    fcb = sorted({x["check"] for x in fc})
    ctrl["M9_canonical"] = {"ok": ("S3_no_denial_assertion" in fcb and "S7_internal_consistency" in fcb),
                            "expected_failure": ["S3_no_denial_assertion", "S7_internal_consistency"],
                            "failed_checks": fcb}
    fb = check_structure(base_data, "base")
    fbb = sorted({x["check"] for x in fb})
    ctrl["M10_base_84b5d3fa"] = {"ok": "S5_no_unlicensed_direction" in fbb,
                                 "expected_failure": ["S5_no_unlicensed_direction"],
                                 "failed_checks": fbb}
    rd["controls"] = ctrl
    rd["controls_ok"] = all(c["ok"] for c in ctrl.values())

    # ---- ranking + recommendation ------------------------------------------------
    clean = [n for n, r in rd["targets"].items() if r.get("clean")]
    rank = {}
    for n in clean:
        m = rd["targets"][n]["metrics"]
        rank[n] = [m["has_explicit_licensed_direction"], m["has_explicit_reverse_prohibition"],
                   m["has_R3_correction_record"], -m["raw_old_denial_occurrences"], -m["bullet_len"]]
    order = sorted(clean, key=lambda n: ([-int(x) for x in rank[n][:3]] + [rank[n][3], rank[n][4]], n))
    rd["clean_candidates"] = clean
    rd["ranking"] = {n: rank[n] for n in order}
    rd["recommended_candidate"] = order[0] if order else None
    rd["defective_targets"] = sorted(set(TARGETS) - set(clean))
    rd["notes"] = [
        "canonical b2ab6acb remains live REVISE: denial assertion + inverted premise (negative control M9).",
        "staged rev30 base 84b5d3fa is NOT publishable on the direction axis: it asserts H2_loc-inextendibility => this class (negative control M10).",
        "the recommended corrected candidate changes exactly one leaf versus 84b5d3fa; publishing it changes the F2b canonical hash and voids b2ab6acb-bound verdicts, as worker-035 already recorded.",
        "HF-075-F2b-VOCAB (conclusion_type token) is untouched by all three candidates and remains open elsewhere.",
    ]
    if not rd["controls_ok"]:
        rd["verdict"] = "CONTROLS_FAILED"
    elif order:
        rd["verdict"] = "CROSSVERIFY_COMPLETE"
    else:
        rd["verdict"] = "NO_CLEAN_CANDIDATE"
    emit(rd)
    return 0


def emit(rd):
    with open(os.path.join(HERE, "report.json"), "w") as f:
        json.dump(rd, f, indent=2, sort_keys=True)
    with open(os.path.join(HERE, "run_record.txt"), "w") as f:
        f.write(f"run_at={NOW}\nverdict={rd.get('verdict')}\n")
        f.write(f"recommended={rd.get('recommended_candidate')}\n")
        f.write(f"clean={rd.get('clean_candidates')}\n")
        f.write(f"controls_ok={rd.get('controls_ok')}\n")
        for n, r in (rd.get("targets") or {}).items():
            f.write(f"target {n}: clean={r.get('clean')} stale={r.get('stale')} "
                    f"findings={[x['check'] for x in r.get('findings', [])]}\n")
    print(json.dumps({"verdict": rd.get("verdict"),
                      "recommended": rd.get("recommended_candidate"),
                      "clean": rd.get("clean_candidates"),
                      "defective": rd.get("defective_targets"),
                      "controls_ok": rd.get("controls_ok")}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
