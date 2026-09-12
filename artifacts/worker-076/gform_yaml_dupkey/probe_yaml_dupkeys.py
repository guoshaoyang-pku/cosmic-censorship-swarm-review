#!/usr/bin/env python3
"""W076-GFORM-YAML-DUPKEY-01: duplicate YAML mapping-key probe for the canonical
G-FORM schemas (and two context artifacts).

Why this exists
---------------
F1-review-094 (HF-094-2) and F1-review-lead-audit-r2 both record a BLOCKING
finding against schemas/af_wcc_vacuum.yaml#9a8bd4c9: duplicate top-level
`revised_at` keys. PyYAML (and any YAML 1.1/1.2 processor that follows
last-wins) silently discards every earlier occurrence, so the machine view of
the revision history is not the file's view.

This probe measures the defect at the live canonical bytes for all three
G-FORM class schemas, plus the F0 taxonomy and the F2 aggregator as context.
It is an instrument, not a verdict: it reports duplicate mapping keys at any
depth with exact line numbers, the first-wins and last-wins values, and an
independent line-based census used as a cross-check. No node status, no
validation_status and no gate verdict is set here.

Falsifier
---------
The probe is FALSE if (a) an occurrence listed as duplicate is not a duplicate
mapping key under a spec-compliant YAML parse, or (b) a duplicate found by the
line census is missed by the node walk, or (c) any input file's sha256 changes
between the pre-scan and the post-scan (status must then read UNMEASURED), or
(d) any control does not return its expected value. The defect claim is FALSE
if a canonical target is re-measured with zero duplicate mapping keys at the
same sha256.

Run from the repo root:
    python3 artifacts/worker-076/gform_yaml_dupkey/probe_yaml_dupkeys.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

TZ = timezone(timedelta(hours=8))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

TARGETS = [
    {
        "role": "primary_class_schema",
        "node_id": "F1",
        "path": "schemas/af_wcc_vacuum.yaml",
        "class_ids": ["AF-WCC-VAC-GEN"],
    },
    {
        "role": "primary_class_schema",
        "node_id": "F2a",
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
    },
    {
        "role": "primary_class_schema",
        "node_id": "F2b",
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
    },
    {
        "role": "context_taxonomy",
        "node_id": "F0",
        "path": "research_map/formulation_taxonomy.yaml",
        "class_ids": [
            "AF-WCC-VAC-GEN",
            "AF-SCC-C2-VAC-GEN",
            "AF-SCC-C0-VAC-GEN",
            "AF-WCC-SCALAR-SPH",
        ],
    },
    {
        "role": "context_aggregator_non_class",
        "node_id": "F2",
        "path": "schemas/af_scc_regularities.yaml",
        "class_ids": [],
    },
]

TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*):(?:\s|$)")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def scalar_key(node):
    """Return the scalar value of a mapping key node, or None if non-scalar."""
    if isinstance(node, yaml.ScalarNode):
        return node.value
    return None


def walk_node(node, path, dups):
    """Collect duplicate mapping keys at any depth of a composed YAML node."""
    if isinstance(node, yaml.MappingNode):
        seen = {}
        for key_node, value_node in node.value:
            key = scalar_key(key_node)
            if key is None:
                continue
            first_line = key_node.start_mark.line + 1
            if key in seen:
                seen[key].append(first_line)
            else:
                seen[key] = [first_line]
            walk_node(value_node, path + [str(key)], dups)
        for key, lines in seen.items():
            if len(lines) > 1:
                dups.append(
                    {
                        "path": "/".join(path + [key]),
                        "key": key,
                        "parent_path": "/".join(path) if path else "<document root>",
                        "occurrence_lines": lines,
                    }
                )
    elif isinstance(node, yaml.SequenceNode):
        for i, child in enumerate(node.value):
            walk_node(child, path + [f"[{i}]"], dups)


def node_to_first_wins(node):
    """Convert a composed node to Python data keeping the FIRST duplicate key."""
    if isinstance(node, yaml.MappingNode):
        out = {}
        for key_node, value_node in node.value:
            key = scalar_key(key_node)
            if key is None:
                continue
            if key not in out:
                out[key] = node_to_first_wins(value_node)
        return out
    if isinstance(node, yaml.SequenceNode):
        return [node_to_first_wins(c) for c in node.value]
    if isinstance(node, yaml.ScalarNode):
        try:
            return yaml.safe_load(node.value)
        except Exception:
            return node.value
    return None


def get_at(doc, dotted_path):
    cur = doc
    for part in dotted_path.split("/"):
        if part.startswith("[") and part.endswith("]"):
            cur = cur[int(part[1:-1])]
        else:
            cur = cur[part]
    return cur


def top_level_line_census(text: str):
    """Independent, syntax-light census of top-level mapping keys.

    Counts column-0 `key:` lines outside block scalars/comments. Good enough to
    cross-check the node walk; disagreements are reported, not hidden.
    """
    counts = {}
    in_block = False
    block_indent = None
    for raw in text.splitlines():
        if in_block:
            if raw.strip() == "":
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if indent > (block_indent or 0):
                continue
            in_block = False
        stripped = raw.split("#", 1)[0]
        m = TOP_LEVEL_KEY_RE.match(stripped)
        if m:
            key = m.group(1)
            counts[key] = counts.get(key, 0) + 1
            # crude block-scalar detection: `key: >-` / `key: |`
            tail = stripped[m.end():].strip()
            if tail[:1] in (">", "|"):
                in_block = True
                block_indent = 0
    return {k: v for k, v in counts.items() if v > 1}


def measure_file(rel_path: str):
    abs_path = os.path.join(REPO, rel_path)
    text = open(abs_path, encoding="utf-8").read()
    node = yaml.compose(text, Loader=yaml.SafeLoader)
    dups = []
    if node is not None:
        walk_node(node, [], dups)
    last_wins = yaml.safe_load(text)
    first_wins = node_to_first_wins(node) if node is not None else None
    enriched = []
    for d in dups:
        fw = lw = "<path missing>"
        try:
            fw = get_at(first_wins, d["path"])
            lw = get_at(last_wins, d["path"])
        except Exception as exc:  # pragma: no cover - defensive
            fw = lw = f"<unresolved: {exc}>"
        enriched.append(
            {
                **d,
                "first_wins_value": fw,
                "last_wins_value": lw,
                "values_differ": fw != lw,
            }
        )
    return {
        "path": rel_path,
        "sha256": sha256_file(abs_path),
        "bytes": os.path.getsize(abs_path),
        "parses_under_pyyaml": True,
        "duplicate_count": len(enriched),
        "duplicates": enriched,
        "top_level_duplicate_census": top_level_line_census(text),
        "class_id_field": (last_wins or {}).get("class_id"),
        "revision_field": (last_wins or {}).get("revision"),
        "revised_at_effective_last_wins": (last_wins or {}).get("revised_at"),
    }


def run_controls():
    controls = []

    def check(name, text, expect_dups, expect_clean_parse=True):
        try:
            node = yaml.compose(text, Loader=yaml.SafeLoader)
            dups = []
            walk_node(node, [], dups)
            parsed = yaml.safe_load(text)
            ok = len(dups) == expect_dups and isinstance(parsed, (dict, list))
        except Exception as exc:
            dups, ok = [], False
            parsed = f"<parse error: {exc}>"
        controls.append(
            {
                "name": name,
                "expect_duplicate_count": expect_dups,
                "observed_duplicate_count": len(dups),
                "observed": dups,
                "pass": bool(ok),
            }
        )

    check(
        "control_clean_unique_keys",
        "class_id: C\nrevision: 1\nnested:\n  a: 1\n  b: 2\n",
        0,
    )
    check(
        "control_nested_duplicate",
        "class_id: C\nnested:\n  a: 1\n  a: 2\n",
        1,
    )
    check(
        "control_top_level_duplicate",
        "revised_at: t1\nrevised_at: t2\n",
        1,
    )
    check(
        "control_anchor_and_merge_key_no_false_positive",
        "base: &b\n  a: 1\nchild:\n  <<: *b\n  c: 2\n",
        0,
    )
    check(
        "control_key_text_in_string_and_comment",
        "note: \"revised_at: fake\"\n# revised_at: comment\nrevision: 2\n",
        0,
    )
    return controls


def main():
    created_at = datetime.now(TZ).isoformat(timespec="seconds")

    pre = {t["path"]: sha256_file(os.path.join(REPO, t["path"])) for t in TARGETS}
    targets = []
    for t in TARGETS:
        rec = measure_file(t["path"])
        rec.update(
            {
                "role": t["role"],
                "node_id": t["node_id"],
                "declared_class_ids": t["class_ids"],
            }
        )
        targets.append(rec)
    post = {t["path"]: sha256_file(os.path.join(REPO, t["path"])) for t in TARGETS}
    stable = pre == post

    controls = run_controls()
    controls_ok = all(c["pass"] for c in controls)

    primary = [t for t in targets if t["role"] == "primary_class_schema"]
    primary_dups = {t["path"]: t["duplicate_count"] for t in primary}
    total_primary_dups = sum(primary_dups.values())

    # Cross-check node walk against the line census on the duplicate key names.
    cross_check = []
    for t in targets:
        walk_keys = sorted({d["key"] for d in t["duplicates"]})
        census_keys = sorted(t["top_level_duplicate_census"].keys())
        missed_by_walk = [k for k in census_keys if k not in walk_keys]
        cross_check.append(
            {
                "path": t["path"],
                "node_walk_duplicate_keys": walk_keys,
                "line_census_duplicate_top_level_keys": census_keys,
                "census_keys_missed_by_node_walk": missed_by_walk,
                "nested_only_duplicates_possible": any(
                    d["parent_path"] != "<document root>" for d in t["duplicates"]
                ),
                "agree": not missed_by_walk,
            }
        )
    cross_ok = all(c["agree"] for c in cross_check)

    if not stable:
        verdict = "UNMEASURED"
    elif not (controls_ok and cross_ok):
        verdict = "INVALID_INSTRUMENT"
    elif total_primary_dups > 0:
        verdict = "DEFECT_PRESENT"
    else:
        verdict = "NO_DEFECT"

    falsifier = (
        "FALSE if (a) any listed occurrence is not a duplicate mapping key under a "
        "spec-compliant YAML parse; (b) a duplicate found by the line census is missed by "
        "the node walk; (c) any target sha256 differs between pre-scan and post-scan "
        "(verdict must read UNMEASURED); (d) any control fails; (e) a canonical primary "
        "target re-measures with zero duplicate mapping keys at the same sha256."
    )

    result = {
        "schema_version": "0.1",
        "artifact_kind": "yaml_duplicate_key_probe",
        "task_id": "W076-GFORM-YAML-DUPKEY-01",
        "worker": "worker-076",
        "created_at": created_at,
        "repo_root": REPO,
        "authority_note": (
            "Worker product: evidence only. No node status, validation_status or gate "
            "verdict is set. Measured at the live canonical bytes; review/acceptance "
            "remains with the controller and group leads."
        ),
        "instrument": {
            "name": "probe_yaml_dupkeys.py",
            "method": (
                "yaml.compose node walk for duplicate mapping keys at any depth + "
                "first-wins reconstruction vs PyYAML last-wins safe_load + independent "
                "column-0 line census"
            ),
            "yaml_library": yaml.__version__,
            "python": sys.version.split()[0],
        },
        "pre_scan_sha256": pre,
        "post_scan_sha256": post,
        "hashes_stable_during_scan": stable,
        "targets": targets,
        "controls": controls,
        "controls_all_pass": controls_ok,
        "cross_check": cross_check,
        "cross_check_all_agree": cross_ok,
        "primary_class_schema_duplicate_counts": primary_dups,
        "primary_class_schema_total_duplicates": total_primary_dups,
        "verdict": verdict,
        "falsifier": falsifier,
        "limits": (
            "Duplicate mapping keys are a YAML spec violation that PyYAML resolves by "
            "last-wins; the probe reports what a spec-compliant consumer silently loses, "
            "it does not adjudicate whether the losing values matter semantically. The "
            "line census is syntax-light and only checks column-0 keys."
        ),
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_result.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
        fh.write("\n")
    result["_written_to"] = out_path
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if verdict in ("DEFECT_PRESENT", "NO_DEFECT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
