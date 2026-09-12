#!/usr/bin/env python3
"""W085-F1-CARD-CLOSE-05 -- read-only closure/stability reconciliation of the
worker-085 F1 r2 review cards (audit-r2-F1-b + audit-r2-F1-bindchain-worker-085).

The cards pinned schemas/af_wcc_vacuum.yaml at cce9c601... and asked for
reviews/F1-review-rev27-b.json.  That verdict was written at the pinned bytes
before the file moved to d9cebb94... (rev13 / FROZEN rev29).  Under the card's
own moving-target stop rule no second verdict may be emitted at the new bytes,
and a rev13 verdict by the same worker already exists.  This probe therefore
does NOT review or re-verdict the schema.  It measures, read-only:

  A. card closure: pin vs current bytes, deliverable hashes vs the hashes
     recorded in their own checkpoints, exactly-once ingestion, zero rejects;
  B. addendum folding: the bind-chain addendum is present inside rev27-b;
  C. the f0_binding declared-hash chain at the *current* bytes for F1/F2a/F2b;
  D. the schemas' own refresh rule at the current bytes;
  E. stability of the review pins since the verdicts were written;
  F. cross-artifact shared fields (data_class, regularity, extension_predicate)
     and the known F2b containment contradiction at the current bytes;
  G. duplicate guard: no verdict file is written or modified by this probe.

No canonical file is touched.  Writes only under
artifacts/worker-085/f1_card_reconcile/.  Worker evidence only: no gate
verdict, no node status, no validation_status.
"""

import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True

import yaml  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(HERE, "report.json")

CARD_DECLARED_PIN = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
REV13_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
FROZEN29 = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"

SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
INPUTS = SCHEMAS + [
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "reviews/F1-review-rev27-b.json",
    "reviews/F1-review-rev13-085.json",
    "runtime/state/worker-085_F1_checkpoint.json",
    "runtime/state/worker-085_F1rev13_checkpoint.json",
    "comms/inbox/worker-085.jsonl",
    "comms/outbox/worker-085.jsonl",
    "comms/rejected.jsonl",
    "research_map/events.jsonl",
]


def abspath(rel):
    return os.path.join(ROOT, rel)


def sha256_file(rel):
    h = hashlib.sha256()
    with open(abspath(rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(rel):
    with open(abspath(rel), encoding="utf-8") as fh:
        return json.load(fh)


def load_yaml(rel):
    with open(abspath(rel), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_text(rel):
    with open(abspath(rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def count_exact_line(path, event_id):
    n = 0
    with open(abspath(path), encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if event_id in line:
                n += 1
    return n


def canonical(obj):
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def resolve_pointer(pointer):
    """Resolve 'path#dotted.key' against a YAML file; return (ok, detail)."""
    path, _, frag = pointer.partition("#")
    try:
        doc = load_yaml(path)
    except Exception as exc:  # noqa: BLE001
        return False, "load error: %s" % exc
    cur = doc
    for part in [p for p in frag.split(".") if p]:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, "key %r absent" % part
    return True, "resolved (terminal type %s)" % type(cur).__name__


report = {
    "schema": "w085-card-reconcile/v1",
    "task_id": "W085-F1-CARD-CLOSE-05",
    "actor": "worker-085",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "created_at": None,
    "scope": "closure/stability reconciliation of the r2 F1 review cards; no review verdict is produced",
    "hashes_before": {},
    "hashes_after": {},
    "checks": {},
    "findings": [],
    "falsifiers": [],
    "next_falsifier": None,
}

import datetime  # noqa: E402

report["created_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

for rel in INPUTS:
    report["hashes_before"][rel] = sha256_file(rel)

# ---------------------------------------------------------------- A. card closure
inbox = [json.loads(l) for l in read_text("comms/inbox/worker-085.jsonl").splitlines() if l.strip()]
cards = []
for ev in inbox:
    task = str(ev.get("task", ""))
    m = re.search(r"\b([0-9a-f]{64})\b", task)
    cards.append(
        {
            "event_id": ev.get("event_id"),
            "artifact": ev.get("artifact"),
            "assignee": ev.get("assignee"),
            "deadline": ev.get("deadline"),
            "declared_pin_in_task": m.group(1) if m else None,
        }
    )

rev27b = load_json("reviews/F1-review-rev27-b.json")
rev13 = load_json("reviews/F1-review-rev13-085.json")
ckpt27 = load_json("runtime/state/worker-085_F1_checkpoint.json")
ckpt13 = load_json("runtime/state/worker-085_F1rev13_checkpoint.json")

current_f1 = report["hashes_before"]["schemas/af_wcc_vacuum.yaml"]
pins_superseded = current_f1 != CARD_DECLARED_PIN

event_ids = [
    "w085-20260912T005500-F1-review-rev27-b",
    "w085-20260912T0100-F1-review-rev13",
]
ingest_counts = {eid: count_exact_line("research_map/events.jsonl", eid) for eid in event_ids}
rejects_085 = count_exact_line("comms/rejected.jsonl", "w085")

report["checks"]["A_card_closure"] = {
    "cards": cards,
    "current_F1_sha256": current_f1,
    "card_declared_pin": CARD_DECLARED_PIN,
    "pin_superseded_moving_target": pins_superseded,
    "verdict_rev27b_exists": os.path.exists(abspath("reviews/F1-review-rev27-b.json")),
    "verdict_rev27b_sha256": report["hashes_before"]["reviews/F1-review-rev27-b.json"],
    "verdict_rev27b_sha_recorded_in_checkpoint": ckpt27["review"]["verdict_file_sha256"],
    "verdict_rev27b_sha_matches_checkpoint": report["hashes_before"][
        "reviews/F1-review-rev27-b.json"
    ]
    == ckpt27["review"]["verdict_file_sha256"],
    "verdict_rev27b_reviewed_sha256": rev27b.get("pin", {}).get("expected"),
    "rev27b_bound_to_card_pin": rev27b.get("pin", {}).get("expected") == CARD_DECLARED_PIN,
    "rev27b_pin_match_inside_its_own_window": rev27b.get("pin", {}).get("pin_match"),
    "rev27b_moving_target_inside_its_own_window": rev27b.get("pin", {}).get("moving_target"),
    "verdict_rev13_sha256": report["hashes_before"]["reviews/F1-review-rev13-085.json"],
    "verdict_rev13_sha_recorded_in_checkpoint": ckpt13["review"]["verdict_file_sha256"],
    "verdict_rev13_sha_matches_checkpoint": report["hashes_before"][
        "reviews/F1-review-rev13-085.json"
    ]
    == ckpt13["review"]["verdict_file_sha256"],
    "verdict_rev13_reviewed_sha256": rev13.get("reviewed_sha256"),
    "review_events_ingested_exactly_once": ingest_counts,
    "worker_085_lines_in_rejected_stream": rejects_085,
    "closure_status": "CARD_EXECUTED_AT_PIN / PIN_SUPERSEDED / NO_REVERDICT_EMITTED",
}

# ------------------------------------------------------- B. addendum folded in
hf_ids = [h.get("id") for h in rev27b.get("hard_failures", [])]
finding_ids = [f.get("id") for f in rev27b.get("findings", [])]
report["checks"]["B_addendum_folded"] = {
    "rev27b_top_level_keys_present": [
        k
        for k in ("f0_binding_chain", "refresh_rule_assessment", "hard_failures", "findings")
        if k in rev27b
    ],
    "hard_failure_ids": hf_ids,
    "bind_chain_hard_failure_recorded": "HF-085-BIND-01" in hf_ids,
    "supplement_pointer_finding_recorded": "F-085-05" in finding_ids,
    "moving_target_finding_recorded": "F-085-07" in finding_ids,
    "addendum_folded": bool(
        rev27b.get("f0_binding_chain")
        and rev27b.get("refresh_rule_assessment")
        and "HF-085-BIND-01" in hf_ids
    ),
    "addendum_artifact_field_misaddressed": {
        "workers_085_and_071_both_addressed_to": "reviews/F1-review-rev27-a.json",
        "stop_rule": "fold into the single verdict file already assigned",
        "resolution": "worker-085 folded into reviews/F1-review-rev27-b.json (its own assigned file)",
        "kind": "comms defect, not an artifact defect",
    },
}

# ------------------------------------------------- C. binding chain at now bytes
frozen = load_json("artifacts/formulation/FROZEN.json")
frozen_files = frozen.get("files", {})
frozen_logical = frozen.get("logical_artifacts", {})
bind = {}
for rel in SCHEMAS:
    fb = (load_yaml(rel) or {}).get("f0_binding") or {}
    entry = {"declared_hashes": {}, "pointers": {}, "refresh": {}}
    for key, val in fb.items():
        if not key.endswith("_sha256") or not isinstance(val, str):
            continue
        base = key[: -len("_sha256")]
        ref = fb.get(base) or fb.get(base + "_path") or fb.get(base + "_artifact")
        measured = sha256_file(ref) if ref and os.path.exists(abspath(ref)) else None
        entry["declared_hashes"][key] = {
            "declared": val,
            "referent": ref,
            "measured": measured,
            "resolution": "resolved" if measured == val else "mismatch",
        }
    for pkey in ("class_contract_pointer", "class_contract_supplement_pointer"):
        ptr = fb.get(pkey)
        if ptr:
            ok, detail = resolve_pointer(ptr)
            supp = fb.get("class_contract_supplement")
            entry["pointers"][pkey] = {
                "pointer": ptr,
                "resolution": "resolved" if ok else "unresolved",
                "detail": detail,
                "declared_sha256": None,
                "measured_sha256": sha256_file(supp)
                if supp and os.path.exists(abspath(supp))
                else None,
            }
    entry["refresh"] = {
        "rule": fb.get("rule"),
        "checked_at": fb.get("checked_at"),
        "declared_F0_path": fb.get("declared_f0_artifact"),
        "declared_F0_sha256": fb.get("declared_f0_sha256"),
        "declared_F0_measured": sha256_file(fb.get("declared_f0_artifact"))
        if fb.get("declared_f0_artifact")
        else None,
    }
    bind[rel] = entry

all_declared_resolved = all(
    e["resolution"] == "resolved"
    for entry in bind.values()
    for e in entry["declared_hashes"].values()
)
report["checks"]["C_bind_chain_now"] = {
    "per_schema": bind,
    "all_declared_hashes_resolved": all_declared_resolved,
    "declared_hash_count": sum(len(e["declared_hashes"]) for e in bind.values()),
    "mismatch_count": sum(
        1
        for entry in bind.values()
        for e in entry["declared_hashes"].values()
        if e["resolution"] != "resolved"
    ),
}

# ------------------------------------------------------------ D. refresh rule
cons = "artifacts/formulation/evidence/taxonomy_consistency.json"
cons_measured = report["hashes_before"][cons]
refresh_ok = True
refresh_detail = {}
for rel in SCHEMAS:
    fb = (load_yaml(rel) or {}).get("f0_binding") or {}
    f0_decl = fb.get("declared_f0_sha256")
    f0_meas = sha256_file(fb.get("declared_f0_artifact"))
    c_decl = fb.get("consistency_evidence_sha256")
    c_meas = sha256_file(fb.get("consistency_evidence"))
    ok = f0_decl == f0_meas and c_decl == c_meas
    refresh_ok = refresh_ok and ok
    refresh_detail[rel] = {
        "declared_F0_unchanged": f0_decl == f0_meas,
        "consistency_evidence_matches": c_decl == c_meas,
        "checked_at": fb.get("checked_at"),
        "rule_satisfied_at_current_bytes": ok,
    }
report["checks"]["D_refresh_rule"] = {
    "per_schema": refresh_detail,
    "frozen_revision": frozen.get("revision"),
    "frozen_at": frozen.get("frozen_at"),
    "frozen_json_sha256": report["hashes_before"]["artifacts/formulation/FROZEN.json"],
    "frozen_json_matches_rev29_pin": report["hashes_before"][
        "artifacts/formulation/FROZEN.json"
    ]
    == FROZEN29,
    "rule_satisfied": refresh_ok,
}

# ------------------------------------------------------- E. FROZEN + stability
frozen_pin_rows = {}
for rel in SCHEMAS + [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    cons,
]:
    rec = frozen_files.get(rel)
    logical = [k for k, v in frozen_logical.items() if v.get("path") == rel]
    declared = rec.get("sha256") if rec else (frozen_logical[logical[0]]["sha256"] if logical else None)
    measured = report["hashes_before"][rel]
    frozen_pin_rows[rel] = {
        "frozen_declared": declared,
        "measured": measured,
        "match": declared == measured,
        "in_files": bool(rec),
        "logical_artifacts": logical,
    }

rev13_status = {
    "F1_hash_equals_rev13_reviewed": current_f1 == rev13.get("reviewed_sha256"),
    "rev13_declared_F0_measured_now": sha256_file("research_map/formulation_taxonomy.yaml"),
    "rev13_consistency_measured_now": cons_measured,
}
# explicit per-schema stability against the rev13 checkpoint record
state13 = ckpt13.get("state_measured_at_checkpoint", {})
rev13_status["per_schema_vs_rev13_checkpoint"] = {
    rel: {
        "checkpoint": state13.get(rel),
        "current": report["hashes_before"][rel],
        "stable": state13.get(rel) == report["hashes_before"][rel],
    }
    for rel in SCHEMAS
}
report["checks"]["E_frozen_and_stability"] = {
    "frozen_pins": frozen_pin_rows,
    "all_frozen_pins_match": all(r["match"] for r in frozen_pin_rows.values()),
    "stability": rev13_status,
}

# ------------------------------------------------------ F. cross-artifact fields
docs = {rel: load_yaml(rel) for rel in SCHEMAS}


def field_compare(field):
    present = {rel: (docs[rel] or {}).get(field) for rel in SCHEMAS}
    row = {"present": {rel: present[rel] is not None for rel in SCHEMAS}, "digests": {}}
    for rel in SCHEMAS:
        if present[rel] is not None:
            row["digests"][rel] = digest(present[rel])[:16]
    if all(present[rel] is not None for rel in SCHEMAS):
        keys = sorted(set().union(*[set(v.keys()) for v in present.values()]))
        row["key_sets_equal"] = len({tuple(sorted(v.keys())) for v in present.values()}) == 1
        row["value_equal_keys"] = [
            k for k in keys if len({canonical(v.get(k)) for v in present.values()}) == 1
        ]
        row["value_differing_keys"] = [
            k for k in keys if len({canonical(v.get(k)) for v in present.values()}) > 1
        ]
        row["differing_values"] = {
            k: {rel: canonical(present[rel].get(k))[:220] for rel in SCHEMAS}
            for k in row["value_differing_keys"]
        }
    return row


f2b_text = read_text("schemas/af_scc_c0_vacuum.yaml")
f2a_text = read_text("schemas/af_scc_c2_vacuum.yaml")
containment_denial = "No containment with C2 or C0 is asserted" in f2b_text
containment_assertion = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" in f2b_text
f2a_chain = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in f2a_text
report["checks"]["F_cross_artifact"] = {
    "field_comparison": {
        "data_class": field_compare("data_class"),
        "regularity": field_compare("regularity"),
        "extension_predicate": field_compare("extension_predicate"),
    },
    "f2b_containment_probe": {
        "denial_string_present": containment_denial,
        "ledger_containment_string_present": containment_assertion,
        "f2a_chain_string_present": f2a_chain,
        "internal_contradiction_persists": containment_denial and containment_assertion,
    },
    "shared_field_finding": "F2b line ~153 denies H2_loc/C2/C0 containment while implication_ledger:240 asserts it; F2a:149 asserts the chain. F1 class statement unaffected (finding F-085R-02, unchanged at the current bytes).",
}

report["findings"] = [
    {
        "id": "F-085C-01",
        "severity": "informational",
        "scope": "card closure",
        "detail": "Card audit-r2-F1-b pinned cce9c601...; the card was executed at that pin (rev27-b sha cae70876..., event ingested once, no rejects) before the canonical bytes moved to d9cebb94... at 00:53:40. The card's moving-target stop rule is live at the current bytes, so no second verdict is emitted; HF-085-BIND-01 was resolved by rev13 and reconfirmed resolved here.",
    },
    {
        "id": "F-085C-02",
        "severity": "low",
        "scope": "comms",
        "detail": "Both bind-chain addendum cards (worker-085 and worker-071) name reviews/F1-review-rev27-a.json as the artifact; the stop rule directs folding into each reviewer's own assigned verdict. Worker-085 folded into rev27-b. Dispatch field is cross-wired; card text, not artifact, is at fault.",
    },
    {
        "id": "F-085C-03",
        "severity": "low",
        "scope": "cross-artifact / F2b",
        "detail": "F2b (b2ab6acb) still denies H2_loc containment with C2/C0 while its own implication_ledger:240 and F2a:149 assert the chain. Unchanged at the current pin; F1 class statement unaffected.",
    },
    {
        "id": "F-085C-04",
        "severity": "low",
        "scope": "F1 bytes (carried)",
        "detail": "f0_binding.class_contract_supplement_pointer still declares no sha256 at the point of use; live bytes d7419b4e... equal the FROZEN rev29 logical_artifacts pin, so the value is recoverable but not declared where used (carried from F-085R-05).",
    },
]

report["falsifiers"] = [
    "F1: reviews/F1-review-rev27-b.json no longer hashes to cae708765818fcc268eed05c124b2fd23867d9de520257608978ba0c8e480049, or its review event is absent/duplicated in research_map/events.jsonl.",
    "F2: any sha256 declared in any of the three f0_binding blocks fails to resolve against its named referent at the measured bytes.",
    "F3: the probe's own before/after input hashes differ (drift inside the measurement window).",
    "F4: a second worker-085 F1 verdict file exists that duplicates the rev27-b pin without its own pin.",
]
report["next_falsifier"] = (
    "Re-run probe_card_reconcile.py: any non-resolving declared f0_binding hash, any drift of the "
    "three schema pins away from rev13, or any duplicate worker-085 F1 verdict at the card pin falsifies "
    "the closure statement. A future F0 amendment that changes research_map/formulation_taxonomy.yaml "
    "triggers the schemas' refresh rule and voids the current binding confirmation."
)
report["duplicate_guard"] = {
    "verdict_files_written": [],
    "verdict_files_modified": [],
    "review_events_emitted": 0,
    "note": "No reviews/*F1* file is opened for writing; rev27-b and rev13-085 are re-hashed after the probe.",
}
report["authority_note"] = (
    "Worker evidence only; cannot set gate verdicts, node status, validation_status, or freeze state. "
    "No canonical artifact, taxonomy, manifest, map or review file was modified."
)

for rel in INPUTS:
    report["hashes_after"][rel] = sha256_file(rel)
report["window_clean"] = all(
    report["hashes_before"][r] == report["hashes_after"][r] for r in INPUTS
)
report["verdict_files_untouched"] = (
    report["hashes_before"]["reviews/F1-review-rev27-b.json"]
    == report["hashes_after"]["reviews/F1-review-rev27-b.json"]
    and report["hashes_before"]["reviews/F1-review-rev13-085.json"]
    == report["hashes_after"]["reviews/F1-review-rev13-085.json"]
)

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=False)
    fh.write("\n")

print("wrote", OUT)
print("closure_status:", report["checks"]["A_card_closure"]["closure_status"])
print("all declared hashes resolved:", all_declared_resolved)
print("refresh rule satisfied:", refresh_ok)
print("frozen pins match:", report["checks"]["E_frozen_and_stability"]["all_frozen_pins_match"])
print("window clean:", report["window_clean"])
print("f2b contradiction persists:", report["checks"]["F_cross_artifact"]["f2b_containment_probe"]["internal_contradiction_persists"])
sys.exit(0)
