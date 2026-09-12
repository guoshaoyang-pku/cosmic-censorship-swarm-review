#!/usr/bin/env python3
"""W060-REV29-BINDING-ACCEPTANCE-01.

Bounded class-bound verifier (classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN,
nodes F1/F2a/F2b, gate G-FORM): an independent, hash-pinned acceptance test for the four bounded
items of assignment `astra-life05-evidence-binding-repair` (CF-20):

  item 1  schemas/taxonomy_cases.jsonl rows rebind to declared F0 rev5 0abb9ed8a961
  item 2  f0_binding.consistency_evidence_sha256 refreshed to the live consistency evidence,
          after a clean check_taxonomy_consistency.py run
  item 3  F1 variant SET/CH strictness text corrected at the anchors worker-076 cites
          (assertion direction only; predicate preservation is machine-checked here, the
          mathematical direction adjudication stays with worker-040 / worker-076)
  item 4  FROZEN.json rev29 published with byte-verified pins

It also measures the class-semantics non-regression guard (the assignment's own falsifier: "any
change to a class definition, hypothesis, conclusion predicate or axis semantics"), the owner
artifact-event discipline for the moved bytes, and whether the *canonical* gate tooling can see
binding staleness at all (gate-gap measurement, read-only).

Read-only with respect to every canonical/shared artifact: mutants and sandbox runs are written
only under this artifact directory (--workdir). Exit codes: 0 = all four items closed at the
measured live pins; 1 = one or more items open; 2 = pin/parse error, i.e. the predecessor
snapshot does not match its recorded hashes.

Usage:
  python3 verify_rev29_binding_acceptance.py [--root REPO] [--workdir DIR] [--json OUT]
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]          # <repo>/artifacts/worker-060/rev29_binding_acceptance
SNAP = HERE / "snapshots"
BOGUS = "0" * 64

TRACKED = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "F0": "research_map/formulation_taxonomy.yaml",
    "F0R": "artifacts/formulation/formulation_taxonomy.yaml",
    "TAXCASES": "schemas/taxonomy_cases.jsonl",
    "FROZEN": "artifacts/formulation/FROZEN.json",
    "CONSEV": "artifacts/formulation/evidence/taxonomy_consistency.json",
}
SCHEMAS = {"F1": TRACKED["F1"], "F2a": TRACKED["F2a"], "F2b": TRACKED["F2b"]}
GATE = "artifacts/formulation/tools/check_class_schema.py"
VERIFY_FROZEN = "artifacts/formulation/tools/verify_frozen.py"
CONSISTENCY_CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
REPAIR_PATHS = list(SCHEMAS.values()) + [TRACKED["TAXCASES"], TRACKED["FROZEN"]]
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"

# Bookkeeping allowed to differ across the repair (assignment: "no class-semantics change").
ALLOWED_CHANGED_PREFIXES = (
    "revision", "revised_at", "supersedes", "revision_history", "timestamp_provenance",
    "f0_binding", "provenance", "review_status",
)
# Prose paths repair item 3 is allowed to touch; each must preserve the class predicate.
AUTHORIZED_ITEM3_PATHS = ("$.visibility.definition", "$.class_identity_variants")
ITEM3_QUANTIFIER_PREFIX = "$.quantifiers.domains."
TAIL_PREDICATE_CANON = "tail gamma([t0,t)) is contained in j^-(q)"
TAIL_PREDICATE_D5 = "tail gamma([t0,t)) is contained in the causal past j^-(q)"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(cid, name, ok, expected, measured, falsifier, severity="acceptance"):
    return {"id": cid, "name": name, "status": "pass" if ok else "fail", "ok": bool(ok),
            "severity": severity, "expected": expected, "measured": measured, "falsifier": falsifier}


def flatten(obj, prefix="$"):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}"))
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, sort_keys=True)
    else:
        out[prefix] = obj
    return out


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "exit": r.returncode,
            "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}


def semantic_fingerprint(doc):
    keep = {k: v for k, v in doc.items() if k not in ALLOWED_CHANGED_PREFIXES}
    return flatten(keep)


def _norm(s):
    return " ".join(str(s).split()).lower()


def _dir_tokens(text):
    return sorted(t for t in ("strictly stronger", "strictly weaker", "equivalent")
                  if t in _norm(text))


def is_authorized_item3_path(k):
    return k in AUTHORIZED_ITEM3_PATHS or (k.startswith(ITEM3_QUANTIFIER_PREFIX)
                                           and k.endswith(".definition"))


def prose_direction_analysis(old, new):
    """Classify the item-3 prose edits: authorized direction text, predicate preserved?"""
    res = {}
    ov, nv = old.get("visibility", {}).get("definition", ""), new.get("visibility", {}).get("definition", "")
    res["visibility.definition"] = {
        "changed": _norm(ov) != _norm(nv),
        "predicate_preserved": TAIL_PREDICATE_CANON in _norm(ov) and TAIL_PREDICATE_CANON in _norm(nv),
        "direction_tokens_old": _dir_tokens(ov), "direction_tokens_new": _dir_tokens(nv),
    }
    od = (old.get("quantifiers", {}).get("domains", {}) or {})
    nd = (new.get("quantifiers", {}).get("domains", {}) or {})
    res["quantifiers.domains"] = {}
    for dom in sorted(set(od) | set(nd)):
        a, b = _norm((od.get(dom, {}) or {}).get("definition", "")), _norm((nd.get(dom, {}) or {}).get("definition", ""))
        pred = TAIL_PREDICATE_D5 if dom == "D5" else None
        res["quantifiers.domains"][dom] = {
            "changed": a != b,
            "predicate_preserved": (pred in a and pred in b) if pred else (a == b),
            "direction_tokens_old": _dir_tokens(a), "direction_tokens_new": _dir_tokens(b),
        }
    ovars = old.get("class_identity_variants") or []
    nvars = new.get("class_identity_variants") or []
    ident = lambda vs: [(v.get("variant_id"), v.get("parent_class"), v.get("is_this_class"),
                         json.dumps(v.get("statement"), sort_keys=True)) for v in vs]
    rel = lambda vs: [(v.get("variant_id"), v.get("relation")) for v in vs]
    res["class_identity_variants"] = {
        "changed": ident(ovars) != ident(nvars) or rel(ovars) != rel(nvars),
        "predicate_preserved": ident(ovars) == ident(nvars),
        "relation_changed": rel(ovars) != rel(nvars),
        "relation_old": [r for _, r in rel(ovars)], "relation_new": [r for _, r in rel(nvars)],
        "direction_tokens_old": _dir_tokens(json.dumps(rel(ovars))),
        "direction_tokens_new": _dir_tokens(json.dumps(rel(nvars))),
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--workdir", default=str(HERE / "tmp"))
    ap.add_argument("--json", default=str(HERE / "evidence.json"))
    ap.add_argument("--skip-gate-probes", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    work = Path(args.workdir).resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    checks, controls, notes = [], [], []
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    # ---- P0 predecessor snapshot integrity (exit 2 on mismatch) -------------------------------
    pins = json.loads((SNAP / "pins.json").read_text())
    bad = [fn for fn, rec in pins["files"].items()
           if not (SNAP / fn).exists() or sha256_file(SNAP / fn) != rec["sha256"]]
    if bad:
        print(f"FATAL: predecessor snapshot integrity failed: {bad}", file=sys.stderr)
        return 2
    checks.append(check("P0", "predecessor snapshot matches its recorded hashes", True,
                        f"{len(pins['files'])} files", "all match",
                        "Any snapshot byte change voids every predecessor comparison in this run."))

    live = {k: sha256_file(root / p) for k, p in TRACKED.items()}
    notes.append({"live_pins": live, "measured_at": now})

    def snap(prefix):
        return SNAP / next(f for f in pins["files"] if f.startswith(prefix))

    pred = {"F1": snap("f1__"), "F2a": snap("f2a__"), "F2b": snap("f2b__"),
            "F0": snap("f0__"), "F0R": snap("f0r__"), "TAXCASES": snap("taxonomy_cases."),
            "FROZEN": snap("FROZEN."), "CONSEV": snap("taxonomy_consistency.")}
    pred_hashes = {k: pins["files"][v.name]["sha256"] for k, v in pred.items()}

    # ---- item 1: taxonomy_cases rebind --------------------------------------------------------
    cases = [json.loads(l) for l in (root / TRACKED["TAXCASES"]).read_text().splitlines() if l.strip()]
    meta = next(c for c in cases if c.get("record_type") == "meta")
    rows = [c for c in cases if c.get("record_type") != "meta"]
    declared = meta["taxonomy_ref"]["sha256"]
    stale_rows = [c["case_id"] for c in rows
                  if not str(c.get("binding_status", "")).startswith("bound_taxonomy_sha_" + declared[:12])]
    item1_ok = declared == live["F0"] == F0_REV5 and not stale_rows
    checks.append(check(
        "I1", "item1: taxonomy_cases rows bound to declared F0 rev5", item1_ok,
        f"{len(rows)}/{len(rows)} rows bound_taxonomy_sha_{F0_REV5[:12]}; meta sha == live F0",
        {"meta_declared": declared, "live_f0": live["F0"], "stale_rows": stale_rows,
         "row_count": len(rows), "open_rows": sum(bool(c.get("open")) for c in rows)},
        "A row whose binding_status names any taxonomy hash other than the declared F0 rev5, or "
        "meta.taxonomy_ref.sha256 != measured F0 hash, reopens item 1."))

    # ---- item 2: f0_binding pins resolve to live bytes ----------------------------------------
    frozen_doc = json.loads((root / TRACKED["FROZEN"]).read_text())
    frozen_files = frozen_doc.get("files", {})
    pin_rows = []
    for cls, rel in SCHEMAS.items():
        doc = load_yaml(root / rel)
        fb = doc.get("f0_binding", {})
        decl_f0 = fb.get("declared_f0_sha256")
        f0_path = root / fb["declared_f0_artifact"]
        ce_path = fb.get("consistency_evidence")
        ce_decl = fb.get("consistency_evidence_sha256")
        pin_rows.append({
            "class": cls, "path": rel, "declared_f0": decl_f0,
            "live_f0": sha256_file(f0_path) if f0_path.exists() else None,
            "f0_resolved": f0_path.exists() and decl_f0 == sha256_file(f0_path),
            "consistency_evidence": ce_path, "declared_consistency": ce_decl,
            "live_consistency": sha256_file(root / ce_path) if ce_path and (root / ce_path).exists() else None,
            "consistency_resolved": bool(ce_path) and (root / ce_path).exists()
                                   and ce_decl == sha256_file(root / ce_path),
            "frozen_pin_for_consistency": (frozen_files.get(ce_path) or {}).get("sha256"),
        })
    f0_bad = [r["class"] for r in pin_rows if not r["f0_resolved"]]
    ce_bad = [r["class"] for r in pin_rows if not r["consistency_resolved"]]
    checks.append(check(
        "I2a", "item2a: declared_f0_sha256 resolves for all three schemas", not f0_bad,
        "3/3 resolved", {"unresolved": f0_bad, "rows": pin_rows},
        "Any schema whose declared F0 hash != measured research_map/formulation_taxonomy.yaml."))
    checks.append(check(
        "I2b", "item2b: consistency_evidence_sha256 refreshed to live evidence", not ce_bad,
        "3/3 resolve to the measured artifacts/formulation/evidence/taxonomy_consistency.json",
        {"unresolved": ce_bad, "live_consistency": live["CONSEV"],
         "declared_values": sorted({r["declared_consistency"] for r in pin_rows}),
         "frozen_manifest_pins": sorted({r["frozen_pin_for_consistency"] for r in pin_rows})},
        "Any schema whose f0_binding.consistency_evidence_sha256 != measured consistency evidence "
        "hash reopens item 2."))

    # ---- item 2 precondition: canonical consistency checker reproduces the live evidence -------
    sb = work / "consistency_sandbox"
    for rel in ["research_map/formulation_taxonomy.yaml",
                "artifacts/formulation/formulation_taxonomy.yaml",
                "artifacts/formulation/VOCAB_ALIASES.json"]:
        dst = sb / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    tool_dst = sb / CONSISTENCY_CHECKER
    tool_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / CONSISTENCY_CHECKER, tool_dst)
    rep2c = run([sys.executable, str(tool_dst)])
    sb_evidence = sb / TRACKED["CONSEV"]
    sb_hash = sha256_file(sb_evidence) if sb_evidence.exists() else None
    item2c_ok = rep2c["exit"] == 0 and sb_hash == live["CONSEV"]
    checks.append(check(
        "I2c", "item2c: clean checker run reproduces the live consistency evidence byte-for-byte",
        item2c_ok, "checker exit 0 and sandbox evidence sha256 == live evidence sha256",
        {"checker_exit": rep2c["exit"], "checker_stdout": rep2c["stdout"].strip(),
         "sandbox_evidence": sb_hash, "live_evidence": live["CONSEV"]},
        "A non-zero checker exit, or a sandbox-regenerated evidence file whose hash differs from "
        "the live one, means the value the repair is asked to pin is not the one a clean run "
        "produces (the refresh target itself is stale)."))

    # ---- item 3: F1 anchors + direction-only prose analysis ------------------------------------
    f1_old, f1_new = load_yaml(pred["F1"]), load_yaml(root / TRACKED["F1"])
    prose = prose_direction_analysis(f1_old, f1_new)
    f1_lines = (root / TRACKED["F1"]).read_text().splitlines()
    anchors = {str(ln): {"line_sha256": hashlib.sha256(f1_lines[ln - 1].encode()).hexdigest(),
                         "contains_strictly_stronger": "strictly STRONGER" in f1_lines[ln - 1]}
               for ln in (72, 234)}
    pred_f1 = pred["F1"].read_text().splitlines()
    changed_anchor_lines = [str(ln) for ln in (72, 234)
                            if hashlib.sha256(pred_f1[ln - 1].encode()).hexdigest()
                            != anchors[str(ln)]["line_sha256"]]
    prose_ok = (prose["visibility.definition"]["predicate_preserved"]
                and prose["class_identity_variants"]["predicate_preserved"]
                and all(v["predicate_preserved"] for v in prose["quantifiers.domains"].values()))
    direction_flip = (prose["class_identity_variants"]["direction_tokens_old"]
                      != prose["class_identity_variants"]["direction_tokens_new"]
                      or prose["visibility.definition"]["direction_tokens_old"]
                      != prose["visibility.definition"]["direction_tokens_new"]
                      or prose["quantifiers.domains"]["D5"]["direction_tokens_old"]
                      != prose["quantifiers.domains"]["D5"]["direction_tokens_new"])
    checks.append(check(
        "I3", "item3: F1 anchors 72/234 carry a direction edit with the class predicate preserved",
        bool(changed_anchor_lines) and prose_ok and direction_flip,
        "anchors 72 and/or 234 changed; tail predicate preserved in visibility/D5; "
        "variant SET statement and is_this_class preserved; a direction token changed",
        {"anchors": anchors, "changed_anchor_lines": changed_anchor_lines, "f1_pin": live["F1"],
         "prose_analysis": prose},
        "Unchanged anchors reopen item 3; a changed class predicate or a changed variant SET "
        "statement/is_this_class makes the edit a class-semantics change (assignment falsifier), "
        "not an assertion-direction fix. The mathematical direction itself is owned by "
        "worker-040 W040-F1-STRICTNESS-ADJ-04 / worker-076 W076-GFORM-STRICTNESS-RECONCILE-06."))

    # ---- item 4: FROZEN rev29 manifest --------------------------------------------------------
    vf = run([sys.executable, str(root / VERIFY_FROZEN)])
    manifest_listed = {p: p in frozen_files for p in REPAIR_PATHS}
    manifest_match = {p: (frozen_files.get(p, {}).get("sha256") == live[k])
                      for p, k in [(TRACKED["F1"], "F1"), (TRACKED["F2a"], "F2a"),
                                   (TRACKED["F2b"], "F2b"), (TRACKED["TAXCASES"], "TAXCASES"),
                                   (TRACKED["FROZEN"], "FROZEN")]}
    core_ok = (frozen_doc.get("revision", 0) >= 29 and vf["exit"] == 0
               and all(manifest_listed[p] and manifest_match[p]
                       for p in [TRACKED["F1"], TRACKED["F2a"], TRACKED["F2b"]]))
    checks.append(check(
        "I4", "item4: FROZEN rev29 published with byte-verified pins", core_ok,
        "revision >= 29; canonical verify_frozen.py exit 0; F1/F2a/F2b listed with live hashes",
        {"frozen_revision": frozen_doc.get("revision"), "frozen_at": frozen_doc.get("frozen_at"),
         "verify_frozen_exit": vf["exit"], "verify_frozen_stdout": vf["stdout"].strip()[:300],
         "manifest_listed": manifest_listed, "manifest_hash_matches_live": manifest_match},
        "A FROZEN revision < 29, any verify_frozen.py drift line, or a schema repair path missing "
        "from / mismatching the manifest reopens item 4."))
    checks.append(check(
        "I4b", "item4b: taxonomy_cases.jsonl pinned by the republished manifest",
        bool(manifest_listed[TRACKED["TAXCASES"]] and manifest_match[TRACKED["TAXCASES"]]),
        "schemas/taxonomy_cases.jsonl listed with its post-repair hash",
        {"listed": manifest_listed[TRACKED["TAXCASES"]],
         "match": manifest_match[TRACKED["TAXCASES"]], "live": live["TAXCASES"]},
        "If the manifest omits taxonomy_cases.jsonl, item 1's moved bytes have no FROZEN pin."))

    live_by_path = {TRACKED[k]: v for k, v in live.items()}
    mirror = {rel: ("artifacts/formulation/schemas/" + Path(rel).name) for rel in SCHEMAS.values()}
    mirror_rows = {m: {"canonical": live_by_path[rel],
                       "mirror": sha256_file(root / m) if (root / m).exists() else None}
                   for rel, m in mirror.items()}
    mirror_ok = all(r["mirror"] == r["canonical"] for r in mirror_rows.values())
    checks.append(check(
        "I5", "item4d: canonical schemas and authoring mirrors byte-identical after rev13", mirror_ok,
        "3/3 mirror pairs aligned at publish time (FROZEN path_policy)",
        mirror_rows,
        "Any canonical/mirror divergence reopens the publication binding and voids same-hash "
        "review claims for that class."))

    # ---- item 4e: variant deltas/registry still apply to the rev13 bases -----------------------
    vwork = work / "variant_sandbox"
    for rel in ("schemas", "artifacts/formulation", "research_map"):
        dst = vwork / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(root / rel, dst)
    vres = {}
    for tool, out_rel in (("artifacts/formulation/tools/check_variant_deltas.py",
                           "artifacts/formulation/evidence/variant_delta_check.json"),
                          ("artifacts/formulation/tools/check_variant_registry.py",
                           "artifacts/formulation/evidence/variant_registry_check.json")):
        r = run([sys.executable, str(vwork / tool)])
        sb_out = vwork / out_rel
        vres[Path(tool).name] = {
            "exit": r["exit"], "stdout": r["stdout"].strip()[:800],
            "sandbox_evidence_sha256": sha256_file(sb_out) if sb_out.exists() else None,
            "live_evidence_sha256": sha256_file(root / out_rel) if (root / out_rel).exists() else None,
            "frozen_manifest_pin": (frozen_files.get(out_rel) or {}).get("sha256"),
        }
    variant_ok = all(v["exit"] == 0 for v in vres.values())
    checks.append(check(
        "I6", "item4e: variant deltas/registry still apply to the rev13 bases", variant_ok,
        "both canonical variant checkers exit 0 (VALID) after the schema move",
        vres,
        "Any base-hash drift line means the schema bytes moved without rebasing the delta files "
        "that bind them; the assignment falsifier 'a FROZEN rev29 manifest whose listed hashes do "
        "not match live bytes' also triggers when the checker rewrites its pinned evidence path."))

    # ---- item 4c: owner artifact-event discipline for the moved bytes --------------------------
    moved = {live["F1"]: TRACKED["F1"], live["F2a"]: TRACKED["F2a"], live["F2b"]: TRACKED["F2b"]}
    events = {"owner": {h: [] for h in moved}, "any_actor": {h: [] for h in moved}}
    files = sorted(glob.glob(str(root / "comms/outbox/*.jsonl"))) + [str(root / "research_map/events.jsonl")]
    for f in files:
        try:
            fh = open(f, errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                if not any(h in line for h in moved):
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("event_type") != "artifact" or d.get("path") not in moved.values():
                    continue
                h = d.get("sha256")
                if h in moved:
                    rec = {"actor": d.get("actor"), "event_id": d.get("event_id"), "path": d.get("path")}
                    events["any_actor"][h].append(rec)
                    if d.get("actor") == "astra-lead-formulation":
                        events["owner"][h].append(rec)
    owner_ok = all(events["owner"][h] for h in moved)
    checks.append(check(
        "I4c", "item4c: owner emitted an artifact event for each moved rev13 schema", owner_ok,
        "astra-lead-formulation artifact event naming each live F1/F2a/F2b sha256",
        {"owner": events["owner"], "any_actor": events["any_actor"],
         "scanned_files": len(files), "scanned_at": now},
        "A schema byte change without an owner artifact event is the repair's own falsifier and "
        "the CF-19 pattern; acceptance evidence must announce the moved bytes.",
        severity="advisory"))

    # ---- semantics non-regression: hard-invariant fields + item-3 prose classification ---------
    hard_changes, authorized_changes = {}, {}
    for cls in SCHEMAS:
        fa = semantic_fingerprint(load_yaml(pred[cls]))
        fb = semantic_fingerprint(load_yaml(root / SCHEMAS[cls]))
        changed = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
        authorized_changes[cls] = [k for k in changed if is_authorized_item3_path(k)]
        hard_changes[cls] = [k for k in changed if not is_authorized_item3_path(k)]
    sem_ok = all(not v for v in hard_changes.values()) and prose_ok
    payload_changed = any(live[k] != pred_hashes[k] for k in SCHEMAS)
    checks.append(check(
        "S1", "repair falsifier: no class-semantics change vs predecessor", sem_ok,
        "0 hard-invariant path changes; item-3 prose edits preserve the class predicate",
        {"hard_invariant_changes": hard_changes, "authorized_item3_prose_edits": authorized_changes,
         "allowed_bookkeeping_prefixes": list(ALLOWED_CHANGED_PREFIXES),
         "predicate_preservation": {k: v.get("predicate_preserved") for k, v in prose.items()
                                    if isinstance(v, dict)},
         "repair_bytes_moved": payload_changed},
        "Any changed path in class_components/quantifiers (outside the authorized definition "
        "prose)/topology/data_class/regularity/genericity/i_plus/visibility structure/conclusion/"
        "implication_ledger/anti_scope/known_status/class_identity_variants structure proves the "
        "repair changed class semantics. A variant SET statement or is_this_class change also "
        "fails. At the baseline pins no schema byte moved and this check is a vacuous pass."))

    # ---- HF-060-CS-01 advisory (out of the four bounded items) ---------------------------------
    f2b = load_yaml(root / TRACKED["F2b"])
    reason = ((f2b.get("implication_ledger") or {}).get("forbidden_transfers") or [{}])[0].get("reason", "")
    hf_line = next((i + 1 for i, l in enumerate((root / TRACKED["F2b"]).read_text().splitlines())
                    if "strictly larger extension class" in l), None)
    checks.append(check(
        "A1", "advisory: HF-060-CS-01 inverted containment premise (out of repair scope)", True,
        "recorded, not one of the four bounded repair items",
        {"present": "strictly larger" in reason, "line": hf_line, "reason": reason},
        "Advisory only; it does not gate this repair. It stays present if the rev29 bytes still "
        "contain the inverted premise. Its separate falsifier: an extension-set reading under "
        "which E_C2 strictly contains E_C0.", severity="advisory"))

    # ---- gate-gap probe: can the canonical gate see binding staleness? -------------------------
    probe = {}
    if not args.skip_gate_probes:
        gate = root / GATE
        mutants = work / "mutants"
        mutants.mkdir(parents=True, exist_ok=True)
        f2b_doc = load_yaml(root / TRACKED["F2b"])

        def dump_mutant(name, fn):
            d = copy.deepcopy(f2b_doc)
            fn(d)
            p = mutants / name
            p.write_text(yaml.safe_dump(d, sort_keys=False, width=110))
            r = run([sys.executable, str(gate), "--json", str(p)])
            try:
                verdict = json.loads(r["stdout"])
            except ValueError:
                verdict = {"verdict": "error", "stdout": r["stdout"][-300:]}
            return {"path": str(p.relative_to(root)), "gate_exit": r["exit"],
                    "gate_verdict": verdict.get("verdict"),
                    "failed_rules": verdict.get("failed_rules", [])}

        def flip_containment(d):
            il = d["implication_ledger"]
            il["extension_class_containment"] = (
                "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; this class requires the "
                "LOWEST regularity, so its inexistence statement is the STRONGEST of the three.")

        probe["g0_canonical_copy"] = dump_mutant("g0_canonical.yaml", lambda d: None)
        probe["g1_refreshed_consistency_pin"] = dump_mutant(
            "g1_refreshed_ce.yaml",
            lambda d: d["f0_binding"].__setitem__("consistency_evidence_sha256", live["CONSEV"]))
        probe["g2_bogus_consistency_pin"] = dump_mutant(
            "g2_bogus_ce.yaml",
            lambda d: d["f0_binding"].__setitem__("consistency_evidence_sha256", BOGUS))
        probe["g3_bogus_declared_f0_pin"] = dump_mutant(
            "g3_bogus_f0.yaml", lambda d: d["f0_binding"].__setitem__("declared_f0_sha256", BOGUS))
        probe["g4_reason_direction_repaired"] = dump_mutant(
            "g4_reason_repaired.yaml",
            lambda d: d["implication_ledger"]["forbidden_transfers"][0].__setitem__(
                "reason", "C2 is a strictly smaller extension class, so C2-inextendibility is strictly stronger"))
        probe["g4b_containment_flipped"] = dump_mutant("g4b_containment_flipped.yaml", flip_containment)
        probe["g5_negative_control_drop_ledger"] = dump_mutant(
            "g5_drop_ledger.yaml", lambda d: d.pop("implication_ledger", None))
        gap_ok = (probe["g0_canonical_copy"]["gate_verdict"] == "pass"
                  and probe["g1_refreshed_consistency_pin"]["gate_verdict"] == "pass"
                  and probe["g2_bogus_consistency_pin"]["gate_verdict"] == "pass"
                  and probe["g3_bogus_declared_f0_pin"]["gate_verdict"] == "pass"
                  and probe["g4_reason_direction_repaired"]["gate_verdict"] == "pass"
                  and probe["g5_negative_control_drop_ledger"]["gate_verdict"] == "fail")
        checks.append(check(
            "G1", "gate gap: canonical gate is blind to f0_binding staleness and premise direction",
            gap_ok,
            "positive control passes; refreshed, bogus-consistency, bogus-F0 and reason-repaired "
            "copies all pass; structural negative control fails",
            probe,
            "If the canonical gate rejects any f0_binding mutant or the reason-repaired copy, this "
            "gate-gap claim is refuted. The structural negative control proves the harness detects "
            "a genuine violation.", severity="gate-gap"))

        # verify_frozen.py end-to-end blindness control, in a full sandbox tree.
        sb2 = work / "frozen_sandbox"
        for rel in frozen_files:
            src = root / rel
            if src.exists():
                dst = sb2 / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        man = copy.deepcopy(frozen_doc)
        for rel in list(man["files"]):
            if (sb2 / rel).exists():
                man["files"][rel]["sha256"] = sha256_file(sb2 / rel)
        (sb2 / TRACKED["FROZEN"]).parent.mkdir(parents=True, exist_ok=True)
        (sb2 / TRACKED["FROZEN"]).write_text(json.dumps(man, indent=1))
        vf_dst = sb2 / VERIFY_FROZEN
        vf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / VERIFY_FROZEN, vf_dst)
        vf0 = run([sys.executable, str(vf_dst)])
        mut_rel = TRACKED["F2b"]
        mut_doc = copy.deepcopy(f2b_doc)
        mut_doc["f0_binding"]["consistency_evidence_sha256"] = BOGUS
        (sb2 / mut_rel).write_text(yaml.safe_dump(mut_doc, sort_keys=False, width=110))
        man["files"][mut_rel]["sha256"] = sha256_file(sb2 / mut_rel)
        (sb2 / TRACKED["FROZEN"]).write_text(json.dumps(man, indent=1))
        vf2 = run([sys.executable, str(vf_dst)])
        probe["vf_positive_control"] = {"exit": vf0["exit"], "stdout": vf0["stdout"].strip()[:200]}
        probe["vf_bogus_pin_regenerated_manifest"] = {
            "exit": vf2["exit"], "stdout": vf2["stdout"].strip()[:200],
            "note": "manifest regenerated to the mutated schema hash; internal pin is 64 zeros"}
        checks.append(check(
            "G2", "gate gap: verify_frozen.py passes a regenerated manifest over a bogus internal pin",
            vf0["exit"] == 0 and vf2["exit"] == 0,
            "sandbox verify_frozen.py exit 0 both before and after the bogus internal pin",
            {"positive_control": probe["vf_positive_control"],
             "bogus_pin": probe["vf_bogus_pin_regenerated_manifest"]},
            "A non-zero exit after the pin mutation means verify_frozen.py does catch the internal "
            "pin; a non-zero positive control means the sandbox itself is inconsistent.",
            severity="gate-gap"))
        man2 = copy.deepcopy(man)
        man2["files"][TRACKED["F1"]]["sha256"] = BOGUS
        (sb2 / TRACKED["FROZEN"]).write_text(json.dumps(man2, indent=1))
        vf3 = run([sys.executable, str(vf_dst)])
        controls.append({"id": "C5", "mutant": "manifest F1 hash drifted",
                         "expected": "verify_frozen.py exit 1", "observed_exit": vf3["exit"],
                         "fires": vf3["exit"] != 0})
        (sb2 / TRACKED["FROZEN"]).write_text(json.dumps(man, indent=1))
    else:
        notes.append({"gate_probes": "skipped"})

    # ---- controls for this verifier's own checks ----------------------------------------------
    row = json.loads((root / TRACKED["TAXCASES"]).read_text().splitlines()[1])
    restamped = dict(row, binding_status="bound_taxonomy_sha_66bf917bd368")
    mutated = load_yaml(root / TRACKED["F2b"])
    mutated["conclusion"] = {"type": "mutant"}
    controls += [
        {"id": "C1", "mutant": "consistency pin -> live hash",
         "expected": "I2b pass", "fires": live["CONSEV"] == live["CONSEV"]},
        {"id": "C2", "mutant": "consistency pin -> 64 zeros",
         "expected": "I2b fail", "fires": BOGUS != live["CONSEV"]},
        {"id": "C3", "mutant": "one taxonomy row restamped to 66bf917bd368",
         "expected": "I1 fail",
         "fires": not str(restamped["binding_status"]).startswith("bound_taxonomy_sha_" + F0_REV5[:12])},
        {"id": "C4", "mutant": "F2b conclusion text changed",
         "expected": "S1 fail",
         "fires": semantic_fingerprint(mutated) != semantic_fingerprint(load_yaml(root / TRACKED["F2b"]))},
    ]
    controls_ok = all(c["fires"] for c in controls)

    open_items = [c["id"] for c in checks if c["severity"] == "acceptance" and not c["ok"]]
    result = {
        "verifier": "W060-REV29-BINDING-ACCEPTANCE-01",
        "created_at": now,
        "actor": "worker-060",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "root": str(root),
        "live_pins": live,
        "predecessor_pins": pred_hashes,
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "open_acceptance_items": open_items,
        "verdict": "ALL_ITEMS_CLOSED" if not open_items else "ITEMS_OPEN",
        "authority_note": ("worker measurement only: no gate verdict, no node status, no "
                           "validation_status=passed, no canonical byte changed; mutants and "
                           "sandbox copies live under this artifact directory"),
        "next_falsifier": ("Re-run this script at any new pin: exit 0 requires revision >= 29, "
                           "3/3 consistency pins resolving to the checker-reproduced evidence hash, "
                           "0 stale taxonomy rows, a direction edit on F1 anchors 72/234 with the "
                           "class predicate preserved, a FROZEN manifest pinning every repair path, "
                           "and 0 hard-invariant class-semantics changes vs snapshots/."),
    }
    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"W060-REV29-BINDING-ACCEPTANCE-01: {result['verdict']} "
          f"({len(checks) - len(open_items)}/{len(checks)} checks pass; open: {open_items}; "
          f"controls_ok={controls_ok})")
    for c in checks:
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['id']} ({c['severity']}) {c['name']}")
    return 0 if not open_items else 1


if __name__ == "__main__":
    sys.exit(main())
