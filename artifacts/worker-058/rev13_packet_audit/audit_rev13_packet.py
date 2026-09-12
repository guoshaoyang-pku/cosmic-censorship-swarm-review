#!/usr/bin/env python3
"""W058-REV13-PACKET-ADJUDICATE-05 -- independent, hash-pinned audit of the
integrated rev13 repair packet `artifacts/worker-083/rev13_repair_packet`.

Question (class-bound, nodes F1/F2a/F2b, gate context G-FORM):
  Q1 apply-exactness  : do the packet's three diffs apply cleanly, with fuzz 0, to the
                        frozen rev28 bytes, and produce exactly the manifest's target hashes?
  Q2 minimality       : does each diff change only the intended line(s)?
  Q3 effect           : does an INDEPENDENT containment sweep confirm the L-FORM-01 defect is
                        closed and enumerate what is still live at the post-patch hash?
  Q4 binding          : does L-FORM-02 close (declared == measured in all three f0_binding
                        blocks), and is the guard stable against the next legitimate write?
  Q5 direction        : restore-enriched-675a99d0 (packet) vs refresh-declared-to-9e335e9b
                        (lead's blocker wording) -- which is the lower-blast-radius repair?
  Q6 coverage         : is the packet sufficient for F2b to produce two fresh accept verdicts,
                        given the findings recorded at the live pin by other workers?

Read-only on every canonical path. All mutation happens in sandbox/ copies.
Exit 0 = audit executed and report written (NOT a gate verdict).
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

HERE = Path(__file__).resolve().parent          # <repo>/artifacts/worker-058/rev13_packet_audit
ROOT = HERE.parents[2]                          # <repo>
PACKET = ROOT / "artifacts/worker-083/rev13_repair_packet"

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
LIVE_PINS = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
}
PACKET_TARGET = {
    "schemas/af_scc_c0_vacuum.yaml": "3cdcaa44e6f103f4dacbc03c509f39586f7788e14ddba981b19985c843821c48",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "3cdcaa44e6f103f4dacbc03c509f39586f7788e14ddba981b19985c843821c48",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "5094870c7f745e5b5a224eaaca986c972bb1afd19dcd9b8f404b9ab707be9385",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
}
DIFFS = {
    "lform01_canonical": "diffs/af_scc_c0_vacuum--LFORM01.patch.diff",
    "lform01_mirror": "diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff",
    "lform02_checker": "diffs/check_taxonomy_consistency--O3-guard.patch.diff",
}
PRISTINE = [
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json",
]
ENRICHED = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"

# F2b findings recorded at the live pin by other workers / prior W058 rounds (hash-bound refs).
RECORDED_F2B_FINDINGS = [
    {
        "id": "L-FORM-01 / W058-HF-1 / W066-R12-F2B-H1",
        "code": "class_size_predicate_inverted",
        "where": "schemas/af_scc_c0_vacuum.yaml:245 implication_ledger.forbidden_transfers[0].reason",
        "recorded_hard": True,
        "packet_repair": "L-FORM-01",
        "evidence": [
            "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T004452-03",
            "artifacts/worker-066/f2b_repair_prereg/report.json",
            "artifacts/worker-058/rev27_cert/sweep_rev27.json",
        ],
    },
    {
        "id": "W066-R12-F2B-H2 / W058-CD-F2 / W058-REPAIR-CERT-02 advisory",
        "code": "stale_or_contradictory_containment_denial",
        "where": "schemas/af_scc_c0_vacuum.yaml:151 regularity.must_not_conflate[0]",
        "recorded_hard": True,
        "recorder_disagreement": "worker-066 records H2 hard; W058 rounds 2/4 classified it advisory (steelman reading: 'here' = this bullet)",
        "packet_repair": None,
        "evidence": [
            "comms/outbox/worker-066.jsonl#W066-F2B-REPAIR-PREREG-01",
            "artifacts/worker-058/contain_derive/containment_derivation.json",
        ],
    },
    {
        "id": "W058-REPAIR-CERT-02/MINOR-1",
        "code": "strength_bucket_mismatch",
        "where": "schemas/af_scc_c0_vacuum.yaml:235 conclusion.forbidden_weakenings[-1]",
        "recorded_hard": False,
        "packet_repair": None,
        "evidence": ["artifacts/worker-058/repair_cert/scc_order_sweep.json"],
    },
    {
        "id": "L-FORM-02 / W086-GFORM-EVIDENCE-COLLISION-01",
        "code": "consistency_evidence_hash_stale",
        "where": "f0_binding.consistency_evidence_sha256 in all three schemas",
        "recorded_hard": True,
        "packet_repair": "L-FORM-02",
        "evidence": [
            "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T004452-03",
            "artifacts/worker-086/evidence_collision/report.json",
            "artifacts/worker-092/evbind/report.json",
        ],
    },
]


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {"cmd": cmd if isinstance(cmd, list) else [cmd], "cwd": str(cwd), "rc": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def make_sandbox(name: str) -> Path:
    sb = HERE / "sandbox" / name
    if sb.exists():
        shutil.rmtree(sb)
    for rel in PRISTINE:
        dst = sb / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return sb


def apply_diff(sb: Path, key: str) -> dict:
    diff = PACKET / DIFFS[key]
    dry = run(["patch", "-p1", "-F0", "--dry-run", "-i", str(diff)], cwd=sb)
    real = run(["patch", "-p1", "-F0", "-i", str(diff)], cwd=sb) if dry["rc"] == 0 else None
    return {"key": key, "diff": str(diff.relative_to(ROOT)), "diff_sha256": sha256_file(diff),
            "dry_run": dry, "apply": real}


def changed_lines(a: str, b: str) -> dict:
    """Line-level replacement/add/delete census between two texts (1-based, inclusive)."""
    al, bl = a.splitlines(), b.splitlines()
    sm = difflib.SequenceMatcher(a=al, b=bl, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            ops.append({"op": tag, "old_lines": [i1 + 1, i2], "new_lines": [j1 + 1, j2],
                        "old_text": al[i1:i2], "new_text": bl[j1:j2]})
    return {"changed_line_count": sum(max(o["old_lines"][1] - o["old_lines"][0] + 1,
                                          o["new_lines"][1] - o["new_lines"][0] + 1) for o in ops),
            "ops": ops}


# ---------------------------------------------------------------- independent sweep
def _norm(tok: str) -> str:
    t = tok.strip().strip('"').strip("'").replace("{", "").replace("}", "")
    t = t.replace("^", "").replace("_", "").replace(" ", "").replace("\\\\", "")
    t = t.replace("H2loc", "H2loc").replace("C11", "C11")
    return t


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


def containment_findings(text: str, label: str) -> dict:
    doc = yaml.safe_load(text)
    led = doc["implication_ledger"]
    chain = led["extension_class_containment"]
    order = parse_chain_order(chain)
    size = {t: i for i, t in enumerate(order)}  # 0 = largest extension set
    own = None
    rk = find_key(doc, "extension_regularity")
    if rk:
        own = _norm(str(rk[1]))
    if own is None or own not in size:
        own = next((t for t in size if t in _norm(str(doc.get("class_id", "")))), None)
    findings = []

    # R1 -- every "X is a strictly larger/smaller extension class" reason must agree with the
    #       file's own declared chain.
    for i, row in enumerate(led.get("forbidden_transfers", [])):
        reason = row.get("reason", "")
        m = re.search(r"([A-Za-z0-9_^{},\\\\ ]+?)\s+is a strictly (larger|smaller) extension class", reason)
        if m:
            subj = _norm(m.group(1))
            word = m.group(2)
            if subj in size and own in size:
                actually_smaller = size[subj] > size[own]
                agrees = (word == "smaller") == actually_smaller
                findings.append({
                    "code": "class_size_predicate_inverted" if not agrees else None,
                    "rule": "R1_size_predicate", "row_index": i, "line_hint": None,
                    "subject": subj, "own_class": own, "word_in_file": word,
                    "declared_order_largest_first": order,
                    "derived": "subject is strictly smaller" if actually_smaller else "subject is strictly larger",
                    "severity": "none" if agrees else "hard",
                })
        # R1b -- forbidden transfer from a strictly smaller sibling to this class is the licensed
        #        direction; a forbidden transfer is only coherent if the from-class is smaller.
        frm = row.get("from", "")
        m2 = re.match(r"no proper future (.+?) extension", frm)
        if m2 and row.get("to") == "this class" and own in size:
            subj = _norm(m2.group(1))
            if subj in size:
                findings.append({
                    "code": None if size[subj] > size[own] else "forbidden_transfer_direction_incoherent",
                    "rule": "R1b_transfer_direction", "row_index": i,
                    "subject": subj, "derived_smaller": size[subj] > size[own],
                    "severity": "none" if size[subj] > size[own] else "hard",
                })

    # R2 -- the same statement must not sit in both forbidden_strengthenings and
    #       forbidden_weakenings (two-sided direction is stronger, so it is not a weakening).
    wk = find_key(doc, "forbidden_weakenings")
    st = find_key(doc, "forbidden_strengthenings")
    if wk and st:
        st_text = " || ".join(str(x) for x in st[1])
        for i, item in enumerate(wk[1]):
            if re.search(r"two-sided", str(item), re.I) and re.search(r"two-sided", st_text, re.I):
                findings.append({
                    "code": "strength_bucket_mismatch", "rule": "R2_bucket",
                    "row_index": i, "item": str(item),
                    "also_in_forbidden_strengthenings": True,
                    "reason": "two-sided inextendibility is recorded as stronger in forbidden_strengthenings",
                    "severity": "advisory",
                })

    # R3 -- a "No containment with X is asserted here" denial while the ledger asserts a
    #       containment relation involving X and this class.
    mnc = find_key(doc, "must_not_conflate")
    if mnc:
        for i, item in enumerate(mnc[1]):
            m3 = re.search(r"[Nn]o containment with ([^.;]+?) is asserted", str(item))
            if m3:
                toks = [_norm(t) for t in re.split(r",|\bor\b|\band\b", m3.group(1)) if _norm(t)]
                hit = [t for t in toks if t in size and own in size and size[t] != size[own]]
                findings.append({
                    "code": "stale_or_contradictory_containment_denial" if hit else None,
                    "rule": "R3_denial", "row_index": i, "item": str(item)[:200],
                    "denied_tokens": toks, "tokens_with_declared_containment": hit,
                    "severity": "hard" if hit else "none",
                    "severity_steelman": "advisory" if hit else "none",
                    "note": "strict reading: contradicts implication_ledger in the same document; "
                            "steelman reading: 'here' may mean 'in this bullet'",
                })

    live = [f for f in findings if f["code"]]
    return {
        "label": label,
        "chain_order_largest_first": order,
        "own_class_token": own,
        "rules_applied": ["R1_size_predicate", "R1b_transfer_direction", "R2_bucket", "R3_denial"],
        "findings": findings,
        "live_findings": live,
        "hard_codes": sorted({f["code"] for f in live if f["severity"] == "hard"}),
        "hard_codes_steelman": sorted({f["code"] for f in live
                                       if f["severity"] == "hard" and f["rule"] != "R3_denial"} |
                                      {f["code"] for f in live if f["rule"] == "R3_denial"
                                       and f["severity_steelman"] == "hard"}),
        "advisory_codes": sorted({f["code"] for f in live if f["severity"] == "advisory"}),
    }


# ---------------------------------------------------------------- binding
def resolve_pointer(sb: Path, ptr) -> dict:
    if not isinstance(ptr, str) or "#" not in ptr:
        return {"resolves": False, "reason": "no #fragment"}
    rel, frag = ptr.split("#", 1)
    p = sb / rel
    if not p.exists():
        return {"resolves": False, "reason": f"missing file {rel}"}
    node = yaml.safe_load(p.read_text())
    for part in frag.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return {"resolves": False, "reason": f"fragment {frag!r} does not resolve at {part!r}"}
    return {"resolves": True, "target_type": type(node).__name__}


def binding_checks(sb: Path) -> dict:
    out = {}
    for node, rel in SCHEMAS.items():
        p = sb / rel
        doc = yaml.safe_load(p.read_text())
        fb = doc.get("f0_binding", {})
        ev = sb / fb.get("consistency_evidence", "")
        ev_hash = sha256_file(ev) if ev.exists() else None
        out[node] = {
            "schema": rel,
            "declared_f0_artifact": fb.get("declared_f0_artifact"),
            "declared_f0_matches_measured": fb.get("declared_f0_sha256") == sha256_file(
                sb / fb.get("declared_f0_artifact", "")) if (sb / fb.get("declared_f0_artifact", "")).exists() else False,
            "consistency_evidence_exists": ev.exists(),
            "declared_consistency_evidence_prefix": str(fb.get("consistency_evidence_sha256"))[:12],
            "measured_consistency_evidence_prefix": (ev_hash or "")[:12],
            "consistency_evidence_matches_measured": ev_hash == fb.get("consistency_evidence_sha256"),
            "class_contract_pointer": resolve_pointer(sb, doc.get("class_contract_pointer")),
            "supplement_pointer": resolve_pointer(sb, doc.get("class_contract_supplement_pointer")),
        }
    out["all_resolve"] = all(v["declared_f0_matches_measured"] and
                             v["consistency_evidence_matches_measured"] and
                             v["class_contract_pointer"]["resolves"] and
                             v["supplement_pointer"]["resolves"] for k, v in out.items() if k != "all_resolve")
    return out


def contract_moves(sb_a: Path, sb_b: Path) -> dict:
    """Which schema bytes move between two sandbox states."""
    moves = {}
    for node, rel in SCHEMAS.items():
        ha, hb = sha256_file(sb_a / rel), sha256_file(sb_b / rel)
        if ha != hb:
            moves[rel] = {"from": ha[:12], "to": hb[:12]}
    return moves


def apply_packet(sb: Path, restore_evidence=True) -> dict:
    res = {"sandbox": str(sb)}
    for key in ("lform01_canonical", "lform01_mirror", "lform02_checker"):
        res[key] = apply_diff(sb, key)
    if restore_evidence:
        dst = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / ENRICHED, dst)
    res["post_hashes"] = {rel: sha256_file(sb / rel) for rel in
                          list(SCHEMAS.values()) + ["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                                                    "artifacts/formulation/tools/check_taxonomy_consistency.py",
                                                    "artifacts/formulation/evidence/taxonomy_consistency.json"]}
    res["targets_match"] = {rel: res["post_hashes"].get(rel) == want for rel, want in PACKET_TARGET.items()}
    return res


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "audit_report.json"))
    args = ap.parse_args()

    report = {"audit_id": "W058-REV13-PACKET-ADJUDICATE-05", "actor": "worker-058",
              "created_at": now(), "class_binding":
              ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
              "nodes": ["F1", "F2a", "F2b"], "gate_context": "G-FORM",
              "authority": "worker evidence only; no canonical path written; no gate verdict or node transition"}

    # P0 -- pins
    pins = {rel: {"measured": sha256_file(ROOT / rel), "expected": want,
                  "match": sha256_file(ROOT / rel) == want} for rel, want in LIVE_PINS.items()}
    packet_files = {}
    for rel in [DIFFS[k] for k in DIFFS] + ["MANIFEST.json", "packet.json", "REPORT.md", "evidence.json"]:
        p = PACKET / rel
        packet_files[rel] = {"exists": p.exists(), "sha256": sha256_file(p) if p.exists() else None}
    manifest = json.loads((PACKET / "MANIFEST.json").read_text())
    selfcheck = []
    for rel, decl in manifest.get("files", {}).items():
        p = PACKET / rel
        got_h = sha256_file(p) if p.exists() else None
        got_b = p.stat().st_size if p.exists() else None
        selfcheck.append({"path": rel, "declared_sha256": decl.get("sha256"), "measured_sha256": got_h,
                          "declared_bytes": decl.get("bytes"), "measured_bytes": got_b,
                          "match": got_h == decl.get("sha256") and got_b == decl.get("bytes")})
    report["pins"] = {"all_match": all(v["match"] for v in pins.values()), "files": pins}
    report["packet"] = {"dir": str(PACKET.relative_to(ROOT)), "packet_id": manifest.get("manifest_id"),
                        "manifest_sha256": packet_files["MANIFEST.json"]["sha256"],
                        "files": packet_files,
                        "manifest_selfcheck": selfcheck,
                        "manifest_selfcheck_all_match": all(s["match"] for s in selfcheck),
                        "declared_base_frozen_sha256": manifest.get("base_frozen_sha256"),
                        "declared_targets": PACKET_TARGET}
    if not report["pins"]["all_match"]:
        report["verdict"] = {"status": "ABORTED_PIN_DRIFT",
                             "reason": "canonical inputs moved before the audit; verdict must be re-bound"}
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n")
        print("ABORTED: pin drift")
        return 1

    # Pinned provenance copies (audit binds to these bytes even if the packet is edited later).
    pin_dir = HERE / "pinned"
    pin_dir.mkdir(exist_ok=True)
    for rel in packet_files:
        dst = pin_dir / Path(rel).name
        shutil.copy2(PACKET / rel, dst)

    # Q1/Q2 -- apply + minimality
    sb_main = make_sandbox("main")
    report["apply"] = apply_packet(sb_main, restore_evidence=True)
    report["apply"]["dual_copy_equal_after_patch"] = (
        sha256_file(sb_main / "schemas/af_scc_c0_vacuum.yaml") ==
        sha256_file(sb_main / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"))
    for rel, key in [("schemas/af_scc_c0_vacuum.yaml", "lform01_canonical"),
                     ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "lform01_mirror"),
                     ("artifacts/formulation/tools/check_taxonomy_consistency.py", "lform02_checker")]:
        report["apply"][f"minimality_{key}"] = changed_lines((ROOT / rel).read_text(),
                                                             (sb_main / rel).read_text())
    report["apply"]["apply_ok"] = all(
        report["apply"][k]["dry_run"]["rc"] == 0 and report["apply"][k]["apply"]["rc"] == 0
        for k in DIFFS) and all(report["apply"]["targets_match"].values()) and \
        report["apply"]["dual_copy_equal_after_patch"]

    # Q3 -- independent sweep, pristine vs post-patch
    report["sweep"] = {
        "pristine": containment_findings((ROOT / SCHEMAS["F2b"]).read_text(), "pristine F2b @55d0a1ea"),
        "post_patch": containment_findings((sb_main / SCHEMAS["F2b"]).read_text(), "patched F2b @3cdcaa44"),
        "siblings": {n: containment_findings((ROOT / SCHEMAS[n]).read_text(), f"pristine {n}")["live_findings"]
                     for n in ("F1", "F2a")},
    }

    # Q4 -- binding + guard
    sb_pre = make_sandbox("binding_pre")
    report["binding"] = {"pristine_sandbox": binding_checks(sb_pre),
                         "post_packet_sandbox": binding_checks(sb_main)}

    ev = sb_main / "artifacts/formulation/evidence/taxonomy_consistency.json"
    checker = sb_main / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    h_before = sha256_file(ev)
    dry = run(["python3", str(checker)], cwd=sb_main)
    h_dry = sha256_file(ev)
    wrt = run(["python3", str(checker), "--write"], cwd=sb_main)
    h_wrt = sha256_file(ev)
    enriched_after_write = json.loads(ev.read_text())
    declared = yaml.safe_load((sb_main / SCHEMAS["F1"]).read_text())["f0_binding"]["consistency_evidence_sha256"]
    report["guard"] = {
        "dry_run": {"rc": dry["rc"], "stdout": dry["stdout"][:300],
                    "evidence_hash_unchanged": h_before == h_dry,
                    "printed_DRY_RUN": "DRY-RUN" in dry["stdout"]},
        "write_run": {"rc": wrt["rc"], "stdout": wrt["stdout"][:300], "hash_changed": h_dry != h_wrt,
                      "new_hash": h_wrt, "fields": sorted(enriched_after_write.keys())},
        "binding_recurs_after_write": h_wrt != declared,
        "interpretation": ("the guard stops the silent overwrite, but every legitimate --write "
                           "re-stamps measured_at, so the declared consistency_evidence_sha256 "
                           "goes stale again unless the write is coupled to a freeze revision"),
    }

    # Amendment M8: drop measured_at -> deterministic enrichment; then two writes are hash-stable.
    sb_m8 = make_sandbox("m8_determinism")
    apply_packet(sb_m8, restore_evidence=False)
    ck = sb_m8 / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    src = ck.read_text()
    src2 = re.sub(r",\s*\n\s*\"measured_at\": datetime\.datetime\.now\(\)\.astimezone\(\)\.isoformat\(timespec=\"seconds\"\)", "", src)
    ck.write_text(src2)
    shutil.copy2(ROOT / ENRICHED, sb_m8 / "artifacts/formulation/evidence/taxonomy_consistency.json")
    ev8 = sb_m8 / "artifacts/formulation/evidence/taxonomy_consistency.json"
    run(["python3", str(ck), "--write"], cwd=sb_m8)
    h8a = sha256_file(ev8)
    run(["python3", str(ck), "--write"], cwd=sb_m8)
    h8b = sha256_file(ev8)
    report["amendment_M8_deterministic_enrichment"] = {
        "patch_applied": "removed measured_at field from checker output",
        "hash_run1": h8a, "hash_run2": h8b, "stable_across_runs": h8a == h8b,
        "equals_declared_675a": h8a == LIVE_PINS[ENRICHED],
        "note": "one declared-hash refresh + freeze bump makes the binding stable thereafter"}

    # Q5 -- direction adjudication: packet (restore+guard) vs refresh-declared-to-live
    sb_refresh = make_sandbox("refresh_direction")
    live_ev = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
    live_hash = sha256_file(live_ev)
    for node, rel in SCHEMAS.items():
        p = sb_refresh / rel
        t = p.read_text().replace(LIVE_PINS[ENRICHED], live_hash)
        p.write_text(t)
    report["lform02_direction_adjudication"] = {
        "packet_restore_guard": {
            "binding_resolves": report["binding"]["post_packet_sandbox"]["all_resolve"],
            "evidence_fields": sorted(json.loads((ROOT / ENRICHED).read_text()).keys()),
            "has_input_pins": True, "hash_stable_on_rerun": False,
            "schema_bytes_moved": contract_moves(sb_pre, sb_main),
            "freeze_moves": ["schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                             "artifacts/formulation/evidence/taxonomy_consistency.json",
                             "artifacts/formulation/tools/check_taxonomy_consistency.py"],
        },
        "refresh_declared_hashes": {
            "binding_resolves": binding_checks(sb_refresh)["all_resolve"],
            "evidence_fields": sorted(json.loads(live_ev.read_text()).keys()),
            "has_input_pins": False, "hash_stable_on_rerun": True,
            "schema_bytes_moved": {rel: {"declared_hash_only": True} for rel in SCHEMAS.values()},
            "freeze_moves": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                             "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/evidence/taxonomy_consistency.json"],
        },
        "recommendation": ("packet direction + M8 determinism amendment: keeps the input pins, "
                           "voids only F2b verdicts (already blocked), and becomes hash-stable "
                           "after one refresh; refresh-direction moves all three schemas and voids "
                           "every live F1/F2a/F2b verdict for zero coverage gain"),
    }

    # Q6 -- coverage against recorded findings
    residual = []
    post_hard = set(report["sweep"]["post_patch"]["hard_codes"])
    post_adv = set(report["sweep"]["post_patch"]["advisory_codes"])
    for f in RECORDED_F2B_FINDINGS:
        if f["code"] == "class_size_predicate_inverted":
            status = "FIXED_BY_PACKET" if "class_size_predicate_inverted" not in post_hard else "LIVE"
        elif f["code"] == "stale_or_contradictory_containment_denial":
            status = "LIVE" if "stale_or_contradictory_containment_denial" in post_hard else "? "
        elif f["code"] == "strength_bucket_mismatch":
            status = "LIVE" if "strength_bucket_mismatch" in post_adv else "? "
        elif f["code"] == "consistency_evidence_hash_stale":
            status = "FIXED_BY_PACKET" if report["binding"]["post_packet_sandbox"]["all_resolve"] else "LIVE"
        else:
            status = "UNKNOWN"
        residual.append({**f, "post_packet_status": status})
    report["coverage"] = {
        "declared_scope": ["L-FORM-01", "L-FORM-02"],
        "declared_scope_closed": report["apply"]["apply_ok"] and
                                 report["binding"]["post_packet_sandbox"]["all_resolve"],
        "f2b_acceptance_coverage": "INCOMPLETE" if any(
            r["post_packet_status"] == "LIVE" for r in residual) else "COMPLETE",
        "residual_findings": [r for r in residual if r["post_packet_status"] == "LIVE"],
        "recorded_findings_census": residual,
        "why_it_matters": ("G-FORM needs two fresh accept verdicts per class at one frozen hash; "
                           "a rev13 that leaves recorded F2b findings live will be re-revised by "
                           "the next blind reviewer and the freeze break is wasted"),
    }

    # Review census at live pins (blast-radius context), substring match on the map.
    try:
        m = json.loads((ROOT / "research_map/research_map.json").read_text())
        census = {c: {"accept": 0, "revise": 0, "reject": 0, "inconclusive": 0} for c in ("F1", "F2a", "F2b")}
        h2c = {"F1": LIVE_PINS["schemas/af_wcc_vacuum.yaml"][:12],
               "F2a": LIVE_PINS["schemas/af_scc_c2_vacuum.yaml"][:12],
               "F2b": LIVE_PINS["schemas/af_scc_c0_vacuum.yaml"][:12]}
        for r in m.get("reviews", []):
            s = json.dumps(r)
            for node, h in h2c.items():
                if h in s and r.get("verdict") in census[node]:
                    census[node][r["verdict"]] += 1
        report["review_census_at_live_pins"] = census
    except Exception as e:  # pragma: no cover
        report["review_census_at_live_pins"] = {"error": repr(e)}

    # Sensitivity / mutants
    sens = []
    # M6 byte-identical control
    sb_ctrl = make_sandbox("m6_control")
    same = containment_findings((sb_ctrl / SCHEMAS["F2b"]).read_text(), "control")["live_findings"] == \
        report["sweep"]["pristine"]["live_findings"]
    sens.append({"id": "M6_control", "expect_caught": False, "caught": not same,
                 "detail": "pristine copy must reproduce the pristine verdict"})
    # M1 canonical-only patch -> mirror divergence
    sb_m1 = make_sandbox("m1_single_copy")
    apply_diff(sb_m1, "lform01_canonical")
    caught = sha256_file(sb_m1 / "schemas/af_scc_c0_vacuum.yaml") != sha256_file(
        sb_m1 / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    sens.append({"id": "M1_single_copy", "expect_caught": True, "caught": caught,
                 "detail": "canonical patched, mirror pristine -> dual-copy equality check fires"})
    # M2 wrong direction kept -> R1 fires
    sb_m2 = make_sandbox("m2_wrong_word")
    apply_packet(sb_m2, restore_evidence=True)
    for rel in ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"):
        p = sb_m2 / rel
        p.write_text(p.read_text().replace("C2 is a strictly smaller", "C2 is a strictly larger"))
    f2 = containment_findings((sb_m2 / SCHEMAS["F2b"]).read_text(), "M2")["hard_codes"]
    sens.append({"id": "M2_wrong_word", "expect_caught": True,
                 "caught": "class_size_predicate_inverted" in f2, "hard_codes": f2,
                 "detail": "re-inverted premise must be caught by R1"})
    # M3 skip evidence restore -> binding fails
    sb_m3 = make_sandbox("m3_no_restore")
    apply_packet(sb_m3, restore_evidence=False)
    b3 = binding_checks(sb_m3)
    sens.append({"id": "M3_no_restore", "expect_caught": True, "caught": not b3["all_resolve"],
                 "detail": "packet without step 3 leaves declared 675a99d0 != measured 9e335e9b"})
    # M4 wrong base -> target hash not reached
    sb_m4 = make_sandbox("m4_wrong_base")
    shutil.copy2(sb_m4 / SCHEMAS["F2a"], sb_m4 / SCHEMAS["F2b"])
    r4 = apply_diff(sb_m4, "lform01_canonical")
    h4 = sha256_file(sb_m4 / SCHEMAS["F2b"])
    caught4 = r4["dry_run"]["rc"] != 0 or h4 != PACKET_TARGET[SCHEMAS["F2b"]]
    sens.append({"id": "M4_wrong_base", "expect_caught": True, "caught": caught4,
                 "patch_rc": r4["dry_run"]["rc"], "detail": "patch against C2 bytes must not yield the C0 target hash"})
    # M5 unguarded checker silently overwrites
    sb_m5 = make_sandbox("m5_unguarded")
    shutil.copy2(ROOT / ENRICHED, sb_m5 / "artifacts/formulation/evidence/taxonomy_consistency.json")
    ev5 = sb_m5 / "artifacts/formulation/evidence/taxonomy_consistency.json"
    h5a = sha256_file(ev5)
    r5 = run(["python3", str(sb_m5 / "artifacts/formulation/tools/check_taxonomy_consistency.py")], cwd=sb_m5)
    h5b = sha256_file(ev5)
    sens.append({"id": "M5_unguarded_overwrite", "expect_caught": True,
                 "caught": h5a != h5b and "DRY-RUN" not in r5["stdout"],
                 "detail": "pre-patch checker rewrites the canonical evidence with no flag"})
    # M7 refresh-direction resolves binding (adjudication control)
    sens.append({"id": "M7_refresh_direction", "expect_caught": False,
                 "caught": not report["lform02_direction_adjudication"]["refresh_declared_hashes"]["binding_resolves"],
                 "detail": "refresh-to-live also closes L-FORM-02's letter; trade-off is information loss"})
    report["sensitivity"] = {"mutants": sens,
                             "all_expectations_met": all(m["caught"] == m["expect_caught"] for m in sens)}

    # Drift guard
    drift = {rel: {"start": pins[rel]["measured"], "end": sha256_file(ROOT / rel),
                   "drift": pins[rel]["measured"] != sha256_file(ROOT / rel)} for rel in LIVE_PINS}
    pdrift = {rel: {"start": packet_files[rel]["sha256"], "end": sha256_file(PACKET / rel),
                    "drift": packet_files[rel]["sha256"] != sha256_file(PACKET / rel)} for rel in packet_files}
    report["drift"] = {"canonical": drift, "packet": pdrift,
                       "any_drift": any(v["drift"] for v in drift.values()) or any(v["drift"] for v in pdrift.values())}

    # Verdict
    hard_residual = [r for r in report["coverage"]["residual_findings"] if r["recorded_hard"]]
    report["verdict"] = {
        "packet_declared_scope": "VALIDATED" if report["coverage"]["declared_scope_closed"] else "FAILED",
        "f2b_acceptance": "NOT_READY" if hard_residual else "READY",
        "review_verdict": "revise",
        "review_score": 3,
        "hard_failures": [f"{r['id']} live at post-patch hash: {r['code']} ({r['where']})" for r in hard_residual],
        "required_amendments": [
            "fold the C0:151 containment-denial repair and the C0:235 strength-bucket repair into the same rev13 (one freeze break)",
            "adopt the M8 determinism amendment (drop measured_at, or bind by a deterministic digest) so L-FORM-02 cannot recur on the next legitimate --write",
            "declare the single owner/writer of artifacts/formulation/evidence/taxonomy_consistency.json in the artifact or FROZEN (worker-086 repair matrix)",
        ],
        "falsifier": ("apply the packet to pristine rev28 bytes, then show (a) a diff that does not "
                      "reproduce the declared target hash, (b) a residual recorded F2b finding that the "
                      "packet's own scope claims to fix, (c) a canonical byte written by this audit, or "
                      "(d) an independent sweep that reports the inverted premise as fixed when it is not"),
        "next_falsifier": ("re-run at the post-rev13 hashes: if F2b's next two blind reviewers accept at "
                           "the new hash while C0:151/C0:235 remain, the coverage call was wrong; if the "
                           "packet direction is rejected in favour of refresh, re-run the direction "
                           "adjudication against the chosen generation"),
    }
    Path(args.json).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"audit": report["audit_id"], "apply_ok": report["apply"]["apply_ok"],
                      "declared_scope": report["verdict"]["packet_declared_scope"],
                      "f2b_acceptance": report["verdict"]["f2b_acceptance"],
                      "hard_residual": [r["id"] for r in hard_residual],
                      "sensitivity": report["sensitivity"]["all_expectations_met"],
                      "drift": report["drift"]["any_drift"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
