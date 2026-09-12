#!/usr/bin/env python3
"""
Emit the W017 F2b rev13 containment adjudication:
  - reviews/F2b-rev13-containment-worker-017.json
  - comms/outbox/worker-017.jsonl  (artifact x2, review, status, blocker)
  - runtime/state/w017_checkpoint_f2b_rev13_containment.json
  - runtime/state/w017_checkpoints.jsonl (append)

Fail-closed: aborts if the reviewed F2b hash moved since the instrument run.
"""
import datetime
import hashlib
import json
import os
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-017/f2b_rev13_containment")

TARGET_PATH = "schemas/af_scc_c0_vacuum.yaml"
TARGET_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jload(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(p, obj):
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def main():
    key_inputs = {
        TARGET_PATH: TARGET_SHA,
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": TARGET_SHA,
        "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
        "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml":
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    }
    live = {p: sha256(os.path.join(ROOT, p)) for p in key_inputs}
    drift = {p: {"expected": v, "live": live[p]} for p, v in key_inputs.items() if live[p] != v}
    if drift:
        print(json.dumps({"status": "PIN_DRIFT_AT_EMIT", "drift": drift}, indent=1))
        sys.exit(2)

    now = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")

    report = jload(os.path.join(HERE, "report.json"))
    controls = jload(os.path.join(HERE, "controls.json"))
    pins = jload(os.path.join(HERE, "pins.json"))
    hashes = {name: sha256(os.path.join(HERE, name))
              for name in ("verify.py", "report.json", "controls.json", "pins.json")}
    rev12 = live["artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml"]

    h1 = {
        "id": "B17-R13-01",
        "severity": "blocking-for-clean-accept",
        "blocking": True,
        "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "line": 246,
        "finding": (
            "Inverted premise in a normative ledger row. The row's from/to pair and its conclusion are "
            "correct (E_C2 is the innermost admissible-extension set, so 'no proper future C2 extension' "
            "does not entail this class's conclusion and C2-inextendibility is strictly weaker). The stated "
            "premise is false against the file's own chain at :238 ('E_C0 contains E_H2loc contains "
            "E_{C^1,1} contains E_C2') and against the sibling C2 schema at :237 ('E_C2 subset of ... subset "
            "of E_C0'), both of which make E_C2 the strictly SMALLER admissible-extension set. The row is "
            "byte-identical to the pinned rev12 55d0a1ea, so rev13 carried the defect forward."
        ),
        "deciding_lines": [
            "schemas/af_scc_c0_vacuum.yaml:238 extension_class_containment (E_C2 innermost)",
            "schemas/af_scc_c0_vacuum.yaml:246 reason ('strictly larger extension class')",
            "schemas/af_scc_c2_vacuum.yaml:237 sibling nested-extension-set statement",
        ],
        "evidence": ["CHK-06", "CHK-07", "CHK-08", "CHK-09", "CHK-11", "gate M0/M1/M2/M10"],
        "minimal_repair": 'one token: "strictly larger extension class" -> "strictly smaller extension class" (owner: lead-formulation; no class-semantics change beyond the premise wording)',
        "falsifier": "an extension-set reading exists under which E_C2 strictly contains E_C0 given the file's own definitions; or the containment chain at :238 is itself repaired to place E_C2 outermost while keeping :246.",
    }
    h2 = {
        "id": "B17-R13-02",
        "severity": "blocking-for-clean-accept",
        "blocking": True,
        "carrier": "regularity.must_not_conflate[0]",
        "line": 152,
        "finding": (
            "Stale containment denial in a required normative slot (rule_spec R06: must_not_conflate is a "
            "non-empty list). The sentence 'No containment with C2 or C0 is asserted here' is false of the "
            "same document, whose implication_ledger asserts E_C0 contains E_H2loc contains E_{C^1,1} "
            "contains E_C2 at :238 and derives four one-way entailments from those containments at :241-244. "
            "The sibling F2a carries the corrected counterpart at :152 and explicitly records the denial "
            "wording as wrong ('the earlier \"no containment with C2 is asserted\" was wrong'), so this is a "
            "stale sentence, not an intended distinct semantics. The row is byte-identical to rev12 55d0a1ea."
        ),
        "deciding_lines": [
            "schemas/af_scc_c0_vacuum.yaml:152 denial sentence",
            "schemas/af_scc_c0_vacuum.yaml:238 asserted containment chain",
            "schemas/af_scc_c0_vacuum.yaml:241-244 one-way entailments",
            "schemas/af_scc_c2_vacuum.yaml:152 corrected sibling wording",
        ],
        "evidence": ["CHK-05", "CHK-10", "CHK-11", "CHK-12", "gate M0/M4/M5"],
        "minimal_repair": "scope the denial to H2_loc as a curvature-based axis value (or delete the denial clause); the remainder of the entry is correct and may stand (owner: lead-formulation)",
        "falsifier": "explicit text at the reviewed hash scopes the denial to the axis-value reading so it cannot be read against the ledger's E_H2loc containment claims.",
    }
    findings = [
        {
            "id": "N17-R13-01",
            "severity": "non_blocking",
            "kind": "instrument_coverage",
            "finding": ("Canonical structural gate cannot certify either carrier: check_class_schema.py returns "
                        "PASS for the defective canonical file and for a fully inverted H1 conclusion, an H1 "
                        "nonsense reason, H2 deletion, a false H2 containment, and a reversed containment chain "
                        "(M0-M5, M10). It is alive on structure (M6 emptied must_not_conflate -> R22/R31 fail, "
                        "M8/M9 ledger -> R16 fail, M11 regularity token -> R06 fail). R16 checks from/to tokens "
                        "and a verb-list prose regex, never the premise of reason/containment strings."),
            "evidence": ["gate M0-M11", "controls.json"],
            "falsifier": "the gate distinguishes repaired from defective wording on any of M1-M5/M10.",
        },
        {
            "id": "N17-R13-02",
            "severity": "non_blocking",
            "kind": "process_disclosure",
            "finding": ("Supersession disclosure: reviews/F2b-review-17-current.json (same slot, earlier instance) "
                        "accepted F2b at the superseded hash 1bb78ce9 while worker-22 had already flagged the H2 "
                        "contradiction at that same hash (inconclusive 2.5) and lead-audit had revised it. This "
                        "verdict is bound to b2ab6acb and supersedes that accept for the two carriers reviewed "
                        "here; the change of judgement is driven by the primary bytes, not by the other verdicts."),
            "evidence": ["reviews/F2b-review-17-current.json", "reviews/F2b-review-22.json"],
            "falsifier": "the earlier verdict is shown to have already carried and discharged these two carriers at 1bb78ce9.",
        },
        {
            "id": "N17-R13-03",
            "severity": "non_blocking",
            "kind": "binding",
            "finding": ("f0_binding names artifacts/formulation/formulation_taxonomy.yaml as class_contract_supplement "
                        "but carries no supplement hash; the declared F0 hash and the consistency-evidence hash both "
                        "resolve (CHK-13). Recommend a class_contract_supplement_sha256 field at the next revision "
                        "(corroborates worker-001 W001-ID-02 by an independent route)."),
            "evidence": ["CHK-13", "f0_binding block"],
            "falsifier": "a pinned supplement hash is present in f0_binding at the reviewed revision.",
        },
        {
            "id": "N17-R13-04",
            "severity": "non_blocking",
            "kind": "process",
            "finding": ("Any repair moves the hash and voids every verdict bound to b2ab6acb, including this one. "
                        "The two single-token/single-clause repairs should be batched with the lead's other rev14 "
                        "edits, re-frozen (FROZEN rev30+), and re-reviewed once; do not re-point this verdict to a "
                        "new hash."),
            "evidence": ["FROZEN rev29", "pins.json"],
            "falsifier": "the owner re-emits a new revision and a fresh review binds it.",
        },
        {
            "id": "N17-R13-05",
            "severity": "non_blocking",
            "kind": "corroboration",
            "finding": ("Independent reproduction note: the H1 carrier was previously measured at the rev12 pin by "
                        "worker-060 (PR-F2B-245, containment sweep) and both carriers were flagged at b2ab6acb by "
                        "worker-066. My instrument was written independently from the primary bytes; the overlap is "
                        "the two carriers themselves. worker-066's rebased file (01:01:15) swaps the H1/H2 label "
                        "assignment relative to its first file (00:56:05) - readers should key on the carrier text, "
                        "not on those labels."),
            "evidence": ["reviews/F2b-containment-normativity-worker-066.json",
                         "reviews/F2b-rev29-containment-rebase-worker-066.json",
                         "artifacts/worker-060/containment_semantics_sweep/REPORT.md"],
            "falsifier": "either prior record is shown not to bind the carriers at its stated pin.",
        },
    ]

    review = {
        "schema_version": "0.1",
        "event_id": "w017-%s-f2b-rev13-containment-review" % stamp,
        "event_type": "review",
        "created_at": now,
        "actor": "worker-017",
        "reviewer": "worker-017",
        "task_id": "W017-F2B-REV13-CONTAINMENT-ADJUDICATION-01",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "target_id": "F2b",
        "target_path": TARGET_PATH,
        "artifact": TARGET_PATH,
        "artifact_sha256": TARGET_SHA,
        "reviewed_sha256": TARGET_SHA,
        "artifact_revision_read": 13,
        "artifact_revision": 13,
        "frozen_revision": 29,
        "frozen_sha256": live["artifacts/formulation/FROZEN.json"],
        "verdict": "revise",
        "score": 3.0,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent": True,
        "verdict_scope": ("Full-surface structural review of the F2b rev13 schema at FROZEN rev29 plus "
                          "adjudication of the two carried containment carriers. It does not re-derive the "
                          "mathematics, the L1 citation ledger, or the F0 index-domain deferral (worker-001's "
                          "axis), and issues no gate verdict and no node status."),
        "summary": ("Both carried containment carriers are live defects at b2ab6acb: the ledger reason at :246 "
                    "inverts the extension-set premise, and the must_not_conflate denial at :152 contradicts the "
                    "same document's asserted containment chain and its corrected C2 sibling. Both are "
                    "byte-identical to the pinned rev12 55d0a1ea; the rev13 delta is binding-only. The canonical "
                    "structural gate PASSES the defective file and every semantically different H1/H2 variant, so "
                    "a gate PASS cannot certify these clauses. Everything else on the structural surface is clean "
                    "(no C0/C2 conclusion merge, quantifier chain and f0_binding resolve). Verdict: revise; two "
                    "minimal wording repairs, then re-freeze and re-review."),
        "hard_failures": [h1, h2],
        "findings": findings,
        "p2_triage": {
            "blocking": ["B17-R13-01", "B17-R13-02"],
            "non_blocking": ["N17-R13-01", "N17-R13-02", "N17-R13-03", "N17-R13-04", "N17-R13-05"],
        },
        "method": {
            "instrument": "artifacts/worker-017/f2b_rev13_containment/verify.py",
            "instrument_sha256": hashes["verify.py"],
            "report": "artifacts/worker-017/f2b_rev13_containment/report.json",
            "report_sha256": hashes["report.json"],
            "controls": "artifacts/worker-017/f2b_rev13_containment/controls.json",
            "controls_sha256": hashes["controls.json"],
            "checks_passed": "%d/%d" % (report["checks_passed"], report["checks_total"]),
            "pre_registered_controls_matched": controls["controls_ok"],
            "pins_stable_pre_post": pins["stable"],
            "gate_mutants": {k: {"expected": v["expected"], "actual": v["actual"]}
                             for k, v in sorted(controls["mutants"].items())},
        },
        "independence": ("I authored no part of the canonical F2b schema, FROZEN.json, rule_spec.json or "
                         "check_class_schema.py. I authored an earlier F2b accept at a superseded hash (disclosed "
                         "in N17-R13-02) and a class-binding gate; neither is relied on here. The instrument is my "
                         "own and every headline check is a primary-byte comparison or a canonical-gate run on "
                         "sandbox mutants; prior worker records were read before the instrument was written and are "
                         "cited only as corroboration, never as evidence for the findings."),
        "blindness": ("No other verdict text was copied. The two carriers were extracted verbatim by hash-pinned "
                      "line search, tested against the file's own chain, the sibling C2 schema, the frozen rule_spec "
                      "slots, the pinned rev12 snapshot, and a pre-registered mutant sweep of the canonical gate."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml#55d0a1ea9bda",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/formulation/rule_spec.json#40f9bb9e657b",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
            "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
            "artifacts/worker-017/f2b_rev13_containment/verify.py#%s" % hashes["verify.py"][:12],
            "artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12],
            "artifacts/worker-017/f2b_rev13_containment/controls.json#%s" % hashes["controls.json"][:12],
            "reviews/F2b-review-17-current.json",
            "reviews/F2b-review-22.json",
            "reviews/F2b-containment-normativity-worker-066.json",
            "reviews/F2b-rev29-containment-rebase-worker-066.json",
        ],
        "falsifier": ("Re-run artifacts/worker-017/f2b_rev13_containment/verify.py at the pinned inputs. This "
                      "verdict is falsified if: (a) F2b bytes move or the canonical/mirror copies diverge (pin "
                      "drift, exit 2); (b) either carrier is absent or differs at rev12 55d0a1ea; (c) an "
                      "extension-set reading exists under which E_C2 strictly contains E_C0 given the file's own "
                      "definitions (H1 refuted); (d) explicit text scopes the must_not_conflate denial away from "
                      "the ledger (H2 downgraded); (e) the canonical gate distinguishes repaired from defective "
                      "carriers (blindness finding refuted); (f) any pre-registered mutant control departs from "
                      "its expectation; (g) any pinned input moves during the run."),
        "next_falsifier": ("The owner's rev14 repair: if 'strictly larger' -> 'strictly smaller' and the :152 "
                           "denial is scoped or deleted, a fresh verdict at the new hash should flip B17-R13-01/02 "
                           "to closed; any remaining assertion that E_C2 is strictly larger, or any unscoped "
                           "denial, keeps them open."),
        "artifact_path": "reviews/F2b-rev13-containment-worker-017.json",
        "authority": "worker reviewer verdict only; no gate verdict, validation_status or node state moved",
        "non_claims": ["no node completion", "no gate verdict", "no validation_status=passed",
                       "no canonical artifact edited", "verdict binds b2ab6acb2bbe only"],
    }

    review_path = os.path.join(ROOT, review["artifact_path"])
    jdump(review_path, review)
    review_sha = sha256(review_path)

    # ---------------- outbox events ----------------
    events = [
        {
            "event_id": "w017-%s-f2b-artifact-report" % stamp,
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-017",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "review_evidence",
            "path": "artifacts/worker-017/f2b_rev13_containment/report.json",
            "sha256": hashes["report.json"],
            "validation_status": "unverified",
            "summary": ("Machine adjudication at FROZEN rev29 pin b2ab6acb: %s checks pass, %s controls match "
                        "pre-registration, pins stable; H1 :246 inverted premise and H2 :152 stale denial "
                        "confirmed; canonical gate blind to both."
                        % (review["method"]["checks_passed"], controls["controls_ok"])),
            "evidence_refs": ["artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12],
                              "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                              "artifacts/formulation/FROZEN.json#815e08079aef"],
        },
        {
            "event_id": "w017-%s-f2b-artifact-verdict" % stamp,
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-017",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "review_verdict",
            "path": review["artifact_path"],
            "sha256": review_sha,
            "validation_status": "unverified",
            "summary": "Independent F2b (AF-SCC-C0-VAC-GEN) G-FORM verdict at b2ab6acb: revise 3.0/5, 2 blocking carriers (B17-R13-01 :246, B17-R13-02 :152), 5 non-blocking findings.",
            "evidence_refs": ["%s#%s" % (review["artifact_path"], review_sha[:12]),
                              "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                              "artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12]],
        },
        {
            "event_id": "w017-%s-f2b-review" % stamp,
            "event_type": "review",
            "created_at": now,
            "actor": "worker-017",
            "reviewer": "worker-017",
            "target_id": "F2b",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": ["B17-R13-01", "B17-R13-02"],
            "findings": ["N17-R13-01", "N17-R13-02", "N17-R13-03", "N17-R13-04", "N17-R13-05"],
            "reviewed_sha256": TARGET_SHA,
            "artifact_sha256": TARGET_SHA,
            "artifact_path": review["artifact_path"],
            "artifact_sha256_verdict": review_sha,
            "artifact_revision_read": 13,
            "counts_as_full_schema_verdict": True,
            "counts_as_independent": True,
            "frozen_rev": 29,
            "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                              "%s#%s" % (review["artifact_path"], review_sha[:12]),
                              "artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12]],
            "next_falsifier": review["next_falsifier"],
        },
        {
            "event_id": "w017-%s-f2b-status" % stamp,
            "event_type": "status",
            "created_at": now,
            "actor": "worker-017",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "status": "active",
            "hours": 0.8,
            "summary": ("W017-F2B-REV13-CONTAINMENT-ADJUDICATION-01 complete from the worker side: one bounded "
                        "class-bound task. Independent full-surface G-FORM verdict on F2b at FROZEN rev29 pin "
                        "b2ab6acb: REVISE 3.0/5, two blocking carriers (inverted extension-set premise :246; "
                        "stale containment denial :152), five non-blocking findings. 18/18 checks, 12/12 "
                        "pre-registered gate controls, pre==post pins stable. Both carriers byte-identical to "
                        "pinned rev12 55d0a1ea; rev13 delta binding-only. Worker events cannot move gates; the "
                        "owner's two-line repair and a re-freeze are the unblock path."),
            "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                              "%s#%s" % (review["artifact_path"], review_sha[:12]),
                              "artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12]],
            "next_falsifier": "re-run the instrument at the reviewed hash; a new revision voids this record.",
        },
        {
            "event_id": "w017-%s-f2b-blocker" % stamp,
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-017",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "description": ("G-FORM cannot cleanly accept F2b at b2ab6acb: implication_ledger.forbidden_transfers[0].reason "
                            "(:246) calls C2 a strictly larger extension class while the file's own chain (:238) and the "
                            "C2 sibling (:237) make E_C2 the smallest set, and regularity.must_not_conflate[0] (:152) "
                            "denies containments the same document asserts (:238, :241-244). Both were carried over "
                            "byte-identically from rev12. The canonical structural gate passes the defective bytes and "
                            "does not see either; R16 must gain premise semantics and R06 a content check if a PASS is "
                            "to certify these slots."),
            "needed_to_unblock": ("lead-formulation rev14: 'strictly larger' -> 'strictly smaller' at :246, scope or "
                                  "delete the :152 denial; re-run run_gate_tests.py, re-freeze FROZEN, then one fresh "
                                  "independent verdict at the new hash."),
            "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                              "%s#%s" % (review["artifact_path"], review_sha[:12]),
                              "artifacts/worker-017/f2b_rev13_containment/report.json#%s" % hashes["report.json"][:12]],
        },
    ]

    outbox = os.path.join(ROOT, "comms/outbox/worker-017.jsonl")
    with open(outbox, "a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # ---------------- checkpoint ----------------
    checkpoint = {
        "worker": "worker-017",
        "agent_id": "deepseek-flash-17",
        "at": now,
        "task": {
            "task_id": "W017-F2B-REV13-CONTAINMENT-ADJUDICATION-01",
            "node_id": "F2b",
            "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact": review["artifact_path"],
            "assignment_event": None,
            "self_proposed": True,
            "hours_spent_estimate": 0.8,
            "result": {"verdict": "revise", "score": 3.0,
                       "blocking": ["B17-R13-01", "B17-R13-02"],
                       "non_blocking": ["N17-R13-01", "N17-R13-02", "N17-R13-03", "N17-R13-04", "N17-R13-05"]},
        },
        "reviewed_sha256": TARGET_SHA,
        "outbox_sha256": sha256(outbox),
        "artifacts": {
            "reviews/F2b-rev13-containment-worker-017.json": review_sha,
            "artifacts/worker-017/f2b_rev13_containment/verify.py": hashes["verify.py"],
            "artifacts/worker-017/f2b_rev13_containment/report.json": hashes["report.json"],
            "artifacts/worker-017/f2b_rev13_containment/controls.json": hashes["controls.json"],
            "artifacts/worker-017/f2b_rev13_containment/pins.json": hashes["pins.json"],
        },
        "instrument_results": {
            "checks": "%d/%d" % (report["checks_passed"], report["checks_total"]),
            "controls_matched": controls["controls_ok"],
            "pins_stable_pre_post": pins["stable"],
            "gate_canonical": report["canonical_gate"]["M0_canonical"]["actual"],
            "gate_blind_variants": [k for k, v in controls["mutants"].items() if v["expected"] == "pass"],
            "gate_live_variants": [k for k, v in controls["mutants"].items() if v["expected"] == "fail"],
        },
        "non_claims": ["no node completion", "no validation_status=passed", "no gate verdict",
                       "no canonical artifact edit", "verdict binds b2ab6acb2bbe only"],
    }
    cp_path = os.path.join(ROOT, "runtime/state/w017_checkpoint_f2b_rev13_containment.json")
    jdump(cp_path, checkpoint)
    with open(os.path.join(ROOT, "runtime/state/w017_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

    out = {
        "review": review["artifact_path"], "review_sha256": review_sha,
        "report_sha256": hashes["report.json"], "controls_sha256": hashes["controls.json"],
        "verify_sha256": hashes["verify.py"], "checkpoint": cp_path,
        "checkpoint_sha256": sha256(cp_path),
        "outbox_sha256": sha256(outbox), "events": [e["event_id"] for e in events],
        "checks": review["method"]["checks_passed"], "controls_ok": controls["controls_ok"],
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
