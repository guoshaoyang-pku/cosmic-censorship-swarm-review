#!/usr/bin/env python3
"""Independent verification of the L0 HF-01 repair proposal (worker-007).

Task W035-L0-HF01-VERIFY-01. Independent re-implementation: this script does NOT
import or execute the proposal generator for its primary checks (the generator is
executed only for the determinism check, into a throwaway directory).

Target: artifacts/worker-007/l0_hf01_artifact_refs/l0_hf01_proposal.json and
        artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl
Pinned canonical inputs: ledger/theorems.jsonl, ledger/citation_audit.csv,
        artifacts/literature/registry.jsonl.

Checks P1-P16 and adversarial controls M1-M7 are emitted to report.json /
controls.json.  Read-only with respect to every canonical artifact.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
FROZEN = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
LEDGER = "ledger/theorems.jsonl"
AUDIT = "ledger/citation_audit.csv"
REGISTRY = "artifacts/literature/registry.jsonl"
PROPOSAL = "artifacts/worker-007/l0_hf01_artifact_refs/l0_hf01_proposal.json"
PATCH = "artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl"
GENERATOR = "artifacts/worker-007/l0_hf01_artifact_refs/run_hf01_refs.py"
VERIFICATION = "artifacts/worker-007/l0_hf01_artifact_refs/verification.json"
RUBRIC = "evaluation_rubric.yaml"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> str:
    """Canonical serialization used by the proposal generator for round-trip checks."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def read_jsonl(path: Path):
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                out.append((n, json.loads(line), line.rstrip("\n")))
    return out


def read_csv_physical(path: Path):
    """Parse one CSV record per physical line; returns (fieldnames, {lineno: row}).

    The proposal locator convention is the physical file line number, so this
    parser refuses files whose records span lines (it would invalidate locators).
    """
    rows = {}
    header = None
    multi = []
    with path.open(encoding="utf-8", newline="") as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            recs = list(csv.reader([raw.rstrip("\r\n")]))
            if len(recs) != 1:
                multi.append(n)
                continue
            rec = recs[0]
            if header is None:
                header = rec
                continue
            if len(rec) != len(header):
                multi.append(n)
                continue
            rows[n] = dict(zip(header, rec))
    return header, rows, multi


def first_nonempty(d: dict, keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def norm(v):
    return "" if v is None else v


def load(root: Path):
    data = {"root": str(root)}
    data["canonical"] = read_jsonl(root / LEDGER)
    data["proposed"] = read_jsonl(root / PATCH)
    data["proposal"] = json.loads((root / PROPOSAL).read_text(encoding="utf-8"))
    data["verification"] = json.loads((root / VERIFICATION).read_text(encoding="utf-8"))
    data["audit_header"], data["audit_rows"], data["audit_multi"] = read_csv_physical(root / AUDIT)
    data["registry"] = read_jsonl(root / REGISTRY)
    data["hashes"] = {
        LEDGER: sha256_file(root / LEDGER),
        AUDIT: sha256_file(root / AUDIT),
        REGISTRY: sha256_file(root / REGISTRY),
        PROPOSAL: sha256_file(root / PROPOSAL),
        PATCH: sha256_file(root / PATCH),
        GENERATOR: sha256_file(root / GENERATOR),
        VERIFICATION: sha256_file(root / VERIFICATION),
        RUBRIC: sha256_file(root / RUBRIC),
    }
    rubric_lines = (root / RUBRIC).read_text(encoding="utf-8").splitlines()
    data["hf01_rubric_text"] = [
        {"line": i, "text": t} for i, t in enumerate(rubric_lines, 1)
        if "HF-01" in t or (170 <= i <= 178)
    ]
    return data


# --------------------------------------------------------------------------- checks

def checks(data) -> dict:
    """Return {check_id: {name, result, detail}} over the given in-memory snapshot."""
    out = {}

    def put(cid, name, ok, detail):
        out[cid] = {"id": cid, "name": name, "result": "pass" if ok else "fail", "detail": detail}

    canonical, proposed = data["canonical"], data["proposed"]
    proposal, verification = data["proposal"], data["verification"]
    hashes = data["hashes"]

    # P1 input pins recorded by the proposal must equal the measured bytes
    pins = {i["path"]: i["sha256"] for i in proposal.get("inputs", []) if "sha256" in i}
    pin_ok = all(hashes.get(p) == h for p, h in pins.items())
    put("P1", "proposal input pins equal measured bytes", pin_ok,
        {"pins": pins, "measured": {p: hashes.get(p) for p in pins}})

    # P2 proposal/patch hashes match the recorded verification record
    v_ok = (
        verification.get("proposal_sha256") == hashes[PROPOSAL]
        and proposal.get("patch", {}).get("patch_sha256") == hashes[PATCH]
        and verification.get("canonical_ledger_sha256") == hashes[LEDGER]
    )
    put("P2", "proposal/patch/canonical hashes match verification record", v_ok,
        {"verification.proposal_sha256": verification.get("proposal_sha256"),
         "measured.proposal": hashes[PROPOSAL],
         "verification.patch_sha256": proposal.get("patch", {}).get("patch_sha256"),
         "measured.patch": hashes[PATCH]})

    # P3 two ledgers have identical row count/order; 30 theorem + 32 non-theorem
    ids_c = [o.get("theorem_id") for _n, o, _r in canonical if o.get("theorem_id")]
    ids_p = [o.get("theorem_id") for _n, o, _r in proposed if o.get("theorem_id")]
    n_theorem = sum(1 for _n, o, _r in canonical if o.get("conclusion_type") == "theorem")
    p3 = (len(canonical) == len(proposed) and ids_c == ids_p and len(ids_c) == len(set(ids_c))
          and n_theorem == 30 and len(canonical) - n_theorem == 32)
    put("P3", "row count/order preserved; 30 theorem + 32 other rows", p3,
        {"canonical_rows": len(canonical), "proposed_rows": len(proposed),
         "theorem_rows": n_theorem, "id_order_equal": ids_c == ids_p,
         "unique_ids": len(set(ids_c))})

    # P4 patch is minimal: only artifact_refs added; other keys identical
    field_diffs, missing_ref_rows, changed = [], [], 0
    by_line_p = {n: o for n, o, _r in proposed}
    for n, o, _r in canonical:
        p = by_line_p.get(n)
        if p is None:
            field_diffs.append({"line": n, "reason": "row missing in patch"})
            continue
        stripped = {k: v for k, v in p.items() if k != "artifact_refs"}
        if stripped != o:
            field_diffs.append({"line": n, "theorem_id": o.get("theorem_id"),
                                "diff_keys": sorted(set(o) ^ set(stripped))})
        if p.get("artifact_refs") is not None:
            changed += 1
        if o.get("conclusion_type") == "theorem" and not p.get("artifact_refs"):
            missing_ref_rows.append(o.get("theorem_id"))
    put("P4", "patch minimal: artifact_refs only, all other keys identical", not field_diffs,
        {"changed_rows": changed, "field_diffs": field_diffs[:10]})

    # P4b patch refs equal the proposal's per-row refs
    prop_refs = {r["theorem_id"]: r["proposed_artifact_refs"] for r in proposal.get("rows", [])}
    ref_mismatch = []
    for n, o, _r in proposed:
        tid = o.get("theorem_id")
        if o.get("conclusion_type") == "theorem":
            if o.get("artifact_refs") != prop_refs.get(tid):
                ref_mismatch.append(tid)
    put("P4b", "patch artifact_refs equal proposal rows (by theorem_id)", not ref_mismatch,
        {"theorem_rows_checked": len(prop_refs), "mismatches": ref_mismatch[:10]})

    # P5 canonical file is in canonical (sort_keys) form; patch round-trip is byte-stable
    noncanon = [n for n, _o, raw in canonical if canon(_o) != raw]
    put("P5", "canonical ledger lines are in canonical form (round-trip byte-stable)",
        not noncanon, {"noncanonical_lines": noncanon[:10], "checked": len(canonical)})

    # P6 per-row ref coverage: exactly one ref per (source, evidence file) occurrence
    audit_by_id = {r["citation_id"]: (n, r) for n, r in data["audit_rows"].items()}
    reg_by_id = {r.get("source_id"): (n, r) for n, r, _raw in data["registry"]}
    coverage_bad, ref_total, unresolved_total = [], 0, 0
    prop_by_id = {r["theorem_id"]: r for r in proposal.get("rows", [])}
    for trow in proposal.get("rows", []):
        tid = trow["theorem_id"]
        canon_row = next((o for _n, o, _r in canonical if o.get("theorem_id") == tid), None)
        if canon_row is None:
            coverage_bad.append({"theorem_id": tid, "reason": "no canonical row"})
            continue
        want = Counter()
        for s in canon_row.get("source_ids") or []:
            if s in audit_by_id:
                want[s] += 1
            if s in reg_by_id:
                want[s] += 1
        got = Counter(r.get("source_id") for r in trow.get("proposed_artifact_refs") or [])
        if want != got:
            coverage_bad.append({"theorem_id": tid, "want": dict(want), "got": dict(got)})
        ref_total += sum(got.values())
        unresolved_total += len(trow.get("unresolved_source_ids") or [])
    put("P6", "ref coverage equals row source_ids x evidence-file presence", not coverage_bad,
        {"refs_total": ref_total, "unresolved_occurrences": unresolved_total,
         "bad_rows": coverage_bad[:5]})

    # P7 every ref path exists, no self-reference, hash matches on-disk bytes
    bad_refs = []
    for r in proposal.get("rows", []):
        for ref in r.get("proposed_artifact_refs") or []:
            path = ref.get("path")
            if not path:
                bad_refs.append({"theorem_id": r["theorem_id"], "reason": "empty path"})
            elif path == LEDGER:
                bad_refs.append({"theorem_id": r["theorem_id"], "reason": "self-reference"})
            elif not (data["root"] and Path(data["root"]).joinpath(path).exists()):
                bad_refs.append({"theorem_id": r["theorem_id"], "path": path, "reason": "missing"})
            else:
                measured = sha256_file(Path(data["root"]) / path)
                if measured != ref.get("sha256"):
                    bad_refs.append({"theorem_id": r["theorem_id"], "path": path,
                                     "reason": "hash mismatch",
                                     "want": ref.get("sha256"), "got": measured})
    put("P7", "all ref paths exist, hash-match, and are not self-referential",
        not bad_refs, {"bad_refs": bad_refs[:10], "refs_checked": ref_total})

    # P8 every line locator resolves to a record carrying the cited source_id
    loc_bad, loc_checked = [], 0
    root = Path(data["root"]) if data["root"] else None
    for r in proposal.get("rows", []):
        for ref in r.get("proposed_artifact_refs") or []:
            loc = ref.get("locator") or ""
            if ":" not in loc:
                loc_bad.append({"theorem_id": r["theorem_id"], "locator": loc, "reason": "no line"})
                continue
            path, line_s = loc.rsplit(":", 1)
            try:
                line = int(line_s)
            except ValueError:
                loc_bad.append({"theorem_id": r["theorem_id"], "locator": loc, "reason": "bad line"})
                continue
            if root is None:
                continue
            if path == AUDIT:
                row = data["audit_rows"].get(line)
                got_id = row.get("citation_id") if row else None
            elif path == REGISTRY:
                row = next((o for n, o, _raw in data["registry"] if n == line), None)
                got_id = row.get("source_id") if row else None
            else:
                loc_bad.append({"theorem_id": r["theorem_id"], "locator": loc, "reason": "unknown file"})
                continue
            loc_checked += 1
            if got_id != ref.get("source_id"):
                loc_bad.append({"theorem_id": r["theorem_id"], "locator": loc,
                                "want": ref.get("source_id"), "got": got_id})
    put("P8", "all line locators resolve to the cited source record", not loc_bad,
        {"locators_checked": loc_checked, "audit_records_span_lines": data["audit_multi"],
         "bad_locators": loc_bad[:10]})

    # P9 ref metadata faithfully copies the cited record
    meta_bad = []
    for r in proposal.get("rows", []):
        for ref in r.get("proposed_artifact_refs") or []:
            loc = ref.get("locator") or ""
            path, _, line_s = loc.rpartition(":")
            if path == AUDIT:
                row = data["audit_rows"].get(int(line_s)) if line_s.isdigit() else None
                if row is None:
                    continue
                want = {
                    "external_locator": first_nonempty(row, ("url", "doi", "arxiv_id")),
                    "bibkey": norm(row.get("bibkey")),
                    "verification_status": norm(row.get("status")),
                    "verdict": norm(row.get("verdict")),
                    "mirror_of": norm(row.get("mirror_of")),
                }
            elif path == REGISTRY:
                row = next((o for n, o, _raw in data["registry"] if n == int(line_s)), None) if line_s.isdigit() else None
                if row is None:
                    continue
                want = {
                    "external_locator": first_nonempty(row, ("url", "doi", "arxiv_id")),
                    "status": norm(row.get("status")),
                }
            else:
                continue
            for k, wv in want.items():
                got = ref.get(k)
                if norm(got) != norm(wv):
                    meta_bad.append({"theorem_id": r["theorem_id"], "locator": loc,
                                     "field": k, "want": wv, "got": got})
    put("P9", "ref metadata fields match the cited record", not meta_bad,
        {"mismatches": meta_bad[:10]})

    # P10 class ids (canonical and proposed) stay inside the frozen four
    leaks = []
    for label, rows in (("canonical", canonical), ("proposed", proposed)):
        for _n, o, _r in rows:
            for c in o.get("class_ids") or []:
                if c not in FROZEN:
                    leaks.append({"file": label, "theorem_id": o.get("theorem_id"), "class_id": c})
    put("P10", "all class_ids inside the frozen four (both files)", not leaks,
        {"leaks": leaks[:10], "frozen": list(FROZEN)})

    # P11 HF-01 detector reading: before 30 firing, after 0 firing
    before_fire, after_fire = [], []
    for trow in proposal.get("rows", []):
        tid = trow["theorem_id"]
        canon_row = next((o for _n, o, _r in canonical if o.get("theorem_id") == tid), None)
        prow = next((o for _n, o, _r in proposed if o.get("theorem_id") == tid), None)
        if canon_row is not None and canon_row.get("conclusion_type") == "theorem" and not canon_row.get("artifact_refs"):
            before_fire.append(tid)
        refs = (prow or {}).get("artifact_refs") or []
        resolved = bool(refs) and any(
            (root / r["path"]).exists() and sha256_file(root / r["path"]) == r.get("sha256")
            for r in refs
        )
        if not resolved:
            after_fire.append(tid)
    p11 = len(before_fire) == 30 and len(after_fire) == 0
    put("P11", "HF-01 (as read) fires on 30 rows before the patch and 0 after",
        p11, {"fires_before": len(before_fire), "unresolved_after": len(after_fire),
              "rubric_lines": data["hf01_rubric_text"],
              "conditional": "applicability of HF-01 to ledger rows is not adjudicated here"})

    # P12 residual: HF-14 self-certified acceptance is not addressed by this patch
    accepted_no_verdict = [
        {"theorem_id": o.get("theorem_id"), "status": o.get("status"),
         "supports_claim": o.get("supports_claim")}
        for _n, o, _r in canonical
        if (o.get("status") == "accepted" or o.get("supports_claim") is True)
        and not any(k in o for k in ("reviewer", "verdict", "artifact_refs"))
    ]
    added_verdict_fields = [
        o.get("theorem_id") for _n, o, _r in proposed
        if any(k in o for k in ("reviewer", "verdict"))
    ]
    put("P12", "HF-14 residual measured (not repaired by this patch)", True,
        {"rows_accepted_or_supporting_without_reviewer_verdict": len(accepted_no_verdict),
         "sample": accepted_no_verdict[:5],
         "reviewer_or_verdict_fields_added_by_patch": added_verdict_fields,
         "note": "recorded as remaining G-LIT/L0 work, outside the proposal's claim"})

    # P13 verification.json self-reported numbers recomputed
    canonical_by_id = {o.get("theorem_id"): o for _n, o, _r in canonical}
    digest_mismatch = 0
    for r in proposal.get("rows", []):
        core = {k: v for k, v in canonical_by_id[r["theorem_id"]].items() if k != "artifact_refs"}
        if r.get("row_content_sha256") != sha256_bytes(canon(core).encode()):
            digest_mismatch += 1
    recomputed = {
        "theorem_rows": n_theorem,
        "source_refs_total": ref_total,
        "unresolved_source_occurrences": unresolved_total,
        "class_leakage_rows": len(leaks),
        "patch_only_artifact_refs_added": changed,
        "patch_rows_untouched_identical": len(canonical) - changed,
        "patched_theorem_rows_missing_refs": len(missing_ref_rows),
        "row_digest_mismatches_against_patched": digest_mismatch,
        "refs_failing_on_disk_hash": len(bad_refs),
        "self_referential_refs": sum(1 for b in bad_refs if b.get("reason") == "self-reference"),
        "canonical_ledger_unchanged": hashes[LEDGER] if hashes[LEDGER] == verification.get("canonical_ledger_sha256") else None,
    }
    v = data["verification"]
    v_ok = all(v.get(k) == recomputed[k] for k in recomputed if k in v)
    put("P13", "verification.json self-reported metrics recomputed", v_ok,
        {"reported": {k: v.get(k) for k in recomputed}, "recomputed": recomputed})

    # P14 determinism: rerun the generator into a throwaway dir, compare bytes
    det = {"skipped": True}
    if data.get("root") and data.get("run_determinism", True):
        root = Path(data["root"])
        with tempfile.TemporaryDirectory() as td:
            out_p = Path(td) / "p.json"
            out_patch = Path(td) / "patch.jsonl"
            proc = subprocess.run(
                [sys.executable, str(root / GENERATOR), "--out", str(out_p),
                 "--patch", str(out_patch)],
                cwd=str(root), capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                det = {"skipped": False, "ok": False, "returncode": proc.returncode,
                       "stderr": proc.stderr[-800:]}
            else:
                new_patch = out_patch.read_bytes()
                new_prop = json.loads(out_p.read_text(encoding="utf-8"))
                disk_prop = copy.deepcopy(proposal)
                new_prop["patch"]["patch_path"] = disk_prop["patch"]["patch_path"]
                det = {"skipped": False, "ok": new_patch == (root / PATCH).read_bytes()
                       and new_prop == disk_prop,
                       "patch_bytes_equal": new_patch == (root / PATCH).read_bytes(),
                       "proposal_dict_equal": new_prop == disk_prop,
                       "regenerated_patch_sha256": sha256_bytes(new_patch)}
    put("P14", "generator is deterministic on the pinned inputs", det.get("ok") is True, det)

    # P15 canonical ledger hash unchanged after all checks
    first_hash = hashes[LEDGER]
    final_hash = sha256_file(Path(data["root"]) / LEDGER) if data.get("root") else first_hash
    put("P15", "canonical ledger byte-unchanged across verification", first_hash == final_hash,
        {"before": first_hash, "after": final_hash})

    # P16 proposal ledger_line anchors point at the right canonical rows
    anchor_bad = []
    for r in proposal.get("rows", []):
        n = r.get("ledger_line")
        canon_row = next((o for ln, o, _raw in canonical if ln == n), None)
        if canon_row is None or canon_row.get("theorem_id") != r.get("theorem_id"):
            anchor_bad.append({"theorem_id": r.get("theorem_id"), "ledger_line": n})
    put("P16", "proposal ledger_line anchors resolve to the right canonical rows",
        not anchor_bad, {"bad_anchors": anchor_bad[:10]})

    return out


# --------------------------------------------------------------------------- controls

def mutate(data, mutation: str):
    """Apply a mutation consistently to the proposal JSON and the proposed ledger."""
    d = copy.deepcopy(data)
    proposal = d["proposal"]
    prop_rows = proposal["rows"]
    patched = [o for _n, o, _r in d["proposed"] if o.get("conclusion_type") == "theorem"]

    def each_ref_pair():
        """Yield (proposal_row, patch_row) pairs that carry at least one ref."""
        for pr, patch_row in zip(prop_rows, patched):
            if pr.get("proposed_artifact_refs"):
                yield pr, patch_row

    if mutation == "M1_drop_refs":
        for r in prop_rows:
            r["proposed_artifact_refs"] = []
        for n, o, _r in d["proposed"]:
            if o.get("conclusion_type") == "theorem":
                o["artifact_refs"] = []
    elif mutation == "M2_corrupt_ref_hash":
        for pr, patch_row in each_ref_pair():
            pr["proposed_artifact_refs"][0]["sha256"] = "0" * 64
            patch_row["artifact_refs"][0]["sha256"] = "0" * 64
            break
    elif mutation == "M3_edit_non_theorem_row":
        for n, o, _r in d["proposed"]:
            if o.get("conclusion_type") != "theorem":
                o["statement_exact"] = str(o.get("statement_exact")) + " [mutant]"
                break
    elif mutation == "M4_class_leak":
        for n, o, _r in d["proposed"]:
            if o.get("conclusion_type") == "theorem" and o.get("class_ids"):
                o["class_ids"] = ["AF-SCC-OTHER-MODELS"]
                break
    elif mutation == "M5_bad_locator":
        for pr, patch_row in each_ref_pair():
            loc = pr["proposed_artifact_refs"][0]["locator"]
            path, _, line = loc.rpartition(":")
            new_loc = f"{path}:{int(line) + 5000}"
            pr["proposed_artifact_refs"][0]["locator"] = new_loc
            patch_row["artifact_refs"][0]["locator"] = new_loc
            break
    elif mutation == "M6_drop_row_field":
        for n, o, _r in d["proposed"]:
            if o.get("conclusion_type") == "theorem":
                o.pop("status", None)
                break
    elif mutation == "M7_extra_ref":
        for pr, patch_row in each_ref_pair():
            extra = copy.deepcopy(pr["proposed_artifact_refs"][0])
            extra["source_id"] = "SRC-999"
            pr["proposed_artifact_refs"].append(extra)
            patch_row["artifact_refs"].append(copy.deepcopy(extra))
            break
    else:
        raise ValueError(mutation)
    return d


CONTROL_EXPECT = {
    "M1_drop_refs": ("P6", "P11"),
    "M2_corrupt_ref_hash": ("P7",),
    "M3_edit_non_theorem_row": ("P4",),
    "M4_class_leak": ("P10",),
    "M5_bad_locator": ("P8",),
    "M6_drop_row_field": ("P4",),
    "M7_extra_ref": ("P6",),
}
# P13/P14 compare the in-memory snapshot against on-disk verification/generator
# artifacts; they are not invariant under in-memory mutation and are excluded
# from the control oracle (their own pass/fail is reported for the null input).
CONTROL_NONLOCAL = ("P13", "P14")


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(here.parents[2]))
    ap.add_argument("--out", default=str(here / "report.json"))
    ap.add_argument("--controls-out", default=str(here / "controls.json"))
    ap.add_argument("--no-determinism", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)

    data = load(root)
    data["run_determinism"] = not args.no_determinism
    result = checks(data)

    null_pass = all(c["result"] == "pass" for c in result.values())
    controls = [{"id": "null", "mutation": "none", "expected_fail": [],
                 "observed_fail": [cid for cid, c in result.items() if c["result"] == "fail"],
                 "result": "pass" if null_pass else "fail"}]
    for mut, expected in CONTROL_EXPECT.items():
        r = checks(mutate(data, mut))
        failed = sorted(cid for cid, c in r.items()
                        if c["result"] == "fail" and cid not in CONTROL_NONLOCAL)
        ok = all(e in failed for e in expected)
        controls.append({"id": mut, "mutation": mut, "expected_fail": list(expected),
                         "observed_fail": failed, "result": "pass" if ok else "fail"})

    hard = [cid for cid, c in result.items() if c["result"] == "fail"]
    report = {
        "artifact_type": "l0_hf01_independent_verification",
        "artifact_version": "1.0",
        "generated_by": "worker-035 (bounded execution worker)",
        "created_at": now(),
        "task": "W035-L0-HF01-VERIFY-01",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": list(FROZEN),
        "target": {
            "proposal": PROPOSAL,
            "patch": PATCH,
            "generator": GENERATOR,
            "claim_event_id": "w07-hf01-claim-repair-20260912T0018",
        },
        "pinned_inputs": data["hashes"],
        "checks": list(result.values()),
        "controls": controls,
        "summary": {
            "checks_total": len(result),
            "checks_pass": len(result) - len(hard),
            "checks_fail": hard,
            "controls_total": len(controls),
            "controls_pass": sum(1 for c in controls if c["result"] == "pass"),
            "hf01_fires_before": result["P11"]["detail"]["fires_before"],
            "hf01_fires_after": result["P11"]["detail"]["unresolved_after"],
            "refs_checked": result["P7"]["detail"]["refs_checked"],
            "locators_checked": result["P8"]["detail"]["locators_checked"],
            "canonical_ledger_sha256": data["hashes"][LEDGER],
            "proposed_ledger_sha256": data["hashes"][PATCH],
        },
        "verdict_recommendation": (
            "accept_conditional" if not hard else "revise"
        ),
        "conditional_scope": (
            "Verifies the proposal against the stated HF-01 detector reading. Whether HF-01 "
            "applies to ledger rows at all is an open adjudication (astra-lead-audit); this "
            "report does not decide it. HF-14 self-certified acceptance is NOT repaired by "
            "this patch and remains a G-LIT blocker."
        ),
        "falsifier": [
            "any theorem row without a non-empty, hash-resolving artifact_refs after applying the patch",
            "any locator that does not resolve to the cited source record at the pinned hash",
            "any ref metadata field differing from the cited record",
            "any class_id outside the frozen four in either ledger",
            "a non-deterministic rebuild of the patch, or any field other than artifact_refs changed",
            "the canonical ledger changing hash under verification",
        ],
        "non_claims": [
            "not a gate verdict; cannot pass G-LIT or move L0 status",
            "does not apply the patch or edit any canonical artifact",
            "does not upgrade verification_status or assert citation support",
            "does not adjudicate the applicability of HF-01 to ledger rows",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.controls_out).write_text(
        json.dumps({"generated_by": "worker-035", "created_at": now(), "controls": controls},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"checks: {len(result) - len(hard)}/{len(result)} pass; fail={hard}")
    print(f"controls: {sum(1 for c in controls if c['result'] == 'pass')}/{len(controls)} pass")
    print(f"report: {args.out}")
    return 0 if not hard and all(c["result"] == "pass" for c in controls) else 1


if __name__ == "__main__":
    sys.exit(main())
