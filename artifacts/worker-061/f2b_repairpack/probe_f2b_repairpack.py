#!/usr/bin/env python3
"""W061-F2B-REPAIRPACK-09 -- independent repair-pack adjudication for F2b.

Class AF-SCC-C0-VAC-GEN / node F2b / gate G-FORM.  Read-only on canonical files:
every mutation happens in ./sandbox/.  The probe is deterministic and fail-closed.

  python3 probe_f2b_repairpack.py            # exit 0 measured / 1 control / 2 pin drift

What it does
  P0  re-measures 12 pins (any drift -> exit 2 before interpreting anything)
  P1  locates the two consensus defect carriers in the pinned F2b bytes
  P2  re-derives the stated containment order and machine-checks 9 obligations
      on the structured YAML (not on prose heuristics alone)
  P3  exhaustive direction census: every containment/strength token line in the
      pinned bytes must be classified; an unclassified line fails the control
  P4  measures the blast radius of a rev14 repair (reviews bound to the hash,
      identical carrier strings elsewhere, FROZEN pins, stale sidecar)
  P5  builds a minimal two-line sandbox repair and re-runs the canonical gate
      plus the obligation checker on live / patched / mutant copies
  P6  controls K1-K6 (single-edit splits, over-correction, unrelated mutation,
      determinism, pin-drift detection)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = HERE / "sandbox"

F2B = "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"

PINS = {
    F2B: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    F2B_MIRROR: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

H1_INVERTED = "C2 is a strictly larger extension class"
H2_STALE = "No containment with C2 or C0 is asserted here"

H1_BEFORE = 'reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"'
H1_AFTER = ('reason: "the converse containment is false; E_C2 is a proper subset of E_C0, '
            'so C2-inextendibility is strictly weaker than this class\'s conclusion"')
H2_BEFORE = "No containment with C2 or C0 is asserted here; the informal phrase"
H2_AFTER = ("The extension sets are nested (E_C2 subset of E_{C^1,1} subset of E_H2loc subset of "
            "E_C0), so containment with both C2 and C0 IS asserted (see implication_ledger); "
            "the informal phrase")

CHAIN_EXPECTED = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
CHAIN_ORDER = ["C2", "C^1,1", "H2loc", "C0"]          # innermost -> outermost E-set
PARTIAL_ORDER = [("C2", "C^1,1"), ("C^1,1", "H2loc"), ("H2loc", "C0"), ("C0dist", "C0")]

TOKEN_RE = re.compile(r"contain|larger|smaller|stronger|weaker|subset|superset|nested|entail", re.I)

# Exhaustive classification of every direction-token line in the pinned bytes,
# keyed by sha1(strip(line))[:10].  categories/verdicts:
#   claim_strength : a claim about relative logical strength / set containment
#   obligation     : machine-checked by the structured checker
#   usage          : set-theoretic/quantifier occurrence, not a strength claim
#   history        : revision-note / provenance text
CENSUS = {
    "78a9253d29": ("history", "n/a", "rev6 delta note naming the containment-chain repair"),
    "2108e81072": ("usage", "n/a", "quantifier domain G_r subset X^r_vac"),
    "c0dc6f4a14": ("usage", "n/a", "D1 definition: residual subsets of X"),
    "e8605f713c": ("usage", "n/a", "negation quantifier G_r subset X"),
    "6372744466": ("claim_strength", "correct", "excludes all continuous => excludes all C2; C0 => C2, converse forbidden"),
    "69a1d07c3f": ("usage", "n/a", "iota(M) open proper subset of M'"),
    "010da7eaaa": ("claim_strength", "correct", "'a subset of this one' => ruling out ALL continuous is the stronger statement"),
    "34bcd6e699": ("claim_strength", "correct", "distributional-vacuum extensions a strictly weaker (smaller) class"),
    "da9b8d1568": ("usage", "n/a", "topology: iota(M) open proper subset of M'"),
    "b05a9b1be1": ("claim_strength", "correct", "differentiable g' is the sibling class or stronger"),
    "f941783ee1": ("claim_strength", "INVERTED", "stale 'No containment with C2 or C0' denial contradicts extension_class_containment + one_way_entailments"),
    "f10eae4223": ("claim_strength", "correct", "distributional-vacuum statement strictly weaker (fewer allowed extensions)"),
    "086df0e0f8": ("usage", "n/a", "ambient-space/topology prose"),
    "6150644480": ("usage", "n/a", "generic set definition"),
    "a0fb0bdaf5": ("usage", "n/a", "Kerr development admits a C-infinity (hence C0) extension: factually correct"),
    "8dd4bdc943": ("claim_strength", "correct", "forall-data and dense-open are strictly stronger than comeager"),
    "123a8f581f": ("claim_strength", "correct", "comeager need not contain an open subset (no_transfer witness)"),
    "42f3ca4bba": ("claim_strength", "correct", "open_dense_escape strictly stronger, implies residual_comeager"),
    "25549bc4c8": ("claim_strength", "correct", "dense_escape strictly weaker, implied by residual_comeager"),
    "eed60a0d49": ("claim_strength", "correct", "none (forall data) strictly stronger"),
    "0cc157b35d": ("usage", "n/a", "non-vacuity witness prose"),
    "fc642c8d3c": ("claim_strength", "correct", "C2 result is weaker evidence for the C0 statement"),
    "7d02041be0": ("claim_strength", "correct", "C0 => C2 only; C0-inextendibility stronger; C2 weaker"),
    "e6ad4b6505": ("claim_strength", "correct", "C2/C1/H2_loc claims are WEAKER -> forbidden_weakenings"),
    "b3afe31de5": ("claim_strength", "correct", "two-sided inextendibility is a stronger statement"),
    "1f17834e4e": ("claim_strength", "correct", "H2_loc-inextendibility weaker than C0 and entails the C2 sibling"),
    "e7a06a0675": ("claim_strength", "correct", "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; C0 conclusion STRONGEST"),
    "2dedb1c8a8": ("usage", "n/a", "structural key"),
    "86771b2817": ("obligation", "correct", "one_way C0 => H2_loc ; E_H2loc subset E_C0"),
    "870125801e": ("obligation", "correct", "one_way H2_loc => C2 ; E_C2 subset E_H2loc"),
    "cdf6d1ff94": ("obligation", "correct", "one_way C0 => C2 by transitivity"),
    "d8de2e92be": ("obligation", "correct", "one_way C0 => C0-distributional ; E_C0dist subset E_C0"),
    "7404aefbc9": ("claim_strength", "INVERTED", "forbidden-transfer reason inverts the premise: C2's extension set is the smallest, not strictly larger"),
    "73b2edee24": ("obligation", "correct", "converse C2-inextendibility => H2_loc-inextendibility forbidden; converse containment false"),
    "e0b5d62c08": ("usage", "n/a", "iota is an isometry onto an open proper subset"),
    "b3cf88d486": ("claim_strength", "correct", "tier-2 refutes only the strictly stronger forall-data class"),
    "cd08f7cb70": ("claim_strength", "correct", "weaker-evidence citation direction"),
    "d75b730021": ("claim_strength", "correct", "C2 sibling is a different (weaker) statement"),
    "ee50dd29b6": ("claim_strength", "correct", "variant CH strictly WEAKER; a subset of extensions suffices to refute it"),
}

SCAN_ROOTS = ["schemas", "artifacts/formulation", "reviews", "research_map", "ledger", "evaluation"]
SCAN_SUFFIX = {".yaml", ".yml", ".json", ".jsonl", ".md", ".txt"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def check_pins(expected: dict) -> dict:
    out = {}
    for rel, want in expected.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else None
        out[rel] = {"expected": want, "measured": got, "ok": got == want}
    return out


# ---------------------------------------------------------------- P2 checker
def _reg_of(label: str):
    l = label.lower()
    if "distributional" in l:
        return "C0dist"
    if "c^1,1" in l or "c^{1,1}" in l or "c1,1" in l:
        return "C^1,1"
    if "h2_loc" in l or "h2loc" in l:
        return "H2loc"
    if re.search(r"\bc2\b", l):
        return "C2"
    if re.search(r"\bc0\b", l):
        return "C0"
    return None


def _entails(chain, a, b) -> bool:
    """no-a-extension entails no-b-extension  iff  E_b subset E_a."""
    if a == b:
        return True
    seen, frontier = {a}, [a]
    while frontier:
        cur = frontier.pop()
        for (inner, outer) in PARTIAL_ORDER:
            if outer == cur and inner not in seen:
                seen.add(inner)
                frontier.append(inner)
    return b in seen


def _find_key(obj, key):
    """First occurrence of `key` anywhere in a nested dict/list (structure is pinned)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def obligation_check(doc: dict) -> dict:
    res = {}

    def fail(oid, detail):
        res.setdefault(oid, {"status": "pass", "failures": []})
        res[oid]["status"] = "fail"
        res[oid]["failures"].append(detail)

    for oid in ("O1_forbidden_reason_premise", "O2_must_not_conflate_stale_denial",
                "O3_containment_chain", "O4_one_way_entailments", "O5_forbidden_rows_not_licensed",
                "O6_subsumption_direction", "O7_sibling_direction", "O8_genericity_strength_labels",
                "O9_weaker_evidence_direction"):
        res[oid] = {"status": "pass", "failures": []}

    il = doc.get("implication_ledger", {})
    chain = str(il.get("extension_class_containment", ""))
    if CHAIN_EXPECTED not in chain:
        fail("O3_containment_chain", f"expected order not found verbatim; got: {chain[:160]}")

    fts = il.get("forbidden_transfers", []) or []
    if not fts:
        fail("O1_forbidden_reason_premise", "forbidden_transfers empty")
    else:
        r0 = str(fts[0].get("reason", ""))
        r0l = r0.lower()
        if H1_INVERTED.lower() in r0l:
            fail("O1_forbidden_reason_premise",
                 "row[0] asserts 'C2 is a strictly larger extension class' while E_C2 is the "
                 "innermost (smallest) set; premise inverted")
        if not re.search(r"converse|false|smaller|proper subset", r0l):
            fail("O1_forbidden_reason_premise",
                 "row[0] reason does not state the correct containment direction")
        if "strictly stronger" in r0l:
            fail("O1_forbidden_reason_premise",
                 "row[0] concludes that C2-inextendibility is strictly stronger, but E_C2 is the "
                 "innermost set so it is strictly weaker than this class's conclusion")
        if "strictly weaker" not in r0l and "converse containment is false" not in r0l:
            fail("O1_forbidden_reason_premise",
                 "row[0] reason does not state the weaker-than conclusion (C2-inextendibility is "
                 "strictly weaker / the converse containment is false)")

    mnc = doc.get("regularity", {}).get("must_not_conflate", []) or []
    stale = [i for i, s in enumerate(mnc) if "no containment with c2" in str(s).lower()]
    if stale:
        fail("O2_must_not_conflate_stale_denial",
             f"must_not_conflate[{stale[0]}] still denies containment with C2/C0 although the "
             "same file asserts the chain and four one-way entailment rows")

    rows = il.get("one_way_entailments", []) or []
    if len(rows) < 3:
        fail("O4_one_way_entailments", f"expected >=3 one-way rows, found {len(rows)}")
    for i, row in enumerate(rows):
        a, b = _reg_of(str(row.get("from", ""))), _reg_of(str(row.get("to", "")))
        if a is None or b is None:
            fail("O4_one_way_entailments", f"row {i}: unrecognized regularity in {row}")
            continue
        if not _entails(chain, a, b):
            fail("O4_one_way_entailments",
                 f"row {i}: claims no-{a} entails no-{b} but E_{b} is not a subset of E_{a}")

    for i, row in enumerate(fts):
        a, b = _reg_of(str(row.get("from", ""))), _reg_of(str(row.get("to", "")))
        if a is None or b is None:
            continue  # cross-family row
        if _entails(chain, a, b):
            fail("O5_forbidden_rows_not_licensed",
                 f"forbidden row {i} (no-{a} -> no-{b}) is in fact a licensed entailment")

    note = str(il.get("subsumption_note", ""))
    if "never the reverse" not in note or "C0 => H2loc => C2" not in note:
        fail("O6_subsumption_direction",
             "subsumption_note must state the chain C0 => H2loc => C2 and 'never the reverse'")

    sib = str(_find_key(doc, "conclusion_relation_to_sibling") or "")
    if "C0 => C2" not in sib or "converse is forbidden" not in sib:
        fail("O7_sibling_direction", "sibling relation must state C0 => C2 and forbid the converse")

    variants = doc.get("genericity", {}).get("variants", []) or []
    want = {"open_dense_escape": "strictly_stronger", "dense_escape": "strictly_weaker"}
    seen = {}
    for v in variants:
        if isinstance(v, dict) and v.get("kind") in want:
            seen[v["kind"]] = str(v.get("statement_strength", ""))
    for kind, strength in want.items():
        if seen.get(kind) != strength:
            fail("O8_genericity_strength_labels",
                 f"{kind}: expected statement_strength={strength}, got {seen.get(kind)!r}")

    weak = str(_find_key(doc, "c0_specific_note") or "") + \
        str(_find_key(doc, "vacuity_falsifier") or "")
    if "C0 => C2" not in weak or "weaker" not in weak.lower():
        fail("O9_weaker_evidence_direction",
             "c0_specific_note/vacuity_falsifier must keep C0 => C2 and call a C2 result weaker")

    flags = sorted(k for k, v in res.items() if v["status"] == "fail")
    return {"obligations": res, "flags": flags}


# ---------------------------------------------------------------- P4 blast radius
def scan_carrier_strings(needles):
    hits = {}
    for needle in needles:
        found = []
        for root_rel in SCAN_ROOTS:
            root = ROOT / root_rel
            if not root.is_dir():
                continue
            for p in sorted(root.rglob("*")):
                if not p.is_file() or p.suffix.lower() not in SCAN_SUFFIX:
                    continue
                if "__pycache__" in p.parts or p.stat().st_size > 2_000_000:
                    continue
                try:
                    t = p.read_text(errors="ignore")
                except OSError:
                    continue
                if needle in t:
                    found.append(str(p.relative_to(ROOT)))
        groups = {}
        for f in found:
            parts = f.split("/")
            key = "/".join(parts[:3]) if parts[:2] == ["artifacts", "formulation"] else \
                "/".join(parts[:2]) if len(parts) > 1 else parts[0]
            groups[key] = groups.get(key, 0) + 1
        hits[needle] = {"count": len(found), "groups": dict(sorted(groups.items())),
                        "files": found[:40], "truncated": len(found) > 40}
    return hits


def reviews_bound(expected_sha: str):
    """Split strict hash-binding (verdict voided by a hash move) from mere mentions."""
    bound, mentions = [], []
    by_verdict, mention_fields = {}, {}
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        sha12 = expected_sha[:12]
        rv = str(d.get("reviewed_sha256") or "")
        meta = {"file": str(p.relative_to(ROOT)), "reviewer": d.get("reviewer"),
                "verdict": d.get("verdict"), "field": "reviewed_sha256",
                "sha256": sha256_file(p),
                "mtime": _dt.datetime.fromtimestamp(
                    p.stat().st_mtime).astimezone().isoformat(timespec="seconds")}
        if rv.startswith(sha12):
            v = str(d.get("verdict"))
            by_verdict[v] = by_verdict.get(v, 0) + 1
            bound.append(dict(meta, score=d.get("score")))
            continue
        for field in ("artifact_sha256", "frozen_rev29_pin", "sibling_sha256",
                      "assignment_pin"):
            val = str(d.get(field) or "")
            if val.startswith(sha12):
                mention_fields[field] = mention_fields.get(field, 0) + 1
                mentions.append(dict(meta, field=field))
                break
    return {"strict_binding_count": len(bound), "by_verdict": by_verdict, "files": bound,
            "other_field_mention_count": len(mentions),
            "other_field_counts": dict(sorted(mention_fields.items())),
            "other_field_files": mentions[:20]}


def frozen_pins():
    man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    out = {"revision": man.get("revision"), "frozen_at": man.get("frozen_at"),
           "pins": {}, "carrier_copies_in_frozen": []}
    for key in (F2B, F2B_MIRROR):
        v = (man.get("files") or {}).get(key)
        out["pins"][key] = v if isinstance(v, str) else json.dumps(v)[:200]
    for key in sorted((man.get("files") or {}).keys()):
        if "fixture" in key or "rebased" in key:
            out["carrier_copies_in_frozen"].append(key)
    out["carrier_copies_in_frozen_count"] = len(out["carrier_copies_in_frozen"])
    return out


# ---------------------------------------------------------------- sandbox runs
def apply_edits(text: str, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"edit target not unique: {old[:60]!r} count={text.count(old)}")
        text = text.replace(old, new)
    return text


def run_gate(path: Path):
    proc = subprocess.run([sys.executable,
                           str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                           "--json", str(path)],
                          capture_output=True, text=True)
    try:
        report = json.loads(proc.stdout)
    except Exception:
        report = {"raw_stdout": proc.stdout[:400], "raw_stderr": proc.stderr[:200]}
    return {"returncode": proc.returncode, "verdict": report.get("verdict"),
            "failed_rules": report.get("failed_rules"), "class_id": report.get("class_id")}


def main():
    import yaml  # local import: yaml is available in this environment

    out = {
        "task_id": "W061-F2B-REPAIRPACK-09",
        "worker": "worker-061",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "target": F2B,
        "method": "read-only pin re-measure, structured obligation checker, exhaustive token census, "
                  "sandbox two-line repair + canonical gate replay, K1-K6 controls",
        "generated_at": None,  # stamped only in the emitted event, not in the deterministic core
        "status": "measured",
        "pins": check_pins(PINS),
    }
    drift = sorted(k for k, v in out["pins"].items() if not v["ok"])
    if drift:
        out["status"] = "pin_drift"
        out["drift"] = drift
        (HERE / "probe_output.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        (HERE / "PROBE_EXIT.txt").write_text("2\n")
        print(json.dumps({"status": "pin_drift", "drift": drift}, indent=1))
        return 2

    raw = (ROOT / F2B).read_bytes()
    live = raw.decode()
    lines = live.splitlines()
    out["target_sha256_measured"] = sha256_bytes(raw)

    # P1 carriers
    carriers = {}
    for cid, needle, correct in (("H1", H1_INVERTED, H1_AFTER),
                                 ("H2", H2_STALE, H2_AFTER)):
        hits = [i + 1 for i, l in enumerate(lines) if needle in l]
        carriers[cid] = {"needle": needle, "lines": hits, "unique": len(hits) == 1,
                         "text": lines[hits[0] - 1].strip() if len(hits) == 1 else None,
                         "proposed_after_substring": correct}
    out["carriers"] = carriers
    if not all(c["unique"] for c in carriers.values()):
        out["status"] = "control_failure"
        out["failure"] = "carrier string not unique in pinned bytes"
        (HERE / "probe_output.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        return 1

    doc = yaml.safe_load(live)
    out["chain"] = {
        "extension_class_containment": doc["implication_ledger"]["extension_class_containment"],
        "partial_order": PARTIAL_ORDER,
        "derived": {
            "E_C2_subset_E_C0": "true (strict)",
            "no_C2_entails_no_C0": False,
            "no_C0_entails_no_C2": True,
            "H1_premise_C2_strictly_larger": False,
            "H1_conclusion_C2_inextendibility_strictly_weaker": True,
            "H2_claim_no_containment_with_C2_or_C0": False,
        },
    }

    live_check = obligation_check(doc)

    # P3 census
    token_lines, flagged, unclassified = [], [], []
    for i, l in enumerate(lines, 1):
        if not TOKEN_RE.search(l):
            continue
        sig = hashlib.sha1(l.strip().encode()).hexdigest()[:10]
        entry = CENSUS.get(sig)
        row = {"line": i, "sig": sig, "text": l.strip()[:180]}
        if entry is None:
            unclassified.append(row)
        else:
            row.update({"category": entry[0], "verdict": entry[1], "note": entry[2]})
            if entry[1] == "INVERTED":
                flagged.append(row)
            token_lines.append(row)
    out["census"] = {"token_line_count": len(token_lines) + len(unclassified),
                     "classified": len(token_lines), "unclassified": unclassified,
                     "flagged": flagged, "rows": token_lines}
    if unclassified:
        out["status"] = "control_failure"
        out["failure"] = "unclassified direction-token lines (completeness guard tripped)"
        (HERE / "probe_output.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        return 1

    # P4 blast radius
    out["blast_radius"] = {
        "reviews_bound_to_target": reviews_bound(PINS[F2B]),
        "identical_carrier_strings_elsewhere": scan_carrier_strings([H1_INVERTED, H2_STALE,
                                                                     H1_BEFORE, H2_BEFORE]),
        "frozen": frozen_pins(),
        "sidecar_sha256_file": {
            "path": "schemas/af_scc_c0_vacuum.yaml.sha256",
            "content": (ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256").read_text().strip()
            if (ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256").is_file() else None,
        },
        "verdicts_voided_by_a_rev14_repair": None,  # filled below
    }
    out["blast_radius"]["verdicts_voided_by_a_rev14_repair"] = \
        out["blast_radius"]["reviews_bound_to_target"]["strict_binding_count"]

    # P5 sandbox repair
    SANDBOX.mkdir(exist_ok=True)
    edit_h1 = (H1_BEFORE, H1_AFTER)
    edit_h2 = (H2_BEFORE, H2_AFTER)
    variants = {
        "live": [],
        "patched": [edit_h1, edit_h2],
        "k1_h1_only": [edit_h1],
        "k2_h2_only": [edit_h2],
        "k3_overcorrect": [edit_h2, (H1_BEFORE,
                                     'reason: "C2 is a strictly smaller extension class, so '
                                     'C2-inextendibility is strictly stronger"')],
        "k4_unrelated": [(CHAIN_EXPECTED, CHAIN_EXPECTED)],  # no-op guard; real mutation below
    }
    results = {}
    for name, edits in variants.items():
        text = live
        for old, new in edits:
            if old == new:
                continue
            if text.count(old) != 1:
                raise SystemExit(f"{name}: edit not unique {old[:50]!r}")
            text = text.replace(old, new)
        if name == "k4_unrelated":
            text = text.rstrip("\n") + "\n# K4 unrelated mutation (sandbox only)\n"
        p = SANDBOX / f"{name}.yaml"
        p.write_text(text)
        try:
            d = yaml.safe_load(text)
            parse_ok = isinstance(d, dict)
        except Exception as exc:
            d, parse_ok = {}, False
            results.setdefault(name, {})["parse_error"] = str(exc)[:200]
        chk = obligation_check(d) if parse_ok else {"flags": ["yaml_unparseable"], "obligations": {}}
        diff_lines = [i + 1 for i, (a, b) in enumerate(zip(lines, text.splitlines())) if a != b]
        results[name] = {"parse_ok": parse_ok, "flags": chk["flags"],
                         "diff_lines": diff_lines, "sha256": sha256_bytes(text.encode()),
                         "gate": run_gate(p)}
        if name in ("live", "patched", "k3_overcorrect", "k4_unrelated"):
            results[name]["obligations"] = chk["obligations"]
    out["checker"] = results

    out["repair_pack"] = {
        "minimal_edits": [
            {"file": F2B, "line": carriers["H1"]["lines"][0], "id": "H1",
             "before": H1_BEFORE, "after": H1_AFTER,
             "why": "the forbidden-transfer row's premise inverts the file's own containment "
                    "order; E_C2 is the innermost (smallest) extension set. The row's from/to "
                    "and conclusion are already correct; only the premise clause is wrong.",
             "authority": "semantic edit -> astra-lead-formulation rev14; void all verdicts "
                          "bound to b2ab6acb and re-freeze FROZEN"},
            {"file": F2B, "line": carriers["H2"]["lines"][0], "id": "H2",
             "before": H2_BEFORE, "after": H2_AFTER,
             "why": "stale pre-R2 denial retained in a required normative slot; the file itself "
                    "asserts E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2 and four "
                    "one-way entailment rows. F2a already carries the corrected counterpart.",
             "authority": "semantic edit -> astra-lead-formulation rev14; mirror copy must be "
                          "byte-identical; fixture corpus needs an explicit rebase-or-leave note"},
        ],
        "sibling_templates": {
            "F2a_must_not_conflate": (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
            .splitlines()[151].strip(),
            "F2a_forbidden_transfers_0": (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
            .splitlines()[242].strip(),
        },
        "mirror_requirement": F2B_MIRROR,
        "not_in_minimal_repair": [
            {"id": "V1", "finding": "F2b has no vocabulary_aliases_ref; F1 binds "
             "artifacts/formulation/VOCAB_ALIASES.json. conclusion_type "
             "scc_c0_future_inextendibility is the canonical first token of that registry and the "
             "supplement's conclusion_type for this class, while the F0 canonical "
             "field_vocabulary.conclusion_type.allowed list holds the alias "
             "strong_cosmic_censorship_C0. Classification: contested binding gap, not one of the "
             "two semantic carriers; needs an F0-side adjudication queued with the rev14 repair."},
            {"id": "V2", "finding": "schemas/af_scc_c0_vacuum.yaml.sha256 still pins the "
             "superseded rev 1bb78ce9b357 (already flagged by worker-035/worker-087)."},
        ],
        "expected_effect": "live flags={} -> patched flags={}".format(live_check["flags"],
                                                                     results["patched"]["flags"]),
    }

    # P6 controls
    controls = {
        "K1_h1_only": {"flags": results["k1_h1_only"]["flags"], "expect": ["O2_must_not_conflate_stale_denial"]},
        "K2_h2_only": {"flags": results["k2_h2_only"]["flags"], "expect": ["O1_forbidden_reason_premise"]},
        "K3_overcorrect": {"flags": results["k3_overcorrect"]["flags"], "expect": ["O1_forbidden_reason_premise"]},
        "K4_unrelated": {"flags": results["k4_unrelated"]["flags"],
                         "expect": live_check["flags"]},
        "K5_determinism": {},  # filled below
        "K6_pin_drift_detector": {},
    }
    # K5 determinism: recompute the structured checker twice on the patched bytes
    ptext = (SANDBOX / "patched.yaml").read_text()
    r1 = obligation_check(yaml.safe_load(ptext))
    r2 = obligation_check(yaml.safe_load(ptext))
    controls["K5_determinism"] = {
        "run1_flags": r1["flags"], "run2_flags": r2["flags"],
        "identical": json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)}
    # K6 pin-drift detector: altered expectation must be reported as drift
    fake = dict(PINS)
    fake[F2B] = "0" * 64
    k6 = check_pins(fake)
    controls["K6_pin_drift_detector"] = {
        "flags_drift": not k6[F2B]["ok"], "other_pins_ok": all(
            v["ok"] for k, v in k6.items() if k != F2B)}
    out["controls"] = controls

    controls_pass = (
        controls["K1_h1_only"]["flags"] == controls["K1_h1_only"]["expect"]
        and controls["K2_h2_only"]["flags"] == controls["K2_h2_only"]["expect"]
        and controls["K3_overcorrect"]["flags"] == controls["K3_overcorrect"]["expect"]
        and controls["K4_unrelated"]["flags"] == controls["K4_unrelated"]["expect"]
        and controls["K5_determinism"]["identical"]
        and controls["K6_pin_drift_detector"]["flags_drift"]
        and controls["K6_pin_drift_detector"]["other_pins_ok"]
        and results["live"]["gate"]["verdict"] == "pass"
        and results["patched"]["gate"]["verdict"] == "pass"
        and results["patched"]["diff_lines"] == sorted(carriers["H1"]["lines"] + carriers["H2"]["lines"])
        and live_check["flags"] == ["O1_forbidden_reason_premise", "O2_must_not_conflate_stale_denial"]
        and results["patched"]["flags"] == []
    )
    out["controls_pass"] = controls_pass
    if not controls_pass:
        out["status"] = "control_failure"
    out["verdict_summary"] = {
        "live_flags": live_check["flags"],
        "patched_flags": results["patched"]["flags"],
        "canonical_gate_on_live": results["live"]["gate"],
        "canonical_gate_on_patched": results["patched"]["gate"],
        "gate_blind_spot": (results["live"]["gate"]["verdict"] == "pass"
                            and results["patched"]["gate"]["verdict"] == "pass"),
        "census_flagged": [r["line"] for r in flagged],
    }

    (HERE / "probe_output.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (HERE / "PROBE_EXIT.txt").write_text("0\n" if out["status"] == "measured" else "1\n")
    print(json.dumps({"status": out["status"], "live_flags": live_check["flags"],
                      "patched_flags": results["patched"]["flags"],
                      "census_flagged_lines": [r["line"] for r in flagged],
                      "controls_pass": controls_pass,
                      "gate_live": results["live"]["gate"]["verdict"],
                      "gate_patched": results["patched"]["gate"]["verdict"]}, indent=1))
    return 0 if out["status"] == "measured" else 1


if __name__ == "__main__":
    sys.exit(main())
