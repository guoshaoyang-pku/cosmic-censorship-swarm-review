#!/usr/bin/env python3
"""W001-F2B-INDEX-DEFERRAL-ADJUDICATION-01  (worker-001, class AF-SCC-C0-VAC-GEN, node F2b)

Bounded, read-only adjudication of the F0-vs-F2b index-domain divergence
(finding W077-HF-01 / W015-HF-01): the declared F0 taxonomy's C0 conclusion
quantifies over "admissible (s,delta)" while the F2b class schema quantifies
"forall r in D0" with D0 = smooth | (sobolev,s,delta).

Question decided: is this a SEMANTIC contradiction between two frozen
statements, or a DOCUMENTATION gap licensed by F0's own deferral clauses and
by the frozen class-contract supplement?  The distinction decides whether
closing it costs zero canonical hash moves (controller adjudication record) or
a freeze cascade (F0 edit -> 3 schema re-binds -> all bound verdicts voided).

The decision rule is PRE-REGISTERED in DECISION_RULE below and is evaluated
only after all inputs are hash-pinned.  Any pin drift exits 3 without a
verdict; any failed mutation control exits 4.  Canonical tree is never written.

Exit codes: 0 verdict emitted, 2 usage/parse failure, 3 pin drift, 4 control failure.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

DECISION_RULE = (
    "LICENSED_DEFERRAL iff ALL of: "
    "(L1) F0 scope_statement says provisional field values are owned by the downstream "
    "schema nodes and names F2 for the two AF-SCC classes; "
    "(L2) F0 C0 hypothesis H3 exists with owned_by=F2, unresolved=true, and names the "
    "topology and data spaces; "
    "(L3) F0 C0 provenance.schema_owner names F2b / schemas/af_scc_c0_vacuum.yaml; "
    "(L4) the frozen supplement's C0 data_class_freeze contains 'smooth-with-decay', the "
    "Sobolev variant (s > 5/2, delta in (1/2,1)), and 'identical across F1/F2a/F2b'; "
    "(L5) F2b D0 is a tagged union containing the smooth branch and the (sobolev,s,delta) "
    "branch, and both quantifiers.formal and conclusion.statement_formal bind 'forall r in D0'; "
    "(L6) F2b f0_binding.declared_f0_sha256 equals the measured F0 taxonomy hash; "
    "(L7) no clause of the F0 C0 contract freezes the index domain as final/authoritative. "
    "SEMANTIC_DIVERGENCE if any of L1-L6 fails, or if L7 finds a freezing clause. "
    "UNDECIDABLE if the inputs needed to evaluate a clause are absent."
)

PIN_FILES = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "reviews/F2b-f0-binding-077.json",
    "reviews/F2b-f0-binding-w015.json",
    "reviews/F2b-rev12-069.json",
]

FREEZE_TOKENS = [
    "is final", "are final", "authoritative", "no deferral", "must be used as stated",
    "ranges over exactly", "operates over exactly", "index domain is frozen",
    "supersedes the class schemas", "not delegable",
]

CASCADING_SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]


# --------------------------------------------------------------------------- io
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys."""


def _strict_mapping(loader, node, deep=False):
    seen = []
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise ValueError("duplicate YAML key %r at line %d" % (key, k.start_mark.line + 1))
        seen.append(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def load_yaml(path: Path):
    return yaml.load(path.read_text(), Loader=StrictLoader)


def get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def dig_text(obj) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(dig_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(dig_text(v) for v in obj)
    return ""


# ------------------------------------------------------------------- measurements
def measure_pins(pin_paths):
    return {p: sha256_file(ROOT / p) for p in pin_paths if (ROOT / p).exists()}


def measure_tree_hashes():
    """hash of every canonical artifact named in this adjudication (start/end drift check)."""
    return {p: sha256_file(ROOT / p) for p in PIN_FILES if (ROOT / p).exists()}


def eval_checks(tax, sup, f2b, frozen, checker_text, pins):
    c0 = get(tax, "classes", "AF-SCC-C0-VAC-GEN", default={}) or {}
    c2 = get(tax, "classes", "AF-SCC-C2-VAC-GEN", default={}) or {}
    scope = str(get(tax, "scope_statement", default=""))
    h3s = [h for h in (c0.get("hypotheses") or []) if isinstance(h, dict) and h.get("id") == "H3"]
    h3 = h3s[0] if h3s else {}
    concl = get(c0, "conclusion", default={}) or {}
    ctext = str(concl.get("text", ""))
    owner = str(get(c0, "provenance", "schema_owner", default=""))
    sup_c0 = get(sup, "class_contracts", "AF-SCC-C0-VAC-GEN", default={}) or {}
    dcf = str(sup_c0.get("data_class_freeze", ""))
    d0 = str(get(f2b, "quantifiers", "domains", "D0", "definition", default=""))
    qformal = str(get(f2b, "quantifiers", "formal", default=""))
    sformal = str(get(f2b, "conclusion", "statement_formal", default=""))
    reg_default = str(get(f2b, "data_class", "regularity_class", "default", default=""))
    reg_sob = get(f2b, "data_class", "regularity_class", "sobolev_variant", default={}) or {}
    fb = get(f2b, "f0_binding", default={}) or {}
    f0_pin = pins.get("research_map/formulation_taxonomy.yaml")
    freeze_hits = [t for t in FREEZE_TOKENS if t in ctext.lower() or t in dig_text(c0.get("hypotheses")).lower()
                   or t in dig_text(c0.get("exclusions")).lower()]
    logical = get(frozen, "logical_artifacts", default={}) or {}
    fro_files = get(frozen, "files", default={}) or {}
    fro_tax = get(fro_files, "research_map/formulation_taxonomy.yaml", "sha256", default=None)
    fro_sup = get(fro_files, "artifacts/formulation/formulation_taxonomy.yaml", "sha256", default=None)
    logical_tax = get(logical, "F0-declared-taxonomy", "sha256", default=None)
    logical_sup = get(logical, "F0-class-contract-supplement", "sha256", default=None)

    checks = []

    def add(cid, desc, ok, detail, fatal=True):
        checks.append({"id": cid, "description": desc, "result": "PASS" if ok else "FAIL",
                       "fatal_for_licensed_deferral": fatal, "detail": detail})

    add("L1", "F0 scope_statement delegates provisional fields to downstream schema nodes and names F2 for the AF-SCC classes",
        ("provisional" in scope.lower() and "owned by the downstream schema nodes" in scope
         and "F2 for the two AF-SCC classes" in scope),
        scope.replace("\n", " ")[:400])
    add("L2", "F0 C0 H3 exists, is unresolved, is owned by F2, and names topology and data spaces",
        bool(h3) and h3.get("owned_by") == "F2" and h3.get("unresolved") is True
        and "topology" in str(h3.get("text", "")) and "data spaces" in str(h3.get("text", "")),
        {"h3_text": h3.get("text"), "owned_by": h3.get("owned_by"), "unresolved": h3.get("unresolved")})
    add("L3", "F0 C0 provenance.schema_owner names F2b and the canonical C0 schema path",
        "F2b" in owner and "schemas/af_scc_c0_vacuum.yaml" in owner, owner)
    add("L4", "frozen supplement C0 data_class_freeze carries smooth-with-decay + Sobolev variant + identical across F1/F2a/F2b",
        ("smooth-with-decay" in dcf and "s > 5/2" in dcf and "delta in (1/2,1)" in dcf
         and "identical across F1/F2a/F2b" in dcf), dcf)
    add("L5", "F2b D0 is a tagged union with smooth and (sobolev,s,delta) branches and both formal statements bind 'forall r in D0'",
        ("tagged disjoint union" in d0 and "r = smooth" in d0 and "(sobolev,s,delta)" in d0
         and "forall r in D0" in qformal and "forall r in D0" in sformal), d0[:300])
    add("L6", "F2b f0_binding.declared_f0_sha256 equals the measured F0 taxonomy hash (hash-current binding)",
        fb.get("declared_f0_sha256") == f0_pin,
        {"declared": fb.get("declared_f0_sha256"), "measured": f0_pin})
    add("L7", "no clause of the F0 C0 contract freezes the index domain as final/authoritative",
        not freeze_hits, {"freeze_tokens_found": freeze_hits})
    # recorded, non-fatal observations
    add("O1", "F0 C0 conclusion text quantifies over (s,delta) and never names the smooth branch",
        ("(s,delta)" in ctext and "smooth" not in ctext), re.sub(r"\s+", " ", ctext)[:300], fatal=False)
    add("O2", "F0 C0 conclusion text carries no explicit index-deferral clause (textual staleness)",
        "deferr" not in ctext.lower() and "owned_by" not in ctext, re.sub(r"\s+", " ", ctext)[:300], fatal=False)
    add("O3", "F2b f0_binding names the supplement but pins no supplement hash",
        "formulation_taxonomy.yaml" in str(fb.get("class_contract_supplement", ""))
        and "class_contract_supplement_sha256" not in fb,
        {"class_contract_supplement": fb.get("class_contract_supplement")}, fatal=False)
    add("O4", "live FROZEN manifest pins both F0 artifacts (files + logical_artifacts) and the consistency evidence",
        bool(fro_tax) and fro_tax == logical_tax and bool(fro_sup) and fro_sup == logical_sup,
        {"revision": get(frozen, "revision"), "files.taxonomy": fro_tax, "logical.taxonomy": logical_tax,
         "files.supplement": fro_sup, "logical.supplement": logical_sup}, fatal=False)
    add("O5", "canonical consistency checker compares only taxonomy vs supplement and never the class schemas / index domains",
        ("research_map/formulation_taxonomy.yaml" in checker_text
         and "artifacts/formulation/formulation_taxonomy.yaml" in checker_text
         and "af_scc_c0_vacuum.yaml" not in checker_text
         and "forall r in D0" not in checker_text),
        "checker references class schema path: %s" % ("af_scc_c0_vacuum.yaml" in checker_text), fatal=False)
    add("O6", "checker presence-checks data_class_freeze but publishes consistent=true with 0 contract divergences",
        ("data_class_freeze" in checker_text and "smooth-with-decay" in checker_text), None, fatal=False)
    add("O7", "C2 sibling shows the same divergence pattern (generality of the finding)",
        ("(s,delta)" in str(get(c2, "conclusion", "text", default=""))
         and "smooth" not in str(get(c2, "conclusion", "text", default=""))), None, fatal=False)
    # rev13 / rev29 context: the evidence-binding repair (W077-HF-02) landed during this task window.
    live_declared = fb.get("consistency_evidence_sha256")
    live_measured = pins.get("artifacts/formulation/evidence/taxonomy_consistency.json")
    add("O8", "W077-HF-02 (consistency-evidence hash) is CLOSED at the live revision: declared == measured",
        live_declared == live_measured,
        {"declared": live_declared, "measured": live_measured,
         "revision": get(f2b, "revision"), "frozen_revision": get(frozen, "revision")}, fatal=False)
    add("O9", "canonical and authoring class-schema copies are byte-identical (publication aligned)",
        pins.get("schemas/af_scc_c0_vacuum.yaml") ==
        pins.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"), None, fatal=False)
    add("O10", "W077-HF-03 (l1_ledger_refs citation_status=verified_by_L1 vs ledger vocabulary) is still open at the live revision",
        any(r.get("citation_status") == "verified_by_L1" for r in (f2b.get("l1_ledger_refs") or [])),
        [r.get("theorem_id") for r in (f2b.get("l1_ledger_refs") or [])
         if r.get("citation_status") == "verified_by_L1"], fatal=False)
    return checks


def decide(checks):
    by = {c["id"]: c for c in checks}
    fatal = [c for c in checks if c["fatal_for_licensed_deferral"]]
    for c in fatal:
        if c["result"] == "FAIL" and c["detail"] is None:
            return "UNDECIDABLE", "check %s could not be evaluated" % c["id"]
    if by["L7"]["result"] == "FAIL":
        return "SEMANTIC_DIVERGENCE", "a freezing clause is present: %s" % by["L7"]["detail"]
    if all(by[c]["result"] == "PASS" for c in ("L1", "L2", "L3", "L4", "L5", "L6")):
        return "LICENSED_DEFERRAL", "all deferral-license conditions hold; divergence is documentation staleness in the F0 conclusion text"
    failed = [c["id"] for c in fatal if c["result"] == "FAIL"]
    return "SEMANTIC_DIVERGENCE", "deferral-license conditions fail: %s" % failed


# ------------------------------------------------------------------- controls
def run_controls(pins):
    """Seeded mutations; every mutation must flip the decision away from LICENSED_DEFERRAL."""
    tax = load_yaml(ROOT / "research_map/formulation_taxonomy.yaml")
    sup = load_yaml(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")
    f2b = load_yaml(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    ctext = (ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    c0 = tax["classes"]["AF-SCC-C0-VAC-GEN"]
    h3 = [h for h in c0["hypotheses"] if h["id"] == "H3"][0]
    results = []

    def rec(cid, mutation, mutation_fn, expect_flip=True):
        import copy
        t2, s2, f2 = copy.deepcopy(tax), copy.deepcopy(sup), copy.deepcopy(f2b)
        c02 = t2["classes"]["AF-SCC-C0-VAC-GEN"]
        h32 = [h for h in c02["hypotheses"] if h["id"] == "H3"][0]
        mutation_fn(t2, s2, f2, c02, h32)
        v, _ = decide(eval_checks(t2, s2, f2, frozen, ctext, pins))
        flipped = (v != "LICENSED_DEFERRAL")
        results.append({"id": cid, "mutation": mutation, "expected": "decision leaves LICENSED_DEFERRAL",
                        "observed": v, "result": "PASS" if flipped == expect_flip else "FAIL"})

    rec("CT1", "remove C0 H3.owned_by", lambda t, s, f, c, h: h.pop("owned_by", None))
    rec("CT2", "set C0 H3.unresolved=false", lambda t, s, f, c, h: h.update({"unresolved": False}))
    rec("CT3", "replace supplement data_class_freeze with a Sobolev-only freeze",
        lambda t, s, f, c, h: s["class_contracts"]["AF-SCC-C0-VAC-GEN"].update(
            {"data_class_freeze": "H^4_{1/2+eps} only; not the smooth default"}))
    rec("CT4", "remove the smooth branch from F2b D0",
        lambda t, s, f, c, h: f["quantifiers"]["domains"]["D0"].update(
            {"definition": "sobolev indices only: r = (sobolev,s,delta) with s > 5/2"}))
    rec("CT5", "inject a freezing clause into the F0 C0 conclusion",
        lambda t, s, f, c, h: c["conclusion"].update(
            {"text": c["conclusion"]["text"] + " The (s,delta) index domain is final and authoritative."}))
    rec("CT6", "corrupt F2b declared_f0_sha256",
        lambda t, s, f, c, h: f["f0_binding"].update({"declared_f0_sha256": "0" * 64}))
    # CT7: pin-drift path must exit 3, exercised through a real subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "Pinned.json"
        expected = json.loads((HERE / "PINNED.json").read_text())["pins"]
        expected["schemas/af_scc_c0_vacuum.yaml"] = "0" * 64
        bad.write_text(json.dumps({"pins": expected}))
        out = Path(td) / "out.json"
        proc = __import__("subprocess").run(
            [sys.executable, str(Path(__file__)), "--expect", str(bad), "--out", str(out)],
            capture_output=True, text=True)
        results.append({"id": "CT7", "mutation": "tampered expected pin map",
                        "expected": "exit 3, no verdict written",
                        "observed": "exit %d, verdict_written=%s" % (proc.returncode, out.exists()),
                        "result": "PASS" if proc.returncode == 3 and not out.exists() else "FAIL"})
    return results


# ---------------------------------------------------------------- cascade cost
def scan_bindings(h, corpus_files):
    """Return review records that bind hash h, both substring and strict-JSON-field."""
    sub, strict = [], []
    for rel in corpus_files:
        p = ROOT / rel
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if h not in text:
            continue
        sub.append(rel)
        try:
            obj = json.loads(text)
        except Exception:
            continue
        hits = []

        def walk(o, key=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
            elif isinstance(o, str) and h in o:
                fieldy = any(t in key.lower() for t in
                             ("sha256", "hash", "pin", "target", "reviewed", "evidence", "artifact"))
                if fieldy or o.strip() == h:
                    hits.append({"key": key, "value": o[:120]})

        walk(obj)
        if hits:
            strict.append({"path": rel, "reviewer": obj.get("reviewer") if isinstance(obj, dict) else None,
                           "verdict": obj.get("verdict") if isinstance(obj, dict) else None,
                           "fields": hits[:4]})
    return {"substring_files": sorted(sub), "strict_binding_files": strict}


def cascade_measurement(pins):
    import glob
    old_f0 = pins["research_map/formulation_taxonomy.yaml"]
    sandbox = HERE / "sandbox"
    sandbox.mkdir(exist_ok=True)
    text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    anchor = "withdrawn as ambiguous."
    if text.count(anchor) != 1:
        return {"status": "INVALID", "reason": "anchor not unique"}
    clause = (" Index domain (representative deferral discharge): the admissible indices are the "
              "ones fixed by the class schema owner F2b: r = smooth (the smooth-with-decay default) "
              "or r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1).")
    patched = text.replace(anchor, anchor + clause)
    try:
        pobj = yaml.safe_load(patched)
        ok = "smooth" in pobj["classes"]["AF-SCC-C0-VAC-GEN"]["conclusion"]["text"]
    except Exception as e:  # noqa
        return {"status": "INVALID", "reason": "patched text does not parse: %s" % e}
    if not ok:
        return {"status": "INVALID", "reason": "patched conclusion does not carry the clause"}
    new_f0 = sha256_bytes(patched.encode())
    (sandbox / "patched_formulation_taxonomy.yaml").write_text(patched)

    reviews = sorted(str(Path(p).relative_to(ROOT)) for p in glob.glob(str(ROOT / "reviews/*.json")))
    corpus = reviews + [
        "research_map/research_map.json",
        "runtime/state/artifact_hashes.json",
        "artifacts/formulation/FROZEN.json",
        "artifacts/formulation/evidence/taxonomy_consistency.json",
    ]
    f0_bind = scan_bindings(old_f0, corpus)
    schema_bind = {}
    for s in CASCADING_SCHEMAS:
        sh = pins.get(s)
        if sh:
            schema_bind[s] = scan_bindings(sh, reviews)
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_entries = [k for k, v in (frozen.get("files") or {}).items()
                      if isinstance(v, dict) and v.get("sha256") == old_f0]
    logical_entries = [k for k, v in (frozen.get("logical_artifacts") or {}).items()
                       if isinstance(v, dict) and v.get("sha256") == old_f0]
    m = json.loads((ROOT / "research_map/research_map.json").read_text())
    map_review_hits = []
    for r in (m.get("reviews") or []):
        t = json.dumps(r)
        if old_f0 in t:
            map_review_hits.append({"reviewer": r.get("reviewer"), "verdict": r.get("verdict"),
                                    "target_id": str(r.get("target_id"))[:120]})
    declared_f0 = {}
    for s in CASCADING_SCHEMAS:
        d = load_yaml(ROOT / s)
        declared_f0[s] = get(d, "f0_binding", "declared_f0_sha256", default=None)
    return {
        "status": "MEASURED",
        "note": "representative minimal F0 edit, applied only to a sandbox copy; canonical tree untouched",
        "measured_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "corpus_review_file_count": len(reviews),
        "corpus_review_dir_snapshot_note": ("the reviews/ directory grows during the run; the at-risk "
                                            "counts are a snapshot at measured_at, not a frozen constant"),
        "old_f0_sha256": old_f0,
        "patched_sandbox_file": "artifacts/worker-001/f2b_index_deferral/sandbox/patched_formulation_taxonomy.yaml",
        "new_f0_sha256": new_f0,
        "f0_hash_moves": True,
        "frozen_files_entries_on_old_f0": frozen_entries,
        "frozen_logical_entries_on_old_f0": logical_entries,
        "schemas_declaring_old_f0_sha256": {k: v for k, v in declared_f0.items() if v == old_f0},
        "review_records_binding_old_f0": {
            "substring_count": len(f0_bind["substring_files"]),
            "strict_count": len(f0_bind["strict_binding_files"]),
            "strict_reviewers": sorted({x["reviewer"] for x in f0_bind["strict_binding_files"] if x.get("reviewer")}),
            "strict_files": f0_bind["strict_binding_files"],
        },
        "map_review_records_binding_old_f0": map_review_hits,
        "schema_review_voids_if_three_schemas_rebound": {
            s: {"strict_count": len(v["strict_binding_files"]),
                "strict_reviewers": sorted({x["reviewer"] for x in v["strict_binding_files"] if x.get("reviewer")})}
            for s, v in schema_bind.items()},
        "total_review_records_at_risk": (len(f0_bind["strict_binding_files"])
                                         + sum(len(v["strict_binding_files"]) for v in schema_bind.values())),
        "scan_definition": "reviews/*.json (substring + strict JSON field binding) plus map/state/FROZEN for substring",
        "canonical_writes": 0,
    }


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", default=str(HERE / "PINNED.json"))
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--measure-only", action="store_true")
    args = ap.parse_args()

    pin_doc = json.loads(Path(args.expect).read_text())
    expected = pin_doc["pins"]
    before = measure_tree_hashes()
    drift = {p: {"expected": expected.get(p), "measured": before.get(p)}
             for p in expected if expected.get(p) != before.get(p)}
    if drift:
        print("PIN DRIFT -> exit 3: " + json.dumps(drift))
        return 3
    if args.measure_only:
        print(json.dumps(before, indent=2))
        return 0

    tax = load_yaml(ROOT / "research_map/formulation_taxonomy.yaml")
    sup = load_yaml(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")
    f2b = load_yaml(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    checker_text = (ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    checks = eval_checks(tax, sup, f2b, frozen, checker_text, before)
    verdict, reason = decide(checks)
    controls = run_controls(before)
    ctl_fail = [c for c in controls if c["result"] != "PASS"]

    report = {
        "task_id": "W001-F2B-INDEX-DEFERRAL-ADJUDICATION-01",
        "actor": "worker-001",
        "role": "bounded execution worker",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "subject_findings": ["W077-HF-01", "W015-HF-01"],
        "question": ("Is the F0 conclusion ('for every admissible (s,delta)') vs F2b D0 "
                     "(tagged union incl. r=smooth) divergence a semantic contradiction of two "
                     "frozen statements, or a documentation gap licensed by F0's own deferral?"),
        "decision_rule_pre_registered": DECISION_RULE,
        "pins": {p: {"expected": expected.get(p), "measured": before.get(p),
                     "match": expected.get(p) == before.get(p)} for p in expected},
        "revision_context": {
            "f2b_revision": get(f2b, "revision"),
            "f2b_revised_at": get(f2b, "revised_at"),
            "frozen_revision": get(frozen, "revision"),
            "frozen_at": get(frozen, "frozen_at"),
            "note": ("measured at FROZEN rev29. The pass-05 evidence-binding repair "
                     "(W077-HF-02) landed at 00:53:20+08:00 while this task was being pinned; "
                     "the harness exit-3 drift guard rejected the pre-repair pins and the whole "
                     "run was re-anchored to rev29. The index-domain divergence this task "
                     "adjudicates is unaffected by that repair."),
        },
        "checks": checks,
        "verdict": verdict,
        "verdict_reason": reason,
        "controls": controls,
        "control_failures": [c["id"] for c in ctl_fail],
        "canonical_writes": 0,
    }

    after = measure_tree_hashes()
    report["inputs_unchanged_at_end"] = (after == before)
    if after != before:
        print("INPUTS MOVED DURING RUN -> exit 3")
        return 3
    if ctl_fail:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
        print("CONTROL FAILURE -> exit 4: " + json.dumps([c["id"] for c in ctl_fail]))
        return 4

    if verdict == "LICENSED_DEFERRAL":
        report["cascade"] = cascade_measurement(before)
        report["disposition"] = {
            "underlying_finding": "ACCEPTED as a real text-level divergence (O1 true, O2 true)",
            "gate_impact": ("NOT a semantic contradiction; licensed by L1-L7. The operative index domain "
                            "is F2b's D0 by F0's own ownership deferral and the frozen supplement's "
                            "data_class_freeze. Closing it needs no canonical edit: a controller "
                            "adjudication record can discharge it with zero hash moves and zero voided verdicts."),
            "caveats": [
                ("L4's 'identical across F1/F2a/F2b' phrase is an annotation-level identity claim: "
                 "W060-XCLASS-DATACLASS-01 measured 15/15 data-space-core keys equal on the licensed "
                 "F2a/F2b pair but two differing annotation paths; the deferral license needs only the "
                 "two regularity branches (smooth default + Sobolev variant), which both carry."),
                ("Scope is the index-domain divergence only. W077-HF-02 is CLOSED by the rev13 repair (O8); "
                 "W077-HF-03 citation_status is still open at rev13 (O10) and is not adjudicated here."),
            ],
            "recommended_actions": [
                "controller records an index-domain discharge referencing this report at the pinned hashes",
                "next F0 revision adopts the D0 wording (cost bounded by the cascade block) or adds a deferral sentence to each SCC conclusion",
                "next F2b/F2a/F1 revision adds class_contract_supplement_sha256 so the deferral license is hash-pinned in the schema itself (O3)",
                "checker gains an index-domain comparison between the taxonomy conclusions and the class-schema D0 (O5)",
            ],
            "scope_limit": ("This adjudication covers only the index-domain divergence. It does not clear the "
                            "remaining F2b finding l1_ledger_refs citation_status (W077-HF-03), which remains open."),
        }
        report["falsifiers"] = [
            "any pinned input hash moves (harness exits 3 without a verdict)",
            "a clause in the F0 C0 contract that freezes the index domain (L7 control CT5)",
            "the supplement at d7419b4e lacking the smooth-with-decay data_class_freeze (L4; CT3)",
            "F2b D0 shown not to contain the smooth branch (L5; CT4)",
            "a definition of 'admissible (s,delta)' in the pinned taxonomy that already includes the smooth branch",
            "FROZEN rev29 shown not to pin the supplement as a logical artifact (O4)",
        ]
    else:
        report["falsifiers"] = ["any pinned input hash moves", "a control mutation that does not flip the verdict"]

    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print("VERDICT %s :: %s" % (verdict, reason))
    print("controls: %d/%d PASS" % (len(controls) - len(ctl_fail), len(controls)))
    if verdict == "LICENSED_DEFERRAL":
        c = report["cascade"]
        print("cascade: 1 F0 edit -> %d schema rebinds, %d review records at risk"
              % (len(c["schemas_declaring_old_f0_sha256"]), c["total_review_records_at_risk"]))
    print("report: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
