#!/usr/bin/env python3
"""W064-GNUM-GUARD-CHANNELS-02: channel-closure test for numerics/gates.py::_protocol_review.

Question: at the live bytes, can any protocol-conformant event that the controller or a
review owner could legally append discharge a counted dissent and clear the C8 contest
WITHOUT changing numerics/gates.py?

Read-only: the live gate module is never imported from its canonical path; a hash-pinned
copy is imported with bytecode writing disabled, and no canonical file is written.

Exit 0 iff every preregistered expectation holds.  Exit 2 on a live-pin move.
Exit 3 on a falsified expectation.  Exit 4 if a negative control clears contest.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"
PIN_GATES = HERE / "pinned" / "gates_fcd1d70991b6.py"
PIN_PROTO = HERE / "pinned" / "CONVERGENCE_PROTOCOL_1e6cdf04d7a2.md"
PRIOR = ROOT / "artifacts" / "worker-064" / "gnum_guard" / "w064_gnum_guard_census.py"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"
GATES_REL = "numerics/gates.py"
EXPECT_GATES_SHA = "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
EXPECT_PROTO_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
SNAP = RAW / "events_snapshot.jsonl"

ACCEPT_ID = "w081-20260912T002140-c8-review"      # accepted, then prose-withdrawn
WITHHELD_DISSENTS = ["w067-review-gnum-protocol-r3-20260912T002256",   # F1
                     "w081-2026-09-12T00:29:19+0800-f1-review"]        # F1'
N0_DISSENTS = ["w067-provledger-20260912T005149-20-review",
               "w042-n0-stoprule-01-review",
               "w081-20260912T005818-pinsplit-review"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_events() -> list[dict]:
    out = []
    for line in SNAP.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def ev(eid, etype, actor, at, **kw) -> dict:
    d = {"event_id": eid, "event_type": etype, "actor": actor, "created_at": at}
    d.update(kw)
    return d


def proto_ref():
    return f"{PROTOCOL_REL}#{EXPECT_PROTO_SHA}"


def channel_events() -> list[tuple[str, dict]]:
    """One synthesized protocol-conformant event per candidate disposition channel."""
    return [
        ("A1-status-disposition", ev(
            "w064-sim-a1-status-disposition", "status", "astra", "2026-09-12T01:14:00+08:00",
            node_id="N0", status="done", gate="G-NUM", hours=0.1,
            summary=("G-NUM C8 disposition of record: worker-067 F1 and worker-081 F1' are "
                     "recorded DISCHARGED by supersession of the evidence basis."),
            evidence_refs=[proto_ref(), "reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae"],
            next_falsifier="any live revise/reject at the current protocol hash reopens the contest")),
        ("A2-gate-pass", ev(
            "w064-sim-a2-gate-pass", "gate", "astra", "2026-09-12T01:14:01+08:00",
            gate_id="G-NUM", scope="N0", verdict="pass", node_id="N0",
            criteria="C8 protocol review: dissents discharged by supersession",
            evidence_refs=[proto_ref(), "reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae"])),
        ("A3-gate-discharge-list", ev(
            "w064-sim-a3-gate-discharge-list", "gate", "astra", "2026-09-12T01:14:02+08:00",
            gate_id="G-NUM", scope="G-NUM-protocol", verdict="pass", node_id="N0",
            discharges=WITHHELD_DISSENTS,
            evidence_refs=[proto_ref()])),
        ("A4-review-rebind", ev(
            "w064-sim-a4-review-rebind", "review", "astra-lead-audit", "2026-09-12T01:14:03+08:00",
            target_id="G-NUM-protocol", reviewer="astra-lead-audit", verdict="accept", score=4.5,
            reviewed_sha256=EXPECT_PROTO_SHA, node_id="N0",
            evidence_refs=[proto_ref(), "reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae"],
            findings=["rebind of the r4 accept with the protocol hash in evidence_refs"])),
        ("A5-review-discharge-carrier", ev(
            "w064-sim-a5-review-discharge-carrier", "review", "astra", "2026-09-12T01:14:04+08:00",
            target_id="G-NUM-protocol", reviewer="astra", verdict="accept", score=4.5,
            reviewed_sha256=EXPECT_PROTO_SHA, node_id="N0", discharges=WITHHELD_DISSENTS,
            evidence_refs=[proto_ref()],
            findings=["explicit fail-closed discharge list on a later same-hash accept"])),
        ("A6-artifact-disposition", ev(
            "w064-sim-a6-artifact-disposition", "artifact", "astra", "2026-09-12T01:14:05+08:00",
            node_id="N0", path="reviews/G-NUM-protocol-r4-adjudication.json",
            sha256="b836902fa4ae0e57af52d408c09ad03b4a2023b038d8d0cb186c45f8f69ad354",
            validation_status="unverified", evidence_refs=[proto_ref()])),
        ("A7-astra-structured-withdrawal", ev(
            "w064-sim-a7-astra-structured-withdrawal", "status", "astra", "2026-09-12T01:14:06+08:00",
            node_id="N0", status="done", withdraws_event_ids=[ACCEPT_ID],
            summary="structured withdrawal of the prose-withdrawn accept",
            evidence_refs=[proto_ref()])),
        ("A8-author-structured-withdrawal", ev(
            "w064-sim-a8-author-structured-withdrawal", "status", "worker-067",
            "2026-09-12T01:14:07+08:00", node_id="N0", status="done",
            withdraws_event_ids=[WITHHELD_DISSENTS[0]],
            summary="author withdrawal of the F1 dissent",
            evidence_refs=[proto_ref()])),
        ("A9-review-discharge-carrier-thirdparty", ev(
            "w064-sim-a9-review-discharge-carrier-thirdparty", "review", "worker-999",
            "2026-09-12T01:14:08+08:00", target_id="G-NUM-protocol", reviewer="worker-999",
            verdict="accept", score=4.0, reviewed_sha256=EXPECT_PROTO_SHA, node_id="N0",
            discharges=WITHHELD_DISSENTS, evidence_refs=[proto_ref()])),
    ]


def carrier(discharges, *, sha=EXPECT_PROTO_SHA, created="2026-09-12T01:14:10+08:00",
            reviewer="astra", eid="w064-sim-carrier", refs_stale=False) -> dict:
    e = ev(eid, "review", reviewer, created, target_id="G-NUM-protocol", reviewer=reviewer,
           verdict="accept", score=4.5, node_id="N0", discharges=discharges,
           evidence_refs=[proto_ref()])
    if sha is not None:
        e["reviewed_sha256"] = sha
    else:
        e.pop("reviewed_sha256", None)
        e["evidence_refs"] = ["reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae"]
    if refs_stale:
        e["evidence_refs"] = [f"{PROTOCOL_REL}#{'0' * 64}"]
    return e


def run_live(gates, events, proto_sha):
    return gates._protocol_review(events, proto_sha)


def norm(d: dict) -> dict:
    return {
        "reviewed": bool(d.get("reviewed")),
        "accepts": sorted(d.get("accepting_reviews", [])),
        "dissents": sorted(x["event_id"] for x in d.get("dissenting_reviews", [])),
        "contest": bool(d.get("contest")),
        "advisory": len(d.get("advisory_reviews_at_other_hashes", [])),
    }


def main() -> int:
    ts_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    gates_sha_before = sha256_file(ROOT / GATES_REL)
    proto_sha_before = sha256_file(ROOT / PROTOCOL_REL)
    pins_before = {"numerics/gates.py": gates_sha_before,
                   "numerics/CONVERGENCE_PROTOCOL.md": proto_sha_before,
                   "events_snapshot": sha256_file(SNAP),
                   "pinned_gates_copy": sha256_file(PIN_GATES),
                   "pinned_protocol_copy": sha256_file(PIN_PROTO)}
    (RAW / "pins_before.json").write_text(json.dumps(pins_before, indent=1) + "\n")
    if gates_sha_before != EXPECT_GATES_SHA or proto_sha_before != EXPECT_PROTO_SHA:
        print(json.dumps({"error": "live pin moved before measurement",
                          "pins": pins_before}, indent=1))
        return 2

    gates = load_module("gates_pinned", PIN_GATES)
    prior = load_module("w064_prior", PRIOR)
    gate_targets = gates.PROTOCOL_REVIEW_TARGETS
    events = load_events()

    base = run_live(gates, events, EXPECT_PROTO_SHA)
    base_n = norm(base)

    channel_rows = []
    for label, addendum in channel_events():
        got = norm(run_live(gates, events + [addendum], EXPECT_PROTO_SHA))
        channel_rows.append({"arm": label, "addendum_event_id": addendum["event_id"],
                             "result": got})

    # --- shadow arms -------------------------------------------------------
    wd = ev("w064-sim-a8-author-structured-withdrawal", "status", "worker-067",
            "2026-09-12T01:14:07+08:00", node_id="N0", status="done",
            withdraws_event_ids=[WITHHELD_DISSENTS[0]], evidence_refs=[proto_ref()])
    car = carrier(WITHHELD_DISSENTS)
    shadow_arms = {}
    for name, evs, hooks in (
            ("E1-hooks-off", events, dict(scope=False, withdrawal=False, discharge=False)),
            ("B1-scope-only", events, dict(scope=True, withdrawal=False, discharge=False)),
            ("B2a-scope+withdrawal-no-field", events, dict(scope=True, withdrawal=True, discharge=False)),
            ("B2b-scope+withdrawal+author-field", events + [wd], dict(scope=True, withdrawal=True, discharge=False)),
            ("B3-scope+withdrawal+discharge", events + [wd, car], dict(scope=True, withdrawal=True, discharge=True))):
        out = prior.shadow_review(evs, EXPECT_PROTO_SHA, gate_targets=gate_targets, **hooks)
        shadow_arms[name] = norm(out)

    # --- negative controls on B3 ------------------------------------------
    controls = []
    base_b3 = events + [wd, car]
    control_cases = [
        ("C1-unknown-discharge-id", events + [wd, carrier(["no-such-event-id"])], True),
        ("C2-stale-hash-carrier", events + [wd, carrier(WITHHELD_DISSENTS, sha="0" * 64,
                                                       refs_stale=True)], True),
        ("C3-pre-dated-carrier", events + [wd, carrier(WITHHELD_DISSENTS, created="2026-09-11T00:00:00+08:00")], True),
        ("C4-uncited-carrier", events + [wd, carrier(WITHHELD_DISSENTS, sha=None)], True),
        ("C5-third-party-withdrawal", events + [wd, ev(
            "w064-sim-c5-third-party-withdrawal", "status", "astra", "2026-09-12T01:14:11+08:00",
            node_id="N0", status="done", withdraws_event_ids=[WITHHELD_DISSENTS[1]],
            evidence_refs=[proto_ref()])], True),
        ("C6-fresh-unlisted-dissent", base_b3 + [ev(
            "w064-sim-c6-fresh-dissent", "review", "worker-999", "2026-09-12T01:14:12+08:00",
            target_id="G-NUM-protocol", reviewer="worker-999", verdict="revise", score=2.0,
            reviewed_sha256=EXPECT_PROTO_SHA, node_id="N0",
            evidence_refs=[proto_ref()])], True),
    ]
    for label, evs, expect_contest in control_cases:
        out = prior.shadow_review(evs, EXPECT_PROTO_SHA, gate_targets=gate_targets,
                                  scope=True, withdrawal=True, discharge=True)
        n = norm(out)
        controls.append({"control": label, "expect_contest": expect_contest,
                         "result": n, "pass": n["contest"] == expect_contest})

    gates_sha_after = sha256_file(ROOT / GATES_REL)
    proto_sha_after = sha256_file(ROOT / PROTOCOL_REL)
    pins_after = {"numerics/gates.py": gates_sha_after,
                  "numerics/CONVERGENCE_PROTOCOL.md": proto_sha_after,
                  "events_snapshot": sha256_file(SNAP)}
    (RAW / "pins_after.json").write_text(json.dumps(pins_after, indent=1) + "\n")

    checks = []
    checks.append(("E1", shadow_arms["E1-hooks-off"] == base_n,
                   {"shadow": shadow_arms["E1-hooks-off"], "live": base_n}))
    checks.append(("E2", all(r["result"]["contest"] for r in channel_rows),
                   {"channel_arms_clearing": [r["arm"] for r in channel_rows
                                              if not r["result"]["contest"]]}))
    checks.append(("E3a", shadow_arms["B1-scope-only"]["contest"] is True, shadow_arms["B1-scope-only"]))
    checks.append(("E3b", shadow_arms["B2a-scope+withdrawal-no-field"]["contest"] is True,
                   shadow_arms["B2a-scope+withdrawal-no-field"]))
    checks.append(("E3c", shadow_arms["B3-scope+withdrawal+discharge"]["contest"] is False,
                   shadow_arms["B3-scope+withdrawal+discharge"]))
    checks.append(("E4", all(c["pass"] for c in controls), controls))
    checks.append(("E5", pins_before[GATES_REL] == pins_after[GATES_REL]
                   and pins_before[PROTOCOL_REL] == pins_after[PROTOCOL_REL],
                   {"before": pins_before, "after": pins_after}))

    fails = [cid for cid, ok, _ in checks if not ok]
    control_fail = [c["control"] for c in controls if not c["pass"]]
    if control_fail:
        verdict = "FAIL_OPEN_RULE_UNSAFE"
    elif fails:
        verdict = "PREREG_FALSIFIED"
    else:
        verdict = ("CHANNEL_CLOSED__NO_STREAM_EVENT_CLEARS_CONTEST__"
                   "ONLY_GUARD_RULE_R1R2R3_CLEARS_WITH_6_OF_6_CONTROLS")

    control_v1 = {
        "round": 1,
        "verdict": "FAIL_OPEN_RULE_UNSAFE (exit 4)",
        "controls_failed": ["C2-stale-hash-carrier", "C5-third-party-withdrawal",
                            "C6-fresh-unlisted-dissent"],
        "diagnosis": [
            "C2 was not a stale-hash control: carrier() still cited the live protocol hash via evidence_refs, so it bound through the evidence_ref path (live semantics: bind if ANY cited hash matches) and its discharge list cleared the remaining dissent. Fixed: refs_stale=True makes the zero hash the only citation.",
            "C5 omitted the author withdrawal and the empty discharge, so the binding carrier discharged both dissents regardless of the third-party withdrawal. Fixed: no carrier; author withdraws F1, third party attempts F1'; R2 must ignore the third party, leaving F1' counted.",
            "C6 targeted N0, which scope R1 excludes by construction, so the fresh dissent never counted. Fixed: target G-NUM-protocol, created after the carrier; the explicit discharge list does not name it.",
        ],
        "corrected_round": 2,
    }
    (RAW / "control_v1_failures.json").write_text(json.dumps(control_v1, indent=1) + "\n")

    summary = {
        "schema": "w064-guard-channels/report/v1",
        "task_id": "W064-GNUM-GUARD-CHANNELS-02",
        "actor": "worker-064",
        "created_at": ts_start,
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N0",
        "gate": "G-NUM",
        "verdict": verdict,
        "pins": {"before": pins_before, "after": pins_after,
                 "protocol_sha256": EXPECT_PROTO_SHA, "gates_sha256": EXPECT_GATES_SHA},
        "baseline_live_guard": base_n,
        "channel_arms": channel_rows,
        "shadow_arms": shadow_arms,
        "negative_controls": controls,
        "control_design_corrections": control_v1,
        "checks": [{"id": cid, "pass": ok, "detail": detail} for cid, ok, detail in checks],
        "fails": fails,
        "prereg": "artifacts/worker-064/guard_channels/prereg.json",
        "finding": ("Every protocol-conformant stream channel (status disposition, gate pass, "
                    "gate discharge list, review rebind, review discharge list, artifact record, "
                    "structured withdrawal) leaves contest=true under the live predicate at "
                    "fcd1d70991b6; only the shadow guard rule (scope R1 + author withdrawal R2 + "
                    "explicit same-hash discharge carrier R3) clears it, with 6/6 negative controls "
                    "fail-closed. Disposition-by-event cannot satisfy audit-l06-b4; a guard "
                    "supersession rule or code patch is required."),
        "not_claimed": ["no gate verdict", "no node completion", "no adoption of R1-R3",
                        "no canonical modification", "no physics claim",
                        "synthetic channel events are simulations, not emitted events"],
        "next_falsifier": ("If the controller adopts a supersession rule or emits a structured "
                           "discharge and gates.py moves off fcd1d70991b6, re-run this harness at "
                           "the new hash; expected accept>=6 / dissent=0 with the six controls "
                           "still failing closed."),
    }
    (HERE / "report.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    with open(HERE / "channels.jsonl", "w") as f:
        for r in channel_rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    with open(HERE / "controls.jsonl", "w") as f:
        for c in controls:
            f.write(json.dumps(c, sort_keys=True) + "\n")

    print(json.dumps({"verdict": verdict, "fails": fails,
                      "baseline": base_n,
                      "channels_contest": {r["arm"]: r["result"]["contest"] for r in channel_rows},
                      "shadow": {k: v["contest"] for k, v in shadow_arms.items()},
                      "controls_pass": [c["pass"] for c in controls]}, indent=1))
    if control_fail:
        return 4
    return 0 if not fails else 3


if __name__ == "__main__":
    sys.exit(main())
