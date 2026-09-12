#!/usr/bin/env python3
"""W008-CONTAINMENT-DIRECTION-01: independent containment-direction audit.

Class scope: AF-SCC-C0-VAC-GEN (F2b) and AF-SCC-C2-VAC-GEN (F2a), with the
F0 canonical taxonomy, the F0 class-contract supplement, and F1 as
cross-artifact controls.

Oracle.  All pinned documents declare the same nested extension sets
    E_C2  subset of  E_{C^1,1}  subset of  E_H2loc  subset of  E_C0
so the inexistence statement strength runs the other way:
    S_X := "no proper future X extension"
    S_X entails S_Y   iff  E_X superset of E_Y   iff  rank(X) >= rank(Y)
with rank(C2)=0 < rank(C^1,1)=1 < rank(H2loc)=2 < rank(C0)=3.

Checks (read-only, deterministic, no network):
  CD-01  class-size prose claim ("X is a strictly larger/smaller extension
         class") disagrees with the rank oracle at the owning document's class.
  CD-02  a "no containment ... asserted" denial in a document that itself
         declares >= 2 containment chain edges.
  CD-03  a declared chain edge E_a subset of E_b with rank(a) >= rank(b).
  CD-04  an entailment row S_from -> S_to whose direction violates the oracle.
  CD-05  a forbidden-transfer row whose direction is licensed by the oracle
         (i.e. the transfer is wrongly forbidden).
  CD-06  cross-document chain contradiction (two pinned documents induce
         opposite orders on a shared token pair).

Controls: --selftest runs a 9-case in-memory battery (identity, repair,
single-defect reverts, mutation sensitivity, chain violation, denial
false-positive guard, fabricated-token robustness, empty-document
robustness).  Exit codes: 0 completed with verdict, 2 selftest failure,
3 fail-closed (missing/moved/unparsable input, pin mismatch).

This instrument never writes to the repository, never runs a canonical
tool, and never edits a canonical artifact.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Canonical oracle -----------------------------------------------------------
RANK = {"C2": 0, "C^1,1": 1, "H2loc": 2, "C0": 3}
TOKEN_ALIASES = {
    "C2": "C2",
    "C^1,1": "C^1,1",
    "C^{1,1}": "C^1,1",
    "C1,1": "C^1,1",
    "C1_1": "C^1,1",
    "C^{1,1}": "C^1,1",
    "H2loc": "H2loc",
    "H2_loc": "H2loc",
    "H^2_loc": "H2loc",
    "H^2_{loc}": "H2loc",
    "C0": "C0",
}
ORDER_TEXT = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"

TOKEN_RE = re.compile(r"E_\{([^}]+)\}|E_([A-Za-z0-9^_]+)")
ENTAIL_PROSE_RE = re.compile(
    r"(?=(?P<a>C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)\s*-\s*inextendibility"
    r"\s+entails\s+"
    r"(?P<b>C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)\s*-\s*inextendibility)",
    re.IGNORECASE,
)
STRONGER_RE = re.compile(
    r"strictly\s+(stronger|weaker)\s+than\s+(?:the\s+)?"
    r"(C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)\b",
    re.IGNORECASE,
)
CLASS_SIZE_RE = re.compile(
    r"\b(C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)\b"
    r"\s+is\s+(?:a\s+)?strictly\s+(larger|smaller)\s+extension\s+class",
    re.IGNORECASE,
)
DENIAL_RE = re.compile(r"no\s+containment", re.IGNORECASE)
FUTURE_RE = re.compile(
    r"no\s+proper\s+future\s+(C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)"
    r"(?:\s+[\w-]+)*?\s+extension",
    re.IGNORECASE,
)


def norm_token(raw: str):
    if raw is None:
        return None
    return TOKEN_ALIASES.get(raw.strip())


def _tok(match):
    return norm_token(match.group(1) or match.group(2))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(node, path=""):
    if isinstance(node, dict):
        for key, val in node.items():
            child = f"{path}.{key}" if path else str(key)
            yield from walk(val, child)
    elif isinstance(node, list):
        for idx, val in enumerate(node):
            yield from walk(val, f"{path}[{idx}]")
    else:
        yield path, node


def chain_edges(text: str):
    """Return [(smaller_token, larger_token)] declared by containment prose."""
    edges = []
    found = list(TOKEN_RE.finditer(text))
    for first, second in zip(found, found[1:]):
        between = text[first.end():second.start()].lower()
        a, b = _tok(first), _tok(second)
        if a is None or b is None:
            continue
        if "subset of" in between:
            edges.append((a, b, "subset"))
        elif "contains" in between:
            edges.append((b, a, "contains"))
    return edges


def denial_asserted(text: str):
    """Return the sentence fragment that *asserts* no containment, or None.

    Guards against the CF-16 metalinguistic-mention false positive: quoted
    historical corrections such as "[... the earlier 'no containment with C2
    is asserted' was wrong]" are not current assertions.
    """
    if not isinstance(text, str):
        return None
    for frag in re.split(r"(?<=[.;])\s+", text):
        if not DENIAL_RE.search(frag):
            continue
        if not re.search(r"\b(is|are)\s+asserted\s+here\b", frag, re.I):
            continue
        if re.search(r"\b(earlier|was wrong|corrected|correction|superseded|"
                     r"previous revision|revision had)\b", frag, re.I):
            continue
        if re.search(r"['\u2018\u2019\"]\s*no\s+containment", frag, re.I):
            continue
        return frag.strip()
    return None


def resolve_reference(tok, own, text):
    """Resolve the class a size claim is compared against."""
    tail = text
    match = re.search(
        r"\bthan\s+(C2|C\^?\{?1,1\}?|C1,1|H2_?loc|H\^2_loc|C0)\b", tail, re.I)
    if match:
        return norm_token(match.group(1))
    for a, b, _rel in chain_edges(text):
        if a == tok:
            return b
        if b == tok:
            return a
    if tok != own:
        return own
    return None


def parse_future(sentence: str, own_class: str):
    own = re.sub(r"^no\s+proper\s+future\s+", "", sentence.strip(), flags=re.I)
    if own.lower().startswith("this class"):
        return own_class
    match = FUTURE_RE.search(sentence)
    if match:
        return norm_token(match.group(1))
    match = re.match(r"\s*no\s+proper\s+future\s+([A-Za-z0-9^_{},]+)", sentence, re.I)
    if match:
        return norm_token(match.group(1))
    return None


class Audit:
    def __init__(self, docs):
        # docs: list of dicts {path, sha256, data, text, label, class_token}
        self.docs = docs
        self.findings = []
        self.chains = {}
        self.info = []

    def add(self, fid, severity, label, yaml_path, text, rule, oracle=None,
            observed=None, line=None):
        self.findings.append({
            "id": fid,
            "severity": severity,
            "doc": label,
            "yaml_path": yaml_path,
            "line_hint": line,
            "text": text if len(text) <= 400 else text[:397] + "...",
            "rule": rule,
            "oracle": oracle,
            "observed": observed,
        })

    def audit(self):
        induced = {}
        for doc in self.docs:
            label, own = doc["label"], doc.get("class_token")
            # pass 1: collect every chain edge in the document first, so the
            # denial check (CD-02) can be evaluated against the full chain
            edges = []
            for ypath, val in walk(doc["data"]):
                if not isinstance(val, str):
                    continue
                for a, b, _rel in chain_edges(val):
                    edges.append((a, b, ypath))
                    if RANK[a] >= RANK[b]:
                        self.add("CD-03", "blocking-for-clean-accept", label, ypath,
                                 val, "chain edge E_%s subset of E_%s violates the "
                                 "rank oracle" % (a, b),
                                 oracle=ORDER_TEXT,
                                 observed="rank(%s)=%d >= rank(%s)=%d" % (a, RANK[a], b, RANK[b]),
                                 line=self.line_of(doc, val))
            # pass 2: prose checks against the complete chain
            for ypath, val in walk(doc["data"]):
                if not isinstance(val, str):
                    continue
                for match in CLASS_SIZE_RE.finditer(val):
                    tok = norm_token(match.group(1))
                    direction = match.group(2).lower()
                    if tok is None:
                        continue
                    ref = resolve_reference(tok, own, val)
                    if ref is None or ref == tok:
                        continue
                    larger = RANK[tok] > RANK[ref]
                    if (direction == "larger") != larger:
                        self.add("CD-01", "blocking-for-clean-accept", label, ypath,
                                 val, "class-size claim disagrees with the canonical "
                                 "chain at the comparison class",
                                 oracle="%s; %s is strictly %s than %s" % (
                                     ORDER_TEXT, tok, "larger" if larger else "smaller", ref),
                                 observed="asserts %s strictly %s than %s" % (tok, direction, ref),
                                 line=self.line_of(doc, val))
                # CD-07 entailment prose: S_a entails S_b requires rank(a) >= rank(b)
                for em in ENTAIL_PROSE_RE.finditer(val):
                    a, b = norm_token(em.group("a")), norm_token(em.group("b"))
                    if a is None or b is None or a == b:
                        continue
                    if not (RANK[a] >= RANK[b]):
                        self.add("CD-07", "major", label, ypath, val,
                                 "inextendibility entailment prose violates the oracle",
                                 oracle="S_%s entails S_%s iff rank(%s) >= rank(%s)" % (
                                     a, b, a, b),
                                 observed="asserts S_%s entails S_%s; rank %d < %d" % (
                                     a, b, RANK[a], RANK[b]),
                                 line=self.line_of(doc, val))
                # CD-08 comparison prose: "strictly stronger/weaker than <token>"
                for sm in STRONGER_RE.finditer(val):
                    direction = sm.group(1).lower()
                    comp = norm_token(sm.group(2))
                    before = val[:sm.start()]
                    subjects = [norm_token(t.group(1) or t.group(2))
                                if (t.group(1) or t.group(2)) in TOKEN_ALIASES
                                else norm_token(t.group(1) or t.group(2))
                                for t in TOKEN_RE.finditer(before)]
                    subjects += [norm_token(w.group(1))
                                 for w in re.finditer(
                                     r"\b(C0|C2|H2_?loc|C1,1|C\^\{1,1\})\b", before, re.I)]
                    subj = next((t for t in reversed(subjects) if t), None) or own
                    if subj is None or comp is None or subj == comp:
                        continue
                    want_stronger = RANK[subj] >= RANK[comp]
                    if (direction == "stronger") != want_stronger:
                        self.add("CD-08", "major", label, ypath, val,
                                 "comparison prose disagrees with the oracle",
                                 oracle="%s is strictly %s than %s" % (
                                     subj, "stronger" if want_stronger else "weaker", comp),
                                 observed="asserts %s strictly %s than %s" % (
                                     subj, direction, comp),
                                 line=self.line_of(doc, val))
                denial = denial_asserted(val)
                if denial and len(edges) >= 2 and (
                        "must_not_conflate" in ypath or "conflate" in ypath):
                    self.add("CD-02", "major", label, ypath, val,
                             "containment denial in a document that declares a "
                             "containment chain",
                             oracle="same document declares %d chain edge(s)" % len(edges),
                             observed="asserts: %s" % denial,
                             line=self.line_of(doc, val))
            induced[label] = edges
            # CD-04 / CD-05 structured ledger rows
            ledger = doc["data"].get("implication_ledger") or {}
            if not isinstance(ledger, dict):
                self.info.append({"doc": label, "row": "implication_ledger",
                                  "note": "not a mapping; structured rows skipped"})
                ledger = {}
            for idx, row in enumerate(ledger.get("one_way_entailments") or []):
                if not isinstance(row, dict):
                    continue
                src = parse_future(str(row.get("from", "")), own)
                dst = parse_future(str(row.get("to", "")), own)
                if src is None or dst is None:
                    self.info.append({"doc": label, "row": "one_way_entailments[%d]" % idx,
                                      "note": "unparsable endpoint; skipped"})
                    continue
                if not (RANK[src] >= RANK[dst]):
                    self.add("CD-04", "major", label,
                             "implication_ledger.one_way_entailments[%d]" % idx,
                             json.dumps(row, ensure_ascii=False),
                             "entailment row whose strength direction violates the oracle",
                             oracle="S_%s entails S_%s iff rank(%s) >= rank(%s)" % (
                                 src, dst, src, dst),
                             observed="rank(%s)=%d < rank(%s)=%d" % (
                                 src, RANK[src], dst, RANK[dst]),
                             line=self.line_of(doc, str(row.get("from", ""))))
            for idx, row in enumerate(ledger.get("forbidden_transfers") or []):
                if not isinstance(row, dict):
                    continue
                src = parse_future(str(row.get("from", "")), own)
                dst = parse_future(str(row.get("to", "")), own)
                if src is None or dst is None:
                    self.info.append({"doc": label, "row": "forbidden_transfers[%d]" % idx,
                                      "note": "non-regularity endpoint (e.g. WCC class); skipped"})
                    continue
                if RANK[src] >= RANK[dst]:
                    self.add("CD-05", "major", label,
                             "implication_ledger.forbidden_transfers[%d]" % idx,
                             json.dumps(row, ensure_ascii=False),
                             "forbidden transfer that the oracle licenses",
                             oracle="forbidden needs rank(%s) < rank(%s)" % (src, dst),
                             observed="rank(%s)=%d >= rank(%s)=%d" % (
                                 src, RANK[src], dst, RANK[dst]),
                             line=self.line_of(doc, str(row.get("reason", ""))))
        self.chains = induced
        # CD-06 cross-document chain contradiction
        for i, a in enumerate(self.docs):
            for b in self.docs[i + 1:]:
                ea, eb = induced[a["label"]], induced[b["label"]]
                for (x, y, yp) in ea:
                    for (u, v, _) in eb:
                        if (x, y) == (v, u):
                            self.add("CD-06", "blocking-for-clean-accept", a["label"],
                                     yp, ORDER_TEXT,
                                     "cross-document chain contradiction with %s" % b["label"],
                                     oracle=ORDER_TEXT,
                                     observed="%s says E_%s subset E_%s; %s says the reverse"
                                              % (a["label"], x, y, b["label"]),
                                     line=self.line_of(a, ORDER_TEXT))
        return self.findings

    @staticmethod
    def line_of(doc, needle):
        if not needle:
            return None
        frag = needle.strip().splitlines()[0][:80]
        for num, line in enumerate(doc["text"].splitlines(), 1):
            if frag and frag in line:
                return num
        return None

    def summary(self):
        by_id = {}
        for f in self.findings:
            by_id.setdefault(f["id"], 0)
            by_id[f["id"]] += 1
        return {
            "documents": [{"label": d["label"], "path": d["path"], "sha256": d["sha256"]}
                          for d in self.docs],
            "chain_edges": {k: sorted({(a, b) for a, b, _ in v})
                            for k, v in self.chains.items()},
            "finding_counts": by_id,
            "findings": self.findings,
            "skipped_rows": self.info,
        }


PINNED_LABELS = {
    "af_scc_c0_vacuum.yaml":
        ("F2b/AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml", "C0"),
    "af_scc_c2_vacuum.yaml":
        ("F2a/AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml", "C2"),
    "af_wcc_vacuum.yaml":
        ("F1/AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml", None),
    "formulation_taxonomy.canonical.yaml":
        ("F0-canonical", "research_map/formulation_taxonomy.yaml", None),
    "formulation_taxonomy.supplement.yaml":
        ("F0-supplement", "artifacts/formulation/formulation_taxonomy.yaml", None),
}


def load_pinned(pinned_dir: Path):
    docs = []
    manifest = {}
    for key, (label, orig, own) in PINNED_LABELS.items():
        path = pinned_dir / key
        if not path.exists():
            raise SystemExit("fail-closed: missing pinned input %s" % path)
        text = path.read_text()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SystemExit("fail-closed: unparsable %s: %s" % (path, exc))
        if not isinstance(data, dict):
            raise SystemExit("fail-closed: %s is not a mapping" % path)
        digest = sha256_file(path)
        manifest[orig] = digest
        docs.append({"path": orig, "label": label, "sha256": digest,
                     "data": data, "text": text, "class_token": own})
    cand = pinned_dir / "candidate_c0_rev12.yaml"
    if cand.exists():
        text = cand.read_text()
        docs.append({"path": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/"
                             "af_scc_c0_vacuum.yaml",
                     "label": "candidate-C0-rev12", "sha256": sha256_file(cand),
                     "data": yaml.safe_load(text), "text": text, "class_token": "C0"})
        manifest["artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/"
                 "af_scc_c0_vacuum.yaml"] = sha256_file(cand)
    return docs, manifest


def selftest(pinned_dir: Path) -> int:
    docs, _ = load_pinned(pinned_dir)
    base = {d["label"]: copy.deepcopy(d) for d in docs}
    failures = []

    def run(selection, mutate=None):
        use = []
        for label in selection:
            d = copy.deepcopy(base[label])
            if mutate:
                d = mutate(d)
            use.append(d)
        return Audit(use).audit()

    def ids(fs):
        return sorted({f["id"] for f in fs})

    # ctl0 identity: canonical C0 has exactly the two known defect kinds
    got = ids(run(["F2b/AF-SCC-C0-VAC-GEN"]))
    if got != ["CD-01", "CD-02"]:
        failures.append("ctl0 identity C0: expected [CD-01, CD-02], got %s" % got)
    # ctl1 identity: canonical C2 clean
    got = ids(run(["F2a/AF-SCC-C2-VAC-GEN"]))
    if got:
        failures.append("ctl1 identity C2: expected clean, got %s" % got)
    # ctl2 repair candidate (rebased rev12, 2 edits) clean
    got = ids(run(["candidate-C0-rev12"]))
    if got:
        failures.append("ctl2 repair candidate: expected clean, got %s" % got)
    # ctl3 single revert: repair inversion only -> CD-01 remains, denial stays repaired
    def revert_reason(d):
        row = d["data"]["implication_ledger"]["forbidden_transfers"][0]
        row["reason"] = ("C2 is a strictly larger extension class, so "
                         "C2-inextendibility is strictly weaker")
        return d
    got = ids(run(["candidate-C0-rev12"], revert_reason))
    if got != ["CD-01"]:
        failures.append("ctl3 single revert (reason): expected [CD-01], got %s" % got)
    # ctl4 single revert: repair denial only -> CD-02 remains, reason stays repaired
    def revert_denial(d):
        d["data"]["regularity"]["must_not_conflate"][0] = (
            "H2_loc is a distinct regularity-axis value. No containment with C2 or "
            "C0 is asserted here; the informal phrase 'strictly between' is not used.")
        return d
    got = ids(run(["candidate-C0-rev12"], revert_denial))
    if got != ["CD-02"]:
        failures.append("ctl4 single revert (denial): expected [CD-02], got %s" % got)
    # ctl5 mutation sensitivity: inject inverted size claim into C2
    def mutate_c2(d):
        row = d["data"]["implication_ledger"]["forbidden_transfers"][1]
        row["reason"] = ("the converse containment is false; C2 is a strictly larger "
                         "extension class than H2_loc")
        return d
    fs = run(["F2a/AF-SCC-C2-VAC-GEN"], mutate_c2)
    if "CD-01" not in ids(fs):
        failures.append("ctl5 mutation sensitivity: injected inversion not detected")
    # ctl6 chain violation: synthetic reversed chain
    def reverse_chain(d):
        d["data"]["implication_ledger"]["extension_class_containment"] = (
            "E_C0 subset of E_C2")
        return d
    fs = run(["F2a/AF-SCC-C2-VAC-GEN"], reverse_chain)
    if "CD-03" not in ids(fs):
        failures.append("ctl6 chain violation: reversed chain not detected")
    # ctl7 denial false-positive guard: denial with no chain in a minimal doc
    def denial_only(d):
        d["data"] = {"class_id": "AF-SCC-C2-VAC-GEN",
                     "regularity": {"extension_regularity": "C2",
                                    "must_not_conflate": [
                                        "No containment with C2 or C0 is asserted here."]},
                     "implication_ledger": {}}
        d["text"] = ""
        return d
    fs = run(["F2a/AF-SCC-C2-VAC-GEN"], denial_only)
    if "CD-02" in ids(fs):
        failures.append("ctl7 denial false-positive guard: fired without a chain")
    # ctl7b metalinguistic-mention guard: quoted historical denial must not fire
    def mention_only(d):
        d["data"]["regularity"]["must_not_conflate"].append(
            "[R2 major: the earlier 'no containment with C2 is asserted' was wrong]")
        return d
    fs = run(["F2a/AF-SCC-C2-VAC-GEN"], mention_only)
    if "CD-02" in ids(fs):
        failures.append("ctl7b mention guard: quoted historical denial fired")
    # ctl8 fabricated token robustness: unknown regularity token must not crash
    def fabricated(d):
        d["data"]["regularity"]["extension_regularity_exact"] = (
            "E_C7 subset of E_C0 and C7 is a strictly larger extension class")
        return d
    try:
        run(["F2a/AF-SCC-C2-VAC-GEN"], fabricated)
    except Exception as exc:  # noqa: BLE001
        failures.append("ctl8 fabricated token: raised %r" % exc)
    # ctl10 identity: F0 canonical + supplement clean under CD-07/CD-08
    got = ids(run(["F0-canonical", "F0-supplement"]))
    if got:
        failures.append("ctl10 identity F0 pair: expected clean, got %s" % got)

    def replace_in_strings(node, old, new):
        if isinstance(node, dict):
            return {k: replace_in_strings(v, old, new) for k, v in node.items()}
        if isinstance(node, list):
            return [replace_in_strings(v, old, new) for v in node]
        if isinstance(node, str) and old in node:
            return node.replace(old, new)
        return node

    # ctl11 CD-08 mutation: invert the canonical F0 C0-vs-C2 comparison
    def mutate_f0(d):
        d["data"] = replace_in_strings(
            d["data"], "strictly stronger than the C2 conclusion",
            "strictly weaker than the C2 conclusion")
        return d
    fs = run(["F0-canonical"], mutate_f0)
    if "CD-08" not in ids(fs):
        failures.append("ctl11 CD-08 mutation: inverted F0 comparison not detected")
    # ctl12 CD-07 mutation: invert the supplement entailment prose
    def mutate_supp(d):
        d["data"] = replace_in_strings(
            d["data"],
            "C0-inextendibility entails H2_loc-inextendibility",
            "C2-inextendibility entails C0-inextendibility")
        return d
    fs = run(["F0-supplement"], mutate_supp)
    if "CD-07" not in ids(fs):
        failures.append("ctl12 CD-07 mutation: inverted entailment prose not detected")

    # ctl9 empty document robustness
    try:
        Audit([{**base["F2a/AF-SCC-C2-VAC-GEN"], "data": {}, "text": ""}]).audit()
    except Exception as exc:  # noqa: BLE001
        failures.append("ctl9 empty document: raised %r" % exc)

    result = {"selftest": "PASS" if not failures else "FAIL",
              "cases": 14, "failures": failures}
    print(json.dumps(result, indent=2))
    return 0 if not failures else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pinned-dir", type=Path, default=HERE / "pinned")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--live-check", type=Path,
                        help="repo root whose live files must match the pinned hashes")
    args = parser.parse_args()
    if args.selftest:
        return selftest(args.pinned_dir)

    docs, manifest = load_pinned(args.pinned_dir)
    audit = Audit(docs)
    audit.audit()
    report = {
        "task_id": "W008-CONTAINMENT-DIRECTION-01",
        "actor": "worker-008",
        "oracle": ORDER_TEXT,
        "rank": RANK,
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(
                __import__("datetime").timedelta(hours=8))).isoformat(timespec="seconds"),
        "pinned_manifest": manifest,
        "findings": audit.findings,
        "finding_counts": audit.summary()["finding_counts"],
        "chain_edges": audit.summary()["chain_edges"],
        "skipped_rows": audit.info,
        "side_effects": "none: read-only audit of pinned copies; no canonical tool run",
    }
    if args.live_check:
        drift = {}
        for rel, want in manifest.items():
            live = args.live_check / rel
            got = sha256_file(live) if live.exists() else "ABSENT"
            drift[rel] = {"pinned": want, "live": got, "match": got == want}
        report["window_stability"] = {
            "all_match": all(v["match"] for v in drift.values()),
            "detail": drift,
        }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
