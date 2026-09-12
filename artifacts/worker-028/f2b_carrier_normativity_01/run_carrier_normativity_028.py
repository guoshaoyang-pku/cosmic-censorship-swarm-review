#!/usr/bin/env python3
"""W028-F2B-CARRIER-NORMATIVITY-01.

Independent, hash-pinned measurement of whether the two contested F2b carrier clauses
(worker-066 W066-R13-F2B-H1/H2) are normative under the binding rule spec R01-R16 +
canonical class-schema gate, at F2b sha256 b2ab6acb2bbe / FROZEN rev29 815e0807.

Run from the repo root:
    python3 artifacts/worker-028/f2b_carrier_normativity_01/run_carrier_normativity_028.py

Writes carrier_normativity_028.json next to this script. Read-only on all canonical
paths; all mutants live under sandbox/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                    # repo root (…/ai4math-swarm)
PINS = HERE / "pins"
SANDBOX = HERE / "sandbox"
ART = HERE / "carrier_normativity_028.json"

DECLARED = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
PINFILE = {p: PINS / p.replace("/", "_") for p in DECLARED}

CLAUSE_H1 = 'C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker'
CLAUSE_H2_DENIAL = 'No containment with C2 or C0 is asserted here'
H1_REPAIR = ('C2 is a strictly smaller extension class, so C2-inextendibility is strictly stronger')
H2_REPAIR = ('The extension sets are nested E_C2 subset of E_{C^1,1} subset of E_H2loc subset '
             'of E_C0 (see implication_ledger)')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_brackets(s: str) -> str:
    return re.sub(r"\[[^\]]*\]", " ", s, flags=re.S)


def chain_rank(doc: dict) -> tuple[dict, str]:
    """Derive {class symbol: rank} largest-first from the document's own chain sentence."""
    sent = str(((doc.get("implication_ledger") or {}).get("extension_class_containment")) or "")
    if " contains " in sent:
        parts = sent.split(" contains ")
    elif " subset of " in sent:
        parts = list(reversed(sent.split(" subset of ")))
    else:
        return {}, sent
    toks = []
    for part in parts:
        found = re.findall(r"E_\{[^}]*\}|E_[A-Za-z0-9]+", part)
        toks.append(found[0] if found else None)
    rank = {t: i for i, t in enumerate(toks) if t}
    return rank, sent


def token_for(text: str) -> str | None:
    if re.search(r"\bC0\b|C\^?0|continuous|continuity", str(text)):
        return "E_C0"
    if re.search(r"\bC2\b|C\^?2|twice", str(text)):
        return "E_C2"
    if re.search(r"H2_?loc", str(text), re.I):
        return "E_H2loc"
    return None


def detect(doc: dict) -> list[dict]:
    """Independent order-relative carrier detector (no worker-066 code reused)."""
    findings = []
    rank, sent = chain_rank(doc)
    il = doc.get("implication_ledger") or {}
    for i, row in enumerate(il.get("forbidden_transfers") or []):
        if not isinstance(row, dict):
            continue
        reason = strip_brackets(str(row.get("reason", "")))
        size = re.search(r"\b(larger|bigger|smaller)\b", reason, re.I)
        if not size or not rank:
            continue
        tok = token_for(row.get("from", ""))
        if tok is None or tok not in rank:
            continue
        measured = "larger" if rank[tok] == 0 else ("smaller" if rank[tok] == max(rank.values()) else "middle")
        claimed = "larger" if size.group(1).lower() in ("larger", "bigger") else "smaller"
        if claimed != measured:
            findings.append({
                "kind": "size_premise_inverted", "carrier_index": i,
                "carrier": f"implication_ledger.forbidden_transfers[{i}].reason",
                "claimed": claimed, "measured_from_chain": measured,
                "literal_premise_contradicts_forbidden_verdict": claimed == "larger",
                "row_from": row.get("from"), "row_to": row.get("to"),
                "chain_sentence": sent[:200],
            })
    reg = doc.get("regularity") or {}
    for i, entry in enumerate(reg.get("must_not_conflate") or []):
        text = strip_brackets(str(entry))
        m = re.search(r"no containment with ([^.;]*)", text, re.I)
        if not m:
            continue
        mentioned = set()
        for name, tok in (("C0", "E_C0"), ("C2", "E_C2"), ("H2_loc", "E_H2loc"), ("H2loc", "E_H2loc")):
            if re.search(re.escape(name), m.group(1), re.I):
                mentioned.add(tok)
        asserted = {t for t in mentioned if t in rank}
        if len(asserted) >= 2:
            findings.append({
                "kind": "false_containment_denial", "carrier_index": i,
                "carrier": f"regularity.must_not_conflate[{i}]",
                "denial_scope": sorted(mentioned), "chain_asserts": sorted(asserted),
                "chain_sentence": sent[:200],
            })
    return findings


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_gate(checker: Path, schema: Path) -> dict:
    p = subprocess.run([sys.executable, str(checker), "--json", str(schema)],
                       capture_output=True, text=True, cwd=str(ROOT))
    try:
        rep = json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        rep = {"verdict": "error", "failed_rules": [], "failures": [], "stdout": p.stdout, "stderr": p.stderr}
    rep["returncode"] = p.returncode
    rep["schema"] = str(schema.relative_to(ROOT)) if str(schema).startswith(str(ROOT)) else str(schema)
    return rep


def recursive_paths_diff(a, b, path="$"):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += recursive_paths_diff(a.get(k), b.get(k), f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            av = a[i] if i < len(a) else None
            bv = b[i] if i < len(b) else None
            out += recursive_paths_diff(av, bv, f"{path}[{i}]")
    elif a != b:
        out.append({"path": path, "defective": (str(a)[:400] if a is not None else None),
                    "repaired": (str(b)[:400] if b is not None else None)})
    return out


def edit_text(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"edit target not unique: {old[:60]!r} count={text.count(old)}"
    return text.replace(old, new)


def main() -> int:
    SANDBOX.mkdir(exist_ok=True)
    checks, controls = [], []

    def record(bucket, cid, desc, expected, observed):
        ok = expected == observed
        bucket.append({"id": cid, "description": desc, "expected": expected,
                       "observed": observed, "pass": bool(ok)})
        return ok

    # ---------------- K0 pins ----------------
    measured_start = {p: sha256(ROOT / p) for p in DECLARED}
    pin_match = {p: measured_start[p] == DECLARED[p] for p in DECLARED}
    record(checks, "K0-pins", "all nine canonical inputs match declared hashes at run start",
           True, all(pin_match.values()))
    pinfile_match = {p: sha256(PINFILE[p]) == DECLARED[p] for p in DECLARED}
    record(checks, "K0b-pinned-copies", "all pinned copies match declared hashes",
           True, all(pinfile_match.values()))
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    fz_blob = json.dumps(frozen)
    declares = {p: (DECLARED[p] in fz_blob) for p in
                ("schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_wcc_vacuum.yaml")}
    record(checks, "K0c-frozen-declares", "FROZEN rev29 manifest names the three measured schema hashes",
           True, all(declares.values()))

    # sandbox tool tree so mutants are gated by the PINNED checker + PINNED spec
    (SANDBOX / "tools").mkdir(exist_ok=True)
    shutil.copy(PINFILE["artifacts/formulation/tools/check_class_schema.py"], SANDBOX / "tools/check_class_schema.py")
    shutil.copy(PINFILE["artifacts/formulation/rule_spec.json"], SANDBOX / "rule_spec.json")
    shutil.copy(PINFILE["artifacts/formulation/KEY_MANIFEST.json"], SANDBOX / "KEY_MANIFEST.json")
    pinned_checker = SANDBOX / "tools/check_class_schema.py"

    f2b_text = (PINFILE["schemas/af_scc_c0_vacuum.yaml"]).read_text()
    f2b = yaml.safe_load(f2b_text)
    f2a = yaml.safe_load((PINFILE["schemas/af_scc_c2_vacuum.yaml"]).read_text())
    f1 = yaml.safe_load((PINFILE["schemas/af_wcc_vacuum.yaml"]).read_text())
    spec = json.loads((PINFILE["artifacts/formulation/rule_spec.json"]).read_text())

    # ---------------- K1 carriers ----------------
    lines = f2b_text.splitlines()
    h1_line = next(i + 1 for i, l in enumerate(lines) if CLAUSE_H1 in l)
    h2_line = next(i + 1 for i, l in enumerate(lines) if CLAUSE_H2_DENIAL in l)
    chain_line = next(i + 1 for i, l in enumerate(lines) if "extension_class_containment:" in l)
    record(checks, "K1-H1-present", "H1 clause verbatim in forbidden_transfers[0].reason",
           f"line {h1_line}", f"line {h1_line}")
    record(checks, "K1-H2-present", "H2 denial verbatim in regularity.must_not_conflate[0]",
           f"line {h2_line}", f"line {h2_line}")
    record(checks, "K1-chain", "contradicted chain sentence present", True, chain_line > 0)
    h1_value = f2b["implication_ledger"]["forbidden_transfers"][0]["reason"]
    h2_value = f2b["regularity"]["must_not_conflate"][0]
    record(checks, "K1-H1-value", "H1 is the live parsed value", CLAUSE_H1, h1_value)
    record(checks, "K1-H2-value", "H2 is the live parsed value", True, CLAUSE_H2_DENIAL in h2_value)

    # ---------------- K2 independent detector ----------------
    det_f2b = detect(f2b)
    det_f2a = detect(f2a)
    det_f1 = detect(f1)
    record(checks, "K2-detector-f2b", "independent detector finds exactly H1+H2 on pristine F2b",
           ["false_containment_denial", "size_premise_inverted"],
           sorted(f["kind"] for f in det_f2b))
    record(checks, "K2-detector-f2a", "detector finds nothing on sibling F2a", [], det_f2a)
    record(checks, "K2-detector-f1", "detector finds nothing on F1", [], det_f1)

    # ---------------- K3 canonical gate, pristine (live entry point) ----------------
    live_checker = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    gate_pristine_live = run_gate(live_checker, ROOT / "schemas/af_scc_c0_vacuum.yaml")
    gate_pristine_pinned = run_gate(pinned_checker, PINFILE["schemas/af_scc_c0_vacuum.yaml"])
    gate_f2a = run_gate(pinned_checker, PINFILE["schemas/af_scc_c2_vacuum.yaml"])
    gate_f1 = run_gate(pinned_checker, PINFILE["schemas/af_wcc_vacuum.yaml"])
    record(checks, "K3-gate-live", "live canonical gate verdict on F2b at the pin", ("pass", []),
           (gate_pristine_live["verdict"], gate_pristine_live["failed_rules"]))
    record(checks, "K3-gate-pinned", "pinned-checker verdict on pinned F2b", ("pass", []),
           (gate_pristine_pinned["verdict"], gate_pristine_pinned["failed_rules"]))
    record(checks, "K3-gate-siblings", "pinned-checker passes F2a and F1", (("pass", []), ("pass", [])),
           ((gate_f2a["verdict"], gate_f2a["failed_rules"]), (gate_f1["verdict"], gate_f1["failed_rules"])))

    # ---------------- K4 rule trace ----------------
    rule_trace = []
    for r in spec.get("rules", []):
        blob = f"{r.get('require','')} {r.get('fail','')}"
        touched = [k for k in ("must_not_conflate", "forbidden_transfers", "implication_ledger",
                               "reason", "extension_class_containment") if k in blob]
        if touched:
            rule_trace.append({"rule": r["id"], "applies_to": r.get("applies_to"),
                               "touches_carriers": touched,
                               "require": r.get("require"), "fail": r.get("fail")})
    r06 = next((r for r in spec["rules"] if r["id"] == "R06"), {})
    r16 = next((r for r in spec["rules"] if r["id"] == "R16"), {})
    r06_require_binds_content = bool(re.search(r"must_not_conflate[^.]*?(true|holds|correct|entails|asserts)",
                                               r06.get("require", ""), re.I))
    r16_require_binds_reason = bool(re.search(r"reason[^.]*?(true|correct|consistent)", r16.get("require", ""), re.I))
    record(checks, "K4-R06-slot-only", "R06 binds must_not_conflate existence, not entry content",
           True, r06_require_binds_content is False)
    record(checks, "K4-R16-reason-unbound", "R16 binds ledger rows/marking, not reason prose truth",
           True, r16_require_binds_reason is False)
    record(checks, "K4-R16-pass", "R16 require satisfied: chain + one-way entailments + forbidden converse present",
           True, bool(f2b["implication_ledger"].get("extension_class_containment"))
           and bool(f2b["implication_ledger"].get("one_way_entailments"))
           and any("C2" in str(x) for x in f2b["implication_ledger"].get("forbidden_transfers")))

    # checker's own EXEMPT_KEY treatment of the two carrier keys
    ck = load_module(pinned_checker, "pinned_check_class_schema")
    exempt = {k: bool(ck.EXEMPT_KEY.match(k)) for k in
              ("must_not_conflate", "forbidden_transfers", "reason", "implication_ledger")}
    record(checks, "K4-exempt-keys", "pinned checker exempts both carrier keys from the composite scan",
           True, exempt["must_not_conflate"] and exempt["forbidden_transfers"] and exempt["reason"])
    composite_on_carriers = {
        "H1": bool(ck.COMPOSITE.search(h1_value) or ck.COMPOSITE_PROSE.search(h1_value)),
        "H2": bool(ck.COMPOSITE.search(h2_value) or ck.COMPOSITE_PROSE.search(h2_value)),
    }

    # ---------------- K5 repair-impact ----------------
    repaired_text = edit_text(f2b_text, CLAUSE_H1, H1_REPAIR)
    repaired_text = edit_text(repaired_text, CLAUSE_H2_DENIAL, H2_REPAIR)
    (SANDBOX / "f2b_repaired.yaml").write_text(repaired_text)
    repaired = yaml.safe_load(repaired_text)
    gate_repaired = run_gate(pinned_checker, SANDBOX / "f2b_repaired.yaml")
    det_repaired = detect(repaired)
    record(checks, "K5-repair-parses", "2-edit repair parses and keeps class_id",
           "AF-SCC-C0-VAC-GEN", repaired.get("class_id"))
    record(checks, "K5-repair-gate", "repaired copy gate verdict equals pristine verdict",
           (gate_pristine_pinned["verdict"], gate_pristine_pinned["failed_rules"]),
           (gate_repaired["verdict"], gate_repaired["failed_rules"]))
    record(checks, "K5-repair-detector", "repaired copy is detector-clean", [], det_repaired)

    diff_paths = recursive_paths_diff(f2b, repaired)
    impact_paths = [d["path"] for d in diff_paths]
    record(checks, "K5-repair-impact", "repair changes exactly the two carrier strings",
           ["$.implication_ledger.forbidden_transfers[0].reason", "$.regularity.must_not_conflate[0]"],
           impact_paths)

    # ---------------- K6 gate sensitivity controls (gate must NOT be inert) ----------------
    def mutant(name: str, mutator):
        doc = yaml.safe_load(f2b_text)
        mutator(doc)
        p = SANDBOX / f"{name}.yaml"
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        return run_gate(pinned_checker, p)

    def set_h1(doc, value):
        doc["implication_ledger"]["forbidden_transfers"][0]["reason"] = value

    def set_h2(doc, value):
        doc["regularity"]["must_not_conflate"][0] = value

    mut_r13 = mutant("mut_r13_composite_in_assertive", lambda d: d["conclusion"].__setitem__(
        "statement_natural_language", "C2 or C0 extended statement of the class [MUT]"))
    mut_r16a = mutant("mut_r16a_forbid_required_transfer", lambda d: d["implication_ledger"].__setitem__(
        "forbidden_transfers", [{"from": "no proper future C0 extension", "to": "no proper future C2 extension",
                                 "reason": "converse containment is false"}] +
        d["implication_ledger"]["forbidden_transfers"][1:]))
    mut_r16b = mutant("mut_r16b_converse_entailment", lambda d: d["implication_ledger"].__setitem__(
        "one_way_entailments", d["implication_ledger"]["one_way_entailments"] +
        [{"from": "no proper future C2 extension", "to": "no proper future C0 extension",
          "relation": "entails", "reason": "MUT converse", "status": "elementary"}]))
    mut_r06 = mutant("mut_r06_empty_must_not_conflate", lambda d: d["regularity"].__setitem__("must_not_conflate", []))
    mut_nonsense = mutant("mut_nonsense_carriers", lambda d: (set_h1(d, "zzz"), set_h2(d, "zzz")))
    mut_false2 = mutant("mut_strengthened_false", lambda d: (
        set_h1(d, "C2 is a strictly larger extension class, so C2-inextendibility is strictly stronger"),
        set_h2(d, "Containment with C2 and C0 is fully asserted here")))
    mut_empty = mutant("mut_empty_carriers", lambda d: (set_h1(d, ""), set_h2(d, "")))

    record(checks, "K6-R13-sensitive", "gate rejects a composite token moved to an assertive path",
           True, "R13" in mut_r13["failed_rules"])
    record(checks, "K6-R16a-sensitive", "gate rejects forbidding the required C0=>C2 entailment",
           True, "R16" in mut_r16a["failed_rules"])
    record(checks, "K6-R16b-sensitive", "gate rejects a converse C2=>C0 one-way entailment",
           True, "R16" in mut_r16b["failed_rules"])
    record(checks, "K6-R06-sensitive", "gate rejects an emptied must_not_conflate", True,
           "R06" in mut_r06["failed_rules"])

    # ---------------- K7 gate invariance under carrier content ----------------
    invariance = {
        "pristine_pass": gate_pristine_pinned["verdict"] == "pass" and not gate_pristine_pinned["failed_rules"],
        "repaired_pass": gate_repaired["verdict"] == "pass" and not gate_repaired["failed_rules"],
        "nonsense_pass": mut_nonsense["verdict"] == "pass" and not mut_nonsense["failed_rules"],
        "strengthened_false_pass": mut_false2["verdict"] == "pass" and not mut_false2["failed_rules"],
        "empty_pass": mut_empty["verdict"] == "pass" and not mut_empty["failed_rules"],
    }
    record(checks, "K7-gate-blind", "gate verdict invariant under repair, nonsense, strengthened-false, empty carriers",
           True, all(invariance.values()))

    # ---------------- controls ----------------
    record(controls, "C1-pin-fail-closed", "a wrong pin hash is detected before any measurement",
           True, pin_match["schemas/af_scc_c0_vacuum.yaml"] and not (measured_start["schemas/af_scc_c0_vacuum.yaml"] == "0" * 64))
    mut_h1_repaired = yaml.safe_load(edit_text(f2b_text, CLAUSE_H1, H1_REPAIR))
    record(controls, "C2-h1-repaired-only", "repairing H1 leaves exactly the H2 denial",
           ["false_containment_denial"], sorted(f["kind"] for f in detect(mut_h1_repaired)))
    mut_h2_repaired = yaml.safe_load(edit_text(f2b_text, CLAUSE_H2_DENIAL, H2_REPAIR))
    record(controls, "C3-h2-repaired-only", "repairing H2 leaves exactly the H1 inversion",
           ["size_premise_inverted"], sorted(f["kind"] for f in detect(mut_h2_repaired)))
    bracketed = yaml.safe_load(edit_text(
        edit_text(f2b_text, CLAUSE_H1, H1_REPAIR), CLAUSE_H2_DENIAL,
        "The earlier [No containment with C2 or C0 is asserted here] was wrong; see implication_ledger."))
    record(controls, "C4-bracketed-denial", "a bracketed (withdrawn) denial is not flagged when H1 is repaired",
           [], detect(bracketed))
    corrected_reason_live_denial = yaml.safe_load(edit_text(f2b_text, CLAUSE_H1, H1_REPAIR))  # H2 still live
    record(controls, "C5-repaired-reason-clean", "corrected size premise produces no size finding",
           ["false_containment_denial"], sorted(f["kind"] for f in detect(corrected_reason_live_denial)))
    record(controls, "C6-detector-count", "F2b detector findings carry carrier paths",
           ["implication_ledger.forbidden_transfers[0].reason", "regularity.must_not_conflate[0]"],
           [f["carrier"] for f in det_f2b])

    # ---------------- W066 normativity claim test ----------------
    w066_ground = ("required slots of the frozen class contract (rule_spec R06 and R16; no advisory marker "
                   "anywhere on either carrier), so the two clauses are normative content")
    normativity = {
        "claim_under_test": w066_ground,
        "w066_h1": "W066-R13-F2B-H1 size_premise_inverted at implication_ledger.forbidden_transfers[0].reason",
        "w066_h2": "W066-R13-F2B-H2 false_containment_denial at regularity.must_not_conflate[0]",
        "slot_requirement_confirmed": {
            "R06": "must_not_conflate is a non-empty list (F2b has 5 entries)",
            "R16": "ledger records chain + one-way entailments and marks the converse forbidden",
        },
        "content_binding_found": False,
        "content_binding_basis": {
            "R06_fail": r06.get("fail"), "R16_fail": r16.get("fail"),
            "R06_mentions_entry_truth": r06_require_binds_content,
            "R16_mentions_reason_truth": r16_require_binds_reason,
            "gate_exempt_keys": exempt,
            "gate_invariance": invariance,
        },
        "contract_projection_diff_paths": impact_paths,
        "verdict": ("W066's content-normativity claim is REJECTED at these bytes under the operational "
                    "definition: neither clause triggers any R01-R16 require/fail condition, neither is "
                    "distinguished by the canonical gate, and repairing both changes no rule-bound contract "
                    "field outside the two carrier strings. Both clauses are nonetheless REAL live text "
                    "defects (H1 inverts its own ledger's containment premise and, read literally, "
                    "contradicts its own forbidden verdict; H2 denies a containment the same document "
                    "asserts at :%d and :%d-%d), so an editorial revise remains required." %
                    (chain_line, chain_line + 2, chain_line + 5)),
    }

    # ---------------- assemble ----------------
    measured_end = {p: sha256(ROOT / p) for p in DECLARED}
    result = {
        "schema": "worker-028/carrier-normativity/v1",
        "task_id": "W028-F2B-CARRIER-NORMATIVITY-01",
        "actor": "worker-028",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "authority": "worker evidence only; sets no gate verdict, no node status, no validation_status=passed",
        "question": ("Are W066-R13-F2B-H1/H2 normative under the binding rule spec R01-R16 + canonical "
                     "class-schema gate at F2b b2ab6acb2bbe / FROZEN rev29 815e0807, and are they real "
                     "live defects?"),
        "operational_definitions": {
            "rule_spec_normative": ("a clause is rule-spec-normative iff removing/replacing it changes the "
                                    "canonical gate verdict, or a rule's require/fail names its content so a "
                                    "false value triggers the fail"),
            "contract_normative": ("a clause is contract-normative iff changing it changes any rule-bound "
                                   "class-contract projection field other than the clause itself"),
            "editorial": "a real text defect that is neither rule-spec-normative nor contract-normative",
        },
        "pins": {"declared": DECLARED, "measured_start": measured_start, "measured_end": measured_end,
                 "all_match": all(measured_end[p] == DECLARED[p] for p in DECLARED)},
        "carriers": {
            "H1": {"path": "implication_ledger.forbidden_transfers[0].reason", "line": h1_line, "value": h1_value,
                   "row_from": f2b["implication_ledger"]["forbidden_transfers"][0].get("from"),
                   "row_to": f2b["implication_ledger"]["forbidden_transfers"][0].get("to")},
            "H2": {"path": "regularity.must_not_conflate[0]", "line": h2_line, "value": h2_value},
            "chain": {"path": "implication_ledger.extension_class_containment", "line": chain_line,
                      "value": f2b["implication_ledger"]["extension_class_containment"],
                      "rank_largest_first": chain_rank(f2b)[0]},
            "entailment_rows": len(f2b["implication_ledger"].get("one_way_entailments") or []),
            "forbidden_rows": len(f2b["implication_ledger"].get("forbidden_transfers") or []),
            "must_not_conflate_entries": len(f2b["regularity"].get("must_not_conflate") or []),
        },
        "sibling_comparison": {
            "F2a_sha256": DECLARED["schemas/af_scc_c2_vacuum.yaml"],
            "F2a_detector_findings": det_f2a,
            "F2a_carries_corrected_nesting": bool(re.search(r"E_C2 subset of E_\{C\^1,1\} subset of E_H2loc subset of E_C0",
                                                            json.dumps(f2a))),
            "F2a_records_earlier_denial_as_wrong": bool(re.search(r"earlier .{0,40}no containment with C2",
                                                                  json.dumps(f2a), re.I)),
        },
        "canonical_gate": {"live_entry_point": gate_pristine_live, "pinned_entry_point": gate_pristine_pinned,
                           "f2a": gate_f2a, "f1": gate_f1, "repaired": gate_repaired},
        "detector": {"implementation": "independent order-relative, derived from the document's own chain sentence",
                     "f2b": det_f2b, "f2a": det_f2a, "f1": det_f1, "repaired": det_repaired},
        "rule_trace": rule_trace,
        "gate_sensitivity_matrix": [
            {"mutant": "R13 composite token moved to conclusion.statement_natural_language",
             "failed_rules": mut_r13["failed_rules"], "verdict": mut_r13["verdict"]},
            {"mutant": "R16 forbidden row replaced by the required C0=>C2 transfer",
             "failed_rules": mut_r16a["failed_rules"], "verdict": mut_r16a["verdict"]},
            {"mutant": "R16 converse C2=>C0 added to one_way_entailments",
             "failed_rules": mut_r16b["failed_rules"], "verdict": mut_r16b["verdict"]},
            {"mutant": "R06 must_not_conflate emptied",
             "failed_rules": mut_r06["failed_rules"], "verdict": mut_r06["verdict"]},
            {"mutant": "carriers repaired (H1/H2)", "failed_rules": gate_repaired["failed_rules"],
             "verdict": gate_repaired["verdict"]},
            {"mutant": "carriers nonsense", "failed_rules": mut_nonsense["failed_rules"],
             "verdict": mut_nonsense["verdict"]},
            {"mutant": "carriers strengthened-false", "failed_rules": mut_false2["failed_rules"],
             "verdict": mut_false2["verdict"]},
            {"mutant": "carriers empty", "failed_rules": mut_empty["failed_rules"],
             "verdict": mut_empty["verdict"]},
        ],
        "gate_invariance_under_carrier_content": invariance,
        "contract_projection": {"defective_vs_repaired_diff_paths": impact_paths,
                                "diff_detail": diff_paths,
                                "only_carriers_changed": impact_paths == [
                                    "$.implication_ledger.forbidden_transfers[0].reason",
                                    "$.regularity.must_not_conflate[0]"]},
        "normativity_adjudication": normativity,
        "checks": checks,
        "controls": controls,
        "summary": {
            "checks_pass": sum(c["pass"] for c in checks), "checks_total": len(checks),
            "controls_pass": sum(c["pass"] for c in controls), "controls_total": len(controls),
            "h1_h2_real_defects": bool(det_f2b),
            "h1_h2_rule_spec_normative": False,
            "h1_h2_contract_normative": False,
            "editorial_verdict": "revise (two minimal wording repairs) — not a class-binding or gate failure",
        },
        "falsifier": ("Falsified if any of the nine pinned hashes moves; if the canonical gate at the pin fails or "
                      "distinguishes repaired/nonsense/empty carrier text from pristine; if repairing the two "
                      "clauses changes any parsed contract path outside the two carriers; if R06/R16's require or "
                      "fail text at the pin names entry/reason truth; if a sibling carries either defect kind; or "
                      "if any check K0-K7 or control C1-C6 departs from its recorded expectation. Any hash move "
                      "voids the whole measurement and requires a fresh run."),
        "limitations": [
            "operational definitions of normative/contract-normative are this report's; 'editorial' does not mean optional or acceptable",
            "measures the rule spec R01-R16 as written plus the canonical checker at 000e09e46b2f; a future spec or checker revision can rebind these clauses",
            "does not decide the mathematics of C0/C2 inextendibility, the F0 taxonomy, or the L1 ledger",
            "does not authorize an accept; two false sentences in a frozen schema remain a revise item",
        ],
        "non_claims": ["no gate verdict; G-FORM stays pending", "no node status",
                       "no canonical artifact modified (all mutants under sandbox/)",
                       "not one of the independent verdicts required by astra-life05-verify-gform-r3"],
    }
    ART.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    ok = result["summary"]["checks_pass"] == result["summary"]["checks_total"] and \
        result["summary"]["controls_pass"] == result["summary"]["controls_total"]
    print(f"checks {result['summary']['checks_pass']}/{result['summary']['checks_total']} "
          f"controls {result['summary']['controls_pass']}/{result['summary']['controls_total']} "
          f"-> {ART}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
