#!/usr/bin/env python3
"""W099-FORM-DIRECTION-CENSUS-01

Deterministic, stdlib-only, read-only census of class/variant *direction*
assertions across the frozen formulation corpus at the rev13 / rev29 pins.

Task origin (open, class-bound, on the G-FORM critical path): the formulation
lead's L-FORM-01 and L-FORM-03 blockers name *specific* surviving instances of
an inverted containment/strength direction:

  * schemas/af_scc_c0_vacuum.yaml  "C2 is a strictly larger extension class"
    (true containment: E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0, so C2
    is the INNERMOST / smallest extension class);
  * research_map/formulation_taxonomy.yaml:200  "The set-based reading ... is
    strictly stronger" (true direction: the single-q TAIL predicate entails the
    union/SET reading, so the union reading is strictly WEAKER);
  * artifacts/formulation/formulation_taxonomy.yaml D1  "F0 was stronger;
    (b) implies (c) but not conversely" (same inversion).

No complete cross-artifact enumeration of the *pattern family* existed.  This
instrument enumerates every candidate sentence in the pinned corpus that
positively asserts a size/strength relation between the frozen classes or the
WCC visibility readings, classifies it with explicit documented rules, and
carries a quote so a human reviewer can adjudicate each row.  Scanning uses a
3-line sliding window so YAML-wrapped sentences are seen whole; hits are
de-duplicated by (path, verdict, rule, window).

It is NOT a gate verdict, NOT a repair, and writes nothing outside its own
directory.  Exit 0 = pins stable + self-tests + corpus anchors pass; exit 3 =
pin drift or a control failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # .../ai4math-swarm

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "schemas/f1_falsifier_tests.jsonl":
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

# True corpus semantics, asserted by the pins above and by the containment
# chains in all three schemas:
#   (1) E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0
#       -> C2 is the smallest/innermost extension class; C0-inextendibility is
#          the STRONGEST conclusion, C2-inextendibility the WEAKEST.
#   (2) single-q TAIL predicate entails the union/SET reading
#       -> SET/union reading is strictly WEAKER (VARIANT_REGISTRY rev13; the
#          rev12 "strictly STRONGER" assertion was false).
CLASS_TOKEN = (r"(?:e_\{?)?(?:c2|c\^2|c\^\{2\}|c\^\{1,1\}|c1,1|h2_?loc|h\^2_?loc|c0|c\^0)\}?")
SMOOTHER = r"(?:c\^\{1,1\}|c1,1|h2_loc|h\^2_loc|c\^k|smooth|analytic)"
STRENGTH = (r"(?:strictly larger|strictly smaller|strictly stronger|strictly weaker|"
            r"larger extension class|smaller extension class|innermost|outermost|"
            r"subset of|superset of|stronger|weaker)")
LARGER_TOK = r"(?:strictly larger|larger extension class)"
STRONG_TOK = r"(?:strictly stronger|strictly weaker)"
SUBJ = r"[a-z0-9_^{},\.\s:;\-]{0,70}?"

RE_LARGER = re.compile(r"(?P<subj>" + SUBJ + r")(?P<tok>" + LARGER_TOK + r")", re.I)
RE_LARGER_FWD = re.compile(r"(?P<tok>" + LARGER_TOK + r")(?P<subj>" + SUBJ + r")", re.I)
RE_STRONG = re.compile(r"(?P<subj>" + SUBJ + r")(?P<tok>" + STRONG_TOK + r")", re.I)
RE_STRONG_FWD = re.compile(r"(?P<tok>" + STRONG_TOK + r")(?P<subj>" + SUBJ + r")", re.I)

META_MARKERS = re.compile(
    r"(was false|were false|is false|wrongly|was wrong|mislabell|downgrad|"
    r"corrected|corrects|no longer|superseded|had the ordering wrong|"
    r"earlier revision|previous revision|prior revision|"
    r"rev1[0-9] '[^']{0,40}' assertion)", re.I)

C2_RX = re.compile(r"(c2|c\^2|c\^\{2\})", re.I)
C0_RX = re.compile(r"(c0|c\^0)", re.I)
CONCLUSION_RX = re.compile(r"(conclusion|inextendib|this class|statement)", re.I)
VARIANT_CTX_RX = re.compile(r"(distributional|variant|subset of extensions|fewer allowed)")


def meta_near(text: str, span, radius: int = 80):
    """True iff a retraction marker sits within +/-radius chars of span."""
    a, b = max(0, span[0] - radius), min(len(text), span[1] + radius)
    return META_MARKERS.search(text[a:b])


def classify(text: str):
    """Return (verdict, rule, reason) for one collapsed candidate window.

    Verdicts: INVERTED | CORRECT | META_RETRACTED | MANUAL_REVIEW | NONE
    """
    t = re.sub(r"\s+", " ", text)
    low = t.lower()

    # ---- P2: WCC visibility readings (SET/union vs single-q tail) ----------
    p2 = ("set-based" in low or "set based" in low or "union reading" in low
          or "union of j" in low or "single-q" in low or "single q" in low
          or "tail predicate" in low or "f0 was stronger" in low)
    if p2:
        m_set = re.search(r"(set-based|set based|union reading|union of j)[^.;]{0,90}"
                          r"(strictly stronger|is stronger|is strictly stronger)", low)
        if m_set:
            if meta_near(t, m_set.span()):
                return ("META_RETRACTED", "P2-META",
                        "SET-stronger phrase appears inside a retraction/correction context")
            return ("INVERTED", "P2-SET-STRONGER",
                    "positive assertion that the union/SET reading is stronger; the single-q "
                    "tail predicate entails it (variant registry rev13)")
        if re.search(r"(set-based|set based|union reading|union of j)[^.;]{0,90}"
                     r"(strictly weaker|is weaker|is strictly weaker)", low):
            return ("CORRECT", "P2-SET-WEAKER",
                    "union/SET reading asserted strictly weaker, matching the rev13 direction")
        if re.search(r"(single-q|single q|tail predicate)[^.;]{0,90}"
                     r"(entails|implies)[^.;]{0,90}(union|set-based|set based)", low):
            return ("CORRECT", "P2-TAIL-ENTAILS-UNION",
                    "single-q tail predicate asserted to entail the union reading (rev13 direction)")
        if "f0 was stronger" in low or "f0 was strictly stronger" in low:
            return ("INVERTED", "P2-F0-STRONGER",
                    "D1 divergence ledger: F0/SET reading called stronger while (b) is said to "
                    "imply (c); the single-q reading entails the union reading")
        if "implies (c) but not conversely" in low or "implies c but not conversely" in low:
            return ("INVERTED", "P2-IMPLIES-DIRECTION",
                    "D1 states (b) implies (c) but not conversely, i.e. the inverted entailment")

    # ---- P1: extension-class containment size / statement strength --------
    # 1. explicit containment-chain enumeration matching the frozen chain
    if len(set(re.findall(CLASS_TOKEN, low))) >= 3 and "subset" in low:
        return ("CORRECT", "P1-CHAIN-ENUMERATION",
                "explicit containment chain enumerated over >=3 class tokens (matches the "
                "frozen E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 ordering)")

    # 2. a smoother class (or anaphoric "those") called strictly larger is correct
    for m in RE_LARGER.finditer(low):
        if re.search(SMOOTHER, m.group("subj")):
            return ("CORRECT", "P1-SMOOTHER-LARGER",
                    "C^{1,1}/H2_loc/smoother class called strictly larger, matching "
                    "E_C2 subset E_{C^1,1} subset E_H2loc")
    if (re.search(SMOOTHER, low) and re.search(LARGER_TOK, low)
            and not re.search(r"(c2|c\^2)[^.;]{0,40}" + LARGER_TOK, low)):
        return ("CORRECT", "P1-SMOOTHER-LARGER-ANAPHORIC",
                "larger-class phrase in a sentence whose subject is a smoother class")

    # 3. C2 itself called larger -> inverted (unless in a retraction context)
    for m in list(RE_LARGER.finditer(low)) + list(RE_LARGER_FWD.finditer(low)):
        if C2_RX.search(m.group("subj")):
            if meta_near(t, m.span()):
                return ("META_RETRACTED", "P1-META",
                        "direction phrase appears inside a retraction/correction context")
            return ("INVERTED", "P1-C2-LARGER",
                    "C2 called a strictly larger/larger extension class; C2 is the innermost "
                    "and smallest extension class")

    # 4. statement-strength attributions
    pairs = list(RE_STRONG.finditer(low)) + list(RE_STRONG_FWD.finditer(low))
    for m in pairs:
        subj, tok = m.group("subj"), m.group("tok")
        around = subj + " " + low[max(0, m.end() - 1): m.end() + 70]
        if C0_RX.search(subj) and "strong" in tok and CONCLUSION_RX.search(around):
            return ("CORRECT", "P1-C0-STRONGER",
                    "C0 conclusion called strictly stronger, matching the containment chain")
        if C0_RX.search(subj) and "weak" in tok:
            if meta_near(t, m.span()):
                return ("META_RETRACTED", "P1-META",
                        "C0-weaker phrase inside a retraction/correction context")
            if VARIANT_CTX_RX.search(subj) or VARIANT_CTX_RX.search(around):
                return ("MANUAL_REVIEW", "P1-C0-VARIANT-WEAKER",
                        "C0 appears as a variant/restricted-extension qualifier, not as the "
                        "class conclusion; direction must be read in context")
            if CONCLUSION_RX.search(around):
                return ("INVERTED", "P1-C0-WEAKER",
                        "C0 conclusion called strictly weaker; C0-inextendibility is the "
                        "strongest of the three SCC conclusions")
            return ("MANUAL_REVIEW", "P1-C0-WEAKER-UNBOUND",
                    "C0 carries a weaker token without a bound conclusion phrase")
        if re.search(SMOOTHER, subj) and "strong" in tok:
            return ("CORRECT", "P1-SMOOTHER-STRONGER",
                    "smoother/higher-regularity class called strictly stronger, matching the "
                    "containment chain")
        if C2_RX.search(subj):
            return ("MANUAL_REVIEW", "P1-C2-STRENGTH-UNBOUND",
                    "C2 carries a strength token without an explicit larger/stronger direction; "
                    "needs human reading of the surrounding clause")

    # 4b. meta-only direction phrase (no class token in the window), e.g. a
    #     changelog line retracting the rev12 "strictly STRONGER" assertion
    m_str = re.search(STRENGTH, low)
    if m_str and meta_near(t, m_str.span(), radius=95):
        return ("META_RETRACTED", "P-META-ONLY",
                "direction phrase explicitly retracted/corrected near the token")

    # 5. containment-chain vocabulary with no bound direction -> reviewer row
    if re.search(CLASS_TOKEN, low) and re.search(STRENGTH, low):
        return ("MANUAL_REVIEW", "UNBOUND-CANDIDATE",
                "class token and strength token co-occur but no documented rule binds a subject")
    return ("NONE", "NOT-A-CANDIDATE", "no direction assertion")


def candidate(text: str) -> bool:
    low = re.sub(r"\s+", " ", text).lower()
    if re.search(CLASS_TOKEN, low) and re.search(STRENGTH, low):
        return True
    if ("set-based" in low or "union" in low or "single-q" in low
            or "tail predicate" in low or "f0 was stronger" in low) and re.search(
                STRENGTH + r"|entails|implies", low):
        return True
    if re.search(STRENGTH, low) and META_MARKERS.search(low):
        return True
    return False


# ---------------------------------------------------------------- self-tests

FIXTURES = [
    ("C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker",
     "INVERTED"),
    ("It does NOT forbid C^{1,1} or H^2_loc extensions: those are strictly larger classes",
     "CORRECT"),
    ("meaning_C0: forbidden extensions are C0 extensions; strictly stronger than the C2 conclusion",
     "CORRECT"),
    ("The set-based reading is strictly stronger; it is registered as variant SET",
     "INVERTED"),
    ("the parent's single-q tail predicate entails the union reading; strictly weaker than AF-WCC-VAC-GEN",
     "CORRECT"),
    ("the rev12 'strictly STRONGER' assertion was false [rev13: strict-order direction corrected]",
     "META_RETRACTED"),
    ("Containment of extension sets runs E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
     "CORRECT"),
    ("The extension metric is C2 across the boundary and Ric = 0 holds at sample points",
     "NONE"),
    ("a distributional-vacuum C0 extension is a strictly weaker statement (fewer allowed extensions)",
     "MANUAL_REVIEW"),
]

# (path, line, expectation).  NOT_INVERTED means: not flagged as a live inversion.
ANCHORS = [
    ("schemas/af_scc_c0_vacuum.yaml", 246, "INVERTED"),
    ("research_map/formulation_taxonomy.yaml", 200, "INVERTED"),
    ("artifacts/formulation/formulation_taxonomy.yaml", 176, "INVERTED"),
    ("research_map/formulation_taxonomy.yaml", 140, "NOT_INVERTED"),
    ("schemas/af_scc_c2_vacuum.yaml", 148, "NOT_INVERTED"),
    ("schemas/af_scc_c2_vacuum.yaml", 237, "NOT_INVERTED"),
    ("schemas/af_wcc_vacuum.yaml", 73, "NOT_INVERTED"),
    ("artifacts/formulation/VARIANT_REGISTRY.json", 57, "NOT_INVERTED"),
]

ANCHOR_PASS = {"NOT_INVERTED": {"CORRECT", "META_RETRACTED", "MANUAL_REVIEW"}}


def pick_line(chunk, base):
    """Line of the decisive direction token inside a 3-line window (1-based)."""
    pat = re.compile(r"strictly|larger|stronger|weaker|subset|innermost|outermost", re.I)
    for off in range(len(chunk) - 1, -1, -1):
        if pat.search(chunk[off]):
            return base + off + 1
    return base + 1


def scan_lines(rel, lines, sha, pin_status="frozen_pin"):
    """Candidate detection + classification over a 3-line sliding window."""
    out = []
    for i in range(len(lines)):
        chunk = lines[max(0, i - 1): i + 2]
        window = re.sub(r"\s+", " ", " ".join(chunk)).strip()
        if not window or not candidate(window):
            continue
        verdict, rule, reason = classify(window)
        if verdict == "NONE":
            continue
        out.append({
            "path": rel, "line": pick_line(chunk, max(0, i - 1)),
            "window": [max(1, i), min(len(lines), i + 2)],
            "verdict": verdict, "rule": rule, "reason": reason,
            "quote": window if len(window) <= 420 else window[:420] + " ...",
            "sha256": sha, "pin_status": pin_status,
        })
    return out


EXTRA_ROOTS = ("artifacts/formulation", "schemas")
EXT_EXT = (".json", ".jsonl", ".yaml", ".yml", ".md", ".txt")


def iter_extra():
    files = []
    for root in EXTRA_ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, root)):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for fn in sorted(filenames):
                if fn.endswith(EXT_EXT):
                    rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                    if rel not in PINS:
                        files.append(rel)
    return files


def dedupe(raw):
    hits, by_key = [], {}
    for h in raw:
        key = (h["path"], h["line"], h["verdict"], h["rule"])
        if key in by_key:
            prev = by_key[key]
            if len(h["quote"]) < len(prev["quote"]):
                by_key[key] = h
                hits[hits.index(prev)] = h
            continue
        by_key[key] = h
        hits.append(h)
    return hits


FIXTURE_MARKERS = ("/fixtures/", "novel_mutants", "rebased_fixtures",
                   "heldout_rebased", "/mutants/", "semantic_contract_tests")


def context_class(rel: str) -> str:
    """Separate live assertions from fixtures/snapshots/reports that quote them."""
    if any(m in rel for m in FIXTURE_MARKERS):
        return "fixture_or_mutant"
    if rel.startswith("artifacts/formulation/schemas/"):
        return "pinned_snapshot"
    if "/evidence/" in rel or "/reviews/" in rel or rel.endswith(".md"):
        return "report_or_review"
    return "live_tree"


def main() -> int:
    measured, drift = {}, []
    for rel, want in PINS.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            drift.append({"path": rel, "error": "missing"})
            measured[rel] = None
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        got = h.hexdigest()
        measured[rel] = got
        if got != want:
            drift.append({"path": rel, "expected": want, "measured": got})

    raw = []
    for rel in PINS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln.rstrip("\n") for ln in f]
        raw.extend(scan_lines(rel, lines, measured[rel], "frozen_pin"))
    hits = dedupe(raw)
    hits.sort(key=lambda h: (h["path"], h["line"], h["rule"]))

    # ---- extended sweep: whole artifacts/formulation + schemas text tree ----
    extra_raw, extra_files, extra_unreadable = [], [], []
    for rel in iter_extra():
        p = os.path.join(ROOT, rel)
        try:
            data = open(p, "rb").read()
        except OSError as exc:
            extra_unreadable.append({"path": rel, "error": str(exc)})
            continue
        sha = hashlib.sha256(data).hexdigest()
        lines = data.decode("utf-8", errors="replace").splitlines()
        extra_files.append({"path": rel, "sha256": sha, "bytes": len(data)})
        extra_raw.extend(scan_lines(rel, lines, sha, "measured_not_pinned"))
    extra_hits = dedupe(extra_raw)
    for h in extra_hits:
        h["context_class"] = context_class(h["path"])
    extra_hits.sort(key=lambda h: (h["context_class"], h["path"], h["line"], h["rule"]))
    extra_counts, ctx_counts, ctx_inverted = {}, {}, {}
    for h in extra_hits:
        extra_counts[h["verdict"]] = extra_counts.get(h["verdict"], 0) + 1
        c = h["context_class"]
        ctx_counts.setdefault(c, {})
        ctx_counts[c][h["verdict"]] = ctx_counts[c].get(h["verdict"], 0) + 1
        if h["verdict"] == "INVERTED":
            ctx_inverted.setdefault(c, []).append(h)
    extra_inverted = [h for h in extra_hits if h["verdict"] == "INVERTED"]
    live_extra_inverted = ctx_inverted.get("live_tree", [])

    selftest, ok = [], True
    for text, want in FIXTURES:
        got, rule, _ = classify(text)
        good = got == want
        ok = ok and good
        selftest.append({"fixture": text, "expected": want, "got": got, "rule": rule, "pass": good})

    anchors, by_key = [], {}
    for h in hits:
        by_key.setdefault((h["path"], h["line"]), []).append(h["verdict"])
    for path, line, want in ANCHORS:
        got = by_key.get((path, line), [])
        good = (("INVERTED" in got) if want == "INVERTED"
                else any(v in ANCHOR_PASS["NOT_INVERTED"] for v in got))
        ok = ok and good
        anchors.append({"path": path, "line": line, "expected": want, "got": got, "pass": good})

    counts = {}
    for h in hits:
        counts[h["verdict"]] = counts.get(h["verdict"], 0) + 1
    inverted = [h for h in hits if h["verdict"] == "INVERTED"]

    report = {
        "task_id": "W099-FORM-DIRECTION-CENSUS-01",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "instrument": "artifacts/worker-099/form_direction_census/run_direction_census.py",
        "read_only": True,
        "pins": measured,
        "pin_drift": drift,
        "true_direction": {
            "extension_containment": "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
            "c2_role": "innermost / smallest extension class; C2-inextendibility weakest",
            "wcc_readings": "single-q TAIL predicate entails the union/SET reading; SET reading strictly weaker (rev13)",
        },
        "counts": counts,
        "inverted_findings": inverted,
        "hits": hits,
        "extended_scan": {
            "roots": list(EXTRA_ROOTS),
            "extensions": list(EXT_EXT),
            "files_scanned": len(extra_files),
            "files": extra_files,
            "unreadable": extra_unreadable,
            "counts": extra_counts,
            "counts_by_context": ctx_counts,
            "inverted_by_context": ctx_inverted,
            "live_tree_inverted": live_extra_inverted,
            "note": ("files are hash-measured at scan time, not frozen pins; fixture/mutant, "
                     "pinned-snapshot and report/review rows quote the pattern deliberately or "
                     "describe it; only live_tree rows are live-assertion candidates"),
        },
        "self_test": {"pass": ok and not drift, "fixtures": selftest, "corpus_anchors": anchors},
        "limitations": [
            "Lexical subject binding over prose; every hit carries a quote for human adjudication.",
            "MANUAL_REVIEW rows are candidates, not findings.",
            "Does not adjudicate L-FORM-04 (falsifier-corpus binding staleness); separate question.",
            "3-line window can merge adjacent YAML entries; quotes are the adjudication surface.",
            "Extended sweep files are not frozen pins; only the 8 anchor pins are gate-relevant.",
            "Not a gate verdict, not a repair, no canonical file written.",
        ],
    }

    out_json = os.path.join(HERE, "census.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=False)
        f.write("\n")
    out_jsonl = os.path.join(HERE, "extended_hits.jsonl")
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for h in extra_hits:
            f.write(json.dumps(h, sort_keys=True) + "\n")

    print(json.dumps({
        "hits": len(hits), "counts": counts,
        "inverted": [(h["path"], h["line"], h["rule"]) for h in inverted],
        "extended_files": len(extra_files), "extended_counts": extra_counts,
        "extended_by_context": ctx_counts,
        "live_tree_inverted": [(h["path"], h["line"], h["rule"]) for h in live_extra_inverted],
        "pin_drift": len(drift), "selftest_pass": ok, "out": out_json,
    }, indent=2))
    return 0 if (ok and not drift) else 3


if __name__ == "__main__":
    sys.exit(main())
