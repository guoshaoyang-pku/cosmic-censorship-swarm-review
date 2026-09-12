#!/usr/bin/env python3
"""W029-F2B-REPAIR-CANDIDATE-VERIFY-01 (worker-029, 2026-09-12).

Independent, read-only verification of the two F2b repair candidates staged by worker-080
(node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM), plus the circulating 2-edit repair.

Fresh re-implementation: no worker-066/worker-080/worker-008 code is imported or copied.
The instrument parses the schema's own declared extension-set chain, derives a partial order,
and checks (a) every one_way_entailments row, (b) every forbidden_transfers row,
(c) every "strictly larger/smaller extension class" size premise, (d) every class-relative
"X-inextendibility ENTAILS ..." claim, and (e) live containment denials in must_not_conflate.
Bracketed/quoted-withdrawn corrections are stripped before (e).

Falsifier (pre-registered): any pinned byte moves; live b2ab6acb does not yield exactly
{size_premise_inverted, false_containment_denial}; candidate_corrected 51c253c4 or
candidate_nesting 4951cc96 yields any finding; the circulating 84b5d3fa does not yield
entailment_direction_inverted; the class-relativity control rejects the same sentence under
own=C2; any other control departs from its pre-registered expectation; patch application does
not reproduce the candidate hashes.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / "pinned"

C0 = "C0"
C2 = "C2"
H2LOC = "H2loc"
C11 = "C^1,1"
C0DV = "C0dv"
OWN_BY_CLASS = {"AF-SCC-C0-VAC-GEN": C0, "AF-SCC-C2-VAC-GEN": C2}

TOK_ALIASES = {
    "C0": C0,
    "C2": C2,
    "H2loc": H2LOC,
    "H2_loc": H2LOC,
    "C^1,1": C11,
    "C^{1,1}": C11,
    "C0dv": C0DV,
    "C0dist": C0DV,
}

PINS = {
    "c0_live": ("c0_live.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "c2_live": ("c2_live.yaml", "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "f1_live": ("f1_live.yaml", "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "frozen_rev29": ("FROZEN_rev29.json", "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "cand_corrected": ("cand_corrected_51c253c4.yaml", "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a"),
    "cand_nesting": ("cand_nesting_4951cc96.yaml", "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f"),
    "cand_circulating": ("cand_circulating_84b5d3fa.yaml", "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"),
    "cand_rev12": ("cand_rev12_98f9ec83.yaml", "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c"),
    "patch_corrected": ("patch_corrected.diff", "174f40ea586e1d0ae3f3cf375644cd2712fbcb959391b4a872e06d8e0f964688"),
}

DEFECT_KINDS = ("chain_missing", "unresolved_statement", "entailment_row_invalid",
                "forbidden_row_licensed", "size_premise_inverted", "false_containment_denial",
                "entailment_direction_inverted", "denial_inconsistent_with_entailment")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


# ---------------------------------------------------------------- chain parsing
def _first_token(chunk: str) -> str | None:
    m = re.search(r"E_\{?([A-Za-z0-9^,]+)\}?", chunk)
    if not m:
        return None
    raw = m.group(1)
    return _resolve_token(raw) or raw


def parse_chain(text: str):
    """Return {token: rank} with rank 0 = largest extension set, or None."""
    if not text:
        return None
    if " contains " in text:
        chunks = text.split(" contains ")
        toks = [_first_token(c) for c in chunks]
    elif " subset of " in text:
        chunks = text.split(" subset of ")
        toks = [_first_token(c) for c in chunks][::-1]
    else:
        return None
    toks = [t for t in toks if t]
    if len(toks) < 2 or len(set(toks)) != len(toks):
        return None
    return {t: i for i, t in enumerate(toks)}


STMT_RE = re.compile(r"no proper future\s+(.+?)\s+extension", re.I)


def parse_stmt(s: str, own: str):
    """Map a ledger statement to an extension-set token, or None."""
    if s is None:
        return None
    s = str(s)
    if "this class" in s.lower():
        return own
    m = STMT_RE.search(s)
    if not m:
        return None
    body = m.group(1).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if body.startswith("c0") and "distributional" in body:
        return C0DV
    if body.startswith("c0"):
        return C0
    if body.startswith("c2"):
        return C2
    if body.startswith("h2loc"):
        return H2LOC
    if body.startswith("c^1,1") or body.startswith("c11"):
        return C11
    return None


def rank(ranks, tok):
    if tok == C0DV and C0 in ranks:
        return ranks[C0] + 0.5
    return ranks.get(tok) if ranks else None


def entails(ranks, a, b) -> bool | None:
    """a => b valid iff E_b subset-of-or-equal E_a (rank_b >= rank_a)."""
    ra, rb = rank(ranks, a), rank(ranks, b)
    if ra is None or rb is None:
        return None
    return rb >= ra


# ---------------------------------------------------------------- text scanning
def strip_withdrawn(text: str) -> str:
    """Remove bracketed corrections and quoted '... was wrong' fragments."""
    out = re.sub(r"\[[^\]]*\]", " ", text)
    out = re.sub(r"'[^']*'\s*was wrong", " ", out)
    out = re.sub(r'"[^"]*"\s*was wrong', " ", out)
    return out


DENIAL_RE = re.compile(r"no\s+containment\s+with[^.]*?assert", re.I)
SIZE_RE = re.compile(r"strictly\s+(larger|smaller)\s+extension\s+class", re.I)
SUBSET_RE = re.compile(r"E_\{?([A-Za-z0-9^,{}]+)\}?\s+subset\s+of\s+E_\{?([A-Za-z0-9^,{}]+)\}?", re.I)
CLAIM_RE = re.compile(
    r"([A-Za-z0-9_^{},\s]+?)-inextendibility\s+(?:therefore\s+)?(?:ENTAILS|entails)\s+"
    r"([^.;]+)",
    re.I,
)


TOK_ALIASES_LC = {k.lower().replace("_", "").replace(" ", ""): v for k, v in TOK_ALIASES.items()}


def _resolve_token(raw: str):
    raw = raw.strip().lower().replace(" ", "").replace("_", "")
    return TOK_ALIASES_LC.get(raw)


def _tok_from_phrase(phrase: str, own: str, reverse: bool = False):
    """Resolve the nearest resolvable token; reverse=True takes the last (nearest preceding)."""
    p = phrase.strip().lower()
    if p.startswith("this class"):
        return own
    cands = re.findall(r"[a-z0-9_^{},]+", p)
    if reverse:
        cands = cands[::-1]
    for c in cands:
        t = _resolve_token(c)
        if t:
            return t
    return None


def check_doc(doc: dict, own: str, label: str) -> dict:
    findings = []
    ledger = doc.get("implication_ledger") or {}
    chain_text = ledger.get("extension_class_containment")
    ranks = parse_chain(str(chain_text)) if chain_text else None
    checks = {"chain_tokens": list(ranks) if ranks else None,
              "one_way_rows": 0, "forbidden_rows": 0, "claims": 0, "denial_slots": 0}

    if not ranks:
        # still scan the normative denial slot: a WCC-family file legitimately has no chain
        mnc = ((doc.get("regularity") or {}).get("must_not_conflate")) or []
        for i, bullet in enumerate(mnc if isinstance(mnc, list) else [mnc]):
            checks["denial_slots"] += 1
            if DENIAL_RE.search(strip_withdrawn(str(bullet))):
                findings.append({"id": "false_containment_denial",
                                 "carrier": f"regularity.must_not_conflate[{i}]",
                                 "detail": "live containment denial survives correction-stripping"})
        findings.insert(0, {"id": "chain_missing", "carrier": "implication_ledger.extension_class_containment",
                            "detail": "no parseable extension-class chain"})
        return {"label": label, "own": own, "findings": findings, "checks": checks,
                "chain": None, "ranks": None}

    def add(kind, carrier, detail):
        findings.append({"id": kind, "carrier": carrier, "detail": detail})

    # (a) one_way_entailments
    for i, row in enumerate(ledger.get("one_way_entailments") or []):
        checks["one_way_rows"] += 1
        a = parse_stmt(row.get("from"), own)
        b = parse_stmt(row.get("to"), own)
        ok = entails(ranks, a, b)
        if ok is None:
            add("unresolved_statement", f"implication_ledger.one_way_entailments[{i}]",
                f"from={row.get('from')!r} to={row.get('to')!r} -> {a}/{b}")
        elif not ok:
            add("entailment_row_invalid", f"implication_ledger.one_way_entailments[{i}]",
                f"{a} => {b} not licensed by ranks {ranks}")

    # (b) forbidden_transfers + (c) size premises
    for i, row in enumerate(ledger.get("forbidden_transfers") or []):
        checks["forbidden_rows"] += 1
        frm, to = row.get("from"), row.get("to")
        reason = str(row.get("reason") or "")
        if "AF-" in str(frm) or "AF-" in str(to) or "AF-" in reason and "independent" in reason.lower():
            if "independent" not in reason.lower() and "no transfer" not in reason.lower():
                add("forbidden_row_licensed", f"implication_ledger.forbidden_transfers[{i}]",
                    "cross-family row lacks an independence reason")
            continue
        a, b = parse_stmt(frm, own), parse_stmt(to, own)
        ok = entails(ranks, a, b)
        if ok is None:
            add("unresolved_statement", f"implication_ledger.forbidden_transfers[{i}]",
                f"from={frm!r} to={to!r} -> {a}/{b}")
        elif ok:
            add("forbidden_row_licensed", f"implication_ledger.forbidden_transfers[{i}]",
                f"{a} => {b} is licensed yet recorded forbidden")
        for m in SIZE_RE.finditer(reason):
            word = m.group(1).lower()
            subject = a
            if subject is None:
                continue
            want = (rank(ranks, subject) < rank(ranks, b)) if word == "larger" else (rank(ranks, subject) > rank(ranks, b))
            if not want:
                add("size_premise_inverted", f"implication_ledger.forbidden_transfers[{i}].reason",
                    f"claims {word} extension class ({subject} vs {b}) but ranks are {ranks}")
        for m in SUBSET_RE.finditer(reason):
            x = _resolve_token(m.group(1)) or m.group(1)
            y = _resolve_token(m.group(2)) or m.group(2)
            if rank(ranks, x) is None or rank(ranks, y) is None or not (rank(ranks, x) > rank(ranks, y)):
                add("size_premise_inverted", f"implication_ledger.forbidden_transfers[{i}].reason",
                    f"parenthetical E_{x} subset of E_{y} contradicts ranks {ranks}")

    # (d) class-relative entailment claims anywhere in the document
    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for j, v in enumerate(node):
                walk(v, f"{path}[{j}]")
        elif isinstance(node, str):
            for clause in re.split(r"[.;]|,\s*and\s+", node):
                for m in CLAIM_RE.finditer(clause):
                    subj = _tok_from_phrase(m.group(1), own, reverse=True)
                    tail = m.group(2)
                    obj = _tok_from_phrase(tail, own)
                    checks["claims"] += 1
                    if subj is None or obj is None:
                        add("unresolved_statement", path, f"claim subject/object unresolved: {m.group(0)!r}")
                        continue
                    if not entails(ranks, subj, obj):
                        add("entailment_direction_inverted", path,
                            f"claim {subj}-inext => {obj} contradicts ranks {ranks}: {m.group(0)[:160]!r}")
                    neg = re.search(r"not\s+this\s+class", tail, re.I)
                    if neg and entails(ranks, subj, own):
                        add("denial_inconsistent_with_entailment", path,
                            f"tail denies {subj} => this class ({own}) but ranks license it")

    walk(doc, "$")

    # (e) live containment denials in must_not_conflate
    mnc = ((doc.get("regularity") or {}).get("must_not_conflate")) or []
    for i, bullet in enumerate(mnc if isinstance(mnc, list) else [mnc]):
        checks["denial_slots"] += 1
        live = strip_withdrawn(str(bullet))
        if DENIAL_RE.search(live):
            add("false_containment_denial", f"regularity.must_not_conflate[{i}]",
                "live containment denial survives correction-stripping")

    return {"label": label, "own": own, "findings": findings, "checks": checks,
            "chain": str(chain_text), "ranks": ranks}


# ---------------------------------------------------------------- patch application
def apply_unified_diff(orig: str, diff: str) -> str:
    lines = orig.splitlines(keepends=True)
    dlines = diff.splitlines()
    out, i, pos = [], 0, 0
    hunks = []
    while i < len(dlines):
        if dlines[i].startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", dlines[i])
            start = int(m.group(1)) - 1
            body, i = [], i + 1
            while i < len(dlines) and not dlines[i].startswith("@@"):
                body.append(dlines[i])
                i += 1
            hunks.append((start, body))
        else:
            i += 1
    for start, body in hunks:
        out.extend(lines[pos:start])
        pos = start
        for b in body:
            if b.startswith(" "):
                assert lines[pos].rstrip("\n") == b[1:].rstrip("\n"), f"context mismatch at {pos}: {lines[pos]!r} vs {b!r}"
                out.append(lines[pos]); pos += 1
            elif b.startswith("-"):
                assert lines[pos].rstrip("\n") == b[1:].rstrip("\n"), f"del mismatch at {pos}: {lines[pos]!r} vs {b!r}"
                pos += 1
            elif b.startswith("+"):
                out.append(b[1:] + "\n")
    out.extend(lines[pos:])
    return "".join(out)


def diff_changed_lines(a: str, b: str):
    al, bl = a.splitlines(), b.splitlines()
    return [(i + 1, al[i], bl[i]) for i in range(min(len(al), len(bl))) if al[i] != bl[i]]


# ---------------------------------------------------------------- canonical gate
def run_gate(path: Path):
    gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    p = subprocess.run([sys.executable, str(gate), "--json", str(path)],
                       capture_output=True, text=True, timeout=300, cwd=str(ROOT))
    try:
        payload = json.loads(p.stdout)
    except Exception:
        payload = {"raw": p.stdout[-4000:], "stderr": p.stderr[-2000:]}
    failed = payload.get("failed_rules") if isinstance(payload, dict) else None
    return {"rc": p.returncode, "failed_rules": failed,
            "verdict": payload.get("verdict") if isinstance(payload, dict) else None,
            "stdout_tail": p.stdout[-1200:], "stderr_tail": p.stderr[-800:]}


# ---------------------------------------------------------------- main
def main() -> int:
    pins = {}
    drift = []
    for key, (name, want) in PINS.items():
        p = PIN / name
        got = sha256_file(p)
        pins[key] = {"path": f"pinned/{name}", "sha256": got, "expected": want, "match": got == want}
        if got != want:
            drift.append(key)
    if drift:
        print(json.dumps({"status": "blocked_pin_drift", "drift": drift}, indent=1))
        return 2

    live_txt = (PIN / "c0_live.yaml").read_text()
    c2_txt = (PIN / "c2_live.yaml").read_text()
    f1_txt = (PIN / "f1_live.yaml").read_text()
    corrected_txt = (PIN / "cand_corrected_51c253c4.yaml").read_text()
    nesting_txt = (PIN / "cand_nesting_4951cc96.yaml").read_text()
    circulating_txt = (PIN / "cand_circulating_84b5d3fa.yaml").read_text()
    patch_txt = (PIN / "patch_corrected.diff").read_text()

    # hash reproduction: live + corrected patch == staged corrected candidate
    reproduced = apply_unified_diff(live_txt, patch_txt)
    repro_sha = sha256_bytes(reproduced.encode())
    hash_repro = {
        "patch_applied_to": "pinned/c0_live.yaml#b2ab6acb2bbe",
        "result_sha256": repro_sha,
        "staged_corrected_sha256": pins["cand_corrected"]["sha256"],
        "reproduces": repro_sha == pins["cand_corrected"]["sha256"],
    }
    nesting_delta = diff_changed_lines(live_txt, nesting_txt)
    corrected_delta = diff_changed_lines(live_txt, corrected_txt)
    blast = {
        "corrected_changed_line_count": len(corrected_delta),
        "corrected_changed_line_numbers": [n for n, _, _ in corrected_delta],
        "nesting_changed_line_count": len(nesting_delta),
        "nesting_changed_line_numbers": [n for n, _, _ in nesting_delta],
        "h1_line_identical_between_candidates":
            corrected_delta[1][2] == nesting_delta[1][2] if len(corrected_delta) == 2 and len(nesting_delta) == 2 else None,
    }

    # primary runs
    docs = {}
    for key, txt, own, label in [
        ("live", live_txt, C0, "live_c0_b2ab6acb"),
        ("circulating", circulating_txt, C0, "circulating_84b5d3fa"),
        ("corrected", corrected_txt, C0, "corrected_51c253c4"),
        ("nesting", nesting_txt, C0, "nesting_only_4951cc96"),
        ("rev12_98f9ec83", (PIN / "cand_rev12_98f9ec83.yaml").read_text(), C0, "rev12_candidate_98f9ec83"),
        ("c2", c2_txt, C2, "c2_live_e9a27996"),
        ("f1", f1_txt, None, "f1_live_d9cebb94"),
    ]:
        d = yaml.safe_load(txt)
        cid = ((d.get("class_identity") or {}).get("class_id")) if isinstance(d, dict) else None
        own_eff = own or OWN_BY_CLASS.get(str(cid), "?")
        docs[key] = check_doc(d, own_eff, label)
        docs[key]["class_id"] = cid
        docs[key]["kind_set"] = sorted({f["id"] for f in docs[key]["findings"]})

    # controls (mutations are in-memory only)
    ctrl = []

    def ctl(cid, expected, observed):
        ctrl.append({"id": cid, "expected": expected, "observed": observed, "match": expected == observed})

    ctl("C1_live_both_defects", ["false_containment_denial", "size_premise_inverted"], docs["live"]["kind_set"])
    ctl("C2_corrected_clean", [], docs["corrected"]["kind_set"])
    ctl("C3_nesting_clean", [], docs["nesting"]["kind_set"])
    ctl("C4_circulating_inversion", ["entailment_direction_inverted"], docs["circulating"]["kind_set"])
    ctl("C5_rev12_candidate_inversion", ["entailment_direction_inverted"], docs["rev12_98f9ec83"]["kind_set"])
    ctl("C6_c2_sibling_clean", [], docs["c2"]["kind_set"])
    ctl("C7_f1_sibling_no_f2_defects", ["chain_missing"], docs["f1"]["kind_set"])

    mutated = corrected_txt.replace(
        "this class's conclusion (C0-inextendibility) therefore ENTAILS H2_loc-inextendibility",
        "H2_loc-inextendibility therefore ENTAILS C0-inextendibility")
    ctl("C8_mut_claim_direction_swapped", ["entailment_direction_inverted"],
        sorted({f["id"] for f in check_doc(yaml.safe_load(mutated), C0, "mut")["findings"]}))
    mutated = corrected_txt.replace("The extension sets are nonetheless nested",
                                    "No containment with C2 or C0 is asserted here; the extension sets are nonetheless nested")
    ctl("C9_mut_denial_reinserted", ["false_containment_denial"],
        sorted({f["id"] for f in check_doc(yaml.safe_load(mutated), C0, "mut")["findings"]}))
    mutated = corrected_txt.replace("C2 is a strictly smaller extension class", "C2 is a strictly larger extension class")
    ctl("C10_mut_size_premise_reinverted", ["size_premise_inverted"],
        sorted({f["id"] for f in check_doc(yaml.safe_load(mutated), C0, "mut")["findings"]}))
    reversed_chain = corrected_txt.replace("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                                           "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0")
    kinds = sorted({f["id"] for f in check_doc(yaml.safe_load(reversed_chain), C0, "mut")["findings"]})
    ctl("C11_mut_chain_reversed_expect_multiple", True,
        {"entailment_row_invalid", "size_premise_inverted"}.issubset(set(kinds)))
    gutted = {"class_identity": {"class_id": "AF-SCC-C0-VAC-GEN"}, "implication_ledger": {}}
    ctl("C12_gutted_chain_missing", ["chain_missing"],
        sorted({f["id"] for f in check_doc(gutted, C0, "mut")["findings"]}))
    # class-relativity: the identical sentence is TRUE in the C2 sibling and must be accepted there
    c2_sentence = ("H2_loc-inextendibility entails this class's conclusion")
    c2_doc = {"class_identity": {"class_id": "AF-SCC-C2-VAC-GEN"},
              "implication_ledger": yaml.safe_load(c2_txt)["implication_ledger"],
              "regularity": {"must_not_conflate": [c2_sentence]}}
    ctl("C13_class_relativity_c2_accepts", [], sorted({f["id"] for f in check_doc(c2_doc, C2, "ctl")["findings"]}))
    c0_doc = dict(c2_doc)
    c0_doc["class_identity"] = {"class_id": "AF-SCC-C0-VAC-GEN"}
    ctl("C14_class_relativity_c0_rejects", ["entailment_direction_inverted"],
        sorted({f["id"] for f in check_doc(c0_doc, C0, "ctl")["findings"]}))

    # canonical gate on live + three candidates (independent of the private checker)
    gate = {}
    for key, name in [("live", "c0_live.yaml"), ("circulating", "cand_circulating_84b5d3fa.yaml"),
                      ("corrected", "cand_corrected_51c253c4.yaml"), ("nesting", "cand_nesting_4951cc96.yaml")]:
        gate[key] = run_gate(PIN / name)

    acceptance = {
        "pins_all_match": all(v["match"] for v in pins.values()),
        "hash_reproduction": hash_repro["reproduces"],
        "live_yields_exactly_two_named_defects": docs["live"]["kind_set"] == ["false_containment_denial", "size_premise_inverted"],
        "corrected_is_finding_free": docs["corrected"]["kind_set"] == [],
        "nesting_is_finding_free": docs["nesting"]["kind_set"] == [],
        "circulating_introduces_inversion": "entailment_direction_inverted" in docs["circulating"]["kind_set"],
        "all_controls_match": all(c["match"] for c in ctrl),
    }
    core = {
        "task_id": "W029-F2B-REPAIR-CANDIDATE-VERIFY-01",
        "actor": "worker-029",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "pins": pins,
        "hash_reproduction": hash_repro,
        "candidate_edit_map": blast,
        "runs": {k: {"label": v["label"], "class_id": v["class_id"], "kind_set": v["kind_set"],
                     "checks": v["checks"], "findings": v["findings"]} for k, v in docs.items()},
        "controls": ctrl,
        "canonical_gate": gate,
        "acceptance": acceptance,
        "verdict": "revise" if not all(acceptance.values()) else "accept_candidate_ready_independent",
        "falsifier": ("Re-run this script on the same pinned bytes: falsified if any pin moves, if live does not yield "
                      "exactly {false_containment_denial, size_premise_inverted}, if candidate_corrected 51c253c4 or "
                      "candidate_nesting 4951cc96 yields any finding, if circulating 84b5d3fa does not yield "
                      "entailment_direction_inverted, if the class-relativity controls C13/C14 swap, if any other control "
                      "departs from its expectation, or if live+patch_corrected does not reproduce 51c253c4."),
    }
    (HERE / "report_core.json").write_text(json.dumps(core, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "acceptance": acceptance,
                      "live": docs["live"]["kind_set"],
                      "circulating": docs["circulating"]["kind_set"],
                      "corrected": docs["corrected"]["kind_set"],
                      "nesting": docs["nesting"]["kind_set"],
                      "gate": {k: v["rc"] for k, v in gate.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
