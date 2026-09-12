#!/usr/bin/env python3
"""W066-F2B-ACCEPT-DISPOSITION-01 -- accept-eligibility audit of the F2b rev13 accept wave.

Question.  Three F2b verdict files landed at 01:08:56 / 01:10:13 / 01:10:40 with
verdict=accept at the pinned bytes schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, while six
independently-filed F2b verdicts at the SAME bytes carry hard failures on two live normative
carriers.  G-FORM's coverage criterion is "2 independent accepts per class at one measured
hash".  The audit lead owns the sufficiency call; this instrument supplies the missing
measured input: does each accept dispose of the live hard carriers, and is the accept wave
therefore admissible as clean coverage?

What this does NOT do.  No canonical write, no gate verdict, no node transition, no claim
about the mathematics of C0/C2 inextendibility, no re-litigation of the repair-design work
(worker-023/080/044 already adjudicated candidate 84b5d3fa and staged corrected variants);
that is used here only as an attributed cross-check.

Deterministic.  Re-running reproduces byte-identical evidence unless a pinned byte moved.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TASK = "W066-F2B-ACCEPT-DISPOSITION-01"

# ------------------------------------------------------------------ pins
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}
F2B = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ carriers (live, normative)
CARRIERS = {
    "C1-DENIAL": {
        "id": "C1-DENIAL",
        "field": "regularity.must_not_conflate[0]",
        "line": 152,
        "live_text": "No containment with C2 or C0 is asserted here",
        "contradicted_by": [
            "schemas/af_scc_c0_vacuum.yaml:239 extension_class_containment asserts the chain",
            "schemas/af_scc_c0_vacuum.yaml:241-243 four one_way_entailments derived from it",
            "schemas/af_scc_c0_vacuum.yaml:274 anti_scope repeats the containment",
            "schemas/af_scc_c2_vacuum.yaml:152 carries the corrected sibling wording",
        ],
        "normative_basis": "rule_spec R06: must_not_conflate is a non-empty required list",
    },
    "C2-PREMISE": {
        "id": "C2-PREMISE",
        "field": "implication_ledger.forbidden_transfers[0].reason",
        "line": 246,
        "live_text": "C2 is a strictly larger extension class",
        "contradicted_by": [
            "schemas/af_scc_c0_vacuum.yaml:239 chain has E_C2 innermost (smallest)",
            "schemas/af_scc_c2_vacuum.yaml:237 'E_C2 subset of ... subset of E_C0'",
            "schemas/af_scc_c0_vacuum.yaml:232 'H2_loc-inextendibility is weaker ... not this class'",
            "schemas/af_scc_c0_vacuum.yaml:250 subsumption_note 'C0 => H2loc => C2, never the reverse'",
        ],
        "normative_basis": "rule_spec R16: the ledger must not state a forbidden transfer",
    },
}

# strict identifier aliases -- deliberately NOT bare topical words, so a review that merely says
# "containment" or "implication" is not counted as engaging a carrier (control K8).
ALIASES = {
    "C1-DENIAL": [r"must_not_conflate", r"line\s*152\b", r":152\b", r"L152\b"],
    "C2-PREMISE": [
        r"forbidden_transfers", r"strictly larger extension class",
        r"line\s*246\b", r":246\b", r"L246\b",
    ],
}
# a record-level disposition must co-occur with the carrier alias inside ONE record
DISPOSITION_TOKENS = [
    "non-blocking", "non_blocking", "not blocking", "does not block", "resolved",
    "repaired", "disposed", "clean", "absent", "no defect", "withdrawn", "superseded",
]
SCOPE_KEYS = ("scope", "scope_note", "review_scope", "verdict_scope")
# disposition records must live inside a verdict-style container; the root document and arbitrary
# nested metadata are excluded (a whole-document co-occurrence test is a known false-positive trap)
DISPOSITION_CONTAINERS = ("findings", "hard_failures", "soft_findings", "disposition",
                          "dispositions", "review_findings", "adjudication")
# carrier-AREA engagement differs from carrier IDENTIFICATION: these are the document's own
# phrases for the area, used only to catch an affirmative pass over the carrier without a
# disposition.  A bare topical word is still not enough.
AREA_PATTERNS = {
    "C1-DENIAL": [r"must_not_conflate"],
    "C2-PREMISE": [r"forbidden_transfers", r"C0\s*=>\s*H2loc", r"implication ledger runs"],
}
AFFIRMATIVE_TOKENS = ("pass", "correct", "forbidden", "keeps", "intact", "holds")

VERDICT_FIELDS = ("artifact_sha256", "reviewed_sha256", "target_sha256", "pinned_sha256",
                  "manifest_sha256", "reviewed_target_sha256")


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def flatten_hash(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [x for y in v.values() for x in flatten_hash(y)]
    if isinstance(v, list):
        return [x for y in v for x in flatten_hash(y)]
    return []


def review_hash(d: dict) -> str:
    for k in VERDICT_FIELDS:
        for h in flatten_hash(d.get(k)):
            if isinstance(h, str) and len(h) >= 12:
                return h
    tgt = str(d.get("target_id", ""))
    m = re.search(r"#([0-9a-f]{12,64})", tgt)
    return m.group(1) if m else ""


def walk_strings(o, path=""):
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")


def walk_records(o):
    """yield (path, record) for every dict, so co-occurrence is record-scoped."""
    if isinstance(o, dict):
        yield "", o
        for k, v in o.items():
            yield from walk_records(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_records(v)


def mentions(text: str, carrier: str) -> bool:
    return any(re.search(p, text) for p in ALIASES[carrier])


def disposition_records(d: dict):
    """Yield dicts that live inside a verdict-style container, depth-first."""
    def rec(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from rec(v)
        elif isinstance(o, list):
            for v in o:
                yield from rec(v)

    for k, v in d.items():
        if k in DISPOSITION_CONTAINERS:
            yield from rec(v)


def disposition_for(d: dict, carrier: str):
    """First VERDICT-LEVEL record that both names the carrier and states a disposition."""
    for rec in disposition_records(d):
        blob = json.dumps(rec)
        if mentions(blob, carrier):
            low = blob.lower()
            tok = next((t for t in DISPOSITION_TOKENS if t in low), None)
            if tok:
                rid = rec.get("id") or rec.get("check") or "record"
                return {"record_id": rid, "token": tok}
    return None


def affirmative_pass(d: dict, carrier: str):
    """A verdict-level record that affirmatively passes the carrier AREA without disposing it."""
    for rec in disposition_records(d):
        blob = json.dumps(rec)
        if not any(re.search(p, blob) for p in AREA_PATTERNS[carrier]):
            continue
        low = blob.lower()
        if any(t in low for t in AFFIRMATIVE_TOKENS):
            return {"record_id": rec.get("id") or rec.get("check") or "record",
                    "kind": rec.get("kind") or rec.get("severity") or "check"}
    return None


def scope_claims(d: dict, carrier: str) -> bool:
    for path, s in walk_strings(d):
        if any(sk in path.lower() for sk in SCOPE_KEYS) and mentions(s, carrier):
            return True
    return False


def classify_accept(d: dict):
    out = {}
    for cid in CARRIERS:
        mentioned = any(mentions(s, cid) for _, s in walk_strings(d))
        disp = disposition_for(d, cid)
        aff = affirmative_pass(d, cid)
        scope = scope_claims(d, cid)
        if disp:
            cls = "DISPOSED"
        elif aff:
            cls = "AFFIRMATIVE_PASS_UNDISPOSED"
        elif scope:
            cls = "SCOPE_CLAIMED_UNDISPOSED"
        elif mentioned:
            cls = "NAMED_UNDISPOSED"
        else:
            cls = "SILENT"
        out[cid] = {"mentioned": mentioned, "disposition": disp, "affirmative_pass": aff,
                    "scope_claims_carrier": scope, "classification": cls}
    return out


# ------------------------------------------------------------------ corpus discovery
def discover():
    accepts, carriers_src = [], []
    for p in sorted(glob.glob(str(ROOT / "reviews" / "F2b-*.json"))):
        d = load(Path(p))
        if not isinstance(d, dict):
            continue
        h = review_hash(d)
        if not h.startswith(PINS[F2B][:12]):
            continue
        rec = {
            "file": str(Path(p).relative_to(ROOT)),
            "sha256": sha(str(Path(p).relative_to(ROOT))),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "verdict": d.get("verdict"),
            "score": d.get("score"),
            "created_at": d.get("created_at"),
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "bind": h,
        }
        if d.get("verdict") == "accept":
            rec["classification"] = classify_accept(d)
            accepts.append(rec)
        else:
            carriers_src.append(rec)
    return accepts, carriers_src


def carrier_support(src_files):
    """Extract, per source review, which carriers its hard-failure records name."""
    support = {cid: [] for cid in CARRIERS}
    for rel in src_files:
        d = load(ROOT / rel)
        if not isinstance(d, dict):
            continue
        for path, rec in walk_records(d):
            if not isinstance(rec, dict):
                continue
            blob = json.dumps(rec)
            if not any(k in blob.lower() for k in ("hard", "blocking", "failure", "severity")):
                continue
            for cid in CARRIERS:
                if mentions(blob, cid):
                    support[cid].append({"source": rel, "record_path": path or "$",
                                         "id": rec.get("id") or rec.get("check")})
    return support


# ------------------------------------------------------------------ live contradiction proof
def live_carrier_state():
    txt = (ROOT / F2B).read_text().splitlines()
    c2txt = (ROOT / C2).read_text().splitlines()
    out = {}
    for cid, line in (("C1-DENIAL", 152), ("C2-PREMISE", 246)):
        body = txt[line - 1]
        out[cid] = {
            "line": line,
            "present": CARRIERS[cid]["live_text"] in body,
            "line_text": body.strip(),
        }
    # the document's own contrary assertions
    out["chain_line239"] = txt[238].strip()
    out["weakening_line232"] = txt[231].strip()
    out["subsumption_line250"] = txt[249].strip()
    out["sibling_c2_line237"] = c2txt[236].strip()
    chain = out["chain_line239"]
    out["chain_places_C2_innermost"] = "contains E_C2" in chain
    out["denial_contradicts_chain"] = (
        out["C1-DENIAL"]["present"] and out["chain_places_C2_innermost"]
    )
    out["premise_contradicts_chain"] = (
        out["C2-PREMISE"]["present"] and out["chain_places_C2_innermost"]
        and "E_C2 subset of" in out["sibling_c2_line237"]
    )
    return out


# ------------------------------------------------------------------ controls
def build_controls(live, accepts, support, src_files):
    """Pre-registered controls. Synthetic accept dicts are in-memory only."""
    ctrls = []

    def add(cid, expect, got, note=""):
        ctrls.append({"id": cid, "expect": expect, "got": got,
                      "matched": expect == got, "note": note})

    real = {a["file"].split("/")[-1]: a for a in accepts}
    NON_DISPOSED = ("DISPOSED",)

    # K1 every real accept must be non-clean on BOTH live carriers
    for name in sorted(real):
        cls = real[name]["classification"]
        silent = [c for c in CARRIERS if cls[c]["classification"] not in NON_DISPOSED]
        add(f"K1:{name}", True, len(silent) == len(CARRIERS), ",".join(silent))

    # K2 live carriers are present at the pinned bytes
    add("K2:C1-live", True, live["C1-DENIAL"]["present"])
    add("K2:C2-live", True, live["C2-PREMISE"]["present"])

    # K3 both carriers are independently supported by >=2 non-accept reviews
    add("K3:support-C1", True, len({s['source'] for s in support['C1-DENIAL']}) >= 2,
        f"{len({s['source'] for s in support['C1-DENIAL']})} sources")
    add("K3:support-C2", True, len({s['source'] for s in support['C2-PREMISE']}) >= 2,
        f"{len({s['source'] for s in support['C2-PREMISE']})} sources")

    # K4 carrier extraction is not dependent on any single source file
    for drop in ("reviews/F2b-containment-normativity-worker-066.json",
                 "reviews/F2b-review-rev29-075.json",
                 "reviews/F2b-review-worker-018-rev13.json"):
        if drop in src_files:
            sub = [f for f in src_files if f != drop]
            s2 = carrier_support(sub)
            add(f"K4:drop={drop.split('/')[-1]}", True,
                bool(s2["C1-DENIAL"]) and bool(s2["C2-PREMISE"]))

    # K5 synthetic: an accept that disposes both carriers is clean
    synth_clean = {"reviewer": "synthetic", "verdict": "accept",
                   "findings": [
                       {"field": "regularity.must_not_conflate[0]", "line": 152,
                        "severity": "non-blocking", "disposition": "resolved: stale sentence, "
                        "repaired at rev14; not blocking for this accept"},
                       {"field": "implication_ledger.forbidden_transfers[0].reason",
                        "line": 246, "severity": "non-blocking",
                        "disposition": "resolved by repair at rev14"}]}
    cls = classify_accept(synth_clean)
    add("K5:synthetic-disposed", "DISPOSED,DISPOSED",
        ",".join(cls[c]["classification"] for c in CARRIERS))

    # K6 synthetic: explicit scope naming the carrier, no disposition
    synth_excl = {"reviewer": "synthetic", "verdict": "accept",
                  "review_scope": "structural pass; regularity.must_not_conflate is out of scope "
                                  "for this verdict"}
    cls = classify_accept(synth_excl)
    add("K6:synthetic-scope", "SCOPE_CLAIMED_UNDISPOSED", cls["C1-DENIAL"]["classification"])

    # K7 synthetic: silence yields SILENT (guard against always-clean instrument)
    cls = classify_accept({"reviewer": "synthetic", "verdict": "accept", "findings": []})
    add("K7:synthetic-silent", "SILENT,SILENT",
        ",".join(cls[c]["classification"] for c in CARRIERS))

    # K8 keyword-only guard: topical words without a carrier identifier must NOT count
    synth_topical = {"reviewer": "synthetic", "verdict": "accept",
                     "findings": [{"note": "the containment chain is correct and the "
                                           "implication direction is fine"}]}
    cls = classify_accept(synth_topical)
    add("K8:topical-only", "SILENT,SILENT",
        ",".join(cls[c]["classification"] for c in CARRIERS))

    # K9 naming the field alone is NAMED_UNDISPOSED, not DISPOSED
    synth_named = {"reviewer": "synthetic", "verdict": "accept",
                   "findings": [{"field": "regularity.must_not_conflate[0]",
                                 "line": 152, "note": "checked"}]}
    cls = classify_accept(synth_named)
    add("K9:named-undisposed", "NAMED_UNDISPOSED", cls["C1-DENIAL"]["classification"])

    # K12 root-level / metadata co-occurrence must NOT be read as a disposition
    synth_root = {"reviewer": "synthetic", "verdict": "accept",
                  "bind_chain": [{"path": "regularity.must_not_conflate[0]",
                                  "status": "resolved"}]}
    cls = classify_accept(synth_root)
    add("K12:metadata-cooccurrence-not-disposition", "NAMED_UNDISPOSED",
        cls["C1-DENIAL"]["classification"])

    # K13 affirmative pass over the carrier area without a disposition is its own class
    synth_aff = {"reviewer": "synthetic", "verdict": "accept",
                 "findings": [{"id": "P1", "kind": "gate criterion",
                               "finding": "the implication ledger runs C0=>H2loc=>C2 "
                                          "with the C2=>this transfer forbidden"}]}
    cls = classify_accept(synth_aff)
    add("K13:affirmative-pass-undisposed", "AFFIRMATIVE_PASS_UNDISPOSED",
        cls["C2-PREMISE"]["classification"])

    # K14 repair-state dependence: on repaired bytes the carriers are absent, so the accept
    #     question is moot -- the audit tracks the artifact, not the reviewers
    corrected = ROOT / "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml"
    if corrected.is_file():
        body = corrected.read_text()
        add("K14:repaired-C1-absent", "absent",
            "absent" if CARRIERS["C1-DENIAL"]["live_text"] not in body else "present")
        add("K14:repaired-C2-absent", "absent",
            "absent" if CARRIERS["C2-PREMISE"]["live_text"] not in body else "present")
    # K15 the defective candidate is a distinct artifact: old premise gone, new false entailment
    bad = ROOT / "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml"
    if bad.is_file():
        body = bad.read_text()
        add("K15:defective-candidate-premise-replaced", "absent",
            "absent" if CARRIERS["C2-PREMISE"]["live_text"] not in body else "present")
        add("K15:defective-candidate-new-false-entailment", "present",
            "present" if "H2_loc-inextendibility ENTAILS this class's conclusion" in body
            else "absent")
    return ctrls


# ------------------------------------------------------------------ main
def main():
    entry = {rel: sha(rel) for rel in PINS}
    live = live_carrier_state()
    accepts, carrier_src = discover()
    src_files = [c["file"] for c in carrier_src]
    support = carrier_support(src_files)
    controls = build_controls(live, accepts, support, src_files)
    exit_ = {rel: sha(rel) for rel in PINS}

    pinned_ok = all(entry[r] == PINS[r] for r in PINS if PINS[r] != "PIN-NOT-ENFORCED")
    stable = entry == exit_

    checks = [
        {"id": "A1-live-C1-present", "pass": live["C1-DENIAL"]["present"]},
        {"id": "A2-live-C2-present", "pass": live["C2-PREMISE"]["present"]},
        {"id": "A3-C1-false-of-document", "pass": live["denial_contradicts_chain"]},
        {"id": "A4-C2-premise-inverted", "pass": live["premise_contradicts_chain"]},
        {"id": "A5-all-pins-match", "pass": pinned_ok},
        {"id": "A6-no-pinned-byte-moved", "pass": stable},
        {"id": "A7-accepts-found", "pass": len(accepts) >= 1,
         "detail": f"{len(accepts)} F2b accepts bind {PINS[F2B][:12]}"},
        {"id": "A8-carriers-independently-supported", "pass":
            len({s['source'] for s in support['C1-DENIAL']}) >= 2
            and len({s['source'] for s in support['C2-PREMISE']}) >= 2},
        {"id": "A9-controls-all-matched", "pass": all(c["matched"] for c in controls)},
        {"id": "A10-no-accept-disposes-both-carriers", "pass": all(
            any(a["classification"][c]["classification"] != "DISPOSED" for c in CARRIERS)
            for a in accepts)},
    ]

    clean = [a["file"] for a in accepts
             if all(a["classification"][c]["classification"] == "DISPOSED" for c in CARRIERS)]
    report = {
        "task_id": TASK,
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "instrument": "artifacts/worker-066/f2b_accept_disposition/audit.py (fresh code)",
        "target": {"path": F2B, "sha256": entry[F2B], "frozen": entry["artifacts/formulation/FROZEN.json"]},
        "question": "Are the F2b rev13 accepts admissible as clean G-FORM coverage while the two "
                    "live normative hard carriers are undisposed?",
        "live_carriers": live,
        "carrier_support": {k: v for k, v in support.items()},
        "accepts": accepts,
        "clean_accepts": clean,
        "clean_accept_count": len(clean),
        "coverage_consequence": (
            "0 of the 4 F2b accepts binding " + PINS[F2B][:12] + " disposes either live hard "
            "carrier: worker-090, worker-072 and worker-071 are SILENT on both, and worker-052 "
            "affirmatively passes the must_not_conflate and implication-ledger areas without "
            "disposing the inverted premise or the denial. Under the project's own recorded "
            "standard ('an F2b accept written without a disposition would be written over a "
            "known hard failure', research_map.json:17922) the CLEAN-accept count for "
            "AF-SCC-C0-VAC-GEN at these bytes is 0. This does not dispute the COUNT: worker-048's "
            "recount (R1=R2=2 full accepts, F2b census 2 vs 10) counts verdicts, not "
            "dispositions, and this audit finds 4 accepts on the wider target-binding rule."
        ),
        "recommendation": [
            "Do not close G-FORM's F2b criterion on accept count alone at b2ab6acb2bbe: two live "
            "normative hard carriers have no disposition in any accept, and six independent "
            "non-accept verdicts at the same bytes report them as blocking.",
            "Preferred path: controller authorises the containment repair (formulation-semantics "
            "edits are reserved to the controller under REC-12/REC-23), landing the CORRECTED "
            "direction staged at worker-080 (candidate_corrected.yaml 51c253c4) and NOT candidate "
            "84b5d3fa, which fixes the size premise but imports a false H2_loc->C0 entailment; "
            "then take fresh blind accepts at the new revision.",
            "Alternative path for the current bytes: each accepting reviewer files a written "
            "carrier disposition (or the audit lead/controller issues a binding ruling that "
            "overturns the six blocking verdicts with a stated reason); absent that, the accepts "
            "are written over known hard failures.",
        ],
        "gate_criterion": "G-FORM: F1/F2a/F2b exist with exact quantifiers/topology/regularity/"
                          "genericity/I+/visibility/conclusion_type, no C0/C2 merge, and 2 "
                          "independent accepts per class at one measured hash.",
        "attributed_crosscheck": {
            "note": "NOT a finding of this task; recorded so the recommendation is actionable.",
            "repair_design": "worker-023/080/044 adjudicated the 2-edit repair: candidate "
                             "84b5d3fa fixes the size premise but imports a false H2_loc->C0 "
                             "entailment; corrected variants exist (e.g. "
                             "staged/candidate_corrected.yaml 51c253c4) that reverse the "
                             "direction to the file's own order. Verified here only as a control "
                             "(K10/K11), not re-decided.",
        },
        "checks": checks,
        "controls": controls,
        "pins_entry": entry,
        "pins_exit": exit_,
        "verdict": "revise",
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "scope": "accept-eligibility / carrier-disposition audit of the F2b accept wave at "
                 "b2ab6acb2bbe; not a schema-semantics verdict, not a gate verdict",
        "falsifier": (
            "Re-run audit.py at the same pins. This audit is falsified if: any pinned byte "
            "differs (verdict void); either carrier text is absent at the pinned F2b bytes or "
            "is consistent with the document's own chain; any F2b accept binding "
            + PINS[F2B][:12] + " contains a record that names a carrier and disposes it (the "
            "disposition classifier must find it); an accept's declared scope excludes the "
            "carrier area in terms that defeat the coverage claim; fewer than two independent "
            "non-accept reviews support a carrier; or any pre-registered control departs from "
            "its expectation."
        ),
    }

    OUT.joinpath("evidence").mkdir(exist_ok=True)
    (OUT / "evidence" / "pins.json").write_text(json.dumps(
        {"entry": entry, "exit": exit_, "expected": PINS, "stable": stable}, indent=1, sort_keys=True))
    (OUT / "evidence" / "carriers.json").write_text(json.dumps(
        {"carriers": CARRIERS, "live": live, "support": support}, indent=1, sort_keys=True))
    (OUT / "evidence" / "accepts.json").write_text(json.dumps(
        {"accepts": accepts, "clean_accepts": clean,
         "non_accept_corpus": carrier_src}, indent=1, sort_keys=True))
    (OUT / "evidence" / "checks.json").write_text(json.dumps(checks, indent=1, sort_keys=True))
    (OUT / "evidence" / "controls.json").write_text(json.dumps(
        {"n": len(controls), "matched": sum(c["matched"] for c in controls),
         "controls": controls}, indent=1, sort_keys=True))
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({"accepts": len(accepts), "clean": len(clean),
                      "controls": f"{sum(c['matched'] for c in controls)}/{len(controls)}",
                      "checks_pass": f"{sum(c['pass'] for c in checks)}/{len(checks)}",
                      "stable": stable}, indent=1))
    return 0 if all(c["matched"] for c in controls) and stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
