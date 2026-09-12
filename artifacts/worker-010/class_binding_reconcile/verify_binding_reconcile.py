#!/usr/bin/env python3
"""Independent second implementation of the binding-relation classifier (W010-CBR-02).

Written from relation_fixtures.py's declared ground truth and the four class
contracts; it does not import binding_reconcile_audit.py.  It scores both the
fixture label set and (when given the report path) cross-checks the per-binding
relations recorded by the audit for agreement.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAMILY = {"AF-WCC-VAC-GEN": "WCC", "AF-WCC-SCALAR-SPH": "WCC",
          "AF-SCC-C2-VAC-GEN": "SCC", "AF-SCC-C0-VAC-GEN": "SCC"}

# ---------------------------------------------------------------- tokens ----
TOK = {
    "c0_ext": re.compile(r"\bC\s*\^?0[-\s]?extendib(?:le|ility)\b|\bcontinuous(?:ly)?\s+(?:metric\s+)?extension\b"
                         r"|\bmetric\s+extends\s+continuously\b|\bextends?\s+continuously\s+across\b"
                         r"|\bextended\s+across\s+(?:the\s+)?Cauchy\s+horizon\s+with\s+continuous\s+metric\b", re.I),
    "c2_ext": re.compile(r"\bC\s*\^?2[-\s]?extendib(?:le|ility)\b|\badmits?\s+(?:a|an)\s+C\s*\^?2\s+extension\b"
                         r"|\bextended?\s+as\s+a\s+C\s*\^?2\b", re.I),
    "inext": re.compile(r"\binextendib(?:le|ility)\b", re.I),
    "no_ext": re.compile(r"\bno\s+proper\s+(?:future\s+)?(?:C\s*\^?0|C\s*\^?2|continuous|H2)[-\s]?"
                         r"(?:metric\s+)?extension\b|\bcannot\s+be\s+(?:continuously\s+)?extended\b"
                         r"|\bno\s+continuous\s+extension\b", re.I),
    "horizon_local": re.compile(r"\bhorizon[-\s]localized\b|\bacross\s+(?:a|the)\s+(?:non-trivial\s+piece\s+of\s+)?"
                                r"(?:the\s+)?Cauchy\s+horizon\b", re.I),
    "naked": re.compile(r"\bnaked\s+singularit(?:y|ies)\b", re.I),
    "inc_ip": re.compile(r"\bincomplete\s+future\s+null\s+infinity\b|\bincomplete\s+I\+\b|\bI\+\s+(?:is\s+)?incomplete\b", re.I),
    "complete_ip": re.compile(r"\bcomplete\s+future\s+null\s+infinity\b|\bI\+\s+(?:is\s+)?complete\b", re.I),
    # stability only counts when it is stability OF the exterior/solution, not when the
    # word appears inside a status record ("the Kerr stability antecedent") or as
    # "instability" (word boundaries exclude the latter).
    "stability": re.compile(r"\bstability\s+of\s+(?:the\s+)?(?:Kerr\s+)?(?:exterior|solution|spacetime|development)\b"
                            r"|\bsettle\s+down\b|\bglobal\s+nonlinear\s+stability\b", re.I),
    "no_sing_visible": re.compile(r"\bno\s+singularity\s+is\s+visible\b|\bno\s+visible\s+singularit", re.I),
    "cc_holds": re.compile(r"\bcosmic\s+censorship\s+(?:holds|is\s+true)\b", re.I),
    "cc_fails": re.compile(r"\bcosmic\s+censorship\s+(?:fails|is\s+violated|is\s+false)\b"
                           r"|\bviolation\s+of\s+cosmic\s+censorship\b", re.I),
    # a naked singularity that is shown unstable is the support side, so the naked token
    # is suppressed inside an instability sentence (handled in classify()).
    "instability": re.compile(r"\binstabilit(?:y|ies)\b|\bunstable\b", re.I),
    "neg_cue": re.compile(r"\bdoes\s+not\s+(?:prove|prove|imply|settle|establish|give|demand|cover|address|decide)\b"
                          r"|\bno\s+peer-reviewed\s+(?:theorem|result|proof)\b|\bnot\s+located\b|\bnot\s+found\b"
                          r"|\bnot\s+proved\b|\bneither\s+proves?\b|\bnor\s+does\b", re.I),
}
SCC_CONTRARY = ("c0_ext", "c2_ext", "horizon_local")
SCC_SUPPORT = ("inext", "no_ext")
WCC_CONTRARY = ("naked", "inc_ip", "cc_fails")
WCC_SUPPORT = ("complete_ip", "stability", "no_sing_visible", "cc_holds")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;:!?])\s+|\n+", text) if s.strip()]


def hits(text: str, names) -> list[dict]:
    out = []
    for sent in sentences(text):
        for name in names:
            for m in TOK[name].finditer(sent):
                prefix = sent[: m.start()]
                out.append({"token": name, "text": m.group(0)[:80],
                            "negated": bool(TOK["neg_cue"].search(prefix)),
                            "sentence": sent.strip()[:200]})
    return out


def classify(text: str, cls: str) -> dict:
    if FAMILY[cls] == "SCC":
        con_t, sup_t = SCC_CONTRARY, SCC_SUPPORT
        if cls == "AF-SCC-C2-VAC-GEN":
            con_t = tuple(t for t in con_t if t != "c0_ext")  # C0-ext is weaker, not contrary here
        elif cls == "AF-SCC-C0-VAC-GEN":
            con_t = tuple(t for t in con_t if t != "c2_ext")  # C2-ext is stronger, not the contrary axis
    else:
        con_t, sup_t = WCC_CONTRARY, WCC_SUPPORT
    con, sup = [], []
    for h in hits(text, con_t):
        if h["token"] == "naked":
            # instability of a naked singularity is the support side, not a contrary hit
            sent = h["sentence"]
            if TOK["instability"].search(sent):
                continue
        (sup if h["negated"] else con).append(h)
    for h in hits(text, sup_t):
        (con if h["negated"] else sup).append(h)
    rel = "contrary" if con else ("support" if sup else "neutral")
    return {"relation": rel, "contrary_hits": con, "support_hits": sup}


def main() -> int:
    report_path = HERE / "binding_reconcile_audit.json"
    audit = json.loads(report_path.read_text())
    fixtures = [f for f in _load_fixtures()]
    rows, agree = [], 0
    for f in fixtures:
        got = classify(f["text"], f["class_id"])["relation"]
        ok = got == f["relation"]
        agree += ok
        rows.append({"id": f["id"], "class_id": f["class_id"], "expected": f["relation"],
                     "got": got, "pass": ok, "text": f["text"][:140]})
    # cross-check the audit's per-binding relations against this implementation
    xrows, xagree = [], 0
    for b in audit["bindings"]:
        text = _entry_text(b)
        got = classify(text, b["class_id"])["relation"]
        ok = got == b["direction"]
        xagree += ok
        xrows.append({"theorem_id": b["theorem_id"], "class_id": b["class_id"],
                      "audit_direction": b["direction"], "independent_direction": got,
                      "pass": ok})
    audit_contrary = {b["theorem_id"] + "|" + b["class_id"] for b in audit["bindings"]
                      if b["direction"] in ("contrary", "both")}
    indep_contrary = {r["theorem_id"] + "|" + r["class_id"] for r in xrows
                      if r["independent_direction"] in ("contrary", "both")}
    out = {
        "report_id": "W010-CBR-02",
        "purpose": "independent second implementation of the relation classifier; scored on the "
                   "labeled fixtures, then used as a sensitivity probe on the audit's bindings",
        "fixture_agreement": f"{agree}/{len(fixtures)}",
        "fixture_all_pass": agree == len(fixtures),
        "binding_cross_implementation_agreement": f"{xagree}/{len(xrows)}",
        "binding_audit_contrary_count": len(audit_contrary),
        "binding_independent_contrary_count": len(indep_contrary),
        "binding_contrary_union_count": len(audit_contrary | indep_contrary),
        "binding_contrary_intersection_count": len(audit_contrary & indep_contrary),
        "binding_disagreement_ids": sorted(
            {r["theorem_id"] + "|" + r["class_id"] for r in xrows if not r["pass"]}),
        "reading": ("the structural reconciliation (cell/entry counts, role grades, pin matches) is "
                    "implementation-independent; the direction/downgrade flags are lexical and the "
                    "two implementations bracket them, so only bindings flagged by both or corroborated "
                    "by the quoted sentence should be actioned"),
        "fixture_rows": rows,
        "binding_rows": xrows,
        "sha256_audit": hashlib.sha256(report_path.read_bytes()).hexdigest(),
    }
    json.dump(out, sys.stdout, indent=1)
    print()
    # exit 0 iff the declared fixture ground truth is fully reproduced (the probe itself
    # has no pass/fail: it exists to measure classifier sensitivity)
    return 0 if agree == len(fixtures) else 1


def _load_fixtures():
    """Load the labeled fixture set (data file, not code)."""
    data = json.loads((HERE / "relation_fixtures.json").read_text())
    return data["fixtures"]


def _entry_text(b: dict) -> str:
    """Reconstruct the entry text fields the audit used, from the frozen ledger."""
    led = HERE / "snapshots/theorems.a1674f094979.jsonl"
    for line in led.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e["theorem_id"] == b["theorem_id"]:
            parts = [str(e.get(k) or "") for k in
                     ("label", "statement_exact", "scope_caveats", "does_not_imply", "unresolved")]
            parts += [str(x) for x in (e.get("class_ids") or [])]
            return " \n ".join(parts)
    raise KeyError(b["theorem_id"])


if __name__ == "__main__":
    raise SystemExit(main())
