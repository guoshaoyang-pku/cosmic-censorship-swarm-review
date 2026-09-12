#!/usr/bin/env python3
"""W068-FORM-POLARITY-10 corpus builder.

Bounded follow-up to FORM-HELDOUT-09. HELDOUT-09 measured a single union escape:
c0_03_conclusion_negated, in which the C0 conclusion statement is logically inverted
while class_id / conclusion_type stay valid, and neither stage detects it.

This builder constructs a *polarity probe* corpus that asks how general that blind
spot is. Every probe is a class-schema YAML whose conclusion CONTENT is inverted by
one explicit, deterministic operation while the class-identifying tokens
(class_id, conclusion.family, conclusion.conclusion_type for the ops that do not
target it) and all required slots are preserved.

Target: the two pinned class-binding stages and the pinned rule spec, applied to
fixtures derived from the canonical class schemas measured live at build time. The
bases are byte copies, so the fixture set is a snapshot and later canonical
republish does not change the probes (see manifest.target_binding.note).

Usage: python3 build_corpus.py
Exit 0 on success; 2 on precondition failure (canonical unreadable / op not applicable).
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # ai4math-swarm/
CST = timezone(timedelta(hours=8))

CANON = {
    "W": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "C2": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "C0": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
CLASS = {
    "W": "AF-WCC-VAC-GEN",
    "C2": "AF-SCC-C2-VAC-GEN",
    "C0": "AF-SCC-C0-VAC-GEN",
}
FROZEN_MANIFEST = ROOT / "artifacts" / "formulation" / "FROZEN.json"
GATE_A = "artifacts/formulation/tools/check_class_schema.py"
GATE_B = "artifacts/worker-06/spec_conformance_audit.py"
RULE_SPEC = "artifacts/formulation/rule_spec.json"

# known-rejected liveness controls (FORM-HELDOUT-07 rebased; all measured rejected by
# stage A in HELDOUT-09) and the HELDOUT-09 escape reference (c0_03).
KNOWN_REJECTED = [
    ("h06_genericity_kind_swap.yaml", "genericity-kind-swap", "R21"),
    ("h19_h2loc_substitution.yaml", "h2loc-substitution", "R18/R31"),
    ("h26_quantifier_order.yaml", "quantifier-order", "R27"),
]
KNOWN_ESCAPE_REF = ROOT / "artifacts" / "worker-068" / "heldout3" / "mutants" / "c0_03_conclusion_negated.yaml"
KNOWN_ESCAPE_SHA = "1e8898ac7bad1b7db81961e9d27b05cc7e7ef8562d5c89a53c1e4a1afeea1f36"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_path(doc, path: str):
    cur = doc
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def set_path(doc, path: str, value) -> None:
    parts = path.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def replace_once(text: str, old: str, new: str, where: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"op not applicable ({where}): expected exactly one {old!r}, found {text.count(old)}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Probe ops. Each entry: (op_id, family, op_kind, expected_rules, leak_claim)
# op_kind: "common" applied to all three classes, "W" only to WCC.
# The op mutates conclusion (and, for p4, conclusion_type) content only.
# ---------------------------------------------------------------------------
COMMON_OPS = [
    ("p1_flip_negated_existence", "conclusion-polarity-inner-negation", "common", ["R27"],
     "The inner negated-existence of the formal conclusion is flipped to a positive existence: the schema now asserts the existence of the forbidden object while every class token is kept."),
    ("p2_negate_formal_outer", "conclusion-polarity-outer-negation", "common", ["NONE"],
     "The whole formal conclusion is wrapped in an explicit outer negation: the schema asserts not(P) where P is the frozen conclusion, while every class token is kept."),
    ("p3_negate_natural_language", "conclusion-polarity-nl-negation", "common", ["NONE"],
     "The natural-language conclusion is negated ('It is not the case that ...'); the formal statement is untouched, so the two conclusion fields now contradict each other."),
    ("p4_conclusion_type_token_flip", "conclusion-polarity-token-flip", "common", ["R11"],
     "The conclusion_type token is inverted (inextendibility -> extendibility, WCC -> its negation form) while class_id and family stay valid: a vocabulary-level polarity inversion."),
]
W_ONLY_OPS = [
    ("p5_iplus_completeness_flip", "conclusion-polarity-iplus-completeness", "W", ["NONE"],
     "The WCC conjunct 'complete(I+_D)' is negated in both the formal and natural-language conclusion: the schema now asserts an incomplete future null infinity, the opposite of the WCC content."),
    ("p6_visibility_flip", "conclusion-polarity-visibility", "W", ["NONE"],
     "The WCC visibility conjunct is inverted ('no singularity visible from I+' -> 'a singularity visible from I+'): the schema asserts the existence of the visible singularity that WCC forbids."),
]
C0_ONLY_OPS = [
    ("p7_heldout09_conclusion_negation_rebuilt", "conclusion-polarity-heldout09-rebuild", "C0", ["NONE"],
     "Exact reproduction of the HELDOUT-09 c0_03 conclusion inversion (formal and natural-language C0 conclusion negated, class tokens kept) rebuilt on the rev12 C0 base, which no longer carries the stale 'revised_at_unused' key. Isolates the polarity content from the key-hygiene artifact that now masks the original fixture bytes."),
]
OP_CLASSES = {
    "common": ["W", "C2", "C0"],
    "W": ["W"],
    "C0": ["C0"],
}


def apply_probe(doc, base_key: str, op_id: str, op_kind: str) -> None:
    c = doc["conclusion"]
    if op_id == "p1_flip_negated_existence":
        c["statement_formal"] = replace_once(c["statement_formal"], "not exists", "exists", "conclusion.statement_formal")
    elif op_id == "p2_negate_formal_outer":
        c["statement_formal"] = "not ( " + c["statement_formal"] + " )"
    elif op_id == "p3_negate_natural_language":
        nl = c["statement_natural_language"]
        c["statement_natural_language"] = "It is not the case that " + nl[0].lower() + nl[1:]
    elif op_id == "p4_conclusion_type_token_flip":
        if base_key == "W":
            c["conclusion_type"] = replace_once(c["conclusion_type"], "weak_cosmic_censorship", "weak_cosmic_censorship_negated", "conclusion_type")
        elif base_key == "C2":
            c["conclusion_type"] = replace_once(c["conclusion_type"], "scc_c2_future_inextendibility", "scc_c2_future_extendibility", "conclusion_type")
        elif base_key == "C0":
            c["conclusion_type"] = replace_once(c["conclusion_type"], "scc_c0_future_inextendibility", "scc_c0_future_extendibility", "conclusion_type")
        else:
            raise ValueError(f"unknown base {base_key}")
    elif op_id == "p5_iplus_completeness_flip":
        c["statement_formal"] = replace_once(c["statement_formal"], "complete(I+_D)", "not complete(I+_D)", "statement_formal")
        c["statement_natural_language"] = replace_once(
            c["statement_natural_language"], "complete future null infinity", "incomplete future null infinity", "statement_natural_language")
    elif op_id == "p6_visibility_flip":
        c["statement_formal"] = replace_once(
            c["statement_formal"], "not exists visible_singularity_from_I_plus(M_D)",
            "exists visible_singularity_from_I_plus(M_D)", "statement_formal")
        c["statement_natural_language"] = replace_once(
            c["statement_natural_language"], "and no singularity visible from future null infinity",
            "and a singularity visible from future null infinity", "statement_natural_language")
    elif op_id == "p7_heldout09_conclusion_negation_rebuilt":
        c["statement_formal"] = "forall (s,delta) in D0 exists G_{s,delta} comeager forall D in G_{s,delta}: exists a proper future C0 metric extension of the maximal development"
        c["statement_natural_language"] = "Generic asymptotically flat vacuum initial data admit a maximal development with a proper future C0 metric extension."
    else:
        raise ValueError(f"unknown op {op_id}")


def main() -> int:
    if not KNOWN_ESCAPE_REF.is_file():
        print(f"missing HELDOUT-09 escape reference {KNOWN_ESCAPE_REF}", file=sys.stderr)
        return 2

    for sub in ("bases", "probes", "controls", "known_leaks", "diag"):
        d = HERE / sub
        d.mkdir(parents=True, exist_ok=True)
        for old in d.iterdir():
            if old.is_file():
                old.unlink()

    frozen = json.loads(FROZEN_MANIFEST.read_text())
    frozen_files = frozen.get("files", {})

    bases = {}
    base_meta = {}
    for key, p in CANON.items():
        raw = p.read_bytes()
        (HERE / "bases" / p.name).write_bytes(raw)
        doc = yaml.safe_load(raw)
        bases[key] = doc
        entry = frozen_files.get(str(p.relative_to(ROOT)), {})
        base_meta[key] = {
            "canonical_path": str(p.relative_to(ROOT)),
            "measured_sha256": sha256_file(p),
            "measured_bytes": p.stat().st_size,
            "schema_revision": doc.get("revision"),
            "schema_revised_at": doc.get("revised_at"),
            "class_id": doc.get("class_id"),
            "frozen_manifest_entry_sha256": entry.get("sha256"),
            "frozen_manifest_entry_matches_measured": entry.get("sha256") == sha256_file(p),
        }

    fixtures = []

    def add(name, base_key, family, op_id, op_kind, expected_rules, leak_claim, expectation, origin):
        doc = copy.deepcopy(bases[base_key])
        if op_id is not None:
            apply_probe(doc, base_key, op_id, op_kind)
        text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)
        sub = "controls" if expectation == "must_be_accepted" else ("known_leaks" if expectation != "should_be_caught" else "probes")
        out = HERE / sub / (name + ".yaml")
        out.write_text(text)
        fixtures.append({
            "fixture": str(out.relative_to(ROOT)),
            "file": out.name,
            "base": base_key,
            "class_id": doc.get("class_id"),
            "family": family,
            "op_id": op_id,
            "op_kind": op_kind,
            "expected_catcher_rules": expected_rules,
            "leak_claim": leak_claim,
            "expectation": expectation,
            "origin": origin,
            "sha256": sha256_file(out),
            "bytes": out.stat().st_size,
        })

    for op_id, family, op_kind, expected, claim in COMMON_OPS + W_ONLY_OPS + C0_ONLY_OPS:
        for base_key in OP_CLASSES[op_kind]:
            add(f"{base_key.lower()}_{op_id}", base_key, family, op_id, op_kind, expected, claim,
                "should_be_caught", "worker-068")

    for base_key in ("W", "C2", "C0"):
        add(f"ctrl_{base_key.lower()}_identity", base_key, "identity-roundtrip", None, "control", ["NONE"],
            "Identity conforming control: canonical schema bytes round-tripped through the same dumper with no mutation. Must be accepted by both stages or every escape reading is a false positive.",
            "must_be_accepted", "worker-068")

    rejected_dir = ROOT / "artifacts" / "formulation" / "evidence" / "heldout_rebased"
    for name, family, rule in KNOWN_REJECTED:
        src = rejected_dir / name
        if not src.is_file():
            print(f"missing known-rejected fixture {src}", file=sys.stderr)
            return 2
        dst = HERE / "known_leaks" / ("rejected_" + name)
        shutil.copyfile(src, dst)
        doc = yaml.safe_load(dst.read_text())
        fixtures.append({
            "fixture": str(dst.relative_to(ROOT)),
            "file": dst.name,
            "base": None,
            "class_id": doc.get("class_id"),
            "family": family,
            "op_id": None,
            "op_kind": "control",
            "expected_catcher_rules": [rule],
            "leak_claim": "KNOWN-REJECTED liveness control copied from FORM-HELDOUT-07 (rebased); measured rejected by stage A in HELDOUT-09. Must still be rejected or the evaluator is dead.",
            "expectation": "known_rejected_positive_control",
            "origin": "copied:artifacts/formulation/evidence/heldout_rebased/" + name,
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
        })

    dst = HERE / "known_leaks" / "escape_reference_c0_03_conclusion_negated.yaml"
    shutil.copyfile(KNOWN_ESCAPE_REF, dst)
    if sha256_file(dst) != KNOWN_ESCAPE_SHA:
        print(f"HELDOUT-09 escape reference hash changed: {sha256_file(dst)}", file=sys.stderr)
        return 2
    fixtures.append({
        "fixture": str(dst.relative_to(ROOT)),
        "file": dst.name,
        "base": "C0",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "family": "heldout09-reference-escape",
        "op_id": "reference",
        "op_kind": "control",
        "expected_catcher_rules": ["NONE"],
        "leak_claim": "The single FORM-HELDOUT-09 union escape (C0 conclusion negated, tokens kept), reused byte-identically as a replication reference. Not a validity control: a catch here would mean the blind spot was fixed.",
        "expectation": "known_escape_reference",
        "origin": "copied:artifacts/worker-068/heldout3/mutants/c0_03_conclusion_negated.yaml",
        "sha256": sha256_file(dst),
        "bytes": dst.stat().st_size,
    })

    probes = [f for f in fixtures if f["expectation"] == "should_be_caught"]
    manifest = {
        "corpus_id": "FORM-POLARITY-10",
        "task_id": "W068-FORM-POLARITY-10",
        "worker": "worker-068",
        "actor": "worker-068",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target_binding": {
            "canonical_bases_measured_at_build": base_meta,
            "frozen_manifest": str(FROZEN_MANIFEST.relative_to(ROOT)),
            "frozen_manifest_sha256_measured": sha256_file(FROZEN_MANIFEST),
            "frozen_revision_measured": frozen.get("revision"),
            "frozen_at_measured": frozen.get("frozen_at"),
            "stages": {
                "structural": GATE_A,
                "structural_sha256": sha256_file(ROOT / GATE_A),
                "semantic": GATE_B,
                "semantic_sha256": sha256_file(ROOT / GATE_B),
                "rule_spec": RULE_SPEC,
                "rule_spec_sha256": sha256_file(ROOT / RULE_SPEC),
            },
            "note": ("bases are byte copies of the live canonical schemas at build time and are shipped in this "
                     "artifact, so the fixture set is a frozen snapshot; the probe targets the pinned stage tools. "
                     "Canonical republish after build does not change the probes and is recorded only as context."),
        },
        "ops": [
            {"op_id": o, "family": f, "applies_to": OP_CLASSES[k], "expected_catcher_rules": e, "leak_claim": c}
            for (o, f, k, e, c) in COMMON_OPS + W_ONLY_OPS + C0_ONLY_OPS
        ],
        "counts": {
            "total": len(fixtures),
            "probes": len(probes),
            "probes_W": sum(1 for f in probes if f["base"] == "W"),
            "probes_C2": sum(1 for f in probes if f["base"] == "C2"),
            "probes_C0": sum(1 for f in probes if f["base"] == "C0"),
            "conforming_controls": sum(1 for f in fixtures if f["expectation"] == "must_be_accepted"),
            "known_rejected_controls": sum(1 for f in fixtures if f["expectation"] == "known_rejected_positive_control"),
            "known_escape_references": sum(1 for f in fixtures if f["expectation"] == "known_escape_reference"),
        },
        "fixtures": fixtures,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"built {len(fixtures)} fixtures at {HERE}")
    print(json.dumps(manifest["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
