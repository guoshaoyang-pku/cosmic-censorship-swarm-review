#!/usr/bin/env python3
"""W078-REC12-PREACCEPT-01 -- independent, hash-bound acceptance measurement for the controller
card `astra-life05-evidence-binding-repair` (Astra pass-05, REC-12): repair of F1 / F2a / F2b
(classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN) and publication of FROZEN rev29.

Card items (map.assignments['astra-life05-evidence-binding-repair']):
  1. rebind schemas/taxonomy_cases.jsonl rows to declared F0 rev5 0abb9ed8a961 and re-run its checker
  2. refresh f0_binding.consistency_evidence_sha256 in all three schemas to the live
     artifacts/formulation/evidence/taxonomy_consistency.json 9e335e9b after a clean
     check_taxonomy_consistency.py run
  3. correct the F1 variant SET/CH strictness text at the exact lines worker-076 cites
     (assertion direction only)
  4. publish FROZEN.json rev29 with byte-verified pins and artifact events for every moved path
Card falsifier: any change to a class definition, hypothesis, conclusion predicate or axis
semantics; an F0 write; a schema byte change without an artifact event; a rev29 manifest whose
listed hashes do not match live bytes.

Method: read-only on every canonical path; writes only under this artifact directory and private
temp dirs.  The check definitions were authored from the pass-05 card and worker-076's pinned probe
while the repair was landing; the rev29 measurement is therefore retrospective for items 1/2/4 but
the direction facts in item 3 are worker-076's machine-checked table, not this harness's
re-derivation.  A recovered rev12 baseline (worker-086's independent pinned copies + worker-074's
rev28 sandbox copy) is projected through the same kernels so the instrument's pre-repair firing
pattern is explicit rather than asserted.

Usage:
  python3 verify_rec12_preaccept.py [--snapshot]
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-078/rec12_preaccept"
SNAP = OUT / "snapshot"
TZ = timezone(timedelta(hours=8))

TASK_ID = "W078-REC12-PREACCEPT-01"
ACTOR = "worker-078"
NODE_ID = "F1,F2a,F2b"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"

SCHEMAS = {
    "F1": {"path": "schemas/af_wcc_vacuum.yaml", "class_id": "AF-WCC-VAC-GEN"},
    "F2a": {"path": "schemas/af_scc_c2_vacuum.yaml", "class_id": "AF-SCC-C2-VAC-GEN"},
    "F2b": {"path": "schemas/af_scc_c0_vacuum.yaml", "class_id": "AF-SCC-C0-VAC-GEN"},
}
CARD_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/taxonomy_cases.jsonl",
    "artifacts/formulation/FROZEN.json",
]
SNAPSHOT_PATHS = CARD_PATHS + [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/flash-02/check_taxonomy_cases.py",
    "artifacts/flash-02/leak_rule_catalog.json",
    "artifacts/flash-02/taxonomy_cases_check_report.json",
    "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
]
# Independent rev12/rev28 baselines (third-party pinned copies, not this worker's snapshots).
BASELINE = {
    "F1": {"path": "artifacts/worker-086/gform_rev12/pinned/af_wcc_vacuum.cce9c60146d6.yaml",
           "sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
           "copied_from": "schemas/af_wcc_vacuum.yaml"},
    "F2a": {"path": "artifacts/worker-086/gform_rev12/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
            "sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
            "copied_from": "schemas/af_scc_c2_vacuum.yaml"},
    "F2b": {"path": "artifacts/worker-086/gform_rev12/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml",
            "sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
            "copied_from": "schemas/af_scc_c0_vacuum.yaml"},
}
BASELINE_FROZEN = {
    "path": "artifacts/worker-074/evbind_rehearsal/sandbox/artifacts/formulation/FROZEN.json",
    "sha256": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "copied_from": "artifacts/formulation/FROZEN.json",
}
BASELINE_F0 = {
    "path": "artifacts/worker-086/gform_rev12/pinned/formulation_taxonomy.canonical.0abb9ed8a961.yaml",
    "sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "copied_from": "research_map/formulation_taxonomy.yaml",
}
BOUND_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPERSEDED_F0 = "66bf917b"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONSISTENCY_TOOL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CASES_CHECKER = "artifacts/flash-02/check_taxonomy_cases.py"
CASES_PATH = "schemas/taxonomy_cases.jsonl"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
F0_PATH = "research_map/formulation_taxonomy.yaml"
EVENTS_PATH = "research_map/events.jsonl"
CASES_BINDING_TOKEN = "bound_taxonomy_sha_0abb9ed8a961"
REQUIRED_FROZEN_REVISION = 29

REVISION_META_KEYS = {
    "revision", "revised_at", "authored_at", "timestamp_provenance", "supersedes",
    "revision_history", "status", "f0_binding",
}
ITEM3_ALLOWED_F1 = (
    "quantifiers/domains/D5/definition",
    "visibility/definition",
    "visibility/negation_conclusion",
    "class_identity_variants[0]/relation",
    "class_identity_variants[0]/falsifier",
    "class_identity_variants[0]/note",
    "class_identity_variants[0]/statement",
    "class_identity_variants[0]/why_separate",
)
FORBIDDEN_PATTERNS = (
    "class_components/", "/class_id", "/class_ids", "conclusion_type",
    "/axes", "genericity", "hypothesis", "extension_topology", "extension_regularity",
    "data_class", "class_identity_variants", "transfer", "implication_ledger",
)

# ----------------------------------------------------------------------------- helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())


def measure(rel: str) -> dict:
    p = ROOT / rel
    try:
        b = p.read_bytes()
    except FileNotFoundError:
        return {"path": rel, "exists": False}
    st = p.stat()
    return {
        "path": rel,
        "exists": True,
        "sha256": sha256_bytes(b),
        "bytes": len(b),
        "mtime": datetime.fromtimestamp(st.st_mtime, TZ).isoformat(timespec="seconds"),
        "mtime_epoch": round(st.st_mtime, 3),
    }


def load_yaml_strict(text: str):
    import yaml

    class StrictLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        seen = []
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"duplicate mapping key: {key!r}")
            seen.append(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return yaml.load(text, Loader=StrictLoader)


def leaf_paths(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaf_paths(v, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from leaf_paths(x, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def leaf_map(obj) -> dict:
    return {p: v for p, v in leaf_paths(obj)}


def changed_leaves(before, after) -> list:
    b, a = leaf_map(before), leaf_map(after)
    out = []
    for p in sorted(set(b) | set(a)):
        if b.get(p) != a.get(p):
            out.append({"path": p, "before": b.get(p), "after": a.get(p)})
    return out


def parse_jsonl(text: str) -> list:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text()


def declared_class_ids(doc) -> dict:
    out = {
        "class_id": doc.get("class_id"),
        "class_ids": sorted(doc.get("class_ids") or []),
        "classes": sorted((doc.get("classes") or {}).keys()) if isinstance(doc.get("classes"), dict) else None,
        "class_components": sorted((doc.get("class_components") or {}).keys()) if isinstance(doc.get("class_components"), dict) else None,
    }
    return out


# --------------------------------------------------------------------- pure check kernels
def k_a1a(cases_text: str, f0_live_sha: str, f0_pinned_sha: str) -> dict:
    rows = parse_jsonl(cases_text)
    meta = [r for r in rows if r.get("record_type") == "meta"]
    cases = [r for r in rows if r.get("record_type") != "meta"]
    stale = [r.get("case_id") for r in cases
             if str(r.get("binding_status", "")) != CASES_BINDING_TOKEN]
    meta_ok = bool(meta) and (meta[0].get("taxonomy_ref") or {}).get("sha256") == f0_live_sha
    live_stale_refs = [r.get("case_id") for r in cases if SUPERSEDED_F0 in json.dumps(r)]
    ok = (not stale) and meta_ok and (f0_live_sha == f0_pinned_sha) and (not live_stale_refs)
    return {
        "status": "PASS" if ok else "FAIL",
        "rows": len(rows), "case_rows": len(cases),
        "rows_with_stale_binding_status": stale[:10],
        "meta_taxonomy_sha256": (meta[0].get("taxonomy_ref") or {}).get("sha256") if meta else None,
        "meta_binds_live_f0": meta_ok,
        "live_binding_refs_to_superseded_f0": live_stale_refs,
        "note": "historical rebind_note mentions of 66bf917b are excluded (not a live binding field)",
    }


def k_a1b(report: dict, live_cases_sha: str, returncode: int) -> dict:
    ok = (returncode == 0 and report.get("verdict") == "PASS" and not report.get("errors")
          and report.get("controls_all_detected") is True
          and ((report.get("cases") or {}).get("sha256")) == live_cases_sha)
    return {
        "status": "PASS" if ok else "FAIL",
        "checker_exit": returncode, "verdict": report.get("verdict"),
        "errors": report.get("errors"),
        "controls_all_detected": report.get("controls_all_detected"),
        "report_cases_sha256": (report.get("cases") or {}).get("sha256"),
        "live_cases_sha256": live_cases_sha,
    }


def k_a1c(report_measure: dict, cases_measure: dict) -> dict:
    if not report_measure.get("exists"):
        return {"status": "FAIL", "reason": "no repo checker report with the live corpus hash"}
    fresh = report_measure["mtime_epoch"] >= cases_measure["mtime_epoch"]
    return {
        "status": "PASS" if fresh else "FAIL",
        "report": report_measure.get("path"),
        "report_mtime_epoch": report_measure.get("mtime_epoch"),
        "corpus_mtime_epoch": cases_measure.get("mtime_epoch"),
        "report_cases_sha256": report_measure.get("cases_sha256"),
    }


def k_a2a(declared_pin, live_evidence_sha: str, declared_f0, live_f0_sha: str) -> dict:
    ok = declared_pin == live_evidence_sha and declared_f0 == live_f0_sha
    return {
        "status": "PASS" if ok else "FAIL",
        "declared_consistency_evidence_sha256": declared_pin,
        "live_consistency_evidence_sha256": live_evidence_sha,
        "declared_f0_sha256": declared_f0, "live_f0_sha256": live_f0_sha,
    }


def k_a2b(evidence_text: str, live_f0_sha: str, live_supplement_sha: str) -> dict:
    doc = json.loads(evidence_text)
    anchored_f0 = doc.get("map_taxonomy_sha256")
    anchored_lead = doc.get("lead_contract_sha256")
    ok = anchored_f0 == live_f0_sha and anchored_lead == live_supplement_sha
    return {
        "status": "PASS" if ok else "WARN", "advisory": True,
        "map_taxonomy_sha256": anchored_f0, "lead_contract_sha256": anchored_lead,
        "note": "card item 2 as worded refreshes the pointer only; input-anchoring is residual CF-20 / worker-047 CB-2 and does not block the card item",
    }


def k_a2c(mirror_bytes, live_bytes: bytes, mirror_rc: int, log: str) -> dict:
    ok = mirror_rc == 0 and mirror_bytes == live_bytes
    return {
        "status": "PASS" if ok else "FAIL",
        "checker_exit": mirror_rc,
        "mirror_sha256": sha256_bytes(mirror_bytes) if mirror_bytes is not None else None,
        "live_sha256": sha256_bytes(live_bytes),
        "byte_identical": mirror_bytes == live_bytes,
        "log_tail": log[-400:],
    }


def _sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def _find(text: str, *needles, flags=re.I) -> list:
    return [s for s in _sentences(text) if all(re.search(n, s, flags) for n in needles)]


def k_a3a_direction(f1_doc: dict) -> dict:
    d5 = str(((f1_doc.get("quantifiers") or {}).get("domains") or {}).get("D5", {}).get("definition", ""))
    vis = str((f1_doc.get("visibility") or {}).get("definition", ""))
    variants = f1_doc.get("class_identity_variants") or []
    setv = next((v for v in variants if v.get("kind") == "set_based_visibility_reading"), {})
    relation = str(setv.get("relation", ""))
    whole_stronger = _find(d5, r"whole[- ]curve", r"strictly\s+STRONGER")
    misclassify = _find(vis, r"would\s+misclassify", r"whole")
    set_stronger = _find(relation, r"variant\s+SET", r"strictly\s+STRONGER")
    set_weaker = _find(relation, r"strictly\s+WEAKER")
    failures = []
    if whole_stronger:
        failures.append("D5.definition still asserts whole-curve containment strictly STRONGER (T1: equivalent)")
    if misclassify:
        failures.append("visibility.definition still asserts whole-containment would misclassify (T1 non-sequitur)")
    if set_stronger:
        failures.append("variant SET relation still asserts SET strictly STRONGER (T4: SET strictly weaker)")
    return {
        "status": "PASS" if not failures else "FAIL",
        "anchors": {
            "d5_whole_curve_strictly_stronger": whole_stronger[:2],
            "visibility_misclassify": misclassify[:2],
            "set_relation_strictly_stronger": set_stronger[:2],
            "set_relation_strictly_weaker": set_weaker[:2],
        },
        "failures": failures,
    }


def k_a3d_falsifier(f1_doc: dict) -> dict:
    variants = f1_doc.get("class_identity_variants") or []
    setv = next((v for v in variants if v.get("kind") == "set_based_visibility_reading"), {})
    falsifier = str(setv.get("falsifier", ""))
    old = _find(falsifier, r"show the two readings equivalent")
    return {
        "status": "WARN" if old else "PASS",
        "adjudication": (
            "worker-076's rev12 table asked for a finiteness/dominating-member restatement at this line; "
            "the rev13 relation now states non-equivalence with T2/T3/T4 and the retained sentence is a "
            "logically apt falsifier OF THE CORRECTED 'strictly WEAKER' claim (equivalence would collapse it). "
            "Residual is the missing explicit finiteness/maximum hypothesis, not an inverted direction."
        ),
        "retained_sentence": old[:1],
    }


def k_a3b_true_strength(f1_doc: dict) -> dict:
    neg = str((f1_doc.get("visibility") or {}).get("negation_conclusion", ""))
    keep = _find(neg, r"B-containment", r"strictly\s+stronger")
    return {"status": "PASS" if keep else "WARN",
            "true_strength_sentence_present": bool(keep)}


def k_a3c_cross_artifact(registry_doc: dict, delta_doc: dict) -> dict:
    reg_set = next((v for v in (registry_doc.get("variants") or []) if v.get("variant_id") == "SET"), {})
    reg_strength = str(reg_set.get("strength", ""))
    delta_strength = str(delta_doc.get("strength", ""))

    def leading_label(text: str) -> str:
        head = re.split(r"[(\[:]", text, maxsplit=1)[0]
        return head.strip()

    bad = []
    for label, text in (("VARIANT_REGISTRY.json variants[SET].strength", reg_strength),
                        ("AF-WCC-VAC-GEN.variant-SET.delta.json strength", delta_strength)):
        head = leading_label(text)
        if re.search(r"strictly\s+stronger", head, re.I):
            bad.append({"artifact": label, "leading_label": head, "full_text": text[:220]})
    mentions = []
    for label, text in (("VARIANT_REGISTRY.json variants[SET].strength", reg_strength),
                        ("AF-WCC-VAC-GEN.variant-SET.delta.json strength", delta_strength)):
        if re.search(r"strictly\s+stronger", text, re.I) and not re.search(r"strictly\s+stronger", leading_label(text), re.I):
            mentions.append({"artifact": label, "mention": leading_label(text) or text[:120]})
    return {
        "status": "PASS" if not bad else "FAIL", "advisory": True, "out_of_card_scope": True,
        "inverted_strength_labels": bad,
        "metalinguistic_mentions_of_superseded_label": [m["artifact"] for m in mentions],
        "note": "only the leading strength label is judged; a historical '(corrected from strictly STRONGER)' mention is not an assertion",
    }


def k_a4a(frozen_doc: dict) -> dict:
    rev = frozen_doc.get("revision")
    ok = isinstance(rev, int) and rev >= REQUIRED_FROZEN_REVISION
    return {"status": "PASS" if ok else "FAIL", "revision": rev, "required": f">= {REQUIRED_FROZEN_REVISION}"}


def k_a4b(frozen_doc: dict, live_hashes: dict) -> dict:
    bad, checked = [], 0
    for section in ("files", "logical_artifacts"):
        for key, meta in (frozen_doc.get(section) or {}).items():
            if not isinstance(meta, dict) or "sha256" not in meta:
                continue
            path = meta.get("path") if section == "logical_artifacts" else key
            if not path:
                bad.append({"path": key, "manifest": meta["sha256"], "live": None,
                            "reason": "logical artifact without a path"})
                continue
            checked += 1
            live = (live_hashes.get(path) or {}).get("sha256")
            if live != meta["sha256"]:
                bad.append({"path": path, "manifest": meta["sha256"], "live": live})
    return {"status": "PASS" if not bad else "FAIL", "checked": checked, "mismatches": bad}


def k_a4c(frozen_doc: dict, moved_paths: list) -> dict:
    listed = frozen_doc.get("files") or {}
    missing = [p for p in moved_paths if p not in listed]
    return {
        "status": "PASS" if not missing else "FAIL",
        "moved_paths": moved_paths,
        "pinned": [p for p in moved_paths if p in listed],
        "missing_from_rev29_manifest": missing,
        "taxonomy_cases_pinned": CASES_PATH in listed,
        "frozen_self_reference_excluded": True,
    }


def k_a4d(frozen_doc: dict, live_evidence_sha: str) -> dict:
    pin = ((frozen_doc.get("files") or {}).get(EVIDENCE) or {}).get("sha256")
    return {"status": "PASS" if pin == live_evidence_sha else "FAIL",
            "manifest_evidence_sha256": pin, "live_evidence_sha256": live_evidence_sha}


def _event_index(events: list) -> dict:
    idx = {}
    for e in events:
        if e.get("event_type") != "artifact":
            continue
        p = str(e.get("path", "")).lstrip("./")
        idx.setdefault(p, set()).add(e.get("sha256"))
    return idx


def k_a4e(moved_paths: list, live_hashes: dict, events: list, outbox_events: list) -> dict:
    accepted, outbox = _event_index(events), _event_index(outbox_events)
    missing, pending = [], []
    for p in moved_paths:
        want = (live_hashes.get(p) or {}).get("sha256")
        if want in accepted.get(p, set()):
            continue
        if want in outbox.get(p, set()):
            pending.append(p)
        else:
            missing.append(p)
    status = "PASS" if (moved_paths and not missing and not pending) else (
        "WARN" if (moved_paths and not missing) else ("UNMEASURED" if not moved_paths else "FAIL"))
    return {
        "status": status, "moved_paths": moved_paths,
        "paths_without_artifact_event": missing,
        "paths_emitted_pending_ingest": pending,
    }


def k_a4f(moved_paths: list, before_hashes: dict, live_hashes: dict) -> dict:
    blobs = []
    for p in (ROOT / "artifacts/formulation").rglob("*"):
        if p.is_file() and p.suffix.lower() in (".json", ".jsonl", ".md", ".txt", ".yaml"):
            try:
                blobs.append(p.read_text(errors="replace"))
            except OSError:
                pass
    missing = []
    for path in moved_paths:
        before = (before_hashes.get(path) or {}).get("sha256")
        after = (live_hashes.get(path) or {}).get("sha256")
        if not before or not after or before == after:
            continue
        if not any(before in t and after in t for t in blobs):
            missing.append(path)
    return {"status": "PASS" if not missing else "FAIL", "moved_paths": moved_paths,
            "paths_without_before_after_report": missing}


def k_a4g(frozen_live_sha: str, events: list, outbox_events: list) -> dict:
    accepted, outbox = _event_index(events), _event_index(outbox_events)
    in_acc = frozen_live_sha in accepted.get(FROZEN_PATH, set())
    in_out = frozen_live_sha in outbox.get(FROZEN_PATH, set())
    return {
        "status": "PASS" if in_acc else ("WARN" if in_out else "FAIL"),
        "frozen_sha256": frozen_live_sha,
        "in_accepted_stream": in_acc, "in_outbox_pending_ingest": in_out,
    }


def k_a5a(live_f0_sha: str, baseline_f0_sha: str) -> dict:
    return {"status": "PASS" if live_f0_sha == baseline_f0_sha else "FAIL",
            "live": live_f0_sha, "baseline": baseline_f0_sha}


def classify_changes(changes: list, node: str) -> dict:
    forbidden, item3, other, allowed = [], [], [], []
    for c in changes:
        p = c["path"]
        q = p.lstrip("/")
        if node == "F1" and any(q.startswith(a) for a in ITEM3_ALLOWED_F1):
            item3.append(c)
            continue
        head = q.split("/")[0].split("[")[0] if q else ""
        if head in REVISION_META_KEYS:
            allowed.append(c)
            continue
        if any(pat in p for pat in FORBIDDEN_PATTERNS):
            forbidden.append(c)
            continue
        other.append(c)
    return {"forbidden": forbidden, "item3_prose": item3, "other_scope": other, "allowed_metadata": allowed}


def k_a5b(changes_by_node: dict) -> dict:
    forbidden = {n: v["forbidden"] for n, v in changes_by_node.items() if v["forbidden"]}
    out_of_scope = {n: v["other_scope"] for n, v in changes_by_node.items() if v["other_scope"]}
    return {
        "status": "PASS" if not forbidden else "FAIL",
        "forbidden_changes": forbidden,
        "out_of_scope_changes_warn": out_of_scope,
        "item3_prose_changes": {n: [c["path"] for c in v["item3_prose"]] for n, v in changes_by_node.items() if v["item3_prose"]},
        "allowed_metadata_change_count": {n: len(v.get("allowed_metadata") or []) for n, v in changes_by_node.items()},
    }


def k_a5c(live_ids: dict, baseline_ids: dict) -> dict:
    return {"status": "PASS" if live_ids == baseline_ids else "FAIL",
            "live": live_ids, "baseline": baseline_ids}


# ----------------------------------------------------------------------------- measurement
def run_cases_checker(tmp: Path) -> tuple:
    report_path = tmp / "taxonomy_cases_report.json"
    proc = subprocess.run([sys.executable, str(ROOT / CASES_CHECKER), "--report", str(report_path)],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    return proc.returncode, report, (proc.stdout + proc.stderr)[-2000:]


def run_consistency_mirror(tmp: Path) -> tuple:
    mirror = tmp / "mirror"
    for rel in (F0_PATH, SUPPLEMENT, "artifacts/formulation/VOCAB_ALIASES.json", CONSISTENCY_TOOL):
        dst = mirror / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    (mirror / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(mirror / CONSISTENCY_TOOL)], cwd=str(mirror),
                          capture_output=True, text=True, timeout=300)
    emitted = mirror / EVIDENCE
    return proc.returncode, (emitted.read_bytes() if emitted.exists() else None), (proc.stdout + proc.stderr)[-2000:]


def write_snapshot() -> dict:
    if SNAP.exists():
        shutil.rmtree(SNAP)
    SNAP.mkdir(parents=True)
    sums = []
    for rel in SNAPSHOT_PATHS:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        sums.append(f"{sha256_file(dst)}  {rel}")
    (SNAP / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    return {"files": len(sums), "sha256sums": sha256_file(SNAP / "SHA256SUMS.txt")}


def load_baselines() -> dict:
    out = {}
    for node, b in BASELINE.items():
        p = ROOT / b["path"]
        ok = p.exists() and sha256_file(p) == b["sha256"] if p.exists() else False
        out[node] = {"source": b, "exists": p.exists(), "sha256_matches": bool(ok),
                     "doc": load_yaml_strict(p.read_text()) if ok else None}
    p = ROOT / BASELINE_FROZEN["path"]
    ok = p.exists() and sha256_file(p) == BASELINE_FROZEN["sha256"] if p.exists() else False
    out["FROZEN"] = {"source": BASELINE_FROZEN, "exists": p.exists(), "sha256_matches": bool(ok),
                     "doc": json.loads(p.read_text()) if ok else None}
    p = ROOT / BASELINE_F0["path"]
    ok = p.exists() and sha256_file(p) == BASELINE_F0["sha256"] if p.exists() else False
    out["F0"] = {"source": BASELINE_F0, "exists": p.exists(), "sha256_matches": bool(ok), "doc": None}
    return out


def load_outbox_events() -> list:
    rows = []
    for p in sorted((ROOT / "comms/outbox").glob("*.jsonl")):
        rows.extend(parse_jsonl(p.read_text(errors="replace")))
    return rows


def run_once(snap_info: dict, baseline: dict) -> dict:
    started = datetime.now(TZ)
    live = {rel: measure(rel) for rel in SNAPSHOT_PATHS}
    live[EVENTS_PATH] = measure(EVENTS_PATH)

    f1 = load_yaml_strict(read_text(SCHEMAS["F1"]["path"]))
    f2a = load_yaml_strict(read_text(SCHEMAS["F2a"]["path"]))
    f2b = load_yaml_strict(read_text(SCHEMAS["F2b"]["path"]))
    docs = {"F1": f1, "F2a": f2a, "F2b": f2b}
    frozen = json.loads(read_text(FROZEN_PATH))
    registry = json.loads(read_text("artifacts/formulation/VARIANT_REGISTRY.json"))
    delta = json.loads(read_text("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"))
    evidence_text = read_text(EVIDENCE)
    cases_text = read_text(CASES_PATH)

    with tempfile.TemporaryDirectory(prefix="w078_rec12_") as td:
        tmp = Path(td)
        cases_rc, cases_report, cases_log = run_cases_checker(tmp)
        mirror_rc, mirror_bytes, mirror_log = run_consistency_mirror(tmp)

    live_evidence_sha = live[EVIDENCE]["sha256"]
    live_f0_sha = live[F0_PATH]["sha256"]
    live_supp_sha = live[SUPPLEMENT]["sha256"]
    live_cases_sha = live[CASES_PATH]["sha256"]
    events = parse_jsonl(read_text(EVENTS_PATH))
    outbox_events = load_outbox_events()

    manifest_paths = set((frozen.get("files") or {}).keys()) | set((frozen.get("logical_artifacts") or {}).keys())
    live_manifest = {p: measure(p) for p in manifest_paths}

    checks = []

    def add(cid, item, node, status, detail, evidence, falsifier, class_id=None):
        checks.append({"id": cid, "card_item": item, "node": node, "status": status, "detail": detail,
                       "class_id": class_id, "evidence_refs": evidence, "falsifier": falsifier})

    d = k_a1a(cases_text, live_f0_sha, BOUND_F0)
    add("A1a", 1, "F0/corpus", d["status"], d,
        [f"{CASES_PATH}#{live_cases_sha[:12]}", f"{F0_PATH}#{live_f0_sha[:12]}"],
        "any case row binding_status or meta.taxonomy_ref.sha256 off the declared F0 rev5 hash")
    d = k_a1b(cases_report, live_cases_sha, cases_rc)
    add("A1b", 1, "F0/corpus", d["status"], d, [CASES_CHECKER, f"{CASES_PATH}#{live_cases_sha[:12]}"],
        "checker non-zero exit, errors non-empty, controls not all detected, or report on another corpus hash")
    repo_report = None
    for p in sorted((ROOT / "artifacts/flash-02").glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        c = doc.get("cases") if isinstance(doc, dict) else None
        if isinstance(c, dict) and c.get("sha256") == live_cases_sha:
            m = measure(str(p.relative_to(ROOT)))
            m["cases_sha256"] = c["sha256"]
            if repo_report is None or m["mtime_epoch"] > repo_report["mtime_epoch"]:
                repo_report = m
    d = k_a1c(repo_report or {"exists": False}, live[CASES_PATH])
    add("A1c", 1, "F0/corpus", d["status"], d,
        [f"{CASES_PATH}#{live_cases_sha[:12]}"] + ([d["report"]] if d.get("report") else []),
        "no repo report binds the live corpus hash at an mtime not older than the corpus")

    for node, meta in SCHEMAS.items():
        bind = docs[node].get("f0_binding") or {}
        d = k_a2a(bind.get("consistency_evidence_sha256"), live_evidence_sha,
                  bind.get("declared_f0_sha256"), live_f0_sha)
        add(f"A2a-{node}", 2, node, d["status"], d,
            [f"{meta['path']}#{live[meta['path']]['sha256'][:12]}", f"{EVIDENCE}#{live_evidence_sha[:12]}"],
            "declared consistency-evidence pin differs from the measured canonical evidence hash",
            class_id=meta["class_id"])
    d = k_a2b(evidence_text, live_f0_sha, live_supp_sha)
    add("A2b", 2, "F0", d["status"], d, [f"{EVIDENCE}#{live_evidence_sha[:12]}"],
        "evidence document lacks input tree hashes equal to the live F0/supplement (residual CF-20)")
    d = k_a2c(mirror_bytes, (ROOT / EVIDENCE).read_bytes(), mirror_rc, mirror_log)
    add("A2c", 2, "F0", d["status"], d, [CONSISTENCY_TOOL, f"{EVIDENCE}#{live_evidence_sha[:12]}"],
        "isolated canonical-checker run does not reproduce the live evidence bytes")

    d = k_a3a_direction(f1)
    add("A3a", 3, "F1", d["status"], d,
        [f"{SCHEMAS['F1']['path']}#{live[SCHEMAS['F1']['path']]['sha256'][:12]}",
         "artifacts/worker-076/gform_strictness_reconcile/probe_result.json#ae1740ac0b15"],
        "F1 still asserts a worker-076-refuted strength direction", class_id="AF-WCC-VAC-GEN")
    d = k_a3d_falsifier(f1)
    add("A3d", 3, "F1", d["status"], d, [f"{SCHEMAS['F1']['path']}#{live[SCHEMAS['F1']['path']]['sha256'][:12]}"],
        "falsifier clause still states the refuted equivalence without the finiteness/maximum hypothesis",
        class_id="AF-WCC-VAC-GEN")
    d = k_a3b_true_strength(f1)
    add("A3b", 3, "F1", d["status"], d, [f"{SCHEMAS['F1']['path']}#{live[SCHEMAS['F1']['path']]['sha256'][:12]}"],
        "the true B-containment-strictly-stronger sentence was deleted instead of the false ones",
        class_id="AF-WCC-VAC-GEN")
    d = k_a3c_cross_artifact(registry, delta)
    add("A3c", 3, "F1", d["status"], d,
        ["artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a384a",
         "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
        "registry/delta keep the refuted 'strictly stronger' SET label after the F1 repair",
        class_id="AF-WCC-VAC-GEN")

    d = k_a4a(frozen)
    add("A4a", 4, NODE_ID, d["status"], d, [f"{FROZEN_PATH}#{live[FROZEN_PATH]['sha256'][:12]}"],
        "FROZEN revision is not >= 29")
    d = k_a4b(frozen, live_manifest)
    add("A4b", 4, NODE_ID, d["status"], d, [f"{FROZEN_PATH}#{live[FROZEN_PATH]['sha256'][:12]}"],
        "any manifest-listed hash differs from the measured live bytes")

    moved = []
    for node, meta in SCHEMAS.items():
        if baseline[node]["sha256_matches"] and baseline[node]["source"]["sha256"] != live[meta["path"]]["sha256"]:
            moved.append(meta["path"])
    if baseline["FROZEN"]["sha256_matches"] and baseline["FROZEN"]["source"]["sha256"] != live[FROZEN_PATH]["sha256"]:
        moved.append(FROZEN_PATH)
    moved = sorted(set(moved))
    moved_excl_frozen = [p for p in moved if p != FROZEN_PATH]

    d = k_a4c(frozen, moved_excl_frozen)
    add("A4c", 4, NODE_ID, d["status"], d, [f"{FROZEN_PATH}#{live[FROZEN_PATH]['sha256'][:12]}"],
        "a moved card artifact is absent from the rev29 manifest (FROZEN excluded as documented self-reference)")
    d = k_a4d(frozen, live_evidence_sha)
    add("A4d", 4, NODE_ID, d["status"], d,
        [f"{FROZEN_PATH}#{live[FROZEN_PATH]['sha256'][:12]}", f"{EVIDENCE}#{live_evidence_sha[:12]}"],
        "manifest evidence pin differs from the live evidence hash")
    d = k_a4e(moved_excl_frozen, live, events, outbox_events)
    add("A4e", 4, NODE_ID, d["status"], d, [EVENTS_PATH, "comms/outbox/"],
        "a moved path has no artifact event (accepted stream or emitted outbox) carrying its new sha256")
    d = k_a4g(live[FROZEN_PATH]["sha256"], events, outbox_events)
    add("A4g", 4, NODE_ID, d["status"], d, [EVENTS_PATH, FROZEN_PATH],
        "the rev29 manifest hash is not carried by any artifact event")
    before = {meta["path"]: {"sha256": baseline[node]["source"]["sha256"] if baseline[node]["sha256_matches"] else None}
              for node, meta in SCHEMAS.items()}
    d = k_a4f(moved_excl_frozen, before, live)
    add("A4f", 4, NODE_ID, d["status"], d, ["artifacts/formulation/"],
        "no machine report under artifacts/formulation names both the before and after sha256 of a moved card path")
    snap_f0 = SNAP / F0_PATH
    baseline_f0 = baseline["F0"]["source"]["sha256"] if baseline["F0"]["sha256_matches"] else (
        sha256_file(snap_f0) if snap_f0.exists() else live_f0_sha)
    d = k_a5a(live_f0_sha, baseline_f0)
    add("A5a", "falsifier", "F0", d["status"], d, [f"{F0_PATH}#{live_f0_sha[:12]}"],
        "the F0 canonical taxonomy bytes moved during the repair (card forbids any F0 write)")

    changes_by_node = {}
    for node, meta in SCHEMAS.items():
        if baseline[node]["doc"] is None:
            changes_by_node[node] = {"forbidden": [], "item3_prose": [], "other_scope": [],
                                     "allowed_metadata": [], "baseline_missing": True}
            continue
        changes_by_node[node] = classify_changes(changed_leaves(baseline[node]["doc"], docs[node]), node)
    d = k_a5b(changes_by_node)
    add("A5b", "falsifier", NODE_ID, d["status"], d,
        [f"{m['path']}#{live[m['path']]['sha256'][:12]}" for m in SCHEMAS.values()],
        "a class id, hypothesis, conclusion predicate or axis/genericity field changed vs the rev12 baseline")
    d = k_a5c({n: declared_class_ids(docs[n]) for n in SCHEMAS},
              {n: declared_class_ids(baseline[n]["doc"]) for n in SCHEMAS if baseline[n]["doc"]})
    add("A5c", "falsifier", NODE_ID, d["status"], d,
        [f"{m['path']}#{live[m['path']]['sha256'][:12]}" for m in SCHEMAS.values()],
        "the declared class-id set changed in any schema")

    # ---- baseline projection: the same kernels against the recovered rev12/rev28 bytes
    proj = []
    if baseline["F1"]["doc"]:
        b_doc = {"F1": baseline["F1"]["doc"], "F2a": baseline["F2a"]["doc"], "F2b": baseline["F2b"]["doc"]}
        b_ind = {"F1": baseline["F1"]["doc"].get("f0_binding") or {},
                 "F2a": baseline["F2a"]["doc"].get("f0_binding") or {},
                 "F2b": baseline["F2b"]["doc"].get("f0_binding") or {}}
        for n in SCHEMAS:
            proj.append({"check": f"A2a-{n}", "on_baseline": k_a2a(b_ind[n].get("consistency_evidence_sha256"),
                         live_evidence_sha, b_ind[n].get("declared_f0_sha256"), live_f0_sha)["status"],
                         "on_rev29": next(c["status"] for c in checks if c["id"] == f"A2a-{n}")})
        proj.append({"check": "A3a", "on_baseline": k_a3a_direction(b_doc["F1"])["status"],
                     "on_rev29": next(c["status"] for c in checks if c["id"] == "A3a")})
        proj.append({"check": "A3d", "on_baseline": k_a3d_falsifier(b_doc["F1"])["status"],
                     "on_rev29": next(c["status"] for c in checks if c["id"] == "A3d")})
        proj.append({"check": "A4a", "on_baseline": k_a4a(baseline["FROZEN"]["doc"])["status"],
                     "on_rev29": next(c["status"] for c in checks if c["id"] == "A4a")})
        proj.append({"check": "A5b", "on_baseline": "PASS (identity)",
                     "on_rev29": next(c["status"] for c in checks if c["id"] == "A5b")})
        proj.append({"check": "A5c", "on_baseline": "PASS (identity)",
                     "on_rev29": next(c["status"] for c in checks if c["id"] == "A5c")})
    discriminates = sorted({p["check"] for p in proj if p["on_baseline"] != p["on_rev29"]})

    advisory = []
    if re.search(r"C2 is a strictly larger extension class", read_text(SCHEMAS["F2b"]["path"])):
        advisory.append({
            "id": "S1", "severity": "hard", "node": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "finding": "line 245 forbidden_transfers[0].reason still asserts the inverted premise 'C2 is a strictly larger extension class' while line 238's own chain places E_C2 smallest; not covered by the four authorized repair items",
            "reporters": ["worker-066 W066-R12-F2B-H1", "worker-060 HF-060-CS-01", "worker-008 W008-CD CD-01"],
            "evidence_refs": [f"{SCHEMAS['F2b']['path']}#{live[SCHEMAS['F2b']['path']]['sha256'][:12]}",
                              f"{SCHEMAS['F2b']['path']}:245", f"{SCHEMAS['F2b']['path']}:238"],
            "falsifier": "the premise sentence is repaired or a controller disposition records it as non-blocking",
        })
    advisory.append({
        "id": "S2", "severity": "info", "node": "F1", "class_id": "AF-WCC-VAC-GEN",
        "finding": "A3d: rev13 keeps the equivalence falsifier and does not add worker-076's finiteness/dominating-member hypothesis; direction is now correct, so this is a wording residual for the r3 reviewer, not a defect",
        "reporters": ["worker-076 W076-GFORM-STRICTNESS-RECONCILE-06 (line 236 table)"],
        "evidence_refs": [f"{SCHEMAS['F1']['path']}#{live[SCHEMAS['F1']['path']]['sha256'][:12]}"],
        "falsifier": "show the retained falsifier is inconsistent with the corrected 'strictly WEAKER' relation",
    })
    a3c_status = next(c["status"] for c in checks if c["id"] == "A3c")
    if a3c_status == "FAIL":
        advisory.append({
            "id": "S3", "severity": "moderate", "node": "F1", "class_id": "AF-WCC-VAC-GEN",
            "finding": "A3c: VARIANT_REGISTRY variants[SET].strength and/or the variant-SET delta still carry the refuted 'strictly stronger' leading label; neither path is in the card artifact list, so rev29 can freeze with F1 and the variant registry contradicting each other",
            "reporters": ["worker-076 W076-GFORM-VIS-STRENGTH-03 blocker"],
            "evidence_refs": ["artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a384a",
                              "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
            "falsifier": "both labels corrected or a controller ruling keeps them with a rationale",
        })
    else:
        advisory.append({
            "id": "S3", "severity": "info", "node": "F1", "class_id": "AF-WCC-VAC-GEN",
            "finding": "A3c: registry and delta SET strength labels are now 'strictly weaker' and the surviving 'strictly STRONGER' occurrence is a bracketed historical mention ('corrected from'); mention-aware leading-label check passes",
            "reporters": ["worker-076 W076-GFORM-VIS-STRENGTH-03 blocker"],
            "evidence_refs": ["artifacts/formulation/VARIANT_REGISTRY.json",
                              "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
            "falsifier": "the leading label reverts to 'strictly stronger' in either artifact",
        })
    advisory.append({
        "id": "S4", "severity": "moderate", "node": "F0", "class_id": "ALL",
        "finding": "A2b: the item-2 refresh closes the hash mismatch but not the input-anchoring gap; the live evidence document records input paths only, so the r3 'refreshed consistency-evidence binding' check cannot verify which F0/supplement bytes were compared",
        "reporters": ["CF-20", "worker-047 CB-2", "worker-078 W078-F2-F0BIND-ADJ-01"],
        "evidence_refs": [f"{EVIDENCE}#{live_evidence_sha[:12]}"],
        "falsifier": "evidence regenerated with map_taxonomy_sha256/lead_contract_sha256 anchors (new hash) or a disposition",
    })
    if not any(c["id"] == "A4e" and c["status"] == "PASS" for c in checks):
        advisory.append({
            "id": "S5", "severity": "moderate", "node": NODE_ID, "class_id": "ALL",
            "finding": "A4e/A4g: publication events for the moved rev13 paths are not yet in the accepted stream (pending ingest or not emitted at measurement time); PROTOCOL rule 2 needs them before a done/gate transition",
            "reporters": ["controller REC-12 item 4"],
            "evidence_refs": [EVENTS_PATH, "comms/outbox/"],
            "falsifier": "artifact events carrying the rev13/rev29 sha256 appear in the accepted stream",
        })

    end = {rel: measure(rel) for rel in SNAPSHOT_PATHS}
    drift = sorted(rel for rel in end if end[rel].get("sha256") != live[rel].get("sha256"))

    def item_status(item):
        st = [c["status"] for c in checks if c["card_item"] == item]
        if "FAIL" in st:
            return "FAIL"
        if "UNMEASURED" in st:
            return "UNMEASURED"
        if "WARN" in st:
            return "WARN"
        return "PASS"

    items = {str(i): item_status(i) for i in (1, 2, 3, 4)}
    items["falsifier"] = item_status("falsifier")
    counts = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    forbidden_present = any(v.get("forbidden") for v in changes_by_node.values())
    card_met = all(items[str(i)] in ("PASS", "WARN") for i in (1, 2, 3, 4)) and items["falsifier"] == "PASS" and not forbidden_present
    clean = all(items[str(i)] == "PASS" for i in (1, 2, 3, 4)) and items["falsifier"] == "PASS"
    verdict = "CARD_ITEMS_MET_AT_REV29" if card_met else "CARD_ITEMS_UNMET_AT_REV29"

    report = {
        "report_version": "1.0", "task_id": TASK_ID, "actor": ACTOR,
        "created_at": started.isoformat(timespec="seconds"),
        "node_id": NODE_ID, "gate": GATE, "class_ids": CLASS_IDS,
        "card": "astra-life05-evidence-binding-repair (Astra pass-05 REC-12)",
        "binding": {
            "state": "DRIFTED" if drift else "PINNED", "drift": drift,
            "snapshot": snap_info,
            "measured_pins": {n: live[m["path"]]["sha256"] for n, m in SCHEMAS.items()},
            "frozen_revision": frozen.get("revision"),
            "frozen_sha256": live[FROZEN_PATH]["sha256"],
            "f0_sha256": live_f0_sha, "evidence_sha256": live_evidence_sha,
            "cases_sha256": live_cases_sha,
            "check_definitions_authored_from": [
                "map.assignments['astra-life05-evidence-binding-repair'] (pass-05 REC-12)",
                "artifacts/worker-076/gform_strictness_reconcile/probe_result.json#ae1740ac0b15",
            ],
            "pre_registration_caveat": "the repair landed 00:53:20-00:55:02 while this instrument was being written; the rev29 measurement is retrospective for items 1/2/4, and the baseline projection shows what the same kernels report on the recovered rev12/rev28 bytes",
        },
        "baseline_recovery": {n: {"source": baseline[n]["source"], "exists": baseline[n]["exists"],
                                  "sha256_matches": baseline[n]["sha256_matches"]} for n in ("F1", "F2a", "F2b", "FROZEN", "F0")},
        "baseline_projection": {"rows": proj, "checks_that_discriminate": discriminates},
        "measured_live": live,
        "checks": checks, "card_items_status": items, "status_counts": counts,
        "verdict": verdict, "card_items_met": card_met, "card_items_met_clean": clean,
        "advisory_findings": advisory,
        "non_claims": [
            "no gate verdict, no node status, no validation_status=passed",
            "no canonical or shared file was written by this harness; only artifacts/worker-078/rec12_preaccept/ and temp dirs",
            "truth, mathematics, non-vacuity and citation scope are outside this instrument",
            "the item-3 direction facts are worker-076's machine-checked table; A3a/A3b encode them rather than re-derive them",
        ],
    }
    return report, checks


# ------------------------------------------------------------------------------- controls
def run_controls() -> dict:
    baseline = load_baselines()
    f1 = baseline["F1"]["doc"]
    f2b = baseline["F2b"]["doc"]
    evidence_text = read_text(EVIDENCE)
    evidence_sha = sha256_bytes(evidence_text.encode())
    f0_sha = sha256_file(ROOT / F0_PATH)
    supp_sha = sha256_file(ROOT / SUPPLEMENT)
    cases_text = read_text(CASES_PATH)
    registry = json.loads(read_text("artifacts/formulation/VARIANT_REGISTRY.json"))
    delta = json.loads(read_text("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"))
    ctl = []

    def ck(cid, seeded, check, expected, status):
        ctl.append({"id": cid, "seeded": seeded, "check": check, "expected": expected,
                    "observed": status, "ok": status == expected})

    ck("C1", "wrong evidence pin", "A2a", "FAIL", k_a2a("deadbeef" * 8, evidence_sha, BOUND_F0, f0_sha)["status"])
    stripped = json.dumps({k: v for k, v in json.loads(evidence_text).items()
                           if k not in ("map_taxonomy_sha256", "lead_contract_sha256")})
    ck("C2", "un-anchored evidence", "A2b", "WARN", k_a2b(stripped, f0_sha, supp_sha)["status"])
    anchored = json.dumps({**json.loads(evidence_text), "map_taxonomy_sha256": f0_sha, "lead_contract_sha256": supp_sha})
    ck("C2b", "anchored evidence (positive)", "A2b", "PASS", k_a2b(anchored, f0_sha, supp_sha)["status"])
    ck("C3", "F0 canonical write", "A5a", "FAIL", k_a5a("f" * 64, f0_sha)["status"])
    mutated = json.loads(json.dumps(f1))
    mutated["class_id"] = "AF-WCC-VAC-GEN-MUT"
    ck("C4", "class-id mutation", "A5b", "FAIL", k_a5b({"F1": classify_changes(changed_leaves(f1, mutated), "F1")})["status"])
    ck("C4b", "class-id mutation", "A5c", "FAIL",
       k_a5c({"F1": declared_class_ids(mutated)}, {"F1": declared_class_ids(f1)})["status"])
    mutated = json.loads(json.dumps(f2b))
    mutated.setdefault("conclusion", {})["conclusion_type"] = "weak_cosmic_censorship"
    ck("C5", "conclusion-predicate mutation", "A5b", "FAIL",
       k_a5b({"F2b": classify_changes(changed_leaves(f2b, mutated), "F2b")})["status"])
    bad = json.loads(json.dumps(baseline["FROZEN"]["doc"]))
    bad["revision"] = 29
    bad["files"][SCHEMAS["F1"]["path"]] = {"sha256": "0" * 64}
    live_manifest = {}
    for p in set((bad.get("files") or {})) | set((bad.get("logical_artifacts") or {})):
        fp = ROOT / p
        if fp.exists():
            live_manifest[p] = {"sha256": sha256_file(fp)}
    ck("C6", "rev29 with one wrong pin", "A4b", "FAIL", k_a4b(bad, live_manifest)["status"])
    ck("C7", "rev12 F1 direction (baseline)", "A3a", "FAIL", k_a3a_direction(f1)["status"])
    fixed = json.loads(json.dumps(f1))
    fixed["quantifiers"]["domains"]["D5"]["definition"] = (
        "pairs (q,t0) with the tail in J^-(q); whole-curve containment is EQUIVALENT for causal gamma.")
    fixed["visibility"]["definition"] = "visible iff some tail lies in J^-(q) for one q in I+."
    fixed["class_identity_variants"][0]["relation"] = (
        "strictly WEAKER than this class's single-q tail predicate: tail containment entails the union reading.")
    ck("C7b", "direction-corrected F1 (positive)", "A3a", "PASS", k_a3a_direction(fixed)["status"])
    ck("C8", "stale corpus row binding", "A1a", "FAIL",
       k_a1a("\n".join(json.dumps({**r, "binding_status": "bound_taxonomy_sha_" + (SUPERSEDED_F0 if i == 1 else CASES_BINDING_TOKEN.replace("bound_taxonomy_sha_", ""))})
                       for i, r in enumerate(parse_jsonl(cases_text))) + "\n", f0_sha, BOUND_F0)["status"])
    inverted_reg = json.loads(json.dumps(registry))
    next(v for v in inverted_reg["variants"] if v.get("variant_id") == "SET")["strength"] = \
        "strictly STRONGER than AF-WCC-VAC-GEN: (seeded control)"
    inverted_delta = {"strength": "strictly stronger than AF-WCC-VAC-GEN (seeded control)"}
    ck("C9", "seeded inverted registry/delta labels", "A3c", "FAIL",
       k_a3c_cross_artifact(inverted_reg, inverted_delta)["status"])
    ck("C9b", "live corrected labels with historical mention (positive)", "A3c", "PASS",
       k_a3c_cross_artifact(registry, delta)["status"])
    ck("C10", "superseded FROZEN revision", "A4a", "FAIL", k_a4a(baseline["FROZEN"]["doc"])["status"])
    ck("C11", "moved path without event", "A4e", "FAIL",
       k_a4e(["schemas/af_wcc_vacuum.yaml"], {SCHEMAS["F1"]["path"]: {"sha256": "a" * 64}}, [], [])["status"])
    return {"controls_ok": all(c["ok"] for c in ctl), "n": len(ctl), "items": ctl,
            "note": "positive controls C2b/C7b prove the kernels clear on corrected input"}


# ---------------------------------------------------------------------------------- main
def normalize(report: dict) -> dict:
    r = json.loads(json.dumps(report))
    r.pop("created_at", None)
    r.pop("measured_live", None)
    (r.get("binding") or {}).pop("drift", None)
    rc = r.get("baseline_projection")
    if isinstance(rc, dict):
        pass
    for c in r.get("checks", []):
        d = c.get("detail") or {}
        if c["id"] in ("A4e", "A4f", "A4g"):
            d.pop("paths_emitted_pending_ingest", None)
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    baseline = load_baselines()
    if not baseline["F1"]["sha256_matches"] or baseline["F1"]["doc"] is None:
        print("WARNING: rev12 baseline copies unavailable; baseline projection degraded", file=sys.stderr)

    if a.snapshot or not SNAP.exists():
        snap_info = write_snapshot()
    else:
        snap_info = {"files": len([p for p in SNAP.rglob("*") if p.is_file()]),
                     "sha256sums": sha256_file(SNAP / "SHA256SUMS.txt")}

    report, checks = run_once(snap_info, baseline)
    report2, _ = run_once(snap_info, baseline)
    det = normalize(report) == normalize(report2)
    report["deterministic_test_retest"] = det
    report["normalized_sha256"] = sha256_bytes(json.dumps(normalize(report), sort_keys=True).encode())
    report2["deterministic_test_retest"] = det
    report2["normalized_sha256"] = report["normalized_sha256"]

    controls = run_controls()
    report["controls"] = {"controls_ok": controls["controls_ok"], "n": controls["n"]}
    report2["controls"] = report["controls"]

    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "report_rerun.json").write_text(json.dumps(report2, indent=2, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps(controls, indent=2, sort_keys=True) + "\n")

    print(f"{TASK_ID}: verdict={report['verdict']} items={report['card_items_status']} "
          f"counts={report['status_counts']} deterministic={det} controls_ok={controls['controls_ok']}")
    print(f"  baseline projection discriminating checks: {report['baseline_projection']['checks_that_discriminate']}")
    for c in checks:
        if c["status"] != "PASS":
            msg = c["detail"].get("failures") or c["detail"].get("note") or c["detail"].get("adjudication") or ""
            print(f"  {c['status']:12s} {c['id']:8s} {c['node']:10s} {str(msg)[:120]}")
    return 0 if controls["controls_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
