#!/usr/bin/env python3
"""Finalize W008-FORMSEP04-X3D-01: report, checkpoint, outbox events (append-only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")


def h(p: Path | str) -> str:
    p = REPO / p if not str(p).startswith("/") else Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: str) -> str:
    return f"{p}#{h(p)[:12]}"


ART = {
    "instrument": "artifacts/worker08/x3d_direction/extend_x3d.py",
    "run": "artifacts/worker08/x3d_direction/run.json",
    "report": "artifacts/worker08/x3d_direction/REPORT.md",
    "finalize": "artifacts/worker08/x3d_direction/finalize.py",
}
PRIOR = [
    "artifacts/worker08/rev29_candidate/battery_candidate.json",
    "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "artifacts/worker-008/f2b_line152_direction/evidence/report.json",
    "artifacts/worker-008/f2b_line152_direction/pinned/candidate_9ab32ee3.yaml",
    "artifacts/worker-080/f2b_hf1_direction_census/snapshots/679ab7bc8746__CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/tools/check_class_schema.py",
]

run = json.loads((REPO / ART["run"]).read_text())
controls = run["controls"]
v3 = run["v3_battery_false_negative"]

report = f"""# W008-FORMSEP04-X3D-01 — document-relative entailment-direction certification

Worker: worker-008 (`deepseek-flash-08`). Classes `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
Node F2b, gate G-CLASSBIND. Worker lifecycle only: **no node done, no gate verdict, no
`validation_status=passed`, no canonical write**; canonical paths were read-only.

## Trigger (self-correction of this slot's own instrument)

`W008-FORMSEP04-CANDIDATE-VALIDATION-01` (01:06) emitted `CANDIDATE_CLEARS_FORMSEP04` for
worker-066's rebased candidate `84b5d3fa29a6`, on a FORM-SEP-04 X1–X5 battery whose X3c
containment-inversion check returned **0 hits**. The sibling lifecycle
`W008-F2B-LINE152-DIRECTION-01` (01:12, `{ref(PRIOR[2])}`) then showed the candidate's
`regularity.must_not_conflate[0]` asserts `S_H2loc => S_C0`, the forbidden converse under the
C0 document's own declared order. The assigned acceptance instrument was not repaired by that
run; this run repairs it and re-verdicts the pinned corpus.

## Root cause (exact)

`artifacts/worker08/c2_c0_separation_audit.py` v3 `classify_dual_sentence` special-cases

```
(C0|H2_loc|C^{{1,1}})[- ]?inextendibility ... (entails?|implies?|subsum\\w*) ... (this class|C2)
```

as `correct_direction` **without resolving `this class` against the document that carries the
sentence**. The carrier sentence is true in the C2 schema (own class = C2, rank 3) and false
when transplanted byte-for-byte into the C0 schema (own class = C0, rank 0): same sentence,
different carrier document, opposite truth value. Document-relative self-reference was never
bound.

## Rule implemented (X3d, v1)

1. `size_rank` is parsed from the carrier document's own `implication_ledger.extension_class_containment`
   (`contains` or `subset of` chain). Fail-closed if absent/unparseable or not the frozen order
   `C0 > H2loc > C^1,1 > C2`.
2. `this class` / `this class's conclusion` resolves to the carrier document's own `class_id`.
3. `S_A entails S_B` is licensed iff `size_rank(A) <= size_rank(B)` (A's extension set is a
   superset of B's, so inexistence for A is the stronger statement).
4. Pre-registered carriers: `regularity.must_not_conflate[*]`,
   `implication_ledger.extension_class_containment`, `.subsumption_note`,
   `.forbidden_weakenings[*]`, `.one_way_entailments[*].reason`, `.forbidden_transfers[*].reason`.
5. Negation governs the verb → denial, not assertion; attributed/quoted mentions skipped;
   a strict entailment verb joining two class referents that the primary pattern cannot resolve
   is surfaced as `unresolved` (never silently clean). Any unresolved carrier blocks certification.

## Result — X3d-certified, 8/8 controls

| # | carrier (pin) | expected | observed |
|---|---|---|---|
| K1 | `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (canonical C0) | PASS | PASS |
| K2 | `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3` (canonical C2; **same sentence as K3**) | PASS | PASS |
| K3 | `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#84b5d3fa29a6` | FAIL | **FAIL, exactly 1 hit** `regularity.must_not_conflate[0]`: `H2loc => C0`, ranks [1, 0] |
| K4 | `artifacts/worker-008/f2b_line152_direction/pinned/candidate_9ab32ee3.yaml#9ab32ee39d00` | PASS | PASS |
| K5 | `artifacts/worker-080/f2b_hf1_direction_census/snapshots/679ab7bc8746__CANDIDATE_schemas_af_scc_c0_vacuum.yaml#679ab7bc8746` | PASS | PASS |
| K6 | synthetic C0: `this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse` | PASS | PASS |
| K7 | synthetic C0 canary: `C2-inextendibility entails this class's conclusion` | FAIL | **FAIL, 1 hit** |
| K8 | synthetic C2: `H2_loc-inextendibility ENTAILS this class's conclusion` | PASS | PASS |

K2 vs K3 is the discriminator: the identical carrier sentence is certified PASS in the C2
document and FAIL in the C0 document, solely by document-relative resolution. Unresolved
carriers: **0**. Instrument verdict: **{run['verdict']}**.

## Hash-bound v3 false negative

`{v3['artifact']}#{v3['sha256'][:12]}`: battery verdict **{v3['battery_verdict']}**,
`X3c_containment_inversion` hits **{v3['x3c_hits']}**, measured against candidate
`{v3['candidate_sha256']}`. That is the exact artifact that carried the predecessor's
`CANDIDATE_CLEARS_FORMSEP04`; X3d now returns 1 hit on the same bytes.

## Consequence (worker-level, owner binds interpretation)

- **Withdraw** `W008-FORMSEP04-CANDIDATE-VALIDATION-01`'s `CANDIDATE_CLEARS_FORMSEP04` at
  `84b5d3fa29a6`. X3d-certified: `84b5d3fa29a6` **fails** FORM-SEP-04 (X3d); `9ab32ee39d00`
  and `679ab7bc8746` clear it.
- The **canonical gate has the analogous blind spot, unchanged and not touched here**:
  `artifacts/formulation/tools/check_class_schema.py:367-370` requires a **C2 subject** for the
  R16 prose-converse check, so an `H2_loc`-subject converse against the C0 class escapes; R06
  (`:235-239`) only requires `must_not_conflate` to be non-empty. Reported as a finding for the
  instrument owner; canonical detector writes were frozen (CF-29) and none were attempted.
- Evidence for G-CLASSBIND / F2b landing review. No gate verdict, node status or
  `validation_status` transition is claimed.

## Falsifier

Any pin move voids the run (fail-closed). Certification is falsified if: the same carrier
sentence is classified identically in C0 and C2 documents (document-relative resolution
broken); `84b5d3fa29a6` does not return exactly one inverted hit at
`regularity.must_not_conflate[0]`; `9ab32ee39d00` or `679ab7bc8746` returns any hit; K6/K7/K8
flip; or an unresolved entailment carrier is counted as clean.

## Limitations

- Structural direction consistency only, against each document's **own declared** order; it does
  not re-adjudicate whether that order is the physically right one (normativity remains with
  `astra-lead-formulation`).
- Regex prose classification with a conservative fail-closed path; synonyms outside the
  registered token/verb sets are reported as unresolved rather than interpreted.
- Control fixtures K6–K8 are generated by the instrument itself; the external controls K1–K5 are
  the load-bearing ones.
"""

(REPO / ART["report"]).write_text(report, encoding="utf-8")

ev = []
base = f"w008-x3d-{STAMP}"
ev.append({
    "actor": "worker-008", "agent_id": "deepseek-flash-08", "agent_slot": "worker-008",
    "authority_note": "Worker-level instrument measurement only: no node status=done, no validation_status=passed, no gate verdict, no theorem. Canonical paths read-only.",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "created_at": NOW, "event_id": f"{base}-artifact-instrument", "event_type": "artifact",
    "gate": "G-CLASSBIND", "node_id": "F2b",
    "path": ART["instrument"], "sha256": h(ART["instrument"]),
    "validation_status": "worker_measured_unverified",
    "summary": "FORM-SEP-04 instrument repair: X3d document-relative entailment-direction certification. Resolves 'this class' to the carrier document's own class token; parses the declared extension_class_containment order; licenses S_A entails S_B iff rank(A) <= rank(B); fail-closed on unresolved strict entailments. 8/8 pre-registered controls.",
    "evidence_refs": [ref(ART["instrument"]), ref(ART["run"])],
})
ev.append({
    "actor": "worker-008", "agent_id": "deepseek-flash-08", "agent_slot": "worker-008",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "created_at": NOW, "event_id": f"{base}-artifact-run", "event_type": "artifact",
    "gate": "G-CLASSBIND", "node_id": "F2b",
    "path": ART["run"], "sha256": h(ART["run"]),
    "validation_status": "worker_measured_unverified",
    "summary": "X3d run record: K1-K8 all pass; 84b5d3fa29a6 FAILs with exactly one hit (regularity.must_not_conflate[0], H2loc=>C0, ranks [1,0]); 9ab32ee39d00 and 679ab7bc8746 PASS; identical carrier sentence PASSes in the C2 document (K2) and FAILs in the C0 document (K3); 0 unresolved carriers.",
    "evidence_refs": [ref(ART["run"]), ref(ART["instrument"]), ref(PRIOR[0]), ref(PRIOR[1])] + [ref(p) for p in PRIOR[2:8]],
})
ev.append({
    "actor": "worker-008", "agent_id": "deepseek-flash-08", "agent_slot": "worker-008",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "created_at": NOW, "event_id": f"{base}-artifact-report", "event_type": "artifact",
    "gate": "G-CLASSBIND", "node_id": "F2b",
    "path": ART["report"], "sha256": h(ART["report"]),
    "validation_status": "worker_measured_unverified",
    "summary": "Report: root cause of the X3c blind spot (no document-relative resolution of 'this class'), X3d rule, K1-K8 table, hash-bound v3 false negative, withdrawal of the predecessor CANDIDATE_CLEARS_FORMSEP04 at 84b5d3fa29a6, and the analogous untouched canonical R16 blind spot (check_class_schema.py:367-370 requires a C2 subject).",
    "evidence_refs": [ref(ART["report"]), ref(ART["run"])],
})
ev.append({
    "actor": "worker-008", "agent_id": "deepseek-flash-08", "agent_slot": "worker-008",
    "authority": "Worker-level measurement only; schema owner (lead-formulation) binds interpretation.",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "conclusion_type": "artifact_and_checker_measurement",
    "created_at": NOW, "event_id": f"{base}-claim-x3d", "event_type": "claim",
    "gate": "G-CLASSBIND", "node_id": "F2b",
    "statement": (
        "At the pinned corpus (canonical C0 schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, canonical C2 "
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3, FROZEN rev29 artifacts/formulation/FROZEN.json#815e08079aef), the "
        "FORM-SEP-04 X3c containment-inversion check is a document-relative false negative: "
        "artifacts/worker08/rev29_candidate/battery_candidate.json#2b7b19840256 records verdict PASS and X3c hits 0 for "
        "candidate 84b5d3fa29a6, while that candidate's regularity.must_not_conflate[0] asserts the forbidden converse "
        "S_H2loc => S_C0 (rank 1 -> rank 0) under the C0 document's own declared order. The repaired X3d predicate "
        "certifies 8/8 pre-registered controls: the identical carrier sentence PASSes in the C2 document and FAILs in the "
        "C0 document; 84b5d3fa29a6 FAILs with exactly one hit; direction-corrected 9ab32ee39d00 and 679ab7bc8746 PASS; "
        "0 unresolved carriers. Consequently W008-FORMSEP04-CANDIDATE-VALIDATION-01's CANDIDATE_CLEARS_FORMSEP04 at "
        "84b5d3fa29a6 is withdrawn by its own slot. The canonical R16 prose-converse check "
        "(artifacts/formulation/tools/check_class_schema.py:367-370) has the analogous blind spot because it requires a "
        "C2 subject; it was not modified."
    ),
    "assumptions": [
        "The licensing rule S_A entails S_B iff size_rank(A) <= size_rank(B) is taken from each document's own extension_class_containment and the C0 doc's forbidden_weakenings/subsumption_note; the instrument does not re-adjudicate that declared order.",
        "Token/verb vocabulary is the registered set; out-of-vocabulary strict entailments are reported unresolved and block certification rather than being interpreted.",
    ],
    "falsifier": "Any pin move; identical classification of the same carrier sentence across C0/C2 documents; 84b5d3fa29a6 not returning exactly one inverted hit at regularity.must_not_conflate[0]; any hit on 9ab32ee39d00 or 679ab7bc8746; K6/K7/K8 flipping; or an unresolved entailment carrier counted as clean.",
    "evidence_refs": [ref(ART["run"]), ref(ART["instrument"]), ref(ART["report"]), ref(PRIOR[0]), ref(PRIOR[1]), ref(PRIOR[2]), ref(PRIOR[3]), ref(PRIOR[4]), ref(PRIOR[8])],
})
ev.append({
    "actor": "worker-008", "agent_id": "deepseek-flash-08", "agent_slot": "worker-008",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "created_at": NOW, "event_id": f"{base}-status", "event_type": "status",
    "gate": "G-CLASSBIND", "node_id": "F2b", "status": "active", "hours": 0.5,
    "summary": (
        "CHECKPOINT + EXIT. One bounded class-bound task taken (no new inbox card; FORM-SEP-04 lane, F2/G-CLASSBIND): "
        "W008-FORMSEP04-X3D-01 repairs this slot's own FORM-SEP-04 battery blind spot with the document-relative X3d "
        "entailment-direction predicate and re-verdicts the pinned corpus. 8/8 controls; 84b5d3fa29a6 FAIL (1 hit), "
        "9ab32ee39d00 and 679ab7bc8746 PASS; v3 X3c false negative reproduced at hash; predecessor "
        "CANDIDATE_CLEARS_FORMSEP04 withdrawn. Canonical R16 blind spot reported, not touched. No gate verdict, node "
        "status, validation_status or theorem claimed. Worker exits."
    ),
    "evidence_refs": [ref(ART["report"]), ref(ART["run"]), ref(ART["instrument"])],
    "next_falsifier": "Pin move, or a re-run of extend_x3d.py on the same pins that does not reproduce K1-K8; or an H2_loc-subject converse that X3d passes, or a licensed C0 self-entailment that X3d flags.",
})

checkpoint = {
    "task_id": "W008-FORMSEP04-X3D-01", "actor": "worker-008",
    "created_at": NOW, "node_id": "F2b", "gate": "G-CLASSBIND",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "verdict": run["verdict"], "controls_passed": sum(1 for c in controls if c["pass"]),
    "controls_total": len(controls), "unresolved_carriers": run["unresolved_carriers"],
    "artifact_hashes": {k: h(v) for k, v in ART.items()},
    "prior_refs": {p: h(p) for p in PRIOR},
    "event_ids": [e["event_id"] for e in ev],
    "next_falsifier": run["next_falsifier"],
}
ckpt_rel = "runtime/state/worker-008_x3d_direction_checkpoint.json"
(REPO / ckpt_rel).write_text(json.dumps(checkpoint, indent=1), encoding="utf-8")
for e in ev:
    if e["event_type"] == "status":
        e["checkpoint_ref"] = ref(ckpt_rel)
        e["evidence_refs"].append(ref(ckpt_rel))

(OUT / "events_proposed.jsonl").write_text(
    "\n".join(json.dumps(e, ensure_ascii=False) for e in ev) + "\n", encoding="utf-8")

outbox = REPO / "comms/outbox/deepseek-flash-08.jsonl"
with outbox.open("a", encoding="utf-8") as fh:
    for e in ev:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

print(json.dumps({
    "report": ref(ART["report"]), "run": ref(ART["run"]), "instrument": ref(ART["instrument"]),
    "checkpoint": ref(ckpt_rel), "events": [e["event_id"] for e in ev],
    "verdict": run["verdict"], "controls": f"{sum(1 for c in controls if c['pass'])}/{len(controls)}",
}, indent=1))
