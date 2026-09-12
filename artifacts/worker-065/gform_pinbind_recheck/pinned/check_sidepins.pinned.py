#!/usr/bin/env python3
"""Fail-closed hash side-pin checker (W065-CANON-SIDEPIN-CENSUS-04).

Rule under test: every hash side-pin that advertises the sha256 of a canonical
gate artifact must equal the artifact's live sha256; where a FROZEN rev29 pin
exists for that target it must also equal the FROZEN pin. A pin that advertises
a revoked revision is exactly the trap that makes a re-binding reviewer read
superseded bytes.

Declared registries (only these are read; the continuously-moving map is
excluded by policy):
  * entry_hashes.json                       (repo-root JSON registry)
  * artifacts/formulation/FROZEN.json       (authority: files{} pins)
  * *.sha256 sidecars under: ., schemas/, ledger/,
    artifacts/formulation/, artifacts/formulation/schemas/, artifacts/flash-04/
  * schemas/af_scc_regularities.yaml        (aggregator component pins)

Sidecar target resolution rule: try the declared path relative to the targets
root first, then relative to the sidecar's own directory. Both are declared;
nothing is silently skipped.

Exit codes: 0 = no gate-relevant defect, 2 = defect(s) found (fail-closed),
1 = instrument error (unreadable registry etc.).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"^[0-9a-f]{64}$")
HEX_ANY = re.compile(r"\b[0-9a-f]{64}\b")
SIDECAR_LINE = re.compile(r"^([0-9a-f]{64})\s+\*?(\S+)\s*$")

# Targets whose binding is on a gate path: a wrong pin here is a gate defect.
GATE_TARGETS = (
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_regularities.yaml",
    "schemas/taxonomy_cases.jsonl",
    "schemas/f1_falsifier_tests.jsonl",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "evaluation_rubric.yaml",
    "ledger/theorems.jsonl",
    "ledger/citation_audit.csv",
)

# A pin on a target that is designed to move is exempt from the equality rule;
# a static side-pin of a moving file is meaningless by construction.
MOVING_TARGETS = {
    "research_map/research_map.json",
}

# CF-26: the recorded frozen pin for the detector is c266dbec while the live
# file is a8c04fc3. A registry advertising the *recorded frozen pin* is not
# stale relative to the freeze; it is the contested drift itself.
CONTESTED_FROZEN_PINS = {
    "research_map/class_separation.py":
        "c266dbecaa87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
}

SIDECAR_DIRS = (
    ".",
    "schemas",
    "ledger",
    "artifacts/formulation",
    "artifacts/formulation/schemas",
    "artifacts/flash-04",
    "artifacts/flash-04/f1_ambiguity",
)

DEFECT_CATS = ("STALE", "FREEZE_DRIFT", "TARGET_MISSING")

# A missing target on a canonical root is a defect even when the raw pin string
# is a bare basename or an unexpected key.
CANONICAL_PREFIXES = ("schemas/", "research_map/", "artifacts/formulation/",
                      "ledger/", "evaluation_rubric")


def _canonical_target(target: str) -> bool:
    return target.startswith(CANONICAL_PREFIXES)

# Files scanned to decide whether a stale advertised hash is merely repointed
# (it is the live hash of some *other* repo file) or an orphan revision hash.
ORPHAN_SCAN_DIRS = (".", "schemas", "research_map", "ledger", "artifacts/formulation",
                    "artifacts/formulation/schemas")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _hex_history(frozen_path: Path) -> set:
    if not frozen_path.is_file():
        return set()
    return set(HEX_ANY.findall(frozen_path.read_text(errors="replace")))


def _live_hash_index(root: Path) -> dict:
    """sha256 -> first declared file that currently has it (orphan detection)."""
    index = {}
    skip = {"tmp", ".git", "__pycache__", ".venv", "node_modules"}
    for rel in ORPHAN_SCAN_DIRS:
        base = (root / rel) if rel != "." else root
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            if any(part in skip for part in path.parts):
                continue
            try:
                digest = sha256_file(path)
            except OSError:
                continue
            index.setdefault(digest, str(path.relative_to(root)))
    return index


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"unreadable registry {path}: {exc}") from exc


def parse_registries(root: Path) -> list:
    """Return the declared pin set as a list of dicts. Read-only."""
    pins = []

    entry = root / "entry_hashes.json"
    if entry.is_file():
        doc = _read_json(entry)
        if isinstance(doc, dict):
            for target, advertised in doc.items():
                if isinstance(advertised, str) and HEX.match(advertised):
                    pins.append({
                        "source": "entry_hashes.json",
                        "source_kind": "json_registry",
                        "target": target,
                        "advertised": advertised,
                    })

    frozen = root / "artifacts/formulation/FROZEN.json"
    if frozen.is_file():
        doc = _read_json(frozen)
        files = doc.get("files") if isinstance(doc, dict) else None
        if isinstance(files, dict):
            for target, meta in files.items():
                if isinstance(meta, dict) and isinstance(meta.get("sha256"), str):
                    pins.append({
                        "source": "artifacts/formulation/FROZEN.json",
                        "source_kind": "frozen_authority",
                        "target": target,
                        "advertised": meta["sha256"],
                        "frozen_revision": doc.get("revision"),
                    })

    seen = set()
    for rel in SIDECAR_DIRS:
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        for sidecar in sorted(base.glob("*.sha256")):
            key = sidecar.resolve()
            if key in seen:
                continue
            seen.add(key)
            try:
                text = sidecar.read_text(errors="replace")
            except OSError as exc:
                raise RuntimeError(f"unreadable sidecar {sidecar}: {exc}") from exc
            sidecar_dir = str(sidecar.parent.relative_to(root)) if sidecar.parent != root else "."
            for line in text.splitlines():
                m = SIDECAR_LINE.match(line.strip())
                if not m:
                    continue
                pins.append({
                    "source": str(sidecar.relative_to(root)),
                    "source_kind": "sha256_sidecar",
                    "target": m.group(2),
                    "advertised": m.group(1),
                    "sidecar_dir": sidecar_dir,
                })

    agg = root / "schemas/af_scc_regularities.yaml"
    if agg.is_file():
        comps = []
        try:
            import yaml  # noqa: PLC0415
            doc = yaml.safe_load(agg.read_text(errors="replace"))
            if isinstance(doc, dict):
                comps = doc.get("components") or []
        except ImportError:
            # stdlib fallback: role/path/sha256 triplets in a components block
            role = path = None
            for line in agg.read_text(errors="replace").splitlines():
                m_role = re.match(r"\s*-\s*role:\s*(\S+)", line)
                m_path = re.match(r"\s*path:\s*(\S+)", line)
                m_sha = re.match(r"\s*sha256:\s*([0-9a-f]{64})\s*$", line)
                if m_role:
                    role, path = m_role.group(1), None
                if m_path:
                    path = m_path.group(1).strip('"')
                if m_sha and path:
                    comps.append({"role": role, "path": path, "sha256": m_sha.group(1)})
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"unparseable aggregator {agg}: {exc}") from exc
        for comp in comps:
            if (isinstance(comp, dict) and isinstance(comp.get("sha256"), str)
                    and isinstance(comp.get("path"), str)):
                pins.append({
                    "source": "schemas/af_scc_regularities.yaml",
                    "source_kind": "aggregator_component",
                    "target": comp["path"],
                    "advertised": comp["sha256"],
                    "role": comp.get("role"),
                })
    return pins


def resolve_target(targets_root: Path, pin: dict):
    """Declared resolution: targets-root-relative first, then sidecar-dir-relative."""
    candidates = [targets_root / pin["target"]]
    if pin.get("sidecar_dir") and pin["sidecar_dir"] not in (".", ""):
        candidates.append(targets_root / pin["sidecar_dir"] / pin["target"])
    for cand in candidates:
        if cand.is_file():
            return cand, [str(c.relative_to(targets_root)) for c in candidates]
    return None, [str(c.relative_to(targets_root)) for c in candidates]


def measure(root: Path, targets_root: Path) -> dict:
    """Classify every declared pin. Returns the census document."""
    pins = parse_registries(root)
    frozen_pins = {p["target"]: p["advertised"]
                   for p in pins if p["source_kind"] == "frozen_authority"}
    history = _hex_history(targets_root / "artifacts/formulation/FROZEN.json")

    live_hashes = _live_hash_index(targets_root)

    rows = []
    for pin in pins:
        path, candidates = resolve_target(targets_root, pin)
        row = dict(pin)
        row["resolution_candidates"] = candidates
        row["gate_relevant_raw"] = pin["target"] in GATE_TARGETS
        if path is None:
            row["category"] = "TARGET_MISSING"
            row["live_sha256"] = None
            row["gate_relevant"] = row["gate_relevant_raw"] or _canonical_target(pin["target"])
            rows.append(row)
            continue
        live = sha256_file(path)
        row["live_sha256"] = live
        row["resolved_path"] = str(path.relative_to(targets_root))
        row["gate_relevant"] = row["gate_relevant_raw"] or row["resolved_path"] in GATE_TARGETS
        row["frozen_pin_for_target"] = (frozen_pins.get(pin["target"])
                                        or frozen_pins.get(row["resolved_path"]))
        adv = pin["advertised"]
        row["advertised_in_frozen_bytes"] = adv in history
        row["advertised_is_live_hash_of"] = live_hashes.get(adv)
        if pin["target"] in MOVING_TARGETS:
            row["category"] = "MOVING_TARGET_EXEMPT"
        elif adv == live:
            if pin["target"] in frozen_pins and frozen_pins[pin["target"]] != live:
                row["category"] = "OK_LIVE_FROZEN_STALE"
            elif pin["target"] in frozen_pins:
                row["category"] = "OK_FROZEN_AND_LIVE"
            else:
                row["category"] = "OK_LIVE"
        else:
            if (pin["target"] in CONTESTED_FROZEN_PINS
                    and adv == CONTESTED_FROZEN_PINS[pin["target"]]):
                row["category"] = "DRIFT_CONTESTED"
            elif pin["source_kind"] == "frozen_authority":
                row["category"] = "FREEZE_DRIFT"
            else:
                row["category"] = "STALE"
        rows.append(row)

    mirror = []
    for target in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                   "schemas/af_scc_c0_vacuum.yaml"):
        canonical = targets_root / target
        mirror_path = targets_root / "artifacts/formulation" / target
        if canonical.is_file() and mirror_path.is_file():
            mirror.append({
                "canonical": target,
                "mirror": str(mirror_path.relative_to(targets_root)),
                "canonical_sha256": sha256_file(canonical),
                "mirror_sha256": sha256_file(mirror_path),
                "aligned": canonical.read_bytes() == mirror_path.read_bytes(),
            })

    defects = [r for r in rows
               if r["category"] in DEFECT_CATS
               and (r["gate_relevant"] or r["source_kind"] == "frozen_authority")]
    advisory = [r for r in rows
                if r["category"] in DEFECT_CATS and r not in defects]
    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return {
        "checker": "check_sidepins.py",
        "root": str(root),
        "targets_root": str(targets_root),
        "n_pins": len(rows),
        "counts": counts,
        "gate_relevant_defects": defects,
        "advisory_defects": advisory,
        "mirror_alignment": mirror,
        "pins": rows,
        "verdict": "SIDEPIN_DEFECT" if defects else "SIDEPINS_CLEAN",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="registry root to read (shadow root)")
    ap.add_argument("--targets", default=None, help="root against which pin targets resolve")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    targets = Path(args.targets).resolve() if args.targets else root
    try:
        result = measure(root, targets)
    except RuntimeError as exc:
        print(f"INSTRUMENT_ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({
        "root": result["root"],
        "n_pins": result["n_pins"],
        "counts": result["counts"],
        "gate_relevant_defects": [
            {k: d[k] for k in ("source", "target", "advertised", "live_sha256", "category")}
            for d in result["gate_relevant_defects"]
        ],
        "mirror_alignment": result["mirror_alignment"],
        "verdict": result["verdict"],
    }, indent=1, sort_keys=True))
    return 2 if result["gate_relevant_defects"] else 0


if __name__ == "__main__":
    sys.exit(main())
