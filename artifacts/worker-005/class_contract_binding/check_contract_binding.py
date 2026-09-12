#!/usr/bin/env python3
"""W005-T2 cross-schema class-contract binding conformance checker (independent implementation).

Question measured (decision-relevant, class-bound):
  All three canonical schemas declare
      class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<ID>
  while f0_binding.declared_f0_artifact names research_map/formulation_taxonomy.yaml.
  The controller's canonical-path policy makes research_map/formulation_taxonomy.yaml
  authoritative, and its top-level key is `classes`, not `class_contracts` (measured).
  Reviewers disagree on whether this is blocking (F2b-review-034 F-034-2 = hard,
  F1-review-090 HF090-01 = major) or non-blocking (F2b-review-030 PTR-01 = N,
  convergence-15-rev11 N4 = N). This checker measures the part that decides B/N:
  whether the authoring contract that the pointer reaches is semantically the SAME
  class contract as the frozen canonical `classes.<ID>` on the class-identity axes.

Output: machine JSON only. No gate verdict is set here; a worker cannot set one.

Self-test: `--selftest` runs a clean control plus five planted mutants and asserts
each mutant is detected and the control passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3] if (Path(__file__).resolve().parents[3] / "schemas").is_dir() else Path.cwd()
CANON_REL = "research_map/formulation_taxonomy.yaml"
AUTH_REL = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = [
    ("F1", "AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
]
FALSIFIER_REL = "schemas/f1_falsifier_tests.jsonl"
# identity tokens comparable across the two trees (canonical axes <- authoring components).
# The two trees use different vocabularies; the mapping below is DECLARED so a reader can
# falsify it. Each entry maps every accepted spelling to one normalized token.
VOCAB = {
    "family": {"wcc": "wcc", "scc": "scc"},
    "asymptotics": {"af": "af", "asymptotically_flat_3p1": "af"},
    "matter_model": {
        "vac": "vacuum",
        "vacuum": "vacuum",
        "massless_scalar_field": "massless_scalar_field",
        "massless scalar field": "massless_scalar_field",
    },
    "regularity_token": {"none": None, "": None, "null": None, "c0": "C0", "c2": "C2"},
}
# conclusion_type labels: canonical predicate-name style vs authoring shorthand style.
# Membership in one equivalence class is a DECLARED semantic equivalence; the report prints
# both texts so the declaration can be checked or rejected on the evidence.
CONCLUSION_EQUIV = {
    "weak_cosmic_censorship": {"weak_cosmic_censorship"},
    "strong_cosmic_censorship_c2": {"strong_cosmic_censorship_c2", "scc_c2_future_inextendibility"},
    "strong_cosmic_censorship_c0": {"strong_cosmic_censorship_c0", "scc_c0_future_inextendibility"},
}
AXIS_MAP = [
    ("family", "censorship"),
    ("matter_model", "matter"),
    ("asymptotics", "asymptotics"),
    ("regularity_token", "regularity_token"),
]
NON_COMPARABLE = {
    "symmetry": "no counterpart field in authoring components for the vacuum classes",
    "genericity_kind": "authoring components.genericity is a class-id token (GEN), not a genericity kind",
}
PIN_TOLERANCE_S = 60


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw_top_level_duplicate_keys(text: str) -> dict:
    counts: dict[str, int] = {}
    for m in re.finditer(r"(?m)^([A-Za-z_][A-Za-z0-9_]*):", text):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def resolve_fragment(doc, fragment: str):
    """Resolve a dotted fragment against a parsed YAML doc. Returns (ok, detail)."""
    if not fragment:
        return False, "empty fragment"
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            where = "top-level" if cur is doc else "nested"
            return False, f"missing key {part!r} at {where} (available: {sorted(cur)[:8] if isinstance(cur, dict) else type(cur).__name__})"
    return True, f"resolved to {type(cur).__name__}"


def parse_pointer(pointer: str):
    if "#" in pointer:
        path, frag = pointer.split("#", 1)
    else:
        path, frag = pointer, ""
    pinned = None
    m = re.search(r"(?:@|sha256=|sha256:)([0-9a-fA-F]{8,64})", pointer)
    if m:
        pinned = m.group(1)
    return path, frag, pinned


def parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def compare_axes(canon_class: dict, auth_class: dict) -> dict:
    cax = canon_class.get("axes") or {}
    acp = auth_class.get("components") or {}
    rows = {}
    for ckey, akey in AXIS_MAP:
        cv, av = cax.get(ckey), acp.get(akey)
        vocab = VOCAB.get(ckey, {})
        ncv, nav = vocab.get(_norm(cv), _norm(cv)), vocab.get(_norm(av), _norm(av))
        rows[ckey] = {
            "canonical": cv,
            "authoring": av,
            "normalized_canonical": ncv,
            "normalized_authoring": nav,
            "agree": ncv == nav,
            "normalization": "declared vocabulary map" if (cv != av) else "literal",
        }
    cc = (canon_class.get("conclusion") or {}).get("type") or cax.get("conclusion_type")
    ac = auth_class.get("conclusion_type")
    ncc, nac = _norm(cc), _norm(ac)
    if ncc == nac:
        agree, basis = True, "literal"
    else:
        agree = ncc in CONCLUSION_EQUIV and nac in CONCLUSION_EQUIV[ncc]
        basis = "declared label equivalence" if agree else "labels differ and are not declared equivalent"
    rows["conclusion_type"] = {
        "canonical": cc,
        "authoring": ac,
        "normalized_canonical": ncc,
        "normalized_authoring": nac,
        "agree": agree,
        "normalization": basis,
        "canonical_text_snippet": str((canon_class.get("conclusion") or {}).get("text", ""))[:220],
        "authoring_predicate": str(auth_class.get("conclusion_predicate", ""))[:220],
    }
    return rows


def _norm(v):
    if isinstance(v, str):
        return v.strip().lower().replace("-", "_")
    return v


def check_one(node, class_id, schema_rel, canon, auth, canon_sha, auth_sha, wall):
    schema_path = ROOT / schema_rel
    text = schema_path.read_text()
    doc = yaml.safe_load(text)
    schema_sha = sha256_file(schema_path)
    pointer = str(doc.get("class_contract_pointer", ""))
    ptr_path, ptr_frag, ptr_pin = parse_pointer(pointer)

    checks = {}

    # P1 pointer is the canonical path AND its fragment resolves there
    canon_ok, canon_detail = (False, "pointer path is not the canonical artifact")
    if ptr_path == CANON_REL:
        canon_ok, canon_detail = resolve_fragment(canon, ptr_frag)
    checks["P1_pointer_resolves_canonical"] = {
        "pass": bool(canon_ok),
        "pointer_path_is_canonical": ptr_path == CANON_REL,
        "fragment_resolves": bool(canon_ok),
        "detail": canon_detail,
    }

    # P2 same fragment resolves in the authoring tree (where the pointer actually lands)
    auth_ok, auth_detail = resolve_fragment(auth, ptr_frag)
    checks["P2_pointer_resolves_authoring"] = {"pass": bool(auth_ok), "detail": auth_detail}

    # P3 pointer carries a content hash pin
    checks["P3_pointer_hash_pinned"] = {
        "pass": bool(ptr_pin),
        "pin": ptr_pin,
        "detail": "pointer carries no sha256 pin; the supplement it names changed during the review window" if not ptr_pin else "pinned",
    }

    # P4 class-identity axes equivalence canonical vs authoring
    canon_class = ((canon.get("classes") or {}).get(class_id)) or {}
    auth_class = ((auth.get("class_contracts") or {}).get(class_id)) or {}
    axes = compare_axes(canon_class, auth_class) if canon_class and auth_class else {}
    disagree = sorted(k for k, v in axes.items() if not v["agree"])
    checks["P4_identity_axes_agree"] = {
        "pass": bool(axes) and not disagree,
        "axes": axes,
        "non_comparable": NON_COMPARABLE,
        "disagree": disagree,
        "detail": "canonical classes.<id> missing" if not canon_class else ("authoring class_contracts.<id> missing" if not auth_class else f"{len(disagree)} disagreeing axis/axes"),
    }

    # P5 schema hygiene: duplicate top-level keys + future-dated machine timestamps + F0 binding
    dups = raw_top_level_duplicate_keys(text)
    future = {}
    for field, val in [("revised_at", doc.get("revised_at")), ("f0_binding.checked_at", (doc.get("f0_binding") or {}).get("checked_at"))]:
        ts = parse_ts(val)
        if ts is not None and (ts - wall).total_seconds() > PIN_TOLERANCE_S:
            future[field] = val
    declared = (doc.get("f0_binding") or {}).get("declared_f0_sha256")
    checks["P5_schema_hygiene"] = {
        "pass": (not dups) and (not future) and declared == canon_sha,
        "duplicate_top_level_keys": dups,
        "future_dated_fields": future,
        "declared_f0_sha256": declared,
        "measured_canonical_sha256": canon_sha,
        "f0_binding_matches_live_canonical": declared == canon_sha,
    }

    # P7 conclusion not composite (class-separation axis)
    concl = str(
        (doc.get("conclusion") or {}).get("conclusion_type")
        or (doc.get("conclusion") or {}).get("type")
        or doc.get("conclusion_type")
        or (doc.get("axes") or {}).get("conclusion_type")
        or ""
    )
    checks["P7_conclusion_not_composite"] = {
        "pass": bool(concl) and (" or " not in concl.lower()) and "," not in concl,
        "conclusion_type": concl,
    }

    return {
        "node_id": node,
        "class_id": class_id,
        "schema_path": schema_rel,
        "schema_sha256": schema_sha,
        "pointer": pointer,
        "pointer_path": ptr_path,
        "pointer_fragment": ptr_frag,
        "checks": checks,
        "failed_checks": sorted(k for k, v in checks.items() if not v["pass"]),
    }


def run(pins=None):
    wall = datetime.now(timezone.utc)
    canon_path, auth_path = ROOT / CANON_REL, ROOT / AUTH_REL
    canon_sha, auth_sha = sha256_file(canon_path), sha256_file(auth_path)
    canon, auth = yaml.safe_load(canon_path.read_text()), yaml.safe_load(auth_path.read_text())
    rows = [check_one(n, c, p, canon, auth, canon_sha, auth_sha, wall) for n, c, p in SCHEMAS]

    # X1 uniformity: every schema's pointer names the non-canonical tree
    non_canon = [r["node_id"] for r in rows if r["pointer_path"] != CANON_REL]
    uniform = len(non_canon) == len(rows)

    # P6 falsifier-test binding (F1's falsifier corpus must bind the reviewed F1 bytes)
    f1_sha = next(r["schema_sha256"] for r in rows if r["node_id"] == "F1")
    fpath = ROOT / FALSIFIER_REL
    binds, n_rows = set(), 0
    if fpath.is_file():
        for line in fpath.read_text().splitlines():
            if line.strip():
                n_rows += 1
                binds.add(str(json.loads(line).get("binding_sha256", "")))
    p6_pass = n_rows > 0 and binds == {f1_sha}

    report = {
        "report_id": "w005-contract-binding-" + wall.strftime("%Y%m%dT%H%M%S%z"),
        "generated_by": "worker-005 / check_contract_binding.py",
        "class_ids": [c for _, c, _ in SCHEMAS],
        "node_ids": [n for n, _, _ in SCHEMAS],
        "gate": "G-FORM",
        "measured_at": wall.isoformat(),
        "canonical_policy_source": "research_map/ASTRA_HANDOFF.md:27 (canonical paths authoritative; artifacts/formulation/** must be published byte-identically before verdicts bind)",
        "pins": {
            CANON_REL: canon_sha,
            AUTH_REL: auth_sha,
            **{r["schema_path"]: r["schema_sha256"] for r in rows},
        },
        "canonical_top_level_keys": sorted(canon.keys())[:40],
        "canonical_has_class_contracts_key": "class_contracts" in canon,
        "authoring_has_class_contracts_key": "class_contracts" in auth,
        "declared_normalizations": {
            "vocabulary_map": {k: v for k, v in VOCAB.items()},
            "conclusion_label_equivalence": {k: sorted(v) for k, v in CONCLUSION_EQUIV.items()},
            "note": "these mappings are declared, not derived; reject them and X2/P4 change accordingly",
        },
        "per_schema": rows,
        "cross_schema": {
            "X1_pointer_defect_uniform": uniform,
            "non_canonical_pointer_nodes": non_canon,
            "X2_identity_axes_agree_all": all(r["checks"]["P4_identity_axes_agree"]["pass"] for r in rows),
            "X3_conclusion_type_matches_authoring_all": all(r["checks"]["P4_identity_axes_agree"]["axes"].get("conclusion_type", {}).get("agree") for r in rows),
        },
        "P6_f1_falsifier_binding": {
            "pass": p6_pass,
            "rows": n_rows,
            "binding_sha256_values": sorted(binds),
            "measured_f1_sha256": f1_sha,
        },
    }
    if pins:
        report["pins_expected"] = pins
        report["pins_match_expected"] = all(
            report["pins"].get(k) == v for k, v in pins.items()
        )
    report["summary"] = {
        "schemas_checked": len(rows),
        "schemas_with_canonical_pointer": len(rows) - len(non_canon),
        "schemas_with_authoring_pointer": len(non_canon),
        "identity_axes_agree_all": report["cross_schema"]["X2_identity_axes_agree_all"],
        "f1_falsifier_corpus_binds_reviewed_bytes": p6_pass,
    }
    return report


# ---------------------------------------------------------------- self-test
def _synth_clean():
    canon = {
        "classes": {
            "AF-TEST-GEN": {
                "axes": {"family": "WCC", "matter_model": "vacuum", "asymptotics": "AF", "regularity_token": None, "genericity_kind": "baire", "conclusion_type": "wcc"},
                "conclusion": {"type": "wcc"},
            }
        }
    }
    auth = {
        "class_contracts": {
            "AF-TEST-GEN": {
                "components": {"censorship": "WCC", "matter": "vacuum", "asymptotics": "AF", "regularity_token": None},
                "conclusion_type": "wcc",
            }
        }
    }
    return canon, auth


def selftest():
    import tempfile

    canon, auth = _synth_clean()
    canon_sha = hashlib.sha256(yaml.safe_dump(canon, sort_keys=True).encode()).hexdigest()
    results, failures = {}, []

    def run_case(name, schema_doc, expect_pass_checks, expect_fail_checks):
        with tempfile.TemporaryDirectory() as td:
            sp = Path(td) / "schema.yaml"
            sp.write_text(yaml.safe_dump(schema_doc, sort_keys=False))
            r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth, canon_sha, "auth", datetime.now(timezone.utc))
            for k in expect_pass_checks:
                if not r["checks"][k]["pass"]:
                    failures.append(f"{name}: expected PASS {k}")
            for k in expect_fail_checks:
                if r["checks"][k]["pass"]:
                    failures.append(f"{name}: expected FAIL {k}")
            results[name] = {"failed": r["failed_checks"], "expect_pass": expect_pass_checks, "expect_fail": expect_fail_checks}

    clean = {
        "class_contract_pointer": CANON_REL + "#classes.AF-TEST-GEN",
        "revised_at": "2020-01-01T00:00:00+00:00",
        "f0_binding": {"checked_at": "2020-01-01T00:00:00+00:00", "declared_f0_sha256": canon_sha},
        "conclusion": {"type": "wcc"},
    }
    # a canonical pointer resolves in the canonical tree and, by design, NOT in the
    # authoring tree (which uses the class_contracts key) - P2 must fail here.
    run_case("control_canonical_pointer", clean,
             ["P1_pointer_resolves_canonical", "P4_identity_axes_agree", "P5_schema_hygiene"],
             ["P2_pointer_resolves_authoring", "P3_pointer_hash_pinned"])

    # the live defect shape: pointer targeting the authoring tree
    auth_ptr = json.loads(json.dumps(clean))
    auth_ptr["class_contract_pointer"] = AUTH_REL + "#class_contracts.AF-TEST-GEN"
    run_case("control_authoring_pointer", auth_ptr,
             ["P2_pointer_resolves_authoring", "P4_identity_axes_agree"],
             ["P1_pointer_resolves_canonical"])

    # a hash-pinned pointer must pass P3
    pinned = json.loads(json.dumps(clean))
    pinned["class_contract_pointer"] = AUTH_REL + "#class_contracts.AF-TEST-GEN@sha256:" + canon_sha
    run_case("control_pinned_pointer", pinned, ["P3_pointer_hash_pinned"], [])

    m_axes = json.loads(json.dumps(clean))
    auth2 = json.loads(json.dumps(auth))
    auth2["class_contracts"]["AF-TEST-GEN"]["conclusion_type"] = "scc_c0"
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(yaml.safe_dump(m_axes, sort_keys=False))
        r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth2, canon_sha, "auth", datetime.now(timezone.utc))
        if r["checks"]["P4_identity_axes_agree"]["pass"]:
            failures.append("mutant_axes_mismatch: not detected")
        results["mutant_axes_mismatch"] = {"disagree": r["checks"]["P4_identity_axes_agree"]["disagree"]}

    # mutant: a comparable vocabulary token genuinely differs (not the known AF/VAC spellings)
    auth3 = json.loads(json.dumps(auth))
    auth3["class_contracts"]["AF-TEST-GEN"]["components"]["censorship"] = "SCC"
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(yaml.safe_dump(clean, sort_keys=False))
        r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth3, canon_sha, "auth", datetime.now(timezone.utc))
        if r["checks"]["P4_identity_axes_agree"]["pass"]:
            failures.append("mutant_vocab_mismatch: not detected")
        results["mutant_vocab_mismatch"] = {"disagree": r["checks"]["P4_identity_axes_agree"]["disagree"]}

    m_dup = clean.copy()
    dup_text = yaml.safe_dump(clean, sort_keys=False) + "revised_at: 2020-01-02T00:00:00+00:00\n"
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(dup_text)
        dups = raw_top_level_duplicate_keys(dup_text)
        if "revised_at" not in dups:
            failures.append("mutant_duplicate_key: not detected")
        results["mutant_duplicate_key"] = {"duplicates": dups}

    m_future = json.loads(json.dumps(clean))
    m_future["revised_at"] = "2099-01-01T00:00:00+00:00"
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(yaml.safe_dump(m_future, sort_keys=False))
        r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth, canon_sha, "auth", datetime.now(timezone.utc))
        if r["checks"]["P5_schema_hygiene"]["pass"]:
            failures.append("mutant_future_timestamp: not detected")
        results["mutant_future_timestamp"] = {"future": r["checks"]["P5_schema_hygiene"]["future_dated_fields"]}

    m_nopin = {"class_contract_pointer": CANON_REL + "#classes.AF-TEST-GEN", "f0_binding": {"declared_f0_sha256": canon_sha}}
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(yaml.safe_dump(m_nopin, sort_keys=False))
        r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth, canon_sha, "auth", datetime.now(timezone.utc))
        if r["checks"]["P3_pointer_hash_pinned"]["pass"]:
            failures.append("mutant_unpinned_pointer: not detected")
        results["mutant_unpinned_pointer"] = {"pass": r["checks"]["P3_pointer_hash_pinned"]["pass"]}

    m_shifted = json.loads(json.dumps(clean))
    m_shifted["f0_binding"]["declared_f0_sha256"] = "deadbeef" * 8
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "schema.yaml"
        sp.write_text(yaml.safe_dump(m_shifted, sort_keys=False))
        r = check_one("TX", "AF-TEST-GEN", str(sp), canon, auth, canon_sha, "auth", datetime.now(timezone.utc))
        if r["checks"]["P5_schema_hygiene"]["pass"]:
            failures.append("mutant_f0_binding_shift: not detected")
        results["mutant_f0_binding_shift"] = {"pass": r["checks"]["P5_schema_hygiene"]["pass"]}

    out = {"selftest": "PASS" if not failures else "FAIL", "failures": failures, "cases": results,
           "cases_run": len(results), "mutants_detected": len(results) - 1 if not failures else None}
    print(json.dumps(out, indent=1))
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    rep = run()
    text = json.dumps(rep, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    # exit code: 0 report emitted (checks may contain failures); 3 = could not measure
    sys.exit(0)


if __name__ == "__main__":
    main()
