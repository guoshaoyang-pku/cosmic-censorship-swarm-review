#!/usr/bin/env python3
"""W090-F0-REV26: independent, hash-bound audit of FROZEN.json revision 26.

Task (class-scoped: AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN):
verify the rev26 adjudication request claim that
  research_map/formulation_taxonomy.yaml (276009f4..., declared F0 taxonomy)
and
  artifacts/formulation/formulation_taxonomy.yaml (c8e979a1..., class-contract
  supplement)
are two DIFFERENT artifacts rather than two divergent mirrors of one artifact,
and that manifest/files-bindings/pointers/clock are internally consistent at the
revision-26 bytes.

Method: pure measurement. Reads bytes, hashes them, parses YAML/JSON, and
compares. Writes report.json in this directory. No network, no map mutation,
no edits to any reviewed artifact. Exit code is 0 always; the verdict is in the
report. Use --expect to force a reviewed-hash guard (freeze rule).

Output: artifacts/worker-090/f0_rev26_adjudication/report.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
CORPORA = {
    "schemas/taxonomy_cases.jsonl": "F0",
    "schemas/f1_falsifier_tests.jsonl": "F1",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> datetime:
    return datetime.now(CST)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_ts(s: str) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def locator(p: Path, h: str | None = None) -> str:
    rel = p.relative_to(ROOT)
    return f"{rel}#{(h or sha256(p))[:12]}"


def yaml_dup_keys(p: Path) -> dict:
    """Top-level duplicate keys plus count of duplicates anywhere (compose-tree scan)."""
    text = p.read_text()
    try:
        node = yaml.compose(text)
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}
    dups_all: dict[str, int] = {}
    top: list[str] = []

    def walk(n, depth=0):
        if isinstance(n, yaml.MappingNode):
            seen: dict[str, int] = {}
            for k, v in n.value:
                key = getattr(k, "value", None)
                seen[key] = seen.get(key, 0) + 1
                walk(v, depth + 1)
            for key, c in seen.items():
                if c > 1:
                    dups_all[key] = dups_all.get(key, 0) + (c - 1)
                    if depth == 0:
                        top.append(key)

    if node is not None:
        walk(node)
    return {"top_level_duplicates": sorted(top), "duplicate_key_counts": dups_all}


def resolve_fragment(tree: dict, fragment: str):
    """Resolve 'class_contracts.CLASS' style dotted fragment in a parsed YAML tree."""
    cur = tree
    parts = fragment.split(".")
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return {"resolved": False, "failed_at": part}
        cur = cur[part]
    return {"resolved": True, "type": type(cur).__name__,
            "keys": list(cur.keys()) if isinstance(cur, dict) else None}


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def normalize_conclusion_type(token) -> str | None:
    """Map the canonical and supplement conclusion-type vocabularies to one token.

    The two F0 artifacts use different vocabularies for the same content:
      weak_cosmic_censorship                       <-> weak_cosmic_censorship
      strong_cosmic_censorship_C2                  <-> scc_c2_future_inextendibility
      strong_cosmic_censorship_C0                  <-> scc_c0_future_inextendibility
    The mapping is declared here so a reader can falsify it; an unmapped token
    returns None and is reported rather than silently compared.
    """
    if not isinstance(token, str):
        return None
    t = token.strip().lower()
    if t in ("weak_cosmic_censorship", "wcc", "weak_cosmic_censorship_wcc"):
        return "WCC"
    if "strong" in t or t.startswith("scc"):
        for reg in ("c0", "c2"):
            if re.search(rf"(^|[^a-z0-9]){reg}([^a-z0-9]|$)", t) or t.endswith(reg):
                return f"SCC-{reg.upper()}"
        return "SCC-?"
    return None


def class_field_diff(canon_cls: dict, supp_cls: dict) -> dict:
    """Report shared top-level fields whose values differ (semantic comparison)."""
    shared = sorted(set(canon_cls) & set(supp_cls))
    equal, differ = [], []
    for k in shared:
        (equal if canon(canon_cls[k]) == canon(supp_cls[k]) else differ).append(k)
    only_c = sorted(set(canon_cls) - set(supp_cls))
    only_s = sorted(set(supp_cls) - set(canon_cls))
    diffs = {}
    for k in differ:
        diffs[k] = {"canonical": str(canon_cls[k])[:400], "supplement": str(supp_cls[k])[:400]}
    return {"shared_fields": shared, "equal_fields": equal, "differing_fields": differ,
            "only_in_canonical": only_c, "only_in_supplement": only_s,
            "differing_values": diffs}


def main() -> int:
    checks: list[dict] = []
    wall = now()

    def check(cid, name, status, measured, expected=None, detail=""):
        checks.append({"check_id": cid, "name": name, "status": status,
                       "measured": measured, "expected": expected, "detail": detail})

    if not FROZEN.exists():
        print(json.dumps({"error": "FROZEN.json missing"}))
        return 3

    frozen_raw = FROZEN.read_text()
    frozen = json.loads(frozen_raw)
    rev = frozen.get("revision")
    frozen_sha = sha256(FROZEN)
    f0c_sha, f0s_sha = sha256(F0_CANON), sha256(F0_SUPP)

    # C1 manifest files vs disk -------------------------------------------------
    mism = []
    measured_files = {}
    for rel, meta in (frozen.get("files") or {}).items():
        p = ROOT / rel
        if not p.exists():
            mism.append({"path": rel, "reason": "missing", "declared": meta.get("sha256")})
            continue
        h, n = sha256(p), p.stat().st_size
        measured_files[rel] = {"sha256": h, "bytes": n}
        if h != meta.get("sha256") or (meta.get("bytes") is not None and n != meta["bytes"]):
            mism.append({"path": rel, "declared": meta.get("sha256"), "measured": h,
                         "declared_bytes": meta.get("bytes"), "measured_bytes": n})
    check("C1-manifest-files", "FROZEN.files hashes match disk",
          "PASS" if not mism else "FAIL",
          {"n_files": len(frozen.get("files") or {}), "mismatches": mism}, "0 mismatches")

    # C2 manifest clock ---------------------------------------------------------
    fat = parse_ts(frozen.get("frozen_at"))
    skew = (fat - wall).total_seconds() if fat else None
    check("C2-manifest-clock", "frozen_at is not future-dated vs wall clock",
          "PASS" if skew is not None and skew <= 5 else "FAIL",
          {"frozen_at": frozen.get("frozen_at"), "wall_clock": iso(wall),
           "skew_seconds": skew}, "skew <= 5s",
          "CF-14 family; rev26 declares it corrected")

    # C2b effective (last-wins) artifact timestamps ------------------------------
    clock_rows = {}
    future_artifacts = []
    for p in [F0_SUPP] + [ROOT / s for s in SCHEMAS]:
        tree = yaml.safe_load(p.read_text())  # PyYAML last-wins on duplicate keys
        row = {"revised_at": tree.get("revised_at"), "revised_at_unused": tree.get("revised_at_unused"),
               "timestamp_provenance": str(tree.get("timestamp_provenance"))[:160],
               "mtime": iso(datetime.fromtimestamp(p.stat().st_mtime, CST))}
        rt = parse_ts(tree.get("revised_at"))
        row["effective_revised_at_future_seconds"] = (rt - wall).total_seconds() if rt else None
        if row["effective_revised_at_future_seconds"] is not None and row["effective_revised_at_future_seconds"] > 5:
            future_artifacts.append(str(p.relative_to(ROOT)))
        clock_rows[str(p.relative_to(ROOT))] = row
    check("C2b-artifact-clocks", "effective artifact revised_at not future-dated vs wall clock",
          "PASS" if not future_artifacts else "FAIL",
          {"by_file": clock_rows, "wall_clock": iso(wall), "future_dated": future_artifacts},
          "skew <= 5s",
          "PyYAML last-wins semantics used deliberately: on duplicated keys the effective value is the last occurrence (CF-14 family)")

    # C3 manifest self-consistency: one hash per logical artifact ---------------
    logical = frozen.get("logical_artifacts") or {}
    log_bad = []
    for name, meta in logical.items():
        p = ROOT / meta.get("path", "")
        m = sha256(p) if p.exists() else None
        if m != meta.get("sha256"):
            log_bad.append({"logical": name, "declared": meta.get("sha256"), "measured": m,
                            "path": meta.get("path")})
    check("C3-logical-artifacts", "logical_artifacts pins match disk",
          "PASS" if not log_bad else "FAIL",
          {"n": len(logical), "mismatches": log_bad}, "0 mismatches")

    # C4 two-artifact claim: key sets, class ids, class content -----------------
    c_tree = yaml.safe_load(F0_CANON.read_text())
    s_tree = yaml.safe_load(F0_SUPP.read_text())
    c_ids = list(c_tree.get("class_ids") or [])
    c_classes = c_tree.get("classes") or {}
    s_frozen_ids = list(s_tree.get("frozen_classes") or [])
    s_contracts = s_tree.get("class_contracts") or {}
    keys_c, keys_s = set(c_tree), set(s_tree)
    check("C4a-distinct-key-sets", "declared taxonomy and supplement have distinct role keys",
          "PASS" if ({"classes", "class_ids"} <= keys_c and {"class_contracts", "frozen_classes"} <= keys_s
                     and "classes" not in keys_s and "class_contracts" not in keys_c) else "FAIL",
          {"canonical_has": sorted(keys_c & {"classes", "class_ids", "class_contracts",
                                             "frozen_classes", "axis_registry", "implication_ledger"}),
           "supplement_has": sorted(keys_s & {"classes", "class_ids", "class_contracts",
                                              "frozen_classes", "axis_registry", "implication_ledger"}),
           "top_level_key_overlap": sorted(keys_c & keys_s)},
          "canonical {class_ids,classes}; supplement {class_contracts,frozen_classes}")

    same_ids = sorted(c_ids) == sorted(s_frozen_ids) == sorted(s_contracts.keys())
    check("C4b-class-id-agreement", "same four frozen class ids in both F0 artifacts",
          "PASS" if same_ids and len(c_ids) == 4 else "FAIL",
          {"canonical": c_ids, "supplement_frozen_classes": s_frozen_ids,
           "supplement_contract_keys": list(s_contracts.keys())}, "identical 4-element sets")

    per_class = {}
    conflicting = []
    style_divergent = []
    for cid in sorted(set(c_ids) | set(s_contracts)):
        cc, sc = c_classes.get(cid), s_contracts.get(cid)
        if not isinstance(cc, dict) or not isinstance(sc, dict):
            per_class[cid] = {"present_canonical": isinstance(cc, dict),
                              "present_supplement": isinstance(sc, dict)}
            conflicting.append({"class_id": cid, "reason": "missing in one artifact"})
            continue
        d = class_field_diff(cc, sc)
        raw_canon = cc.get("conclusion", {}).get("type") if isinstance(cc.get("conclusion"), dict) else None
        raw_supp = sc.get("conclusion_type")
        nc, ns = normalize_conclusion_type(raw_canon), normalize_conclusion_type(raw_supp)
        d["conclusion_type"] = {"canonical_raw": raw_canon, "supplement_raw": raw_supp,
                                "canonical_normalized": nc, "supplement_normalized": ns,
                                "equivalent": nc is not None and nc == ns,
                                "raw_style_divergent": raw_canon != raw_supp}
        per_class[cid] = d
        if nc is None or ns is None or nc != ns:
            conflicting.append({"class_id": cid, "reason": "conclusion_type mismatch",
                                "canonical": raw_canon, "supplement": raw_supp})
        elif raw_canon != raw_supp:
            style_divergent.append(cid)
    check("C4c-class-content", "no conclusion_type contradiction across the two artifacts",
          "FAIL" if conflicting else ("WARN" if style_divergent else "PASS"),
          {"per_class": per_class, "contradictions": conflicting,
           "raw_style_divergent_classes": style_divergent,
           "normalization_rule": "weak|wcc -> WCC; strong|scc + regularity token -> SCC-C0 / SCC-C2; mapping declared in script, falsifiable"},
          "normalized tokens equal per class",
          "shared fields compared by canonical JSON; differing hypotheses/exclusions wording is a dual-source risk, not a proven contradiction; raw token styles differ by design vocabulary, normalized comparison is the substantive test")

    # C5 pointer resolution ------------------------------------------------------
    ptr_rows = []
    ptr_ok = True
    for rel in SCHEMAS:
        d = yaml.safe_load((ROOT / rel).read_text())
        ptr = d.get("class_contract_pointer")
        row = {"schema": rel, "pointer": ptr, "canonical": None, "supplement": None}
        m = re.match(r"^([^#]+)#(.+)$", ptr or "")
        if not m:
            row["canonical"] = {"resolved": False, "failed_at": "malformed"}
            row["supplement"] = {"resolved": False, "failed_at": "malformed"}
        else:
            frag = m.group(2)
            row["canonical"] = resolve_fragment(c_tree, frag)
            row["supplement"] = resolve_fragment(s_tree, frag)
            if not (row["supplement"].get("resolved") and not row["canonical"].get("resolved")):
                ptr_ok = False
        ptr_rows.append(row)
    check("C5-contract-pointers", "each schema class_contract_pointer resolves only in the supplement",
          "PASS" if ptr_ok else "FAIL", {"rows": ptr_rows},
          "resolved=supplement, unresolved=canonical",
          "policy note: canonical-path policy says schemas/*.yaml is authoritative; the pointer targets the authoring supplement by design per rev26")

    # C6 f0_binding of the three schemas ----------------------------------------
    bind_rows = []
    bind_bad = []
    for rel in SCHEMAS:
        d = yaml.safe_load((ROOT / rel).read_text())
        b = d.get("f0_binding") or {}
        row = {"schema": rel, "declared_f0_artifact": b.get("declared_f0_artifact"),
               "declared_f0_sha256": b.get("declared_f0_sha256"),
               "class_contract_supplement": b.get("class_contract_supplement"),
               "checked_at": b.get("checked_at")}
        row["declared_matches_measured"] = b.get("declared_f0_sha256") == f0c_sha
        row["supplement_matches_measured"] = None
        if b.get("class_contract_supplement"):
            sp = ROOT / b["class_contract_supplement"]
            row["supplement_matches_measured"] = sp.exists() and sha256(sp) == f0s_sha
        ct = parse_ts(b.get("checked_at"))
        row["checked_at_future_seconds"] = (ct - wall).total_seconds() if ct else None
        if not row["declared_matches_measured"] or row["supplement_matches_measured"] is False:
            bind_bad.append(row)
        bind_rows.append(row)
    check("C6-schema-f0-binding", "f0_binding declares the measured canonical F0 and supplement",
          "PASS" if not bind_bad else "FAIL",
          {"rows": bind_rows, "measured_canonical": f0c_sha[:16], "measured_supplement": f0s_sha[:16]},
          "all declared == measured")
    future_binds = [r["schema"] for r in bind_rows
                    if r["checked_at_future_seconds"] is not None and r["checked_at_future_seconds"] > 5]
    check("C6b-binding-clock", "f0_binding.checked_at not future-dated",
          "PASS" if not future_binds else "FAIL",
          {"future_dated_schemas": future_binds,
           "checked_at": [r["checked_at"] for r in bind_rows], "wall_clock": iso(wall)},
          "skew <= 5s", "machine-readable timestamp discipline (CF-14 family)")

    # C7 downstream corpora pins ------------------------------------------------
    corpus_rows = {}
    for rel, node in CORPORA.items():
        p = ROOT / rel
        expected_hash = f0c_sha if node == "F0" else sha256(ROOT / "schemas/af_wcc_vacuum.yaml")
        pins, rows = set(), 0
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rows += 1
            try:
                r = json.loads(line)
            except Exception:
                continue
            for k in ("binding_sha256", "binding_status", "taxonomy_ref", "binding_ref",
                      "rebind_note", "rebound_at"):
                if k in r:
                    for h in re.findall(r"\b([0-9a-f]{12,64})\b", str(r[k])):
                        pins.add(h)
        stale = [x for x in pins if not (expected_hash.startswith(x) or x.startswith(expected_hash[:12]))]
        corpus_rows[rel] = {"node": node, "rows": rows, "pins": sorted(pins)[:6],
                            "expected_node_hash": expected_hash[:16],
                            "pins_not_matching_expected": sorted(stale)[:6]}
    stale_corpora = [rel for rel, r in corpus_rows.items() if r["pins_not_matching_expected"]]
    check("C7-corpus-pins", "downstream corpus pins equal the frozen node hashes",
          "PASS" if not stale_corpora else "FAIL",
          {"corpora": corpus_rows, "stale": stale_corpora},
          "0 stale pins", "life03-repin-claims covers this repair; measured as-is")

    # C8 duplicate machine-readable keys ---------------------------------------
    dup_rows = {}
    for p in [FROZEN, F0_CANON, F0_SUPP] + [ROOT / s for s in SCHEMAS]:
        dup_rows[str(p.relative_to(ROOT))] = yaml_dup_keys(p)
    dup_bad = [k for k, v in dup_rows.items() if v.get("duplicate_key_counts")]
    check("C8-duplicate-keys", "no duplicate mapping keys in machine-readable artifacts under audit",
          "PASS" if not dup_bad else "FAIL",
          {"by_file": dup_rows}, "no duplicate keys",
          "F1 duplicate revised_at/revised_at_unused is a known open repair item")

    # ---- verdict --------------------------------------------------------------
    hard = [c for c in checks if c["status"] == "FAIL"]
    warn = [c for c in checks if c["status"] == "WARN"]
    verdict = "revise" if hard else "accept"
    claim_supported = next(c["status"] for c in checks if c["check_id"] == "C4a-distinct-key-sets") == "PASS" \
        and next(c["status"] for c in checks if c["check_id"] == "C4b-class-id-agreement") == "PASS"
    report = {
        "report_id": "W090-F0-REV26-ADJUDICATION",
        "task": "verify FROZEN rev26 claim: canonical declared-F0 and authoring class-contract supplement are two different artifacts, not divergent mirrors; report binding/clock defects",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "emitted_at": iso(wall),
        "reviewed": {
            "frozen_path": "artifacts/formulation/FROZEN.json",
            "frozen_revision": rev,
            "frozen_sha256": frozen_sha,
            "canonical_f0": {"path": "research_map/formulation_taxonomy.yaml", "sha256": f0c_sha},
            "supplement_f0": {"path": "artifacts/formulation/formulation_taxonomy.yaml", "sha256": f0s_sha},
        },
        "rev26_claim_supported_by_bytes": claim_supported,
        "verdict": verdict,
        "checks": checks,
        "hard_failures": [c["check_id"] for c in hard],
        "warnings": [c["check_id"] for c in warn],
        "next_falsifier": "re-run this script after the controller adjudicates REC-1/REC-2 and the lead repins taxonomy_cases.jsonl: a stale pin surviving, a duplicate key surviving, or checked_at still ahead of wall clock at the next revision falsifies closure of the clock/repin items.",
        "policy_note": "canonical-path policy (ASTRA_HANDOFF) requires artifacts/formulation/** published byte-identically before verdicts bind; rev26 withholds that and requests adjudication. This report measures the bytes and does not decide the policy question.",
        "reproduction": "python3 artifacts/worker-090/f0_rev26_adjudication/audit_f0_rev26.py",
        "authority_note": "worker evidence only; cannot set gate verdict or node status",
    }
    if "--expect" in sys.argv:
        want = sys.argv[sys.argv.index("--expect") + 1]
        if frozen_sha != want:
            report["verdict"] = "inconclusive"
            report["hard_failures"].append("FREEZE-GUARD")
            report["freeze_guard"] = {"expected": want, "measured": frozen_sha, "moved": True}
    HERE.mkdir(parents=True, exist_ok=True)
    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out.relative_to(ROOT)), "verdict": report["verdict"],
                      "hard_failures": report["hard_failures"], "warnings": report["warnings"],
                      "claim_supported": claim_supported,
                      "frozen_sha256": frozen_sha[:16],
                      "report_sha256": sha256(out)[:16]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
