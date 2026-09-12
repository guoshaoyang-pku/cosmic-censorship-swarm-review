#!/usr/bin/env python3
"""W043E-REV13-CLOSURE-01 -- post-repair binding-closure audit of the landed rev13 trio.

Class-bound to F1 AF-WCC-VAC-GEN, F2a AF-SCC-C2-VAC-GEN, F2b AF-SCC-C0-VAC-GEN.
Read-only on every canonical path.  The canonical consistency checker is executed
only against a scratch ROOT (it rewrites its own evidence file), never against the
canonical tree.

Question under test (the objective the repair card declares): after
astra-life05-evidence-binding-repair item (2) refreshed
f0_binding.consistency_evidence_sha256 in all three schemas to the live
artifacts/formulation/evidence/taxonomy_consistency.json 9e335e9ba1bf, is the
resulting f0_binding chain *closed* -- schema -> evidence -> F0 bytes -- or only
pointer-resolved?

Run:  python3 closure_probe.py
Out:  raw/*.json, report.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-043/w043e_rev13_closure -> repo root
RAW = HERE / "raw"
SCRATCH = HERE / "scratch"
CST = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(CST).replace(microsecond=0)
TS = NOW.isoformat()

TASK_ID = "W043E-REV13-CLOSURE-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F1", "F2a", "F2b"]
GATE = "G-FORM"

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF = {"F1": "AF-WCC-VAC-GEN", "F2a": "AF-SCC-C2-VAC-GEN", "F2b": "AF-SCC-C0-VAC-GEN"}
MIRRORS = {k: f"artifacts/formulation/schemas/{Path(v).name}" for k, v in SCHEMAS.items()}

F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
TOOL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
SET_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"

PIN_PATHS = [F0_CANON, F0_SUPP, EVIDENCE, FROZEN, TOOL, VOCAB, SET_DELTA,
             *SCHEMAS.values(), *MIRRORS.values()]

HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONSISTENCY_RE = re.compile(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"')
DECLARED_F0_RE = re.compile(r'declared_f0_sha256:\s*"([0-9a-f]{64})"')

checks: list[dict] = []
raw: dict[str, dict] = {}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def add(cid: str, status: str, detail: str, **data):
    entry = {"id": cid, "status": status, "detail": detail}
    if data:
        entry["data"] = data
    checks.append(entry)
    print(f"[{status:4}] {cid}: {detail}")


class DupLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently keeping the last."""


def _dup_mapping(loader, node, deep=False):
    loader.dup_keys = getattr(loader, "dup_keys", [])
    keys = []
    for key_node, _ in node.value:
        try:
            k = loader.construct_object(key_node, deep=deep)
        except Exception:
            k = repr(key_node)
        keys.append(k)
    for k in set(map(str, keys)):
        if sum(1 for x in keys if str(x) == k) > 1:
            loader.dup_keys.append(k)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_mapping)


def load_yaml_report(p: Path):
    loader = DupLoader(p.read_text())
    try:
        data = loader.get_single_data()
        dups = list(getattr(loader, "dup_keys", []))
    finally:
        loader.dispose()
    return data, dups


def measure_pins(paths):
    out = {}
    for rel in paths:
        p = ROOT / rel
        out[rel] = {"exists": p.exists(),
                    "sha256": sha256_file(p) if p.exists() else None,
                    "bytes": p.stat().st_size if p.exists() else None}
    return out


def chain_check(label: str, schema_text: str, evidence_bytes: bytes,
                measured_f0: str, measured_supp: str) -> dict:
    """The closure predicate: schema -> evidence -> F0 bytes.  Pure function of bytes."""
    m = CONSISTENCY_RE.search(schema_text)
    declared = m.group(1) if m else None
    ev_sha = sha256_bytes(evidence_bytes)
    try:
        ev = json.loads(evidence_bytes.decode("utf-8"))
    except Exception as exc:  # evidence must be JSON
        return {"label": label, "evidence_parse_error": str(exc), "chain_closed": False}
    pointer_resolves = bool(declared) and declared == ev_sha
    has_map = "map_taxonomy_sha256" in ev
    has_lead = "lead_contract_sha256" in ev
    has_at = "measured_at" in ev
    map_matches = has_map and ev["map_taxonomy_sha256"] == measured_f0
    lead_matches = has_lead and ev["lead_contract_sha256"] == measured_supp
    return {
        "label": label,
        "declared_evidence_sha256": declared,
        "measured_evidence_sha256": ev_sha,
        "pointer_resolves": pointer_resolves,
        "evidence_keys": sorted(ev.keys()),
        "evidence_has_map_taxonomy_sha256": has_map,
        "evidence_has_lead_contract_sha256": has_lead,
        "evidence_has_measured_at": has_at,
        "map_taxonomy_sha256_matches_measured_f0": map_matches,
        "lead_contract_sha256_matches_measured_supplement": lead_matches,
        "chain_closed": pointer_resolves and map_matches and lead_matches,
    }


def run_tool(scratch: Path, tag: str, timeout=180):
    tool = scratch / TOOL
    proc = subprocess.run([sys.executable, str(tool)], cwd=str(scratch),
                          capture_output=True, text=True, timeout=timeout)
    out_path = scratch / EVIDENCE
    b = out_path.read_bytes() if out_path.exists() else b""
    rec = {"tag": tag, "exit_code": proc.returncode, "stdout": proc.stdout.strip(),
           "stderr": proc.stderr.strip()[-800:], "output_sha256": sha256_bytes(b),
           "output_bytes": len(b)}
    raw[f"tool_{tag}"] = rec
    (RAW / f"tool_{tag}.json").write_text(json.dumps(rec, indent=2) + "\n")
    return rec, b


def build_scratch():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    for rel in (F0_CANON, F0_SUPP, VOCAB, TOOL):
        dst = SCRATCH / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    (SCRATCH / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    pins_start = measure_pins(PIN_PATHS)
    add("S0-PINS-START", "INFO", f"{len(pins_start)} pins measured",
        pins={k: v["sha256"] for k, v in pins_start.items()})

    # ---------------------------------------------------------------- S1 pointers
    live_f0 = pins_start[F0_CANON]["sha256"]
    live_supp = pins_start[F0_SUPP]["sha256"]
    live_ev_bytes = (ROOT / EVIDENCE).read_bytes()
    live_ev_sha = sha256_bytes(live_ev_bytes)
    add("S1-EVIDENCE-LIVE", "INFO",
        f"live evidence {live_ev_sha[:12]} ({len(live_ev_bytes)} B); "
        f"F0 {live_f0[:12]}; supplement {live_supp[:12]}",
        evidence_sha256=live_ev_sha, f0=live_f0, supplement=live_supp)

    live_chain = {}
    for label, rel in SCHEMAS.items():
        text = (ROOT / rel).read_text()
        _data, dups = load_yaml_report(ROOT / rel)
        ch = chain_check(label, text, live_ev_bytes, live_f0, live_supp)
        ch["schema_sha256"] = pins_start[rel]["sha256"]
        ch["yaml_duplicate_keys"] = dups
        live_chain[label] = ch
        raw[f"chain_live_{label}"] = ch
        add(f"S1-{label}-POINTER", "PASS" if ch["pointer_resolves"] else "FAIL",
            f"{CLASS_OF[label]}: declared {str(ch['declared_evidence_sha256'])[:12]} vs measured "
            f"{ch['measured_evidence_sha256'][:12]} -> resolves={ch['pointer_resolves']}",
            schema=rel, **{k: ch[k] for k in (
                "evidence_has_map_taxonomy_sha256", "evidence_has_lead_contract_sha256",
                "evidence_has_measured_at", "map_taxonomy_sha256_matches_measured_f0",
                "lead_contract_sha256_matches_measured_supplement", "chain_closed")})
        add(f"S1-{label}-TREEBIND", "PASS" if ch["chain_closed"] else "FAIL",
            f"{label}: evidence carries no F0-tree hash "
            f"(map_key={ch['evidence_has_map_taxonomy_sha256']}, "
            f"lead_key={ch['evidence_has_lead_contract_sha256']}) -> chain_closed="
            f"{ch['chain_closed']}")

    # ---------------------------------------------------- S2 scratch executables
    build_scratch()
    rec1, base_bytes = run_tool(SCRATCH, "run1")
    rec2, base2_bytes = run_tool(SCRATCH, "run2")
    durable = (rec1["output_sha256"] == rec2["output_sha256"] == live_ev_sha)
    add("S2-TOOL-DURABLE", "PASS" if durable else "FAIL",
        f"canonical tool run twice in scratch: {rec1['output_sha256'][:12]} / "
        f"{rec2['output_sha256'][:12]} (live {live_ev_sha[:12]}), exit "
        f"{rec1['exit_code']}/{rec2['exit_code']} -> byte-stable={durable}",
        stdout=rec1["stdout"], matches_live=base_bytes == live_ev_bytes)

    # S2b: mutate an UNCHECKED top-level field of F0 -> does the evidence move?
    f0_path = SCRATCH / F0_CANON
    f0_data = yaml.safe_load(f0_path.read_text())
    f0_data["w043e_probe_marker"] = "unchecked-field-mutation"
    f0_path.write_text(yaml.safe_dump(f0_data, sort_keys=False, allow_unicode=True))
    mutated_f0_hash = sha256_file(f0_path)
    rec3, mut_bytes = run_tool(SCRATCH, "f0_unchecked_mutation")
    raw["f0_unchecked_mutation"] = {"f0_before": live_f0, "f0_after": mutated_f0_hash,
                                    "evidence_unchanged": mut_bytes == base_bytes,
                                    "evidence_sha256": rec3["output_sha256"]}
    add("S2-EVIDENCE-INVARIANT", "FAIL" if mut_bytes == base_bytes else "PASS",
        f"F0 canonical mutated on an unchecked field ({live_f0[:12]} -> {mutated_f0_hash[:12]}); "
        f"tool output {'unchanged' if mut_bytes == base_bytes else 'changed'} "
        f"({rec3['output_sha256'][:12]}) -> the evidence hash is not a function of the F0 bytes",
        f0_before=live_f0, f0_after=mutated_f0_hash, evidence_sha256=rec3["output_sha256"])

    # S2c: mutate a COMPARED field -> tool must go INCONSISTENT (instrument can fail)
    f0_path.write_text((ROOT / F0_CANON).read_text())
    f0_data = yaml.safe_load(f0_path.read_text())
    f0_data["classes"]["AF-WCC-VAC-GEN"]["axes"]["family"] = "SCC"
    f0_path.write_text(yaml.safe_dump(f0_data, sort_keys=False, allow_unicode=True))
    rec4, cmp_bytes = run_tool(SCRATCH, "f0_compared_mutation")
    caught = rec4["exit_code"] != 0 and cmp_bytes != base_bytes
    raw["f0_compared_mutation"] = {"exit_code": rec4["exit_code"], "stdout": rec4["stdout"],
                                   "evidence_sha256": rec4["output_sha256"], "caught": caught}
    add("S2-COMPARED-MUTATION-CONTROL", "PASS" if caught else "FAIL",
        f"compared-field mutation: exit={rec4['exit_code']}, evidence moved="
        f"{cmp_bytes != base_bytes} -> tool detects compared differences={caught}",
        stdout=rec4["stdout"])
    f0_path.write_text((ROOT / F0_CANON).read_text())

    # ------------------------------- S3 minimal amendment: bind the evidence
    bound = json.loads(base_bytes.decode("utf-8"))
    for k in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at"):
        bound.pop(k, None)
    bound["map_taxonomy_sha256"] = sha256_file(SCRATCH / F0_CANON)
    bound["lead_contract_sha256"] = sha256_file(SCRATCH / F0_SUPP)
    bound["measured_at"] = "2026-09-12T00:53:20+08:00"
    bound_bytes = (json.dumps(bound, indent=2) + "\n").encode()
    bound_sha = sha256_bytes(bound_bytes)
    bound2_bytes = (json.dumps(json.loads(bound_bytes.decode()), indent=2) + "\n").encode()
    stable = sha256_bytes(bound2_bytes) == bound_sha
    (RAW / "evidence_bound_candidate.json").write_bytes(bound_bytes)
    add("S3-BOUND-EVIDENCE", "PASS" if stable else "FAIL",
        f"amended evidence adds map_taxonomy_sha256={bound['map_taxonomy_sha256'][:12]}, "
        f"lead_contract_sha256={bound['lead_contract_sha256'][:12]}, measured_at; "
        f"two renders byte-stable={stable}; candidate sha256={bound_sha[:12]}",
        candidate_sha256=bound_sha)

    # S3b: simulate the schema re-point (single-token substitution), then re-close
    repointed = {}
    (SCRATCH / "schemas_repointed").mkdir(parents=True, exist_ok=True)
    for label, rel in SCHEMAS.items():
        text = (ROOT / rel).read_text()
        n = text.count(live_ev_sha)
        new_text = text.replace(live_ev_sha, bound_sha)
        dst = SCRATCH / "schemas_repointed" / Path(rel).name
        dst.write_text(new_text)
        diff_chars = sum(1 for a, b in zip(text, new_text) if a != b)
        repointed[label] = {"occurrences": n, "changed_chars": diff_chars,
                            "sha256": sha256_file(dst)}
        added_checks = len(new_text.splitlines()) - len(text.splitlines())
        repointed[label]["added_lines"] = added_checks
    all_single = all(v["occurrences"] == 1 and v["added_lines"] == 0 for v in repointed.values())
    add("S3-REPOINT-MINIMAL", "PASS" if all_single else "FAIL",
        "each schema declares the evidence hash exactly once; re-point is a single-token "
        f"substitution with no line-count change: {[ (k, v['occurrences']) for k,v in repointed.items() ]}",
        repointed=repointed)
    raw["repointed"] = repointed

    amended_chain = {}
    for label, rel in SCHEMAS.items():
        text = (SCRATCH / "schemas_repointed" / Path(rel).name).read_text()
        ch = chain_check(label, text, bound_bytes,
                         sha256_file(SCRATCH / F0_CANON), sha256_file(SCRATCH / F0_SUPP))
        amended_chain[label] = ch
        raw[f"chain_amended_{label}"] = ch
    closed = all(c["chain_closed"] for c in amended_chain.values())
    add("S3-AMENDED-CLOSURE", "PASS" if closed else "FAIL",
        f"amended direction: chain_closed for all three classes = {closed}",
        amended_chains=amended_chain)

    # S3c tamper controls on the closure predicate itself
    tampered_schema = (SCRATCH / "schemas_repointed" / Path(SCHEMAS["F2a"]).name).read_text()
    bad = bound_sha[:-1] + ("0" if bound_sha[-1] != "0" else "1")
    t1 = chain_check("tamper-schema", tampered_schema.replace(bound_sha, bad), bound_bytes,
                     sha256_file(SCRATCH / F0_CANON), sha256_file(SCRATCH / F0_SUPP))
    ev_bad = json.loads(bound_bytes.decode())
    ev_bad["map_taxonomy_sha256"] = "0" * 64
    t2 = chain_check("tamper-evidence", tampered_schema,
                     (json.dumps(ev_bad, indent=2) + "\n").encode(),
                     sha256_file(SCRATCH / F0_CANON), sha256_file(SCRATCH / F0_SUPP))
    ctrl_ok = (not t1["pointer_resolves"]) and (not t2["chain_closed"])
    raw["predicate_controls"] = {"tampered_schema": t1, "tampered_evidence": t2}
    add("S3-PREDICATE-CONTROLS", "PASS" if ctrl_ok else "FAIL",
        f"tampered declared hash -> resolves={t1['pointer_resolves']}; "
        f"tampered tree hash -> chain_closed={t2['chain_closed']} (both must be False)")

    # ------------------------------------------------------------- S4 FROZEN rev29
    frozen = json.loads((ROOT / FROZEN).read_text())
    frozen_files = frozen.get("files", {})
    pin_rows = {}
    for label, rel in SCHEMAS.items():
        entry = frozen_files.get(rel, {})
        pin_rows[label] = {
            "canonical_pin": entry.get("sha256"),
            "canonical_measured": pins_start[rel]["sha256"],
            "canonical_match": entry.get("sha256") == pins_start[rel]["sha256"],
        }
        mrel = MIRRORS[label]
        pin_rows[label]["mirror_pin"] = frozen_files.get(mrel, {}).get("sha256")
        pin_rows[label]["mirror_measured"] = pins_start[mrel]["sha256"]
        pin_rows[label]["mirror_match"] = (pin_rows[label]["mirror_pin"]
                                           == pins_start[mrel]["sha256"])
    ev_pin = frozen_files.get(EVIDENCE, {}).get("sha256")
    tool_pin = frozen_files.get(TOOL, {}).get("sha256")
    pin_rows["evidence"] = {"pin": ev_pin, "measured": live_ev_sha, "match": ev_pin == live_ev_sha}
    pin_rows["tool"] = {"pin": tool_pin, "measured": pins_start[TOOL]["sha256"],
                        "match": tool_pin == pins_start[TOOL]["sha256"]}
    revision = frozen.get("revision")
    all_pins = all(v.get("canonical_match") and v.get("mirror_match") for v in pin_rows.values()
                   if isinstance(v, dict) and "canonical_match" in v) and \
        pin_rows["evidence"]["match"] and pin_rows["tool"]["match"]
    add("S4-FROZEN-REV29", "PASS" if revision == 29 and all_pins else "FAIL",
        f"FROZEN revision={revision} frozen_at={frozen.get('frozen_at')}; "
        f"rev13 pins + evidence + tool resolve={all_pins}", pins=pin_rows)
    raw["frozen_rev29"] = {"revision": revision, "frozen_at": frozen.get("frozen_at"),
                           "pins": pin_rows}

    # S4b: revision number is not a unique object -- detect a re-stamp of the same revision
    prev_frozen = None
    if (HERE / "report.json").exists():
        try:
            prev = json.loads((HERE / "report.json").read_text())
            prev_frozen = (prev.get("pins_end") or {}).get(FROZEN)
        except Exception:
            prev_frozen = None
    cur_frozen = pins_start[FROZEN]["sha256"]
    restamped = bool(prev_frozen and prev_frozen != cur_frozen)
    if restamped:
        raw["frozen_restamp"] = {"previous_pins_end": prev_frozen, "current": cur_frozen,
                                 "revision": revision, "frozen_at": frozen.get("frozen_at")}
        add("S4b-FROZEN-RESTAMP", "INFO",
            f"FROZEN file hash moved {prev_frozen[:12]} -> {cur_frozen[:12]} while revision "
            f"stayed {revision} (frozen_at={frozen.get('frozen_at')}); bind FROZEN by file hash, "
            f"not by the revision label", previous=prev_frozen, current=cur_frozen)

    # --------------------------------------------- S5 rev12 -> rev13 repair delta
    import difflib
    snap = ROOT / "artifacts/worker-043/f2a_rev12_verdict/snapshot"
    delta = {}
    allowed_prefixes = ("revised_at:", "revision:", "f0_binding:")
    for label, rel in SCHEMAS.items():
        old = snap / f"schemas__{Path(rel).name}"
        new = ROOT / rel
        if not old.exists():
            delta[label] = {"available": False}
            continue
        old_lines = old.read_text().splitlines()
        new_lines = new.read_text().splitlines()
        sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
        replaced, inserted, deleted, unexpected = [], [], [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            if tag == "replace":
                for k in range(max(i2 - i1, j2 - j1)):
                    o = old_lines[i1 + k] if i1 + k < i2 else None
                    n = new_lines[j1 + k] if j1 + k < j2 else None
                    row = {"old": (o or "")[:240], "new": (n or "")[:240]}
                    replaced.append(row)
                    is_meta = (o or "").lstrip().startswith(allowed_prefixes) or \
                        "revision_history" in (o or "") or '"index": 11' in (o or "")
                    is_f1_token = label == "F1" and ("STRONGER" in (o or "") or "misclassif" in (o or ""))
                    if not (is_meta or is_f1_token):
                        unexpected.append(row)
            elif tag == "insert":
                ins = [ln[:240] for ln in new_lines[j1:j2]]
                inserted.extend(ins)
                if not all(ln.lstrip().startswith(("  - {index: 11", "revised_at:", "revision:"))
                           or "index: 11" in ln or "rev13 delta" in ln for ln in ins):
                    unexpected.extend({"old": None, "new": ln} for ln in ins)
            elif tag == "delete":
                deleted.extend([ln[:240] for ln in old_lines[i1:i2]])
        delta[label] = {
            "available": True, "old_sha256": sha256_file(old), "new_sha256": sha256_file(new),
            "replaced": len(replaced), "inserted": len(inserted), "deleted": len(deleted),
            "unexpected_semantic_changes": unexpected,
            "changed_rows": replaced,
        }
    raw["rev12_to_rev13_delta"] = delta
    f1 = delta["F1"]
    f1_tokens = [c for c in f1.get("changed_rows", [])
                 if "STRONGER" in (c["old"] or "") or "STRONGER" in (c["new"] or "")]
    unexp = {k: v.get("unexpected_semantic_changes", []) for k, v in delta.items()}
    n_unexp = sum(len(v) for v in unexp.values())
    add("S5-REPAIR-DELTA", "PASS" if n_unexp == 0 else "FAIL",
        f"F1 {f1.get('replaced', 0)}R/{f1.get('inserted', 0)}I, "
        f"F2a {delta['F2a'].get('replaced', 0)}R/{delta['F2a'].get('inserted', 0)}I, "
        f"F2b {delta['F2b'].get('replaced', 0)}R/{delta['F2b'].get('inserted', 0)}I; "
        f"F1 strictness-token edits={len(f1_tokens)}; unexpected semantic changes={n_unexp}",
        delta={k: {"old": v.get("old_sha256"), "new": v.get("new_sha256"),
                   "replaced": v.get("replaced"), "inserted": v.get("inserted"),
                   "unexpected": v.get("unexpected_semantic_changes")}
               for k, v in delta.items()})

    # ------------------------------- S6 residual: F2b internal strength contradiction
    f2b_text = (ROOT / SCHEMAS["F2b"]).read_text().splitlines()
    cont_line = next((i + 1 for i, ln in enumerate(f2b_text)
                      if "strictly larger extension class" in ln), None)
    contain_line = next((i + 1 for i, ln in enumerate(f2b_text)
                         if "contains E_H2loc" in ln and "contains E_C2" in ln), None)
    # F2a has no such row (its forbidden_transfers name no size claim)
    f2a_text = (ROOT / SCHEMAS["F2a"]).read_text()
    residual = {
        "f2b_contradiction_line": cont_line,
        "f2b_containment_line": contain_line,
        "f2b_claim": f2b_text[cont_line - 1].strip() if cont_line else None,
        "f2b_containment": f2b_text[contain_line - 1].strip()[:220] if contain_line else None,
        "f2a_has_size_claim": "strictly larger extension class" in f2a_text,
        "f0_meaning_C2": "strictly larger classes" in (ROOT / F0_CANON).read_text(),
    }
    raw["residual_f2b"] = residual
    # direction audit: the file's own containment says E_C2 is innermost; the forbidden row says larger.
    f2b_self_contradiction = cont_line is not None and contain_line is not None and cont_line > contain_line
    add("S6-F2B-RESIDUAL", "FAIL" if f2b_self_contradiction else "PASS",
        f"F2b line {cont_line} still reads 'C2 is a strictly larger extension class' while "
        f"line {contain_line} states E_C0 contains ... contains E_C2 -> self-contradictory "
        f"strength claim at rev13 (worker-083 L-FORM-01, fleet SIZE_CLAIM hard defect)",
        residual=residual)

    # ------------------------------------------- S7 reviewer coverage not discharged
    hits = []
    for f in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        s = json.dumps(d)
        if ("map_taxonomy_sha256" in s or "lead_contract_sha256" in s
                or "does not bind the F0" in s or "hashless" in s):
            ids = []
            for h in (d.get("hard_failures") or []):
                if isinstance(h, dict) and any(k in json.dumps(h) for k in
                                               ("map_taxonomy_sha256", "lead_contract_sha256",
                                                "does not bind", "hashless")):
                    ids.append({"id": h.get("id"), "severity": h.get("severity")})
            hits.append({"file": f"reviews/{f.name}", "reviewer": d.get("reviewer"),
                         "verdict": d.get("verdict"),
                         "binding_findings": ids[:3],
                         "reviewed_sha256": str(d.get("reviewed_sha256")
                                                or d.get("artifact_sha256") or "")[:16]})
    raw["reviewer_binding_findings"] = hits
    add("S7-REVIEWER-COVERAGE", "INFO",
        f"{len(hits)} review files carry a tree-hash/binding finding that the landed refresh "
        f"does not discharge (evidence still lacks the keys)", files=[h["file"] for h in hits][:12])

    # ------------------------------------------------------------- S8 window close
    pins_end = measure_pins(PIN_PATHS)
    drift = {k: {"start": pins_start[k]["sha256"], "end": pins_end[k]["sha256"]}
             for k in PIN_PATHS if pins_start[k]["sha256"] != pins_end[k]["sha256"]}
    add("S8-WINDOW", "PASS" if not drift else "FAIL",
        f"moving-target guard: {len(drift)} of {len(PIN_PATHS)} pins drifted during the window",
        drift=drift)
    raw["window"] = {"start": pins_start, "end": pins_end, "drift": drift}

    # ------------------------------------------------------------------- report
    live_closed = all(c["chain_closed"] for c in live_chain.values())
    findings = [
        {
            "id": "HF-W043E-1",
            "severity": "blocking-for-clean-accept",
            "axis": "f0_binding closure (all three classes)",
            "finding": (
                "The landed rev13 repair resolves the pointer but does not close the chain. "
                "F1/F2a/F2b now declare consistency_evidence_sha256=9e335e9ba1bf and the live "
                "evidence measures 9e335e9ba1bf (pointer PASS), but that evidence document "
                "carries no map_taxonomy_sha256, no lead_contract_sha256 and no measured_at, so "
                "it cannot be tied to the declared F0 bytes 0abb9ed8a961 or the supplement "
                "d7419b4e8963. Execution controls: (a) the canonical tool is byte-deterministic "
                "on unchanged inputs (9e335e9b twice), so the pointer is durable but nominal; "
                "(b) mutating an unchecked F0 field changes the F0 hash while the tool output "
                "stays byte-identical -- the evidence hash is not a function of the F0 bytes; "
                "(c) mutating a compared field does change the output, so the gap is specifically "
                "the missing input-hash binding, not a blind checker. The rev27 closure item (e) "
                "regression reported by F1-review-090 F090-05, F2b-rev12-069 HF-069F2B-I09, "
                "F2a-review-19 HF-19-F2A-3, F2a-review-043 HF-043-2 and F2b-review-022 therefore "
                "survives the landed repair."),
            "repair": (
                "Complete the refresh with the binding: emit map_taxonomy_sha256, "
                "lead_contract_sha256 and measured_at in the consistency evidence (the writer is "
                "de356d999ea3, unchanged by the repair), re-run once, then re-point the three "
                "schemas' consistency_evidence_sha256 to the new evidence hash and publish FROZEN "
                "rev30. The tested minimal candidate is raw/evidence_bound_candidate.json "
                f"({bound_sha[:12]}); re-pointing each schema is a single-token substitution "
                "(no line-count change) and the simulated chain_closed predicate is True for all "
                "three classes. Alternative: land worker-083's W083-REV13-REPAIR-PACKET-01 "
                "L-FORM-02 (enriched writer + restored 675a99d0) instead, which keeps the schema "
                "bytes and moves only FROZEN."),
            "falsifier": ("Re-measure at the landed bytes: falsified if the live evidence "
                          "document contains map_taxonomy_sha256/lead_contract_sha256 whose "
                          "values equal the measured F0/supplement hashes, or if a clean "
                          "check_taxonomy_consistency.py run produces such a document."),
            "evidence_refs": ["raw/chain_live_F1.json", "raw/chain_live_F2a.json",
                              "raw/chain_live_F2b.json", "raw/tool_run1.json",
                              "raw/f0_unchecked_mutation.json",
                              "raw/evidence_bound_candidate.json"],
        },
        {
            "id": "HF-W043E-2",
            "severity": "hard (residual at rev13, corroborates worker-083 L-FORM-01)",
            "axis": "AF-SCC-C0-VAC-GEN internal strength relation",
            "finding": (
                f"schemas/af_scc_c0_vacuum.yaml line {cont_line} still reads 'C2 is a strictly "
                f"larger extension class, so C2-inextendibility is strictly weaker' while line "
                f"{contain_line} in the same file states the containment 'E_C0 contains E_H2loc "
                "contains E_{C^1,1} contains E_C2' and the one_way_entailments run C0 => H2loc "
                "=> C2. E_C2 is the innermost (smallest) extension set, so the row's reason is "
                "false and internally contradicts the file; the F2a sibling states the correct "
                "'converse containment is false' reason. Worker-083 W083-REV13-REPAIR-PACKET-01 "
                "L-FORM-01 specifies the same one-token repair and remains unapplied at rev13."),
            "repair": ("'strictly larger' -> 'strictly smaller' in "
                       "schemas/af_scc_c0_vacuum.yaml forbidden_transfers[0] and in the authoring "
                       "mirror, then re-freeze."),
            "falsifier": ("Falsified if E_C2 is not contained in E_C0 under the taxonomy's own "
                          "extension-set ordering, or if the live rev13 F2b row already reads "
                          "'strictly smaller'."),
            "evidence_refs": [f"{SCHEMAS['F2b']}#rev13", "raw/residual_f2b.json"],
        },
    ]
    report = {
        "schema": "w043e-postrepair-closure/v1",
        "task_id": TASK_ID,
        "worker": "worker-043",
        "created_at": TS,
        "gate": GATE,
        "node_ids": NODE_IDS,
        "class_ids": CLASS_IDS,
        "scope": ("Post-repair audit of astra-life05-evidence-binding-repair at the landed "
                  "rev13/FROZEN rev29 bytes: pointer resolution, evidence-to-F0 hash closure, "
                  "durability, minimal completion, and residual rev13 defects. Read-only on all "
                  "canonical paths; the canonical checker was executed only against a scratch "
                  "ROOT."),
        "verdict": "revise" if (not live_closed or f2b_self_contradiction) else "accept",
        "chain_closed_live": live_closed,
        "amended_chain_closed": closed,
        "check_count": len(checks),
        "checks": checks,
        "card_item_status": {
            "I1_taxonomy_cases_rebind": "not re-audited here (worker-007 preflight measured satisfied)",
            "I2_consistency_pointer": "pointer RESOLVED 3/3; evidence-to-F0 closure OPEN",
            "I3_F1_strictness_text": "tokens moved (3 F1 legs); correctness adjudication is "
                                     "worker-076/040/061 territory, not endorsed here",
            "I4_FROZEN_rev29": f"published revision={revision}, pins resolve={all_pins}",
        },
        "findings": findings,
        "reviewer_binding_findings": hits,
        "authority_note": ("Worker evidence only. This report cannot set a gate verdict, node "
                           "status or validation_status, and it is not one of the two binding "
                           "independent verdicts per class that G-FORM requires. No canonical "
                           "byte was modified."),
        "next_falsifier": ("Re-run closure_probe.py after the next repair: the finding is "
                           "discharged when the live evidence carries map_taxonomy_sha256 and "
                           "lead_contract_sha256 equal to the measured F0/supplement hashes and "
                           "all three schemas declare that evidence hash, with FROZEN pins "
                           "matching live bytes."),
        "moving_target": bool(drift),
        "pins_start": {k: v["sha256"] for k, v in pins_start.items()},
        "pins_end": {k: v["sha256"] for k, v in pins_end.items()},
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, obj in raw.items():
        (RAW / f"{name}.json").write_text(json.dumps(obj, indent=2, default=str) + "\n")
    print(f"\nverdict={report['verdict']} chain_closed_live={live_closed} "
          f"amended_chain_closed={closed} checks={len(checks)} drift={len(drift)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
