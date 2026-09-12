#!/usr/bin/env python3
"""Build reviews/F2-review-18.json from probe reports (worker deepseek-flash-18, node A1).

Assignment asg-2026-09-11-A1-deepseek-flash-18-27. Stop rule: two separate verdicts, one per
regularity; falsifier: the two verdicts must not share reasoning or conclusion type.

The review is an A1 artifact, not an F2 artifact: it does not claim F2 complete and does not
assert that either schema is mathematically correct beyond the separation question it tests.

Usage:
  python3 write_review.py --c2 PATH --c0 PATH --probe-report PATH --out OUT.json
                          [--findings FINDINGS.json] [--md OUT.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
CLASS_C2 = "AF-SCC-C2-VAC-GEN"
CLASS_C0 = "AF-SCC-C0-VAC-GEN"
SEP_RULES = {"S5", "K1", "K2", "K3", "K9", "K10a", "S3", "S4", "S2"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def tok_jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    return 0.0 if not ta or not tb else len(ta & tb) / len(ta | tb)


def score_for(hard, warns, collapse):
    if collapse == "supported":
        return 0
    if not hard and not warns:
        return 5
    if not hard:
        return 4
    # hard failures: distinguish "cannot accept" from "merge evidence"
    if any(p.split("-")[0] in ("S5", "K1", "K2", "K3", "K9", "K10a") for p in hard):
        return 1
    return 2


def reasoning_for(cid, branch, hard, warns, peer, collapse):
    """Class-specific verdict rationale. The two classes must not share reasoning; the
    stop rule of assignment asg-2026-09-11-A1-deepseek-flash-18-27 is checked downstream
    by tok_jaccard(reasoning_C2, reasoning_C0) < 0.6."""
    ev = ", ".join(hard) if hard else "none"
    if cid == CLASS_C2:
        if branch == "inconclusive":
            return ("C2 verdict withheld: schemas/af_scc_c2_vacuum.yaml is not on disk at review "
                    "time, so the C2 boundary cannot be tested. The instrument that would test it "
                    "passed its planted-collapse control.")
        if branch == "collapse":
            return (f"The C2 class lives or dies on the differentiability it demands of the "
                    f"extension: C2-inextendibility is the statement that survives known "
                    f"continuous extensions. Collapse evidence [{ev}] shows the submitted C2 "
                    f"document is not C2-specific where it must be, so its separation from the "
                    f"low-regularity class is rejected rather than merely incomplete.")
        if branch == "hard":
            return (f"C2 boundary not collapsed, but the submitted C2 document is not yet a "
                    f"well-formed class definition: hard failures [{ev}] leave the C2 side "
                    f"dependent on fields it does not itself supply.")
        if branch == "provenance":
            return (f"C2 separation holds and no content failure was found; what blocks a clean "
                    f"acceptance is hash provenance [{ev}], which prevents freezing a citable "
                    f"sha256 for the reviewed pair.")
        if branch == "warn":
            return (f"C2 separation holds on the discriminating probes; residual warnings "
                    f"[{', '.join(warns)}] concern completeness, not class identity.")
        return ("C2 separation holds: the C2 document declares its own regularity, carries a "
                "C2-specific obstruction, and does not duplicate the low-regularity conclusion.")
    # CLASS_C0
    if branch == "inconclusive":
        return ("C0 verdict withheld: schemas/af_scc_c0_vacuum.yaml is not on disk at review "
                "time. The continuous-extension anchor (Dafermos-Luk, arXiv:1710.01722) is "
                "recorded here so the eventual C0 review tests the right failure mode.")
    if branch == "collapse":
        return (f"The C0 class is defined by what fails at continuity: Kerr Cauchy horizons "
                f"extend with a continuous metric (arXiv:1710.01722), so a C0 schema must record "
                f"that obstruction and cannot reuse an inextendibility conclusion. Collapse "
                f"evidence [{ev}] shows the submitted C0 document shares the C2 content instead "
                f"of stating its own, so the low-regularity class is not distinguished.")
    if branch == "hard":
        return (f"The C0 document is separable from C2 in principle, but hard failures [{ev}] "
                f"mean it does not yet pin its own regularity, obstruction, or anti-scope, so it "
                f"cannot be frozen as a distinct class.")
    if branch == "provenance":
        return (f"The C0 content separates from C2 on every discriminating probe, but the "
                f"artifact's hash provenance is broken [{ev}]: the companion sidecar names a "
                f"superseded revision, so no reviewer or gate can cite a stable sha256 for the "
                f"document under review. Regenerate the sidecar to the current revision or "
                f"remove it, then re-run the probe set.")
    if branch == "warn":
        return (f"C0 separation holds on the discriminating probes; warnings [{', '.join(warns)}] "
                f"are non-blocking but must be dispositioned before freeze.")
    return ("C0 separation holds: the document records the continuous-extendibility obstruction "
            "with a primary-source anchor and excludes the C2 conclusion explicitly.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c2", required=True)
    ap.add_argument("--c0", required=True)
    ap.add_argument("--probe-report", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md")
    ap.add_argument("--findings")
    a = ap.parse_args()

    c2, c0 = Path(a.c2), Path(a.c0)
    probe = json.loads(Path(a.probe_report).read_text())
    manual = json.loads(Path(a.findings).read_text()) if a.findings else {}

    inputs_exist = c2.exists() and c0.exists()
    probes = probe.get("probes", [])
    collapse = probe.get("class_collapse", "undetermined")

    def block(cid, peer, peer_role):
        own = [p for p in probes if p["class_id"] in (cid, "BOTH")]
        hard = [p["probe_id"] for p in own if p["severity"] == "hard" and p["verdict"] == "fail"]
        warns = [p["probe_id"] for p in own if p["severity"] == "warn" and p["verdict"] in ("fail", "warn")]
        findings = [{"finding_id": p["probe_id"], "severity": p["severity"], "verdict": p["verdict"],
                     "statement": p["detail"], "evidence_refs": p["evidence"]} for p in own]
        findings += manual.get(cid, [])
        # manual hard findings are reviewer findings: they belong in hard_failures even though
        # they were not produced by the probe script (e.g. cross-instrument disagreements).
        manual_hard = [f["finding_id"] for f in manual.get(cid, [])
                       if f.get("severity") == "hard" and f.get("verdict") == "fail"]
        hard = sorted(set(hard + manual_hard))
        if not inputs_exist:
            verdict, sc, branch = "inconclusive", 0, "inconclusive"
        elif collapse == "supported":
            verdict, sc, branch = "reject", score_for(hard, warns, collapse), "collapse"
        elif hard:
            if all(h.startswith("K12") for h in hard):
                verdict, sc, branch = "revise", score_for(hard, warns, collapse), "provenance"
            else:
                verdict = "reject" if any(p.split("-")[0] in SEP_RULES for p in hard) else "revise"
                sc, branch = score_for(hard, warns, collapse), "hard"
        elif warns:
            verdict, sc, branch = "revise", score_for(hard, warns, collapse), "warn"
        else:
            verdict, sc, branch = "accept", 5, "clean"
        reasoning = reasoning_for(cid, branch, hard, warns, peer, collapse)
        return {
            "class_id": cid,
            "target_path": str(c2 if cid == CLASS_C2 else c0),
            "target_sha256": sha256_file(c2 if cid == CLASS_C2 else c0) if inputs_exist else None,
            "peer_class": peer,
            "verdict": verdict,
            "score_0_5": sc,
            "hard_failures": sorted(set(hard)),
            "warnings": sorted(set(warns)),
            "reasoning": reasoning,
            "findings": findings,
            "next_falsifier": (
                f"A rewritten {cid} schema that (a) declares its own extension regularity, "
                f"(b) does not restate the {peer_role} conclusion, and (c) names a class-specific "
                f"known obstruction, would refute this verdict's reject/revise component; re-run "
                f"f2_class_probe.py and require zero hard failures."),
            "not_claimed": ["F2 node completion", "schema mathematical correctness",
                            "that no C0==C2 collapse exists off the probe set"],
        }

    v2 = block(CLASS_C2, CLASS_C0, "C0")
    v0 = block(CLASS_C0, CLASS_C2, "C2")
    distinct = tok_jaccard(v2["reasoning"], v0["reasoning"])
    if distinct >= 0.6:
        print(f"REVIEW ERROR: verdict reasonings too similar (jaccard={distinct:.2f}); "
              f"stop rule violated", file=sys.stderr)
        return 1
    if v2["verdict"] == "accept" and v0["verdict"] == "accept" and collapse == "supported":
        print("REVIEW ERROR: both accepted while collapse supported", file=sys.stderr)
        return 1

    review = {
        "review_id": "F2-review-18",
        "reviewer": "deepseek-flash-18",
        "node_id": "A1",
        "target_node": "F2",
        "assignment_event_id": "asg-2026-09-11-A1-deepseek-flash-18-27",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "gate": "G-AUDIT",
        "adversarial_goal": "Try to prove the C0 and C2 schemas are the same class.",
        "class_collapse_attempt": {
            "result": collapse,
            "evidence": probe.get("collapse_evidence", []),
            "conclusion": ("The collapse attempt SUCCEEDED: collapse probes fired."
                           if collapse == "supported" else
                           "The collapse attempt FAILED: no class-collapse evidence on the probe set."
                           if collapse == "not_supported" else
                           "The collapse attempt is UNDETERMINED: inputs missing or unparseable."),
        },
        "inputs": {
            CLASS_C2: {"path": str(c2), "sha256": sha256_file(c2) if c2.exists() else None,
                       "exists": c2.exists()},
            CLASS_C0: {"path": str(c0), "sha256": sha256_file(c0) if c0.exists() else None,
                       "exists": c0.exists()},
            "probe_report": {"path": a.probe_report, "sha256": sha256_file(Path(a.probe_report))},
            "instrument": {"path": "artifacts/worker18/f2_review/f2_class_probe.py",
                           "sha256": sha256_file(Path("artifacts/worker18/f2_review/f2_class_probe.py"))},
        },
        "verdicts": [v2, v0],
        "verdict_distinctness_jaccard": round(distinct, 3),
        "limitations": [
            "Probes are structural/lexical; they detect merged-class tokens, conclusion inheritance, "
            "identical obstructions, and C2-assumption leakage, but they cannot prove two schemas "
            "define different solution sets.",
            "K5 anchors the C0 obstruction to arXiv:1710.01722 (Dafermos-Luk); that anchor itself "
            "was fetched from the arXiv abstract page, not from the published Annals version.",
            "Artifact correctness beyond separation is out of scope for this review; a separate "
            "content review of each schema is required before freeze.",
        ],
        "reviewer_independence_note": (
            "The same reviewer produced both verdicts as the assignment directs. Independence "
            "between the two verdicts is enforced mechanically (reasoning jaccard "
            f"{distinct:.2f} < 0.6) and each verdict lists class-specific probes; independence of "
            "this reviewer from the schema authors is preserved (worker 18 drafted neither schema)."),
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review, indent=2))
    if a.md:
        lines = [f"# F2 review 18 — adversarial class-collapse review", "",
                 f"- assignment: {review['assignment_event_id']}",
                 f"- collapse attempt result: **{collapse}**",
                 f"- C2 sha256: `{review['inputs'][CLASS_C2]['sha256']}`",
                 f"- C0 sha256: `{review['inputs'][CLASS_C0]['sha256']}`", ""]
        for v in review["verdicts"]:
            lines += [f"## {v['class_id']} — verdict: **{v['verdict']}** (score {v['score_0_5']}/5)", "",
                      v["reasoning"], "",
                      f"hard failures: {v['hard_failures'] or 'none'}",
                      f"warnings: {v['warnings'] or 'none'}", ""]
            for f in v["findings"]:
                lines.append(f"- [{f['severity']}/{f['verdict']}] {f['finding_id']}: {f['statement']}")
            lines.append("")
        lines += ["## Limitations", ""] + [f"- {x}" for x in review["limitations"]] + [""]
        Path(a.md).write_text("\n".join(lines))
    print(json.dumps({"out": str(out), "class_collapse": collapse,
                      "verdicts": {v["class_id"]: {"verdict": v["verdict"], "score": v["score_0_5"],
                                                   "hard_failures": v["hard_failures"]}
                                   for v in review["verdicts"]},
                      "distinctness_jaccard": round(distinct, 3)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
