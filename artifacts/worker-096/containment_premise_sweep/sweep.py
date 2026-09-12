#!/usr/bin/env python3
"""
W096-F2B-CONTAINMENT-PREMISE-SWEEP-01

Independent, deterministic sweep of EVERY extension-class containment premise in the
frozen formulation set (F1, F2a, F2b, F0-taxonomy), checked against the containment
chain the artifacts themselves declare:

    E_C2  subset of  E_{C^1,1}  subset of  E_H2loc  subset of  E_C0

(poset index = size of the extension set; strictly increasing C2 < C11 < H2LOC < C0.)

Purpose: L-FORM-01 (astra-lead-formulation, 2026-09-12T00:44:52+08:00) reports one
inverted justification premise at schemas/af_scc_c0_vacuum.yaml:245.  A single known
defect does not bound the blast radius.  This sweep answers the bounded question:

    Is the C0:245 inversion the ONLY extension-class containment premise in the frozen
    set that contradicts the declared chain, or are there siblings?

Independence: the classifier is written from the raw YAML/strings, not from any
reviewer's report; every premise is extracted and re-adjudicated here.  It does not
read reviews/*L-FORM*, worker-060/084/086/092/096 artifacts, or the map prose.

Read-only.  Writes only report.json / runlog.txt next to this file.  Exits 0 when the
sweep ran, 1 on input drift or control failure, 10 when a NEW (non-C0:245) defect is
found (so the caller can branch without parsing).

Usage:  python3 sweep.py            # runs sweep, writes report.json
        python3 sweep.py --selftest # controls only
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FROZEN_REV = 28
FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"

# label -> (relative path, document class id or None)
FILES = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "WCC"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "C2"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "C0"),
    "F0": ("research_map/formulation_taxonomy.yaml", None),
}

# canonical chain, smallest extension set first (declared at F2a:236 and F2b:238)
POSET = ["C2", "C11", "H2LOC", "C0"]

# token -> canonical class.  Longest alternatives first.
TOKEN_CLASS = [
    (r"c\^?\{?1\s*,\s*1\}?", "C11"),
    (r"h\^?2[_\s]?\{?loc\}?", "H2LOC"),
    (r"c\s*0", "C0"),
    (r"c\s*2", "C2"),
    (r"c\s*1", "C1"),  # separate axis value, deliberately out of the poset
]
TOKEN_RE = re.compile("|".join(f"(?:{p})" for p, _ in TOKEN_CLASS), re.I)


def norm_token(tok):
    for pat, cls in TOKEN_CLASS:
        if re.fullmatch(pat, tok, re.I):
            return cls
    return None


def norm_text_token(tok):
    """Normalise a possibly LaTeX-braced token like 'C^{1,1}' or '{C^1,1}'."""
    t = tok.strip().strip("{}")
    if t.startswith("E_"):
        t = t[2:]
    t = t.strip().strip("{}")
    t = t.replace("\\", "")
    return norm_token(t)


# Extension-class token, optionally written E_<class> with LaTeX braces.
E_TOKEN = r"(?:E_)?\{?\s*(?:C\^?\{?1\s*,\s*1\}?|H\^?2[_\s]?\{?loc\}?|C\s*[012])\s*\}?"
# Strict form used only for pair scanning: mandatory E_, so the lookahead cannot also
# match the same token starting inside it (which double-counted every link).
PAIR_TOKEN = r"E_\{?\s*(?:C\^?\{?1\s*,\s*1\}?|H\^?2[_\s]?\{?loc\}?|C\s*[012])\s*\}?"

# E_<class> contains|subset of E_<class>   (chains decompose into consecutive pairs).
# Scanned with a lookahead so consecutive chain links overlap: "A contains B contains C"
# must yield BOTH (A,B) and (B,C); a plain finditer drops the middle link.
PAIR_BODY = (
    rf"(?P<a>{PAIR_TOKEN})\s*(?P<rel>contains|subset\s+of|is\s+a\s+subset\s+of)\s*(?P<b>{PAIR_TOKEN})"
)
PAIR_SCAN_RE = re.compile(rf"(?=(?<![A-Za-z0-9_^{{}},])({PAIR_BODY}))", re.I)
# <class> is a strictly larger|smaller extension class
LARGER_RE = re.compile(
    rf"(?P<a>{E_TOKEN})\s+is\s+(?:a|the)\s+strictly\s+(?P<dir>larger|smaller)\s+extension\s+class",
    re.I,
)
# "those are strictly larger classes" (taxonomy meaning_C2; referent = C2)
THOSE_RE = re.compile(r"those\s+are\s+strictly\s+(?P<dir>larger|smaller)\s+classes", re.I)

NO_EXT_RE = re.compile(
    rf"no\s+proper\s+future\s+(?P<cls>{E_TOKEN})\s+(?:[\w-]+\s+){{0,3}}extension",
    re.I,
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_line(raw_lines, needle, start=0):
    """First line at/after `start` (0-based) containing the needle. A cursor keeps
    short quoted strings (which also occur earlier as substrings) on their own line."""
    key = needle.strip()[:60]
    order = range(max(start, 0), len(raw_lines))
    for i in order:
        if key and key in raw_lines[i]:
            return i + 1
    key = needle.strip()[:30]
    for i in order:
        if key and key in raw_lines[i]:
            return i + 1
    for i in range(0, max(start, 0)):  # wrap as last resort
        if key and key in raw_lines[i]:
            return i + 1
    return None


def walk(obj, path=""):
    """Yield (json-ish path, string value)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def context_for(path, doc_class):
    """Class the sentence is *about*, for larger/smaller claims."""
    if doc_class:
        return doc_class
    if path.endswith("meaning_C2"):
        return "C2"
    return None


def check_relation(a, b, rel):
    """Return ('consistent'|'inverted'|'out_of_scope', detail)."""
    if a not in POSET or b not in POSET:
        return "out_of_scope", f"class outside poset ({a} or {b}; C1 is a separate axis value)"
    ia, ib = POSET.index(a), POSET.index(b)
    if rel in ("contains", "superset"):
        ok = ia > ib
        detail = f"poset says C2<C11<H2LOC<C0; claimed {a} contains {b}"
    else:  # subset of
        ok = ia < ib
        detail = f"poset says C2<C11<H2LOC<C0; claimed {a} subset of {b}"
    return ("consistent" if ok else "inverted"), detail


def extract_statements(label, doc_class, path, value, raw_lines, cursor=None):
    rows = []
    start = cursor["line"] if cursor else 0

    def fl(text):
        ln = find_line(raw_lines, text, start)
        if cursor is not None and ln:
            cursor["line"] = ln - 1
        return ln

    for m in PAIR_SCAN_RE.finditer(value):
        whole = m.group(1)
        a, b = norm_text_token(m.group("a")), norm_text_token(m.group("b"))
        rel = "contains" if "contain" in m.group("rel").lower() else "subset"
        verdict, detail = check_relation(a, b, rel)
        rows.append(
            {
                "kind": "containment_rel",
                "file": label,
                "path": path,
                "line": fl(value),
                "text": whole,
                "subject": a,
                "object": b,
                "claimed": rel,
                "verdict": verdict,
                "detail": detail,
            }
        )
    for m in LARGER_RE.finditer(value):
        a = norm_text_token(m.group("a"))
        ctx = context_for(path, doc_class)
        direction = m.group("dir").lower()
        if ctx is None or a not in POSET or ctx not in POSET:
            verdict, detail = "out_of_scope", f"no poset context for {a} vs {ctx}"
        else:
            larger = POSET.index(a) > POSET.index(ctx)
            ok = larger if direction == "larger" else (not larger)
            verdict = "consistent" if ok else "inverted"
            detail = (
                f"poset: idx({a})={POSET.index(a)}, idx({ctx})={POSET.index(ctx)} "
                f"(C2<C11<H2LOC<C0); claimed {a} strictly {direction} than context {ctx}"
            )
        rows.append(
            {
                "kind": "larger_smaller",
                "file": label,
                "path": path,
                "line": fl(value),
                "text": m.group(0),
                "subject": a,
                "context": ctx,
                "claimed": f"strictly {direction}",
                "verdict": verdict,
                "detail": detail,
            }
        )
    for m in THOSE_RE.finditer(value):
        # taxonomy meaning_C2: "those" = C^{1,1} and H2_loc, referent C2
        ctx = context_for(path, doc_class)
        direction = m.group("dir").lower()
        subjects = ["C11", "H2LOC"]
        if ctx != "C2":
            rows.append(
                {
                    "kind": "larger_smaller_referent",
                    "file": label,
                    "path": path,
                    "line": find_line(raw_lines, value),
                    "text": m.group(0),
                    "subject": "C11,H2LOC",
                    "context": ctx,
                    "claimed": f"strictly {direction}",
                    "verdict": "out_of_scope",
                    "detail": f"referent not C2 (got {ctx})",
                }
            )
            continue
        ok = all(POSET.index(s) > POSET.index(ctx) for s in subjects)
        rows.append(
            {
                "kind": "larger_smaller_referent",
                "file": label,
                "path": path,
                "line": fl(value),
                "text": m.group(0),
                "subject": "C11,H2LOC",
                "context": ctx,
                "claimed": f"strictly {direction}",
                "verdict": "consistent" if ok else "inverted",
                "detail": "poset: C2 < C11,H2LOC; referent C2",
            }
        )
    return rows


def class_of_no_extension(text):
    m = NO_EXT_RE.search(text)
    if not m:
        return None
    if "distributional" in m.group(0).lower():
        return "C0d"  # variant axis, outside the poset
    return norm_text_token(m.group("cls"))


def entailment_licensed(src, dst):
    """'no proper future <src> extension' entails 'no proper future <dst> extension'
    iff every dst-extension is a src-extension, i.e. E_dst subset E_src (idx(dst) < idx(src))."""
    return POSET.index(dst) < POSET.index(src)


def ledger_checks(label, doc_class, ledger):
    rows = []
    for i, row in enumerate(ledger.get("one_way_entailments", []) or []):
        src, dst = class_of_no_extension(row.get("from", "")), class_of_no_extension(row.get("to", ""))
        rel = row.get("relation", "")
        if src in POSET and dst in POSET:
            licensed = entailment_licensed(src, dst)
            ok = (rel == "entails" and licensed) or (rel == "forbidden" and not licensed)
            rows.append(
                {
                    "kind": "ledger_row",
                    "file": label,
                    "path": f".implication_ledger.one_way_entailments[{i}]",
                    "from": row.get("from"),
                    "to": row.get("to"),
                    "relation": rel,
                    "source_class": src,
                    "target_class": dst,
                    "verdict": "consistent" if ok else "defect",
                    "detail": f"entailment licensed iff E_{dst} subset E_{src}; licensed={licensed}",
                    "reason": row.get("reason"),
                }
            )
        else:
            rows.append(
                {
                    "kind": "ledger_row",
                    "file": label,
                    "path": f".implication_ledger.one_way_entailments[{i}]",
                    "from": row.get("from"),
                    "to": row.get("to"),
                    "relation": rel,
                    "source_class": src,
                    "target_class": dst,
                    "verdict": "out_of_scope",
                    "detail": "variant/cross-family row outside the E_* poset (e.g. C0 distributional variant)",
                    "reason": row.get("reason"),
                }
            )
    for i, row in enumerate(ledger.get("forbidden_transfers", []) or []):
        src, dst = class_of_no_extension(row.get("from", "")), class_of_no_extension(row.get("to", ""))
        if src is None and row.get("from") == "AF-WCC-VAC-GEN":
            src = "WCC"
        if dst is None and row.get("to") == "this class":
            dst = doc_class
        if src in POSET and dst in POSET:
            licensed = entailment_licensed(src, dst)
            ok = not licensed
            rows.append(
                {
                    "kind": "forbidden_row",
                    "file": label,
                    "path": f".implication_ledger.forbidden_transfers[{i}]",
                    "from": row.get("from"),
                    "to": row.get("to"),
                    "source_class": src,
                    "target_class": dst,
                    "verdict": "consistent" if ok else "defect",
                    "detail": f"forbidden transfer correct iff E_{dst} NOT subset E_{src}; licensed={licensed}",
                    "reason": row.get("reason"),
                }
            )
        else:
            rows.append(
                {
                    "kind": "forbidden_row",
                    "file": label,
                    "path": f".implication_ledger.forbidden_transfers[{i}]",
                    "from": row.get("from"),
                    "to": row.get("to"),
                    "source_class": src,
                    "target_class": dst,
                    "verdict": "out_of_scope",
                    "detail": "cross-family or variant row outside the E_* poset",
                    "reason": row.get("reason"),
                }
            )
    return rows


# ---------------------------------------------------------------- controls
CONTROLS = [
    ("E_C2 is a strictly larger extension class", "C0", "C0", "inverted"),
    ("E_C2 is a strictly smaller extension class", "C0", "C0", "consistent"),
    ("E_C0 is a strictly larger extension class", "C2", "C2", "consistent"),
    ("E_{C^1,1} is a strictly smaller extension class", "C0", "C0", "consistent"),
    ("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2", "C0", "C0", "consistent"),
    ("E_C2 contains E_C0", "C0", "C0", "inverted"),
    ("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0", "C2", "C2", "consistent"),
    ("E_C0 subset of E_C2", "C2", "C2", "inverted"),
]

# chain controls: (text, doc_class, expected_link_count, expectation)
CHAIN_CONTROLS = [
    ("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2", "C0", 3, "all_consistent"),
    ("E_C0 contains E_C2 contains E_H2loc", "C0", 2, "has_inverted"),
]


def run_controls():
    results = []
    for text, doc_class, ctx, expected in CONTROLS:
        pseudo_lines = [text]
        if text.startswith("E_C0 contains"):
            rows = extract_statements("CTL", doc_class, ".ctl", text, pseudo_lines)
            got = rows[0]["verdict"] if rows else "none"
        elif re.search(r"strictly (larger|smaller) extension class", text):
            rows = extract_statements("CTL", doc_class, ".ctl", text, pseudo_lines)
            got = rows[0]["verdict"] if rows else "none"
        else:
            rows = extract_statements("CTL", doc_class, ".ctl", text, pseudo_lines)
            verdicts = [r["verdict"] for r in rows]
            got = "consistent" if verdicts and all(v == "consistent" for v in verdicts) else (
                "inverted" if "inverted" in verdicts else "none"
            )
        results.append({"text": text, "context": ctx, "expected": expected, "got": got, "pass": got == expected})
    # chain controls: the overlapping scan must recover every consecutive link
    for text, doc_class, n_expected, expectation in CHAIN_CONTROLS:
        rows = [r for r in extract_statements("CTL", doc_class, ".ctl", text, [text])
                if r["kind"] == "containment_rel"]
        verdicts = [r["verdict"] for r in rows]
        if expectation == "all_consistent":
            ok = len(rows) == n_expected and all(v == "consistent" for v in verdicts)
        else:
            ok = len(rows) == n_expected and "inverted" in verdicts
        results.append(
            {
                "text": text,
                "context": doc_class,
                "expected": f"{n_expected} links, {expectation}",
                "got": f"{len(rows)} links {verdicts}",
                "pass": ok,
            }
        )
    # ledger control: forbidden no-C0 -> no-C2 is a wrongly-forbidden licensed transfer
    led = {        "one_way_entailments": [
            {"from": "no proper future C0 extension", "to": "no proper future C2 extension",
             "relation": "entails", "reason": "ctl"}
        ],
        "forbidden_transfers": [
            {"from": "no proper future C0 extension", "to": "no proper future C2 extension",
             "reason": "ctl wrongly forbidden"}
        ],
    }
    rows = ledger_checks("CTL", "C2", led)
    results.append({"text": "ledger: forbidden no-C0->no-C2", "context": "C2", "expected": "defect",
                    "got": rows[1]["verdict"], "pass": rows[1]["verdict"] == "defect"})
    return results


def run_sweep():
    inputs, statements, ledgers = {}, [], []
    before = {}
    for label, (rel, _) in FILES.items():
        before[label] = sha256(REPO / rel)
    for label, (rel, doc_class) in FILES.items():
        text = (REPO / rel).read_text()
        raw_lines = text.splitlines()
        data = yaml.safe_load(text)
        inputs[label] = {
            "path": rel,
            "sha256": before[label],
            "lines": len(raw_lines),
            "doc_class": doc_class,
        }
        cursor = {"line": 0}
        for path, value in walk(data):
            statements.extend(extract_statements(label, doc_class, path, value, raw_lines, cursor))
        led = data.get("implication_ledger")
        if led:
            ledgers.extend(ledger_checks(label, doc_class, led))
    after = {label: sha256(REPO / rel) for label, (rel, _) in FILES.items()}
    drift = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    return inputs, statements, ledgers, drift


def main():
    selftest = "--selftest" in sys.argv
    controls = run_controls()
    controls_pass = all(c["pass"] for c in controls)
    if selftest:
        print(json.dumps({"controls": controls, "all_pass": controls_pass}, indent=1))
        return 0 if controls_pass else 1

    inputs, statements, ledgers, drift = run_sweep()
    frozen_ok = sha256(REPO / "artifacts/formulation/FROZEN.json") == FROZEN_SHA
    known = {"file": "F2b", "line": 245}
    findings = [
        s for s in statements + ledgers
        if s["verdict"] in ("inverted", "defect")
    ]
    new_findings = [f for f in findings if not (f["file"] == known["file"] and f["line"] == known["line"])]
    summary = {
        "files_swept": len(FILES),
        "containment_premises_extracted": len(statements),
        "ledger_rows_checked": len(ledgers),
        "consistent": sum(1 for s in statements + ledgers if s["verdict"] == "consistent"),
        "inverted_or_defect": len(findings),
        "out_of_scope": sum(1 for s in statements + ledgers if s["verdict"] == "out_of_scope"),
        "defect_lines": sorted({f"{f['file']}:{f['line']}" for f in findings}),
        "per_file": {
            lab: {
                "premises": sum(1 for s in statements if s["file"] == lab),
                "ledger_rows": sum(1 for s in ledgers if s["file"] == lab),
                "consistent": sum(1 for s in statements + ledgers if s["file"] == lab and s["verdict"] == "consistent"),
                "inverted_or_defect": sum(1 for s in statements + ledgers if s["file"] == lab and s["verdict"] in ("inverted", "defect")),
            }
            for lab in FILES
        },
        "new_defects_beyond_C0_245": len(new_findings),
        "C0_245_inversion_reproduced": any(
            s["file"] == "F2b" and s["line"] == 245 and s["verdict"] == "inverted" for s in statements
        ),
        "controls_pass": controls_pass,
        "frozen_rev28_manifest_pin_ok": frozen_ok,
        "input_drift": drift,
    }
    report = {
        "schema_version": "w096-containment-sweep/1",
        "task_id": "W096-F2B-CONTAINMENT-PREMISE-SWEEP-01",
        "worker": "worker-096",
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "poset": {"order": POSET, "meaning": "strictly increasing extension-set size; E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
                  "declared_at": ["schemas/af_scc_c2_vacuum.yaml:236", "schemas/af_scc_c0_vacuum.yaml:238"]},
        "inputs": inputs,
        "frozen_rev": FROZEN_REV,
        "frozen_sha256": FROZEN_SHA,
        "statements": statements,
        "ledger_checks": ledgers,
        "controls": controls,
        "summary": summary,
        "falsifier": (
            "Re-run this script. Falsified if it reports >0 NEW defect lines beyond F2b:245, if it fails to "
            "reproduce the F2b:245 inversion, if any input hash differs from the values in inputs{}, if the "
            "FROZEN rev28 pin stops matching, or if a control fails. A revision of the declared containment "
            "chain itself (F2a:236 / F2b:238) voids every verdict in this report."
        ),
        "non_claims": [
            "Not a full-schema review and not a gate verdict; one criterion (containment-premise direction) only.",
            "The poset is the chain the frozen artifacts declare; this sweep checks internal consistency, not the mathematics of the chain.",
            "C1 and the distributional-vacuum variant are outside the poset and reported out_of_scope, not adjudicated.",
            "F1 (af_wcc_vacuum.yaml) carries no implication_ledger and asserts no extension-class containment; its 0-row contribution is a negative finding, not an unchecked file.",
            "No canonical file was edited; worker events cannot set status=done or a gate verdict.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps(summary, indent=1))
    if not controls_pass or drift or not frozen_ok:
        return 1
    return 10 if new_findings else 0


if __name__ == "__main__":
    sys.exit(main())
