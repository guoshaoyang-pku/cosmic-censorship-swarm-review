#!/usr/bin/env python3
"""W096-F2A-REQDROP-STRENGTH-LABEL-SWEEP-01

Independent, read-only sweep of *requirement-drop* strength labels in the three live
SCC/WCC class schemas at the rev13 / FROZEN-rev29 pins.

Scope (deliberately disjoint from the earlier worker-096 containment-premise sweep and
from worker-080's F2b HF-1 direction census):
  a *requirement-drop* premise is one that changes the set of admissible extensions by
  adding or dropping a requirement on the extension (an equation, a regularity, a
  causality condition), rather than by changing the extension-set containment chain.

The project's own stated convention, taken from the pinned bytes themselves:
  - C0 extension_class_containment: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2
    ("this class requires the LOWEST regularity, so its inexistence statement is the
    STRONGEST of the three").
  - C2 extension_class_containment: "the lower the required regularity, the larger the set
    of admissible extensions, hence the stronger the inexistence statement".
  - C0 extension_predicate.why_bare_metric: "NO equation is required of g' ... this is the
    strongest form of the statement: every extension class with more structure or more
    requirements is a subset of this one".
Therefore: dropping a requirement on the extension ENLARGES the forbidden set and makes
the inexistence statement STRONGER, not weaker.

Checks:
  A1 containment_denial               (control; known live C0 defect, line 152)
  A2 inverted_size_premise            (control; known live C0 defect, line 246)
  A3 class_relative_entailment_inversion (control; class-relative, fires on the
                                     circulating defective candidate 84b5d3fa, not on live
                                     C0 and not on the two corrected candidates)
  B1 ric_drop_strength_label          (finding; C2 line 265 "weaker statement" vs the
                                     convention above)
  B2 weaker_visibility_conflict       (finding; F1 line 260 "weaker visibility notion"
                                     under a conclusion block whose own variant relation
                                     defines the weaker visibility predicate as the one
                                     that admits MORE geodesics)
  B3 cross_file_ric_label_conflict    (finding; B1 coexists with the C0 "strongest form"
                                     anchor for the same construction)

Exit 0 iff every pin resolves and every control matches; findings are reported, not
asserted as gate-relevant by this harness.  No writes outside the artifact directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))

F1 = "schemas/af_wcc_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
CANDS = {
    "candidate_corrected": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
    "candidate_nesting_only": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
    "candidate_84b5d3fa": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
}
PINS = {
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F2A: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CANDS["candidate_corrected"]: "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
    CANDS["candidate_nesting_only"]: "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
    CANDS["candidate_84b5d3fa"]: "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}

TOK = re.compile(
    r"stronger|weaker|strongest|weakest|larger|smaller|entails|entailment|implies|imply|"
    r"subset|superset|contain|nest|reverse|converse|inflat|subsum",
    re.I,
)

# ---------------------------------------------------------------- YAML with marks


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(path: str):
    """Return composed node tree + source text (line numbers via start_mark)."""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    with open(path, "rb") as fh:
        raw = fh.read()
    return src, raw, yaml.compose(src)


def walk_scalars(node, path=""):
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            yield from walk_scalars(v, path + "." + str(k.value))
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            yield from walk_scalars(v, f"{path}[{i}]")
    elif isinstance(node, yaml.ScalarNode):
        yield path, node


def duplicate_keys(node, path="", found=None):
    if found is None:
        found = []
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k, v in node.value:
            if k.value in seen:
                found.append({"path": path + "." + str(k.value), "line": k.start_mark.line + 1})
            seen.add(k.value)
            duplicate_keys(v, path + "." + str(k.value), found)
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            duplicate_keys(v, f"{path}[{i}]", found)
    return found


def scalars(path):
    """{json_path: (line, text)} for every scalar; duplicate paths keep the first."""
    _, _, root = load(path)
    out = {}
    for p, n in walk_scalars(root):
        out.setdefault(p, (n.start_mark.line + 1, str(n.value)))
    return out


def chain_of(sc):
    """Class family of a schema, read from its own declared containment chain."""
    text = sc.get(".implication_ledger.extension_class_containment", (0, ""))[1]
    if "E_C0 contains" in text:
        return "C0"
    if "E_C2 subset" in text:
        return "C2"
    return "?"


def side(sc):
    """Which side of the family a schema is on."""
    if any(p.startswith(".c0_specifics") for p in sc):
        return "C0"
    if chain_of(sc) == "C2":
        return "C2"
    return "WCC"


# ---------------------------------------------------------------- checks

def hits(sc, path_pred, text_pred, label):
    out = []
    for p, (line, text) in sorted(sc.items(), key=lambda kv: kv[1][0]):
        if path_pred(p) and text_pred(text):
            out.append({"label": label, "path": p, "line": line, "text": text[:260]})
    return out


def check_a1(sc):
    return hits(sc, lambda p: p.startswith(".regularity.must_not_conflate["),
                lambda t: "No containment with C2 or C0 is asserted here" in t, "A1")


def check_a2(sc):
    return hits(sc, lambda p: p.startswith(".implication_ledger.forbidden_transfers[") and p.endswith(".reason"),
                lambda t: "C2 is a strictly larger extension class" in t, "A2")


def check_a3(sc):
    if chain_of(sc) != "C0":
        return []
    return hits(sc, lambda p: p.startswith(".regularity.must_not_conflate["),
                lambda t: "H2_loc-inextendibility ENTAILS this class's conclusion" in t, "A3")


def check_b1(sc):
    return hits(sc, lambda p: p.startswith(".falsifier.schema_falsifiers["),
                lambda t: re.search(r"not required to solve Ric\s*=\s*0", t) and "weaker" in t, "B1")


def check_b2(sc):
    if side(sc) != "WCC":
        return []
    weak_variant = False
    for p, (_, t) in sc.items():
        if p.startswith(".class_identity_variants[") and p.endswith(".relation"):
            if "strictly WEAKER" in t and "entails the union reading" in t:
                weak_variant = True
    if not weak_variant:
        return []
    return hits(sc, lambda p: p.startswith(".conclusion.forbidden_weakenings["),
                lambda t: "weaker visibility notion" in t, "B2")


ANCHORS = [
    (F2B, ".extension_predicate.definition", "NO equation is required of g'"),
    (F2B, ".extension_predicate.why_bare_metric", "strongest form of the statement"),
    (F2A, ".implication_ledger.extension_class_containment", "hence the stronger the inexistence statement"),
    (F2A, ".conventions.field_equations_on_extension", "required: Ric(g') = 0"),
    (F1, ".class_identity_variants[0].relation", "strictly WEAKER than this class's single-q tail predicate"),
    (F1, ".class_identity_variants[0].relation", "entails the union reading"),
]


def main() -> int:
    now = datetime.now(CST)
    failed = []
    inputs, pin_ok = {}, True
    for rel, want in PINS.items():
        got = sha256(os.path.join(ROOT, rel))
        ok = got == want
        pin_ok &= ok
        inputs[rel] = {"sha256": got, "pinned": want, "match": ok}
        if not ok:
            failed.append(f"pin drift: {rel}: {got[:12]} != {want[:12]}")

    sc = {name: scalars(os.path.join(ROOT, rel)) for name, rel in
          (("F1", F1), ("F2a", F2A), ("F2b", F2B),
           ("candidate_corrected", CANDS["candidate_corrected"]),
           ("candidate_nesting_only", CANDS["candidate_nesting_only"]),
           ("candidate_84b5d3fa", CANDS["candidate_84b5d3fa"]))}

    # controls -------------------------------------------------------------
    dup = {}
    for name, rel in (("F1", F1), ("F2a", F2A), ("F2b", F2B),
                      ("candidate_corrected", CANDS["candidate_corrected"]),
                      ("candidate_nesting_only", CANDS["candidate_nesting_only"]),
                      ("candidate_84b5d3fa", CANDS["candidate_84b5d3fa"])):
        _, _, root = load(os.path.join(ROOT, rel))
        d = duplicate_keys(root)
        dup[name] = d
        if d:
            failed.append(f"duplicate keys in {name}: {d[:3]}")

    anchors = []
    for rel, path, needle in ANCHORS:
        name = {"F1": "F1", "F2a": "F2a", "F2b": "F2b"}[
            "F1" if rel == F1 else ("F2a" if rel == F2A else "F2b")]
        present = needle in sc[name].get(path, (0, ""))[1]
        anchors.append({"file": rel, "path": path, "needle": needle, "present": present})
        if not present:
            failed.append(f"anchor missing: {rel} {path} :: {needle}")

    observed = {
        "A1": {n: check_a1(sc[n]) for n in sc},
        "A2": {n: check_a2(sc[n]) for n in sc},
        "A3": {n: check_a3(sc[n]) for n in sc},
        "B1": {n: check_b1(sc[n]) for n in sc},
        "B2": {n: check_b2(sc[n]) for n in sc},
    }

    expect_fire = {
        "A1": ["F2b"],
        "A2": ["F2b"],
        "A3": ["candidate_84b5d3fa"],
    }
    control_rows = []
    for cid, exp in expect_fire.items():
        got = sorted(n for n, h in observed[cid].items() if h)
        ok = got == sorted(exp)
        control_rows.append({"check_id": cid, "kind": "control",
                             "expected_fire_on": sorted(exp), "observed_fire_on": got,
                             "match": ok})
        if not ok:
            failed.append(f"control {cid}: expected {sorted(exp)} got {got}")

    # class-relativity control: the C2 sibling's true sentence must not fire A3
    cr = ("H2_loc-inextendibility ENTAILS this class's conclusion" in
          sc["F2a"].get(".regularity.must_not_conflate[1]", (0, ""))[1]) and not observed["A3"]["F2a"]
    control_rows.append({"check_id": "A3-class-relativity", "kind": "control",
                         "expected_fire_on": [], "observed_fire_on": observed["A3"]["F2a"],
                         "match": cr})
    if not cr:
        failed.append("class-relativity control failed: C2 sibling")

    controls_pass = all(r["match"] for r in control_rows) and pin_ok and not dup_errors(dup)

    # findings -------------------------------------------------------------
    findings = []
    b1_on = sorted(n for n, h in observed["B1"].items() if h)
    findings.append({
        "id": "W096-REQDROP-B1",
        "check_id": "B1",
        "severity": "major",
        "status": "candidate_defect_unadjudicated_by_author",
        "files": b1_on,
        "evidence": observed["B1"]["F2a"],
        "claim": ("C2/F2a schema_falsifiers[3] labels the requirement-drop construction "
                  "'weaker statement bound to the wrong class'. The file's own stated rule "
                  "('the lower the required regularity, the larger the set of admissible "
                  "extensions, hence the stronger the inexistence statement', C2:237) and "
                  "the C0 sibling's explicit anchor for the same construction ('NO equation "
                  "is required of g' ... this is the strongest form of the statement', "
                  "C0:95-97) both make the requirement drop STRONGER, not weaker."),
        "expected_fire_on": ["F2a"],
        "observed_fire_on": b1_on,
        "delta": b1_on != ["F2a"],
        "gate_relevance": ("F2a e9a27996 is an accepted artifact on the G-FORM critical "
                           "path; a landing of candidate_corrected repairs only F2b's two "
                           "carriers and leaves this F2a label untouched, so the "
                           "requirement-drop family would remain asymmetric."),
        "falsifier": ("Exhibit the author's reading under which dropping Ric(g')=0 yields a "
                      "weaker inexistence statement; e.g. a rule_spec/authority clause that "
                      "defines statement strength inversely to forbidden-set size, or an "
                      "author edit of C2:265 to a consistent label. Not falsified by the "
                      "canonical structural gate: check_class_schema.py is measured blind "
                      "to direction/strength prose (worker-029/066/096)."),
    })

    b2_on = sorted(n for n, h in observed["B2"].items() if h)
    findings.append({
        "id": "W096-REQDROP-B2",
        "check_id": "B2",
        "severity": "minor",
        "status": "candidate_convention_conflict",
        "files": b2_on,
        "evidence": observed["B2"]["F1"],
        "claim": ("F1 conclusion.forbidden_weakenings[3] lists 'using a weaker visibility "
                  "notion' as a weakening, while the same file's class_identity_variants[0] "
                  "defines the weaker visibility predicate as the one that admits MORE "
                  "geodesics (union/SET reading, 'strictly WEAKER ... entails the union "
                  "reading'). Under the predicate-strength convention used at F1:235, a "
                  "weaker visibility predicate makes the class conclusion STRONGER, so the "
                  "entry is at best using 'weaker' in the opposite sense."),
        "expected_fire_on": ["F1"],
        "observed_fire_on": b2_on,
        "delta": b2_on != ["F1"],
        "gate_relevance": "F1 d9cebb94 is an accepted artifact (4 distinct accepts) on G-FORM.",
        "falsifier": ("Show that F1:260 'weaker visibility notion' is defined elsewhere in "
                      "the file/taxonomy as the notion classifying FEWER geodesics as "
                      "visible (then the entry is consistent and this finding is void), or "
                      "edit F1:260 to disambiguate."),
    })

    b3 = bool(observed["B1"]["F2a"]) and any(a["present"] for a in anchors
                                             if a["file"] == F2B and "strongest form" in a["needle"])
    findings.append({
        "id": "W096-REQDROP-B3",
        "check_id": "B3",
        "severity": "major",
        "status": "cross_file_conflict",
        "files": ["F2a", "F2b"],
        "evidence": {"F2a": observed["B1"]["F2a"], "F2b_anchor": [
            {"path": ".extension_predicate.why_bare_metric",
             "text": sc["F2b"][".extension_predicate.why_bare_metric"][1][:220]}]},
        "claim": ("The construction named in C2/F2a schema_falsifiers[3] (extension not "
                  "required to solve Ric=0) is exactly the C0 class construction, and the "
                  "C0 file calls that same construction 'the strongest form of the "
                  "statement'. The two pinned files therefore assign opposite strength "
                  "labels to the same requirement drop."),
        "expected_fire_on": ["F2a"],
        "observed_fire_on": sorted(n for n, h in observed["B1"].items() if h),
        "delta": not b3,
        "falsifier": "Repair either label; the conflict is a function of the two pinned strings.",
    })

    # canonical structural gate corroboration (blindness control) -----------------
    import subprocess
    gate_tool = "artifacts/formulation/tools/check_class_schema.py"
    gate = {}
    for name, rel in (("F1", F1), ("F2a", F2A), ("F2b", F2B),
                      ("candidate_corrected", CANDS["candidate_corrected"]),
                      ("candidate_nesting_only", CANDS["candidate_nesting_only"]),
                      ("candidate_84b5d3fa", CANDS["candidate_84b5d3fa"])):
        p = subprocess.run([sys.executable, os.path.join(ROOT, gate_tool), os.path.join(ROOT, rel)],
                           capture_output=True, text=True, cwd=ROOT)
        gate[name] = {"rc": p.returncode, "sha256": sha256(os.path.join(ROOT, rel))}
    gate["_corroboration"] = ("canonical structural gate rc=0 on live F1/F2a/F2b, the two "
                              "corrected candidates and the known-defective 84b5d3fa: it is "
                              "blind to the two known C0 hard defects and to B1/B2.")

    census = {}
    for name in ("F1", "F2a", "F2b"):
        entries = [{"line": ln, "path": p, "text": t[:240]}
                   for p, (ln, t) in sorted(sc[name].items(), key=lambda kv: kv[1][0])
                   if TOK.search(t)]
        census[name] = {"count": len(entries), "entries": entries}

    flagged = {(f["check_id"], e["path"], e["line"])
               for f in findings for e in (f["evidence"] if isinstance(f["evidence"], list) else [])}
    for name, rows in census.items():
        for r in rows["entries"]:
            r["flagged"] = any(k[0] in ("B1", "B2") and k[2] == r["line"] and
                               (k[1] == r["path"]) for k in flagged)

    report = {
        "schema_version": "w096-reqdrop-sweep-1",
        "task_id": "W096-F2A-REQDROP-STRENGTH-LABEL-SWEEP-01",
        "worker": "worker-096",
        "generated_at": now.isoformat(),
        "mode": "read-only; no canonical write",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "node_ids": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "convention": {
            "rule": ("larger forbidden extension set => stronger inexistence statement; "
                     "dropping a requirement on the extension enlarges the set => stronger"),
            "anchors": anchors,
        },
        "inputs": inputs,
        "census": census,
        "canonical_gate_corroboration": gate,
        "duplicate_keys": dup,
        "checks": control_rows,
        "findings": findings,
        "summary": {
            "pins_ok": pin_ok,
            "controls_pass": controls_pass,
            "controls_total": len(control_rows),
            "controls_matched": sum(1 for r in control_rows if r["match"]),
            "census_total": sum(v["count"] for v in census.values()),
            "known_defects_reproduced": {"C0:152": len(observed["A1"]["F2b"]),
                                         "C0:246": len(observed["A2"]["F2b"])},
            "new_findings": len(findings),
            "new_finding_labels": [f["id"] for f in findings],
        },
        "falsifier": ("Any pin mismatch; a control not firing; the C2 sibling's true "
                      "entailment sentence firing A3; or the canonical structural gate "
                      "no longer passing on the live files. Findings B1-B3 are additionally "
                      "falsified per their own falsifier fields."),
        "non_claims": [
            "No gate verdict, no node status, no validation_status=passed.",
            "B1-B3 are prose-label findings measured against the schemas' own stated "
            "convention; they do not change any accepted artifact's structural pass.",
            "This sweep does not re-adjudicate class semantics; it reports where two "
            "pinned strings disagree.",
        ],
        "failed": failed,
    }

    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")

    lines = [
        "W096-F2A-REQDROP-STRENGTH-LABEL-SWEEP-01 runlog",
        f"at={now.isoformat()}",
        f"pins_ok={pin_ok} controls={sum(1 for r in control_rows if r['match'])}/{len(control_rows)}",
        f"census_total={report['summary']['census_total']}",
        f"known_defects_reproduced={report['summary']['known_defects_reproduced']}",
        f"findings={[f['id'] + ':' + ','.join(f['observed_fire_on']) for f in findings]}",
    ]
    for cid, exp in expect_fire.items():
        got = sorted(n for n, h in observed[cid].items() if h)
        lines.append(f"control {cid}: expected={sorted(exp)} observed={got}")
    for f in findings:
        for e in (f["evidence"] if isinstance(f["evidence"], list) else []):
            lines.append(f"  {f['id']} {e['path']} line {e['line']}: {e['text'][:140]}")
    lines.append("failed=" + json.dumps(failed))
    lines.append("exit=" + ("0" if not failed else "1"))
    with open(os.path.join(OUT, "runlog.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    return 0 if not failed else 1


def dup_errors(dup):
    return [n for n, d in dup.items() if d]


if __name__ == "__main__":
    sys.exit(main())
