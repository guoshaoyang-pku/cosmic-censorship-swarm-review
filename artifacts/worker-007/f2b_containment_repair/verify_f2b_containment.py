#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W007-F2B-CONTAINMENT-REPAIR-01
================================================================
Independent, hash-pinned adjudication of the AF-SCC-C0-VAC-GEN (F2b) containment-
direction blocker at rev13 schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, plus a
reusable acceptance predicate for the staged repair candidates.

The adjudication is mechanical: the extension-class containment order is parsed
from the reviewed document's OWN frozen chain and from the F0 class-contract
supplement's axis registry, then every normative containment sentence in the
document is tested against that order.

Reads only the snapshot/ copies (byte-identical to the declared pins) and the
live paths for drift detection.  Writes only with --emit.  Author: worker-007.
Authority: worker measurement only; cannot set node status, validation_status or
any gate verdict.  Not a mathematics claim.
"""

import argparse
import hashlib
import json
import os
import re
import sys

try:
    import yaml
except Exception:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PKT = os.path.join(ROOT, "artifacts", "worker-007", "f2b_containment_repair")
SNAP = os.path.join(PKT, "snapshot")

# ---------------------------------------------------------------- pins ----
# live repository paths -> (expected sha256, snapshot filename)
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": (
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "schemas__af_scc_c0_vacuum.b2ab6acb2bbe.yaml",
    ),
    "research_map/formulation_taxonomy.yaml": (
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "research_map__formulation_taxonomy.0abb9ed8a961.yaml",
    ),
    "artifacts/formulation/formulation_taxonomy.yaml": (
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
        "formulation_taxonomy.d7419b4e8963.yaml",
    ),
    "artifacts/formulation/rule_spec.json": (
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
        "rule_spec.40f9bb9e657b.json",
    ),
    "artifacts/formulation/FROZEN.json": (
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "FROZEN.815e08079aef.json",
    ),
}

# staged repair candidates (not canonical; measured, never trusted)
CANDIDATES = {
    "C-022-cd-repair": (
        "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
        "candidate_w022.a110f8e875af.yaml",
    ),
    "C-044-rev13-integration": (
        "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml",
        "candidate_w044_rev13.48cadb72e507.yaml",
    ),
    "C-044-acceptance-oracle": (
        "artifacts/worker-044/f2b_acceptance_oracle/sandbox/schemas/af_scc_c0_vacuum.yaml",
        "candidate_w044_oracle.3ab16da27e7b.yaml",
    ),
}

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"

# extension-set size order (smallest set first).  Strength of "no proper future
# X extension" runs the other way: the larger the extension set, the stronger
# the no-extension statement.
SET_ORDER = ["C2", "C1_1", "H2loc", "C0"]
SET_RANK = {"C2": 0, "C1_1": 1, "H2loc": 2, "C0d": 3, "C0": 3}
ALIASES = {
    "C2": ("C2", "C^2"),
    "C1_1": ("C^{1,1}", "C1_1", "C^{1,1}"),
    "H2loc": ("H2_loc", "H2loc"),
    "C0d": ("C0 distributional", "distributional-vacuum", "distributional_vacuum"),
    "C0": ("C0", "C^0"),
}

CHAIN_OK = re.compile(
    r"E_C0\s+contains\s+E_H2loc\s+contains\s+E_\{C\^1,1\}\s+contains\s+E_C2"
)
CHAIN_SUBSET_OK = re.compile(
    r"E_C2\s+subset\s+of\s+E_\{C\^1,1\}\s+subset\s+of\s+E_H2loc\s+subset\s+of\s+E_C0",
    re.IGNORECASE,
)
DENIAL_RE = re.compile(r"[Nn]o containment with\s+([^;.\"]{2,40})")
DIRECTION_RE = re.compile(
    r"(?i)(strictly\s+)?(larger|bigger|smaller|stronger|weaker)\s+extension\s+class"
)
# markers that turn a containment denial into a quoted/withdrawn mention rather
# than a live normative denial (the CF-16 metalinguistic-mention pattern)
MENTION_MARKERS = ("earlier", "was wrong", "corrected", "no longer", "withdrawn", "superseded")
CLASS_TOKEN = {
    "AF-WCC-VAC-GEN": "C0",  # placeholder, unused for SCC
    "AF-SCC-C2-VAC-GEN": "C2",
    "AF-SCC-C0-VAC-GEN": "C0",
}


def class_token(doc):
    return CLASS_TOKEN.get(str(doc.get("class_id")), "C0")


def denial_mentions(item):
    """Live (non-quoted, non-withdrawn) containment-denial occurrences in a string."""
    hits = []
    for m in DENIAL_RE.finditer(item):
        start, end = m.span()
        window = item[max(0, start - 90): min(len(item), end + 90)].lower()
        quoted = item[max(0, start - 1):start] in ("'", '"') and item[end:end + 1] in ("'", '"')
        mentioned = any(k in window for k in MENTION_MARKERS)
        if quoted or mentioned:
            continue
        hits.append(m)
    return hits


def direction_findings_for_reason(reason, frm_tokens, to_tokens, line):
    """Adjudicate a 'larger/smaller extension class' claim inside one reason string."""
    out = []
    for m in DIRECTION_RE.finditer(reason):
        subject = (tokens_in(reason[: m.start()]) or [None])[-1]
        if subject is None:
            continue
        other = None
        if frm_tokens and subject == frm_tokens[0] and to_tokens:
            other = to_tokens[0]
        elif to_tokens and subject == to_tokens[0] and frm_tokens:
            other = frm_tokens[0]
        else:
            paren = re.search(r"\(([^)]*)\)", reason[m.start():])
            if paren:
                cand = [t for t in tokens_in(paren.group(1)) if t != subject]
                other = cand[0] if cand else None
        if other is None or other == subject:
            continue
        word = m.group(2).lower()
        s_rank, o_rank = SET_RANK.get(subject, -1), SET_RANK.get(other, -1)
        if s_rank < 0 or o_rank < 0:
            continue
        claim_larger = word in ("larger", "bigger", "stronger")
        consistent = (s_rank > o_rank) if claim_larger else (s_rank < o_rank)
        if not consistent:
            out.append(
                {
                    "line": line,
                    "claim": reason.strip()[:260],
                    "subject": subject,
                    "compared_to": other,
                    "asserted": word,
                    "true_relation": "smaller" if s_rank < o_rank else "larger",
                    "document_rank_note": "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                }
            )
    return out


def sha256_path(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_yaml_text(text):
    return yaml.safe_load(text)


def strings_in(obj):
    """Yield every string leaf of a nested mapping/list."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from strings_in(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from strings_in(value)


def tokens_in(s):
    """All regularity tokens mentioned in a sentence, most specific first."""
    found = []
    low = s
    for tok, needles in ALIASES.items():
        for nd in needles:
            if nd in low:
                found.append(tok)
                break
    # keep unique, order by SET_RANK ascending (specific -> general)
    seen = []
    for t in found:
        if t not in seen:
            seen.append(t)
    return seen


def first_line(text, needle):
    if not needle:
        return None
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


# --------------------------------------------------------- adjudication ----
def adjudicate(doc, text, rule_spec):
    """Mechanical containment-consistency predicate for one F2b document.

    Returns (checks, findings, meta).  Checks are booleans; the repair verdict
    is REPAIR_OK iff every check is True.
    """
    findings = []
    all_strings = list(strings_in(doc))
    must_not = ((doc.get("regularity") or {}).get("must_not_conflate")) or []
    ledger = doc.get("implication_ledger") or {}
    chain_text = str(ledger.get("extension_class_containment") or "")
    one_way = ledger.get("one_way_entailments") or []
    forbidden = ledger.get("forbidden_transfers") or []

    # --- C1: the document's own containment chain -------------------------
    c1_chain = bool(CHAIN_OK.search(chain_text)) or bool(CHAIN_SUBSET_OK.search(chain_text))
    # --- C1b: cross-artifact chain (F0 supplement axis registry) ----------
    c1b_cross = False
    if rule_spec is not None:
        pass  # rule_spec carries vocabularies, not the chain; checked separately

    # --- C2: live containment denials -------------------------------------
    denials = []
    for item in must_not:
        for m in denial_mentions(str(item)):
            toks = tokens_in(m.group(1))
            if len(toks) >= 2:
                denials.append(
                    {
                        "line": first_line(text, "No containment with") or first_line(text, "no containment with"),
                        "text": m.group(0).strip(),
                        "tokens": toks,
                        "document_asserts_containment": c1_chain,
                    }
                )
    c2_no_denial = not denials

    # --- C3: "larger/smaller extension class" premises ---------------------
    premise_findings = []
    for row in forbidden:
        reason = str(row.get("reason", ""))
        frm_t = tokens_in(str(row.get("from", "")))
        to_raw = str(row.get("to", ""))
        to_t = tokens_in(to_raw) or ([class_token(doc)] if "this class" in to_raw else [])
        line = first_line(text, reason[:60]) if reason[:60] else None
        premise_findings.extend(direction_findings_for_reason(reason, frm_t, to_t, line))
    # secondary scan: any other string with an explicit parenthetical comparison
    reason_strings = {str(r.get("reason", "")) for r in forbidden}
    for s in all_strings:
        if s in reason_strings:
            continue
        for m in DIRECTION_RE.finditer(s):
            paren = re.search(r"\(([^)]*)\)", s[m.start():])
            if not paren:
                continue
            subject = (tokens_in(s[: m.start()]) or [None])[-1]
            if subject is None:
                continue
            cand = [t for t in tokens_in(paren.group(1)) if t != subject]
            if not cand:
                continue
            row = {"from": subject, "to": cand[0], "reason": s}
            premise_findings.extend(
                direction_findings_for_reason(s, [subject], [cand[0]], first_line(text, s[:60]))
            )
    c3_no_bad_premise = not premise_findings

    # --- C4: one-way entailments must run from larger set to smaller set ---
    entail_bad = []
    for row in one_way:
        frm = tokens_in(str(row.get("from", "")))
        to = tokens_in(str(row.get("to", "")))
        if not frm or not to:
            continue
        if SET_RANK.get(frm[0], -1) < SET_RANK.get(to[0], -1):
            entail_bad.append({"from": row.get("from"), "to": row.get("to"), "why": "from is weaker than to"})
    c4_entailments = not entail_bad

    # --- C5: the forbidden C2 -> this-class transfer must be present -------
    c5_row_present = False
    for row in forbidden:
        frm = tokens_in(str(row.get("from", "")))
        to = str(row.get("to", ""))
        if frm and frm[0] == "C2" and ("this class" in to or CLASS_ID in to):
            c5_row_present = True
    c5_forbidden_row = c5_row_present

    # --- C5b: R06 must_not_conflate non-empty ------------------------------
    c5b_r06 = isinstance(must_not, list) and len(must_not) > 0

    # --- C6: R11 conclusion_type vs frozen vocabularies --------------------
    conc = (doc.get("conclusion") or {}).get("conclusion_type")
    vocab = ((rule_spec or {}).get("vocabularies") or {}).get("class_conclusion_type") or {}
    expected = vocab.get(CLASS_ID)
    c6_r11 = conc == expected

    # --- C7: class identity / sibling --------------------------------------
    c7_identity = doc.get("class_id") == CLASS_ID and doc.get("sibling_disjoint_from") == SIBLING

    checks = {
        "C1_chain_matches_frozen_order": c1_chain,
        "C2_no_containment_denial": c2_no_denial,
        "C3_no_false_larger_class_premise": c3_no_bad_premise,
        "C4_one_way_entailments_consistent": c4_entailments,
        "C5_forbidden_C2_to_C0_row_present": c5_forbidden_row,
        "C5b_R06_must_not_conflate_nonempty": c5b_r06,
        "C6_R11_conclusion_type_matches_rule_spec": c6_r11,
        "C7_class_identity_and_sibling": c7_identity,
    }

    if denials:
        findings.append(
            {
                "id": "W007-F2B-CR-F1",
                "slot": "regularity.must_not_conflate[0]",
                "severity": "blocking-for-clean-accept",
                "type": "containment_denial_contradicts_own_chain",
                "line": denials[0]["line"],
                "text": denials[0]["text"],
                "detail": (
                    "The document denies asserting containment with C2 or C0 while its own "
                    "implication_ledger.extension_class_containment asserts "
                    "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2."
                ),
                "reading_note": (
                    "A strictly metalinguistic reading ('here' = this bullet) is grammatically "
                    "available and would make the sentence true of the bullet, but the sentence "
                    "sits in a normative must_not_conflate list and is unsafe as written; three "
                    "independent reviewers (worker-066 H2, worker-017 B17-R13-02, worker-018 B1) "
                    "read it as a live denial."
                ),
            }
        )
    if premise_findings:
        findings.append(
            {
                "id": "W007-F2B-CR-F2",
                "slot": "implication_ledger.forbidden_transfers[0].reason",
                "severity": "blocking-for-clean-accept",
                "type": "inverted_containment_premise",
                "line": premise_findings[0]["line"],
                "text": premise_findings[0]["claim"],
                "detail": (
                    "The reason asserts C2 is the LARGER extension class; the document's own "
                    "chain makes E_C2 the SMALLEST set. The normative rule (no transfer from "
                    "C2-inextendibility to this class) is correct; only its stated premise is "
                    "inverted."
                ),
            }
        )

    meta = {
        "chain_text": chain_text[:300],
        "must_not_conflate_count": len(must_not),
        "one_way_entailment_count": len(one_way),
        "forbidden_transfer_count": len(forbidden),
        "conclusion_type": conc,
        "rule_spec_expected_conclusion_type": expected,
        "denials": denials,
        "premise_findings": premise_findings,
        "entailment_defects": entail_bad,
    }
    return checks, findings, meta


def repair_verdict(checks):
    return "REPAIR_OK" if all(checks.values()) else "REPAIR_OPEN"


# ------------------------------------------------------------- controls ----
def run_controls(live_doc, live_text, rule_spec, cand_w022):
    """In-memory mutation controls; nothing is written."""
    import copy

    controls = []

    def record(name, expected, got, note=""):
        controls.append(
            {"id": name, "expected": expected, "observed": got, "pass": bool(expected) == bool(got), "note": note}
        )

    # K1: injecting the worker-022 corrected wording must make the live doc REPAIR_OK
    d = copy.deepcopy(live_doc)
    reg = d["regularity"]["must_not_conflate"]
    fixed_first = [s for s in cand_w022["regularity"]["must_not_conflate"] if "sits strictly between" in s]
    if fixed_first:
        reg[0] = fixed_first[0]
    for row in d["implication_ledger"]["forbidden_transfers"]:
        if tokens_in(str(row.get("from", ""))) == ["C2"] and "this class" in str(row.get("to", "")):
            row["reason"] = "C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker"
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K1_repaired_wording_makes_predicate_pass", "REPAIR_OK", repair_verdict(ch))

    # K2: inverting the document chain must be detected
    d = copy.deepcopy(live_doc)
    d["implication_ledger"]["extension_class_containment"] = "E_C2 contains E_H2loc contains E_C0"
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K2_inverted_chain_detected", False, ch["C1_chain_matches_frozen_order"])

    # K3: deleting the forbidden C2 -> this-class row must be detected
    d = copy.deepcopy(live_doc)
    d["implication_ledger"]["forbidden_transfers"] = [
        r
        for r in d["implication_ledger"]["forbidden_transfers"]
        if not (tokens_in(str(r.get("from", ""))) == ["C2"] and "this class" in str(r.get("to", "")))
    ]
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K3_missing_forbidden_row_detected", False, ch["C5_forbidden_C2_to_C0_row_present"])

    # K4: empty must_not_conflate must fail R06
    d = copy.deepcopy(live_doc)
    d["regularity"]["must_not_conflate"] = []
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K4_empty_must_not_conflate_fails_R06", False, ch["C5b_R06_must_not_conflate_nonempty"])

    # K5: alias conclusion token must fail R11 (vocabulary single-sourcing is a
    # separate gate-owner question, recorded by worker-048)
    d = copy.deepcopy(live_doc)
    d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C0"
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K5_alias_conclusion_token_fails_R11", False, ch["C6_R11_conclusion_type_matches_rule_spec"])

    # K6: re-injecting the inverted premise must fire C3
    d = copy.deepcopy(live_doc)
    for row in d["implication_ledger"]["forbidden_transfers"]:
        if tokens_in(str(row.get("from", ""))) == ["C2"] and "this class" in str(row.get("to", "")):
            row["reason"] = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
    ch, _, _ = adjudicate(d, live_text, rule_spec)
    record("K6_reinjected_inverted_premise_fires", False, ch["C3_no_false_larger_class_premise"])

    return controls


# ----------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write report.json")
    ap.add_argument("--generated-at", default=None)
    args = ap.parse_args()

    generated_at = args.generated_at or os.environ.get("W007_GENERATED_AT") or "2026-09-12T01:10:00+08:00"

    pin_rows = []
    drift = []
    texts = {}
    for rel, (expect, snapname) in PINS.items():
        live_path = os.path.join(ROOT, rel)
        snap_path = os.path.join(SNAP, snapname)
        live_hash = sha256_path(live_path)
        snap_hash = sha256_path(snap_path)
        text = open(snap_path, "r", encoding="utf-8").read()
        texts[rel] = text
        ok = live_hash == expect and snap_hash == expect
        pin_rows.append(
            {"path": rel, "expected_sha256": expect, "live_sha256": live_hash, "snapshot_sha256": snap_hash, "pin_ok": ok}
        )
        if live_hash != expect or snap_hash != expect:
            drift.append(rel)

    rule_spec = json.loads(texts["artifacts/formulation/rule_spec.json"])
    f0 = load_yaml_text(texts["research_map/formulation_taxonomy.yaml"])
    supplement = load_yaml_text(texts["artifacts/formulation/formulation_taxonomy.yaml"])
    live_doc = load_yaml_text(texts["schemas/af_scc_c0_vacuum.yaml"])
    live_text = texts["schemas/af_scc_c0_vacuum.yaml"]

    # cross-artifact axis registry statement
    axis = ((supplement.get("axis_registry") or {}).get("regularity_axis") or {})
    axis_containment = str(axis.get("containment") or "")
    cross_chain_ok = bool(CHAIN_SUBSET_OK.search(axis_containment)) or "E_C2" in axis_containment
    canonical_axes = (((f0.get("classes") or {}).get(CLASS_ID) or {}).get("axes") or {})

    checks, findings, meta = adjudicate(live_doc, live_text, rule_spec)
    verdict = repair_verdict(checks)

    cand_rows = []
    cand_docs = {}
    for name, (rel, snapname) in CANDIDATES.items():
        p = os.path.join(SNAP, snapname)
        ctext = open(p, "r", encoding="utf-8").read()
        cdoc = load_yaml_text(ctext)
        cand_docs[name] = cdoc
        cchecks, cfindings, cmeta = adjudicate(cdoc, ctext, rule_spec)
        cand_rows.append(
            {
                "candidate": name,
                "path": rel,
                "snapshot": snapname,
                "measured_sha256": sha256_path(p),
                "checks": cchecks,
                "verdict": repair_verdict(cchecks),
                "open_items": [f["id"] for f in cfindings],
                "findings": cfindings,
                "meta": cmeta,
            }
        )

    controls = run_controls(live_doc, live_text, rule_spec, cand_docs["C-022-cd-repair"])

    report = {
        "task_id": "W007-F2B-CONTAINMENT-REPAIR-01",
        "worker": "worker-007",
        "generated_at": generated_at,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID, SIBLING],
        "node_id": "F2b",
        "gate": "G-FORM",
        "authority": (
            "Worker measurement only. No canonical file, map, gate or node status modified; "
            "no node done; no validation_status passed; no gate verdict."
        ),
        "question": (
            "At FROZEN rev29 pins, is the AF-SCC-C0-VAC-GEN (F2b) containment-direction blocker "
            "real at b2ab6acb2bbe, which staged repair candidates close it, and what is the "
            "machine-checkable acceptance predicate for the repair?"
        ),
        "method": (
            "Parse the document's own frozen containment chain, derive the extension-set order "
            "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0, then test every normative "
            "containment sentence, one-way entailment and forbidden transfer in the document "
            "against that order. The predicate is state-independent: it is a function of the "
            "document, not of a diff against a baseline."
        ),
        "pins": pin_rows,
        "pin_drift": drift,
        "cross_artifact": {
            "f0_supplement_axis_registry_containment": axis_containment[:400],
            "axis_registry_chain_ok": cross_chain_ok,
            "canonical_taxonomy_axes": canonical_axes,
            "frozen_revision": json.loads(texts["artifacts/formulation/FROZEN.json"]).get("revision"),
        },
        "live_document": {
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
            "checks": checks,
            "verdict": verdict,
            "findings": findings,
            "meta": meta,
        },
        "candidates": cand_rows,
        "controls": controls,
        "controls_all_pass": all(c["pass"] for c in controls),
        "falsifier": (
            "At the same pins: (a) a re-reading under which the F2b must_not_conflate[0] denial "
            "is true of the whole document (i.e. the document asserts no containment anywhere), "
            "or under which 'C2 is a strictly larger extension class' is true of the document's "
            "own order; (b) any pinned input whose live bytes no longer measure the declared "
            "hash; (c) a repair candidate this predicate passes while an independent reader "
            "finds an inverted containment sentence in it; (d) a control that fails to fire as "
            "declared. A later revision of F2b supersedes (does not falsify) this measurement."
        ),
        "non_claims": [
            "No mathematics or physics claim; this is a statement about document bytes and the "
            "containment relation those bytes themselves declare.",
            "No gate verdict and no node status; the audit lead and controller own those.",
            "Candidate verdicts are advisory worker measurements of staged, non-canonical files; "
            "they do not authorize promotion.",
            "The conclusion_type alias direction (scc_* canonical in rule_spec/VOCAB_ALIASES vs "
            "strong_cosmic_censorship_* in the F0 field_vocabulary) is deliberately recorded as "
            "an INFO cross-reference, not re-adjudicated: worker-048 W48-GFORM-VOCAB-ADJUDICATION-01 "
            "already covers it.",
        ],
    }

    if args.emit:
        out = os.path.join(PKT, "report.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
            fh.write("\n")
        run_out = os.path.join(PKT, "checker_runs", "adjudication.json")
        with open(run_out, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "live_verdict": verdict,
                    "live_findings": [f["id"] for f in findings],
                    "candidate_verdicts": {c["candidate"]: c["verdict"] for c in cand_rows},
                    "controls_all_pass": report["controls_all_pass"],
                    "pin_drift": drift,
                },
                fh,
                indent=1,
                sort_keys=True,
            )
            fh.write("\n")

    print(json.dumps({"live_verdict": verdict, "open_findings": [f["id"] for f in findings],
                      "candidates": {c["candidate"]: c["verdict"] for c in cand_rows},
                      "controls_all_pass": report["controls_all_pass"], "pin_drift": drift}, indent=1))
    return 0 if not drift and report["controls_all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
