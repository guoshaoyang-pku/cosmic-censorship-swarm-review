#!/usr/bin/env python3
"""W073-F0-GENERICITY-ADJUDICATION-01 -- independent adjudicator.

Question
--------
At the pinned F0 pair (declared taxonomy, class-contract supplement, FROZEN
rev28), what is the correct disposition of the contested finding F0V-S1 --
`AF-WCC-SCALAR-SPH.axes.genericity_kind == "unresolved"` coexisting with a
class conclusion that binds "a comeager set G" -- with respect to gate G-F0?

Three pre-registered readings are possible:
  H-BLOCK  the coexistence is a gate-blocking hard failure;
  H-DEFER  it is a real but declared / documented unresolved state, i.e. an
           objection that must be discharged before theorem-status promotion
           but does not block G-F0 as declared;
  H-VOID   there is no coexistence (the bytes are consistent).

The decision rule below is fixed before measurement and applied mechanically.
It deliberately does not consult the prior verdicts of worker-073 (revise,
F0V-S1 blocking) or worker-087 (accept, B3 non-blocking); those verdicts are
inputs to the disagreement, not evidence for the disposition.

This instrument is read-only over the repository. It imports no author-family
or prior-worker tooling; PyYAML is the only third-party dependency.

Exit codes: 0 = adjudication produced, 2 = a control did not fire as
predicted, 3 = input hash drift (no report written).
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

CST = timezone(timedelta(hours=8))

# Pins are pre-registered. Any drift aborts before measurement.
PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json":
        "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}

CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCALAR = "AF-WCC-SCALAR-SPH"

# D2 is triggered by an explicit theorem-status assertion. `status: frozen`
# alone is NOT treated as a theorem status in this project's vocabulary: byte
# freezing is governed by FROZEN.json, while `claims_theorem_status` is the
# artifact's own explicit flag.
THEOREM_STATUS_TOKENS = {"validated", "passed", "verified"}
DETERMINATE_GENERICITY_KINDS = {"baire_residual", "dense_open", "measure_one"}
GENERIC_QUANTIFIER_RE = re.compile(
    r"\b(comeager|generic|generically|dense[- ]open|dense[- ]escape|"
    r"full[- ]measure|residual)\b",
    re.IGNORECASE,
)
MERGED_REGULARITY_RE = re.compile(
    r"C\s*0?[\s_^{}()]*(?:or|and|/)[\s_^{}()]*C\s*0?2|"
    r"C\s*0?2[\s_^{}()]*(?:or|and|/)[\s_^{}()]*C\s*0?",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _construct_mapping(loader: StrictLoader, node, deep=False):
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key: {key!r}", key_node.start_mark,
            )
        seen[key] = True
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_strict(src):
    text = src.read_text(encoding="utf-8") if isinstance(src, Path) else src.read()
    return yaml.load(text, Loader=StrictLoader)


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return i
    return None


def lines_of(text: str, needle: str) -> list[int]:
    return [i for i, line in enumerate(text.splitlines(), start=1) if needle in line]


def line_in_range(text: str, needle: str, start_marker: str, end_marker: str) -> int | None:
    """First line containing `needle` inside the [start_marker, end_marker) window."""
    rows = text.splitlines()
    start = next((i for i, l in enumerate(rows) if start_marker in l), 0)
    end = next((i for i, l in enumerate(rows) if i > start and end_marker in l), len(rows))
    for i in range(start, end):
        if needle in rows[i]:
            return i + 1
    return None


def measure(doc: dict) -> dict:
    """Mechanical per-class measurement at the pinned bytes."""
    out = {"classes": {}, "file_status": {}, "vocabulary": {}}
    fv = doc.get("field_vocabulary", {})
    out["vocabulary"] = {
        "genericity_kind_allowed": fv.get("genericity_kind", {}).get("allowed"),
        "genericity_kind_rule": fv.get("genericity_kind", {}).get("rule"),
        "genericity_topology_allowed": fv.get("genericity_topology", {}).get("allowed"),
        "genericity_topology_rule": fv.get("genericity_topology", {}).get("rule"),
    }
    out["file_status"] = {
        "status": doc.get("status"),
        "claims_theorem_status": doc.get("claims_theorem_status"),
        "provenance_claims_theorem_status": (doc.get("provenance") or {}).get(
            "claims_theorem_status"
        ),
        "asserts_no_theorem": "asserts no theorem" in str(doc.get("scope_statement", "")),
    }
    for cid in CLASSES:
        cls = (doc.get("classes") or {}).get(cid, {})
        axes = cls.get("axes") or {}
        conclusion = cls.get("conclusion") or {}
        text = str(conclusion.get("text", ""))
        hyp = {h.get("id"): h for h in (cls.get("hypotheses") or [])}
        quant = sorted({m.group(0).lower() for m in GENERIC_QUANTIFIER_RE.finditer(text)})
        out["classes"][cid] = {
            "family": axes.get("family"),
            "genericity_kind": axes.get("genericity_kind"),
            "genericity_topology_present": "genericity_topology" in axes,
            "genericity_value_status": cls.get("genericity_value_status"),
            "h4_unresolved": hyp.get("H4", {}).get("unresolved"),
            "h4_owned_by": hyp.get("H4", {}).get("owned_by"),
            "conclusion_type": conclusion.get("type"),
            "generic_quantifier_tokens": quant,
            "generic_quantified": bool(quant),
        }
    out["declarations"] = {
        "coverage_gap_CG1": "CG1"
        in [g.get("id") for g in (doc.get("coverage_gaps") or [])],
        "open_question_Q1": "Q1"
        in [q.get("id") for q in (doc.get("open_questions") or [])],
        "scope_statement_names_owners": "owned by the downstream schema nodes"
        in str(doc.get("scope_statement", "")),
    }
    return out


def supplement_measure(doc: dict) -> dict:
    axis = ((doc.get("axis_registry") or {}).get("genericity_axis")) or {}
    frozen = axis.get("frozen") or {}
    return {
        "values": axis.get("values"),
        "frozen": frozen,
        "scalar_frozen": frozen.get(SCALAR),
        "scalar_unresolved_declared": frozen.get(SCALAR) == "unresolved",
        "scalar_note": axis.get("scalar_note"),
        "scalar_token_in_values": frozen.get(SCALAR) in (axis.get("values") or []),
    }


def detect_merged(doc: dict) -> list[str]:
    """Class-merge non-vacuity control: merged C0/C2 tokens anywhere in a class."""
    hits = []
    for cid in CLASSES:
        cls = (doc.get("classes") or {}).get(cid, {})
        fields = [str((cls.get("conclusion") or {}).get("type", ""))]
        fields += [str(v) for v in (cls.get("axes") or {}).values()]
        for f in fields:
            if MERGED_REGULARITY_RE.search(f):
                hits.append(f"{cid}:{f}")
    return hits


def classify(declared: dict, supplement: dict) -> dict:
    """The pre-registered decision rule. Pure function of the two documents."""
    m = measure(declared)
    s = supplement_measure(supplement)
    reasons: list[str] = []

    scalar = m["classes"][SCALAR]
    kind = scalar["genericity_kind"]
    allowed = m["vocabulary"]["genericity_kind_allowed"] or []
    theorem_status_asserted = bool(m["file_status"]["claims_theorem_status"]) or bool(
        m["file_status"]["provenance_claims_theorem_status"]
    ) or (m["file_status"]["status"] in THEOREM_STATUS_TOKENS)

    # --- F1: the contested coexistence -----------------------------------
    quantified = bool(scalar["generic_quantified"])
    if not quantified:
        f1 = "RESOLVED"
        reasons.append("F1: the scalar conclusion carries no generic quantifier")
    elif kind not in allowed:
        f1 = "BLOCK"
        reasons.append(f"F1: genericity_kind={kind!r} is outside the allowed vocabulary")
    elif kind in DETERMINATE_GENERICITY_KINDS:
        f1 = "RESOLVED"
        reasons.append(f"F1: genericity_kind={kind!r} is a determinate generic token")
    elif theorem_status_asserted:
        f1 = "BLOCK"
        reasons.append(
            "F1: theorem status is asserted while the scalar genericity kind is unresolved"
        )
    else:
        declarations = m["declarations"]
        declared_count = sum(
            [
                scalar["genericity_value_status"] == "unresolved_pending_L1",
                scalar["h4_unresolved"] is True,
                declarations["coverage_gap_CG1"],
                declarations["open_question_Q1"],
            ]
        )
        if declared_count >= 3 and s["scalar_unresolved_declared"]:
            f1 = "DEFER"
            reasons.append(
                "F1: the unresolved state is declared in the artifact "
                f"({declared_count}/4 declaration markers) and corroborated by the "
                "companion supplement (scalar frozen = unresolved)"
            )
        else:
            f1 = "BLOCK"
            reasons.append(
                "F1: unresolved kind coexists with a comeager conclusion without "
                f"sufficient declaration (declarations {declared_count}/4, companion "
                f"corroboration {s['scalar_unresolved_declared']})"
            )

    # --- F2: the genericity_topology slot gap ----------------------------
    missing_topology = [c for c in CLASSES if not m["classes"][c]["genericity_topology_present"]]
    quantified_classes = [c for c in CLASSES if m["classes"][c]["generic_quantified"]]
    if not missing_topology:
        f2 = "RESOLVED"
    elif theorem_status_asserted:
        f2 = "BLOCK"
        reasons.append(
            f"F2: genericity_topology is due before theorem status but absent on "
            f"{len(missing_topology)}/4 classes"
        )
    else:
        f2 = "DEFER"
        reasons.append(
            f"F2: genericity_topology absent on {len(missing_topology)}/4 class axes "
            f"({len(quantified_classes)}/4 classes carry a generic quantifier); the "
            "artifact's own topology rule defers naming until a theorem-status claim exists"
        )

    # --- F3: pair consistency on the scalar genericity state -------------
    f3 = "CONSISTENT" if s["scalar_unresolved_declared"] else "DIVERGENT"
    if f3 == "DIVERGENT":
        reasons.append("F3: companion supplement does not record the scalar kind as unresolved")

    # --- F4: supplement value-list hygiene (secondary observation) -------
    f4 = "TOKEN_OUTSIDE_VALUE_LIST" if not s["scalar_token_in_values"] else "IN_VALUE_LIST"

    # --- F5: class-merge guard (non-vacuity control) ---------------------
    merged = detect_merged(declared)
    f5 = "FOUND" if merged else "CLEAR"
    if merged:
        reasons.append(f"F5: merged regularity token(s) found: {merged}")

    states = {f1, f2, f5}
    if "BLOCK" in states or f5 == "FOUND":
        overall = "H-BLOCK"
    elif "DEFER" in states:
        overall = "H-DEFER"
    else:
        overall = "H-VOID"

    return {
        "overall": overall,
        "F1_scalar_unresolved_vs_comeager": f1,
        "F2_genericity_topology_slot": f2,
        "F3_pair_consistency": f3,
        "F4_supplement_value_list": f4,
        "F5_class_merge": f5,
        "reasons": reasons,
        "measurements": m,
        "supplement": s,
    }


# ---------------------------------------------------------------------------
# Controls: each mutates an in-memory copy and states the expected verdict
# before the mutation is applied. A control that does not fire voids the run.
# ---------------------------------------------------------------------------
def run_controls(declared: dict, supplement: dict) -> list[dict]:
    results = []

    def check(cid, description, doc_mut, sup_mut, expect):
        d = copy.deepcopy(declared)
        s = copy.deepcopy(supplement)
        doc_mut(d)
        sup_mut(s)
        got = classify(d, s)
        results.append(
            {
                "control": cid,
                "description": description,
                "expected": expect,
                "observed": got["overall"],
                "observed_detail": {
                    "F1": got["F1_scalar_unresolved_vs_comeager"],
                    "F2": got["F2_genericity_topology_slot"],
                    "F3": got["F3_pair_consistency"],
                    "F5": got["F5_class_merge"],
                },
                "fired": got["overall"] == expect,
            }
        )

    check(
        "C1_resolved_kind",
        "set the scalar genericity_kind to baire_residual (in-vocabulary resolved token)",
        lambda d: d["classes"][SCALAR]["axes"].__setitem__("genericity_kind", "baire_residual"),
        lambda s: None,
        "H-DEFER",  # F2 topology gap remains; F1 clears
    )
    check(
        "C2_out_of_vocabulary_kind",
        "set the scalar genericity_kind to a token outside the allowed list",
        lambda d: d["classes"][SCALAR]["axes"].__setitem__("genericity_kind", "not_a_token"),
        lambda s: None,
        "H-BLOCK",
    )
    check(
        "C3_theorem_status_asserted",
        "assert theorem status while the scalar kind stays unresolved",
        lambda d: (d.__setitem__("claims_theorem_status", True), d.__setitem__("status", "frozen")),
        lambda s: None,
        "H-BLOCK",
    )
    check(
        "C4_declarations_removed",
        "remove the deferral declarations (value status, H4.unresolved, CG1, Q1) and companion record",
        lambda d: (
            d["classes"][SCALAR].pop("genericity_value_status", None),
            d["classes"][SCALAR]["hypotheses"][3].pop("unresolved", None),
            d.pop("coverage_gaps", None),
            d.pop("open_questions", None),
        ),
        lambda s: s["axis_registry"]["genericity_axis"]["frozen"].__setitem__(SCALAR, "residual_comeager"),
        "H-BLOCK",
    )
    check(
        "C5_quantifier_removed",
        "remove the comeager quantifier from the scalar conclusion",
        lambda d: d["classes"][SCALAR]["conclusion"].__setitem__(
            "text", "Every member of the class has a maximal development with the stated visibility property."
        ),
        lambda s: None,
        "H-DEFER",  # F1 clears (no coexistence); F2 topology gap remains
    )
    check(
        "C6_topology_slot_added",
        "add genericity_topology to all four class axes",
        lambda d: [d["classes"][c]["axes"].__setitem__("genericity_topology", "unresolved") for c in CLASSES],
        lambda s: None,
        "H-DEFER",  # F1 still deferred; F2 clears
    )
    check(
        "C7_merged_regularity_control",
        "inject a merged C0-or-C2 conclusion_type (class-merge non-vacuity control)",
        lambda d: d["classes"]["AF-SCC-C2-VAC-GEN"]["conclusion"].__setitem__(
            "type", "strong_cosmic_censorship_C0_or_C2"
        ),
        lambda s: None,
        "H-BLOCK",
    )
    check(
        "C8_companion_diverges",
        "flip the companion supplement's scalar record to residual_comeager",
        lambda d: None,
        lambda s: s["axis_registry"]["genericity_axis"]["frozen"].__setitem__(SCALAR, "residual_comeager"),
        "H-BLOCK",
    )
    check(
        "C9_file_frozen_no_theorem_flag",
        "freeze the file but keep claims_theorem_status false (status alone is not theorem status)",
        lambda d: d.__setitem__("status", "frozen"),
        lambda s: None,
        "H-DEFER",
    )
    return results


def main() -> int:
    # --- drift guard before any measurement ------------------------------
    measured = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"DRIFT: missing {rel}", file=sys.stderr)
            return 3
        got = sha256_file(p)
        measured[rel] = got
        if got != expected:
            print(f"DRIFT: {rel}\n  expected {expected}\n  measured {got}", file=sys.stderr)
            return 3

    declared_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text(encoding="utf-8")
    supplement_path = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
    supplement_text = supplement_path.read_text(encoding="utf-8")

    declared = load_strict(ROOT / "research_map/formulation_taxonomy.yaml")
    supplement = load_strict(supplement_path)
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())

    # duplicate-key control: the strict loader must reject a duplicate key
    dup_control = {"fired": False}
    try:
        load_strict(io.StringIO("a: 1\na: 2\n"))
    except yaml.constructor.ConstructorError:
        dup_control["fired"] = True

    result = classify(declared, supplement)
    controls = run_controls(declared, supplement)
    control_failures = [c["control"] for c in controls if not c["fired"]]

    evidence = {
        "declared_taxonomy": {
            "scalar_axes_genericity_kind_line": line_of(
                declared_text, 'genericity_kind: "unresolved"'
            ),
            "scalar_conclusion_comeager_line": line_of(
                declared_text, "For a comeager set G of data in the class"
            ),
            "scalar_value_status_line": line_of(
                declared_text, 'genericity_value_status: "unresolved_pending_L1"'
            ),
            "scalar_H4_unresolved_line": line_in_range(
                declared_text,
                "unresolved: true",
                '"AF-WCC-SCALAR-SPH":',
                "# Pairwise disjointness",
            ),
            "kind_allowed_line": line_of(declared_text, 'allowed: ["baire_residual"'),
            "kind_rule_line": line_of(declared_text, "a generic-quantified claim must name"),
            "topology_rule_line": line_of(
                declared_text, "must be named before any theorem-status claim"
            ),
            "status_line": line_of(declared_text, 'status: "draft_unverified"'),
            "claims_theorem_status_lines": lines_of(declared_text, "claims_theorem_status: false"),
            "CG1_line": line_of(declared_text, 'id: "CG1"'),
            "Q1_line": line_of(declared_text, 'id: "Q1"'),
        },
        "supplement": {
            "genericity_axis_frozen_line": line_of(
                supplement_text, "AF-WCC-SCALAR-SPH: unresolved"
            ),
            "scalar_note_line": line_of(supplement_text, "scalar_note:"),
        },
        "frozen_rev28": {
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "logical_artifact_F0_declared": (
                frozen.get("logical_artifacts") or {}
            ).get("F0-declared-taxonomy", {}).get("sha256"),
            "logical_artifact_F0_supplement": (
                frozen.get("logical_artifacts") or {}
            ).get("F0-class-contract-supplement", {}).get("sha256"),
        },
    }

    report = {
        "schema_version": "0.1",
        "artifact_type": "adjudication_report",
        "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
        "actor": "worker-073",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": CLASSES,
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "review_kind": "finding_disposition_adjudication",
        "counts_as_full_schema_verdict": False,
        "independent_of_prior_verdicts": True,
        "question": (
            "What is the correct disposition of F0V-S1 (AF-WCC-SCALAR-SPH "
            "axes.genericity_kind='unresolved' coexisting with a comeager-quantified class "
            "conclusion) with respect to gate G-F0 at the pinned F0 pair?"
        ),
        "decision_rule_pre_registered": [
            "D1 out-of-vocabulary genericity_kind token -> H-BLOCK",
            "D2 theorem status asserted while kind is unresolved -> H-BLOCK; theorem status means claims_theorem_status true at either location, or status in {validated,passed,verified}; status 'frozen' alone is byte-freezing (FROZEN.json), not a theorem claim",
            "D3 coexistence plus >=3/4 explicit deferral declarations plus companion corroboration -> H-DEFER",
            "D4 coexistence with insufficient declaration -> H-BLOCK",
            "D5 quantified conclusion with a determinate in-vocabulary kind -> F1 resolved",
            "D6 any merged C0/C2 regularity token in a class -> H-BLOCK (non-vacuity guard)",
        ],
        "pins": PINS,
        "pins_stable_during_run": measured,
        "adjudication": {
            "overall": result["overall"],
            "F1_scalar_unresolved_vs_comeager": result["F1_scalar_unresolved_vs_comeager"],
            "F2_genericity_topology_slot": result["F2_genericity_topology_slot"],
            "F3_pair_consistency": result["F3_pair_consistency"],
            "F4_supplement_value_list": result["F4_supplement_value_list"],
            "F5_class_merge": result["F5_class_merge"],
            "reasons": result["reasons"],
        },
        "measurements": result["measurements"],
        "supplement_measurements": result["supplement"],
        "evidence_lines": evidence,
        "controls": controls,
        "duplicate_key_loader_control": dup_control,
        "control_failures": control_failures,
        "prior_verdict_split": {
            "worker-073_prior": "revise 3.5, F0V-S1 labelled blocking hard failure",
            "worker-087_prior": "accept 4.0, B3 same observation labelled non-blocking declared deferral",
            "adjudicated": (
                "The observation is confirmed in both verdicts. The blocking label is not supported "
                "at the pinned bytes: the value is in-vocabulary, the artifact declares no theorem "
                "status and gates topology naming to theorem-status claims, and the companion "
                "supplement independently records the scalar kind as unresolved. F0V-S1 is therefore "
                "reclassified as a must-discharge-before-promotion objection, not a G-F0 hard failure."
            ),
        },
        "disposition": {
            "for_gate_G-F0": "non-blocking objection (advisory)",
            "accept_with_objection_is_consistent": True,
            "must_discharge_before": (
                "any theorem-status promotion for AF-WCC-SCALAR-SPH, or any F0 closure revision "
                "that fixes the scalar class's genericity"
            ),
            "required_actions": [
                "name genericity_topology in every class axes block (4/4 currently absent; due at theorem-status promotion per the artifact's own topology rule)",
                "either resolve the scalar genericity_kind to a determinate token (the supplement freezes residual_comeager for the three vacuum classes) or mark the comeager quantifier in the scalar conclusion as pending",
            ],
        },
        "erratum": {
            "target": "worker-073 prior review event w073-f0frozen-review-20260912T004619",
            "change": (
                "hard_failures F0V-S1 severity reclassified blocking -> advisory-conditional; "
                "the underlying measurement and the finding text are unchanged"
            ),
            "scope": "disposition only; no gate verdict, node status or validation_status is set",
        },
        "falsifiers": [
            "a rule at the pinned bytes that makes an unresolved genericity_kind incompatible with a comeager-phrased class conclusion at draft_unverified status without a theorem-status claim",
            "a theorem-status assertion at the pinned bytes (claims_theorem_status true, or status frozen/validated/passed/verified) that triggers the naming obligation",
            "a companion supplement record showing the scalar genericity resolved, which would make the pair divergent and re-open the blocking reading",
            "a controller or reviewer adjudication that cites a declared G-F0 criterion making genericity resolution a gate requirement",
        ],
        "non_claims": [
            "asserts no theorem, counterexample or numerical result",
            "does not set a gate verdict, node status or validation_status",
            "does not re-review the full F0 schema; it adjudicates one finding's disposition",
            "does not endorse the scalar class's unresolved genericity as final; it is a promotion blocker",
        ],
        "reproduce": "python3 artifacts/worker-073/f0_genericity_adjudication/adjudicate.py",
    }

    if control_failures or not dup_control["fired"]:
        print("CONTROL FAILURE:", control_failures, dup_control, file=sys.stderr)
        (OUT / "control_failure.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        return 2

    (OUT / "report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"overall={result['overall']}")
    for r in result["reasons"]:
        print(" -", r)
    print(f"controls={sum(c['fired'] for c in controls)}/{len(controls)} fired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
