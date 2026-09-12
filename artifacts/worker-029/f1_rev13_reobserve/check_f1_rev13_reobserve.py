#!/usr/bin/env python3
"""W029-F1-REV13-REOBSERVE-01

Independent re-observation of the F1 falsifier suite (`schemas/f1_falsifier_tests.jsonl`,
sha256 56bcb4b3234b) against the LIVE F1 schema revision 13 (`schemas/af_wcc_vacuum.yaml`,
sha256 d9cebb9404b2), which moved the visibility-strictness directions.

Scope: READ-ONLY worker measurement. Writes only under this artifact directory.
No canonical byte is written, no gate verdict, no node status, no claim.

Why this task exists: REC-36 item (6) folds into the rev14 FROZEN rev30 revision a rebind
of all 25 suite rows to the live F1 pin plus re-observation of F1-AMB-11/F1-AMB-17/
F1-AMB-23 against the rev13 text. This checker answers, for each row, whether the rev13
delta touches what the row actually probes, and whether a sha256-only rebind would leave
a row green while the substance it relies on moved.

Exit codes: 0 = measurement complete, expectations hold; 2 = a declared expectation
failed; 3 = pin drift (T0 -> T1).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent          # .../ai4math-swarm
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

TASK_ID = "W029-F1-REV13-REOBSERVE-01"
ACTOR = "worker-029"
NODE_ID = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
GATE = "G-FORM"

LIVE_F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
LIVE_SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
LIVE_F0 = ROOT / "research_map/formulation_taxonomy.yaml"
LIVE_FROZEN = ROOT / "artifacts/formulation/FROZEN.json"

# three independent on-disk copies of the rev12 snapshot (corpus-integrity control K6)
REV12_SOURCES = [
    ROOT / "artifacts/worker-029/f1_suite_materiality/snapshots/"
           "artifacts__worker-060__rev29_binding_acceptance__snapshots__f1__af_wcc_vacuum.cce9c60146d6.yaml.cce9c60146d6",
    ROOT / "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
    ROOT / "artifacts/worker-088/f1_disposition/sandbox/rev12_cce9c6_cce9c60146d6_af_wcc_vacuum.yaml",
]

# independent on-disk copies of the live rev13 bytes (corpus-integrity control K7)
REV13_SOURCES = [
    ROOT / "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.d9cebb9404b2.yaml",
    ROOT / "artifacts/worker-040/f2a_pred_divergence_adjudication/snapshot_schema_F1.d9cebb9404b2.yaml",
    ROOT / "artifacts/worker-060/lform04_stale_binding_materiality/snapshots/f1_rev13.d9cebb9404b2.yaml",
    ROOT / "artifacts/worker-082/a1_xtarget_census/snapshots/af_wcc_vacuum.d9cebb9404b2.yaml",
]

PIN = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/f1_falsifier_tests.jsonl": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "rev12_snapshot": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",   # F0 rev5, prefix pin (recorded at T0)
    "artifacts/formulation/FROZEN.json": "815e08079aef",       # FROZEN rev29 prefix pin
}

NAMED_ROWS = ("F1-AMB-11", "F1-AMB-17", "F1-AMB-23")
KNOWN_AMB25_MISMATCH = [
    "F1-AMB-25|f0_binding.declared_f0_sha256|equals",
    "F1-AMB-25|f0_binding.binding_note|contains",
]

_TOKEN = re.compile(r"([^.[\]]+)|\[(\d+)\]")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def getpath(doc, path: str):
    cur = doc
    for name, idx in _TOKEN.findall(path):
        if name:
            if isinstance(cur, dict) and name in cur:
                cur = cur[name]
            else:
                return False, None
        else:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                return False, None
    return True, cur


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def evaluate(doc, spec: dict) -> dict:
    """Independent re-implementation of the vendor C8 probe semantics."""
    found, value = getpath(doc, str(spec.get("path", "")))
    kind = spec.get("kind")
    needle = spec.get("expected")
    if kind in ("path_exists", "nonnull"):
        ok = bool(found and value is not None)
    elif kind == "is_none":
        ok = (not found) or value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = bool(found and value == needle)
    elif kind == "contains":
        ok = bool(found and value is not None and isinstance(needle, str) and needle in flat(value))
    else:
        return {"found": found, "pass": None, "error": f"unknown probe kind {kind!r}"}
    return {"found": found, "pass": bool(ok), "error": None}


def leaf_paths(obj, prefix="") -> dict:
    out = {}
    if isinstance(obj, dict):
        if not obj:
            out[prefix] = obj
        for k, v in obj.items():
            out.update(leaf_paths(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        if not obj:
            out[prefix] = obj
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def load_rows(path: Path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def probe_relevance(probe_path: str, changed: set) -> str:
    """How the rev12->rev13 delta relates to what this probe reads."""
    if probe_path in changed:
        return "EXACT_CHANGED_LEAF"
    for cl in changed:
        if cl.startswith(probe_path + ".") or cl.startswith(probe_path + "["):
            return "READS_CHANGED_SUBTREE"
    for cl in changed:
        if probe_path.startswith(cl + ".") or probe_path.startswith(cl + "["):
            return "READS_WITHIN_CHANGED_LEAF"
    return "UNCHANGED"


def main() -> int:
    t0 = NOW()
    pins_t0 = {
        "schemas/af_wcc_vacuum.yaml": sha256_file(LIVE_F1),
        "schemas/f1_falsifier_tests.jsonl": sha256_file(LIVE_SUITE),
    }
    rev12_hashes = [sha256_file(p) for p in REV12_SOURCES]
    pins_t0["rev12_snapshot_sources"] = rev12_hashes

    if pins_t0["schemas/af_wcc_vacuum.yaml"] != PIN["schemas/af_wcc_vacuum.yaml"]:
        print("PIN DRIFT: live F1 != declared rev13 pin", file=sys.stderr)
        return 3
    if pins_t0["schemas/f1_falsifier_tests.jsonl"] != PIN["schemas/f1_falsifier_tests.jsonl"]:
        print("PIN DRIFT: live suite != declared pin", file=sys.stderr)
        return 3
    if any(h != PIN["rev12_snapshot"] for h in rev12_hashes):
        print("PIN DRIFT: a rev12 snapshot source differs", file=sys.stderr)
        return 3

    rev12 = yaml.safe_load(REV12_SOURCES[0].read_text(encoding="utf-8"))
    rev13 = yaml.safe_load(LIVE_F1.read_text(encoding="utf-8"))
    rows = load_rows(LIVE_SUITE)

    f12, f13 = leaf_paths(rev12), leaf_paths(rev13)
    changed = {k for k in set(f12) | set(f13) if f12.get(k) != f13.get(k)}

    # ---- suite-wide census -------------------------------------------------
    probe_total = 0
    mismatches = []
    row_census = []
    for r in rows:
        tid = r.get("test_id")
        probes = r.get("probe_results") or []
        pclasses = {}
        row_mismatch = []
        for i, p in enumerate(probes):
            probe_total += 1
            path = str(p.get("path", ""))
            rel = probe_relevance(path, changed)
            pclasses[rel] = pclasses.get(rel, 0) + 1
            res = evaluate(rev13, p)
            if res.get("error"):
                row_mismatch.append(f"{tid}|{path}|ERROR:{res['error']}")
            elif bool(res["pass"]) != bool(p.get("pass")):
                row_mismatch.append(f"{tid}|{path}|{p.get('kind')}")
        if row_mismatch:
            mismatches.extend(row_mismatch)
        row_census.append({
            "test_id": tid,
            "probes": len(probes),
            "binding_sha256": r.get("binding_sha256"),
            "binding_frozen_revision_schema": r.get("binding_frozen_revision_schema"),
            "schema_under_test": r.get("schema_under_test"),
            "probe_relevance": {k: pclasses[k] for k in sorted(pclasses)},
            "reads_changed_content": any(k != "UNCHANGED" for k in pclasses),
            "recomputed_mismatches": row_mismatch,
        })

    census = {
        "rows": len(rows),
        "probes": probe_total,
        "rows_bound_to_rev12_cce9c60146d6": sum(
            1 for r in rows if r.get("binding_sha256") == PIN["rev12_snapshot"]),
        "rows_bound_to_live_rev13_d9cebb9404b2": sum(
            1 for r in rows if r.get("binding_sha256") == PIN["schemas/af_wcc_vacuum.yaml"]),
        "rows_reading_changed_content": sum(1 for c in row_census if c["reads_changed_content"]),
        "rows_with_recomputed_mismatch": sum(1 for c in row_census if c["recomputed_mismatches"]),
        "recomputed_mismatch_set": sorted(mismatches),
        "changed_leaves_rev12_to_rev13": sorted(changed),
        "changed_leaf_count": len(changed),
    }

    # ---- named-row re-observation -----------------------------------------
    by_id = {r.get("test_id"): r for r in rows}
    named = {}
    for tid in NAMED_ROWS:
        r = by_id.get(tid)
        if r is None:
            named[tid] = {"present": False}
            continue
        probes = r.get("probe_results") or []
        detail = []
        for p in probes:
            path = str(p.get("path", ""))
            found13, val13 = getpath(rev13, path)
            found12, val12 = getpath(rev12, path)
            res = evaluate(rev13, p)
            detail.append({
                "path": path,
                "kind": p.get("kind"),
                "role": p.get("role"),
                "expected": p.get("expected"),
                "stored_pass": p.get("pass"),
                "recomputed_pass": res.get("pass"),
                "relevance": probe_relevance(path, changed),
                "value_changed_rev12_to_rev13": (flat(val12) if found12 else None)
                                                 != (flat(val13) if found13 else None),
                "changed_leaves_read": sorted(
                    cl for cl in changed
                    if cl == path or cl.startswith(path + ".") or cl.startswith(path + "[")) ,
            })
        deciding = str(r.get("deciding_field", ""))
        deciding_changed = sorted(
            cl for cl in changed
            if cl == deciding or cl.startswith(deciding + ".") or cl.startswith(deciding + "["))
        named[tid] = {
            "present": True,
            "title": r.get("title"),
            "deciding_field": deciding,
            "deciding_field_status": r.get("deciding_field_status"),
            "deciding_field_alternates": r.get("deciding_field_alternates"),
            "probe_detail": detail,
            "changed_leaves_under_deciding_field": deciding_changed,
            "mechanical_verdict": (
                "unchanged_pass" if all(d["stored_pass"] == d["recomputed_pass"] for d in detail)
                else "MECHANICAL_FLIP"),
            "substance_changed": bool(deciding_changed),
            "rebind_must_do": [],
        }

    # --- explicit, pre-registered per-row substance observations ------------
    # F1-AMB-11: deciding field IS the changed leaf; probes read only its unchanged prefix.
    n11 = named.get("F1-AMB-11", {})
    if n11.get("present"):
        n11["rebind_must_do"] = [
            "re-observe `visibility.definition` against rev13 and refresh the stored "
            "observed_excerpt, which currently quotes only the unchanged prefix and does not "
            "carry the rev13 equivalence statement",
            "the row's deciding_field_status `resolved_geodesic` remains correct; the rev13 "
            "removal of the rev12 misclassification non-sequitur does not change it",
        ]

    # F1-AMB-17: deciding field changed; its own non-equivalence lives on a DIFFERENT, unchanged
    # leaf (`visibility.negation_conclusion`). Flag the scope-collision hazard explicitly.
    n17 = named.get("F1-AMB-17", {})
    if n17.get("present"):
        n17["rebind_must_do"] = [
            "keep the row's `NOT equivalent` expectation on `visibility.negation_conclusion` "
            "(single-point vs open-set, unchanged at rev13); do NOT retarget it at "
            "`visibility.definition`, which now asserts the tail/whole-curve EQUIVALENCE on the "
            "same `visibility` block - a whole-block equivalence grep would conflate them",
            "re-observe probe[0] (`visibility.definition` contains `TAIL`) at rev13 and record "
            "that the field moved for an unrelated strictness correction",
        ]

    # F1-AMB-23: probes the container `class_identity_variants`, whose `[0].relation` changed
    # direction (STRONGER -> WEAKER). No probe covers `relation`, so the direction is unpinned.
    n23 = named.get("F1-AMB-23", {})
    if n23.get("present"):
        n23["rebind_must_do"] = [
            "the row's probed paths read a container whose `[0].relation` changed direction at "
            "rev13 (`strictly STRONGER` -> `strictly WEAKER`); no stored probe covers `relation`",
            "either add a direction probe on `class_identity_variants[0].relation` or record "
            "explicitly that the row's `is_this_class=false` conclusion is direction-independent",
            "row has `schema_snapshot: null` and `schema_under_test: null` - it declares no "
            "schema-under-test, so its re-observation rests on the suite binding alone",
        ]

    # ---- direction-coverage census (is ANY row pinning the corrected direction?) ----
    direction_tokens = ("STRONGER", "WEAKER", "strictly")
    direction_probes = [
        {"test_id": r.get("test_id"), "path": p.get("path"), "expected": p.get("expected")}
        for r in rows for p in (r.get("probe_results") or [])
        if isinstance(p.get("expected"), str) and any(t in p.get("expected") for t in direction_tokens)
    ]
    relation_probes = [
        {"test_id": r.get("test_id"), "path": p.get("path")}
        for r in rows for p in (r.get("probe_results") or [])
        if "relation" in str(p.get("path", ""))
    ]

    # ---- controls ----------------------------------------------------------
    controls = {}
    # K1 fail-closed on unknown probe kind
    controls["K1_unknown_kind_fail_closed"] = (
        evaluate(rev13, {"path": "visibility.definition", "kind": "no_such_kind", "expected": "x"})
        .get("error") is not None)
    # K2 determinism
    def census_once():
        mm = []
        for r in rows:
            for p in (r.get("probe_results") or []):
                res = evaluate(rev13, p)
                if bool(res["pass"]) != bool(p.get("pass")):
                    mm.append(f"{r.get('test_id')}|{p.get('path')}|{p.get('kind')}")
        return sorted(mm)
    controls["K2_determinism"] = census_once() == census_once()
    # K4 probe sensitivity: remove the token from a synthetic copy -> F1-AMB-11 probe[1] must flip.
    # NOTE: the mutation must actually DELETE the substring; replacing TAIL->TAILX would leave
    # "TAIL" present and the control would pass vacuously. The control asserts the removal first.
    synth = json.loads(json.dumps(rev13))
    orig_def = synth["visibility"]["definition"]
    synth["visibility"]["definition"] = orig_def.replace("TAIL", "T41L")
    amb11_probe1 = [p for p in (by_id["F1-AMB-11"].get("probe_results") or [])
                    if p.get("path") == "visibility.definition" and p.get("expected") == "TAIL"]
    removed = ("TAIL" in orig_def) and ("TAIL" not in synth["visibility"]["definition"])
    controls["K4_probe_sensitive_to_field"] = bool(amb11_probe1) and removed and (
        evaluate(synth, amb11_probe1[0])["pass"] is False)
    controls["K4_mutation_removed_token"] = removed
    # K5 known negative control: the F1-AMB-25 mismatches must reproduce
    controls["K5_known_amb25_mismatch_reproduced"] = set(KNOWN_AMB25_MISMATCH) <= set(mismatches)
    # K6 corpus integrity: three independent rev12 copies identical
    controls["K6_rev12_corpus_identical"] = len(set(rev12_hashes)) == 1
    # K7 corpus integrity: four independent rev13 copies identical to the live bytes
    rev13_hashes = [sha256_file(p) for p in REV13_SOURCES]
    controls["K7_rev13_corpus_identical"] = (
        len(set(rev13_hashes)) == 1
        and rev13_hashes[0] == pins_t0["schemas/af_wcc_vacuum.yaml"])

    # ---- expectations ------------------------------------------------------
    def chk(cid, name, ok, measured, falsifier):
        return {"id": cid, "name": name, "ok": bool(ok), "measured": measured, "falsifier": falsifier}

    ex = [
        chk("E1", "live F1 is rev13 d9cebb9404b2", pins_t0["schemas/af_wcc_vacuum.yaml"] == PIN["schemas/af_wcc_vacuum.yaml"],
            pins_t0["schemas/af_wcc_vacuum.yaml"][:12], "live F1 hash differs from the declared rev13 pin"),
        chk("E2", "suite bytes are 56bcb4b3234b", pins_t0["schemas/f1_falsifier_tests.jsonl"] == PIN["schemas/f1_falsifier_tests.jsonl"],
            pins_t0["schemas/f1_falsifier_tests.jsonl"][:12], "suite bytes move"),
        chk("E3", "all 25 rows bound to superseded rev12, none to live rev13",
            census["rows_bound_to_rev12_cce9c60146d6"] == 25 and census["rows_bound_to_live_rev13_d9cebb9404b2"] == 0,
            {"rev12": census["rows_bound_to_rev12_cce9c60146d6"], "rev13": census["rows_bound_to_live_rev13_d9cebb9404b2"]},
            "any row already rebound to d9cebb9404b2 makes the rebind finding void"),
        chk("E4", "rev12->rev13 delta is 12 leaves",
            census["changed_leaf_count"] == 12, census["changed_leaf_count"],
            "a different delta size means the rev13 snapshot pair is not the pair under test"),
        chk("E5", "delta includes visibility.definition, class_identity_variants[0].relation, quantifiers.domains.D5.definition",
            {"visibility.definition", "class_identity_variants[0].relation", "quantifiers.domains.D5.definition"} <= set(changed),
            sorted(c for c in changed if c in {"visibility.definition", "class_identity_variants[0].relation", "quantifiers.domains.D5.definition"}),
            "missing a named strictness leaf means the delta is mis-identified"),
        chk("E6", "the three REC-36 named rows exist and carry probes",
            all(named.get(t, {}).get("present") and len(named[t]["probe_detail"]) >= 2 for t in NAMED_ROWS),
            {t: len(named.get(t, {}).get("probe_detail", [])) for t in NAMED_ROWS},
            "a named row is absent or probe-less"),
        chk("E7", "no named row flips mechanically against rev13",
            all(named[t]["mechanical_verdict"] == "unchanged_pass" for t in NAMED_ROWS),
            {t: named[t]["mechanical_verdict"] for t in NAMED_ROWS},
            "a named row's stored pass no longer recomputes at rev13"),
        chk("E8", "known F1-AMB-25 mismatch reproduces (negative control)",
            controls["K5_known_amb25_mismatch_reproduced"], census["recomputed_mismatch_set"],
            "the known mismatch disappears, so the probe recomputation is not sensitive"),
        chk("E9", "no probe anywhere pins the corrected direction (STRONGER/WEAKER)",
            len(direction_probes) == 0, direction_probes,
            "a direction probe exists, so the direction is already machine-checkable"),
        chk("E10", "no probe reads any `relation` leaf (F1-AMB-23 direction uncovered)",
            len(relation_probes) == 0, relation_probes,
            "a relation probe exists, so F1-AMB-23's direction is covered"),
        chk("E11", "F1-AMB-17's non-equivalence leaf is unchanged and still carries the token",
            ("visibility.negation_conclusion" not in changed)
            and ("NOT equivalent" in flat(getpath(rev13, "visibility.negation_conclusion")[1])),
            "visibility.negation_conclusion unchanged and contains 'NOT equivalent'",
            "the leaf moved or lost the token, which would change the row's expectation"),
        chk("E12", "rev13 visibility.definition asserts EQUIVALENT where rev12 did not (collision source)",
            ("EQUIVALENT" in rev13["visibility"]["definition"])
            and ("EQUIVALENT" not in rev12["visibility"]["definition"]),
            "rev13 contains EQUIVALENT; rev12 does not",
            "the stated collision source is absent, so the hazard note is void"),
        chk("E13", "F1-AMB-23 declares no schema_under_test / schema_snapshot",
            by_id["F1-AMB-23"].get("schema_under_test") is None
            and by_id["F1-AMB-23"].get("schema_snapshot") is None,
            {"schema_under_test": by_id["F1-AMB-23"].get("schema_under_test"),
             "schema_snapshot": by_id["F1-AMB-23"].get("schema_snapshot")},
            "the row does declare a schema-under-test, so that finding is void"),
        chk("E14", "no row in the suite cites the live rev13 pin",
            census["rows_bound_to_live_rev13_d9cebb9404b2"] == 0,
            census["rows_bound_to_live_rev13_d9cebb9404b2"],
            "a row cites rev13, so the suite is partially rebound"),
        chk("E15", "the rev13-relevant row set is closed and equals REC-36 item (6)'s set",
            sorted(c["test_id"] for c in row_census if c["reads_changed_content"])
            == ["F1-AMB-11", "F1-AMB-17", "F1-AMB-23", "F1-AMB-25"],
            sorted(c["test_id"] for c in row_census if c["reads_changed_content"]),
            "an additional row reads changed content and is missing from REC-36 item (6), or a "
            "named row does not read changed content"),
    ]

    findings = [
        {
            "id": "W029-R13-01",
            "claim": "All 25 F1 suite rows are bound to the superseded rev12 hash cce9c60146d6; "
                     "0/25 cite the live rev13 hash d9cebb9404b2. Re-observation is required, and "
                     "a sha256-only rebind would satisfy the binding check without re-observing.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "any row whose binding_sha256 equals d9cebb9404b2",
        },
        {
            "id": "W029-R13-02",
            "claim": "The rev12->rev13 delta is 12 leaves and is substantive (visibility strictness "
                     "directions), not bookkeeping. All three REC-36 named rows read changed "
                     "content: F1-AMB-11 reads the changed leaf visibility.definition exactly; "
                     "F1-AMB-17 reads it too; F1-AMB-23 reads the container class_identity_variants "
                     "whose [0].relation changed direction.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "a named row none of whose probe paths intersects the 12 changed leaves",
        },
        {
            "id": "W029-R13-03",
            "claim": "Direction coverage is empty: 0 of the suite's probes assert STRONGER/WEAKER, "
                     "and 0 probes read any `relation` leaf. The rev13 correction to "
                     "class_identity_variants[0].relation is therefore unpinned by the suite; "
                     "F1-AMB-23 would stay green under a rebind while the direction it depends on "
                     "reversed.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "a probe whose expected string contains STRONGER/WEAKER or whose path "
                         "contains `relation`",
        },
        {
            "id": "W029-R13-04",
            "claim": "Scope-collision hazard: rev13 visibility.definition now contains "
                     "'EQUIVALENT' (tail vs whole-curve, the same block) while F1-AMB-17's "
                     "expectation 'NOT equivalent' correctly lives on the unchanged leaf "
                     "visibility.negation_conclusion (single-point vs open-set). The two must not "
                     "be conflated during the rev14 re-observation. The row's own probes are "
                     "path-scoped, so its mechanical pass is unaffected.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "F1-AMB-17's expectation retargeted to visibility.definition, or the two "
                         "equivalence statements shown to be the same claim",
        },
        {
            "id": "W029-R13-05",
            "claim": "F1-AMB-23 carries schema_snapshot=null and schema_under_test=null while still "
                     "probing through the suite binding; its re-observation rests on the suite "
                     "binding alone and it declares no schema revision under test.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "a non-null schema_under_test or schema_snapshot on F1-AMB-23",
        },
        {
            "id": "W029-R13-06",
            "claim": "The set of suite rows whose probes read content changed by rev12->rev13 is "
                     "CLOSED and equals {F1-AMB-11, F1-AMB-17, F1-AMB-23, F1-AMB-25} - exactly the "
                     "three rows REC-36 item (6) names for re-observation plus F1-AMB-25, which it "
                     "names for repair. No other row reads changed content, so item (6) misses no "
                     "row; conversely the re-observation is not vacuous for any named row.",
            "evidence": ["artifacts/worker-029/f1_rev13_reobserve/report.json"],
            "falsifier": "any other test_id in the reads_changed_content census, or a named row "
                         "absent from it",
        },
    ]

    verdict = "reobserve_required__no_mechanical_flip__direction_unpinned"
    report = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "role": "independent_reobservation_read_only",
        "created_at": NOW(),
        "pins": PIN,
        "pins_measured_t0": pins_t0,
        "rev12_snapshot_sources": [str(p.relative_to(ROOT)) for p in REV12_SOURCES],
        "rev13_snapshot_sources": [str(p.relative_to(ROOT)) for p in REV13_SOURCES],
        "census": census,
        "row_census": row_census,
        "named_rows": named,
        "direction_probes": direction_probes,
        "relation_probes": relation_probes,
        "controls": controls,
        "expectations": ex,
        "findings": findings,
        "verdict": verdict,
        "falsifier": "Re-run check_f1_rev13_reobserve.py at the same declared pins: falsified if "
                     "any named row flips mechanically against rev13; if the F1-AMB-25 mismatch "
                     "set does not reproduce; if a probe is found asserting STRONGER/WEAKER or "
                     "reading a `relation` leaf; if the rev12->rev13 delta is not the 12 declared "
                     "leaves; or if any declared pin moves T0->T1.",
        "next_falsifier": "After the rev14 / FROZEN rev30 fold lands: re-run at the new F1 pin and "
                          "check that (a) all 25 rows cite the new pin, (b) F1-AMB-11's excerpt "
                          "carries the rev13 equivalence text, (c) F1-AMB-23 gains direction "
                          "coverage or an explicit direction-independence note, and (d) F1-AMB-17's "
                          "expectation is still on visibility.negation_conclusion.",
        "no_canonical_write": True,
        "no_gate_verdict": True,
    }

    # ---- emit + pin-stability T1 ------------------------------------------
    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    pins_t1 = {
        "schemas/af_wcc_vacuum.yaml": sha256_file(LIVE_F1),
        "schemas/f1_falsifier_tests.jsonl": sha256_file(LIVE_SUITE),
    }
    drift = [k for k in pins_t1 if pins_t1[k] != pins_t0[k]]
    report["pins_measured_t1"] = pins_t1
    report["pin_drift"] = drift
    # measurement_digest over the stable measurement body
    body = json.dumps({k: report[k] for k in
                       ("census", "named_rows", "controls", "expectations", "findings", "verdict")},
                      sort_keys=True).encode()
    report["measurement_digest"] = sha256_bytes(body)[:12]
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    failed = [e["id"] for e in ex if not e["ok"]]
    print(json.dumps({"task_id": TASK_ID, "verdict": verdict,
                      "rows": census["rows"], "probes": census["probes"],
                      "changed_leaves": census["changed_leaf_count"],
                      "mismatches": census["recomputed_mismatch_set"],
                      "failed_expectations": failed,
                      "pin_drift": drift,
                      "controls": controls}, indent=1))
    if drift:
        return 3
    if failed:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
