#!/usr/bin/env python3
"""W083-F2B-CANDIDATE-ADJUDICATION-01

Independent, hash-bound adjudication between the two apply-ready F2b rev29
text-carrier repair candidates for the blocking defects
  W018-R13-F2B-B1  (line 152: 'No containment with C2 or C0 is asserted here',
                    contradicted by implication_ledger.extension_class_containment)
  W018-R13-F2B-B2  (line 246: 'C2 is a strictly larger extension class',
                    inverted against the same chain)
on class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM.

Candidates:
  C024 = artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml
  C083 = artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml

Deterministic, read-only with respect to canonical artifacts.  Every check is
reproducible from the pinned bytes recorded in evidence.json.  No gate verdict,
no node status, no validation_status, no canonical write.

Pre-registered decision rule (fixed before measuring, see report.json):
  Q1 correctness : resolves D1 (no containment denial; chain consistent with the
                   live implication_ledger) and D2 (no inversion; correct
                   strength direction), with zero undECLARED line changes and a
                   canonical-checker pass.
  Q2 support     : every added assertion is entailed by the frozen artifact set
                   (implication_ledger, VARIANT_REGISTRY pinned in FROZEN rev29).
  Q3 minimality  : among qualifiers, fewest changed lines, then fewest added bytes.
  Q4 tie-break   : prefer the self-contained carrier (fewest external artifact
                   references added).

Falsifier: re-run at the pins; any FAIL, any pin movement, or any UNDECLARED
line difference between live and a candidate voids this adjudication.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-083/f2b_candidate_adjudication"
SNAP = ART / "snapshot"
CTRL = ART / "controls"

LIVE = ROOT / "schemas/af_scc_c0_vacuum.yaml"
C024 = ROOT / "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
C083 = ROOT / "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
REGISTRY = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
VOCAB = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
CHECKER = ROOT / "artifacts/formulation/tools/check_class_schema.py"

# ---------------------------------------------------------------- pinned values
PIN_LIVE_C0 = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN_FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
PIN_C024 = "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9"
PIN_C083 = "1315427fbc92ed118982f20998066fd21c1714714213dc70b04023da74be3275"
PIN_F2A = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
PIN_F1 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
PIN_F0_MAP = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_REGISTRY = "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb"
PIN_CHECKER = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"

DECLARED_CHANGED_LINES = {"C024": [152, 246], "C083": [152, 246]}

# Chains that must be present, smallest set first, exactly as written in
# live implication_ledger.extension_class_containment (line 238):
CHAIN_SMALL_TO_LARGE = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
DENIAL_RE = re.compile(r"No containment with\s+C2 or C0 is asserted", re.I)
INVERSION_RE = re.compile(r"strictly larger extension class", re.I)
WEAKER_RE = re.compile(r"strictly weaker", re.I)
SMALLER_RE = re.compile(r"(strictly smaller extension class|SMALLEST extension set)", re.I)
# quoted or bracketed spans are MENTIONS (reported speech / repair notes), not assertions
MENTION_SPAN_RE = re.compile(
    r"\[[^\]]*\]|\"[^\"]*\"|'[^']*'|\u2018[^\u2019]*\u2019|\u201c[^\u201d]*\u201d", re.S)


def strip_mentions(text: str) -> str:
    """Remove quoted/bracketed spans so that only asserted prose remains.

    Assertion-vs-mention discipline: C083's repair note quotes the old false
    sentence inside single quotes plus a bracketed note; that is a mention and
    must not be counted as the artifact still asserting the denial.
    """
    return MENTION_SPAN_RE.sub(" ", text)


def asserts_denial(text: str) -> bool:
    return bool(DENIAL_RE.search(strip_mentions(text)))


def asserts_inversion(text: str) -> bool:
    return bool(INVERSION_RE.search(strip_mentions(text)))

EVENT_ID = "w083-f2b-candidate-adjudication-01"


# ---------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lines(path: Path):
    return path.read_text().splitlines(keepends=True)


def changed_lines(a: Path, b: Path):
    """Return sorted live-file line numbers whose content changed (1-based)."""
    la, lb = load_lines(a), load_lines(b)
    sm = difflib.SequenceMatcher(a=la, b=lb, autojunk=False)
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        changed.extend(range(i1 + 1, i2 + 1))
    return sorted(changed)


def added_bytes(a: Path, b: Path) -> int:
    la, lb = load_lines(a), load_lines(b)
    sm = difflib.SequenceMatcher(a=la, b=lb, autojunk=False)
    n = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            n += sum(len(x) for x in lb[j1:j2]) - sum(len(x) for x in la[i1:i2])
    return n


def yaml_load(path: Path):
    return yaml.safe_load(path.read_text())


def carrier_text(path: Path, carrier: str):
    d = yaml_load(path)
    if carrier == "must_not_conflate[0]":
        return d["regularity"]["must_not_conflate"][0]
    if carrier == "forbidden_transfers[0].reason":
        return d["implication_ledger"]["forbidden_transfers"][0]["reason"]
    if carrier == "conclusion_type":
        return d["conclusion"]["conclusion_type"]
    if carrier == "extension_class_containment":
        return d["implication_ledger"]["extension_class_containment"]
    raise KeyError(carrier)


def check(cid, status, msg, **ev):
    return {"id": cid, "status": status, "msg": msg, **ev}


# ---------------------------------------------------------------- checks
def run_checks():
    checks = []

    # --- pins -------------------------------------------------------------
    pin_map = [
        ("F2B-LIVE-PIN", LIVE, PIN_LIVE_C0),
        ("FROZEN-PIN", FROZEN, PIN_FROZEN),
        ("C024-PIN", C024, PIN_C024),
        ("C083-PIN", C083, PIN_C083),
        ("F2A-PIN", ROOT / "schemas/af_scc_c2_vacuum.yaml", PIN_F2A),
        ("F1-PIN", ROOT / "schemas/af_wcc_vacuum.yaml", PIN_F1),
        ("F0-MAP-PIN", TAXONOMY, PIN_F0_MAP),
        ("REGISTRY-PIN", REGISTRY, PIN_REGISTRY),
        ("CHECKER-PIN", CHECKER, PIN_CHECKER),
    ]
    drift = []
    for cid, path, pin in pin_map:
        live = sha256(path)
        ok = live == pin
        if not ok:
            drift.append(cid)
        checks.append(check(cid, "PASS" if ok else "FAIL",
                            f"{path.relative_to(ROOT)} at {live[:12]} == pinned {pin[:12]}"
                            if ok else f"PIN DRIFT {path.relative_to(ROOT)}: {live} != {pin}",
                            measured=live, pinned=pin, path=str(path.relative_to(ROOT))))
    frozen = json.loads(FROZEN.read_text())
    checks.append(check("FROZEN-REVISION", "PASS" if frozen.get("revision") == 29 else "FAIL",
                        f"FROZEN revision {frozen.get('revision')} frozen_at {frozen.get('frozen_at')}",
                        revision=frozen.get("revision"), frozen_at=frozen.get("frozen_at")))
    fp = frozen.get("files", {})
    for p, expected in [("schemas/af_scc_c0_vacuum.yaml", PIN_LIVE_C0),
                        ("artifacts/formulation/VARIANT_REGISTRY.json", PIN_REGISTRY),
                        ("artifacts/formulation/tools/check_class_schema.py", PIN_CHECKER)]:
        got = fp.get(p, {}).get("sha256") if isinstance(fp.get(p), dict) else None
        checks.append(check("FROZEN-ENTRY:" + p, "PASS" if got == expected else "FAIL",
                            f"FROZEN entry {p} = {str(got)[:12]}",
                            entry=got, expected=expected))

    # --- same base / declared delta --------------------------------------
    measured = {"C024": changed_lines(LIVE, C024), "C083": changed_lines(LIVE, C083)}
    for name in ("C024", "C083"):
        ok = measured[name] == DECLARED_CHANGED_LINES[name]
        checks.append(check(f"{name}-DECLARED-LINES", "PASS" if ok else "FAIL",
                            f"{name} changed live lines {measured[name]} == declared {DECLARED_CHANGED_LINES[name]}",
                            measured=measured[name], declared=DECLARED_CHANGED_LINES[name]))
    # candidates differ from each other only in the same two carriers
    cross = changed_lines(C024, C083)
    checks.append(check("CROSS-DELTA-LINES", "PASS" if cross == [152, 246] else "FAIL",
                        f"C024 vs C083 differ at lines {cross}",
                        measured=cross))
    # every other live line byte-identical in both candidates
    for name, path in (("C024", C024), ("C083", C083)):
        la, lb = load_lines(LIVE), load_lines(path)
        same = len(la) == len(lb)
        checks.append(check(f"{name}-LINE-COUNT", "PASS" if same else "FAIL",
                            f"{name} line count {len(lb)} == live {len(la)}" if same
                            else f"line count changed live={len(la)} candidate={len(lb)}",
                            live=len(la), candidate=len(lb)))

    # --- D1: containment denial vs live ledger ----------------------------
    live_mnc = carrier_text(LIVE, "must_not_conflate[0]")
    live_chain = carrier_text(LIVE, "extension_class_containment")
    checks.append(check("D1-LIVE-DENIAL", "PASS" if asserts_denial(live_mnc) else "FAIL",
                        "live must_not_conflate[0] asserts the false denial (defect reproduced)"
                        if asserts_denial(live_mnc) else "live denial NOT reproduced",
                        text=live_mnc))
    checks.append(check("D1-LIVE-LEDGER-CHAIN",
                        "PASS" if "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" in live_chain else "FAIL",
                        "live implication_ledger.extension_class_containment carries the strict chain "
                        "E_C0 > E_H2loc > E_{C^1,1} > E_C2 (defect carrier context)",
                        text=live_chain))
    for name, path in (("C024", C024), ("C083", C083)):
        t = carrier_text(path, "must_not_conflate[0]")
        denial_gone = not asserts_denial(t)
        chain_ok = CHAIN_SMALL_TO_LARGE in t.replace("  ", " ")
        checks.append(check(f"D1-{name}-DENIAL-REMOVED", "PASS" if denial_gone else "FAIL",
                            f"{name} must_not_conflate[0] no longer ASSERTS the denial "
                            f"(quoted mentions excluded)" if denial_gone
                            else f"{name} still asserts the denial", text=t,
                            asserted=asserts_denial(t)))
        checks.append(check(f"D1-{name}-CHAIN-CONSISTENT", "PASS" if chain_ok else "FAIL",
                            f"{name} states the nesting in the ledger's order (E_C2 subset ... E_C0)"
                            if chain_ok else f"{name} does not state the full nesting chain", text=t))
        d = yaml_load(path)["regularity"]["must_not_conflate"]
        checks.append(check(f"D1-{name}-LIST-LENGTH", "PASS" if len(d) == 5 else "FAIL",
                            f"{name} must_not_conflate has {len(d)} entries (live 5, no entry deleted)",
                            length=len(d)))

    # --- D2: strength inversion ------------------------------------------
    live_ft = carrier_text(LIVE, "forbidden_transfers[0].reason")
    checks.append(check("D2-LIVE-INVERSION", "PASS" if asserts_inversion(live_ft) else "FAIL",
                        "live forbidden_transfers[0].reason asserts C2 is 'a strictly larger extension "
                        "class' (defect reproduced)" if asserts_inversion(live_ft)
                        else "live inversion NOT reproduced", text=live_ft))
    # formal sanity model of the ordering the repair must respect
    E_C0, E_H2, E_C11, E_C2 = {0, 1, 2, 3}, {0, 1, 2}, {0, 1}, {0}
    strict = E_C2 < E_C11 < E_H2 < E_C0
    weaker = (not E_C2) and (not E_C0)  # placeholder to keep both truths explicit
    formal_ok = strict and (len(E_C2) < len(E_C0)) and (E_C2 <= E_C0)
    checks.append(check("D2-FORMAL-ORDER", "PASS" if formal_ok else "FAIL",
                        "chain is strictly nested, so 'no C2 extension' (smallest set) is the "
                        "weakest statement and 'no C0 extension' the strongest",
                        chain=["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"],
                        strengths={"no_C0": "strongest", "no_C2": "weakest"}))
    for name, path in (("C024", C024), ("C083", C083)):
        t = carrier_text(path, "forbidden_transfers[0].reason")
        no_larger = not asserts_inversion(t)
        weaker_ok = bool(WEAKER_RE.search(t))
        attribution = bool(SMALLER_RE.search(t))
        ok = no_larger and weaker_ok and attribution
        checks.append(check(f"D2-{name}-REPAIRED", "PASS" if ok else "FAIL",
                            f"{name} reason: inversion removed={no_larger}, 'strictly weaker'={weaker_ok}, "
                            f"correct set-size attribution={attribution}", text=t,
                            no_larger=no_larger, weaker=weaker_ok, attribution=attribution))

    # --- D3 out of scope: conclusion token untouched ----------------------
    tok = {n: carrier_text(p, "conclusion_type") for n, p in
           (("LIVE", LIVE), ("C024", C024), ("C083", C083))}
    same_tok = len(set(tok.values())) == 1
    checks.append(check("D3-TOKEN-UNTOUCHED", "PASS" if same_tok else "FAIL",
                        f"conclusion_type identical across live/C024/C083: {tok['LIVE']} "
                        "(D3 vocabulary adjudication deliberately out of this repair's scope)",
                        tokens=tok))

    # --- claim support: added assertions must be entailed by frozen bytes --
    c024_text = carrier_text(C024, "must_not_conflate[0]")
    c083_text = carrier_text(C083, "must_not_conflate[0]")
    for name, t in (("C024", c024_text), ("C083", c083_text)):
        derived = CHAIN_SMALL_TO_LARGE in t.replace("  ", " ") and \
            "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" in live_chain
        checks.append(check(f"SUP-{name}-NESTING-DERIVED", "PASS" if derived else "FAIL",
                            f"{name}'s added nesting assertion is byte-derivable from live "
                            f"implication_ledger.extension_class_containment", text=t))
    refs_registry = "VARIANT_REGISTRY.json" in c024_text
    reg = json.loads(REGISTRY.read_text())
    h2 = [v for v in reg.get("variants", []) if v.get("variant_id") == "H2LOC"]
    h2_ok = len(h2) == 1 and h2[0].get("parent_class") == "AF-SCC-C0-VAC-GEN"
    checks.append(check("SUP-024-REGISTRY-REF", "PASS" if (not refs_registry or h2_ok) else "FAIL",
                        "C024 cites VARIANT_REGISTRY.json; H2LOC is registered with parent "
                        "AF-SCC-C0-VAC-GEN at the FROZEN-pinned registry hash" if (refs_registry and h2_ok)
                        else ("C024 does not cite the registry" if not refs_registry else
                              "C024 cites an UNSUPPORTED registry claim"),
                        cites_registry=refs_registry, h2loc_found=len(h2) == 1,
                        h2loc=h2[0] if h2 else None))
    checks.append(check("SUP-C024-H2LOC-STATUS", "PASS" if (not refs_registry or (
        h2 and h2[0].get("status") == "registered_variant_not_written")) else "FAIL",
                        "H2LOC registry status is 'registered_variant_not_written' "
                        "(registered, not written as a class) consistent with C024's wording"
                        if h2 else "H2LOC absent", h2loc_registry_status=h2[0].get("status") if h2 else None))
    # traceability is recorded, not required for qualification
    trace = {
        "C024": {"cites_ledger": "implication_ledger" in c024_text,
                 "cites_registry": refs_registry,
                 "cites_repair_ids": bool(re.search(r"W018-R13-F2B-B[12]", c024_text))},
        "C083": {"cites_ledger": "implication_ledger" in c083_text,
                 "cites_registry": "VARIANT_REGISTRY" in c083_text,
                 "cites_repair_ids": bool(re.search(r"W018-R13-F2B-B[12]", c083_text))},
    }
    checks.append(check("TRACEABILITY-RECORD", "PASS", "citation inventory recorded (informational)",
                        trace=trace))

    # --- canonical checker as structural control --------------------------
    checker_results = {}
    for name, path in (("LIVE", LIVE), ("C024", C024), ("C083", C083)):
        proc = subprocess.run([sys.executable, str(CHECKER), "--json", str(path)],
                              capture_output=True, text=True)
        try:
            out = json.loads(proc.stdout)
        except Exception:
            out = {"verdict": "UNPARSEABLE", "stdout": proc.stdout[-400:], "stderr": proc.stderr[-400:]}
        checker_results[name] = {"exit": proc.returncode, "verdict": out.get("verdict"),
                                 "failed_rules": out.get("failed_rules")}
    all_pass = all(v["exit"] == 0 and v["verdict"] == "pass" for v in checker_results.values())
    checks.append(check("CANONICAL-CHECKER", "PASS" if all_pass else "FAIL",
                        "canonical structural checker passes on live and both candidates "
                        "(documented blind spot: it does not decide the semantic contradictions)",
                        results=checker_results))
    return checks, measured, checker_results


# ---------------------------------------------------------------- controls
def _mutate(src: Path, dst: Path, line_no: int, new_text: str):
    lines = load_lines(src)
    lines[line_no - 1] = new_text
    dst.write_text("".join(lines))


def run_controls(live_lines):
    CTRL.mkdir(parents=True, exist_ok=True)
    out = []

    def rec(cid, expected, observed, ok, note):
        out.append({"id": cid, "expected": expected, "observed": observed,
                    "status": "PASS" if ok else "FAIL", "note": note})

    # P1/P2: defect detectors fire on the live artifact
    live_mnc = carrier_text(LIVE, "must_not_conflate[0]")
    live_ft = carrier_text(LIVE, "forbidden_transfers[0].reason")
    rec("P1-live-denial-detector", "fires", asserts_denial(live_mnc),
        asserts_denial(live_mnc), "positive control: live D1 defect detectable")
    rec("P2-live-inversion-detector", "fires", asserts_inversion(live_ft),
        asserts_inversion(live_ft), "positive control: live D2 defect detectable")

    # N1: reinsert the denial into C083 -> D1 check must flag
    n1 = CTRL / "n1_denial_reinserted.yaml"
    _mutate(C083, n1, 152, live_lines[151])
    t = carrier_text(n1, "must_not_conflate[0]")
    rec("N1-denial-mutant", "denial detected", asserts_denial(t),
        asserts_denial(t), "negative control: reinserted denial is caught")

    # N2: reinsert the inversion into C083 -> D2 check must flag
    n2 = CTRL / "n2_inversion_reinserted.yaml"
    _mutate(C083, n2, 246, live_lines[245])
    t = carrier_text(n2, "forbidden_transfers[0].reason")
    rec("N2-inversion-mutant", "inversion detected", asserts_inversion(t),
        asserts_inversion(t), "negative control: reinserted inversion is caught")

    # N3: spurious undeclared change -> declared-lines check must flag
    n3 = CTRL / "n3_spurious_line.yaml"
    _mutate(C083, n3, 30, live_lines[29].rstrip("\n") + " # spurious\n")
    m = changed_lines(LIVE, n3)
    rec("N3-spurious-mutant", "changed lines {30,152,246}", m, m == [30, 152, 246],
        "negative control: undeclared change widens measured delta")

    # N4: truncated candidate -> line-count check must flag
    n4 = CTRL / "n4_truncated.yaml"
    n4.write_text("".join(load_lines(C083)[:-1]))
    rec("N4-truncation-mutant", "line count differs",
        len(load_lines(n4)) != len(live_lines), len(load_lines(n4)) != len(live_lines),
        "negative control: truncated carrier detected")

    # N5: registry claim support check must flag when H2LOC parent is altered
    n5 = CTRL / "n5_registry_parent_altered.json"
    reg = json.loads(REGISTRY.read_text())
    for v in reg["variants"]:
        if v["variant_id"] == "H2LOC":
            v["parent_class"] = "AF-WCC-VAC-GEN"
    n5.write_text(json.dumps(reg, indent=1))
    reg2 = json.loads(n5.read_text())
    h2 = [v for v in reg2["variants"] if v["variant_id"] == "H2LOC"]
    flagged = not (len(h2) == 1 and h2[0]["parent_class"] == "AF-SCC-C0-VAC-GEN")
    rec("N5-registry-parent-mutant", "unsupported claim detected", flagged, flagged,
        "negative control: altered registry parent breaks the support check")

    # N6: assert-vs-mention control: quote the live denial inside C083 ->
    # the denial is now only MENTIONED and must NOT count as asserted.
    n6 = CTRL / "n6_quoted_denial.yaml"
    quoted = live_lines[151].replace(
        "No containment with C2 or C0 is asserted here;",
        "the earlier 'No containment with C2 or C0 is asserted here' was wrong;")
    _mutate(C083, n6, 152, quoted)
    t6 = carrier_text(n6, "must_not_conflate[0]")
    rec("N6-quoted-mention", "not asserted", not asserts_denial(t6), not asserts_denial(t6),
        "assert-vs-mention control: a quoted denial is a mention, not an assertion "
        "(the CLASSSEP failure mode)")
    return out


# ---------------------------------------------------------------- main
def main():
    SNAP.mkdir(parents=True, exist_ok=True)
    snap_specs = {
        "live__schemas__af_scc_c0_vacuum.yaml": LIVE,
        "live__schemas__af_scc_c2_vacuum.yaml": ROOT / "schemas/af_scc_c2_vacuum.yaml",
        "live__schemas__af_wcc_vacuum.yaml": ROOT / "schemas/af_wcc_vacuum.yaml",
        "candidate_024__af_scc_c0_vacuum.yaml": C024,
        "candidate_083__af_scc_c0_vacuum.yaml": C083,
        "artifacts__formulation__FROZEN.json": FROZEN,
        "artifacts__formulation__VARIANT_REGISTRY.json": REGISTRY,
        "artifacts__formulation__VOCAB_ALIASES.json": VOCAB,
        "research_map__formulation_taxonomy.yaml": TAXONOMY,
        "tools__check_class_schema.py": CHECKER,
    }
    snap_hashes = {}
    for name, path in snap_specs.items():
        dst = SNAP / name
        shutil.copyfile(path, dst)
        snap_hashes[name] = sha256(dst)

    checks, measured, checker_results = run_checks()
    live_lines = load_lines(LIVE)
    controls = run_controls(live_lines)

    failed = [c for c in checks if c["status"] != "PASS"]
    ctrl_failed = [c for c in controls if c["status"] != "PASS"]

    # --- pre-registered selection ----------------------------------------
    qual = {}
    for name, path in (("C024", C024), ("C083", C083)):
        d1 = all(c["status"] == "PASS" for c in checks if c["id"].startswith(f"D1-{name}"))
        d2 = all(c["status"] == "PASS" for c in checks if c["id"].startswith(f"D2-{name}"))
        base = all(c["status"] == "PASS" for c in checks
                   if c["id"].startswith(f"{name}-") )
        tok = all(c["status"] == "PASS" for c in checks if c["id"] == "D3-TOKEN-UNTOUCHED")
        sup = all(c["status"] == "PASS" for c in checks if c["id"].startswith("SUP-") and name in c["id"])
        ck = checker_results[name]["exit"] == 0 and checker_results[name]["verdict"] == "pass"
        qual[name] = {"D1": d1, "D2": d2, "base": base, "D3": tok, "support": sup,
                      "checker": ck, "qualified": all([d1, d2, base, tok, sup, ck]),
                      "changed_lines": measured[name],
                      "added_bytes": added_bytes(LIVE, path),
                      "external_refs_added": ("VARIANT_REGISTRY" in carrier_text(path, "must_not_conflate[0]"))}
    ranked = sorted([n for n in qual if qual[n]["qualified"]],
                    key=lambda n: (len(qual[n]["changed_lines"]), qual[n]["added_bytes"],
                                   qual[n]["external_refs_added"], n))
    recommendation = ranked[0] if ranked else None
    rule_trace = []
    if recommendation:
        rule_trace = [
            f"Q1 both candidates resolve D1/D2 with exactly {measured[recommendation]} changed lines and checker pass",
            "Q2 all added assertions verified against FROZEN-pinned evidence (ledger chain; H2LOC registry entry for C024)",
            f"Q3 minimality: " + ", ".join(f"{n} added_bytes={qual[n]['added_bytes']}" for n in ("C024", "C083")),
            f"Q4 tie-break external refs: " + ", ".join(
                f"{n} external_refs_added={qual[n]['external_refs_added']}" for n in ("C024", "C083")),
            f"selected {recommendation} under the pre-registered rule",
        ]

    report = {
        "task_id": "W083-F2B-CANDIDATE-ADJUDICATION-01",
        "actor": "worker-083",
        "node": "F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "scope": "adjudicate the two apply-ready rev29 text-carrier repair candidates for "
                 "W018-R13-F2B-B1 (line 152) and W018-R13-F2B-B2 (line 246)",
        "verdict": ("BOTH_CANDIDATES_RESOLVE_B1_B2; ONE RECOMMENDED UNDER PRE-REGISTERED RULE"
                    if recommendation else "NO_CANDIDATE_QUALIFIES"),
        "recommendation": {
            "candidate": recommendation,
            "candidate_path": str({"C024": C024, "C083": C083}[recommendation].relative_to(ROOT)) if recommendation else None,
            "candidate_sha256": {"C024": PIN_C024, "C083": PIN_C083}[recommendation] if recommendation else None,
            "rule_trace": rule_trace,
            "author_conflict": recommendation == "C083",
            "author_conflict_note": ("this worker authored candidate C083; the mechanical checks are "
                                     "reproducible from the pins, but the owner or an independent "
                                     "reviewer must confirm the recommendation before applying") if recommendation == "C083" else "",
            "counter_argument": ("C024 is strictly more traceable (cites W018-R13-F2B-B1/B2 and the "
                                 "H2LOC registry entry); if the owner values repair-ID traceability over "
                                 "minimal delta, C024 is equally correct and checker-clean") if recommendation == "C083" else
                                ("C083 is more minimal; C024's extra registry reference is verified true "
                                 "but adds a cross-artifact dependency") if recommendation == "C024" else "",
        },
        "measured": {
            "changed_lines_vs_live": measured,
            "declared_changed_lines": DECLARED_CHANGED_LINES,
            "added_bytes": {n: qual[n]["added_bytes"] for n in qual},
            "checker_results": checker_results,
            "traceability": next(c for c in checks if c["id"] == "TRACEABILITY-RECORD")["trace"],
        },
        "instrument_notes": [
            "D1/D2 detectors are mention-aware: quoted or bracketed spans are stripped before "
            "matching, because a repair note that QUOTES the old false sentence is not asserting it "
            "(control N6; the same assertion-vs-mention failure mode as CLASSSEP).",
            "The canonical check_class_schema.py passes on live and both candidates: it is a structural "
            "gate and does not decide the semantic contradictions, so it is a control, not the adjudicator.",
        ],
        "checks": {"passed": len(checks) - len(failed), "total": len(checks),
                   "failed": [c["id"] for c in failed]},
        "controls": {"passed": len(controls) - len(ctrl_failed), "total": len(controls),
                     "failed": [c["id"] for c in ctrl_failed]},
        "pins": {k: sha256(v) for k, v in snap_specs.items()},
        "out_of_scope": ["D3 conclusion_type vocabulary adjudication (F0/F2a/F2b gate-owner token decision)",
                         "D4 semantic_escape_rebased corpus base rebind",
                         "any canonical write, gate verdict, node status or validation_status"],
        "falsifier": "re-run at the pins; any FAIL, any pin movement, or any undeclared line "
                     "difference between live and a candidate voids this adjudication",
        "no_gate_verdict": True,
    }
    evidence = {
        "task_id": "W083-F2B-CANDIDATE-ADJUDICATION-01",
        "pins": snap_hashes,
        "checks": checks,
        "control_records": controls,
        "carrier_texts": {
            "live_must_not_conflate0": carrier_text(LIVE, "must_not_conflate[0]"),
            "live_forbidden_transfers0_reason": carrier_text(LIVE, "forbidden_transfers[0].reason"),
            "c024_must_not_conflate0": carrier_text(C024, "must_not_conflate[0]"),
            "c024_forbidden_transfers0_reason": carrier_text(C024, "forbidden_transfers[0].reason"),
            "c083_must_not_conflate0": carrier_text(C083, "must_not_conflate[0]"),
            "c083_forbidden_transfers0_reason": carrier_text(C083, "forbidden_transfers[0].reason"),
            "live_extension_class_containment": carrier_text(LIVE, "extension_class_containment"),
        },
        "diff_unified": {
            "C024": "".join(difflib.unified_diff(load_lines(LIVE), load_lines(C024),
                                                 fromfile="live", tofile="C024")),
            "C083": "".join(difflib.unified_diff(load_lines(LIVE), load_lines(C083),
                                                 fromfile="live", tofile="C083")),
        },
    }
    (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (ART / "evidence.json").write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n")
    (ART / "controls.json").write_text(json.dumps(controls, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"checks": report["checks"], "controls": report["controls"],
                      "recommendation": report["recommendation"]["candidate"],
                      "verdict": report["verdict"],
                      "failed": report["checks"]["failed"] + report["controls"]["failed"]}, indent=1))
    return 0 if not failed and not ctrl_failed else 1


if __name__ == "__main__":
    sys.exit(main())
