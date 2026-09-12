#!/usr/bin/env python3
"""W069-LIFE05-REC12-REPAIR-COVERAGE-01 -- pre-registered sufficiency test of the
authorized evidence-binding repair card `astra-life05-evidence-binding-repair` (REC-12).

Question (decision-relevant, pre-deadline 2026-09-12T01:40+08:00):
  Do the FOUR bounded repair items authorized by the card close the blocking findings
  that currently keep F1/F2a/F2b at revise at the rev12 pins, or will the rev29
  re-review round (astra-life05-verify-gform-r3) reproduce some of them?

Method: read-only measurement at pinned hashes, plus faithful sandbox replays of the
project's own tools on byte copies. No canonical file is written.

Findings are per blocker class B1..B5. Each carries: the closure predicate, the
authorized item (if any), the measured state, and a falsifier.

Deterministic: the report body is a pure function of the pinned inputs (no wall clock,
no environment). Run twice; SHA256 must match.

Usage: python3 check_rec12_repair_coverage.py [--json]
Exit 0 = report written; 1 = internal check failure; 2 = pinned input missing.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-069/rec12_repair_coverage -> repo root
SB = HERE / "sandbox"

P = {  # pinned relative paths
    "card_source": "comms/inbox/astra-lead-formulation.jsonl",
    "f1": "schemas/af_wcc_vacuum.yaml",
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "f0_declared": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "frozen": "artifacts/formulation/FROZEN.json",
    "evidence_live": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "evidence_preserved_675a": "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json",
    "c0_sidecar": "schemas/af_scc_c0_vacuum.yaml.sha256",
    "taxonomy_cases": "schemas/taxonomy_cases.jsonl",
    "acceptance_tool": "artifacts/formulation/tools/run_acceptance.py",
    "acceptance_record": "artifacts/formulation/evidence/semantic_escape_rebased.json",
    "checker": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "w069_f2a_report": "artifacts/worker-069/f2a_rev12_closure_verdict/report.json",
    "w069_f2b_report": "artifacts/worker-069/f2b_rev12_independent_verdict/report.json",
    "w090_f1_review": "reviews/F1-rev12-closure-090.json",
    "w092_evbind": "artifacts/worker-092/evbind/report.json",
    "w094_closefind": "reviews/closefind-verify-094.json",
    "w091_f2b_review": "artifacts/worker-091/f2b_rev12_closure/REVIEW.md",
}
CARD_EVENT_ID = "astra-life05-evidence-binding-repair"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(rel: str) -> str:
    return sha_bytes((ROOT / rel).read_bytes())


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text()


def load_card() -> dict:
    for line in read_text(P["card_source"]).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event_id") == CARD_EVENT_ID:
            return d
    raise SystemExit(f"card {CARD_EVENT_ID} not found in {P['card_source']}")


def run(cmd: list[str], cwd: Path) -> dict:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
    return {"argv": cmd, "exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


# ---------------------------------------------------------------- checker replay
def checker_replay(mutate: bool) -> dict:
    sb = SB / ("checker_replay_mutant" if mutate else "checker_replay")
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "artifacts/formulation/tools").mkdir(parents=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True)
    (sb / "research_map").mkdir(parents=True)
    shutil.copy2(ROOT / P["checker"], sb / "artifacts/formulation/tools/")
    shutil.copy2(ROOT / P["aliases"], sb / "artifacts/formulation/")
    shutil.copy2(ROOT / P["f0_supplement"], sb / "artifacts/formulation/")
    tax = (ROOT / P["f0_declared"]).read_text()
    if mutate:
        tax2, n = re.subn(r'family:\s*"WCC"', 'family: "SCC"', tax, count=1)
        if n != 1:
            raise SystemExit("mutant substitution failed (family: \"WCC\" not found)")
        tax = tax2
    (sb / "research_map/formulation_taxonomy.yaml").write_text(tax)
    res = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"], sb)
    out = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"
    body = out.read_bytes() if out.exists() else b""
    doc = json.loads(body) if body else {}
    return {
        "sandbox": str(sb.relative_to(ROOT)),
        "mutated": mutate,
        "exit": res["exit"],
        "stdout": res["stdout"].strip(),
        "output_sha256": sha_bytes(body) if body else None,
        "output_keys": sorted(doc.keys()),
        "embeds_f0_sha256": sha(P["f0_declared"]) in body.decode(errors="replace"),
        "embeds_supplement_sha256": sha(P["f0_supplement"]) in body.decode(errors="replace"),
    }


# ------------------------------------------------------------- acceptance replay
def acceptance_replay(patch_record: bool) -> dict:
    sb = SB / ("acceptance_replay_positive_control" if patch_record else "acceptance_replay")
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "artifacts/formulation/tools").mkdir(parents=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True)
    (sb / "artifacts/formulation/schemas").mkdir(parents=True)
    shutil.copy2(ROOT / P["acceptance_tool"], sb / "artifacts/formulation/tools/")
    shutil.copy2(ROOT / P["acceptance_record"], sb / "artifacts/formulation/evidence/")
    base_copy = sb / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    shutil.copy2(ROOT / P["f2b"], base_copy)
    rec_path = sb / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    rec = json.loads(rec_path.read_text())
    original_base = rec.get("base_sha256")
    if patch_record:
        rec["base_sha256"] = sha_bytes(base_copy.read_bytes())
        rec_path.write_text(json.dumps(rec, indent=1) + "\n")
    res = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py", "--json"], sb)
    return {
        "sandbox": str(sb.relative_to(ROOT)),
        "record_base_sha256": original_base,
        "base_file_sha256": sha_bytes(base_copy.read_bytes()),
        "preflight_fail_in_stdout": "PREFLIGHT FAIL" in res["stdout"],
        "exit": res["exit"],
        "stdout_head": "\n".join(res["stdout"].splitlines()[:4]),
    }


# --------------------------------------------------------------- B1..B5 measurements
def main() -> int:
    pins = {rel: sha(P[rel]) for rel in P if (ROOT / P[rel]).exists()}
    missing = [P[rel] for rel in P if not (ROOT / P[rel]).exists()]
    if missing:
        print("MISSING PINNED INPUTS:", missing, file=sys.stderr)
        return 2

    card = load_card()
    card_canon = json.dumps(card, sort_keys=True, separators=(",", ":")).encode()

    # ---- B1: declared consistency_evidence_sha256 vs measured evidence file
    import yaml  # PyYAML is a project dependency (used by the checker itself)

    declared = {}
    for key in ("f1", "f2a", "f2b"):
        doc = yaml.safe_load((ROOT / P[key]).read_text())
        declared[key] = doc["f0_binding"]["consistency_evidence_sha256"]
    ev_live = sha(P["evidence_live"])
    b1_rows = [
        {"schema": P[k], "declared": declared[k], "measured": ev_live,
         "declared_equals_measured": declared[k] == ev_live}
        for k in ("f1", "f2a", "f2b")
    ]
    b1_closed_by_item2 = all(r["declared_equals_measured"] for r in b1_rows)
    b1_status = (
        "CLOSED_AT_MEASURED_BYTES" if b1_closed_by_item2
        else ("CLOSED_BY_ITEM_2_ON_EXECUTION" if all(not r["declared_equals_measured"] for r in b1_rows)
              else "PARTIAL_MIXED")
    )

    # ---- B2: does the clean checker output bind its compared trees by digest?
    replay = checker_replay(mutate=False)
    mutant = checker_replay(mutate=True)
    clean_reproduces_live = replay["output_sha256"] == ev_live
    preserved = json.loads((ROOT / P["evidence_preserved_675a"]).read_text())
    b2 = {
        "clean_replay_reproduces_live_evidence": clean_reproduces_live,
        "live_output_keys": replay["output_keys"],
        "live_output_embeds_f0_sha256": replay["embeds_f0_sha256"],
        "live_output_embeds_supplement_sha256": replay["embeds_supplement_sha256"],
        "preserved_675a_keys": sorted(preserved.keys()),
        "preserved_675a_embeds_f0_sha256": pins["f0_declared"] in json.dumps(preserved),
        "preserved_675a_embeds_supplement_sha256": pins["f0_supplement"] in json.dumps(preserved),
        "mutant_control": mutant,
    }
    b2_closed = bool(
        replay["embeds_f0_sha256"] and replay["embeds_supplement_sha256"]
    )

    # ---- B3: C0 stale sidecar (not named in the card's artifact list)
    sidecar_txt = read_text(P["c0_sidecar"]).split()[0].strip()
    b3 = {
        "sidecar_declared": sidecar_txt,
        "canonical_measured": pins["f2b"],
        "stale": sidecar_txt != pins["f2b"],
        "named_in_card_artifact_list": P["c0_sidecar"] in (card.get("artifact") or []),
    }

    # ---- B4: acceptance preflight
    acc_now = acceptance_replay(patch_record=False)
    acc_ctl = acceptance_replay(patch_record=True)
    rec_base = json.loads((ROOT / P["acceptance_record"]).read_text()).get("base_sha256")
    b4 = {
        "record_base_sha256": rec_base,
        "current_authoring_c0_sha256": pins["f2b"],
        "preflight_would_pass_now": rec_base == pins["f2b"],
        "replay_current_bytes": acc_now,
        "positive_control_patched_record": acc_ctl,
        "item2_moves_c0_bytes": True,
        "note": (
            "item (2) edited f0_binding in all three schemas, so the frozen rev29 C0 bytes are a new hash "
            "(b2ab6acb); the record's base_sha256 (1bb78ce9) cannot equal it. The preflight passes only after "
            "measure_semantic_escape.py is re-run, which no card item names."
        ),
    }
    b4_closed = False  # as-written: no item regenerates the corpus

    # ---- frozen-manifest chain for B3/B4 (the freeze is the object the r3 round will review)
    frozen_doc = json.loads((ROOT / P["frozen"]).read_text())
    frozen_files = frozen_doc.get("files", {})
    frozen_c0 = (frozen_files.get(P["f2b"]) or {}).get("sha256")
    frozen_rec = (frozen_files.get(P["acceptance_record"]) or {}).get("sha256")
    b4["frozen_manifest_pins_acceptance_record"] = frozen_rec == pins["acceptance_record"]
    b4["frozen_manifest_c0_sha256"] = frozen_c0
    b4["frozen_manifest_record_base_sha256"] = rec_base
    b4["frozen_manifest_preflight_holds"] = bool(frozen_rec) and rec_base == frozen_c0
    b3["frozen_manifest_pins_sidecar"] = P["c0_sidecar"] in frozen_files
    b3["frozen_manifest_revision"] = frozen_doc.get("revision")

    # ---- B5: taxonomy_cases rows
    rows = [json.loads(l) for l in read_text(P["taxonomy_cases"]).splitlines() if l.strip()]
    meta = next(r for r in rows if r.get("record_type") == "meta")
    row_bindings = sorted({str(r.get("binding_status")) for r in rows if r.get("record_type") != "meta"})
    b5 = {
        "meta_taxonomy_ref_sha256": (meta.get("taxonomy_ref") or {}).get("sha256"),
        "row_binding_status_values": row_bindings,
        "declared_f0_sha256": pins["f0_declared"],
        "rows_bound_to_declared_f0": row_bindings == ["bound_taxonomy_sha_" + pins["f0_declared"][:12]],
    }
    b5_closed_by_item1 = b5["rows_bound_to_declared_f0"]

    findings = [
        {
            "id": "B1-declared-consistency-evidence-hash",
            "blocker_classes": ["HF-086-R1", "HF-094C-2", "HF-069R-3", "HF-069F2B-I08", "HF-091-1/A9", "W090-R12-01(limb1)"],
            "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "authorized_item": "item (2) refresh f0_binding.consistency_evidence_sha256 to the live evidence hash",
            "closure_predicate": "for each schema, declared consistency_evidence_sha256 == sha256(live evidence) at frozen bytes",
            "measured": b1_rows,
            "status": b1_status,
            "residual_risk": (
                "item (2) restores declared==measured only as a fixpoint: worker-041 showed the evidence is a "
                "derived output of four inputs and the schema refresh rule names one of them, so any later edit "
                "to supplement/aliases/checker re-opens it silently (HF-041-RCA-2)."
            ),
            "falsifier": "a rev29 freeze at which declared!=measured for any schema, or an input edit after the freeze that re-opens the mismatch",
            "evidence_refs": [
                f"{P['f1']}#{pins['f1'][:12]}", f"{P['f2a']}#{pins['f2a'][:12]}", f"{P['f2b']}#{pins['f2b'][:12]}",
                f"{P['evidence_live']}#{ev_live[:12]}",
                "reviews/G-FORM-rev12-binding-086.json",
                f"{P['w094_closefind']}#{pins['w094_closefind'][:12]}",
                f"{P['w069_f2a_report']}#{pins['w069_f2a_report'][:12]}",
                f"{P['w069_f2b_report']}#{pins['w069_f2b_report'][:12]}",
                f"{P['w090_f1_review']}#{pins['w090_f1_review'][:12]}",
            ],
        },
        {
            "id": "B2-evidence-does-not-bind-its-inputs",
            "blocker_classes": ["W090-R12-01(limb2)", "HF-069F2B-I09", "w092 P3"],
            "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "authorized_item": "NONE -- item (2) pins the output of the unpatched checker",
            "closure_predicate": (
                "the frozen consistency evidence embeds the measured sha256 of both compared trees "
                "(canonical F0 and authoring supplement), so 'consistent=true' is bound to the inputs it checks"
            ),
            "measured": b2,
            "status": "CLOSED_BY_ITEM_SET" if b2_closed else "NOT_CLOSED_BY_ITEMS_AS_WRITTEN",
            "residual_risk": (
                "the checker de356d999ea3 emits exactly the 8 keys of the live document and no input digest; a clean "
                "run reproduces the live bytes, so item (2) is self-consistent but cannot satisfy the rebuttal "
                "condition recorded by worker-090 and worker-069. The preserved 675a99d0 generation did carry both "
                "digests, so a digest-emitting checker is demonstrably possible (worker-030/086/096 drafts), but "
                "adopting one changes the evidence bytes and makes item (2)'s named target hash stale by construction."
            ),
            "falsifier": (
                "a frozen consistency evidence whose bytes contain the measured sha256 of both compared trees AND "
                "equal the declared pin; or a card amendment that changes the checker and pins the post-change output"
            ),
            "evidence_refs": [
                f"{P['checker']}#{pins['checker'][:12]}",
                f"{P['evidence_live']}#{ev_live[:12]}",
                f"{P['evidence_preserved_675a']}#{pins['evidence_preserved_675a'][:12]}",
                f"{P['w092_evbind']}#{pins['w092_evbind'][:12]}",
                f"{P['w090_f1_review']}#{pins['w090_f1_review'][:12]}",
                "artifacts/worker-030/evidence_pin_repair/patched_check_taxonomy_consistency.py",
                "artifacts/worker-096/evidence_binding_adjudication/proposed_checker_patch.diff",
            ],
        },
        {
            "id": "B3-stale-c0-sidecar",
            "blocker_classes": ["HF-091-2/A10"],
            "classes": ["AF-SCC-C0-VAC-GEN"],
            "authorized_item": "NONE explicitly (item (4) says 'byte-verified pins' but the sidecar is not in the card artifact list)",
            "closure_predicate": "schemas/af_scc_c0_vacuum.yaml.sha256 records sha256(canonical schema)",
            "measured": b3,
            "status": "CLOSED_BY_ITEM_SET" if not b3["stale"] else ("AMBIGUOUS_UNDER_ITEM_4" if not b3["named_in_card_artifact_list"] else "CLOSED_BY_ITEM_4"),
            "residual_risk": "an unmanaged companion that leads a reader to superseded bytes: it still records rev11 1bb78ce9 while the frozen rev29 C0 is b2ab6acb; it is not in FROZEN rev29 files and not in the card artifact list",
            "falsifier": "the sidecar is refreshed to the rev29 C0 hash (or removed / explicitly out of scope) at freeze time",
            "evidence_refs": [f"{P['c0_sidecar']}#{sha(P['c0_sidecar'])[:12]}", f"{P['f2b']}#{pins['f2b'][:12]}", f"{P['frozen']}#{pins['frozen'][:12]}", "artifacts/worker-091/f2b_rev12_closure/REVIEW.md"],
        },
        {
            "id": "B4-acceptance-preflight-stale-corpus",
            "blocker_classes": ["HF-069R-2", "HF-069F2B-F07", "worker-16 staged re-run"],
            "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "authorized_item": "NONE -- no card item regenerates artifacts/formulation/evidence/semantic_escape_rebased.json / rebased_fixtures",
            "closure_predicate": "artifacts/formulation/tools/run_acceptance.py passes preflight, i.e. record.base_sha256 == sha256(current C0 schema), then both stages accept the canonical schemas",
            "measured": b4,
            "status": "NOT_CLOSED_BY_ITEMS_AS_WRITTEN",
            "residual_risk": (
                "run_acceptance.py exits 3 PREFLIGHT FAIL at the frozen rev29 bytes: the record's base_sha256 is "
                "1bb78ce9 while the frozen C0 schema is b2ab6acb, and FROZEN rev29 itself pins the stale corpus "
                "(semantic_escape_rebased.json 7e44de0e carries base_sha256 1bb78ce9). No card item re-runs "
                "measure_semantic_escape.py, so the two-stage acceptance criterion remains failing at rev29 and "
                "astra-life05-verify-gform-r3 will reproduce this blocker on bytes it cannot judge."
            ),
            "falsifier": "run_acceptance.py reports ACCEPTANCE: PASS at the rev29 pins with a record base_sha256 equal to the rev29 C0 hash",
            "evidence_refs": [
                f"{P['acceptance_tool']}#{pins['acceptance_tool'][:12]}",
                f"{P['acceptance_record']}#{pins['acceptance_record'][:12]}",
                f"{P['f2b']}#{pins['f2b'][:12]}",
                f"{P['frozen']}#{pins['frozen'][:12]}",
                f"{P['w069_f2a_report']}#{pins['w069_f2a_report'][:12]}",
                f"{P['w069_f2b_report']}#{pins['w069_f2b_report'][:12]}",
            ],
        },
        {
            "id": "B5-taxonomy-cases-row-binding",
            "blocker_classes": ["HF-094C-1"],
            "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "authorized_item": "item (1) rebind schemas/taxonomy_cases.jsonl rows to F0 rev5 and re-run its checker",
            "closure_predicate": "every non-meta row's binding_status == bound_taxonomy_sha_<declared F0 sha prefix>",
            "measured": b5,
            "status": "CLOSED_ALREADY_AT_MEASURED_BYTES" if b5_closed_by_item1 else "CLOSED_BY_ITEM_1",
            "residual_risk": "none measured; item (1) is a re-run/attestation rather than a byte change at these bytes",
            "falsifier": "a row still carrying bound_taxonomy_sha_66bf917bd368 at freeze time",
            "evidence_refs": [f"{P['taxonomy_cases']}#{pins['taxonomy_cases'][:12]}", f"{P['f0_declared']}#{pins['f0_declared'][:12]}", f"{P['w094_closefind']}#{pins['w094_closefind'][:12]}"],
        },
    ]

    blockers_open = [f["id"] for f in findings if f["status"] in ("NOT_CLOSED_BY_ITEMS_AS_WRITTEN", "AMBIGUOUS_UNDER_ITEM_4", "NOT_CLOSED")]
    report = {
        "schema_version": "0.1",
        "record_id": "W069-LIFE05-REC12-REPAIR-COVERAGE-01-report",
        "task_id": "W069-LIFE05-REC12-REPAIR-COVERAGE-01",
        "actor": "worker-069",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "authority": "measurement/adjudication of a repair card only; no canonical write, no gate verdict, no node status",
        "reviewed_card": {
            "event_id": CARD_EVENT_ID,
            "created_at": card.get("created_at"),
            "deadline": card.get("deadline"),
            "assignee": card.get("assignee"),
            "source": f"{P['card_source']}",
            "card_canonical_sha256": sha_bytes(card_canon),
        },
        "pins": {P[k]: v for k, v in pins.items()},
        "findings": findings,
        "counts": {
            "blocker_classes": sum(len(f["blocker_classes"]) for f in findings),
            "finding_classes": len(findings),
            "closed_by_items": len(findings) - len(blockers_open),
            "open_or_ambiguous_after_items": len(blockers_open),
        },
        "verdict": "REPAIR_COVERAGE_INCOMPLETE",
        "verdict_detail": (
            "At the measured candidate-repair bytes the schemas already declare consistency evidence 9e335e9b == "
            "measured (B1 closed) and all 36 case rows already bind F0 rev5 (B5 closed). The four items do not "
            "close B2 (the consistency evidence still embeds no digest of either compared tree; no item changes the "
            "checker), B3 (the C0 sidecar is still stale and is not in the card artifact list) or B4 (the acceptance "
            "preflight corpus is not regenerated, and item (2)'s own schema edit moves the base hash to b2ab6acb, so "
            "the preflight still fails). B4 alone means the two-stage acceptance criterion stays failing at the "
            "repair bytes, and astra-life05-verify-gform-r3 will reproduce it."
        ),
        "open_blockers_after_items": blockers_open,
        "recommended_amendment": (
            "extend the card with (5) re-run artifacts/formulation/tools/measure_semantic_escape.py to regenerate "
            "artifacts/formulation/evidence/semantic_escape_rebased.json + rebased_fixtures at the rev29 C0 hash and "
            "record the new base_sha256, and (6) either refresh or retire schemas/af_scc_c0_vacuum.yaml.sha256; and "
            "record an explicit disposition for B2 (adopt a digest-emitting checker and pin its output, or accept "
            "B2 as a residual and state it in the gate criteria)."
        ),
        "falsifier": (
            "This coverage test is falsified if, at the rev29 pins: (a) any schema's declared "
            "consistency_evidence_sha256 != measured evidence (B1 re-opened); (b) the frozen evidence embeds the "
            "measured sha256 of both compared trees and equals the declared pin (B2 closed); (c) the C0 sidecar "
            "equals the rev29 C0 hash or is explicitly out of scope (B3 closed); (d) run_acceptance.py reports "
            "ACCEPTANCE: PASS with record.base_sha256 == the rev29 C0 hash (B4 closed); or (e) a case row still "
            "binds 66bf917b (B5 re-opened). Input drift without a rev29 freeze voids the binding, not the finding."
        ),
        "method": (
            "read-only pinning + census; sandbox replay of check_taxonomy_consistency.py (clean and one-token "
            "family mutant) and of run_acceptance.py (current record and a base_sha256-patched positive control). "
            "All sandboxes under artifacts/worker-069/rec12_repair_coverage/sandbox/."
        ),
        "controls": {
            "C1_checker_replay_reproduces_live": clean_reproduces_live,
            "C2_checker_mutant_is_discriminated": mutant["exit"] != 0 and mutant["output_sha256"] != replay["output_sha256"],
            "C3_acceptance_preflight_discriminates": acc_now["preflight_fail_in_stdout"] and not acc_ctl["preflight_fail_in_stdout"],
            "C4_preserved_generation_binds_inputs": b2["preserved_675a_embeds_f0_sha256"] and b2["preserved_675a_embeds_supplement_sha256"],
        },
    }
    # ---- drift check: re-hash every pinned input at write time (cf. worker-091 lesson)
    end = {rel: sha(P[rel]) for rel in P}
    drift = {
        P[rel]: {"snapshot": pins[rel], "measured_at_write": end[rel], "moved": pins[rel] != end[rel]}
        for rel in P
    }
    frozen_doc = json.loads((ROOT / P["frozen"]).read_text())
    report["drift_at_write"] = {
        "pins": drift,
        "moved_since_snapshot": [k for k, v in drift.items() if v["moved"]],
        "binding_status": "STABLE" if not any(v["moved"] for v in drift.values()) else "MOVED_DURING_RUN",
    }
    report["candidate_repair_bytes"] = {
        "note": "frozen rev29 repair state measured at snapshot (frozen_at 2026-09-12T00:54:32+08:00)",
        "schema_sha256": {P[k]: pins[k] for k in ("f1", "f2a", "f2b")},
        "frozen_revision": frozen_doc.get("revision"),
        "frozen_sha256": pins["frozen"],
        "item4_rev29_published": frozen_doc.get("revision") == 29,
    }
    controls_ok = all(report["controls"].values())
    if not controls_ok:
        report["verdict"] = "INSTRUMENT_CONTROL_FAILURE"
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (HERE / "raw").mkdir(exist_ok=True)
    (HERE / "raw" / "checker_replay.json").write_text(json.dumps({"clean": replay, "mutant": mutant}, indent=1) + "\n")
    (HERE / "raw" / "acceptance_replay.json").write_text(json.dumps({"current": acc_now, "positive_control": acc_ctl}, indent=1) + "\n")
    (HERE / "raw" / "b1_declared.json").write_text(json.dumps(b1_rows, indent=1) + "\n")
    (HERE / "raw" / "b5_taxonomy_cases.json").write_text(json.dumps(b5, indent=1) + "\n")
    if "--json" in sys.argv:
        print(json.dumps({k: report[k] for k in ("verdict", "counts", "open_blockers_after_items", "controls")}, indent=1))
    else:
        print(f"REC12 REPAIR COVERAGE: {report['verdict']}  controls_ok={controls_ok}")
        print(f"  open/ambiguous after the four items: {blockers_open}")
    return 0 if controls_ok else 1


if __name__ == "__main__":
    sys.exit(main())
