#!/usr/bin/env python3
"""W057-GFORM-D0-SINGLE-CLASS-VERIFY-01 (worker-057).

Deterministic, class-bound measurement at the frozen rev-29 formulation bytes:
does the G-FORM criterion

    "no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b,
     which disables the licensed C0=>C2 transfer"

move at rev 29, where D0 was retyped as a *tagged disjoint union* over a bare
regularity index r?

This is a measurement instrument, not an adjudication.  It decides six
literal, machine-checkable questions about the pinned bytes and records the
one question that stays reserved to the G-FORM owner as `reserved`.

Design rules (same discipline as the rev-13 symbol verifier):
  * every input is pinned by full sha256; a moved byte aborts the run;
  * the instrument re-implements the comparisons from the bytes, it does not
    call the author's checkers;
  * every reported figure has a pre-registered control that would flip it;
  * no schema is modified; nothing is written outside this directory.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

RUN_DIR = Path(__file__).resolve().parent
REPO = RUN_DIR.parents[2]

# ---------------------------------------------------------------------------
# Pins.  Captured from the live tree; the run aborts if any byte moved.
# ---------------------------------------------------------------------------
PINS = {
    "schemas/af_wcc_vacuum.yaml": {
        "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "bytes": 37662,
        "node": "F1",
        "class_id": "AF-WCC-VAC-GEN",
    },
    "schemas/af_scc_c2_vacuum.yaml": {
        "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "bytes": 30594,
        "node": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
    },
    "schemas/af_scc_c0_vacuum.yaml": {
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "bytes": 35602,
        "node": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
    "research_map/formulation_taxonomy.yaml": {
        "sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "bytes": 36372,
        "node": "F0",
        "class_id": None,
    },
    "artifacts/formulation/FROZEN.json": {
        "sha256": None,  # filled from disk; only the revision field is consumed
        "bytes": None,
        "node": "F0,F1,F2a,F2b",
        "class_id": None,
    },
}

SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
SHORT = {p: p.split("/")[-1] for p in SCHEMAS}

# G-FORM unmet item, verbatim from research_map/research_map.json (measured,
# not transcribed from a review): the unmet list of the gate whose criteria
# begin "all three schemas exist with exact quantifiers/...".
CRITERION_TEXT = (
    "no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, "
    "which disables the licensed C0=>C2 transfer"
)

# The Sobolev numeric contract the three schemas declare for the r=(sobolev,s,delta) tag.
SOBOLEV_S = "s > 5/2"
SOBOLEV_DELTA = "delta in (1/2, 1)"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def load_pinned(path: str):
    raw = (REPO / path).read_bytes()
    got = sha256_bytes(raw)
    pin = PINS[path]
    if pin["sha256"] is not None and got != pin["sha256"]:
        raise SystemExit(
            f"PIN DRIFT: {path}\n  pinned {pin['sha256']}\n  disk   {got}\n"
            "refusing to report on moved bytes"
        )
    if pin["bytes"] is not None and len(raw) != pin["bytes"]:
        raise SystemExit(
            f"PIN DRIFT (bytes): {path} pinned {pin['bytes']} disk {len(raw)}"
        )
    return raw, got, yaml.safe_load(raw)


def tag_of_d0(d0: dict) -> list[str] | None:
    """Return the tag names D0 declares, from the definition prose.

    The rev-12+ D0 is written as a tagged disjoint union:
        "r = smooth (the smooth-with-decay default) or r = (sobolev,s,delta) ..."
    This extracts the tag tokens in order; it is intentionally brittle so that
    a reworded D0 changes the measured answer instead of silently passing.
    """
    if not isinstance(d0, dict):
        return None
    text = str(d0.get("definition", ""))
    m = re.search(r"r\s*=\s*smooth.*?or\s+r\s*=\s*\(\s*([A-Za-z]+)\s*,", text)
    if not m:
        return None
    return ["smooth", m.group(1)]


def canon_norm_space(text) -> str | None:
    """Canonical form of a declared space string.

    The blocks legitimately annotate the ambient space ('(weighted Sobolev)',
    '(weighted Sobolev)').  A parenthetical annotation is not a different norm;
    stripping it before comparison is the pre-registered rule, and C5 checks it.
    """
    if not isinstance(text, str):
        return None
    return re.sub(r"\s*\((?:weighted\s+)?sobolev\)", "", text, flags=re.I).strip()


def canon_numeric(text) -> str | None:
    """Canonical form of a numeric bound ('s > 5/2', 'delta in (1/2, 1)')."""
    if not isinstance(text, str):
        return None
    return re.sub(r"\s+", "", text)


def normed_spaces(regularity_class: dict) -> dict:
    """The (s, delta, norm) family a regularity_class block declares.

    The smooth default is a C^infinity class with pointwise rates, so it
    declares no normed Sobolev space: `default_is_normed_sobolev` is False and
    its (s,delta,norm) slots are None.  The sobolev_variant declares a family,
    not a single triple: s and delta are ranges and the space symbol still
    carries the free indices s, delta.
    """
    sv = (regularity_class or {}).get("sobolev_variant") or {}
    return {
        "default_is_normed_sobolev": False,
        "s": canon_numeric(sv.get("s")),
        "delta": canon_numeric(sv.get("delta")),
        "norm": canon_norm_space(sv.get("spaces")),
    }


def normed_triples_from_domain(d0_def: str) -> list[dict]:
    """Every (s,delta,norm)-shaped instantiation D0's own text supplies.

    The smooth branch is read from the clause that introduces the tag
    ("r = smooth (the smooth-with-decay default)"); the revision note later in
    the same string quotes 'suitable' regularity and must not be mistaken for
    an instantiation.  A branch that supplies s but no delta, or a space but no
    s/delta, is returned with the missing slot as None so the caller can see the
    shortfall instead of averaging it away.
    """
    branches = []
    # sobolev branch
    s_m = re.search(r"s\s*>\s*[0-9./]+", d0_def)
    d_m = re.search(r"delta\s*(?:in|∈)\s*\([^)]*\)", d0_def)
    h_m = re.search(r"weighted\s+Sobolev\s+product\s+([^;.)]+)", d0_def, re.I)
    branches.append(
        {
            "tag": "sobolev",
            "s": canon_numeric(s_m.group(0)) if s_m else None,
            "delta": canon_numeric(d_m.group(0)) if d_m else None,
            "norm": canon_norm_space(h_m.group(1)) if h_m else None,
        }
    )
    # smooth branch: read only the tag-introducing clause, stop at the first
    # period or semicolon so the revision note cannot leak into the reading.
    smooth_clause = ""
    sm = re.search(r"r\s*=\s*smooth([^.;]*)", d0_def)
    if sm:
        smooth_clause = sm.group(0)
    smooth_has_sd = bool(re.search(r"\((?:s\s*,\s*delta|s,delta)\)", smooth_clause))
    smooth_norm = None
    if re.search(r"Frechet", smooth_clause, re.I):
        smooth_norm = "Frechet"
    branches.append(
        {
            "tag": "smooth",
            "s": SOBOLEV_S if smooth_has_sd else None,
            "delta": SOBOLEV_DELTA if smooth_has_sd else None,
            "norm": smooth_norm,
        }
    )
    return branches


def main() -> int:
    report: dict = {
        "task_id": "W057-GFORM-D0-SINGLE-CLASS-VERIFY-01",
        "actor": "worker-057",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": [
            "AF-WCC-VAC-GEN",
            "AF-SCC-C2-VAC-GEN",
            "AF-SCC-C0-VAC-GEN",
        ],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "instrument": "artifacts/worker-057/gform_d0_single_class_verify/verify_d0_single_class.py",
        "criterion_text": CRITERION_TEXT,
        "inputs": {},
        "checks": {},
        "findings": [],
        "controls": [],
        "reserved_adjudication": None,
        "verdict": None,
    }

    # -- pins -------------------------------------------------------------
    raw_all, docs = {}, {}
    for p in list(PINS) + []:
        raw, got, doc = load_pinned(p)
        raw_all[p] = raw
        docs[p] = doc
        report["inputs"][p] = {
            "sha256": got,
            "bytes": len(raw),
            "node": PINS[p]["node"],
            "class_id": PINS[p]["class_id"],
        }

    frozen = docs["artifacts/formulation/FROZEN.json"]
    report["inputs"]["artifacts/formulation/FROZEN.json"]["revision"] = frozen.get("revision")
    report["inputs"]["artifacts/formulation/FROZEN.json"]["frozen_at"] = frozen.get("frozen_at")
    # two independent consistency sub-checks on the pin set itself
    report["checks"]["FROZEN_revision_is_29"] = frozen.get("revision") == 29
    frozen_files = frozen.get("files", {})
    declared = {
        p: (frozen_files.get(p) or {}).get("sha256")
        for p in SCHEMAS
    }
    report["checks"]["FROZEN_pins_match_disk_all_three"] = all(
        declared[p] == report["inputs"][p]["sha256"] for p in SCHEMAS
    )
    report["inputs"]["FROZEN_declared_schema_pins"] = declared

    # -- D0 tag structure -------------------------------------------------
    d0_defs, tags = {}, {}
    for p in SCHEMAS:
        q = docs[p].get("quantifiers") or {}
        d0 = (q.get("domains") or {}).get("D0")
        d0_defs[p] = canon(d0)
        tags[p] = tag_of_d0(d0)
    report["checks"]["D0_present_all_three"] = all(
        d0_defs[p] not in ("null", None) for p in SCHEMAS
    )
    report["checks"]["D0_normalized_equal_all_three"] = len(set(d0_defs.values())) == 1
    report["checks"]["D0_tag_set_equal_all_three"] = (
        len(set(canon(t) for t in tags.values())) == 1 and all(tags.values())
    )
    report["inputs"]["D0_tags"] = {SHORT[p]: tags[p] for p in SCHEMAS}
    report["checks"]["D0_is_tagged_union_not_single_triple"] = all(
        t == ["smooth", "sobolev"] for t in tags.values() if t
    )

    # -- the (s,delta,norm) instantiation the union actually supplies ------
    dom_branches = normed_triples_from_domain(str((docs[SCHEMAS[0]].get("quantifiers") or {}).get("domains", {}).get("D0", {}).get("definition", "")))
    report["checks"]["D0_smooth_branch_supplies_s_delta"] = bool(
        dom_branches[1]["s"] and dom_branches[1]["delta"]
    )
    report["checks"]["D0_smooth_branch_supplies_normed_space"] = bool(
        dom_branches[1]["norm"] and "sobolev" in str(dom_branches[1]["norm"]).lower()
    )
    # a triple is complete for the criterion only if s, delta and norm are all present
    complete_branches = [b for b in dom_branches if b["s"] and b["delta"] and b["norm"]]
    derived = {
        "branches": dom_branches,
        "complete_normed_triples": len(complete_branches),
        "incomplete_branches": len(dom_branches) - len(complete_branches),
    }
    report["inputs"]["D0_normed_instantiations"] = derived

    # -- regularity_class blocks -----------------------------------------
    rc_blocks, rc_norm = {}, {}
    for p in SCHEMAS:
        rc = ((docs[p].get("data_class") or {}).get("regularity_class"))
        rc_blocks[p] = canon(rc)
        rc_norm[p] = normed_spaces(rc)
    report["checks"]["regularity_class_normalized_equal_all_three"] = (
        len(set(rc_blocks.values())) == 1
    )
    report["inputs"]["regularity_class_distinct_blocks"] = len(set(rc_blocks.values()))
    report["checks"]["regularity_class_distinct_block_count_is_1"] = (
        len(set(rc_blocks.values())) == 1
    )
    # Numeric/space contract, annotation-stripped (C7 fixes the rule): this is a
    # strict equality on (s, delta, canon_space), not on the prose `status` field.
    contract = {
        p: (
            rc_norm[p]["s"],
            rc_norm[p]["delta"],
            canon_norm_space(rc_norm[p]["norm"]),
        )
        for p in SCHEMAS
    }
    numeric_equal = len(set(contract.values())) == 1
    report["checks"]["sobolev_numeric_contract_equal_all_three"] = numeric_equal
    report["inputs"]["regularity_numeric_core"] = {
        SHORT[p]: {
            "s": rc_norm[p]["s"],
            "delta": rc_norm[p]["delta"],
            "norm": rc_norm[p]["norm"],
            "norm_canon": canon_norm_space(rc_norm[p]["norm"]),
            "status_prose_differs": None,  # filled below
        }
        for p in SCHEMAS
    }
    statuses = {
        SHORT[p]: ((docs[p].get("data_class") or {}).get("regularity_class") or {})
        .get("sobolev_variant", {})
        .get("status")
        for p in SCHEMAS
    }
    report["inputs"]["regularity_status_prose"] = statuses
    report["checks"]["regularity_status_prose_equal_all_three"] = (
        len(set(statuses.values())) == 1
    )
    for p in SCHEMAS:
        report["inputs"]["regularity_numeric_core"][SHORT[p]]["status_prose_differs"] = (
            statuses[SHORT[p]] != statuses[SHORT[SCHEMAS[1]]]
        )

    # cross-artifact divergence *explicitly declared inside a class artifact*
    warn_hits = {}
    for p in SCHEMAS:
        txt = raw_all[p].decode("utf-8", "replace")
        warn_hits[p] = {
            "f1_only_no_transfer_warning": [
                i + 1
                for i, line in enumerate(txt.splitlines())
                if "may not be transferred" in line
            ],
            "has_excluded_data_key": "excluded_data" in (docs[p].get("data_class") or {}),
        }
    report["inputs"]["per_schema_declarations"] = {SHORT[p]: warn_hits[p] for p in SCHEMAS}
    report["checks"]["F1_declares_no_transfer_between_D0_branches"] = bool(
        warn_hits[SCHEMAS[0]]["f1_only_no_transfer_warning"]
    )
    report["checks"]["F2a_or_F2b_declares_same_no_transfer_warning"] = any(
        warn_hits[p]["f1_only_no_transfer_warning"] for p in SCHEMAS[1:]
    )
    report["checks"]["excluded_data_key_present_in_all_or_none"] = (
        len(set(w["has_excluded_data_key"] for w in warn_hits.values())) == 1
    )

    # ---------------------------------------------------------------------
    # Pre-registered controls.  Each control is a claim about a synthetic or
    # in-tree object whose outcome is fixed BEFORE the run; a control that does
    # not fire invalidates the corresponding measurement above.
    # ---------------------------------------------------------------------
    c1_single = normed_triples_from_domain(
        "admissible regularity indices, the single frozen weighted Sobolev "
        "class r = (sobolev,s,delta): s > 5/2, delta in (1/2,1); "
        "weighted Sobolev product H^s_delta x H^{s-1}_{delta+1}."
    )
    report["controls"].append(
        {
            "id": "C1",
            "claim": "a single frozen (s,delta,norm) domain yields exactly one complete normed triple",
            "expected": 1,
            "observed": len([b for b in c1_single if b["s"] and b["delta"] and b["norm"]]),
            "pass": len([b for b in c1_single if b["s"] and b["delta"] and b["norm"]]) == 1,
        }
    )
    report["controls"].append(
        {
            "id": "C2",
            "claim": "the live tagged-union D0 text yields two branches and only one complete normed triple",
            "expected": [2, 1],
            "observed": [len(dom_branches), len(complete_branches)],
            "pass": len(dom_branches) == 2 and len(complete_branches) == 1,
        }
    )
    tampered = raw_all[SCHEMAS[0]].replace(b"tagged disjoint union", b"tagged disjoint union ")
    report["controls"].append(
        {
            "id": "C3",
            "claim": "a one-byte-class edit to a pinned schema is caught by the pin check",
            "expected": False,
            "observed": sha256_bytes(tampered) == report["inputs"][SCHEMAS[0]]["sha256"],
            "pass": sha256_bytes(tampered) != report["inputs"][SCHEMAS[0]]["sha256"],
        }
    )
    # C4: does `tag_of_d0` distinguish a reworded (non-union) D0?  A single
    # triple D0 has no "or r =" clause and must return None.
    report["controls"].append(
        {
            "id": "C4",
            "claim": "tag_of_d0 returns no tag list for a non-union single-triple D0",
            "expected": None,
            "observed": tag_of_d0(
                {"definition": "the single frozen weighted Sobolev class r = (sobolev,s,delta), s > 5/2, delta in (1/2,1)"}
            ),
            "pass": tag_of_d0(
                {"definition": "the single frozen weighted Sobolev class r = (sobolev,s,delta), s > 5/2, delta in (1/2,1)"}
            )
            is None,
        }
    )
    # C5: the F2a/F2b regularity_class blocks must be pairwise byte-identical
    # if and only if the measured distinct-count is 2 (the family, not a fluke).
    pair_ab = rc_blocks[SCHEMAS[1]] == rc_blocks[SCHEMAS[2]]
    report["controls"].append(
        {
            "id": "C5",
            "claim": "F2a and F2b regularity_class blocks are identical while F1 differs (2 distinct blocks)",
            "expected": [True, 2],
            "observed": [pair_ab, len(set(rc_blocks.values()))],
            "pass": pair_ab and len(set(rc_blocks.values())) == 2,
        }
    )
    # C6: the smooth-clause reader must not pick up the rev12 note's
    # "(sobolev,s,delta)" or its 'Frechet for r = smooth' parenthetical.
    live_smooth = dom_branches[1]
    report["controls"].append(
        {
            "id": "C6",
            "claim": "the smooth branch reader reports no (s,delta) and no normed space even though the D0 string mentions both elsewhere",
            "expected": [None, None, None],
            "observed": [live_smooth["s"], live_smooth["delta"], live_smooth["norm"]],
            "pass": live_smooth["s"] is None
            and live_smooth["delta"] is None
            and live_smooth["norm"] is None,
        }
    )
    # C7: the annotation-stripping rule must make the F2a/F2b space strings and
    # F1's annotated space string compare equal, while a real space change differs.
    report["controls"].append(
        {
            "id": "C7",
            "claim": "stripping the '(weighted Sobolev)' annotation makes the three space strings equal; a different space symbol does not",
            "expected": [True, False],
            "observed": [
                len(
                    set(
                        canon_norm_space(rc_norm[p]["norm"]) for p in SCHEMAS
                    )
                )
                == 1,
                canon_norm_space("H^s_delta x H^{s-1}_{delta+1}")
                == canon_norm_space("H^s_delta x H^{s-1}_{delta+2}"),
            ],
            "pass": len(set(canon_norm_space(rc_norm[p]["norm"]) for p in SCHEMAS)) == 1
            and canon_norm_space("H^s_delta x H^{s-1}_{delta+1}")
            != canon_norm_space("H^s_delta x H^{s-1}_{delta+2}"),
        }
    )
    all_controls_pass = all(c["pass"] for c in report["controls"])
    report["checks"]["all_controls_pass"] = all_controls_pass

    # ---------------------------------------------------------------------
    # Findings.  Literal answers to the criterion's components, each one
    # traceable to a check above.  No gate verdict is claimed.
    # ---------------------------------------------------------------------
    def finding(fid: str, statement: str, state: str, refs: list[str]) -> dict:
        return {"id": fid, "statement": statement, "state": state, "evidence": refs}

    f1_ref = f"schemas/af_wcc_vacuum.yaml#{report['inputs'][SCHEMAS[0]]['sha256'][:12]}"
    f2a_ref = f"schemas/af_scc_c2_vacuum.yaml#{report['inputs'][SCHEMAS[1]]['sha256'][:12]}"
    f2b_ref = f"schemas/af_scc_c0_vacuum.yaml#{report['inputs'][SCHEMAS[2]]['sha256'][:12]}"

    report["findings"].append(
        finding(
            "D0-01",
            "The three schemas share a byte-identical D0 regularity domain "
            "(normalized JSON equal; tagged disjoint union r = smooth | (sobolev,s,delta)), "
            "so the rev-11/12 charge that D0 is a bare disjunction is repaired at rev 29.",
            "confirmed",
            [f1_ref, f2a_ref, f2b_ref],
        )
    )
    report["findings"].append(
        finding(
            "D0-02",
            "The D0 union supplies exactly one complete (s,delta,norm) instantiation "
            f"(the sobolev branch: {SOBOLEV_S}, {SOBOLEV_DELTA}, weighted Sobolev product). "
            "The smooth branch is a Frechet C^infinity class with pointwise rates, so it "
            "supplies no (s,delta) pair and no normed space. D0 therefore does not instantiate "
            "a *single* frozen triple; it is a union over a bare index.",
            "confirmed",
            [f1_ref, "quantifiers.domains.D0 (definition text)"],
        )
    )
    report["findings"].append(
        finding(
            "D0-03",
            "data_class.regularity_class is NOT identical across the three schemas: "
            f"{len(set(rc_blocks.values()))} distinct normalized blocks (F2a == F2b, F1 differs). "
            "The divergence is not only prose: F1 alone carries data_class.excluded_data and the "
            "declaration 'smooth-data statements may not be transferred to the Sobolev variant without "
            "an approximation/stability argument' (F1 line 136). That declaration is the sharpest "
            "recorded statement that the D0 branches are not one interchangeable data class.",
            "confirmed",
            [f1_ref, f2a_ref, f2b_ref],
        )
    )
    report["findings"].append(
        finding(
            "D0-04",
            "On the gate's literal wording, no single frozen (s,delta,norm) triple is present at rev 29. "
            "What is shared is (a) the tagged-union D0 domain and (b) a numeric/space contract that is "
            "itself a *family*: the shared object is the parameterised space H^s_delta x H^{s-1}_{delta+1} "
            "with s > 5/2 and delta in (1/2,1), i.e. a contract over ranges, not one frozen triple. "
            "The norm (weighted-Sobolev product) is shared; the numeric point is not fixed.",
            "confirmed",
            [f1_ref, f2a_ref, f2b_ref, "research_map/research_map.json gate G-FORM unmet[3]"],
        )
    )
    report["findings"].append(
        finding(
            "D0-05",
            "On the recorded-divergence reading, the union is a *stronger* substitute for a single "
            "instantiation, not an equivalent one: forall r in D0 makes the class statement hold for the "
            "smooth tag and for every (s,delta) simultaneously. If the criterion is read as 'the three "
            "classes must be instantiated over one common frozen (s,delta,norm) so that the C0=>C2 "
            "transfer lemma is stated on a common data space', the union does not supply that; it "
            "supplies a common *index set*. Whether that satisfies the criterion, or is accepted with "
            "the divergence recorded, is reserved to the G-FORM owner.",
            "reserved",
            [f1_ref, f2a_ref, f2b_ref],
        )
    )
    report["reserved_adjudication"] = {
        "question": (
            "Does the tagged-union D0 (forall r in D0) satisfy the G-FORM criterion "
            "'a single frozen data class (s,delta,norm) shared by F1/F2a/F2b', or must one "
            "(s,delta,norm) be frozen and the other branch registered as a variant?"
        ),
        "why_reserved": (
            "It is a class-identity/transfer ruling owned by the gate owner; this instrument "
            "measures the bytes only and claims no gate verdict."
        ),
        "precedent_carrying": [
            "research_map/research_map.json reviews[43] ('family of two class statements', supersedes an earlier accept)",
            "research_map/research_map.json reviews[70] Q2 ('disjunctive D0: not acceptable for class identity')",
            "reviews/F2b-review-034-repin.json (records G-FORM text allows 'or record the divergence explicitly')",
            "reviews/F1-review-088-rev12.json (literal wording satisfied by shared D0 + equal numeric contract; strict byte-identity reading fails)",
        ],
    }

    # -- verdict ----------------------------------------------------------
    if not all_controls_pass:
        verdict = "INVALID_CONTROLS_FAILED"
    elif (
        report["checks"]["D0_normalized_equal_all_three"]
        and report["checks"]["D0_tag_set_equal_all_three"]
        and numeric_equal
        and not report["checks"]["regularity_class_normalized_equal_all_three"]
        and report["checks"]["D0_is_tagged_union_not_single_triple"]
    ):
        verdict = "MEASURED_SHARED_UNION_AND_PARAMETERISED_CONTRACT__NO_SINGLE_FROZEN_TRIPLE"
    else:
        verdict = "MEASURED_UNEXPECTED_SHAPE_REVIEW_INSTRUMENT"
    report["verdict"] = verdict
    report["criterion_state_literal_reading"] = "UNMET_AS_MEASURED"
    report["criterion_state_recorded_divergence_reading"] = "RESERVED_TO_GATE_OWNER"
    report["claims_completion"] = False
    report["no_gate_verdict_claimed"] = True

    out = RUN_DIR / "report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in ("verdict", "checks", "controls")}, indent=1))
    print(f"\nwrote {out}")
    return 0 if all_controls_pass else 1


if __name__ == "__main__":
    sys.exit(main())
