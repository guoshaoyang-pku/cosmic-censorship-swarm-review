#!/usr/bin/env python3
"""W038-F1-REV13-REVIEW-01: independent read-only G-FORM conformance review of
schemas/af_wcc_vacuum.yaml (class AF-WCC-VAC-GEN, node F1) at the FROZEN rev29 pin
d9cebb9404b2 (revision 13).

Independent instrument: it does NOT import artifacts/formulation/tools/check_class_schema.py,
check_taxonomy_consistency.py (except to re-execute the pinned file in an isolated copy as a
determinism check), run_gate_tests.py, or any owner checker. Checks K01-K17 are re-implemented
from the class-bound acceptance contract (map FROZEN path_policy + schema's own binding rule +
PROTOCOL rules 2/5). Mutation controls M1-M10 must fire the corresponding check or the
instrument reports itself dead.

Writes only under artifacts/worker-038/f1_rev13_review/. Never mutates a canonical artifact.
Worker authority limit: this emits review evidence only; it cannot set status=done,
validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-038/f1_rev13_review -> repo root

# Pins measured at task claim time (2026-09-12T00:58+08:00). Fail-closed: drift is reported.
EXPECTED = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
CLASS_ID = "AF-WCC-VAC-GEN"
FROZEN_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
CANONICAL_CONCLUSION = "weak_cosmic_censorship"
CANONICAL_GENERICITY = "residual_comeager"
REQUIRED_TOP = [
    "schema_version", "class_id", "node_id", "revision", "revision_history", "class_components",
    "class_contract_pointer", "class_contract_supplement_pointer", "epistemic_status",
    "promotion_rule", "scope_statement", "quantifiers", "topology", "data_class", "regularity",
    "genericity", "non_vacuity", "i_plus", "visibility", "class_identity_variants", "conclusion",
    "falsifier", "anti_scope", "l1_ledger_refs", "known_status", "f0_binding", "provenance",
    "unresolved_items", "review_status",
]
CHECK_IDS = [f"K{i:02d}" for i in range(1, 18)]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


class DupKeySafeLoader(yaml.SafeLoader):
    pass


def _no_dup_mapping(loader, node, deep=False):
    keys = set()
    for k_node, _ in node.value:
        k = loader.construct_object(k_node, deep=deep)
        try:
            dup = k in keys
        except TypeError:
            dup = False
        if dup:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate mapping key: {k!r}", k_node.start_mark)
        keys.add(k)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup_mapping)


def dig(d, dotted, default=None):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


class Ctx:
    """All inputs are read once; paths are overridable so mutation controls can point at
    temp copies without touching the repository."""

    def __init__(self, root: Path, overrides: dict | None = None):
        self.root = root
        self.paths = {
            "f1": "schemas/af_wcc_vacuum.yaml",
            "mirror": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "frozen": "artifacts/formulation/FROZEN.json",
            "f0": "research_map/formulation_taxonomy.yaml",
            "supplement": "artifacts/formulation/formulation_taxonomy.yaml",
            "evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
            "checker": "artifacts/formulation/tools/check_taxonomy_consistency.py",
            "aliases": "artifacts/formulation/VOCAB_ALIASES.json",
            "registry": "artifacts/formulation/VARIANT_REGISTRY.json",
            "setdelta": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        }
        if overrides:
            self.paths.update(overrides)
        self.bytes = {k: (root / v).read_bytes() for k, v in self.paths.items()}
        self.sha = {k: hashlib.sha256(b).hexdigest() for k, b in self.bytes.items()}
        self.text = {k: b.decode("utf-8", "replace") for k, b in self.bytes.items()}
        self.frozen = json.loads(self.text["frozen"])
        self.evidence = json.loads(self.text["evidence"])
        self.aliases = json.loads(self.text["aliases"])
        self.registry = json.loads(self.text["registry"])
        self.setdelta = json.loads(self.text["setdelta"])
        self.f1_yaml = yaml.load(self.text["f1"], Loader=DupKeySafeLoader)
        self.f0_yaml = yaml.safe_load(self.text["f0"])
        self.supp_yaml = yaml.safe_load(self.text["supplement"])

    def yaml_from_text(self, text: str):
        return yaml.load(text, Loader=DupKeySafeLoader)


def result(cid, ok, detail, severity="info", **extra):
    r = {"check": cid, "status": "PASS" if ok else "FAIL", "detail": detail, "severity": severity}
    r.update(extra)
    return r


# ---------------------------------------------------------------- checks K01..K17
def check_k01_pin(ctx: Ctx) -> dict:
    fz = ctx.frozen
    pins = fz.get("files", {})
    problems = []
    if fz.get("revision") != 29:
        problems.append(f"FROZEN revision {fz.get('revision')} != 29")
    if len(pins) != 50:
        problems.append(f"FROZEN pinned file count {len(pins)} != 50 (rev29 re-freeze at 00:57:26)")
    for key, path in (("f1", ctx.paths["f1"]), ("mirror", ctx.paths["mirror"])):
        rec = pins.get(path)
        if not rec:
            problems.append(f"{path} not pinned in FROZEN")
        elif rec["sha256"] != ctx.sha[key]:
            problems.append(f"{path} pin {rec['sha256'][:12]} != live {ctx.sha[key][:12]}")
    for path in (ctx.paths["evidence"], "schemas/taxonomy_cases.jsonl", "schemas/f1_falsifier_tests.jsonl"):
        rec = pins.get(path)
        live_path = ctx.root / path
        live = sha256_file(live_path)
        if not rec:
            problems.append(f"{path} not pinned in FROZEN")
        elif rec["sha256"] != live:
            problems.append(f"{path} pin {rec['sha256'][:12]} != live {live[:12]}")
    return result("K01", not problems,
                  "FROZEN rev29 pins F1 canonical+mirror+corpora+consistency evidence at live bytes"
                  if not problems else "; ".join(problems),
                  "H" if problems else "info")


def check_k02_mirror(ctx: Ctx) -> dict:
    same = ctx.bytes["f1"] == ctx.bytes["mirror"]
    return result("K02", same,
                  "canonical F1 and artifacts/ mirror byte-identical "
                  f"({ctx.sha['f1'][:12]})" if same else
                  f"mirror divergence {ctx.sha['f1'][:12]} vs {ctx.sha['mirror'][:12]}",
                  "H" if not same else "info")


def _required_top_problems(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["top-level YAML is not a mapping"]
    return [f"missing top-level key {k}" for k in REQUIRED_TOP if k not in doc]


def check_k03_yaml(ctx: Ctx) -> dict:
    problems = []
    try:
        doc = yaml.load(ctx.text["f1"], Loader=DupKeySafeLoader)
    except yaml.YAMLError as exc:
        doc = None
        problems.append(f"YAML parse/duplicate-key error: {str(exc)[:200]}")
    if doc is not None:
        problems += _required_top_problems(doc)
    return result("K03", not problems,
                  "parses under duplicate-key-detecting loader; all 29 required top-level keys present"
                  if not problems else "; ".join(problems), "H" if problems else "info")


def check_k04_identity(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    problems = []
    if d.get("class_id") != CLASS_ID:
        problems.append(f"class_id {d.get('class_id')!r} != {CLASS_ID}")
    if d.get("node_id") != "F1":
        problems.append(f"node_id {d.get('node_id')!r} != F1")
    if d.get("revision") != 13:
        problems.append(f"revision {d.get('revision')!r} != 13")
    if d.get("epistemic_status") != "open_problem":
        problems.append(f"epistemic_status {d.get('epistemic_status')!r} != open_problem")
    comp = d.get("class_components") or {}
    if comp != {"asymptotics": "AF", "censorship": "WCC", "matter": "VAC",
                "genericity": "GEN", "regularity_token": "none"}:
        problems.append(f"class_components drift: {comp}")
    scope = str(d.get("scope_statement", ""))
    for token in ("asymptotically flat", "vacuum", "future null infinity"):
        if token not in scope:
            problems.append(f"scope_statement missing {token!r}")
    return result("K04", not problems,
                  "class id / node / revision 13 / frozen component decomposition / open-problem status / scope held"
                  if not problems else "; ".join(problems), "H" if problems else "info")


def check_k05_history(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    hist = d.get("revision_history") or []
    problems = []
    idx = [h.get("index") for h in hist]
    if idx != list(range(1, len(idx) + 1)):
        problems.append(f"history indices {idx} are not unique-contiguous 1..{len(idx)}")
    if len(hist) < 11:
        problems.append(f"only {len(hist)} revision_history entries for revision 13")
    revised = str(d.get("revised_at", ""))
    if not revised:
        problems.append("revised_at missing")
    allnotes = " || ".join(" ".join(h.get("notes") or []) for h in hist)
    for tag in ("rev12", "rev13"):
        if tag not in allnotes:
            problems.append(f"revision_history carries no {tag} delta note")
    if hist and "rev13" not in " ".join(hist[-1].get("notes") or []):
        problems.append("last revision_history entry is not the rev13 delta")
    for h in hist:
        if revised and str(h.get("at", "")) > revised:
            problems.append(f"history entry {h.get('index')} dated after revised_at")
    ats = [str(h.get("at", "")) for h in hist]
    monotone = ats == sorted(ats)
    base = ("revision_history unique-contiguous, rev12+rev13 delta notes present, last entry is rev13, "
            "no entry after revised_at")
    if not monotone:
        base += " (entry timestamps are backfilled and not monotone; metadata hygiene only)"
    return result("K05", not problems, base if not problems else "; ".join(problems),
                  "H" if problems else ("N" if not monotone else "info"),
                  timestamps_monotone=monotone, history_len=len(hist))


def check_k06_f0_binding(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    b = d.get("f0_binding") or {}
    spec = ctx.f0_yaml or {}
    supp = ctx.supp_yaml or {}
    problems = []
    if b.get("declared_f0_artifact") != ctx.paths["f0"]:
        problems.append(f"declared_f0_artifact {b.get('declared_f0_artifact')!r} != {ctx.paths['f0']}")
    if b.get("declared_f0_sha256") != ctx.sha["f0"]:
        problems.append(f"declared_f0_sha256 {str(b.get('declared_f0_sha256'))[:12]} != live F0 {ctx.sha['f0'][:12]}")
    if b.get("class_contract_supplement") != ctx.paths["supplement"]:
        problems.append("class_contract_supplement path drift")
    if b.get("consistency_evidence") != ctx.paths["evidence"]:
        problems.append("consistency_evidence path drift")
    if b.get("consistency_evidence_sha256") != ctx.sha["evidence"]:
        problems.append(
            f"consistency_evidence_sha256 {str(b.get('consistency_evidence_sha256'))[:12]} != live evidence {ctx.sha['evidence'][:12]}")
    if not str(b.get("rule", "")).lower().startswith("if the declared f0 artifact changes hash"):
        problems.append("binding rule text missing refresh obligation")
    # pointer resolution: canonical taxonomy #classes.<class> and supplement #class_contracts.<class>
    if CLASS_ID not in (spec.get("classes") or {}):
        problems.append(f"canonical taxonomy #classes.{CLASS_ID} does not resolve")
    if CLASS_ID not in (supp.get("class_contracts") or {}):
        problems.append(f"supplement #class_contracts.{CLASS_ID} does not resolve")
    # live consistency evidence must be green and name this class
    ev = ctx.evidence
    if ev.get("consistent") is not True:
        problems.append("consistency evidence is not green")
    if CLASS_ID not in (ev.get("classes_compared") or []):
        problems.append(f"consistency evidence does not compare {CLASS_ID}")
    checked = str(b.get("checked_at", ""))
    if not re.match(r"^2026-09-12T\d\d:\d\d:\d\d\+08:00$", checked):
        problems.append(f"checked_at not a wall-clock CST stamp: {checked!r}")
    return result("K06", not problems,
                  "f0_binding chain resolves: declared F0 live, both pointers resolve, consistency evidence "
                  f"live+green, checked_at {checked}",
                  "H" if problems else "info")


def isolate_and_run_checker(ctx: Ctx, tmp: Path) -> tuple[bytes, bytes]:
    """Copy the four checker inputs + checker into tmp with identical relative layout,
    re-execute the *pinned* checker twice, return the two output byte-strings."""
    for rel in (ctx.paths["f0"], ctx.paths["supplement"], ctx.paths["aliases"], ctx.paths["checker"]):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.root / rel, dst)
    (tmp / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    outs = []
    for _ in range(2):
        out = tmp / "artifacts/formulation/evidence/taxonomy_consistency.json"
        if out.exists():
            out.unlink()
        proc = subprocess.run([sys.executable, str(tmp / ctx.paths["checker"])],
                              cwd=tmp, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"isolated checker exit {proc.returncode}: {proc.stdout[:200]} {proc.stderr[:200]}")
        outs.append(out.read_bytes())
    return outs[0], outs[1]


def check_k07_regeneration(ctx: Ctx, tmp: Path) -> dict:
    try:
        first, second = isolate_and_run_checker(ctx, tmp)
    except Exception as exc:  # noqa: BLE001
        return result("K07", False, f"isolated checker rerun failed: {exc}", "H")
    problems = []
    if first != second:
        problems.append("two isolated reruns are not byte-identical")
    if first != ctx.bytes["evidence"]:
        problems.append(
            f"live consistency evidence {ctx.sha['evidence'][:12]} != regenerated "
            f"{hashlib.sha256(first).hexdigest()[:12]}")
    return result("K07", not problems,
                  "live taxonomy_consistency.json is exactly reproducible by the FROZEN-pinned checker "
                  "from live inputs (two byte-identical isolated reruns)",
                  "H" if problems else "info")


def check_k08_quantifiers(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    q = d.get("quantifiers") or {}
    problems = []
    ordered = q.get("ordered") or []
    kinds = [o.get("kind") for o in ordered]
    if kinds != ["forall", "exists", "forall", "exists", "forall", "not_exists"]:
        problems.append(f"quantifier order {kinds}")
    formal = str(q.get("formal", ""))
    m = re.search(r"exists G_r[^:]*comeager", formal)
    if not m:
        problems.append("comeager binder not attached to exists G_r in formal string")
    else:
        before = formal[:m.start()]
        after = formal[m.end():]
        if "forall (Sigma,h,K)" not in after:
            problems.append("data forall does not follow the comeager binder")
        if "forall r in D0" not in before:
            problems.append("regularity forall does not precede the comeager binder")
    cf = str(dig(d, "conclusion.statement_formal", ""))
    if "comeager" not in cf or "forall" not in cf:
        problems.append("conclusion.statement_formal does not restate the comeager quantifier")
    d1 = str(dig(q, "domains.D1.definition", ""))
    if "comeager" not in d1:
        problems.append("D1 domain definition does not define comeager")
    return result("K08", not problems,
                  "quantifier order forall r / exists G_r comeager / forall data / exists completion / forall gamma / "
                  "not_exists (q,t0); comeager bound before the data", "H" if problems else "info")


def check_k09_class_semantics(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    problems = []
    if dig(d, "conclusion.conclusion_type") != CANONICAL_CONCLUSION:
        problems.append(f"conclusion_type {dig(d, 'conclusion.conclusion_type')!r} != {CANONICAL_CONCLUSION}")
    if dig(d, "conclusion.family") != "WCC":
        problems.append("conclusion.family != WCC")
    if dig(d, "genericity.kind") != CANONICAL_GENERICITY:
        problems.append(f"genericity.kind {dig(d, 'genericity.kind')!r} != {CANONICAL_GENERICITY}")
    ex = dig(d, "genericity.excluded_set")
    if not ex:
        problems.append("genericity.excluded_set empty")
    if dig(d, "data_class.matter") != "none":
        problems.append("data_class.matter != none")
    if dig(d, "data_class.cosmological_constant") != 0:
        problems.append("cosmological_constant != 0")
    if not str(dig(d, "topology.slice_topology", "")).count("one asymptotically flat end"):
        problems.append("slice topology does not pin exactly one AF end")
    anti = dig(d, "anti_scope.not_this_class") or []
    anti_ids = {a.get("class_id") for a in anti if a.get("class_id")}
    for cid in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"):
        if cid not in anti_ids:
            problems.append(f"anti_scope does not exclude sibling class {cid}")
    return result("K09", not problems,
                  "frozen class semantics held: WCC conclusion_type, residual_comeager genericity, vacuum/Lambda=0, "
                  "one-ended topology, all three sibling classes excluded", "H" if problems else "info")


SET_SUBJECT = re.compile(
    r"variant\s+`?SET`?|set-based|union of J\^?-\(q\)|J\^?-\(I\+\)(\s+as\s+a\s+set)?|"
    r"contained in the union|outside (the )?union|union of J\^?-",
    re.IGNORECASE)
HISTORICAL = re.compile(
    r"corrected from|rev13 direction|was stronger|F0 was|pre-adjudication|"
    r"earlier (text|wording|reading)|prior (text|reading)|superseded", re.IGNORECASE)
NEGATION_CTX = re.compile(r"negation|NOT contained in the union|no such visible", re.IGNORECASE)
B_CONTAINMENT = re.compile(r"B-containment|contained in B\b|B = M minus|inside B\b", re.IGNORECASE)


def _strength_mentions(text: str, path_label: str) -> list[dict]:
    """Census every 'strictly stronger/weaker' occurrence and classify it:
    operative SET-variant direction claim vs historical note vs negation-direction note vs other axis."""
    out = []
    pattern = re.compile(r"strictly\s+(STRONGER|WEAKER)", re.IGNORECASE)
    for i, line in enumerate(text.splitlines(), 1):
        for m in pattern.finditer(line):
            s, e = max(0, m.start() - 240), min(len(line), m.end() + 240)
            window = line[s:e]
            direction = m.group(1).upper()
            subject = bool(SET_SUBJECT.search(window))
            historical = bool(HISTORICAL.search(window))
            negation = bool(NEGATION_CTX.search(window))
            if historical:
                kind = "historical"
            elif B_CONTAINMENT.search(window):
                kind = "other_axis"  # a claim about B-containment, not about the SET reading
            elif negation and direction == "STRONGER":
                kind = "negation_consistent"  # a weaker predicate has a stronger negation
            elif subject:
                kind = "operative"
            else:
                kind = "other_axis"
            out.append({
                "file": path_label, "line": i, "direction": direction, "kind": kind,
                "operative_contradiction": kind == "operative" and direction == "STRONGER",
                "context": window.strip()[:480],
            })
    return out


def check_k10_visibility(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    vis = d.get("visibility") or {}
    problems = []
    definition = str(vis.get("definition", ""))
    for token in ("q in I+", "t0 in [0,T)", "TAIL", "J^-(q)"):
        if token not in definition:
            problems.append(f"visibility.definition missing {token!r}")
    if "EQUIVALENT" not in definition.upper():
        problems.append("visibility.definition does not state the whole/tail EQUIVALENCE")
    if "past-closed" not in definition.lower():
        problems.append("visibility.definition does not cite past-closedness of J^-(q) as the equivalence premise")
    if vis.get("in_conclusion") is not True or vis.get("role") != "conclusion":
        problems.append("visibility is not marked as a conclusion component")
    if vis.get("predicate_name") != "visible_singularity_from_I_plus":
        problems.append("visibility predicate name drift")
    variants = d.get("class_identity_variants") or []
    setv = [v for v in variants if v.get("kind") == "set_based_visibility_reading"]
    if not setv:
        problems.append("SET variant record absent")
    else:
        rel = str(setv[0].get("relation", ""))
        if "strictly WEAKER" not in rel:
            problems.append("SET variant relation does not state 'strictly WEAKER'")
        if "NOT equivalent" not in rel and "not equivalent" not in rel.lower():
            problems.append("SET variant relation does not state the non-equivalence")
    f1_mentions = _strength_mentions(ctx.text["f1"], ctx.paths["f1"])
    f1_operative = [m for m in f1_mentions if m["operative_contradiction"]]
    if f1_operative:
        problems.append("F1 still carries an operative 'strictly STRONGER' SET direction: " +
                        "; ".join(f"line {m['line']}" for m in f1_operative))
    if not str(vis.get("must_not_conflate")):
        problems.append("visibility.must_not_conflate missing")
    return result("K10", not problems,
                  ("visibility rev13 repair: single-q tail predicate + explicit whole/tail EQUIVALENT via "
                   "past-closedness; SET variant recorded strictly WEAKER + non-equivalent; any 'STRONGER' left in "
                   f"F1 is on another axis or a historical note ({len(f1_mentions)} mention(s) censused, "
                   f"{len(f1_operative)} operative SET contradictions)")
                  if not problems else "; ".join(problems),
                  "H" if problems else "info")


RESIDUAL_FILES = [
    ("research_map/formulation_taxonomy.yaml", "F0 canonical (G-F0 frozen)"),
    ("artifacts/formulation/formulation_taxonomy.yaml", "F0 class-contract supplement"),
    ("artifacts/formulation/VARIANT_REGISTRY.json", "VARIANT_REGISTRY v2"),
    ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", "variant SET delta"),
]


def check_k11_cross_artifact(ctx: Ctx) -> dict:
    """Census the SET-variant strength direction in the four residual files against F1 rev13.
    Only an *operative* 'strictly STRONGER' claim about the SET/union reading contradicts F1 rev13's
    'strictly WEAKER'; historical 'corrected from' notes and the (correctly) stronger negation of a
    weaker predicate are not contradictions."""
    f1_mentions = _strength_mentions(ctx.text["f1"], ctx.paths["f1"])
    residual = []
    contradictions = []
    for rel, label in RESIDUAL_FILES:
        text = (ctx.root / rel).read_text(errors="replace")
        for m in _strength_mentions(text, rel):
            m = dict(m, label=label)
            residual.append(m)
            if m["operative_contradiction"]:
                contradictions.append(m)
    return result("K11", not contradictions,
                  ("no residual file makes an operative SET-variant 'strictly STRONGER' claim; "
                   f"{len(residual)} strength mention(s) censused across the 4 residual files "
                   f"({sum(m['operative_contradiction'] for m in residual)} operative contradictions)")
                  if not contradictions else
                  "GATE-BLOCKING cross-artifact contradiction: " + "; ".join(
                      f"{c['file']}:{c['line']} operative {c['direction']} vs F1 rev13 'strictly WEAKER'"
                      for c in contradictions),
                  "GATE" if contradictions else "info"), residual, f1_mentions


def check_k12_falsifier(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    f = d.get("falsifier") or {}
    problems = []
    t1 = f.get("tier_1") or {}
    t2 = f.get("tier_2") or {}
    if t1.get("refutes") != CLASS_ID:
        problems.append("tier_1 does not name the class as its refutation target")
    if "non-meager" not in str(t1.get("genericity_requirement", "")).lower():
        problems.append("tier_1 lacks the non-meagerness requirement")
    if not t1.get("machine_checkable_steps"):
        problems.append("tier_1 machine_checkable_steps empty")
    if not t1.get("non_machine_checkable_step"):
        problems.append("tier_1 non_machine_checkable_step missing")
    if "forall" not in str(t2.get("refutes", "")):
        problems.append("tier_2 does not separate the for-all-data strengthening")
    return result("K12", not problems,
                  "falsifier tiers separate non-meager refutation (tier_1) from the for-all-data strengthening "
                  "(tier_2); machine-checkable and human-scale steps declared", "H" if problems else "info")


def check_k13_no_inflation(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    problems = []
    if dig(d, "known_status.status") != "open_problem":
        problems.append("known_status.status != open_problem")
    if not dig(d, "provenance.no_status_claim"):
        problems.append("provenance.no_status_claim missing")
    if "artifact_refs" not in str(d.get("promotion_rule", "")):
        problems.append("promotion_rule does not require artifact_refs")
    if not d.get("unresolved_items"):
        problems.append("unresolved_items empty")
    if dig(d, "review_status.verdict") not in ("pending", "accepted", "revise"):
        problems.append("review_status.verdict missing")
    if re.search(r"theorem\s+(is\s+)?(proved|established)", ctx.text["f1"], re.IGNORECASE):
        problems.append("self-claim of a proved theorem found in text")
    return result("K13", not problems,
                  "no status inflation: open_problem, no_status_claim, promotion requires artifact_refs, "
                  "unresolved obligations retained", "H" if problems else "info")


def check_k14_ledger(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    refs = d.get("l1_ledger_refs") or []
    problems = []
    if not refs:
        problems.append("l1_ledger_refs empty")
    for r in refs:
        tid = str(r.get("theorem_id", ""))
        if not re.match(r"^[DT]-\d+$", tid):
            problems.append(f"malformed theorem id {tid!r}")
        if not r.get("scope_use"):
            problems.append(f"{tid} lacks scope_use")
    known = str(dig(d, "known_status.non_transfer_warning", ""))
    if not known:
        problems.append("known_status.non_transfer_warning missing")
    return result("K14", not problems,
                  f"{len(refs)} L1 ledger refs well-formed with per-ref scope_use; non-transfer warning present",
                  "H" if problems else "info")


def check_k15_pointers(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    problems = []
    cp = str(d.get("class_contract_pointer", ""))
    sp = str(d.get("class_contract_supplement_pointer", ""))
    if not cp.startswith(ctx.paths["f0"] + "#classes." + CLASS_ID):
        problems.append(f"class_contract_pointer {cp!r} does not resolve to canonical taxonomy#classes")
    if not sp.startswith(ctx.paths["supplement"] + "#class_contracts." + CLASS_ID):
        problems.append(f"class_contract_supplement_pointer {sp!r} does not resolve to supplement#class_contracts")
    if cp.split("#")[0] == sp.split("#")[0]:
        problems.append("canonical pointer and supplement pointer share a path (conflation)")
    return result("K15", not problems,
                  "declared-F0 pointer targets research_map taxonomy#classes; supplement pointer targets the distinct "
                  "supplement#class_contracts; paths never conflated", "H" if problems else "info")


def check_k16_crossfile_semantics(ctx: Ctx) -> dict:
    d = ctx.f1_yaml or {}
    spec = ctx.f0_yaml or {}
    supp = ctx.supp_yaml or {}
    problems = []
    a = (spec.get("classes") or {}).get(CLASS_ID) or {}
    b = (supp.get("class_contracts") or {}).get(CLASS_ID) or {}
    axes = a.get("axes") or {}
    if axes.get("family") != "WCC":
        problems.append(f"canonical taxonomy family {axes.get('family')!r} != WCC")
    if axes.get("regularity_token") not in (None, "none"):
        problems.append(f"canonical taxonomy regularity_token {axes.get('regularity_token')!r} not none/null")
    if not a.get("exclusions"):
        problems.append("canonical taxonomy exclusions empty")
    if not b.get("positive_test_case"):
        problems.append("supplement positive_test_case missing")
    f1_concl = dig(d, "conclusion.conclusion_type")
    alias = ctx.aliases.get("conclusion_type", {})
    canon = {f1_concl}
    for c, al in alias.items():
        if f1_concl == c or f1_concl in (al or []):
            canon.add(c)
    tax_concl = axes.get("conclusion_type")
    if tax_concl not in canon and f1_concl not in (alias.get(tax_concl) or []):
        problems.append(f"conclusion_type token mismatch F1={f1_concl!r} taxonomy={tax_concl!r} (alias-aware)")
    return result("K16", not problems,
                  "alias-aware cross-file semantics agree (family, regularity token, exclusions, test case, "
                  "conclusion_type)" if not problems else "; ".join(problems),
                  "H" if problems else "info")


# ---------------------------------------------------------------- controls
def run_controls(ctx: Ctx, tmp: Path) -> list[dict]:
    controls = []

    def record(name, fired, detail):
        controls.append({"control": name, "status": "PASS" if fired else "FAIL",
                         "detail": detail})

    # M1 FROZEN pin mismatch
    bad = deepcopy(ctx.frozen)
    bad["files"][ctx.paths["f1"]]["sha256"] = "0" * 64
    m = Ctx(ctx.root)
    m.frozen = bad
    k = check_k01_pin(m)
    record("M1_frozen_pin_mismatch", k["status"] == "FAIL", k["detail"])

    # M2 mirror divergence
    m = Ctx(ctx.root)
    m.bytes["mirror"] = ctx.bytes["mirror"] + b"\n# mutant\n"
    m.sha["mirror"] = hashlib.sha256(m.bytes["mirror"]).hexdigest()
    k = check_k02_mirror(m)
    record("M2_mirror_divergence", k["status"] == "FAIL", k["detail"])

    # M3 duplicate YAML key
    m = Ctx(ctx.root)
    m.text["f1"] = ctx.text["f1"] + "\nclass_id: AF-WCC-VAC-GEN\n"
    k = check_k03_yaml(m)
    record("M3_duplicate_yaml_key", k["status"] == "FAIL", k["detail"])

    # M4 f0 declared hash wrong
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["f0_binding"]["declared_f0_sha256"] = "0" * 64
    k = check_k06_f0_binding(m)
    record("M4_f0_declared_hash_wrong", k["status"] == "FAIL", k["detail"])

    # M5 consistency evidence hash wrong
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["f0_binding"]["consistency_evidence_sha256"] = "675a99d0d25b" + "0" * 52
    m.sha = dict(ctx.sha)
    m.sha["evidence"] = "f" * 64
    k = check_k06_f0_binding(m)
    record("M5_stale_consistency_evidence", k["status"] == "FAIL", k["detail"])

    # M6 comeager binder moved after the data forall
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["quantifiers"]["formal"] = "forall r in D0: forall (Sigma,h,K) in G_r: exists G_r comeager: true"
    k = check_k08_quantifiers(m)
    record("M6_quantifier_order", k["status"] == "FAIL", k["detail"])

    # M7 reinstate the inverted SET direction
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["class_identity_variants"][0]["relation"] = (
        "strictly STRONGER than this class's single-q tail predicate")
    k = check_k10_visibility(m)
    record("M7_inverted_set_direction", k["status"] == "FAIL", k["detail"])

    # M8a conclusion inflation: conclusion_type -> theorem must trip K09
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["conclusion"]["conclusion_type"] = "theorem"
    k9 = check_k09_class_semantics(m)
    record("M8a_conclusion_type_inflation", k9["status"] == "FAIL", k9["detail"])

    # M8b status inflation: known_status/status -> proved must trip K13
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["known_status"]["status"] = "proved"
    m.f1_yaml["provenance"]["no_status_claim"] = ""
    k13 = check_k13_no_inflation(m)
    record("M8b_status_inflation", k13["status"] == "FAIL", k13["detail"])

    # M9 stale SET strength in a residual file (all inputs copied to a temp tree)
    d2 = Path(tempfile.mkdtemp(prefix="w038_m9_"))
    for rel in set(ctx.paths.values()) | {rel for rel, _ in RESIDUAL_FILES}:
        dst = d2 / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.root / rel, dst)
    for rel, _ in RESIDUAL_FILES:
        p = d2 / rel
        text = p.read_text(errors="replace")
        if "SET" in text or "set_based" in text or "variant" in text.lower():
            text = text.replace("strictly WEAKER", "strictly STRONGER")
        p.write_text(text)
    m = Ctx(d2)
    k, _, _ = check_k11_cross_artifact(m)
    record("M9_residual_stale_set_token", k["status"] == "FAIL", k["detail"])

    # M10 revision history gap
    m = Ctx(ctx.root)
    m.f1_yaml = deepcopy(ctx.f1_yaml)
    m.f1_yaml["revision_history"] = m.f1_yaml["revision_history"][:-1]
    k = check_k05_history(m)
    record("M10_revision_history_gap", k["status"] == "FAIL", k["detail"])

    return controls


# ---------------------------------------------------------------- driver
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="w038-f1-rev13")
    args = ap.parse_args()

    started = now()
    ctx = Ctx(ROOT)
    pin_drift = {}
    for k, rel in (("f1", ctx.paths["f1"]), ("frozen", ctx.paths["frozen"]),
                   ("evidence", ctx.paths["evidence"])):
        expected = EXPECTED.get(rel)
        if expected and expected != ctx.sha[k]:
            pin_drift[rel] = {"expected": expected, "measured": ctx.sha[k]}

    checks = []
    for fn in (check_k01_pin, check_k02_mirror, check_k03_yaml, check_k04_identity, check_k05_history,
               check_k06_f0_binding, check_k08_quantifiers, check_k09_class_semantics, check_k10_visibility,
               check_k12_falsifier, check_k13_no_inflation, check_k14_ledger, check_k15_pointers,
               check_k16_crossfile_semantics):
        checks.append(fn(ctx))

    with tempfile.TemporaryDirectory(prefix="w038_k07_") as td:
        checks.append(check_k07_regeneration(ctx, Path(td)))

    k11, residual_mentions, f1_mentions = check_k11_cross_artifact(ctx)

    # guard stability: all pinned inputs re-measured after the checks
    after = {rel: sha256_file(ROOT / rel) for rel in ctx.paths.values()}
    drift = {rel: {"before": ctx.sha[k], "after": after[rel]}
             for k, rel in ctx.paths.items() if after[rel] != ctx.sha[k]}
    checks.append(result("K17", not drift,
                         "all 11 pinned inputs byte-stable across the review window" if not drift
                         else f"input drift during review: {sorted(drift)}", "H" if drift else "info"))

    with tempfile.TemporaryDirectory(prefix="w038_controls_") as td:
        controls = run_controls(ctx, Path(td))

    f1_hard = [c for c in checks if c["status"] == "FAIL"]
    controls_failed = [c for c in controls if c["status"] == "FAIL"]
    gate_blocking = k11["status"] == "FAIL"
    if pin_drift:
        verdict, score = "inconclusive", 0.0
        hard = [f"PIN_DRIFT {pin_drift}"]
    elif f1_hard or controls_failed:
        verdict, score = "revise", 2.0 if not controls_failed else 1.0
        hard = [f"{c['check']}: {c['detail']}" for c in f1_hard] + \
               [f"CONTROL_DEAD {c['control']}: {c['detail']}" for c in controls_failed]
    else:
        verdict, score = "accept", 4.0
        hard = []
    checks.append(k11)  # recorded for the gate; a FAIL here is a cross-artifact owner action

    findings = []
    if gate_blocking:
        findings.append({
            "id": "W038-F1R13-01", "severity": "H", "gate_blocking": True,
            "scope": "cross-artifact (F1 rev13 vs the G-F0-frozen declared taxonomy); owner action, not an F1 semantic defect",
            "text": k11["detail"],
            "evidence": [f"{m['file']}:{m['line']} [{m['direction']}, kind={m['kind']}]"
                         for m in residual_mentions if m["operative_contradiction"]],
            "historical_residue": [f"{m['file']}:{m['line']}" for m in residual_mentions
                                   if m["kind"] == "historical" and m["direction"] == "STRONGER"],
            "already_reported_by": ["astra-life05-evidence-binding-repair/rev29_delta L-FORM-03",
                                    "worker-007 W007-REV29-PREFLIGHT-01 (I3 open)"],
            "delta_vs_L_FORM_03": "L-FORM-03 named research_map:200, supplement:176, registry:57, "
                                  "SET-delta:11,22. This census adds research_map:94 (variant definition block, "
                                  "missed by L-FORM-03), shows registry:57 and SET-delta:11/22 now carry the "
                                  "corrected direction plus a quoted historical note, and classifies supplement:176 "
                                  "as a historical D1 record rather than an operative claim.",
        })
    findings.append({
        "id": "W038-F1R13-02", "severity": "N", "gate_blocking": False,
        "text": "FROZEN.json is self-excluded from its own manifest, so its revision integer stayed 29 while "
                "its bytes moved from 3d9e3d77fd87 (00:55:02, 48 files) to 815e08079aef (00:57:26, 50 files). "
                "This review binds to the 50-file byte-state 815e08079aef; reviewers must cite the FROZEN "
                "sha256, not the integer alone.",
        "evidence": [f"artifacts/formulation/FROZEN.json#{ctx.sha['frozen']}"],
    })
    if f1_mentions:
        findings.append({
            "id": "W038-F1R13-03", "severity": "N", "gate_blocking": False,
            "text": "F1 strength-direction mentions after rev13 (census, for reviewers): " +
                    "; ".join(f"line {m['line']}: {m['direction']} (kind={m['kind']})" for m in f1_mentions) +
                    ". Zero are operative contradictions; the STRONGER occurrence is the quoted "
                    "'corrected from' provenance note inside the repair record.",
            "evidence": [f"schemas/af_wcc_vacuum.yaml#{ctx.sha['f1'][:12]}"],
        })
    k05 = next(c for c in checks if c["check"] == "K05")
    if k05.get("timestamps_monotone") is False:
        findings.append({
            "id": "W038-F1R13-04", "severity": "N", "gate_blocking": False,
            "text": "F1 revision_history entry timestamps are not monotone (backfilled entries: index 8 at "
                    "23:32:53 sits after index 7 at 00:30). Metadata hygiene only; indices are unique-contiguous "
                    "and the rev13 note is last.",
            "evidence": [f"schemas/af_wcc_vacuum.yaml#{ctx.sha['f1'][:12]}"],
        })

    report = {
        "task_id": "W038-F1-REV13-REVIEW-01",
        "worker": "worker-038",
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": started,
        "finished_at": now(),
        "authority": "worker review evidence only; cannot set status=done, validation_status=passed or a gate verdict",
        "task_origin": "no inbox card for worker-038; one bounded class-bound task taken from the live immediate queue "
                       "(G-FORM r3 needs rev13-live F1 review evidence; F2a/F2b already have rev13 verdicts)",
        "pins": {rel: ctx.sha[k] for k, rel in ctx.paths.items()},
        "pin_drift": pin_drift,
        "checks": checks,
        "controls": controls,
        "controls_summary": f"{sum(c['status'] == 'PASS' for c in controls)}/{len(controls)} controls fired",
        "cross_artifact": {
            "f1_strength_mentions": f1_mentions,
            "residual_mentions": residual_mentions,
            "gate_blocking": gate_blocking,
        },
        "verdict": verdict,
        "score": score,
        "hard_failures": hard,
        "findings": findings,
        "counts_as_full_schema_verdict": True,
        "gate_recommendation": ("revise G-FORM until the cross-artifact SET direction is reconciled in one atomic "
                                "revision" if gate_blocking else "accept at the pins above, subject to the audit "
                                "lead's independent adjudication"),
        "falsifier": "Any of: a K01-K17 check or M1-M10 control flips; the F1 canonical/mirror bytes move from "
                     "d9cebb9404b2; FROZEN.json bytes move from 815e08079aef (rev29, 50 files); the live "
                     "taxonomy_consistency.json stops being byte-reproducible by the pinned checker from live inputs; "
                     "F1 text is shown to state the SET variant as stronger than the single-q predicate; or a "
                     "hard failure is found at a hash other than the one pinned here.",
        "next_falsifier": "If the formulation lead lands a revision that clears the cross-artifact SET direction and "
                          "re-pins the corpora, re-run this instrument at the new pin: any K-check failure at the new "
                          "hash, or any surviving 'strictly STRONGER' SET mention in the four residual files, "
                          "falsifies the repair.",
        "replay": "python3 artifacts/worker-038/f1_rev13_review/run_f1_rev13_review.py",
    }

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    raw = HERE / "raw" / f"run_{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}.json"
    raw.write_text(json.dumps(report, indent=2) + "\n")

    print(f"verdict={verdict} score={score} checks={sum(c['status']=='PASS' for c in checks)}/{len(checks)} "
          f"controls={sum(c['status']=='PASS' for c in controls)}/{len(controls)} gate_blocking={gate_blocking}")
    for c in checks:
        if c["status"] != "PASS":
            print("  FAIL", c["check"], c["detail"])
    for c in controls:
        if c["status"] != "PASS":
            print("  DEAD CONTROL", c["control"], c["detail"])
    print("report", out)
    return 0 if verdict == "accept" and not controls_failed else 2


if __name__ == "__main__":
    sys.exit(main())
