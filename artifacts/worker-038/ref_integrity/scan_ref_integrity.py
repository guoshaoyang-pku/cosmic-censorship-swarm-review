#!/usr/bin/env python3
"""W038-REFINT-01: embedded-reference integrity scanner for a frozen artifact closure.

Task class: G-FORM scope (F1 AF-WCC-VAC-GEN / F2a AF-SCC-C2-VAC-GEN /
F2b AF-SCC-C0-VAC-GEN), with F0 AF-WCC-VAC-GEN declared-hash bindings.

Question: for every file in a freeze manifest, does each hash-shaped reference
embedded *inside* the file resolve to the bytes of the path it names at the
manifest's revision?  verify_frozen.py only re-hashes the listed files; it cannot
see a stale reference embedded in a pinned file.  This scanner closes that gap.

Determinism: findings are emitted in sorted order; `findings_digest` is the
sha256 of the canonical JSON of the findings list, so two runs over identical
bytes produce identical digests even though `generated_at` differs.

Scratch-only: this tool never writes to a scanned path.  Mutation controls are
applied to copies under --scratch-root.

Exit codes: 0 = no STALE/UNRESOLVABLE findings; 2 = findings present (report
written); 3 = input drift during scan (report marked VOID); 4 = control battery
failed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX_ANY = re.compile(r"^[0-9a-f]{6,64}$")
TEXT_REF = re.compile(r"([A-Za-z0-9_./-]+\.(?:yaml|yml|json|jsonl|md|py|csv|txt))#([0-9a-f]{6,64})")
PATHLIKE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:yaml|yml|json|jsonl|md|py|csv|txt)$")
HIST_KEY = re.compile(r"(?i)(superseded|void|historical|archived|archive|previous|retired|deprecated|prior)")
HIST_TEXT = re.compile(r"(?i)(prior_binding|at_authoring|_before\b|before_by|\bsuperseded\b|\bhistorical\b|\bdeprecated\b|\bvoid\b|\bprevious revision\b)")

# Files whose embedded hash fields are live bindings: a mismatch is a defect.
# Everything else (evidence reports, review ledgers, summaries, variant deltas) is a
# historical record; a mismatch there is reported as RECORD_SNAPSHOT, never as a repair.
LIVE_BINDING_FILES = {
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/taxonomy_cases.jsonl",
    "schemas/f1_falsifier_tests.jsonl",
}


def is_live_binding(rel: str) -> bool:
    return rel in LIVE_BINDING_FILES
HASH_KEY = re.compile(r"(?i)(sha256|_hash$|^hash$|_sha$)")
PATH_KEY = re.compile(r"(?i)(path|artifact|evidence|file|source|target|pointer|locator|manifest|taxonomy|contract|schema|ledger|report)")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_key(k: str) -> str:
    k = re.sub(r"(?i)(sha256|hash|sha)$", "", str(k))
    return re.sub(r"[^a-z0-9]+", "", k.lower())


def find_line(text: str, needle: str, start: int = 0) -> int:
    i = text.find(needle, start)
    if i < 0:
        return 0
    return text.count("\n", 0, i) + 1


def is_pathlike(s: str) -> bool:
    if not isinstance(s, str) or len(s) < 3 or len(s) > 400:
        return False
    s = s.split("#", 1)[0]
    return bool(PATHLIKE.match(s)) and ("/" in s or s.endswith((".yaml", ".yml", ".json", ".jsonl", ".md", ".py")))


def mapping_pairs(node, text):
    """Yield (key, scalar_value, line) for scalar pairs of a yaml mapping node."""
    out = []
    for k, v in node.value:
        key = k.value if isinstance(k, yaml.ScalarNode) else None
        if key is None:
            continue
        if isinstance(v, yaml.ScalarNode):
            out.append((str(key), v.value, k.start_mark.line + 1))
        else:
            out.append((str(key), None, k.start_mark.line + 1))
    return out


def walk_yaml(node, path=(), parent_key=None, parent_pairs=()):
    """Yield ('map', keypath, pairs, line, parent_key, parent_pairs)."""
    if isinstance(node, yaml.MappingNode):
        pairs = mapping_pairs(node, None)
        yield ("map", path, pairs, node.start_mark.line + 1, parent_key, parent_pairs)
        for k, v in node.value:
            key = k.value if isinstance(k, yaml.ScalarNode) else None
            if key is None:
                continue
            yield from walk_yaml(v, path + (str(key),), str(key), pairs)
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            yield from walk_yaml(v, path + (i,), parent_key, parent_pairs)


def walk_json(obj, path=(), parent_key=None, parent_pairs=()):
    if isinstance(obj, dict):
        pairs = [(str(k), v if isinstance(v, (str, int, float)) else None, 0) for k, v in obj.items()]
        yield ("map", path, pairs, 0, parent_key, parent_pairs)
        for k, v in obj.items():
            yield from walk_json(v, path + (str(k),), str(k), pairs)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, path + (i,), parent_key, parent_pairs)


def pick_ref_path(hash_key, pairs, parent_key, parent_pairs):
    """Choose the path-like sibling that names the object of a *_sha256 key.

    Returns (ref_key, ref_path, strength):
      strong     - the path key shares the hash key's name prefix
                   (declared_f0_sha256 <-> declared_f0_artifact)
      structural - the hash key is a bare sha256/hash key in a {path,sha256}
                   record or a manifest child whose parent key is the path
      weak       - name fallback; a provenance/review-ledger snapshot, not a
                   live path pin.  Weak pairs are never treated as defects.
    """
    base = norm_key(hash_key)
    cands = []
    for pk, pv, _ln in list(pairs) + list(parent_pairs):
        if isinstance(pv, str) and is_pathlike(pv):
            nk = norm_key(pk)
            if base and nk and (nk.startswith(base) or base.startswith(nk)):
                cands.append((len(os.path.commonprefix([nk, base])), pk, pv))
    if cands:
        cands.sort(key=lambda t: (-t[0], t[1]))
        return cands[0][1], cands[0][2], "strong"
    if not base:
        for pk, pv, _ln in list(pairs) + list(parent_pairs):
            if isinstance(pv, str) and is_pathlike(pv) and norm_key(pk) == "path":
                return pk, pv, "structural"
        if isinstance(parent_key, str) and is_pathlike(parent_key):
            return "<parent-key>", parent_key, "structural"
    for pk, pv, _ln in list(pairs) + list(parent_pairs):
        if isinstance(pv, str) and is_pathlike(pv):
            return pk, pv, "weak"
    if isinstance(parent_key, str) and is_pathlike(parent_key):
        return "<parent-key>", parent_key, "weak"
    return None, None, None


def historical(pairs, ref_path):
    if ref_path and ("/archive/" in ref_path or ref_path.startswith("archive/")):
        return "path is in an archive/ tree"
    for k, v, _ln in pairs:
        if HIST_KEY.search(str(k)) and v not in (None, "", False, "false", "False"):
            return f"sibling historical marker {k}={str(v)[:40]!r}"
    return None


def scan_file(root: Path, rel: str):
    """Return (refs, notes, measured_sha256)."""
    p = root / rel
    refs, notes = [], []
    if not p.exists():
        return refs, [f"MISSING_SCANNED_FILE {rel}"], None, []
    raw = p.read_bytes()
    measured = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    suffix = p.suffix.lower()
    docs = []
    if suffix in (".yaml", ".yml"):
        try:
            node = yaml.compose(text)
            if node is not None:
                docs = list(walk_yaml(node))
        except yaml.YAMLError as e:
            notes.append(f"YAML_PARSE_ERROR {rel}: {str(e)[:120]}")
    elif suffix == ".json":
        try:
            docs = list(walk_json(json.loads(text)))
        except json.JSONDecodeError as e:
            notes.append(f"JSON_PARSE_ERROR {rel}: {str(e)[:120]}")
    elif suffix == ".jsonl":
        for ln, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                for kind, kp, pairs, _l, pk, pp in walk_json(json.loads(line)):
                    docs.append((kind, kp, pairs, ln, pk, pp))
            except json.JSONDecodeError:
                continue
    line_text = {i: l for i, l in enumerate(text.splitlines(), 1)}
    live = is_live_binding(rel)

    seen = set()
    for kind, kp, pairs, line, pk, pp in docs:
        for key, val, kline in pairs:
            if not (isinstance(val, str) and HEX_ANY.match(val) and HASH_KEY.search(key)):
                continue
            ref_key, ref_path, strength = pick_ref_path(key, pairs, pk, pp)
            if ref_path is None:
                refs.append(dict(status="UNPAIRED", source=rel, line=kline or line, declared_key=key,
                                 declared_hash=val, ref_key=None, ref_path=None, measured_hash=None,
                                 reason="no path-like sibling or parent key names the object", strength=None))
                continue
            rid = (rel, key, val, ref_path)
            if rid in seen:
                continue
            seen.add(rid)
            target = root / ref_path.split("#", 1)[0]
            ctx_hist = HIST_TEXT.search(line_text.get(kline or line, ""))
            if strength == "weak":
                refs.append(dict(status="SNAPSHOT", source=rel, line=kline or line, declared_key=key,
                                 declared_hash=val, ref_key=ref_key, ref_path=ref_path,
                                 measured_hash=sha256_file(target) if target.exists() else None,
                                 reason="provenance/review-ledger snapshot: the hash key does not share a "
                                        "name prefix with the path key, so this is not a live path pin",
                                 strength=strength))
                continue
            if not target.exists():
                st = "UNRESOLVABLE" if (live and not ctx_hist) else "RECORD_SNAPSHOT"
                refs.append(dict(status=st, source=rel, line=kline or line, declared_key=key,
                                 declared_hash=val, ref_key=ref_key, ref_path=ref_path, measured_hash=None,
                                 reason="named path does not exist" + ("" if live else " (record document)"),
                                 strength=strength))
                continue
            m = sha256_file(target)
            if m == val or (len(val) < 64 and m.startswith(val)):
                status = "MATCH"
                reason = "declared hash equals measured bytes"
            else:
                hist = historical(pairs, ref_path)
                if hist:
                    status, reason = "HISTORICAL", hist
                elif not live:
                    status = "RECORD_SNAPSHOT"
                    reason = "record document (evidence/review/summary), not a live binding; mismatch is expected after a revision"
                elif ctx_hist:
                    status = "RECORD_SNAPSHOT"
                    reason = "line context marks this as an authoring/prior-revision observation"
                else:
                    status, reason = "STALE", "declared hash differs from measured bytes at a live path"
            refs.append(dict(status=status, source=rel, line=kline or line, declared_key=key,
                             declared_hash=val, ref_key=ref_key, ref_path=ref_path, measured_hash=m,
                             reason=reason, strength=strength, live_binding_document=live))

    # textual `path#hash` references (delta notes, markdown, code comments)
    for m in TEXT_REF.finditer(text):
        path, h = m.group(1), m.group(2)
        rid = (rel, "<text>", h, path)
        if rid in seen:
            continue
        seen.add(rid)
        target = root / path
        ln = find_line(text, m.group(0))
        if not target.exists():
            refs.append(dict(status="UNRESOLVABLE", source=rel, line=ln, declared_key="<text-ref>",
                             declared_hash=h, ref_key=None, ref_path=path, measured_hash=None,
                             reason="textual path#hash reference does not resolve"))
            continue
        mh = sha256_file(target)
        ok = mh == h or (len(h) < 64 and mh.startswith(h))
        st = "MATCH" if ok else ("STALE" if live else "RECORD_SNAPSHOT")
        refs.append(dict(status=st, source=rel, line=ln, declared_key="<text-ref>",
                         declared_hash=h, ref_key=None, ref_path=path, measured_hash=mh,
                         reason="textual path#hash reference" if ok else
                                ("textual path#hash reference is stale" if live else
                                 "textual path#hash reference in a record document (mismatch expected after a revision)"),
                         strength="text"))
    declared = {r["declared_hash"] for r in refs}
    unmatched = sorted({t for t in HEX64.findall(text) if t not in declared})
    return refs, notes, measured, unmatched


def digest(refs):
    canon = json.dumps(sorted(refs, key=lambda r: json.dumps(r, sort_keys=True)), sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()


def load_scan_set(root: Path, manifest_rel: str, extra):
    files = [manifest_rel]  # the manifest's own embedded pins are in scope
    mp = root / manifest_rel
    if mp.exists():
        man = json.loads(mp.read_text())
        files.extend(sorted(man.get("files", {}).keys()))
    files.extend(extra)
    return sorted(set(files))


def run(root: Path, manifest_rel: str, extra):
    files = load_scan_set(root, manifest_rel, extra)
    before = {f: sha256_file(root / f) for f in files if (root / f).exists()}
    refs, notes, unmatched = [], [], {}
    for f in files:
        r, n, _m, u = scan_file(root, f)
        refs.extend(r)
        notes.extend(n)
        if u:
            unmatched[f] = u
    after = {f: sha256_file(root / f) for f in files if (root / f).exists()}
    drift = sorted(f for f in before if before[f] != after.get(f))
    order = {"STALE": 0, "UNRESOLVABLE": 1, "HISTORICAL": 2, "RECORD_SNAPSHOT": 3, "SNAPSHOT": 4,
             "UNPAIRED": 5, "MATCH": 6}
    refs.sort(key=lambda r: (order.get(r["status"], 9), r["source"], r["line"], r["declared_key"]))
    counts = {}
    for r in refs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    live_refs = [r for r in refs if r.get("live_binding_document")]
    report = dict(
        schema_version="w038-refint/v1",
        task_id="W038-GFORM-REFINT-01",
        node_ids=["F0", "F1", "F2a", "F2b"],
        class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        gate="G-FORM",
        manifest=manifest_rel,
        manifest_sha256=sha256_file(root / manifest_rel) if (root / manifest_rel).exists() else None,
        files_scanned=len(files),
        live_binding_documents=sorted({r["source"] for r in live_refs}),
        live_binding_references_checked=len(live_refs),
        counts=counts,
        findings_digest=digest(refs),
        drift_during_scan=drift,
        validity="VOID_DRIFT" if drift else "VALID",
        repair_list=[r for r in refs if r["status"] in ("STALE", "UNRESOLVABLE")],
        record_snapshots=[r for r in refs if r["status"] == "RECORD_SNAPSHOT"],
        references=refs,
        scanned_files={f: before.get(f) for f in files},
        unmatched_hex_tokens=unmatched,
        notes=notes,
        generated_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
    )
    return report


CONTROL_MUTATIONS = {
    "C1_baseline_clean_closure": "expect the three known STALE consistency_evidence_sha256 pairs and no stale provenance snapshot",
    "C2_repin_fixed": "replace 675a99d0.. with the measured evidence hash -> those pairs become MATCH",
    "C3_bad_path": "point consistency_evidence at a nonexistent path -> UNRESOLVABLE",
    "C4_bad_hash": "flip one hex digit -> STALE",
    "C5_correct_pin": "declared_f0_sha256 -> canonical F0 is already correct -> MATCH (false-positive control)",
    "C6_historical": "superseded:true + stale hash -> HISTORICAL, not STALE",
    "C7_weak_snapshot": "provenance worker_sha256 + harvested_from -> SNAPSHOT, never STALE (false-positive control)",
}


def control_battery(root: Path, schemas):
    scratch = root / "artifacts/worker-038/ref_integrity/scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    (scratch / "artifacts/formulation/evidence").mkdir(parents=True)
    (scratch / "schemas").mkdir(parents=True)
    evidence = root / "artifacts/formulation/evidence/taxonomy_consistency.json"
    shutil.copy2(evidence, scratch / "artifacts/formulation/evidence/taxonomy_consistency.json")
    ev_hash = sha256_file(scratch / "artifacts/formulation/evidence/taxonomy_consistency.json")
    files = ["artifacts/formulation/evidence/taxonomy_consistency.json"]
    for s in schemas:
        dst = scratch / s
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / s, dst)
        files.append(s)
    # a canonical F0 copy so C5's declared_f0_sha256 resolves
    (scratch / "research_map").mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "research_map/formulation_taxonomy.yaml", scratch / "research_map/formulation_taxonomy.yaml")
    files.append("research_map/formulation_taxonomy.yaml")
    manifest = scratch / "MANIFEST.json"
    manifest.write_text(json.dumps({"files": {f: {"sha256": sha256_file(scratch / f)} for f in files}}, indent=1))

    results = {}
    for name, expect in CONTROL_MUTATIONS.items():
        for s in schemas:
            (scratch / s).write_bytes((root / s).read_bytes())
        (scratch / "artifacts/formulation/evidence/taxonomy_consistency.json").write_bytes(evidence.read_bytes())
        if name == "C2_repin_fixed":
            for s in schemas:
                t = (scratch / s).read_text()
                (scratch / s).write_text(t.replace("675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48", ev_hash))
        elif name == "C3_bad_path":
            for s in schemas:
                t = (scratch / s).read_text()
                (scratch / s).write_text(t.replace("consistency_evidence: artifacts/formulation/evidence/taxonomy_consistency.json",
                                                   "consistency_evidence: artifacts/formulation/evidence/does_not_exist.json"))
        elif name == "C4_bad_hash":
            for s in schemas:
                t = (scratch / s).read_text()
                (scratch / s).write_text(t.replace("675a99d0d25b2b37", "675a99d0d25b2b38"))
        elif name == "C6_historical":
            hist = scratch / "artifacts/formulation/evidence/historical_note.yaml"
            hist.write_text(
                "superseded: true\nsuperseded_reason: control fixture\n"
                "old_evidence: artifacts/formulation/evidence/taxonomy_consistency.json\n"
                "old_evidence_sha256: " + "0" * 64 + "\n")
            files.append(str(hist.relative_to(scratch)))
            manifest.write_text(json.dumps({"files": {f: {"sha256": sha256_file(scratch / f)} for f in files}}, indent=1))
        rep = run(scratch, "MANIFEST.json", [])
        st = {}
        for r in rep["references"]:
            st[r["status"]] = st.get(r["status"], 0) + 1
        results[name] = dict(expectation=expect, counts=st,
                             stale_pairs=sorted({r["declared_key"] for r in rep["references"] if r["status"] == "STALE"}),
                             unpaired_examples=sorted({r["declared_key"] for r in rep["references"] if r["status"] == "UNPAIRED"})[:5])
    checks = {
        "C1_baseline_clean_closure": (
            results["C1_baseline_clean_closure"]["counts"].get("STALE", 0) >= 3
            and results["C1_baseline_clean_closure"]["stale_pairs"] == ["consistency_evidence_sha256"]
        ),
        "C2_repin_fixed": results["C2_repin_fixed"]["counts"].get("STALE", 0) == 0,
        "C3_bad_path": results["C3_bad_path"]["counts"].get("UNRESOLVABLE", 0) >= 3,
        "C4_bad_hash": results["C4_bad_hash"]["counts"].get("STALE", 0) >= 3,
        "C5_correct_pin": False,  # set below by direct specificity check
        "C6_historical": results["C6_historical"]["counts"].get("HISTORICAL", 0) >= 1 and results["C6_historical"]["counts"].get("STALE", 0) >= 3,
        "C7_weak_snapshot": (
            results["C7_weak_snapshot"]["counts"].get("SNAPSHOT", 0) >= 1
            and "worker_sha256" not in results["C7_weak_snapshot"]["stale_pairs"]
        ),
    }
    # C5/C7 specificity: the F0 declared pin must appear as MATCH, and the provenance
    # snapshot in the same tree must never enter the stale repair list.
    c5 = run(scratch, "MANIFEST.json", [])
    checks["C5_correct_pin"] = any(
        r["declared_key"] == "declared_f0_sha256" and r["status"] == "MATCH" for r in c5["references"])
    checks["C7_weak_snapshot"] = checks["C7_weak_snapshot"] and not any(
        r["status"] == "STALE" and r["declared_key"] == "worker_sha256" for r in c5["references"])
    return dict(controls=CONTROL_MUTATIONS, results=results, checks=checks,
                all_pass=all(checks.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--manifest", default="artifacts/formulation/FROZEN.json")
    ap.add_argument("--extra", nargs="*", default=[
        "schemas/taxonomy_cases.jsonl", "schemas/f1_falsifier_tests.jsonl",
        "research_map/formulation_taxonomy.yaml",
    ])
    ap.add_argument("--report", default=None)
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    schemas = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
    out = run(root, args.manifest, args.extra)
    controls = control_battery(root, schemas) if args.controls else None
    payload = dict(report=out, controls=controls)
    if args.report:
        Path(args.report).write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"counts": out["counts"], "digest": out["findings_digest"],
                      "validity": out["validity"],
                      "repair_list": [{k: r[k] for k in ("source", "line", "declared_key", "ref_path", "measured_hash", "status")}
                                      for r in out["repair_list"]],
                      "controls_pass": (controls or {}).get("all_pass")}, indent=1))
    if controls and not controls["all_pass"]:
        return 4
    if out["validity"] == "VOID_DRIFT":
        return 3
    return 0 if not out["repair_list"] else 2


if __name__ == "__main__":
    sys.exit(main())
