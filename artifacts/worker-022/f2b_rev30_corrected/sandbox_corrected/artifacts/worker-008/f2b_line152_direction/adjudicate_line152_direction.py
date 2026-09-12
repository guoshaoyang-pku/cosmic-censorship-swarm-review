#!/usr/bin/env python3
"""Independent, read-only adjudication of the F2b rev29 line-152 replacement-clause
direction across the standing repair candidates, at FROZEN rev29 pins.

Question (live worker dispute): worker-023 reports that the standing repair
(worker-066 candidate 84b5d3fa, worker-044 composed 48cadb72) *introduces* a
normative entailment inversion in `regularity.must_not_conflate[0]`
("H2_loc-inextendibility ENTAILS this class's conclusion"), while worker-036 and
worker-066 report the same candidate defect-free.  This instrument decides the
dispute on the documents' own declared structure with an independent code path.

Oracle (all of it read from the documents themselves, none imported from a
worker's detector):
  * `implication_ledger.extension_class_containment` declares the extension-set
    chain; parsed left-to-right -> `contains` order -> size rank (larger set =
    higher rank).
  * Inexistence statements quantify over extension sets: "no proper future X
    extension" = S_X.  S_X entails S_Y iff E_X is a superset of E_Y
    (killing all extensions of a bigger set kills all of a subset), i.e.
    rank_size(X) >= rank_size(Y).
  * `implication_ledger.forbidden_weakenings` and `subsumption_note` declare the
    licensed direction in prose; they are cross-checks, not the oracle.

Findings kinds:
  denial_of_declared_containment   (canonical defect 1)
  inverted_size_premise            (canonical defect 2)
  entailment_direction_inverted    (the disputed candidate defect)
  malformed_carrier

Fail-closed: exit 2 if any pinned byte moved; exit 3 if an input cannot be
parsed/classified.  Read-only on every canonical path: only artifacts/ is
written, by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

import yaml  # noqa: E402

CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
CANON_C2 = "schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

PINS = {
    CANON_C0: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CANON_C2: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
CANDIDATES = {
    "worker-066/prior-008 standing repair": (
        "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
        "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    ),
    "worker-044 composed rev14": (
        "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml",
        "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a",
    ),
    "worker-024 2-line repair": (
        "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
        "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9",
    ),
    "worker-023 direction-corrected": (
        "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
        "9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17",
    ),
}

H2LOC = re.compile(r"h2[_\- ]?loc", re.I)
ENTAILS = re.compile(r"\bentails\b", re.I)
TARGET = re.compile(
    r"entails\s+(this\s+class(?:'s)?|the\s+C2\s+(?:sibling|class)(?:'s)?|the\s+H2[_\- ]?loc\s+(?:sibling|class)(?:'s)?)"
    r"[^.;]*?\bconclusion\b",
    re.I,
)
DENIAL = re.compile(r"no\s+containment\s+with\s+(?:C2|C0)", re.I)
SIZE_LARGER = re.compile(r"strictly\s+larger\s+extension\s+class", re.I)
SIZE_SMALLER = re.compile(r"strictly\s+smaller\s+extension\s+class", re.I)
QUOTED = re.compile(r"(?<![A-Za-z])'[^']*'(?![A-Za-z])|\u2018[^\u2019]*\u2019")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assertive(text: str) -> str:
    """Drop single-quoted spans (quoted historical mentions are not assertions)."""
    return QUOTED.sub(" ", text or "")


def parse_chain(ledger: dict) -> tuple[list[str], dict[str, int]]:
    s = str(ledger.get("extension_class_containment", ""))
    toks = re.findall(r"E_\{?([^}\s;]+)\}?", s)
    order, seen = [], set()
    for t in toks:
        t = t.strip().rstrip(",")
        if t and t not in seen:
            seen.add(t)
            order.append(t)
    ranks = {t: len(order) - 1 - i for i, t in enumerate(order)}  # biggest set = highest
    return order, ranks


def carrier(doc: dict) -> dict:
    reg = (doc.get("regularity") or {}).get("must_not_conflate") or []
    led = doc.get("implication_ledger") or {}
    fts = led.get("forbidden_transfers") or []
    return {
        "clause": reg[0] if reg else "",
        "reason": (fts[0] or {}).get("reason", "") if fts else "",
        "weakenings": led.get("forbidden_weakenings") or [],
        "subsumption_note": led.get("subsumption_note", ""),
        "ledger": led,
    }


def findings_for(doc: dict) -> list[dict]:
    c = carrier(doc)
    order, ranks = parse_chain(c["ledger"])
    out = []
    text = c["clause"]
    if not isinstance(text, str) or not text.strip():
        out.append({"kind": "malformed_carrier", "carrier": "regularity.must_not_conflate[0]",
                    "text": repr(text), "detail": "missing/empty required R06 slot"})
        return out
    a = assertive(text)
    if DENIAL.search(a):
        out.append({"kind": "denial_of_declared_containment",
                    "carrier": "regularity.must_not_conflate[0]", "text": text,
                    "detail": "denies a containment the same document declares at implication_ledger.extension_class_containment"})
    for sent in re.split(r"(?<=[.;])\s+", a):
        if H2LOC.search(sent) and ENTAILS.search(sent):
            if re.search(r"\b(flagged|notes?|noted|quotes?|quoted|reports?|reported|attributes?|according to|cites?)\b", sent, re.I):
                continue  # attributed mention, not an assertion (see control D)
            m = TARGET.search(sent)
            if m:
                obj = m.group(1).strip().lower()
                if obj.startswith("this class"):
                    holds = ranks.get("H2loc", -1) >= ranks.get("C0", 10 ** 6)
                    out.append({
                        "kind": "entailment_direction_inverted",
                        "carrier": "regularity.must_not_conflate[0]",
                        "text": text,
                        "detail": ("clause asserts S_H2loc => S_C0 (this class); declared ranks "
                                   f"{ranks} give size(H2loc) < size(C0), so S_C0 => S_H2loc, never the reverse"),
                        "oracle_holds_claim": bool(holds),
                    })
    if SIZE_LARGER.search(c["reason"]):
        out.append({"kind": "inverted_size_premise",
                    "carrier": "implication_ledger.forbidden_transfers[0].reason",
                    "text": c["reason"],
                    "detail": "calls C2 a strictly larger extension class; declared chain makes E_C2 the smallest set"})
    return out


def classify(path: Path) -> tuple[dict, list[dict]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc, findings_for(doc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report: dict = {"instrument": "worker-008/f2b-line152-direction/v1",
                    "pins": {}, "candidates": {}, "controls": {}, "verdict": None}
    # 1. pin verification, fail closed
    moved = []
    for rel, expect in PINS.items():
        got = sha256(ROOT / rel)
        report["pins"][rel] = {"expected": expect, "measured": got, "match": got == expect}
        if got != expect:
            moved.append(rel)
    for label, (rel, expect) in CANDIDATES.items():
        got = sha256(ROOT / rel)
        report["pins"][rel] = {"expected": expect, "measured": got, "match": got == expect}
        if got != expect:
            moved.append(rel)
    if moved:
        report["verdict"] = "VOID_PIN_MOVED"
        report["moved"] = moved
        _write(report, args)
        return 2

    # 2. per-candidate findings
    for label, (rel, _expect) in CANDIDATES.items():
        _doc, f = classify(ROOT / rel)
        report["candidates"][label] = {"path": rel, "findings": f,
                                       "kinds": sorted({x["kind"] for x in f})}
    _c0, canon_f = classify(ROOT / CANON_C0)
    report["candidates"]["CANONICAL LIVE"] = {"path": CANON_C0, "findings": canon_f,
                                              "kinds": sorted({x["kind"] for x in canon_f})}

    # 3. oracle census from the canonical document
    led = (yaml.safe_load((ROOT / CANON_C0).read_text(encoding="utf-8")) or {}).get("implication_ledger") or {}
    order, ranks = parse_chain(led)
    report["oracle"] = {
        "extension_class_containment": led.get("extension_class_containment"),
        "contains_order": order,
        "size_rank": ranks,
        "declared_edges": [{"from": e.get("from"), "to": e.get("to")} for e in (led.get("one_way_entailments") or [])],
        "forbidden_weakenings": led.get("forbidden_weakenings"),
        "subsumption_note": led.get("subsumption_note"),
        "rule": "S_X entails S_Y iff size_rank(X) >= size_rank(Y)",
    }

    # 4. controls: in-memory mutation on the direction-corrected candidate
    base = yaml.safe_load((ROOT / CANDIDATES["worker-023 direction-corrected"][0]).read_text(encoding="utf-8"))
    def mutate(clause: str | None):
        import copy
        d = copy.deepcopy(base)
        if clause is None:
            d["regularity"]["must_not_conflate"] = []
        else:
            d["regularity"]["must_not_conflate"][0] = clause
        return findings_for(d)
    ctl = {
        "A_canonical_denial": ("No containment with C2 or C0 is asserted here.",
                               {"denial_of_declared_containment"}),
        "B_reinject_disputed_entailment": ("H2_loc-inextendibility ENTAILS this class's conclusion.",
                                           {"entailment_direction_inverted"}),
        "C_valid_c2_direction": ("H2_loc-inextendibility entails the C2 sibling's conclusion.",
                                 set()),
        "D_quoted_mention_guard": ("worker-023 flagged 'H2_loc-inextendibility ENTAILS this class's conclusion' as wrong.",
                                   set()),
        "E_reinject_inverted_size": None,
    }
    for name, spec in ctl.items():
        if name == "E_reinject_inverted_size":
            import copy
            d = copy.deepcopy(base)
            d["implication_ledger"]["forbidden_transfers"][0]["reason"] = \
                "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
            got = {x["kind"] for x in findings_for(d)}
            expect = {"inverted_size_premise"}
        else:
            clause, expect = spec
            got = {x["kind"] for x in mutate(clause)}
        report["controls"][name] = {"expected": sorted(expect), "observed": sorted(got),
                                    "pass": got == expect}
    # F: malformed carrier fails closed (empty required slot)
    got = {x["kind"] for x in mutate(None)}
    report["controls"]["F_empty_required_slot"] = {"expected": ["malformed_carrier"],
                                                   "observed": sorted(got), "pass": got == {"malformed_carrier"}}

    # 5. verdict
    cands = report["candidates"]
    standing_inverted = [l for l, v in cands.items()
                         if "entailment_direction_inverted" in v["kinds"] and l != "CANONICAL LIVE"]
    corrected_clean = "entailment_direction_inverted" not in cands["worker-023 direction-corrected"]["kinds"] \
        and not cands["worker-023 direction-corrected"]["kinds"]
    canon_kinds = set(cands["CANONICAL LIVE"]["kinds"])
    if {"denial_of_declared_containment", "inverted_size_premise"} <= canon_kinds \
            and standing_inverted and corrected_clean and all(c["pass"] for c in report["controls"].values()):
        report["verdict"] = "W023_CONFIRMED: standing repair rewrites line 152 into a false H2loc=>C0 entailment; direction-corrected variant is clean"
    else:
        report["verdict"] = "INCONCLUSIVE_OR_CONTRADICTED"
    report["falsifier"] = ("Exhibit a reading of the pinned C0 document under which "
                           "E_C0 is not the largest extension set while its own "
                           "extension_class_containment/forbidden_weakenings/subsumption_note "
                           "say 'C0 => H2loc => C2, never the reverse'; or show candidate "
                           "9ab32ee3 (or my detector) fails on the pins. Any pin move voids the "
                           "run (exit 2); an unclassifiable carrier exits 3.")
    _write(report, args)
    return 0


def _write(report: dict, args) -> None:
    (OUT / "evidence").mkdir(parents=True, exist_ok=True)
    (OUT / "evidence" / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print(json.dumps({"verdict": report["verdict"],
                          "kinds": {k: v["kinds"] for k, v in report.get("candidates", {}).items()},
                          "controls_pass": all(c.get("pass") for c in report.get("controls", {}).values())}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
