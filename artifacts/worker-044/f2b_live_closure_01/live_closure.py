#!/usr/bin/env python3
"""W044-F2B-REV13-INTEGRATION-01 (rebound).

One bounded class-bound task on the live G-FORM critical path: take a hash-pinned snapshot of the
F2b (class AF-SCC-C0-VAC-GEN) input set, compose the remaining repairs into ONE sandbox revision
candidate, and verify that the union is sufficient, mutually consistent, durable, and closes every
live machine pin it moves.

Why the task was rebound: at 00:53:20+08:00 a separate lifecycle ("astra-life05-evidence-binding-
repair") published rev13 of all three class schemas + gate_test_report.json with no FROZEN
refresh. Measured immediately after: schemas/af_scc_c0_vacuum.yaml b2ab6acb2bbe (rev13, evidence
declaration moved from the enriched 675a99d0 to the live lean 9e335e9b), C2 e9a27996dfd3, F1
d9cebb9404b2, FROZEN still rev28 -> verify_frozen reports 7 drift problems. The containment defects
are unchanged. This task therefore composes, on a frozen snapshot:

  P1 containment (worker-066 W066-F2B-REPAIR-PREREG-01 / worker-008):
     the two C0 text edits -- false containment denial in regularity.must_not_conflate[0] and the
     inverted size premise in implication_ledger.forbidden_transfers[0].reason (still live).
  P2 binding completion (worker-044 oracle / worker-086 / worker-005):
     restore the enriched self-verifying evidence document (675a99d0) at the declared canonical
     path and re-declare it (A1+A2), bind VOCAB_ALIASES.json by path+sha256 under the R22
     `extensions:` escape hatch (A6), and install worker-086's non-writing writer guard.
  P3 closure (new here):
     regenerate KEY_MANIFEST.json, regenerate FROZEN for every drifted path including the three
     schema mirrors and gate_test_report.json, and re-pin the F2 aggregator's stale component
     hashes (SEP-6) to the composed C0 and the snapshot C2 -- the integration step the partial
     repairs each leave out.

AUTHORITY: worker measurement only. No canonical file written; all mutation in
artifacts/worker-044/f2b_rev13_integration/sandbox/. No gate verdict, node status, or
validation_status=passed; structure/binding only, no truth or physics claim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = HERE / "pinned"
SANDBOX = HERE / "sandbox"

# canonical / authoring artifacts
C0, C0A = "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
C2, C2A = "schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F1, F1A = "schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
AGG = "schemas/af_scc_regularities.yaml"
F1TESTS = "schemas/f1_falsifier_tests.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"
KEYM = "artifacts/formulation/KEY_MANIFEST.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
EV = "artifacts/formulation/evidence/taxonomy_consistency.json"
F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
RULES = "artifacts/formulation/rule_spec.json"
VREG = "artifacts/formulation/VARIANT_REGISTRY.json"
DSUM = "artifacts/formulation/DELIVERABLE_SUMMARY.md"
FORM = "artifacts/formulation/FORMULATION.md"
CCS = "artifacts/formulation/tools/check_class_schema.py"
CTC = "artifacts/formulation/tools/check_taxonomy_consistency.py"
MKM = "artifacts/formulation/tools/make_key_manifest.py"
RGF = "artifacts/formulation/tools/regenerate_frozen.py"
VFZ = "artifacts/formulation/tools/verify_frozen.py"
CLS = "research_map/class_separation.py"
RESTORE = "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json"
GUARD = "artifacts/worker-086/evbind_repair_demo/check_taxonomy_consistency.guarded.py"
PATCH = "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff"

EXTRA_RELS = [C0, C0A, C2, C2A, F1, F1A, AGG, F1TESTS, FROZEN, KEYM, VOCAB, EV, F0, SUPP, RULES, VREG,
              DSUM, FORM, CCS, CTC, MKM, RGF, VFZ, CLS, RESTORE, GUARD, PATCH,
              "artifacts/formulation/reviews/BN_TRIAGE.md",
              "artifacts/formulation/evidence/bn_triage.json",
              "artifacts/formulation/evidence/variant_registry_check.json",
              "artifacts/formulation/evidence/variant_delta_check.json"]
MIRRORS = {C0: C0A, C2: C2A, F1: F1A}
SCHEMAS3 = [C0, C2, F1]
LIVE_BINDING_FILES = [C0, C0A, C2, C2A, F1, F1A, AGG, F1TESTS, FROZEN, KEYM, VOCAB, EV, F0, SUPP,
                      RULES, VREG, DSUM, FORM]

AGG_C0_OLD = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
AGG_C2_OLD = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
OBSOLETE_DECL = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def load_json(p: Path):
    return json.loads(p.read_text())


def replace_once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        raise AssertionError(f"{where}: expected exactly 1 occurrence, got {n}")
    return text.replace(old, new)


def parse_two_line_patch(patch_text: str):
    pairs, minus, plus = [], None, None
    for line in patch_text.splitlines():
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            minus = line[1:]
        elif line.startswith("+"):
            plus = line[1:]
        if minus is not None and plus is not None:
            pairs.append((minus, plus))
            minus = plus = None
    return pairs


# ----------------------------------------------------------------------------- snapshot + sandbox

def input_rels(root: Path):
    frozen = load_json(root / FROZEN)
    return sorted(set(frozen["files"]) | set(EXTRA_RELS))


def snapshot_inputs():
    if SNAP.exists():
        shutil.rmtree(SNAP)
    rels = input_rels(REPO)
    pins = {}
    for rel in rels:
        src, dst = REPO / rel, SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        pins[rel] = dict(sha256=sha256_file(dst), bytes=dst.stat().st_size)
    return rels, pins


def build_sandbox(rels):
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    for rel in rels:
        dst = SANDBOX / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SNAP / rel, dst)


# ----------------------------------------------------------------------------- P1 containment

def apply_containment(root: Path):
    pairs = parse_two_line_patch((SNAP / PATCH).read_text())
    if len(pairs) != 2:
        raise AssertionError(f"expected 2 patch line pairs, got {len(pairs)}")
    evidence = []
    for rel in (C0, C0A):
        text = (root / rel).read_text()
        for old, new in pairs:
            text = replace_once(text, old, new, f"{rel} containment edit")
        (root / rel).write_text(text)
        evidence.append(dict(path=rel, sha256=sha256_file(root / rel)))
    return dict(edits=["H2-must_not_conflate[0] containment assertion",
                       "H1-forbidden_transfers[0] size premise"],
                patch=PATCH, patch_sha256=sha256_file(SNAP / PATCH), applied_to=evidence)


# ----------------------------------------------------------------------------- P2 binding

def apply_binding(root: Path):
    edits = []
    shutil.copyfile(SNAP / RESTORE, root / EV)
    edits.append(dict(edit="R3a-restore-enriched-evidence", path=EV, sha256=sha256_file(root / EV),
                      source=RESTORE))
    # one atomic revision must leave all three class schemas declaring the same, self-verifying
    # evidence document; the 00:53 partial repair had moved all three declarations to the lean doc
    ev_sha = sha256_file(root / EV)
    for canon, auth in MIRRORS.items():
        for rel in (canon, auth):
            text = (root / rel).read_text()
            text = replace_once(text, OBSOLETE_DECL, ev_sha, f"{rel} re-declare evidence")
            text = replace_once(text, "revision: 13", "revision: 14", f"{rel} revision bump")
            (root / rel).write_text(text)
            edits.append(dict(edit="R3b-redeclare-enriched-evidence+R5-bump-revision", path=rel,
                              declared=ev_sha, revision=14))
    voc_sha = sha256_file(root / VOCAB)
    block = ("extensions:\n"
             "  vocabulary_binding:\n"
             f"    alias_registry: {VOCAB}\n"
             f'    alias_registry_sha256: "{voc_sha}"\n'
             "    declared_conclusion_type_canonical: scc_c0_future_inextendibility\n"
             "    declared_genericity_kind_canonical: residual_comeager\n")
    for rel in (C0, C0A):
        text = (root / rel).read_text()
        text = text.rstrip("\n") + "\n" + block
        (root / rel).write_text(text)
        edits.append(dict(edit="R4-bind-alias-registry", path=rel, sha256=sha256_file(root / rel),
                          slot="extensions.vocabulary_binding", alias_registry_sha256=voc_sha))
    shutil.copyfile(SNAP / GUARD, root / CTC)
    edits.append(dict(edit="R6-install-guarded-writer", path=CTC, sha256=sha256_file(root / CTC),
                      source=GUARD))
    return edits


# ----------------------------------------------------------------------------- P3 closure

def apply_closure(root: Path, delta: str, at: str):
    edits = []
    r = subprocess.run([sys.executable, str(root / MKM)], capture_output=True, text=True, cwd=str(root))
    if r.returncode != 0:
        raise RuntimeError(f"make_key_manifest failed: {r.stderr[:300]}")
    edits.append(dict(edit="R7-regenerate-key-manifest", path=KEYM, stdout=r.stdout.strip(),
                      sha256=sha256_file(root / KEYM)))
    r = subprocess.run([sys.executable, str(root / RGF), "--revision", "29", "--delta", delta,
                        "--at", at], capture_output=True, text=True, cwd=str(root))
    if r.returncode != 0:
        raise RuntimeError(f"regenerate_frozen failed: {r.stdout[-300:]} {r.stderr[-300:]}")
    edits.append(dict(edit="R8-regenerate-frozen", path=FROZEN, stdout=r.stdout.strip().splitlines()[0],
                      revision=load_json(root / FROZEN)["revision"]))
    text = (root / AGG).read_text()
    text = replace_once(text, AGG_C0_OLD, sha256_file(root / C0), "aggregator C0 component pin")
    text = replace_once(text, AGG_C2_OLD, sha256_file(root / C2), "aggregator C2 component pin")
    text = replace_once(text, "revision: 6", "revision: 7", "aggregator revision bump")
    (root / AGG).write_text(text)
    edits.append(dict(edit="R9-repin-aggregator-components", path=AGG, c0=sha256_file(root / C0),
                      c2=sha256_file(root / C2), sha256=sha256_file(root / AGG)))
    return edits


# ----------------------------------------------------------------------------- checkers

def containment_findings(text: str):
    findings = []
    m = re.search(r'extension_class_containment:\s*"([^"]*)"', text)
    ranks = {}
    if m:
        chain = m.group(1)
        order = re.findall(r"E_\{?([A-Za-z0-9^,]+)\}?", chain.split(";")[0])
        for i, tok in enumerate(order):
            ranks[tok.upper().replace("^", "").replace(",", "")] = len(order) - 1 - i
    c0_rank, c2_rank = ranks.get("C0"), ranks.get("C2")
    for row in re.finditer(r'\{from:\s*"([^"]*)",\s*to:\s*"([^"]*)",\s*reason:\s*"([^"]*)"\}', text):
        frm, to, reason = row.group(1), row.group(2), row.group(3)
        if "C2" in frm and to == "this class" and re.search(r"strictly larger", reason):
            if c0_rank is not None and c2_rank is not None and c2_rank < c0_rank:
                findings.append(dict(kind="size_premise_inverted", rank_c0=c0_rank, rank_c2=c2_rank,
                                     reason=reason))
    if m:
        for entry in re.findall(r'must_not_conflate:\s*\n((?:\s+- .*\n?)+)', text):
            for line in entry.splitlines():
                if re.search(r"No containment with C2 or C0 is asserted", line) and "was wrong" not in line:
                    findings.append(dict(kind="false_containment_denial",
                                         clause="a must_not_conflate entry denies a containment the same "
                                                "file declares"))
                    break
    return findings, ranks


def run_ccs(root: Path, rel: str):
    r = subprocess.run([sys.executable, str(root / CCS), "--json", str(root / rel)],
                       capture_output=True, text=True)
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"verdict": "unparseable", "stdout": r.stdout[:300], "stderr": r.stderr[:300]}
    return r.returncode, rep


def run_verify_frozen(root: Path):
    r = subprocess.run([sys.executable, str(root / VFZ)], capture_output=True, text=True, cwd=str(root))
    drift = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith("DRIFT")]
    missing = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith("MISSING")]
    return dict(rc=r.returncode, summary=r.stdout.strip().splitlines()[:1], drift=drift, missing=missing)


def sep_findings(text: str):
    spec = importlib.util.spec_from_file_location("class_separation", SNAP / CLS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.findings_for_text(text, "F2b")


def canon(registry: dict, kind: str, tok):
    for c, aliases in (registry.get(kind) or {}).items():
        if tok == c or tok in aliases:
            return c
    return tok


def alias_class(registry: dict, kind: str, tok):
    for c, aliases in (registry.get(kind) or {}).items():
        if tok == c or tok in aliases:
            return sorted({c, *aliases})
    return [tok]


ACCEPT_IDS = ["A1", "A2", "A3", "A4b", "A5b", "A6", "A7", "A8"]


def checks(root: Path):
    out = []
    f0 = load_yaml(root / F0)
    voc = load_json(root / VOCAB)
    c0_txt = (root / C0).read_text()
    f2b = yaml.safe_load(c0_txt)
    ev = load_json(root / EV)
    frozen = load_json(root / FROZEN)
    f0_sha, supp_sha, voc_sha, ev_sha = (sha256_file(root / F0), sha256_file(root / SUPP),
                                        sha256_file(root / VOCAB), sha256_file(root / EV))
    binding = f2b.get("f0_binding") or {}
    declared = binding.get("consistency_evidence_sha256")
    axes = f0["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]
    fv = f0["field_vocabulary"]
    c_tok = (f2b.get("conclusion") or {}).get("conclusion_type")
    g_tok = (f2b.get("genericity") or {}).get("kind")
    ext_bind = ((f2b.get("extensions") or {}).get("vocabulary_binding") or {})

    fnd, ranks = containment_findings(c0_txt)
    out.append(dict(id="H1H2", title="no containment defect (inverted size premise / false denial)",
                    status="pass" if not fnd else "fail", detail=dict(findings=fnd, ranks=ranks)))
    out.append(dict(id="A1", title="declared consistency_evidence_sha256 == measured canonical evidence bytes",
                    status="pass" if declared == ev_sha else "fail",
                    detail=dict(declared=declared, measured=ev_sha)))
    pins = {k: ev.get(k) for k in ("map_taxonomy_sha256", "lead_contract_sha256")}
    ok2 = pins.get("map_taxonomy_sha256") == f0_sha and pins.get("lead_contract_sha256") == supp_sha
    out.append(dict(id="A2", title="evidence document pins both inputs it evaluated (self-verifying)",
                    status="pass" if ok2 else "fail",
                    detail=dict(evidence_pins=pins, measured=dict(map_taxonomy=f0_sha, lead_contract=supp_sha))))
    fz = (frozen.get("files", {}).get(EV) or {}).get("sha256")
    out.append(dict(id="A3", title="FROZEN pin for the evidence path == measured evidence bytes",
                    status="pass" if fz == ev_sha else "fail", detail=dict(frozen=fz, measured=ev_sha)))
    c_allowed = (fv.get("conclusion_type") or {}).get("allowed", [])
    out.append(dict(id="A4", title="conclusion_type is a literal member of the bound F0 allowed-list",
                    status="pass" if c_tok in c_allowed else "fail",
                    detail=dict(declared=c_tok, f0_allowed=c_allowed, f0_axis_value=axes.get("conclusion_type"))))
    ca, cb = canon(voc, "conclusion_type", c_tok), canon(voc, "conclusion_type", axes.get("conclusion_type"))
    out.append(dict(id="A4b", title="conclusion_type canon()-equivalent to the BOUND CLASS axis value",
                    status="pass" if ca == cb else "fail",
                    detail=dict(canon_declared=ca, canon_f0=cb, alias_class=alias_class(voc, "conclusion_type", c_tok))))
    g_allowed = (fv.get("genericity_kind") or {}).get("allowed", [])
    out.append(dict(id="A5", title="genericity.kind is a literal member of the bound F0 allowed-list",
                    status="pass" if g_tok in g_allowed else "fail",
                    detail=dict(declared=g_tok, f0_allowed=g_allowed, f0_axis_value=axes.get("genericity_kind"))))
    ga, gb = canon(voc, "genericity_kind", g_tok), canon(voc, "genericity_kind", axes.get("genericity_kind"))
    out.append(dict(id="A5b", title="genericity.kind canon()-equivalent to the BOUND CLASS axis value",
                    status="pass" if ga == gb else "fail",
                    detail=dict(canon_declared=ga, canon_f0=gb, alias_class=alias_class(voc, "genericity_kind", g_tok))))
    a6 = (ext_bind.get("alias_registry") == VOCAB and ext_bind.get("alias_registry_sha256") == voc_sha) or (
        c_tok in c_allowed and g_tok in g_allowed)
    out.append(dict(id="A6", title="alias registry bound by path+sha256 in C0 (or literals in F0 allowed-lists)",
                    status="pass" if a6 else "fail",
                    detail=dict(binding=ext_bind or None, measured_registry_sha256=voc_sha,
                                literals_allowed=(c_tok in c_allowed and g_tok in g_allowed))))
    rc, rep = run_ccs(root, C0)
    out.append(dict(id="A7", title="canonical structural class-schema gate exit 0 on C0",
                    status="pass" if rc == 0 else "fail",
                    detail=dict(rc=rc, verdict=rep.get("verdict"), failed_rules=rep.get("failed_rules"))))
    fnd2 = [f for f in sep_findings(c0_txt) if "composite" in f.lower() or "merge" in f.lower()]
    out.append(dict(id="A8", title="class_separation reports no composite/merge finding on C0",
                    status="pass" if not fnd2 else "fail", detail=dict(findings=fnd2[:5])))
    return out


def status_of(rows, ids=None):
    return {r["id"]: r["status"] for r in rows if ids is None or r["id"] in ids}


def readiness(rows):
    st = status_of(rows, ACCEPT_IDS + ["H1H2"])
    failing = sorted(k for k, v in st.items() if v != "pass")
    return dict(ready=not failing, failing=failing, statuses=st)


def aggregator_sep6(root: Path):
    agg = load_yaml(root / AGG)
    comps = {c["class_id"]: dict(pinned=c.get("sha256"), measured=sha256_file(root / c["path"]),
                                 ok=c.get("sha256") == sha256_file(root / c["path"]))
             for c in agg.get("components", [])}
    return dict(ok=all(v["ok"] for v in comps.values()), components=comps)


def state_summary(root: Path):
    return dict(checks=checks(root), readiness=readiness(checks(root)),
                schema_gates={rel: run_ccs(root, rel)[0] for rel in SCHEMAS3},
                verify_frozen=run_verify_frozen(root), aggregator_sep6=aggregator_sep6(root),
                containment=containment_findings((root / C0).read_text())[0],
                mirrors={c: sha256_file(root / c) == sha256_file(root / a) for c, a in MIRRORS.items()})


def composed(root: Path, rels, at: str):
    res = {}
    res["containment"] = apply_containment(root)
    res["binding"] = apply_binding(root)
    res["closure"] = apply_closure(
        root, "rev14 F2b integration candidate: containment repair + evidence/vocabulary binding + "
              "durable writer + FROZEN/KEY_MANIFEST/aggregator pin closure (worker-044 "
              "W044-F2B-REV13-INTEGRATION-01 sandbox, snapshot-bound)", at)
    res["checks"] = checks(root)
    res["readiness"] = readiness(res["checks"])
    res["schema_gates"] = {}
    for rel in SCHEMAS3:
        rc, rep = run_ccs(root, rel)
        res["schema_gates"][rel] = dict(rc=rc, verdict=rep.get("verdict"),
                                        failed_rules=rep.get("failed_rules"))
    res["verify_frozen"] = run_verify_frozen(root)
    res["aggregator_sep6"] = aggregator_sep6(root)
    res["mirrors"] = {c: dict(canonical=sha256_file(root / c), authoring=sha256_file(root / a),
                              equal=sha256_file(root / c) == sha256_file(root / a))
                      for c, a in MIRRORS.items()}
    return res


def closure_scan(root: Path, moved_old: dict):
    """Structured machine-binding scan + separate raw-prose mention scan."""
    machine = []
    for rel in list(MIRRORS) + list(MIRRORS.values()):
        s = load_yaml(root / rel)
        decl = (s.get("f0_binding") or {}).get("consistency_evidence_sha256")
        for name, old in moved_old.items():
            if decl == old:
                machine.append(dict(file=rel, moved=name,
                                    field="f0_binding.consistency_evidence_sha256"))
    frozen = load_json(root / FROZEN)
    for p, rec in frozen.get("files", {}).items():
        for name, old in moved_old.items():
            if rec.get("sha256") == old:
                machine.append(dict(file=FROZEN, moved=name, field=f"files[{p}].sha256"))
    for c in load_yaml(root / AGG).get("components", []):
        for name, old in moved_old.items():
            if c.get("sha256") == old:
                machine.append(dict(file=AGG, moved=name,
                                    field=f"components[{c['class_id']}].sha256"))
    prose = []
    for rel in LIVE_BINDING_FILES:
        p = root / rel
        if not p.exists():
            continue
        text = p.read_text(errors="replace")
        for name, old in moved_old.items():
            if old[:12] in text:
                prose.append(dict(file=rel, moved=name, old_prefix=old[:12]))
    return machine, prose


def main():
    at = datetime.now().astimezone().isoformat(timespec="seconds")
    report = {"task_id": "W044-F2B-LIVE-CLOSURE-01", "actor": "worker-044", "node_id": "F2b",
              "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "created_at": at,
              "rebound": "live closure re-probe after astra-life05-evidence-binding-repair (REC-12) landed rev13/rev29; "
                         "snapshot and composed columns below are bound to the pinned/ snapshot taken at run time",
              "snapshot_at": at}
    rels, pins = snapshot_inputs()
    report["pins"] = pins
    report["authority"] = ("worker measurement only; sandbox writes only; no canonical edit; no gate verdict, "
                           "node status, or validation_status=passed; structure/binding only, no truth claim")

    # ---- snapshot state (what the owner would start from)
    build_sandbox(rels)
    cur = state_summary(SANDBOX)
    report["snapshot_state"] = cur
    report["snapshot_hashes"] = {rel: pins[rel]["sha256"] for rel in (C0, C0A, C2, C2A, F1, F1A, AGG,
                                                                      FROZEN, KEYM, VOCAB, EV)}

    # ---- composed candidate
    build_sandbox(rels)
    comp = composed(SANDBOX, rels, at)
    c0_new, ev_new = sha256_file(SANDBOX / C0), sha256_file(SANDBOX / EV)
    report["composed"] = comp
    report["composed_hashes"] = dict(c0=c0_new, c0_authoring=sha256_file(SANDBOX / C0A),
                                     evidence=ev_new, frozen=sha256_file(SANDBOX / FROZEN),
                                     key_manifest=sha256_file(SANDBOX / KEYM),
                                     aggregator=sha256_file(SANDBOX / AGG))

    # ---- one-edit-removed sensitivity controls (all rebuilt from the snapshot)
    pairs = parse_two_line_patch((SNAP / PATCH).read_text())
    controls = []

    def fresh():
        build_sandbox(rels)
        composed(SANDBOX, rels, at)

    def k1():
        fresh()
        for rel in (C0, C0A):
            t = (SANDBOX / rel).read_text()
            (SANDBOX / rel).write_text(replace_once(t, pairs[0][1], pairs[0][0], f"{rel} revert H2"))
        return status_of(checks(SANDBOX), ["H1H2"])

    def k2():
        fresh()
        for rel in (C0, C0A):
            t = (SANDBOX / rel).read_text()
            (SANDBOX / rel).write_text(replace_once(t, pairs[1][1], pairs[1][0], f"{rel} revert H1"))
        return status_of(checks(SANDBOX), ["H1H2"])

    def k3():
        fresh()
        for rel in (C0, C0A):
            t = (SANDBOX / rel).read_text()
            (SANDBOX / rel).write_text(replace_once(t, sha256_file(SANDBOX / EV), OBSOLETE_DECL,
                                                    f"{rel} stale declaration"))
        return status_of(checks(SANDBOX), ["A1", "A2"])

    def k4():
        fresh()
        for rel in (C0, C0A):
            t = (SANDBOX / rel).read_text().split("\nextensions:")[0].rstrip("\n") + "\n"
            (SANDBOX / rel).write_text(t)
        return status_of(checks(SANDBOX), ["A6"])

    def k5():
        build_sandbox(rels)
        apply_containment(SANDBOX)
        apply_binding(SANDBOX)
        return {"verify_frozen": run_verify_frozen(SANDBOX)["rc"]}

    def k6():
        fresh()
        t = (SANDBOX / AGG).read_text()
        (SANDBOX / AGG).write_text(replace_once(t, sha256_file(SANDBOX / C0), AGG_C0_OLD,
                                                "revert aggregator C0 pin"))
        return {"stale": [k for k, v in aggregator_sep6(SANDBOX)["components"].items() if not v["ok"]]}

    def k7():
        fresh()
        shutil.copyfile(SNAP / CTC, SANDBOX / CTC)
        before = sha256_file(SANDBOX / EV)
        subprocess.run([sys.executable, str(SANDBOX / CTC)], capture_output=True, text=True, cwd=str(SANDBOX))
        return {"evidence_before": before, "evidence_after": sha256_file(SANDBOX / EV)}

    k1o, k2o, k3o, k4o = k1(), k2(), k3(), k4()
    k5o, k6o, k7o = k5(), k6(), k7()
    controls.append(dict(id="K1-revert-containment-H2", target="false containment denial returns -> H1H2 fails",
                         passed=k1o["H1H2"] == "fail", observed=k1o))
    controls.append(dict(id="K2-revert-containment-H1", target="inverted size premise returns -> H1H2 fails",
                         passed=k2o["H1H2"] == "fail", observed=k2o))
    controls.append(dict(id="K3-stale-evidence-declaration", target="declared hash unresolved -> A1 fails",
                         passed=k3o["A1"] == "fail", observed=k3o))
    controls.append(dict(id="K4-unbind-alias-registry", target="no alias binding -> A6 fails",
                         passed=k4o["A6"] == "fail", observed=k4o))
    controls.append(dict(id="K5-skip-freeze-refresh", target="stale FROZEN -> verify_frozen nonzero",
                         passed=k5o["verify_frozen"] != 0, observed=k5o))
    controls.append(dict(id="K6-revert-aggregator-repin", target="stale component pin -> SEP-6 fails",
                         passed=bool(k6o["stale"]), observed=k6o))
    controls.append(dict(id="K7-unguarded-writer", target="writer moves the evidence -> non-durable",
                         passed=k7o["evidence_before"] != k7o["evidence_after"], observed=k7o))
    controls.append(dict(id="K8-classsep-positive-control",
                         target="class_separation detector fires on an explicit merge assertion",
                         passed=len(sep_findings("the C0 or C2 classes are one class")) >= 1,
                         observed=sep_findings("the C0 or C2 classes are one class")[:1]))
    report["controls"] = controls

    # ---- durability on the composed candidate (guarded writer, twice)
    fresh()
    ev0 = sha256_file(SANDBOX / EV)
    runs = []
    for _ in range(2):
        r = subprocess.run([sys.executable, str(SANDBOX / CTC)], capture_output=True, text=True, cwd=str(SANDBOX))
        runs.append(dict(rc=r.returncode, stdout=r.stdout.strip()[:200], evidence=sha256_file(SANDBOX / EV)))
    vf = run_verify_frozen(SANDBOX)
    report["durability"] = dict(runs=runs, evidence_before=ev0, evidence_after=sha256_file(SANDBOX / EV),
                                stable=(sha256_file(SANDBOX / EV) == ev0),
                                verify_frozen_rc=vf["rc"], verify_frozen_summary=vf["summary"])

    # ---- closure scan + live drift
    moved_old = {"C0": pins[C0]["sha256"], "C0-authoring": pins[C0A]["sha256"],
                 "evidence": pins[EV]["sha256"]}
    machine_stale, prose_mentions = closure_scan(SANDBOX, moved_old)
    report["closure"] = dict(moved_old={k: v[:16] for k, v in moved_old.items()},
                             machine_binding_stale=machine_stale, prose_mentions=prose_mentions,
                             live_binding_files=LIVE_BINDING_FILES,
                             policy="reviews/, comms/, runtime/ and artifacts/worker-*/ pins are historical "
                                    "records and are invalidated by drift, never rewritten; prose mentions in "
                                    "binding_note/revision_history are history, not bindings")
    live = {rel: sha256_file(REPO / rel) for rel in rels if (REPO / rel).exists()}
    report["live_drift_since_snapshot"] = sorted(rel for rel, h in live.items() if h != pins[rel]["sha256"])
    report["live_missing"] = sorted(rel for rel in rels if not (REPO / rel).exists())

    ok = (report["composed"]["readiness"]["ready"]
          and report["composed"]["aggregator_sep6"]["ok"]
          and report["composed"]["verify_frozen"]["rc"] == 0
          and all(v["rc"] == 0 for v in report["composed"]["schema_gates"].values())
          and not machine_stale
          and report["durability"]["stable"] and report["durability"]["verify_frozen_rc"] == 0
          and all(c["passed"] for c in controls))
    report["verdict"] = ("COMPOSED_F2B_CANDIDATE_ACCEPTANCE_READY_ON_LIVE_BASE"
                         if ok else "COMPOSED_F2B_CANDIDATE_HAS_RESIDUAL_FAILURES_ON_LIVE_BASE")
    report["ready"] = bool(ok)
    report["falsifier"] = (
        "(a) any snapshot-state or composed-state check reported pass measures fail (or vice versa) on the "
        "pinned bytes; (b) any of K1-K8 failing to flip its target check (harness vacuity); (c) the "
        "containment repair pair not matching worker-066's proposed_patch.diff; (d) verify_frozen or any of "
        "the three structural gates nonzero after regeneration; (e) the aggregator SEP-6 check leaving a "
        "stale component pin; (f) either guarded-writer run moving the evidence hash or breaking "
        "verify_frozen; (g) any live machine-binding file still referencing an old moved hash; (h) the "
        "snapshot hashes not reproducing pinned/ bytes; (i) any pinned input drifting after the snapshot, "
        "which voids the live applicability (not the snapshot measurement).")
    report["non_claims"] = [
        "no canonical file written; all edits confined to the integration sandbox",
        "no gate verdict, node status, or validation_status=passed",
        "the candidate is a demonstration, not the lead's chosen repair; the owner must publish it and "
        "choose the real next revision numbers",
        "the verdict is bound to the snapshot hashes; live drift after the snapshot is reported separately "
        "and voids live applicability",
        "structure/binding only: no mathematics, physics, or literature claim",
        "credit: containment patch worker-066 (from worker-008), evidence restore/collision worker-086, "
        "alias-registry finding worker-005, writer guard worker-086; this task composes them and adds the "
        "change-impact closure (KEY_MANIFEST, FROZEN drift, schema mirrors, aggregator SEP-6) and the "
        "durability test",
    ]
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(dict(verdict=report["verdict"], ready=report["ready"],
                          snapshot=report["snapshot_state"]["readiness"],
                          snapshot_frozen=report["snapshot_state"]["verify_frozen"]["summary"],
                          snapshot_sep6=report["snapshot_state"]["aggregator_sep6"]["ok"],
                          composed=report["composed"]["readiness"],
                          composed_gates={k: v["rc"] for k, v in report["composed"]["schema_gates"].items()},
                          composed_frozen=report["composed"]["verify_frozen"]["summary"],
                          controls=[(c["id"], c["passed"]) for c in controls],
                          machine_stale=machine_stale, live_drift=report["live_drift_since_snapshot"]),
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
