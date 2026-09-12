#!/usr/bin/env python3
"""W022-F2B-REV14-LANDING-PREFLIGHT-01 (worker-022, class AF-SCC-C0-VAC-GEN, node F2b).

Read-only preflight for an atomic rev14 landing of the two confirmed F2b containment
defects at the live rev13 pins. It:

  1. re-measures every declared pin and both live repair candidates (worker-022 A,
     worker-066 B reconstructed from the published diff);
  2. re-runs the pinned structural gate and the class-separation detector on each
     candidate (frozen c266dbec and live a8c04fc3 detector hashes both reported);
  3. evaluates independently implemented defect detectors D1 (inverted size premise
     against the file's own containment chain) and D2 (live containment denial) and
     builds the per-reviewer blocking-carrier closure matrix at b2ab6acb;
  4. recomputes the full FROZEN rev30 draft against the repaired bytes using
     regenerate_frozen.py's own key lists, and checks that only the two C0 entries move;
  5. enumerates the derived-evidence regeneration obligations created by the landing;
  6. runs five pre-registered controls.

Nothing canonical is written. Outputs live only under this directory plus the
worker-022 outbox / checkpoint. Run: python3 preflight.py
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(rel_or_path) -> str:
    p = Path(rel_or_path)
    p = p if p.is_absolute() else ROOT / p
    return sha_bytes(p.read_bytes())


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text()


def run_gate(path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"), "--json", str(path)],
        capture_output=True, text=True, timeout=300,
    )
    rep = {}
    out = proc.stdout
    if "{" in out:
        try:
            rep = json.loads(out[out.index("{"):])
        except ValueError:
            rep = {}
    return {
        "exit": proc.returncode,
        "verdict": rep.get("verdict", "no_verdict"),
        "failed_rules": rep.get("failed_rules", []),
        "accepted": proc.returncode == 0 and str(rep.get("verdict", "")).lower() == "pass",
        "stderr_tail": proc.stderr.strip()[-200:],
    }


_CLASSSEP_CACHE: dict = {}


def classsep_findings(detector_rel: str, text: str, where: str) -> list:
    if detector_rel not in _CLASSSEP_CACHE:
        spec = importlib.util.spec_from_file_location(
            "cs_" + sha(detector_rel)[:12], ROOT / detector_rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CLASSSEP_CACHE[detector_rel] = mod
    return _CLASSSEP_CACHE[detector_rel].findings_for_text(text, where)


# ---------------------------------------------------------------- defect detectors

def load_doc(text: str) -> dict:
    return yaml.safe_load(text)


def containment_direction(doc: dict) -> dict:
    chain = doc.get("implication_ledger", {}).get("extension_class_containment", "")
    toks = ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
    pos = {t: chain.find(t) for t in toks}
    present = all(p >= 0 for p in pos.values())
    ordered = present and pos["E_C0"] < pos["E_H2loc"] < pos["E_{C^1,1}"] < pos["E_C2"]
    reversed_ = present and pos["E_C2"] < pos["E_{C^1,1}"] < pos["E_H2loc"] < pos["E_C0"]
    # E_C2 innermost (last) => smallest extension set; reversed chain => E_C2 largest.
    expected = "smaller" if ordered else ("larger" if reversed_ else "undefined")
    return {"chain": chain, "tokens_present": present, "ordered": ordered,
            "reversed": reversed_, "expected_c2_size": expected}


def detect_d1(text: str) -> dict:
    """D1: forbidden-transfer size premise contradicts the file's own containment chain."""
    doc = load_doc(text)
    row = doc.get("implication_ledger", {}).get("forbidden_transfers", [{}])[0]
    reason = str(row.get("reason", ""))
    d = containment_direction(doc)
    claims_larger = bool(re.search(r"strictly\s+larger|is\s+a\s+strictly\s+larger", reason))
    claims_smaller = bool(re.search(r"strictly\s+smaller|is\s+strictly\s+smaller|subset", reason))
    fires = d["expected_c2_size"] == "smaller" and claims_larger and not claims_smaller
    fires = fires or (d["expected_c2_size"] == "larger" and claims_smaller)
    return {"fires": bool(fires), "reason": reason[:220],
            "expected_c2_size": d["expected_c2_size"], "chain_ordered": d["ordered"],
            "chain_reversed": d["reversed"], "claims_larger": claims_larger,
            "claims_smaller": claims_smaller}


def detect_d2(text: str) -> dict:
    """D2: live (non-withdrawn) containment denial in regularity.must_not_conflate[0].

    Bracketed correction segments ([...]) are treated as withdrawn/quoted, not asserted;
    the naive variant is reported alongside so the mention-vs-assertion gap is measured.
    """
    doc = load_doc(text)
    items = doc.get("regularity", {}).get("must_not_conflate", []) or []
    denial = re.compile(r"no\s+containment\s+with", re.I)
    per_item_naive = [bool(denial.search(str(x))) for x in items]
    per_item_aware = [bool(denial.search(re.sub(r"\[[^\]]*\]", "", str(x)))) for x in items]
    return {"fires": bool(per_item_aware and per_item_aware[0]),
            "fires_naive": bool(per_item_naive and per_item_naive[0]),
            "per_item": per_item_aware, "per_item_naive": per_item_naive,
            "first_item": str(items[0])[:220] if items else ""}


def chain_ranks(doc: dict) -> dict:
    """Rank 0 = largest extension set (E_C0) .. last = smallest, from the file's own chain."""
    chain = doc.get("implication_ledger", {}).get("extension_class_containment", "")
    toks = ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
    pos = {t: chain.find(t) for t in toks}
    if not all(p >= 0 for p in pos.values()):
        return {}
    return {t: i for i, t in enumerate(sorted(toks, key=lambda t: pos[t]))}


def reviewer_predicates(text: str) -> dict:
    """Re-implement the documented blocking predicates of the six live F2b reviewers.

    Types: naive_substring (fires on any occurrence, including quoted/withdrawn mentions),
    order_relative (fires only if the stated size relation contradicts the file's chain),
    mention_aware (bracketed corrections stripped before the search).
    """
    doc = load_doc(text)
    mnc = doc.get("regularity", {}).get("must_not_conflate", []) or []
    fts = doc.get("implication_ledger", {}).get("forbidden_transfers", []) or []
    h2_row = str(mnc[0]) if mnc else ""
    h1_row = str(fts[0].get("reason", "")) if fts else ""
    reason = h1_row
    ranks = chain_ranks(doc)
    m = re.search(r"strictly\s+(larger|smaller)\s+extension\s+class", reason)
    c10_fires = False
    if m and ranks:
        claimed_larger = m.group(1) == "larger"          # from = C2, to = this class (C0)
        c10_fires = (claimed_larger and ranks["E_C2"] > ranks["E_C0"]) or \
                    ((not claimed_larger) and ranks["E_C2"] < ranks["E_C0"])
    return {
        "w017-CHK-09": {"fires": "strictly larger extension class" in h1_row,
                        "type": "naive_substring",
                        "source": "artifacts/worker-017/f2b_rev13_containment/verify.py:203"},
        "w017-CHK-10": {"fires": "No containment with C2 or C0 is asserted here" in h2_row,
                        "type": "naive_substring",
                        "source": "artifacts/worker-017/f2b_rev13_containment/verify.py:213"},
        "w018-B1": {"fires": any("No containment with C2 or C0 is asserted here" in str(s) for s in mnc),
                    "type": "naive_substring",
                    "source": "artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py:194"},
        "w018-B2": {"fires": any("strictly larger extension class" in str(r.get("reason", "")) for r in fts),
                    "type": "naive_substring",
                    "source": "artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py:204"},
        "w053-C10": {"fires": bool(c10_fires), "type": "order_relative",
                     "source": "artifacts/worker-053/f2b_rev29_review/check_f2b_rev29.py:412-463"},
        "w066-H1": {"fires": bool(c10_fires), "type": "order_relative",
                    "source": "artifacts/worker-066/f2b_rev29_containment_binding/rebind.py:104-140"},
        "w066-H2": {"fires": bool(re.search(r"No\s+containment\s+with\s+.{0,80}?\s+is\s+asserted",
                                            re.sub(r"\[[^\]]*\]", "", h2_row), re.I)),
                    "type": "mention_aware",
                    "source": "artifacts/worker-066/f2b_rev29_containment_binding/rebind.py:150-160"},
        "normalized_ci_denial": {
            "fires": bool(re.search(r"no\s+containment\s+with\s+.{0,80}?\s+is\s+asserted", h2_row, re.I)),
            "type": "case_insensitive_normalized_probe",
            "source": "not a reviewer instrument; sensitivity probe (case-insensitive matcher over the raw slot)"},
    }


def detector_live(text: str) -> dict:
    return {"D1": detect_d1(text), "D2": detect_d2(text)}


def asserts_chain(bullet: str) -> bool:
    return ("E_C2" in bullet and "E_C0" in bullet
            and ("contains" in bullet or "subset" in bullet))


# ---------------------------------------------------------------- FROZEN rev30 draft

CANONICAL = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
PIN_EXTRAS = [
    "artifacts/formulation/reviews/BN_TRIAGE.md",
    "artifacts/formulation/evidence/bn_triage.json",
    "artifacts/formulation/evidence/variant_registry_check.json",
    "artifacts/formulation/evidence/variant_delta_check.json",
    "artifacts/formulation/tools/regenerate_frozen.py",
    "schemas/taxonomy_cases.jsonl",
    "schemas/f1_falsifier_tests.jsonl",
    "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json",
    "artifacts/formulation/tools/evidence_binding_repair_rev29.py",
    "artifacts/formulation/evidence/variant_rebase_rev29_report.json",
    "artifacts/formulation/tools/variant_rebase_rev29.py",
]
VOLATILE = ["artifacts/formulation/evidence/aggregator_pin_check_rev3.json"]
C0_RELS = ["schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]


def frozen_draft(label: str, candidate_bytes: bytes, revision: int = 30) -> dict:
    man = json.loads(read_text("artifacts/formulation/FROZEN.json"))
    files = dict(man["files"])
    dropped = [r for r in VOLATILE if r in files]
    for r in dropped:
        files.pop(r, None)
    missing, added, changed = [], [], []
    for rel in list(files) + CANONICAL + PIN_EXTRAS:
        if rel in C0_RELS:
            b = candidate_bytes
        else:
            p = ROOT / rel
            if not p.exists():
                missing.append(rel)
                continue
            b = p.read_bytes()
        h = sha_bytes(b)
        if rel not in files:
            added.append(rel)
        elif files[rel]["sha256"] != h:
            changed.append({"path": rel, "rev29": files[rel]["sha256"], "draft": h})
        files[rel] = {"sha256": h, "bytes": len(b)}
    draft = dict(man)
    draft["files"] = dict(sorted(files.items()))
    draft["revision"] = revision
    # Deterministic placeholder: a draft must not carry a moving timestamp (the CF-27 hazard).
    draft["frozen_at"] = "DRAFT-NOT-PUBLISHED (worker-022 preflight; do not cite as a freeze)"
    draft["rev30_delta"] = [
        "DRAFT by worker-022 preflight (not published): rev14 F2b containment repair, "
        "candidate %s; two leaf edits (implication_ledger.forbidden_transfers[0].reason, "
        "regularity.must_not_conflate[0]); canonical + authoring mirror re-hashed." % label
    ]
    draft["_draft_meta"] = {
        "producer": "worker-022", "task_id": "W022-F2B-REV14-LANDING-PREFLIGHT-01",
        "candidate": label, "candidate_sha256": sha_bytes(candidate_bytes),
        "based_on_revision": man.get("revision"), "not_published": True,
    }
    if dropped:
        draft["_draft_meta"]["volatile_unpinned"] = dropped
    return {"draft": draft, "changed": changed, "missing": missing, "added": added,
            "n_entries": len(files), "dropped": dropped}


def draft_staleness(draft: dict, candidate_bytes: bytes) -> list:
    bad = []
    for rel in C0_RELS:
        declared = draft["files"].get(rel, {}).get("sha256")
        if declared != sha_bytes(candidate_bytes):
            bad.append({"path": rel, "declared": declared,
                        "measured": sha_bytes(candidate_bytes)})
    return bad


# ---------------------------------------------------------------- reviewer matrix

REVIEWER_BLOCKING = {
    "worker-017": {"B17-R13-01": "D1", "B17-R13-02": "D2"},
    "worker-018": {"W018-R13-F2B-B1": "D2", "W018-R13-F2B-B2": "D1"},
    "worker-035": {"HF-035-01": "D2", "HF-035-R3-01": "D2"},
    "worker-053": {"W053-F2B-REV29-01": "D1"},
    "worker-066": {"W066-R13-F2B-H1": "D2", "W066-R13-F2B-H2": "D1"},
    "worker-075": {"HF-075-F2b-LARGER": "D1", "HF-075-F2b-VOCAB": "VOCAB"},
}
NON_BLOCKING_RESIDUALS = [
    {"reviewer": "worker-017", "id": "N17-R13-03",
     "item": "f0_binding carries no class_contract_supplement_sha256 field (recommendation)",
     "disposition": "non-blocking; owner edit at a future revision, not part of the two-carrier repair"},
    {"reviewer": "worker-035", "id": "F-035-R3-02/03/04/N1",
     "item": "stale declared hashes outside the binding chain; provenance sha with no referent; revision_history ordering",
     "disposition": "non-gating collateral; reported, no schema-content change required for accept"},
    {"reviewer": "worker-053", "id": "fixture-blast-radius",
     "item": "the defective reason string is copied into the semantic-contract fixture corpus and the lead's rebased evidence trees",
     "disposition": "corpus is provenance-frozen (worker-06 copies); see derived-evidence table -- regeneration, not fixture editing, is the coherent path"},
    {"reviewer": "worker-075", "id": "SF-075-F2b-CORPUS",
     "item": "semantic-escape corpus binds a superseded C0 base; run_acceptance preflight fails closed",
     "disposition": "pre-existing stale (1bb78ce9 vs b2ab6acb); landing adds a new base value -> re-run measure_semantic_escape.py post-landing"},
    {"reviewer": "worker-019", "id": "W019-RV13-02",
     "item": "schemas/f1_falsifier_tests.jsonl binds F1 rev12 (F1-scoped, not an F2b carrier)",
     "disposition": "already tracked as lead finding L-FORM-04; out of F2b scope"},
]


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-events", action="store_true", default=False,
                    help="append status/claim/artifact events to comms/outbox/worker-022.jsonl and write the checkpoint")
    args = ap.parse_args()

    t0 = now()
    prereg = json.loads((HERE / "preregistration.json").read_text())
    declared = prereg["declared_pins"]

    pins_start = {rel: sha(rel) for rel in declared}
    pin_drift_start = {rel: {"declared": declared[rel], "measured": pins_start[rel],
                             "match": declared[rel] == pins_start[rel]}
                       for rel in declared}

    # ---- candidates
    live_text = read_text("schemas/af_scc_c0_vacuum.yaml")
    live_bytes = live_text.encode()
    d1_live, d2_live = detect_d1(live_text), detect_d2(live_text)
    live_doc = load_doc(live_text)
    live_reason = live_doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    live_bullet = live_doc["regularity"]["must_not_conflate"][0]

    cand_a_src = ROOT / prereg["candidate_sources"]["A"]["path"]
    cand_a_bytes = cand_a_src.read_bytes()
    cand_a_sha = sha_bytes(cand_a_bytes)
    (HERE / "candidate_A/af_scc_c0_vacuum.rev14.yaml").write_bytes(cand_a_bytes)

    diff_lines = []
    for line in difflib.unified_diff(live_text.splitlines(), cand_a_bytes.decode().splitlines(),
                                     lineterm="", n=0):
        if line.startswith(("---", "+++", "@@")):
            diff_lines.append(line)
        elif line.startswith(("+", "-")):
            diff_lines.append(line)
    a_changed_lines = sorted({int(re.search(r"@@ -(\d+)", l).group(1))
                              for l in diff_lines if l.startswith("@@")})

    patch = (ROOT / prereg["candidate_sources"]["B"]["source"]).read_text()
    dels = [l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
    adds = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
    assert len(dels) == len(adds) == 2, f"unexpected patch shape: {len(dels)} deletions, {len(adds)} additions"
    cand_b_text = live_text
    b_old_counts = []
    for o, n in zip(dels, adds):
        b_old_counts.append(cand_b_text.count(o))
        cand_b_text = cand_b_text.replace(o, n, 1)
    cand_b_bytes = cand_b_text.encode()
    cand_b_sha = sha_bytes(cand_b_bytes)
    (HERE / "candidate_B/af_scc_c0_vacuum.rev14.yaml").write_bytes(cand_b_bytes)

    cand_a_text = cand_a_bytes.decode()
    a_doc, b_doc = load_doc(cand_a_text), load_doc(cand_b_text)
    a_reason = a_doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    b_reason = b_doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    a_bullet = a_doc["regularity"]["must_not_conflate"][0]
    b_bullet = b_doc["regularity"]["must_not_conflate"][0]
    c2_sibling_bullet = load_doc(read_text("schemas/af_scc_c2_vacuum.yaml"))["regularity"]["must_not_conflate"][1]

    # ---- gates and class separation
    gate = {}
    sep = {}
    for label, path in (("A", HERE / "candidate_A/af_scc_c0_vacuum.rev14.yaml"),
                        ("B", HERE / "candidate_B/af_scc_c0_vacuum.rev14.yaml")):
        gate[label] = run_gate(path)
        text = path.read_text()
        sep[label] = {
            "frozen_c266": {"detector": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
                            "sha256": sha("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"),
                            "n_findings": len(classsep_findings(
                                "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
                                text, f"preflight:{label}"))},
            "live_a8c0": {"detector": "research_map/class_separation.py",
                          "sha256": sha("research_map/class_separation.py"),
                          "n_findings": len(classsep_findings("research_map/class_separation.py",
                                                              text, f"preflight:{label}"))},
        }

    # ---- FROZEN drafts
    drafts = {}
    for label, b in (("A", cand_a_bytes), ("B", cand_b_bytes)):
        fd = frozen_draft(label, b)
        fd2 = frozen_draft(label, b)
        out = HERE / f"drafts/FROZEN.rev30.{label}.draft.json"
        out.write_text(json.dumps(fd["draft"], indent=2) + "\n")
        fd["draft_file"] = str(out.relative_to(ROOT))
        fd["draft_file_sha256"] = sha(out)
        fd["draft_stale_check_on_candidate"] = draft_staleness(fd["draft"], b)
        fd["deterministic"] = json.dumps(fd["draft"], sort_keys=True) == json.dumps(fd2["draft"], sort_keys=True)
        drafts[label] = fd

    # ---- reviewer closure matrix
    closure = {}
    for reviewer, carriers in REVIEWER_BLOCKING.items():
        rows = []
        for cid, kind in carriers.items():
            row = {"reviewer": reviewer, "carrier_id": cid, "detector": kind}
            if kind == "D1":
                row.update({"closed_by_A": not detect_d1(cand_a_text)["fires"],
                            "closed_by_B": not detect_d1(cand_b_text)["fires"]})
            elif kind == "D2":
                row.update({"closed_by_A": not detect_d2(cand_a_text)["fires"],
                            "closed_by_B": not detect_d2(cand_b_text)["fires"]})
            else:  # VOCAB
                vocab = json.loads(read_text("artifacts/formulation/VOCAB_ALIASES.json"))
                rule = json.loads(read_text("artifacts/formulation/rule_spec.json"))
                f0 = load_doc(read_text("research_map/formulation_taxonomy.yaml"))
                allowed = f0["field_vocabulary"]["conclusion_type"]["allowed"]
                f0_token = f0["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["conclusion_type"]
                schema_token = a_doc["conclusion"]["conclusion_type"]
                rule_token = rule["vocabularies"]["class_conclusion_type"]["AF-SCC-C0-VAC-GEN"]
                alias_ref = rule["vocabularies"].get("aliases_ref")
                alias_canonical = schema_token in vocab.get("conclusion_type", {})
                row.update({
                    "schema_token": schema_token,
                    "f0_declared_token": f0_token, "f0_allowed": allowed,
                    "rule_spec_class_conclusion_type": rule_token,
                    "rule_spec_aliases_ref": alias_ref,
                    "rule_spec_aliases_ref_resolves": bool(alias_ref) and (ROOT / alias_ref).exists(),
                    "schema_token_is_alias_registry_canonical": alias_canonical,
                    "alias_list": vocab.get("conclusion_type", {}).get(schema_token),
                    "rule_spec_token_equals_schema_token": rule_token == schema_token,
                    "f0_allowed_contains_schema_token": schema_token in allowed,
                    "adjudication_ref": "artifacts/worker-066/f2b_vocab_binding_adjudication/report.json",
                    "adjudication_sha256": sha("artifacts/worker-066/f2b_vocab_binding_adjudication/report.json"),
                    "closed_by_A": None, "closed_by_B": None,
                    "disposition": "two canonical sources disagree on the conclusion_type token; worker-066's independent binding adjudication (13/13 checks, 10/10 controls) resolves the binding through rule_spec.vocabularies.class_conclusion_type + the frozen alias registry; the residual is a gate-owner re-stamp, not a content edit, and is NOT closed by the two-candidate repair",
                })
            rows.append(row)
        closure[reviewer] = rows

    # ---- derived-evidence impact
    ev = json.loads(read_text("artifacts/formulation/evidence/semantic_escape_rebased.json"))
    held = json.loads(read_text("artifacts/formulation/evidence/heldout_rebased.json"))
    contract = json.loads(read_text("schemas/semantic_contract_tests/manifest.json"))
    cur_base = sha("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    derived = [
        {"artifact": "artifacts/formulation/evidence/semantic_escape_rebased.json",
         "bound_base": ev.get("base_sha256"), "current_base": cur_base,
         "stale_now": ev.get("base_sha256") != cur_base,
         "effect": "run_acceptance.py preflight fails closed (exit 3) until regenerated",
         "rerun": "python3 artifacts/formulation/tools/measure_semantic_escape.py"},
        {"artifact": "artifacts/formulation/evidence/heldout_rebased.json",
         "bound_base": held.get("base_sha256"), "current_base": cur_base,
         "stale_now": held.get("base_sha256") != cur_base,
         "effect": "held-out rebase evidence binds an older C0 base",
         "rerun": "python3 artifacts/formulation/tools/rebase_heldout.py"},
        {"artifact": "artifacts/formulation/evidence/rebased_fixtures/ (60 generated files)",
         "bound_base": ev.get("base_sha256"), "current_base": cur_base,
         "stale_now": ev.get("base_sha256") != cur_base,
         "effect": "generated by measure_semantic_escape.py from the base; regenerated with it",
         "rerun": "python3 artifacts/formulation/tools/measure_semantic_escape.py"},
        {"artifact": "schemas/semantic_contract_tests/ (frozen worker-06 corpus)",
         "bound_base": contract.get("provenance", {}).get("corpus_base_sha256"),
         "current_base": cur_base,
         "stale_now": contract.get("provenance", {}).get("corpus_base_sha256") != cur_base,
         "effect": "provenance-frozen copies; mutants must not be edited (hash-verified on run); ADJ-CONTROL-STALENESS remains the lead's control-rebase-or-pin decision",
         "rerun": "python3 schemas/semantic_contract_tests/run_contract_tests.py  (after control adjudication)"},
        {"artifact": "artifacts/formulation/evidence/gate_test_report.json",
         "bound_base": None, "current_base": cur_base, "stale_now": None,
         "effect": "gate acceptance battery records canonical/control/mutant verdicts at run time",
         "rerun": "python3 artifacts/formulation/tools/run_gate_tests.py"},
    ]

    # ---- controls
    controls = []

    def add_control(cid, mutation, expectation, observed, ok):
        controls.append({"id": cid, "mutation": mutation, "expected": expectation,
                         "observed": observed, "pass": bool(ok)})

    add_control("M1", "pristine live bytes", "D1 fires and D2 fires",
                {"D1": d1_live["fires"], "D2": d2_live["fires"]},
                d1_live["fires"] and d2_live["fires"])

    m2 = cand_a_text.replace(a_reason, live_reason)
    add_control("M2", "candidate A with the line-246 repair reverted to live reason",
                "D1 fires, D2 silent",
                {"D1": detect_d1(m2)["fires"], "D2": detect_d2(m2)["fires"]},
                detect_d1(m2)["fires"] and not detect_d2(m2)["fires"])

    m3 = cand_a_text.replace(a_bullet, live_bullet)
    add_control("M3", "candidate A with the line-152 repair reverted to live denial",
                "D2 fires, D1 silent",
                {"D1": detect_d1(m3)["fires"], "D2": detect_d2(m3)["fires"]},
                detect_d2(m3)["fires"] and not detect_d1(m3)["fires"])

    chain_live = load_doc(live_text)["implication_ledger"]["extension_class_containment"]
    chain_rev = "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; (control reversal)"
    m4 = cand_a_text.replace(chain_live, chain_rev)
    add_control("M4", "candidate A with the containment chain reversed (repaired reason kept)",
                "D1 fires (chain-relative detector), D2 silent",
                {"D1": detect_d1(m4)["fires"], "D2": detect_d2(m4)["fires"]},
                detect_d1(m4)["fires"] and not detect_d2(m4)["fires"])

    m5_doc = load_doc(cand_a_text)
    m5_doc.pop("conclusion", None)
    m5_path = HERE / "controls/M5_required_key_deleted.yaml"
    m5_path.write_text(yaml.safe_dump(m5_doc, sort_keys=False, width=110))
    g5 = run_gate(m5_path)
    add_control("M5", "candidate A with the required top-level conclusion block deleted",
                "structural gate does not accept",
                {"exit": g5["exit"], "verdict": g5["verdict"], "failed_rules": g5["failed_rules"][:3]},
                not g5["accepted"])

    dup_path = HERE / "controls/O1_duplicate_key_last_wins.yaml"
    dup_path.write_text(cand_a_text + '\nclass_id: "AF-WCC-VAC-GEN"\n')
    g_dup = run_gate(dup_path)
    observations = [{
        "id": "O1",
        "mutation": "candidate A with a duplicate top-level class_id appended (last-wins value AF-WCC-VAC-GEN)",
        "observed": {"exit": g_dup["exit"], "verdict": g_dup["verdict"],
                     "failed_rules": g_dup["failed_rules"][:3]},
        "note": "The mutated document is rejected on R02/R06/R09 (class-identity/vocabulary/structure), not on a duplicate-key diagnostic: PyYAML last-wins surfaces the conflicting value through downstream rules; worker-018's own instrument adds a strict NoDupLoader. Pre-existing gate behaviour, unchanged by the repair.",
    }]

    stale_draft = copy.deepcopy(drafts["A"]["draft"])
    stale_draft["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"] = \
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
    stale_bad = draft_staleness(stale_draft, cand_a_bytes)
    add_control("M6", "FROZEN rev30 draft with the canonical C0 entry set to the superseded rev12 hash",
                "draft staleness detector fires",
                {"n_mismatches": len(stale_bad)},
                len(stale_bad) == 1)

    # ---- sibling non-collateral
    sibling = {rel: {"sha256": sha(rel), "gate": run_gate(ROOT / rel)}
               for rel in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml"]}

    # ---- reviewer-instrument predicate matrix
    rp = {"live": reviewer_predicates(live_text),
          "A": reviewer_predicates(cand_a_text),
          "B": reviewer_predicates(cand_b_text)}

    pins_end = {rel: sha(rel) for rel in declared}
    pin_drift_end = {rel: pins_end[rel] != declared[rel] for rel in declared}

    checks = {
        "C1": {"desc": "all declared pins stable start/end",
               "pass": not any(pin_drift_start[r]["match"] is False for r in declared)
                       and not any(pin_drift_end.values()),
               "drift_start": [r for r in declared if not pin_drift_start[r]["match"]],
               "drift_end": [r for r, v in pin_drift_end.items() if v]},
        "C2": {"desc": "candidate A reproduces a110f8e8 and differs from live on exactly lines 152 and 246",
               "pass": cand_a_sha == prereg["candidate_sources"]["A"]["declared_sha256"]
                       and a_changed_lines == [152, 246]
                       and list(load_doc(live_text)) == list(a_doc)
                       and not detect_d1(cand_a_text)["fires"] and not detect_d2(cand_a_text)["fires"],
               "sha256": cand_a_sha, "changed_lines": a_changed_lines},
        "C3": {"desc": "candidate B reconstructed from proposed_patch.diff reproduces 84b5d3fa",
               "pass": cand_b_sha == prereg["candidate_sources"]["B"]["declared_sha256"]
                       and b_old_counts == [1, 1]
                       and not detect_d1(cand_b_text)["fires"] and not detect_d2(cand_b_text)["fires"],
               "sha256": cand_b_sha, "old_string_occurrences": b_old_counts},
        "C4": {"desc": "A and B agree on the line-246 repair; line-152 wording differs but both assert the chain",
               "pass": a_reason == b_reason and a_bullet != b_bullet
                       and asserts_chain(a_bullet) and asserts_chain(b_bullet)
                       and not asserts_chain(live_bullet),
               "line246_identical": a_reason == b_reason,
               "line152_identical": a_bullet == b_bullet,
               "A_asserts_chain": asserts_chain(a_bullet),
               "B_asserts_chain": asserts_chain(b_bullet),
               "live_asserts_chain": asserts_chain(live_bullet),
               "B_mirrors_C2_sibling_style": ("subset of" in b_bullet and "[R2 major" in b_bullet
                                              and "ENTAILS" in b_bullet),
               "C2_sibling_bullet": c2_sibling_bullet[:220]},
        "C5": {"desc": "pinned structural gate accepts A and B",
               "pass": gate["A"]["accepted"] and gate["B"]["accepted"], "gate": gate},
        "C6": {"desc": "class-separation detector returns 0 findings on A and B (frozen and live detector hashes)",
               "pass": all(sep[l][d]["n_findings"] == 0 for l in ("A", "B")
                           for d in ("frozen_c266", "live_a8c0")), "separation": sep},
        "C7": {"desc": "D1 and D2 fire on live and are silent on both candidates",
               "pass": d1_live["fires"] and d2_live["fires"]
                       and not detect_d1(cand_a_text)["fires"] and not detect_d2(cand_a_text)["fires"]
                       and not detect_d1(cand_b_text)["fires"] and not detect_d2(cand_b_text)["fires"],
               "live": {"D1": d1_live, "D2": d2_live}},
        "C8": {"desc": "every blocking F2b carrier at b2ab6acb maps to a closed detector; residuals enumerated",
               "pass": all(r["closed_by_A"] is True and r["closed_by_B"] is True
                           for rows in closure.values() for r in rows if r["detector"] in ("D1", "D2")),
               "closure": closure, "residuals": NON_BLOCKING_RESIDUALS},
        "C9": {"desc": "FROZEN rev30 draft: 0 missing, only the two C0 entries move vs rev29, deterministic re-emit",
               "pass": all(drafts[l]["missing"] == [] and
                           sorted(c["path"] for c in drafts[l]["changed"]) == sorted(C0_RELS) and
                           drafts[l]["deterministic"]
                           for l in ("A", "B")),
               "A": {"changed": drafts["A"]["changed"], "missing": drafts["A"]["missing"],
                     "added": drafts["A"]["added"], "n_entries": drafts["A"]["n_entries"],
                     "draft_file_sha256": drafts["A"]["draft_file_sha256"]},
               "B": {"changed": drafts["B"]["changed"], "missing": drafts["B"]["missing"],
                     "added": drafts["B"]["added"], "n_entries": drafts["B"]["n_entries"],
                     "draft_file_sha256": drafts["B"]["draft_file_sha256"]}},
        "C10": {"desc": "derived-evidence regeneration obligations enumerated",
                "pass": len(derived) >= 5 and all("rerun" in d for d in derived),
                "table": derived},
        "C11": {"desc": "canonical write guard: C0 canonical/mirror, FROZEN, F0 unchanged at exit",
                "pass": not any(pin_drift_end.values()), "drift_end": pin_drift_end},
        "C12": {"desc": "reviewer-instrument predicate matrix: live bytes fire all seven documented predicates; A and B are both silent under all seven; only a case-insensitive normalized probe still sees B's quoted mention",
                "pass": all(rp["live"][k]["fires"] for k in rp["live"] if k != "normalized_ci_denial")
                        and all(not rp["A"][k]["fires"] for k in rp["A"] if k != "normalized_ci_denial")
                        and all(not rp["B"][k]["fires"] for k in rp["B"] if k != "normalized_ci_denial")
                        and rp["B"]["normalized_ci_denial"]["fires"]
                        and not rp["A"]["normalized_ci_denial"]["fires"],
                "matrix": rp,
                "reading": ("Measured, not assumed: both candidates clear every documented blocking predicate at "
                            "the live pin. B's [R2 major] correction marker preserves the sibling C2 style and "
                            "quotes the withdrawn denial in lowercase, so the case-sensitive naive substring "
                            "checks of workers 017/018 stay silent; only a case-insensitive normalized matcher "
                            "(the sensitivity probe) still sees the quoted mention in B. A removes the phrase "
                            "entirely and is silent even under that probe. The choice trades maximum "
                            "detector-robustness (A) against sibling-consistent wording (B); neither option "
                            "re-trips a documented reviewer instrument.")},
    }

    report = {
        "task_id": prereg["task_id"],
        "actor": "worker-022",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "started_at": t0,
        "finished_at": now(),
        "verdict": "REV14_LANDING_PREFLIGHT_COMPLETE" if all(c["pass"] for c in checks.values())
                   else "PREFLIGHT_FAILED",
        "checks_total": len(checks),
        "checks_pass": sum(1 for c in checks.values() if c["pass"]),
        "controls_total": len(controls),
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "pins_start": pins_start,
        "pins_end": pins_end,
        "pin_drift_end": pin_drift_end,
        "candidates": {
            "A": {"producer": "worker-022", "sha256": cand_a_sha,
                  "path": "artifacts/worker-022/f2b_rev14_landing/candidate_A/af_scc_c0_vacuum.rev14.yaml",
                  "changed_lines": a_changed_lines, "line246_reason": a_reason,
                  "line152_bullet": a_bullet},
            "B": {"producer": "worker-066", "sha256": cand_b_sha,
                  "path": "artifacts/worker-022/f2b_rev14_landing/candidate_B/af_scc_c0_vacuum.rev14.yaml",
                  "line246_reason": b_reason, "line152_bullet": b_bullet,
                  "reconstructed_from": prereg["candidate_sources"]["B"]["source"]},
            "recommendation": ("Both candidates are normatively equivalent on line 246, both pass the pinned "
                               "structural gate and class separation, and both are measured silent under all "
                               "seven documented reviewer predicates. For line 152 the difference is style and "
                               "robustness: A removes the denial phrase entirely and is silent even under a "
                               "case-insensitive normalized probe; B mirrors the corrected C2 sibling bullet "
                               "(nesting + [R2 major] marker + ENTAILS) and keeps the withdrawn denial only as a "
                               "lowercase quotation, which a normalized matcher would still see. B is the "
                               "reader-consistent choice, A the maximally detector-robust choice; the owner "
                               "decides."),
        },
        "drafts": {l: {k: v for k, v in drafts[l].items() if k != "draft"} for l in drafts},
        "gate": gate,
        "class_separation": sep,
        "sibling_non_collateral": sibling,
        "reviewer_predicate_matrix": rp,
        "closure_matrix": closure,
        "non_blocking_residuals": NON_BLOCKING_RESIDUALS,
        "observations": observations,
        "derived_evidence": derived,
        "checks": checks,
        "controls": controls,
        "detectors": {"live": {"D1": d1_live, "D2": d2_live}},
        "independence": "Detectors D1/D2, the FROZEN draft recomputation and the closure matrix are implemented in this file from the pinned primary bytes; no reviewer instrument or worker-066 code was imported. Candidate A is worker-022's own prior artifact; candidate B is reconstructed from worker-066's published diff. Review records were read to build the carrier union, not to implement the detectors.",
        "authority_note": "Worker preflight only: no canonical write, no node status, no validation_status, no gate verdict. Candidate bytes and FROZEN rev30 drafts are proposals.",
        "falsifier": prereg["falsifier"],
        "reproduce": f"python3 {Path(__file__).relative_to(ROOT)}",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    report_sha = sha(HERE / "report.json")
    report["_report_sha256"] = report_sha

    checkpoint = {
        "actor": "worker-022", "task_id": prereg["task_id"], "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN", "at": now(),
        "verdict": report["verdict"],
        "checks": f"{report['checks_pass']}/{report['checks_total']}",
        "controls": f"{report['controls_pass']}/{report['controls_total']}",
        "pins_end": pins_end, "candidate_A": cand_a_sha, "candidate_B": cand_b_sha,
        "draft_A": drafts["A"]["draft_file_sha256"], "draft_B": drafts["B"]["draft_file_sha256"],
        "report": "artifacts/worker-022/f2b_rev14_landing/report.json",
        "report_sha256": report_sha,
        "no_canonical_write": True,
        "next_falsifier": prereg["falsifier"],
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    if args.emit_events:
        (ROOT / "runtime/state/w022_checkpoint_6.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
        emit_events(report, checkpoint)

    print(json.dumps({"verdict": report["verdict"], "checks": f"{report['checks_pass']}/{report['checks_total']}",
                      "controls": f"{report['controls_pass']}/{report['controls_total']}",
                      "candidate_A": cand_a_sha[:12], "candidate_B": cand_b_sha[:12],
                      "draft_A": drafts["A"]["draft_file_sha256"][:12],
                      "draft_B": drafts["B"]["draft_file_sha256"][:12],
                      "report_sha256": report_sha[:16]}, indent=1))
    return 0 if report["verdict"] == "REV14_LANDING_PREFLIGHT_COMPLETE" else 1


def emit_events(report: dict, checkpoint: dict) -> None:
    out = ROOT / "comms/outbox/worker-022.jsonl"
    existing = out.read_text() if out.exists() else ""
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    base = f"w022-f2b-rev14-preflight-{stamp}"
    refs = [
        f"artifacts/worker-022/f2b_rev14_landing/report.json#sha256:{report['_report_sha256'][:16]}",
        f"artifacts/worker-022/f2b_rev14_landing/candidate_A/af_scc_c0_vacuum.rev14.yaml#sha256:{report['candidates']['A']['sha256'][:12]}",
        f"artifacts/worker-022/f2b_rev14_landing/candidate_B/af_scc_c0_vacuum.rev14.yaml#sha256:{report['candidates']['B']['sha256'][:12]}",
        f"artifacts/worker-022/f2b_rev14_landing/drafts/FROZEN.rev30.A.draft.json#sha256:{report['drafts']['A']['draft_file_sha256'][:12]}",
        f"artifacts/worker-022/f2b_rev14_landing/drafts/FROZEN.rev30.B.draft.json#sha256:{report['drafts']['B']['draft_file_sha256'][:12]}",
        f"artifacts/worker-022/f2b_rev14_landing/preregistration.json#sha256:{sha(HERE / 'preregistration.json')[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{report['pins_end']['schemas/af_scc_c0_vacuum.yaml'][:12]}",
        f"artifacts/formulation/FROZEN.json#sha256:{report['pins_end']['artifacts/formulation/FROZEN.json'][:12]}",
        f"runtime/state/w022_checkpoint_6.json#sha256:{sha(ROOT / 'runtime/state/w022_checkpoint_6.json')[:12]}",
    ]
    closed = sum(1 for rows in report["closure_matrix"].values() for r in rows
                 if r["detector"] in ("D1", "D2") and r["closed_by_A"] and r["closed_by_B"])
    statement = (
        "At the live rev13 pins (F2b b2ab6acb2bbe, FROZEN 815e08079aef, F0 0abb9ed8a961) two "
        f"independently produced rev14 candidates close {closed} blocking containment carriers named by "
        "workers 017/018/035/053/066/075: candidate A (worker-022) a110f8e8 and candidate B (worker-066, "
        "reconstructed byte-exactly from the published diff) 84b5d3fa. Both pass the pinned structural gate "
        "and the frozen and live class-separation detectors with 0 findings. Measured reviewer-predicate "
        "matrix at the live pin: all seven documented blocking predicates (017 CHK-09/10, 018 B1/B2, 053 C10, "
        "066 H1/H2) fire on live bytes and are silent on both candidates. The candidates differ only in "
        "line-152 wording: A removes the denial phrase; B quotes the withdrawn denial in lowercase inside the "
        "C2-sibling [R2 major] correction marker, which stays silent under the documented case-sensitive "
        "instruments but is still visible to a case-insensitive normalized probe. A FROZEN rev30 draft "
        "recomputed with regenerate_frozen.py's own key lists against the repaired bytes shows 0 missing "
        "entries and exactly the two C0 entries (canonical + authoring mirror) moving; all other pins are "
        "unchanged. The only residual non-content blocker is the conclusion_type token binding, independently "
        "adjudicated by worker-066 (13/13 checks, 10/10 controls) and requiring a gate-owner re-stamp rather "
        "than a schema edit. Landing obligations: re-run measure_semantic_escape.py, rebase_heldout.py and "
        "run_gate_tests.py at the new base. No canonical file was written by this task."
    )
    events = [
        {"event_id": base + "-artifact-report", "event_type": "artifact", "created_at": now(),
         "actor": "worker-022", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "rev14_landing_preflight_report",
         "path": "artifacts/worker-022/f2b_rev14_landing/report.json",
         "sha256": report["_report_sha256"], "validation_status": "unverified",
         "summary": statement[:900], "evidence_refs": refs},
        {"event_id": base + "-claim", "event_type": "claim", "created_at": now(),
         "actor": "worker-022", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "conclusion_type": "formal_model", "statement": statement,
         "assumptions": [
             "The measured sha256 is artifact identity; FROZEN rev29 815e08079aef is the binding pin set.",
             "The two candidates differ only in the two named leaf fields (verified by line diff and YAML top-level key comparison).",
             "D1/D2 are text-consistency detectors over the file's own containment chain, not claims about the mathematics of C0/C2 inextendibility.",
             "The FROZEN rev30 draft is computed with regenerate_frozen.py's own CANONICAL/PIN_EXTRAS/VOLATILE lists and is not published."],
         "falsifier": report["falsifier"],
         "evidence_refs": refs,
         "artifact_refs": ["artifacts/worker-022/f2b_rev14_landing/candidate_A/af_scc_c0_vacuum.rev14.yaml",
                           "artifacts/worker-022/f2b_rev14_landing/candidate_B/af_scc_c0_vacuum.rev14.yaml",
                           "artifacts/worker-022/f2b_rev14_landing/drafts/FROZEN.rev30.A.draft.json",
                           "artifacts/worker-022/f2b_rev14_landing/drafts/FROZEN.rev30.B.draft.json"]},
        {"event_id": base + "-status", "event_type": "status", "created_at": now(),
         "actor": "worker-022", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "status": "active", "hours": 0.7, "task_id": report["task_id"],
         "summary": (f"W022-F2B-REV14-LANDING-PREFLIGHT-01 complete at worker level: "
                     f"{report['checks_pass']}/{report['checks_total']} checks, "
                     f"{report['controls_pass']}/{report['controls_total']} controls, 0 canonical writes. "
                     "Owner action requested: choose A or B, land canonical+mirror, regenerate FROZEN rev30 "
                     "with the provided draft as cross-check, then re-run the three derived-evidence tools. "
                     "No node status, validation_status, or gate verdict is set."),
         "evidence_refs": refs,
         "next_falsifier": report["falsifier"]},
    ]
    new = [json.dumps(e, ensure_ascii=False) for e in events if e["event_id"] not in existing]
    if new:
        with out.open("a") as fh:
            fh.write("\n".join(new) + "\n")
        print(f"emitted {len(new)} events to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
