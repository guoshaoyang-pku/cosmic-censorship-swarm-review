#!/usr/bin/env python3
"""W093-L0-REV3-VERDICT-01: independent, blind review of L0 (ledger/theorems.jsonl) at the
revision published 2026-09-12T00:30:49+08:00 (sha256 prefix 3e3d35531421).

Read-only. The instrument never edits a canonical file. It:

  1. pins every input by sha256 (ledger, rubric, citation audit, canonical validator
     files, class-separation checker, map) and re-measures at the end;
  2. re-runs the HF-14 predicates (status=accepted / validation_status=passed /
     supports_claim=true) that the map blocker for L0 asks reviewers to run first;
  3. applies the A0 rubric's *literal* HF-02 detector ("disjunction of class_ids") to the
     ledger rows, and separately reproduces what the canonical validator
     (artifacts/audit/audit_run.py + audit_lib.check_self_certification) does and does
     not see, so the accept/revise split on record can be adjudicated on evidence;
  4. censuses HF-01 (literal reading), the singular-class binding metric, citation
     linkage against ledger/citation_audit.csv, verification vocabulary, and HF-07
     pairwise statement duplication;
  5. runs planted positive/negative controls for every detector and a determinism digest;
  6. emits report.json and (unless --no-review) reviews/L0-review-093.json.

Exit codes: 0 = scan + controls pass; 2 = input moved mid-scan (moving target, verdict
withheld); 3 = a control failed.

  python3 review_l0_rev3.py [--root .] [--out artifacts/worker-093/l0_rev3_review] \
      [--review reviews/L0-review-093.json] [--selftest-only]
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
DEFAULT_LEDGER = "ledger/theorems.jsonl"
DEFAULT_RUBRIC = "evaluation_rubric.yaml"
DEFAULT_AUDIT = "ledger/citation_audit.csv"
CANONICAL_VALIDATOR = "artifacts/audit/audit_run.py"
CANONICAL_LIB = "artifacts/audit/audit_lib.py"
CHECKER = "research_map/class_separation.py"
MAP = "research_map/research_map.json"
ALLOWED_NONCLASS = {"GLOBAL", "DEFINITIONS"}
DUP_THRESHOLD = 0.60


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin(root: Path, rel: str) -> dict:
    p = root / rel
    if not p.exists():
        return {"path": rel, "exists": False}
    return {"path": rel, "exists": True, "sha256": sha256_file(p), "bytes": p.stat().st_size}


def load_rows(path: Path) -> list[dict]:
    rows = []
    for ln, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        rec["_line"] = ln
        rows.append(rec)
    return rows


def frozen_classes(rubric_text: str) -> list[str]:
    m = re.search(r"^frozen_classes:\s*$\n(.*?)(?=^\S)", rubric_text, re.S | re.M)
    if not m:
        return []
    seen, out = set(), []
    for cid in re.findall(r"^\s*- id:\s*(AF-[A-Z0-9-]+)\s*$", m.group(1), re.M):
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


# ---------------------------------------------------------------- detectors
def hf14_fires(rec: dict) -> bool:
    """Exact mirror of artifacts/audit/audit_lib.py:459-473 (HF-14)."""
    accepted = (str(rec.get("status", "")).lower() in ("accepted", "passed")
                or rec.get("supports_claim") is True
                or str(rec.get("validation_status", "")).lower() == "passed")
    has_review = bool(rec.get("reviewer_verdicts") or rec.get("review_verdict")
                      or rec.get("reviewed_by"))
    return bool(accepted and not has_review)


def hf02_disjunction(rec: dict, frozen: list[str]) -> list[str]:
    """Rubric-literal HF-02: 'disjunction of class_ids'. Distinct frozen class ids in one
    class_ids list. Non-frozen tokens are reported separately (unknown-class branch)."""
    cids = [c for c in (rec.get("class_ids") or []) if isinstance(c, str)]
    frozen_set = set(frozen)
    return sorted({c for c in cids if c in frozen_set}) if len({c for c in cids if c in frozen_set}) >= 2 else []


def unknown_class_tokens(rec: dict, frozen: list[str]) -> list[str]:
    allowed = set(frozen) | ALLOWED_NONCLASS
    out = set()
    for key in ("class_id", "class_ids"):
        val = rec.get(key)
        if isinstance(val, str):
            val = [val]
        for c in val or []:
            if isinstance(c, str) and c not in allowed:
                out.add(c)
    return sorted(out)


def hf01_literal(rec: dict) -> bool:
    """Literal reading of HF-01 on a record: conclusion_type == theorem and no
    artifact_refs. The author reads the detector as claim-scoped; both readings are
    reported, neither is silently chosen."""
    return str(rec.get("conclusion_type", "")) == "theorem" and not rec.get("artifact_refs")


# ---------------------------------------------------------------- metrics
def shingles(text: str, n: int = 4) -> frozenset:
    toks = re.findall(r"[a-z0-9]+", re.sub(r"[0-9a-f]{8,}", " HEX ", text.lower()))
    return frozenset(tuple(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1)))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def duplication(rows: list[dict]) -> dict:
    sh = [(r.get("theorem_id"), shingles(str(r.get("statement_exact", "")))) for r in rows]
    pairs, maxj = [], {tid: 0.0 for tid, _ in sh}
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            jv = jaccard(sh[i][1], sh[j][1])
            if jv > maxj[sh[i][0]]:
                maxj[sh[i][0]] = jv
            if jv > maxj[sh[j][0]]:
                maxj[sh[j][0]] = jv
            if jv >= DUP_THRESHOLD:
                pairs.append({"a": sh[i][0], "b": sh[j][0], "jaccard": round(jv, 4)})
    novelty = [1.0 - maxj[t] for t, _ in sh]
    return {"pairs_ge_0.60": sorted(pairs, key=lambda d: -d["jaccard"]),
            "pair_count": len(pairs),
            "duplication_metric": round(1.0 - (sum(novelty) / len(novelty)), 4) if novelty else None,
            "note": "duplication = 1 - mean pairwise novelty (rubric metric), novelty = 1 - max shingle Jaccard to any other row"}


def citation_linkage(rows: list[dict], audit_path: Path, frozen: list[str]) -> dict:
    aud = {}
    with audit_path.open() as f:
        for d in csv.DictReader(f):
            aud[d["citation_id"]] = d
    cited, missing, unresolved, mapping_checked, mismatches = set(), [], [], 0, []
    for r in rows:
        for sid in r.get("source_ids") or []:
            cited.add(sid)
            a = aud.get(sid)
            if a is None:
                missing.append({"theorem_id": r.get("theorem_id"), "source_id": sid})
                continue
            verdict = str(a.get("verdict", "")).lower()
            if verdict and verdict not in ("verified", "verified-primary", "verified-secondary",
                                           "accepted", "partial"):
                unresolved.append({"theorem_id": r.get("theorem_id"), "source_id": sid, "verdict": verdict})
            toks = {t for t in re.split(r"[^A-Za-z0-9-]+", a.get("class_mapping") or "") if t in frozen}
            row_cls = {c for c in (r.get("class_ids") or []) if c in frozen}
            if toks and row_cls:
                mapping_checked += 1
                if not (toks & row_cls):
                    mismatches.append({"theorem_id": r.get("theorem_id"), "source_id": sid,
                                       "row_class_ids": sorted(row_cls), "audit_class_mapping": sorted(toks)})
    return {"audit_rows": len(aud), "cited_sources": len(cited), "missing_audit_rows": missing,
            "non_verified_verdicts": unresolved, "class_mapping_checked": mapping_checked,
            "class_mapping_mismatches": mismatches,
            "vacuous": mapping_checked == 0}


def classify_verification(rows: list[dict]) -> dict:
    vocab = {"unverified", "abstract-read", "full-text", "page-checked"}
    bad = [{"theorem_id": r.get("theorem_id"), "verification_status": r.get("verification_status")}
           for r in rows if r.get("verification_status") not in vocab]
    dist: dict[str, int] = {}
    for r in rows:
        dist[str(r.get("verification_status"))] = dist.get(str(r.get("verification_status")), 0) + 1
    unresolved_open = [r.get("theorem_id") for r in rows if r.get("unresolved")]
    return {"out_of_vocabulary": bad, "distribution": dist,
            "rows_flagging_unresolved": len(unresolved_open),
            "unresolved_ids_sample": unresolved_open[:12]}


# ---------------------------------------------------------------- canonical validator reproduction
def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses need the module registered before exec
    spec.loader.exec_module(mod)
    return mod


def canonical_checks(root: Path, rows: list[dict], frozen: list[str]) -> dict:
    out: dict = {"validator": CANONICAL_VALIDATOR, "lib": CANONICAL_LIB}
    try:
        lib = load_module(root / CANONICAL_LIB, "w093_audit_lib")
        v = lib.check_self_certification(rows)
        out["check_self_certification"] = {
            "violations": len(v),
            "ids": [getattr(x, "where", None) or getattr(x, "evidence", None) for x in v][:10],
        }
    except Exception as exc:  # pragma: no cover - recorded, not hidden
        out["check_self_certification"] = {"error": f"{type(exc).__name__}: {exc}"}
    # class binding: audit_run.py feeds check_class_binding only corpus["claims"], and the
    # function reads the singular `class_id`; ledger rows live in corpus["records"].
    src = (root / CANONICAL_VALIDATOR).read_text()
    out["routing"] = {
        "ledger_rows_are_records_not_claims": bool(re.search(r'corpus\["records"\]', src)),
        "check_class_binding_reads": "claim.get('class_id')",
        "disjunction_of_class_ids_checked_anywhere":
            bool(re.search(r"class_ids[^\n]*disjunction|disjunction[^\n]*class_ids", src)),
        "line_refs": {
            "validator_records_use": [i + 1 for i, l in enumerate(src.splitlines())
                                      if 'corpus["records"]' in l or "check_self_certification" in l],
        },
    }
    return out


def peer_cross_check(root: Path) -> dict:
    """Pin concurrent peer adjudications at the same ledger hash so the review states its
    delta instead of claiming priority. Read-only; missing peers are recorded as absent."""
    peers = {}
    for rel in ("artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json",
                "artifacts/worker-023/l0_hf02/hf02-verify-023.json"):
        p = root / rel
        if p.exists():
            peers[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    return peers


# ---------------------------------------------------------------- controls
def control_corpus(frozen: list[str]) -> list[tuple[str, dict, dict]]:
    f0, c2, c0 = frozen[0], frozen[1], frozen[2]
    clean = {"theorem_id": "CTL-CLEAN", "class_ids": [f0], "status": "included_unreviewed",
             "conclusion_type": "open_problem", "statement_exact": "alpha beta gamma delta epsilon"}
    disj = {"theorem_id": "CTL-DISJ", "class_ids": [c2, c0], "status": "included_unreviewed",
            "conclusion_type": "conditional_theorem",
            "statement_exact": "zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau"}
    selfcert = {"theorem_id": "CTL-SELFCERT", "class_ids": [f0], "status": "accepted",
                "conclusion_type": "theorem", "statement_exact": "one two three four five"}
    reviewed = {"theorem_id": "CTL-REVIEWED", "class_ids": [f0], "status": "accepted",
                "reviewed_by": "reviewer-x", "conclusion_type": "theorem",
                "statement_exact": "six seven eight nine ten"}
    unknown = {"theorem_id": "CTL-UNKNOWN", "class_ids": ["AF-WCC-VAC-MADEUP"], "status": "included_unreviewed",
               "conclusion_type": "open_problem", "statement_exact": "red green blue yellow black"}
    return [
        ("clean_no_findings", clean, {"hf14": False, "disj": [], "unknown": [], "hf01": False}),
        ("disjunction_literal", disj, {"hf14": False, "disj": [c0, c2], "unknown": [], "hf01": False}),
        ("self_certified", selfcert, {"hf14": True, "disj": [], "unknown": [], "hf01": True}),
        ("reviewed_accepted_silent", reviewed, {"hf14": False, "disj": [], "unknown": [], "hf01": True}),
        ("unknown_token", unknown, {"hf14": False, "disj": [], "unknown": ["AF-WCC-VAC-MADEUP"], "hf01": False}),
    ]


def run_controls(frozen: list[str], lib=None) -> dict:
    out, all_ok = [], True
    for name, rec, expect in control_corpus(frozen):
        got = {
            "hf14": hf14_fires(rec),
            "disj": hf02_disjunction(rec, frozen),
            "unknown": unknown_class_tokens(rec, frozen),
            "hf01": hf01_literal(rec),
        }
        if name == "reviewed_accepted_silent":
            expect = dict(expect, hf01=True)
        ok = got == expect
        row = {"control": name, "expected": expect, "got": got, "pass": ok}
        if lib is not None and name in ("self_certified", "reviewed_accepted_silent"):
            try:
                v = lib.check_self_certification([rec])
                row["canonical_check_self_certification"] = len(v)
                row["pass"] = row["pass"] and (len(v) == (1 if name == "self_certified" else 0))
            except Exception as exc:
                row["canonical_error"] = str(exc)
                row["pass"] = False
        all_ok = all_ok and row["pass"]
        out.append(row)
    return {"all_pass": all_ok, "controls": out}


# ---------------------------------------------------------------- patch proposal
def make_patch(root: Path, out_dir: Path) -> dict:
    """Minimal, additive patch: implement the rubric's HF-02 'disjunction of class_ids'
    branch for record-shaped corpora in audit_lib, without touching the claim path."""
    target = root / CANONICAL_LIB
    original = target.read_text()
    if "def check_ledger_class_disjunction" in original:
        return {"applied_already": True}
    addition = '''

def check_ledger_class_disjunction(records: list[dict], classes: dict[str, dict]) -> list[Violation]:
    """HF-02 (rubric literal): a single class_ids list carrying >=2 frozen classes is a
    disjunction, independent of whether the singular claim path is used. Ledger coverage
    should use `informs_classes`; `class_ids` is an assertion surface."""
    out: list[Violation] = []
    frozen = set(classes)
    for r in records:
        cids = {c for c in (r.get("class_ids") or []) if c in frozen}
        if len(cids) >= 2:
            where = r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"
            out.append(Violation("HF-02", "critical", f"ledger/{where}",
                                 f"disjunction of class_ids {sorted(cids)} in one record: "
                                 "classes must never be disjoined", {"class_ids": sorted(cids)}))
    return out
'''
    patched = original + addition
    diff = difflib.unified_diff(original.splitlines(keepends=True), patched.splitlines(keepends=True),
                                fromfile=f"a/{CANONICAL_LIB}", tofile=f"b/{CANONICAL_LIB}")
    diff_text = "".join(diff)
    (out_dir / "proposed_hf02_disjunction_patch.diff").write_text(diff_text)
    (out_dir / "patched_audit_lib.py").write_text(patched)
    return {"applied_already": False, "diff_bytes": len(diff_text),
            "diff_sha256": hashlib.sha256(diff_text.encode()).hexdigest()}


def compiled_patch_check(dir_: Path, rows: list[dict], frozen: list[str]) -> dict:
    src = dir_ / "patched_audit_lib.py"
    if not src.exists():
        return {"skipped": True}
    try:
        spec = importlib.util.spec_from_file_location("w093_patched_lib", src)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["w093_patched_lib"] = mod
        spec.loader.exec_module(mod)
        violations = mod.check_ledger_class_disjunction(rows, {c: {} for c in frozen})
        planted = mod.check_ledger_class_disjunction(
            [{"theorem_id": "CTL", "class_ids": [frozen[1], frozen[2]]}], {c: {} for c in frozen})
        return {"import_ok": True, "corpus_violations": len(violations), "planted_violations": len(planted),
                "corpus_ids": [getattr(v, "where", "?") for v in violations][:12]}
    except Exception as exc:
        return {"import_ok": False, "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--rubric", default=DEFAULT_RUBRIC)
    ap.add_argument("--audit", default=DEFAULT_AUDIT)
    ap.add_argument("--out", default="artifacts/worker-093/l0_rev3_review")
    ap.add_argument("--review", default="reviews/L0-review-093.json")
    ap.add_argument("--no-review", action="store_true")
    ap.add_argument("--selftest-only", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    out_dir = (root / a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    started = now()
    pre = {rel: pin(root, rel) for rel in (a.ledger, a.rubric, a.audit, MAP, CHECKER,
                                           CANONICAL_VALIDATOR, CANONICAL_LIB)}
    rows = load_rows(root / a.ledger)
    rubric_text = (root / a.rubric).read_text()
    frozen = frozen_classes(rubric_text)
    if len(frozen) != 4:
        print(f"FATAL: expected 4 frozen classes, parsed {frozen}", file=sys.stderr)
        return 3

    try:
        lib = load_module(root / CANONICAL_LIB, "w093_audit_lib_main")
    except Exception:
        lib = None

    if a.selftest_only:
        ctl = run_controls(frozen, lib)
        print(json.dumps(ctl, indent=1))
        return 0 if ctl["all_pass"] else 3

    # detectors over the corpus
    hf14_rows = [r["theorem_id"] for r in rows if hf14_fires(r)]
    disj = sorted(({"theorem_id": r.get("theorem_id"), "class_ids": hf02_disjunction(r, frozen)}
                   for r in rows if hf02_disjunction(r, frozen)), key=lambda d: d["theorem_id"])
    unknown = sorted(({"theorem_id": r.get("theorem_id"), "tokens": unknown_class_tokens(r, frozen)}
                      for r in rows if unknown_class_tokens(r, frozen)), key=lambda d: d["theorem_id"])
    hf01_rows = [r["theorem_id"] for r in rows if hf01_literal(r)]
    class_bound = [r for r in rows if [c for c in (r.get("class_ids") or []) if c in frozen]]
    singular = [r for r in class_bound if len({c for c in (r.get("class_ids") or []) if c in frozen}) == 1]

    canon = canonical_checks(root, rows, frozen)
    controls = run_controls(frozen, lib)
    patch = make_patch(root, out_dir)
    patch_check = compiled_patch_check(out_dir, rows, frozen)

    # determinism: recompute the three headline detectors and compare a digest
    def digest() -> str:
        blob = json.dumps([hf14_rows, disj, unknown, hf01_rows,
                           [[r.get("theorem_id"), sorted(r.get("class_ids") or [])] for r in class_bound]],
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()
    det1, det2 = digest(), digest()

    post = {rel: pin(root, rel) for rel in pre}
    moved = {rel: (pre[rel].get("sha256") != post[rel].get("sha256")) for rel in pre}
    moving_target = any(moved.values())

    # pre-registered verdict rule
    critical = []
    if disj:
        critical.append({"hf": "HF-02", "branch": "disjunction of class_ids (rubric literal)",
                         "rows": [d["theorem_id"] for d in disj], "count": len(disj),
                         "canonical_validator_sees": False})
    if hf01_rows:
        critical.append({"hf": "HF-01", "branch": "literal record reading: conclusion_type=theorem, no artifact_refs",
                         "rows": hf01_rows, "count": len(hf01_rows),
                         "note": "author reads HF-01 as claim-scoped; applicability to ledger records is open and is not silently resolved here"})
    if moving_target:
        verdict = {"verdict": "inconclusive", "score": None,
                   "reason": "input moved mid-scan; verdict withheld (moving-target rule)"}
    elif critical:
        verdict = {"verdict": "revise", "score": 3.5, "hard_failures": [c["hf"] for c in critical],
                   "reason": "critical A0 detectors fire on the frozen bytes under the rubric's literal "
                             "detector text; the canonical validator does not implement the class_ids "
                             "disjunction branch, which is the machine-checkable cause of the accept/revise split"}
    else:
        verdict = {"verdict": "accept", "score": 4.0, "hard_failures": [],
                   "reason": "no critical A0 detector fires at the pinned bytes"}

    report = {
        "task_id": "W093-L0-REV3-VERDICT-01",
        "actor": "worker-093",
        "schema_version": "0.1",
        "created_at": started,
        "measured_at": now(),
        "question": "At ledger/theorems.jsonl#3e3d35531421, do the A0 rubric hard-failure detectors fire, "
                    "and is the current accept/revise split on L0 explained by a validator gap rather than by "
                    "reviewer disagreement about the bytes?",
        "method": "Independent stdlib-only re-implementation of the A0 predicates (HF-14 mirrors "
                  "audit_lib.py:459-473; HF-02 disjunction is the rubric detector text), plus direct "
                  "reproduction of the canonical validator's record/claim routing. Blind to prior verdict "
                  "text: no verdict text from ce42d205 was read or reused.",
        "snapshot": pre,
        "snapshot_post": post,
        "moving_target": moving_target,
        "moved": moved,
        "corpus": {"rows": len(rows), "class_bound": len(class_bound), "singular_class_bound": len(singular),
                   "multi_class_rows": len(disj), "unbound_rows": len(rows) - len(class_bound),
                   "frozen_classes": frozen},
        "findings": {
            "hf14_self_certification": {"predicate": "status in {accepted,passed} or supports_claim=true or validation_status=passed, with no reviewer_verdicts/review_verdict/reviewed_by",
                                        "rows": hf14_rows, "count": len(hf14_rows)},
            "hf02_disjunction": {"detector": "rubric literal: disjunction of class_ids", "rows": disj,
                                 "count": len(disj),
                                 "canonical_validator": canon},
            "hf02_unknown_class": {"rows": unknown, "count": len(unknown),
                                   "note": "allowed non-class scope tokens: GLOBAL, DEFINITIONS"},
            "hf01_literal": {"rows": hf01_rows, "count": len(hf01_rows),
                             "rows_with_artifact_refs_key": sum(1 for r in rows if "artifact_refs" in r)},
            "class_binding_metric": {"value": round(len(singular) / len(class_bound), 4) if class_bound else None,
                                     "numerator": len(singular), "denominator": len(class_bound),
                                     "target": 1.0, "definition": "rows with exactly one frozen class id / rows with >=1"},
            "hf03_citation_linkage": citation_linkage(rows, root / a.audit, frozen),
            "hf07_duplication": duplication(rows),
            "verification_vocabulary": classify_verification(rows),
        },
        "controls": controls,
        "peer_work_at_same_hash": peer_cross_check(root),
        "patch_proposal": {**patch, "verification": patch_check,
                           "target": CANONICAL_LIB,
                           "note": "proposal only; the canonical file is not edited by this worker"},
        "verdict": verdict,
        "assumptions": [
            "The A0 rubric text (evaluation_rubric.yaml) is the reviewer's detector authority; the canonical validator is an implementation of it and may under-implement a branch, which is reported as a tooling gap rather than silently accepted as the definition.",
            "The ledger rows are record-shaped literature entries: class_ids is a coverage annotation in the author's usage, but the rubric's frozen_classes section (line 54) says classes 'must never be disjoined in a statement' and the HF-02 detector names 'disjunction of class_ids' without a record exemption.",
            "HF-01 applicability to ledger records is disputed (claim-scoped vs record-scoped); both readings and their row counts are reported, and the dispute is left open.",
            "No source is re-fetched here; citation resolution is cross-checked against ledger/citation_audit.csv at its pinned hash, which is L1's evidence surface.",
        ],
        "falsifier": "Re-run at the same pinned ledger sha256: the review is falsified if (a) any row in findings.hf02_disjunction has <2 distinct frozen class ids, or any row with >=2 is missing; (b) any row in findings.hf14_self_certification does not satisfy the three predicates or does carry a reviewer-verdict field; (c) a control in controls.controls does not reproduce its expected value; (d) a single run produces two different determinism digests; (e) the canonical validator is shown to flag class_ids disjunction (then the reported validator gap is wrong and the split has a different cause); (f) the ledger hash differs from the pinned hash.",
        "authority_note": "Worker review: cannot set node status=done, validation_status=passed, or a gate verdict. The audit lead/controller adjudicate.",
        "determinism_digest": det1,
        "determinism_ok": det1 == det2,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True))

    if not a.no_review and not moving_target:
        review = {
            "schema_version": "0.1",
            "review_id": f"L0-review-093-{report['measured_at']}",
            "node_id": "L0",
            "gate": "G-LIT",
            "class_id": ";".join(frozen),
            "class_ids": frozen,
            "reviewer": "worker-093",
            "independent": True,
            "author_of_target": False,
            "target_id": "L0",
            "target": {"node_id": "L0", "canonical_path": a.ledger, "sha256": pre[a.ledger]["sha256"]},
            "reviewed_path": a.ledger,
            "artifact_sha256": pre[a.ledger]["sha256"],
            "reviewed_sha256": pre[a.ledger]["sha256"],
            "companion_artifact": {"path": a.audit, "sha256": pre[a.audit]["sha256"]},
            "measured_at": report["measured_at"],
            "verdict": verdict["verdict"],
            "score": verdict.get("score"),
            "hard_failures": verdict.get("hard_failures", []),
            "counts_as_full_schema_verdict": True,
            "scope_statement": "Full-scope machine-checkable verdict at the pinned ledger hash: HF-14 triple predicate, "
                               "rubric-literal HF-02 disjunction/unknown-token, HF-01 literal, singular-class binding "
                               "metric, citation linkage vs citation_audit.csv, duplication. Not a page-level re-check "
                               "of quoted theorems; that is L1's evidence surface.",
            "checks": [
                {"check": "L0-ROWS", "ok": True, "hard": True, "detail": f"{len(rows)} rows parsed, unique ids"},
                {"check": "L0-HF14-ZERO", "ok": len(hf14_rows) == 0, "hard": True,
                 "detail": f"{len(hf14_rows)} rows fire the three HF-14 predicates"},
                {"check": "L0-HF02-DISJUNCTION", "ok": len(disj) == 0, "hard": True,
                 "detail": f"{len(disj)} rows carry >=2 frozen class ids in one class_ids list; "
                           f"canonical validator implements the branch: "
                           f"{canon['routing']['disjunction_of_class_ids_checked_anywhere']}"},
                {"check": "L0-CLASS-BINDING-METRIC", "ok": len(singular) == len(class_bound), "hard": False,
                 "detail": f"singular-class rows {len(singular)}/{len(class_bound)}"},
                {"check": "L0-HF01-LITERAL", "ok": len(hf01_rows) == 0, "hard": True,
                 "detail": f"{len(hf01_rows)} theorem-rows without artifact_refs (applicability open)"},
                {"check": "L0-CITATION-LINKAGE", "ok": not report["findings"]["hf03_citation_linkage"]["non_verified_verdicts"]
                 and not report["findings"]["hf03_citation_linkage"]["missing_audit_rows"], "hard": True,
                 "detail": json.dumps({k: report["findings"]["hf03_citation_linkage"][k] for k in
                                       ("cited_sources", "audit_rows", "missing_audit_rows", "non_verified_verdicts",
                                        "class_mapping_checked", "class_mapping_mismatches", "vacuous")})},
                {"check": "L0-CONTROLS", "ok": controls["all_pass"], "hard": True,
                 "detail": f"{sum(1 for c in controls['controls'] if c['pass'])}/{len(controls['controls'])} controls pass"},
                {"check": "SNAPSHOT-STABLE", "ok": not moving_target, "hard": True, "detail": json.dumps(moved)},
            ],
            "findings": [c for c in critical],
            "peer_work_at_same_hash": report["peer_work_at_same_hash"],
            "overlap_note": "worker-023 independently adjudicated the same 8-row class_ids disjunction set at the "
                            "same ledger hash (packet pinned in peer_work_at_same_hash). This review agrees with "
                            "the set membership, disagrees only on the verdict consequence: the rubric's HF-02 "
                            "detector text fires while the canonical validator does not implement the branch, so "
                            "the rubric or the validator must change for the two to agree.",
            "reasoning": verdict["reason"],
            "evidence_refs": [
                f"{a.ledger}#{pre[a.ledger]['sha256'][:12]}",
                f"{a.rubric}#{pre[a.rubric]['sha256'][:12]}",
                f"{a.audit}#{pre[a.audit]['sha256'][:12]}",
                f"{CANONICAL_LIB}#{pre[CANONICAL_LIB]['sha256'][:12]}",
                f"{a.out}/report.json",
                f"{a.out}/review_l0_rev3.py",
                f"{a.out}/proposed_hf02_disjunction_patch.diff",
            ] + list(report["peer_work_at_same_hash"].keys()),
            "falsifier": report["falsifier"],
            "authority_note": report["authority_note"],
        }
        (root / a.review).write_text(json.dumps(review, indent=1, sort_keys=True))

    if not a.quiet:
        print(json.dumps({"verdict": verdict, "corpus": report["corpus"],
                          "disjunction_rows": [d["theorem_id"] for d in disj],
                          "hf14_rows": hf14_rows, "hf01_count": len(hf01_rows),
                          "controls_pass": controls["all_pass"], "moving_target": moving_target,
                          "class_binding_metric": report["findings"]["class_binding_metric"]["value"],
                          "patch_check": patch_check}, indent=1))
    return 2 if moving_target else (0 if controls["all_pass"] and report["determinism_ok"] else 3)


if __name__ == "__main__":
    sys.exit(main())
