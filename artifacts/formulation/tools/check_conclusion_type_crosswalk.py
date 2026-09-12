#!/usr/bin/env python3
"""Consistency check for the REC-37 conclusion_type crosswalk (rev14 item 4).

Compares CLASS-SCHEMA conclusion tokens to the VOCAB_ALIASES canonical mapping -- never to
F0's raw alias list. The G-F0-frozen taxonomy (research_map/formulation_taxonomy.yaml) cannot
be edited, so its alias tokens are accepted only through canonicalization; this tool fails if a
schema token is an alias (the alias policy forbids aliases in a new canonical artifact), if a
schema token disagrees with rule_spec.json, if an F0 alias token fails to canonicalize onto the
schema token, or if the pinned crosswalk artifact has gone stale against live bytes.

USAGE
  python3 check_conclusion_type_crosswalk.py           # exit 0 pass / 1 fail
  python3 check_conclusion_type_crosswalk.py --json    # machine report on stdout
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
XW_PATH = "artifacts/formulation/CONCLUSION_TYPE_CROSSWALK.json"
SCHEMA = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    fails: list[dict] = []

    def fail(rule, msg):
        fails.append({"rule": rule, "message": msg})

    xw = json.loads((ROOT / XW_PATH).read_text())
    AL = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    RS = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
    F0 = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    CONC = RS["vocabularies"]["class_conclusion_type"]
    canon_map = AL["conclusion_type"]

    def canon(tok):
        for c, al in canon_map.items():
            if tok == c or tok in al:
                return c
        return None

    # X01 pinned sources still live
    for field, rel in (
        ("canonical_mapping_source_sha256", "artifacts/formulation/VOCAB_ALIASES.json"),
        ("rule_spec_sha256", "artifacts/formulation/rule_spec.json"),
        ("f0_source_sha256", "research_map/formulation_taxonomy.yaml"),
    ):
        if xw.get(field) != sha(rel):
            fail("X01", f"crosswalk pin {field} is stale vs live {rel} "
                        f"({str(xw.get(field))[:12]} != {sha(rel)[:12]})")

    # X02 comparison rule is canonical-mapping based, not F0-raw-list based
    if "VOCAB_ALIASES" not in str(xw.get("comparison_rule", "")):
        fail("X02", "crosswalk comparison_rule must name the VOCAB_ALIASES canonical mapping")
    if "never to F0" not in str(xw.get("comparison_rule", "")):
        fail("X02", "crosswalk comparison_rule must explicitly exclude F0's raw alias list")

    # X03 one entry per schema-backed class, keys complete
    entries = {e.get("class_id"): e for e in xw.get("entries", [])}
    if set(entries) != set(SCHEMA):
        fail("X03", f"crosswalk entries {sorted(entries)} != schema-backed classes {sorted(SCHEMA)}")

    for cid, path in SCHEMA.items():
        e = entries.get(cid, {})
        d = yaml.safe_load((ROOT / path).read_text())
        stok = d["conclusion"]["conclusion_type"]
        f0tok = (F0["classes"].get(cid, {}).get("axes") or {}).get("conclusion_type")
        # X04 schema token is the rule_spec canonical token
        if stok != CONC[cid]:
            fail("X04", f"{cid}: schema token {stok!r} != rule_spec {CONC[cid]!r}")
        # X05 schema token is a canonical KEY in VOCAB_ALIASES, not an alias
        if stok not in canon_map:
            fail("X05", f"{cid}: schema token {stok!r} is not a VOCAB_ALIASES canonical key")
        # X06 F0 raw token canonicalizes onto the schema token (via VOCAB_ALIASES only)
        if canon(f0tok) != stok:
            fail("X06", f"{cid}: F0 raw token {f0tok!r} canonicalizes to {canon(f0tok)!r}, "
                        f"not onto schema token {stok!r}")
        # X07 crosswalk entry agrees with live bytes
        if e.get("schema_token") != stok:
            fail("X07", f"{cid}: crosswalk schema_token {e.get('schema_token')!r} != live {stok!r}")
        if e.get("f0_raw_token") != f0tok:
            fail("X07", f"{cid}: crosswalk f0_raw_token {e.get('f0_raw_token')!r} != live {f0tok!r}")
        if e.get("canonical_token") != stok:
            fail("X07", f"{cid}: crosswalk canonical_token {e.get('canonical_token')!r} != live {stok!r}")
        if e.get("schema_sha256") != sha(path):
            fail("X07", f"{cid}: crosswalk schema_sha256 stale vs live {path}")

    # X08 F0's declared allowed list canonicalizes entirely onto registered canonical keys
    allowed = ((F0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    uncanon = [t for t in allowed if canon(t) is None]
    if uncanon:
        fail("X08", f"F0 allowed tokens with no VOCAB_ALIASES canonical key: {uncanon}")

    rep = {
        "check": "conclusion_type_crosswalk",
        "crosswalk": XW_PATH,
        "crosswalk_sha256": sha(XW_PATH),
        "rule_spec_sha256": sha("artifacts/formulation/rule_spec.json"),
        "vocab_aliases_sha256": sha("artifacts/formulation/VOCAB_ALIASES.json"),
        "f0_source_sha256": sha("research_map/formulation_taxonomy.yaml"),
        "classes_checked": sorted(SCHEMA),
        "comparison": "schema token vs VOCAB_ALIASES canonical key (F0 raw list NOT used as the oracle)",
        "f0_residual": xw.get("residual"),
        "verdict": "pass" if not fails else "fail",
        "failed_rules": sorted({f["rule"] for f in fails}),
        "failures": fails,
    }
    out = ROOT / "artifacts/formulation/evidence/conclusion_type_crosswalk_check.json"
    out.write_text(json.dumps(rep, indent=2) + "\n")
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(("PASS" if not fails else "FAIL") + f" conclusion_type crosswalk: "
              f"{len(SCHEMA)} classes, {len(fails)} failure(s)")
        for f in fails:
            print(f"  {f['rule']}: {f['message']}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
