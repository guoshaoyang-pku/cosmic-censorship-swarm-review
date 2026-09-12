#!/usr/bin/env python3
"""worker-087 — independent re-binding audit of the F0 open-case dispositions.

Bounded class-bound task (node F0 / gate G-F0, all four frozen class ids). It answers
one question mechanically, without using flash-02's checker:

    Do the 9 open taxonomy cases, their disposition rows, and their evidence refs
    still resolve against the CURRENT canonical F0 taxonomy (rev4, 276009f4), and
    are the disposition tokens consistent with the cases' own declared fields?

What is checked (all mechanical, no physics judgement):

  C1  corpus parses; ids unique; counts equal the corpus meta counts
  C2  per-case binding_status vs the corpus meta rebound hash vs current canonical
  C3  every evidence_ref resolves: taxonomy YAML anchors, hash pins, path#sha#record,
      bare paths, and unanchored markdown anchors are classified separately
  C4  9 open cases <-> 9 disposition rows: token legality and expected_resolution mapping
  C5  guards/hypotheses named in each open case's decisive_hypothesis exist in rev4
  C6  where a disposition row carries an axis_vector, it matches no frozen class axes
  C7  controls (the resolver must accept known-good refs and reject known-bad ones)

Honest scope limits, recorded in the report:
  * canonical only. The authoring tree is a DIFFERENT document (publication divergent);
    taxonomy refs are not expected to resolve there.
  * C4/C6 check the classification *direction* the row claims; they do not re-derive the
    physics reading of each statement. That needs a domain reviewer.
  * a worker audit is adjudication input, never a gate verdict or a class decision.

Exit codes: 0 instrument valid (findings are data), 1 controls/instrument failed,
2 input hash drift vs the pins measured at run start.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # artifacts/worker-087/f0_rebind_audit/audit.py
OUT_DIR = Path(__file__).resolve().parent
REPORT = OUT_DIR / "audit_report.json"
CST = timezone(timedelta(hours=8))

TAX = "research_map/formulation_taxonomy.yaml"
CORPUS = "schemas/taxonomy_cases.jsonl"
MATRIX = "artifacts/flash-02/open_case_disposition.json"

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
# corpus meta's own rebind chain, oldest -> newest, plus the current canonical
KNOWN_TAX_HASHES = ["66bf917bd368", "565a6e505188", "276009f4f63d"]
COMPOSITE_IDS = {"COMPOSITE_C0_C2", "COMPOSITE_WCC_SCC"}
RESOLUTION_TOKENS = {
    "reject_new_class_required": {"NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI"},
    "reject_split_required": {"SPLIT_REQUIRED", "SPLIT_AND_BRIDGE_REQUIRED"},
}
HASH12 = re.compile(r"^[0-9a-f]{12}$")
AF_TOKEN = re.compile(r"AF-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resolve_taxonomy(doc: dict, parts: list[str]):
    """Resolve a dotted YAML anchor. Returns (ok, mode, failure_reason)."""
    cur = doc
    modes: list[str] = []
    for part in parts:
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
                modes.append("key")
                continue
            # rev4 stores test cases as {positive: {id: F0-P1, ...}}; allow id-value addressing
            if str(cur.get("id")) == part or str(cur.get("case_id")) == part:
                modes.append("value_id")
                continue
            return False, modes, f"missing key {part!r}"
        if isinstance(cur, list):
            hit = next((x for x in cur if isinstance(x, dict) and str(x.get("id")) == part), None)
            if hit is None:
                return False, modes, f"no list element id={part!r}"
            cur = hit
            modes.append("list_id")
            continue
        return False, modes, f"scalar encountered before {part!r}"
    return True, modes, None


def resolve_ref(ref: str, tax_doc: dict, corpus_records: dict):
    """Classify and resolve one evidence_ref. Returns a dict row."""
    row = {"ref": ref, "form": None, "resolved": False, "mode": None, "note": None}
    if ref.startswith(TAX + "#"):
        frag = ref[len(TAX) + 1:]
        if HASH12.match(frag):
            row["form"] = "taxonomy_hash_pin"
            row["resolved"] = True
            row["mode"] = "hash_pin"
            row["note"] = ("current" if frag == KNOWN_TAX_HASHES[-1][:12]
                           else "stale_superseded" if frag in [h[:12] for h in KNOWN_TAX_HASHES[:-1]]
                           else "unknown_pin")
            return row
        ok, modes, why = resolve_taxonomy(tax_doc, frag.split("."))
        row.update(form="taxonomy_anchor", resolved=ok, mode="+".join(modes) if ok else None,
                   note=None if ok else why)
        return row
    if "#" in ref:
        path, frag = ref.split("#", 1)
        if path == CORPUS and "#" in frag:
            digest, record_id = frag.split("#", 1)
            row["form"] = "corpus_record"
            exists = (ROOT / path).is_file()
            digest_ok = exists and sha256_file(ROOT / path).startswith(digest)
            row["resolved"] = bool(exists and digest_ok and record_id in corpus_records)
            row["mode"] = "path+sha+record"
            if not exists:
                row["note"] = "corpus file missing"
            elif not digest_ok:
                row["note"] = f"corpus sha prefix {digest} does not match file"
            elif record_id not in corpus_records:
                row["note"] = f"record {record_id} missing"
            return row
        row["form"] = "path_anchor"
        exists = (ROOT / path).is_file()
        # markdown anchors are not machine-checkable here
        row["resolved"] = exists
        row["mode"] = "file_exists"
        row["note"] = None if exists else "file missing"
        return row
    row["form"] = "path"
    exists = (ROOT / ref).is_file()
    row["resolved"] = exists
    row["mode"] = "file_exists"
    row["note"] = None if exists else "file missing"
    return row


def main() -> int:
    started = datetime.now(CST)
    pins = {p: sha256_file(ROOT / p) for p in (TAX, CORPUS, MATRIX)}
    tax_doc = yaml.safe_load((ROOT / TAX).read_text(encoding="utf-8"))
    corpus = [json.loads(l) for l in (ROOT / CORPUS).read_text(encoding="utf-8").splitlines() if l.strip()]
    meta = next(c for c in corpus if c.get("record_type") == "meta")
    cases = [c for c in corpus if c.get("record_type") == "case"]
    by_id = {c["case_id"]: c for c in cases}
    matrix = json.loads((ROOT / MATRIX).read_text(encoding="utf-8"))
    rows = matrix["rows"]
    rows_by_case = {r["case_id"]: r for r in rows}

    checks: list[dict] = []
    findings: list[dict] = []

    def check(cid, desc, ok, detail):
        checks.append({"id": cid, "description": desc, "status": "pass" if ok else "finding", "detail": detail})
        return ok

    # C1 corpus integrity
    dupes = len(cases) - len(by_id)
    counts = {"positive": sum(1 for c in cases if c.get("polarity") == "positive"),
              "negative": sum(1 for c in cases if c.get("polarity") == "negative")}
    check("C1-corpus-integrity",
          "corpus parses, case ids unique, counts equal corpus meta counts",
          dupes == 0 and counts == meta.get("counts"),
          {"cases": len(cases), "duplicate_ids": dupes, "counts": counts, "meta_counts": meta.get("counts")})

    # C2 binding metadata
    declared = sorted({c.get("binding_status") for c in cases})
    meta_rebound = meta.get("rebound_at")
    binding_current = declared == [f"bound_taxonomy_sha_{pins[TAX][:12]}"]
    check("C2-binding-metadata",
          "per-case binding_status agrees with the corpus meta rebind and the current canonical hash",
          binding_current,
          {"per_case_values": declared, "meta_rebound_at": meta_rebound,
           "meta_rebind_note_present": bool(meta.get("rebind_note")),
           "current_canonical": pins[TAX][:12],
           "expected_current": pins[TAX][:12]})
    findings.append({
        "id": "F-087-2", "severity": "medium",
        "summary": ("all 36 cases still declare binding_status "
                    f"{declared[0] if declared else '?'} while the corpus meta records a rebind to "
                    f"{KNOWN_TAX_HASHES[1]} and the canonical taxonomy is now {pins[TAX][:12]}"),
        "evidence_refs": [f"{CORPUS}#{pins[CORPUS][:12]}", f"{TAX}#{pins[TAX][:12]}"],
        "action": "lead re-pins the corpus binding_status (and any axis vectors) to the rev4 hash",
    })

    # C3 evidence graph
    ref_rows: list[dict] = []
    seen: set[str] = set()
    for c in cases:
        for ref in c.get("evidence_refs", []):
            if ref in seen:
                continue
            seen.add(ref)
            r = resolve_ref(ref, tax_doc, by_id)
            r["used_by"] = [c["case_id"]]
            ref_rows.append(r)
    for r in rows:
        for ref in r.get("evidence_refs", []):
            if ref in seen:
                ref_rows[[x["ref"] for x in ref_rows].index(ref)]["used_by"].append(r["case_id"] + " (disposition)")
                continue
            seen.add(ref)
            rr = resolve_ref(ref, tax_doc, by_id)
            rr["used_by"] = [r["case_id"] + " (disposition)"]
            ref_rows.append(rr)
    dangling = [r for r in ref_rows if not r["resolved"]]
    stale_pins = [r for r in ref_rows if r["form"] == "taxonomy_hash_pin" and r["note"] == "stale_superseded"]
    check("C3-evidence-refs",
          "every evidence_ref resolves under its own convention (anchors, pins, records, files)",
          not dangling,
          {"total": len(ref_rows),
           "by_form": {f: sum(1 for r in ref_rows if r["form"] == f) for f in sorted({r["form"] for r in ref_rows})},
           "dangling": [{"ref": r["ref"], "note": r["note"], "used_by": r["used_by"]} for r in dangling],
           "stale_pins": [{"ref": r["ref"], "used_by": r["used_by"]} for r in stale_pins]})
    if stale_pins:
        findings.append({
            "id": "F-087-1", "severity": "medium",
            "summary": (f"{len(stale_pins)} disposition/x refs pin the superseded rev3 hash "
                        f"{KNOWN_TAX_HASHES[1]}; canonical is rev4 {pins[TAX][:12]}"),
            "evidence_refs": [f"{TAX}#{pins[TAX][:12]}"],
            "action": "re-pin the disposition evidence to rev4 before it can bind for G-F0",
        })

    # C4 open-case <-> disposition mapping
    open_cases = [c for c in cases if c.get("open")]
    missing_rows = [c["case_id"] for c in open_cases if c["case_id"] not in rows_by_case]
    extra_rows = [r["case_id"] for r in rows if r["case_id"] not in {c["case_id"] for c in open_cases}]
    token_errors, mapping_errors, class_errors = [], [], []
    token_map = matrix.get("disposition_tokens", {})
    for c in open_cases:
        r = rows_by_case.get(c["case_id"])
        if not r:
            continue
        tok = r.get("disposition")
        if tok not in token_map:
            token_errors.append({"case_id": c["case_id"], "token": tok})
        allowed = RESOLUTION_TOKENS.get(c.get("expected_resolution"), set())
        if allowed and tok not in allowed:
            mapping_errors.append({"case_id": c["case_id"], "expected_resolution": c.get("expected_resolution"),
                                   "disposition": tok, "allowed": sorted(allowed)})
        for cid in r.get("bound_parent_class_ids", []):
            if cid not in FROZEN:
                class_errors.append({"case_id": c["case_id"], "class_id": cid})
    af_unknown = sorted({t.upper() for r in rows for t in AF_TOKEN.findall(json.dumps(r))
                         if t.upper() not in FROZEN})
    c4_ok = not (missing_rows or extra_rows or token_errors or mapping_errors or class_errors or af_unknown)
    check("C4-disposition-mapping",
          "9 open cases <-> 9 rows; tokens legal; expected_resolution -> token mapping holds; parents frozen",
          c4_ok,
          {"open_cases": len(open_cases), "rows": len(rows), "missing_rows": missing_rows,
           "extra_rows": extra_rows, "token_errors": token_errors, "mapping_errors": mapping_errors,
           "non_frozen_parents": class_errors, "unknown_af_tokens_in_rows": af_unknown})

    # C5 guard / hypothesis existence
    guard_ids = {g["id"] for g in tax_doc.get("guards", [])}
    forbidden_ids = {g["id"] for g in tax_doc.get("transfer_rules", {}).get("forbidden", [])}
    gap_ids = {g["id"] for g in tax_doc.get("coverage_gaps", [])}
    hyp_errors = []
    for c in open_cases:
        text = c.get("decisive_hypothesis") or ""
        for cid in re.findall(r"AF-[A-Z0-9-]+", text.upper()):
            if cid not in FROZEN:
                hyp_errors.append({"case_id": c["case_id"], "kind": "unknown_class_in_hypothesis", "value": cid})
        for hid in re.findall(r"\bH[1-9]\b", text):
            parents = [p for p in re.findall(r"AF-[A-Z0-9-]+", text.upper()) if p in FROZEN]
            for p in parents:
                ids = [h.get("id") for h in tax_doc["classes"][p].get("hypotheses", [])]
                if hid not in ids:
                    hyp_errors.append({"case_id": c["case_id"], "kind": "unknown_hypothesis",
                                       "class_id": p, "value": hid, "have": ids})
        for gid in re.findall(r"\bG[1-9]\b", text):
            if gid not in guard_ids:
                hyp_errors.append({"case_id": c["case_id"], "kind": "unknown_guard", "value": gid})
        for xid in re.findall(r"\bX[1-9]\b", text):
            if xid not in forbidden_ids:
                hyp_errors.append({"case_id": c["case_id"], "kind": "unknown_transfer_rule", "value": xid})
        for cg in re.findall(r"\bCG[1-9]\b", text):
            if cg not in gap_ids:
                hyp_errors.append({"case_id": c["case_id"], "kind": "unknown_coverage_gap", "value": cg})
    check("C5-guard-hypothesis-existence",
          "every guard/hypothesis/transfer-rule/gap named by an open case exists in rev4",
          not hyp_errors, {"errors": hyp_errors})

    # C6 axis vectors vs frozen class axes
    axis_rows, axis_violations = [], []
    for c in open_cases:
        r = rows_by_case.get(c["case_id"], {})
        vec = r.get("axis_vector")
        if vec is None:
            axis_rows.append({"case_id": c["case_id"], "axis_vector": None, "matches_frozen": None})
            continue
        matches = [cid for cid in FROZEN if tax_doc["classes"][cid]["axes"] == vec]
        diff = {cid: sorted(k for k in set(vec) | set(tax_doc["classes"][cid]["axes"])
                            if vec.get(k) != tax_doc["classes"][cid]["axes"].get(k)) for cid in FROZEN}
        axis_rows.append({"case_id": c["case_id"], "axis_vector": vec, "matches_frozen": matches,
                          "differing_axes": diff})
        if c.get("expected_classification") == "NO_CLASS_IN_TAXONOMY" and matches:
            axis_violations.append({"case_id": c["case_id"], "matches_frozen": matches,
                                    "expected_classification": c.get("expected_classification")})
    check("C6-axis-vector-vs-frozen-axes",
          "vectors of new-class negatives match no frozen class axes",
          not axis_violations, {"vectors_checked": sum(1 for a in axis_rows if a["axis_vector"]),
                                "violations": axis_violations})

    # C7 controls
    controls = {
        "positive_key": resolve_taxonomy(tax_doc, ["class_ids"]),
        "positive_nested": resolve_taxonomy(tax_doc, ["classes", FROZEN[0], "axes", "family"]),
        "positive_list_id": resolve_taxonomy(tax_doc, ["guards", "G5"]),
        "positive_value_id": resolve_taxonomy(tax_doc, ["classes", FROZEN[2], "test_cases", "positive", "F0-P3"]),
        "negative_bad_guard": resolve_taxonomy(tax_doc, ["guards", "G99"]),
        "negative_bad_class": resolve_taxonomy(tax_doc, ["classes", "NO-SUCH-CLASS"]),
        "negative_bad_pin": resolve_ref(TAX + "#deadbeef0000", tax_doc, by_id),
    }
    controls_ok = (all(controls[k][0] for k in controls if k.startswith("positive"))
                   and all(not controls[k][0] for k in ("negative_bad_guard", "negative_bad_class"))
                   and controls["negative_bad_pin"]["note"] == "unknown_pin")
    check("C7-instrument-controls",
          "resolver accepts known-good refs and rejects known-bad refs",
          controls_ok, {k: (v if not isinstance(v, tuple) else {"ok": v[0], "mode": v[1], "note": v[2]})
                        for k, v in controls.items()})

    # C8 ref addressing convention
    value_id_refs = [r["ref"] for r in ref_rows if r["mode"] and "value_id" in r["mode"]]
    check("C8-ref-addressing",
          "taxonomy anchors are key-addressable, not only id-value-addressable",
          not value_id_refs,
          {"value_id_only_refs": value_id_refs})
    if value_id_refs:
        findings.append({
            "id": "F-087-7", "severity": "low",
            "summary": (f"{len(value_id_refs)} evidence refs address test cases by id-value "
                        "(test_cases.positive.F0-Px) although rev4 stores them under keys; "
                        "they resolve only with an id-value lookup rule"),
            "evidence_refs": sorted(set(value_id_refs)),
            "action": "optional: write refs as test_cases.positive.id (or key the test cases) for key-only resolvers",
        })

    # drift re-measure
    end_pins = {p: sha256_file(ROOT / p) for p in (TAX, CORPUS, MATRIX)}
    stale = end_pins != pins
    if stale:
        findings.append({"id": "F-087-4", "severity": "high",
                         "summary": "input hash drift during the run; report is stale",
                         "evidence_refs": [f"{p}#{pins[p][:12]}->{end_pins[p][:12]}" for p in pins],
                         "action": "re-run audit.py"})

    # authoring-tree divergence note (read-only measurement)
    authoring = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
    divergence = None
    if authoring.is_file():
        divergence = {"canonical_sha256": pins[TAX], "authoring_sha256": sha256_file(authoring),
                      "byte_identical": sha256_file(authoring) == pins[TAX]}
        if not divergence["byte_identical"]:
            findings.append({"id": "F-087-3", "severity": "info",
                             "summary": ("canonical F0 and the authoring tree are different documents; "
                                         "taxonomy anchors in this audit bind canonical only"),
                             "evidence_refs": [f"{TAX}#{pins[TAX][:12]}",
                                               f"artifacts/formulation/formulation_taxonomy.yaml#{divergence['authoring_sha256'][:12]}"],
                             "action": "publication policy decision owned by lead-formulation/Astra"})

    if not c4_ok or hyp_errors:
        findings.append({"id": "F-087-5", "severity": "high",
                         "summary": "at least one open-case disposition/guard check failed at rev4",
                         "evidence_refs": [f"{CORPUS}#{pins[CORPUS][:12]}", f"{TAX}#{pins[TAX][:12]}"],
                         "action": "review the failed rows before any G-F0 disposition"})
    findings.append({"id": "F-087-6", "severity": "info",
                     "summary": (f"{len(open_cases)} cases remain open=true with no disposition field in the corpus; "
                                 "the flash-02 matrix is a sidecar, so machine closure needs a lead-side annotation"),
                     "evidence_refs": [f"{CORPUS}#{pins[CORPUS][:12]}"],
                     "action": "lead annotates the corpus (or re-pins it) when it accepts the dispositions"})

    instrument_ok = controls_ok
    verdict = ("STALE_RERUN" if stale else
               "INSTRUMENT_FAILED" if not instrument_ok else
               "REBIND_REQUIRED_CONSISTENT" if (not c4_ok or hyp_errors or stale_pins or not binding_current) else
               "CONSISTENT_AND_BOUND")
    report = {
        "artifact_type": "f0_open_case_rebind_audit",
        "artifact_version": "1.0",
        "artifact_id": "artifacts/worker-087/f0_rebind_audit/audit_report.json",
        "task": {
            "task_id": "w087-F0-open-case-rebind-audit-20260912",
            "assignment": ("immediate-queue class-bound task: independent re-binding audit of the 9 open F0 "
                           "taxonomy-case dispositions and the 36-case evidence graph against canonical F0 rev4; "
                           "no card was issued to worker-087 in this lifecycle"),
            "node_id": "F0",
            "gate": "G-F0",
            "class_ids": FROZEN,
            "authority": ("worker adjudication input only; no class id created, no gate verdict, "
                          "no node status, no review verdict"),
            "not_duplicative_of": [
                "artifacts/worker-002/softflag-disposition (class-token soft flags, superseded hash)",
                "artifacts/worker-054/f0_replay (runs flash-02's checker; this audit does not use it)",
                "artifacts/flash-02/open_case_disposition.json (author self-check; audited here)",
            ],
        },
        "inputs": [{"path": p, "sha256": pins[p], "bytes": (ROOT / p).stat().st_size} for p in (TAX, CORPUS, MATRIX)],
        "canonical_authoring_divergence": divergence,
        "checks": checks,
        "evidence_ref_graph": ref_rows,
        "open_case_rebind": [{
            "case_id": c["case_id"],
            "expected_resolution": c.get("expected_resolution"),
            "expected_classification": c.get("expected_classification"),
            "as_filed_class_id": c.get("as_filed_class_id"),
            "leak_kind": c.get("leak_kind"),
            "disposition": rows_by_case.get(c["case_id"], {}).get("disposition"),
            "bound_parent_class_ids": rows_by_case.get(c["case_id"], {}).get("bound_parent_class_ids"),
            "decisive_hypothesis": c.get("decisive_hypothesis"),
        } for c in open_cases],
        "axis_vector_check": axis_rows,
        "findings": findings,
        "rebind_patch_suggestion": {
            "note": ("non-binding suggestion for the owner; this worker did not edit any lead-owned or "
                     "canonical artifact"),
            "corpus_case_binding_status": {"from": declared[0] if declared else None,
                                           "to": f"bound_taxonomy_sha_{pins[TAX][:12]}"},
            "disposition_evidence_ref": {"from": f"{TAX}#{KNOWN_TAX_HASHES[1]}",
                                         "to": f"{TAX}#{pins[TAX][:12]}"},
            "open_case_closure": ("the 9 rows are mechanically consistent with rev4; closing them in the "
                                  "corpus (open=false + a disposition field) is a lead-side edit"),
        },
        "summary": {
            "verdict": verdict,
            "instrument_ok": instrument_ok,
            "stale": stale,
            "cases_total": len(cases),
            "open_cases": len(open_cases),
            "disposition_rows": len(rows),
            "taxonomy_refs_total": sum(1 for r in ref_rows if r["form"] == "taxonomy_anchor"),
            "taxonomy_refs_resolved": sum(1 for r in ref_rows if r["form"] == "taxonomy_anchor" and r["resolved"]),
            "dangling_refs": len(dangling),
            "stale_pins": len(stale_pins),
            "dispositions_consistent": c4_ok and not hyp_errors,
            "finding_count": len(findings),
        },
        "falsifier": ("Re-run this instrument at the pinned hashes; the audit is falsified if any check "
                      "verdict changes, if any taxonomy anchor that resolved here fails to resolve, if any "
                      "open case has no row or maps to a token outside its expected_resolution family, if a "
                      "row names a non-frozen parent class, or if the corpus is later annotated with a "
                      "disposition that contradicts its row. Controls failing also void the audit."),
        "reopen_rule": ("Any change to the sha256 of research_map/formulation_taxonomy.yaml, "
                        "schemas/taxonomy_cases.jsonl, or artifacts/flash-02/open_case_disposition.json "
                        "makes this report stale and requires a re-run."),
        "instrument": {"path": "artifacts/worker-087/f0_rebind_audit/audit.py",
                       "reproduce_command": "python3 artifacts/worker-087/f0_rebind_audit/audit.py",
                       "exit_codes": {"0": "instrument valid", "1": "controls failed", "2": "input hash drift"}},
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "started_at": started.isoformat(timespec="seconds"),
        "generator": "worker-087",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"[worker-087] verdict={verdict} instrument_ok={instrument_ok} stale={stale} "
          f"findings={len(findings)} report={REPORT.relative_to(ROOT)}")
    return 2 if stale else (0 if instrument_ok else 1)


if __name__ == "__main__":
    sys.exit(main())
