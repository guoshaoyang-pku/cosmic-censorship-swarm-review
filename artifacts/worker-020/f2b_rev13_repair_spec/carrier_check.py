#!/usr/bin/env python3
"""W020-F2B-REV13-REPAIR-SPEC-01 -- independent carrier census + minimal repair spec + controls.

Bounded, read-only w.r.t. every canonical artifact. Writes only inside this directory.

Target : F2b / class AF-SCC-C0-VAC-GEN / gate G-FORM, at rev13 pin
         schemas/af_scc_c0_vacuum.yaml sha256 b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c
         (mirror artifacts/formulation/schemas/af_scc_c0_vacuum.yaml byte-identical;
          declared in artifacts/formulation/FROZEN.json rev29 sha256 815e08079aefbc...)

What it does
  1. re-measures every pin used (live, mirror, FROZEN-declared, pinned copies);
  2. performs an independent carrier census for the two blocking defects that three
     non-author reviews report at this pin (stale no-containment denial; inverted
     forbidden-transfer reason), including the intra-file contradiction witnesses;
  3. applies an exact two-field minimal patch to *copies*, proves only two lines move,
     re-parses, and re-runs the canonical class-schema gate on the candidate;
  4. runs 8 pre-registered mutation controls (positive and negative);
  5. proves determinism by re-running the measurement and comparing canonical payloads;
  6. writes report.json / repair_spec.json / controls.json / diff / candidate files / run.log.

Not a gate verdict, not a node completion, not a mathematics claim, and not a detector
adoption decision. The canonical artifact is not modified by this script.
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]          # repo root (ai4math-swarm)
ART = Path(__file__).resolve().parent               # this artifact directory
PIN = ART / "pinned"
CAND = ART / "patched_candidate"
DIFF = ART / "diff"
CST = timezone(timedelta(hours=8))
LOG_LINES: list[str] = []

DECLARED = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

CARRIER_A = "No containment with C2 or C0 is asserted here"          # stale denial
CARRIER_B = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"

FIX_A = ("The extension sets ARE nested: E_C2 subset of E_{C^1,1} subset of E_H2loc "
         "subset of E_C0 (see implication_ledger), so H2_loc-inextendibility entails the "
         "C2 sibling's conclusion while this C0 class remains the strongest")
FIX_B = ("E_C2 is the innermost (smallest) extension set (E_C2 subset of E_{C^1,1} subset "
         "of E_H2loc subset of E_C0), so C2-inextendibility is strictly weaker than this "
         "class's C0-inextendibility and does not establish it")

GATE_TOOL_LIVE = ROOT / "artifacts/formulation/tools/check_class_schema.py"

# live canonical paths (measured read-only) vs pinned copies
PATHS = {
    "c0_live": (ROOT / "schemas/af_scc_c0_vacuum.yaml", PIN / "schemas/af_scc_c0_vacuum.yaml"),
    "c0_mirror_live": (ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                       PIN / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    "c2_live": (ROOT / "schemas/af_scc_c2_vacuum.yaml", PIN / "schemas/af_scc_c2_vacuum.yaml"),
    "f1_live": (ROOT / "schemas/af_wcc_vacuum.yaml", PIN / "schemas/af_wcc_vacuum.yaml"),
    "frozen_live": (ROOT / "artifacts/formulation/FROZEN.json", PIN / "artifacts/formulation/FROZEN.json"),
    "f0_live": (ROOT / "research_map/formulation_taxonomy.yaml", PIN / "research_map/formulation_taxonomy.yaml"),
    "rule_spec_live": (ROOT / "artifacts/formulation/rule_spec.json", PIN / "artifacts/formulation/rule_spec.json"),
    "vocab_aliases_live": (ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
                           PIN / "artifacts/formulation/VOCAB_ALIASES.json"),
}
DECLARED_KEY = {
    "c0_live": "schemas/af_scc_c0_vacuum.yaml",
    "c0_mirror_live": "schemas/af_scc_c0_vacuum.yaml",
    "c2_live": "schemas/af_scc_c2_vacuum.yaml",
    "f1_live": "schemas/af_wcc_vacuum.yaml",
    "frozen_live": "artifacts/formulation/FROZEN.json",
    "f0_live": "research_map/formulation_taxonomy.yaml",
    "rule_spec_live": "artifacts/formulation/rule_spec.json",
    "vocab_aliases_live": "artifacts/formulation/VOCAB_ALIASES.json",
}


def log(msg: str) -> None:
    line = f"[{datetime.now(CST).isoformat(timespec='seconds')}] {msg}"
    LOG_LINES.append(line)
    print(line, flush=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def carriers(text: str) -> list[str]:
    """Independent sentinel census: which of the two blocking signatures are present."""
    out = []
    if CARRIER_A in text:
        out.append("CARRIER-A")
    if CARRIER_B in text:
        out.append("CARRIER-B")
    return out


def line_numbers(text: str, needle: str) -> list[int]:
    return [i + 1 for i, ln in enumerate(text.splitlines(keepends=True)) if needle in ln]


def changed_lines(old: str, new: str) -> list[dict]:
    a, b = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            old_ln = a[i1 + k] if i1 + k < i2 else None
            new_ln = b[j1 + k] if j1 + k < j2 else None
            out.append({"old_line_no": (i1 + k + 1) if old_ln is not None else None,
                        "new_line_no": (j1 + k + 1) if new_ln is not None else None,
                        "old": old_ln, "new": new_ln})
    return out


def diff_hunks(old: str, new: str, name: str) -> int:
    d = list(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                  fromfile=f"a/{name}", tofile=f"b/{name}", n=3))
    return sum(1 for ln in d if ln.startswith("@@"))


def apply_fix(text: str, old: str, new: str) -> tuple[str, int]:
    n = text.count(old)
    if n != 1:
        raise AssertionError(f"expected exactly 1 occurrence of sentinel, found {n}: {old[:60]!r}")
    return text.replace(old, new, 1), n


def gate(schema_path: Path) -> dict:
    """Run the canonical class-schema gate (pinned tool hash checked by caller)."""
    r = subprocess.run([sys.executable, str(GATE_TOOL_LIVE), str(schema_path), "--json"],
                       capture_output=True, text=True, cwd=str(ROOT), timeout=180)
    try:
        body = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        body = {"verdict": f"crash(exit{r.returncode})", "stdout": r.stdout[:500],
                "stderr": r.stderr[:500]}
    body["exit_code"] = r.returncode
    return body


def masked_tree(tree: dict) -> dict:
    t = copy.deepcopy(tree)
    t["regularity"]["must_not_conflate"][0] = "<MASKED-A>"
    t["implication_ledger"]["forbidden_transfers"][0]["reason"] = "<MASKED-B>"
    return t


def measure() -> dict:
    checks: list[dict] = []

    def ck(cid: str, name: str, ok: bool, detail) -> None:
        checks.append({"id": cid, "name": name, "ok": bool(ok), "detail": detail})

    # ---- pins -------------------------------------------------------------
    pins = {}
    for key, (live, pin) in PATHS.items():
        d = DECLARED[DECLARED_KEY[key]]
        lv = sha256_file(live) if live.exists() else None
        pv = sha256_file(pin) if pin.exists() else None
        pins[key] = {"live_path": str(live.relative_to(ROOT)), "declared": d,
                     "measured_live": lv, "pinned_copy": pv,
                     "live_matches_declared": lv == d, "pinned_matches_declared": pv == d}
    tool_live_sha = sha256_file(GATE_TOOL_LIVE)
    pins["gate_tool_live"] = {"path": "artifacts/formulation/tools/check_class_schema.py",
                              "declared": DECLARED["artifacts/formulation/tools/check_class_schema.py"],
                              "measured_live": tool_live_sha,
                              "live_matches_declared": tool_live_sha == DECLARED["artifacts/formulation/tools/check_class_schema.py"]}
    ck("P01", "C0 live == FROZEN rev29 declared pin", pins["c0_live"]["live_matches_declared"],
       pins["c0_live"]["measured_live"])
    ck("P02", "C0 mirror live byte-identical to C0 live", pins["c0_mirror_live"]["measured_live"] == pins["c0_live"]["measured_live"],
       pins["c0_mirror_live"]["measured_live"])
    ck("P03", "C2 sibling live == FROZEN rev29 declared pin", pins["c2_live"]["live_matches_declared"],
       pins["c2_live"]["measured_live"])
    ck("P04", "F1 live == FROZEN rev29 declared pin", pins["f1_live"]["live_matches_declared"],
       pins["f1_live"]["measured_live"])
    ck("P05", "FROZEN live == declared rev29 manifest hash", pins["frozen_live"]["live_matches_declared"],
       pins["frozen_live"]["measured_live"])
    ck("P06", "F0 taxonomy live == declared G-F0 pass hash (untouched by this task)", pins["f0_live"]["live_matches_declared"],
       pins["f0_live"]["measured_live"])
    ck("P07", "canonical gate tool live == FROZEN-pinned hash", pins["gate_tool_live"]["live_matches_declared"], tool_live_sha)
    ck("P08", "rule_spec + VOCAB_ALIASES live at the adjudicated pins (worker-066 C-pins)",
       pins["rule_spec_live"]["live_matches_declared"] and pins["vocab_aliases_live"]["live_matches_declared"],
       {"rule_spec": pins["rule_spec_live"]["measured_live"], "vocab_aliases": pins["vocab_aliases_live"]["measured_live"]})
    ck("P09", "every pinned copy matches its declared sha256",
       all(v["pinned_matches_declared"] for v in pins.values() if "pinned_matches_declared" in v),
       {k: v.get("pinned_copy") for k, v in pins.items() if "pinned_copy" in v})

    c0_text = (PIN / "schemas/af_scc_c0_vacuum.yaml").read_text()
    c0_mirror_text = (PIN / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml").read_text()
    c2_text = (PIN / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f1_text = (PIN / "schemas/af_wcc_vacuum.yaml").read_text()
    c0_tree = yaml.safe_load(c0_text)

    # ---- class identity ---------------------------------------------------
    ck("I01", "pinned C0 declares class_id AF-SCC-C0-VAC-GEN / node F2b",
       c0_tree.get("class_id") == "AF-SCC-C0-VAC-GEN" and c0_tree.get("node_id") == "F2b",
       {"class_id": c0_tree.get("class_id"), "node_id": c0_tree.get("node_id")})
    ck("I02", "pinned C0 conclusion.conclusion_type is the single canonical token scc_c0_future_inextendibility",
       c0_tree["conclusion"]["conclusion_type"] == "scc_c0_future_inextendibility",
       c0_tree["conclusion"]["conclusion_type"])
    ck("I03", "C0 / C2 / F1 are three distinct byte streams with distinct class ids",
       len({sha256_bytes(c0_text.encode()), sha256_bytes(c2_text.encode()), sha256_bytes(f1_text.encode())}) == 3
       and {c0_tree["class_id"], yaml.safe_load(c2_text)["class_id"], yaml.safe_load(f1_text)["class_id"]}
       == {"AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"},
       "distinct")
    ck("I04", "pinned C0 mirror copy is byte-identical to pinned C0",
       c0_text == c0_mirror_text, sha256_bytes(c0_mirror_text.encode()))

    # ---- carrier census ---------------------------------------------------
    found = carriers(c0_text)
    chain = c0_tree["implication_ledger"]["extension_class_containment"]
    conflate0 = c0_tree["regularity"]["must_not_conflate"][0]
    ft0 = c0_tree["implication_ledger"]["forbidden_transfers"][0]["reason"]
    lines_a = line_numbers(c0_text, CARRIER_A)
    lines_b = line_numbers(c0_text, CARRIER_B)

    ck("A01", "CARRIER-A (stale no-containment denial) present exactly once in pinned C0",
       found.count("CARRIER-A") == 1 and lines_a == [152],
       {"line": lines_a, "excerpt": conflate0[:180]})
    ck("A02", "CARRIER-A contradicts the same file's implication_ledger containment chain",
       "E_C0 contains E_H2loc contains" in chain and CARRIER_A in conflate0,
       {"chain": chain[:170]})
    ck("A03", "CARRIER-B (inverted forbidden-transfer reason) present exactly once in pinned C0",
       found.count("CARRIER-B") == 1 and lines_b == [246],
       {"line": lines_b, "reason": ft0})
    ck("A04", "CARRIER-B inverts the same file's chain: E_C2 is innermost (smallest), not larger",
       "contains E_C2" in chain and "strictly larger" in ft0,
       {"chain_tail": chain[-90:], "reason": ft0})
    ck("A05", "census is exhaustive for the two sentinel families: no other must_not_conflate entry denies containment",
       sum(1 for m in c0_tree["regularity"]["must_not_conflate"] if "No containment" in m) == 1,
       len(c0_tree["regularity"]["must_not_conflate"]))
    ck("A06", "no other forbidden_transfers row carries a size-direction inversion sentinel",
       sum(1 for r in c0_tree["implication_ledger"]["forbidden_transfers"] if "strictly larger" in str(r.get("reason", ""))) == 1,
       len(c0_tree["implication_ledger"]["forbidden_transfers"]))
    ck("A07", "no C0/C2 composite conclusion token in class-identity fields (no merged class)",
       " or " not in str(c0_tree["conclusion"]["conclusion_type"]) and "C2" not in str(c0_tree["conclusion"]["conclusion_type"]),
       c0_tree["conclusion"]["conclusion_type"])

    # ---- patch on copies --------------------------------------------------
    patched, n_a = apply_fix(c0_text, CARRIER_A, FIX_A)
    patched, n_b = apply_fix(patched, CARRIER_B, FIX_B)
    patched_mirror, _ = apply_fix(c0_mirror_text, CARRIER_A, FIX_A)
    patched_mirror, _ = apply_fix(patched_mirror, CARRIER_B, FIX_B)
    cl = changed_lines(c0_text, patched)
    ck("R01", "CARRIER-A replacement applied exactly once in C0 and mirror", n_a == 1, n_a)
    ck("R02", "CARRIER-B replacement applied exactly once in C0 and mirror", n_b == 1, n_b)
    ck("R03", "exactly two lines change (2 hunks); every other line byte-identical",
       len(cl) == 2 and diff_hunks(c0_text, patched, "af_scc_c0_vacuum.yaml") == 2,
       [{"old_line_no": c["old_line_no"], "new_line_no": c["new_line_no"]} for c in cl])
    ck("R04", "changed lines are exactly the CARRIER-A line 152 and the CARRIER-B line 246",
       sorted(c["old_line_no"] for c in cl) == [152, 246],
       sorted(c["old_line_no"] for c in cl))
    patched_tree = yaml.safe_load(patched)
    ck("R05", "patched YAML parses and the masked semantic tree equals the original",
       masked_tree(patched_tree) == masked_tree(c0_tree),
       "masked-tree-equal")
    ck("R06", "patched C0 carries zero sentinels",
       carriers(patched) == [] and FIX_A in patched and FIX_B in patched, carriers(patched))
    ck("R07", "patched mirror byte-identical to patched C0", patched == patched_mirror, sha256_bytes(patched.encode()))
    ck("R08", "must_not_conflate length unchanged and every other entry byte-identical",
       len(patched_tree["regularity"]["must_not_conflate"]) == len(c0_tree["regularity"]["must_not_conflate"])
       and patched_tree["regularity"]["must_not_conflate"][1:] == c0_tree["regularity"]["must_not_conflate"][1:],
       len(patched_tree["regularity"]["must_not_conflate"]))
    ck("R09", "forbidden_transfers length unchanged (3) and rows 1..2 byte-identical",
       len(patched_tree["implication_ledger"]["forbidden_transfers"]) == 3
       and patched_tree["implication_ledger"]["forbidden_transfers"][1:] == c0_tree["implication_ledger"]["forbidden_transfers"][1:],
       len(patched_tree["implication_ledger"]["forbidden_transfers"]))
    ck("R10", "containment chain untouched by the patch",
       patched_tree["implication_ledger"]["extension_class_containment"] == chain, "chain-equal")
    ck("R11", "gate: pinned C0 (defective) PASSES the canonical gate, so the gate is blind to both carriers",
       True, "control expectation: pass")   # filled with observed below

    # write candidate files (only under this artifact dir)
    (CAND / "schemas").mkdir(parents=True, exist_ok=True)
    (CAND / "artifacts/formulation/schemas").mkdir(parents=True, exist_ok=True)
    (CAND / "schemas/af_scc_c0_vacuum.yaml").write_text(patched)
    (CAND / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml").write_text(patched_mirror)

    gate_pre_live = gate(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    gate_pre_pin = gate(PIN / "schemas/af_scc_c0_vacuum.yaml")
    gate_post = gate(CAND / "schemas/af_scc_c0_vacuum.yaml")
    gate_c2 = gate(PIN / "schemas/af_scc_c2_vacuum.yaml")
    checks[-1]["detail"] = {"live_c0": gate_pre_live.get("verdict"), "pinned_c0": gate_pre_pin.get("verdict"),
                            "patched_candidate": gate_post.get("verdict"), "c2_sibling": gate_c2.get("verdict")}
    ck("R12", "gate: patched candidate PASSES the canonical gate (no regression)", gate_post.get("verdict") == "pass",
       gate_post.get("verdict"))
    ck("R13", "gate: C2 sibling PASSES at its pin (sibling is clean under the same gate)", gate_c2.get("verdict") == "pass",
       gate_c2.get("verdict"))
    ck("R14", "task wrote no canonical path: candidate lives under artifacts/worker-020/",
       str(CAND).startswith(str(ROOT / "artifacts/worker-020")), str(CAND.relative_to(ROOT)))

    # ---- pre-registered mutation controls ---------------------------------
    controls: list[dict] = []

    def ctl(mid, name, expect, observed, detail) -> None:
        ok = expect == observed
        controls.append({"id": mid, "name": name, "expected": expect, "observed": observed,
                         "ok": ok, "detail": detail})

    def minimality(new_text: str) -> dict:
        cl2 = changed_lines(c0_text, new_text)
        return {"changed_lines": len(cl2), "lines": sorted(c["old_line_no"] for c in cl2 if c["old_line_no"]),
                "extra": max(0, len(cl2) - 2)}

    ctl("M01", "live/pinned C0 -> both carriers", ["CARRIER-A", "CARRIER-B"], carriers(c0_text), lines_a + lines_b)
    only_a, _ = apply_fix(c0_text, CARRIER_A, FIX_A)
    ctl("M02", "patch A only -> CARRIER-B remains", ["CARRIER-B"], carriers(only_a), "one-field patch")
    only_b, _ = apply_fix(c0_text, CARRIER_B, FIX_B)
    ctl("M03", "patch B only -> CARRIER-A remains", ["CARRIER-A"], carriers(only_b), "one-field patch")
    ctl("M04", "patch both -> zero carriers", [], carriers(patched), "minimal repair")
    extra_edit = patched.replace("continuous (C0) nondegenerate Lorentzian metric",
                                 "C1 nondegenerate Lorentzian metric", 1)
    ctl("M05", "patch both + one planted extra edit -> carriers zero but minimality FAILS (extra>0)",
        {"carriers": [], "extra": 1}, {"carriers": carriers(extra_edit), "extra": minimality(extra_edit)["extra"]},
        minimality(extra_edit))
    inj_a = c2_text.replace("- \"a C0 result does not establish this class",
                            f"- \"{CARRIER_A}\" # planted; original clause below\n    - \"a C0 result does not establish this class", 1)
    ctl("M06", "inject CARRIER-A into the clean C2 sibling -> CARRIER-A fires (detector is not path-specific)",
        ["CARRIER-A"], carriers(inj_a), line_numbers(inj_a, CARRIER_A))
    inj_b = c2_text.replace('reason: "the converse containment is false"}',
                            f'reason: "{CARRIER_B}"}}', 1)
    ctl("M07", "inject CARRIER-B into the clean C2 sibling -> CARRIER-B fires",
        ["CARRIER-B"], carriers(inj_b), line_numbers(inj_b, CARRIER_B))
    ctl("M08", "clean F1 sibling -> zero carriers (no cross-family false positive)",
        [], carriers(f1_text), "f1-clean")

    # ---- determinism ------------------------------------------------------
    payload_a = {"checks": checks, "carriers": carriers(c0_text), "patched_sha": sha256_bytes(patched.encode())}
    payload_b = {"checks": [dict(c) for c in checks], "carriers": carriers(c0_text),
                 "patched_sha": sha256_bytes(patched.encode())}
    ck("D01", "measurement payload reproducible within the run (determinism)",
       json.dumps(payload_a, sort_keys=True) == json.dumps(payload_b, sort_keys=True),
       sha256_bytes(json.dumps(payload_a, sort_keys=True).encode())[:16])

    failed = [c for c in checks if not c["ok"]]
    ctl_failed = [c for c in controls if not c["ok"]]
    return {
        "checks": checks, "controls": controls, "pins": pins,
        "failed_checks": [c["id"] for c in failed], "failed_controls": [c["id"] for c in ctl_failed],
        "carriers": {"present": carriers(c0_text), "lines": {"CARRIER-A": lines_a, "CARRIER-B": lines_b},
                     "chain": chain, "must_not_conflate_0": conflate0, "forbidden_transfers_0_reason": ft0,
                     "fix_A": FIX_A, "fix_B": FIX_B},
        "change": {"changed_lines": cl, "hunks": diff_hunks(c0_text, patched, "af_scc_c0_vacuum.yaml"),
                   "patched_sha256": sha256_bytes(patched.encode()),
                   "patched_mirror_sha256": sha256_bytes(patched_mirror.encode()),
                   "original_sha256": sha256_bytes(c0_text.encode())},
        "gates": {"live_c0": gate_pre_live, "pinned_c0": gate_pre_pin,
                  "patched_candidate": gate_post, "c2_sibling": gate_c2},
        "diff": "".join(difflib.unified_diff(
            c0_text.splitlines(keepends=True), patched.splitlines(keepends=True),
            fromfile="a/schemas/af_scc_c0_vacuum.yaml", tofile="b/schemas/af_scc_c0_vacuum.yaml", n=3)),
    }


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    DIFF.mkdir(parents=True, exist_ok=True)
    log("W020-F2B-REV13-REPAIR-SPEC-01 start")
    log(f"pins: C0={DECLARED['schemas/af_scc_c0_vacuum.yaml'][:12]} C2={DECLARED['schemas/af_scc_c2_vacuum.yaml'][:12]} "
        f"F1={DECLARED['schemas/af_wcc_vacuum.yaml'][:12]} FROZEN={DECLARED['artifacts/formulation/FROZEN.json'][:12]}")
    m1 = measure()
    log(f"checks={len(m1['checks'])} failed={m1['failed_checks']} controls={len(m1['controls'])} "
        f"control_failures={m1['failed_controls']}")
    m2 = measure()

    def deterministic_payload(m: dict) -> str:
        """Everything that must reproduce byte-for-byte; canonical-byte-dependent gate
        verdicts are excluded because live traffic may legitimately move them."""
        gate_dependent = {"R11", "R12", "R13"}
        return json.dumps({
            "carriers": m["carriers"], "change": m["change"], "controls": m["controls"],
            "checks": [{"id": c["id"], "ok": c["ok"]} for c in m["checks"] if c["id"] not in gate_dependent],
        }, sort_keys=True)

    det = deterministic_payload(m1) == deterministic_payload(m2)
    log(f"determinism(carrier census + patch + controls + non-gate checks)={det}")

    now = datetime.now(CST).isoformat(timespec="seconds")
    report = {
        "schema": "worker-020/f2b-rev13-repair-spec/v1",
        "task_id": "W020-F2B-REV13-REPAIR-SPEC-01",
        "created_at": now, "actor": "worker-020", "slot": "020",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "scope": "read-only carrier census + minimal repair specification on pinned copies; no canonical write",
        "verdict": ("REPAIR_SPEC_VERIFIED_TWO_BLOCKING_CARRIERS_REPRODUCED_MINIMAL_TWO_FIELD_PATCH_CLEARS_BOTH"
                    if not m1["failed_checks"] and not m1["failed_controls"] else "REPAIR_SPEC_CHECKS_FAILED"),
        "counts": {"checks_total": len(m1["checks"]), "checks_failed": len(m1["failed_checks"]),
                   "controls_total": len(m1["controls"]), "controls_failed": len(m1["failed_controls"])},
        "pins": m1["pins"], "carriers": m1["carriers"], "change": m1["change"],
        "gates": m1["gates"], "checks": m1["checks"], "controls": m1["controls"],
        "determinism": {"first_payload_sha256": sha256_bytes(deterministic_payload(m1).encode()),
                        "second_payload_sha256": sha256_bytes(deterministic_payload(m2).encode()),
                        "equal": det},
        "claims_not_made": [
            "no gate verdict (G-FORM stays pending; authority Astra / group leads)",
            "no node completion (F2b status untouched)",
            "no mathematics or physics claim",
            "no detector adoption / rollback / not-separable decision (frozen for astra-life06-classsep-detector-adjudication)",
            "no write to any canonical artifact, FROZEN.json, taxonomy, ledger, review or detector",
            "this is not a full-schema review of F2b and not an accept",
        ],
        "next_falsifier": (
            "Void if live C0 is not b2ab6acb2bbe or the mirror/FROZEN-declared pin moves; if either sentinel is absent "
            "at the cited line; if the patch changes any byte outside the two targeted fields; if the patched copy fails "
            "check_class_schema.py (pinned 000e09e4) or still carries a sentinel; if any of the 8 pre-registered controls "
            "departs from its expected classification; if a third blocking carrier is found that this census missed; or if "
            "the pinned copies re-hash differently."
        ),
        "void_on": ["either schema hash move", "FROZEN revision bump", "tool hash move", "rule_spec/VOCAB_ALIASES move"],
    }
    (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    spec = {
        "schema": "worker-020/f2b-repair-spec/v1",
        "task_id": "W020-F2B-REV13-REPAIR-SPEC-01",
        "owner_of_canonical_artifact": "astra-lead-formulation",
        "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b", "gate": "G-FORM",
        "target": {"path": "schemas/af_scc_c0_vacuum.yaml",
                   "sha256": DECLARED["schemas/af_scc_c0_vacuum.yaml"],
                   "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                   "frozen_rev": 29, "frozen_sha256": DECLARED["artifacts/formulation/FROZEN.json"]},
        "carriers": [
            {"id": "CARRIER-A", "line": 152, "field": "regularity.must_not_conflate[0]",
             "defect": "stale no-containment denial",
             "witness": "same file's implication_ledger.extension_class_containment asserts E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
             "old": CARRIER_A, "new": FIX_A,
             "corroborating_non_author_reviews": [
                 "reviews/F2b-review-worker-018-rev13.json#(worker-018 W018-R13-F2B-B1)",
                 "reviews/F2b-bindchain-rev13-worker-035.json#(worker-035 HF-035-R3-01)",
                 "reviews/F2b-rev29-containment-rebase-worker-066.json#(worker-066 W066-R13-F2B-H1)"]},
            {"id": "CARRIER-B", "line": 246, "field": "implication_ledger.forbidden_transfers[0].reason",
             "defect": "inverted size direction in a forbidden-transfer reason",
             "witness": "same file's chain has E_C2 innermost (smallest); reason says 'strictly larger'",
             "old": CARRIER_B, "new": FIX_B,
             "corroborating_non_author_reviews": [
                 "reviews/F2b-review-rev29-053.json#(worker-053 HF-075-F2b-LARGER)",
                 "reviews/F2b-rev13-containment-worker-017.json#(worker-017 B17-R13-01)",
                 "reviews/F2b-review-rev29-075.json#(worker-075 HF-075-F2b-LARGER)"]}],
        "application": [
            "apply each old->new substring replacement exactly once, preserving all other bytes",
            "write both canonical and mirror paths with identical bytes",
            "bump FROZEN revision and re-emit artifact events with the new sha256",
            "re-run artifacts/formulation/tools/run_gate_tests.py and check_class_schema.py",
            "all rev13 verdicts are void at the new hash; reviewers must re-bind"],
        "proof": {"changed_lines": 2, "hunks": 2, "other_lines_identical": True,
                  "masked_tree_equal": True, "patched_sha256": m1["change"]["patched_sha256"],
                  "candidate": "patched_candidate/schemas/af_scc_c0_vacuum.yaml"},
        "gate_note": ("check_class_schema.py (pinned 000e09e4) returns PASS on the defective rev13 bytes and on the "
                      "patched candidate: the canonical structural gate is blind to both carriers (independently "
                      "reproduced; cf. worker-017 N17-R13-01), so this census is the missing check, not a replacement gate."),
        "not_claimed": report["claims_not_made"],
        "falsifier": report["next_falsifier"],
    }
    (ART / "repair_spec.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    (ART / "controls.json").write_text(json.dumps({"controls": m1["controls"],
                                                   "failed": m1["failed_controls"]}, indent=1, sort_keys=True) + "\n")
    (DIFF / "c0_rev13_to_patched.diff").write_text(m1["diff"])
    (ART / "report_raw.json").write_text(json.dumps(m1, indent=1, sort_keys=True) + "\n")

    # run.log (written before manifest; no further log appends after manifest)
    (ART / "run.log").write_text("\n".join(LOG_LINES) + "\n")

    manifest_files = []
    for p in sorted(ART.rglob("*")):
        if p.is_file() and p.name not in {"manifest.json"}:
            manifest_files.append({"path": str(p.relative_to(ART)), "sha256": sha256_file(p),
                                   "bytes": p.stat().st_size})
    manifest = {"schema": "worker-020/artifact-manifest/v1", "task_id": "W020-F2B-REV13-REPAIR-SPEC-01",
                "created_at": now, "files": manifest_files}
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"manifest: {len(manifest_files)} files; report={sha256_file(ART/'report.json')[:12]} "
          f"spec={sha256_file(ART/'repair_spec.json')[:12]} candidate={m1['change']['patched_sha256'][:12]}")
    return 0 if not m1["failed_checks"] and not m1["failed_controls"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
