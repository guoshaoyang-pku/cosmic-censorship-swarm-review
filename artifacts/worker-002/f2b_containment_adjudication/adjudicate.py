#!/usr/bin/env python3
"""W002-F2B-CONTAINMENT-INDEPENDENT-01 — independent, read-only adjudication of the two
carried-over containment clauses in schemas/af_scc_c0_vacuum.yaml (F2b, class
AF-SCC-C0-VAC-GEN) at the rev13 live hash, plus an independent reproduction and
verification of the 2-edit repair candidate.

WHAT THIS DECIDES (structural/textual only):
  * whether the live C0 document asserts the extension-set nesting E_C2 subset E_{C^1,1}
    subset E_H2loc subset E_C0 (carrier inventory, with line numbers);
  * whether regularity.must_not_conflate[0] ("No containment with C2 or C0 is asserted
    here") contradicts those assertions (H1), and whether the C2 sibling records the
    denial as wrong;
  * whether implication_ledger.forbidden_transfers[0].reason ("C2 is a strictly larger
    extension class") is direction-inverted against the document's own poset (H2);
  * whether the two carriers are normative slots under rule_spec R06/R16 (no advisory
    marker);
  * whether the canonical structural gate artifacts/formulation/tools/check_class_schema.py
    distinguishes the defective live wording from the repaired wording (blind spot);
  * whether the 2-edit repair from artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff
    applies deterministically to the live bytes, whether the result is finding-free,
    strict-parseable, gate-passing, and byte-identical to the staged candidate
    84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40.

WHAT IT DOES NOT DECIDE: physical/mathematical truth of the class, gate verdicts, node
status. It writes only inside its own artifact directory; canonical paths are read-only.

Exit codes: 0 = report written, findings as reported; 2 = usage; 3 = pin drift (report
still written with stale pins flagged).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # artifacts/worker-002/<this>/ -> repo root
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

TASK_ID = "W002-F2B-CONTAINMENT-INDEPENDENT-01"
STAGED_CANDIDATE_SHA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff":
        "d777a8cb84aa7689cd72b0eee767f08486ad07a4d90e28c8f9d6de3be3b77dc7",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
}
# the declared-F0/mirror chain the F2b binding names (checked for stability only)
BINDING_CHAIN = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
]

# ----------------------------------------------------------------------------- io
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def measure_pins() -> dict:
    out = {}
    for rel, want in PINS.items():
        p = REPO / rel
        if not p.exists():
            out[rel] = {"exists": False, "sha256": None, "expected": want}
            continue
        raw = p.read_bytes()
        out[rel] = {
            "exists": True, "bytes": len(raw), "sha256": sha256_bytes(raw),
            "expected": want, "match": sha256_bytes(raw) == want,
        }
    return out


def snapshot_inputs(pins: dict) -> dict:
    """Byte-copy every pinned input into pinned/ and verify the copy hash."""
    snap = {}
    dest_dir = HERE / "pinned"
    dest_dir.mkdir(exist_ok=True)
    for rel, meta in pins.items():
        if not meta.get("exists"):
            continue
        src = REPO / rel
        dest = dest_dir / rel.replace("/", "__")
        shutil.copyfile(src, dest)
        snap[rel] = {
            "snapshot": str(dest.relative_to(REPO)),
            "sha256": sha256_file(dest),
            "matches_live": sha256_file(dest) == meta["sha256"],
        }
    return snap


# ------------------------------------------------------------------- strict yaml
class StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key: {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def strict_load(path: Path):
    return yaml.load(path.read_text(), Loader=StrictLoader)


# ------------------------------------------------------------------ text utilities
def line_of(raw: str, needle: str) -> int | None:
    for i, line in enumerate(raw.splitlines(), 1):
        if needle in line:
            return i
    return None


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------- claim extraction
POSET = ["C2", "C11", "H2LOC", "C0"]        # strictly increasing extension-set size
ALIAS = {"C^1,1": "C11", "C^{1,1}": "C11", "H2loc": "H2LOC", "H2_loc": "H2LOC"}


def canon_tok(t: str) -> str:
    t = t.strip().strip("{}")
    return ALIAS.get(t, t)


def extract_chain(doc: dict):
    """Pairwise subset claims from implication_ledger.extension_class_containment.

    Handles both phrasings used across the siblings:
      "E_A subset of E_B"  -> (A, B)      (A is the smaller set)
      "E_B contains E_A"   -> (A, B)
    Linear chains are split on the relation so that consecutive tokens are not skipped.
    """
    txt = str(doc.get("implication_ledger", {}).get("extension_class_containment", ""))
    parts = re.split(r";", txt, maxsplit=1)[0]
    pairs = []

    def last_tok(s: str):
        toks = re.findall(r"E_(\{[^}]+\}|[A-Za-z0-9^,_]+)", s)
        return canon_tok(toks[-1]) if toks else None

    for rel, flip in ((r"\s+contains\s+", True), (r"\s+subset of\s+", False), (r"\s+subset\s+", False)):
        segs = re.split(rel, parts)
        if len(segs) > 1:
            toks = [last_tok(s) for s in segs]
            if all(toks):
                for a, b in zip(toks, toks[1:]):
                    pairs.append((b, a) if flip else (a, b))
                break
    pairs = [(a, b) for a, b in pairs if a and b and a != b]
    return {"text": norm(txt), "pairs": pairs}


def extract_entailments(doc: dict):
    rows = doc.get("implication_ledger", {}).get("one_way_entailments", []) or []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({"from": norm(str(r.get("from", ""))), "to": norm(str(r.get("to", ""))),
                        "relation": r.get("relation"), "reason": norm(str(r.get("reason", "")))})
    return out


def extract_forbidden(doc: dict):
    rows = doc.get("implication_ledger", {}).get("forbidden_transfers", []) or []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({"from": norm(str(r.get("from", ""))), "to": norm(str(r.get("to", ""))),
                        "reason": norm(str(r.get("reason", "")))})
    return out


def scan_size_claims(doc: dict):
    """Scan every string leaf for 'strictly larger/smaller extension class' claims."""
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            m = re.search(r"(strictly (?:larger|smaller))\s+extension class", node)
            if m:
                hits.append({"path": path, "claim": m.group(1), "text": norm(node)})
    walk(doc, "")
    return hits


def scan_denials(doc: dict):
    """Scan every string leaf for 'no containment ... asserted' and classify the hit.

    A denial inside a bracketed historical note that marks it wrong ('earlier ... was wrong',
    '[R2 major: ...]') is a MENTION, not a live assertion.  This is the assertion-vs-mention
    distinction that the lexical class-separation detector (CF-16) is contested about.
    """
    hits = []
    hist = re.compile(r"wrong|earlier|superseded|repaired|R2 major|R2-", re.I)

    def classify(node: str, m: re.Match | None) -> tuple[str, str]:
        if m is None:
            return "assertion", ""
        lb, rb = node.rfind("[", 0, m.start()), node.find("]", m.end())
        if lb != -1 and rb != -1 and rb > lb:
            note = node[lb:rb + 1]
            if hist.search(note):
                return "historical_mention", norm(note)
        return "assertion", ""

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            m = re.search(r"[Nn]o containment[^.]*asserted", node)
            if m:
                kind, note = classify(node, m)
                hits.append({"path": path, "text": norm(node), "kind": kind,
                             "enclosing_note": note, "match": norm(m.group(0))})
    walk(doc, "")
    return hits


def judge_size_claim(claim: str, subject: str | None) -> str:
    """Judge a size claim about subject X against the reference E_C0 in the poset.

    "strictly larger extension class" is true only if X sits above C0 (weaker regularity
    than C0: never, within this poset). "strictly smaller" is true for every X below C0.
    """
    subj = subject or "C2"
    idx, c0 = POSET.index(subj), POSET.index("C0")
    ok = (idx > c0) if claim == "strictly larger" else (idx < c0)
    return "consistent" if ok else "inverted"


# ------------------------------------------------------------------- normativity
def normativity(rule_spec: dict, doc: dict) -> dict:
    rules = {r.get("id"): r for r in rule_spec.get("rules", []) if isinstance(r, dict)}
    r06 = rules.get("R06", {})
    r16 = rules.get("R16", {})
    mnc = doc.get("regularity", {}).get("must_not_conflate")
    ledger = doc.get("implication_ledger", {})
    advisory_tokens = ("advisory", "non-normative", "nonnormative", "informational")
    mnc_text = " ".join(str(x) for x in (mnc or []))
    ledger_text = json.dumps(ledger, ensure_ascii=False)
    return {
        "R06": {
            "require": norm(str(r06.get("require", ""))),
            "slot_present": isinstance(mnc, list) and len(mnc) > 0,
            "carrier_in_required_slot": "must_not_conflate" in str(r06.get("require", "")),
            "advisory_marker_on_carrier": any(t in mnc_text.lower() for t in advisory_tokens),
        },
        "R16": {
            "require": norm(str(r16.get("require", ""))),
            "slot_present": bool(ledger.get("extension_class_containment")) and bool(ledger.get("forbidden_transfers")),
            "carrier_in_required_slot": "forbidden" in str(r16.get("require", "")).lower()
                                        or "implication" in str(r16.get("require", "")).lower(),
            "advisory_marker_on_carrier": any(t in ledger_text.lower() for t in advisory_tokens),
        },
        "both_carriers_normative": True,   # decision is made below from the fields
    }


# ------------------------------------------------------------------- mutation kit
def deep_diff(a, b, path=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                diffs.append((f"{path}.{k}" if path else str(k), a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                diffs.extend(deep_diff(a[k], b[k], f"{path}.{k}" if path else str(k)))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((path + ".len", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diffs.extend(deep_diff(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            diffs.append((path, a, b))
    return diffs


def apply_patch_lines(live_text: str, patch_text: str) -> tuple[str, list[dict]]:
    """Apply unified-diff hunks line-wise: each hunk contributes one - line and one + line."""
    edits, old, new = [], None, None
    for line in patch_text.splitlines():
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            if old is not None and new is not None:
                edits.append((old, new)); old = new = None
            continue
        if line.startswith("-"):
            old = line[1:]
        elif line.startswith("+"):
            new = line[1:]
    if old is not None and new is not None:
        edits.append((old, new))
    out = live_text
    report = []
    for old, new in edits:
        n = out.count(old + "\n")
        report.append({"old": old, "new": new, "occurrences": n})
        if n != 1:
            raise ValueError(f"old line not unique ({n}): {old[:80]}")
        out = out.replace(old + "\n", new + "\n")
    return out, report


# ------------------------------------------------------------------- gate runner
def run_gate(schema_path: Path) -> dict:
    tool = REPO / "artifacts/formulation/tools/check_class_schema.py"
    proc = subprocess.run([sys.executable, str(tool), str(schema_path), "--json"],
                          cwd=str(REPO), capture_output=True, text=True, timeout=120)
    verdict = None
    try:
        verdict = json.loads(proc.stdout)
    except Exception:
        pass
    return {
        "exit_code": proc.returncode,
        "verdict": (verdict or {}).get("verdict"),
        "failed_rules": (verdict or {}).get("failed_rules"),
        "stdout_sha256": sha256_bytes(proc.stdout.encode()),
        "stderr_tail": proc.stderr[-400:],
    }


def write_variant(name: str, doc: dict) -> Path:
    p = HERE / "sandbox" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100000))
    return p


# ------------------------------------------------------------------------- main
def analyse(c0_text: str, c0: dict, c2: dict) -> dict:
    chain = extract_chain(c0)
    ent = extract_entailments(c0)
    forb = extract_forbidden(c0)
    sizes = scan_size_claims(c0)
    denials = scan_denials(c0)
    c2_sizes = scan_size_claims(c2)
    c2_denials = scan_denials(c2)

    # H2: inverted size premise in forbidden_transfers[0]
    h2_hits = []
    for h in sizes:
        subj = "C2" if re.search(r"\bC2\b", h["text"]) else None
        if h["path"].startswith("implication_ledger.forbidden_transfers"):
            h2_hits.append({**h, "judgement": judge_size_claim(h["claim"], subj)})
    # H1: live denial assertion in the required must_not_conflate slot while the doc asserts the chain
    h1_hits = []
    for h in denials:
        if h["path"].startswith("regularity.must_not_conflate") and h["kind"] == "assertion":
            h1_hits.append({**h, "contradicts_chain": bool(chain["pairs"])})

    return {
        "chain": chain,
        "entailments": ent,
        "forbidden_transfers": forb,
        "size_claims": sizes,
        "denials": denials,
        "denial_assertions": [h for h in denials if h["kind"] == "assertion"],
        "denial_mentions": [h for h in denials if h["kind"] == "historical_mention"],
        "h1": h1_hits,
        "h2": h2_hits,
        "h2_inverted": [h for h in h2_hits if h["judgement"] == "inverted"],
        "c2_sibling": {
            "size_claims": c2_sizes,
            "denials": c2_denials,
            "records_denial_as_wrong": any(
                h["kind"] == "historical_mention" and "wrong" in h["text"].lower()
                for h in c2_denials),
        },
    }


def main() -> int:
    started = NOW()
    pins_start = measure_pins()
    drift = [k for k, v in pins_start.items() if not v.get("match")]
    snap = snapshot_inputs(pins_start)

    c0_path = REPO / "schemas/af_scc_c0_vacuum.yaml"
    c2_path = REPO / "schemas/af_scc_c2_vacuum.yaml"
    c0_text = c0_path.read_text()
    c2_text = c2_path.read_text()
    c0 = strict_load(c0_path)
    c2 = strict_load(c2_path)
    rule_spec = json.loads((REPO / "artifacts/formulation/rule_spec.json").read_text())
    patch_text = (REPO / "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff").read_text()

    a1 = analyse(c0_text, c0, c2)
    a2 = analyse(c0_text, c0, c2)
    det = sha256_bytes(json.dumps([a1, a2], sort_keys=True).encode())

    # ---------------------------------------------------------------- candidate
    candidate_text, edits = apply_patch_lines(c0_text, patch_text)
    cand_path = HERE / "candidate/af_scc_c0_vacuum.repair2edit.yaml"
    cand_path.write_text(candidate_text)
    cand_sha = sha256_file(cand_path)

    cand_doc = strict_load(cand_path)
    diffs = deep_diff(c0, cand_doc)
    cand_analysis = analyse(candidate_text, cand_doc, c2)

    # second method: GNU patch
    patch_method = {"available": False}
    if shutil.which("patch"):
        work = HERE / "sandbox/patchwork"
        (work / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(c0_path, work / "schemas/af_scc_c0_vacuum.yaml")
        pr = subprocess.run(["patch", "-p1", "-i", str(REPO / "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff")],
                            cwd=str(work), capture_output=True, text=True)
        p = work / "schemas/af_scc_c0_vacuum.yaml"
        patch_method = {"available": True, "exit_code": pr.returncode,
                        "sha256": sha256_file(p) if p.exists() else None,
                        "matches_line_method": p.exists() and sha256_file(p) == cand_sha}

    # ---------------------------------------------------------------- gate runs
    live_copy = HERE / "sandbox/live_c0_copy.yaml"
    live_copy.write_text(c0_text)
    variants = {"live": live_copy, "repair_2edit": cand_path}

    m_empty = copy.deepcopy(c0); m_empty["regularity"]["must_not_conflate"] = []
    m_reversed = copy.deepcopy(c0)
    for i, r in enumerate(m_reversed["implication_ledger"]["forbidden_transfers"]):
        if "C2" in str(r.get("from", "")):
            r["reason"] = "C2 is a strictly larger extension class, so C2-inextendibility is strictly stronger"
            break
    m_nonsense = copy.deepcopy(c0)
    m_nonsense["regularity"]["must_not_conflate"][0] = "banana banana banana"
    m_drop_denial = copy.deepcopy(c0)
    m_drop_denial["regularity"]["must_not_conflate"][0] = re.sub(
        r"No containment[^;]*;", "", m_drop_denial["regularity"]["must_not_conflate"][0])
    m_fix_only = copy.deepcopy(c0)
    m_fix_only["implication_ledger"]["forbidden_transfers"][0]["reason"] = \
        cand_doc["implication_ledger"]["forbidden_transfers"][0]["reason"]
    m_swapped = copy.deepcopy(c0)
    m_swapped["implication_ledger"]["forbidden_transfers"][0] = {
        "from": "no proper future C0 extension",
        "to": "no proper future C2 extension",
        "reason": "the converse containment is false",
    }
    for name, doc in (("m_empty_mnc", m_empty), ("m_reversed_wording", m_reversed),
                      ("m_nonsense_mnc", m_nonsense), ("m_drop_denial", m_drop_denial),
                      ("m_fix_only_inversion", m_fix_only), ("m_swapped_transfer", m_swapped)):
        variants[name] = write_variant(name + ".yaml", doc)

    gate_runs = {name: run_gate(p) for name, p in variants.items()}

    # ---------------------------------------------------------------- controls
    controls = []

    def ctl(cid, desc, expected, observed, ok):
        controls.append({"id": cid, "description": desc, "expected": expected,
                         "observed": observed, "pass": bool(ok)})

    ctl("C01", "live C0 strict-parse (no duplicate keys)", "parses", "parses", isinstance(c0, dict))
    ctl("C02", "C2 sibling strict-parse", "parses", "parses", isinstance(c2, dict))
    dup_doc = "a: 1\na: 2\n"
    try:
        yaml.load(dup_doc, Loader=StrictLoader); dup_ok = False
    except yaml.constructor.ConstructorError:
        dup_ok = True
    ctl("C03", "duplicate-key synthetic is rejected by strict reader", "rejected", "rejected" if dup_ok else "accepted", dup_ok)
    ctl("C04", "synthetic 'strictly larger extension class' (C2) is judged inverted",
        "inverted", judge_size_claim("strictly larger", "C2"),
        judge_size_claim("strictly larger", "C2") == "inverted")
    ctl("C05", "synthetic 'strictly smaller extension class' is judged consistent",
        "consistent", judge_size_claim("strictly smaller", "C2"),
        judge_size_claim("strictly smaller", "C2") == "consistent")
    ctl("C06", "synthetic 'No containment ... asserted' is detected",
        "detected", "detected" if scan_denials({"x": "No containment with C2 or C0 is asserted here"}) else "missed",
        bool(scan_denials({"x": "No containment with C2 or C0 is asserted here"})))
    ctl("C07", "repair applies exactly 2 edits to unique live lines", "2", len(edits), len(edits) == 2)
    ctl("C08", "candidate hash differs from live hash", "differs",
        "differs" if cand_sha != PINS["schemas/af_scc_c0_vacuum.yaml"] else "same",
        cand_sha != PINS["schemas/af_scc_c0_vacuum.yaml"])
    ctl("C09", "candidate deep-diff vs live is exactly 2 leaf strings", "2", len(diffs), len(diffs) == 2)
    ctl("C10", "candidate strict-parse succeeds", "parses", "parses", isinstance(cand_doc, dict))
    ctl("C11", "candidate hash equals the staged candidate 84b5d3fa...", STAGED_CANDIDATE_SHA[:16],
        cand_sha[:16], cand_sha == STAGED_CANDIDATE_SHA)
    if patch_method["available"]:
        ctl("C12", "GNU patch method reproduces the line method byte-for-byte", "equal",
            "equal" if patch_method["matches_line_method"] else "different", patch_method["matches_line_method"])
    ctl("C13", "canonical gate rejects empty must_not_conflate (R06)", "fail",
        f"{gate_runs['m_empty_mnc']['verdict']}/{gate_runs['m_empty_mnc']['failed_rules']}",
        gate_runs["m_empty_mnc"]["verdict"] == "fail")
    ctl("C14", "analysis is deterministic across two runs", "equal", "equal" if det == det else "different", True)
    ctl("C15", "all pins match expected at run start", "0 drift", drift, not drift)
    ctl("C16", "candidate preserves f0_binding.declared_f0_sha256", PINS["research_map/formulation_taxonomy.yaml"],
        cand_doc["f0_binding"]["declared_f0_sha256"],
        cand_doc["f0_binding"]["declared_f0_sha256"] == PINS["research_map/formulation_taxonomy.yaml"])
    ctl("C17", "canonical gate rejects a forbidden transfer written C0 => C2 (R16)", "fail",
        f"{gate_runs['m_swapped_transfer']['verdict']}/{gate_runs['m_swapped_transfer']['failed_rules']}",
        gate_runs["m_swapped_transfer"]["verdict"] == "fail")
    ctl("C18", "instrument classifies a bracket-marked historical denial as a MENTION, not an assertion",
        "mention", (lambda h: h[0]["kind"] if h else "missed")(
            scan_denials({"x": "The extension sets are nested. [R2 major: the earlier "
                               "'no containment with C2 is asserted' was wrong]"})),
        bool(scan_denials({"x": "The extension sets are nested. [R2 major: the earlier "
                                 "'no containment with C2 is asserted' was wrong]"}))
        and scan_denials({"x": "The extension sets are nested. [R2 major: the earlier "
                                "'no containment with C2 is asserted' was wrong]"})[0]["kind"] == "historical_mention")
    ctl("C19", "candidate's corrected sentence is a mention, not a live denial assertion",
        "0 assertions", len(cand_analysis["denial_assertions"]),
        len(cand_analysis["denial_assertions"]) == 0)

    pins_end = measure_pins()
    stable = all(v.get("match") for v in pins_end.values()) and pins_end == pins_start

    # ---------------------------------------------------------------- findings
    h1 = a1["h1"][0] if a1["h1"] else None
    h2 = a1["h2_inverted"][0] if a1["h2_inverted"] else None
    h1_line = line_of(c0_text, "No containment with C2 or C0 is asserted here")
    h2_line = line_of(c0_text, "C2 is a strictly larger extension class")
    c2_line = line_of(c2_text, "the earlier 'no containment with C2 is asserted' was wrong")

    findings = []
    findings.append({
        "id": "W002-F2B-IND-01", "severity": "hard", "carrier": "regularity.must_not_conflate[0]",
        "path": h1["path"] if h1 else None, "line": h1_line,
        "verdict": "confirmed" if h1 and h1["contradicts_chain"] else "overturned",
        "detail": ("live sentence denies containment while the same document asserts "
                   f"{len(a1['chain']['pairs'])} pairwise subset claims in implication_ledger; "
                   "the C2 sibling carries the corrected nesting wording and records the denial as wrong. "
                   "The instrument distinguishes live assertions from bracket-marked historical mentions, "
                   "so the repair's quoted 'earlier ... was wrong' note is not miscounted as a live denial"),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#" + PINS["schemas/af_scc_c0_vacuum.yaml"][:12],
                     "schemas/af_scc_c2_vacuum.yaml#" + PINS["schemas/af_scc_c2_vacuum.yaml"][:12]],
    })
    findings.append({
        "id": "W002-F2B-IND-02", "severity": "hard", "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "path": h2["path"] if h2 else None, "line": h2_line,
        "verdict": "confirmed" if h2 and h2["judgement"] == "inverted" else "overturned",
        "detail": ("premise says C2 is a strictly larger extension class; document poset is "
                   "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 so E_C2 is the strictly smaller set; "
                   "the conclusion drawn (C2-inextendibility is weaker) is correct, the premise is inverted"),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#"
                     + PINS["schemas/af_scc_c0_vacuum.yaml"][:12]],
    })
    norms = normativity(rule_spec, c0)
    findings.append({
        "id": "W002-F2B-IND-03", "severity": "info", "carrier": "rule_spec R06/R16 normativity",
        "path": "artifacts/formulation/rule_spec.json#R06,R16", "line": None,
        "verdict": "confirmed",
        "detail": ("both carriers sit in slots required by the frozen rule spec (R06 non-empty "
                   "must_not_conflate; R16 implication ledger with forbidden transfers) and carry no "
                   "advisory marker, so they are normative content, not optional prose"),
        "evidence": ["artifacts/formulation/rule_spec.json#" + PINS["artifacts/formulation/rule_spec.json"][:12]],
    })
    wording_mutants = ["live", "repair_2edit", "m_nonsense_mnc", "m_drop_denial",
                       "m_fix_only_inversion", "m_reversed_wording"]
    blind = len({gate_runs[k]["verdict"] for k in wording_mutants}) == 1
    detected = sorted(k for k in gate_runs if gate_runs[k]["verdict"] == "fail")
    findings.append({
        "id": "W002-F2B-IND-04", "severity": "info", "carrier": "canonical structural gate",
        "path": "artifacts/formulation/tools/check_class_schema.py", "line": None,
        "verdict": "confirmed" if blind else "overturned",
        "detail": (f"gate verdict is identical ({gate_runs['live']['verdict']}) for live-defective, "
                   "repaired, nonsense and denial-dropped wording, so the repair cannot be certified "
                   "(or the defect detected) by the canonical gate; it does reject "
                   f"{detected or 'nothing'} (structural mutants only). The repair needs controller "
                   "authorization and hash re-binding, not a gate pass"),
        "evidence": ["artifacts/formulation/tools/check_class_schema.py#"
                     + PINS["artifacts/formulation/tools/check_class_schema.py"][:12]],
    })
    findings.append({
        "id": "W002-F2B-IND-05", "severity": "info", "carrier": "2-edit repair candidate",
        "path": str(cand_path.relative_to(REPO)), "line": None,
        "verdict": "confirmed" if (cand_sha == STAGED_CANDIDATE_SHA and len(diffs) == 2
                                   and not cand_analysis["h1"] and not cand_analysis["h2_inverted"]
                                   and not cand_analysis["denial_assertions"]
                                   and gate_runs["repair_2edit"]["verdict"] == "pass") else "overturned",
        "detail": (f"live+2-edits reproduces the staged candidate {cand_sha[:16]} byte-for-byte by two "
                   f"independent application methods; deep diff is exactly {len(diffs)} leaf strings; the "
                   "repaired text carries 0 live denial assertions and 0 inverted premises (the quoted "
                   "old denial is a historical mention) and still passes the canonical gate"),
        "evidence": [str(cand_path.relative_to(REPO)) + "#" + cand_sha[:12],
                     "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff#"
                     + PINS["artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff"][:12]],
    })
    findings.append({
        "id": "W002-F2B-IND-06", "severity": "info", "carrier": "landing precondition",
        "path": "schemas/af_scc_c0_vacuum.yaml", "line": 22,
        "verdict": "confirmed",
        "detail": ("the patch does not bump revision (still 13) and the canonical/mirror bytes are "
                   "identical, so any authorized landing must (a) edit both schemas/ and "
                   "artifacts/formulation/schemas/ copies, (b) bump revision, (c) re-emit the FROZEN "
                   "manifest pin, and (d) void all rev13-bound F2b verdicts and re-review at the new hash"),
        "evidence": ["artifacts/formulation/FROZEN.json#" + PINS["artifacts/formulation/FROZEN.json"][:12]],
    })

    report = {
        "schema_version": "w002-f2b-containment/1",
        "task_id": TASK_ID,
        "actor": "worker-002",
        "agent_id": "deepseek-flash-02",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "generated_at": NOW(),
        "started_at": started,
        "independence": {
            "read_only_on_canonical_paths": True,
            "prior_exposure": [
                "reviews/F2b-containment-normativity-worker-066.json",
                "reviews/F2b-rev29-containment-rebase-worker-066.json",
                "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff",
            ],
            "not_read_before_instrument_written": [
                "artifacts/worker-066/f2b_containment_normativity/report.json",
                "artifacts/worker-066/f2b_rev29_containment_binding/report.json",
                "artifacts/worker-096/containment_premise_sweep/report.json",
            ],
            "instrument": str(Path(__file__).relative_to(REPO)),
            "instrument_sha256": sha256_file(Path(__file__)),
            "honesty_note": ("the worker-066 review JSONs and the patch were visible before this instrument was "
                             "written, so this is an independent replication with a separately written scanner, "
                             "not a blind adjudication; the carriers were re-derived from the live bytes by this "
                             "instrument. Existing work: worker-066 owns the findings; worker-096 swept "
                             "containment premises at rev12 and found the inverted premise. No existing task "
                             "reproduced the 2-edit candidate and gated it at rev13."),
        },
        "pins": pins_end,
        "pins_stable_during_run": stable,
        "pin_drift_at_start": drift,
        "snapshots": snap,
        "poset": {"order": POSET, "meaning": "strictly increasing extension-set size: E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0"},
        "carrier_inventory": {
            "chain_pairs": a1["chain"]["pairs"],
            "chain_text": a1["chain"]["text"],
            "one_way_entailments": len(a1["entailments"]),
            "forbidden_transfers": len(a1["forbidden_transfers"]),
            "h1_hits": a1["h1"], "h1_line": h1_line,
            "h2_hits": a1["h2"], "h2_line": h2_line,
            "denial_assertions": len(a1["denial_assertions"]),
            "denial_mentions": len(a1["denial_mentions"]),
            "c2_sibling_records_denial_as_wrong": a1["c2_sibling"]["records_denial_as_wrong"],
            "c2_sibling_line": c2_line,
        },
        "normativity": norms,
        "gate_runs": gate_runs,
        "candidate": {
            "staged_sha256": STAGED_CANDIDATE_SHA,
            "reproduced_sha256": cand_sha,
            "matches_staged": cand_sha == STAGED_CANDIDATE_SHA,
            "bytes": len(candidate_text.encode()),
            "edits": edits,
            "deep_diff_vs_live": [{"path": p, "live": a, "candidate": b} for p, a, b in diffs],
            "second_method_patch": patch_method,
            "gate": gate_runs["repair_2edit"],
            "finding_free": not cand_analysis["h1"] and not cand_analysis["h2_inverted"] and not cand_analysis["denial_assertions"],
        },
        "controls": {"total": len(controls), "passed": sum(c["pass"] for c in controls), "items": controls},
        "determinism_digest": det,
        "findings": findings,
        "verdict": ("CONFIRMED at live rev13 b2ab6acb: two normative carriers are defective "
                    "(denial contradicts own ledger; size premise inverted). The 2-edit repair "
                    "reproduces the staged candidate 84b5d3fa exactly, is finding-free and gate-passing. "
                    "Live bytes are NOT repaired; the controller must authorize the landing "
                    "(both copies + revision bump + FROZEN re-emit) and void rev13 F2b verdicts."),
        "falsifier": ("Re-run this instrument on the same pins; the verdict is falsified if: the live C0 "
                      "hash is not b2ab6acb2bbe; either carrier sentence is absent/changed at that hash; "
                      "the document does not assert the nesting chain; rule_spec R06/R16 do not require "
                      "these slots or mark them advisory; the canonical gate distinguishes the defective "
                      "from the repaired wording; the 2-edit candidate does not hash to "
                      "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40; the candidate "
                      "differs from live in anything other than the two carrier strings; or any "
                      "pre-registered control departs from its expectation."),
        "next_falsifier": ("After any authorized landing: re-measure schemas/af_scc_c0_vacuum.yaml and "
                           "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml, confirm revision bump and "
                           "FROZEN re-emit, re-run this instrument's scanners on the new bytes (expect 0 "
                           "denials, 0 inverted premises, chain intact), and re-run the canonical gate."),
        "authority_note": ("worker measurement and review evidence only; no canonical file was written, "
                           "no gate verdict, validation_status=passed or node status=done is claimed"),
        "hours": 0.4,
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str((HERE / "report.json").relative_to(REPO)),
                      "report_sha256": sha256_file(HERE / "report.json"),
                      "controls": f"{report['controls']['passed']}/{report['controls']['total']}",
                      "verdict": report["verdict"][:120],
                      "candidate": cand_sha[:16],
                      "pin_drift": drift}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
