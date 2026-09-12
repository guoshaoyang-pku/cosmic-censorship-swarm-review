#!/usr/bin/env python3
"""W018-REQDROP-STRENGTH-ADJ-01 -- deterministic, read-only adjudication of the
requirement-drop strength-label conflict raised by worker-096 (W096-REQDROP-B1/B2/B3)
at the FROZEN rev29 pins.

Question
--------
At F2a schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3 the reviewer-facing falsifier list
carries the entry

    "the extension is not required to solve Ric = 0: weaker statement bound to the wrong class"

The same file's implication_ledger rule (line 237) states the opposite convention
("the lower the required regularity, the larger the set of admissible extensions,
hence the STRONGER the inexistence statement"), and the C0 sibling (line 95-98)
calls the bare-metric construction "the strongest form of the statement". Is the
word "weaker" at F2a:265 a real content defect, an author-defined inversion, or a
reading artifact? Same question at F2a:231 (forbidden_weakenings carrier) and at
F1:260 ("using a weaker visibility notion").

Method
------
Read-only. Hash-pins the three canonical schemas + FROZEN.json, extracts the exact
anchored lines, applies six consistency rules, and runs six in-memory controls that
must each discriminate. Writes only into this task directory. Exit 0 iff the live
outcome equals the pre-registered expectation and all controls behave; exit 2 on pin
drift or a failed control; exit 3 on an unexpected live outcome.

Pre-registered expectation
--------------------------
R1 PASS  containment direction is stated correctly and consistently in F2a
R2 FAIL  F2a:265 labels the Ric-drop "weaker statement" -> finding B1 (confirmed)
R3 N     F2a:231 lists the same drop under forbidden_weakenings -> non-blocking N
R4 FAIL  C0:95-98 ("strongest form") vs F2a:265 ("weaker") -> finding B3 (same carrier)
R5 N     F1:260 "weaker visibility notion" is ambiguous/inverted under F1:235 -> N
R6 PASS  FROZEN rev29 binds the three measured canonical hashes

Non-claims
----------
Not a schema verdict, not a gate verdict, not a node transition, no canonical write.
Confirms/voids another worker's finding; the repair decision belongs to the artifact
author and the G-FORM gate owner.
"""

import hashlib
import json
import sys
from pathlib import Path

TASK_ID = "W018-REQDROP-STRENGTH-ADJ-01"
REPO = Path(__file__).resolve().parents[3]

PINS = {
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

# (file, line, yaml-path, exact substring that must be on that line)
ANCHORS = [
    ("schemas/af_scc_c2_vacuum.yaml", 231, ".falsifier.forbidden_weakenings[2]",
     'allowing extensions that do not satisfy Ric = 0'),
    ("schemas/af_scc_c2_vacuum.yaml", 237, ".implication_ledger.extension_class_containment",
     'hence the stronger the inexistence statement'),
    ("schemas/af_scc_c2_vacuum.yaml", 243, ".implication_ledger.forbidden_transfers[0]",
     'the converse containment is false'),
    ("schemas/af_scc_c2_vacuum.yaml", 265, ".falsifier.schema_falsifiers[3]",
     'the extension is not required to solve Ric = 0: weaker statement bound to the wrong class'),
    ("schemas/af_scc_c2_vacuum.yaml", 269, ".anti_scope.not_this_class[0]",
     'different (stronger) extension class'),
    ("schemas/af_scc_c0_vacuum.yaml", 80, ".conclusion_relation_to_sibling",
     'the logical strength is not lower'),
    ("schemas/af_scc_c0_vacuum.yaml", 96, ".extension_predicate.why_bare_metric",
     'this is the strongest form of the statement'),
    ("schemas/af_scc_c0_vacuum.yaml", 101, ".extension_predicate.must_not_conflate[1]",
     'are a DIFFERENT, strictly weaker class'),
    ("schemas/af_wcc_vacuum.yaml", 235, ".class_identity_variants[0].relation",
     'strictly WEAKER than this class\'s single-q tail predicate'),
    ("schemas/af_wcc_vacuum.yaml", 260, ".conclusion.forbidden_weakenings[3]",
     'using a weaker visibility notion'),
]

F1_FORBIDDEN_WEAKENINGS_HEADER = ("schemas/af_wcc_vacuum.yaml", 256)
F2A_FORBIDDEN_WEAKENINGS_HEADER = ("schemas/af_scc_c2_vacuum.yaml", 228)
F2A_FORBIDDEN_WEAKENINGS_END = ("schemas/af_scc_c2_vacuum.yaml", 233)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_ok(observed: str, expected: str) -> bool:
    """Fail-closed pin predicate: exact match, no prefix semantics."""
    return isinstance(observed, str) and isinstance(expected, str) and observed == expected


def read_lines(path: Path):
    return path.read_text(encoding="utf-8").splitlines()


def extract(texts):
    """Return per-file list of anchors found, plus missing anchors."""
    found, missing = [], []
    for fname, lineno, ypath, quote in ANCHORS:
        lines = texts.get(fname)
        if lines is None:
            missing.append({"file": fname, "line": lineno, "path": ypath, "reason": "file-not-read"})
            continue
        if lineno < 1 or lineno > len(lines):
            missing.append({"file": fname, "line": lineno, "path": ypath, "reason": "line-out-of-range"})
            continue
        text = lines[lineno - 1]
        if quote in text:
            found.append({"file": fname, "line": lineno, "path": ypath, "quote": quote, "text": text.strip()})
        else:
            missing.append({"file": fname, "line": lineno, "path": ypath,
                            "reason": "quote-not-on-line", "expected": quote, "observed": text.strip()})
    return found, missing


def _line(texts, fname, lineno):
    lines = texts.get(fname) or []
    return lines[lineno - 1] if 0 < lineno <= len(lines) else ""


def run_rules(texts, found):
    """Apply R1-R6. Returns (rules, findings, live_outcome)."""
    f2a = "schemas/af_scc_c2_vacuum.yaml"
    c0 = "schemas/af_scc_c0_vacuum.yaml"
    f1 = "schemas/af_wcc_vacuum.yaml"

    l237 = _line(texts, f2a, 237)
    l243 = _line(texts, f2a, 243)
    l265 = _line(texts, f2a, 265)
    l269 = _line(texts, f2a, 269)
    l80 = _line(texts, c0, 80)
    l96 = _line(texts, c0, 96)
    l101 = _line(texts, c0, 101)
    l235 = _line(texts, f1, 235)
    l260 = _line(texts, f1, 260)

    findings = []

    # R1 -- containment direction: F2a states the convention and uses it consistently.
    r1_pass = ("hence the stronger the inexistence statement" in l237
               and "different (stronger) extension class" in l269
               and "the converse containment is false" in l243)
    rules = {"R1_containment_direction_consistency": "PASS" if r1_pass else "FAIL"}

    # R2 -- the Ric-drop label at F2a:265.
    r2_hit = ("not required to solve Ric = 0" in l265) and ("weaker" in l265)
    rules["R2_ric_drop_label_consistency"] = "FAIL" if r2_hit else "PASS"
    if r2_hit:
        findings.append({
            "id": "W018-REQDROP-B1-CONFIRMED",
            "check_id": "B1",
            "severity": "major",
            "blocking": True,
            "carrier": "schemas/af_scc_c2_vacuum.yaml:265",
            "yaml_path": ".falsifier.schema_falsifiers[3]",
            "statement": ("F2a:265 labels the Ric=0 requirement-drop 'weaker statement', "
                          "inverting the file's own rule at F2a:237 and the C0 sibling's anchor "
                          "at C0:95-98/101. E_C2 is a subset of E_C0, so excluding all bare-metric "
                          "C0 extensions is the STRONGER inexistence statement; the class binding "
                          "('wrong class') is right, the strength word is wrong."),
            "evidence": [
                {"file": f2a, "line": 265, "text": l265.strip()},
                {"file": f2a, "line": 237, "text": l237.strip()},
                {"file": c0, "line": 96, "text": l96.strip()},
                {"file": c0, "line": 101, "text": l101.strip()},
                {"file": f2a, "line": 269, "text": l269.strip()},
            ],
            "minimal_repair": ("replace 'weaker statement' by 'stronger statement' (or "
                               "'weaker extension requirement, stronger statement') at F2a:265; "
                               "one-word edit, no formal field touched."),
            "falsifier": ("exhibit a frozen authority clause (rule_spec / schema / VARIANT_REGISTRY) "
                          "that defines statement strength inversely to forbidden-set size, or show "
                          "that 'weaker' at F2a:265 modifies the extension requirement rather than the "
                          "statement; or land the word fix before the rev14 freeze, which voids the finding."),
        })

    # R3 -- the same drop under forbidden_weakenings at F2a:231.
    in_weakenings = (F2A_FORBIDDEN_WEAKENINGS_HEADER[1] < 231 < F2A_FORBIDDEN_WEAKENINGS_END[1])
    l231 = _line(texts, f2a, 231)
    r3_hit = in_weakenings and ("not satisfy Ric = 0" in l231)
    rules["R3_forbidden_weakenings_classification"] = "N" if r3_hit else "PASS"
    if r3_hit:
        findings.append({
            "id": "W018-REQDROP-N1-CLASSIFICATION",
            "check_id": "N1",
            "severity": "minor",
            "blocking": False,
            "carrier": "schemas/af_scc_c2_vacuum.yaml:231",
            "yaml_path": ".falsifier.forbidden_weakenings[2]",
            "statement": ("The Ric=0 drop is listed under forbidden_weakenings. Under F2a:237 the "
                          "mutation is a class substitution that enlarges the extension set (stronger "
                          "statement), not a weakening. The list is already known-mixed (line 232 is a "
                          "token misuse, not a strength claim), so this is an annotation/placement "
                          "issue, not a second inversion."),
            "evidence": [
                {"file": f2a, "line": 231, "text": l231.strip()},
                {"file": f2a, "line": 228, "text": _line(texts, f2a, 228).strip()},
                {"file": f2a, "line": 232, "text": _line(texts, f2a, 232).strip()},
                {"file": f2a, "line": 237, "text": l237.strip()},
            ],
            "minimal_repair": ("annotate the entry as a class substitution to the stronger C0 class "
                               "(or move it to a forbidden_class_substitutions block) at the same "
                               "edit as B1."),
            "falsifier": ("show the entry is a pure weakening under some frozen clause, or show the "
                          "list header is documented as mixed-mutation, which downgrades N1 to recorded."),
        })

    # R4 -- cross-file label agreement for the same construction.
    r4_hit = r2_hit and ("strongest form of the statement" in l96)
    rules["R4_cross_file_label_agreement"] = "FAIL" if r4_hit else "PASS"
    if r4_hit:
        findings.append({
            "id": "W018-REQDROP-B3-CONFIRMED",
            "check_id": "B3",
            "severity": "major",
            "blocking": True,
            "carrier": "schemas/af_scc_c2_vacuum.yaml:265 vs schemas/af_scc_c0_vacuum.yaml:95-98",
            "statement": ("The same requirement drop carries opposite labels across the frozen set: "
                          "F2a:265 'weaker', C0:95-98 'the strongest form of the statement' (with "
                          "C0:80 'the logical strength is not lower'). The defect carrier is F2a, not "
                          "F2b/C0; the C0 labelling is the one consistent with F2a:237."),
            "evidence": [
                {"file": c0, "line": 96, "text": l96.strip()},
                {"file": c0, "line": 80, "text": l80.strip()},
                {"file": f2a, "line": 265, "text": l265.strip()},
                {"file": f2a, "line": 237, "text": l237.strip()},
            ],
            "minimal_repair": "same one-word edit as B1; no C0/F2b edit is indicated by this finding.",
            "falsifier": ("show C0:95-98's 'strongest' governs a different construction than "
                          "F2a:265's Ric-drop (it does not: both name the bare-metric class), or land "
                          "the F2a edit."),
        })

    # R5 -- F1 visibility label.
    in_f1_weakenings = (F1_FORBIDDEN_WEAKENINGS_HEADER[1] < 260 < 262)
    r5_hit = (in_f1_weakenings and "using a weaker visibility notion" in l260
              and "strictly WEAKER than this class's single-q tail predicate" in l235)
    rules["R5_f1_visibility_label"] = "N" if r5_hit else "PASS"
    if r5_hit:
        findings.append({
            "id": "W018-REQDROP-N2-F1-VISIBILITY",
            "check_id": "B2",
            "severity": "minor",
            "blocking": False,
            "carrier": "schemas/af_wcc_vacuum.yaml:260",
            "yaml_path": ".conclusion.forbidden_weakenings[3]",
            "statement": ("F1:260 lists 'using a weaker visibility notion' as a weakening while F1:235 "
                          "defines the union/SET visibility predicate as strictly WEAKER (it admits more "
                          "geodesics). A weaker predicate makes 'no visible singularity' stronger, so the "
                          "entry is inverted or ambiguous under the file's own token convention. It stays "
                          "N-level because the same list already carries a non-weakening at line 259 "
                          "('no singularity' is stronger than 'no visible singularity'), so the header is "
                          "not a strict strength classifier."),
            "evidence": [
                {"file": f1, "line": 235, "text": l235.strip()},
                {"file": f1, "line": 260, "text": l260.strip()},
                {"file": f1, "line": 259, "text": _line(texts, f1, 259).strip()},
            ],
            "minimal_repair": ("disambiguate to 'a visibility notion under which fewer geodesics count "
                               "as visible' (the actual weakening direction), or move the entry to "
                               "forbidden_strengthenings."),
            "falsifier": ("show 'weaker visibility notion' is defined in the frozen taxonomy as the "
                          "notion classifying FEWER geodesics as visible; that voids N2 and is the "
                          "exact falsifier worker-096 registered."),
        })

    # R6 -- FROZEN manifest binding.
    frozen = json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text())
    files = frozen.get("files", {})
    bound = {}
    for rel, digest in PINS.items():
        if not rel.startswith("schemas/"):
            continue  # the manifest is self-pinned by PINS, not listed in its own files map
        canon = "artifacts/formulation/" + rel
        entry = files.get(canon)
        bound[canon] = bool(entry and entry.get("sha256") == digest)
    r6_pass = frozen.get("revision") == 29 and len(bound) == 3 and all(bound.values())
    rules["R6_frozen_manifest_binding"] = "PASS" if r6_pass else "FAIL"

    live = {
        "expected": {"R1": "PASS", "R2": "FAIL", "R3": "N", "R4": "FAIL", "R5": "N", "R6": "PASS"},
        "observed": {"R1": rules["R1_containment_direction_consistency"],
                     "R2": rules["R2_ric_drop_label_consistency"],
                     "R3": rules["R3_forbidden_weakenings_classification"],
                     "R4": rules["R4_cross_file_label_agreement"],
                     "R5": rules["R5_f1_visibility_label"],
                     "R6": rules["R6_frozen_manifest_binding"]},
    }
    return rules, findings, live, {"frozen_revision": frozen.get("revision"), "bound": bound}


def run_controls(texts):
    """Six in-memory mutation controls; each must discriminate. No writes."""
    f2a = "schemas/af_scc_c2_vacuum.yaml"
    c0 = "schemas/af_scc_c0_vacuum.yaml"
    f1 = "schemas/af_wcc_vacuum.yaml"
    out = []

    def rules_of(t):
        _r, _fi, _live, _r6 = run_rules(t, None)
        return _fi, _live

    # K1 sensitivity: fix the word in memory -> B1 must vanish.
    t = {k: list(v) for k, v in texts.items()}
    t[f2a][264] = t[f2a][264].replace("weaker statement", "stronger statement")
    f, _ = rules_of(t)
    out.append({"control": "K1_ric_drop_word_sensitivity", "expected": "B1_absent",
                "observed": "B1_absent" if not any(x["check_id"] == "B1" for x in f) else "B1_present",
                "pass": not any(x["check_id"] == "B1" for x in f)})

    # K2 dependency: remove the C0 anchor -> B3 must vanish while B1 stays.
    t = {k: list(v) for k, v in texts.items()}
    t[c0][95] = t[c0][95].replace("the strongest form of the statement", "a form of the statement")
    f, _ = rules_of(t)
    b3 = any(x["check_id"] == "B3" for x in f)
    b1 = any(x["check_id"] == "B1" for x in f)
    out.append({"control": "K2_cross_file_anchor_dependency", "expected": "B3_absent_B1_present",
                "observed": ("B3_absent_B1_present" if (not b3 and b1) else
                             ("B3_present" if b3 else "B1_absent")),
                "pass": (not b3 and b1)})

    # K3 direction: invert the file's stated convention -> R1 must fail.
    t = {k: list(v) for k, v in texts.items()}
    t[f2a][236] = t[f2a][236].replace("stronger the inexistence statement", "weaker the inexistence statement")
    f, _ = rules_of(t)
    _r, _fi, live, _r6 = run_rules(t, None)
    r1 = live["observed"]["R1"] == "FAIL"
    out.append({"control": "K3_convention_direction_sensitivity", "expected": "R1_FAIL",
                "observed": live["observed"]["R1"], "pass": r1})

    # K4 determinism: same bytes -> same extraction.
    f1a, m1 = extract(texts)
    f2b, m2 = extract(texts)
    same = (json.dumps(f1a, sort_keys=True) == json.dumps(f2b, sort_keys=True)
            and json.dumps(m1, sort_keys=True) == json.dumps(m2, sort_keys=True))
    out.append({"control": "K4_extraction_determinism", "expected": "identical",
                "observed": "identical" if same else "differs", "pass": same})

    # K5 specificity: a decoy 'weaker statement' line elsewhere must not create a hit.
    t = {k: list(v) for k, v in texts.items()}
    t[f2a].append('    - "decoy: weaker statement not bound to a class"')
    f, _ = rules_of(t)
    hits = {x["carrier"] for x in f if x["check_id"] == "B1"}
    ok = hits == {f"{f2a}:265"}
    out.append({"control": "K5_anchor_specificity", "expected": "only_F2a:265",
                "observed": sorted(hits), "pass": ok})

    # K6 fail-closed pin check: a wrong pin must be rejected by the same predicate main() uses.
    good = sha256_file(REPO / f1)
    bad = ("0" * 8) + good[8:]
    out.append({"control": "K6_fail_closed_pin_check", "expected": "rejected",
                "observed": "rejected" if not pin_ok(bad, good) else "accepted",
                "pass": not pin_ok(bad, good)})

    return out


def main():
    pins = {}
    texts = {}
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha256_file(p)
        pins[rel] = {"expected": want, "observed": got, "match": pin_ok(got, want)}
        if not pin_ok(got, want):
            print(json.dumps({"task_id": TASK_ID, "status": "PIN_DRIFT", "pins": pins}, indent=1))
            return 2
        texts[rel] = read_lines(p)

    found, missing = extract(texts)
    if missing:
        print(json.dumps({"task_id": TASK_ID, "status": "ANCHOR_MISSING", "missing": missing}, indent=1))
        return 2

    rules, findings, live, r6detail = run_rules(texts, found)
    controls = run_controls(texts)
    controls_ok = all(c["pass"] for c in controls)
    expectation_met = live["observed"] == live["expected"]
    core = {
        "task_id": TASK_ID,
        "pins": pins,
        "anchors_found": found,
        "rules": rules,
        "findings": findings,
        "live_outcome": live,
        "controls": controls,
        "frozen_manifest": r6detail,
    }
    core_digest = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    result = {
        "schema": "worker-018/reqdrop-strength-adjudication/v1",
        "task_id": TASK_ID,
        "core_digest": core_digest,
        "status": ("ADJUDICATED" if (expectation_met and controls_ok)
                   else ("CONTROL_FAILED" if not controls_ok else "UNEXPECTED_OUTCOME")),
        "verdict": {
            "B1": "CONFIRMED" if any(x["check_id"] == "B1" for x in findings) else "VOID",
            "B3": "CONFIRMED" if any(x["check_id"] == "B3" for x in findings) else "VOID",
            "B2": "AMBIGUOUS_OR_INVERTED_N_LEVEL" if any(x["check_id"] == "B2" for x in findings) else "VOID",
            "N1": "CLASSIFICATION_ISSUE_N_LEVEL" if any(x["check_id"] == "N1" for x in findings) else "CLEAR",
            "authority_inversion_found": any(x["check_id"] == "B1" for x in findings),
        },
        "repair_scope_advice": ("fold a one-word fix at F2a:265 ('weaker'->'stronger') and the F2a:231 "
                                "annotation into the authorized rev14/FROZEN rev30 before the byte move; "
                                "F2b/C0 carry no defect on this carrier; F1:260 is N-level disambiguation."),
        "non_claims": ["not a schema verdict", "not a gate verdict", "not a node transition",
                       "no canonical write", "does not supersede worker-096's sweep"],
        "authority_note": ("worker event; cannot set status=done, validation_status=passed or a gate "
                           "verdict; the repair decision belongs to astra-lead-formulation and G-FORM."),
        "reproduce": "python3 artifacts/worker-018/strength_label_adjudication/adjudicate.py",
        **core,
    }
    (Path(__file__).resolve().parent / "report.json").write_text(
        json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"task_id": TASK_ID, "status": result["status"], "core_digest": core_digest,
                      "live": live["observed"], "controls_ok": controls_ok,
                      "findings": [f["id"] for f in findings]}, indent=1))
    if not controls_ok:
        return 2
    if not expectation_met:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
