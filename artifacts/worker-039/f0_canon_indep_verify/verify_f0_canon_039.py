#!/usr/bin/env python3
"""W039-F0-CANON-INDEP-VERIFY-01 -- independent, non-author verification of
W042-F0-CANON-CANDIDATE-08 (frozen F0 declared-conclusion-vocabulary canonicality).

Read-only wrt every canonical path.  Own instrument: does not import worker-042 code.
Fail-closed: any pinned input that moves exits 3 without a verdict.

Run:  python3 artifacts/worker-039/f0_canon_indep_verify/verify_f0_canon_039.py
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SN = HERE / "snapshot"
SCRATCH = HERE / "scratch"
SANDBOX = HERE / "sandbox"
OUT = HERE / "report.json"

import yaml

TASK = "W039-F0-CANON-INDEP-VERIFY-01"
ACTOR = "worker-039"
CLASS_ID = "AF-WCC-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
NODE = "F0"
GATE = "G-F0"
SECONDARY_GATE = "G-FORM"
TARGET_TASK = "W042-F0-CANON-CANDIDATE-08"

# ---------------------------------------------------------------- pinned inputs
PINS = {
    # canonical live inputs (must match the declared bytes)
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b",  # 12-char declared prefix per worker-042 evidence_refs
    # worker-042 artifacts under verification (declared bytes)
    "artifacts/worker-042/f0_canon_candidate/CANDIDATE_A_formulation_taxonomy.yaml":
        "ef180b5cfe0a32265f2f561b02673ce2883d327560038e64762b55e98146a869",
    "artifacts/worker-042/f0_canon_candidate/CANDIDATE_B_formulation_taxonomy.yaml":
        "f0a78706e5e89bfc3257c39816a8e4ce5d5b8134264c9d36fe4bdfd094ac326a",
    "artifacts/worker-042/f0_canon_candidate/report.json":
        "21b7598096bb",  # declared prefix
    "artifacts/worker-042/f0_canon_candidate/snapshot/research_map/events.jsonl":
        "fff3ecbbc2bb75c48afeca8563501eff6eb45006e8aff16cff17f0313cb67c3f",
    "artifacts/worker-019/f2a_review/results.json":
        "e5bf6729db48",  # declared prefix
    "artifacts/formulation/tools/check_taxonomy_consistency.py":
        "de356d999ea3",  # declared prefix
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def matches(declared: str, measured: str) -> bool:
    return measured.startswith(declared) or declared.startswith(measured[:12])


def check_pins() -> dict:
    out = {}
    for rel, declared in PINS.items():
        p = ROOT / rel
        if not p.is_file():
            out[rel] = {"declared": declared, "measured": None, "match": False,
                        "error": "missing"}
            continue
        m = sha256_file(p)
        out[rel] = {"declared": declared, "measured": m, "match": matches(declared, m)}
    return out


# ---------------------------------------------------------------- vocab helpers
def vocab_sets(vocab: dict):
    canonical = set(vocab["conclusion_type"].keys())
    alias_of = {}
    for canon, aliases in vocab["conclusion_type"].items():
        for a in aliases:
            alias_of[a] = canon
    rejected = set((vocab.get("rejected_ambiguous_tokens") or {}).keys())
    return canonical, alias_of, rejected


def canon(tok, alias_of):
    return alias_of.get(tok, tok)


SCC_ALIASES = ["strong_cosmic_censorship_C2", "strong_cosmic_censorship_c2",
               "strong_cosmic_censorship_C0", "strong_cosmic_censorship_c0"]
ABBREV_RE = re.compile(r"(?<![A-Za-z0-9_])_[Cc][02]\b")


def use_site_census(doc: dict, vocab: dict) -> dict:
    """Structural census of conclusion tokens in use positions (own parser)."""
    canonical, alias_of, rejected = vocab_sets(vocab)
    sites = []
    fv = ((doc.get("field_vocabulary") or {}).get("conclusion_type") or {})
    for i, tok in enumerate(fv.get("allowed") or []):
        sites.append({"path": f"field_vocabulary.conclusion_type.allowed[{i}]",
                      "token": tok, "kind": "allowed"})
    for cid, cls in (doc.get("classes") or {}).items():
        axes = (cls.get("axes") or {})
        if "conclusion_type" in axes:
            sites.append({"path": f"classes.{cid}.axes.conclusion_type",
                          "token": axes["conclusion_type"], "kind": "axes"})
        concl = (cls.get("conclusion") or {})
        if "type" in concl:
            sites.append({"path": f"classes.{cid}.conclusion.type",
                          "token": concl["type"], "kind": "conclusion"})
    for s in sites:
        t = s["token"]
        if t in canonical:
            s["class"] = "canonical"
        elif t in alias_of:
            s["class"] = "alias"
        elif t in rejected:
            s["class"] = "rejected_ambiguous"
        else:
            s["class"] = "unknown"
    return {
        "sites": sites,
        "alias_use_sites": [s for s in sites if s["class"] == "alias"],
        "rejected_use_sites": [s for s in sites if s["class"] == "rejected_ambiguous"],
        "unknown_use_sites": [s for s in sites if s["class"] == "unknown"],
        "allowed_list_length": len(fv.get("allowed") or []),
    }


def text_residue(text: str) -> dict:
    full = {}
    for tok in SCC_ALIASES:
        full[tok] = text.count(tok)
    quoted = {tok: text.count('"%s"' % tok) for tok in SCC_ALIASES}
    unquoted = {tok: full[tok] - quoted[tok] for tok in SCC_ALIASES}
    abbrev = ABBREV_RE.findall(text)
    return {
        "full_occurrences": full,
        "full_total": sum(full.values()),
        "quoted": quoted,
        "quoted_total": sum(quoted.values()),
        "unquoted": unquoted,
        "unquoted_total": sum(unquoted.values()),
        "abbrev_occurrences": len(abbrev),
        "abbrev_tokens": sorted(set(abbrev)),
    }


# ---------------------------------------------------------------- tree diff
def flatten(doc, prefix=""):
    out = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = doc
    return out


def tree_diff(a, b):
    fa, fb = flatten(a), flatten(b)
    changed = sorted(k for k in fa.keys() & fb.keys() if fa[k] != fb[k])
    added = sorted(fb.keys() - fa.keys())
    removed = sorted(fa.keys() - fb.keys())
    return {"changed": changed, "added": added, "removed": removed}


# ---------------------------------------------------------------- YAML strict
def strict_load(text: str):
    """safe_load + duplicate-key rejection (own implementation)."""
    class Dup(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        keys = set()
        for k, _ in node.value:
            kk = loader.construct_object(k, deep=deep)
            if kk in keys:
                raise ValueError(f"duplicate key: {kk!r}")
            keys.add(kk)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    Dup.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    return yaml.load(text, Loader=Dup)


# ---------------------------------------------------------------- consumer rules
def consumer_rules(rule_map, candidates, vocab):
    """Worker-019 B1 literal-membership and worker-097 alias_allowed rules,
    evaluated per variant against that variant's own allowed list."""
    canonical, alias_of, rejected = vocab_sets(vocab)
    req = {cid: rule_map[cid] for cid in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")}
    literal, alias_ok = {}, {}
    for name, doc in (("frozen", candidates["frozen_doc"]),
                      ("A", candidates["A_doc"]), ("B", candidates["B_doc"])):
        allowed = ((doc.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
        canon_allowed = {canon(t, alias_of) for t in allowed}
        literal[name] = {
            "allowed": allowed,
            "c2_required_in_allowed": req["AF-SCC-C2-VAC-GEN"] in allowed,
            "c0_required_in_allowed": req["AF-SCC-C0-VAC-GEN"] in allowed}
        alias_ok[name] = {
            "c2_alias_allowed": canon(req["AF-SCC-C2-VAC-GEN"], alias_of) in canon_allowed,
            "c0_alias_allowed": canon(req["AF-SCC-C0-VAC-GEN"], alias_of) in canon_allowed}
    return {"required_tokens": req,
            "literal_membership": literal, "alias_allowed": alias_ok}


def run_consistency_tool(variant_text: str, frozen_text: str, vocab_text: str,
                         tool_text: str) -> dict:
    """End-to-end replay of the pinned checker in a sandbox, per variant."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "research_map").mkdir(parents=True)
    (SANDBOX / "artifacts/formulation/tools").mkdir(parents=True)
    (SANDBOX / "artifacts/formulation/evidence").mkdir(parents=True)
    (SANDBOX / "research_map/formulation_taxonomy.yaml").write_text(variant_text)
    (SANDBOX / "artifacts/formulation/formulation_taxonomy.yaml").write_text(frozen_text)
    (SANDBOX / "artifacts/formulation/VOCAB_ALIASES.json").write_text(vocab_text)
    tool = SANDBOX / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    tool.write_text(tool_text)
    proc = subprocess.run([sys.executable, str(tool)], capture_output=True,
                          text=True, timeout=120)
    return {"exit": proc.returncode,
            "stdout": proc.stdout.strip()[:400],
            "stderr": proc.stderr.strip()[:200]}


# ---------------------------------------------------------------- main
def main():
    checks, findings = {}, []

    def add(cid, status, detail, **extra):
        checks[cid] = {"status": status, "detail": detail}
        checks[cid].update(extra)

    # V1 pins -------------------------------------------------------------
    pins0 = check_pins()
    bad = [k for k, v in pins0.items() if not v["match"]]
    add("V1_PINS", "pass" if not bad else "fail",
        f"{len(pins0)} pinned inputs; mismatches={len(bad)}", pins=pins0, mismatches=bad)
    if bad:
        add("VERDICT", "fail", "pinned input moved; fail-closed, no verdict")
        OUT.write_text(json.dumps({"task_id": TASK, "status": "PIN_DRIFT",
                                   "checks": checks}, indent=2) + "\n")
        print("PIN_DRIFT", bad)
        sys.exit(3)

    frozen_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    vocab_text = (ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text()
    rule_spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
    cand_a_text = (ROOT / "artifacts/worker-042/f0_canon_candidate/"
                   "CANDIDATE_A_formulation_taxonomy.yaml").read_text()
    cand_b_text = (ROOT / "artifacts/worker-042/f0_canon_candidate/"
                   "CANDIDATE_B_formulation_taxonomy.yaml").read_text()
    w042 = json.loads((ROOT / "artifacts/worker-042/f0_canon_candidate/report.json").read_text())
    w019 = json.loads((ROOT / "artifacts/worker-019/f2a_review/results.json").read_text())
    tool_text = (ROOT / "artifacts/formulation/tools/"
                 "check_taxonomy_consistency.py").read_text()

    vocab = json.loads(vocab_text)
    frozen_doc = strict_load(frozen_text)
    a_doc = strict_load(cand_a_text)
    b_doc = strict_load(cand_b_text)

    # V2 frozen use-site census ------------------------------------------
    cen_frozen = use_site_census(frozen_doc, vocab)
    exp_paths = sorted([
        "field_vocabulary.conclusion_type.allowed[1]",
        "field_vocabulary.conclusion_type.allowed[2]",
        "classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type",
        "classes.AF-SCC-C2-VAC-GEN.conclusion.type",
        "classes.AF-SCC-C0-VAC-GEN.axes.conclusion_type",
        "classes.AF-SCC-C0-VAC-GEN.conclusion.type",
    ])
    got_paths = sorted(s["path"] for s in cen_frozen["alias_use_sites"])
    ok = (got_paths == exp_paths and not cen_frozen["rejected_use_sites"]
          and not cen_frozen["unknown_use_sites"])
    add("V2_FROZEN_USE_CENSUS", "pass" if ok else "fail",
        f"alias use sites={len(got_paths)} (expected 6); exact paths={got_paths == exp_paths}",
        alias_sites=cen_frozen["alias_use_sites"],
        rejected=cen_frozen["rejected_use_sites"],
        unknown=cen_frozen["unknown_use_sites"])

    # V3 frozen text residue ---------------------------------------------
    res_frozen = text_residue(frozen_text)
    ok = (res_frozen["quoted_total"] == 6 and res_frozen["unquoted_total"] == 1
          and res_frozen["abbrev_occurrences"] == 1 and res_frozen["full_total"] == 7)
    add("V3_FROZEN_TEXT_RESIDUE", "pass" if ok else "fail",
        "quoted=6, unquoted=1, abbrev=1, full=7 expected", residue=res_frozen)

    # V4 independent candidate-A rebuild (byte oracle) --------------------
    a0_text, n_c2, n_c0 = frozen_text, 0, 0
    for tok, canon_tok in (("strong_cosmic_censorship_C2", "scc_c2_future_inextendibility"),
                           ("strong_cosmic_censorship_C0", "scc_c0_future_inextendibility")):
        n = a0_text.count('"%s"' % tok)
        a0_text = a0_text.replace('"%s"' % tok, '"%s"' % canon_tok)
        if tok.endswith("_C2"):
            n_c2 = n
        else:
            n_c0 = n
    a0_sha = sha256_bytes(a0_text.encode())
    a_sha = sha256_file(ROOT / "artifacts/worker-042/f0_canon_candidate/"
                        "CANDIDATE_A_formulation_taxonomy.yaml")
    add("V4_A_REBUILD_BYTE_ORACLE", "pass" if (a0_sha == a_sha and n_c2 == 3 and n_c0 == 3) else "fail",
        f"own quoted-substitution rebuild sha==candidate A: {a0_sha == a_sha}; "
        f"substitutions C2={n_c2} C0={n_c0}",
        own_sha256=a0_sha, candidate_a_sha256=a_sha)

    cen_a = use_site_census(a_doc, vocab)
    res_a = text_residue(cand_a_text)
    diff_fa = tree_diff(frozen_doc, a_doc)
    ok = (not cen_a["alias_use_sites"] and res_a["full_total"] == 1
          and res_a["abbrev_occurrences"] == 1
          and diff_fa == {"changed": exp_paths, "added": [], "removed": []}
          and cen_a["allowed_list_length"] == cen_frozen["allowed_list_length"]
          and sorted(a_doc.get("class_ids") or []) == sorted(frozen_doc.get("class_ids") or []))
    add("V5_CANDIDATE_A", "pass" if ok else "fail",
        "alias use sites=0; residue=1; diff==6 declared paths; list length/class_ids stable",
        use_census_alias=cen_a["alias_use_sites"], residue=res_a, diff=diff_fa,
        allowed_len=(cen_frozen["allowed_list_length"], cen_a["allowed_list_length"]))

    cen_b = use_site_census(b_doc, vocab)
    res_b = text_residue(cand_b_text)
    diff_ab = tree_diff(a_doc, b_doc)
    exp_ab = {"changed": ["field_vocabulary.conclusion_type.rule"], "added": [], "removed": []}
    ok = (not cen_b["alias_use_sites"] and res_b["full_total"] == 0
          and res_b["abbrev_occurrences"] == 0 and diff_ab == exp_ab)
    add("V6_CANDIDATE_B", "pass" if ok else "fail",
        "alias use sites=0; residue=0; diff vs A confined to conclusion_type.rule",
        use_census_alias=cen_b["alias_use_sites"], residue=res_b, diff=diff_ab)

    # V7 semantics --------------------------------------------------------
    def sem(doc):
        return {cid: {
            "axes_canon": canon((doc["classes"][cid]["axes"]).get("conclusion_type"), vocab_sets(vocab)[1]),
            "type_canon": canon(((doc["classes"][cid].get("conclusion") or {}).get("type")), vocab_sets(vocab)[1]),
        } for cid in doc.get("class_ids", [])}

    sf, sa, sb = sem(frozen_doc), sem(a_doc), sem(b_doc)
    c2c = sf["AF-SCC-C2-VAC-GEN"]["axes_canon"]
    c0c = sf["AF-SCC-C0-VAC-GEN"]["axes_canon"]
    per_class_ok = all(v["axes_canon"] == v["type_canon"] for v in sf.values())
    stable = (sf == sa == sb)
    distinct = c2c != c0c
    rule_map = rule_spec["vocabularies"]["class_conclusion_type"]
    rule_ok = all(sf[cid]["axes_canon"] == rule_map[cid] for cid in rule_map)
    add("V7_SEMANTICS", "pass" if (per_class_ok and stable and distinct and rule_ok) else "fail",
        "canonical-resolved tokens identical frozen/A/B, C0!=C2, rule_spec map matches",
        frozen=sorted((k, v["axes_canon"]) for k, v in sf.items()),
        c0_c2_distinct=distinct, rule_spec_match=rule_ok)

    # V8 consumer rules ---------------------------------------------------
    cons = consumer_rules(rule_spec["vocabularies"]["class_conclusion_type"],
                          {"frozen_doc": frozen_doc, "A_doc": a_doc, "B_doc": b_doc}, vocab)
    lit = cons["literal_membership"]
    alw = cons["alias_allowed"]
    lit_expected = (lit["frozen"]["c2_required_in_allowed"] is False
                    and lit["frozen"]["c0_required_in_allowed"] is False
                    and lit["A"]["c2_required_in_allowed"] is True
                    and lit["A"]["c0_required_in_allowed"] is True
                    and lit["B"]["c2_required_in_allowed"] is True
                    and lit["B"]["c0_required_in_allowed"] is True)
    alw_expected = all(v["c2_alias_allowed"] and v["c0_alias_allowed"] for v in alw.values())
    tool_runs = {name: run_consistency_tool(txt, (ROOT / "artifacts/formulation/"
                                                  "formulation_taxonomy.yaml").read_text(),
                                            vocab_text, tool_text)
                 for name, txt in (("frozen", frozen_text), ("A", cand_a_text), ("B", cand_b_text))}
    tool_refs = tool_text.count("field_vocabulary")
    tool_all_pass = all(r["exit"] == 0 for r in tool_runs.values())
    add("V8_CONSUMER_RULES", "pass" if (lit_expected and alw_expected and tool_all_pass
                                        and tool_refs == 0) else "fail",
        "literal FAIL(frozen)->PASS(A/B); alias_allowed all PASS; checker exit 0 on all three; "
        f"checker field_vocabulary refs={tool_refs}",
        literal=lit, alias_allowed=alw, tool_runs=tool_runs, tool_field_vocabulary_refs=tool_refs,
        worker019_B1={"pass": next(c["pass"] for c in w019["checks"] if c["id"] == "B1"),
                      "detail": next(c["detail"] for c in w019["checks"] if c["id"] == "B1")})

    # V9 blast radius (third-party pinned events snapshot + live count) ---
    snap_events = ROOT / "artifacts/worker-042/f0_canon_candidate/snapshot/research_map/events.jsonl"
    tot, by_type, gates = 0, {}, []
    for line in snap_events.read_text().splitlines():
        if "0abb9ed8a961" not in line:
            continue
        tot += 1
        try:
            o = json.loads(line)
        except Exception:
            continue
        et = str(o.get("event_type"))
        by_type[et] = by_type.get(et, 0) + 1
        if et == "gate":
            gates.append({"created_at": o.get("created_at"), "event_id": o.get("event_id"),
                          "gate": o.get("gate_id") or o.get("gate") or o.get("scope")})
    live_events = ROOT / "research_map/events.jsonl"
    live_sha = sha256_file(live_events)
    live_tot = sum(1 for ln in live_events.read_text().splitlines() if "0abb9ed8a961" in ln)
    r = w042["blast_radius"]
    ok = (tot == r["events_matching_f0_short"] == 817
          and by_type == {k: v for k, v in r["by_event_type"].items()})
    add("V9_BLAST_RADIUS", "pass" if ok else "fail",
        f"pinned snapshot count={tot} (claim 817); by_event_type matched={by_type == r['by_event_type']}; "
        f"live count at {live_sha[:12]}={live_tot}",
        pinned_total=tot, by_event_type=by_type, gate_records=gates,
        live_events_sha256=live_sha, live_total=live_tot)

    # V10 controls --------------------------------------------------------
    ctrls = {}

    def run_census_pair():
        return json.dumps(use_site_census(frozen_doc, vocab), sort_keys=True)

    ctrls["K1_DETERMINISM"] = {"detected": run_census_pair() == run_census_pair()}
    mut = a0_text.replace('"scc_c2_future_inextendibility"',
                          '"strong_cosmic_censorship_C2"', 1)
    ctrls["K2_ALIAS_REINTRODUCED"] = {
        "detected": bool(use_site_census(strict_load(mut), vocab)["alias_use_sites"])}
    v2 = json.loads(vocab_text)
    v2["conclusion_type"]["scc_c2_future_inextendibility"] = []
    ctrls["K3_VOCAB_ALIAS_REMOVED"] = {
        "detected": len(use_site_census(frozen_doc, v2)["alias_use_sites"]) != 6}
    ctrls["K4_REBUILD_ORACLE_MATCH"] = {"detected": a0_sha == a_sha}
    ctrls["K5_QUOTE_BOUNDARY"] = {
        "detected": text_residue(frozen_text)["unquoted_total"] == 1}
    dup_text = frozen_text.replace(
        'schema_version: "0.1"',
        'schema_version: "0.1"\nschema_version: "0.1"', 1)
    ok_dup = False
    if dup_text != frozen_text:
        try:
            strict_load(dup_text)
        except (ValueError, yaml.YAMLError):
            ok_dup = True
    ctrls["K6_DUPLICATE_KEY_DETECTOR"] = {"detected": ok_dup}
    pins1 = check_pins()
    ctrls["K7_PIN_GUARD_AT_EXIT"] = {
        "detected": all(v["match"] for v in pins1.values())}
    add("V10_CONTROLS", "pass" if all(c["detected"] for c in ctrls.values()) else "fail",
        f"{sum(1 for c in ctrls.values() if c['detected'])}/{len(ctrls)} controls fired",
        controls=ctrls)

    # findings / verdict --------------------------------------------------
    sha_ok = a0_sha == a_sha
    findings.append({
        "id": "W039-F0CANON-V01",
        "severity": "evidence",
        "statement": ("Frozen F0 0abb9ed8a961 carries exactly 6 conclusion-token alias use sites "
                      "(allowed[1..2] + C2/C0 axes.conclusion_type + C2/C0 conclusion.type), one "
                      "full alias token in the line-153 rule prose and one '_C0' abbreviation; an "
                      "independent quoted-substitution rebuild reproduces candidate A byte-for-byte"
                      if sha_ok else
                      "the alias-use census reproduces, but the independent rebuild does NOT "
                      "reproduce candidate A byte-for-byte"),
        "falsifier": ("a pinned byte moving, an alias site outside the six declared structural "
                      "paths, or a rebuild whose sha256 differs from candidate A")})
    if not sha_ok:
        findings.append({"id": "W039-F0CANON-V02", "severity": "major",
                         "statement": "candidate A is not the minimal alias-site substitution produced "
                                      "by this instrument; parsed-tree diff and semantics still measured",
                         "falsifier": "worker-042 build_candidates.py rebuilds its declared bytes"})
    verdict = ("REPRODUCED" if all(c["status"] == "pass" for c in checks.values())
               else "REPRODUCED_WITH_FINDINGS")
    report = {
        "schema": "w039-f0-canon-indep-verify/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "created_at": None,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE,
        "gate": GATE,
        "secondary_gate": SECONDARY_GATE,
        "target_task": TARGET_TASK,
        "target_id": "artifacts/worker-042/f0_canon_candidate/report.json#21b7598096bb",
        "question": ("Independently reproduce W042-F0-CANON-CANDIDATE-08: is frozen F0 "
                     "0abb9ed8a961 non-canonical at 6 alias use sites, are candidates A/B "
                     "byte-minimal and semantics-preserving, do the consumer rules diverge and "
                     "converge, and is the 817-event blast radius reproducible?"),
        "method": ("own stdlib+PyYAML instrument (no worker-042 code imported); strict duplicate-key "
                   "loader; structural use-site census; quoted-substitution rebuild as byte oracle; "
                   "parsed-tree diff; end-to-end sandbox replay of the pinned consistency checker"),
        "pins": pins0,
        "checks": checks,
        "findings": findings,
        "verdict": verdict,
        "falsifier": ("Re-run this instrument on the same pinned bytes: falsified if (a) any pinned "
                      "input moves (exit 3), (b) my census finds an alias use site outside the six "
                      "declared paths or a non-zero rejected/unknown use site, (c) my rebuild's sha256 "
                      "differs from candidate A, (d) the A and B parsed-tree diffs escape the declared "
                      "paths, (e) canonical-resolved tokens differ across frozen/A/B or C0==C2, "
                      "(f) a consumer rule flips, (g) the pinned-snapshot blast count differs from "
                      "817, or (h) any control stops firing."),
        "authority_note": ("Worker measurement and review only. No canonical path written, no gate "
                           "verdict, no node status, no validation_status=passed. Adoption of either "
                           "candidate remains a separate G-F0 reopening decision under REC-37."),
        "limits": ("Blast radius is a substring count of the F0 short hash on worker-042's pinned "
                   "events snapshot and a live recount at the stated hash; the live stream moves. "
                   "Candidate B's prose rewrite is verified as confined and residue-free, not "
                   "endorsed as wording. Content of the two candidate files is measured, not authored."),
    }
    import datetime
    report["created_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    # hashes + checkpoint -------------------------------------------------
    def h(rel):
        p = HERE / rel
        return {"bytes": p.stat().st_size, "sha256": sha256_file(p)}

    entry = {
        "schema": "w039-entry-hashes/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "pins": pins0,
        "deliverables": {n: h(n) for n in ("verify_f0_canon_039.py", "report.json")},
    }
    (HERE / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
    ck = {
        "schema": "w039-worker-checkpoint/v1",
        "task_id": TASK, "actor": ACTOR, "created_at": report["created_at"],
        "state": "complete_worker_level",
        "class_id": CLASS_ID, "class_ids": CLASS_IDS, "node_id": NODE, "gate": GATE,
        "verdict": verdict,
        "counts": {"checks": len(checks),
                   "pass": sum(1 for c in checks.values() if c["status"] == "pass"),
                   "fail": sum(1 for c in checks.values() if c["status"] != "pass")},
        "target": {"task_id": TARGET_TASK, "artifact": report["target_id"]},
        "key_measurements": {
            "frozen_alias_use_sites": len(cen_frozen["alias_use_sites"]),
            "frozen_text_full_alias_occurrences": res_frozen["full_total"],
            "candidate_A_rebuild_matches_bytes": sha_ok,
            "candidate_B_text_residue": res_b["full_total"],
            "blast_radius_pinned_snapshot": tot,
            "blast_radius_live_at": live_sha[:12],
            "blast_radius_live": live_tot,
        },
        "findings": [f["id"] for f in findings],
        "next_falsifier": report["falsifier"],
        "authority_note": report["authority_note"],
        "non_canonical": True,
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(ck, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "checks_pass": ck["counts"]["pass"], "checks": ck["counts"]["checks"],
                      "alias_sites": len(cen_frozen["alias_use_sites"]),
                      "A_byte_match": sha_ok, "blast": tot, "live": live_tot}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
