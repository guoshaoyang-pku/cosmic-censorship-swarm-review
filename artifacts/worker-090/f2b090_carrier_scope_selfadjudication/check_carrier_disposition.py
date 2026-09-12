#!/usr/bin/env python3
"""
W090-F2B-ACCEPT-SCOPE-SELFADJUDICATION-01

Read-only carrier-disposition classifier for the three F2b accepts counted by the
G-FORM r3 coverage table at schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe.

Carriers (defined and frozen in prereg.json BEFORE the run):
  D1  :152  regularity.must_not_conflate[0]        stale containment denial
  D2  :246  implication_ledger.forbidden_transfers[0].reason   inverted size premise

No canonical path is written. All control mutations happen on in-memory copies or
under artifacts/worker-090/f2b090_carrier_scope_selfadjudication/sandbox/.

Exit codes: 0 all expectations reproduced + all controls pass
            3 pin / carrier-fingerprint hard failure (no classification)
            4 at least one pre-registered expectation or control failed
"""
import hashlib
import io
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PREREG = os.path.join(HERE, "prereg.json")
SANDBOX = os.path.join(HERE, "sandbox")

REVIEWS = [
    "reviews/F2b-rev13-full-090.json",
    "reviews/F2b-review-rev13-worker-071.json",
    "reviews/F2b-review-rev13-052.json",
]
SCHEMA = "schemas/af_scc_c0_vacuum.yaml"
PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN = "artifacts/formulation/FROZEN.json"
STALE_PIN = "1bb78ce9b3572cda"

DETERMINATION_MARKERS = [
    "contradict", "inverted", "inversion", "false premise", "is false", "incorrect",
    "erroneous", "does not hold", "is wrong", "violates", "inconsistent", "stale",
    "repair", "should read", "corrected wording", "superseded",
]
WINDOW = 3


class DupKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    mapping = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in mapping:
            raise DupKeyError(f"duplicate key {key!r} at {node.start_mark}")
        mapping[key] = loader.construct_object(v, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_path(p):
    with open(p, "rb") as f:
        return sha256_bytes(f.read())


def read_text(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def lines_of(text):
    return text.split("\n")


def find_lines(lines, needle):
    n = needle.lower()
    return [i + 1 for i, ln in enumerate(lines) if n in ln.lower()]


def classify(lines, carrier, declared_pin_ok):
    """Deterministic per-carrier classification. Returns dict."""
    out = {"classification": None, "mentions": [], "windows": [], "reason": None}
    if not declared_pin_ok:
        out["classification"] = "NOT_AT_PIN"
        out["reason"] = "review does not bind schemas/af_scc_c0_vacuum.yaml at the measured pin"
        return out
    mention_hits = {}
    for m in carrier["mention_markers"]:
        hits = find_lines(lines, m)
        if hits:
            mention_hits[m] = hits
    if not mention_hits:
        out["classification"] = "SILENT"
        out["reason"] = "zero mention markers present in the review bytes"
        return out
    for m, hits in mention_hits.items():
        for ln in hits:
            out["mentions"].append({"marker": m, "line": ln, "text": lines[ln - 1].strip()[:400]})
    # DISPOSES: determination + relation marker within +/-WINDOW of a mention
    for m, hits in mention_hits.items():
        for ln in hits:
            lo = max(1, ln - WINDOW)
            hi = min(len(lines), ln + WINDOW)
            block = "\n".join(lines[lo - 1:hi]).lower()
            det = [d for d in DETERMINATION_MARKERS if d in block]
            rel = [r for r in carrier["relation_markers"] if r.lower() in block]
            if det and rel:
                out["classification"] = "DISPOSES"
                out["reason"] = f"determination {det} + relation {rel} within +/-{WINDOW} of mention {m!r} at line {ln}"
                out["windows"].append({"around_line": ln, "marker": m, "lo": lo, "hi": hi,
                                       "determination_markers": det, "relation_markers": rel,
                                       "text": "\n".join(lines[lo - 1:hi])[:2000]})
                return out
    # CONTRADICTED: the carrier's own false text appears (a mention marker equal to carrier_text)
    # and no determination marker sits in its window
    ct = carrier["carrier_text"].lower()
    ctl = find_lines(lines, carrier["carrier_text"])
    if ctl:
        for ln in ctl:
            lo = max(1, ln - WINDOW)
            hi = min(len(lines), ln + WINDOW)
            block = "\n".join(lines[lo - 1:hi]).lower()
            det = [d for d in DETERMINATION_MARKERS if d in block]
            if not det:
                out["classification"] = "CONTRADICTED"
                out["reason"] = f"carrier text present at line {ln} with no determination marker in window; read as affirmative"
                out["windows"].append({"around_line": ln, "lo": lo, "hi": hi, "text": "\n".join(lines[lo - 1:hi])[:2000]})
                return out
    out["classification"] = "MENTIONS_UNDISPOSED"
    out["reason"] = "carrier mention present but no window carries a determination on the carrier's claim"
    for m, hits in mention_hits.items():
        for ln in hits:
            lo = max(1, ln - WINDOW)
            hi = min(len(lines), ln + WINDOW)
            out["windows"].append({"around_line": ln, "marker": m, "lo": lo, "hi": hi,
                                   "text": "\n".join(lines[lo - 1:hi])[:2000]})
    return out


def load_carriers(text):
    """Structural + raw-text carrier fingerprint."""
    data = yaml.load(text, Loader=StrictLoader)
    d1 = data["regularity"]["must_not_conflate"][0]
    d2 = data["implication_ledger"]["forbidden_transfers"][0]["reason"]
    lines = lines_of(text)
    d1_line = None
    d2_line = None
    for i, ln in enumerate(lines):
        if "must_not_conflate" in ln:
            d1_line = i + 1
        if "forbidden_transfers" in ln:
            d2_line = i + 1
    return {
        "D1": {"locus": f"{SCHEMA}:{d1_line}", "line": d1_line, "field": "regularity.must_not_conflate[0]",
               "carrier_text": d1, "why_false": "the file's extension_class_containment chain asserts E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
               "mention_markers": ["must_not_conflate", ":152", "No containment with C2 or C0"],
               "relation_markers": ["contain", "chain", "E_C2", "E_C0", "assert"]},
        "D2": {"locus": f"{SCHEMA}:{d2_line}", "line": d2_line, "field": "implication_ledger.forbidden_transfers[0].reason",
               "carrier_text": d2, "why_false": "E_C2 is the innermost/smallest set in the file's own chain; the transfer conclusion is right but the premise is inverted",
               "mention_markers": ["forbidden_transfers", ":246", "C2 is a strictly larger extension class"],
               "relation_markers": ["larger", "smaller", "weaker", "stronger", "invert", "innermost", "subset"]},
    }


def declared_binding(text):
    """Return (binds_pin: bool, declared: dict) for review bytes."""
    try:
        d = json.loads(text)
    except Exception as e:
        return False, {"parse_error": str(e)}
    declared = {"reviewed_sha256": d.get("reviewed_sha256")}
    rp = d.get("reviewed_pins") or {}
    if isinstance(rp, dict):
        declared["reviewed_pins"] = {k: v for k, v in rp.items() if "af_scc_c0_vacuum" in k}
    ok = False
    if isinstance(d.get("reviewed_sha256"), str) and d["reviewed_sha256"].startswith(PIN[:12]):
        ok = True
    if isinstance(rp, dict):
        for k, v in rp.items():
            if "af_scc_c0_vacuum" in k and isinstance(v, str) and v.startswith(PIN[:12]):
                ok = True
    return ok, declared


def run(schema_text, reviews, pins_ok):
    carriers = load_carriers(schema_text)
    result = {
        "carrier_fingerprint": {k: {"locus": v["locus"], "carrier_text": v["carrier_text"][:300]} for k, v in carriers.items()},
        "carrier_fingerprint_ok": True,
        "pins_ok": pins_ok,
        "per_file": {},
        "coverage": {"D1": [], "D2": []},
    }
    for path, text in reviews.items():
        lines = lines_of(text)
        binds, declared = declared_binding(text)
        entry = {"sha256": sha256_bytes(text.encode("utf-8")), "declared": declared, "carriers": {}}
        for cid, c in carriers.items():
            entry["carriers"][cid] = classify(lines, c, binds)
            if entry["carriers"][cid]["classification"] == "DISPOSES":
                result["coverage"][cid].append(path)
        result["per_file"][path] = entry
    return result


def main():
    with open(PREREG) as f:
        prereg = json.load(f)
    os.makedirs(SANDBOX, exist_ok=True)

    # --- pin block -------------------------------------------------------
    pins_ok = {}
    hard = []
    for p, exp in prereg["pins"].items():
        full = os.path.join(ROOT, p)
        if not os.path.exists(full):
            pins_ok[p] = "MISSING"
            hard.append(f"{p} missing")
            continue
        m = sha256_path(full)
        pins_ok[p] = m
        if m != exp:
            hard.append(f"{p} measured {m} != prereg {exp}")

    schema_text = read_text(os.path.join(ROOT, SCHEMA))
    live_fp = load_carriers(schema_text)
    fp_ok = True
    for cid in ("D1", "D2"):
        want = prereg["carrier_definitions"][cid]["carrier_text"]
        got = live_fp[cid]["carrier_text"]
        if want.lower() not in got.lower():
            fp_ok = False

    result = {
        "task_id": prereg["task_id"],
        "node_id": prereg["node_id"],
        "class_id": prereg["class_id"],
        "gate": prereg["gate"],
        "actor": "worker-090",
        "measured_at": None,
        "pins_measured": pins_ok,
        "pins_ok": not hard,
        "pin_problems": hard,
        "carrier_fingerprint_live": {k: {"locus": v["locus"], "carrier_text": v["carrier_text"]} for k, v in live_fp.items()},
        "carrier_fingerprint_ok": fp_ok,
        "expectations": prereg["pre_registered_expectations"],
        "consequence": None,
        "run": None,
    }
    if hard or not fp_ok:
        result["verdict"] = "HARD_FAIL_PIN_OR_FINGERPRINT"
        with open(os.path.join(HERE, "results.json"), "w") as f:
            json.dump(result, f, indent=1, sort_keys=True)
        print("HARD FAIL:", hard, "fp_ok=", fp_ok)
        return 3

    reviews = {p: read_text(os.path.join(ROOT, p)) for p in REVIEWS}
    run1 = run(schema_text, reviews, True)
    run2 = run(schema_text, reviews, True)
    payload1 = sha256_bytes(json.dumps(run1, sort_keys=True).encode())
    payload2 = sha256_bytes(json.dumps(run2, sort_keys=True).encode())
    result["run"] = run1
    result["determinism"] = {"run1_payload_sha256": payload1, "run2_payload_sha256": payload2,
                             "byte_identical": payload1 == payload2}

    # expectation check
    mismatches = []
    for path, exp in prereg["pre_registered_expectations"].items():
        got = {cid: run1["per_file"][path]["carriers"][cid]["classification"] for cid in ("D1", "D2")}
        for cid in ("D1", "D2"):
            if got[cid] != exp[cid]:
                mismatches.append({"file": path, "carrier": cid, "expected": exp[cid], "got": got[cid]})
    result["expectation_mismatches"] = mismatches
    result["coverage_counts"] = {cid: len(v) for cid, v in run1["coverage"].items()}
    result["consequence"] = (
        "0 of the 3 r3-counted F2b full accepts dispose D1 or D2"
        if not any(run1["coverage"].values()) else
        "at least one counted accept disposes a carrier: " + json.dumps(run1["coverage"]))

    # --- controls --------------------------------------------------------
    def synth(obj):
        return json.dumps(obj, indent=1)

    review090 = reviews["reviews/F2b-rev13-full-090.json"]
    c_specs = {
        "C1": synth({"reviewer": "ctl", "verdict": "revise", "counts_as_full_schema_verdict": True,
                     "reviewed_sha256": PIN,
                     "findings": [{"statement": "must_not_conflate :152 says no containment with C2 or C0 is asserted here; this is contradicted by the file's own chain and the wording should read as the corrected F2a containment statement."}]}),
        "C2": synth({"reviewer": "ctl", "verdict": "accept", "counts_as_full_schema_verdict": True,
                     "reviewed_sha256": PIN,
                     "checks": ["P1: must_not_conflate field present - pass"]}),
        "C3": synth({"reviewer": "ctl", "verdict": "accept", "counts_as_full_schema_verdict": True,
                     "reviewed_sha256": PIN,
                     "note": "confirmed: C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}),
        "C4": synth({"reviewer": "ctl", "verdict": "revise", "counts_as_full_schema_verdict": True,
                     "reviewed_sha256": PIN,
                     "findings": [{"statement": "forbidden_transfers :246 reason is inverted: C2 is the innermost subset, so the premise is false; corrected wording required."}]}),
        "C5": review090,
        "C6": json.dumps({**json.loads(review090), "reviewed_sha256": STALE_PIN}, indent=1),
    }
    ctl_results = []
    for cid, text in c_specs.items():
        with open(os.path.join(SANDBOX, f"control_{cid}.json"), "w") as f:
            f.write(text)
        r = run(schema_text, {f"control_{cid}": text}, True)
        ctl_results.append({"id": cid, "D1": r["per_file"][f"control_{cid}"]["carriers"]["D1"]["classification"],
                            "D2": r["per_file"][f"control_{cid}"]["carriers"]["D2"]["classification"]})
    # C7: mutated schema fingerprint
    mut = schema_text.replace("No containment with C2 or C0 is asserted here",
                              "Some containment with C2 or C0 may be asserted here")
    with open(os.path.join(SANDBOX, "control_C7_schema.yaml"), "w") as f:
        f.write(mut)
    mut_fp = load_carriers(mut)
    c7_ok = prereg["carrier_definitions"]["D1"]["carrier_text"].lower() not in mut_fp["D1"]["carrier_text"].lower()
    ctl_results.append({"id": "C7", "carrier_fingerprint_moved_detected": c7_ok,
                        "mutated_carrier_text": mut_fp["D1"]["carrier_text"][:200]})
    ctl_results.append({"id": "C8", "byte_identical": payload1 == payload2,
                        "run1_payload_sha256": payload1, "run2_payload_sha256": payload2})

    expected_controls = {
        "C1": {"D1": "DISPOSES", "D2": "SILENT"},
        "C2": {"D1": "MENTIONS_UNDISPOSED", "D2": "SILENT"},
        "C3": {"D1": "SILENT", "D2": "CONTRADICTED"},
        "C4": {"D1": "SILENT", "D2": "DISPOSES"},
        "C5": {"D1": "SILENT", "D2": "SILENT"},
        "C6": {"D1": "NOT_AT_PIN", "D2": "NOT_AT_PIN"},
    }
    ctl_fail = []
    for r in ctl_results:
        exp = expected_controls.get(r["id"])
        if exp and any(r[k] != exp[k] for k in ("D1", "D2")):
            ctl_fail.append({"id": r["id"], "expected": exp, "got": {"D1": r["D1"], "D2": r["D2"]}})
    if not c7_ok:
        ctl_fail.append({"id": "C7", "expected": "fingerprint moved", "got": "not detected"})
    if payload1 != payload2:
        ctl_fail.append({"id": "C8", "expected": "byte identical", "got": "differs"})

    controls = {"controls": ctl_results, "expected": expected_controls,
                "failures": ctl_fail, "all_pass": not ctl_fail}
    with open(os.path.join(HERE, "controls.json"), "w") as f:
        json.dump(controls, f, indent=1, sort_keys=True)

    # --- erratum emission (pre-registered condition) ---------------------
    erratum = {
        "schema": "scope-narrowing-erratum/1",
        "task_id": prereg["task_id"],
        "created_at": "2026-09-12T01:27:00+08:00",
        "actor": "worker-090",
        "target_review": "reviews/F2b-rev13-full-090.json",
        "target_sha256": pins_ok["reviews/F2b-rev13-full-090.json"],
        "target_bytes_rewritten": False,
        "counts_as_full_schema_verdict_retained": True,
        "retained_carrier_scope": ["B06-embedding-witnesses", "V02-F0-allowed-list-inversion",
                                   "V03-registry-pointer-declared", "R01-review-status-fresh"],
        "excluded_carrier_scope": ["HF-152/W050-F2B-D1 containment denial",
                                   "HF-246/W053-F2B-REV29-01 inverted size premise"],
        "statement": "The accept in reviews/F2b-rev13-full-090.json remains a full-schema accept at b2ab6acb2bbe for the four carriers it declares. It is NOT carrier coverage for the F2b :152 containment denial or the :246 inverted size premise: the file's bytes contain zero mentions of either locus or field (measured, sha256 unchanged). r3 or any successor coverage count must not count this file as disposing those two carriers.",
        "authority_note": "Advisory worker scope declaration; no gate verdict, no node transition. The review bytes are deliberately NOT rewritten (anti-CF-31 norm).",
    }
    withheld = {
        "schema": "scope-narrowing-erratum/1",
        "task_id": prereg["task_id"],
        "status": "WITHHELD",
        "reason": "pre-registered expectation did not reproduce; see results.json expectation_mismatches",
        "mismatches": mismatches,
        "authority_note": "Advisory worker evidence only.",
    }
    if not mismatches:
        with open(os.path.join(HERE, "erratum_scope_narrowing.json"), "w") as f:
            json.dump(erratum, f, indent=1, sort_keys=True)
        result["erratum"] = "erratum_scope_narrowing.json"
    else:
        with open(os.path.join(HERE, "erratum_WITHHELD.json"), "w") as f:
            json.dump(withheld, f, indent=1, sort_keys=True)
        result["erratum"] = "erratum_WITHHELD.json"

    result["verdict"] = ("PASS_EXPECTATIONS_AND_CONTROLS" if (not mismatches and not ctl_fail)
                         else "FAIL_EXPECTATION_OR_CONTROL")
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print(json.dumps({"verdict": result["verdict"], "coverage_counts": result["coverage_counts"],
                      "expectation_mismatches": mismatches, "control_failures": ctl_fail,
                      "determinism": result["determinism"]["byte_identical"]}, indent=1))
    return 0 if result["verdict"].startswith("PASS") else 4


if __name__ == "__main__":
    sys.exit(main())
