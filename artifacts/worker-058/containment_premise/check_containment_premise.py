#!/usr/bin/env python3
"""W058-CONTAIN-01 -- independent containment-premise consistency audit.

Task:  check every extension-class containment / strength / size premise in the
       frozen canonical SCC schema pair (C2, C0) against the containment order
       those schemas themselves declare, and against each other.

Independence statement (why this is not a re-run of artifacts/worker08/
c2_c0_separation_audit.py): this checker is written from the declarations up.
It does not import, read, or copy worker08's scanner; it does not use a
hand-curated list of known-bad strings.  The reference order is parsed from the
`implication_ledger.extension_class_containment` field of the two canonical
schemas, and every other size/strength/entailment/forbidden statement in the
ledger is then *derived* from that order.

Derivation used (declared by both schemas, verbatim):
    E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0
    => rank(C2)=0 < rank(C^1,1)=1 < rank(H2_loc)=2 < rank(C0)=3
    => "no proper future X extension" is monotone in rank:
       higher rank  = larger extension set = STRONGER inexistence statement.

Consequences checked mechanically:
    * class-size claim  "X is a strictly {larger,smaller} extension class"
      must agree with rank(X) vs rank(reference).
    * strength claim "X-inextendibility is {stronger,weaker}" must agree with
      the ranks of the two classes in the transfer context.
    * `one_way_entailments` with relation=entails must run from higher rank to
      lower rank (stronger -> weaker).
    * `forbidden_transfers` must run from lower rank to higher rank
      (weaker -> stronger is the direction that must NOT be licensed).
    * both schemas must declare the same strict total order.

Exit code 0 = no hard failure, 1 = >=1 hard failure, 2 = input/parse error.
Read-only: never writes to the canonical tree.

Usage:
    python3 check_containment_premise.py --root <repo> [--json OUT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    raise SystemExit(2)

CST = timezone(timedelta(hours=8))
SCHEMA_FILES = {
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
}
AUTHORING = {
    "AF-SCC-C2-VAC-GEN": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "AF-WCC-VAC-GEN": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
}
FROZEN = "artifacts/formulation/FROZEN.json"

# ---------------------------------------------------------------- utilities


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(path: Path, needle: str) -> int | None:
    """1-based line number of the first raw-text line containing needle."""
    try:
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if needle in raw:
                return i
    except OSError:
        return None
    return None


TOKEN_RE = re.compile(r"E_\{?([^}\s,]+(?:,[^}\s]+)?)\}?")


def norm(tok: str) -> str:
    """Normalize an extension-class token to a canonical key."""
    t = tok.strip().strip("{}").rstrip(";.,:)]").replace("^", "").replace("_", "").replace(" ", "")
    t = t.lower()
    table = {
        "c2": "C2",
        "c0": "C0",
        "c11": "C^1,1",
        "c1,1": "C^1,1",
        "h2loc": "H2_loc",
    }
    return table.get(t, f"UNKNOWN({tok})")


# Token + relation scanning.  A single regex findall would miss every other
# link of a chain ("A subset of B subset of C"), so tokens and relations are
# located independently and paired by position.
TOK_POS_RE = re.compile(r"E_\{?([^}\s]+?)\}?(?=[\s;.)\]:]|$)")
REL_POS_RE = re.compile(r"\b(subset of|contains)\b")


def edges_from_text(text: str) -> list[tuple[str, str]]:
    """Return (smaller, larger) pairs declared by one string."""
    toks = [(m.start(), m.end(), norm(m.group(1))) for m in TOK_POS_RE.finditer(text)]
    rels = [(m.start(), m.end(), m.group(1)) for m in REL_POS_RE.finditer(text)]
    out = []
    for rs, re_, rel in rels:
        left = [t for t in toks if t[1] <= rs]
        right = [t for t in toks if t[0] >= re_]
        if not left or not right:
            continue
        a, b = left[-1][2], right[0][2]
        if a.startswith("UNKNOWN") or b.startswith("UNKNOWN") or a == b:
            continue
        out.append((a, b) if rel == "subset of" else (b, a))
    return out


def parse_chain(text: str) -> list[tuple[str, str]]:
    """Parse an explicit containment chain string into (smaller, larger) pairs.

    Handles both the 'subset of' and the 'contains' phrasing; returns [] when
    the string does not actually declare a chain (>=2 classes linked).
    """
    return edges_from_text(text)


def close_rank(edges: list[tuple[str, str]]) -> tuple[dict[str, int], list[str]]:
    """Topological rank (0 = smallest extension set) + contradiction list."""
    from collections import deque

    nodes = sorted({n for e in edges for n in e})
    es = sorted(set(edges))
    problems: list[str] = []
    eset = set(es)
    for a, b in es:
        if a == b:
            problems.append(f"self containment: {a}")
        elif (b, a) in eset:
            problems.append(f"contradictory containment pair: {a} < {b} and {b} < {a}")
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for a, b in es:
        if a == b or b in adj[a]:
            continue
        adj[a].add(b)
        indeg[b] += 1
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    topo: list[str] = []
    while q:
        n = q.popleft()
        topo.append(n)
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if len(topo) != len(nodes):
        cyclic = sorted(set(nodes) - set(topo))
        problems.append("containment cycle involving: " + ", ".join(cyclic))
        return {}, problems
    rank: dict[str, int] = {n: 0 for n in nodes}
    for n in topo:
        for m in adj[n]:
            rank[m] = max(rank[m], rank[n] + 1)
    return rank, problems


# ------------------------------------------------------- statement patterns

SIZE_RE = re.compile(
    r"\b(C\^?\{?1,1\}?|C2|C0|H2_?loc)\b\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class",
    re.IGNORECASE,
)
STRENGTH_RE = re.compile(
    r"\b(C\^?\{?1,1\}?|C2|C0|H2_?loc)\s*(?:-\s*)?inextendibility\s+is\s+"
    r"(?:strictly\s+)?(stronger|weaker)\b",
    re.IGNORECASE,
)
COMPARE_RE = re.compile(
    r"\b(C\^?\{?1,1\}?|C2|C0|H2_?loc)\s*(?:-\s*)?inextendibility\s+is\s+"
    r"(?:strictly\s+)?(stronger|weaker)\s+than\s+(this class|C\^?\{?1,1\}?|C2|C0|H2_?loc)",
    re.IGNORECASE,
)
CLASS_IN_FROMTO_RE = re.compile(
    r"no proper future\s+(C\^?\{?1,1\}?|C2|C0|H2_?loc)\s+extension",
    re.IGNORECASE,
)


def rank_of(tok: str, rank: dict[str, int], self_class: str) -> int | None:
    t = norm(tok)
    if t == "UNKNOWN(thisclass)":
        t = self_class
    return rank.get(t)


# ------------------------------------------------------------------- audit


def audit(root: Path) -> dict:
    files: dict[str, dict] = {}
    raw: dict[str, str] = {}
    docs: dict[str, dict] = {}
    for cid, rel in SCHEMA_FILES.items():
        p = root / rel
        if not p.exists():
            return {"status": "INPUT_ERROR", "detail": f"missing {rel}"}
        data = p.read_bytes()  # read once: hash and parse the same bytes
        digest = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8")
        files[cid] = {"path": rel, "sha256": digest}
        raw[cid] = text
        try:
            docs[cid] = yaml.safe_load(text) or {}
        except yaml.YAMLError as e:
            return {"status": "INPUT_ERROR", "detail": f"{rel}: {e}"}

    frozen_p = root / FROZEN
    frozen = json.loads(frozen_p.read_text(encoding="utf-8")) if frozen_p.exists() else {}
    frozen_files = frozen.get("files", {})
    for cid, rel in SCHEMA_FILES.items():
        entry = frozen_files.get(AUTHORING[cid]) or frozen_files.get(rel)
        files[cid]["frozen_sha256"] = (entry or {}).get("sha256")
        files[cid]["frozen_match"] = bool(entry) and entry.get("sha256") == files[cid]["sha256"]
        ap = root / AUTHORING[cid]
        files[cid]["authoring_path"] = AUTHORING[cid]
        files[cid]["authoring_sha256"] = sha256_file(ap) if ap.exists() else None
        files[cid]["canonical_equals_authoring"] = (
            files[cid]["authoring_sha256"] == files[cid]["sha256"]
        )

    # -- 1. reference order from the two SCC declarations
    decl_edges: dict[str, list] = {}
    for cid in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"):
        il = docs[cid].get("implication_ledger") or {}
        text = str(il.get("extension_class_containment") or "")
        decl_edges[cid] = parse_chain(text)

    rank_c2, prob_c2 = close_rank(decl_edges["AF-SCC-C2-VAC-GEN"])
    rank_c0, prob_c0 = close_rank(decl_edges["AF-SCC-C0-VAC-GEN"])
    chain_concordant = bool(rank_c2) and rank_c2 == rank_c0
    chain_problems = list(dict.fromkeys(prob_c2 + prob_c0))
    if not chain_concordant:
        chain_problems.append(
            "C2 and C0 declare different containment orders: "
            f"C2={rank_c2} vs C0={rank_c0}"
        )

    # reference rank: prefer C2's declaration; if they disagree the audit fails anyway
    rank = dict(rank_c2 or rank_c0)
    self_class = {"AF-SCC-C2-VAC-GEN": "C2", "AF-SCC-C0-VAC-GEN": "C0"}

    findings: list[dict] = []
    checked: list[dict] = []

    def add(code: str, cid: str, path_key: str, text: str, detail: str, expected: str,
            needle: str | None = None):
        p = root / SCHEMA_FILES[cid]
        line = line_of(p, needle) if needle else None
        if line is None and text.strip():
            line = line_of(p, text.strip()[:80])
        findings.append(
            {
                "id": f"W058-CONTAIN-01-F{len(findings) + 1}",
                "code": code,
                "class_id": cid,
                "yaml_path": path_key,
                "line": line,
                "text": text.strip()[:300],
                "detail": detail,
                "expected": expected,
                "verdict": "FAIL",
            }
        )

    # -- 2. per-file ledger walk
    for cid in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"):
        il = docs[cid].get("implication_ledger") or {}
        this = self_class[cid]

        # 2a. declaration itself: every edge must match the reference rank
        for a, b in decl_edges[cid]:
            ra, rb = rank.get(a), rank.get(b)
            ok = ra is not None and rb is not None and ra < rb
            checked.append(
                {
                    "class_id": cid,
                    "kind": "declaration_edge",
                    "statement": f"{a} subset of {b}",
                    "verdict": "PASS" if ok else "FAIL",
                }
            )
            if not ok:
                add(
                    "declaration_edge_contradicts_reference",
                    cid,
                    "implication_ledger.extension_class_containment",
                    str(il.get("extension_class_containment") or ""),
                    f"declared edge {a} subset of {b} disagrees with reference rank "
                    f"{rank}",
                    "every declared edge must raise rank",
                )

        # 2b. entailment direction table
        for i, row in enumerate(il.get("one_way_entailments") or []):
            if not isinstance(row, dict):
                continue
            frm, to = str(row.get("from", "")), str(row.get("to", ""))
            mf = CLASS_IN_FROMTO_RE.search(frm)
            mt = CLASS_IN_FROMTO_RE.search(to)
            cf = norm(mf.group(1)) if mf else (this if "this class" in frm else None)
            ct = norm(mt.group(1)) if mt else (this if "this class" in to else None)
            if cf is None or ct is None:
                continue
            rf, rt = rank.get(cf), rank.get(ct)
            ok = rf is not None and rt is not None and rf > rt
            checked.append(
                {
                    "class_id": cid,
                    "kind": "entailment_direction",
                    "statement": f"{frm} => {to}",
                    "ranks": {cf: rf, ct: rt},
                    "verdict": "PASS" if ok else "FAIL",
                }
            )
            if not ok:
                add(
                    "entailment_runs_weaker_to_stronger",
                    cid,
                    f"implication_ledger.one_way_entailments[{i}]",
                    f"{frm} => {to}",
                    f"entails row runs {cf}(rank {rf}) -> {ct}(rank {rt}); an entailment "
                    "must run from the stronger (higher-rank) statement to the weaker one",
                    "rank(from) > rank(to)",
                    needle=frm,
                )

        # 2c. forbidden-transfer direction table
        for i, row in enumerate(il.get("forbidden_transfers") or []):
            if not isinstance(row, dict):
                continue
            frm, to = str(row.get("from", "")), str(row.get("to", ""))
            mf = CLASS_IN_FROMTO_RE.search(frm)
            mt = CLASS_IN_FROMTO_RE.search(to)
            cf = norm(mf.group(1)) if mf else None
            ct = norm(mt.group(1)) if mt else (this if "this class" in to else None)
            if cf is None or ct is None:
                continue  # cross-family rows (e.g. AF-WCC-...) are out of scope
            rf, rt = rank.get(cf), rank.get(ct)
            ok = rf is not None and rt is not None and rf < rt
            checked.append(
                {
                    "class_id": cid,
                    "kind": "forbidden_transfer_direction",
                    "statement": f"{frm} =/=> {to}",
                    "ranks": {cf: rf, ct: rt},
                    "verdict": "PASS" if ok else "FAIL",
                }
            )
            if not ok:
                add(
                    "forbidden_transfer_is_actually_valid",
                    cid,
                    f"implication_ledger.forbidden_transfers[{i}]",
                    f"{frm} =/=> {to}",
                    f"forbidden row runs {cf}(rank {rf}) -> {ct}(rank {rt}); forbidding a "
                    "stronger->weaker transfer contradicts the declared order",
                    "rank(from) < rank(to)",
                    needle=frm,
                )

            # 2d. provenance text of the forbidden row: size + strength premises
            reason = str(row.get("reason", ""))
            for m in SIZE_RE.finditer(reason):
                subj = norm(m.group(1))
                claimed = m.group(2).lower()
                rs = rank.get(subj)
                ref = rank.get(ct) if ct else None
                if rs is None or ref is None or rs == ref:
                    continue
                truth = "larger" if rs > ref else "smaller"
                ok = claimed == truth
                checked.append(
                    {
                        "class_id": cid,
                        "kind": "class_size_premise",
                        "statement": m.group(0),
                        "ranks": {subj: rs, ct: ref},
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "class_size_premise_inverted",
                        cid,
                        f"implication_ledger.forbidden_transfers[{i}].reason",
                        reason,
                        f"text calls {subj} a strictly {claimed} extension class than "
                        f"{ct}; declared order gives rank({subj})={rs} vs rank({ct})={ref}, "
                        f"so {subj} is strictly {truth}",
                        f"'{subj} is a strictly {truth} extension class'",
                    )
            for m in STRENGTH_RE.finditer(reason):
                subj = norm(m.group(1))
                claimed = m.group(2).lower()
                rs = rank.get(subj)
                ref = rank.get(ct) if ct else None
                if rs is None or ref is None or rs == ref:
                    continue
                truth = "stronger" if rs > ref else "weaker"
                ok = claimed == truth
                checked.append(
                    {
                        "class_id": cid,
                        "kind": "strength_premise",
                        "statement": m.group(0),
                        "ranks": {subj: rs, ct: ref},
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "strength_premise_inverted",
                        cid,
                        f"implication_ledger.forbidden_transfers[{i}].reason",
                        reason,
                        f"text calls {subj}-inextendibility {claimed} than {ct}; declared "
                        f"order gives rank({subj})={rs} vs rank({ct})={ref}, so it is {truth}",
                        f"'{subj}-inextendibility is {truth}'",
                    )

        # 2e. one-way entailment provenance text
        for i, row in enumerate(il.get("one_way_entailments") or []):
            if not isinstance(row, dict):
                continue
            reason = str(row.get("reason", ""))
            for a, b in edges_from_text(reason):
                ra, rb = rank.get(a), rank.get(b)
                ok = ra is not None and rb is not None and ra < rb
                checked.append(
                    {
                        "class_id": cid,
                        "kind": "reason_edge",
                        "statement": f"{a} subset of {b}",
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "reason_containment_edge_inverted",
                        cid,
                        f"implication_ledger.one_way_entailments[{i}].reason",
                        reason,
                        f"reason declares {a} subset of {b} but reference rank is "
                        f"{a}={ra}, {b}={rb}",
                        "declared edge must raise rank",
                    )
            for m in COMPARE_RE.finditer(reason):
                subj = norm(m.group(1))
                claimed = m.group(2).lower()
                other = m.group(3)
                other_n = this if other.lower() == "this class" else norm(other)
                rs, ro = rank.get(subj), rank.get(other_n)
                if rs is None or ro is None or rs == ro:
                    continue
                truth = "stronger" if rs > ro else "weaker"
                ok = claimed == truth
                checked.append(
                    {
                        "class_id": cid,
                        "kind": "comparative_strength",
                        "statement": m.group(0),
                        "ranks": {subj: rs, other_n: ro},
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "comparative_strength_inverted",
                        cid,
                        f"implication_ledger.one_way_entailments[{i}].reason",
                        reason,
                        f"text calls {subj}-inextendibility {claimed} than {other_n}; "
                        f"declared order gives {rs} vs {ro}",
                        f"'{subj}-inextendibility is {truth} than {other_n}'",
                    )

        # 2f. subsumption note / one-way implication prose
        for key in ("subsumption_note", "one_way_implication", "cross_family"):
            text = str(il.get(key) or "")
            if not text:
                continue
            for a, b in edges_from_text(text):
                ra, rb = rank.get(a), rank.get(b)
                ok = ra is not None and rb is not None and ra < rb
                checked.append(
                    {
                        "class_id": cid,
                        "kind": f"{key}_edge",
                        "statement": f"{a} subset of {b}",
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "prose_containment_edge_inverted",
                        cid,
                        f"implication_ledger.{key}",
                        text,
                        f"declares {a} subset of {b}; reference rank {a}={ra}, {b}={rb}",
                        "declared edge must raise rank",
                    )

        # 2g. remaining ledger prose fields: size/strength claims vs "this class"
        for path_key, text in _iter_strings(il, "implication_ledger"):
            if path_key.endswith("extension_class_containment"):
                continue
            if "forbidden_transfers" in path_key or "one_way_entailments" in path_key:
                continue  # already checked in 2d/2e
            for m in SIZE_RE.finditer(text):
                subj = norm(m.group(1))
                claimed = m.group(2).lower()
                if subj == this or this not in rank or subj not in rank:
                    continue
                truth = "larger" if rank[subj] > rank[this] else "smaller"
                ok = claimed == truth
                checked.append(
                    {
                        "class_id": cid,
                        "kind": "class_size_premise",
                        "statement": m.group(0),
                        "ranks": {subj: rank[subj], this: rank[this]},
                        "verdict": "PASS" if ok else "FAIL",
                    }
                )
                if not ok:
                    add(
                        "class_size_premise_inverted",
                        cid,
                        path_key,
                        text,
                        f"calls {subj} strictly {claimed} than this class ({this}); "
                        f"reference rank {rank[subj]} vs {rank[this]}",
                        f"'{subj} is a strictly {truth} extension class'",
                    )

    hard_failures = [f for f in findings if f["verdict"] == "FAIL"]
    result = {
        "artifact": "W058-CONTAIN-01 containment-premise audit",
        "worker": "worker-058",
        "actor": "deepseek-flash-058",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "task_id": "W058-CONTAIN-01",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "scope_declaration": (
            "Audits the logical consistency of declared extension-class containment, "
            "class-size and statement-strength premises inside the frozen canonical SCC "
            "ledgers, and concordance of the two declarations. It does NOT audit physical "
            "truth, data-class regularity, citation scope, or definitional correctness, and "
            "claims no node completion or gate verdict; interpretation is owned by "
            "astra-lead-formulation. Read-only."
        ),
        "reference_order": {
            "source": "implication_ledger.extension_class_containment (both SCC schemas)",
            "rank_smallest_extension_set_first": rank,
            "c2_declared_edges": [f"{a} subset of {b}" for a, b in decl_edges["AF-SCC-C2-VAC-GEN"]],
            "c0_declared_edges": [f"{a} subset of {b}" for a, b in decl_edges["AF-SCC-C0-VAC-GEN"]],
            "concordant": chain_concordant,
        },
        "strength_rule": (
            "higher rank = larger extension set = stronger 'no proper future extension' "
            "statement; entailment must run high rank -> low rank; forbidden transfer must "
            "run low rank -> high rank"
        ),
        "inputs": {
            "files": files,
            "frozen_manifest": {
                "path": FROZEN,
                "sha256": sha256_file(frozen_p) if frozen_p.exists() else None,
                "revision": frozen.get("revision"),
                "frozen_at": frozen.get("frozen_at"),
            },
        },
        "binding_status": {
            "mode": (
                "FROZEN"
                if all(f.get("frozen_match") for f in files.values())
                else "LIVE_ONLY_FROZEN_STALE"
            ),
            "note": (
                "Findings bind to the live sha256 recorded in inputs.files; verdicts are "
                "valid only for bytes equal to those hashes. If mode is "
                "LIVE_ONLY_FROZEN_STALE the FROZEN.json entries for these paths do not "
                "match disk, so a reviewer must bind to the live hash, not the manifest "
                "revision number, and the freeze/publication task owns that discrepancy."
            ),
            "live_hashes": {cid: files[cid]["sha256"] for cid in files},
            "frozen_hashes": {cid: files[cid].get("frozen_sha256") for cid in files},
            "frozen_mismatches": [cid for cid in files if not files[cid].get("frozen_match")],
        },
        "checked_statement_count": len(checked),
        "checked_statements": checked,
        "chain_problems": chain_problems,
        "hard_failure_count": len(hard_failures),
        "hard_failures": hard_failures,
        "verdict": "FAIL" if (hard_failures or chain_problems) else "PASS",
        "next_falsifier": (
            "Re-run at the next canonical revision. This audit is falsified if (a) it "
            "reports PASS at the hash bound here, (b) a reviewer exhibits a size/strength "
            "premise this checker accepts that contradicts the declared order, or (c) after "
            "the 'strictly larger' -> 'strictly smaller' repair in "
            "C0#implication_ledger.forbidden_transfers[0].reason the checker still reports "
            "class_size_premise_inverted (repair insufficiency), or still reports PASS while "
            "the C2/C0 declarations disagree."
        ),
    }
    return result


def _iter_strings(obj, prefix):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    res = audit(root)
    out = json.dumps(res, indent=2, sort_keys=False)
    if args.json:
        Path(args.json).write_text(out + "\n", encoding="utf-8")
    print(out)
    if res.get("status") == "INPUT_ERROR":
        return 2
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
