#!/usr/bin/env python3
"""Independent formulation-lead re-verification of the FROZEN rev28 freeze-hold state.

Run from the swarm root:
    python3 artifacts/formulation/tools/verify_freeze_hold_findings.py

Re-measures, from disk only, everything the lead lifecycle asserted, and re-tests the two
findings it reports. Nothing is written to any frozen path; the evidence record is written
to artifacts/formulation/evidence/lead_freeze_hold_independent_verify.json.

Findings under test
-------------------
L-FORM-01 (F2b, content): schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda,
  implication_ledger.forbidden_transfers[0].reason calls C2 "a strictly larger extension
  class". The same file's implication_ledger.extension_class_containment states
  "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2". C2 is therefore the SMALLER
  extension class; the premise is inverted. The row's conclusion ("C2-inextendibility is
  strictly weaker") is correct, so this is a justification defect, not a class merge.

L-FORM-02 (F1/F2a/F2b, binding hygiene): all three class schemas declare
  f0_binding.consistency_evidence_sha256 = 675a99d0d25b..., which resolves to no file on
  disk, while the named evidence file artifacts/formulation/evidence/taxonomy_consistency.json
  measures 9e335e9ba1bf... and is pinned at that hash by FROZEN rev28.

Exit codes
----------
0  all recorded findings reproduced (state unchanged since the record was written)
10 one or more findings no longer reproduce (repaired, or the record is falsified)
1  measurement error
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
RECORD = ROOT / "artifacts" / "formulation" / "evidence" / "lead_freeze_hold_independent_verify.json"

CANONICAL = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}
SCHEMAS = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
DEAD_DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
ANCHOR = "schemas/af_scc_c0_vacuum.yaml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line_of(text: str, needle: str) -> int | None:
    for i, l in enumerate(text.splitlines(), 1):
        if needle in l:
            return i
    return None


def main() -> int:
    checks: list[dict] = []
    problems: list[str] = []

    def check(cid: str, ok: bool, detail: str, **extra) -> None:
        checks.append({"check": cid, "ok": bool(ok), "detail": detail, **extra})
        if not ok:
            problems.append(f"{cid}: {detail}")

    # --- 1. five held canonical paths vs pinned hashes -------------------------------
    measured = {}
    for rel, want in CANONICAL.items():
        p = ROOT / rel
        if not p.exists():
            check(f"held:{rel}", False, "missing on disk")
            continue
        got = sha256(p)
        measured[rel] = {"sha256": got, "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")}
        check(f"held:{rel}", got == want, f"measured {got[:12]} vs pinned {want[:12]}", measured=got, pinned=want)

    # --- 2. FROZEN manifest pins vs disk -------------------------------------------
    fz = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_sha = sha256(ROOT / "artifacts/formulation/FROZEN.json")
    mism, missing = [], []
    for rel, meta in fz["files"].items():
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        if sha256(p) != meta["sha256"]:
            mism.append(rel)
    check("frozen:pins", not mism and not missing,
          f"rev{fz['revision']} frozen_at {fz['frozen_at']}: {len(fz['files'])} pins, {len(mism)} mismatch, {len(missing)} missing",
          revision=fz["revision"], frozen_at=fz["frozen_at"], sha256=frozen_sha, mismatches=mism, missing=missing)
    check("frozen:non_future", fz["frozen_at"] <= datetime.now(CST).isoformat(timespec="seconds"),
          f"frozen_at {fz['frozen_at']} <= now {datetime.now(CST).isoformat(timespec='seconds')}")

    # --- 3. L-FORM-01: inverted containment premise in F2b --------------------------
    f2b = (ROOT / ANCHOR).read_text()
    ln_bad = line_of(f2b, "C2 is a strictly larger extension class")
    ln_contain = line_of(f2b, "E_C0 contains E_H2loc contains")
    check("L-FORM-01:inverted_premise", ln_bad is not None,
          f"{ANCHOR}:{ln_bad} still calls C2 a strictly larger extension class" if ln_bad
          else "inverted premise is absent (repaired)")
    check("L-FORM-01:self_contradiction", ln_bad is not None and ln_contain is not None,
          f"same file line {ln_contain} orders E_C2 inside E_C0, contradicting line {ln_bad}")

    # systematic scan: any other row asserting 'larger/smaller extension class'
    rows = []
    for rel in SCHEMAS:
        for i, l in enumerate((ROOT / rel).read_text().splitlines(), 1):
            if "extension class" in l and re.search(r"strictly (larger|smaller)", l):
                rows.append({"path": rel, "line": i, "text": l.strip()[:180]})
    check("L-FORM-01:unique", len(rows) == 1 and rows[0]["path"] == ANCHOR,
          f"{len(rows)} row(s) assert a strictly larger/smaller extension class across the three schemas",
          rows=rows)

    # --- 4. L-FORM-02: dangling declared consistency-evidence hash -------------------
    ev = ROOT / EVIDENCE
    ev_sha = sha256(ev) if ev.exists() else None
    decl = {}
    for rel in SCHEMAS:
        txt = (ROOT / rel).read_text()
        m = re.search(r"consistency_evidence_sha256:\s*\"([0-9a-f]{64})\"", txt)
        decl[rel] = m.group(1) if m else None
    dangling = [r for r, h in decl.items() if h == DEAD_DECLARED]
    check("L-FORM-02:declared_set", len(dangling) == 3,
          f"{len(dangling)}/3 schemas declare consistency_evidence_sha256={DEAD_DECLARED[:12]}",
          declared=decl)
    resolves = []
    for dp, _dn, fn in os.walk(ROOT / "artifacts"):
        for f in fn:
            if f.startswith("._"):
                continue
            p = Path(dp) / f
            try:
                if sha256(p) == DEAD_DECLARED:
                    resolves.append(str(p.relative_to(ROOT)))
            except OSError:
                pass
    at_canonical = EVIDENCE in resolves
    check("L-FORM-02:canonical_path_mismatch", ev_sha is not None and ev_sha != DEAD_DECLARED and not at_canonical,
          f"canonical path {EVIDENCE} measures {str(ev_sha)[:12]}, declared {DEAD_DECLARED[:12]}",
          measured=ev_sha, declared=DEAD_DECLARED)
    check("L-FORM-02:declared_only_in_snapshots", bool(resolves) and not at_canonical,
          f"declared hash survives only in {len(resolves)} superseded snapshot copy/copies: {resolves}",
          resolves=resolves)
    check("L-FORM-02:frozen_pins_evidence", fz["files"].get(EVIDENCE, {}).get("sha256") == ev_sha,
          f"FROZEN rev{fz['revision']} pins the evidence file at {str(fz['files'].get(EVIDENCE, {}).get('sha256'))[:12]}")

    # --- 4b. my own hash-pinned verdict census at the measured class hashes ----------
    class_hashes = {CANONICAL[k]: n for k, n in (
        ("schemas/af_wcc_vacuum.yaml", "F1"),
        ("schemas/af_scc_c2_vacuum.yaml", "F2a"),
        ("schemas/af_scc_c0_vacuum.yaml", "F2b"),
    )}
    census: dict[str, dict[str, list[str]]] = {n: {"accept": [], "revise": [], "reject": [], "inconclusive": []} for n in class_hashes.values()}
    for line in (ROOT / "research_map/events.jsonl").read_text().splitlines():
        line = line.strip()
        if not line or '"review"' not in line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("event_type") != "review":
            continue
        rh = e.get("reviewed_sha256")
        node = class_hashes.get(rh) if isinstance(rh, str) else None
        v = e.get("verdict")
        if node and v in census[node]:
            census[node][v].append(str(e.get("reviewer")))
    check("census:measured", True,
          "hash-pinned verdicts at the measured class hashes: " +
          "; ".join(f"{n} accept={len(c['accept'])} revise={len(c['revise'])} reject={len(c['reject'])}" for n, c in census.items()),
          census=census)

    # --- 5. record ------------------------------------------------------------------
    finding_checks = [c for c in checks if c["check"].startswith("L-FORM")]
    reproduced = all(c["ok"] for c in finding_checks)
    rec = {
        "artifact": "LEAD-FREEZE-HOLD-INDEPENDENT-VERIFY",
        "owner": "astra-lead-formulation",
        "lifecycle": "formulation independent lifecycle 2026-09-12T00:43+08:00",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "assignment_verified": "astra-life04-freeze-hold (executed by the prior lifecycle; re-derived here from disk)",
        "authority": "measurement and blocker report only. No frozen path was written; no node status, validation_status or gate verdict is moved by this record.",
        "measured": measured,
        "checks": checks,
        "findings_reproduced": reproduced,
        "findings": [
            {
                "id": "L-FORM-01",
                "node_id": "F2b",
                "class_id": "AF-SCC-C0-VAC-GEN",
                "severity": "major",
                "kind": "inverted justification premise (prose), conclusion direction unaffected",
                "anchor": f"{ANCHOR}#55d0a1ea9bda:{ln_bad}",
                "statement": "implication_ledger.forbidden_transfers[0].reason calls C2 'a strictly larger extension class', contradicting the same file's containment chain where E_C2 is the innermost (smallest) extension set.",
                "repair": "one token: 'strictly larger' -> 'strictly smaller' (or the F2a wording 'the converse containment is false'). Not applied: the freeze-hold stop rule forbids editing a held path.",
                "independent_reproduction": "worker-060 HF-060-F2B-1 and worker-096 R09 (both revise 3.5 at 55d0a1ea); worker-084 f2b_conflict_adj adjudicates it real/major and reconciles it against worker-098's accept.",
                "classification_open": "audit lead must rule whether G-FORM counts a prose-justification defect that is not an enumerated hard failure and sits inside a prohibition, not a transfer.",
            },
            {
                "id": "L-FORM-02",
                "node_id": "F1,F2a,F2b",
                "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                "severity": "binding hygiene (hash-level, not mathematical)",
                "anchor": f"{EVIDENCE}#{str(ev_sha)[:12]}",
                "statement": "All three class schemas declare f0_binding.consistency_evidence_sha256=675a99d0d25b while the named canonical evidence path measures 9e335e9ba1bf and is pinned there by FROZEN rev28. The declared hash is a SUPERSEDED generation of the same path that survives only inside worker snapshot copies, not at the canonical path.",
                "corroboration": "Not first reported here. worker-086 W086-GFORM-EVIDENCE-COLLISION-01 root-causes it as a canonical-path collision between three producers (declared 675a99d0 from close_findings_rev27 @00:32:02, live 9e335e9b from the standalone checker, producer-now 0f065226 with binding_rule added); worker-092 evbind measured the same mismatch on F1 and F2a. This record independently reproduces it and adds nothing new except the freeze-hold framing.",
                "repair": "refresh consistency_evidence_sha256 in all three schemas in the same revision that repairs L-FORM-01, and settle which producer owns the canonical path (worker-086 repair matrix). Not applied: freeze-hold.",
                "note": "declared_f0_sha256=0abb9ed8a961 is correct in all three; the evidence file was regenerated byte-identically at 00:42:29, so this is a stale declaration plus a producer collision, not evidence drift.",
            },
        ],
        "falsifiers": [
            "L-FORM-01 falsified if schemas/af_scc_c0_vacuum.yaml no longer contains 'C2 is a strictly larger extension class', or a containment-respecting set model exists in which E_C2 is strictly larger than E_C0.",
            "L-FORM-02 falsified if consistency_evidence_sha256 equals the measured hash of artifacts/formulation/evidence/taxonomy_consistency.json in all three schemas, or a file with the declared 675a99d0d25b hash is produced.",
            "This record is voided (not falsified) by any byte change to the five held canonical paths or by FROZEN rev28 pins ceasing to match disk.",
        ],
        "queue_impact": [
            "astra-life04-verify-gform-r2 (lead-audit, deadline 02:15) cannot reach two accepts for F2b at 55d0a1ea while two independent revise verdicts naming a content defect stand; the repair necessarily creates a new hash and voids verdicts collected at the old one. Order the repair BEFORE spending F2b re-verification budget.",
            "F1 and F2a have no reported hash-bound CONTENT defect at the rev12 hashes: the audit lead's three revise 3.5 verdicts at 00:35:58 name only coverage debt ('no second independent verdict cites <hash>', 'pre-rev27 verdicts superseded'), so their 02:15 re-verification is well-posed at the current bytes.",
            "Coverage moved during this lifecycle, so the 00:37 controller audit and the 00:41 worker-086 census are both stale: this record's stricter recount (reviewed_sha256 equal to the canonical hash) finds F1 1 accept (worker-061, created 00:40, cce9c60146d6) + 6 revise, F2a 0 accept + 5 revise, F2b 1 accept (worker-098, counts_as_full_schema_verdict=true) + 9 revise. G-FORM still needs a second independent accept per class; none of the accepts self-declares as one for F1.",
            "None of the raw accepts is evidence-anchored under PROTOCOL rule 2 as the controller reads it (no review_path/review_sha256), so 'coverage 0/N' and '1 accept present' are both defensible depending on the binding channel; worker-084 flagged this instrument ambiguity and it is unresolved.",
        ],
        "residual_uncertainty": [
            "Whether G-FORM's criteria count L-FORM-01 is a gate-classification question owned by the audit lead, not the formulation lead.",
            "This record re-measures disk and re-reads existing verdicts; it adds no new mathematical verdict.",
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "record": str(RECORD.relative_to(ROOT)),
        "findings_reproduced": reproduced,
        "checks_failed": problems,
        "held_hashes": {k: v["sha256"][:12] for k, v in measured.items()},
        "frozen": {"revision": fz["revision"], "sha256": frozen_sha[:12], "pins_ok": not mism and not missing},
    }, indent=2))
    return 0 if reproduced else 10


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # pragma: no cover
        print(f"measurement error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
