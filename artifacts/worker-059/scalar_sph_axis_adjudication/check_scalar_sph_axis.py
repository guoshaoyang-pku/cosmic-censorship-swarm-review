#!/usr/bin/env python3
"""W059-SCALARSPH-AXIS-ADJ-01 independent instrument.

Cross-artifact adjudication of the AF-WCC-SCALAR-SPH genericity/record binding
across the two FROZEN-rev28-pinned F0 logical artifacts, with token legality
measured against the two independent registries.

Inputs (pinned snapshot, all hashes asserted in R5):
  A  : research_map/formulation_taxonomy.yaml            (declared F0, rev5)
  B  : artifacts/formulation/formulation_taxonomy.yaml   (F0-R supplement, rev9)
  R1 : artifacts/formulation/VOCAB_ALIASES.json
  R2 : artifacts/formulation/rule_spec.json
  F  : artifacts/formulation/FROZEN.json                 (rev28 pins)
  M  : research_map/research_map.json snapshot           (claims audit)

No canonical-gate imports: stdlib + PyYAML only.  The canonical consistency
tool is executed as an opaque subprocess inside a throwaway sandbox tree so
that the canonical evidence file is never mutated.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCALAR = "AF-WCC-SCALAR-SPH"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", SCALAR]
PIN = {
    "A": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "B": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "R1": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "R2": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "F": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}
SET_PAT = re.compile(r"J\s*\^?-?\s*\(?\s*I\s*\+", re.I)
TAIL_PAT = re.compile(r"tail", re.I)
GENERIC_PAT = re.compile(r"comeager|generic|dense|full[-_ ]measure", re.I)


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _no_dup(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        kk = loader.construct_object(k, deep=deep)
        if kk in keys:
            raise ValueError(f"duplicate mapping key: {kk!r}")
        keys.add(kk)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def syaml(path):
    return yaml.load(Path(path).read_text(), Loader=StrictLoader)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strip_brackets(text):
    """Remove editorial [label: ...] annotation spans so only assertive text is scanned.

    Numeric intervals such as [0,T) are kept (they carry no 'word:' prefix).
    """
    return re.sub(r"\[(?:rev\d+|[A-Za-z][A-Za-z0-9 _-]{0,24}):[^\[\]]*\]", " ", text)


def canon_kind(R1, tok):
    for c, al in (R1.get("genericity_kind") or {}).items():
        if tok == c or tok in al:
            return c, ("canonical" if tok == c else "alias")
    return None, "unregistered"


def run_checks(A, B, R1, R2, F, M):
    """Return an ordered list of check dicts."""
    out = []

    def add(cid, desc, expected, measured, ok):
        out.append({"id": cid, "desc": desc, "expected": expected,
                    "measured": measured, "pass": bool(ok)})

    # ---------------- structural ----------------
    a_ids = list(A.get("class_ids") or [])
    a_cls = list((A.get("classes") or {}).keys())
    b_frozen = list(B.get("frozen_classes") or [])
    b_contracts = list((B.get("class_contracts") or {}).keys())
    add("S1", "canonical parses with no duplicate mapping keys",
        "parsed", "parsed", True)
    add("S2", "supplement parses with no duplicate mapping keys",
        "parsed", "parsed", True)
    add("S3", "four-class id set identical across A.class_ids / A.classes / B.frozen_classes / B.class_contracts",
        sorted(CLASSES), sorted(set(map(str, a_ids + a_cls + b_frozen + b_contracts))),
        sorted(set(a_ids)) == sorted(set(a_cls)) == sorted(set(b_frozen)) == sorted(set(b_contracts)) == sorted(CLASSES))
    add("S4", "AF-WCC-SCALAR-SPH present in both artifacts",
        True, SCALAR in a_cls and SCALAR in b_contracts, SCALAR in a_cls and SCALAR in b_contracts)

    ac = A["classes"][SCALAR]
    bc = B["class_contracts"][SCALAR]
    axis = ac.get("axes") or {}
    comp = bc.get("components") or {}

    # ---------------- cross-artifact contract ----------------
    add("X1", "family WCC == supplement components.censorship",
        "WCC", f"{axis.get('family')} / {comp.get('censorship')}",
        axis.get("family") == comp.get("censorship") == "WCC")
    add("X2", "matter_model massless_scalar_field == supplement matter prose",
        "massless_scalar_field", f"{axis.get('matter_model')} / {comp.get('matter')}",
        axis.get("matter_model") == "massless_scalar_field"
        and "massless scalar field" in str(comp.get("matter", "")).lower())
    add("X3", "symmetry spherical on both sides",
        "spherical", f"{axis.get('symmetry')} / {comp.get('symmetry')}",
        axis.get("symmetry") == comp.get("symmetry") == "spherical")
    add("X4", "WCC regularity token absent (null) on both sides",
        "null/none", f"{axis.get('regularity_token')} / {comp.get('regularity_token')}",
        axis.get("regularity_token") is None and comp.get("regularity_token") == "none")
    ctok = str(axis.get("conclusion_type"))
    concl_map = R1.get("conclusion_type") or {}
    ct_canon = None
    ct_class = "unregistered"
    for c, al in concl_map.items():
        if ctok == c or ctok in al:
            ct_canon, ct_class = c, ("canonical" if ctok == c else "alias")
    add("X5", "conclusion_type canonical-equivalent across A/B and registered in R1",
        "weak_cosmic_censorship/canonical",
        f"A={ctok} B={bc.get('conclusion_type')} R1={ct_class}",
        ctok == str(bc.get("conclusion_type")) == "weak_cosmic_censorship" and ct_class == "canonical")

    concl_text = str((ac.get("conclusion") or {}).get("text") or "")
    assertive = strip_brackets(concl_text)
    add("X6", "scalar conclusion asserts the single-q TAIL predicate and no assertive set-based J-(I+) predicate",
        "tail predicate, no SET",
        f"tail={bool(TAIL_PAT.search(assertive))} set_assertive={bool(SET_PAT.search(assertive))}",
        bool(TAIL_PAT.search(assertive)) and not SET_PAT.search(assertive)
        and "for every q in I+" in assertive and "J^-(q)" in assertive)
    bpred = str(bc.get("conclusion_predicate") or "")
    add("X7", "supplement scalar conclusion_predicate is the WCC visibility predicate",
        "visibility from I+", bpred[:80],
        "visible from I+" in bpred and "inextendib" not in bpred.lower())
    add("X8", "scalar exclusions non-empty both sides and exclude SCC/non-spherical content",
        "non-empty/SCC-excluded",
        f"lenA={len(ac.get('exclusions') or [])} lenB={len(bc.get('exclusions') or [])}",
        bool(ac.get("exclusions")) and bool(bc.get("exclusions"))
        and any("non-spherical" in str(x).lower() for x in ac["exclusions"])
        and any("scc" in str(x).lower() or "inextendib" in str(x).lower() for x in bc["exclusions"]))
    add("X9", "test cases present on both sides",
        True, bool(ac.get("test_cases")) and bool(bc.get("positive_test_case")),
        bool(ac.get("test_cases")) and bool(bc.get("positive_test_case")))

    # ---------------- genericity binding ----------------
    kind = str(axis.get("genericity_kind"))
    allowed = ((A.get("field_vocabulary") or {}).get("genericity_kind") or {}).get("allowed") or []
    r2_vocab = ((R2.get("vocabularies") or {}).get("genericity_kind")) or []
    r1_canon, r1_class = canon_kind(R1, kind)
    add("G1", "scalar genericity_kind is in F0's own field_vocabulary.allowed",
        "member", f"{kind} in {allowed}", kind in allowed)
    add("G2", "scalar genericity_kind is in the frozen rule_spec vocabulary (R2)",
        "member", f"{kind} in {r2_vocab}", kind in r2_vocab)
    add("G3", "scalar genericity_kind is registered in R1 (canonical key or declared alias)",
        "registered", f"{kind} -> {r1_class} (canonical={r1_canon})", r1_class != "unregistered")
    topo_present = "genericity_topology" in axis
    add("G4", "scalar axes instantiates the declared genericity_topology slot required for a generic-quantified claim",
        "slot present", f"present={topo_present} generic_quantified={bool(GENERIC_PAT.search(assertive))}",
        topo_present)
    topo_counts = {cid: ("genericity_topology" in ((A["classes"][cid].get("axes")) or {})) for cid in CLASSES}
    add("G5", "genericity_topology instantiated in every class of the declared taxonomy",
        "4/4", f"{sum(topo_counts.values())}/4 {topo_counts}", all(topo_counts.values()))
    b_frozen_kind = str((((B.get("axis_registry") or {}).get("genericity_axis") or {}).get("frozen") or {}).get(SCALAR))
    b_values = ((B.get("axis_registry") or {}).get("genericity_axis") or {}).get("values") or []
    add("G6", "supplement freezes a scalar genericity value that is a member of its own values list",
        "member", f"{b_frozen_kind} in {b_values}", b_frozen_kind in [str(v) for v in b_values])
    a_canon_kind, a_class_kind = canon_kind(R1, kind)
    b_canon_kind, b_class_kind = canon_kind(R1, b_frozen_kind)
    add("G7", "supplement and canonical agree on the scalar genericity token up to R1 alias equivalence",
        f"equal-up-to-alias", f"A({kind})={a_canon_kind} B({b_frozen_kind})={b_canon_kind}",
        a_canon_kind == b_canon_kind)
    note = str(((B.get("axis_registry") or {}).get("genericity_axis") or {}).get("scalar_note") or "")
    a_rev = A.get("revision")
    note_cites_rev3 = bool(re.search(r"worker-01 rev3", note))
    note_says_provisional = "provisional" in note.lower()
    add("G8", "supplement scalar_note provenance matches the declared artifact (rev5, kind=unresolved)",
        "no stale rev3/provisional claim",
        f"note rev3={note_cites_rev3} provisional={note_says_provisional}; A rev={a_rev} kind={kind}",
        not note_cites_rev3 and not note_says_provisional)
    h4 = next((h for h in (ac.get("hypotheses") or []) if h.get("id") == "H4"), {})
    owned = str(h4.get("owned_by") or "")
    b_node = str(bc.get("node_id") or "")
    add("G9", "unresolved-genericity ownership is consistent across A.H4, B.scalar_note and B.class_contracts node_id",
        "single owner",
        f"A.H4={owned[:46]!r} B.note_future_node={'future node' in note} B.node_id={b_node[:34]!r}",
        ("no F-node" in owned) and ("future node" not in note) and (not b_node.startswith("unmapped")))
    f_nodes = {cid: n.get("class_id") for g in (M.get("groups") or []) if str(g.get("group_id")) == "formulation"
               for n in (g.get("nodes") or []) for cid in [str(n.get("class_id"))]}
    formulation_owns_scalar = any(SCALAR in str(v) for v in f_nodes.values())
    n0_node = [n for g in (M.get("groups") or []) for n in (g.get("nodes") or [])
               if n.get("node_id") == "N0" or "scalar-wave" in str(n.get("label", "")).lower()]
    n0_class = str(n0_node[0].get("class_id")) if n0_node else ""
    add("G10", "pinned map has no formulation F-node owning the scalar class (A.H4/CG1 correct; B 'future node' unsupported)",
        "no formulation F-node",
        f"formulation_owns_scalar={formulation_owns_scalar} N0_class={n0_class}",
        not formulation_owns_scalar and SCALAR in n0_class)

    # ---------------- D-records and certification ----------------
    d1a = next((d for d in ((A.get("class_scope_adjudication") or {}).get("resolved_divergences") or []) if d.get("id") == "D1"), {})
    add("R1c", "D1 record is resolved and the canonical WCC conclusion carries the single-q tail predicate",
        "resolved/tail", f"D1={d1a.get('status')} set_assertive={bool(SET_PAT.search(assertive))}",
        d1a.get("status") == "resolved" and not SET_PAT.search(assertive))
    d3a = next((d for d in ((A.get("class_scope_adjudication") or {}).get("resolved_divergences") or []) if d.get("id") == "D3"), {})
    d3b = next((d for d in ((B.get("contract_divergences") or {}).get("items") or []) if d.get("id") == "D3"), {})
    res_a = str(d3a.get("resolution") or "")
    cls_b = str(d3b.get("class") or "")
    res_b = str(d3b.get("resolution") or "")
    a_all_four = ("ALL FOUR" in res_a.upper()) and (SCALAR in res_a)
    b_three = ("three vacuum" in cls_b.lower()) and (SCALAR not in cls_b) and (SCALAR not in res_b)
    add("R2c", "D3 discharge record has the same class scope in A and B (no cross-artifact contradiction)",
        "same scope", f"A_all_four={a_all_four} B_three_vacuum_only={b_three}",
        not (a_all_four and b_three))
    add("R2c_evidence", "D3 scope texts quoted for the contradiction",
        "quoted", json.dumps({"A_resolution": res_a[:150], "B_class": cls_b, "B_resolution": res_b[:110]}), True)

    # ---------------- claims materiality (H4) ----------------
    bound = []
    for i, c in enumerate(M.get("claims") or []):
        ids = set()
        if isinstance(c.get("class_id"), str):
            ids.add(c["class_id"])
        for x in (c.get("class_ids") or []):
            ids.add(str(x))
        if SCALAR in ids:
            bound.append((i, c))
    theorem_level = [(i, c.get("conclusion_type")) for i, c in bound
                     if str(c.get("conclusion_type")) in ("theorem", "conditional_theorem")]
    asserting = [(i, c.get("conclusion_type")) for i, c in bound
                 if re.search(r"no visible singularity|visible from I\+|weak cosmic censorship (holds|is proved)|MGHD admits I\+",
                              str(c.get("statement") or ""), re.I)]
    add("R4c", "no live claim bound to the scalar class asserts the class WCC conclusion (H4 deferral honoured)",
        "0 asserting / 0 theorem-level",
        f"bound={len(bound)} asserting={len(asserting)} theorem_level={len(theorem_level)}",
        len(asserting) == 0 and len(theorem_level) == 0)

    # ---------------- FROZEN pins ----------------
    la = ((F.get("logical_artifacts") or {}).get("F0-declared-taxonomy") or {}).get("sha256")
    lb = ((F.get("logical_artifacts") or {}).get("F0-class-contract-supplement") or {}).get("sha256")
    add("R5c", "FROZEN rev28 pins both F0 logical artifacts at the measured hashes",
        f"rev=28 {PIN['A'][:12]}/{PIN['B'][:12]}",
        f"rev={F.get('revision')} A={str(la)[:12]} B={str(lb)[:12]}",
        F.get("revision") == 28 and la == PIN["A"] and lb == PIN["B"])

    return out


def sandbox_consistency(root: Path, snap: Path, workdir: Path):
    """Run the canonical consistency tool in a throwaway tree; never touch canonical evidence."""
    sb = workdir / "sandbox_consistency"
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "research_map").mkdir(parents=True, exist_ok=True)
    (sb / "artifacts/formulation/tools").mkdir(parents=True, exist_ok=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    shutil.copy(snap / "formulation_taxonomy.canonical.0abb9ed8a961.yaml", sb / "research_map/formulation_taxonomy.yaml")
    shutil.copy(snap / "formulation_taxonomy.supplement.d7419b4e8963.yaml", sb / "artifacts/formulation/formulation_taxonomy.yaml")
    shutil.copy(snap / "VOCAB_ALIASES.46cd9f1eb534.json", sb / "artifacts/formulation/VOCAB_ALIASES.json")
    tool_src = root / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    shutil.copy(tool_src, sb / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    p = subprocess.run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                       cwd=sb, capture_output=True, text=True, timeout=120)
    ev = {}
    evp = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"
    if evp.exists():
        ev = json.loads(evp.read_text())
    return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip(),
            "report": ev, "tree": str(sb.relative_to(workdir))}


# ------------------------- deterministic mutants -------------------------
def _mut_kind(new):
    def f(A, B, R1, R2, F, M):
        A["classes"][SCALAR]["axes"]["genericity_kind"] = new
    return f


def _mut_topology(A, B, R1, R2, F, M):
    A["classes"][SCALAR]["axes"]["genericity_topology"] = "unresolved"


def _mut_d3_three(A, B, R1, R2, F, M):
    for d in A["class_scope_adjudication"]["resolved_divergences"]:
        if d.get("id") == "D3":
            d["resolution"] = ("the comeager quantifier is now stated explicitly in each of the three "
                               "vacuum class conclusion texts and bound before the data")


def _mut_d3_no_scalar(A, B, R1, R2, F, M):
    for d in A["class_scope_adjudication"]["resolved_divergences"]:
        if d.get("id") == "D3":
            d["resolution"] = d["resolution"].replace("for ALL FOUR classes, including AF-WCC-SCALAR-SPH,", "for the three vacuum classes,")


def _mut_set_predicate(A, B, R1, R2, F, M):
    A["classes"][SCALAR]["conclusion"]["text"] = (
        "For a comeager set G of data in the class, every future-inextendible causal geodesic "
        "contained in J-(I+) is complete.")


def _mut_note_rev(A, B, R1, R2, F, M):
    ax = B["axis_registry"]["genericity_axis"]
    ax["scalar_note"] = (ax["scalar_note"]
                         .replace("worker-01 rev3", "worker-01 rev5")
                         .replace("records genericity as provisional", "records genericity as unresolved"))


def _mut_note_owner(A, B, R1, R2, F, M):
    ax = B["axis_registry"]["genericity_axis"]
    ax["scalar_note"] = ax["scalar_note"].replace("owned by that future node", "owned by L0/L1")
    B["class_contracts"][SCALAR]["node_id"] = "F3 (future scalar node)"


def _mut_frozen(A, B, R1, R2, F, M):
    F["logical_artifacts"]["F0-declared-taxonomy"]["sha256"] = "0" * 64


def _mut_drop_scalar(A, B, R1, R2, F, M):
    A["class_ids"] = [c for c in A["class_ids"] if c != SCALAR]
    del A["classes"][SCALAR]


MUTANTS = [
    ("M01-kind-residual-comeager", _mut_kind("residual_comeager"), "G3", True),
    ("M02-topology-installed", _mut_topology, "G4", True),
    ("M03-kind-worker001-alias", _mut_kind("provisional_baire_residual"), "G3", True),
    ("M04-D3-canonical-scoped-three", _mut_d3_three, "R2c", True),
    ("M05-D3-scalar-mention-removed", _mut_d3_no_scalar, "R2c", True),
    ("M06-assertive-set-predicate", _mut_set_predicate, "X6", False),
    ("M07-note-citation-refreshed", _mut_note_rev, "G8", True),
    ("M08-note-owner-L0L1", _mut_note_owner, "G9", True),
    ("M09-frozen-pin-corrupted", _mut_frozen, "R5c", False),
    ("M10-scalar-class-dropped", _mut_drop_scalar, "S3", False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data3/guoshaoyang/workdir/ai4math-swarm")
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    snap = Path(args.snapshot) if args.snapshot else root / "artifacts/worker-059/scalar_sph_axis_adjudication/snapshot"

    paths = {
        "A": snap / "formulation_taxonomy.canonical.0abb9ed8a961.yaml",
        "B": snap / "formulation_taxonomy.supplement.d7419b4e8963.yaml",
        "R1": snap / "VOCAB_ALIASES.46cd9f1eb534.json",
        "R2": snap / "rule_spec.40f9bb9e657b.json",
        "F": snap / "FROZEN.2f358f6722d9.json",
        "M": snap / "research_map.at00T0053.json",
    }
    measured = {k: sha(p) for k, p in paths.items()}
    A = syaml(paths["A"]); B = syaml(paths["B"])
    R1 = json.loads(paths["R1"].read_text()); R2 = json.loads(paths["R2"].read_text())
    F = json.loads(paths["F"].read_text()); M = json.loads(paths["M"].read_text())

    checks = run_checks(A, B, R1, R2, F, M)

    art_dir = root / "artifacts/worker-059/scalar_sph_axis_adjudication"
    cons = sandbox_consistency(root, snap, art_dir)
    (art_dir / "corroboration").mkdir(exist_ok=True)
    (art_dir / "corroboration/check_taxonomy_consistency_stdout.txt").write_text(
        f"exit_code={cons['exit_code']}\n{cons['stdout']}\n{cons['stderr']}\n")
    (art_dir / "corroboration/sandbox_taxonomy_consistency.json").write_text(
        json.dumps(cons["report"], indent=1) + "\n")
    # certification blindness: canonical tool green while R2c contradiction holds
    r2c = next(c for c in checks if c["id"] == "R2c")
    cons_green = cons["exit_code"] == 0 and "CONSISTENT" in cons["stdout"]
    checks.append({
        "id": "R3c",
        "desc": "the canonical consistency certificate is green while the D3 record contradiction is live (certification gap)",
        "expected": "not (green and contradiction)",
        "measured": f"tool_exit={cons['exit_code']} stdout={cons['stdout']!r} contradiction={not r2c['pass']}",
        "pass": not (cons_green and not r2c["pass"]),
    })

    mutants = []
    for name, mut, target, expect_after in MUTANTS:
        A2, B2, R12, R22, F2, M2 = (copy.deepcopy(x) for x in (A, B, R1, R2, F, M))
        mut(A2, B2, R12, R22, F2, M2)
        try:
            got = run_checks(A2, B2, R12, R22, F2, M2)
            tgt = next(c for c in got if c["id"] == target)
            base = next(c for c in checks if c["id"] == target)
            mutants.append({"mutant": name, "target": target,
                            "baseline_pass": base["pass"], "mutated_pass": tgt["pass"],
                            "mutated_measured": tgt["measured"],
                            "detected": (base["pass"] != tgt["pass"]) and (tgt["pass"] == expect_after)})
        except Exception as e:  # a crash on a mutant is itself detection
            mutants.append({"mutant": name, "target": target, "detected": True,
                            "mutated_measured": f"exception:{type(e).__name__}:{e}"})

    failures = [c for c in checks if not c["pass"]]
    report = {
        "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
        "class_id": SCALAR,
        "node_id": "F0",
        "gate": "G-F0/G-FORM",
        "measured_sha256": measured,
        "expected_pins": PIN,
        "pins_match": {k: measured[k] == PIN[k] for k in PIN},
        "checks_total": len(checks),
        "checks_pass": len(checks) - len(failures),
        "failures": [c["id"] for c in failures],
        "checks": checks,
        "canonical_tool_sandbox": cons,
        "mutants_total": len(mutants),
        "mutants_detected": sum(1 for m in mutants if m["detected"]),
        "mutants": mutants,
    }
    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0 if report["mutants_detected"] == report["mutants_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
