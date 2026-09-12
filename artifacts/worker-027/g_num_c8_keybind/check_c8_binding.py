#!/usr/bin/env python3
"""W027-GNUM-C8-KEYBIND-01 — independent measurement of the G-NUM criterion-C8
binding path in the controller lifecycle tool.

Question
--------
The controller's G-NUM gate reason (lifecycle pass 2026-09-12T00:24:40+08:00 and the
map's carry-over `controller_gate_audit`) says:

    "... the recorded protocol verdict reviews/G-NUM-protocol-review.json binds
     unbound (stale), so criterion C8 is the exact unmet requirement."

At the same pinned snapshot:
  * numerics/CONVERGENCE_PROTOCOL.md measures 1e6cdf04d7a2...
  * reviews/G-NUM-protocol-review.json is verdict=accept,
    counts_as_full_schema_verdict=true, reviewer=astra-lead-audit, and pins
    reviewed_sha256 = 1e6cdf04d7a2... (the measured revision).

Hypothesis under test (registered before running):
  H1: the controller's single-file extraction for the G-NUM protocol verdict reads
      only the key `artifact_sha256` (astra_lifecycle.py line 259 at the pinned
      controller hash), while the review file declares its pin under
      `reviewed_sha256`; therefore the reason reports "unbound" although the
      verdict binds the measured revision.
  H2: the corpus-wide binding scanner (`review_coverage`, keys
      artifact_sha256/reviewed_sha256/sha256/cited_sha256 over the measured node-id
      set) cannot cover this verdict either, because its target universe is the
      measured node ids and `G-NUM-protocol` is not one of them.

Method
------
Stdlib only; no project imports; both controller code paths are re-implemented
here verbatim-in-effect from line-cited source text extracted from the *pinned
controller bytes* (the extracted source lines are recorded in the report).
Fail-closed on input drift: every input is hashed and, with --expect-*, compared.

Exit codes
----------
  0  FINDING_REPRODUCED : all registered expectations hold
  2  INPUT_DRIFT        : a --expect-* pin does not match the file on disk
  3  FALSIFIED          : at least one registered expectation failed

Falsifier (pre-registered)
--------------------------
The finding is falsified if any of:
  (a) the pinned review file's `reviewed_sha256` does not equal the measured
      sha256 of the pinned protocol file;
  (b) the pinned review file is not an accept with
      counts_as_full_schema_verdict != false;
  (c) the controller expression on the pinned review bytes does not return
      "unbound";
  (d) the newest lifecycle report's G-NUM reason does not contain
      "binds unbound (stale)" while the inputs are unchanged;
  (e) control C1 (artifact_sha256-only synthetic review) does not return the
      protocol prefix — i.e. the extraction expression is insensitive, so the
      field-scope reading is wrong;
  (f) control C3 (mutated hash) binds under the corpus prefix rule — i.e. that
      rule is a rubber stamp.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DEFAULTS = {
    "protocol": "numerics/CONVERGENCE_PROTOCOL.md",
    "review": "reviews/G-NUM-protocol-review.json",
    "controller": "research_map/astra_lifecycle.py",
    "map": "research_map/research_map.json",
    "lifecycle_dir": "runtime/state/controller_verification",
}

# Controller code paths re-implemented from the pinned source text.  The exact
# source lines are extracted at run time and recorded under `source_lines`.
CONTROLLER_EXPR_KEYS = ("artifact_sha256",)          # astra_lifecycle.py:~259
CORPUS_PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")  # ~147
CORPUS_TARGET_KEYS = ("target_id", "target", "target_subnode")                     # ~130
TARGET_ALIASES = {                                    # ~119
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def controller_expr(doc: dict) -> str:
    """Verbatim effect of astra_lifecycle.py:~259 on one parsed review object."""
    return str(doc.get("artifact_sha256") or "unbound")[:12]


def corpus_pins(doc: dict) -> list:
    """Verbatim effect of astra_lifecycle.py:~144-157 (_explicit_pins)."""
    pins = []
    for key in CORPUS_PIN_KEYS:
        v = doc.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = doc.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def corpus_targets(doc: dict) -> set:
    """Verbatim effect of astra_lifecycle.py:~128-141 (_targets_in_review)."""
    out = set()
    for key in CORPUS_TARGET_KEYS:
        v = doc.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def corpus_binds(doc: dict, measured_hash: str) -> bool:
    """Verbatim effect of review_coverage's 12-hex prefix bind (astra_lifecycle.py:~185)."""
    h = measured_hash or ""
    if not h:
        return False
    return any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in corpus_pins(doc))


def newest_gate_reason(report_dir: str, gate: str = "G-NUM"):
    """Newest lifecycle report containing a controller_gate_audit reason for `gate`."""
    best = None
    for p in sorted(glob.glob(os.path.join(report_dir, "lifecycle_*.json"))):
        try:
            with open(p, "r") as fh:
                d = json.load(fh)
        except Exception:
            continue
        reason = (((d.get("controller_gate_audit") or {}).get(gate) or {}).get("reason"))
        if not reason:
            continue
        key = (str(d.get("at") or d.get("started_at") or ""), os.path.getmtime(p), p)
        if best is None or key > best[0]:
            best = (key, p, d, reason)
    return best


def source_lines(controller_bytes: bytes, needles) -> dict:
    lines = controller_bytes.decode("utf-8", "replace").splitlines()
    out = {}
    for n, line in enumerate(lines, 1):
        for needle in needles:
            if needle in line and needle not in out:
                out[needle] = {"line": n, "text": line.strip()}
    return out


def ctrl(checks: list, cid: str, expectation: str, observed, ok: bool, detail: str = ""):
    checks.append({"id": cid, "expectation": expectation, "observed": observed,
                   "ok": bool(ok), "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser(description="W027 G-NUM C8 binding measurement")
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), default=os.path.join(ROOT, v))
    ap.add_argument("--expect-protocol", default=None)
    ap.add_argument("--expect-review", default=None)
    ap.add_argument("--expect-controller", default=None)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "artifacts/worker-027/g_num_c8_keybind/report.json"))
    ap.add_argument("--snapshot-dir", default=os.path.join(
        ROOT, "artifacts/worker-027/g_num_c8_keybind/snapshots"))
    args = ap.parse_args()

    protocol_path = args.protocol
    review_path = args.review
    controller_path = args.controller
    map_path = args.map
    lifecycle_dir = args.lifecycle_dir

    checks: list = []
    findings: list = []

    # ---- pins -------------------------------------------------------------
    protocol_bytes = open(protocol_path, "rb").read()
    review_bytes = open(review_path, "rb").read()
    controller_bytes = open(controller_path, "rb").read()
    map_bytes = open(map_path, "rb").read()
    protocol_h = sha256_bytes(protocol_bytes)
    review_h = sha256_bytes(review_bytes)
    controller_h = sha256_bytes(controller_bytes)
    map_h = sha256_bytes(map_bytes)

    drift = []
    if args.expect_protocol and protocol_h != args.expect_protocol:
        drift.append(("protocol", protocol_h, args.expect_protocol))
    if args.expect_review and review_h != args.expect_review:
        drift.append(("review", review_h, args.expect_review))
    if args.expect_controller and controller_h != args.expect_controller:
        drift.append(("controller", controller_h, args.expect_controller))
    if drift:
        print(json.dumps({"verdict": "INPUT_DRIFT", "drift": drift}, indent=2))
        return 2

    src = source_lines(controller_bytes,
                       ["proto_rev_h = str(", 'for key in ("artifact_sha256",',
                        'for key in ("target_id", "target", "target_subnode")',
                        "p.startswith(h[:12]) or h.startswith(p[:12])"])

    review_doc = json.loads(review_bytes.decode("utf-8"))
    pins = corpus_pins(review_doc)
    tgt = corpus_targets(review_doc)

    # ---- H1 / core checks -------------------------------------------------
    ctrl(checks, "C1_review_verdict_is_accept",
         "review verdict == accept and counts_as_full_schema_verdict != false",
         {"verdict": review_doc.get("verdict"),
          "counts_as_full_schema_verdict": review_doc.get("counts_as_full_schema_verdict"),
          "reviewer": review_doc.get("reviewer"), "score": review_doc.get("score")},
         review_doc.get("verdict") == "accept"
         and review_doc.get("counts_as_full_schema_verdict") is not False,
         "An eligible accept owned by the audit lead is present on disk.")

    ctrl(checks, "C2_review_binds_measured_protocol",
         "reviewed_sha256 == measured sha256 of numerics/CONVERGENCE_PROTOCOL.md",
         {"reviewed_sha256": review_doc.get("reviewed_sha256"), "protocol_sha256": protocol_h,
          "full_equal": review_doc.get("reviewed_sha256") == protocol_h,
          "prefix12_equal": str(review_doc.get("reviewed_sha256", ""))[:12] == protocol_h[:12]},
         review_doc.get("reviewed_sha256") == protocol_h,
         "The pinned verdict is bound to the currently measured protocol revision.")

    expr_out = controller_expr(review_doc)
    ctrl(checks, "C3_controller_expr_on_real_review",
         'controller extraction str(d.get("artifact_sha256") or "unbound")[:12] '
         'returns "unbound" while the review pins reviewed_sha256 == measured protocol hash',
         {"observed": expr_out, "protocol_prefix12": protocol_h[:12],
          "review_pins_reviewed_sha256": review_doc.get("reviewed_sha256") == protocol_h},
         expr_out == "unbound" and review_doc.get("reviewed_sha256") == protocol_h,
         "Observed output isolates the field-scope mismatch (H1).")

    best = newest_gate_reason(lifecycle_dir)
    reason = best[3] if best else ""
    ctrl(checks, "C4_controller_reason_reports_unbound",
         'newest lifecycle G-NUM reason contains "binds unbound (stale)"',
         {"report": os.path.relpath(best[1], ROOT) if best else None,
          "checked_at": (best[2].get("controller_gate_audit", {}).get("G-NUM", {}) or {}).get("checked_at") if best else None,
          "reason": reason[:400]},
         "binds unbound (stale)" in reason,
         "Controller output at the pinned inputs.")

    map_reason = (((json.loads(map_bytes.decode("utf-8")).get("controller_gate_audit") or {})
                   .get("G-NUM") or {}).get("reason") or "")
    ctrl(checks, "C5_map_carries_same_reason",
         'map controller_gate_audit.G-NUM.reason contains "binds unbound (stale)"',
         {"reason": map_reason[:400]}, "binds unbound (stale)" in map_reason,
         "The stale wording is carried into the sole global state.")

    # ---- H2: corpus scanner cannot cover the target -----------------------
    measured_nodes = []
    try:
        with open(best[1]) as fh:
            measured_nodes = sorted((json.load(fh).get("measured_hashes") or {}).keys())
    except Exception:
        pass
    ctrl(checks, "C6_corpus_scanner_target_universe",
         "review_coverage's cov keys are the measured node ids and exclude G-NUM-protocol",
         {"targets_in_review": sorted(tgt), "measured_node_ids": measured_nodes,
          "target_in_universe": bool(tgt & set(measured_nodes))},
         bool(tgt) and not (tgt & set(measured_nodes)),
         "H2: no corpus-wide path in gate_audit counts this verdict either.")
    ctrl(checks, "C7_corpus_prefix_rule_would_bind",
         "the corpus 12-hex prefix rule (re-implemented) does bind this review to the "
         "measured protocol hash when applied directly",
         {"pins": pins, "corpus_binds": corpus_binds(review_doc, protocol_h)},
         corpus_binds(review_doc, protocol_h),
         "Shows the review bytes are well-formed for the corpus rule; only the "
         "single-file path and target universe exclude them.")

    # ---- controls ---------------------------------------------------------
    base = {"verdict": "accept", "reviewer": "synthetic-control",
            "counts_as_full_schema_verdict": True}
    c1 = dict(base, artifact_sha256=protocol_h)
    ctrl(checks, "CTRL-C1_artifact_key_only",
         "synthetic review with only artifact_sha256==protocol hash -> expression returns prefix",
         {"observed": controller_expr(c1)}, controller_expr(c1) == protocol_h[:12],
         "Sensitivity control: the expression is not type-broken.")
    c2 = dict(base, reviewed_sha256=protocol_h)
    ctrl(checks, "CTRL-C2_reviewed_key_only",
         'synthetic review with only reviewed_sha256==protocol hash -> expression returns "unbound"',
         {"observed": controller_expr(c2)}, controller_expr(c2) == "unbound",
         "Reproduces H1 on synthetic bytes, independent of the real file.")
    mutated = ("0" if protocol_h[0] != "0" else "1") + protocol_h[1:]
    c3 = dict(base, reviewed_sha256=mutated)
    ctrl(checks, "CTRL-C3_mutated_hash",
         "mutated protocol hash does not bind under the corpus prefix rule",
         {"observed": corpus_binds(c3, protocol_h)}, corpus_binds(c3, protocol_h) is False,
         "Specificity control: the corpus rule is not a rubber stamp.")
    c4a = dict(base, reviewed_sha256=protocol_h, verdict="accept")
    c4b = dict(base, reviewed_sha256=protocol_h, verdict="revise")
    ctrl(checks, "CTRL-C4_verdict_filter",
         "hash binding is verdict-agnostic; accept-set membership is filtered by verdict",
         {"accept_binds": corpus_binds(c4a, protocol_h), "revise_binds": corpus_binds(c4b, protocol_h),
          "accept_is_accept": c4a["verdict"] == "accept", "revise_is_accept": c4b["verdict"] == "accept"},
         corpus_binds(c4a, protocol_h) is True and c4b["verdict"] != "accept",
         "Both pins bind; only the accept set excludes the revise verdict.")
    c5 = controller_expr({})
    ctrl(checks, "CTRL-C5_empty",
         'expression on {} returns "unbound"', {"observed": c5}, c5 == "unbound",
         "Baseline of the reader's default branch.")

    # ---- findings ---------------------------------------------------------
    f1_ok = all(checks[i]["ok"] for i in (0, 1, 2, 3))
    findings.append({
        "id": "W027-F1",
        "severity": "major",
        "status": "CONFIRMED" if f1_ok else "NOT_REPRODUCED",
        "statement": ("The G-NUM gate reason's single-file binding reader for "
                      "reviews/G-NUM-protocol-review.json extracts only the key "
                      "`artifact_sha256` (astra_lifecycle.py:%s at controller sha %s), "
                      "while the verdict declares its pin as `reviewed_sha256`; the reader "
                      "therefore returns 'unbound' although an eligible audit-lead accept "
                      "binds the measured protocol revision %s." % (
                          src.get("proto_rev_h = str(", {}).get("line", "?"), controller_h[:12],
                          protocol_h[:12])),
        "evidence": ["reviews/G-NUM-protocol-review.json#%s" % review_h[:12],
                     "numerics/CONVERGENCE_PROTOCOL.md#%s" % protocol_h[:12],
                     "research_map/astra_lifecycle.py#%s" % controller_h[:12],
                     (os.path.relpath(best[1], ROOT) + "#" + sha256_file(best[1])[:12]) if best else None,
                     "research_map/research_map.json#%s" % map_h[:12]],
        "falsifier": ("Re-run this checker at the pinned hashes. Falsified if the review's "
                      "reviewed_sha256 != measured protocol sha256, or the review is not an "
                      "accept, or check C3 returns the protocol prefix, or the newest "
                      "lifecycle G-NUM reason no longer says 'binds unbound (stale)'."),
    })
    f2 = next((c for c in checks if c["id"] == "C6_corpus_scanner_target_universe"), None)
    findings.append({
        "id": "W027-F2",
        "severity": "major",
        "status": "CONFIRMED" if (f2 and f2["ok"]) else "NOT_REPRODUCED",
        "statement": ("The corpus-wide binding scanner cannot compensate: review_coverage() "
                      "iterates only measured node ids %s, and 'G-NUM-protocol' is not among "
                      "them (nor in TARGET_ALIASES), so no gate_audit path counts this verdict."
                      % (measured_nodes,)),
        "evidence": ["research_map/astra_lifecycle.py#%s" % controller_h[:12],
                     (os.path.relpath(best[1], ROOT) + "#" + sha256_file(best[1])[:12]) if best else None],
        "falsifier": ("A lifecycle pass in which review_coverage's target universe contains "
                      "'G-NUM-protocol' and counts the accept would falsify this finding."),
    })
    findings.append({
        "id": "W027-F3",
        "severity": "info",
        "status": "CENSUS",
        "statement": ("Scope note: single-key `get('artifact_sha256')` reads exist at "
                      "astra_lifecycle.py:%s (map node declared-hash path) and :%s (G-NUM "
                      "protocol verdict path), plus artifacts/audit/*.py; the review corpus "
                      "convention (both keys) is only implemented in _explicit_pins." % (
                          src.get('proto_rev_h = str(', {}).get("line", "?"),
                          src.get('for key in ("artifact_sha256",', {}).get("line", "?"))),
        "evidence": ["research_map/astra_lifecycle.py#%s" % controller_h[:12]],
        "falsifier": "n/a (census, not a claim about correctness of any single site).",
    })

    reproduced = all(c["ok"] for c in checks)

    # ---- byte snapshots so the measurement is replayable after drift ------
    snapshots = []
    snap_specs = [
        ("CONVERGENCE_PROTOCOL.%s.md" % protocol_h[:12], protocol_path),
        ("G-NUM-protocol-review.%s.json" % review_h[:12], review_path),
        ("astra_lifecycle.%s.py" % controller_h[:12], controller_path),
    ]
    if best:
        snap_specs.append((os.path.basename(best[1]), best[1]))
    os.makedirs(args.snapshot_dir, exist_ok=True)
    for name, src_path in snap_specs:
        with open(src_path, "rb") as fh:
            data = fh.read()
        dst = os.path.join(args.snapshot_dir, name)
        with open(dst, "wb") as fh:
            fh.write(data)
        snapshots.append({"path": os.path.relpath(dst, ROOT),
                          "sha256": sha256_bytes(data),
                          "bytes": len(data),
                          "source": os.path.relpath(src_path, ROOT),
                          "byte_identical": sha256_bytes(data) == sha256_file(src_path)})

    report = {
        "schema_version": "0.1",
        "task_id": "W027-GNUM-C8-KEYBIND-01",
        "worker": "worker-027",
        "actor": "worker-027",
        "created_at": now(),
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "verdict": "FINDING_REPRODUCED" if reproduced else "FALSIFIED",
        "measurement": ("At the pinned snapshot, criterion C8 of G-NUM is reported unmet "
                        "('binds unbound (stale)') by the controller even though an eligible "
                        "independent accept binds the measured protocol revision; the report "
                        "localizes the cause to a key-scope mismatch plus a target-universe "
                        "gap in the controller's own audit path."),
        "snapshot": {
            "protocol_path": DEFAULTS["protocol"], "protocol_sha256": protocol_h,
            "review_path": DEFAULTS["review"], "review_sha256": review_h,
            "controller_path": DEFAULTS["controller"], "controller_sha256": controller_h,
            "map_path": DEFAULTS["map"], "map_sha256": map_h,
            "newest_lifecycle_report": os.path.relpath(best[1], ROOT) if best else None,
            "newest_lifecycle_report_sha256": sha256_file(best[1]) if best else None,
            "lifecycle_reports_scanned": len(glob.glob(os.path.join(lifecycle_dir, "lifecycle_*.json"))),
        },
        "source_lines": src,
        "snapshots": snapshots,
        "checks": checks,
        "controls": [c for c in checks if c["id"].startswith("CTRL")],
        "findings": findings,
        "non_claims": [
            "not a gate verdict: worker events cannot set pending/pass/fail or node done",
            "does not modify any canonical artifact, review, map, or controller tool",
            "does not adjudicate the protocol's numerical content or N0 convergence",
            "does not assert the review's findings are correct, only that its binding is real",
        ],
        "falsifier": (
            "Re-run check_c8_binding.py at the pinned protocol/review/controller hashes "
            "(--expect-protocol %s --expect-review %s --expect-controller %s). "
            "FINDING_REPRODUCED means checks C1-C7 and CTRL-C1..C5 all hold; any failing "
            "check must flip the verdict to FALSIFIED." % (protocol_h, review_h, controller_h)),
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({"verdict": report["verdict"], "report": os.path.relpath(args.out, ROOT),
                      "failed_checks": [c["id"] for c in checks if not c["ok"]],
                      "findings": [(f["id"], f["status"]) for f in findings]}, indent=1))
    return 0 if reproduced else 3


if __name__ == "__main__":
    sys.exit(main())
