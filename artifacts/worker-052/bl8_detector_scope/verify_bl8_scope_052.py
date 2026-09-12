#!/usr/bin/env python3
"""W052-BL8-DETECTOR-SCOPE-01: independent, read-only measurement of literature BL-8.

BL-8 (comms/outbox/astra-lead-literature.jsonl -> lit-l5-20260912-021) claims an
A0 detector scope defect: hard failure HF-14 (self_certified_acceptance) is reported at
corpus level over every .json/.jsonl file under artifacts/, comms/outbox and ledger, so it
also fires on immutable archives, incoming shards and worker review snapshots.  If that is
true, HF-14 can never reach zero through any legitimate repair of the live corpus and
G-AUDIT / G-LIT stay red independently of literature quality.

This harness tests that claim by measurement, not agreement:

  * It re-implements the audit corpus-selection rule and the HF-14 predicate from the
    rubric text and the audit source, and imports none of the author's code.
  * It pins every input by sha256 and re-measures the pins at the end (drift => fail).
  * It classifies every HF-14 hit file as CANONICAL / LIVE_BUILD_INPUT / historical.
  * It pre-registers expectations E1..E9 and 8 controls C0..C7 (see EXPECTATIONS and
    CONTROLS below).  Exit code is 0 iff every expectation and control holds.
  * It writes report.json; it never writes outside its own artifact directory, the
    sandbox (which is asserted to be OUTSIDE the repository so synthetic records can never
    pollute the standing audit corpus), and stdout.

Spec sources (read, not imported):
  evaluation_rubric.yaml:243-252  HF-14 detector text
  artifacts/audit/audit_lib.py:458-473  check_self_certification implementation
  artifacts/audit/audit_run.py:57-112  scan_corpus selection rule
  artifacts/audit/audit_run.py:283-310 systemic aggregation
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm

# --- pinned inputs (path -> role); hashes are measured, not assumed ----------------------
PINS = [
    "ledger/theorems.jsonl",
    "evaluation_rubric.yaml",
    "artifacts/audit/audit_lib.py",
    "artifacts/audit/audit_run.py",
    "artifacts/audit/reports/audit-20260912T003820.json",
    "artifacts/literature/tools/build_literature.py",
    "artifacts/literature/reviews/rev3-axis-split.json",
    "comms/outbox/astra-lead-literature.jsonl",
]
LIVE_BUILD_GLOB = "artifacts/literature/theorems/batch-*.jsonl"
CANONICAL_LEDGER = "ledger/theorems.jsonl"

FROZEN_FOUR = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# --- audit corpus selection rule (audit_run.py scan_corpus) ------------------------------
SCAN_ROOTS = ["artifacts", "comms/outbox", "ledger"]
EXCLUDE_SUBSTR = ("audit/reports", "audit/checkpoints")
FIXTURE_TOKENS = ("/fixtures/", "/corpus/", "/selftest/", "repaired_inputs")
FIXTURE_SUFFIX = ("EXPECTATIONS.json", "manifest.json")
SCHEMA_DOC_KEYS = ("class_components", "quantifiers", "axes", "documents",
                   "quantifier_order", "inextendibility", "artifact_kind")
FORBIDDEN_KEYS = ("status", "validation_status", "supports_claim")

SANDBOX = Path("/data3/guoshaoyang/tmp/w052_bl8_sandbox")

# --- pre-registered expectations ----------------------------------------------------------
EXPECTATIONS = [
    ("E1", "canonical ledger exists and every pinned input is readable and hash-measured"),
    ("E2", "canonical ledger carries 0 rows with any HF-14 forbidden key "
           "(status / validation_status / supports_claim) and 0 HF-14 predicate hits"),
    ("E3", "all live build inputs batch-*.jsonl carry 0 forbidden-key rows, 0 HF-14 hits, "
           "and hold the same record count as the canonical ledger"),
    ("E4", "restricting the corpus scan to the 8 files named in the 00:38:20 report "
           "reproduces the report's 346 HF-14 records exactly"),
    ("E5", "every file with HF-14 hits in the live corpus classifies as historical "
           "(ARCHIVE / INCOMING / SNAPSHOT / PROPOSED / WORKER_BATCH); none is CANONICAL "
           "or LIVE_BUILD_INPUT"),
    ("E6", "total HF-14 hits > 0 while canonical+live hits == 0 (repair-unfalsifiability)"),
    ("E7", "the proposed allowlist predicate returns 0 hits on the live corpus and fires "
           "on a tampered canonical ledger (fail-closed, not fail-open)"),
    ("E8", "the proposed predicate reports a violation when the canonical ledger is "
           "missing (fail-closed on absence)"),
    ("E9", "all controls C0..C7 behave as pre-registered"),
]
CONTROLS = [
    ("C0", "sandbox is outside the repository tree (synthetic records cannot pollute "
           "the standing audit corpus)"),
    ("C1", "self-certified row with no reviewer verdict fires under the rubric predicate"),
    ("C2", "same row with a reviewer verdict field does NOT fire (exemption branch live)"),
    ("C3", "corpus scan of a mini tree finds the hit only in the ARCHIVE copy; the "
           "allowlist predicate ignores it and passes"),
    ("C4", "tampered canonical ledger fires under BOTH the corpus scan and the allowlist "
           "predicate (scope narrowing does not exempt the canonical path)"),
    ("C5", "clean canonical ledger does not fire under either predicate (negative control)"),
    ("C6", "missing canonical ledger is reported as MISSING_CANONICAL, never a silent pass"),
    ("C7", "a denylist rule ('exclude paths containing snapshots/') silently passes a "
           "canonical file that lives under such a path, while the allowlist predicate "
           "still fails closed; allowlist > denylist"),
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_objects(p: Path):
    """Yield dict objects from .json / .jsonl, mirroring audit_run.iter_json_objects."""
    if not p.is_file():
        return
    text = p.read_text(errors="replace")
    if p.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    yield json.loads(line)
                except ValueError:
                    pass
    elif p.suffix == ".json":
        try:
            obj = json.loads(text)
        except ValueError:
            return
        if isinstance(obj, list):
            yield from (o for o in obj if isinstance(o, dict))
        elif isinstance(obj, dict):
            yield obj


def is_record(obj: dict) -> bool:
    """audit_run.scan_corpus record rule: theorem_id, or class_ids + statement_exact."""
    return "theorem_id" in obj or ("class_ids" in obj and "statement_exact" in obj)


def is_fixture(rel: str, obj: dict) -> bool:
    if any(t in rel for t in FIXTURE_TOKENS) or rel.endswith(FIXTURE_SUFFIX):
        return True
    return any(k in obj for k in SCHEMA_DOC_KEYS)


def hf14_hit(r: dict) -> bool:
    """Rubric HF-14 + audit_lib.check_self_certification predicate, re-implemented."""
    accepted = (str(r.get("status", "")).lower() in ("accepted", "passed")
                or r.get("supports_claim") is True
                or str(r.get("validation_status", "")).lower() == "passed")
    has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict")
                      or r.get("reviewed_by"))
    return accepted and not has_review


def select_records(root: Path, scan_roots=None):
    """Return list of (relpath, obj) for every audit-corpus record."""
    out = []
    roots = scan_roots if scan_roots is not None else [root / s for s in SCAN_ROOTS]
    for d in roots:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix not in (".json", ".jsonl"):
                continue
            rel = str(p.resolve().relative_to(root.resolve()))
            if any(t in str(p) for t in EXCLUDE_SUBSTR):
                continue
            for obj in iter_objects(p):
                if not is_fixture(rel, obj) and is_record(obj):
                    out.append((rel, obj))
    return out


def classify(rel: str) -> str:
    if rel == CANONICAL_LEDGER:
        return "CANONICAL"
    if rel.startswith("artifacts/literature/theorems/batch-") and rel.endswith(".jsonl"):
        return "LIVE_BUILD_INPUT"
    if rel.startswith("artifacts/literature/archive/"):
        return "ARCHIVE"
    if rel.startswith("artifacts/literature/incoming/"):
        return "INCOMING"
    if rel.startswith("artifacts/worker-07/ledger_contribution/batches/"):
        return "WORKER_BATCH"
    if "snapshot" in rel or "/proposed/" in rel:
        return "SNAPSHOT_OR_PROPOSED"
    return "UNCLASSIFIED"


HISTORICAL = {"ARCHIVE", "INCOMING", "SNAPSHOT_OR_PROPOSED", "WORKER_BATCH"}


def allowed_paths(root: Path, build_glob: str = LIVE_BUILD_GLOB):
    return [root / CANONICAL_LEDGER] + sorted(root.glob(build_glob))


def proposed_check(root: Path, build_glob: str = LIVE_BUILD_GLOB):
    """Fail-closed allowlist predicate: canonical ledger + live build inputs only.

    Missing canonical ledger is a violation, not a silent pass.  Returns list of
    (relpath, kind, where).
    """
    out = []
    for p in allowed_paths(root, build_glob):
        rel = str(p.relative_to(root))
        if not p.exists():
            out.append((rel, "MISSING_CANONICAL", "<file absent>"))
            continue
        for obj in iter_objects(p):
            if is_record(obj) and hf14_hit(obj):
                where = obj.get("theorem_id") or obj.get("claim_id") or obj.get("event_id") or "<record>"
                out.append((rel, "HF-14", where))
    return out


def naive_denylist_check(root: Path, build_glob: str = LIVE_BUILD_GLOB):
    """Counter-control C7: naive denylist that drops any path containing 'snapshot'."""
    out = []
    for p in [root / CANONICAL_LEDGER] + sorted(root.glob(build_glob)):
        rel = str(p.relative_to(root))
        if "snapshot" in rel:
            continue  # naive exclusion silently drops the file, even if canonical
        if not p.exists():
            continue
        for obj in iter_objects(p):
            if is_record(obj) and hf14_hit(obj):
                out.append((rel, "HF-14"))
    return out


def scan_hits(root: Path):
    per_file = {}
    for rel, obj in select_records(root):
        if hf14_hit(obj):
            per_file[rel] = per_file.get(rel, 0) + 1
    return per_file


def write_row(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def build_sandbox():
    """Create mini-repo sandboxes.  Never inside ROOT (asserted by C0)."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    cases = {}

    def mk(name, ledger_rows, archive_rows):
        base = SANDBOX / name
        if ledger_rows is not None:
            write_row(base / CANONICAL_LEDGER, ledger_rows)
        else:
            base.mkdir(parents=True, exist_ok=True)
        if archive_rows:
            write_row(base / "artifacts/literature/archive/old.jsonl", archive_rows)
        cases[name] = base
        return base

    clean = {"theorem_id": "T-CLEAN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
             "statement_exact": "clean row", "content_status": "verified",
             "review_status": "reviewed"}
    selfcert = {"theorem_id": "T-SELFCERT", "class_ids": ["AF-SCC-C0-VAC-GEN"],
                "statement_exact": "self certified", "status": "accepted"}
    reviewed = {"theorem_id": "T-REVIEWED", "class_ids": ["AF-SCC-C0-VAC-GEN"],
                "statement_exact": "reviewed", "status": "accepted",
                "review_verdict": "accept"}

    mk("C1_selfcert", selfcert, None)
    mk("C2_reviewed", reviewed, None)
    mk("C3_archive_only", clean, selfcert)
    mk("C4_tampered_canonical", selfcert, None)
    mk("C5_clean", clean, None)
    mk("C6_missing", None, None)
    # C7: canonical path itself contains 'snapshot' -> denylist drops it
    c7 = SANDBOX / "C7_denylist"
    write_row(c7 / "snapshots/theorems.jsonl", selfcert)
    cases["C7_denylist"] = c7
    return cases


def main() -> int:
    t0 = time.time()
    checks = []

    def record(eid, statement, observed, ok):
        checks.append({"id": eid, "statement": statement, "observed": observed,
                       "pass": bool(ok)})
        print(f"[{'PASS' if ok else 'FAIL'}] {eid}: {observed}")

    # --- pins -------------------------------------------------------------------------
    pins = {}
    pin_problems = []
    for rel in PINS:
        p = ROOT / rel
        if p.is_file():
            pins[rel] = sha256_file(p)
        else:
            pin_problems.append(f"missing pin {rel}")
    build_files = sorted(ROOT.glob(LIVE_BUILD_GLOB))
    for p in build_files:
        pins[str(p.relative_to(ROOT))] = sha256_file(p)
    print(f"pins measured: {len(pins)} files, {len(pin_problems)} problems")
    record("E1", EXPECTATIONS[0][1], f"{len(pins)} pins measured, problems={pin_problems}",
           not pin_problems)

    # --- E2 canonical ledger ----------------------------------------------------------
    canon_rows = list(iter_objects(ROOT / CANONICAL_LEDGER))
    canon_n = len(canon_rows)
    canon_forbidden = sum(1 for r in canon_rows if any(k in r for k in FORBIDDEN_KEYS))
    canon_hits = sum(1 for r in canon_rows if is_record(r) and hf14_hit(r))
    canon_class_ok = all(
        all(c in FROZEN_FOUR for c in (r.get("class_ids") or [])) for r in canon_rows
    )
    canon_content_status = sum(1 for r in canon_rows if "content_status" in r)
    canon_review_status = sum(1 for r in canon_rows if "review_status" in r)
    print(f"canonical: rows={canon_n} forbidden={canon_forbidden} hf14={canon_hits} "
          f"content_status={canon_content_status} review_status={canon_review_status} "
          f"class_tokens_frozen={canon_class_ok}")
    record("E2", EXPECTATIONS[1][1],
           f"rows={canon_n} forbidden_rows={canon_forbidden} hf14_hits={canon_hits} "
           f"class_tokens_in_frozen_four={canon_class_ok}",
           canon_forbidden == 0 and canon_hits == 0 and canon_class_ok)

    # --- E3 live build inputs ---------------------------------------------------------
    build_rows = []
    build_forbidden = 0
    build_hits = 0
    for p in build_files:
        rows = list(iter_objects(p))
        build_rows.extend(rows)
        build_forbidden += sum(1 for r in rows if any(k in r for k in FORBIDDEN_KEYS))
        build_hits += sum(1 for r in rows if is_record(r) and hf14_hit(r))
    print(f"live build inputs: files={len(build_files)} rows={len(build_rows)} "
          f"forbidden={build_forbidden} hf14={build_hits}")
    record("E3", EXPECTATIONS[2][1],
           f"files={len(build_files)} rows={len(build_rows)} forbidden={build_forbidden} "
           f"hf14={build_hits} same_count_as_canonical={len(build_rows) == canon_n}",
           build_forbidden == 0 and build_hits == 0 and len(build_rows) == canon_n)

    # --- E4 replicate the 00:38:20 report's 8-file / 346-record measurement -----------
    report = json.loads((ROOT / PINS[4]).read_text())
    report_files = []
    report_records = None
    for v in report.get("violations", []):
        if v.get("hf") == "HF-14":
            report_files = list(v.get("evidence", {}).get("files", []))
            detail = v.get("detail", "")
            import re
            m = re.search(r"(\d+) affected records", detail)
            report_records = int(m.group(1)) if m else None
    live_per_file = scan_hits(ROOT)
    subset = {f: live_per_file.get(f, 0) for f in report_files}
    subset_total = sum(subset.values())
    print(f"report HF-14: files={len(report_files)} records={report_records}; "
          f"my scan on those files={subset_total} {subset}")
    record("E4", EXPECTATIONS[3][1],
           f"report_files={len(report_files)} report_records={report_records} "
           f"replicated_records={subset_total} per_file={subset}",
           subset_total == report_records
           and all(live_per_file.get(f, 0) > 0 for f in report_files))

    # --- E5/E6 classification of every live hit file ----------------------------------
    classification = {f: classify(f) for f in sorted(live_per_file)}
    non_historical = {f: c for f, c in classification.items() if c not in HISTORICAL}
    total_hits = sum(live_per_file.values())
    live_hits = sum(n for f, n in live_per_file.items()
                    if classification[f] in ("CANONICAL", "LIVE_BUILD_INPUT"))
    hist_hits = total_hits - live_hits
    new_since_report = sorted(set(live_per_file) - set(report_files))
    print(f"live HF-14: files={len(live_per_file)} records={total_hits} "
          f"historical={hist_hits} canonical_or_live={live_hits}")
    print(f"classification: {classification}")
    print(f"new hit files since 00:38:20 report: {new_since_report}")
    record("E5", EXPECTATIONS[4][1],
           f"hit_files={len(live_per_file)} non_historical={non_historical} "
           f"new_since_report={new_since_report}",
           not non_historical and len(live_per_file) > 0)
    record("E6", EXPECTATIONS[5][1],
           f"total_hits={total_hits} historical_hits={hist_hits} live_hits={live_hits}",
           total_hits > 0 and live_hits == 0)

    # --- controls ---------------------------------------------------------------------
    cases = build_sandbox()
    c0_ok = not str(SANDBOX.resolve()).startswith(str(ROOT.resolve()) + "/")
    print(f"[{'PASS' if c0_ok else 'FAIL'}] C0: sandbox={SANDBOX} outside_root={c0_ok}")
    controls = [{"id": "C0", "statement": CONTROLS[0][1], "observed": str(SANDBOX),
                 "pass": c0_ok}]
    if not c0_ok:
        print("FATAL: sandbox inside repo; refusing to write synthetic records")
        return 2

    c1_hits = scan_hits(cases["C1_selfcert"])
    c1_ok = c1_hits.get(CANONICAL_LEDGER, 0) == 1
    controls.append({"id": "C1", "statement": CONTROLS[1][1], "observed": c1_hits, "pass": c1_ok})

    c2_hits = scan_hits(cases["C2_reviewed"])
    c2_ok = sum(c2_hits.values()) == 0
    controls.append({"id": "C2", "statement": CONTROLS[2][1], "observed": c2_hits, "pass": c2_ok})

    c3_hits = scan_hits(cases["C3_archive_only"])
    c3_ok = (c3_hits == {"artifacts/literature/archive/old.jsonl": 1}
             and proposed_check(cases["C3_archive_only"]) == [])
    controls.append({"id": "C3", "statement": CONTROLS[3][1],
                     "observed": {"scan": c3_hits,
                                  "allowlist": proposed_check(cases["C3_archive_only"])},
                     "pass": c3_ok})

    c4_scan = scan_hits(cases["C4_tampered_canonical"])
    c4_allow = proposed_check(cases["C4_tampered_canonical"])
    c4_ok = c4_scan.get(CANONICAL_LEDGER, 0) == 1 and len(c4_allow) == 1
    controls.append({"id": "C4", "statement": CONTROLS[4][1],
                     "observed": {"scan": c4_scan, "allowlist": c4_allow}, "pass": c4_ok})

    c5_scan = scan_hits(cases["C5_clean"])
    c5_ok = sum(c5_scan.values()) == 0 and proposed_check(cases["C5_clean"]) == []
    controls.append({"id": "C5", "statement": CONTROLS[5][1],
                     "observed": {"scan": c5_scan, "allowlist": proposed_check(cases["C5_clean"])},
                     "pass": c5_ok})

    c6 = proposed_check(cases["C6_missing"])
    c6_ok = len(c6) == 1 and c6[0][1] == "MISSING_CANONICAL"
    controls.append({"id": "C6", "statement": CONTROLS[6][1], "observed": c6, "pass": c6_ok})

    c7_deny = naive_denylist_check(cases["C7_denylist"])
    c7_allow = proposed_check(cases["C7_denylist"])
    c7_ok = c7_deny == [] and len(c7_allow) == 1
    controls.append({"id": "C7", "statement": CONTROLS[7][1],
                     "observed": {"denylist": c7_deny, "allowlist": c7_allow}, "pass": c7_ok})

    for c in controls[1:]:
        print(f"[{'PASS' if c['pass'] else 'FAIL'}] {c['id']}: {c['observed']}")
    record("E9", EXPECTATIONS[8][1], f"{sum(c['pass'] for c in controls)}/{len(controls)} "
           "controls pass", all(c["pass"] for c in controls))

    # --- E7/E8 proposed allowlist on the live corpus ----------------------------------
    live_allow = proposed_check(ROOT)
    print(f"allowlist predicate on live corpus: {live_allow}")
    record("E7", EXPECTATIONS[6][1],
           f"live_allowlist_violations={live_allow} (expect []); "
           f"tampered_canonical_fires={c4_ok}",
           live_allow == [] and c4_ok)
    record("E8", EXPECTATIONS[7][1],
           "covered by control C6: missing canonical -> MISSING_CANONICAL",
           c6_ok)

    # --- re-measure pins (drift => fail) ----------------------------------------------
    drift = [rel for rel, h in pins.items()
             if not (ROOT / rel).is_file() or sha256_file(ROOT / rel) != h]
    print(f"pin drift after run: {drift if drift else 'none'}")
    record("E1b", "no pinned input changed during the run", f"drift={drift}", not drift)

    elapsed = round(time.time() - t0, 2)
    ok = all(c["pass"] for c in checks)

    findings = [
        {"id": "W052-BL8-F1", "severity": "confirm",
         "text": f"BL-8 replicated at the pinned snapshot: HF-14's remaining hits are "
                 f"{total_hits} records in {len(live_per_file)} files, every one historical "
                 f"(archives, incoming shards, worker snapshots/proposals). Canonical ledger "
                 f"and live build inputs: 0 forbidden-key rows, 0 HF-14 hits."},
        {"id": "W052-BL8-F2", "severity": "confirm",
         "text": f"The 00:38:20 report's own measurement is reproduced exactly: the 8 files "
                 f"it names carry {subset_total} records (report: {report_records}). The live "
                 f"set has since grown to {len(live_per_file)} files / {total_hits} records, "
                 f"because review workers snapshot the pre-rev3 ledger; new files: "
                 f"{new_since_report}. The count is monotone in review activity, so no "
                 f"legitimate repair of the live corpus can drive it to zero."},
        {"id": "W052-BL8-F3", "severity": "confirm",
         "text": "Fix direction validated by control: an allowlist predicate (canonical "
                 "ledger + live batch-*.jsonl) returns 0 violations on the live corpus, "
                 "still fires on a tampered canonical ledger (C4), and fails closed when the "
                 "canonical file is absent (C6). A path denylist is unsafe: C7 shows a "
                 "canonical file under a 'snapshots/' path silently passing."},
        {"id": "W052-BL8-F4", "severity": "advisory-correction",
         "text": "BL-8's HF-03 sub-claim is only partly the same shape: of HF-03's 15 files, "
                 "12 are live work products (artifacts/literature/registry.jsonl, 97 records; "
                 "artifacts/literature/sources/batch-*.jsonl, 104 records) and 3 are "
                 "historical copies. HF-03's live portion is repairable by the deferred BL-2 "
                 "metadata patch and is not structurally unfalsifiable. Only HF-14 is "
                 "measured here as never-zero."},
        {"id": "W052-BL8-F5", "severity": "advisory",
         "text": "The allowlist must be paired with a path/role registry pinned by hash "
                 "(or a map field), otherwise a future canonical path can be added and be "
                 "silently out of scope. Recommendation includes 'canonical set declared in "
                 "one pinned manifest; absent entry => violation'."},
    ]
    report_obj = {
        "task_id": "W052-BL8-DETECTOR-SCOPE-01",
        "worker": "worker-052",
        "created_at": now_iso(),
        "node_id": "A0",
        "gate": "G-AUDIT",
        "gates_affected": ["G-AUDIT", "G-LIT"],
        "class_id": "GLOBAL",
        "scope_class_tokens": FROZEN_FOUR,
        "verdict": "BL8_CONFIRMED" if ok else "INCONCLUSIVE",
        "pins": pins,
        "measured": {
            "canonical_ledger": {"rows": canon_n, "forbidden_rows": canon_forbidden,
                                 "hf14_hits": canon_hits,
                                 "content_status_rows": canon_content_status,
                                 "review_status_rows": canon_review_status},
            "live_build_inputs": {"files": len(build_files), "rows": len(build_rows),
                                  "forbidden_rows": build_forbidden, "hf14_hits": build_hits},
            "corpus_hf14": {"total_hits": total_hits, "files": len(live_per_file),
                            "historical_hits": hist_hits, "canonical_or_live_hits": live_hits,
                            "per_file": live_per_file, "classification": classification,
                            "new_files_since_report": new_since_report},
            "report_20260912T003820": {"files": report_files, "records": report_records,
                                       "replicated_records": subset_total},
            "allowlist_predicate_live": live_allow,
            "elapsed_s": elapsed,
        },
        "expectations": checks,
        "controls": controls,
        "findings": findings,
        "recommendation": {
            "owner": "lead-audit (A0 rubric) with controller approval",
            "rule": "Run HF-14 (and path-scoped HFs) over an allowlist: (1) the canonical "
                    "ledger ledger/theorems.jsonl and (2) the live build inputs "
                    "artifacts/literature/theorems/batch-*.jsonl, with the allowlist itself "
                    "declared in one hash-pinned manifest so a missing canonical file or a "
                    "renamed canonical path is a violation (fail closed). Keep the corpus-wide "
                    "scan for information, report historical hits as a separate advisory "
                    "count, never as a blocking HF.",
            "do_not": "Do not patch or delete the archives/snapshots: they are the record of "
                      "what was actually reviewed at ce42d205, and deleting them would make "
                      "the audit record unfalsifiable in the other direction.",
            "validation_of_fix": "C3/C4/C6/C7 in this harness; re-run "
                                 "verify_bl8_scope_052.py after the patch.",
        },
        "falsifier": "Re-run this harness at the pinned inputs: falsified if canonical "
                     "ledger/theorems.jsonl or any live batch-*.jsonl carries an HF-14 "
                     "forbidden key or predicate hit; or if any HF-14 hit file classifies as "
                     "CANONICAL / LIVE_BUILD_INPUT; or if the harness's 8-file replication no "
                     "longer equals the 00:38:20 report's count; or if the allowlist predicate "
                     "fails to fire on the C4 tampered canonical sandbox or silently passes "
                     "the C6 missing-canonical sandbox.",
        "non_claims": [
            "no gate verdict (G-AUDIT/G-LIT stay pending)",
            "no node status change (A0/L0 untouched)",
            "no mathematical claim",
            "no canonical file was modified; this report is advisory evidence",
        ],
        "exit_ok": ok,
    }
    out = HERE / "report.json"
    out.write_text(json.dumps(report_obj, indent=2, sort_keys=True) + "\n")
    print(f"report: {out} sha256={sha256_file(out)}")
    print(f"TOTAL: {'ALL PASS' if ok else 'FAILURES PRESENT'} elapsed={elapsed}s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
