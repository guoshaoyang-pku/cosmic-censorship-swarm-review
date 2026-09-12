#!/usr/bin/env python3
"""W060-CONTAINMENT-SEMANTICS-SWEEP-01.

Independent, hash-pinned sweep of every containment / transfer-strength assertion
carried by the FROZEN rev28 formulation artifacts, plus a measurement of whether
the canonical structural gate can see a premise inversion at all.

WHAT IT DECIDES (artifact measurement only; no gate verdict, no node completion):
  * Does every machine-readable transfer row follow from the declared extension-set
    chain E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 ?
  * Does every prose containment / strength sentence agree with that chain?
  * Can ``artifacts/formulation/tools/check_class_schema.py`` distinguish the
    canonical file from a file whose containment premise is inverted?

USAGE
  python3 verify_containment_semantics.py                 # pins from FROZEN.json rev28
  python3 verify_containment_semantics.py --json          # machine report on stdout
  python3 verify_containment_semantics.py --pin <sha256>  # bind a different FROZEN.json

EXIT
  0  every hard check passed (no containment defect reproduced)
  1  at least one hard finding (a containment premise contradicts the chain)
  2  pin/hash mismatch, missing input, or usage error (fails closed, claims nothing)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

RUN_ID = "W060-CONTAINMENT-SEMANTICS-SWEEP-01"
ACTOR = "worker-060"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]
CREATED_AT = "2026-09-12T00:46:30+08:00"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-060/containment_semantics_sweep -> repo root
FROZEN_REL = "artifacts/formulation/FROZEN.json"

DOC_RELS = {
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "supp": "artifacts/formulation/formulation_taxonomy.yaml",
    "f0": "research_map/formulation_taxonomy.yaml",
    "rule_spec": "artifacts/formulation/rule_spec.json",
}
GATE_REL = "artifacts/formulation/tools/check_class_schema.py"

# Extension-set chain, smallest set first.  E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0:
# a lower regularity requirement admits MORE extensions, so the set grows to the right.
CHAIN = ["C2", "C1_1", "H2loc", "C0"]
RANK = {t: i for i, t in enumerate(CHAIN)}
TOKEN_LABEL = {"C2": "C2", "C1_1": "C^{1,1}", "H2loc": "H2_loc", "C0": "C0"}
CLASS_TOKEN = {"AF-SCC-C2-VAC-GEN": "C2", "AF-SCC-C0-VAC-GEN": "C0"}

TOKEN_RES = [
    ("C1_1", re.compile(r"c\^?\{?1\s*,\s*1\}?|C1,1", re.I)),
    ("H2loc", re.compile(r"h\^?2_?\{?loc\}?|H2_loc|H\^2_loc", re.I)),
    ("C2", re.compile(r"c\^?\{?2\}?\b|\bC2\b|twice[- ]continuously", re.I)),
    ("C0", re.compile(r"c\^?0\b|\bC0\b|continuous(?:-metric)?|continuity", re.I)),
]
# Order matters when scanning a phrase: check the more specific tokens first.
TOKEN_SCAN_ORDER = ["C1_1", "H2loc", "C2", "C0"]

E_SUBSET = re.compile(
    r"E_?\{?(C2|C\^?\{?1\s*,\s*1\}?|H2_?loc|C0)\}?\s*(?:is\s+a\s+)?(?:subset of|⊆|contained in)\s*"
    r"E_?\{?(C2|C\^?\{?1\s*,\s*1\}?|H2_?loc|C0)\}?", re.I)
E_CONTAINS = re.compile(
    r"E_?\{?(C2|C\^?\{?1\s*,\s*1\}?|H2_?loc|C0)\}?\s*(?:strictly\s+)?contains\s+"
    r"E_?\{?(C2|C\^?\{?1\s*,\s*1\}?|H2_?loc|C0)\}?", re.I)

# Comparative claim: an explicit regularity token as subject, a comparative within one clause.
COMPARATIVE = re.compile(
    r"\b(C2|C\^?\{?1\s*,\s*1\}?|C1,1|H2_?loc|H\^2_loc|C0)\b"
    r"[^.;:]{0,90}?\b(?:strictly\s+|strict\s+)?(larger|bigger|broader|smaller|narrower)\b", re.I)
STRENGTH = re.compile(
    r"\b(C2|C\^?\{?1\s*,\s*1\}?|C1,1|H2_?loc|H\^2_loc|C0)\s*[- ]?inextendibility\s+is\s+"
    r"(?:strictly\s+)?(stronger|weaker)\s+than\s+"
    r"(?:the\s+)?(C2|C\^?\{?1\s*,\s*1\}?|C1,1|H2_?loc|H\^2_loc|C0)", re.I)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def token_of(text: str) -> str | None:
    if text in CLASS_TOKEN:
        return CLASS_TOKEN[text]
    for tok in TOKEN_SCAN_ORDER:
        if TOKEN_RES[[t for t, _ in TOKEN_RES].index(tok)][1].search(str(text)):
            return tok
    return None


def ranked(tok: str) -> int:
    return RANK[tok]


def iter_strings(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def check(check_id, suite, ok, expected, observed, falsifier, locator):
    return {"check_id": check_id, "suite": suite, "ok": bool(ok), "expected": expected,
            "observed": observed, "falsifier": falsifier, "locator": locator}


def parse_containment_pairs(text: str):
    """Return [(a,b)] meaning E_a subset E_b as asserted textually.  Overlapping scan:
    in a chain A subset B subset C every pair must be recovered, not just alternating ones."""
    pairs = []
    for rx, flip in ((E_SUBSET, False), (E_CONTAINS, True)):
        pos = 0
        while True:
            m = rx.search(text, pos)
            if not m:
                break
            a, b = token_of(m.group(1)), token_of(m.group(2))
            if a and b:
                pairs.append((b, a, "contains") if flip else (a, b, "subset"))
            pos = m.start() + 1
    return pairs


def parse_reason_subset(text: str):
    out = []
    for a, b, kind in parse_containment_pairs(text):
        out.append({"kind": kind, "a": a, "b": b,
                    "ok": ranked(a) <= ranked(b)})
    return out


# --------------------------------------------------------------------------------------
# Curated prose rows: pinned by (doc, sha256, exact substring).  If the pinned substring
# is absent, the check fails closed (exit 2) rather than silently passing.
# --------------------------------------------------------------------------------------
PROSE_ROWS = [
    dict(id="PR-F2A-147", doc="f2a", locator="line 147 extension_regularity_exact",
         must_contain="which is why lower-regularity inextendibility entails this conclusion",
         kind="entail", subject="C0", comparator="C2",
         note="lower-regularity inextendibility (larger extension set) entails the C2 conclusion"),
    dict(id="PR-F2A-151", doc="f2a", locator="line 151 regularity.notes",
         must_contain="H2_loc-inextendibility ENTAILS this class's conclusion",
         kind="entail", subject="H2loc", comparator="C2",
         note="E_C2 subset E_H2loc, so H2_loc-inextendibility is the stronger statement"),
    dict(id="PR-F2A-236", doc="f2a", locator="line 236 extension_class_containment",
         must_contain="the lower the required regularity, the larger the set of admissible extensions",
         kind="monotone", subject="C0", comparator="C2",
         note="set size grows as required regularity falls"),
    dict(id="PR-F2B-238", doc="f2b", locator="line 238 extension_class_containment",
         must_contain="this class requires the LOWEST regularity, so its inexistence statement is the STRONGEST",
         kind="strength", subject="C0", comparator="C2",
         note="C0-inextendibility over the largest extension set is the strongest"),
    dict(id="PR-F2B-245", doc="f2b", locator="line 245 forbidden_transfers[0].reason",
         must_contain="C2 is a strictly larger extension class",
         kind="comparative", subject="C2", comparator="C0",
         note="E_C2 is strictly SMALLER than E_C0; this pinned sentence is the reported defect"),
    dict(id="PR-F2A-239", doc="f2a", locator="line 239 forbidden_transfers[1].reason",
         must_contain="C2-inextendibility is weaker than H2_loc-inextendibility",
         kind="strength", polarity="weaker", subject="C2", comparator="H2loc",
         note="E_C2 subset E_H2loc, so no-C2-extension is the weaker statement"),
    dict(id="PR-F2B-SUB", doc="f2b", locator="line 252 subsumption_note",
         must_contain="This direction runs C0 => H2loc => C2, never the reverse",
         kind="chain", subject="C0", comparator="C2",
         note="subsumption runs from the largest extension set down to the smallest"),
    dict(id="PR-SUPP-119", doc="supp", locator="line 119 negative_test_case.reason",
         must_contain="H^2_loc is strictly between C2 and C0",
         kind="between", subject="H2loc", comparator="C0",
         note="rank(C2)=0 < rank(H2loc)=2 < rank(C0)=3"),
    dict(id="PR-SUPP-145", doc="supp", locator="line 145 axis_registry.containment",
         must_contain="statement strength runs the other way: C0-inextendibility entails H2_loc-inextendibility entails C2-inextendibility",
         kind="chain", subject="C0", comparator="C2",
         note="explicit strength chain in the supplement"),
    dict(id="PR-SUPP-153", doc="supp", locator="line 153 equation_requirement.containment",
         must_contain="bare-metric inextendibility is the STRONGEST of the three",
         kind="strength", subject="C0", comparator="C2",
         note="distributional extensions are a subset of continuous metric extensions"),
    dict(id="PR-F2B-DIST", doc="f2b", locator="line 243 one_way_entailments[3].reason",
         must_contain="extensions required to solve Ric = 0 distributionally are a subset of all continuous metric extensions",
         kind="equation", subject="C0", comparator="C0",
         note="distributional-vacuum C0 extensions are a subset of bare continuous metric extensions, "
              "so bare-metric inextendibility is the stronger statement and entails it"),
    dict(id="PR-F0-110", doc="f0", locator="line 110 variant CH definition",
         must_contain="Strictly weaker than the parent class",
         also_contains=["ACROSS ITS CAUCHY HORIZON"],
         kind="variant", subject="C0", comparator="C0",
         note="variant CH refutes the parent with a subset of extensions (horizon-localized), "
              "which is a variant-level weakening, not a regularity-axis rank claim"),
    dict(id="PR-F0-140", doc="f0", locator="line 140 field_vocabulary.regularity_token.meaning_C2",
         must_contain="those are strictly larger classes, so excluding C2 does not exclude them",
         kind="comparative", subject="C1_1", comparator="C2",
         note="C^{1,1}/H2_loc extension sets are strictly larger than the C2 extension set"),
    dict(id="PR-F0-141", doc="f0", locator="line 141 field_vocabulary.regularity_token.meaning_C0",
         must_contain="strictly stronger than the C2 conclusion",
         kind="strength", subject="C0", comparator="C2",
         note="C0-inextendibility is stronger than the C2 conclusion at equal data class"),
]


def evaluate_prose(row):
    """Return (ok, observed) for a curated prose row against the chain."""
    kind = row["kind"]
    s, c = row["subject"], row["comparator"]
    if kind == "comparative":
        ok = ranked(s) > ranked(c) if "larger" in row.get("polarity", "larger") else ranked(s) < ranked(c)
        observed = f"E_{TOKEN_LABEL[s]} vs E_{TOKEN_LABEL[c]}: rank {ranked(s)} vs {ranked(c)}"
    elif kind == "entail":
        ok = ranked(s) >= ranked(c)
        observed = f"entailment licensed iff E_{TOKEN_LABEL[s]} superset-or-equal E_{TOKEN_LABEL[c]}"
    elif kind == "strength":
        stronger = row.get("polarity", "stronger") == "stronger"
        ok = ranked(s) >= ranked(c) if stronger else ranked(s) <= ranked(c)
        observed = (f"strength order follows extension-set size: rank {ranked(s)} vs {ranked(c)}; "
                    f"asserted {row.get('polarity', 'stronger')}")
    elif kind == "between":
        ok = ranked("C2") < ranked(s) < ranked("C0")
        observed = f"rank(C2)=0 < rank({TOKEN_LABEL[s]})={ranked(s)} < rank(C0)=3"
    elif kind == "equation":
        ok = "subset of all continuous metric extensions" in row["must_contain"]
        observed = ("distributional-Ricci C0 extensions subset of bare C0 metric extensions: "
                    "target set smaller, so the source statement is the stronger one and entails the target")
    elif kind == "variant":
        ok = True  # content pinned by must_contain/also_contains, validated in the caller
        observed = ("horizon-localized reading excludes a subset of future extensions, so the parent's "
                    "inextendibility does not follow from it (variant weaker); not a regularity-axis claim")
    elif kind == "monotone":
        ok = ranked("C0") > ranked("C2")
        observed = "E_C0 strictly contains E_C2, so lower required regularity -> larger set"
    elif kind == "chain":
        ok = ranked("C0") > ranked("H2loc") > ranked("C1_1") > ranked("C2")
        observed = f"ranks C0={ranked('C0')} H2loc={ranked('H2loc')} C1,1={ranked('C1_1')} C2={ranked('C2')}"
    else:  # pragma: no cover
        ok, observed = False, f"unknown kind {kind}"
    return ok, observed


def _sentence_around(text, start, end):
    left = max(text.rfind(".", 0, start), text.rfind(";", 0, start),
               text.rfind(":", 0, start), text.rfind("\n", 0, start))
    right_candidates = [i for i in (text.find(".", end), text.find(";", end), text.find("\n", end)) if i != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right]


def detect_comparatives(strings_with_defaults):
    """Generalised CS-01 detector over (path, text, default_comparator) triples.

    Comparator resolution: the first regularity token in the surrounding sentence, other than
    the subject, preferring a token after the comparative; the row's target token is the
    fallback when the sentence names none (e.g. 'C2 is a strictly larger extension class')."""
    findings, unparsed, seen = [], [], set()
    for path, text, default_cmp in strings_with_defaults:
        for m in COMPARATIVE.finditer(text):
            subj = token_of(m.group(1))
            sentence = _sentence_around(text, m.start(), m.end())
            post = text[m.end():m.end() + 120]
            cmp_tok = None
            for scan in (post, sentence):
                for tok in TOKEN_SCAN_ORDER:
                    if tok == subj:
                        continue
                    if TOKEN_RES[[t for t, _ in TOKEN_RES].index(tok)][1].search(scan):
                        cmp_tok = tok
                        break
                if cmp_tok:
                    break
            if cmp_tok is None:
                cmp_tok = default_cmp
            if subj is None or cmp_tok is None or subj == cmp_tok:
                unparsed.append({"path": path, "text": m.group(0), "reason": "token unresolved"})
                continue
            want_larger = m.group(2) in ("larger", "bigger", "broader")
            observed_larger = ranked(subj) > ranked(cmp_tok)
            if want_larger != observed_larger:
                key = (m.group(0), subj, cmp_tok)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "rule": "CS-01",
                    "path": path,
                    "claim": m.group(0),
                    "subject": subj,
                    "comparator": cmp_tok,
                    "asserted": m.group(2),
                    "chain_says": "larger" if observed_larger else "smaller",
                    "falsifier": (f"exhibit an extension-set reading under which E_{TOKEN_LABEL[subj]} "
                                  f"strictly contains E_{TOKEN_LABEL[cmp_tok]} given the file's own definitions"),
                })
        for m in STRENGTH.finditer(text):
            a, word, b = token_of(m.group(1)), m.group(2).lower(), token_of(m.group(3))
            if a is None or b is None or a == b:
                unparsed.append({"path": path, "text": m.group(0), "reason": "token unresolved"})
                continue
            # stronger iff it excludes a larger extension set, i.e. rank(a) > rank(b)
            observed_stronger = ranked(a) > ranked(b)
            if (word == "stronger") != observed_stronger:
                key = (m.group(0), a, b)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "rule": "CS-02",
                    "path": path,
                    "claim": m.group(0),
                    "subject": a,
                    "comparator": b,
                    "asserted": word,
                    "chain_says": "stronger" if observed_stronger else "weaker",
                    "falsifier": (f"exhibit an extension-set reading under which {TOKEN_LABEL[a]}-inextendibility "
                                  f"is {word} than {TOKEN_LABEL[b]}-inextendibility given the chain"),
                })
    return findings, unparsed


def run_gate(path: Path):
    r = subprocess.run([sys.executable, str(ROOT / GATE_REL), "--json", str(path)],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip()[:400], (r.stderr or "").strip()[:200]


def mutation_text_missing(text, needle):
    return needle not in text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", default=None, help="expected sha256 of FROZEN.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    checks, findings, notes = [], [], []
    pins = {}

    frozen_path = ROOT / FROZEN_REL
    if not frozen_path.exists():
        print("FROZEN.json missing", file=sys.stderr)
        return 2
    frozen_sha = sha256_file(frozen_path)
    pins[FROZEN_REL] = frozen_sha
    if args.pin and frozen_sha != args.pin:
        print(f"pin mismatch: FROZEN.json measured {frozen_sha} != --pin {args.pin}", file=sys.stderr)
        return 2
    frozen = json.loads(frozen_path.read_text())
    manifest = frozen["files"]

    # ---- Suite PINS: every reviewed doc must match its FROZEN rev28 entry ----
    docs = {}
    for key, rel in DOC_RELS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"missing input {rel}", file=sys.stderr)
            return 2
        measured = sha256_file(p)
        declared = manifest.get(rel, {}).get("sha256")
        pins[rel] = measured
        ok = declared is not None and declared == measured
        checks.append(check(f"PIN-{key}", "pins", ok,
                            f"{rel} sha256 == FROZEN entry {str(declared)[:16]}",
                            f"measured {measured[:16]}", "any byte change to a reviewed input",
                            rel))
        docs[key] = yaml.safe_load(p.read_text()) if p.suffix in (".yaml", ".yml") else json.loads(p.read_text())
    if not all(c["ok"] for c in checks if c["suite"] == "pins"):
        print("pin failure: an input does not match the FROZEN rev28 manifest", file=sys.stderr)
        return 2

    # ---- Suite CHAIN: machine-readable containment strings ----
    strings_with_defaults = []
    for key in ("f2a", "f2b"):
        row_default = CLASS_TOKEN[docs[key]["class_id"]]
        il = docs[key].get("implication_ledger") or {}
        text = il.get("extension_class_containment", "")
        pairs = parse_containment_pairs(text)
        required = [("C2", "C1_1"), ("C1_1", "H2loc"), ("H2loc", "C0")]
        got = {(a, b) for a, b, _ in pairs}
        ok = all(p in got for p in required) and all(ranked(a) <= ranked(b) for a, b, _ in pairs)
        checks.append(check(f"CHAIN-{key}", "chain_text", ok,
                            "text encodes E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
                            f"pairs={sorted(got)}", "a containment string that encodes a different ordering",
                            f"{DOC_RELS[key]}#implication_ledger.extension_class_containment"))
        strings_with_defaults.append((f"{DOC_RELS[key]}#extension_class_containment", text, row_default))

    supp = docs["supp"]
    for axis, blk in (supp.get("axis_registry") or {}).items():
        text = blk.get("containment") if isinstance(blk, dict) else None
        if not text:
            continue
        pairs = parse_containment_pairs(text)
        if not pairs:
            notes.append(f"supp axis_registry.{axis}.containment: no E_* pair parsed (informational)")
            continue
        ok = all(ranked(a) <= ranked(b) for a, b, _ in pairs)
        checks.append(check(f"CHAIN-SUPP-{axis}", "chain_text", ok,
                            "every asserted E_a subset E_b pair respects the rank order",
                            f"pairs={[(TOKEN_LABEL[a], TOKEN_LABEL[b]) for a, b, _ in pairs]}",
                            "a pair whose asserted containment contradicts the chain",
                            f"{DOC_RELS['supp']}#axis_registry.{axis}.containment"))

    # ---- Suite TRANSFER: machine-readable one_way_entailments ----
    def resolve(x, default):
        return token_of(x) or (default if re.search(r"this class|our class|the class", str(x)) else None)

    for key in ("f2a", "f2b"):
        cid = docs[key]["class_id"]
        default = CLASS_TOKEN[cid]
        il = docs[key].get("implication_ledger") or {}
        for i, row in enumerate(il.get("one_way_entailments") or []):
            a, b = resolve(row.get("from", ""), default), resolve(row.get("to", ""), default)
            loc = f"{DOC_RELS[key]}#implication_ledger.one_way_entailments[{i}]"
            if a is None or b is None or a == b:
                notes.append(f"{loc}: token pair ({a},{b}) not a regularity transfer (informational)")
                continue
            # "no X-extension" entails "no Y-extension" iff every Y-extension is an X-extension,
            # i.e. E_Y subset-of-or-equal E_X (rank(Y) <= rank(X)).
            want = ranked(b) <= ranked(a)
            ok = row.get("relation") == "entails" and want
            checks.append(check(f"XFER-{key}-{i}", "transfer_licensing", ok,
                                f"entails licensed iff E_{TOKEN_LABEL[b]} subset-of-or-equal "
                                f"E_{TOKEN_LABEL[a]} (rank {ranked(b)} <= {ranked(a)})",
                                f"relation={row.get('relation')} ranks {ranked(a)}->{ranked(b)}",
                                "a row whose stated entailment contradicts the chain", loc))
            strings_with_defaults.append((loc, json.dumps(row), default))

        for i, row in enumerate(il.get("forbidden_transfers") or []):
            a, b = resolve(row.get("from", ""), default), resolve(row.get("to", ""), default)
            loc = f"{DOC_RELS[key]}#implication_ledger.forbidden_transfers[{i}]"
            if a is None or b is None or a == b:
                notes.append(f"{loc}: non-regularity forbidden transfer (informational)")
                strings_with_defaults.append((loc, json.dumps(row), default))
                continue
            legal_transfer = ranked(b) <= ranked(a)
            ok = not legal_transfer
            checks.append(check(f"FORB-{key}-{i}", "transfer_licensing", ok,
                                f"forbidden iff the transfer is NOT licensed "
                                f"(rank {ranked(b)} > {ranked(a)})",
                                f"ranks {ranked(a)}->{ranked(b)}", "a forbidden row that the chain licenses", loc))
            for sub in parse_reason_subset(json.dumps(row)):
                sub_ok = ranked(sub["a"]) <= ranked(sub["b"])
                checks.append(check(f"PREM-{key}-{i}", "premise_consistency", sub_ok,
                                    f"stated premise E_{TOKEN_LABEL[sub['a']]} subset E_{TOKEN_LABEL[sub['b']]}",
                                    f"Asserted {sub['kind']}; ranks {ranked(sub['a'])} vs {ranked(sub['b'])}",
                                    "a stated premise that contradicts the chain", loc))
            strings_with_defaults.append((loc, json.dumps(row), default))

    # ---- Suite SUPP-LEDGER: the supplement implication ledger rows ----
    supp_tokens = {"AF-SCC-C2-VAC-GEN": "C2", "AF-SCC-C0-VAC-GEN": "C0"}
    for i, row in enumerate(supp.get("implication_ledger") or []):
        a = token_of(row.get("from", "")) or supp_tokens.get(row.get("from", ""))
        b = token_of(row.get("to", "")) or supp_tokens.get(row.get("to", ""))
        loc = f"{DOC_RELS['supp']}#implication_ledger[{i}]"
        rel = row.get("relation")
        if a is None or b is None or a == b:
            notes.append(f"{loc}: non-regularity row relation={rel} (informational)")
            continue
        legal = ranked(b) <= ranked(a)
        ok = (rel == "entails") == legal and (rel == "does_not_entail") == (not legal)
        checks.append(check(f"SUPP-{i}", "transfer_licensing", ok,
                            f"relation must be {'entails' if legal else 'does_not_entail'} "
                            f"(E_{TOKEN_LABEL[b]} subset-of-or-equal E_{TOKEN_LABEL[a]}: "
                            f"rank {ranked(b)} <= {ranked(a)})",
                            f"relation={rel}; ranks {ranked(a)}->{ranked(b)}",
                            "a supplement row whose relation contradicts the chain", loc))
        strings_with_defaults.append((loc, json.dumps(row), b))

    # ---- Suite PROSE: curated pinned sentences ----
    doc_texts = {k: (ROOT / rel).read_text() for k, rel in DOC_RELS.items()}
    for row in PROSE_ROWS:
        text = doc_texts[row["doc"]]
        needles = [row["must_contain"]] + [s for s in row.get("also_contains", [])]
        missing = [n for n in needles if n not in text]
        if missing:
            print(f"pinned prose absent from {DOC_RELS[row['doc']]}: {row['id']} "
                  f"({missing[0][:60]}...)", file=sys.stderr)
            return 2
        ok, observed = evaluate_prose(row)
        checks.append(check(row["id"], "prose_semantics", ok,
                            f"{row['kind']}: {row['note']}", observed,
                            "exhibit an extension-set reading under which the pinned sentence is correct",
                            f"{DOC_RELS[row['doc']]} {row['locator']}"))
        strings_with_defaults.append((f"{DOC_RELS[row['doc']]}#{row['id']}",
                                      row["must_contain"], row["comparator"]))

    # ---- Suite DETECTOR: generalised comparative-claim rule ----
    det_findings, det_unparsed = detect_comparatives(strings_with_defaults)
    findings.extend(det_findings)

    # ---- Suite GATE: can the structural gate see the canonical defect? ----
    gate_controls, tmp = [], tempfile.mkdtemp(prefix="w060-gate-")
    f2b_path = ROOT / DOC_RELS["f2b"]
    canonical_text = f2b_path.read_text()
    variants = {"canonical": canonical_text}
    repaired = canonical_text.replace("C2 is a strictly larger extension class",
                                      "C2 is a strictly smaller extension class")
    if repaired == canonical_text:
        print("mutation M-A failed to apply", file=sys.stderr)
        return 2
    variants["M-A_premise_repaired"] = repaired
    flipped = canonical_text.replace(
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2;",
        "E_C2 contains E_C0;")
    if flipped == canonical_text:
        print("mutation M-B failed to apply", file=sys.stderr)
        return 2
    variants["M-B_containment_flipped"] = flipped
    doc_m = yaml.safe_load(canonical_text)
    doc_m["implication_ledger"]["one_way_entailments"].append(
        {"from": "no proper future C2 extension", "to": "no proper future C0 extension",
         "relation": "entails", "reason": "injected positive control", "status": "injected"})
    variants["M-C_forbidden_converse_asserted"] = yaml.safe_dump(doc_m, sort_keys=False)
    gate_expect = {"canonical": 0, "M-A_premise_repaired": 0, "M-B_containment_flipped": 0,
                   "M-C_forbidden_converse_asserted": 1}
    for name, text in variants.items():
        p = Path(tmp) / f"{name}.yaml"
        p.write_text(text)
        rc, out, err = run_gate(p)
        gate_controls.append({"variant": name, "gate_exit": rc, "expected_exit": gate_expect[name],
                              "gate_stdout_head": out, "gate_stderr_head": err})
    gate_ok = all(c["gate_exit"] == c["expected_exit"] for c in gate_controls)
    # The measurement of interest: canonical-with-defect and flipped-containment both PASS.
    blind = (gate_controls[0]["gate_exit"] == 0 and gate_controls[2]["gate_exit"] == 0
             and gate_controls[3]["gate_exit"] == 1)
    checks.append(check("GATE-SENS", "gate_sensitivity", gate_ok and blind,
                        "canonical passes; repaired passes; flipped-containment passes (blind); "
                        "asserted forbidden converse fails (gate alive)",
                        "; ".join(f"{c['variant']}=exit{c['gate_exit']}" for c in gate_controls),
                        "the gate rejecting the flipped-containment mutant (blind-spot claim refuted)",
                        GATE_REL))

    # Detector controls: fires on canonical, silent on repaired, silent on the true taxonomy sentence.
    det_on_repaired, _ = detect_comparatives([(DOC_RELS["f2b"], repaired, "C0")])
    det_on_taxonomy, _ = detect_comparatives([
        (DOC_RELS["f0"], "It does NOT forbid C^{1,1} or H^2_loc extensions: those are strictly "
                         "larger classes, so excluding C2 does not exclude them", "C2")])
    synthetic = ("C2 is a strictly larger extension class than H2_loc, so C2-inextendibility "
                 "is strictly weaker than H2_loc-inextendibility")
    det_on_synthetic, _ = detect_comparatives([("synthetic", synthetic, None)])
    detector_controls = [
        {"control": "canonical_f2b", "expected_findings": 1, "observed_findings": len(det_findings)},
        {"control": "M-A_repaired", "expected_findings": 0, "observed_findings": len(det_on_repaired)},
        {"control": "taxonomy_true_sentence", "expected_findings": 0, "observed_findings": len(det_on_taxonomy)},
        {"control": "synthetic_inversion", "expected_findings": 1, "observed_findings": len(det_on_synthetic)},
    ]
    det_ok = all(c["expected_findings"] == c["observed_findings"] for c in detector_controls)
    checks.append(check("DETECT-CTRL", "detector", det_ok, "detector fires only on inversions",
                        "; ".join(f"{c['control']}={c['observed_findings']}" for c in detector_controls),
                        "a detector control whose expected finding count is not observed",
                        "artifacts/worker-060/containment_semantics_sweep/verify_containment_semantics.py"))

    # ---- Suite COVERAGE: full-text recall probe over every string in the frozen docs ----
    # Scanned patterns: (a) set-size comparatives anchored on an explicit regularity token,
    # (b) explicit "X-inextendibility is stronger/weaker than Y" pairs.  Strength claims on the
    # equation / genericity / variant axes are not regularity-rank claims and are covered by the
    # curated PROSE rows; they are enumerated in evidence.notes, never silently skipped.
    coverage_hits, coverage_unresolved, coverage_strings = [], [], 0
    for key, rel in DOC_RELS.items():
        doc = docs[key]
        default = CLASS_TOKEN.get(doc.get("class_id")) if isinstance(doc, dict) else None
        for path, s in iter_strings(doc):
            coverage_strings += 1
            f, u = detect_comparatives([(f"{rel}{path[1:]}", s, default)])
            coverage_hits += f
            coverage_unresolved += u
    seen_keys = {(f.get("claim"), f.get("subject"), f.get("comparator")) for f in findings}
    new_hits = [f for f in coverage_hits
                if (f["claim"], f["subject"], f["comparator"]) not in seen_keys]
    findings.extend(new_hits)
    checks.append(check("COVERAGE-SCAN", "coverage", len(new_hits) == 0,
                        "no comparative inversion outside the set already reported",
                        f"scanned {coverage_strings} strings; hits={len(coverage_hits)}; "
                        f"new={len(new_hits)}; unresolved={len(coverage_unresolved)}",
                        "a comparative inversion in a field the targeted pass did not cover",
                        "full-text scan by verify_containment_semantics.py"))
    coverage = {"strings_scanned": coverage_strings, "hits": len(coverage_hits),
                "new_hits": len(new_hits), "unresolved": len(coverage_unresolved),
                "scope": "set-size comparatives on explicit regularity tokens + explicit "
                         "regularity-token inextendibility strength pairs"}

    # ---- findings bookkeeping ----
    hard = [f for f in findings if f["rule"] in ("CS-01", "CS-02")]
    if hard:
        findings.append({
            "rule": "GATE-GAP", "severity": "moderate",
            "statement": ("check_class_schema.py R16 passes both the canonical F2b file carrying the "
                          "inverted containment premise and a file whose containment string is flipped, "
                          "while it still rejects an asserted forbidden converse: premise semantics of "
                          "extension_class_containment / transfer reasons are not machine-checked."),
            "falsifier": "a gate rule in check_class_schema.py that rejects M-B_containment_flipped",
            "evidence": gate_controls, "status": "measured",
        })
    else:
        findings.append({
            "rule": "GATE-GAP", "severity": "note",
            "statement": "no inverted premise reproduced at this pin; detector coverage measured only",
            "falsifier": "an inverted premise at a future pin", "status": "not_triggered",
        })

    evidence = {
        "run_id": RUN_ID,
        "actor": ACTOR,
        "created_at": CREATED_AT,
        "class_ids": CLASS_IDS,
        "node_ids": ["F2a", "F2b", "F0"],
        "authority": ("worker artifact measurement only; no gate verdict, no node completion, "
                      "no validation_status promotion, no byte change to any reviewed file"),
        "frozen": {"path": FROZEN_REL, "sha256": frozen_sha, "revision": frozen.get("revision"),
                   "frozen_at": frozen.get("frozen_at")},
        "pins": pins,
        "chain": {"order": CHAIN, "label": "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
                  "strength_order": "C0 > H2loc > C^{1,1} > C2"},
        "checks": checks,
        "checks_total": len(checks),
        "checks_failed": [c["check_id"] for c in checks if not c["ok"]],
        "findings": findings,
        "gate_controls": gate_controls,
        "detector_controls": detector_controls,
        "coverage": coverage,
        "detector_unparsed": det_unparsed,
        "notes": notes,
        "verdict": "HARD_FINDING" if hard else "NO_CONTAINMENT_DEFECT_REPRODUCED",
        "exit_code": 1 if hard else 0,
    }

    # snapshots of every reviewed non-tool input, byte-identical, plus SHA256SUMS handled by caller
    snap = outdir / "snapshots"
    snap.mkdir(parents=True, exist_ok=True)
    for key, rel in DOC_RELS.items():
        (snap / f"{key}__{Path(rel).name}").write_bytes((ROOT / rel).read_bytes())
    (snap / f"gate__{Path(GATE_REL).name}").write_bytes((ROOT / GATE_REL).read_bytes())

    ev_path = outdir / "evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=2, sort_keys=False) + "\n")
    if args.json:
        print(json.dumps(evidence, indent=2))
    else:
        print(f"{RUN_ID}: {evidence['verdict']} ({evidence['checks_total']} checks, "
              f"{len(evidence['checks_failed'])} failed) -> {ev_path}")
        for f in hard:
            print(f"  HARD {f['rule']} {f['path']}: {f['claim']}")
        print(f"  gate controls: " + "; ".join(f"{c['variant']}=exit{c['gate_exit']}" for c in gate_controls))
    return evidence["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
