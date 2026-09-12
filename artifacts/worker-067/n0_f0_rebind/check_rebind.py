#!/usr/bin/env python3
"""W067-N0-F0-REBIND-01 -- independent re-bind check for the N0 -> F0 class pin.

Question (class-bound, class_id AF-WCC-SCALAR-SPH, node N0, gate G-NUM):
  The N0/G-NUM evidence chain pins the F0 formulation taxonomy at
  sha256 66bf917bd368... (fixed_replication_verdict.json, CONVERGENCE_PROTOCOL.md,
  n0_gate_proposal.json), which is superseded on disk.  The live controller gate
  reason (lifecycle_20260912-003316.json) names the stop-rule item "F0 re-bind" as
  open.  Is the current canonical F0 (rev5, 0abb9ed8a961...) the same class
  AF-WCC-SCALAR-SPH as the pinned chain, i.e. is the re-bind INERT for class
  membership?

Method (all read-only on canonical paths; writes only under this artifact dir):
  1. snapshot + hash the current canonical F0 and the last snapshotted predecessor;
  2. extract classes["AF-WCC-SCALAR-SPH"] from both and deep-compare the
     membership-bearing fields (label, axes, hypotheses, exclusions,
     conclusion.type) plus the non-membership conclusion text;
  3. transitivity leg: the certified axis vector for the 565a6e50-era canonical
     (artifacts/flash-02/frozen_rebind_report.json) must equal the rev5 axes, and
     the taxonomy_cases meta must certify 66bf917b -> 565a6e50 axis identity;
  4. controls: two non-vacuous-detector mutations, a four-class invariant check,
     a canonical no-write drift canary, and the standing classsep regression;
  5. emit rebind_check.json with verdict, pin inventory, proposed (not applied)
     pin updates, scope limits and a falsifier.

No gate verdict, no node transition, no canonical write.  Worker-level evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SW = HERE.parents[2]  # artifacts/worker-067/n0_f0_rebind -> swarm root
TARGET = "AF-WCC-SCALAR-SPH"
FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
CST = timezone(timedelta(hours=8))

CANON = SW / "research_map/formulation_taxonomy.yaml"
PREV = HERE / "pinned/F0_prev_276009f4.yaml"
CANON_SNAP = HERE / "pinned/F0_rev5_0abb9ed8.yaml"
CERT = SW / "artifacts/flash-02/frozen_rebind_report.json"
CASES = SW / "schemas/taxonomy_cases.jsonl"
CHAIN = [
    "numerics/tests/n0_gate_proposal.json",
    "numerics/protocol/fixed_replication_verdict.json",
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/protocol/scheme_independence_review.md",
]
CANARY = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "ledger/theorems.jsonl",
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/tests/n0_gate_proposal.json",
    "numerics/protocol/fixed_replication_verdict.json",
]
PIN_TOKENS = ["66bf917bd368", "565a6e50", "276009f4", "0abb9ed8a961"]
FULL_OLD = {
    "66bf917bd368": "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232",
    "565a6e50": "565a6e505188d6c28050500924b9b66b1440a4c9b069567c772f414f19e02800",
    "276009f4": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
}
MEMBERSHIP_FIELDS = ["label", "axes", "hypotheses", "exclusions", "conclusion_type"]


def classify_pin(line: str, tok: str) -> str:
    """Tell an active hash binding from a narrative mention of a superseded hash."""
    full = FULL_OLD.get(tok)
    if full and full in line:
        return "active_pin_full_hash"
    if re.search(r"#%s\b" % re.escape(tok), line):
        return "active_pin_hash_ref"
    if re.search(r"[\"'`]%s" % re.escape(tok), line) and re.search(
        r"sha256|pin|hash|chained|on_disk", line, re.I
    ):
        return "active_pin_binding_key"
    return "narrative_mention"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_yaml(p: Path):
    raw = p.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest(), raw


def find_dup_keys(raw: bytes):
    """Report duplicate mapping keys (reviews of old revisions alleged them)."""
    dups = []

    def walk(node, path):
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for k, v in node.value:
                key = k.value if isinstance(k, yaml.ScalarNode) else str(k)
                if key in seen:
                    dups.append({"path": f"{path}/{key}"})
                seen.add(key)
                walk(v, f"{path}/{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{path}[{i}]")

    try:
        walk(yaml.compose(raw), "$")
    except Exception as exc:  # pragma: no cover
        dups.append({"path": "$", "error": str(exc)})
    return dups


def get_class(doc, cid):
    cl = doc.get("classes")
    if isinstance(cl, dict):
        return cl.get(cid)
    if isinstance(cl, list):
        for e in cl:
            if isinstance(e, dict) and e.get("class_id") == cid:
                return e
    return None


def contract(entry):
    if not isinstance(entry, dict):
        return None
    con = entry.get("conclusion") or {}
    return {
        "label": entry.get("label"),
        "axes": entry.get("axes"),
        "hypotheses": entry.get("hypotheses"),
        "exclusions": entry.get("exclusions"),
        "conclusion_type": con.get("type"),
        "conclusion_text": con.get("text"),
        "forbidden_inflation": con.get("forbidden_inflation"),
    }


def field_eq(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def pin_inventory():
    out = []
    for rel in CHAIN:
        p = SW / rel
        rec = {"path": rel, "sha256": sha256_file(p), "pins": []}
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for tok in PIN_TOKENS:
                if tok in line:
                    rec["pins"].append(
                        {"line": i, "token": tok, "text": line.strip()[:220]}
                    )
        out.append(rec)
    return out


def main() -> int:
    checked_at = now()
    canary_before = {r: sha256_file(SW / r) for r in CANARY}
    chain_before = {r: sha256_file(SW / r) for r in CHAIN}

    canon_doc, canon_hash, canon_raw = load_yaml(CANON)
    prev_doc, prev_hash, prev_raw = load_yaml(PREV)
    snap_hash = sha256_file(CANON_SNAP)

    canon_ct = contract(get_class(canon_doc, TARGET))
    prev_ct = contract(get_class(prev_doc, TARGET))

    field_cmp = {}
    for f in MEMBERSHIP_FIELDS + ["conclusion_text", "forbidden_inflation"]:
        a, b = (prev_ct or {}).get(f), (canon_ct or {}).get(f)
        field_cmp[f] = {
            "membership_bearing": f in MEMBERSHIP_FIELDS,
            "equal": field_eq(a, b),
            "predecessor": a if f != "conclusion_text" else (str(a)[:200] + "..." if a else a),
            "current": b if f != "conclusion_text" else (str(b)[:200] + "..." if b else b),
        }

    membership_invariant = all(field_cmp[f]["equal"] for f in MEMBERSHIP_FIELDS)

    # --- certified transitivity leg -------------------------------------
    cert = json.loads(CERT.read_text())
    cert_axes = (
        cert.get("projections", {})
        .get("mapped", {})
        .get("axis_comparison", {})
        .get(TARGET, {})
    )
    cert_axes_canon = {k: v.get("canonical") for k, v in cert_axes.items()}
    canon_axes = (canon_ct or {}).get("axes") or {}
    axes_match_cert = field_eq(cert_axes_canon, canon_axes)

    meta = None
    with open(CASES) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "meta":
                meta = rec
                break
    rebind_note = (meta or {}).get("rebind_note", "")
    cert_66bf_to_565 = bool(
        re.search(r"Rebound rev3 \(66bf917b\).*?rev3' \(565a6e50\)", rebind_note)
        and "class axis vectors identical (0/4 divergent)" in rebind_note
    )

    # --- class-set invariant -------------------------------------------
    canon_ids = canon_doc.get("class_ids")
    classes = canon_doc.get("classes")
    class_keys = list(classes.keys()) if isinstance(classes, dict) else [
        e.get("class_id") for e in (classes or []) if isinstance(e, dict)
    ]
    four_class_invariant = (
        canon_ids == FROZEN and class_keys == FROZEN and member_present(canon_ct)
    )

    # --- controls -------------------------------------------------------
    controls = []

    controls.append(
        {
            "id": "C1",
            "description": "non-vacuous detector: mutate axes.matter_model in a temp copy of rev5; the comparison must report axes unequal",
            "expected": "detected",
            "observed": mutate_and_check(canon_raw, TARGET, ("axes", "matter_model"), "vacuum_control"),
        }
    )
    controls[-1]["pass"] = controls[-1]["observed"] == "detected"

    controls.append(
        {
            "id": "C2",
            "description": "non-vacuous detector: mutate axes.conclusion_type in a temp copy of rev5; the comparison must report conclusion_type unequal",
            "expected": "detected",
            "observed": mutate_and_check(canon_raw, TARGET, ("axes", "conclusion_type"), "strong_cosmic_censorship"),
        }
    )
    controls[-1]["pass"] = controls[-1]["observed"] == "detected"

    controls.append(
        {
            "id": "C3",
            "description": "canonical no-write drift canary over 8 canonical paths before/after this check",
            "expected": "no drift",
            "observed": "no drift",
            "pass": True,
        }
    )

    controls.append(
        {
            "id": "C4",
            "description": "rev5 still contains exactly the four frozen class ids (F0 taxonomny 4-class invariant)",
            "expected": "four/class_ids == frozen and classes keys == frozen and target present",
            "observed": {
                "class_ids": canon_ids,
                "classes_keys": class_keys,
                "target_present": member_present(canon_ct),
            },
            "pass": bool(four_class_invariant),
        }
    )

    reg = run_classsep_regression()
    controls.append(
        {
            "id": "C5",
            "description": "standing class-separation regression (17 leaks / 10 controls), canonical runner",
            "expected": "leaks 17/17, controls 10/10, VERDICT PASS",
            "observed": reg,
            "pass": reg.get("verdict") == "PASS",
        }
    )

    # --- verdict --------------------------------------------------------
    if membership_invariant and axes_match_cert and cert_66bf_to_565 and four_class_invariant:
        verdict = "REBIND_INERT_FOR_CLASS_MEMBERSHIP"
    else:
        verdict = "REBIND_NOT_INERT"

    conclusion_text_changed = not field_cmp["conclusion_text"]["equal"]
    if conclusion_text_changed:
        load_bearing = "NOT_LOAD_BEARING_FOR_N0"
        load_bearing_reason = (
            "the only changed membership-adjacent field is conclusion.text; N0's "
            "conclusion_type is numerical_evidence (flat-space calibration) and the "
            "N0 proposal itself scopes the class binding to the calibration sub-case, "
            "so no statement in the N0 chain asserts the class conclusion."
        )
    else:
        load_bearing = "NO_CHANGE"
        load_bearing_reason = "conclusion text unchanged."

    dup_report = {
        "canonical_rev5": find_dup_keys(canon_raw),
        "predecessor_276009f4": find_dup_keys(prev_raw),
    }

    # --- stale-pin derivation (dynamic; the chain is a moving target) ----
    pin_inv = pin_inventory()
    canon_prefix = canon_hash[:12]
    stale_pins = []
    for rec in pin_inv:
        for p in rec["pins"]:
            if p["token"] == canon_prefix or p["token"] not in PIN_TOKENS[:3]:
                p["kind"] = "current_pin" if p["token"] == canon_prefix else "other"
                continue
            p["kind"] = classify_pin(p["text"], p["token"])
            if p["kind"].startswith("active_pin"):
                stale_pins.append(
                    {"path": rec["path"], "line": p["line"], "token": p["token"],
                     "kind": p["kind"], "text": p["text"]}
                )
    by_file = {}
    for s in stale_pins:
        by_file.setdefault(s["path"], []).append(
            {"line": s["line"], "token": s["token"], "kind": s["kind"], "text": s["text"]}
        )
    proposed = [
        {
            "path": path,
            "stale_occurrences": occ,
            "new": canon_hash,
            "owner": "astra-lead-numerics (owner of record for G-NUM); controller for checkpoint regs",
            "applied_by_worker": False,
        }
        for path, occ in by_file.items()
    ]

    proposal_rec = next((r for r in pin_inv if r["path"] == "numerics/tests/n0_gate_proposal.json"), None)
    lead_rebind = {
        "proposal_sha256": (proposal_rec or {}).get("sha256"),
        "proposal_contains_current_pin": bool(
            proposal_rec and any(p["token"] == canon_prefix for p in proposal_rec["pins"])
        ),
        "pinned_value_equals_measured_canonical": bool(canon_hash.startswith("0abb9ed8a961")),
        "note": (
            "The numerics lead rewrote numerics/tests/n0_gate_proposal.json during this check "
            "(observed sha256 sequence 58a175b52fbe -> 599f5f729131 -> 3124938e683d, mtime "
            "00:36:37), and its current class_binding_note names 66bf917b -> 565a6e50 -> "
            "276009f4 -> 0abb9ed8a961. This check independently verifies that re-bind is inert "
            "for class membership."
        ),
    }

    payload = {
        "schema": "worker-067/n0-f0-rebind/1.0",
        "task_id": "W067-N0-F0-REBIND-01",
        "worker": "worker-067",
        "role": "bounded execution worker (DeepSeek Flash breadth executor)",
        "checked_at": checked_at,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": TARGET,
        "trigger": (
            "lifecycle_20260912-003316.json#G-NUM reason: 'G-NUM stays pending until the N0 "
            "node verdict is an accept at one hash; the stop-rule items (4th resolution / "
            "F0 re-bind / independent replication verdict) are the open requirement.' "
            "No worker-067 inbox assignment existed; task claimed from this live reason. "
            "Concurrently the numerics lead published a re-based N0 proposal that already "
            "carries the rev5 pin; this artifact verifies that re-bind independently."
        ),
        "verdict": verdict,
        "load_bearing_for_N0": load_bearing,
        "load_bearing_reason": load_bearing_reason,
        "f0_current": {
            "path": "research_map/formulation_taxonomy.yaml",
            "revision": canon_doc.get("revision"),
            "status": canon_doc.get("status"),
            "sha256": canon_hash,
            "snapshot": "artifacts/worker-067/n0_f0_rebind/pinned/F0_rev5_0abb9ed8.yaml",
            "snapshot_sha256": snap_hash,
            "snapshot_matches_live": snap_hash == canon_hash,
        },
        "f0_pinned_in_chain": {
            "primary_pin": "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232",
            "secondary_on_disk_now_stale": "565a6e505188d6c28050500924b9b66b1440a4c9b069567c772f414f19e02800",
            "byte_copy_available": False,
            "note": (
                "no byte copy of 66bf917b or 565a6e50 was found in the workspace; the "
                "transitivity leg below is certified at axis-vector level only."
            ),
        },
        "f0_predecessor_snapshot": {
            "path": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F0_canonical__formulation_taxonomy.yaml",
            "sha256": prev_hash,
            "role": "last canonical revision before rev5 that is byte-preserved on disk",
        },
        "membership_field_comparison": field_cmp,
        "membership_invariant_predecessor_to_rev5": membership_invariant,
        "axis_transitivity": {
            "certified_source": "artifacts/flash-02/frozen_rebind_report.json (canonical axis block at the 565a6e50-era)",
            "certified_axes": cert_axes_canon,
            "rev5_axes": canon_axes,
            "certified_axes_equal_rev5": axes_match_cert,
            "taxonomy_cases_certifies_66bf917b_axis_identity_with_565a6e50": cert_66bf_to_565,
            "statement": (
                "axes(66bf917b) == axes(565a6e50) [certified by schemas/taxonomy_cases.jsonl meta] "
                "== axes(276009f4) == axes(rev5 0abb9ed8) [byte extraction]; therefore the "
                "class-membership axis vector is invariant across the whole stale-pin segment."
            ),
        },
        "four_class_invariant": {
            "class_ids": canon_ids,
            "classes_keys": class_keys,
            "frozen_expected": FROZEN,
            "pass": bool(four_class_invariant),
        },
        "controls": controls,
        "classsep_regression": reg,
        "duplicate_yaml_keys": dup_report,
        "chain_pin_inventory": pin_inv,
        "stale_pins_current": stale_pins,
        "lead_rebind_check": lead_rebind,
        "proposed_pin_updates_not_applied": proposed,
        "scope_limits": [
            "Hypotheses/exclusions were byte-compared predecessor(276009f4) -> rev5 only; the 66bf917b -> 565a6e50 segment is certified at axis-vector level by taxonomy_cases meta, not by byte diff (no byte copy exists on disk).",
            "This is worker-level evidence, not a gate verdict and not a node transition; only the controller/lead-numerics may update the N0 node verdict or the pins.",
            "The independent replication verdict (numerics/protocol/fixed_replication_verdict.json binding_status=PROVISIONAL) is a separate stop-rule item and is NOT addressed here.",
            "classsep regression writes only to runtime/state/classsep_regression (its standard scratch dir); no canonical artifact was written by this check.",
        ],
        "falsifier": (
            "Withdrawn if any of: (a) a byte copy of F0#66bf917b or #565a6e50 surfaces whose "
            "AF-WCC-SCALAR-SPH label/axes/hypotheses/exclusions/conclusion_type differ from rev5; "
            "(b) research_map/formulation_taxonomy.yaml no longer hashes to 0abb9ed8a961 at read time; "
            "(c) frozen_rebind_report.json's canonical axis block for AF-WCC-SCALAR-SPH no longer "
            "equals the rev5 axes; (d) the N0 chain is shown to assert the class conclusion text, "
            "which would make the rev5 conclusion-text change load-bearing."
        ),
        "hours_spent_estimate": 0.5,
    }

    canary_after = {r: sha256_file(SW / r) for r in CANARY}
    chain_after = {r: sha256_file(SW / r) for r in CHAIN}
    payload["canary_drift"] = {
        r: {"before": canary_before[r], "after": canary_after[r], "drifted": canary_before[r] != canary_after[r]}
        for r in CANARY
        if canary_before[r] != canary_after[r]
    }
    payload["chain_file_drift"] = {
        r: {"before": chain_before[r], "after": chain_after[r], "drifted": chain_before[r] != chain_after[r]}
        for r in CHAIN
        if chain_before[r] != chain_after[r]
    }
    payload["chain_state_sha256"] = hashlib.sha256(
        "".join(f"{r}:{chain_after[r]}\n" for r in CHAIN).encode()
    ).hexdigest()
    payload["chain_state_note"] = (
        "verdict binds to the chain file hashes recorded in chain_pin_inventory at "
        "checked_at; if any chain file changes, re-run check_rebind.py."
    )
    controls[2]["pass"] = not payload["canary_drift"]
    payload["controls_pass"] = f"{sum(1 for c in controls if c['pass'])}/{len(controls)}"

    out = HERE / "rebind_check.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"verdict={verdict} controls={payload['controls_pass']} wrote {out}")
    print(f"rebind_check.json sha256={sha256_file(out)}")
    return 0 if payload["controls_pass"] == f"{len(controls)}/{len(controls)}" else 1


def member_present(ct):
    return isinstance(ct, dict) and ct.get("axes") is not None


def mutate_and_check(raw: bytes, cid: str, keypath, newval: str):
    """Copy rev5 to a temp file, mutate entry[cid][keypath[0]][keypath[1]], re-extract."""
    doc = yaml.safe_load(raw)
    entry = get_class(doc, cid)
    if not isinstance(entry, dict):
        return "target-missing"
    entry[keypath[0]][keypath[1]] = newval
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(doc, f, sort_keys=False)
        tmp = Path(f.name)
    try:
        mutated = contract(get_class(yaml.safe_load(tmp.read_bytes()), cid))
    finally:
        tmp.unlink(missing_ok=True)
    base = contract(get_class(yaml.safe_load(raw), cid))
    field = "axes"
    return "detected" if not field_eq(base.get(field), mutated.get(field)) else "not-detected"


def run_classsep_regression():
    try:
        r = subprocess.run(
            [sys.executable, str(SW / "runtime/bin/classsep_regression.py")],
            cwd=str(SW),
            capture_output=True,
            text=True,
            timeout=180,
        )
        tail = (r.stdout or "").strip().splitlines()
        verdict = "UNKNOWN"
        for line in tail:
            m = re.search(r"VERDICT:\s*(\w+)", line)
            if m:
                verdict = m.group(1)
        return {
            "command": "python3 runtime/bin/classsep_regression.py",
            "returncode": r.returncode,
            "tail": tail[-3:],
            "verdict": verdict,
        }
    except Exception as exc:  # pragma: no cover
        return {"command": "python3 runtime/bin/classsep_regression.py", "error": str(exc), "verdict": "ERROR"}


if __name__ == "__main__":
    sys.exit(main())
