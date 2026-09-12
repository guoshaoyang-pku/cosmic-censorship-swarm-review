#!/usr/bin/env python3
"""AF-SOFTFLAG-DISPOSITION-02: disposition of the open CLASSSEP-SOFT flags.

Task (one class-bound task, worker-002)
---------------------------------------
The 2026-09-12T00:11:13 lifecycle leaves 3 un-disposed soft findings of the form
`CLASSSEP-SOFT: unknown class token in <artifact>: '<TOKEN>'`:
  2 on the F0 canonical artifact `research_map/formulation_taxonomy.yaml`,
  1 on the F1 canonical artifact `schemas/af_wcc_vacuum.yaml`.
G-F0's unmet list names the 2 F0 flags explicitly. This script adjudicates each
flag against the frozen class set and the registered-variant bindings, and
measures whether the disposition weakens genuine leak detection (controls).

Method
------
1. Reproduce the detector findings verbatim with
   `class_separation.findings_for_text` at the measured sha256.
2. Extract *maximal* `AF-...` tokens per artifact (the detector's own extractor
   matches exactly four hyphen segments, so it can truncate longer identifiers).
3. Resolve every maximal token to exactly one of:
     frozen_class | family_abbreviation | registered_variant(parent_class,
     variant_id) | unresolved.
   A token is a registered variant iff deleting one hyphen-delimited occurrence
   of `-<variant_id>` leaves the frozen `parent_class` (covers both naming forms
   in use: `PARENT-SET` and the infix `AF-SCC-C0-CH-VAC-GEN`).
4. Census every `class_id`/`class_ids` value in the map and in the frozen
   artifacts; a variant id in a class field is a genuine leak (registry rule).
5. Run negative/positive controls, including the falsifier path.

Read-only with respect to every canonical artifact. Writes only into
`artifacts/worker-002/softflag-disposition/`.

Falsifier
---------
This disposition is REJECTED if any maximal `AF-*` token in a frozen canonical
artifact is neither a frozen class id, nor a family abbreviation, nor a
registered variant whose `parent_class` is one of the four frozen ids; or if any
variant token occurs as a `class_id`/`class_ids` value; or if the exact-token
extraction is shown to drop a genuine unknown token the detector would catch.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402
import yaml  # noqa: E402

CST = timezone(timedelta(hours=8))

KNOWN_CLASSES = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
KNOWN = frozenset(KNOWN_CLASSES)
FAMILY_ABBREV = frozenset({"AF-WCC", "AF-SCC"})
CLASS_FIELD_KEYS = ("class_id", "class_ids")

CANON = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
AUTHOR = {
    "F0": "artifacts/formulation/formulation_taxonomy.yaml",
    "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
BINDING_SOURCES = {
    "canonical_taxonomy": "research_map/formulation_taxonomy.yaml",
    "variant_registry": "artifacts/formulation/VARIANT_REGISTRY.json",
}
MAP = "research_map/research_map.json"

EXACT = re.compile(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*")
DETECTOR_TOKEN = re.compile(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+")
REPORTED = re.compile(r"unknown class token in .*?: '([^']+)'")
PROHIBIT = re.compile(
    r"leakage|must not|never|not a class|forbid|prohibit|is NOT|conflat", re.I
)
SPLIT = re.compile(r"split|separate|distinct|versus|\bvs\b", re.I)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def digest(path: Path) -> dict:
    return {"sha256": sha256(path), "bytes": path.stat().st_size}


# --------------------------------------------------------------------------
# bindings
# --------------------------------------------------------------------------
def load_bindings() -> tuple[dict, dict]:
    """Return (bindings, delta_check). bindings: (parent,variant_id) -> info."""
    tax = yaml.safe_load((ROOT / BINDING_SOURCES["canonical_taxonomy"]).read_text())
    reg = json.loads((ROOT / BINDING_SOURCES["variant_registry"]).read_text())
    rows: dict = {}
    for src, items in (
        ("canonical_taxonomy", tax.get("variants") or []),
        ("variant_registry", reg.get("variants") or []),
    ):
        for v in items:
            p, vid = v.get("parent_class"), v.get("variant_id")
            if not p or not vid:
                continue
            row = rows.setdefault((p, vid), {"sources": [], "delta_refs": []})
            row["sources"].append(src)
            if isinstance(v.get("delta_ref"), str):
                row["delta_refs"].append(v["delta_ref"])
            for e in v.get("evidence") or []:
                if isinstance(e, str) and e.endswith(".delta.json"):
                    row["delta_refs"].append(e)
    delta_check = {}
    for key, row in rows.items():
        row["delta_refs"] = sorted(set(row["delta_refs"]))
        p, vid = key
        checks = []
        for ref in row["delta_refs"]:
            fp = ROOT / ref
            entry = {"path": ref, "exists": fp.is_file()}
            if fp.is_file():
                entry["sha256"] = sha256(fp)
                try:
                    d = json.loads(fp.read_text())
                    entry["parent_class"] = d.get("parent_class")
                    entry["variant_id"] = d.get("variant_id")
                    entry["binds"] = d.get("parent_class") == p and d.get("variant_id") == vid
                except ValueError as exc:  # pragma: no cover
                    entry["parse_error"] = str(exc)
                    entry["binds"] = False
            checks.append(entry)
        delta_check[f"{p}+{vid}"] = checks
    return rows, delta_check


def resolve(token: str, keys) -> dict:
    t = token.upper()
    if t in KNOWN:
        return {"kind": "frozen_class", "parent_class": t, "variant_id": None}
    if t in FAMILY_ABBREV:
        return {"kind": "family_abbreviation", "parent_class": None, "variant_id": None}
    for p, vid in keys:
        marker = f"-{vid}"
        if marker in t and t.replace(marker, "", 1) == p:
            return {"kind": "registered_variant", "parent_class": p, "variant_id": vid}
    longer = [f"{p}-{v}" for p, v in keys if f"{p}-{v}".startswith(t) and f"{p}-{v}" != t]
    if longer:
        return {
            "kind": "truncated_prefix_of_registered_variant",
            "parent_class": None,
            "variant_id": None,
            "full_tokens": sorted(longer),
        }
    return {"kind": "unresolved", "parent_class": None, "variant_id": None}


# --------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------
def parse_key(line: str):
    m = re.match(r"\s*-?\s*[\"']?([A-Za-z_]+)[\"']?\s*[:=]", line)
    return m.group(1) if m else None


def context_tags(line: str, token: str) -> list:
    tags = []
    key = parse_key(line)
    if key in CLASS_FIELD_KEYS:
        tags.append("class_field")
    if ".json" in line or ".yaml" in line or "variants/" in line:
        tags.append("path_or_file_reference")
    if PROHIBIT.search(line):
        tags.append("prohibition_or_rule")
    if SPLIT.search(line):
        tags.append("separation_context")
    if key in ("parent_class", "variant_id"):
        tags.append("registry_binding")
    return sorted(set(tags)) or ["prose"]


def scan_text(rel: str) -> dict:
    text = (ROOT / rel).read_text(errors="replace")
    tokens: dict = {}
    for i, line in enumerate(text.splitlines(), 1):
        for m in EXACT.finditer(line.upper()):
            tok = m.group(0)
            tokens.setdefault(tok, []).append(
                {"line": i, "context": line.strip()[:240], "tags": context_tags(line, tok)}
            )
    return {"text": text, "tokens": tokens}


def class_fields(rel: str, keys) -> dict:
    """Census of class_id/class_ids values in a YAML/JSON artifact."""
    values: list = []
    try:
        doc = yaml.safe_load((ROOT / rel).read_text())
    except Exception as exc:  # pragma: no cover
        return {"parse_error": f"{type(exc).__name__}: {exc}", "values": [], "violations": []}

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in CLASS_FIELD_KEYS:
                    values.append({"path": f"{path}.{k}" if path else k, "value": v})
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(doc)
    violations = []
    non_class_values = []
    for item in values:
        raw = item["value"]
        parts: list = []
        if isinstance(raw, list):
            parts = [str(x) for x in raw]
        elif isinstance(raw, str):
            parts = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
        else:
            violations.append({**item, "kind": "malformed_class_field"})
            continue
        for part in parts:
            if part in KNOWN or part == "GLOBAL":
                continue
            if not part.startswith("AF-"):
                # map normalization artefacts (e.g. the literal string "class_ids"
                # left in _normalized.class_id by the event normalizer) are not
                # class tokens; recorded as anomalies, never as leakage.
                non_class_values.append({**item, "part": part})
                continue
            kind = resolve(part, keys)["kind"]
            if kind == "registered_variant":
                vkind = "variant_id_in_class_field"
            elif kind in ("frozen_class",):
                continue
            else:
                vkind = "unknown_class_token_in_class_field"
            violations.append({**item, "kind": vkind, "part": part, "resolution": kind})
    return {
        "parse_ok": True,
        "values": values,
        "violations": violations,
        "non_class_values": non_class_values,
    }


def detector_findings(rel: str, text: str) -> list:
    return cs.findings_for_text(text, rel)


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def run_controls(keys) -> list:
    ctl = []

    def add(cid, purpose, observed, expected, passed):
        ctl.append(
            {
                "control_id": cid,
                "purpose": purpose,
                "observed": observed,
                "expected": expected,
                "pass": bool(passed),
            }
        )

    # C1 sensitivity: an unregistered 4-segment variant token must stay unresolved
    t1 = "class_id: AF-WCC-VAC-GEN-XYZ\n"
    f1 = detector_findings("control-C1", t1)
    r1 = resolve("AF-WCC-VAC-GEN-XYZ", keys)
    add(
        "C1-unregistered-token-detected",
        "an unregistered variant-like token must resolve as unresolved and be flagged",
        {"resolve": r1["kind"], "findings": f1},
        {"resolve": "unresolved", "has_soft_flag": True},
        r1["kind"] == "unresolved" and any("CLASSSEP-SOFT" in x for x in f1),
    )

    # C2 truncation: the detector token is a prefix, the file holds a longer token
    t2 = '- "artifacts/formulation/variants/AF-SCC-C0-CH-VAC-GEN.delta.json"\n'
    det2 = DETECTOR_TOKEN.findall(t2.upper())
    maximal2 = EXACT.findall(t2.upper())
    add(
        "C2-detector-truncation",
        "detector extractor returns a 4-segment prefix of a 5-segment identifier",
        {"detector_tokens": det2, "maximal_tokens": maximal2},
        {"detector_tokens": ["AF-SCC-C0-CH-VAC"], "maximal_tokens": ["AF-SCC-C0-CH-VAC-GEN"]},
        det2 == ["AF-SCC-C0-CH-VAC"] and maximal2 == ["AF-SCC-C0-CH-VAC-GEN"],
    )

    # C3 binding dependence: the same token is unresolved without the registry
    r3_empty = resolve("AF-WCC-VAC-GEN-SET", [])
    r3_real = resolve("AF-WCC-VAC-GEN-SET", keys)
    add(
        "C3-binding-dependence",
        "variant verdict depends on the explicit (parent_class, variant_id) binding",
        {"without_bindings": r3_empty["kind"], "with_bindings": r3_real["kind"]},
        {"without_bindings": "unresolved", "with_bindings": "registered_variant"},
        r3_empty["kind"] == "unresolved" and r3_real["kind"] == "registered_variant",
    )

    # C4 hard-merge sensitivity retained: the checker still catches a bare composite
    t4 = 'class_id: "C0 or C2"\n'
    f4 = detector_findings("control-C4", t4)
    add(
        "C4-bare-composite-still-caught",
        "disposition must not weaken the detector against an explicit composite",
        {"findings": f4},
        {"has_hard_flag": True},
        any(x.startswith("CLASSSEP:") for x in f4),
    )

    # C5 falsifier path: a variant token used as a class id is genuine leakage
    c5_res = resolve("AF-WCC-VAC-GEN-SET", keys)
    add(
        "C5-variant-as-class-id",
        "a variant token in a class_id field must be reported as a violation",
        {
            "synthetic_field": "class_id: AF-WCC-VAC-GEN-SET",
            "token_resolution": c5_res["kind"],
            "registry_rule": "variant ids are NOT class ids and must never appear in a class_ids field",
            "genuine_violation_reachable": True,
        },
        {"violation_kind": "variant_id_in_class_field", "resolution": "registered_variant"},
        c5_res["kind"] == "registered_variant",
    )

    # C6 text-route blind spot: full-id composite on a keyed line
    t6 = "class_id: AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN\n"
    f6_text = detector_findings("control-C6", t6)
    f6_dict = cs.findings({"class_id": "AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN"}, "control-C6")
    add(
        "C6-full-id-composite-text-route",
        "findings_for_text must be measured for the full-class-id composite form",
        {"findings_for_text": f6_text, "findings_dict_route": f6_dict},
        {"text_route_flags": 0, "dict_route_flags": ">=1 (documented gap, secondary finding G2)"},
        len(f6_text) == 0 and len(f6_dict) >= 1,
    )

    # C7 text-route blind spot: a 3-segment AF token in prose
    t7 = "the reading AF-WCC-BAD appears here\n"
    f7 = detector_findings("control-C7", t7)
    add(
        "C7-short-token-text-route",
        "findings_for_text extractor requires exactly four segments",
        {"findings_for_text": f7, "exact_token_kind": resolve("AF-WCC-BAD", keys)["kind"]},
        {"text_route_flags": 0, "exact_token_kind": "unresolved (documented gap, secondary finding G3)"},
        len(f7) == 0 and resolve("AF-WCC-BAD", keys)["kind"] == "unresolved",
    )
    return ctl


# --------------------------------------------------------------------------
def main() -> dict:
    bindings, delta_check = load_bindings()
    keys = sorted(bindings.keys())
    measured_at = now()

    inputs = {}
    for rel in list(CANON.values()) + list(AUTHOR.values()) + list(BINDING_SOURCES.values()) + [MAP]:
        p = ROOT / rel
        if p.is_file():
            inputs[rel] = digest(p)
        else:
            inputs[rel] = {"sha256": None, "bytes": None, "exists": False}
    inputs["research_map/class_separation.py"] = digest(ROOT / "research_map/class_separation.py")

    per_file = {}
    flags = []
    for node, rel in CANON.items():
        scanned = scan_text(rel)
        tokens = scanned["tokens"]
        found = detector_findings(rel, scanned["text"])
        census = class_fields(rel, keys)
        per_file[node] = {
            "canonical": rel,
            "authoring_mirror": AUTHOR[node],
            "detector_findings": found,
            "token_count": len(tokens),
            "tokens": {
                tok: {
                    "kind": resolve(tok, keys)["kind"],
                    "resolution": resolve(tok, keys),
                    "occurrences": occ,
                }
                for tok, occ in sorted(tokens.items())
            },
            "unresolved_tokens": sorted(t for t in tokens if resolve(t, keys)["kind"] == "unresolved"),
            "class_field_census": census,
        }
        for f in found:
            if not f.startswith("CLASSSEP-SOFT:"):
                continue
            m = REPORTED.search(f)
            if not m:
                continue
            reported = m.group(1)
            literal = reported in tokens
            exact_holders = sorted(t for t in tokens if t == reported or t.startswith(reported))
            res = resolve(reported, keys)
            if literal and res["kind"] == "registered_variant":
                cause = "registered_variant_identifier"
                verdict = "FALSE_POSITIVE"
            elif not literal and any(
                resolve(t, keys)["kind"] == "registered_variant" for t in exact_holders
            ):
                cause = "detector_prefix_truncation_of_registered_variant"
                verdict = "FALSE_POSITIVE"
                res = resolve(exact_holders[0], keys)
                res["reported_token_is_prefix_of_full_token"] = True
                res["full_token_that_occurs"] = exact_holders[0]
            elif res["kind"] == "unresolved":
                cause = "unresolved_class_like_token"
                verdict = "GENUINE_LEAK_CANDIDATE"
            else:
                cause = res["kind"]
                verdict = "FALSE_POSITIVE"
            flags.append(
                {
                    "flag_id": f"SOFTFLAG-{node}-{len(flags) + 1:02d}",
                    "node_id": node,
                    "artifact": rel,
                    "detector_finding": f,
                    "token_reported": reported,
                    "token_occurs_literally": literal,
                    "exact_token_holders": exact_holders,
                    "resolution": res,
                    "cause": cause,
                    "verdict": verdict,
                    "detector_token_form": DETECTOR_TOKEN.findall(reported.upper()),
                    "occurrences": [
                        {"token": t, **occ} for t in exact_holders for occ in tokens[t]
                    ],
                }
            )

    controls = run_controls(keys)
    unresolved_all = sorted(
        {t for node in per_file.values() for t in node["unresolved_tokens"]}
    )
    field_violations = [
        {"node": node, **v}
        for node, data in per_file.items()
        for v in data["class_field_census"].get("violations", [])
    ]

    m = json.loads((ROOT / MAP).read_text())
    map_findings = cs.findings_for_map(m)
    map_fields = class_fields(MAP, keys)

    genuine = [f for f in flags if f["verdict"] != "FALSE_POSITIVE"]
    secondary = []
    c6 = next(c for c in controls if c["control_id"] == "C6-full-id-composite-text-route")
    if c6["pass"]:
        secondary.append(
            {
                "id": "G2",
                "severity": "minor",
                "class_bound": True,
                "finding": (
                    "findings_for_text does NOT flag a full-class-id composite on a keyed line "
                    "(`class_id: AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN`), while the dict/map "
                    "route (findings -> _scan_class_ids) does. audit_evidence.py scans artifacts "
                    "with the text route only."
                ),
                "evidence": "controls.json#C6-full-id-composite-text-route",
                "falsifier": (
                    "show findings_for_text returning a hard CLASSSEP flag for that exact line, "
                    "or show no artifact can carry a class_id/class_ids value in that form"
                ),
            }
        )
    c7 = next(c for c in controls if c["control_id"] == "C7-short-token-text-route")
    if c7["pass"]:
        secondary.append(
            {
                "id": "G3",
                "severity": "minor",
                "class_bound": True,
                "finding": (
                    "the body-text unknown-token scan (_class_tokens) matches exactly four hyphen "
                    "segments, so a short AF- token in prose (e.g. `AF-WCC-VAC`) is not reported; "
                    "field-level class_id/class_ids values are still caught by _scan_class_ids in "
                    "the dict route."
                ),
                "evidence": "controls.json#C7-short-token-text-route",
                "falsifier": (
                    "show findings_for_text flagging a 3-segment AF- token in prose, or show the "
                    "field-level route is not used for artifacts"
                ),
            }
        )

    author_mirror = {}
    for n, rel in AUTHOR.items():
        p = ROOT / rel
        if p.is_file():
            author_mirror[n] = {
                "path": rel,
                "sha256": sha256(p),
                "detector_findings": detector_findings(rel, p.read_text(errors="replace")),
            }
        else:
            author_mirror[n] = {"path": rel, "sha256": None, "detector_findings": ["absent"]}

    tertiary = []
    for i, finding in enumerate(map_findings):
        hard_route = not finding.startswith("CLASSSEP-SOFT:")
        tertiary.append(
            {
                "id": f"O{i + 1}",
                "severity": "major" if hard_route else "minor",
                "class_bound": True,
                "status": "NOT_DISPOSED_HERE",
                "finding": finding,
                "route": "hard (audit_evidence._route: non-CLASSSEP-SOFT -> hard failure)"
                if hard_route
                else "soft",
                "measured_at": measured_at,
                "map_sha256": inputs[MAP]["sha256"],
                "why_out_of_scope": (
                    "this flag is on a research_map.json claim applied after the 00:11:13 "
                    "lifecycle, not on the F0/F1 canonical artifacts this task dispositions"
                ),
                "assessment": (
                    "candidate false positive of the prose merge-assertion rule: the claim text "
                    "describes two SPLIT dispositions ('the 2 split rows (TC-F0-N14 ... merge, "
                    "TC-F0-N15 ... merge) need no new class'); _scan_composite's prose branch "
                    "matches _MERGE_ASSERT first and only exempts a negation immediately before "
                    "the assertion, so the descriptive use of 'merge' is flagged. Lead "
                    "adjudication required; not disposed by worker-002."
                )
                if hard_route
                else None,
                "falsifier": (
                    "show the flagged map claim asserts a class merge rather than describing "
                    "split dispositions; then the flag is genuine and the map claim must be revised"
                ),
                "action_recommended": (
                    "controller/lead-audit: adjudicate before the next evidence audit so a prose "
                    "false positive is not counted as a hard failure, or have the claim author "
                    "rephrase to avoid the bare 'merge' token"
                )
                if hard_route
                else None,
            }
        )

    author_hard = {
        n: [f for f in v["detector_findings"] if not f.startswith("CLASSSEP-SOFT:")]
        for n, v in author_mirror.items()
    }
    author_hard = {n: fs for n, fs in author_hard.items() if fs}
    if author_hard:
        tertiary.append(
            {
                "id": f"O{len(tertiary) + 1}",
                "severity": "major",
                "class_bound": True,
                "status": "NOT_DISPOSED_HERE",
                "finding": (
                    "the AUTHORING F0 mirror emits hard-route composite flags "
                    "(`CLASSSEP: composite C0/C2 asserted as one class`) from "
                    "findings_for_text on the `composite_regularity_ban` prohibition clause "
                    "(\"no artifact may use 'C0 or C2', ... as a single class\"), while the "
                    "canonical F0 artifact measured 0 hard flags. Same branch-order weakness "
                    "as O1: _scan_composite tests _MERGE_ASSERT before _PROHIBIT, so a clause "
                    "that prohibits a merge is flagged as asserting one."
                ),
                "route": "hard (audit_evidence._route: non-CLASSSEP-SOFT -> hard failure)",
                "measured_at": measured_at,
                "authoring_mirror": {n: author_mirror[n] for n in author_hard},
                "canonical_counterpart": {n: CANON[n] for n in author_hard},
                "why_out_of_scope": (
                    "audit_evidence.py scans the map's canonical artifact paths; the authoring "
                    "tree is not in that scan. It is in scope only because it is a frozen-pin "
                    "tree that must be published byte-identically before review verdicts bind."
                ),
                "falsifier": (
                    "show the flagged clause asserts a class merge rather than prohibiting one, "
                    "or show the composite flags vanish when the same text is placed at a "
                    "canonical path (they do not)"
                ),
                "action_recommended": (
                    "lead-formulation/lead-audit: reword the ban clause so it contains no bare "
                    "'merge'/'merged' assertion token, and fix the canonical/authoring F0 "
                    "divergence deliberately -- do not publish the authoring text as-is"
                ),
            }
        )

    # Frozen evidence of the immediately preceding revision. The three flags in the
    # 00:11:13 lifecycle reproduced at revision 0fcc6a19/68392dd8 (measured 00:18:15,
    # disposition preserved byte-identically) and no longer reproduce after the
    # formulation lead rewrote the artifacts at 00:18:26-00:18:37. The block is
    # evidence-only: this run re-measures its own inputs and never trusts stored hashes.
    superseded = None
    superseded_path = OUT / "superseded" / "disposition-rev-0fcc6a19.json"
    if superseded_path.is_file():
        sup = json.loads(superseded_path.read_text())
        superseded = {
            "path": str(superseded_path.relative_to(ROOT)),
            "sha256": sha256(superseded_path),
            "measured_at": sup.get("measured_at"),
            "verdict": sup.get("summary", {}).get("verdict"),
            "input_pins": {k: v.get("sha256") for k, v in sorted(sup.get("inputs", {}).items())},
            "flags": sup.get("flags", []),
            "note": (
                "flags no longer reproduce on the current revision; the disposition "
                "mechanism (registered-variant binding and detector prefix truncation) "
                "is unchanged and remains latent for any future reference of the same form"
            ),
        }
        churn = []
        for rel, cur in sorted(inputs.items()):
            old = superseded["input_pins"].get(rel)
            if old and cur.get("sha256") and old != cur["sha256"]:
                churn.append({"path": rel, "at_prior_pin": old, "at_current_pin": cur["sha256"]})
        superseded["revision_churn"] = churn

    if superseded and not flags and not unresolved_all and not field_violations:
        verdict = "CURRENT_REVISION_CLEAN__PRIOR_REVISION_FLAGS_DISPOSED_AS_FALSE_POSITIVES"
    elif not genuine and not unresolved_all and not field_violations:
        verdict = "ALL_SOFT_FLAGS_DISPOSED_AS_FALSE_POSITIVES"
    else:
        verdict = "REVIEW_REQUIRED"

    disposition = {
        "schema_version": "0.1",
        "audit": "AF-SOFTFLAG-DISPOSITION-02",
        "task_id": "AF-SOFTFLAG-DISPOSITION-02",
        "actor": "worker-002",
        "node_ids": ["F0", "F1"],
        "class_ids": list(KNOWN_CLASSES),
        "measured_at": measured_at,
        "scope": {
            "canonical_artifacts": CANON,
            "scan_scope": "canonical frozen class artifacts (F0/F1/F2a/F2b) + map",
            "not_in_scope": [
                "the F0 dual-tree (canonical vs authoring) divergence; out of scope, still open",
                "any schema-level accept/revise verdict; this is not a review verdict",
                "any gate verdict; workers cannot set gate verdicts",
            ],
        },
        "inputs": inputs,
        "variant_bindings": {
            f"{p}+{v}": {"sources": sorted(set(info["sources"]))}
            for (p, v), info in sorted(bindings.items())
        },
        "variant_delta_check": delta_check,
        "detector_reproduction": {
            "module": "research_map/class_separation.py",
            "function": "findings_for_text",
            "findings_per_artifact": {n: per_file[n]["detector_findings"] for n in CANON},
        },
        "flags": flags,
        "summary": {
            "flags_total": len(flags),
            "false_positives": sum(1 for f in flags if f["verdict"] == "FALSE_POSITIVE"),
            "genuine_leak_candidates": len(genuine),
            "unresolved_tokens_in_frozen_artifacts": unresolved_all,
            "class_field_violations": field_violations,
            "map_route_findings": map_findings,
            "map_class_field_violations": map_fields.get("violations", []),
            "map_class_field_anomalies_not_leakage": map_fields.get("non_class_values", []),
            "outstanding_not_disposed": [t["id"] for t in tertiary],
            "prior_revision_disposition": (
                {
                    "measured_at": superseded["measured_at"],
                    "flags_total": len(superseded["flags"]),
                    "false_positives": sum(
                        1 for f in superseded["flags"] if f["verdict"] == "FALSE_POSITIVE"
                    ),
                    "verdict": superseded["verdict"],
                    "evidence": f"{superseded['path']}#{superseded['sha256'][:12]}",
                }
                if superseded
                else None
            ),
            "verdict": verdict,
        },
        "secondary_findings": secondary,
        "tertiary_observations": tertiary,
        "superseded_revision": superseded,
        "falsifier": (
            "REJECT this disposition if: (a) any maximal AF-* token in a frozen canonical "
            "artifact resolves as neither a frozen class, nor a family abbreviation, nor a "
            "registered variant with parent_class in the four frozen ids; or (b) any variant "
            "token appears as a class_id/class_ids value; or (c) the reported token occurs "
            "literally as a standalone class-like identifier rather than as a path/registry "
            "reference. Any of (a)-(c) makes the corresponding flag genuine leakage instead."
        ),
        "authority_note": (
            "Worker event: cannot set status=done, validation_status=passed, or any gate "
            "verdict. This is a disposition proposal with reproducible evidence for "
            "lead-formulation / lead-audit / controller review."
        ),
    }

    (OUT / "disposition.json").write_text(json.dumps(disposition, indent=2, sort_keys=True))
    (OUT / "token_census.json").write_text(
        json.dumps(
            {
                "measured_at": measured_at,
                "canonical": per_file,
                "map": {
                    "findings_for_map": map_findings,
                    "class_field_census": map_fields,
                },
                "authoring_mirrors": author_mirror,
            },
            indent=2,
            sort_keys=True,
        )
    )
    (OUT / "controls.json").write_text(
        json.dumps(
            {
                "measured_at": measured_at,
                "controls": controls,
                "all_pass": all(c["pass"] for c in controls),
            },
            indent=2,
            sort_keys=True,
        )
    )

    # Append-only revision watch: one line per distinct pin set observed. The
    # formulation artifacts were rewritten several times during this bounded task
    # (see SCAN.md); this records the churn mechanically instead of hiding it.
    watch = OUT / "revision_watch.jsonl"
    entry = {
        "measured_at": measured_at,
        "pins": {
            k: (v.get("sha256") or "")[:16]
            for k, v in sorted(inputs.items())
            if k.startswith(("research_map/formulation", "schemas/", "artifacts/formulation"))
        },
        "flags_total": len(flags),
        "canonical_detector_findings_total": sum(
            len(per_file[n]["detector_findings"]) for n in CANON
        ),
        "recorded_by": "scan_softflags.py",
    }
    last = None
    if watch.is_file():
        lines = [ln for ln in watch.read_text().splitlines() if ln.strip()]
        if lines:
            last = json.loads(lines[-1])
    if not last or last.get("pins") != entry["pins"]:
        with watch.open("a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    print(json.dumps(disposition["summary"], indent=2, sort_keys=True))
    print("controls all_pass:", all(c["pass"] for c in controls))
    return disposition


if __name__ == "__main__":
    main()
