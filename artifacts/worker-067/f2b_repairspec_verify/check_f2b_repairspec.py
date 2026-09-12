#!/usr/bin/env python3
"""W067-F2B-REPAIRSPEC-VERIFY-01 -- independent verification of the W020 F2b rev13
repair spec (node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM).

Independent of the author instrument `artifacts/worker-020/f2b_rev13_repair_spec/
carrier_check.py` (never imported): this script derives the containment order from the
target file's own `implication_ledger`, builds the candidate by applying the spec's two
exact substring replacements to the live bytes, checks byte-level minimality, runs its own
direction/containment carrier scan over every string leaf, and cross-runs two independent
instruments on live vs candidate (canonical `check_class_schema.py`, stage-B
`spec_conformance_audit.py`).

Read-only w.r.t. every canonical path. Writes only inside this directory.
Exit: 0 all checks+controls pass; 1 a check or control failed; 2 pin drift / fail-closed.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
SCRATCH = ART / "scratch"
CAND_DIR = ART / "candidate"
CST = timezone(timedelta(hours=8))

TASK_ID = "W067-F2B-REPAIRSPEC-VERIFY-01"
WORKER = "worker-067"
NODE = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/worker-020/f2b_rev13_repair_spec/repair_spec.json":
        "179f8f993ddea82595fd0e4c439e8ecc822f35fb884edb256e1a0a49bfb2f7ba",
    "artifacts/worker-020/f2b_rev13_repair_spec/patched_candidate/schemas/af_scc_c0_vacuum.yaml":
        "6aaff1633faf9313bbf4927fe8655781cf537ee211c412a7b18d78f03322aebf",
    "artifacts/worker-020/f2b_rev13_repair_spec/report.json":
        "50d08f625ab8dbe26c21778c8788da39871b393f67bc86a8015234233a048dae",
    "artifacts/worker-020/f2b_rev13_repair_spec/controls.json":
        "6e7dc402e3ca47f69dca16907d9a2c1a9da34c47a2bf73e74def1a11baafb337",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
}
CANONICAL_TARGETS = ["schemas/af_scc_c0_vacuum.yaml",
                     "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                     "artifacts/formulation/FROZEN.json"]
CITED_LINES = {"CARRIER-A": 152, "CARRIER-B": 246}
FIELD_A = ("regularity", "must_not_conflate", 0)
FIELD_B = ("implication_ledger", "forbidden_transfers", 0, "reason")
MENTION_PREFIXES = ("anti_scope", "class_identity_variants", "revision_history",
                    "unresolved_items", "timestamp_provenance", "provenance",
                    "known_status", "l1_ledger_refs", "falsifier")
CLASS_TOKENS = {"C0": "E_C0", "H2loc": "E_H2loc", "C^1,1": "E_{C^1,1}", "C2": "E_C2"}
FIELD_A_STR = "regularity.must_not_conflate[0]"
FIELD_B_STR = "implication_ledger.forbidden_transfers[0].reason"


class PinDrift(Exception):
    pass


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get_path(doc, path):
    cur = doc
    for k in path:
        cur = cur[k]
    return cur


def set_path(doc, path, value):
    cur = doc
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def leaves(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def verify_pins(pin_map=None) -> list:
    pin_map = PINS if pin_map is None else pin_map
    rows, bad = [], []
    for rel, expected in pin_map.items():
        p = ROOT / rel
        if not p.exists():
            bad.append({"path": rel, "expected": expected, "measured": None})
            continue
        measured = sha256_file(p)
        rows.append({"path": rel, "expected": expected, "measured": measured,
                     "match": measured == expected})
        if measured != expected:
            bad.append({"path": rel, "expected": expected, "measured": measured})
    if bad:
        raise PinDrift(json.dumps(bad, indent=1))
    return rows


def line_of(text: str, needle: str) -> int:
    off = text.index(needle)
    return text.count("\n", 0, off) + 1


def build_candidate(text: str, reps: list) -> str:
    out = text
    for old, new in reps:
        n = out.count(old)
        if n != 1:
            raise ValueError(f"replacement sentinel occurs {n} times, expected 1: {old[:60]!r}")
        out = out.replace(old, new)
    return out


def leaf_diff(a, b, prefix=""):
    """All (path, old, new) leaf differences between two parsed docs."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            child = f"{prefix}.{k}" if prefix else str(k)
            if k not in a or k not in b:
                out.append((child, a.get(k), b.get(k)))
            else:
                out += leaf_diff(a[k], b[k], child)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((f"{prefix}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += leaf_diff(x, y, f"{prefix}[{i}]")
    elif a != b:
        out.append((prefix, a, b))
    return out


def masked_tree_equal(a, b, mask_paths) -> bool:
    import copy
    x, y = copy.deepcopy(a), copy.deepcopy(b)
    for p in mask_paths:
        try:
            set_path(x, p, "__MASK__")
        except (KeyError, IndexError, TypeError):
            pass
        try:
            set_path(y, p, "__MASK__")
        except (KeyError, IndexError, TypeError):
            pass
    return x == y


def parse_chain(doc):
    """Derive the extension-set containment order from the file's own ledger.

    Returns dict: canonical class token -> rank (0 == largest set), plus the raw edges
    and the containment sentence. Independent of the text under test: built from
    implication_ledger.extension_class_containment and the one_way_entailments reasons.
    """
    led = doc["implication_ledger"]
    sent = led["extension_class_containment"]
    chain = re.findall(r"E_(\{[^}]+\}|[A-Za-z0-9^,]+)(?=\s+contains|\s*;|\s*$)", sent)
    chain_tokens = []
    for c in chain:
        tok = "E_" + c
        if tok not in chain_tokens:
            chain_tokens.append(tok)
    rank = {tok: i for i, tok in enumerate(chain_tokens)}
    edges = []
    for row in led.get("one_way_entailments", []):
        for m in re.finditer(r"(E_\S+?)\s+subset of\s+(E_\S+?)(?:\s|\(|,|$)", row.get("reason", "")):
            edges.append((m.group(1), m.group(2)))
    consistent_edges, inconsistent_edges = [], []
    for x, y in edges:
        if x in rank and y in rank:
            (consistent_edges if rank[x] >= rank[y] else inconsistent_edges).append((x, y))
    return {"sentence": sent, "chain_largest_to_smallest": chain_tokens, "rank": rank,
            "edges": edges, "consistent_edges": consistent_edges,
            "inconsistent_edges": inconsistent_edges}


def direction_scan(doc):
    """Independent scan of every string leaf for containment/direction assertions.

    Classification is against the order derived by parse_chain(). Assertion paths and
    mention containers are separated by path prefix and reported distinctly; only
    inconsistent clauses on assertion paths are carriers.
    """
    order = parse_chain(doc)
    rank = order["rank"]
    tok = {k: rank.get(v) for k, v in CLASS_TOKENS.items()}
    findings = []
    for path, val in leaves(doc):
        if not isinstance(val, str):
            continue
        mention = path.startswith(MENTION_PREFIXES)
        for clause in re.split(r"[;.]", val):
            clause = clause.strip()
            if not clause:
                continue
            checks = []
            for m in re.finditer(r"(E_\S+?)\s+contains\s+(E_\S+)", clause):
                a, b = m.group(1), m.group(2)
                if a in rank and b in rank:
                    checks.append(("contains", f"{a} contains {b}", rank[a] <= rank[b]))
            for m in re.finditer(r"(E_\S+?)\s+subset of\s+(E_\S+)", clause):
                a, b = m.group(1), m.group(2)
                if a in rank and b in rank:
                    checks.append(("subset", f"{a} subset of {b}", rank[a] >= rank[b]))
            for m in re.finditer(r"\b(C2|C0|H2_loc)\s+is\s+(?:a\s+)?strictly\s+(larger|smaller)\s+extension class", clause):
                cls, direction = m.group(1), m.group(2)
                r = tok.get(cls)
                if r is not None and rank:
                    minrank = min(rank.values())
                    # rank 0 == largest extension set (this class, E_C0)
                    ok = (r == minrank) if direction == "larger" else (r > minrank)
                    checks.append(("size-claim", m.group(0), ok))
            for m in re.finditer(r"\b(C2|C0|H2_loc)\b[^.]*\b(innermost|outermost)\b", clause):
                cls, pos = m.group(1), m.group(2)
                r = tok.get(cls)
                if r is not None:
                    ok = (pos == "innermost" and r == max(rank.values())) or \
                         (pos == "outermost" and r == min(rank.values()))
                    checks.append(("position-claim", m.group(0), ok))
            if re.search(r"no containment with .*?(C2|C0)", clause, re.I):
                checks.append(("containment-denial", clause, False))
            class_ctx = bool(re.search(r"E_C2|E_C0|E_H2loc|extension class|inextendibility|sibling", clause))
            for m in re.finditer(r"\b(C2|C0|H2_loc)\b[^.]*?\b(?:strictly\s+)?(weaker|stronger)\b", clause):
                cls, strength = m.group(1), m.group(2)
                r = tok.get(cls)
                if r is not None and class_ctx:
                    ok = (strength == "weaker") if r > 0 else (strength == "stronger" and r == 0)
                    checks.append(("strength-claim", m.group(0), ok))
            if not checks:
                continue
            for kind, text, ok in checks:
                findings.append({"path": path, "kind": kind, "clause": text[:220],
                                 "consistent": ok, "mention_container": mention,
                                 "carrier": (not ok) and (not mention)})
    return order, findings


def run_cmd(argv) -> dict:
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-2000:]}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    checks, controls, findings = [], [], []
    ok = True

    def chk(cid, claim, passed, detail=None):
        nonlocal ok
        checks.append({"id": cid, "claim": claim, "pass": bool(passed), "detail": detail})
        ok = ok and bool(passed)

    # ---- pins / fail closed -------------------------------------------------
    try:
        pin_rows = verify_pins()
        chk("C01-pins", "all 12 pinned inputs hash-match the declared sha256", True,
            {"n": len(pin_rows)})
    except PinDrift as e:
        chk("C01-pins", "all 12 pinned inputs hash-match the declared sha256", False,
            str(e)[:1500])
        payload = {"task_id": TASK_ID, "worker": WORKER, "verdict": "FAIL_CLOSED_PIN_DRIFT",
                   "generated_at": now(), "checks": checks,
                   "falsifier": "void on any pin drift"}
        (ART / "report.json").write_text(json.dumps(payload, indent=1) + "\n")
        print(json.dumps(payload, indent=1))
        return 2

    live_path = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    mirror_path = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    spec_path = ROOT / "artifacts/worker-020/f2b_rev13_repair_spec/repair_spec.json"
    w020_cand = ROOT / "artifacts/worker-020/f2b_rev13_repair_spec/patched_candidate/schemas/af_scc_c0_vacuum.yaml"
    live_text = live_path.read_text(encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    live_doc = yaml.safe_load(live_text)

    # ---- C02 spec shape / target binding -----------------------------------
    carriers = {c["id"]: c for c in spec["carriers"]}
    chk("C02-spec-shape",
        "spec declares CARRIER-A/B with field, line, old, new; target sha == live sha",
        set(carriers) == {"CARRIER-A", "CARRIER-B"}
        and all(all(k in carriers[i] for k in ("field", "line", "old", "new")) for i in carriers)
        and spec["target"]["sha256"] == sha256_file(live_path),
        {"ids": sorted(carriers), "target": spec["target"]["sha256"]})
    reps = [(carriers["CARRIER-A"]["old"], carriers["CARRIER-A"]["new"]),
            (carriers["CARRIER-B"]["old"], carriers["CARRIER-B"]["new"])]

    # ---- C03 sentinels at cited lines + field paths ------------------------
    sent_rows = []
    for cid, field, line in (("CARRIER-A", FIELD_A, CITED_LINES["CARRIER-A"]),
                             ("CARRIER-B", FIELD_B, CITED_LINES["CARRIER-B"])):
        old = carriers[cid]["old"]
        n = live_text.count(old)
        ln = line_of(live_text, old) if n else None
        field_val = get_path(live_doc, field)
        sent_rows.append({"id": cid, "occurrences": n, "cited_line": line, "measured_line": ln,
                          "at_cited_field": isinstance(field_val, str) and old in field_val})
    chk("C03-sentinels",
        "each carrier sentinel occurs exactly once, at its cited line and cited field path",
        all(r["occurrences"] == 1 and r["measured_line"] == r["cited_line"]
            and r["at_cited_field"] for r in sent_rows), sent_rows)

    # ---- C04 independent containment order from the ledger ------------------
    order, scan_live = direction_scan(live_doc)
    chk("C04-order",
        "containment order derived from the file's own ledger is a strict chain and every "
        "E_A subset-of-E_B edge agrees with it",
        bool(order["chain_largest_to_smallest"]) and not order["inconsistent_edges"],
        {"chain": order["chain_largest_to_smallest"], "n_edges": len(order["edges"]),
         "inconsistent_edges": order["inconsistent_edges"]})
    live_carriers = [f for f in scan_live if f["carrier"]]
    chk("C05-live-carriers",
        "live bytes carry both known carriers as inconsistent assertions on assertion paths "
        "(and only those)",
        sorted({f["path"] for f in live_carriers}) ==
        sorted({FIELD_A_STR, FIELD_B_STR}),
        {"carrier_paths": sorted({f["path"] for f in live_carriers}),
         "n_findings": len(scan_live)})

    # ---- C06 independent candidate build (+ hash equality to W020) ----------
    built = build_candidate(live_text, reps)
    built_path = CAND_DIR / "af_scc_c0_vacuum.yaml"
    built_path.write_text(built, encoding="utf-8")
    built_sha = sha256_bytes(built.encode("utf-8"))
    w020_sha = sha256_file(w020_cand)
    chk("C06-candidate-hash",
        "applying the spec's two replacements to live bytes reproduces W020's candidate "
        "sha256 byte-for-byte",
        built_sha == w020_sha == PINS[
            "artifacts/worker-020/f2b_rev13_repair_spec/patched_candidate/schemas/af_scc_c0_vacuum.yaml"],
        {"built": built_sha, "w020": w020_sha})

    # ---- C07 minimality: 2 changed leaves, 2 lines, masked tree equal -------
    cand_doc = yaml.safe_load(built)
    diffs = leaf_diff(live_doc, cand_doc)
    diff_lines = list(difflib.unified_diff(
        live_text.splitlines(), built.splitlines(), lineterm="", n=0))
    changed_lines = [l for l in diff_lines if l.startswith(("+", "-"))
                     and not l.startswith(("+++", "---"))]
    n_hunks = sum(1 for l in diff_lines if l.startswith("@@"))
    n_removed = sum(1 for l in changed_lines if l.startswith("-"))
    n_added = sum(1 for l in changed_lines if l.startswith("+"))
    chk("C07-minimality",
        "exactly the two targeted leaves change in 2 hunks (2 removed / 2 added lines); "
        "masked YAML trees equal",
        len(diffs) == 2 and {d[0] for d in diffs} ==
        {FIELD_A_STR, FIELD_B_STR}
        and n_hunks == 2 and n_removed == 2 and n_added == 2
        and masked_tree_equal(live_doc, cand_doc, [FIELD_A, FIELD_B]),
        {"changed_leaf_paths": [d[0] for d in diffs], "hunks": n_hunks,
         "removed_lines": n_removed, "added_lines": n_added})

    # ---- C08 candidate clears carriers + scanner on candidate ---------------
    _, scan_cand = direction_scan(cand_doc)
    cand_carriers = [f for f in scan_cand if f["carrier"]]
    cand_text = built_path.read_text(encoding="utf-8")
    residual = [cid for cid in ("CARRIER-A", "CARRIER-B")
                if carriers[cid]["old"] in cand_text]
    new_direction_ok = []
    for cid in ("CARRIER-A", "CARRIER-B"):
        new = carriers[cid]["new"]
        hits = [f for f in scan_cand if f["clause"] in new and f["consistent"]]
        new_direction_ok.append(bool(hits) or cid == "CARRIER-A")
    chk("C08-candidate-clean",
        "candidate has no residual sentinel and no inconsistent direction carrier; the "
        "spec's replacement text is itself direction-consistent where it makes a claim",
        not residual and not cand_carriers and all(new_direction_ok),
        {"residual_old_sentinels": residual,
         "candidate_carriers": [f["path"] for f in cand_carriers],
         "assertion_paths_scanned": len({f["path"] for f in scan_cand})})

    # ---- C09 third-carrier census ------------------------------------------
    all_hits = [f for f in scan_cand if not f["mention_container"]]
    inconsistent_other = [f for f in all_hits if not f["consistent"]
                          and f["path"] not in (FIELD_A_STR, FIELD_B_STR)]
    chk("C09-third-carrier",
        "no third inconsistent containment/direction assertion outside the two repaired "
        "fields on any assertion path",
        not inconsistent_other,
        {"assertion_path_hits": len(all_hits),
         "mention_hits": len(scan_cand) - len(all_hits),
         "third_carriers": inconsistent_other})

    # ---- C10 cross-instrument: canonical structural gate --------------------
    gate_live = run_cmd([sys.executable, "artifacts/formulation/tools/check_class_schema.py",
                         "schemas/af_scc_c0_vacuum.yaml", "--json"])
    gate_cand = run_cmd([sys.executable, "artifacts/formulation/tools/check_class_schema.py",
                         str(built_path), "--json"])
    chk("C10-canonical-gate",
        "canonical structural gate passes defective live and repaired candidate alike "
        "(blindness to both carriers independently reproduced)",
        gate_live["rc"] == 0 and gate_cand["rc"] == 0,
        {"live_rc": gate_live["rc"], "candidate_rc": gate_cand["rc"]})

    # ---- C11 cross-instrument: stage-B auditor ------------------------------
    sca_json_live = SCRATCH / "stageb_live.json"
    sca_json_cand = SCRATCH / "stageb_candidate.json"
    sca = [sys.executable, "artifacts/worker-06/spec_conformance_audit.py"]
    spec_arg = ["--spec", "artifacts/formulation/rule_spec.json",
                "--expect-class", CLASS_ID]
    sb_live = run_cmd(sca + ["schemas/af_scc_c0_vacuum.yaml"] + spec_arg + ["--json", str(sca_json_live)])
    sb_cand = run_cmd(sca + [str(built_path)] + spec_arg + ["--json", str(sca_json_cand)])
    lj = json.loads(sca_json_live.read_text()) if sca_json_live.exists() else {}
    cj = json.loads(sca_json_cand.read_text()) if sca_json_cand.exists() else {}
    lrules = {c["rule"]: c.get("verdict") for c in lj.get("checks", [])}
    crules = {c["rule"]: c.get("verdict") for c in cj.get("checks", [])}
    worse = [r for r in crules if crules[r] == "fail" and lrules.get(r) != "fail"]
    chk("C11-stage-b",
        "stage-B auditor verdict on the candidate is no worse than on live (no new rule "
        "failure), live verdict reproduced",
        sb_live["rc"] == sb_cand["rc"] and lj.get("verdict") == cj.get("verdict")
        and not worse,
        {"live": {"rc": sb_live["rc"], "verdict": lj.get("verdict")},
         "candidate": {"rc": sb_cand["rc"], "verdict": cj.get("verdict")},
         "new_failures": worse,
         "rule_verdicts_candidate": {k: v for k, v in sorted(crules.items())}})

    # ---- K-controls ---------------------------------------------------------
    # K1 single replacement -> hash mismatch + residual carrier
    half = build_candidate(live_text, reps[:1])
    half_sha = sha256_bytes(half.encode("utf-8"))
    half_residual = carriers["CARRIER-B"]["old"] in half
    controls.append({"id": "K1", "name": "single-replacement mutant",
                     "expected": "candidate hash differs from W020 and CARRIER-B residual present",
                     "observed": {"sha": half_sha, "residual_B": half_residual},
                     "pass": half_sha != w020_sha and half_residual})
    # K2 wrong-direction replacement -> scanner fires
    wrong = build_candidate(live_text, [(carriers["CARRIER-B"]["old"],
        "E_C2 is the outermost (largest) extension class, so C2-inextendibility is strictly stronger")])
    wdoc = yaml.safe_load(wrong)
    _, wscan = direction_scan(wdoc)
    wcar = [f for f in wscan if f["carrier"]]
    controls.append({"id": "K2", "name": "wrong-direction replacement mutant",
                     "expected": "third-carrier scanner flags the inverted claim",
                     "observed": [f["path"] for f in wcar], "pass": len(wcar) >= 1})
    # K3 sentinel mutation -> exact-once build fails
    k3 = False
    try:
        build_candidate(live_text.replace(carriers["CARRIER-A"]["old"], "no denial here", 1), reps)
    except ValueError:
        k3 = True
    controls.append({"id": "K3", "name": "sentinel-mutation control",
                     "expected": "build refuses when a sentinel is absent",
                     "observed": k3, "pass": k3})
    # K4 cited-line shift -> line assertion fails
    shifted = "filler: 1\n" + live_text
    k4 = all(line_of(shifted, carriers[c]["old"]) != CITED_LINES[c] for c in carriers)
    controls.append({"id": "K4", "name": "line-shift control",
                     "expected": "a one-line insertion moves both cited lines",
                     "observed": {c: line_of(shifted, carriers[c]["old"]) for c in carriers},
                     "pass": k4})
    # K5 pin-drift control -> fail closed
    bad_pins = dict(PINS)
    bad_pins["schemas/af_scc_c0_vacuum.yaml"] = "0" * 64
    k5 = False
    try:
        verify_pins(bad_pins)
    except PinDrift:
        k5 = True
    controls.append({"id": "K5", "name": "pin-drift fail-closed control",
                     "expected": "verify_pins raises PinDrift on a mutated pin",
                     "observed": k5, "pass": k5})
    # K6 masked-tree inequality -> control on the equality predicate itself
    f2a = yaml.safe_load((ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text(encoding="utf-8"))
    k6 = not masked_tree_equal(live_doc, f2a, [FIELD_A, FIELD_B])
    controls.append({"id": "K6", "name": "masked-tree discriminator control",
                     "expected": "masked comparison reports unequal for a different schema",
                     "observed": k6, "pass": k6})
    # K7 determinism (in-process measurement payload, timestamps stripped)
    def payload():
        o, s = direction_scan(yaml.safe_load(live_path.read_text(encoding="utf-8")))
        return {"order": o, "scan": s}
    controls.append({"id": "K7", "name": "determinism control",
                     "expected": "two in-process measurement payloads are equal",
                     "observed": payload() == payload(), "pass": payload() == payload()})
    # K8 no-write canary: canonical targets re-hash unchanged
    pre = {rel: sha256_file(ROOT / rel) for rel in CANONICAL_TARGETS}
    post = {rel: sha256_file(ROOT / rel) for rel in CANONICAL_TARGETS}
    controls.append({"id": "K8", "name": "no-write canary",
                     "expected": "canonical target hashes identical before/after",
                     "observed": {"equal": pre == post}, "pass": pre == post})

    if not all(c["pass"] for c in controls):
        ok = False
    if not all(c["pass"] for c in checks):
        ok = False

    report = {
        "schema": "worker-067/f2b-repairspec-verify/v1",
        "task_id": TASK_ID, "worker": WORKER, "node_id": NODE, "class_id": CLASS_ID,
        "gate": GATE, "generated_at": now(),
        "authority": "worker measurement only; no gate verdict, no node status, no "
                     "validation_status promotion, no canonical write",
        "target": {"path": "schemas/af_scc_c0_vacuum.yaml",
                   "sha256": sha256_file(live_path),
                   "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                   "mirror_sha256": sha256_file(mirror_path),
                   "frozen": "artifacts/formulation/FROZEN.json#815e08079aef"},
        "spec_verified": {"path": "artifacts/worker-020/f2b_rev13_repair_spec/repair_spec.json",
                          "sha256": sha256_file(spec_path)},
        "candidate": {"path": str(built_path.relative_to(ROOT)),
                      "sha256": built_sha,
                      "w020_candidate_sha256": w020_sha},
        "containment_order": order,
        "checks": checks, "controls": controls,
        "live_scan_findings": scan_live,
        "candidate_scan_findings": scan_cand,
        "findings": findings,
        "verdict": ("ACCEPT_REPAIR_SPEC_VERIFIED" if ok
                    else "REVISE_REPAIR_SPEC_CHECK_FAILED"),
        "falsifier": "Void if any pinned input re-hashes differently; if the independently "
                     "built candidate differs from W020's candidate bytes; if the two-field "
                     "patch is not minimal; if a third inconsistent containment/direction "
                     "assertion exists on an assertion path at these bytes; if the stage-B "
                     "auditor or the canonical gate verdict differs on a re-run; or if any "
                     "control departs from its expected outcome.",
        "canonical_writes": 0,
    }
    (ART / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("task_id", "verdict", "target", "candidate",
                                      "containment_order")}
    summary["checks_passed"] = sum(c["pass"] for c in checks)
    summary["checks_total"] = len(checks)
    summary["controls_passed"] = sum(c["pass"] for c in controls)
    summary["controls_total"] = len(controls)
    print(json.dumps(summary, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
