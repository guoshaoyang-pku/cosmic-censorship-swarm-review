#!/usr/bin/env python3
"""F0 genericity two-slot coherence audit (worker-001, class-bound to AF-WCC-SCALAR-SPH).

Bounded task: at the PINNED canonical F0 taxonomy hash, test whether the artifact's own
genericity rules are satisfied by its class blocks and covered by its own certification
instrument.  Deterministic, fail-closed on hash drift, no network, no writes outside the
report path.

Rules under test (research_map/formulation_taxonomy.yaml, canonical rev5 0abb9ed8a961):
  L144  genericity_kind rule: "a generic-quantified claim must name genericity_kind AND
        genericity_topology; ..."
  L147  genericity_topology rule: "the topology or measure space in which genericity is
        defined; must be named before any theorem-status claim."
  L501  transfer T1 guard: "genericity_kind and genericity_topology must match exactly"

Checks:
  A  hash pin (canonical + supplement)                        -> exit 3 on drift
  B  per-class: generic-quantified conclusion? kind slot? topology slot?
  C  kind/conclusion-text coherence (kind=unresolved vs an asserted comeager set)
  D  scope conflict between L144 (unconditional) and L147 (theorem-status stage)
  E  instrument coverage: is genericity_topology accepted by validate_taxonomy.py?
  F  vacuity of the T1 transfer guard when the slot is absent everywhere

Self-test plants 4 defects and 2 controls; all must be classified as predicted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPPLEMENT_PIN = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"

# Tokens in genericity_kind that assert a topological (Baire) genericity kind.
BAIRE_TOKENS = {"baire_residual", "provisional_baire_residual", "residual_comeager"}
# Vocabulary allowed values, read from the artifact itself at runtime; fallback below.
FALLBACK_KIND_ALLOWED = ["baire_residual", "dense_open", "measure_one",
                         "provisional_baire_residual", "unresolved"]
FALLBACK_TOPOLOGY_ALLOWED = ["unresolved", "named_by_F1", "named_by_F2"]

GENERIC_TEXT_RE = re.compile(
    r"comeager|generic(?:ally)?|full[- ]measure|dense[- ]open|residual", re.IGNORECASE)
COMEAGER_TEXT_RE = re.compile(r"comeager", re.IGNORECASE)
FULL_MEASURE_TEXT_RE = re.compile(r"full[- ]measure", re.IGNORECASE)
DENSE_OPEN_TEXT_RE = re.compile(r"dense[- ]open", re.IGNORECASE)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_allowed_axis_names(validator_src: str) -> set[str]:
    """Extract the ALLOWED_FAMILY_AXES literal from the validator source."""
    m = re.search(r"ALLOWED_FAMILY_AXES\s*=\s*\{(.*?)\}", validator_src, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def check_taxonomy(tax: dict, allowed_axes: set[str], validator_src: str = "") -> list[dict]:
    """Return a list of finding dicts; empty list == no defect."""
    findings: list[dict] = []
    field_vocab = tax.get("field_vocabulary", {}) or {}
    kind_rule = str((field_vocab.get("genericity_kind") or {}).get("rule", ""))
    topo_block = field_vocab.get("genericity_topology") or {}
    topo_rule = str(topo_block.get("rule", ""))
    kind_allowed = (field_vocab.get("genericity_kind") or {}).get("allowed") or FALLBACK_KIND_ALLOWED
    topo_allowed = topo_block.get("allowed") or FALLBACK_TOPOLOGY_ALLOWED

    classes = tax.get("classes", {}) or {}
    class_ids = tax.get("class_ids") or sorted(classes.keys())

    rows = []
    for cid in class_ids:
        c = classes.get(cid) or {}
        axes = c.get("axes", {}) or {}
        con = c.get("conclusion", {}) or {}
        text = str(con.get("text", ""))
        kind = axes.get("genericity_kind", None)
        topo_present = "genericity_topology" in axes
        topo_val = axes.get("genericity_topology", None)
        generic = bool(GENERIC_TEXT_RE.search(text))
        comeager = bool(COMEAGER_TEXT_RE.search(text))
        full_measure = bool(FULL_MEASURE_TEXT_RE.search(text))
        dense_open = bool(DENSE_OPEN_TEXT_RE.search(text))
        rows.append(dict(class_id=cid, conclusion_type=con.get("type"), kind=kind,
                         topo_present=topo_present, topo_value=topo_val,
                         generic_quantified=generic, comeager=comeager,
                         full_measure=full_measure, dense_open=dense_open,
                         text_head=text.strip()[:120]))

    # C: kind vs conclusion-text coherence
    for r in rows:
        cid = r["class_id"]
        kind = str(r["kind"])
        if kind not in kind_allowed:
            findings.append(dict(
                id="G-KIND-TOKEN", class_id=cid, severity="medium",
                detail=f"axes.genericity_kind={kind!r} is not in the artifact's allowed set {kind_allowed}",
                falsifier=("Show an alias mapping in a pinned companion artifact that makes "
                           f"{kind!r} equivalent to an allowed token.")))
        if r["comeager"] and kind not in BAIRE_TOKENS and kind != "unresolved":
            findings.append(dict(
                id="G-KIND-TEXT-MISMATCH", class_id=cid, severity="medium",
                detail=(f"conclusion asserts a comeager set but genericity_kind={kind!r} does not "
                        "carry a Baire/residual kind"),
                falsifier=("Show that the class conclusion text is non-assertoric at this hash "
                           "(quoted/withdrawn/provisional) or that the kind token is aliased.")))
        if r["full_measure"] and kind not in ("measure_one", "unresolved"):
            findings.append(dict(
                id="G-KIND-TEXT-MISMATCH", class_id=cid, severity="medium",
                detail=(f"conclusion asserts a full-measure set but genericity_kind={kind!r}"),
                falsifier="Show a pinned alias making the token a measure token."))
        if kind == "unresolved" and (r["comeager"] or r["full_measure"] or r["dense_open"]):
            asserted = "comeager" if r["comeager"] else ("full measure" if r["full_measure"] else "dense open")
            findings.append(dict(
                id="G-KIND-TOPOLOGY-CONFLATION", class_id=cid, severity="medium",
                detail=(f"axes.genericity_kind='unresolved' (a kind-slot value) while the conclusion "
                        f"asserts a {asserted} set (line 414 for AF-WCC-SCALAR-SPH). 'Comeager' fixes "
                        "the KIND (Baire/residual); only the topology/ambient space remains unresolved, "
                        "and the artifact has a separate slot for that. The two slots are conflated."),
                falsifier=("Produce a pinned artifact defining genericity_kind='unresolved' as "
                           "'topology unresolved while the kind is fixed', or show the scalar "
                           "conclusion is not asserted at this hash.")))

    # B: topology slot coverage
    missing = [r["class_id"] for r in rows if not r["topo_present"]]
    if missing:
        findings.append(dict(
            id="G-TOPOLOGY-SLOT-ABSENT", class_id="ALL", severity="medium",
            affected=missing,
            detail=(f"{len(missing)}/{len(rows)} class axes blocks carry no genericity_topology, "
                    "although L144 makes naming it mandatory for a generic-quantified claim and "
                    "L147 says it must be named before any theorem-status claim"),
            falsifier=("Show that no class conclusion is generic-quantified at this hash, or that "
                       "a pinned companion artifact supplies the topology for every affected class.")))

    # D: rule scope conflict (textual, from the artifact's own words)
    if "must" in kind_rule and "AND genericity_topology" in kind_rule and "theorem-status" in topo_rule:
        findings.append(dict(
            id="G-RULE-SCOPE-CONFLICT", class_id="ALL", severity="low",
            detail=("L144 states the two-slot requirement unconditionally for a generic-quantified "
                    "claim; L147 stages the topology requirement at 'before any theorem-status claim'. "
                    "The two readings disagree for formulation-stage claims, and the artifact does "
                    "not say which governs. Strict reading: all four classes violate L144; lenient "
                    "reading: only the scalar kind/topology conflation is a defect."),
            falsifier=("Show a pinned scope note that resolves the two sentences (e.g. a definition "
                       "of 'generic-quantified claim' as theorem-status claim).")))

    # E: instrument coverage. Criterion: does the committed validator mention the slot at
    # all? ALLOWED_FAMILY_AXES constrains only disjointness[].decisive_axes names, NOT the
    # class axes dicts, so neither presence nor value of genericity_topology is checked.
    if "genericity_topology" not in validator_src:
        findings.append(dict(
            id="G-INSTRUMENT-GAP", class_id="ALL", severity="medium",
            detail=("validate_taxonomy.py contains no reference to genericity_topology, so the "
                    "253/253 suite is silent on L144/L147 in both directions: it does not require "
                    "the slot, and it does not reject the slot. Its ALLOWED_FAMILY_AXES literal "
                    "constrains only disjointness[].decisive_axes names, not class axes keys. "
                    "Measured: the proposed patch adding the slot passes the current validator "
                    "253/253 unchanged (proposed_validation_current_validator.json), which is the "
                    "control that refuted an earlier 'validator forbids the fix' reading."),
            falsifier=("Show a committed checker at the pinned FROZEN revision that inspects "
                       "genericity_topology presence or value; or show that the green suite "
                       "changes verdict when the slot is added/removed.")))

    # F: transfer-guard vacuity
    guards = []
    for entry in (tax.get("transfer_rules", {}) or {}).get("allowed", []) or []:
        guards.extend(entry.get("guards", []) or [])
    guard_refs_topo = any("genericity_topology" in str(g) for g in guards)
    if guard_refs_topo and missing:
        findings.append(dict(
            id="G-GUARD-VACUOUS", class_id="ALL", severity="low",
            detail=("the T1 guard requires genericity_kind and genericity_topology to match exactly, "
                    "but the slot is absent in every class, so the guard is vacuously true "
                    "(None == None) and transfers no information."),
            falsifier=("Show a class carrying the slot, or a checker that evaluates the guard "
                       "non-vacuously at this hash.")))

    return findings, rows


def run(paths: dict, tax: dict, allowed_axes: set[str], pin: str,
        validator_src: str = "") -> dict:
    measured = sha256_file(paths["canonical"])
    supplement = sha256_file(paths["supplement"])
    drift = []
    if measured != pin:
        drift.append(f"canonical {measured} != pinned {pin}")
    if supplement != SUPPLEMENT_PIN:
        drift.append(f"supplement {supplement} != pinned {SUPPLEMENT_PIN}")
    findings, rows = check_taxonomy(tax, allowed_axes, validator_src)
    return dict(
        audit="F0 genericity two-slot coherence",
        worker="worker-001", node_id="F0",
        class_id="AF-WCC-SCALAR-SPH",
        class_ids=list((tax.get("class_ids") or [])),
        pinned={"canonical": pin, "supplement": SUPPLEMENT_PIN},
        measured={"canonical": measured, "supplement": supplement},
        hash_drift=drift,
        verdict="FINDINGS" if findings else "NO_DEFECT",
        findings=findings,
        per_class=rows,
        validator_coverage=dict(
            mentions_genericity_topology="genericity_topology" in validator_src,
            decisive_axis_allowlist_size=len(allowed_axes)),
        scope_note=("author-side self-audit of a frozen artifact; not a reviewer verdict and "
                    "no theorem-status claim"),
    )


# ---------------------------------------------------------------- self-test
def _mk_tax(kind_by_class, topo_by_class):
    base = {"class_ids": ["C-A", "C-B"], "classes": {}}
    for cid in base["class_ids"]:
        axes = {"family": "WCC", "matter_model": "vacuum", "symmetry": "none_assumed",
                "asymptotics": "asymptotically_flat_3p1", "regularity_token": None,
                "genericity_kind": kind_by_class[cid], "conclusion_type": "weak_cosmic_censorship"}
        if topo_by_class.get(cid) is not None:
            axes["genericity_topology"] = topo_by_class[cid]
        base["classes"][cid] = {
            "axes": axes,
            "conclusion": {"type": "weak_cosmic_censorship",
                           "text": "For a comeager set G of data in the class, P holds."},
        }
    base["field_vocabulary"] = {
        "genericity_kind": {"rule": "a generic-quantified claim must name genericity_kind AND "
                                     "genericity_topology; 'generic' alone is not machine-readable",
                            "allowed": FALLBACK_KIND_ALLOWED},
        "genericity_topology": {"rule": "the topology or measure space in which genericity is "
                                        "defined; must be named before any theorem-status claim.",
                                "allowed": FALLBACK_TOPOLOGY_ALLOWED},
    }
    base["transfer_rules"] = {"allowed": [{"guards": ["genericity_kind and genericity_topology "
                                                      "must match exactly"]}]}
    return base


def self_test() -> int:
    cases = []
    allow_with = {"family", "genericity_kind", "genericity_topology"}
    vsrc_with = 'ALLOWED_FAMILY_AXES = {"family", "genericity_topology"}'
    allow_without = {"family", "genericity_kind"}
    # control 1: all slots present, coherent -> no defect. G-RULE-SCOPE-CONFLICT is
    # excluded by construction: it is a finding about the artifact's own rule TEXT and is
    # present in every fixture that quotes L144 and L147 verbatim, coherent or not.
    t = _mk_tax({"C-A": "provisional_baire_residual", "C-B": "provisional_baire_residual"},
                {"C-A": "unresolved", "C-B": "named_by_F1"})
    f, _ = check_taxonomy(t, allow_with, vsrc_with)
    residual = [x["id"] for x in f if x["id"] != "G-RULE-SCOPE-CONFLICT"]
    cases.append(("control_all_slots", residual == [], f"residual_findings={residual}"))
    # control 2: no generic quantifier -> no conflation (text is universal)
    t = _mk_tax({"C-A": "unresolved", "C-B": "unresolved"}, {"C-A": "unresolved", "C-B": "unresolved"})
    t["classes"]["C-A"]["conclusion"]["text"] = "For every datum in the class, P holds."
    t["classes"]["C-B"]["conclusion"]["text"] = "For every datum in the class, P holds."
    f, _ = check_taxonomy(t, allow_with, vsrc_with)
    cases.append(("control_no_generic_quantifier",
                  not any(x["id"] == "G-KIND-TOPOLOGY-CONFLATION" for x in f),
                  f"findings={[x['id'] for x in f]}"))
    # planted 1: kind unresolved + comeager text -> conflation
    t = _mk_tax({"C-A": "unresolved", "C-B": "provisional_baire_residual"},
                {"C-A": "unresolved", "C-B": "unresolved"})
    f, _ = check_taxonomy(t, allow_with, vsrc_with)
    cases.append(("planted_conflation",
                  any(x["id"] == "G-KIND-TOPOLOGY-CONFLATION" and x["class_id"] == "C-A" for x in f),
                  f"findings={[x['id'] for x in f]}"))
    # planted 2: missing topology slot -> slot-absent
    t = _mk_tax({"C-A": "provisional_baire_residual", "C-B": "provisional_baire_residual"},
                {"C-A": None, "C-B": "unresolved"})
    f, _ = check_taxonomy(t, allow_with, vsrc_with)
    cases.append(("planted_topology_absent",
                  any(x["id"] == "G-TOPOLOGY-SLOT-ABSENT" for x in f),
                  f"findings={[x['id'] for x in f]}"))
    # planted 3: validator allow-list lacks the slot -> instrument gap
    t = _mk_tax({"C-A": "provisional_baire_residual", "C-B": "provisional_baire_residual"},
                {"C-A": "unresolved", "C-B": "unresolved"})
    f, _ = check_taxonomy(t, allow_without, "")
    cases.append(("planted_instrument_gap",
                  any(x["id"] == "G-INSTRUMENT-GAP" for x in f),
                  f"findings={[x['id'] for x in f]}"))
    # planted 4: kind says full_measure but text says comeager -> mismatch
    t = _mk_tax({"C-A": "measure_one", "C-B": "provisional_baire_residual"},
                {"C-A": "unresolved", "C-B": "unresolved"})
    f, _ = check_taxonomy(t, allow_with, vsrc_with)
    cases.append(("planted_kind_text_mismatch",
                  any(x["id"] == "G-KIND-TEXT-MISMATCH" and x["class_id"] == "C-A" for x in f),
                  f"findings={[x['id'] for x in f]}"))
    ok = all(c[1] for c in cases)
    print(json.dumps({"self_test": "pass" if ok else "fail",
                      "cases": [{"name": n, "ok": bool(r), "detail": d} for n, r, d in cases]},
                     indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "research_map" / "formulation_taxonomy.yaml"))
    ap.add_argument("--supplement", default=str(ROOT / "artifacts" / "formulation" /
                                              "formulation_taxonomy.yaml"))
    ap.add_argument("--validator", default=str(ROOT / "artifacts" / "worker-01" /
                                              "validate_taxonomy.py"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--pin", default=CANONICAL_PIN)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    paths = dict(canonical=Path(args.file), supplement=Path(args.supplement))
    for k, p in paths.items():
        if not p.is_file():
            print(f"missing {k}: {p}", file=sys.stderr)
            return 3
    vsrc = Path(args.validator).read_text()
    allowed_axes = parse_allowed_axis_names(vsrc)
    tax = yaml.safe_load(paths["canonical"].read_text())
    out = run(paths, tax, allowed_axes, args.pin, validator_src=vsrc)
    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json:
        Path(args.json).write_text(text + "\n")
    print(text)
    if out["hash_drift"]:
        print("FAIL-CLOSED: hash drift", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
