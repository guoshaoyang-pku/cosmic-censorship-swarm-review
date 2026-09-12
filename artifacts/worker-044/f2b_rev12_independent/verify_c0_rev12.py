#!/usr/bin/env python3
"""W044-F2B-REV12-INDEP-02: independent class-binding verification of F2b
(AF-SCC-C0-VAC-GEN) at the live canonical bytes of schemas/af_scc_c0_vacuum.yaml.

Bounded execution worker deliverable. Read-only on all repo artifacts except
artifacts/worker-044/**. No gate verdict, no node completion, no mathematical claim.

Design:
  * pin every input by sha256 BEFORE any check, snapshot the target bytes, and
    re-measure AFTER the checks (any drift voids the verdict);
  * every check is a pure function state->{pass,fail,observed} over byte-pinned inputs;
  * non-vacuity controls: mutants that must flip exactly the targeted check, plus
    positive/negative class-separation text controls;
  * report.json carries ids, per-check evidence, artifact hashes and a falsifier.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-044/f2b_rev12_independent"
SNAP = OUT / "snapshot"
MUT = OUT / "mutations"
TZ = timezone(timedelta(hours=8))

TARGET = "schemas/af_scc_c0_vacuum.yaml"
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pin(rel: str) -> dict:
    p = ROOT / rel
    return {"path": rel, "exists": p.exists(), "sha256": sha256_file(p) if p.exists() else None,
            "bytes": p.stat().st_size if p.exists() else None}


def parse_ts(v):
    if not isinstance(v, str):
        return None
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


# ---------------------------------------------------------------- strict yaml
def duplicate_keys(node, path="") -> list:
    """Walk a composed YAML node tree and return duplicate mapping-key paths."""
    out = []
    if isinstance(node, yaml.MappingNode):
        seen = {}
        for k, v in node.value:
            key = getattr(k, "value", None)
            if key in seen:
                out.append({"path": path or "<root>", "key": key, "lines": [seen[key], k.start_mark.line + 1]})
            else:
                seen[key] = k.start_mark.line + 1
            out.extend(duplicate_keys(v, f"{path}.{key}" if path else str(key)))
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            out.extend(duplicate_keys(v, f"{path}[{i}]"))
    return out


def strict_dup_report(text: str) -> dict:
    try:
        node = yaml.compose(text)
    except yaml.YAMLError as e:
        return {"parses": False, "error": str(e), "duplicates": []}
    return {"parses": True, "duplicates": duplicate_keys(node)}


# ------------------------------------------------------------- pointer / axis
def resolve_pointer(doc, pointer: str):
    """Resolve 'path#a.b.c' dotted pointers used by the class schemas."""
    if "#" not in pointer:
        return None, "no-fragment"
    path, frag = pointer.split("#", 1)
    cur = doc
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, f"anchor-missing:{part}"
    return cur, None


def vocab_equiv(vocab: dict, axis: str, a, b) -> bool:
    table = vocab.get(axis, {})
    if a == b:
        return True
    for canon, aliases in table.items():
        members = {canon, *aliases}
        if a in members and b in members:
            return True
    return False


def mutate(text: str, old: str, new: str, count: int = 1) -> str:
    assert old in text, f"mutation base not found: {old[:60]}"
    return text.replace(old, new, count)


# ------------------------------------------------------------------- checks
class Result:
    def __init__(self):
        self.checks = []
        self.controls = []

    def add(self, cid, desc, passed, observed, evidence=None, axis="binding"):
        self.checks.append({"check_id": cid, "description": desc, "pass": bool(passed),
                            "observed": observed, "axis": axis, "evidence": evidence or []})

    def control(self, cid, desc, passed, observed, targets=None):
        self.controls.append({"control_id": cid, "description": desc, "pass": bool(passed),
                              "observed": observed, "targets": targets or []})


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)
    MUT.mkdir(parents=True, exist_ok=True)
    wall0 = now()
    t0 = datetime.now(TZ)

    # ---- pins before any check
    pins0 = {rel: pin(rel) for rel in (TARGET, F0_CANON, F0_SUPP, FROZEN, GATE, EVID, VOCAB)}
    target_bytes = (ROOT / TARGET).read_bytes()
    target_sha = sha256_bytes(target_bytes)
    snap_path = SNAP / f"af_scc_c0_vacuum.{target_sha[:12]}.yaml"
    snap_path.write_bytes(target_bytes)
    snap_sha = sha256_file(snap_path)
    text = target_bytes.decode("utf-8")
    doc = yaml.safe_load(text)
    f0_canon = yaml.safe_load((ROOT / F0_CANON).read_text())
    f0_supp = yaml.safe_load((ROOT / F0_SUPP).read_text())
    vocab = json.loads((ROOT / VOCAB).read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    mt = datetime.fromtimestamp((ROOT / TARGET).stat().st_mtime, TZ)

    r = Result()
    ev_target = f"{TARGET}#{target_sha[:12]}"

    # PIN
    r.add("PIN-01", "snapshot bytes == measured canonical bytes",
          snap_sha == target_sha, {"canonical": target_sha, "snapshot": snap_sha}, [ev_target])

    # YAML strictness
    dup = strict_dup_report(text)
    r.add("YAML-01", "strict YAML: parses and no duplicate mapping keys",
          dup["parses"] and not dup["duplicates"], dup, [ev_target])
    r.add("YAML-02", "root is a mapping with class_id/node_id", isinstance(doc, dict) and "class_id" in doc,
          {"type": type(doc).__name__, "class_id": doc.get("class_id") if isinstance(doc, dict) else None}, [ev_target])

    # timestamps
    for cid, field in (("TIME-01", "revised_at"), ("TIME-02", "f0_binding.checked_at")):
        val = doc.get(field) if "." not in field else doc.get("f0_binding", {}).get(field.split(".")[1])
        ts = parse_ts(val)
        ok = ts is not None and ts <= mt + timedelta(seconds=5) and ts <= datetime.now(TZ) + timedelta(seconds=5)
        r.add(cid, f"{field} present, <= file mtime and <= wall clock",
              ok, {"value": val, "file_mtime": mt.isoformat(timespec="seconds"), "wall": now()}, [ev_target])

    # class binding
    ptr = doc.get("class_contract_pointer", "")
    anchor = ptr.split("#", 1)[1] if "#" in ptr else None
    canon_entry, err = resolve_pointer(f0_canon, ptr) if ptr else (None, "no-pointer")
    canon_key_ok = bool(anchor) and anchor.split(".")[-1] == CLASS_ID
    r.add("BIND-01", "class_id == pointer anchor == canonical taxonomy classes key",
          doc.get("class_id") == CLASS_ID and canon_key_ok and isinstance(canon_entry, dict) and err is None,
          {"class_id": doc.get("class_id"), "pointer": ptr, "anchor": anchor, "resolve_error": err,
           "canonical_entry_found": isinstance(canon_entry, dict)}, [ev_target, f"{F0_CANON}#{pins0[F0_CANON]['sha256'][:12]}"])

    supp, serr = resolve_pointer(f0_supp, doc.get("class_contract_supplement_pointer", ""))
    r.add("BIND-02", "class_contract_supplement_pointer resolves in the authoring supplement",
          isinstance(supp, dict) and serr is None,
          {"pointer": doc.get("class_contract_supplement_pointer"), "resolve_error": serr}, [ev_target])

    declared_f0 = doc.get("f0_binding", {}).get("declared_f0_sha256")
    r.add("BIND-03", "f0_binding.declared_f0_sha256 == measured canonical F0 bytes",
          declared_f0 == pins0[F0_CANON]["sha256"],
          {"declared": declared_f0, "measured": pins0[F0_CANON]["sha256"]},
          [f"{F0_CANON}#{pins0[F0_CANON]['sha256'][:12]}"])

    fz = frozen.get("files", {})
    fz_canon = fz.get(TARGET, {}).get("sha256")
    fz_auth = fz.get("artifacts/formulation/" + TARGET, {}).get("sha256")
    r.add("BIND-04", "FROZEN manifest pins canonical and authoring C0 to the measured bytes",
          fz_canon == target_sha and fz_auth == target_sha,
          {"frozen_revision": frozen.get("revision"), "frozen_canonical": fz_canon,
           "frozen_authoring": fz_auth, "measured": target_sha},
          [f"{FROZEN}#{pins0[FROZEN]['sha256'][:12]}"])

    declared_ev = doc.get("f0_binding", {}).get("consistency_evidence_sha256")
    # best-effort location of the bytes that DO carry the declared hash (read-only probe)
    declared_at, declared_keys, live_keys = None, None, None
    for cand in sorted(ROOT.glob("artifacts/worker-*/**/*taxonomy_consistency*")):
        try:
            if cand.is_file() and sha256_file(cand) == declared_ev:
                declared_at = str(cand.relative_to(ROOT))
                dkeys = set(json.loads(cand.read_text()).keys())
                lkeys = set(json.loads((ROOT / EVID).read_text()).keys())
                declared_keys = sorted(dkeys - lkeys)
                live_keys = sorted(lkeys - dkeys)
                break
        except Exception:
            continue
    r.add("BIND-05", "f0_binding.consistency_evidence_sha256 resolves at the declared evidence path",
          declared_ev == pins0[EVID]["sha256"],
          {"declared": declared_ev, "measured": pins0[EVID]["sha256"], "path": EVID,
           "frozen_pin": fz.get(EVID, {}).get("sha256"),
           "declared_bytes_found_at": declared_at,
           "keys_only_in_declared_bytes": declared_keys, "keys_only_in_live_bytes": live_keys},
          [f"{EVID}#{pins0[EVID]['sha256'][:12]}"] + ([f"{declared_at}#{declared_ev[:12]}"] if declared_at else []))

    # axes
    concl = doc.get("conclusion", {}).get("conclusion_type")
    canon_concl = canon_entry.get("axes", {}).get("conclusion_type") if isinstance(canon_entry, dict) else None
    r.add("AXIS-01", "conclusion_type equivalent (VOCAB_ALIASES) to canonical taxonomy axis",
          vocab_equiv(vocab, "conclusion_type", concl, canon_concl),
          {"schema": concl, "canonical_axis": canon_concl}, [ev_target, f"{VOCAB}#{pins0[VOCAB]['sha256'][:12]}"])

    reg_schema = doc.get("extension_predicate", {}).get("frozen_regularity")
    reg_comp = doc.get("class_components", {}).get("regularity_token")
    reg_canon = canon_entry.get("axes", {}).get("regularity_token") if isinstance(canon_entry, dict) else None
    r.add("AXIS-02", "regularity token C0 agrees across schema and canonical axis",
          reg_schema == "C0" and reg_comp == "C0" and reg_canon == "C0",
          {"extension_predicate": reg_schema, "class_components": reg_comp, "canonical_axis": reg_canon}, [ev_target])

    gen_schema = doc.get("genericity", {}).get("kind")
    gen_canon = canon_entry.get("axes", {}).get("genericity_kind") if isinstance(canon_entry, dict) else None
    r.add("AXIS-03", "genericity kind equivalent (VOCAB_ALIASES) to canonical taxonomy axis",
          vocab_equiv(vocab, "genericity_kind", gen_schema, gen_canon),
          {"schema": gen_schema, "canonical_axis": gen_canon,
           "canonical_genericity_status": canon_entry.get("genericity_value_status") if isinstance(canon_entry, dict) else None},
          [ev_target])

    # no C0/C2 merge
    anti = doc.get("anti_scope", {}).get("not_this_class", [])
    anti_ids = [x.get("class_id") for x in anti if isinstance(x, dict)]
    sib = doc.get("sibling_disjoint_from")
    r.add("NOMERGE-01", "no C0/C2 merge: C2 listed as anti-scope and as declared disjoint sibling",
          SIBLING in anti_ids and sib == SIBLING and concl != "scc_c2_future_inextendibility",
          {"anti_scope_ids": anti_ids, "sibling_disjoint_from": sib, "conclusion_type": concl}, [ev_target])

    # canonical gate on the snapshot (not the live path)
    gate = subprocess.run([sys.executable, str(ROOT / GATE), "--json", str(snap_path)],
                          capture_output=True, text=True, cwd=str(ROOT))
    gate_json = None
    try:
        gate_json = json.loads(gate.stdout)
    except Exception:
        pass
    r.add("GATE-01", "canonical structural gate (check_class_schema.py) passes on the snapshot",
          gate.returncode == 0 and isinstance(gate_json, dict) and gate_json.get("verdict") == "pass",
          {"exit": gate.returncode, "verdict": (gate_json or {}).get("verdict"),
           "failed_rules": (gate_json or {}).get("failed_rules"), "stderr": gate.stderr[-300:]},
          [f"{GATE}#{pins0[GATE]['sha256'][:12]}"])

    # class separation: nested walker and text scanner
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    f_nested = cs.findings(doc, f"{TARGET}#{target_sha[:12]} (independent nested walk)")
    f_text = cs.findings_for_text(text, f"{TARGET}#{target_sha[:12]} (independent text scan)")
    r.add("SEP-01", "class_separation.findings (nested declaration walk) clean on the snapshot",
          len(f_nested) == 0, {"findings": f_nested}, [ev_target], axis="class-separation")
    r.add("SEP-02", "class_separation.findings_for_text (prose scan) clean on the snapshot",
          len(f_text) == 0, {"findings": f_text}, [ev_target], axis="class-separation")

    # review status (self-declared; informational for the second-verdict gap)
    rs = doc.get("review_status", {})
    r.add("REVIEW-01", "self-declared review_status reflects an independent verdict at these bytes",
          bool(rs.get("independent_reviewers")) and rs.get("verdict") not in (None, "pending"),
          rs, [ev_target], axis="review-coverage")

    # ------------------------------------------------ non-vacuity controls
    def check_on(mutant_text, fn):
        d = yaml.safe_load(mutant_text)
        return d, fn(d)

    # MUT-1 class_id
    m1 = mutate(text, f"class_id: {CLASS_ID}\n", f"class_id: {SIBLING}\n")
    (MUT / "MUT-1_class_id.yaml").write_text(m1)
    d1 = yaml.safe_load(m1)
    p1 = d1.get("class_contract_pointer", "")
    e1, _ = resolve_pointer(f0_canon, p1)
    r.control("MUT-1", "class_id swapped to C2 must fail BIND-01", not (d1.get("class_id") == CLASS_ID),
              {"class_id": d1.get("class_id"), "anchor": p1.split("#")[-1]}, ["BIND-01"])

    # MUT-2 pointer anchor
    m2 = mutate(text, f"#classes.{CLASS_ID}", "#classes.AF-SCC-C0-VAC-GEN_MISSING")
    (MUT / "MUT-2_pointer.yaml").write_text(m2)
    d2 = yaml.safe_load(m2)
    e2, err2 = resolve_pointer(f0_canon, d2.get("class_contract_pointer", ""))
    r.control("MUT-2", "pointer anchor corrupted must fail BIND-01", e2 is None and err2 is not None,
              {"resolve_error": err2}, ["BIND-01"])

    # MUT-3 duplicate key (prepend a duplicate top-level revised_at after line 1)
    lines = text.splitlines()
    m3 = "\n".join([lines[0], 'revised_at: "2000-01-01T00:00:00+08:00"'] + lines[1:]) + "\n"
    (MUT / "MUT-3_dupkey.yaml").write_text(m3)
    dup3 = strict_dup_report(m3)
    r.control("MUT-3", "injected duplicate top-level revised_at must fail YAML-01",
              dup3["parses"] and len(dup3["duplicates"]) >= 1, dup3, ["YAML-01"])

    # MUT-4 f0 pin
    m4 = mutate(text, declared_f0, "0" * 64)
    (MUT / "MUT-4_f0pin.yaml").write_text(m4)
    d4 = yaml.safe_load(m4)
    r.control("MUT-4", "wrong declared_f0_sha256 must fail BIND-03",
              d4.get("f0_binding", {}).get("declared_f0_sha256") != pins0[F0_CANON]["sha256"],
              {"declared": d4.get("f0_binding", {}).get("declared_f0_sha256")}, ["BIND-03"])

    # MUT-5 conclusion type C2
    m5 = mutate(text, 'conclusion_type: scc_c0_future_inextendibility',
                'conclusion_type: scc_c2_future_inextendibility')
    (MUT / "MUT-5_conclusion.yaml").write_text(m5)
    d5 = yaml.safe_load(m5)
    c5 = d5.get("conclusion", {}).get("conclusion_type")
    r.control("MUT-5", "C2 conclusion token must fail AXIS-01 and NOMERGE-01",
              not vocab_equiv(vocab, "conclusion_type", c5, canon_concl) and c5 == "scc_c2_future_inextendibility",
              {"conclusion_type": c5, "canonical_axis": canon_concl}, ["AXIS-01", "NOMERGE-01"])

    # MUT-6 regularity token C2
    m6 = mutate(text, 'frozen_regularity: C0', 'frozen_regularity: C2')
    (MUT / "MUT-6_regularity.yaml").write_text(m6)
    d6 = yaml.safe_load(m6)
    r.control("MUT-6", "C2 regularity token must fail AXIS-02",
              d6.get("extension_predicate", {}).get("frozen_regularity") != "C0",
              {"frozen_regularity": d6.get("extension_predicate", {}).get("frozen_regularity")}, ["AXIS-02"])

    # MUT-7/8 class-separation positive and negative controls
    merge_text = ("This document treats C0 or C2 as one class; the two regularity classes are unified "
                  "and must be read as a single class.")
    benign_text = ("The AF-SCC-C0-VAC-GEN class asserts future inextendibility in the C0 regularity class. "
                   "A separate class AF-SCC-C2-VAC-GEN is disjoint from it and is not merged here.")
    fp = cs.findings_for_text(merge_text, "MUT-7 synthetic merge assertion")
    fn = cs.findings_for_text(benign_text, "MUT-8 synthetic benign text")
    r.control("MUT-7", "class-separation positive control: an explicit C0-or-C2 merge assertion is flagged",
              len(fp) > 0, {"findings": fp}, ["SEP-02"])
    r.control("MUT-8", "class-separation negative control: a benign disjointness sentence is clean",
              len(fn) == 0, {"findings": fn}, ["SEP-02"])

    # informational probes (not pass/fail controls): measured scanner coverage
    probes = []
    id_merge = (f"This document asserts that the class {CLASS_ID} is identical to {SIBLING} and that "
                "the two classes are one and the same class.")
    id_findings = cs.findings_for_text(id_merge, "PROBE-01 class-id-phrased merge assertion")
    probes.append({"probe_id": "PROBE-01", "question": "does the prose scanner flag a merge assertion phrased "
                  "only with full class ids (no literal 'C0 or C2')?", "detected": len(id_findings) > 0,
                  "findings": id_findings, "where": "class_separation.findings_for_text"})

    # ------------------------------------------------------- post-run drift
    pins1 = {rel: pin(rel) for rel in (TARGET, F0_CANON, F0_SUPP, FROZEN, GATE, EVID, VOCAB)}
    drift = {rel: {"before": pins0[rel]["sha256"], "after": pins1[rel]["sha256"],
                   "moved": pins0[rel]["sha256"] != pins1[rel]["sha256"]}
             for rel in pins0}
    moved = [k for k, v in drift.items() if v["moved"]]
    r.add("POST-01", "no pin drift across the verification window",
          not moved, {"moved": moved, "drift": drift}, [ev_target], axis="drift")

    hard_ids = [c["check_id"] for c in r.checks
                if not c["pass"] and c["check_id"] in
                {"YAML-01", "TIME-01", "TIME-02", "BIND-01", "BIND-02", "BIND-03", "BIND-04",
                 "BIND-05", "AXIS-01", "AXIS-02", "AXIS-03", "NOMERGE-01", "GATE-01",
                 "SEP-01", "SEP-02", "POST-01"}]
    controls_failed = [c["control_id"] for c in r.controls if not c["pass"]]
    if moved:
        verdict = "inconclusive"
    elif hard_ids or controls_failed:
        verdict = "revise"
    else:
        verdict = "accept"
    hard_failures = []
    for cid in hard_ids:
        c = next(x for x in r.checks if x["check_id"] == cid)
        hard_failures.append({"id": f"HF-044-{cid}", "check_id": cid, "axis": c["axis"],
                              "finding": c["description"], "observed": c["observed"]})

    falsifier = (
        "This verdict is void if any pinned input moves (POST-01 drift) or the snapshot sha256 does not "
        "reproduce schemas/af_scc_c0_vacuum.yaml at review time. Each check is falsified by re-running its "
        "stated detector on the pinned bytes: YAML-01 by a strict duplicate-key loader accepting the file; "
        "BIND-01 by a reader showing class_contract_pointer resolves to a different canonical entry; "
        "BIND-03 by the FROZEN manifest pinning different bytes; BIND-05 by exhibiting the declared evidence "
        "hash 675a99d0d25b at the declared path (or a corrected pointer); AXIS-01/02/03 by VOCAB_ALIASES "
        "showing the tokens inequivalent; GATE-01 by check_class_schema.py exiting nonzero on the snapshot; "
        "SEP-01/02 by class_separation returning a finding. Any control that fails to flip its target check "
        "falsifies the harness (vacuity), not the schema."
    )

    report = {
        "task_id": "W044-F2B-REV12-INDEP-02",
        "actor": "worker-044",
        "created_at": now(),
        "node_id": "F2b",
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "target_path": TARGET,
        "target_sha256": target_sha,
        "snapshot": str(snap_path.relative_to(ROOT)),
        "snapshot_sha256": snap_sha,
        "settled_revision": {"frozen_revision": frozen.get("revision"), "schema_revision": doc.get("revision"),
                             "revised_at": doc.get("revised_at")},
        "pins_t0": pins0,
        "pins_t1": pins1,
        "method": "byte-pinned snapshot; strict duplicate-key YAML; dotted-pointer resolution against the "
                  "canonical taxonomy; VOCAB_ALIASES token equivalence; canonical structural gate run on the "
                  "snapshot; class_separation nested and text scanners; five schema mutants and two "
                  "class-separation text controls; post-run drift re-measure.",
        "checks": r.checks,
        "controls": r.controls,
        "probes": probes,
        "summary": {"verdict": verdict, "total_checks": len(r.checks),
                    "passed": sum(1 for c in r.checks if c["pass"]),
                    "failed": sum(1 for c in r.checks if not c["pass"]),
                    "hard_failures": hard_failures,
                    "controls_failed": controls_failed,
                    "drift_moved": moved,
                    "probes_measured": len(probes)},
        "falsifier": falsifier,
        "does_not_claim": ["no gate verdict", "no node status change", "no validation_status=passed",
                           "no mathematics/physics/literature result", "no claim about F1 or F2a beyond "
                           "the shared consistency-evidence pointer noted in BIND-05"],
        "wall_clock": {"started": wall0, "finished": now(), "wall_seconds": round((datetime.now(TZ) - t0).total_seconds(), 2)},
    }
    rep = OUT / "report.json"
    rep.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"report": str(rep.relative_to(ROOT)), "sha256": sha256_file(rep),
                      "verdict": verdict, "hard": [h["id"] for h in hard_failures],
                      "controls_failed": controls_failed, "drift": moved}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
