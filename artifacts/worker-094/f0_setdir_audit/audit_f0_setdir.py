#!/usr/bin/env python3
"""W094E-F0-SETDIR-01 -- read-only, hash-pinned audit of the AF-WCC-VAC-GEN variant SET
direction language at the FROZEN rev29 pins.

Question. F0/F1/registry/delta all describe the relation between
  P(q) = "some tail of gamma lies in J^-(q) for one q"   (canonical single-q tail predicate)
  S    = "gamma lies in the union of J^-(q) over all q"  (variant SET predicate)
Two different levels are in play:
  predicate level : P entails S and not conversely  =>  S is strictly WEAKER than P;
  statement level : variant SET asserts not-S, the parent asserts not-P, and
                    not-S entails not-P, not conversely  =>  the SET variant is strictly
                    STRONGER than its parent class.
A direction phrase is adjudicated at the level of its grammatical subject; the expected
label therefore differs by level.  The audit extracts every live direction claim about SET
from the pinned bytes, classifies its level with a pre-registered rule, and reports
label/level conflicts -- in particular whether the 2026-09-12T00:57:26 re-base of
VARIANT_REGISTRY.json and the SET delta moved a class-level label in the wrong direction while
the owner's own checker still returns VALID.

Exit codes: 0 = measured; 2 = UNMEASURED (pin drift / missing input); 3 = instrument invalid
(a declared control did not behave as pre-registered).

Read-only on every canonical path: nothing outside artifacts/worker-094/... is written.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
RUN = OUT / "run"
TZ = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- pinned inputs
# measured 2026-09-12T01:0x+08:00; any change during the run voids the snapshot.
PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/tools/check_variant_registry.py":
        "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
# corroborating peer artifact, cited but NOT load-bearing: worker-076 was revising it during
# this run, so a change must not void this audit.  Measured once and recorded.
ADVISORY_REFS = (
    "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
)
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPPL = "artifacts/formulation/formulation_taxonomy.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
REG = "artifacts/formulation/VARIANT_REGISTRY.json"
DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CHECKER = "artifacts/formulation/tools/check_variant_registry.py"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def measure_pins() -> dict:
    out = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.exists():
            out[rel] = {"expected": expected, "measured": None, "ok": False,
                        "error": "missing"}
            continue
        b = p.read_bytes()
        m = sha256_bytes(b)
        out[rel] = {"expected": expected, "measured": m, "ok": m == expected,
                    "bytes": len(b)}
    return out


# ---------------------------------------------------------------- level rules
# Pre-registered: the level of a direction phrase is the level of its grammatical subject.
PREDICATE_SUBJECTS = (
    "the set-based reading", "the union reading", "the set based reading",
    "the predicate", "single-q tail predicate", "tail predicate",
    "visibility =", "the definition", "the reading", "is implied by", "as a set",
)
CLASS_SUBJECTS = (
    "than the parent class", "than af-wcc-vac-gen", "than its parent",
    "the variant class", "the variant is", "variant set is", "as a class",
)
STATEMENT_SUBJECTS = (
    "the negation", "single-q negation", "the class conclusion", "class statement",
    "the conclusion ",
)


def classify_level(text: str) -> str:
    """Return predicate | class | statement | mixed | unlabeled for a direction phrase.
    A clause that names the negation is statement-level by construction (the negation of a
    visibility predicate is the class conclusion)."""
    t = text.lower()
    if "negation" in t:
        return "statement"
    pred = any(s in t for s in PREDICATE_SUBJECTS)
    cls = any(s in t for s in CLASS_SUBJECTS)
    stm = any(s in t for s in STATEMENT_SUBJECTS)
    kinds = [k for k, hit in (("predicate", pred), ("class", cls), ("statement", stm)) if hit]
    if len(kinds) == 1:
        return kinds[0]
    if len(kinds) > 1:
        return "mixed"
    return "unlabeled"


def operative(text: str) -> str:
    """Drop revision/correction notes so a 'corrected from strictly STRONGER' mention cannot be
    read as an operative direction assertion.  The bracket must start with a revision marker
    (rev/R/W/CF-number), so interval notation such as gamma([0,T)) survives and a note cannot
    swallow the clause that precedes it."""
    return re.sub(r"\[(?:rev\d|R\d|W\d|CF-\d)[^\]]*\]", " ", text)


def direction_of(text: str) -> str | None:
    t = operative(text).lower()
    strong = re.search(r"strictly\s+stronger", t)
    weak = re.search(r"strictly\s+weaker", t)
    if strong and not weak:
        return "stronger"
    if weak and not strong:
        return "weaker"
    if strong and weak:
        return "both"
    return None


EXPECTED = {"predicate": "weaker", "class": "stronger", "statement": "stronger"}


def judge(level: str, direction: str | None) -> str:
    if direction is None:
        return "no_direction"
    if level in EXPECTED:
        return "consistent" if direction == EXPECTED[level] else "inverted"
    return "level_ambiguous"


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def newline_span(text: str, idx: int) -> list:
    a = text.rfind("\n", 0, idx) + 1
    b = text.find("\n", idx)
    if b < 0:
        b = len(text)
    return [line_of(text, a), line_of(text, max(a, b - 1))]


def line_shas(text: str, span: list) -> list:
    lines = text.splitlines()
    return [sha256_bytes(lines[i - 1].encode())[:12]
            for i in range(span[0], span[1] + 1) if 1 <= i <= len(lines)]


# ---------------------------------------------------------------- predicate model
def is_transitive(rel: set, n: int) -> bool:
    return all((a, c) in rel for a in range(n) for b in range(n) for c in range(n)
               if (a, b) in rel and (b, c) in rel)


def all_preorders(n: int):
    pairs = [(i, j) for i in range(n) for j in range(n)]
    for mask in range(1 << len(pairs)):
        rel = {pairs[k] for k in range(len(pairs)) if mask >> k & 1}
        if all((i, i) in rel for i in range(n)) and is_transitive(rel, n):
            yield rel


def nondecreasing_sequences(rel: set, n: int, max_len: int):
    seqs = [[i] for i in range(n)]
    out = list(seqs)
    for _ in range(max_len - 1):
        nxt = []
        for s in seqs:
            for j in range(n):
                if (s[-1], j) in rel:
                    nxt.append(s + [j])
        out.extend(nxt)
        seqs = nxt
    return out


def p_holds(rel: set, gamma: list, q) -> bool:
    n = len(gamma)
    return any(all((gamma[t], q) in rel for t in range(t0, n)) for t0 in range(n))


def whole_holds(rel: set, gamma: list, q) -> bool:
    return all((x, q) in rel for x in gamma)


def s_holds(rel: set, gamma: list, ip: list) -> bool:
    return all(any((x, q) in rel for q in ip) for x in gamma)


def census(n: int, max_len: int = 4) -> dict:
    """Enumerate all preorders and causal gamma; check P=>S, finite collapse S=>P, and the
    whole-curve single-q predicate equivalence (T1 replication)."""
    p_implies_s = s_not_p = finite_s_not_p = whole_neq_tail = 0
    cases = 0
    preorders = 0
    for rel in all_preorders(n):
        preorders += 1
        seqs = nondecreasing_sequences(rel, n, max_len)
        for gamma in seqs:
            for r in range(1, n + 1):
                ip = list(range(r))
                for q in ip:
                    for _ in (0,):
                        cases += 1
                        ph = p_holds(rel, gamma, q)
                        sh = s_holds(rel, gamma, ip)
                        if ph and not sh:
                            p_implies_s += 1
                        if ph != whole_holds(rel, gamma, q):
                            whole_neq_tail += 1
                if s_holds(rel, gamma, ip) and not any(p_holds(rel, gamma, q) for q in ip):
                    finite_s_not_p += 1
                    s_not_p += 1
    return {"n": n, "preorders": preorders, "cases": cases,
            "P_implies_S_violations": p_implies_s,
            "finite_S_and_not_P_violations": finite_s_not_p,
            "whole_curve_neq_tail_violations": whole_neq_tail}


def omega_chain(n: int) -> dict:
    """Model: gamma = (x_i)_{i in N}, I+ = {q_j}_{j in N}, x_i <= q_j iff i <= j.
    S holds (x_i <= q_i).  No q_j sees a tail: for any t0 the tail contains x_t with
    t = max(t0, j+1) > j, and x_t <= q_j is false.  The witness index is computed, not
    asserted; it lies beyond the finite enumeration because the model is unbounded."""
    def s_holds_symbolic() -> bool:
        return all(any(i <= j for j in range(n)) for i in range(n))

    witnesses = []
    for j in range(n):
        found = None
        for t0 in range(n + 1):
            # a tail from t0 is inside J^-(q_j) iff every t >= t0 has t <= j; exhibit the
            # first violating index (t = max(t0, j+1)) rather than testing a finite window
            t = max(t0, j + 1)
            if not (t <= j):
                found = {"t0": t0, "violating_t": t}
                break
        witnesses.append(found)
    return {"N": n, "S": s_holds_symbolic(),
            "exists_q_with_tail": any(w is None for w in witnesses),
            "tail_search": "for each q_j a tail from t0 is refuted by x_t, t=max(t0,j+1)>j; "
                           "a q_j sees a tail only if some t0 has no refutation",
            "first_refutation_per_q": witnesses[:3],
            "i_le_j_rule": "x_i <= q_j iff i <= j"}


def non_transitive_control() -> dict:
    """Reflexive closure of {(a,b),(b,q)}: P(q) holds (tail [b,q] inside J^-(q)) while S fails
    because a is not <= q.  Shows the P=>S step needs transitivity and the harness sees it."""
    rel = {("a", "a"), ("b", "b"), ("q", "q"), ("a", "b"), ("b", "q")}
    gamma = ["a", "b", "q"]
    ip = ["q"]
    missing = [(a, c) for a in ("a", "b", "q") for b in ("a", "b", "q")
               for c in ("a", "b", "q") if (a, b) in rel and (b, c) in rel
               and (a, c) not in rel]
    return {"P": p_holds(rel, gamma, "q"), "S": s_holds(rel, gamma, ip),
            "transitive": not missing, "missing_transitivity_witness": missing[:3]}


# ---------------------------------------------------------------- extraction
def extract_f0_variants(text: str) -> dict:
    m = re.search(r'variant_id:\s*"SET"', text)
    if not m:
        return {"found": False}
    seg = text[m.start():m.start() + 900]
    span = newline_span(text, m.start())
    dm = re.search(r"Strictly (stronger|weaker) than the parent class", seg)
    return {"found": True, "line": span,
            "phrase_line": [line_of(text, m.start() + dm.start())] if dm else span,
            "direction_phrase": dm.group(0) if dm else None,
            "context": " ".join(seg.split())[:260]}


def extract_f0_reading(text: str) -> dict:
    m = re.search(r"The set-based reading[^;]{0,240}?is (strictly (?:stronger|weaker))", text)
    if not m:
        return {"found": False}
    span = newline_span(text, m.start())
    sentence = " ".join(text[m.start():m.end() + 1].split())
    return {"found": True, "lines": span, "line_sha": line_shas(text, span),
            "sentence": sentence, "direction": direction_of(sentence),
            "level": classify_level(sentence)}


def extract_supplement_d1(text: str) -> dict:
    row = re.search(r'id:\s*D1.*?\n', text)
    m = re.search(r'f0_reading:\s*"([^"]*)"', text)
    if not m:
        return {"found": False}
    val = m.group(1)
    span = newline_span(text, m.start())
    return {"found": True, "lines": span, "line_sha": line_shas(text, span),
            "value": val, "direction": direction_of(val), "level": classify_level(val),
            "relation_note": "the same row's relation field ('F0 was stronger') is a "
                             "statement-level claim and is separately correct"}


def extract_f1_relation(text: str) -> dict:
    m = re.search(r"relation:\s*\"(strictly [A-Z]+ than this class's single-q tail predicate[^\"]*)", text)
    if not m:
        return {"found": False}
    val = m.group(1)
    span = newline_span(text, m.start())
    return {"found": True, "lines": span, "line_sha": line_shas(text, span),
            "value": " ".join(val.split())[:300], "direction": direction_of(val),
            "level": classify_level(val)}


def extract_registry(reg: dict) -> dict:
    setv = next((v for v in reg.get("variants", [])
                 if v.get("parent_class") == "AF-WCC-VAC-GEN"
                 and v.get("variant_id") == "SET"), None)
    if not setv:
        return {"found": False}
    strength = setv.get("strength", "")
    label = strength.split("(", 1)[0].strip()
    return {"found": True, "strength": strength, "label": label,
            "label_direction": direction_of(label), "label_level": classify_level(label),
            "justification_statement_level": "not conversely" in strength,
            "has_correction_note": "corrected from" in strength,
            "note_contains_stronger": ("STRONGER" in strength.split("[", 1)[-1])
            if "[" in strength else False}


def extract_delta(delta: dict) -> dict:
    strength = delta.get("strength", "")
    label = strength.split("(", 1)[0].strip()
    to_texts = []
    for ch in delta.get("changes", []):
        if isinstance(ch, dict) and isinstance(ch.get("to"), str):
            to_texts.append({"path": ch.get("path"), "to": ch["to"]})
    return {"found": True, "strength": strength, "label": label,
            "label_direction": direction_of(label), "label_level": classify_level(label),
            "changes_to": to_texts}


# ---------------------------------------------------------------- official checker sandbox
def run_official_checker_sandbox() -> dict:
    """Copy the owner's checker + inputs into a local sandbox and run it three times:
    (a) live registry; (b) correction notes stripped; (c) class-level label restored."""
    sb = OUT / "sandbox"
    for sub in ("artifacts/formulation/tools", "artifacts/formulation/evidence",
                "artifacts/formulation/variants", "schemas"):
        (sb / sub).mkdir(parents=True, exist_ok=True)
    for rel in (CHECKER, "artifacts/formulation/FROZEN.json",
                "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml"):
        (sb / rel).write_bytes((ROOT / rel).read_bytes())
    for delta in (ROOT / "artifacts/formulation/variants").glob("*.json"):
        (sb / "artifacts/formulation/variants" / delta.name).write_bytes(delta.read_bytes())

    def execute(label: str, registry_obj: dict) -> dict:
        (sb / REG).write_text(json.dumps(registry_obj, indent=2) + "\n")
        proc = subprocess.run([sys.executable, str(sb / CHECKER)],
                              capture_output=True, text=True, cwd=str(sb))
        return {"label": label, "exit": proc.returncode,
                "stdout_tail": proc.stdout.strip().splitlines()[-6:] if proc.stdout else [],
                "stderr_tail": proc.stderr.strip().splitlines()[-3:] if proc.stderr else []}

    live = json.loads((ROOT / REG).read_text())
    results = [execute("live_registry", live)]

    stripped = json.loads(json.dumps(live))
    for v in stripped.get("variants", []):
        if v.get("variant_id") == "SET":
            v["strength"] = v["strength"].split("[", 1)[0].strip()
    results.append(execute("live_registry_with_correction_notes_stripped", stripped))

    fixed = json.loads(json.dumps(live))
    for v in fixed.get("variants", []):
        if v.get("variant_id") == "SET":
            v["strength"] = ("strictly STRONGER than AF-WCC-VAC-GEN as a class statement "
                             "(not-S entails not-P, not conversely), while the SET predicate "
                             "is strictly weaker than the single-q tail predicate")
    results.append(execute("class_level_label_restored", fixed))
    return {"sandbox": str(sb.relative_to(ROOT)), "runs": results}


# ---------------------------------------------------------------- claim assembly
def build_claims(pins: dict) -> list:
    f0 = (ROOT / F0_CANON).read_text()
    sup = (ROOT / F0_SUPPL).read_text()
    f1 = (ROOT / F1).read_text()
    reg = json.loads((ROOT / REG).read_text())
    delta = json.loads((ROOT / DELTA).read_text())
    claims = []

    v = extract_f0_variants(f0)
    claims.append({"site": "F0-canonical variants[SET].definition", "artifact": F0_CANON,
                   "lines": v.get("phrase_line") or v.get("line"), "line_sha": None,
                   "text": v.get("context"),
                   "level": "class", "asserted": direction_of(v.get("direction_phrase") or ""),
                   "expected": "stronger",
                   "verdict": judge("class", direction_of(v.get("direction_phrase") or "")),
                   "note": "subject is the variant compared with the parent class"})

    l = extract_f0_reading(f0)
    claims.append({"site": "F0-canonical class_identity_variants (SET reading)",
                   "artifact": F0_CANON, "lines": l.get("lines"), "line_sha": l.get("line_sha"),
                   "text": l.get("sentence"), "level": l.get("level"),
                   "asserted": l.get("direction"), "expected": EXPECTED.get(l.get("level")),
                   "verdict": judge(l.get("level"), l.get("direction")),
                   "note": "grammatical subject is 'The set-based reading', i.e. the predicate"})

    d = extract_supplement_d1(sup)
    claims.append({"site": "F0-supplement contract_divergences D1.f0_reading",
                   "artifact": F0_SUPPL, "lines": d.get("lines"), "line_sha": d.get("line_sha"),
                   "text": d.get("value"), "level": d.get("level"),
                   "asserted": d.get("direction"), "expected": EXPECTED.get(d.get("level")),
                   "verdict": judge(d.get("level"), d.get("direction")),
                   "note": d.get("relation_note")})

    r = extract_f1_relation(f1)
    claims.append({"site": "F1 class_identity_variants[SET].relation", "artifact": F1,
                   "lines": r.get("lines"), "line_sha": r.get("line_sha"),
                   "text": r.get("value"), "level": r.get("level"),
                   "asserted": r.get("direction"), "expected": EXPECTED.get(r.get("level")),
                   "verdict": judge(r.get("level"), r.get("direction")),
                   "note": "rev13 repair; predicate-level subject"})

    rr = extract_registry(reg)
    claims.append({"site": "VARIANT_REGISTRY variants[SET].strength (label)", "artifact": REG,
                   "lines": None, "text": rr.get("label"), "level": rr.get("label_level"),
                   "asserted": rr.get("label_direction"),
                   "expected": EXPECTED.get(rr.get("label_level")),
                   "verdict": judge(rr.get("label_level"), rr.get("label_direction")),
                   "justification_statement_level": rr.get("justification_statement_level"),
                   "note": "label compares the variant with the class; the following clause "
                           "(not-S => not-P, not conversely) entails the opposite direction"})

    dd = extract_delta(delta)
    claims.append({"site": "SET-delta strength (label)", "artifact": DELTA, "lines": [11],
                   "text": dd.get("label"), "level": dd.get("label_level"),
                   "asserted": dd.get("label_direction"),
                   "expected": EXPECTED.get(dd.get("label_level")),
                   "verdict": judge(dd.get("label_level"), dd.get("label_direction")),
                   "note": "label compares the variant with the class"})
    mixed = next((c["to"] for c in dd["changes_to"] if "implied by" in c["to"]), "")
    claims.append({"site": "SET-delta changes[visibility.definition].to", "artifact": DELTA,
                   "lines": [22], "text": mixed[:400], "level": classify_level(mixed),
                   "asserted": direction_of(mixed), "expected": EXPECTED.get(classify_level(mixed)),
                   "verdict": judge(classify_level(mixed), direction_of(mixed)),
                   "note": "predicate-level clause; correct after the rev29 re-base"})
    neg = next((c["to"] for c in dd["changes_to"] if "single-q negation" in c["to"]), "")
    claims.append({"site": "SET-delta changes[visibility.negation_conclusion].to",
                   "artifact": DELTA, "lines": [27], "text": neg[:300],
                   "level": classify_level(neg), "asserted": direction_of(neg),
                   "expected": EXPECTED.get(classify_level(neg)),
                   "verdict": judge(classify_level(neg), direction_of(neg)),
                   "note": "statement-level clause about the negation; correct"})
    return claims


# ---------------------------------------------------------------- main
def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    created = now_iso()
    pins = measure_pins()
    drift = [k for k, v in pins.items() if not v["ok"]]
    if drift:
        report = {"audit_id": "W094E-F0-SETDIR-01", "actor": "worker-094",
                  "created_at": created, "verdict": "UNMEASURED",
                  "reason": "pin drift or missing input before extraction",
                  "drift": drift, "pins": pins}
        (RUN / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("UNMEASURED:", drift)
        return 2

    claims = build_claims(pins)
    checker = run_official_checker_sandbox()

    c2, c3 = census(2), census(3)
    oc = [omega_chain(n) for n in (8, 24, 64)]
    nt = non_transitive_control()
    controls = [
        {"id": "C1-P-implies-S-finite-census",
         "description": "all preorders on 2 and 3 points, all causal gamma, all q: P entails S",
         "expected": {"n2": 0, "n3": 0},
         "observed": {"n2": c2["P_implies_S_violations"], "n3": c3["P_implies_S_violations"]},
         "ok": c2["P_implies_S_violations"] == 0 and c3["P_implies_S_violations"] == 0},
        {"id": "C2-finite-collapse",
         "description": "finite I+/gamma: S implies some single-q tail (0 violations)",
         "expected": {"n2": 0, "n3": 0},
         "observed": {"n2": c2["finite_S_and_not_P_violations"],
                      "n3": c3["finite_S_and_not_P_violations"]},
         "ok": c2["finite_S_and_not_P_violations"] == 0
               and c3["finite_S_and_not_P_violations"] == 0},
        {"id": "C3-omega-chain-separation",
         "description": "infinite I+ without causal maximum: S holds and no q sees a tail",
         "expected": {"S": True, "exists_q_with_tail": False}, "observed": oc,
         "ok": all(x["S"] and not x["exists_q_with_tail"] for x in oc)},
        {"id": "C4-non-transitive-control",
         "description": "drop transitivity: P holds while S fails; the harness sees it",
         "expected": {"P": True, "S": False}, "observed": nt,
         "ok": nt["P"] is True and nt["S"] is False},
        {"id": "C5-whole-curve-equals-tail",
         "description": "replicate T1: whole-curve single-q containment is equivalent to the "
                        "tail form on every finite preorder model",
         "expected": {"n2": 0, "n3": 0},
         "observed": {"n2": c2["whole_curve_neq_tail_violations"],
                      "n3": c3["whole_curve_neq_tail_violations"]},
         "ok": c2["whole_curve_neq_tail_violations"] == 0
               and c3["whole_curve_neq_tail_violations"] == 0},
    ]
    live_run, stripped_run, fixed_run = checker["runs"]
    controls.append({"id": "C6-owner-checker-note-sensitivity",
                     "description": "check_variant_registry requires 'STRONGER' in SET.strength; "
                                    "the live label is 'strictly weaker' and passes only because "
                                    "the bracket note contains the old token",
                     "expected": {"live": 0, "notes_stripped": 1, "class_level_restored": 0},
                     "observed": {"live": live_run["exit"],
                                  "notes_stripped": stripped_run["exit"],
                                  "class_level_restored": fixed_run["exit"]},
                     "ok": live_run["exit"] == 0 and stripped_run["exit"] == 1
                           and fixed_run["exit"] == 0})
    # C7 note stripper must not swallow the operative clause or interval notation
    probe = next((c["to"] for c in extract_delta(
        json.loads((ROOT / DELTA).read_text()))["changes_to"]
        if "implied by" in c["to"]), "")
    op = operative(probe)
    controls.append({"id": "C7-operative-note-stripping",
                     "description": "the revision-note stripper removes the corrected-from "
                                    "mention but keeps the operative clause and gamma([0,T))",
                     "expected": {"has_weaker": True, "has_note_stronger": False,
                                  "interval_intact": True},
                     "observed": {"has_weaker": "strictly weaker" in op.lower(),
                                  "has_note_stronger": "'strictly stronger'" in op.lower(),
                                  "interval_intact": "[0,T)" in op,
                                  "operative_prefix": op[:80]},
                     "ok": "strictly weaker" in op.lower()
                           and "'strictly stronger'" not in op.lower()
                           and "[0,T)" in op})
    instrument_ok = all(c["ok"] for c in controls)

    findings = []
    for cl in claims:
        if cl["verdict"] == "inverted":
            findings.append({"id": "F0V-SETDIR-" + str(len(findings) + 1).zfill(2),
                             "severity": "major", "site": cl["site"],
                             "artifact": cl["artifact"], "text": cl["text"],
                             "level": cl["level"], "asserted": cl["asserted"],
                             "expected": cl["expected"],
                             "consequence": "a direction phrase at this level licenses the "
                                            "wrong transfer between the SET variant and "
                                            "AF-WCC-VAC-GEN"})
    if live_run["exit"] == 0 and stripped_run["exit"] == 1:
        findings.append({
            "id": "F0V-SETDIR-CHECKER", "severity": "major",
            "site": "artifacts/formulation/tools/check_variant_registry.py#c471da4b7be9",
            "asserted": "SET strength label is 'strictly weaker than AF-WCC-VAC-GEN'",
            "required": "the same file requires 'STRONGER' in SET.strength "
                        "(\"variant SET must be marked stronger than its parent\")",
            "text": "the checker's SET requirement is a bare substring test; on the live "
                    "registry it is satisfied only by the bracket note \"corrected from "
                    "'strictly STRONGER'\" while the operative label is 'strictly weaker than "
                    "AF-WCC-VAC-GEN'",
            "consequence": "check_variant_registry reports VALID on a class-level label that "
                           "contradicts the checker's own stated requirement; stripping the "
                           "note makes it INVALID (control C6)"})

    report = {
        "audit_id": "W094E-F0-SETDIR-01", "actor": "worker-094", "created_at": created,
        "class_id": "AF-WCC-VAC-GEN", "variant_id": "SET", "node_id": "F0",
        "gate_context": "G-FORM / F0 class-identity and variant strength; L-FORM-03",
        "pins": pins,
        "level_model": {
            "predicate_level": "P (single-q tail) entails S (union), not conversely; "
                               "S is strictly WEAKER than P",
            "statement_level": "variant SET asserts not-S, parent asserts not-P; not-S "
                               "entails not-P, not conversely; the SET variant is strictly "
                               "STRONGER than its parent class",
            "adjudication_rule": "a direction phrase is judged at the level of its "
                                 "grammatical subject",
            "derivation": {"finite_census": [c2, c3], "omega_chain": oc,
                           "scope": "model-theoretic, in the declared causal-preorder "
                                    "semantics; physical realizability of the omega-chain "
                                    "is carried by the class's own T4 note"}},
        "claims": claims, "findings": findings, "checker_audit": checker,
        "controls": controls, "instrument_valid": instrument_ok,
        "advisory_refs": {rel: (sha256_file(ROOT / rel) if (ROOT / rel).exists() else None)
                          for rel in ADVISORY_REFS},
        "verdict": "MEASURED_INSTRUMENT_VALID" if instrument_ok else "INSTRUMENT_INVALID",
        "drift": [],
        "falsifier": "FALSE if any pinned input hash differs at re-measure; if the F0 "
                     "canonical sentence's grammatical subject is class-level rather than "
                     "predicate-level; if a claim read as class-level is in fact governed by "
                     "a declared predicate-level convention in the artifact; or if control "
                     "C6 does not reproduce (live checker exit != 0).",
        "authority_note": "Read-only worker evidence. No gate verdict, no node status, no "
                          "canonical file written; artifacts/worker-094/f0_setdir_audit only.",
    }
    final = measure_pins()
    drift_after = [k for k, v in final.items() if not v["ok"]]
    report["pins_after"] = final
    report["drift"] = drift_after
    if drift_after:
        report["verdict"] = "UNMEASURED"
        report["reason"] = "pin drift during the run"
        instrument_ok = False
    (RUN / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    manifest = {"audit_id": report["audit_id"], "created_at": created, "files": {}}
    for rel in ("audit_f0_setdir.py", "run/report.json"):
        p = OUT / rel
        if p.exists():
            manifest["files"][rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"{report['verdict']}: {len(findings)} finding(s); "
          f"instrument_valid={instrument_ok}; drift={drift_after}")
    for f in findings:
        print(f"  {f['id']} {f['site']}: {f.get('asserted')} (expected {f.get('expected')})")
    for c in controls:
        print(f"  control {c['id']}: {'ok' if c['ok'] else 'FAIL'}")
    return 0 if instrument_ok and not drift_after else (3 if not instrument_ok else 2)


if __name__ == "__main__":
    sys.exit(main())
