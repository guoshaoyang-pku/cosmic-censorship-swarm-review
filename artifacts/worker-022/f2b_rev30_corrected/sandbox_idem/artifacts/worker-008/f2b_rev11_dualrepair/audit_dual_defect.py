#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — fail-closed containment-consistency audit.

Read-only. Audits the *internal* consistency of declared extension-class
containment in the frozen AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN schemas:

  CHK-1 chain_concordance      C0 and C2 declare the same nested order
  CHK-2 size_premise           every "is a strictly larger|smaller extension
                               class" / explicit `E_A subset of E_B` /
                               `E_A contains E_B` statement agrees with the
                               order the file itself declares
  CHK-3 false_containment_denial
                               a "no containment with X is asserted" sentence
                               contradicts an order the file declares
                               (historical/negated quotations are exempt)
  CHK-4 binding_integrity      required ledger/binding keys are present and
                               parseable

Exit codes:  0 = PASS (no findings)
             1 = FAIL (consistency findings)
             3 = FAIL-CLOSED (hash mismatch, parse error, unparseable chain)
No verdict is emitted on exit 3.

Scope declaration: textual/logical consistency only.  It does not audit the
physical truth of the classes, citations, data-class regularity, or
definitional correctness, and it claims no node completion or gate verdict.
Interpretation and any repair are owned by astra-lead-formulation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

KNOWN = {"C0", "C2", "C11", "H2LOC"}
TOKEN_ALIASES = {
    "C0": "C0", "C2": "C2",
    "H2loc": "H2LOC", "H2LOC": "H2LOC", "H2_loc": "H2LOC",
    "C^1,1": "C11", "C1,1": "C11", "C11": "C11",
}

E_TOKEN = r"E_\{?([A-Za-z0-9^,]+)\}?"
SIZE_RE = re.compile(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc)\b\s+is a strictly (larger|smaller)\b")
SUBSET_RE = re.compile(E_TOKEN + r"\s+subset of\s+" + E_TOKEN)
CONTAINS_RE = re.compile(E_TOKEN + r"\s+contains\s+" + E_TOKEN)
STRENGTH_RE = re.compile(
    r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc)[- ]inextendibility is (?:strictly )?(stronger|weaker) than\b")
DENIAL_RE = re.compile(r"[Nn]o containment with ([^;.]*?) is asserted")
HISTORICAL_RE = re.compile(r"\b(was|is)\s+(wrong|false|corrected|repaired)\b")


def norm(tok: str) -> str:
    t = tok.strip()
    if t.startswith("E_"):
        t = t[2:]
    t = t.strip("{}").replace("\\", "").replace(" ", "")
    return TOKEN_ALIASES.get(t, t)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def yaml_leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from yaml_leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from yaml_leaves(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def line_of(text: str, fragment: str):
    i = text.find(fragment)
    return None if i < 0 else text[:i].count("\n") + 1


class FailClosed(Exception):
    pass


def parse_chain(text: str, path: str):
    head = text.split("(")[0].split(";")[0]
    parts = re.split(r"\s+(contains|subset of)\s+", head)
    if len(parts) < 3 or len(parts) % 2 == 0:
        raise FailClosed(f"unparseable extension_class_containment at {path}: {text!r}")
    toks = [norm(t) for t in parts[0::2]]
    rels = parts[1::2]
    for t in toks:
        if t not in KNOWN:
            raise FailClosed(f"unknown regularity token {t!r} in chain at {path}")
    edges = set()
    for i, rel in enumerate(rels):
        a, b = toks[i], toks[i + 1]
        edges.add((a, b) if rel == "contains" else (b, a))  # (larger, smaller)
    order = {t: 0 for t in toks}
    for _ in range(len(toks) + 1):
        changed = False
        for hi, lo in edges:
            if order[hi] <= order[lo]:
                order[hi] = order[lo] + 1
                changed = True
        if not changed:
            break
    for hi, lo in edges:
        if order[hi] <= order[lo]:
            raise FailClosed(f"declared containment cycle at {path}")
    return order, edges


def reachable(edges):
    reach = {t: set() for t in KNOWN}
    for hi, lo in edges:
        reach[hi].add(lo)
    for _ in range(len(KNOWN)):
        for a in KNOWN:
            reach[a] |= {y for x in list(reach[a]) for y in reach.get(x, set())}
    return reach


def historical(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 1):start]
    after = text[end:end + 70]
    return before in ("'", '"') and bool(HISTORICAL_RE.search(after))


def scan_file(path: Path, order, edges, file_class, text, findings):
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise FailClosed(f"{path}: not a mapping")
    leaves = list(yaml_leaves(data))

    # CHK-4 binding integrity
    if "implication_ledger" not in data or not isinstance(data["implication_ledger"], dict):
        findings.append(dict(kind="binding_integrity", file=str(path), path="implication_ledger",
                             line=None, detail="implication_ledger missing"))
    for key in ("class_contract_pointer", "class_id"):
        if key not in data:
            findings.append(dict(kind="binding_integrity", file=str(path), path=key,
                                 line=None, detail=f"{key} missing"))

    for leaf_path, value in leaves:
        # CHK-2a size premise
        for m in SIZE_RE.finditer(value):
            if historical(value, m.start(), m.end()):
                continue
            subject = norm(m.group(1))
            word = m.group(2)
            dest = file_class
            if leaf_path.startswith("implication_ledger.forbidden_transfers"):
                row = data["implication_ledger"]["forbidden_transfers"][
                    int(re.search(r"\[(\d+)\]", leaf_path).group(1))]
                to = str(row.get("to", ""))
                if to != "this class":
                    dest = norm(re.search(E_TOKEN, to).group(1)) if re.search(E_TOKEN, to) else file_class
            if word == "larger" and not order.get(subject, -1) > order.get(dest, -1):
                findings.append(dict(
                    kind="size_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)), detail=(
                        f"reason says {subject} is a strictly LARGER extension class than "
                        f"{dest}, but the declared order says rank({subject})="
                        f"{order.get(subject)} < rank({dest})={order.get(dest)}")))
            if word == "smaller" and not order.get(subject, -1) < order.get(dest, -1):
                findings.append(dict(
                    kind="size_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)), detail=(
                        f"reason says {subject} is a strictly SMALLER extension class than "
                        f"{dest}, but the declared order says rank({subject})="
                        f"{order.get(subject)} >= rank({dest})={order.get(dest)}")))

        # CHK-2b explicit subset/contains claims anywhere in the document
        for m in SUBSET_RE.finditer(value):
            a, b = norm(m.group(1)), norm(m.group(2))
            if a not in KNOWN or b not in KNOWN:
                continue
            if not order.get(a, 0) < order.get(b, 0):
                findings.append(dict(
                    kind="subset_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)),
                    detail=f"claims {a} subset of {b}, declared ranks {order.get(a)} >= {order.get(b)}"))
        for m in CONTAINS_RE.finditer(value):
            a, b = norm(m.group(1)), norm(m.group(2))
            if a not in KNOWN or b not in KNOWN:
                continue
            if not order.get(a, 0) > order.get(b, 0):
                findings.append(dict(
                    kind="contains_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)),
                    detail=f"claims {a} contains {b}, declared ranks {order.get(a)} <= {order.get(b)}"))

        # CHK-2c strength claims with an explicit second class token ("than X")
        for m in STRENGTH_RE.finditer(value):
            if historical(value, m.start(), m.end()):
                continue
            subject, word = norm(m.group(1)), m.group(2)
            tail = value[m.end():m.end() + 40]
            other = re.search(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc)\b", tail)
            if not other:
                continue
            dest = norm(other.group(1))
            if word == "stronger" and not order.get(subject, -1) > order.get(dest, -1):
                findings.append(dict(
                    kind="strength_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)),
                    detail=f"claims {subject}-inextendibility stronger than {dest}, "
                           f"declared ranks {order.get(subject)} <= {order.get(dest)}"))
            if word == "weaker" and not order.get(subject, -1) < order.get(dest, -1):
                findings.append(dict(
                    kind="strength_premise_inverted", file=str(path), path=leaf_path,
                    line=line_of(text, m.group(0)),
                    detail=f"claims {subject}-inextendibility weaker than {dest}, "
                           f"declared ranks {order.get(subject)} >= {order.get(dest)}"))

        # CHK-3 false containment denial
        for m in DENIAL_RE.finditer(value):
            if historical(value, m.start(), m.end()):
                continue
            mentioned = {norm(t) for t in re.findall(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc)\b", m.group(1))}
            mentioned = {t for t in mentioned if t in KNOWN}
            head = value[:m.start()]
            subject_m = re.search(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc)\b", head)
            subject = norm(subject_m.group(1)) if subject_m else file_class
            for other in sorted(mentioned):
                if other != subject and (other in reachable(edges).get(subject, set())
                                         or subject in reachable(edges).get(other, set())):
                    findings.append(dict(
                        kind="false_containment_denial", file=str(path), path=leaf_path,
                        line=line_of(text, m.group(0)), detail=(
                            f"denies containment between {subject} and {other}, but the "
                            f"declared chain orders them (ranks {order.get(subject)} vs "
                            f"{order.get(other)})")))


def audit(c0_path: Path, c2_path: Path, expect_c0: str, expect_c2: str,
          taxonomy: Path | None = None) -> dict:
    out = {"verdict": "FAIL-CLOSED", "checks": {}, "findings": [],
           "inputs": {}, "exit_code": 3}
    for label, path, expect in (("c0", c0_path, expect_c0), ("c2", c2_path, expect_c2)):
        got = sha256_file(path)
        out["inputs"][label] = {"path": str(path), "sha256": got, "expected_sha256": expect}
        if got != expect and expect:
            out["findings"].append(dict(kind="hash_mismatch", file=str(path), path=None, line=None,
                                        detail=f"measured {got} != expected {expect}"))
            return out
    c0_text = c0_path.read_text()
    c2_text = c2_path.read_text()
    c0 = yaml.safe_load(c0_text)
    c2 = yaml.safe_load(c2_text)
    try:
        c0_chain = c0["implication_ledger"]["extension_class_containment"]
        c2_chain = c2["implication_ledger"]["extension_class_containment"]
        order, edges = parse_chain(c0_chain, f"{c0_path}#implication_ledger.extension_class_containment")
        order2, edges2 = parse_chain(c2_chain, f"{c2_path}#implication_ledger.extension_class_containment")
    except (KeyError, TypeError) as exc:
        raise FailClosed(f"missing extension_class_containment: {exc}") from exc

    # CHK-1 concordance
    concordant = edges == edges2
    out["checks"]["CHK-1 chain_concordance"] = {
        "result": "PASS" if concordant else "FAIL",
        "c0_edges": sorted(list(e) for e in edges),
        "c2_edges": sorted(list(e) for e in edges2),
    }
    if not concordant:
        out["findings"].append(dict(kind="chain_declaration_divergence", file=str(c0_path),
                                    path="implication_ledger.extension_class_containment", line=None,
                                    detail=f"C0 edges {sorted(edges)} != C2 edges {sorted(edges2)}"))

    file_class = {"c0": "C0", "c2": "C2"}
    for label, path, text in (("c0", c0_path, c0_text), ("c2", c2_path, c2_text)):
        scan_file(path, order, edges, file_class[label], text, out["findings"])
    if taxonomy and taxonomy.exists():
        ttext = taxonomy.read_text()
        tdata = yaml.safe_load(ttext)
        node = (tdata or {}).get("implication_ledger", {}) if isinstance(tdata, dict) else {}
        if isinstance(node, dict) and "extension_class_containment" in node:
            t_edges = parse_chain(node["extension_class_containment"], str(taxonomy))[1]
            same = t_edges == edges
            out["checks"]["CHK-1b taxonomy_concordance"] = {
                "result": "PASS" if same else "FAIL", "taxonomy_edges": sorted(list(e) for e in t_edges)}
            if not same:
                out["findings"].append(dict(kind="chain_declaration_divergence", file=str(taxonomy),
                                            path="implication_ledger.extension_class_containment",
                                            line=None, detail="taxonomy chain differs from schema chain"))
        else:
            out["checks"]["CHK-1b taxonomy_concordance"] = {"result": "NOT-APPLICABLE",
                                                           "detail": "no implication_ledger.extension_class_containment"}
    # de-duplicate identical findings
    seen, uniq = set(), []
    for f in out["findings"]:
        key = (f["kind"], f["file"], f["path"], f["detail"])
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    out["findings"] = sorted(uniq, key=lambda f: (f["kind"], f["file"], f["path"] or "", f["detail"]))
    out["checks"]["CHK-2 size/strength premises"] = {
        "result": "FAIL" if any(f["kind"].endswith("_inverted") for f in out["findings"]) else "PASS"}
    out["checks"]["CHK-3 containment denials"] = {
        "result": "FAIL" if any(f["kind"] == "false_containment_denial" for f in out["findings"]) else "PASS"}
    bad_binding = [f for f in out["findings"] if f["kind"] == "binding_integrity"]
    out["checks"]["CHK-4 binding_integrity"] = {"result": "FAIL" if bad_binding else "PASS"}
    blocking = [f for f in out["findings"] if f["kind"] != "binding_integrity"] or bad_binding
    out["verdict"] = "FAIL" if out["findings"] else "PASS"
    out["exit_code"] = 1 if out["findings"] else 0
    return out


def selftest() -> int:
    """Synthetic minimal pairs: proves the checker follows the DECLARED order,
    not a hardcoded C2<C0 answer."""
    import tempfile
    base = {
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_contract_pointer": "synthetic",
        "regularity": {"must_not_conflate": ["synthetic bullet"]},
        "implication_ledger": {
            "extension_class_containment": "E_C0 contains E_H2loc contains E_C2",
            "one_way_entailments": [],
            "forbidden_transfers": [
                {"from": "no proper future C2 extension", "to": "this class",
                 "reason": "C2 is a strictly smaller extension class (E_C2 subset of E_C0), "
                           "so C2-inextendibility is strictly weaker"}]}}
    c2 = {
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_contract_pointer": "synthetic",
        "regularity": {"must_not_conflate": ["synthetic bullet"]},
        "implication_ledger": {
            "extension_class_containment": "E_C2 subset of E_H2loc subset of E_C0",
            "one_way_entailments": [],
            "forbidden_transfers": []}}
    results = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        c0p, c2p = td / "c0.yaml", td / "c2.yaml"
        c2p.write_text(yaml.safe_dump(c2))
        # A: consistent "smaller" -> PASS
        c0p.write_text(yaml.safe_dump(base))
        r = audit(c0p, c2p, sha256_file(c0p), sha256_file(c2p))
        results["synthetic_smaller_consistent"] = r["verdict"]
        # B: same declared order, "larger" -> FAIL
        bad = json.loads(json.dumps(base))
        bad["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
            "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")
        c0p.write_text(yaml.safe_dump(bad))
        r = audit(c0p, c2p, sha256_file(c0p), sha256_file(c2p))
        results["synthetic_larger_inverted"] = r["verdict"]
        # C: false denial -> FAIL
        bad2 = json.loads(json.dumps(base))
        bad2["regularity"]["must_not_conflate"] = [
            "H2_loc is a distinct axis. No containment with C2 or C0 is asserted here."]
        c0p.write_text(yaml.safe_dump(bad2))
        r = audit(c0p, c2p, sha256_file(c0p), sha256_file(c2p))
        results["synthetic_false_denial"] = r["verdict"]
        # D: historical/negated denial -> PASS (no false positive)
        hist = json.loads(json.dumps(base))
        hist["regularity"]["must_not_conflate"] = [
            "H2_loc is a distinct axis. [R2 major: the earlier 'No containment with C2 or C0 "
            "is asserted here' was wrong]"]
        c0p.write_text(yaml.safe_dump(hist))
        r = audit(c0p, c2p, sha256_file(c0p), sha256_file(c2p))
        results["synthetic_historical_denial_quoted"] = r["verdict"]
        # D2: clean base -> PASS
        c0p.write_text(yaml.safe_dump(base))
        r = audit(c0p, c2p, sha256_file(c0p), sha256_file(c2p))
        results["synthetic_clean"] = r["verdict"]
        # E: hash mismatch -> FAIL-CLOSED
        r = audit(c0p, c2p, "0" * 64, sha256_file(c2p))
        results["synthetic_hash_mismatch"] = r["verdict"]
    expected = {"synthetic_smaller_consistent": "PASS", "synthetic_larger_inverted": "FAIL",
                "synthetic_false_denial": "FAIL", "synthetic_historical_denial_quoted": "PASS",
                "synthetic_clean": "PASS",
                "synthetic_hash_mismatch": "FAIL-CLOSED"}
    print(json.dumps({"selftest": results, "expected": expected,
                      "ok": results == expected}, indent=1))
    return 0 if results == expected else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0", type=Path)
    ap.add_argument("--c2", type=Path)
    ap.add_argument("--taxonomy", type=Path, default=None)
    ap.add_argument("--expect-c0", default="")
    ap.add_argument("--expect-c2", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.c0 or not args.c2:
        ap.error("--c0 and --c2 are required unless --selftest")
    try:
        report = audit(args.c0, args.c2, args.expect_c0, args.expect_c2, args.taxonomy)
    except FailClosed as exc:
        report = {"verdict": "FAIL-CLOSED", "error": str(exc), "exit_code": 3, "findings": []}
    report["label"] = args.label
    report["task_id"] = "W008-F2B-DUALREPAIR-01"
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.json:
        args.json.write_text(text + "\n")
    print(text)
    return int(report["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
