#!/usr/bin/env python3
"""W068-FORM-POLARITY-12 corpus builder (worker-068, bounded task).

Builds a fresh, self-contained, fully pinned three-class probe corpus against the
archived revision-11 class bases, for a measurement of whether the two-stage
class-binding pipeline compares *conclusion statement content* against the frozen
class conclusion at all:

  * identity controls           (3)  must be accepted by both stages (arm calibration)
  * polarity probes p1..p4      (12) carried-over negation/token ops from FORM-POLARITY-10
  * W-only p5/p6, C0-only p7    (3)  carried-over WCC completeness/visibility and C0 rebuild
  * content-substitution s1..s4 (12) NEW: non-negation statement-content substitutions,
                                     one op family per semantic axis, in-vocabulary tokens
  * known-rejected liveness     (3)  FORM-HELDOUT-07 C0 leaks copied byte-identically

Every probe mutates `conclusion.*` content only (p4 also `conclusion_type`). The
builder writes fixtures/, manifest.json (fixture + shadow + union-corpus pins hashed
BEFORE any stage run), corpus_index.json and checkpoint-0 state. It never sets a map
gate verdict or node status.

Usage: python3 build_corpus12.py
Exit: 0 built; 2 precondition/IO failure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SHADOW = HERE / "shadow"
BUILDER_REL = "artifacts/worker-068/polarity12/build_corpus12.py"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        raise ValueError(f"{where}: expected exactly one {old!r}, found {n}")
    return text.replace(old, new)


# --------------------------------------------------------------------------
# Probe ops. All content edits are confined to conclusion.statement_formal and
# conclusion.statement_natural_language (p4: conclusion_type token only).
# --------------------------------------------------------------------------
COMMON_POLARITY_OPS = [
    ("p1_flip_negated_existence", "conclusion-polarity-inner-negation", ["R27"],
     "Flip the inner negated existence to positive existence; class tokens kept."),
    ("p2_negate_formal_outer", "conclusion-polarity-outer-negation", ["NONE"],
     "Wrap the whole formal conclusion in an explicit outer negation."),
    ("p3_negate_natural_language", "conclusion-polarity-nl-negation", ["NONE"],
     "Negate the natural-language conclusion; formal statement untouched."),
    ("p4_conclusion_type_token_flip", "conclusion-polarity-token-flip", ["R11"],
     "Invert the conclusion_type token; statements and class_id untouched."),
]
W_ONLY_POLARITY_OPS = [
    ("p5_iplus_completeness_flip", "conclusion-polarity-iplus-completeness", ["NONE"],
     "Negate the WCC conjunct complete(I+_D) in formal and natural language."),
    ("p6_visibility_flip", "conclusion-polarity-visibility", ["NONE"],
     "Invert the WCC visibility conjunct (no visible singularity -> visible singularity)."),
]
C0_ONLY_POLARITY_OPS = [
    ("p7_heldout09_conclusion_negation_rebuilt", "conclusion-polarity-heldout09-rebuild", ["NONE"],
     "Reproduce the HELDOUT-09 c0_03 conclusion inversion on the pinned rev11 C0 base."),
]
# NEW non-negation content-substitution ops: each keeps every class token and every
# negation marker count; only the conclusion's semantic content changes.
SUBSTITUTION_OPS = [
    ("s1_argument_substitution", "conclusion-content-argument-substitution", ["NONE"],
     "Change the object the conclusion is about (W: I+_D -> I-_D; SCC: MGHD(D) -> D)."),
    ("s2_quantifier_strength_substitution", "conclusion-content-quantifier-substitution", ["NONE"],
     "Change the generic quantifier strength (comeager -> meager; Generic -> Every)."),
    ("s3_domain_substitution", "conclusion-content-domain-substitution", ["NONE"],
     "Change the quantifier domain index in the formal conclusion (D0 -> D1)."),
    ("s4_object_substitution", "conclusion-content-object-substitution", ["NONE"],
     "Change the object/regularity claim in the natural-language conclusion."),
]
OP_APPLIES = {"common": ["W", "C2", "C0"], "W": ["W"], "C0": ["C0"], "sub": ["W", "C2", "C0"]}


def apply_polarity(doc: dict, base_key: str, op_id: str) -> None:
    c = doc["conclusion"]
    if op_id == "p1_flip_negated_existence":
        c["statement_formal"] = replace_once(c["statement_formal"], "not exists", "exists", "formal")
    elif op_id == "p2_negate_formal_outer":
        c["statement_formal"] = "not ( " + c["statement_formal"] + " )"
    elif op_id == "p3_negate_natural_language":
        nl = c["statement_natural_language"]
        c["statement_natural_language"] = "It is not the case that " + nl[0].lower() + nl[1:]
    elif op_id == "p4_conclusion_type_token_flip":
        tok = {"W": ("weak_cosmic_censorship", "weak_cosmic_censorship_negated"),
               "C2": ("scc_c2_future_inextendibility", "scc_c2_future_extendibility"),
               "C0": ("scc_c0_future_inextendibility", "scc_c0_future_extendibility")}[base_key]
        c["conclusion_type"] = replace_once(c["conclusion_type"], tok[0], tok[1], "conclusion_type")
    elif op_id == "p5_iplus_completeness_flip":
        c["statement_formal"] = replace_once(c["statement_formal"], "complete(I+_D)", "not complete(I+_D)", "formal")
        c["statement_natural_language"] = replace_once(
            c["statement_natural_language"], "complete future null infinity", "incomplete future null infinity", "nl")
    elif op_id == "p6_visibility_flip":
        c["statement_formal"] = replace_once(
            c["statement_formal"], "not exists visible_singularity_from_I_plus(M_D)",
            "exists visible_singularity_from_I_plus(M_D)", "formal")
        c["statement_natural_language"] = replace_once(
            c["statement_natural_language"], "and no singularity visible from future null infinity",
            "and a singularity visible from future null infinity", "nl")
    elif op_id == "p7_heldout09_conclusion_negation_rebuilt":
        c["statement_formal"] = ("forall (s,delta) in D0 exists G_{s,delta} comeager forall D in G_{s,delta}: "
                                 "exists a proper future C0 metric extension of the maximal development")
        c["statement_natural_language"] = ("Generic asymptotically flat vacuum initial data admit a maximal "
                                           "development with a proper future C0 metric extension.")
    else:
        raise ValueError(f"unknown polarity op {op_id}")


def apply_substitution(doc: dict, base_key: str, op_id: str) -> None:
    c = doc["conclusion"]
    if op_id == "s1_argument_substitution":
        if base_key == "W":
            c["statement_formal"] = replace_once(c["statement_formal"], "complete(I+_D)", "complete(I-_D)", "formal")
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "complete future null infinity", "complete past null infinity", "nl")
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "visible from future null infinity",
                "visible from past null infinity", "nl")
        else:
            c["statement_formal"] = replace_once(
                c["statement_formal"], "proper_future_extension_in_class(MGHD(D))",
                "proper_future_extension_in_class(D)", "formal")
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "maximal development that is future-inextendible",
                "initial data set that is future-inextendible", "nl")
    elif op_id == "s2_quantifier_strength_substitution":
        c["statement_formal"] = replace_once(c["statement_formal"], "comeager", "meager", "formal")
        c["statement_natural_language"] = replace_once(c["statement_natural_language"], "Generic ", "Every ", "nl")
    elif op_id == "s3_domain_substitution":
        c["statement_formal"] = replace_once(c["statement_formal"], "in D0", "in D1", "formal")
    elif op_id == "s4_object_substitution":
        if base_key == "W":
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "have a maximal development", "have a development", "nl")
        elif base_key == "C2":
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "as a C2 vacuum solution", "as a smooth vacuum solution", "nl")
        else:
            c["statement_natural_language"] = replace_once(
                c["statement_natural_language"], "as a continuous Lorentzian manifold",
                "as a topological manifold", "nl")
    else:
        raise ValueError(f"unknown substitution op {op_id}")


BASE_FILES = {
    "W": "shadow/schemas/af_wcc_vacuum.yaml",
    "C2": "shadow/schemas/af_scc_c2_vacuum.yaml",
    "C0": "shadow/schemas/af_scc_c0_vacuum.yaml",
}


def main() -> int:
    for sub in ("fixtures",):
        d = HERE / sub
        d.mkdir(parents=True, exist_ok=True)
        for old in d.iterdir():
            if old.is_file():
                old.unlink()

    bases = {k: yaml.safe_load((HERE / p).read_text()) for k, p in BASE_FILES.items()}
    fixtures = []

    def add(name, base_key, family, op_id, op_kind, expected_rules, leak_claim, expectation):
        doc = copy.deepcopy(bases[base_key])
        if op_id is not None:
            if op_kind == "sub":
                apply_substitution(doc, base_key, op_id)
            else:
                apply_polarity(doc, base_key, op_id)
        out = HERE / "fixtures" / (name + ".yaml")
        out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))
        fixtures.append({
            "fixture": str(out.relative_to(ROOT)),
            "file": out.name,
            "base": base_key,
            "base_path": str((HERE / BASE_FILES[base_key]).relative_to(ROOT)),
            "class_id": doc.get("class_id"),
            "family": family,
            "op_id": op_id,
            "op_kind": op_kind,
            "expected_catcher_rules": expected_rules,
            "leak_claim": leak_claim,
            "expectation": expectation,
            "origin": "worker-068",
            "sha256": sha256_file(out),
            "bytes": out.stat().st_size,
        })

    for op_id, family, expected, claim in COMMON_POLARITY_OPS:
        for base_key in OP_APPLIES["common"]:
            add(f"{base_key.lower()}_{op_id}", base_key, family, op_id, "common", expected, claim, "should_be_caught")
    for op_id, family, expected, claim in W_ONLY_POLARITY_OPS:
        add(f"w_{op_id}", "W", family, op_id, "W", expected, claim, "should_be_caught")
    for op_id, family, expected, claim in C0_ONLY_POLARITY_OPS:
        add(f"c0_{op_id}", "C0", family, op_id, "C0", expected, claim, "should_be_caught")
    for op_id, family, expected, claim in SUBSTITUTION_OPS:
        for base_key in OP_APPLIES["sub"]:
            add(f"{base_key.lower()}_{op_id}", base_key, family, op_id, "sub", expected, claim, "should_be_caught")
    for base_key in ("W", "C2", "C0"):
        add(f"ctrl_{base_key.lower()}_identity", base_key, "identity-roundtrip", None, "control",
            ["NONE"], "Unmutated base; must be accepted by both stages (arm calibration).", "must_be_accepted")

    # known-rejected liveness controls: byte-identical copies of FORM-HELDOUT-07 C0 leaks
    for src in sorted((HERE / "known_leaks").glob("rejected_h*.yaml")):
        fixtures.append({
            "fixture": str(src.relative_to(ROOT)),
            "file": src.name,
            "base": "C0",
            "base_path": str((HERE / BASE_FILES["C0"]).relative_to(ROOT)),
            "class_id": "AF-SCC-C0-VAC-GEN",
            "family": "known-rejected-liveness",
            "op_id": None,
            "op_kind": "liveness",
            "expected_catcher_rules": ["see FORM-HELDOUT-07 (copied)"],
            "leak_claim": "Copied byte-identically from FORM-HELDOUT-07 via FORM-HELDOUT-09; must be rejected or the evaluator is dead.",
            "expectation": "known_rejected_positive_control",
            "origin": "copied:artifacts/worker-068/heldout3/known_leaks/" + src.name,
            "sha256": sha256_file(src),
            "bytes": src.stat().st_size,
        })

    shadow_inputs = sorted(str(p.relative_to(ROOT)) for p in SHADOW.rglob("*") if p.is_file())
    shadow_pins = {rel: {"sha256": sha256_file(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}
                   for rel in shadow_inputs}

    # union-corpus inputs re-used read-only for the candidate-rule evaluation
    union_manifests = {
        "heldout3": "artifacts/worker-068/heldout3/manifest.json",
        "polarity10": "artifacts/worker-068/polarity10/manifest.json",
        "polarity11": "artifacts/worker-068/polarity11/manifest.json",
    }
    union_pins = {}
    for corp, rel in union_manifests.items():
        union_pins[rel] = sha256_file(ROOT / rel)
        m = json.loads((ROOT / rel).read_text())
        for f in m["fixtures"]:
            p = ROOT / f["fixture"]
            union_pins[f["fixture"]] = sha256_file(p)
        raw = json.loads((ROOT / f"artifacts/worker-068/{corp}/raw_verdicts.json").read_text())
        union_pins[f"artifacts/worker-068/{corp}/raw_verdicts.json"] = hashlib.sha256(
            (ROOT / f"artifacts/worker-068/{corp}/raw_verdicts.json").read_bytes()).hexdigest()

    counts = {}
    for f in fixtures:
        counts[f["expectation"]] = counts.get(f["expectation"], 0) + 1

    manifest = {
        "corpus_id": "FORM-POLARITY-12",
        "task_id": "W068-FORM-POLARITY-12",
        "worker": "worker-068",
        "actor": "worker-068",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "question": ("Does the two-stage class-binding pipeline at a fully pinned three-class shadow "
                     "(rev11 bases; stage A 000e09e46b2f; stage B c79d8ab8440a; rule spec 40f9bb9e657b; "
                     "KEY_MANIFEST rev27 fce91948ba3a) accept conclusion-statement content substitutions that "
                     "contain no negation marker, and can a conclusion-freeze candidate rule catch the whole "
                     "conclusion-content escape family without flagging any conforming control?"),
        "shadow_pins": shadow_pins,
        "bases": {k: {"path": str((HERE / v).relative_to(ROOT)), "sha256": sha256_file(HERE / v),
                      "revision": bases[k].get("revision"), "class_id": bases[k].get("class_id")}
                  for k, v in BASE_FILES.items()},
        "builder": {"path": BUILDER_REL, "sha256": sha256_file(ROOT / BUILDER_REL)},
        "union_corpus_pins": union_pins,
        "counts": {"total": len(fixtures), **counts,
                   "polarity_probes": sum(1 for f in fixtures if f["op_kind"] in ("common", "W", "C0")),
                   "substitution_probes": sum(1 for f in fixtures if f["op_kind"] == "sub")},
        "falsifier": ("Any identity control rejected by either stage (arm non-informative); any pinned shadow or "
                      "fixture byte drift between build and run; a substituted probe rejected by both stages is a "
                      "catch (reported as such, not an escape); a candidate-rule flag on a conforming control."),
        "fixtures": fixtures,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (HERE / "corpus_index.json").write_text(json.dumps(
        {"corpus_id": manifest["corpus_id"], "counts": manifest["counts"],
         "fixtures": [{k: f[k] for k in ("file", "base", "class_id", "family", "op_id", "expectation", "sha256")}
                      for f in fixtures]}, indent=2, sort_keys=True))
    print(json.dumps({"manifest": str((HERE / "manifest.json").relative_to(ROOT)),
                      "manifest_sha256": sha256_file(HERE / "manifest.json"),
                      "counts": manifest["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
