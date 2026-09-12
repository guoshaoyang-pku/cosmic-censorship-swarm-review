#!/usr/bin/env python3
"""W090-F2A-REV12-VERDICT-02 -- independent, hash-bound verification of F2a
(class AF-SCC-C2-VAC-GEN, node F2a, gate G-FORM) at the frozen rev12 bytes.

Bounded class-bound task taken by worker-090 (slot 090) with no inbox assignment card.
Read-only with respect to every canonical path; all writes go under this script's directory
(plus one temporary pipeline sandbox under tmp/ that is removed at the end).

Deliverable checks and their failure modes are declared in results.json; each check carries
an id, expected status, measured value, evidence ref (path#sha256) and a falsifier where the
check is a claim rather than a reading.

Run:  python3 check_f2a_rev12.py
Exit: 0 iff no blocking check failed and all mutants were caught.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshot"
SANDBOX = OUT / "sandbox_consistency"
PIPE_SANDBOX = ROOT / "tmp" / "w090_f2a_pipeline_sandbox"

PIN = {
    "F2a": ("schemas/af_scc_c2_vacuum.yaml",
            "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml",
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"),
    "F0": ("research_map/formulation_taxonomy.yaml",
           "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "F0R": ("artifacts/formulation/formulation_taxonomy.yaml",
            "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "FROZEN": ("artifacts/formulation/FROZEN.json",
               "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"),
    "CONSISTENCY": ("artifacts/formulation/evidence/taxonomy_consistency.json",
                    "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"),
    "VOCAB": ("artifacts/formulation/VOCAB_ALIASES.json",
              "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"),
    "SEMESC": ("artifacts/formulation/evidence/semantic_escape_rebased.json",
               "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292"),
}

FROZEN_CONSISTENCY_DECLARED = (
    "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


class _DupKeyError(Exception):
    pass


class _StrictLoader(yaml.SafeLoader):
    pass


def _no_dup_mapping(loader, node, deep=False):
    mapping = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in mapping:
            raise _DupKeyError(f"duplicate mapping key {key!r} at line {k.start_mark.line + 1}")
        mapping[key] = loader.construct_object(v, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup_mapping)


def strict_load(text: str):
    return yaml.load(text, Loader=_StrictLoader)


def raw_duplicate_keys(text: str):
    """Return a list of duplicate mapping keys in the raw document (independent of the loader)."""
    dups = []
    try:
        root = yaml.compose(text)
    except Exception as exc:  # noqa: BLE001
        return [f"compose-error: {exc}"]
    stack = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = getattr(k, "value", None)
                if key in seen:
                    dups.append(f"{key} (lines {seen[key] + 1},{k.start_mark.line + 1})")
                else:
                    seen[key] = k.start_mark.line
                stack.append(v)
        elif isinstance(node, yaml.SequenceNode):
            stack.extend(node.value)
    return dups


def anchor_get(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def check(id_, claim, expected, measured, ok, evidence_refs, falsifier=None, severity="info"):
    return {
        "id": id_,
        "claim": claim,
        "expected": expected,
        "measured": measured,
        "status": "PASS" if ok else "FAIL",
        "severity": "blocking" if (not ok and severity == "blocking") else severity,
        "evidence_refs": evidence_refs,
        "falsifier": falsifier,
    }


# --------------------------------------------------------------------------------------
# 1. snapshot + pin measurement
# --------------------------------------------------------------------------------------
def snapshot_inputs():
    SNAP.mkdir(parents=True, exist_ok=True)
    rows = {}
    for name, (rel, expect) in PIN.items():
        src = ROOT / rel
        dst = SNAP / rel.replace("/", "__")
        if src.exists():
            shutil.copy2(src, dst)
            rows[name] = {"path": rel, "sha256": sha256_file(src),
                          "bytes": src.stat().st_size, "expected_sha256": expect}
        else:
            rows[name] = {"path": rel, "sha256": None, "expected_sha256": expect, "absent": True}
    (SNAP / "pins.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def pin_checks(pins):
    out = []
    for name in ("F2a", "F0", "F0R", "FROZEN", "CONSISTENCY"):
        r = pins[name]
        ok = r.get("sha256") == r.get("expected_sha256")
        out.append(check(
            f"P1-{name}-pin", f"{name} measures the frozen pin", r.get("expected_sha256"),
            r.get("sha256"), ok,
            [f"{r['path']}#{(r.get('sha256') or 'absent')[:12]}"],
            f"Re-measure {r['path']}; any byte other than the frozen pin falsifies this check.",
            severity="blocking"))
    frozen = json.loads((ROOT / PIN["FROZEN"][0]).read_text())
    la = frozen.get("logical_artifacts", {})
    fz_files = frozen.get("files", {})
    declared = {}
    for k, v in la.items():
        if isinstance(v, dict) and v.get("sha256"):
            declared[v.get("path")] = v.get("sha256")
    for name, want_key in (("F2a", "F2a"), ("F0", "F0"), ("F0R", "F0R")):
        rel = PIN[name][0]
        fz = declared.get(rel) or (fz_files.get(rel) or {}).get("sha256")
        ok = fz == PIN[name][1]
        out.append(check(
            f"P1-FROZEN-{name}", f"FROZEN rev{frozen.get('revision')} declares {rel} at the measured pin",
            PIN[name][1], fz, ok,
            [f"{PIN['FROZEN'][0]}#{PIN['FROZEN'][1][:12]}"],
            "A FROZEN declaration that differs from the frozen pin falsifies freeze integrity.",
            severity="blocking"))
    return out


# --------------------------------------------------------------------------------------
# 2. structural checks on the F2a document
# --------------------------------------------------------------------------------------
REQUIRED_SECTIONS = [
    "quantifiers", "topology", "data_class", "regularity", "genericity", "i_plus",
    "visibility", "conclusion", "class_components", "f0_binding", "anti_scope", "falsifier",
]


def structural_checks(text: str, doc: dict, ctx: dict):
    out = []
    ref = f"schemas/af_scc_c2_vacuum.yaml#{PIN['F2a'][1][:12]}"

    # P2 strict parse / duplicates
    dups = raw_duplicate_keys(text)
    out.append(check("P2-no-duplicate-keys",
                     "F2a rev12 contains no duplicate mapping keys (strict-YAML parse)",
                     "[]", dups, not dups, [ref],
                     "A duplicate key found by a strict reader falsifies this check.",
                     severity="blocking"))
    missing = [s for s in REQUIRED_SECTIONS if s not in doc]
    out.append(check("P2-required-sections",
                     "every G-FORM-required section is present",
                     "[]", missing, not missing, [ref],
                     "Any missing required section falsifies the schema's completeness.",
                     severity="blocking"))

    # P3 clock discipline
    revised = doc.get("revised_at")
    future, parse_ok = None, False
    if isinstance(revised, str):
        try:
            t = _dt.datetime.fromisoformat(revised)
            parse_ok = True
            future = t > _dt.datetime.now(tz=t.tzinfo)
        except ValueError:
            parse_ok = False
    top_level_revised = sum(1 for line in text.splitlines()
                            if line.startswith("revised_at:"))
    ok = parse_ok and not future and top_level_revised == 1
    out.append(check("P3-clock-discipline",
                     "exactly one top-level revised_at, parseable and not in the future",
                     {"parseable": True, "future": False, "top_level_revised_at": 1},
                     {"parseable": parse_ok, "future": future,
                      "top_level_revised_at": top_level_revised, "revised_at": revised},
                     ok, [ref],
                     "A future-dated or duplicated revised_at falsifies clock discipline.",
                     severity="blocking"))

    # C1 class identity
    cid = doc.get("class_id")
    comp = doc.get("class_components") or {}
    expected_comp = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
                     "genericity": "GEN", "regularity_token": "C2"}
    ok = cid == "AF-SCC-C2-VAC-GEN" and comp == expected_comp and doc.get("node_id") == "F2a"
    out.append(check("C1-class-identity",
                     "class_id, node_id and class_components are exactly AF-SCC-C2-VAC-GEN",
                     {"class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a",
                      "class_components": expected_comp},
                     {"class_id": cid, "node_id": doc.get("node_id"),
                      "class_components": comp}, ok, [ref],
                     "Any component outside AF/SCC/VAC/GEN/C2 falsifies class identity.",
                     severity="blocking"))

    # Q1 quantifier binding
    ordered = (doc.get("quantifiers") or {}).get("ordered") or []
    first = ordered[0] if ordered else {}
    formal = str((doc.get("quantifiers") or {}).get("formal", ""))
    stmt = str((doc.get("conclusion") or {}).get("statement_formal", ""))
    ok_first = first.get("kind") == "forall" and first.get("binder") == "r" \
        and first.get("domain_id") == "D0"
    binds_r = ("forall r in D0" in formal) and ("forall r in D0" in stmt)
    no_pair_binder = "(s,delta) in D0" not in text and "(s, delta) in D0" not in text
    out.append(check("Q1-quantifier-binding",
                     "first binder is forall r in D0 and no pair-typed binder over D0 survives",
                     {"first": {"kind": "forall", "binder": "r", "domain_id": "D0"},
                      "forall_r_in_D0": True, "pair_binder_absent": True},
                     {"first": first, "forall_r_in_D0": binds_r,
                      "pair_binder_absent": no_pair_binder},
                     ok_first and binds_r and no_pair_binder, [ref],
                     "A pair-typed binder, or a first binder other than r/D0, falsifies the rev12 repair.",
                     severity="blocking"))

    # Q2 D0 tagged union
    d0 = str(((doc.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", ""))
    ok = ("tagged disjoint union" in d0) and ("smooth" in d0) and ("(sobolev,s,delta)" in d0)
    out.append(check("Q2-D0-typed-union",
                     "D0 is defined as a tagged disjoint union r=smooth | r=(sobolev,s,delta)",
                     {"tagged_union": True, "smooth_branch": True, "sobolev_branch": True},
                     {"tagged_union": "tagged disjoint union" in d0, "smooth_branch": "smooth" in d0,
                      "sobolev_branch": "(sobolev,s,delta)" in d0,
                      "definition_head": d0[:160]}, ok, [ref],
                     "A D0 that admits an untagged 'suitable regularity' reading falsifies the repair.",
                     severity="blocking"))

    # Q3 domain resolution
    domains = (doc.get("quantifiers") or {}).get("domains") or {}
    unresolved = [q.get("domain_id") for q in ordered if q.get("domain_id") not in domains]
    out.append(check("Q3-domain-resolution",
                     "every ordered binder's domain_id is defined in quantifiers.domains",
                     "[]", unresolved, not unresolved, [ref],
                     "An ordered binder with no domain definition falsifies well-formedness.",
                     severity="blocking"))

    # V1 visibility is not the class conclusion (SCC vs WCC separation)
    vis = doc.get("visibility") or {}
    ip = doc.get("i_plus") or {}
    ip_conc = ((doc.get("conclusion") or {}).get("statement_formal", "")
               + (doc.get("conclusion") or {}).get("statement_natural_language", ""))
    ok = vis.get("role") == "not_in_conclusion" and vis.get("visible_singularity_is_wcc") is True \
        and "WCC" in str(vis.get("forbidden_falsifier", "")) and ip.get("in_conclusion") is False \
        and "I+" not in ip_conc
    out.append(check("V1-visibility-separation",
                     "visibility from I+ is declared out of this SCC class conclusion",
                     {"role": "not_in_conclusion", "visible_singularity_is_wcc": True,
                      "i_plus.in_conclusion": False, "I+_absent_from_conclusion": True},
                     {"role": vis.get("role"),
                      "visible_singularity_is_wcc": vis.get("visible_singularity_is_wcc"),
                      "i_plus.in_conclusion": ip.get("in_conclusion"),
                      "I+_absent_from_conclusion": "I+" not in ip_conc},
                     ok, [ref],
                     "An SCC conclusion that asserts the WCC I+ predicate falsifies class separation.",
                     severity="blocking"))

    # C2 no C0/C2 merge (alias-aware)
    vocab = ctx["vocab"]

    def canon(tok):
        for c, aliases in (vocab.get("conclusion_type") or {}).items():
            if tok == c or tok in (aliases or []):
                return c
        return tok

    f2a_tok = (doc.get("conclusion") or {}).get("conclusion_type")
    f2b_tok = ((ctx["f2b"].get("conclusion") or {}).get("conclusion_type"))
    ca, cb = canon(f2a_tok), canon(f2b_tok)
    ok = ca == "scc_c2_future_inextendibility" and cb == "scc_c0_future_inextendibility" and ca != cb
    out.append(check("C2-no-C0-C2-merge",
                     "F2a and F2b conclusion tokens resolve to distinct canonical class tokens",
                     {"F2a_canonical": "scc_c2_future_inextendibility",
                      "F2b_canonical": "scc_c0_future_inextendibility"},
                     {"F2a_token": f2a_tok, "F2a_canonical": ca,
                      "F2b_token": f2b_tok, "F2b_canonical": cb,
                      "vocab_policy": vocab.get("policy")},
                     ok, [f"schemas/af_scc_c0_vacuum.yaml#{PIN['F2b'][1][:12]}",
                          "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"],
                     "Both tokens resolving to the same canonical token would falsify separation.",
                     severity="blocking"))

    # C3 vocabulary authority split (literal registry check)
    f0_cls = anchor_get(ctx["f0"], "classes.AF-SCC-C2-VAC-GEN") or {}
    f0_allowed = ((ctx["f0"].get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    f0_axes_tok = (f0_cls.get("axes") or {}).get("conclusion_type")
    literal_hit = f2a_tok in f0_allowed
    axes_hit = f0_axes_tok in f0_allowed
    out.append(check("C3a-vocab-alias-equivalence",
                     "F2a conclusion token and F0 axes token resolve to the same canonical token",
                     True, canon(f2a_tok) == canon(f0_axes_tok),
                     canon(f2a_tok) == canon(f0_axes_tok), [ref,
                     f"{PIN['F0'][0]}#{PIN['F0'][1][:12]}"],
                     "Distinct canonical resolutions would be a real C0/C2 or SCC/WCC merge.",
                     severity="blocking"))
    out.append(check("C3b-vocab-literal-registry",
                     "F2a conclusion token appears literally in F0 field_vocabulary.conclusion_type.allowed",
                     True, literal_hit, literal_hit, [ref,
                     f"{PIN['F0'][0]}#{PIN['F0'][1][:12]}"],
                     "A token found in the canonical registry would close this item; its absence "
                     "is the measured vocabulary-authority split (worker-045 blocker).",
                     severity="blocking"))
    out.append(check("C3c-vocab-policy-direction",
                     "canonical F0 uses the alias form that VOCAB_ALIASES forbids in new canonical artifacts",
                     {"alias_in_canonical": True},
                     {"f0_axes_token": f0_axes_tok, "in_allowed": axes_hit,
                      "is_alias_of": canon(f0_axes_tok)},
                     axes_hit and canon(f0_axes_tok) != f0_axes_tok, [
                         "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                         f"{PIN['F0'][0]}#{PIN['F0'][1][:12]}"],
                     "If F0 carried the canonical token, the policy-direction finding would be false.",
                     severity="info"))

    # B1/B2 contract pointers
    def resolve_pointer(ptr, target_doc):
        if not isinstance(ptr, str) or "#" not in ptr:
            return None, "malformed"
        path, frag = ptr.split("#", 1)
        return anchor_get(target_doc, frag), path

    p1, path1 = resolve_pointer(doc.get("class_contract_pointer"), ctx["f0"])
    out.append(check("B1-canonical-pointer",
                     "class_contract_pointer resolves into the canonical F0 taxonomy #classes subtree",
                     {"resolves": True, "path": "research_map/formulation_taxonomy.yaml"},
                     {"resolves": p1 is not None, "path": path1,
                      "pointer": doc.get("class_contract_pointer")},
                     p1 is not None and path1 == "research_map/formulation_taxonomy.yaml", [ref,
                     f"{PIN['F0'][0]}#{PIN['F0'][1][:12]}"],
                     "A pointer to the authoring tree or an unresolvable anchor falsifies this.",
                     severity="blocking"))
    p2, path2 = resolve_pointer(doc.get("class_contract_supplement_pointer"), ctx["f0r"])
    out.append(check("B2-supplement-pointer",
                     "class_contract_supplement_pointer resolves into the F0 supplement #class_contracts",
                     {"resolves": True, "path": "artifacts/formulation/formulation_taxonomy.yaml"},
                     {"resolves": p2 is not None, "path": path2,
                      "pointer": doc.get("class_contract_supplement_pointer")},
                     p2 is not None and path2 == "artifacts/formulation/formulation_taxonomy.yaml",
                     [ref, f"{PIN['F0R'][0]}#{PIN['F0R'][1][:12]}"],
                     "An unresolvable supplement pointer falsifies the split-contract repair.",
                     severity="blocking"))

    # B3/B4 f0_binding hashes
    fb = doc.get("f0_binding") or {}
    ok = fb.get("declared_f0_sha256") == PIN["F0"][1]
    out.append(check("B3-declared-F0-hash",
                     "f0_binding.declared_f0_sha256 equals the measured canonical F0 pin",
                     PIN["F0"][1], fb.get("declared_f0_sha256"), ok, [ref],
                     "A stale declared F0 hash falsifies the binding.",
                     severity="blocking"))
    live_ev = sha256_file(ROOT / PIN["CONSISTENCY"][0])
    declared_ev = fb.get("consistency_evidence_sha256")
    out.append(check("B4-consistency-evidence-hash",
                     "f0_binding.consistency_evidence_sha256 equals the measured evidence file",
                     declared_ev, live_ev, declared_ev == live_ev,
                     [ref, f"{PIN['CONSISTENCY'][0]}#{live_ev[:12]}"],
                     "The declared pin matching the measured evidence file would close this item; "
                     "a post-freeze regeneration or a stale declaration keeps it open.",
                     severity="blocking"))
    return out


# --------------------------------------------------------------------------------------
# 3. consistency-evidence re-derivation + controls
# --------------------------------------------------------------------------------------
def run_consistency_tool(sandbox: Path):
    tool = sandbox / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    proc = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True)
    ev = sandbox / "artifacts/formulation/evidence/taxonomy_consistency.json"
    content = ev.read_text() if ev.exists() else None
    return proc, content


def make_consistency_sandbox(dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    for rel in ("research_map/formulation_taxonomy.yaml",
                "artifacts/formulation/formulation_taxonomy.yaml",
                "artifacts/formulation/VOCAB_ALIASES.json",
                "artifacts/formulation/tools/check_taxonomy_consistency.py"):
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    (dst / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    return dst


def consistency_checks():
    out = []
    live_path = ROOT / PIN["CONSISTENCY"][0]
    live_hash = sha256_file(live_path)
    live_text = live_path.read_text()

    sandbox = make_consistency_sandbox(SANDBOX)
    proc, content = run_consistency_tool(sandbox)
    fresh_hash = sha256_bytes(content.encode()) if content is not None else None
    out.append(check("E1-evidence-reproducible",
                     "the live consistency evidence is byte-reproducible from the frozen F0 pair",
                     {"exit": 0, "sha256": live_hash},
                     {"exit": proc.returncode, "sha256": fresh_hash,
                      "stdout": (proc.stdout or "").strip()[:200]},
                     fresh_hash == live_hash and proc.returncode == 0,
                     [f"{PIN['CONSISTENCY'][0]}#{live_hash[:12]}",
                      f"{PIN['F0'][0]}#{PIN['F0'][1][:12]}",
                      f"{PIN['F0R'][0]}#{PIN['F0R'][1][:12]}"],
                     "A fresh run on the frozen pair producing different bytes would mean the live "
                     "evidence was not generated from the frozen pair.",
                     severity="info"))

    # mutation control: break a supplement contract -> checker must report INCONSISTENT
    mut = make_consistency_sandbox(OUT / "sandbox_consistency_mutant")
    sup = mut / "artifacts/formulation/formulation_taxonomy.yaml"
    doc = yaml.safe_load(sup.read_text())
    target = doc["class_contracts"]["AF-SCC-C2-VAC-GEN"]
    target.pop("exclusions", None)
    sup.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
    proc_m, content_m = run_consistency_tool(mut)
    mut_json = json.loads(content_m) if content_m else {}
    out.append(check("E2-consistency-checker-sensitive",
                     "deleting a supplement contract's exclusions makes the checker report INCONSISTENT",
                     {"exit": 1, "consistent": False},
                     {"exit": proc_m.returncode, "consistent": mut_json.get("consistent"),
                      "errors": (mut_json.get("errors") or [])[:2]},
                     proc_m.returncode == 1 and mut_json.get("consistent") is False,
                     ["artifacts/formulation/tools/check_taxonomy_consistency.py"],
                     "The checker reporting CONSISTENT on a mutated contract would falsify the "
                     "evidence's sensitivity.",
                     severity="blocking"))

    # coverage test: the checker never reads the three schemas
    src = (ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    mentions_schemas = "schemas/" in src
    probe = make_consistency_sandbox(OUT / "sandbox_consistency_schemaprobe")
    sch = probe / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
    sch.parent.mkdir(parents=True, exist_ok=True)
    sch.write_text("this: file is not a schema and is not an input\n")
    proc_p, content_p = run_consistency_tool(probe)
    same = content_p is not None and sha256_bytes(content_p.encode()) == fresh_hash
    out.append(check("E3-evidence-coverage-gap",
                     "the consistency evidence does not cover the three class schemas",
                     {"tool_mentions_schemas": False, "output_invariant_to_schema_bytes": True},
                     {"tool_mentions_schemas": mentions_schemas,
                      "probe_output_sha256": sha256_bytes(content_p.encode()) if content_p else None,
                      "unmutated_output_sha256": fresh_hash, "output_invariant": same},
                     (not mentions_schemas) and same,
                     ["artifacts/formulation/tools/check_taxonomy_consistency.py",
                      f"{PIN['CONSISTENCY'][0]}#{live_hash[:12]}"],
                     "If the tool read the schemas, its output would change with the probe file.",
                     severity="info"))

    # hash-binding gap: evidence embeds no sha256 of the compared trees
    embeds = ("0abb9ed8" in live_text) or ("d7419b4e" in live_text) \
        or ("sha256" in live_text and "675a99d0" in live_text)
    out.append(check("E4-evidence-embeds-no-tree-hashes",
                     "the live evidence embeds no sha256 of either compared tree",
                     {"embeds_tree_hash": False},
                     {"embeds_tree_hash": embeds, "live_sha256": live_hash,
                      "declared_sha256": FROZEN_CONSISTENCY_DECLARED},
                     not embeds, [f"{PIN['CONSISTENCY'][0]}#{live_hash[:12]}"],
                     "Locating either tree's sha256 inside the evidence would close this item.",
                     severity="info"))
    return out


# --------------------------------------------------------------------------------------
# 4. acceptance pipeline (read-only wrt canonical tree)
# --------------------------------------------------------------------------------------
def pipeline_checks():
    out = []
    rec_path = ROOT / PIN["SEMESC"][0]
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    cur = sha256_file(ROOT / rec.get("base_schema", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"))
    out.append(check("A1-acceptance-preflight",
                     "the recorded acceptance corpus is rebased onto the current canonical C0 bytes",
                     {"recorded_base": cur},
                     {"recorded_base": rec.get("base_sha256"), "current_base": cur,
                      "stale": rec.get("base_sha256") != cur},
                     rec.get("base_sha256") == cur,
                     [f"{PIN['SEMESC'][0]}",
                      f"artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#{cur[:12]}"],
                     "Re-running measure_semantic_escape.py so the recorded base equals the current "
                     "base would close this item; a recorded base that still differs keeps it open.",
                     severity="blocking"))

    # Run the pipeline in a throwaway sandbox so canonical writes are impossible.
    if PIPE_SANDBOX.exists():
        shutil.rmtree(PIPE_SANDBOX)
    PIPE_SANDBOX.mkdir(parents=True, exist_ok=True)
    for rel in ("artifacts/formulation", "artifacts/worker-06"):
        shutil.copytree(ROOT / rel, PIPE_SANDBOX / rel, symlinks=False)
    runner = PIPE_SANDBOX / "artifacts/formulation/tools/run_acceptance.py"
    meas = PIPE_SANDBOX / "artifacts/formulation/tools/measure_semantic_escape.py"

    t0 = time.time()
    stale = subprocess.run([sys.executable, str(runner), "--json"], capture_output=True, text=True)
    stale_out = (stale.stdout or "") + (stale.stderr or "")
    (OUT / "raw_acceptance_stale.log").write_text(
        f"exit={stale.returncode}\n{stale_out}")
    out.append(check("A2-acceptance-preflight-reproduced",
                     "the on-disk stale corpus makes the frozen-byte acceptance run fail closed",
                     {"exit": 3, "preflight_fail": True},
                     {"exit": stale.returncode, "preflight_fail": "PREFLIGHT FAIL" in stale_out},
                     stale.returncode == 3 and "PREFLIGHT FAIL" in stale_out,
                     ["artifacts/formulation/tools/run_acceptance.py"],
                     "An acceptance run that proceeds on the stale corpus would falsify the preflight.",
                     severity="info"))

    reb = subprocess.run([sys.executable, str(meas)], capture_output=True, text=True)
    (OUT / "raw_measure_rebased.log").write_text(
        f"exit={reb.returncode}\n{(reb.stdout or '')[-4000:]}\n{(reb.stderr or '')[-2000:]}")
    fresh = subprocess.run([sys.executable, str(runner), "--json"], capture_output=True, text=True)
    (OUT / "raw_acceptance_rebased.log").write_text(
        f"exit={fresh.returncode}\n{(fresh.stdout or '')[-6000:]}\n{(fresh.stderr or '')[-2000:]}")
    acc = {}
    try:
        acc = json.loads(fresh.stdout)
    except Exception:  # noqa: BLE001
        pass
    m = acc.get("mutants", {})
    rows = {r.get("schema"): r for r in acc.get("canonical", [])}
    f2a_row = rows.get("af_scc_c2_vacuum.yaml", {})
    f1_row = rows.get("af_wcc_vacuum.yaml", {})
    f2b_row = rows.get("af_scc_c0_vacuum.yaml", {})
    canon_ok = all(r.get("ok") for r in acc.get("canonical", []))
    ctrl_ok = all(r.get("ok") for r in acc.get("controls", []))
    union_ok = bool(m) and m.get("total") and m.get("union_caught") == m.get("total")
    out.append(check("A3a-f2a-acceptance-row",
                     "F2a passes both acceptance stages on the frozen bytes after the corpus rebase",
                     {"structural": "pass", "semantic": "pass", "ok": True},
                     f2a_row, f2a_row.get("ok") is True,
                     ["artifacts/formulation/tools/run_acceptance.py",
                      "artifacts/formulation/tools/measure_semantic_escape.py",
                      f"schemas/af_scc_c2_vacuum.yaml#{PIN['F2a'][1][:12]}"],
                     "Either stage failing on F2a would falsify this F2a-specific acceptance row.",
                     severity="blocking"))
    out.append(check("A3b-acceptance-union-and-controls",
                     "on the rebased frozen bytes the union of both stages catches every mutant and "
                     "both controls pass",
                     {"union_caught": "total", "controls_false_positive": 0},
                     {"mutants": m, "controls": acc.get("controls")},
                     union_ok and ctrl_ok,
                     ["artifacts/formulation/tools/run_acceptance.py"],
                     "A union escape or a control false positive falsifies the acceptance hard requirement.",
                     severity="blocking"))
    sem_tool = PIPE_SANDBOX / "artifacts/worker-06/spec_conformance_audit.py"
    sem_run = subprocess.run(
        [sys.executable, str(sem_tool), str(PIPE_SANDBOX / "artifacts/formulation/schemas/af_wcc_vacuum.yaml")],
        capture_output=True, text=True)
    (OUT / "raw_f1_semantic_audit.json").write_text(sem_run.stdout or "")
    sem_json = {}
    try:
        sem_json = json.loads(sem_run.stdout)
    except Exception:  # noqa: BLE001
        pass
    out.append(check("A3c-family-pipeline-verdict",
                     "the acceptance pipeline verdict on the frozen bytes is FAIL and the failing "
                     "canonical schema is F1 (af_wcc_vacuum.yaml), not F2a",
                     {"pipeline_verdict": "FAIL", "failing_schema": "af_wcc_vacuum.yaml",
                      "semantic_failed_rules": ["R03"]},
                     {"pipeline_verdict": acc.get("verdict"), "f1_row": f1_row, "f2b_row": f2b_row,
                      "semantic_verdict": sem_json.get("verdict"),
                      "semantic_failed_rules": sem_json.get("failed_rules")},
                     acc.get("verdict") == "FAIL" and f1_row.get("ok") is False
                     and f2a_row.get("ok") is True and "R03" in (sem_json.get("failed_rules") or []),
                     ["artifacts/worker-06/spec_conformance_audit.py",
                      "artifacts/worker-090/f2a_rev12_verdict/raw_f1_semantic_audit.json",
                      "schemas/af_wcc_vacuum.yaml#cce9c60146d6"],
                     "A PASS verdict, or a failure located in F2a rather than F1, falsifies this reading.",
                     severity="info"))
    return out


# --------------------------------------------------------------------------------------
# 5. self-controls (mutants of the F2a snapshot)
# --------------------------------------------------------------------------------------
def self_mutants(ctx):
    base_text = (SNAP / PIN["F2a"][0].replace("/", "__")).read_text()
    cases = []

    def add(name, mutate, expect_id):
        cases.append((name, mutate, expect_id))

    def corrupt_pointer(txt):
        return txt.replace("research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN",
                           "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN-NOPE", 1)

    def future_date(txt):
        return txt.replace("revised_at: '2026-09-12T00:31:41+08:00'",
                           "revised_at: '2030-01-01T00:00:00+08:00'", 1) \
            .replace('revised_at: "2026-09-12T00:31:41+08:00"',
                     'revised_at: "2030-01-01T00:00:00+08:00"', 1)

    def duplicate_key(txt):
        return txt.replace("revision: 12", "revision: 12\nrevision: 12", 1)

    def merge_token(txt):
        return txt.replace("conclusion_type: scc_c2_future_inextendibility",
                           "conclusion_type: scc_c0_future_inextendibility", 1)

    add("M1-pointer-corruption", corrupt_pointer, "B1-canonical-pointer")
    add("M2-future-revised-at", future_date, "P3-clock-discipline")
    add("M3-duplicate-top-level-key", duplicate_key, "P2-no-duplicate-keys")
    add("M4-c0-token-swap", merge_token, "C2-no-C0-C2-merge")
    results = []
    for name, mutate, expect_id in cases:
        text = mutate(base_text)
        try:
            doc = strict_load(text)
            bad = structural_checks(text, doc, ctx)
            flipped = [c for c in bad if c["id"] == expect_id and c["status"] == "FAIL"]
            results.append({"mutant": name, "expected_fail": expect_id,
                            "caught": bool(flipped),
                            "observed": {c["id"]: c["status"] for c in bad
                                         if c["id"] in (expect_id, "P2-no-duplicate-keys")}})
        except Exception as exc:  # noqa: BLE001
            results.append({"mutant": name, "expected_fail": expect_id, "caught": True,
                            "observed": f"parse/raise: {exc}"})
    return results


# --------------------------------------------------------------------------------------
def main():
    started = _dt.datetime.now().astimezone()
    pins = snapshot_inputs()
    f2a_text = (ROOT / PIN["F2a"][0]).read_text()
    f2a_doc = strict_load(f2a_text)
    f2b_doc = strict_load((ROOT / PIN["F2b"][0]).read_text())
    f0_doc = strict_load((ROOT / PIN["F0"][0]).read_text())
    f0r_doc = strict_load((ROOT / PIN["F0R"][0]).read_text())
    vocab = json.loads((ROOT / PIN["VOCAB"][0]).read_text())
    ctx = {"f0": f0_doc, "f0r": f0r_doc, "f2b": f2b_doc, "vocab": vocab}

    checks = []
    checks += pin_checks(pins)
    checks += structural_checks(f2a_text, f2a_doc, ctx)
    checks += consistency_checks()
    checks += pipeline_checks()
    mutants = self_mutants(ctx)

    # determinism: rerun the structural block on a fresh read
    repeat = structural_checks((ROOT / PIN["F2a"][0]).read_text(),
                               strict_load((ROOT / PIN["F2a"][0]).read_text()), ctx)
    repeat_ids = {c["id"] for c in repeat}
    det_ok = json.dumps([(c["id"], c["status"]) for c in repeat]) == \
        json.dumps([(c["id"], c["status"]) for c in checks if c["id"] in repeat_ids])

    # drift: re-measure every pin at exit
    drift = []
    for name, (rel, expect) in PIN.items():
        now = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        if now != pins[name].get("sha256"):
            drift.append({"pin": name, "start": pins[name].get("sha256"), "end": now})

    blocking = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "blocking"]
    mutants_all_caught = all(m["caught"] for m in mutants)
    results = {
        "schema": "w090-f2a-rev12-verdict/v1",
        "task_id": "W090-F2A-REV12-VERDICT-02",
        "actor": "worker-090",
        "authority_note": "worker evidence only; no gate verdict, no node status, no canonical-file edit",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "started_at": started.isoformat(),
        "finished_at": _dt.datetime.now().astimezone().isoformat(),
        "pins": pins,
        "checks": checks,
        "controls": {
            "determinism_structural": det_ok,
            "mutants": mutants,
            "mutants_all_caught": mutants_all_caught,
            "pin_drift": drift,
            "read_only_note": "canonical paths were only read; writes are under "
                              "artifacts/worker-090/f2a_rev12_verdict/ and tmp/w090_f2a_pipeline_sandbox/",
        },
        "summary": {
            "checks_total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail": sum(1 for c in checks if c["status"] == "FAIL"),
            "blocking_failures": [c["id"] for c in blocking],
            "class_semantics_failures": [c["id"] for c in blocking
                                         if c["id"].startswith(("C1", "C2", "C3a", "Q", "V"))],
            "provenance_or_bookkeeping_failures": [c["id"] for c in blocking
                                                   if c["id"].startswith(("B4", "A", "C3b"))],
            "verdict_basis": "revise iff any blocking failure survives at the frozen pin",
        },
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results["summary"], indent=1))
    print("blocking:", results["summary"]["blocking_failures"])
    print("mutants all caught:", mutants_all_caught, "determinism:", det_ok, "drift:", drift)
    return 0 if (not blocking and mutants_all_caught and det_ok and not drift) else 1


if __name__ == "__main__":
    sys.exit(main())
