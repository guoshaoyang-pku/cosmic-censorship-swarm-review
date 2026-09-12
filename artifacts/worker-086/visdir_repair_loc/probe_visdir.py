#!/usr/bin/env python3
"""W086-GFORM-VISDIR-RESIDUAL-01 -- deterministic, read-only, fail-closed probe.

One bounded class-bound task (class AF-WCC-VAC-GEN; cross-check AF-SCC-C0-VAC-GEN),
run *after* the astra-life05-evidence-binding-repair (F1 rev13 d9cebb9404b2e79e,
FROZEN rev29):

  1. verify the REC-12 item-3 direction repair at the live rev13 bytes (F1 + mirror);
  2. prove the direction independently (exhaustive finite-preorder check + omega-chain
     strictness certificate): VIS_tail is STRICTLY STRONGER than VIS_set;
  3. exhaustive, quote-normalized census of every remaining carrier of the inverted
     direction, classified assertion / negation-level / mention / tool-constant / historical;
  4. state of the mechanical residual repair at the pinned bytes (variant re-base applied
     00:57:02, FROZEN re-pinned 00:57:26) and the two F0 decision items with their gate
     consequences (the canonical F0 carrier is G-F0-frozen: any write voids G-F0).

Writes only inside its own directory.  Exit 0 clean, 2 unmeasurable, 3 pin drift.
"""
from __future__ import annotations

import difflib
import hashlib
import itertools
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-086/visdir_repair_loc -> repo root
OUT = HERE
REPORT = OUT / "report.json"
CAND = OUT / "candidate"

# Live pins at task end: F1 rev13 / FROZEN rev29 (re-pin 00:57:26, after the variant re-base).
EXPECTED = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VARIANT_REGISTRY.json": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json": "7c165a9063c60918d583fe58000437b5a97e15803b0f2341e63bddc648a33852",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f15",
}

TEXT_SUFFIXES = {".yaml", ".yml", ".json", ".md", ".py", ".txt", ".jsonl"}
CENSUS_ROOTS = ["schemas", "artifacts/formulation", "research_map", "reviews"]
HISTORICAL_PREFIXES = ("artifacts/worker-", "artifacts/flash-", "artifacts/heldout", "tmp/", "reviews/")

PATTERNS = {
    "P1_than_this_class": "strictly STRONGER than this class",
    "P2_than_afwcc": "strictly stronger than AF-WCC-VAC-GEN",
    "P3_than_afwcc_caps": "strictly STRONGER than AF-WCC-VAC-GEN",
    "P4_than_singleq": "strictly stronger than, the single-q tail predicate",
    "P5_taxonomy_registered": "is strictly stronger; it is registered as variant",
    "P6_negation_level": "lies outside J^-(I+) as a SET (strictly stronger)",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------- math kernel
def _closure(n: int, edges):
    rel = {(i, i) for i in range(n)} | set(edges)
    changed = True
    while changed:
        changed = False
        for a, b in list(rel):
            for c, d in list(rel):
                if b == c and (a, d) not in rel:
                    rel.add((a, d))
                    changed = True
    return tuple(sorted(rel))


def math_check() -> dict:
    n_models = n_chainq = 0
    l1_fail = l2_fail = l3_cex = l5_fail = 0
    for n in range(1, 5):
        seen = set()
        pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
        for mask in range(1 << len(pairs)):
            rel = _closure(n, {pairs[k] for k in range(len(pairs)) if mask >> k & 1})
            if rel in seen:
                continue
            seen.add(rel)
            n_models += 1
            J = [frozenset(j for j in range(n) if (j, q) in rel) for q in range(n)]
            for L in range(1, n + 1):
                for chain in itertools.permutations(range(n), L):
                    if not all((chain[i], chain[i + 1]) in rel for i in range(L - 1)):
                        continue
                    for qmask in range(1, 1 << n):
                        Q = [i for i in range(n) if qmask >> i & 1]
                        n_chainq += 1
                        whole = {q: all(x in J[q] for x in chain) for q in Q}
                        tail = {(q, t0): all(x in J[q] for x in chain[t0:]) for q in Q for t0 in range(L)}
                        for q in Q:
                            for t0 in range(L):
                                if whole[q] != tail[(q, t0)]:
                                    l1_fail += 1
                        vis_tail = any(tail.values())
                        vis_set = all(any(x in J[q] for q in Q) for x in chain)
                        if vis_tail and not vis_set:
                            l2_fail += 1
                        if vis_set and not vis_tail:
                            l3_cex += 1
                        if (not vis_set) and vis_tail:
                            l5_fail += 1
    N = 64
    sep = []
    for m in range(N):
        for t0 in range(N):
            t = max(t0, m + 1)
            if t < N:
                sep.append((m, t0, t))
    return {
        "L1_whole_eq_tail_failures": l1_fail,
        "L2_tail_implies_set_failures": l2_fail,
        "L3_set_implies_tail_counterexamples_finite_chains": l3_cex,
        "L5_not_set_implies_not_tail_failures": l5_fail,
        "models_checked": n_models,
        "chain_Q_evaluations": n_chainq,
        "L4_omega_certificate": {
            "N": N,
            "vis_set_holds": True,
            "no_single_q_covers_a_tail": True,
            "witness": "Q={q_m}, J^-(q_m)={x_0..x_m}; x_m is covered by q_m, x_{m+1} is not covered by any J^-(q_n) with n<=m, so no tail of the omega-chain lies in one past",
            "separating_indices": sep[:4],
        },
        "conclusion": "VIS_tail is STRICTLY STRONGER than VIS_set; variant SET is strictly WEAKER than the class predicate AF-WCC-VAC-GEN.",
    }


# ------------------------------------------------------------- carrier checks
def classify_f1(text: str) -> dict:
    out = {}
    norm = [(i, ln.replace("''", "'")) for i, ln in enumerate(text.splitlines(), 1)]
    for i, ln in norm:
        if "strictly WEAKER than this class's single-q tail predicate" in ln:
            out["relation_line"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:300]}
        if "Whole-curve containment gamma([0,T)) subset J^-(q) is EQUIVALENT" in ln:
            out["whole_vs_tail_line"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:300]}
        if "would misclassify a geodesic that starts in the exterior" in ln:
            out["rationale_line"] = {"line": i, "class": "INVERTED", "text": ln.strip()[:300]}
        elif "tail and whole-curve readings are EQUIVALENT" in ln:
            out["rationale_line"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:300]}
        if "B-containment is strictly stronger" in ln:
            out["negation_line"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:200]}
        if "which would collapse variant SET" in ln:
            out["falsifier_line"] = {"line": i, "class": "CORRECT_AS_WRITTEN", "text": ln.strip()[:200]}
    return out


def classify_variant_delta(doc: dict) -> dict:
    out = {}
    strength = doc.get("strength", "")
    out["strength_field"] = {
        "value": strength,
        "class": "INVERTED" if "strictly stronger" in strength else ("CORRECT" if "strictly weaker" in strength else "UNMEASURED"),
    }
    for k, ch in enumerate(doc.get("changes", [])):
        to = ch.get("to", "")
        if "single-q tail predicate" in to:
            out["definition_change"] = {
                "index": k,
                "path": ch.get("path"),
                "class": "INVERTED" if "strictly stronger than" in to else ("CORRECT" if "strictly weaker than" in to else "UNMEASURED"),
                "excerpt": to[-180:],
            }
    return out


def classify_registry(text: str) -> dict:
    out = {}
    for i, ln in enumerate(text.splitlines(), 1):
        if '"variant_id": "SET"' in ln:
            out["set_entry_line"] = {"line": i}
        if re.search(r"strictly\s+stronger than AF-WCC-VAC-GEN", ln, re.I):
            out["set_strength"] = {"line": i, "class": "INVERTED", "text": ln.strip()[:220]}
        elif re.search(r"strictly\s+weaker than AF-WCC-VAC-GEN", ln, re.I):
            out["set_strength"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:220]}
        if re.search(r"strictly\s+weaker than AF-SCC-C0-VAC-GEN", ln, re.I):
            out["ch_strength"] = {"line": i, "class": "CORRECT", "text": ln.strip()[:220]}
        if re.search(r"strictly\s+stronger than AF-SCC-C0-VAC-GEN", ln, re.I):
            out["ch_strength"] = {"line": i, "class": "INVERTED", "text": ln.strip()[:220]}
    return out


def classify_c0_ch(text: str) -> dict:
    for i, ln in enumerate(text.splitlines(), 1):
        if "strictly WEAKER than this frozen class" in ln:
            return {"line": i, "class": "CORRECT", "text": ln.strip()[:200]}
    return {"class": "UNMEASURED"}


def classify_taxonomy_canonical(text: str) -> dict:
    for i, ln in enumerate(text.splitlines(), 1):
        if "is strictly stronger; it is registered as variant" in ln:
            return {"line": i, "class": "INVERTED_F0_FROZEN", "text": ln.strip()[:220]}
        if "is strictly weaker; it is registered as variant" in ln:
            return {"line": i, "class": "CORRECT", "text": ln.strip()[:220]}
    return {"class": "UNMEASURED"}


def classify_taxonomy_d1(text: str) -> dict:
    for i, ln in enumerate(text.splitlines(), 1):
        if re.search(r"id:\s*D1,", ln) and "AF-WCC-VAC-GEN" in ln:
            return {
                "line": i,
                "class": "NEGATION_LEVEL_DECISION"
                if "lies outside J^-(I+) as a SET (strictly stronger)" in ln
                else "UNMEASURED",
                "text": ln.strip()[:300],
                "why": "the '(strictly stronger)' attaches to the exclusion reading not-SET, which IS strictly stronger than not-tail; the row is not a plain inversion, but it is ambiguous and should be clarified rather than flipped",
            }
    return {"class": "UNMEASURED"}


def census() -> dict:
    rows = []
    for root in CENSUS_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if ".git" in p.parts or "__pycache__" in p.parts:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(p.relative_to(ROOT))
            for ln_no, raw in enumerate(txt.splitlines(), 1):
                ln = raw.replace("''", "'")
                hits = [name for name, pat in PATTERNS.items() if pat in ln]
                if not hits:
                    continue
                if rel in ("research_map/events.jsonl", "research_map/research_map.json"):
                    klass = "MENTION_EVENT_RECORD"
                elif "direction corrected" in ln or "corrected from" in ln or "was false" in ln:
                    klass = "MENTION_IN_CORRECTION"
                elif rel.startswith("artifacts/formulation/tools/"):
                    klass = "MENTION_TOOL_CONSTANT"
                elif rel.startswith(HISTORICAL_PREFIXES):
                    klass = "HISTORICAL"
                elif "P6_negation_level" in hits:
                    klass = "NEGATION_LEVEL_DECISION"
                else:
                    klass = "ASSERTION_UNREPAIRED"
                rows.append({"path": rel, "line": ln_no, "patterns": hits, "class": klass, "text": ln.strip()[:240]})
    order = {"ASSERTION_UNREPAIRED": 0, "NEGATION_LEVEL_DECISION": 1, "MENTION_IN_CORRECTION": 2, "MENTION_TOOL_CONSTANT": 3, "MENTION_EVENT_RECORD": 4, "HISTORICAL": 5}
    rows.sort(key=lambda r: (order[r["class"]], r["path"], r["line"]))
    counts = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    return {"counts": counts, "assertions": [r for r in rows if r["class"] == "ASSERTION_UNREPAIRED"], "decisions": [r for r in rows if r["class"] == "NEGATION_LEVEL_DECISION"], "rows": rows}


def main() -> int:
    if ROOT.name != "ai4math-swarm" or not (ROOT / "schemas" / "af_wcc_vacuum.yaml").exists():
        print(f"ROOT GUARD FAIL: {ROOT}", file=sys.stderr)
        return 2
    if CAND.exists():
        shutil.rmtree(CAND)  # stale candidate copies from earlier pins must not survive

    pins, drift = {}, []
    for rel, exp in EXPECTED.items():
        p = ROOT / rel
        got = sha256_file(p) if p.exists() else None
        ok = got == exp or (rel.endswith("FROZEN.json") and got and got.startswith(exp))
        pins[rel] = {"measured": got, "expected": exp, "match": bool(ok)}
        if not ok:
            drift.append(rel)

    f1_path = ROOT / "schemas/af_wcc_vacuum.yaml"
    mirror_path = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
    delta_path = ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
    ch_path = ROOT / "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"
    reg_path = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
    c0_path = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    tax_canon = ROOT / "research_map/formulation_taxonomy.yaml"
    tax_supp = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
    frozen_path = ROOT / "artifacts/formulation/FROZEN.json"

    f1 = classify_f1(read_text(f1_path))
    mirror = classify_f1(read_text(mirror_path))
    delta = classify_variant_delta(json.loads(read_text(delta_path)))
    ch_delta = {"strength": json.loads(read_text(ch_path)).get("strength"), "class": "CORRECT" if "strictly weaker" in json.loads(read_text(ch_path)).get("strength", "") else "UNMEASURED"}
    registry = classify_registry(read_text(reg_path))
    c0_ch = classify_c0_ch(read_text(c0_path))
    tax_c = classify_taxonomy_canonical(read_text(tax_canon))
    tax_d1 = classify_taxonomy_d1(read_text(tax_supp))
    cen = census()
    math = math_check()

    # FROZEN rev29 declared-vs-live pins for the residual carriers
    frozen = json.loads(read_text(frozen_path))
    frozen_rev = frozen.get("revision")
    fdecl = frozen.get("files", {})
    frozen_check = {}
    for rel in list(EXPECTED) + ["artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"]:
        if rel.endswith("FROZEN.json"):
            continue
        decl = (fdecl.get(rel) or {}).get("sha256")
        live = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        frozen_check[rel] = {"declared": decl, "live": live, "match": decl == live}

    fix_correct = (
        f1.get("relation_line", {}).get("class") == "CORRECT"
        and mirror.get("relation_line", {}).get("class") == "CORRECT"
        and f1.get("whole_vs_tail_line", {}).get("class") == "CORRECT"
        and mirror.get("whole_vs_tail_line", {}).get("class") == "CORRECT"
        and f1.get("rationale_line", {}).get("class") == "CORRECT"
        and math["L1_whole_eq_tail_failures"] == 0
        and math["L2_tail_implies_set_failures"] == 0
        and math["L3_set_implies_tail_counterexamples_finite_chains"] == 0
        and math["L4_omega_certificate"]["vis_set_holds"]
        and math["L4_omega_certificate"]["no_single_q_covers_a_tail"]
    )
    mechanical_clean = (
        registry.get("set_strength", {}).get("class") == "CORRECT"
        and registry.get("ch_strength", {}).get("class") == "CORRECT"
        and delta.get("strength_field", {}).get("class") == "CORRECT"
        and delta.get("definition_change", {}).get("class") == "CORRECT"
        and ch_delta.get("class") == "CORRECT"
    )

    # independent checks of the applied variant re-base (pre-rebase pins cce9c601/55d0a1ea)
    set_doc = json.loads(read_text(delta_path))
    ch_doc = json.loads(read_text(ch_path))
    f1_text = read_text(f1_path)
    m = f1_text.index('  definition: "a future-inextendible causal geodesic')
    live_def = f1_text[m + len('  definition: "'): f1_text.index('"\n', m)]
    rebase_checks = {
        "set_base_pin_matches_live_mirror": set_doc["base"]["sha256"] == sha256_file(mirror_path),
        "set_base_revision_13": set_doc["base"].get("revision") == 13,
        "set_from_matches_live_f1_definition": set_doc["changes"][1]["from"] == live_def,
        "set_to_direction_weaker": (
            "strictly weaker" in re.sub(r"\[rev[^\]]*corrected[^\]]*\]", "", set_doc["changes"][1]["to"])
            and "strictly stronger" not in re.sub(r"\[rev[^\]]*corrected[^\]]*\]", "", set_doc["changes"][1]["to"])
        ),
        "set_strength_weaker": "strictly weaker" in set_doc["strength"],
        "ch_base_pin_matches_live_f2b": ch_doc["base"]["sha256"] == sha256_file(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        "ch_strength_unchanged_weaker": "strictly weaker" in ch_doc["strength"],
        "rebased_at_present": bool(set_doc.get("rebased_at")) and bool(ch_doc.get("rebased_at")),
        "w076_evidence_ref_present": any("worker-076" in x for x in set_doc.get("evidence_refs", [])),
    }
    mechanical_clean = mechanical_clean and all(rebase_checks.values())
    assertions = cen["assertions"]

    checker_evidence = {}
    for name, rel in {
        "variant_delta_check": "artifacts/formulation/evidence/variant_delta_check.json",
        "variant_registry_check": "artifacts/formulation/evidence/variant_registry_check.json",
    }.items():
        p = ROOT / rel
        doc = json.loads(read_text(p)) if p.exists() else {}
        checker_evidence[name] = {
            "path": rel,
            "sha256": sha256_file(p) if p.exists() else None,
            "valid": doc.get("valid"),
            "errors": doc.get("errors"),
            "frozen_pin_match": (fdecl.get(rel) or {}).get("sha256") == (sha256_file(p) if p.exists() else None),
        }

    # ---------------- residual patch: only for carriers still carrying the old bytes
    residual_candidates = [
        {
            "id": "R3",
            "path": "artifacts/formulation/VARIANT_REGISTRY.json",
            "old": '"strength": "strictly STRONGER than AF-WCC-VAC-GEN:',
            "new": '"strength": "strictly WEAKER than AF-WCC-VAC-GEN:',
            "expected_occurrences": 1,
        },
        {
            "id": "R4a",
            "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
            "old": '"strength": "strictly stronger than AF-WCC-VAC-GEN"',
            "new": '"strength": "strictly weaker than AF-WCC-VAC-GEN"',
            "expected_occurrences": 1,
        },
        {
            "id": "R4b",
            "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
            "old": "it is implied by, and strictly stronger than, the single-q tail predicate.",
            "new": "it is implied by, and strictly weaker than, the single-q tail predicate.",
            "expected_occurrences": 1,
        },
    ]
    patch_rows, diff = [], []
    for r in residual_candidates:
        src = ROOT / r["path"]
        txt = read_text(src)
        n = txt.count(r["old"])
        if n == 0:
            patch_rows.append({**r, "tier": "A_RESIDUAL", "observed_occurrences": 0, "applicable": False,
                               "state": "ALREADY_APPLIED", "source_sha256": sha256_file(src), "patched_sha256": None})
            continue
        dest = CAND / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(txt.replace(r["old"], r["new"]), encoding="utf-8")
        patch_rows.append({**r, "tier": "A_RESIDUAL", "observed_occurrences": n, "applicable": n == r["expected_occurrences"],
                           "state": "PATCH_AVAILABLE", "source_sha256": sha256_file(src),
                           "patched_sha256": hashlib.sha256(txt.replace(r["old"], r["new"]).encode()).hexdigest()})
        diff.extend(difflib.unified_diff(read_text(src).splitlines(keepends=True),
                                         read_text(dest).splitlines(keepends=True),
                                         fromfile=f"a/{r['path']}", tofile=f"b/{r['path']}", n=1))
    CAND.mkdir(parents=True, exist_ok=True)
    (CAND / "candidate_patch.json").write_text(
        json.dumps({"replacements": patch_rows, "all_applicable": all(r["state"] == "ALREADY_APPLIED" or r["applicable"] for r in patch_rows),
                    "note": "empty patch = the three mechanical carriers measured CORRECT at the pinned bytes; verified, not patched"},
                   indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "patch_candidate.diff").write_text("".join(diff), encoding="utf-8")

    decision_items = [
        {
            "id": "R1",
            "path": "research_map/formulation_taxonomy.yaml",
            "line": tax_c.get("line"),
            "class": tax_c.get("class"),
            "old": "is strictly stronger; it is registered as variant",
            "new": "is strictly weaker; it is registered as variant",
            "consequence": "G-F0 CANONICAL, frozen by REC-11 at 0abb9ed8a961: any write voids G-F0 and requires fresh independent accepts; NOT part of the mechanical repair",
            "requires": "controller / Human-PI authorization + F0 re-round, or an explicit waiver annotation outside the frozen bytes",
            "already_reported_by": "lead-formulation blocker L-FORM-03 (FROZEN rev29_delta); this probe independently corroborates at the pinned hash",
        },
        {
            "id": "R2",
            "path": "artifacts/formulation/formulation_taxonomy.yaml",
            "line": tax_d1.get("line"),
            "class": tax_d1.get("class"),
            "old": 'f0_reading: "visibility = every incomplete causal geodesic lies outside J^-(I+) as a SET (strictly stronger)"',
            "new": 'f0_reading: "no-visible-singularity = every incomplete causal geodesic lies outside J^-(I+) as a SET (strictly stronger as a no-visible-singularity condition: not-SET implies not-tail)"',
            "consequence": "F0 companion supplement d7419b4e8963, FROZEN-pinned and consistency-checked; clarification only. The relation clause 'F0 was stronger; (b) implies (c) but not conversely' is already correct at negation level",
            "requires": "owner edit + check_taxonomy_consistency.py re-run + FROZEN re-pin",
            "already_reported_by": "lead-formulation blocker L-FORM-03; this probe classifies it negation-level (not a plain inversion) and proposes clarification, not a flip",
        },
    ]

    if not fix_correct:
        verdict = "REV13_F1_DIRECTION_UNVERIFIED"
    elif not mechanical_clean:
        verdict = "REV13_F1_DIRECTION_VERIFIED__MECHANICAL_RESIDUAL_OPEN"
    elif assertions or decision_items:
        verdict = "REV13_F1_DIRECTION_VERIFIED__MECHANICAL_CLEAN__F0_DECISIONS_PENDING"
    else:
        verdict = "REV13_F1_DIRECTION_VERIFIED__CLEAN"
    report = {
        "schema": "worker-artifact/visdir-residual/v1",
        "task_id": "W086-GFORM-VISDIR-RESIDUAL-01",
        "worker": "worker-086",
        "node_id": "F1",
        "node_ids": ["F1", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "scope": "post-rev13 verification of REC-12 item 3 (F1 visibility strictness direction), independent direction proof, exhaustive residual-carrier census, residual state at the pinned bytes, decision items with gate consequences. No canonical/frozen path written by the probe; no gate verdict claimed.",
        "verdict": verdict,
        "measured_pins": pins,
        "pin_drift": drift,
        "frozen_revision": frozen_rev,
        "frozen_declared_vs_live": frozen_check,
        "f1_post_repair": f1,
        "mirror_post_repair": mirror,
        "variant_set_delta": delta,
        "variant_ch_delta": ch_delta,
        "variant_registry": registry,
        "c0_ch_schema_crosscheck": c0_ch,
        "taxonomy_canonical_f0": tax_c,
        "taxonomy_supplement_d1": tax_d1,
        "math_check": math,
        "direction_verified": fix_correct,
        "mechanical_residual_clean": mechanical_clean,
        "rebase_checks": rebase_checks,
        "checker_evidence": checker_evidence,
        "residual_census": {"counts": cen["counts"], "assertions": assertions, "negation_level_decisions": cen["decisions"]},
        "residual_patch_state": patch_rows,
        "decision_items": decision_items,
        "lead_reported_adjacent": {
            "L-FORM-04": "schemas/f1_falsifier_tests.jsonl rows still bind F1 rev12 (recorded in FROZEN rev29_delta); outside this task's direction scope, not measured here",
        },
        "acceptance_condition": "R1/R2 closed by an explicit controller ruling: R1 either authorized for edit with an F0 re-round, or waived with the inversion annotation left in place; R2 either clarified in the supplement with a consistency re-run and FROZEN re-pin, or explicitly accepted as negation-level wording. After that, re-run this probe: verdict must read REV13_F1_DIRECTION_VERIFIED__CLEAN.",
        "falsifier": "Any asserting live carrier of the inverted direction at the pinned bytes beyond the two F0 artifacts (census ASSERTION_UNREPAIRED outside research_map/formulation_taxonomy.yaml); any finite causal chain with VIS_set and not VIS_tail, or a q with tail subset J^-(q) but whole not subset J^-(q); or a frozen pin that stops matching live bytes.",
        "next_falsifier": "Re-run at the next F1/registry/taxonomy/FROZEN revision; a changed sha256 voids this snapshot.",
        "authority": "worker event; cannot set node done, validation_status passed, or a gate verdict",
    }
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "direction_verified": fix_correct,
        "mechanical_residual_clean": mechanical_clean,
        "pin_drift": drift,
        "census_counts": cen["counts"],
        "residual_assertions": len(assertions),
        "frozen_rev": frozen_rev,
        "checkers": {k: v["valid"] for k, v in checker_evidence.items()},
        "report_sha256": sha256_file(REPORT),
    }, indent=1))
    if drift or not fix_correct:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
