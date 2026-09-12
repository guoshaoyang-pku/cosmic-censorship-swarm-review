#!/usr/bin/env python3
"""W067-N0-PROVENANCE-DRIFT-LEDGER-01

Independent, read-only, hash-bound census of every path->sha256 binding reachable
from the live N0 / G-NUM acceptance chain, plus a re-computation of the explicit
"*_matches_on_disk" assertions in the chain.

Scope (class-bound): AF-WCC-SCALAR-SPH / N0 / G-NUM.  Permitted under
numerics_lock (N0 flat-space only; no solver code, no self-gravitating run).

Anchors swept (measured at run time, hashed before and after):
  A) numerics/tests/n0_gate_proposal.json            -> .evidence_hashes
  B) numerics/protocol/fixed_replication_verdict.json-> .chained_evidence_hashes,
                                                        .provenance.* assertions
  C) numerics/protocol/n0_fixed_dt_certification.json-> .frozen_module, .artifact,
                                                        .supersedes_evidence_basis
  D) numerics/CONVERGENCE_PROTOCOL.md                -> inline path#hash refs

Method: parse declared (path, expected-hash) pairs; measure the live bytes of each
declared path relative to the repository root; classify MATCH / STALE / MISSING /
UNRESOLVED.  For explicit booleans, recompute the truth of the assertion from the
measured bytes and classify AGREES / CONTRADICTS / UNCHECKED.

Writes nothing except ledger.json in this directory.  Exit 0 = ledger complete;
exit 2 = fail-closed (anchor drift, control failure, or non-reproducible read).
"""

import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LEDGER = os.path.join(HERE, "ledger.json")

A_PROPOSAL = "numerics/tests/n0_gate_proposal.json"
A_VERDICT = "numerics/protocol/fixed_replication_verdict.json"
A_CERT = "numerics/protocol/n0_fixed_dt_certification.json"
A_PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
ANCHORS = [A_PROPOSAL, A_VERDICT, A_CERT, A_PROTOCOL]

# Files scanned for the *recording* of a drift (is a stale pin annotated anywhere?).
ANNOTATION_FILES = [
    A_PROTOCOL, A_VERDICT, A_PROPOSAL, A_CERT,
    "numerics/results/flat_wave_convergence_rev3.json",
    "numerics/blockers.md",
    "numerics/protocol/scheme_independence_review.md",
]
ANNOTATION_WORDS = (
    "supersed", "stale", "drift", "not load-bearing", "not_load_bearing",
    "previous_stale_pins", "relabelled", "frozen", "provisional", "blocker",
)

# Explicit assertions in numerics/protocol/fixed_replication_verdict.json:
#   (assertion key, referenced path, sibling hash key)
ASSERTIONS = [
    ("fixed_json_sha256_matches_pinned", None, "fixed_json_sha256"),          # path in provenance.fixed_json
    ("fixed_harness_sha256_matches_on_disk", "artifacts/flash-04/n0_acceptance/harness.py", "harness_sha256"),
    ("fixed_script_sha256_matches_on_disk", "numerics/tests/flat_wave_replication.py", "replication_script_sha256"),
    ("fixed_taxonomy_sha256_matches_on_disk", "research_map/formulation_taxonomy.yaml", "taxonomy_sha256"),
]

HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
REF_RE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_./-]*)#([0-9a-f]{7,64})")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def line_of(text, needle):
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def resolve(path):
    p = path.lstrip("./")
    cand = os.path.join(REPO, p)
    return cand if os.path.isfile(cand) else None


def classify(path, expected):
    """Return dict(status, measured, resolved_path). expected may be a >=7-hex prefix."""
    resolved = resolve(path)
    if resolved is None:
        return {"status": "MISSING", "measured": None, "resolved_path": path}
    measured = sha256_file(resolved)
    exp = (expected or "").lower()
    if not exp:  # existence-only binding
        return {"status": "MATCH", "measured": measured, "resolved_path": path}
    if measured.startswith(exp):
        return {"status": "MATCH", "measured": measured, "resolved_path": path}
    return {"status": "STALE", "measured": measured, "resolved_path": path}


def binding(source, key, path, expected, kind, line):
    c = classify(path, expected)
    return {
        "source": source, "source_key": key, "kind": kind,
        "path": path, "expected": expected, "line": line,
        "measured": c["measured"], "status": c["status"],
    }


def sweep():
    bindings = []
    anchors_before = {}
    for a in ANCHORS:
        rp = resolve(a)
        if rp is None:
            die("anchor missing: %s" % a)
        anchors_before[a] = sha256_file(rp)

    # ---- A: proposal evidence_hashes -------------------------------------
    prop_txt = read_text(resolve(A_PROPOSAL))
    prop = json.loads(prop_txt)
    for path, expected in prop.get("evidence_hashes", {}).items():
        bindings.append(binding("proposal", "evidence_hashes", path, expected,
                                "input_binding", line_of(prop_txt, '"%s"' % path)))
    for path, blob in prop.get("mutable_registry_snapshots", {}).items():
        if not isinstance(blob, dict) or path == "superseded_pins":
            continue
        bindings.append(binding("proposal", "mutable_registry_snapshots", path,
                                    str(blob.get("measured_full") or blob.get("sha256") or ""),
                                    "excluded_mutable_snapshot",
                                    line_of(prop_txt, '"%s"' % path)))
    for path, expected in (prop.get("mutable_registry_snapshots", {}).get("superseded_pins") or {}).items():
        if path == "note":
            continue
        bindings.append(binding("proposal", "mutable_registry_snapshots.superseded_pins",
                                path, expected, "known_superseded_pin",
                                line_of(prop_txt, '"%s"' % path)))
    sup = (prop.get("provenance") or {}).get("supersedes")
    if sup:
        m = REF_RE.search(sup)
        if m:
            bindings.append(binding("proposal", "provenance.supersedes", m.group(1),
                                    m.group(2), "historical_supersession",
                                    line_of(prop_txt, "supersedes")))

    # ---- B: fixed replication verdict ------------------------------------
    ver_txt = read_text(resolve(A_VERDICT))
    ver = json.loads(ver_txt)
    for path, expected in ver.get("chained_evidence_hashes", {}).items():
        bindings.append(binding("replication_verdict", "chained_evidence_hashes", path,
                                expected, "input_binding", line_of(ver_txt, '"%s"' % path)))
    prov = ver.get("provenance") or {}
    fixed_json = prov.get("fixed_json")
    assertions = []
    for akey, apath, hkey in ASSERTIONS:
        if apath is None:
            apath = fixed_json
        declared = prov.get(akey)
        expected = prov.get(hkey)
        c = classify(apath, expected or "")
        truth = {"MATCH": True, "STALE": False, "MISSING": False, "UNRESOLVED": False}[c["status"]]
        if declared is None:
            status = "UNCHECKED"
        elif bool(declared) == truth:
            status = "AGREES"
        else:
            status = "CONTRADICTS"
        assertions.append({
            "source": "replication_verdict", "key": akey, "path": apath,
            "hash_key": hkey, "declared": declared, "expected": expected,
            "measured": c["measured"], "binding_status": c["status"],
            "recomputed_truth": truth, "status": status,
            "line": line_of(ver_txt, '"%s"' % akey),
        })
        bindings.append(binding("replication_verdict", "provenance." + hkey, apath,
                                expected or "", "assertion_backing",
                                line_of(ver_txt, '"%s"' % hkey)))

    # ---- C: certification -------------------------------------------------
    cert_txt = read_text(resolve(A_CERT))
    cert = json.loads(cert_txt)
    fm = cert.get("frozen_module") or {}
    if fm.get("path"):
        bindings.append(binding("certification", "frozen_module", fm["path"],
                                fm.get("sha256", ""), "input_binding",
                                line_of(cert_txt, '"sha256"')))
    if cert.get("artifact"):
        bindings.append(binding("certification", "artifact", cert["artifact"], "",
                                "generator_existence", line_of(cert_txt, '"artifact"')))
    for kind, ref in (cert.get("supersedes_evidence_basis") or {}).items():
        if not isinstance(ref, str):
            continue
        m = REF_RE.search(ref)
        if m:
            bindings.append(binding("certification", "supersedes_evidence_basis." + kind,
                                    m.group(1), m.group(2), "supersession_ref",
                                    line_of(cert_txt, ref)))

    # ---- D: protocol inline refs -----------------------------------------
    proto_txt = read_text(resolve(A_PROTOCOL))
    for i, line in enumerate(proto_txt.splitlines(), 1):
        for m in REF_RE.finditer(line):
            path, expected = m.group(1), m.group(2)
            if resolve(path) is None and "/" not in path:
                continue
            bindings.append(binding("protocol", "inline_ref", path, expected,
                                    "inline_ref", i))

    # ---- stale recording scan --------------------------------------------
    stale_values = sorted({b["expected"] for b in bindings if b["status"] == "STALE"})
    recording = {}
    for val in stale_values:
        prefix = val[:12]
        hits = []
        for rel in ANNOTATION_FILES:
            rp = resolve(rel)
            if rp is None:
                continue
            txt = read_text(rp)
            for i, line in enumerate(txt.splitlines(), 1):
                if prefix in line:
                    hits.append({
                        "file": rel, "line": i,
                        "recorded_as_drift": any(w in line.lower() for w in ANNOTATION_WORDS),
                        "excerpt": line.strip()[:220],
                    })
        recording[val] = hits
    for b in bindings:
        if b["status"] == "STALE":
            b["recorded_drift"] = any(h["recorded_as_drift"]
                                      for h in recording.get(b["expected"], []))

    # ---- anchor stability + read-only proof ------------------------------
    anchors_after = {}
    for a in ANCHORS:
        anchors_after[a] = sha256_file(resolve(a))
    swept_paths = sorted({b["path"] for b in bindings if b["status"] != "MISSING"})
    swept_after = {}
    for p in swept_paths:
        rp = resolve(p)
        if rp is not None:
            swept_after[p] = sha256_file(rp)
    return bindings, assertions, anchors_before, anchors_after, swept_paths, swept_after, recording


def die(msg):
    print("FAIL-CLOSED: %s" % msg, file=sys.stderr)
    sys.exit(2)


def main():
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    (bindings, assertions, a_before, a_after, swept_paths, swept_after,
     recording) = sweep()

    # ---------------- controls (no canonical writes) ----------------
    controls = []
    def ctl(cid, desc, ok, detail):
        controls.append({"id": cid, "description": desc, "pass": bool(ok), "detail": detail})

    tax = [b for b in bindings
           if b["source"] == "proposal" and b["source_key"] == "evidence_hashes"
           and b["path"] == "research_map/formulation_taxonomy.yaml"]
    ctl("C1", "known-good: proposal pins canonical F0 rev5",
        len(tax) == 1 and tax[0]["status"] == "MATCH",
        {"binding": tax[0] if tax else None})

    stale_tax = [b for b in bindings if b["source"] == "replication_verdict"
                 and b["source_key"] == "chained_evidence_hashes"
                 and b["path"] == "research_map/formulation_taxonomy.yaml"]
    ctl("C2", "known-stale: replication verdict chains superseded F0 rev2",
        len(stale_tax) == 1 and stale_tax[0]["status"] == "STALE",
        {"binding": stale_tax[0] if stale_tax else None})

    flipped = classify(tax[0]["path"], "0" * 64) if tax else {"status": None}
    ctl("C3", "detector sensitivity: corrupted expectation flips MATCH -> STALE",
        flipped["status"] == "STALE", {"flipped_status": flipped["status"]})

    missing = classify("numerics/does_not_exist_worker_067.json", "ab" * 32)
    ctl("C4", "missing-path detection", missing["status"] == "MISSING",
        {"status": missing["status"]})

    tax_assert = [a for a in assertions if a["key"] == "fixed_taxonomy_sha256_matches_on_disk"]
    good5 = bool(tax_assert) and tax_assert[0]["declared"] is True \
        and tax_assert[0]["recomputed_truth"] is False \
        and tax_assert[0]["status"] == "CONTRADICTS"
    ctl("C5", "assertion detector: declared true + measured mismatch -> CONTRADICTS",
        good5, {"assertion": tax_assert[0] if tax_assert else None})

    drift = [a for a in ANCHORS if a_before[a] != a_after[a]]
    ctl("C6", "anchor stability before/after sweep (fails closed on drift)",
        not drift, {"drifted": drift})
    ro = [p for p in swept_paths if swept_after.get(p) != next(
        (b["measured"] for b in bindings if b["path"] == p and b["measured"]), None)]
    ctl("C7", "read-only on every swept canonical byte", not ro, {"changed": ro})

    if not all(c["pass"] for c in controls):
        die("control failure: %s" % [c["id"] for c in controls if not c["pass"]])

    stale = [b for b in bindings if b["status"] == "STALE"]
    stale_excluded = [b for b in stale if b["kind"] == "excluded_mutable_snapshot"]
    stale_recorded = [b for b in stale if b.get("recorded_drift")]
    stale_unrecorded = [b for b in stale
                        if not b.get("recorded_drift") and b["kind"] != "excluded_mutable_snapshot"]
    contradicted = [a for a in assertions if a["status"] == "CONTRADICTS"]
    missing_b = [b for b in bindings if b["status"] == "MISSING"]

    verdict = "LEDGER_COMPLETE"
    if contradicted:
        verdict = "LEDGER_COMPLETE_WITH_CONTRADICTED_ASSERTION"
    elif stale:
        verdict = "LEDGER_COMPLETE_WITH_STALE_BINDINGS"

    ledger = {
        "schema": "w067-n0-provenance-drift-ledger/v1",
        "task_id": "W067-N0-PROVENANCE-DRIFT-LEDGER-01",
        "actor": "worker-067",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "created_at": started,
        "repo_root": REPO,
        "script": {"path": "artifacts/worker-067/n0_provenance_ledger/check_provenance.py",
                   "sha256": sha256_file(os.path.abspath(__file__))},
        "anchors": {a: {"sha256_before": a_before[a], "sha256_after": a_after[a],
                        "stable": a_before[a] == a_after[a]} for a in ANCHORS},
        "counts": {
            "bindings": len(bindings), "match": sum(b["status"] == "MATCH" for b in bindings),
            "stale": len(stale), "missing": len(missing_b),
            "stale_excluded_by_source": len(stale_excluded),
            "stale_recorded_drift": len(stale_recorded),
            "stale_unrecorded": len(stale_unrecorded),
            "assertions": len(assertions),
            "assertions_contradicted": len(contradicted),
        },
        "key_finding": (
            "fixed_replication_verdict.json (sha256 dcad962324e3...) line 31 declares "
            "fixed_taxonomy_sha256_matches_on_disk=true while lines 7/39 pin the superseded F0 rev2 "
            "hash 66bf917bd368...; live research_map/formulation_taxonomy.yaml measures "
            "0abb9ed8a961... (rev5), so the declared boolean is CONTRADICTED by the bytes.  The "
            "chained path->hash rows and two sibling booleans (fixed_json, harness, script) all MATCH."
        ),
        "bindings": bindings,
        "assertions": assertions,
        "stale_values": sorted({b["expected"] for b in stale}),
        "stale_recording_scan": recording,
        "controls": controls,
        "verdict": verdict,
        "load_bearing_note": (
            "The proposal's own class_binding_note declares the F0 binding provisional and NOT "
            "load-bearing for the order claim; the protocol preamble stale pin is recorded in "
            "numerics/blockers.md item 5 and in the rev3 report annotation.  What is NOT recorded "
            "anywhere in the chain is that fixed_replication_verdict.json line 31 asserts "
            "fixed_taxonomy_sha256_matches_on_disk=true while its own pinned value is the "
            "superseded rev2 hash: the assertion is contradicted by the live bytes."
        ),
        "not_claimed": [
            "no gate verdict (G-NUM), no node status change, no validation_status=passed",
            "no claim that the stale bindings change any certified order number",
            "no canonical file edited; sweep is read-only",
            "no self-gravitating numerics; N1 untouched",
        ],
        "next_falsifier": (
            "Re-run check_provenance.py at the same four anchor hashes: the ledger is withdrawn if "
            "any control fails, if an anchor drifts, or if a binding classified STALE re-hashes to "
            "its declared value (or vice versa).  The contradicted-assertion finding is withdrawn if "
            "fixed_replication_verdict.json is repaired so that taxonomy_sha256 / line-7 pin equal "
            "the measured canonical taxonomy, or if the artifact is formally superseded by an event."
        ),
    }
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(json.dumps({"verdict": verdict, "counts": ledger["counts"],
                      "stale_values": ledger["stale_values"],
                      "ledger": LEDGER,
                      "ledger_sha256": sha256_file(LEDGER)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
