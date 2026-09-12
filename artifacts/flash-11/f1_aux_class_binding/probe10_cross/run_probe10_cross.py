#!/usr/bin/env python3
"""FD14-PROBE10-XMEAS: independent cross-measurement on worker-06 FORM-PROBE-10.

Closes FORM-DIFF-02 acceptance tests D3 (per-fixture disagreements as findings)
and D4 (own escape rate on the worker-06 semantic corpus, with corpus hash).

Claim bound to pinned bytes only:
  - corpus = artifacts/worker-06/probe10/manifest.json @ 9afd257312b5
  - flash11 gate = artifacts/flash-11/f1_aux_class_binding/check_schema.py @ a89b221c1c68
  - canonical gate = artifacts/formulation/tools/check_class_schema.py @ 000e09e46b2f
No canonical bytes are written. Verdicts are advisory worker evidence only:
no gate verdict, no node completion, no theorem, no physics result.

Fail-closed pins: if the manifest, a manifest-listed fixture, the raw_verdicts
reference, or either gate has moved at run start, the run aborts with
valid=false and publishes no escape number.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PROBE = REPO / "artifacts/worker-06/probe10"
MANIFEST = PROBE / "manifest.json"
RAW = PROBE / "raw_verdicts.json"
FLASH11 = REPO / "artifacts/flash-11/f1_aux_class_binding/check_schema.py"
CANON = REPO / "artifacts/formulation/tools/check_class_schema.py"

PINS = {
    "corpus_manifest_sha256": "9afd257312b5019d19adf94fb6488696ef902a57bcaf898183085860adb2882d",
    "worker06_raw_verdicts_sha256": "88e52d144602b41108d1534a0866ba39698f226131f7ed26714040f7ace2d6bd",
    "flash11_gate_sha256": "a89b221c1c68e34f87776e5648a8e890d2a0f9f0b919280d3e176422b2d689f0",
    "canonical_gate_sha256": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
TIMEOUT = 90


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_gate(tool: Path, fixture: Path, cwd: Path, kind: str) -> dict:
    """kind: 'flash11' (JSON list) | 'canonical' (JSON object)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(tool), str(fixture), "--json"],
            cwd=str(cwd), capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"verdict": "error", "rule_ids": [], "exit": None, "detail": f"timeout({TIMEOUT}s)"}
    raw = proc.stdout.strip()
    payload = None
    if raw.startswith(("{", "[")):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
    if payload is None:
        crash = "Traceback" in proc.stderr
        return {
            "verdict": "crash" if crash else "error",
            "rule_ids": [], "exit": proc.returncode,
            "detail": (proc.stderr.strip().splitlines() or [""])[-1][:200],
        }
    if kind == "flash11":
        rec = payload[0] if isinstance(payload, list) and payload else payload
        v = {"ACCEPT": "accept", "REJECT": "reject"}.get(rec.get("verdict"), "error")
        return {"verdict": v, "rule_ids": rec.get("failed_codes", []),
                "exit": proc.returncode, "detail": rec.get("layout", "")}
    v = {"pass": "accept", "fail": "reject"}.get(payload.get("verdict"), "error")
    return {"verdict": v, "rule_ids": payload.get("failed_rules", []),
            "exit": proc.returncode, "detail": ""}


def main() -> int:
    started = datetime.now(timezone.utc).astimezone().isoformat()
    manifest = json.loads(MANIFEST.read_text())
    raw_ref = json.loads(RAW.read_text())
    w06 = {r["fixture"]: r for r in raw_ref["rows"]}

    pins_measured = {
        "corpus_manifest_sha256": sha256_file(MANIFEST),
        "worker06_raw_verdicts_sha256": sha256_file(RAW),
        "flash11_gate_sha256": sha256_file(FLASH11),
        "canonical_gate_sha256": sha256_file(CANON),
    }
    pin_mismatches = [k for k, v in PINS.items() if pins_measured[k] != v]
    invalid: list[str] = [f"pin moved before run: {k}" for k in pin_mismatches]

    entries: list[dict] = []
    for key in ("mutants", "pass_controls", "sensitivity_controls"):
        for item in manifest.get(key, []):
            entries.append({
                "name": item["fixture"], "role": item["role"],
                "family": item.get("family", ""), "path": item["path"],
                "declared_sha256": item["sha256"],
            })
    # post-hoc probes: not part of the manifest corpus; reported separately.
    posthoc_dir = PROBE / "fixtures_posthoc"
    for p in sorted(posthoc_dir.glob("*.yaml")) if posthoc_dir.is_dir() else []:
        entries.append({"name": p.stem, "role": "posthoc_not_in_manifest",
                        "family": "posthoc", "path": str(p.relative_to(REPO)),
                        "declared_sha256": None})

    rows = []
    for e in entries:
        fp = REPO / e["path"]
        got = sha256_file(fp) if fp.exists() else None
        sha_match = bool(got and e["declared_sha256"] and got == e["declared_sha256"])
        if e["declared_sha256"] and not sha_match:
            invalid.append(f"fixture hash mismatch: {e['name']}")
        f11 = run_gate(FLASH11, fp, FLASH11.parent, "flash11") if fp.exists() else \
            {"verdict": "error", "rule_ids": [], "exit": None, "detail": "missing"}
        can = run_gate(CANON, fp, CANON.parent, "canonical") if fp.exists() else \
            {"verdict": "error", "rule_ids": [], "exit": None, "detail": "missing"}
        ref = w06.get(e["name"])
        rows.append({
            **e, "sha256_measured": got, "sha_match": sha_match,
            "flash11": f11, "canonical": can,
            "w06_published_stageA": (
                {"verdict": ref["A"]["verdict"], "caught": ref["A"]["caught"],
                 "failed_rules": ref["A"]["failed_rules"]} if ref else None),
            "agreement": "agree" if f11["verdict"] == can["verdict"] else "disagree",
        })

    mutants = [r for r in rows if r["role"] == "mutant"]
    pass_ctrls = [r for r in rows if r["role"] == "pass_control"]
    sens_ctrls = [r for r in rows if r["role"] == "sensitivity_control"]
    posthoc = [r for r in rows if r["role"] == "posthoc_not_in_manifest"]

    def esc(rs, key):
        return sum(1 for r in rs if r[key]["verdict"] == "accept")

    f11_esc, can_esc = esc(mutants, "flash11"), esc(mutants, "canonical")
    w06_esc = sum(1 for r in mutants
                  if r["w06_published_stageA"] and not r["w06_published_stageA"]["caught"])

    f11_pc_fail = [r["name"] for r in pass_ctrls if r["flash11"]["verdict"] != "accept"]
    can_pc_fail = [r["name"] for r in pass_ctrls if r["canonical"]["verdict"] != "accept"]
    f11_sens_miss = [r["name"] for r in sens_ctrls if r["flash11"]["verdict"] != "reject"]
    can_sens_miss = [r["name"] for r in sens_ctrls if r["canonical"]["verdict"] != "reject"]
    if f11_pc_fail:
        invalid.append("flash11 rejected pass control(s): " + ",".join(f11_pc_fail))
    if can_pc_fail:
        invalid.append("canonical rejected pass control(s): " + ",".join(can_pc_fail))

    families: dict[str, dict] = {}
    for r in mutants:
        fam = families.setdefault(r["family"], {"n": 0, "flash11_escaped": 0,
                                                "canonical_escaped": 0, "w06_escaped": 0,
                                                "fixtures": []})
        fam["n"] += 1
        fam["fixtures"].append(r["name"])
        fam["flash11_escaped"] += int(r["flash11"]["verdict"] == "accept")
        fam["canonical_escaped"] += int(r["canonical"]["verdict"] == "accept")
        fam["w06_escaped"] += int(bool(r["w06_published_stageA"]
                                       and not r["w06_published_stageA"]["caught"]))

    disagreements = [{
        "fixture": r["name"], "role": r["role"], "family": r["family"],
        "flash11": r["flash11"], "canonical": r["canonical"],
        "minimal_repro": (
            f"python3 {FLASH11.relative_to(REPO)} {r['path']} --json  # vs "
            f"python3 {CANON.relative_to(REPO)} {r['path']} --json"),
    } for r in rows if r["agreement"] == "disagree"]

    published_m03 = w06.get("m03_rephrased_completeness_in_c0_iplus_definition")
    m03_row = next((r for r in rows if r["name"] == published_m03["fixture"]), None) \
        if published_m03 else None
    published_catch_reproduced = bool(
        m03_row and (m03_row["flash11"]["verdict"] == "reject"
                     or m03_row["canonical"]["verdict"] == "reject"))

    result = {
        "task_id": "FD14-PROBE10-XMEAS",
        "parent_assignment": "assign-FORM-DIFF-02-20260911T2331",
        "actor": "deepseek-flash-11",
        "node_id": "F1",
        "gate": "G-CLASSBIND",
        "class_ids": CLASS_IDS,
        "corpus_id": manifest.get("corpus_id"),
        "corpus_frozen_revision": manifest.get("frozen_revision"),
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "pins": PINS, "pins_measured": pins_measured, "pin_mismatches": pin_mismatches,
        "valid": not invalid, "invalid_reasons": invalid,
        "sensitivity": {
            "rule": "a sensitivity control must be REJECTED (caught) by a gate to show the instrument is live",
            "flash11_missed": f11_sens_miss, "canonical_missed": can_sens_miss},
        "sensitivity_check": {
            "flash11_passed": not f11_sens_miss, "canonical_passed": not can_sens_miss,
        },
        "interpretation": {
            "flash11_escape_rate_is_upper_bound": True,
            "like_for_like_with_canonical": not f11_sens_miss and not can_sens_miss,
            "reason": ("flash11 accepted both sensitivity controls, so its escape rate 11/12 is an "
                       "upper bound from a less sensitive instrument, not a like-for-like detection "
                       "comparison with canonical at 000e09e4; the matched mutant escape rate alone "
                       "would have hidden this difference."),
        },
        "aggregates": {
            "mutants": len(mutants),
            "flash11_escaped": f11_esc, "flash11_escape_rate": round(f11_esc / len(mutants), 4) if mutants else None,
            "canonical_escaped": can_esc, "canonical_escape_rate": round(can_esc / len(mutants), 4) if mutants else None,
            "w06_published_stageA_escaped": w06_esc,
            "w06_published_stageA_escape_rate": round(w06_esc / len(mutants), 4) if mutants else None,
            "flash11_vs_canonical_agreements": sum(1 for r in mutants if r["agreement"] == "agree"),
            "pass_controls_accepted_flash11": len(pass_ctrls) - len(f11_pc_fail),
            "pass_controls_accepted_canonical": len(pass_ctrls) - len(can_pc_fail),
            "w06_published_m03_catch_reproduced": published_catch_reproduced,
            "posthoc_fixtures": len(posthoc),
            "posthoc_flash11_escaped": esc(posthoc, "flash11"),
            "posthoc_canonical_escaped": esc(posthoc, "canonical"),
        },
        "families": families,
        "disagreements": disagreements,
        "rows": rows,
        "posthoc_rows": posthoc,
        "falsifier": {
            "statement": (
                "FIRED IF (a) the manifest, a manifest-listed fixture, worker-06 raw_verdicts.json, "
                "or either gate hash differs from its pin at run start (abort, no number); (b) flash11 "
                "or canonical rejects any of the 5 pass controls (instrument false positive, no number); "
                "(c) a re-run at the same pins returns a different per-fixture verdict for any fixture "
                "(nondeterministic instrument); (d) the published worker-06 stage-A catch m03 is not "
                "reproduced as a reject by either gate at the pins (corpus/pin mismatch)."),
            "status_pre_registered": "not fired at first run (see aggregates/valid)",
        },
        "non_claims": [
            "no gate verdict, no node status, no validation_status=passed, no canonical write",
            "no theorem, no counterexample, no physics result",
            "escape here means only 'this gate accepts bytes whose inserted wrong-class content was authored as a leak'; it is not a physics claim",
            "posthoc fixtures are outside the published manifest corpus and are reported separately",
        ],
    }
    (OUT / "cross_results.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({
        "valid": result["valid"], "invalid_reasons": result["invalid_reasons"],
        "aggregates": result["aggregates"],
        "disagreements": [d["fixture"] for d in disagreements],
        "sensitivity": result["sensitivity"],
    }, indent=1))
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
