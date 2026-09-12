#!/usr/bin/env python3
"""FD13-LEXCEIL-01: does the proposed FD-13 R12 fix generalise past the exact token it keys on?

Context. FD-13 (flash-11, unverified) is the field-global scope of the canonical R12 geodesic
exemption in artifacts/formulation/tools/check_class_schema.py (000e09e4): the check is
`INEXTENDIB.search(field) and not GEODESIC.search(field)`, so one legitimate geodesic word
anywhere in `non_vacuity.condition` exempts every non-geodesic (SCC-style) inextendibility
assertion in that field. The proposed patch (5eaab3f8) applies the same regexes per clause,
`re.split(r"(?<=[.;])\\s+", field)`. Both detectors are token detectors; the patch only changes
the *granularity* of the token search. This script bounds what the patch can and cannot close.

Probe families (all byte-minimal: frozen WCC schema + exactly one appended sentence inside
non_vacuity.condition, anchor `(worker-16 F1-16-03 accepted).`):
  A  contains the INEXTENDIB token in its own `.`/`;` clause   -> patch should catch at R12
  B  contains the INEXTENDIB token, comma/`and`/`while`-joined to a geodesic word in the SAME
     clause (no `.`/`;` between)                               -> patch predicted to escape
  C  asserts non-geodesic inextendibility in words that avoid the INEXTENDIB token entirely
     (isometric-embedding / no-continuation / no-larger-manifold phrasings) -> both escape
  K  controls: legitimate geodesic statements, must stay accepted

Falsifier (falsifiable, reported whether or not it fires):
  FIRED IF (a) any family-C probe is rejected by canonical_patched at R12 (the lexical-ceiling
  reading would be false), or (b) any family-B probe is rejected by canonical_patched at R12
  (the punctuation-sensitivity mechanism claim would be false), or (c) any control is rejected
  by any gate, or any canonical schema copy is rejected, or (d) an asserted pin hash moves
  before the run (binding abort before measurement). Rejections by rules other than R12 are
  reported as confounds, not as falsifier firings.

Read-only w.r.t. every shared tree; writes only under this directory.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml  # noqa: E402  (used only to reject malformed probe fixtures before measuring)

CST = timezone(timedelta(hours=8))

HERE = Path(__file__).resolve().parent
BIND = HERE.parent
REPO = BIND.parents[2]

CANON_BASE = REPO / "artifacts/formulation/tools/check_class_schema.py"
CANON_PATCHED = BIND / "fd13_rev26/patched/tools/patched_check_class_schema.py"
CANON_PATCHED_ENV = BIND / "fd13_rev26/patched"
FLASH11 = BIND / "check_schema.py"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
KEY_MANIFEST = REPO / "artifacts/formulation/KEY_MANIFEST.json"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
SCHEMAS = REPO / "artifacts/formulation/schemas"
SCHEMA_NAMES = ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")
WCC = SCHEMAS / "af_wcc_vacuum.yaml"
ANCHOR = '(worker-16 F1-16-03 accepted)."'

PINS = {
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/flash-11/f1_aux_class_binding/check_schema.py":
        "a89b221c1c68e34f87776e5648a8e890d2a0f9f0b919280d3e176422b2d689f0",
    "artifacts/flash-11/f1_aux_class_binding/fd13/tools/patched_check_class_schema.py":
        "5eaab3f8f031396e9d787fd975ebc9d2a647cab6d144cd4a3c31ea45e70b215d",
}

IMPLS = {
    "canonical_base": {"path": CANON_BASE, "cwd": CANON_BASE.parent, "kind": "canonical"},
    "canonical_patched": {"path": CANON_PATCHED, "cwd": CANON_PATCHED_ENV / "tools",
                          "kind": "canonical"},
    "flash11": {"path": FLASH11, "cwd": BIND, "kind": "flash11"},
}

# probe_id, family, intent, sentence
PROBES = [
    ("A1_inextendib_own_clause", "A",
     "SCC-style non-geodesic inextendibility, own clause",
     " The maximal development is C^2-inextendible."),
    ("A2_inextendib_own_clause_manifold", "A",
     "SCC-style non-geodesic inextendibility, own clause",
     " The maximal development is future-inextendible as a Lorentzian manifold of the same regularity."),
    ("A3_semicolon_split", "A",
     "token separated from the geodesic preamble by a semicolon",
     " No extension of the development exists beyond this boundary; the development is inextendible."),
    ("B1_comma_joined_geodesic", "B",
     "non-geodesic claim comma-joined to a geodesic word in one clause",
     " The spacetime is geodesically complete, and the maximal development is C^2-inextendible."),
    ("B2_and_joined_geodesic", "B",
     "non-geodesic claim after a geodesic witness in one clause",
     " Singularities are witnessed by future-inextendible causal geodesics, but the maximal development is also inextendible as a manifold."),
    ("B3_while_joined_geodesic", "B",
     "non-geodesic claim while-joined to a geodesic word in one clause",
     " The data are future geodesically incomplete, while the maximal development is inextendible."),
    ("C1_no_extension_embedding", "C",
     "no INEXTENDIB token: no extension as a C^{1,1} Lorentzian manifold",
     " The maximal development admits no extension as a C^{1,1} Lorentzian manifold."),
    ("C2_no_isometric_embedding", "C",
     "no INEXTENDIB token: no isometric embedding into a larger manifold",
     " There is no isometric embedding of the maximal development into a larger Lorentzian manifold of the same regularity."),
    ("C3_no_causal_continuation", "C",
     "no INEXTENDIB token: no causal continuation past the boundary",
     " The maximal development cannot be continued beyond this boundary by any causal curve."),
    ("C4_no_larger_supermanifold", "C",
     "no INEXTENDIB token: no larger manifold contains the development properly",
     " No larger Lorentzian manifold of the same regularity contains the maximal development as a proper open subset."),
    ("K1_geodesic_witness", "K",
     "control: legitimate geodesic-inextendibility statement",
     " Any singular point is witnessed by a future-inextendible causal geodesic of finite affine length."),
    ("K2_geodesic_comma_joined", "K",
     "control: geodesic statement with a comma-joined second clause",
     " Every singular point is witnessed by a future-inextendible causal geodesic, and the boundary is reached at finite affine length."),
    ("K3_geodesic_split", "K",
     "control: geodesic statement split across two clauses",
     " Any singular point is witnessed by a future-inextendible causal geodesic. The boundary is reached at finite affine length."),
]

CANON_TARGETS = [(f"canonical_{n}", n) for n in SCHEMA_NAMES]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_binding() -> dict:
    frozen = json.loads(FROZEN.read_text())
    binding = {"frozen_manifest_sha256": sha256_file(FROZEN),
               "frozen_revision": frozen.get("revision"),
               "frozen_at": frozen.get("frozen_at"), "checks": [], "schemas": [], "problems": []}
    for rel, want in PINS.items():
        p = REPO / rel
        real = sha256_file(p) if p.exists() else "MISSING"
        if real != want:
            binding["problems"].append(f"pin mismatch {rel}: {real} != {want}")
        binding["checks"].append({"path": rel, "expected_sha256": want, "disk_sha256": real,
                                  "match": real == want})
    for name in SCHEMA_NAMES:
        rel = f"artifacts/formulation/schemas/{name}"
        man = (frozen.get("files", {}).get(rel) or {}).get("sha256")
        real = sha256_file(SCHEMAS / name)
        if man != real:
            binding["problems"].append(f"manifest does not bind {rel}: {man} != {real}")
        binding["schemas"].append({"path": rel, "disk_sha256": real,
                                   "frozen_manifest_sha256": man,
                                   "frozen_manifest_matches_disk": man == real})
    binding["patched_env_rule_spec_sha256"] = sha256_file(CANON_PATCHED_ENV / "rule_spec.json")
    binding["patched_env_key_manifest_sha256"] = sha256_file(CANON_PATCHED_ENV / "KEY_MANIFEST.json")
    if binding["patched_env_rule_spec_sha256"] != PINS["artifacts/formulation/rule_spec.json"]:
        binding["problems"].append("patched env rule_spec != pinned rule_spec")
    if binding["patched_env_key_manifest_sha256"] != PINS["artifacts/formulation/KEY_MANIFEST.json"]:
        binding["problems"].append("patched env KEY_MANIFEST != pinned manifest")
    return binding


def run_gate(gate: str, fixture: Path) -> dict:
    spec = IMPLS[gate]
    cmd = [sys.executable, str(spec["path"]), str(fixture), "--json"]
    try:
        proc = subprocess.run(cmd, cwd=spec["cwd"], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"verdict": "error", "rule_ids": [], "detail": "timeout(90s)"}
    try:
        payload = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"verdict": "crash" if "Traceback" in proc.stderr else "error", "rule_ids": [],
                "detail": (proc.stderr.strip().splitlines() or [""])[-1][:200]}
    if spec["kind"] == "flash11":
        rec = payload[0] if isinstance(payload, list) else payload
        return {"verdict": {"ACCEPT": "accept", "REJECT": "reject"}.get(rec.get("verdict"), "error"),
                "rule_ids": rec.get("failed_codes", []), "detail": rec.get("layout", "")}
    return {"verdict": "accept" if payload.get("verdict") == "pass" else
                       ("reject" if payload.get("verdict") == "fail" else "error"),
            "rule_ids": payload.get("failed_rules", []),
            "failures": payload.get("failures", payload.get("failed_checks", [])), "detail": ""}


def main() -> int:
    binding = check_binding()
    if binding["problems"]:
        print("BINDING ABORT: " + "; ".join(binding["problems"]), file=sys.stderr)
        (HERE / "lexceiling_binding_abort.json").write_text(json.dumps(binding, indent=2))
        return 2

    # byte copies of the measured canonical schemas (binding recorded, not asserted)
    for name in SCHEMA_NAMES:
        (HERE / f"canonical_{name}").write_bytes((SCHEMAS / name).read_bytes())

    if WCC.read_bytes().count(ANCHOR.encode()) != 1:
        print(f"BINDING ABORT: anchor not unique in {WCC}", file=sys.stderr)
        return 2

    rows = []
    parse_errors = []
    for pid, fam, intent, sentence in PROBES:
        fx = HERE / f"probe_{pid}.yaml"
        fx.write_bytes(WCC.read_bytes().replace(
            ANCHOR.encode(), (ANCHOR[:-1] + sentence + '"').encode()))
        try:
            doc = yaml.safe_load(fx.read_text())
        except yaml.YAMLError as exc:
            parse_errors.append(f"{pid}: {exc}")
            doc = None
        row = {"probe_id": pid, "family": fam, "intent": intent, "sentence": sentence.strip(),
               "fixture": fx.name, "fixture_sha256": sha256_file(fx),
               "yaml_parses": doc is not None,
               "mutated_field_value": doc.get("non_vacuity", {}).get("condition") if doc else None,
               "verdicts": {}}
        for gate in IMPLS:
            row["verdicts"][gate] = run_gate(gate, fx)
        pv = row["verdicts"]["canonical_patched"]
        bv = row["verdicts"]["canonical_base"]
        fv = row["verdicts"]["flash11"]
        row["classification"] = {
            "base_escapes": bv["verdict"] == "accept",
            "patched_r12_catch": pv["verdict"] == "reject" and "R12" in pv["rule_ids"],
            "patched_escape": pv["verdict"] == "accept",
            "patched_other_rule_reject": pv["verdict"] == "reject" and "R12" not in pv["rule_ids"],
            "flash11_r12_catch": fv["verdict"] == "reject" and "R12" in fv["rule_ids"],
            "confound_rules": sorted({r for r in pv["rule_ids"] if r != "R12"}) if pv["verdict"] == "reject" else [],
        }
        rows.append(row)

    # canonical unmodified schemas as controls
    for fname, orig in CANON_TARGETS:
        fx = HERE / fname
        ros = {"probe_id": f"K4_{orig}", "family": "K", "intent": "control: frozen schema unchanged",
               "sentence": None, "fixture": fname, "fixture_sha256": sha256_file(fx),
               "verdicts": {g: run_gate(g, fx) for g in IMPLS}}
        ros["classification"] = {"base_escapes": None,
                                 "patched_r12_catch": False, "patched_escape": ros["verdicts"]["canonical_patched"]["verdict"] == "accept",
                                 "patched_other_rule_reject": ros["verdicts"]["canonical_patched"]["verdict"] == "reject" and "R12" not in ros["verdicts"]["canonical_patched"]["rule_ids"],
                                 "flash11_r12_catch": False, "confound_rules": []}
        rows.append(ros)

    def fam(f):
        return [r for r in rows if r["family"] == f]

    A, B, C, K = fam("A"), fam("B"), fam("C"), fam("K")
    fired = []
    if any(r["classification"]["patched_r12_catch"] for r in C):
        fired.append("(a) a family-C token-free paraphrase was caught by canonical_patched at R12")
    if any(r["classification"]["patched_r12_catch"] for r in B):
        fired.append("(b) a family-B punctuation-joined probe was caught by canonical_patched at R12")
    for r in K:
        for g, v in r["verdicts"].items():
            if v["verdict"] != "accept":
                fired.append(f"(c) control {r['probe_id']} rejected by {g}: {v['rule_ids']}")
    for r in C:
        if r["classification"]["patched_other_rule_reject"]:
            fired.append(f"(confound-only) family-C {r['probe_id']} rejected by canonical_patched on "
                         f"non-R12 rules {r['classification']['confound_rules']}")

    stats = {
        "A_total": len(A),
        "A_base_escape": sum(r["classification"]["base_escapes"] for r in A),
        "A_patched_r12_catch": sum(r["classification"]["patched_r12_catch"] for r in A),
        "B_total": len(B),
        "B_base_escape": sum(r["classification"]["base_escapes"] for r in B),
        "B_patched_r12_catch": sum(r["classification"]["patched_r12_catch"] for r in B),
        "B_patched_escape": sum(r["classification"]["patched_escape"] for r in B),
        "C_total": len(C),
        "C_base_escape": sum(r["classification"]["base_escapes"] for r in C),
        "C_patched_r12_catch": sum(r["classification"]["patched_r12_catch"] for r in C),
        "C_patched_escape": sum(r["classification"]["patched_escape"] for r in C),
        "K_total": len(K),
        "K_false_positives": sum(1 for r in K for v in r["verdicts"].values() if v["verdict"] != "accept"),
        "flash11_r12_catch_total": sum(1 for r in rows if r["family"] in "ABC" and r["classification"]["flash11_r12_catch"]),
        "yaml_parse_errors": parse_errors,
    }

    if fired and all(x.startswith("(confound-only)") for x in fired):
        state = "LEXICAL_CEILING_CONFIRMED_WITH_CONFOUNDS"
    elif fired:
        state = "FALSIFIER_FIRED"
    else:
        state = "LEXICAL_CEILING_CONFIRMED"

    out = {
        "artifact": "FD13-LEXCEIL-01 lexical-ceiling probes for the proposed R12 clause-local fix",
        "status": "unverified worker measurement; no completion claim; schema owner binds interpretation",
        "task_id": "FD13-LEXCEIL-01",
        "proposed_under": "assign-FORM-DIFF-02-20260911T2331 (FORM-DIFF-02 stopped at 3.0h budget; this is a new bounded card proposal)",
        "node_id": "F1", "group_id": "formulation", "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "binding": binding,
        "summary": {
            "detectors_are_token_detectors": "INEXTENDIB=/inextendib/i, GEODESIC=/geodesic/i; the "
                "patch only moves the same token test from field scope to clause scope",
            "state": state,
            "A_token_separate_clause": f"{stats['A_patched_r12_catch']}/{stats['A_total']} caught by patched at R12; "
                                        f"{stats['A_base_escape']}/{stats['A_total']} still escaped by base",
            "B_token_joined_to_geodesic": f"{stats['B_patched_escape']}/{stats['B_total']} escape the patched gate "
                                          f"({stats['B_patched_r12_catch']} R12 catches)",
            "C_no_token_paraphrase": f"{stats['C_patched_escape']}/{stats['C_total']} escape the patched gate "
                                     f"({stats['C_patched_r12_catch']} R12 catches)",
            "controls": f"{stats['K_total']} controls, {stats['K_false_positives']} false positives across all gates",
        },
        "falsifier": {
            "statement": ("FIRED IF (a) any family-C token-free paraphrase is rejected by canonical_patched at R12, "
                          "or (b) any family-B punctuation-joined probe is rejected by canonical_patched at R12, "
                          "or (c) any control/canonical schema is rejected by any gate, or (d) an asserted pin moves "
                          "(binding abort). Non-R12 rejections are confounds, reported separately."),
            "fired": bool([x for x in fired if not x.startswith("(confound-only)")]),
            "reasons": fired,
        },
        "probes": rows,
        "stats": stats,
        "interpretation": {
            "what_the_patch_closes": "period/semicolon-separated INEXTENDIB-token leaks in non_vacuity.condition",
            "what_it_does_not_close": [
                "family B: the same token joined to a geodesic word by a comma/and/while in one clause",
                "family C: non-geodesic inextendibility phrased without the INEXTENDIB token (isometric embedding, "
                "no extension as a C^{1,1} manifold, no causal continuation, no larger supermanifold)",
            ],
            "consequence": "the clause-local fix is an improvement over the field-global guard but does not make the "
                           "check semantic or punctuation-insensitive; a class crossing of the FD-13 kind survives in "
                           "the patched gate on the same frozen schema",
            "owner_action": "do not score FD-13 closed on the patch alone; a semantic predicate (or an explicit "
                            "class-content check on assertive paths) is required for the C-side channels",
        },
        "non_claims": ["no canonical bytes modified", "no gate verdict", "no node completion",
                       "no claim about physics content beyond schema-surface tokens"],
    }
    (HERE / "lexceiling_results.json").write_text(json.dumps(out, indent=2) + "\n")

    live_tool = sha256_file(CANON_BASE)
    out["stability"] = {"tool_after_run_sha256": live_tool,
                        "tool_stable_during_run": live_tool == PINS["artifacts/formulation/tools/check_class_schema.py"],
                        "schema_equal_live": all(sha256_file(HERE / f"canonical_{n}") == sha256_file(SCHEMAS / n)
                                                 for n in SCHEMA_NAMES)}
    (HERE / "lexceiling_results.json").write_text(json.dumps(out, indent=2) + "\n")

    print(json.dumps({"state": state, "falsifier_fired": out["falsifier"]["fired"],
                      "reasons": fired, "stats": stats}, indent=2))
    print("results sha256:", sha256_file(HERE / "lexceiling_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
