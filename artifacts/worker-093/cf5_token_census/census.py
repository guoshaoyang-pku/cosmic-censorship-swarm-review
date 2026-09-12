#!/usr/bin/env python3
"""W093-CF5-VERIFY-01 -- independent class-token hygiene census (CF-5 disposition evidence).

Task (worker-093, bounded, class-bound): at the canonical revision pinned by this run,
independently verify the astra-classscope-02 rule --

    only the four frozen class ids may appear in any class_id/class_ids field, and every
    non-frozen reading is a VARIANT registered as {parent_class, variant_id}, never as a
    class-id-shaped token on a checker-scanned declaration surface.

This scanner does NOT import `research_map/class_separation.py` for its own detection
(independent regex + structural JSON walk); it *calls* that module only in check C2 to
record two-checker agreement on byte-identical input. It is read-only: no input file is
modified, no event is emitted, nothing under research_map/ is written.

Checks
  C1 declaration-surface token census: every `AF-...` shaped token on the four canonical
     class-bound surfaces, with key context and a DECLARATION / IDENTITY_FIELD / PATH_REF /
     PROSE_MENTION classification.  Expected: 0 non-frozen tokens.
  C2 two-checker agreement: class_separation.findings_for_text on byte-identical input.
  C3 variant-registry compliance: parents frozen, variant_id not class-id shaped, every
     evidence path (fragment stripped) resolves on disk.
  C4 on-disk variant delta filenames carry no class-id-shaped token.
  C5 global-state structural hygiene: recursive walk of research_map.json class_id/class_ids
     values; allowed = frozen four, GLOBAL (documented scope token), normalizer provenance.
  C6 checker blind spot: 5-segment tokens are truncated by class_separation's 4-block regex;
     record whether the blind spot is moot at this revision.

Falsifier (whole task): any non-frozen class-id-shaped token whose enclosing key is
class_id/class_ids on a canonical surface; or any FAIL in C1-C5; or a registry evidence path
that does not resolve.  A PASS here is a statement about these bytes only, not about
class_separation's sensitivity in general.

Usage:  python3 artifacts/worker-093/cf5_token_census/census.py [--root DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
TASK_ID = "W093-CF5-VERIFY-01"
WORKER = "worker-093"

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
FROZEN_SET = set(FROZEN)
# documented non-class scope token (comms/PROTOCOL.md assignment scope) and normalizer provenance
ALLOWED_NON_CLASS = {"GLOBAL", "class_ids", ""}

# independent detector: one-or-more hyphen blocks after AF-
TOKEN_FULL = re.compile(r"AF-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+")
# class_separation._class_tokens equivalent (exactly four blocks) to expose truncation
TOKEN_FOUR = re.compile(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+")
KEY_BEFORE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]")
DECLARATION_KEYS = {"class_id", "class_ids", "class"}
IDENTITY_KEYS = {"parent_class", "variant_id", "canonical_artifact", "authoring_artifact",
                 "frozen_parent", "base_class"}
PATHISH = re.compile(r"/|\.json\b|\.yaml\b|\.yml\b|\.md\b")

CANONICAL_SURFACES = [
    ("F0", "research_map/formulation_taxonomy.yaml"),
    ("F1", "schemas/af_wcc_vacuum.yaml"),
    ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "schemas/af_scc_c0_vacuum.yaml"),
]
ADJACENT_SURFACES = [
    ("F2-legacy", "schemas/af_scc_regularities.yaml"),
]
STRUCTURAL_INPUTS = [
    ("registry", "artifacts/formulation/VARIANT_REGISTRY.json"),
    ("frozen-manifest", "artifacts/formulation/FROZEN.json"),
    ("global-state", "research_map/research_map.json"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def key_before(line: str, pos: int) -> str:
    best = ""
    for m in KEY_BEFORE.finditer(line[:pos]):
        best = m.group(1)
    return best


def strip_strings(line: str):
    """Yield (start, end, text) spans of quoted strings on the line."""
    spans = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c in "\"'":
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == c:
                    break
                j += 1
            if j < n:
                spans.append((i, j, line[i + 1:j]))
                i = j + 1
                continue
        i += 1
    return spans


def classify_occurrence(line: str, start: int, end: int, token: str) -> str:
    key = key_before(line, start)
    if key in DECLARATION_KEYS:
        return "DECLARATION"
    if key in IDENTITY_KEYS:
        return "IDENTITY_FIELD"
    for s, e, text in strip_strings(line):
        if s <= start and end <= e and PATHISH.search(text):
            return "PATH_REF"
    if PATHISH.search(line[max(0, start - 12):end + 12]) and "/" in line[max(0, start - 8):start]:
        return "PATH_REF"
    return "PROSE_MENTION"


def variant_shaped(token: str):
    for parent in FROZEN:
        if token.upper().startswith(parent + "-"):
            return parent, token[len(parent) + 1:]
    return None, None


def walk_class_fields(obj, path=""):
    """Yield (json_path, key, value) for every class_id/class_ids value in a JSON tree."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if k in ("class_id", "class_ids"):
                vals = v if isinstance(v, list) else [v]
                for i, x in enumerate(vals):
                    yield (f"{p}[{i}]" if isinstance(v, list) else p), k, x
            yield from walk_class_fields(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_class_fields(v, f"{path}[{i}]")


def census_surface(path: Path, text: str) -> dict:
    """C1: every class-shaped token with context and classification."""
    rows = []
    nonfrozen = []
    truncated_demo = []
    for lineno, line in enumerate(text.splitlines(), 1):
        matches = list(TOKEN_FULL.finditer(line))
        if not matches:
            continue
        four = {m.group(0) for m in TOKEN_FOUR.finditer(line)}
        for m in matches:
            tok = m.group(0)
            cls = classify_occurrence(line, m.start(), m.end(), tok)
            row = {"line": lineno, "token": tok, "classification": cls,
                   "frozen": tok in FROZEN_SET, "key": key_before(line, m.start()),
                   "context": line.strip()[:220]}
            rows.append(row)
            if tok not in FROZEN_SET:
                nonfrozen.append(row)
                p, vid = variant_shaped(tok)
                row["variant_of"] = p
                row["variant_id"] = vid
            # expose class_separation's 4-block truncation for 5+ segment tokens
            if tok not in four and tok.count("-") > 4:
                truncated_demo.append({"line": lineno, "full": tok,
                                       "checker_regex_capture": sorted(four)})
    return {"rows": len(rows), "nonfrozen_rows": nonfrozen,
            "truncation_examples": truncated_demo}


def check_registry(path: Path, root: Path) -> dict:
    doc = json.loads(path.read_text())
    parents = [p.get("class_id") for p in doc.get("parent_classes", [])]
    parent_ok = parents and all(p in FROZEN_SET for p in parents)
    variants, bad_variant, unresolved, path_count = [], [], [], 0
    for v in doc.get("variants", []):
        pc, vid = v.get("parent_class"), v.get("variant_id")
        variants.append({"parent_class": pc, "variant_id": vid})
        if pc not in FROZEN_SET:
            bad_variant.append(f"{pc}#{vid}: parent not frozen")
        if not vid or variant_shaped(f"{pc}-{vid}")[1]:
            pass
        if re.fullmatch(r"AF-[A-Za-z0-9-]+", str(vid or "")):
            bad_variant.append(f"{pc}#{vid}: variant_id is class-id shaped")
        for ev in v.get("evidence", []):
            path_count += 1
            raw = str(ev).split("#")[0]
            if raw and not (root / raw).exists():
                unresolved.append(str(ev))
    for jp, key, val in walk_class_fields(doc):
        if isinstance(val, str) and val.strip() and val.strip() not in ALLOWED_NON_CLASS and val.strip() not in FROZEN_SET:
            bad_variant.append(f"registry class field {jp}={val!r} outside frozen four")
    return {"version": doc.get("version"), "parents": parents, "parents_frozen": bool(parent_ok),
            "variants": variants, "variant_count": len(variants),
            "variant_id_class_shaped": bad_variant,
            "evidence_paths_checked": path_count, "unresolved_evidence_paths": unresolved,
            "verdict": "PASS" if parent_ok and not bad_variant and not unresolved else "FAIL"}


def check_variant_filenames(vdir: Path) -> dict:
    if not vdir.is_dir():
        return {"dir": str(vdir), "exists": False, "verdict": "FAIL",
                "files": [], "class_shaped_names": [str(vdir)]}
    files, bad = [], []
    for p in sorted(vdir.glob("*.json")):
        toks = TOKEN_FULL.findall(p.name)
        # a frozen parent id in the filename is allowed ({parent}.variant-{ID}.delta.json);
        # only a non-frozen class-id-shaped token (parent+variant concatenated) is a violation.
        offenders = [t for t in toks if t not in FROZEN_SET]
        files.append(p.name)
        if offenders:
            bad.append({"file": p.name, "tokens": offenders})
    return {"dir": str(vdir), "exists": True, "files": files,
            "class_shaped_names": bad, "verdict": "PASS" if not bad else "FAIL"}


def check_map_class_fields(path: Path) -> dict:
    m = json.loads(path.read_text())
    rows, violations = [], []
    for jp, key, val in walk_class_fields(m):
        vals = val if isinstance(val, list) else [val]
        for x in vals:
            s = str(x).strip()
            if not s:
                continue
            parts = [q.strip() for q in s.split(";") if q.strip()]
            ok = all(q in FROZEN_SET or q in ALLOWED_NON_CLASS for q in parts)
            if "_normalized" in jp:
                ok = True  # normalizer provenance record, not a declaration
            row = {"json_path": jp, "key": key, "value": s, "allowed": ok}
            if not ok:
                violations.append(row)
            rows.append(row)
    return {"fields_seen": len(rows), "violations": violations,
            "by_value": {v: sum(1 for r in rows if r["value"] == v)
                         for v in sorted({r["value"] for r in rows})},
            "verdict": "PASS" if not violations else "FAIL"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="repo root (default: four levels up from this file)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    out = Path(args.out) if args.out else Path(__file__).with_name("census.json")

    inputs = []
    for group, rel in CANONICAL_SURFACES + ADJACENT_SURFACES + STRUCTURAL_INPUTS:
        p = root / rel
        inputs.append({"group": group, "path": rel, "exists": p.is_file(),
                       "sha256": sha256_file(p) if p.is_file() else None,
                       "bytes": p.stat().st_size if p.is_file() else None})

    c1 = {}
    for group, rel in CANONICAL_SURFACES + ADJACENT_SURFACES:
        p = root / rel
        text = p.read_text(errors="replace")
        res = census_surface(p, text)
        res["sha256"] = sha256_file(p)
        res["status"] = "PASS" if not res["nonfrozen_rows"] else "FAIL"
        c1[group] = res

    c2 = {}
    try:
        sys.path.insert(0, str(root / "research_map"))
        import class_separation  # type: ignore
        for group, rel in CANONICAL_SURFACES + ADJACENT_SURFACES:
            txt = (root / rel).read_text(errors="replace")
            f = class_separation.findings_for_text(txt, rel)
            c2[group] = {"findings": f, "count": len(f),
                         "status": "PASS" if not f else "FAIL"}
    except Exception as e:  # pragma: no cover
        c2 = {"error": f"{type(e).__name__}: {e}", "status": "ERROR"}

    reg = next(r for g, r in STRUCTURAL_INPUTS if g == "registry")
    c3 = check_registry(root / reg, root)
    c4 = check_variant_filenames(root / "artifacts/formulation/variants")
    c5 = check_map_class_fields(root / "research_map/research_map.json")
    trunc = {k: v["truncation_examples"] for k, v in c1.items() if v["truncation_examples"]}
    c6 = {"checker_regex": TOKEN_FOUR.pattern,
          "independent_regex": TOKEN_FULL.pattern,
          "canonical_5plus_segment_tokens": trunc,
          "moot_on_canonical_surfaces": not trunc,
          "status": "PASS"}

    checks = {"C1_declaration_census": {"surfaces": c1,
                                        "status": "PASS" if all(v["status"] == "PASS" for v in c1.values()) else "FAIL"},
              "C2_two_checker_agreement": c2,
              "C3_variant_registry": c3,
              "C4_variant_filenames": c4,
              "C5_global_state_class_fields": c5,
              "C6_checker_blind_spot": c6}
    def _status(v):
        """Uniform PASS/FAIL read: prefer explicit status/verdict, else recurse."""
        if isinstance(v, dict):
            for k in ("status", "verdict"):
                if k in v:
                    return v[k]
            return "PASS" if all(_status(x) == "PASS" for x in v.values()) else "FAIL"
        return "PASS"

    overall = "PASS" if all(_status(v) == "PASS" for v in checks.values()) else "FAIL"

    doc = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "scanner_sha256": sha256_file(Path(__file__).resolve()),
        "rule_verified": "astra-classscope-02: class_ids fields carry only the four frozen ids; "
                         "non-frozen readings are variants {parent_class, variant_id}",
        "inputs": inputs,
        "checks": checks,
        "overall_verdict": overall,
        "falsifier": "Any non-frozen class-id-shaped token on a canonical checker-scanned surface whose "
                     "enclosing key is class_id/class_ids (i.e. variant_shaped() -> DECLARATION), or any "
                     "FAIL in C1-C5, or a variant-registry evidence path that fails to resolve, falsifies "
                     "this verdict. Scope: these bytes at the recorded sha256 only.",
        "scope_limits": [
            "PASS is a statement about the pinned bytes, not proof of checker sensitivity.",
            "Historical logs/checkpoints/events/reviews that quote the pre-fix class-id-shaped variant "
            "names are not declarations and are out of scope; see C1 nonfrozen classification.",
            "The unrelated pre-existing hard flag claims[36] (composite C0/C2; directive "
            "astra-classscope-02 already adjudicated it) and the dual-tree divergence are not re-adjudicated here.",
        ],
    }
    body = json.dumps(doc, indent=2, sort_keys=True)
    out.write_text(body + "\n")
    print(json.dumps({"task_id": TASK_ID, "overall_verdict": overall,
                      "checks": {k: _status(v) for k, v in checks.items()},
                      "out": str(out), "census_sha256": sha256_text(body)}, indent=2))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
