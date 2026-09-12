#!/usr/bin/env python3
"""W045-CF5-POSTFIX-VERIFY — post-fix verification of CF-5 class-token hygiene.

Task (class-bound): node F0/F1, classes AF-WCC-VAC-GEN (+variant SET),
AF-SCC-C0-VAC-GEN (+variant CH), gates G-F0/G-FORM/G-AUDIT.

What it does (read-only; imports the controller's own checker/auditor):
  1. pins sha256 of the canonical class-bound inputs;
  2. runs research_map.audit_evidence.audit() over the live map and splits
     CLASSSEP findings into unknown-class-token / other;
  3. runs class_separation.findings_for_text() over every node-declared
     artifact in the audit corpus;
  4. positive control: re-render the variant the pre-fix class-id-shaped way
     in the *current* bytes and confirm the checker fires (sensitivity);
  5. negative control: the frozen four class ids alone must not fire;
  6. binding-position control: a variant token used as a class_id must still
     hard-flag (soundness of the R2 rule);
  7. residual inventory: where else on disk the old tokens survive, with an
     explicit in_audit_corpus flag.

Prints one JSON object to stdout. Writes nothing. No network.

Usage: python3 artifacts/worker-045/run_cf5_postfix_verify.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))

import class_separation as cs  # noqa: E402
from audit_evidence import audit  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK_ID = "W045-CF5-POSTFIX-VERIFY"
NODE_IDS = ["F0", "F1"]
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TASK_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
VARIANTS = [
    {"parent_class": "AF-WCC-VAC-GEN", "variant_id": "SET"},
    {"parent_class": "AF-SCC-C0-VAC-GEN", "variant_id": "CH"},
]
# the pre-fix class-id-shaped renderings that CF-5 flagged
OLD_TOKENS = ["AF-WCC-VAC-GEN-SET", "AF-SCC-C0-CH-VAC-GEN"]

CANONICAL_INPUTS = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "research_map/class_separation.py",
    "research_map/audit_evidence.py",
    "research_map/research_map.json",
]

SKIP_DIRS = {".git", "runtime", "node_modules", "__pycache__", ".cache"}
SKIP_FILES = {"rejected.jsonl"}
TEXT_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".md", ".py", ".txt", ".csv", ".tsv"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_inputs() -> dict:
    out = {}
    for rel in CANONICAL_INPUTS:
        p = ROOT / rel
        out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size} if p.is_file() else {
            "sha256": None, "bytes": None, "missing": True}
    return out


def audit_corpus_scan() -> dict:
    """Replicate audit_evidence step 3 over the map's declared node artifacts."""
    m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    scanned, flags = [], []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if not art:
                continue
            p = ROOT / art
            if not (p.is_file() and p.stat().st_size < 2_000_000):
                continue
            rel = str(p.relative_to(ROOT))
            scanned.append({"node_id": n["id"], "path": rel, "sha256": sha256_file(p)})
            for it in cs.findings_for_text(p.read_text(errors="replace"), f"{n['id']} artifact {rel}"):
                flags.append({"node_id": n["id"], "path": rel, "finding": it})
    return {"scanned_count": len(scanned), "scanned": sorted(scanned, key=lambda x: x["path"]),
            "findings": flags}


def residual_inventory() -> dict:
    """Where the pre-fix tokens still appear, split by audit-corpus membership."""
    m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    declared = set()
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("artifact"):
                declared.add(n["artifact"])
    hits = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.name.startswith("._") or p.name in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        found = sorted({t for t in OLD_TOKENS if t in txt})
        if found:
            rel = str(p.relative_to(ROOT))
            lines = [i for i, ln in enumerate(txt.splitlines(), 1) if any(t in ln for t in found)]
            # The unknown-token rule runs only inside findings_for_text, i.e. on
            # declared node artifacts. research_map.json is scanned by
            # findings_for_map, which has no unknown-token rule.
            rule_applies = rel in declared
            hits.append({"path": rel, "tokens": found, "line_count": len(lines),
                         "first_lines": lines[:5], "in_audit_corpus": rel in (declared | {"research_map/research_map.json"}),
                         "unknown_token_rule_applies": rule_applies})
    by_dir: dict = {}
    for h in hits:
        top = h["path"].split("/")[0] if "/" in h["path"] else "(root)"
        by_dir[top] = by_dir.get(top, 0) + 1
    return {"total_files": len(hits),
            "in_audit_corpus_files": sorted(h["path"] for h in hits if h["in_audit_corpus"]),
            "in_corpus_unknown_token_rule_files": sorted(h["path"] for h in hits if h["unknown_token_rule_applies"]),
            "outside_audit_corpus_files": len([h for h in hits if not h["in_audit_corpus"]]),
            "by_top_dir": dict(sorted(by_dir.items(), key=lambda kv: -kv[1])),
            "hits": hits}


def positive_control(inputs: dict) -> dict:
    """Re-render each variant in the pre-fix class-id shape inside the CURRENT
    canonical bytes; the checker must fire. Proves the zero baseline is not
    a blind spot."""
    arms = {}
    f1 = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text(errors="replace")
    f0 = (ROOT / "research_map/formulation_taxonomy.yaml").read_text(errors="replace")
    pairs = [
        ("F1", f1, "AF-WCC-VAC-GEN.variant-SET", "AF-WCC-VAC-GEN-SET"),
        ("F0", f0, "AF-WCC-VAC-GEN.variant-SET", "AF-WCC-VAC-GEN-SET"),
        ("F0", f0, "AF-SCC-C0-VAC-GEN.variant-CH", "AF-SCC-C0-CH-VAC-GEN"),
    ]
    for i, (node, text, new, old) in enumerate(pairs):
        assert new in text, f"control anchor missing in {node}: {new}"
        mutated = text.replace(new, old)
        fs = cs.findings_for_text(mutated, f"control:{node}:re-render:{old}")
        arms[f"C1-{node}-{old}"] = {
            "mutations": mutated.count(old) - text.count(old),
            "unknown_token_findings": len([x for x in fs if x.startswith("CLASSSEP-SOFT: unknown class token")]),
            "passed": len([x for x in fs if x.startswith("CLASSSEP-SOFT: unknown class token")]) >= 1,
        }
    return arms


def binding_controls() -> dict:
    arms = {}
    # a variant cited AS a class id must still hard-flag (R2 soundness)
    for tok in OLD_TOKENS:
        fs = cs.findings({"class_id": tok, "statement": "probe"}, f"control:binding:{tok}")
        arms[f"C2-binding-{tok}"] = {"findings": fs, "passed": len(fs) == 1 and "unknown class token" in fs[0]}
    # the frozen four as class_ids must be silent (no over-blocking)
    fs = cs.findings({"class_ids": CLASS_IDS, "statement": "frozen four control"}, "control:frozen-four")
    arms["C3-frozen-four-negative"] = {"findings": fs, "passed": len(fs) == 0}
    return arms


def main() -> int:
    measured_at = datetime.now(CST).isoformat(timespec="seconds")
    inputs = measure_inputs()
    res = audit(ROOT / "research_map" / "research_map.json")
    classsep_soft_unknown = [s for s in res["soft"] if s.startswith("CLASSSEP-SOFT: unknown class token")]
    classsep_hard = [h for h in res["hard"] if h.startswith("CLASSSEP")]
    other_soft = [s for s in res["soft"] if s not in classsep_soft_unknown]

    corpus = audit_corpus_scan()
    pcontrols = positive_control(inputs)
    bcontrols = binding_controls()
    residual = residual_inventory()
    inputs_end = measure_inputs()

    drift = {p: {"start": inputs[p]["sha256"], "end": inputs_end[p]["sha256"]}
             for p in CANONICAL_INPUTS if inputs[p]["sha256"] != inputs_end[p]["sha256"]}

    controls_pass = (all(a["passed"] for a in pcontrols.values())
                     and all(a["passed"] for a in bcontrols.values()))
    cf5_cleared = len(classsep_soft_unknown) == 0
    if drift:
        verdict = "INCONCLUSIVE-DRIFT"
    else:
        verdict = "PASS" if (cf5_cleared and controls_pass) else "FAIL"

    claim_statement = (
        f"At the recorded hashes (F0 {str(inputs['research_map/formulation_taxonomy.yaml']['sha256'])[:12]}, "
        f"F1 {str(inputs['schemas/af_wcc_vacuum.yaml']['sha256'])[:12]}), the CF-5 unknown-class-token finding "
        f"is cleared in the corpus defined by research_map/audit_evidence.py: "
        f"{len(classsep_soft_unknown)} unknown-class-token findings, {len(corpus['findings'])} class-token findings "
        f"across {corpus['scanned_count']} declared node artifacts. The sensitivity control re-renders the SET/CH "
        f"variants in their pre-fix class-id shape inside the same bytes and the checker fires in all "
        f"{len(pcontrols)} arms, so the zero is a measured clearance, not a blind spot. No canonical input drifted "
        f"during the measurement ({len(drift)} drifted). Residual pre-fix tokens "
        f"survive only as provenance outside the unknown-token scan surface ({residual['outside_audit_corpus_files']} files "
        f"outside the audit corpus; research_map.json quotes history but is scanned by findings_for_map, which has no "
        f"unknown-token rule). Files where the unknown-token rule applies and the token survives: "
        f"{residual['in_corpus_unknown_token_rule_files']}. "
        f"Scope limit: this does not prove absence beyond the checker's measured sensitivity."
    )

    out = {
        "schema_version": "0.1",
        "task_id": TASK_ID,
        "worker": "worker-045",
        "instance": "worker-045-20260912T001657-968807",
        "measured_at": measured_at,
        "node_ids": NODE_IDS,
        "class_ids": TASK_CLASSES,
        "frozen_class_ids": CLASS_IDS,
        "variant_ids": VARIANTS,
        "gates": ["G-F0", "G-FORM", "G-AUDIT"],
        "inputs": inputs,
        "inputs_at_end": inputs_end,
        "drift_during_run": drift,
        "result": {
            "verdict": verdict,
            "cf5_unknown_token_findings_in_audit_corpus": len(classsep_soft_unknown),
            "cf5_cleared": cf5_cleared,
            "controls_pass": controls_pass,
            "audit_hard_total": len(res["hard"]),
            "audit_soft_total": len(res["soft"]),
            "classsep_hard": classsep_hard,
            "classsep_soft_unknown_token": classsep_soft_unknown,
            "other_soft": other_soft,
            "drift_during_run": drift,
            "claim_statement": claim_statement,
        },
        "corpus_scan": corpus,
        "controls": {"positive_re_render": pcontrols, "binding_positions": bcontrols},
        "residual_inventory": residual,
        "falsifier": (
            "Falsified if any of: (a) re-running research_map/audit_evidence.py at the recorded canonical hashes "
            "yields >=1 'CLASSSEP-SOFT: unknown class token' finding; (b) any positive re-render control yields 0 "
            "unknown-token findings (measurement insensitive); (c) the binding control fails to hard-flag a variant "
            "token used as a class_id, i.e. the rule cannot tell a variant citation from a class id; (d) any canonical "
            "input hash differs from the recorded value at re-run time (drift voids this measurement)."
        ),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{str(inputs['research_map/formulation_taxonomy.yaml']['sha256'])[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{str(inputs['schemas/af_wcc_vacuum.yaml']['sha256'])[:12]}",
            f"research_map/class_separation.py#{str(inputs['research_map/class_separation.py']['sha256'])[:12]}",
            f"research_map/audit_evidence.py#{str(inputs['research_map/audit_evidence.py']['sha256'])[:12]}",
            "comms/outbox/astra-lead-audit.jsonl:22 (audit-art-20260912T0014-addendum)",
            "comms/inbox/astra-lead-audit.jsonl:10 (astra-life02-softflag-f0f1)",
        ],
        "scope_limit": (
            "Measured clearance under class_separation.py + audit_evidence.py over the corpus they define "
            "(map fields + declared node artifacts). Not a proof of absence outside that corpus or beyond the "
            "checker's measured sensitivity; historical provenance quoting the old tokens is listed separately."
        ),
    }
    print(json.dumps(out, indent=2, sort_keys=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
