#!/usr/bin/env python3
"""Re-bind the SCC class-binding correction patch (worker-009) to the rev12 frozen
class contracts, then adversarially dry-run it against the frozen canonical ledger.

Bounded worker task, worker=009 (assignment asg-2026-09-11-L1-deepseek-flash-09-18).
Classes: AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN.  Gate: G-LIT.  Node: L1.
Group: literature.

Why this task exists (new since the patch was authored):
  The patch (ledger/citation_audit_scc_classbinding_worker-009.csv, 00:35) cites
  F2a T-514 / F2b variant CH / variant LIP as the reason its seven rows must not
  carry frozen vacuum class ids, but its verification record pins only the ledger,
  the theorem ledger and VARIANT_REGISTRY - NOT the schema bytes.  At 00:31:41 the
  canonical F2a/F2b/F1 schemas moved to revision 12 (5476a3f2 / 55d0a1ea / cce9c601)
  and artifacts/formulation/FROZEN.json revision 28 pins those same bytes.  A lead
  applying the patch needs the correction re-bound to the bytes that will actually
  be frozen, or a stale-anchor objection voids it.

What this tool does (all read-only against canonical state):
  1. binds every input by sha256 (canonical ledger, rev12 F2a/F2b/F1, FROZEN.json,
     VARIANT_REGISTRY.json, theorem ledger, patch CSV+JSONL);
  2. extracts the exact rev12 contract fields that forbid the seven bindings;
  3. re-checks each of the seven patch rows against the current canonical bytes;
  4. machine-applies the patch to an in-memory copy and writes the applied ledger to
     artifacts/worker-009/classbinding/dryrun_applied_citation_audit.csv;
  5. runs a documented detector (DET-REV12) over all 97 canonical rows and reports
     covered vs uncovered candidates honestly;
  6. runs adversarial probes, including a negative control showing the applier
     refuses a stale old_class_mapping.

It never writes ledger/citation_audit.csv.  Output is deterministic given
--verified-at; no wall clock is read inside.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_LEDGER = ROOT / "ledger" / "citation_audit.csv"
PATCH_CSV = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.csv"
PATCH_JSONL = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.jsonl"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
ENTRY_HASHES = ROOT / "entry_hashes.json"
OUT_RECORD = ROOT / "artifacts" / "worker-009" / "classbinding" / "verification_classbinding_rev12_worker-009.json"
OUT_DRYRUN = ROOT / "artifacts" / "worker-009" / "classbinding" / "dryrun_applied_citation_audit.csv"

BOUND_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
BOUND_THEOREMS_SHA256 = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
BOUND_PATCH_CSV_SHA256 = "47917e0e54bc447bab2143decdb22349cfea0214abea5a5619c125f55c1c70aa"
BOUND_PATCH_JSONL_SHA256 = "158d9875e5b0a742a1f85e390e20a9645779021463e47fb31ed2119c68c40c9d"
BOUND_REGISTRY_SHA256 = "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b"

FROZEN_CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
PATCHED_ROWS = ["SRC-021", "SRC-056", "SRC-025", "SRC-058", "SRC-057", "SRC-024", "SRC-050"]
EXPECTED_UNCOVERED = ["SRC-014", "SRC-029", "SRC-033", "SRC-048", "SRC-061"]
EXPECTED_ROOT_CAUSE_CLASS_IDS = {
    "D-002": ["AF-SCC-C0-VAC-GEN"],
    "D-003": ["AF-SCC-C2-VAC-GEN"],
    "D-005": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
    "D-007": ["AF-SCC-C2-VAC-GEN"],
    "T-514": [],
    "T-516": ["AF-WCC-SCALAR-SPH"],
}
# DET-REV12: a row is a candidate class-binding leak iff its class_mapping carries a
# frozen VACUUM class id (registered (parent, variant) pair pointers are stripped first)
# and one of its used records either (i) is named in a rev12 schema contract with
# scope_use "different data class; do not transfer", or
# (ii) records in does_not_imply that it says nothing about / does not settle / does
#     not transfer to the vacuum class, or
# (iii) carries that vacuum class id in its own class_ids while its assumptions are a
#     matter model (Einstein-Maxwell / scalar / Vaidya / FLRW / charged).
# A fourth, broader criterion (rows citing T-301/D-002 while binding the frozen C0 class)
# is reported separately as an ADVISORY: those rows are vacuum results sitting on the
# horizon-localized variant-CH reading, so the row-level derivation has to decide; they
# are not counted as leaks here.
VACUUM_CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
EXPLICIT_DO_NOT_TRANSFER = {"T-514", "T-520"}
NON_TRANSFER_RE = re.compile(
    r"says nothing directly about vacuum|does not settle the C\^?0 formulation"
    r"|does not imply C\^?2 SCC for vacuum|does not apply to vacuum"
    r"|does not transfer to AF vacuum|does not prove C\^?2 SCC in vacuum"
    r"|does not refute AF-SCC-C[02]-VAC-GEN|does not decide the C\^?2 formulation"
    r"|does not prove SCC failure in vacuum|Not the C\^?[02] formulation"
    r"|does not imply the same for vacuum",
    re.I,
)
MATTER_RE = re.compile(
    r"Einstein-Maxwell|scalar field|Vaidya|FLRW|charged|matter model", re.I
)
PAIR_RE = re.compile(r"variant\s+([A-Z0-9]+)\s+parent\s+(AF-[A-Z0-9-]+)")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def read_csv_rows(p: Path):
    raw = p.read_bytes()
    text = raw.decode("utf-8")
    lineterm = "\r\n" if "\r\n" in text else "\n"
    rows = list(csv.reader(io.StringIO(text, newline="")))
    return raw, lineterm, rows


def roundtrip(rows, lineterm: str) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=lineterm)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def read_theorems(p: Path) -> dict:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["theorem_id"]] = d
    return out


def contract_index(schema: dict):
    return {e["theorem_id"]: e for e in schema.get("l1_ledger_refs", [])}


def anti_scope_ids(schema: dict):
    return [
        e.get("class_id")
        for e in schema.get("anti_scope", {}).get("not_this_class", [])
        if e.get("class_id")
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verified-at", required=True)
    ap.add_argument("--out", default=str(OUT_RECORD))
    ap.add_argument("--dryrun-out", default=str(OUT_DRYRUN))
    args = ap.parse_args()

    checks: list[dict] = []

    def check(cid, desc, ok, detail=""):
        checks.append(
            {
                "check_id": cid,
                "description": desc,
                "result": "PASS" if ok else "FAIL",
                "detail": detail,
            }
        )

    def advisory(cid, desc, detail=""):
        checks.append(
            {
                "check_id": cid,
                "description": desc,
                "result": "ADVISORY",
                "detail": detail,
            }
        )

    inputs = {}
    for name, p in [
        ("canonical_ledger", CANONICAL_LEDGER),
        ("patch_csv", PATCH_CSV),
        ("patch_jsonl", PATCH_JSONL),
        ("theorem_ledger", THEOREMS),
        ("f2a_rev12", F2A),
        ("f2b_rev12", F2B),
        ("f1_rev12", F1),
        ("frozen", FROZEN),
        ("variant_registry", REGISTRY),
        ("entry_hashes", ENTRY_HASHES),
    ]:
        inputs[name] = {
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
        }

    # ---- input binding -------------------------------------------------
    check("B01", "canonical ledger hashes to the frozen L1 sha",
          inputs["canonical_ledger"]["sha256"] == BOUND_LEDGER_SHA256,
          inputs["canonical_ledger"]["sha256"])
    raw, lineterm, rows = read_csv_rows(CANONICAL_LEDGER)
    header = rows[0]
    data = rows[1:]
    check("B02", "canonical ledger shape is 97 rows x 25 columns",
          len(data) == 97 and len(header) == 25, f"rows={len(data)} cols={len(header)}")
    check("B03", "canonical ledger round-trips byte-identically through the CSV reader/writer",
          roundtrip(rows, lineterm) == raw, f"lineterm={'CRLF' if lineterm == chr(13)+chr(10) else 'LF'}")

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    fpins = {k: v.get("sha256") for k, v in frozen.get("files", {}).items()}
    for cid, key, path_rel in [
        ("B04", "f2a_rev12", "schemas/af_scc_c2_vacuum.yaml"),
        ("B05", "f2b_rev12", "schemas/af_scc_c0_vacuum.yaml"),
        ("B06", "f1_rev12", "schemas/af_wcc_vacuum.yaml"),
        ("B07", "variant_registry", "artifacts/formulation/VARIANT_REGISTRY.json"),
    ]:
        pinned = fpins.get(path_rel)
        check(cid, f"FROZEN.json pins the measured sha256 of {path_rel}",
              pinned == inputs[key]["sha256"], f"pin={pinned} measured={inputs[key]['sha256']}")
    check("B08", "FROZEN.json revision is >= 28 and records a rev12 delta",
          frozen.get("revision", 0) >= 28 and "rev12_delta" in frozen,
          f"revision={frozen.get('revision')}")
    check("B09", "theorem ledger hashes to the sha the patch verification pinned",
          inputs["theorem_ledger"]["sha256"] == BOUND_THEOREMS_SHA256,
          inputs["theorem_ledger"]["sha256"])
    check("B10", "patch CSV hashes to its declared sha",
          inputs["patch_csv"]["sha256"] == BOUND_PATCH_CSV_SHA256,
          inputs["patch_csv"]["sha256"])
    check("B11", "patch JSONL hashes to its declared sha",
          inputs["patch_jsonl"]["sha256"] == BOUND_PATCH_JSONL_SHA256,
          inputs["patch_jsonl"]["sha256"])
    check("B12", "VARIANT_REGISTRY hashes to the sha the patch verification pinned",
          inputs["variant_registry"]["sha256"] == BOUND_REGISTRY_SHA256,
          inputs["variant_registry"]["sha256"])

    # duplicate top-level key control on the rev12 schemas
    for cid, key, p in [("B13", "f2a_rev12", F2A), ("B14", "f2b_rev12", F2B)]:
        keys = [
            ln.split(":")[0]
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln and not ln[0].isspace() and ":" in ln
            and not ln.startswith("-") and not ln.startswith("#")
        ]
        check(cid, f"{p.name} has no duplicate top-level mapping keys",
              len(keys) == len(set(keys)), f"keys={len(keys)} unique={len(set(keys))}")

    f2a = yaml.safe_load(F2A.read_text(encoding="utf-8"))
    f2b = yaml.safe_load(F2B.read_text(encoding="utf-8"))
    f1 = yaml.safe_load(F1.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    theorems = read_theorems(THEOREMS)
    f2a_refs = contract_index(f2a)
    f2b_refs = contract_index(f2b)

    # ---- rev12 contract extraction -------------------------------------
    t514 = f2a_refs.get("T-514", {})
    t520 = f2a_refs.get("T-520", {})
    check("C01", "F2a rev12 T-514 scope_use forbids transfer",
          t514.get("scope_use") == "different data class; do not transfer",
          f"scope_use={t514.get('scope_use')!r} citation_status={t514.get('citation_status')!r}")
    check("C02", "F2a rev12 T-520 (Gowdy) scope_use forbids transfer",
          t520.get("scope_use") == "different data class; do not transfer",
          f"scope_use={t520.get('scope_use')!r}")
    caveat = f2a.get("known_status", {}).get("strongest_caveat", "")
    check("C03", "F2a rev12 strongest_caveat requires does_not_imply clauses to travel",
          "does_not_imply" in caveat and "travel" in caveat, caveat[:140])
    f2a_anti = anti_scope_ids(f2a)
    check("C04", "F2a rev12 anti_scope registers AF-WCC-SCALAR-SPH as not this class",
          "AF-WCC-SCALAR-SPH" in f2a_anti, f"anti_scope={f2a_anti}")
    check("C05", "F2a rev12 anti_scope registers AF-SCC-C0-VAC-GEN as not this class",
          "AF-SCC-C0-VAC-GEN" in f2a_anti, f"anti_scope={f2a_anti}")
    for cid, sch, name in [("C06", f2a, "F2a"), ("C07", f2b, "F2b"), ("C08", f1, "F1")]:
        dc = sch.get("data_class", {})
        check(cid, f"{name} rev12 data_class is 4D vacuum (matter none, Lambda 0, Ric=0)",
              dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
              and "Ric(g) = 0" in str(dc.get("equations")),
              f"matter={dc.get('matter')!r} lambda={dc.get('cosmological_constant')!r}")
    ch = f2b.get("class_identity_variants", {}).get("horizon_localized_variant", {})
    check("C09", "F2b rev12 variant CH is explicitly not this class",
          ch.get("is_this_class") is False and ch.get("status") == "registered_variant_not_written",
          f"is_this_class={ch.get('is_this_class')!r} status={ch.get('status')!r}")
    check("C10", "F2b rev12 variant CH is addressed_by D-002 (and T-301)",
          "D-002" in ch.get("addressed_by", []), f"addressed_by={ch.get('addressed_by')}")
    check("C11", "F2b rev12 variant CH says binding T-301 to the frozen class is a scope error",
          "scope error" in ch.get("why_separate", ""), ch.get("why_separate", "")[:140])
    f2b_anti = anti_scope_ids(f2b)
    check("C12", "F2b rev12 anti_scope registers AF-SCC-C2-VAC-GEN as not this class",
          "AF-SCC-C2-VAC-GEN" in f2b_anti, f"anti_scope={f2b_anti}")
    check("C13", "F2b rev12 anti_scope registers AF-WCC-SCALAR-SPH as not this class",
          "AF-WCC-SCALAR-SPH" in f2b_anti, f"anti_scope={f2b_anti}")
    d002 = f2b_refs.get("D-002", {})
    check("C14", "F2b rev12 D-002 scope_use is the horizon-localized reading",
          "horizon-localized" in d002.get("scope_use", ""), f"scope_use={d002.get('scope_use')!r}")
    rule = registry.get("class_id_rule", "")
    listed = set(re.findall(r"AF-[A-Z0-9-]+", rule))
    check("C15", "VARIANT_REGISTRY class_id_rule limits class_ids fields to the four frozen ids",
          listed == set(FROZEN_CLASS_IDS), f"listed={sorted(listed)}")
    reg_pairs = {(v["parent_class"], v["variant_id"]) for v in registry.get("variants", [])}
    check("C16", "VARIANT_REGISTRY registers variant CH under AF-SCC-C0-VAC-GEN",
          ("AF-SCC-C0-VAC-GEN", "CH") in reg_pairs, f"pairs={sorted(reg_pairs)}")
    check("C17", "VARIANT_REGISTRY registers variant LIP under AF-SCC-C0-VAC-GEN",
          ("AF-SCC-C0-VAC-GEN", "LIP") in reg_pairs, f"pairs={sorted(reg_pairs)}")
    check("C18", "VARIANT_REGISTRY rule text forbids citing a variant as a class",
          "parent_class" in registry.get("rule", "")
          and "variant_id" in registry.get("rule", "")
          and "leakage" in registry.get("rule", ""),
          registry.get("rule", "")[:160])

    # ---- patch row re-binding against current canonical bytes ----------
    rows_by_id = {r[0]: r for r in data}
    cm_idx = header.index("class_mapping")
    patch_rows = list(csv.DictReader(io.StringIO(PATCH_CSV.read_text(encoding="utf-8"), newline="")))
    patch_jsonl = {}
    for line in PATCH_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            patch_jsonl[d["correction_id"]] = d
    check("P01", "patch carries exactly 7 corrections with distinct canonical rows",
          len(patch_rows) == 7 and len({r["canonical_row_id"] for r in patch_rows}) == 7,
          f"n={len(patch_rows)} rows={[r['canonical_row_id'] for r in patch_rows]}")

    row_binding = []
    for r in patch_rows:
        cid = r["correction_id"]
        target = r["canonical_row_id"]
        row = rows_by_id.get(target)
        check(f"P-{cid}-1", f"{target} exists in the canonical ledger", row is not None, target)
        if row is None:
            continue
        check(f"P-{cid}-2", f"{target}: patch binds the current canonical sha",
              r["canonical_file_sha256"] == BOUND_LEDGER_SHA256, r["canonical_file_sha256"][:16])
        check(f"P-{cid}-3", f"{target}: recorded old_class_mapping equals the canonical cell",
              r["old_class_mapping"] == row[cm_idx],
              f"old={r['old_class_mapping']!r} canonical={row[cm_idx]!r}")
        new = r["new_class_mapping"]
        check(f"P-{cid}-4", f"{target}: replacement is an evidence/tag-only no-binding cell",
              new.startswith("(evidence/tag only") and "scope_use: do-not-transfer" in new
              and "no class-id binding" in new, new[:110])
        lead = new.split(";")[0]
        check(f"P-{cid}-5", f"{target}: no frozen class id in the leading binding position",
              not any(f in lead for f in FROZEN_CLASS_IDS), f"lead={lead!r}")
        pairs = PAIR_RE.findall(new)
        stripped = PAIR_RE.sub("", new)
        check(f"P-{cid}-6", f"{target}: every frozen-id occurrence in the cell is a registered pair pointer",
              not any(f in stripped for f in FROZEN_CLASS_IDS),
              f"pairs={pairs} residue_ok={not any(f in stripped for f in FROZEN_CLASS_IDS)}")
        pair_ok = all((p, v) in reg_pairs for v, p in pairs)
        check(f"P-{cid}-7", f"{target}: every (parent, variant) pair is registered",
              pair_ok and all(v not in FROZEN_CLASS_IDS for v, _ in pairs),
              f"pairs={pairs}")
        j = patch_jsonl.get(cid, {})
        check(f"P-{cid}-8", f"{target}: JSONL companion exists with matching old/new cell",
              j.get("canonical_row_id") == target
              and j.get("old_class_mapping") == r["old_class_mapping"]
              and j.get("new_class_mapping") == new,
              f"jsonl_old={j.get('old_class_mapping')!r}")
        check(f"P-{cid}-9", f"{target}: matter_model names a non-vacuum model",
              bool(r.get("matter_model")) and not re.fullmatch(r"\s*none\s*", r.get("matter_model", "")),
              r.get("matter_model"))
        row_binding.append({
            "correction_id": cid,
            "canonical_row_id": target,
            "old_class_mapping": r["old_class_mapping"],
            "new_class_mapping": new,
            "matter_model": r.get("matter_model"),
            "registry_variant_pointer": r.get("registry_variant_pointer"),
            "root_cause_theorem_ids": r.get("root_cause_theorem_ids"),
        })

    # ---- dry-run application -------------------------------------------
    def apply_patch(rows_in, corrections):
        """Return (rows_out, changed_cells, changed_rows).  Raises on stale old value."""
        out = [list(r) for r in rows_in]
        hdr = out[0]
        ci = hdr.index("class_mapping")
        ii = hdr.index("citation_id")
        changed = []
        for c in corrections:
            hit = [r for r in out[1:] if r[ii] == c["canonical_row_id"]]
            if len(hit) != 1:
                raise ValueError(f"row {c['canonical_row_id']} resolves {len(hit)} times")
            if hit[0][ci] != c["old_class_mapping"]:
                raise ValueError(
                    f"stale old_class_mapping for {c['canonical_row_id']}: "
                    f"{hit[0][ci]!r} != {c['old_class_mapping']!r}"
                )
            hit[0][ci] = c["new_class_mapping"]
            changed.append(c["canonical_row_id"])
        return out, [ci], changed

    applied, _, changed_rows = apply_patch(rows, patch_rows)
    diff_cells = sum(
        1
        for a, b in zip(rows, applied)
        for x, y in zip(a, b)
        if x != y
    )
    diff_rows = sum(1 for a, b in zip(rows, applied) if a != b)
    check("P-MIN1", "dry-run changes exactly 7 cells (one per corrected row)",
          diff_cells == 7, f"diff_cells={diff_cells}")
    check("P-MIN2", "dry-run changes exactly 7 rows",
          diff_rows == 7 and set(changed_rows) == set(PATCHED_ROWS),
          f"diff_rows={diff_rows} rows={sorted(changed_rows)}")
    check("P-MIN3", "dry-run leaves header and row/column order untouched",
          applied[0] == rows[0] and [r[0] for r in applied[1:]] == [r[0] for r in data],
          "header+order identical")
    applied_bytes = roundtrip(applied, lineterm)
    OUT_DRYRUN.write_bytes(applied_bytes)
    check("P-MIN4", "applied ledger re-reads as 97 rows x 25 columns",
          len(list(csv.reader(io.StringIO(applied_bytes.decode('utf-8'), newline="")))) == 98,
          f"bytes={len(applied_bytes)}")
    check("P-MIN5", "applied ledger hash differs from canonical (the patch really bites)",
          sha256_bytes(applied_bytes) != BOUND_LEDGER_SHA256,
          sha256_bytes(applied_bytes))

    # negative control: stale old value must be refused
    bogus = [dict(c) for c in patch_rows]
    bogus[0]["old_class_mapping"] = bogus[0]["old_class_mapping"] + ";AF-WCC-VAC-GEN"
    try:
        apply_patch(rows, bogus)
        refused = False
    except ValueError:
        refused = True
    check("P-NEG", "negative control: applier refuses a mutated old_class_mapping",
          refused, "ValueError raised" if refused else "NOT raised")

    # ---- detector over all 97 rows -------------------------------------
    def detect(canonical_rows):
        hits = []
        for r in canonical_rows:
            cm = r[cm_idx]
            cm_binding = PAIR_RE.sub("", cm)  # registered (parent, variant) pointers are not bindings
            vs = [v for v in VACUUM_CLASS_IDS if v in cm_binding]
            if not vs:
                continue
            reasons = []
            for t in [x for x in r[header.index("used_by_theorems")].split(";") if x]:
                rec = theorems.get(t)
                if not rec:
                    continue
                dnis = " ".join(rec.get("does_not_imply", []))
                if t in EXPLICIT_DO_NOT_TRANSFER:
                    reasons.append(f"{t}:rev12 contract scope_use=do-not-transfer")
                elif NON_TRANSFER_RE.search(dnis):
                    reasons.append(f"{t}:does_not_imply denies vacuum transfer")
                elif any(v in rec.get("class_ids", []) for v in vs) and MATTER_RE.search(
                    " ".join(rec.get("assumptions", []) + rec.get("does_not_imply", [])
                             + rec.get("scope_caveats", []))
                ):
                    reasons.append(f"{t}:matter-model record carries {vs[0]}")
            if reasons:
                hits.append({
                    "citation_id": r[0],
                    "class_mapping": cm,
                    "used_by_theorems": r[header.index("used_by_theorems")],
                    "reasons": reasons,
                })
        return hits

    hits = detect(data)
    hit_ids = [h["citation_id"] for h in hits]
    covered = [h for h in hits if h["citation_id"] in PATCHED_ROWS]
    uncovered = [h for h in hits if h["citation_id"] not in PATCHED_ROWS]
    check("D01", "DET-REV12 finds every one of the 7 patched rows",
          set(PATCHED_ROWS).issubset(set(hit_ids)), f"hits={hit_ids}")
    check("D02", "DET-REV12 uncovered candidate set matches the recorded snapshot",
          sorted(h["citation_id"] for h in uncovered) == sorted(EXPECTED_UNCOVERED),
          f"uncovered={sorted(h['citation_id'] for h in uncovered)}")
    n_frozen_rows = sum(1 for r in data if any(f in r[cm_idx] for f in FROZEN_CLASS_IDS))
    check("D03", "null control: rows with frozen ids but no detector reason remain untouched",
          n_frozen_rows - len(hits) == 44,
          f"frozen_rows={n_frozen_rows} candidates={len(hits)} control={n_frozen_rows - len(hits)}")
    post_hits = [h for h in detect(applied[1:]) if h["citation_id"] in PATCHED_ROWS]
    check("D04", "post-apply detector finds zero remaining hits among the 7 patched rows",
          post_hits == [], f"remaining={[h['citation_id'] for h in post_hits]}")
    post_other = sorted(h["citation_id"] for h in detect(applied[1:]) if h["citation_id"] not in PATCHED_ROWS)
    check("D05", "post-apply detector leaves the uncovered candidate set unchanged",
          post_other == sorted(EXPECTED_UNCOVERED), f"other={post_other}")

    # ---- adversarial probes --------------------------------------------
    transfer_re = re.compile(r"may transfer|same data class|transferable|does transfer", re.I)
    hits_txt = []
    for p in [F2A, F2B, F1]:
        txt = p.read_text(encoding="utf-8")
        for m in transfer_re.finditer(txt):
            hits_txt.append(f"{p.name}:{m.group(0)}")
    check("F01", "no rev12 schema field authorizes transfer of a model-class result",
          hits_txt == [], f"hits={hits_txt}")
    f2b_text = F2B.read_text(encoding="utf-8")
    if "LIP" not in f2b_text:
        advisory("F02", "F2b rev12 text never names variant LIP; the SRC-024 LIP pointer "
                        "resolves only through VARIANT_REGISTRY.json (pinned in FROZEN.json)",
                "F2b contains 0 'LIP' tokens; F2b anti_scope names H2LOC and DISTRIBUTIONAL only")
    else:
        check("F02", "F2b rev12 text names variant LIP", True, "LIP present")
    check("F03", "SRC-024 uses the registry-registered LIP pair form",
          any(c["canonical_row_id"] == "SRC-024" and "variant LIP parent AF-SCC-C0-VAC-GEN" in c["new_class_mapping"]
              for c in patch_rows), "pair=(AF-SCC-C0-VAC-GEN, LIP)")
    check("F04", "patch falsifier condition (a) holds: canonical ledger sha unchanged",
          inputs["canonical_ledger"]["sha256"] == BOUND_LEDGER_SHA256, "frozen sha holds")
    check("F05", "patch falsifier condition (c) holds: registry still has CH and LIP under the C0 parent",
          ("AF-SCC-C0-VAC-GEN", "CH") in reg_pairs and ("AF-SCC-C0-VAC-GEN", "LIP") in reg_pairs,
          "both pairs registered")
    check("F06", "patch falsifier condition (e) holds: all recorded old_class_mapping cells still match",
          all(r["old_class_mapping"] == rows_by_id[r["canonical_row_id"]][cm_idx] for r in patch_rows),
          "7/7 match")
    missing_used = []
    for c in patch_rows:
        row = rows_by_id[c["canonical_row_id"]]
        for t in [x for x in row[header.index("used_by_theorems")].split(";") if x]:
            if t not in theorems:
                missing_used.append(f"{c['canonical_row_id']}:{t}")
    check("F07", "every theorem used by the 7 rows resolves in the frozen theorem ledger",
          missing_used == [], f"missing={missing_used}")
    check("F08", "patch verification pins only ledger+theorem+registry, not schema bytes "
                 "(this record closes that gap)",
          "f2a_rev12" not in json.loads(
              (ROOT / "artifacts/worker-009/classbinding/verification_classbinding_worker-009.json")
              .read_text(encoding="utf-8")).get("inputs", {}),
          "confirmed: previous record had no schema-byte inputs")
    # root-cause records at the frozen theorem hash
    rc = {}
    for tid, expected in EXPECTED_ROOT_CAUSE_CLASS_IDS.items():
        rec = theorems.get(tid, {})
        got = rec.get("class_ids", [])
        rc[tid] = {"resolved": bool(rec), "class_ids": got, "expected": expected,
                   "matches_patch_basis": got == expected}
    check("R01", "all six declared root-cause records resolve at the frozen theorem hash",
          all(v["resolved"] for v in rc.values()), f"resolved={sorted(k for k, v in rc.items() if v['resolved'])}")
    check("R02", "every root-cause class_ids list matches the patch's declared basis",
          all(v["matches_patch_basis"] for v in rc.values()),
          json.dumps({k: v["class_ids"] for k, v in rc.items()}))
    check("R03", "root cause still present: >=1 declared record carries a frozen class id",
          any(any(f in v["class_ids"] for f in FROZEN_CLASS_IDS) for v in rc.values()),
          "root cause persists at the frozen theorem hash; the patch is still required")
    check("R04", "D-002 root cause is the variant-CH scope error, not a C0-class theorem",
          rc["D-002"]["class_ids"] == ["AF-SCC-C0-VAC-GEN"] and ch.get("is_this_class") is False,
          "D-002 carries the frozen C0 id while F2b assigns its reading to variant CH")

    # broader variant-CH registration surface (advisory, not counted as leaks)
    variant_ch_rows = sorted(
        r[0] for r in data
        if "AF-SCC-C0-VAC-GEN" in PAIR_RE.sub("", r[cm_idx])
        and "T-301" in r[header.index("used_by_theorems")].split(";")
    )
    advisory("F10", "rows citing T-301 while binding the frozen C0 class are variant-CH "
                    "registration candidates per F2b why_separate (vacuum results; the lead's "
                    "derivation decides; not counted as leaks by DET-REV12)",
            f"rows={variant_ch_rows}")

    # stale entry_hashes advisory
    eh = json.loads(ENTRY_HASHES.read_text(encoding="utf-8"))
    stale = {k: (eh.get(k), inputs["f2a_rev12" if "c2" in k else "f2b_rev12"]["sha256"])
             for k in ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
             if eh.get(k) and eh.get(k) != inputs["f2a_rev12" if "c2" in k else "f2b_rev12"]["sha256"]}
    if stale:
        advisory("F09", "entry_hashes.json still pins pre-rev12 SCC schema hashes "
                        "(FROZEN.json rev28 pins the rev12 bytes); refresh before using it as a freeze source",
                json.dumps(stale))
    else:
        check("F09", "entry_hashes.json agrees with rev12 schema bytes", True, "")

    # ---- record --------------------------------------------------------
    n_pass = sum(1 for c in checks if c["result"] == "PASS")
    n_fail = sum(1 for c in checks if c["result"] == "FAIL")
    n_adv = sum(1 for c in checks if c["result"] == "ADVISORY")
    record = {
        "verification_id": "CBC-09-REV12-BIND-20260912T0043",
        "worker": "worker-009",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-LIT",
        "gate_ids": ["G-LIT"],
        "created_at": args.verified_at,
        "verified_at": args.verified_at,
        "inputs": inputs,
        "rev12_contract_bindings": {
            "f2a_T-514_scope_use": t514.get("scope_use"),
            "f2a_T-520_scope_use": t520.get("scope_use"),
            "f2a_strongest_caveat": caveat,
            "f2a_anti_scope_not_this_class": f2a_anti,
            "f2a_data_class_matter": f2a.get("data_class", {}).get("matter"),
            "f2b_variant_CH": {k: ch.get(k) for k in ["class_id", "status", "is_this_class",
                                                       "statement", "addressed_by", "relation",
                                                       "why_separate"]},
            "f2b_anti_scope_not_this_class": f2b_anti,
            "f2b_D-002_scope_use": d002.get("scope_use"),
            "f2b_data_class_matter": f2b.get("data_class", {}).get("matter"),
            "registry_class_id_rule": rule,
            "registry_rule": registry.get("rule"),
            "registry_pairs_present": sorted(f"{p}/{v}" for p, v in reg_pairs
                                             if v in ("CH", "LIP")),
            "frozen_revision": frozen.get("revision"),
        },
        "patch_binding": {
            "patch_csv": "ledger/citation_audit_scc_classbinding_worker-009.csv",
            "patch_csv_sha256": inputs["patch_csv"]["sha256"],
            "bound_canonical_sha256": BOUND_LEDGER_SHA256,
            "rows": row_binding,
            "dryrun_applied": {
                "path": str(OUT_DRYRUN.relative_to(ROOT)),
                "sha256": sha256_bytes(applied_bytes),
                "bytes": len(applied_bytes),
                "changed_cells": diff_cells,
                "changed_rows": sorted(changed_rows),
                "canonical_rows": len(data),
                "canonical_columns": len(header),
            },
            "negative_control": "applier raises ValueError on a mutated old_class_mapping",
        },
        "detector": {
            "id": "DET-REV12",
            "criterion": ("row class_mapping carries a frozen VACUUM class id (pair pointers stripped) "
                          "and a used record (i) is T-514/T-520 with rev12 scope_use 'different data "
                          "class; do not transfer', or (ii) has a does_not_imply sentence denying "
                          "vacuum transfer, or (iii) carries that vacuum id while its assumptions are "
                          "a matter model"),
            "candidate_rows": len(hits),
            "covered_by_patch": sorted(h["citation_id"] for h in covered),
            "uncovered_candidates": uncovered,
            "uncovered_promotion_requirement": (
                "primary-source re-fetch + model-class determination + rev12 contract scope_use; "
                "the listed rows are candidates only, not verified leaks, and are NOT patched here"),
            "control_rows_without_reason": n_frozen_rows - len(hits),
            "post_apply_hits_in_patched_rows": len(post_hits),
            "post_apply_uncovered_candidates": post_other,
            "variant_ch_registration_candidates_advisory": variant_ch_rows,
        },
        "root_cause_at_frozen_theorem_hash": rc,
        "adversarial_probes": {
            "authorizing_transfer_phrases": hits_txt,
            "schema_bytes_were_not_pinned_by_prior_record": True,
            "out_of_band_falsifier_conditions": [
                "(b) a re-fetch showing a cited source is vacuum or a different theorem number",
                "(d) the lead's class_mapping derivation regenerating a frozen class id",
            ],
        },
        "checks": checks,
        "counts": {"pass": n_pass, "fail": n_fail, "advisory": n_adv, "total": len(checks)},
        "all_checks_pass": n_fail == 0,
        "canonical_write": "none - proposal only; lead-literature owns ledger/citation_audit.csv",
        "dryrun_write": str(OUT_DRYRUN.relative_to(ROOT)),
        "falsifier": (
            "This rev12 re-binding is void if any of the following holds: (a) "
            "ledger/citation_audit.csv no longer hashes to "
            "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; "
            "(b) schemas/af_scc_c2_vacuum.yaml or schemas/af_scc_c0_vacuum.yaml moves off "
            "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce / "
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6, or "
            "VARIANT_REGISTRY.json moves off "
            "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b; "
            "(c) any recorded old_class_mapping no longer equals the canonical cell; "
            "(d) the F2a T-514 scope_use or the F2b variant-CH registration changes so the "
            "seven rows become transferable; (e) ledger/theorems.jsonl moves off "
            "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28, in which case "
            "the root-cause section is void."
        ),
        "next_falsifier": (
            "Promote or drop the uncovered candidates "
            f"({', '.join(h['citation_id'] for h in uncovered)}) "
            "by primary-source re-fetch at the same method as the seven verified rows; or show "
            "that a candidate's cited source is vacuum, which drops it. Separately: the lead "
            "applies the 7-row patch to the canonical ledger and regenerates from the theorem "
            "layer; a frozen class id reappearing on any of the seven voids the derivation fix."
        ),
        "worker_authority_note": (
            "worker cannot set status=done, validation_status=passed, or a gate verdict; this is "
            "a re-verification record and a revision proposal only"
        ),
    }
    out = Path(args.out)
    out.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "record": str(out.relative_to(ROOT)),
        "record_sha256": sha256_file(out),
        "dryrun": str(OUT_DRYRUN.relative_to(ROOT)),
        "dryrun_sha256": sha256_bytes(applied_bytes),
        "checks": {"pass": n_pass, "fail": n_fail, "advisory": n_adv},
        "uncovered_candidates": [h["citation_id"] for h in uncovered],
    }, indent=1, sort_keys=True))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
