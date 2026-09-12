#!/usr/bin/env python3
"""W055-A0-HF01-FIRING-01 — independent census/probe of the contested HF-01 firing.

Question adjudicated (worker-089 finding A0-089-A, reviews/A0-review-worker-089.json):
  "HF-01 conformance (evaluation_rubric.yaml:174) reads claim.artifact_refs, absent from
   all 62 ledger/theorems.jsonl rows incl. the 30 theorem rows; audit_lib.py:189-191 +
   audit_run.py:216 make that 30 false criticals and break the G-AUDIT hard_failure_rate
   criterion."

Method: read-only. Pin every input by sha256 (refuse on drift). Independently re-implement
the canonical corpus-bucket predicate of artifacts/audit/audit_run.py:81-121 (no import),
then run the *canonical* detector function audit_lib.check_class_binding on labelled probes.
The canonical subprocess run is separate (see run_all.sh) so this file only measures the
routing tier and the detector tier.

Tiers measured:
  T0 canonical routing : which corpus bucket each of the 62 ledger rows lands in.
  T1 rubric-literal    : rows with conclusion_type==theorem and no artifact_refs (the count
                         worker-089 reports).
  T2 detector          : does audit_lib.check_class_binding emit HF-01 for the labelled
                         probes (positive/negative/without-class-id controls)?

Exit codes: 0 measured, 3 hash drift (refuse).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")

PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/audit/audit_run.py":
        "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
}

FROZEN_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
              "AF-WCC-SCALAR-SPH"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_json_objects(path: Path):
    """Mirror of audit_run.iter_json_objects for .jsonl (one object per line)."""
    if path.suffix == ".jsonl":
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    else:
        try:
            obj = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if isinstance(obj, list):
            for o in obj:
                if isinstance(o, dict):
                    yield o
        elif isinstance(obj, dict):
            yield obj


def bucket(obj: dict, rel: str) -> set[str]:
    """Independent re-implementation of audit_run.scan_corpus's routing predicate.

    A single object may land in more than one bucket; the canonical runner applies
    check_class_binding (the only HF-01 emitter) to corpus["claims"] only
    (audit_run.py:232-233).
    """
    b: set[str] = set()
    is_schema_doc = any(k in obj for k in
                        ("class_components", "quantifiers", "axes", "documents",
                         "quantifier_order", "inextendibility", "artifact_kind"))
    is_fixture = any(t in rel for t in ("/fixtures/", "/corpus/", "/selftest/",
                                        "repaired_inputs")) \
        or rel.endswith(("EXPECTATIONS.json", "manifest.json"))
    if not is_fixture and ("claim_id" in obj or
                           (not is_schema_doc and "class_id" in obj and "statement" in obj)):
        b.add("claims")
    status = obj.get("resolution_status") or obj.get("status")
    if status and ("cite_key" in obj or "source_id" in obj) and not is_fixture:
        b.add("citations")
    if "node_id" in obj and "path" in obj and "sha256" in obj:
        b.add("artifacts")
    if "seeds" in obj and "statistic" in obj:
        b.add("results")
    if "theorem_id" in obj or ("class_ids" in obj and "statement_exact" in obj):
        b.add("records")
    return b


def load_lib():
    spec = importlib.util.spec_from_file_location(
        "audit_lib_pinned", ROOT / "artifacts" / "audit" / "audit_lib.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclass() resolves cls.__module__ via sys.modules
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    measured = {}
    drift = []
    for rel, want in PINS.items():
        got = sha256_file(ROOT / rel)
        measured[rel] = got
        if got != want:
            drift.append({"path": rel, "declared": want, "measured": got})
    if drift:
        print(json.dumps({"status": "HASH_DRIFT", "drift": drift}, indent=2))
        return 3

    lib = load_lib()
    rubric = lib.load_rubric(str(ROOT / "evaluation_rubric.yaml"))
    classes = lib.frozen_classes(rubric)

    rows = list(iter_json_objects(ROOT / "ledger" / "theorems.jsonl"))
    rel_ledger = "ledger/theorems.jsonl"
    tier0 = {"claims": [], "records": [], "both": [], "neither": []}
    for i, r in enumerate(rows):
        b = bucket(r, rel_ledger)
        if "claims" in b and "records" in b:
            tier0["both"].append(i)
        elif "claims" in b:
            tier0["claims"].append(i)
        elif "records" in b:
            tier0["records"].append(i)
        else:
            tier0["neither"].append(i)

    theorem_rows = [r for r in rows if r.get("conclusion_type") == "theorem"]
    tier1_fire = [r for r in theorem_rows if not r.get("artifact_refs")]

    # T2 detector probes against the canonical function.
    def probe(claim):
        v = lib.check_class_binding(claim, classes)
        return [x.as_dict() if hasattr(x, "as_dict") else x.__dict__ for x in v]

    pos = probe({"claim_id": "PROBE-POS", "class_id": "AF-WCC-VAC-GEN",
                 "statement": "probe", "conclusion_type": "theorem",
                 "falsifier": "probe", "evidence_refs": []})
    neg = probe({"claim_id": "PROBE-NEG", "class_id": "AF-WCC-VAC-GEN",
                 "statement": "probe", "conclusion_type": "theorem",
                 "falsifier": "probe", "evidence_refs": [],
                 "artifact_refs": [{"path": "x", "sha256": "0" * 64}]})
    nocid = probe({"claim_id": "PROBE-NOCID", "class_ids": ["AF-WCC-VAC-GEN"],
                   "statement_exact": "probe", "conclusion_type": "theorem",
                   "falsifier": "probe"})
    # forced-claim control: a real theorem ledger row with a singular class_id injected
    forced = []
    for r in tier1_fire[:3]:
        c = dict(r)
        c["class_id"] = (r.get("class_ids") or [None])[0]
        forced.append({"theorem_id": r.get("theorem_id"),
                       "hfs": [x["hf"] for x in probe(c)]})

    def hfs(vs):
        return sorted({x["hf"] for x in vs})

    result = {
        "task_id": "W055-A0-HF01-FIRING-01",
        "class_ids": FROZEN_IDS,
        "gate": "G-AUDIT",
        "node_id": "A0",
        "measured_at_utc": None,
        "pins": measured,
        "ledger_rows": len(rows),
        "tier0_canonical_routing": {
            "claims": len(tier0["claims"]),
            "records": len(tier0["records"]),
            "both": len(tier0["both"]),
            "neither": len(tier0["neither"]),
            "claims_rows_sample": tier0["claims"][:5],
            "hf01_emitter_applies_to": "corpus['claims'] only (audit_run.py:232-233)",
        },
        "tier1_rubric_literal": {
            "theorem_rows": len(theorem_rows),
            "theorem_rows_without_artifact_refs": len(tier1_fire),
            "theorem_ids": [r.get("theorem_id") for r in tier1_fire],
            "any_row_has_artifact_refs": any("artifact_refs" in r for r in rows),
        },
        "tier2_detector_probes": {
            "positive_theorem_no_refs": {"hfs": hfs(pos), "hf01_count": sum(1 for x in pos if x["hf"] == "HF-01")},
            "negative_theorem_with_refs": {"hfs": hfs(neg), "hf01_count": sum(1 for x in neg if x["hf"] == "HF-01")},
            "ledger_row_without_singular_class_id": {"hfs": hfs(nocid), "hf01_count": sum(1 for x in nocid if x["hf"] == "HF-01")},
            "forced_claim_real_rows": forced,
        },
        "verdict": None,
        "falsifier": None,
        "caveat": ("T0 measures the canonical routing; T1 is the rubric-literal count worker-089 "
                   "reports; T2 shows the detector itself works on a canonical claim. The "
                   "canonical subprocess run report is a separate artifact (canonical_live/)."),
    }

    t0_ok = result["tier0_canonical_routing"]["claims"] == 0 and \
        result["tier0_canonical_routing"]["records"] == len(rows)
    t1_ok = result["tier1_rubric_literal"]["theorem_rows_without_artifact_refs"] == 30
    t2_ok = result["tier2_detector_probes"]["positive_theorem_no_refs"]["hf01_count"] == 1 and \
        result["tier2_detector_probes"]["negative_theorem_with_refs"]["hf01_count"] == 0 and \
        result["tier2_detector_probes"]["ledger_row_without_singular_class_id"]["hf01_count"] == 0

    if t0_ok and t1_ok and t2_ok:
        result["verdict"] = ("A0-089-A REFUTED-AS-TO-MECHANISM / CONFIRMED-AS-TO-COUNT: the "
                             "canonical runner routes all 62 ledger rows to corpus['records'] "
                             "(0 claims), and check_class_binding (the only HF-01 emitter) is "
                             "applied to corpus['claims'] only, so the live ledger produces 0 "
                             "canonical HF-01 violations and no 30 false criticals. The count 30 "
                             "is correct only under the rubric-literal reading of ledger records "
                             "as claims-with-singular-class_id; the detector itself fires exactly "
                             "once on a labelled theorem-without-refs claim and 0 on the "
                             "with-refs control, so it is not inert.")
    else:
        result["verdict"] = "MEASUREMENT_CONTRADICTS_PRIOR_READING: see tiers"
    result["falsifier"] = ("Re-run census.py at the pinned hashes; the adjudication is falsified "
                           "if scan_corpus routes >=1 ledger row into corpus['claims'] at "
                           "audit_run.py#3b27dd3fef7f, or if the canonical full run's HF-01 "
                           "violations include a where naming a ledger row, or if the T2 positive "
                           "control fails to fire exactly one HF-01.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("ledger_rows", "tier0_canonical_routing", "tier1_rubric_literal",
                       "tier2_detector_probes")}, indent=2)[:1800])
    print("VERDICT:", result["verdict"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
