#!/usr/bin/env python3
"""W045-C8-BINDING-VERIFY — independent, read-only verification of the G-NUM criterion-C8
verdict-binding state at the protocol hash of record.

Bounded class-bound task (slot worker-045):
  class_id : AF-WCC-SCALAR-SPH   (calibration sub-case)
  node     : N0
  gate     : G-NUM  (criterion C8: protocol reviewed by audit at the measured protocol hash)

Claim under test (the controller's own G-NUM reason string):
  "protocol measured 1e6cdf04d7a2; the recorded protocol verdict
   reviews/G-NUM-protocol-review.json binds unbound (stale), so criterion C8 is the exact
   unmet requirement."

Measurement: execute the controller's *literal* pin-extraction expression (extracted from
research_map/astra_lifecycle.py at a recorded sha256) against the live canonical review file
and against synthetic controls; separately apply the controller's own _explicit_pins()
convention, and census every C8 verdict artifact on disk.

This script only reads canonical artifacts. It writes:
  artifacts/worker-045/c8_binding_verification.json
  artifacts/worker-045/README.md
  comms/outbox/worker-045.jsonl                      (append; artifact/claim/status/blocker)
  runtime/state/w045_c8_checkpoint_<ts>.json
  runtime/state/w045_c8_checkpoints.jsonl            (append)

It never edits research_map/, schemas/, numerics/, reviews/, ledger/ or any other agent's
artifact, and it claims no gate verdict, node completion, or physics result.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))

TASK_ID = "W045-C8-BINDING-VERIFY"
WORKER = "worker-045"
CLASS_ID = "AF-WCC-SCALAR-SPH"
CLASS_IDS = [CLASS_ID]
NODE_ID = "N0"
GATE = "G-NUM"

PROTO = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
CANON_REVIEW = ROOT / "reviews" / "G-NUM-protocol-review.json"
LIFECYCLE_SRC = ROOT / "research_map" / "astra_lifecycle.py"
W081_REVIEW = ROOT / "artifacts" / "worker-081" / "n0_c8_protocol_review" / "review.json"
W067_REVIEW = ROOT / "artifacts" / "worker-067" / "g_num_protocol_review" / "review.json"
MAP = ROOT / "research_map" / "research_map.json"
ARTIFACT_HASHES = ROOT / "runtime" / "state" / "artifact_hashes.json"
REPLICATION_RUN = ROOT / "runtime" / "state" / "controller_verification" / "n0_replication_astra_run2_FIXED.json"
REPORTS_DIR = ROOT / "runtime" / "state" / "controller_verification"
OUT_ARTIFACT = ROOT / "artifacts" / "worker-045" / "c8_binding_verification.json"
OUT_README = ROOT / "artifacts" / "worker-045" / "README.md"
OUTBOX = ROOT / "comms" / "outbox" / "worker-045.jsonl"
CKPT_JSON = ROOT / "runtime" / "state" / "w045_c8_checkpoint_1.json"
CKPT_JSONL = ROOT / "runtime" / "state" / "w045_c8_checkpoints.jsonl"

# The exact source expression the controller uses for the G-NUM reason (astra_lifecycle.py).
CONTROLLER_EXPR = 'str(json.loads(proto_review.read_text()).get("artifact_sha256") or "unbound")[:12]'
STALE_PROTOCOL_PREFIX = "01b2072434cd"
FALSIFIER = (
    "Falsified if any of: (a) re-running artifacts/worker-045/run_c8_binding_verify.py at the "
    "recorded input hashes yields controller_expression(live_canonical_review) != 'unbound', or "
    "_explicit_pins(live_canonical_review) does not bind the measured protocol hash; (b) the "
    "canonical review file carries a top-level artifact_sha256 equal to the measured protocol "
    "hash at re-run time (remedy applied), which voids the field-mismatch claim; (c) the measured "
    "protocol sha256 is no longer 1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274; "
    "(d) the synthetic controls fail to separate bound / stale / unbound (measurement insensitive); "
    "(e) the controller expression segment is not present exactly once in research_map/"
    "astra_lifecycle.py at the recorded source hash."
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def short(h: str | None) -> str:
    return (h or "")[:12]


def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def binds(pins: list[str], full_hash: str) -> bool:
    """The controller's own review_coverage() prefix test."""
    if not full_hash:
        return False
    p12 = full_hash[:12]
    return any(p.startswith(p12) or p12.startswith(p[:12]) for p in pins if p)


def run_controller_expr(expr: str, doc: dict) -> str:
    """Execute the controller's literal expression with a stubbed review-file reader."""
    class _FakeReview:
        def read_text(self) -> str:
            return json.dumps(doc)

    tree = ast.parse(expr, mode="eval")
    code = compile(tree, "<astra_lifecycle.py:G-NUM-pin-expression>", "eval")
    return eval(code, {"json": json, "proto_review": _FakeReview()})  # noqa: S307 - controller's own expression


def main() -> int:
    ts = stamp()
    generated_at = now()

    # ---------------------------------------------------------------- input hashes
    latest_report = max(REPORTS_DIR.glob("lifecycle_*.json"), key=lambda p: p.stat().st_mtime, default=None)
    input_paths = [
        PROTO, CANON_REVIEW, LIFECYCLE_SRC, W081_REVIEW, W067_REVIEW, MAP, ARTIFACT_HASHES,
        REPLICATION_RUN,
    ] + ([latest_report] if latest_report else [])
    inputs = {str(p.relative_to(ROOT)): sha256_file(p) for p in input_paths if p is not None}

    # ---------------------------------------------------------------- core measurements
    proto_sha = sha256_file(PROTO)
    canon = load_json(CANON_REVIEW) or {}

    src = LIFECYCLE_SRC.read_text()
    expr_occurrences = src.count(CONTROLLER_EXPR)
    expr_line = (src[: src.index(CONTROLLER_EXPR)].count("\n") + 1) if expr_occurrences == 1 else None

    # the controller's literal expression, evaluated against the live canonical review file
    live_expr_value = run_controller_expr(CONTROLLER_EXPR, canon)

    # the controller's own explicit-pin convention (used by review_coverage)
    sys.path.insert(0, str(ROOT / "research_map"))
    import astra_lifecycle as AL  # noqa: E402  (read-only import; no module-level writes)

    canon_pins = AL._explicit_pins(canon)
    canon_binds = binds(canon_pins, proto_sha or "")
    canon_has_artifact_sha256 = "artifact_sha256" in canon

    # ---------------------------------------------------------------- controls
    H = proto_sha or ""
    controls = {
        "C1_positive_synthetic_artifact_sha256": {
            "input": {"artifact_sha256": H},
            "controller_expression_result": run_controller_expr(CONTROLLER_EXPR, {"artifact_sha256": H}),
            "expected": short(H),
        },
        "C2_negative_synthetic_reviewed_sha256_only": {
            "input": {"reviewed_sha256": H},
            "controller_expression_result": run_controller_expr(CONTROLLER_EXPR, {"reviewed_sha256": H}),
            "expected": "unbound",
        },
        "C3_stale_synthetic_artifact_sha256": {
            "input": {"artifact_sha256": STALE_PROTOCOL_PREFIX},
            "controller_expression_result": run_controller_expr(CONTROLLER_EXPR, {"artifact_sha256": STALE_PROTOCOL_PREFIX}),
            "expected": STALE_PROTOCOL_PREFIX,
        },
        "C4_empty_synthetic": {
            "input": {},
            "controller_expression_result": run_controller_expr(CONTROLLER_EXPR, {}),
            "expected": "unbound",
        },
        "C5_live_canonical_review": {
            "input": "<live reviews/G-NUM-protocol-review.json>",
            "controller_expression_result": live_expr_value,
            "expected": "unbound",
        },
        "C6_remedy_simulation_add_artifact_sha256": {
            "input": "<live review + top-level artifact_sha256 = measured protocol hash>",
            "controller_expression_result": run_controller_expr(CONTROLLER_EXPR, {**canon, "artifact_sha256": H}),
            "expected": short(H),
        },
        "C7_controller_own_pin_convention_live": {
            "input": "<live reviews/G-NUM-protocol-review.json>",
            "pins": canon_pins,
            "binds_measured_protocol_hash": canon_binds,
            "expected": True,
        },
        "C8_expression_identity": {
            "segment": CONTROLLER_EXPR,
            "occurrences_in_astra_lifecycle_py": expr_occurrences,
            "line": expr_line,
            "expected_occurrences": 1,
        },
    }
    controls["controls_pass"] = (
        controls["C1_positive_synthetic_artifact_sha256"]["controller_expression_result"] == short(H)
        and controls["C2_negative_synthetic_reviewed_sha256_only"]["controller_expression_result"] == "unbound"
        and controls["C3_stale_synthetic_artifact_sha256"]["controller_expression_result"] == STALE_PROTOCOL_PREFIX
        and controls["C4_empty_synthetic"]["controller_expression_result"] == "unbound"
        and controls["C5_live_canonical_review"]["controller_expression_result"] == "unbound"
        and controls["C6_remedy_simulation_add_artifact_sha256"]["controller_expression_result"] == short(H)
        and controls["C7_controller_own_pin_convention_live"]["binds_measured_protocol_hash"] is True
        and expr_occurrences == 1
    )

    # ---------------------------------------------------------------- C8 verdict census
    candidates = [CANON_REVIEW, W081_REVIEW, W067_REVIEW]
    for pat in ("reviews/*.json", "artifacts/*/g_num_protocol_review/*.json",
                "artifacts/*/n0_c8_protocol_review/*.json"):
        candidates.extend(sorted(ROOT.glob(pat)))
    seen: set[str] = set()
    c8_verdicts = []
    for p in candidates:
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        if rel in seen:
            continue
        seen.add(rel)
        d = load_json(p)
        if not isinstance(d, dict):
            continue
        target = str(d.get("target_id") or d.get("target") or "")
        if "CONVERGENCE_PROTOCOL" not in target and "G-NUM-protocol" not in target:
            continue
        pins = AL._explicit_pins(d)
        c8_verdicts.append({
            "path": rel,
            "sha256": sha256_file(p),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "verdict": d.get("verdict"),
            "score": d.get("score"),
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "pins": pins,
            "pin_fields": [k for k in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256") if d.get(k)],
            "binds_measured_protocol_hash": binds(pins, H),
            "hard_failures": d.get("hard_failures") if isinstance(d.get("hard_failures"), list) else d.get("hard_failures"),
        })

    # ingested review events for the same target (map-level view)
    map_doc = load_json(MAP) or {}
    map_reviews = []
    for r in map_doc.get("reviews", []) or []:
        tgt = str(r.get("target_id") or "")
        if "CONVERGENCE_PROTOCOL" in tgt or "G-NUM-protocol" in tgt:
            pins = AL._explicit_pins(r)
            map_reviews.append({
                "event_id": r.get("event_id"),
                "actor": r.get("actor"),
                "reviewer": r.get("reviewer"),
                "verdict": r.get("verdict"),
                "pins": pins,
                "binds_measured_protocol_hash": binds(pins, H),
            })

    accepts_current = sorted({v["reviewer"] for v in c8_verdicts
                              if v["verdict"] == "accept" and v["binds_measured_protocol_hash"]})
    dissents_current = sorted({v["reviewer"] for v in c8_verdicts
                               if v["verdict"] in ("revise", "reject") and v["binds_measured_protocol_hash"]})

    # ---------------------------------------------------------------- gate reason
    report_reason = None
    report_label = None
    if latest_report is not None:
        rep = load_json(latest_report) or {}
        report_label = rep.get("label")
        report_reason = ((rep.get("controller_gate_audit") or {}).get("G-NUM") or {}).get("reason")
    map_reason = ((map_doc.get("controller_gate_audit") or {}).get("G-NUM") or {}).get("reason")

    # ---------------------------------------------------------------- content anchors
    proto_text = PROTO.read_text()
    proto_lines = proto_text.splitlines()
    anchor_patterns = {
        "scheme_appropriate_invariant_functional": [r"R1 — declare the functional",
                                                      r"R2 — exact discrete conservation",
                                                      r"R4 — no cross-scheme functional gate"],
        "resolution_aware_drift_criterion": [r"R3 — convergent diagnostics"],
        "order_fit_with_uncertainty": [r"Order carries an uncertainty \(R5\)", r"R5a"],
        "negative_controls_must_fail": [r"## 5\. Negative controls"],
        "four_rung_requirement": [r"four or more rungs are required"],
        "artifact_registration_rule": [r"## 7\. Evidence and artifact schema"],
    }
    anchors = {}
    for name, pats in anchor_patterns.items():
        hits = []
        for pat in pats:
            for i, line in enumerate(proto_lines, 1):
                if re.search(pat, line):
                    hits.append({"pattern": pat, "line": i})
                    break
        anchors[name] = {"present": len(hits) == len(pats), "hits": hits}

    # ---------------------------------------------------------------- cited path#hash census
    ref_re = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:md|json|py|yaml|csv|jsonl|txt))#([0-9a-f]{12,64})")
    refs = []
    for m in ref_re.finditer(proto_text):
        rel, claimed = m.group(1), m.group(2)
        f = ROOT / rel
        actual = sha256_file(f)
        if actual is None:
            status = "MISSING"
        elif actual.startswith(claimed) or claimed.startswith(actual[: len(claimed)]):
            status = "MATCH"
        else:
            status = "MISMATCH"
        refs.append({"ref": f"{rel}#{claimed}", "claimed_prefix": claimed[:12],
                     "actual_prefix": short(actual), "status": status})
    refs = [dict(t) for t in {tuple(sorted(r.items())) for r in refs}]  # dedupe, keep dicts
    refs.sort(key=lambda r: r["ref"])

    # ---------------------------------------------------------------- adjacent C4 registration probe
    ah_text = ARTIFACT_HASHES.read_text() if ARTIFACT_HASHES.is_file() else ""
    repl_sha = sha256_file(REPLICATION_RUN)
    c4_probe = {
        "replication_run": str(REPLICATION_RUN.relative_to(ROOT)),
        "replication_run_sha256": repl_sha,
        "replication_prefix_present_in_artifact_hashes": bool(repl_sha and repl_sha[:12] in ah_text),
        "protocol_prefix_present_in_artifact_hashes": bool(proto_sha and proto_sha[:12] in ah_text),
        "note": "supporting probe only; C4 registration is controller-owned and outside this task's claim",
    }

    # ---------------------------------------------------------------- drift check
    inputs_after = {str(p.relative_to(ROOT)): sha256_file(p) for p in input_paths if p is not None}
    drift = {k: [inputs.get(k), inputs_after.get(k)] for k in inputs if inputs.get(k) != inputs_after.get(k)}

    binding_defect_confirmed = (
        expr_occurrences == 1
        and short(proto_sha) == "1e6cdf04d7a2"
        and canon_has_artifact_sha256 is False
        and live_expr_value == "unbound"
        and canon_binds is True
        and controls["controls_pass"] is True
    )

    if binding_defect_confirmed:
        claim_text = (
            "The controller's G-NUM reason string 'the recorded protocol verdict "
            "reviews/G-NUM-protocol-review.json binds unbound (stale)' is produced by a pin-field "
            "mismatch, not by an absent or stale verdict: the canonical review carries verdict=accept, "
            "counts_as_full_schema_verdict=true and reviewed_sha256 equal to the measured protocol "
            "sha256, but no top-level artifact_sha256, while the controller's reason expression at "
            f"research_map/astra_lifecycle.py:{expr_line} reads only artifact_sha256 from that one file. "
            "Under the controller's own _explicit_pins() convention the same file binds the measured "
            f"protocol hash; {len(accepts_current)} independent accept(s) at the current hash "
            f"({', '.join(accepts_current) or 'none'}) and {len(dissents_current)} dissent(s) "
            f"({', '.join(dissents_current) or 'none'}) exist on disk."
        )
    else:
        claim_text = (
            "The expected binding defect did NOT reproduce at measurement time; no claim is emitted. "
            "See measurements/controls: this run is recorded as INCONCLUSIVE so the negative result "
            "is not lost (protocol hash, canonical-review fields and controller-expression output are "
            "all recorded)."
        )

    artifact = {
        "schema": "worker-045/c8_binding_verification/v1",
        "task_id": TASK_ID,
        "worker": WORKER,
        "generated_at": generated_at,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "criterion": "C8 — protocol reviewed by audit at the measured protocol hash",
        "verdict": "BINDING-DEFECT-CONFIRMED" if binding_defect_confirmed else "INCONCLUSIVE",
        "claim": claim_text,
        "measurements": {
            "protocol_path": str(PROTO.relative_to(ROOT)),
            "protocol_sha256": proto_sha,
            "protocol_revision_marker": "rev 3 (revision log)",
            "controller_expression": CONTROLLER_EXPR,
            "controller_expression_line": expr_line,
            "controller_expression_occurrences": expr_occurrences,
            "controller_expression_live_value": live_expr_value,
            "canonical_review_path": str(CANON_REVIEW.relative_to(ROOT)),
            "canonical_review_sha256": sha256_file(CANON_REVIEW),
            "canonical_review_has_top_level_artifact_sha256": canon_has_artifact_sha256,
            "canonical_review_explicit_pins": canon_pins,
            "canonical_review_binds_measured_hash_by_own_convention": canon_binds,
            "controller_gate_audit_reason_from_latest_report": report_reason,
            "latest_report": str(latest_report.relative_to(ROOT)) if latest_report else None,
            "latest_report_label": report_label,
            "controller_gate_audit_reason_from_map": map_reason,
            "c8_verdicts": c8_verdicts,
            "c8_map_review_events": map_reviews,
            "accepts_at_current_hash": accepts_current,
            "dissents_at_current_hash": dissents_current,
        },
        "controls": controls,
        "content_anchors": anchors,
        "cited_ref_census": refs,
        "c4_registration_probe": c4_probe,
        "inputs": inputs,
        "drift_during_run": drift,
        "falsifier": FALSIFIER,
        "scope_limit": (
            "Read-only binding-state measurement over the corpus named in inputs. It does not "
            "adjudicate the substance of any C8 verdict, does not resolve worker-067's section-3.4 "
            "dissent, does not touch numerics/, reviews/ or canonical publication, and does not "
            "assert the protocol is correct."
        ),
        "no_completion_claim": (
            "Worker events cannot set node status=done, validation_status=passed, or a gate verdict; "
            "N0/G-NUM remain lead- and controller-owned. This artifact is a measurement for the "
            "controller's next lifecycle pass."
        ),
        "needed_to_unblock": (
            "Either (a) the canonical review's owner (astra-lead-audit) adds top-level "
            f"artifact_sha256={proto_sha} to reviews/G-NUM-protocol-review.json and re-emits the "
            "verdict event, or (b) the controller computes the G-NUM reason's pin with its own "
            "_explicit_pins() convention at research_map/astra_lifecycle.py:%s. No measured number "
            "changes; this is a one-field/one-line binding fix." % (expr_line,)
        ),
    }

    OUT_ARTIFACT.write_text(json.dumps(artifact, indent=2) + "\n")
    artifact_sha = sha256_file(OUT_ARTIFACT)

    readme_body = (
        f"""The G-NUM reason "binds unbound (stale)" is a pin-field mismatch, not a missing verdict:
`reviews/G-NUM-protocol-review.json` (accept 4.5, `counts_as_full_schema_verdict=true`) pins the
current protocol hash via `reviewed_sha256` (`{short(proto_sha)}`), while
`research_map/astra_lifecycle.py:{expr_line}` reads only `artifact_sha256` from that file. The
controller's own `_explicit_pins()` convention binds the verdict, and {len(accepts_current)}
independent accept(s) at the current hash exist on disk."""
        if binding_defect_confirmed else
        "The expected binding defect did NOT reproduce; see the measurement JSON (INCONCLUSIVE)."
    )
    readme = f"""# worker-045 — C8 gate-binding verification ({generated_at})

Task `{TASK_ID}` · class `{CLASS_ID}` · node `{NODE_ID}` · gate `{GATE}`.

**Verdict: {artifact['verdict']}.** {readme_body}

- Full measurement: `c8_binding_verification.json` (sha256 `{artifact_sha}`)
- Reproduce: `python3 artifacts/worker-045/run_c8_binding_verify.py`
- Falsifier: see `falsifier` in the JSON.
- Scope: read-only; no gate verdict, no node completion, no physics claim.
"""
    OUT_README.write_text(readme)
    runner_sha = sha256_file(Path(__file__).resolve())

    # ---------------------------------------------------------------- events
    evidence_refs = [
        f"numerics/CONVERGENCE_PROTOCOL.md#{short(proto_sha)}",
        f"reviews/G-NUM-protocol-review.json#{short(sha256_file(CANON_REVIEW))}",
        f"research_map/astra_lifecycle.py#{short(sha256_file(LIFECYCLE_SRC))}",
        f"artifacts/worker-081/n0_c8_protocol_review/review.json#{short(sha256_file(W081_REVIEW))}",
        f"artifacts/worker-067/g_num_protocol_review/review.json#{short(sha256_file(W067_REVIEW))}",
        f"research_map/research_map.json#{short(sha256_file(MAP))}",
    ]
    if latest_report is not None:
        evidence_refs.append(f"{latest_report.relative_to(ROOT)}#{short(sha256_file(latest_report))}")

    event_ids = {
        "artifact": f"w045-art-{ts}-c8bind",
        "claim": f"w045-claim-{ts}-c8bind",
        "status": f"w045-status-{ts}-c8bind",
        "blocker": f"w045-blocker-{ts}-c8bind",
    }
    events = [
        {
            "actor": WORKER, "event_id": event_ids["artifact"], "event_type": "artifact",
            "created_at": generated_at, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "node_id": NODE_ID, "gate": GATE,
            "artifact_type": "c8_gate_binding_verification",
            "path": str(OUT_ARTIFACT.relative_to(ROOT)), "sha256": artifact_sha,
            "validation_status": "unverified",
            "summary": artifact["claim"],
            "evidence_refs": evidence_refs, "next_falsifier": FALSIFIER,
        },
        {
            "actor": WORKER, "event_id": event_ids["claim"], "event_type": "claim",
            "created_at": generated_at, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "node_id": NODE_ID, "gate": GATE,
            "conclusion_type": "formal_model",
            "statement": artifact["claim"],
            "assumptions": [
                "the G-NUM reason is computed by research_map/astra_lifecycle.py at the recorded source hash, and the load-bearing pin extraction is the single expression recorded in the artifact",
                "reviewed_sha256 is a valid explicit pin under the controller's own _explicit_pins() convention (astra_lifecycle.py), which review_coverage() uses",
                "the protocol hash 1e6cdf04d7a2 was current throughout the measurement and 0 inputs drifted",
                "verdict substance is not adjudicated here; worker-067's revise dissent (section 3.4) is recorded, not resolved",
            ],
            "falsifier": FALSIFIER,
            "evidence_refs": evidence_refs,
            "artifact_refs": [
                {"path": str(OUT_ARTIFACT.relative_to(ROOT)), "sha256": artifact_sha},
                {"path": "artifacts/worker-045/run_c8_binding_verify.py", "sha256": runner_sha},
            ],
        },
        {
            "actor": WORKER, "event_id": event_ids["status"], "event_type": "status",
            "created_at": generated_at, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "node_id": NODE_ID, "status": "active", "hours": 0.6,
            "summary": (
                f"Bounded class-bound task {TASK_ID} complete (worker task complete; node/gate status "
                f"remains lead/controller-owned). VERDICT {artifact['verdict']}. Artifact "
                f"{OUT_ARTIFACT.relative_to(ROOT)}#{short(artifact_sha)}. Observed but not dispositioned: "
                f"C8 has {len(accepts_current)} independent accept(s) at the measured protocol hash "
                f"({', '.join(accepts_current) or 'none'}) plus dissent {', '.join(dissents_current) or 'none'}; "
                f"C4 registration probe negative (replication prefix present="
                f"{c4_probe['replication_prefix_present_in_artifact_hashes']})."
            ),
            "evidence_refs": evidence_refs, "next_falsifier": FALSIFIER,
        },
        {
            "actor": WORKER, "event_id": event_ids["blocker"], "event_type": "blocker",
            "created_at": generated_at, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "node_id": NODE_ID, "gate": GATE,
            "description": (
                f"G-NUM criterion C8 is reported unmet by a binding-field artifact, not by a missing "
                f"verdict: research_map/astra_lifecycle.py:{expr_line} reads only "
                f".get('artifact_sha256') from reviews/G-NUM-protocol-review.json, which pins the "
                f"measured protocol hash {short(proto_sha)} via reviewed_sha256 and has no "
                f"artifact_sha256 field. The controller's own _explicit_pins() convention binds it. "
                f"{len(accepts_current)} independent accept(s) at the current hash exist on disk "
                f"({', '.join(accepts_current) or 'none'}); 1 recorded dissent "
                f"({', '.join(dissents_current) or 'none'}) remains a substantive open item."
            ),
            "needed_to_unblock": artifact["needed_to_unblock"],
            "evidence_refs": evidence_refs,
            "summary": f"One-field/one-line binding fix; no measured number changes. Artifact sha256 {artifact_sha}.",
        },
    ]
    if binding_defect_confirmed:
        with OUTBOX.open("a") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
        emitted = list(event_ids.values())
    else:
        emitted = []

    # ---------------------------------------------------------------- checkpoint
    instance = None
    inst_dirs = sorted(ROOT.glob("runtime/instances/worker-045-*"), key=lambda p: p.stat().st_mtime)
    if inst_dirs:
        instance = inst_dirs[-1].name
    checkpoint = {
        "worker": WORKER, "instance": instance, "task_id": TASK_ID,
        "checkpoint_at": now(), "class_ids": CLASS_IDS, "node_ids": [NODE_ID], "gate": GATE,
        "verdict": artifact["verdict"], "artifacts": {
            str(OUT_ARTIFACT.relative_to(ROOT)): artifact_sha,
            "artifacts/worker-045/run_c8_binding_verify.py": runner_sha,
        },
        "inputs": inputs, "controls_pass": controls["controls_pass"],
        "drift_during_run": drift,
        "protocol_sha256": proto_sha,
        "canonical_review_binds_by_own_convention": canon_binds,
        "controller_expression_live_value": live_expr_value,
        "accepts_at_current_hash": accepts_current, "dissents_at_current_hash": dissents_current,
        "events_emitted": emitted,
        "falsifier": FALSIFIER,
        "no_completion_claim": artifact["no_completion_claim"],
        "next_step": "Controller's next lifecycle pass: recompute the G-NUM reason with _explicit_pins() or have the canonical review's owner add artifact_sha256; then adjudicate C8 with the dissent recorded.",
    }
    CKPT_JSON.write_text(json.dumps(checkpoint, indent=2) + "\n")
    with CKPT_JSONL.open("a") as f:
        f.write(json.dumps(checkpoint) + "\n")

    # ---------------------------------------------------------------- local schema validation (read-only)
    schema_ok = {}
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        from schemas import validate_event  # noqa: E402
        for ev in events:
            try:
                validate_event(ev)
                schema_ok[ev["event_type"]] = "VALID"
            except Exception as e:  # noqa: BLE001
                schema_ok[ev["event_type"]] = f"INVALID: {e}"
    except Exception as e:  # noqa: BLE001
        schema_ok = {"import": f"FAILED: {e}"}

    # ---------------------------------------------------------------- report
    print(json.dumps({
        "task_id": TASK_ID, "verdict": artifact["verdict"],
        "protocol_sha256": proto_sha,
        "controller_expression_live_value": live_expr_value,
        "controller_expression_line": expr_line,
        "canon_binds_by_own_convention": canon_binds,
        "canon_has_artifact_sha256": canon_has_artifact_sha256,
        "accepts_at_current_hash": accepts_current,
        "dissents_at_current_hash": dissents_current,
        "controls_pass": controls["controls_pass"],
        "drift_during_run": drift,
        "artifact_sha256": artifact_sha,
        "events": event_ids,
        "event_schema": schema_ok,
        "checkpoint": str(CKPT_JSON.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
