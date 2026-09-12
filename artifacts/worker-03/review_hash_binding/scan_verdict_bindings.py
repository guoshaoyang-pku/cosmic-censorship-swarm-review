#!/usr/bin/env python3
"""VERDICT-BIND-01 -- do independent review verdicts bind to the FROZEN revision?

Why this exists
---------------
G-FORM's acceptance criterion is "all three schemas exist ... reviewers 17,18 accept with
cited sha256".  audit_evidence.py checks (a) dual-tree divergence between
`schemas/*.yaml` and `artifacts/formulation/schemas/*.yaml` and (b) drift of entries in
`research_map.json:frozen_artifacts`.  Neither reads the review store, so nothing measures
whether an *accepted verdict* actually cites the sha256 of the artifact the gate would
freeze.  This scanner measures exactly that, and nothing else.

What it does
------------
1. Hashes every candidate artifact under a fixed whitelist of roots (deterministic set).
2. Reads the FROZEN manifest (default artifacts/formulation/FROZEN.json) and records
   declared-vs-disk hashes for every entry.
3. Reads the review stores (reviews/*.json, artifacts/formulation/reviews/*.json).
4. For every review, extracts *binding* fields (keys containing sha256/sha/hash/checksum)
   and *mentioned* hex strings, resolves each 12-64 hex prefix against the on-disk hash
   index, and classifies the verdict:
       binds_frozen      cited sha == FROZEN-declared sha of the review's canonical target
       binds_authoring   cited sha resolves to the same-basename file outside the frozen tree
       resolves_other    cited sha resolves to some other on-disk file
       unresolved        cited sha matches no file on disk (revision overwritten)
       unbound           review declares no binding field at all
   The primary binding is chosen by an explicit key priority, not alphabetically.
5. Reports per-class G-FORM eligibility: an accept counts only if it binds_frozen and is
   not self-declared non-independent, plus every other verdict per class for context.
6. Emits `findings` (id, severity, statement, evidence_refs as path#sha256-prefix,
   falsifier) so downstream review does not have to re-derive them from raw rows.

Determinism / limits
--------------------
* stdlib only, no network, sorted iteration everywhere; only `generated_at` and the
  tool's own sha256 vary between runs.
* Unresolved citations are EXPECTED under an overwrite-in-place workflow; they mean
  "cannot be re-verified against current disk", not "fabricated".
* A review is only as machine-readable as its declared fields; prose-only citations are
  reported as `mention` and never upgraded to a binding.
* This measures citation binding only; it makes no claim about the mathematical content
  of any review or schema.

Usage:
  python3 artifacts/worker-03/review_hash_binding/scan_verdict_bindings.py \
      [--root .] [--out artifacts/worker-03/review_hash_binding/report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))

FROZEN_DEFAULT = "artifacts/formulation/FROZEN.json"
REVIEW_STORES = ("reviews", "artifacts/formulation/reviews")
HASH_ROOTS = ("schemas", "research_map", "ledger", "reviews", "numerics",
              "evaluation", "artifacts", "runtime/bin")
ROOT_FILES = ("evaluation_rubric.yaml",)

# authoring tree -> published/frozen tree (the layout audit_evidence.py:123-135 watches)
TREE_PAIRS = (
    ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    ("research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"),
)

# G-FORM class targets, keyed by basename.
GATE_TARGETS = (
    ("AF-WCC-VAC-GEN", "af_wcc_vacuum.yaml"),
    ("AF-SCC-C2-VAC-GEN", "af_scc_c2_vacuum.yaml"),
    ("AF-SCC-C0-VAC-GEN", "af_scc_c0_vacuum.yaml"),
)

HEX_RE = re.compile(r"^[0-9a-f]{12,64}$")
PATH_KEYS = ("target_path", "artifact_path", "artifact", "path")
BIND_KEY_HINTS = ("sha256", "sha", "hash", "checksum")
# semantic priority for the *primary* binding field
BIND_PRIORITY = ("artifact_sha256", "target_sha256", "reviewed_sha256", "reviewed_sha",
                 "dispatched_sha256", "own_hash_of_target", "manifest_sha256",
                 "manifest_sha256_before_run", "pin_check_sha256", "sha256", "sha", "hash")
REVIEW_MARKERS = ("verdict", "event_type", "review_id", "review_kind")


# ----------------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_prefix(value) -> bool:
    """A 12-64 char lowercase hex string. Pure-digit values need >=32 chars so that
    counters/ids (e.g. '1016578408204') are not mistaken for truncated hashes."""
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    if not HEX_RE.match(v):
        return False
    if len(v) >= 32:
        return True
    return any(c in "abcdef" for c in v)


def looks_like_path(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v or "\n" in v or len(v) > 300:
        return False
    return "/" in v or v.endswith((".yaml", ".yml", ".json", ".jsonl", ".md", ".py"))


def declared_target(doc: dict):
    for key in PATH_KEYS:
        v = doc.get(key)
        if isinstance(v, str) and looks_like_path(v):
            return v
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and looks_like_path(item):
                    return item
    return None


def walk_strings(obj, path="$"):
    """Yield (json_path, key, string_value) for every string in the document."""
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from walk_strings(obj[k], f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from walk_strings(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, path.rsplit(".", 1)[-1], obj


def reviewer_of(doc: dict, filename: str) -> str:
    for key in ("reviewer", "reviewer_id", "actor"):
        v = doc.get(key)
        if isinstance(v, str) and v:
            return v
    return filename.split("-review")[0]


def pick_primary(binding: list) -> dict:
    """Choose the primary binding field by semantic priority, then by shallowest path."""
    if not binding:
        return None

    def rank(rec):
        key = rec["key"].lower()
        prio = BIND_PRIORITY.index(key) if key in BIND_PRIORITY else len(BIND_PRIORITY)
        depth = rec["json_path"].count(".") + rec["json_path"].count("[")
        return (prio, depth, rec["json_path"])

    return sorted(binding, key=rank)[0]


# ----------------------------------------------------------------------------- scan
def build_index(root: Path) -> tuple:
    """Return (digest -> [paths], path -> digest). Both are frozen at scan time so that
    evidence refs in the report equal the hashes recorded in the rows, even though other
    agents keep editing files while the report is assembled."""
    index: dict[str, list[str]] = {}
    path_digest: dict[str, str] = {}
    files: list[Path] = []
    for rel in HASH_ROOTS:
        d = root / rel
        if d.is_dir():
            files.extend(p for p in d.rglob("*") if p.is_file() and not p.name.startswith("._"))
    for rel in ROOT_FILES:
        p = root / rel
        if p.is_file():
            files.append(p)
    for p in sorted(set(files)):
        try:
            digest = sha256_file(p)
        except OSError:
            continue
        rel = str(p.relative_to(root))
        index.setdefault(digest, []).append(rel)
        path_digest[rel] = digest
    return index, path_digest


def load_reviews(root: Path) -> list:
    out = []
    for store in REVIEW_STORES:
        d = root / store
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            if p.name.startswith("._"):
                continue
            try:
                doc = json.loads(p.read_text(errors="replace"))
            except ValueError as e:
                out.append({"review_file": str(p.relative_to(root)), "parse_error": str(e)})
                continue
            if not isinstance(doc, dict):
                continue
            if not any(m in doc for m in REVIEW_MARKERS):
                continue
            out.append({"review_file": str(p.relative_to(root)),
                        "sha256": sha256_file(p), "doc": doc})
    return out


def resolve(prefix: str, index: dict) -> list:
    p = prefix.strip().lower()
    return sorted(path for digest, paths in index.items() if digest.startswith(p) for path in paths)


def classify(review: dict, index: dict, frozen_by_basename: dict) -> dict:
    doc = review["doc"]
    target = declared_target(doc)
    binding, mentions = [], []
    for jpath, key, value in walk_strings(doc):
        if not looks_like_prefix(value):
            continue
        rec = {"json_path": jpath, "key": key, "prefix": value.strip().lower(),
               "resolves_to": resolve(value, index)}
        if any(h in key.lower() for h in BIND_KEY_HINTS):
            binding.append(rec)
        else:
            mentions.append(rec)

    canonical = frozen_by_basename.get(Path(target).name) if target else None
    for rec in binding + mentions:
        rec["is_frozen_revision"] = bool(canonical and canonical in rec["resolves_to"])
        rec["binds_declared_target"] = bool(target and target in rec["resolves_to"])

    primary = pick_primary(binding)
    if primary is None:
        verdict_binding = "unbound"
    elif primary.get("is_frozen_revision"):
        verdict_binding = "binds_frozen"
    elif canonical and Path(target).name in {Path(x).name for x in primary["resolves_to"]} \
            and canonical not in primary["resolves_to"]:
        verdict_binding = "binds_authoring"
    elif primary["resolves_to"]:
        verdict_binding = "resolves_other"
    else:
        verdict_binding = "unresolved"

    counts_independent = doc.get("counts_as_independent_second_verdict")
    return {
        "review_file": review["review_file"],
        "review_sha256": review["sha256"],
        "review_id": doc.get("review_id") or doc.get("event_id"),
        "reviewer": reviewer_of(doc, Path(review["review_file"]).name),
        "target_id": doc.get("target_id") or doc.get("target"),
        "declared_target_path": target,
        "canonical_frozen_path": canonical,
        "counts_as_independent_second_verdict": counts_independent,
        "verdict": doc.get("verdict"),
        "score": doc.get("score"),
        "primary_binding_field": primary["json_path"] if primary else None,
        "binding_fields": binding,
        "mentioned_hashes": mentions,
        "verdict_binding": verdict_binding,
        "binding_prefix": primary["prefix"] if primary else None,
    }


def scan(root: Path, frozen_rel: str) -> dict:
    frozen_path = root / frozen_rel
    frozen_bytes = frozen_path.read_bytes() if frozen_path.is_file() else b"{}"
    frozen_manifest_sha = hashlib.sha256(frozen_bytes).hexdigest()
    frozen_doc = json.loads(frozen_bytes)
    frozen_files = frozen_doc.get("files", {}) if isinstance(frozen_doc, dict) else {}
    frozen_by_basename = {Path(p).name: p for p in frozen_files}

    index, path_digest = build_index(root)

    declared_vs_disk = []
    for rel, meta in sorted(frozen_files.items()):
        p = root / rel
        declared = str(meta.get("sha256", ""))
        disk = sha256_file(p) if p.is_file() else None
        declared_vs_disk.append({
            "path": rel,
            "declared_sha256": declared,
            "disk_sha256": disk,
            "match": bool(disk and disk == declared),
            "disk_bytes": p.stat().st_size if p.is_file() else None,
            "declared_bytes": meta.get("bytes"),
        })

    tree_pairs = []
    for author_rel, canon_rel in TREE_PAIRS:
        ap, cp = root / author_rel, root / canon_rel
        ah = sha256_file(ap) if ap.is_file() else None
        ch = sha256_file(cp) if cp.is_file() else None
        tree_pairs.append({
            "authoring_path": author_rel, "authoring_sha256": ah,
            "published_path": canon_rel, "published_sha256": ch,
            "identical": bool(ah and ch and ah == ch),
        })

    reviews = []
    for review in load_reviews(root):
        if "doc" not in review:
            reviews.append(review)
            continue
        reviews.append(classify(review, index, frozen_by_basename))

    # which side of each divergent pair do review citations actually land on?
    cited_paths = set()
    for r in reviews:
        if not isinstance(r, dict) or "binding_fields" not in r:
            continue
        for rec in r["binding_fields"] + r["mentioned_hashes"]:
            cited_paths.update(rec["resolves_to"])
    for pair in tree_pairs:
        pair["authoring_cited_by_reviews"] = pair["authoring_path"] in cited_paths
        pair["published_cited_by_reviews"] = pair["published_path"] in cited_paths

    gate = {"gate_id": "G-FORM",
            "criteria": ("all three schemas exist with exact quantifiers/topology/regularity/"
                         "genericity/I+/visibility/conclusion_type; no C0/C2 merge; reviewers "
                         "17,18 accept with cited sha256"),
            "classes": []}
    for class_id, basename in GATE_TARGETS:
        canon = frozen_by_basename.get(basename)
        rows = []
        for r in reviews:
            if not isinstance(r, dict) or "verdict_binding" not in r:
                continue
            tgt = r.get("declared_target_path")
            if not tgt or Path(tgt).name != basename:
                continue
            independent = r["counts_as_independent_second_verdict"] is not False
            rows.append({
                "review_file": r["review_file"], "reviewer": r["reviewer"],
                "verdict": r["verdict"], "binding_prefix": r["binding_prefix"],
                "verdict_binding": r["verdict_binding"],
                "counts_as_independent_second_verdict": r["counts_as_independent_second_verdict"],
                "eligible_for_gate": bool(r["verdict"] == "accept" and independent
                                          and r["verdict_binding"] == "binds_frozen"),
            })
        accepts = [x for x in rows if x["verdict"] == "accept"]
        gate["classes"].append({
            "class_id": class_id,
            "canonical_path": canon,
            "frozen_declared_sha256": (frozen_files.get(canon, {}) or {}).get("sha256"),
            "verdicts": rows,
            "accept_count": len(accepts),
            "eligible_count": sum(1 for x in rows if x["eligible_for_gate"]),
        })

    accept_counts = {}
    for r in reviews:
        if isinstance(r, dict) and r.get("verdict") == "accept":
            accept_counts[r["verdict_binding"]] = accept_counts.get(r["verdict_binding"], 0) + 1

    # ---------------------------------------------------------------- findings
    def ev(rel: str, prefix_len: int = 12) -> str:
        digest = path_digest.get(rel)
        if digest:
            return f"{rel}#{digest[:prefix_len]}"
        p = root / rel
        return f"{rel}#{sha256_file(p)[:prefix_len]}" if p.is_file() else rel

    drifted = [d for d in declared_vs_disk if not d["match"]]
    divergent = [p for p in tree_pairs if not p["identical"]]
    unresolved = [r for r in reviews if isinstance(r, dict)
                  and r.get("verdict_binding") == "unresolved"]
    authoring_bound = [r for r in reviews if isinstance(r, dict)
                       and r.get("verdict_binding") == "binds_authoring"]
    ineligible_accepts = [r for r in reviews if isinstance(r, dict)
                          and r.get("verdict") == "accept"
                          and r.get("verdict_binding") != "binds_frozen"]

    map_doc = json.loads((root / "research_map/research_map.json").read_text())
    map_frozen_paths = {f.get("path") for f in map_doc.get("frozen_artifacts", [])}
    canon_paths = {c["canonical_path"] for c in gate["classes"]}
    map_missing = sorted(p for p in canon_paths if p and p not in map_frozen_paths)

    findings = []
    if all(c["eligible_count"] == 0 for c in gate["classes"]):
        findings.append({
            "id": "W03-FB-01",
            "severity": "major",
            "statement": ("No G-FORM class has an eligible independent accept verdict bound to the "
                          "FROZEN-declared sha256: " +
                          "; ".join(f"{c['class_id']} eligible=0/{c['accept_count']} accepts"
                                    for c in gate["classes"])),
            "evidence_refs": [ev(frozen_rel), ev("research_map/research_map.json")] +
                             [ev(c["canonical_path"]) for c in gate["classes"] if c["canonical_path"]],
            "falsifier": ("A review file with verdict=accept that cites the FROZEN-declared sha256 of "
                          "its class schema appears in reviews/ or artifacts/formulation/reviews/ on re-scan."),
        })
    if divergent:
        findings.append({
            "id": "W03-FB-02",
            "severity": "major",
            "statement": (f"{len(divergent)}/{len(tree_pairs)} authoring/published tree pairs differ; "
                          "review citations land on the authoring side (" +
                          ", ".join(p["authoring_path"] for p in divergent) + ")"),
            "evidence_refs": [ev(p["authoring_path"]) for p in divergent] +
                             [ev(p["published_path"]) for p in divergent],
            "falsifier": ("Any listed pair is byte-identical on re-hash, or the review store cites the "
                          "published side for a pair listed as authoring-cited."),
        })
    if drifted:
        findings.append({
            "id": "W03-FB-03",
            "severity": "major",
            "statement": ("FROZEN.json declares sha256 for files whose bytes on disk no longer match: " +
                          ", ".join(f"{d['path']} {d['declared_sha256'][:12]}->{str(d['disk_sha256'])[:12]}"
                                    for d in drifted)),
            "evidence_refs": [ev(frozen_rel)] + [ev(d["path"]) for d in drifted],
            "falsifier": "A drifted entry matches its declared sha256 on re-hash.",
        })
    if map_missing:
        findings.append({
            "id": "W03-FB-04",
            "severity": "minor",
            "statement": ("research_map.json:frozen_artifacts does not pin the current canonical "
                          "formulation artifacts, so the drift check in audit_evidence.py cannot "
                          "protect them: " + ", ".join(map_missing)),
            "evidence_refs": [ev("research_map/research_map.json")] + [ev(p) for p in map_missing],
            "falsifier": "The map's frozen_artifacts list contains every canonical formulation path.",
        })
    if unresolved:
        findings.append({
            "id": "W03-FB-05",
            "severity": "minor",
            "statement": (f"{len(unresolved)}/{len([r for r in reviews if isinstance(r, dict)])} review "
                          "files cite a sha256 that resolves to no file on disk (revision overwritten "
                          "in place); those verdicts cannot be re-verified against current disk: " +
                          ", ".join(r["review_file"] for r in unresolved)),
            "evidence_refs": [ev(r["review_file"]) for r in unresolved],
            "falsifier": ("Every listed citation resolves to an on-disk artifact on re-scan "
                          "(e.g. because revision snapshots were published)."),
        })
    if authoring_bound or ineligible_accepts:
        findings.append({
            "id": "W03-FB-06",
            "severity": "minor",
            "statement": (f"{len(authoring_bound)} review files bind to the authoring tree; "
                          f"{len(ineligible_accepts)} accept verdicts exist and none binds the frozen "
                          "revision"),
            "evidence_refs": [ev(r["review_file"]) for r in sorted(
                authoring_bound + ineligible_accepts, key=lambda x: x["review_file"])],
            "falsifier": "Any of these reviews cites the FROZEN-declared sha256 of its target.",
        })

    for f in findings:
        f["evidence_refs"] = list(dict.fromkeys(f["evidence_refs"]))

    return {
        "report_id": f"W03-VERDICT-BIND-01-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": "VERDICT-BIND-01",
        "node_id": "A1",
        "gate": "G-FORM",
        "class_ids": [c for c, _ in GATE_TARGETS],
        "actor": "worker-03",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "inputs": {
            "frozen_manifest": frozen_rel,
            "frozen_manifest_sha256": frozen_manifest_sha,
            "frozen_manifest_sha256_at_scan_end": (sha256_file(frozen_path)
                                                   if frozen_path.is_file() else None),
            "frozen_manifest_stable_during_scan": bool(
                frozen_path.is_file() and sha256_file(frozen_path) == frozen_manifest_sha),
            "frozen_revision": frozen_doc.get("revision"),
            "frozen_at": frozen_doc.get("frozen_at"),
            "review_stores": list(REVIEW_STORES),
            "hash_roots": list(HASH_ROOTS),
            "indexed_files": len({p for paths in index.values() for p in paths}),
            "indexed_distinct_hashes": len(index),
            "research_map_sha256": sha256_file(root / "research_map/research_map.json"),
        },
        "frozen_declared_vs_disk": declared_vs_disk,
        "tree_pairs": tree_pairs,
        "reviews": reviews,
        "gate_eligibility": gate,
        "accept_verdict_binding_counts": accept_counts,
        "findings": findings,
        "falsifier": (
            "Re-run this scanner against the same FROZEN revision. The report is FALSIFIED if "
            "(a) any review classified != binds_frozen cites a 12+ hex prefix equal to the "
            "FROZEN-declared sha256 of the class artifact its target names; or (b) any tree pair "
            "classified non-identical is byte-identical on re-hash; or (c) any FROZEN entry "
            "classified drifted matches its declared sha256 on re-hash. A prose-only citation is "
            "not a counterexample; only a declared binding field counts."
        ),
        "limits": [
            "All hashes and evidence refs come from one scan pass (path_digest snapshot). The "
            "formulation lead regenerates FROZEN.json and the review store concurrently, so a "
            "re-run can legitimately differ; this report is a snapshot, not a standing invariant.",
            "Unresolved citations are expected when a revision is overwritten in place; they mean "
            "'not re-verifiable against current disk', not 'fabricated'.",
            "Reviewer identity is taken from declared fields; the independent-second-verdict flag is "
            "honoured only when the review declares it.",
            "Only declared binding fields (keys containing sha256/sha/hash/checksum) are treated as "
            "bindings; hex strings elsewhere are recorded as mentions.",
            "This measures citation binding only; it makes no claim about the mathematical content "
            "of any review or schema.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--frozen", default=FROZEN_DEFAULT)
    ap.add_argument("--out", default="artifacts/worker-03/review_hash_binding/report.json")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    report = scan(root, a.frozen)
    report["tool"] = {"path": str(Path(__file__).resolve().relative_to(root)),
                      "sha256": sha256_file(Path(__file__).resolve())}
    out = root / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = {
        "report": a.out,
        "report_id": report["report_id"],
        "frozen_revision": report["inputs"]["frozen_revision"],
        "frozen_manifest_stable_during_scan": report["inputs"]["frozen_manifest_stable_during_scan"],
        "reviews_scanned": len([r for r in report["reviews"] if "verdict_binding" in r]),
        "accept_binding_counts": report["accept_verdict_binding_counts"],
        "frozen_drift": [d["path"] for d in report["frozen_declared_vs_disk"] if not d["match"]],
        "tree_pairs_identical": {p["authoring_path"]: p["identical"] for p in report["tree_pairs"]},
        "gate_eligibility": {c["class_id"]: {"accepts": c["accept_count"],
                                             "eligible": c["eligible_count"]}
                             for c in report["gate_eligibility"]["classes"]},
        "findings": [f["id"] + ":" + f["severity"] for f in report["findings"]],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
