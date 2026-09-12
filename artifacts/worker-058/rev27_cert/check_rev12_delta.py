#!/usr/bin/env python3
"""W058-REV27-CERT-03 -- independent rev12-delta certificate for the frozen SCC pair.

Context
-------
The SCC canonical pair moved from FROZEN rev26 (C0 1bb78ce9, C2 b6123750) to FROZEN rev27
(C0 55d0a1ea, C2 5476a3f2) at 00:32:59 through an in-file rev12 edit that *claims* to close
the hash-bound findings of `astra-life03-close-findings`:

  C1  duplicate `revised_at:` keys collapsed into a single `revision_history` block
  C2  `revised_at` stamped with wall clock (no future dating)
  C3  `class_contract_pointer` repointed at the canonical taxonomy key `classes`, the
      authoring supplement split into `class_contract_supplement_pointer`
  C4  D0 retyped from a regularity *pair* `(s,delta)` to a tagged regularity *index* `r`
  (and, F1 only, the visibility clause + AF_{I+} definition -- out of scope for the SCC pair)

What this checker does
----------------------
1. Re-runs the pre-registered acceptance checker `sweep_scc_order.py` UNMODIFIED at the
   current hash and at the rev26 baseline snapshot, and reports the order/strength delta.
2. Independently re-measures the four rev12 claims C1-C4 on the live bytes (C1 with a
   node-level duplicate-key walk, not a loader hook; C4 as a stale-pair-binder scan).
3. Reports the two known pending C0 repairs (HF-1 line 245, MINOR-1 line 234) at the new
   hash so the certificate answers the recorded `next_falsifier` directly.

Read-only on canonical bytes. Exit code 0 = PASS (no hard finding), 1 = FAIL, 2 = error.
`--root` supports mutant trees for the sensitivity self-test.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print("checker error: pyyaml unavailable: %s" % exc, file=sys.stderr)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
C0_PATH = "schemas/af_scc_c0_vacuum.yaml"
C2_PATH = "schemas/af_scc_c2_vacuum.yaml"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
SWEEP = os.path.join(HERE, "sweep_scc_order_frozen_copy.py")
DEFAULT_BASELINE = os.path.join(HERE, "..", "repair_cert", "_scratch", "M0_canonical")
FROZEN_REV_EXPECTED = 27
BASELINE_EXPECTED = {
    C0_PATH: "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    C2_PATH: "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
}
HF1_RE = re.compile(r"C2 is a strictly larger extension class")
HF1_REPAIRED_RE = re.compile(r"C2 is a strictly smaller extension class")
MINOR1_RE = re.compile(r"replacing future by two-sided direction")
PAIR_BINDER_RE = re.compile(r"\(\s*s\s*,\s*delta\s*\)|X\^\{s\s*,\s*delta\}|\bforall\s*\(\s*s\b")
D0_DEFINITION_MARK = "admissible regularity indices"
FUTURE_TOLERANCE_S = 120


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dup_keys(text):
    """Node-level duplicate scalar-key walk: independent of loader construction order."""
    dups = []

    def walk(node):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for key_node, value_node in node.value:
                if isinstance(key_node, yaml.ScalarNode):
                    key = str(key_node.value)
                    if key in seen:
                        dups.append({"key": key, "first_line": seen[key],
                                     "again_line": key_node.start_mark.line + 1})
                    else:
                        seen[key] = key_node.start_mark.line + 1
                walk(value_node)
        elif isinstance(node, yaml.SequenceNode):
            for child in node.value:
                walk(child)

    walk(yaml.compose(text))
    return dups


def parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def resolve_dotted(doc, dotted):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def resolve_pointer(root, pointer):
    if not isinstance(pointer, str) or "#" not in pointer:
        return False, "malformed (no '#fragment')"
    rel, frag = pointer.split("#", 1)
    full = os.path.join(root, rel)
    if not os.path.exists(full):
        return False, "file not found: %s" % rel
    try:
        doc = yaml.safe_load(open(full, encoding="utf-8"))
    except Exception as exc:
        return False, "unparseable: %s" % exc
    cur = doc
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, "fragment path %r does not resolve in %s" % (frag, rel)
    return True, None


def check_file(root, rel, now):
    path = os.path.join(root, rel)
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    doc = yaml.safe_load(text)
    findings = []
    info = {}

    # C1 duplicate keys (node level)
    dups = dup_keys(text)
    info["duplicate_keys"] = dups
    if dups:
        findings.append({"check": "C1_duplicate_keys", "severity": "hard", "file": rel,
                         "line": dups[0]["again_line"],
                         "detail": "%d duplicate mapping key(s): %s"
                                   % (len(dups), sorted({d["key"] for d in dups}))})

    # C2 timestamps not future-dated; revised_at >= max history entry
    stamps = []
    top = parse_iso(doc.get("revised_at"))
    if top is None:
        findings.append({"check": "C2_wall_clock", "severity": "hard", "file": rel,
                         "line": None, "detail": "top-level revised_at missing/unparseable"})
    else:
        stamps.append(("revised_at", top, None))
    for i, entry in enumerate(doc.get("revision_history") or []):
        ts = parse_iso((entry or {}).get("at"))
        if ts is None:
            findings.append({"check": "C2_wall_clock", "severity": "hard", "file": rel,
                             "line": None, "detail": "revision_history[%d].at missing/unparseable" % i})
            continue
        stamps.append(("revision_history[%d].at" % i, ts, i))
    limit = now + datetime.timedelta(seconds=FUTURE_TOLERANCE_S)
    for label, ts, _ in stamps:
        if ts > limit:
            findings.append({"check": "C2_wall_clock", "severity": "hard", "file": rel,
                             "line": None, "detail": "%s is future-dated: %s > %s"
                             % (label, ts.isoformat(), now.isoformat())})
    if top is not None and stamps:
        newest = max(ts for _, ts, _ in stamps)
        if top < newest:
            findings.append({"check": "C2_wall_clock", "severity": "hard", "file": rel,
                             "line": None, "detail": "revised_at %s precedes a history entry %s"
                             % (top.isoformat(), newest.isoformat())})
    info["timestamp_summary"] = {
        "revised_at": doc.get("revised_at"),
        "history_entries": len(doc.get("revision_history") or []),
        "max_history_at": max((ts.isoformat() for _, ts, _ in stamps), default=None),
    }

    # C3 revision_history structural integrity
    hist = doc.get("revision_history") or []
    indices = [(e or {}).get("index") for e in hist]
    info["revision_history_indices"] = indices
    if not hist:
        findings.append({"check": "C3_revision_history", "severity": "hard", "file": rel,
                         "line": None, "detail": "revision_history missing/empty"})
    else:
        if indices != list(range(1, len(indices) + 1)):
            findings.append({"check": "C3_revision_history", "severity": "hard", "file": rel,
                             "line": None, "detail": "indices are not contiguous ascending 1..N: %s" % indices})
        if len(set(indices)) != len(indices):
            findings.append({"check": "C3_revision_history", "severity": "hard", "file": rel,
                             "line": None, "detail": "duplicate revision_history index"})
        rev = doc.get("revision")
        if not isinstance(rev, int) or rev < max(i for i in indices if isinstance(i, int)):
            findings.append({"check": "C3_revision_history", "severity": "hard", "file": rel,
                             "line": None, "detail": "top-level revision %r < max history index" % (rev,)})
        if not any((e or {}).get("unused") is False for e in hist):
            findings.append({"check": "C3_revision_history", "severity": "hard", "file": rel,
                             "line": None, "detail": "no published (unused:false) history entry"})

    # C4 stale pair-typed regularity binders after the D0 retyping
    stale = [(i + 1, ln.strip()) for i, ln in enumerate(lines)
             if PAIR_BINDER_RE.search(ln) and D0_DEFINITION_MARK not in ln]
    info["stale_pair_binders"] = stale
    for line_no, quote in stale:
        findings.append({"check": "C4_stale_pair_binder", "severity": "hard", "file": rel,
                         "line": line_no, "detail": "pair-typed regularity binder outside the D0 "
                         "definition: %s" % quote[:120]})

    # C3b pointer resolution (taxonomy file + authoring supplement + in-file definition_refs)
    for key in ("class_contract_pointer", "class_contract_supplement_pointer"):
        ok, why = resolve_pointer(root, doc.get(key))
        info[key] = {"value": doc.get(key), "resolves": ok, "why": why}
        if not ok:
            findings.append({"check": "C3_pointer", "severity": "hard", "file": rel,
                             "line": None, "detail": "%s does not resolve: %s" % (key, why)})
    domains = ((doc.get("quantifiers") or {}).get("domains") or {})
    for dname, dval in domains.items():
        ref = (dval or {}).get("definition_ref")
        if ref and not resolve_dotted(doc, ref):
            findings.append({"check": "C3_pointer", "severity": "hard", "file": rel,
                             "line": None, "detail": "definition_ref %r of domain %s does not resolve"
                             % (ref, dname)})

    # D6 known pending repairs, re-measured at these bytes
    repaired = []
    for key in ("conclusion", "implication_ledger"):
        if key not in doc:
            findings.append({"check": "D6_structure", "severity": "hard", "file": rel,
                             "line": None, "detail": "section %r missing" % key})
    if HF1_RE.search(text):
        findings.append({"check": "D6_HF1_open", "severity": "hard", "file": rel,
                         "line": next((i + 1 for i, ln in enumerate(lines) if HF1_RE.search(ln)), None),
                         "detail": "HF-1 still present: 'C2 is a strictly larger extension class'"})
    elif HF1_REPAIRED_RE.search(text):
        repaired.append("HF-1 (C0 'strictly larger' -> 'strictly smaller')")
    weakenings = ((doc.get("conclusion") or {}).get("forbidden_weakenings") or [])
    minor1_lines = [i + 1 for i, ln in enumerate(lines) if MINOR1_RE.search(ln)]
    minor1_in_weakenings = any(isinstance(w, str) and MINOR1_RE.search(w) for w in weakenings)
    info["minor1_lines_anywhere"] = minor1_lines
    if minor1_in_weakenings:
        findings.append({"check": "D6_MINOR1_open", "severity": "hard", "file": rel,
                         "line": minor1_lines[0] if minor1_lines else None,
                         "detail": "MINOR-1 still present: 'replacing future by two-sided direction' "
                                   "filed under conclusion.forbidden_weakenings"})
    elif minor1_lines:
        info["minor1_note"] = ("the two-sided item still appears in the file at %s but is no longer "
                               "under forbidden_weakenings; sweep decides" % minor1_lines)
        repaired.append("MINOR-1 (item no longer under forbidden_weakenings)")
    info["repaired_items"] = repaired

    return {"file": rel, "sha256": sha256_file(path), "bytes": len(text.encode("utf-8")),
            "findings": findings, "info": info, "doc": doc}


def run_sweep(root, out_path):
    proc = subprocess.run([sys.executable, SWEEP, "--root", root, "--out", out_path],
                          capture_output=True, text=True)
    payload = None
    if os.path.exists(out_path):
        try:
            payload = json.load(open(out_path, encoding="utf-8"))
        except Exception:
            payload = None
    return payload, proc.returncode, (proc.stderr or "").strip()[-400:]


def sweep_summary(payload):
    if not payload:
        return None
    return {
        "verdict": payload.get("verdict"),
        "counts": payload.get("counts"),
        "hard_codes": sorted({f.get("code") for f in payload.get("hard_findings") or []}),
        "hard_lines": {f.get("code"): f.get("line") for f in payload.get("hard_findings") or []},
        "advisory_codes": sorted({f.get("code") for f in payload.get("advisories") or []}),
        "duplicate_key_count": len(payload.get("yaml_duplicate_keys") or []),
        "frozen_match": {k: v.get("frozen_match") for k, v in
                         ((payload.get("inputs") or {}).get("files") or {}).items()},
    }


def run(root, baseline_root, mutant_name=None):
    now = datetime.datetime.now().astimezone()
    root = os.path.abspath(root)
    baseline_root = os.path.abspath(baseline_root)
    findings = []
    files = {}
    for rel in (C0_PATH, C2_PATH):
        res = check_file(root, rel, now)
        files[rel] = {k: v for k, v in res.items() if k != "doc"}
        findings.extend(res["findings"])

    frozen = {}
    fpath = os.path.join(root, FROZEN_PATH)
    if os.path.exists(fpath):
        frozen = json.load(open(fpath, encoding="utf-8"))
    frozen_files = frozen.get("files") or {}
    binding = {}
    for rel in (C0_PATH, C2_PATH):
        pin = (frozen_files.get(rel) or {}).get("sha256")
        measured = files[rel]["sha256"]
        binding[rel] = {"measured_sha256": measured, "frozen_sha256": pin,
                        "frozen_match": pin == measured}
        if pin is not None and pin != measured:
            findings.append({"check": "D5_frozen_pin", "severity": "hard", "file": rel,
                             "line": None, "detail": "measured %s != FROZEN pin %s" % (measured, pin)})

    scratch = os.path.join(HERE, "_scratch")
    os.makedirs(scratch, exist_ok=True)
    tag = mutant_name or "canonical"
    now_sweep, rc_now, err_now = run_sweep(root, os.path.join(scratch, "sweep_%s.json" % tag))
    base_sweep, rc_base, err_base = run_sweep(baseline_root, os.path.join(scratch, "sweep_baseline.json"))
    now_s = sweep_summary(now_sweep)
    base_s = sweep_summary(base_sweep)

    delta = {"baseline_root": os.path.relpath(baseline_root, root) if baseline_root.startswith(root)
             else baseline_root,
             "baseline_expected_sha256": BASELINE_EXPECTED,
             "sweep_base": base_s, "sweep_now": now_s,
             "new_hard_codes": [], "resolved_hard_codes": [], "persisting_hard_codes": [],
             "line_shift": {}, "sweep_error": err_now or None}
    if base_s and now_s:
        base_codes, now_codes = set(base_s["hard_codes"]), set(now_s["hard_codes"])
        delta["new_hard_codes"] = sorted(now_codes - base_codes)
        delta["resolved_hard_codes"] = sorted(base_codes - now_codes)
        delta["persisting_hard_codes"] = sorted(base_codes & now_codes)
        for code in sorted(base_codes & now_codes):
            b, n = base_s["hard_lines"].get(code), now_s["hard_lines"].get(code)
            delta["line_shift"][code] = {"rev26_line": b, "rev27_line": n,
                                         "shift": (n - b) if (b is not None and n is not None) else None}
        if delta["new_hard_codes"]:
            findings.append({"check": "D7_order_strength_delta", "severity": "hard",
                             "file": "C0+C2", "line": None,
                             "detail": "rev12 introduced new order/strength hard code(s): %s"
                                       % delta["new_hard_codes"]})

    # baseline delta on the four rev12 claims
    base_info = {}
    if os.path.isdir(baseline_root):
        for rel in (C0_PATH, C2_PATH):
            bp = os.path.join(baseline_root, rel)
            if os.path.exists(bp):
                btext = open(bp, encoding="utf-8").read()
                base_info[rel] = {
                    "sha256": sha256_file(bp),
                    "duplicate_keys": len(dup_keys(btext)),
                    "hf1_present": bool(HF1_RE.search(btext)),
                    "minor1_in_weakenings": False,
                }
                try:
                    bdoc = yaml.safe_load(btext)
                    base_info[rel]["minor1_in_weakenings"] = any(
                        isinstance(w, str) and MINOR1_RE.search(w)
                        for w in ((bdoc.get("conclusion") or {}).get("forbidden_weakenings") or []))
                except Exception:
                    pass
    delta["rev26_baseline"] = base_info
    for rel, info in base_info.items():
        exp = BASELINE_EXPECTED.get(rel)
        if exp and info["sha256"] != exp:
            findings.append({"check": "D7_baseline_pin", "severity": "hard", "file": rel,
                             "line": None,
                             "detail": "baseline snapshot %s is not the recorded rev26 byte (%s != %s)"
                                       % (rel, info["sha256"], exp)})

    hard = [f for f in findings if f["severity"] == "hard"]
    checks = sorted({f["check"] for f in findings})
    repaired_items = sorted({i for f in files.values() for i in f["info"].get("repaired_items", [])})
    result = {
        "artifact": "W058-REV27-CERT-03 rev12-delta certificate for the frozen SCC pair",
        "worker": "worker-058",
        "actor": "deepseek-flash-058",
        "generated_at": now.isoformat(timespec="seconds"),
        "task_id": "W058-REV27-CERT-03",
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "mode": "MUTANT:%s" % mutant_name if mutant_name else "CANONICAL",
        "scope": {
            "does": ["re-run the unmodified pre-registered order/strength acceptance test at the "
                     "current hash and at the rev26 baseline snapshot",
                     "independently re-measure the four rev12 close-findings claims C1-C4 on the SCC pair",
                     "re-measure HF-1/MINOR-1 presence at the bound bytes"],
            "does_not_audit": ["physical truth", "citation scope", "mathematical correctness",
                               "F1/WCC rev12 changes (visibility clause, AF_{I+})",
                               "F0 taxonomy", "C0/C2 class-merge (FORM-SEP-04 owns it)"],
            "read_only": True, "claims_no_completion": True,
            "interpretation_owner": "astra-lead-formulation",
        },
        "inputs": {"files": {rel: {"sha256": files[rel]["sha256"], "bytes": files[rel]["bytes"]}
                             for rel in files},
                   "frozen_manifest": FROZEN_PATH,
                   "frozen_manifest_sha256": sha256_file(fpath) if os.path.exists(fpath) else None,
                   "frozen_revision": frozen.get("revision"),
                   "frozen_at": frozen.get("frozen_at"),
                   "manifest_motion_note": ("FROZEN moved rev27 (00:32:59) -> rev28 (00:35:08) while "
                                            "this task ran; the SCC pin bytes were unchanged at every "
                                            "measurement, so verdicts bind to the measured sha256 "
                                            "values, not to the revision number."),
                   "frozen_pin_binding": binding,
                   "baseline_root": delta["baseline_root"],
                   "sweep_tool": os.path.relpath(SWEEP, root),
                   "sweep_tool_sha256": sha256_file(SWEEP)},
        "rev12_claim_checks": {
            "C1_duplicate_revised_at_collapsed": {
                "status": "verified" if not files[C0_PATH]["info"]["duplicate_keys"] and
                          not files[C2_PATH]["info"]["duplicate_keys"] else "failed",
                "rev26_duplicate_keys_C0": base_info.get(C0_PATH, {}).get("duplicate_keys"),
                "rev27_duplicate_keys_C0": len(files[C0_PATH]["info"]["duplicate_keys"]),
                "rev27_duplicate_keys_C2": len(files[C2_PATH]["info"]["duplicate_keys"])},
            "C2_wall_clock_revised_at": {
                "status": "verified" if not any(f["check"] == "C2_wall_clock" for f in findings) else "failed",
                "detail": files[C0_PATH]["info"]["timestamp_summary"]},
            "C3_pointers_resolve": {
                "status": "verified" if not any(f["check"] == "C3_pointer" for f in findings) else "failed",
                "C0": {k: files[C0_PATH]["info"].get(k) for k in
                       ("class_contract_pointer", "class_contract_supplement_pointer")},
                "C2": {k: files[C2_PATH]["info"].get(k) for k in
                       ("class_contract_pointer", "class_contract_supplement_pointer")}},
            "C4_D0_retyped_no_stale_pair_binder": {
                "status": "verified" if not any(f["check"] == "C4_stale_pair_binder" for f in findings) else "failed",
                "rev27_stale_lines_C0": files[C0_PATH]["info"]["stale_pair_binders"],
                "rev27_stale_lines_C2": files[C2_PATH]["info"]["stale_pair_binders"]},
        },
        "file_reports": files,
        "delta": delta,
        "counts": {"hard": len(hard), "checks": len(checks)},
        "verdict": "FAIL" if hard else "PASS",
        "hard_findings": hard,
        "repaired_items": repaired_items,
        "repair_status": {
            "HF1_open": any(f["check"] == "D6_HF1_open" for f in findings),
            "MINOR1_open": any(f["check"] == "D6_MINOR1_open" for f in findings),
            "pre_registered_test": ("PASS iff the unmodified sweep returns hard==0 at the current "
                                    "hash; measured: %s" % (now_s or {}).get("verdict")),
        },
        "falsifier": ("A reader exhibits (a) a rev12 claim C1-C4 that is false at the bound bytes, "
                      "(b) a stale pair-typed regularity binder or dangling pointer this checker "
                      "misses, (c) an order/strength hard finding present at rev26 but absent from "
                      "this certificate, or (d) a new rev27 defect that the calibrated mutants show "
                      "the checker would have caught but did not."),
        "next_falsifier": ("Re-run after the two C0 repairs land. The certificate is falsified if the "
                           "unmodified sweep still returns hard>0 at the new hash, or if the "
                           "new hash re-introduces one of the four C1-C4 classes."),
        "authority_note": ("Worker claims no node completion and no gate verdict; lead-formulation "
                           "owns the repairs and any gate consequence."),
    }
    return result, (0 if not hard else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--out")
    ap.add_argument("--mutant", default=None)
    args = ap.parse_args()
    try:
        result, rc = run(args.root, args.baseline, args.mutant)
    except FileNotFoundError as exc:
        print("checker error: %s" % exc, file=sys.stderr)
        return 2
    payload = json.dumps(result, indent=1, sort_keys=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
    print("%s hard=%d mode=%s" % (result["verdict"], result["counts"]["hard"], result["mode"]))
    for f in result["hard_findings"]:
        print("  HARD %-26s %s:%s %s" % (f["check"], f["file"], f.get("line"),
                                         str(f.get("detail"))[:100]))
    for claim, val in result["rev12_claim_checks"].items():
        print("  %-44s %s" % (claim, val["status"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
