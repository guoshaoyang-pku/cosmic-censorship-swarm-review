#!/usr/bin/env python3
"""Build the SCC-side class-binding correction patch for the canonical L1 citation ledger.

Bounded worker task, worker=009 (assignment asg-2026-09-11-L1-deepseek-flash-09-18).
Classes: AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN. Gate: G-LIT.

Problem (reviews/L1-spotcheck-09.json HF-09-CLASS-01/HF-09-CLASS-02, extended):
  ledger/citation_audit.csv binds canonical rows to frozen VACUUM class ids although
  the cited results are matter-model results (Einstein-Maxwell-scalar,
  Einstein-Maxwell-Klein-Gordon, Reissner-Nordstrom-Vaidya, FLRW).  Frozen schemas:
    - schemas/af_scc_c2_vacuum.yaml#l1_ledger_refs  T-514 scope_use
      "different data class; do not transfer"
    - schemas/af_scc_c0_vacuum.yaml#anti_scope  horizon-localized C0 reading is
      variant CH of parent AF-SCC-C0-VAC-GEN; C^{0,1}_loc is variant LIP
    - artifacts/formulation/VARIANT_REGISTRY.json  rule: cite a frozen class id or
      the (parent_class, variant_id) pair of a registered variant; variant ids are
      never class ids

This tool READS the frozen canonical ledger and emits a patch.  It never writes
ledger/citation_audit.csv.  Output is deterministic (no wall-clock inside the
artifacts) so concurrent worker instances converge on identical bytes.  Every
quote below is verified present in a locally re-fetched arXiv e-print TeX file,
and the archive sha256 is recorded.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
SPOTCHECK = ROOT / "ledger" / "citation_audit_scc_worker-009_spotcheck.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
REFETCH = ROOT / "artifacts" / "worker-009" / "refetch"
OUT_CSV = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.csv"
OUT_JSONL = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.jsonl"
OUT_VERIFY = ROOT / "artifacts" / "worker-009" / "classbinding" / "verification_classbinding_worker-009.json"
OUT_MANIFEST = ROOT / "artifacts" / "worker-009" / "classbinding" / "REFETCH_ADDENDUM_worker-009.json"

BOUND_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FROZEN_PREFIX = "315c19145065"
EVIDENCE_BASIS = "worker-009-classbinding-refetch-20260912T0034"


def tag(model: str, variant: str = "") -> str:
    """Canonical evidence/tag-only replacement cell.  Never a class-id binding."""
    mid = f" variant {variant};" if variant else ""
    return (f"(evidence/tag only; model-class: {model};{mid} "
            f"scope_use: do-not-transfer; no class-id binding)")


TEX = {
    "dafermos": "artifacts/worker-009/refetch/src_gr-qc_0307013v3/interior.tex",
    "vdm": "artifacts/worker-009/refetch/src_2001.11156v2/globalinext_revised_for_CMP.tex",
    "partII": "artifacts/worker-009/refetch/src_1702.05716v2/SCCExterior-arXiv.190222.tex",
    "partI": "artifacts/worker-009/refetch/src_1702.05715v2/SCCInterior-arXiv-190222.tex",
    "holonomy": "artifacts/worker-009/refetch/src_2007.12049v2/21_07_09_RevisedVersionForDMJ.tex",
    "scattering": "artifacts/worker-009/refetch/src_2201.12294v2/massinflation.220613.arxiv.tex",
}
ARCHIVE = {
    "dafermos": "artifacts/worker-009/refetch/src_gr-qc_0307013v3.tar.gz",
    "vdm": "artifacts/worker-009/refetch/src_2001.11156v2.tar.gz",
    "partII": "artifacts/worker-009/refetch/src_1702.05716v2.tar.gz",
    "partI": "artifacts/worker-009/refetch/src_1702.05715v2.tar.gz",
    "holonomy": "artifacts/worker-009/refetch/src_2007.12049v2.tar.gz",
    "scattering": "artifacts/worker-009/refetch/src_2201.12294v2.tar.gz",
}
Q_DAF = r"for the Einstein-Maxwell-\(real\) scalar field equations\."
Q_VDM = r"Einstein--Maxwell--Klein--Gordon equations"
Q_PARTII = (r"we prove the \$C\^2\$-formulation of the strong cosmic censorship conjecture for the "
            r"Einstein--Maxwell--\(real\)--scalar--field system in spherical symmetry for two-ended "
            r"asymptotically flat data")
Q_PARTI = (r"we prove the \$C\^\{2\}\$-formulation of the strong cosmic censorship conjecture for the "
           r"Einstein--Maxwell--\(real\)--scalar--field system in spherical symmetry for two-ended "
           r"asymptotically flat data")
Q_HOL = (r"spacetimes which arise from small and generic spherically symmetric perturbations of "
         r"two-ended subextremal Reissner-Nordstr\\\"om initial data for the Einstein-Maxwell-scalar "
         r"field system")
Q_SCAT = (r"we prove a conditional mass inflation result for a nonlinear system, namely, the "
          r"Einstein--Maxwell--\(real\)--scalar field system in spherical symmetry")

CORRECTIONS = [
    {
        "correction_id": "CBC-09-001", "canonical_row_id": "SRC-021",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN",
        "new_class_mapping": tag("Einstein-Maxwell-scalar", "CH parent AF-SCC-C0-VAC-GEN"),
        "matter_model": "Einstein-Maxwell-(real)-scalar, spherical symmetry",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "parent AF-SCC-C0-VAC-GEN / variant CH (horizon-localized C0 reading)",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN",
        "root_cause_theorem_ids": "D-002",
        "tex_key": "dafermos", "quote_regex": Q_DAF, "spotcheck_id": "SC-09-004",
        "spotcheck_quote_sha256": "93e51f2e1e23d89dd299b111d028b0a7e405b559a468d4212a3f92c5dae6b829",
        "class_binding_finding": ("Non-vacuum Einstein-Maxwell-scalar C0-falsity (Thm 1.2 / Cor 1.3) bound to frozen "
                                  "vacuum class AF-SCC-C0-VAC-GEN; F2b registers the horizon-localized C0 statement as "
                                  "variant CH and warns that binding it to the frozen class is a scope error in the "
                                  "other direction."),
    },
    {
        "correction_id": "CBC-09-002", "canonical_row_id": "SRC-056",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "new_class_mapping": tag("Einstein-Maxwell-scalar", "CH parent AF-SCC-C0-VAC-GEN"),
        "matter_model": "Einstein-Maxwell-(real)-scalar, spherical symmetry",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "parent AF-SCC-C0-VAC-GEN / variant CH (horizon-localized C0 reading)",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "root_cause_theorem_ids": "D-002;T-516",
        "tex_key": "dafermos", "quote_regex": Q_DAF, "spotcheck_id": "SC-09-004",
        "spotcheck_quote_sha256": "93e51f2e1e23d89dd299b111d028b0a7e405b559a468d4212a3f92c5dae6b829",
        "class_binding_finding": ("Same source as SRC-021 (arXiv mirror). Double leak: frozen C0 vacuum class plus "
                                  "AF-WCC-SCALAR-SPH although the model carries Maxwell charge and is not the massless "
                                  "neutral-scalar class."),
    },
    {
        "correction_id": "CBC-09-003", "canonical_row_id": "SRC-025",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN",
        "new_class_mapping": tag("Einstein-Maxwell-Klein-Gordon spherical"),
        "matter_model": "Einstein-Maxwell-Klein-Gordon (charged scalar), spherical symmetry",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": "D-003",
        "tex_key": "vdm", "quote_regex": Q_VDM, "spotcheck_id": "SC-09-002",
        "spotcheck_quote_sha256": "eda972b70431ce15eb4e4011fcd901abe1f6fb9e08b797f11858128d39350f7e",
        "class_binding_finding": ("Non-vacuum EMKG C^2-future-inextendibility bound to frozen vacuum class "
                                  "AF-SCC-C2-VAC-GEN; F2a l1_ledger_refs T-514 scope_use is 'different data class; "
                                  "do not transfer'."),
    },
    {
        "correction_id": "CBC-09-004", "canonical_row_id": "SRC-058",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN",
        "new_class_mapping": tag("Einstein-Maxwell-real-scalar spherical two-ended"),
        "matter_model": "Einstein-Maxwell-(real)-scalar, spherical symmetry, two-ended AF data",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": "D-007;T-510",
        "tex_key": "partII", "quote_regex": Q_PARTII, "spotcheck_id": "SC-09-003",
        "spotcheck_quote_sha256": "ac8b3dc0172b5d1fb94c99b7ffb8e5c218d3c4219c31a9c19e6d32e4c79dcca9",
        "class_binding_finding": ("Spherical EM-real-scalar two-ended C^2 result bound to frozen vacuum class; F2a "
                                  "strongest_caveat requires model-class support not to be transferred and "
                                  "does_not_imply clauses to travel."),
    },
    {
        "correction_id": "CBC-09-005", "canonical_row_id": "SRC-057",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN;AF-WCC-SCALAR-SPH",
        "new_class_mapping": tag("Einstein-Maxwell-real-scalar spherical two-ended"),
        "matter_model": "Einstein-Maxwell-(real)-scalar, spherical symmetry, two-ended AF data",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN;AF-WCC-SCALAR-SPH",
        "root_cause_theorem_ids": "D-007;T-510;T-514;T-516",
        "tex_key": "partI", "quote_regex": Q_PARTI, "spotcheck_id": "",
        "spotcheck_quote_sha256": "",
        "class_binding_finding": ("Luk-Oh Part I (companion of SRC-058, same detector hit as SRC-058 via T-514): "
                                  "spherical EM-real-scalar two-ended C^2 result carries the same double leak, frozen "
                                  "C2 vacuum class plus AF-WCC-SCALAR-SPH."),
    },
    {
        "correction_id": "CBC-09-006", "canonical_row_id": "SRC-024",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "new_class_mapping": tag("FLRW / Reissner-Nordstrom-Vaidya / Einstein-Maxwell-scalar",
                                 "LIP parent AF-SCC-C0-VAC-GEN"),
        "matter_model": "FLRW with matter; Reissner-Nordstrom-Vaidya; Einstein-Maxwell-scalar perturbations",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "parent AF-SCC-C0-VAC-GEN / variant LIP (C^{0,1}_loc extension class)",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": "D-005;T-304;T-506",
        "tex_key": "holonomy", "quote_regex": Q_HOL, "spotcheck_id": "",
        "spotcheck_quote_sha256": "",
        "class_binding_finding": ("Holonomy-singularity paper proves C^{0,1}_loc-inextendibility for FLRW, "
                                  "RN-Vaidya and EM-scalar perturbations; bound to C0 and C2 frozen vacuum classes. "
                                  "Two errors: non-vacuum matter model, and regularity is the registered LIP variant "
                                  "(C^{0,1}_loc), neither C0 nor C2."),
    },
    {
        "correction_id": "CBC-09-007", "canonical_row_id": "SRC-050",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN",
        "new_class_mapping": tag("Reissner-Nordstrom charged scalar / Einstein-Maxwell-real-scalar"),
        "matter_model": "linear scalar wave on charged Reissner-Nordstrom; conditional EM-real-scalar mass inflation",
        "scope_use": "do-not-transfer",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": "D-003;T-510",
        "tex_key": "scattering", "quote_regex": Q_SCAT, "spotcheck_id": "",
        "spotcheck_quote_sha256": "",
        "class_binding_finding": ("Scattering-map paper is set on charged Reissner-Nordstrom with a scalar field and "
                                  "gives a conditional EM-real-scalar mass-inflation result; bound to frozen vacuum "
                                  "class AF-SCC-C2-VAC-GEN."),
    },
]

FALSIFIER = (
    "Any of the following voids this correction: (a) ledger/citation_audit.csv no longer hashes to "
    f"{BOUND_LEDGER_SHA256}; (b) a re-fetch of the cited arXiv e-print shows the matter content is VAC "
    "(4D Einstein vacuum, Lambda=0) or shows a different theorem number for the bound row; (c) "
    "artifacts/formulation/VARIANT_REGISTRY.json no longer registers variant CH or LIP under parent_class "
    "AF-SCC-C0-VAC-GEN; (d) the lead's class_mapping derivation regenerates a frozen class id for these rows, "
    "in which case the theorem-layer root cause (D-002/D-003/D-005/D-007 class_ids) must be adjudicated first; "
    "(e) the canonical ledger is edited so a recorded old_class_mapping no longer matches, in which case this "
    "patch is void rather than partially applicable."
)

BARE_CLASS_RE = re.compile(r"\bAF-(?:WCC|SCC)-[A-Z0-9-]+\b")
TAG_RE = re.compile(
    r"^\(evidence/tag only; model-class: [^;]+;(?: variant [A-Z0-9]+ parent AF-[A-Z0-9-]+;)? "
    r"scope_use: do-not-transfer; no class-id binding\)$"
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return " ".join(s.split())


def load_rows() -> list[dict]:
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    checks: list[dict] = []

    def check(cid: str, desc: str, ok: bool, detail: str = "") -> None:
        checks.append({"check_id": cid, "description": desc,
                       "result": "PASS" if ok else "FAIL", "detail": detail})

    ledger_sha = sha256_file(LEDGER)
    check("V1", "canonical ledger hash equals the frozen L1 hash",
          ledger_sha == BOUND_LEDGER_SHA256 and ledger_sha.startswith(FROZEN_PREFIX), ledger_sha)

    rows = load_rows()
    by_id = {r["citation_id"]: r for r in rows}

    for c in CORRECTIONS:
        r = by_id.get(c["canonical_row_id"])
        check(f"V2-{c['correction_id']}", f"{c['canonical_row_id']} exists with recorded old class_mapping",
              r is not None and r.get("class_mapping") == c["old_class_mapping"],
              "" if r is None else f"found={r.get('class_mapping')!r}")

    # V3 matter model + quote presence in the locally re-fetched primary TeX
    quotes: dict[str, dict] = {}
    for c in CORRECTIONS:
        key = c["tex_key"]
        tex = ROOT / TEX[key]
        ok = tex.exists()
        detail = f"missing {tex}" if not ok else ""
        quote = ""
        if ok:
            txt = tex.read_text(encoding="utf-8", errors="replace")
            m = re.search(c["quote_regex"], txt)
            if m is None:
                ok, detail = False, "quote regex not found"
            else:
                quote = norm(m.group(0))
                detail = (f"sha256={sha256_file(tex)[:16]} line={txt[:m.start()].count(chr(10)) + 1} "
                          f"quote_sha256={hashlib.sha256(quote.encode()).hexdigest()[:16]}")
        quotes[c["correction_id"]] = {"quote_tex": quote, "quote_tex_sha256":
                                      hashlib.sha256(quote.encode()).hexdigest() if quote else ""}
        check(f"V3-{c['correction_id']}",
              f"{c['canonical_row_id']} primary TeX confirms a non-vacuum matter model (verbatim quote)",
              ok, detail)

    for c in CORRECTIONS:
        m = BARE_CLASS_RE.search(c["new_class_mapping"])
        bad = bool(m) and c["new_class_mapping"][max(0, m.start() - 7):m.start()] != "parent "
        check(f"V4-{c['correction_id']}",
              f"{c['canonical_row_id']} replacement has no class-id binding (only parent-class variant pointers)",
              not bad, "" if not bad else f"binding match {m.group(0)!r}")

    for c in CORRECTIONS:
        check(f"V5-{c['correction_id']}",
              f"{c['canonical_row_id']} replacement matches the evidence/tag-only pattern",
              bool(TAG_RE.match(c["new_class_mapping"])), c["new_class_mapping"])

    changed = [c["canonical_row_id"] for c in CORRECTIONS
               if c["new_class_mapping"] != by_id[c["canonical_row_id"]]["class_mapping"]]
    check("V6", "patch changes exactly the declared cells and no others",
          sorted(changed) == sorted(c["canonical_row_id"] for c in CORRECTIONS), f"changed={sorted(changed)}")

    applied = dict((r["citation_id"], r["class_mapping"]) for r in rows)
    for c in CORRECTIONS:
        applied[c["canonical_row_id"]] = c["new_class_mapping"]
    diff = [k for k in applied if applied[k] != by_id[k]["class_mapping"]]
    check("V6b", "applying the patch to the frozen snapshot changes exactly 7 of 97 cells",
          sorted(diff) == sorted(c["canonical_row_id"] for c in CORRECTIONS) and len(rows) == 97,
          f"rows={len(rows)} changed={len(diff)}")

    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    ch = [v for v in reg["variants"] if v.get("variant_id") == "CH"
          and v.get("parent_class") == "AF-SCC-C0-VAC-GEN"]
    lip = [v for v in reg["variants"] if v.get("variant_id") == "LIP"
           and v.get("parent_class") == "AF-SCC-C0-VAC-GEN"]
    check("V7", "VARIANT_REGISTRY registers variant CH under AF-SCC-C0-VAC-GEN", len(ch) == 1, f"found={len(ch)}")
    check("V7b", "VARIANT_REGISTRY registers variant LIP under AF-SCC-C0-VAC-GEN", len(lip) == 1, f"found={len(lip)}")
    check("V7c", "registry class_id_rule limits class_ids fields to the frozen four",
          "only the four frozen class ids" in reg.get("class_id_rule", ""), "")

    theo = {}
    with open(THEOREMS, encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            tid = d.get("theorem_id") or d.get("id")
            if tid:
                theo[tid] = d
    for c in CORRECTIONS:
        for tid in c["root_cause_theorem_ids"].split(";"):
            d = theo.get(tid)
            check(f"V8-{c['correction_id']}-{tid}", f"root-cause theorem {tid} resolves in ledger/theorems.jsonl",
                  d is not None, "" if d is None else f"class_ids={d.get('class_ids')}")

    spot = {}
    with open(SPOTCHECK, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            spot[r["spotcheck_id"]] = r
    for c in CORRECTIONS:
        if not c["spotcheck_id"]:
            continue
        r = spot.get(c["spotcheck_id"])
        ok = r is not None and r.get("quote_tex_sha256") == c["spotcheck_quote_sha256"]
        check(f"V9-{c['correction_id']}", f"{c['spotcheck_id']} recorded quote hash matches the spot-check ledger",
              ok, "" if r is None else f"spot={r.get('quote_tex_sha256', '')[:16]}")

    # archive provenance for every cited e-print
    archive_records = {}
    for c in CORRECTIONS:
        key = c["tex_key"]
        if key in archive_records:
            continue
        p = ROOT / ARCHIVE[key]
        archive_records[key] = {"path": ARCHIVE[key],
                                "sha256": sha256_file(p) if p.exists() else "",
                                "exists": p.exists()}
    check("V10", "every cited e-print archive is present with a recorded sha256",
          all(v["exists"] and len(v["sha256"]) == 64 for v in archive_records.values()),
          f"archives={len(archive_records)}")

    # emit patch
    cols = ["correction_id", "canonical_file", "canonical_file_sha256", "canonical_row_id",
            "old_class_mapping", "new_class_mapping", "matter_model", "scope_use",
            "registry_variant_pointer", "relevant_class_nonbinding", "root_cause_theorem_ids",
            "source_tex_file", "source_tex_sha256", "quote_tex", "quote_tex_sha256",
            "spotcheck_id", "spotcheck_quote_sha256", "evidence_basis", "class_binding_finding",
            "verification_status", "falsifier"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    for c in CORRECTIONS:
        row = dict(c)
        q = quotes[c["correction_id"]]
        row.update({
            "canonical_file": "ledger/citation_audit.csv",
            "canonical_file_sha256": BOUND_LEDGER_SHA256,
            "source_tex_file": TEX[c["tex_key"]],
            "source_tex_sha256": sha256_file(ROOT / TEX[c["tex_key"]]),
            "quote_tex": q["quote_tex"],
            "quote_tex_sha256": q["quote_tex_sha256"],
            "evidence_basis": EVIDENCE_BASIS,
            "verification_status": "unverified",
            "falsifier": FALSIFIER,
        })
        csv_rows.append({k: row.get(k, "") for k in cols})
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(csv_rows)

    with open(OUT_JSONL, "w", encoding="utf-8") as fh:
        for row in csv_rows:
            row = dict(row)
            row.update({
                "node_id": "L1", "group_id": "literature", "gate": "G-LIT",
                "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                "artifact_type": "class_binding_correction",
            })
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    OUT_MANIFEST.write_text(json.dumps({
        "manifest_id": "REFETCH-ADDENDUM-worker-009-classbinding",
        "note": "e-print archives added by the class-binding correction pass; the prior REFETCH_MANIFEST.json is unchanged",
        "archives": archive_records,
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    check("V11", "canonical ledger bytes unchanged by this tool", sha256_file(LEDGER) == BOUND_LEDGER_SHA256,
          sha256_file(LEDGER))

    all_pass = all(c["result"] == "PASS" for c in checks)
    verdict = {
        "verification_id": "CBC-09-VERIFY-20260912T0034",
        "node_id": "L1", "group_id": "literature", "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "worker": "worker-009",
        "inputs": {
            "canonical_ledger": {"path": "ledger/citation_audit.csv", "sha256": ledger_sha,
                                 "bytes": LEDGER.stat().st_size, "frozen_prefix": FROZEN_PREFIX},
            "variant_registry": {"path": "artifacts/formulation/VARIANT_REGISTRY.json",
                                 "sha256": sha256_file(REGISTRY)},
            "spotcheck_ledger": {"path": "ledger/citation_audit_scc_worker-009_spotcheck.csv",
                                 "sha256": sha256_file(SPOTCHECK)},
            "theorem_ledger": {"path": "ledger/theorems.jsonl", "sha256": sha256_file(THEOREMS)},
        },
        "refetch_archives": archive_records,
        "checks": checks,
        "counts": {"rows_checked": len(rows), "rows_corrected": len(CORRECTIONS),
                   "other_rows_changed": 0},
        "patch": {"csv": "ledger/citation_audit_scc_classbinding_worker-009.csv",
                  "jsonl": "ledger/citation_audit_scc_classbinding_worker-009.jsonl"},
        "canonical_write": "none - proposal only; lead-literature owns ledger/citation_audit.csv",
        "verification_status": "unverified",
        "worker_authority_note": "worker cannot set validation_status=passed; this is a revision proposal",
        "detector": ("canonical rows whose class_mapping contains a frozen class id while a used theorem's "
                     "does_not_imply records a matter-model/no-vacuum-transfer caveat; extended by manual "
                     "primary-source checks of every hit"),
        "falsifier": FALSIFIER,
        "all_checks_pass": all_pass,
    }
    OUT_VERIFY.parent.mkdir(parents=True, exist_ok=True)
    OUT_VERIFY.write_text(json.dumps(verdict, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "out_csv": str(OUT_CSV.relative_to(ROOT)), "out_csv_sha256": sha256_file(OUT_CSV),
        "out_jsonl": str(OUT_JSONL.relative_to(ROOT)), "out_jsonl_sha256": sha256_file(OUT_JSONL),
        "out_verify": str(OUT_VERIFY.relative_to(ROOT)), "out_verify_sha256": sha256_file(OUT_VERIFY),
        "out_manifest": str(OUT_MANIFEST.relative_to(ROOT)), "out_manifest_sha256": sha256_file(OUT_MANIFEST),
        "rows_corrected": len(CORRECTIONS), "all_checks_pass": all_pass,
        "failed": [c["check_id"] for c in checks if c["result"] != "PASS"],
    }, indent=1))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
