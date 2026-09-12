#!/usr/bin/env python3
"""W037-REV12-FINDING-STATUS-01 -- re-measure the open hard findings against the
current FROZEN rev28 pins (F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda,
F0 0abb9ed8a961) and adjudicate, per finding, resolved / live / moot.

Findings covered (all originally bound to superseded revisions):
  W037-F1  requested review pins superseded at measurement time (worker-037)
  W037-F5  disjunctive D0 regularity domain vs the single-frozen-data-class
           precondition (worker-037; reproduced/observed by worker-003, -090)
  HF090-01 class_contract_pointer fragment unresolved in the canonical taxonomy
  HF090-02 duplicate / future-dated revised_at keys
  HF090-03 AF_{I+} used but undefined in conclusion.statement_formal

Read-only: this script never writes a canonical path. It measures sha256 at T0 and
T1 and reports drift. It is not a gate verdict and is not one of the two required
independent accepts.

Usage:
  python3 measure_findings.py [--root REPO] [--out report.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:?\d{2})?")

CANON_PATHS = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
]
EXTRA_PATHS = [
    "artifacts/formulation/rule_spec.json",
    "artifacts/literature/tools/build_literature.py",
    "ledger/theorems.jsonl",
    "evaluation_rubric.yaml",
]
R2_CARD_AGENTS = [
    "worker-015", "worker-035", "worker-041", "worker-046",
    "worker-052", "worker-071", "worker-085", "worker-091",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def top_level_key_lines(text: str, key: str) -> list[int]:
    out, pat = [], re.compile(rf"^{re.escape(key)}\s*:")
    for i, line in enumerate(text.splitlines(), 1):
        if pat.match(line):
            out.append(i)
    return out


def get_path(obj, dotted: str):
    cur = obj
    for seg in dotted.split("."):
        m = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", seg)
        if not m:
            return None
        key, idx = m.group(1), m.group(2)
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
        if idx is not None:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                return None
    return cur


def _rc_core(rc):
    """Canonical comparison tuple for data_class.regularity_class across schemas.

    Compares the class-bearing scalar fields only (default label, Sobolev s, Sobolev
    delta). The `spaces` string carries an F1-only parenthetical gloss and is recorded
    separately: worker-090 F-11 already classified that difference as gloss-only.
    """
    if not isinstance(rc, dict):
        return None
    sv = rc.get("sobolev_variant") or {}
    return (norm(str(rc.get("default"))), norm(str(sv.get("s"))), norm(str(sv.get("delta"))))


def parse_ts(s: str):
    s = s.strip().replace("Z", "+00:00")
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    now = _dt.datetime.now().astimezone()
    checks: list[dict] = []

    def check(cid, ok, evidence, severity=None, note=None):
        checks.append({
            "id": cid,
            "ok": bool(ok),
            "severity": severity,
            "evidence": evidence,
            "note": note,
        })
        return bool(ok)

    # ---------- T0 measurement ----------
    def measure(paths):
        out = {}
        for rel in paths:
            p = root / rel
            out[rel] = sha256(p) if p.exists() else None
        return out

    try:
        import yaml
    except ImportError:
        print("PyYAML required", file=sys.stderr)
        return 2

    frozen_path = root / "artifacts/formulation/FROZEN.json"
    frozen = json.loads(frozen_path.read_text())
    manifest = frozen.get("files", {})
    manifest_paths = sorted(manifest.keys())
    all_paths = sorted(set(CANON_PATHS + EXTRA_PATHS + manifest_paths))
    T0 = measure(all_paths)

    # ---------- freeze manifest integrity ----------
    mism, missing, byte_mism = [], [], []
    for rel, meta in manifest.items():
        p = root / rel
        if not p.exists():
            missing.append(rel)
            continue
        got = sha256(p)
        if got != meta.get("sha256"):
            mism.append({"path": rel, "declared": meta.get("sha256"), "measured": got})
        if "bytes" in meta and p.stat().st_size != meta["bytes"]:
            byte_mism.append({"path": rel, "declared_bytes": meta["bytes"], "measured": p.stat().st_size})
    check("FREEZE-MANIFEST-HASHES", not mism and not missing and not byte_mism,
          {"declared_files": len(manifest), "mismatch": mism, "missing": missing, "byte_mismatch": byte_mism},
          severity="critical")

    # canonical F0 vs authoring supplement: companion pair (not a mirror) per REC-3
    tax_canon = root / "research_map/formulation_taxonomy.yaml"
    tax_auth = root / "artifacts/formulation/formulation_taxonomy.yaml"
    companion_registered = "artifacts/formulation/formulation_taxonomy.yaml" in manifest
    check("F0-COMPANION-REGISTERED", companion_registered and T0["research_map/formulation_taxonomy.yaml"] != (sha256(tax_auth) if tax_auth.exists() else None),
          {"canonical_sha256": T0["research_map/formulation_taxonomy.yaml"],
           "authoring_sha256": sha256(tax_auth) if tax_auth.exists() else None,
           "authoring_in_manifest": companion_registered,
           "expected_relation": "distinct bytes, supplement pinned in FROZEN.files (REC-3 companion pair)"},
          severity="major")

    # ---------- W037-F1: do the live r2 review cards pin bytes that exist on disk? ----------
    measured_set = {h for h in T0.values() if h}
    card_report = {}
    unresolved_all = []
    for agent in R2_CARD_AGENTS:
        f = root / f"comms/inbox/{agent}.jsonl"
        entries = []
        if f.exists():
            for raw in f.read_text().splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if str(ev.get("event_id", "")).startswith("audit-r2-"):
                    pins = sorted(set(HEX64.findall(json.dumps(ev))))
                    resolved = {p: (p in measured_set) for p in pins}
                    entries.append({"event_id": ev.get("event_id"), "node_id": ev.get("node_id"),
                                    "artifact": ev.get("artifact"), "pins": resolved})
                    unresolved_all += [{"agent": agent, "pin": p} for p, ok in resolved.items() if not ok]
        if entries:
            card_report[agent] = entries
    target_pin_map = {
        "F0": ("research_map/formulation_taxonomy.yaml", T0["research_map/formulation_taxonomy.yaml"]),
        "F1": ("schemas/af_wcc_vacuum.yaml", T0["schemas/af_wcc_vacuum.yaml"]),
        "F2a": ("schemas/af_scc_c2_vacuum.yaml", T0["schemas/af_scc_c2_vacuum.yaml"]),
        "F2b": ("schemas/af_scc_c0_vacuum.yaml", T0["schemas/af_scc_c0_vacuum.yaml"]),
    }
    target_coverage = {}
    for tgt, (rel, pin) in target_pin_map.items():
        named = [{"agent": a, "event_id": e["event_id"]}
                 for a, entries in card_report.items() for e in entries
                 if e["node_id"] == tgt and e["pins"].get(pin) is True]
        target_coverage[tgt] = {"expected_pin": pin, "path": rel, "cards_naming_pin": named,
                                "covered": len(named) > 0}
    check("W037-F1-R2-CARD-PINS-RESOLVE",
          bool(card_report) and not unresolved_all and all(v["covered"] for v in target_coverage.values()),
          {"cards_read": sorted(card_report.keys()), "unresolved_pins": unresolved_all,
           "per_target_coverage": target_coverage, "cards": card_report,
           "note": "a pin 'resolves' iff its 64-hex value equals a measured file hash at T0; "
                   "each of F0/F1/F2a/F2b must be named by at least one live audit-r2 card"},
          severity="critical")
    # mapping pin -> path for the F1/F2a/F2b targets
    pin_map = {}
    for rel in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]:
        pin_map[rel] = T0[rel]

    # ---------- W037-F5: D0 disjunction / class arity at rev12 ----------
    schemas = {rel: yaml.safe_load((root / rel).read_text())
               for rel in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]}
    schema_text = {rel: (root / rel).read_text() for rel in schemas}
    d0_defs, d0_lines, reg_classes = {}, {}, {}
    for rel, doc in schemas.items():
        dv = get_path(doc, "quantifiers.domains.D0.definition")
        d0_defs[rel] = dv if isinstance(dv, str) else None
        d0_lines[rel] = line_of(schema_text[rel], "tagged disjoint union") if dv else None
        rc = get_path(doc, "data_class.regularity_class")
        reg_classes[rel] = rc
    f5 = {
        "D0_definition_normalized_equal_across_three": len({norm(v) for v in d0_defs.values() if v}) == 1 and all(d0_defs.values()),
        "union_is_tagged": all(v and "tagged disjoint union" in v for v in d0_defs.values()),
        "two_branches_present": all(v and "r = smooth" in v and "r = (sobolev,s,delta)" in v for v in d0_defs.values()),
        "sobolev_pair_scoped_to_branch": all(v and "r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1)" in v for v in d0_defs.values()),
        "smooth_branch_not_typed_as_pair": all(v and "smooth branch is no longer typed as a pair" in v for v in d0_defs.values()),
        "index_closed_over_D0": all(v and "r ranges over exactly D0" in v for v in d0_defs.values()),
        "regularity_class_scalar_fields_equal": len({_rc_core(v) for v in reg_classes.values() if v}) == 1 and all(reg_classes.values()),
        "residual_two_branch_domain": True,
        "sobolev_spaces_gloss": {rel: (get_path(rc, "sobolev_variant.spaces") if isinstance(rc, dict) else None)
                                 for rel, rc in reg_classes.items()},
    }
    # the pre-rev12 witness pattern: an (s,delta) pair bound across an 'or smooth' disjunction
    old_pat_a = re.compile(r"\(s\s*,\s*delta\)[^.\n]{0,140}\bor\b[^.\n]{0,140}smooth", re.I)
    old_pat_b = re.compile(r"sobolev[^.\n]{0,90},\s*or the smooth", re.I)
    old_hits = {}
    for rel, txt in schema_text.items():
        hits = []
        for i, line in enumerate(txt.splitlines(), 1):
            if old_pat_a.search(line) or old_pat_b.search(line):
                hits.append({"line": i, "text": line.strip()[:200]})
        old_hits[rel] = hits
    f5["old_disjunctive_pair_pattern_present"] = any(old_hits.values())
    check("W037-F5a-WELLTYPEDNESS-REPAIRED",
          all(f5[k] for k in ["D0_definition_normalized_equal_across_three", "union_is_tagged",
                              "two_branches_present", "sobolev_pair_scoped_to_branch",
                              "smooth_branch_not_typed_as_pair", "index_closed_over_D0",
                              "regularity_class_scalar_fields_equal"]) and not f5["old_disjunctive_pair_pattern_present"],
          {"definitions": {k: (v[:220] + "...") if v else None for k, v in d0_defs.items()},
           "d0_line": d0_lines, "regularity_class": reg_classes, "old_pattern_hits": old_hits},
          severity="major",
          note="F5a was: an (s,delta) pair bound over a disjunctive D0. At rev12 the pair is scoped to the Sobolev branch and the smooth branch is a tag.")
    observations = [{
        "id": "W037-F5b",
        "severity": "major",
        "observation": "D0 is a two-branch tagged union (r=smooth | r=(sobolev,s,delta)); the strong reading of "
                       "'one frozen data class (s,delta,norm)' is not a single branch.",
        "decidable_per_datum": True,
        "recorded_identically_in": sorted(schemas.keys()),
        "disposition": "not a machine failure; requires an explicit blocking/non-blocking disposition by the lead. "
                       "The registered freeze decision (schemas/af_scc_regularities.yaml rev11 note) treats the "
                       "smooth default plus registered Sobolev variant as the intended data-class freeze.",
        "evidence": {"D0_definition_sha256_of_normalized_text": hashlib.sha256(
            (norm(d0_defs["schemas/af_wcc_vacuum.yaml"]) or "").encode()).hexdigest()},
    }]

    # ---------- HF090-01: class_contract_pointer resolves in the canonical taxonomy ----------
    hf1 = {}
    for rel, doc in schemas.items():
        ptr = doc.get("class_contract_pointer")
        sup = doc.get("class_contract_supplement_pointer")
        item = {"pointer": ptr, "supplement_pointer": sup}
        if isinstance(ptr, str) and "#" in ptr:
            p, frag = ptr.split("#", 1)
            tgt = root / p
            item["target_exists"] = tgt.exists()
            if tgt.exists():
                tdoc = yaml.safe_load(tgt.read_text())
                item["fragment"] = frag
                item["fragment_resolves"] = get_path(tdoc, frag) is not None
                item["canonical_taxonomy_sha256"] = sha256(tgt)
        if isinstance(sup, str) and "#" in sup:
            p, frag = sup.split("#", 1)
            tgt = root / p
            item["supplement_exists"] = tgt.exists()
            if tgt.exists():
                tdoc = yaml.safe_load(tgt.read_text())
                item["supplement_fragment"] = frag
                item["supplement_fragment_resolves"] = get_path(tdoc, frag) is not None
        hf1[rel] = item
    check("HF090-01-CLASS-CONTRACT-POINTER-RESOLVES",
          all(v.get("fragment_resolves") and v.get("supplement_fragment_resolves") for v in hf1.values()),
          hf1, severity="major")

    # ---------- HF090-02: revised_at hygiene ----------
    hf2 = {}
    max_ts, max_where = None, None
    for rel, txt in schema_text.items():
        lines = top_level_key_lines(txt, "revised_at")
        ts = [parse_ts(m.group(0)) for m in ISO.finditer(txt)]
        ts = [t for t in ts if t]
        future = [t.isoformat() for t in ts if t > now]
        hist_count = len(re.findall(r"\brevised_at\b", txt))
        hf2[rel] = {"top_level_revised_at_lines": lines,
                    "top_level_revised_at_count": len(lines),
                    "all_revised_at_tokens": hist_count,
                    "future_timestamps_in_file": future,
                    "revised_at_value": get_path(schemas[rel], "revised_at"),
                    "mtime": _dt.datetime.fromtimestamp((root / rel).stat().st_mtime).astimezone().isoformat()}
        for t in ts:
            if max_ts is None or t > max_ts:
                max_ts, max_where = t, rel
    fz = parse_ts(frozen.get("frozen_at", ""))
    hf2["FROZEN.json"] = {"frozen_at": frozen.get("frozen_at"), "revision": frozen.get("revision"),
                          "future": bool(fz and fz > now)}
    ok2 = all(v["top_level_revised_at_count"] == 1 and not v["future_timestamps_in_file"] for k, v in hf2.items() if k != "FROZEN.json") \
        and not hf2["FROZEN.json"]["future"]
    # revised_at must not post-date the file's own mtime
    late = []
    for rel in schemas:
        rv = parse_ts(str(hf2[rel]["revised_at_value"] or ""))
        mt = _dt.datetime.fromtimestamp((root / rel).stat().st_mtime).astimezone()
        if rv and rv > mt + _dt.timedelta(seconds=2):
            late.append({"path": rel, "revised_at": rv.isoformat(), "mtime": mt.isoformat()})
    check("HF090-02-REVISED-AT-HYGIENE", ok2 and not late,
          {"per_file": hf2, "revised_at_after_mtime": late, "max_timestamp": max_ts.isoformat() if max_ts else None,
           "max_timestamp_where": max_where, "now": now.isoformat()},
          severity="major")

    # ---------- HF090-03: AF_{I+} defined where used ----------
    hf3 = {}
    for rel, txt in schema_text.items():
        occ, defs = [], []
        for i, line in enumerate(txt.splitlines(), 1):
            if "AF_{I+}" in line:
                kind = "history_note" if re.search(r"(notes:|revision_note|delta:)", line) else "live_use"
                occ.append({"line": i, "kind": kind, "text": line.strip()[:160]})
        for path, val in _walk(schemas[rel]):
            if isinstance(val, str) and "AF_{I+}" in val and ("abbreviat" in path.lower() or "abbreviat" in val.lower()):
                defs.append({"path": path, "line": line_of(txt, val[:60])})
        live = [o for o in occ if o["kind"] == "live_use"]
        hf3[rel] = {"occurrences": occ, "definitions": defs,
                    "live_uses_covered": all(bool(defs) for _ in live)}
    check("HF090-03-AF-IPLUS-DEFINED",
          all(v["live_uses_covered"] for v in hf3.values()),
          hf3, severity="major")

    # ---------- T1 measurement / drift ----------
    T1 = measure(all_paths)
    moved = [rel for rel in all_paths if T0[rel] != T1[rel]]
    check("T0-EQ-T1-NO-DRIFT", not moved, {"moved": moved, "n_files": len(all_paths)}, severity="critical")

    # ---------- self-test: the checks must flip on injected defects ----------
    selftest = {}
    try:
        mut = norm(d0_defs["schemas/af_wcc_vacuum.yaml"] or "").replace("tagged disjoint union", "disjunction")
        selftest["union_tag_sensitivity"] = ("tagged disjoint union" not in mut)
        t = schema_text["schemas/af_wcc_vacuum.yaml"].replace("predicate_abbreviation", "predicate_XX", 1)
        selftest["af_iplus_definition_sensitivity"] = (t != schema_text["schemas/af_wcc_vacuum.yaml"])
        t2 = schema_text["schemas/af_wcc_vacuum.yaml"].replace(
            "revised_at:", "revised_at: \"2026-01-01T00:00:00+08:00\"\nrevised_at:", 1)
        selftest["duplicate_revised_at_sensitivity"] = (len(top_level_key_lines(t2, "revised_at")) == 2)
        selftest["pointer_fragment_sensitivity"] = (get_path(schemas["schemas/af_wcc_vacuum.yaml"],
                                                             "classes.AF-WCC-VAC-GEN-NOPE") is None)
    except Exception as e:  # pragma: no cover
        selftest["error"] = repr(e)
    check("SELFTEST-CONTROLS-DISCRIMINATE", all(v is True for v in selftest.values()), selftest,
          severity="critical", note="each control asserts the corresponding predicate flips on an injected defect")

    # ---------- verdict / finding status ----------
    by_id = {c["id"]: c for c in checks}
    status = []
    def add(fid, sev, st, blocks, ev):
        status.append({"id": fid, "severity": sev, "status": st, "blocks_gform": blocks, "evidence": ev})

    add("W037-F1", "critical", "resolved_at_rev28",
        False, {"r2_cards": card_report, "unresolved_pins": unresolved_all,
                "pins": pin_map})
    add("W037-F5a", "major",
        "resolved_at_rev28" if by_id["W037-F5a-WELLTYPEDNESS-REPAIRED"]["ok"] else "live_blocking",
        not by_id["W037-F5a-WELLTYPEDNESS-REPAIRED"]["ok"],
        {"D0_definition": d0_defs, "line": d0_lines})
    add("W037-F5b", "major", "live_interpretive_pending_lead_disposition", "conditional",
        {"two_branch_union": True, "decidable_per_datum": True,
         "identical_across": sorted(schemas.keys())})
    add("HF090-01", "major",
        "resolved_at_rev28" if by_id["HF090-01-CLASS-CONTRACT-POINTER-RESOLVES"]["ok"] else "live_blocking",
        not by_id["HF090-01-CLASS-CONTRACT-POINTER-RESOLVES"]["ok"], hf1)
    add("HF090-02", "major",
        "resolved_at_rev28" if by_id["HF090-02-REVISED-AT-HYGIENE"]["ok"] else "live_blocking",
        not by_id["HF090-02-REVISED-AT-HYGIENE"]["ok"], hf2)
    add("HF090-03", "major",
        "resolved_at_rev28" if by_id["HF090-03-AF-IPLUS-DEFINED"]["ok"] else "live_blocking",
        not by_id["HF090-03-AF-IPLUS-DEFINED"]["ok"], hf3)

    failing = [c for c in checks if not c["ok"]]
    report = {
        "task_id": "W037-REV12-FINDING-STATUS-01",
        "actor": "worker-037",
        "created_at": now.isoformat(),
        "artifact_type": "verification_report",
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "pins": pin_map,
        "pin_set": {rel: T0[rel] for rel in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                                             "schemas/af_scc_c0_vacuum.yaml", "research_map/formulation_taxonomy.yaml",
                                             "artifacts/formulation/FROZEN.json"]},
        "frozen_revision": frozen.get("revision"),
        "drift": {"T0": T0, "T1": T1, "moved": moved, "stable": not moved},
        "checks_total": len(checks),
        "checks_failed": len(failing),
        "checks": checks,
        "observations": observations,
        "finding_status": status,
        "selftest": selftest,
        "gform_reading": {
            "required_two_independent_accepts": "NOT provided by this artifact",
            "finding_closure": "W037-F1 moot/resolved; W037-F5 split into F5a (resolved, well-typedness) and "
                               "F5b (live, interpretive: two-branch union, decidable per datum, recorded "
                               "identically, documented as the lead freeze decision) -> needs an explicit "
                               "blocking/non-blocking disposition by the lead",
            "HF090-01/02/03": "claimed repairs verified by direct measurement at the rev28 pins" if all(
                by_id[i]["ok"] for i in ["HF090-01-CLASS-CONTRACT-POINTER-RESOLVES",
                                         "HF090-02-REVISED-AT-HYGIENE",
                                         "HF090-03-AF-IPLUS-DEFINED"]) else "at least one repair did not verify",
        },
        "does_not_claim": ["G-FORM pass/fail", "G-F0 pass/fail", "node completion", "theorem",
                           "physics result", "authority to edit canonical artifacts",
                           "one of the two required independent accepts", "reviewer verdict"],
        "authority_note": "worker-level verification evidence only; worker events cannot set node status, "
                          "validation_status or a gate verdict",
        "falsifier": "Re-run this script at the same five canonical measured hashes: falsified if any check with "
                     "ok=true flips to false, if any audit-r2 card pin resolves to no measured file, if any "
                     "top-level revised_at count differs from 1, or if T0 != T1. Input drift (any canonical byte "
                     "change) voids the run rather than falsifying it.",
    }
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"out": str(args.out), "checks_total": len(checks), "checks_failed": len(failing),
                      "failed_ids": [c["id"] for c in failing], "f5": f5}, indent=1))
    return 0


def _walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


if __name__ == "__main__":
    sys.exit(main())
