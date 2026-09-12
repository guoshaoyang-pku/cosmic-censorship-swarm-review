#!/usr/bin/env python3
"""Builder: HF-02 disjunctive class-binding adjudication packet (worker-023).

Bounded, class-bound L0 task taken from the open blockers in
artifacts/literature/reviews/L0-rev3-adjudication-20260912T0035.md section 7 (BL-6:
"HF-02 disjunction on 8 named rows") and from evaluation_rubric.yaml HF-02
("disjunction of class_ids" is a critical hard failure).

Scope discipline
----------------
* Read-only with respect to every input (ledger, registry, schemas, taxonomy).
* Writes exactly two files under artifacts/worker-023/l0_hf02/:
    - hf02-disjunction-adjudication-023.json   (the packet)
    - build_manifest_hf02_023.json             (input hashes + output hash)
* This is a PROPOSAL packet, not a ledger edit and not a gate verdict. The
  L0 owner (astra-lead-literature) and the formulation lead own any application.

Method (falsifiable, deterministic, offline)
--------------------------------------------
1. Pin every input by sha256. If ledger/theorems.jsonl is not the anchor
   revision the packet declares, record the drift; the packet stays bound to
   the measured hash only.
2. Independently re-derive the set of rows with a class_ids disjunction
   (len(class_ids) > 1) and require it to equal the 8 rows named by the L0
   rev-3 adjudication.
3. For each row, measure its own `regularity` / `statement_exact` /
   `genericity` fields (exact text stored in row_evidence) and map the
   extension class through the registered containment lattice in
   artifacts/formulation/VARIANT_REGISTRY.json.
4. Recommend one of:
     WCC_ONLY          -> class_ids = [AF-WCC-VAC-GEN]
     VARIANT_INFORMS   -> class_ids = [], informs_classes = [variant parent]
     RELATION_INFORMS  -> class_ids = [], informs_classes = [C0, C2]
     NEEDS_F1_RULING   -> class_ids = [], informs_classes = [...], open question
5. Self-check every recommendation: class_ids and informs_classes are disjoint,
   both use only the four frozen class ids, and every cited variant id is
   registered with the declared parent.

Run: python3 artifacts/worker-023/l0_hf02/build_hf02_023.py
"""

import hashlib
import json
import glob
import os
import platform
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

CST = timezone(timedelta(hours=8))

FROZEN_FOUR = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

WCC = "AF-WCC-VAC-GEN"
C2 = "AF-SCC-C2-VAC-GEN"
C0 = "AF-SCC-C0-VAC-GEN"

ANCHOR_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"

# Hash history observed while this packet was being built. The adjudication
# reads only class_ids / regularity / statement / genericity / tags /
# unresolved / caveats; the pin move 3e3d355314 -> a1674f09 changed only the
# review-status family on the eight rows (status/supports_claim_basis ->
# content_status/author_asserts_supports), verified by a field-level diff
# against the archived copy in prior_pin_evidence_check below.
PRIOR_PIN = {
    "sha256": "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6",
    "label": "L0 rev-3 HF-14 repair (astra-lead-literature, 00:30:26)",
}

INPUTS = {
    "ledger/theorems.jsonl": None,
    "ledger/citation_audit.csv": None,
    "artifacts/formulation/VARIANT_REGISTRY.json": None,
    "research_map/formulation_taxonomy.yaml": None,
    "schemas/af_scc_c0_vacuum.yaml": None,
    "schemas/af_scc_c2_vacuum.yaml": None,
    "evaluation_rubric.yaml": None,
}

ROW_ORDER = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

# Fields whose exact text is captured as per-row evidence.
EVIDENCE_FIELDS = [
    "label",
    "statement_exact",
    "regularity",
    "genericity",
    "conclusion_type",
    "entry_kind",
    "evidence_level",
    "ledger_tags",
    "unresolved",
    "scope_caveats",
]

# Adjudication table. Every recommendation below is justified against the
# registered variant lattice; nothing here edits an input.
ADJ = {
    "D-004": {
        "measured_extension_class": "L2CONN",
        "variant_id": "L2CONN",
        "registry_parent": C0,
        "disposition": "VARIANT_INFORMS",
        "lattice_quote": "between C2 and C0: WEAKER than AF-SCC-C0-VAC-GEN, STRONGER than AF-SCC-C2-VAC-GEN. A C2 extension has continuous (hence L^2_loc) Christoffels, so E_C2 is a subset of E_L2conn; a bare continuous extension has no L^2 control, so E_L2conn is a subset of E_C0.",
        "recommended": {"class_ids": [], "informs_classes": [C0], "ledger_tags_add": ["L2CONN"]},
        "rationale": (
            "D-004 defines 'the extension class: continuous metric with Christoffel symbols in L^2_loc' "
            "— byte-for-byte the registered variant L2CONN (parent AF-SCC-C0-VAC-GEN). The containment "
            "E_C2 subset E_L2conn subset E_C0 makes it neither a C0 statement (bare continuous extensions "
            "are not excluded) nor a C2 statement (only L^2-connection extensions are excluded). The "
            "registry rule says variant ids must never appear in class_ids and citing a variant as a "
            "class is class leakage; binding the row to both C0 and C2 is therefore a disjunction over "
            "classes the row does not assert."
        ),
        "falsifier": (
            "Falsified if VARIANT_REGISTRY.json changes L2CONN's parent or strength ordering, or if the "
            "row's `regularity` field at the pin is edited to a bare C0 (continuous only) or an exact C2 "
            "statement."
        ),
    },
    "D-005": {
        "measured_extension_class": "LIP",
        "variant_id": "LIP",
        "registry_parent": C0,
        "disposition": "VARIANT_INFORMS",
        "lattice_quote": "between C^{1,1} and C0: E_{C^{1,1}} is a subset of E_{C^{0,1}} is a subset of E_C0; incomparable with E_H2loc and E_L2conn in general",
        "recommended": {"class_ids": [], "informs_classes": [C0], "ledger_tags_add": ["LIP"]},
        "rationale": (
            "D-005 defines the Lipschitz / C^{0,1}_loc and L^s_loc-connection family — the registered "
            "variant LIP (parent AF-SCC-C0-VAC-GEN), explicitly recorded as 'between C^{1,1} and C0'. "
            "Lipschitz-inextendibility neither forbids a bare continuous extension (not C0) nor is the "
            "exact C2 predicate. The row is a definition of an intermediate variant, so it informs the "
            "C0 dossier without being a member of C0 or C2."
        ),
        "falsifier": (
            "Falsified if VARIANT_REGISTRY.json changes LIP's parent or strength ordering, or if the "
            "row's `regularity` field at the pin is edited to exactly C0 or exactly C2."
        ),
    },
    "T-303": {
        "measured_extension_class": "L2CONN",
        "variant_id": "L2CONN",
        "registry_parent": C0,
        "disposition": "VARIANT_INFORMS",
        "lattice_quote": "citing an L^2-connection result as C0 or C2 would be a scope error",
        "recommended": {"class_ids": [], "informs_classes": [C0], "ledger_tags_add": ["L2CONN"]},
        "rationale": (
            "T-303 is a construction with C^0 extension and Christoffels not in L^2_loc: it is a "
            "counterexample inside the L2CONN variant (E_C2 subset E_L2conn subset E_C0), not a C0 or "
            "C2 statement. Its own `genericity` field records that the data class is special "
            "(high-frequency/impulsive) and 'not generic AF collapse data', so it also fails the "
            "genericity conjunct of both frozen SCC classes. It is an ingredient for the C0 dossier, "
            "and it is exactly the class of result the registry warns must not be reported as C0 or C2."
        ),
        "falsifier": (
            "Falsified if the cited source (SRC-022) is shown at the pin to quantify over generic "
            "one-ended asymptotically flat vacuum Cauchy data, or if its extension is shown to be C2 "
            "(which would make the row a C2-class counterexample rather than an L2CONN ingredient)."
        ),
    },
    "T-305": {
        "measured_extension_class": "LIP",
        "variant_id": "LIP",
        "registry_parent": C0,
        "disposition": "VARIANT_INFORMS",
        "lattice_quote": "L1's T-305 gives a conditional Lipschitz-inextendibility result (preprint, Price-law assumption, only near i+) which must not be reported as C0 or C2",
        "recommended": {"class_ids": [], "informs_classes": [C0], "ledger_tags_add": ["LIP"]},
        "rationale": (
            "T-305 concludes Lipschitz-inextendibility (metric C^{0,1}) near i_+, conditional on a "
            "nonlinear Price-law estimate. That is the registered LIP variant, whose parent is "
            "AF-SCC-C0-VAC-GEN; the registry names this exact row as one that must not be reported as "
            "C0 or C2. It is an ingredient for the C0 dossier (and, by E_C2 subset E_LIP, also bears on "
            "C2), but it is not a member of either frozen class: it controls only the horizon piece near "
            "i_+ and rests on an assumption."
        ),
        "falsifier": (
            "Falsified if the result is upgraded to forbid a bare continuous (C0) extension or is "
            "re-stated as exactly a C2 statement, or if the registry moves LIP to a different parent."
        ),
    },
    "T-402": {
        "measured_extension_class": "H2LOC",
        "variant_id": "H2LOC",
        "registry_parent": C0,
        "disposition": "RELATION_INFORMS",
        "lattice_quote": "between C2 and C0: WEAKER than AF-SCC-C0-VAC-GEN, STRONGER than AF-SCC-C2-VAC-GEN; containment E_C2 subset E_H2loc subset E_C0",
        "recommended": {"class_ids": [], "informs_classes": [C0, C2], "ledger_tags_add": ["H2LOC"]},
        "rationale": (
            "T-402 is an open-problem row asserting a relation between the C0 and C2 pictures "
            "(C0-extendible but generically C2-singular / weak-null). Its regularity field places it "
            "'between C^0 and C^2', i.e. the registered intermediate variant H2LOC, whose parent is C0. "
            "It asserts membership in no single frozen class; it is an ingredient for both dossiers. "
            "The registry calls the Dafermos-Luk-type class 'the most likely scope error' precisely "
            "because it is often reported as C0 or C2."
        ),
        "falsifier": (
            "Falsified if the conjecture is proved as an exact C0 or exact C2 statement at the pin, or "
            "if the registry changes H2LOC's parent/strength or removes the intermediate reading."
        ),
    },
    "T-515": {
        "measured_extension_class": "WCC-ANTECEDENT",
        "variant_id": None,
        "registry_parent": WCC,
        "disposition": "WCC_ONLY",
        "lattice_quote": "a visible incomplete causal geodesic is a WCC falsifier; it is NOT the falsifier of this class",
        "recommended": {"class_ids": [WCC], "informs_classes": [], "ledger_tags_add": []},
        "rationale": (
            "T-515 records Kerr exterior stability status (a)-(d): global nonlinear stability claims, "
            "linear stability for the full subextremal range, and a Lambda>0 clause. That is the WCC "
            "antecedent (complete I+ / no visible incompleteness), not an inextendibility statement "
            "about the maximal development. The C0 and C2 schemas state that visibility/I+ matters are "
            "the WCC predicate and are logically independent of SCC inextendibility; the row carries no "
            "inextendibility conclusion. Its caveat that it bounds how far T-301's refutation reaches is "
            "a consequence, not a class membership. Binding it to C0 was the disjunction defect."
        ),
        "falsifier": (
            "Falsified if the entry at the pin is edited to assert a C0/C2 inextendibility or "
            "extendibility conclusion about the maximal development, rather than an exterior stability "
            "status."
        ),
    },
    "T-526": {
        "measured_extension_class": "LIP",
        "variant_id": "LIP",
        "registry_parent": C0,
        "disposition": "NEEDS_F1_RULING",
        "lattice_quote": "The result is nonlinear vacuum without symmetry: this is the strongest vacuum SCC-type statement in the ledger.",
        "recommended": {"class_ids": [], "informs_classes": [C2], "ledger_tags_add": ["LIP"]},
        "needs_f1_ruling": {
            "question": (
                "Does a characteristic interior-data result (data on a dynamical event horizon settling "
                "to subextremal Kerr) discharge AF-SCC-C2-VAC-GEN, whose data class is generic one-ended "
                "asymptotically flat vacuum Cauchy data?"
            ),
            "row_evidence": "unresolved: 'Whether the AF-SCC class should count a characteristic interior result as discharging it.'",
            "if_yes": "class_ids = [AF-SCC-C2-VAC-GEN] (non-Lipschitz-extendibility entails non-C2-extendibility by E_C2 subset E_LIP)",
            "if_no": "class_ids = [], informs_classes = [AF-SCC-C2-VAC-GEN] (this packet's default)",
        },
        "rationale": (
            "T-526 proves C^0-extendibility but not Lipschitz-extendibility (registered LIP variant, "
            "parent C0) for characteristic interior data. Because E_C2 subset E_LIP, non-Lipschitz-"
            "extendibility implies non-C2-extendibility, so the row is the strongest vacuum pointer for "
            "the C2 dossier — but its data class is not the frozen class's generic one-ended AF Cauchy "
            "data, and the row itself flags that membership question as unresolved. It therefore cannot "
            "be a C2 member without an F1 ruling, and it is certainly not a C0 member."
        ),
        "falsifier": (
            "Falsified if an F1 ruling makes characteristic interior data a member of the AF-SCC class "
            "(then class_ids=[C2] is licensed), or if the metric is shown to admit a Lipschitz (hence "
            "C2) extension."
        ),
    },
    "T-528": {
        "measured_extension_class": "WCC-ANTECEDENT",
        "variant_id": None,
        "registry_parent": WCC,
        "disposition": "WCC_ONLY",
        "lattice_quote": "a visible incomplete causal geodesic is a WCC falsifier; it is NOT the falsifier of this class",
        "recommended": {"class_ids": [WCC], "informs_classes": [], "ledger_tags_add": []},
        "rationale": (
            "T-528 is Hintz 2026 exterior nonlinear stability of subextremal Kerr: an open-neighbourhood "
            "convergence statement in the exterior region with prescribed AF asymptotics. It is the WCC "
            "antecedent, not an inextendibility result for the maximal development. The row's own "
            "caveat that it supersedes T-515 (a status row) confirms it belongs with the WCC class. "
            "Binding it to C0 was the disjunction defect."
        ),
        "falsifier": (
            "Falsified if the entry at the pin is edited to assert an interior/Cauchy-horizon "
            "inextendibility conclusion."
        ),
    },
}


def sha256_file(rel):
    p = os.path.join(ROOT, rel)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_abs(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    errors = []

    # 1. pin inputs
    input_hashes = {}
    for rel in INPUTS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            errors.append("MISSING_INPUT: " + rel)
            continue
        input_hashes[rel] = sha256_file(rel)

    ledger_rel = "ledger/theorems.jsonl"
    ledger_sha = input_hashes.get(ledger_rel)
    pin_drift = (ledger_sha != ANCHOR_LEDGER)

    # 2. load ledger rows
    rows = {}
    with open(os.path.join(ROOT, ledger_rel), "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rows[r["theorem_id"]] = r

    measured_disjunctive = sorted(
        tid for tid, r in rows.items() if len(r.get("class_ids") or []) > 1
    )
    if measured_disjunctive != sorted(ROW_ORDER):
        errors.append(
            "DISJUNCTIVE_SET_MISMATCH: measured=%s declared=%s"
            % (measured_disjunctive, sorted(ROW_ORDER))
        )

    # 2b. moving-target discipline: if the prior pin's bytes are archived,
    # verify that every binding-relevant evidence field is unchanged.
    prior_pin_check = {
        "prior_sha256": PRIOR_PIN["sha256"],
        "prior_label": PRIOR_PIN["label"],
        "archive_path": None,
        "evidence_fields_compared": list(EVIDENCE_FIELDS),
        "evidence_fields_identical": None,
        "changed_evidence_fields": {},
    }
    for cand in sorted(glob.glob(os.path.join(ROOT, "artifacts/literature/archive/*"))):
        if sha256_abs(cand) == PRIOR_PIN["sha256"]:
            prior_pin_check["archive_path"] = os.path.relpath(cand, ROOT)
            prior_rows = {}
            with open(cand, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rr = json.loads(line)
                        prior_rows[rr["theorem_id"]] = rr
            changed = {}
            for tid in ROW_ORDER:
                diffs = [
                    f
                    for f in EVIDENCE_FIELDS
                    if prior_rows.get(tid, {}).get(f) != rows.get(tid, {}).get(f)
                ]
                if diffs:
                    changed[tid] = diffs
            prior_pin_check["evidence_fields_identical"] = not changed
            prior_pin_check["changed_evidence_fields"] = changed
            break

    # 3. registry lattice
    reg = json.load(open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json"), encoding="utf-8"))
    reg_variants = {v["variant_id"]: v for v in reg["variants"]}
    reg_parents = {p["class_id"] for p in reg["parent_classes"]}
    if set(FROZEN_FOUR) != reg_parents:
        errors.append("REGISTRY_PARENT_SET_MISMATCH: %s" % sorted(reg_parents))
    reg_text = json.dumps(reg, ensure_ascii=False)

    rubric_text = open(os.path.join(ROOT, "evaluation_rubric.yaml"), encoding="utf-8").read()
    # Corpus for lattice/visibility quotes: the variant registry plus the two
    # frozen SCC schemas (their visibility sections are quoted by WCC_ONLY rows).
    lattice_corpus = reg_text
    for rel in ("schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml"):
        lattice_corpus += open(os.path.join(ROOT, rel), encoding="utf-8").read()

    # 4. per-row evidence + recommendations
    packet_rows = []
    for tid in ROW_ORDER:
        r = rows.get(tid)
        if r is None:
            errors.append("MISSING_ROW: " + tid)
            continue
        adj = ADJ[tid]
        row_evidence = {}
        for f in EVIDENCE_FIELDS:
            if f in r:
                row_evidence[f] = r[f]
        if not row_evidence.get("regularity") or not row_evidence.get("statement_exact"):
            errors.append("EMPTY_CORE_EVIDENCE: " + tid)

        rec = adj["recommended"]
        cids = list(rec["class_ids"])
        inf = list(rec["informs_classes"])

        # self-checks on the recommendation
        for c in cids + inf:
            if c not in FROZEN_FOUR:
                errors.append("NON_FROZEN_CLASS_IN_REC: %s %s" % (tid, c))
        if set(cids) & set(inf):
            errors.append("CLASS_IDS_INFORMS_OVERLAP: " + tid)
        if not cids and not inf:
            errors.append("EMPTY_BINDING_REC: " + tid)
        vid = adj.get("variant_id")
        if vid is not None:
            if vid not in reg_variants:
                errors.append("UNREGISTERED_VARIANT: %s %s" % (tid, vid))
            else:
                if reg_variants[vid]["parent_class"] != adj["registry_parent"]:
                    errors.append("VARIANT_PARENT_MISMATCH: %s" % tid)
        if adj["lattice_quote"] not in lattice_corpus and adj["lattice_quote"] not in json.dumps(row_evidence, ensure_ascii=False):
            errors.append("LATTICE_QUOTE_NOT_FOUND: " + tid)

        packet_rows.append(
            {
                "row_id": tid,
                "node_id": "L0",
                "class_ids_at_pin": r.get("class_ids"),
                "current_disjunction": True,
                "measured_extension_class": adj["measured_extension_class"],
                "registry_variant_id": vid,
                "registry_parent": adj["registry_parent"],
                "disposition": adj["disposition"],
                "lattice_quote": adj["lattice_quote"],
                "row_evidence": row_evidence,
                "recommended": {
                    "class_ids": cids,
                    "informs_classes": inf,
                    "ledger_tags_add": list(rec["ledger_tags_add"]),
                },
                "needs_f1_ruling": adj.get("needs_f1_ruling"),
                "rationale": adj["rationale"],
                "falsifier": adj["falsifier"],
            }
        )

    # 5. summary
    disp_counts = {}
    for pr in packet_rows:
        disp_counts[pr["disposition"]] = disp_counts.get(pr["disposition"], 0) + 1
    remaining_disjunctions_after_patch = sum(
        1 for pr in packet_rows if len(pr["recommended"]["class_ids"]) > 1
    )

    packet = {
        "schema": "l0-hf02-disjunction-adjudication/v1",
        "artifact_id": "w023-hf02-disjunction-adjudication-20260912T0035",
        "actor": "worker-023",
        "worker_slot": "023",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": [C2, C0],
        "hard_failure_targeted": "HF-02 class_leakage (disjunction of class_ids)",
        "authority": (
            "Worker evidence and proposal only. No ledger edit, no gate verdict, no node status, no "
            "re-adjudication of any mathematical claim; class-binding application is owned by "
            "astra-lead-literature and the formulation lead."
        ),
        "applied": False,
        "inputs": input_hashes,
        "anchor_ledger_sha256": ANCHOR_LEDGER,
        "pin_drift": pin_drift,
        "pin_drift_note": (
            "ledger/theorems.jsonl measured hash differs from the declared anchor; every statement "
            "below is bound to the measured hash only."
            if pin_drift
            else "ledger/theorems.jsonl equals the declared anchor at build time."
        ),
        "pin_history": [
            dict(PRIOR_PIN, note="superseded while this packet was in build; content_status / author_asserts_supports rename only"),
            {"sha256": ledger_sha, "label": "measured anchor for every statement in this packet"},
        ],
        "prior_pin_evidence_check": prior_pin_check,
        "disjunctive_row_set": measured_disjunctive,
        "rows": packet_rows,
        "summary": {
            "n_rows": len(packet_rows),
            "dispositions": disp_counts,
            "predicted_hf02_disjunctions_after_patch": remaining_disjunctions_after_patch,
            "singular_class_members_after_patch": sum(
                1 for pr in packet_rows if len(pr["recommended"]["class_ids"]) == 1
            ),
            "relation_bindings_after_patch": sum(
                1 for pr in packet_rows if not pr["recommended"]["class_ids"]
            ),
        },
        "proposed_patch": [
            {
                "op": "set",
                "row_id": pr["row_id"],
                "class_ids": pr["recommended"]["class_ids"],
                "informs_classes": pr["recommended"]["informs_classes"],
                "ledger_tags_add": pr["recommended"]["ledger_tags_add"],
                "note": "proposal only; not applied by worker-023",
            }
            for pr in packet_rows
        ],
        "self_checks": {
            "disjunctive_set_equals_declared": measured_disjunctive == sorted(ROW_ORDER),
            "all_recommendations_use_frozen_four_only": all(
                set(pr["recommended"]["class_ids"]) | set(pr["recommended"]["informs_classes"])
                <= set(FROZEN_FOUR)
                for pr in packet_rows
            ),
            "class_ids_and_informs_disjoint": all(
                not (set(pr["recommended"]["class_ids"]) & set(pr["recommended"]["informs_classes"]))
                for pr in packet_rows
            ),
            "all_cited_variants_registered": all(
                pr["registry_variant_id"] is None
                or (
                    pr["registry_variant_id"] in reg_variants
                    and reg_variants[pr["registry_variant_id"]]["parent_class"] == pr["registry_parent"]
                )
                for pr in packet_rows
            ),
            "hf02_detector_text_present_in_rubric": "disjunction of class_ids" in rubric_text,
            "errors": errors,
        },
        "falsifiers": [
            "Any of the 8 rows' measured regularity/statement fields differs at the measured ledger "
            "hash from the row_evidence quoted here.",
            "VARIANT_REGISTRY.json changes a cited variant's parent or the containment lattice used in "
            "`lattice_quote`.",
            "An F1 ruling licenses a characteristic-interior or intermediate-variant result as a member "
            "of a frozen SCC class, which would move T-303/T-305/T-526 to a singular class_ids binding.",
            "The ledger hash moves: this packet is void at any hash other than the measured one.",
        ],
        "validation_status": "unverified",
        "reproduction": "python3 artifacts/worker-023/l0_hf02/build_hf02_023.py && python3 artifacts/worker-023/l0_hf02/verify_hf02_023.py",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    out_path = os.path.join(HERE, "hf02-disjunction-adjudication-023.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(packet, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")

    out_sha = sha256_file(os.path.relpath(out_path, ROOT))
    manifest = {
        "builder": "artifacts/worker-023/l0_hf02/build_hf02_023.py",
        "built_at": packet["created_at"],
        "inputs": input_hashes,
        "output": {
            "path": "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json",
            "sha256": out_sha,
        },
        "self_check_errors": errors,
        "ok": not errors,
    }
    with open(os.path.join(HERE, "build_manifest_hf02_023.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(json.dumps({"output_sha256": out_sha, "errors": errors, "ok": not errors}, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
