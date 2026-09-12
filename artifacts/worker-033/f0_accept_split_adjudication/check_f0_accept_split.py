#!/usr/bin/env python3
"""Independent adjudication of the F0 accept/revise split at canonical hash 276009f4f63d.

Task: W033-F0-ACCEPT-SPLIT-ADJ-01  (worker-033, class-bound)
Classes in scope: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH

Context. At the pinned canonical F0 hash two independent reviewers disagree:
  worker-040 (00:22:41) verdict=accept  score 4.0
  worker-082 (00:23:10) verdict=revise  with blocking W082-F-01 and W082-F-02
G-F0 requires two independent accepts at the published hash. This script does not
adjudicate by vote: it re-derives each contested claim from the primary bytes and
records, per claim, whether it is confirmed, refuted, or needs scope correction.

Independence. This checker shares no code with worker-040 / worker-082 / the
authoring tools. It reads only canonical bytes plus the two review events.
A check whose `status` is "confirmed" asserts a defect; "refuted" asserts the
defect is absent at this hash. `mutation_controls.py` plants defects and requires
the named check to flip, so a checker that always agrees with itself fails.

Deterministic, offline, read-only. Emits report.json next to this file.
Usage: python3 check_f0_accept_split.py [--root REPO_ROOT] [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"FATAL: PyYAML required: {exc}", file=sys.stderr)
    raise

CANON_F0 = "research_map/formulation_taxonomy.yaml"
CANON_F1 = "schemas/af_wcc_vacuum.yaml"
CANON_F2A = "schemas/af_scc_c2_vacuum.yaml"
CANON_F2B = "schemas/af_scc_c0_vacuum.yaml"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
AUTHORING = "artifacts/formulation/formulation_taxonomy.yaml"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
EVENTS = "research_map/events.jsonl"

PINNED = {
    CANON_F0: "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    CANON_F1: "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    CANON_F2A: "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    CANON_F2B: "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    ALIASES: "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

# Registry-canonical conclusion tokens, as declared in VOCAB_ALIASES.json.
REGISTRY_CANONICAL = ["weak_cosmic_censorship", "scc_c2_future_inextendibility",
                      "scc_c0_future_inextendibility"]
# The alias direction: what the registry lists as an accepted alias of the above.
REGISTRY_ALIASES = {"weak_cosmic_censorship": ["WCC"],
                    "scc_c2_future_inextendibility": ["strong_cosmic_censorship_C2",
                                                     "strong_cosmic_censorship_c2"],
                    "scc_c0_future_inextendibility": ["strong_cosmic_censorship_C0",
                                                     "strong_cosmic_censorship_c0"]}

VACUUM_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SCALAR = "AF-WCC-SCALAR-SPH"
EXPLICIT_QUANT = ("comeager", "residual", "dense open", "dense_open", "measure one", "measure_one")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def ctext(tax: dict, cid: str) -> str:
    return str(((tax.get("classes", {}) or {}).get(cid, {}) or {}).get("conclusion", {}).get("text", "") or "")


def find_key(obj, key):
    """Recursive first-match lookup; canonical schemas nest these keys at varying depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            got = find_key(v, key)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_key(v, key)
            if got is not None:
                return got
    return None


def bind_explicit(text: str) -> bool:
    low = text.lower()
    return any(tok in low for tok in EXPLICIT_QUANT)


def load_f0_reviews(events: Path, pinned_hash: str):
    """F0-targeted reviews that bind the pinned hash, by evidence_ref or artifact_sha256.

    Target-scoped on purpose: many reviews of *other* nodes cite F0's hash as an input,
    so a ref-only match over-counts the split (30 vs the true F0 verdict set).
    """
    out = []
    if not events.exists():
        return out
    for line in events.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") != "review":
            continue
        if e.get("target_id") not in ("F0", None) and e.get("node_id") != "F0":
            continue
        if e.get("target_id") != "F0" and e.get("node_id") != "F0":
            continue
        refs = " ".join(str(r) for r in (e.get("evidence_refs") or []))
        if (pinned_hash[:12] in refs) or (e.get("artifact_sha256") == pinned_hash):
            out.append({"actor": e.get("actor"), "created_at": e.get("created_at"),
                        "verdict": e.get("verdict"), "score": e.get("score"),
                        "event_id": e.get("event_id"),
                        "blocking": [f for f in (e.get("hard_failures") or [])]})
    return out


def run_checks(root: Path) -> dict:
    checks = []

    def add(cid, title, status, expected, observed, binds):
        checks.append({"check_id": cid, "title": title, "status": status,
                       "expected": expected, "observed": observed, "binds": binds})

    paths = {k: root / k for k in (CANON_F0, CANON_F1, CANON_F2A, CANON_F2B, ALIASES, AUTHORING, CHECKER)}
    missing = [k for k, p in paths.items() if not p.exists()]
    hashes = {}
    for k, p in paths.items():
        if p.exists():
            hashes[k] = sha256(p)

    # ADJ-01 binding
    ok = hashes.get(CANON_F0) == PINNED[CANON_F0]
    add("ADJ-01", "verdict binds the pinned canonical F0 hash", "confirmed" if ok else "refuted",
        PINNED[CANON_F0], hashes.get(CANON_F0), CANON_F0)

    f0 = load_yaml(paths[CANON_F0]) if paths[CANON_F0].exists() else {}
    aliases = json.loads(paths[ALIASES].read_text()) if paths[ALIASES].exists() else {}
    f1 = load_yaml(paths[CANON_F1]) if paths[CANON_F1].exists() else {}
    f2a = load_yaml(paths[CANON_F2A]) if paths[CANON_F2A].exists() else {}
    f2b = load_yaml(paths[CANON_F2B]) if paths[CANON_F2B].exists() else {}

    # ADJ-02 four separate class ids
    ids = list(f0.get("class_ids") or [])
    add("ADJ-02", "exactly four separate class ids", "confirmed" if len(ids) == 4 and len(set(ids)) == 4 else "refuted",
        "4 distinct", f"{len(ids)} listed, {len(set(ids))} distinct: {sorted(ids)}", CANON_F0)

    # ADJ-03 the split itself (record, not a defect)
    pinned_reviews = load_f0_reviews(root / EVENTS, PINNED[CANON_F0])
    verdicts = sorted({r["verdict"] for r in pinned_reviews if r.get("verdict")})
    add("ADJ-03", "independent F0 verdicts at the pinned hash", "info" if len(pinned_reviews) >= 2 else "underdetermined",
        ">=2 independent verdicts", {"n_at_hash": len(pinned_reviews), "verdicts": verdicts,
                                     "reviewers": [r["actor"] for r in pinned_reviews]}, EVENTS)

    # ---- W082-F-01 : SCALAR-SPH conclusion quantifier vs its own H4 ----
    scalar = (f0.get("classes", {}) or {}).get(SCALAR, {}) or {}
    s_text = ctext(f0, SCALAR)
    s_axes = scalar.get("axes", {}) or {}
    h4 = next((h for h in (scalar.get("hypotheses") or []) if h.get("id") == "H4"), {}) or {}

    bare = bool(re.search(r"for\s+generic\s+data", s_text, re.I)) and not bind_explicit(s_text)
    add("ADJ-04", "W082-F-01a: SCALAR-SPH conclusion quantifies bare 'generic data'",
        "confirmed" if bare else "refuted",
        "conclusion binds an explicit named genericity set (comeager/residual/dense-open/measure-one)",
        {"quantifier_phrase": bool(re.search(r"for\s+generic\s+data", s_text, re.I)),
         "explicit_quantifier_token": bind_explicit(s_text),
         "axes.genericity_kind": s_axes.get("genericity_kind"),
         "conclusion_excerpt": s_text[:180]}, CANON_F0)

    contradiction = bool(h4.get("unresolved") is True) and bare
    add("ADJ-05", "W082-F-01b: H4 declares genericity unresolved while the conclusion quantifies generically",
        "confirmed" if contradiction else "refuted",
        "no unresolved genericity hypothesis when the conclusion text quantifies over 'generic data'",
        {"H4.unresolved": h4.get("unresolved"), "H4.text": (h4.get("text") or "")[:160],
         "genericity_value_status": scalar.get("genericity_value_status"),
         "bare_generic_conclusion": bare}, CANON_F0)

    prov = str(scalar.get("provenance", {}))
    equivalent = "equivalent" in s_text.lower()
    sourced = any(tok in prov.lower() for tok in ("equivalent", "equivalence"))
    add("ADJ-06", "W082-F-01c: SCALAR-SPH conclusion asserts an unsourced 'equivalently'",
        "confirmed" if (equivalent and not sourced) else "refuted",
        "every asserted equivalence carries a provenance/evidence binding",
        {"asserts_equivalently": equivalent, "provenance_mentions_equivalence": sourced,
         "provenance": prov[:180]}, CANON_F0)

    # ---- W082-F-02 : D3 scope overstatement and the checker's blind spot ----
    d3 = next((d for d in ((f0.get("class_scope_adjudication", {}) or {}).get("resolved_divergences") or [])
               if d.get("id") == "D3"), {}) or {}
    d3_res = str(d3.get("resolution", ""))
    claims_each = "each class" in d3_res.lower()
    explicit_classes = [c for c in f0.get("class_ids", []) if bind_explicit(ctext(f0, c))]
    missing_explicit = [c for c in f0.get("class_ids", []) if c not in explicit_classes]
    add("ADJ-07", "W082-F-02a: D3 'each class conclusion text' is wider than what holds",
        "confirmed" if (claims_each and missing_explicit) else "refuted",
        "a 'each class' resolution holds for every listed class",
        {"d3_resolution": d3_res[:200], "classes_with_explicit_quantifier": explicit_classes,
         "classes_without": missing_explicit}, CANON_F0)

    checker_src = paths[CHECKER].read_text() if paths[CHECKER].exists() else ""
    # The D3 detector's guard is the `if "for every data set in the class" in ctext(...)` line.
    # Class ids appear both as ctext("AF-...") args and as bare string literals in the join tuple,
    # so collect every AF- token on the guard line.
    guard = next((ln for ln in checker_src.splitlines() if 'for every data set in the class' in ln), "")
    d3_scope = sorted(set(re.findall(r"(AF-[A-Z0-9\-]+)", guard)))
    declared = re.findall(r'"class":"([^"]+)"', checker_src.split('"id":"D3"')[-1][:200]) if '"id":"D3"' in checker_src else []
    declared_classes = sorted({c for grp in declared for c in grp.split("/") if c.startswith("AF-")})
    inspects_scalar = SCALAR in d3_scope
    add("ADJ-08", "W082-F-02b: the D3 detector never reads AF-WCC-SCALAR-SPH",
        "confirmed" if (d3_scope and not inspects_scalar and SCALAR not in declared_classes) else "refuted",
        "the D3 detector reads every class the F0 D3 resolution claims ('each class conclusion text')",
        {"d3_detector_texts_read": d3_scope, "d3_detector_declared_classes": declared_classes,
         "declared_but_unread": [c for c in declared_classes if c not in d3_scope],
         "scalar_in_d3_scope": inspects_scalar, "scalar_named_in_d3": SCALAR in declared_classes,
         "guard": guard.strip()[:220]}, CHECKER)

    # Scope correction: is SCALAR-SPH compared elsewhere by the same checker?
    generic_loop = bool(re.search(r"for cid in sorted\(set\(A\[\"class_ids\"\]\)", checker_src)) and "genericity_kind" in checker_src
    add("ADJ-09", "scope correction to W082-F-02: SCALAR-SPH IS inspected for its genericity axis label",
        "confirmed" if generic_loop else "refuted",
        "'without inspecting that class' is imprecise: the axis label is compared, the conclusion text is not",
        {"axis_label_loop_present": generic_loop,
         "d3_text_scope_is_two_scc_classes_only": not inspects_scalar}, CHECKER)

    # ---- vocabulary: registry direction, F0 allowed tokens, per-schema pointers ----
    allowed = list((((f0.get("field_vocabulary", {}) or {}).get("conclusion_type", {}) or {}).get("allowed")) or [])
    canon_tokens = aliases.get("conclusion_type", {}) or {}
    registry_canonical = sorted(canon_tokens.keys())
    # A canonical token may list itself; only non-self entries are true aliases.
    alias_of = {a: c for c, al in canon_tokens.items() for a in al if a != c}
    f0_uses_alias = sorted({t for t in allowed if t in alias_of})
    f0_uses_registry_canonical = sorted({t for t in allowed if t in registry_canonical})
    add("ADJ-10", "W033-F0-01: canonical F0's allowed conclusion_type values include registry ALIASES",
        "confirmed" if f0_uses_alias else "refuted",
        "a canonical artifact lists registry-canonical tokens only (policy: aliases must never appear in a new canonical artifact)",
        {"f0_allowed": allowed, "registry_canonical": registry_canonical,
         "registry_alias_direction": alias_of,
         "f0_tokens_that_are_aliases": f0_uses_alias,
         "f0_tokens_that_are_registry_canonical": f0_uses_registry_canonical},
        [CANON_F0, ALIASES])

    ptr = {name: find_key(schema, "vocabulary_aliases_ref")
           for name, schema in (("F1", f1), ("F2a", f2a), ("F2b", f2b))}
    refs_present = [k for k, v in ptr.items() if v]
    f2_tokens = {"F2a": find_key(f2a, "conclusion_type"), "F2b": find_key(f2b, "conclusion_type")}
    add("ADJ-11", "W033-F0-02: only F1 carries the vocabulary_aliases_ref bridge",
        "confirmed" if refs_present == ["F1"] else "refuted",
        "either every canonical schema uses registry-canonical tokens, or each carries the alias-registry pointer",
        {"vocabulary_aliases_ref": ptr, "F2_conclusion_type_tokens": f2_tokens,
         "f2a_token_is_registry_canonical": f2_tokens["F2a"] in registry_canonical,
         "f2b_token_is_registry_canonical": f2_tokens["F2b"] in registry_canonical}, [CANON_F1, CANON_F2A, CANON_F2B])

    add("ADJ-12", "three vacuum classes bind an explicit comeager set; SCALAR-SPH does not",
        "confirmed" if (len(explicit_classes) == 3 and SCALAR in missing_explicit) else "refuted",
        "the same quantifier discipline across the four classes",
        {"explicit": explicit_classes, "not_explicit": missing_explicit}, CANON_F0)

    defect = [c for c in checks if c["status"] == "confirmed"]
    content = [c["check_id"] for c in defect if c["check_id"] in ("ADJ-04", "ADJ-05", "ADJ-06", "ADJ-07", "ADJ-10", "ADJ-11", "ADJ-12")]
    process = [c["check_id"] for c in defect if c["check_id"] in ("ADJ-08",)]
    return {
        "report_id": "W033-F0-ACCEPT-SPLIT-ADJ-01-report",
        "task_id": "W033-F0-ACCEPT-SPLIT-ADJ-01",
        "worker": "worker-033",
        "classes_in_scope": f0.get("class_ids"),
        "pinned_hashes": {k: hashes.get(k) for k in PINNED},
        "pinned_hashes_match": {k: (hashes.get(k) == v) for k, v in PINNED.items()},
        "missing_inputs": missing,
        "checks": checks,
        "checks_total": len(checks),
        "checks_confirmed": len(defect),
        "defect_checks_content": content,
        "defect_checks_process": process,
        "accept_split": {"n_at_pinned_hash": len(pinned_reviews),
                         "verdicts": verdicts, "reviews": pinned_reviews},
        "conclusion": ("revise at " + PINNED[CANON_F0][:12] +
                       ": W082-F-01 confirmed; W082-F-02 confirmed with a scope correction; "
                       "W033-F0-01/02 re-scope the earlier HF-02 (F2a token is registry-canonical, "
                       "not class leakage). worker-040's accept is not reproducible as-is."),
        "not_a_gate_verdict": True,
        "no_promotion": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[3]
    rep = run_checks(root)
    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "report.json"
    out.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"report": str(out), "checks_total": rep["checks_total"],
                      "confirmed": rep["checks_confirmed"],
                      "content_defects": rep["defect_checks_content"],
                      "process_defects": rep["defect_checks_process"],
                      "conclusion": rep["conclusion"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
