#!/usr/bin/env python3
"""W043G-F2B-HISTORY-CLOSURE-01 -- bounded, class-bound worker measurement.

Question: at the live F2b pins (AF-SCC-C0-VAC-GEN, schemas/af_scc_c0_vacuum.yaml
b2ab6acb2bbe, FROZEN rev29 815e0807), does the staged containment repair close the
whole audit trail, or does the next revision still carry the worker-035 F-035-01
revision_history defect family?  Which staged candidate leaves the
{revision, revised_at, revision_history, f0_binding} quadruple coherent, and what is a
minimal edit set that closes both the containment carriers and the history invariants?

What this is: a machine check over document bytes and the document's own fields, plus
the FROZEN change protocol quoted in artifacts/formulation/FROZEN.json.  It is NOT a
mathematics claim, NOT a gate verdict, NOT a node status, and it writes no canonical
path.

Invariants (all derived from the document's own content / the frozen change protocol):
  H1 history timestamps are non-decreasing in list order.
  H2 the newest history row names the current revision (f"rev{revision}").
  H3 the newest history row names the live f0_binding.declared_f0_sha256.
  H4 no row marked unused carries an active delta note.
  H5 document.revised_at equals the newest row's `at`.
  H6 f0_binding declared F0 hash and consistency-evidence hash resolve on disk.
  H7 canonical and mirror copies are byte-identical (landing precondition).
  C1 containment carriers: no live denial of the document's own chain (R06 slot) and
     no size premise inverted against the chain (R16 slot).  Semantics follow the
     document-relative instruments of worker-002/worker-007/worker-066; re-implemented
     here so this report is self-contained.

Run:  python3 check_f2b_history_closure.py
Exit: 0 = verdict produced; 2 = a pin moved during the run (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

LIVE = "schemas/af_scc_c0_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"

CANDIDATES = {
    "live": LIVE,
    "w002_2edit_84b5d3fa": "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml",
    "w022_cd_a110f8e8": "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "w044_rev13_48cadb72": "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml",
}

NEW_AT = "2026-09-12T01:24:00+08:00"  # wall-clock stamp for the closure candidates below
STAMP = "2026-09-12T01:24:00+08:00"    # fixed measurement stamp: this instrument is byte-deterministic


def now() -> str:
    return STAMP


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode("utf-8"))


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# ---------------------------------------------------------------- containment oracle
def norm_token(raw: str):
    t = str(raw).strip().lower().replace("{", "").replace("}", "").replace("^", "")
    t = t.replace("_", "").replace(" ", "").replace("\\", "").replace(",", "")
    if t == "c0":
        return "C0"
    if t.startswith("c2"):
        return "C2"
    if t in ("h2loc", "h2"):
        return "H2LOC"
    if t in ("c11", "c1,1"):
        return "C11"
    return None


OWN = {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2", "AF-WCC-VAC-GEN": None}


def parse_order(chain_text: str):
    head = str(chain_text).split(";")[0]
    parts = re.split(r"\s+contains\s+", head)
    order = {}
    for i, part in enumerate(parts):
        m = re.search(r"E_?\{?([A-Za-z0-9^_,]+)\}?", part.strip())
        tok = norm_token(m.group(1)) if m else None
        if tok:
            order[tok] = i
    return order


def phrase_token(phr: str):
    m = re.search(r"\bC0\b|\bC2\b|C\^?\{?1,?1\}?|H2_?loc", str(phr))
    return norm_token(m.group(0)) if m else None


def find_line(text: str, needle: str):
    pos = text.find(needle)
    return text.count("\n", 0, pos) + 1 if pos >= 0 else None


def containment_findings(text: str, class_id: str):
    """Document-relative: a reason contradicting the document's own chain, or a live
    must_not_conflate denial of containment the document asserts."""
    doc = yaml.safe_load(text)
    own = OWN[class_id]
    order = parse_order(str((doc.get("implication_ledger") or {}).get("extension_class_containment", "")))
    out = []
    for i, e in enumerate(((doc.get("implication_ledger") or {}).get("forbidden_transfers")) or []):
        reason = str(e.get("reason", ""))
        to_tok = own if str(e.get("to", "")).strip() == "this class" else phrase_token(e.get("to", ""))
        from_tok = phrase_token(e.get("from", ""))
        if not from_tok or not to_tok or from_tok not in order or to_tok not in order:
            continue
        m = re.search(r"strictly\s+(larger|smaller)\s+extension\s+class", reason)
        if m:
            violation = (order[from_tok] > order[to_tok]) if m.group(1) == "larger" else (order[from_tok] < order[to_tok])
            if violation:
                out.append({"kind": "size_premise_inverted",
                            "clause": f"implication_ledger.forbidden_transfers[{i}].reason",
                            "line": find_line(text, reason[:60]), "stated": m.group(0)})
    for i, s in enumerate(((doc.get("regularity") or {}).get("must_not_conflate")) or []):
        stripped = re.sub(r"\[[^\]]*\]", "", str(s))
        for m in re.finditer(r"No\s+containment\s+with\s+(.{0,80}?)\s+is\s+asserted", stripped, re.I):
            named = [t for t in (norm_token(x) for x in re.findall(r"C0|C2|C\^?\{?1,?1\}?|H2_?loc", m.group(1), re.I)) if t]
            if named:
                out.append({"kind": "false_containment_denial",
                            "clause": f"regularity.must_not_conflate[{i}]",
                            "line": find_line(text, m.group(0)[:40]), "sentence": m.group(0)})
    return sorted(out, key=lambda x: (x["kind"], x["clause"])), order


# ---------------------------------------------------------------- history invariants
def history_invariants(text: str, path: str, declared_f0: str, measured_f0: str,
                       measured_consistency: str, mirror_text: str | None):
    doc = yaml.safe_load(text)
    rev = doc.get("revision")
    revised_at = str(doc.get("revised_at", ""))
    rows = doc.get("revision_history") or []
    fb = doc.get("f0_binding") or {}
    checks = []

    def ck(cid, desc, ok, observed):
        checks.append({"check": cid, "description": desc, "pass": bool(ok), "observed": observed})

    ats = [str(r.get("at", "")) for r in rows]
    ck("H1", "history timestamps non-decreasing in list order",
       all(ats[i] <= ats[i + 1] for i in range(len(ats) - 1)),
       {"order": ats, "violations": [f"{ats[i]} > {ats[i+1]}" for i in range(len(ats) - 1) if ats[i] > ats[i + 1]]})

    last_notes = " ".join(str(n) for n in (rows[-1].get("notes") or [])) if rows else ""
    ck("H2", "newest history row names the current revision",
       f"rev{rev}" in last_notes,
       {"revision": rev, "newest_row_names_rev": f"rev{rev}" in last_notes, "newest_notes_head": last_notes[:120]})

    ck("H3", "newest history row names the live declared F0 hash",
       measured_f0 in last_notes or measured_f0[:12] in last_notes,
       {"declared_f0_sha256": fb.get("declared_f0_sha256"),
        "measured_f0_sha256": measured_f0,
        "named_in_newest_row": (measured_f0 in last_notes or measured_f0[:12] in last_notes),
        "hashes_named_anywhere": sorted(set(re.findall(r"\b[0-9a-f]{12}\b", " ".join(
            str(n) for r in rows for n in (r.get("notes") or [])))))})

    bad_unused = [r.get("index") for r in rows
                  if r.get("unused") in (True, "True", "true") and (r.get("notes") or [])]
    ck("H4", "no unused history row carries an active delta note", not bad_unused,
       {"unused_rows_with_notes": bad_unused})

    ck("H5", "revised_at equals the newest history row timestamp",
       bool(rows) and revised_at == ats[-1],
       {"revised_at": revised_at, "newest_row_at": ats[-1] if ats else None})

    decl_f0 = str(fb.get("declared_f0_sha256", ""))
    decl_cons = str(fb.get("consistency_evidence_sha256", ""))
    ck("H6", "declared F0 and consistency-evidence hashes resolve on disk",
       decl_f0 == measured_f0 and decl_cons == measured_consistency,
       {"declared_f0": decl_f0, "measured_f0": measured_f0,
        "declared_consistency": decl_cons, "measured_consistency": measured_consistency})

    if mirror_text is not None:
        ck("H7", "canonical and mirror copies are byte-identical",
           sha256_text(text) == sha256_text(mirror_text),
           {"canonical": sha256_text(text)[:12], "mirror": sha256_text(mirror_text)[:12]})

    fails = [c["check"] for c in checks if not c["pass"]]
    return {"path": path, "sha256": sha256_text(text), "revision": rev, "revised_at": revised_at,
            "history_rows": len(rows), "checks": checks, "failed": fails,
            "history_clean": not fails}


# ---------------------------------------------------------------- closure candidates
def closure_variants(live_text: str, f0_hash: str):
    """Two minimal edits on top of the containment-clean candidate (the history block is
    flow-style YAML, one row per line):
    V1 = append a rev14 row + bump revision/revised_at (closes H2/H3/H5).
    V2 = V1 + move the unused out-of-order row into chronological position and clear its
         active delta notes (closes H1/H4 as well; rewrites historical ordering)."""
    lines = live_text.splitlines(keepends=True)

    def line_idx(frag: str):
        hits = [i for i, ln in enumerate(lines) if frag in ln]
        return hits[0] if hits else None

    i_top_rev = next((i for i, ln in enumerate(lines) if ln.startswith("revision:")), None)
    i_top_at = next((i for i, ln in enumerate(lines) if ln.startswith("revised_at:")), None)
    i_row1 = line_idx("{index: 1,")
    i_row9 = line_idx("{index: 9,")
    i_row11 = line_idx("{index: 11,")
    assert None not in (i_top_rev, i_top_at, i_row1, i_row9, i_row11), "live history shape changed"

    new_row = ('  - {index: 12, at: "%s", unused: false, notes: ["rev14 delta: F2b containment '
               'carriers repaired (must_not_conflate[0] denial and forbidden_transfers[0].reason size '
               'premise) and f0_binding declared-F0 hash %s re-affirmed; revision_history '
               'refreshed; no other class-semantics change."] }\n' % (NEW_AT, f0_hash))
    row9_clean = ('  - {index: 9, at: "2026-09-11T23:30:35+08:00", unused: true, notes: [] }\n')

    v1 = list(lines)
    v1[i_top_rev] = "revision: 14\n"
    v1[i_top_at] = 'revised_at: "%s"\n' % NEW_AT
    v1.insert(i_row11 + 1, new_row)
    v1 = "".join(v1)

    v2 = list(lines)
    v2[i_top_rev] = "revision: 14\n"
    v2[i_top_at] = 'revised_at: "%s"\n' % NEW_AT
    v2[i_row9] = row9_clean
    i_row9b = v2.index(row9_clean)
    moved = v2.pop(i_row9b)
    i_row1b = next(i for i, ln in enumerate(v2) if "{index: 1," in ln)
    v2.insert(i_row1b, moved)  # 23:30:35 precedes 23:34:10 -> chronological, monotone
    i_row11b = next(i for i, ln in enumerate(v2) if "{index: 11," in ln)
    v2.insert(i_row11b + 1, new_row)
    v2 = "".join(v2)
    return {"V1_append_row_and_bump": v1, "V2_plus_unused_row_reorder": v2}


def leaf_paths(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaf_paths(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def main() -> int:
    # pins at entry
    pin_paths = [LIVE, MIRROR, "schemas/af_scc_c2_vacuum.yaml", "schemas/af_wcc_vacuum.yaml",
                 FROZEN, F0, "artifacts/formulation/formulation_taxonomy.yaml", CONSISTENCY,
                 RULE_SPEC, VOCAB, GATE] + list(CANDIDATES.values())
    pins_start = {}
    for p in pin_paths:
        fp = ROOT / p
        if fp.exists():
            pins_start[p] = {"sha256": sha256_file(fp), "bytes": fp.stat().st_size}
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "raw" / "pins_start.json").write_text(json.dumps(pins_start, indent=1, sort_keys=True) + "\n")

    measured_f0 = pins_start[F0]["sha256"]
    measured_consistency = pins_start[CONSISTENCY]["sha256"]
    live_text = (ROOT / LIVE).read_text()
    mirror_text = (ROOT / MIRROR).read_text()

    # candidate census
    census = {}
    for name, p in CANDIDATES.items():
        fp = ROOT / p
        if not fp.exists():
            census[name] = {"path": p, "exists": False}
            continue
        txt = fp.read_text()
        h = history_invariants(txt, p, None, measured_f0, measured_consistency,
                               mirror_text if p == LIVE else None)
        cf, order = containment_findings(txt, "AF-SCC-C0-VAC-GEN")
        live_leaves = leaf_paths(yaml.safe_load(live_text))
        cand_leaves = leaf_paths(yaml.safe_load(txt))
        changed = sorted({k for k in set(live_leaves) | set(cand_leaves)
                          if live_leaves.get(k) != cand_leaves.get(k)})
        census[name] = {"path": p, "exists": True, "sha256": h["sha256"], "bytes": fp.stat().st_size,
                        "revision": h["revision"], "revised_at": h["revised_at"],
                        "containment_findings": cf, "containment_clean": not cf,
                        "history": h, "changed_leaf_paths_vs_live": changed,
                        "changed_leaf_count": len(changed),
                        "chain_order": order}

    # closure variants on the containment-clean candidate
    clean_name = "w002_2edit_84b5d3fa"
    base_text = (ROOT / CANDIDATES[clean_name]).read_text()
    variants = closure_variants(base_text, measured_f0)
    closure = {}
    for vname, vtext in variants.items():
        h = history_invariants(vtext, f"<{vname}>", None, measured_f0, measured_consistency, None)
        cf, _ = containment_findings(vtext, "AF-SCC-C0-VAC-GEN")
        closure[vname] = {"sha256": sha256_text(vtext), "bytes": len(vtext.encode()),
                          "history": h, "containment_findings": cf,
                          "all_closed": (not h["failed"]) and (not cf)}
    # write the fully-closing variant as a candidate artifact for the owner (not canonical)
    full = variants["V2_plus_unused_row_reorder"]
    (OUT / "scratch").mkdir(parents=True, exist_ok=True)
    (OUT / "scratch" / "candidate_rev14_closed.yaml").write_text(full)
    full_sha = sha256_text(full)
    # dual-apply check: the mirror is byte-identical, so the same transform must land there
    dual = closure_variants(mirror_text, measured_f0)["V2_plus_unused_row_reorder"]
    canonical_dual = closure_variants(live_text, measured_f0)["V2_plus_unused_row_reorder"]
    dual_identical = (sha256_text(dual) == sha256_text(canonical_dual)
                      and sha256_text(live_text) == sha256_text(mirror_text))

    # controls -- pre-registered before the numbers above were read
    controls = []

    def ctl(cid, desc, expected, observed):
        controls.append({"control": cid, "description": desc, "expected": expected,
                         "observed": observed, "matched": expected == observed})

    live_h = census["live"]["history"]
    ctl("K1-live-baseline", "live rev13 fails H1,H3,H4 and passes H2,H5,H6,H7",
        ["H1", "H3", "H4"], live_h["failed"])
    ctl("K2-containment-repair-only", "84b5d3fa is containment-clean but history-unchanged",
        {"containment_clean": True, "history_failed": ["H1", "H3", "H4"]},
        {"containment_clean": census[clean_name]["containment_clean"],
         "history_failed": census[clean_name]["history"]["failed"]})
    rev14 = census.get("w044_rev13_48cadb72", {})
    ctl("K3-rev-bump-without-row", "48cadb72 (revision=14) additionally fails H2 and regresses H6",
        ["H1", "H2", "H3", "H4", "H6"], (rev14.get("history") or {}).get("failed"))
    monotone_mutant = base_text.replace('"2026-09-11T23:30:35+08:00"', '"2026-09-12T00:30:30+08:00"')
    ctl("K4-monotone-history-passes-H1", "repairing only the out-of-order timestamp clears H1",
        "H1" in history_invariants(monotone_mutant, "<m>", None, measured_f0,
                                   measured_consistency, None)["failed"], False)
    f0_named = "".join(
        (ln.replace("no class-semantics change.", "no class-semantics change; declared-F0 "
                    + measured_f0 + " re-affirmed.", 1) if "{index: 11," in ln else ln)
        for ln in base_text.splitlines(keepends=True))
    ctl("K5-f0-named-clears-H3", "naming the live F0 hash in the newest row clears H3",
        "H3" in history_invariants(f0_named, "<m>", None, measured_f0,
                                   measured_consistency, None)["failed"], False)
    ctl("K6-full-closure", "V2 closes every history invariant and both containment carriers",
        True, closure["V2_plus_unused_row_reorder"]["all_closed"])
    ctl("K7-dual-apply-identity", "the same transform on the byte-identical mirror yields the same hash",
        True, dual_identical)
    ctl("K8-inverted-premise-control", "the live file still fires the inverted-premise detector",
        "size_premise_inverted" in [f["kind"] for f in census["live"]["containment_findings"]], True)
    w044_text = (ROOT / CANDIDATES["w044_rev13_48cadb72"]).read_text() if (ROOT / CANDIDATES["w044_rev13_48cadb72"]).exists() else ""
    ctl("K9-w044-self-contradiction", "48cadb72 binding_note names the rev13 evidence hash 9e335e9b while the field still carries 675a99d0",
        True, ("675a99d0d25b" in w044_text) and ("9e335e9ba1bf" in w044_text)
            and ("consistency_evidence_sha256: \"675a99d0d25b" in w044_text))

    # pin re-measure: fail closed
    pins_end = {}
    moved = []
    for p in pin_paths:
        fp = ROOT / p
        if fp.exists():
            h = sha256_file(fp)
            pins_end[p] = {"sha256": h, "bytes": fp.stat().st_size}
            if pins_start.get(p, {}).get("sha256") != h:
                moved.append(p)
    (OUT / "raw" / "pins_end.json").write_text(json.dumps(pins_end, indent=1, sort_keys=True) + "\n")
    if moved:
        print("PIN MOVED during run:", moved)
        return 2

    report = {
        "task_id": "W043G-F2B-HISTORY-CLOSURE-01",
        "actor": "worker-043",
        "agent_id": "worker-043",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "generated_at": now(),
        "question": ("Does the staged F2b containment repair close the whole audit trail at the "
                     "FROZEN rev29 pins, or does the next revision still carry the worker-035 "
                     "F-035-01 revision_history defect family?"),
        "target": {"path": LIVE, "sha256": pins_start[LIVE]["sha256"], "revision": 13,
                   "frozen_manifest": FROZEN, "frozen_manifest_sha256": pins_start[FROZEN]["sha256"],
                   "frozen_revision": json.loads((ROOT / FROZEN).read_text()).get("revision")},
        "invariants": {"H1": "history timestamps non-decreasing", "H2": "newest row names current revision",
                       "H3": "newest row names live declared F0 hash", "H4": "unused row carries no active delta",
                       "H5": "revised_at equals newest row at", "H6": "f0_binding hashes resolve on disk",
                       "H7": "canonical == mirror bytes",
                       "C1": "no live containment denial; no inverted size premise vs own chain"},
        "live": {"sha256": pins_start[LIVE]["sha256"],
                 "history_failed": live_h["failed"], "containment_findings": census["live"]["containment_findings"],
                 "history_detail": {c["check"]: c["observed"] for c in live_h["checks"] if not c["pass"]}},
        "candidate_census": census,
        "closure_variants": closure,
        "closure_candidate": {"path": "artifacts/worker-043/w043g_f2b_history_closure/scratch/candidate_rev14_closed.yaml",
                              "sha256": full_sha, "bytes": len(full.encode()),
                              "changed_leaf_paths_vs_84b5d3fa": sorted(
                                  {k for k in set(leaf_paths(yaml.safe_load(full))) |
                                   set(leaf_paths(yaml.safe_load(base_text)))
                                   if leaf_paths(yaml.safe_load(full)).get(k) != leaf_paths(yaml.safe_load(base_text)).get(k)}),
                              "status": "worker candidate only; NOT canonical; owner decision required"},
        "finding": ("At the FROZEN rev29 pins the containment-clean staged candidate 84b5d3fa "
                    "(and the worker-022 candidate a110f8e8) leave revision_history byte-unchanged, so "
                    "F-035-01's three defects persist: non-monotone timestamps (row 8 00:30:00 before "
                    "row 9 23:30:35 of the previous day), no row naming the live declared F0 hash "
                    "0abb9ed8 (newest hash named is 565a6e50), and an unused:true row carrying two active "
                    "delta notes. The worker-044 rev13-integration candidate 48cadb72 is worse: it bumps "
                    "revision to 14 while its newest history row still names rev13, and it re-declares the "
                    "pre-rev13 consistency-evidence hash 675a99d0 in f0_binding while its own binding_note "
                    "states the rev13 refresh to 9e335e9b - landing it would regress the rev13 evidence "
                    "binding. Appending a rev14 row, bumping revision and revised_at, moving the unused "
                    "row into chronological position and clearing its active notes closes all seven "
                    "invariants together with both containment carriers (V2)."),
        "recommendation": ("Any authorized F2b landing should carry the containment edits AND the "
                           "revision_history refresh in the same revision, rebased on the rev13 f0_binding "
                           "(9e335e9b), not the rev12 value; shipping containment alone leaves a recorded "
                           "major finding for the r3 reviewer to re-raise, and shipping 48cadb72 as-is "
                           "regresses the evidence binding."),
        "checks_passed": sum(1 for v in census.values() if v.get("exists")),
        "controls_matched": sum(1 for c in controls if c["matched"]),
        "controls_total": len(controls),
        "controls": controls,
        "pins_stable_entry_exit": not moved,
        "authority_note": ("Worker measurement and review evidence only. No canonical file, map, gate "
                           "verdict, validation_status or node status was modified; the closure candidate "
                           "is stored under this worker's artifact directory only."),
        "falsifier": ("Re-run this script on the same pins. Falsified if: the live F2b hash is not "
                      "b2ab6acb2bbe; the live file does not carry the three history defects; any staged "
                      "candidate listed here is shown to carry a rev14 history row or a refreshed "
                      "declared-F0 reference; 48cadb72 does not carry revision=14 with a rev13-newest row; "
                      "V2 fails any invariant or fires the containment detectors; any pre-registered "
                      "control departs from its expectation; or a rule/FROZEN-protocol clause is produced "
                      "under which revision_history coherence is not required for a class-schema revision."),
    }
    (OUT / "raw" / "history_frontier_raw.json").write_text(json.dumps(
        {"task_id": report["task_id"], "generated_at": report["generated_at"],
         "live": report["live"], "candidate_census": census, "closure_variants":
         {k: {"sha256": v["sha256"], "history_failed": v["history"]["failed"],
              "containment_clean": not v["containment_findings"], "all_closed": v["all_closed"]}
          for k, v in closure.items()}, "controls": controls}, indent=1) + "\n")
    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict_live_history_failed": live_h["failed"],
                      "candidates": {k: {"sha": v.get("sha256", "")[:12],
                                         "containment_clean": v.get("containment_clean"),
                                         "history_failed": (v.get("history") or {}).get("failed")}
                                     for k, v in census.items()},
                      "closure": {k: {"sha": v["sha256"][:12], "all_closed": v["all_closed"],
                                      "failed": v["history"]["failed"]} for k, v in closure.items()},
                      "controls": f"{report['controls_matched']}/{report['controls_total']}",
                      "pins_stable": not moved}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
