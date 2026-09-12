#!/usr/bin/env python3
"""W020-GNUM-PROTOCOL-REVIEW-SEMANTICS-01.

Independent, read-only, hash-pinned semantics audit of
``numerics/gates.py::_protocol_review`` (pin fcd1d70991b6) at protocol pin
1e6cdf04d7a2, motivated by controller finding B-N0-R2-2 and worker-017 closure
review W017-N0C-F05.

Method
------
1. The full gate input set is pinned: the four named files plus every event
   source that ``numerics/gates.py::load_event_stream`` reads (accepted stream,
   then comms/outbox, then comms/inbox).  Pinned copies are re-hashed and the
   live sources are re-hashed (read-only) to record drift.
2. The live review state is reproduced by calling the *pinned* module copy's
   ``_protocol_review`` on the pinned event list.
3. Every binding review row is decomposed (reviewer, verdict, target, target
   class document|node, created_at, cited hash, binds).
4. Five candidate semantics are evaluated on the same pinned live event set:
   live (union scope, no supersession), R1 (union + latest verdict per
   reviewer), R2 (document scope, no supersession), R3 (document scope +
   latest verdict per reviewer), R4 (union + latest verdict per
   (reviewer,target)).
5. A 15-case synthetic truth table with fail-closed tie and dedup controls is
   run against all five rules.

Authority: worker evidence only.  No gate verdict, no node status, no canonical
write, no lock change.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

PROTOCOL_PATH = "numerics/CONVERGENCE_PROTOCOL.md"
REVIEW_SELF = "astra-lead-numerics"
UNION_TARGETS = (PROTOCOL_PATH, "G-NUM-protocol", "N0")
DOC_TARGETS = (PROTOCOL_PATH, "G-NUM-protocol")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pinned(task: Path, manifest: dict) -> dict[str, bytes]:
    """Verify every pinned copy against the manifest; fail closed on drift."""
    out: dict[str, bytes] = {}
    for logical, rec in manifest["files"].items():
        p = task / "pinned" / rec["copy"]
        if not p.is_file():
            raise SystemExit(f"FAIL-CLOSED: pinned copy missing for {logical}")
        got = sha256_file(p)
        if got != rec["sha256"]:
            raise SystemExit(f"FAIL-CLOSED: pinned {logical} copy measures {got} != {rec['sha256']}")
        out[logical] = p.read_bytes()
    sources = []
    for rec in manifest["tree"]["sources"]:
        p = task / "pinned" / "tree" / rec["copy"]
        if not p.is_file():
            raise SystemExit(f"FAIL-CLOSED: pinned tree copy missing for {rec['rel']}")
        got = sha256_file(p)
        if got != rec["sha256"]:
            raise SystemExit(f"FAIL-CLOSED: pinned tree {rec['rel']} measures {got} != {rec['sha256']}")
        sources.append((rec["rel"], p.read_bytes()))
    out["__tree__"] = sources
    return out


def load_pinned_gates(pinned: dict):
    src = pinned["numerics/gates.py"]
    tmp = Path("/tmp") / "w020_pinned_gates.py"
    tmp.write_bytes(src)
    spec = importlib.util.spec_from_file_location("w020_pinned_gates", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_event_list(tree: list[tuple[str, bytes]]) -> list[dict]:
    """Reconstruct load_event_stream order: events.jsonl, outbox sorted, inbox sorted."""
    order = {"research_map/events.jsonl": 0}
    ordered = sorted(
        tree,
        key=lambda kv: (
            0 if kv[0] == "research_map/events.jsonl" else (1 if kv[0].startswith("comms/outbox/") else 2),
            kv[0],
        ),
    )
    events: list[dict] = []
    for _rel, blob in ordered:
        for line in blob.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(doc, dict):
                events.append(doc)
    return events


def cited_hashes(e: dict) -> list[str]:
    out: list[str] = []
    for k in ("reviewed_sha256", "artifact_sha256", "reviewed_protocol_hash"):
        v = e.get(k)
        if isinstance(v, str) and len(v.strip()) >= 12:
            out.append(v.strip().lower())
    for ref in e.get("evidence_refs", []) or []:
        if not isinstance(ref, str):
            continue
        for sep in ("#sha256:", "#"):
            if ref.startswith(PROTOCOL_PATH + sep):
                h = ref.split(sep, 1)[1].strip().lower()
                if len(h) >= 12:
                    out.append(h)
    return out


def make_target_matcher(targets):
    def match(target: str) -> bool:
        t = str(target).strip()
        for cand in targets:
            if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
                return True
        return False

    return match


TARGET_UNION = make_target_matcher(UNION_TARGETS)
TARGET_DOC = make_target_matcher(DOC_TARGETS)


def binds(e: dict, protocol_sha: str) -> bool:
    return any(
        protocol_sha.startswith(c) or c.startswith(protocol_sha)
        for c in cited_hashes(e)
    )


def target_class(target: str) -> str:
    if TARGET_DOC(target):
        return "document"
    if TARGET_UNION(target):
        return "node"
    return "other"


def _sort_key(created, seq):
    return (str(created or "")[:19], seq)


def run_rule(events, protocol_sha, scope, supersede, supersede_key="reviewer"):
    target_fn = TARGET_UNION if scope == "union" else TARGET_DOC
    seen: set[str] = set()
    rows: list[dict] = []
    advisory: list[dict] = []
    for seq, e in enumerate(events):
        if e.get("event_type") != "review":
            continue
        verdict = e.get("verdict")
        if verdict not in ("accept", "revise", "reject"):
            continue
        if not target_fn(str(e.get("target_id", ""))):
            continue
        if e.get("reviewer") == REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or f"__noid_{seq}")
        if eid in seen:
            continue
        seen.add(eid)
        row = {
            "event_id": eid,
            "reviewer": e.get("reviewer") or "(anonymous)",
            "target_id": e.get("target_id"),
            "target_class": target_class(str(e.get("target_id", ""))),
            "verdict": verdict,
            "created_at": e.get("created_at"),
            "score": e.get("score"),
            "cited": cited_hashes(e),
            "seq": seq,
        }
        (rows if binds(e, protocol_sha) else advisory).append(row)

    superseded: list[dict] = []
    if supersede:
        latest: dict[tuple, dict] = {}
        for row in rows:
            key = (row["reviewer"],) if supersede_key == "reviewer" else (
                row["reviewer"], target_class(str(row["target_id"])), str(row["target_id"])
            )
            cur = latest.get(key)
            if cur is None:
                latest[key] = row
                continue
            if _sort_key(row["created_at"], row["seq"]) > _sort_key(cur["created_at"], cur["seq"]):
                latest[key] = row
            elif _sort_key(row["created_at"], row["seq"]) == _sort_key(cur["created_at"], cur["seq"]):
                if row["verdict"] != "accept" and cur["verdict"] == "accept":
                    latest[key] = row
        keep = {id(r) for r in latest.values()}
        superseded = [r for r in rows if id(r) not in keep]
        rows = [r for r in rows if id(r) in keep]

    accepts = [r for r in rows if r["verdict"] == "accept"]
    dissents = [r for r in rows if r["verdict"] in ("revise", "reject")]
    return {
        "scope": scope,
        "supersede": supersede,
        "supersede_key": supersede_key if supersede else None,
        "reviewed": bool(accepts),
        "accepting_reviews": [r["event_id"] for r in accepts],
        "dissenting_reviews": [
            {"event_id": r["event_id"], "reviewer": r["reviewer"], "verdict": r["verdict"],
             "target_class": r["target_class"]}
            for r in dissents
        ],
        "contest": bool(dissents),
        "advisory_at_other_hashes": [
            {"event_id": r["event_id"], "reviewer": r["reviewer"], "verdict": r["verdict"]}
            for r in advisory
        ],
        "superseded_rows": [
            {"event_id": r["event_id"], "reviewer": r["reviewer"], "verdict": r["verdict"],
             "target_class": r["target_class"]}
            for r in superseded
        ],
        "n_binding_rows": len(rows) + len(superseded),
    }


RULES = [
    ("live", "union", False, "reviewer"),
    ("R1", "union", True, "reviewer"),
    ("R2", "document", False, "reviewer"),
    ("R3", "document", True, "reviewer"),
    ("R4", "union", True, "reviewer_target"),
]


def classify(out: dict) -> str:
    if out["contest"]:
        return "contest"
    if out["reviewed"]:
        return "clear"
    return "unreviewed"


# ---------------------------------------------------------------- truth table
def truth_table(proto: str) -> list[dict]:
    A = proto
    P = PROTOCOL_PATH + "#" + A
    G = "G-NUM-protocol"
    cases = []

    def ev(eid, reviewer, verdict, target, created, cited=None, event_type="review"):
        return {
            "event_id": eid,
            "event_type": event_type,
            "reviewer": reviewer,
            "verdict": verdict,
            "target_id": target,
            "created_at": created,
            "reviewed_sha256": cited or A,
        }

    def add(cid, events, expected, note):
        cases.append({"id": cid, "events": events, "expected": expected, "note": note})

    ALL = {"live": "contest", "R1": "contest", "R2": "contest", "R3": "contest", "R4": "contest"}
    add("C01", [ev("e1", "r1", "revise", G, "2026-01-01T00:00:01+08:00")], ALL,
        "single document revise -> contested under every rule")
    add("C02", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r1", "accept", G, "2026-01-01T00:00:02+08:00")],
        {k: "clear" for k in ALL}, "two accepts, same reviewer, no dissent")
    add("C03", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r1", "revise", G, "2026-01-01T00:00:02+08:00")], ALL,
        "accept then later revise -> contested incl. supersession")
    add("C04", [ev("e1", "r1", "revise", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r1", "accept", G, "2026-01-01T00:00:02+08:00")],
        {"live": "contest", "R1": "clear", "R2": "contest", "R3": "clear", "R4": "clear"},
        "revise then later accept by same reviewer -> supersession clears")
    add("C05", [ev("e1", "r1", "revise", "N0", "2026-01-01T00:00:01+08:00")],
        {"live": "contest", "R1": "contest", "R2": "unreviewed", "R3": "unreviewed", "R4": "contest"},
        "N0-node revise only -> union rules contest, document rules do not see it")
    add("C06", [ev("e1", "r1", "accept", "N0", "2026-01-01T00:00:01+08:00")],
        {"live": "clear", "R1": "clear", "R2": "unreviewed", "R3": "unreviewed", "R4": "clear"},
        "N0-node accept only -> union rules count it, document rules do not")
    add("C07", [ev("e1", REVIEW_SELF, "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", REVIEW_SELF, "revise", G, "2026-01-01T00:00:02+08:00")],
        {k: "unreviewed" for k in ALL}, "self-review excluded everywhere")
    add("C08", [ev("e1", "r1", "revise", G, "2026-01-01T00:00:01+08:00", cited="b" * 64)],
        {k: "unreviewed" for k in ALL}, "review at a superseded hash is advisory only")
    add("C09", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r1", "revise", G, "2026-01-01T00:00:01+08:00")], ALL,
        "exact created_at tie, same reviewer -> dissent wins (fail-closed)")
    add("C10", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r2", "revise", G, "2026-01-01T00:00:02+08:00")], ALL,
        "two distinct reviewers, one dissent -> contested everywhere")
    add("C11", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e2", "r1", "revise", "N0", "2026-01-01T00:00:02+08:00")],
        {"live": "contest", "R1": "contest", "R2": "clear", "R3": "clear", "R4": "contest"},
        "same reviewer: document accept + later N0 revise -> union keeps both keys")
    add("C12", [ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00"),
                ev("e1", "r1", "accept", G, "2026-01-01T00:00:01+08:00")],
        {k: "clear" for k in ALL}, "duplicate event_id deduped (stream + outbox copy)")
    add("C13", [ev("e1", "r1", "revise", P, "2026-01-01T00:00:01+08:00", cited=A)], ALL,
        "path#hash target form IS recognized by the live matcher")
    add("C14", [ev("e1", "r1", "accept", P, "2026-01-01T00:00:01+08:00", cited=A),
                ev("e2", "r1", "revise", P, "2026-01-01T00:00:02+08:00", cited=A)], ALL,
        "path#hash accept then later revise -> contested incl. supersession")
    add("C15", [ev("e1", "r1", "accept", P, "2026-01-01T00:00:01+08:00", cited=A),
                ev("e2", "r1", "revise", P, "2026-01-01T00:00:02+08:00", cited=A),
                ev("e3", "r1", "accept", P, "2026-01-01T00:00:03+08:00", cited=A),
                ev("e4", "r1", "revise", "N0", "2026-01-01T00:00:04+08:00")],
        {"live": "contest", "R1": "contest", "R2": "contest", "R3": "clear", "R4": "contest"},
        "live-like 081 pattern: document revise retracted by later document accept; "
        "N0 revise dropped only by document scope + supersession (R3)")
    add("C16", [ev("e1", "r1", "revise", P, "2026-01-01T00:00:01+08:00", cited=A),
                ev("e2", "r2", "revise", "N0", "2026-01-01T00:00:02+08:00"),
                ev("e3", "r3", "accept", G, "2026-01-01T00:00:03+08:00")], ALL,
        "standing document revise (067-like) survives every candidate rule")
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--task-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    task = Path(args.task_dir).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((task / "pinned" / "manifest.json").read_text())
    pinned = load_pinned(task, manifest)
    gates_mod = load_pinned_gates(pinned)
    events = build_event_list(pinned["__tree__"])
    protocol_sha = manifest["files"][PROTOCOL_PATH]["sha256"]

    # live drift check (read-only): does the pinned source tree still equal disk?
    live_drift = []
    for rec in manifest["tree"]["sources"]:
        p = root / rec["rel"]
        if not p.is_file():
            live_drift.append({"rel": rec["rel"], "status": "missing"})
        elif sha256_file(p) != rec["sha256"]:
            live_drift.append({"rel": rec["rel"], "status": "changed",
                               "pinned": rec["sha256"][:12], "live": sha256_file(p)[:12]})
    for logical, rec in manifest["files"].items():
        p = root / logical
        if not p.is_file():
            live_drift.append({"rel": logical, "status": "missing"})
        elif sha256_file(p) != rec["sha256"]:
            live_drift.append({"rel": logical, "status": "changed",
                               "pinned": rec["sha256"][:12], "live": sha256_file(p)[:12]})

    live_call = gates_mod._protocol_review(events, protocol_sha)

    # full live decomposition under union scope (all rows, binding or advisory)
    all_rows = []
    seen = set()
    for seq, e in enumerate(events):
        if e.get("event_type") != "review" or e.get("verdict") not in ("accept", "revise", "reject"):
            continue
        if not TARGET_UNION(str(e.get("target_id", ""))) or e.get("reviewer") == REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or f"__noid_{seq}")
        if eid in seen:
            continue
        seen.add(eid)
        all_rows.append({
            "event_id": eid,
            "reviewer": e.get("reviewer"),
            "verdict": e.get("verdict"),
            "target_id": e.get("target_id"),
            "target_class": target_class(str(e.get("target_id", ""))),
            "created_at": e.get("created_at"),
            "score": e.get("score"),
            "cited_hashes": [h[:12] for h in cited_hashes(e)],
            "binds_current_protocol": binds(e, protocol_sha),
        })
    all_rows.sort(key=lambda r: (str(r["created_at"]), r["event_id"]))

    rule_out = {name: run_rule(events, protocol_sha, scope, sup, key)
                for name, scope, sup, key in RULES}

    cases = truth_table(protocol_sha)
    case_results = []
    controls_passed = 0
    for c in cases:
        got = {name: classify(run_rule(c["events"], protocol_sha, scope, sup, key))
               for name, scope, sup, key in RULES}
        ok = got == c["expected"]
        controls_passed += int(ok)
        case_results.append({"id": c["id"], "note": c["note"], "expected": c["expected"],
                             "got": got, "match": ok})

    binding = [r for r in all_rows if r["binds_current_protocol"]]
    doc_binding = [r for r in binding if r["target_class"] == "document"]
    node_binding = [r for r in binding if r["target_class"] == "node"]
    r3 = rule_out["R3"]
    findings = [
        {"id": "W020-PRS-01", "severity": "major",
         "finding": f"Live union-scope state at protocol {protocol_sha[:12]}: "
                    f"{len(binding)} binding rows = {len([r for r in binding if r['verdict']=='accept'])} "
                    f"accept / {len([r for r in binding if r['verdict']!='accept'])} dissent; "
                    f"{len(node_binding)} of the dissents target N0 (node reviews that cite the "
                    f"protocol hash), {len([r for r in doc_binding if r['verdict']!='accept'])} "
                    f"target the document. The tool reports reviewed=true, contest=true."},
        {"id": "W020-PRS-02", "severity": "major",
         "finding": "Scope conflation is real: the union target scope (path, G-NUM-protocol, N0) "
                    "counts an N0-node revise as a protocol-document dissent. The three N0-targeted "
                    "dissents (067-provledger 00:51:49, 042-stoprule 00:52:59, 081-pinsplit "
                    "00:58:18) are node verdicts, not document verdicts; under document scope they "
                    "are excluded (rules R2/R3)."},
        {"id": "W020-PRS-03", "severity": "major",
         "finding": "No supersession: the live accepted_reviews list keeps 081-c8 (00:21:40) and "
                    "081-adj2 (00:42:05) while dissenting_reviews keeps 081-f1adj (00:29:19), "
                    "although 081-adj2 is later than 081-f1adj and retracts it in its own text "
                    "(DISPOSITION F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION). R3/R4 remove "
                    "081-f1adj and keep 081-adj2 as 081's operative document verdict."},
        {"id": "W020-PRS-04", "severity": "major",
         "finding": "Supersession and scope alone do NOT clear the live contest. R3 (document "
                    "scope + latest per reviewer) still reports contest=true with exactly one "
                    "standing dissent: worker-067 w067-review-gnum-protocol-r3 (revise 4.0, "
                    "00:22:56, path#hash target, F1 major: section 3.4 text must be scoped in "
                    "rev 4). Worker-067 published no later document verdict, so the correct "
                    "controller statement is 'one standing document revise', not 'no contest'."},
        {"id": "W020-PRS-05", "severity": "advisory",
         "finding": "Correction to B-N0-R2-2's chronology: 081's adj2 accept (00:42:05) supersedes "
                    "only its own f1adj revise (00:29:19). 081's later binding verdict is the "
                    "pinsplit revise (00:58:18, N0 target), which is later than adj2 and is what "
                    "withdraws 081's c8 accept under union scope. A (reviewer,target)-supersession "
                    "rule (R4) therefore leaves 081 as accept-on-document + revise-on-N0 "
                    "simultaneously; only document scope + per-reviewer supersession (R3) yields a "
                    "single coherent 081 document position (accept)."},
        {"id": "W020-PRS-06", "severity": "advisory",
         "finding": "Candidate semantics for controller disposition (not adopted here): "
                    "(a) score the protocol on document-targeted verdicts (path or G-NUM-protocol) "
                    "and keep N0-targeted verdicts for node N0; (b) supersede per (reviewer, scope) "
                    "by created_at with dissent winning exact ties; (c) keep the union scope only "
                    "for the 'is there any independent accept' predicate, not for contest. Live "
                    "effect of that candidate (R3): reviewed=true, contest=true with the single "
                    "standing dissent 067-r3; the remaining blocker is substantive (067 F1 vs "
                    "081-adj2/flash-12 C3 discharge), not mechanical."},
        {"id": "W020-PRS-07", "severity": "info",
         "finding": f"Controls: {controls_passed}/{len(cases)} truth-table cases matched declared "
                    f"expectations; live-source drift at audit time: {len(live_drift)} file(s). "
                    f"Advisory rows at superseded hashes: "
                    f"{len(live_call['advisory_reviews_at_other_hashes'])} "
                    f"(reported separately, do not bind)."},
    ]

    report = {
        "schema": "worker-020/gates-protocol-review-semantics/v1",
        "task_id": "W020-GNUM-PROTOCOL-REVIEW-SEMANTICS-01",
        "actor": "worker-020",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "instrument": "sandbox/audit_protocol_review_semantics.py",
        "pins": {k: {"sha256": v["sha256"], "copy": v["copy"]}
                 for k, v in manifest["files"].items()},
        "tree": {"n_sources": len(manifest["tree"]["sources"]),
                 "sha256": manifest["tree"]["sha256"]},
        "live_drift_at_audit": live_drift,
        "live_reproduction": live_call,
        "live_event_table": all_rows,
        "rule_outcomes_live": rule_out,
        "truth_table": case_results,
        "controls_passed": controls_passed,
        "controls_total": len(cases),
        "findings": findings,
        "not_claimed": [
            "not a gate verdict; G-NUM stays pending and astra/lead-audit own the disposition",
            "no canonical file edited; numerics/gates.py untouched",
            "no node status, no validation_status, no numerics_lock change",
            "the candidate semantics is a recommendation for controller disposition, not an adjudication",
            "no claim about which of 067-r3 / 081-adj2 / flash-12 C3 is substantively correct",
        ],
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    # determinism: recompute the pure result sets and compare digests
    d1 = hashlib.sha256(json.dumps(
        [rule_out, case_results], sort_keys=True).encode()).hexdigest()
    rule_out_2 = {name: run_rule(events, protocol_sha, scope, sup, key)
                  for name, scope, sup, key in RULES}
    case_results_2 = []
    for c in cases:
        case_results_2.append({name: classify(run_rule(c["events"], protocol_sha, scope, sup, key))
                               for name, scope, sup, key in RULES})
    d2 = hashlib.sha256(json.dumps(
        [rule_out_2, case_results_2], sort_keys=True).encode()).hexdigest()
    (out_dir / "determinism_check.txt").write_text(
        ("PASS recomputation digest identical\n" if d1 == d2 else f"FAIL {d1} != {d2}\n"))
    (out_dir / "determinism_digest.txt").write_text(d1 + "\n")

    print(json.dumps({
        "live": {"reviewed": live_call["reviewed"], "contest": live_call["contest"],
                 "n_accepts": len(live_call["accepting_reviews"]),
                 "n_dissents": len(live_call["dissenting_reviews"])},
        "rules": {k: {"state": classify(v), "accepts": len(v["accepting_reviews"]),
                      "dissents": len(v["dissenting_reviews"])} for k, v in rule_out.items()},
        "R3_standing_dissents": [d["event_id"] for d in rule_out["R3"]["dissenting_reviews"]],
        "controls": f"{controls_passed}/{len(cases)}",
        "live_drift": live_drift,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
