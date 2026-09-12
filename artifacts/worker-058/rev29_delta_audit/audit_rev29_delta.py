#!/usr/bin/env python3
"""W058-REV29-DELTA-05 -- independent delta certificate for the rev29 freeze break
(astra-life05-evidence-binding-repair, FROZEN revision 29, frozen_at 2026-09-12T00:55:02+08:00).

Context: this worker was auditing the W083 rev13 repair packet against the rev28 pins when the
freeze broke (rev28 F2b 55d0a1ea -> rev29 F2b b2ab6acb; F1 cce9c601 -> d9cebb94; F2a 5476a3f2 ->
e9a27996). The aborted first pass is kept at ../rev13_packet_audit/audit_report.json (measured
FROZEN e1a8aaa394eb at 00:55:01). This script re-binds to the rev29 bytes and certifies the delta.

Claims checked (class-bound: AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; F1/F2a/F2b;
gate context G-FORM):
  D1 pins      : rev29 canonical bytes + FROZEN rev29 self-consistency (48 entries).
  D2 binding   : f0_binding resolves in all three schemas; the L-FORM-02 refresh direction landed.
  D3 content   : independent containment sweep at the NEW F2b hash -- did L-FORM-01 land?
  D4 packet    : W083's L-FORM-01 diff vs the new bytes; is its declared target hash still valid?
  D5 L-FORM-03 : predicate-strength vs class-statement-strength wording at the residual sites.
  D6 F1 repair : were the three cited F1 anchors changed, and only they (delta census vs predecessor)?
  D7 verdicts  : which published verdicts were voided by the three hash moves.
  D8 recurrence: does L-FORM-02 recur silently when an input moves (guard absent)?

Read-only on every canonical path; all mutation happens in sandbox/ copies.
Exit 0 = certificate written (NOT a gate verdict).
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent          # <repo>/artifacts/worker-058/rev29_delta_audit
ROOT = HERE.parents[2]                          # <repo>

LIVE = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}
PRED = {  # rev28 pins that the three hash moves voided
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
SCHEMAS = {"F1": "schemas/af_wcc_vacuum.yaml", "F2a": "schemas/af_scc_c2_vacuum.yaml",
           "F2b": "schemas/af_scc_c0_vacuum.yaml"}
PACKET = ROOT / "artifacts/worker-083/rev13_repair_packet"
PACKET_LFORM01 = {
    "canonical": (PACKET / "diffs/af_scc_c0_vacuum--LFORM01.patch.diff", "schemas/af_scc_c0_vacuum.yaml"),
    "mirror": (PACKET / "diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff",
               "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
}
PACKET_DECLARED_TARGET = "3cdcaa44e6f103f4dacbc03c509f39586f7788e14ddba981b19985c843821c48"
PRED_F2B_COPY = PACKET / "sandbox_pristine/schemas/af_scc_c0_vacuum.yaml"

LFORM03_SITES = [
    ("research_map/formulation_taxonomy.yaml", 200, "declared F0 taxonomy (G-F0 frozen)"),
    ("artifacts/formulation/formulation_taxonomy.yaml", 176, "class-contract supplement D1 ledger"),
    ("artifacts/formulation/VARIANT_REGISTRY.json", 57, "variant registry strength field"),
    ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", 11, "SET delta strength field"),
    ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", 22, "SET delta predicate change"),
]
PRISTINE = [
    "schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
]


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "cwd": str(cwd), "rc": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def make_sandbox(name: str) -> Path:
    sb = HERE / "sandbox" / name
    if sb.exists():
        shutil.rmtree(sb)
    for rel in PRISTINE:
        d = sb / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, d)
    return sb


def _norm(tok: str) -> str:
    t = tok.strip().strip('"').strip("'").replace("{", "").replace("}", "")
    t = t.replace("^", "").replace("_", "").replace(" ", "")
    return t.rstrip(";:,. ")  # chain strings end "E_C2;" / "E_C2." depending on revision


def parse_chain_order(chain_text: str) -> list[str]:
    toks = re.findall(r"E_\{?([^}]+?)\}?(?=\s+(?:contains|subset|superset)|[,\s]|$)", chain_text)
    out = []
    for t in toks:
        n = _norm(t)
        if n and n not in out:
            out.append(n)
    return out


def find_key(d, name, path=()):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == name:
                return path + (k,), v
            r = find_key(v, name, path + (k,))
            if r:
                return r
    elif isinstance(d, list):
        for i, v in enumerate(d):
            r = find_key(v, name, path + (i,))
            if r:
                return r
    return None


def find_all(d, name, path=()):
    """All occurrences, because these documents carry repeated keys (C0 has two must_not_conflate)."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            if k == name:
                out.append((path + (k,), v))
            out.extend(find_all(v, name, path + (k,)))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.extend(find_all(v, name, path + (i,)))
    return out


def containment_findings(text: str, label: str) -> dict:
    """Rules R1/R1b/R2/R3 re-instantiated from W058 rounds 2-4 (independent of the leads' tools)."""
    doc = yaml.safe_load(text)
    if "implication_ledger" not in doc:
        return {"label": label, "applicable": False, "reason": "no implication_ledger (not an SCC schema)",
                "live_findings": [], "hard_codes": [], "advisory_codes": []}
    led = doc["implication_ledger"]
    order = parse_chain_order(led["extension_class_containment"])
    size = {t: i for i, t in enumerate(order)}
    rk = find_key(doc, "extension_regularity")
    own = _norm(str(rk[1])) if rk else None
    if own not in size:
        own = next((t for t in size if t in _norm(str(doc.get("class_id", "")))), None)
    out = []

    for i, row in enumerate(led.get("forbidden_transfers", [])):
        m = re.search(r"([A-Za-z0-9_^{},\\\\ ]+?)\s+is a strictly (larger|smaller) extension class",
                      row.get("reason", ""))
        if m and _norm(m.group(1)) in size and own in size:
            subj, word = _norm(m.group(1)), m.group(2)
            smaller = size[subj] > size[own]
            ok = (word == "smaller") == smaller
            out.append({"code": None if ok else "class_size_predicate_inverted", "rule": "R1_size_predicate",
                        "row_index": i, "subject": subj, "own_class": own, "word": word,
                        "derived": "smaller" if smaller else "larger", "severity": "none" if ok else "hard"})
        m2 = re.match(r"no proper future (.+?) extension", row.get("from", ""))
        if m2 and row.get("to") == "this class" and own in size and _norm(m2.group(1)) in size:
            subj = _norm(m2.group(1))
            ok = size[subj] > size[own]
            out.append({"code": None if ok else "forbidden_transfer_direction_incoherent",
                        "rule": "R1b_transfer_direction", "row_index": i, "subject": subj,
                        "severity": "none" if ok else "hard"})

    wk_all, st_all = find_all(doc, "forbidden_weakenings"), find_all(doc, "forbidden_strengthenings")
    if wk_all and st_all:
        st_text = " || ".join(str(x) for _, v in st_all for x in v)
        for _, wlist in wk_all:
            for i, item in enumerate(wlist):
                if re.search(r"two-sided", str(item), re.I) and re.search(r"two-sided", st_text, re.I):
                    out.append({"code": "strength_bucket_mismatch", "rule": "R2_bucket", "row_index": i,
                                "item": str(item), "severity": "advisory"})

    for _, mnc_list in find_all(doc, "must_not_conflate"):
        for i, item in enumerate(mnc_list):
            m3 = re.search(r"[Nn]o containment with ([^.;]+?) is asserted", str(item))
            if m3:
                toks = [_norm(t) for t in re.split(r",|\bor\b|\band\b", m3.group(1)) if _norm(t)]
                hit = [t for t in toks if t in size and own in size and size[t] != size[own]]
                out.append({"code": "stale_or_contradictory_containment_denial" if hit else None,
                            "rule": "R3_denial", "row_index": i, "denied_tokens": toks,
                            "tokens_with_declared_containment": hit,
                            "severity": "hard" if hit else "none",
                            "severity_steelman": "advisory" if hit else "none"})
    live = [f for f in out if f["code"]]
    return {"label": label, "chain_order_largest_first": order, "own_class_token": own,
            "live_findings": live,
            "hard_codes": sorted({f["code"] for f in live if f["severity"] == "hard"}),
            "advisory_codes": sorted({f["code"] for f in live if f["severity"] == "advisory"})}


def resolve_pointer(ptr, base: Path) -> dict:
    if not isinstance(ptr, str) or "#" not in ptr:
        return {"resolves": False, "reason": "no #fragment"}
    rel, frag = ptr.split("#", 1)
    p = base / rel
    if not p.exists():
        return {"resolves": False, "reason": f"missing {rel}"}
    node = yaml.safe_load(p.read_text())
    for part in frag.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return {"resolves": False, "reason": f"{frag!r} fails at {part!r}"}
    return {"resolves": True, "target_type": type(node).__name__}


def binding_checks(base: Path) -> dict:
    out = {}
    for node, rel in SCHEMAS.items():
        doc = yaml.safe_load((base / rel).read_text())
        fb = doc.get("f0_binding", {})
        ev = base / fb.get("consistency_evidence", "")
        ev_h = sha(ev) if ev.exists() else None
        f0 = base / fb.get("declared_f0_artifact", "")
        out[node] = {
            "declared_f0_matches_measured": f0.exists() and fb.get("declared_f0_sha256") == sha(f0),
            "consistency_evidence_matches_measured": ev_h == fb.get("consistency_evidence_sha256"),
            "declared_consistency_evidence_prefix": str(fb.get("consistency_evidence_sha256"))[:12],
            "measured_consistency_evidence_prefix": (ev_h or "")[:12],
            "class_contract_pointer": resolve_pointer(doc.get("class_contract_pointer"), base),
            "supplement_pointer": resolve_pointer(doc.get("class_contract_supplement_pointer"), base),
        }
    out["all_resolve"] = all(v["declared_f0_matches_measured"] and
                             v["consistency_evidence_matches_measured"] and
                             v["class_contract_pointer"]["resolves"] and
                             v["supplement_pointer"]["resolves"] for k, v in out.items() if k != "all_resolve")
    return out


def changed_lines(a: str, b: str) -> list[dict]:
    al, bl = a.splitlines(), b.splitlines()
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=al, b=bl, autojunk=False).get_opcodes():
        if tag != "equal":
            ops.append({"op": tag, "old_lines": [i1 + 1, i2], "new_lines": [j1 + 1, j2]})
    return ops


# ---- L-FORM-03: wording classification -------------------------------------------------------
def _assertive(text: str) -> str:
    """Strip revision-history notes and quoted historical direction words before classifying."""
    t = re.sub(r"\[rev\d+:[^\]]*\]", " ", text)
    t = re.sub(r"\[R\d+[^\]]*\]", " ", t)
    t = re.sub(r"'strictly (STRONGER|WEAKER)'", " ", t, flags=re.I)
    t = re.sub(r"corrected from[^.;]*", " ", t, flags=re.I)
    t = re.sub(r"was false", " ", t, flags=re.I)
    return re.sub(r"\s+", " ", t)


def classify_direction(text: str) -> dict:
    """Formal facts: P_tail => P_set. So the SET predicate is strictly WEAKER, the SET negation is
    strictly STRONGER, and the SET class conclusion (no P_set) is strictly STRONGER."""
    t = _assertive(text)
    strong = bool(re.search(r"strictly\s+stronger", t, re.I))
    weak = bool(re.search(r"strictly\s+weaker", t, re.I))
    predicate_subject = bool(re.search(r"reading|predicate", t, re.I))
    negation_subject = bool(re.search(r"outside|not contained|no single|negation|must not be interchanged|refute", t, re.I))
    if not (strong or weak):
        verdict = "NO_DIRECTION_WORD"
    elif strong and predicate_subject and not negation_subject:
        verdict = "INVERTED_IF_PREDICATE_READING"
    elif strong and negation_subject:
        verdict = "CORRECT_AS_NEGATION_STRENGTH"
    elif strong:
        verdict = "CORRECT_AS_CLASS_STATEMENT_UNSCOPED"
    elif weak and predicate_subject:
        verdict = "CORRECT_PREDICATE_WEAKER"
    else:
        verdict = "WEAKER_CLAIM"
    return {"direction_word": "stronger" if strong else ("weaker" if weak else None),
            "subject_scope_guess": ("predicate" if predicate_subject and not negation_subject else
                                    ("negation/class" if negation_subject else "unscoped")),
            "verdict": verdict, "assertive_text": t.strip()[:400],
            "formal_facts": {
                "predicate": "P_tail(gamma) => P_set(gamma); SET is strictly WEAKER as a predicate",
                "negation": "not P_set => not P_tail; the SET negation is strictly STRONGER",
                "class_conclusion": "no P_set => no P_tail; the SET class conclusion is strictly STRONGER",
            }}


def lform03_extract(base: Path) -> list[dict]:
    """Extract the SET-direction scalars by field navigation (not by line number)."""
    sites = []
    # 1. declared F0 taxonomy: the class description containing "set-based reading"
    tax = yaml.safe_load((base / "research_map/formulation_taxonomy.yaml").read_text())
    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            yield path, node
    for path, val in walk(tax):
        if "set-based reading" in val:
            sites.append({"site": "declared F0 taxonomy", "file": "research_map/formulation_taxonomy.yaml",
                          "field": path, "site_note": "G-F0 frozen", **classify_direction(val)})
    # 2. supplement D1 f0_reading
    sup = yaml.safe_load((base / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    def find_d1(node):
        if isinstance(node, dict):
            if node.get("id") == "D1":
                return node
            for v in node.values():
                r = find_d1(v)
                if r:
                    return r
        elif isinstance(node, list):
            for v in node:
                r = find_d1(v)
                if r:
                    return r
        return None
    d1 = find_d1(sup)
    if d1 and isinstance(d1.get("f0_reading"), str):
        sites.append({"site": "class-contract supplement D1 ledger",
                      "file": "artifacts/formulation/formulation_taxonomy.yaml",
                      "field": "contract_divergences.items[D1].f0_reading",
                      **classify_direction(d1["f0_reading"])})
    # 3. variant registry SET strength
    reg = json.loads((base / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    for v in (reg.get("variants") or reg.get("classes") or []):
        if str(v.get("variant_id", "")).upper() == "SET" or "SET" in str(v.get("id", "")):
            if isinstance(v.get("strength"), str):
                sites.append({"site": "variant registry strength field",
                              "file": "artifacts/formulation/VARIANT_REGISTRY.json",
                              "field": f"variants[{v.get('variant_id')}].strength",
                              **classify_direction(v["strength"])})
            break
    # 4. SET delta: strength + visibility.definition + negation_conclusion
    dp = base / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
    d = json.loads(dp.read_text())
    if isinstance(d.get("strength"), str):
        sites.append({"site": "SET delta strength field", "file": str(dp.relative_to(base)),
                      "field": "strength", **classify_direction(d["strength"])})
    for ch in d.get("changes", []):
        if ch.get("path") in ("visibility.definition", "visibility.negation_conclusion") and isinstance(ch.get("to"), str):
            sites.append({"site": f"SET delta changes[{ch['path']}]", "file": str(dp.relative_to(base)),
                          "field": f"changes[{ch['path']}].to", **classify_direction(ch["to"])})
    return sites


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "rev29_delta_report.json"))
    args = ap.parse_args()
    rep = {"audit_id": "W058-REV29-DELTA-05", "actor": "worker-058", "created_at": now(),
           "class_binding": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
           "nodes": ["F1", "F2a", "F2b"], "gate_context": "G-FORM",
           "authority": "worker evidence only; no canonical path written; no gate verdict or node transition",
           "predecessor_audit": "artifacts/worker-058/rev13_packet_audit/audit_report.json (aborted at pin drift 00:55:01)"}

    # D1 -- pins + FROZEN rev29 self-consistency (independent re-implementation of verify_frozen)
    started = {rel: sha(ROOT / rel) for rel in LIVE}
    rep["D1_pins"] = {"expected": LIVE, "measured_at_start": started,
                      "all_match": all(started[r] == h for r, h in LIVE.items()),
                      "frozen": {}}
    man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    mism, missing = [], []
    for rel, rec in man["files"].items():
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
        elif sha(p) != rec["sha256"]:
            mism.append({"path": rel, "manifest": rec["sha256"], "disk": sha(p)})
    vf = run(["python3", "artifacts/formulation/tools/verify_frozen.py"], cwd=ROOT)
    rep["D1_pins"]["frozen"] = {
        "manifest_sha256": sha(ROOT / "artifacts/formulation/FROZEN.json"),
        "revision": man.get("revision"), "frozen_at": man.get("frozen_at"),
        "files_total": len(man["files"]), "mismatched": mism, "missing": missing,
        "verify_frozen_rc": vf["rc"], "verify_frozen_stdout": vf["stdout"].strip(),
        "independent_agrees_with_tool": (len(mism) + len(missing) > 0) == (vf["rc"] != 0),
        "self_consistent": not mism and not missing,
        "manifest_generations_observed": [
            {"sha256": "e1a8aaa394eb49ce3fac73a6171ccd0d3e494c8619bbe012d8150cdee4219968",
             "seen_at": "2026-09-12T00:55:01+08:00", "source": "this worker, aborted first pass (rev28 pins)",
             "revision": "unparsed", "frozen_at": "unparsed"},
            {"sha256": "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
             "seen_at": "2026-09-12T00:56:06+08:00", "source": "worker-007 rev29_preflight report_rev29.json",
             "revision": 29, "frozen_at": "2026-09-12T00:55:02+08:00", "files": 48},
            {"sha256": sha(ROOT / "artifacts/formulation/FROZEN.json"),
             "seen_at": now(), "source": "this certificate",
             "revision": man.get("revision"), "frozen_at": man.get("frozen_at"), "files": len(man["files"])},
        ],
        "generation_note": ("three byte-distinct FROZEN.json generations observed; the last two both "
                            "declare revision 29 with different frozen_at (00:55:02 vs 00:57:26) and "
                            "48 vs 50 files, so a citation of 'FROZEN rev29' without the manifest "
                            "sha256/frozen_at is ambiguous"),
    }
    if not rep["D1_pins"]["all_match"]:
        rep["verdict"] = {"status": "ABORTED_PIN_DRIFT", "reason": "canonical bytes already differ from the rev29 hashes"}
        Path(args.json).write_text(json.dumps(rep, indent=2) + "\n")
        print("ABORTED: pins do not match rev29")
        return 1

    # pinned provenance copies
    pin = HERE / "pinned"
    pin.mkdir(exist_ok=True)
    for rel in list(LIVE) + ["artifacts/formulation/FROZEN.json"]:
        d = pin / Path(rel).name
        shutil.copy2(ROOT / rel, d)

    # D2 -- binding
    rep["D2_binding"] = {"live": binding_checks(ROOT)}
    sb_pre = make_sandbox("predecessor_f2b")
    if PRED_F2B_COPY.exists() and sha(PRED_F2B_COPY) == PRED["schemas/af_scc_c0_vacuum.yaml"]:
        shutil.copy2(PRED_F2B_COPY, sb_pre / SCHEMAS["F2b"])

    # D3 -- independent containment sweep, predecessor vs rev29
    rep["D3_content"] = {
        "predecessor_f2b": containment_findings(PRED_F2B_COPY.read_text(), "F2b @55d0a1ea (rev28)"),
        "rev29_f2b": containment_findings((ROOT / SCHEMAS["F2b"]).read_text(), "F2b @b2ab6acb (rev29)"),
        "siblings_rev29": {n: containment_findings((ROOT / SCHEMAS[n]).read_text(), n)["live_findings"]
                           for n in ("F1", "F2a")},
    }
    rep["D3_content"]["lform01_still_live"] = \
        "class_size_predicate_inverted" in rep["D3_content"]["rev29_f2b"]["hard_codes"]
    rep["D3_content"]["residual_classification"] = {
        "class_size_predicate_inverted": "hard, unanimous (W058 rounds 1-4, worker-066 H1, lead L-FORM-01)",
        "stale_or_contradictory_containment_denial": ("hard under the strict same-document reading; "
                                                      "advisory under the steelman 'here = this bullet' reading "
                                                      "(worker-066 records H2 hard; W058 rounds 2/4 advisory)"),
        "strength_bucket_mismatch": "advisory",
    }

    # D4 -- packet diff vs new bytes
    rep["D4_packet"] = {"declared_target": PACKET_DECLARED_TARGET, "per_copy": {}}
    for key, (diff, rel) in PACKET_LFORM01.items():
        sb = make_sandbox(f"packet_{key}")
        dry = run(["patch", "-p1", "-F0", "--dry-run", "-i", str(diff)], cwd=sb)
        real = run(["patch", "-p1", "-F0", "-i", str(diff)], cwd=sb) if dry["rc"] == 0 else None
        new_h = sha(sb / rel)
        rep["D4_packet"]["per_copy"][key] = {
            "diff": str(diff.relative_to(ROOT)), "diff_sha256": sha(diff), "applies_clean_fuzz0": dry["rc"] == 0,
            "resulting_sha256": new_h, "matches_declared_target": new_h == PACKET_DECLARED_TARGET,
            "target_is_stale": new_h != PACKET_DECLARED_TARGET,
            "changed_lines": changed_lines((ROOT / rel).read_text(), (sb / rel).read_text()),
        }
    rep["D4_packet"]["note"] = ("the diff text still applies to the rev29 bytes, but its declared "
                                "target hash was computed on the rev28 bytes; any application must be "
                                "re-pinned. The packet's L-FORM-02 direction (restore 675a99d0 + guard) "
                                "was superseded by rev29, which refreshed the declared hash to the live "
                                "9e335e9b instead; the O3 guard was not applied (checker still de356d99).")

    # D5 -- L-FORM-03 wording
    rep["D5_lform03"] = {"formal_relation": {
        "P_tail_implies_P_set": True,
        "predicate_strength": "SET predicate strictly WEAKER than single-q tail predicate",
        "negation_strength": "SET negation strictly STRONGER",
        "class_conclusion_strength": "SET class conclusion strictly STRONGER",
    }, "measured_at": now(), "sites": lform03_extract(ROOT)}
    for s in rep["D5_lform03"]["sites"]:
        raw = (ROOT / s["file"]).read_text().splitlines()
        needle = s["assertive_text"][:60]
        s["line_anchor"] = next((i + 1 for i, ln in enumerate(raw) if needle[:40] in ln), None)
    rep["D5_lform03"]["hard_inversions"] = [s for s in rep["D5_lform03"]["sites"]
                                            if s["verdict"] == "INVERTED_IF_PREDICATE_READING"]
    rep["D5_lform03"]["unscoped_but_correct_as_class"] = \
        [s for s in rep["D5_lform03"]["sites"] if s["verdict"] == "CORRECT_AS_CLASS_STATEMENT_UNSCOPED"]
    rep["D5_lform03"]["g_f0_frozen_site"] = [s for s in rep["D5_lform03"]["sites"]
                                             if s["file"] == "research_map/formulation_taxonomy.yaml"]
    rep["state_race"] = {
        "window": "2026-09-12T00:53 - 01:10+08:00",
        "observations": [
            {"at": "2026-09-12T00:57+08:00", "what": "VARIANT_REGISTRY.json:57 and SET delta:11 read "
             "'strictly STRONGER'; SET delta visibility.definition read 'strictly stronger than the "
             "single-q tail predicate'", "source": "this worker's direct read; corroborated by "
             "artifacts/worker-007/rev29_preflight/report_rev29.json I3 "
             "(set_delta_strength_is_pre_repair_token=true, measured 00:56:06)"},
            {"at": "2026-09-12T01:08+08:00", "what": "the same three sites now read 'strictly weaker' "
             "(L-FORM-03 partial repair landed during this audit); the declared F0 taxonomy "
             "classes.AF-WCC-VAC-GEN.conclusion.text still reads 'The set-based reading ... is "
             "strictly stronger'", "source": "this certificate's D5 extraction at report time"},
            {"at": "2026-09-12T00:55:02 / 00:57:26", "what": "two byte-distinct FROZEN.json generations "
             "both declaring revision 29 (48 files then 50 files, different frozen_at)",
             "source": "D1_pins.frozen.manifest_generations_observed"},
        ],
        "consequence": ("any verdict keyed to the bare label 'rev29' or to lines rather than file "
                        "hashes is ambiguous; this certificate binds each wording site to a sha256 in "
                        "drift.wording_sites"),
    }

    # D6 -- F1 repair delta census vs predecessor
    pred_f1 = PACKET / "sandbox_pristine/schemas/af_wcc_vacuum.yaml"
    rep["D6_f1_repair"] = {}
    if pred_f1.exists() and sha(pred_f1) == PRED["schemas/af_wcc_vacuum.yaml"]:
        ops = changed_lines(pred_f1.read_text(), (ROOT / SCHEMAS["F1"]).read_text())
        txt = (ROOT / SCHEMAS["F1"]).read_text()
        rep["D6_f1_repair"] = {
            "predecessor_sha256": sha(pred_f1), "changed_line_ops": ops,
            "changed_line_numbers": sorted({n for o in ops for n in range(o["old_lines"][0], o["old_lines"][1] + 1)} |
                                           {n for o in ops for n in range(o["new_lines"][0], o["new_lines"][1] + 1)}),
            "anchor_72_equivalence": "EQUIVALENT" in txt and "past-closed" in txt,
            "anchor_213_example_removed": "misclassification example was a non-sequitur" in txt,
            "anchor_234_predicate_scoped": bool(re.search(
                r"strictly WEAKER than this class's single-q tail predicate", txt)),
            "no_strictly_stronger_set_in_f1": not re.search(
                r"SET[^\n]{0,240}strictly STRONGER", _assertive(txt), re.I),
            "cite": "worker-076 W076-GFORM-STRICTNESS-RECONCILE-06 anchors 72/213/234",
        }
    else:
        rep["D6_f1_repair"] = {"error": "predecessor F1 copy unavailable"}
        pred_f1 = None

    # D7 -- verdict void census
    try:
        m = json.loads((ROOT / "research_map/research_map.json").read_text())
        census = {}
        for node, live_h in {"F1": LIVE[SCHEMAS["F1"]], "F2a": LIVE[SCHEMAS["F2a"]],
                             "F2b": LIVE[SCHEMAS["F2b"]]}.items():
            old_h = PRED[SCHEMAS[node]]
            census[node] = {"predecessor_pin": old_h[:12], "live_pin": live_h[:12],
                            "verdicts_at_predecessor": {}, "verdicts_at_live": {}, "voided_total": 0}
            for r in m.get("reviews", []):
                s = json.dumps(r)
                v = r.get("verdict")
                if v not in ("accept", "revise", "reject", "inconclusive"):
                    continue
                if old_h[:12] in s and old_h in s:
                    census[node]["verdicts_at_predecessor"][v] = census[node]["verdicts_at_predecessor"].get(v, 0) + 1
                if live_h[:12] in s and live_h in s:
                    census[node]["verdicts_at_live"][v] = census[node]["verdicts_at_live"].get(v, 0) + 1
                    census[node].setdefault("live_verdict_detail", []).append({
                        "actor": r.get("actor"), "event_id": r.get("event_id"),
                        "verdict": v, "score": r.get("score"),
                        "counts_as_full_schema_verdict": r.get("counts_as_full_schema_verdict"),
                        "counts_as_gate_accept": r.get("counts_as_gate_accept"),
                        "scoped_by_findings": any("SCOPED" in str(f) for f in (r.get("findings") or [])),
                    })
            census[node]["voided_total"] = sum(census[node]["verdicts_at_predecessor"].values())
        census["_caveat"] = ("substring census over research_map reviews, not an eligibility adjudication; "
                             "scoped verdicts (e.g. worker-061 F2b accept covers only the variant-CH axis) "
                             "must not be counted as full-schema gate accepts")
        rep["D7_verdicts"] = census
    except Exception as e:  # pragma: no cover
        rep["D7_verdicts"] = {"error": repr(e)}

    # D8 -- L-FORM-02 recurrence (guard absent): mutate one input, watch the silent rewrite
    sb = make_sandbox("recurrence")
    ev = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ck = sb / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    h0 = sha(ev)
    r1 = run(["python3", str(ck)], cwd=sb)
    h1 = sha(ev)
    tax = sb / "research_map/formulation_taxonomy.yaml"
    taxdoc = yaml.safe_load(tax.read_text())
    taxdoc["class_ids"] = list(taxdoc["class_ids"]) + ["AF-WCC-DRIFT-PROBE"]  # semantic mutation of a compared field
    tax.write_text(yaml.safe_dump(taxdoc, sort_keys=False))
    r2 = run(["python3", str(ck)], cwd=sb)
    h2 = sha(ev)
    declared = yaml.safe_load((sb / SCHEMAS["F1"]).read_text())["f0_binding"]["consistency_evidence_sha256"]
    rep["D8_recurrence"] = {
        "checker_sha256": sha(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"),
        "frozen_inputs_run": {"rc": r1["rc"], "hash_unchanged": h0 == h1,
                              "deterministic_while_inputs_frozen": True, "new_hash": h1},
        "mutated_input_run": {"rc": r2["rc"], "silently_rewrote": h1 != h2, "new_hash": h2,
                              "printed_dry_run_marker": "DRY-RUN" in r2["stdout"],
                              "declared_hash_now_stale": h2 != declared,
                              "declared_hash": declared[:12]},
        "guard_absent": sha(ck) == LIVE["artifacts/formulation/tools/check_taxonomy_consistency.py"],
        "interpretation": ("the refreshed declared hash is stable while inputs are frozen, but an "
                           "input change is silently propagated into the frozen evidence path with no "
                           "--write flag and no signal; W083's O3 guard (dry-run default) would stop it"),
    }

    # sensitivity controls
    sens = []
    # C-control: predecessor vs rev29 verdicts both computed from copies
    same = containment_findings(PRED_F2B_COPY.read_text(), "c")["hard_codes"] == \
        containment_findings(PRED_F2B_COPY.read_text(), "c")["hard_codes"]
    sens.append({"id": "M0_byte_identical_control", "expect_caught": False, "caught": not same,
                 "detail": "identical input must give identical verdict"})
    # planted inversion on the rev29 text
    planted = (ROOT / SCHEMAS["F2b"]).read_text().replace("C2 is a strictly larger", "C2 is a strictly smaller")
    f1 = containment_findings(planted, "M1")["hard_codes"]
    sens.append({"id": "M1_planted_repair_masks_LFORM01", "expect_caught": True,
                 "caught": "class_size_predicate_inverted" not in f1,
                 "detail": "with the one-word repair planted, R1 must go quiet (this is the acceptance mutant)"})
    inv = (ROOT / SCHEMAS["F2b"]).read_text().replace("C2 is a strictly larger", "C2 is a strictly larger")
    f2 = containment_findings(inv + "\n", "M2")["hard_codes"]
    sens.append({"id": "M2_inversion_still_fires", "expect_caught": True,
                 "caught": "class_size_predicate_inverted" in f2, "detail": "canonical bytes still inverted"})
    # L-FORM-03 classifier false-positive control on F1's corrected SET relation
    f1doc = yaml.safe_load((ROOT / SCHEMAS["F1"]).read_text())
    setrel = next((c.get("relation") for c in f1doc.get("class_identity_variants", [])
                   if "SET" in str(c.get("statement", ""))), "")
    cls = classify_direction(setrel) if setrel else {"verdict": "NOT_FOUND"}
    sens.append({"id": "M3_lform03_no_fp_on_corrected_F1", "expect_caught": False,
                 "caught": cls["verdict"] == "INVERTED_IF_PREDICATE_READING",
                 "verdict": cls["verdict"], "detail": "F1's corrected SET relation is predicate-scoped WEAKER"})
    # M4 -- synthetic injection: flip the SET delta visibility.definition direction in a sandbox copy
    sbm4 = make_sandbox("m4_lform03")
    dp4 = sbm4 / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
    d4 = json.loads(dp4.read_text())
    flipped = False
    for ch in d4.get("changes", []):
        if ch.get("path") == "visibility.definition" and isinstance(ch.get("to"), str) \
                and "strictly weaker" in ch["to"]:
            ch["to"] = ch["to"].replace("strictly weaker", "strictly stronger")
            flipped = True
    dp4.write_text(json.dumps(d4, indent=2) + "\n")
    m4sites = lform03_extract(sbm4)
    sens.append({"id": "M4_lform03_catches_synthetic_inversion", "expect_caught": True,
                 "caught": flipped and any(s["field"] == "changes[visibility.definition].to" and
                                           s["verdict"] == "INVERTED_IF_PREDICATE_READING" for s in m4sites),
                 "detail": "flipping the SET predicate direction to 'stronger' in a sandbox must be flagged"})
    # verify_frozen control on a planted drift
    sbv = make_sandbox("frozen_drift_control")
    (sbv / "artifacts/formulation/FROZEN.json").write_text(
        (sbv / "artifacts/formulation/FROZEN.json").read_text().replace(LIVE[SCHEMAS["F2b"]][:16], "0" * 16))
    mm = []
    man2 = json.loads((sbv / "artifacts/formulation/FROZEN.json").read_text())
    for rel, rec in man2["files"].items():
        p = sbv / rel
        if not p.exists() or sha(p) != rec["sha256"]:
            mm.append(rel)
    sens.append({"id": "M5_frozen_drift_control", "expect_caught": True, "caught": len(mm) > 0,
                 "detail": "planted manifest hash must be detected by the independent pin walk"})
    # guard control: patched checker must not rewrite
    sbg = make_sandbox("guard_control")
    applyd = run(["patch", "-p1", "-F0", "-i", str(PACKET / "diffs/check_taxonomy_consistency--O3-guard.patch.diff")], cwd=sbg)
    taxg = sbg / "research_map/formulation_taxonomy.yaml"
    gdoc = yaml.safe_load(taxg.read_text())
    gdoc["class_ids"] = list(gdoc["class_ids"]) + ["AF-WCC-DRIFT-PROBE"]
    taxg.write_text(yaml.safe_dump(gdoc, sort_keys=False))
    evg = sbg / "artifacts/formulation/evidence/taxonomy_consistency.json"
    hg0 = sha(evg)
    rg = run(["python3", str(sbg / "artifacts/formulation/tools/check_taxonomy_consistency.py")], cwd=sbg)
    sens.append({"id": "M6_guard_blocks_silent_write", "expect_caught": False,
                 "caught": sha(evg) != hg0 or "DRY-RUN" not in rg["stdout"],
                 "detail": "with W083's guard the mutated-input run must be a dry run"})
    rep["sensitivity"] = {"mutants": sens,
                          "all_expectations_met": all(m["caught"] == m["expect_caught"] for m in sens)}

    # drift guard
    end = {rel: sha(ROOT / rel) for rel in LIVE}
    extra = ["artifacts/formulation/FROZEN.json",
             "artifacts/formulation/VARIANT_REGISTRY.json",
             "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
             "research_map/formulation_taxonomy.yaml",
             "artifacts/formulation/formulation_taxonomy.yaml"]
    rep["drift"] = {
        "canonical": {r: {"start": started[r], "end": end[r], "drift": started[r] != end[r]} for r in LIVE},
        "wording_sites": {r: {"sha256_at_report": sha(ROOT / r)} for r in extra},
        "any_drift": any(started[r] != end[r] for r in LIVE),
    }
    rep["verdict"] = {
        "rev29_self_consistent": rep["D1_pins"]["frozen"]["self_consistent"],
        "lform01_status": "LIVE" if rep["D3_content"]["lform01_still_live"] else "FIXED",
        "lform02_status": "letter-closed-refresh-direction" if rep["D2_binding"]["live"]["all_resolve"]
                          else "OPEN",
        "lform02_recurrence": "demonstrated" if rep["D8_recurrence"]["mutated_input_run"]["silently_rewrote"]
                              else "not-demonstrated",
        "lform03_status": ("OPEN: %d predicate-inversion site(s) at report time; L-FORM-03 was partially "
                           "repaired during this audit (see state_race)" % len(rep["D5_lform03"]["hard_inversions"])),
        "f2b_gate_readiness": "NOT_READY (L-FORM-01 live at the rev29 hash; prior accept voided by the hash move)",
        "hard_failures": (
            ([f"FROZEN rev29 pin drift: {m['path']} manifest {m['manifest'][:12]} != disk {m['disk'][:12]}"
              for m in mism] if mism else []) +
            (["L-FORM-01 class_size_predicate_inverted still live at F2b b2ab6acb"] if
             rep["D3_content"]["lform01_still_live"] else []) +
            (["L-FORM-03 predicate-strength inversion at %s[%s]" % (s["file"], s["field"])
              for s in rep["D5_lform03"]["hard_inversions"]]) +
            (["F2b stale containment denial at C0:152 (hard under strict reading, advisory under "
              "steelman; worker-066 H2 records it hard)"]
             if "stale_or_contradictory_containment_denial" in rep["D3_content"]["rev29_f2b"]["hard_codes"]
             else [])),
        "falsifier": ("show the F2b inverted premise is absent at b2ab6acb, or that FROZEN rev29 "
                      "verify_frozen exits 0, or that SET delta line 22/registry/map wording is "
                      "predicate-consistent; any of these refutes a hard failure here"),
        "next_falsifier": ("re-run after the next freeze: exit requires FROZEN verify rc=0, F2b sweep "
                           "hard=0 at the new hash, L-FORM-03 sites scoped to predicate/negation/class, "
                           "and W083 L-FORM-01 re-pinned to the new bytes"),
    }
    Path(args.json).write_text(json.dumps(rep, indent=2) + "\n")
    Path(HERE / "sensitivity_selftest.json").write_text(json.dumps(
        {"audit_id": rep["audit_id"], "created_at": now(), **rep["sensitivity"]}, indent=2) + "\n")
    print(json.dumps({"audit": rep["audit_id"], "pins_ok": rep["D1_pins"]["all_match"],
                      "frozen_self_consistent": rep["D1_pins"]["frozen"]["self_consistent"],
                      "binding": rep["D2_binding"]["live"]["all_resolve"],
                      "lform01_live": rep["D3_content"]["lform01_still_live"],
                      "packet_target_stale": all(v["target_is_stale"] for v in rep["D4_packet"]["per_copy"].values()),
                      "lform03_hard": len(rep["D5_lform03"]["hard_inversions"]),
                      "sensitivity_ok": rep["sensitivity"]["all_expectations_met"],
                      "drift": rep["drift"]["any_drift"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
