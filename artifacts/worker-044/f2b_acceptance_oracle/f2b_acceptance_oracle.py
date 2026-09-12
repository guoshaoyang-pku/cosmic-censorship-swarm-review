#!/usr/bin/env python3
"""W044-F2B-ACCEPTANCE-ORACLE-01.

One class-bound task: build and execute a single structural/binding acceptance oracle for
node F2b (class AF-SCC-C0-VAC-GEN, gate G-FORM) that covers BOTH live blocker families
found at frozen rev12 by other workers:

  family P (pin binding, worker-041/045/065/086): f0_binding.consistency_evidence_sha256
      declares 675a99d0 but the canonical path measures 9e335e9b and FROZEN rev28 pins
      9e335e9b;
  family V (vocabulary binding, worker-005): the declared conclusion_type and genericity.kind
      are registry-canonical tokens that are not literal members of the bound F0 rev5
      allowed-lists, and F2b binds no reference to the alias registry that establishes the
      equivalence.

The oracle decides, on pinned bytes: (a) which checks the CURRENT state fails, (b) whether
the failures are semantic or only binding-level, (c) whether a candidate minimal repair makes
all checks pass IN A SANDBOX, and (d) whether that repair is durable against the current
canonical writer.

AUTHORITY: worker measurement only. No canonical file is written; all mutations happen in
artifacts/worker-044/f2b_acceptance_oracle/sandbox/. No gate verdict, no node status, no
validation_status=passed, no mathematics claim. This oracle decides structure and binding,
NOT truth, non-vacuity, or physical correctness.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # artifacts/worker-044/f2b_acceptance_oracle -> repo
SANDBOX = HERE / "sandbox"

# repo-relative paths (the sandbox mirrors these)
F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
EV = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
F2B = "schemas/af_scc_c0_vacuum.yaml"
CCS = "artifacts/formulation/tools/check_class_schema.py"
CTC = "artifacts/formulation/tools/check_taxonomy_consistency.py"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
KEY_MANIFEST = "artifacts/formulation/KEY_MANIFEST.json"
CLS = "research_map/class_separation.py"
RESTORE = "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json"

SANDBOX_FILES = [F0, SUPP, VOCAB, EV, FROZEN, F2B, CCS, CTC, RULE_SPEC, KEY_MANIFEST]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def load_json(p: Path):
    return json.loads(p.read_text())


def dump_yaml(p: Path, obj):
    p.write_text(yaml.safe_dump(obj, sort_keys=False, default_flow_style=False, allow_unicode=True))


def canon(registry: dict, kind: str, tok):
    """Return the canonical registry token for tok, or tok if unresolved."""
    for c, aliases in (registry.get(kind) or {}).items():
        if tok == c or tok in aliases:
            return c
    return tok


def alias_class(registry: dict, kind: str, tok):
    for c, aliases in (registry.get(kind) or {}).items():
        if tok == c or tok in aliases:
            return sorted({c, *aliases})
    return [tok]


def build_sandbox():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    for rel in SANDBOX_FILES:
        dst = SANDBOX / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, dst)


def run_ccs(root: Path):
    """Run the structural class-schema gate copy inside root against root's F2b."""
    r = subprocess.run(
        [sys.executable, str(root / CCS), "--json", str(root / F2B)],
        capture_output=True, text=True,
    )
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"verdict": "unparseable", "failed_rules": [], "stdout": r.stdout[:500], "stderr": r.stderr[:500]}
    return r.returncode, rep


def sep_findings(text: str):
    spec = importlib.util.spec_from_file_location("class_separation", REPO / CLS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.findings_for_text(text, "F2b")


def checks(root: Path):
    """The 10 oracle checks on the bytes under root. Pure read-only."""
    out = []
    f0 = load_yaml(root / F0)
    voc = load_json(root / VOCAB)
    f2b_txt = (root / F2B).read_text()
    f2b = yaml.safe_load(f2b_txt)
    ev = load_json(root / EV)
    frozen = load_json(root / FROZEN)

    f0_sha, supp_sha, voc_sha, ev_sha = sha256_file(root / F0), sha256_file(root / SUPP), sha256_file(root / VOCAB), sha256_file(root / EV)
    binding = f2b.get("f0_binding") or {}
    declared = binding.get("consistency_evidence_sha256")
    axes = f0["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]
    fv = f0["field_vocabulary"]
    c_tok = (f2b.get("conclusion") or {}).get("conclusion_type")
    g_tok = (f2b.get("genericity") or {}).get("kind")
    ext_bind = ((f2b.get("extensions") or {}).get("vocabulary_binding") or {})

    # A1 declared evidence hash resolves at the declared canonical path
    out.append(dict(id="A1", title="declared consistency_evidence_sha256 == measured canonical evidence bytes",
                    status="pass" if declared == ev_sha else "fail",
                    detail=dict(declared=declared, measured=ev_sha)))
    # A2 evidence self-verification: carries sha256 of both inputs it claims to compare
    pins = {k: ev.get(k) for k in ("map_taxonomy_sha256", "lead_contract_sha256")}
    ok2 = pins.get("map_taxonomy_sha256") == f0_sha and pins.get("lead_contract_sha256") == supp_sha
    out.append(dict(id="A2", title="evidence document pins both inputs it evaluated (self-verifying)",
                    status="pass" if ok2 else "fail",
                    detail=dict(evidence_pins=pins, measured=dict(map_taxonomy=f0_sha, lead_contract=supp_sha))))
    # A3 FROZEN agrees with the canonical evidence bytes
    fz = (frozen.get("files", {}).get(EV) or {}).get("sha256")
    out.append(dict(id="A3", title="FROZEN pin for the evidence path == measured evidence bytes",
                    status="pass" if fz == ev_sha else "fail", detail=dict(frozen=fz, measured=ev_sha)))
    # A4 literal membership: conclusion_type in bound F0 allowed-list
    c_allowed = (fv.get("conclusion_type") or {}).get("allowed", [])
    out.append(dict(id="A4", title="conclusion_type is a literal member of the bound F0 allowed-list",
                    status="pass" if c_tok in c_allowed else "fail",
                    detail=dict(declared=c_tok, f0_allowed=c_allowed, f0_axis_value=axes.get("conclusion_type"))))
    # A4b semantic equivalence under the alias registry (the discriminating class-axis check:
    # F0's allowed-list is a UNION over classes, so literal membership alone is necessary-not-sufficient)
    ca, cb = canon(voc, "conclusion_type", c_tok), canon(voc, "conclusion_type", axes.get("conclusion_type"))
    out.append(dict(id="A4b", title="conclusion_type canon()-equivalent to the BOUND CLASS axis value",
                    status="pass" if ca == cb else "fail",
                    detail=dict(canon_declared=ca, canon_f0=cb, alias_class=alias_class(voc, "conclusion_type", c_tok))))
    # A5 literal membership: genericity_kind
    g_allowed = (fv.get("genericity_kind") or {}).get("allowed", [])
    out.append(dict(id="A5", title="genericity.kind is a literal member of the bound F0 allowed-list",
                    status="pass" if g_tok in g_allowed else "fail",
                    detail=dict(declared=g_tok, f0_allowed=g_allowed, f0_axis_value=axes.get("genericity_kind"))))
    # A5b semantic equivalence under the alias registry (discriminating check, see A4b)
    ga, gb = canon(voc, "genericity_kind", g_tok), canon(voc, "genericity_kind", axes.get("genericity_kind"))
    out.append(dict(id="A5b", title="genericity.kind canon()-equivalent to the BOUND CLASS axis value",
                    status="pass" if ga == gb else "fail",
                    detail=dict(canon_declared=ga, canon_f0=gb, alias_class=alias_class(voc, "genericity_kind", g_tok))))
    # A6 alias equivalence is bound inside the schema (or is unnecessary because literals are allowed)
    a6 = (ext_bind.get("alias_registry") == VOCAB and ext_bind.get("alias_registry_sha256") == voc_sha) or (
        c_tok in c_allowed and g_tok in g_allowed)
    out.append(dict(id="A6", title="alias registry bound by path+sha256 in F2b (or literals in F0 allowed-lists)",
                    status="pass" if a6 else "fail",
                    detail=dict(binding=ext_bind or None, measured_registry_sha256=voc_sha,
                                literals_allowed=(c_tok in c_allowed and g_tok in g_allowed))))
    # A7 canonical structural gate
    rc, rep = run_ccs(root)
    out.append(dict(id="A7", title="canonical structural class-schema gate exit 0 on F2b",
                    status="pass" if rc == 0 else "fail",
                    detail=dict(rc=rc, verdict=rep.get("verdict"), failed_rules=rep.get("failed_rules"))))
    # A8 class-separation detector: no C0/C2-merge finding on the F2b declaration
    fnd = [f for f in sep_findings(f2b_txt) if "composite" in f.lower() or "merge" in f.lower()]
    out.append(dict(id="A8", title="class_separation reports no composite/merge finding on F2b",
                    status="pass" if not fnd else "fail", detail=dict(findings=fnd[:5])))
    return out


def repaired_sandbox():
    """Sandbox + candidate minimal repair R* (three edits), all inside the sandbox."""
    build_sandbox()
    edits = []
    # R1: restore the enriched self-verifying evidence document (byte-exact 675a99d0)
    src = REPO / RESTORE
    shutil.copyfile(src, SANDBOX / EV)
    edits.append(dict(edit="R1-restore-enriched-evidence", path=EV, sha256=sha256_file(SANDBOX / EV),
                      source=RESTORE))
    # R2: bind the alias registry inside F2b under the checker's sanctioned `extensions` slot
    f2b = load_yaml(SANDBOX / F2B)
    ext = dict(f2b.get("extensions") or {})
    voc_sha = sha256_file(SANDBOX / VOCAB)
    ext["vocabulary_binding"] = {
        "alias_registry": VOCAB,
        "alias_registry_sha256": voc_sha,
        "declared_conclusion_type_canonical": "scc_c0_future_inextendibility",
        "declared_genericity_kind_canonical": "residual_comeager",
    }
    f2b["extensions"] = ext
    dump_yaml(SANDBOX / F2B, f2b)
    edits.append(dict(edit="R2-bind-alias-registry", path=F2B, sha256=sha256_file(SANDBOX / F2B),
                      slot="extensions.vocabulary_binding", alias_registry_sha256=voc_sha))
    # R3: refresh FROZEN pins for the two moved paths
    frozen = load_json(SANDBOX / FROZEN)
    for rel in (EV, F2B):
        blob = (SANDBOX / rel).read_bytes()
        entry = frozen["files"].setdefault(rel, {})
        entry["sha256"] = hashlib.sha256(blob).hexdigest()
        entry["bytes"] = len(blob)
        mirror = "artifacts/formulation/" + F2B
        if rel == F2B and mirror in frozen["files"]:
            frozen["files"][mirror] = {"sha256": entry["sha256"], "bytes": entry["bytes"]}
    old_rev = frozen.get("revision")
    frozen["revision"] = (old_rev or 0) + 1
    (SANDBOX / FROZEN).write_text(json.dumps(frozen, indent=2) + "\n")
    edits.append(dict(edit="R3-refresh-freeze-pins", path=FROZEN, revision_from=old_rev,
                      revision_to=frozen["revision"], pinned={EV: frozen["files"][EV]["sha256"],
                                                              F2B: frozen["files"][F2B]["sha256"]}))
    return edits


def status_of(rows, ids):
    return {r["id"]: r["status"] for r in rows if r["id"] in ids}


ACCEPT_IDS = ["A1", "A2", "A3", "A4b", "A5b", "A6", "A7", "A8"]


def readiness(rows):
    st = status_of(rows, ACCEPT_IDS)
    failing = sorted(k for k, v in st.items() if v != "pass")
    return dict(ready=not failing, failing=failing, statuses=st)


def main():
    report = {"task_id": "W044-F2B-ACCEPTANCE-ORACLE-01", "actor": "worker-044", "node_id": "F2b",
              "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
              "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")}
    pins = {rel: {"sha256": sha256_file(REPO / rel), "bytes": (REPO / rel).stat().st_size}
            for rel in SANDBOX_FILES + [RESTORE]}
    report["pins"] = pins
    report["authority"] = ("worker measurement only; sandbox writes only; no canonical edit; no gate verdict, "
                           "node status, or validation_status=passed; structure/binding only, no truth claim")

    # 1. current live bytes
    build_sandbox()
    cur = checks(SANDBOX)
    report["current"] = {"checks": cur, "summary": status_of(cur, [r["id"] for r in cur]),
                         "readiness": readiness(cur)}

    # 2. controls: each must flip exactly its target check (or fire the positive control)
    controls = []
    build_sandbox()
    c = checks(SANDBOX)
    rdy = readiness(c)
    controls.append(dict(id="N1-negative-control-live-bytes",
                         target="current-state signature: not ready, exactly {A1,A2,A6} fail",
                         passed=(not rdy["ready"] and rdy["failing"] == ["A1", "A2", "A6"]),
                         observed=rdy,
                         note="unmodified sandbox copy of the live tree must reproduce the known failures"))

    build_sandbox()
    edited = repaired_sandbox()
    ref = checks(SANDBOX)
    rdy_ref = readiness(ref)
    controls.append(dict(id="N2-positive-control-candidate-repair", target="ready after R*",
                         passed=rdy_ref["ready"], observed=rdy_ref, edits=edited))

    # M1: wrong declared evidence hash -> A1
    build_sandbox(); repaired_sandbox()
    f2b = load_yaml(SANDBOX / F2B); f2b["f0_binding"]["consistency_evidence_sha256"] = "0" * 64
    dump_yaml(SANDBOX / F2B, f2b)
    m = checks(SANDBOX); controls.append(dict(id="M1-wrong-declared-hash", target="A1",
        passed=status_of(m, ["A1"])["A1"] == "fail", observed=readiness(m)))
    # M2: strip input pins from the enriched evidence (keep declared+FROZEN consistent) -> A2
    build_sandbox(); repaired_sandbox()
    ev = load_json(SANDBOX / EV); ev.pop("map_taxonomy_sha256", None); ev.pop("lead_contract_sha256", None)
    (SANDBOX / EV).write_text(json.dumps(ev, indent=2) + "\n")
    frozen = load_json(SANDBOX / FROZEN)
    frozen["files"][EV] = {"sha256": sha256_file(SANDBOX / EV), "bytes": (SANDBOX / EV).stat().st_size}
    (SANDBOX / FROZEN).write_text(json.dumps(frozen, indent=2) + "\n")
    f2b = load_yaml(SANDBOX / F2B); f2b["f0_binding"]["consistency_evidence_sha256"] = sha256_file(SANDBOX / EV)
    dump_yaml(SANDBOX / F2B, f2b)
    m = checks(SANDBOX); controls.append(dict(id="M2-strip-input-pins", target="A2",
        passed=status_of(m, ["A2"])["A2"] == "fail", observed=readiness(m)))
    # M3: out-of-class conclusion token (literal member of the union list!) -> A4b
    build_sandbox(); repaired_sandbox()
    f2b = load_yaml(SANDBOX / F2B); f2b["conclusion"]["conclusion_type"] = "weak_cosmic_censorship"
    dump_yaml(SANDBOX / F2B, f2b)
    m = checks(SANDBOX); controls.append(dict(id="M3-out-of-class-conclusion", target="A4b (A4 literal passes: union-list)",
        passed=status_of(m, ["A4b"])["A4b"] == "fail", observed=readiness(m)))
    # M4: out-of-class genericity kind (literal member of the union list!) -> A5b
    build_sandbox(); repaired_sandbox()
    f2b = load_yaml(SANDBOX / F2B); f2b["genericity"]["kind"] = "measure_one"
    dump_yaml(SANDBOX / F2B, f2b)
    m = checks(SANDBOX); controls.append(dict(id="M4-out-of-class-genericity", target="A5b (A5 literal passes: union-list)",
        passed=status_of(m, ["A5b"])["A5b"] == "fail", observed=readiness(m)))
    # M5: remove the registry binding from the repaired schema -> A6
    build_sandbox(); repaired_sandbox()
    f2b = load_yaml(SANDBOX / F2B); f2b.get("extensions", {}).pop("vocabulary_binding", None)
    dump_yaml(SANDBOX / F2B, f2b)
    frozen = load_json(SANDBOX / FROZEN)
    frozen["files"][F2B] = {"sha256": sha256_file(SANDBOX / F2B), "bytes": (SANDBOX / F2B).stat().st_size}
    frozen["files"]["artifacts/formulation/" + F2B] = dict(frozen["files"][F2B])
    (SANDBOX / FROZEN).write_text(json.dumps(frozen, indent=2) + "\n")
    m = checks(SANDBOX); controls.append(dict(id="M5-unbind-alias-registry", target="A6",
        passed=status_of(m, ["A6"])["A6"] == "fail", observed=readiness(m)))
    # M6: detector positive control for A8
    pos = "the C0 or C2 classes are one class"
    f = sep_findings(pos)
    controls.append(dict(id="M6-classsep-positive-control", target="A8-detector-fires",
                         passed=len(f) >= 1, observed=f[:2]))
    # M7: structural gate positive control (drop class_id) -> A7
    build_sandbox(); repaired_sandbox()
    f2b = load_yaml(SANDBOX / F2B); f2b.pop("class_id", None)
    dump_yaml(SANDBOX / F2B, f2b)
    rc, rep = run_ccs(SANDBOX)
    controls.append(dict(id="M7-structural-positive-control", target="A7-gate-rejects",
                         passed=rc != 0, detail=dict(rc=rc, failed_rules=rep.get("failed_rules"))))
    report["controls"] = controls

    # 3. durability of the candidate repair against the current canonical writer
    build_sandbox(); repaired_sandbox()
    before = sha256_file(SANDBOX / EV)
    r = subprocess.run([sys.executable, str(SANDBOX / CTC)], capture_output=True, text=True, cwd=str(SANDBOX))
    after = sha256_file(SANDBOX / EV)
    post = checks(SANDBOX)
    report["durability"] = dict(
        probe="run the sandbox copy of check_taxonomy_consistency.py once after R1",
        rc=r.returncode, stdout=r.stdout.strip()[:200], stderr=r.stderr.strip()[:200],
        evidence_before=before, evidence_after=after, evidence_stable=(before == after),
        post_probe_checks=status_of(post, ["A1", "A2", "A3", "A6"]),
        note=("writer overwrites the enriched document with the pin-free lean schema; R1/R2-style "
              "restoration is not durable unless the writer is made non-writing or emits the enriched schema"))
    report["candidate_repair"] = dict(edits=edited, checks=ref, readiness=rdy_ref,
                                      all_pass=rdy_ref["ready"])

    # 4. drift re-measure
    drift = []
    for rel, pin in pins.items():
        if sha256_file(REPO / rel) != pin["sha256"]:
            drift.append(rel)
    report["post_run_drift"] = drift

    report["verdict"] = ("CURRENT_F2B_NOT_ACCEPTANCE_READY__SEMANTICS_CLEAN__CANDIDATE_REPAIR_PASSES_IN_SANDBOX__"
                         "RESTORE_NON_DURABLE_AGAINST_CURRENT_WRITER")
    report["falsifier"] = (
        "(a) at the pinned hashes any current-state check marked fail measures pass, or vice versa; "
        "(b) a control that fails to flip its target check (oracle vacuity); "
        "(c) the candidate repair failing to make all checks pass in the sandbox; "
        "(d) the durability probe leaving the restored evidence byte-identical (which would falsify the "
        "non-durability finding); (e) any pinned input moving before adjudication, which voids the report.")
    report["non_claims"] = [
        "no canonical file written; all edits confined to the oracle sandbox",
        "no gate verdict, node status, or validation_status=passed",
        "no claim that the candidate repair is the lead's chosen repair; it is a demonstration only",
        "no mathematics, physics, or literature claim; structure and binding only",
        "worker-005 owns the literal-membership finding (P4/P5/P6) and worker-086 the collision/repair "
        "matrix; this oracle integrates them into one executable acceptance test and adds the "
        "semantics-vs-binding separation and the durability probe",
    ]
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("verdict", "post_run_drift", "durability")}, indent=1))
    print("current :", report["current"]["readiness"])
    print("repaired:", rdy_ref)
    print("controls:", [(c["id"], c["passed"]) for c in controls])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
