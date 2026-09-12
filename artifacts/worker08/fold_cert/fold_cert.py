#!/usr/bin/env python3
"""W008-FORMSEP04-FOLD-CERT-01: rev30 fold-candidate certification (worker-008).

Pre-registered question
-----------------------
REC-36 authorizes exactly one rev14 / FROZEN rev30 write that must fold the F2b
D1/D2 content defects.  Which byte images on disk are *foldable* on the
direction axis, i.e. (a) replace the D1 containment denial with the correct
entailment direction, (b) state the D2 containment premise in the correct
direction, and (c) introduce no other direction inversion?

Document-relative rule (same rule as worker-008/FORMSEP04-X3D, sha256 3a1ca2fd9fe3)
----------------------------------------------------------------------------------
Each document declares its own order in `extension_class_containment`:
    E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2
so size_rank(C0)=0 < size_rank(H2loc)=1 < size_rank(C^1,1)=2 < size_rank(C2)=3
(0 = largest extension set).  S_A ("no proper future A extension") entails S_B
iff size_rank(A) <= size_rank(B).  "this class" resolves to the carrier
document's own class_id.  A document whose declared order is not the frozen
order, or which carries a strict entailment the predicate cannot resolve, is
fail-closed (never silently clean).

Defects certified
-----------------
D1 = `regularity.must_not_conflate[*]` entries naming H2_loc.  Five outcomes:
     CORRECT_DIRECTION (nesting asserted AND this class => H2loc asserted),
     DIRECTION_DEFERRED (nesting asserted, direction only in the ledger),
     DENIAL (containment denied, e.g. canonical "No containment ... is asserted"),
     INVERTED (H2loc-inextendibility entails this class), ABSENT (no H2 entry).
D2 = `implication_ledger.forbidden_transfers[*].reason` for from=C2, to=this
     class: CORRECT_PREMISE (C2 smaller / E_C2 subset E_C0), INVERTED_PREMISE
     (C2 larger), MISSING (fail-closed), or negation-aware NOT_INVERTED.

Fold verdicts
-------------
FOLD_CLEAN_STRICT            D1 CORRECT_DIRECTION, D2 CORRECT_PREMISE, 0 other inversions
FOLD_CLEAN_DIRECTION_DEFERRED D1 DIRECTION_DEFERRED, D2 CORRECT_PREMISE, 0 other inversions
FOLD_BLOCKED                 anything else (incl. any unresolved carrier)

Read-only on canonical paths.  Worker-level instrument: no gate verdict, no
node status, no validation_status, no theorem.  Exit 0 measured / 2 fail-closed
pin-parse / 3 control failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE

TASK_ID = "W008-FORMSEP04-FOLD-CERT-01"
ACTOR = "worker-008"
AGENT_ID = "deepseek-flash-08"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"
CREATED_AT = "2026-09-12T01:24:00+08:00"
X3D_INSTRUMENT = "artifacts/worker08/x3d_direction/extend_x3d.py"
X3D_PIN = "3a1ca2fd9fe3"

CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
CANON_C2 = "schemas/af_scc_c2_vacuum.yaml"
MIRROR_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

PINS = {
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    X3D_INSTRUMENT: "3a1ca2fd9fe3 (prefix pin)",
}
# Pre-registered rev29 baseline (the bytes the D1/D2 defects were measured on).
REV29_SNAPSHOT = "artifacts/worker-022/f2b_rev30_corrected/sandbox_control_rev29/schemas/af_scc_c0_vacuum.yaml"
REV29_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
REV29_C2 = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
CANON_AT_START = {CANON_C0: REV29_PIN, CANON_C2: REV29_C2, MIRROR_C0: REV29_PIN}

# Named carriers from the live REC-36 / W-053 / W-034 / W-003 traffic (explicit,
# independent of the mechanical census so a rename cannot silently drop one).
NAMED = {
    "w008_84b5d3fa": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "w080_corrected_51c253c4": "artifacts/worker-029/f2b_repair_candidate_verify/pinned/cand_corrected_51c253c4.yaml",
    "w080_nesting_4951cc96": "artifacts/worker-029/f2b_repair_candidate_verify/pinned/cand_nesting_4951cc96.yaml",
    "w023_9ab32ee3": "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
    "w024_679ab7bc": "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
    "w083_1315427f": "artifacts/worker-083/f2b_candidate_adjudication/snapshot/candidate_083__af_scc_c0_vacuum.yaml",
    "w076_940e54ad": "artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml",
    "w044_48cadb72": "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml",
    "w022_a110f8e8": "artifacts/worker-022/f2b_rev30_corrected/sandbox_corrected/schemas/af_scc_c0_vacuum.yaml",
    "w022_control_rev29": "artifacts/worker-022/f2b_rev30_corrected/sandbox_control_rev29/schemas/af_scc_c0_vacuum.yaml",
    "w003_rev14_sandbox": "artifacts/worker-003/f2b_rev14_candidate_closure/sandbox/schemas/af_scc_c0_vacuum.yaml",
    "w020_patched": "artifacts/worker-020/f2b_rev13_repair_spec/patched_candidate/schemas/af_scc_c0_vacuum.yaml",
}

PIN_GUARD = [CANON_C0, CANON_C2, FROZEN, MIRROR_C0] + sorted(NAMED.values())

TOKEN = r"(?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?|this class)"
SUFFIX = (r"(?:'s)?[\s-]*(?:(?:conclusion|inextendibility)"
          r"|\s+(?:sibling|class|endpoint))")
CLAIM_RX = re.compile(
    r"(?P<ant>" + TOKEN + SUFFIX + r")"
    r"(?P<mid>[^.;]{0,90}?)"
    r"(?P<verb>entails?|implies?|subsum\w*|establish\w*)"
    r"(?P<post>[^.;]{0,60}?)"
    r"(?:(?:the|a|an)\s+)?(?P<cons>" + TOKEN + SUFFIX +
    r"(?:\s*(?:,|and)\s*(?:(?:the|a|an)\s+)?" + TOKEN + SUFFIX + r")*)",
    re.I,
)
CONS_RX = re.compile(r"(?P<tok>" + TOKEN + r")" + SUFFIX, re.I)
ENTAIL_VERB = re.compile(r"\b(?:entails?|implies?|subsum\w*|establish\w*)\b", re.I)
NEG_BEFORE = re.compile(r"\b(?:not|no|never|cannot|does not|do not)\b[^.;]{0,60}$", re.I)
ATTRIBUTION = re.compile(r"worker-\d+|according to|quoted|quotation|must not be cited", re.I)
DENIAL_RX = re.compile(
    r"\bno\s+containment\b|\bno\s+(?:set-?theoretic\s+)?(?:inclusion|nesting)\b"
    r"|\bnot\s+(?:be\s+)?(?:nested|contained|comparable|a\s+subset)\b"
    r"|\bcontainment\s+is\s+not\s+asserted\b|\bare\s+not\s+nested\b",
    re.I,
)
NORM = {"C0": "C0", "C2": "C2", "C^1,1": "C^1,1", "C1,1": "C^1,1", "C^{1,1}": "C^1,1",
        "H2LOC": "H2loc", "H2_loc": "H2loc", "THIS CLASS": "SELF"}
CHAIN_TOKEN = r"(?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?)"
CHAIN_RX = re.compile(
    r"E_?\{?(" + CHAIN_TOKEN + r")\}?(?:\s+(contains|subset of)\s+E_?\{?(" + CHAIN_TOKEN + r")\}?)+",
    re.I,
)
FROZEN_ORDER = ["C0", "H2loc", "C^1,1", "C2"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm_token(raw: str, own: str) -> str:
    r = raw.strip().strip("'\"")
    if re.fullmatch(r"this class(?:'s)?", r, re.I):
        return own
    key = re.sub(r"\s+", "", r).upper().replace("_", "").replace("{", "").replace("}", "")
    for k, v in NORM.items():
        if re.sub(r"\s+", "", k).upper().replace("_", "").replace("{", "").replace("}", "") == key:
            return v
    if "1,1" in key:
        return "C^1,1"
    if key.startswith("H2"):
        return "H2loc"
    return "UNKNOWN"


def parse_chain(text: str, own: str):
    """Parse a declared containment chain. Returns (ranks, direction) or (None, None)."""
    m = CHAIN_RX.search(text or "")
    if not m:
        return None, None
    toks = [norm_token(t, own) for t in re.findall(r"E_?\{?(" + CHAIN_TOKEN + r")\}?", m.group(0), re.I)]
    direction = "contains" if "contains" in m.group(0).lower() else "subset"
    if direction == "subset":
        toks = list(reversed(toks))
    if len(toks) >= 4 and all(t != "UNKNOWN" for t in toks):
        return {t: i for i, t in enumerate(toks)}, direction
    return None, None


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text or "") if s.strip()]


def direction_claims(text: str, own: str, ranks: dict):
    """Return (claims, denials, unresolved) for one prose slot, X3d rule."""
    claims, denials, unresolved = [], [], []
    for sent in sentences(text):
        if not ENTAIL_VERB.search(sent):
            continue
        if ATTRIBUTION.search(sent) and "this class" not in sent:
            continue
        found = False
        for m in CLAIM_RX.finditer(sent):
            preceding = sent[:m.start("verb")]
            if NEG_BEFORE.search(preceding) and not re.search(r"never the reverse", sent[m.end():], re.I):
                denials.append({"sentence": sent[:240]})
                found = True
                continue
            ant = norm_token(re.sub(SUFFIX + r"$", "", m.group("ant").strip(), flags=re.I), own)
            for c in CONS_RX.finditer(m.group("cons")):
                cons = norm_token(c.group("tok"), own)
                if ant == "UNKNOWN" or cons == "UNKNOWN":
                    unresolved.append({"sentence": sent[:240]})
                else:
                    claims.append({"ant": ant, "cons": cons, "ant_rank": ranks[ant],
                                   "cons_rank": ranks[cons], "licensed": ranks[ant] <= ranks[cons],
                                   "sentence": sent[:240]})
                found = True
        if not found and re.search(r"\b(?:entails?|implies?|subsum\w*)\b", sent, re.I):
            before = sent[:ENTAIL_VERB.search(sent).start()]
            if not NEG_BEFORE.search(before) and re.search(TOKEN + r"[^.;]{0,40}$", before, re.I):
                unresolved.append({"sentence": sent[:240]})
    return claims, denials, unresolved


def find_own_class(doc: dict):
    cid = doc.get("class_id")
    return {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2"}.get(cid)


def declared_ranks(doc: dict, own: str):
    for key in ("implication_ledger", "regularity"):
        sec = doc.get(key) or {}
        ranks, direction = parse_chain(sec.get("extension_class_containment") or "", own)
        if ranks:
            return ranks, direction, f"{key}.extension_class_containment"
    # fallback: any leaf ending extension_class_containment
    def leaves(o, pre=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from leaves(v, f"{pre}.{k}" if pre else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from leaves(v, f"{pre}[{i}]")
        else:
            yield pre, o
    for path, v in leaves(doc):
        if path.endswith("extension_class_containment") and isinstance(v, str):
            ranks, direction = parse_chain(v, own)
            if ranks:
                return ranks, direction, path
    return None, None, None


SUPERSEDED_RX = re.compile(
    r"\[[^\]]*(?:wrong|earlier|superseded|obsolete|must not be cited|was not)[^\]]*\]"
    r"|'[^']*(?:wrong|earlier|superseded|obsolete|must not be cited)[^']*'"
    r"|\"[^\"]*(?:wrong|earlier|superseded|obsolete|must not be cited)[^\"]*\"",
    re.I,
)


def strip_superseded(text: str) -> str:
    """Remove bracketed/quoted spans that explicitly mark an older denial as wrong."""
    return SUPERSEDED_RX.sub(" ", text or "")


def classify_d1(doc: dict, own: str, ranks: dict):
    """Classify the H2_loc containment clause in regularity.must_not_conflate[*]."""
    reg = doc.get("regularity") or {}
    entries = [(i, v) for i, v in enumerate(reg.get("must_not_conflate") or [])
               if isinstance(v, str) and re.search(r"H2", v, re.I)]
    if not entries:
        return {"outcome": "ABSENT", "sites": [], "detail": "no H2_loc entry in regularity.must_not_conflate"}
    sites = []
    verdicts = []
    for i, text in entries:
        path = f"regularity.must_not_conflate[{i}]"
        eff = strip_superseded(text)
        claims, denials, unresolved = direction_claims(eff, own, ranks)
        nesting, ndir = parse_chain(eff, own)
        nesting_ok = nesting is not None and [t for t in sorted(nesting, key=nesting.get)] == FROZEN_ORDER
        inverted = [c for c in claims if not c["licensed"]]
        correct = [c for c in claims if c["licensed"]]
        if DENIAL_RX.search(eff):
            outcome = "DENIAL"
        elif inverted:
            outcome = "INVERTED"
        elif unresolved:
            outcome = "UNRESOLVED"
        elif correct:
            outcome = "CORRECT_DIRECTION" if nesting_ok else "CORRECT_DIRECTION_NO_NESTING"
        elif nesting_ok:
            outcome = "DIRECTION_DEFERRED"
        else:
            outcome = "ABSENT"
        verdicts.append(outcome)
        sites.append({"path": path, "outcome": outcome, "nesting_asserted": bool(nesting_ok),
                      "claims": claims, "denials": denials, "unresolved": unresolved,
                      "sentence": text[:300]})
    if "INVERTED" in verdicts:
        overall = "INVERTED"
    elif "UNRESOLVED" in verdicts:
        overall = "UNRESOLVED"
    elif "DENIAL" in verdicts:
        overall = "DENIAL"
    elif "CORRECT_DIRECTION" in verdicts:
        overall = "CORRECT_DIRECTION"
    elif "CORRECT_DIRECTION_NO_NESTING" in verdicts:
        overall = "CORRECT_DIRECTION_NO_NESTING"
    elif "DIRECTION_DEFERRED" in verdicts:
        overall = "DIRECTION_DEFERRED"
    else:
        overall = "ABSENT"
    return {"outcome": overall, "sites": sites}


def classify_d2(doc: dict, own: str, ranks: dict):
    """Classify the C2 -> this class transfer premise in implication_ledger.forbidden_transfers."""
    led = doc.get("implication_ledger") or {}
    fts = led.get("forbidden_transfers") or []
    if not fts:
        return {"outcome": "MISSING", "sites": [], "detail": "no forbidden_transfers"}
    sites, verdicts = [], []
    for i, t in enumerate(fts):
        if not isinstance(t, dict):
            continue
        frm, to = str(t.get("from", "")), str(t.get("to", ""))
        if not (re.search(r"C2", frm) and re.search(r"this class", to, re.I)):
            continue
        reason = str(t.get("reason", ""))
        path = f"implication_ledger.forbidden_transfers[{i}].reason"
        low = reason.lower()
        # negation-aware premise extraction: a negated "not a strictly larger" is not an inversion
        low_pos = re.sub(r"\b(?:not|no|never)\b[^.;]{0,30}?(?:strictly\s+)?(?:larger|smaller)", " ", low)
        larger_c2 = bool(re.search(r"C2[^.;]{0,60}?(?:strictly\s+)?larger", low_pos)
                         or re.search(r"(?:strictly\s+)?larger[^.;]{0,60}?C2", low_pos))
        smaller_c2 = bool(re.search(r"C2[^.;]{0,60}?(?:strictly\s+)?smaller", low)
                          or re.search(r"(?:strictly\s+)?smaller[^.;]{0,60}?C2", low))
        c0_smaller = bool(re.search(r"C0[^.;]{0,60}?(?:strictly\s+)?smaller", low))
        subset_e_c2 = bool(re.search(r"E_?\{?C2\}?\s+subset\s+of\s+E_?\{?C0\}?", reason, re.I))
        subset_e_c0 = bool(re.search(r"E_?\{?C0\}?\s+subset\s+of\s+E_?\{?C2\}?", reason, re.I))
        reason_ranks, _ = parse_chain(reason, own)
        reason_frozen_chain = bool(reason_ranks) and [t for t in sorted(reason_ranks, key=reason_ranks.get)] == FROZEN_ORDER
        c2_smallest = bool(re.search(r"C2[^.;]{0,80}?(?:smallest|lowest)\s+(?:extension\s+)?set", low)) or \
            bool(re.search(r"E_?\{?C2\}?[^.;]{0,60}?(?:smallest|lowest)", low))
        if larger_c2 or c0_smaller or subset_e_c0:
            outcome = "INVERTED_PREMISE"
        elif smaller_c2 or subset_e_c2 or reason_frozen_chain or c2_smallest:
            outcome = "CORRECT_PREMISE"
        else:
            outcome = "NOT_INVERTED_UNCLASSIFIED"
        verdicts.append(outcome)
        sites.append({"path": path, "outcome": outcome, "from": frm, "to": to, "reason": reason[:300]})
    if not sites:
        return {"outcome": "MISSING", "sites": [], "detail": "no C2->this class transfer row"}
    if "INVERTED_PREMISE" in verdicts:
        overall = "INVERTED_PREMISE"
    elif "CORRECT_PREMISE" in verdicts:
        overall = "CORRECT_PREMISE"
    else:
        overall = "NOT_INVERTED_UNCLASSIFIED"
    return {"outcome": overall, "sites": sites}


def whole_doc_scan(doc: dict, own: str, ranks: dict):
    """X3d strict-entailment direction scan over pre-registered normative slots."""
    slots = []

    def add(path, value):
        if isinstance(value, str) and value.strip():
            slots.append((path, value))

    reg = doc.get("regularity") or {}
    for i, v in enumerate(reg.get("must_not_conflate") or []):
        add(f"regularity.must_not_conflate[{i}]", v)
    add("regularity.extension_class_containment", reg.get("extension_class_containment"))
    led = doc.get("implication_ledger") or {}
    add("implication_ledger.extension_class_containment", led.get("extension_class_containment"))
    add("implication_ledger.subsumption_note", led.get("subsumption_note"))
    for i, v in enumerate(led.get("forbidden_weakenings") or []):
        add(f"implication_ledger.forbidden_weakenings[{i}]", v if isinstance(v, str) else (v or {}).get("reason"))
    for i, v in enumerate(led.get("one_way_entailments") or []):
        add(f"implication_ledger.one_way_entailments[{i}].reason", (v or {}).get("reason"))
    for i, v in enumerate(led.get("forbidden_transfers") or []):
        add(f"implication_ledger.forbidden_transfers[{i}].reason", (v or {}).get("reason"))
    hits, unresolved, licensed = [], [], []
    for path, text in slots:
        claims, denials, unres = direction_claims(text, own, ranks)
        for c in claims:
            (licensed if c["licensed"] else hits).append({**c, "path": path})
        for u in unres:
            unresolved.append({**u, "path": path})
    return {"inverted_hits": hits, "unresolved": unresolved, "licensed_claims": licensed}


def leaf_diff(a: dict, b: dict):
    """Leaf-level differences a -> b (path, old, new)."""
    def leaves(o, pre=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from leaves(v, f"{pre}.{k}" if pre else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from leaves(v, f"{pre}[{i}]")
        else:
            yield pre, o
    la = dict(leaves(a))
    lb = dict(leaves(b))
    changed = []
    for k in sorted(set(la) | set(lb)):
        if la.get(k) != lb.get(k):
            changed.append({"path": k, "live": str(la.get(k))[:200], "candidate": str(lb.get(k))[:200]})
    return changed


def classify_doc(doc: dict, rel: str, live: dict | None):
    own = find_own_class(doc)
    if own is None:
        return {"path": rel, "sha256": sha256(REPO / rel), "own_token": None,
                "outcome": "NOT_A_SCHEMA", "reason": f"class_id={doc.get('class_id')!r}"}
    ranks, direction, chain_path = declared_ranks(doc, own)
    if not ranks:
        return {"path": rel, "sha256": sha256(REPO / rel), "own_token": own,
                "outcome": "FAIL_CLOSED_NO_CHAIN",
                "reason": "no parsable extension_class_containment"}
    if [t for t in sorted(ranks, key=ranks.get)] != FROZEN_ORDER:
        return {"path": rel, "sha256": sha256(REPO / rel), "own_token": own,
                "outcome": "FAIL_CLOSED_ORDER", "declared_order": sorted(ranks, key=ranks.get)}
    d1 = classify_d1(doc, own, ranks)
    d2 = classify_d2(doc, own, ranks)
    scan = whole_doc_scan(doc, own, ranks)
    if own != "C0":
        fold = "NOT_APPLICABLE_NON_C0"
    elif d1["outcome"] == "CORRECT_DIRECTION" and d2["outcome"] == "CORRECT_PREMISE" \
            and not scan["inverted_hits"] and not scan["unresolved"]:
        fold = "FOLD_CLEAN_STRICT"
    elif d1["outcome"] == "DIRECTION_DEFERRED" and d2["outcome"] == "CORRECT_PREMISE" \
            and not scan["inverted_hits"] and not scan["unresolved"]:
        fold = "FOLD_CLEAN_DIRECTION_DEFERRED"
    else:
        fold = "FOLD_BLOCKED"
    return {
        "path": rel, "sha256": sha256(REPO / rel), "own_token": own,
        "declared_order": [t for t in sorted(ranks, key=ranks.get)],
        "chain_path": chain_path, "containment_direction": direction,
        "D1_h2_clause": d1, "D2_transfer_premise": d2,
        "other_inverted_hits": scan["inverted_hits"],
        "unresolved_carriers": scan["unresolved"],
        "licensed_claims": len(scan["licensed_claims"]),
        "fold_verdict": fold,
        "changed_leaves_vs_live": len(leaf_diff(live, doc)) if (live is not None and own == "C0") else None,
        "changed_paths_vs_live": [c["path"] for c in leaf_diff(live, doc)][:20]
        if (live is not None and own == "C0") else None,
    }


def census_paths(day_start: float):
    seen, out = set(), []
    for p in sorted((REPO / "artifacts").rglob("*af_scc_c0_vacuum*")):
        if p.is_file() and p.stat().st_mtime >= day_start:
            rel = str(p.relative_to(REPO))
            if rel not in seen:
                seen.add(rel)
                out.append(rel)
    for rel in [CANON_C0, MIRROR_C0]:
        if rel not in seen:
            seen.add(rel)
            out.append(rel)
    for rel in NAMED.values():
        if rel not in seen and (REPO / rel).exists():
            seen.add(rel)
            out.append(rel)
    return out


def synthetic(own: str, h2: str, ft_reason: str = "C2 is a strictly smaller extension class (E_C2 subset of E_C0)"):
    cid = "AF-SCC-C0-VAC-GEN" if own == "C0" else "AF-SCC-C2-VAC-GEN"
    return {
        "class_id": cid,
        "regularity": {
            "extension_class_containment": "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
            "must_not_conflate": [h2],
        },
        "implication_ledger": {
            "forbidden_transfers": [
                {"from": "no proper future C2 extension", "to": "this class", "reason": ft_reason}
            ]
        },
    }


def synth_audit(label: str, doc: dict):
    tmp = OUT / f"_synth_{label}.yaml"
    tmp.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    res = classify_doc(doc, str(tmp.relative_to(REPO)), None)
    res["label"] = label
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(OUT / "report.json"))
    ap.add_argument("--census", default=str(OUT / "candidates.json"))
    args = ap.parse_args()

    t0 = time.time()
    guard_t0 = {rel: (sha256(REPO / rel) if (REPO / rel).exists() else None) for rel in PIN_GUARD}
    pins = {}
    for rel, exp in PINS.items():
        p = REPO / rel
        got = sha256(p) if p.exists() else None
        ok = (got == exp) if rel != X3D_INSTRUMENT else (got is not None and got.startswith(X3D_PIN))
        pins[rel] = {"expected": exp, "measured": got, "match": ok}
    if not all(v["match"] for v in pins.values()):
        print(json.dumps({"verdict": "FAIL-CLOSED", "reason": "pin mismatch", "pins": pins}, indent=1))
        return 2

    live = yaml.safe_load((REPO / CANON_C0).read_text(encoding="utf-8"))
    rev29 = yaml.safe_load((REPO / REV29_SNAPSHOT).read_text(encoding="utf-8"))
    for rel, exp in CANON_AT_START.items():
        got = sha256(REPO / rel) if (REPO / rel).exists() else None
        pins[rel] = {"rev29_expected": exp, "measured_t1": got, "moved": got != exp}
    day_start = datetime(2026, 9, 12, 0, 0).timestamp()
    paths = census_paths(day_start)

    missing_named = [rel for rel in NAMED.values() if not (REPO / rel).exists()]
    if missing_named:
        print(json.dumps({"verdict": "FAIL-CLOSED", "reason": "named carrier missing",
                          "missing": missing_named}, indent=1))
        return 2

    rows, errors = [], []
    for rel in paths:
        try:
            doc = yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors.append({"path": rel, "error": f"{type(e).__name__}: {e}"})
            continue
        if not isinstance(doc, dict):
            continue
        rows.append(classify_doc(doc, rel, rev29))

    # dedupe by sha256, keeping the NAMED label / shortest path
    by_hash = {}
    for r in rows:
        h = r["sha256"]
        prev = by_hash.get(h)
        if prev is None or len(r["path"]) < len(prev["path"]):
            by_hash[h] = r
    unique = sorted(by_hash.values(), key=lambda r: r["sha256"])

    # controls: on-disk named carriers + synthetic mutants
    named_rows = {}
    by_path = {r["path"]: r for r in rows}
    for label, rel in NAMED.items():
        if rel in by_path:
            named_rows[label] = by_path[rel]
    synth = [
        synth_audit("k5_c0_correct_explicit",
                    synthetic("C0", "the extension sets are nested: E_C2 subset of E_{C^1,1} subset "
                                    "of E_H2loc subset of E_C0; this class's conclusion ENTAILS "
                                    "H2_loc-inextendibility, never the reverse")),
        synth_audit("k7_c0_h2_converse_canary",
                    synthetic("C0", "the extension sets are nested: E_C2 subset of E_{C^1,1} subset "
                                    "of E_H2loc subset of E_C0; H2_loc-inextendibility ENTAILS this "
                                    "class's conclusion")),
        synth_audit("k8_c0_larger_c2_mutant",
                    synthetic("C0", "the extension sets are nested: E_C2 subset of E_{C^1,1} subset "
                                    "of E_H2loc subset of E_C0; this class's conclusion ENTAILS "
                                    "H2_loc-inextendibility",
                              ft_reason="C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")),
        synth_audit("k9_c0_no_chain",
                    {"class_id": "AF-SCC-C0-VAC-GEN", "regularity": {"must_not_conflate": ["x"]}}),
        synth_audit("k10_c0_double_negation_not_larger",
                    synthetic("C0", "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0; this "
                                    "class's conclusion ENTAILS H2_loc-inextendibility",
                              ft_reason="C2 is NOT a strictly larger extension class; C2 is strictly smaller")),
        synth_audit("k11_c2_same_sentence_is_licensed",
                    synthetic("C2", "the extension sets are nested: E_C2 subset of E_{C^1,1} subset "
                                    "of E_H2loc subset of E_C0; H2_loc-inextendibility ENTAILS this "
                                    "class's conclusion")),
    ]

    expectations = {
        "rev29_control_b2ab6acb2bbe": ("DENIAL", "INVERTED_PREMISE", "FOLD_BLOCKED"),
        "w008_84b5d3fa": ("INVERTED", "CORRECT_PREMISE", "FOLD_BLOCKED"),
        "w080_corrected_51c253c4": ("CORRECT_DIRECTION", "CORRECT_PREMISE", "FOLD_CLEAN_STRICT"),
        "w080_nesting_4951cc96": ("DIRECTION_DEFERRED", "CORRECT_PREMISE", "FOLD_CLEAN_DIRECTION_DEFERRED"),
        "k5_c0_correct_explicit": ("CORRECT_DIRECTION", "CORRECT_PREMISE", "FOLD_CLEAN_STRICT"),
        "k7_c0_h2_converse_canary": ("INVERTED", "CORRECT_PREMISE", "FOLD_BLOCKED"),
        "k8_c0_larger_c2_mutant": ("CORRECT_DIRECTION", "INVERTED_PREMISE", "FOLD_BLOCKED"),
        "k9_c0_no_chain": ("FAIL_CLOSED_NO_CHAIN", None, None),
        "k10_c0_double_negation_not_larger": ("CORRECT_DIRECTION", "CORRECT_PREMISE", "FOLD_CLEAN_STRICT"),
        "k11_c2_same_sentence_is_licensed": (None, None, "NOT_APPLICABLE_NON_C0"),
    }
    observed = {}
    canon_row = by_path.get(REV29_SNAPSHOT)
    if canon_row is not None:
        observed["rev29_control_b2ab6acb2bbe"] = ("D1:" + canon_row["D1_h2_clause"]["outcome"],
                                                  "D2:" + canon_row["D2_transfer_premise"]["outcome"],
                                                  canon_row["fold_verdict"])
    for label, r in named_rows.items():
        observed[label] = ("D1:" + r["D1_h2_clause"]["outcome"],
                           "D2:" + r["D2_transfer_premise"]["outcome"],
                           r["fold_verdict"])
    for r in synth:
        if r.get("own_token") not in (None, "C0") and "fold_verdict" in r:
            observed[r["label"]] = (None, None, r["fold_verdict"])
            continue
        if str(r.get("outcome", "")).startswith("FAIL_CLOSED"):
            observed[r["label"]] = (r["outcome"], None, None)
        else:
            observed[r["label"]] = ("D1:" + r["D1_h2_clause"]["outcome"],
                                    "D2:" + r["D2_transfer_premise"]["outcome"],
                                    r["fold_verdict"])
    controls = []
    for key, exp in expectations.items():
        got = observed.get(key)
        exp_t = tuple((None if e is None else e) for e in exp)
        got_t = None if got is None else tuple(
            (None if g is None else (g.split(":", 1)[1] if g.startswith(("D1:", "D2:")) else g))
            for g in got)
        controls.append({"control": key, "expected": list(exp), "observed": list(got) if got else None,
                         "pass": got_t == exp_t})
    ok = all(c["pass"] for c in controls)
    guard_t1 = {rel: (sha256(REPO / rel) if (REPO / rel).exists() else None) for rel in PIN_GUARD}
    pin_guard_stable = guard_t0 == guard_t1
    if not pin_guard_stable:
        print(json.dumps({"verdict": "FAIL-CLOSED", "reason": "pin guard moved during run",
                          "t0": guard_t0, "t1": guard_t1}, indent=1))
        return 2
    live_row = next((r for r in rows if r["path"] == CANON_C0), None)
    mirror_row = next((r for r in rows if r["path"] == MIRROR_C0), None)
    live_t1 = None
    if live_row is not None:
        live_t1 = {"path": CANON_C0, "sha256": live_row["sha256"],
                   "mirror_sha256": mirror_row["sha256"] if mirror_row else None,
                   "mirror_aligned": bool(mirror_row and mirror_row["sha256"] == live_row["sha256"]),
                   "D1": live_row["D1_h2_clause"]["outcome"],
                   "D2": live_row["D2_transfer_premise"]["outcome"],
                   "other_inverted_hits": len(live_row["other_inverted_hits"]),
                   "unresolved_carriers": len(live_row["unresolved_carriers"]),
                   "fold_verdict": live_row["fold_verdict"],
                   "changed_leaves_vs_rev29": live_row.get("changed_leaves_vs_live"),
                   "changed_paths_vs_rev29": live_row.get("changed_paths_vs_live"),
                   "measured_as": "T1 measurement after the 01:25:42 canonical write; FROZEN.json still rev29, so this is a measurement on live bytes, not a gate verdict"}

    clean_strict = [r["path"] for r in unique if r.get("fold_verdict") == "FOLD_CLEAN_STRICT"]
    clean_deferred = [r["path"] for r in unique if r.get("fold_verdict") == "FOLD_CLEAN_DIRECTION_DEFERRED"]
    blocked = [r for r in unique if r.get("fold_verdict") == "FOLD_BLOCKED"]
    fail_closed_docs = [{"path": r["path"], "outcome": r.get("outcome")} for r in unique
                        if str(r.get("outcome", "")).startswith("FAIL_CLOSED")]
    out = {
        "instrument": "worker-008/FORMSEP04-FOLD-CERT/v1",
        "task_id": TASK_ID, "actor": ACTOR, "agent_id": AGENT_ID,
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "node_id": NODE_ID, "gate": GATE, "created_at": CREATED_AT,
        "rule": "document-relative size_rank license from each document's own extension_class_containment "
                "(same rule as worker-008/FORMSEP04-X3D v1, sha256 " + X3D_PIN + "); "
                "D1 = regularity.must_not_conflate[*] naming H2_loc; D2 = implication_ledger."
                "forbidden_transfers[C2 -> this class].reason",
        "pins": pins, "pin_guard_t0": guard_t0, "pin_guard_t1": guard_t1,
        "pin_guard_stable": pin_guard_stable,
        "live_T1": live_t1,
        "census": {"day_start_utc_offset": "+08:00", "files_matched": len(paths),
                   "unique_byte_images": len(unique), "parse_errors": errors,
                   "unique_docs": unique},
        "named_controls": named_rows,
        "synthetic_controls": synth,
        "controls": controls, "controls_all_pass": ok,
        "summary": {
            "FOLD_CLEAN_STRICT": clean_strict,
            "FOLD_CLEAN_DIRECTION_DEFERRED": clean_deferred,
            "FOLD_BLOCKED_count": len(blocked),
            "live_T1_fold_verdict": live_t1["fold_verdict"] if live_t1 else None,
            "FAIL_CLOSED_docs": fail_closed_docs,
            "FOLD_BLOCKED": [{"path": r["path"], "sha256": r["sha256"],
                              "D1": r["D1_h2_clause"]["outcome"],
                              "D2": r["D2_transfer_premise"]["outcome"],
                              "other_hits": len(r["other_inverted_hits"])} for r in blocked][:40],
        },
        "verdict": "FOLD_CERT_MEASURED" if (ok and live_t1 and live_t1["fold_verdict"] != "FOLD_BLOCKED")
                   else ("CONTROL_FAILURE" if not ok else "LIVE_T1_STILL_BLOCKED"),
        "next_falsifier": "Re-run at the same pins and carrier sha256s: the certification is falsified if a "
                          "carrier classified INVERTED/DENIAL here orders this class (C0) => H2_loc in its own "
                          "bytes; if a FOLD_CLEAN_STRICT carrier is shown to lack the direction or to carry "
                          "another inversion; if the live canonical is not DENIAL+INVERTED_PREMISE; if any "
                          "control does not reproduce its expectation; or if any input hash moves (a later "
                          "revision supersedes rather than falsifies).",
        "does_not_claim": ["no gate verdict; G-FORM stays pending for the controller/lead-audit",
                           "no node status; F2b stays active",
                           "no full-schema verdict; this is a candidate-level direction certification",
                           "no canonical write; every carrier was read-only"],
    }
    (REPO / args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    (REPO / args.census).write_text(json.dumps(
        {"task_id": TASK_ID, "pins": {k: v["measured"] for k, v in pins.items()},
         "unique_docs": unique, "parse_errors": errors}, indent=1), encoding="utf-8")
    print(json.dumps({"verdict": out["verdict"], "controls": controls,
                      "clean_strict": clean_strict, "clean_deferred": clean_deferred,
                      "blocked": len(blocked), "runtime_s": round(time.time() - t0, 2)}, indent=1))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
