#!/usr/bin/env python3
"""W084-F2B-CONFLICT-ADJ-01: independent adjudication of the F2b rev12 verdict conflict.

One bounded class-bound task at ONE pinned hash of ONE class. The conflict:

  * worker-098  `reviews/F2b-repair-verify-worker-098.json`  -> ACCEPT 4.5 at
    schemas/af_scc_c0_vacuum.yaml sha256 55d0a1ea9bda (full class-schema verdict,
    re-test of its own B1/B2/B3 blockers, 11 checks / 9 controls, gate reproduction);
  * worker-060  `artifacts/worker-060/f2b_rev12_closure_verify/` -> REVISE at the
    same hash, with HF-060-F2B-1 (hard) = an inverted containment premise in
    `implication_ledger.forbidden_transfers[0].reason` and HF-060-F2B-2 (minor) =
    a stale `f0_binding.consistency_evidence_sha256` pin.

This instrument does four things, all deterministic:

  1. re-runs the class-identity/binding surface at the pinned bytes (same checks as
     worker-084 rounds 1-3, adapted to rev12) so the conflict is known to be narrow;
  2. fact-checks the inverted premise by PARSING the YAML (not grepping) and by
     exhaustively enumerating finite set-containment models, so "strictly larger"
     is decided by model theory rather than by prose reading;
  3. measures the two verdicts' SCOPE (does the accept evaluate the field that the
     revise finding names?) so a scope gap is not misread as a contradiction;
  4. binds the finding to the A0 rubric's enumerated hard-failure taxonomy and to
     the canonical binding gate, to separate "real defect" from "enumerated
     critical HF" and to expose any instrument gap between them.

Authority: worker evidence only. No gate verdict, no node status, no
validation_status promotion. Whether G-FORM counts a non-enumerated major prose
defect is the audit lead's and the controller's call.

Freeze discipline: every input is read ONCE into memory and hashed; canonical and
rubric paths are re-hashed at the end. Any movement is recorded as drift and the
verdict is VOID for gate use.

Usage:  python3 artifacts/worker-084/f2b_conflict_adj/verify_f2b_conflict_adj.py
Writes: report.json + snapshots/ (byte copies) in this directory.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK_ID = "W084-F2B-CONFLICT-ADJ-01"
WORKER = "worker-084"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
FROZEN_FOUR = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}

CANON = ROOT / "schemas/af_scc_c0_vacuum.yaml"
AUTHOR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
RUBRIC = ROOT / "evaluation_rubric.yaml"
CONS = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
W060_EV = ROOT / "artifacts/worker-060/f2b_rev12_closure_verify/evidence.json"
W060_RP = ROOT / "artifacts/worker-060/f2b_rev12_closure_verify/REPORT.md"
W098_RV = ROOT / "reviews/F2b-repair-verify-worker-098.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, CST).isoformat(timespec="seconds")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def top_level_duplicate_keys(text: str) -> dict:
    seen: dict[str, int] = {}
    for line in text.splitlines():
        if not line or line[0] in " \t#-":
            continue
        m = TOP_KEY.match(line)
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    return {k: v for k, v in seen.items() if v > 1}


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def containment_models() -> dict:
    """Exhaustive finite model check over a 2-element universe.

    E_C0, E_C2 are sets of admissible extensions. The file asserts
    E_C2 subset of E_C0 (a C2 metric extension is a continuous metric extension).
    I_k := (E_k is empty)  =  "no proper future k extension".

    * is 'E_C2 strictly larger than E_C0' compatible with E_C2 subset E_C0?
    * is I_C2 (C2-inextendibility) strictly weaker than I_C0?
    """
    universe = [0, 1]
    subsets = [set(s) for r in range(3) for s in itertools.combinations(universe, r)]
    n_containment_models = 0
    n_c2_strictly_larger = 0
    entailment_counterexample = 0          # I_C0 true and I_C2 false
    strictness_witness = 0                 # I_C2 true and I_C0 false
    for e_c0 in subsets:
        for e_c2 in subsets:
            if not e_c2 <= e_c0:
                continue
            n_containment_models += 1
            if e_c2 > e_c0:
                n_c2_strictly_larger += 1
            i_c0 = len(e_c0) == 0
            i_c2 = len(e_c2) == 0
            if i_c0 and not i_c2:
                entailment_counterexample += 1
            if i_c2 and not i_c0:
                strictness_witness += 1
    return {
        "universe_size": len(universe),
        "containment_models": n_containment_models,
        "models_with_c2_strictly_larger": n_c2_strictly_larger,
        "models_with_I_C0_true_and_I_C2_false": entailment_counterexample,
        "models_with_I_C2_true_and_I_C0_false": strictness_witness,
    }


def main() -> int:
    # ---- atomic snapshot -------------------------------------------------
    paths = {
        "canonical": CANON, "authoring": AUTHOR, "sibling_f2a": F2A,
        "f0_canonical": F0, "frozen": FROZEN, "rubric_a0": RUBRIC,
        "consistency_evidence": CONS, "w060_evidence": W060_EV,
        "w060_report": W060_RP, "w098_review": W098_RV,
    }
    blobs, shas, mtimes = {}, {}, {}
    for k, p in paths.items():
        b = p.read_bytes()
        blobs[k] = b
        shas[k] = sha256_bytes(b)
        mtimes[k] = iso(p.stat().st_mtime)

    doc = yaml.safe_load(blobs["canonical"])
    adoc = yaml.safe_load(blobs["authoring"])
    sib = yaml.safe_load(blobs["sibling_f2a"])
    tax = yaml.safe_load(blobs["f0_canonical"])
    frozen = json.loads(blobs["frozen"])
    rubric = yaml.safe_load(blobs["rubric_a0"])
    w060 = json.loads(blobs["w060_evidence"])
    w098 = json.loads(blobs["w098_review"])
    run_now = now()
    canon_text = blobs["canonical"].decode("utf-8")

    checks: dict[str, dict] = {}
    facts: dict[str, dict] = {}
    hard: list[str] = []
    major: list[str] = []
    soft: list[str] = []

    def check(cid: str, ok: bool, detail: str, severity: str = "hard"):
        """Conformance check: ok=False IS a defect of the artifact under test."""
        if not ok:
            if severity == "hard":
                hard.append(f"{cid}: {detail}")
            elif severity == "major":
                major.append(f"{cid}: {detail}")
            else:
                soft.append(f"{cid}: {detail}")
        checks[cid] = {"ok": bool(ok), "severity": severity, "detail": detail}

    def fact(cid: str, confirmed: bool, detail: str, classification: str = "info"):
        """Adjudication fact: `confirmed` records whether the proposition holds.
        It never adds to the defect lists by itself; the adjudication block does
        the classification."""
        facts[cid] = {"confirmed": bool(confirmed), "classification": classification,
                      "detail": detail}

    # ---- C1 binding / identity surface (rounds 1-3, adapted to rev12) ----
    check("C1.1_canonical_authoring_byte_identical",
          shas["canonical"] == shas["authoring"],
          f"canonical={shas['canonical'][:12]} authoring={shas['authoring'][:12]}")
    check("C1.2_class_id_is_this_frozen_class",
          doc.get("class_id") == CLASS_ID and doc.get("class_id") in FROZEN_FOUR,
          f"class_id={doc.get('class_id')!r} expected {CLASS_ID!r}")
    fz = frozen.get("files", {})
    fz_canon = (fz.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    fz_author = (fz.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    frozen_at = str(frozen.get("frozen_at", ""))
    check("C1.3_frozen_manifest_canonical_entry_matches", fz_canon == shas["canonical"],
          f"FROZEN rev{frozen.get('revision')} entry={str(fz_canon)[:12]} measured={shas['canonical'][:12]}")
    check("C1.4_frozen_manifest_authoring_entry_matches", fz_author == shas["canonical"],
          f"FROZEN rev{frozen.get('revision')} entry={str(fz_author)[:12]} measured={shas['authoring'][:12]}")
    check("C1.5_frozen_at_not_future_vs_own_mtime",
          frozen_at <= mtimes["frozen"],
          f"frozen_at={frozen_at} FROZEN mtime={mtimes['frozen']} now={run_now}")
    sidecar = CANON.with_name(CANON.name + ".sha256")
    sidecar_sha = sidecar.read_text().split()[0] if sidecar.exists() else None
    check("C1.6_sidecar_present_and_wellformed",
          sidecar_sha is None or bool(re.fullmatch(r"[0-9a-f]{64}", str(sidecar_sha))),
          f"sidecar={str(sidecar_sha)[:12]} exists={sidecar.exists()} "
          f"(staleness is adjudicated at C5.1)")
    dup = top_level_duplicate_keys(canon_text)
    check("C1.7_no_duplicate_top_level_keys", not dup, f"duplicates={dup}")
    rev_at = str(doc.get("revised_at", ""))
    check("C1.8_revised_at_not_future_vs_own_mtime", rev_at <= mtimes["canonical"],
          f"revised_at={rev_at} schema mtime={mtimes['canonical']}")
    fb = doc.get("f0_binding") or {}
    check("C1.9_f0_binding_matches_measured_F0",
          str(fb.get("declared_f0_sha256")) == shas["f0_canonical"],
          f"declared={str(fb.get('declared_f0_sha256'))[:12]} measured={shas['f0_canonical'][:12]}")
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_path, _, ptr_frag = ptr.partition("#")
    frag_class = ptr_frag.split(".", 1)[1] if "." in ptr_frag else ptr_frag
    check("C1.10_pointer_is_canonical_F0_and_resolves",
          ptr_path == "research_map/formulation_taxonomy.yaml"
          and frag_class == CLASS_ID
          and frag_class in (tax.get("classes") or {}),
          f"pointer={ptr!r} resolves_in_classes={frag_class in (tax.get('classes') or {})}")
    rs = doc.get("review_status") or {}
    check("C1.11_review_not_self_passed", rs.get("verdict") == "pending",
          f"review_status.verdict={rs.get('verdict')!r}")

    # ---- C2 class identity / separation ----------------------------------
    cc = doc.get("class_components") or {}
    contract = (tax.get("classes") or {}).get(CLASS_ID) or {}
    axes = contract.get("axes") or {}
    check("C2.1_regularity_token_is_C0",
          cc.get("regularity_token") == "C0" and axes.get("regularity_token") == "C0",
          f"schema={cc.get('regularity_token')!r} contract={axes.get('regularity_token')!r}")
    check("C2.2_conclusion_family_is_SCC",
          (doc.get("conclusion") or {}).get("family") == "SCC",
          f"conclusion.family={(doc.get('conclusion') or {}).get('family')!r}")
    pairs = [tuple(sorted(d.get("pair", []))) for d in tax.get("disjointness", [])]
    check("C2.3_sibling_disjointness_declared",
          doc.get("sibling_disjoint_from") == SIBLING
          and tuple(sorted((SIBLING, CLASS_ID))) in pairs,
          f"sibling={doc.get('sibling_disjoint_from')!r} taxonomy_pair_present="
          f"{tuple(sorted((SIBLING, CLASS_ID))) in pairs}")
    anti_ids = {e.get("class_id") for e in (doc.get("anti_scope") or {}).get("not_this_class", [])}
    check("C2.4_anti_scope_covers_three_siblings",
          {s for s in FROZEN_FOUR if s != CLASS_ID} <= anti_ids,
          f"anti_scope ids={sorted(x for x in anti_ids if x)}")
    findings = cs.findings_for_text(canon_text, CANON.name)
    hard_sep = [f for f in findings if not f.startswith("CLASSSEP-SOFT:")]
    reg = cs.regression()
    check("C2.5_class_separation_clean_and_regression_pass",
          not hard_sep and reg.get("verdict") == "PASS",
          f"hard_sep={hard_sep[:2]} regression={reg.get('verdict')} "
          f"tp={reg.get('tp')} fn={reg.get('fn')} fp={reg.get('fp')} tn={reg.get('tn')}")

    # ---- C3 the conflict: fact-check the inverted premise ----------------
    ledger = doc.get("implication_ledger") or {}
    row = next((r for r in (ledger.get("forbidden_transfers") or [])
                if isinstance(r, dict)
                and r.get("from") == "no proper future C2 extension"
                and r.get("to") == "this class"), None)
    row_reason = str((row or {}).get("reason", ""))
    inverted = bool(row) and "larger" in row_reason
    fact("C3.1_inverted_premise_confirmed_at_pinned_bytes", inverted,
         f"forbidden_transfers[C2->this class].reason={row_reason!r} "
         f"line={line_of(canon_text, row_reason) if row_reason else None}",
         classification="major" if inverted else "info")

    contain = str(ledger.get("extension_class_containment", ""))
    order = [contain.find(t) for t in ("E_C0", "E_H2loc", "E_{C^1,1}", "E_C2")]
    own_chain_oks = all(i >= 0 for i in order) and order == sorted(order)
    fact("C3.2_own_file_orders_E_C2_last_smallest", own_chain_oks,
         f"containment={contain[:160]!r} token_positions={order}",
         classification="contradiction-with-C3.1" if own_chain_oks else "info")

    models = containment_models()
    model_ok = (models["models_with_c2_strictly_larger"] == 0
                and models["models_with_I_C0_true_and_I_C2_false"] == 0
                and models["models_with_I_C2_true_and_I_C0_false"] > 0)
    fact("C3.3_model_check_refutes_strictly_larger_confirms_weaker", model_ok,
         f"exhaustive over containment-respecting set models: {models}",
         classification="major" if model_ok else "info")

    sib_led = sib.get("implication_ledger") or {}
    sib_contain = str(sib_led.get("extension_class_containment", ""))
    sib_row = next((r for r in (sib_led.get("forbidden_transfers") or [])
                    if isinstance(r, dict)
                    and r.get("from") == "no proper future C2 extension"), None)
    sib_reason = str((sib_row or {}).get("reason", ""))
    sib_consistent = "E_C2 subset of" in sib_contain and "larger" not in sib_reason
    fact("C3.4_sibling_F2a_states_same_containment_without_inversion", sib_consistent,
         f"F2a containment={sib_contain[:120]!r} F2a parallel reason={sib_reason!r}",
         classification="cross-class-precedent" if sib_consistent else "info")

    fcs = {c.get("id"): c for c in (rubric.get("frozen_classes") or [])}
    c0_meta = fcs.get(CLASS_ID) or {}
    c2_meta = fcs.get(SIBLING) or {}
    implied = c0_meta.get("conclusion_implied") or []
    note = str(c2_meta.get("implication_note", ""))
    rubric_agrees = (any("C2_inextendibility" in str(x) for x in implied)
                     and "SCC-C0 implies SCC-C2" in note
                     and "converse does not hold" in note)
    fact("C3.5_rubric_A0_agrees_C0_implies_C2_converse_not", rubric_agrees,
         f"conclusion_implied={implied} implication_note={note!r}",
         classification="authority-direction" if rubric_agrees else "info")

    rel_sib = str((doc.get("c0_specifics") or {}).get("conclusion_relation_to_sibling", ""))
    rel_ok = "C0 => C2" in rel_sib and "converse is forbidden" in rel_sib
    fact("C3.6_third_internal_statement_agrees", rel_ok,
         f"c0_specifics.conclusion_relation_to_sibling={rel_sib[:160]!r}",
         classification="contradiction-with-C3.1" if rel_ok else "info")

    w060_hf = {f.get("id"): f for f in (w060.get("hard_findings") or [])}
    hf1 = w060_hf.get("HF-060-F2B-1") or {}
    w060_confirmed = (str(w060.get("pinned_sha256")) == shas["canonical"]
                      and "strictly larger" in json.dumps(hf1))
    fact("C3.7_worker060_finding_reproduced_at_same_hash", w060_confirmed,
         f"w060 pinned={str(w060.get('pinned_sha256'))[:12]} measured={shas['canonical'][:12]} "
         f"w060_hf_ids={sorted(w060_hf)}", classification="independent-corroboration")

    w098_text = json.dumps(w098)
    scope_terms = [t for t in ("implication_ledger", "forbidden_transfers",
                               "extension_class_containment", "strictly larger",
                               "containment", "sidecar", "consistency_evidence")
                   if t in w098_text]
    w098_clean_scope = bool(str(w098.get("reviewed_sha256") or w098.get("artifact_sha256"))
                            == shas["canonical"] and not scope_terms)
    fact("C3.8_w098_accept_does_not_cover_the_finding_surfaces", w098_clean_scope,
         f"w098 verdict={w098.get('verdict')!r} sha="
         f"{str(w098.get('reviewed_sha256'))[:12]} terms_found={scope_terms} "
         f"(empty = the accept never evaluates implication_ledger prose, the sidecar, "
         f"or the consistency declaration)",
         classification="scope-gap" if w098_clean_scope else "info")

    # ---- C4 the instrument surface ---------------------------------------
    gate_doc = GATE.read_text()
    gate_exempts_forbidden = bool(re.search(r"forbidden_transfers", gate_doc))
    gate_declares_no_math = ("does NOT decide physical correctness" in gate_doc
                             and "no check that the mathematics in a" in gate_doc)
    proc = subprocess.run([sys.executable, str(GATE), "--json", str(CANON)],
                          capture_output=True, text=True, timeout=180)
    gate_json = None
    try:
        gate_json = json.loads(proc.stdout)
    except Exception:
        gate_json = None
    gate_verdict = (gate_json or {}).get("verdict")
    fact("C4.1_binding_gate_passes_canonical_despite_inversion",
         proc.returncode == 0 and inverted,
         f"gate exit={proc.returncode} verdict={gate_verdict!r} canonical={shas['canonical'][:12]}",
         classification="instrument-gap" if (proc.returncode == 0 and inverted) else "info")
    fact("C4.2_gate_declares_math_correctness_out_of_scope", gate_declares_no_math,
         "check_class_schema.py: 'It does NOT decide physical correctness, truth, or the "
         "scope of any cited source' + 'no check that the mathematics in a definition is "
         "correct, only that it is present'; EXEMPT_KEY regex contains "
         f"forbidden_transfers={gate_exempts_forbidden}",
         classification="instrument-gap" if gate_declares_no_math else "info")

    hf_tax = rubric.get("hard_failures") or []
    hf_ids = [h.get("id") for h in hf_tax]
    # Strip regularity/class tokens (C0, C2, C^{1,1}, H2_loc) before looking for numeric
    # quantities, so a class label is not misread as an HF-04 quantity claim.
    reason_stripped = row_reason
    for tok in ("C^{1,1}", "C^1,1", "H2_loc", "C0", "C2", "C2-"):
        reason_stripped = reason_stripped.replace(tok, "")
    det_hits = []
    if re.search(r"\d", reason_stripped):
        det_hits.append("HF-04_quantity_token_in_reason")
    if any(t in row_reason.lower() for t in ("arxiv", "doi", "et al", "theorem", "proposition")):
        det_hits.append("HF-03_citation_token_in_reason")
    if doc.get("claims_theorem_status") is True:
        det_hits.append("HF-01_theorem_flag")
    if any(cid in row_reason for cid in FROZEN_FOUR if cid != CLASS_ID):
        det_hits.append("HF-02_foreign_class_token_in_reason")
    fact("C4.3_no_enumerated_A0_hard_failure_detector_matches", len(det_hits) == 0,
         f"enumerated_HF={hf_ids}; detector scan on the defective reason string "
         f"('{row_reason}', tokens stripped: '{reason_stripped}') hits={det_hits}. "
         f"The defect is not a theorem promotion, class-id violation, citation, quantity, "
         f"missing artifact, smuggled assumption, duplicate, command/seed issue, budget issue, "
         f"recycled claim, or cross-project contamination.",
         classification="rubric-scope" if not det_hits else "info")

    # ---- C5 evidence-binding surface: sidecar + consistency declaration ---
    check("C5.1_no_stale_published_sidecar_hash", sidecar_sha in (None, shas["canonical"]),
          f"schemas/af_scc_c0_vacuum.yaml.sha256 declares {str(sidecar_sha)[:12]} while the "
          f"canonical file measures {shas['canonical'][:12]} (sidecar mtime "
          f"{iso(sidecar.stat().st_mtime) if sidecar.exists() else None}; F1/F2a carry no sidecar)",
          severity="hard")

    declared_cons = str(fb.get("consistency_evidence_sha256"))
    fz_cons = (fz.get("artifacts/formulation/evidence/taxonomy_consistency.json") or {}).get("sha256")
    cons_measured = shas["consistency_evidence"]
    check("C5.2_consistency_declaration_matches_measured_at_pin",
          declared_cons == cons_measured,
          f"declared={declared_cons[:12]} measured={cons_measured[:12]} "
          f"FROZEN_pin={str(fz_cons)[:12]} mtime={mtimes['consistency_evidence']} "
          f"declared==frozen:{declared_cons == fz_cons} frozen==measured:{fz_cons == cons_measured} "
          f"(the named file is regenerated by artifacts/formulation/tools/"
          f"check_taxonomy_consistency.py, so a hash pin to it is single-instant)",
          severity="major")

    # ---- drift re-hash ----------------------------------------------------
    after = {k: sha256_bytes(p.read_bytes()) for k, p in paths.items()}
    drifted = {k: [shas[k][:12], after[k][:12]] for k in paths if after[k] != shas[k]}

    # ---- adjudication -----------------------------------------------------
    inversion_confirmed = bool(inverted and own_chain_oks and model_ok and w060_confirmed)
    sidecar_stale = sidecar_sha not in (None, shas["canonical"])
    cons_stale = declared_cons != cons_measured
    repair = ("three cheap repairs, no content rewrite: (1) one token at "
              "implication_ledger.forbidden_transfers[0].reason, 'strictly larger' -> "
              "'strictly smaller' (or the F2a wording 'the converse containment is false'); "
              "(2) regenerate schemas/af_scc_c0_vacuum.yaml.sha256 to the measured canonical "
              "hash; (3) refresh f0_binding.consistency_evidence_sha256 to the measured "
              "taxonomy_consistency.json it names at the pin instant.")
    findings = [
        {"id": "W084-ADJ-1", "severity": "major", "enumerated_A0_HF": False,
         "blocking_recommendation": True,
         "subject": "implication_ledger.forbidden_transfers[0].reason",
         "finding": ("inverted premise: 'C2 is a strictly larger extension class'. The file's "
                     "own containment (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2), "
                     "the F2a sibling, the A0 rubric implication_note and the schema's own "
                     "c0_specifics sentence all state the opposite direction. The stated "
                     "conclusion ('C2-inextendibility is strictly weaker') survives; only the "
                     "premise is false. Confirmed by exhaustive finite model check."),
         "repair": "'strictly larger' -> 'strictly smaller'"},
        {"id": "W084-ADJ-2", "severity": "major", "enumerated_A0_HF": False,
         "blocking_recommendation": True,
         "subject": "schemas/af_scc_c0_vacuum.yaml.sha256",
         "finding": (f"stale published hash record: the sidecar declares {str(sidecar_sha)[:12]} "
                     f"(rev11) while the canonical file measures {shas['canonical'][:12]} (rev12). "
                     f"Any consumer running 'sha256sum -c' on the published sidecar gets a false "
                     f"mismatch. F1/F2a carry no sidecar, so this is F2b-specific."),
         "repair": "regenerate the sidecar from the measured canonical bytes"},
        {"id": "W084-ADJ-3", "severity": "minor", "enumerated_A0_HF": False,
         "blocking_recommendation": False,
         "subject": "f0_binding.consistency_evidence_sha256",
         "finding": (f"declared {declared_cons[:12]} != measured {cons_measured[:12]} at the pin "
                     f"instant; FROZEN rev{frozen.get('revision')} pins the measured value. The "
                     f"named file is unconditionally regenerated by "
                     f"check_taxonomy_consistency.py, so the declaration is a single-instant pin "
                     f"that has gone stale (worker-060 HF-060-F2B-2, independently reproduced)."),
         "repair": "refresh the declared hash at the pin instant or pin a frozen copy"},
    ]
    adjudication = {
        "inversion_confirmed": inversion_confirmed,
        "sidecar_stale_confirmed": sidecar_stale,
        "consistency_declaration_stale_confirmed": cons_stale,
        "finding_real": inversion_confirmed,          # worker-060 HF-060-F2B-1
        "severity": "major" if inversion_confirmed else "none",
        "enumerated_hard_failure": False,
        "gate_letter_violation": False,
        "gate_letter_note": ("G-FORM's criteria are structural; the inverted sentence sits in a "
                             "PROHIBITION (forbidden_transfers), so no cross-class evidence is "
                             "used without a transfer_argument. The defect is correctness of the "
                             "stated justification, not a class merge or a conclusion transfer."),
        "conflict_reconcilable": True,
        "conflict_note": ("The accept (worker-098) and the revise (worker-060) evaluate disjoint "
                          "surfaces: worker-098 re-tests B1/B2/B3, strict parse, pointer, "
                          "class-separation and gate reproduction and never mentions "
                          "implication_ledger, the sidecar, or the consistency declaration; "
                          "worker-060 found the inversion and the consistency staleness but not "
                          "the sidecar. They are not contradictory; the accept is INCOMPLETE "
                          "with respect to every field the revise findings name."),
        "instrument_gap": ("A0's hard_failure taxonomy has no binary detector for (a) an inverted "
                           "logical premise in implication_ledger prose or (b) a stale published "
                           "sidecar hash; the binding gate declares mathematical correctness out "
                           "of scope and exempts forbidden_transfers from its leakage scan, and "
                           "it exits pass on these bytes. Real evidence/correctness defects are "
                           "therefore invisible to both instruments; the controller/audit-lead "
                           "must rule whether G-FORM counts them."),
        "recommended_repair": repair,
        "finding_ids": [f["id"] for f in findings],
        "worker_verdict": "revise" if (inversion_confirmed or sidecar_stale) else "accept",
        "worker_score": 3.0 if (inversion_confirmed or sidecar_stale) else 4.0,
        "enumerated_hard_failures": [],
        "authority_note": ("Worker evidence only. This does not move node status, "
                           "validation_status, or any gate verdict; it adjudicates one "
                           "conflict at one pinned hash and hands the classification "
                           "question to the audit lead."),
    }

    report = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "scope": ("single class AF-SCC-C0-VAC-GEN at the pinned canonical bytes; adjudicates "
                  "the worker-098 accept / worker-060 revise conflict on HF-060-F2B-1 and "
                  "HF-060-F2B-2; no mathematical verdict on cosmic censorship"),
        "generated_at": run_now,
        "snapshot": {k: {"path": str(paths[k].relative_to(ROOT)), "sha256": shas[k],
                         "mtime": mtimes[k]} for k in paths},
        "conflict": {
            "accept": {"reviewer": "worker-098", "review": "reviews/F2b-repair-verify-worker-098.json",
                       "sha256": shas["w098_review"], "verdict": w098.get("verdict"),
                       "score": w098.get("score"),
                       "reviewed_sha256": w098.get("reviewed_sha256")},
            "revise": {"reviewer": "worker-060",
                       "evidence": "artifacts/worker-060/f2b_rev12_closure_verify/evidence.json",
                       "sha256": shas["w060_evidence"], "verdict": w060.get("verdict"),
                       "pinned_sha256": w060.get("pinned_sha256"),
                       "hard_finding_ids": sorted(w060_hf)},
        },
        "checks": checks,
        "facts": facts,
        "hard_failures": hard,
        "major_findings": major,
        "soft_findings": soft,
        "confirmed_facts": {
            "inverted_reason_string": row_reason,
            "inverted_line": line_of(canon_text, row_reason) if row_reason else None,
            "own_containment_chain": contain,
            "model_check": models,
            "third_internal_statement": rel_sib,
            "rubric_implication_note": note,
            "sidecar_declared": str(sidecar_sha),
            "sidecar_measured": shas["canonical"],
            "consistency_declared": declared_cons,
            "consistency_measured": cons_measured,
            "consistency_frozen_pin": fz_cons,
            "w098_scope_terms_absent": scope_terms,
        },
        "findings": findings,
        "adjudication": adjudication,
        "gate_run": {"command": f"python3 {GATE.relative_to(ROOT)} --json {CANON.relative_to(ROOT)}",
                     "exit_code": proc.returncode, "verdict": gate_verdict,
                     "stdout_head": (proc.stdout or "")[:400]},
        "drift": {"moved_during_check": bool(drifted), "moved": drifted,
                  "canonical_before": shas["canonical"], "canonical_after": after["canonical"]},
        "falsifier": (
            "Re-run this instrument at the same pinned hashes. Falsified if: (a) the "
            "forbidden_transfers[C2->this class].reason no longer contains an inverted "
            "'larger' premise, the sidecar hash equals the canonical hash, and the "
            "consistency declaration equals the measured file (i.e. all three repairs "
            "landed); (b) any fact recorded confirmed=true re-runs false; (c) a "
            "containment-respecting set model exists in which E_C2 is strictly larger than "
            "E_C0, or in which C0-inextendibility holds while C2-inextendibility fails; or "
            "(d) worker-098's review is shown to evaluate implication_ledger prose, the "
            "sidecar, or the consistency declaration (retiring the scope-gap "
            "reconciliation). Canonical/authoring/F0/FROZEN/rubric hash drift VOIDS the "
            "verdict, it does not falsify the finding."
        ),
        "claim_boundary": (
            "CLEAN at this snapshot: class identity, C0 regularity token, SCC conclusion "
            "family, sibling disjointness, anti-scope, F0/class-contract binding, revision "
            "stamps, and the canonical class-separation regression; the binding gate exits "
            "pass. DEFECTIVE: (1) one inverted premise in "
            "implication_ledger.forbidden_transfers[0].reason, confirmed by exhaustive "
            "finite model check (major, one-token repair); (2) the published sidecar "
            "schemas/af_scc_c0_vacuum.yaml.sha256 still records the superseded rev11 hash "
            "(major, regenerate); (3) the consistency-evidence declaration is stale against "
            "the file it names at the pin instant (minor, refresh). None is an enumerated "
            "A0 critical HF; whether they block a clean G-FORM accept is the audit lead's "
            "call. No claim about cosmic censorship."
        ),
        "warning": ("LIVE DRIFT: inputs moved during the check window; verdict VOID for gate "
                    "use." if drifted else None),
        "partial_defect_correction": (
            "Correction of worker-084's own checkpoint 3 (runtime/state/w084_checkpoint_3.json): "
            "its 'measured_hashes_at_emit' recorded the SUPERSEDED pre-close-findings hashes "
            "(276009f4/9a8bd4c9/b6123750/1bb78ce9) under a label that reads as measured. The "
            "round-4 report and REVIEW.md measured 0abb9ed8/cce9c601/5476a3f2/55d0a1ea; this "
            "checkpoint re-states the measured set and the mislabel is disclosed so the error "
            "is not inherited."
        ),
    }

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")

    # ---- byte-copy snapshots (read-only provenance) ----------------------
    snap = HERE / "snapshots"
    snap.mkdir(exist_ok=True)
    for k, p in paths.items():
        shutil.copyfile(p, snap / f"{k}.{shas[k][:12]}{p.suffix}")

    print(f"canonical {shas['canonical'][:12]}  F0 {shas['f0_canonical'][:12]}  "
          f"FROZEN rev{frozen.get('revision')} {shas['frozen'][:12]}")
    print(f"inverted={inverted} models={models}")
    print(f"hard={len(hard)} major={len(major)} soft={len(soft)} drift={bool(drifted)}")
    print(f"w060_hf={sorted(w060_hf)} w098_scope_terms={scope_terms}")
    print(f"sidecar_stale={sidecar_stale} consistency_stale={cons_stale}")
    print(f"gate exit={proc.returncode} verdict={gate_verdict!r}")
    for h in hard:
        print("  HARD:", h)
    for m in major:
        print("  MAJOR:", m)
    print(f"ADJUDICATION: inversion={inversion_confirmed} sidecar_stale={sidecar_stale} "
          f"worker_verdict={adjudication['worker_verdict']} -> {out}")
    return 1 if (inversion_confirmed or sidecar_stale or drifted) else 0


if __name__ == "__main__":
    sys.exit(main())
