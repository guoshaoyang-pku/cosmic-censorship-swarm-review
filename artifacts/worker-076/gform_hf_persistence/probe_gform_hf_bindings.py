#!/usr/bin/env python3
"""W076-GFORM-HFBIND-01 -- hash-rebind + named-hard-failure persistence probe.

Bounded, read-only, deterministic. Answers one question at the live bytes:

    Do the G-FORM unmet items (hash pins and named hard failures HF-A1, HF-A2,
    HF-B1, HF-B2) still hold at the current canonical revision of F1/F2a/F2b,
    or were they silently repaired while the map kept the stale text?

Why this is needed: the map's G-FORM unmet list pins F1 at 7a3e1f93, F2a at
23fec0e9, F2b at e6b1af2b and F2 at the retired merged artifact; the canonical
tree was republished around 00:16-00:18 and had already moved again by 00:19.
A pin that is not re-measured is not evidence.

Method
------
* measure sha256 of the four canonical class artifacts before and after the run
  (a stable window is required for the result to bind);
* collect every hash pin on those paths from map.gates[*].unmet,
  map.publication_status, map.frozen_artifacts and
  runtime/state/artifact_hashes.json, and classify MATCH / STALE_OR_UNKNOWN;
* re-test the four named hard failures textually and structurally at the
  measured revision:
    HF-A1  extension_predicate referenced but never defined (F2a)
    HF-A2  conclusion.statement_formal quantifies over undefined D0 / D_gen
           and contradicts quantifiers.formal (F2a)
    HF-B1  "C0 or C2" merged-class text outside the lint exemption block (F2b)
    HF-B2  node_id identity mismatch (artifact F2b vs map node F2) (F2b)
* calibration controls: the detectors must fire on synthetic positives and stay
  silent on synthetic negatives, else controls_ok=false and the probe void.

No gate verdict, no node transition, no theorem: worker events cannot set
done/passed. Output is evidence only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MAP = ROOT / "research_map" / "research_map.json"
REGISTRY = ROOT / "runtime" / "state" / "artifact_hashes.json"
CST = timezone(timedelta(hours=8))

CANON = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
FILENAME_NODE = {
    "schemas/af_wcc_vacuum.yaml": "F1",
    "schemas/af_scc_c2_vacuum.yaml": "F2a",
    "schemas/af_scc_c0_vacuum.yaml": "F2b",
}
# merged-class pattern: C0/C2 in either order, with or without the caret
MERGED_PAT = re.compile(r"c\s*\^?\s*0\s*(?:or|/)\s*c\s*\^?\s*2|c\s*\^?\s*2\s*(?:or|/)\s*c\s*\^?\s*0", re.I)
HEX = re.compile(r"\b[0-9a-f]{8,64}\b")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"path": rel, "exists": False}
    b = p.read_bytes()
    return {
        "path": rel,
        "exists": True,
        "bytes": len(b),
        "sha256": sha256_bytes(b),
        "sha8": sha256_bytes(b)[:8],
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
    }


def load_texts() -> dict:
    out = {}
    for rel in CANON.values():
        p = ROOT / rel
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            try:
                parsed = yaml.safe_load(text)
            except Exception as exc:  # noqa: BLE001
                parsed = None
                out[rel + "::parse_error"] = str(exc)
            out[rel] = {"text": text, "lines": text.splitlines(), "parsed": parsed}
    return out


# ---------------------------------------------------------------- structure ---
def walk(obj, path=()):
    """Yield (dotted_path, key, value) for every mapping entry, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from walk(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),))


def find_values(parsed, key):
    return [v for _, k, v in walk(parsed) if k == key]


def domain_ids(parsed):
    ids = set()
    for _, k, v in walk(parsed):
        if k == "domains" and isinstance(v, dict):
            ids.update(str(x) for x in v.keys())
    return sorted(ids)


def block_line_range(lines, top_key):
    """[start, end) 0-based line range of a top-level YAML block."""
    start = None
    indent = None
    for i, ln in enumerate(lines):
        if re.match(rf"^{re.escape(top_key)}\s*:", ln):
            start, indent = i, 0
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        cur = len(ln) - len(ln.lstrip(" "))
        if cur <= indent:
            end = j
            break
    return (start, end)


# -------------------------------------------------------------- detectors ----
def hf_a1(text, parsed):
    """F2a: extension_predicate referenced but never defined."""
    hits = [(i + 1, ln.strip()) for i, ln in enumerate(text.splitlines()) if "extension_predicate" in ln]
    defs = []
    if parsed is not None:
        defs = ["/".join(p + (k,)) for p, k, _ in walk(parsed) if k == "extension_predicate"]
    refs = [h for h in hits if not re.match(r"^\s*extension_predicate\s*:", h[1])]
    clause_text = bool(re.search(r"clauses?\s*\(a\)\s*[-–]\s*\(f\)", text, re.I))
    if defs:
        verdict = "REPAIRED_DEFINITION_PRESENT"
    elif refs:
        verdict = "HF_A1_PERSISTS_DANGLING"
    else:
        verdict = "NOT_APPLICABLE_NO_REFERENCE"
    return {
        "id": "HF-A1",
        "artifact": CANON["F2a"],
        "verdict": verdict,
        "definition_key_paths": defs,
        "reference_hits": [{"line": n, "text": t[:160]} for n, t in refs],
        "clauses_a_to_f_defined": clause_text,
        "falsifier": "A definition of extension_predicate (a key with a non-empty body, or explicit clauses (a)-(f)) appearing in the same file as the references voids HF_A1.",
    }


def hf_a2(text, parsed):
    """F2a: conclusion.statement_formal over undefined D0/D_gen."""
    stmt = ""
    quant = ""
    if parsed is not None:
        for v in find_values(parsed, "statement_formal"):
            if isinstance(v, str):
                stmt = v
        for v in find_values(parsed, "formal"):
            if isinstance(v, str) and len(v) > len(quant):
                quant = v
    tokens = sorted({t for t in re.findall(r"\bD_[A-Za-z0-9]+\b|\bD0\b", stmt)})
    defined = domain_ids(parsed) if parsed is not None else []
    dangling = [t for t in tokens if t not in defined]
    disj = bool(re.search(r"\bor\b", stmt, re.I))
    if dangling:
        verdict = "HF_A2_PERSISTS_UNDEFINED_DOMAIN"
    elif tokens:
        verdict = "REPAIRED_DOMAINS_DEFINED"
    else:
        verdict = "NOT_APPLICABLE_NO_DOMAIN_TOKEN"
    return {
        "id": "HF-A2",
        "artifact": CANON["F2a"],
        "verdict": verdict,
        "statement_formal_tokens": tokens,
        "defined_domain_ids": defined,
        "dangling_tokens": dangling,
        "statement_formal_excerpt": stmt[:220],
        "quantifiers_formal_excerpt": quant[:220],
        "statement_formal_contains_or": disj,
        "falsifier": "Every domain token used in conclusion.statement_formal resolving in the file's own domains block, with no disjunctive domain in the conclusion, voids HF_A2.",
    }


NEGATION_PAT = re.compile(
    r"\b(?:no|not|never|neither|nor|without|must\s+not|is\s+not|are\s+not|do\s+not|does\s+not)\b", re.I)
NEGATIVE_CONTEXT = re.compile(
    r"phrases?_that_are_not_this_class|not_this_class|forbidden|anti_scope|composite[_-]regularity[_-]lint|leak", re.I)


def classify_merged_occurrence(lines, i, match):
    """Classify one merged-pattern hit: LINT_BLOCK / NEGATED / QUOTED_FORBIDDEN / ASSERTED."""
    line = lines[i]
    window = lines[max(0, i - 6):i + 1]
    negated = bool(NEGATION_PAT.search(line))
    quoted = bool(re.search(r"['\"][^'\"]*" + re.escape(match.group(0)) + r"[^'\"]*['\"]", line))
    negative_context = any(NEGATIVE_CONTEXT.search(w) for w in window)
    return {
        "negated": negated,
        "quoted": quoted,
        "negative_context_within_6_lines": negative_context,
    }


def hf_b1(text, parsed):
    """F2b: merged-class text outside the lint exemption block.

    The original HF-B1 was a *false self-description*: the file claimed the
    merged-class pattern occurred nowhere outside its lint block while a
    comment carried 'C0 or C2'.  A bare regex hit is not the failure; an
    ASSERTED (non-negated, non-quoted, non-lint) hit is.
    """
    lines = text.splitlines()
    rng = block_line_range(lines, "composite_regularity_lint")
    occ = []
    for i, ln in enumerate(lines):
        for m in MERGED_PAT.finditer(ln):
            inside = bool(rng and rng[0] <= i < rng[1])
            ctx = classify_merged_occurrence(lines, i, m)
            if inside:
                kind = "LINT_BLOCK"
            elif ctx["negated"] or ctx["negative_context_within_6_lines"]:
                kind = "NEGATED"
            elif ctx["quoted"]:
                kind = "QUOTED_FORBIDDEN"
            else:
                kind = "ASSERTED"
            occ.append({"line": i + 1, "match": m.group(0), "kind": kind, "text": ln.strip()[:200], **ctx})
    asserted = [o for o in occ if o["kind"] == "ASSERTED"]
    exemption_claim = None
    if parsed is not None:
        for v in find_values(parsed, "exemption"):
            if isinstance(v, str):
                exemption_claim = v
    claims_zero = bool(exemption_claim and re.search(r"no occurrence|zero|none", exemption_claim, re.I))
    if asserted:
        verdict = "HF_B1_PERSISTS_ASSERTED_MERGED_TEXT"
    elif exemption_claim and claims_zero and len(occ) > 0:
        verdict = "HF_B1_PERSISTS_FALSE_ZERO_CLAIM"
    elif occ:
        verdict = "HF_B1_SIGNATURE_NOT_REPRODUCED"
    else:
        verdict = "NO_MERGED_PATTERN_FOUND"
    return {
        "id": "HF-B1",
        "artifact": CANON["F2b"],
        "verdict": verdict,
        "lint_block_line_range": [rng[0] + 1, rng[1]] if rng else None,
        "occurrences": occ,
        "occurrence_kinds": {k: sum(1 for o in occ if o["kind"] == k) for k in ("LINT_BLOCK", "NEGATED", "QUOTED_FORBIDDEN", "ASSERTED")},
        "asserted_outside": len(asserted),
        "exemption_claim": exemption_claim[:220] if exemption_claim else None,
        "exemption_claims_zero_outside": claims_zero,
        "falsifier": "An ASSERTED merged-class hit at the measured hash (non-negated, non-quoted, outside any lint block), or an exemption claiming zero occurrences while any occurrence exists, voids the clean reading.",
    }


def hf_b2(path, parsed, map_json):
    """F2b: declared node_id vs map node vs filename-derived node."""
    declared = parsed.get("node_id") if isinstance(parsed, dict) else None
    fname_node = FILENAME_NODE.get(path)
    map_nodes = sorted({
        a.get("node_id") for a in map_json.get("assignments", [])
        if a.get("artifact") == path and a.get("node_id")
    })
    gate_scope = None
    for g in map_json.get("gates", []):
        if g.get("gate_id") == "G-FORM":
            gate_scope = g.get("scope")
    mismatch = declared != fname_node
    map_mismatch = bool(map_nodes) and declared not in map_nodes
    if mismatch:
        verdict = "HF_B2_PERSISTS_ID_MISMATCH"
    elif map_mismatch:
        verdict = "HF_B2_REPAIRED_ARTIFACT_SIDE_MAP_RESIDUAL"
    else:
        verdict = "HF_B2_REPAIRED_ID_CONSISTENT"
    return {
        "id": "HF-B2",
        "artifact": path,
        "verdict": verdict,
        "declared_node_id": declared,
        "filename_derived_node": fname_node,
        "map_assignment_nodes_for_path": map_nodes,
        "gate_scope_for_F2": gate_scope,
        "declared_equals_filename_node": not mismatch,
        "declared_in_map_assignment_nodes": not map_mismatch,
        "falsifier": "The artifact declaring a node_id equal to its filename-derived node and to the map assignment node for that path (or the map repointing the path) voids HF_B2.",
    }


def merged_census(texts):
    out = {}
    for rel, blob in texts.items():
        if not rel.endswith((".yaml", ".yml")):
            continue
        occ = [(i + 1, ln.strip()[:120]) for i, ln in enumerate(blob["lines"]) if MERGED_PAT.search(ln)]
        out[rel] = {"occurrences": len(occ), "hits": occ[:8]}
    return out


# ---------------------------------------------------------------- bindings ---
def classify(measured_sha, pin_sha):
    if not pin_sha:
        return "NO_PIN"
    if measured_sha == pin_sha:
        return "MATCH"
    if measured_sha.startswith(pin_sha) or pin_sha.startswith(measured_sha):
        return "MATCH_PREFIX"
    return "STALE_OR_UNKNOWN"


def collect_bindings(map_json, registry, meas_before):
    rows = []

    def add(where, path, pin, note=""):
        m = meas_before.get(path, {})
        rows.append({
            "where": where,
            "path": path,
            "pin": pin,
            "measured": m.get("sha256"),
            "measured_sha8": m.get("sha8"),
            "classification": classify(m.get("sha256") or "", pin or ""),
            "note": note,
        })

    for pair in map_json.get("publication_status", {}).get("pairs", []):
        add("publication_status.canonical", pair.get("canonical"), pair.get("canonical_sha256"), pair.get("status", ""))
        add("publication_status.authoring", pair.get("authoring"), pair.get("authoring_sha256"), pair.get("status", ""))
    for fa in map_json.get("frozen_artifacts", []):
        if fa.get("path") in CANON.values():
            add("frozen_artifacts", fa.get("path"), fa.get("sha256"),
                f"active={fa.get('active')} superseded_at={fa.get('superseded_at')}")
    reg = registry.get("registry", {}) if isinstance(registry, dict) else {}
    for path in CANON.values():
        if path in reg:
            add("artifact_hashes.registry", path, reg[path].get("sha256"), f"bytes={reg[path].get('bytes')}")
    # hashes quoted inside gate unmet prose, bound by label when present
    label_to_path = {v: k for k, v in CANON.items()}
    path_to_label = dict(CANON)
    for g in map_json.get("gates", []):
        for unmet in g.get("unmet", []):
            for h in HEX.findall(unmet):
                labels = [lbl for lbl in path_to_label if re.search(rf"\b{re.escape(lbl)}\b", unmet)]
                if not labels:
                    continue
                for lbl in labels:
                    add(f"gates[{g.get('gate_id')}].unmet[{lbl}]", path_to_label[lbl], h, unmet[:180])
    return rows


# ---------------------------------------------------------------- controls ---
def run_controls(texts):
    f2a = texts[CANON["F2a"]]
    f2b = texts[CANON["F2b"]]

    # C1: merged pattern injected outside the lint block must fire as ASSERTED
    c1_text = "class_note: this record is filed as C0 or C2 in the old draft\n"
    c1_hf = hf_b1(c1_text, None)
    c1 = {"control": "C1 merged-positive-asserted", "expected": ">=1 ASSERTED",
          "observed": c1_hf["occurrence_kinds"]["ASSERTED"],
          "pass": c1_hf["occurrence_kinds"]["ASSERTED"] >= 1}

    # C2: no merged pattern at all must yield zero hits
    c2_text = MERGED_PAT.sub("C0 and C2", f2b["text"])
    c2_occ = [(i + 1) for i, ln in enumerate(c2_text.splitlines()) if MERGED_PAT.search(ln)]
    c2 = {"control": "C2 merged-negative", "expected": "0 hits", "observed": len(c2_occ), "pass": len(c2_occ) == 0}

    # C3: a negative sentence must not be classified ASSERTED
    c3_text = "note: no containment with C2 or C0 is asserted here\n"
    c3_hf = hf_b1(c3_text, None)
    c3 = {"control": "C3 merged-negation-not-asserted", "expected": "0 ASSERTED, 1 NEGATED",
          "observed": c3_hf["occurrence_kinds"],
          "pass": c3_hf["occurrence_kinds"]["ASSERTED"] == 0 and c3_hf["occurrence_kinds"]["NEGATED"] == 1}

    # C4: quoted forbidden phrase under a negative-context heading must not be ASSERTED
    c4_text = "phrases_that_are_not_this_class:\n  - \"any 'C0 or C2' composite regularity\"\n"
    c4_hf = hf_b1(c4_text, None)
    c4 = {"control": "C4 merged-quoted-forbidden-not-asserted", "expected": "0 ASSERTED",
          "observed": c4_hf["occurrence_kinds"],
          "pass": c4_hf["occurrence_kinds"]["ASSERTED"] == 0}

    # C5: defining extension_predicate must flip HF-A1 to repaired on the copy
    c5_text = "extension_predicate:\n  clauses:\n    a: \"isometric embedding\"\n" + f2a["text"]
    c5 = {"control": "C5 hf-a1-positive", "expected": "REPAIRED_DEFINITION_PRESENT",
          "observed": hf_a1(c5_text, yaml.safe_load(c5_text))["verdict"],
          "pass": hf_a1(c5_text, yaml.safe_load(c5_text))["verdict"] == "REPAIRED_DEFINITION_PRESENT"}

    # C6: a synthetic parsed object with an undefined D0 must read as dangling
    c6_parsed = {"quantifiers": {"domains": {"D1": "one class"}},
                 "conclusion": {"statement_formal": "forall D in D0: no C2 extension exists"}}
    c6_text = json.dumps(c6_parsed)
    c6 = {"control": "C6 hf-a2-positive-dangling", "expected": "HF_A2_PERSISTS_UNDEFINED_DOMAIN",
          "observed": hf_a2(c6_text, c6_parsed)["verdict"],
          "pass": hf_a2(c6_text, c6_parsed)["verdict"] == "HF_A2_PERSISTS_UNDEFINED_DOMAIN"}

    # C7: a defined D0 with a single-domain conclusion must read as repaired
    c7_parsed = {"quantifiers": {"domains": {"D0": "one frozen data class"}},
                 "conclusion": {"statement_formal": "forall x in D0: no C2 extension exists"}}
    c7_text = json.dumps(c7_parsed)
    c7 = {"control": "C7 hf-a2-negative-repaired", "expected": "REPAIRED_DOMAINS_DEFINED",
          "observed": hf_a2(c7_text, c7_parsed)["verdict"],
          "pass": hf_a2(c7_text, c7_parsed)["verdict"] == "REPAIRED_DOMAINS_DEFINED"}

    controls = [c1, c2, c3, c4, c5, c6, c7]
    return controls, all(c["pass"] for c in controls)


# -------------------------------------------------------------------- main ---
def main():
    map_json = json.loads(MAP.read_text())
    registry = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}

    meas_before = {rel: measure(rel) for rel in CANON.values()}
    texts = load_texts()

    bindings = collect_bindings(map_json, registry, meas_before)
    controls, controls_ok = run_controls(texts)

    hf = [
        hf_a1(texts[CANON["F2a"]]["text"], texts[CANON["F2a"]]["parsed"]),
        hf_a2(texts[CANON["F2a"]]["text"], texts[CANON["F2a"]]["parsed"]),
        hf_b1(texts[CANON["F2b"]]["text"], texts[CANON["F2b"]]["parsed"]),
        hf_b2(CANON["F2b"], texts[CANON["F2b"]]["parsed"], map_json),
    ]

    meas_after = {rel: measure(rel) for rel in CANON.values()}
    stability = {
        rel: {
            "before": meas_before[rel].get("sha8"),
            "after": meas_after[rel].get("sha8"),
            "stable": meas_before[rel].get("sha256") == meas_after[rel].get("sha256"),
        }
        for rel in CANON.values()
    }
    stable = all(v["stable"] for v in stability.values())

    stale = [b for b in bindings if b["classification"] == "STALE_OR_UNKNOWN"]
    persisting = [h["id"] for h in hf if "PERSISTS" in h["verdict"]]
    repaired = [h["id"] for h in hf if "REPAIRED" in h["verdict"]]

    report = {
        "artifact_id": "w076-gform-hfbind-" + datetime.now(CST).strftime("%Y%m%dT%H%M%S%z"),
        "artifact_kind": "independent_hash_rebind_and_hard_failure_persistence_probe",
        "actor": "worker-076",
        "role": "bounded execution worker (100-slot independent lifecycle)",
        "created_at": now(),
        "task_id": "W076-GFORM-HFBIND-01",
        "node_id": "F2",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "supporting_class_ids": ["AF-WCC-VAC-GEN"],
        "task": (
            "Re-measure the G-FORM unmet hash pins and re-test the four named hard failures "
            "(HF-A1, HF-A2 on F2a; HF-B1, HF-B2 on F2b) at the live canonical revision, because the "
            "map still pins F1 7a3e1f93 / F2a 23fec0e9 / F2b e6b1af2b and F2 at the retired merged artifact."
        ),
        "method": (
            "read-only: sha256 before/after; yaml.safe_load for structure; textual regex for merged-class "
            "and dangling-token detection; hash pins harvested from map.gates[*].unmet, publication_status, "
            "frozen_artifacts and artifact_hashes.registry; five synthetic calibration controls"
        ),
        "measured_canonical": meas_before,
        "hash_stability_window": stability,
        "hash_stable_across_run": stable,
        "controls": controls,
        "controls_ok": controls_ok,
        "bindings": bindings,
        "binding_summary": {
            "total": len(bindings),
            "match": sum(1 for b in bindings if b["classification"].startswith("MATCH")),
            "stale_or_unknown": len(stale),
            "no_pin": sum(1 for b in bindings if b["classification"] == "NO_PIN"),
        },
        "hard_failures": hf,
        "hard_failures_persisting": persisting,
        "hard_failures_explicitly_repaired": repaired,
        "hard_failures_signature_not_reproduced": [h["id"] for h in hf if "NOT_REPRODUCED" in h["verdict"]],
        "merged_class_census_all_canonical": merged_census(texts),
        "observation_log": [
            "00:17:46 publication_status pinned F1 68392dd8 / F2a 4f97273e / F2b a2aef5ac / F0 0fcc6a19 (canonical).",
            "00:19:02 artifact_hashes.registry snapshot carried F1 16128b62 / F2a 4b3dfd76 / F2b 962f33c6.",
            "00:19:14 mtime: all three schema files rewritten again; live hashes became F1 9a8bd4c9 / F2a b6123750 / F2b 1bb78ce9.",
            "00:19:58 publication_status refreshed to the same three live hashes (schemas aligned, taxonomy 276009f4 divergent).",
            "Consequence: every review verdict and every map unmet pin bound to a hash measured before 00:19:14 no longer binds the live artifact.",
        ],
        "headline": (
            ("HASH_UNSTABLE_DURING_RUN " if not stable else "")
            + f"named_hard_failures_persisting={len(persisting)}/{len(hf)} "
            + f"explicitly_repaired={len(repaired)}/{len(hf)} "
            + f"stale_or_unknown_pins={len(stale)}/{len(bindings)}"
        ),
        "interpretation_limits": [
            "This is a textual/structural probe, not a schema review; a REPAIRED verdict means the detector signature is gone, not that the artifact is acceptable.",
            "HF-B2 reports the node-identity convention mismatch quantitatively; whether the fix belongs in the artifact or in the map is a lead/controller decision.",
            "Bindings marked NO_PIN are not failures; they mean the map carries no hash for that path in that slot.",
            "Valid only for the sha256 values measured above; any edit to those files voids the result (recorded in hash_stability_window).",
        ],
        "no_completion_claim": (
            "Worker event: cannot set status=done, validation_status=passed, or any gate verdict. "
            "No theorem, no physics claim. Decision authority stays with lead-formulation / lead-audit / astra."
        ),
        "falsifier": (
            "Re-run this script and find (a) a hash differing from measured_canonical, (b) any control failing, "
            "or (c) a named hard failure reading opposite to hard_failures at the same hash. Substantively: a "
            "reviewer exhibits a definition of extension_predicate (HF-A1), a resolved D0/D_gen domain with a "
            "single-domain conclusion (HF-A2), zero merged-class hits outside the lint block (HF-B1), or a "
            "node_id equal to the filename-derived and map-assignment node (HF-B2)."
        ),
        "next_falsifier": (
            "Re-measure after the next canonical publish: any of the four verdicts flipping without a recorded "
            "artifact event and a new sha256 voids the persistence claim for that item."
        ),
    }

    out = HERE / "probe_result.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    digest = sha256_bytes(out.read_bytes())
    (HERE / "probe_result.json.sha256").write_text(digest + "  probe_result.json\n")
    print(json.dumps({
        "report": str(out.relative_to(ROOT)),
        "sha256": digest,
        "headline": report["headline"],
        "controls_ok": controls_ok,
        "persisting": persisting,
        "stale_pins": [(b["where"], b["path"], b["pin"], b["measured_sha8"]) for b in stale],
        "verdicts": {h["id"]: h["verdict"] for h in hf},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
