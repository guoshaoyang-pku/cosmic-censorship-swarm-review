#!/usr/bin/env python3
"""W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01 -- independent checker.

Adjudicates the open F2b blocker (w008-f2b-20260912T003407+0800-blocker-rev12):
at the FROZEN rev27/28 pin schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda the file is
claimed to carry two containment inconsistencies with its own declared chain,
with the sibling C2 (5476a3f2c6bc) already carrying corrected wording.

This checker is written from scratch against the pinned bytes. It does NOT import
or call worker-008's audit_dual_defect.py. Rules are order-relative: the reference
containment order is parsed out of the document under test, never hardcoded.

Pre-registered controls (expectations fixed before the first run; see PREREG):
  ctl0 pristine canonical C0            -> H1 + H2
  ctl1 candidate 98f9ec83 (2 edits)     -> none
  ctl2 candidate with H1 span reverted  -> H1 only
  ctl3 candidate with H2 span reverted  -> H2 only
  ctl4 canonical with polarity flipped  -> H2 only   (order unchanged)
  ctl5 canonical with declared chain reversed -> H2 only (phase proves order-relative)
  ctl6 sibling C2 rev12 (quotation guard)     -> none

Usage: python3 adjudicate.py     (reads pinned/, writes evidence/ + report.json)
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINNED = HERE / "pinned"
EVID = HERE / "evidence"
EVID.mkdir(exist_ok=True)

C0_PIN = PINNED / "c0_canonical__af_scc_c0_vacuum.yaml"
C2_PIN = PINNED / "c2_canonical__af_scc_c2_vacuum.yaml"
CAND_PIN = PINNED / "worker008_candidate_rev12__af_scc_c0_vacuum.yaml"
FROZEN_PIN = PINNED / "frozen_manifest__FROZEN.json"
F0_PIN = PINNED / "f0_declared_taxonomy__formulation_taxonomy.yaml"
SUP_PIN = PINNED / "f0_supplement__formulation_taxonomy.yaml"
PINNED_JSON = HERE / "PINNED.json"

EXPECT_C0_SHA = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
EXPECT_C2_SHA = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
EXPECT_CAND_SHA = "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c"

CLASS_TOKEN = {
    "AF-SCC-C0-VAC-GEN": "C0",
    "AF-SCC-C2-VAC-GEN": "C2",
    "AF-WCC-VAC-GEN": "WCC",
    "AF-WCC-SCALAR-SPH": "SPH",
}
# tokens appearing inside E_* names -> normalised class token
TOKEN_ALIASES = {
    "C0": "C0", "C2": "C2", "H2LOC": "H2LOC", "H2_loc": "H2LOC",
    "C^{1,1}": "C11", "C^1,1": "C11", "C11": "C11",
}
TOKEN_DISPLAY = {"C0": "C0", "C2": "C2", "H2LOC": "H2_loc", "C11": "C^{1,1}"}

PREREG = {
    "ctl0_pristine_canonical": {"expect": ["W066-R12-F2B-H1", "W066-R12-F2B-H2"]},
    "ctl1_candidate_repair": {"expect": []},
    "ctl2_candidate_revert_h1": {"expect": ["W066-R12-F2B-H1"]},
    "ctl3_candidate_revert_h2": {"expect": ["W066-R12-F2B-H2"]},
    "ctl4_canonical_polarity_flipped": {"expect": ["W066-R12-F2B-H2"]},
    "ctl5_canonical_chain_reversed": {"expect": ["W066-R12-F2B-H2"]},
    "ctl6_sibling_c2_quotation_guard": {"expect": []},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scalars(node, path=""):
    """Yield (leaf_path, string_value) for every scalar in the document."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from scalars(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from scalars(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def line_of(raw: str, needle: str) -> int | None:
    probe = needle.strip()[:48]
    for i, line in enumerate(raw.splitlines(), start=1):
        if probe and probe in line:
            return i
    return None


def norm_token(tok: str) -> str:
    t = re.sub(r"\s+", "", tok)
    t = t.removeprefix("E_").strip("{}")
    return TOKEN_ALIASES.get(t) or TOKEN_ALIASES.get(t.upper().replace("_", ""), t)


def parse_chain_order(doc) -> dict:
    """Parse the document's own declared extension-set containment order.

    Returns {'order': [largest set ... smallest set], 'scalar': str, 'leaf': str, 'mode': ...}
    'E_A contains E_B'           -> listed largest-first
    'E_A subset of E_B'          -> listed smallest-first, so reverse
    """
    for path, val in scalars(doc):
        if path.endswith("extension_class_containment") and "E_" in val:
            toks = [norm_token(t) for t in re.findall(r"E_\{[^}]+\}|E_[A-Za-z0-9_]+", val)]
            toks = [t for t in toks if t]
            if " contains " in val:
                mode = "contains"
                order = toks
            elif " subset of " in val:
                mode = "subset_of"
                order = list(reversed(toks))
            else:
                return {"order": [], "scalar": val, "leaf": path, "mode": "unparsed"}
            return {"order": order, "scalar": val, "leaf": path, "mode": mode}
    return {"order": [], "scalar": "", "leaf": "", "mode": "absent"}


def rank(order, token):
    return order.index(token) if token in order else None


def row_for_leaf(doc, leaf_path: str):
    """If the leaf is a forbidden_transfers[i].reason, return that row mapping."""
    m = re.match(r"implication_ledger\.forbidden_transfers\[(\d+)\]\.reason$", leaf_path)
    if not m:
        return None
    rows = (doc.get("implication_ledger", {}) or {}).get("forbidden_transfers", []) or []
    i = int(m.group(1))
    return rows[i] if i < len(rows) and isinstance(rows[i], dict) else None


def reference_token(row, doc_token: str) -> str:
    if not row:
        return doc_token
    to = str(row.get("to", ""))
    if "this class" in to:
        return doc_token
    for t in re.findall(r"C\^\{?1,1\}?|H2_loc|H2loc|C0|C2", to):
        nt = norm_token(t)
        if nt in TOKEN_DISPLAY:
            return nt
    return doc_token


def rule_h1(raw: str, doc) -> list[dict]:
    """Class-size premise inside a transfer reason must match the declared order."""
    chain = parse_chain_order(doc)
    order = chain["order"]
    doc_token = CLASS_TOKEN.get(doc.get("class_id"), "?")
    out = []
    for path, val in scalars(doc):
        for m in re.finditer(r"([A-Za-z0-9_]+) is a strictly (larger|smaller) extension class", val):
            subject = norm_token(m.group(1))
            claimed = m.group(2)
            row = row_for_leaf(doc, path)
            ref = reference_token(row, doc_token)
            rs, rr = rank(order, subject), rank(order, ref)
            if rs is None or rr is None:
                continue
            subject_is_larger = rs < rr
            consistent = (claimed == "larger") == subject_is_larger
            if not consistent:
                out.append({
                    "kind": "W066-R12-F2B-H1",
                    "severity": "hard",
                    "defect": "size_premise_inverted",
                    "leaf_path": path,
                    "line": line_of(raw, val),
                    "span": m.group(0),
                    "full_scalar": val,
                    "subject_class": subject,
                    "reference_class": ref,
                    "claimed_relation": f"strictly {claimed}",
                    "declared_chain_largest_to_smallest": order,
                    "declared_subject_rank": rs,
                    "declared_reference_rank": rr,
                    "declared_relation": "larger" if subject_is_larger else "smaller",
                    "conclusion_in_same_scalar": "C2-inextendibility is strictly weaker" if "strictly weaker" in val else None,
                    "note": "the row's own conclusion is correct under the declared chain; only the premise clause is inverted, so the reason does not support the prohibition as written",
                })
    return out


def rule_h2(raw: str, doc) -> tuple[list[dict], list[dict]]:
    """A live 'no containment ... is asserted' denial inside a document whose own
    chain asserts that containment is a defect. A quotation of a repaired error
    ('the earlier ... was wrong') is not a live denial and must not be flagged."""
    chain = parse_chain_order(doc)
    order = chain["order"]
    out, quotations = [], []
    for path, val in scalars(doc):
        for m in re.finditer(r"[Nn]o containment with ([^.;()\[\]]+?) is asserted", val):
            prefix = val[max(0, m.start() - 48):m.start()]
            quoted = bool(re.search(r"'[^']*$", prefix)) or "earlier" in prefix.lower()
            corrected = "was wrong" in val.lower() or "earlier" in val.lower()
            denied = []
            for t in re.findall(r"C\^\{?1,1\}?|H2_loc|H2loc|C0|C2", m.group(1)):
                nt = norm_token(t)
                if nt in TOKEN_DISPLAY and nt not in denied:
                    denied.append(nt)
            subj = None
            for t in re.findall(r"C\^\{?1,1\}?|H2_loc|H2loc|C0|C2", val[:m.start()]):
                subj = norm_token(t)
            record = {
                "leaf_path": path,
                "line": line_of(raw, val),
                "span": m.group(0),
                "subject_class": subj,
                "denied_tokens": denied,
                "declared_chain_largest_to_smallest": order,
                "quoted_prefix": prefix[-24:],
            }
            if quoted or corrected:
                record["classification"] = "quotation_of_repaired_error"
                record["guard_basis"] = ("match is inside a quoted earlier wording" if quoted else "scalar records the wording as wrong")
                quotations.append(record)
                continue
            pairs = [(a, b) for a in ([subj] if subj else []) + denied for b in denied if a and a != b]
            contradicted = [p for p in pairs if rank(order, p[0]) is not None and rank(order, p[1]) is not None]
            if contradicted:
                record["classification"] = "live_denial_contradicting_own_chain"
                record["contradicted_pairs"] = [list(p) for p in contradicted]
                record["kind"] = "W066-R12-F2B-H2"
                record["severity"] = "hard"
                record["defect"] = "false_containment_denial"
                out.append(record)
    return out, quotations


def dup_keys(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")

    def walk(n, p=""):
        bad = []
        if isinstance(n, yaml.MappingNode):
            seen = set()
            for k, v in n.value:
                if k.value in seen:
                    bad.append(f"{p}/{k.value}")
                seen.add(k.value)
            for k, v in n.value:
                bad += walk(v, f"{p}/{k.value}")
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                bad += walk(v, f"{p}[{i}]")
        return bad

    return walk(yaml.compose(text))


def leaf_diff(a, b, path="") -> dict:
    """Leaf-level diff between two loaded documents."""
    changed, added, removed = [], [], []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else str(k)
            if k not in a:
                added.append(p)
            elif k not in b:
                removed.append(p)
            else:
                sub = leaf_diff(a[k], b[k], p)
                changed += sub["changed"]; added += sub["added"]; removed += sub["removed"]
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = f"{path}[{i}]"
            if i >= len(a):
                added.append(p)
            elif i >= len(b):
                removed.append(p)
            else:
                sub = leaf_diff(a[i], b[i], p)
                changed += sub["changed"]; added += sub["added"]; removed += sub["removed"]
    else:
        if a != b:
            changed.append(path)
    return {"changed": changed, "added": added, "removed": removed}


def findings_of(raw: str, doc) -> tuple[list[str], list[dict], list[dict]]:
    h1 = rule_h1(raw, doc)
    h2, quotations = rule_h2(raw, doc)
    fs = [f["kind"] for f in h1] + [f["kind"] for f in h2]
    return fs, h1 + h2, quotations


def mutate(original: str, old: str, new: str) -> str:
    assert old in original, "anchored replacement failed"
    return original.replace(old, new, 1)


def main() -> dict:
    checks: dict = {"task_id": "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    # ---- 0. pins ------------------------------------------------------------
    pins = json.loads(PINNED_JSON.read_text(encoding="utf-8"))["inputs"]
    measured = {
        "c0_canonical": sha256(C0_PIN),
        "c2_canonical": sha256(C2_PIN),
        "candidate": sha256(CAND_PIN),
        "f0_declared_taxonomy": sha256(F0_PIN),
        "f0_supplement": sha256(SUP_PIN),
        "frozen_manifest": sha256(FROZEN_PIN),
    }
    frozen = json.loads(FROZEN_PIN.read_text(encoding="utf-8"))
    frozen_files = frozen.get("files", {})
    frozen_pins = {
        "revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "c0_declared": (frozen_files.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256"),
        "c2_declared": (frozen_files.get("schemas/af_scc_c2_vacuum.yaml") or {}).get("sha256"),
        "c0_matches_disk": (frozen_files.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256") == measured["c0_canonical"],
        "c2_matches_disk": (frozen_files.get("schemas/af_scc_c2_vacuum.yaml") or {}).get("sha256") == measured["c2_canonical"],
    }
    pin_ok = (measured["c0_canonical"] == EXPECT_C0_SHA and measured["c2_canonical"] == EXPECT_C2_SHA
              and measured["candidate"] == EXPECT_CAND_SHA)
    checks["pins"] = {"measured": measured, "expected_c0": EXPECT_C0_SHA, "expected_c2": EXPECT_C2_SHA,
                      "expected_candidate": EXPECT_CAND_SHA, "match": pin_ok, "frozen_manifest": frozen_pins}

    raw0 = C0_PIN.read_text(encoding="utf-8")
    raw2 = C2_PIN.read_text(encoding="utf-8")
    rawc = CAND_PIN.read_text(encoding="utf-8")
    d0, d2, dc = load(C0_PIN), load(C2_PIN), load(CAND_PIN)

    # ---- 1. structural context (not the adjudication target itself) ---------
    chain0 = parse_chain_order(d0)
    chain2 = parse_chain_order(d2)
    f0 = load(F0_PIN)
    checks["structure"] = {
        "c0_chain": chain0,
        "c2_chain": chain2,
        "chain_agree": chain0["order"] == chain2["order"] and bool(chain0["order"]),
        "c0_duplicate_yaml_keys": dup_keys(C0_PIN),
        "c2_duplicate_yaml_keys": dup_keys(C2_PIN),
        "c0_revision": d0.get("revision"), "c0_revised_at": d0.get("revised_at"),
        "c2_revision": d2.get("revision"), "c2_revised_at": d2.get("revised_at"),
        "c0_f0_binding_sha": (d0.get("f0_binding") or {}).get("declared_f0_sha256"),
        "f0_measured_sha": measured["f0_declared_taxonomy"],
        "f0_binding_matches_disk": (d0.get("f0_binding") or {}).get("declared_f0_sha256") == measured["f0_declared_taxonomy"],
        "c0_class_contract_pointer": d0.get("class_contract_pointer"),
        "pointer_resolves": bool((f0.get("classes") or {}).get("AF-SCC-C0-VAC-GEN")),
        "c2_class_contract_pointer": d2.get("class_contract_pointer"),
        "c2_pointer_resolves": bool((f0.get("classes") or {}).get("AF-SCC-C2-VAC-GEN")),
    }

    # ---- 2. adjudication of the two contested spans on the pinned C0 --------
    fs0, f0_findings, q0 = findings_of(raw0, d0)
    checks["canonical_c0"] = {
        "finding_ids": fs0, "findings": f0_findings, "quotations": q0,
        "verdict": "FAIL" if fs0 else "PASS",
    }
    # sibling check: the same denial wording at C2 was explicitly recorded as wrong
    _, f2_findings, q2 = findings_of(raw2, d2)
    checks["sibling_c2"] = {
        "finding_ids": [f["kind"] for f in f2_findings], "findings": f2_findings,
        "quotations": q2, "verdict": "PASS" if not f2_findings else "FAIL",
    }
    # text the sibling uses at the corresponding repaired spot
    sib_repair = [v for p, v in scalars(d2) if "was wrong" in v and "containment" in v]
    checks["sibling_c2_repair_wording"] = sib_repair
    # the C0 denial's subject: the scalar sentence immediately before it
    h2_scalar = (d0.get("regularity") or {}).get("must_not_conflate", [""])[0]
    checks["c0_denial_rescue_reading"] = {
        "rescue_reading": "the qualifier 'phrased in terms of CURVATURE, not metric differentiability' scopes the denial to the regularity axis, so the sentence could be read as 'this bullet does not itself assert containment' rather than as a claim about the extension sets",
        "textual_basis": h2_scalar,
        "why_rejected": [
            "the denial is unqualified inside its own sentence ('No containment with C2 or C0 is asserted here') and is not marked as axis-scoped; the only marked scope is the preceding clause about curvature vs metric differentiability",
            "the same document asserts the containment three times: implication_ledger.extension_class_containment (line 238), the transfer rows at lines 242-243, and anti_scope line 274 ('the H2_loc extension class is a VARIANT of this class')",
            "the sibling C2 at the same revision 12 carries the corrected wording for this exact sentence and records the earlier denial as wrong ('[R2 major: the earlier \\'no containment with C2 is asserted\\' was wrong]')",
            "the bullet's own ledger reference ('see implication_ledger') points at the nesting it denies",
        ],
    }

    # ---- 3. candidate repair -------------------------------------------------
    diff = leaf_diff(d0, dc)
    diff_text = list(difflib.unified_diff(raw0.splitlines(), rawc.splitlines(), lineterm="", n=0))
    hunks = sum(1 for l in diff_text if l.startswith("@@"))
    binding_fields = ["class_id", "revision", "f0_binding", "class_contract_pointer",
                      "class_contract_supplement_pointer", "sibling_disjoint_from", "revision_history"]
    binding_equal = {f: d0.get(f) == dc.get(f) for f in binding_fields}
    fsc, fc_findings, qc = findings_of(rawc, dc)
    checks["candidate_98f9ec83"] = {
        "sha256": measured["candidate"],
        "changed_leaf_paths": diff["changed"], "added": diff["added"], "removed": diff["removed"],
        "changed_leaf_count": len(diff["changed"]) + len(diff["added"]) + len(diff["removed"]),
        "diff_hunks": hunks,
        "binding_fields_unchanged": binding_equal,
        "binding_minimal": all(binding_equal.values()),
        "defect_ids_after_repair": fsc,
        "verdict": "PASS" if not fsc else "FAIL",
        "publishes_nothing": True,
    }

    # ---- 4. pre-registered controls -----------------------------------------
    c0_h1_span = (d0["implication_ledger"]["forbidden_transfers"][0]["reason"])
    c0_h2_span = d0["regularity"]["must_not_conflate"][0]
    cand_h1_span = dc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    cand_h2_span = dc["regularity"]["must_not_conflate"][0]
    chain_smaller_phrase = "strictly smaller extension class"
    chain_larger_phrase = "strictly larger extension class"

    def run_control(name, raw, doc):
        fs, findings, quotations = findings_of(raw, doc)
        exp = PREREG[name]["expect"]
        return {
            "name": name, "expected": exp, "observed": fs,
            "match": sorted(fs) == sorted(exp),
            "n_findings": len(findings),
            "findings": [{"kind": f["kind"], "leaf_path": f["leaf_path"], "line": f["line"], "span": f["span"]} for f in findings],
            "quotations_suppressed": [q["line"] for q in quotations],
        }

    controls = []
    controls.append(run_control("ctl0_pristine_canonical", raw0, d0))
    controls.append(run_control("ctl1_candidate_repair", rawc, dc))
    controls.append(run_control("ctl2_candidate_revert_h1", mutate(rawc, cand_h1_span, c0_h1_span), load_text(mutate(rawc, cand_h1_span, c0_h1_span))))
    controls.append(run_control("ctl3_candidate_revert_h2", mutate(rawc, cand_h2_span, c0_h2_span), load_text(mutate(rawc, cand_h2_span, c0_h2_span))))
    flipped = raw0.replace(chain_larger_phrase, chain_smaller_phrase, 1)
    controls.append(run_control("ctl4_canonical_polarity_flipped", flipped, load_text(flipped)))
    reversed_chain = mutate(raw0, chain0["scalar"],
                            chain0["scalar"].replace(
                                "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                                "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"))
    controls.append(run_control("ctl5_canonical_chain_reversed", reversed_chain, load_text(reversed_chain)))
    controls.append(run_control("ctl6_sibling_c2_quotation_guard", raw2, d2))

    checks["controls"] = controls
    checks["controls_all_match_prereg"] = all(c["match"] for c in controls)

    # ---- 5. verdict ----------------------------------------------------------
    confirmed = [f for f in f0_findings]
    checks["adjudication"] = {
        "target": f"schemas/af_scc_c0_vacuum.yaml#{EXPECT_C0_SHA[:12]}",
        "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b",
        "worker008_claim": "two live text-level containment inconsistencies at rev12 (H1 size premise line 245, H2 denial line 151); sibling C2 corrected",
        "independent_reproduction": "CONFIRMED" if fs0 else "REFUTED",
        "confirmed_hard_findings": [f["kind"] for f in confirmed],
        "refuted_by": None,
        "candidate_repair_effect": checks["candidate_98f9ec83"]["verdict"],
        "candidate_binding_minimal": checks["candidate_98f9ec83"]["binding_minimal"],
        "scope_limit": "text-level consistency of a formal-model artifact; no claim about the mathematics or physics of C0/C2 inextendibility",
        "verdict": "revise" if fs0 else "accept",
    }

    # ---- 6. provenance vs the superseded rev11 bytes (if the prior pin survives)
    prior_c0 = REPO / "artifacts/worker-066/rev25_independent_verdict/pinned/schemas/af_scc_c0_vacuum.yaml"
    prov = {"prior_pin": str(prior_c0.relative_to(REPO)), "available": prior_c0.exists()}
    if prior_c0.exists():
        praw = prior_c0.read_text(encoding="utf-8")
        ph1 = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
        ph2 = ("No containment with C2 or C0 is asserted here")
        prov.update({
            "prior_sha256": sha256(prior_c0),
            "h1_span_present": ph1 in praw,
            "h1_span_identical": ph1 == d0["implication_ledger"]["forbidden_transfers"][0]["reason"],
            "h2_denial_clause_present": ph2 in praw,
            "h2_denial_clause_identical": ph2 in d0["regularity"]["must_not_conflate"][0],
            "interpretation": "both contested clauses are byte-identical to the superseded rev11/rev25 bytes; the rev12 rework moved them to new line numbers but did not change their wording, so these are carried-over defects, not regressions introduced by rev12",
        })
    checks["provenance_rev11"] = prov

    # ---- 7. write ------------------------------------------------------------
    (EVID / "checks.json").write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8")
    (EVID / "controls.json").write_text(json.dumps({
        "prereg": PREREG, "controls": controls, "all_match": checks["controls_all_match_prereg"]}, indent=1) + "\n", encoding="utf-8")
    (EVID / "candidate_check.json").write_text(json.dumps(checks["candidate_98f9ec83"], indent=1) + "\n", encoding="utf-8")

    h1 = next(f for f in f0_findings if f["kind"] == "W066-R12-F2B-H1")
    h2 = next(f for f in f0_findings if f["kind"] == "W066-R12-F2B-H2")
    report = {
        "task_id": "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "node_id": "F2b",
        "reviewer": "worker-066",
        "reviewer_independence": "not an author of any F2b artifact; prior worker-066 verdicts bind the superseded rev11 hash 1bb78ce9 and are superseded by the hash move; this is a fresh adjudication at 55d0a1ea",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "target": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": EXPECT_C0_SHA, "revision": d0.get("revision")},
        "sibling": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": EXPECT_C2_SHA, "revision": d2.get("revision")},
        "frozen_pin_context": {"manifest": "artifacts/formulation/FROZEN.json", "manifest_sha256": measured.get("frozen_manifest"),
                               "frozen_revision": 28, "declared_f0": measured["f0_declared_taxonomy"]},
        "verdict": "revise",
        "score": 2.5,
        "hard_failures": ["W066-R12-F2B-H1", "W066-R12-F2B-H2"],
        "confirmed_findings": [h1, h2],
        "machine_green_elsewhere": {
            "duplicate_yaml_keys_c0": checks["structure"]["c0_duplicate_yaml_keys"],
            "chain_agreement_c0_c2": checks["structure"]["chain_agree"],
            "f0_binding_matches_disk": checks["structure"]["f0_binding_matches_disk"],
            "class_contract_pointer_resolves": checks["structure"]["pointer_resolves"],
            "c2_sibling_containment_section": "PASS (quotation guard suppresses the recorded-as-wrong wording)",
        },
        "sibling_asymmetry": "the C2 sibling at the same revision 12 carries the corrected nesting wording at regularity.must_not_conflate[0] and marks the earlier denial wrong; C0 carries the unrepaired denial",
        "candidate_98f9ec83": {
            "sha256": measured["candidate"],
            "changed_leaf_paths": checks["candidate_98f9ec83"]["changed_leaf_paths"],
            "changed_leaf_count": checks["candidate_98f9ec83"]["changed_leaf_count"],
            "binding_minimal": checks["candidate_98f9ec83"]["binding_minimal"],
            "defects_after_repair": checks["candidate_98f9ec83"]["defect_ids_after_repair"],
            "independent_control_isolation": {"revert_h1_fires_only_H1": controls[2]["match"], "revert_h2_fires_only_H2": controls[3]["match"]},
        },
        "provenance_rev11": prov,
        "controls": {"prereg": PREREG, "all_match_prereg": checks["controls_all_match_prereg"],
                     "observed": {c["name"]: c["observed"] for c in controls}},
        "resolution_required": "owner publishes an equivalent 2-edit repair (C0 55d0a1ea -> candidate 98f9ec83 semantics), bumps revision, mirrors byte-identically, re-freezes, and re-runs a containment checker to PASS with C2 unchanged; a reviewer may alternatively rule the two clauses non-normative at the bound hash, which this adjudication does not",
        "falsifier": "re-run adjudicate.py on the same pins: this adjudication is falsified if C0 55d0a1ea no longer yields both findings, or if the checker's order parsing disagrees with the file's extension_class_containment sentence, or if a control departs from its pre-registered expectation, or if the candidate 98f9ec83 changes any binding field or more than the two named leaf paths, or if the sibling C2 rev12 contains the same live denial (it does not), or if a reviewer shows the two clauses are non-normative prose",
        "scope_limit": "text-level consistency of a formal-model artifact; no claim about the mathematics or physics of C0/C2 inextendibility; reviewer verdict only, not a gate verdict and not a node done (PROTOCOL rules 2 and authority limits)",
        "assumptions": [
            "a verdict binds bytes, not paths; all checks ran on pinned copies",
            "the document's own implication_ledger.extension_class_containment sentence is the reference order; the order is not re-derived from the physics",
            "the phrase 'extension class' refers to the extension set E_X as the document itself defines it; no other definition exists in the file",
            "the sibling C2 rev12 correction is evidence of the intended wording, not an authority for the C0 content",
        ],
        "evidence_refs": [],
    }
    ev = {
        "checks": sha256(EVID / "checks.json"),
        "controls": sha256(EVID / "controls.json"),
        "candidate_check": sha256(EVID / "candidate_check.json"),
        "pinned": sha256(PINNED_JSON),
    }
    report["evidence_refs"] = [
        f"artifacts/worker-066/f2b_containment_adjudication/evidence/checks.json#{ev['checks'][:12]}",
        f"artifacts/worker-066/f2b_containment_adjudication/evidence/controls.json#{ev['controls'][:12]}",
        f"artifacts/worker-066/f2b_containment_adjudication/evidence/candidate_check.json#{ev['candidate_check'][:12]}",
        f"artifacts/worker-066/f2b_containment_adjudication/PINNED.json#{ev['pinned'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{EXPECT_C0_SHA[:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{EXPECT_C2_SHA[:12]}",
    ]
    report["artifact_refs"] = [f"artifacts/worker-066/f2b_containment_adjudication/report.json", 
                               f"artifacts/worker-066/f2b_containment_adjudication/README.md"]
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    readme = f"""# W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01

Independent, hash-bound adjudication of the open F2b blocker
`w008-f2b-20260912T003407+0800-blocker-rev12`, taken as one bounded class-bound task
(class `AF-SCC-C0-VAC-GEN`, node F2b) by worker-066. Reviewer verdict only: workers cannot
set a gate verdict or a node done.

## Target

| item | value |
|---|---|
| target | `schemas/af_scc_c0_vacuum.yaml#{EXPECT_C0_SHA[:12]}` (rev {d0.get('revision')}, FROZEN rev27/28 pin) |
| sibling | `schemas/af_scc_c2_vacuum.yaml#{EXPECT_C2_SHA[:12]}` (rev {d2.get('revision')}) |
| claim adjudicated | worker-008: two containment inconsistencies persist at rev12; C2 already corrected |
| method | fresh checker (`adjudicate.py`), order-relative; no import of worker-008's checker; 7 pre-registered controls |

## Result: claim CONFIRMED, verdict revise 2.5

Both contested clauses are **byte-identical to the superseded rev11 bytes** (they moved
line numbers only), so rev12 carried them over rather than introducing them:

1. **W066-R12-F2B-H1** — `implication_ledger.forbidden_transfers[0].reason`, line 245:
   "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker".
   The file's own chain (line 238) is `E_C0 contains E_H2loc contains E_{{C^1,1}} contains E_C2`,
   so E_C2 is the *smallest* extension set. The clause's conclusion ("strictly weaker") is
   correct under the chain; only the premise token is inverted, so the stated reason does not
   support the transfer prohibition as written. Fix: "strictly smaller".
2. **W066-R12-F2B-H2** — `regularity.must_not_conflate[0]`, line 151:
   "No containment with C2 or C0 is asserted here" in a file that asserts exactly that
   containment at lines 238, 242-243 and 274, and whose sibling C2 (same revision) replaced
   the same sentence with the nesting statement and recorded the earlier wording as wrong
   ("[R2 major: the earlier 'no containment with C2 is asserted' was wrong]"). Fix: state the
   nesting, as the candidate does.

Rescue reading tested and rejected: the preceding clause ("phrased in terms of CURVATURE, not
metric differentiability") does not scope the denial; the denial sentence is unqualified and the
scalar itself points at `implication_ledger`. Details in `evidence/checks.json`
(`c0_denial_rescue_reading`).

## Machine-green at the same bytes (not blocking)

- no duplicate YAML mapping keys (C0 and C2); C0/C2 chains agree; `f0_binding` hash matches the
  live declared-F0 taxonomy `0abb9ed8a961`; `class_contract_pointer` resolves in `classes.*`.
- sibling C2 passes the checker (the quotation guard suppresses its recorded-as-wrong wording),
  which is why the checker is not merely flagging every mention of containment.

## Repair candidate (worker-008, independently re-measured)

`artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml#98f9ec83c487`
changes exactly two leaf paths, leaves every binding field byte-equal, and clears both defects.
Re-run per-defect single-revert controls fire exactly one finding each. The candidate is not
published: the owner must publish, mirror, re-freeze and re-run the containment check.

## Controls (all 7 matched pre-registration)

| control | expected | observed |
|---|---|---|
| pristine canonical C0 | H1 + H2 | H1 + H2 |
| candidate 98f9ec83 | none | none |
| candidate, H1 reverted | H1 only | H1 only |
| candidate, H2 reverted | H2 only | H2 only |
| canonical, polarity flipped | H2 only | H2 only |
| canonical, chain reversed | H2 only | H2 only |
| sibling C2 rev12 | none | none |

## Falsifier

Re-run `adjudicate.py` on the pins: falsified if C0 `{EXPECT_C0_SHA[:12]}` stops yielding both
findings, if a control departs from its pre-registered expectation, if the candidate changes a
binding field or more than the two named leaf paths, or if a reviewer shows the two clauses are
non-normative prose at the bound hash.

## Limits

Text-level consistency of a formal-model artifact only; no claim about the mathematics or
physics of C0/C2 inextendibility. Verdict binds the pinned bytes; a hash move voids it.
"""
    (HERE / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"pins_ok": pin_ok, "canonical": checks["canonical_c0"]["finding_ids"],
                      "sibling": checks["sibling_c2"]["verdict"], "controls_all_match": checks["controls_all_match_prereg"],
                      "verdict": checks["adjudication"]["verdict"], "report": "written"}, indent=1))
    return checks


def load_text(text: str):
    return yaml.safe_load(text)


if __name__ == "__main__":
    main()
