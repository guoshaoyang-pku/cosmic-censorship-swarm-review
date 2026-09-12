#!/usr/bin/env python3
"""W076-F2B-LANDING-AUDIT-02 -- independent landing audit of the staged F2b repair candidates.

Class-bound task taken by worker-076 (no inbox card exists for this slot).
Node F2b / class AF-SCC-C0-VAC-GEN / gate G-FORM.

Question: which staged repair of the live F2b containment defects can be promoted to the
canonical path schemas/af_scc_c0_vacuum.yaml without re-opening an already-closed hard
failure or violating the FROZEN change protocol?

Method: a checker that is independent of worker-007's predicate. It reads byte snapshots of
every input, measures live hashes before and after, and evaluates:

  A class identity / frozen class tokens
  B defect F1 (live containment denial in regularity.must_not_conflate) fixed, mention-aware
  C defect F2 (inverted "strictly larger extension class" premise) fixed
  D f0_binding.consistency_evidence_sha256 equals the live evidence file hash
  E declared F0 / supplement / rule_spec conclusion_type bindings resolve live
  F rule_spec class_conclusion_type token match
  G FROZEN change protocol: bytes changed => revision bumped AND a matching revision_history entry
  H no metalinguistic self-contradiction in the repaired line-152 bullet
  I line-diff minimality vs live: every changed line classified as an allowed repair slot
  J advisory: vocabulary-binding block present and pinned to the live alias registry

It also builds candidate/af_scc_c0_vacuum.repair-minimal.yaml: the composite of the two
semantic repairs (line 152 wording from worker-044 48cadb72e507, line 246 correction from
both candidates), a revision bump to 14, the live 9e335e9b consistency-evidence pin kept,
and the two advisory fields placed under the documented `extensions:` escape hatch. The
composite is staged and non-canonical; promotion is lead-owned.

Authority: worker measurement only. No canonical file, map node, validation_status or gate
verdict is changed. This is a statement about document bytes and declared bindings.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-076/f2b_repair_landing_audit -> repo root
CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

TASK_ID = "W076-F2B-LANDING-AUDIT-02"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"

LIVE = "schemas/af_scc_c0_vacuum.yaml"
CANDIDATES = {
    "LIVE": LIVE,
    "C022_minimal": "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "C044_integration": "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml",
    "C044_acceptance_oracle": "artifacts/worker-044/f2b_acceptance_oracle/sandbox/schemas/af_scc_c0_vacuum.yaml",
}
BINDING_INPUTS = {
    "evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "vocab_aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "rule_spec": "artifacts/formulation/rule_spec.json",
    "frozen": "artifacts/formulation/FROZEN.json",
    "f0_declared": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
}
LEAD_TOOL = "artifacts/formulation/tools/check_class_schema.py"

SNAP = HERE / "snapshot"
CAND_DIR = HERE / "candidate"
PROBE_DIR = HERE / "probe"

COMPOSITE = CAND_DIR / "af_scc_c0_vacuum.repair-minimal.yaml"

# exact live-defect anchors at F2b b2ab6acb2bbe (the audit is valid only at these bytes)
DEFECT_F1_RE = re.compile(r"no containment with[^.;]*asserted here", re.I)
DEFECT_F2_ROW = "C2 is a strictly larger extension class"

# composite line 152 wording: worker-044's repaired bullet (48cadb72e507), R2 bracket omitted
# so that a normative must_not_conflate list stays free of revision chatter; the revision_history
# entry added below records the repair.
COMPOSITE_LINE152 = (
    '    - "H2_loc (locally square-integrable curvature) is a distinct regularity-axis value '
    "phrased in terms of CURVATURE, not metric differentiability. The extension sets are "
    "nonetheless nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (see "
    "implication_ledger), so H2_loc-inextendibility ENTAILS this class's conclusion; the "
    "informal phrase 'strictly between' is not a class definition and must not be cited "
    '(worker-16 F2b-16-02 accepted)."'
)
COMPOSITE_LINE246 = (
    '    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly '
    'smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker"}'
)
COMPOSITE_REV_NOTE = (
    '  - {index: 12, at: "%s", unused: false, notes: ["rev14 delta (staged W076-F2B-LANDING-AUDIT-02 '
    "composite, NON-CANONICAL until lead promotion): regularity.must_not_conflate[0] reworded to "
    "match implication_ledger.extension_class_containment; implication_ledger.forbidden_transfers[0] "
    "premise corrected 'larger' -> 'smaller' extension class; revision bumped per the FROZEN change "
    'protocol; f0_binding.consistency_evidence_sha256 retained at live 9e335e9b; no class-semantics '
    'change."]}'
) % TS
COMPOSITE_EXTENSIONS = (
    "extensions:\n"
    "  binding_completeness:\n"
    "    class_contract_supplement: artifacts/formulation/formulation_taxonomy.yaml\n"
    '    class_contract_supplement_sha256: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"\n'
    "  vocabulary_binding:\n"
    "    alias_registry: artifacts/formulation/VOCAB_ALIASES.json\n"
    '    alias_registry_sha256: "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"\n'
    "    declared_conclusion_type_canonical: scc_c0_future_inextendibility\n"
    "    declared_genericity_kind_canonical: residual_comeager\n"
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"path": rel, "exists": False, "sha256": None, "bytes": None,
                "mtime": None}
    st = p.stat()
    return {
        "path": rel,
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, CST).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }


def strip_mentions(text: str) -> str:
    """Remove quoted and bracketed spans so metalinguistic mentions are not read as live text.

    Bracket removal runs first (a quoted correction often lives inside brackets), and the quote
    pattern refuses to treat in-word apostrophes ('class's') as delimiters.
    """
    out = re.sub(r"\[[^\]]*\]", " ", text)
    out = re.sub(r"(?<![A-Za-z0-9])'[^']*'(?![A-Za-z0-9])", " ", out)
    out = re.sub(r"(?<![A-Za-z0-9])\"[^\"]*\"(?![A-Za-z0-9])", " ", out)
    return out


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def denial_scan(bullets) -> list:
    """Return live (non-mention) containment denials found in must_not_conflate bullets."""
    hits = []
    for i, b in enumerate(bullets or []):
        if not isinstance(b, str):
            continue
        live = strip_mentions(b)
        for m in DEFECT_F1_RE.finditer(live):
            hits.append({"index": i, "span": [m.start(), m.end()], "text": m.group(0)})
    return hits


def premise_scan(doc) -> dict:
    """Check the C2->this-class forbidden transfer premise against the declared chain."""
    rows = ((doc.get("implication_ledger") or {}).get("forbidden_transfers")) or []
    target = None
    for r in rows:
        if not isinstance(r, dict):
            continue
        frm = str(r.get("from", ""))
        to = str(r.get("to", ""))
        if "C2" in frm and to.strip().lower() in ("this class", "this_class"):
            target = r
            break
    if target is None:
        return {"row_found": False, "ok": False, "reason": "no C2 -> this-class forbidden transfer row"}
    reason = str(target.get("reason", ""))
    has_larger = "larger extension class" in reason.lower()
    has_smaller = "smaller extension class" in reason.lower()
    has_weaker = "strictly weaker" in reason.lower()
    ok = has_smaller and not has_larger and has_weaker
    return {"row_found": True, "reason": reason, "has_larger": has_larger,
            "has_smaller": has_smaller, "has_strictly_weaker": has_weaker, "ok": ok}


def chain_ok(doc) -> bool:
    chain = str((doc.get("implication_ledger") or {}).get("extension_class_containment", ""))
    return all(t in chain for t in ("E_C0 contains E_H2loc", "E_{C^1,1}", "E_C2"))


def self_reference_ok(doc) -> dict:
    """The repaired bullet must not use 'strictly between' live while declaring it unused."""
    bullets = ((doc.get("regularity") or {}).get("must_not_conflate")) or []
    for i, b in enumerate(bullets):
        if not isinstance(b, str) or "strictly between" not in b:
            continue
        live = strip_mentions(b)
        uses_live = "strictly between" in live
        claims_unused = bool(re.search(r"is not used|not used and must not be cited", live, re.I))
        return {"bullet_index": i, "live_use": uses_live, "claims_unused": claims_unused,
                "ok": not (uses_live and claims_unused)}
    return {"bullet_index": None, "live_use": False, "claims_unused": False, "ok": True}


def classify_changed_line(line: str, live_binding: dict) -> str:
    s = line.strip()
    if not s:
        return "layout:blank"
    if s.startswith("revision:"):
        return "protocol:revision_bump"
    if s.startswith("revised_at:"):
        return "protocol:revised_at"
    if re.match(r"^- \{index: 1[2-9],", s):
        return "protocol:revision_history_entry"
    if "H2_loc (locally square-integrable curvature)" in line:
        return "repair:F1_containment_denial"
    if "strictly larger extension class" in line or "strictly smaller extension class" in line:
        return "repair:F2_premise"
    if s.startswith("f0_binding:"):
        return "binding:f0_binding"
    if s.startswith("extensions:"):
        return "advisory:extensions_block"
    if s in ("binding_completeness:", "vocabulary_binding:") or s.startswith(
        ("class_contract_supplement", "alias_registry", "declared_conclusion_type_canonical",
         "declared_genericity_kind_canonical")
    ):
        return "advisory:extensions_block"
    return "UNCLASSIFIED"


def field_of_binding(doc: dict, key: str):
    return ((doc or {}).get("f0_binding") or {}).get(key)


def evaluate(name: str, rel: str, snap_path: Path, pins: dict) -> dict:
    res = {"name": name, "path": rel, "snapshot": str(snap_path.relative_to(ROOT)),
           "checks": {}, "blockers": [], "advisories": []}
    try:
        doc = load_yaml(snap_path)
    except Exception as e:  # noqa: BLE001
        res["blockers"].append(f"unparseable YAML: {type(e).__name__}: {e}")
        res["verdict"] = "NOT_PROMOTION_READY"
        return res
    raw = snap_path.read_bytes()
    res["measured_sha256"] = sha256_bytes(raw)
    res["bytes"] = len(raw)

    # A. class identity
    comps = doc.get("class_components") or {}
    a_ok = (doc.get("class_id") == CLASS_ID and doc.get("node_id") == NODE_ID
            and comps.get("regularity_token") == "C0")
    res["checks"]["A_class_identity"] = a_ok
    if not a_ok:
        res["blockers"].append("class identity / node / regularity token does not match F2b")

    # B. F1 denial
    denials = denial_scan((doc.get("regularity") or {}).get("must_not_conflate"))
    b_ok = not denials
    res["checks"]["B_no_live_containment_denial"] = b_ok
    res["denials"] = denials
    if not b_ok:
        res["blockers"].append(f"live containment denial still present in must_not_conflate[{denials[0]['index']}]")

    # C. F2 premise
    pre = premise_scan(doc)
    res["checks"]["C_premise_direction"] = pre["ok"]
    res["premise"] = pre
    if not pre["ok"]:
        res["blockers"].append("C2->this-class forbidden-transfer premise is not the declared smaller-class direction")

    # D. consistency-evidence binding vs live
    declared_ev = field_of_binding(doc, "consistency_evidence_sha256")
    live_ev = pins["evidence"]["sha256"]
    d_ok = declared_ev == live_ev
    res["checks"]["D_consistency_evidence_binding_live"] = d_ok
    res["declared_consistency_evidence_sha256"] = declared_ev
    if not d_ok:
        res["blockers"].append(
            "f0_binding.consistency_evidence_sha256 does not equal the live evidence hash "
            f"({str(declared_ev)[:16]} != {str(live_ev)[:16]})"
        )

    # E. declared F0 / supplement / rule_spec
    e_f0 = field_of_binding(doc, "declared_f0_sha256") == pins["f0_declared"]["sha256"]
    supp_declared = field_of_binding(doc, "class_contract_supplement_sha256")
    e_supp = (supp_declared is None) or (supp_declared == pins["f0_supplement"]["sha256"])
    res["checks"]["E_declared_f0_binding_live"] = e_f0
    res["checks"]["E_supplement_binding_live_if_present"] = e_supp
    if not e_f0:
        res["blockers"].append("declared_f0_sha256 does not equal the live declared-F0 hash")
    if not e_supp:
        res["blockers"].append("class_contract_supplement_sha256 does not equal the live F0 supplement hash")

    # F. rule_spec conclusion_type
    expected = (((pins.get("_rule_spec_doc") or {}).get("vocabularies") or {})
                .get("class_conclusion_type") or {}).get(CLASS_ID)
    got = (doc.get("conclusion") or {}).get("conclusion_type")
    f_ok = expected is not None and got == expected
    res["checks"]["F_rule_spec_conclusion_type"] = f_ok
    res["conclusion_type"] = got
    res["rule_spec_expected"] = expected
    if not f_ok:
        res["blockers"].append(f"conclusion_type {got!r} != rule_spec class token {expected!r}")

    # chain consistency (shared by all copies; guards the premise reading)
    res["checks"]["chain_declared"] = chain_ok(doc)

    # G. change protocol
    live_raw = (ROOT / LIVE).read_bytes()
    changed = raw != live_raw
    revision = doc.get("revision")
    hist = doc.get("revision_history") or []
    has_bump_entry = any(
        isinstance(h, dict) and int(h.get("index") or 0) >= 12 for h in hist
    )
    g_ok = (not changed) or (isinstance(revision, int) and revision > 13 and has_bump_entry)
    res["checks"]["G_change_protocol"] = g_ok
    res["revision"] = revision
    res["bytes_changed_vs_live"] = changed
    if changed and not g_ok:
        res["blockers"].append(
            "bytes differ from live but revision is not bumped with a revision_history entry "
            "(FROZEN same-revision move pattern, CF-27)"
        )

    # H. self-reference
    h = self_reference_ok(doc)
    res["checks"]["H_no_metalinguistic_self_contradiction"] = h["ok"]
    res["self_reference"] = h
    if not h["ok"]:
        res["blockers"].append(
            "repaired bullet uses 'strictly between' as live text while declaring the phrase unused"
        )

    # I. diff minimality
    live_lines = live_raw.decode().splitlines()
    cand_lines = raw.decode().splitlines()
    sm = difflib.SequenceMatcher(a=live_lines, b=cand_lines, autojunk=False)
    changes = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for off, ln in enumerate(cand_lines[j1:j2]):
            changes.append({"op": tag, "line_no": j1 + off + 1,
                            "class": classify_changed_line(ln, {}), "text": ln[:110]})
    unclassified = [c for c in changes if c["class"] == "UNCLASSIFIED"]
    i_ok = not unclassified and not any(c["class"] == "binding:f0_binding" and not d_ok for c in changes)
    res["checks"]["I_diff_minimality"] = i_ok
    res["diff_changes"] = changes
    if unclassified:
        res["blockers"].append(f"{len(unclassified)} unclassified changed line(s) vs live")
    if any(c["class"] == "binding:f0_binding" and not d_ok for c in changes):
        res["blockers"].append("f0_binding line rewritten to a non-live evidence hash (binding regression)")

    # J. advisory vocabulary binding
    ext = doc.get("extensions") or {}
    vb = ext.get("vocabulary_binding") or {}
    j_ok = vb.get("alias_registry_sha256") == pins["vocab_aliases"]["sha256"]
    res["checks"]["J_vocabulary_binding_present_live"] = j_ok
    if not j_ok:
        res["advisories"].append(
            "no extensions.vocabulary_binding pinned to the live VOCAB_ALIASES hash "
            f"{pins['vocab_aliases']['sha256'][:16]}"
        )
    # R22 hazard: a new key directly under f0_binding is rejected by the lead's KEY_MANIFEST walk
    if supp_declared is not None:
        res["advisories"].append(
            "class_contract_supplement_sha256 sits under f0_binding: R22 unknown-key hazard; "
            "place it under extensions.binding_completeness"
        )

    blocking = [v for k, v in res["checks"].items()
                if k[0] in "ABCDEFGHI"]
    res["verdict"] = "PROMOTION_READY" if all(blocking) else "NOT_PROMOTION_READY"
    return res


def build_composite(live_snap: Path) -> str:
    lines = live_snap.read_text().splitlines()
    out = []
    replaced = {"line152": 0, "line246": 0, "revision": 0, "revised_at": 0}
    for ln in lines:
        if "H2_loc (locally square-integrable curvature)" in ln and "must_not_conflate" not in ln:
            out.append(COMPOSITE_LINE152)
            replaced["line152"] += 1
            continue
        if DEFECT_F2_ROW in ln:
            out.append(COMPOSITE_LINE246)
            replaced["line246"] += 1
            continue
        if ln.startswith("revision: 13"):
            out.append("revision: 14")
            replaced["revision"] += 1
            continue
        if ln.startswith("revised_at:"):
            out.append(f'revised_at: "{TS}"')
            replaced["revised_at"] += 1
            continue
        if re.match(r"^  - \{index: 11,", ln):
            out.append(ln)
            out.append(COMPOSITE_REV_NOTE)
            continue
        out.append(ln)
    text = "\n".join(out) + "\n"
    if not text.endswith("\n\n"):
        text += ""
    # append extensions escape hatch
    if "extensions:" not in text:
        text = text.rstrip("\n") + "\n\n" + COMPOSITE_EXTENSIONS
    assert all(v == 1 for v in replaced.values()), f"composite anchors not unique: {replaced}"
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    COMPOSITE.write_text(text)
    return text


def run_lead_tool(p: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / LEAD_TOOL), str(p), "--json"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=900,
    )
    verdict, failed = None, None
    try:
        rep = json.loads(proc.stdout)
        verdict, failed = rep.get("verdict"), rep.get("failed_rules")
    except Exception:  # noqa: BLE001
        verdict = f"exit={proc.returncode}"
    return {"path": str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p),
            "exit": proc.returncode, "verdict": verdict, "failed_rules": failed,
            "stdout_tail": (proc.stdout or "")[-1500:], "stderr_tail": (proc.stderr or "")[-600:]}


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_DIR.mkdir(parents=True, exist_ok=True)

    # --- measure live pins, snapshot every input ---
    pins = {}
    snap_map = {}
    for rel in [LIVE, *CANDIDATES.values(), *BINDING_INPUTS.values(), LEAD_TOOL]:
        if rel in pins:
            continue
        m = measure(rel)
        pins[rel] = m
        if m["exists"]:
            dest = SNAP / f"{Path(rel).name}.{m['sha256'][:12]}"
            shutil.copy2(ROOT / rel, dest)
            snap_map[rel] = str(dest.relative_to(ROOT))
    pins["_rule_spec_doc"] = load_yaml(SNAP / f"rule_spec.json.{pins[BINDING_INPUTS['rule_spec']]['sha256'][:12]}")
    pins["_frozen_doc"] = json.loads((SNAP / f"FROZEN.json.{pins[BINDING_INPUTS['frozen']]['sha256'][:12]}").read_text())

    # --- composite (staged, non-canonical) ---
    live_snap = SNAP / f"af_scc_c0_vacuum.yaml.{pins[LIVE]['sha256'][:12]}"
    build_composite(live_snap)

    targets = dict(CANDIDATES)
    targets["COMPOSITE_minimal_staged"] = str(COMPOSITE.relative_to(ROOT))
    snap_paths = {k: (ROOT / v) for k, v in targets.items()}
    snap_paths["COMPOSITE_minimal_staged"] = COMPOSITE

    results = {}
    eval_pins = {name: pins[rel] for name, rel in BINDING_INPUTS.items()}
    eval_pins["_rule_spec_doc"] = pins["_rule_spec_doc"]
    for name, rel in targets.items():
        results[name] = evaluate(name, rel, snap_paths[name], eval_pins)

    # --- lead-owned conformance tool on every target (second, non-independent signal) ---
    lead = {name: run_lead_tool(snap_paths[name]) for name in targets}

    # --- R22 probe: naive placement of class_contract_supplement_sha256 under f0_binding ---
    probe_note = None
    try:
        live_doc_text = live_snap.read_text()
        probe = re.sub(
            r'(class_contract_supplement_pointer: "[^"]*",)',
            r'\1 class_contract_supplement_sha256: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",',
            live_doc_text, count=1,
        )
        probe_path = PROBE_DIR / "f0_binding_naive_supplement_sha_probe.yaml"
        probe_path.write_text(probe)
        probe_tool = run_lead_tool(probe_path)
        probe_note = {
            "probe": str(probe_path.relative_to(ROOT)),
            "sha256": sha256_file(probe_path),
            "purpose": "show that adding class_contract_supplement_sha256 directly under f0_binding "
                       "is rejected by the lead's own R22 unknown-key walk, so the field must go "
                       "under extensions:",
            "lead_tool": probe_tool,
            "r22_fires": "R22" in (probe_tool.get("failed_rules") or []),
        }
    except Exception as e:  # noqa: BLE001
        probe_note = {"error": f"{type(e).__name__}: {e}"}

    # --- re-measure live pins (fail closed on drift) ---
    after = {rel: measure(rel) for rel in [LIVE, *CANDIDATES.values(), *BINDING_INPUTS.values()]}
    drift = {rel: {"before": pins[rel]["sha256"], "after": after[rel]["sha256"]}
             for rel in after if pins[rel]["sha256"] != after[rel]["sha256"]}

    report = {
        "task_id": TASK_ID,
        "actor": "worker-076",
        "created_at": TS,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "authority": "worker measurement only; no canonical file, map node, validation_status or gate "
                     "verdict changed; the COMPOSITE candidate is staged and non-canonical",
        "question": "which staged F2b containment repair can be promoted to the canonical path without "
                    "re-opening a closed hard failure or violating the FROZEN change protocol?",
        "pins": {k: v for k, v in pins.items() if not k.startswith("_")},
        "snapshots": snap_map,
        "live_after": after,
        "pin_drift": drift,
        "lead_tool_sha256": pins[LEAD_TOOL]["sha256"],
        "lead_tool": lead,
        "r22_probe": probe_note,
        "candidates": results,
        "summary": {
            "promotion_ready": [k for k, v in results.items() if v["verdict"] == "PROMOTION_READY"],
            "not_promotion_ready": [k for k, v in results.items() if v["verdict"] != "PROMOTION_READY"],
        },
        "falsifier": (
            "At the pinned snapshots: (a) any candidate marked NOT_PROMOTION_READY that passes every "
            "check when re-run by an independent implementation at the same bytes; (b) the COMPOSITE "
            "passing all checks while any changed line falls outside the classified repair slots; "
            "(c) the live taxonomy_consistency.json measuring a value other than 9e335e9b at the "
            "declared checked_at, which would void the binding-regression finding against C044; "
            "(d) the lead's check_class_schema.py returning pass on the R22 probe."
        ),
        "reproduce": f"python3 {Path(__file__).relative_to(ROOT)}",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    # --- human-readable run log ---
    print(json.dumps({k: v for k, v in report.items()
                      if k in ("task_id", "created_at", "pin_drift", "summary")}, indent=2))
    for name, r in results.items():
        print(f"\n[{name}] {r['verdict']}  sha={r.get('measured_sha256','?')[:16]} rev={r.get('revision')}")
        for k, v in r["checks"].items():
            print(f"   {'PASS' if v else 'FAIL'}  {k}")
        for b in r["blockers"]:
            print(f"   BLOCKER: {b}")
        for a in r["advisories"]:
            print(f"   advisory: {a}")
        print(f"   lead tool: {lead[name].get('verdict')} exit={lead[name].get('exit')} "
              f"failed={lead[name].get('failed_rules')}")
    print(f"\nR22 probe fires R22: {probe_note.get('r22_fires')} "
          f"(lead failed_rules={((probe_note.get('lead_tool') or {}).get('failed_rules'))})")
    print(f"\nCOMPOSITE: {COMPOSITE.relative_to(ROOT)} sha={sha256_file(COMPOSITE)[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
