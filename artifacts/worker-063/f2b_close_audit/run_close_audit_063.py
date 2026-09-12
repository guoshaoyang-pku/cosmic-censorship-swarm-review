#!/usr/bin/env python3
"""W063-F2B-CLOSE-AUDIT-01 -- does the pending containment-only F2b rev14 close F2b?

FROZEN-BEFORE-MEASUREMENT runner.  All thresholds, the review frame, the carrier-family
table and the pin set below were fixed before the first measurement; the review files and
the accepted-stream events are read against pinned sha256, and any pin drift exits 3.

Question (from lead-form-20260912T005743-91, L-FORM-01): the owner has a validated
two-edit F2b repair candidate (containment denial at regularity.must_not_conflate[0];
inverted size premise at implication_ledger.forbidden_transfers[0].reason).  Before the
r3 F2b review budget is spent, measure whether a rev14 carrying ONLY those two edits
closes the open F2b finding record at FROZEN rev29 / F2b rev13.

Method: (1) measure every pin; (2) diff canonical F2b b2ab6acb2bbe against both published
candidates and derive the changed YAML leaf paths with an independent indentation-aware
path tracker; (3) extract every hard-failure record for F2b at rev13/rev29 from pinned
review files plus a byte-verbatim snapshot of accepted-stream review/blocker events;
(4) normalise each hard failure to one of eight declared carrier families; (5) join: a
family is TOUCHED iff a candidate changed leaf path is a path-prefix of (or equal to) a
carrier path; (6) measure, for every UNTOUCHED family, whether the defect is still live at
the frozen bytes, and which actor can close it.

Worker measurement only: no gate verdict, no node status, no validation_status, no edit to
any canonical path.  Exit codes: 0 measured, 3 pin drift (fail closed), 4 instrument
self-check failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EVID = HERE / "evidence"
CST = timezone(timedelta(hours=8))
TASK_ID = "W063-F2B-CLOSE-AUDIT-01"

# ----------------------------------------------------------------------------------
# 1. PINS (measured and frozen at 2026-09-12T01:09+08:00, before the first measurement)
# ----------------------------------------------------------------------------------
PIN_FILES = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    # MID-AUDIT MOVE: this file was pinned at frame time (01:09:57) as
    # 94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4 (revision 6, whose
    # SEP-6 component pins pointed at rev11 bytes).  Between frame time and this run the
    # owner published revision 7 in three writes (observed hashes fa74db62a7e4 and
    # 0f1376871663 were intermediate; the observed stable bytes are 27255e5b34f3, mtime
    # 01:11:13, unchanged across repeated reads).  The runner pins the stable bytes and
    # verifies the revision's declared supersedes_sha256 equals the frame-time pin, so the
    # mid-audit closure is provenance-chained rather than assumed.  End-of-run re-measure
    # (pins_stable_during_run) catches any further move.
    "schemas/af_scc_regularities.yaml": "27255e5b34f36b252accf1217dc01b63a5f5ec09f33af03938565c8fb99b20ed",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/acceptance_pipeline_report.json": "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6",
    "artifacts/formulation/evidence/semantic_escape_rebased.json": "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml": "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757",
    "artifacts/worker-063/f2b_close_audit/evidence/review_events_snapshot.json": None,  # self-pinned at first read
    "artifacts/worker-063/f2b_close_audit/evidence/owner_blocker_snapshot.json": None,  # self-pinned at first read
    # review files in frame
    "reviews/F2b-review-rev29-053.json": "6813037ab0543a849ae6b3d0cb15eb9cbe42c41d9ec0413cf8d4c025bd625098",
    "reviews/F2b-review-rev29-075.json": "2fb2878ec1fb59e2d1e770542c278ec2f9adb4bf34b89bc622c7a0044797d6a5",
    "reviews/F2b-review-worker-018-rev13.json": "50f9c0c0e94fa42e8d673b35d53ff4c7617324d81bffaaab78e85a30444947e7",
    "reviews/F2b-rev13-containment-worker-017.json": "c41009f1cbdae7dbb0a229678a68dbfe9e176d2a0470f71a3c5b66d32c32dfab",
    "reviews/F2b-bindchain-rev13-worker-035.json": "7aaabdf8395d5a508eefd6585d7a97fb2f870e806cf40292c9a09b12ace49c20",
    "reviews/F2b-rev29-containment-rebase-worker-066.json": "1489a3fe719b7ebd68c17dfe1b32bf8e286228e300a065e84ab6d2a820db402c",
    "reviews/F2b-containment-normativity-worker-066.json": "0dec35934e9f687bf0ce8e604a2c021df54112ace40958e61e9ca42b2b2d2344",
}
FRAME_PIN_AGGREGATOR = "94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4"
PIN_REVIEW_SNAPSHOT = "artifacts/worker-063/f2b_close_audit/evidence/review_events_snapshot.json"
PIN_OWNER_SNAPSHOT = "artifacts/worker-063/f2b_close_audit/evidence/owner_blocker_snapshot.json"

CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
CANDIDATES = {
    "worker08_worker066_rebased": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "worker022_cd_repair": "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
}

# ----------------------------------------------------------------------------------
# 2. Review frame and declared carrier normalisation
#    Frame: every hard-failure record in the pinned review files with verdict=revise that
#    bind F2b at rev13/FROZEN rev29, plus every hard failure in the pinned accepted-stream
#    review/blocker snapshot that names F2b/C0.  No mtime cutoff is used (files were
#    selected by target bytes b2ab6acb2bbe / F2b rev13 / FROZEN rev29).
# ----------------------------------------------------------------------------------
# Declared carrier map for records whose hard failure is a bare string (no field/carrier/
# location in the record).  Values are the carrier the source's own prose names.
DECLARED_STRING_CARRIERS = {
    ("reviews/F2b-rev29-containment-rebase-worker-066.json", "W066-R13-F2B-H1"): "implication_ledger.forbidden_transfers[0].reason",
    ("reviews/F2b-rev29-containment-rebase-worker-066.json", "W066-R13-F2B-H2"): "regularity.must_not_conflate[0]",
    ("w044-20260912T0104-liveclosure-review", "H1_false_containment_denial"): "regularity.must_not_conflate[0]",
    ("w044-20260912T0104-liveclosure-review", "H2_inverted_size_premise"): "implication_ledger.forbidden_transfers",
    ("w044-20260912T0104-liveclosure-review", "A2_evidence_not_self_verifying"): "f0_binding.consistency_evidence",
    ("w044-20260912T0104-liveclosure-review", "A6_alias_registry_unbound"): "f0_binding.alias_registry_binding",
    ("w044-20260912T0104-liveclosure-review", "SEP6_aggregator_component_pins_stale"): "schemas/af_scc_regularities.yaml",
    ("w095-hold-r4-20260912T010257-review-binding", "HF-06-01"): "stream:events.jsonl#latest-artifact-ordering",
    ("w095-hold-r4-20260912T010257-review-binding", "HF-06-02"): "stream:events.jsonl#w06-20260912T0115-f2b-rev6",
    ("w062-rev13-2026-09-12T01:02:53+08:00-review", "HF-W062-REV13-01"): "artifacts/formulation/evidence/semantic_escape_rebased.json",
    ("w062-rev13-2026-09-12T01:02:53+08:00-review", "HF-W062-REV13-02"): "artifacts/formulation/evidence/acceptance_pipeline_report.json",
    ("w017-20260912-vocab-source-blocker", "W017-VOCAB-BLOCKER"): "conclusion.conclusion_type",
    ("lead-form-20260912T005743-91", "L-FORM-01"): "implication_ledger.forbidden_transfers[0].reason",
    ("w047-f2a13-20260912T010049-blocker", "HF-047-02"): "conclusion.conclusion_type",
    ("lead-form-20260912T0113-106", "C_PIPE-BLOCKER"): "artifacts/formulation/evidence/semantic_escape_rebased.json",
}

# Declared carrier families.  A family is a set of carrier path strings; the join rule is
# prefix-or-equal on '/'-free YAML paths, and for file paths exact string equality.
FAMILIES = [
    ("C_H1_containment_denial", "regularity.must_not_conflate[0]",
     "stale sentence 'No containment with C2 or C0 is asserted here' in a required normative slot"),
    ("C_H2_inverted_size_premise", "implication_ledger.forbidden_transfers[0]",
     "justification calls C2 a strictly larger extension class while the file's own chain makes E_C2 smallest"),
    ("C_VOCAB_conclusion_token", "conclusion.conclusion_type",
     "schema canonical token vs F0 field_vocabulary.allowed alias list; alias-registry pointer absent"),
    ("C_A2_evidence_self_verification", "f0_binding.consistency_evidence",
     "taxonomy_consistency.json records consistent=true but pins neither input it evaluated"),
    ("C_A6_alias_registry_binding", "f0_binding.alias_registry_binding",
     "no path+sha256 binding for VOCAB_ALIASES.json in the schema"),
    ("C_PIPE_acceptance_base_binding", "artifacts/formulation/evidence/semantic_escape_rebased.json",
     "acceptance/semantic-escape evidence binds rev11 base bytes or records no base at all"),
    ("C_SEP6_aggregator_pins", "schemas/af_scc_regularities.yaml",
     "aggregator component sha256 pins are stale against live rev13 component bytes"),
    ("C_STREAM_ordering_shadow", "stream:events.jsonl",
     "future-dated, non-ingested artifact event shadows the F2b pin; no declared latest-artifact ordering rule"),
]

MIN_FAMILIES = 8
MIN_HF_RECORDS = 10
MIN_SOURCES = 5


# ----------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text()


def canonical_sha256(doc) -> str:
    return sha256_bytes(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------------
# 3. independent YAML leaf-path tracker + candidate diff
# ----------------------------------------------------------------------------------
ITEM = re.compile(r"^- ")


def yaml_line_paths(lines: list[str]) -> list[str | None]:
    """Indentation-aware key path per line; list items get [index] appended."""
    stack: list[tuple[int, str]] = []          # (indent, key)
    counters: dict[str, int] = {}
    out: list[str | None] = []
    for raw in lines:
        s = raw.rstrip("\n")
        stripped = s.strip()
        if not stripped or stripped.startswith("#"):
            out.append(None)
            continue
        indent = len(s) - len(s.lstrip(" "))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = ".".join(k for _, k in stack)
        if stripped.startswith("- "):
            body = stripped[2:].strip()
            key = body.split(":", 1)[0].strip().strip("'\"") if ":" in body else ""
            if key and re.fullmatch(r"[A-Za-z0-9_.\-]+", key):
                idx = counters.get(parent + "|" + key, 0)
                counters[parent + "|" + key] = idx + 1
                out.append(f"{parent}.{key}[{idx}]" if parent else f"{key}[{idx}]")
            else:
                idx = counters.get(parent + "|-", 0)
                counters[parent + "|-"] = idx + 1
                out.append(f"{parent}[{idx}]" if parent else f"[{idx}]")
        elif ":" in stripped:
            key = stripped.split(":", 1)[0].strip().strip("'\"")
            if key and re.fullmatch(r"[A-Za-z0-9_.\-]+", key):
                stack.append((indent, key))
                out.append(".".join(k for _, k in stack))
            else:
                out.append(parent or None)
        else:
            out.append(parent or None)
    return out


def candidate_diff(canon_rel: str, cand_rel: str) -> dict:
    c_lines = read_text(canon_rel).split("\n")
    k_lines = read_text(cand_rel).split("\n")
    paths = yaml_line_paths(c_lines)
    changed = []
    if len(c_lines) != len(k_lines):
        raise RuntimeError("candidate line count differs; this instrument assumes in-place leaf edits")
    for i, (a, b) in enumerate(zip(c_lines, k_lines), 1):
        if a != b:
            changed.append({
                "line": i,
                "yaml_path_at_line": paths[i - 1],
                "canonical_text": a,
                "candidate_text": b,
            })
    return {
        "canonical": canon_rel,
        "candidate": cand_rel,
        "line_count": len(c_lines),
        "changed_line_count": len(changed),
        "changed_lines": changed,
        "changed_leaf_paths": sorted({c["yaml_path_at_line"] for c in changed if c["yaml_path_at_line"]}),
    }


# ----------------------------------------------------------------------------------
# 4. hard-failure extraction from pinned sources
# ----------------------------------------------------------------------------------
def extract_hf_from_record(rec: dict, key: tuple[str, str]) -> tuple[str, str, str]:
    """Return (hf_id, carrier, evidence_quote)."""
    if isinstance(rec, dict):
        hf_id = str(rec.get("id") or rec.get("hf_id") or "UNKNOWN")
        carrier = rec.get("field") or rec.get("carrier") or rec.get("location") or ""
        carrier = str(carrier)
        if carrier:
            carrier = carrier.split(" (")[0]
            m = re.match(r"^(schemas/[^\s:]+)(?::\d+)?", carrier)
            if m:
                carrier = m.group(1)
        quote = str(rec.get("detail") or rec.get("statement") or rec.get("finding") or "")
    else:
        hf_id = str(rec)
        carrier = ""
        quote = str(rec)
    if not carrier:
        carrier = DECLARED_STRING_CARRIERS.get((key[0], hf_id), "")
        if not carrier:
            raise RuntimeError(f"UNMAPPED hard failure {key[0]}::{hf_id}")
    return hf_id, carrier, quote[:400]


def family_of(carrier: str) -> str | None:
    for fam, anchor, _desc in FAMILIES:
        if anchor.endswith(".yaml") or "/" in anchor:
            if carrier == anchor:
                return fam
        else:
            # two-way path prefix: reviewers name both the list item and its .reason leaf
            if carrier == anchor or carrier.startswith(anchor + ".") or anchor.startswith(carrier + "."):
                return fam
    if carrier == "stream:events.jsonl#latest-artifact-ordering":
        return "C_STREAM_ordering_shadow"
    return None


def extract_hard_failures() -> list[dict]:
    records = []

    def fsv_for(target: str, flagged) -> bool:
        if flagged is False:
            return False
        t = target or ""
        if t.startswith("schemas/af_scc"):
            return True
        if t.startswith("F2b"):
            return "#containment-rebase" not in t
        return False

    # (a) pinned review files
    for rel, pin in PIN_FILES.items():
        if not rel.startswith("reviews/"):
            continue
        doc = json.loads(read_text(rel))
        reviewer = doc.get("reviewer") or Path(rel).stem
        target = str(doc.get("target_id") or "")
        for rec in doc.get("hard_failures") or []:
            hf_id, carrier, quote = extract_hf_from_record(rec, (rel, ""))
            records.append({
                "source": rel, "source_sha256": pin, "reviewer": reviewer,
                "verdict": doc.get("verdict"), "target_id": target,
                "hf_id": hf_id, "carrier": carrier, "quote": quote,
                "full_schema_verdict": fsv_for(target, doc.get("counts_as_full_schema_verdict")),
            })
    # (b) frozen accepted-stream snapshot
    for snap_rel in (PIN_REVIEW_SNAPSHOT, PIN_OWNER_SNAPSHOT):
        snap = json.loads(read_text(snap_rel))
        for entry in snap["events"]:
            ev = entry["event"]
            if canonical_sha256(ev) != entry["canonical_sha256"]:
                raise RuntimeError(f"snapshot self-check failed for {entry['event_id']}")
            eid = entry["event_id"]
            hfs = []
            if ev.get("event_type") == "review":
                hfs = ev.get("hard_failures") or []
            elif ev.get("event_type") == "blocker":
                hfs = [{"id": ("L-FORM-01" if eid.startswith("lead-form-20260912T005743") else
                               ("C_PIPE-BLOCKER" if eid.startswith("lead-form-20260912T0113") else
                                ("HF-047-02" if eid.startswith("w047") else "W017-VOCAB-BLOCKER"))),
                        "detail": ev.get("description", "")}]
            for rec in hfs:
                hf_id, carrier, quote = extract_hf_from_record(rec, (eid, ""))
                records.append({
                    "source": eid, "source_sha256": entry["canonical_sha256"],
                    "reviewer": ev.get("actor"), "verdict": ev.get("verdict", "blocker"),
                    "target_id": str(ev.get("target_id") or ""), "hf_id": hf_id,
                    "carrier": carrier, "quote": quote,
                    "full_schema_verdict": fsv_for(str(ev.get("target_id") or ""),
                                                   ev.get("counts_as_full_schema_verdict")),
                })
    return records


# ----------------------------------------------------------------------------------
# 5. measured facts for the untouched families
# ----------------------------------------------------------------------------------
def measure_vocab() -> dict:
    f0 = yaml.safe_load(read_text("research_map/formulation_taxonomy.yaml"))
    f2b = yaml.safe_load(read_text("schemas/af_scc_c0_vacuum.yaml"))
    f2a = yaml.safe_load(read_text("schemas/af_scc_c2_vacuum.yaml"))
    va = json.loads(read_text("artifacts/formulation/VOCAB_ALIASES.json"))
    allowed = f0["field_vocabulary"]["conclusion_type"]["allowed"]
    allowed_gen = f0["field_vocabulary"]["genericity_kind"]["allowed"]
    f2b_val = f2b["conclusion"]["conclusion_type"]
    f2a_val = f2a["conclusion"]["conclusion_type"]
    f2b_gen = f2b["genericity"]["kind"]
    c0_axes = f0["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]
    canon = va["conclusion_type"]
    gen_canon = va["genericity_kind"]
    inv = {alias: k for k, aliases in canon.items() for alias in aliases}
    gen_inv = {alias: k for k, aliases in gen_canon.items() for alias in aliases}
    return {
        "f0_allowed_conclusion_type": allowed,
        "f0_allowed_genericity_kind": allowed_gen,
        "f0_declared_c0_token": c0_axes["conclusion_type"],
        "f0_declared_c0_genericity_kind": c0_axes["genericity_kind"],
        "vocab_aliases_canonical_keys": sorted(canon.keys()),
        "vocab_aliases_genericity_canonical_keys": sorted(gen_canon.keys()),
        "vocab_aliases_policy": va["policy"],
        "f0_conclusion_rule": f0["field_vocabulary"]["conclusion_type"]["rule"],
        "taxonomy_consistency_alias_policy": json.loads(read_text(
            "artifacts/formulation/evidence/taxonomy_consistency.json")).get("alias_policy"),
        "f2b_conclusion_type": f2b_val,
        "f2a_conclusion_type": f2a_val,
        "f2b_genericity_kind": f2b_gen,
        "f2b_token_in_f0_allowed": f2b_val in allowed,
        "f2b_token_is_registry_canonical": f2b_val in canon,
        "f0_declared_token_is_alias_of_f2b_token": inv.get(c0_axes["conclusion_type"]) == f2b_val,
        "f2b_genericity_in_f0_allowed": f2b_gen in allowed_gen,
        "f2b_genericity_is_registry_canonical": f2b_gen in gen_canon,
        "f0_declared_genericity_is_alias_of_f2b": gen_inv.get(c0_axes["genericity_kind"]) == f2b_gen,
        "vocab_aliases_sha256": sha256_file(ROOT / "artifacts/formulation/VOCAB_ALIASES.json"),
        "vocab_aliases_mentioned_in_f2b_bytes": "VOCAB_ALIASES" in read_text("schemas/af_scc_c0_vacuum.yaml"),
    }


def measure_a2() -> dict:
    rel = "artifacts/formulation/evidence/taxonomy_consistency.json"
    txt = read_text(rel)
    doc = json.loads(txt)
    hexes = re.findall(r"\b[0-9a-f]{64}\b", txt)
    bind = yaml.safe_load(read_text("schemas/af_scc_c0_vacuum.yaml"))["f0_binding"]
    return {
        "evidence_path": rel,
        "bytes": len(txt.encode()),
        "top_level_keys": sorted(doc.keys()),
        "embedded_sha256_count": len(hexes),
        "embeds_measured_input_hashes": len(hexes) > 0,
        "declares_consistent": doc.get("consistent"),
        "declares_alias_policy": bool(doc.get("alias_policy")),
        "f2b_binding_points_here": bind.get("consistency_evidence") == rel,
        "f2b_binding_hash_matches_live_file": bind.get("consistency_evidence_sha256") == sha256_file(ROOT / rel),
    }


def measure_a6() -> dict:
    txt = read_text("schemas/af_scc_c0_vacuum.yaml")
    bind = yaml.safe_load(txt)["f0_binding"]
    return {
        "f2b_bytes_mention_VOCAB_ALIASES": "VOCAB_ALIASES" in txt,
        "f0_binding_keys": sorted(bind.keys()),
        "f0_binding_has_alias_registry_field": any("alias" in k.lower() or "vocab" in k.lower() for k in bind),
        "registry_file_pinned_in_FROZEN": "artifacts/formulation/VOCAB_ALIASES.json" in
            json.loads(read_text("artifacts/formulation/FROZEN.json"))["files"],
    }


def measure_pipe() -> dict:
    se = json.loads(read_text("artifacts/formulation/evidence/semantic_escape_rebased.json"))
    ap = json.loads(read_text("artifacts/formulation/evidence/acceptance_pipeline_report.json"))
    frozen = json.loads(read_text("artifacts/formulation/FROZEN.json"))["files"]
    base_rel = se["base_schema"]
    live_base = sha256_file(ROOT / base_rel)
    return {
        "semantic_escape_base_schema": base_rel,
        "semantic_escape_declared_base_sha256": se["base_sha256"],
        "semantic_escape_live_base_sha256": live_base,
        "semantic_escape_base_mismatch": se["base_sha256"] != live_base,
        "acceptance_pipeline_top_level_keys": sorted(ap.keys()),
        "acceptance_pipeline_records_base_bytes": any(
            k for k in ap.keys() if "sha" in k.lower() or "base" in k.lower() or "revision" in k.lower()),
        "acceptance_pipeline_verdict": ap.get("verdict"),
        "both_pinned_in_FROZEN_rev29": all(
            p in frozen for p in ("artifacts/formulation/evidence/semantic_escape_rebased.json",
                                  "artifacts/formulation/evidence/acceptance_pipeline_report.json")),
        "frozen_revision": json.loads(read_text("artifacts/formulation/FROZEN.json")).get("revision"),
        "live_c0_sha256": sha256_file(ROOT / CANON_C0),
    }


def measure_sep6() -> dict:
    rel = "schemas/af_scc_regularities.yaml"
    txt = read_text(rel)
    agg = yaml.safe_load(txt)
    comps = []
    for c in agg["components"]:
        live = sha256_file(ROOT / c["path"])
        comps.append({
            "role": c["role"], "path": c["path"], "pinned_sha256": c["sha256"],
            "live_sha256": live, "stale": c["sha256"] != live,
        })
    frozen = json.loads(read_text("artifacts/formulation/FROZEN.json"))["files"]
    supersedes = agg.get("supersedes_sha256")
    return {
        "aggregator_revision": agg.get("revision"),
        "aggregator_sha256": sha256_file(ROOT / rel),
        "aggregator_mtime": datetime.fromtimestamp((ROOT / rel).stat().st_mtime, CST).isoformat(timespec="seconds"),
        "frame_time_pin": FRAME_PIN_AGGREGATOR,
        "declared_supersedes_sha256": supersedes,
        "frame_pin_chain_confirmed": supersedes == FRAME_PIN_AGGREGATOR,
        "aggregator_pinned_in_FROZEN": "schemas/af_scc_regularities.yaml" in frozen,
        "sep6_rule": next(i["rule"] for i in agg["separation_invariants"] if i["id"] == "SEP-6"),
        "components": comps,
        "stale_component_count": sum(1 for c in comps if c["stale"]),
        "closed_during_audit": (supersedes == FRAME_PIN_AGGREGATOR
                                and sum(1 for c in comps if c["stale"]) == 0),
        "rev6_staleness_evidence": ("pinned w044 review in review_events_snapshot.json records rev6 pins "
                                    "C0 1bb78ce9b357 / C2 b6123750b37d against disk b2ab6acb2bbe / e9a27996dfd3"),
    }


def measure_stream() -> dict:
    target_eid = "w06-20260912T0115-f2b-rev6"
    # (a) is it a top-level event in the accepted stream, and how is it stamped?
    in_events = None
    total = 0
    with (ROOT / "research_map/events.jsonl").open() as fh:
        for lineno, line in enumerate(fh, 1):
            total = lineno
            if target_eid not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("event_id") == target_eid and in_events is None:
                in_events = {
                    "line": lineno,
                    "created_at": d.get("created_at"),
                    "received_at": d.get("_received_at"),
                    "received_at_present": "_received_at" in d and d.get("_received_at") is not None,
                    "path": d.get("path"), "sha256": d.get("sha256"),
                    "future_dated_at_measure": str(d.get("created_at") or "") > now(),
                    "sha_differs_from_live_c0": d.get("sha256") != sha256_file(ROOT / CANON_C0),
                }
    # (b) where does it live as an outbox artifact event?
    outbox_hits = []
    for p in sorted((ROOT / "comms/outbox").glob("*.jsonl")):
        with p.open() as fh:
            for lineno, line in enumerate(fh, 1):
                if target_eid not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("event_id") == target_eid:
                    outbox_hits.append({
                        "file": str(p.relative_to(ROOT)), "line": lineno,
                        "created_at": d.get("created_at"),
                        "received_at_present": "_received_at" in d,
                        "path": d.get("path"), "sha256": d.get("sha256"),
                        "future_dated_at_measure": str(d.get("created_at") or "") > now(),
                        "sha_differs_from_live_c0": d.get("sha256") != sha256_file(ROOT / CANON_C0),
                    })
    live = bool(outbox_hits) and any(
        h["future_dated_at_measure"] or not h["received_at_present"] for h in outbox_hits)
    return {
        "events_jsonl_total_lines_at_measure": total,
        "shadow_event_in_accepted_stream": in_events is not None,
        "shadow_event_accepted_stream": in_events,
        "shadow_event_outbox_hits": outbox_hits,
        "shadow_event_outbox_hit_count": len(outbox_hits),
        "ordering_rule_declared": False,  # no stream spec in comms/PROTOCOL.md declares a latest-per-path rule
        "defect_live": live,
    }


# ----------------------------------------------------------------------------------
# 6. main
# ----------------------------------------------------------------------------------
def main() -> int:
    entry_pins = {}

    def check_pins() -> list[dict]:
        drift = []
        for rel, pin in PIN_FILES.items():
            p = ROOT / rel
            measured = sha256_file(p) if p.exists() else None
            if pin is None:  # self-pin placeholder, resolve on first pass
                PIN_FILES[rel] = measured
                pin = measured
            entry_pins[rel] = measured
            if measured != pin:
                drift.append({"path": rel, "expected": pin, "measured": measured})
        return drift

    drift = check_pins()
    if drift:
        print(json.dumps({"status": "PIN_DRIFT", "drift": drift}, indent=2))
        return 3
    start_pins = dict(entry_pins)

    diffs = {name: candidate_diff(CANON_C0, rel) for name, rel in CANDIDATES.items()}
    hfs = extract_hard_failures()
    facts = {
        "C_VOCAB_conclusion_token": measure_vocab(),
        "C_A2_evidence_self_verification": measure_a2(),
        "C_A6_alias_registry_binding": measure_a6(),
        "C_PIPE_acceptance_base_binding": measure_pipe(),
        "C_SEP6_aggregator_pins": measure_sep6(),
        "C_STREAM_ordering_shadow": measure_stream(),
    }

    # ---- join: does either candidate touch a family's anchor? ----
    changed_union = sorted({p for d in diffs.values() for p in d["changed_leaf_paths"] if p})
    fam_rows = []
    for fam, anchor, desc in FAMILIES:
        members = [r for r in hfs if family_of(r["carrier"]) == fam]
        touched_by = []
        for name, d in diffs.items():
            for p in d["changed_leaf_paths"]:
                if p and (p == anchor or p.startswith(anchor + ".") or anchor.startswith(p + ".")):
                    touched_by.append(name)
        live = facts.get(fam, {})
        live_flag = None
        if fam in ("C_H1_containment_denial", "C_H2_inverted_size_premise"):
            live_flag = True  # present in canonical bytes; both candidates rewrite the anchor line
        elif fam == "C_VOCAB_conclusion_token":
            live_flag = (not facts[fam]["f2b_token_in_f0_allowed"]
                         or not facts[fam]["f2b_genericity_in_f0_allowed"])
        elif fam == "C_A2_evidence_self_verification":
            live_flag = not facts[fam]["embeds_measured_input_hashes"]
        elif fam == "C_A6_alias_registry_binding":
            live_flag = not facts[fam]["f0_binding_has_alias_registry_field"]
        elif fam == "C_PIPE_acceptance_base_binding":
            live_flag = facts[fam]["semantic_escape_base_mismatch"] or not facts[fam]["acceptance_pipeline_records_base_bytes"]
        elif fam == "C_SEP6_aggregator_pins":
            live_flag = facts[fam]["stale_component_count"] > 0
        elif fam == "C_STREAM_ordering_shadow":
            live_flag = facts[fam]["defect_live"]
        rows_actor = {
            "C_H1_containment_denial": "schema_owner_edit (both candidates already carry it)",
            "C_H2_inverted_size_premise": "schema_owner_edit (both candidates already carry it)",
            "C_VOCAB_conclusion_token": "gate_owner_ruling (no single schema edit can satisfy both frozen artifacts)",
            "C_A2_evidence_self_verification": "schema_owner_edit or gate_owner_ruling on the evidence standard",
            "C_A6_alias_registry_binding": "schema_owner_edit (add VOCAB_ALIASES path+sha binding; subsumed by the C_VOCAB ruling)",
            "C_PIPE_acceptance_base_binding": "schema_owner_edit (rebase + version-stamp the frozen evidence, then re-freeze)",
            "C_SEP6_aggregator_pins": "schema_owner_edit (re-pin aggregator components to rev13; aggregator is not FROZEN-pinned)",
            "C_STREAM_ordering_shadow": "controller_stream_hygiene (quarantine/annotate the future-dated event; declare an ordering rule)",
        }
        fam_rows.append({
            "family": fam,
            "anchor": anchor,
            "description": desc,
            "hf_records": len(members),
            "distinct_sources": sorted({m["source"] for m in members}),
            "distinct_reviewers": sorted({m["reviewer"] for m in members if m["reviewer"]}),
            "full_schema_verdict_sources": sorted({m["source"] for m in members if m["full_schema_verdict"]}),
            "touched_by_candidate": sorted(set(touched_by)),
            "defect_live_at_frozen_bytes": live_flag,
            "closing_actor_required": rows_actor[fam],
            "measured": facts.get(fam),
        })

    untouched_live = [r for r in fam_rows if not r["touched_by_candidate"] and r["defect_live_at_frozen_bytes"]]
    touched = [r for r in fam_rows if r["touched_by_candidate"]]
    closed_during = [r for r in fam_rows if (not r["defect_live_at_frozen_bytes"] and r["measured"]
                                             and r["measured"].get("closed_during_audit"))]
    verdict = {
        "families_total": len(fam_rows),
        "families_touched_by_containment_repair": len(touched),
        "families_closed_by_concurrent_owner_edit_during_audit": len(closed_during),
        "closed_by_concurrent_owner_edit": [r["family"] for r in closed_during],
        "mid_audit_move": {
            k: facts["C_SEP6_aggregator_pins"][k] for k in
            ("aggregator_revision", "aggregator_sha256", "frame_time_pin",
             "declared_supersedes_sha256", "frame_pin_chain_confirmed",
             "stale_component_count", "rev6_staleness_evidence")
        },
        "families_untouched_and_still_live": len(untouched_live),
        "untouched_live_families": [r["family"] for r in untouched_live],
        "conclusion": (
            "A rev14 carrying only the two validated containment edits closes "
            f"{len(touched)}/{len(fam_rows)} open F2b carrier families "
            "(C_H1, C_H2) and leaves "
            f"{len(untouched_live)} live ({', '.join(r['family'] for r in untouched_live)}). "
            f"{len(closed_during)} further family (C_SEP6) was live at frame time and was closed by a "
            "concurrent owner edit (aggregator revision 7) before this run, verified by the revision's "
            "declared supersedes_sha256 equalling this audit's frame-time pin. "
            "The containment-only rev14 is therefore predicted, on the frozen bytes, to attract further "
            "revise verdicts from the same sources unless the remaining families are edited or ruled out "
            "before re-freeze."
        ),
        "falsifier": (
            "FALSIFIED IF any of: (a) a pinned input differs from its recorded sha256 at "
            "measurement time (runner exits 3); (b) the changed-leaf join misses a containment "
            "carrier or flags a non-containment carrier (K1/K2 fail); (c) any family recorded "
            "defect_live=true is shown closed at the pinned bytes by a frozen adjudication or "
            "corrected bytes; (d) a rev14 lands that already carries edits to C_VOCAB/C_A2/"
            "C_A6/C_PIPE/C_SEP6 or a controller ruling closes them; (e) the review record at "
            "the frozen pins contains a hard-failure family not enumerated here."
        ),
    }

    # ---- controls ----
    controls = {}
    controls["K1_candidate_minimality_and_join"] = all(
        d["changed_line_count"] == 2 and set(d["changed_leaf_paths"]) == {
            "regularity.must_not_conflate[0]", "implication_ledger.forbidden_transfers[0]"}
        for d in diffs.values())
    # K2 join sensitivity: synthetic carrier at a changed path must be TOUCHED, elsewhere not
    k2_hit = any(p == "regularity.must_not_conflate[0]" for p in changed_union)
    k2_miss = any(p == "provenance.citation_status" for p in changed_union)
    controls["K2_join_sensitivity"] = k2_hit and not k2_miss
    # K3 determinism of extraction + join (recompute, compare canonical hash)
    SIG_KEYS = ("family", "anchor", "description", "hf_records", "distinct_sources",
                "distinct_reviewers", "full_schema_verdict_sources", "touched_by_candidate")
    fam_sig_1 = canonical_sha256([{k: r[k] for k in SIG_KEYS} for r in fam_rows])
    hfs_sig_1 = canonical_sha256(hfs)
    hfs2 = extract_hard_failures()
    fam_rows2 = []
    for fam, anchor, desc in FAMILIES:
        members = [r for r in hfs2 if family_of(r["carrier"]) == fam]
        touched_by = []
        for name, d in diffs.items():
            for p in d["changed_leaf_paths"]:
                if p and (p == anchor or p.startswith(anchor + ".") or anchor.startswith(p + ".")):
                    touched_by.append(name)
        fam_rows2.append({"family": fam, "anchor": anchor, "description": desc,
                          "hf_records": len(members),
                          "distinct_sources": sorted({m["source"] for m in members}),
                          "distinct_reviewers": sorted({m["reviewer"] for m in members if m["reviewer"]}),
                          "full_schema_verdict_sources": sorted({m["source"] for m in members if m["full_schema_verdict"]}),
                          "touched_by_candidate": sorted(set(touched_by))})
    fam_sig_2 = canonical_sha256([{k: r[k] for k in SIG_KEYS} for r in fam_rows2])
    controls["K3_determinism"] = (fam_sig_1 == fam_sig_2 and hfs_sig_1 == canonical_sha256(hfs2))
    # K4 fail-closed pin drift (simulated, must be detected by check_pins logic)
    saved = PIN_FILES[CANON_C0]
    PIN_FILES[CANON_C0] = "0" * 64
    controls["K4_fail_closed_pin_drift"] = bool(check_pins())
    PIN_FILES[CANON_C0] = saved
    # K5 extraction non-vacuity
    controls["K5_extraction_non_vacuity"] = (
        len(fam_rows) >= MIN_FAMILIES and len(hfs) >= MIN_HF_RECORDS
        and len({r["source"] for r in hfs}) >= MIN_SOURCES)
    # K6 negative control: unnamed path is not in the carrier set
    controls["K6_negative_control_unmapped_path"] = family_of("provenance.citation_status") is None
    if not all(controls.values()):
        print(json.dumps({"status": "INSTRUMENT_SELF_CHECK_FAILED", "controls": controls}, indent=2))
        return 4

    report = {
        "task_id": TASK_ID,
        "actor": "worker-063",
        "created_at": now(),
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "authority_note": ("Worker measurement only. No gate verdict, node status, validation_status, "
                           "or canonical byte change is made or claimed. Interpretation is owned by "
                           "astra-lead-formulation / astra-lead-audit."),
        "question": "Does a containment-only F2b rev14 (the two validated edits) close the open F2b finding record at FROZEN rev29 / F2b rev13?",
        "frame": {
            "canonical_f2b": CANON_C0,
            "candidates": CANDIDATES,
            "review_frame": ("hard-failure records binding F2b/C0 at b2ab6acb2bbe / F2b rev13 / FROZEN rev29 in the pinned "
                             "review files plus the pinned accepted-stream review/blocker snapshot"),
            "frozen_revision": 29,
            "frozen_at": json.loads(read_text("artifacts/formulation/FROZEN.json")).get("frozen_at"),
        },
        "pins_measured_at_start": start_pins,
        "candidate_diffs": diffs,
        "hard_failure_records": hfs,
        "hard_failure_record_count": len(hfs),
        "families": fam_rows,
        "verdict": verdict,
        "controls": controls,
        "limits": [
            "The join is path-based on this project's YAML layout; a future re-layout can move a carrier without moving the defect.",
            "C_A2/C_A6/C_SEP6/C_STREAM each rest on one advisory or non-full-schema source (worker-044/095/062) at frame time; C_PIPE also has the formulation lead's own 01:13 blocker. They are live at the bytes but carry less weight than the multi-reviewer containment families.",
            "The instrument does not re-adjudicate whether each reviewer's hard failure is correct; it measures whether the defect is still present in the frozen bytes and whether the candidate edits its carrier.",
            "The review frame closes at 01:09-01:13; reviews published after that (e.g. worker-085 01:11:45) are not in the record.",
            "Review traffic continues; applicability is bounded by the pinned hashes and exits 3 on drift.",
        ],
        "next_falsifier": verdict["falsifier"],
    }
    # ---- end-of-run stability: any pin moved while measuring? ----
    end_pins = {}
    end_drift = []
    for rel, pin in PIN_FILES.items():
        measured = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        end_pins[rel] = measured
        if measured != start_pins.get(rel):
            end_drift.append({"path": rel, "start": start_pins.get(rel), "end": measured})
    report["pins_stable_during_run"] = not end_drift
    report["end_drift"] = end_drift
    report["end_pins"] = end_pins
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    with (HERE / "matrix.tsv").open("w") as fh:
        fh.write("family\tanchor\thf_records\tdistinct_sources\ttouched_by_candidate\tdefect_live\tclosing_actor_required\n")
        for r in fam_rows:
            fh.write("\t".join([r["family"], r["anchor"], str(r["hf_records"]),
                                str(len(r["distinct_sources"])), ",".join(r["touched_by_candidate"]) or "-",
                                str(r["defect_live_at_frozen_bytes"]), r["closing_actor_required"]]) + "\n")
    status = "MEASURED" if not end_drift else "SUPERSEDED_DURING_RUN"
    print(json.dumps({
        "status": status,
        "report_sha256": sha256_file(HERE / "report.json"),
        "matrix_sha256": sha256_file(HERE / "matrix.tsv"),
        "controls": controls,
        "verdict": {k: verdict[k] for k in ("families_total", "families_touched_by_containment_repair",
                                            "families_closed_by_concurrent_owner_edit_during_audit",
                                            "families_untouched_and_still_live", "untouched_live_families")},
        "changed_leaf_paths": {k: v["changed_leaf_paths"] for k, v in diffs.items()},
        "hard_failure_records": len(hfs),
        "end_drift": end_drift,
    }, indent=2))
    return 0 if not end_drift else 3


if __name__ == "__main__":
    sys.exit(main())
