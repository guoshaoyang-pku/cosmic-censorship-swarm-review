#!/usr/bin/env python3
"""W041-XSCHEMA-DATACLASS-01 — independent cross-schema data-class identity and
class-binding measurement for F1/F2a/F2b at the rev12 frozen hashes.

Reviewer: worker-041.  Classes: AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN.
Nodes: F1, F2a, F2b.  Gates: G-FORM (primary), G-AUDIT / A1 (secondary).

Motivation (not assumed): worker-088's F1 verdict flags
`cross_schema_summary: strict_data_class_shared=false` as "adjudication required".
This instrument measures *what actually differs* between the three schemas'
data_class/topology/regularity blocks and separates, by a rule fixed before the run:
  (C) SHARED CORE that must be identical across the three classes;
  (A) CLASS AXIS fields whose divergence IS the C0/C2/WCC distinction;
  (E) editorial/provenance-only differences.
Only an unexplained difference on a shared-core field is a failure.

Detector-bug guard: the first draft of this instrument used a whole-block
numeric-multiset rule and flagged (i) class-defining fields (F1 "none" vs F2a "C2" vs
F2b "C0") and (ii) the schemas' own `must_not_conflate` prohibition text that names
C2/C0 in order to forbid conflation (the controller's CF-16 metalinguistic-mention
pattern).  Both were detector false positives and are corrected here; the raw first-run
output is retained at raw/checks.draft1.json for audit.

Pre-registered checks
  X1 hashes: measured sha256 of the three canonical schemas == rev12/FROZEN-rev28 pins.
  X2 d0_verbatim: quantifiers.domains.D0.definition identical across F1/F2a/F2b (G-FORM).
  X3 shared_core_identity: every SHARED_CORE path exists in all three and is identical
     after whitespace/case normalisation (equations, matter, Lambda, constraints,
     s/delta, decay-rate forms, slice topology, dimension, completeness).
  X4 class_axis_binding: extension_regularity is exactly {F1: none, F2a: C2, F2b: C0}
     and matches each class contract's regularity_token; C0 and C2 are not merged in
     any ASSERTION field (class_id, class_components, extension_regularity, conclusion
     statement/type); prohibition text (`must_not_conflate`, `forbidden_*`) is excluded
     from the merge scan by construction (CF-16).
  X5 diff_census: every difference in the three blocks classified C/A/E; zero
     unexplained (non-core, non-class-axis, meaning-bearing) differences.
  X6 controls: (pos) in-memory mutation of a shared-core exponent and of a
     shared-core decay rate must be flagged; (neg) a wording-only change must not.
     If any control fails the run is INVALID.

Determinism / fail-closed: all three target hashes are measured before and after; the
run exits 3 if any target moves.  Read-only on live artifacts: writes are confined to
artifacts/worker-041/xschema_dataclass/.
Authority: measurement only — no node status, no validation promotion, no gate verdict.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

TARGETS = {
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "class_id": "AF-WCC-VAC-GEN",
        "pin": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "expect_extension_regularity": "none",
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "pin": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "expect_extension_regularity": "c2",
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "pin": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "expect_extension_regularity": "c0",
    },
}
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPPL = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
VOCAB = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"

BLOCKS = ("data_class", "topology", "regularity")

# (C) must be identical across the three classes — the G-FORM data-class core
SHARED_CORE = (
    "data_class.matter",
    "data_class.cosmological_constant",
    "data_class.equations",
    "data_class.constraints.hamiltonian",
    "data_class.constraints.momentum",
    "data_class.regularity_class.default",
    "data_class.regularity_class.sobolev_variant.s",
    "data_class.regularity_class.sobolev_variant.delta",
    "data_class.asymptotic_decay.metric",
    "data_class.asymptotic_decay.second_fundamental_form",
    "topology.spacetime_dimension",
    "topology.slice_topology",
    "topology.completeness_of_slice",
)
# (A) class-defining fields; divergence expected and checked against the class token
CLASS_AXIS_PREFIXES = (
    "regularity.extension_regularity",
    "regularity.extension_solution_concept",
    "regularity.must_not_conflate",
    "topology.extension_topology",
    "topology.horizon_topology",
    "data_class.excluded_data",
)
RATE_RE = re.compile(r"o\(r\^\{?(-?\d+)\}?\)")
EQUATION_TOKENS = ("ric", "r(h)", "k_ij", "d^j", "delta_ij", "r^3", "c^infinity", "h^s")
# word-boundary token matcher: substring matching made "numeric" contain "ric"
TOKEN_RE = {t: re.compile(r"(?<![a-z0-9_])" + re.escape(t) + r"(?![a-z0-9_])") for t in EQUATION_TOKENS}


def tokens_present(text) -> tuple:
    n = norm(text)
    return tuple(t for t in EQUATION_TOKENS if TOKEN_RE[t].search(n))


class DupKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    keys = set()
    for k, _v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise ValueError(f"duplicate YAML key {key!r} at line {k.start_mark.line + 1}")
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower().rstrip(".")


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def rates(text) -> tuple:
    return tuple(sorted(RATE_RE.findall(norm(text))))


def canon(vocab, kind, tok):
    for c, al in vocab[kind].items():
        if tok == c or tok in al:
            return c
    return tok


def main() -> int:
    now = datetime.now(TZ)
    before = {k: sha256(ROOT / v["path"]) for k, v in TARGETS.items()}
    frozen = json.load(open(FROZEN))
    frozen_pins = {k: frozen["files"].get(v["path"], {}).get("sha256") for k, v in TARGETS.items()}

    docs, parse = {}, {}
    for k, v in TARGETS.items():
        try:
            docs[k] = yaml.load(open(ROOT / v["path"]), Loader=DupKeyLoader)
            parse[k] = "PASS"
        except Exception as exc:  # pragma: no cover
            docs[k] = yaml.safe_load(open(ROOT / v["path"]))
            parse[k] = f"FAIL: {exc}"

    checks = []

    def chk(cid, ok, detail, evidence=None):
        checks.append({"check_id": cid, "status": "PASS" if ok else "FAIL",
                       "detail": detail, "evidence": evidence})
        return ok

    # X1
    chk(
        "X1_target_hashes_match_rev12_and_frozen_rev28_pins",
        all(before[k] == v["pin"] for k, v in TARGETS.items())
        and all(frozen_pins[k] == before[k] for k in TARGETS),
        "; ".join(f"{k}={before[k][:12]} pin={v['pin'][:12]} frozen={str(frozen_pins[k])[:12]}"
                  for k, v in TARGETS.items()),
        {"frozen_revision": frozen.get("revision")},
    )

    # X2
    d0s = {k: norm(((d.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", ""))
           for k, d in docs.items()}
    chk("X2_d0_definition_verbatim_shared",
        len(set(d0s.values())) == 1 and "" not in d0s.values(),
        f"{len(set(d0s.values()))} distinct D0 definition(s)", {k: v[:160] for k, v in d0s.items()})

    leaf_maps = {k: dict(leaves({b: d.get(b) for b in BLOCKS})) for k, d in docs.items()}

    # X3 shared core
    core_rows, core_bad = [], []
    for p in SHARED_CORE:
        vals = {k: leaf_maps[k].get(p, "<ABSENT>") for k in TARGETS}
        ok = len(set(norm(v) for v in vals.values())) == 1 and "<ABSENT>" not in vals.values()
        row = {"path": p, "values": {k: norm(v)[:200] for k, v in vals.items()}, "identical": ok}
        core_rows.append(row)
        if not ok:
            core_bad.append(row)
    chk("X3_shared_core_identity", not core_bad,
        f"{len(SHARED_CORE) - len(core_bad)}/{len(SHARED_CORE)} shared-core paths identical across F1/F2a/F2b",
        {"non_identical": core_bad})

    # X4 class axis + no C0/C2 merge in assertion fields
    axis_rows, axis_bad = [], []
    for k, v in TARGETS.items():
        er = norm(((docs[k].get("regularity") or {}).get("extension_regularity")))
        comp_tok = norm((docs[k].get("class_components") or {}).get("regularity_token"))
        exp = v["expect_extension_regularity"]
        ok = er == exp and (comp_tok == exp or (exp == "none" and comp_tok == "none"))
        axis_rows.append({"target": k, "extension_regularity": er,
                          "class_components.regularity_token": comp_tok, "expected": exp, "ok": ok})
        if not ok:
            axis_bad.append(axis_rows[-1])
    merged = {}
    for k, d in docs.items():
        conc = d.get("conclusion") or {}
        assertion_blob = json.dumps({
            "class_id": d.get("class_id"),
            "class_components": d.get("class_components"),
            "extension_regularity": (d.get("regularity") or {}).get("extension_regularity"),
            "conclusion_type": conc.get("conclusion_type"),
            "statement_natural_language": conc.get("statement_natural_language"),
            "statement_formal": conc.get("statement_formal"),
        }).lower()
        merged[k] = bool(re.search(r"c0\s*(or|/)\s*c2|c2\s*(or|/)\s*c0", assertion_blob))
    chk("X4_class_axis_binding_no_c0_c2_merge",
        not axis_bad and not any(merged.values()),
        f"axis rows ok={sum(1 for r in axis_rows if r['ok'])}/3; "
        f"C0/C2 merge token in assertion fields={merged} (prohibition text excluded, CF-16)",
        {"axis_rows": axis_rows})

    # X5 full diff census with C/A/E classification
    all_paths = sorted(set().union(*[set(m) for m in leaf_maps.values()]))
    c_core, a_axis, e_edit, unexplained = [], [], [], []
    for p in all_paths:
        vals = {k: leaf_maps[k].get(p, "<ABSENT>") for k in TARGETS}
        if len(set(norm(v) for v in vals.values())) == 1:
            continue
        rec = {"path": p, "values": {k: norm(v)[:200] for k, v in vals.items()},
               "present_in": [k for k in TARGETS if vals[k] != "<ABSENT>"]}
        if p in SHARED_CORE:
            rec["class"] = "C_shared_core"; c_core.append(rec)
        elif p.startswith(CLASS_AXIS_PREFIXES):
            rec["class"] = "A_class_axis"; a_axis.append(rec)
        else:
            # non-core, non-axis: meaning-bearing only if decay rates or equation tokens move
            ra = {k: rates(vals[k]) for k in TARGETS}
            ta = {k: tokens_present(vals[k]) for k in TARGETS}
            if len(set(ra.values())) > 1 or len(set(ta.values())) > 1:
                rec["class"] = "U_unexplained_semantic"; unexplained.append(rec)
            else:
                rec["class"] = "E_editorial"; e_edit.append(rec)
    chk("X5_diff_census_no_unexplained_difference", not unexplained,
        f"{len(all_paths)} leaf paths; shared-core diff={len(c_core)}, class-axis diff={len(a_axis)}, "
        f"editorial diff={len(e_edit)}, unexplained semantic diff={len(unexplained)}",
        {"unexplained": unexplained})

    # X6 controls: shared-core mutations must be flagged, wording must not
    def core_classifier(path, a, b):
        if norm(a) == norm(b):
            return False
        if path in SHARED_CORE:
            return True
        if rates(a) != rates(b):
            return True
        return tokens_present(a) != tokens_present(b)

    s_old = docs["F2a"]["data_class"]["regularity_class"]["sobolev_variant"]["s"]
    r_old = docs["F2a"]["data_class"]["asymptotic_decay"]["metric"]
    pos1 = core_classifier("data_class.regularity_class.sobolev_variant.s", s_old, "s > 2")
    pos2 = core_classifier("data_class.asymptotic_decay.metric", r_old, "h_ij - delta_ij = O(r^{-2})")
    neg = core_classifier("data_class.regularity_class.sobolev_variant.status",
                          "standard_choice; UNVERIFIED citation",
                          "standard choice; unverified citation (provenance note)")
    chk("X6_classifier_controls", pos1 and pos2 and not neg,
        f"exponent mutation flagged={pos1}; rate mutation flagged={pos2}; wording change flagged={neg}")

    # X7 class binding vs canonical taxonomy + supplement
    vocab = json.load(open(VOCAB))
    canon_doc = yaml.safe_load(open(F0_CANON))
    supp_doc = yaml.safe_load(open(F0_SUPPL))
    binding, bind_bad = {}, []
    for k, v in TARGETS.items():
        cid = v["class_id"]
        comp = docs[k].get("class_components") or {}
        caxes = ((canon_doc.get("classes") or {}).get(cid) or {}).get("axes") or {}
        sclass = (supp_doc.get("class_contracts") or {}).get(cid) or {}
        scomp = sclass.get("components") or {}
        ct_canon = canon(vocab, "conclusion_type", caxes.get("conclusion_type"))
        ct_supp = canon(vocab, "conclusion_type", sclass.get("conclusion_type"))
        ct_schema = canon(vocab, "conclusion_type", (docs[k].get("conclusion") or {}).get("conclusion_type"))
        ok = (
            docs[k].get("class_id") == cid
            and str(comp.get("asymptotics")) == "AF" and str(comp.get("matter")) == "VAC"
            and str(comp.get("genericity")) == "GEN"
            and str(scomp.get("censorship")) == str(comp.get("censorship"))
            and str(scomp.get("matter")) == "VAC"
            and ct_canon == ct_supp == ct_schema
        )
        binding[k] = {"schema_class_components": comp, "canonical_axes": caxes,
                      "supplement_components": scomp,
                      "conclusion_type_schema/canonical/supplement": [ct_schema, ct_canon, ct_supp],
                      "status": "PASS" if ok else "FAIL"}
        if not ok:
            bind_bad.append(k)
    chk("X7_class_binding_taxonomy_and_supplement", not bind_bad,
        f"binding rows pass={3 - len(bind_bad)}/3; failing={bind_bad}",
        {"binding": {k: binding[k]["status"] for k in binding}})

    after = {k: sha256(ROOT / v["path"]) for k, v in TARGETS.items()}
    stable = before == after
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")

    report = {
        "schema_version": "0.1",
        "record_id": "W041-XSCHEMA-DATACLASS-01-report",
        "task_id": "W041-XSCHEMA-DATACLASS-01",
        "actor": "worker-041",
        "created_at": now.isoformat(),
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "secondary_gate": "G-AUDIT/A1",
        "measurement_kind": "cross-schema data-class identity + class binding, hash-pinned",
        "authority": "measurement only; no gate verdict, no node status, no validation promotion",
        "parser_status": parse,
        "measured_sha256": before,
        "frozen_rev28_pins": frozen_pins,
        "frozen_revision": frozen.get("revision"),
        "hash_stable_across_run": stable,
        "n_pass": sum(1 for c in checks if c["status"] == "PASS"),
        "n_fail": n_fail,
        "checks": checks,
        "shared_core_rows": core_rows,
        "class_axis_rows": axis_rows,
        "class_binding": binding,
        "diff_census": {"shared_core": c_core, "class_axis": a_axis,
                        "editorial": e_edit, "unexplained_semantic": unexplained},
        "detector_bug_log": [
            "draft1 flagged 14 class-differentiating differences by whole-block numeric-multiset rule; "
            "all were class-axis fields (extension_regularity none/C2/C0, extension_topology, "
            "must_not_conflate warnings) or identifier digits (l1, timestamps) — false positives.",
            "draft1 C0/C2 merge scan hit F2b must_not_conflate text that names C2 in order to forbid "
            "conflation (controller CF-16 metalinguistic-mention pattern) — false positive.",
            "draft2 flagged sobolev_variant.status as semantic because the substring 'ric' matched "
            "inside 'numeric' in F1's provenance sentence — fixed by word-boundary token matching.",
        ],
    }
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "raw").mkdir(exist_ok=True)
    out = HERE / "xschema_report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    (HERE / "raw" / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
    (HERE / "raw" / "diff_census.json").write_text(json.dumps(report["diff_census"], indent=1) + "\n")
    print(json.dumps({c["check_id"]: c["status"] for c in checks}, indent=1))
    print(f"report={out} sha256={sha256(out)[:12]} n_fail={n_fail} stable={stable}")
    return 3 if not stable else (0 if n_fail == 0 else 1)


if __name__ == "__main__":
    import shutil
    draft = HERE / "xschema_report.json"
    if draft.exists():
        (HERE / "raw").mkdir(exist_ok=True)
        shutil.copy(draft, HERE / "raw" / "report.draft1.json")
    sys.exit(main())
