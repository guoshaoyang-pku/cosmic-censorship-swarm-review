#!/usr/bin/env python3
"""W096-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-01.

Independent, non-author, read-only verification of the staged F2b repair candidates
against the live F2b rev13 bytes (schemas/af_scc_c0_vacuum.yaml sha256 b2ab6acb2bbe)
and the live FROZEN rev29 manifest (artifacts/formulation/FROZEN.json 815e08079aef).

Method (written from scratch; worker-080's harness and worker-022/worker-100 artifacts
are NOT imported or executed):
  1. Strict duplicate-key-aware YAML load of every input; sha256 pins measured and
     re-measured at the end (drift is fatal, exit 2).
  2. The document's OWN containment chain is parsed into a set order; every normative
     sentence that fixes a size premise, asserts/denies containment, or states an
     entailment direction is adjudicated against that order, class-relatively
     ("this class" resolves through class_components.regularity_token).
  3. Live defects and repair-introduced defects are separated by carrier
     (regularity.must_not_conflate[0], implication_ledger.forbidden_transfers[0].reason).
  4. Candidate deltas are computed as changed YAML leaf paths against live and must be
     a subset of the declared two carriers; line diff must be exactly two lines.
  5. The canonical structural gate (artifacts/formulation/tools/check_class_schema.py)
     is run as corroboration on snapshot copies only.
  6. Planted controls must fire; a control that does not fire is a harness failure.

Read-only on every canonical path. No gate verdict, no node status, no promotion.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ART = HERE

TASK_ID = "W096-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"

# ---------------------------------------------------------------- declared pins
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}

CANDIDATES = {
    "candidate_corrected": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
        "declared": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
        "author": "worker-080",
    },
    "candidate_nesting_only": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
        "declared": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
        "author": "worker-080",
    },
    "candidate_84b5d3fa": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
        "declared": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
        "author": "worker-066/worker-008",
    },
    "candidate_worker022": {
        "path": "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
        "declared": "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757",
        "author": "worker-022",
    },
}

LIVE_PATH = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_PATH = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
C2_PATH = "schemas/af_scc_c2_vacuum.yaml"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"

ALLOWED_CHANGED_PATHS = {
    "regularity.must_not_conflate[0]",
    "implication_ledger.forbidden_transfers[0].reason",
}

# ---------------------------------------------------------------- yaml (strict)
class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(
                f"duplicate mapping key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_doc(path: Path):
    text = path.read_text(encoding="utf-8")
    doc = yaml.load(text, Loader=StrictLoader)
    return doc, text, text.splitlines()


def walk_strings(node, prefix=""):
    """Yield (path, text) for every string leaf; path uses [i] for list items."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{prefix}[{i}]")
    elif isinstance(node, str):
        yield prefix, node


def diff_leaf_paths(a, b, prefix=""):
    """Changed leaf paths between two parsed documents."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{prefix}.{k}" if prefix else str(k)
            if k not in a or k not in b:
                out.append(p)
            else:
                out.extend(diff_leaf_paths(a[k], b[k], p))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(prefix or "<root>")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out.extend(diff_leaf_paths(x, y, f"{prefix}[{i}]"))
    elif type(a) is not type(b) or a != b:
        out.append(prefix or "<root>")
    return out


# ---------------------------------------------------------------- token order
def norm_token(tok: str) -> str:
    t = tok.strip().strip("{}").replace("\\", "").replace(" ", "").strip(",")
    t = t.replace("H2_loc", "H2loc").replace("H2loc", "H2loc")
    t = t.replace("C^{1,1}", "C^1,1").replace("C1,1", "C^1,1")
    return t


def parse_order_from_chain(chain: str):
    """Parse 'E_A contains E_B contains ...' -> [A, B, ...] largest set first."""
    toks = []
    for m in re.finditer(r"E_\{([^}]*)\}|E_([A-Za-z0-9,^]+)", chain):
        raw = m.group(1) or m.group(2)
        t = norm_token(raw)
        if t and (not toks or toks[-1] != t):
            toks.append(t)
    if len(toks) >= 2 and "contains" in chain:
        return toks
    return None


def parse_subset_order(chain: str):
    """Parse 'E_A subset of E_B subset of ...' -> [A, B, ...] smallest set first."""
    pairs = re.findall(r"E_\{([^}]*)\}|E_([A-Za-z0-9,^]+)", chain)
    toks = [norm_token(a or b) for a, b in pairs]
    toks = [t for t in toks if t]
    if len(toks) >= 2 and re.search(r"subset\s+of", chain):
        return toks
    return None


def _in_brackets(text: str, start: int) -> bool:
    """True if offset start sits inside a [...] meta-audit annotation."""
    return text.rfind("[", 0, start) > text.rfind("]", 0, start)


def _in_single_quotes(text: str, start: int) -> bool:
    """Quote-state machine that does not treat apostrophes in words as quotes."""
    state = False
    for i in range(start):
        if text[i] != "'":
            continue
        prev = text[i - 1] if i > 0 else " "
        nxt = text[i + 1] if i + 1 < len(text) else " "
        if not state and (prev.isspace() or prev in "([{:"):
            if not nxt.isspace():
                state = True
        elif state and (nxt.isspace() or nxt in ".,;:)]}"):
            state = False
    return state


def _metalinguistic(text: str, start: int, end: int) -> bool:
    """A quoted/bracketed mention of a defect phrase is not an assertion of it."""
    if _in_brackets(text, start) or _in_single_quotes(text, start):
        return True
    prefix = text[max(0, start - 30) : start].lower()
    return any(
        marker in prefix
        for marker in ("the earlier", "the phrase", "previously", "quoted", "instead of")
    )


def idx_of(order, token):
    try:
        return order.index(token)
    except ValueError:
        return None


# ---------------------------------------------------------------- detectors
def normative_strings(doc):
    keys = (
        "must_not_conflate",
        "forbidden_weakenings",
        "forbidden_transfers",
        "one_way_entailments",
        "subsumption_note",
        "extension_class_containment",
        "cross_family",
        "conclusion",
    )
    for path, text in walk_strings(doc):
        if any(k in path for k in keys):
            yield path, text


def find_containment_denials(doc):
    """Normative sentences denying containment the document itself asserts."""
    chain = None
    for path, text in walk_strings(doc):
        if path.endswith("implication_ledger.extension_class_containment"):
            chain = text
    if not chain or not ("contains" in chain or "subset of" in chain):
        return []
    hits = []
    for path, text in normative_strings(doc):
        for m in re.finditer(r"(?i)\bno\s+containment\b", text):
            if _metalinguistic(text, m.start(), m.end()):
                continue
            hits.append(
                {
                    "id": "containment_denial",
                    "severity": "hard",
                    "path": path,
                    "excerpt": text[:220],
                    "against": chain[:160],
                }
            )
    return hits


def find_size_premises(doc, order, own_token):
    """'X is a strictly larger/smaller extension class' checked against the chain."""
    hits = []
    for path, text in normative_strings(doc):
        for m in re.finditer(
            r"(?i)\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class",
            text,
        ):
            if _metalinguistic(text, m.start(), m.end()):
                continue
            tok = norm_token(m.group(1))
            claim = m.group(2).lower()
            i_tok, i_own = idx_of(order, tok), idx_of(order, own_token)
            ok = None
            if i_tok is not None and i_own is not None:
                # lower index = larger extension set
                ok = (i_tok < i_own) if claim == "larger" else (i_tok > i_own)
            hits.append(
                {
                    "id": "size_premise_inverted" if ok is False else "size_premise_ok",
                    "severity": "hard" if ok is False else "info",
                    "path": path,
                    "token": tok,
                    "claim": claim,
                    "order": order,
                    "own_token": own_token,
                    "consistent": ok,
                    "excerpt": m.group(0),
                }
            )
    return hits


def find_subset_claims(doc, order):
    """Declared 'E_A subset of E_B' pairs checked against the ledger chain order."""
    hits = []
    for path, text in normative_strings(doc):
        if text.lstrip().startswith("[") and text.rstrip().endswith("]"):
            continue
        toks = parse_subset_order(text)
        if not toks:
            continue
        idxs = [idx_of(order, t) for t in toks]
        ok = all(i is not None for i in idxs) and all(
            a > b for a, b in zip(idxs, idxs[1:])
        )
        hits.append(
            {
                "id": "subset_order_ok" if ok else "subset_order_inverted",
                "severity": "info" if ok else "hard",
                "path": path,
                "declared_small_to_large": toks,
                "declared_indices_largest_first": idxs,
                "consistent": ok,
            }
        )
    return hits


def find_entailment_rows(doc, order, own_token):
    """implication_ledger.one_way_entailments rows: from-inext entails to-inext."""
    hits = []
    ledger = doc.get("implication_ledger", {})
    rows = ledger.get("one_way_entailments", []) if isinstance(ledger, dict) else []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        src_tok = _first_token(str(row.get("from", "")))
        dst_tok = _first_token(str(row.get("to", "")))
        if src_tok is None or dst_tok is None:
            continue
        i_s, i_d = idx_of(order, src_tok), idx_of(order, dst_tok)
        ok = None if (i_s is None or i_d is None) else (i_s <= i_d)
        hits.append(
            {
                "id": "entailment_row_ok" if ok else "entailment_row_inverted",
                "severity": "info" if ok else "hard",
                "path": f"implication_ledger.one_way_entailments[{i}]",
                "from": row.get("from"),
                "to": row.get("to"),
                "src": src_tok,
                "dst": dst_tok,
                "relation": row.get("relation"),
                "consistent": ok,
            }
        )
    return hits


TOKEN_IN_TEXT = re.compile(r"(C0|C2|H2_?loc|C\^?\{?1,1\}?)")


def _first_token(text):
    m = TOKEN_IN_TEXT.search(text)
    return norm_token(m.group(1)) if m else None


DIRECTION_SRC = re.compile(r"(?i)\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)[- ]inextendibility")
ENTAIL = re.compile(r"(?i)(\bENTAILS\b|\bentails\b|\bimplies\b|=>)")


def _dst_token(fragment, own_token):
    if re.search(r"(?i)this\s+class'?s?\s+conclusion", fragment):
        return own_token
    m = re.search(
        r"(?i)\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)\s+(?:sibling'?s?\s+)?conclusion", fragment
    )
    if m:
        return norm_token(m.group(1))
    m = re.search(r"(?i)\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)[- ]inextendibility", fragment)
    if m:
        return norm_token(m.group(1))
    return None


def find_direction_claims(doc, order, own_token):
    """Every 'A-inext ... entails ... B' statement adjudicated against the chain order.

    Rule (derived from the document's own order, largest set first):
    A-inext entails B-inext  iff  E_A subset-of-or-equal E_B  iff  idx(A) >= idx(B).
    """
    hits = []
    for path, text in normative_strings(doc):
        # pass A: "A-inext ... ENTAILS ... dst"
        for m in re.finditer(
            r"(?i)(C0|C2|H2_?loc|C\^?\{?1,1\}?)[- ]inextendibility((?:(?!\b(?:C0|C2|H2_?loc)[- ]inextendibility).){0,90}?)(\bENTAILS\b|\bentails\b|\bimplies\b|=)>?\s*(.{0,90})",
            text,
        ):
            src = norm_token(m.group(1))
            dst = _dst_token(m.group(4), own_token)
            if dst is None:
                continue
            if _metalinguistic(text, m.start(), m.end()):
                continue
            hits.append(_adjudicate(src, dst, order, own_token, path, m.group(0)))
        # pass B: "this class's conclusion ... ENTAILS ... B-inext"
        for m in re.finditer(
            r"(?i)(this\s+class'?s?\s+conclusion|(?:C0|C2|H2_?loc|C\^?\{?1,1\})[- ]inextendibility)((?:(?!\bENTAILS\b|\bentails\b|\bimplies\b).){0,60}?)(\bENTAILS\b|\bentails\b|\bimplies\b)\s*(.{0,90})",
            text,
        ):
            head = m.group(1)
            src = own_token if head.lower().startswith("this") else norm_token(head)
            dst = _dst_token(m.group(4), own_token)
            if dst is None:
                continue
            if _metalinguistic(text, m.start(), m.end()):
                continue
            hits.append(_adjudicate(src, dst, order, own_token, path, m.group(0)))
    # de-duplicate on (path, excerpt)
    seen, out = set(), []
    for h in hits:
        k = (h["path"], h["excerpt"])
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def _adjudicate(src, dst, order, own_token, path, excerpt):
    i_s, i_d = idx_of(order, src), idx_of(order, dst)
    ok = None
    if i_s is not None and i_d is not None:
        # order is largest extension set first.  src-inext ("no extension in E_src")
        # entails dst-inext iff E_dst subset-of E_src, i.e. idx(dst) >= idx(src).
        ok = i_s <= i_d
    return {
        "id": "direction_inverted" if ok is False else "direction_ok",
        "severity": "hard" if ok is False else "info",
        "path": path,
        "src": src,
        "dst": dst,
        "own_token": own_token,
        "consistent": ok,
        "excerpt": excerpt[:200],
    }


def detect_all(doc, text, own_token):
    chain = next(
        (
            t
            for p, t in walk_strings(doc)
            if p.endswith("implication_ledger.extension_class_containment")
        ),
        "",
    )
    order = parse_order_from_chain(chain)
    if order is None:
        sub = parse_subset_order(chain)
        if sub is not None:
            order = list(reversed(sub))
    if order is None:
        return None
    return {
        "order_largest_first": order,
        "own_token": own_token,
        "defects": {
            "containment_denial": find_containment_denials(doc),
            "size_premise": [
                h for h in find_size_premises(doc, order, own_token) if h["severity"] == "hard"
            ],
            "subset_order": [
                h for h in find_subset_claims(doc, order) if h["severity"] == "hard"
            ],
            "direction": [
                h for h in find_direction_claims(doc, order, own_token) if h["severity"] == "hard"
            ],
            "entailment_rows": [
                h for h in find_entailment_rows(doc, order, own_token) if h["severity"] == "hard"
            ],
        },
    }


def defect_count(res):
    return sum(len(v) for v in res["defects"].values())


def defect_ids(res):
    return sorted({h["id"] for v in res["defects"].values() for h in v})


# ---------------------------------------------------------------- pins + controls
def measure_pins(expectations):
    out = {}
    for rel, expected in expectations.items():
        p = ROOT / rel
        measured = sha256_file(p) if p.exists() else None
        out[rel] = {
            "expected": expected,
            "measured": measured,
            "match": measured == expected,
            "exists": p.exists(),
        }
    return out


def run_gate(schema_path: Path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / GATE), "--json", str(schema_path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"raw_stdout": proc.stdout[:2000], "raw_stderr": proc.stderr[:2000]}
    return {"returncode": proc.returncode, "report": report}


def main():
    failures = []
    report = {
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "generated_from": "artifacts/worker-096/f2b_repair_candidate_independent/verify_candidates.py",
        "authority": "Worker measurement only. No canonical file, map, gate or node status modified; no node done; no validation_status passed; no gate verdict.",
        "method": (
            "Strict duplicate-key YAML parse; sha256 pins measured before/after; the document's own "
            "extension_class_containment chain is parsed into a set order and every normative size/"
            "containment/direction sentence is adjudicated against it class-relatively; candidate leaf "
            "deltas must be a subset of the two declared defect carriers; canonical structural gate run "
            "as corroboration on snapshots."
        ),
    }

    # ---- snapshots (byte copies; canonical untouched)
    snap_dir = ART / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    snapshots = {}
    for name, spec in CANDIDATES.items():
        src = ROOT / spec["path"]
        if not src.exists():
            failures.append(f"candidate missing: {spec['path']}")
            continue
        data = src.read_bytes()
        measured = hashlib.sha256(data).hexdigest()
        snap = snap_dir / f"{name}.{measured[:12]}.yaml"
        snap.write_bytes(data)
        snapshots[name] = {
            "source_path": spec["path"],
            "declared_sha256": spec["declared"],
            "measured_sha256": measured,
            "declared_match": measured == spec["declared"],
            "snapshot": str(snap.relative_to(ROOT)),
            "snapshot_sha256": sha256_file(snap),
            "author": spec["author"],
        }
    live_snap = snap_dir / "af_scc_c0_vacuum.live.b2ab6acb2bbe.yaml"
    live_snap.write_bytes((ROOT / LIVE_PATH).read_bytes())
    c2_snap = snap_dir / "af_scc_c2_vacuum.live.e9a27996dfd3.yaml"
    c2_snap.write_bytes((ROOT / C2_PATH).read_bytes())
    report["snapshots"] = snapshots

    # ---- input documents
    live_doc, live_text, live_lines = load_doc(ROOT / LIVE_PATH)
    mirror_bytes = (ROOT / MIRROR_PATH).read_bytes()
    c2_doc, c2_text, _ = load_doc(ROOT / C2_PATH)
    frozen = json.loads((ROOT / FROZEN_PATH).read_text())

    live_token = live_doc["class_components"]["regularity_token"]
    c2_token = c2_doc["class_components"]["regularity_token"]
    report["live"] = {
        "path": LIVE_PATH,
        "sha256": sha256_file(ROOT / LIVE_PATH),
        "mirror_byte_identical": (ROOT / LIVE_PATH).read_bytes() == mirror_bytes,
        "class_id": live_doc["class_id"],
        "revision": live_doc["revision"],
        "regularity_token": live_token,
        "conclusion_type": live_doc["conclusion"]["conclusion_type"],
    }

    # FROZEN declares the live F2b pin?  (manifest layout: files is path -> {sha256, bytes})
    frozen_files = frozen.get("files", {})
    frozen_entry = frozen_files.get(LIVE_PATH) if isinstance(frozen_files, dict) else None
    frozen_f2b_sha = frozen_entry.get("sha256") if isinstance(frozen_entry, dict) else None
    report["frozen"] = {
        "path": FROZEN_PATH,
        "sha256": sha256_file(ROOT / FROZEN_PATH),
        "revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "files_layout": "path->{sha256,bytes}" if isinstance(frozen_files, dict) else type(frozen_files).__name__,
        "n_pins": len(frozen_files) if hasattr(frozen_files, "__len__") else None,
        "f2b_pin": frozen_f2b_sha,
        "f2b_pin_matches_live": frozen_f2b_sha == report["live"]["sha256"],
    }
    if not report["frozen"]["f2b_pin_matches_live"]:
        failures.append("FROZEN rev29 does not declare the measured live F2b pin")

    # ---- live documents adjudicated
    live_res = detect_all(live_doc, live_text, live_token)
    c2_res = detect_all(c2_doc, c2_text, c2_token)
    report["live_adjudication"] = live_res
    report["c2_sibling_adjudication"] = c2_res

    # ---- candidates
    cand_results = {}
    for name, spec in snapshots.items():
        doc, text, lines = load_doc(ROOT / spec["snapshot"])
        token = doc["class_components"]["regularity_token"]
        res = detect_all(doc, text, token)
        changed_paths = sorted(set(diff_leaf_paths(live_doc, doc)))
        sm = difflib.SequenceMatcher(None, live_lines, lines)
        changed_lines = []
        unified = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for ln in range(i1 + 1, i2 + 1):
                changed_lines.append(ln)
            unified.extend(
                difflib.unified_diff(
                    live_lines[i1:i2],
                    lines[j1:j2],
                    fromfile="live",
                    tofile=name,
                    lineterm="",
                    n=0,
                )
            )
        cand_results[name] = {
            "author": spec["author"],
            "sha256": spec["measured_sha256"],
            "declared_sha256": spec["declared_sha256"],
            "declared_match": spec["declared_match"],
            "regularity_token": token,
            "revision": doc.get("revision"),
            "class_id": doc.get("class_id"),
            "unchanged_identity_fields": {
                "class_id": doc.get("class_id") == live_doc.get("class_id"),
                "conclusion_type": doc["conclusion"]["conclusion_type"]
                == live_doc["conclusion"]["conclusion_type"],
                "sibling": doc.get("sibling_disjoint_from")
                == live_doc.get("sibling_disjoint_from"),
                "f0_binding": doc.get("f0_binding") == live_doc.get("f0_binding"),
                "revision": doc.get("revision") == live_doc.get("revision"),
                "extension_regularity": doc["regularity"].get("extension_regularity")
                == live_doc["regularity"].get("extension_regularity"),
            },
            "changed_yaml_leaf_paths": changed_paths,
            "changed_paths_allowed": set(changed_paths) <= ALLOWED_CHANGED_PATHS,
            "changed_lines": changed_lines,
            "exactly_two_changed_lines": changed_lines == [152, 246],
            "unified_diff": "\n".join(unified),
            "adjudication": res,
            "hard_defects": res["defects"] if res else None,
            "gate": run_gate(ROOT / spec["snapshot"]),
        }
        if res is None:
            failures.append(f"{name}: no parseable containment chain")
            continue
        d = res["defects"]
        cand_results[name]["summary"] = {
            "live_defect_size_premise_cleared": not d["size_premise"],
            "live_defect_containment_denial_cleared": not d["containment_denial"],
            "subset_order_declared_consistent": not d["subset_order"],
            "no_repair_introduced_direction_defect": not d["direction"],
            "minimal_two_carrier_edit": set(changed_paths) <= ALLOWED_CHANGED_PATHS
            and changed_lines == [152, 246],
            "gate_pass": cand_results[name]["gate"]["report"].get("verdict") == "pass",
        }
    report["candidates"] = cand_results

    # ---- gate blindness control (live carries both defects yet gate passes)
    report["gate_blindness"] = {
        "live_gate": run_gate(live_snap),
        "note": "live b2ab6acb carries the two live defects; if this gate verdict is pass, the gate is blind to them (corroboration only).",
    }

    # ---- fixture drift measurement (consequence, not a defect of the candidates)
    old_strings = [
        "No containment with C2 or C0 is asserted here",
        "C2 is a strictly larger extension class",
    ]
    new_strings = [
        "H2_loc-inextendibility ENTAILS this class's conclusion",
        "entails the C2 sibling's conclusion, not this class",
        "strictly smaller extension class (E_C2 subset of E_C0)",
    ]
    fixture_hits = {s: [] for s in old_strings + new_strings}
    scan_roots = ["schemas", "artifacts/formulation"]
    for root_rel in scan_roots:
        for p in (ROOT / root_rel).rglob("*"):
            if not p.is_file() or p.suffix.lower() not in (".yaml", ".yml", ".json", ".jsonl", ".md", ".txt", ".py"):
                continue
            try:
                blob = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for s in fixture_hits:
                if s in blob:
                    fixture_hits[s].append(str(p.relative_to(ROOT)))
    frozen_paths = set(frozen_files.keys()) if isinstance(frozen_files, dict) else set()
    report["fixture_drift"] = {
        s: {
            "count": len(v),
            "files": v[:12],
            "frozen_pinned": sorted(set(v) & frozen_paths),
        }
        for s, v in fixture_hits.items()
    }

    # ---- consequence note: verdicts bound to the live F2b hash
    verdicts = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(d, dict):
            continue
        tgt = " ".join(str(d.get(k, "")) for k in ("reviewed_sha256", "target_id", "target_path"))
        if "b2ab6acb2bbe" in tgt and ("F2b" in json.dumps(d)[:400] or "af_scc_c0" in json.dumps(d)[:400]):
            verdicts.append(
                {
                    "file": str(p.relative_to(ROOT)),
                    "reviewer": d.get("reviewer"),
                    "verdict": d.get("verdict"),
                    "score": d.get("score"),
                    "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
                }
            )
    report["consequence"] = {
        "live_pin": report["live"]["sha256"],
        "frozen_revision": frozen.get("revision"),
        "verdicts_bound_to_live_hash_on_disk": verdicts,
        "note": (
            "Landing either candidate content-bumps F2b and voids every verdict bound to "
            "b2ab6acb2bbe; the landed bytes will NOT equal the candidate hash because revision/"
            "revised_at must move, so the landed revision needs its own freeze and fresh "
            "independent verdicts."
        ),
    }

    # ---- controls
    controls = []

    def add_control(cid, expected, observed, note=""):
        controls.append(
            {
                "id": cid,
                "expected": expected,
                "observed": observed,
                "pass": expected == observed,
                "note": note,
            }
        )

    # K1 live fires both live defects
    add_control(
        "K1_live_carries_two_live_defects",
        ["containment_denial", "size_premise_inverted"],
        defect_ids(live_res),
    )
    # K2 84b5d3fa clears live defects but introduces direction inversion
    if "candidate_84b5d3fa" in cand_results:
        c = cand_results["candidate_84b5d3fa"]["adjudication"]
        add_control(
            "K2_circulating_candidate_repair_introduced_inversion",
            ["direction_inverted"],
            defect_ids(c),
        )
    # K3/K4 the two corrected candidates are clean
    for name, cid in (
        ("candidate_corrected", "K3_corrected_candidate_clean"),
        ("candidate_nesting_only", "K4_nesting_only_candidate_clean"),
    ):
        if name in cand_results:
            add_control(cid, [], defect_ids(cand_results[name]["adjudication"]))
    # K5 synthetic: corrected candidate with the line-152 direction flipped must fire
    if "candidate_corrected" in snapshots:
        base = (ROOT / snapshots["candidate_corrected"]["snapshot"]).read_text()
        flipped = base.replace(
            "this class's conclusion (C0-inextendibility) therefore ENTAILS H2_loc-inextendibility",
            "H2_loc-inextendibility ENTAILS this class's conclusion",
        )
        tmp = ART / "snapshots" / "_control_flipped_direction.yaml"
        tmp.write_text(flipped)
        fd, ft, _ = load_doc(tmp)
        fres = detect_all(fd, ft, fd["class_components"]["regularity_token"])
        add_control("K5_flipped_direction_detected", ["direction_inverted"], defect_ids(fres))
    # K6 class-relative control: the same sentence in the C2 sibling must NOT fire
    add_control("K6_c2_sibling_sentence_is_class_relative_ok", [], defect_ids(c2_res))
    # K7 predicate is a function of the chain: invert the chain in the corrected candidate
    if "candidate_corrected" in snapshots:
        base = (ROOT / snapshots["candidate_corrected"]["snapshot"]).read_text()
        inv = base.replace(
            "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
            "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0",
            1,
        )
        tmp = ART / "snapshots" / "_control_inverted_chain.yaml"
        tmp.write_text(inv)
        fd, ft, _ = load_doc(tmp)
        fres = detect_all(fd, ft, fd["class_components"]["regularity_token"])
        add_control(
            "K7_inverted_chain_flips_detectors",
            [
                "direction_inverted",
                "entailment_row_inverted",
                "size_premise_inverted",
                "subset_order_inverted",
            ],
            defect_ids(fres),
        )
    # K8 delta detector catches a non-carrier change
    if "candidate_corrected" in snapshots:
        fd, _, _ = load_doc(ROOT / snapshots["candidate_corrected"]["snapshot"])
        fd2 = json.loads(json.dumps(fd))
        fd2["conclusion"]["conclusion_type"] = "tampered_token"
        changed = sorted(set(diff_leaf_paths(live_doc, fd2)))
        add_control(
            "K8_non_carrier_change_flagged_by_delta_check",
            False,
            set(changed) <= ALLOWED_CHANGED_PATHS,
        )
    # K9 strict duplicate-key loader
    dup = ART / "snapshots" / "_control_duplicate_key.yaml"
    dup.write_text("class_id: A\nclass_id: B\n")
    try:
        load_doc(dup)
        dup_raised = False
    except ValueError:
        dup_raised = True
    add_control("K9_duplicate_key_loader_fails_closed", True, dup_raised)
    # K10 pin drift fails closed
    drift_probe = measure_pins({"schemas/af_scc_c0_vacuum.yaml": "0" * 64})
    add_control(
        "K10_pin_drift_detected",
        False,
        drift_probe["schemas/af_scc_c0_vacuum.yaml"]["match"],
    )
    # K11 candidate 84b5d3fa is byte-identical to the worker-066 circulating candidate claim
    add_control(
        "K11_candidate_84b5d3fa_hash_matches_declared",
        True,
        snapshots.get("candidate_84b5d3fa", {}).get("declared_match"),
    )
    report["controls"] = controls
    report["controls_all_pass"] = all(c["pass"] for c in controls)

    # ---- final pin re-measure (drift guard)
    final = measure_pins(PINS)
    report["pin_recheck"] = final
    drifted = sorted(k for k, v in final.items() if not v["match"])

    # ---- verdicts
    verdicts_by_cand = {}
    primary = {"candidate_corrected", "candidate_nesting_only"}
    for name, c in cand_results.items():
        s = c["summary"]
        clean = all(
            s[k]
            for k in (
                "live_defect_size_premise_cleared",
                "live_defect_containment_denial_cleared",
                "subset_order_declared_consistent",
                "no_repair_introduced_direction_defect",
                "minimal_two_carrier_edit",
                "gate_pass",
            )
        ) and c["declared_match"]
        if name in primary:
            verdicts_by_cand[name] = (
                "candidate_clean_on_independent_predicate" if clean else "candidate_defective"
            )
        else:
            # Context candidates are measured on the same predicate but are NOT adjudicated
            # here as landing candidates (peer findings such as worker-100's REP-CD-02 wording
            # deficiency are outside this predicate's scope).
            verdicts_by_cand[name] = (
                "context_candidate_clean_on_this_predicate_not_adjudicated"
                if clean
                else "context_candidate_defective_on_this_predicate"
            )
    report["verdicts"] = verdicts_by_cand
    report["falsifier"] = (
        "Re-run verify_candidates.py on the same pins. Falsified if any declared pin no longer "
        "matches measured bytes, a control stops firing, either worker-080 candidate yields a hard "
        "defect under the document's own chain, the two corrected candidates differ from live on any "
        "path outside the two declared carriers, or the canonical gate fails on a candidate."
    )
    report["non_claims"] = [
        "No mathematics or physics claim; this is a statement about document bytes and the containment relation those bytes themselves declare.",
        "Verdicts are about staged, non-canonical files only. They are reviewer input, not a landing authorization and not a full-schema verdict at a canonical hash.",
        "No canonical write; no node status; no validation_status=passed; no gate verdict.",
        "The canonical structural gate is corroboration only and is blind to both live defects (measured).",
    ]
    report["failures"] = failures
    report["drifted_pins"] = drifted

    (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "task_id": TASK_ID,
        "live": report["live"]["sha256"][:12],
        "frozen": report["frozen"]["sha256"][:12],
        "verdicts": verdicts_by_cand,
        "controls": f"{sum(c['pass'] for c in controls)}/{len(controls)}",
        "failures": failures,
        "drifted_pins": drifted,
        "report": str((ART / "report.json").relative_to(ROOT)),
    }, indent=2))
    if failures or drifted or not report["controls_all_pass"]:
        print("FAIL-CLOSED: failures/drift/control failure", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
