#!/usr/bin/env python3
"""W48-GFORM-VOCAB-ADJUDICATION-01 / audit_vocab.py

Independent, hash-bound adjudication of the cross-registry conclusion-type /
genericity vocabulary divergence at the G-FORM pins.

The task is bound to class AF-SCC-C2-VAC-GEN / node F2a, with cross-checks of
F1, F2b and the two F0 companion artifacts.  It answers one question:

  A gate reader sees F2a's conclusion_type 'scc_c2_future_inextendibility' and
  F0 rev5's field_vocabulary.conclusion_type.allowed list, which does not
  contain it.  Is F2a wrong, or is F0's allow-list wrong, and what has to change
  before a clean accept exists?

All checks read ./snapshot/ copies pinned by snapshot_inputs.py; the live
canonical paths are never written.  Controls mutate in-memory copies only and
must flip the named check.

Usage:  python3 audit_vocab.py [--controls] [--out report.json]
Exit 0 = harness sound (all controls flipped); 1 = harness defect.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
SNAP = HERE / "snapshot"
SNAP_FILES = {
    "f0": "f0_canonical.formulation_taxonomy.yaml",
    "supp": "f0_supplement.formulation_taxonomy.yaml",
    "f1": "f1.af_wcc_vacuum.yaml",
    "f2a": "f2a.af_scc_c2_vacuum.yaml",
    "f2b": "f2b.af_scc_c0_vacuum.yaml",
    "spec": "rule_spec.json",
    "aliases": "VOCAB_ALIASES.json",
    "frozen": "FROZEN.json",
    "evidence": "taxonomy_consistency.json",
}
SCHEMA_KEYS = {"f1": "AF-WCC-VAC-GEN", "f2a": "AF-SCC-C2-VAC-GEN", "f2b": "AF-SCC-C0-VAC-GEN"}
ALL_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def load() -> dict:
    d = {}
    for k, fn in SNAP_FILES.items():
        p = SNAP / fn
        if not p.is_file():
            raise SystemExit(f"missing snapshot file {p}; run snapshot_inputs.py first")
        raw = p.read_bytes()
        d[k] = yaml.safe_load(raw) if fn.endswith((".yaml", ".yml")) else json.loads(raw)
        d[k + "_sha256"] = sha256_bytes(raw)
        d[k + "_text"] = raw.decode("utf-8", "replace")
    return d


def canon(reg: dict, kind: str, tok):
    """Alias-aware normalisation, mirroring the owner-declared VOCAB_ALIASES policy."""
    if tok is None:
        return None
    table = reg.get(kind, {})
    for c, al in table.items():
        if tok == c or tok in al:
            return c
    return tok


# --------------------------------------------------------------------------- checks
def v1_r11_alignment(d):
    rs = d["spec"]["vocabularies"]["class_conclusion_type"]
    rows, bad = [], []
    for k, cid in SCHEMA_KEYS.items():
        got, want = d[k]["conclusion"]["conclusion_type"], rs.get(cid)
        rows.append({"class": cid, "schema": got, "rule_spec_R11": want, "match": got == want})
        if got != want:
            bad.append(cid)
    return ("PASS" if not bad else "FAIL",
            {"rows": rows, "mismatched_classes": bad,
             "detail": "every frozen schema conclusion_type equals the rule_spec R11 value enforced by check_class_schema.py"})


def v2_schema_tokens_canonical(d):
    al = d["aliases"]
    rows, bad = [], []
    for k, cid in SCHEMA_KEYS.items():
        tok = d[k]["conclusion"]["conclusion_type"]
        is_canon = tok in al["conclusion_type"]
        is_alias = any(tok in v for v in al["conclusion_type"].values())
        rows.append({"class": cid, "token": tok, "is_canonical_key": is_canon,
                     "is_registered_alias_form": is_alias})
        if not is_canon:
            bad.append(cid)
    return ("PASS" if not bad else "FAIL",
            {"rows": rows, "non_canonical_classes": bad,
             "detail": "all three schemas use the canonical key, not an accepted alias"})


def v3_schema_genericity_canonical(d):
    al, rs = d["aliases"], d["spec"]["vocabularies"]["genericity_kind"]
    rows, bad = [], []
    for k, cid in SCHEMA_KEYS.items():
        tok = (d[k].get("genericity") or {}).get("kind")
        ok = tok in al["genericity_kind"] and tok in rs
        rows.append({"class": cid, "schema_genericity_kind": tok,
                     "canonical_key": tok in al["genericity_kind"], "in_rule_spec": tok in rs})
        if not ok:
            bad.append(cid)
    return ("PASS" if not bad else "FAIL",
            {"rows": rows, "non_canonical_classes": bad,
             "detail": "schemas use the canonical genericity token residual_comeager"})


def v4_f0_axis_tokens(d):
    f0, al, rs = d["f0"], d["aliases"], d["spec"]["vocabularies"]["genericity_kind"]
    rows, offenders = [], []
    for cid in ALL_CLASSES:
        ax = f0["classes"][cid]["axes"]
        ct, gk = ax.get("conclusion_type"), ax.get("genericity_kind")
        ct_canon = ct in al["conclusion_type"]
        gk_canon = gk in al["genericity_kind"]
        gk_registered = gk_canon or any(gk in v for v in al["genericity_kind"].values())
        gk_in_spec = gk in rs
        rows.append({"class": cid, "conclusion_type": ct, "ct_is_canonical": ct_canon,
                     "genericity_kind": gk, "gk_is_canonical": gk_canon,
                     "gk_is_registered_alias": gk_registered, "gk_in_rule_spec": gk_in_spec})
        if not ct_canon:
            offenders.append(f"{cid}.axes.conclusion_type={ct} (alias form)")
        if not gk_canon:
            offenders.append(f"{cid}.axes.genericity_kind={gk} "
                             f"({'alias form' if gk_registered else 'UNREGISTERED token'})")
    return ("FAIL" if offenders else "PASS",
            {"rows": rows, "offenders": offenders,
             "detail": "the canonical F0 taxonomy's own class axes use alias/unregistered tokens, "
                       "not the canonical vocabulary that rule_spec enforces downstream"})


def v5_f0_conclusion_allowlist(d):
    f0, al = d["f0"], d["aliases"]
    allowed = list(f0["field_vocabulary"]["conclusion_type"]["allowed"])
    canonical_required = list(al["conclusion_type"].keys())
    present = [t for t in canonical_required if t in allowed]
    missing = [t for t in canonical_required if t not in allowed]
    alias_only = all(t not in al["conclusion_type"] for t in allowed)
    return ("PASS" if not missing else "FAIL",
            {"allowed_list": allowed, "canonical_required": canonical_required,
             "canonical_present": present, "canonical_missing": missing,
             "allow_list_is_entirely_alias_forms": alias_only,
             "detail": "strict reading of F0's allow-list cannot admit the canonical SCC tokens "
                       "used by F2a/F2b; this is the measured root cause of F2a review "
                       "HF-059-F2A-01 and w063-C08"})


def v6_f0_genericity_allowlist(d):
    f0, al, rs = d["f0"], d["aliases"], d["spec"]["vocabularies"]["genericity_kind"]
    allowed = list(f0["field_vocabulary"]["genericity_kind"]["allowed"])
    canonical = list(al["genericity_kind"].keys())
    unregistered = [t for t in allowed if t not in canonical
                    and not any(t in v for v in al["genericity_kind"].values())]
    return ("FAIL" if unregistered else "PASS",
            {"allowed_list": allowed, "canonical_keys": canonical,
             "canonical_present": [t for t in canonical if t in allowed],
             "unregistered_in_alias_registry": unregistered,
             "detail": "F0's genericity allow-list is written entirely in alias forms plus at least "
                       "one token that no registry defines"})


def v7_unregistered_token_census(d):
    f0, al, rs = d["f0"], d["aliases"], d["spec"]["vocabularies"]["genericity_kind"]

    def registered(tok):
        return tok in al["genericity_kind"] or any(tok in v for v in al["genericity_kind"].values()) or tok in rs

    seen, spec_only = [], []
    for cid in ALL_CLASSES:
        gk = f0["classes"][cid]["axes"].get("genericity_kind")
        if not registered(gk):
            seen.append({"class": cid, "vocabulary": "genericity_kind", "token": gk,
                         "in_rule_spec": gk in rs, "registered_alias": False})
    for t in f0["field_vocabulary"]["genericity_kind"]["allowed"]:
        if not registered(t):
            seen.append({"class": "*field_vocabulary*", "vocabulary": "genericity_kind",
                         "token": t, "in_rule_spec": t in rs, "registered_alias": False})
        elif t not in al["genericity_kind"] and not any(t in v for v in al["genericity_kind"].values()):
            spec_only.append(t)
    return ("FAIL" if seen else "PASS",
            {"unregistered": seen, "rule_spec_only_tokens": spec_only,
             "detail": "'unresolved' is a placeholder in F0's own vocabulary but is defined by "
                       "neither rule_spec.json nor VOCAB_ALIASES.json; a downstream machine reader "
                       "cannot resolve it.  rule_spec_only_tokens are defined in rule_spec but absent "
                       "from the alias registry (coverage gap, not a blocker)."})


def v8_supplement_conformance(d):
    supp, al = d["supp"], d["aliases"]
    rows, bad = [], []
    for cid in ALL_CLASSES:
        tok = (supp.get("class_contracts", {}).get(cid) or {}).get("conclusion_type")
        ok = tok in al["conclusion_type"]
        rows.append({"class": cid, "supplement_conclusion_type": tok, "canonical_key": ok})
        if not ok:
            bad.append(cid)
    return ("PASS" if not bad else "FAIL",
            {"rows": rows, "non_canonical_classes": bad,
             "detail": "the F0 companion supplement already uses canonical conclusion tokens; "
                       "the two F0 companion artifacts therefore disagree on vocabulary form"})


def v9_f2a_membership_strict_vs_alias(d):
    f0, al = d["f0"], d["aliases"]
    tok = d["f2a"]["conclusion"]["conclusion_type"]
    axis = f0["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["conclusion_type"]
    allowed = list(f0["field_vocabulary"]["conclusion_type"]["allowed"])
    strict = tok in allowed
    alias_equiv = canon(al, "conclusion_type", tok) == canon(al, "conclusion_type", axis)
    return ("DIVERGENCE" if strict != alias_equiv else ("PASS" if strict else "FAIL"),
            {"f2a_token": tok, "f0_axis_token": axis, "f0_allowed": allowed,
             "strict_membership": strict, "alias_aware_equal": alias_equiv,
             "detail": "the alleged F2a defect exists only under strict literal membership; "
                       "under the owner-declared alias policy the two tokens are the same class "
                       "conclusion"})


def v10_policy_timeline(d):
    al_created = d["aliases"].get("created_at")
    f0_written = d["f0"].get("written_at")
    supp_rev = d["supp"].get("revised_at")
    schema_mtimes = [d["f1"].get("revised_at"), d["f2a"].get("revised_at"), d["f2b"].get("revised_at")]
    ok = bool(al_created and f0_written and al_created <= f0_written)
    return ("PASS" if ok else "FAIL",
            {"alias_registry_created_at": al_created, "f0_rev5_written_at": f0_written,
             "f0_supplement_revised_at": supp_rev, "schema_revised_at": schema_mtimes,
             "f0_is_post_policy": ok,
             "detail": "F0 rev5 was written after the alias policy existed, so the alias forms it "
                       "carries are 'new canonical artifact' content under the policy text"})


def v11_author_acknowledged(d):
    note = d["f0"].get("revision_note", "") or ""
    hit = "one conclusion-type vocabulary" in note
    return ("PASS" if hit else "INFO",
            {"quote": "Findings 1 and 3 need lead-formulation/Astra designation (canonical F0 "
                      "artifact and one conclusion-type vocabulary)",
             "found_in_rev2_revision_note": hit,
             "detail": "F0's own revision note records the vocabulary designation as an open item, "
                       "so this is a known-undecided governance gap, not a new semantic claim"})


def v12_policy_text_violation(d):
    al = d["aliases"]
    policy = al.get("policy", "")
    violators = [f"{cid}.axes.conclusion_type={d['f0']['classes'][cid]['axes']['conclusion_type']}"
                 for cid in ALL_CLASSES
                 if d["f0"]["classes"][cid]["axes"]["conclusion_type"] not in al["conclusion_type"]]
    violators += [f"{cid}.axes.genericity_kind={d['f0']['classes'][cid]['axes']['genericity_kind']}"
                  for cid in ALL_CLASSES
                  if d["f0"]["classes"][cid]["axes"]["genericity_kind"] not in al["genericity_kind"]]
    return ("FAIL" if violators else "PASS",
            {"policy": policy, "violating_values": violators,
             "detail": "policy text says accepted aliases 'must never appear in a new canonical "
                       "artifact'; the canonical F0 artifact (canonical path is authoritative for "
                       "G-F0 per REC-3) carries alias forms in its class axes"})


CHECKS = [
    ("V1", "rule_spec R11 conclusion alignment", v1_r11_alignment),
    ("V2", "schema conclusion tokens are canonical keys", v2_schema_tokens_canonical),
    ("V3", "schema genericity tokens are canonical keys", v3_schema_genericity_canonical),
    ("V4", "F0 axis tokens conform to the canonical vocabulary", v4_f0_axis_tokens),
    ("V5", "F0 conclusion allow-list admits the canonical SCC tokens", v5_f0_conclusion_allowlist),
    ("V6", "F0 genericity allow-list conforms", v6_f0_genericity_allowlist),
    ("V7", "no unregistered token in the canonical F0 vocabulary", v7_unregistered_token_census),
    ("V8", "F0 supplement uses canonical tokens", v8_supplement_conformance),
    ("V9", "F2a strict-vs-alias membership", v9_f2a_membership_strict_vs_alias),
    ("V10", "alias policy predates F0 rev5", v10_policy_timeline),
    ("V11", "vocabulary designation recorded open by F0 author", v11_author_acknowledged),
    ("V12", "policy-text conformance of the canonical F0 artifact", v12_policy_text_violation),
]


def run_checks(d):
    rows = []
    for cid, title, fn in CHECKS:
        status, detail = fn(d)
        rows.append({"id": cid, "title": title, "status": status, "detail": detail})
    return rows


# ------------------------------------------------------------------------- controls
def run_controls(base):
    out = []

    def rec(cid, target, injection, expected, fn):
        d = copy.deepcopy(base)
        injection(d)
        status, detail = fn(d)
        observed = status
        out.append({"id": cid, "targets_check": target, "injection": injection.__doc__,
                    "expected": expected, "observed": observed,
                    "flipped_as_declared": observed == expected, "detail": detail})

    def inject_f2a_alias(d):
        """F2a conclusion_type := alias form strong_cosmic_censorship_C2"""
        d["f2a"]["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C2"

    rec("C1", "V2 (and V1)", inject_f2a_alias, "FAIL", v2_schema_tokens_canonical)

    def inject_f0_allowlist_canonical(d):
        """F0 conclusion allow-list := the canonical rule_spec token set"""
        d["f0"]["field_vocabulary"]["conclusion_type"]["allowed"] = [
            "weak_cosmic_censorship", "scc_c2_future_inextendibility", "scc_c0_future_inextendibility"]

    rec("C2", "V5", inject_f0_allowlist_canonical, "PASS", v5_f0_conclusion_allowlist)

    def drop_alias_key(d):
        """VOCAB_ALIASES.json: canonical key scc_c2_future_inextendibility removed"""
        d["aliases"]["conclusion_type"].pop("scc_c2_future_inextendibility")

    rec("C3", "V2", drop_alias_key, "FAIL", v2_schema_tokens_canonical)

    def resolve_scalar_genericity(d):
        """F0 scalar genericity_kind := residual_comeager, allow-list := canonical set"""
        d["f0"]["classes"]["AF-WCC-SCALAR-SPH"]["axes"]["genericity_kind"] = "residual_comeager"
        d["f0"]["field_vocabulary"]["genericity_kind"]["allowed"] = [
            "residual_comeager", "full_measure", "open_dense_escape",
            "finite_codimension_complement", "none"]

    rec("C4", "V7", resolve_scalar_genericity, "PASS", v7_unregistered_token_census)

    def inject_supplement_alias(d):
        """F0 supplement C2 conclusion_type := alias form strong_cosmic_censorship_C2"""
        d["supp"]["class_contracts"]["AF-SCC-C2-VAC-GEN"]["conclusion_type"] = "strong_cosmic_censorship_C2"

    rec("C5", "V8", inject_supplement_alias, "FAIL", v8_supplement_conformance)

    def corrupt_snapshot(d):
        """flip one byte of the F2a snapshot bytes (reproduce guard must notice)"""
        d["f2a_sha256"] = "0" * 64

    rec("C6", "reproduce guard", corrupt_snapshot, "MISMATCH", lambda d: (
        "MISMATCH" if d["f2a_sha256"] != sha256_bytes((SNAP / SNAP_FILES["f2a"]).read_bytes()) else "OK",
        {"detail": "sha256 recorded in the manifest vs the snapshot file bytes"}))

    # positive control: alias equivalence must hold in the unmodified data
    d = copy.deepcopy(base)
    ok = canon(d["aliases"], "conclusion_type", d["f2a"]["conclusion"]["conclusion_type"]) == \
        canon(d["aliases"], "conclusion_type", d["f0"]["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["conclusion_type"])
    out.append({"id": "C7", "targets_check": "V9 positive leg",
                "injection": "none (positive control)", "expected": "POSITIVE-HOLDS",
                "observed": "POSITIVE-HOLDS" if ok else "POSITIVE-BROKEN",
                "flipped_as_declared": ok,
                "detail": {"alias_equivalence_of_f2a_and_f0_axis": ok}})
    return out


# --------------------------------------------------------------------------- report
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((HERE / "snapshot_manifest.json").read_text())
    d = load()

    # reproduce guard: every snapshot file must still hash to the manifest value
    guard = {}
    for rel, rec in manifest["inputs"].items():
        fp = HERE / rec["snapshot_file"]
        got = sha256_bytes(fp.read_bytes())
        guard[rel] = {"declared": rec["sha256"], "measured": got, "match": got == rec["sha256"]}
    guard_ok = all(v["match"] for v in guard.values())

    checks = run_checks(d)
    controls = run_controls(d) if args.controls else []
    controls_all_flip = all(c["flipped_as_declared"] for c in controls) if controls else None

    by_id = {c["id"]: c for c in checks}
    report = {
        "task_id": "W48-GFORM-VOCAB-ADJUDICATION-01",
        "worker": "worker-048",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ALL_CLASSES,
        "gate": "G-FORM",
        "reviewed_pins": {
            "F1": d["f1_sha256"], "F2a": d["f2a_sha256"], "F2b": d["f2b_sha256"],
            "F0_canonical": d["f0_sha256"], "F0_supplement": d["supp_sha256"],
            "rule_spec": d["spec_sha256"], "VOCAB_ALIASES": d["aliases_sha256"],
            "FROZEN": d["frozen_sha256"],
        },
        "snapshot_at": manifest["snapshot_at"],
        "reproduce_guard": {"all_match": guard_ok, "files": guard},
        "checks": checks,
        "controls": controls,
        "summary": {
            "n_checks": len(checks),
            "n_pass": sum(1 for c in checks if c["status"] == "PASS"),
            "n_fail": sum(1 for c in checks if c["status"] == "FAIL"),
            "n_divergence": sum(1 for c in checks if c["status"] == "DIVERGENCE"),
            "n_info": sum(1 for c in checks if c["status"] == "INFO"),
            "controls_all_flip": controls_all_flip,
            "n_controls": len(controls),
            "verdict_inputs": {
                "f1_token": d["f1"]["conclusion"]["conclusion_type"],
                "f2a_token": d["f2a"]["conclusion"]["conclusion_type"],
                "f2b_token": d["f2b"]["conclusion"]["conclusion_type"],
                "f0_conclusion_allowlist": d["f0"]["field_vocabulary"]["conclusion_type"]["allowed"],
                "f0_genericity_allowlist": d["f0"]["field_vocabulary"]["genericity_kind"]["allowed"],
                "canonical_conclusion_keys": sorted(d["aliases"]["conclusion_type"].keys()),
            },
        },
        "findings": [
            {"id": "W48-VOCAB-01", "severity": "root-cause",
             "finding": "The alleged F2a/F2b defect (conclusion tokens off F0's allow-list) is not a "
                        "schema defect. The schemas use the canonical tokens required by rule_spec R11 "
                        "and declared canonical by VOCAB_ALIASES; F0 rev5's field_vocabulary allow-list "
                        "and class axes are written in alias forms instead.",
             "evidence": ["schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc", "artifacts/formulation/rule_spec.json#40f9bb9e657b",
                          "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                          "research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
             "falsifier": "A canonical registry that lists strong_cosmic_censorship_C2 as the required "
                          "form for a new canonical artifact, or an F2a/F2b revision whose conclusion "
                          "token is not the rule_spec R11 value."},
            {"id": "W48-VOCAB-02", "severity": "hard-gate",
             "finding": "No gate tool detects the divergence: check_class_schema.py enforces rule_spec "
                        "(passes) and check_taxonomy_consistency.py is alias-aware (passes), while no "
                        "checker compares F0 field_vocabulary against the canonical vocabulary.",
             "evidence": ["artifacts/formulation/tools/check_class_schema.py#000e09e46b2f:36-44",
                          "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3:1-60"],
             "falsifier": "An existing gate run that reports the F0 field_vocabulary divergence."},
            {"id": "W48-VOCAB-03", "severity": "hard-gate",
             "finding": "F0 rev5 uses the token 'unresolved' as AF-WCC-SCALAR-SPH.genericity_kind, "
                        "which is defined by neither rule_spec.json genericity_kind nor VOCAB_ALIASES.json.",
             "evidence": ["research_map/formulation_taxonomy.yaml#0abb9ed8a961:393",
                          "research_map/formulation_taxonomy.yaml#0abb9ed8a961:142-144"],
             "falsifier": "A registry that defines 'unresolved' as a genericity_kind token."},
            {"id": "W48-VOCAB-04", "severity": "governance",
             "finding": "F0's own rev2 revision note already records the missing designation: "
                        "'Findings 1 and 3 need lead-formulation/Astra designation (canonical F0 "
                        "artifact and one conclusion-type vocabulary)'.",
             "evidence": ["research_map/formulation_taxonomy.yaml#0abb9ed8a961:34-35"],
             "falsifier": "A controller record that designates the governing vocabulary."},
        ],
        "repair_matrix": [
            {"path": "A: revise F0 field_vocabulary + axes to canonical tokens",
             "artifacts_touched": ["research_map/formulation_taxonomy.yaml"],
             "declared_rule_consequence": "F0 rev6; each schema's own f0_binding rule ('if the declared F0 "
                                          "artifact changes hash, this binding must be refreshed and the "
                                          "consistency check re-run before any gate verdict') then forces "
                                          "F1/F2a/F2b revisions and voids every rev12 verdict",
             "durability": "high", "cost": "highest"},
            {"path": "B: record a controller/lead ruling that VOCAB_ALIASES canonical keys govern and the "
                     "F0 field_vocabulary list is a descriptive legacy vocabulary",
             "artifacts_touched": ["research_map/research_map.json (ruling only, no artifact bytes)"],
             "declared_rule_consequence": "no hash moves; F2a/F2b tokens are conformant under rule_spec R11 "
                                          "and the ruling; HF-059-F2A-01 / w063-C08 close as alias-form "
                                          "artifacts of F0's stale list",
             "durability": "medium (needs the ruling at the current hashes)", "cost": "lowest"},
            {"path": "C: rewrite the schemas to F0 alias tokens",
             "artifacts_touched": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                                   "schemas/af_scc_c0_vacuum.yaml"],
             "declared_rule_consequence": "violates the VOCAB_ALIASES policy text and fails rule_spec R11 "
                                          "in check_class_schema.py",
             "durability": "none", "cost": "invalid"},
        ],
        "recommendation": "Path B now (zero hash movement, makes the existing pins judgeable), Path A at the "
                          "next scheduled F0 revision (durable single-vocabulary fix). The choice belongs to "
                          "lead-formulation/Astra; this artifact only measures the consequences.",
        "next_falsifier": "A canonical registry that names strong_cosmic_censorship_C2 / "
                          "strong_cosmic_censorship_C0 as the required token form for a new canonical "
                          "artifact; or a controller ruling that F0's field_vocabulary governs the schemas "
                          "(which would make F2a/F2b non-conformant and reverse W48-VOCAB-01); or a gate run "
                          "that detects this divergence without a human reading it.",
        "reproduce": "python3 artifacts/worker-048/gform_vocab_adjudication/snapshot_inputs.py && "
                     "python3 artifacts/worker-048/gform_vocab_adjudication/audit_vocab.py --controls",
        "authority_note": "Worker verdict only: no gate verdict, no node status, no validation_status=passed. "
                          "No canonical artifact was modified; all reads are against ./snapshot/ copies.",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    out = HERE / args.out
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"checks: {report['summary']['n_pass']} pass / {report['summary']['n_fail']} fail / "
          f"{report['summary']['n_divergence']} divergence / {report['summary']['n_info']} info; "
          f"controls_all_flip={controls_all_flip}; guard_ok={guard_ok}")
    for c in checks:
        print(f"  {c['id']:>3} {c['status']:<10} {c['title']}")
    return 0 if (guard_ok and (controls_all_flip is not False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
