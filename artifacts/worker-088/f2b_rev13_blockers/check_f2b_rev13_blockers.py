#!/usr/bin/env python3
"""F2b rev13 live-blocker probe (worker-088, class AF-SCC-C0-VAC-GEN, gate G-FORM).

Independent, read-only measurement of the distinct blocker families raised by the
rev13 F2b review wave against the canonical bytes at hash b2ab6acb2bbe. Emits a
machine-readable disposition per blocker. No gate verdict; writes only --out.

Blocker families measured:
  B1 inverted_containment_premise   forbidden_transfers[*].reason direction vs the
                                    file's own extension_class_containment chain
  B2 stale_containment_denial       regularity.must_not_conflate entry denying a
                                    containment the same file asserts elsewhere
  B3 vocabulary_binding_gap         conclusion.conclusion_type / genericity.kind
                                    canonical-vs-F0-allowed membership and whether
                                    an alias registry is bound in the schema
  B4 evidence_not_self_verifying    f0_binding consistency evidence resolves but
                                    records no sha256 of the inputs it compared

Usage:
  python3 check_f2b_rev13_blockers.py --out report.json [--schema PATH] [--label live]
Exit code 0 if every probe executed (dispositions may be LIVE_DEFECT); 2 on drift.
"""
import argparse
import datetime as _dt
import hashlib
import json
import re
import sys

import yaml

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"

DEFAULTS = {
    "schema": f"{ROOT}/schemas/af_scc_c0_vacuum.yaml",
    "sibling": f"{ROOT}/schemas/af_scc_c2_vacuum.yaml",
    "taxonomy": f"{ROOT}/research_map/formulation_taxonomy.yaml",
    "aliases": f"{ROOT}/artifacts/formulation/VOCAB_ALIASES.json",
    "evidence": f"{ROOT}/artifacts/formulation/evidence/taxonomy_consistency.json",
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return text, yaml.safe_load(text)


def strict_duplicate_keys(text):
    """Return list of duplicate-key paths using the composer (strict readers)."""
    dups = []

    def walk(node, path):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for key_node, value_node in node.value:
                key = key_node.value
                if key in seen:
                    dups.append(f"{path}/{key}")
                seen[key] = True
                walk(value_node, f"{path}/{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, item in enumerate(node.value):
                walk(item, f"{path}[{i}]")

    walk(yaml.compose(text), "")
    return dups


def line_of(text, needle):
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def probe_b1(schema_text, schema, sibling):
    """Inverted containment premise in forbidden_transfers reasons."""
    ledger = schema.get("implication_ledger") or {}
    chain = str(ledger.get("extension_class_containment") or "")
    transfers = ledger.get("forbidden_transfers") or []
    findings = []
    for idx, row in enumerate(transfers):
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "")
        frm = str(row.get("from") or "")
        to = str(row.get("to") or "")
        says_larger = bool(re.search(r"strictly\s+larger", reason))
        says_smaller = bool(re.search(r"strictly\s+smaller", reason))
        if says_larger and "C2" in frm:
            findings.append(
                {
                    "row_index": idx,
                    "from": frm,
                    "to": to,
                    "reason": reason,
                    "line": line_of(schema_text, reason[:60]) if reason else None,
                    "defect": "premise says C2 extension class is strictly LARGER",
                    "chain_says": "E_C2 is the innermost/smallest set"
                    if "E_C2" in chain
                    else "chain not parsed",
                    "consequent_direction": "weaker" if "weaker" in reason else "?",
                    "consequent_is_correct": "weaker" in reason,
                }
            )
    sibling_ledger = sibling.get("implication_ledger") or {}
    sibling_rows = sibling_ledger.get("forbidden_transfers") or []
    sibling_reasons = [
        r.get("reason") for r in sibling_rows if isinstance(r, dict)
    ]
    return {
        "id": "B1",
        "name": "inverted_containment_premise",
        "claim": "forbidden_transfers[0].reason calls C2 the strictly larger extension "
        "class while the file's own extension_class_containment makes E_C2 the "
        "innermost (smallest) set",
        "disposition": "LIVE_DEFECT" if findings else "NOT_LIVE",
        "chain": chain,
        "hits": findings,
        "sibling_reasons": sibling_reasons,
        "sibling_corrects_direction": any(
            r and "weaker" in r for r in sibling_reasons
        ),
        "repair": "in every forbidden_transfers row whose reason asserts 'strictly "
        "larger', rewrite the premise to the file's own chain: 'E_C2 is a strictly "
        "smaller extension set than E_C0'; leave the consequent 'C2-inextendibility "
        "is strictly weaker' unchanged",
        "falsifier": "exhibit a containment-respecting reading in which E_C2 is a "
        "strictly larger extension set than E_C0, or a revision whose "
        "extension_class_containment chain makes C2 outermost",
    }


def probe_b2(schema_text, schema):
    """Stale containment denial in regularity.must_not_conflate."""
    reg = schema.get("regularity") or {}
    entries = reg.get("must_not_conflate") or []
    ledger = schema.get("implication_ledger") or {}
    chain = str(ledger.get("extension_class_containment") or "")
    asserts_h2loc_containment = ("H2loc" in chain) and (
        "E_C2" in chain or "E_{C^1,1}" in chain
    )
    hits = []
    for idx, entry in enumerate(entries):
        text = str(entry)
        if re.search(r"no\s+containment\s+with", text, re.IGNORECASE):
            hits.append(
                {
                    "entry_index": idx,
                    "line": line_of(schema_text, text[:70]),
                    "entry": text,
                    "denies_containment": True,
                    "file_asserts_h2loc_containment": asserts_h2loc_containment,
                }
            )
    return {
        "id": "B2",
        "name": "stale_containment_denial",
        "claim": "regularity.must_not_conflate denies containment with C2/C0 while "
        "the same file asserts E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
        "disposition": "LIVE_DEFECT"
        if (hits and asserts_h2loc_containment)
        else "NOT_LIVE",
        "chain": chain,
        "hits": hits,
        "repair": "replace the denial sentence with the sibling's corrected wording: "
        "H2_loc is a distinct regularity-axis value from C2 and C0, but the "
        "extension sets are nested (E_C2 subset E_{C^1,1} subset E_H2loc subset "
        "E_C0; see extension_class_containment)",
        "falsifier": "show the denial sentence concerns only regularity-axis value "
        "identity and cannot be read as a claim about extension-set containment "
        "at the bound hash",
    }


def probe_b3(schema_text, schema, taxonomy, aliases):
    """Canonical-token vs F0-allowed-list membership and registry binding."""
    fv = (taxonomy.get("field_vocabulary") or {})
    allowed_ct = list(((fv.get("conclusion_type") or {}).get("allowed")) or [])
    allowed_gk = list(((fv.get("genericity_kind") or {}).get("allowed")) or [])
    alias_ct = aliases.get("conclusion_type") or {}
    alias_gk = aliases.get("genericity_kind") or {}

    def canonical_of(registry, token):
        for canon, alist in registry.items():
            if token == canon:
                return canon
            if token in (alist or []):
                return canon
        return None

    conclusion = schema.get("conclusion") or {}
    genericity = schema.get("genericity") or {}
    ct_token = conclusion.get("conclusion_type")
    gk_token = genericity.get("kind")
    registry_bound = bool(
        re.search(r"alias_registry|VOCAB_ALIASES", schema_text)
    )

    def classify(token, allowed, registry):
        canon = canonical_of(registry, token)
        literal = token in allowed
        equiv = None
        if canon and not literal:
            aliases_of_canon = registry.get(canon) or []
            equiv = next((a for a in aliases_of_canon if a in allowed), None)
        return {
            "token": token,
            "canonical_in_registry": canon or token if token in registry else bool(canon),
            "registry_canonical": canon,
            "literal_member_of_f0_allowed": literal,
            "f0_allowed_equivalent_alias": equiv,
            "registry_bound_in_schema": registry_bound,
            "resolved": literal or (equiv is not None and registry_bound),
        }

    ct = classify(ct_token, allowed_ct, alias_ct)
    gk = classify(gk_token, allowed_gk, alias_gk)
    unresolved = [c["token"] for c in (ct, gk) if not c["resolved"]]
    return {
        "id": "B3",
        "name": "vocabulary_binding_gap",
        "claim": "the schema uses VOCAB_ALIASES canonical tokens that are not "
        "literal members of the frozen F0 allowed-lists, and binds no alias "
        "registry, so literal-membership detectors flag it and equivalence is "
        "undecidable from the artifact alone",
        "disposition": "BINDING_GAP" if unresolved else "NOT_LIVE",
        "f0_allowed": {"conclusion_type": allowed_ct, "genericity_kind": allowed_gk},
        "conclusion_type": ct,
        "genericity_kind": gk,
        "inverse_mapping": {
            "note": "F0's allowed tokens are the registry's accepted aliases; the "
            "registry's canonical tokens are absent from F0's allowed list, so no "
            "literal change can satisfy both without an explicit equivalence "
            "binding or an F0 edit (which voids G-F0)",
            "policy": aliases.get("policy"),
        },
        "repair": "declare a vocabulary_binding block in the schema that binds "
        "artifacts/formulation/VOCAB_ALIASES.json by path+sha256 and records, per "
        "field, the canonical token, its F0-allowed alias, and resolution "
        "equivalent_via_bound_alias_registry; F0 stays frozen. Owner adjudication "
        "required on whether the registry or F0's allowed list is operative.",
        "falsifier": "publish a gate-owner ruling that the F0 allowed-list is "
        "operative and the schemas must carry the literal F0 tokens (then the "
        "binding-gap repair is void), or show a bound registry already present in "
        "the schema bytes at this hash",
    }


def probe_b4(schema, schema_text, evidence, evidence_path, measured_evidence_sha):
    f0b = schema.get("f0_binding") or {}
    declared = str(f0b.get("consistency_evidence_sha256") or "")
    evidence_declares_input_hashes = False
    if isinstance(evidence, dict):
        evidence_declares_input_hashes = any(
            isinstance(v, str) and HEX64.match(v) for v in evidence.values()
        )
    resolves = bool(declared)
    declared_matches_measured = declared == measured_evidence_sha
    defect = (not declared_matches_measured) or (resolves and not evidence_declares_input_hashes)
    return {
        "id": "B4",
        "name": "evidence_not_self_verifying",
        "claim": "the consistency-evidence document that f0_binding depends on "
        "records only path strings and consistent=true; it embeds no sha256 of the "
        "inputs it compared, so the consistency claim is not reproducible from the "
        "evidence file alone",
        "disposition": "LIVE_DEFECT" if defect else "NOT_LIVE",
        "evidence_path": evidence_path,
        "declared_evidence_sha256": declared,
        "measured_evidence_sha256": measured_evidence_sha,
        "declared_matches_measured": declared_matches_measured,
        "evidence_keys": sorted(evidence.keys()) if isinstance(evidence, dict) else None,
        "evidence_declares_input_hashes": evidence_declares_input_hashes,
        "evidence_doc": evidence,
        "repair": "regenerate the evidence document so it records "
        "map_taxonomy_sha256 and lead_contract_sha256 (the two compared inputs) and "
        "the generator emits them; re-stamp f0_binding.consistency_evidence_sha256 "
        "in the same revision",
        "falsifier": "produce an evidence document at the declared path whose bytes "
        "contain the sha256 of each compared input and whose recomputation "
        "reproduces consistent=true",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default=DEFAULTS["schema"])
    ap.add_argument("--sibling", default=DEFAULTS["sibling"])
    ap.add_argument("--taxonomy", default=DEFAULTS["taxonomy"])
    ap.add_argument("--aliases", default=DEFAULTS["aliases"])
    ap.add_argument("--evidence", default=DEFAULTS["evidence"])
    ap.add_argument("--label", default="live")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pins = {
        "schema": {"path": args.schema, "sha256_before": sha256_file(args.schema)},
        "sibling": {"path": args.sibling, "sha256": sha256_file(args.sibling)},
        "taxonomy": {"path": args.taxonomy, "sha256": sha256_file(args.taxonomy)},
        "aliases": {"path": args.aliases, "sha256": sha256_file(args.aliases)},
        "evidence": {"path": args.evidence, "sha256": sha256_file(args.evidence)},
    }

    schema_text, schema = load_yaml(args.schema)
    _, sibling = load_yaml(args.sibling)
    _, taxonomy = load_yaml(args.taxonomy)
    with open(args.aliases, "r", encoding="utf-8") as fh:
        aliases = json.load(fh)
    with open(args.evidence, "r", encoding="utf-8") as fh:
        evidence = json.load(fh)

    items = [
        probe_b1(schema_text, schema, sibling),
        probe_b2(schema_text, schema),
        probe_b3(schema_text, schema, taxonomy, aliases),
        probe_b4(
            schema,
            schema_text,
            evidence,
            args.evidence,
            pins["evidence"]["sha256"],
        ),
    ]

    pins["schema"]["sha256_after"] = sha256_file(args.schema)
    drift = pins["schema"]["sha256_before"] != pins["schema"]["sha256_after"]
    report = {
        "instrument": "worker-088/f2b_rev13_blockers/check_f2b_rev13_blockers.py",
        "schema_version": "w088-f2b-blockers/v1",
        "generated_at": _dt.datetime.now().astimezone().isoformat(),
        "label": args.label,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "pins": pins,
        "drift_during_read": drift,
        "duplicate_keys": strict_duplicate_keys(schema_text),
        "items": items,
        "summary": {
            "live_defects": [i["id"] for i in items if i["disposition"] == "LIVE_DEFECT"],
            "binding_gaps": [i["id"] for i in items if i["disposition"] == "BINDING_GAP"],
            "not_live": [i["id"] for i in items if i["disposition"] == "NOT_LIVE"],
        },
        "authority_note": "worker measurement only; no gate verdict, node status or "
        "validation_status is set; no canonical artifact is written",
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(
        json.dumps(
            {
                "out": args.out,
                "label": args.label,
                "schema_sha256": pins["schema"]["sha256_before"],
                "summary": report["summary"],
                "drift": drift,
            }
        )
    )
    return 2 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
