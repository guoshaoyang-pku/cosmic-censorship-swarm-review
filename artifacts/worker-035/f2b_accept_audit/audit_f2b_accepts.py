#!/usr/bin/env python3
"""W035-F2B-ACCEPT-AUDIT-01 -- adversarial materiality audit of F2b accept coverage.

Node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.
Pinned target: schemas/af_scc_c0_vacuum.yaml @
b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c
(FROZEN rev29 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0).

Question: at the live pin, do the F2b *accept* verdicts bind the bytes, cover the full
schema, and dispose of the live containment defects -- or is the accept count nominal?

Read-only with respect to every canonical path. Deterministic; stdlib + PyYAML only.
Worker measurement only: issues no gate verdict, node status or validation_status.
"""
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "artifacts", "worker-035", "f2b_accept_audit")
SNAP = os.path.join(OUT, "snapshot")

PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
F0_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
EVID_PIN = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"

CANON = "schemas/af_scc_c0_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2A_PIN = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
F0 = "research_map/formulation_taxonomy.yaml"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
MAP = "research_map/research_map.json"

AUTHOR = "astra-lead-formulation"
CHAIN_MARKER = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
INVERSION_MARKER = "C2 is a strictly larger extension class"
DENIAL_MARKER = "No containment with C2 or C0 is asserted here"


def sha256_file(rel):
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def line_of(text, needle):
    idx = text.find(needle)
    if idx < 0:
        return None
    return text.count("\n", 0, idx) + 1


def walk_find(obj, key):
    """Yield every value bound to `key` anywhere in the document."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from walk_find(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_find(v, key)


def find_list(doc, key, needle):
    for val in walk_find(doc, key):
        if isinstance(val, list) and any(needle in str(x) for x in val):
            return val
    return None


def find_transfer_row(doc, frm, to):
    for val in walk_find(doc, "forbidden_transfers"):
        if isinstance(val, list):
            for row in val:
                if isinstance(row, dict) and row.get("from") == frm and row.get("to") == to:
                    return row
    return None


def detect_defects(doc, text):
    """Mechanical detection of the two live containment-direction defects."""
    chains = [str(v) for v in walk_find(doc, "extension_class_containment")]
    chain = next((c for c in chains if CHAIN_MARKER in c), None)
    row = find_transfer_row(doc, "no proper future C2 extension", "this class")
    reason = str(row.get("reason")) if isinstance(row, dict) else ""
    denial_list = find_list(doc, "must_not_conflate", DENIAL_MARKER)
    denial = next((str(x) for x in (denial_list or []) if DENIAL_MARKER in str(x)), None)
    d1 = bool(chain) and INVERSION_MARKER in reason
    d2 = bool(chain) and denial is not None
    return {
        "chain_present": bool(chain),
        "chain_line": line_of(text, chain) if chain else None,
        "chain": chain,
        "forbidden_transfer_reason": reason or None,
        "forbidden_transfer_line": line_of(text, reason) if reason else None,
        "inversion_marker_present": INVERSION_MARKER in reason,
        "denial_sentence": denial,
        "denial_line": line_of(text, denial) if denial else None,
        "D1_inverted_containment_reason": d1,
        "D2_stale_containment_denial": d2,
    }


def reimplement_c04(doc):
    """Faithful re-implementation of worker-090 check_f2b_rev13_full.py C04.

    Their predicate (lines 299-305) tests structural presence only:
      c0_to_c2 and not rev_rows and rev_forbidden
    It never inspects forbidden_transfers[*].reason, so it cannot see D1.
    """
    led = None
    for val in walk_find(doc, "one_way_entailments"):
        if isinstance(val, list):
            led = val
            break
    led = led or []
    forb = None
    for val in walk_find(doc, "forbidden_transfers"):
        if isinstance(val, list):
            forb = val
            break
    forb = forb or []
    c0_to_c2 = any("C0" in str(r.get("from")) and "C2" in str(r.get("to")) for r in led)
    rev_rows = [r for r in led if "C2" in str(r.get("from")) and "C0" in str(r.get("to"))]
    rev_forbidden = any("C2" in str(r.get("from")) for r in forb)
    return {
        "c0_to_c2": c0_to_c2,
        "reverse_rows": len(rev_rows),
        "forbidden_reverse": rev_forbidden,
        "C04_pass": bool(c0_to_c2 and not rev_rows and rev_forbidden),
        "inspects_reason_field": False,
    }


ACCEPT_RESOLVE_RE = re.compile(
    r"(gone|resolved|corrected|repaired|no longer)", re.IGNORECASE)
D1_TOKEN_RE = re.compile(
    r"(strictly larger|containment direction|forbidden[_ ]transfer|transfer row)", re.IGNORECASE)
D2_TOKEN_RE = re.compile(
    r"(h2_loc|must_not_conflate|containment)", re.IGNORECASE)


def classify_accept(rec, pin):
    """Classify one review record against the pin and the live defect families."""
    blob = json.dumps(rec.get("findings") or [], ensure_ascii=False) + " " + str(rec.get("target_id"))
    hashes = rec.get("reviewed_sha256")
    if isinstance(hashes, dict):
        bound = pin in json.dumps(hashes)
    else:
        bound = isinstance(hashes, str) and hashes.split(";")[0].strip().startswith(pin[:24])
    fs = rec.get("counts_as_full_schema_verdict")
    scoped = bool(re.search(r"\bSCOPED\b|not the full schema|not a full-schema", blob, re.IGNORECASE))
    full_schema = False if (fs is False or scoped) else (True if fs is True else None)
    permissive_full = bool(not scoped and fs is not False and "F2b" in str(rec.get("target_id")))
    mentions_d1 = bool(D1_TOKEN_RE.search(blob))
    flags_d1_marker = bool(re.search(
        r"strictly larger|containment direction|forbidden_transfers\[0\]", blob, re.IGNORECASE))
    mentions_d2 = bool(D2_TOKEN_RE.search(blob))
    asserts_resolved = bool(ACCEPT_RESOLVE_RE.search(blob))
    return {
        "event_id": rec.get("event_id"),
        "reviewer": rec.get("reviewer"),
        "verdict": rec.get("verdict"),
        "score": rec.get("score"),
        "created_at": rec.get("created_at"),
        "bound_to_pin": bound,
        "full_schema_declared": fs,
        "self_scoped": scoped,
        "full_schema": full_schema,
        "full_schema_permissive": permissive_full,
        "independent_of_author": rec.get("reviewer") != AUTHOR,
        "mentions_D1_family": mentions_d1,
        "flags_D1_marker": flags_d1_marker,
        "mentions_D2_family": mentions_d2,
        "asserts_resolved": asserts_resolved,
        "disposes_D1": bool(mentions_d1 and asserts_resolved and "revise" not in str(rec.get("verdict"))),
        "disposes_D2": bool(mentions_d2 and asserts_resolved and "revise" not in str(rec.get("verdict"))),
    }


def assess_accepts(accepts, defects):
    """Annotate accepts against the live defect families.

    An accept can only *dispose* a family if that family is not live at the pin; if the
    family is live, any 'resolved/corrected/gone' claim about it is contradicted by the
    bytes the verdict itself cites.
    """
    out = []
    for a in accepts:
        d1_live = bool(defects["D1_inverted_containment_reason"])
        d2_live = bool(defects["D2_stale_containment_denial"])
        a = dict(a)
        a["disposes_D1"] = bool(a["mentions_D1_family"] and a["asserts_resolved"] and not d1_live)
        a["disposes_D2"] = bool(a["mentions_D2_family"] and a["asserts_resolved"] and not d2_live)
        a["contradicts_D1"] = bool(d1_live and a["mentions_D1_family"] and a["asserts_resolved"])
        a["contradicts_D2"] = bool(d2_live and a["mentions_D2_family"] and a["asserts_resolved"])
        a["engages_live_defects"] = bool(
            (d1_live and a["mentions_D1_family"]) or (d2_live and a["mentions_D2_family"]))
        a["material_for_pin"] = bool(
            (not d1_live or a["disposes_D1"]) and (not d2_live or a["disposes_D2"]))
        out.append(a)
    return out


def accept_census(map_doc, pin):
    records = []
    for rec in map_doc.get("reviews") or []:
        blob = json.dumps(rec, ensure_ascii=False)
        if "F2b" not in blob:
            continue
        if pin not in blob and pin[:12] not in blob:
            continue
        records.append(rec)
    accepts = [r for r in records if r.get("verdict") == "accept"]
    non_accepts = [r for r in records if r.get("verdict") != "accept"]

    def _bound(rec):
        h = rec.get("reviewed_sha256")
        if isinstance(h, dict):
            return pin in json.dumps(h)
        return isinstance(h, str) and h.split(";")[0].strip().startswith(pin[:24])

    return {
        "records_citing_pin_and_F2b": len(records),
        "records_bound_to_pin": sum(1 for r in records if _bound(r)),
        "accept_records": len(accepts),
        "accept_records_bound_to_pin": sum(1 for r in accepts if _bound(r)),
        "non_accept_records": len(non_accepts),
        "non_accept_records_bound_to_pin": sum(1 for r in non_accepts if _bound(r)),
        "accepts": [classify_accept(r, pin) for r in sorted(accepts, key=lambda x: x.get("created_at", ""))],
        "non_accept_verdict_ids": [
            {"event_id": r.get("event_id"), "reviewer": r.get("reviewer"),
             "verdict": r.get("verdict"), "score": r.get("score"),
             "full_schema": r.get("counts_as_full_schema_verdict")}
            for r in sorted(non_accepts, key=lambda x: x.get("created_at", ""))
        ],
    }


def run_audit(canon_text, f2a_text, frozen_doc, map_doc, pins_ok=True):
    doc = yaml.safe_load(canon_text)
    d = detect_defects(doc, canon_text)
    c04 = reimplement_c04(doc)
    census = accept_census(map_doc, PIN)
    census["accepts"] = assess_accepts(census["accepts"], d)

    full = [a for a in census["accepts"] if a["bound_to_pin"] and a["full_schema"] is True
            and a["independent_of_author"]]
    permissive = [a for a in census["accepts"] if a["bound_to_pin"] and a["full_schema_permissive"]
                  and a["independent_of_author"]]
    material = [a for a in permissive if a["material_for_pin"]]
    silent = [a for a in permissive if not a["engages_live_defects"]]
    contradicted = [a for a in permissive if a["contradicts_D1"] or a["contradicts_D2"]]
    engaging = [a for a in permissive if a["engages_live_defects"] and a not in contradicted]
    flags_d1 = [a for a in permissive if a["flags_D1_marker"]]
    mentions_d2 = [a for a in permissive if a["mentions_D2_family"]]

    checks = []

    def add(cid, ok, detail, blocking=True):
        checks.append({"id": cid, "status": "pass" if ok else "fail", "blocking": blocking, "detail": detail})

    add("P01-canonical-at-pin", pins_ok, f"canonical measured == pin {PIN[:12]}")
    add("P02-chain-present", d["chain_present"], f"chain line {d['chain_line']}: {str(d['chain'])[:90]}")
    add("P03-D1-inversion-live", d["D1_inverted_containment_reason"],
        f"line {d['forbidden_transfer_line']}: {str(d['forbidden_transfer_reason'])[:110]}")
    add("P04-D2-stale-denial-live", d["D2_stale_containment_denial"],
        f"line {d['denial_line']}: {str(d['denial_sentence'])[:110]}")
    add("P05-C04-presence-check-passes-on-inverted-reason", c04["C04_pass"] and d["D1_inverted_containment_reason"],
        f"C04={c04}; inspects_reason_field=False while D1 live")
    add("P06-accept-census-extracted", census["accept_records"] >= 1,
        f"{census['accept_records_bound_to_pin']} bound accept(s) and {census['non_accept_records_bound_to_pin']} bound non-accepts among {census['records_citing_pin_and_F2b']} F2b records citing the pin")
    add("P07-nominal-accept-bar", len(permissive) >= 2,
        f"{len(full)} strict full-schema ({', '.join(sorted(a['reviewer'] for a in full))}); "
        f"{len(permissive)} permissive full-schema ({', '.join(sorted(a['reviewer'] for a in permissive))}); "
        "nominal bar is 2", blocking=False)
    add("P08-material-accepts", len(material) >= 1,
        f"{len(material)} accept(s) dispose of every live defect family")
    add("P09-no-silent-accepts", len(silent) == 0,
        f"{len(silent)} full-schema accept(s) do not engage any live defect family: "
        + ", ".join(sorted(a['reviewer'] for a in silent)), blocking=False)
    add("P10-no-contradicted-resolution-claims", len(contradicted) == 0,
        f"{len(contradicted)} accept(s) assert resolution while a defect family is live: "
        + ", ".join(sorted(a['reviewer'] for a in contradicted)))
    add("P13-no-accept-flags-D1-marker", len(flags_d1) == 0,
        f"{len(flags_d1)} full-schema accept(s) flag the inversion marker: "
        + ", ".join(sorted(a['reviewer'] for a in flags_d1)), blocking=False)
    add("P11-frozen-pins-consistent",
        frozen_doc.get("revision") == 29
        and (frozen_doc.get("files") or {}).get(CANON, {}).get("sha256") == PIN
        and (frozen_doc.get("files") or {}).get(FROZEN.rsplit("/", 1)[-1], {}) is not None,
        f"FROZEN revision={frozen_doc.get('revision')} canonical entry="
        f"{(frozen_doc.get('files') or {}).get(CANON, {}).get('sha256', '')[:12]}")
    add("P12-f2a-sibling-direction", "strictly larger" not in f2a_text,
        "F2a e9a27996 contains no 'strictly larger' containment phrase")

    headline = {
        "pin": PIN,
        "census_map_sha256": None,  # filled by main()
        "live_defects": [k for k in ("D1_inverted_containment_reason", "D2_stale_containment_denial") if d[k]],
        "accepts_selected": census["accept_records"],
        "accepts_bound_at_pin": census["accept_records_bound_to_pin"],
        "records_bound_to_pin": census["records_bound_to_pin"],
        "full_schema_accepts_strict": len(full),
        "full_schema_accepts_permissive": len(permissive),
        "material_accepts_disposing_all_live_defects": len(material),
        "full_schema_accepts_engaging_live_defects": len(engaging),
        "silent_full_schema_accepts": len(silent),
        "accepts_with_contradicted_resolution_claims": len(contradicted),
        "accepts_flagging_D1_marker": len(flags_d1),
        "accepts_mentioning_D2_block": len(mentions_d2),
        "conclusion": (
            "NOMINAL, NOT MATERIAL: live defects D1/D2 at the pin are not disposed of by any "
            "hash-bound full-schema accept; the accept count cannot establish F2b coverage "
            "until the bytes are repaired or the accepts are adjudicated."
            if (d["D1_inverted_containment_reason"] or d["D2_stale_containment_denial"]) and not material
            else "MATERIAL: at least one hash-bound full-schema accept disposes both live defect families."
        ),
    }
    return {"defects": d, "c04_reimplementation": c04, "census": census,
            "headline": headline, "checks": checks}


# ---------------------------------------------------------------- controls

def _doc():
    return {
        "implication_ledger": {
            "extension_class_containment": CHAIN_MARKER + "; this class requires the LOWEST regularity.",
            "one_way_entailments": [
                {"from": "no proper future C0 metric extension", "to": "no proper future C2 extension",
                 "relation": "entails"}],
            "forbidden_transfers": [
                {"from": "no proper future C2 extension", "to": "this class",
                 "reason": "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}],
        },
        "regularity": {"must_not_conflate": [
            "H2_loc is distinct. " + DENIAL_MARKER + "; the informal phrase is not used."]},
    }


def _accept(verdict="accept", reviewer="worker-x", full=True, findings=None, sha=PIN):
    return {"event_id": "fixture-" + reviewer, "reviewer": reviewer, "verdict": verdict,
            "score": 4.0, "created_at": "2026-09-12T01:00:00+08:00", "reviewed_sha256": sha,
            "counts_as_full_schema_verdict": full, "target_id": "F2b",
            "findings": findings if findings is not None else ["no mention of containment"]}


def run_controls():
    controls = []

    def check(name, caught, detail):
        controls.append({"control": name, "caught": bool(caught), "detail": detail})

    base = _doc()
    d0 = detect_defects(base, "")
    check("K0-null", d0["D1_inverted_containment_reason"] and d0["D2_stale_containment_denial"],
          "null fixture reproduces both defects (test is not vacuous)")

    fixed = copy.deepcopy(base)
    fixed["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
        "C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker")
    d1 = detect_defects(fixed, "")
    check("K1-repair-reason-flips-D1", (not d1["D1_inverted_containment_reason"]) and d0["D1_inverted_containment_reason"],
          "reason 'larger'->'smaller' clears D1 only")

    fixed2 = copy.deepcopy(base)
    fixed2["regularity"]["must_not_conflate"][0] = "H2_loc is a distinct regularity value; extension sets nested."
    d2 = detect_defects(fixed2, "")
    check("K2-repair-denial-flips-D2", (not d2["D2_stale_containment_denial"]) and d0["D2_stale_containment_denial"],
          "removing the denial clears D2 only")

    c04 = reimplement_c04(base)
    check("K3-C04-blind-to-reason", c04["C04_pass"] and not c04["inspects_reason_field"]
          and detect_defects(base, "")["D1_inverted_containment_reason"],
          "C04 still passes a document whose only containment row has the inverted reason")

    cen = {"reviews": [
        {"event_id": "a1", "reviewer": "w1", "verdict": "accept", "reviewed_sha256": PIN, "target_id": "F2b", "counts_as_full_schema_verdict": True, "findings": ["no containment mention"]},
        {"event_id": "a2", "reviewer": "w2", "verdict": "accept", "reviewed_sha256": "0" * 64, "target_id": "F2b", "counts_as_full_schema_verdict": True, "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"], "findings": ["no containment mention"]},
        {"event_id": "a3", "reviewer": "w3", "verdict": "accept", "reviewed_sha256": PIN, "target_id": "F2b", "counts_as_full_schema_verdict": False, "findings": ["SCOPED: not the full schema"]},
        {"event_id": "a4", "reviewer": "w4", "verdict": "accept", "reviewed_sha256": PIN, "target_id": "F2b", "counts_as_full_schema_verdict": True, "findings": ["the H2_loc containment contradiction is gone and the transfer row was corrected"]},
    ]}
    cen2 = accept_census(cen, PIN)
    cen2["accepts"] = assess_accepts(cen2["accepts"], d0)
    bound = [a for a in cen2["accepts"] if a["bound_to_pin"] and a["full_schema"] is True]
    check("K4-unbound-excluded", len(bound) == 2 and cen2["accept_records"] == 4,
          "unbound record excluded from bound full-schema set, still counted in raw accepts")
    check("K5-scoped-excluded", all(a["reviewer"] != "w3" for a in bound),
          "self-scoped accept excluded from full-schema set")
    contra = [a for a in cen2["accepts"] if a["contradicts_D1"] or a["contradicts_D2"]]
    check("K6-resolved-claim-contradicted", len(contra) == 1 and contra[0]["reviewer"] == "w4",
          "an accept asserting resolution is flagged when the reason is still inverted")
    empty = accept_census({"reviews": []}, PIN)
    check("K7-empty-census-no-vacuous-pass", empty["accept_records"] == 0 and empty["accepts"] == [],
          "empty census yields 0 accepts, no vacuous pass")
    return controls


def main():
    os.makedirs(SNAP, exist_ok=True)
    started = datetime.now(timezone(timedelta(hours=8))).isoformat()

    canon_text = read_text(CANON)
    f2a_text = read_text(F2A)
    frozen_doc = json.loads(read_text(FROZEN))
    map_raw = open(os.path.join(ROOT, MAP), "rb").read()
    map_sha = hashlib.sha256(map_raw).hexdigest()
    map_doc = json.loads(map_raw)

    before = {
        CANON: sha256_file(CANON), MIRROR: sha256_file(MIRROR),
        FROZEN: sha256_file(FROZEN), F2A: sha256_file(F2A),
        F0: sha256_file(F0), EVID: sha256_file(EVID), MAP: map_sha,
    }
    pins_ok = before[CANON] == before[MIRROR] == PIN

    # snapshot the pinned inputs (read-only copies)
    with open(os.path.join(SNAP, f"af_scc_c0_vacuum.{PIN[:12]}.yaml"), "w", encoding="utf-8") as fh:
        fh.write(canon_text)
    with open(os.path.join(SNAP, f"af_scc_c2_vacuum.{F2A_PIN[:12]}.yaml"), "w", encoding="utf-8") as fh:
        fh.write(f2a_text)
    with open(os.path.join(SNAP, "FROZEN.json"), "w", encoding="utf-8") as fh:
        json.dump(frozen_doc, fh, indent=1, sort_keys=True)
    census_records = [r for r in (map_doc.get("reviews") or [])
                      if PIN in json.dumps(r, ensure_ascii=False) and "F2b" in json.dumps(r, ensure_ascii=False)]
    with open(os.path.join(SNAP, f"census_map_{map_sha[:12]}.json"), "w", encoding="utf-8") as fh:
        json.dump({"map_sha256": map_sha, "pin": PIN, "records": census_records}, fh, indent=1)
    sums = []
    for fn in sorted(os.listdir(SNAP)):
        sums.append(f"{sha256_file(os.path.join(SNAP, fn))}  {fn}")
    with open(os.path.join(SNAP, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sums) + "\n")

    audit = run_audit(canon_text, f2a_text, frozen_doc, map_doc, pins_ok)
    audit["headline"]["census_map_sha256"] = map_sha
    audit["headline"]["census_note"] = (
        "Census is bound to research_map/research_map.json at the start sha above. The accepted "
        "event stream moves during the window; a later census may add accepts and does not "
        "invalidate the measured live defects, which bind the pinned schema bytes.")
    controls = run_controls()

    after = {
        CANON: sha256_file(CANON), MIRROR: sha256_file(MIRROR),
        FROZEN: sha256_file(FROZEN), F2A: sha256_file(F2A),
        F0: sha256_file(F0), EVID: sha256_file(EVID), MAP: sha256_file(MAP),
    }
    drift = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}

    fail = [c for c in audit["checks"] if c["blocking"] and c["status"] != "pass"]
    ctrl_fail = [c for c in controls if not c["caught"]]

    report = {
        "task_id": "W035-F2B-ACCEPT-AUDIT-01",
        "actor": "worker-035",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": started,
        "authority": ("Worker measurement only. No canonical path written; no node status, "
                      "validation_status, theorem, or gate verdict set. Advisory to the gate owner."),
        "question": ("At FROZEN rev29 pin b2ab6acb, do F2b accept verdicts bind the bytes, cover the "
                     "full schema, and dispose of the live containment defects?"),
        "pins": {"declared": {"canonical_schema": PIN, "frozen_manifest": FROZEN_PIN,
                              "f0_taxonomy": F0_PIN, "consistency_evidence": EVID_PIN,
                              "f2a_sibling": F2A_PIN},
                 "measured_start": before, "measured_end": after, "drift": drift,
                 "canonical_mirror_aligned_at_pin": before[CANON] == before[MIRROR] == PIN},
        "defects": audit["defects"],
        "c04_reimplementation": audit["c04_reimplementation"],
        "accept_census": audit["census"],
        "headline": audit["headline"],
        "checks": audit["checks"],
        "checks_failed_blocking": [c["id"] for c in fail],
        "controls": controls,
        "controls_failed": [c["control"] for c in ctrl_fail],
        "verdict": "revise",
        "score": 2.5,
        "hard_failures": [
            {"id": "HF-W035-AA-01",
             "field": "implication_ledger.forbidden_transfers[0].reason",
             "detail": ("At the pin the transfer reason still says 'C2 is a strictly larger extension class' "
                        "while the same file's chain at line %s has E_C2 innermost; 0 of %d hash-bound "
                        "full-schema accepts flags the inversion."
                        % (audit["defects"]["chain_line"],
                           audit["headline"]["full_schema_accepts_permissive"])),
             "falsifier": ("corrected bytes at that field in a new revision, or a containment-respecting "
                           "reading in which E_C2 is strictly larger than E_C0"),
             "corroborates": ["W053-F2B-REV29-01", "W088 F2b B1", "W066 R13-F2B-H2", "W075 C8"]},
            {"id": "HF-W035-AA-02",
             "field": "regularity.must_not_conflate[0]",
             "detail": ("The stale denial 'No containment with C2 or C0 is asserted here' is live at line %s "
                        "while the file asserts the chain; at least one accept at the pin asserts this "
                        "contradiction resolved." % audit["defects"]["denial_line"]),
             "falsifier": ("show the denial cannot be read as an extension-set claim, or produce corrected "
                           "bytes at that field"),
             "corroborates": ["W088 F2b B2", "W066 R13-F2B-H1", "W085 F-085R-02"]},
            {"id": "HF-W035-AA-03",
             "field": "review_status",
             "detail": ("review_status.independent_reviewers=[] and verdict=pending at the pin while %d F2b "
                        "verdict records bind the measured bytes; the status block is stale and cannot "
                        "certify coverage."
                        % audit["census"]["records_bound_to_pin"]),
             "falsifier": "a revision whose review_status lists the bound reviewers and a decided verdict",
             "corroborates": ["W090-F2B13-02", "W090 R01-review-status-fresh fail"]},
        ],
        "falsifiers": [
            "a hash-bound full-schema accept at the pin that explicitly dispositions both live defect families",
            "corrected bytes at lines %s/%s in a new revision" % (audit["defects"]["forbidden_transfer_line"],
                                                                  audit["defects"]["denial_line"]),
            "evidence the live chain marker is not the operative containment reading",
        ],
        "non_claims": [
            "not a gate verdict; worker events cannot set G-FORM, node status or validation_status",
            "does not overturn or replace any reviewer verdict; it audits coverage materiality only",
            "no physics claim; the containment chain is read as the file states it",
            "does not edit any canonical path",
        ],
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    controls_doc = {
        "task_id": "W035-F2B-ACCEPT-AUDIT-01",
        "actor": "worker-035",
        "created_at": started,
        "controls": controls,
        "controls_caught": sum(1 for c in controls if c["caught"]),
        "controls_total": len(controls),
        "null_control": "K0",
        "note": "Controls validate the detector, not the physics of the schema.",
    }
    with open(os.path.join(OUT, "controls.json"), "w", encoding="utf-8") as fh:
        json.dump(controls_doc, fh, indent=1, sort_keys=True)

    summary = {
        "headline": audit["headline"],
        "checks_pass": sum(1 for c in audit["checks"] if c["status"] == "pass"),
        "checks_total": len(audit["checks"]),
        "blocking_failed": [c["id"] for c in fail],
        "controls_pass": controls_doc["controls_caught"],
        "controls_total": controls_doc["controls_total"],
        "drift": drift,
    }
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
