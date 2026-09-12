#!/usr/bin/env python3
"""W082-F1-MACHINE-DEFECT-VERIFY-01

Independent, reproducible machine-defect verification for the F1 class artifact
(schemas/af_wcc_vacuum.yaml, class AF-WCC-VAC-GEN), bound to the frozen sha256
9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503.

This is a DATA-INTEGRITY / BINDING check only. It is NOT a full-schema content
review and must not be counted as a G-FORM accept. The semantic reading of the
D0 disjunction is recorded as an inherited review claim and is explicitly
marked not_checked here.

Usage:
    python3 run_checks.py                 # check frozen copy, emit JSON to stdout
    python3 run_checks.py --out evidence.json
    python3 run_checks.py --artifact <path> [--repo-root <dir>]

Deterministic: all artifact-derived fields are pure functions of the bytes.
Only wall_clock / checked_at / future_dating deltas depend on run time, and the
falsifier is stated over the artifact-derived fields alone.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FATAL: PyYAML required", file=sys.stderr)
    raise SystemExit(2)

TARGET_SHA256 = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
TZ = dt.timezone(dt.timedelta(hours=8))
REQUIRED_SLOTS = [
    "schema_version", "artifact_kind", "class_id", "node_id", "owner",
    "quantifiers", "topology", "regularity", "genericity", "i_plus",
    "visibility", "conclusion", "falsifier",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _key_repr(node) -> str:
    if isinstance(node, yaml.ScalarNode):
        return str(node.value)
    return "<%s>" % type(node).__name__


def scan_duplicate_keys(node, path="$", out=None):
    """Recursively collect duplicate mapping keys with 1-based line numbers."""
    if out is None:
        out = []
    if isinstance(node, yaml.MappingNode):
        seen: dict[str, list[int]] = {}
        for key_node, value_node in node.value:
            k = _key_repr(key_node)
            seen.setdefault(k, []).append(key_node.start_mark.line + 1)
        for k, lines in seen.items():
            if len(lines) > 1:
                out.append({"path": "%s.%s" % (path, k), "key": k, "count": len(lines), "lines": lines})
        for key_node, value_node in node.value:
            scan_duplicate_keys(value_node, "%s.%s" % (path, _key_repr(key_node)), out)
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            scan_duplicate_keys(item, "%s[%d]" % (path, i), out)
    return out


def effective_last_wins(node, key: str):
    """Return the value of the LAST occurrence of `key` at the root mapping."""
    last = None
    for key_node, value_node in node.value:
        if _key_repr(key_node) == key:
            last = value_node
    if last is None:
        return None
    if isinstance(last, yaml.ScalarNode):
        return last.value
    return "<non-scalar>"


def parse_dt(value):
    if not isinstance(value, str):
        return None
    try:
        d = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    return d


def main() -> int:
    here = Path(__file__).resolve()
    default_repo = here.parents[3]
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=str(here.parent / "frozen_f1_9a8bd4c96800.yaml"))
    ap.add_argument("--canonical", default=None,
                    help="canonical path to re-measure (default <repo>/schemas/af_wcc_vacuum.yaml)")
    ap.add_argument("--repo-root", default=str(default_repo))
    ap.add_argument("--out", default=None)
    ap.add_argument("--worker", default="worker-082")
    ap.add_argument("--instance", default="worker-082-20260912T002424-968807")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    art_path = Path(args.artifact).resolve()
    canon_path = Path(args.canonical).resolve() if args.canonical else repo / "schemas" / "af_wcc_vacuum.yaml"
    now = dt.datetime.now(TZ)

    text = art_path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    root = yaml.compose(text)

    art_sha = sha256_file(art_path)
    canon_sha = sha256_file(canon_path) if canon_path.exists() else None

    checks: list[dict] = []

    def add(cid, name, status, observed, expected, method, lines=None):
        checks.append({
            "id": cid, "name": name, "status": status, "observed": observed,
            "expected": expected, "method": method, "lines": lines or [],
        })

    # C1 binding of the frozen bytes to the measured canonical bytes
    add("W082M-01", "frozen copy is byte-identical to the canonical artifact at freeze time",
        "confirmed" if art_sha == canon_sha == TARGET_SHA256 else "refuted",
        {"frozen_sha256": art_sha, "canonical_sha256": canon_sha, "canonical_path": str(canon_path)},
        {"frozen_sha256": TARGET_SHA256, "canonical_sha256": TARGET_SHA256},
        "sha256 of frozen copy vs canonical path at run time")

    # C2 duplicate top-level keys (PyYAML silently keeps the last)
    dups = scan_duplicate_keys(root)
    top_dups = [d for d in dups if d["path"].count(".") == 1]
    add("W082M-02", "duplicate top-level YAML keys exist (YAML spec requires unique keys)",
        "confirmed" if top_dups else "refuted",
        {"duplicate_top_level_keys": top_dups, "all_duplicate_paths": dups},
        {"duplicate_top_level_keys": []},
        "yaml.compose representation graph, key occurrence count per mapping")

    # C3 empirical last-wins data loss for revised_at / revised_at_unused
    rev_eff = doc.get("revised_at")
    rev_last = effective_last_wins(root, "revised_at")
    rev_lines = [d["lines"] for d in top_dups if d["key"] == "revised_at"]
    rev_written = []
    for key_node, value_node in root.value:
        if _key_repr(key_node) == "revised_at" and isinstance(value_node, yaml.ScalarNode):
            rev_written.append({"line": key_node.start_mark.line + 1, "value": value_node.value})
    discarded = rev_written[:-1] if len(rev_written) > 1 else []
    add("W082M-03", "effective revised_at equals the last occurrence; earlier revision entries are silently discarded",
        "confirmed" if (rev_eff == rev_last and len(rev_written) > 1) else "refuted",
        {"occurrences": rev_written, "pyyaml_effective_value": rev_eff,
         "last_occurrence_value": rev_last, "discarded_entries": discarded,
         "discarded_count": len(discarded)},
        {"occurrences": "<=1"},
        "yaml.safe_load (PyYAML last-wins) vs yaml.compose document order")

    rev_unused = [{"line": k.start_mark.line + 1, "value": v.value}
                  for k, v in root.value
                  if _key_repr(k) == "revised_at_unused" and isinstance(v, yaml.ScalarNode)]
    add("W082M-04", "revised_at_unused is itself duplicated and dead (no reader), so it cannot serve as the revision timeline",
        "confirmed" if len(rev_unused) > 1 else "refuted",
        {"occurrences": rev_unused, "effective_pyyaml_value": doc.get("revised_at_unused")},
        {"occurrences": "<=1"},
        "yaml.compose key scan")

    # C5 future-dating of the effective revision stamp and binding checked_at
    binding = doc.get("f0_binding") or {}
    checked_at = parse_dt(binding.get("checked_at"))
    rev_dt = parse_dt(rev_eff)
    delta_rev = (rev_dt - now).total_seconds() if rev_dt else None
    delta_chk = (checked_at - now).total_seconds() if checked_at else None
    future = [x for x in (delta_rev, delta_chk) if x is not None and x > 0]
    add("W082M-05", "effective revised_at and f0_binding.checked_at are ahead of the wall clock at check time",
        "confirmed" if future else "refuted",
        {"effective_revised_at": rev_eff, "f0_binding_checked_at": binding.get("checked_at"),
         "wall_clock": now.isoformat(timespec="seconds"),
         "revised_at_minus_wallclock_seconds": delta_rev,
         "checked_at_minus_wallclock_seconds": delta_chk},
        {"revised_at_minus_wallclock_seconds": "<= 0", "checked_at_minus_wallclock_seconds": "<= 0"},
        "datetime.fromisoformat vs timezone-aware wall clock (+08:00)")

    # C6 contract pointer resolves into the authoring tree, not the declared canonical tree
    ptr = doc.get("class_contract_pointer") or ""
    ptr_path = ptr.split("#", 1)[0]
    ptr_abs = repo / ptr_path
    ptr_sha = sha256_file(ptr_abs) if ptr_abs.exists() else None
    declared_art = binding.get("declared_f0_artifact")
    declared_sha = binding.get("declared_f0_sha256")
    declared_abs = repo / declared_art if declared_art else None
    declared_measured = sha256_file(declared_abs) if declared_abs and declared_abs.exists() else None
    supp = binding.get("class_contract_supplement")
    supp_sha = sha256_file(repo / supp) if supp and (repo / supp).exists() else None
    pointer_in_canonical = ptr_path.startswith(("research_map/", "schemas/"))
    matches_declared = ptr_sha == declared_sha
    add("W082M-06", "class_contract_pointer resolves outside the declared canonical tree and to bytes that need not match the declared F0 hash",
        "confirmed" if (not pointer_in_canonical and not matches_declared) else "refuted",
        {"class_contract_pointer": ptr, "pointer_path": ptr_path,
         "pointer_sha256": ptr_sha, "pointer_in_canonical_tree": pointer_in_canonical,
         "pointer_matches_declared_f0_sha256": matches_declared,
         "declared_f0_artifact": declared_art, "declared_f0_sha256": declared_sha,
         "declared_artifact_measured_sha256": declared_measured,
         "declared_artifact_matches_declared_sha256": declared_measured == declared_sha,
         "class_contract_supplement": supp, "class_contract_supplement_sha256": supp_sha,
         "binding_note": binding.get("binding_note")},
        {"pointer_in_canonical_tree": True, "pointer_matches_declared_f0_sha256": True},
        "path resolution + sha256 against repo root; canonical-tree policy per ASTRA_HANDOFF")

    # C7 self-reported review_status is stale vs the hash-bound review corpus
    bound, mentions = [], []
    rdir = repo / "reviews"
    for f in sorted(rdir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        declared = [d.get(k) for k in ("reviewed_sha256", "artifact_sha256", "sha256")]
        if TARGET_SHA256 in [x for x in declared if isinstance(x, str)]:
            bound.append({"file": f.name, "reviewer": d.get("reviewer"),
                          "verdict": d.get("verdict"),
                          "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict")})
        elif TARGET_SHA256 in f.read_text(encoding="utf-8"):
            mentions.append(f.name)
    reported = ((doc.get("review_status") or {}).get("independent_reviewers"))
    add("W082M-07", "review_status.independent_reviewers is empty while reviews declare this exact hash",
        "confirmed" if (reported == [] and bound) else "refuted",
        {"reported_independent_reviewers": reported,
         "reported_verdict": (doc.get("review_status") or {}).get("verdict"),
         "hash_bound_reviews": bound,
         "hash_bound_review_count": len(bound),
         "distinct_hash_bound_reviewers": sorted({b["reviewer"] for b in bound if b["reviewer"]}),
         "files_mentioning_hash_without_declaring_it": mentions},
        {"reported_independent_reviewers": "non-empty once any verdict binds the hash"},
        "scan reviews/*.json for the exact sha256 in declared hash fields")

    # C8 syntactic disjunction in the D0 domain under a single pair binder (syntax only)
    quant = doc.get("quantifiers") or {}
    d0 = ((quant.get("domains") or {}).get("D0") or {})
    ordered0 = (quant.get("ordered") or [{}])[0]
    d0_def = d0.get("definition") or ""
    contains_or = bool(re.search(r"\bor\b", d0_def))
    reg = (doc.get("regularity") or {}).get("data_regularity")
    add("W082M-08", "D0 definition is syntactically disjunctive while bound by one (s,delta) pair [SYNTAX ONLY]",
        "confirmed" if (contains_or and ordered0.get("domain_id") == "D0") else "refuted",
        {"domain_id": ordered0.get("domain_id"), "binder": ordered0.get("binder"),
         "D0_definition": d0_def, "D0_definition_ref": d0.get("definition_ref"),
         "contains_top_level_or": contains_or,
         "regularity.data_regularity": reg,
         "semantic_family_of_statements_claim": "not_checked here; inherited from worker-088 HF-088-1 / lead-audit r2"},
        {"contains_top_level_or": False},
        "regex on the parsed D0 definition string; semantic reading NOT adjudicated by this script")

    # C9 slot presence only (not a content review)
    present = [s for s in REQUIRED_SLOTS if s in doc]
    add("W082M-09", "required top-level slots are present [PRESENCE ONLY, not a content review]",
        "confirmed" if len(present) == len(REQUIRED_SLOTS) else "refuted",
        {"present": present, "missing": [s for s in REQUIRED_SLOTS if s not in doc]},
        {"missing": []},
        "membership test on parsed mapping")

    blocking = [c["id"] for c in checks if c["status"] == "confirmed"
                and c["id"] in {"W082M-02", "W082M-03", "W082M-04", "W082M-05", "W082M-06", "W082M-07"}]
    evidence = {
        "schema_version": "w082-machine-defect-1.0",
        "task_id": "W082-F1-MACHINE-DEFECT-VERIFY-01",
        "worker": args.worker,
        "instance": args.instance,
        "checked_at": now.isoformat(timespec="seconds"),
        "wall_clock": now.isoformat(timespec="seconds"),
        "subject": {
            "node_id": doc.get("node_id"), "class_id": doc.get("class_id"),
            "canonical_path": str(canon_path.relative_to(repo)) if canon_path.is_relative_to(repo) else str(canon_path),
            "canonical_sha256": canon_sha,
            "frozen_copy": str(art_path.relative_to(repo)) if art_path.is_relative_to(repo) else str(art_path),
            "frozen_sha256": art_sha,
            "expected_binding_sha256": TARGET_SHA256,
        },
        "checks": checks,
        "summary": {
            "confirmed": [c["id"] for c in checks if c["status"] == "confirmed"],
            "refuted": [c["id"] for c in checks if c["status"] == "refuted"],
            "blocking_defect_ids": blocking,
            "verdict": "revise (data integrity / binding)" if blocking else "no blocking machine defect found",
            "counts_as_full_schema_verdict": False,
            "scope_note": "Machine data-integrity and binding check only; no independent semantic re-verification of the class content was performed.",
        },
        "falsifier": (
            "Re-measure schemas/af_wcc_vacuum.yaml. If it is republished at a new sha256 whose top-level key set has no "
            "duplicates, whose effective revised_at and f0_binding.checked_at are not ahead of the wall clock, whose "
            "class_contract_pointer resolves inside the canonical tree to the declared F0 hash, and whose "
            "review_status.independent_reviewers is non-empty, then this record is void and requires a re-run at the new "
            "hash. Re-running this script against the frozen copy "
            "(artifacts/worker-082/f1_machine_defect/frozen_f1_9a8bd4c96800.yaml, sha256 " + TARGET_SHA256 + ") must "
            "reproduce duplicate top-level keys revised_at at lines [8,10,12,14,16,20,23] and revised_at_unused at "
            "lines [26,28] with PyYAML effective revised_at 2026-09-12T00:30:00+08:00; any different artifact-derived "
            "result falsifies this evidence file."
        ),
    }

    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0 if not blocking else 1


if __name__ == "__main__":
    raise SystemExit(main())
