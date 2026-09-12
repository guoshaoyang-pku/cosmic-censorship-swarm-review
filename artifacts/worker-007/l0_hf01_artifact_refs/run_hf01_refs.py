#!/usr/bin/env python3
"""L0 HF-01 repair proposal: class-bound `artifact_refs` for theorem rows.

Background. Reviewer flash-17's L0 verdict (reviews/L0-review-17.json, HF-01, critical)
fires on 30 rows of `ledger/theorems.jsonl` that carry `conclusion_type == "theorem"`
while the ledger has no `artifact_refs` field at all. The A0 rubric detector is:

    HF-01: claim.conclusion_type == theorem AND (no artifact_refs OR artifact
           missing OR hash mismatch)          (evaluation_rubric.yaml:171-174)

This script does NOT edit the canonical ledger. It measures pinned hashes, resolves
every theorem row's `source_ids` to records in the two ledger evidence files, and emits:

  * l0_hf01_proposal.json                         per-row, class-bound proposal
  * proposed/theorems.with_artifact_refs.jsonl    machine-applicable patch (proposal only)

Design note (self-reference). A ref of the form {path: ledger/theorems.jsonl,
sha256: <ledger hash>} placed inside that same ledger can never verify: writing the
ref changes the hash it pins. This proposal therefore uses only refs to artifacts
*outside* the amended file (ledger/citation_audit.csv, artifacts/literature/registry.jsonl),
whose hashes are stable across application, plus a per-row `row_content_sha256` computed
over the row with `artifact_refs` excluded. The digest is provenance for the claim-bearing
content, not a file hash, and survives application unchanged.

Every ref is a real on-disk artifact with a real sha256 and a line locator.
The proposal is deterministic and offline; run it twice and diff the outputs.

Controls (`--selftest`): a null (clean proposal -> 0 findings) and five mutants that
MUST each be caught (missing refs, file hash mismatch, missing artifact, class leakage,
row-digest mismatch). A control that does not fire is a script failure, not a finding.

Scope limits (non-claims) are in the emitted JSON and in README.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = "ledger/theorems.jsonl"
AUDIT = "ledger/citation_audit.csv"
REGISTRY = "artifacts/literature/registry.jsonl"
FROZEN = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
CLAIM_FIELDS_EXCLUDED_FROM_DIGEST = ("artifact_refs",)


def sha256_file(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def row_content_digest(row: dict) -> str:
    """Digest of the claim-bearing row content, excluding artifact_refs itself."""
    core = {k: v for k, v in row.items() if k not in CLAIM_FIELDS_EXCLUDED_FROM_DIGEST}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_jsonl(rel: str):
    """Return [(line_number, obj, raw_line)] for a JSONL file, 1-based."""
    out = []
    with open(ROOT / rel, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                out.append((n, json.loads(line), line.rstrip("\n")))
    return out


def load_csv(rel: str):
    with open(ROOT / rel, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        return rd.fieldnames, list(enumerate(rd, 1))


def build() -> dict:
    ledger_hash = sha256_file(LEDGER)
    audit_hash = sha256_file(AUDIT)
    registry_hash = sha256_file(REGISTRY)

    ledger_rows = load_jsonl(LEDGER)
    _hdr, audit_rows = load_csv(AUDIT)
    registry_rows = load_jsonl(REGISTRY)

    audit_by_id = {}
    for i, obj in audit_rows:
        audit_by_id.setdefault(obj["citation_id"], (i, obj))
    reg_by_id = {}
    for n, obj, _raw in registry_rows:
        reg_by_id.setdefault(obj.get("source_id"), (n, obj))

    rows_out = []
    n_theorem = 0
    n_unresolved = 0
    unresolved_sources = []
    class_leaks = []

    for lineno, row, _raw in ledger_rows:
        if row.get("conclusion_type") != "theorem":
            continue
        n_theorem += 1
        tid = row.get("theorem_id")
        class_ids = row.get("class_ids") or []
        if isinstance(class_ids, str):
            class_ids = [class_ids]
        bad_classes = [c for c in class_ids if c not in FROZEN]
        if bad_classes:
            class_leaks.append({"theorem_id": tid, "line": lineno, "class_ids": bad_classes})

        refs, row_unresolved = [], []
        for sid in row.get("source_ids") or []:
            a = audit_by_id.get(sid)
            r = reg_by_id.get(sid)
            if a is None and r is None:
                row_unresolved.append(sid)
                unresolved_sources.append({"theorem_id": tid, "line": lineno, "source_id": sid})
                continue
            if a is not None:
                refs.append({
                    "role": "citation_record",
                    "source_id": sid,
                    "path": AUDIT,
                    "sha256": audit_hash,
                    "locator": f"{AUDIT}:{a[0] + 1}",
                    "external_locator": a[1].get("url") or a[1].get("doi") or a[1].get("arxiv_id"),
                    "bibkey": a[1].get("bibkey"),
                    "verification_status": a[1].get("status"),
                    "verdict": a[1].get("verdict"),
                    "mirror_of": a[1].get("mirror_of"),
                    "supports": f"locator/provenance record for {sid}; does not by itself establish the row statement",
                })
            if r is not None:
                refs.append({
                    "role": "registry_record",
                    "source_id": sid,
                    "path": REGISTRY,
                    "sha256": registry_hash,
                    "locator": f"{REGISTRY}:{r[0]}",
                    "external_locator": r[1].get("url") or r[1].get("doi") or r[1].get("arxiv_id"),
                    "status": r[1].get("status"),
                    "supports": f"registry record for {sid}; locator and verification status only",
                })

        n_unresolved += len(row_unresolved)
        rows_out.append({
            "theorem_id": tid,
            "ledger_line": lineno,
            "class_ids": class_ids,
            "class_ids_all_frozen": not bad_classes,
            "status": row.get("status"),
            "verification_status": row.get("verification_status"),
            "evidence_level": row.get("evidence_level"),
            "row_content_sha256": row_content_digest(row),
            "row_content_digest_scope": "sha256 over the row with artifact_refs excluded; not a file hash",
            "proposed_artifact_refs": refs,
            "unresolved_source_ids": row_unresolved,
            "recommended_remedy": "A_add_artifact_refs",
            "remedy_B_rename_available": True,
            "residual_hf01_risk": "none" if not row_unresolved else "unresolved_source_record",
            "non_claims": [
                "artifact_refs are locator/provenance pins, not an upgrade of verification_status",
                "the row's statement is not re-verified here; verification_status=%s" % row.get("verification_status"),
                "row_content_sha256 covers the claim-bearing row content only, not a file",
                "this is not a reviewer verdict and does not move L0 or G-LIT",
            ],
        })

    return {
        "artifact_type": "l0_hf01_repair_proposal",
        "artifact_version": "1.1",
        "generated_by": "deepseek-flash-07 / worker-007 (bounded execution worker)",
        "task": "resolve flash-17 L0 HF-01 without editing the canonical ledger",
        "frozen_ids": list(FROZEN),
        "inputs": [
            {"path": LEDGER, "sha256": ledger_hash},
            {"path": AUDIT, "sha256": audit_hash},
            {"path": REGISTRY, "sha256": registry_hash},
            {"path": "reviews/L0-review-17.json"},
            {"path": "evaluation_rubric.yaml"},
        ],
        "detector": 'claim.conclusion_type == "theorem" AND (no artifact_refs OR artifact missing OR hash mismatch)',
        "summary": {
            "theorem_rows": n_theorem,
            "rows_with_artifact_refs_before": 0,
            "rows_with_artifact_refs_after": n_theorem,
            "source_refs_total": sum(len(r["proposed_artifact_refs"]) for r in rows_out),
            "unresolved_source_occurrences": n_unresolved,
            "class_leakage_rows": len(class_leaks),
            "class_leakage_detail": class_leaks,
            "remedy_A": "add the proposed artifact_refs to each theorem row (patch supplied)",
            "remedy_B": "rename conclusion_type -> mathematical_result_kind to reserve the claim vocabulary "
                        "(same effect on the detector; loses the theorem marker; no evidence added)",
            "recommendation": "A unless the lead prefers vocabulary separation; A preserves the theorem marker and adds provenance",
        },
        "rows": rows_out,
        "unresolved_sources": unresolved_sources,
        "application_procedure": [
            "1. review this proposal and proposed/theorems.with_artifact_refs.jsonl (proposal, not canonical)",
            "2. apply the patch only if the ledger is still at " + ledger_hash[:16],
            "3. no ref-hash refresh is needed: all refs point outside the amended file and row digests exclude artifact_refs",
            "4. record the new ledger sha256 in runtime/state/artifact_hashes.json and request re-review at the new hash",
        ],
        "falsifier": [
            "any theorem row left without artifact_refs after applying the patch -> HF-01 stands",
            "any cited locator that does not resolve to the source record at the pinned sha256 -> proposal fails",
            "any proposed class binding outside the frozen four -> HF-02 fires",
            "a row_content_sha256 that does not recompute from the canonical row -> proposal fails",
            "re-running build on the same inputs gives a different proposal (non-deterministic) -> proposal fails",
        ],
        "non_claims": [
            "this proposal does not edit ledger/theorems.jsonl; canonical hash unchanged at " + ledger_hash[:16],
            "it does not upgrade any verification_status; 29/30 theorem rows remain abstract-read",
            "it does not establish citation_support == 1.0 for the accepted set (G-LIT unmet item)",
            "it does not adjudicate duplicate/mirror clusters (13 citation rows carry mirror_of)",
            "it is not a gate verdict and cannot pass G-LIT",
        ],
    }


def check(proposal: dict, ledger_by_id: dict | None = None) -> list:
    """Check a proposal for HF-01/HF-02 violations against on-disk hashes."""
    if ledger_by_id is None:
        ledger_by_id = {r.get("theorem_id"): r for _n, r, _raw in load_jsonl(LEDGER)}
    findings = []
    for row in proposal["rows"]:
        refs = row.get("proposed_artifact_refs")
        tid = row.get("theorem_id")
        if not refs:
            findings.append({"kind": "hf01_missing_refs", "theorem_id": tid})
        for c in row.get("class_ids") or []:
            if c not in FROZEN:
                findings.append({"kind": "hf02_class_leakage", "theorem_id": tid, "class_id": c})
        for ref in refs or []:
            path = ref.get("path")
            if not path or not (ROOT / path).exists():
                findings.append({"kind": "hf01_artifact_missing", "theorem_id": tid, "path": path})
                continue
            if ref.get("sha256") and sha256_file(path) != ref["sha256"]:
                findings.append({"kind": "hf01_hash_mismatch", "theorem_id": tid, "path": path})
        canonical = ledger_by_id.get(tid)
        if canonical is not None and row.get("row_content_sha256") != row_content_digest(canonical):
            findings.append({"kind": "hf01_row_digest_mismatch", "theorem_id": tid})
    return findings


def selftest(proposal: dict) -> int:
    import copy
    failures = []
    ledger_by_id = {r.get("theorem_id"): r for _n, r, _raw in load_jsonl(LEDGER)}

    def expect(name, mut, want_kinds):
        f = check(mut, ledger_by_id)
        got = sorted({x["kind"] for x in f})
        ok = got == sorted(want_kinds)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: kinds={got} want={sorted(want_kinds)}")
        if not ok:
            failures.append(name)

    print("controls:")
    expect("null (clean proposal)", copy.deepcopy(proposal), [])
    m = copy.deepcopy(proposal)
    for r in m["rows"]:
        r["proposed_artifact_refs"] = []
    expect("mutant M1 (all refs dropped)", m, ["hf01_missing_refs"])

    m = copy.deepcopy(proposal)
    m["rows"][0]["proposed_artifact_refs"][0]["sha256"] = "0" * 64
    expect("mutant M2 (file ref hash corrupted)", m, ["hf01_hash_mismatch"])

    m = copy.deepcopy(proposal)
    m["rows"][0]["proposed_artifact_refs"][0]["path"] = "ledger/does_not_exist.jsonl"
    expect("mutant M3 (artifact missing)", m, ["hf01_artifact_missing"])

    m = copy.deepcopy(proposal)
    m["rows"][0]["class_ids"] = ["AF-SCC-OTHER-MODELS"]
    expect("mutant M4 (non-frozen class token)", m, ["hf02_class_leakage"])

    m = copy.deepcopy(proposal)
    m["rows"][0]["row_content_sha256"] = "0" * 64
    expect("mutant M5 (row content digest corrupted)", m, ["hf01_row_digest_mismatch"])

    print(f"selftest: {'PASS' if not failures else 'FAIL ' + ','.join(failures)}")
    return 1 if failures else 0


def write_patch(proposal: dict, out_path: Path) -> dict:
    """Rebuild the ledger with artifact_refs injected; never touches the canonical file."""
    by_line = {r["ledger_line"]: r["proposed_artifact_refs"] for r in proposal["rows"]}
    out_lines, changed, roundtrip_stable = [], 0, True
    for n, row, raw in load_jsonl(LEDGER):
        if n in by_line:
            row = dict(row)
            row["artifact_refs"] = by_line[n]
            changed += 1
            new = json.dumps(row, sort_keys=True, ensure_ascii=False)
        else:
            new = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if new != raw:
                roundtrip_stable = False
        out_lines.append(new)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return {
        "patch_path": str(out_path.relative_to(ROOT)) if str(out_path).startswith(str(ROOT)) else str(out_path),
        "rows_changed": changed,
        "rows_unchanged": len(out_lines) - changed,
        "untouched_rows_byte_identical_on_roundtrip": roundtrip_stable,
        "patch_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
    }


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(here / "l0_hf01_proposal.json"))
    ap.add_argument("--patch", default=str(here / "proposed" / "theorems.with_artifact_refs.jsonl"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    proposal = build()
    patch_meta = write_patch(proposal, Path(args.patch))
    proposal["patch"] = patch_meta
    findings = check(proposal)
    proposal["self_check_findings"] = findings
    Path(args.out).write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"theorem rows: {proposal['summary']['theorem_rows']}")
    print(f"source refs: {proposal['summary']['source_refs_total']}")
    print(f"unresolved source occurrences: {proposal['summary']['unresolved_source_occurrences']}")
    print(f"class leakage rows: {proposal['summary']['class_leakage_rows']}")
    print(f"patch: {patch_meta['patch_path']} changed={patch_meta['rows_changed']} sha256={patch_meta['patch_sha256'][:16]}")
    print(f"self-check findings on emitted proposal: {len(findings)}")
    if args.selftest:
        return selftest(proposal)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
