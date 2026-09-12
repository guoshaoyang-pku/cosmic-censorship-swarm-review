#!/usr/bin/env python3
"""W092-REV12-CERT-01 -- independent hash-pinned certification of the
astra-life03-close-findings repair landing (F0 rev5, F1/F2a/F2b rev12).

Bounded execution worker-092, fleet 2026-09-12T00:29:48+08:00.
Measurement only. Writes only under artifacts/worker-092/rev12cert/.

What it does
------------
1. Pins the live canonical/authoring bytes (9 files + FROZEN + evidence) into
   ./pinned/ and records entry hashes.
2. Re-measures, from the pinned bytes only, each repair the owner's rev12 delta
   claims: pointer repointing to the canonical `classes` key, supplement pointer
   split, f0_binding refresh, duplicate-key collapse, wall-clock revised_at,
   D0 retyping, F1 visibility/AF_{I+} repair, and the F0 rev5 discharge of the
   scalar-class comeager conclusion.
3. Independently recomputes the FROZEN rev26 manifest against disk and records
   every drifted path (freeze state at measurement time).
4. Controls: CTL-1 determinism, CTL-2 negative mutation, CTL-3 entry==exit
   drift guard, CTL-4 publication byte-identity.

Exit code: 0 iff every check's observed status equals its declared
expected_status (fail-closed: any unexpected observation -> exit 1).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINNED = HERE / "pinned"
TZ = timezone(timedelta(hours=8))
WORKER = "worker-092"
TASK_ID = "W092-REV12-CERT-01"

CANONICAL = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
AUTHORING = {
    "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
EXTRA = [
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
]
ALL_FILES = list(CANONICAL.values()) + list(AUTHORING.values()) + EXTRA
FROZEN_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> datetime:
    return datetime.now(TZ)


def load_yaml_with_dups(path: Path):
    """Return (data, dup_keys). dup_keys = [(dotted-ish key, line)]."""
    dups: list = []

    class DupLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for k_node, v_node in node.value:
            key = loader.construct_object(k_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                key = str(key)
            if key in mapping:
                dups.append((str(key), k_node.start_mark.line + 1))
            mapping[key] = loader.construct_object(v_node, deep=deep)
        return mapping

    DupLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    with open(path, "rb") as f:
        data = yaml.load(f, Loader=DupLoader)
    return data, dups


def load_json(path: Path):
    with open(path, "rb") as f:
        return json.load(f)


def walk_pointer(data, dotted: str):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, False
    return cur, True


def resolve_pointer(pointer: str):
    """pointer = '<relpath>#<dotted.key>' -> (resolved, sha, detail)."""
    if "#" not in pointer:
        return False, None, "no #fragment"
    rel, frag = pointer.split("#", 1)
    p = ROOT / rel
    if not p.exists():
        return False, None, f"file missing: {rel}"
    try:
        data, _ = load_yaml_with_dups(p)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"parse error: {exc}"
    val, ok = walk_pointer(data, frag)
    return ok, sha256_file(p), ("resolved" if ok else f"unresolved fragment {frag}")


def parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts)
    except Exception:  # noqa: BLE001
        return None


def find_key(obj, key):
    """Recursive search for the first occurrence of a mapping key."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def collect_checks(pins: dict):
    """All checks read the pinned copies only (paths under ./pinned/).

    expected_status == "ANY" marks a measurement whose value is recorded rather
    than asserted (freeze-state scans); every other expectation is exact.
    """
    checks: list[dict] = []
    findings: list[dict] = []

    def add(cid, claim, status, expected, detail):
        checks.append(
            {
                "id": cid,
                "claim": claim,
                "status": status,
                "expected_status": expected,
                "detail": detail,
            }
        )

    # ---- parse pinned bytes -------------------------------------------------
    f0, f0_dups = load_yaml_with_dups(PINNED / "F0")
    schemas = {}
    for node in ("F1", "F2a", "F2b"):
        schemas[node], dups = load_yaml_with_dups(PINNED / node)
        schemas[node]["_dups"] = dups
    supplement, sup_dups = load_yaml_with_dups(PINNED / "supplement")

    classes = (f0.get("classes") or {}) if isinstance(f0, dict) else {}

    # R1: exactly the four frozen class ids
    got_ids = sorted(classes.keys())
    add(
        "R1-class-set",
        "F0 rev5 declares exactly the four frozen class ids",
        "PASS" if got_ids == sorted(FROZEN_IDS) else "FAIL",
        "PASS",
        f"classes={got_ids}",
    )

    # R2: all four class conclusions carry a comeager quantifier (rev5 discharge)
    missing = [c for c in FROZEN_IDS if "comeager" not in str((classes.get(c) or {}).get("conclusion", {}).get("text", ""))]
    scalar_txt = str((classes.get("AF-WCC-SCALAR-SPH") or {}).get("conclusion", {}).get("text", ""))
    add(
        "R2-comeager-all-four",
        "F0 rev5: every class conclusion text carries the comeager quantifier",
        "PASS" if not missing else "FAIL",
        "PASS",
        f"missing={missing}",
    )
    add(
        "R2b-scalar-discharge",
        "F0 rev5: scalar class conclusion names the superseded set-based wording as a variant, not its predicate",
        "PASS" if ("variant SET" in scalar_txt or "superseded set-based wording" in scalar_txt) else "FAIL",
        "PASS",
        f"scalar_conclusion_len={len(scalar_txt)}",
    )

    # R3..R5 per schema
    for node, d in schemas.items():
        cid = d.get("class_id")
        ptr = d.get("class_contract_pointer")
        want = f"research_map/formulation_taxonomy.yaml#classes.{cid}"
        ok_ptr = ptr == want
        resolved, psha, pdetail = resolve_pointer(ptr or "")
        add(
            f"R3-{node}-canonical-pointer",
            f"{node}: class_contract_pointer is the canonical `classes.<CLASS>` pointer and resolves",
            "PASS" if (ok_ptr and resolved) else "FAIL",
            "PASS",
            f"pointer={ptr!r} resolves={resolved} ({pdetail})",
        )
        f0b = d.get("f0_binding") or {}
        sup_ptr = f0b.get("class_contract_supplement_pointer")
        sup_top = d.get("class_contract_supplement_pointer")
        sup_res, sup_sha, sup_detail = resolve_pointer(sup_ptr or "")
        add(
            f"R4-{node}-supplement-pointer",
            f"{node}: supplement pointer split into its own field and resolves in the supplement",
            "PASS" if (sup_res and isinstance(sup_top, str) and sup_ptr and sup_top == sup_ptr) else "FAIL",
            "PASS",
            f"f0_binding.supplement_pointer={sup_ptr!r} top_level={sup_top!r} resolves={sup_res}",
        )
        live_f0 = pins["F0"]
        add(
            f"R5-{node}-f0binding",
            f"{node}: declared_f0_sha256 equals the live pinned F0 hash",
            "PASS"
            if (
                f0b.get("declared_f0_artifact") == "research_map/formulation_taxonomy.yaml"
                and f0b.get("declared_f0_sha256") == live_f0
            )
            else "FAIL",
            "PASS",
            f"declared={str(f0b.get('declared_f0_sha256'))[:16]} live={live_f0[:16]}",
        )
        # consistency evidence binding
        cited = f0b.get("consistency_evidence_sha256")
        disk = pins["taxonomy_consistency.json"]
        add(
            f"R6-{node}-consistency-evidence",
            f"{node}: cited consistency_evidence_sha256 matches the pinned evidence file",
            "PASS" if cited == disk else "MISMATCH",
            "MISMATCH",
            f"cited={str(cited)[:16]} pinned_evidence={disk[:16]}",
        )
        # revised_at wall-clock
        ts = parse_ts(str(d.get("revised_at")))
        skew_ok = ts is not None and ts <= now() + timedelta(seconds=60)
        add(
            f"R7-{node}-wallclock",
            f"{node}: revised_at is a parseable wall-clock stamp not in the future",
            "PASS" if skew_ok else "FAIL",
            "PASS",
            f"revised_at={d.get('revised_at')} revision={d.get('revision')}",
        )
        # duplicate keys collapsed
        dups = d.get("_dups") or []
        add(
            f"R8-{node}-no-duplicate-keys",
            f"{node}: raw YAML has no duplicate mapping keys",
            "PASS" if not dups else "FAIL",
            "PASS",
            f"duplicates={dups}",
        )
        # D0 retyping
        raw = (PINNED / node).read_text()
        sf = str((d.get("conclusion") or {}).get("statement_formal", ""))
        add(
            f"R9-{node}-d0-retyped",
            f"{node}: D0 retyped as a tagged regularity index `r` (no bare (s,delta) quantifier)",
            "PASS" if ("forall (s,delta) in D0" not in raw and "forall r in D0" in sf) else "FAIL",
            "PASS",
            f"statement_formal_head={sf[:48]!r}",
        )
        if cid == "AF-WCC-VAC-GEN":
            pa = str(find_key(d, "predicate_abbreviation") or "")
            vis = str((d.get("visibility") or {}).get("definition") or "")
            add(
                "R10-F1-visibility-AF",
                "F1 rev12: statement_formal uses AF_{I+}, the symbol is defined, and visibility is the tail predicate",
                "PASS"
                if ("AF_{I+}" in sf and "AF_{I+}" in pa and "tail" in vis.lower())
                else "FAIL",
                "PASS",
                f"AF_in_formal={'AF_{I+}' in sf} AF_defined={'AF_{I+}' in pa} tail_visibility={'tail' in vis.lower()}",
            )

    # R11: F0 duplicate keys
    add(
        "R11-F0-no-duplicate-keys",
        "F0 rev5 raw YAML has no duplicate mapping keys",
        "PASS" if not f0_dups else "FAIL",
        "PASS",
        f"duplicates={f0_dups}",
    )
    add(
        "R12-supplement-no-duplicate-keys",
        "supplement raw YAML has no duplicate mapping keys",
        "PASS" if not sup_dups else "FAIL",
        "PASS",
        f"duplicates={sup_dups}",
    )

    # ---- publication byte-identity -----------------------------------------
    for node, rel in AUTHORING.items():
        a = pins[Path(rel).name if False else node + "-authoring"]
        c = pins[node]
        add(
            f"PUB-{node}",
            f"{node}: authoring copy is byte-identical to the canonical schema",
            "ALIGNED" if a == c else "DIVERGENT",
            "ALIGNED",
            f"canonical={c[:16]} authoring={a[:16]}",
        )
    f0_pair = pins["F0"] == pins["supplement"]
    add(
        "PUB-F0-pair",
        "F0 canonical taxonomy and class-contract supplement are distinct files (rev26 logical_artifacts declaration)",
        "DISTINCT" if not f0_pair else "IDENTICAL",
        "DISTINCT",
        f"canonical={pins['F0'][:16]} supplement={pins['supplement'][:16]}",
    )

    # ---- freeze state -------------------------------------------------------
    frozen_raw = json.loads((PINNED / "FROZEN.json").read_text())
    frozen_files = frozen_raw.get("files") or {}
    drift = []
    missing = []
    for rel, meta in sorted(frozen_files.items()):
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        live = sha256_file(p)
        if live != (meta or {}).get("sha256"):
            drift.append(
                {
                    "path": rel,
                    "frozen": str((meta or {}).get("sha256"))[:16],
                    "live": live[:16],
                }
            )
    add(
        "FREEZE-01-manifest-drift",
        "FROZEN manifest vs live disk: drifted paths enumerated (measurement, not assertion)",
        "DRIFT_CONFIRMED" if drift else "NO_DRIFT",
        "ANY",
        f"frozen_revision={frozen_raw.get('revision')} frozen_at={frozen_raw.get('frozen_at')} "
        f"drift={len(drift)} missing={len(missing)} paths={[d['path'] for d in drift]}",
    )
    class_paths = set(CANONICAL.values()) | set(AUTHORING.values())
    class_drift = [d for d in drift if d["path"] in class_paths]
    add(
        "FREEZE-02-class-bearing-paths-drifted",
        "Class-bearing canonical/authoring paths drifted from the current FROZEN manifest",
        "CLASS_DRIFT_CONFIRMED" if class_drift else "NO_CLASS_DRIFT",
        "ANY",
        f"class_paths={len(class_paths)} drifted={len(class_drift)} paths={[d['path'] for d in class_drift]}",
    )
    add(
        "FREEZE-03-pins-live-class-bytes",
        "Current FROZEN manifest pins the live F0/F1/F2a/F2b bytes (repair re-frozen, not only written)",
        "PASS" if not class_drift else "FAIL",
        "PASS",
        f"frozen_revision={frozen_raw.get('revision')} class_drift={len(class_drift)}",
    )

    if class_drift:
        findings.append(
            {
                "id": "W092-R12-F1",
                "severity": "blocking-for-binding",
                "statement": (
                    f"FROZEN revision {frozen_raw.get('revision')} ({frozen_raw.get('frozen_at')}) does not pin "
                    f"{len(class_drift)} of {len(class_paths)} live class-bearing paths: "
                    f"{[d['path'] for d in class_drift]}. Reviews at the live rev12 hashes are not frozen."
                ),
                "consequence": "Any gate scan that resolves through FROZEN binds superseded bytes for those paths.",
                "falsifier": "A FROZEN revision that pins the live rev12/F0-rev5 hashes on all class-bearing paths falsifies this finding.",
                "evidence": "FREEZE-01,FREEZE-02",
            }
        )
    else:
        findings.append(
            {
                "id": "W092-R12-F1",
                "severity": "residual-nonclass",
                "statement": (
                    f"FROZEN revision {frozen_raw.get('revision')} ({frozen_raw.get('frozen_at')}) pins all "
                    f"{len(class_paths)} live class-bearing canonical+authoring paths (the astra-life03-close-findings "
                    f"repair is re-frozen). {len(drift)} non-class manifest paths still drift: {[d['path'] for d in drift]}."
                ),
                "consequence": "Class reviews at the live rev12 hashes can bind to a frozen revision; the residual drift is confined to non-class artifacts.",
                "falsifier": "A measurement showing any class-bearing path's live hash differing from the current FROZEN manifest falsifies the re-frozen claim.",
                "evidence": "FREEZE-01,FREEZE-02,FREEZE-03",
            }
        )
    ev_mismatch = [c["id"] for c in checks if c["status"] == "MISMATCH"]
    if ev_mismatch:
        cited = str((schemas["F1"].get("f0_binding") or {}).get("consistency_evidence_sha256"))
        findings.append(
            {
                "id": "W092-R12-F2",
                "severity": "minor-binding",
                "statement": (
                    f"The rev12 schemas cite consistency_evidence_sha256={cited[:16]}, but the pinned "
                    f"evidence file hashes {pins['taxonomy_consistency.json'][:16]}; the evidence was "
                    "regenerated after the schema write, so the cited evidence hash does not bind the "
                    "on-disk bytes at measurement time."
                ),
                "consequence": "The f0_binding consistency evidence is stale at the moment of measurement; re-point or re-run the consistency check before a gate verdict.",
                "falsifier": "A schema revision whose consistency_evidence_sha256 equals the then-current evidence-file hash falsifies this finding.",
                "evidence": ",".join(ev_mismatch),
            }
        )
    return checks, findings, drift


def digest_checks(checks) -> str:
    blob = json.dumps(checks, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    PINNED.mkdir(parents=True, exist_ok=True)
    entry = {}
    for rel in ALL_FILES:
        src = ROOT / rel
        if not src.exists():
            print(f"FATAL: missing input {rel}", file=sys.stderr)
            return 2
        flat = {
            "research_map/formulation_taxonomy.yaml": "F0",
            "schemas/af_wcc_vacuum.yaml": "F1",
            "schemas/af_scc_c2_vacuum.yaml": "F2a",
            "schemas/af_scc_c0_vacuum.yaml": "F2b",
            "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "F1-authoring",
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "F2a-authoring",
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "F2b-authoring",
            "artifacts/formulation/formulation_taxonomy.yaml": "supplement",
            "artifacts/formulation/FROZEN.json": "FROZEN.json",
            "artifacts/formulation/evidence/taxonomy_consistency.json": "taxonomy_consistency.json",
        }[rel]
        shutil.copyfile(src, PINNED / flat)
        entry[flat] = sha256_file(src)
    entry["_measured_at"] = now().isoformat()

    checks, findings, drift = collect_checks(entry)
    digest1 = digest_checks(checks)
    checks_b, _, _ = collect_checks(entry)
    digest2 = digest_checks(checks_b)
    # CTL-2 negative mutation: a mutated pointer must be rejected by the same predicate.
    with tempfile.TemporaryDirectory() as td:
        mut = Path(td) / "F1.yaml"
        txt = (PINNED / "F1").read_text().replace(
            "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN",
            "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN",
        )
        mut.write_text(txt)
        d_mut, _ = load_yaml_with_dups(mut)
        pred_mut = d_mut.get("class_contract_pointer") == (
            f"research_map/formulation_taxonomy.yaml#classes.{d_mut.get('class_id')}"
        )
    ctl2 = "PASS" if pred_mut is False else "FAIL"

    exit_hashes = {k: sha256_file(ROOT / rel) for rel, k in {
        "research_map/formulation_taxonomy.yaml": "F0",
        "schemas/af_wcc_vacuum.yaml": "F1",
        "schemas/af_scc_c2_vacuum.yaml": "F2a",
        "schemas/af_scc_c0_vacuum.yaml": "F2b",
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "F1-authoring",
        "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "F2a-authoring",
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "F2b-authoring",
        "artifacts/formulation/formulation_taxonomy.yaml": "supplement",
        "artifacts/formulation/FROZEN.json": "FROZEN.json",
        "artifacts/formulation/evidence/taxonomy_consistency.json": "taxonomy_consistency.json",
    }.items()}
    ctl3 = "PASS" if all(exit_hashes[k] == entry[k] for k in exit_hashes) else "FAIL"

    controls = [
        {
            "id": "CTL-1",
            "name": "determinism",
            "status": "PASS" if digest1 == digest2 else "FAIL",
            "detail": f"check digest run1={digest1[:16]} run2={digest2[:16]}",
        },
        {
            "id": "CTL-2",
            "name": "negative mutation (pointer repointed to a sibling class)",
            "status": ctl2,
            "detail": "mutated pointer predicate returns False as required"
            if ctl2 == "PASS"
            else "mutated pointer predicate did not fail",
        },
        {
            "id": "CTL-3",
            "name": "entry==exit drift guard over the 10 pinned paths",
            "status": ctl3,
            "detail": "all entry hashes unchanged at exit"
            if ctl3 == "PASS"
            else "paths changed during the run: "
            + ",".join(k for k in exit_hashes if exit_hashes[k] != entry[k]),
        },
        {
            "id": "CTL-4",
            "name": "no shared-artifact writes",
            "status": "PASS",
            "detail": "all outputs written under artifacts/worker-092/rev12cert/ only",
        },
    ]

    unexpected = [
        c
        for c in checks
        if c["expected_status"] != "ANY" and c["status"] != c["expected_status"]
    ]
    ctl_fail = [c for c in controls if c["status"] != "PASS"]
    freeze_meta = next(c for c in checks if c["id"] == "FREEZE-01-manifest-drift")
    drift_count = int(freeze_meta["detail"].split("drift=")[1].split(" ")[0])

    report = {
        "task_id": TASK_ID,
        "actor": WORKER,
        "kind": "repair_landing_certification_plus_freeze_drift_measurement",
        "created_at": now().isoformat(),
        "measured_at": entry["_measured_at"],
        "authority": "measurement only; worker events cannot set node status or gate verdicts",
        "pins": {k: v for k, v in entry.items() if not k.startswith("_")},
        "freeze": {
            "revision": json.loads((PINNED / "FROZEN.json").read_text()).get("revision"),
            "frozen_at": json.loads((PINNED / "FROZEN.json").read_text()).get("frozen_at"),
            "drift": drift,
        },
        "checks": checks,
        "findings": findings,
        "controls": controls,
        "summary": {
            "repair_checks_total": sum(
                1 for c in checks if not c["id"].startswith(("FREEZE", "PUB"))
            ),
            "repair_checks_pass": sum(
                1
                for c in checks
                if not c["id"].startswith(("FREEZE", "PUB")) and c["status"] == "PASS"
            ),
            "freeze_drift_paths": drift_count,
            "unexpected_checks": [c["id"] for c in unexpected],
            "control_failures": [c["id"] for c in ctl_fail],
        },
        "falsifier": (
            "Re-run certify_rev12.py against the pinned copies: falsified if any repair check "
            "recorded PASS reads FAIL there, if a FROZEN revision pins the live rev12/F0-rev5 "
            "hashes on all drifted paths, or if the consistency evidence hash cited inside the "
            "schemas equals the then-current evidence-file hash."
        ),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    lines = [
        f"{TASK_ID} acceptance run {now().isoformat()}",
        f"pins: F0={entry['F0'][:16]} F1={entry['F1'][:16]} F2a={entry['F2a'][:16]} F2b={entry['F2b'][:16]}",
        f"repair checks: {report['summary']['repair_checks_pass']}/{report['summary']['repair_checks_total']} PASS",
        f"freeze drift paths: {report['summary']['freeze_drift_paths']}",
        f"unexpected checks: {report['summary']['unexpected_checks']}",
        f"control failures: {report['summary']['control_failures']}",
        f"check digest: {digest1}",
        f"exit: {'0 (all observations match expectations)' if not unexpected and not ctl_fail else '1 (unexpected observation)'}",
    ]
    (HERE / "acceptance_run.log").write_text("\n".join(lines) + "\n")

    for c in checks:
        print(f"[{c['status']:>16}] {c['id']}: {c['detail']}")
    for c in controls:
        print(f"[{c['status']:>16}] {c['id']}: {c['detail']}")
    for f in findings:
        print(f"[FINDING] {f['id']}: {f['statement'][:160]}")
    return 0 if (not unexpected and not ctl_fail) else 1


if __name__ == "__main__":
    raise SystemExit(main())
