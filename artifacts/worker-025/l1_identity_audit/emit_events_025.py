#!/usr/bin/env python3
"""Emit the W025-L1-IDENTITY-AUDIT-01 outbox events (append-only, validated).

Writes to comms/outbox/worker-025.jsonl only. Refuses to append an event whose
required fields are missing for its event_type.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "comms", "outbox", "worker-025.jsonl")

BASE = "artifacts/worker-025/l1_identity_audit"
TS = "2026-09-12T01:26:00+08:00"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
LEDGER = "ledger/citation_audit.csv#315c19145065"
THEOREMS = "ledger/theorems.jsonl#a1674f094979"
RUBRIC = "evaluation_rubric.yaml#d748a9e3574e"


def sha12(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


EV = []


def add(d):
    EV.append(d)


# --- artifact events -------------------------------------------------------
ARTIFACTS = [
    ("art-prereg", BASE + "/PREREGISTRATION.json", "preregistration",
     "Preregistration fixed before the first fetch: population, resolver method, frozen title thresholds (Jaccard>=0.60 or ratio>=0.80), verdict vocabulary, and four falsifiers."),
    ("art-report", BASE + "/report.json", "measurement_report",
     "Machine census of all 97 rows: per-row identifier resolutions, both-channel comparison for the 59 dual rows, frozen-threshold metrics, 10 duplicate-identifier groups, resolver-agency accounting."),
    ("art-manifest", BASE + "/cache_manifest.json", "fetch_provenance",
     "114 cached registry bodies with request URL, HTTP status and body sha256, so every bibliographic field in report.json is re-hashable."),
    ("art-script", BASE + "/run_identity_audit_025.py", "measurement_script",
     "Deterministic runner; --offline rebuilds report.json from the shipped cache with no network and no timestamp, so the report is byte-identical between fetch and replay."),
    ("art-readme", BASE + "/README.md", "measurement_readme",
     "Findings with verified counts, the two resolver defects found and fixed in-pass, scope discipline, and the exact falsifier."),
    ("art-review", "reviews/L1-identity-audit-025.json", "independent_review",
     "Independent measurement verdict: revise-scope-none / no identity defect found; F1-F7 findings, no hard failures, no gate verdict claimed."),
]
for suffix, rel, atype, note in ARTIFACTS:
    add({
        "event_id": "w025-l1id-20260912T012600-%s" % suffix,
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASSES,
        "artifact_type": atype,
        "path": rel,
        "sha256": sha12(rel),
        "validation_status": "unverified",
        "summary": note,
        "evidence_refs": [LEDGER, THEOREMS, RUBRIC, rel + "#" + sha12(rel)],
        "non_claim": "Worker artifact event; cannot set validation_status=passed, status=done, or a gate verdict.",
    })

# --- review event ----------------------------------------------------------
add({
    "event_id": "w025-l1id-20260912T012600-review",
    "event_type": "review",
    "created_at": TS,
    "actor": "worker-025",
    "reviewer": "worker-025",
    "target_id": "L1",
    "gate": "G-LIT",
    "class_id": CLASSES,
    "verdict": "revise",
    "score": 4.0,
    "counts_as_gate_verdict": False,
    "counts_as_full_schema_verdict": False,
    "counts_as_independent": True,
    "independence_of": [
        "artifacts/worker-076/l1_spotcheck_frozen/spotcheck_report.json",
        "artifacts/worker-099/l1_spotcheck/spotcheck-l1-099.json",
        "reviews/L1-spotcheck-10.json",
        "reviews/L1-spotcheck-11.json",
    ],
    "hard_failures": [],
    "summary": "Independent full-population identity census at the frozen hash: 95/97 rows resolve at least one identifier, 59/59 dual-identifier rows resolve both channels title-compatibly, 0 identity mismatches, 0 title mismatches, 0 fetch failures. 26/92 DOIs live only at DataCite (25 arXiv 10.48550/*), invisible to a Crossref-only checker. 18 year flags are preprint->journal offsets with 0 author flags after surname-token correction. Scope-limited: does not re-adjudicate evidence excerpts (worker-099 SRC-025 FAIL stands) and sets no gate verdict.",
    "findings": [
        {"id": "W025-L1ID-F1", "severity": "info", "finding": "Identifier layer clean population-wide: 0/97 rows resolve to a title-contradicting work; 46/59 dual rows carry an explicit registry cross-link and 13 agree by title at the frozen thresholds."},
        {"id": "W025-L1ID-F2", "severity": "medium", "finding": "26/92 DOI rows are Crossref-invisible: 25 are arXiv-issued 10.48550/* DOIs registered at DataCite, plus one thesis DOI (SRC-007). A Crossref-only checker yields 26 spurious unresolvable rows."},
        {"id": "W025-L1ID-F3", "severity": "low", "finding": "18/97 rows carry an arXiv-preprint year 2-6 years earlier than the declared journal year; 0 author-overlap flags after surname-token correction."},
        {"id": "W025-L1ID-F4", "severity": "low", "finding": "10 duplicate-identifier groups cite one work from two citation ids, often binding one via arXiv and one via journal DOI; dedup must key on the resolved record, not the identifier string."},
        {"id": "W025-L1ID-F5", "severity": "info", "finding": "SRC-011 is a legitimate 1969/2002 reprint binding: the DOI resolves to the 'Golden Oldie' reprint already recorded in the row's venue field."},
        {"id": "W025-L1ID-F6", "severity": "info", "finding": "SRC-020 and SRC-044 are INSPIRE-only; both records resolve live to the declared titles. A locator policy should state whether an INSPIRE record id is an acceptable sole locator."},
        {"id": "W025-L1ID-F7", "severity": "low", "finding": "SRC-057/SRC-086 are one paper whose declared titles differ by a dropped subtitle (Jaccard 0.583); no row verdict is affected, but it shows the frozen thresholds are sensitive on long titles."},
    ],
    "evidence_refs": [
        LEDGER, THEOREMS, RUBRIC,
        BASE + "/report.json#" + sha12(BASE + "/report.json"),
        BASE + "/cache_manifest.json#" + sha12(BASE + "/cache_manifest.json"),
        BASE + "/README.md#" + sha12(BASE + "/README.md"),
        "reviews/L1-identity-audit-025.json#" + sha12("reviews/L1-identity-audit-025.json"),
        "artifacts/worker-099/l1_spotcheck/spotcheck-l1-099.json",
        "artifacts/worker-076/l1_spotcheck_frozen/spotcheck_report.json",
    ],
    "falsifier": "Re-run run_identity_audit_025.py --offline on the shipped 114-body cache: falsified if report.json does not re-measure to 5bd6b3263feaf9ff497a1c96c2afb269e9c7cad088d1c377e1b016d1d4f3603b, if any row verdict differs, or if a cached DOI/arXiv body pair for a row reported clean is shown to be two different works.",
})

# --- claim event -----------------------------------------------------------
add({
    "event_id": "w025-l1id-20260912T012600-claim",
    "event_type": "claim",
    "created_at": TS,
    "actor": "worker-025",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_id": CLASSES,
    "conclusion_type": "formal_model",
    "statement": "At ledger/citation_audit.csv#315c19145065, the declared identifier layer resolves to the declared works for every row that carries an identifier: 95/97 rows (the other 2, SRC-020 and SRC-044, are INSPIRE-only and resolve there), with 0 identity mismatches, 0 declared-title mismatches and 0 fetch failures across the full population; all 59 rows carrying both a DOI and an arXiv id resolve both channels title-compatibly. 66 DOIs are held by Crossref and 26 only by DataCite (25 arXiv-issued 10.48550/* plus one thesis DOI). 18 rows carry a preprint-vs-journal year offset and 0 carry an author contradiction at surname level. This is an identifier-identity census only: it does not endorse the evidence excerpts, does not supersede the W025-L1-LOCATOR-ADJ-01 finding that 71/97 exact_locator values are not record locators, and establishes no rubric hard failure.",
    "assumptions": [
        "the reviewed bytes are ledger/citation_audit.csv#315c19145065 (unchanged by this task)",
        "title identity is decided by the preregistered rule Jaccard>=0.60 or difflib ratio>=0.80 on normalized titles",
        "author identity is decided at surname-token level because registries abbreviate given names inconsistently",
        "a year offset of more than one year is reported as a flag, not normalized away",
        "DataCite is the correct registration agency for DOI prefixes Crossref does not hold (10.48550/*)",
    ],
    "falsifier": "Re-run run_identity_audit_025.py --offline on the shipped cache: falsified if report.json does not re-measure to 5bd6b3263fea, if the census totals change, if any cached DOI/arXiv body pair for a row reported clean is shown to be two different works, or if a row reported clean has a cached record contradicting the declared authors at surname level.",
    "evidence_refs": [
        LEDGER, THEOREMS, RUBRIC,
        BASE + "/PREREGISTRATION.json#" + sha12(BASE + "/PREREGISTRATION.json"),
        BASE + "/report.json#" + sha12(BASE + "/report.json"),
        BASE + "/cache_manifest.json#" + sha12(BASE + "/cache_manifest.json"),
        BASE + "/run_identity_audit_025.py#" + sha12(BASE + "/run_identity_audit_025.py"),
        "reviews/L1-identity-audit-025.json#" + sha12("reviews/L1-identity-audit-025.json"),
    ],
    "artifact_refs": [
        BASE + "/report.json#" + sha12(BASE + "/report.json"),
        BASE + "/cache_manifest.json#" + sha12(BASE + "/cache_manifest.json"),
        BASE + "/run_identity_audit_025.py#" + sha12(BASE + "/run_identity_audit_025.py"),
        BASE + "/README.md#" + sha12(BASE + "/README.md"),
        "reviews/L1-identity-audit-025.json#" + sha12("reviews/L1-identity-audit-025.json"),
    ],
})

# --- status event ----------------------------------------------------------
add({
    "event_id": "w025-l1id-20260912T012600-status",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-025",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_id": CLASSES,
    "status": "active",
    "hours": 0.5,
    "summary": "W025-L1-IDENTITY-AUDIT-01 complete and bounded (self-selected: no inbox card for worker-025; the open G-LIT evidence-hygiene work had 12/97 rows of hash-bound independent coverage). Full-population identifier->record census: 77 clean IDENTITY_MATCH, 18 IDENTITY_MATCH_WITH_AUTHOR_YEAR_FLAG, 2 NO_IDENTIFIER, 0 mismatch, 0 fetch failure; 95/97 rows resolve, 59/59 dual rows resolve both channels. Found and fixed two resolver defects in-pass (legacy arXiv id normalization; DataCite fallback for 25 arXiv-issued DOIs) that had produced 31 spurious failures. Deterministic offline replay; no live file written; no gate or node verdict claimed.",
    "evidence_refs": [
        LEDGER, THEOREMS, RUBRIC,
        BASE + "/report.json#" + sha12(BASE + "/report.json"),
        BASE + "/cache_manifest.json#" + sha12(BASE + "/cache_manifest.json"),
        "reviews/L1-identity-audit-025.json#" + sha12("reviews/L1-identity-audit-025.json"),
    ],
    "next_falsifier": "Owner decision on locator policy (INSPIRE-only rows) and duplicate-id dedup; or re-run run_identity_audit_025.py --offline and obtain a different report hash or census.",
})

# --- validate and append ---------------------------------------------------
REQUIRED = {
    "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type", "path", "sha256", "validation_status"],
    "review": ["event_id", "event_type", "created_at", "actor", "target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
    "claim": ["event_id", "event_type", "created_at", "actor", "class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
    "status": ["event_id", "event_type", "created_at", "actor", "node_id", "status", "hours", "summary", "evidence_refs", "next_falsifier"],
    "blocker": ["event_id", "event_type", "created_at", "actor", "node_id", "description", "needed_to_unblock", "evidence_refs"],
    "direction_update": ["event_id", "event_type", "created_at", "actor", "group_id", "old_direction", "new_direction", "reason", "evidence_refs", "budget_delta_agent_hours"],
    "resource_request": ["event_id", "event_type", "created_at", "actor", "group_id", "requested_agents", "requested_agent_hours", "justification", "expected_information_gain", "stop_rule"],
}
ids = set()
for e in EV:
    for k in REQUIRED[e["event_type"]]:
        if k not in e:
            sys.exit("event %s missing required field %s" % (e["event_id"], k))
    if e["event_id"] in ids:
        sys.exit("duplicate event_id %s" % e["event_id"])
    ids.add(e["event_id"])

# refuse to duplicate events already in the outbox
existing = set()
if os.path.exists(OUT):
    with open(OUT, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                existing.add(json.loads(line)["event_id"])
new = [e for e in EV if e["event_id"] not in existing]
with open(OUT, "a", encoding="utf-8") as fh:
    for e in new:
        fh.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n")

print("validated %d events; appended %d new (already present: %d)"
      % (len(EV), len(new), len(EV) - len(new)))
for e in new:
    print(" ", e["event_type"], e["event_id"])
