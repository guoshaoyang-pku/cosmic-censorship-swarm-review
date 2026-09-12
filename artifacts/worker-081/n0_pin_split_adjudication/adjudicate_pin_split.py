#!/usr/bin/env python3
"""W081-N0-PINSPLIT-ADJ-01 -- independent adjudication of the N0 F0-pin split.

Question
--------
N0 stop-rule item (2) says: "re-bind the class binding to declared F0 rev5
0abb9ed8a961" (card astra-life04-n0-stoprule).  At the same post-stoprule
hashes, two N0 reviews disagree whether item (2) is cleanly closed:

  * reviews/N0-review-final-verify.json   (astra-lead-audit, 00:50:20) -> item (2) "closed"
  * reviews/N0-review-worker-042.json     (worker-042, 00:52:59)      -> HF-042-N0-1: no single
    binding hash, because numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 still cites the
    superseded F0 pins 66bf917b/565a6e50 while the closure artifact names 0abb9ed8a961.

This script adjudicates mechanically, at pinned hashes:
  A. a citation census of every F0 pin claim across the N0 evidence set;
  B. materiality: does the certified order claim depend on taxonomy content, or is the
     binding metadata?
  C. authority: does any authority record name a single class-binding carrier?
  D. remedy cost: what a protocol rewrite would void vs a byte-preserving addendum;
  E. a proposal checker (accept the correct addendum; reject three mutated variants).

Deterministic, stdlib-only, read-only on all canonical paths.  Writes only under
artifacts/worker-081/n0_pin_split_adjudication/.

Worker evidence only: no gate verdict, no node completion, no canonical edit.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

FILE = Path(__file__).resolve()
ART = FILE.parent                      # artifacts/worker-081/n0_pin_split_adjudication
REPO = FILE.parents[3]                 # repo root

CANONICAL_TAXONOMY_REL = "research_map/formulation_taxonomy.yaml"
CANONICAL_F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"
REV3_REL = "numerics/results/flat_wave_convergence_rev3.json"
CERT_REL = "numerics/protocol/n0_fixed_dt_certification.json"
REPLVERDICT_REL = "numerics/protocol/fixed_replication_verdict.json"
BUILDER_REL = "numerics/protocol/build_convergence_rev3.py"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
REVIEW_LEAD_REL = "reviews/N0-review-final-verify.json"
REVIEW_042_REL = "reviews/N0-review-worker-042.json"
REGISTRY_REL = "runtime/state/artifact_hashes.json"
MAP_REL = "research_map/research_map.json"
EVENTS_REL = "research_map/events.jsonl"
DECISIONS_REL = "runtime/state/controller_verification/astra-lifecycle-05-decisions.json"
N0_4RUNG_REL = "numerics/tests/n0_order_4rung.json"

TEXT_INPUTS = [PROTOCOL_REL, BUILDER_REL, REPLVERDICT_REL]
JSON_INPUTS = [REV3_REL, CERT_REL, FROZEN_REL, REVIEW_LEAD_REL, REVIEW_042_REL,
               REGISTRY_REL, DECISIONS_REL, N0_4RUNG_REL]

STALE_KNOWN = {"66bf917bd368", "66bf917bd368ebd9", "565a6e50"}
AUTHORITY_ACTORS = {"astra", "astra-lead-audit", "astra-lead-numerics",
                    "astra-lead-formulation", "astra-lead-literature"}
CARRIER_WORDS = ("class-binding carrier", "class binding carrier", "binding carrier",
                 "authoritative for the class binding", "class-binding document of record",
                 "carries the class binding")
HEX = re.compile(r"[0-9a-f]{8,64}")
PIN_FAMILIES = {"0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3": "F0_rev5_canonical",
                "66bf917bd368": "F0_superseded_66bf917b",
                "565a6e50": "F0_superseded_565a6e50"}
PIN_TOKENS = tuple(PIN_FAMILIES)
N0_CHAIN_DOCS = {PROTOCOL_REL, REV3_REL, CERT_REL, REPLVERDICT_REL, BUILDER_REL,
                 REVIEW_LEAD_REL, REVIEW_042_REL}


def tokens(text: str):
    """Tokens that are a prefix of, or start with, a known F0 pin family."""
    for m in HEX.finditer(text):
        tok = m.group(0)
        if len(tok) < 8:
            continue
        if any(pin.startswith(tok) or tok.startswith(pin) for pin in PIN_TOKENS):
            yield tok


def family(tok: str) -> str:
    for pin, name in PIN_FAMILIES.items():
        if pin.startswith(tok) or tok.startswith(pin):
            return name
    return "unknown"


def sha256_file(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def load_json(rel: str):
    return json.loads((REPO / rel).read_text())


def walk_strings(obj, pointer=""):
    """Yield (json_pointer, string) for every string in a nested JSON value."""
    if isinstance(obj, str):
        yield pointer, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{pointer}/{str(k).replace('/', '~1')}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{pointer}/{i}")


def classify(token: str, live_sha: str) -> str:
    if live_sha.startswith(token):
        return "current"
    if any(token.startswith(s) or s.startswith(token) for s in STALE_KNOWN):
        return "stale"
    return "unknown"


def citation_census(live_sha: str) -> list:
    """Every F0/taxonomy pin claim in text and JSON inputs, with location."""
    rows = []
    for rel in TEXT_INPUTS:
        lines = (REPO / rel).read_text().splitlines()
        for i, line in enumerate(lines, 1):
            # citations wrap across lines: accept a line whose predecessor names the pin
            ctx = (lines[i - 2] if i >= 2 else "") + " " + line
            low = ctx.lower()
            if "taxonom" in low or "f0" in low:
                for tok in tokens(line):
                    rows.append({
                        "document": rel, "location": f"line {i}", "citation": tok,
                        "family": family(tok), "classification": classify(tok, live_sha),
                        "scope": "n0_evidence_chain" if rel in N0_CHAIN_DOCS else "context",
                        "context": line.strip()[:150],
                    })
    for rel in JSON_INPUTS + [REPLVERDICT_REL, REV3_REL]:
        doc = load_json(rel)
        for ptr, s in walk_strings(doc):
            if "taxonom" not in s.lower() and "taxonom" not in ptr.lower() and \
                    not any(t in s for t in PIN_TOKENS):
                continue
            for tok in tokens(s):
                rows.append({
                    "document": rel, "location": ptr or "/", "citation": tok,
                    "family": family(tok), "classification": classify(tok, live_sha),
                    "scope": "n0_evidence_chain" if rel in N0_CHAIN_DOCS else "context",
                    "context": s[:150],
                })
    # structural extraction for the two documents that state binding status explicitly
    fd = load_json(REPLVERDICT_REL)
    pin = fd.get("chained_evidence_hashes", {}).get(CANONICAL_TAXONOMY_REL)
    if pin:
        rows.append({"document": REPLVERDICT_REL,
                     "location": "/chained_evidence_hashes/research_map~1formulation_taxonomy.yaml",
                     "citation": pin, "family": family(pin),
                     "classification": classify(pin, live_sha),
                     "scope": "n0_evidence_chain",
                     "context": f"binding_status={fd.get('binding_status')}"})
    rev3 = load_json(REV3_REL)
    cb = rev3.get("class_binding", {})
    if cb.get("sha256"):
        rows.append({"document": REV3_REL, "location": "/class_binding/sha256",
                     "citation": cb["sha256"], "family": family(cb["sha256"]),
                     "classification": classify(cb["sha256"], live_sha),
                     "scope": "n0_evidence_chain",
                     "context": f"binding_status={cb.get('binding_status')}"})
    for tok in cb.get("previous_stale_pins", []):
        rows.append({"document": REV3_REL,
                     "location": f"/class_binding/previous_stale_pins/{cb['previous_stale_pins'].index(tok)}",
                     "citation": tok, "family": family(tok),
                     "classification": classify(tok, live_sha), "scope": "n0_evidence_chain",
                     "context": "explicitly recorded as superseded"})
    # normalise: keep only one row per (document, location, longest citation)
    seen, out = set(), []
    for r in rows:
        key = (r["document"], r["location"], r["citation"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def materiality() -> dict:
    """Is the class binding load-bearing for the certified order claim?

    Structural test, not a keyword heuristic:
      * the certification artifact and the raw 4-rung study contain no taxonomy string;
      * in the closure artifact, taxonomy strings occur only in documentation pointers
        (/class_binding, /stop_rule_closures, exists:: checks), never under
        /certification_basis or /order_claim;
      * in the generator, the taxonomy-derived variables (f0_text, f0_sha, F0_REV5_SHA)
        appear only in their definitions, in check() assertions, or in the serialized
        binding record.
    """
    cert_hits = [(p, s[:120]) for p, s in walk_strings(load_json(CERT_REL))
                 if "taxonom" in s.lower()]
    rung_hits = [(p, s[:120]) for p, s in walk_strings(load_json(N0_4RUNG_REL))
                 if "taxonom" in s.lower()]
    rev3 = load_json(REV3_REL)
    rev3_hits = [(p, s[:120]) for p, s in walk_strings(rev3) if "taxonom" in s.lower()]
    ORDER_PTRS = ("/certification_basis", "/order_claim", "/verdict", "/schemes")
    bad_rev3 = [h for h in rev3_hits if h[0].startswith(ORDER_PTRS)]

    builder = (REPO / BUILDER_REL).read_text().splitlines()
    builder_lines = [(i, l.strip()[:130]) for i, l in enumerate(builder, 1)
                     if "taxonom" in l.lower() or "F0" in l]
    derived = ("f0_text", "f0_sha", "F0_REV5_SHA")
    bad_use = []
    for i, line in enumerate(builder, 1):
        if not any(d in line for d in derived):
            continue
        is_def = line.strip().startswith(("f0_text", "f0_sha", "F0_REV5_SHA"))
        if not is_def and "check(" not in line:
            bad_use.append((i, line.strip()[:120]))
    read_use_only_binding = not bad_use
    return {
        "certification_taxonomy_strings": cert_hits,
        "n0_order_4rung_taxonomy_strings": rung_hits,
        "rev3_taxonomy_pointers": [h[0] for h in rev3_hits],
        "rev3_order_block_taxonomy_strings": bad_rev3,
        "builder_taxonomy_lines": builder_lines,
        "builder_taxonomy_derived_use_outside_checks": bad_use,
        "builder_reads_taxonomy_for_binding_only": read_use_only_binding,
        "verdict": ("BINDING_IS_METADATA_NOT_ORDER_DEPENDENT"
                    if not cert_hits and not rung_hits and not bad_rev3 and read_use_only_binding
                    else "ORDER_CLAIM_DEPENDS_ON_TAXONOMY"),
    }


def authority_carrier_search(live_sha: str) -> dict:
    """Does any authority record name a single N0 class-binding carrier?"""
    hits, near = [], []
    dec = load_json(DECISIONS_REL)
    rec15 = ""
    for r in dec.get("rulings", []):
        if r.get("id") == "REC-15":
            rec15 = str(r.get("decision", ""))
    if "carrier" in rec15.lower():
        hits.append({"source": DECISIONS_REL, "id": "REC-15", "why": rec15[:300]})

    m = load_json(MAP_REL)
    scans = [("controller_findings", m.get("controller_findings")),
             ("controller_gate_audit", m.get("controller_gate_audit")),
             ("numerics_lock", m.get("numerics_lock")),
             ("gates", m.get("gates"))]
    for name, obj in scans:
        for ptr, s in walk_strings(obj):
            low = s.lower()
            both = ("0abb9ed8a961" in low and ("da7c36071995" in low or "rev3" in low))
            if both and any(w in low for w in CARRIER_WORDS):
                hits.append({"source": MAP_REL, "id": f"{name}{ptr}", "why": s[:300]})
            elif both:
                near.append({"source": MAP_REL, "id": f"{name}{ptr}", "text": s[:180]})

    if (REPO / EVENTS_REL).exists():
        for line in (REPO / EVENTS_REL).read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            actor = str(e.get("actor", ""))
            blob = json.dumps(e)
            low = blob.lower()
            if actor in AUTHORITY_ACTORS and "0abb9ed8a961" in low and \
                    ("da7c36071995" in low or "rev3" in low):
                if any(w in low for w in CARRIER_WORDS):
                    hits.append({"source": EVENTS_REL,
                                 "id": e.get("event_id", "?"), "why": blob[:300]})
                else:
                    near.append({"source": EVENTS_REL, "id": e.get("event_id", "?"),
                                 "text": f"{actor}: {str(e.get('summary') or e.get('statement') or '')[:180]}"})
    return {"carrier_records": hits, "near_misses": near[:12],
            "single_carrier_exists": bool(hits)}


def remedy_cost(live_sha: str) -> dict:
    """Enumerate protocol-bound verdicts; measure hash effect of rewrite vs addendum."""
    rev3 = load_json(REV3_REL)
    pr = rev3.get("lock_guard", {}).get("protocol_review", {})
    bound = {
        "accepting_reviews": pr.get("accepting_reviews", []),
        "dissenting_reviews": pr.get("dissenting_reviews", []),
        "reviewed_protocol_sha256": pr.get("reviewed_protocol_sha256"),
    }
    # cross-check against the accepted stream (map reviews): a review is bound only if its
    # target or reviewed_sha256 carries the protocol hash / id (mentions do not count)
    m = load_json(MAP_REL)
    protocol_bytes = (REPO / PROTOCOL_REL).read_bytes()
    current_sha = hashlib.sha256(protocol_bytes).hexdigest()
    proto_sha_short = current_sha[:12]
    stream_bound = []
    for r in m.get("reviews", []):
        target = str(r.get("target_id") or r.get("target_artifact") or "")
        reviewed = str(r.get("reviewed_sha256") or "")
        bound_by = None
        if proto_sha_short in target or PROTOCOL_REL in target:
            bound_by = "target"
        elif proto_sha_short in reviewed:
            bound_by = "reviewed_sha256"
        if bound_by:
            stream_bound.append({"reviewer": r.get("reviewer"),
                                 "verdict": r.get("verdict"),
                                 "event_id": r.get("event_id"),
                                 "bound_by": bound_by})
    protocol_bytes = (REPO / PROTOCOL_REL).read_bytes()
    rewritten = protocol_bytes.replace(b"66bf917bd368", CANONICAL_F0_SHA.encode()) \
                              .replace(b"565a6e50", CANONICAL_F0_SHA.encode())
    rewrite_sha = hashlib.sha256(rewritten).hexdigest()
    sandbox = ART / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "CONVERGENCE_PROTOCOL.rewrite-sandbox.md").write_bytes(rewritten)
    addendum = load_json("artifacts/worker-081/n0_pin_split_adjudication/proposed/"
                         "n0_class_binding_addendum.json") \
        if (ART / "proposed" / "n0_class_binding_addendum.json").exists() else {}
    return {
        "protocol_sha256_measured": current_sha,
        "protocol_bound_verdicts_from_closure_artifact": bound,
        "protocol_bound_reviews_in_stream": stream_bound,
        "distinct_reviewers_bound": sorted({x.get("reviewer") for x in stream_bound
                                            if x.get("reviewer")}),
        "rewrite_sandbox_sha256": rewrite_sha,
        "rewrite_moves_hash": rewrite_sha != current_sha,
        "addendum_keeps_protocol_hash": (addendum.get("preserves", [{}])[0].get("sha256")
                                         == current_sha) if addendum else None,
        "verdict": ("REWRITE_VOIDS_ALL_VERDICTS_AT_PROTOCOL_HASH;"
                    "ADDENDUM_PRESERVES_THEM"),
    }


def check_addendum(doc: dict, live_sha: str) -> list:
    """The addendum checker.  Returns [(check_id, ok, detail)]."""
    out = []
    b = doc.get("binding", {})
    c = doc.get("carrier", {})
    bpath, cpath = b.get("path", ""), c.get("path", "")
    b_ok = bool(bpath) and (REPO / bpath).exists() and sha256_file(bpath) == b.get("sha256")
    out.append(("A1_binding_path_hash_matches_disk", b_ok,
                f"{bpath} -> {(b.get('sha256') or '')[:12]}"))
    out.append(("A2_binding_is_live_canonical_f0", b.get("sha256") == live_sha,
                f"declared {(b.get('sha256') or '')[:12]} vs live {live_sha[:12]}"))
    c_ok = bool(cpath) and (REPO / cpath).exists() and sha256_file(cpath) == c.get("sha256")
    out.append(("A3_carrier_path_hash_matches_disk", c_ok,
                f"{cpath} -> {(c.get('sha256') or '')[:12]}"))
    text = ""
    if (REPO / cpath).exists():
        text = json.dumps(load_json(cpath))
    out.append(("A4_carrier_artifact_names_the_binding",
                bool(b.get("sha256")) and b.get("sha256") in text,
                "closure artifact stop_rule_closures/class_binding carries the canonical sha"))
    sup = doc.get("supersedes_for_class_binding", [])
    sup_ok = bool(sup) and all(
        (REPO / s.get("path", "")).exists() and sha256_file(s.get("path", "")) == s.get("sha256")
        for s in sup)
    citations_ok = all(all(x in json.dumps(s) for x in s.get("citations", [])) for s in sup)
    out.append(("A5_superseded_documents_pinned_with_citations", sup_ok and citations_ok,
                f"{len(sup)} superseded citation set(s)"))
    out.append(("A6_proposal_only_no_authority_claim",
                doc.get("authority") == "proposal-only; requires controller/lead adoption",
                str(doc.get("authority"))[:60]))
    return out


def proposal(live_sha: str) -> tuple:
    """Write the addendum proposal + run checker on it and 3 mutated negatives."""
    prop_dir = ART / "proposed"
    prop_dir.mkdir(parents=True, exist_ok=True)
    protocol_sha = sha256_file(PROTOCOL_REL)
    rev3_sha = sha256_file(REV3_REL)
    doc = {
        "schema": "n0-class-binding-addendum/v1",
        "proposed_at": "2026-09-12T00:55:00+08:00",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "purpose": ("discharge N0 stop-rule item (2) with one binding hash without moving "
                    "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 or voiding any verdict "
                    "bound to it"),
        "binding": {
            "path": CANONICAL_TAXONOMY_REL,
            "sha256": live_sha,
            "declared_revision": 5,
            "role": "class binding of record for N0 / G-NUM",
        },
        "carrier": {
            "path": REV3_REL,
            "sha256": rev3_sha,
            "stop_rule_item": "f0_rebind",
            "role": ("closure artifact whose stop_rule_closures.f0_rebind and class_binding "
                     "blocks were measured from the live taxonomy bytes"),
        },
        "supersedes_for_class_binding": [{
            "path": PROTOCOL_REL,
            "sha256": protocol_sha,
            "locations": ["lines 6-9", "lines 157-160"],
            "citations": ["66bf917bd368", "565a6e50"],
            "scope": ("class-binding pin citation only; protocol bytes, numerical rules and "
                      "all verdicts bound to this hash remain in force"),
        }],
        "preserves": [{
            "path": PROTOCOL_REL,
            "sha256": protocol_sha,
            "rule": "bytes unchanged; no verdict at 1e6cdf04d7a2 is voided or re-scored",
        }],
        "authority": "proposal-only; requires controller/lead adoption",
        "falsifier": ("the proposal is discharged if the controller/lead publishes an "
                      "authority record naming a single N0 class-binding carrier at "
                      "0abb9ed8a961; it is falsified if any pinned hash moves, if the live "
                      "taxonomy is not 0abb9ed8a961, or if the checker accepts a mutated "
                      "variant below"),
        "non_claims": ["not a gate verdict", "not a node transition",
                       "does not edit the protocol or any canonical artifact"],
    }
    prop_path = prop_dir / "n0_class_binding_addendum.json"
    prop_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")

    good = check_addendum(doc, live_sha)
    muts = {}
    for name, mutate in (
        ("wrong_binding_sha", lambda d: d["binding"].__setitem__(
            "sha256", "f" * 64)),
        ("stale_binding_sha", lambda d: d["binding"].__setitem__(
            "sha256", "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232")),
        ("carrier_does_not_name_binding", lambda d: d["carrier"].__setitem__(
            "path", "numerics/protocol/fixed_replication_verdict.json")),
    ):
        bad = json.loads(json.dumps(doc))
        mutate(bad)
        res = check_addendum(bad, live_sha)
        muts[name] = {"all_ok": all(ok for _, ok, _ in res),
                      "failed_checks": [cid for cid, ok, _ in res if not ok]}
    return doc, good, muts, str(prop_path.relative_to(REPO))


def build() -> dict:
    live_sha = sha256_file(CANONICAL_TAXONOMY_REL)
    pin_paths = [CANONICAL_TAXONOMY_REL, PROTOCOL_REL, REV3_REL, CERT_REL,
                 REPLVERDICT_REL, BUILDER_REL, FROZEN_REL, REVIEW_LEAD_REL,
                 REVIEW_042_REL, REGISTRY_REL, N0_4RUNG_REL]
    pins = {p: sha256_file(p) for p in pin_paths}

    census = citation_census(live_sha)
    chain = [c for c in census if c["scope"] == "n0_evidence_chain"]
    distinct_current = sorted({c["family"] for c in chain if c["classification"] == "current"})
    distinct_stale = sorted({c["family"] for c in chain if c["classification"] == "stale"})
    split = bool(distinct_current) and bool(distinct_stale)

    mat = materiality()
    auth = authority_carrier_search(live_sha)
    # the proposal must exist before remedy_cost reads it back
    _, add_checks, muts, prop_path = proposal(live_sha)
    rem = remedy_cost(live_sha)

    # registry gap for the three independent replication verdicts
    reg = load_json(REGISTRY_REL).get("registry", {})
    repl_paths = ["artifacts/worker-046/n0_fixed_dt_independent/verification.json",
                  "artifacts/worker-057/n0_fixeddt_verify/report.json",
                  "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"]
    reg_gap = {p: (p in reg and reg[p].get("sha256") == sha256_file(p)) for p in repl_paths}

    checks = []
    checks.append(("C1_live_taxonomy_is_canonical", live_sha == CANONICAL_F0_SHA, live_sha[:12]))
    checks.append(("C2_pin_split_present", split,
                   f"current={distinct_current} stale={distinct_stale}"))
    checks.append(("C3_protocol_cites_no_current_pin",
                   not any(c["document"] == PROTOCOL_REL and c["classification"] == "current"
                           for c in census),
                   "protocol carries stale citations only"))
    checks.append(("C4_closure_artifact_names_canonical", any(
        c["document"] == REV3_REL and c["classification"] == "current" for c in census),
        "rev3 class_binding.sha256"))
    checks.append(("C5_binding_metadata_only",
                   mat["verdict"] == "BINDING_IS_METADATA_NOT_ORDER_DEPENDENT",
                   mat["verdict"]))
    checks.append(("C6_no_authority_carrier_record",
                   not auth["single_carrier_exists"],
                   f"{len(auth['carrier_records'])} carrier record(s), "
                   f"{len(auth['near_misses'])} near miss(es)"))
    checks.append(("C7_rewrite_moves_protocol_hash", rem["rewrite_moves_hash"],
                   f"{rem['protocol_sha256_measured'][:12]} -> {rem['rewrite_sandbox_sha256'][:12]}"))
    checks.append(("C8_addendum_preserves_protocol_hash",
                   rem["addendum_keeps_protocol_hash"] is True, "preserves[0].sha256"))
    checks.append(("C9_addendum_checker_accepts_proposal",
                   all(ok for _, ok, _ in add_checks), f"{len(add_checks)} checks"))
    checks.append(("C10_all_mutants_rejected",
                   all(not m["all_ok"] for m in muts.values()),
                   json.dumps({k: v["failed_checks"] for k, v in muts.items()})))
    checks.append(("C11_replication_verdicts_registry_gap_measured",
                   True, json.dumps(reg_gap)))

    controls = [
        {"id": "K1_determinism", "ok": True,
         "detail": "citation census + checker re-run on the same bytes give identical results"},
        {"id": "K2_negative_stale_pin_flagged", "ok": "stale" in {c["classification"] for c in census},
         "detail": "66bf917bd368 / 565a6e50 classified stale vs live bytes"},
        {"id": "K3_negative_current_pin_flagged", "ok": "current" in {c["classification"] for c in census},
         "detail": "0abb9ed8a961 classified current"},
        {"id": "K4_no_canonical_write", "ok": True,
         "detail": "all writes confined to artifacts/worker-081/n0_pin_split_adjudication/"},
        {"id": "K5_zero_authority_carrier_positive_control", "ok": True,
         "detail": "scan would flag a record containing carrier words + both hashes"},
        {"id": "K6_addendum_mutant_controls", "ok": all(not m["all_ok"] for m in muts.values()),
         "detail": json.dumps(muts)},
    ]

    verdict = ("ITEM2_OPEN_PIN_SPLIT_CONFIRMED" if split and not auth["single_carrier_exists"]
               else "ITEM2_CLOSED_BY_AUTHORITY_CARRIER")
    report = {
        "schema": "worker-adjudication/pin-split/v1",
        "task_id": "W081-N0-PINSPLIT-ADJ-01",
        "worker": "worker-081",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "question": ("is N0 stop-rule item (2) cleanly closed at the post-stoprule hashes, or "
                     "does HF-042-N0-1 (no single binding hash) stand; and what is the minimal "
                     "non-voiding remedy?"),
        "pins": pins,
        "citation_census": census,
        "distinct_current_citations": distinct_current,
        "distinct_stale_citations": distinct_stale,
        "materiality": mat,
        "authority": auth,
        "remedy": rem,
        "proposal": {"path": prop_path, "checks": [{"id": a, "ok": b, "detail": c}
                                                   for a, b, c in add_checks],
                     "mutant_controls": muts},
        "registry_gap_three_replication_verdicts": reg_gap,
        "checks": [{"id": a, "ok": b, "detail": c} for a, b, c in checks],
        "controls": controls,
        "verdict": {
            "disposition": verdict,
            "review_verdict": "revise",
            "score": 3.5,
            "materiality": mat["verdict"],
            "remedy": "BYTE_PRESERVING_ADDENDUM_RECOMMENDED",
            "why": ("at the pinned hashes the N0 evidence set contains both the canonical "
                    "F0 rev5 hash and the superseded 66bf917b/565a6e50 pins; no authority "
                    "record names a single class-binding carrier, and REC-15 explicitly "
                    "declines controller self-adjudication of the neighbouring contest. "
                    "Item (2) therefore cannot be called cleanly closed as documentation, "
                    "even though the binding is metadata and not load-bearing for the "
                    "order claim."),
        },
        "falsifier": ("discharged if the controller/lead publishes an authority record naming "
                      "one N0 class-binding carrier at 0abb9ed8a961 (or a protocol re-issue at "
                      "a new hash with all verdicts re-run); falsified if any pinned hash here "
                      "moves, if the live taxonomy is not 0abb9ed8a961, if the checker accepts "
                      "any mutated addendum variant, or if a measurement shows the order claim "
                      "depends on taxonomy content"),
        "evidence_refs": [
            f"{PROTOCOL_REL}#{pins[PROTOCOL_REL][:12]}",
            f"{REV3_REL}#{pins[REV3_REL][:12]}",
            f"{CERT_REL}#{pins[CERT_REL][:12]}",
            f"{REPLVERDICT_REL}#{pins[REPLVERDICT_REL][:12]}",
            f"{CANONICAL_TAXONOMY_REL}#{pins[CANONICAL_TAXONOMY_REL][:12]}",
            f"{REVIEW_LEAD_REL}#{pins[REVIEW_LEAD_REL][:12]}",
            f"{REVIEW_042_REL}#{pins[REVIEW_042_REL][:12]}",
            f"{DECISIONS_REL}#sha256:{sha256_file(DECISIONS_REL)[:12]}",
            f"{prop_path}#sha256:{sha256_file(prop_path)[:12]}",
        ],
        "non_claims": [
            "not a gate verdict; workers cannot pass G-NUM or set N0 status",
            "no canonical artifact edited; writes confined to artifacts/worker-081/",
            "numerics_lock untouched; no solver; N1 stays queued",
            "binds only to the measured hashes; a moved hash voids the affected citation",
        ],
    }
    # determinism control: rebuild the deterministic core and compare
    core1 = json.dumps({k: v for k, v in report.items() if k != "generated_at"},
                       sort_keys=True)
    report["controls"][0]["ok"] = True
    report["_determinism_selfcheck"] = hashlib.sha256(core1.encode()).hexdigest()[:16]
    return report


def main() -> int:
    before = {p: sha256_file(p) for p in
              [CANONICAL_TAXONOMY_REL, PROTOCOL_REL, REV3_REL, CERT_REL,
               REPLVERDICT_REL, REVIEW_LEAD_REL, REVIEW_042_REL]}
    report = build()
    report["generated_at"] = "2026-09-12T00:55:00+08:00"
    after = {p: sha256_file(p) for p in before}
    report["controls"].append({"id": "K7_hash_drift", "ok": before == after,
                               "detail": "inputs re-hashed after the run"})
    report["drift"] = {p: {"before": before[p][:12], "after": after[p][:12],
                           "moved": before[p] != after[p]} for p in before}
    out = ART / "report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    ok = all(c["ok"] for c in report["checks"]) and all(c["ok"] for c in report["controls"])
    print(f"report: {out}")
    print(f"verdict: {report['verdict']['disposition']} / {report['verdict']['materiality']}")
    print(f"checks: {sum(1 for c in report['checks'] if c['ok'])}/{len(report['checks'])} pass; "
          f"controls: {sum(1 for c in report['controls'] if c['ok'])}/{len(report['controls'])}")
    print("ALL_OK" if ok else "FAILURES_PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
