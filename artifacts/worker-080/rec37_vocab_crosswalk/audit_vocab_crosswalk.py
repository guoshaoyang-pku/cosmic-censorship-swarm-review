#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W080-REC37-VOCAB-CROSSWALK-01 -- assertion-correct consistency check for the
conclusion_type crosswalk (REC-37 / REC-36 item 4).

Read-only on every canonical path.  Deterministic.  Fail-closed on pin drift.
No network.  Requires PyYAML (already used by the canonical tools).

Checks
------
Live run (all active):
  V1  crosswalk internal schema
  V2  alias partition (canonical distinct; true-alias sets disjoint; no
      collision with canonicals; recomputed from live VOCAB_ALIASES.json)
  V3  F0 allowed-list coverage: every F0 allowed entry maps to exactly one
      canonical token; recorded status matches recomputation
  V4  asserted schema token is a CANONICAL token (never an alias)
  V5  no true-alias token in an asserted YAML scalar position
      (assertion-vs-mention: comment lines and mention-context keys excluded)
  V6  R11 binding: asserted token == rule_spec.vocabularies.class_conclusion_type[class_id]
  V7  crosswalk line anchors point at the recorded token  (binding)
  V8  mirror identity: schemas/ vs artifacts/formulation/schemas/ byte-identical
  V9  F0 no-write invariant: measured allowed list == crosswalk record  (binding)
  V10 every pin is declared in FROZEN.json with the same sha256          (binding)
  V11 pin guard: measured sha256 == declared pin                        (binding)
  V12 binding structural gate passes on all three canonical schemas     (binding)

Sandbox mutation controls (never touch canonical paths):
  K0  baseline unmutated sandbox -> no findings
  K1  alias dropped into conclusion.conclusion_type -> V4 fires
  K1b alias in a new asserted scalar -> V5 fires
  K2  unknown token in conclusion_type -> V4 and V6 fire
  K3  cross-class canonical token in F1 -> V6 fires
  K4  alias collision injected into VOCAB_ALIASES.json -> V2 fires
  K5  unmapped token added to F0 allowed list -> V3 fires
  K6  alias in mention context + comment only -> V4/V5 do NOT fire (specificity)
  K7  determinism: two live evaluations byte-identical
  K8  pin-guard tamper -> drift reported
  K9  mirror divergence -> V8 fires

Exit codes: 0 PASS, 1 check failure, 2 control failure, 3 pin drift.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import datetime

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("FATAL: PyYAML required\n")
    sys.exit(3)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SANDBOX = os.path.join(HERE, "control_sandbox")

CANON_SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
MIRROR_SCHEMAS = [
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}
CROSSWALK_REL = "artifacts/worker-080/rec37_vocab_crosswalk/crosswalk.json"
SANDBOX_FILES = CANON_SCHEMAS + MIRROR_SCHEMAS + [
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/rule_spec.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    CROSSWALK_REL,
]
MENTION_KEYS = {
    "provenance", "history", "historical", "notes", "note", "change_log",
    "revisions", "formerly", "alias", "aliases", "vocab_note",
    "f0_binding_note", "citation_note", "scope_note", "l1_ledger_refs",
}
MENTION_SUBSTRINGS = ("provenance", "histor", "note", "former", "alias",
                      "revision", "change", "comment")
ASSERTED_TOKEN_KEY_PATH = ("conclusion", "conclusion_type")


def is_conclusion_type_key(key):
    return str(key) == "conclusion_type" or str(key).endswith("_conclusion_type")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def walk_scalars(node, path=()):
    if isinstance(node, dict):
        for key, val in node.items():
            for item in walk_scalars(val, path + (str(key),)):
                yield item
    elif isinstance(node, list):
        for idx, val in enumerate(node):
            for item in walk_scalars(val, path + (str(idx),)):
                yield item
    else:
        yield path, node


def is_mention_path(path):
    """A path is a mention context if any component looks like provenance/history/
    alias/comment bookkeeping rather than an asserted content slot."""
    for comp in path[:-1]:
        c = str(comp).lower()
        if c in MENTION_KEYS or any(sub in c for sub in MENTION_SUBSTRINGS):
            return True
    return False


def ok(fid, condition, detail, severity="hard"):
    return {"id": fid, "ok": bool(condition), "severity": severity, "detail": detail}


def check_pins(base, pins):
    drift = []
    measured = {}
    for rel, want in sorted(pins.items()):
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            drift.append({"path": rel, "declared": want, "measured": None, "reason": "missing"})
            continue
        got = sha256_file(p)
        measured[rel] = got
        if got != want:
            drift.append({"path": rel, "declared": want, "measured": got, "reason": "hash_mismatch"})
    return measured, drift


def run_canonical_gate(base):
    """Run the binding structural gate on the three canonical schemas (read-only)."""
    tool = os.path.join(base, "artifacts/formulation/tools/check_class_schema.py")
    results, bad = {}, []
    for rel in CANON_SCHEMAS:
        proc = subprocess.run([sys.executable, tool, "--json", os.path.join(base, rel)],
                              capture_output=True, text=True)
        try:
            doc = json.loads(proc.stdout)
            verdict = doc.get("verdict")
        except Exception:
            doc, verdict = None, None
        results[rel] = {"exit_code": proc.returncode, "verdict": verdict}
        if proc.returncode != 0 or verdict != "pass":
            bad.append({"path": rel, "exit_code": proc.returncode, "verdict": verdict,
                        "stderr": proc.stderr[-300:]})
    return results, bad


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------
def evaluate(base, enforce_pins=False):
    """Run all rules against `base`.  Returns dict(findings, measured_pins, drift)."""
    findings = []
    measured, drift = check_pins(base, PINS)
    cw = load_json(os.path.join(base, CROSSWALK_REL))
    aliases_doc = load_json(os.path.join(base, "artifacts/formulation/VOCAB_ALIASES.json"))
    rule_spec = load_json(os.path.join(base, "artifacts/formulation/rule_spec.json"))
    f0 = load_yaml(os.path.join(base, "research_map/formulation_taxonomy.yaml"))

    # ---------------- V1 internal schema ----------------
    req_top = ["artifact", "schema_version", "task_id", "adjudication_ref", "policy",
               "tokens", "pins", "f0_alias_entries", "hard_failure_dispositions"]
    missing_top = [k for k in req_top if k not in cw]
    req_tok = ["canonical", "class_ids", "true_aliases", "f0_allowed_entries", "live_schemas"]
    tok_problems = []
    for t in cw.get("tokens", []):
        for k in req_tok:
            if k not in t:
                tok_problems.append("token %r missing %s" % (t.get("canonical"), k))
    canonicals = [t["canonical"] for t in cw.get("tokens", [])]
    dup_canon = sorted({c for c in canonicals if canonicals.count(c) > 1})
    findings.append(ok(
        "V1_crosswalk_schema",
        not missing_top and not tok_problems and not dup_canon and len(canonicals) >= 3,
        "missing_top=%s token_problems=%s dup_canonical=%s n_tokens=%d"
        % (missing_top, tok_problems, dup_canon, len(canonicals)),
    ))

    # ---------------- V2 alias partition (recomputed from live bytes) ----------------
    live_aliases = aliases_doc.get("conclusion_type", {})
    recomputed = {}
    for tok, raw in live_aliases.items():
        recomputed[tok] = [a for a in raw if a != tok]
    cross_rec = {t["canonical"]: sorted(t["true_aliases"]) for t in cw.get("tokens", [])}
    live_rec = {k: sorted(v) for k, v in recomputed.items()}
    mismatch = {k: {"crosswalk": cross_rec.get(k), "live": live_rec.get(k)}
                for k in sorted(set(cross_rec) | set(live_rec))
                if cross_rec.get(k) != live_rec.get(k)}
    all_true = []
    for v in recomputed.values():
        all_true.extend(v)
    collisions = sorted({a for a in all_true if all_true.count(a) > 1})
    canon_hits = sorted(set(all_true) & set(canonicals))
    rejected = set(cw.get("rejected_ambiguous_tokens", {}))
    rejected_hits = sorted(set(all_true) & rejected)
    findings.append(ok(
        "V2_alias_partition",
        not mismatch and not collisions and not canon_hits and not rejected_hits,
        "live_vs_crosswalk_mismatch=%s alias_collisions=%s alias_equals_canonical=%s "
        "alias_in_rejected=%s" % (mismatch, collisions, canon_hits, rejected_hits),
    ))

    # ---------------- V3 F0 coverage ----------------
    f0_allowed = (((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed")) or []
    owner = {}
    for t in cw.get("tokens", []):
        owner[t["canonical"]] = t["canonical"]
        for a in t["true_aliases"]:
            owner.setdefault(a, t["canonical"])
    unmapped = [e for e in f0_allowed if e not in owner]
    multi = sorted({e for e in f0_allowed if f0_allowed.count(e) > 1})
    rec_status = {}
    for t in cw.get("tokens", []):
        for e in t.get("f0_allowed_entries", []):
            rec_status[e] = "canonical" if e == t["canonical"] else "alias"
    status_mismatch = {e: {"recorded": rec_status.get(e),
                           "recomputed": ("canonical" if e in canonicals else "alias")}
                       for e in f0_allowed if rec_status.get(e) != ("canonical" if e in canonicals else "alias")}
    canon_covered = sorted(set(canonicals) - set(owner[e] for e in f0_allowed if e in owner))
    findings.append(ok(
        "V3_f0_coverage",
        not unmapped and not multi and not status_mismatch and not canon_covered,
        "f0_allowed=%s unmapped=%s duplicate_entries=%s status_mismatch=%s canonical_without_f0_entry=%s"
        % (f0_allowed, unmapped, multi, status_mismatch, canon_covered),
    ))

    # ---------------- V4/V5/V6 per schema ----------------
    v4_bad, v5_bad, v6_bad, anchors_bad = [], [], [], []
    r11_map = (rule_spec.get("vocabularies") or {}).get("class_conclusion_type", {})
    alias_to_canon = {}
    for t in cw.get("tokens", []):
        for a in t["true_aliases"]:
            alias_to_canon[a] = t["canonical"]
    anchor_map = {}
    for t in cw.get("tokens", []):
        for entry in t.get("live_schemas", []):
            anchor_map[entry["path"]] = (entry["line"], t["canonical"])

    for rel in CANON_SCHEMAS:
        doc = load_yaml(os.path.join(base, rel))
        lines = read_text(os.path.join(base, rel)).split("\n")
        cls = doc.get("class_id")
        tok = ((doc.get("conclusion") or {}).get("conclusion_type"))
        want = r11_map.get(cls)
        if tok not in canonicals:
            v4_bad.append({"path": rel, "class_id": cls, "asserted": tok,
                           "canonical_set": canonicals})
        if tok != want:
            v6_bad.append({"path": rel, "class_id": cls, "asserted": tok, "r11_expected": want})
        # V5: every OTHER conclusion_type-typed key must assert a canonical token.
        # Scoped to keys named *conclusion_type; family labels (e.g. "WCC") and
        # identifiers that merely contain a token substring are not assertions.
        hits = []
        for path, val in walk_scalars(doc):
            if not isinstance(val, str):
                continue
            if not path or not is_conclusion_type_key(path[-1]):
                continue
            if tuple(path) == ASSERTED_TOKEN_KEY_PATH:
                continue  # V4 owns the canonical conclusion_type slot
            if is_mention_path(path):
                continue  # provenance/history/alias bookkeeping is a mention
            if val not in canonicals:
                hits.append({"path": ".".join(path), "value": val[:120],
                             "kind": "alias" if val in alias_to_canon else "unknown"})
        if hits:
            v5_bad.append({"path": rel, "hits": hits})
        # V7 anchors
        if rel in anchor_map:
            line_no, expect_tok = anchor_map[rel]
            got_line = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            if expect_tok not in got_line:
                anchors_bad.append({"path": rel, "line": line_no,
                                    "expected_token": expect_tok, "line_text": got_line.strip()[:120]})

    findings.append(ok("V4_asserted_canonical", not v4_bad,
                       "non-canonical asserted tokens: %s" % v4_bad))
    findings.append(ok("V5_no_alias_in_asserted_position", not v5_bad,
                       "true-alias tokens in asserted scalar positions: %s" % v5_bad))
    findings.append(ok("V6_r11_binding", not v6_bad,
                       "R11 mismatches vs rule_spec.class_conclusion_type: %s" % v6_bad))

    # ---------------- V8 mirror identity ----------------
    mirror_bad = []
    for c, m in zip(CANON_SCHEMAS, MIRROR_SCHEMAS):
        hc = sha256_file(os.path.join(base, c))
        hm = sha256_file(os.path.join(base, m))
        if hc != hm:
            mirror_bad.append({"canonical": c, "mirror": m, "canonical_sha": hc, "mirror_sha": hm})
    findings.append(ok("V8_mirror_identity", not mirror_bad, "mirror divergences: %s" % mirror_bad))

    # ---------------- live-only binding rules ----------------
    if enforce_pins:
        findings.append(ok("V7_line_anchors", not anchors_bad,
                           "anchor mismatches: %s" % anchors_bad))
        rec_allowed = (cw.get("f0_alias_entries") or {}).get("allowed_list_measured")
        findings.append(ok("V9_f0_no_write", rec_allowed == f0_allowed,
                           "crosswalk_recorded=%s measured=%s" % (rec_allowed, f0_allowed)))
        frozen = load_json(os.path.join(base, "artifacts/formulation/FROZEN.json")).get("files", {})
        fb = []
        for rel, want in sorted(PINS.items()):
            if rel == "artifacts/formulation/FROZEN.json":
                continue
            got = frozen.get(rel, {}).get("sha256")
            if got != want:
                fb.append({"path": rel, "frozen": got, "pin": want})
        findings.append(ok("V10_frozen_binding", not fb, "FROZEN undeclared/mismatched pins: %s" % fb))
        findings.append(ok("V11_pin_guard", not drift, "pin drift: %s" % drift))
        gate_results, gate_bad = run_canonical_gate(base)
        findings.append(ok("V12_canonical_gate", not gate_bad,
                           "canonical gate non-pass/skipped: %s ; per-schema=%s" % (gate_bad, gate_results)))

    verdict = "PASS" if all(f["ok"] for f in findings) else "FAIL"
    out = {"verdict": verdict, "findings": findings, "measured_pins": measured,
           "pin_drift": drift, "enforce_pins": enforce_pins}
    if enforce_pins:
        out["canonical_gate"] = gate_results
    return out


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def _p(base, rel):
    return os.path.join(base, rel)


def build_sandbox(dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    for rel in SANDBOX_FILES:
        src = os.path.join(ROOT, rel)
        dst = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def mutate_text(rel, old, new):
    def _f(base):
        path = _p(base, rel)
        txt = read_text(path)
        assert old in txt, "mutation anchor missing in %s" % rel
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(txt.replace(old, new, 1))
    return _f


def mutate_yaml_key(rel, key_path, new_value):
    def _f(base):
        path = _p(base, rel)
        doc = load_yaml(path)
        node = doc
        for k in key_path[:-1]:
            node = node[k]
        node[key_path[-1]] = new_value
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
    return _f


def mutate_json(rel, fn):
    def _f(base):
        path = _p(base, rel)
        doc = load_json(path)
        fn(doc)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=False)
            fh.write("\n")
    return _f


def mutate_yaml(rel, fn):
    def _f(base):
        _mutate_yaml(base, rel, fn)
    return _f


def mutate_schema_key(schema_rel, key_path, new_value):
    """Apply the same edit to the canonical schema AND its declared mirror, so the
    V8 mirror-identity invariance is not disturbed by the control itself."""
    def _f(base):
        for rel in ("schemas/" + schema_rel, "artifacts/formulation/schemas/" + schema_rel):
            path = _p(base, rel)
            doc = load_yaml(path)
            node = doc
            for k in key_path[:-1]:
                node = node[k]
            node[key_path[-1]] = new_value
            with open(path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
    return _f


def append_schema_pair(schema_rel, text):
    def _f(base):
        for rel in ("schemas/" + schema_rel, "artifacts/formulation/schemas/" + schema_rel):
            with open(_p(base, rel), "a", encoding="utf-8") as fh:
                fh.write(text)
    return _f


def run_control(name, mutate, expect_fail_ids, liveness=None):
    dest = os.path.join(SANDBOX, name)
    build_sandbox(dest)
    if mutate is not None:
        mutate(dest)
    live_ok, live_detail = (True, "n/a")
    if liveness is not None:
        live_ok, live_detail = liveness(dest)
    res = evaluate(dest, enforce_pins=False)
    fails = sorted(f["id"] for f in res["findings"] if not f["ok"])
    passed = (fails == sorted(expect_fail_ids)) and live_ok
    return {"id": name, "ok": passed, "expected_failures": sorted(expect_fail_ids),
            "observed_failures": fails, "mutation_live": live_ok,
            "liveness_detail": live_detail, "sandbox": os.path.relpath(dest, ROOT)}


def control_pin_guard():
    tampered = dict(PINS)
    target = "schemas/af_scc_c2_vacuum.yaml"
    tampered[target] = "0" * 64
    _, drift = check_pins(ROOT, tampered)
    okc = len(drift) == 1 and drift[0]["path"] == target
    return {"id": "K8_pin_guard_tamper", "ok": okc,
            "expected_failures": ["V11_pin_guard"], "observed_failures": ["V11_pin_guard"] if drift else [],
            "mutation_live": okc, "liveness_detail": "tampered %s -> drift=%s" % (target, drift),
            "sandbox": "in-memory"}


def control_determinism():
    a = evaluate(ROOT, enforce_pins=True)
    b = evaluate(ROOT, enforce_pins=True)
    sa = json.dumps({"v": a["verdict"], "f": a["findings"], "p": a["measured_pins"]}, sort_keys=True)
    sb = json.dumps({"v": b["verdict"], "f": b["findings"], "p": b["measured_pins"]}, sort_keys=True)
    return {"id": "K7_determinism", "ok": sa == sb, "expected_failures": [],
            "observed_failures": [], "mutation_live": sa == sb,
            "liveness_detail": "two live evaluations byte-identical" if sa == sb else "DIVERGED",
            "sandbox": "live"}


def run_controls():
    controls = []
    # K0 baseline
    controls.append(run_control("K0_baseline", None, []))
    # K1 alias into conclusion_type
    controls.append(run_control(
        "K1_alias_in_conclusion_type",
        mutate_schema_key("af_scc_c2_vacuum.yaml", ["conclusion", "conclusion_type"],
                          "strong_cosmic_censorship_C2"),
        ["V4_asserted_canonical", "V6_r11_binding"]))
    # K1b alias in another conclusion_type-typed key
    controls.append(run_control(
        "K1b_alias_in_typed_key",
        append_schema_pair("af_scc_c2_vacuum.yaml",
                           "\nmisc_conclusion_type: strong_cosmic_censorship_C2\n"),
        ["V5_no_alias_in_asserted_position"],
        liveness=lambda b: ("strong_cosmic_censorship_C2" in read_text(_p(b, "schemas/af_scc_c2_vacuum.yaml")),
                            "mutated append present")))
    # K2 unknown token
    controls.append(run_control(
        "K2_unknown_token",
        mutate_schema_key("af_scc_c2_vacuum.yaml", ["conclusion", "conclusion_type"],
                          "scc_c3_future_inextendibility"),
        ["V4_asserted_canonical", "V6_r11_binding"]))
    # K3 cross-class token in F1
    controls.append(run_control(
        "K3_cross_class_token",
        mutate_schema_key("af_wcc_vacuum.yaml", ["conclusion", "conclusion_type"],
                          "scc_c0_future_inextendibility"),
        ["V6_r11_binding"]))
    # K4 alias collision in VOCAB_ALIASES
    def collide(doc):
        doc["conclusion_type"]["scc_c0_future_inextendibility"].append("strong_cosmic_censorship_C2")
    controls.append(run_control(
        "K4_alias_collision",
        mutate_json("artifacts/formulation/VOCAB_ALIASES.json", collide),
        ["V2_alias_partition"]))
    # K5 unmapped F0 entry
    def add_f0(doc):
        doc["field_vocabulary"]["conclusion_type"]["allowed"].append("scc_c3_future_inextendibility")
    controls.append(run_control(
        "K5_f0_unmapped_entry",
        mutate_yaml("research_map/formulation_taxonomy.yaml", add_f0),
        ["V3_f0_coverage"]))
    # K6 mention-only (specificity)
    mention_text = ('\n# historical alias: strong_cosmic_censorship_C2\n'
                    'provenance_note:\n'
                    '  formerly_conclusion_type: strong_cosmic_censorship_C2\n')
    mention_only = append_schema_pair("af_scc_c2_vacuum.yaml", mention_text)
    controls.append(run_control(
        "K6_mention_context_only", mention_only, [],
        liveness=lambda b: ("strong_cosmic_censorship_C2" in read_text(_p(b, "schemas/af_scc_c2_vacuum.yaml")),
                            "mention-only mutation present")))
    # K7 determinism
    controls.append(control_determinism())
    # K8 pin guard
    controls.append(control_pin_guard())
    # K9 mirror divergence
    def diverge_mirror(base):
        path = _p(base, "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n# mirror-only divergent line\n")
    controls.append(run_control(
        "K9_mirror_divergence", diverge_mirror, ["V8_mirror_identity"],
        liveness=lambda b: (sha256_file(_p(b, "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")) !=
                            sha256_file(_p(b, "schemas/af_scc_c2_vacuum.yaml")),
                            "mirror hash differs from canonical")))
    return controls


def _mutate_yaml(base, rel, fn):
    path = _p(base, rel)
    doc = load_yaml(path)
    fn(doc)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    os.makedirs(SANDBOX, exist_ok=True)
    controls = run_controls()
    # Live evaluation runs AFTER every sandbox control, so the recorded pins also
    # witness that no canonical path moved during this run.
    live = evaluate(ROOT, enforce_pins=True)
    controls_ok = all(c["ok"] for c in controls)
    measured = live["measured_pins"]
    if live["pin_drift"]:
        exit_code = 3
    elif not controls_ok:
        exit_code = 2
    elif live["verdict"] != "PASS":
        exit_code = 1
    else:
        exit_code = 0
    finished = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    report = {
        "artifact": "vocab_crosswalk_audit_report",
        "schema_version": "w080-rec37-v1",
        "task_id": "W080-REC37-VOCAB-CROSSWALK-01",
        "actor": "worker-080",
        "gate": "G-FORM",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "started_at": started,
        "finished_at": finished,
        "verdict": live["verdict"],
        "exit_code": exit_code,
        "n_findings": len(live["findings"]),
        "n_findings_failed": sum(1 for f in live["findings"] if not f["ok"]),
        "findings": live["findings"],
        "controls": controls,
        "controls_all_pass": controls_ok,
        "measured_pins": measured,
        "pin_drift": live["pin_drift"],
        "canonical_gate": live.get("canonical_gate"),
        "crosswalk": CROSSWALK_REL,
        "hard_failure_dispositions": load_json(os.path.join(ROOT, CROSSWALK_REL)).get("hard_failure_dispositions"),
        "scope": ("assertion-correct consistency check of conclusion_type tokens per REC-37; "
                  "no gate verdict, no node status, no canonical write, no mathematics claim"),
        "falsifier": ("Re-run this instrument at the pinned hashes. Falsified if: any measured pin differs "
                      "(drift voids the run); a canonical schema asserts an alias or unknown token; an alias "
                      "occurs in an asserted scalar position; a F0 allowed entry maps to no or to more than one "
                      "canonical token; the VOCAB_ALIASES partition collides; R11 disagrees with the crosswalk; "
                      "a mirror diverges; a control returns its unmutated verdict; or the mention-only and "
                      "asserted-scalar controls produce identical outcomes (instrument blind to assertion vs mention)."),
        "authority_note": ("Worker evidence only. Cannot set a gate verdict, node status or validation_status. "
                           "Canonical write is the owner's (astra-lead-formulation). Read-only on every canonical path."),
    }
    out = os.path.join(HERE, "report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("verdict=%s exit=%d findings_failed=%d controls=%d/%d report=%s"
          % (live["verdict"], exit_code, report["n_findings_failed"],
             sum(1 for c in controls if c["ok"]), len(controls), out))
    for f in live["findings"]:
        if not f["ok"]:
            print("FAIL %s: %s" % (f["id"], f["detail"]))
    for c in controls:
        if not c["ok"]:
            print("CONTROL-FAIL %s expected=%s observed=%s live=%s"
                  % (c["id"], c["expected_failures"], c["observed_failures"], c["mutation_live"]))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
