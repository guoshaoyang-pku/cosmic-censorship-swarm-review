#!/usr/bin/env python3
"""Independent verifier for W075-F2B-DEFECT-RECONCILIATION-09.

Different extraction path from the instrument: raw line scanning and direct
subprocess checks rather than the instrument's YAML helpers. Re-hashes every
pinned input, re-derives the four verdicts, re-checks the D3 instrument-coverage
claim and the repair dry-run, and fails closed on any mismatch.

Writes verification.json next to this file and exits 0 only if all checks pass.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REP = json.loads((OUT / "reconciliation.json").read_text())

F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CHECKER = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CAND = OUT / "candidate"

checks = []


def add(cid, ok, detail):
    checks.append({"id": cid, "pass": bool(ok), "detail": str(detail)[:400]})


# C1: every pinned input still re-hashes to the recorded value
bad = []
for rel, h in REP["pins"].items():
    p = ROOT / rel
    got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if got != h:
        bad.append({"path": rel, "recorded": h, "measured": got})
add("V1_pin_stability", not bad, bad or f"{len(REP['pins'])} pins stable")

# C2: D1 re-derived from raw lines (different path than the instrument's YAML access)
lines = F2B.read_text().splitlines()
reason_line = next((ln for ln in lines if "strictly larger extension class" in ln), None)
chain_line = next((ln for ln in lines if "extension_class_containment" in ln), None)
d1_ok = bool(reason_line) and bool(chain_line) and "contains E_C2" in chain_line
add("V2_D1_reason_inversion", d1_ok,
    {"reason_line": reason_line, "chain_line": chain_line})

# C3: D2 re-derived from raw lines
denial_line = next((ln for ln in lines if re.search(r"no containment with C2 or C0 is asserted", ln, re.I)), None)
mnc_idx = next((i for i, ln in enumerate(lines) if "must_not_conflate" in ln), None)
denial_in_mnc = denial_line is not None and mnc_idx is not None and lines.index(denial_line) > mnc_idx
add("V3_D2_denial", bool(denial_line) and denial_in_mnc,
    {"denial_line": denial_line, "in_must_not_conflate": denial_in_mnc})

# C4: D3 - operational checker accepts canonical F2b, rejects the F0-token variant
r = subprocess.run([sys.executable, str(CHECKER), str(F2B), "--json"], capture_output=True, text=True, cwd=str(ROOT))
canon = json.loads(r.stdout[r.stdout.index("{"):])
mut = CAND / "control_f0token__af_scc_c0_vacuum.yaml"
r2 = subprocess.run([sys.executable, str(CHECKER), str(mut), "--json"], capture_output=True, text=True, cwd=str(ROOT))
mutd = json.loads(r2.stdout[r2.stdout.index("{"):])
f0 = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
allowed = f0["field_vocabulary"]["conclusion_type"]["allowed"]
f2b_tok = yaml.safe_load(F2B.read_text())["conclusion"]["conclusion_type"]
coverage_ok = (canon.get("verdict") == "pass" and mutd.get("verdict") == "fail"
               and "R11" in mutd.get("failed_rules", []) and f2b_tok not in allowed
               and any("strong_cosmic_censorship_C0" == a for a in allowed))
add("V4_D3_instrument_coverage", coverage_ok,
    {"canonical": canon.get("verdict"), "f0_token_variant": mutd.get("verdict"),
     "variant_failed_rules": mutd.get("failed_rules"), "f2b_token": f2b_tok, "f0_allowed": allowed})

# C5: D4 - corpus base differs from live C0 and the frozen preflight returns False
corpus = json.loads((ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
live = hashlib.sha256(F2B.read_bytes()).hexdigest()
pf = REP["defects"][3]["frozen_preflight"]
add("V5_D4_stale_corpus", corpus["base_sha256"] != live and pf["returns"] is False
    and "PREFLIGHT FAIL" in pf["stdout"],
    {"corpus_base": corpus["base_sha256"], "live": live, "preflight_returns": pf["returns"]})

# C6: repair dry-run - file hash matches, D1/D2 do not fire there, checker passes
dry = REP["proposed_repair"]["dryrun"]
rp = ROOT / dry["path"]
got = hashlib.sha256(rp.read_bytes()).hexdigest()
rl = rp.read_text()
d1_after = bool(re.search(r"strictly larger extension class", rl))
d2_after = bool(re.search(r"no containment with C2 or C0 is asserted", rl, re.I))
rr = subprocess.run([sys.executable, str(CHECKER), str(rp), "--json"], capture_output=True, text=True, cwd=str(ROOT))
rd = json.loads(rr.stdout[rr.stdout.index("{"):])
add("V6_repair_dryrun", got == dry["sha256"] and not d1_after and not d2_after and rd.get("verdict") == "pass",
    {"hash_matches": got == dry["sha256"], "d1_after": d1_after, "d2_after": d2_after,
     "checker": rd.get("verdict")})

# C7: controls all committed and passing
add("V7_controls", REP.get("controls_pass") is True and len(REP.get("controls", [])) == 8
    and all(c.get("pass") for c in REP.get("controls", [])),
    [{"id": c["id"], "pass": c["pass"]} for c in REP.get("controls", [])])

# C8: the erratum is recorded and the original review event is untouched
erratum = REP["cross_ledger_reconciliation"]["w075_self_erratum"]
myout = (ROOT / "comms/outbox/worker-075.jsonl").read_text()
review_still_present = '"event_id": "w075-20260912T0103-review-f2b"' in myout
add("V8_erratum_recorded", bool(erratum.get("gap")) and review_still_present,
    {"erratum": erratum.get("gap"), "original_review_event_present": review_still_present})

verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
out = {
    "schema": "w075-f2b-defect-reconciliation-verification/v1",
    "verifier": "verify_f2b_reconciliation_075.py",
    "task_id": REP["task_id"],
    "actor": "worker-075",
    "verified_report": "artifacts/worker-075/f2b_defect_reconciliation/reconciliation.json",
    "verified_report_sha256": hashlib.sha256((OUT / "reconciliation.json").read_bytes()).hexdigest(),
    "checks": checks,
    "verdict": verdict,
    "authority": "independent worker-side verification of a worker-side measurement; no gate verdict, no canonical write",
}
(OUT / "verification.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({"verdict": verdict, "checks": [{"id": c["id"], "pass": c["pass"]} for c in checks]}, indent=1))
raise SystemExit(0 if verdict == "PASS" else 1)
