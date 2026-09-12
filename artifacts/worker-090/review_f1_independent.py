#!/usr/bin/env python3
"""Independent, reproducible review checks for F1 = schemas/af_wcc_vacuum.yaml.

Class-bound task: AF-WCC-VAC-GEN (node F1).
Reviewer: worker-090.  Method: mechanical inspection of the frozen bytes; no network,
no seeds, no state mutation.  Emits a JSON evidence record.

Usage (from repo root):
    python3 artifacts/worker-090/review_f1_independent.py \
        --expect 68392dd820505fbb8c59c2944e744d00cef5a94fecafb3e927fd14a235d7175c \
        --out artifacts/worker-090/evidence.json

Exit codes: 0 = target hash matches --expect; 3 = target moved (review void; rebind);
1 = structural check failure (target unreadable/unparseable).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = "schemas/af_wcc_vacuum.yaml"
F0_CANONICAL = "research_map/formulation_taxonomy.yaml"
F0_AUTHORING = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
FALSIFIER_SUITE = "schemas/f1_falsifier_tests.jsonl"
CST = timezone(timedelta(hours=8))

REQUIRED_SECTIONS = [
    "class_id", "class_components", "quantifiers", "topology", "data_class",
    "regularity", "genericity", "i_plus", "visibility", "conclusion", "falsifier",
    "anti_scope",
]
REQUIRED_SCALARS = [
    ("conclusion.conclusion_type", "weak_cosmic_censorship"),
    ("class_components.asymptotics", "AF"),
    ("class_components.censorship", "WCC"),
    ("class_components.matter", "VAC"),
]


def sha256_file(rel: str) -> dict:
    p = ROOT / rel
    if not p.is_file():
        return {"path": rel, "exists": False, "sha256": None, "mtime": None}
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {
        "path": rel,
        "exists": True,
        "sha256": h.hexdigest(),
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
    }


def get_path(doc: dict, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return ("unresolved", None)
        cur = cur[part]
    return ("resolved", cur)


def top_level_duplicate_keys(text: str) -> dict:
    """Duplicate mapping keys at indent 0 (YAML last-wins => parser-dependent header)."""
    positions: dict[str, list[int]] = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if m:
            positions.setdefault(m.group(1), []).append(i)
    dups = {k: v for k, v in positions.items() if len(v) > 1}
    effective = {}
    for k, lines in dups.items():
        raw = text.splitlines()[lines[-1] - 1]
        effective[k] = {"occurrences": len(lines), "lines": lines,
                        "last_win_value": raw.split(":", 1)[1].strip().strip('"')}
    return {"duplicates": dups, "effective_last_win": effective}


def symbol_definition_scan() -> dict:
    """AF_{I+} occurs in the normative statement_formal; is it defined anywhere we ship?"""
    pattern = re.compile(r"AF_\{I\+\}")
    hits, definitions = [], []
    scan_roots = ["schemas", "research_map", "artifacts/formulation"]
    for root in scan_roots:
        base = ROOT / root
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix not in {".yaml", ".yml", ".json", ".jsonl", ".md"} or not p.is_file():
                continue
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    hits.append({"file": str(p.relative_to(ROOT)), "line": i,
                                 "text": line.strip()[:200]})
                    if re.search(r"AF_\{I\+\}\s*(?::=|:=|is\s+defined|denotes|abbreviates|means)", line):
                        definitions.append({"file": str(p.relative_to(ROOT)), "line": i})
    return {"occurrences": hits, "explicit_definitions": definitions,
            "defined": bool(definitions)}


def class_separation_scan(target_text: str) -> dict:
    sys.path.insert(0, str(ROOT / "research_map"))
    try:
        import class_separation as cs  # type: ignore
    except Exception as exc:  # pragma: no cover
        return {"error": f"class_separation import failed: {exc}", "findings": None}
    findings = cs.findings_for_text(target_text, TARGET)
    return {"findings": findings, "n_findings": len(findings)}


def falsifier_suite_binding(target_hash: str) -> dict:
    p = ROOT / FALSIFIER_SUITE
    if not p.is_file():
        return {"exists": False}
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    bindings = Counter(str(r.get("binding_sha256")) for r in rows)
    return {
        "exists": True,
        "rows": len(rows),
        "bindings": dict(bindings),
        "bound_to_target": target_hash in bindings,
        "citation_status": dict(Counter(str(r.get("citation_status")) for r in rows)),
    }


def parse_time(value: str):
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", default=None, help="expected sha256 of the target")
    ap.add_argument("--out", default=None, help="write JSON evidence to this path")
    args = ap.parse_args()

    target_info = sha256_file(TARGET)
    if not target_info["exists"]:
        print(json.dumps({"error": f"missing {TARGET}"}), file=sys.stderr)
        return 1

    import yaml  # local import: only needed here

    raw = (ROOT / TARGET).read_text()
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(json.dumps({"error": f"YAML parse failed: {exc}"}), file=sys.stderr)
        return 1

    f0_canon = sha256_file(F0_CANONICAL)
    f0_auth = sha256_file(F0_AUTHORING)

    missing = [k for k in REQUIRED_SECTIONS if k not in doc]
    scalars = {}
    for dotted, expected in REQUIRED_SCALARS:
        status, value = get_path(doc, dotted)
        scalars[dotted] = {"status": status, "value": value, "expected": expected,
                           "matches": status == "resolved" and value == expected}

    binding = doc.get("f0_binding", {}) if isinstance(doc.get("f0_binding"), dict) else {}
    declared = binding.get("declared_f0_sha256")
    binding_match = {
        "declared_f0_artifact": binding.get("declared_f0_artifact"),
        "declared_f0_sha256": declared,
        "measured_canonical_sha256": f0_canon["sha256"],
        "matches_canonical": declared == f0_canon["sha256"],
        "measured_authoring_sha256": f0_auth["sha256"],
        "matches_authoring": declared == f0_auth["sha256"],
    }

    pointer = doc.get("class_contract_pointer")
    ptr_canon = ptr_auth = None
    if isinstance(pointer, str) and "#" in pointer:
        path_part, frag = pointer.split("#", 1)
        try:
            canon_doc = yaml.safe_load((ROOT / F0_CANONICAL).read_text())
            ptr_canon = {"fragment": frag, **dict(zip(("status", "value"), get_path(canon_doc, frag)))}
        except Exception as exc:
            ptr_canon = {"fragment": frag, "status": "error", "error": str(exc)}
        try:
            auth_doc = yaml.safe_load((ROOT / F0_AUTHORING).read_text())
            ptr_auth = {"fragment": frag, **dict(zip(("status", "value"), get_path(auth_doc, frag)))}
        except Exception as exc:
            ptr_auth = {"fragment": frag, "status": "error", "error": str(exc)}

    dups = top_level_duplicate_keys(raw)
    mtime = parse_time(target_info["mtime"])
    eff = dups["effective_last_win"].get("revised_at", {}).get("last_win_value")
    eff_dt = parse_time(eff) if eff else None
    now = datetime.now(CST)
    clock = {
        "file_mtime": target_info["mtime"],
        "effective_revised_at_last_wins": eff,
        "effective_revised_at_is_future_vs_mtime": bool(eff_dt and mtime and eff_dt > mtime),
        "effective_revised_at_is_future_vs_wall_clock": bool(eff_dt and eff_dt > now),
        "wall_clock_at_review": now.isoformat(timespec="seconds"),
    }

    consistency = {"path": CONSISTENCY_EVIDENCE, "exists": (ROOT / CONSISTENCY_EVIDENCE).is_file()}
    if consistency["exists"]:
        ctext = (ROOT / CONSISTENCY_EVIDENCE).read_text()
        consistency.update({
            "sha256": sha256_file(CONSISTENCY_EVIDENCE)["sha256"],
            "mtime": sha256_file(CONSISTENCY_EVIDENCE)["mtime"],
            "contains_content_hashes": "sha256" in ctext.lower(),
        })

    evidence = {
        "check_id": "W090-F1-REVIEW-CHECKS",
        "reviewer": "worker-090",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "target": target_info,
        "expected_sha256": args.expect,
        "hash_matches_expected": (args.expect is None or args.expect == target_info["sha256"]),
        "f0_canonical": f0_canon,
        "f0_authoring": f0_auth,
        "required_sections_missing": missing,
        "required_scalars": scalars,
        "f0_binding": binding_match,
        "class_contract_pointer": {
            "raw": pointer,
            "resolves_in_canonical": ptr_canon,
            "resolves_in_authoring": ptr_auth,
        },
        "duplicate_top_level_keys": dups,
        "clock_discipline": clock,
        "symbol_scan_AF_Iplus": symbol_definition_scan(),
        "class_separation": class_separation_scan(raw),
        "falsifier_suite_binding": falsifier_suite_binding(target_info["sha256"]),
        "consistency_evidence": consistency,
        "emitted_at": now.isoformat(timespec="seconds"),
    }

    if args.out:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print(json.dumps(evidence, indent=2, sort_keys=True))
    if not evidence["hash_matches_expected"]:
        print(f"TARGET MOVED: expected {args.expect}, measured {target_info['sha256']}",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
