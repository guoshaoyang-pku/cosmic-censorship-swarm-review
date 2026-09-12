#!/usr/bin/env python3
"""Worker-07 falsification harness for the class-separation gate.

TARGET
    research_map/audit_evidence.py :: audit(map_path)
    (the shared evidence auditor; its section 3 is supposed to forbid merging
     the four frozen classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
     AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH, per ASTRA_HANDOFF.md hard decision 1)

WHY
    No assignment was present in comms/inbox at start.  Inspecting the queue and
    the live logs showed several workers independently *building* class-binding
    linters; nobody was *falsifying the one that already exists*.  A gate that has
    never been attacked is not evidence.  This harness attacks it.

METHOD (mutation testing, fail-closed)
    * A minimal synthetic map is built containing exactly one fixture node with
      status "queued", so no artifact/dependency/gate checks fire.  Any hard
      failure is therefore attributable to the class-separation logic alone.
      The one exception is the artifact-content scan, which is exercised on
      purpose by fixtures whose `artifact` field points at a real fixture file.
    * Ground truth (`is_class_merge`) is a domain judgement about hard decision 1,
      recorded independently of the checker's regexes.  `expect_detected` is a
      secondary prediction read off the checker source at the pinned hash.
    * Primary metrics, grounded in domain truth, not in the regexes:
        missed_violations = is_class_merge AND NOT detected   (soundness defect)
        spurious_flags    = NOT is_class_merge AND detected   (precision defect)
    * Every fixture carries `surface`: which map field carries the mutation.  This
      keeps each finding attributed to the code path that actually failed.
    * The target's sha256 is pinned and the tested revision is snapshotted, because
      the target is untracked and was edited three times inside five minutes.
      If the file changes after pinning the run aborts (exit 2) rather than
      silently testing a moving target.

EXIT CODES
    0 = checker sound and precise on this corpus (all violations caught, no
        legitimate document flagged)
    1 = defects found (missed violations and/or spurious flags) -- expected on
        the first run; this is the finding, not a harness malfunction
    2 = harness/target error (hash drift, import failure, isolation broken)

USAGE
    python3 artifacts/worker-07/class_separation_falsification/run_falsification.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent                      # repo root
RESEARCH_MAP = ROOT / "research_map"
FIXTURE_DIR = HERE / "fixtures"
RESULTS = HERE / "results.json"
PINNED = HERE / "baseline_hashes.txt"
CST = timezone(timedelta(hours=8))

CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# The target was edited repeatedly while worker-07 was running (23:18:08, 23:19:39,
# 23:19:53).  The harness pins one revision and snapshots it; this list documents
# earlier revisions so a reader can tell which checker a result belongs to.
SUPERSEDED_PINS = [
    "31323c780157d4eb2dbb636f3a15ecea3e7ca569ad69934159b52e6a119554be",  # first read
    "7ee30daf2bd95bee921e868b655d5e39fce8732b02f2b3f368347996291272e9",  # +NEG heuristic
    "c4769b99ab706146c4091fbe51d3e4dcd4faa8ded0c77f12342c74df6d9064a5",  # first full test
]

LEAKY_ARTIFACT = "artifacts/worker-07/class_separation_falsification/fixtures/leaky_schema.yaml"
PROHIBITION_ARTIFACT = "artifacts/worker-07/class_separation_falsification/fixtures/prohibition_schema.yaml"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pinned_hash(path: Path) -> str | None:
    if not PINNED.exists():
        return None
    for line in PINNED.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == str(path.relative_to(ROOT)):
            return parts[0]
    return None


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
def base_map() -> dict:
    """Minimal map: one queued node, no gates, no artifacts -> zero baseline noise."""
    return {
        "schema_version": "0.1",
        "groups": [
            {
                "id": "formulation",
                "direction": "enumerate and freeze distinct WCC/SCC classes without cross-class leakage",
                "nodes": [
                    {
                        "id": "FX",
                        "label": "fixture node",
                        "status": "queued",
                        "class_id": "AF-WCC-VAC-GEN",
                        "depends_on": [],
                    }
                ],
            }
        ],
        "cross_group_edges": [],
        "portfolio_events": [],
        "gates": [],
    }


def _node(m: dict) -> dict:
    return m["groups"][0]["nodes"][0]


# kind: "leak" -> a merge/violation of hard decision 1 that the gate SHOULD reject
#       "control" -> a legitimate document that the gate MUST NOT reject
# is_class_merge: domain ground truth, independent of the checker's implementation
# expect_detected: prediction from reading the checker source at the pinned hash
# surface: map field carrying the mutation (keeps findings attributed to code paths)
FIXTURES: list[dict] = [
    # ---- leaks: textual conflation -----------------------------------------
    dict(
        id="L01_plain_or",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=True,
        description="label literally says 'C0 or C2' (the phrase the gate was written for)",
        mutate=lambda m: _node(m).update(label="AF-SCC C0 or C2 schema"),
    ),
    dict(
        id="L02_slash",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="label says 'C0/C2' -- one class file covering both regularities",
        mutate=lambda m: _node(m).update(label="AF-SCC C0/C2 schema"),
    ),
    dict(
        id="L03_caret",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="LaTeX-style 'C^0 or C^2' -- caret defeats the regex",
        mutate=lambda m: _node(m).update(label="AF-SCC C^0 or C^2 schema"),
    ),
    dict(
        id="L04_unicode_superscript",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="Unicode 'C\u2070 or C\u00b2' -- superscripts defeat the regex",
        mutate=lambda m: _node(m).update(label="AF-SCC C\u2070 or C\u00b2 schema"),
    ),
    dict(
        id="L05_class_id_concat",
        kind="leak",
        surface="class_id",
        is_class_merge=True,
        expect_detected=True,
        description="class_id 'AF-SCC-C0C2-VAC-GEN' contains both tokens (substring rule fires)",
        mutate=lambda m: _node(m).update(class_id="AF-SCC-C0C2-VAC-GEN"),
    ),
    dict(
        id="L06_class_id_unknown",
        kind="leak",
        surface="class_id",
        is_class_merge=True,
        expect_detected=False,
        description="class_id 'AF-SCC-REG-VAC-GEN' is not one of the four frozen classes (no allowlist)",
        mutate=lambda m: _node(m).update(class_id="AF-SCC-REG-VAC-GEN"),
    ),
    dict(
        id="L07_two_classes_one_node",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="one node unifies a WCC class and an SCC class (no C0/C2 adjacency)",
        mutate=lambda m: _node(m).update(
            label="AF-WCC-VAC-GEN and AF-SCC-C2-VAC-GEN unified schema"
        ),
    ),
    dict(
        id="L08_conclusion_inflation",
        kind="leak",
        surface="conclusion",
        is_class_merge=True,
        expect_detected=False,
        description="WCC class carries an SCC conclusion; only conclusion_type is scanned, not the conclusion text",
        mutate=lambda m: _node(m).update(
            class_id="AF-WCC-VAC-GEN",
            label="AF-WCC vacuum schema",
            conclusion_type="theorem",
            conclusion="the maximal development is C^0-inextendible",
        ),
    ),
    dict(
        id="L09_group_direction_and",
        kind="leak",
        surface="direction",
        is_class_merge=True,
        expect_detected=False,
        description="merge stated in groups[0].direction -- that field is never scanned",
        mutate=lambda m: m["groups"][0].update(
            direction="treat C0 and C2 as one regularity class"
        ),
    ),
    dict(
        id="L10_portfolio_event_and",
        kind="leak",
        surface="portfolio_event",
        is_class_merge=True,
        expect_detected=False,
        description="merge stated in a portfolio_event -- never scanned",
        mutate=lambda m: m.update(
            portfolio_events=[{"event": "merge C0 and C2 into a single regularity condition"}]
        ),
    ),
    dict(
        id="L11_class_family_mismatch",
        kind="leak",
        surface="class_id",
        is_class_merge=True,
        expect_detected=False,
        description="node label is the WCC class but class_id is the SCC C2 class (no family consistency rule)",
        mutate=lambda m: _node(m).update(
            label="AF-WCC-VAC-GEN vacuum schema", class_id="AF-SCC-C2-VAC-GEN"
        ),
    ),
    dict(
        id="L12_comma_list",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="'schemas for C0, C2 (single file)' -- comma list of both regularities",
        mutate=lambda m: _node(m).update(label="AF-SCC schemas for C0, C2 (single file)"),
    ),
    dict(
        id="L13_unicode_and",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="Unicode 'C\u2070 and C\u00b2 share one schema'",
        mutate=lambda m: _node(m).update(label="C\u2070 and C\u00b2 share one schema"),
    ),
    dict(
        id="L14_negation_bypass_label",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="real merge in a SCANNED field, preceded by 'Do not separate them' -- defeats the NEG window",
        mutate=lambda m: _node(m).update(
            label="Do not separate them: C0 or C2 are one class"
        ),
    ),
    dict(
        id="L15_benign_no_bypass_label",
        kind="leak",
        surface="label",
        is_class_merge=True,
        expect_detected=False,
        description="real merge in a SCANNED field, preceded by an unrelated 'no' -- NEG window suppresses it",
        mutate=lambda m: _node(m).update(
            label="There is no known obstruction; C0 or C2 merged"
        ),
    ),
    dict(
        id="L16_artifact_content_leak",
        kind="leak",
        surface="artifact",
        is_class_merge=True,
        expect_detected=True,
        description="the referenced schema file itself merges the regularities (new artifact scan)",
        mutate=lambda m: _node(m).update(artifact=LEAKY_ARTIFACT),
    ),
    dict(
        id="L17_notes_merge_unscanned",
        kind="leak",
        surface="notes",
        is_class_merge=True,
        expect_detected=False,
        description="merge stated in node.notes -- never scanned, even though an earlier revision scanned whole-node JSON",
        mutate=lambda m: _node(m).update(notes="C0 or C2 are merged in this schema"),
    ),
    # ---- controls: legitimate documents that must NOT be flagged ------------
    dict(
        id="C01_separate_nodes",
        kind="control",
        surface="multi-node",
        is_class_merge=False,
        expect_detected=False,
        description="the mandated structure: two nodes, one per SCC regularity",
        mutate=lambda m: m["groups"][0].update(
            nodes=[
                {"id": "FX", "label": "AF-SCC C2 schema", "status": "queued",
                 "class_id": "AF-SCC-C2-VAC-GEN", "depends_on": []},
                {"id": "FY", "label": "AF-SCC C0 schema", "status": "queued",
                 "class_id": "AF-SCC-C0-VAC-GEN", "depends_on": []},
            ]
        ),
    ),
    dict(
        id="C02_slash_split_label",
        kind="control",
        surface="label",
        is_class_merge=False,
        expect_detected=False,
        description="node label 'AF-SCC C2/C0 split' (the real F2 label; was a false positive at 23:17:50)",
        mutate=lambda m: _node(m).update(label="AF-SCC C2/C0 split", class_id=""),
    ),
    dict(
        id="C03_prohibition_text_notes",
        kind="control",
        surface="notes",
        is_class_merge=False,
        expect_detected=False,
        description="a document that FORBIDS the conflation by quoting it (accepted because notes is unscanned)",
        mutate=lambda m: _node(m).update(
            notes="Forbidden: never write 'C0 or C2' in a schema."
        ),
    ),
    dict(
        id="C04_related_classes",
        kind="control",
        surface="class_id",
        is_class_merge=False,
        expect_detected=False,
        description="legitimate cross-reference field naming the sibling regularity",
        mutate=lambda m: _node(m).update(
            class_id="AF-SCC-C2-VAC-GEN",
            related_classes=["AF-SCC-C0-VAC-GEN"],
            notes="distinct classes; leakage matrix applies",
        ),
    ),
    dict(
        id="C05_hyphen_vs",
        kind="control",
        surface="label",
        is_class_merge=False,
        expect_detected=False,
        description="prose 'C0-vs-C2 distinction enforced'",
        mutate=lambda m: _node(m).update(label="C0-vs-C2 distinction enforced"),
    ),
    dict(
        id="C06_wcc_visibility",
        kind="control",
        surface="label",
        is_class_merge=False,
        expect_detected=False,
        description="normal AF-WCC schema shape with I+ visibility fields",
        mutate=lambda m: _node(m).update(
            class_id="AF-WCC-VAC-GEN",
            label="AF-WCC vacuum schema",
            i_plus="future null infinity, complete",
            visibility="no naked singularity visible to I+",
            genericity="open dense set of asymptotically flat vacuum data",
        ),
    ),
    dict(
        id="C07_unicode_prohibition",
        kind="control",
        surface="notes",
        is_class_merge=False,
        expect_detected=False,
        description="prohibition written with Unicode superscripts",
        mutate=lambda m: _node(m).update(notes="never conflate C\u2070 and C\u00b2"),
    ),
    dict(
        id="C08_prohibition_after_phrase_label",
        kind="control",
        surface="label",
        is_class_merge=False,
        expect_detected=False,
        description="SCANNED field: prohibition written AFTER the quoted phrase -- NEG window looks backwards only",
        mutate=lambda m: _node(m).update(
            label="keep C0 and C2 separate"
        ),
    ),
    dict(
        id="C09_prohibition_artifact",
        kind="control",
        surface="artifact",
        is_class_merge=False,
        expect_detected=False,
        description="referenced schema file forbids the conflation by quoting it (NEG window applies)",
        mutate=lambda m: _node(m).update(artifact=PROHIBITION_ARTIFACT),
    ),
    dict(
        id="C10_conclusion_type_ok",
        kind="control",
        surface="conclusion",
        is_class_merge=False,
        expect_detected=False,
        description="legitimate SCC C2 conclusion_type on the matching class",
        mutate=lambda m: _node(m).update(
            class_id="AF-SCC-C2-VAC-GEN",
            label="AF-SCC C2 schema",
            conclusion_type="conditional_theorem",
        ),
    ),
]


def ensure_assets():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / LEAKY_ARTIFACT).write_text(
        "class_id: AF-SCC-C2-VAC-GEN\nregularity: C0 or C2 (merged)\n"
    )
    (ROOT / PROHIBITION_ARTIFACT).write_text(
        "class_id: AF-SCC-C2-VAC-GEN\nrule: never write 'C0 or C2' in a schema\n"
    )


def run() -> int:
    ensure_assets()
    target = RESEARCH_MAP / "audit_evidence.py"
    if not target.exists():
        print(f"HARNESS ERROR: target missing: {target}")
        return 2
    actual = sha256_file(target)
    pinned = pinned_hash(target)
    if pinned is None:
        print("HARNESS ERROR: no pinned hash in baseline_hashes.txt")
        return 2
    if actual != pinned:
        print("HARNESS ERROR: target drifted since pinning.")
        print(f"  pinned {pinned}")
        print(f"  actual {actual}")
        print("  Re-pin baseline_hashes.txt and re-run; results are otherwise void.")
        return 2

    sys.path.insert(0, str(RESEARCH_MAP))
    import audit_evidence  # noqa: E402

    # Preserve the exact revision under test: the target is untracked and is being
    # edited concurrently, so hash-only provenance would be unreproducible.
    snap_dir = HERE / "target_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snapshot = snap_dir / f"audit_evidence.{actual[:12]}.py"
    if not snapshot.exists():
        snapshot.write_bytes(target.read_bytes())
    snap_hash = sha256_file(snapshot)
    if snap_hash != actual:
        print("HARNESS ERROR: snapshot hash mismatch")
        return 2

    base = base_map()
    base_hard = audit_evidence.audit(_write_tmp("_base", base))["hard"]
    if base_hard:
        print(f"HARNESS ERROR: isolation broken; base map yields hard failures: {base_hard}")
        return 2

    records = []
    for fx in FIXTURES:
        m = copy.deepcopy(base)
        fx["mutate"](m)
        path = FIXTURE_DIR / f"{fx['id']}.json"
        path.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        res = audit_evidence.audit(path)
        hard = res["hard"]
        detected = len(hard) > 0
        if fx["kind"] == "leak":
            if detected and fx["expect_detected"]:
                cls = "SOUND_REJECT"
            elif detected and not fx["expect_detected"]:
                cls = "DETECTED_BEYOND_PREDICTION"
            elif not detected and fx["expect_detected"]:
                cls = "UNEXPECTED_ESCAPE"
            else:
                cls = "CONFIRMED_ESCAPE"
        else:
            cls = "FALSE_POSITIVE" if detected else "ACCEPTED"
        records.append({
            "id": fx["id"],
            "kind": fx["kind"],
            "surface": fx["surface"],
            "is_class_merge": fx["is_class_merge"],
            "expect_detected": fx["expect_detected"],
            "detected": detected,
            "classification": cls,
            "description": fx["description"],
            "fixture_path": str(path.relative_to(ROOT)),
            "fixture_sha256": sha256_file(path),
            "hard_failures": hard,
        })

    missed = [r["id"] for r in records if r["is_class_merge"] and not r["detected"]]
    spurious = [r["id"] for r in records if not r["is_class_merge"] and r["detected"]]
    leaks = [r for r in records if r["kind"] == "leak"]
    controls = [r for r in records if r["kind"] == "control"]

    by_surface: dict[str, dict[str, int]] = {}
    for r in leaks:
        b = by_surface.setdefault(r["surface"], {"leaks": 0, "missed": 0})
        b["leaks"] += 1
        b["missed"] += 0 if r["detected"] else 1

    summary = {
        "fixtures_total": len(records),
        "leaks_total": len(leaks),
        "controls_total": len(controls),
        "violations_detected": sum(1 for r in leaks if r["detected"]),
        "missed_violations": len(missed),
        "missed_violation_ids": missed,
        "missed_by_surface": {k: v["missed"] for k, v in sorted(by_surface.items()) if v["missed"]},
        "accepted_controls": sum(1 for r in controls if not r["detected"]),
        "spurious_flags": len(spurious),
        "spurious_flag_ids": spurious,
    }
    verdict = (
        "GATE SOUND AND PRECISE ON THIS CORPUS"
        if not missed and not spurious
        else f"GATE DEFECTIVE: {len(missed)} missed violation(s), {len(spurious)} spurious flag(s)"
    )
    out = {
        "harness": "worker-07 class-separation falsification v2",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target": {
            "path": str(target.relative_to(ROOT)),
            "function": "audit_evidence.audit",
            "sha256": actual,
            "pinned_sha256": pinned,
            "superseded_pins": SUPERSEDED_PINS,
            "snapshot_path": str(snapshot.relative_to(ROOT)),
            "snapshot_sha256": snap_hash,
        },
        "classes": CLASSES,
        "method": (
            "minimal single-node synthetic maps (status=queued) isolate the class-separation "
            "logic; is_class_merge is domain ground truth independent of the checker regexes; "
            "each fixture names the map surface it mutates"
        ),
        "summary": summary,
        "verdict": verdict,
        "fixtures": records,
        "next_falsifier": (
            "Adjudicate the escaped fixtures with the formulation lead: each is a concrete "
            "candidate counterexample to the gate's sufficiency. The gate is only accepted once "
            "a second reviewer confirms at least one escaped fixture is a genuine class merge "
            "AND all controls still pass after the fix."
        ),
    }
    RESULTS.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")

    print(f"target {target.relative_to(ROOT)} sha256={actual[:16]}... snapshot={snapshot.name}")
    print(f"fixtures: {len(records)} ({len(leaks)} leaks, {len(controls)} controls)")
    print(f"  violations detected : {summary['violations_detected']}/{len(leaks)}")
    print(f"  MISSED VIOLATIONS   : {len(missed)}  {missed}")
    print(f"  missed by surface   : {summary['missed_by_surface']}")
    print(f"  controls accepted   : {summary['accepted_controls']}/{len(controls)}")
    print(f"  SPURIOUS FLAGS      : {len(spurious)}  {spurious}")
    print(f"verdict: {verdict}")
    print(f"wrote {RESULTS.relative_to(ROOT)}")
    return 1 if (missed or spurious) else 0


def _write_tmp(name: str, m: dict) -> Path:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    p = FIXTURE_DIR / f"{name}.json"
    p.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
    return p


if __name__ == "__main__":
    sys.exit(run())
