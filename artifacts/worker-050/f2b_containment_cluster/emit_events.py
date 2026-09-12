#!/usr/bin/env python3
"""Emit the W050-F2B-CONTAINMENT-CLUSTER-05 events + checkpoint.

Writes (append-only, idempotent by event_id):
  comms/outbox/worker-050.jsonl                    (upward events)
  runtime/state/w050_checkpoint_f2b_containment.json
  runtime/state/w050_checkpoints.jsonl             (append one line)

Read-only on every canonical artifact. No map/ledger/schema/detector write.
"""
import datetime
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-050.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT = os.path.join(STATE, "w050_checkpoint_f2b_containment.json")
CKPT_LOG = os.path.join(STATE, "w050_checkpoints.jsonl")

NOW = datetime.datetime.now().astimezone()
TS = NOW.strftime("%Y-%m-%dT%H:%M:%S%z")
TS = TS[:-2] + ":" + TS[-2:]
PREFIX = "w050-f2bcluster-" + NOW.strftime("%Y%m%dT%H%M%S")

PINS = {
    "f2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "f2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "frozen": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "vocab": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}


def sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build_manifest():
    files = ["report.json", "review_binding_table.json", "audit_f2b_containment.py",
             "README.md", "emit_events.py"]
    man = {
        "task_id": "W050-F2B-CONTAINMENT-CLUSTER-05",
        "self_reference": ("this manifest cannot contain its own post-write sha256; its hash "
                           "is recorded in the artifact event that publishes it and in the "
                           "checkpoint"),
        "files": {f: sha("artifacts/worker-050/f2b_containment_cluster/" + f) for f in files},
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
        fh.write("\n")
    return man


def main():
    rep = json.load(open(os.path.join(OUT, "report.json")))
    raw_hf = sum(len(r.get("hard_failure_ids") or []) for r in rep["review_binding"]
                 if r.get("binding") == "current" and r.get("verdict") == "revise")
    adverse_curr = len([r for r in rep["review_binding"]
                        if r.get("binding") == "current" and r.get("verdict") == "revise"])
    accept_curr = len([r for r in rep["review_binding"]
                       if r.get("binding") == "current" and r.get("verdict") == "accept"])
    man = build_manifest()
    base = "artifacts/worker-050/f2b_containment_cluster"
    h = {f: sha(base + "/" + f) for f in
         ["report.json", "review_binding_table.json", "audit_f2b_containment.py",
          "README.md", "manifest.json"]}
    ref = {k: "%s/%s#sha256:%s" % (base, k, v) for k, v in h.items()}

    events = [
        {
            "event_id": PREFIX + "-artifact-report", "event_type": "artifact",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "measurement_report",
            "path": base + "/report.json", "sha256": h["report.json"],
            "validation_status": "unverified",
            "note": ("10/10 pre-registered predicates hold, exit 0, no input drift. The six "
                     "adverse F2b rev13 verdicts dedupe to 3 defects: D1 live line-152 "
                     "containment denial vs same-file chain (3 reviewers), D2 line-246 "
                     "inverted premise (5 reviewers), D3 F0/VOCAB conclusion-token "
                     "divergence (1 reviewer); 7 adverse/0 accepts bound to b2ab6acb."),
            "evidence_refs": [
                "schemas/af_scc_c0_vacuum.yaml#" + PINS["f2b"][:12],
                "schemas/af_scc_c2_vacuum.yaml#" + PINS["f2a"][:12],
                "artifacts/formulation/FROZEN.json#" + PINS["frozen"][:12],
                "artifacts/formulation/VOCAB_ALIASES.json#" + PINS["vocab"][:12],
            ],
            "falsifier": ("F4: any pinned input moves (exit 3, measurement void); F1: D1 "
                          "carrier absent at the pinned bytes; F2: a chain reading with E_C2 "
                          "largest; F3: an F0/VOCAB revision containing the F2b token."),
        },
        {
            "event_id": PREFIX + "-artifact-bindtable", "event_type": "artifact",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "review_binding_census",
            "path": base + "/review_binding_table.json", "sha256": h["review_binding_table.json"],
            "validation_status": "unverified",
            "note": ("Per-verdict binding census at F2b b2ab6acb: 7 adverse verdicts bound to "
                     "the current pin (worker-066 x2, 017, 018, 053, 075, 035), 0 accepts "
                     "bound to it; worker-001's accept cites 177a5f0019b1 (superseded). Each "
                     "row carries the review-file sha256."),
            "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#" + PINS["f2b"][:12]],
            "falsifier": ("A verdict counted as current whose cited sha256 is not b2ab6acb, or "
                          "an accept bound to b2ab6acb not counted."),
        },
        {
            "event_id": PREFIX + "-artifact-runner", "event_type": "artifact",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "reproducible_runner",
            "path": base + "/audit_f2b_containment.py", "sha256": h["audit_f2b_containment.py"],
            "validation_status": "unverified",
            "note": ("Deterministic stdlib+PyYAML checker; pins all inputs, exits 3 on drift, "
                     "2 if any pre-registered predicate fails, 0 if all hold; rebuilds "
                     "report.json + review_binding_table.json."),
            "evidence_refs": [ref["report.json"]],
            "falsifier": "Re-run produces a different report from the same pinned inputs.",
        },
        {
            "event_id": PREFIX + "-artifact-readme", "event_type": "artifact",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "documentation",
            "path": base + "/README.md", "sha256": h["README.md"],
            "validation_status": "unverified",
            "note": "Claims, pins, per-defect evidence, dedup table, limits, falsifiers F1-F5, re-run command.",
            "evidence_refs": [ref["report.json"]],
            "falsifier": "F1-F5 in the README.",
        },
        {
            "event_id": PREFIX + "-artifact-manifest", "event_type": "artifact",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "manifest",
            "path": base + "/manifest.json", "sha256": h["manifest.json"],
            "validation_status": "unverified",
            "note": "Hashes of every artifact in this bundle after the final run.",
            "evidence_refs": [ref["report.json"]],
            "falsifier": "Any listed file whose measured bytes differ from the manifest hash.",
        },
        {
            "event_id": PREFIX + "-claim", "event_type": "claim",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "conclusion_type": "numerical_evidence",
            "statement": (
                "Artifact-and-checker measurement at the FROZEN rev29 pin "
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (F2a control "
                "e9a27996dfd3, FROZEN 815e08079aef, F0 0abb9ed8a961, VOCAB 46cd9f1eb534; no "
                "drift start-to-exit): the six adverse F2b rev13 verdicts dedupe to exactly "
                "three defects - (D1) the live denial 'No containment with C2 or C0 is "
                "asserted here' at regularity.must_not_conflate[0] line 152 contradicts the "
                "same file's asserted chain at line 238 and the corrected F2a sibling, "
                "flagged independently by 3 reviewers; (D2) the inverted premise 'C2 is a "
                "strictly larger extension class' at "
                "implication_ledger.forbidden_transfers[0].reason line 246, flagged by 5 "
                "reviewers, whose conclusion and prohibition are nevertheless correct; (D3) "
                "the conclusion token scc_c0_future_inextendibility is VOCAB_ALIASES-canonical "
                "but absent from the F0 declared allowed vocabulary, which holds its alias. "
                "At this pin 7 adverse verdicts are bound to b2ab6acb and 0 accepts are, so "
                "no binding accept exists for F2b at the rev13 publication; both carriers "
                "are also present in the rev12 snapshot 55d0a1ea. No truth value is assigned "
                "to any conjecture and no gate verdict is claimed."),
            "assumptions": [
                "the pinned bytes are the authoritative rev13 publication (FROZEN rev29 declares them)",
                "the file's own asserted containment chain is the comparison basis; the set-theoretic claim is not re-derived",
                "the rev12 carry-over uses a third-party snapshot whose bytes hash to the rev12 pin cited by the rev12 verdicts",
            ],
            "falsifier": ("F1/F2/F3 as stated in report.json: a carrier absent at the pinned "
                          "bytes, a chain reading with E_C2 largest, or an F0/VOCAB revision "
                          "containing the F2b token refutes the corresponding defect; F4 "
                          "input drift voids the whole measurement."),
            "evidence_refs": [
                ref["report.json"], ref["review_binding_table.json"],
                "schemas/af_scc_c0_vacuum.yaml#" + PINS["f2b"][:12],
                "schemas/af_scc_c2_vacuum.yaml#" + PINS["f2a"][:12],
            ],
            "artifact_refs": [ref["report.json"], ref["review_binding_table.json"],
                              ref["audit_f2b_containment.py"]],
        },
        {
            "event_id": PREFIX + "-review", "event_type": "review",
            "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "target_id": "schemas/af_scc_c0_vacuum.yaml",
            "target_sha256": PINS["f2b"],
            "reviewer": "worker-050", "verdict": "revise", "score": 3.0,
            "independence": ("worker-050 authored none of the schemas, FROZEN, the taxonomies, "
                             "the registry or the cited reviews; the census read the adverse "
                             "verdicts rather than being blind to them, which is disclosed; "
                             "the carrier checks are mechanical at the pinned bytes."),
            "hard_failures": [
                {"id": "W050-F2B-D1", "severity": "blocking",
                 "carrier": "regularity.must_not_conflate[0]", "line": 152,
                 "finding": ("live containment denial is false of the same document and of the "
                             "corrected F2a sibling; 3 independent reviewers agree")},
                {"id": "W050-F2B-D2", "severity": "blocking",
                 "carrier": "implication_ledger.forbidden_transfers[0].reason", "line": 246,
                 "finding": ("inverted premise contradicts the file's own containment chain; "
                             "5 independent reviewers agree; the row's conclusion is correct")},
                {"id": "W050-F2B-D3", "severity": "high",
                 "carrier": "conclusion.conclusion_type",
                 "finding": ("VOCAB_ALIASES-canonical token absent from the F0 declared allowed "
                             "vocabulary; cross-artifact frozen vocabulary divergence")},
            ],
            "findings": [
                "The cluster is deduplicated: %d raw hard-failure entries across %d adverse verdicts bound to the current pin are 3 defects; D1 and D2 share the same root" % (raw_hf, adverse_curr) + " (the file asserts a containment chain in the ledger while its normative regularity slot denies containment and its forbidden-transfer reason states the ordering backwards).",
                "The F2a sibling at the same publication carries the corrected wording; the asymmetry is the strongest single-line evidence that F2b's carriers are stale, not deliberate.",
                "The four one_way_entailments rows are orientation-consistent, so the repair surface is exactly two lines plus the token divergence.",
                "7 adverse / 0 accepts bound to b2ab6acb; the criterion is unmet at this pin regardless of verdict arithmetic, and a fix must bump the revision and void the current advisory verdicts.",
            ],
            "evidence_refs": [ref["report.json"], ref["review_binding_table.json"]],
            "falsifier": ("A pinned revision with either carrier fixed, or an independent reader "
                          "showing the F2b denial/ordering is consistent with its chain."),
        },
    ]

    # --- checkpoint ----------------------------------------------------------
    artifacts = {base + "/" + f: v for f, v in h.items()}
    ckpt = {
        "checkpoint_id": PREFIX,
        "actor": "worker-050",
        "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "sibling_control_class": "AF-SCC-C2-VAC-GEN",
        "created_at": TS,
        "inputs": PINS,
        "counts": {
            "adverse_verdicts_bound_to_pin": adverse_curr,
            "accepts_bound_to_pin": accept_curr,
            "raw_hard_failure_entries": raw_hf,
            "distinct_defects": 3,
            "blocking_defects": 2,
            "checks_passed": 10, "checks_total": 10,
        },
        "defects": [{"id": d["id"], "severity": d["severity"], "carrier": d["carrier"],
                     "reviewers": len(d["independent_reviewers"])} for d in rep["defects"]],
        "artifacts": artifacts,
        "events_emitted": [e["event_id"] for e in events] ,
        "falsifier": ("F4: any pinned input moves -> void; F1/F2/F3: carrier absent, chain "
                      "reading reversed, or F0/VOCAB revision containing the token -> the "
                      "corresponding defect refuted."),
        "next_step": ("Formulation lead: fix the two F2b carriers (align must_not_conflate[0] "
                      "with the chain; state the forbidden-transfer premise in chain "
                      "orientation) plus the token decision in one revision bump; then re-run "
                      "this audit at the new pin. Audit lead: use report.json as the F2b defect "
                      "list for astra-life05-verify-gform-r3."),
        "authority": ("Worker measurement and review input only. No gate verdict, no "
                      "validation_status=passed, no node completion, no canonical write."),
        "not_a_gate_verdict": True,
    }
    with open(CKPT, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1)
        fh.write("\n")
    ckpt_sha = sha("runtime/state/w050_checkpoint_f2b_containment.json")
    ckpt_rel = "runtime/state/w050_checkpoint_f2b_containment.json"

    events.append({
        "event_id": PREFIX + "-status", "event_type": "status",
        "created_at": TS, "actor": "worker-050", "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN", "status": "active", "hours": 0.4,
        "summary": ("CHECKPOINT + EXIT. No assignment card existed in comms/inbox/worker-050 "
                    "for this instance; one self-selected bounded class-bound task was taken: "
                    "W050-F2B-CONTAINMENT-CLUSTER-05 = independent reconciliation of the "
                    "adverse F2b rev13 verdict cluster at FROZEN rev29 pin b2ab6acb. Result: "
                    "10/10 checks pass, no drift; 7 adverse / 0 accept verdicts bound to the "
                    "pin; %d raw hard-failure entries dedupe to 3 defects (2 blocking carriers " % raw_hf +
                    "+ 1 frozen vocabulary divergence); both carriers carried over from rev12; "
                    "F2a sibling shows the corrected wording F2b lacks. No map, schema, ledger, "
                    "review, detector or gate state was edited; no gate verdict claimed."),
        "artifact": ckpt_rel, "artifact_sha256": ckpt_sha,
        "evidence_refs": [ref["report.json"], ref["review_binding_table.json"],
                          ckpt_rel + "#sha256:" + ckpt_sha[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + PINS["f2b"][:12]],
        "next_falsifier": ("Re-run audit_f2b_containment.py after any F2b/F0/VOCAB movement; "
                           "exit 3 voids, exit 2 means a defect was refuted, exit 0 with the "
                           "carriers still present reconfirms the defect list at the new pin."),
    })

    # idempotent append to outbox
    existing = set()
    if os.path.exists(OUTBOX):
        with open(OUTBOX, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    written = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, sort_keys=False) + "\n")
            written += 1
    # append checkpoint log (idempotent by checkpoint_id)
    seen = False
    if os.path.exists(CKPT_LOG):
        with open(CKPT_LOG, "r", encoding="utf-8") as fh:
            for line in fh:
                if PREFIX in line:
                    seen = True
                    break
    ckpt["events_emitted"] = [e["event_id"] for e in events]
    if not seen:
        with open(CKPT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print("emitted_events=%d skipped=%d checkpoint=%s sha256=%s" %
          (written, len(events) - written, ckpt_rel, ckpt_sha))


if __name__ == "__main__":
    main()
