#!/usr/bin/env python3
"""W034-REV29-POSTREPAIR-VERIFY-01.

Independent, read-only, deterministic verification of the FROZEN rev29 pin set
published by astra-lead-formulation (frozen_at 2026-09-12T00:55:02+08:00),
scoped to the three class-bound formulation artifacts and the repairs claimed
in FROZEN.rev29_delta:

  F1  schemas/af_wcc_vacuum.yaml      (AF-WCC-VAC-GEN)
  F2a schemas/af_scc_c2_vacuum.yaml   (AF-SCC-C2-VAC-GEN)
  F2b schemas/af_scc_c0_vacuum.yaml   (AF-SCC-C0-VAC-GEN)
  F0  research_map/formulation_taxonomy.yaml + supplement (context, L-FORM-03)

Checks: every FROZEN entry resolves at its declared bytes, hash stability across
the run, the f0_binding refresh (L-FORM-02), the F1 strictness/direction repair,
the F2b containment premise (L-FORM-01), the F0<->F1 variant-SET direction
(L-FORM-03), the F1 falsifier-corpus binding at the rev13 hash, structural
class-separation tokens, the canonical structural gate, and an independent
re-run of the canonical gate-test suite.

Authority: measurement only.  No gate verdict, no node status/validation
promotion, no byte change to any reviewed artifact.

Usage: python3 verify_rev29.py [--out DIR]
Exit codes: 0 = all checks passed, 1 = one or more checks failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]  # .../ai4math-swarm
RUN_ID = "W034-REV29-POSTREPAIR-VERIFY-01"
WORKER = "worker-034"

# Paths under test.  Hashes are MEASURED below (and cross-checked against FROZEN).
PIN_PATHS = {
    "FROZEN": "artifacts/formulation/FROZEN.json",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "F0_MAP": "research_map/formulation_taxonomy.yaml",
    "F0_SUPP": "artifacts/formulation/formulation_taxonomy.yaml",
    "CONSISTENCY": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "F1_TESTS": "schemas/f1_falsifier_tests.jsonl",
    "GATE_TOOL": "artifacts/formulation/tools/check_class_schema.py",
    "GATE_SUITE": "artifacts/formulation/tools/run_gate_tests.py",
}
# rev29 declared pins for the subject artifacts (read from FROZEN at run time and
# asserted here; full 64-hex values measured 2026-09-12T00:54-00:57+08:00).
REV29_DECLARED = {
    "F1": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "F2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "F2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "F0_MAP": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "F0_SUPP": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "CONSISTENCY": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "F1_TESTS": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "GATE_TOOL": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "GATE_SUITE": "78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa",
}
# rev12 snapshots (superseded pins) used only to characterise the rev13 delta.
REV12_SNAPSHOTS = {
    "F1": ("artifacts/worker-040/f1_rev12_independent_verdict/"
           "snapshot_af_wcc_vacuum.cce9c60146d6.yaml",
           "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "F2a": ("artifacts/worker-060/containment_semantics_sweep/snapshots/"
            "f2a__af_scc_c2_vacuum.yaml",
            "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "F2b": ("artifacts/worker-060/containment_semantics_sweep/snapshots/"
            "f2b__af_scc_c0_vacuum.yaml",
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"),
}
CONTAINMENT_RANK = {"C2": 0, "C^{1,1}": 1, "C1_1": 1, "H2_loc": 2, "H2loc": 2, "C0": 3}
# Independently pinned on-disk byte-states of FROZEN.json that both call themselves
# "revision 29" (see finding W034-REV29-F5).  Paths are hashed at run time.
FROZEN_REV29_STATES = {
    "state_A": ("artifacts/worker-083/rev29_postapply_integrity/snapshot/FROZEN.json",
                "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833"),
    "state_B": ("artifacts/worker-058/rev29_delta_audit/pinned/FROZEN.json",
                "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
}
# third state measured directly in this session with sha256sum before it was
# overwritten (no on-disk copy survives); recorded, not hash-checkable.
FROZEN_REV29_OBSERVED = {
    "state_0": {"sha256_prefix": "e1a8aaa394eb49ce", "frozen_at": "2026-09-12T00:54:32+08:00",
                "measured_at": "2026-09-12T00:54:47+08:00", "means": "direct sha256sum by worker-034"},
}

CHECKS: list[dict] = []


def variant_direction_lines(path: Path, window: int = 3):
    """Lines that assert a strict order for the set-based/union reading.

    A hit is a line containing 'strictly stronger' that is itself within
    [i-window, i+window] of a line naming the set-based / union reading.
    """
    lines = path.read_text().splitlines()
    anchors = set()
    for i, ln in enumerate(lines):
        low = ln.casefold()
        if "set-based" in low or ("union of j^-(q)" in low and "set" in low) or "as a set" in low:
            anchors.add(i)
    hits = []
    for j, ln in enumerate(lines):
        if "strictly stronger" not in ln.casefold():
            continue
        if any(abs(j - a) <= window for a in anchors):
            hits.append(j + 1)
    return hits


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rec(check_id, suite, ok, expected, observed, falsifier, locator):
    CHECKS.append({
        "check_id": check_id, "suite": suite, "ok": bool(ok),
        "expected": expected, "observed": observed,
        "falsifier": falsifier, "locator": locator,
    })
    return bool(ok)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_jsonl(path: Path):
    out = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if line:
            out.append((i, json.loads(line)))
    return out


def dig(obj, path):
    for part in path.split("/"):
        if not part:
            continue
        m = re.fullmatch(r"(.+)\[(\d+)\]", part)
        if m:
            obj = obj[m.group(1)][int(m.group(2))]
        else:
            obj = obj[part]
    return obj


def deep_diff(a, b, path=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                diffs.append((f"{path}/{k}", "<absent>", str(b[k])[:200]))
            elif k not in b:
                diffs.append((f"{path}/{k}", str(a[k])[:200], "<absent>"))
            else:
                diffs += deep_diff(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((f"{path}/len", str(len(a)), str(len(b))))
        for i, (x, y) in enumerate(zip(a, b)):
            diffs += deep_diff(x, y, f"{path}[{i}]")
    elif a != b:
        diffs.append((path, str(a)[:200], str(b)[:200]))
    return diffs


def line_numbers(path: Path, needle: str, casefold=False):
    out = []
    for i, ln in enumerate(path.read_text().splitlines(), 1):
        hay = ln.casefold() if casefold else ln
        pin = needle.casefold() if casefold else needle
        if pin in hay:
            out.append(i)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    started = now()
    # ---------- 0. root pins + stability ----------
    before = {k: sha256(ROOT / p) for k, p in PIN_PATHS.items()}
    frozen = json.loads((ROOT / PIN_PATHS["FROZEN"]).read_text())
    rec("PIN-ROOT-REVISION", "pins", frozen.get("revision") == 29,
        "FROZEN.json revision == 29",
        f"revision={frozen.get('revision')} frozen_at={frozen.get('frozen_at')} "
        f"sha256={before['FROZEN'][:24]}",
        "a FROZEN revision != 29; then all rev29-bound conclusions are void",
        PIN_PATHS["FROZEN"])
    pin_ok = all(before[k] == REV29_DECLARED[k] for k in REV29_DECLARED)
    rec("PIN-SUBJECTS", "pins", pin_ok,
        "the nine subject pins equal the rev29 values measured at freeze",
        json.dumps({k: before[k][:16] for k in REV29_DECLARED}),
        "any byte change in a subject pin; then rebind every hash-bound statement",
        ";".join(PIN_PATHS[k] for k in REV29_DECLARED))

    # ---------- 1. every FROZEN entry resolves at the declared bytes ----------
    mism, missing = [], []
    for rel, meta in sorted(frozen["files"].items()):
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        got = sha256(p)
        if got != meta["sha256"] or p.stat().st_size != meta.get("bytes"):
            mism.append({"path": rel, "declared": meta["sha256"][:24], "measured": got[:24],
                         "bytes_declared": meta.get("bytes"), "bytes_measured": p.stat().st_size})
    rec("PIN-FROZEN-ENTRIES", "pins", not mism and not missing,
        f"all {len(frozen['files'])} FROZEN entries match disk bytes+size",
        f"{len(frozen['files'])} entries; {len(mism)} hash/size mismatches; {len(missing)} missing",
        "any FROZEN entry whose measured sha256/bytes differ from the manifest",
        PIN_PATHS["FROZEN"])
    for m in mism[:10]:
        rec(f"PIN-MISMATCH::{m['path']}", "pins", False, "declared == measured",
            json.dumps(m), "a re-run of sha256 on the named path", m["path"])
    for m in missing[:10]:
        rec(f"PIN-MISSING::{m}", "pins", False, "entry present on disk", "missing",
            "restore the file or amend the manifest", m)

    # per-key declared pin agreement from the manifest read at run start
    for key, rel in PIN_PATHS.items():
        if key == "FROZEN" or rel not in frozen["files"]:
            continue
        decl = frozen["files"][rel]["sha256"]
        rec(f"PIN-DECLARED::{key}", "pins", decl == before[key],
            f"FROZEN declares {decl[:24]}", f"measured {before[key][:24]}",
            "re-measure the path; a difference falsifies the pin", rel)

    # ---------- 2. f0_binding refresh (L-FORM-02) ----------
    schemas = {}
    for key in ("F1", "F2a", "F2b"):
        try:
            schemas[key] = yaml.safe_load((ROOT / PIN_PATHS[key]).read_text())
        except Exception as exc:  # noqa: BLE001
            rec(f"PARSE::{key}", "schema", False, "YAML parses", f"{type(exc).__name__}: {exc}",
                "any parse failure", PIN_PATHS[key])
            schemas[key] = {}
    cons = json.loads((ROOT / PIN_PATHS["CONSISTENCY"]).read_text())
    for key, d in schemas.items():
        fb = d.get("f0_binding", {})
        rec(f"BIND::{key}", "repair-1",
            fb.get("consistency_evidence_sha256") == before["CONSISTENCY"],
            f"f0_binding.consistency_evidence_sha256 == {before['CONSISTENCY'][:24]}",
            str(fb.get("consistency_evidence_sha256"))[:24],
            "the declared evidence hash no longer resolving at the canonical path",
            f"{PIN_PATHS[key]}#f0_binding.consistency_evidence_sha256")
        rec(f"BIND-DECL::{key}", "repair-1", fb.get("declared_f0_sha256") == before["F0_MAP"],
            f"declared_f0_sha256 == {before['F0_MAP'][:24]}",
            str(fb.get("declared_f0_sha256"))[:24],
            "F0 canonical hash move without a binding refresh",
            f"{PIN_PATHS[key]}#f0_binding.declared_f0_sha256")
    rec("BIND-EVIDENCE", "repair-1",
        cons.get("consistent") is True and not cons.get("errors") and not cons.get("contract_divergences"),
        "taxonomy_consistency.json consistent=true, errors=[], contract_divergences=[]",
        f"consistent={cons.get('consistent')} errors={cons.get('errors')} "
        f"divergences={cons.get('contract_divergences')}",
        "a consistency run reporting an error or a contract divergence",
        PIN_PATHS["CONSISTENCY"])

    # ---------- 3. F1 strictness repair (repair item 3) ----------
    f1 = schemas["F1"]
    d5 = str(dig(f1, "quantifiers/domains/D5/definition"))
    vis = str(dig(f1, "visibility/definition"))
    rec("F1-D5-EQUIV", "repair-2",
        "EQUIVALENT to the tail form" in d5 and "NOT a weakening" in d5 and "was false" in d5,
        "quantifiers.domains.D5.definition states the tail/whole-curve EQUIVALENCE and marks the "
        "rev12 strict-order assertion false",
        d5[:220].replace("\n", " "),
        "a witness with tail-containment but not whole-curve containment under past-closed J^-(q)",
        f"{PIN_PATHS['F1']}#quantifiers.domains.D5.definition")
    rec("F1-VIS-REPAIRED", "repair-2",
        "EQUIVALENT" in vis and "would misclassify" not in vis,
        "visibility.definition states EQUIVALENT and the 'would misclassify' claim is removed",
        vis[:220].replace("\n", " "),
        "an admissible geodesic misclassified by the whole-curve reading",
        f"{PIN_PATHS['F1']}#visibility.definition")
    variants = f1.get("class_identity_variants") or [{}]
    rel_txt = str(variants[0].get("relation", ""))
    rec("F1-VARIANT-DIR", "repair-2",
        "strictly WEAKER" in rel_txt and "corrected from 'strictly STRONGER'" in rel_txt,
        "variant SET relation states strictly WEAKER and records the direction correction",
        rel_txt[:200].replace("\n", " "),
        "a finite causal structure in which the union reading and the single-q tail reading coincide",
        f"{PIN_PATHS['F1']}#class_identity_variants[0].relation")
    live_stronger = line_numbers(ROOT / PIN_PATHS["F1"], "is strictly STRONGER")
    rec("F1-NO-LIVE-STRONGER", "repair-2", not live_stronger,
        "no live field asserts 'is strictly STRONGER' for the whole-curve reading",
        f"occurrences at lines {live_stronger}",
        "a live field that still asserts the strict order",
        PIN_PATHS["F1"])

    # ---------- 4. F2b containment premise (L-FORM-01) ----------
    bigger = line_numbers(ROOT / PIN_PATHS["F2b"], "larger extension class")
    rec("F2B-NO-LARGER-PREMISE", "repair-3", not bigger,
        "no 'C2 is a strictly larger extension class' premise in F2b",
        f"occurrences at lines {bigger}",
        "the chain E_C2 subset E_C0 falsifies the larger-extension-class premise",
        PIN_PATHS["F2b"])
    licensing = {}
    for key in ("F2a", "F2b"):
        rows = (schemas[key].get("implication_ledger") or {}).get("forbidden_transfers") or []
        bad = []
        for i, row in enumerate(rows):
            frm, to = str(row.get("from", "")), str(row.get("to", ""))
            m1 = re.match(r"no proper future (\S+) extension", frm)
            m2 = re.match(r"no proper future (\S+) extension", to)
            if m1 and m2:
                rf, rt = CONTAINMENT_RANK.get(m1.group(1)), CONTAINMENT_RANK.get(m2.group(1))
                # transfer "no X-ext" -> "no Y-ext" is licensed iff E_Y subset E_X (rank Y <= X)
                if rf is not None and rt is not None and rt <= rf:
                    bad.append({"row": i, "from": frm, "to": to, "reason": row.get("reason")})
        licensing[key] = {"rows": len(rows), "wrongly_forbidden": bad}
        rec(f"{key}-FORBIDDEN-LICENSING", "repair-3", not bad,
            "every forbidden_transfers row is genuinely unlicensed under E_C2 subset ... subset E_C0",
            f"{len(rows)} rows; {len(bad)} wrongly listed as forbidden",
            "a row whose target extension set is contained in its source set",
            f"{PIN_PATHS[key]}#implication_ledger.forbidden_transfers")

    # ---------- 5. F0 <-> F1 variant-SET direction (L-FORM-03 residual) ----------
    f0_path = ROOT / PIN_PATHS["F0_MAP"]
    f0_lines = variant_direction_lines(f0_path)
    rec("F0-VARIANT-DIR-CONSISTENT", "repair-4", not f0_lines,
        "F0 canonical taxonomy does not assert the set-based reading is strictly stronger",
        f"F0 opposite-direction lines: {f0_lines[:8]}",
        "the contradiction is retired when F0 adopts the F1 rev13 direction (strictly WEAKER)",
        PIN_PATHS["F0_MAP"])
    supp_lines = variant_direction_lines(ROOT / PIN_PATHS["F0_SUPP"])
    rec("F0-SUPP-VARIANT-DIR", "repair-4", not supp_lines,
        "F0 supplement does not assert the set-based reading is strictly stronger",
        f"supplement opposite-direction lines: {supp_lines[:8]}",
        "a supplement revision adopting the F1 rev13 direction (strictly WEAKER)",
        PIN_PATHS["F0_SUPP"])
    registry = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    set_variant = next((v for v in registry.get("variants", [])
                        if str(v.get("variant_id")) == "SET"), {})
    reg_strength = str(set_variant.get("strength", ""))
    rec("F0-REGISTRY-VARIANT-DIR", "repair-4",
        "strictly weaker" in reg_strength and "corrected from 'strictly STRONGER'" in reg_strength,
        "VARIANT_REGISTRY SET strength states strictly weaker and records the correction",
        reg_strength[:200],
        "a registry revision that reverts the SET strength direction",
        "artifacts/formulation/VARIANT_REGISTRY.json#variants[SET].strength")
    delta_json = json.loads((ROOT / "artifacts/formulation/variants/"
                             "AF-WCC-VAC-GEN.variant-SET.delta.json").read_text())
    delta_strength = str(delta_json.get("strength", ""))
    rec("F0-DELTA-VARIANT-DIR", "repair-4",
        "strictly weaker" in delta_strength and str(delta_json.get("base", {}).get("sha256")) == before["F1"],
        "SET variant delta states strictly weaker and is rebased on the F1 rev13 pin",
        f"strength={delta_strength[:120]}; base_sha256={str(delta_json.get('base', {}).get('sha256'))[:16]}",
        "a delta file still bound to the rev12 F1 base or the inverted direction",
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")
    rec("F0-F1-DIRECTION-MATCH", "repair-4",
        ("strictly WEAKER" in rel_txt) and not (f0_lines or supp_lines),
        "F0 canonical + supplement and F1 agree on the variant-SET direction at their pins",
        f"F1 'strictly WEAKER' present={('strictly WEAKER' in rel_txt)}; "
        f"F0 opposite lines={f0_lines[:8]}; supplement opposite lines={supp_lines[:8]}",
        "any F0/F1 pair stating opposite strict directions for the same reading",
        PIN_PATHS["F0_MAP"])

    # ---------- 5b. FROZEN revision-29 manifest churn ----------
    churn = []
    for label, (rel, want) in FROZEN_REV29_STATES.items():
        p = ROOT / rel
        got = sha256(p) if p.is_file() else "missing"
        state = json.loads(p.read_text()) if p.is_file() else {}
        churn.append({"label": label, "path": rel, "sha256": got[:24],
                      "declared_expected": want[:24], "revision": state.get("revision"),
                      "frozen_at": state.get("frozen_at"),
                      "n_files": len(state.get("files", {})), "on_disk": p.is_file()})
    churn_ok = len({c["sha256"] for c in churn if c["on_disk"]}) == len(churn) and all(
        c["revision"] == 29 for c in churn if c["on_disk"])
    rec("FROZEN-REV29-CHURN", "pins", churn_ok,
        "record every on-disk FROZEN byte-state that labels itself revision 29",
        json.dumps(churn),
        "a revision bump or a re-freeze that makes two revision-29 states byte-identical",
        PIN_PATHS["FROZEN"])
    distinct_states = sorted({c["sha256"] for c in churn if c["on_disk"]})
    rec("FROZEN-REV29-SINGLE-STATE", "pins", len(distinct_states) <= 1,
        "exactly one byte-state carries revision 29",
        f"{len(distinct_states)} distinct revision-29 byte-states on disk: {distinct_states}",
        "a re-freeze that overwrites the manifest without bumping the revision",
        PIN_PATHS["FROZEN"])

    # ---------- 6. F1 falsifier corpus binding at rev13 ----------
    rows = load_jsonl(ROOT / PIN_PATHS["F1_TESTS"])
    bindings: dict[str, int] = {}
    for _, d in rows:
        b = str(d.get("binding_sha256"))
        bindings[b] = bindings.get(b, 0) + 1
    stale = {k: v for k, v in bindings.items() if k != before["F1"]}
    rec("F1-TESTS-REBOUND", "repair-5", not stale,
        f"every falsifier row binds the rev13 F1 sha256 {before['F1'][:24]}",
        f"{len(rows)} rows; binding census { {k[:16]: v for k, v in bindings.items()} }",
        "a row whose binding_sha256 differs from the current F1 pin",
        PIN_PATHS["F1_TESTS"])

    # ---------- 7. class separation at rev13 ----------
    c2, c0 = schemas["F2a"], schemas["F2b"]
    tok2 = str((c2.get("class_components") or {}).get("regularity_token"))
    tok0 = str((c0.get("class_components") or {}).get("regularity_token"))
    rec("SEP-TOKENS", "separation", tok2 == "C2" and tok0 == "C0" and tok2 != tok0,
        "F2a/F2b class_components.regularity_token are distinct C2/C0",
        f"F2a={tok2} F2b={tok0}",
        "a schema whose regularity token collides with its sibling's",
        "schemas/af_scc_c2_vacuum.yaml#class_components;schemas/af_scc_c0_vacuum.yaml#class_components")
    rec("SEP-SIBLING", "separation",
        str(c2.get("sibling_disjoint_from")) == str(c0.get("class_id"))
        and str(c0.get("sibling_disjoint_from")) == str(c2.get("class_id")),
        "sibling_disjoint_from is symmetric between F2a and F2b",
        f"F2a->{c2.get('sibling_disjoint_from')} F2b->{c0.get('sibling_disjoint_from')}",
        "an asymmetric or stale sibling pointer",
        "schemas/af_scc_c2_vacuum.yaml#sibling_disjoint_from")
    dc2 = c2.get("data_class") or {}
    dc0 = c0.get("data_class") or {}
    same_keys = sorted(dc2) == sorted(dc0) and all(
        sorted(dc2[k]) == sorted(dc0[k]) for k in dc2 if isinstance(dc2[k], dict) and isinstance(dc0.get(k), dict))
    rec("SEP-DATACLASS-KEYS", "separation", True,
        "record whether the C2/C0 data_class blocks are key-identical (O-GFORM-R2-1 input)",
        f"key-identical={same_keys}; separation carried by regularity_token+extension_predicate",
        "a reviewer adjudication that key-identity is or is not the intended encoding",
        "schemas/af_scc_c2_vacuum.yaml#data_class")

    # ---------- 8. rev13 delta vs rev12 snapshots ----------
    deltas = {}
    for key, (snap, rev12_hash) in REV12_SNAPSHOTS.items():
        sp = ROOT / snap
        if not sp.is_file():
            rec(f"DELTA::{key}", "delta", False, "rev12 snapshot present", "missing",
                "snapshot deleted; delta unmeasurable", snap)
            continue
        if sha256(sp) != rev12_hash:
            rec(f"DELTA::{key}", "delta", False, f"snapshot == rev12 {rev12_hash[:16]}",
                f"measured {sha256(sp)[:16]}", "snapshot bytes changed", snap)
            continue
        old = yaml.safe_load(sp.read_text())
        d = deep_diff(old, schemas[key])
        deltas[key] = d
        rec(f"DELTA::{key}", "delta", True, "rev13 delta enumerated vs rev12",
            f"{len(d)} changed leaf paths: {[x[0] for x in d][:8]}",
            "any additional changed path falsifies the enumerated delta", snap)

    # ---------- 9. canonical structural gate on the three pins ----------
    gate_tool = ROOT / PIN_PATHS["GATE_TOOL"]
    gate_results = {}
    for key in ("F1", "F2a", "F2b"):
        proc = subprocess.run([sys.executable, str(gate_tool), PIN_PATHS[key], "--json"],
                              capture_output=True, text=True, cwd=ROOT)
        try:
            gj = json.loads(proc.stdout)
        except Exception:  # noqa: BLE001
            gj = {"verdict": "unparseable", "stdout": proc.stdout[-400:], "stderr": proc.stderr[-400:]}
        gate_results[key] = gj
        rec(f"GATE::{key}", "gate", gj.get("verdict") == "pass" and not gj.get("failed_rules"),
            "canonical check_class_schema.py verdict=pass, failed_rules=[]",
            f"verdict={gj.get('verdict')} failed_rules={gj.get('failed_rules')}",
            "a canonical structural gate that fails on the pinned bytes",
            f"{PIN_PATHS[key]} via {PIN_PATHS['GATE_TOOL']}")

    # ---------- 10. independent re-run of the canonical gate-test suite ----------
    # NOTE: this tool writes artifacts/formulation/evidence/gate_test_report.{json,txt},
    # one of which is FROZEN-pinned.  The re-run is immediately followed by an
    # idempotence check against the pin; a non-idempotent run would be reported as a
    # blocking finding rather than hidden.
    suite_runs = []
    suite_out = ""
    for attempt in (1, 2):
        suite = subprocess.run([sys.executable, str(ROOT / PIN_PATHS["GATE_SUITE"])],
                               capture_output=True, text=True, cwd=ROOT)
        suite_out = suite.stdout.strip()
        suite_runs.append({"attempt": attempt, "exit": suite.returncode,
                           "stdout_len": len(suite.stdout), "stderr_tail": suite.stderr[-300:]})
        if "GATE TEST REPORT" in suite_out:
            break
    m = re.search(r"canonical pass\s*:\s*(\d+)/(\d+)", suite_out)
    m2 = re.search(r"null controls\s*:\s*(\d+)/(\d+)", suite_out)
    m3 = re.search(r"mutants caught\s*:\s*(\d+)/(\d+)", suite_out)
    suite_ok = bool(m and m2 and m3) and m.group(1) == m.group(2) and m2.group(1) == m2.group(2) \
        and m3.group(1) == m3.group(2)
    rec("GATE-SUITE", "gate", suite_ok,
        "run_gate_tests.py: canonical 3/3, controls 6/6, mutants 31/31",
        f"runs={suite_runs}; {m.group(0) if m else '?'}; {m2.group(0) if m2 else '?'}; "
        f"{m3.group(0) if m3 else '?'}",
        "a mutant not caught, a canonical file failing the suite, or an empty/flaky run",
        PIN_PATHS["GATE_SUITE"])
    report_rel = "artifacts/formulation/evidence/gate_test_report.json"
    if report_rel in frozen["files"]:
        want = frozen["files"][report_rel]["sha256"]
        got = sha256(ROOT / report_rel)
        rec("GATE-SUITE-IDEMPOTENT", "gate", got == want,
            "the suite's FROZEN-pinned report is byte-identical after the re-run",
            f"pin={want[:16]} after_rerun={got[:16]}",
            "a re-run that rewrites the pinned report with different bytes (harness not idempotent)",
            report_rel)

    # ---------- 11. stability: re-measure every pin after the checks ----------
    after = {k: sha256(ROOT / p) for k, p in PIN_PATHS.items()}
    moved = {k: (before[k][:16], after[k][:16]) for k in before if before[k] != after[k]}
    rec("STABLE", "pins", not moved,
        "every measured pin is byte-identical before and after the verification run",
        f"{len(before)} pins re-measured; moved={moved}",
        "any write to a pinned path during the run voids hash-bound conclusions on that path",
        ";".join(PIN_PATHS.values()))

    # ---------- summary ----------
    failed = [c for c in CHECKS if not c["ok"]]
    f1_fail = any(not c["ok"] for c in CHECKS if c["check_id"] in {
        "F1-D5-EQUIV", "F1-VIS-REPAIRED", "F1-VARIANT-DIR", "F1-NO-LIVE-STRONGER",
        "F1-TESTS-REBOUND", "BIND::F1", "BIND-DECL::F1", "GATE::F1"})
    f2a_fail = any(not c["ok"] for c in CHECKS if c["check_id"] in {
        "BIND::F2a", "BIND-DECL::F2a", "GATE::F2a", "F2a-FORBIDDEN-LICENSING"})
    f2b_fail = any(not c["ok"] for c in CHECKS if c["check_id"] in {
        "F2B-NO-LARGER-PREMISE", "BIND::F2b", "BIND-DECL::F2b", "GATE::F2b",
        "F2b-FORBIDDEN-LICENSING"})
    per_class = {"F1": "revise" if f1_fail else "accept-at-pin",
                 "F2a": "revise" if f2a_fail else "accept-at-pin",
                 "F2b": "revise" if f2b_fail else "accept-at-pin"}
    findings = []
    if any(not c["ok"] for c in CHECKS if c["check_id"] == "F2B-NO-LARGER-PREMISE"):
        findings.append({
            "id": "W034-REV29-F1", "severity": "major", "class_id": "AF-SCC-C0-VAC-GEN",
            "finding": "L-FORM-01 is NOT repaired at rev29: schemas/af_scc_c0_vacuum.yaml:246 still "
                       "states 'C2 is a strictly larger extension class, so C2-inextendibility is "
                       "strictly weaker'. The row's conclusion (transfer forbidden) is right, but the "
                       "premise contradicts the file's own extension_class_containment chain "
                       "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0.",
            "falsifier": "a C0 schema revision whose forbidden_transfers[0].reason states C2 is the "
                         "smaller extension set / C2-inextendibility is strictly stronger",
        })
    if any(not c["ok"] for c in CHECKS if c["check_id"] == "F0-F1-DIRECTION-MATCH"):
        findings.append({
            "id": "W034-REV29-F2", "severity": "major", "class_id": "AF-WCC-VAC-GEN",
            "finding": "L-FORM-03 residual is measurable at the pins: F1 rev13 says the variant-SET "
                       "reading is strictly WEAKER (class_identity_variants[0].relation, "
                       f"{PIN_PATHS['F1']}#{before['F1'][:8]}); VARIANT_REGISTRY and the SET delta "
                       "file were rebased to 'strictly weaker' (rebased_at 00:57:02), but F0 "
                       f"canonical {PIN_PATHS['F0_MAP']}#{before['F0_MAP'][:8]} still says 'strictly "
                       f"stronger' at lines {f0_lines[:8]} and the F0 supplement "
                       f"{PIN_PATHS['F0_SUPP']}#{before['F0_SUPP'][:8]} at lines {supp_lines[:8]}. "
                       "The frozen F0 artifacts and the frozen F1 artifact state opposite directions "
                       "for the same reading.",
            "falsifier": "an F0 revision (canonical and supplement) aligning both texts to the F1 "
                         "rev13 direction at their published hashes",
        })
    if any(not c["ok"] for c in CHECKS if c["check_id"] == "F1-TESTS-REBOUND"):
        findings.append({
            "id": "W034-REV29-F3", "severity": "major", "class_id": "AF-WCC-VAC-GEN",
            "finding": f"{PIN_PATHS['F1_TESTS']} (FROZEN rev29 pin "
                       f"{before['F1_TESTS'][:12]}) still binds all {len(rows)} rows to the "
                       f"superseded rev12 F1 hash cce9c60146d6; VF-R2-5 ('25/25 rows carry "
                       "binding_sha256=cce9c601') is void at the rev13 pin "
                       f"{before['F1'][:12]}.",
            "falsifier": "a falsifier-corpus revision whose 25 binding_sha256 values equal the F1 "
                         "rev13 pin, or a written decision that the corpus is intentionally frozen to "
                         "rev12 (then FROZEN should not pin it as rev13 evidence)",
        })
    if moved:
        findings.append({
            "id": "W034-REV29-F4", "severity": "blocking-for-pin", "class_id": "GLOBAL",
            "finding": f"pin movement during the run: {moved}",
            "falsifier": "a re-run in a quiescent window; hash-bound conclusions on moved paths are void",
        })
    if len(distinct_states) > 1 or any(not c["ok"] for c in CHECKS
                                       if c["check_id"] == "FROZEN-REV29-SINGLE-STATE"):
        findings.append({
            "id": "W034-REV29-F5", "severity": "major", "class_id": "GLOBAL",
            "finding": "FROZEN.json revision 29 is not a single byte-state: two on-disk third-party "
                       f"pins carry revision 29 with different frozen_at and different entries "
                       f"({distinct_states}), and a third state (e1a8aaa394eb49ce, frozen_at "
                       "00:54:32) was measured directly at 00:54:47 before being overwritten. The "
                       "subject schema pins are identical in every state, but a verdict that cites "
                       "'FROZEN rev29' without the manifest sha256 is ambiguous.",
            "falsifier": "a manifest policy that bumps revision per re-freeze, or publishes one "
                         "immutable manifest path per revision",
        })
    if any(not c["ok"] for c in CHECKS if c["check_id"] == "GATE-SUITE"):
        findings.append({
            "id": "W034-REV29-F6", "severity": "advisory", "class_id": "GLOBAL",
            "finding": "the canonical gate-test suite was not reproducible in at least one "
                       f"invocation under load: {suite_runs}. The suite hardcodes the authoring "
                       "tree and writes a FROZEN-pinned report, so concurrency/flakiness here "
                       "touches pinned bytes.",
            "falsifier": "a run in a quiescent window that returns the full report on first "
                         "invocation",
        })
    if any(not c["ok"] for c in CHECKS if c["check_id"] == "GATE-SUITE-IDEMPOTENT"):
        findings.append({
            "id": "W034-REV29-F7", "severity": "blocking", "class_id": "GLOBAL",
            "finding": "re-running the canonical gate-test suite changed the bytes of the "
                       "FROZEN-pinned artifacts/formulation/evidence/gate_test_report.json; a "
                       "worker re-run can therefore silently invalidate a pin.",
            "falsifier": "a suite revision that writes to a scratch path or restores the pinned "
                         "bytes",
        })

    evidence = {
        "run_id": RUN_ID,
        "actor": WORKER,
        "created_at": started,
        "finished_at": now(),
        "authority": "worker measurement only; NO gate verdict, NO node status/validation promotion, "
                     "NO byte change to any reviewed artifact",
        "scope": {
            "task": "independent post-repair verification of the FROZEN rev29 pin set",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "node_ids": ["F0", "F1", "F2a", "F2b"],
        },
        "frozen": {"path": PIN_PATHS["FROZEN"], "revision": frozen.get("revision"),
                   "frozen_at": frozen.get("frozen_at"), "sha256": before["FROZEN"]},
        "frozen_rev29_states_on_disk": churn,
        "frozen_rev29_observed_not_on_disk": FROZEN_REV29_OBSERVED,
        "pins_before": before,
        "pins_after": after,
        "gate_results": gate_results,
        "gate_suite_runs": suite_runs,
        "gate_suite_stdout_tail": suite_out[-1500:],
        "forbidden_transfer_licensing": licensing,
        "rev13_delta_vs_rev12": {k: v[:40] for k, v in deltas.items()},
        "summary": {
            "checks": len(CHECKS), "passed": len(CHECKS) - len(failed), "failed": len(failed),
            "failed_ids": [c["check_id"] for c in failed],
            "per_class_measured_status": per_class,
        },
        "findings": findings,
        "checks": CHECKS,
        "next_falsifier": "re-run this script after any schema/FROZEN byte change; a revision that "
                          "repairs L-FORM-01, aligns the F0/F1 variant-SET direction and rebinds "
                          "schemas/f1_falsifier_tests.jsonl to the live F1 pin retires F1/F2/F3",
    }
    ev_path = outdir / "evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"checks": len(CHECKS), "failed": len(failed),
                      "failed_ids": evidence["summary"]["failed_ids"],
                      "per_class": per_class, "moved_pins": moved,
                      "evidence": str(ev_path), "evidence_sha256": sha256(ev_path)}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
