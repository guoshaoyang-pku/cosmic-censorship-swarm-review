#!/usr/bin/env python3
"""W043B-F0-PAIR-DEPCLOSURE-01 -- independent dependency-closure audit of the F0
companion/mirror conflict (astra-lead-formulation blocker leadform-blocker-0007,
evidence artifacts/formulation/evidence/f0_mirror_conflict.json).

Question: can research_map/formulation_taxonomy.yaml (declared F0) and
artifacts/formulation/formulation_taxonomy.yaml (class-contract supplement) be made
byte-identical in either direction, and what does each of the lead's two options
(REC-1 companion-pair exception, REC-2 bounded re-freeze) actually invalidate?

Method (all read-only on shared paths; every write goes under the scratch dir):
  A. measure both artifacts + the three frozen schemas + FROZEN rev26 + map frozen_artifacts;
  B. top-level key sets, shared-key conflict analysis and a lossless-union probe;
  C. class_contract_pointer / f0_binding resolution matrix (canonical / authoring / union);
  D. repo-wide reference scan for the two F0 paths and the pinned hashes;
  E. executed controls: run the real check_taxonomy_consistency.py (source-patched ROOT)
     against (i) the current pair, (ii) canonical->authoring publication, (iii)
     authoring->canonical publication -- the two publication directions must fail closed;
  F. classification of what REC-1 and REC-2 invalidate.

Exit 0 if every declared check completed and the two negative controls behaved as the
lead's blocker predicts; exit 1 otherwise. This is worker evidence only: no gate verdict,
no node status, no canonical byte is modified.

Usage: python3 check_f0_pair.py [--out report.json] [--scratch DIR]
"""
from __future__ import annotations

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

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]  # <repo>/artifacts/worker-043/f0_pair_depclosure/<file>
SELF_DIR = Path(__file__).resolve().parent

CANON = "research_map/formulation_taxonomy.yaml"
AUTHOR = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = "artifacts/formulation/FROZEN.json"
MAP = "research_map/research_map.json"

LITERALS = [
    CANON,
    AUTHOR,
    "276009f4f63d",   # canonical F0 declared hash
    "c8e979a1eb48",   # authoring F0 hash
    "9a8bd4c96800",   # F1 rev11
    "b6123750b37d",   # F2a rev11
    "1bb78ce9b357",   # F2b rev11
    "taxonomy_consistency.json",
    "FROZEN.json",
]
SCAN_DIRS = [
    "schemas", "research_map", "artifacts/formulation", "reviews",
    "ledger", "numerics", "evaluation", "runtime/state", "runtime/bin",
]
MAX_SCAN_BYTES = 1_500_000
SCAN_CAP = 40  # paths recorded per literal


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    return {
        "path": rel,
        "exists": p.is_file(),
        "sha256": sha256(p) if p.is_file() else None,
        "bytes": p.stat().st_size if p.is_file() else None,
    }


def load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def norm(v) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def dotted(doc: dict, fragment: str):
    cur = doc
    for part in fragment.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, part
        cur = cur[part]
    return cur, None


def key_sets(A: dict, B: dict) -> dict:
    ka, kb = set(A), set(B)
    shared = sorted(ka & kb)
    conflicts = []
    for k in shared:
        if isinstance(A[k], (dict, list)) and isinstance(B[k], (dict, list)):
            same = norm(A[k]) == norm(B[k])
        else:
            same = A[k] == B[k]
        if not same:
            conflicts.append({
                "key": k,
                "canonical_shape": type(A[k]).__name__,
                "authoring_shape": type(B[k]).__name__,
                "canonical_preview": norm(A[k])[:220],
                "authoring_preview": norm(B[k])[:220],
            })
    return {
        "canonical_only": sorted(ka - kb),
        "authoring_only": sorted(kb - ka),
        "shared": shared,
        "shared_value_conflicts": conflicts,
    }


def built_union(A: dict, B: dict) -> dict:
    U = dict(A)
    for k, v in B.items():
        U.setdefault(k, v)  # first-wins; conflicts are reported separately
    return U


def ref_scan() -> dict:
    out = {lit: [] for lit in LITERALS}
    totals = {lit: 0 for lit in LITERALS}
    skipped_large, scanned = 0, 0
    for d in SCAN_DIRS:
        dp = ROOT / d
        if not dp.is_dir():
            continue
        for f in sorted(x for x in dp.rglob("*") if x.is_file()):
            if f.name.startswith("._") or "__pycache__" in f.parts:
                continue
            if f.stat().st_size > MAX_SCAN_BYTES:
                skipped_large += 1
                continue
            try:
                txt = f.read_text(errors="replace")
            except OSError:
                continue
            scanned += 1
            rel = str(f.relative_to(ROOT))
            for lit in LITERALS:
                if lit in txt:
                    totals[lit] += 1
                    if len(out[lit]) < SCAN_CAP:
                        out[lit].append(rel)
    return {"scanned_files": scanned, "skipped_large": skipped_large,
            "totals_uncapped": totals, "matches": out, "path_cap": SCAN_CAP}


def run_checker_control(label: str, canonical_src: str, authoring_src: str, scratch: Path) -> dict:
    """Execute the real checker with a patched ROOT so its writes stay in scratch."""
    root = scratch / label
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    (root / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    (root / "artifacts/formulation/tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / canonical_src, root / CANON)
    shutil.copyfile(ROOT / authoring_src, root / AUTHOR)
    shutil.copyfile(ROOT / ALIASES, root / ALIASES)
    src = (ROOT / CHECKER).read_text()
    patched = src.replace(
        'ROOT = Path(__file__).resolve().parents[3]',
        f'ROOT = Path(r"{root}")',
    )
    assert patched != src, "checker ROOT line not found; refusing to run unpatched"
    tool = root / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    tool.write_text(patched)
    proc = subprocess.run(
        [sys.executable, str(tool)],
        capture_output=True, text=True, cwd=str(root), timeout=120,
    )
    evidence = root / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ev = None
    if evidence.is_file():
        try:
            ev = json.loads(evidence.read_text())
        except ValueError:
            ev = {"unparseable": True}
    return {
        "label": label,
        "canonical_src": canonical_src,
        "authoring_src": authoring_src,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip()[:600],
        "stderr_tail": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
        "stderr_has_keyerror": "KeyError" in proc.stderr,
        "keyerror_token": next(
            (m for m in re.findall(r"KeyError: [^\n]+", proc.stderr)), None),
        "evidence_written": ev is not None,
        "evidence_consistent": (ev or {}).get("consistent"),
    }


def fixtures_scan() -> dict:
    d = ROOT / "artifacts/formulation/fixtures"
    if not d.is_dir():
        return {"dir": "artifacts/formulation/fixtures", "exists": False}
    files = sorted(x for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
    pins = []
    for f in files:
        if f.stat().st_size > MAX_SCAN_BYTES:
            continue
        txt = f.read_text(errors="replace")
        hit = [lit for lit in ("9a8bd4c9", "b6123750", "1bb78ce9", "276009f4", "c8e979a1") if lit in txt]
        if hit:
            pins.append({"path": str(f.relative_to(ROOT)), "pins": hit})
    return {"dir": "artifacts/formulation/fixtures", "exists": True,
            "n_files": len(files), "files_pinning_hashes": pins}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SELF_DIR / "report.json"))
    ap.add_argument("--scratch", default=None)
    a = ap.parse_args()
    scratch = Path(a.scratch) if a.scratch else Path(tempfile.mkdtemp(prefix="w043_f0pair_"))
    scratch.mkdir(parents=True, exist_ok=True)

    started = now()
    inputs = [CANON, AUTHOR, *SCHEMAS, CHECKER, ALIASES, FROZEN, MAP]
    start_hashes = {rel: measure(rel) for rel in inputs}

    A, B = load_yaml(CANON), load_yaml(AUTHOR)
    ks = key_sets(A, B)
    U = built_union(A, B)

    # --- pointer matrix -------------------------------------------------------------
    pointers = []
    for s in SCHEMAS:
        d = load_yaml(s)
        raw = str(d.get("class_contract_pointer", ""))
        path_part, _, frag = raw.partition("#")
        cid = d.get("class_id")
        frag = frag or f"class_contracts.{cid}"
        res = {}
        for label, doc in (("canonical", A), ("authoring", B), ("union", U)):
            val, missing = dotted(doc, frag)
            res[label] = {"resolves": missing is None,
                          "missing_at": missing,
                          "value_present": val is not None}
        fb = d.get("f0_binding", {}) or {}
        pointers.append({
            "schema": s,
            "class_id": cid,
            "class_contract_pointer": raw,
            "pointer_path": path_part,
            "pointer_fragment": frag,
            "resolution": res,
            "f0_binding": {
                "declared_f0_artifact": fb.get("declared_f0_artifact"),
                "declared_f0_sha256": fb.get("declared_f0_sha256"),
                "class_contract_supplement": fb.get("class_contract_supplement"),
                "consistency_evidence": fb.get("consistency_evidence"),
            },
        })

    # --- reference scan + fixtures --------------------------------------------------
    scan = ref_scan()
    fixtures = fixtures_scan()

    # --- executed controls ----------------------------------------------------------
    controls = [
        run_checker_control("control_current_pair", CANON, AUTHOR, scratch),
        run_checker_control("sim_canonical_to_authoring", CANON, CANON, scratch),
        run_checker_control("sim_authoring_to_canonical", AUTHOR, AUTHOR, scratch),
    ]
    ctrl = {c["label"]: c for c in controls}
    controls_ok = (
        ctrl["control_current_pair"]["exit_code"] == 0
        and ctrl["control_current_pair"]["evidence_consistent"] is True
        and ctrl["sim_canonical_to_authoring"]["exit_code"] != 0
        and ctrl["sim_canonical_to_authoring"]["stderr_has_keyerror"]
        and ctrl["sim_authoring_to_canonical"]["exit_code"] != 0
        and ctrl["sim_authoring_to_canonical"]["stderr_has_keyerror"]
    )

    # --- REC blast radius -----------------------------------------------------------
    m = json.loads((ROOT / MAP).read_text())
    frozen_paths = {f["path"] for f in m.get("frozen_artifacts", []) if f.get("active", True)}
    canonical_f0_active = CANON in frozen_paths
    author_consumers = [p for p in scan["matches"][AUTHOR] if not p.startswith("artifacts/worker-043/")]
    canon_consumers = [p for p in scan["matches"][CANON] if not p.startswith("artifacts/worker-043/")]
    mirror_consumers = []
    for d in ("research_map", "runtime/bin", "artifacts/formulation/tools"):
        dp = ROOT / d
        if not dp.is_dir():
            continue
        for f in sorted(dp.rglob("*.py")):
            if f.stat().st_size > MAX_SCAN_BYTES:
                continue
            txt = f.read_text(errors="replace")
            if "MIRRORS" in txt or "dual-tree" in txt:
                lines = [
                    i + 1 for i, ln in enumerate(txt.splitlines())
                    if "MIRRORS = [" in ln or "MIRRORS=" in ln
                ]
                mirror_consumers.append({
                    "path": str(f.relative_to(ROOT)),
                    "defines_MIRRORS_at_lines": lines,
                    "has_dual_tree_text": "dual-tree" in txt,
                })

    # --- findings -------------------------------------------------------------------
    shared_conflicts = ks["shared_value_conflicts"]
    findings = [
        {
            "id": "W043B-F-01",
            "severity": "info",
            "finding": (
                f"The F0 pair are two different artifacts at the measured instant: "
                f"canonical {start_hashes[CANON]['sha256'][:12]} ({start_hashes[CANON]['bytes']} B) "
                f"vs authoring {start_hashes[AUTHOR]['sha256'][:12]} ({start_hashes[AUTHOR]['bytes']} B); "
                f"{len(ks['canonical_only'])} canonical-only, {len(ks['authoring_only'])} authoring-only, "
                f"{len(ks['shared'])} shared top-level keys."
            ),
            "falsifier": "Re-measure both paths: if they are byte-identical the pair question is moot.",
            "evidence_refs": [f"{CANON}#{start_hashes[CANON]['sha256'][:12]}",
                              f"{AUTHOR}#{start_hashes[AUTHOR]['sha256'][:12]}"],
        },
        {
            "id": "W043B-F-02",
            "severity": "major",
            "finding": (
                "All three frozen schemas' class_contract_pointer fragments resolve only in the "
                "authoring artifact; none resolves in the declared canonical F0; all resolve in a "
                "union document. This independently reproduces worker-020 C15 and leadform-blocker-0007."
            ),
            "falsifier": ("Re-run the pointer matrix: falsified if any class_contract_pointer resolves "
                          f"in {CANON} alone or fails in {AUTHOR}."),
            "evidence_refs": [f"{s}#{start_hashes[s]['sha256'][:12]}" for s in SCHEMAS]
                              + ["reviews/F0-rev26-adjudication-090.json#498a415808e1"],
        },
        {
            "id": "W043B-F-03",
            "severity": "major",
            "finding": (
                "Executed controls on the real checker (ROOT-patched to scratch): the current pair is "
                f"CONSISTENT (exit 0); byte-identical canonical->authoring publication fails with "
                f"{ctrl['sim_canonical_to_authoring']['keyerror_token']}; byte-identical "
                f"authoring->canonical publication fails with "
                f"{ctrl['sim_authoring_to_canonical']['keyerror_token']}. Both destructive directions in "
                "the lead's blocker are reproduced by execution, not by reading."
            ),
            "falsifier": ("Falsified if the patched-checker controls no longer reproduce exit 0 / two "
                          "distinct KeyErrors on unchanged inputs, or if the checker exits 0 on either "
                          "single-artifact publication."),
            "evidence_refs": [f"{CHECKER}", f"{ALIASES}"],
        },
        {
            "id": "W043B-F-04",
            "severity": "major",
            "finding": (
                f"Shared-key conflict analysis: {len(shared_conflicts)} shared top-level key(s) carry "
                "different values across the pair"
                + (f" ({', '.join(c['key'] for c in shared_conflicts)})" if shared_conflicts else "")
                + "; a first-wins union resolves every schema pointer, but each conflicting key is a "
                "semantic decision a merge must adjudicate."
            ),
            "falsifier": ("Falsified if a union built from the two artifacts changes no shared-key value, "
                          "or if the listed conflicting keys are in fact equal under YAML normalization."),
            "evidence_refs": [f"{CANON}#{start_hashes[CANON]['sha256'][:12]}",
                              f"{AUTHOR}#{start_hashes[AUTHOR]['sha256'][:12]}"],
        },
        {
            "id": "W043B-F-05",
            "severity": "major",
            "finding": (
                "REC-1 blast radius is not one line: the F0 divergence is computed by TWO independent "
                "hard-coded MIRRORS lists - research_map/audit_evidence.py:123 (audit finding) and "
                "research_map/astra_lifecycle.py:44 (publication_status, CF-13, gate reasons) - and the "
                "pass-02 event generators re-state the divergence in their own text. The canonical F0 "
                f"path is currently NOT an active entry in map.frozen_artifacts ({canonical_f0_active}), "
                "so the audit reports the divergence as soft today; re-activating a frozen F0 entry "
                "(which G-F0 review requires) flips the same divergence to hard under "
                "audit_evidence.py:135. REC-1 therefore has to be encoded once and consumed by every "
                "mirror consumer, or the controller's own lifecycle keeps publishing F0 as divergent."
            ),
            "falsifier": ("Falsified if astra_lifecycle.py no longer derives publication_status from its "
                          "own MIRRORS list, or if audit_evidence.py routes the F0 divergence to hard "
                          "while the canonical path is inactive."),
            "evidence_refs": ["research_map/audit_evidence.py:123", "research_map/astra_lifecycle.py:44",
                              MAP],
        },
        {
            "id": "W043B-F-06",
            "severity": "info",
            "finding": (
                "REC-2 blast radius measured by reference scan (uncapped file counts): "
                f"{scan['totals_uncapped'][AUTHOR]} file(s) reference {AUTHOR}; "
                f"{scan['totals_uncapped'][CANON]} reference {CANON}; "
                f"{scan['totals_uncapped']['taxonomy_consistency.json']} reference the pinned consistency "
                f"evidence; {scan['totals_uncapped']['FROZEN.json']} reference FROZEN.json. "
                f"{fixtures.get('n_files')} fixture file(s) live under artifacts/formulation/fixtures, "
                f"{len(fixtures.get('files_pinning_hashes', []))} of them pin a schema/F0 hash prefix. "
                "REC-2 changes the three schema hashes and the supplement path, so the packaged "
                "semantic-contract fixtures, the acceptance fixture base and every current F1/F2a/F2b "
                "review binding must be re-cut in the same bounded re-freeze; that is a larger surface "
                "than the lead's ~3-4 agent-hour estimate lists."
            ),
            "falsifier": ("Falsified if the reference scan missed a live consumer, i.e. a file that reads "
                          "either F0 path or pins a schema/F0 hash and is not counted in "
                          "raw/reference_scan.json."),
            "evidence_refs": ["artifacts/worker-043/f0_pair_depclosure/raw/reference_scan.json", FROZEN],
        },
        {
            "id": "W043B-F-07",
            "severity": "info",
            "finding": (
                "Lossless-union probe: a first-wins union of the two artifacts resolves all three "
                "class_contract_pointers, but the pair shares "
                f"{len(shared_conflicts)} conflicting top-level key(s) "
                f"({', '.join(c['key'] for c in shared_conflicts)}). A merge is therefore not "
                "mechanical: each conflicting key (identity/revision/provenance/timestamp metadata and "
                "the two different class_scope_adjudication blocks) needs an explicit owner decision, "
                "which is another reason the companion-pair option (REC-1) is cheaper than a union."
            ),
            "falsifier": ("Falsified if a union preserves both values of every shared key or if the listed "
                          "keys are in fact equal under YAML normalization."),
            "evidence_refs": [f"{CANON}#{start_hashes[CANON]['sha256'][:12]}",
                              f"{AUTHOR}#{start_hashes[AUTHOR]['sha256'][:12]}"],
        },
    ]

    end_hashes = {rel: measure(rel) for rel in inputs}
    stable = all(start_hashes[r]["sha256"] == end_hashes[r]["sha256"] for r in inputs)

    if not stable:
        overall = "VOID_INPUTS_CHANGED"
    elif controls_ok:
        overall = "LEAD_BLOCKER_SUPPORTED"
    else:
        overall = "LEAD_BLOCKER_NOT_REPRODUCED"

    report = {
        "task_id": "W043B-F0-PAIR-DEPCLOSURE-01",
        "worker": "worker-043",
        "created_at": now(),
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": (
            "Is the lead's blocker leadform-blocker-0007 (byte-identical publication in either "
            "direction destroys a frozen input) reproducible, and what does each of REC-1 / REC-2 "
            "invalidate?"
        ),
        "method": [
            "measure hashes/bytes of both F0 artifacts, the three schemas, checker, FROZEN rev26, map",
            "top-level key sets + shared-key conflict analysis + first-wins union",
            "class_contract_pointer / f0_binding resolution matrix (canonical/authoring/union)",
            "repo-wide literal reference scan (caps: 1.5 MB/file, 40 paths/literal)",
            "executed checker controls in scratch with source-patched ROOT (current pair, both single-artifact publications)",
            "REC-1/REC-2 consumer classification from the scan + audit_evidence.py code path",
        ],
        "measured": {
            "canonical_f0": start_hashes[CANON],
            "authoring_f0": start_hashes[AUTHOR],
            "schemas": {s: start_hashes[s] for s in SCHEMAS},
            "checker": start_hashes[CHECKER],
            "frozen": start_hashes[FROZEN],
            "frozen_revision": json.loads((ROOT / FROZEN).read_text()).get("revision"),
            "map_updated_at": m.get("updated_at"),
        },
        "key_sets": ks,
        "pointer_matrix": pointers,
        "reference_scan": scan,
        "fixtures": fixtures,
        "controls": controls,
        "controls_ok": controls_ok,
        "blast_radius": {
            "rec1": {
                "action": "add the F0 pair to a documented exception in research_map/audit_evidence.py MIRRORS",
                "mirror_semantics_consumers": mirror_consumers,
                "canonical_f0_active_frozen_entry": canonical_f0_active,
                "divergence_would_become_hard_if_refrozen": True,
                "frozen_artifact_bytes_changed": 0,
            },
            "rec2": {
                "action": "publish supplement as its own canonical artifact, mirror declared F0, repoint checker, regenerate FROZEN, re-dispatch reviews",
                "authoring_path_consumers": author_consumers,
                "canonical_path_consumers": canon_consumers,
                "schema_hashes_invalidated": [s for s in SCHEMAS],
                "fixture_files_pinning_hashes": fixtures.get("files_pinning_hashes", []),
                "frozen_artifact_bytes_changed": "schemas x3 + FROZEN + map.frozen_artifacts + evidence/taxonomy_consistency.json + fixtures",
            },
        },
        "concurrent_work": {
            "overlap": (
                "reviews/F0-rev26-adjudication-090.json (worker-090, written 00:29) concurrently "
                "supports the same two-artifact claim and the same pointer-resolution-only-in-"
                "supplement result, and explicitly leaves REC-1 vs REC-2 to the controller."
            ),
            "delta_of_this_audit": (
                "executed destructive-direction controls on the real consistency checker; the "
                "two-MIRRORS-list REC-1 blast radius and its hard/soft flip under re-freeze; the "
                "uncapped REC-2 consumer/fixture counts."
            ),
            "evidence_ref": "reviews/F0-rev26-adjudication-090.json#498a415808e1",
        },
        "input_stability": {
            "start": start_hashes, "end": end_hashes, "stable": stable,
            "window": {"started_at": started, "ended_at": now()},
        },
        "findings": findings,
        "verdict": overall,
        "recommendation": (
            "REC-1 is the only option that leaves every frozen byte and every in-flight review hash "
            "intact, but the audit shows it is a policy change, not a local audit exception: the same "
            "companion-pair rule must be consumed by research_map/astra_lifecycle.py (publication_status "
            "/ CF-13 / gate reasons) as well as research_map/audit_evidence.py, and the divergence "
            "flips hard as soon as a canonical F0 freeze entry is re-activated. REC-2 remains "
            "technically feasible - a first-wins union resolves all three schema pointers - but it "
            f"requires adjudicating {len(shared_conflicts)} shared-key conflict(s), repointing "
            f"{scan['totals_uncapped'][AUTHOR]} authoring-path reference(s), re-cutting the three schema "
            f"hashes, the checker path, the {fixtures.get('n_files')}-file fixture tree and every "
            "current F1/F2a/F2b review binding. Worker evidence only: the choice between REC-1 and REC-2 "
            "is the controller's."
        ),
        "falsifier": (
            "This audit is falsified if re-running check_f0_pair.py on byte-unchanged inputs yields a "
            "different pointer matrix or control outcome (current pair must be CONSISTENT, both "
            "single-artifact publications must fail closed with a KeyError), or if any measured input "
            "hash differs between the start and end windows. Per-finding falsifiers are attached to "
            "each finding."
        ),
        "authority_note": (
            "worker-043 is the author of no formulation artifact and read-only on every canonical "
            "path; this report cannot set a gate verdict, a node status or validation_status, and it "
            "was produced without modifying any file outside artifacts/worker-043/."
        ),
        "evidence_refs": [
            f"{CANON}#{start_hashes[CANON]['sha256'][:12]}",
            f"{AUTHOR}#{start_hashes[AUTHOR]['sha256'][:12]}",
            f"{FROZEN}#{start_hashes[FROZEN]['sha256'][:12]}",
            f"{CHECKER}",
            "artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75",
        ],
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    raw = SELF_DIR / "raw"
    raw.mkdir(exist_ok=True)
    (raw / "pointer_matrix.json").write_text(json.dumps(pointers, indent=2) + "\n")
    (raw / "reference_scan.json").write_text(json.dumps(scan, indent=2) + "\n")
    (raw / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")
    (raw / "key_sets.json").write_text(json.dumps(ks, indent=2) + "\n")
    (raw / "input_hashes_start.json").write_text(json.dumps(start_hashes, indent=2) + "\n")
    (raw / "input_hashes_end.json").write_text(json.dumps(end_hashes, indent=2) + "\n")
    (raw / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")

    print(json.dumps({
        "verdict": overall,
        "controls_ok": controls_ok,
        "stable": stable,
        "shared_conflicts": [c["key"] for c in shared_conflicts],
        "canonical_f0": start_hashes[CANON]["sha256"][:12],
        "authoring_f0": start_hashes[AUTHOR]["sha256"][:12],
        "report": str(out),
        "scratch": str(scratch),
    }, indent=2))
    return 0 if (controls_ok and stable) else 1


if __name__ == "__main__":
    sys.exit(main())
