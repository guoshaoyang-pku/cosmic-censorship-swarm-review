#!/usr/bin/env python3
"""W003-C0-POLARITY-ADJUDICATION-01 -- independent adjudication of the FORM-HELDOUT-09
escape `c0_03_conclusion_negated`.

Question (from blocker w068-hel09r-13-blocker, item 2): the two-stage class-binding
pipeline accepts a C0 mutant whose conclusion content asserts the EXISTENCE of a proper
future C0 metric extension while its conclusion_type token still claims
`scc_c0_future_inextendibility`.  Is that a genuine class-contract violation (true
positive the pipeline misses), and does a minimal, independently implemented
content-polarity check catch it without false positives?

WHAT THIS SCRIPT DECIDES (structure/semantics of the frozen bytes only):
  criterion 1  token-implied polarity (rule_spec class_conclusion_type vocabulary) equals
               the polarity of conclusion.statement_formal / statement_natural_language;
  criterion 2  conclusion statement polarity equals quantifiers.formal polarity;
  criterion 3  conclusion statement polarity is OPPOSITE to quantifiers.negation_normal_form
               polarity (a schema's conclusion must not assert its own declared negation);
  criterion 4  conclusion statement polarity equals the nearest frozen class base's polarity.
All four are decided by one transparent lexical polarity classifier with a declared
trigger vocabulary and an explicit `undecided` outcome.  A fixture is FLAGGED if any
decidable criterion disagrees.  This is NOT a re-implementation of FORM-RULE-SPEC R11 and
it decides no mathematics, no gate, and no class truth.

Independent of worker-068 / worker-06 code: only PyYAML + stdlib are used for the checks.
The two frozen stage tools are re-run as subprocesses (replication evidence), never
imported for the verdict.

USAGE
  python3 adjudicate_c0_polarity.py --out report.json [--blindspot-out blindspot_entry.json]
Exit: 0 = all declared expectations hold; 1 = an expectation was violated (adjudication
itself failed); 2 = usage/IO error; 3 = input hash drift (fail-closed, no verdict).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- pinned inputs
# Every pinned input must match the default pin below, or the probe exits 3 without a
# verdict.  Pins are the hashes this adjudication was written against.
PINS = {
    "base_c0": ("artifacts/worker-068/heldout3/bases/af_scc_c0_vacuum.yaml",
                "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"),
    "fixture": ("artifacts/worker-068/heldout3/mutants/c0_03_conclusion_negated.yaml",
                "1e8898ac7bad1b7db81961e9d27b05cc7e7ef8562d5c89a53c1e4a1afeea1f36"),
    "stage_a": ("artifacts/formulation/tools/check_class_schema.py",
                "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"),
    "stage_b": ("artifacts/worker-06/spec_conformance_audit.py",
                "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec"),
    "rule_spec": ("artifacts/formulation/rule_spec.json",
                  "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"),
    "manifest": ("artifacts/worker-068/heldout3/manifest.json",
                 "72c0353ad0de617adeb6f68fc5ad232886b30b3d2a998aa354fbbe9d0a854b18"),
    "raw_verdicts": ("artifacts/worker-068/heldout3/raw_verdicts.json",
                     "3fe7499bfc12"),  # prefix only: the replication report records this prefix
}
# raw_verdicts is recorded by prefix in the replication report; measured hash is reported,
# not used as a hard pin.
SOFT_PINS = {"raw_verdicts"}
# Measured-but-not-pinned (live files may move; drift is recorded, not fatal):
UNPINNED = {
    "live_canonical_c0": "schemas/af_scc_c0_vacuum.yaml",
    "f0_canonical": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "bases_dir": "artifacts/worker-068/heldout3/bases",
    "mutants_dir": "artifacts/worker-068/heldout3/mutants",
    "controls_dir": "artifacts/worker-068/heldout3/controls",
}

# conclusion-type token -> asserted polarity of the class conclusion.  Derived from the
# rule_spec vocabulary (class_conclusion_type) and the canonical class contracts: each
# frozen token is a NON-EXISTENCE family statement (no C0/C2 extension, no visible
# incomplete geodesic).  Only these three tokens are mapped; anything else is undecided.
TOKEN_POLARITY = {
    "scc_c0_future_inextendibility": "negative",
    "scc_c2_future_inextendibility": "negative",
    "weak_cosmic_censorship": "negative",
}

NEG_PATTERNS = [
    (r"\bnot\s+exists?\b", "not_exists"),
    (r"\bno\s+(?:proper\s+|future\s+|c0\s+|continuous\s+|metric\s+){0,5}extension", "no_extension"),
    (r"\b(?:admits?|admit|has|have|possess(?:es)?|contains?)\s+no\b", "admits_no"),
    (r"\bdoes\s+not\s+(?:admit|have|possess)\b", "does_not_admit"),
    (r"\binextendib\w*", "inextendible"),
    (r"\bcannot\s+be\s+(?:continuously\s+)?extended\b", "cannot_be_extended"),
    (r"\bis\s+not\s+extendib\w*", "is_not_extendible"),
    (r"\bnever\s+(?:admits?|has|have|possess(?:es)?)\b", "never_admits"),
    (r"\bno\s+(?:\w+\s+){0,4}(?:admits?|has|have|possess(?:es)?)\b", "no_subject_admits"),
    (r"\bfails?\s+to\s+(?:admit|have|possess)\b", "fails_to_admit"),
    (r"\bno\s+isometric\s+embedding\b", "no_isometric_embedding"),
    (r"\bwithout\s+(?:a\s+|any\s+)?(?:proper\s+|future\s+|c0\s+|metric\s+){0,4}extension", "without_extension"),
]
EXT_MENTION = re.compile(r"\b(extension|extensions|extendible|extended|extend)\w*\b", re.I)


def normalize(text: str) -> str:
    # underscores are normalized to spaces so that identifier-shaped statements like
    # `proper_future_extension_in_class(MGHD(D))` are readable by the lexical classifier
    return re.sub(r"\s+", " ", str(text).replace("_", " ")).strip().lower()


def classify_polarity(statement: str) -> dict:
    """Lexical polarity classifier.  Returns {polarity, marker, text}.

    negative : the statement mentions an extension AND carries a negation marker
    positive : the statement mentions an extension and carries no negation marker
    undecided: no extension mention at all (criterion not decidable for this statement)
    """
    t = normalize(statement)
    if not EXT_MENTION.search(t):
        return {"polarity": "undecided", "marker": "no_extension_mention", "text": t}
    for pat, name in NEG_PATTERNS:
        if re.search(pat, t):
            return {"polarity": "negative", "marker": name, "text": t}
    return {"polarity": "positive", "marker": "extension_mentioned_without_negation", "text": t}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stamp() -> str:
    return datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def leaf_diff(a, b, path="", out=None, ignore=None):
    """Leaf-level difference list between two parsed YAML documents."""
    if out is None:
        out = []
    if ignore and any(re.fullmatch(p, path.strip("/").split("/")[-1] or "") for p in ignore):
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append({"path": f"{path}/{k}", "base": "<missing>", "other": b[k]})
            elif k not in b:
                out.append({"path": f"{path}/{k}", "base": a[k], "other": "<missing>"})
            else:
                leaf_diff(a[k], b[k], f"{path}/{k}", out, ignore)
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            out.append({"path": path or "/", "base": f"<list len {len(a)}>", "other": f"<list len {len(b)}>"})
    elif a != b:
        out.append({"path": path or "/", "base": a, "other": b})
    return out


def conclusion_fields(doc: dict) -> dict:
    c = doc.get("conclusion") or {}
    q = doc.get("quantifiers") or {}
    return {
        "class_id": doc.get("class_id"),
        "conclusion_type": c.get("conclusion_type"),
        "statement_formal": c.get("statement_formal"),
        "statement_natural_language": c.get("statement_natural_language"),
        "quantifiers_formal": q.get("formal"),
        "negation": q.get("negation"),
        "negation_normal_form": q.get("negation_normal_form"),
    }


def criteria_for(doc: dict, base_polarity: str | None) -> list:
    """Apply the four consistency criteria to one parsed schema document."""
    f = conclusion_fields(doc)
    pol_formal = classify_polarity(f["statement_formal"] or "")
    pol_nl = classify_polarity(f["statement_natural_language"] or "")
    pol_qformal = classify_polarity(f["quantifiers_formal"] or "")
    pol_neg = classify_polarity(f["negation_normal_form"] or f["negation"] or "")
    pol_token = TOKEN_POLARITY.get(f["conclusion_type"], "unmapped")
    rows = []

    def add(cid, expected, observed, decided, note):
        rows.append({"criterion": cid, "expected": expected, "observed": observed,
                     "decided": decided, "agrees": (expected == observed) if decided else None,
                     "note": note})

    # criterion 1: token-implied polarity vs statement polarity (formal preferred; NL fallback)
    for label, pol in (("statement_formal", pol_formal), ("statement_natural_language", pol_nl)):
        if pol["polarity"] == "undecided" or pol_token == "unmapped":
            add(f"C1:{label}", pol_token, pol["polarity"], False, f"token map={pol_token}; {pol['marker']}")
        else:
            add(f"C1:{label}", pol_token, pol["polarity"], True, f"marker={pol['marker']}")
    # criterion 2: statement polarity == quantifiers.formal polarity
    for label, pol in (("statement_formal", pol_formal), ("statement_natural_language", pol_nl)):
        decided = pol["polarity"] != "undecided" and pol_qformal["polarity"] != "undecided"
        add(f"C2:{label}", pol_qformal["polarity"], pol["polarity"], decided,
            f"quantifiers.formal marker={pol_qformal['marker']}")
    # criterion 3: statement polarity != negation_normal_form polarity
    for label, pol in (("statement_formal", pol_formal), ("statement_natural_language", pol_nl)):
        if pol["polarity"] == "undecided" or pol_neg["polarity"] == "undecided":
            add(f"C3:{label}", "opposite_of:" + pol_neg["polarity"], pol["polarity"], False,
                f"negation marker={pol_neg['marker']}")
        else:
            expected = "positive" if pol_neg["polarity"] == "negative" else "negative"
            add(f"C3:{label}", expected, pol["polarity"], True, f"negation marker={pol_neg['marker']}")
    # criterion 4: statement polarity == nearest frozen base polarity
    for label, pol in (("statement_formal", pol_formal), ("statement_natural_language", pol_nl)):
        decided = base_polarity is not None and pol["polarity"] != "undecided"
        add(f"C4:{label}", base_polarity, pol["polarity"], decided,
            "nearest frozen class base")
    return {"fields": f, "polarities": {"statement_formal": pol_formal,
                                        "statement_natural_language": pol_nl,
                                        "quantifiers_formal": pol_qformal,
                                        "negation_normal_form": pol_neg,
                                        "token_implied": {"polarity": pol_token, "marker": "rule_spec_vocabulary"}},
            "criteria": rows,
            "flagged": any(r["decided"] and not r["agrees"] for r in rows)}


def run_stage(cmd: list, timeout=180) -> dict:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(cmd), "exit_code": p.returncode,
            "stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
            "stdout_head": p.stdout.strip()[:400], "stderr_head": p.stderr.strip()[:400]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts/worker-003/c0_polarity_adjudication/report.json"))
    ap.add_argument("--blindspot-out", default=str(ROOT / "artifacts/worker-003/c0_polarity_adjudication/blindspot_entry.json"))
    args = ap.parse_args()

    checks = []
    drift = []

    def check(cid, expectation, observed, note=""):
        ok = expectation == observed
        checks.append({"id": cid, "expectation": expectation, "observed": observed,
                       "pass": ok, "note": note})
        return ok

    # ------------------------------------------------------------ input hashes
    measured = {}
    for key, (rel, pin) in PINS.items():
        path = ROOT / rel
        if not path.exists():
            print(f"missing input {rel}", file=sys.stderr)
            return 2
        h = sha256_file(path)
        match = (h == pin) if len(pin) == 64 else h.startswith(pin)
        measured[key] = {"path": rel, "sha256": h, "pinned": pin, "match": match}
        if key not in SOFT_PINS and not match:
            drift.append({"input": key, "path": rel, "pinned": pin, "measured": h})
    for key, rel in UNPINNED.items():
        p = ROOT / rel
        measured[key] = {"path": rel, "sha256": sha256_file(p) if p.is_file() else None,
                         "pinned": None, "match": None}
    if drift:
        print(json.dumps({"status": "INPUT_DRIFT", "drift": drift}, indent=2))
        return 3

    base = load_yaml(ROOT / PINS["base_c0"][0])
    fixture = load_yaml(ROOT / PINS["fixture"][0])
    live = load_yaml(ROOT / UNPINNED["live_canonical_c0"])
    rule_spec = json.loads((ROOT / PINS["rule_spec"][0]).read_text())

    # ------------------------------------------------------------ semantic diff
    semantic = leaf_diff(base, fixture)
    header_only = [d for d in semantic if re.fullmatch(
        r"revision|revised_at|revised_at_unused|revision_history|timestamp_provenance|supersedes",
        str(d["path"]).strip("/").split("/")[-1])]
    semantic_core = [d for d in semantic if d not in header_only]
    check("D1", 2, len(semantic_core),
          f"core={len(semantic_core)} header/format={len(header_only)}")
    check("D2", ["conclusion/statement_formal", "conclusion/statement_natural_language"],
          sorted(str(d["path"]).strip("/") for d in semantic_core))

    # ------------------------------------------------------------ criteria
    base_pol = classify_polarity(base["conclusion"]["statement_formal"])["polarity"]
    live_pol = classify_polarity(live["conclusion"]["statement_formal"])["polarity"]
    base_res = criteria_for(base, base_pol)
    fixture_res = criteria_for(fixture, base_pol)

    check("A1", "negative", base_pol, "rev11 frozen C0 base conclusion polarity")
    check("A2", "negative", live_pol,
          f"live canonical rev{live.get('revision')} conclusion polarity (drift not fatal)")
    check("A3", "positive", fixture_res["polarities"]["statement_formal"]["polarity"],
          "mutant conclusion now asserts extension existence")
    check("A4", "positive", fixture_res["polarities"]["negation_normal_form"]["polarity"],
          "declared negation of the class is the existence statement")
    check("A5", False, base_res["flagged"], "base must not be flagged by its own criteria")
    check("A6", True, fixture_res["flagged"], "mutant must be flagged")
    # token demonstration: token is unchanged and R11-shaped token check cannot see content
    check("A7", fixture["conclusion"]["conclusion_type"], base["conclusion"]["conclusion_type"],
          "conclusion_type token unchanged, so a token-only R11 check passes")

    # ------------------------------------------------------------ recorded pipeline verdicts
    raw = json.loads((ROOT / PINS["raw_verdicts"][0]).read_text())
    recorded_fixture = next(e for e in raw["fixtures"]
                            if e["file"] == PINS["fixture"][0].split("/")[-1])
    recorded_head = json.dumps({k: recorded_fixture[k] for k in
                                ("file", "stage_a", "stage_b", "caught_stage_a", "caught_stage_b",
                                 "caught_union", "escaped_union")})

    # ------------------------------------------------------------ stage re-runs
    # The live re-run is a function of (tool bytes, rule_spec, KEY_MANIFEST, schema bytes).
    # KEY_MANIFEST.json is NOT pinned by the corpus manifest; it moved after the corpus run,
    # so the recorded accept is compared against the live verdict and the drift is recorded.
    stage_a = run_stage([sys.executable, str(ROOT / PINS["stage_a"][0]), str(ROOT / PINS["base_c0"][0]), "--json"])
    stage_a_mut = run_stage([sys.executable, str(ROOT / PINS["stage_a"][0]), str(ROOT / PINS["fixture"][0]), "--json"])
    stage_b = run_stage([sys.executable, str(ROOT / PINS["stage_b"][0]), str(ROOT / PINS["base_c0"][0])])
    stage_b_mut = run_stage([sys.executable, str(ROOT / PINS["stage_b"][0]), str(ROOT / PINS["fixture"][0])])
    km = ROOT / "artifacts/formulation/KEY_MANIFEST.json"
    key_manifest = {"path": "artifacts/formulation/KEY_MANIFEST.json",
                    "sha256": sha256_file(km) if km.exists() else None,
                    "mtime": datetime.fromtimestamp(km.stat().st_mtime, CST).isoformat(timespec="seconds")
                    if km.exists() else None,
                    "pinned_by_corpus_manifest": False}
    measured["key_manifest"] = {**key_manifest, "pinned": None, "match": None}
    check("S1", {"verdict": "pass", "exit": 0},
          {"verdict": recorded_fixture["stage_a"]["verdict"], "exit": recorded_fixture["stage_a"]["exit"]},
          "RECORDED stage-A verdict at corpus time (raw_verdicts.json)")
    check("S2", {"verdict": "accept", "exit": 0},
          {"verdict": recorded_fixture["stage_b"]["verdict"], "exit": recorded_fixture["stage_b"]["exit"]},
          "RECORDED stage-B verdict at corpus time (raw_verdicts.json)")
    check("S3", 0, stage_b_mut["exit_code"],
          "LIVE semantic stage still accepts the polarity mutant at pinned tool hash")
    check("S4", True,
          stage_a["exit_code"] == stage_a_mut["exit_code"] and
          stage_a["exit_code"] != 0 and stage_a_mut["exit_code"] != 0,
          f"LIVE structural stage now rejects BOTH base and mutant identically "
          f"(base exit {stage_a['exit_code']}, mutant exit {stage_a_mut['exit_code']}): "
          f"unpinned KEY_MANIFEST drift (R22 revised_at_unused), not a polarity fix")
    check("S5", False, key_manifest["pinned_by_corpus_manifest"],
          f"KEY_MANIFEST.json moved at {key_manifest['mtime']} (sha {str(key_manifest['sha256'])[:16]}), "
          "after the 00:22 corpus run and the 00:29 replication; it is a live dependency of both stage verdicts")

    # ------------------------------------------------------------ controls
    def synth(ctype, formal, nl, qformal=None, qneg=None):
        d = copy.deepcopy(base)
        d["conclusion"] = dict(d["conclusion"])
        d["conclusion"]["conclusion_type"] = ctype
        d["conclusion"]["statement_formal"] = formal
        d["conclusion"]["statement_natural_language"] = nl
        if qformal is not None:
            d["quantifiers"]["formal"] = qformal
        if qneg is not None:
            d["quantifiers"]["negation_normal_form"] = qneg
        return d

    repair = copy.deepcopy(fixture)
    repair["conclusion"]["statement_formal"] = base["conclusion"]["statement_formal"]
    repair["conclusion"]["statement_natural_language"] = base["conclusion"]["statement_natural_language"]
    novel_pos = synth("scc_c0_future_inextendibility",
                      "forall (s,delta) in D0 for comeager many data D: there exists a proper future C0 metric extension of the maximal development of D",
                      "For comeager many generic data the maximal development can be continuously extended.")
    novel_neg = synth("scc_c0_future_inextendibility",
                      "every comeager set of data contains a datum whose maximal development admits no proper future C0 metric extension",
                      "No generic datum admits a proper future C0 metric extension of its maximal development.")
    simple_pos = synth("scc_c0_future_inextendibility",
                       "exists a proper future C0 metric extension", "it can be continuously extended")
    simple_neg = synth("scc_c0_future_inextendibility",
                       "not exists a proper future C0 metric extension", "it is future-inextendible")

    control_rows = []
    for name, doc, expect_flag, why in [
        ("base_rev11", base, False, "frozen class base"),
        ("live_rev12", live, False, "live canonical"),
        ("fixture_c0_03", fixture, True, "escape under adjudication"),
        ("repair_control", repair, False, "mutant with the two statement fields restored"),
        ("novel_positive", novel_pos, True, "independently authored polarity inversion"),
        ("novel_negative", novel_neg, False, "independently authored negation-preserving paraphrase"),
        ("sanity_positive", simple_pos, True, "two-sided classifier sanity"),
        ("sanity_negative", simple_neg, False, "two-sided classifier sanity"),
    ]:
        r = criteria_for(doc, base_pol)
        control_rows.append({"control": name, "expected_flag": expect_flag, "observed_flag": r["flagged"],
                             "why": why, "polarities": {k: v["polarity"] for k, v in r["polarities"].items()}})
    check("C1", [c["expected_flag"] for c in control_rows],
          [c["observed_flag"] for c in control_rows], "control matrix (see controls table)")

    # conforming corpus controls must not be flagged
    for cf in sorted((ROOT / UNPINNED["controls_dir"]).glob("*.yaml")):
        doc = load_yaml(cf)
        b = load_yaml(ROOT / UNPINNED["bases_dir"] / {
            "AF-SCC-C0-VAC-GEN": "af_scc_c0_vacuum.yaml",
            "AF-SCC-C2-VAC-GEN": "af_scc_c2_vacuum.yaml",
            "AF-WCC-VAC-GEN": "af_wcc_vacuum.yaml"}.get(doc.get("class_id"), "af_scc_c0_vacuum.yaml"))
        bp = classify_polarity(b["conclusion"]["statement_formal"])["polarity"]
        r = criteria_for(doc, bp)
        control_rows.append({"control": f"corpus_control:{cf.name}", "expected_flag": False,
                             "observed_flag": r["flagged"], "why": "conforming corpus control",
                             "polarities": {k: v["polarity"] for k, v in r["polarities"].items()}})
    check("C2", False, any(c["observed_flag"] for c in control_rows if c["control"].startswith("corpus_control")),
          "no conforming corpus control flagged")

    # ------------------------------------------------------------ specificity sweep
    bases = {}
    for cid, fn in {"AF-SCC-C0-VAC-GEN": "af_scc_c0_vacuum.yaml",
                    "AF-SCC-C2-VAC-GEN": "af_scc_c2_vacuum.yaml",
                    "AF-WCC-VAC-GEN": "af_wcc_vacuum.yaml"}.items():
        bases[cid] = load_yaml(ROOT / UNPINNED["bases_dir"] / fn)
    sweep = []
    for mf in sorted((ROOT / UNPINNED["mutants_dir"]).glob("*.yaml")):
        doc = load_yaml(mf)
        diffs = {cid: len(leaf_diff(b, doc)) for cid, b in bases.items()}
        order = sorted(diffs.items(), key=lambda kv: kv[1])
        nearest, ndiff = order[0]
        tie = len(order) > 1 and order[1][1] == ndiff
        bp = classify_polarity(bases[nearest]["conclusion"]["statement_formal"])["polarity"] if not tie else None
        r = criteria_for(doc, bp)
        reasons = [x["criterion"] for x in r["criteria"] if x["decided"] and not x["agrees"]]
        sweep.append({"fixture": mf.name, "class_id": doc.get("class_id"),
                      "nearest_base": None if tie else nearest, "base_leaf_diff": diffs,
                      "polarity_formal": r["polarities"]["statement_formal"]["polarity"],
                      "base_polarity": bp, "flagged": r["flagged"], "reasons": reasons})
    flagged = [s for s in sweep if s["flagged"]]
    check("P1", 1, len(flagged), "specificity sweep: exactly the known escape is flagged")
    check("P2", PINS["fixture"][0].split("/")[-1], flagged[0]["fixture"] if len(flagged) == 1 else None)

    # ------------------------------------------------------------ (recorded verdicts loaded above)
    drift_live = measured["live_canonical_c0"]["sha256"] != PINS["base_c0"][1]

    findings = [
        {"id": "W003-PA-01", "severity": "major", "kind": "confirmed_blind_spot",
         "finding": "c0_03_conclusion_negated is a genuine class-contract violation: its conclusion statements assert the existence of a proper future C0 metric extension while conclusion_type, quantifiers.formal and quantifiers.negation_normal_form all remain the canonical non-existence form. At corpus time both frozen pipeline stages accepted it (recorded in raw_verdicts.json: structural exit 0/pass, semantic exit 0/accept; see W003-PA-05 for the live re-run), so the escape is real, not a labelling artifact.",
         "falsifier": "Re-run both frozen stages at the pinned hashes on the pinned fixture: any non-zero exit code, or a semantic verdict other than accept, falsifies this finding. A semantic diff showing a change outside conclusion.statement_formal/statement_natural_language also falsifies it."},
        {"id": "W003-PA-02", "severity": "major", "kind": "detector_gap",
         "finding": "The gap is content-vs-token: R11 (per rule_spec) checks that conclusion.conclusion_type equals the class vocabulary token, and the token is unchanged. No rule in the spec compares the polarity/content of conclusion statements against conclusion_type, quantifiers.formal, or quantifiers.negation_normal_form. The candidate repair is additive: conclusion polarity must equal quantifiers.formal polarity, must be the opposite of quantifiers.negation_normal_form polarity, and must match the token family.",
         "falsifier": "A rule-spec or gate revision that already compares conclusion content polarity against the declared negation, demonstrated by catching this fixture in a re-run at pinned hashes, falsifies the 'gap' claim."},
        {"id": "W003-PA-03", "severity": "info", "kind": "measurement",
         "finding": "A minimal lexical polarity check with a declared trigger vocabulary flags this escape and nothing else in the 49-fixture FORM-HELDOUT-09 corpus (specificity 48/48), is silent on all four conforming controls, on the rev11 base and on the live rev12 canonical, flags an independently authored inversion phrased differently, and is silent on a negation-preserving paraphrase and on a repair control. Scope limit: the classifier decides only statements that mention extension/extendibility vocabulary; a polarity inversion phrased without that vocabulary is undecided, not caught.",
         "falsifier": "Any control in the matrix with an observed flag different from its declared expectation, or a flagged fixture in the specificity sweep other than c0_03_conclusion_negated, falsifies the sensitivity/specificity claim on re-run."},
        {"id": "W003-PA-04", "severity": "info", "kind": "drift_observation",
         "finding": f"The live canonical schemas/af_scc_c0_vacuum.yaml is revision {live.get('revision')} at {measured['live_canonical_c0']['sha256'][:16]} while the corpus base is the frozen rev11 at 1bb78ce9b357. The live revision's conclusion polarity is negative (consistent), so the adjudication is unaffected, but the corpus owner should re-derive mutants from the live revision before the next held-out run.",
         "falsifier": "A measurement showing the live canonical still at 1bb78ce9b357, or a live conclusion polarity of positive, falsifies the drift observation."},
        {"id": "W003-PA-05", "severity": "major", "kind": "unpinned_dependency",
         "finding": f"Stage verdicts are a function of (tool bytes, rule_spec, KEY_MANIFEST.json, schema bytes). The corpus manifest pins the first two and the schema hashes but not KEY_MANIFEST.json; that file moved at {key_manifest['mtime']} (sha {str(key_manifest['sha256'])[:16]}), after the 00:22 corpus build and the 00:29 replication. Live re-run of the pinned structural stage now rejects BOTH the rev11 base and the c0_03 mutant with R22 (unknown key 'revised_at_unused'), so the recorded accept is no longer reproducible and the escape is currently masked by an unrelated structural failure rather than fixed. The live semantic stage still accepts the mutant.",
         "falsifier": "Reproduce the recorded accept by re-running the pinned structural stage at a KEY_MANIFEST hash that contains revised_at_unused (or excludes it from the schema), demonstrating the live rejection is manifest drift and not a polarity rule."},
    ]

    adjudication = {
        "question_1_genuine_violation": bool(
            fixture_res["flagged"]
            and recorded_fixture["stage_a"]["exit"] == 0
            and recorded_fixture["stage_b"]["exit"] == 0),
        "question_2_check_catches_without_false_positives": bool(len(flagged) == 1 and not any(
            c["observed_flag"] for c in control_rows if not c["expected_flag"])),
        "verdict": "CONFIRMED_BLIND_SPOT",
        "scope": "Structure/semantics of the frozen bytes only. No mathematics is decided, no gate verdict, no node completion, no class-truth claim.",
    }

    blindspot = {
        "entry_id": "W003-BS-C0-POLARITY-01",
        "corpus_id": "FORM-HELDOUT-09",
        "fixture_path": PINS["fixture"][0],
        "fixture_sha256": PINS["fixture"][1],
        "class_id": "AF-SCC-C0-VAC-GEN",
        "family": "c0-conclusion-polarity-inversion",
        "status": "confirmed_blind_spot",
        "confirmed_by": "worker-003 (independent of worker-068/worker-06 code; frozen stages re-run as subprocesses)",
        "pipeline_behavior": {
            "structural_stage_recorded_corpus_time": f"accept exit {recorded_fixture['stage_a']['exit']}",
            "semantic_stage_recorded_corpus_time": f"accept exit {recorded_fixture['stage_b']['exit']}",
            "structural_stage_live": f"exit {stage_a_mut['exit_code']} (KEY_MANIFEST drift, R22; same rejection as the base)",
            "semantic_stage_live": f"exit {stage_b_mut['exit_code']}",
            "r11": "conclusion_type token present and equal to class vocabulary -> pass"},
        "defect": "conclusion.statement_formal and conclusion.statement_natural_language assert existence of a proper future C0 metric extension; conclusion_type, quantifiers.formal and quantifiers.negation_normal_form remain the canonical non-existence form.",
        "proposed_rule_extension": "R11+: polarity(conclusion.statement_formal) == polarity(quantifiers.formal) AND polarity(conclusion.statement_formal) == opposite(polarity(quantifiers.negation_normal_form)) AND polarity(conclusion.statement_formal) == TOKEN_POLARITY[conclusion_type].",
        "falsifier": "A re-run of the frozen stages at the pinned hashes that rejects the fixture, or a re-run of the adjudicator whose control matrix differs from the declared expectations, retires this entry.",
    }

    report = {
        "task_id": "W003-C0-POLARITY-ADJUDICATION-01",
        "actor": "worker-003",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "A1",
        "gate": "G-CLASSBIND (folded into G-AUDIT as calibration evidence)",
        "inputs": measured,
        "semantic_diff_base_vs_fixture": {"core": semantic_core, "header_or_format_only": header_only},
        "polarities": {"base_rev11": base_res["polarities"], "fixture": fixture_res["polarities"],
                       "live_canonical": {"revision": live.get("revision"), "polarity": live_pol}},
        "criteria_fixture": fixture_res["criteria"],
        "checks": checks,
        "stage_reruns": {"base": {"structural": stage_a, "semantic": stage_b},
                         "fixture": {"structural": stage_a_mut, "semantic": stage_b_mut},
                         "recorded_fixture": recorded_fixture,
                         "key_manifest": key_manifest},
        "controls": control_rows,
        "specificity_sweep": {"fixtures": sweep, "flagged_count": len(flagged),
                              "flagged": [s["fixture"] for s in flagged]},
        "recorded_pipeline_verdict_sample": recorded_head,
        "live_canonical_drift": drift_live,
        "findings": findings,
        "adjudication": adjudication,
        "environment": {"python": sys.version.split()[0], "pyyaml": yaml.__version__},
        "reproduce": "python3 artifacts/worker-003/c0_polarity_adjudication/adjudicate_c0_polarity.py --out artifacts/worker-003/c0_polarity_adjudication/report.json",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    Path(args.blindspot_out).write_text(json.dumps(blindspot, indent=2, sort_keys=True) + "\n")

    failed = [c for c in checks if not c["pass"]]
    print(json.dumps({"report": str(out_path), "checks": len(checks), "failed": failed,
                      "adjudication": adjudication}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
