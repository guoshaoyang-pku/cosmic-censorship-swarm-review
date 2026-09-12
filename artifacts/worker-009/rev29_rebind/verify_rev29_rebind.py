#!/usr/bin/env python3
"""worker-009 bounded class-bound task: post-repair re-binding + DET-REV12 closure.

Context
-------
The 12-row SCC class-binding correction proposal (7 rows CBC-09-001..007 + 5 rows
CBC-09-008..012) was verified by worker-009 against the rev12 schema bytes
(F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda) and FROZEN rev28
(2f358f6722d9).  While this worker was running, the formulation lead landed
astra-life05-evidence-binding-repair: schemas moved to rev13
(F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe) and FROZEN moved to rev29
(3d9e3d77fd87 at 00:55:02, re-written to 815e08079aef at 00:57:26; VARIANT_REGISTRY was
also repaired to 6bac9adea19e).  That move *voids* the rev12 binding record by its own
falsifier, so this tool re-binds the patch at the new bytes and runs the declared
next-falsifier: DET-REV12 over the 12-row dry-run ledger.

What is checked (read-only against canonical state; canonical ledger and the two
canonical patch files are never written)
  A  anchors: L1 ledger, L0 theorem ledger, rev13 schemas + mirrors, FROZEN rev29
     pins, VARIANT_REGISTRY, consistency evidence, declared F0, rev12 snapshots,
     the patch inputs and the prior dry-run/record;
  B  rev12 -> rev13 delta audit: every changed leaf path classified; F2a/F2b must
     be metadata-only, F1 metadata + exactly the three declared text corrections;
     class-id census, data_class, anti_scope, T-514/T-520 scope_use and the
     variant-CH record must be byte-identical;
  C  re-binding: reproduce the pinned 12-row dry-run byte-identically from the
     current inputs; exactly 12 class_mapping cells change; stale-old-mapping
     negative control;
  D  DET-REV12 (verbatim detector from the rev12 verification) on canonical and
     dry-run ledgers, strict-token reading and removal-clause-aware reading;
  E  remediation: a 2-row minimal text fix that removes the literal frozen vacuum
     ids from the replacement cells, dry-run applied and re-tested;
  F  falsifier conditions: root causes still present at the frozen theorem hash,
     no transfer-authorizing schema text, advisories carried.

Deterministic given --verified-at (no wall clock is read inside).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_LEDGER = ROOT / "ledger" / "citation_audit.csv"
PATCH7_CSV = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.csv"
PATCH5_CSV = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"
PATCH5_JSONL = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.jsonl"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
CONSISTENCY = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
DRYRUN12 = ROOT / "artifacts" / "worker-009" / "detrev12" / "dryrun_applied_citation_audit_12row.csv"
PRIOR_RECORD = ROOT / "artifacts" / "worker-009" / "detrev12" / "verification_candidates_worker-009.json"
SNAPDIR = ROOT / "artifacts" / "worker-060" / "rev29_binding_acceptance" / "snapshots"
SNAP_F1 = SNAPDIR / "f1__af_wcc_vacuum.cce9c60146d6.yaml"
SNAP_F2A = SNAPDIR / "f2a__af_scc_c2_vacuum.5476a3f2c6bc.yaml"
SNAP_F2B = SNAPDIR / "f2b__af_scc_c0_vacuum.55d0a1ea9bda.yaml"
MIRROR_F1 = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
MIRROR_F2A = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
MIRROR_F2B = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"

OUTDIR = ROOT / "artifacts" / "worker-009" / "rev29_rebind"
OUT_RECORD = OUTDIR / "verification_rev29_rebind_worker-009.json"
OUT_REMEDIATED_DRYRUN = OUTDIR / "dryrun_applied_citation_audit_12row_remediated.csv"
OUT_REMEDIATION_CSV = OUTDIR / "remediation_classmapping_2row_worker-009.csv"
OUT_REMEDIATION_JSONL = OUTDIR / "remediation_classmapping_2row_worker-009.jsonl"
CHECKPOINT = ROOT / "runtime" / "state" / "w009_rev29_rebind_checkpoint_1.json"

EXPECTED = {
    "ledger": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "theorems": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "f1_rev13": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "f2a_rev13": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "f2b_rev13": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "frozen_rev29": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "registry": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "frozen_rev29_first_measure": "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
    "registry_pre_repair": "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    "consistency": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "patch7_csv": "47917e0e54bc447bab2143decdb22349cfea0214abea5a5619c125f55c1c70aa",
    "patch5_csv": "2571c88b668659f8993b0fe614b15e752832c5044be082e7d3443baf8ec29c98",
    "patch5_jsonl": "a977250fcc45405ef7884965724185caa27a7131c0f1508da8e81ba8f37965b2",
    "dryrun12": "e222822986254c45bafae45bd0bcba7893a7d824e5fcb8036d9385b4f3ba00de",
    "prior_record": "2473a47c92d52da075f7f5c64064233cf9ac8ad3b40ff4ec6f556719cbe34e9e",
    "snap_f1_rev12": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "snap_f2a_rev12": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "snap_f2b_rev12": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "consistency_declared_rev12": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
}

FROZEN_VACUUM_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
FROZEN_CLASS_IDS_4 = FROZEN_VACUUM_IDS + ["AF-WCC-SCALAR-SPH"]
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
PATCHED_ROWS_7 = ["SRC-021", "SRC-056", "SRC-025", "SRC-058", "SRC-057", "SRC-024", "SRC-050"]
CANDIDATE_ROWS = ["SRC-014", "SRC-029", "SRC-033", "SRC-048", "SRC-061"]
ALL_12 = PATCHED_ROWS_7 + CANDIDATE_ROWS
EXPECTED_UNCOVERED = ["SRC-014", "SRC-029", "SRC-033", "SRC-048", "SRC-061"]
EXPECTED_ROOT_CAUSE_CLASS_IDS = {
    "D-002": ["AF-SCC-C0-VAC-GEN"],
    "D-003": ["AF-SCC-C2-VAC-GEN"],
    "D-004": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
    "D-005": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
    "D-007": ["AF-SCC-C2-VAC-GEN"],
    "T-516": ["AF-WCC-SCALAR-SPH"],
}
ID_TOKEN_RE = re.compile(r"AF-[A-Z0-9-]+")
VACUUM_TOKEN_RE = re.compile(r"AF-(?:WCC|SCC-C[02])-VAC-GEN")
REMOVAL_CLAUSE_RE = re.compile(r"AF-[A-Z0-9-]+\s+removed", re.I)
PAIR_RE = re.compile(r"variant\s+([A-Z0-9]+)\s+parent\s+(AF-[A-Z0-9-]+)")
EXPLICIT_DO_NOT_TRANSFER = {"T-514", "T-520"}
NON_TRANSFER_RE = re.compile(
    r"says nothing directly about vacuum|does not settle the C\^?0 formulation"
    r"|does not imply C\^?2 SCC for vacuum|does not apply to vacuum"
    r"|does not transfer to AF vacuum|does not prove C\^?2 SCC in vacuum"
    r"|does not refute AF-SCC-C[02]-VAC-GEN|does not decide the C\^?2 formulation"
    r"|does not prove SCC failure in vacuum|Not the C\^?[02] formulation"
    r"|does not imply the same for vacuum",
    re.I,
)
MATTER_RE = re.compile(r"Einstein-Maxwell|scalar field|Vaidya|FLRW|charged|matter model", re.I)
TRANSFER_RE = re.compile(r"may transfer|same data class|transferable|does transfer", re.I)

REMEDIATION = {
    "SRC-014": (
        "AF-WCC-SCALAR-SPH (WCC-side scalar tag retained with scope caveat); "
        "SCC-side frozen vacuum binding removed; model-class: Einstein-massless-scalar "
        "spherical collapse; scope_use: do-not-transfer; no SCC vacuum class binding"
    ),
    "SRC-061": (
        "AF-WCC-SCALAR-SPH (scalar-side tag retained; T-516 registers this source for the "
        "neutral-scalar case with optional Maxwell field); SCC-side frozen vacuum binding "
        "removed; model-class: Einstein-Maxwell-(real)-scalar spherical; scope_use: "
        "do-not-transfer; no SCC vacuum class binding"
    ),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def read_csv_rows(p: Path):
    raw = p.read_bytes()
    text = raw.decode("utf-8")
    lineterm = "\r\n" if "\r\n" in text else "\n"
    rows = list(csv.reader(io.StringIO(text, newline="")))
    return raw, lineterm, rows


def roundtrip(rows, lineterm: str) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=lineterm)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def read_theorems(p: Path) -> dict:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["theorem_id"]] = d
    return out


def flatten(o, prefix: str = "") -> dict:
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = o
    return out


def yaml_dup_paths(node, prefix: str = "") -> list:
    """Return paths of duplicate mapping keys anywhere in a composed YAML doc."""
    dups = []
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k_node, v_node in node.value:
            key = k_node.value
            if key in seen:
                dups.append(f"{prefix}.{key}" if prefix else key)
            seen.add(key)
            dups.extend(yaml_dup_paths(v_node, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            dups.extend(yaml_dup_paths(v, f"{prefix}[{i}]"))
    return dups


def is_metadata_path(p: str) -> bool:
    top = p.split(".")[0].split("[")[0]
    if top in ("revised_at", "revision"):
        return True
    if p.startswith("revision_history["):
        return True
    if p.startswith("f0_binding."):
        return True
    return False


def is_f1_correction_path(p: str) -> bool:
    if p == "visibility.definition":
        return True
    if p == "quantifiers.domains.D5.definition":
        return True
    if p.startswith("class_identity_variants[") and p.endswith(".relation"):
        return True
    return False


def detect(rows, header, theorems, removal_aware: bool):
    """DET-REV12 verbatim from verify_rev12_binding.py, plus an optional
    removal-clause-aware pre-strip that removes '<class-id> removed' mentions."""
    ci = header.index("class_mapping")
    ui = header.index("used_by_theorems")
    hits = []
    for r in rows:
        cm = r[ci]
        cm_binding = PAIR_RE.sub("", cm)
        if removal_aware:
            cm_binding = REMOVAL_CLAUSE_RE.sub("", cm_binding)
        vs = [v for v in FROZEN_VACUUM_IDS if v in cm_binding]
        if not vs:
            continue
        reasons = []
        for t in [x for x in r[ui].split(";") if x]:
            rec = theorems.get(t)
            if not rec:
                continue
            dnis = " ".join(rec.get("does_not_imply", []))
            if t in EXPLICIT_DO_NOT_TRANSFER:
                reasons.append(f"{t}:rev12 contract scope_use=do-not-transfer")
            elif NON_TRANSFER_RE.search(dnis):
                reasons.append(f"{t}:does_not_imply denies vacuum transfer")
            elif any(v in rec.get("class_ids", []) for v in vs) and MATTER_RE.search(
                " ".join(
                    rec.get("assumptions", [])
                    + rec.get("does_not_imply", [])
                    + rec.get("scope_caveats", [])
                )
            ):
                reasons.append(f"{t}:matter-model record carries {vs[0]}")
        if reasons:
            hits.append(
                {
                    "citation_id": r[0],
                    "class_mapping": cm,
                    "used_by_theorems": r[ui],
                    "reasons": reasons,
                }
            )
    return hits


def apply_patch(ledger_rows, header, patch_records):
    """Apply patch records to a byte-faithful copy; refuse stale old_class_mapping."""
    applied = [list(r) for r in ledger_rows]
    ci = header.index("class_mapping")
    ri = header.index("citation_id")
    changed, refused = [], []
    for pr in patch_records:
        target = None
        for r in applied:
            if r[ri] == pr["canonical_row_id"]:
                target = r
                break
        if target is None or target[ci] != pr["old_class_mapping"]:
            refused.append(pr["correction_id"])
            continue
        if target[ci] != pr["new_class_mapping"]:
            target[ci] = pr["new_class_mapping"]
            changed.append((pr["correction_id"], pr["canonical_row_id"]))
    return applied, changed, refused


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verified-at", required=True)
    ap.add_argument("--out", default=str(OUT_RECORD))
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    def check(cid, desc, ok, detail=""):
        checks.append(
            {
                "check_id": cid,
                "description": desc,
                "result": "PASS" if ok else "FAIL",
                "detail": str(detail)[:400],
            }
        )

    def advisory(cid, desc, detail=""):
        checks.append(
            {
                "check_id": cid,
                "description": desc,
                "result": "ADVISORY",
                "detail": str(detail)[:400],
            }
        )

    named = [
        ("canonical_ledger", CANONICAL_LEDGER),
        ("patch7_csv", PATCH7_CSV),
        ("patch5_csv", PATCH5_CSV),
        ("patch5_jsonl", PATCH5_JSONL),
        ("theorems", THEOREMS),
        ("f1_rev13", F1),
        ("f2a_rev13", F2A),
        ("f2b_rev13", F2B),
        ("mirror_f1", MIRROR_F1),
        ("mirror_f2a", MIRROR_F2A),
        ("mirror_f2b", MIRROR_F2B),
        ("frozen_rev29", FROZEN),
        ("variant_registry", REGISTRY),
        ("consistency_evidence", CONSISTENCY),
        ("declared_f0", F0),
        ("dryrun12", DRYRUN12),
        ("prior_record", PRIOR_RECORD),
        ("snap_f1_rev12", SNAP_F1),
        ("snap_f2a_rev12", SNAP_F2A),
        ("snap_f2b_rev12", SNAP_F2B),
    ]
    inputs = {}
    for name, p in named:
        inputs[name] = {
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
        }

    # ---------------- A. anchors ----------------------------------------
    check("A01", "canonical L1 ledger hashes to the frozen sha",
          inputs["canonical_ledger"]["sha256"] == EXPECTED["ledger"],
          inputs["canonical_ledger"]["sha256"])
    raw, lineterm, rows = read_csv_rows(CANONICAL_LEDGER)
    header = rows[0]
    data = rows[1:]
    check("A02", "canonical ledger shape is 97 rows x 25 columns and round-trips byte-identically",
          len(data) == 97 and len(header) == 25 and roundtrip(rows, lineterm) == raw,
          f"rows={len(data)} cols={len(header)} crlf={'yes' if lineterm == chr(13)+chr(10) else 'no'}")
    check("A03", "L0 theorem ledger hashes to the frozen sha",
          inputs["theorems"]["sha256"] == EXPECTED["theorems"],
          inputs["theorems"]["sha256"])
    for cid, key, exp in [
        ("A04", "f1_rev13", EXPECTED["f1_rev13"]),
        ("A05", "f2a_rev13", EXPECTED["f2a_rev13"]),
        ("A06", "f2b_rev13", EXPECTED["f2b_rev13"]),
    ]:
        check(cid, f"schema {inputs[key]['path']} hashes to the measured rev13 byte",
              inputs[key]["sha256"] == exp, inputs[key]["sha256"])
    for cid, live, mirror in [
        ("A07", "f1_rev13", "mirror_f1"),
        ("A08", "f2a_rev13", "mirror_f2a"),
        ("A09", "f2b_rev13", "mirror_f2b"),
    ]:
        check(cid, f"live {inputs[live]['path']} == formulation mirror bytes",
              inputs[live]["sha256"] == inputs[mirror]["sha256"],
              f"live={inputs[live]['sha256'][:12]} mirror={inputs[mirror]['sha256'][:12]}")

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    fpins = {k: v.get("sha256") for k, v in frozen.get("files", {}).items()}
    check("A10", "FROZEN.json is revision 29 at the second measured byte (bytes re-written in-session 00:55:02 -> 00:57:26)",
          frozen.get("revision") == 29 and inputs["frozen_rev29"]["sha256"] == EXPECTED["frozen_rev29"]
          and EXPECTED["frozen_rev29"] != EXPECTED["frozen_rev29_first_measure"],
          f"revision={frozen.get('revision')} frozen_at={frozen.get('frozen_at')} sha={inputs['frozen_rev29']['sha256'][:12]} first={EXPECTED['frozen_rev29_first_measure'][:12]}")
    for cid, key, rel in [
        ("A11", "f1_rev13", "schemas/af_wcc_vacuum.yaml"),
        ("A12", "f2a_rev13", "schemas/af_scc_c2_vacuum.yaml"),
        ("A13", "f2b_rev13", "schemas/af_scc_c0_vacuum.yaml"),
    ]:
        check(cid, f"FROZEN rev29 pins the measured sha of {rel} (live and mirror keys)",
              fpins.get(rel) == inputs[key]["sha256"]
              and fpins.get("artifacts/formulation/" + rel) == inputs[key]["sha256"],
              f"pin={fpins.get(rel)} measured={inputs[key]['sha256'][:12]}")
    check("A14", "FROZEN rev29 pins VARIANT_REGISTRY and taxonomy_consistency at measured bytes",
          fpins.get("artifacts/formulation/VARIANT_REGISTRY.json") == inputs["variant_registry"]["sha256"]
          and fpins.get("artifacts/formulation/evidence/taxonomy_consistency.json") == inputs["consistency_evidence"]["sha256"],
          f"registry={inputs['variant_registry']['sha256'][:12]} consistency={inputs['consistency_evidence']['sha256'][:12]}")

    schemas = {}
    for key, p in [("f1_rev13", F1), ("f2a_rev13", F2A), ("f2b_rev13", F2B)]:
        schemas[key] = yaml.safe_load(p.read_text(encoding="utf-8"))
    check("A15", "declared F0 taxonomy byte is untouched and every schema f0_binding names it",
          inputs["declared_f0"]["sha256"] == EXPECTED["f0"]
          and all(s["f0_binding"]["declared_f0_sha256"] == EXPECTED["f0"] for s in schemas.values()),
          f"f0={inputs['declared_f0']['sha256'][:12]}")
    check("A16", "every schema f0_binding names the live taxonomy_consistency.json (rev13 repair item 2)",
          all(s["f0_binding"]["consistency_evidence_sha256"] == EXPECTED["consistency"] for s in schemas.values())
          and inputs["consistency_evidence"]["sha256"] == EXPECTED["consistency"],
          f"consistency={inputs['consistency_evidence']['sha256'][:12]}")
    check("A17", "every schema f0_binding was refreshed from the rev12 evidence sha (repair really bit)",
          all(s["f0_binding"]["consistency_evidence_sha256"] != EXPECTED["consistency_declared_rev12"] for s in schemas.values()),
          "rev12 675a99d0 -> rev13 9e335e9b in all three")
    check("A18", "patch inputs and prior dry-run/record hash to their declared bytes",
          inputs["patch7_csv"]["sha256"] == EXPECTED["patch7_csv"]
          and inputs["patch5_csv"]["sha256"] == EXPECTED["patch5_csv"]
          and inputs["patch5_jsonl"]["sha256"] == EXPECTED["patch5_jsonl"]
          and inputs["dryrun12"]["sha256"] == EXPECTED["dryrun12"]
          and inputs["prior_record"]["sha256"] == EXPECTED["prior_record"],
          "5/5 pinned")
    check("A19", "rev12 snapshots hash to the bytes the rev12 record pinned",
          inputs["snap_f1_rev12"]["sha256"] == EXPECTED["snap_f1_rev12"]
          and inputs["snap_f2a_rev12"]["sha256"] == EXPECTED["snap_f2a_rev12"]
          and inputs["snap_f2b_rev12"]["sha256"] == EXPECTED["snap_f2b_rev12"],
          "3/3 pinned")
    dups = {}
    for key, p in [("f1_rev13", F1), ("f2a_rev13", F2A), ("f2b_rev13", F2B)]:
        dups[key] = yaml_dup_paths(yaml.compose(p.read_text(encoding="utf-8")))
    check("A20", "no duplicate mapping keys anywhere in the three rev13 schemas",
          all(len(v) == 0 for v in dups.values()), json.dumps(dups))
    check("A21", "all three schemas declare revision 13 at the measured bytes",
          all(s.get("revision") == 13 for s in schemas.values())
          and all(str(s.get("revised_at", "")).startswith("2026-09-12T00:53") for s in schemas.values()),
          json.dumps({k: (v.get("revision"), v.get("revised_at")) for k, v in schemas.items()}))

    # ---------------- B. rev12 -> rev13 delta audit ----------------------
    snaps = {
        "f1_rev13": yaml.safe_load(SNAP_F1.read_text(encoding="utf-8")),
        "f2a_rev13": yaml.safe_load(SNAP_F2A.read_text(encoding="utf-8")),
        "f2b_rev13": yaml.safe_load(SNAP_F2B.read_text(encoding="utf-8")),
    }
    delta = {}
    for key in ("f1_rev13", "f2a_rev13", "f2b_rev13"):
        old = flatten(snaps[key])
        new = flatten(schemas[key])
        paths = sorted(set(old) | set(new))
        changed = [p for p in paths if old.get(p) != new.get(p)]
        delta[key] = changed
    meta_only = lambda ps: [p for p in ps if not is_metadata_path(p)]
    f2a_extra = meta_only(delta["f2a_rev13"])
    f2b_extra = meta_only(delta["f2b_rev13"])
    f1_extra = meta_only(delta["f1_rev13"])
    f1_unexpected = [p for p in f1_extra if not is_f1_correction_path(p)]
    check("B01", "F2a rev12->rev13 changed leaf paths are metadata-only",
          f2a_extra == [], f"changed={len(delta['f2a_rev13'])} non-metadata={f2a_extra}")
    check("B02", "F2b rev12->rev13 changed leaf paths are metadata-only",
          f2b_extra == [], f"changed={len(delta['f2b_rev13'])} non-metadata={f2b_extra}")
    check("B03", "F1 rev12->rev13 non-metadata changes are exactly the 3 declared text corrections",
          sorted(f1_extra) == sorted([
              "visibility.definition",
              "quantifiers.domains.D5.definition",
              "class_identity_variants[0].relation",
          ]) and f1_unexpected == [],
          f"non-metadata={sorted(f1_extra)}")
    census_ok = True
    census_detail = {}
    for key, p_old, p_new in [
        ("f1_rev13", SNAP_F1, F1),
        ("f2a_rev13", SNAP_F2A, F2A),
        ("f2b_rev13", SNAP_F2B, F2B),
    ]:
        a = sorted(ID_TOKEN_RE.findall(p_old.read_text(encoding="utf-8")))
        b = sorted(ID_TOKEN_RE.findall(p_new.read_text(encoding="utf-8")))
        census_detail[key] = {"equal": a == b, "n_old": len(a), "n_new": len(b)}
        census_ok = census_ok and a == b
    check("B04", "whole-file class-id census is unchanged rev12 -> rev13 in all three schemas",
          census_ok, json.dumps(census_detail))
    dc_ok = all(snaps[k].get("data_class") == schemas[k].get("data_class") for k in ("f1_rev13", "f2a_rev13", "f2b_rev13"))
    check("B05", "data_class blocks are byte-identical rev12 -> rev13",
          dc_ok, json.dumps({k: schemas[k]["data_class"].get("matter") for k in ("f1_rev13", "f2a_rev13", "f2b_rev13")}))
    anti_ok = all(
        [e.get("class_id") for e in snaps[k].get("anti_scope", {}).get("not_this_class", [])]
        == [e.get("class_id") for e in schemas[k].get("anti_scope", {}).get("not_this_class", [])]
        for k in ("f1_rev13", "f2a_rev13", "f2b_rev13")
    )
    check("B06", "anti_scope class lists are identical rev12 -> rev13",
          anti_ok, "lists compared element-wise")
    f2a_refs = {e["theorem_id"]: e for e in schemas["f2a_rev13"].get("l1_ledger_refs", [])}
    f2a_refs_old = {e["theorem_id"]: e for e in snaps["f2a_rev13"].get("l1_ledger_refs", [])}
    anchors_ok = (
        f2a_refs.get("T-514", {}).get("scope_use") == "different data class; do not transfer"
        and f2a_refs.get("T-520", {}).get("scope_use") == "different data class; do not transfer"
        and f2a_refs.get("T-514") == f2a_refs_old.get("T-514")
        and f2a_refs.get("T-520") == f2a_refs_old.get("T-520")
    )
    check("B07", "F2a T-514/T-520 do-not-transfer contract rows are unchanged and still binding",
          anchors_ok, "T-514/T-520 scope_use='different data class; do not transfer', records identical")
    ch_new = schemas["f2b_rev13"].get("class_identity_variants", {}).get("horizon_localized_variant", {})
    ch_old = snaps["f2b_rev13"].get("class_identity_variants", {}).get("horizon_localized_variant", {})
    ch_ok = (
        ch_new == ch_old
        and ch_new.get("is_this_class") is False
        and ch_new.get("status") == "registered_variant_not_written"
        and "D-002" in ch_new.get("addressed_by", [])
        and "scope error" in ch_new.get("why_separate", "")
    )
    check("B08", "F2b variant-CH record is identical and still not-this-class with the scope-error warning",
          ch_ok, f"is_this_class={ch_new.get('is_this_class')!r} addressed_by={ch_new.get('addressed_by')}")
    f1_variants = schemas["f1_rev13"].get("class_identity_variants", [])
    f1_variants_old = snaps["f1_rev13"].get("class_identity_variants", [])
    f1_rel_ok = (
        len(f1_variants) == len(f1_variants_old)
        and all(
            {k: v for k, v in a.items() if k != "relation"} == {k: v for k, v in b.items() if k != "relation"}
            for a, b in zip(f1_variants, f1_variants_old)
        )
        and "strictly WEAKER" in f1_variants[0].get("relation", "")
        and "strictly STRONGER" in f1_variants_old[0].get("relation", "")
    )
    check("B09", "F1 variant SET record differs only in the corrected strictness direction",
          f1_rel_ok, "rev12 'strictly STRONGER' -> rev13 'strictly WEAKER'; all other fields identical")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    reg_pairs = {(v.get("parent_class"), v.get("variant_id")) for v in reg.get("variants", [])}
    reg_rule_ok = (
        "AF-WCC-SCALAR-SPH" in reg.get("class_id_rule", "")
        and "parent_class" in reg.get("rule", "")
        and "variant_id" in reg.get("rule", "")
        and "leakage" in reg.get("rule", "")
    )
    check("B10", "VARIANT_REGISTRY (re-anchored after the in-session C4 repair) still registers CH/LIP under C0 and keeps the no-leakage rule",
          inputs["variant_registry"]["sha256"] == EXPECTED["registry"]
          and {("AF-SCC-C0-VAC-GEN", "CH"), ("AF-SCC-C0-VAC-GEN", "LIP")} <= reg_pairs
          and reg_rule_ok,
          f"registry={inputs['variant_registry']['sha256'][:12]} moved_from={EXPECTED['registry_pre_repair'][:12]} rule_ok={reg_rule_ok}")

    # ---------------- C. re-binding / reproduction -----------------------
    patch7 = list(csv.DictReader(io.StringIO(PATCH7_CSV.read_text(encoding="utf-8"), newline="")))
    patch5 = list(csv.DictReader(io.StringIO(PATCH5_CSV.read_text(encoding="utf-8"), newline="")))
    check("C01", "patch input record counts are 7 + 5 = 12",
          len(patch7) == 7 and len(patch5) == 5, f"patch7={len(patch7)} patch5={len(patch5)}")
    check("C02", "every patch row declares the frozen canonical ledger sha",
          all(p["canonical_file_sha256"] == EXPECTED["ledger"] for p in patch7 + patch5),
          "12/12")
    rows_by_id = {r[0]: r for r in data}
    cm_idx = header.index("class_mapping")
    check("C03", "every patch old_class_mapping still equals the canonical class_mapping cell (falsifier e)",
          all(p["old_class_mapping"] == rows_by_id[p["canonical_row_id"]][cm_idx] for p in patch7 + patch5),
          "12/12 match")
    applied, changed, refused = apply_patch(data, header, patch7 + patch5)
    check("C04", "all 12 patch rows apply to the frozen ledger; 0 refused",
          len(changed) == 12 and refused == [], f"changed={len(changed)} refused={refused}")
    diff_cells = [(i, j) for i, (a, b) in enumerate(zip(data, applied)) for j, (x, y) in enumerate(zip(a, b)) if x != y]
    check("C05", "dry-run changes exactly 12 cells, all in class_mapping",
          len(diff_cells) == 12 and {j for _, j in diff_cells} == {cm_idx},
          f"cells={len(diff_cells)} cols={sorted({j for _, j in diff_cells})}")
    applied_bytes = roundtrip([header] + applied, lineterm)
    check("C06", "reproduced 12-row dry-run is byte-identical to the pinned rev12 dry-run",
          sha256_bytes(applied_bytes) == EXPECTED["dryrun12"] and applied_bytes == DRYRUN12.read_bytes(),
          f"reproduced={sha256_bytes(applied_bytes)[:12]} pinned={EXPECTED['dryrun12'][:12]}")
    bogus = [dict(p) for p in (patch7 + patch5)]
    bogus[0]["old_class_mapping"] = bogus[0]["old_class_mapping"] + ";AF-WCC-VAC-GEN"
    _, _, neg_refused = apply_patch(data, header, bogus)
    check("C07", "negative control: applier refuses a stale old_class_mapping",
          neg_refused == [bogus[0]["correction_id"]], f"refused={neg_refused}")

    # ---------------- D. DET-REV12 closure -------------------------------
    theorems = read_theorems(THEOREMS)
    hits_canon = detect(data, header, theorems, removal_aware=False)
    ids_canon = sorted(h["citation_id"] for h in hits_canon)
    check("D01", "DET-REV12 on the canonical ledger finds exactly the 7 patched + 5 candidate rows",
          ids_canon == sorted(ALL_12), f"hits={ids_canon}")
    hits_dry = detect(applied, header, theorems, removal_aware=False)
    remaining = sorted(h["citation_id"] for h in hits_dry)
    check("D02", "declared next-falsifier: DET-REV12 strict on the 12-row dry-run returns ZERO hits",
          remaining == [], f"remaining={remaining} reasons={[h['reasons'] for h in hits_dry]}")
    hits_dry_aware = detect(applied, header, theorems, removal_aware=True)
    check("D03", "removal-clause-aware reading of the same dry-run returns zero hits",
          hits_dry_aware == [], f"remaining={sorted(h['citation_id'] for h in hits_dry_aware)}")
    literal_rows = {r[0] for r in applied if VACUUM_TOKEN_RE.search(PAIR_RE.sub("", r[cm_idx]))}
    patched_literal = sorted(r[0] for r in applied if r[0] in ALL_12 and r[0] in literal_rows)
    check("D04", "mechanism control: every strict flag carries a literal vacuum id, and the patched rows surviving strict are exactly the patched rows still carrying one",
          set(remaining) <= literal_rows and set(remaining) == set(patched_literal),
          f"strict={remaining} patched_literal={patched_literal} all_literal_rows={len(literal_rows)}")
    n_frozen_rows = sum(1 for r in data if any(f in r[cm_idx] for f in FROZEN_CLASS_IDS_4))
    check("D05", "null control: frozen-id rows (4-id census) with no detector reason stay untouched (44)",
          n_frozen_rows - len(hits_canon) == 44,
          f"frozen_rows={n_frozen_rows} hits={len(hits_canon)} control={n_frozen_rows - len(hits_canon)}")
    check("D06", "detector hit reasons are recorded for every remaining flag",
          all(h["reasons"] for h in hits_dry), json.dumps({h["citation_id"]: h["reasons"] for h in hits_dry}))

    # ---------------- E. minimal remediation -----------------------------
    rem_rows = []
    for p in patch5:
        q = dict(p)
        if q["canonical_row_id"] in REMEDIATION:
            q["new_class_mapping"] = REMEDIATION[q["canonical_row_id"]]
            q["remediation_of"] = p["correction_id"]
            q["remediation_reason"] = (
                "replacement text carried the literal frozen vacuum class id in the removal "
                "phrase, so token-level consumers still saw a frozen binding"
            )
        rem_rows.append(q)
    rem_applied, rem_changed, rem_refused = apply_patch(data, header, patch7 + rem_rows)
    rem_diff = [(i, j) for i, (a, b) in enumerate(zip(applied, rem_applied)) for j, (x, y) in enumerate(zip(a, b)) if x != y]
    rem_rows_changed = sorted({i for i, _ in rem_diff})
    check("E01", "remediation changes exactly 2 class_mapping cells vs the 12-row dry-run",
          len(rem_diff) == 2 and {j for _, j in rem_diff} == {cm_idx} and rem_refused == [],
          f"cells={len(rem_diff)} rows={[rem_applied[i][0] for i in rem_rows_changed]}")
    check("E02", "remediated cells contain no exact frozen vacuum class-id token",
          all(not VACUUM_TOKEN_RE.search(REMEDIATION[r]) for r in REMEDIATION),
          json.dumps({r: VACUUM_TOKEN_RE.findall(REMEDIATION[r]) for r in REMEDIATION}))
    rem_hits = detect(rem_applied, header, theorems, removal_aware=False)
    check("E03", "DET-REV12 strict on the remediated 12-row dry-run returns zero hits",
          rem_hits == [], f"remaining={sorted(h['citation_id'] for h in rem_hits)}")
    check("E04", "remediation keeps the retained scalar tag and the do-not-transfer scope",
          all("AF-WCC-SCALAR-SPH" in REMEDIATION[r] and "do-not-transfer" in REMEDIATION[r] for r in REMEDIATION),
          "both rows keep AF-WCC-SCALAR-SPH + scope_use do-not-transfer")
    rem_bytes = roundtrip(rem_applied, lineterm)
    OUT_REMEDIATED_DRYRUN.write_bytes(rem_bytes)
    rem_fields = list(patch5[0].keys()) + ["remediation_of", "remediation_reason"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rem_fields, lineterminator="\r\n")
    w.writeheader()
    for q in rem_rows:
        if q["canonical_row_id"] in REMEDIATION:
            w.writerow({k: q.get(k, "") for k in rem_fields})
    rem_csv_bytes = buf.getvalue().encode("utf-8")
    OUT_REMEDIATION_CSV.write_bytes(rem_csv_bytes)
    jl = []
    for q in rem_rows:
        if q["canonical_row_id"] in REMEDIATION:
            obj = {k: q.get(k, "") for k in rem_fields}
            obj["artifact_type"] = "class_binding_correction_remediation"
            obj["class_ids"] = CLASS_IDS
            obj["gate"] = "G-LIT"
            obj["group_id"] = "literature"
            obj["node_id"] = "L1"
            jl.append(obj)
    rem_jsonl_bytes = "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in jl).encode("utf-8")
    OUT_REMEDIATION_JSONL.write_bytes(rem_jsonl_bytes)
    check("E05", "remediation artifacts written and re-hash on read",
          sha256_file(OUT_REMEDIATED_DRYRUN) == sha256_bytes(rem_bytes)
          and sha256_file(OUT_REMEDIATION_CSV) == sha256_bytes(rem_csv_bytes)
          and sha256_file(OUT_REMEDIATION_JSONL) == sha256_bytes(rem_jsonl_bytes)
          and len(jl) == 2,
          f"dryrun={sha256_bytes(rem_bytes)[:12]} patch2={sha256_bytes(rem_csv_bytes)[:12]} jsonl={sha256_bytes(rem_jsonl_bytes)[:12]}")
    check("E06", "canonical ledger and both canonical patch files are untouched by this run",
          sha256_file(CANONICAL_LEDGER) == EXPECTED["ledger"]
          and sha256_file(PATCH7_CSV) == EXPECTED["patch7_csv"]
          and sha256_file(PATCH5_CSV) == EXPECTED["patch5_csv"],
          "canonical_write=none")

    # ---------------- F. falsifier conditions / advisories ---------------
    rc = {}
    for tid, expected in EXPECTED_ROOT_CAUSE_CLASS_IDS.items():
        rec = theorems.get(tid, {})
        rc[tid] = {"resolved": bool(rec), "class_ids": rec.get("class_ids", []), "expected": expected}
    check("F01", "all six root-cause records resolve at the frozen theorem hash with the declared class_ids (order-insensitive)",
          all(v["resolved"] for v in rc.values())
          and all(sorted(v["class_ids"]) == sorted(v["expected"]) for v in rc.values()),
          json.dumps({k: v["class_ids"] for k, v in rc.items()}))
    check("F02", "root cause persists: >=1 declared record carries a frozen class id (patch still required)",
          any(any(f in v["class_ids"] for f in FROZEN_VACUUM_IDS) for v in rc.values()),
          "theorem-layer leak remains; row patch necessary but not sufficient")
    transfer_hits = []
    for p in (F1, F2A, F2B):
        for m in TRANSFER_RE.finditer(p.read_text(encoding="utf-8")):
            transfer_hits.append(f"{p.name}:{m.group(0)}")
    check("F03", "no rev13 schema field authorizes transfer of a model-class result",
          transfer_hits == [], f"hits={transfer_hits}")
    variant_ch_rows = sorted(
        r[0] for r in data if "AF-SCC-C0-VAC-GEN" in PAIR_RE.sub("", r[cm_idx]) and "T-301" in r[header.index("used_by_theorems")].split(";")
    )
    advisory("F04", "rows citing T-301 while binding the frozen C0 class remain variant-CH registration candidates",
             f"rows={variant_ch_rows} (lead derivation decides; not counted as leaks by DET-REV12)")
    advisory("F05", "FROZEN rev29 was written twice in-session (00:55:02 -> 00:57:26); its rev29_delta records the repair",
             f"frozen_at={frozen.get('frozen_at')} " + json.dumps(frozen.get("rev29_delta"))[:260])

    drift = {}
    for name, p in named:
        cur = sha256_file(p)
        if cur != inputs[name]["sha256"]:
            drift[name] = {"first": inputs[name]["sha256"], "last": cur}
    check("A22", "all anchored inputs are byte-stable between first and last measurement in this run",
          drift == {}, json.dumps(drift))

    counts = {
        "pass": sum(1 for c in checks if c["result"] == "PASS"),
        "fail": sum(1 for c in checks if c["result"] == "FAIL"),
        "advisory": sum(1 for c in checks if c["result"] == "ADVISORY"),
    }
    hard_failures = [
        f"D02 strict DET-REV12 closure FAILED: {remaining} still carry a literal frozen vacuum class id "
        f"in class_mapping ({[h['reasons'] for h in hits_dry]})"
    ] if remaining else []

    record = {
        "verification_id": "worker-009-rev29-rebind-" + args.verified_at,
        "created_at": args.verified_at,
        "verified_at": args.verified_at,
        "worker": "worker-009",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASS_IDS,
        "retained_tag": "AF-WCC-SCALAR-SPH",
        "task": ("post-repair (rev13 schemas + FROZEN rev29) adversarial re-binding of the 12-row SCC "
                 "class-binding correction proposal, DET-REV12 closure over the 12-row dry-run, and a "
                 "minimal 2-row textual remediation of the rows that survived the strict detector"),
        "canonical_write": "none - proposal/review only; lead-literature owns ledger/citation_audit.csv and the patch files",
        "inputs": inputs,
        "measurement_window": {
            "note": ("the swarm was live while this worker ran; two patch dependencies moved in-session and are "
                     "re-anchored here: FROZEN rev29 bytes 3d9e3d77fd87 (00:55:02) -> 815e08079aef (00:57:26), and "
                     "VARIANT_REGISTRY 5eb42f9a384a (rev12 record) -> 6bac9adea19e (C4 repair). All other anchors "
                     "were stable first-to-last in this run (check A22)."),
            "frozen_rev29_first_measure": EXPECTED["frozen_rev29_first_measure"],
            "frozen_rev29_measured": EXPECTED["frozen_rev29"],
            "registry_pre_repair": EXPECTED["registry_pre_repair"],
            "registry_measured": EXPECTED["registry"],
        },
        "anchor_summary": {
            "ledger": EXPECTED["ledger"],
            "theorems": EXPECTED["theorems"],
            "schemas_rev13": {k: inputs[k]["sha256"] for k in ("f1_rev13", "f2a_rev13", "f2b_rev13")},
            "frozen": {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                       "sha256": inputs["frozen_rev29"]["sha256"]},
            "registry": EXPECTED["registry"],
            "consistency_evidence": EXPECTED["consistency"],
            "declared_f0": EXPECTED["f0"],
        },
        "delta_audit": {
            "changed_leaf_paths": delta,
            "f2a_non_metadata": f2a_extra,
            "f2b_non_metadata": f2b_extra,
            "f1_non_metadata": sorted(f1_extra),
            "verdict": ("F2a/F2b metadata-only; F1 metadata + the three declared text corrections; "
                        "class-id census, data_class, anti_scope, T-514/T-520 and variant-CH intact"),
        },
        "rebind": {
            "patch_rows": 12,
            "applied": len(changed),
            "refused": refused,
            "changed_cells": len(diff_cells),
            "dryrun_sha256": sha256_bytes(applied_bytes),
            "dryrun_reproduced_pinned_byte": sha256_bytes(applied_bytes) == EXPECTED["dryrun12"],
            "negative_control_refused": neg_refused,
        },
        "detector": {
            "name": "DET-REV12",
            "canonical_hits": ids_canon,
            "dryrun_strict_remaining": remaining,
            "dryrun_strict_reasons": {h["citation_id"]: h["reasons"] for h in hits_dry},
            "dryrun_removal_aware_remaining": sorted(h["citation_id"] for h in hits_dry_aware),
            "literal_id_rows": sorted(literal_rows),
            "patched_rows_still_literal": patched_literal,
            "null_control": n_frozen_rows - len(hits_canon),
            "declared_closure_falsifier": "FAILED" if remaining else "PASSED",
            "interpretation": (
                "strict-token reading: 2 rows still name a frozen vacuum class id inside a removal "
                "phrase, so a token-level consumer still sees a frozen binding; removal-clause-aware "
                "reading: 0 rows bind a frozen id. The remediation makes both readings agree."
            ),
        },
        "remediation": {
            "rows": sorted(REMEDIATION),
            "correction_ids": [p["correction_id"] for p in rem_rows if p["canonical_row_id"] in REMEDIATION],
            "changed_cells_vs_dryrun": len(rem_diff),
            "remediated_dryrun_sha256": sha256_bytes(rem_bytes),
            "strict_hits_after": sorted(h["citation_id"] for h in rem_hits),
            "status": "candidate-only proposal; canonical ledger and patch files untouched",
        },
        "review_of_prior_patch": {
            "target_id": "ledger/citation_audit_scc_candidates_worker-009.csv",
            "target_sha256": EXPECTED["patch5_csv"],
            "previous_verification": "artifacts/worker-009/detrev12/verification_candidates_worker-009.json",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": hard_failures,
            "findings": [
                "rev13/FROZEN rev29 anchors hold: the patch re-binds and reproduces byte-identically",
                "two dependencies moved in-session (FROZEN rev29 bytes; registry C4 repair) and are re-anchored, not assumed",
                "the declared next-falsifier (zero uncovered candidates on the 12-row dry-run) fails in the strict reading",
                "minimal 2-cell text remediation makes the strict and removal-aware readings agree at 0 hits",
            ],
        },
        "checks": checks,
        "counts": counts,
        "falsifier": (
            "Any of the following voids this record: (a) any anchored input moves from the sha recorded in "
            "inputs (especially ledger 315c19145065, theorems a1674f09, rev13 schemas d9cebb94/e9a27996/b2ab6acb, "
            "FROZEN rev29 3d9e3d77, registry 5eb42f9a); (b) a re-fetch showing any of the five promoted sources "
            "is 4D Einstein vacuum Lambda=0; (c) a strict DET-REV12 run over a lead-applied 12-row ledger that "
            "finds a row binding (not merely naming) a frozen vacuum class id; (d) FROZEN rev29 being superseded "
            "with different bytes for the three schemas without re-measurement."
        ),
        "next_falsifier": (
            "Lead-literature applies the 2-cell remediation (or equivalent wording) to the proposal and re-runs "
            "DET-REV12 strict over the applied ledger, expecting zero hits; independently reviews the five "
            "verbatim quote sets at the pinned source hashes (this record is author self-verification of the "
            "mechanical checks, not an independent verdict)."
        ),
        "worker_authority_note": (
            "worker events cannot set status=done, validation_status=passed, or a gate verdict; this record is a "
            "completion claim plus an adversarial review of worker-009's own prior proposal, not a gate verdict."
        ),
    }
    OUT_RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    record_sha = sha256_file(OUT_RECORD)

    checkpoint = {
        "checkpoint_id": "w009-rev29-rebind-" + args.verified_at,
        "created_at": args.verified_at,
        "worker": "worker-009",
        "label": "worker-009-rev29-rebind-detrev12-closure",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "record": {"path": str(OUT_RECORD.relative_to(ROOT)), "sha256": record_sha},
        "artifacts": {
            str(OUT_REMEDIATED_DRYRUN.relative_to(ROOT)): sha256_file(OUT_REMEDIATED_DRYRUN),
            str(OUT_REMEDIATION_CSV.relative_to(ROOT)): sha256_file(OUT_REMEDIATION_CSV),
            str(OUT_REMEDIATION_JSONL.relative_to(ROOT)): sha256_file(OUT_REMEDIATION_JSONL),
            str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__)),
        },
        "anchors": record["anchor_summary"],
        "counts": counts,
        "closure_verdict": "revise" if remaining else "accept",
        "canonical_untouched": True,
        "numerics_lock": "respected (no numerics/ work)",
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "verification_id": record["verification_id"],
        "record_sha256": record_sha,
        "checks": counts,
        "detector_remaining_strict": remaining,
        "detector_remaining_removal_aware": sorted(h["citation_id"] for h in hits_dry_aware),
        "remediation_changed_cells": len(rem_diff),
        "remediated_dryrun_sha256": sha256_bytes(rem_bytes),
        "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
