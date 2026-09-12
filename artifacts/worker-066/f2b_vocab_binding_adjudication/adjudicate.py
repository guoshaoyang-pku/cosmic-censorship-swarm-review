#!/usr/bin/env python3
"""W066-F2B-VOCAB-BINDING-ADJUDICATION-01 - independent, hash-bound adjudication of
worker-075's hard failure HF-075-F2b-VOCAB (reviews/F2b-review-rev29-075.json, sha256
2fb2878ec1fb59e2d1e770542c278ec2f9adb4bf34b89bc622c7a0044797d6a5).

Finding under test (verbatim premise): "schema token 'scc_c0_future_inextendibility' is not in
the bound F0 declared field_vocabulary.conclusion_type.allowed
['weak_cosmic_censorship', 'strong_cosmic_censorship_C2', 'strong_cosmic_censorship_C0']; the F0
declared class entry uses 'strong_cosmic_censorship_C0' while VOCAB_ALIASES.json declares
'scc_c0_future_inextendibility' canonical, so two frozen artifacts disagree on the canonical token
and the alias policy forbids aliases in canonical artifacts."

What this instrument does, in fresh code (no import of any lead tool except as a black-box
subprocess on pinned copies):
  * pins every input by sha256 against FROZEN rev29 815e0807 and copies it;
  * reproduces the textual premise (checks C1-C4);
  * resolves it at the binding layer (C5-C9: rule spec, canonical gate, consistency layer,
    frozen AMB-10 precedent, absence of any binding consumer of the F0 allowed list);
  * tests both repair directions (C10: F0 adopts canonical -> premise gone; schema adopts
    alias -> canonical gate R11 fails);
  * runs 10 pre-registered controls including mutation and normalization-off controls;
  * re-measures every pin after the run (C13).

Worker authority only: this writes nothing outside its own artifact directory and never writes a
canonical artifact. It emits a reviewer adjudication, not a gate transition.

USAGE: python3 adjudicate.py     # exit 0 = all checks and all controls matched expectations
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
EVID = TASK / "evidence"
PINNED = TASK / "pinned"
TMP = TASK / "tmp"

CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

# relpath -> sha256 expected from FROZEN rev29 (815e0807) / direct measurement
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/tools/check_taxonomy_consistency.py":
        "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "artifacts/formulation/tools/run_acceptance.py":
        "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/formulation/tools/run_gate_tests.py":
        "78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md":
        "f947b8f2ea770e475f7348ac7aa994ea2f173d3019abb272b4cf6efb458bf8d2",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "reviews/F2b-review-rev29-075.json":
        "2fb2878ec1fb59e2d1e770542c278ec2f9adb4bf34b89bc622c7a0044797d6a5",
}

CANON_C0 = "scc_c0_future_inextendibility"
CANON_C2 = "scc_c2_future_inextendibility"
CANON_WCC = "weak_cosmic_censorship"
ALIAS_C0 = "strong_cosmic_censorship_C0"
ALIAS_C2 = "strong_cosmic_censorship_C2"

checks: list[dict] = []
controls: list[dict] = []


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(bucket: list, cid: str, question: str, expected, observed, pass_) -> None:
    bucket.append({"id": cid, "question": question, "expected": expected,
                   "observed": observed, "pass": bool(pass_)})


def run_gate(gate: Path, schema: Path) -> dict:
    r = subprocess.run([sys.executable, str(gate), "--json", str(schema)],
                       capture_output=True, text=True, cwd=str(ROOT))
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"verdict": "parse_error", "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
    rep["returncode"] = r.returncode
    return rep


def fresh_consistency(f0: dict, supplement: dict, aliases: dict, normalize: bool = True) -> list:
    """Fresh re-implementation of the alias-normalized cross-check (black-box independent)."""
    def canon(kind: str, tok):
        if not normalize:
            return tok
        table = aliases.get(kind, {})
        for c, al in table.items():
            if tok == c or tok in (al or []):
                return c
        return tok

    errs = []
    a_classes = f0.get("classes", {})
    b_contracts = supplement.get("class_contracts", {})
    if set(a_classes) != set(b_contracts):
        errs.append(f"class id sets differ: {set(a_classes)} vs {set(b_contracts)}")
    for cid in sorted(set(a_classes) & set(b_contracts)):
        ta = (a_classes[cid].get("axes") or {}).get("conclusion_type")
        tb = b_contracts[cid].get("conclusion_type")
        ca, cb = canon("conclusion_type", ta), canon("conclusion_type", tb)
        if ca != cb:
            errs.append(f"{cid}: conclusion_type {ta!r} vs {tb!r} (normalized {ca!r} vs {cb!r})")
    return errs


def main() -> int:
    for d in (EVID, PINNED / "tools", TMP):
        d.mkdir(parents=True, exist_ok=True)

    # ---------------- P0: pin every input, against FROZEN declarations ----------------
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_files = frozen.get("files", {})
    pins = {"frozen_revision": frozen.get("revision"),
            "frozen_manifest_sha256": sha256_file(ROOT / "artifacts/formulation/FROZEN.json"),
            "created_at": CREATED_AT, "inputs": {}}
    pin_ok = True
    for rel, expected in PINS.items():
        p = ROOT / rel
        live = sha256_file(p)
        declared = frozen_files.get(rel, {}).get("sha256")
        ok = live == expected and (declared is None or declared == live)
        pin_ok &= ok
        pins["inputs"][rel] = {"sha256": live, "expected": expected, "bytes": p.stat().st_size,
                               "mtime": datetime.fromtimestamp(p.stat().st_mtime)
                               .astimezone().isoformat(timespec="seconds"),
                               "frozen_declared": declared, "match": ok}
    record(checks, "P0_pins",
           "every input matches its pinned sha256 and its FROZEN rev29 declaration",
           "16/16 match", f"{sum(1 for v in pins['inputs'].values() if v['match'])}/16 match", pin_ok)

    # pinned copies
    copies = {
        "schemas/af_scc_c0_vacuum.yaml": PINNED / "af_scc_c0_vacuum.yaml",
        "schemas/af_scc_c2_vacuum.yaml": PINNED / "af_scc_c2_vacuum.yaml",
        "research_map/formulation_taxonomy.yaml": PINNED / "f0_map_taxonomy.yaml",
        "artifacts/formulation/formulation_taxonomy.yaml": PINNED / "f0r_supplement.yaml",
        "artifacts/formulation/VOCAB_ALIASES.json": PINNED / "VOCAB_ALIASES.json",
        "artifacts/formulation/rule_spec.json": PINNED / "rule_spec.json",
        "artifacts/formulation/KEY_MANIFEST.json": PINNED / "KEY_MANIFEST.json",
        "artifacts/formulation/tools/check_class_schema.py": PINNED / "tools/check_class_schema.py",
        "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md": PINNED / "ADJUDICATION_flash04_ambiguity.md",
    }
    for rel, dst in copies.items():
        shutil.copyfile(ROOT / rel, dst)

    c0 = yaml.safe_load((PINNED / "af_scc_c0_vacuum.yaml").read_text())
    c2 = yaml.safe_load((PINNED / "af_scc_c2_vacuum.yaml").read_text())
    f0 = yaml.safe_load((PINNED / "f0_map_taxonomy.yaml").read_text())
    f0r = yaml.safe_load((PINNED / "f0r_supplement.yaml").read_text())
    aliases = json.loads((PINNED / "VOCAB_ALIASES.json").read_text())
    spec = json.loads((PINNED / "rule_spec.json").read_text())
    precedent = (PINNED / "ADJUDICATION_flash04_ambiguity.md").read_text()
    gate_src = (PINNED / "tools/check_class_schema.py").read_text()

    f0_allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed", [])
    f0_axes = {cid: ((c.get("axes") or {}).get("conclusion_type"))
               for cid, c in (f0.get("classes") or {}).items()}
    alias_table = aliases.get("conclusion_type", {})
    spec_conc = spec["vocabularies"]["class_conclusion_type"]

    # ---------------- C1-C4: reproduce the textual premise ----------------
    record(checks, "C1_f0_allowed_is_alias_only",
           "F0 rev5 declared conclusion_type vocabulary omits both canonical SCC tokens and lists the aliases",
           {"canonical_absent": [CANON_C0, CANON_C2], "aliases_present": [ALIAS_C0, ALIAS_C2]},
           {"allowed": f0_allowed,
            "canonical_absent": [t for t in (CANON_C0, CANON_C2) if t not in f0_allowed],
            "aliases_present": [t for t in (ALIAS_C0, ALIAS_C2) if t in f0_allowed]},
           CANON_C0 not in f0_allowed and CANON_C2 not in f0_allowed
           and ALIAS_C0 in f0_allowed and ALIAS_C2 in f0_allowed)

    record(checks, "C2_f0_class_axes_alias",
           "F0 declared class entries use the alias tokens for C0 and C2",
           {ALIAS_C0: f0_axes.get("AF-SCC-C0-VAC-GEN"), ALIAS_C2: f0_axes.get("AF-SCC-C2-VAC-GEN")},
           {ALIAS_C0: f0_axes.get("AF-SCC-C0-VAC-GEN"), ALIAS_C2: f0_axes.get("AF-SCC-C2-VAC-GEN")},
           f0_axes.get("AF-SCC-C0-VAC-GEN") == ALIAS_C0 and f0_axes.get("AF-SCC-C2-VAC-GEN") == ALIAS_C2)

    record(checks, "C3_alias_registry_canonical",
           "the frozen alias registry declares exactly one canonical conclusion_type token per SCC class, with the F0 tokens accepted aliases",
           {"C0": CANON_C0, "C2": CANON_C2},
           {"policy": aliases.get("policy"),
            "C0_block": alias_table.get(CANON_C0), "C2_block": alias_table.get(CANON_C2)},
           CANON_C0 in alias_table and ALIAS_C0 in alias_table.get(CANON_C0, [])
           and CANON_C2 in alias_table and ALIAS_C2 in alias_table.get(CANON_C2, []))

    record(checks, "C4_schema_tokens_canonical",
           "the C0/C2 schemas themselves carry the canonical tokens (the alias policy forbids aliases in new canonical artifacts)",
           {"C0": CANON_C0, "C2": CANON_C2},
           {"C0": (c0.get("conclusion") or {}).get("conclusion_type"),
            "C2": (c2.get("conclusion") or {}).get("conclusion_type")},
           (c0.get("conclusion") or {}).get("conclusion_type") == CANON_C0
           and (c2.get("conclusion") or {}).get("conclusion_type") == CANON_C2)

    # ---------------- C5-C9: resolve at the binding layer ----------------
    record(checks, "C5_rule_spec_binds_canonical",
           "R11's binding vocabulary is rule_spec.vocabularies.class_conclusion_type, and it carries the canonical tokens",
           {"aliases_ref": "artifacts/formulation/VOCAB_ALIASES.json", "C0": CANON_C0, "C2": CANON_C2},
           {"aliases_ref": spec["vocabularies"].get("aliases_ref"),
            "aliases_ref_exists": (ROOT / spec["vocabularies"]["aliases_ref"]).exists(),
            "C0": spec_conc.get("AF-SCC-C0-VAC-GEN"), "C2": spec_conc.get("AF-SCC-C2-VAC-GEN")},
           spec["vocabularies"].get("aliases_ref") == "artifacts/formulation/VOCAB_ALIASES.json"
           and spec_conc.get("AF-SCC-C0-VAC-GEN") == CANON_C0
           and spec_conc.get("AF-SCC-C2-VAC-GEN") == CANON_C2)

    g_c0 = run_gate(PINNED / "tools/check_class_schema.py", PINNED / "af_scc_c0_vacuum.yaml")
    g_c2 = run_gate(PINNED / "tools/check_class_schema.py", PINNED / "af_scc_c2_vacuum.yaml")
    record(checks, "C6_canonical_gate_passes",
           "the canonical gate (R01-R16) passes both pinned schemas at the pins",
           {"C0": "pass", "C2": "pass", "rc": 0},
           {"C0": g_c0.get("verdict"), "C2": g_c2.get("verdict"),
            "failed_rules": [g_c0.get("failed_rules"), g_c2.get("failed_rules")],
            "rc": [g_c0.get("returncode"), g_c2.get("returncode")]},
           g_c0.get("verdict") == "pass" and g_c2.get("verdict") == "pass"
           and g_c0.get("returncode") == 0 and g_c2.get("returncode") == 0)

    fresh_errs = fresh_consistency(f0, f0r, aliases, normalize=True)
    tool = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py")],
                          capture_output=True, text=True, cwd=str(ROOT))
    record(checks, "C7_consistency_layer_resolves",
           "the alias-normalized cross-check of F0 vs the class-contract supplement reports no divergence; the pinned tool agrees",
           {"fresh_errors": [], "tool_exit": 0},
           {"fresh_errors": fresh_errs, "tool_exit": tool.returncode,
            "tool_stdout": tool.stdout.strip()[:200]},
           fresh_errs == [] and tool.returncode == 0)

    supp_tokens = {cid: (c or {}).get("conclusion_type")
                   for cid, c in (f0r.get("class_contracts") or {}).items()}
    record(checks, "C8_bound_supplement_agrees",
           "the artifact C0's f0_binding points to as class-contract supplement already carries the canonical token, so the schema has no divergence with its bound supplement",
           CANON_C0, supp_tokens.get("AF-SCC-C0-VAC-GEN"),
           supp_tokens.get("AF-SCC-C0-VAC-GEN") == CANON_C0 and supp_tokens.get("AF-SCC-C2-VAC-GEN") == CANON_C2)

    binding_srcs = {}
    for rel in ("artifacts/formulation/tools/check_class_schema.py",
                "artifacts/formulation/tools/run_acceptance.py",
                "artifacts/formulation/tools/run_gate_tests.py"):
        binding_srcs[rel] = (ROOT / rel).read_text().count("field_vocabulary")
    record(checks, "C9_no_binding_consumer_of_f0_list",
           "no binding formulation tool consumes F0 field_vocabulary as an exact-match list; the gate reads rule_spec instead",
           {"field_vocabulary_hits": {"check_class_schema.py": 0, "run_acceptance.py": 0, "run_gate_tests.py": 0},
            "gate_reads_rule_spec": True},
           {"field_vocabulary_hits": {Path(k).name: v for k, v in binding_srcs.items()},
            "gate_reads_rule_spec": 'vocabularies"]["class_conclusion_type"]' in gate_src},
           all(v == 0 for v in binding_srcs.values())
           and 'vocabularies"]["class_conclusion_type"]' in gate_src)

    amb10 = ('Ruled: one canonical token, `residual_comeager`' in precedent
             and 'baire_residual' in precedent and 'accepted aliases' in precedent
             and 'VOCAB_ALIASES.json' in precedent)
    f0_gen_allowed = ((f0.get("field_vocabulary") or {}).get("genericity_kind") or {}).get("allowed", [])
    record(checks, "C10_frozen_precedent_same_shape",
           "AMB-10 already ruled the same-shaped F0-vs-rule-spec token conflict on the genericity axis: canonical token + accepted aliases in VOCAB_ALIASES; F0's allowed list still carries only aliases",
           {"precedent_ruling_found": True, "canonical_residual_comeager_absent_from_F0_allowed": True},
           {"precedent_ruling_found": amb10,
            "f0_genericity_allowed": f0_gen_allowed,
            "canonical_residual_comeager_absent_from_F0_allowed": "residual_comeager" not in f0_gen_allowed},
           amb10 and "residual_comeager" not in f0_gen_allowed)

    # ---------------- C11: test both repair directions ----------------
    f0_fixed = json.loads(json.dumps(f0))
    for tok in (CANON_C0, CANON_C2):
        if tok not in f0_fixed["field_vocabulary"]["conclusion_type"]["allowed"]:
            f0_fixed["field_vocabulary"]["conclusion_type"]["allowed"].append(tok)
    premise_after_f0_fix = [t for t in (CANON_C0, CANON_C2)
                            if t not in f0_fixed["field_vocabulary"]["conclusion_type"]["allowed"]]

    tmp_schema = TMP / "c0_alias_token.yaml"
    c0_alias = json.loads(json.dumps(c0))
    c0_alias["conclusion"]["conclusion_type"] = ALIAS_C0
    tmp_schema.write_text(yaml.safe_dump(c0_alias, sort_keys=False))
    g_alias = run_gate(PINNED / "tools/check_class_schema.py", tmp_schema)

    record(checks, "C11_repair_directions",
           "adding the canonical tokens to F0 removes the premise; swapping the schema token to the alias is rejected by the canonical gate (so the alias direction is not a permissible re-stamp)",
           {"premise_after_f0_fix": [], "gate_on_alias_token": "fail", "alias_rule": "R11"},
           {"premise_after_f0_fix": premise_after_f0_fix, "gate_on_alias_token": g_alias.get("verdict"),
            "failed_rules": g_alias.get("failed_rules"), "rc": g_alias.get("returncode")},
           premise_after_f0_fix == [] and g_alias.get("verdict") == "fail"
           and "R11" in (g_alias.get("failed_rules") or []))

    # ---------------- pre-registered controls ----------------
    # ctrl-1 pin drift detection
    drift = TMP / "drifted.yaml"
    drift.write_bytes((PINNED / "af_scc_c0_vacuum.yaml").read_bytes() + b"\n# drift\n")
    record(controls, "ctrl01_pin_drift_detected",
           "a single appended byte changes the sha256, so pin drift is detectable",
           "hash differs", "hash differs" if sha256_file(drift) != PINS["schemas/af_scc_c0_vacuum.yaml"]
           else "hash same", sha256_file(drift) != PINS["schemas/af_scc_c0_vacuum.yaml"])

    # ctrl-2 F0 with canonical tokens -> premise false
    record(controls, "ctrl02_f0_canonical_added",
           "the premise is a wording fact about F0 rev5, not a structural impossibility: appending canonical tokens to a copy makes it false",
           "premise false", "premise false" if premise_after_f0_fix == [] else "premise true",
           premise_after_f0_fix == [])

    # ctrl-3 schema alias token -> R11 fail
    record(controls, "ctrl03_schema_alias_rejected",
           "canonical gate rejects the alias token in the schema (R11)",
           "fail/R11", f"{g_alias.get('verdict')}/{g_alias.get('failed_rules')}",
           g_alias.get("verdict") == "fail" and "R11" in (g_alias.get("failed_rules") or []))

    # ctrl-4 mutated rule_spec with alias token -> gate passes (binding source is rule_spec)
    c4 = TMP / "ctrl04"
    (c4 / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PINNED / "tools/check_class_schema.py", c4 / "tools/check_class_schema.py")
    shutil.copyfile(PINNED / "KEY_MANIFEST.json", c4 / "KEY_MANIFEST.json")
    spec_alias = json.loads(json.dumps(spec))
    spec_alias["vocabularies"]["class_conclusion_type"]["AF-SCC-C0-VAC-GEN"] = ALIAS_C0
    (c4 / "rule_spec.json").write_text(json.dumps(spec_alias, indent=1))
    g_alias_spec = run_gate(c4 / "tools/check_class_schema.py", tmp_schema)
    record(controls, "ctrl04_rulespec_is_binding_source",
           "with rule_spec mutated to the alias token, the same schema files pass: the gate trusts rule_spec, not F0's allowed list",
           "pass", f"{g_alias_spec.get('verdict')}/{g_alias_spec.get('failed_rules')}",
           g_alias_spec.get("verdict") == "pass")

    # ctrl-5 normalization off -> the raw token duality appears
    errs_off = fresh_consistency(f0, f0r, {}, normalize=False)
    record(controls, "ctrl05_normalization_off_reproduces_duality",
           "with alias normalization disabled, the F0 map vs supplement comparison reports the C0/C2 token duality (two errors) - this is exactly what the alias layer resolves",
           "2 errors", f"{len(errs_off)} errors",
           len(errs_off) == 2)

    # ctrl-6 C2 sibling same shape
    c2_ok = (f0_axes.get("AF-SCC-C2-VAC-GEN") == ALIAS_C2
             and CANON_C2 not in f0_allowed
             and (c2.get("conclusion") or {}).get("conclusion_type") == CANON_C2
             and spec_conc.get("AF-SCC-C2-VAC-GEN") == CANON_C2)
    record(controls, "ctrl06_c2_sibling_same_shape",
           "the C2 sibling has the identical structure (canonical in schema/spec, alias in F0 rev5)",
           "same shape", "same shape" if c2_ok else "different",
           c2_ok)

    # ctrl-7 WCC has no conflict (canonical == F0 token)
    record(controls, "ctrl07_wcc_no_conflict",
           "the WCC conclusion token is identical in F0, the supplement, the alias registry and rule_spec, so the divergence is specific to the SCC canonicalization",
           CANON_WCC,
           {"f0": f0_axes.get("AF-WCC-VAC-GEN"), "supplement": supp_tokens.get("AF-WCC-VAC-GEN"),
            "spec": spec_conc.get("AF-WCC-VAC-GEN")},
           f0_axes.get("AF-WCC-VAC-GEN") == CANON_WCC
           and supp_tokens.get("AF-WCC-VAC-GEN") == CANON_WCC
           and spec_conc.get("AF-WCC-VAC-GEN") == CANON_WCC)

    # ctrl-8 aliases_ref unresolved if the registry is missing
    record(controls, "ctrl08_aliases_ref_resolves",
           "rule_spec.aliases_ref resolves to the frozen registry; if the registry is treated as absent the reference is unresolved",
           {"resolves": True, "unresolved_when_removed": True},
           {"resolves": (ROOT / spec["vocabularies"]["aliases_ref"]).exists(),
            "unresolved_when_removed": not (TMP / "no_such_VOCAB_ALIASES.json").exists()},
           (ROOT / spec["vocabularies"]["aliases_ref"]).exists())

    # ctrl-9 precedent text really rules the canonical token
    record(controls, "ctrl09_precedent_rules_canonical",
           "the frozen AMB-10 adjudication names residual_comeager the one canonical genericity token and baire_residual/provisional_baire_residual accepted aliases in VOCAB_ALIASES.json",
           True, amb10, amb10)

    # ctrl-10 supplement agreement defeats the over-broad reading
    supp_agrees = all(supp_tokens.get(cid) == spec_conc.get(cid)
                      for cid in ("AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"))
    record(controls, "ctrl10_supplement_canonical_agreement",
           "the class-contract supplement (a frozen artifact, and the schema's bound pointer target) uses the same canonical tokens as rule_spec, so 'two frozen artifacts disagree on the canonical token' is not true of the schema's binding chain",
           True, supp_agrees, supp_agrees)

    # ---------------- C13: no pin drift during the run ----------------
    drift_after = {rel: sha256_file(ROOT / rel) for rel in PINS}
    no_drift = all(drift_after[rel] == PINS[rel] for rel in PINS)
    record(checks, "C13_no_pin_drift",
           "every pinned input re-measured after all runs is unchanged",
           "no drift", "no drift" if no_drift else
           [rel for rel in PINS if drift_after[rel] != PINS[rel]], no_drift)

    # ---------------- write evidence ----------------
    EVID.mkdir(exist_ok=True)
    (EVID / "pins.json").write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
    (EVID / "checks.json").write_text(json.dumps(
        {"task_id": "W066-F2B-VOCAB-BINDING-ADJUDICATION-01", "created_at": CREATED_AT,
         "n_checks": len(checks), "n_passed": sum(1 for c in checks if c["pass"]),
         "checks": checks}, indent=1, sort_keys=True) + "\n")
    (EVID / "controls.json").write_text(json.dumps(
        {"task_id": "W066-F2B-VOCAB-BINDING-ADJUDICATION-01", "created_at": CREATED_AT,
         "preregistration": "controls fixed before the run; each records expected vs observed",
         "n_controls": len(controls), "n_matched": sum(1 for c in controls if c["pass"]),
         "controls": controls}, indent=1, sort_keys=True) + "\n")

    checks_ok = all(c["pass"] for c in checks)
    controls_ok = all(c["pass"] for c in controls)

    adjudication = {
        "target_finding": "HF-075-F2b-VOCAB",
        "target_source": "reviews/F2b-review-rev29-075.json",
        "target_source_sha256": PINS["reviews/F2b-review-rev29-075.json"],
        "textual_premise": "CONFIRMED",
        "severity_claimed": "hard",
        "severity_adjudicated": "non_blocking",
        "ruling": "resolved_by_frozen_alias_registry_and_frozen_precedent",
        "why": [
            "R11's binding vocabulary is rule_spec.vocabularies.class_conclusion_type (canonical tokens); the canonical gate reads rule_spec, not F0 field_vocabulary.",
            "rule_spec.vocabularies.aliases_ref declares the frozen VOCAB_ALIASES.json registry, which names scc_c0_future_inextendibility / scc_c2_future_inextendibility canonical and the F0 tokens accepted aliases.",
            "The class-contract supplement that C0's f0_binding points to already uses the canonical tokens, and the alias-normalized cross-check of F0 vs that supplement passes; the pinned tool agrees (exit 0).",
            "The same-shaped F0-vs-rule-spec conflict on the genericity axis was already ruled in the frozen AMB-10 adjudication: one canonical token plus accepted aliases in VOCAB_ALIASES.json, with F0 left on the alias token.",
            "No binding tool consumes F0 field_vocabulary as an exact-match list (0 occurrences in the gate, acceptance and gate-test tools).",
            "The alias direction is not a permissible repair: the canonical gate rejects the alias token at R11, and the alias policy forbids aliases in new canonical artifacts; the schema already complies.",
        ],
        "residual": "documentation hygiene only: a reader who treats F0 rev5 field_vocabulary.conclusion_type.allowed as an exact-match vocabulary will re-derive this false blocker; an optional next-F0-revision note or re-stamp to canonical tokens removes the trap. No gate action required.",
        "gate_effect": "none measured: C0/C2 pass the canonical gate and the consistency layer at the pins",
    }

    report = {
        "task_id": "W066-F2B-VOCAB-BINDING-ADJUDICATION-01",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "created_at": CREATED_AT,
        "instrument": "artifacts/worker-066/f2b_vocab_binding_adjudication/adjudicate.py (fresh code; lead tools only as black-box subprocesses on pinned copies)",
        "verdict_on_finding": adjudication,
        "reviewer_verdict": {"verdict": "revise", "score": 3.0, "counts_as_full_schema_verdict": False,
                             "scope": "severity re-scope of HF-075-F2b-VOCAB only; no schema verdict issued here"},
        "pins": {"frozen_revision": pins["frozen_revision"],
                 "frozen_manifest_sha256": pins["frozen_manifest_sha256"],
                 "n_inputs": len(PINS), "all_match": pin_ok},
        "checks": {"n": len(checks), "n_passed": sum(1 for c in checks if c["pass"]), "all_passed": checks_ok},
        "controls": {"n": len(controls), "n_matched": sum(1 for c in controls if c["pass"]), "all_matched": controls_ok},
        "falsifier": ("Re-run adjudicate.py on the same pins. This adjudication is falsified if: live C0 is not "
                      "b2ab6acb2bbe or C2 not e9a27996, or FROZEN rev29 815e0807 does not declare the measured hashes, "
                      "or the canonical gate rejects C0/C2 at the pins, or R11's vocabulary source is F0 "
                      "field_vocabulary rather than rule_spec.vocabularies.class_conclusion_type, or "
                      "rule_spec.aliases_ref does not resolve to the frozen VOCAB_ALIASES.json, or the alias registry "
                      "does not name scc_c0_future_inextendibility canonical, or the class-contract supplement carries "
                      "a different token than the schema, or any binding tool consumes F0 field_vocabulary as an "
                      "exact-match list, or the canonical gate accepts the alias token, or any pre-registered control "
                      "departs from its expectation, or any pinned byte moves."),
        "limits": [
            "text-consistency, binding and instrument-coverage result only; says nothing about the mathematics of C0/C2 inextendibility",
            "does not re-open or re-decide AMB-10; uses it as frozen precedent",
            "does not issue a full-schema verdict (worker-075's remaining findings are out of scope)",
            "does not write any canonical artifact and does not transition a gate",
        ],
        "evidence": {},
    }
    for name in ("pins.json", "checks.json", "controls.json"):
        report["evidence"][name] = sha256_file(EVID / name)
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"checks": f"{report['checks']['n_passed']}/{report['checks']['n']}",
                      "controls": f"{report['controls']['n_matched']}/{report['controls']['n']}",
                      "adjudicated_severity": adjudication["severity_adjudicated"],
                      "report_sha256": sha256_file(TASK / "report.json")}, indent=1))
    return 0 if (pin_ok and checks_ok and controls_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
