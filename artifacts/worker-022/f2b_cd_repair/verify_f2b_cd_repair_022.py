#!/usr/bin/env python3
"""W022-F2B-CD-REPAIR-CAND-01 verifier (worker-022, class AF-SCC-C0-VAC-GEN, gate G-FORM).

Deterministic, fail-closed, read-only on canonical paths. It:
  1. re-measures the preregistration pins (entry + exit);
  2. emits the minimal repair candidate for worker-008's CD-01/CD-02 by exact
     single-occurrence text replacement (fail-closed if a pattern is not unique);
  3. runs independent detectors for CD-01 and CD-02 (not importing worker-008's checker);
  4. runs C1-C10 and adversarial controls M1-M6 from preregistration.json;
  5. writes candidate/, report.json and CHECKPOINT.json.

Exit codes: 0 = REPAIR_READY, 1 = REPAIR_FAILED, 2 = PIN_VOID / measurement error.
Usage: python3 verify_f2b_cd_repair_022.py [--emit]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANON = REPO / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = REPO / "artifacts" / "formulation" / "FROZEN.json"
GATE = REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
PINNED = HERE / "pinned" / "af_scc_c0_vacuum.b2ab6acb2bbe.yaml"
FROZEN_PINNED = HERE / "pinned" / "FROZEN.rev29.json"
CAND_DIR = HERE / "candidate"
CAND = CAND_DIR / "af_scc_c0_vacuum.repair-candidate.yaml"
PREREG = HERE / "preregistration_rev13_addendum2.json"
REPORT = HERE / "report.json"
CHECKPOINT = HERE / "CHECKPOINT.json"

F2B_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
F2B_SHA_REV12_SUPERSEDED = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
FROZEN_SHA = "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833"

# Exact, single-occurrence replacement patterns (fail-closed).
CD01_FROM = 'reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"'
CD01_TO = 'reason: "C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker"'
CD02_FROM = "No containment with C2 or C0 is asserted here;"
CD02_TO = ("Its extension class sits strictly between the C0 endpoint class and the C2 endpoint class, "
           "exactly as declared in implication_ledger.extension_class_containment "
           "(E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2); "
           "no metric-differentiability containment is asserted;")

CHAIN_TOKENS = ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
DENIAL_RE = re.compile(r"no\s+containment\s+with\s+(?:C2|C0)", re.IGNORECASE)
LARGER_RE = re.compile(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class", re.IGNORECASE)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


class DupKeyError(ValueError):
    pass


def _no_dup_loader():
    import yaml

    class L(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        mapping = {}
        for k, v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in mapping:
                raise DupKeyError(f"duplicate key {key!r}")
            mapping[key] = loader.construct_object(v, deep=deep)
        return mapping

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    return L


def load_yaml_strict(text: str) -> dict:
    import yaml

    return yaml.load(text, Loader=_no_dup_loader())


def apply_repairs(text: str) -> tuple[str, dict]:
    """Apply the two preregistered single-line repairs. Fail-closed on ambiguity."""
    out = text
    meta = {}
    for name, old, new in (("REP-CD-01", CD01_FROM, CD01_TO), ("REP-CD-02", CD02_FROM, CD02_TO)):
        n = out.count(old)
        if n != 1:
            raise SystemExit(f"[fail-closed] {name}: expected 1 occurrence of pattern, found {n}")
        out = out.replace(old, new, 1)
        meta[name] = {"occurrences": n, "old_len": len(old), "new_len": len(new)}
    return out, meta


def chain_ok(doc: dict) -> tuple[bool, str]:
    try:
        chain = doc["implication_ledger"]["extension_class_containment"]
    except Exception as e:  # noqa: BLE001
        return False, f"chain unreadable: {e}"
    pos = -1
    for tok in CHAIN_TOKENS:
        i = chain.find(tok)
        if i < 0:
            return False, f"chain token {tok!r} absent"
        if i <= pos:
            return False, f"chain token {tok!r} out of order"
        pos = i
    return True, chain


def detect_cd01(doc: dict) -> tuple[bool, str]:
    """Independent CD-01 detector: forbidden C2->this-class transfer whose reason
    asserts C2 is a strictly LARGER extension class while the doc's own chain says smaller."""
    rows = (doc.get("implication_ledger") or {}).get("forbidden_transfers") or []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("from", "")).strip() == "no proper future C2 extension" and \
           str(r.get("to", "")).strip() == "this class":
            reason = str(r.get("reason", ""))
            if LARGER_RE.search(reason):
                return True, f"size-premise inversion in forbidden_transfers reason: {reason!r}"
    return False, "no C2-larger premise found in the forbidden C2->this-class transfer"


def detect_cd02(doc: dict) -> tuple[bool, str]:
    """Independent CD-02 detector: a must_not_conflate bullet denies C0/C2 containment
    while the same document declares the containment chain."""
    ok, chain = chain_ok(doc)
    bullets = (doc.get("regularity") or {}).get("must_not_conflate") or []
    for b in bullets:
        if isinstance(b, str) and DENIAL_RE.search(b):
            if ok:
                return True, f"containment denial in must_not_conflate while chain declared: {b[:120]!r}"
            return False, "denial present but no chain declared in the same document"
    return False, "no containment denial found in must_not_conflate"


def deep_diff(a, b, path=""):
    """Return list of differing paths between two parsed YAML structures."""
    out = []
    if type(a) is not type(b):
        return [path or "<root>"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}" if path else str(k))
            else:
                out.extend(deep_diff(a[k], b[k], f"{path}.{k}" if path else str(k)))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}[len]")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out.extend(deep_diff(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append(path)
    return out


def diff_lines(canon_text: str, cand_text: str):
    a, b = canon_text.splitlines(), cand_text.splitlines()
    if len(a) != len(b):
        return None
    return [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]


def run_gate(path: Path):
    p = subprocess.run([sys.executable, str(GATE), "--json", str(path)],
                       cwd=str(REPO), capture_output=True, text=True, timeout=180)
    parsed = None
    txt = (p.stdout or "").strip()
    for chunk in ([txt] if txt else []):
        try:
            parsed = json.loads(chunk)
        except Exception:  # noqa: BLE001
            parsed = None
    verdict = None
    if isinstance(parsed, dict):
        verdict = parsed.get("verdict") or parsed.get("status")
    return {"exit_code": p.returncode, "verdict": verdict,
            "stdout_tail": txt[-800:], "stderr_tail": (p.stderr or "")[-400:],
            "json_parsed": parsed is not None}


def class_sep_findings(text: str):
    sys.path.insert(0, str(REPO / "research_map"))
    import class_separation  # noqa: E402

    return class_separation.findings_for_text(text, "w022-f2b-cd-repair-candidate")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write candidate/ (always on in this run)")
    ap.parse_args()

    started = datetime.now(CST).isoformat(timespec="seconds")
    checks: dict[str, dict] = {}
    controls: dict[str, dict] = {}
    errors: list[str] = []

    prereg = json.loads(PREREG.read_text())
    pins = prereg["pins"]

    def check(cid: str, ok: bool, detail: str):
        checks[cid] = {"pass": bool(ok), "detail": detail}
        if not ok:
            errors.append(f"{cid}: {detail}")
        return ok

    # C1 entry: canonical + pinned copies; FROZEN rev28 unchanged and still pinning the superseded rev12 hash
    canon_bytes = CANON.read_bytes()
    canon_text = canon_bytes.decode("utf-8")
    c1_entry = sha256_bytes(canon_bytes) == F2B_SHA and sha256_file(PINNED) == F2B_SHA
    frozen_entry = sha256_file(FROZEN) == FROZEN_SHA == sha256_file(FROZEN_PINNED)
    frozen_doc = json.loads(FROZEN.read_text())
    frozen_f2b = (frozen_doc.get("files") or {}).get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
    check("C1", c1_entry and frozen_entry and frozen_f2b == F2B_SHA,
          f"canonical={sha256_bytes(canon_bytes)[:12]} pinned={sha256_file(PINNED)[:12]} "
          f"frozen={sha256_file(FROZEN)[:12]} frozen_pin_f2b={str(frozen_f2b)[:12]} "
          f"(frozen_pin_matches_live={frozen_f2b == sha256_bytes(canon_bytes)})")

    # emit candidate
    cand_text, repair_meta = apply_repairs(canon_text)
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    CAND.write_text(cand_text)
    cand_sha = sha256_bytes(cand_text.encode("utf-8"))

    # C2: exactly two changed lines, and they are exactly the two target lines
    dl = diff_lines(canon_text, cand_text)
    canon_doc = load_yaml_strict(canon_text)
    cand_doc = load_yaml_strict(cand_text)
    keys_ok = set(canon_doc) == set(cand_doc)
    src_lines = canon_text.splitlines()
    cd01_line = next((i + 1 for i, ln in enumerate(src_lines) if CD01_FROM in ln), None)
    cd02_line = next((i + 1 for i, ln in enumerate(src_lines) if CD02_FROM in ln), None)
    check("C2", dl is not None and len(dl) == 2 and sorted(dl) == sorted([x for x in (cd01_line, cd02_line) if x]) and keys_ok,
          f"changed_lines={dl} cd01_line={cd01_line} cd02_line={cd02_line} top_level_keys_identical={keys_ok} candidate_sha256={cand_sha[:12]}")

    # C3/C4 independent detectors
    cd01_canon = detect_cd01(canon_doc)
    cd01_cand = detect_cd01(cand_doc)
    cd02_canon = detect_cd02(canon_doc)
    cd02_cand = detect_cd02(cand_doc)
    check("C3", cd01_canon[0] and not cd01_cand[0],
          f"canonical_fires={cd01_canon[0]} ({cd01_canon[1][:90]}) candidate_fires={cd01_cand[0]}")
    check("C4", cd02_canon[0] and not cd02_cand[0],
          f"canonical_fires={cd02_canon[0]} ({cd02_canon[1][:90]}) candidate_fires={cd02_cand[0]}")

    # C5 chain + consistency of repair
    ok_chain, chain_txt = chain_ok(cand_doc)
    rep_reason = cand_doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    rep_bullet = cand_doc["regularity"]["must_not_conflate"][0]
    c5 = ok_chain and "strictly smaller" in rep_reason and \
        "strictly between the C0 endpoint class and the C2 endpoint class" in rep_bullet \
        and not DENIAL_RE.search(rep_bullet)
    check("C5", c5, f"chain_ok={ok_chain} repaired_reason_smaller={'strictly smaller' in rep_reason} "
                    f"repaired_bullet_consistent={'strictly between the C0 endpoint class and the C2 endpoint class' in rep_bullet}")

    # C6 structural gate on candidate
    gate = run_gate(CAND)
    check("C6", gate["exit_code"] == 0 and (gate["verdict"] in ("pass", "PASS", None)) and gate["json_parsed"],
          f"exit={gate['exit_code']} verdict={gate['verdict']} json_parsed={gate['json_parsed']}")

    # C7 class separation
    cs = class_sep_findings(cand_text)
    check("C7", len(cs) == 0, f"class_separation_findings={len(cs)}")

    # C8 no other semantic differences
    dd = deep_diff(canon_doc, cand_doc)
    allowed = {"implication_ledger.forbidden_transfers[0].reason", "regularity.must_not_conflate[0]"}
    check("C8", set(dd) == allowed, f"deep_diff_paths={dd}")

    # C9 exit pins
    check("C9", sha256_file(CANON) == F2B_SHA and sha256_file(FROZEN) == FROZEN_SHA,
          f"canonical_exit={sha256_file(CANON)[:12]} frozen_exit={sha256_file(FROZEN)[:12]}")

    # C10 determinism
    cand2, _ = apply_repairs(canon_text)
    check("C10", sha256_bytes(cand2.encode("utf-8")) == cand_sha, f"re-emit_sha256={sha256_bytes(cand2.encode('utf-8'))[:12]}")

    # ---- controls M1-M6 (in memory; no canonical writes) ----
    m1 = cand_text.replace(CD01_TO, CD01_FROM, 1)
    controls["M1"] = {"pass": detect_cd01(load_yaml_strict(m1))[0], "detail": "revert REP-CD-01 -> CD-01 fires"}
    m2 = cand_text.replace(CD02_TO, CD02_FROM, 1)
    controls["M2"] = {"pass": detect_cd02(load_yaml_strict(m2))[0], "detail": "revert REP-CD-02 -> CD-02 fires"}
    m3 = cand_text.replace("C2 is a strictly smaller extension class",
                           "C2 is a strictly larger extension class", 1)
    controls["M3"] = {"pass": detect_cd01(load_yaml_strict(m3))[0], "detail": "mutate smaller->larger -> CD-01 fires"}
    chain_lines = [ln for ln in cand_text.splitlines() if ln.strip().startswith("extension_class_containment:")]
    if len(chain_lines) != 1:
        errors.append(f"M4 setup: expected 1 extension_class_containment line, found {len(chain_lines)}")
    chain_line = chain_lines[0]
    m4 = cand_text.replace(chain_line, chain_line.replace("E_C0 contains E_H2loc", "E_H2loc contains E_C0", 1), 1)
    controls["M4"] = {"pass": not chain_ok(load_yaml_strict(m4))[0], "detail": "mutate chain to false direction -> C5 chain check fails"}
    controls["M5"] = {"pass": not detect_cd01(cand_doc)[0] and not detect_cd02(cand_doc)[0],
                      "detail": "pristine candidate -> no false positive"}
    m6 = canon_text + "\n# whitespace-only perturbation\n"
    controls["M6"] = {"pass": detect_cd01(load_yaml_strict(m6))[0] and detect_cd02(load_yaml_strict(m6))[0],
                      "detail": "canonical + whitespace perturbation -> both detectors still fire"}

    for mid, rec in controls.items():
        if not rec["pass"]:
            errors.append(f"control {mid} failed")

    verdict = "REPAIR_READY" if not errors else "REPAIR_FAILED"
    if not c1_entry or not checks["C9"]["pass"]:
        verdict = "PIN_VOID"

    report = {
        "task_id": "W022-F2B-CD-REPAIR-CAND-01",
        "worker": "worker-022",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "started_at": started,
        "finished_at": datetime.now(CST).isoformat(timespec="seconds"),
        "verdict": verdict,
        "pins": pins,
        "pins_measured": {
            "schemas/af_scc_c0_vacuum.yaml": sha256_file(CANON),
            "artifacts/formulation/FROZEN.json": sha256_file(FROZEN),
            "artifacts/worker-008/containment_direction/evidence/report.json":
                sha256_file(REPO / "artifacts/worker-008/containment_direction/evidence/report.json"),
            "artifacts/formulation/tools/check_class_schema.py": sha256_file(GATE),
            "research_map/class_separation.py": sha256_file(REPO / "research_map/class_separation.py"),
        },
        "pin_move_record": {
            "superseded_rev12_pin": F2B_SHA_REV12_SUPERSEDED,
            "first_run_result": "PIN_VOID",
            "first_run_report": "artifacts/worker-022/f2b_cd_repair/report.rev12-pinvoid.json",
            "reason": "canonical moved 55d0a1ea -> b2ab6acb at 2026-09-12T00:53:20 (rev13 binding refresh by the owner); task re-pinned per the preregistered falsifier clause (a)",
            "frozen_state_at_emit": "FROZEN rev28 still pins the rev12 hash for F2b; re-frozen by the owner as rev29 3d9e3d77 at 00:55:02 (observed during this run); second addendum records the re-pin"
        },
        "repair_meta": repair_meta,
        "candidate": {"path": str(CAND.relative_to(REPO)), "sha256": cand_sha,
                      "changed_lines": dl, "non_canonical": True},
        "checks": checks,
        "controls": controls,
        "cd01_canonical": {"fires": cd01_canon[0], "detail": cd01_canon[1]},
        "cd02_canonical": {"fires": cd02_canon[0], "detail": cd02_canon[1]},
        "gate": gate,
        "class_separation_findings": cs,
        "errors": errors,
        "out_of_scope_remaining_blockers": [
            "f0_binding.consistency_evidence_sha256=675a99d0 stale pin in F1/F2a/F2b (separate pin-repair track)"
        ],
        "falsifier": prereg["falsifier"],
        "authority_note": prereg["authority_note"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    chk = {
        "worker": "worker-022", "checkpoint": 4,
        "at": report["finished_at"], "task_id": report["task_id"],
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "verdict": verdict, "changed_lines": dl,
        "artifact_hashes": {
            "artifacts/worker-022/f2b_cd_repair/preregistration.json": sha256_file(HERE / "preregistration.json"),
            "artifacts/worker-022/f2b_cd_repair/preregistration_rev13_addendum.json": sha256_file(HERE / "preregistration_rev13_addendum.json"),
            "artifacts/worker-022/f2b_cd_repair/preregistration_rev13_addendum2.json": sha256_file(PREREG),
            "artifacts/worker-022/f2b_cd_repair/verify_f2b_cd_repair_022.py": sha256_file(Path(__file__)),
            "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml": cand_sha,
            "artifacts/worker-022/f2b_cd_repair/report.json": sha256_file(REPORT),
            "artifacts/worker-022/f2b_cd_repair/report.rev12-pinvoid.json": sha256_file(HERE / "report.rev12-pinvoid.json"),
            "artifacts/worker-022/f2b_cd_repair/README.md": sha256_file(HERE / "README.md"),
        },
        "pins": {"f2b_canonical_rev13": F2B_SHA, "f2b_rev12_superseded": F2B_SHA_REV12_SUPERSEDED,
                 "frozen_rev29": FROZEN_SHA},
        "next_falsifier": prereg["falsifier"],
    }
    CHECKPOINT.write_text(json.dumps(chk, indent=2) + "\n")

    print(json.dumps({"verdict": verdict, "candidate_sha256": cand_sha, "changed_lines": dl,
                      "checks": {k: v["pass"] for k, v in checks.items()},
                      "controls": {k: v["pass"] for k, v in controls.items()},
                      "errors": errors}, indent=2))
    return 0 if verdict == "REPAIR_READY" else (2 if verdict == "PIN_VOID" else 1)


if __name__ == "__main__":
    sys.exit(main())
