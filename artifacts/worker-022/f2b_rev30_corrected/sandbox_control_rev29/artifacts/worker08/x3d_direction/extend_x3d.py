#!/usr/bin/env python3
"""W008-FORMSEP04-X3D-01: document-relative entailment-direction certification.

Closes the FORM-SEP-04 X3c blind spot: the v3 battery classified
"H2_loc-inextendibility ENTAILS this class's conclusion" as correct_direction in
*any* SCC document, because it never resolved "this class" against the document
that carries the sentence.  In the C2 schema (own class C2, rank 0) the sentence
is true; transplanted into the C0 schema (own class C0, rank 3) the same bytes
are a forbidden converse assertion.

Rule (from the documents themselves):
  extension_class_containment declares E_C0 contains E_H2loc contains E_{C^1,1}
  contains E_C2, i.e. size_rank {C0:0, H2loc:1, C^{1,1}:2, C2:3} (0 = largest set).
  S_A ("no proper future A extension") entails S_B iff size_rank(A) <= size_rank(B).
  "this class" resolves to the carrier document's own class token.

Exit codes: 0 measured, 2 pin/parse failure (fail closed), 3 unresolved carrier.
Worker-level instrument only: no gate verdict, no node status, no canonical write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
CANON_C2 = "schemas/af_scc_c2_vacuum.yaml"
CANDS = {
    "c0_84b5d3fa": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "c0_9ab32ee3": "artifacts/worker-008/f2b_line152_direction/pinned/candidate_9ab32ee3.yaml",
    "c0_679ab7bc": "artifacts/worker-080/f2b_hf1_direction_census/snapshots/679ab7bc8746__CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
}
PINS = {
    CANON_C0: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CANON_C2: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml":
        "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/worker-008/f2b_line152_direction/pinned/candidate_9ab32ee3.yaml":
        "9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17",
    "artifacts/worker-080/f2b_hf1_direction_census/snapshots/679ab7bc8746__CANDIDATE_schemas_af_scc_c0_vacuum.yaml":
        "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9",
}
FROZEN = "artifacts/formulation/FROZEN.json"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
V3_BATTERY = "artifacts/worker08/rev29_candidate/battery_candidate.json"
V3_BATTERY_PIN = "2b7b19840256b0dea486e8f6ba25615229f1bdbc3aa548fed4bb9ff4b38e54da"

TOKEN_RX = r"(?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?|this class)"
CLASS_ID_TO_TOKEN = {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2"}
NORM = {
    "C0": "C0", "C2": "C2", "C^1,1": "C^1,1", "C1,1": "C^1,1", "C^{1,1}": "C^1,1",
    "H2LOC": "H2loc", "H2_loc": "H2loc", "THIS CLASS": "SELF",
}
ATTRIBUTION = re.compile(r"worker-\d+|according to|quoted|quotation|must not be cited", re.I)
ENTAIL_VERB = re.compile(r"\b(?:entails?|implies?|subsum\w*|establish\w*)\b", re.I)
NEG_BEFORE = re.compile(r"\b(?:not|no|never|cannot|does not|do not)\b[^.;]{0,60}$", re.I)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk_leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def norm_token(raw: str, own: str) -> str:
    r = raw.strip().strip("'\"")
    if re.fullmatch(r"this class(?:'s)?", r, re.I):
        return own
    key = re.sub(r"\s+", "", r).upper().replace("_", "").replace("{", "").replace("}", "")
    for k, v in NORM.items():
        if re.sub(r"\s+", "", k).upper().replace("_", "").replace("{", "").replace("}", "") == key:
            return v
    if "1,1" in key:
        return "C^1,1"
    if key.startswith("H2"):
        return "H2loc"
    return "UNKNOWN"


def parse_chain(text: str, own: str):
    """Parse 'E_A contains E_B ...' or 'E_A subset of E_B ...' -> {token: rank}."""
    seq = []
    m = re.search(r"E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?))"
                  r"(?:\s+(contains|subset of)\s+E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?)))+", text)
    if m:
        toks = re.findall(r"E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?))", m.group(0))
        toks = [norm_token(t, own) for t in toks]
        direction = "contains" if "contains" in m.group(0) else "subset"
        if direction == "subset":
            toks = list(reversed(toks))
        if len(toks) >= 4 and all(t != "UNKNOWN" for t in toks):
            return {t: i for i, t in enumerate(toks)}, direction
    # fallback: explicit 'subset of' chain anywhere
    m2 = re.search(r"E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?))(?:\s+subset of\s+E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?)))+", text)
    if m2:
        toks = [norm_token(t, own) for t in re.findall(r"E_?\{?((?:C0|C2|C\^?\{?1,1\}?|H2_?\{?loc\}?))", m2.group(0))]
        seq = list(reversed(toks))
        if len(seq) >= 4 and all(t != "UNKNOWN" for t in seq):
            return {t: i for i, t in enumerate(seq)}, "subset"
    return None, None


def own_token(doc: dict, path: str) -> str:
    cid = doc.get("class_id")
    if cid in CLASS_ID_TO_TOKEN:
        return CLASS_ID_TO_TOKEN[cid]
    raise SystemExit(f"FAIL-CLOSED: cannot resolve own class token for {path} (class_id={cid!r})")


def carrier_paths(doc: dict):
    """Pre-registered carrier set: normative prose slots of the SCC schemas."""
    out = []

    def add(path, value):
        if isinstance(value, str) and value.strip():
            out.append((path, value))

    reg = doc.get("regularity") or {}
    for i, v in enumerate(reg.get("must_not_conflate") or []):
        add(f"regularity.must_not_conflate[{i}]", v)
    add("regularity.extension_class_containment", reg.get("extension_class_containment"))
    led = doc.get("implication_ledger") or {}
    add("implication_ledger.extension_class_containment", led.get("extension_class_containment"))
    add("implication_ledger.subsumption_note", led.get("subsumption_note"))
    for i, v in enumerate(led.get("forbidden_weakenings") or []):
        add(f"implication_ledger.forbidden_weakenings[{i}]", v if isinstance(v, str) else (v or {}).get("reason"))
    for i, v in enumerate(led.get("one_way_entailments") or []):
        add(f"implication_ledger.one_way_entailments[{i}].reason", (v or {}).get("reason"))
    for i, v in enumerate(led.get("forbidden_transfers") or []):
        add(f"implication_ledger.forbidden_transfers[{i}].reason", (v or {}).get("reason"))
    return [(p, t) for p, t in out if t]


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


SUFFIX = (r"(?:'s)?[\s-]*(?:(?:conclusion|inextendibility)"
          r"|\s+(?:sibling|class|endpoint))")
CLAIM_RX = re.compile(
    r"(?P<ant>" + TOKEN_RX + SUFFIX + r")"
    r"(?P<mid>[^.;]{0,90}?)"
    r"(?P<verb>entails?|implies?|subsum\w*|establish\w*)"
    r"(?P<post>[^.;]{0,60}?)"
    r"(?:(?:the|a|an)\s+)?(?P<cons>" + TOKEN_RX + SUFFIX +
    r"(?:\s*(?:,|and)\s*(?:(?:the|a|an)\s+)?" + TOKEN_RX + SUFFIX + r")*)",
    re.I,
)
CONS_RX = re.compile(r"(?P<tok>" + TOKEN_RX + r")" + SUFFIX, re.I)
STRICT_VERB = re.compile(r"\b(?:entails?|implies?|subsum\w*)\b", re.I)
LOOSE_ANT = re.compile(r"(?:" + TOKEN_RX + r")[^.;]{0,40}$", re.I)
LOOSE_CONS = re.compile(r"^[^.;]{0,40}?(?:" + TOKEN_RX + r")", re.I)


def classify_sentence(sent: str, own: str, ranks: dict):
    """Return list of {ant, cons, licensed} claims, denial markers, or 'unresolved'."""
    if not ENTAIL_VERB.search(sent):
        return []
    if ATTRIBUTION.search(sent) and "this class" not in sent:
        return [{"skipped": "attributed_or_quoted_mention"}]
    claims = []
    for m in CLAIM_RX.finditer(sent):
        # a negation governing the verb is a denial, not an assertion
        preceding = sent[:m.start("verb")]
        if NEG_BEFORE.search(preceding) and not re.search(r"never the reverse", sent[m.end():], re.I):
            claims.append({"denial": True, "ant": m.group("ant"), "cons": m.group("cons")})
            continue
        ant = norm_token(re.sub(SUFFIX + r"$", "", m.group("ant").strip(), flags=re.I), own)
        for c in CONS_RX.finditer(m.group("cons")):
            cons = norm_token(c.group("tok"), own)
            if ant == "UNKNOWN" or cons == "UNKNOWN":
                claims.append({"unresolved": True, "ant_raw": m.group("ant"), "cons_raw": m.group("cons")})
                continue
            claims.append({"ant": ant, "cons": cons, "licensed": ranks[ant] <= ranks[cons],
                           "ant_rank": ranks[ant], "cons_rank": ranks[cons]})
    if claims:
        return claims
    # conservative fail-closed: a strict entailment verb joining two class referents that the
    # primary pattern could not resolve must be surfaced, never silently passed.
    for vm in STRICT_VERB.finditer(sent):
        before, after = sent[:vm.start()], sent[vm.end():]
        if NEG_BEFORE.search(before) or re.search(r"\b(?:not|never|no)\b", before[-30:], re.I):
            continue
        if LOOSE_ANT.search(before) and LOOSE_CONS.search(after):
            return [{"unresolved": True, "sentence": sent}]
    return claims


def audit_doc(path: str, own_expected: str | None = None):
    p = REPO / path
    if not p.exists():
        raise SystemExit(f"FAIL-CLOSED: missing {p}")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    own = own_token(doc, path)
    if own_expected and own != own_expected:
        raise SystemExit(f"FAIL-CLOSED: {path} own class {own} != expected {own_expected}")
    chain_text = ""
    for k, v in walk_leaves(doc):
        if k.endswith("extension_class_containment") and isinstance(v, str):
            chain_text = v
            break
    ranks, direction = parse_chain(chain_text, own)
    if not ranks:
        raise SystemExit(f"FAIL-CLOSED: cannot parse declared containment in {path}")
    if sorted(ranks, key=ranks.get) != ["C0", "H2loc", "C^1,1", "C2"]:
        raise SystemExit(f"FAIL-CLOSED: declared order in {path} is not the frozen order: {ranks}")
    hits, unresolved, denials, clean = [], [], [], []
    for cpath, text in carrier_paths(doc):
        for sent in sentences(text):
            for c in classify_sentence(sent, own, ranks):
                if c.get("denial"):
                    denials.append({"path": cpath, "sentence": sent[:200]})
                elif c.get("skipped"):
                    clean.append({"path": cpath, "skipped": c["skipped"]})
                elif c.get("unresolved"):
                    unresolved.append({"path": cpath, "sentence": sent[:200]})
                elif c["licensed"]:
                    clean.append({"path": cpath, "ant": c["ant"], "cons": c["cons"],
                                  "ranks": [c["ant_rank"], c["cons_rank"]], "sentence": sent[:200]})
                else:
                    hits.append({"kind": "entailment_direction_inverted", "path": cpath,
                                 "ant": c["ant"], "cons": c["cons"],
                                 "ranks": [c["ant_rank"], c["cons_rank"]],
                                 "sentence": sent[:260]})
    return {
        "path": path, "sha256": sha256(p), "own_token": own,
        "declared_order": [t for t in sorted(ranks, key=ranks.get)],
        "size_rank": ranks, "containment_direction": direction,
        "hits": hits, "denials": denials, "unresolved": unresolved, "clean_licensed": clean,
        "verdict": "FAIL" if hits else ("REVIEW" if unresolved else "PASS"),
    }


def synthetic(own: str, carrier: str):
    doc = {
        "class_id": "AF-SCC-C0-VAC-GEN" if own == "C0" else "AF-SCC-C2-VAC-GEN",
        "regularity": {
            "extension_class_containment": (
                "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; this class requires the "
                "LOWEST regularity, so its inexistence statement is the STRONGEST"
                if own == "C0" else
                "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; this class is the C2 endpoint"
            ),
            "must_not_conflate": [carrier],
        },
    }
    return doc


def synthetic_audit(label, doc, own_expected):
    tmp = OUT / f"_synth_{label}.yaml"
    tmp.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    res = audit_doc(str(tmp.relative_to(REPO)), own_expected)
    res["label"] = label
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(OUT / "run.json"))
    args = ap.parse_args()

    # pin check (fail closed before any measurement)
    pins = {}
    for rel, exp in list(PINS.items()) + [(FROZEN, FROZEN_PIN), (V3_BATTERY, V3_BATTERY_PIN)]:
        p = REPO / rel
        got = sha256(p) if p.exists() else None
        pins[rel] = {"expected": exp, "measured": got, "match": got == exp}
    if not all(v["match"] for v in pins.values()):
        print(json.dumps({"verdict": "FAIL-CLOSED", "reason": "pin mismatch", "pins": pins}, indent=1))
        return 2

    corpus = []
    corpus.append(dict(audit_doc(CANON_C0, "C0"), label=f"{CANON_C0}#{PINS[CANON_C0][:12]}"))
    corpus.append(dict(audit_doc(CANON_C2, "C2"), label=f"{CANON_C2}#{PINS[CANON_C2][:12]}"))
    for label, rel in CANDS.items():
        row = dict(audit_doc(rel, "C0"))
        row["label"] = f"{label}#{row['sha256'][:12]}"
        corpus.append(row)

    synth = [
        synthetic_audit("c0_repaired_self_entails_h2loc_c2", synthetic(
            "C0", "this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse"), "C0"),
        synthetic_audit("c0_converse_canary", synthetic(
            "C0", "C2-inextendibility entails this class's conclusion"), "C0"),
        synthetic_audit("c2_same_carrier_is_true", synthetic(
            "C2", "H2_loc-inextendibility ENTAILS this class's conclusion"), "C2"),
    ]

    # v3 battery false negative: read the frozen battery artifact for the same candidate hash
    v3 = json.loads((REPO / V3_BATTERY).read_text())
    v3_x3c = v3.get("X3c_containment_inversion", {})
    v3_entry = {
        "artifact": V3_BATTERY, "sha256": V3_BATTERY_PIN,
        "battery_verdict": v3.get("verdict"),
        "x3c_hits": len(v3_x3c.get("hits") or []),
        "candidate_sha256": (v3.get("inputs") or {}).get(
            "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml"),
    }

    expectations = {
        f"{CANON_C0}#{PINS[CANON_C0][:12]}": "PASS",
        f"{CANON_C2}#{PINS[CANON_C2][:12]}": "PASS",
        "c0_84b5d3fa#84b5d3fa29a6": "FAIL",
        "c0_9ab32ee3#9ab32ee39d00": "PASS",
        "c0_679ab7bc#679ab7bc8746": "PASS",
        "c0_repaired_self_entails_h2loc_c2": "PASS",
        "c0_converse_canary": "FAIL",
        "c2_same_carrier_is_true": "PASS",
    }
    observed = {}
    for r in corpus:
        observed[r.get("label") or f"{r['path']}#{r['sha256'][:12]}"] = r["verdict"]
    for r in synth:
        observed[r["label"]] = r["verdict"]

    controls = []
    for key, exp in expectations.items():
        got = observed.get(key)
        controls.append({"control": key, "expected": exp, "observed": got, "pass": got == exp})
    unresolved_total = sum(len(r["unresolved"]) for r in corpus + synth)
    fail_closed_ok = unresolved_total == 0
    ok = all(c["pass"] for c in controls) and fail_closed_ok

    out = {
        "instrument": "worker-008/FORMSEP04-X3D/v1",
        "task_id": "W008-FORMSEP04-X3D-01",
        "actor": "worker-008", "agent_id": "deepseek-flash-08",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F2b", "gate": "G-CLASSBIND",
        "created_at": "2026-09-12T01:20:00+08:00",
        "rule": "S_A entails S_B iff size_rank(A) <= size_rank(B), size_rank from the carrier document's own extension_class_containment; 'this class' = the carrier document's own class token",
        "pins": pins,
        "corpus": [{k: v for k, v in r.items() if k != "clean_licensed"} for r in corpus],
        "synthetic_controls": [{k: v for k, v in r.items() if k != "clean_licensed"} for r in synth],
        "controls": controls,
        "v3_battery_false_negative": v3_entry,
        "unresolved_carriers": unresolved_total,
        "verdict": "X3D_CERTIFIED" if ok else "FAIL-CLOSED",
        "next_falsifier": "Any of: a pin move; the same carrier sentence classified identically in C0 and C2 documents (document-relative resolution broken); 84b5d3fa not returning exactly one inverted hit at regularity.must_not_conflate[0]; 9ab32ee3 or 679ab7bc returning a hit; a correct C0 self-entailment flagged; an unresolved entailment carrier passing as clean.",
    }
    (REPO / args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("verdict", "controls", "v3_battery_false_negative")}, indent=1))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
