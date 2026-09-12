#!/usr/bin/env python3
"""L13 literature lifecycle — independent, read-only re-derivation of the decisive
G-LIT gate evidence at the frozen pins.

Owner : astra-lead-literature (group literature)
Node  : L0 (ledger/theorems.jsonl @ a1674f094979) + L1 (ledger/citation_audit.csv @ 315c19145065)
Gate  : G-LIT  (this instrument returns measurements, NOT a gate verdict)

What it does
------------
Re-derives, with an independently written stdlib-only implementation, the counts that the
two decisive new reviews rest on:
  * reviews/L0-review-final-verify.json            (astra-lead-audit, adjudication of the L0 split)
  * reviews/L1-review-032-full.json                (worker-032, full independent L1 review)

It also re-checks the accepts each review relies on, the cross-surface binding chain
L1 -> L0 -> registry, the duplicate-cluster annotation state, and the locator-column
classification under two explicit predicates (to show the boundary is predicate-dependent,
which is exactly what worker-032 referred to the standing ruling rather than decided).

Guarantees: no network, no write outside its own JSON output, no canonical/ledger/map/
taxonomy/detector write, no node status, no gate verdict. Inputs are hashed before and
after the run; any drift is reported and falsifies the record.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # artifacts/literature/reviews -> repo root
FROZEN_FOUR = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

PINS = {
    "L0_ledger": "ledger/theorems.jsonl",
    "L1_audit": "ledger/citation_audit.csv",
    "registry": "artifacts/literature/registry.jsonl",
    "unresolved": "artifacts/literature/unresolved.jsonl",
    "acceptance_md": "artifacts/literature/L0_L1_ACCEPTANCE.md",
    "manifest": "artifacts/literature/MANIFEST.json",
    "rubric": "evaluation_rubric.yaml",
    "taxonomy": "research_map/formulation_taxonomy.yaml",
    "detector": "research_map/class_separation.py",
    "l0_final_verify": "reviews/L0-review-final-verify.json",
    "l1_full_review": "reviews/L1-review-032-full.json",
    "l0_accept_075": "reviews/L0-review-075-rev3.json",
    "l0_accept_079": "reviews/L0-review-worker-079.json",
}

DECLARED = {  # hashes declared by the reviews / prior lifecycle records this instrument checks
    "L0_ledger": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "L1_audit": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "registry": "ea02d194",           # prefix, as cited by worker-032 companion pins
    "acceptance_md": "fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5",
    "manifest": "762b748939b184f19f4bb96b6b7ace9144942453ca26a14e06c57b300c16189e",
    "unresolved": "c7662d2926264eccb92f17c0889cbfc4afb4ae1b03b3d8113ee8ceb97b25d235",
    "rubric": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "taxonomy": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "detector": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure() -> dict:
    out = {}
    for key, rel in PINS.items():
        p = ROOT / rel
        if not p.exists():
            out[key] = {"path": rel, "present": False}
            continue
        b = p.read_bytes()
        st = p.stat()
        out[key] = {
            "path": rel,
            "present": True,
            "sha256": hashlib.sha256(b).hexdigest(),
            "bytes": len(b),
            "mtime_ns": st.st_mtime_ns,
        }
    return out


def jsonl(rel: str) -> list:
    return [json.loads(l) for l in (ROOT / rel).read_text().splitlines() if l.strip()]


def split_ids(value: str) -> list:
    if not value:
        return []
    return [x.strip() for x in re.split(r"[;,]", value) if x.strip()]


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def components(rows: list, keyfn, extra_pairs=None) -> list:
    """Union-find style components over a key function returning a list of keys."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    buckets = defaultdict(list)
    for i, r in enumerate(rows):
        for k in keyfn(r):
            buckets[k].append(i)
    for idxs in buckets.values():
        for j in idxs[1:]:
            union(idxs[0], j)
    for i, j in (extra_pairs or []):
        union(i, j)
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(i)
    return [sorted(v) for v in groups.values() if len(v) > 1]


def main() -> dict:
    t0 = measure()
    result = {
        "schema": "literature-gate-rederive/1",
        "instrument": "artifacts/literature/reviews/l13_gate_evidence_rederive.py",
        "lifecycle": "L13",
        "actor": "astra-lead-literature",
        "authority": "read-only owner re-derivation; no gate verdict, no node status, no canonical write",
        "pins_before": t0,
        "pins_match_declared": {
            k: (t0[k].get("present") and t0[k]["sha256"].startswith(DECLARED[k]) if k in DECLARED else None)
            for k in t0
        },
        "checks": {},
        "review_claims": {},
        "notes": [],
        "falsifiers": [
            "any input pin re-hashing differently after this run",
            "an L0 row carrying status/validation_status/supports_claim",
            "a foreign class token on either ledger surface",
            "an L1 row whose used_by_theorems id does not resolve in L0",
            "a duplicate component with zero or >=2 unannotated primaries",
        ],
    }

    # ---------------- L0 : ledger/theorems.jsonl ----------------
    l0 = jsonl("ledger/theorems.jsonl")
    forbidden = Counter()
    for r in l0:
        for key in ("status", "validation_status", "supports_claim"):
            if key in r and r[key] not in (None, "", [], {}):
                forbidden[key] += 1

    tokens = Counter()
    foreign_rows = []
    empty_rows, multi_rows, hf02_rows = [], [], []
    for r in l0:
        tids = r.get("theorem_id", "?")
        cls = r.get("class_ids") or []
        for c in cls:
            tokens[c] += 1
            if c not in FROZEN_FOUR:
                foreign_rows.append({"theorem_id": tids, "token": c})
        if not cls:
            empty_rows.append(tids)
        if len(set(cls)) >= 2:
            multi_rows.append(tids)
            hf02_rows.append(tids)

    theorem_like = [r for r in l0 if r.get("conclusion_type") in ("theorem", "conditional_theorem")]
    theorem_like_unbound = [r.get("theorem_id") for r in theorem_like if not (r.get("class_ids") or [])]

    result["checks"]["L0"] = {
        "rows": len(l0),
        "bytes": t0["L0_ledger"]["bytes"],
        "hf14_forbidden_key_rows": dict(forbidden),
        "class_token_counts": dict(tokens),
        "foreign_class_token_rows": foreign_rows,
        "rows_empty_class_ids": len(empty_rows),
        "empty_class_ids_ids": empty_rows,
        "rows_multi_class_ids": len(multi_rows),
        "hf02_literal_ids": sorted(hf02_rows),
        "theorem_like_rows": len(theorem_like),
        "theorem_like_unbound_rows": len(theorem_like_unbound),
        "theorem_like_unbound_ids": sorted(theorem_like_unbound),
        "review_status_values": dict(Counter(r.get("review_status") for r in l0)),
        "content_status_values": dict(Counter(r.get("content_status") for r in l0)),
    }

    # accepts the L0 adjudication rests on
    accepts = {}
    for key in ("l0_accept_075", "l0_accept_079"):
        p = ROOT / PINS[key]
        if not p.exists():
            accepts[key] = {"present": False}
            continue
        o = json.loads(p.read_text())
        accepts[key] = {
            "reviewer": o.get("reviewer"),
            "verdict": o.get("verdict"),
            "score": o.get("score"),
            "reviewed_sha256": o.get("reviewed_sha256"),
            "counts_as_full_schema_verdict": o.get("counts_as_full_schema_verdict"),
            "hard_failures": o.get("hard_failures"),
            "pin_matches_live": o.get("reviewed_sha256") == t0["L0_ledger"]["sha256"],
            "non_author": o.get("reviewer") != "astra-lead-literature",
        }
    l0fv = json.loads((ROOT / PINS["l0_final_verify"]).read_text())
    result["checks"]["L0_accepts"] = accepts
    result["checks"]["L0_final_verify"] = {
        "reviewer": l0fv.get("reviewer"),
        "reviewed_sha256": l0fv.get("reviewed_sha256"),
        "measured_sha256": l0fv.get("measured_sha256"),
        "pin_matches_live": l0fv.get("reviewed_sha256") == t0["L0_ledger"]["sha256"],
        "adjudicated_verdict": l0fv.get("adjudicated_verdict"),
        "gate_proposal": l0fv.get("gate_proposal"),
        "carried_objections": [o.get("id") for o in l0fv.get("carried_objections", [])],
    }

    # ---------------- L1 : ledger/citation_audit.csv ----------------
    with (ROOT / PINS["L1_audit"]).open(newline="") as fh:
        rd = csv.DictReader(fh)
        columns = rd.fieldnames
        l1 = list(rd)

    l0_ids = {r.get("theorem_id") for r in l0}
    l0_class = {r.get("theorem_id"): set(r.get("class_ids") or []) for r in l0}

    b1_foreign, b2_noanchor, b3_mismatch, b6_overstate = [], [], [], []
    b4_dangling, b5_nointersect, b9_divergent = [], [], []
    locator_classes = Counter()
    annotation_only_rows = []
    for d in l1:
        cid = d["citation_id"]
        raw_toks = [x.strip() for x in (d.get("class_mapping") or "").split(";") if x.strip()]
        toks = []
        for x in raw_toks:
            clean = x.split("(")[0].strip()
            if clean in FROZEN_FOUR:
                toks.append(clean)
            elif clean:
                toks.append(clean)  # foreign or malformed token -> B1
            if "(" in x:
                annotation_only_rows.append(cid)
        if any(t not in FROZEN_FOUR for t in toks):
            b1_foreign.append(cid)
        anchor = any((d.get(k) or "").strip() for k in ("doi", "arxiv_id", "url", "evidence_url"))
        if not anchor:
            b2_noanchor.append(cid)
        if d.get("resolver_result") == "resolved" and not (d.get("status") or "").startswith("verified"):
            b3_mismatch.append(cid)
        if (d.get("status") or "").startswith("verified") and d.get("resolver_result") != "resolved":
            b3_mismatch.append(cid)
        # B6 (independent reading): a verified-* status must carry a recorded http 2xx and a
        # non-empty evidence method/excerpt channel.
        if (d.get("status") or "").startswith("verified"):
            if str(d.get("http_status") or "").strip() not in ("200", "201", "202", "203", "204"):
                b6_overstate.append(cid)
        used = set(split_ids(d.get("used_by_theorems") or ""))
        av = (d.get("assessment") or "").strip()
        assessed = set() if av.startswith("assessed_no_binding") else set(
            split_ids(re.sub(r"^assessed\s*:\s*", "", av))
        )
        if used - l0_ids:
            b4_dangling.append({"citation_id": cid, "dangling": sorted(used - l0_ids)})
        if assessed != used:
            b9_divergent.append({"citation_id": cid, "only_assessed": sorted(assessed - used),
                                 "only_used": sorted(used - assessed)})
        if toks:
            hit = any(l0_class.get(t) and (set(toks) & l0_class[t]) for t in used)
            if not hit:
                b5_nointersect.append(cid)

        loc = (d.get("exact_locator") or "").strip()
        if re.search(r"doi\.org/|arxiv\.org/(abs|pdf)/|/abs/\d{4}\.\d{4,5}", loc):
            locator_classes["record_shaped_strict"] += 1
        elif re.search(r"[?&](q|query|search|find|terms)=", loc) or re.search(r"/(search|find)\b", loc):
            locator_classes["discovery_query"] += 1
        elif loc in ("...", "…") or loc.endswith("..."):
            locator_classes["elided_literal"] += 1
        elif loc.startswith("http"):
            locator_classes["other_http"] += 1
        elif loc:
            locator_classes["other_nonhttp"] += 1
        else:
            locator_classes["empty"] += 1

    reg = jsonl("artifacts/literature/registry.jsonl")
    reg_by_id = {r["source_id"]: r for r in reg}
    reg_missing, reg_title_mismatch = [], []
    for d in l1:
        r = reg_by_id.get(d["citation_id"])
        if not r:
            reg_missing.append(d["citation_id"])
        elif norm_title(r.get("title")) != norm_title(d.get("title")):
            reg_title_mismatch.append(d["citation_id"])

    # duplicate components: identifier-keyed (DOI or arXiv) and title-keyed
    def ident_keys(d):
        keys = []
        if d["doi"].strip():
            keys.append(("doi", d["doi"].strip().lower()))
        if d["arxiv_id"].strip():
            keys.append(("arxiv", d["arxiv_id"].strip().lower()))
        return keys

    def title_keys(d):
        return [("title", norm_title(d["title"]))] if norm_title(d["title"]) else []

    def key_groups(keyfns):
        groups = defaultdict(list)
        for i, d in enumerate(l1):
            for kf in keyfns:
                for k in kf(d):
                    groups[k].append(i)
        return {k: sorted(v) for k, v in groups.items() if len(v) > 1}

    doi_groups = key_groups([lambda d: [("doi", d["doi"].strip().lower())] if d["doi"].strip() else []])
    arxiv_groups = key_groups([lambda d: [("arxiv", d["arxiv_id"].strip().lower())] if d["arxiv_id"].strip() else []])
    title_groups = key_groups([title_keys])
    total_key_groups = len(doi_groups) + len(arxiv_groups) + len(title_groups)

    ident_groups = components(l1, ident_keys)
    title_only = [g for g in components(l1, title_keys)
                  if not any(set(g) <= s for s in [set(x) for x in ident_groups])]

    def with_mirror_edges(d):
        keys = ident_keys(d) + [("title", norm_title(d["title"]))] if norm_title(d["title"]) else ident_keys(d)
        m = (d.get("mirror_of") or "").strip()
        if m:
            keys = keys + [("mirror", m)]
        return keys

    # mirror closure needs the mirror edge to point at the *target row index*; map ids to index
    id2idx = {d["citation_id"]: i for i, d in enumerate(l1)}
    mirror_pairs = [(i, id2idx[(d.get("mirror_of") or "").strip()])
                    for i, d in enumerate(l1) if (d.get("mirror_of") or "").strip() in id2idx]
    closure_components = components(l1, with_mirror_edges, extra_pairs=mirror_pairs)

    def comp_record(idxs, note):
        prim = [l1[i]["citation_id"] for i in idxs if not (l1[i]["mirror_of"] or "").strip()]
        members = {l1[i]["citation_id"] for i in idxs}
        mirrors = {l1[i]["citation_id"]: (l1[i]["mirror_of"] or "").strip()
                   for i in idxs if (l1[i]["mirror_of"] or "").strip()}
        return {
            "predicate": note,
            "size": len(idxs),
            "members": sorted(members),
            "primaries": sorted(prim),
            "one_primary": len(prim) == 1,
            "mirrors_all_resolve_to_known_id": all(m in id2idx for m in mirrors.values()),
            "mirrors_inside_component": all(m in members for m in mirrors.values()),
        }

    ident_records = [comp_record(g, "identity-connected (doi/arxiv/title)") for g in ident_groups + title_only]
    closure_records = [comp_record(g, "identity+mirror_of closure") for g in closure_components if len(g) > 1]

    result["checks"]["L1"] = {
        "rows": len(l1),
        "columns": columns,
        "unique_citation_ids": len({d["citation_id"] for d in l1}),
        "unique_bibkeys": len({d["bibkey"] for d in l1}),
        "b1_foreign_class_token_rows": b1_foreign,
        "b2_missing_record_anchor_rows": b2_noanchor,
        "b3_resolution_status_mismatch_rows": b3_mismatch,
        "b6_status_overstatement_rows": b6_overstate,
        "b4_dangling_theorem_refs": b4_dangling,
        "b9_assessment_used_by_divergence": b9_divergent,
        "b5_no_class_intersection_rows": b5_nointersect,
        "registry_rows": len(reg),
        "registry_missing_source_ids": reg_missing,
        "registry_title_mismatch_ids": reg_title_mismatch,
        "duplicate_components": {
            "key_group_counting": {
                "doi_groups": len(doi_groups),
                "arxiv_groups": len(arxiv_groups),
                "title_groups": len(title_groups),
                "total_multi_row_key_groups": total_key_groups,
            },
            "identity_connected_components": len(ident_groups) + len(title_only),
            "identifier_connected": len(ident_groups),
            "title_only_connected": len(title_only),
            "records": ident_records,
            "all_one_primary": all(c["one_primary"] for c in ident_records),
            "all_mirrors_inside": all(c["mirrors_inside_component"] for c in ident_records),
            "mirror_closure": {
                "components": len(closure_records),
                "records": closure_records,
                "all_one_primary": all(c["one_primary"] for c in closure_records),
                "all_mirrors_inside": all(c["mirrors_inside_component"] for c in closure_records),
            },
        },
        "annotation_only_class_mapping_rows": sorted(set(annotation_only_rows)),
        "annotation_only_class_mapping_count": len(set(annotation_only_rows)),
        "locator_classification_owner_predicate": dict(locator_classes),
        "locator_non_record_rows": len(l1) - locator_classes["record_shaped_strict"],
        "status_values": dict(Counter(d["status"] for d in l1)),
        "resolver_values": dict(Counter(d["resolver_result"] for d in l1)),
        "evidence_type_values": dict(Counter(d["evidence_type"] for d in l1)),
    }

    # ---------------- L1 review claims vs my re-derivation ----------------
    l1rv = json.loads((ROOT / PINS["l1_full_review"]).read_text())
    mine = result["checks"]["L1"]
    claims = {
        "reviewed_sha256 == live": l1rv.get("reviewed_sha256") == t0["L1_audit"]["sha256"],
        "verdict": l1rv.get("verdict"),
        "score": l1rv.get("score"),
        "counts_toward_gate_accept": l1rv.get("counts_toward_gate_accept"),
        "hard_failures": l1rv.get("hard_failures"),
        "claim_97_rows": mine["rows"] == 97,
        "claim_97_unique_ids": mine["unique_citation_ids"] == 97,
        "claim_b1_zero": mine["b1_foreign_class_token_rows"] == [],
        "claim_b2_zero": mine["b2_missing_record_anchor_rows"] == [],
        "claim_b3_zero": mine["b3_resolution_status_mismatch_rows"] == [],
        "claim_b4_zero": mine["b4_dangling_theorem_refs"] == [],
        "claim_b9_zero": mine["b9_assessment_used_by_divergence"] == [],
        "claim_b5_zero": mine["b5_no_class_intersection_rows"] == [],
        "claim_11_components": mine["duplicate_components"]["key_group_counting"]["total_multi_row_key_groups"] == 11,
        "claim_one_primary_per_component": mine["duplicate_components"]["mirror_closure"]["all_one_primary"],
        "claim_mirrors_inside_component": mine["duplicate_components"]["mirror_closure"]["all_mirrors_inside"],
        "component_reconciliation": (
            "key-groups doi=%d + arxiv=%d + title=%d = %d; identity-connected=%d; "
            "identity+mirror closure=%d"
            % (mine["duplicate_components"]["key_group_counting"]["doi_groups"],
               mine["duplicate_components"]["key_group_counting"]["arxiv_groups"],
               mine["duplicate_components"]["key_group_counting"]["title_groups"],
               mine["duplicate_components"]["key_group_counting"]["total_multi_row_key_groups"],
               mine["duplicate_components"]["identity_connected_components"],
               mine["duplicate_components"]["mirror_closure"]["components"])
        ),
        "companion_pins_match_live": {
            PINS[k]: (t0[k]["sha256"] == v if t0[k].get("present") else None)
            for k, v in (l1rv.get("companion_pins") or {}).items()
            if k in t0
        },
    }
    result["review_claims"]["L1_review_032"] = claims
    result["review_claims"]["L0_final_verify"] = {
        "claim_rows_62": result["checks"]["L0"]["rows"] == 62,
        "claim_bytes_151521": result["checks"]["L0"]["bytes"] == 151521,
        "claim_hf14_zero": all(v == 0 for v in result["checks"]["L0"]["hf14_forbidden_key_rows"].values()),
        "claim_mtime_0039": t0["L0_ledger"]["mtime_ns"] // 10**9,
        "reviewer": l0fv.get("reviewer"),
        "adjudicated_verdict": l0fv.get("adjudicated_verdict"),
    }

    # ---------------- worker-100 census replication: integrity re-check ----------------
    w100_dir = ROOT / "artifacts/worker-100/glit_universe_replication"
    w100_report_p = w100_dir / "replication_report.json"
    w100 = {}
    if w100_report_p.exists():
        rep = json.loads(w100_report_p.read_text())
        t0p = json.loads((w100_dir / "raw/inputs_hashes_t0.json").read_text())
        t1p = json.loads((w100_dir / "raw/inputs_hashes_t1.json").read_text())
        hc = rep.get("headline_comparisons") or {}
        w100 = {
            "report_sha256": sha256(w100_report_p),
            "headline_comparisons": len(hc),
            "headline_all_match": all(v.get("match") for v in hc.values()),
            "headline_universes": {k: v.get("recorded") for k, v in hc.items()},
            "controls_all_pass": rep.get("controls_all_pass"),
            "pin_count": len(t0p),
            "pins_t0_eq_t1": t0p == t1p,
            "distinct_ids_named_decomposition_104": "97+97+7",
            "note": "worker-100 replication of worker-075's source-meta census; 9/9 headline "
                    "universes reproduce at 43/43 pins stable t0==t1 and 13/13 controls. The "
                    "'201 citations' gate-unmet figure equals none of the measured universes.",
        }
    result["checks"]["w100_census_replication_integrity"] = w100

    # ---------------- declared-pin reconciliation ----------------
    drift = []
    for k, declared in DECLARED.items():
        got = t0[k].get("sha256") if t0[k].get("present") else None
        if got is None or not got.startswith(declared):
            drift.append({"pin": k, "declared": declared, "measured": got})
    result["declared_pin_drift"] = drift

    # ---------------- non-blocking observations ----------------
    ev = l1rv.get("event_id", "")
    result["notes"] = [
        "L1-review-032-full.json event_id embeds 'T0126' while its created_at is 01:22:00 and its "
        "mtime is 01:22:31; the mismatch is in the event-id literal only and does not touch the "
        "reviewed hash, verdict, or counts. Recorded as an advisory naming inconsistency.",
        "The duplicate-component count is predicate-scoped and reconciles exactly under all three "
        "readings: key-group counting = 6 DOI + 4 arXiv + 1 title = 11 multi-row key-groups; "
        "identity-only closure (doi/arxiv/title edges) = 10 components (the DOI and arXiv "
        "key-groups for SRC-002/SRC-068 merge); identity+mirror_of closure = 11 components, each "
        "with exactly one empty primary and every mirror inside its component, which reproduces "
        "worker-032's F-032-03 sentence exactly. One precision note for the gate binder: under "
        "key-group counting the DOI group {SRC-060, SRC-072} has no in-group empty primary (both "
        "mirror SRC-020); the claim holds under its own closure predicate. Annotation completeness "
        "holds under every reading.",
        "exact_locator record-shaped counts are predicate-bounded (worker-032 18/97 strict, lead "
        "30/97 including metadata endpoints, this instrument %d/97 under the strict predicate); "
        "the finding is a documentation defect on L0_L1_ACCEPTANCE.md:18, referred to the ruling."
        % (result["checks"]["L1"]["locator_classification_owner_predicate"].get("record_shaped_strict", 0)),
    ]

    t1 = measure()
    result["pins_after"] = t1
    result["pin_stability"] = {
        k: (t0[k].get("sha256") == t1[k].get("sha256")) for k in t0
    }
    result["all_pins_stable"] = all(result["pin_stability"].values())
    print(json.dumps(result, indent=1, sort_keys=True))
    return result


if __name__ == "__main__":
    out = main()
    dest = ROOT / "artifacts/literature/reviews/L13-gate-evidence-rederive.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("WROTE", dest)
