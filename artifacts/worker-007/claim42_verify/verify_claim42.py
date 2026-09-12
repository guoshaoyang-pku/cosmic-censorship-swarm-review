#!/usr/bin/env python3
"""W007-CLAIM42-INDEP-VERIFY-01

Independent verification of the open map claim
  w072-20260912T001917-claim-conclusion-poor  (node L1, class AF-WCC-SCALAR-SPH)

Claim (verbatim): "At research_map/formulation_taxonomy.yaml#276009f4f63d,
ledger/theorems.jsonl#ce42d205e761 and ledger/citation_audit.csv#315c19145065:
no entry bound to AF-WCC-SCALAR-SPH discharges the class's weak-cosmic-censorship
conclusion, and no bound entry names the class's genericity notion (H4). 5/10 are
mechanically in-class (H1-H3) and carry instability/obstruction or numerical results
instead. The class is evidence-rich and conclusion-poor; with CG1 (no F-node) the
class cannot yet state a WCC claim."

Claim falsifier (verbatim): "A class-bound ledger entry that passes H1-H3, names an
explicit genericity notion with topology and primary-source scope, and carries
conclusion_type=weak_cosmic_censorship; or a class-conforming WCC entry omitted from
the bound set."

Method: written from scratch for worker-007; imports none of worker-072's code.
Pins the three inputs by sha256 (snapshot/ copies), re-derives the H1-H4 rules from
the pinned F0 bytes, classifies every ledger entry with documented token rules,
searches the whole ledger for the falsifier witnesses, and reconciles with worker-072's
stated per-entry rule (reproduced separately, including its substring hazard).

Outputs: report.json (machine-readable) + stdout summary.  Exit 0 when the scan
completes (whatever the verdict); 2 on binding failure (snapshot hash mismatch).
No canonical artifact is edited.  Not a gate verdict; not a node transition.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # repo root: artifacts/worker-007/<task>/ -> repo
SNAP = HERE / "snapshot"

TASK_ID = "W007-CLAIM42-INDEP-VERIFY-01"
CLAIM_ID = "w072-20260912T001917-claim-conclusion-poor"
CLASS_ID = "AF-WCC-SCALAR-SPH"

PINS = {
    "research_map/formulation_taxonomy.yaml": {
        "snapshot": "snapshot/formulation_taxonomy.276009f4f63d.yaml",
        "sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    },
    "ledger/theorems.jsonl": {
        "snapshot": "snapshot/theorems.ce42d205e761.jsonl",
        "sha256": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    },
    "ledger/citation_audit.csv": {
        "snapshot": "snapshot/citation_audit.315c19145065.csv",
        "sha256": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    },
}

# worker-072's reported numbers, for cross-check only (never used in the verdict)
W072_REPORTED = {
    "entries_bound": 10,
    "mechanically_conform_H1_H2_H3": 5,
    "genericity_H4_named": 0,
    "discharge_class_WCC_conclusion": 0,
}
# worker-072's per-entry H results, extracted from its own report
W072_PER_ENTRY_H = {
    "T-101": {"H1": True, "H2": True, "H3": True},
    "T-102": {"H1": True, "H2": True, "H3": False},
    "T-103": {"H1": True, "H2": True, "H3": True},
    "T-105": {"H1": True, "H2": True, "H3": True},
    "T-106": {"H1": True, "H2": True, "H3": False},
    "T-107": {"H1": True, "H2": True, "H3": False},
    "T-516": {"H1": True, "H2": True, "H3": True},
    "T-523": {"H1": True, "H2": True, "H3": False},
    "T-524": {"H1": True, "H2": True, "H3": True},
    "T-525": {"H1": True, "H2": True, "H3": False},
}

# ---------------------------------------------------------------- token rules
RX = {
    "scalar": re.compile(r"massless\s+scalar|scalar\s+field|scalar-field|scalar\s+wave", re.I),
    "dimension": re.compile(r"3\s*\+\s*1|four[- ]dimensional|4[- ]dimensional", re.I),
    "einstein": re.compile(r"einstein|lambda\s*=\s*0|field\s+equation", re.I),
    "spherical_raw": re.compile(r"spherical|SO\(3\)|2-sphere|two-sphere", re.I),
    "asymptotic": re.compile(
        r"asymptotically\s+flat|asymptotic\s+flatness|asymptotic[- ]flat|\bAF\b|null\s+infinity|I\s*\+|scri",
        re.I,
    ),
    # the narrower asymptotic-flatness token set that worker-072's table actually uses
    "asymptotic_spelled": re.compile(r"asymptotically\s+flat|asymptotic\s+flatness|asymptotic[- ]flat|\bAF\b", re.I),
    # positive genericity notions (what "names the class's genericity notion" needs)
    "genericity_positive": re.compile(
        r"comeager|co-meager|residual|dense[- ]open|open[- ]dense|dense\s+G|G_delta|"
        r"full[- ]measure|positive\s+measure|measure[- ]one|measure\s+one|"
        r"Baire[- ]generic|generic\s+set",
        re.I,
    ),
    "topology": re.compile(r"topolog|Baire|measure|norm|Sobolev|C\^|Fr[eé]chet", re.I),
    "genericity_negative_guard": re.compile(
        r"left\s+open|unresolved|must\s+be\s+supplied|not\s+(?:be\s+)?specified|no\s+genericity|"
        r"does\s+not\s+fix|open\s+in\s+the\s+quoted|to\s+be\s+fixed|separately|non-?generic|fine[- ]tuned",
        re.I,
    ),
    "negated_spherical": re.compile(r"non[-\s]?spherical|not\s+spherical|axisymmetric", re.I),
    "wcc": re.compile(r"cosmic\s+censorship|weak\s+cosmic|\bWCC\b", re.I),
}

H4_POSITIVE_FIELDS = ("genericity", "statement_exact", "statement")
H4_NEGATIVE_FIELDS = ("genericity", "scope_caveats", "assumptions", "does_not_imply", "falsifiers")


def now() -> str:
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def all_text(rec: dict) -> str:
    """Content text of a record.  Identifier fields (class_ids, theorem_id, id, source_ids,
    ledger_tags) are deliberately excluded so that class tokens like 'AF-WCC-SCALAR-SPH'
    cannot satisfy the content token rules (e.g. the 'AF' alias of asymptotically flat)."""
    parts = []
    for k in (
        "label", "statement_exact", "statement", "genericity", "regularity", "assumptions",
        "scope_caveats", "conclusion_type", "entry_kind", "evidence_level",
        "does_not_imply", "falsifiers", "hypotheses", "topology", "unresolved",
    ):
        v = rec.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        elif isinstance(v, dict):
            parts.append(json.dumps(v, ensure_ascii=False))
        else:
            parts.append(str(v))
    return "\n".join(parts)


def field_text(rec: dict, keys) -> str:
    parts = []
    for k in keys:
        v = rec.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return "\n".join(parts)


# Field set reconstructed for worker-072's rule: content fields, but NOT class_ids,
# identifiers, scope_caveats, or next_action.  This reconstruction reproduces its
# published per-entry H1/H2/H3 table exactly (see reconcile()).
W072_FIELDS = (
    "label", "statement_exact", "statement", "genericity", "regularity", "assumptions",
    "topology", "unresolved", "does_not_imply", "falsifiers", "hypotheses",
    "conclusion_type", "entry_kind", "evidence_level",
)


def w072_text(rec: dict) -> str:
    return field_text(rec, W072_FIELDS)


def class_ids_of(rec: dict) -> list:
    v = rec.get("class_ids")
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [t.strip() for t in re.split(r"[;,]", v) if t.strip()]
    return []


def conclusion_tokens_of(rec: dict) -> list:
    toks = []
    for k in ("conclusion_type", "conclusion_types"):
        v = rec.get(k)
        if isinstance(v, str):
            toks.append(v)
        elif isinstance(v, list):
            toks.extend(str(x) for x in v)
    return toks


def has_spherical(txt: str) -> bool:
    """True iff a non-negated spherical-symmetry token occurs."""
    cleaned = RX["negated_spherical"].sub(" ", txt)
    return bool(RX["spherical_raw"].search(cleaned))


def has_h4(rec: dict) -> dict:
    """Strict H4 test: an explicit genericity notion named with a topology in the
    entry's own genericity/statement fields and not guarded as open/unresolved."""
    pos_txt = field_text(rec, H4_POSITIVE_FIELDS)
    neg_txt = field_text(rec, H4_NEGATIVE_FIELDS)
    positive = bool(RX["genericity_positive"].search(pos_txt))
    topology = bool(RX["topology"].search(pos_txt))
    guarded = bool(RX["genericity_negative_guard"].search(neg_txt))
    return {
        "positive_genericity_notion": positive,
        "topology_token_in_positive_scope": topology,
        "negative_guard_present": guarded,
        "explicit_genericity_with_topology": positive and topology and not guarded,
    }


def classify(rec: dict) -> dict:
    txt = all_text(rec)
    wtxt = w072_text(rec)
    cids = class_ids_of(rec)
    bound = CLASS_ID in cids

    h1_scalar = bool(RX["scalar"].search(txt))
    h1_dim = bool(RX["dimension"].search(txt))
    h1_einstein = bool(RX["einstein"].search(txt))
    h2_strict = has_spherical(txt)
    h2_raw = bool(RX["spherical_raw"].search(txt))  # substring rule over the full content text
    h3 = bool(RX["asymptotic"].search(txt))
    h4 = has_h4(rec)
    ctoks = conclusion_tokens_of(rec)
    wcc_conclusion = any(t.strip() == "weak_cosmic_censorship" for t in ctoks)

    # reconstructed worker-072 rule, evaluated on its own scopes:
    #   H1/H2 scan the full record serialization (so the class id token SCALAR and the
    #   substring 'spherical' inside 'non-spherical' both count); H3 scans content fields
    #   with the spelled-out asymptotic-flatness tokens only.
    full = json.dumps({k: v for k, v in rec.items() if k != "_line"}, ensure_ascii=False)
    w1 = bool(RX["scalar"].search(full))
    w2 = bool(RX["spherical_raw"].search(full))
    w3 = bool(RX["asymptotic_spelled"].search(wtxt))

    h1_strict = h1_scalar and h1_dim and h1_einstein
    strict_h1h3 = h1_strict and h2_strict and h3
    w072_h1h3 = w1 and w2 and w3  # reconstructed worker-072 rule
    w072_h1h3_guarded = w1 and has_spherical(wtxt) and w3

    return {
        "theorem_id": rec.get("theorem_id") or rec.get("id"),
        "label": (rec.get("label") or "")[:140],
        "class_ids": cids,
        "bound_to_class": bound,
        "conclusion_tokens": ctoks,
        "checks": {
            "H1_scalar_massless": h1_scalar,
            "H1_spacetime_3p1": h1_dim,
            "H1_einstein_lambda0": h1_einstein,
            "H1_strict_all": h1_strict,
            "H1_worker072_scalar_only": w1,
            "H2_spherical_strict": h2_strict,
            "H2_spherical_raw_substring": w2,
            "H3_asymptotically_flat": h3,
            "H3_worker072_spelled": w3,
            **h4,
            "conclusion_type_weak_cosmic_censorship": wcc_conclusion,
            "wcc_mentioned_in_text": bool(RX["wcc"].search(txt)),
        },
        "H1_H3_strict": strict_h1h3,
        "H1_H3_worker072_rule": w072_h1h3,
        "H1_H3_worker072_rule_guarded": w072_h1h3_guarded,
        "qualifies_falsifier": strict_h1h3 and h4["explicit_genericity_with_topology"] and wcc_conclusion,
        "qualifies_falsifier_lenient_h2": (w1 and w2 and w3) and h4["explicit_genericity_with_topology"] and wcc_conclusion,
        "wcc_omission_candidate": (not bound) and strict_h1h3 and wcc_conclusion,
        "wcc_omission_candidate_lenient": (not bound) and w072_h1h3 and wcc_conclusion,
    }


def load_pinned() -> tuple:
    pins = {}
    for logical, meta in PINS.items():
        p = SNAP / Path(meta["snapshot"]).name
        got = sha256_file(p)
        pins[logical] = {
            "snapshot": str(p.relative_to(ROOT)),
            "expected_sha256": meta["sha256"],
            "measured_sha256": got,
            "match": got == meta["sha256"],
        }
    bad = [k for k, v in pins.items() if not v["match"]]
    if bad:
        raise SystemExit(f"BINDING FAILURE: snapshot hash mismatch for {bad}")

    f0 = yaml.safe_load(open(SNAP / "formulation_taxonomy.276009f4f63d.yaml"))
    cls = f0["classes"][CLASS_ID]
    hypotheses = {h["id"]: h["text"] for h in cls.get("hypotheses", [])}

    recs = []
    with open(SNAP / "theorems.ce42d205e761.jsonl") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rec["_line"] = ln
            recs.append(rec)

    with open(SNAP / "citation_audit.315c19145065.csv") as f:
        cit = f.read()

    live = {}
    for logical in PINS:
        lp = ROOT / logical
        ls = sha256_file(lp) if lp.exists() else None
        live[logical] = {
            "live_path": logical,
            "live_sha256": ls,
            "live_equals_pin": ls == PINS[logical]["sha256"],
        }
    return pins, cls, hypotheses, recs, cit, live


def scan(recs: list) -> dict:
    rows = [classify(r) for r in recs]
    bound = [r for r in rows if r["bound_to_class"]]
    return {
        "n_records": len(rows),
        "n_bound": len(bound),
        "n_bound_H1_H3_strict": sum(1 for r in bound if r["H1_H3_strict"]),
        "n_bound_H1_H3_worker072_rule": sum(1 for r in bound if r["H1_H3_worker072_rule"]),
        "n_bound_H1_H3_worker072_rule_guarded": sum(1 for r in bound if r["H1_H3_worker072_rule_guarded"]),
        "n_bound_genericity_named_strict": sum(1 for r in bound if r["checks"]["explicit_genericity_with_topology"]),
        "n_bound_wcc_conclusion": sum(1 for r in bound if r["checks"]["conclusion_type_weak_cosmic_censorship"]),
        "n_qualifying_falsifier_witnesses": sum(1 for r in rows if r["qualifies_falsifier"]),
        "n_qualifying_falsifier_witnesses_lenient_h2": sum(1 for r in rows if r["qualifies_falsifier_lenient_h2"]),
        "n_omission_candidates_H1H3_WCC_unbound": sum(1 for r in rows if r["wcc_omission_candidate"]),
        "n_omission_candidates_lenient_unbound": sum(1 for r in rows if r["wcc_omission_candidate_lenient"]),
        "bound_ids": [r["theorem_id"] for r in bound],
        "bound_H1_H3_strict_ids": [r["theorem_id"] for r in bound if r["H1_H3_strict"]],
        "bound_H1_H3_worker072_rule_ids": [r["theorem_id"] for r in bound if r["H1_H3_worker072_rule"]],
        "bound_genericity_strict_ids": [r["theorem_id"] for r in bound if r["checks"]["explicit_genericity_with_topology"]],
        "bound_wcc_ids": [r["theorem_id"] for r in bound if r["checks"]["conclusion_type_weak_cosmic_censorship"]],
        "qualifying_witnesses": [r for r in rows if r["qualifies_falsifier"]],
        "omission_candidates": [
            {"theorem_id": r["theorem_id"], "class_ids": r["class_ids"],
             "conclusion_tokens": r["conclusion_tokens"], "label": r["label"]}
            for r in rows if r["wcc_omission_candidate"]
        ],
        "per_record": rows,
    }


def controls(recs: list, hypotheses: dict) -> dict:
    base = {
        "theorem_id": "CTRL-POS",
        "label": "CTRL: spherical massless scalar collapse, asymptotic flatness, comeager genericity",
        "statement_exact": (
            "For a comeager (Baire-residual) set of asymptotically flat 3+1 dimensional "
            "spherically symmetric initial data for the Einstein equations coupled to a "
            "massless scalar field, the MGHD is future null infinity complete and no "
            "singularity is visible from I+."
        ),
        "genericity": "comeager in the Baire topology on the symmetry-reduced data space",
        "conclusion_type": "weak_cosmic_censorship",
        "class_ids": [CLASS_ID],
        "evidence_level": "peer-reviewed",
        "source_ids": ["SRC-CTRL"],
    }

    def with_patch(patch):
        m = dict(base)
        m.update(patch)
        return m

    mutation_specs = [
        # name, patch, expected qualifies_falsifier, expected omission_candidate
        ("no_scalar_token", {
            "label": "CTRL: spherical perfect-fluid collapse with comeager genericity",
            "statement_exact": base["statement_exact"].replace("massless scalar field", "perfect fluid"),
        }, False, False),
        ("no_spherical_token", {
            "label": "CTRL: axisymmetric massless scalar collapse with comeager genericity",
            "statement_exact": base["statement_exact"].replace("spherically symmetric", "axisymmetric"),
        }, False, False),
        ("no_asymptotic_token", {
            "label": "CTRL: spherical massless scalar collapse with comeager genericity",
            "statement_exact": base["statement_exact"].replace("asymptotically flat", "compact").replace(
                "future null infinity", "the conformal boundary").replace("I+", "the horizon"),
        }, False, False),
        ("no_genericity_notion", {
            "label": "CTRL: spherical massless scalar collapse, genericity not specified",
            "statement_exact": (
                "For asymptotically flat 3+1 dimensional spherically symmetric initial data for the "
                "Einstein equations coupled to a massless scalar field, the development is complete at I+."
            ),
            "genericity": "not specified",
        }, False, False),
        ("wrong_conclusion_type", {"conclusion_type": "strong_cosmic_censorship"}, False, False),
        ("unbound_but_conforming", {"class_ids": ["AF-SCC-C2-VAC-GEN"]}, True, True),
    ]
    mutants = {}
    for name, patch, exp_q, exp_om in mutation_specs:
        c = classify(with_patch(patch))
        mutants[name] = {
            "expected_qualifying": exp_q,
            "got_qualifying": c["qualifies_falsifier"],
            "expected_omission_candidate": exp_om,
            "got_omission_candidate": c["wcc_omission_candidate"],
            "pass": c["qualifies_falsifier"] is exp_q and c["wcc_omission_candidate"] is exp_om,
            "H1_H3_strict": c["H1_H3_strict"],
            "H4": c["checks"]["explicit_genericity_with_topology"],
            "wcc": c["checks"]["conclusion_type_weak_cosmic_censorship"],
        }
    pos = classify(base)
    d1 = hashlib.sha256(json.dumps([classify(r) for r in recs], sort_keys=True).encode()).hexdigest()
    d2 = hashlib.sha256(json.dumps([classify(r) for r in recs], sort_keys=True).encode()).hexdigest()
    return {
        "positive_fixture_qualifies": pos["qualifies_falsifier"],
        "positive_fixture_expected": True,
        "positive_fixture_pass": pos["qualifies_falsifier"] is True,
        "mutation_controls": mutants,
        "mutation_controls_all_pass": all(m["pass"] for m in mutants.values()),
        "determinism_digest_1": d1,
        "determinism_digest_2": d2,
        "determinism_pass": d1 == d2,
        "h4_rule_note": (
            "F0 H4 is machine_checkable=False and the class records genericity_value_status="
            "unresolved_pending_L1; the H4 test detects whether an entry NAMES a positive "
            "genericity notion with a topology in its own genericity/statement fields and does "
            "not guard it as open/unresolved. It cannot certify that a named notion is coherent."
        ),
        "h2_rule_note": (
            "worker-072's per-entry table passes T-106 (label: 'non-spherical Einstein-scalar "
            "naked singularities') on H2, which is a substring hazard; the strict rule here "
            "negation-guards 'non-spherical'/'not spherical'/'axisymmetric'."
        ),
        "f0_hypotheses_used": hypotheses,
    }


def reconcile(primary: dict, rows: list) -> dict:
    """Compare the reconstructed worker-072 rule with its own published per-entry table."""
    got = {}
    for r in rows:
        if r["bound_to_class"]:
            got[r["theorem_id"]] = {
                "H1": r["checks"]["H1_worker072_scalar_only"],
                "H2": r["checks"]["H2_spherical_raw_substring"],
                "H3": r["checks"]["H3_worker072_spelled"],
            }
    mismatches = []
    for tid, exp in W072_PER_ENTRY_H.items():
        g = got.get(tid)
        if g != exp:
            mismatches.append({"theorem_id": tid, "worker_072": exp, "replication": g})
    return {
        "rule_reconstructed": (
            "H1 = /scalar/i over the full record serialization (satisfied by the class-id token "
            "SCALAR for every bound entry); H2 = unguarded /spherical/i substring over the full "
            "serialization (satisfied by 'non-spherical' for T-105/T-106); H3 = spelled "
            "'asymptotically flat'/'asymptotic flatness' over content fields minus "
            "class_ids/identifiers/scope_caveats/next_action"
        ),
        "per_entry_mismatches": mismatches,
        "replication_agrees": not mismatches,
        "h2_substring_hazard_ids": [
            r["theorem_id"] for r in rows
            if r["bound_to_class"] and r["checks"]["H2_spherical_raw_substring"] and not r["checks"]["H2_spherical_strict"]
        ],
        "h1_vacuity_ids": [
            r["theorem_id"] for r in rows
            if r["bound_to_class"] and r["checks"]["H1_worker072_scalar_only"] and not r["checks"]["H1_strict_all"]
        ],
        "strict_vs_reconstructed_note": (
            "the claim's sub-assertion '5/10 mechanically in-class' is rule-dependent: the "
            "reconstructed worker-072 rule gives 5/10, the strict rule used here gives "
            f"{primary['n_bound_H1_H3_strict']}/10. The verdict-relevant clauses (no WCC "
            "conclusion, no H4 naming) are identical under both rules."
        ),
    }


def main() -> int:
    t0 = now()
    pins, cls, hypotheses, recs, cit, live = load_pinned()
    primary = scan(recs)
    ctrl = controls(recs, hypotheses)
    rec = reconcile(primary, primary["per_record"])

    witnesses = primary["qualifying_witnesses"]
    if witnesses:
        verdict = "FALSIFIED"
        reason = ("qualifying witness(es) found: entry passes H1-H3, names a genericity notion with "
                  "a topology, and carries conclusion_type=weak_cosmic_censorship")
    elif primary["n_bound"] == 0:
        verdict = "INCONCLUSIVE"
        reason = "no ledger entry is bound to the class at the pinned hash, so the claim has no population"
    elif primary["n_bound_wcc_conclusion"] > 0 or primary["n_omission_candidates_H1H3_WCC_unbound"] > 0:
        verdict = "PARTIAL"
        reason = ("no full H4 witness, but WCC-conclusion/omission candidates exist; the claim's "
                  "'no entry discharges the conclusion' clause is not clean")
    else:
        verdict = "CONFIRMED"
        reason = ("at the pinned bytes: 0/10 bound entries carry conclusion_type=weak_cosmic_censorship; "
                  "0/10 name a positive genericity notion with a topology in their own genericity/"
                  "statement fields; 0 falsifier witnesses and 0 omission candidates in the full ledger")

    agreement = {
        "entries_bound": primary["n_bound"] == W072_REPORTED["entries_bound"],
        "H1_H3_count_under_worker072_rule": primary["n_bound_H1_H3_worker072_rule"] == W072_REPORTED["mechanically_conform_H1_H2_H3"],
        "H1_H3_count_strict": primary["n_bound_H1_H3_strict"] == W072_REPORTED["mechanically_conform_H1_H2_H3"],
        "genericity_named": primary["n_bound_genericity_named_strict"] == W072_REPORTED["genericity_H4_named"],
        "wcc_conclusion": primary["n_bound_wcc_conclusion"] == W072_REPORTED["discharge_class_WCC_conclusion"],
    }

    secondary = None
    live_theorems = ROOT / "ledger/theorems.jsonl"
    if live_theorems.exists() and not live["ledger/theorems.jsonl"]["live_equals_pin"]:
        lrecs = []
        with open(live_theorems) as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                r["_line"] = ln
                lrecs.append(r)
        ls = scan(lrecs)
        secondary = {
            "live_sha256": live["ledger/theorems.jsonl"]["live_sha256"],
            "n_records": ls["n_records"], "n_bound": ls["n_bound"],
            "n_bound_H1_H3_strict": ls["n_bound_H1_H3_strict"],
            "n_bound_H1_H3_worker072_rule": ls["n_bound_H1_H3_worker072_rule"],
            "n_bound_genericity_named_strict": ls["n_bound_genericity_named_strict"],
            "n_bound_wcc_conclusion": ls["n_bound_wcc_conclusion"],
            "n_qualifying_falsifier_witnesses": ls["n_qualifying_falsifier_witnesses"],
            "n_omission_candidates_H1H3_WCC_unbound": ls["n_omission_candidates_H1H3_WCC_unbound"],
            "note": ("secondary observation only; the claim is stated at the pinned hash, so a "
                     "difference here is drift/supersession, not a falsification of the claim"),
        }

    report = {
        "schema_version": "w007-claim-verify/1",
        "task_id": TASK_ID,
        "created_at": t0,
        "finished_at": now(),
        "actor": "worker-007",
        "role": "bounded execution worker",
        "kind": "independent verification of an open map claim",
        "claim_under_test": CLAIM_ID,
        "claim_node": "L1",
        "class_ids": [CLASS_ID],
        "gate_context": "G-LIT / G-FORM (evidence only; no gate verdict claimed)",
        "claim_falsifier_verbatim": (
            "A class-bound ledger entry that passes H1-H3, names an explicit genericity notion with "
            "topology and primary-source scope, and carries conclusion_type=weak_cosmic_censorship; or "
            "a class-conforming WCC entry omitted from the bound set."
        ),
        "pins": pins,
        "live_check": live,
        "f0_class_definition": {
            "class_id": CLASS_ID,
            "label": cls.get("label"),
            "axes": cls.get("axes"),
            "genericity_value_status": cls.get("genericity_value_status"),
            "conclusion_type": cls.get("conclusion", {}).get("type"),
            "hypotheses": hypotheses,
        },
        "primary_scan_at_pin": primary,
        "worker_072_rule_reconciliation": rec,
        "controls": ctrl,
        "cross_check_worker_072_reported": W072_REPORTED,
        "cross_check_agreement": agreement,
        "secondary_scan_live_ledger": secondary,
        "verdict": verdict,
        "verdict_reason": reason,
        "verdict_rule": (
            "FALSIFIED iff a qualifying witness exists (H1-H3 + explicit genericity with topology + "
            "conclusion_type=weak_cosmic_censorship, bound or unbound); CONFIRMED iff no bound entry "
            "has a WCC conclusion, no bound entry names H4, and no unbound H1-H3+WCC omission candidate "
            "exists; PARTIAL if omission/WCC candidates exist without a full H4 witness; INCONCLUSIVE "
            "if the bound population is empty."
        ),
        "non_claims": [
            "Not a gate verdict; not a node transition; worker events cannot set done/passed.",
            "Does not assert any physics; classification is token-mechanical over entry metadata.",
            "Does not certify that a named genericity notion is coherent (F0 H4 is not machine-checkable).",
            "No canonical artifact was edited; snapshots under snapshot/ are read-only copies.",
        ],
        "next_falsifier": (
            "Re-run verify_claim42.py against a later pinned ledger/taxonomy revision; the claim is "
            "falsified if any ledger entry passes H1-H3, names a genericity notion with a topology, and "
            "carries conclusion_type=weak_cosmic_censorship; or if an unbound class-conforming WCC entry "
            "exists. A revision change alone supersedes (does not falsify) this verification."
        ),
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    if not cit.strip():
        print("WARNING: citation_audit snapshot is empty", file=sys.stderr)
    print(json.dumps({
        "verdict": verdict,
        "bound": primary["n_bound"],
        "bound_H1_H3_strict": primary["n_bound_H1_H3_strict"],
        "bound_H1_H3_worker072_rule": primary["n_bound_H1_H3_worker072_rule"],
        "bound_genericity_named_strict": primary["n_bound_genericity_named_strict"],
        "bound_wcc": primary["n_bound_wcc_conclusion"],
        "falsifier_witnesses": primary["n_qualifying_falsifier_witnesses"],
        "falsifier_witnesses_lenient_h2": primary["n_qualifying_falsifier_witnesses_lenient_h2"],
        "omission_candidates": primary["n_omission_candidates_H1H3_WCC_unbound"],
        "worker072_rule_replication_agrees": rec["replication_agrees"],
        "h2_substring_hazard_ids": rec["h2_substring_hazard_ids"],
        "controls_pass": ctrl["positive_fixture_pass"] and ctrl["mutation_controls_all_pass"] and ctrl["determinism_pass"],
        "agreement_with_w072": agreement,
        "report": "artifacts/worker-007/claim42_verify/report.json",
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
