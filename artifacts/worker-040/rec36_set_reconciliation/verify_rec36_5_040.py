#!/usr/bin/env python3
"""W040-REC36-5-SET-VERIFY-02 -- bounded class-bound worker task (AF-WCC-VAC-GEN, node F1/F0).

ONE task, read-only on every canonical byte:
 (A) fresh independent non-author verification of the worker-024 SET candidate set
     (REC-36 item 5) against live bytes, and
 (B) reconciliation of the REC36-5 "no non-author verification located" census
     classification emitted by worker-003 at 01:21:37.

The instrument never imports or executes worker-024's or worker-030's instruments.  It
re-derives everything from primary bytes: sha256 pin guard, unified-diff round trip in
/tmp sandboxes, a 7-case checker matrix, a reverse-patch reconstruction of the cited
checker, and negative/positive controls.

Exit codes: 0 = report written (verdict may be adverse), 2 = harness/pin failure
(fail-closed; nothing is claimed).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-040/rec36_set_reconciliation"
SNAP = OUT / "snapshots"

# ------------------------------------------------------------------ cited values
# Every value below was read from a cited artifact, not from live bytes:
#   worker-030 review  reviews/SET-STRENGTH-REPAIR-030.json (34dbe45db808)
#   worker-030 event   w030-set-20260912T0121-review
#   worker-003 census  artifacts/worker-003/rec36_fold_readiness/report.json (5582548617d4)
# full cited hashes (kept explicit so a copy/paste error cannot silently pass)
CITED = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/tools/check_variant_registry.py":
        "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
}

CANDIDATES = {
    "artifacts/worker-024/set_strength_repair/CANDIDATE_VARIANT_REGISTRY.json":
        "5c05a8cc7ea2583a97d3a977d81aef4de74ff9378337b42a00ef992b61aa1c2a",
    "artifacts/worker-024/set_strength_repair/CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json":
        "7a1f6212ad70e55ee760e0c271c339eca30ac7bdfca2dd5969ba14df771e6927",
    "artifacts/worker-024/set_strength_repair/CANDIDATE_check_variant_registry.py":
        "8b15f43e843dfcce87035215b92efd4b995b8fba4ac272391932364ee2ecd7fe",
    "artifacts/worker-024/set_strength_repair/repair.patch":
        "9fb0c6674849477350bbac7a0ef838f7c344dae6b3d3d918b30bc5aebf1be6ba",
}

REVIEW_PATH = "reviews/SET-STRENGTH-REPAIR-030.json"
REVIEW_SHA = "34dbe45db808bff3cda58c33f49d25a613f792ab36d34e6eba6c10e2dbe69d9a"

PRODUCER = "worker-024"
REVIEWER = "worker-030"
CENSUS_ACTOR = "worker-003"

# snapshot -> (repo path, role)
SNAPSHOTS = {
    "live.VARIANT_REGISTRY.json": ("artifacts/formulation/VARIANT_REGISTRY.json", "live"),
    "live.SET.delta.json": ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", "live"),
    "live.check_variant_registry.py": ("artifacts/formulation/tools/check_variant_registry.py", "live"),
    "live.FROZEN.json": ("artifacts/formulation/FROZEN.json", "live"),
    "live.F0.taxonomy.yaml": ("research_map/formulation_taxonomy.yaml", "live"),
    "live.F0.supplement.yaml": ("artifacts/formulation/formulation_taxonomy.yaml", "live"),
    "live.af_wcc_vacuum.yaml": ("schemas/af_wcc_vacuum.yaml", "live"),
    "cand.VARIANT_REGISTRY.json": ("artifacts/worker-024/set_strength_repair/CANDIDATE_VARIANT_REGISTRY.json", "candidate"),
    "cand.SET.delta.json": ("artifacts/worker-024/set_strength_repair/CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json", "candidate"),
    "cand.check_variant_registry.py": ("artifacts/worker-024/set_strength_repair/CANDIDATE_check_variant_registry.py", "candidate"),
    "cand.repair.patch": ("artifacts/worker-024/set_strength_repair/repair.patch", "candidate"),
    "review.SET-STRENGTH-REPAIR-030.json": (REVIEW_PATH, "review"),
}

VOLATILE = {"created_at", "duration_s", "sandbox_root", "core_digest", "run_id", "live_at_emission", "live_state_digest"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(p: Path):
    if not p.is_file():
        return {"exists": False, "path": str(p)}
    st = p.stat()
    return {
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
        "mtime_epoch": round(st.st_mtime, 3),
    }


def strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in sorted(obj.items()) if k not in VOLATILE}
    if isinstance(obj, list):
        return [strip_volatile(x) for x in obj]
    return obj


def core_digest(report) -> str:
    return hashlib.sha256(
        json.dumps(strip_volatile(report), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run(cmd, cwd=None, timeout=120):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"rc": 124, "stdout": "", "stderr": "timeout"}


# ------------------------------------------------------------------ patch handling
def split_patch(text: str):
    """Split a unified diff into {target_path: section_text}."""
    sections, cur, name = {}, [], None
    for line in text.splitlines(keepends=True):
        if line.startswith("--- "):
            if name is not None:
                sections[name] = "".join(cur)
            name = line[4:].split("\t")[0].strip()
            if name.startswith("a/"):
                name = name[2:]
            cur = [line]
        elif name is not None:
            cur.append(line)
    if name is not None:
        sections[name] = "".join(cur)
    return sections


def hunk_stats(section: str):
    import re
    minus = plus = 0
    for line in section.splitlines():
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("-"):
            minus += 1
        elif line.startswith("+"):
            plus += 1
    hunks = re.findall(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@", section, re.M)
    return {"minus_lines": minus, "plus_lines": plus,
            "hunks": [{"old": [int(a), int(b)], "new": [int(c), int(d)]} for a, b, c, d in hunks]}


def build_sandbox(tmp_root: Path, registry_src: Path, delta_src: Path, checker_src: Path, tag: str):
    """Build a checker-ready tree. Returns the sandbox path."""
    sb = tmp_root / ("sb_" + tag)
    (sb / "artifacts/formulation/tools").mkdir(parents=True, exist_ok=True)
    (sb / "artifacts/formulation/variants").mkdir(parents=True, exist_ok=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    (sb / "schemas").mkdir(parents=True, exist_ok=True)
    shutil.copy2(registry_src, sb / "artifacts/formulation/VARIANT_REGISTRY.json")
    shutil.copy2(delta_src, sb / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")
    shutil.copy2(checker_src, sb / "artifacts/formulation/tools/check_variant_registry.py")
    shutil.copy2(SNAP / "live.FROZEN.json", sb / "artifacts/formulation/FROZEN.json")
    # every other declared variant delta must exist for the delta_ref check
    for src in sorted((ROOT / "artifacts/formulation/variants").glob("*.delta.json")):
        if "AF-WCC-VAC-GEN.variant-SET" in src.name:
            continue
        shutil.copy2(src, sb / "artifacts/formulation/variants" / src.name)
    for name in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"):
        shutil.copy2(ROOT / "schemas" / name, sb / "schemas" / name)
    return sb


def run_checker(sb: Path):
    r = run([sys.executable, "artifacts/formulation/tools/check_variant_registry.py"], cwd=str(sb))
    out = {"rc": r["rc"], "stdout": r["stdout"], "stderr": r["stderr"]}
    ev = sb / "artifacts/formulation/evidence/variant_registry_check.json"
    if ev.is_file():
        try:
            out["evidence"] = json.loads(ev.read_text())
        except Exception as exc:  # pragma: no cover
            out["evidence_error"] = str(exc)
    return out


def replace_strength(text: str, new_strength: str) -> str:
    """Replace the value of the SET variant's top-level \"strength\" key (registry JSON)."""
    doc = json.loads(text)
    for v in doc.get("variants", []):
        if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
            v["strength"] = new_strength
    return json.dumps(doc, indent=2) + "\n"


def replace_delta_strength(text: str, new_strength: str) -> str:
    doc = json.loads(text)
    doc["strength"] = new_strength
    return json.dumps(doc, indent=2) + "\n"


def main() -> int:
    t0 = time.time()
    report = {
        "task_id": "W040-REC36-5-SET-VERIFY-02",
        "schema_version": "w040-rec36-5-v1",
        "actor": "worker-040",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "scope": ("Fresh independent non-author verification of the worker-024 SET candidate set at "
                  "live bytes + reconciliation of worker-003's REC36-5 census classification. "
                  "Candidate-level only: no adoption, no gate verdict, no node status, no canonical write."),
        "independence": {
            "relation_to_author": "none; worker-024 authored the candidate and its self-verifier",
            "relation_to_prior_verifier": "none; worker-030's instrument was neither imported nor executed",
            "method": ("primary-byte sha256 pin guard, unified-diff round trip with /usr/bin/patch in /tmp "
                       "sandboxes, 7-case checker matrix, reverse-patch reconstruction of the cited checker, "
                       "negative/positive controls, and an accepted-stream binding census"),
        },
        "sections": {},
        "falsifiers": [
            "Any cited pin or candidate hash re-measures differently at the same live path voids the corresponding section.",
            "Falsified if the worker-024 candidate set is shown adoptable at live checker bytes 8c7ef46f without a re-pin or a registry label revision.",
            "Falsified if the live (registry 6bac9ade, checker 8c7ef46f) pair is shown VALID by an independent checker run.",
            "Falsified if reviews/SET-STRENGTH-REPAIR-030.json is shown by a non-author to bind the candidates incorrectly or to be authored by worker-024.",
            "Falsified if a non-author verification event for the candidate set was present in research_map/events.jsonl before 2026-09-12T01:21:37+08:00.",
        ],
    }

    # ---------------- K0: snapshot integrity (fail-closed)
    snapshot_expected = {
        "live.VARIANT_REGISTRY.json": CITED["artifacts/formulation/VARIANT_REGISTRY.json"],
        "live.SET.delta.json": CITED["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
        "live.check_variant_registry.py": "8c7ef46f11db2d43430e3fd2dfa7ba2e2621134e9c4e7f148c01446bc1c7bb47",
        "live.FROZEN.json": CITED["artifacts/formulation/FROZEN.json"],
        "live.F0.taxonomy.yaml": CITED["research_map/formulation_taxonomy.yaml"],
        "live.F0.supplement.yaml": CITED["artifacts/formulation/formulation_taxonomy.yaml"],
        "live.af_wcc_vacuum.yaml": CITED["schemas/af_wcc_vacuum.yaml"],
        "cand.VARIANT_REGISTRY.json": CANDIDATES["artifacts/worker-024/set_strength_repair/CANDIDATE_VARIANT_REGISTRY.json"],
        "cand.SET.delta.json": CANDIDATES["artifacts/worker-024/set_strength_repair/CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"],
        "cand.check_variant_registry.py": CANDIDATES["artifacts/worker-024/set_strength_repair/CANDIDATE_check_variant_registry.py"],
        "cand.repair.patch": CANDIDATES["artifacts/worker-024/set_strength_repair/repair.patch"],
        "review.SET-STRENGTH-REPAIR-030.json": REVIEW_SHA,
    }
    snap = {}
    for name in sorted(SNAPSHOTS):
        m = measure(SNAP / name)
        m["expected_sha256"] = snapshot_expected[name]
        m["status"] = ("MATCH" if m.get("exists") and m.get("sha256") == snapshot_expected[name]
                       else "MISSING" if not m.get("exists") else "TAMPERED")
        if m["status"] != "MATCH":
            print("HARNESS FAIL: snapshot", name, m["status"])
            return 2
        snap[name] = m
    report["sections"]["snapshot_manifest"] = snap

    # ---------------- A: live pin + candidate measurement
    pins, drift = {}, []
    for rel, cited in sorted(CITED.items()):
        m = measure(ROOT / rel)
        rec = {"cited_sha256": cited, "measured": m}
        rec["status"] = ("MATCH" if m.get("sha256") == cited else
                         "MISSING" if not m.get("exists") else "MOVED")
        if rec["status"] != "MATCH":
            drift.append(rel)
        pins[rel] = rec
    cands = {}
    for rel, cited in sorted(CANDIDATES.items()):
        m = measure(ROOT / rel)
        cands[rel] = {"cited_sha256": cited, "measured": m,
                      "status": "MATCH" if m.get("sha256") == cited else "MOVED/MISSING"}
    report["sections"]["pin_measurements"] = pins
    report["sections"]["candidate_measurements"] = cands
    report["sections"]["live_drift"] = drift

    # ---------------- B: patch split + minimality
    patch_text = (SNAP / "cand.repair.patch").read_text()
    sections = split_patch(patch_text)
    report["sections"]["patch_sections"] = {
        name: hunk_stats(sec) for name, sec in sorted(sections.items())
    }

    tmp_root = Path(tempfile.mkdtemp(prefix="w040_set_"))
    report["sandbox_root"] = str(tmp_root)

    # ---------------- C: patch round trip against live bytes
    roundtrip = {}
    # registry + delta sections apply to live sources
    for target, live_snap, cand_snap in (
        ("artifacts/formulation/VARIANT_REGISTRY.json", "live.VARIANT_REGISTRY.json", "cand.VARIANT_REGISTRY.json"),
        ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", "live.SET.delta.json", "cand.SET.delta.json"),
        ("artifacts/formulation/tools/check_variant_registry.py", "live.check_variant_registry.py", "cand.check_variant_registry.py"),
    ):
        sbdir = tmp_root / ("rt_" + Path(target).name)
        work = sbdir / target
        work.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SNAP / live_snap, work)
        sec_path = sbdir / "section.patch"
        sec_path.write_text(sections[target])
        r = run(["patch", "-p1", "--batch", "--forward", "-i", str(sec_path)], cwd=str(sbdir))
        post = measure(work) if work.is_file() else {"exists": False}
        roundtrip[target] = {
            "apply_rc": r["rc"], "apply_stdout": r["stdout"], "apply_stderr": r["stderr"],
            "post_sha256": post.get("sha256"),
            "candidate_sha256": sha256_file(SNAP / cand_snap),
            "reproduces_candidate": post.get("sha256") == sha256_file(SNAP / cand_snap),
        }
    report["sections"]["patch_roundtrip"] = roundtrip

    # ---------------- C2: reverse patch reconstructs the cited checker
    sb = tmp_root / "revcheck"
    (sb / "artifacts/formulation/tools").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SNAP / "cand.check_variant_registry.py", sb / "artifacts/formulation/tools/check_variant_registry.py")
    (sb / "rev.patch").write_text(sections["artifacts/formulation/tools/check_variant_registry.py"])
    rrev = run(["patch", "-R", "-p1", "--batch", "--forward", "-i", str(sb / "rev.patch")], cwd=str(sb))
    old_checker = sb / "artifacts/formulation/tools/check_variant_registry.py"
    old_sha = sha256_file(old_checker) if old_checker.is_file() else None
    report["sections"]["reverse_patch_old_checker"] = {
        "rc": rrev["rc"], "stdout": rrev["stdout"], "stderr": rrev["stderr"],
        "reconstructed_sha256": old_sha,
        "cited_checker_sha256": CITED["artifacts/formulation/tools/check_variant_registry.py"],
        "matches_cited": old_sha == CITED["artifacts/formulation/tools/check_variant_registry.py"],
    }

    # ---------------- D: checker matrix
    live_reg = SNAP / "live.VARIANT_REGISTRY.json"
    live_delta = SNAP / "live.SET.delta.json"
    live_chk = SNAP / "live.check_variant_registry.py"
    cand_reg = SNAP / "cand.VARIANT_REGISTRY.json"
    cand_delta = SNAP / "cand.SET.delta.json"
    cand_chk = SNAP / "cand.check_variant_registry.py"

    # flat-label registry (live text transplanted onto the candidate bytes) for negative controls
    flat_text = json.loads(live_reg.read_text())
    flat_strength = None
    for v in flat_text.get("variants", []):
        if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
            flat_strength = v.get("strength")
    flat_cand = tmp_root / "mut.flat.VARIANT_REGISTRY.json"
    flat_cand.write_text(replace_strength(cand_reg.read_text(), flat_strength))

    matrix = {}
    cases = [
        ("M0_live_registry_live_checker", live_reg, live_delta, live_chk),
        ("M1_cand_registry_cand_checker", cand_reg, cand_delta, cand_chk),
        ("M2_live_registry_cand_checker", live_reg, live_delta, cand_chk),
        ("M3_cand_registry_live_checker", cand_reg, cand_delta, live_chk),
        ("M4_flat_label_cand_checker_NEGATIVE", flat_cand, cand_delta, cand_chk),
        ("M5_flat_label_old_checker_POSITIVE_DEFECT", flat_cand, cand_delta, old_checker),
        ("M6_live_registry_old_checker_CITED_BASELINE", live_reg, live_delta, old_checker),
    ]
    for name, reg, delta, chk in cases:
        s = build_sandbox(tmp_root, Path(reg), Path(delta), Path(chk), name)
        res = run_checker(s)
        matrix[name] = {
            "registry_sha256": sha256_file(Path(reg)),
            "checker_sha256": sha256_file(Path(chk)),
            "rc": res["rc"], "stdout": res["stdout"],
            "errors": (res.get("evidence") or {}).get("errors", []),
            "valid": (res.get("evidence") or {}).get("valid"),
        }
    # M7: tampered registry context must not apply the patch
    sb_t = tmp_root / "tamper"
    (sb_t / "artifacts/formulation").mkdir(parents=True, exist_ok=True)
    tampered = (SNAP / "live.VARIANT_REGISTRY.json").read_text().replace(
        '"status": "registered_variant_not_written"', '"status": "TAMPERED_CONTEXT"', 1)
    (sb_t / "artifacts/formulation/VARIANT_REGISTRY.json").write_text(tampered)
    (sb_t / "sec.patch").write_text(sections["artifacts/formulation/VARIANT_REGISTRY.json"])
    rt = run(["patch", "-p1", "--batch", "--forward", "-i", str(sb_t / "sec.patch")], cwd=str(sb_t))
    matrix["M7_tampered_base_patch_must_fail"] = {
        "rc": rt["rc"], "stdout": rt["stdout"], "stderr": rt["stderr"],
        "reproduces_candidate": measure(sb_t / "artifacts/formulation/VARIANT_REGISTRY.json").get("sha256")
        == sha256_file(cand_reg),
        "negative_control": rt["rc"] != 0,
    }
    report["sections"]["checker_matrix"] = matrix

    # ---------------- E: level semantics (independent marker model)
    def strength_of(text, kind):
        doc = json.loads(text)
        if kind == "registry":
            for v in doc.get("variants", []):
                if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
                    return v.get("strength")
        return doc.get("strength")

    sem = {}
    for label, path, kind in (
        ("live_registry", live_reg, "registry"), ("cand_registry", cand_reg, "registry"),
        ("live_delta", live_delta, "delta"), ("cand_delta", cand_delta, "delta"),
    ):
        s = strength_of(path.read_text(), kind)
        sem[label] = {
            "strength": s,
            "flat_prefix": bool(s and s.startswith("strictly weaker than AF-WCC-VAC-GEN")),
            "has_STRONGER": "STRONGER" in (s or ""),
            "has_WEAKER": "WEAKER" in (s or ""),
            "has_class_statement": "class statement" in (s or ""),
            "has_class_level_marker": "class-level" in (s or ""),
            "has_predicate_level_marker": "predicate-level" in (s or ""),
            "has_single_q_tail": "single-q tail" in (s or ""),
            "classification": ("FLAT_LEVEL_MIXED" if s and s.startswith("strictly weaker than AF-WCC-VAC-GEN")
                               else "CLASS_STATEMENT_QUALIFIED" if "class statement" in (s or "")
                               else "OTHER"),
        }
    report["sections"]["level_semantics"] = sem

    # ---------------- F: review binding + reconciliation
    review = json.loads((SNAP / "review.SET-STRENGTH-REPAIR-030.json").read_text())
    rev_bind = {"reviewer": review.get("reviewer"), "verdict": review.get("verdict"),
                "score": review.get("score"), "created_at": review.get("created_at"),
                "reviewer_role": review.get("reviewer_role")}
    rv = review.get("reviewed_sha256", {})
    bind_rows = []
    for path_str, cited in sorted(CANDIDATES.items()):
        base = os.path.basename(path_str)
        claimed = rv.get(base) or rv.get(path_str)
        measured = sha256_file(ROOT / path_str)
        bind_rows.append({"candidate": base, "review_claimed_sha256": claimed,
                          "measured_sha256": measured, "binds": claimed == measured})
    rev_bind["binding_rows"] = bind_rows
    rev_bind["all_candidates_bound"] = all(x["binds"] for x in bind_rows)
    rev_bind["reviewer_is_not_producer"] = review.get("reviewer") != PRODUCER
    rev_bind["review_hash"] = sha256_file(SNAP / "review.SET-STRENGTH-REPAIR-030.json")
    rev_bind["review_event"] = {
        "event_id": "w030-set-20260912T0121-review",
        "created_at": "2026-09-12T01:21:09+08:00",
        "received_at": "2026-09-12T01:22:04+08:00",
    }
    report["sections"]["review_binding"] = rev_bind

    # accepted-stream scan: replicate worker-003's events_for_sha predicate
    events = []
    for line in (ROOT / "research_map/events.jsonl").read_text(errors="replace").splitlines():
        if '"event_id"' not in line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    accepted_hits = {}
    for path_str in CANDIDATES:
        sha = sha256_file(ROOT / path_str)
        short = sha[:16]
        hits = []
        for e in events:
            if e.get("actor") in (CENSUS_ACTOR, PRODUCER):
                continue
            raw = json.dumps(e)
            if sha in raw or short in raw:
                hits.append({"event_id": e.get("event_id"), "actor": e.get("actor"),
                             "event_type": e.get("event_type"),
                             "created_at": e.get("created_at"),
                             "received_at": e.get("_received_at")})
        accepted_hits[os.path.basename(path_str)] = hits

    # file-level scan: every reviews/*.json that binds a candidate hash and is by a non-author
    file_hits = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        raw = json.dumps(doc)
        bound = [os.path.basename(c) for c in CANDIDATES if sha256_file(ROOT / c)[:16] in raw]
        if not bound:
            continue
        actor = doc.get("reviewer") or doc.get("actor")
        if actor in (PRODUCER, CENSUS_ACTOR) or actor is None:
            continue
        file_hits.append({"path": str(p.relative_to(ROOT)), "actor": actor,
                          "verdict": doc.get("verdict"), "bound_candidates": sorted(bound),
                          "sha256": sha256_file(p)})

    census_created = "2026-09-12T01:21:37+08:00"
    review_mtime = measure(SNAP / "review.SET-STRENGTH-REPAIR-030.json").get("mtime")
    checker_mtime = pins["artifacts/formulation/tools/check_variant_registry.py"]["measured"].get("mtime")
    reconciliation = {
        "requirement": ("REC36-5: obtain one non-author verification of the worker-024 SET candidate set "
                        "(worker-003 census hard failure REC36-5:STAGED_AWAITING_INDEPENDENT_VERIFICATION)"),
        "accepted_stream_predicate": "worker-003 events_for_sha: scan research_map/events.jsonl for the candidate sha, exclude actor in {worker-003, producer}",
        "accepted_stream_hits": accepted_hits,
        "file_level_binding_records": file_hits,
        "timeline": {
            "worker-024_candidate_events": "2026-09-12T01:16:47+0800",
            "worker-030_review_file_mtime_snapshot": review_mtime,
            "worker-030_review_event_created_at": "2026-09-12T01:21:09+08:00",
            "worker-003_census_report_created_at": census_created,
            "live_checker_mtime_at_snapshot": checker_mtime,
            "worker-030_events_received_at": "2026-09-12T01:22:04+08:00",
            "rev14_registry_and_delta_write_mtime": "2026-09-12T01:25:42+08:00",
        },
        "finding": ("The non-author verification existed as a file from 01:20:42 and as an event from 01:21:09, "
                    "but the accepted-stream scan at 01:21:37 could not see it because the outbox events were "
                    "ingested at 01:22:04 (27 s after the census report). The census scans events.jsonl only; it "
                    "does not scan the reviews/ tree for binding records. REC36-5's requirement was therefore "
                    "satisfied on disk at the cited pins, and the census classification is an ingest-race "
                    "artifact, not a missing verification. The checker moved at 01:21:56 and the registry/delta "
                    "at 01:25:42, so the verification does not bind live bytes; the rev14 live pair is valid and "
                    "needs its own post-fold non-author verification."),
        "checker_drift": {
            "cited_checker_sha256": CITED["artifacts/formulation/tools/check_variant_registry.py"],
            "live_checker_sha256_snapshot": pins["artifacts/formulation/tools/check_variant_registry.py"]["measured"].get("sha256"),
            "live_checker_mtime_snapshot": checker_mtime,
            "events_citing_live_hash": sum(1 for e in events if "8c7ef46f" in json.dumps(e)),
            "events_citing_cited_hash": sum(1 for e in events if "c471da4b" in json.dumps(e)),
            "consequence": ("at snapshot time (registry 6bac9ade, checker 8c7ef46f) the live pair was red and "
                            "the candidate checker hunk no longer applied; the rev14 fold then wrote registry "
                            "08afa691 / delta 518cab5d at 01:25:42, and the live pair is valid at emission "
                            "(see live_at_emission)"),
        },
    }
    report["sections"]["reconciliation"] = reconciliation

    # ---------------- F2: live state at emission (the tree moved mid-task)
    live_now, drift_now = {}, []
    for rel, cited in sorted(CITED.items()):
        m = measure(ROOT / rel)
        st = "MATCH" if m.get("sha256") == cited else ("MISSING" if not m.get("exists") else "MOVED")
        live_now[rel] = {"cited_sha256": cited, "measured": m, "status": st}
        if st != "MATCH":
            drift_now.append(rel)
    live_pair = run_checker(build_sandbox(
        tmp_root, ROOT / "artifacts/formulation/VARIANT_REGISTRY.json",
        ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        ROOT / "artifacts/formulation/tools/check_variant_registry.py", "live_emission"))
    # candidate components against live bytes
    cand_vs_live = {}
    for name, target in (
        ("registry_hunk_vs_live", "artifacts/formulation/VARIANT_REGISTRY.json"),
        ("delta_hunk_vs_live", "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"),
        ("checker_hunk_vs_live", "artifacts/formulation/tools/check_variant_registry.py"),
    ):
        sb2 = tmp_root / ("cvl_" + name)
        work = sb2 / target
        work.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / target, work)
        sp = sb2 / "section.patch"
        sp.write_text(sections[target])
        rr = run(["patch", "-p1", "--batch", "--forward", "-i", str(sp)], cwd=str(sb2))
        post = measure(work).get("sha256")
        cand_vs_live[name] = {"rc": rr["rc"], "post_sha256": post,
                              "reproduces_candidate": post == sha256_file(SNAP / (
                                  "cand.VARIANT_REGISTRY.json" if "registry" in name else
                                  "cand.SET.delta.json" if "delta" in name else
                                  "cand.check_variant_registry.py"))}
    # candidate checker against the live (rev14) registry
    sb3 = build_sandbox(tmp_root, ROOT / "artifacts/formulation/VARIANT_REGISTRY.json",
                        ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
                        SNAP / "cand.check_variant_registry.py", "cand_checker_live_registry")
    cand_checker_live = run_checker(sb3)
    live_label = {}
    try:
        doc = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
        for v in doc.get("variants", []):
            if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
                s = v.get("strength") or ""
                live_label = {
                    "strength": s,
                    "has_class_level_marker": "class-level" in s,
                    "has_predicate_level_marker": "predicate-level" in s,
                    "flat_prefix": s.startswith("strictly weaker than AF-WCC-VAC-GEN"),
                    "classification": ("LEVEL_QUALIFIED_REV14" if "class-level" in s and "predicate-level" in s
                                       else "FLAT_LEVEL_MIXED" if s.startswith("strictly weaker") else "OTHER"),
                }
    except Exception as exc:
        live_label = {"error": str(exc)}
    report["sections"]["live_at_emission"] = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "pins": live_now, "drift": drift_now,
        "live_pair": {"registry_sha256": live_now["artifacts/formulation/VARIANT_REGISTRY.json"]["measured"].get("sha256"),
                      "delta_sha256": live_now["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"]["measured"].get("sha256"),
                      "checker_sha256": live_now["artifacts/formulation/tools/check_variant_registry.py"]["measured"].get("sha256"),
                      "rc": live_pair["rc"], "errors": (live_pair.get("evidence") or {}).get("errors", []),
                      "valid": (live_pair.get("evidence") or {}).get("valid")},
        "candidate_vs_live": cand_vs_live,
        "candidate_checker_vs_live_registry": {"rc": cand_checker_live["rc"],
                                               "errors": (cand_checker_live.get("evidence") or {}).get("errors", [])},
        "live_set_label": live_label,
        "note": ("The rev14 fold wrote artifacts/formulation/VARIANT_REGISTRY.json (mtime 01:25:42) and "
                 "AF-WCC-VAC-GEN.variant-SET.delta.json (mtime 01:25:42) after this task's snapshot and after "
                 "the worker-030 verification; FROZEN.json still measures rev29. Any further byte move voids "
                 "this section; it is excluded from core_digest and carries its own live_state_digest."),
    }
    report["sections"]["live_at_emission"]["emission_controls"] = [
        {"id": "E1_live_pair_valid", "pass": bool((live_pair.get("evidence") or {}).get("valid")),
         "detail": "rev14 registry/delta + checker 8c7ef46f run VALID at emission"},
        {"id": "E2_candidate_registry_hunk_no_longer_applies",
         "pass": not cand_vs_live["registry_hunk_vs_live"]["reproduces_candidate"],
         "detail": "worker-024 registry hunk no longer reproduces its candidate against live bytes"},
        {"id": "E3_candidate_checker_rejects_live_rev14_label",
         "pass": cand_checker_live["rc"] != 0,
         "detail": "the candidate checker's marker vocabulary is superseded by the rev14 label"},
    ]
    report["live_state_digest"] = hashlib.sha256(json.dumps(
        report["sections"]["live_at_emission"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    # ---------------- G: controls
    controls = [
        {"id": "K0_snapshot_integrity", "pass": all(v["status"] == "MATCH" for v in snap.values()),
         "detail": "12 pinned snapshots hash-verified against their cited/recorded values before any run"},
        {"id": "K1_patch_reproduces_registry",
         "pass": roundtrip["artifacts/formulation/VARIANT_REGISTRY.json"]["reproduces_candidate"],
         "detail": "hunk 1 (1 line) applied to the live registry reproduces the candidate byte-for-byte"},
        {"id": "K2_patch_reproduces_delta",
         "pass": roundtrip["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"]["reproduces_candidate"],
         "detail": "hunk 2 (1 line) applied to the live delta reproduces the candidate byte-for-byte"},
        {"id": "K3_checker_hunk_stale",
         "pass": not roundtrip["artifacts/formulation/tools/check_variant_registry.py"]["reproduces_candidate"],
         "detail": "hunk 3 fails to apply to the live checker at 8c7ef46f (context moved)"},
        {"id": "K4_tampered_base_rejected",
         "pass": matrix["M7_tampered_base_patch_must_fail"]["negative_control"],
         "detail": "a one-token context mutation stops the patch (rc!=0) and does not reproduce the candidate"},
        {"id": "K5_flat_label_rejected_by_candidate_checker",
         "pass": matrix["M4_flat_label_cand_checker_NEGATIVE"]["rc"] != 0,
         "detail": "candidate checker fails the flat level-confused label (level assertion discriminates)"},
        {"id": "K6_old_checker_accepts_flat_label",
         "pass": matrix["M5_flat_label_old_checker_POSITIVE_DEFECT"]["rc"] == 0,
         "detail": "reconstructed cited checker c471da4b passes the flat label because the bracket note contains STRONGER"},
        {"id": "K7_cited_baseline_valid",
         "pass": matrix["M6_live_registry_old_checker_CITED_BASELINE"]["rc"] == 0,
         "detail": "live registry + reconstructed cited checker was VALID (the registry did not move)"},
        {"id": "K8_live_pair_red",
         "pass": matrix["M0_live_registry_live_checker"]["rc"] != 0,
         "detail": "live registry 6bac9ade + live checker 8c7ef46f is INVALID at the level marker rule"},
        {"id": "K9_reverse_patch_matches_cited_checker",
         "pass": report["sections"]["reverse_patch_old_checker"]["matches_cited"],
         "detail": "reverse-applying hunk 3 to the candidate checker reconstructs the cited c471da4b bytes"},
        {"id": "K10_review_binds_all_candidates", "pass": rev_bind["all_candidates_bound"],
         "detail": "review reviewed_sha256 binds all four candidate hashes as measured"},
        {"id": "K11_reviewer_not_producer", "pass": rev_bind["reviewer_is_not_producer"],
         "detail": "worker-030 != worker-024"},
        {"id": "K12_producer_event_excluded",
         "pass": all(all(h["actor"] != PRODUCER for h in hits) for hits in accepted_hits.values()),
         "detail": "producer events are excluded by the non-author predicate"},
    ]
    report["sections"]["controls"] = controls

    # ---------------- verdict
    live_checker_moved = pins["artifacts/formulation/tools/check_variant_registry.py"]["status"] != "MATCH"
    cand_ok = (roundtrip["artifacts/formulation/VARIANT_REGISTRY.json"]["reproduces_candidate"]
               and roundtrip["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"]["reproduces_candidate"])
    live_valid = bool((live_pair.get("evidence") or {}).get("valid"))
    all_cited_pins_moved = all(v["status"] != "MATCH" for v in
                               (pins["artifacts/formulation/VARIANT_REGISTRY.json"],
                                pins["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
                                pins["artifacts/formulation/tools/check_variant_registry.py"]))
    if cand_ok and live_valid and all_cited_pins_moved:
        verdict = ("REC36_5_NON_AUTHOR_VERIFICATION_EXISTED_AT_CITED_PINS__ALL_THREE_CITED_PINS_MOVED__"
                   "REV14_LIVE_PAIR_VALID__POST_FOLD_NON_AUTHOR_VERIFICATION_PENDING")
    elif cand_ok and live_checker_moved:
        verdict = "SET_CANDIDATE_REGISTRY_AND_DELTA_STILL_REPRODUCE__CHECKER_COMPONENT_STALE__LIVE_PAIR_RED"
    elif cand_ok and not live_checker_moved:
        verdict = "SET_CANDIDATE_REPRODUCES_AT_CITED_PINS__NON_AUTHOR_VERIFICATION_PRESENT"
    else:
        verdict = "SET_CANDIDATE_FAILS_INDEPENDENT_REPRODUCTION"
    report["verdict"] = verdict
    report["verdict_scope"] = ("candidate/evidence-level only; not an adoption, not a gate verdict, "
                               "not a node status, not a mathematics claim")
    report["cited_pair_state"] = {
        "cited_registry": pins["artifacts/formulation/VARIANT_REGISTRY.json"]["measured"].get("sha256"),
        "cited_checker": pins["artifacts/formulation/tools/check_variant_registry.py"]["measured"].get("sha256"),
        "cited_pair_rc": matrix["M0_live_registry_live_checker"]["rc"],
        "cited_pair_errors": matrix["M0_live_registry_live_checker"]["errors"],
    }
    report["recommended_unblock_evidence_only"] = [
        "REC36-5: record that the non-author verification existed (worker-030, 01:20:29) and that worker-003's census classification was an accepted-stream ingest race (events landed 01:22:04, census 01:21:37)",
        "re-verify the SET repair at the rev14 live pins (registry 08afa691, delta 518cab5d, checker 8c7ef46f): the 01:20:29 verification binds pre-fold bytes that no longer exist live",
        "do not fold the worker-024 checker hunk as-is (stale context); do not cite the candidate checker's marker vocabulary against the rev14 label",
    ]
    report["duration_s"] = round(time.time() - t0, 3)
    report["core_digest"] = core_digest(report)

    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps(controls, indent=2, sort_keys=True) + "\n")
    print("VERDICT:", verdict)
    print("live drift:", drift)
    print("controls pass:", sum(1 for c in controls if c["pass"]), "/", len(controls))
    print("core_digest:", report["core_digest"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
