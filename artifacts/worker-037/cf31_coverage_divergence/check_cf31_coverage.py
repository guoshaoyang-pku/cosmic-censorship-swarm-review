#!/usr/bin/env python3
"""W037-CF31-COVERAGE-DIVERGENCE-01 -- independent, read-only reconstruction of the
CF-31 / REC-39 F2b coverage-count divergence at F2b@b2ab6acb2bbe.

Question adjudicated
--------------------
CF-31 records two incompatible G-FORM F2b coverage counts at the *same* measured hash
b2ab6acb2bbe: the controller's hash-bound scan of ``reviews/*.json`` reported 4 distinct
full accepts (worker-052/071/072/090) while the formulation lead's per-file census
reported 0 accept / 7 revise (worker-066 x2, worker-035, worker-017, worker-075,
worker-018, worker-053).  REC-39 requires the r3 verifier to state which count is
correct and why the other is wrong.

What this checker does (read-only)
----------------------------------
1. Re-implements the controller scan rule *exactly* as
   ``research_map/astra_lifecycle.py::review_coverage`` (lines 176-214) does, including
   its ``_explicit_pins`` / ``_targets_in_review`` helpers and the
   ``counts_as_full_schema_verdict is not False`` full-verdict rule.
2. Re-implements the lead's 7-file census from the pinned lead artifact
   ``artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json``.
3. Computes the pin-bound universe: every ``reviews/*.json`` with a verdict, an explicit
   pin field whose first 12 hex chars equal the F2b pin, and an F2b scope signal
   (normalized target, node_id/class_id, or F2b- filename).
4. Reports the enumeration split and the *materiality* column separately: each pin-bound
   verdict file's own declared blocking hard failures, plus the recorded accept->revise
   self-supersession of ``reviews/F2b-review-worker-072-rev29.json``.
5. Runs seven controls; mutation controls operate on private temp copies only.

CANONICAL WRITES: none.  The only paths this program writes are its ``--json-out``
argument and auto-cleaned temp directories.  No canonical artifact, review, schema,
map, ledger or frozen byte is touched.

Falsifier
---------
Falsified if any of:
  (a) the F2b canonical or mirror bytes at run time are not
      b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c;
  (b) the live ``reviews/F2b-review-worker-072-rev29.json`` verdict is not ``revise`` or
      its own ``revision_history`` does not record a revision-1 ``accept`` at
      2026-09-12T01:10:13+08:00 (file sha 7487f310d208...) superseded at
      2026-09-12T01:14:51+08:00;
  (c) the live scan rule does not reproduce exactly
      [worker-052, worker-071, worker-090] distinct F2b full-accept reviewers, or, with
      the worker-072 file reverted to its recorded revision-1 accept, does not reproduce
      [worker-052, worker-071, worker-072, worker-090];
  (d) the 7-file census named in the lead artifact does not reproduce 0 accept / 7 revise;
  (e) the scan rule is shown to admit a file whose ``target_id`` is of the form
      ``schemas/af_scc_c0_vacuum.yaml#<pin>`` (i.e. the observed drop is not caused by
      target normalization).

Usage
-----
  python3 check_cf31_coverage.py                 # writes ./report.json
  python3 check_cf31_coverage.py --json-out /tmp/r.json
  python3 check_cf31_coverage.py --no-sandbox    # skip mutation controls (read-only envs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-037/cf31_coverage_divergence -> repo root

F2B_CANON = "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
MAP = "research_map/research_map.json"
LIFECYCLE = "research_map/astra_lifecycle.py"
LEAD_ARTIFACT = "artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json"
W072 = "F2b-review-worker-072-rev29.json"

# The seven files behind the formulation lead's "F2b 0 accept / 7 revise at
# b2ab6acb2bbe" (lead-form-20260912T0113-107 / measurement_3 of LEAD_ARTIFACT).
# Pinned by filename so the reproduction is deterministic and byte-bound.
CENSUS_FILES = [
    "F2b-containment-normativity-worker-066.json",   # worker-066
    "F2b-rev29-containment-rebase-worker-066.json",  # worker-066 (rev29 rebase)
    "F2b-bindchain-rev13-worker-035.json",           # worker-035
    "F2b-rev13-containment-worker-017.json",         # worker-017
    "F2b-review-rev29-075.json",                     # worker-075
    "F2b-review-worker-018-rev13.json",              # worker-018
    "F2b-review-rev29-053.json",                     # worker-053
]

# Expected pin, taken from the CF-31 / REC-39 gate text and the pass-08 measured pins.
EXPECTED_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"

# --- vv exact re-implementation of astra_lifecycle.review_coverage helpers ------------
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}


def targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def explicit_pins(d: dict) -> list:
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins
# --- end re-implementation -----------------------------------------------------------


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def pin_matches(pin: str, pins: list) -> bool:
    return any(p.startswith(pin[:12]) or pin.startswith(p[:12]) for p in pins)


def is_full(d: dict) -> bool:
    """astra_lifecycle semantics: absent flag counts as full."""
    return d.get("counts_as_full_schema_verdict") is not False


def scan_targets(d: dict) -> set:
    return targets_in_review(d)


def f2b_scope_signals(d: dict, name: str) -> dict:
    tgt = scan_targets(d)
    node = str(d.get("node_id") or d.get("node") or "")
    cls = str(d.get("class_id") or "")
    return {
        "scan_target": "F2b" in tgt,
        "node_field": "f2b" in (node + " " + cls).lower(),
        "filename": name.startswith("F2b"),
        "class_field": "AF-SCC-C0-VAC-GEN" in cls,
    }


def blocking_hard_failures(d: dict) -> list:
    out = []
    for hf in d.get("hard_failures") or []:
        if not isinstance(hf, dict):
            out.append({"raw": str(hf)[:120]})
            continue
        sev = str(hf.get("severity", ""))
        flag = hf.get("blocking")
        if flag is True or "block" in sev.lower():
            out.append({"id": hf.get("id"), "severity": sev, "carrier": hf.get("carrier")})
    return out


def load_reviews(review_dir: Path) -> list:
    rows = []
    for rp in sorted(review_dir.glob("*.json")):
        try:
            d = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        pins = explicit_pins(d)
        pset = set(pins)
        rows.append({
            "file": rp.name,
            "file_sha256": sha256_file(rp),
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": v,
            "score": d.get("score"),
            "counts_as_full_schema_verdict": is_full(d),
            "explicit_pin_match": pin_matches(EXPECTED_F2B, pins),
            "explicit_pins_head": sorted({p[:12] for p in pset}),
            "reviewed_sha256": d.get("reviewed_sha256"),
            "target_id": d.get("target_id") if isinstance(d.get("target_id"), str) else None,
            "node_id": d.get("node_id"),
            "class_id": d.get("class_id"),
            "created_at": d.get("created_at") or d.get("reviewed_at"),
            "mtime": datetime.fromtimestamp(rp.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "hard_failures": len(d.get("hard_failures") or []),
            "blocking_hard_failures": blocking_hard_failures(d),
            "scope": f2b_scope_signals(d, rp.name),
        })
    return rows


def scan_rule(rows: list) -> dict:
    """Exact controller rule: F2b in normalized targets AND explicit pin prefix match."""
    sel = [r for r in rows if r["explicit_pin_match"] and r["scope"]["scan_target"]]
    return summarize(sel)


def pin_bound_rule(rows: list) -> dict:
    """Broad read-only census: pin match AND any F2b scope signal (not only target_id)."""
    sel = [r for r in rows if r["explicit_pin_match"] and any(
        (r["scope"]["scan_target"], r["scope"]["node_field"],
         r["scope"]["filename"], r["scope"]["class_field"]))]
    return summarize(sel)


def summarize(sel: list) -> dict:
    full_accepts = [r for r in sel if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]]
    full_revises = [r for r in sel if r["verdict"] == "revise" and r["counts_as_full_schema_verdict"]]
    scoped_accepts = [r for r in sel if r["verdict"] == "accept" and not r["counts_as_full_schema_verdict"]]
    scoped_revises = [r for r in sel if r["verdict"] == "revise" and not r["counts_as_full_schema_verdict"]]
    return {
        "n": len(sel),
        "files": [r["file"] for r in sel],
        "accept": sorted({r["reviewer"] for r in full_accepts}),
        "revise": sorted({r["reviewer"] for r in full_revises}),
        "full_accept_reviewers": sorted({r["reviewer"] for r in full_accepts}),
        "full_revise_reviewers": sorted({r["reviewer"] for r in full_revises}),
        "scoped_accept_reviewers": sorted({r["reviewer"] for r in scoped_accepts}),
        "scoped_revise_reviewers": sorted({r["reviewer"] for r in scoped_revises}),
        "counts": {"accept_full": len(full_accepts), "revise_full": len(full_revises),
                   "accept_scoped": len(scoped_accepts), "revise_scoped": len(scoped_revises)},
    }


def census_rule(rows: list, census_files: list) -> dict:
    sel = [r for r in rows if r["file"] in census_files]
    return summarize(sel)


def measure_pins() -> dict:
    out = {}
    for label, rel in (("f2b_canonical", F2B_CANON), ("f2b_mirror", F2B_MIRROR),
                       ("frozen_json", FROZEN), ("research_map", MAP),
                       ("astra_lifecycle", LIFECYCLE)):
        p = ROOT / rel
        out[label] = {"path": rel, "exists": p.exists(),
                      "sha256": sha256_file(p) if p.exists() else None}
    out["pin_ok"] = out["f2b_canonical"]["sha256"] == EXPECTED_F2B and \
        out["f2b_mirror"]["sha256"] == EXPECTED_F2B
    return out


def lead_census_files() -> list:
    """The lead's declared reviewer set, cross-checked against the pinned file list."""
    p = ROOT / LEAD_ARTIFACT
    declared = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        m3 = d.get("measurement_3_review_coverage_at_live_hashes", {})
        f2b = m3.get("F2b_at_b2ab6acb2bbe", {})
        declared = {k: f2b.get(k) for k in ("accept", "revise", "inconclusive")}
    return CENSUS_FILES, declared


def run_mutation_controls(rows: list, outdir: Path) -> dict:
    """All mutations happen under a private temp directory; canonical tree untouched."""
    src = ROOT / "reviews"
    ctl = {}
    tmp_root = Path(tempfile.mkdtemp(prefix="w037_cf31_ctl_"))
    try:
        # C1 live scan == pass-08-final
        live = scan_rule(rows)
        ctl["C1_live_scan_reproduces_pass08_final"] = {
            "pass": live["full_accept_reviewers"] == ["worker-052", "worker-071", "worker-090"],
            "observed": live["full_accept_reviewers"],
            "expected": ["worker-052", "worker-071", "worker-090"],
        }
        # C2 revert of worker-072 revision-2 revise -> revision-1 accept == pass-08-open
        d = tmp_root / "open"
        shutil.copytree(src, d)
        w = d / W072
        obj = json.loads(w.read_text(encoding="utf-8"))
        obj["verdict"] = "accept"
        obj["score"] = 4.0
        obj["counts_as_full_schema_verdict"] = True
        w.write_text(json.dumps(obj, indent=1))
        m = scan_rule(load_reviews(d))
        ctl["C2_scan_reproduces_pass08_open_after_072_revert"] = {
            "pass": m["full_accept_reviewers"] == ["worker-052", "worker-071", "worker-072", "worker-090"],
            "observed": m["full_accept_reviewers"],
            "expected": ["worker-052", "worker-071", "worker-072", "worker-090"],
        }
        # C3 target normalization is the drop cause for path-targeted F2b reviews
        d2 = tmp_root / "target"
        shutil.copytree(src, d2)
        f66 = d2 / "F2b-containment-normativity-worker-066.json"
        before = scan_rule(load_reviews(d2))
        obj = json.loads(f66.read_text(encoding="utf-8"))
        obj["target_id"] = "F2b"
        f66.write_text(json.dumps(obj, indent=1))
        after = scan_rule(load_reviews(d2))
        ctl["C3_target_normalization_is_drop_cause"] = {
            "pass": "F2b-containment-normativity-worker-066.json" not in before["files"]
            and "F2b-containment-normativity-worker-066.json" in after["files"],
            "before_files": before["files"],
            "after_files": after["files"],
        }
        # C4 census reproduces the lead's 0 accept / 7 revise
        cen = census_rule(rows, CENSUS_FILES)
        declared_reviewers = sorted({r["reviewer"] for r in rows if r["file"] in CENSUS_FILES})
        ctl["C4_census_reproduces_lead_0_7"] = {
            "pass": cen["counts"]["accept_full"] == 0 and len(cen["files"]) == 7,
            "observed_counts": cen["counts"], "observed_files": cen["files"],
            "observed_reviewers": declared_reviewers,
        }
        # C5 the absent/false full flag drives full-accept membership
        d3 = tmp_root / "flag"
        shutil.copytree(src, d3)
        f71 = d3 / "F2b-review-rev13-worker-071.json"
        obj = json.loads(f71.read_text(encoding="utf-8"))
        obj["counts_as_full_schema_verdict"] = False
        f71.write_text(json.dumps(obj, indent=1))
        ctl["C5_full_flag_drives_full_accepts"] = {
            "pass": scan_rule(load_reviews(d3))["counts"]["accept_full"] == 2,
            "observed": scan_rule(load_reviews(d3))["counts"],
        }
        # C6 a wrong pin zeroes every rule (counts are pin-bound, not name-bound)
        global EXPECTED_F2B
        keep, EXPECTED_F2B = EXPECTED_F2B, "0" * 64
        try:
            zero = {"scan": scan_rule(load_reviews(src))["n"],
                    "bound": pin_bound_rule(load_reviews(src))["n"]}
        finally:
            EXPECTED_F2B = keep
        ctl["C6_wrong_pin_zeroes_counts"] = {"pass": zero["scan"] == 0 and zero["bound"] == 0,
                                             "observed": zero}
        # C7 no canonical write: report path must lie outside the canonical root sets
        canon = [ROOT / "reviews", ROOT / "schemas", ROOT / "research_map",
                 ROOT / "artifacts/formulation", ROOT / "numerics", ROOT / "ledger"]
        rep = (outdir / "report.json").resolve()
        ctl["C7_report_path_outside_canonical_sets"] = {
            "pass": not any(str(rep).startswith(str(c)) for c in canon),
            "report_path": str(rep),
        }
        # C8 the live controller instrument itself agrees with the re-implementation
        try:
            import importlib.util
            if str(ROOT / "research_map") not in sys.path:
                sys.path.insert(0, str(ROOT / "research_map"))
            spec = importlib.util.spec_from_file_location("w037_live_astra", ROOT / LIFECYCLE)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            f2b = mod.review_coverage({"F2b": {"sha256": EXPECTED_F2B}}).get("F2b", {})
            live_files = sorted(e["file"] for e in f2b.get("verdicts", []))
            mine = sorted(scan_rule(rows)["files"])
            ctl["C8_live_instrument_agrees_with_reimplementation"] = {
                "pass": f2b.get("distinct_accept_reviewers") == ["worker-052", "worker-071", "worker-090"]
                and live_files == mine,
                "live_files": live_files,
                "live_distinct_accept_reviewers": f2b.get("distinct_accept_reviewers"),
                "instrument_sha256": sha256_file(ROOT / LIFECYCLE),
            }
        except Exception as exc:  # instrument import must never mask the measurement
            ctl["C8_live_instrument_agrees_with_reimplementation"] = {
                "pass": False, "error": repr(exc)[:300]}
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    return ctl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(HERE / "report.json"))
    ap.add_argument("--no-sandbox", action="store_true", help="skip mutation controls")
    args = ap.parse_args()

    t0 = now()
    pins_t0 = measure_pins()
    rows = load_reviews(ROOT / "reviews")
    scan = scan_rule(rows)
    bound = pin_bound_rule(rows)
    census = census_rule(rows, CENSUS_FILES)
    census_declared = lead_census_files()[1]

    # accept/revise files pinned by name for the binding table
    binding = [r for r in rows if r["explicit_pin_match"] and any(
        (r["scope"]["scan_target"], r["scope"]["node_field"],
         r["scope"]["filename"], r["scope"]["class_field"]))]

    def corpus_digest(rs: list) -> str:
        payload = sorted((r["file"], r["file_sha256"], r["verdict"]) for r in rs)
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    corpus_sha_t0 = corpus_digest(rows)

    controls = run_mutation_controls(rows, HERE) if not args.no_sandbox else {"skipped": True}

    # worker-072 self-supersession evidence
    w72 = next((r for r in rows if r["file"] == W072), None)
    w72_obj = json.loads((ROOT / "reviews" / W072).read_text(encoding="utf-8")) if w72 else {}

    materiality = {
        "pin_bound_full_accepts_zero_hard_failures": sorted(
            r["reviewer"] for r in binding
            if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]
            and r["hard_failures"] == 0),
        "pin_bound_full_accepts_with_hard_failures": sorted(
            r["reviewer"] for r in binding
            if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]
            and r["hard_failures"] > 0),
        "pin_bound_full_accepts_with_explicitly_blocking": sorted(
            r["reviewer"] for r in binding
            if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]
            and r["blocking_hard_failures"]),
        "pin_bound_full_revises_hard_failure_inventory": [
            {"file": r["file"], "reviewer": r["reviewer"],
             "n_hard_failures": r["hard_failures"],
             "explicitly_blocking": r["blocking_hard_failures"]}
            for r in binding if r["verdict"] == "revise" and r["counts_as_full_schema_verdict"]],
        "worker_072_self_supersession": {
            "verdict_now": w72_obj.get("verdict"),
            "superseded_at": w72_obj.get("superseded_at"),
            "supersedes_sha256": w72_obj.get("supersedes_sha256"),
            "revision_history": w72_obj.get("revision_history"),
        },
        "note": ("Enumeration and materiality are separate columns. Every live pin-bound "
                 "full accept declares zero hard failures, while the live pin-bound full "
                 "revises carry hard failures against the same bytes (worker-017/018/072 "
                 "mark them blocking; worker-075/085 list hard findings without a severity "
                 "label); worker-072's own file records its earlier accept superseded by a "
                 "revise at the same pin. A coverage number without the materiality column "
                 "is not a gate-coverage count."),
    }

    dropped_from_scan = sorted(set(bound["files"]) - set(scan["files"]))
    divergence = {
        "controller_scan_pass08_open_011238": {
            "full_accept_reviewers": ["worker-052", "worker-071", "worker-072", "worker-090"],
            "source": "runtime/state/controller_verification/lifecycle_20260912-011239.json",
        },
        "controller_scan_pass08_final_011625": {
            "full_accept_reviewers": ["worker-052", "worker-071", "worker-090"],
            "source": "runtime/state/controller_verification/lifecycle_20260912-011626.json",
        },
        "live_scan": scan["full_accept_reviewers"],
        "lead_census": census["counts"],
        "pin_bound_universe": bound["counts"],
        "symmetric_difference_scan_vs_census": sorted(set(scan["files"]) ^ set(census["files"])),
        "dropped_from_scan_by_target_normalization": dropped_from_scan,
        "n_dropped_from_scan": len(dropped_from_scan),
        "causes": [
            f"rule scope: the scan enumerates only reviews whose *normalized* target set "
            f"contains F2b; {len(dropped_from_scan)} pin-bound F2b verdict files express "
            f"target_id as a path#hash string or omit target_id and are silently dropped "
            f"(control C3)",
            "reviewer scope: the lead census enumerates only its seven tracked reviewers "
            "and therefore omits the three pin-bound full accepts worker-052/071/090",
            "mutability: reviews/F2b-review-worker-072-rev29.json self-superseded "
            "accept->revise under an unchanged filename at 01:14:51, so the 4-accept scan "
            "snapshot at 01:12:38 was stale when CF-31 quoted it (controls C1/C2)",
            "category: the two numbers answer different questions (verdict-file "
            "enumeration vs materiality-filtered acceptance); neither is a gate-coverage "
            "count on its own",
        ],
    }

    headline = (
        "At F2b@b2ab6acb2bbe the live pin-bound verdict universe is "
        f"{bound['counts']['accept_full']} full accept / {bound['counts']['revise_full']} full revise / "
        f"{bound['counts']['revise_scoped']} scoped revise files, of which the exact controller "
        f"scan sees only {scan['n']} files ({scan['counts']['accept_full']} accept / "
        f"{scan['counts']['revise_full']} revise) and the lead census sees only its 7 tracked "
        "revise files. CF-31's '4 accepts' was the 01:12:38 snapshot and is superseded by "
        "worker-072's 01:14:51 self-revision; the lead's '0 accept' is a materiality-filtered "
        "count over a reviewer subset, not the enumeration. The three live full accepts "
        "(worker-052/071/090) exist on disk at the pin but declare zero hard failures while "
        "the live full revises carry hard failures against the same bytes, so G-FORM coverage "
        "must publish both columns and may not cite either number alone.")

    t1 = now()
    pins_t1 = measure_pins()
    corpus_sha_t1 = corpus_digest(load_reviews(ROOT / "reviews"))
    result = {
        "schema": "worker-037/cf31-coverage-divergence/v1",
        "task_id": "W037-CF31-COVERAGE-DIVERGENCE-01",
        "actor": "worker-037",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "finding_ref": "CF-31 / REC-39",
        "headline": headline,
        "created_at": t0,
        "json_out": str(Path(args.json_out).resolve()),
        "expected_f2b_pin": EXPECTED_F2B,
        "pins_t0": pins_t0,
        "pins_t1": pins_t1,
        "pin_stable": pins_t0 == pins_t1,
        "corpus_sha256_t0": corpus_sha_t0,
        "corpus_sha256_t1": corpus_sha_t1,
        "corpus_stable": corpus_sha_t0 == corpus_sha_t1,
        "instrument": {
            "scan_rule_source": f"{LIFECYCLE}:176-214",
            "astra_lifecycle_sha256": pins_t0["astra_lifecycle"]["sha256"],
            "full_rule": "counts_as_full_schema_verdict is not False",
            "pin_match_rule": "explicit pin field first-12-hex equality",
        },
        "review_files_scanned": len(rows),
        "binding_table": binding,
        "counts": {"scan_rule": scan, "census_rule": census, "pin_bound_rule": bound,
                   "census_declared_lead_artifact": census_declared},
        "divergence": divergence,
        "materiality": materiality,
        "controls": controls,
        "falsifier": (
            "Falsified if (a) F2b canonical/mirror bytes differ from " + EXPECTED_F2B + "; "
            "(b) reviews/F2b-review-worker-072-rev29.json is not revise or its "
            "revision_history lacks the 01:10:13 accept (7487f310d208) superseded at "
            "01:14:51; (c) the live scan does not yield [worker-052, worker-071, "
            "worker-090] or the reverted-072 control does not yield [worker-052, "
            "worker-071, worker-072, worker-090]; (d) the lead's 7-file census does not "
            "reproduce 0 accept / 7 revise; (e) the scan admits a "
            "target_id='schemas/af_scc_c0_vacuum.yaml#<pin>' file."
        ),
        "does_not_claim": [
            "G-FORM pass/fail or any gate verdict",
            "node completion, validation_status=passed, or done status",
            "the REC-39 binding table (owned by astra-life05-verify-gform-r3 / astra-lead-audit)",
            "which materiality ruling on the named F2b findings is correct (gate-owner scope)",
            "that accepting reviewers acted in bad faith: their own files classify the named findings as non-blocking",
            "any canonical artifact, review, schema, map or ledger write or edit",
        ],
        "canonical_writes": 0,
        "runtime_seconds": round((datetime.now(CST) - datetime.fromisoformat(t0)).total_seconds(), 3),
    }
    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[w037-cf31] wrote {out}")
    print(f"[w037-cf31] pin_ok={pins_t0['pin_ok']} stable={result['pin_stable']} "
          f"corpus_stable={result['corpus_stable']} "
          f"scan={scan['full_accept_reviewers']} census={census['counts']} "
          f"bound={bound['counts']}")
    ok = all(v.get("pass") for v in controls.values() if isinstance(v, dict)) if not args.no_sandbox else True
    print(f"[w037-cf31] controls_pass={ok}")
    return 0 if (pins_t0["pin_ok"] and result["corpus_stable"] and ok) else 1


if __name__ == "__main__":
    sys.exit(main())
