#!/usr/bin/env python3
"""W002-F2B-REV14-LANDING-PREDICATE-01

Deterministic, read-only, no-network predicate for the F2b portion of the REC-36
authorized repair (astra-lifecycle-08 decisions; class AF-SCC-C0-VAC-GEN, sibling
AF-SCC-C2-VAC-GEN, node F2b, gate G-FORM).

WHAT IT DECIDES
  D1   no assertive containment-denial carrier in regularity.must_not_conflate[*]
  D1b  the nesting chain E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 is asserted
       in implication_ledger.extension_class_containment, in the correct direction
  D2   no inverted extension-set size premise in the C2->C0 forbidden-transfer reason,
       with the conclusion polarity (C2-inextendibility strictly weaker) preserved
  M1..M5  landing mechanics: mirror byte-identity, revision bump, FROZEN re-emit with
       all pins resolving, delta confinement vs the pinned rev13 snapshot, rollback copy
  M6   informational census of review files that bind the rev13 F2b hash

WHAT IT DOES NOT DECIDE
  mathematics, physical correctness, citation scope, or any gate verdict. A
  PASS_CANDIDATE_REV14 is an input to astra-life05-verify-gform-r3, nothing more.

USAGE
  python3 verify_rev14_landing.py --live       # -> report.json
  python3 verify_rev14_landing.py --controls   # -> controls.json
  python3 verify_rev14_landing.py --all

No canonical byte is written. All mutants live under ./sandbox/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm
CST = timezone(timedelta(hours=8))

REV13_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
REV13_F2A = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml": REV13_F2B,
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": REV13_F2B,
    "schemas/af_scc_c2_vacuum.yaml": REV13_F2A,
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}
CANON_F2B = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_F2B = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
REV13_SNAPSHOT = "artifacts/worker-002/f2b_containment_adjudication/pinned/schemas__af_scc_c0_vacuum.yaml"
CANDIDATE = "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml"
CANDIDATE_SHA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

# ---------------------------------------------------------------- strict yaml

def strict_load(text: str):
    """Parse YAML, rejecting duplicate mapping keys at any depth."""
    def scan(node, path="$"):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k_node, v_node in node.value:
                try:
                    key = k_node.value
                except AttributeError:  # pragma: no cover
                    key = repr(k_node)
                if key in seen:
                    raise ValueError(f"duplicate key {key!r} at {path}")
                seen[key] = True
                scan(v_node, f"{path}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, item in enumerate(node.value):
                scan(item, f"{path}[{i}]")
    node = yaml.compose(text)
    if node is not None:
        scan(node)
    return yaml.safe_load(text)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    digest = sha256_file(p)
    return {
        "path": rel,
        "exists": p.is_file(),
        "bytes": p.stat().st_size if p.is_file() else 0,
        "sha256": digest,
        "expected": PINS.get(rel),
        "match": digest == PINS.get(rel) if rel in PINS else None,
    }


# ---------------------------------------------------------------- semantics

DENY_PATTERNS = [
    r"\bno\s+containment\b",
    r"\bno\s+nesting\b",
    r"\bdoes\s+not\s+(?:assert|claim|imply|establish|entail)\b[^.]{0,60}\b(?:containment|nesting)\b",
    r"\bnothing\s+here\s+asserts\b[^.]{0,60}\bcontainment\b",
    r"\bno\s+containment\s+(?:is|was)\s+(?:asserted|claimed|established)\b",
    r"\bnot\s+(?:asserted|claimed)\s+(?:here|in\s+this\s+(?:class|document|artifact))\b",
]
HISTORICAL_MARKERS = re.compile(
    r"\b(earlier|previous|prior\s+revision|was\s+wrong|were\s+wrong|is\s+wrong|corrected|"
    r"superseded|retract(?:ed)?|no\s+longer\s+asserted)\b",
    re.I,
)


def _bracket_spans(text: str) -> list[tuple[int, int]]:
    spans, start = [], None
    for i, ch in enumerate(text):
        if ch == "[" and start is None:
            start = i
        elif ch == "]" and start is not None:
            spans.append((start, i + 1))
            start = None
    return spans


def _sentences(text: str) -> list[tuple[int, int, str]]:
    out, start = [], 0
    for m in re.finditer(r"(?<=[.;])\s+|\n", text):
        end = m.start()
        if end > start:
            out.append((start, end, text[start:end]))
        start = m.end()
    if start < len(text):
        out.append((start, len(text), text[start:]))
    return out


def live_denials(item_text: str) -> list[dict]:
    """Deny-assertions in one must_not_conflate item that are not marked historical."""
    spans = _bracket_spans(item_text)
    hits = []
    for s0, s1, sentence in _sentences(item_text):
        for pat in DENY_PATTERNS:
            for m in re.finditer(pat, sentence, re.I):
                g0, g1 = s0 + m.start(), s0 + m.end()
                in_bracket = any(b0 <= g0 < b1 for b0, b1 in spans)
                if in_bracket:
                    continue
                context = item_text[max(0, s0 - 120):s1]
                if HISTORICAL_MARKERS.search(context):
                    continue
                hits.append({"pattern": pat, "quote": sentence.strip()[:240]})
                break
    return hits


def _norm_chain(text: str) -> str:
    t = text.replace("⊂", " subsetof ").replace("⊆", " subsetof ")
    t = re.sub(r"contained\s+in", " subsetof ", t, flags=re.I)
    t = re.sub(r"subset\s+of", " subsetof ", t, flags=re.I)
    t = re.sub(r"[^A-Za-z0-9;]", "", t)
    return t.lower()


def chain_status(text: str) -> dict:
    """Adjacent-pair nesting check on implication_ledger.extension_class_containment."""
    n = _norm_chain(text or "")
    pairs = [("ec0", "eh2loc"), ("eh2loc", "ec11"), ("ec11", "ec2")]  # (big, small)
    forward, reversed_ = [], []
    for big, small in pairs:
        fwd = (f"{big}contains{small}" in n) or (f"{small}subsetof{big}" in n)
        rev = (f"{small}contains{big}" in n) or (f"{big}subsetof{small}" in n)
        (forward if fwd else reversed_).append(f"{small} in {big}" if fwd else f"{small} !in {big}")
        if rev and not fwd:
            reversed_.append(f"REVERSED:{big} in {small}")
    return {
        "ok": len(forward) == 3 and not reversed_,
        "forward_pairs": forward,
        "violations": reversed_,
        "normalized": n[:400],
    }


SIZE_INVERSION = [
    r"c2\b[^.]{0,70}\b(?:strictly\s+)?(?:larger|bigger|wider|broader|more\s+general|largest|widest)\b[^.]{0,30}\bextension",
    r"c2\b[^.]{0,70}\bsuperset\b",
]
POSITIVE_PREMISE = [
    r"smaller\s+extension",
    r"strictly\s+weaker",
    r"subsetof",
]


def inverted_premise(reason: str) -> dict:
    raw = re.sub(r"\s+", " ", (reason or "").lower())
    norm = _norm_chain(reason or "")
    inv = [p for p in SIZE_INVERSION if re.search(p, raw)]
    if "ec0subsetofec2" in norm:
        inv.append("normalized reversed containment E_C0 subset E_C2")
    pos = [p for p in POSITIVE_PREMISE if (re.search(p, raw) or (p == "subsetof" and "ec2subsetofec0" in norm))]
    return {"ok": not inv and bool(pos), "inversions": inv, "positive_markers": pos}


def semantics(text: str, doc: dict) -> dict:
    reg = (doc or {}).get("regularity") or {}
    mnc = reg.get("must_not_conflate")
    ledger = (doc or {}).get("implication_ledger") or {}
    findings = []

    if not isinstance(mnc, list) or not mnc:
        d1 = {"ok": False, "reason": "regularity.must_not_conflate absent or empty", "live_denials": []}
    else:
        hits = []
        for i, item in enumerate(mnc):
            for h in live_denials(str(item)):
                h["index"] = i
                hits.append(h)
        d1 = {"ok": not hits, "live_denials": hits, "items": len(mnc)}

    chain = chain_status(ledger.get("extension_class_containment") if isinstance(ledger, dict) else None)

    d2 = {"ok": False, "reason": "no C2->this-class forbidden transfer found", "carrier": None}
    fts = ledger.get("forbidden_transfers") if isinstance(ledger, dict) else None
    if isinstance(fts, list):
        for t in fts:
            if not isinstance(t, dict):
                continue
            if str(t.get("from", "")).strip() == "no proper future C2 extension" and str(t.get("to", "")).strip() == "this class":
                d2 = inverted_premise(str(t.get("reason", "")))
                d2["carrier"] = {"from": t.get("from"), "to": t.get("to"), "reason": t.get("reason")}
                break

    if not d1["ok"]:
        findings.append({"id": "D1", "severity": "hard",
                         "detail": "assertive containment-denial carrier in regularity.must_not_conflate",
                         "hits": d1["live_denials"]})
    if not chain["ok"]:
        findings.append({"id": "D1b", "severity": "hard",
                         "detail": "nesting chain missing or reversed in implication_ledger.extension_class_containment",
                         "violations": chain["violations"]})
    if not d2["ok"]:
        findings.append({"id": "D2", "severity": "hard",
                         "detail": "C2->C0 forbidden-transfer premise inverted or conclusion polarity lost",
                         "inversions": d2.get("inversions"), "positive_markers": d2.get("positive_markers")})
    return {"D1": d1, "D1b": chain, "D2": d2, "hard_findings": findings, "clean": not findings}


# ---------------------------------------------------------------- mechanics

ALLOWED_EXACT = {"revision", "written_at", "created_at", "revised_at"}
ALLOWED_PREFIX = ("f0_binding", "revision")
ALLOWED_INDEXED = {"regularity.must_not_conflate[0]",
                   "implication_ledger.forbidden_transfers[0].reason"}


def leaf_diff(a, b, path="$") -> list[str]:
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}"
            if k not in a or k not in b:
                out.append(p)
            else:
                out.extend(leaf_diff(a[k], b[k], p))
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = f"{path}[{i}]"
            if i >= len(a) or i >= len(b):
                out.append(p)
            else:
                out.extend(leaf_diff(a[i], b[i], p))
    elif a != b:
        out.append(path)
    return out


def allowed_leaf(p: str) -> bool:
    key = p.lstrip("$.")
    if key in ALLOWED_EXACT or key in ALLOWED_INDEXED:
        return True
    return key.split(".")[0].split("[")[0].startswith(ALLOWED_PREFIX)


def rollback_paths() -> list[str]:
    found = []
    for p in sorted(ROOT.glob("artifacts/**/*rollback*")):
        if "worker-002" in str(p):
            continue
        rel = str(p.relative_to(ROOT))
        if len(rel) < 200 and (p.is_file() or p.is_dir()):
            found.append(rel)
    return found[:20]


def verdict_bound_reviews(f2b_hash: str) -> dict:
    hits = []
    reviews = ROOT / "reviews"
    if reviews.is_dir():
        for p in sorted(reviews.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            stack = [data]
            while stack:
                cur = stack.pop()
                if isinstance(cur, dict):
                    for k, v in cur.items():
                        if isinstance(v, str) and f2b_hash[:12] in v and ("sha256" in k or "hash" in k or "pin" in k):
                            hits.append(str(p.relative_to(ROOT)))
                            stack = []
                            break
                        stack.append(v)
                elif isinstance(cur, list):
                    stack.extend(cur)
            if hits and hits[-1] == str(p.relative_to(ROOT)):
                continue
    return {"count": len(set(hits)), "files": sorted(set(hits))[:40]}


def mechanics(f2b_doc: dict, f2b_text: str) -> dict:
    canon = measure(CANON_F2B)
    mirror = measure(MIRROR_F2B)
    m1 = {"id": "M1", "state": "pass" if (canon["sha256"] and canon["sha256"] == mirror["sha256"]) else "fail",
          "detail": {"canonical": canon["sha256"], "mirror": mirror["sha256"]}}

    rev = f2b_doc.get("revision")
    m2 = {"id": "M2", "state": "pass" if isinstance(rev, int) and rev >= 14 else ("pending" if isinstance(rev, int) else "fail"),
          "detail": {"revision": rev, "required_min": 14}}

    frozen = json.loads((ROOT / FROZEN).read_text())
    frev = frozen.get("revision")
    pins = frozen.get("files") or {}
    unresolved = []
    for rel, meta in pins.items():
        want = (meta or {}).get("sha256") if isinstance(meta, dict) else None
        got = sha256_file(ROOT / rel)
        if want != got:
            unresolved.append({"path": rel, "declared": want, "measured": got})
    if not isinstance(frev, int) or frev < 30:
        m3 = {"id": "M3", "state": "pending", "detail": {"frozen_revision": frev, "required_min": 30,
                                                          "pins": len(pins),
                                                          "unresolved": unresolved[:12],
                                                          "unresolved_count": len(unresolved)}}
    else:
        m3 = {"id": "M3", "state": "pass" if not unresolved else "fail",
              "detail": {"frozen_revision": frev, "pins": len(pins), "unresolved": unresolved[:12],
                         "unresolved_count": len(unresolved)}}

    if REV13_SNAPSHOT and (ROOT / REV13_SNAPSHOT).is_file():
        snap = strict_load((ROOT / REV13_SNAPSHOT).read_text())
        changed = leaf_diff(snap, f2b_doc)
    else:
        changed = []
    out_of_scope = [c for c in changed if not allowed_leaf(c)]
    m4 = {"id": "M4", "state": "pass" if not out_of_scope else "fail",
          "detail": {"changed_leaves": changed, "out_of_scope": out_of_scope}}

    rb = rollback_paths()
    if isinstance(rev, int) and rev < 14:
        m5 = {"id": "M5", "state": "pending", "detail": {"rollback_candidates": rb}}
    else:
        m5 = {"id": "M5", "state": "pass" if rb else "fail", "detail": {"rollback_candidates": rb}}

    m6 = {"id": "M6", "state": "info", "detail": verdict_bound_reviews(REV13_F2B)}

    gate_run = subprocess.run(
        [sys.executable, str(ROOT / GATE), str(ROOT / CANON_F2B)],
        capture_output=True, text=True, timeout=120,
    )
    m7 = {"id": "M7", "state": "info",
          "detail": {"exit_code": gate_run.returncode,
                     "stdout_tail": gate_run.stdout.strip()[-300:],
                     "stderr_tail": gate_run.stderr.strip()[-300:]}}

    checks = [m1, m2, m3, m4, m5, m6, m7]
    blocking = [c for c in checks if c["id"] in {"M1", "M2", "M3", "M4", "M5"} and c["state"] == "fail"]
    pending = [c["id"] for c in checks if c["state"] == "pending"]
    return {"checks": checks, "blocking_failures": [c["id"] for c in blocking], "pending": pending}


def decide(sem: dict, mech: dict, revision) -> str:
    sem_clean = sem["clean"]
    if isinstance(revision, int) and revision >= 14:
        if not sem_clean:
            return "FAIL_REV14_STILL_DEFECTIVE"
        if mech["blocking_failures"]:
            return "FAIL_MECHANICS"
        return "PASS_CANDIDATE_REV14"
    if not sem_clean:
        return "FAIL_REC36_OPEN"
    return "FAIL_UNSANCTIONED_BYTE_MOVE"


# ---------------------------------------------------------------- subjects

def load_subject(rel_or_path: str) -> tuple[str, dict, str]:
    p = Path(rel_or_path)
    if not p.is_absolute():
        p = ROOT / p
    text = p.read_text()
    return str(p), strict_load(text), text


def mutate_text(text: str, old: str, new: str, tag: str) -> tuple[str, dict]:
    n = text.count(old)
    if n != 1:
        raise ValueError(f"mutant {tag}: target occurs {n} times, expected 1")
    return text.replace(old, new), {"mode": "text", "tag": tag, "old": old, "new": new}


def mutate_parsed(doc: dict, fn, tag: str) -> tuple[str, dict]:
    import copy
    d = copy.deepcopy(doc)
    fn(d)
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True), {"mode": "parsed", "tag": tag}


LIVE_DENIAL = "No containment with C2 or C0 is asserted here"
CAND_REASON = "C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker"
LIVE_REASON = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
CHAIN_SENT = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"


def build_controls() -> dict:
    live_text = (ROOT / CANON_F2B).read_text()
    cand_text = (ROOT / CANDIDATE).read_text()
    live_doc = strict_load(live_text)
    cand_doc = strict_load(cand_text)

    def c03(d):
        d["regularity"]["must_not_conflate"][0] = (
            "H2_loc is a distinct regularity-axis value phrased in terms of curvature, not metric "
            "differentiability. Nothing here asserts any containment between the C2 and C0 extension "
            "classes. [R2 major: the earlier revision listed H2_loc as forbidden and as incomparable]"
        )
    def c04(d):
        d["regularity"]["must_not_conflate"][0] = (
            "H2_loc is a distinct regularity-axis value phrased in terms of curvature, not metric "
            "differentiability. [The earlier wording 'no containment with C2 or C0 is asserted here' "
            "was wrong; the extension sets are nested E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0.]"
        )
    def c05(d):
        d["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
            "C2 is the widest of the extension classes, so C2-inextendibility is strictly weaker"
        )
    def c06(d):
        d["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
            "Because E_C2 is a subset of E_C0, a C2-inextendibility result is strictly weaker than "
            "this class's conclusion"
        )
    def c08(d):
        d["regularity"]["must_not_conflate"] = []
    def c09(d):
        d["regularity"]["must_not_conflate"].append(
            "an unrelated carrier that must leave D1/D2 unchanged"
        )

    specs = [
        ("C01", "live rev13", live_text, live_doc, {"D1": "fail", "D1b": "pass", "D2": "fail"}),
        ("C02", "candidate 84b5d3fa", cand_text, cand_doc, {"D1": "pass", "D1b": "pass", "D2": "pass"}),
        ("C03", "denial paraphrase", None, live_doc, {"D1": "fail", "D1b": "pass", "D2": "fail"}, c03),
        ("C04", "historical-only mention", None, live_doc, {"D1": "pass", "D1b": "pass", "D2": "fail"}, c04),
        ("C05", "inversion paraphrase", None, cand_doc, {"D1": "pass", "D1b": "pass", "D2": "fail"}, c05),
        # C06 is built on the live carrier so that D1 stays fail, as pre-registered; the mutant
        # isolates the D2 paraphrase.
        ("C06", "correct paraphrase", None, live_doc, {"D1": "fail", "D1b": "pass", "D2": "pass"}, c06),
        ("C07", "reversed chain", None, live_doc, {"D1": "fail", "D1b": "fail", "D2": "fail"}, None),
        ("C08", "empty must_not_conflate", None, live_doc, {"D1": "fail", "D1b": "pass", "D2": "fail",
                                                             "canonical_gate_nonzero": True}, c08),
        ("C09", "candidate + unrelated carrier", None, cand_doc, {"D1": "pass", "D1b": "pass", "D2": "pass"}, c09),
    ]

    sandbox = HERE / "sandbox"
    sandbox.mkdir(exist_ok=True)
    results = []
    for spec in specs:
        cid, label, text, doc, expect, fn = (list(spec) + [None] * 6)[:6]
        try:
            if cid == "C07":
                text, delta = mutate_text(live_text, CHAIN_SENT, "E_C2 contains E_C0", "C07")
                subject_doc = strict_load(text)
            elif fn is not None:
                text, delta = mutate_parsed(doc, fn, cid)
                subject_doc = strict_load(text)
            else:
                subject_doc = doc
                delta = {"mode": "none", "tag": cid}
            sem = semantics(text, subject_doc)
            observed = {"D1": "pass" if sem["D1"]["ok"] else "fail",
                        "D1b": "pass" if sem["D1b"]["ok"] else "fail",
                        "D2": "pass" if sem["D2"]["ok"] else "fail"}
            sub_path = sandbox / f"{cid}.yaml"
            sub_path.write_text(text)
            if cid in {"C02", "C08"}:
                gate = subprocess.run([sys.executable, str(ROOT / GATE), str(sub_path)],
                                      capture_output=True, text=True, timeout=120)
                observed["canonical_gate_exit"] = gate.returncode
                if cid == "C08":
                    observed["canonical_gate_nonzero"] = gate.returncode != 0
            ok = all(observed.get(k) == v for k, v in expect.items())
            results.append({"id": cid, "label": label, "expected": expect, "observed": observed,
                            "pass": ok, "delta": delta, "subject_sandbox": str(sub_path.relative_to(ROOT))})
        except Exception as exc:  # pragma: no cover
            results.append({"id": cid, "label": label, "expected": expect, "observed": {"error": str(exc)},
                            "pass": False, "delta": delta if "delta" in dir() else None})
    return {"controls_total": len(results), "controls_passed": sum(1 for r in results if r["pass"]),
            "items": results}


# ---------------------------------------------------------------- main

def core_of_live() -> dict:
    pins_entry = {rel: measure(rel) for rel in PINS}
    _, doc, text = load_subject(CANON_F2B)
    sem = semantics(text, doc)
    mech = mechanics(doc, text)
    pins_exit = {rel: measure(rel) for rel in PINS}
    drift = [rel for rel in PINS if pins_entry[rel]["sha256"] != pins_exit[rel]["sha256"]]
    verdict = decide(sem, mech, doc.get("revision"))
    core = {
        "predicate_id": "W002-F2B-REV14-LANDING-PREDICATE-01",
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "pins_entry": pins_entry,
        "pins_exit": pins_exit,
        "pin_drift": drift,
        "subject_revision": doc.get("revision"),
        "subject_sha256": pins_entry[CANON_F2B]["sha256"],
        "semantics": sem,
        "mechanics": mech,
        "verdict": verdict,
        "verdict_meaning": {
            "FAIL_REC36_OPEN": "pre-landing state: the two REC-36 F2b defects are live; not a failure of this instrument",
            "PASS_CANDIDATE_REV14": "post-landing F2b portion of REC-36 is complete and structurally well-formed (candidate for r3, not a gate verdict)",
            "FAIL_REV14_STILL_DEFECTIVE": "revision >= 14 but a defect carrier is still live",
            "FAIL_MECHANICS": "semantics clean but a landing-mechanics check failed",
            "FAIL_UNSANCTIONED_BYTE_MOVE": "canonical bytes moved without the authorized revision bump",
        }[verdict],
        "falsifier": ("Re-run this instrument on the same pins: any pin move, any departure of the live "
                      "measurement from PREREGISTRATION.json pre_registered_predictions P1-P7, any control "
                      "departing from its pre-registered expectation, or a differing core_digest across two "
                      "consecutive runs falsifies this measurement."),
        "next_falsifier": ("After the authorized rev14 landing: re-run --live; PASS_CANDIDATE_REV14 must be "
                           "reproduced at the new pins, and any out-of-scope F2b leaf change, unresolved FROZEN "
                           "pin, mirror mismatch or missing rollback copy returns FAIL_MECHANICS."),
        "authority_note": ("Worker measurement and predicate evidence only. No canonical file was written; no "
                           "gate verdict, validation_status=passed or node status=done is claimed."),
        "non_claims": [
            "does not decide mathematics or physical correctness",
            "does not replace a binding reviewer verdict in astra-life05-verify-gform-r3",
            "M6 is an informational census, not a coverage ruling (CF-31)",
        ],
    }
    # M6 is a census of concurrent review traffic, which is not stationary while other agents
    # write; it stays in the report but is excluded from the determinism digest.
    digest_payload = json.loads(json.dumps(core))
    for chk in digest_payload["mechanics"]["checks"]:
        if chk["id"] == "M6":
            chk["detail"] = {"excluded_from_core_digest": True,
                             "reason": "informational census of concurrent review traffic"}
    core["core_digest"] = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return core


def run_live() -> dict:
    core = core_of_live()
    core["determinism_repeat_equal"] = core_of_live()["core_digest"] == core["core_digest"]
    report = dict(core)
    report["schema"] = "w002-rev14-predicate/report/1"
    report["actor"] = "worker-002"
    report["agent_id"] = "deepseek-flash-02"
    report["generated_at"] = datetime.now(CST).isoformat(timespec="seconds")
    report["preregistration"] = "artifacts/worker-002/f2b_rev14_landing_predicate/PREREGISTRATION.json"
    report["evidence_refs"] = [
        f"{CANON_F2B}#{PINS[CANON_F2B][:12]}",
        f"{MIRROR_F2B}#{PINS[MIRROR_F2B][:12]}",
        f"{CANDIDATE}#{CANDIDATE_SHA[:12]}",
        f"{FROZEN}#{PINS[FROZEN][:12]}",
        f"research_map/formulation_taxonomy.yaml#{PINS['research_map/formulation_taxonomy.yaml'][:12]}",
        "runtime/state/controller_verification/astra-lifecycle-08-decisions.json#REC-36",
    ]
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


def run_controls() -> dict:
    ctl = build_controls()
    ctl.update({
        "schema": "w002-rev14-predicate/controls/1",
        "predicate_id": "W002-F2B-REV14-LANDING-PREDICATE-01",
        "actor": "worker-002",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "preregistration": "artifacts/worker-002/f2b_rev14_landing_predicate/PREREGISTRATION.json",
        "verdict": "ALL_CONTROLS_AS_PREREGISTERED" if ctl["controls_passed"] == ctl["controls_total"] else "CONTROL_DEPARTURE",
    })
    (HERE / "controls.json").write_text(json.dumps(ctl, indent=1) + "\n")
    return ctl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if not (args.live or args.controls or args.all):
        ap.error("choose --live, --controls or --all")
    rc = 0
    if args.live or args.all:
        rep = run_live()
        print(f"live: {rep['verdict']} core_digest={rep['core_digest'][:16]} "
              f"hard={[f['id'] for f in rep['semantics']['hard_findings']]} "
              f"drift={rep['pin_drift']}")
        # exit codes: 0 = pre-landing expected, 10 = pre-landing unexpected, 20 = post-landing pass,
        # 21 = post-landing fail
        rc = {"FAIL_REC36_OPEN": 0, "PASS_CANDIDATE_REV14": 20}.get(rep["verdict"], 21)
    if args.controls or args.all:
        ctl = run_controls()
        print(f"controls: {ctl['controls_passed']}/{ctl['controls_total']} {ctl['verdict']}")
        if ctl["controls_passed"] != ctl["controls_total"]:
            rc = max(rc, 30) if rc else 30
    return rc


if __name__ == "__main__":
    sys.exit(main())
