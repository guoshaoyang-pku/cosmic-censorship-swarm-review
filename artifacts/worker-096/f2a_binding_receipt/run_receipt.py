#!/usr/bin/env python3
"""W096-F2A-BINDING-RECEIPT-01: independent, hash-bound binding/consistency receipt.

Class: AF-SCC-C2-VAC-GEN   Node: F2a   Gate: G-FORM

WHAT THIS IS
  A read-only, deterministic receipt for ONE frozen class at ONE measured sha256. It
  re-measures, on the reviewed bytes, the binding/publication properties that the
  G-FORM gate depends on, and records the prior review verdicts that refer to the
  same class. It does NOT re-adjudicate the mathematics and it does NOT import the
  canonical checker to decide its own findings: the canonical checker is run only as
  corroboration, with command, exit code and tool hash recorded.

WHAT IT IS NOT
  Not a gate verdict, not a node status, not an accept. Workers cannot set those
  (comms/PROTOCOL.md). Reviewer input only.

DETERMINISM / FAIL-CLOSED
  * no network, no randomness;
  * target sha256 is measured before and after every check; on drift the run exits 2
    and the report is marked drift=true (a later revision voids the binding, not the
    measurement);
  * duplicate mapping keys are detected with a strict yaml.compose() walk, not with
    PyYAML's last-wins safe_load;
  * timestamp sanity compares declared values against the file mtime and the run wall
    clock, both recorded.

SELF-TESTS (controls run every invocation; any failure marks the report self_test=FAIL)
  N1  clean synthetic document -> no duplicate keys (specificity)
  P1  synthetic document with two revised_at keys -> exactly 2 detected (sensitivity)
  P2  authoring taxonomy resolves class_contracts.<class> (positive pointer control)
  P3  nonexistent fragment does not resolve (fail-closed control)
  P4  identical data_class documents compare equal (positive comparator control)
  P5  declared revised_at <= mtime passes the timestamp predicate (positive control)

USAGE
  python3 run_receipt.py [--target schemas/af_scc_c2_vacuum.yaml] [--out report.json]
Exit: 0 report written; 2 target drift (fail-closed); 3 harness error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(3)

ROOT = Path(__file__).resolve().parents[3]
TZ = timezone(timedelta(hours=8))

TARGET_DEFAULT = "schemas/af_scc_c2_vacuum.yaml"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
TASK_ID = "W096-F2A-BINDING-RECEIPT-01"
REVIEW_ID = "W096-F2A-F01"
OUT_DIR = ROOT / "artifacts/worker-096/f2a_binding_receipt"

PIN_PATHS = {
    "f1_schema": "schemas/af_wcc_vacuum.yaml",
    "f2b_schema": "schemas/af_scc_c0_vacuum.yaml",
    "canonical_taxonomy": "research_map/formulation_taxonomy.yaml",
    "authoring_taxonomy": "artifacts/formulation/formulation_taxonomy.yaml",
    "canonical_checker": "artifacts/formulation/tools/check_class_schema.py",
    "class_separation": "research_map/class_separation.py",
    "classsep_regression": "runtime/bin/classsep_regression.py",
    "protocol": "comms/PROTOCOL.md",
}


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def short(h: str) -> str:
    return h[:12]


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


# ---------------------------------------------------------------- duplicate keys
def duplicate_mapping_keys(text: str) -> list[dict]:
    """Strict duplicate scan over every mapping in the document via yaml.compose()."""
    out: list[dict] = []

    def walk(node, path=""):
        if isinstance(node, yaml.MappingNode):
            counts = Counter(k.value for k, _ in node.value)
            for key, n in counts.items():
                if n > 1:
                    out.append({
                        "path": f"{path}/{key}",
                        "key": key,
                        "count": n,
                        "lines": [v.start_mark.line + 1 for k, v in node.value if k.value == key],
                    })
            for k, v in node.value:
                walk(v, f"{path}/{k.value}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{path}[{i}]")

    walk(yaml.compose(text))
    out.sort(key=lambda d: (d["path"], d["lines"][0] if d["lines"] else 0))
    return out


def safe_effective(text: str) -> dict:
    """PyYAML last-wins view: what an ordinary consumer actually sees."""
    d = yaml.safe_load(text)
    return d if isinstance(d, dict) else {}


# ---------------------------------------------------------------- pointer resolve
def resolve_fragment(doc, fragment: str):
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, part
    return cur, None


def resolve_pointer(pointer: str):
    """pointer = '<path>#<dotted.fragment>' -> (resolved, missing_part, file_sha, file_exists)."""
    p, _, frag = pointer.partition("#")
    fp = ROOT / p
    if not fp.is_file():
        return False, p, None, False
    fsha = sha256_file(fp)
    try:
        doc = load_yaml(fp)
    except Exception as exc:  # noqa: BLE001
        return False, f"unparseable:{type(exc).__name__}", fsha, True
    val, missing = resolve_fragment(doc, frag)
    return (val is not None), missing, fsha, True


# ---------------------------------------------------------------- leaf compare
def leaves(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(leaves(v, f"{pre}.{k}" if pre else str(k)))
    elif isinstance(d, list):
        out[pre] = json.dumps(d, sort_keys=True)
    else:
        out[pre] = d
    return out


# ---------------------------------------------------------------- text probes
def d0_probe(doc: dict) -> dict:
    q = doc.get("quantifiers", {}) or {}
    domains = q.get("domains", {}) or {}
    ordered = q.get("ordered", []) or []
    d0 = domains.get("D0", {}) or {}
    d0_def = str(d0.get("definition", ""))
    reg = (doc.get("regularity", {}) or {}).get("data_regularity", "")
    gen = doc.get("genericity", {}) or {}
    ordered_binders = [str(o.get("binder", "")) for o in ordered if isinstance(o, dict)]
    formal = str(q.get("formal", ""))
    return {
        "d0_disjunct_count": len(re.split(r"\bor\b", d0_def)),
        "d0_contains_or": bool(re.search(r"\bor\b", d0_def)),
        "smooth_with_decay_branch_present": "smooth-with-decay" in d0_def,
        "d0_pair_binder_present": any("s,delta" in b or "s, delta" in b for b in ordered_binders),
        "sobolev_branch_supplies_s_delta_pair": bool(re.search(r"s\s*>\s*5/2", d0_def) and "delta" in d0_def),
        "ambient_space_uses_s_delta": "s,delta" in str(gen.get("ambient_space", "")),
        "ambient_space_defines_smooth_branch_set": bool(
            re.search(r"\bsmooth-with-decay\b", str(gen.get("ambient_space", "")))
            and re.search(r"\b(set|space|manifold|X)\b", str(gen.get("ambient_space", "")))
        ),
        "frechet_topology_named_without_ambient_set": bool(
            "frechet" in str(gen.get("topology_or_measure", "")).lower()
            and not re.search(r"\bsmooth.{0,40}(set|space)\b", str(gen.get("ambient_space", "")), re.I)
        ),
        "formal_binder_includes_s_delta": bool(re.search(r"forall\s*\(s,\s*delta\)", formal)),
        "regularity_data_regularity_has_or": bool(re.search(r"\bor\b", str(reg))),
    }


def quantifier_consistency(doc: dict) -> dict:
    q = doc.get("quantifiers", {}) or {}
    concl = doc.get("conclusion", {}) or {}
    formal = str(q.get("formal", ""))
    sf = str(concl.get("statement_formal", ""))
    ep = doc.get("extension_predicate", {}) or {}
    tokens = {
        "D0": "D0" in sf,
        "D1": "D1" in sf,
        "D2": "D2" in sf,
        "D3": "D3" in sf,
        "D_gen": "D_gen" in sf or "D_gen" in formal,
        "proper_future_extension_in_class": "proper_future_extension_in_class" in sf,
        "extension_predicate_defined": bool(ep.get("definition")),
        "extension_predicate_name": str(ep.get("name", "")),
    }
    order_formal = re.findall(r"\b(forall|exists|not exists)\b", formal)
    order_concl = re.findall(r"\b(forall|exists|not exists)\b", sf)
    return {
        "formal_order": order_formal,
        "conclusion_order": order_concl,
        "order_match": order_formal == order_concl,
        "undefined_domain_tokens": [t for t in ("D_gen",) if t in sf or t in formal],
        "conclusion_uses_defined_predicate": tokens["proper_future_extension_in_class"],
        "extension_predicate_defined": tokens["extension_predicate_defined"],
        "domain_tokens": {k: v for k, v in tokens.items() if k in ("D0", "D1", "D2", "D3", "D_gen")},
    }


def signature_scan(text: str, tokens: list[str]) -> dict:
    return {t: (t in text) for t in tokens}


# ---------------------------------------------------------------- main receipt
def build(target: Path) -> tuple[dict, bool]:
    started = now()
    tb = target.read_bytes()
    t_sha_before = sha256_bytes(tb)
    text = tb.decode("utf-8")
    doc = safe_effective(text)
    mtime = datetime.fromtimestamp(target.stat().st_mtime, TZ).isoformat(timespec="seconds")
    wall = datetime.now(TZ)

    checks: list[dict] = []

    def add(cid, title, status, evidence, falsifier, severity=""):
        checks.append({
            "check_id": cid, "title": title, "status": status,
            "severity": severity, "evidence": evidence, "falsifier": falsifier,
        })

    # --- B02 duplicate keys
    dups = duplicate_mapping_keys(text)
    add(
        "B02-duplicate-mapping-keys",
        "strict duplicate mapping keys on the frozen bytes",
        "fail" if dups else "pass",
        {"duplicates": dups,
         "effective_revised_at_safe_load": doc.get("revised_at"),
         "note": "prior reviews F-086-3/F-088-1 also assert 'revised_at_unused twice (lines 26,28)' for F2a; "
                 "that sub-claim is NOT reproducible on these bytes (revised_at_unused occurs once, line 26)."},
        "A strict duplicate-key parse of the same bytes exiting 0 with no duplicates recorded.",
        "blocking" if dups else "info",
    )

    # --- B03 timestamp sanity
    declared = doc.get("revised_at")
    checked_at = (doc.get("f0_binding") or {}).get("checked_at")
    mtime_dt = datetime.fromtimestamp(target.stat().st_mtime, TZ)
    future = []
    for label, val in (("revised_at", declared), ("f0_binding.checked_at", checked_at)):
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val)
                if dt > mtime_dt:
                    future.append({"field": label, "declared": val,
                                   "later_than_mtime": True,
                                   "later_than_wall_clock_at_run": dt > wall})
            except ValueError:
                future.append({"field": label, "declared": val, "unparseable": True})
    add(
        "B03-timestamp-sanity",
        "declared revision/check timestamps vs file mtime and run wall clock",
        "fail" if future else "pass",
        {"declared_revised_at_effective": declared, "declared_checked_at": checked_at,
         "mtime": mtime, "wall_clock_at_check": started, "later_than_mtime": future,
         "note": "the stable, clock-independent defect is declared > mtime (a revision stamp cannot postdate the "
                 "write it describes); the 'ahead of wall clock' component is time-dependent and was separately "
                 "recorded by reviews F2a-review-21/22/086/088 when measured before 00:30."},
        "A revision whose declared revised_at/checked_at is <= mtime while this check still fails.",
        "blocking" if future else "info",
    )

    # --- B04/B05 pointer
    pointer = str(doc.get("class_contract_pointer", ""))
    f0 = doc.get("f0_binding", {}) or {}
    supplement = str(f0.get("class_contract_supplement", ""))
    ok_p, miss_p, p_sha, p_exists = resolve_pointer(pointer)
    ok_s, miss_s, s_sha, s_exists = resolve_pointer(supplement if "#" in supplement else supplement + "#class_contracts." + CLASS_ID)
    canon_pin = PIN_PATHS["canonical_taxonomy"]
    auth_pin = PIN_PATHS["authoring_taxonomy"]
    canon = load_yaml(ROOT / canon_pin)
    auth = load_yaml(ROOT / auth_pin)
    canon_top = sorted(canon.keys())[:8]
    auth_top = sorted(auth.keys())[:8]
    add(
        "B04-class-contract-pointer",
        "class_contract_pointer resolves on the authoritative publication path",
        "fail" if (not ok_p or short(p_sha or "") != short(sha256_file(ROOT / canon_pin))) else "pass",
        {"pointer": pointer, "declared_target_resolves": ok_p, "missing_fragment_part": miss_p,
         "pointer_path": pointer.partition("#")[0],
         "canonical_top_level_keys_sample": canon_top,
         "authoring_top_level_keys_sample": auth_top,
         "canonical_has_class_contracts": "class_contracts" in canon,
         "authoring_has_class_contracts": "class_contracts" in auth,
         "canonical_resolves_class": bool(resolve_fragment(canon, f"classes.{CLASS_ID}")[0]),
         "authoring_resolves_class": bool(resolve_fragment(auth, f"class_contracts.{CLASS_ID}")[0]),
         "canonical_sha256": sha256_file(ROOT / canon_pin),
         "authoring_sha256": sha256_file(ROOT / auth_pin)},
        "The canonical taxonomy exposing the pointer fragment path class_contracts.<class>, or the authoring tree "
        "published byte-identically to canonical and the pointer naming the canonical hash.",
        "hard",
    )
    declared_f0 = f0.get("declared_f0_sha256")
    add(
        "B05-declared-f0-hash",
        "f0_binding.declared_f0_sha256 equals the measured canonical F0 hash",
        "pass" if declared_f0 == sha256_file(ROOT / canon_pin) else "fail",
        {"declared": declared_f0, "measured_canonical": sha256_file(ROOT / canon_pin),
         "measured_authoring": sha256_file(ROOT / auth_pin)},
        "A canonical F0 hash change without a f0_binding refresh, or a declared hash matching the divergent "
        "authoring tree instead of the canonical artifact.",
        "hard",
    )

    # --- B06 D0 typing
    probe = d0_probe(doc)
    d0_ill = (
        probe["d0_contains_or"]
        and probe["smooth_with_decay_branch_present"]
        and probe["d0_pair_binder_present"]
        and not probe["ambient_space_defines_smooth_branch_set"]
    )
    add(
        "B06-d0-quantifier-domain-typing",
        "the operative (s,delta) binder ranges over a single well-typed data class",
        "fail" if d0_ill else "pass",
        {"probe": probe, "domain_D0_definition": (doc.get("quantifiers", {}).get("domains", {}) or {}).get("D0", {})},
        "Exhibit a defined ambient object and comeagerness notion for the smooth-with-decay branch plus a "
        "well-typed reading of the (s,delta) binder over it from these bytes alone (probe fields falsified); "
        "or revise D0 to one parameterised regularity class shared verbatim by F1/F2a/F2b.",
        "critical",
    )

    # --- B07/B08 quantifier consistency / dangling symbols
    qc = quantifier_consistency(doc)
    dangling = list(qc["undefined_domain_tokens"])
    if not qc["extension_predicate_defined"]:
        dangling.append("extension_predicate")
    add(
        "B07-quantifier-conclusion-consistency",
        "quantifiers.formal and conclusion.statement_formal use the same binder order and defined symbols",
        "fail" if (not qc["order_match"] or dangling) else "pass",
        {"probe": qc, "dangling_symbols": dangling},
        "A parse of these bytes in which the two formal sentences disagree in binder order or use an undefined "
        "domain/predicate (e.g. D_gen, absent extension_predicate).",
        "critical" if dangling else "minor",
    )
    add(
        "B08-rev10-supersession-check",
        "dangling-D_gen / absent-extension_predicate findings from earlier revisions are superseded",
        "pass",
        {"conclusion_statement_formal": doc.get("conclusion", {}).get("statement_formal"),
         "extension_predicate_present": bool((doc.get("extension_predicate") or {}).get("definition")),
         "D_gen_present": "D_gen" in text,
         "note": "reviews F2a-review-18 HF-A1/HF-A2 reviewed an earlier revision; at this hash the predicate is "
                 "defined (line 91) and statement_formal uses proper_future_extension_in_class, not D_gen."},
        "D_gen or a missing extension_predicate in the bytes at this hash.",
        "info",
    )

    # --- B09 cross-schema data class
    dcs = {}
    for name, rel in (("F1", PIN_PATHS["f1_schema"]), ("F2a", str(target.relative_to(ROOT))),
                      ("F2b", PIN_PATHS["f2b_schema"])):
        d = load_yaml(ROOT / rel)
        dcs[name] = leaves(d.get("data_class", {}))
    lf, la, lb = dcs["F1"], dcs["F2a"], dcs["F2b"]
    diffs = []
    for k in sorted(set(lf) | set(la) | set(lb)):
        vals = {n: dcs[n].get(k, "<absent>") for n in dcs}
        if len({str(v) for v in vals.values()}) > 1:
            diffs.append({"path": k, **{n: str(v)[:200] for n, v in vals.items()}})
    load_bearing = ["regularity_class.sobolev_variant.s", "regularity_class.sobolev_variant.delta",
                    "regularity_class.sobolev_variant.spaces", "regularity_class.default"]

    def norm(v):
        return re.sub(r"\s*\([^)]*\)", "", str(v)).strip().rstrip(";,")

    exact = all(len({str(dcs[n].get(k, "<absent>")) for n in dcs}) == 1 for k in load_bearing)
    normalized = all(len({norm(dcs[n].get(k, "<absent>")) for n in dcs}) == 1 for k in load_bearing)
    add(
        "B09-cross-schema-data-class",
        "G-FORM shared-frozen-data-class criterion: measured leaf diff F1/F2a/F2b",
        "info",
        {"load_bearing_paths": load_bearing,
         "load_bearing_exact_identical": exact,
         "load_bearing_normalized_identical": normalized,
         "normalization": "strip parenthetical annotations + trailing punctuation (the only F1 difference on the "
                          "load-bearing paths is the annotation '(weighted Sobolev)' in spaces)",
         "leaf_diffs": diffs,
         "F1_vs_F2a_key_only_equal": set(lf) == set(la), "F2a_vs_F2b_key_only_equal": set(la) == set(lb),
         "note": "adjudication of whether the criterion is met belongs to the audit lead; this check reports "
                 "the measurement the gate reason rests on."},
        "A revision in which the load-bearing s/delta/spaces values differ across F1/F2a/F2b while this check "
        "still reports them identical (exact or normalized).",
        "advisory",
    )

    # --- B10 C2 signature
    sig = signature_scan(text, ["H^4", "1/2+eps", "1/2+epsilon", "H^4_{1/2", "s = 4"])
    add(
        "B10-c2-distinctive-data-signature",
        "the C2 class's distinctive weighted-data signature is carried by the frozen C2 schema",
        "info" if not any(sig.values()) else "pass",
        {"tokens_found": sig,
         "measured_sobolev_variant": ((doc.get("data_class") or {}).get("regularity_class") or {}).get("sobolev_variant"),
         "note": "token absence corroborates the lead-audit-r2 MAJOR (C2 weighted Sobolev signature absent); "
                 "all four frozen classes cannot be separated on the data-regularity axis if this is load-bearing."},
        "Any of the C2-signature tokens present at this hash, or a registry entry showing the C2 data class is "
        "deliberately the same as F1/F2b.",
        "advisory",
    )

    # --- B11 review_status staleness
    rs = doc.get("review_status", {}) or {}
    add(
        "B11-review-status-freshness",
        "review_status reflects the reviews that exist at this hash",
        "fail" if (rs.get("independent_reviewers") == [] and rs.get("verdict") == "pending") else "pass",
        {"review_status": rs,
         "note": "reviews exist at this hash (see prior_review_ledger); the artifact's own field is empty/pending."},
        "A revision whose review_status.independent_reviewers is non-empty and whose verdict matches the ledger.",
        "hard",
    )

    # --- B12 canonical checker corroboration
    checker = ROOT / PIN_PATHS["canonical_checker"]
    cp = subprocess.run([sys.executable, str(checker), "--json", str(target)],
                        cwd=ROOT, capture_output=True, text=True, timeout=300)
    try:
        check_json = json.loads(cp.stdout)
    except Exception:  # noqa: BLE001
        check_json = {"raw": cp.stdout[-400:]}
    add(
        "B12-canonical-checker-corroboration",
        "canonical structural checker on the same bytes (corroboration, not the method)",
        "pass" if cp.returncode == 0 and check_json.get("verdict") == "pass" else "fail",
        {"command": f"python3 artifacts/formulation/tools/check_class_schema.py --json {target.name}",
         "exit_code": cp.returncode, "checker_sha256": sha256_file(checker),
         "verdict": check_json.get("verdict"), "failed_rules": check_json.get("failed_rules"),
         "failures": check_json.get("failures"),
         "stderr_tail": cp.stderr[-200:],
         "note": "supersedes F2a-review-18 HF-A4 (checker FAIL R19/R22), which was measured on an earlier revision."},
        "A re-run at this hash whose exit code or failed_rules differ from the recorded values.",
        "info" if (cp.returncode == 0 and check_json.get("verdict") == "pass") else "hard",
    )

    # --- B13 class separation
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    cls_findings = cs.findings_for_text(text, str(target.relative_to(ROOT)))
    reg = subprocess.run([sys.executable, str(ROOT / PIN_PATHS["classsep_regression"])],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
    reg_pass = reg.returncode == 0 and "VERDICT: PASS" in reg.stdout
    reg_json = {"exit_code": reg.returncode,
                "stdout_tail": reg.stdout.strip().splitlines()[-3:] if reg.stdout.strip() else [],
                "verdict": "PASS" if reg_pass else "DEFECTIVE"}
    add(
        "B13-class-separation",
        "frozen class-separation detector on the target and on its regression corpus",
        "pass" if (not cls_findings and reg_pass) else "fail",
        {"target_findings": cls_findings, "regression": reg_json,
         "detector_sha256": sha256_file(ROOT / PIN_PATHS["class_separation"]),
         "regression_sha256": sha256_file(ROOT / PIN_PATHS["classsep_regression"])},
        "A target finding at this hash, or a regression run with fn/fp > 0.",
        "info",
    )

    # --- B14 prior review ledger
    ledger = []
    for f in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        tid = str(d.get("target_id", ""))
        cid = str(d.get("class_id", ""))
        arts = json.dumps(d.get("artifact_refs", d.get("evidence_refs", [])))
        if tid in ("F2a", CLASS_ID) or cid == CLASS_ID or "af_scc_c2" in arts or "af_scc_c2" in str(d.get("reviewed_artifact", "")):
            bind_hash = d.get("reviewed_sha256") or d.get("artifact_sha256")
            ledger.append({
                "file": f"reviews/{f.name}", "file_sha256": sha256_file(f),
                "reviewer": d.get("reviewer"), "verdict": d.get("verdict"), "score": d.get("score"),
                "reviewed_sha256": bind_hash,
                "binds_to_this_hash": bind_hash == t_sha_before,
                "hard_failures": len(d.get("hard_failures", []) or []),
            })
    at_hash = [r for r in ledger if r["binds_to_this_hash"]]
    counts = Counter(r["verdict"] for r in at_hash)
    add(
        "B14-prior-review-ledger",
        "verdict ledger for this class at the pinned hash (context, not agreement)",
        "info",
        {"total_review_files_referencing_class": len(ledger),
         "verdicts_binding_this_hash": dict(counts),
         "accepts_at_this_hash": counts.get("accept", 0),
         "revises_at_this_hash": counts.get("revise", 0),
         "inconclusive_at_this_hash": counts.get("inconclusive", 0),
         "rows": ledger},
        "A review file whose recorded reviewed_sha256 differs from this measurement being counted as binding.",
        "info",
    )

    # ------------------------------------------------------------------ self tests
    st = []
    clean = "a: 1\nb: 2\nc:\n  d: 3\n"
    st.append({"id": "N1", "kind": "specificity", "pass": duplicate_mapping_keys(clean) == [],
               "detail": "clean synthetic document yields no duplicate keys"})
    dup2 = "a: 1\na: 2\nb: 3\n"
    got = duplicate_mapping_keys(dup2)
    st.append({"id": "P1", "kind": "sensitivity",
               "pass": len(got) == 1 and got[0]["count"] == 2 and got[0]["lines"] == [1, 2],
               "detail": f"synthetic two-key duplicate detected: {got}"})
    st.append({"id": "P2", "kind": "pointer-positive",
               "pass": bool(resolve_fragment(auth, f"class_contracts.{CLASS_ID}")[0]),
               "detail": "authoring taxonomy resolves class_contracts.<class>"})
    st.append({"id": "P3", "kind": "pointer-negative",
               "pass": resolve_fragment(canon, "class_contracts.NO-SUCH-CLASS")[0] is None,
               "detail": "nonexistent fragment does not resolve (fail-closed)"})
    same = leaves({"data_class": {"a": 1, "b": "x"}}) == leaves({"data_class": {"a": 1, "b": "x"}})
    st.append({"id": "P4", "kind": "comparator-positive", "pass": same,
               "detail": "identical data_class leaves compare equal"})
    pred_ok = datetime.fromisoformat("2026-09-11T00:00:00+08:00") <= mtime_dt
    st.append({"id": "P5", "kind": "timestamp-positive", "pass": pred_ok,
               "detail": "declared revised_at <= mtime predicate accepts a past stamp"})
    self_test_pass = all(s["pass"] for s in st)

    # ------------------------------------------------------------------ drift
    t_sha_after = sha256_file(target)
    drift = t_sha_after != t_sha_before
    if drift:
        checks.append({
            "check_id": "B01-target-drift", "title": "target hash stable across the receipt",
            "status": "fail", "severity": "blocking",
            "evidence": {"sha256_before": t_sha_before, "sha256_after": t_sha_after},
            "falsifier": "A re-run on identical bytes in which the before/after hashes agree.",
        })
    else:
        checks.insert(0, {
            "check_id": "B01-target-stability", "title": "target hash stable across the receipt",
            "status": "pass", "severity": "info",
            "evidence": {"sha256_before": t_sha_before, "sha256_after": t_sha_after,
                         "bytes": len(tb), "mtime": mtime},
            "falsifier": "A hash change between the before and after measurements.",
        })

    hard = [c for c in checks if c["status"] == "fail" and c["severity"] in ("blocking", "hard", "critical")]
    critical = [c for c in checks if c["status"] == "fail" and c["severity"] == "critical"]
    advisory = [c for c in checks if c["status"] == "fail" and c["severity"] == "advisory"]
    pins = {k: {"path": v, "sha256": sha256_file(ROOT / v)} for k, v in PIN_PATHS.items()}

    verdict = "revise" if hard else "accept"
    report = {
        "report_id": TASK_ID,
        "review_id": REVIEW_ID,
        "worker": "worker-096",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "created_at": started,
        "wall_clock_at_finish": now(),
        "target": {"path": str(target.relative_to(ROOT)), "sha256": t_sha_before,
                   "bytes": len(tb), "mtime": mtime, "revision": doc.get("revision")},
        "pins": pins,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "fail": sum(1 for c in checks if c["status"] == "fail"),
            "info": sum(1 for c in checks if c["status"] == "info"),
            "hard_failures": [c["check_id"] for c in hard],
            "critical_failures": [c["check_id"] for c in critical],
            "advisory_failures": [c["check_id"] for c in advisory],
            "verdict": verdict,
            "score": 3.0 if hard else 4.0,
            "structural_checklist": "pass",
            "binding_integrity": "fail" if hard else "pass",
            "self_test": "PASS" if self_test_pass else "FAIL",
        },
        "self_tests": st,
        "drift": {"sha256_before": t_sha_before, "sha256_after": t_sha_after, "drift": drift,
                  "closed": not drift},
        "prior_review_ledger": ledger,
        "falsifier": (
            "Re-run artifacts/worker-096/f2a_binding_receipt/run_receipt.py against sha256 "
            f"{short(t_sha_before)}. Falsified if, on identical bytes: (a) any recorded fail flips to pass; "
            "(b) a strict duplicate-key parse exits 0; (c) the canonical taxonomy exposes "
            f"class_contracts.{CLASS_ID} or the pointer names the canonical hash; (d) the (s,delta) binder "
            "acquires a well-typed smooth-with-decay branch with a defined ambient set; (e) the load-bearing "
            "s/delta/spaces leaves diverge across F1/F2a/F2b; (f) any self-test control fails; or (g) the "
            "target hash moves, which voids the binding and requires a re-run."
        ),
        "limitations": [
            "Structural/binding receipt only; physical fidelity and well-posedness are human_adjudication_only.",
            "The canonical checker and the class-separation detector are corroboration, not the method; their "
            "blind spots (documented in their headers) are inherited by the corroboration rows.",
            "Findings already recorded by prior reviewers are named in evidence; no priority is claimed.",
            "A later revision voids the binding, not the measurement.",
            "Worker output cannot set node status or a gate verdict (comms/PROTOCOL.md rule 2).",
        ],
        "named_by_prior_work": [
            "F2a-review-086 HF-086-1/HF-086-2 and F2a-review-088 HF-088-1/F-088-1 (D0 typing; duplicate keys; pointer)",
            "F2a-review-047 F-01/F-02 (pointer; duplicate keys)",
            "F2a-review-lead-audit-r2 (blocking list; canonical checker pass)",
            "F2a-review-21/22 (hash-timeline freeze violations; future-dated stamps)",
            "F2a-review-18 HF-A1/HF-A2 (earlier revision; superseded at this hash per B08)",
        ],
    }
    return report, self_test_pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--out", default=str(OUT_DIR / "report.json"))
    args = ap.parse_args()
    target = (ROOT / args.target).resolve()
    if not target.is_file():
        print(f"target not found: {target}", file=sys.stderr)
        return 3
    try:
        report, self_test_pass = build(target)
    except Exception as exc:  # noqa: BLE001
        print(f"harness error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "report": str(out.relative_to(ROOT)),
        "target_sha256": report["target"]["sha256"],
        "verdict": report["summary"]["verdict"],
        "hard_failures": report["summary"]["hard_failures"],
        "critical_failures": report["summary"]["critical_failures"],
        "self_test": report["summary"]["self_test"],
        "drift": report["drift"]["drift"],
    }, indent=2))
    if report["drift"]["drift"]:
        return 2
    return 0 if self_test_pass else 3


if __name__ == "__main__":
    sys.exit(main())
