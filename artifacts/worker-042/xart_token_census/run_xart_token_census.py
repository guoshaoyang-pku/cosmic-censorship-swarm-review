#!/usr/bin/env python3
"""W042-XART-TOKEN-CENSUS-07: cross-artifact conclusion-token binding census.

Reads ONLY the frozen snapshot produced by pin_inputs.py, then re-hashes the
live files to detect post-pin drift. Deterministic given identical input bytes
(the deterministic_payload_sha256 excludes only generated_at).

Question: for each of the four frozen classes, what conclusion-type token does
each frozen artifact carry, and is the F0-declared vocabulary
(field_vocabulary.conclusion_type.allowed) internally consistent with the frozen
alias policy (VOCAB_ALIASES.json: "canonical token first; accepted aliases are
equivalent for consistency checks only and must never appear in a new canonical
artifact")?

Checks
  E1_TOKENS_PRESENT     every audited surface yields a mappable conclusion token
                        for the four frozen classes (no missing/blank/unmapped).
  E2_WITHIN_CLASS_AGREE all surfaces of one class map to one canonical group.
  E3_SCHEMA_CANONICAL   the three schema conclusion.conclusion_type tokens are
                        the canonical group token (alias policy rule 1).
  E4_NO_MERGE           four distinct canonical groups; no rejected/ambiguous
                        token anywhere (C0/C2 not merged).
  E5_VOCAB_CANONICAL    F0 field_vocabulary.conclusion_type.allowed uses the
                        canonical group tokens, not aliases (policy rule 1).
  E6_CLASS_IDENTITY     class ids on schema/supplement surfaces are exactly the
                        four frozen ids.
  E7_FROZEN_PINS        every audited input listed in FROZEN.json matches the
                        snapshot bytes at its declared sha256.

Exit: 0 all checks pass, 1 at least one check fails, 2 hash/pin drift,
      3 input missing, 4 a pre-registered control misbehaved.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import yaml

FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
INPUTS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
] + list(SCHEMAS.values())
P_F0 = "research_map/formulation_taxonomy.yaml"
P_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
P_FROZEN = "artifacts/formulation/FROZEN.json"
P_ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
P_VARIANTS = "artifacts/formulation/VARIANT_REGISTRY.json"
P_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_aliases(doc):
    canonical_of, group_of, rejected = {}, {}, {}
    for group, members in (doc.get("conclusion_type") or {}).items():
        for m in [group] + list(members or []):
            canonical_of[str(m)] = group
            group_of[str(m)] = group
    for tok, why in (doc.get("rejected_ambiguous_tokens") or {}).items():
        rejected[str(tok)] = str(why)
    return canonical_of, group_of, rejected


def classify(token, canonical_of, group_of, rejected):
    if token is None or str(token).strip() == "":
        return {"raw": token, "canonical_token": None, "group": None, "class": "MISSING"}
    tok = str(token)
    if tok in rejected:
        return {"raw": tok, "canonical_token": None, "group": None, "class": "REJECTED", "why": rejected[tok]}
    if tok in canonical_of:
        return {"raw": tok, "canonical_token": canonical_of[tok], "group": group_of[tok],
                "class": "CANONICAL" if canonical_of[tok] == tok else "ALIAS"}
    return {"raw": tok, "canonical_token": None, "group": None, "class": "UNMAPPED"}


def snap_path(root, rel):
    """Snapshot copies are flat-named <path with __>.<sha12>; resolve via prefix scan."""
    flat = rel.replace("/", "__")
    for name in sorted(os.listdir(root)):
        if name.startswith(flat + ".") and name != "manifest.json":
            return os.path.join(root, name)
    return os.path.join(root, rel)


def surface_rows(root, rel):
    """Yield (surface, class_id, token, is_identity) for one audited file."""
    path = snap_path(root, rel)
    rows = []
    if rel == P_F0:
        d = yaml.safe_load(open(path))
        for cid in FROZEN_CLASSES:
            c = (d.get("classes") or {}).get(cid) or {}
            rows.append(("F0.classes[%s].axes.conclusion_type" % cid, cid,
                         (c.get("axes") or {}).get("conclusion_type"), False))
            rows.append(("F0.classes[%s].conclusion.type" % cid, cid,
                         (c.get("conclusion") or {}).get("type"), False))
        allowed = ((d.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
        for i, tok in enumerate(allowed):
            rows.append(("F0.field_vocabulary.conclusion_type.allowed[%d]" % i, None, tok, False))
    elif rel == P_SUPP:
        d = yaml.safe_load(open(path))
        for cid, cc in (d.get("class_contracts") or {}).items():
            rows.append(("supplement.class_contracts[%s].conclusion_type" % cid, cid,
                         (cc or {}).get("conclusion_type"), False))
        for i, cid in enumerate(d.get("frozen_classes") or []):
            rows.append(("supplement.frozen_classes[%d]" % i, cid, cid, True))
    elif rel in SCHEMAS.values():
        d = yaml.safe_load(open(path))
        cid = d.get("class_id")
        rows.append(("%s.conclusion.conclusion_type" % rel, cid,
                     (d.get("conclusion") or {}).get("conclusion_type"), False))
        rows.append(("%s.class_id" % rel, cid, cid, True))
    elif rel == P_VARIANTS:
        d = json.load(open(path))
        for v in (d.get("variants") or []):
            if isinstance(v, dict):
                rows.append(("variant_registry.variants[%s].parent_class" % v.get("variant_id"),
                             v.get("parent_class"), v.get("parent_class"), True))
    return rows


def build_census(root, aliases_doc):
    canonical_of, group_of, rejected = load_aliases(aliases_doc)
    census = {cid: {"surfaces": [], "groups": set(), "identity_ids": set()} for cid in FROZEN_CLASSES}
    vocabulary, foreign_ids = [], []
    for rel in (P_F0, P_SUPP, P_VARIANTS) + tuple(SCHEMAS.values()):
        for surface, cid, token, is_identity in surface_rows(root, rel):
            if is_identity:
                if cid is not None and cid not in FROZEN_CLASSES:
                    foreign_ids.append("%s -> %r" % (surface, cid))
                if cid in census:
                    census[cid]["identity_ids"].add(cid)
                continue
            cl = classify(token, canonical_of, group_of, rejected)
            rec = {"path": rel, "surface": surface, "class_id": cid}
            rec.update(cl)
            if cid is None and rel == P_F0 and "field_vocabulary" in surface:
                vocabulary.append(rec)
            elif cid in census:
                census[cid]["surfaces"].append(rec)
                if cl["group"]:
                    census[cid]["groups"].add(cl["group"])
            else:
                foreign_ids.append("%s -> class %r token %r" % (surface, cid, token))
    return census, vocabulary, foreign_ids


def check_census(census, vocabulary, foreign_ids, root):
    checks = []

    def add(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    missing = []
    for cid in FROZEN_CLASSES:
        for s in census[cid]["surfaces"]:
            if s["class"] in ("MISSING", "UNMAPPED", "REJECTED"):
                missing.append("%s [%s] token=%r" % (s["surface"], s["class"], s["raw"]))
    add("E1_TOKENS_PRESENT", not missing, missing or ["all audited surfaces carry a mappable token"])

    disagree = {cid: sorted(census[cid]["groups"]) for cid in FROZEN_CLASSES if len(census[cid]["groups"]) > 1}
    add("E2_WITHIN_CLASS_AGREE", not disagree,
        disagree or ["each class's surfaces map to exactly one canonical group"])

    schema_bad = []
    for cid in FROZEN_CLASSES:
        for s in census[cid]["surfaces"]:
            if s["path"] in SCHEMAS.values() and s["class"] != "CANONICAL":
                schema_bad.append("%s token=%r (%s)" % (s["path"], s["raw"], s["class"]))
    add("E3_SCHEMA_CANONICAL", not schema_bad,
        schema_bad or ["all three schema conclusion tokens are canonical (policy rule 1)"])

    groups = {cid: sorted(census[cid]["groups"]) for cid in FROZEN_CLASSES}
    non_singleton = {cid: g for cid, g in groups.items() if len(g) != 1}
    c0_c2_merged = groups["AF-SCC-C0-VAC-GEN"] == groups["AF-SCC-C2-VAC-GEN"]
    rejected_seen = ["%s token=%r" % (s["surface"], s["raw"])
                     for cid in FROZEN_CLASSES for s in census[cid]["surfaces"] if s["class"] == "REJECTED"]
    merge_detail = []
    if non_singleton:
        merge_detail.append({"not_single_valued": non_singleton})
    if c0_c2_merged:
        merge_detail.append({"c0_c2_merged": groups["AF-SCC-C0-VAC-GEN"]})
    if rejected_seen:
        merge_detail.append({"rejected_tokens": rejected_seen})
    add("E4_NO_MERGE", not merge_detail,
        merge_detail or {"per_class_groups": groups,
                         "distinct_groups": sorted({g for v in groups.values() for g in v}),
                         "note": "each class single-valued; C0 and C2 distinct; no rejected/ambiguous token observed"})

    vocab_bad = [{"surface": v["surface"], "token": v["raw"], "class": v["class"],
                  "canonical_token": v["canonical_token"]} for v in vocabulary if v["class"] != "CANONICAL"]
    add("E5_VOCAB_CANONICAL", not vocab_bad,
        vocab_bad or ["F0 declared allowed-list tokens are canonical"])

    id_bad = list(foreign_ids)
    for rel in SCHEMAS.values():
        d = yaml.safe_load(open(snap_path(root, rel)))
        if d.get("class_id") != SCHEMA_CLASS.get(rel):
            id_bad.append("%s class_id=%r != expected %r" % (rel, d.get("class_id"), SCHEMA_CLASS.get(rel)))
    supp = yaml.safe_load(open(snap_path(root, P_SUPP)))
    if sorted(str(x) for x in (supp.get("frozen_classes") or [])) != sorted(FROZEN_CLASSES):
        id_bad.append("supplement.frozen_classes=%r" % (supp.get("frozen_classes"),))
    add("E6_CLASS_IDENTITY", not id_bad, id_bad or ["class ids on schema/supplement/variant surfaces are the four frozen ids"])

    return checks


SCHEMA_CLASS = {  # path -> owning class
    "schemas/af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
    "schemas/af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
    "schemas/af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
}


def check_frozen_pins(root):
    frozen = json.load(open(snap_path(root, P_FROZEN)))
    files = frozen.get("files") or {}
    bad, audited = [], []
    for rel, rec in files.items():
        if rel not in INPUTS:
            continue
        p = snap_path(root, rel)
        if not os.path.isfile(p):
            bad.append("%s listed in FROZEN but missing in snapshot" % rel)
            continue
        live = sha256_file(p)
        if live != rec.get("sha256"):
            bad.append("%s declared %s measured %s" % (rel, str(rec.get("sha256"))[:12], live[:12]))
        audited.append(rel)
    missing_from_manifest = [r for r in INPUTS if r != P_FROZEN and r not in files]
    if missing_from_manifest:
        bad.append("audited inputs not listed in FROZEN: %s" % missing_from_manifest)
    residual = None
    if P_FROZEN not in files:
        residual = ("FROZEN.json does not and structurally cannot list its own sha256; "
                    "its bytes are pinned by snapshot manifest %s instead" % sha256_file(snap_path(root, P_FROZEN))[:12])
    out = {"id": "E7_FROZEN_PINS", "ok": not bad,
           "detail": bad or ["%d/%d audited inputs match their FROZEN.json pins" % (len(audited), len(INPUTS))]}
    if residual:
        out["residual_note"] = residual
    return out


def run_controls(root, aliases_doc, tmpdir):
    """Mutation controls on a private copy; each must flip its pre-registered check."""
    results = []

    def set_token(rel, d, token):
        d["conclusion"] = dict(d.get("conclusion") or {})
        d["conclusion"]["conclusion_type"] = token
        return d

    def case(name, rel_target, mutator, check_id):
        work = os.path.join(tmpdir, name)
        for rel in (P_F0, P_SUPP, P_VARIANTS) + tuple(SCHEMAS.values()):
            dst = os.path.join(work, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            raw = open(snap_path(root, rel), "rb").read()
            if rel in SCHEMAS.values():
                d = yaml.safe_load(raw)
                d = mutator(rel, d)
                with open(dst, "w") as fh:
                    yaml.safe_dump(d, fh, sort_keys=False)
            else:
                with open(dst, "wb") as fh:
                    fh.write(raw)
        census, vocab, foreign = build_census(work, aliases_doc)
        checks = {c["id"]: c for c in check_census(census, vocab, foreign, work)}
        results.append({"control": name, "expected_check": check_id,
                        "detected": bool(not checks[check_id]["ok"]),
                        "observed_detail": checks[check_id]["detail"]})

    c2, c0, f1 = SCHEMAS["F2a"], SCHEMAS["F2b"], SCHEMAS["F1"]
    case("M1_SCHEMA_ALIAS_TOKEN", c2, lambda r, d: set_token(r, d, "strong_cosmic_censorship_C2") if r == c2 else d,
         "E3_SCHEMA_CANONICAL")
    case("M2_SCHEMA_BOGUS_TOKEN", f1, lambda r, d: set_token(r, d, "weak_cosmic_censorship_typo") if r == f1 else d,
         "E1_TOKENS_PRESENT")
    case("M3_REJECTED_MERGE_TOKEN", c0, lambda r, d: set_token(r, d, "strong_cosmic_censorship") if r == c0 else d,
         "E1_TOKENS_PRESENT")
    case("M4_CLASS_TOKEN_CROSSWIRE", c2, lambda r, d: set_token(r, d, "scc_c0_future_inextendibility") if r == c2 else d,
         "E2_WITHIN_CLASS_AGREE")
    case("M5_BASELINE_UNCHANGED", None, lambda r, d: d, "E2_WITHIN_CLASS_AGREE")
    return results


def build_findings(root, census, vocabulary):
    """Pre-registered finding list; each finding carries its own falsifier.

    F-1 is the E5 failure. F-2 records the measured consumer-rule divergence at the
    same F0 field (literal-membership vs alias-registry) and is severity evidence,
    not a fresh check: it is added only when F-1 holds.
    """
    findings = []
    alias_vocab = [v for v in vocabulary if v["class"] == "ALIAS"]
    if alias_vocab:
        findings.append({
            "id": "F-1",
            "severity": "hard",
            "severity_basis": "alias policy rule 1 says accepted aliases must never appear in a new canonical artifact; F0 is a frozen canonical artifact (status %r, draft_unverified)." % (
                yaml.safe_load(open(snap_path(root, P_F0))).get("status"),),
            "surface": "research_map/formulation_taxonomy.yaml#field_vocabulary.conclusion_type.allowed",
            "measured": [{"index": v["surface"], "token": v["raw"], "canonical_token": v["canonical_token"]} for v in alias_vocab],
            "statement": "The F0 declared allowed-list carries the non-canonical alias forms for the two SCC classes where every other canonical artifact (F0 class axes, supplement class_contracts, schemas) carries the canonical forms.",
            "falsifier": "Re-run at the pinned hashes: falsified if every token in field_vocabulary.conclusion_type.allowed is its own canonical group token, or if VOCAB_ALIASES.json no longer declares scc_c2_future_inextendibility / scc_c0_future_inextendibility canonical.",
        })

        # measured consumer-rule divergence over the same frozen F0 field
        f0 = yaml.safe_load(open(snap_path(root, P_F0)))
        allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
        canonical_of, _, _ = load_aliases(json.load(open(snap_path(root, P_ALIASES))))
        rows = []
        for node, rel in SCHEMAS.items():
            d = yaml.safe_load(open(snap_path(root, rel)))
            ct = (d.get("conclusion") or {}).get("conclusion_type")
            rows.append({
                "node": node,
                "schema_token": ct,
                "literal_membership_in_F0_allowed": ct in allowed,
                "alias_registry_rule_accepts": ct in canonical_of,
                "rules_agree": (ct in allowed) == (ct in canonical_of),
            })
        divergent = [r for r in rows if not r["rules_agree"]]
        if divergent:
            findings.append({
                "id": "F-2",
                "severity": "hard",
                "severity_basis": "two reviewer-side consumers of the same F0 field return opposite results on the same frozen bytes: worker-019 check_f2a_independent.py B1 (hard, literal membership) FAILS, worker-097 check_f2b_rev13.py alias_allowed (alias-registry) PASSES. Reproduced here mechanically from the frozen bytes.",
                "surface": "research_map/formulation_taxonomy.yaml#field_vocabulary.conclusion_type.allowed",
                "divergent_rows": divergent,
                "all_rows": rows,
                "statement": "F0's allowed-list is simultaneously the field that makes a hard literal-membership check fail and the field that an alias-aware check passes; the field's own non-canonical content is what separates the two rules.",
                "falsifier": "Re-run at the pinned hashes: falsified if no audited schema token has literal_membership_in_F0_allowed != alias_registry_rule_accepts, or if worker-019 B1 and worker-097 alias_allowed are shown to be the same rule.",
            })
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    root, out = os.path.abspath(args.root), os.path.abspath(args.out)
    snap = os.path.join(out, "snapshot")
    man_path = os.path.join(snap, "manifest.json")
    if not os.path.isfile(man_path):
        print("no snapshot manifest; run pin_inputs.py first", file=sys.stderr)
        return 3
    manifest = json.load(open(man_path))
    manifest_sha = sha256_file(man_path)

    snap_bad = [rel for rel, rec in manifest["inputs"].items()
                if not os.path.isfile(os.path.join(snap, rec["snapshot_name"]))
                or sha256_file(os.path.join(snap, rec["snapshot_name"])) != rec["sha256"]]
    if snap_bad:
        print("snapshot integrity failure: %s" % snap_bad, file=sys.stderr)
        return 2
    drift = [rel for rel, rec in manifest["live_after"].items()
             if not os.path.isfile(os.path.join(root, rel))
             or sha256_file(os.path.join(root, rel)) != rec["sha256"]]
    if drift:
        print("LIVE DRIFT after pin: %s" % drift, file=sys.stderr)
        return 2

    aliases_doc = json.load(open(os.path.join(snap, manifest["inputs"][P_ALIASES]["snapshot_name"])))
    census, vocabulary, foreign = build_census(snap, aliases_doc)
    checks = check_census(census, vocabulary, foreign, snap)
    checks.append(check_frozen_pins(snap))
    findings = build_findings(snap, census, vocabulary)
    controls = run_controls(snap, aliases_doc, os.path.join(out, "_control_sandbox"))
    controls_ok = (all(c["detected"] for c in controls if c["control"] != "M5_BASELINE_UNCHANGED")
                   and not any(c["detected"] for c in controls if c["control"] == "M5_BASELINE_UNCHANGED"))

    payload = {
        "task_id": "W042-XART-TOKEN-CENSUS-07",
        "tool_sha256": sha256_file(os.path.abspath(__file__)),
        "snapshot_manifest_sha256": manifest_sha,
        "frozen_revision": json.load(open(os.path.join(snap, manifest["inputs"][P_FROZEN]["snapshot_name"]))).get("revision"),
        "inputs": {rel: rec["sha256"] for rel, rec in sorted(manifest["inputs"].items())},
        "pin_window_drift": manifest.get("pin_window_drift", []),
        "census": {
            cid: {
                "groups": sorted(census[cid]["groups"]),
                "surfaces": [
                    {"path": s["path"], "surface": s["surface"], "token": s["raw"],
                     "class": s["class"], "canonical_token": s["canonical_token"]}
                    for s in census[cid]["surfaces"]
                ],
            }
            for cid in FROZEN_CLASSES
        },
        "declared_vocabulary": [
            {"surface": v["surface"], "token": v["raw"], "class": v["class"],
             "canonical_token": v["canonical_token"], "group": v["group"]}
            for v in vocabulary
        ],
        "findings": findings,
        "checks": checks,
        "controls": controls,
        "controls_ok": bool(controls_ok),
        "all_checks_pass": all(c["ok"] for c in checks),
    }
    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "deterministic_payload": payload,
        "deterministic_payload_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    rep_path = args.report or os.path.join(out, "report.json")
    with open(rep_path, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("report: %s" % rep_path)
    print("deterministic_payload_sha256: %s" % report["deterministic_payload_sha256"])
    for c in checks:
        print("  %-22s %s" % (c["id"], "PASS" if c["ok"] else "FAIL"))
    for c in controls:
        print("  control %-26s detected=%s" % (c["control"], c["detected"]))
    if not controls_ok:
        return 4
    return 0 if payload["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
