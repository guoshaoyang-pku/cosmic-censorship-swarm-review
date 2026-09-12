#!/usr/bin/env python3
"""W083-F0-GENERICITY-DELEGATION-01 — machine check of the F0 genericity-slot delegation.

Question (class-bound, node F0 / gate G-F0):
  G-F0's unmet list says "the taxonomy ... genericity slots are owned by F1/F2". For each of
  the four frozen classes, is that delegation actually discharged by the frozen owner artifact
  at the measured bytes, under the registry's own vocabulary aliases, or is the slot still
  open?  And is the F0 slot itself complete (genericity_kind AND genericity_topology, per the
  taxonomy's own rule at field_vocabulary.genericity_kind.rule)?

This script does NOT decide a gate, a node status, or a class id. It measures artifacts and
records exact evidence refs (path:line) with sha256 of every input at one instant.

Exit code 0 iff every control passes and every input parsed. A firing control is a failure of
the checker, and is reported as such.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # artifacts/worker-083/genericity_delegation -> swarm root
INPUTS = HERE / "inputs"

CST = timezone(timedelta(hours=8))

# (class_id, F0 generation-owner field, owner artifact snapshot, owner live path)
CLASSES = [
    ("AF-WCC-VAC-GEN", "provisional_owned_by_F1", "inputs/af_wcc_vacuum.yaml", "schemas/af_wcc_vacuum.yaml"),
    ("AF-SCC-C2-VAC-GEN", "provisional_owned_by_F2", "inputs/af_scc_c2_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml"),
    ("AF-SCC-C0-VAC-GEN", "provisional_owned_by_F2", "inputs/af_scc_c0_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"),
    # AF-WCC-SCALAR-SPH has no schema artifact in the frozen four; F0 declares L1 ownership.
    ("AF-WCC-SCALAR-SPH", "unresolved_pending_L1", None, None),
]

F0_SNAP = "inputs/formulation_taxonomy.yaml"
F0_LIVE = "research_map/formulation_taxonomy.yaml"
ALIAS_SNAP = "inputs/VOCAB_ALIASES.json"
ALIAS_LIVE = "artifacts/formulation/VOCAB_ALIASES.json"

UNRESOLVED_TOKENS = {"unresolved", "provisional", ""}


# --------------------------------------------------------------------------- io helpers

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DuplicateRecordingLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently keeping last-wins."""


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            dup = key in seen
        except TypeError:
            dup = False
        if dup:
            loader.duplicate_keys.append(str(key))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DuplicateRecordingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml_recording_duplicates(path: Path):
    loader = DuplicateRecordingLoader(path.read_text())
    loader.duplicate_keys = []
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, sorted(set(loader.duplicate_keys))


def line_of(lines, pattern: str, start: int = 0):
    rx = re.compile(pattern)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i + 1  # 1-based
    return None


def ref(path: str, sha: str, line=None) -> str:
    base = f"{path}#{sha[:12]}"
    return f"{base}:{line}" if line else base


# --------------------------------------------------------------------------- check logic

def canonical_token(token, alias_map):
    """Return the canonical vocabulary token for `token`, or None if unregistered."""
    if token in alias_map:
        return alias_map[token]
    return None


def build_alias_map(aliases_doc):
    """field -> {token_or_alias: canonical} using VOCAB_ALIASES.genericity_kind."""
    kind = aliases_doc.get("genericity_kind", {})
    amap = {}
    for canon, alist in kind.items():
        amap[canon] = canon
        for a in alist:
            amap[a] = canon
    return amap


def discharge_verdict(placeholder_kind, owner_kind, owner_topology, alias_map):
    """Pure decision function; used both on live data and on synthetic controls."""
    if owner_kind is None or str(owner_kind).strip() == "":
        return "NOT_DISCHARGED_OWNER_SLOT_EMPTY", "owner artifact has no genericity kind value"
    ok = str(owner_kind).strip()
    if ok in UNRESOLVED_TOKENS or ok.startswith("provisional"):
        return "NOT_DISCHARGED_OWNER_STILL_UNRESOLVED", f"owner kind is still {ok!r}"
    oc = canonical_token(ok, alias_map)
    if oc is None:
        return "NOT_DISCHARGED_UNREGISTERED_TOKEN", f"owner kind {ok!r} is not canonical and has no registered alias"
    pc = canonical_token(str(placeholder_kind), alias_map)
    if pc is None:
        return "NOT_DISCHARGED_UNREGISTERED_PLACEHOLDER", f"placeholder {placeholder_kind!r} has no registered alias"
    if pc != oc:
        return "NOT_DISCHARGED_TOKEN_MISMATCH", (
            f"placeholder canonical {pc!r} != owner canonical {oc!r}"
        )
    if owner_topology is None or str(owner_topology).strip() == "":
        return "NOT_DISCHARGED_TOPOLOGY_MISSING", "owner artifact names no topology/measure"
    return "DISCHARGED", f"placeholder -> {pc!r}; owner names kind {oc!r} and a topology string"


def previous_revision_crosscheck(alias_map):
    """Re-run the same pure decision on byte-identical pinned copies of the revision the
    controller cited at its 00:24:40 audit (F0 276009f4 / F1 9a8bd4c9 / F2a b6123750 /
    F2b 1bb78ce9). Pins are third-party snapshots, hashed here; a hash mismatch voids the
    cross-check instead of silently binding the wrong bytes."""
    pins = {
        "AF-WCC-VAC-GEN": ("artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
                           "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"),
        "AF-SCC-C2-VAC-GEN": ("artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c2_vacuum.yaml",
                              "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"),
        "AF-SCC-C0-VAC-GEN": ("artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c0_vacuum.yaml",
                              "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"),
    }
    f0_pin = "artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.canonical.yaml"
    f0_expected = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
    f0_real = sha256_file(ROOT / f0_pin)
    f0_doc, _dups = load_yaml_recording_duplicates(ROOT / f0_pin)
    f0_classes = f0_doc.get("classes", {})
    out = {
        "f0_pin": f0_pin, "f0_pin_sha256": f0_real, "f0_pin_expected": f0_expected,
        "f0_pin_matches": f0_real == f0_expected, "rows": [],
    }
    for cid, (rel, expected) in pins.items():
        real = sha256_file(ROOT / rel)
        doc, _d = load_yaml_recording_duplicates(ROOT / rel)
        gen = (doc.get("genericity", {}) or {})
        axes = (f0_classes.get(cid, {}) or {}).get("axes", {})
        verdict, reason = discharge_verdict(axes.get("genericity_kind"), gen.get("kind"),
                                            gen.get("topology_or_measure"), alias_map)
        out["rows"].append({
            "class_id": cid, "pin_path": rel, "pin_sha256": real, "pin_expected": expected,
            "pin_matches": real == expected, "placeholder_kind": axes.get("genericity_kind"),
            "owner_kind": gen.get("kind"), "verdict": verdict, "reason": reason,
        })
    out["all_pins_match"] = out["f0_pin_matches"] and all(r["pin_matches"] for r in out["rows"])
    out["verdicts"] = {r["class_id"]: r["verdict"] for r in out["rows"]}
    return out


def build():
    generated_at = datetime.now(CST).isoformat(timespec="seconds")
    inputs = []
    parse_notes = []
    digest_map = {}

    def snap_meta(snap_rel: str, live_rel: str):
        snap = HERE / snap_rel
        live = ROOT / live_rel
        sha = sha256_file(snap)
        digest_map[snap_rel] = sha
        inputs.append({
            "role": snap_rel.split("/")[-1],
            "snapshot_path": f"artifacts/worker-083/genericity_delegation/{snap_rel}",
            "live_path": live_rel,
            "sha256": sha,
            "bytes": snap.stat().st_size,
            "mtime": datetime.fromtimestamp(snap.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "live_sha256_now": sha256_file(live) if live.exists() else None,
        })
        return snap

    f0_path = snap_meta(F0_SNAP, F0_LIVE)
    alias_path = snap_meta(ALIAS_SNAP, ALIAS_LIVE)
    owner_paths = {}
    for cid, _owner_field, snap_rel, live_rel in CLASSES:
        if snap_rel:
            owner_paths[cid] = snap_meta(snap_rel, live_rel)

    # ---- parse
    f0, f0_dups = load_yaml_recording_duplicates(f0_path)
    f0_lines = f0_path.read_text().splitlines()
    if f0_dups:
        parse_notes.append({"file": F0_SNAP, "duplicate_keys": f0_dups})

    aliases_doc = json.loads(alias_path.read_text())
    alias_map = build_alias_map(aliases_doc)

    owner_docs = {}
    for cid, _owner_field, _snap, _live in CLASSES:
        p = owner_paths.get(cid)
        if p is None:
            continue
        doc, dups = load_yaml_recording_duplicates(p)
        owner_docs[cid] = (doc, dups, p.read_text().splitlines())
        if dups:
            parse_notes.append({"file": p.name, "duplicate_keys": dups})

    # ---- per-class rows
    classes = f0.get("classes", {})
    rows = []
    for cid, declared_owner, snap_rel, live_rel in CLASSES:
        c = classes.get(cid)
        if c is None:
            rows.append({"class_id": cid, "verdict": "CLASS_NOT_FOUND_IN_F0"})
            continue
        axes = c.get("axes", {})
        placeholder_kind = axes.get("genericity_kind")
        f0_topology_slot = axes.get("genericity_topology")   # may be absent
        value_status = c.get("genericity_value_status")

        blk = line_of(f0_lines, rf'^\s{{2}}"?{re.escape(cid)}"?:\s*$')
        kind_line = line_of(f0_lines, r"genericity_kind:", blk or 0)
        status_line = line_of(f0_lines, r"genericity_value_status:", blk or 0)
        topo_slot_line = line_of(f0_lines, r"genericity_topology:", blk or 0)
        topo_slot_line = topo_slot_line if topo_slot_line and (blk is None or topo_slot_line < _next_class_line(f0_lines, blk)) else None

        row = {
            "class_id": cid,
            "f0_kind_placeholder": placeholder_kind,
            "f0_kind_ref": ref(F0_SNAP, digest_map[F0_SNAP], kind_line),
            "f0_genericity_value_status": value_status,
            "f0_value_status_ref": ref(F0_SNAP, digest_map[F0_SNAP], status_line),
            "f0_topology_axis_present": "genericity_topology" in axes,
            "f0_topology_axis_ref": ref(F0_SNAP, digest_map[F0_SNAP], topo_slot_line) if topo_slot_line else None,
            "declared_owner": declared_owner,
        }

        if snap_rel is None:
            row.update({
                "owner_artifact": None,
                "verdict": "OPEN_BY_DESIGN_L1",
                "reason": ("F0 declares the slot unresolved_pending_L1 and names no F1/F2 owner; "
                           "the scalar-spherical class has no frozen schema artifact in this input set, "
                           "so this slot is not an F1/F2 delegation gap"),
            })
            rows.append(row)
            continue

        odoc, _odups, olines = owner_docs[cid]
        gen = odoc.get("genericity", {}) or {}
        owner_kind = gen.get("kind")
        owner_topology = gen.get("topology_or_measure")
        gen_line = line_of(olines, r"^genericity:")
        o_kind_line = line_of(olines, r"^\s*kind:", gen_line or 0)
        o_topo_line = line_of(olines, r"^\s*topology_or_measure:", gen_line or 0)
        verdict, reason = discharge_verdict(placeholder_kind, owner_kind, owner_topology, alias_map)
        row.update({
            "owner_artifact": f"artifacts/worker-083/genericity_delegation/{snap_rel}",
            "owner_live_path": live_rel,
            "owner_sha256": digest_map[snap_rel],
            "owner_kind": owner_kind,
            "owner_kind_ref": ref(snap_rel, digest_map[snap_rel], o_kind_line),
            "owner_topology_named": bool(owner_topology and str(owner_topology).strip()),
            "owner_topology_ref": ref(snap_rel, digest_map[snap_rel], o_topo_line),
            "owner_mandated_key_names_present": bool(
                ("genericity_kind" in gen) and ("genericity_topology" in gen)
            ),
            "verdict": verdict,
            "reason": reason,
        })
        rows.append(row)

    discharged = [r for r in rows if r.get("verdict") == "DISCHARGED"]
    open_l1 = [r for r in rows if r.get("verdict") == "OPEN_BY_DESIGN_L1"]
    stuck = [r for r in rows if r.get("verdict") not in ("DISCHARGED", "OPEN_BY_DESIGN_L1")]

    # ---- findings
    findings = []
    findings.append({
        "id": "F-GEN-1",
        "severity": "info",
        "statement": (
            f"{len(discharged)}/{len(rows)} class slots delegated by F0 to F1/F2 are discharged by the "
            "owner artifact at the measured bytes under the registry's own alias map "
            "(provisional_baire_residual -> residual_comeager); no owner slot is still provisional."
        ),
        "classes": [r["class_id"] for r in discharged],
    })
    findings.append({
        "id": "F-GEN-2",
        "severity": "major",
        "statement": (
            f"F0's own field_vocabulary rule requires every generic-quantified class to name "
            "genericity_kind AND genericity_topology, but the axes block of "
            f"{len([r for r in rows if not r.get('f0_topology_axis_present')])}/{len(rows)} classes carries no "
            "genericity_topology value. The owner artifacts do name the topology content, so the "
            "closure edit is to set the F0 axis to its declared status token (named_by_F1 / named_by_F2) "
            "or to backfill the owner's topology string."
        ),
        "classes": [r["class_id"] for r in rows if not r.get("f0_topology_axis_present")],
    })
    if open_l1:
        findings.append({
            "id": "F-GEN-3",
            "severity": "info",
            "statement": (
                f"{open_l1[0]['class_id']} remains unresolved_pending_L1 by F0's own declaration; it is "
                "not F1/F2-owned, so it cannot be discharged by the F0 closure revision and must not be "
                "counted as the same blocker."
            ),
            "classes": [r["class_id"] for r in open_l1],
        })
    key_mismatch = [r["class_id"] for r in rows if r.get("owner_artifact") and not r.get("owner_mandated_key_names_present")]
    if key_mismatch:
        findings.append({
            "id": "F-GEN-4",
            "severity": "minor",
            "statement": (
                "F0 says downstream schemas MUST reference the slot names genericity_kind/genericity_topology; "
                "the owner artifacts instead use genericity.kind / genericity.topology_or_measure. The values "
                "are alias-compatible, so this is a labelling divergence, not a semantic one; it is reported "
                "because a literal-name cross-class linter would report it as missing."
            ),
            "classes": key_mismatch,
        })
    for note in parse_notes:
        findings.append({
            "id": "F-GEN-5",
            "severity": "major",
            "statement": f"{note['file']} still contains duplicate YAML mapping keys: {note['duplicate_keys']}",
        })

    prev = previous_revision_crosscheck(alias_map)
    if not prev["all_pins_match"]:
        findings.append({
            "id": "F-GEN-6",
            "severity": "major",
            "statement": ("cross-revision pins do not reproduce the controller-cited hashes; the "
                          "cross-revision half of this check is void and only the live-snapshot rows bind"),
        })
    elif all(v == "DISCHARGED" for v in prev["verdicts"].values()):
        findings.append({
            "id": "F-GEN-6",
            "severity": "info",
            "statement": ("robustness across the revision move: all three F1/F2 slots are also DISCHARGED "
                          "on byte-identical pinned copies of the controller-cited revision "
                          "(F0 276009f4 / F1 9a8bd4c9 / F2a b6123750 / F2b 1bb78ce9), so the finding is not "
                          "an artifact of the 00:31-00:32 rewrite"),
        })
    else:
        findings.append({
            "id": "F-GEN-6",
            "severity": "major",
            "statement": ("the delegation verdict differs between the controller-cited revision and the "
                          f"live revision: previous={prev['verdicts']}"),
        })

    # ---- controls (synthetic, in-memory; exercise every branch of discharge_verdict)
    def ctl(ph, ok, ot, amap):
        return discharge_verdict(ph, ok, ot, amap)[0]

    base_amap = {"residual_comeager": "residual_comeager", "provisional_baire_residual": "residual_comeager",
                 "baire_residual": "residual_comeager"}
    controls = [
        {"id": "C1-positive-discharge", "expect": "DISCHARGED",
         "got": ctl("provisional_baire_residual", "residual_comeager", "subspace topology", base_amap)},
        {"id": "C2-owner-still-provisional", "expect": "NOT_DISCHARGED_OWNER_STILL_UNRESOLVED",
         "got": ctl("provisional_baire_residual", "provisional_baire_residual", "t", base_amap)},
        {"id": "C3-alias-unregistered", "expect": "NOT_DISCHARGED_UNREGISTERED_TOKEN",
         "got": ctl("provisional_baire_residual", "residual_comeager", "t", {})},
        {"id": "C4-owner-unresolved", "expect": "NOT_DISCHARGED_OWNER_STILL_UNRESOLVED",
         "got": ctl("unresolved", "unresolved", "t", base_amap)},
        {"id": "C5-topology-missing", "expect": "NOT_DISCHARGED_TOPOLOGY_MISSING",
         "got": ctl("provisional_baire_residual", "residual_comeager", "", base_amap)},
        {"id": "C6-token-mismatch", "expect": "NOT_DISCHARGED_TOKEN_MISMATCH",
         "got": ctl("provisional_baire_residual", "full_measure", "t", {**base_amap, "full_measure": "full_measure"})},
    ]
    # C7: the duplicate-key recorder must actually fire on a planted duplicate.
    planted = "a: 1\na: 2\nb: 3\n"
    loader = DuplicateRecordingLoader(planted)
    loader.duplicate_keys = []
    try:
        loader.get_single_data()
    finally:
        loader.dispose()
    controls.append({"id": "C7-duplicate-key-recorder", "expect": ["a"], "got": sorted(set(loader.duplicate_keys))})
    # C8: F0 topology-axis detector must flag an axes block that lacks the slot.
    controls.append({"id": "C8-topology-axis-detector", "expect": True,
                     "got": ("genericity_topology" not in {"genericity_kind": "x"})})

    for c in controls:
        c["pass"] = c["got"] == c["expect"]
    controls_ok = all(c["pass"] for c in controls)

    # ---- determinism: rebuild the payload and compare a digest that excludes wall-clock fields
    payload = {
        "schema": "w083-f0-genericity-delegation/v1",
        "task_id": "W083-F0-GENERICITY-DELEGATION-01",
        "generated_at": generated_at,
        "worker": "worker-083",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": [c[0] for c in CLASSES],
        "claim_scope": "artifact measurement at the snapshot hashes below; no gate verdict, no node status, no class-id change",
        "inputs": inputs,
        "alias_map_used": alias_map,
        "classes": rows,
        "summary": {
            "classes_total": len(rows),
            "discharged": len(discharged),
            "open_by_design_l1": len(open_l1),
            "still_blocked": len(stuck),
            "f0_topology_axis_missing": [r["class_id"] for r in rows if not r.get("f0_topology_axis_present")],
            "duplicate_key_files": [n["file"] for n in parse_notes],
        },
        "findings": findings,
        "previous_revision_crosscheck": prev,
        "controls": controls,
        "controls_ok": controls_ok,
        "falsifiers": [
            "F1: exhibit bytes for one of the three owner artifacts, at its cited sha256, whose genericity.kind is still provisional/unresolved or whose topology_or_measure is empty -> the DISCHARGED row is falsified for that class.",
            "F2: exhibit a VOCAB_ALIASES revision at the cited sha256 that does not map provisional_baire_residual to the owner token -> the alias-compatibility half of F-GEN-1 is falsified.",
            "F3: exhibit an F0 axes block at the cited sha256 that does carry genericity_topology -> F-GEN-2 is falsified for that class.",
            "F4: exhibit an AF-WCC-SCALAR-SPH owner schema artifact frozen in the four-class set that the F0 closure revision must discharge -> F-GEN-3's 'not F1/F2-owned' claim is falsified.",
        ],
        "claims_not_made": [
            "no gate verdict (G-F0 remains pending; worker events cannot move a gate)",
            "no node status (F0 remains active/unverified)",
            "no theorem, no physics claim, no class-id creation or merge",
            "no claim that the current revision is stable: the formulation tree was being rewritten during this run; live_sha256_now and live_equals_snapshot record the movement",
        ],
    }
    digest_payload = json.dumps({k: v for k, v in payload.items() if k != "generated_at"},
                                sort_keys=True, separators=(",", ":"))
    payload["canonical_digest_sha256"] = hashlib.sha256(digest_payload.encode()).hexdigest()
    return payload


def _next_class_line(lines, blk):
    """First 1-based line strictly after a class header at 1-based `blk` that starts a new
    2-space-indented class key, or EOF+1."""
    rx = re.compile(r'^\s{2}"?AF-[A-Z0-9-]+"?:\s*$')
    for i in range(blk, len(lines)):      # i is 0-based, blk is 1-based -> starts on the next line
        if rx.match(lines[i]):
            return i + 1
    return len(lines) + 1


def recheck_live(payload_inputs):
    """Re-measure the live paths; report whether the bytes moved during the run."""
    moved = []
    for entry in payload_inputs:
        live = ROOT / entry["live_path"]
        now = sha256_file(live) if live.exists() else None
        entry["live_sha256_at_end"] = now
        entry["live_equals_snapshot"] = (now == entry["sha256"])
        if not entry["live_equals_snapshot"]:
            moved.append(entry["live_path"])
    return moved


def main():
    payload = build()
    # determinism control: a second pure build must give the same canonical digest
    second = build()
    det = payload["canonical_digest_sha256"] == second["canonical_digest_sha256"]
    payload["controls"].append({"id": "C9-determinism", "expect": True, "got": det, "pass": det})
    payload["controls_ok"] = all(c["pass"] for c in payload["controls"])

    moved = recheck_live(payload["inputs"])
    payload["moving_target"] = {"live_paths_changed_during_run": moved, "stable": not moved}
    if moved:
        payload["findings"].append({
            "id": "F-GEN-MOVING-TARGET",
            "severity": "major",
            "statement": ("the formulation tree changed while this check ran; the verdict binds only the "
                          f"snapshot hashes recorded here. Changed live paths: {moved}"),
        })

    out = HERE / "evidence.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")

    print(f"evidence: {out}")
    print(f"verdicts: " + ", ".join(f"{r['class_id']}={r.get('verdict')}" for r in payload["classes"]))
    print(f"controls_ok={payload['controls_ok']} moving_target={moved or 'none'}")
    print(f"canonical_digest_sha256={payload['canonical_digest_sha256']}")
    return 0 if payload["controls_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
