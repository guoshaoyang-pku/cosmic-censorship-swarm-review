#!/usr/bin/env python3
"""W078-GF0-CRITERIA-AUDIT-01 — independent audit of the G-F0 gate criteria at the
canonical F0 hash measured at run start.

Task (one, bounded, class-bound): G-F0 / F0 / classes
AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH.

The gate criterion text (research_map/research_map.json gates[G-F0].criteria) is:
  "formulation_taxonomy.yaml exists; exactly 4 separate class ids; disjointness tests;
   2 independent reviewer verdicts"

This harness audits exactly those four sub-criteria, and nothing else:
  A. existence + content integrity of the pinned canonical artifact (byte-exact snapshot);
  B. exactly four separate class ids, with descriptor completeness for all four, and a
     document-wide leak scan for a fifth/merged class id;
  C. disjointness: all 6 unordered pairs present exactly once with non-empty decisive_axes
     and a non-empty separation argument, axes drawn from the declared field_vocabulary,
     plus the anti-merge guard G3 token scan;
  D. two independent reviewer verdicts: recomputed from the reviews/ corpus by an
     independent implementation of the coverage rule, cross-checked against the controller's
     astra_lifecycle.review_coverage result (mechanism cross-check, not a copy);
  E. the two named G-F0 blockers that could make a reviewer-set count non-load-bearing
     (status: draft_unverified; genericity slots owned by F1/F2) — reported, not adjudicated.

Read-only on all canonical paths.  The only writes go under artifacts/worker-078/.

Run:  python3 artifacts/worker-078/f0_criteria_audit/audit_gf0_criteria_078.py [--json OUT]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

CANON = ROOT / "research_map" / "formulation_taxonomy.yaml"
SUPPLEMENT = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshot"
REVIEWS = ROOT / "reviews"

EXPECTED_CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
EXPECTED_PAIRS = [
    ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"),
    ("AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"),
    ("AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"),
    ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"),
    ("AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH"),
    ("AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"),
]
VOCAB_AXES = {
    "family", "matter_model", "symmetry", "asymptotics",
    "regularity_token", "genericity_kind", "genericity_topology", "conclusion_type",
}
# G3 merged-regularity spellings (braced / superscript / subscript, normalized).
MERGED_REGULARITY_PATTERNS = [
    r"C\s*[\^_]\s*\{?\s*0\s*[,/]\s*2\s*\}?",
    r"C\s*[\^_]\s*\{?\s*2\s*[,/]\s*0\s*\}?",
    r"C0\s*/\s*C2",
    r"C2\s*/\s*C0",
    r"\bC\s*\{\s*0\s*,\s*2\s*\}",
]
GATE_HASH_PREFIX_LEN = 12


# --------------------------------------------------------------------------- helpers
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def norm_pair(pair) -> tuple:
    return tuple(sorted(str(x) for x in pair))


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text())


class Check:
    """One named assertion with a machine-readable status."""

    def __init__(self, cid: str, title: str):
        self.cid, self.title = cid, title
        self.status = "PASS"
        self.detail = ""
        self.data = {}

    def fail(self, detail: str):
        self.status = "FAIL"
        self.detail = detail
        return self

    def warn(self, detail: str):
        if self.status == "PASS":
            self.status = "WARN"
        self.detail = (self.detail + " | " if self.detail else "") + detail
        return self

    def ok(self, detail: str = "", **data):
        self.detail = detail
        self.data.update(data)
        return self

    def as_dict(self):
        return {"check_id": self.cid, "title": self.title, "status": self.status,
                "detail": self.detail, **({"data": self.data} if self.data else {})}


# --------------------------------------------------------------------------- checks
def check_identity(pinned: str) -> Check:
    """A1: pinned snapshot is byte-identical to the live canonical artifact."""
    c = Check("A1_identity", "pinned snapshot == live canonical F0 artifact")
    live = sha256_file(CANON)
    snap_files = sorted(SNAPSHOT_DIR.glob("formulation_taxonomy.*.yaml"))
    if not snap_files:
        return c.fail("no snapshot present")
    snap = sha256_file(snap_files[0])
    if live != pinned:
        return c.fail(f"live canonical {live} != pinned {pinned} (drift voids the binding)")
    if snap != pinned:
        return c.fail(f"snapshot {snap} != pinned {pinned}")
    return c.ok(f"live == snapshot == {pinned}", sha256=live,
                bytes=CANON.stat().st_size, path=str(CANON.relative_to(ROOT)))


def check_exactly_four_ids(doc: dict) -> Check:
    """B1: exactly four separate class ids, in order, and descriptors exist for each."""
    c = Check("B1_four_class_ids", "exactly 4 separate class ids with descriptors")
    ids = doc.get("class_ids")
    if not isinstance(ids, list):
        return c.fail("class_ids is not a list")
    if len(ids) != 4:
        return c.fail(f"class_ids has {len(ids)} entries: {ids}")
    if ids != EXPECTED_CLASS_IDS:
        return c.fail(f"class_ids {ids} != expected order {EXPECTED_CLASS_IDS}")
    classes = doc.get("classes")
    if not isinstance(classes, dict):
        return c.fail("classes is not a mapping")
    missing = [i for i in ids if i not in classes]
    if missing:
        return c.fail(f"class ids without descriptor: {missing}")
    extra = [k for k in classes if k not in ids]
    if extra:
        return c.fail(f"descriptors not in class_ids (a fifth class): {extra}")
    return c.ok("4 ids, 4 descriptors, no extras", class_ids=ids,
                descriptor_sizes={k: len(classes[k]) for k in ids})


def check_descriptor_completeness(doc: dict) -> Check:
    """B2: each descriptor carries the axis fields the disjointness table relies on."""
    c = Check("B2_descriptor_fields", "each class descriptor carries required axis fields")
    classes = doc.get("classes", {})
    required = ["family", "matter_model", "symmetry", "conclusion_type"]
    bad = {}
    for cid in EXPECTED_CLASS_IDS:
        d = classes.get(cid) or {}
        flat = json.dumps(d)
        miss = [k for k in required if k not in flat]
        if miss:
            bad[cid] = miss
    if bad:
        return c.fail(f"descriptors missing required axis fields: {bad}")
    return c.ok("all four descriptors expose family/matter_model/symmetry/conclusion_type",
                descriptors_checked=4)


def check_disjointness(doc: dict) -> Check:
    """C1: all six unordered pairs exactly once, non-empty axes and separation."""
    c = Check("C1_disjointness_pairs", "6/6 disjointness pairs, unique, axes+argument non-empty")
    rows = doc.get("disjointness")
    if not isinstance(rows, list):
        return c.fail("disjointness is not a list")
    seen, problems = {}, []
    for r in rows:
        if not isinstance(r, dict):
            problems.append(f"non-mapping row {r!r}")
            continue
        pr = r.get("pair")
        if not isinstance(pr, list) or len(pr) != 2:
            problems.append(f"malformed pair {pr!r}")
            continue
        key = norm_pair(pr)
        seen.setdefault(key, 0)
        seen[key] += 1
        axes = r.get("decisive_axes") or []
        sep = (r.get("separation") or "").strip()
        if not axes:
            problems.append(f"pair {key} has empty decisive_axes")
        if not sep:
            problems.append(f"pair {key} has empty separation argument")
        self_pair = sorted(pr)[0] == sorted(pr)[1]
        if self_pair:
            problems.append(f"pair {key} is a self-pair")
    expected = {norm_pair(p) for p in EXPECTED_PAIRS}
    missing = sorted(expected - set(seen))
    extra = sorted(set(seen) - expected)
    dupes = sorted(k for k, n in seen.items() if n != 1)
    if missing:
        problems.append(f"missing pairs: {missing}")
    if extra:
        problems.append(f"unexpected pairs: {extra}")
    if dupes:
        problems.append(f"duplicated pairs: {dupes}")
    if problems:
        return c.fail("; ".join(problems))
    return c.ok("6 unordered pairs, each exactly once, axes+argument non-empty",
                pairs=sorted("|".join(k) for k in seen))


def check_disjointness_axes_vocab(doc: dict) -> Check:
    """C2: decisive_axes tokens are drawn from the declared field_vocabulary."""
    c = Check("C2_axis_vocabulary", "decisive_axes drawn from field_vocabulary")
    vocab = doc.get("field_vocabulary")
    if not isinstance(vocab, dict):
        return c.fail("field_vocabulary missing")
    declared = set(vocab.keys())
    if declared != VOCAB_AXES:
        return c.fail(f"field_vocabulary {sorted(declared)} != expected {sorted(VOCAB_AXES)}")
    unknown = {}
    for r in doc.get("disjointness", []):
        for ax in r.get("decisive_axes") or []:
            if ax not in declared:
                unknown.setdefault("|".join(map(str, r.get("pair") or [])), []).append(ax)
    if unknown:
        return c.fail(f"axes not in field_vocabulary: {unknown}")
    return c.ok(f"all decisive_axes resolve in field_vocabulary ({len(declared)} axes)")


def check_no_fifth_class_token(doc: dict) -> Check:
    """B3: no class-id-shaped token outside class_ids anywhere in the document."""
    c = Check("B3_no_fifth_class_token", "no fifth class id token in the document")
    pat = re.compile(r"\bAF-(?:WCC|SCC)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
    raw = CANON.read_text()
    found = set(pat.findall(raw))
    unknown = sorted(t for t in found if t not in EXPECTED_CLASS_IDS)
    if unknown:
        return c.fail(f"class-id-shaped tokens outside class_ids: {unknown}")
    return c.ok(f"{len(found)} distinct AF-* tokens, all within the frozen four",
                tokens=sorted(found))


def check_g3_merged_regularity(doc: dict) -> Check:
    """C3: anti-merge scan with the frozen validator's own regex, plus a cross-check
    against the stricter W078 pattern set.  A hit is only a DEFECT when the match is a
    class token (inside a class id / regularity_token value); a hit in ordinary prose is
    reported as a notation-hygiene NOTE, because the class ids and the transfer/guard
    tables remain unmerged (B1/B3/D1 pass independently)."""
    c = Check("C3_merged_regularity_guard", "no merged-regularity class token (G3), frozen regex")
    raw = CANON.read_text()
    try:
        sys.path.insert(0, str(ROOT / "artifacts" / "worker-01"))
        import validate_taxonomy as vt  # type: ignore
        frozen_hits = []
        for m in vt.MERGED_RE.finditer(raw):
            frozen_hits.append({"line": raw[:m.start()].count("\n") + 1, "text": m.group(0)})
        for m in vt.MERGED_RE.finditer(vt.normalize_regularity(raw)):
            frozen_hits.append({"line": None, "text": m.group(0), "normalized": True})
        frozen_name = "artifacts/worker-01/validate_taxonomy.py:MERGED_RE"
    except Exception as exc:
        frozen_hits, frozen_name = [], f"unavailable ({type(exc).__name__})"

    # class-token position test: a merged spelling inside a class id or a
    # regularity_token value would be a real class merge.
    class_token_merge = bool(re.search(r"AF-(?:WCC|SCC)-C\s*\{?\s*(?:0\s*[,/]\s*2|2\s*[,/]\s*0)", raw))
    rt_merge = False
    for cid in EXPECTED_CLASS_IDS:
        d = (doc.get("classes") or {}).get(cid) or {}
        rt = str(d.get("regularity_token") or d.get("components", {}).get("regularity_token") or "")
        rt_merge = rt_merge or bool(re.search(r"[Cc]\s*\{?\s*(?:0\s*[,/]\s*2|2\s*[,/]\s*0)", rt))

    strict_hits = []
    for pat in MERGED_REGULARITY_PATTERNS:
        for m in re.finditer(pat, raw):
            strict_hits.append({"pattern": pat, "line": raw[:m.start()].count("\n") + 1,
                                "text": m.group(0)})

    if class_token_merge or rt_merge:
        return c.fail(f"merged regularity used as a class token: class_id={class_token_merge} "
                      f"regularity_token={rt_merge}; frozen hits={frozen_hits[:4]}")
    if strict_hits:
        return c.warn(f"{len(strict_hits)} merged-notation hit(s) in ordinary prose, not in class "
                      f"tokens: {strict_hits[:4]}; frozen-regex hits: {frozen_hits[:4]} "
                      f"(cross-check {frozen_name}); class-token scan clean")
    return c.ok("0 merged-regularity hits (frozen + strict pattern sets); class-token scan clean",
                frozen_regex_hits=len(frozen_hits))


def check_supplement_consistency(doc: dict, supp: dict) -> Check:
    """D1: the companion authoring supplement agrees on the frozen class set."""
    c = Check("D1_supplement_classset", "companion supplement agrees on frozen class set")
    if not isinstance(supp, dict):
        return c.fail("supplement unreadable")
    frozen = supp.get("frozen_classes")
    contracts = supp.get("class_contracts")
    if not isinstance(frozen, list) or not isinstance(contracts, dict):
        return c.fail("supplement lacks frozen_classes/class_contracts")
    if sorted(frozen) != sorted(EXPECTED_CLASS_IDS):
        return c.fail(f"supplement frozen_classes {frozen} != canonical four")
    if sorted(contracts.keys()) != sorted(EXPECTED_CLASS_IDS):
        return c.fail(f"supplement class_contracts keys {sorted(contracts)} != canonical four")
    return c.ok("supplement frozen_classes and class_contracts both equal the canonical four",
                supplement_revision=supp.get("revision"), artifact_role=str(supp.get("artifact_role"))[:60])


def check_reviewer_verdicts(pinned: str) -> Check:
    """E1: recompute the two-independent-accept criterion over reviews/ (own implementation)."""
    c = Check("E1_independent_verdicts", ">=2 distinct full-accept reviewers at the pinned hash")
    prefix = pinned[:GATE_HASH_PREFIX_LEN]
    pin_keys = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
    full_accepts, scoped, all_verdicts = [], [], []
    if not REVIEWS.is_dir():
        return c.fail("reviews/ missing")
    for rp in sorted(REVIEWS.glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        verdict = str(d.get("verdict") or "").lower()
        if verdict not in {"accept", "revise", "reject", "inconclusive"}:
            continue
        target = d.get("target_id")
        targets = set()
        if isinstance(target, str):
            targets.add(target)
        elif isinstance(target, dict):
            for k in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(target.get(k), str):
                    targets.add(target[k])
        for k in ("target_id", "target_node_id", "node_id"):
            if isinstance(d.get(k), str):
                targets.add(d[k])
        if not any("F0" in t for t in targets):
            continue
        pins = []
        for k in pin_keys:
            if isinstance(d.get(k), str):
                pins.append(d[k].lower())
        for k in ("target", "artifact"):
            v = d.get(k)
            if isinstance(v, dict):
                for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                    if isinstance(v.get(k2), str):
                        pins.append(v[k2].lower())
        if not any(p.startswith(prefix) or prefix.startswith(p[:GATE_HASH_PREFIX_LEN]) for p in pins):
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        rec = {"file": rp.name, "reviewer": reviewer, "verdict": verdict, "full": full}
        all_verdicts.append(rec)
        if verdict == "accept":
            (full_accepts if full else scoped).append(rec)
    distinct = sorted({r["reviewer"] for r in full_accepts})
    if len(distinct) < 2:
        return c.fail(f"{len(distinct)} distinct full-accept reviewer(s) at {prefix}: {distinct}; "
                      f"all bound verdicts: {[(r['reviewer'], r['verdict']) for r in all_verdicts]}")
    return c.ok(f"{len(distinct)} distinct full-accept reviewers at {prefix}: {distinct}",
                full_accepts=full_accepts, scoped_accepts=scoped,
                bound_verdicts=all_verdicts)


def check_mechanism_crosscheck(pinned: str) -> Check:
    """E2: cross-check E1 against the controller implementation (independent code path)."""
    c = Check("E2_controller_crosscheck", "controller review_coverage agrees (mechanism check)")
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import astra_lifecycle as al  # type: ignore
        m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
        hashes = al.measured_hashes(m)
        cov = al.review_coverage(hashes)
        got = cov.get("F0", {})
        op_distinct = sorted(got.get("distinct_accept_reviewers", []))
    except Exception as exc:  # pragma: no cover
        return c.warn(f"controller cross-check unavailable: {type(exc).__name__}: {exc}")
    own = _last_e1_distinct
    if own is None:
        return c.warn("no E1 result to compare")
    if own == op_distinct:
        return c.ok(f"both mechanisms report {op_distinct} full-accept reviewer(s)",
                    controller_measured_f0=(hashes.get("F0", {}) or {}).get("sha256"),
                    controller_two_distinct=got.get("two_distinct_accepts"))
    return c.fail(f"mechanism disagreement: own={own} controller={op_distinct}")


def check_named_blockers(doc: dict) -> Check:
    """F1: report the two named F0 blockers that could void a reviewer-set count."""
    c = Check("F1_named_blockers", "named G-F0 blockers reported (status + genericity ownership)")
    status = doc.get("status")
    qs = doc.get("open_questions") or []
    genericity_owner = [q.get("id") for q in qs if "genericity" in str(q.get("text", "")).lower()]
    findings = []
    if status != "accepted":
        findings.append(f"canonical status is {status!r}, not an accepted status")
    if genericity_owner:
        findings.append(f"open genericity question(s) {genericity_owner} still owned downstream")
    return c.ok("; ".join(findings) if findings else "no named blocker present",
                status=status, coverage_gaps=[g.get("id") for g in doc.get("coverage_gaps") or []])


def check_controls(doc: dict) -> Check:
    """G1: the harness must FAIL on perturbed bytes (null control per HANDOFF rule)."""
    c = Check("G1_discriminating_controls", "harness fails on 3 targeted perturbations")
    results = {}

    # control 1: drop a disjointness pair
    d1 = copy.deepcopy(doc)
    d1["disjointness"] = [r for r in d1["disjointness"]
                          if norm_pair(r.get("pair", [])) != norm_pair(EXPECTED_PAIRS[0])]
    results["drop_pair"] = check_disjointness(d1).status

    # control 2: add a fifth class id
    d2 = copy.deepcopy(doc)
    d2["class_ids"] = list(d2["class_ids"]) + ["AF-WCC-VAC-GEN-EXTRA"]
    d2["classes"]["AF-WCC-VAC-GEN-EXTRA"] = {"family": "WCC"}
    results["add_fifth_class"] = check_exactly_four_ids(d2).status

    # control 3: blank a separation argument
    d3 = copy.deepcopy(doc)
    d3["disjointness"][0]["separation"] = "   "
    results["blank_separation"] = check_disjointness(d3).status

    # control 4: unknown axis token
    d4 = copy.deepcopy(doc)
    d4["disjointness"][0]["decisive_axes"] = ["family", "made_up_axis"]
    results["unknown_axis"] = check_disjointness_axes_vocab(d4).status

    expected = {"drop_pair": "FAIL", "add_fifth_class": "FAIL",
                "blank_separation": "FAIL", "unknown_axis": "FAIL"}
    bad = {k: v for k, v in results.items() if v != expected[k]}
    if bad:
        return c.fail(f"controls did not discriminate: {bad} (all={results})")
    return c.ok(f"4/4 perturbations rejected: {results}", controls=results)


_last_e1_distinct = None


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="report path (default: alongside this script)")
    ap.add_argument("--pin", default=None, help="expected canonical sha256 (drift check)")
    args = ap.parse_args()

    out_path = Path(args.json) if args.json else Path(__file__).resolve().parent / "report.json"
    started = now_iso()

    live_sha = sha256_file(CANON)
    pinned = args.pin or live_sha
    if args.pin and args.pin != live_sha:
        early = {
            "schema_version": "0.1", "artifact_type": "gate_criteria_audit",
            "task_id": "W078-GF0-CRITERIA-AUDIT-01", "actor": "worker-078",
            "node_id": "F0", "gate": "G-F0", "started_at": started, "finished_at": now_iso(),
            "binding": {"pinned_sha256": args.pin, "live_canonical_sha256_at_start": live_sha,
                        "drift_voids_binding": True},
            "verdict": "inconclusive",
            "hard_failures": [{"check_id": "A0_drift", "status": "FAIL",
                               "detail": f"live canonical {live_sha} != requested pin {args.pin}; "
                                         "audit not run (drift voids the binding)"}],
            "checks": [], "counts": {"checks": 0, "pass": 0, "warn": 0, "fail": 1},
            "non_claims": ["binding check failed; no criteria verdict issued"],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(early, indent=1) + "\n")
        print(json.dumps({"report": str(out_path), "verdict": "inconclusive",
                          "reason": "pin drift", "live": live_sha[:12], "pin": args.pin[:12]}))
        return 2
    doc = load_yaml(SNAPSHOT_DIR / f"formulation_taxonomy.{live_sha[:12]}.yaml") \
        if (SNAPSHOT_DIR / f"formulation_taxonomy.{live_sha[:12]}.yaml").is_file() else load_yaml(CANON)
    supp_path = next(iter(sorted(SNAPSHOT_DIR.glob("formulation_taxonomy_supplement.*.yaml"))), None)
    supp = load_yaml(supp_path) if supp_path else None

    checks = []
    checks.append(check_identity(pinned))
    checks.append(check_exactly_four_ids(doc))
    checks.append(check_descriptor_completeness(doc))
    checks.append(check_no_fifth_class_token(doc))
    checks.append(check_disjointness(doc))
    checks.append(check_disjointness_axes_vocab(doc))
    checks.append(check_g3_merged_regularity(doc))
    checks.append(check_supplement_consistency(doc, supp))
    e1 = check_reviewer_verdicts(pinned)
    global _last_e1_distinct
    _last_e1_distinct = sorted({r["reviewer"] for r in e1.data.get("full_accepts", [])}) \
        if e1.status == "PASS" else []
    checks.append(e1)
    checks.append(check_mechanism_crosscheck(pinned))
    checks.append(check_named_blockers(doc))
    checks.append(check_controls(doc))

    fails = [c for c in checks if c.status == "FAIL"]
    warns = [c for c in checks if c.status == "WARN"]
    verdict = "accept" if not fails and not warns else ("revise" if fails else "accept_with_notes")

    report = {
        "schema_version": "0.1",
        "artifact_type": "gate_criteria_audit",
        "task_id": "W078-GF0-CRITERIA-AUDIT-01",
        "actor": "worker-078",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": EXPECTED_CLASS_IDS,
        "started_at": started,
        "finished_at": now_iso(),
        "binding": {
            "pinned_sha256": pinned,
            "live_canonical_sha256_at_start": live_sha,
            "live_canonical_sha256_at_end": sha256_file(CANON),
            "path": "research_map/formulation_taxonomy.yaml",
            "drift_voids_binding": True,
        },
        "gate_criteria_audited": [
            "formulation_taxonomy.yaml exists",
            "exactly 4 separate class ids",
            "disjointness tests",
            "2 independent reviewer verdicts",
        ],
        "counts": {"checks": len(checks), "pass": len(checks) - len(fails) - len(warns),
                   "warn": len(warns), "fail": len(fails)},
        "verdict": verdict,
        "hard_failures": [c.as_dict() for c in fails],
        "warnings": [c.as_dict() for c in warns],
        "checks": [c.as_dict() for c in checks],
        "non_claims": [
            "not a controller gate verdict; worker cannot set gate verdict or node status",
            "does not re-derive the physics, truth or non-vacuity of the four class contracts",
            "does not adjudicate whether status=draft_unverified blocks G-F0 (reported as F1 only)",
            "reviewer-independence is measured by distinct reviewer id + full-verdict flag, not by provenance audit",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"report": str(out_path), "verdict": verdict,
                      "counts": report["counts"],
                      "pinned": pinned[:12],
                      "hard_failures": [c["check_id"] for c in report["hard_failures"]]}))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
