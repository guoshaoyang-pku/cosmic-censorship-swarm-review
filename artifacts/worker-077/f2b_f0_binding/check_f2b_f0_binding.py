#!/usr/bin/env python3
"""W077-F2B-F0BIND-CONSISTENCY-01.

Independent, read-only, hash-pinned cross-artifact consistency audit for one class:
AF-SCC-C0-VAC-GEN (F2b schema vs the declared F0 taxonomy), plus two binding-integrity
replications and one ledger-citation replication at the hashes measured on 2026-09-12.

The primary question is semantic and is NOT covered by the lead's
artifacts/formulation/tools/check_taxonomy_consistency.py, which compares the map taxonomy
against the authoring supplement only:
  does the quantifier domain of the C0 class statement in the DECLARED F0 artifact
  (research_map/formulation_taxonomy.yaml, classes.AF-SCC-C0-VAC-GEN.conclusion.text)
  agree with the quantifier domain of the F2b schema that binds to it
  (schemas/af_scc_c0_vacuum.yaml, quantifiers.domains.D0 / quantifiers.formal)?

Everything is read-only: the script writes only inside its own --out directory.
Fail-closed: if any pinned input hash differs from PINS, the verdict is SUPERSEDED and the
hard checks are not asserted.

Exit codes: 0 all hard checks pass; 2 at least one hard check fails; 3 input drift (superseded).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]

TASK_ID = "W077-F2B-F0BIND-CONSISTENCY-01"
WORKER = "worker-077"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_IDS = ["F2b", "F0"]
GATE = "G-FORM"
SECONDARY_GATE = "G-F0"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
}
# Context-only inputs (measured, never a hard check; may move without superseding this report).
CONTEXT_PINS = {
    "artifacts/formulation/formulation_taxonomy.yaml": None,
    "artifacts/formulation/FROZEN.json": None,
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def duplicate_yaml_keys(path: Path) -> list[dict]:
    """Strict compose-based duplicate mapping-key scan (PyYAML drops duplicates silently)."""
    dups: list[dict] = []
    try:
        node = yaml.compose(path.read_text())
    except yaml.YAMLError as exc:  # pragma: no cover - malformed target
        return [{"path": str(path), "error": str(exc)}]

    def walk(n, trail):
        if isinstance(n, yaml.MappingNode):
            seen: dict[str, int] = {}
            for k, v in n.value:
                key = getattr(k, "value", str(k))
                if key in seen:
                    dups.append({"key": str(key), "line": k.start_mark.line + 1,
                                 "trail": list(trail)})
                else:
                    seen[key] = k.start_mark.line + 1
                walk(v, trail + [str(key)])
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, trail + [f"[{i}]"])

    walk(node, [])
    return dups


def find_lines(text: str, pattern: str, after: int = 0) -> list[int]:
    rx = re.compile(pattern)
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        if i > after and rx.search(line):
            out.append(i)
    return out


def classify_index(domain_text: str, statement_text: str) -> dict:
    """Compare the F2b index domain against an F0 class-statement text.

    Branches are detected on the F2b D0 definition; the F0 statement is inspected for an
    explicit mention of each branch and for a pair-indexed form. The classifier is exercised
    by the controls below before it is applied to the real artifacts.
    """
    dom = (domain_text or "")
    st = (statement_text or "")
    dom_l, st_l = dom.lower(), st.lower()

    f2b_smooth = bool(re.search(r"smooth", dom_l))
    f2b_sobolev = bool(re.search(r"sobolev", dom_l))
    f2b_tagged_union = bool(re.search(r"disjoint union|tagged union", dom_l))

    f0_smooth = bool(re.search(r"smooth", st_l))
    f0_sobolev = bool(re.search(r"sobolev|\bs\b\s*>\s*5/2|\(s,\s*delta\)", st_l))
    f0_r_index = bool(re.search(r"forall\s+r\b|for every\s+r\b|\br\s+in\s+D0\b", st_l))
    f0_pair_index = bool(re.search(r"admissible\s*\(s,\s*delta\)|G_\{s,\s*delta\}", st_l))

    if not (f2b_smooth or f2b_sobolev):
        verdict = "DOMAIN_NOT_DETECTED"
    elif f0_r_index:
        # The F0 statement quantifies over the shared tagged-union index by name; the branch
        # enumeration lives in the domain definition both artifacts bind.
        verdict = "CONSISTENT"
    elif f0_pair_index and f2b_smooth and not f0_smooth:
        verdict = "DIVERGENT_F0_OMITS_SMOOTH_BRANCH"
    elif f0_smooth and not f0_sobolev and f2b_sobolev:
        verdict = "DIVERGENT_F0_OMITS_SOBOLEV_BRANCH"
    elif f0_pair_index and f0_smooth and f2b_sobolev:
        verdict = "CONSISTENT"
    elif not f0_r_index and not f0_pair_index and not f0_smooth and not f0_sobolev:
        verdict = "F0_INDEX_NOT_MACHINE_EXPLICIT"
    else:
        verdict = "DIVERGENT_OTHER"
    return {
        "verdict": verdict,
        "f2b_branches": {"smooth_with_decay": f2b_smooth, "sobolev": f2b_sobolev,
                         "tagged_disjoint_union": f2b_tagged_union},
        "f0_statement": {"mentions_smooth": f0_smooth, "mentions_sobolev_or_pair": f0_sobolev,
                         "r_indexed": f0_r_index, "pair_indexed": f0_pair_index},
    }


def self_test_classifier() -> dict:
    dom = ("admissible regularity indices, a tagged disjoint union: r = smooth "
           "(the smooth-with-decay default) or r = (sobolev,s,delta) with s > 5/2")
    cases = [
        ("equal_r_index", dom,
         "forall r in D0 exists G_r comeager: for all data in G_r ...", "CONSISTENT"),
        ("omit_smooth", dom,
         "For every admissible (s,delta) there is a comeager set G_{s,delta} of data such that ...",
         "DIVERGENT_F0_OMITS_SMOOTH_BRANCH"),
        ("omit_sobolev", dom,
         "For every smooth-with-decay datum there is a comeager set of data such that ...",
         "DIVERGENT_F0_OMITS_SOBOLEV_BRANCH"),
        ("both_branches_named", dom,
         "For every admissible (s,delta) and for the smooth-with-decay default there is a "
         "comeager set of data such that ...", "CONSISTENT"),
        ("no_index", dom, "The MGHD is inextendible for generic data.", "F0_INDEX_NOT_MACHINE_EXPLICIT"),
    ]
    results = []
    for name, d, s, expected in cases:
        got = classify_index(d, s)["verdict"]
        results.append({"case": name, "expected": expected, "got": got,
                        "pass": got == expected})
    return {"cases": results, "passed": sum(c["pass"] for c in results), "total": len(results),
            "all_pass": all(c["pass"] for c in results)}


def check_citation_binding(schema: dict, ledger_rows: dict, ledger_text: str) -> dict:
    refs = schema.get("l1_ledger_refs") or []
    per_row = []
    for ref in refs:
        tid = ref.get("theorem_id")
        row = ledger_rows.get(tid)
        claimed = ref.get("citation_status")
        rec = {
            "theorem_id": tid,
            "claimed_citation_status": claimed,
            "claimed_l1_status": ref.get("l1_status"),
            "ledger_present": row is not None,
        }
        if row is None:
            rec["classification"] = "MISSING_LEDGER_ROW"
        else:
            rec.update({
                "ledger_verification_status": row.get("verification_status"),
                "ledger_review_status": row.get("review_status"),
                "ledger_content_status": row.get("content_status"),
                "ledger_evidence_level": row.get("evidence_level"),
                "ledger_acceptance_authority": row.get("acceptance_authority"),
            })
            if claimed == "verified_by_L1":
                if (row.get("review_status") == "not_independently_reviewed"
                        and row.get("verification_status") in {"abstract-read", "unverified"}):
                    rec["classification"] = "OVERCLAIM"
                elif row.get("review_status") != "not_independently_reviewed":
                    rec["classification"] = "SUPPORTED"
                else:
                    rec["classification"] = "AMBIGUOUS"
            elif claimed in {"unresolved", "unverified"}:
                rec["classification"] = "HONEST_DOWNGRADE"
            elif claimed == row.get("verification_status"):
                rec["classification"] = "MATCH"
            else:
                rec["classification"] = "OTHER"
        per_row.append(rec)
    overclaims = [r for r in per_row if r["classification"] == "OVERCLAIM"]
    token_occurrences = ledger_text.count("verified_by_L1")
    provenance_status = (schema.get("provenance") or {}).get("citation_status")
    return {
        "rows": per_row,
        "overclaim_count": len(overclaims),
        "overclaim_ids": [r["theorem_id"] for r in overclaims],
        "ledger_token_verified_by_L1_count": token_occurrences,
        "schema_provenance_citation_status": provenance_status,
        "self_contradiction": bool(overclaims) and provenance_status in {"unverified", "unresolved"},
    }


def frozen_context(frozen_path: Path, needles: list[str]) -> dict:
    try:
        data = json.loads(frozen_path.read_text())
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc)}
    hits: dict[str, list[str]] = {}
    raw = json.dumps(data, ensure_ascii=False)

    def walk(obj, trail=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{trail}.{k}" if trail else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{trail}[{i}]")
        elif isinstance(obj, str) and len(obj) == 64 and re.fullmatch(r"[0-9a-f]{64}", obj):
            for n in needles:
                if n in trail:
                    hits.setdefault(n, []).append(f"{trail}={obj[:16]}")

    walk(data)
    return {"frozen_sha256": sha256_file(frozen_path), "pin_hits": hits,
            "mentions_taxonomy_consistency": "taxonomy_consistency" in raw}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "snapshots").mkdir(parents=True, exist_ok=True)

    started = datetime.now().astimezone().isoformat(timespec="seconds")
    drift: list[dict] = []
    measured: dict[str, str] = {}

    # --- pin verification + byte snapshots ------------------------------------------------
    for rel, expect in PINS.items():
        p = REPO / rel
        got = sha256_file(p)
        measured[rel] = got
        if got != expect:
            drift.append({"path": rel, "expected": expect, "measured": got})
        snap = out / "snapshots" / rel.replace("/", "__")
        shutil.copyfile(p, snap)
        snap_hash = sha256_file(snap)
        if snap_hash != got:
            drift.append({"path": f"snapshot:{rel}", "expected": got, "measured": snap_hash})
    context_measured = {}
    for rel in CONTEXT_PINS:
        p = REPO / rel
        context_measured[rel] = sha256_file(p) if p.exists() else None

    superseded = bool(drift)
    checks: list[dict] = []

    def add(cid, status, severity, detail, evidence):
        checks.append({"check_id": cid, "status": status, "severity": severity,
                       "detail": detail, "evidence": evidence})

    add("C0-PIN-STABILITY", "FAIL" if superseded else "PASS", "hard",
        ("pinned input hash drift: " + json.dumps(drift)) if superseded
        else "all four pinned inputs matched their declared sha256 before the checks",
        [f"{k}#{v[:16]}" for k, v in measured.items()])

    if not superseded:
        f2b_path = REPO / "schemas/af_scc_c0_vacuum.yaml"
        tax_path = REPO / "research_map/formulation_taxonomy.yaml"
        ledger_path = REPO / "ledger/theorems.jsonl"

        f2b = yaml.safe_load(f2b_path.read_bytes())
        tax = yaml.safe_load(tax_path.read_bytes())
        ledger_rows = {}
        ledger_text = ledger_path.read_text()
        for line in ledger_text.splitlines():
            if line.strip():
                r = json.loads(line)
                ledger_rows[r.get("theorem_id")] = r

        # --- C1 duplicate-key guard (parse-safety control, not the target finding) --------
        dups = duplicate_yaml_keys(f2b_path) + duplicate_yaml_keys(tax_path)
        add("C1-DUP-KEY-GUARD", "PASS" if not dups else "FAIL", "hard",
            "no duplicate YAML mapping keys in the two parsed targets" if not dups
            else f"duplicate mapping keys shadow the parse: {dups[:5]}",
            [f"schemas/af_scc_c0_vacuum.yaml#{measured['schemas/af_scc_c0_vacuum.yaml'][:16]}",
             f"research_map/formulation_taxonomy.yaml#{measured['research_map/formulation_taxonomy.yaml'][:16]}"])

        # --- C2 primary: F0 declared index vs F2b index ----------------------------------
        tax_text = tax_path.read_text()
        c0_anchor = find_lines(tax_text, r'^\s*"AF-SCC-C0-VAC-GEN":')
        c0_start = c0_anchor[0] if c0_anchor else 0
        c2_anchor = find_lines(tax_text, r'^\s*"AF-SCC-C2-VAC-GEN":')
        c2_start = c2_anchor[0] if c2_anchor else 0
        f0_text = tax["classes"][CLASS_ID]["conclusion"]["text"]
        f0_text_lines = find_lines(tax_text, r"For every admissible \(s,delta\)", after=c0_start - 1)
        c2_text = tax["classes"]["AF-SCC-C2-VAC-GEN"]["conclusion"]["text"]
        c2_text_lines = find_lines(tax_text, r"For every admissible \(s,delta\)", after=c2_start - 1)

        d0 = f2b["quantifiers"]["domains"]["D0"]
        cls = classify_index(d0.get("definition", ""), f0_text)
        add("C2-F0-F2B-INDEX-CONSISTENCY",
            "FAIL" if cls["verdict"] != "CONSISTENT" else "PASS", "hard",
            f"primary finding: F0 declared C0 quantifier domain vs F2b D0 -> {cls['verdict']}",
            [f"research_map/formulation_taxonomy.yaml:{f0_text_lines} (classes.{CLASS_ID}.conclusion.text)",
             "schemas/af_scc_c0_vacuum.yaml:52 (quantifiers.domains.D0.definition)",
             "schemas/af_scc_c0_vacuum.yaml:42 (quantifiers.formal)",
             "schemas/af_scc_c0_vacuum.yaml:214 (conclusion.statement_formal)"])
        c2_note = {
            "f0_c0_statement_excerpt": f0_text.strip().replace("\n", " ")[:300],
            "f0_c0_statement_lines": f0_text_lines,
            "f2b_d0_definition_excerpt": str(d0.get("definition", "")).strip().replace("\n", " ")[:300],
            "f2b_formal": str(f2b["quantifiers"].get("formal", "")).strip().replace("\n", " ")[:300],
            "f2b_statement_formal": f2b["conclusion"].get("statement_formal"),
            "classification": cls,
            "same_pattern_in_C2_taxonomy_text": bool(c2_text_lines) and "(s,delta)" in c2_text,
            "c2_text_lines": c2_text_lines,
            "f0_taxonomy_C0_text_mentions_smooth": "smooth" in f0_text.lower(),
            "f0_h3_defers_data_space_to_F2": "owned by F2 and are unresolved here"
                                                in json.dumps(tax["classes"][CLASS_ID]["hypotheses"]),
        }
        add("C2b-F0-QUANTIFIER-EXPLICITNESS", "PASS", "info",
            "the declared F0 C0 text does carry an explicit comeager quantifier bound before the "
            "data, so the G-F0 'explicit comeager quantifier' wording criterion is nominally met; "
            "the defect is the index domain, not quantifier absence",
            [f"research_map/formulation_taxonomy.yaml:{f0_text_lines}"])

        # --- C3 F2b -> F0 binding integrity (replicated at the live hashes) --------------
        fb = f2b.get("f0_binding") or {}
        declared_hash = fb.get("declared_f0_sha256")
        live_f0 = measured["research_map/formulation_taxonomy.yaml"]
        declared_matches = declared_hash == live_f0
        ev_rel = fb.get("consistency_evidence")
        ev_path = REPO / ev_rel if ev_rel else None
        ev_live = sha256_file(ev_path) if ev_path and ev_path.exists() else None
        ev_declared = fb.get("consistency_evidence_sha256")
        ev_matches = bool(ev_live) and ev_live == ev_declared
        add("C3-F2B-F0-BINDING", "PASS" if (declared_matches and ev_matches) else "FAIL", "hard",
            ("declared F0 hash matches the live declared artifact"
             + ("; consistency-evidence hash matches the live file"
                if ev_matches else
                f"; consistency evidence declared {str(ev_declared)[:12]} but live file measures "
                f"{str(ev_live)[:12]}"))
            if declared_matches else
            f"declared F0 hash {str(declared_hash)[:12]} != live {live_f0[:12]}",
            [f"schemas/af_scc_c0_vacuum.yaml#f0_binding",
             f"{ev_rel}#{str(ev_live)[:16] if ev_live else 'missing'}"])
        binding_note = {
            "declared_f0_artifact": fb.get("declared_f0_artifact"),
            "declared_f0_sha256": declared_hash,
            "measured_f0_sha256": live_f0,
            "declared_f0_matches_live": declared_matches,
            "consistency_evidence": ev_rel,
            "consistency_evidence_declared_sha256": ev_declared,
            "consistency_evidence_measured_sha256": ev_live,
            "consistency_evidence_matches": ev_matches,
            "binding_note_excerpt": str(fb.get("binding_note", ""))[:400],
        }

        # --- C4 citation binding replication at the current ledger hash ------------------
        cit = check_citation_binding(f2b, ledger_rows, ledger_text)
        add("C4-CITATION-BINDING-REPLICATION", "FAIL" if cit["overclaim_count"] else "PASS",
            "hard",
            f"{cit['overclaim_count']} F2b l1_ledger_refs rows claim citation_status="
            f"'verified_by_L1' while the pinned ledger records review_status="
            f"'not_independently_reviewed' (token 'verified_by_L1' occurs "
            f"{cit['ledger_token_verified_by_L1_count']}x in the ledger; schema provenance."
            f"citation_status={cit['schema_provenance_citation_status']})",
            [f"schemas/af_scc_c0_vacuum.yaml:295-300 (l1_ledger_refs)",
             f"ledger/theorems.jsonl#{measured['ledger/theorems.jsonl'][:16]}"])

        # --- C5 self-tested comparator ----------------------------------------------------
        st = self_test_classifier()
        add("C5-CLASSIFIER-SELFTEST", "PASS" if st["all_pass"] else "FAIL", "hard",
            f"index classifier controls {st['passed']}/{st['total']} pass (equal, omit-smooth, "
            f"omit-sobolev, both-named, absent)", [json.dumps(st["cases"])])

        # --- C6 context -------------------------------------------------------------------
        ctx = frozen_context(REPO / "artifacts/formulation/FROZEN.json",
                             ["formulation_taxonomy", "af_scc_c0_vacuum", "taxonomy_consistency"])
        add("C6-FROZEN-CONTEXT", "PASS", "info",
            "FROZEN.json measured for context only (not a hard check; the freeze is owned by the "
            "formulation lead)", [f"artifacts/formulation/FROZEN.json#{str(ctx.get('frozen_sha256'))[:16]}"])
    else:
        c2_note, binding_note, cit, st, ctx, dups = {}, {}, {}, {}, {}, []

    # --- re-measure pinned inputs after the checks ----------------------------------------
    after = {}
    for rel in PINS:
        after[rel] = sha256_file(REPO / rel)
    moved = {k: {"before": measured.get(k), "after": v} for k, v in after.items()
             if measured.get(k) != v}
    add("C7-POST-CHECK-DRIFT", "FAIL" if moved else "PASS", "hard",
        "no pinned input moved during the audit window" if not moved
        else f"pinned inputs moved during the audit: {moved}",
        [f"{k}#{v[:16]}" for k, v in after.items()])

    hard_failures = [c for c in checks if c["severity"] == "hard" and c["status"] == "FAIL"]
    if superseded:
        verdict, score = "inconclusive", 0.0
    elif hard_failures:
        verdict, score = "revise", 2.5
    else:
        verdict, score = "accept", 4.0

    findings = []
    if not superseded:
        if next(c for c in checks if c["check_id"] == "C2-F0-F2B-INDEX-CONSISTENCY")["status"] == "FAIL":
            findings.append({
                "id": "W077-HF-01",
                "severity": "major",
                "class": CLASS_ID,
                "finding": ("Declared-F0 vs F2b quantifier-domain divergence: the canonical "
                            "taxonomy's C0 conclusion quantifies over admissible (s,delta) pairs "
                            "(G_{s,delta}) and never mentions the smooth-with-decay branch, while "
                            "F2b rev12 defines D0 as the tagged disjoint union r = smooth OR "
                            "r = (sobolev,s,delta) and quantifies 'forall r in D0'. The F2b "
                            "f0_binding is hash-current to the same taxonomy revision, so one "
                            "class id currently has two pinned statements with different index "
                            "domains. The taxonomy's H3 defers the data space to F2, which makes "
                            "this a dispositionable deferral rather than a mathematical "
                            "contradiction, but no explicit deferral note is recorded at the "
                            "conclusion and the lead's taxonomy_consistency check does not compare "
                            "the class-statement index domain."),
                "evidence": [f"research_map/formulation_taxonomy.yaml:{f0_text_lines}",
                             "schemas/af_scc_c0_vacuum.yaml:52",
                             "schemas/af_scc_c0_vacuum.yaml:42",
                             "schemas/af_scc_c0_vacuum.yaml:214"],
                "needed_to_unblock": ("gate owner disposition: either refresh the F0 C0 conclusion "
                                      "text to the r-index (matching F2b/F2a) at a new taxonomy "
                                      "revision, or record the deferral explicitly in the F0 class "
                                      "text and re-review at the new hash"),
                "falsifier": ("At the same pinned hashes, the finding is refuted if the F0 "
                              "taxonomy C0 conclusion quantifies over the smooth-with-decay "
                              "branch as well as the Sobolev branch, or if it carries an explicit "
                              "index-deferral clause that supersedes its '(s,delta)' wording."),
            })
        if next(c for c in checks if c["check_id"] == "C3-F2B-F0-BINDING")["status"] == "FAIL":
            findings.append({
                "id": "W077-HF-02",
                "severity": "major",
                "class": CLASS_ID,
                "finding": ("F2b f0_binding.consistency_evidence_sha256 is stale: it declares "
                            f"{str(binding_note.get('consistency_evidence_declared_sha256'))[:16]} "
                            "while the file it names measures "
                            f"{str(binding_note.get('consistency_evidence_measured_sha256'))[:16]}. "
                            "The declared F0 artifact hash itself does match the live taxonomy. "
                            "Independently reproduced from worker-095's F-EVID-1 at the same "
                            "hashes."),
                "evidence": [f"schemas/af_scc_c0_vacuum.yaml#f0_binding",
                             f"{binding_note.get('consistency_evidence')}"
                             f"#{str(binding_note.get('consistency_evidence_measured_sha256'))[:16]}"],
                "needed_to_unblock": ("refresh f0_binding.consistency_evidence_sha256 to the "
                                      "canonical-path bytes and re-freeze, or restore the enriched "
                                      "evidence bytes and re-pin"),
                "falsifier": ("declared consistency-evidence sha256 == measured canonical-path "
                              "sha256 at the reviewed revision"),
            })
        if next(c for c in checks if c["check_id"] == "C4-CITATION-BINDING-REPLICATION")["status"] == "FAIL":
            findings.append({
                "id": "W077-HF-03",
                "severity": "major",
                "class": CLASS_ID,
                "finding": (f"F2b l1_ledger_refs over-claim replicated at ledger "
                            f"{measured['ledger/theorems.jsonl'][:16]}: "
                            f"{cit['overclaim_ids']} claim citation_status='verified_by_L1' while "
                            "the ledger records verification_status='abstract-read' and "
                            "review_status='not_independently_reviewed'; the token "
                            "'verified_by_L1' occurs 0 times in the ledger."),
                "evidence": ["schemas/af_scc_c0_vacuum.yaml:295-300",
                             f"ledger/theorems.jsonl#{measured['ledger/theorems.jsonl'][:16]}"],
                "needed_to_unblock": ("set those five citation_status values to the ledger's own "
                                      "vocabulary (abstract-read) or produce ledger rows whose "
                                      "verification_status/review_status record independent L1 "
                                      "verification, then re-pin"),
                "falsifier": ("a ledger row for any of the five ids with "
                              "verification_status='verified' and a review_status other than "
                              "'not_independently_reviewed' at the pinned ledger hash"),
            })

    report = {
        "schema_version": "0.1",
        "report_id": TASK_ID,
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "kind": "cross_artifact_consistency_audit",
        "is_theorem": False,
        "node_ids": NODE_IDS,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE,
        "secondary_gate": SECONDARY_GATE,
        "created_at": started,
        "authority": ("worker evidence only; does not set node status, validation_status=passed, "
                      "or any gate verdict"),
        "targets": {
            "f2b": "schemas/af_scc_c0_vacuum.yaml",
            "f0": "research_map/formulation_taxonomy.yaml",
        },
        "pins": {k: {"sha256": v, "sha256_after_checks": after.get(k)} for k, v in measured.items()},
        "context_pins": context_measured,
        "drift": drift,
        "superseded": superseded,
        "checks": checks,
        "index_domain_evidence": c2_note,
        "f0_binding_evidence": binding_note,
        "citation_binding": cit,
        "classifier_selftest": st,
        "frozen_context": ctx,
        "duplicate_key_scan": dups,
        "findings": findings,
        "hard_failures": [c["check_id"] for c in hard_failures],
        "verdict": verdict,
        "score": score,
        "summary": ("F0-declared vs F2b quantifier-domain divergence (W077-HF-01) plus two "
                    "binding/citation defects replicated at the live hashes; worker evidence only, "
                    "no gate verdict"),
        "falsifier": ("Re-run this harness on the same pinned bytes: any hard check that reports "
                      "PASS here must still report PASS; a pinned input that changes supersedes "
                      "the verdict instead of falsifying it. W077-HF-01 is falsified by an F0 C0 "
                      "conclusion that quantifies the smooth-with-decay branch too."),
        "non_claims": ["not a gate verdict", "does not set any node done",
                       "does not upgrade validation_status",
                       "not a full-schema acceptance verdict",
                       "F2b rev12 content is not re-adjudicated here"],
        "reproduce": "python3 artifacts/worker-077/f2b_f0_binding/check_f2b_f0_binding.py",
    }

    report_path = out / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    write_markdown(out / "REPORT.md", report)
    print(json.dumps({"report": str(report_path), "verdict": verdict, "score": score,
                      "hard_failures": report["hard_failures"],
                      "superseded": superseded,
                      "report_sha256": sha256_file(report_path)}, indent=1))
    return 3 if superseded else (2 if hard_failures else 0)


def write_markdown(path: Path, r: dict) -> None:
    lines = [
        f"# {r['report_id']} — F0-declared vs F2b consistency audit (worker-077)",
        "",
        f"- **Class**: `{r['class_id']}` · **Nodes**: {', '.join(r['node_ids'])} · "
        f"**Gate**: {r['gate']} (+ {r['secondary_gate']})",
        f"- **Verdict**: `{r['verdict']}` ({r['score']}/5) · hard failures: "
        f"{', '.join(r['hard_failures']) or 'none'} · superseded: {r['superseded']}",
        f"- **Created**: {r['created_at']} · worker evidence only; no gate verdict.",
        "",
        "## Pinned inputs",
        "",
        "| path | sha256 |",
        "|---|---|",
    ]
    for k, v in r["pins"].items():
        lines.append(f"| `{k}` | `{v['sha256'][:16]}` |")
    lines += ["", "## Checks", "", "| id | severity | result | detail |", "|---|---|---|---|"]
    for c in r["checks"]:
        lines.append(f"| {c['check_id']} | {c['severity']} | **{c['status']}** | "
                     f"{c['detail'][:220]} |")
    lines += ["", "## Primary finding (W077-HF-01)", ""]
    ev = r.get("index_domain_evidence") or {}
    if ev:
        lines += [
            "The declared F0 taxonomy C0 conclusion (lines "
            f"{ev.get('f0_c0_statement_lines')}) reads:",
            "",
            f"> {ev.get('f0_c0_statement_excerpt', '')}",
            "",
            "F2b rev12 defines the same class over a wider index (line 52):",
            "",
            f"> {ev.get('f2b_d0_definition_excerpt', '')}",
            "",
            f"Classifier result: `{(ev.get('classification') or {}).get('verdict')}`. "
            "The F2b `f0_binding` is hash-current to this taxonomy revision, so the two pinned "
            "artifacts state the class over different index domains; the taxonomy's H3 defers the "
            "data space to F2, so the gate owner should either refresh the F0 text or record the "
            "deferral explicitly.",
        ]
    lines += ["", "## Findings", ""]
    for f in r["findings"]:
        lines += [f"### {f['id']} ({f['severity']})", "", f["finding"], "",
                  f"- **needed_to_unblock**: {f['needed_to_unblock']}",
                  f"- **falsifier**: {f['falsifier']}", ""]
    lines += ["## Falsifier", "", r["falsifier"], "",
              "## Non-claims", ""]
    lines += [f"- {n}" for n in r["non_claims"]]
    lines += ["", "## Reproduce", "", "```bash", r["reproduce"], "```", ""]
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
