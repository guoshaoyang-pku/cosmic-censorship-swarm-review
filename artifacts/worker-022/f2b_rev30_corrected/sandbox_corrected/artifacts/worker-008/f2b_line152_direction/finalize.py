#!/usr/bin/env python3
"""Finalize W008-F2B-LINE152-DIRECTION-01: pins, README, checkpoints, outbox events."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-008/f2b_line152_direction"
OUTBOX = ROOT / "comms/outbox/worker-008.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TS = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


INPUTS = {
    "canonical_c0__af_scc_c0_vacuum.yaml": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "canonical_c2__af_scc_c2_vacuum.yaml": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "frozen__FROZEN.json": ROOT / "artifacts/formulation/FROZEN.json",
    "candidate_84b5d3fa.yaml": ROOT / "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "candidate_48cadb72.yaml": ROOT / "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml",
    "candidate_679ab7bc.yaml": ROOT / "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
    "candidate_9ab32ee3.yaml": ROOT / "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
}


def main() -> int:
    pin = OUT / "pinned"
    pin.mkdir(parents=True, exist_ok=True)
    pins = {}
    for name, src in INPUTS.items():
        dst = pin / name
        if not dst.exists() or sha(dst) != sha(src):
            shutil.copy2(src, dst)
        pins[name] = {"source": str(src.relative_to(ROOT)), "sha256": sha(dst)}
    (OUT / "evidence" / "pins.json").write_text(json.dumps(pins, indent=1) + "\n", encoding="utf-8")

    report = json.loads((OUT / "evidence" / "report.json").read_text())
    readme = f"""# W008-F2B-LINE152-DIRECTION-01 — line-152 replacement-clause direction adjudication

Worker: worker-008 (deepseek-flash-08 slot 008). Class: AF-SCC-C0-VAC-GEN (node F2b, gate G-FORM).
Scope: worker lifecycle only. No node done, no gate verdict, no canonical write, no validation_status=passed.

## Live dispute decided
worker-023 (W023-F2B-DIR-REVIEW-01) reported that the standing F2b rev29 repair
(worker-066 candidate `84b5d3fa29a6`, worker-044 composed `48cadb72e507`) *introduces* a false
entailment in `regularity.must_not_conflate[0]`: "so H2_loc-inextendibility ENTAILS this class's
conclusion". worker-036 (`24/24 candidate checks`) and worker-066 reported the same candidate
defect-free. This run independently adjudicates the dispute at the pinned bytes.

## Oracle (from the documents themselves)
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` declares
`extension_class_containment: E_C0 contains E_H2loc contains E_{{C^1,1}} contains E_C2`, i.e.
size ranks {{C0:3, H2loc:2, C^1,1:1, C2:0}}; `forbidden_weakenings[2]` says
"H2_loc-inextendibility is weaker and entails the C2 sibling, **not this class**"; `subsumption_note`
says "C0 => H2loc => C2, **never the reverse**". Rule used: S_X entails S_Y iff size(X) >= size(Y).
For the clause's claim S_H2loc => S_C0: size(H2loc)=2 < size(C0)=3, so the claim is false.

## Result ({NOW})
| artifact | sha256 | finding |
|---|---|---|
| canonical C0 (live) | b2ab6acb2bbe | denial (`:152`) + inverted size premise (`:246`) — the two known defects |
| worker-066 / prior-008 candidate | 84b5d3fa29a6 | **entailment_direction_inverted** at `regularity.must_not_conflate[0]` |
| worker-044 composed rev14 | 48cadb72e507 | **entailment_direction_inverted** (same clause, byte-identical) |
| worker-024 2-line repair | 679ab7bc8746 | clean |
| worker-023 direction-corrected | 9ab32ee39d00 | clean |

Verdict: **{report['verdict']}**. Controls 6/6 pass (A canonical denial, B re-injected entailment,
C valid C2 direction, D attributed-quote guard, E re-injected size inversion, F empty R06 slot).
Instrument: `adjudicate_line152_direction.py` (fail-closed: exit 2 on any pin move, exit 3 on
unclassifiable carrier). Evidence: `evidence/report.json`, `evidence/pins.json`.

## Falsifier
{report['falsifier']}

## Provenance note
`84b5d3fa` is also this slot's predecessor candidate (W008-FORMSEP04-CANDIDATE-VALIDATION-01);
this run corrects it: its containment-defect repair is right in substance but its replacement
sentence states the C0 entailment backwards. Any landing must use a direction-corrected clause
(e.g. `9ab32ee3` / `679ab7bc` or equivalent) and a gate predicate that certifies entailment
direction, since R06 passes direction-reversed text.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    artifacts = {
        "instrument": OUT / "adjudicate_line152_direction.py",
        "report": OUT / "evidence/report.json",
        "pins": OUT / "evidence" / "pins.json",
        "readme": OUT / "README.md",
    }
    hashes = {k: sha(v) for k, v in artifacts.items()}
    checkpoint = {
        "schema": "worker-008/checkpoint/v1",
        "task_id": "W008-F2B-LINE152-DIRECTION-01",
        "worker": "worker-008",
        "actor": "worker-008",
        "instance": "worker-008-20260912T010638-968807",
        "created_at": NOW,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "worker-level complete; no node done, no gate verdict",
        "verdict": report["verdict"],
        "pins": {k: v["sha256"] for k, v in pins.items()},
        "artifacts": {k: {"path": str(v.relative_to(ROOT)), "sha256": hashes[k]} for k, v in artifacts.items()},
        "controls_passed": sum(1 for c in report["controls"].values() if c["pass"]),
        "controls_total": len(report["controls"]),
        "falsifier": report["falsifier"],
        "authority_limit": "worker evidence only; canonical paths read-only; formulation owner lands any repair",
    }
    (OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n", encoding="utf-8")
    hashes["checkpoint"] = sha(OUT / "CHECKPOINT.json")
    (ROOT / "runtime/state/worker-008_f2b_line152_direction_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=1) + "\n", encoding="utf-8")
    with (ROOT / "artifacts/worker-008/checkpoints.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"worker": "worker-008", "task_id": checkpoint["task_id"],
                            "checkpoint_at": NOW, "verdict": report["verdict"],
                            "artifacts": checkpoint["artifacts"],
                            "controls": f"{checkpoint['controls_passed']}/{checkpoint['controls_total']}",
                            "next_falsifier": report["falsifier"]}, sort_keys=True) + "\n")

    # ---- events ----
    sys.path.insert(0, str(ROOT / "research_map"))
    from schemas import validate_event  # noqa: E402

    refs_common = [
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#84b5d3fa29a6",
        "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml#48cadb72e507",
        "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml#679ab7bc8746",
        "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml#9ab32ee39d00",
        "schemas/af_scc_c0_vacuum.yaml:152",
        "schemas/af_scc_c0_vacuum.yaml:232",
        "schemas/af_scc_c0_vacuum.yaml:239",
    ]
    art_refs = [f"{checkpoint['artifacts'][k]['path']}#{hashes[k][:12]}" for k in
                ("instrument", "report", "pins", "readme")]
    art_refs.append(f"{checkpoint['artifacts']['readme']['path'].rsplit('/', 1)[0]}/CHECKPOINT.json#{hashes['checkpoint'][:12]}")
    ev = []

    def add(tag, **kw):
        e = {"event_id": f"w008-l152-{TS}-{tag}", "created_at": NOW, "actor": "worker-008"}
        e.update(kw)
        validate_event(e)
        ev.append(e)

    add("artifact-instrument", event_type="artifact", node_id="F2b", artifact_type="tool",
        path=checkpoint["artifacts"]["instrument"]["path"], sha256=hashes["instrument"],
        validation_status="unverified",
        summary="Read-only fail-closed direction oracle: parses the document's own chain/ranks, classifies carriers, 6/6 controls.")
    add("artifact-report", event_type="artifact", node_id="F2b", artifact_type="evidence",
        path=checkpoint["artifacts"]["report"]["path"], sha256=hashes["report"],
        validation_status="unverified",
        summary=f"Per-candidate findings + oracle census: standing repair 84b5d3fa/48cadb72 inverted at :152; 024/023 candidates clean; canonical carries the two known defects. Controls 6/6.")
    add("artifact-pins", event_type="artifact", node_id="F2b", artifact_type="evidence",
        path=checkpoint["artifacts"]["pins"]["path"], sha256=hashes["pins"],
        validation_status="unverified", summary="Byte copies + sha256 of all seven pinned inputs.")
    add("artifact-readme", event_type="artifact", node_id="F2b", artifact_type="report",
        path=checkpoint["artifacts"]["readme"]["path"], sha256=hashes["readme"],
        validation_status="unverified", summary="Method, oracle, result table, falsifier, authority limits, predecessor correction.")
    add("artifact-checkpoint", event_type="artifact", node_id="F2b", artifact_type="checkpoint",
        path="artifacts/worker-008/f2b_line152_direction/CHECKPOINT.json", sha256=hashes["checkpoint"],
        validation_status="unverified", summary="Worker checkpoint (worker-level completion only).")

    add("claim", event_type="claim", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        conclusion_type="formal_model",
        statement=("At the pinned bytes (canonical F2b b2ab6acb2bbe, F2a e9a27996dfd3, FROZEN rev29 815e08079aef), "
                   "an independent class-relative direction oracle built only from the document's own declared chain/ranks "
                   "adjudicates the live worker-023-vs-worker-036/066 dispute: the standing rev29 repair candidates "
                   "worker-066/prior-008 84b5d3fa29a6 and worker-044 48cadb72e507 rewrite regularity.must_not_conflate[0] "
                   "into the sentence 'so H2_loc-inextendibility ENTAILS this class's conclusion', which is false for "
                   "AF-SCC-C0-VAC-GEN: the document's own forbidden_weakenings[2] says H2_loc-inextendibility 'entails the C2 "
                   "sibling, not this class' and subsumption_note says C0 => H2loc => C2, never the reverse; under the declared "
                   "chain E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2, S_H2loc does not entail S_C0. Both candidates "
                   "therefore fix the size-premise defect but introduce a normative entailment inversion in a required R06 slot "
                   "that the canonical structural gate cannot see. worker-024's 679ab7bc8746 and worker-023's 9ab32ee39d00 carry "
                   "no direction finding and are clean on this axis. Canonical b2ab6acb still carries the two known defects "
                   "(denial at :152, inverted size premise at :246). Measurement only; no class is claimed true or refuted."),
        assumptions=[
            "the document's own extension_class_containment/ranks, forbidden_weakenings and subsumption_note are the oracle for licensed direction; nestedness is not re-derived from regularity definitions",
            "inexistence statements S_X quantify over extension sets E_X, so S_X entails S_Y iff size(E_X) >= size(E_Y)",
            "textual direction consistency is not mathematical truth; a corrected clause does not make either class true or refuted",
            "worker evidence only: a G-FORM reviewer and the formulation owner must dispose the landing decision",
        ],
        falsifier=report["falsifier"], evidence_refs=refs_common + art_refs)

    add("review", event_type="review", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        target_id="artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#84b5d3fa29a6",
        target_sha256="84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
        reviewer="worker-008", verdict="revise", score=2.5,
        hard_failures=[{"id": "W008-L152-D1", "severity": "blocking", "carrier": "regularity.must_not_conflate[0]",
                        "finding": ("replacement clause asserts H2_loc-inextendibility ENTAILS this class's conclusion; the "
                                    "document's own forbidden_weakenings[2]/subsumption_note/ranks deny the reverse direction "
                                    "(C0 => H2loc => C2, never the reverse)")}],
        findings=["worker-023 W023-F2B-DIR1 independently reproduced by a separate code path at the same pins; worker-036's 24/24 candidate-clean verdict did not test class-relative entailment direction.",
                  "worker-044 48cadb72 carries the same clause byte-identically.",
                  "worker-024 679ab7bc and worker-023 9ab32ee3 are clean on chain direction, size premise and denial at these pins.",
                  "Instrument controls 6/6; canonical gate blindness to direction is the reason a G-FORM accept at the repaired bytes would freeze the inversion."],
        evidence_refs=refs_common + art_refs,
        summary="Independent adjudication of the line-152 replacement clause: standing repair 84b5d3fa/48cadb72 is direction-inverted; revise. Not a full-schema verdict; canonical paths untouched.")

    add("blocker", event_type="blocker", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        description=("The standing F2b rev29 landing candidate is not direction-finding-free: 84b5d3fa29a6 and 48cadb72e507 "
                     "replace the line-152 denial with 'H2_loc-inextendibility ENTAILS this class's conclusion', which the C0 "
                     "document itself denies (forbidden_weakenings[2], subsumption_note, rank order). Landing it freezes a new "
                     "normative inversion in a required R06 slot."),
        needed_to_unblock=("astra-lead-formulation lands a direction-corrected two-leaf clause (worker-023 9ab32ee39d00 / "
                           "worker-024 679ab7bc8746, or equivalent wording that keeps C0 => H2loc => C2), re-freezes, and the "
                           "G-FORM r3 reviewers re-run at the new hashes; recommended alongside: add an entailment-direction "
                           "predicate to check_class_schema.py so R06/R16 certify slot content, not just slot presence."),
        stop_rule="Repair + re-freeze + re-run to PASS; or a reviewer shows a reading of the pinned document under which S_H2loc entails S_C0.",
        evidence_refs=refs_common + art_refs)

    add("status", event_type="status", node_id="F2b", status="active", hours=0.5, gate="G-FORM",
        summary=("CHECKPOINT + EXIT. W008-F2B-LINE152-DIRECTION-01 complete at worker level: one self-selected bounded "
                 "class-bound task (no inbox card existed). Independent direction oracle at FROZEN rev29 pins confirmed "
                 "worker-023 and corrected the standing repair + this slot's predecessor candidate: 84b5d3fa/48cadb72 invert "
                 "the H2loc->C0 entailment at line 152; 024/023 candidates clean; canonical carries the two known defects; "
                 "6/6 controls. No node done, no gate verdict, no canonical write."),
        evidence_refs=refs_common + art_refs, next_falsifier=report["falsifier"])

    existing = set()
    if OUTBOX.exists():
        for ln in OUTBOX.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(ln).get("event_id"))
            except Exception:
                pass
    new = [e for e in ev if e["event_id"] not in existing]
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"outbox": str(OUTBOX.relative_to(ROOT)), "emitted": len(new),
                      "event_ids": [e["event_id"] for e in new],
                      "artifacts": checkpoint["artifacts"], "verdict": report["verdict"],
                      "controls": f"{checkpoint['controls_passed']}/{checkpoint['controls_total']}"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
