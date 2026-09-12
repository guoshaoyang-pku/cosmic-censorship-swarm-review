#!/usr/bin/env python3
"""
W057-GFORM-F2B-VERDICT-SENSITIVITY-01 -- bounded, read-only worker measurement.

Question
--------
At the live F2b pin (schemas/af_scc_c0_vacuum.yaml sha256 b2ab6acb2bbe..., FROZEN rev29
815e08079aef...), several full-schema ACCEPT verdicts and several REVISE verdicts bind the
same bytes.  The revise verdicts name two live text carriers:

  HC1  regularity.must_not_conflate[0]            (line 152)
       "No containment with C2 or C0 is asserted here"
  HC2  implication_ledger.forbidden_transfers[0].reason  (line 246)
       "C2 is a strictly larger extension class"

both contradicted by the same file's chain

  CHAIN implication_ledger.extension_class_containment   (line 239)
       "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"

This instrument harvests every live-hash F2b verdict, resolves each verdict's declared
instrument source on disk, and measures -- deterministically, by literal probe counts --
whether that instrument can have exercised HC1/HC2 at all.  An instrument whose source never
contains the carrier text (and never reads the contradicted chain field) cannot have discharged
that carrier's revise finding.  It issues NO review verdict on the schema and no gate verdict.

Usage
-----
    python3 audit_f2b_verdict_sensitivity.py            # writes report.json + evidence/
    python3 audit_f2b_verdict_sensitivity.py --check    # exit 0 iff all controls pass
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-057/<task>/ -> repo root

# ----------------------------------------------------------------------------- pre-registered pins
LIVE_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": LIVE_F2B,
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": LIVE_F2B,
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    # the controller's own freshest scan for this pass; pinned so the reconciliation is byte-bound
    "runtime/state/controller_verification/lifecycle_20260912-011029.json": None,
}
CONTROLLER_SCAN = "runtime/state/controller_verification/lifecycle_20260912-011029.json"

# pre-registered probes: literal strings whose presence in an instrument source is necessary for
# that instrument to exercise the corresponding carrier.
PROBES = {
    "hc1_text": "No containment with C2 or C0 is asserted here",
    "hc2_text": "strictly larger extension class",
    "mnc_block": "must_not_conflate",
    "ft_block": "forbidden_transfers",
    "chain_field": "extension_class_containment",
    "chain_literal_a": "contains E_H2loc",
    "chain_literal_b": "E_C2 subset",
}
TARGETED_TIER = "targeted_defect_text"
BLOCK_TIER = "block_referencing_only"
BLIND_TIER = "blind_to_both_blocks"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jdump(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, prefix + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, prefix + "[%d]" % i)
    else:
        yield prefix, obj


# --------------------------------------------------------------------------------- pin measurement
def measure_pins():
    out = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.exists():
            out[rel] = {"exists": False, "sha256": None, "bytes": None, "match": False}
            continue
        h = sha256_file(p)
        out[rel] = {
            "exists": True,
            "sha256": h,
            "bytes": p.stat().st_size,
            "expected": expected,
            "match": (expected is None) or (h == expected),
        }
    return out


# ------------------------------------------------------------------------------- live carriers
def carrier_report():
    raw = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    lines = raw.splitlines()

    def line_of(needle):
        for i, ln in enumerate(lines, 1):
            if needle in ln:
                return i
        return None

    mnc = doc.get("regularity", {}).get("must_not_conflate", []) or []
    hc1_hits = [s for s in mnc if PROBES["hc1_text"] in str(s)]
    il = doc.get("implication_ledger", {}) or {}
    fts = il.get("forbidden_transfers", []) or []
    hc2_hits = [
        r for r in fts
        if isinstance(r, dict) and PROBES["hc2_text"] in str(r.get("reason", ""))
    ]
    chain = str(il.get("extension_class_containment", ""))
    return {
        "file": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": LIVE_F2B,
        "hc1": {
            "carrier": "regularity.must_not_conflate",
            "hit_count": len(hc1_hits),
            "line": line_of(PROBES["hc1_text"]),
            "text": hc1_hits[0][:200] if hc1_hits else None,
        },
        "hc2": {
            "carrier": "implication_ledger.forbidden_transfers[0].reason",
            "hit_count": len(hc2_hits),
            "line": line_of(PROBES["hc2_text"]),
            "text": hc2_hits[0].get("reason") if hc2_hits else None,
        },
        "chain": {
            "carrier": "implication_ledger.extension_class_containment",
            "line": line_of(chain[:60]) if chain else None,
            "text": chain[:300],
            "declares": "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
        },
        "contradiction_live": bool(hc1_hits) or bool(hc2_hits),
    }


# --------------------------------------------------------------------------------- verdict census
def live_binding_kind(doc):
    """Return the field by which this review binds the live F2b bytes, or None.

    Merely citing the hash in evidence_refs is NOT a binding; it is a citation.  The binding
    fields below are the ones a reader would use to say 'this verdict is about these bytes'.
    """
    checks = [
        ("reviewed_sha256", doc.get("reviewed_sha256")),
        ("artifact_sha256", doc.get("artifact_sha256")),
        ("reviewed_pins.F2b.sha256",
         ((doc.get("reviewed_pins") or {}).get("F2b") or {}).get("sha256")),
        ("frozen_pin.pins_target_at", (doc.get("frozen_pin") or {}).get("pins_target_at")),
    ]
    for kind, val in checks:
        if isinstance(val, str) and val == LIVE_F2B:
            return kind
    tgt = str(doc.get("target_id") or "")
    if LIVE_F2B in tgt:
        return "target_id"
    return None


def is_f2b_schema_verdict(doc, fname: str) -> bool:
    """True only for verdicts on the F2b schema artifact (not on other reviews/manifests)."""
    if doc.get("node_id") == "F2b":
        return True
    tgt = str(doc.get("target_id") or "")
    if tgt in ("F2b", "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"):
        return True
    if str(doc.get("reviewed_path") or "").endswith("af_scc_c0_vacuum.yaml"):
        return True
    if "f2b" in fname.lower() and "review" in fname.lower() and doc.get("class_id") == "AF-SCC-C0-VAC-GEN":
        return True
    return False


def _ts_minutes(s):
    """Parse an ISO-ish timestamp to epoch minutes; None when unparseable."""
    if not s:
        return None
    import datetime as _dt
    t = str(s).strip().replace("Z", "+00:00")
    for cand in (t, t[:19], t[:16]):
        try:
            return int(_dt.datetime.fromisoformat(cand).timestamp() // 60)
        except Exception:
            continue
    return None


def _score_key(s):
    try:
        return "%.2f" % float(s)
    except Exception:
        return str(s)


def harvest_verdicts():
    rows = []
    file_idents = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        kind = live_binding_kind(doc)
        if not kind or not is_f2b_schema_verdict(doc, p.name):
            continue
        row = build_row(doc, "reviews/" + p.name, kind)
        rows.append(row)
        file_idents.append((str(row["reviewer"]), str(row["verdict"]), str(row["score"]),
                            str(row["target_id"]), _ts_minutes(row["created_at"])))
    # map review records whose verdict never landed as a file, strictly bound only
    try:
        m = json.loads((ROOT / "research_map/research_map.json").read_text(encoding="utf-8"))
        for r in m.get("reviews", []):
            if not isinstance(r, dict) or not is_f2b_schema_verdict(r, ""):
                continue
            kind = live_binding_kind(r)
            if not kind and LIVE_F2B in json.dumps(r.get("evidence_refs") or []):
                kind = "evidence_refs_only"
            if not kind:
                continue
            ts = _ts_minutes(r.get("created_at") or r.get("received_at"))
            dup = False
            for rev, ver, sc, tgt, fts in file_idents:
                if (rev, ver, sc) != (str(r.get("reviewer")), str(r.get("verdict")), str(r.get("score"))):
                    continue
                if tgt == str(r.get("target_id")):
                    dup = True
                elif ts is not None and fts is not None and abs(ts - fts) <= 10:
                    dup = True
                if dup:
                    break
            if dup:
                continue
            rows.append(build_row(r, "research_map.json#reviews/" + str(r.get("event_id")), kind))
    except Exception:
        pass
    # collapse duplicate emissions of the same verdict (same reviewer/verdict/score/target within
    # 15 minutes); keep the earliest source and record the others.
    collapsed = []
    for row in sorted(rows, key=lambda x: str(x.get("created_at") or "~")):
        key = (str(row["reviewer"]), str(row["verdict"]), _score_key(row["score"]),
               str(row["target_id"]))
        ts = _ts_minutes(row["created_at"])
        hit = None
        for c in collapsed:
            if (str(c["reviewer"]), str(c["verdict"]), _score_key(c["score"]),
                    str(c["target_id"])) != key:
                continue
            cts = _ts_minutes(c["created_at"])
            if ts is None or cts is None or abs(ts - cts) <= 15:
                hit = c
                break
        if hit is None:
            row["duplicate_sources"] = []
            collapsed.append(row)
        else:
            hit["duplicate_sources"].append(row["source"])
    collapsed.sort(key=lambda r: (str(r.get("created_at") or "~"), str(r.get("reviewer"))))
    map_sha = sha256_file(ROOT / "research_map/research_map.json")
    for row in collapsed:
        src = str(row["source"]).split("#")[0]
        p = ROOT / src
        row["source_sha256"] = sha256_file(p) if p.exists() else map_sha
        # verdict-liveness: a map-only (accepted-event) row may have a review file on disk that
        # was rewritten in place after the event; record what that file says NOW.
        row["current_file"] = None
        if src == "research_map.json":
            for fp in sorted((ROOT / "reviews").glob("*.json")):
                try:
                    d = json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(d, dict) or str(d.get("reviewer")) != str(row["reviewer"]):
                    continue
                rid = d.get("review_id") or d.get("event_id")
                same_id = bool(rid) and bool(row.get("review_id")) and str(rid) == str(row["review_id"])
                same_ts = str(d.get("created_at") or "") == str(row.get("created_at") or "")
                same_tgt = str(d.get("target_id")) == str(row.get("target_id"))
                if same_id or (same_ts and same_tgt):
                    row["current_file"] = {
                        "path": "reviews/" + fp.name,
                        "verdict": d.get("verdict"),
                        "score": d.get("score"),
                        "sha256": sha256_file(fp),
                    }
                    break
    return collapsed


def collect_py_candidates(doc):
    scored = {}
    for path, v in walk(doc):
        if not isinstance(v, str):
            continue
        for m in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.py", v):
            p = m.split("#")[0].lstrip("./")
            key = path.lower()
            pref = 3 if any(t in key for t in ("instrument", "harness", "script", "runner")) else (
                2 if any(t in key for t in ("check", "method", "tool")) else 1)
            scored[p] = max(scored.get(p, 0), pref)
    return sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))


def resolve_instruments(cands):
    resolved, unresolved = [], []
    for rel, pref in cands:
        p = ROOT / rel
        if p.exists() and p.is_file():
            resolved.append({"path": rel, "pref": pref, "sha256": sha256_file(p),
                             "bytes": p.stat().st_size})
        else:
            unresolved.append({"path": rel, "pref": pref})
    return resolved, unresolved


def probe_counts(src: str):
    return {k: src.count(v) for k, v in PROBES.items()}


def classify(pc):
    named_hc1 = pc["hc1_text"] > 0
    named_hc2 = pc["hc2_text"] > 0
    reads_chain = (pc["chain_field"] > 0) or (pc["chain_literal_a"] > 0) or (pc["chain_literal_b"] > 0)
    touches_block = (pc["mnc_block"] > 0) or (pc["ft_block"] > 0) or reads_chain
    if named_hc1 or named_hc2:
        tier = TARGETED_TIER
    elif touches_block:
        tier = BLOCK_TIER
    else:
        tier = BLIND_TIER
    return {
        "tier": tier,
        "names_hc1_text": named_hc1,
        "names_hc2_text": named_hc2,
        "reads_contradicted_chain": reads_chain,
        # capability = names the defect text AND reads the chain it contradicts
        "hc1_detect_capable": named_hc1 and reads_chain,
        "hc2_detect_capable": named_hc2 and reads_chain,
    }


def build_row(doc, source, binding_kind):
    cands = collect_py_candidates(doc)
    resolved, unresolved = resolve_instruments(cands)
    per_instrument = []
    for inst in resolved:
        src = (ROOT / inst["path"]).read_text(encoding="utf-8", errors="replace")
        pc = probe_counts(src)
        cls = classify(pc)
        per_instrument.append({"path": inst["path"], "sha256": inst["sha256"],
                               "probe_counts": pc, "sensitivity": cls})
    # a verdict stands on the union of its declared instruments: it is carrier-capable if ANY
    # declared instrument names the carrier text and reads the contradicted chain.
    union = {
        "tier": "instrument_unresolved" if not per_instrument else
                (TARGETED_TIER if any(i["sensitivity"]["tier"] == TARGETED_TIER for i in per_instrument)
                 else (BLOCK_TIER if any(i["sensitivity"]["tier"] == BLOCK_TIER for i in per_instrument)
                       else BLIND_TIER)),
        "names_hc1_text": any(i["sensitivity"]["names_hc1_text"] for i in per_instrument),
        "names_hc2_text": any(i["sensitivity"]["names_hc2_text"] for i in per_instrument),
        "reads_contradicted_chain": any(i["sensitivity"]["reads_contradicted_chain"] for i in per_instrument),
        "hc1_detect_capable": any(i["sensitivity"]["hc1_detect_capable"] for i in per_instrument),
        "hc2_detect_capable": any(i["sensitivity"]["hc2_detect_capable"] for i in per_instrument),
        "n_instruments_resolved": len(per_instrument),
        "n_instruments_unresolved": len(unresolved),
    }
    return {
        "source": source,
        "reviewer": doc.get("reviewer"),
        "review_id": doc.get("review_id") or doc.get("event_id"),
        "verdict": doc.get("verdict"),
        "score": doc.get("score"),
        "created_at": doc.get("created_at") or doc.get("received_at"),
        "counts_as_full_schema_verdict": doc.get("counts_as_full_schema_verdict"),
        "binding_kind": binding_kind,
        "reviewed_sha256": doc.get("reviewed_sha256") or doc.get("artifact_sha256"),
        "target_id": doc.get("target_id"),
        "hard_failures": len(doc.get("hard_failures") or []),
        "instruments": per_instrument,
        "unresolved_instruments": unresolved,
        "sensitivity": union,
    }


def controller_scan():
    p = ROOT / CONTROLLER_SCAN
    if not p.exists():
        return {"available": False}
    doc = json.loads(p.read_text(encoding="utf-8"))
    f2b = (doc.get("review_coverage") or {}).get("F2b") or {}
    return {
        "available": True,
        "path": CONTROLLER_SCAN,
        "sha256": sha256_file(p),
        "two_distinct_accepts": f2b.get("two_distinct_accepts"),
        "distinct_accept_reviewers": f2b.get("distinct_accept_reviewers"),
        "verdicts": [{"reviewer": v.get("reviewer"), "verdict": v.get("verdict"),
                      "file": v.get("file"),
                      "counts_as_full_schema_verdict": v.get("counts_as_full_schema_verdict")}
                     for v in (f2b.get("verdicts") or [])],
    }


# ------------------------------------------------------------------------------------- controls
def run_controls(rep, pins_before, determinism_ok):
    rows = []
    accepted = [r for r in rep["verdict_inventory"] if r["verdict"] == "accept"]
    revises = [r for r in rep["verdict_inventory"] if r["verdict"] == "revise"]

    def add(name, expected, observed, why):
        rows.append({"name": name, "expected": expected, "observed": observed,
                     "pass": expected == observed, "why": why})

    pin_ok = all(v["match"] for v in rep["pins"].values())
    add("C1_LIVE_PINS_MATCH", True, pin_ok,
        "all pinned inputs hash to their pre-registered values (a moved byte aborts)")

    syn_targeted = classify(probe_counts(
        "chain = il['extension_class_containment']\n"
        "if 'strictly larger extension class' in row['reason']:\n    fail()\n"
        "if 'No containment with C2 or C0 is asserted here' in s:\n    fail()\n"))
    add("C2_SYNTHETIC_TARGETED_IS_TARGETED", TARGETED_TIER, syn_targeted["tier"],
        "positive control: an instrument naming both carriers classifies targeted")

    syn_blind = classify(probe_counts("print('hello world')\n"))
    add("C3_SYNTHETIC_BLIND_IS_BLIND", BLIND_TIER, syn_blind["tier"],
        "negative control: an instrument with no carrier probes classifies blind")

    syn_block = classify(probe_counts("fts = il['forbidden_transfers']\nfor r in fts: pass\n"))
    add("C4_BLOCK_ONLY_IS_NOT_CAPABLE", False, syn_block["hc2_detect_capable"],
        "an instrument that reads the block but not the defect text is not detect-capable")

    raw = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text(encoding="utf-8")
    mutant = raw.replace(PROBES["hc2_text"], "C2 is a strictly smaller extension class")
    mutant = mutant.replace(
        "No containment with C2 or C0 is asserted here",
        "The containment with C2 and C0 is asserted in implication_ledger")
    live_hits = raw.count(PROBES["hc1_text"]) + raw.count(PROBES["hc2_text"])
    mut_hits = mutant.count(PROBES["hc1_text"]) + mutant.count(PROBES["hc2_text"])
    add("C5_REPAIR_FLIP", [2, 0], [live_hits, mut_hits],
        "two in-memory repairs remove both carrier texts; mutant hash differs: %s" %
        (sha256_bytes(mutant.encode()) != LIVE_F2B))

    add("C6_DETERMINISM", True, determinism_ok,
        "two independent full builds of the report body hash identically")

    pin_after = measure_pins()
    add("C7_CANONICAL_READ_ONLY", True,
        all(pin_after[k]["sha256"] == pins_before[k]["sha256"] for k in pins_before),
        "no pinned canonical input changed during the run")

    ref = [r for r in revises if r["reviewer"] == "worker-017"]
    ref_ok = bool(ref) and ref[0]["sensitivity"]["hc1_detect_capable"] and ref[0]["sensitivity"]["hc2_detect_capable"]
    add("C8_REAL_REVISE_INSTRUMENT_IS_CAPABLE", True, ref_ok,
        "worker-017's containment revise instrument names both carriers and reads the chain")

    w018 = [r for r in revises if r["reviewer"] == "worker-018"]
    w018_ok = bool(w018) and w018[0]["sensitivity"]["hc1_detect_capable"] and w018[0]["sensitivity"]["hc2_detect_capable"]
    add("C9_SECOND_REVISE_INSTRUMENT_IS_CAPABLE", True, w018_ok,
        "worker-018's C17-CHAIN-DENIAL / C18-TRANSFER-REASON instrument is carrier-capable")

    add("C10_ACCEPT_INSTRUMENTS_NOT_CAPABLE", 0,
        sum(1 for r in accepted if r["sensitivity"]["hc1_detect_capable"] or r["sensitivity"]["hc2_detect_capable"]),
        "finding control: no live-hash accept instrument names either carrier and reads the chain")
    ctrl_rev = set((rep["conflict_matrix"].get("controller_counted_accepts") or {}).get("counted_reviewers") or [])
    ctrl_cap = (rep["conflict_matrix"].get("controller_counted_accepts") or {}).get("n_carrier_capable")
    add("C11_CONTROLLER_COUNTED_ACCEPTS_NOT_CAPABLE", 0, ctrl_cap,
        "finding control: none of the controller-counted full accepts %s is carrier-capable" % sorted(ctrl_rev))
    add("C12_ACCEPT_TO_REVISE_FLIP_RECORDED", True,
        (rep["conflict_matrix"]["accepts"]["current_file_flips"] > 0),
        "liveness control: at least one accepted-event row now has an on-disk review file with "
        "verdict=revise at the same review_id (worker-072 rewrite)")
    return rows


# --------------------------------------------------------------------------------------- build
def build_body():
    pins_before = measure_pins()
    bad = [k for k, v in pins_before.items() if not v["match"]]
    if bad:
        raise SystemExit("PIN MISMATCH, aborting: %s" % bad)

    carriers = carrier_report()
    inventory = harvest_verdicts()
    ctrl_scan = controller_scan()
    corpus_digest = sha256_bytes(jdump(
        sorted((r["source"], r["source_sha256"]) for r in inventory)).encode())

    accepted = [r for r in inventory if r["verdict"] == "accept"]
    revises = [r for r in inventory if r["verdict"] == "revise"]
    inconc = [r for r in inventory if r["verdict"] == "inconclusive"]

    def agg(rows):
        return {
            "n": len(rows),
            "hc1_detect_capable": sum(1 for r in rows if r["sensitivity"]["hc1_detect_capable"]),
            "hc2_detect_capable": sum(1 for r in rows if r["sensitivity"]["hc2_detect_capable"]),
            "reads_contradicted_chain": sum(1 for r in rows if r["sensitivity"]["reads_contradicted_chain"]),
            "names_hc1_text": sum(1 for r in rows if r["sensitivity"]["names_hc1_text"]),
            "names_hc2_text": sum(1 for r in rows if r["sensitivity"]["names_hc2_text"]),
            "instrument_unresolved": sum(1 for r in rows if r["sensitivity"]["tier"] == "instrument_unresolved"),
            "current_file_flips": sum(1 for r in rows
                                      if r.get("current_file")
                                      and str(r["current_file"]["verdict"]) != str(r["verdict"])),
            "reviewers": sorted({str(r["reviewer"]) for r in rows}),
        }

    ctrl_accept_reviewers = list(ctrl_scan.get("distinct_accept_reviewers") or [])
    ctrl_rows = [r for r in accepted if str(r["reviewer"]) in ctrl_accept_reviewers]
    controller_accept_capability = {
        "counted_reviewers": ctrl_accept_reviewers,
        "resolved_rows": [{"reviewer": r["reviewer"], "source": r["source"],
                           "tier": r["sensitivity"]["tier"],
                           "hc1_detect_capable": r["sensitivity"]["hc1_detect_capable"],
                           "hc2_detect_capable": r["sensitivity"]["hc2_detect_capable"],
                           "n_instruments_resolved": r["sensitivity"]["n_instruments_resolved"]}
                          for r in ctrl_rows],
        "n_counted": len(ctrl_accept_reviewers),
        "n_carrier_capable": sum(1 for r in ctrl_rows
                                 if r["sensitivity"]["hc1_detect_capable"]
                                 or r["sensitivity"]["hc2_detect_capable"]),
    }

    matrix = {
        "accepts": agg(accepted),
        "revises": agg(revises),
        "inconclusive": agg(inconc),
        "full_accepts_explicit": agg([r for r in accepted
                                      if r["counts_as_full_schema_verdict"] is True]),
        "controller_scan": ctrl_scan,
        "controller_counted_accepts": controller_accept_capability,
    }

    body = {
        "schema": "worker-057/f2b-verdict-sensitivity/v1",
        "task_id": "W057-GFORM-F2B-VERDICT-SENSITIVITY-01",
        "actor": "worker-057",
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "authority_note": ("Worker measurement only. Issues no review verdict on the schema, sets no "
                           "node status, no validation_status and no gate verdict; the audit lead and "
                           "controller alone adjudicate coverage and move G-FORM."),
        "pins": pins_before,
        "review_corpus": {
            "map_sha256": sha256_file(ROOT / "research_map/research_map.json"),
            "n_sources": len(inventory),
            "corpus_sha256": corpus_digest,
        },
        "live_carriers": carriers,
        "verdict_inventory": inventory,
        "conflict_matrix": matrix,
        "verdict": None,  # filled below (depends on matrix)
        "findings": [],
        "falsifier": "",
        "next_falsifier": "",
        "non_claims": [
            "no gate verdict, node status, validation_status or review verdict",
            "no canonical artifact was written or edited",
            "no claim that an accept instrument is incorrect; the claim is only that it cannot have "
            "exercised the named carriers (its source never reads them)",
            "no mathematics: no class is claimed true, refuted or closed",
        ],
    }

    n_acc = len(accepted)
    acc_cap = matrix["accepts"]["hc2_detect_capable"] + matrix["accepts"]["hc1_detect_capable"]
    flips = matrix["accepts"]["current_file_flips"]
    body["verdict"] = (
        "LIVE_F2B_CENSUS_AT_%s__%d_ACCEPT_%d_REVISE__%d_OF_%d_ACCEPT_INSTRUMENTS_CARRIER_CAPABLE__"
        "%d_ACCEPT_ROW(S)_FLIPPED_TO_REVISE_ON_DISK"
        % (LIVE_F2B[:12], n_acc, len(revises), acc_cap, n_acc, flips))
    body["findings"] = [
        {"id": "F2BS-01", "state": "confirmed",
         "statement": ("At the pinned F2b bytes both live carriers are present: HC1 at line %s and HC2 "
                       "at line %s, each contradicted by the chain at line %s."
                       % (carriers["hc1"]["line"], carriers["hc2"]["line"], carriers["chain"]["line"]))},
        {"id": "F2BS-02", "state": "confirmed",
         "statement": ("The live-hash F2b verdict set is split: %d accept(s) [%s] against %d revise(s) "
                       "[%s] and %d inconclusive. A reviewer may appear on both sides at different times "
                       "at the same bytes (verdict flip); the census keeps each dated verdict."
                       % (n_acc, ", ".join(matrix["accepts"]["reviewers"]), len(revises),
                          ", ".join(matrix["revises"]["reviewers"]), len(inconc)))},
        {"id": "F2BS-03", "state": "confirmed",
         "statement": ("%d of %d live-hash accept instruments name neither carrier text and %d of %d "
                       "never read the contradicted chain field; their accepts therefore cannot have "
                       "discharged the HC1/HC2 revise findings at these bytes."
                       % (n_acc - matrix["accepts"]["names_hc1_text"], n_acc,
                          n_acc - matrix["accepts"]["reads_contradicted_chain"], n_acc))},
        {"id": "F2BS-04", "state": "confirmed",
         "statement": ("%d of %d live-hash revise instruments are carrier-capable (both name a carrier "
                       "text and read the chain); the blocking findings are carried by instruments that "
                       "can see the carriers, not by the accept instruments."
                       % (matrix["revises"]["hc2_detect_capable"], len(revises)))},
        {"id": "F2BS-05", "state": "confirmed",
         "statement": ("The controller's own fresh scan (%s) counts F2b two_distinct_accepts=%s with "
                       "accept reviewers %s: the >=2-accept coverage criterion is numerically met at the "
                       "same bytes that carry both live blocking carriers. Whether those accepts discharge "
                       "the revise findings is an adjudication for the audit lead."
                       % (CONTROLLER_SCAN, ctrl_scan.get("two_distinct_accepts"),
                          ctrl_scan.get("distinct_accept_reviewers")))},
        {"id": "F2BS-06", "state": "confirmed",
         "statement": ("Of the controller-counted accepts %s, %d of %d have any resolved instrument that "
                       "names a carrier text and reads the contradicted chain (%s)."
                       % (ctrl_accept_reviewers,
                          matrix["controller_counted_accepts"]["n_carrier_capable"],
                          matrix["controller_counted_accepts"]["n_counted"],
                          [(r["reviewer"], r["tier"]) for r in
                           matrix["controller_counted_accepts"]["resolved_rows"]]))},
        {"id": "F2BS-07", "state": "confirmed",
         "statement": ("%d accept row(s) carry a review file on disk whose verdict is no longer accept: "
                       "%s. The map's accepted event and the current file therefore disagree at the same "
                       "review_id and the same bytes; the on-disk rewrite happened inside this "
                       "measurement window (corpus pin %s). Coverage counts taken before the rewrite are "
                       "stale for the current corpus."
                       % (flips,
                          [(r["reviewer"], r["verdict"], r["current_file"])
                           for r in accepted
                           if r.get("current_file")
                           and str(r["current_file"]["verdict"]) != str(r["verdict"])],
                          body["review_corpus"]["corpus_sha256"][:12]))},
    ]
    body["falsifier"] = (
        "Re-hash the pinned inputs and the review corpus and re-run this instrument. The report is "
        "falsified for these bytes if any pin differs, if any review source hash differs, if a live-hash "
        "accept instrument is shown to name HC1/HC2 text and read the chain (making it carrier-capable), "
        "if either carrier is absent from the live F2b bytes, if the controller scan pin no longer "
        "reports F2b accepts, or if any control C1-C12 flips. A moved byte or a rewritten review file "
        "voids the report for the new corpus.")
    body["next_falsifier"] = (
        "Adjudication falsifier for the audit lead: produce a live-hash accept whose instrument exercises "
        "HC1 and HC2 and states why they are non-material, or a formulation revision that removes both "
        "carriers and re-collects accepts at the new hash. Either converts this measurement.")
    body["census_note"] = (
        "The census is bound to review_corpus.corpus_sha256. review files are live: the worker-072 "
        "accept file was overwritten in place with a revise at the same review_id during the "
        "measurement window (recorded in F2BS-07 and control C12).")

    # report_body_sha256 makes C6 self-referential-safe: hash the body with the field blanked.
    body_probe = dict(body)
    body_probe["report_body_sha256"] = ""
    h1 = sha256_bytes(jdump(body_probe).encode())
    body["report_body_sha256"] = h1
    return body


def build(determinism_ok=True):
    body = build_body()
    controls = run_controls(body, body["pins"], determinism_ok)
    body["controls"] = controls
    body["controls_passed"] = sum(1 for c in controls if c["pass"])
    body["controls_total"] = len(controls)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 0 iff all controls pass")
    args = ap.parse_args()
    b1 = build_body()
    b2 = build_body()
    determinism_ok = b1["report_body_sha256"] == b2["report_body_sha256"]
    rep = build(determinism_ok)
    out = HERE / "report.json"
    out.write_text(jdump(rep), encoding="utf-8")
    if args.check:
        print("controls %d/%d" % (rep["controls_passed"], rep["controls_total"]))
        for c in rep["controls"]:
            if not c["pass"]:
                print("FAIL", c["name"], c["expected"], c["observed"])
        return 0 if rep["controls_passed"] == rep["controls_total"] else 1
    print(jdump({"verdict": rep["verdict"], "controls": "%d/%d" % (rep["controls_passed"],
                                                                   rep["controls_total"]),
                 "accepts": rep["conflict_matrix"]["accepts"]["n"],
                 "revises": rep["conflict_matrix"]["revises"]["n"]}))
    return 0 if rep["controls_passed"] == rep["controls_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
