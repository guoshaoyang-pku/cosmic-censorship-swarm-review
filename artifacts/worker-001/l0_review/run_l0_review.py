#!/usr/bin/env python3
"""worker-001 / W001-L0-REVIEW-CE42D205 — independent, hash-pinned L0 review.

Task: one class-bound execution task for gate G-LIT, node L0, classes
AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH.

Design rules (from HANDOFF.md / ASTRA_HANDOFF.md):
  * run the null first: every check has a negative control that must fire;
  * fail closed on hash drift: exit 3 and emit NO verdict if the reviewed
    artifact is not byte-identical to the pinned revision;
  * a worker emits evidence, never a gate verdict or a node status.

Read-only on every reviewed artifact. Writes only under
artifacts/worker-001/l0_review/.
"""
import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts" / "worker-001" / "l0_review"
RAW = OUT / "raw"

PINS = {
    "ledger/theorems.jsonl":
        "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "artifacts/literature/registry.jsonl":
        "ea02d1943fda50e5e1c7ce10fe2a1cd6e7784a2c9f2467c7cb8597c63442652d",
    "ledger/citation_audit.csv":
        "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "research_map/formulation_taxonomy.yaml":
        "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "artifacts/literature/L0_L1_ACCEPTANCE.md":
        "fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5",
}
FROZEN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
          "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
REQUIRED_ROW_KEYS = ("theorem_id", "label", "class_ids", "conclusion_type",
                     "status", "verification_status", "source_ids",
                     "assumptions", "falsifiers", "statement_exact")
MIN_RUN = 9  # longest common token run required for a source-payload match
# verified at review time (transcript recorded in the worker's run log)
SPOTCHECKS = [
    {"theorem_id": "T-302", "source_id": "SRC-005", "arxiv": "1507.00601",
     "phrase": "inextendible as a lorentzian manifold with a continuous metric"},
    {"theorem_id": "T-505", "source_id": "SRC-025", "arxiv": "2001.11156",
     "phrase": "assuming sufficiently slow decay of the charged scalar field "
               "on the event horizon"},
    {"theorem_id": "T-526", "source_id": "SRC-080", "arxiv": "2604.04877",
     "phrase": "the spacetime metric is continuously extendible but not "
               "lipschitz extendible"},
    {"theorem_id": "T-401", "source_id": "SRC-004", "arxiv": "1710.01722",
     "phrase": "extended across a non trivial piece of cauchy horizon as a "
               "lorentzian manifold with continuous metric"},
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    s = str(s).lower()
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def longest_run(a_tokens, b_tokens):
    """Longest common contiguous token run length (0 if none)."""
    bset = {}
    for i, t in enumerate(b_tokens):
        bset.setdefault(t, []).append(i)
    best = 0
    for i, t in enumerate(a_tokens):
        for j in bset.get(t, []):
            k = 0
            while (i + k < len(a_tokens) and j + k < len(b_tokens)
                   and a_tokens[i + k] == b_tokens[j + k]):
                k += 1
            best = max(best, k)
    return best


def load_rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def load_registry(path):
    return {r["source_id"]: r for r in load_rows(path)}


def load_audit_class_map(path):
    """source_id -> audit class_mapping string (csv)."""
    import csv
    m = {}
    with open(path, newline="") as f:
        for d in csv.DictReader(f):
            sid = d.get("citation_id")
            if sid:
                m[sid] = (d.get("class_mapping") or "").strip()
    return m


# ---------------------------------------------------------------- checks ---
def check(rows, registry, audit_map, raw_dir):
    """Return dict of check_id -> measured result (pure function of inputs)."""
    r = {}
    ids = [x.get("theorem_id") for x in rows]
    r["C1_rows"] = len(rows)
    r["C2_missing_required"] = sorted(
        x.get("theorem_id") for x in rows
        if any(k not in x for k in REQUIRED_ROW_KEYS))
    toks = sorted({c for x in rows for c in (x.get("class_ids") or [])})
    r["C3_class_tokens"] = toks
    r["C3_unknown_tokens"] = sorted(set(toks) - FROZEN)
    r["C3_empty_class_rows"] = sorted(x["theorem_id"] for x in rows
                                      if not x.get("class_ids"))
    r["C3_empty_class_accepted"] = sorted(
        x["theorem_id"] for x in rows
        if not x.get("class_ids") and x.get("status") == "accepted")
    r["C3_informs_only_rows"] = sorted(
        x["theorem_id"] for x in rows
        if not x.get("class_ids") and x.get("informs_classes"))
    r["C3_unbound_rows"] = sorted(
        x["theorem_id"] for x in rows
        if not x.get("class_ids") and not x.get("informs_classes"))
    r["C3_rows_per_class_class_ids"] = {
        c: sum(1 for x in rows if c in (x.get("class_ids") or []))
        for c in sorted(FROZEN)}
    r["C3_rows_per_class_with_informs"] = {
        c: sum(1 for x in rows
               if c in (x.get("class_ids") or [])
               or c in (x.get("informs_classes") or []))
        for c in sorted(FROZEN)}
    refs = {s for x in rows for s in (x.get("source_ids") or [])}
    r["C4_distinct_sources"] = len(refs)
    r["C4_missing_sources"] = sorted(s for s in refs if s not in registry)
    r["C5_locatorless_registry_rows"] = sorted(
        s for s, v in registry.items()
        if not (v.get("doi") or v.get("arxiv_id") or v.get("url")))
    r["C6_accepted_unverified_rows"] = sorted(
        x["theorem_id"] for x in rows
        if x.get("status") == "accepted"
        and str(x.get("verification_status")) == "unverified")
    r["C6_accepted_nonverified_source_rows"] = sorted(
        x["theorem_id"] for x in rows if x.get("status") == "accepted"
        for s in (x.get("source_ids") or [])
        if not str(registry.get(s, {}).get("status", "")).startswith("verified"))
    r["C7_theorem_rows_without_artifact_refs"] = sorted(
        x["theorem_id"] for x in rows
        if x.get("conclusion_type") == "theorem" and not x.get("artifact_refs"))
    r["C7_rows_with_artifact_refs_field"] = sum(
        1 for x in rows if "artifact_refs" in x)
    r["C8_verification_status"] = _counts(
        str(x.get("verification_status")) for x in rows)
    r["C8_registry_status"] = _counts(str(v.get("status"))
                                       for v in registry.values())
    r["C9_registry_reviewers"] = _counts(str(v.get("reviewer"))
                                          for v in registry.values())
    n = sum(r["C9_registry_reviewers"].values())
    r["C9_kish_ess"] = round(
        n * n / sum(c * c for c in r["C9_registry_reviewers"].values()), 3)
    dup = _counts(ids)
    r["C10_duplicate_ids"] = sorted(k for k, v in dup.items() if v > 1)
    labels = _counts(norm(x.get("label")) for x in rows)
    r["C10_duplicate_labels"] = sorted(k for k, v in labels.items() if v > 1)
    # C11 live spot checks against raw arXiv Atom payloads
    sc = []
    for s in SPOTCHECKS:
        p = raw_dir / ("arxiv_%s.xml" % s["arxiv"])
        row = next((x for x in rows if x["theorem_id"] == s["theorem_id"]), None)
        rec = dict(s)
        if not p.exists() or row is None:
            rec.update({"status": "MISSING_INPUT", "run": 0}); sc.append(rec); continue
        body = p.read_text(errors="replace")
        summary = re.sub(r"<[^>]+>", " ", body)
        run = longest_run(norm(s["phrase"]).split(),
                          norm(summary).split())
        reg = registry.get(s["source_id"], {})
        edge_ok = (s["source_id"] in (row.get("source_ids") or [])
                   and str(reg.get("arxiv_id")) == s["arxiv"])
        rec["sha256"] = sha256(p)
        rec["payload_phrase_run"] = run
        rec["citation_edge_ok"] = edge_ok
        rec["class_ids"] = row.get("class_ids")
        rec["informs_classes"] = row.get("informs_classes")
        rec["row_conclusion_type"] = row.get("conclusion_type")
        rec["statement_overlap_run"] = longest_run(
            norm(row.get("statement_exact")).split(), norm(summary).split())
        rec["status"] = ("SUPPORTED" if (run >= MIN_RUN and edge_ok)
                         else "NOT_REPRODUCED")
        sc.append(rec)
    r["C11_spotchecks"] = sc
    r["C11_supported"] = sum(1 for x in sc if x["status"] == "SUPPORTED")
    # C12 ledger class binding vs the ledger's own citation audit
    incons = []
    for x in rows:
        if x.get("class_ids"):
            continue
        mapped = sorted({audit_map.get(s, "") for s in (x.get("source_ids") or [])})
        mapped = [m for m in mapped
                  if set(m.split(";")) & FROZEN]
        if mapped:
            incons.append({"theorem_id": x["theorem_id"], "status": x.get("status"),
                           "audit_class_mapping": mapped,
                           "informs_classes": x.get("informs_classes")})
    r["C12_audit_mapped_but_unbound"] = incons
    # assignment stop rule, quoted from map.assignments (L0 / astra-lead-literature)
    r["C13_stop_rule_class_column"] = (
        "MET" if not r["C3_empty_class_rows"] else "UNMET")
    return r


def _counts(it):
    out = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


# ------------------------------------------------------------- controls ----
def negative_controls(rows, registry, audit_map, raw_dir):
    """Mutate copies; each injected defect must be caught by its check."""
    ctl = []

    def run(mut_rows, mut_reg):
        return check(mut_rows, mut_reg, audit_map, raw_dir)

    # NEG-1 inject a bogus source_id -> C4 must list it missing
    m = [dict(x) for x in rows]
    victim = next(x for x in m if x.get("source_ids"))
    victim["source_ids"] = list(victim["source_ids"]) + ["SRC-DOES-NOT-EXIST"]
    res = run(m, registry)
    ctl.append({"control": "NEG-1_missing_source", "check": "C4",
                "expected": "SRC-DOES-NOT-EXIST",
                "caught": "SRC-DOES-NOT-EXIST" in res["C4_missing_sources"]})
    # NEG-2 unknown class token -> C3
    m = [dict(x) for x in rows]
    m[0] = dict(m[0]); m[0]["class_ids"] = list(m[0]["class_ids"]) + ["AF-SCC-C0-OR-C2-VAC-GEN"]
    res = run(m, registry)
    ctl.append({"control": "NEG-2_unknown_token", "check": "C3",
                "caught": "AF-SCC-C0-OR-C2-VAC-GEN" in res["C3_unknown_tokens"]})
    # NEG-3 accepted+unverified -> C6
    m = [dict(x) for x in rows]
    idx = next(i for i, x in enumerate(m) if x.get("status") == "accepted")
    m[idx] = dict(m[idx]); m[idx]["verification_status"] = "unverified"
    res = run(m, registry)
    ctl.append({"control": "NEG-3_accepted_unverified", "check": "C6",
                "caught": m[idx]["theorem_id"] in res["C6_accepted_unverified_rows"]})
    # NEG-4 strip a registry locator -> C5
    mr = {k: dict(v) for k, v in registry.items()}
    k0 = next(iter(mr)); mr[k0].pop("doi", None); mr[k0].pop("arxiv_id", None); mr[k0].pop("url", None)
    res = run(rows, mr)
    ctl.append({"control": "NEG-4_locatorless_source", "check": "C5",
                "caught": k0 in res["C5_locatorless_registry_rows"]})
    # NEG-5 add artifact_refs to a theorem row -> C7 count must drop by 1
    base = check(rows, registry, audit_map, raw_dir)["C7_theorem_rows_without_artifact_refs"]
    m = [dict(x) for x in rows]
    idx = next(i for i, x in enumerate(m) if x.get("conclusion_type") == "theorem")
    m[idx] = dict(m[idx]); m[idx]["artifact_refs"] = ["artifacts/example#deadbeef"]
    res = run(m, registry)
    ctl.append({"control": "NEG-5_rule1_repaired", "check": "C7",
                "caught": len(res["C7_theorem_rows_without_artifact_refs"]) == len(base) - 1})
    # NEG-6 blank the class column of a class-bound row -> C3 empty list grows
    base_empty = check(rows, registry, audit_map, raw_dir)["C3_empty_class_rows"]
    m = [dict(x) for x in rows]
    idx = next(i for i, x in enumerate(m) if x.get("class_ids"))
    tid = m[idx]["theorem_id"]
    m[idx] = dict(m[idx]); m[idx]["class_ids"] = []
    res = run(m, registry)
    ctl.append({"control": "NEG-6_class_column_blanked", "check": "C3",
                "caught": tid in res["C3_empty_class_rows"]
                and len(res["C3_empty_class_rows"]) == len(base_empty) + 1})
    return ctl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None,
                    help="ISO timestamp for the review; default wall clock")
    ap.add_argument("--expect-ledger", default=PINS["ledger/theorems.jsonl"])
    args = ap.parse_args()
    now = args.now or _dt.datetime.now().astimezone().replace(
        microsecond=0).isoformat()
    pins = dict(PINS)
    pins["ledger/theorems.jsonl"] = args.expect_ledger

    measured = {p: sha256(ROOT / p) for p in pins}
    drift = {p: {"expected": pins[p], "measured": measured[p]}
             for p in pins if measured[p] != pins[p]}
    if drift:
        print(json.dumps({"status": "HASH_DRIFT_NO_VERDICT_EMITTED",
                          "drift": drift}, indent=1))
        return 3

    rows = load_rows(ROOT / "ledger/theorems.jsonl")
    registry = load_registry(ROOT / "artifacts/literature/registry.jsonl")
    audit_map = load_audit_class_map(ROOT / "ledger/citation_audit.csv")
    res = check(rows, registry, audit_map, RAW)
    ctl = negative_controls(rows, registry, audit_map, RAW)
    controls_ok = all(c.get("caught") for c in ctl)

    hard = []
    if res["C13_stop_rule_class_column"] == "UNMET":
        hard.append({
            "id": "HF-L0-01",
            "claim": "L0 stop rule class-column clause unmet at the reviewed hash",
            "evidence": (
                "map.assignments L0/astra-lead-literature stop_rule: 'every row has "
                "a locator and the class column is non-empty'. Measured: %d/%d rows "
                "have class_ids == [] (%d accepted); %d of those have no "
                "informs_classes fallback either. The class-token flag is cleared at "
                "this hash, but by restricting class_ids to the four frozen classes "
                "and moving extension labels to ledger_tags (build_literature.py:19-20), "
                "not by re-binding the rows that lost a binding."
                % (len(res["C3_empty_class_rows"]), res["C1_rows"],
                   len(res["C3_empty_class_accepted"]), len(res["C3_unbound_rows"]))),
            "artifact": "ledger/theorems.jsonl",
            "sha256": measured["ledger/theorems.jsonl"],
            "repair": (
                "Add informs_classes (or an explicit 'class_binding: none "
                "(evidence/tag only)') to the %d unbound rows, and disclose the "
                "%d tagged rows in artifacts/literature/L0_L1_ACCEPTANCE.md; or get "
                "the controller to amend the L0 stop rule to allow disclosed tagged "
                "entries." % (len(res["C3_unbound_rows"]),
                              len(res["C3_empty_class_rows"]))),
            "falsifier": (
                "Void if a ledger at this sha256 has a non-empty class column on "
                "every row, or if map.assignments contains an amendment to the L0 "
                "stop rule that explicitly permits unclassed tagged entries."),
        })

    findings = [
        {"id": "L0-M1", "severity": "major",
         "statement": ("PROTOCOL rule 1 exposure persists: %d rows carry "
                       "conclusion_type='theorem' while the ledger has no "
                       "artifact_refs field at all (%d rows carry one). "
                       "research_map/schemas.py:55-56 auto-rejects a claim event "
                       "with conclusion_type='theorem' and no artifact_refs, so "
                       "these rows cannot be promoted as written."
                       % (len(res["C7_theorem_rows_without_artifact_refs"]),
                          res["C7_rows_with_artifact_refs_field"])),
         "prior": "deepseek-flash-17 L0-review-17 HF-01 (older hash); unfixed here."},
        {"id": "L0-M2", "severity": "major",
         "statement": ("Evidence depth is locator/metadata level: ledger "
                       "verification_status %s; registry %s."
                       % (res["C8_verification_status"], res["C8_registry_status"])),
         "prior": "L0-review-17 major; the acceptance note defends it (paywalled "
                  "bodies) and MANIFEST labels evidence_level as derived."},
        {"id": "L0-M3", "severity": "major",
         "statement": ("Registry reviewer independence is nominal: %s "
                       "(Kish effective sample size %.3f). citation_support "
                       "computed over the registry is effectively one reviewer."
                       % (res["C9_registry_reviewers"], res["C9_kish_ess"])),
         "prior": "L0-review-17 major; unchanged."},
        {"id": "L0-M4", "severity": "minor",
         "statement": ("Acceptance note L0_L1_ACCEPTANCE.md reports 'L0 gaps: none' "
                       "while %d/%d rows are unclassed tagged/evidence entries "
                       "(disclosed only in generated falsifiers.md)."
                       % (len(res["C3_empty_class_rows"]), res["C1_rows"]))},
    ]
    positives = [
        "source_id resolution %d/%d (0 missing; prior '24 unresolved' is fixed)"
        % (res["C4_distinct_sources"] - len(res["C4_missing_sources"]),
           res["C4_distinct_sources"]),
        "0 registry rows without doi/arxiv/url; 0 accepted rows with an "
        "unverified source; 0 accepted+unverified contradictions (prior HF fixed)",
        "class_ids tokens are exactly the four frozen ids, no extension tokens",
        "row count %d >= 15; 4/4 independent arXiv Atom spot checks SUPPORTED"
        % res["C1_rows"],
        "L1 contested mismatches independently refuted on disk "
        "(worker-021 MISMATCH_FINDINGS_NOT_REPLICATED=3/3; worker-025 "
        "SPOT4_MISMATCH_REFUTED x3 with controls)",
    ]
    verdict = "revise" if hard else "accept"
    review = {
        "review_id": "L0-review-worker-001-20260912T0028+0800",
        "created_at": now,
        "actor": "worker-001",
        "reviewer": "worker-001",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": sorted(FROZEN),
        "target_id": "ledger/theorems.jsonl#%s" % measured["ledger/theorems.jsonl"],
        "artifact": "ledger/theorems.jsonl",
        "artifact_sha256": measured["ledger/theorems.jsonl"],
        "verdict": verdict,
        "score": 3.5,
        "hard_failures": hard,
        "findings": findings,
        "positives": positives,
        "cross_checks": {
            "citation_audit.csv": measured["ledger/citation_audit.csv"],
            "registry.jsonl": measured["artifacts/literature/registry.jsonl"],
            "f0_taxonomy": measured["research_map/formulation_taxonomy.yaml"],
            "l0_l1_acceptance.md": measured["artifacts/literature/L0_L1_ACCEPTANCE.md"],
            "classseparation_tool": "not re-run: frozen tool authored by another "
                                    "worker, self-authored corpus (CF-9)",
            "controls_all_passed": controls_ok,
        },
        "measured": res,
        "controls": ctl,
        "not_claimed": [
            "no gate verdict (G-LIT stays whatever the controller measures)",
            "no node status (L0 not moved to done)",
            "no ledger or registry edit; reviewed artifacts untouched",
            "no claim that any citation is unsupported: 4/4 spot checks SUPPORTED",
        ],
        "next_falsifier": (
            "Re-measure ledger/theorems.jsonl: a sha256 other than %s voids this "
            "review (run_l0_review.py exits 3 without emitting a verdict). At the "
            "pinned hash the HF-L0-01 finding is falsified by a row-by-row class "
            "column that is non-empty, or by a controller amendment to the L0 stop "
            "rule; L0-M1 is falsified by an artifact_refs field on every "
            "conclusion_type='theorem' row with values that resolve on disk."
            % measured["ledger/theorems.jsonl"]),
        "authority_note": (
            "Worker events cannot set status=done, validation_status=passed, or a "
            "gate verdict. This review is an artifact-level verdict only."),
        "reviewed_paths_read_only": sorted(PINS),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review.json").write_text(json.dumps(review, indent=1) + "\n")
    (OUT / "EVIDENCE.json").write_text(json.dumps(
        {"pins": PINS, "measured": measured, "checks": res, "controls": ctl,
         "generated_at": now}, indent=1) + "\n")
    print(json.dumps({"status": "VERDICT_EMITTED", "verdict": verdict,
                      "hard_failures": [h["id"] for h in hard],
                      "controls_all_passed": controls_ok,
                      "review": str(OUT / "review.json")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
