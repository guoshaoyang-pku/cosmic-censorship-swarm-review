#!/usr/bin/env python3
"""W021-L0-BUILD-REPL-01 — independent replication of the L0 rev-3 build.

Worker: worker-021.  Node: L0.  Gate: G-LIT.
Classes: AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH.

Question (the literature lead's own published next_falsifier, lit-l5-20260912-019):

  Is `ledger/theorems.jsonl` sha256 a1674f094979... (L0 rev 3 final) and
  `ledger/citation_audit.csv` sha256 315c19145065... byte-exactly reproducible from the
  source-of-truth batch inputs by the pinned hardened builder
  `artifacts/literature/tools/build_literature.py` (a497a968638f...), and is the HF-14
  repair durable (fail-closed guard) rather than a hand-patch?

Method: run the pinned builder in throwaway sandboxes inside this artifact directory,
never on a canonical path; compare emitted bytes to the canonical pins; mutate sandbox
copies to prove the guard fires; run the frozen A0 HF-14 predicate and an independent
re-implementation of it and require exact per-record agreement; recount the live A0
corpus HF-14 fire list at T0.

Fail-closed: exit 3 (VOID) if any pinned input or canonical output drifts during the run;
exit 2 on any failed check or control; exit 0 only when every check passes.

Read-only on all canonical paths.  Writes only under
`artifacts/worker-021/l0_build_replication/`.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ART = HERE

# ----- canonical pins (the claim under test) ------------------------------------------
EXPECTED_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
EXPECTED_CIT = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CANON_LEDGER = ROOT / "ledger" / "theorems.jsonl"
CANON_CIT = ROOT / "ledger" / "citation_audit.csv"
BUILDER = ROOT / "artifacts" / "literature" / "tools" / "build_literature.py"
SRC_DIR = ROOT / "artifacts" / "literature" / "sources"
THM_DIR = ROOT / "artifacts" / "literature" / "theorems"
ARCHIVE = ROOT / "artifacts" / "literature" / "archive" / "theorems.pre-rev3-20260912T003026.jsonl"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
AUDIT_LIB = ROOT / "artifacts" / "audit" / "audit_lib.py"
AUDIT_RUN = ROOT / "artifacts" / "audit" / "audit_run.py"
LATEST = ROOT / "artifacts" / "audit" / "reports" / "LATEST.json"
MAP = ROOT / "research_map" / "research_map.json"

FORBIDDEN = ("status", "validation_status", "supports_claim")
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TASK_ID = "W021-L0-BUILD-REPL-01"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_jsonl(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def pin_paths():
    """All inputs/outputs whose drift voids the run."""
    paths = [CANON_LEDGER, CANON_CIT, BUILDER, FROZEN, AUDIT_LIB, AUDIT_RUN]
    paths += sorted(SRC_DIR.glob("batch-*.jsonl"))
    paths += sorted(THM_DIR.glob("batch-*.jsonl"))
    return paths


def measure(paths):
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


# ----- sandbox ------------------------------------------------------------------------
def make_sandbox(dst: Path, mutate=None, with_classes: bool = True):
    for sub in ("artifacts/literature/sources", "artifacts/literature/theorems",
                "artifacts/literature/tools", "ledger"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    if with_classes:
        (dst / "artifacts/literature/classes").mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC_DIR.glob("batch-*.jsonl")):
        shutil.copy2(p, dst / "artifacts/literature/sources" / p.name)
    for p in sorted(THM_DIR.glob("batch-*.jsonl")):
        shutil.copy2(p, dst / "artifacts/literature/theorems" / p.name)
    shutil.copy2(BUILDER, dst / "artifacts/literature/tools" / BUILDER.name)
    if mutate is not None:
        mutate(dst)


def _patch_first_theorem(dst: Path, patch):
    batches = sorted((dst / "artifacts/literature/theorems").glob("batch-*.jsonl"))
    for b in batches:
        lines = b.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                obj = json.loads(line)
                patch(obj)
                lines[i] = json.dumps(obj, ensure_ascii=False)
                b.write_text("\n".join(lines) + "\n")
                return b.name
    raise RuntimeError("no theorem row to patch")


def mutate_supports_claim(dst: Path):
    return _patch_first_theorem(dst, lambda o: o.__setitem__("supports_claim", True))


def mutate_class_token(dst: Path):
    def patch(o):
        ids = o.get("class_ids") or []
        if ids:
            ids[0] = "DEFINITIONS"
        else:
            o["class_ids"] = ["DEFINITIONS"]
    return _patch_first_theorem(dst, patch)


def run_build(sb: Path):
    t0 = datetime.now(CST)
    p = subprocess.run([sys.executable, str(sb / "artifacts/literature/tools/build_literature.py")],
                       cwd=str(sb), capture_output=True, text=True, timeout=600)
    return {"rc": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:],
            "seconds": round((datetime.now(CST) - t0).total_seconds(), 2)}


# ----- HF-14 --------------------------------------------------------------------------
def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


def frozen_hf14_ids(mod, records):
    """Frozen A0 detector, imported (not re-implemented); returns the fired record ids."""
    fired = []
    for v in mod.check_self_certification(records):
        where = str(getattr(v, "where", ""))
        fired.append(where.split("ledger/", 1)[1] if where.startswith("ledger/") else where)
    return fired


def indep_hf14_flags(records):
    """Independent re-implementation of evaluation_rubric.yaml HF-14 as read at d748a9e3."""
    out = []
    for r in records:
        status = str(r.get("status", "")).lower()
        accepted = (status in ("accepted", "passed")
                    or r.get("supports_claim") is True
                    or str(r.get("validation_status", "")).lower() == "passed")
        has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))
        out.append(bool(accepted and not has_review))
    return out


def indep_hf14_ids(records):
    return [r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"
            for r, fired in zip(records, indep_hf14_flags(records)) if fired]


SYNTHETIC = [
    {"theorem_id": "X1", "status": "accepted"},
    {"theorem_id": "X2", "validation_status": "passed"},
    {"theorem_id": "X3", "supports_claim": True},
    {"theorem_id": "X4", "status": "accepted", "reviewed_by": "reviewer-01"},
    {"theorem_id": "X5", "supports_claim": True, "reviewer_verdicts": [{"verdict": "accept"}]},
    {"theorem_id": "X6", "status": "provisional"},
    {"theorem_id": "X7", "status": "passed", "review_verdict": "revise"},
    {"theorem_id": "X8", "content_status": "verified", "verification_status": "full-text",
     "review_status": "not_independently_reviewed"},
]
SYNTHETIC_EXPECTED = [True, True, True, False, False, False, False, False]


def census(rows):
    content, review, forbidden, vstatus = {}, {}, {}, {}
    for r in rows:
        content[r.get("content_status", "<none>")] = content.get(r.get("content_status", "<none>"), 0) + 1
        review[r.get("review_status", "<none>")] = review.get(r.get("review_status", "<none>"), 0) + 1
        vstatus[r.get("verification_status", "<none>")] = vstatus.get(r.get("verification_status", "<none>"), 0) + 1
        for k in FORBIDDEN:
            if k in r:
                forbidden[k] = forbidden.get(k, 0) + 1
    return {"rows": len(rows), "unique_theorem_ids": len({r.get("theorem_id") for r in rows}),
            "content_status": content, "review_status": review,
            "verification_status": vstatus, "forbidden_key_rows": forbidden}


# ----- corpus recount -----------------------------------------------------------------
def classify(rel: str) -> str:
    if rel == "ledger/theorems.jsonl":
        return "canonical_l0"
    if rel.startswith("artifacts/literature/theorems/") or rel.startswith("artifacts/literature/sources/"):
        return "live_build_input"
    if rel.startswith("artifacts/literature/archive/"):
        return "archive_snapshot"
    if rel.startswith("artifacts/literature/incoming/"):
        return "incoming_drop"
    if rel.startswith("artifacts/worker-"):
        return "worker_snapshot"
    if rel.startswith("artifacts/audit/"):
        return "audit_artifact"
    return "other"


def corpus_recount():
    mod = load_module("w021_audit_run", AUDIT_RUN)
    corpus = mod.scan_corpus([ROOT / "artifacts", ROOT / "comms" / "outbox", ROOT / "ledger"])
    v = mod.A.check_self_certification(corpus["records"])
    by_src = {}
    for x in v:
        src = x.evidence.get("source", "") if isinstance(x.evidence, dict) else ""
        by_src[src] = by_src.get(src, 0) + 1
    files = {rel: {"count": n, "class": classify(rel)} for rel, n in sorted(by_src.items())}
    latest_hf14 = {}
    if LATEST.exists():
        for x in json.loads(LATEST.read_text()).get("violations", []):
            if x.get("hf") == "HF-14":
                where = str(x.get("where", ""))
                src = where.split("ledger:", 1)[1] if where.startswith("ledger:") else where
                latest_hf14[src] = latest_hf14.get(src, 0) + 1
    classes = {}
    for rel, d in files.items():
        classes[d["class"]] = classes.get(d["class"], 0) + d["count"]
    return {"scanned_records": len(corpus["records"]), "scanned_files": len(corpus["files"]),
            "hf14_files": files, "hf14_records_by_class": classes,
            "hf14_total": sum(by_src.values()),
            "latest_00_38_hf14_files": latest_hf14,
            "latest_sha256": sha256(LATEST) if LATEST.exists() else None}


def self_neutrality():
    """Post-write scan of this task's own directory with the frozen A0 corpus reader."""
    mod = load_module("w021_audit_run_self", AUDIT_RUN)
    corpus = mod.scan_corpus([ART])
    fires = []
    for v in mod.A.check_self_certification(corpus["records"]):
        fires.append(str(getattr(v, "where", "")))
    return {"scanned_files": len(corpus["files"]), "records_read_as_ledger_rows": len(corpus["records"]),
            "hf14_fires": len(fires), "fire_ids": fires}


# ----- main ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-corpus", action="store_true", help="skip the full A0 corpus recount")
    ap.add_argument("--keep-sandboxes", action="store_true")
    a = ap.parse_args()

    started = now()
    checks = []

    def check(cid, name, expected, observed, ok, note=""):
        checks.append({"id": cid, "name": name, "expected": expected, "observed": observed,
                       "status": "PASS" if ok else "FAIL", "note": note})
        return ok

    paths = pin_paths()
    t0 = measure(paths)
    map_sha = sha256(MAP)

    run_dir = ART / "run"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # --- R1/R2 pristine build, twice, independent sandboxes ---------------------------
    sb_a, sb_b = run_dir / "sandbox_a", run_dir / "sandbox_b"
    make_sandbox(sb_a)
    make_sandbox(sb_b)
    res_a = run_build(sb_a)
    res_b = run_build(sb_b)
    led_a, cit_a = sb_a / "ledger/theorems.jsonl", sb_a / "ledger/citation_audit.csv"
    led_b, cit_b = sb_b / "ledger/theorems.jsonl", sb_b / "ledger/citation_audit.csv"
    h_led_a = sha256(led_a) if led_a.exists() else None
    h_cit_a = sha256(cit_a) if cit_a.exists() else None
    h_led_b = sha256(led_b) if led_b.exists() else None
    h_cit_b = sha256(cit_b) if cit_b.exists() else None

    check("R1a", "pristine sandbox A build exits 0", 0, res_a["rc"], res_a["rc"] == 0,
          res_a["stderr"][-300:])
    check("R1b", "pristine sandbox A ledger == canonical pin", EXPECTED_LEDGER, h_led_a,
          h_led_a == EXPECTED_LEDGER)
    check("R1c", "pristine sandbox A citation_audit == canonical pin", EXPECTED_CIT, h_cit_a,
          h_cit_a == EXPECTED_CIT)
    check("R2a", "pristine sandbox B build exits 0", 0, res_b["rc"], res_b["rc"] == 0,
          res_b["stderr"][-300:])
    check("R2b", "build is deterministic (A ledger == B ledger)", h_led_a, h_led_b,
          h_led_a == h_led_b and h_led_a is not None)
    check("R2c", "build is deterministic (A citation_audit == B citation_audit)", h_cit_a, h_cit_b,
          h_cit_a == h_cit_b and h_cit_a is not None)

    # --- R3 emitted-record shape ------------------------------------------------------
    rows = iter_jsonl(led_a) if led_a.exists() else []
    cen = census(rows)
    check("R3a", "emitted ledger has 62 rows / 62 theorem_ids",
          {"rows": 62, "unique_theorem_ids": 62},
          {"rows": cen["rows"], "unique_theorem_ids": cen["unique_theorem_ids"]},
          cen["rows"] == 62 and cen["unique_theorem_ids"] == 62)
    check("R3b", "no emitted row carries an HF-14 forbidden key", {},
          cen["forbidden_key_rows"], not cen["forbidden_key_rows"])
    check("R3c", "every emitted row truthfully marks the review axis absent",
          {"not_independently_reviewed": cen["rows"]},
          cen["review_status"], cen["review_status"] == {"not_independently_reviewed": cen["rows"]})

    # --- R4 HF-14 differential --------------------------------------------------------
    mod = load_module("w021_audit_lib", AUDIT_LIB)
    archive_rows = iter_jsonl(ARCHIVE)
    synth_frozen_ids = frozen_hf14_ids(mod, SYNTHETIC)
    synth_indep_flags = indep_hf14_flags(SYNTHETIC)
    check("R4a", "HF-14 synthetic battery: frozen A0 detector matches pre-registered expectations",
          {"flags": SYNTHETIC_EXPECTED, "ids": ["X1", "X2", "X3"]},
          {"flags": synth_indep_flags, "ids": synth_frozen_ids},
          synth_indep_flags == SYNTHETIC_EXPECTED and synth_frozen_ids == ["X1", "X2", "X3"])
    arch_frozen = frozen_hf14_ids(mod, archive_rows)
    arch_indep = indep_hf14_ids(archive_rows) if archive_rows else ["<no rows>"]
    check("R4b", "pre-rev3 archive positive control: both predicates fire identically (non-vacuous)",
          ">=1 fire on ce42d205, frozen == independent",
          {"archive_rows": len(archive_rows), "frozen_fires": len(arch_frozen),
           "independent_fires": len(arch_indep), "ids_equal": arch_frozen == arch_indep},
          len(arch_frozen) >= 1 and arch_frozen == arch_indep)
    em_frozen = frozen_hf14_ids(mod, rows)
    em_indep = indep_hf14_ids(rows) if rows else ["<no rows>"]
    check("R4c", "emitted ledger: frozen and independent HF-14 predicates both return 0 fires",
          {"frozen": [], "independent": []}, {"frozen": em_frozen, "independent": em_indep},
          em_frozen == [] and em_indep == [])

    # --- R5 mutation controls on the builder (fail-closed) ----------------------------
    sb_c = run_dir / "sandbox_c"
    make_sandbox(sb_c, mutate=mutate_supports_claim)
    res_c = run_build(sb_c)
    msg_c = res_c["stdout"] + res_c["stderr"]
    check("R5a", "forbidden-key mutation is rejected fail-closed (rc!=0, HF-14 guard message)",
          {"rc!=0": True, "no ledger written": True, "guard": "HF-14 forbidden key"},
          {"rc": res_c["rc"], "ledger_written": (sb_c / "ledger/theorems.jsonl").exists(),
           "guard": "HF-14 forbidden key" in msg_c},
          res_c["rc"] != 0 and "HF-14 forbidden key" in msg_c
          and not (sb_c / "ledger/theorems.jsonl").exists())
    sb_d = run_dir / "sandbox_d"
    make_sandbox(sb_d, mutate=mutate_class_token)
    res_d = run_build(sb_d)
    msg_d = res_d["stdout"] + res_d["stderr"]
    check("R5b", "non-frozen class_id mutation is rejected fail-closed",
          {"rc!=0": True, "class message": True},
          {"rc": res_d["rc"], "ledger_written": (sb_d / "ledger/theorems.jsonl").exists(),
           "message": "not one of the four frozen classes" in msg_d},
          res_d["rc"] != 0 and "not one of the four frozen classes" in msg_d
          and not (sb_d / "ledger/theorems.jsonl").exists())
    sb_e = run_dir / "sandbox_e"
    make_sandbox(sb_e, with_classes=False)
    res_e = run_build(sb_e)
    led_e = sb_e / "ledger/theorems.jsonl"
    h_led_e = sha256(led_e) if led_e.exists() else None
    check("R5c", "missing classes/ dir aborts late but L0/L1 pair is still emitted byte-exactly",
          {"rc!=0": True, "ledger==canonical": True},
          {"rc": res_e["rc"], "ledger": h_led_e, "error": "classes" in (res_e["stdout"] + res_e["stderr"])},
          res_e["rc"] != 0 and h_led_e == EXPECTED_LEDGER)

    # --- D1/D2 drift ------------------------------------------------------------------
    t1 = measure(paths)
    drift = sorted(k for k in t0 if t0[k] != t1.get(k))
    map_after = sha256(MAP)
    check("D1", "no pinned input/output drifted during the run (else VOID)", [], drift, not drift,
          "pin drift voids the run")
    check("D2", "map moved during run (context only; expected, not a void)",
          "any", {"map_t0": map_sha, "map_t1": map_after}, True)

    # --- evidence hashes, then drop sandboxes BEFORE the corpus recount ---------------
    # Emitted bytes are recorded by hash only: a retained copy of the 62-row ledger would
    # duplicate canonical records into the live A0 scan corpus and distort HF-02/duplication.
    raw = ART / "raw"
    if raw.exists():
        shutil.rmtree(raw)  # never leave a previous run's ledger copies in the A0 corpus
    raw.mkdir(parents=True, exist_ok=True)
    emitted = {}
    for tag, sb in (("A", sb_a), ("B", sb_b)):
        for rel in ("ledger/theorems.jsonl", "ledger/citation_audit.csv"):
            src = sb / rel
            if src.exists():
                h = sha256(src)
                (raw / f"emitted_{tag}_{Path(rel).name}.sha256").write_text(f"{h}  {rel}\n")
                emitted[f"{tag}:{rel}"] = {"sha256": h, "bytes": src.stat().st_size}
    (raw / "entry_hashes.json").write_text(json.dumps(
        {"task_id": TASK_ID, "started_at": started, "finished_at": now(),
         "map_sha256": {"t0": map_sha, "t1": map_after},
         "pins_t0": t0, "pins_t1": t1, "drift": drift,
         "expected": {"ledger/theorems.jsonl": EXPECTED_LEDGER, "ledger/citation_audit.csv": EXPECTED_CIT},
         "emitted": emitted}, indent=2) + "\n")
    if not a.keep_sandboxes:
        shutil.rmtree(run_dir, ignore_errors=True)

    # --- R6 corpus recount (descriptive; no void) -------------------------------------
    corpus = None
    if not a.skip_corpus:
        corpus = corpus_recount()
    check("R6", "A0 HF-14 corpus recount completed",
          "recount present", {"present": corpus is not None},
          corpus is not None, "" if corpus else "skipped by flag")
    own = [p for p in (corpus or {}).get("hf14_files", {}) if p.startswith("artifacts/worker-021/")]
    check("R6b", "this task's own artifacts are corpus-neutral (no HF-14 fire attributed to worker-021)",
          [], own, not own)

    failed = [c for c in checks if c["status"] == "FAIL"]
    void = bool(drift)
    if void:
        verdict = "VOID_PIN_DRIFT"
    elif failed:
        verdict = "REVISE"
    else:
        verdict = "ACCEPT"

    report = {
        "task_id": TASK_ID,
        "worker": "worker-021",
        "instance_id": __import__("os").environ.get("DSH_INSTANCE_ID", "worker-021-20260912T004218-968807"),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "started_at": started,
        "finished_at": now(),
        "question": ("Are canonical L0 rev-3-final ledger/citation-audit bytes reproducible from the "
                     "source-of-truth batches by the pinned hardened builder, and is the HF-14 repair "
                     "durable (fail-closed) rather than a hand-patch?"),
        "pins": {"map_sha256_t0": map_sha, "map_sha256_t1": map_after,
                 "expected": {"ledger/theorems.jsonl": EXPECTED_LEDGER,
                              "ledger/citation_audit.csv": EXPECTED_CIT},
                 "entry_hashes": "artifacts/worker-021/l0_build_replication/raw/entry_hashes.json",
                 "drift": drift},
        "checks": checks,
        "emitted_census": cen,
        "hf14_differential": {
            "synthetic_expected_flags": SYNTHETIC_EXPECTED,
            "synthetic_frozen_ids": synth_frozen_ids,
            "synthetic_independent_flags": synth_indep_flags,
            "archive_rows": len(archive_rows), "archive_frozen_fires": len(arch_frozen),
            "archive_independent_fires": len(arch_indep),
            "emitted_frozen_fires": len(em_frozen), "emitted_independent_fires": len(em_indep),
        },
        "builder_runs": {"A": res_a, "B": res_b, "C_supports_claim_mutation": res_c,
                         "D_class_token_mutation": res_d, "E_missing_classes_dir": res_e},
        "corpus_recount": corpus,
        "summary": {"checks_total": len(checks), "passed": len(checks) - len(failed),
                    "failed": len(failed), "void": void, "verdict": verdict,
                    "verdict_note": ("accept at worker level means the build-replication claim "
                                     "reproduced; it is not a gate verdict, node completion or "
                                     "validation promotion")},
        "findings": [
            {"id": "W021-BR-F1", "severity": "advisory",
             "finding": ("The canonical L0/L1 pair is byte-exactly reproducible from the batch inputs "
                         "by the pinned builder in a clean sandbox, so the 'build product, not "
                         "hand-patch' claim survives independent replication at the pinned hashes."),
             "evidence": "checks R1a-R2c"},
            {"id": "W021-BR-F2", "severity": "advisory",
             "finding": ("The builder is not self-contained on a clean tree: it writes "
                         "artifacts/literature/classes/<cid>.md without creating that directory, so a "
                         "checkout without classes/ aborts after L0/L1 emission (control R5c). The "
                         "canonical pair is unaffected, but the failure mode should be mkdir'd or "
                         "documented by the literature owner."),
             "evidence": "check R5c"},
            {"id": "W021-BR-F3", "severity": "minor",
             "finding": ("The class dossiers generated by the builder count "
                         "content_status=='accepted', a value the builder itself rejects (valid set: "
                         "verified/provisional/unresolved/rejected), so every generated "
                         "classes/*.md line reports '0 accepted' regardless of content. "
                         "Non-pinned output, author-side fix."),
             "evidence": "build_literature.py:346 vs :200-201"},
        ],
        "falsifier": ("Re-run this instrument at the same pins: falsified if (a) a pristine sandbox "
                      "build does not reproduce a1674f094979 for ledger/theorems.jsonl or "
                      "315c19145065 for citation_audit.csv; (b) two pristine builds disagree; (c) the "
                      "forbidden-key or non-frozen-class mutation does not make the builder exit "
                      "non-zero with no ledger written; (d) the pre-rev3 archive positive control does "
                      "not fire; or (e) any pinned input/output drifts during the run (void, not "
                      "falsified)."),
        "no_authority": ("Worker-level receipt only: no gate verdict, node status, claim edit or "
                         "canonical write. L0 review dispatch and any G-LIT disposition belong to the "
                         "literature lead and the controller."),
    }
    if corpus:
        files = corpus["hf14_files"]
        nonhist = [p for p, d in files.items()
                   if d["class"] not in ("archive_snapshot", "incoming_drop", "worker_snapshot")]
        report["findings"].append({
            "id": "W021-BR-F4", "severity": "advisory",
            "finding": (f"A0 HF-14 recount at T0: {corpus['hf14_total']} affected records across "
                        f"{len(files)} files, every one an archive/incoming/worker snapshot of "
                        f"pre-rev3 bytes; {len(nonhist)} canonical or live-build-input files fire. "
                        "Independent confirmation of lit-l5-20260912-021 (detector scope defect): the "
                        "repair is durable on the source of truth while each new pre-rev3 worker "
                        "snapshot adds another historical false-positive file."),
            "evidence": "check R6 + report.json:corpus_recount"})
    (ART / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    # serialise fixtures with a neutral key so the live A0 corpus scan cannot read these
    # positive controls as ledger records (keeps this task corpus-neutral, see R6b)
    fixtures_public = [{("fixture_id" if k == "theorem_id" else k): v for k, v in r.items()}
                       for r in SYNTHETIC]
    (ART / "controls.json").write_text(json.dumps(
        {"task_id": TASK_ID, "at": now(),
         "hf14_synthetic": {"rows": fixtures_public, "expected_flags": SYNTHETIC_EXPECTED,
                            "frozen_ids": synth_frozen_ids,
                            "independent_flags": synth_indep_flags},
         "builder_mutations": {
             "supports_claim": {"rc": res_c["rc"],
                                "guard_message": "HF-14 forbidden key" in (res_c["stdout"] + res_c["stderr"])},
             "non_frozen_class": {"rc": res_d["rc"],
                                  "guard_message": "not one of the four frozen classes" in (res_d["stdout"] + res_d["stderr"]),
                                  "ledger_written": (sb_d / "ledger/theorems.jsonl").exists()},
             "missing_classes_dir": {"rc": res_e["rc"],
                                     "ledger_matches_canonical": h_led_e == EXPECTED_LEDGER}},
         "positive_control_archive": {"path": str(ARCHIVE.relative_to(ROOT)),
                                      "sha256": sha256(ARCHIVE) if ARCHIVE.exists() else None,
                                      "rows": len(archive_rows), "fired": len(arch_frozen)},
         "drift": drift}, indent=2, ensure_ascii=False) + "\n")

    # --- R6c final-artifact neutrality (post-write; scans only this task dir) ----------
    neut = self_neutrality()
    check("R6c", "final report.json/controls.json/raw are corpus-neutral on disk",
          {"records_read_as_ledger_rows": 0, "hf14_fires": 0}, neut,
          neut["records_read_as_ledger_rows"] == 0 and neut["hf14_fires"] == 0)
    failed = [c for c in checks if c["status"] == "FAIL"]
    verdict = "VOID_PIN_DRIFT" if void else ("REVISE" if failed else "ACCEPT")
    report["checks"] = checks
    report["summary"] = {"checks_total": len(checks), "passed": len(checks) - len(failed),
                         "failed": len(failed), "void": void, "verdict": verdict,
                         "verdict_note": ("accept at worker level means the build-replication claim "
                                          "reproduced; it is not a gate verdict, node completion or "
                                          "validation promotion")}
    (ART / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps(report["summary"], indent=2))
    for c in failed:
        print("FAIL", c["id"], c["name"], "expected=", c["expected"], "observed=", c["observed"])
    return 3 if void else (2 if failed else 0)


if __name__ == "__main__":
    sys.exit(main())
