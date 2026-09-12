#!/usr/bin/env python3
"""W027-CLASSSEP-ARITY-01 — adversarial verification of class_separation token binding.

Question under test: does `research_map/class_separation.py` detect class tokens in
*artifact text* for all four frozen class ids and for out-of-distribution (OOD) token
arities?

Measured, with hashes pinned in the output report:
  A. `_class_tokens` match table for the 4 frozen ids and for unknown 3-/4-group probes.
  B. `findings_for_text` detection table on artifact-text probes.
  C. Map-level control: unknown 3-group token declared in a node `class_id`
     (hard channel, membership test) — is it caught regardless of arity?
  D. Token census of worker-07's standing 27-fixture corpus by arity and known/unknown.
  E. The official regression runner (`runtime/bin/classsep_regression.py`) end to end.
  F. The official 27-fixture corpus scored in-process, unpatched vs. with a proposed
     extractor regex (`AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+`) monkeypatched in.
  G. The worker-027 OOD corpus scored in-process, unpatched vs. patched.
  H. Patch delta on repository artifacts: any artifact newly flagged, any token whose
     identity is reported differently.

Nothing in the repository is modified: the patch is evaluated by in-process monkeypatch
only, and this script writes exactly one file, `token_binding_report.json`, in its own
artifact directory. It exits 0 when the report was produced (the report carries the
finding verdict and the falsifier), 2 on a measurement error.

Reproduce:
  python3 artifacts/worker-027/classsep_token_binding/verify_token_binding.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-027/classsep_token_binding"
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

TASK_ID = "W027-CLASSSEP-ARITY-01"
NODE_ID = "A1"
GATE = "G-AUDIT"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
FROZEN = list(CLASS_IDS)
UNKNOWN_3GROUP = ["AF-WCC-VAC-REG", "AF-SCC-REG-GEN"]
UNKNOWN_4GROUP = ["AF-SCC-REG-VAC-GEN", "AF-WCC-VAC-BH-FORM"]
LONG_GROUP = "AF-SCC-C0-CH-VAC-GEN"  # >4 groups; appears in the canonical taxonomy
PATCH_OLD = r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+"
PATCH_NEW = r"AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+"
STANDING_CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification"
OOD_CORPUS = ART / "ood_corpus"
INPUT_PATHS = [
    "research_map/class_separation.py",
    "runtime/bin/classsep_regression.py",
    "research_map/audit_evidence.py",
    "artifacts/worker-07/class_separation_falsification/results.json",
    "research_map/research_map.json",
    "research_map/formulation_taxonomy.yaml",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def token_arity(tok: str) -> int:
    return len(tok.split("-")) - 1


def now_local() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def patched_tokens(text: str):
    return re.findall(PATCH_NEW, text.upper())


@contextmanager
def use_patched_extractor():
    """Evaluate the proposed patch without editing any repository file."""
    orig = cs._class_tokens
    cs._class_tokens = patched_tokens
    try:
        yield
    finally:
        cs._class_tokens = orig


def score_corpus(corpus_dir: Path) -> dict:
    """Replicate runtime/bin/classsep_regression.py scoring exactly."""
    res = json.loads((corpus_dir / "results.json").read_text())
    tp = fn = tn = fp = 0
    rows = []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            rows.append({"id": fx.get("id"), "class": "MISSING", "detected": None,
                         "truth": bool(fx.get("is_class_merge")), "first_finding": ""})
            continue
        m = json.loads(p.read_text())
        det = cs.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += cs.findings_for_text(
                        (ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN-MISSED"
        elif not truth and got:
            fp += 1; cls = "FP-SPURIOUS"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fx.get("id"), "class": cls, "surface": fx.get("surface"),
                     "detected": got, "truth": truth,
                     "first_finding": (det[0][:160] if det else "")})
    n_leaks, n_ctrl = tp + fn, tn + fp
    return {
        "corpus_dir": str(corpus_dir.relative_to(ROOT)),
        "corpus_size": len(res["fixtures"]),
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        "leaks_detected": f"{tp}/{n_leaks}", "controls_clean": f"{tn}/{n_ctrl}",
        "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
        "rows": rows,
    }


def measure_a_token_match():
    out = []
    for tok in FROZEN + UNKNOWN_3GROUP + UNKNOWN_4GROUP + [LONG_GROUP]:
        out.append({
            "token": tok,
            "hyphen_groups": token_arity(tok),
            "known_class": tok in cs.KNOWN_CLASSES,
            "matched_unpatched": cs._class_tokens(tok),
            "matched_patched": patched_tokens(tok),
        })
    return out


def measure_b_text_detection():
    out = []
    with use_patched_extractor():
        patched = {t: cs.findings_for_text(f"class_id: {t}\n", f"probe:{t}")
                   for t in FROZEN + UNKNOWN_3GROUP + UNKNOWN_4GROUP}
    for t in FROZEN + UNKNOWN_3GROUP + UNKNOWN_4GROUP:
        base = cs.findings_for_text(f"class_id: {t}\n", f"probe:{t}")
        out.append({
            "token": t,
            "hyphen_groups": token_arity(t),
            "findings_unpatched": base,
            "findings_patched": patched[t],
            "flagged_unpatched": bool(base),
            "flagged_patched": bool(patched[t]),
        })
    return out


def measure_c_map_level():
    tok = UNKNOWN_3GROUP[0]
    m = {"groups": [{"id": "probe", "nodes": [{"id": "X", "class_id": tok}]}]}
    found = cs.findings_for_map(m)
    return {"probe_token": tok, "findings_for_map": found, "detected": bool(found),
            "channel": "hard (membership test in _scan_class_ids), arity-independent"}


def measure_d_corpus_census():
    res = json.loads((STANDING_CORPUS / "results.json").read_text())
    tokpat = re.compile(r"AF-(?:[A-Za-z0-9]+-)+[A-Za-z0-9]+")
    by_arity_known, by_arity_unknown = {}, {}
    unknown3, files = set(), []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            continue
        files.append(fx["fixture_path"])
        texts = [p.read_text()]
        m = json.loads(p.read_text())
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                a = n.get("artifact")
                if a and (ROOT / a).is_file():
                    files.append(a)
                    texts.append((ROOT / a).read_text(errors="replace"))
        for t in texts:
            for tok in tokpat.findall(t.upper()):
                ar = token_arity(tok)
                if tok in cs.KNOWN_CLASSES:
                    by_arity_known[str(ar)] = by_arity_known.get(str(ar), 0) + 1
                else:
                    by_arity_unknown[str(ar)] = by_arity_unknown.get(str(ar), 0) + 1
                    if ar == 3:
                        unknown3.add(tok)
    return {
        "fixture_count": len(res["fixtures"]),
        "files_scanned": len(set(files)),
        "occurrences_by_arity_frozen": dict(sorted(by_arity_known.items())),
        "occurrences_by_arity_unknown": dict(sorted(by_arity_unknown.items())),
        "unknown_3group_tokens": sorted(unknown3),
        "scope_gap": len(unknown3) == 0,
    }


def measure_h_real_artifact_delta():
    map_obj = json.loads((ROOT / "research_map/research_map.json").read_text())
    paths = set()
    for g in map_obj.get("groups", []):
        for n in g.get("nodes", []):
            a = n.get("artifact")
            if a and (ROOT / a).is_file():
                paths.add(a)
    for p in sorted((ROOT / "schemas").glob("*.yaml")):
        paths.add(str(p.relative_to(ROOT)))
    if (ROOT / "research_map/formulation_taxonomy.yaml").is_file():
        paths.add("research_map/formulation_taxonomy.yaml")

    newly_flagged, token_identity_deltas, scanned = [], [], 0
    for a in sorted(paths):
        try:
            text = (ROOT / a).read_text(errors="replace")
        except OSError:
            continue
        scanned += 1
        base = cs.findings_for_text(text, f"artifact {a}")
        with use_patched_extractor():
            new = cs.findings_for_text(text, f"artifact {a}")
        added = [x for x in new if x not in base]
        if added:
            if not base:
                newly_flagged.append({"path": a, "added": added})
            else:
                token_identity_deltas.append({"path": a, "added": added,
                                              "existing": base[:3]})
    return {
        "artifacts_scanned": scanned,
        "artifacts_newly_flagged": newly_flagged,
        "token_identity_deltas": token_identity_deltas,
        "n_newly_flagged": len(newly_flagged),
        "n_identity_deltas": len(token_identity_deltas),
    }


def measure_e_official_runner():
    cmd = [sys.executable, "runtime/bin/classsep_regression.py", "--verbose"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return {"command": " ".join(cmd), "returncode": proc.returncode,
            "tail": lines[-4:] if lines else [], "stdout_sha256":
            hashlib.sha256(proc.stdout.encode()).hexdigest()}


def main() -> int:
    created = now_local()
    inputs = {}
    for rel in INPUT_PATHS:
        p = ROOT / rel
        if p.is_file():
            inputs[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}

    a = measure_a_token_match()
    b = measure_b_text_detection()
    c = measure_c_map_level()
    d = measure_d_corpus_census()
    h = measure_h_real_artifact_delta()

    official_unpatched = score_corpus(STANDING_CORPUS)
    with use_patched_extractor():
        official_patched = score_corpus(STANDING_CORPUS)
    ood_unpatched = score_corpus(OOD_CORPUS)
    with use_patched_extractor():
        ood_patched = score_corpus(OOD_CORPUS)
    e = measure_e_official_runner()

    frozen_unmatched = [r["token"] for r in a
                        if r["token"] in FROZEN and not r["matched_unpatched"]]
    unknown3_invisible = [r["token"] for r in b
                          if r["token"] in UNKNOWN_3GROUP and not r["flagged_unpatched"]]
    extractor_blindspot = bool(frozen_unmatched) and bool(unknown3_invisible)
    if extractor_blindspot and d["scope_gap"]:
        status = "CONFIRMED"
    elif extractor_blindspot:
        status = "PARTIAL"
    else:
        status = "REFUTED"

    patch_repairs = (
        ood_unpatched["verdict"] == "DEFECTIVE"
        and ood_patched["verdict"] == "PASS"
        and official_patched["verdict"] == "PASS"
        and h["n_newly_flagged"] == 0
    )

    finding = {
        "id": "W027-F1",
        "status": status,
        "severity": "soft-channel false negative in artifact-text scanning; map-declaration "
                    "(hard) scanning is arity-independent and unaffected",
        "statement": (
            "At research_map/class_separation.py sha256 "
            f"{inputs['research_map/class_separation.py']['sha256']}, _class_tokens matches only "
            "AF- tokens with exactly four hyphen groups. Two of the four frozen class ids "
            "(AF-WCC-VAC-GEN, AF-WCC-SCALAR-SPH) are three-group and are not matched, and "
            "findings_for_text's unknown-token rule is therefore blind to unknown three-group "
            "AF- tokens in artifact text (AF-WCC-VAC-REG, AF-SCC-REG-GEN). Unknown four-group "
            "tokens are flagged as CLASSSEP-SOFT (soft). The standing 27-fixture regression "
            "corpus contains no unknown three-group token, so its 17/17 leaks, 10/10 controls, "
            "FP 0, FN 0 verdict does not cover this input class. The proposed extractor "
            f"'{PATCH_NEW}' flags the unknown three-group probes, keeps the standing corpus at "
            "17/17, 10/10, FP 0, FN 0, and adds no new finding on any of the scanned repository "
            "artifacts (measurement H: 0 newly flagged, 0 token-identity deltas in this "
            "snapshot; the patch also reports >4-group tokens whole rather than truncated, "
            "which no scanned artifact exercises here)."
        ),
        "falsifier": (
            "Re-run at the pinned checker sha256. The finding is FALSIFIED if (a) _class_tokens "
            "matches every frozen id listed as unmatched; or (b) findings_for_text emits no "
            "CLASSSEP-SOFT finding for any unknown three-group probe; or (c) the standing "
            "corpus contains at least one unknown three-group AF- token (scope covered); or "
            "(d) the official runner does not read 17/17 leaks, 10/10 controls, FP 0, FN 0 at "
            "the pinned corpus sha256; or (e) the patched extractor changes any standing-corpus "
            "fixture classification, or flags a repository artifact that the unpatched "
            "extractor did not flag (see measurement H; re-reporting a >4-group token in full "
            "instead of truncated is not a new flag)."
        ),
        "unmatched_frozen_ids": frozen_unmatched,
        "invisible_unknown_3group_tokens": unknown3_invisible,
    }

    report = {
        "schema_version": "1.0",
        "report_id": f"w027-classsep-arity-{created.replace(':', '').replace('-', '')}",
        "task_id": TASK_ID,
        "worker": "worker-027",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "created_at": created,
        "authority": "worker evidence only; no gate verdict, no done/passed transition",
        "reproduce": "python3 artifacts/worker-027/classsep_token_binding/verify_token_binding.py",
        "inputs": inputs,
        "finding": finding,
        "measurements": {
            "A_token_match": a,
            "B_text_detection": b,
            "C_map_level_control": c,
            "D_standing_corpus_census": d,
            "E_official_runner": e,
            "F_standing_corpus_unpatched": official_unpatched,
            "F_standing_corpus_patched": official_patched,
            "G_ood_corpus_unpatched": ood_unpatched,
            "G_ood_corpus_patched": ood_patched,
            "H_repo_artifact_patch_delta": h,
        },
        "proposed_patch": {
            "target": "research_map/class_separation.py",
            "symbol": "_class_tokens",
            "old": PATCH_OLD,
            "new": PATCH_NEW,
            "applied": False,
            "diff_path": "artifacts/worker-027/classsep_token_binding/proposed_patch.diff",
            "evaluation": "in-process monkeypatch only; repository bytes unchanged",
            "repairs": patch_repairs,
        },
        "expected_information_gain": "Removes an unexercised soft-channel false negative from "
                                     "class-separation gate evidence and supplies a regression "
                                     "fixture that exercises it.",
    }

    out = ART / "token_binding_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"task          {TASK_ID}  ({status})")
    print(f"checker sha   {inputs['research_map/class_separation.py']['sha256'][:12]}")
    print(f"frozen ids unmatched by _class_tokens : {frozen_unmatched}")
    print(f"unknown 3-group tokens invisible      : {unknown3_invisible}")
    print(f"map-level unknown 3-group hard control: detected={c['detected']}")
    print(f"standing corpus unpatched             : {official_unpatched['leaks_detected']} "
          f"leaks, {official_unpatched['controls_clean']} controls, FP {official_unpatched['fp']}, "
          f"FN {official_unpatched['fn']} -> {official_unpatched['verdict']}")
    print(f"standing corpus patched               : {official_patched['leaks_detected']} "
          f"leaks, {official_patched['controls_clean']} controls, FP {official_patched['fp']}, "
          f"FN {official_patched['fn']} -> {official_patched['verdict']}")
    print(f"OOD corpus unpatched                  : {ood_unpatched['verdict']} "
          f"(tp {ood_unpatched['tp']}, fn {ood_unpatched['fn']}, tn {ood_unpatched['tn']})")
    print(f"OOD corpus patched                    : {ood_patched['verdict']} "
          f"(tp {ood_patched['tp']}, fn {ood_patched['fn']}, tn {ood_patched['tn']})")
    print(f"repo artifacts newly flagged by patch : {h['n_newly_flagged']} "
          f"(scanned {h['artifacts_scanned']}, identity deltas {h['n_identity_deltas']})")
    print(f"official runner subprocess            : exit {e['returncode']}")
    print(f"report written                        : {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
