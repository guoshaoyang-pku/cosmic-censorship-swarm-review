#!/usr/bin/env python3
"""W068-FORM-POLARITY-11 corpus builder (worker-068, bounded task).

Predecessor finding (W068-FORM-POLARITY-10, report sha256 66301211174d): the
conclusion-polarity/content blind spot is measured and class-general for the two
SCC arms, but the WCC arm was NON-INFORMATIVE because stage B
(spec_conformance_audit.py c79d8ab8440a) rejects the LIVE canonical WCC base at
rev12 cce9c60146d6 with R03 (binder '(q,t0)' absent from formal sentence), and the
archived pre-rev12 base 9a8bd4c96800 is rejected by stage A under the CURRENT
KEY_MANIFEST 014e2d301978 (R22: 'revised_at_unused' no longer allowed).

This builder removes BOTH obstructions by constructing a *pinned shadow pipeline*:
the two stage tools and the rule spec at their pinned bytes, plus KEY_MANIFEST at
the earlier pinned revision fce91948ba3a (worker-061 hist, rev27), applied to the
archived pre-rev12 base 9a8bd4c96800. All five inputs are hash-asserted before any
fixture is written. The shadow is a byte copy; the live tree is never modified.

It then builds the six WCC polarity/content probes p1..p6 with exactly the operation
semantics of FORM-POLARITY-10 (op source 7f1213ad18dd), plus identity / format /
known-rejected controls.

Usage: python3 build_corpus11.py
Exit 0 on success; 2 on precondition failure (pinned input drift / op not applicable).
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

CORPUS_ID = "FORM-POLARITY-11"
TASK_ID = "W068-FORM-POLARITY-11"
WORKER = "worker-068"

# ---------------------------------------------------------------------------
# Pinned shadow inputs. Every hash was measured on the live tree before the
# shadow was built; the shadow is what isolates the measurement from live drift.
# ---------------------------------------------------------------------------
SHADOW = HERE / "shadow"
PINNED = {
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/KEY_MANIFEST.json":
        "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
    "artifacts/worker-068/polarity11/shadow/artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-068/polarity11/shadow/schemas/af_wcc_vacuum.yaml":
        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
}
BASE_REL = "artifacts/worker-068/polarity11/shadow/schemas/af_wcc_vacuum.yaml"

# provenance of the shadow inputs (where the pinned bytes came from)
PROVENANCE = {
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/tools/check_class_schema.py":
        "copied from live artifacts/formulation/tools/check_class_schema.py",
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/rule_spec.json":
        "copied from live artifacts/formulation/rule_spec.json",
    "artifacts/worker-068/polarity11/shadow/artifacts/formulation/KEY_MANIFEST.json":
        "copied from artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json (rev27, fce91948ba3a); the live KEY_MANIFEST is 014e2d301978 and rejects this base at R22",
    "artifacts/worker-068/polarity11/shadow/artifacts/worker-06/spec_conformance_audit.py":
        "copied from live artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/worker-068/polarity11/shadow/schemas/af_wcc_vacuum.yaml":
        "copied from artifacts/worker-054/f1_repair_verify/snapshot/af_wcc_vacuum.pinned.9a8bd4c96800.yaml; self-declared revision 11, superseded by live rev12 cce9c60146d6",
}

LIVE_CONTEXT = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
}
OP_SOURCE = "artifacts/worker-068/polarity10/build_corpus.py"
OP_SOURCE_SHA = "7f1213ad18dd545f05ca30a01a2f76cdf1068ccc9f575cbaf8ed025b92c16f68"
KNOWN_REJECTED_SRC = "artifacts/formulation/evidence/heldout_rebased"

W_ONLY_OPS = [
    ("p1_flip_negated_existence", "conclusion-polarity-inner-negation", "W", ["R27"],
     "The inner negated-existence of the formal conclusion is flipped to a positive existence: the schema now asserts the existence of the forbidden object while every class token is kept."),
    ("p2_negate_formal_outer", "conclusion-polarity-outer-negation", "W", ["NONE"],
     "The whole formal conclusion is wrapped in an explicit outer negation: the schema asserts not(P) where P is the frozen conclusion, while every class token is kept."),
    ("p3_negate_natural_language", "conclusion-polarity-nl-negation", "W", ["NONE"],
     "The natural-language conclusion is negated ('It is not the case that ...'); the formal statement is untouched, so the two conclusion fields now contradict each other."),
    ("p4_conclusion_type_token_flip", "conclusion-polarity-token-flip", "W", ["R11"],
     "The conclusion_type token is inverted (weak_cosmic_censorship -> weak_cosmic_censorship_negated) while class_id and family stay valid: a vocabulary-level polarity inversion."),
    ("p5_iplus_completeness_flip", "conclusion-polarity-iplus-completeness", "W", ["NONE"],
     "The WCC conjunct 'complete(I+_D)' is negated in both the formal and natural-language conclusion: the schema now asserts an incomplete future null infinity, the opposite of the WCC content."),
    ("p6_visibility_flip", "conclusion-polarity-visibility", "W", ["NONE"],
     "The WCC visibility conjunct is inverted ('no singularity visible from I+' -> 'a singularity visible from I+'): the schema asserts the existence of the visible singularity that WCC forbids."),
]

KNOWN_REJECTED = [
    ("h06_genericity_kind_swap.yaml", "genericity-kind-swap", "R21"),
    ("h19_h2loc_substitution.yaml", "h2loc-substitution", "R18/R31"),
    ("h26_quantifier_order.yaml", "quantifier-order", "R27"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_once(text: str, old: str, new: str, where: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"op not applicable ({where}): expected exactly one {old!r}, found {text.count(old)}")
    return text.replace(old, new, 1)


def apply_probe(doc, op_id: str) -> None:
    """Identical semantics to FORM-POLARITY-10 build_corpus.py (op source 7f1213ad18dd)."""
    c = doc["conclusion"]
    if op_id == "p1_flip_negated_existence":
        c["statement_formal"] = replace_once(c["statement_formal"], "not exists", "exists", "conclusion.statement_formal")
    elif op_id == "p2_negate_formal_outer":
        c["statement_formal"] = "not ( " + c["statement_formal"] + " )"
    elif op_id == "p3_negate_natural_language":
        nl = c["statement_natural_language"]
        c["statement_natural_language"] = "It is not the case that " + nl[0].lower() + nl[1:]
    elif op_id == "p4_conclusion_type_token_flip":
        c["conclusion_type"] = replace_once(c["conclusion_type"], "weak_cosmic_censorship",
                                            "weak_cosmic_censorship_negated", "conclusion_type")
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
    else:
        raise ValueError(f"unknown op {op_id}")


def main() -> int:
    # --- precondition 1: pinned shadow inputs unchanged ---------------------
    problems = []
    for rel, expected in PINNED.items():
        p = ROOT / rel
        if not p.is_file():
            problems.append(f"missing pinned shadow input {rel}")
            continue
        live = sha256_file(p)
        if live != expected:
            problems.append(f"pinned shadow input drift {rel}: {expected[:12]} -> {live[:12]}")
    for rel, expected in LIVE_CONTEXT.items():
        p = ROOT / rel
        if not p.is_file():
            problems.append(f"missing live context file {rel}")
            continue
        live = sha256_file(p)
        if live != expected:
            problems.append(f"UNEXPECTED live drift {rel}: expected context {expected[:12]}, measured {live[:12]}")
    if problems:
        for x in problems:
            print("PRECONDITION FAIL: " + x, file=sys.stderr)
        return 2

    for sub in ("fixtures", "controls", "known_leaks"):
        d = HERE / sub
        d.mkdir(parents=True, exist_ok=True)
        for old in d.iterdir():
            if old.is_file():
                old.unlink()

    raw_base = (ROOT / BASE_REL).read_bytes()
    base_doc = yaml.safe_load(raw_base)
    if base_doc.get("class_id") != "AF-WCC-VAC-GEN":
        print("PRECONDITION FAIL: base is not AF-WCC-VAC-GEN", file=sys.stderr)
        return 2

    fixtures = []

    def add(name, sub, family, op_id, expected_rules, leak_claim, expectation, origin, text):
        out = HERE / sub / (name + ".yaml")
        out.write_text(text)
        fixtures.append({
            "fixture": str(out.relative_to(ROOT)),
            "file": out.name,
            "base": "W",
            "class_id": base_doc.get("class_id"),
            "family": family,
            "op_id": op_id,
            "expected_catcher_rules": expected_rules,
            "leak_claim": leak_claim,
            "expectation": expectation,
            "origin": origin,
            "sha256": sha256_file(out),
            "bytes": out.stat().st_size,
            "differs_from_base": sha256_file(out) != PINNED[BASE_REL],
        })

    # --- 6 polarity/content probes -----------------------------------------
    for op_id, family, _kind, expected, claim in W_ONLY_OPS:
        doc = copy.deepcopy(base_doc)
        apply_probe(doc, op_id)
        add("w_" + op_id, "fixtures", family, op_id, expected, claim,
            "should_be_caught", f"{OP_SOURCE}#{OP_SOURCE_SHA[:12]} (op copied verbatim)",
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))

    # --- identity + format controls (must pass both stages) ----------------
    identity_text = yaml.safe_dump(copy.deepcopy(base_doc), sort_keys=False, allow_unicode=True, width=1000)
    add("ctrl_w_identity_roundtrip", "controls", "identity-roundtrip", None, ["NONE"],
        "Identity conforming control: archived base bytes round-tripped through the same dumper with no mutation. Must be accepted by both stages or the WCC arm is non-informative.",
        "must_be_accepted", "worker-068", identity_text)
    add("ctrl_w_comment_prepend", "controls", "format-comment-prepend", None, ["NONE"],
        "Conforming format control: a single comment line prepended; no content change. Must be accepted by both stages.",
        "must_be_accepted", "worker-068",
        "# FORM-POLARITY-11 conforming control: comment prepended, no other change.\n" + identity_text)
    add("ctrl_w_comment_append_blank_eof", "controls", "format-comment-append", None, ["NONE"],
        "Conforming format control: comment plus blank lines appended at EOF; no content change. Must be accepted by both stages.",
        "must_be_accepted", "worker-068",
        identity_text.rstrip("\n") + "\n# FORM-POLARITY-11 conforming control: comment + blank lines appended at EOF.\n\n\n")
    resorted = yaml.safe_dump(copy.deepcopy(base_doc), sort_keys=True, allow_unicode=True, width=1000)
    add("ctrl_w_pyyaml_resorted", "controls", "format-resorted", None, ["NONE"],
        "Conforming format control: same document re-dumped with sort_keys=True. Must be accepted by both stages; a reject here means key order is load-bearing.",
        "must_be_accepted", "worker-068", resorted)

    # renamed byte-identical copy
    dst = HERE / "controls" / "ctrl_w_renamed_identical_copy.yaml"
    dst.write_bytes(raw_base)
    fixtures.append({
        "fixture": str(dst.relative_to(ROOT)),
        "file": dst.name, "base": "W", "class_id": base_doc.get("class_id"),
        "family": "format-renamed-identical-copy", "op_id": None, "expected_catcher_rules": ["NONE"],
        "leak_claim": "Conforming format control: byte-identical copy of the archived base under a different file name. Must be accepted by both stages.",
        "expectation": "must_be_accepted", "origin": "byte copy of " + BASE_REL,
        "sha256": sha256_file(dst), "bytes": dst.stat().st_size,
        "differs_from_base": False,
    })

    # --- known-rejected liveness controls ----------------------------------
    for name, family, rule in KNOWN_REJECTED:
        src = ROOT / KNOWN_REJECTED_SRC / name
        if not src.is_file():
            print(f"PRECONDITION FAIL: missing known-rejected fixture {src}", file=sys.stderr)
            return 2
        dst = HERE / "known_leaks" / ("rejected_" + name)
        shutil.copyfile(src, dst)
        fixtures.append({
            "fixture": str(dst.relative_to(ROOT)),
            "file": dst.name, "base": None, "class_id": yaml.safe_load(dst.read_text()).get("class_id"),
            "family": family, "op_id": None, "expected_catcher_rules": [rule],
            "leak_claim": "KNOWN-REJECTED liveness control from FORM-HELDOUT-07 (rebased); rejected by stage A in HELDOUT-09. Must still be rejected or the evaluator is dead.",
            "expectation": "known_rejected_positive_control",
            "origin": f"copied:{KNOWN_REJECTED_SRC}/{name}",
            "sha256": sha256_file(dst), "bytes": dst.stat().st_size,
            "differs_from_base": None,
        })

    probes = [f for f in fixtures if f["expectation"] == "should_be_caught"]
    manifest = {
        "corpus_id": CORPUS_ID,
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "question": ("Does the conclusion-polarity/content blind spot measured for the SCC arms in "
                     "FORM-POLARITY-10 also hold for AF-WCC-VAC-GEN, once the two known obstructions "
                     "(stage B R03 on live rev12; stage A R22 under the current KEY_MANIFEST) are "
                     "removed by a fully pinned shadow pipeline?"),
        "shadow_pins": {
            rel: {"sha256": PINNED[rel], "provenance": PROVENANCE[rel]} for rel in PINNED
        },
        "live_context_measured_at_build": LIVE_CONTEXT,
        "op_source": {"path": OP_SOURCE, "sha256": OP_SOURCE_SHA,
                      "note": "w_* probes apply the p1..p6 operations of FORM-POLARITY-10 verbatim, restricted to the W arm."},
        "counts": {
            "total": len(fixtures),
            "probes": len(probes),
            "conforming_controls": sum(1 for f in fixtures if f["expectation"] == "must_be_accepted"),
            "known_rejected_controls": sum(1 for f in fixtures if f["expectation"] == "known_rejected_positive_control"),
        },
        "falsifier": ("Any drift in a pinned shadow input between build and run; a fixture whose disk sha256 differs "
                      "from this manifest; the identity control rejected by either stage (WCC arm non-informative); "
                      "a probe verdict that differs from raw_verdicts.json on re-run; or a claim that this measurement "
                      "speaks about the live rev12 schema rather than the pinned archived base."),
        "non_claims": [
            "Not a gate verdict and not a node transition; A1/G-CLASSBIND/G-FORM remain owned by the controller/leads.",
            "No claim about the truth of the WCC class or of cosmic censorship.",
            "The result is about the pinned detector pipeline on an archived pre-rev12 base; it is not a statement that live rev12 has an unmeasured polarity leak (live rev12 is rejected by stage B R03 before any probe).",
        ],
        "fixtures": fixtures,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"built {len(fixtures)} fixtures at {HERE}")
    print(json.dumps(manifest["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
