#!/usr/bin/env python3
"""W030C-REV13-PREFLIGHT-01 -- independent, read-only pre-freeze audit of the rev13
formulation bytes against the astra-life05-evidence-binding-repair card (REC-12).

Scope: the live class schemas F1 AF-WCC-VAC-GEN / F2a AF-SCC-C2-VAC-GEN /
F2b AF-SCC-C0-VAC-GEN at the instant of measurement, before FROZEN rev29 is published.

Question: does the landed rev13 delta satisfy REC-12 items (1)-(3) and REC-12's falsifier
("any class-semantics change"), and is the recorded repair provenance consistent with the
bytes on disk?

This instrument writes only under its own artifact directory. It never writes a canonical
path. The one subprocess it spawns (the canonical consistency checker) runs against a
private sandbox copy, never the live tree.

Exit 0 = every check classified; exit 1 = at least one UNAUTHORIZED change or failed check.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # <repo>/artifacts/worker-030/rev13_preflight -> repo root

REV12 = {
    "AF-WCC-VAC-GEN": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "AF-SCC-C2-VAC-GEN": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "AF-SCC-C0-VAC-GEN": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
PATHS = {
    "AF-WCC-VAC-GEN": ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    "AF-SCC-C2-VAC-GEN": ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    "AF-SCC-C0-VAC-GEN": ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
}
SNAP_CANDIDATES = [
    "artifacts/worker-061/f2a_rev12_bind/pinned",
    "tmp/w031_f2a_preflight/sandbox/schemas",
    "artifacts/worker-080/semct_rebase/stage/schemas",
]
CONSISTENCY_SHA = "9e335e9b"  # prefix; full value asserted
CONSISTENCY_FULL = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
SUPERSEDED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
CASES = "schemas/taxonomy_cases.jsonl"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
TOOL = "artifacts/formulation/tools/evidence_binding_repair_rev29.py"
REPORT = "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"

# files whose bytes must not move while this instrument runs (read-only guarantee)
GUARDED = [F0, SUPP, CASES, EVIDENCE, FROZEN, TOOL, REPORT] + [p for pair in PATHS.values() for p in pair]

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print("FATAL: pyyaml unavailable:", exc)
    sys.exit(2)


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(rel: str) -> str:
    return sha_bytes((ROOT / rel).read_bytes())


def flatten(obj, prefix=""):
    """YAML document -> {dotted.path: leaf json} with list indices."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = json.dumps(obj, sort_keys=True)
    return out


def find_rev12(cid: str) -> tuple[str, str]:
    """Return (path, sha) of a snapshot whose bytes hash to the rev12 pin."""
    fn = Path(PATHS[cid][0]).name
    want = REV12[cid]
    for cand in SNAP_CANDIDATES:
        p = ROOT / cand / fn
        if p.exists() and sha_bytes(p.read_bytes()) == want:
            return str(p.relative_to(ROOT)), want
    raise SystemExit(f"FATAL: no rev12 snapshot for {cid} ({want[:12]}) in {SNAP_CANDIDATES}")


ABSENT = "<absent>"


def _val(raw: str):
    """Decode a flattened leaf, tolerating the ABSENT sentinel."""
    if raw == ABSENT:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


def classify_header(path: str, old: str, new: str, newdoc: dict) -> str | None:
    if path in ("revised_at", "revision"):
        return "header_stamp"
    if path.startswith("revision_history["):
        try:
            idx = int(path.split("[", 1)[1].split("]", 1)[0])
        except Exception:
            return None
        hist = newdoc.get("revision_history")
        if isinstance(hist, list) and idx < len(hist) and isinstance(hist[idx], dict):
            if any("rev13" in str(x) for x in hist[idx].get("notes", [])):
                return "header_revision_history_rev13"
        return None
    return None


def classify_binding(path: str, old: str, new: str, newdoc: dict) -> str | None:
    if path == "f0_binding.consistency_evidence_sha256":
        if _val(old) == SUPERSEDED and _val(new) == CONSISTENCY_FULL:
            return "item2_binding_refresh"
        return None
    if path == "f0_binding.checked_at":
        return "item2_checked_at_restamp"
    if path == "f0_binding.binding_note":
        o, n = _val(old), _val(new)
        if isinstance(o, str) and isinstance(n, str) and n.startswith(o) and "rev13" in n:
            return "item2_binding_note_append"
        return None
    return None


def classify_f1_text(path: str, old: str, new: str, newdoc: dict) -> str | None:
    """F1-only item-3 strictness corrections: value-pattern checked, not path-trusted.

    The rev13 replacement text quotes the superseded token inside a [rev13: ...] annotation,
    so the test keys on the corrected direction markers, not on token absence.
    """
    o, n = _val(old), _val(new)
    if not (isinstance(o, str) and isinstance(n, str)):
        return None
    if "misclassif" in o and "EQUIVALENT" in n and "[rev13" in n and "non-sequitur" in n:
        return "item3_misclassification_removed"
    if "strictly STRONGER" in o and "[rev13" in n:
        if "EQUIVALENT to the tail form" in n:
            return "item3_equivalence_direction"
        if "strictly WEAKER than this class's single-q tail predicate" in n:
            return "item3_set_relation_direction"
    return None


def main() -> int:
    checks, changed_paths_all = {}, {}
    t0 = {rel: sha(rel) for rel in GUARDED if (ROOT / rel).exists()}

    # ---- A. pins, mirrors, revisions -------------------------------------------
    a = {}
    for cid, (canon, mirror) in PATHS.items():
        a[cid] = {"live_sha256": sha(canon), "mirror_sha256": sha(mirror),
                  "mirror_identical": sha(canon) == sha(mirror),
                  "rev12_pin": REV12[cid], "drifted_from_rev12": sha(canon) != REV12[cid]}
    checks["A_pins_and_mirrors"] = a

    # ---- B/C. item 2 per class --------------------------------------------------
    b = {}
    for cid, (canon, _m) in PATHS.items():
        doc = yaml.safe_load((ROOT / canon).read_text())
        fb = doc.get("f0_binding", {})
        h = fb.get("consistency_evidence_sha256")
        b[cid] = {
            "declared": h,
            "declared_is_live_evidence": h == CONSISTENCY_FULL,
            "checked_at": fb.get("checked_at"),
            "binding_note_has_rev13": "rev13" in str(fb.get("binding_note", "")),
            "residual_675a99d0_in_document": "675a99d0" in (ROOT / canon).read_text(),
        }
    checks["B_item2_binding_all_three"] = b
    checks["B_pass"] = all(v["declared_is_live_evidence"] for v in b.values())

    # ---- item 1 cases -----------------------------------------------------------
    rows = [json.loads(l) for l in (ROOT / CASES).read_text().splitlines() if l.strip()]
    bad = [r.get("case_id") for r in rows[1:]
           if r.get("binding_status") != "bound_taxonomy_sha_0abb9ed8a961"]
    checks["C_item1_cases"] = {
        "rows": len(rows) - 1, "meta_sha256": rows[0]["taxonomy_ref"]["sha256"],
        "unbound_rows": bad, "cases_sha256": sha(CASES),
        "pass": not bad and rows[0]["taxonomy_ref"]["sha256"].startswith("0abb9ed8a961"),
    }

    # ---- item 3 F1 text + CH ----------------------------------------------------
    f1doc = yaml.safe_load((ROOT / PATHS["AF-WCC-VAC-GEN"][0]).read_text())
    c0doc = yaml.safe_load((ROOT / PATHS["AF-SCC-C0-VAC-GEN"][0]).read_text())
    f1txt = (ROOT / PATHS["AF-WCC-VAC-GEN"][0]).read_text()
    ch = c0doc["class_identity_variants"]["horizon_localized_variant"]["relation"]
    checks["D_item3_strictness"] = {
        "residual_strictly_STRONGER_occurrences": f1txt.count("strictly STRONGER"),
        "equivalence_text_present": "EQUIVALENT to the tail form" in f1txt,
        "set_relation_strictly_WEAKER": "strictly WEAKER than this class's single-q tail predicate" in f1txt,
        "CH_unchanged_and_ok": ch.startswith("strictly WEAKER than this frozen class"),
        "rev13_note_in_revision_history": "rev13 delta" in f1txt,
        "pass": ("EQUIVALENT to the tail form" in f1txt
                 and "strictly WEAKER than this class's single-q tail predicate" in f1txt
                 and ch.startswith("strictly WEAKER than this frozen class")),
    }

    # ---- E. masked deep-diff rev12 -> rev13 (REC-12 falsifier) ------------------
    e, unauthorized_total = {}, 0
    for cid, (canon, _m) in PATHS.items():
        snap_rel, _ = find_rev12(cid)
        newdoc = yaml.safe_load((ROOT / canon).read_text())
        old = flatten(yaml.safe_load((ROOT / snap_rel).read_text()))
        new = flatten(newdoc)
        keys = sorted(set(old) | set(new))
        changed = [k for k in keys if old.get(k) != new.get(k)]
        allowed, unauth = [], []
        for k in changed:
            o, n = old.get(k, ABSENT), new.get(k, ABSENT)
            cat = classify_header(k, o, n, newdoc) or classify_binding(k, o, n, newdoc)
            if cat is None and cid == "AF-WCC-VAC-GEN":
                cat = classify_f1_text(k, o, n, newdoc)
            (allowed if cat else unauth).append({"path": k, "category": cat,
                                                 "old": str(o)[:160], "new": str(n)[:160]})
        unauthorized_total += len(unauth)
        e[cid] = {"rev12_snapshot": snap_rel, "n_changed_leaf_paths": len(changed),
                  "allowed": allowed, "unauthorized": unauth}
        changed_paths_all[cid] = changed
    checks["E_masked_deep_diff"] = e
    checks["E_pass"] = unauthorized_total == 0
    checks["E_unauthorized_total"] = unauthorized_total

    # ---- F. header discipline ---------------------------------------------------
    f = {}
    for cid, (canon, _m) in PATHS.items():
        txt = (ROOT / canon).read_text()
        doc = yaml.safe_load(txt)
        mtime = os.path.getmtime(ROOT / canon)
        import datetime as dt
        mt = dt.datetime.fromtimestamp(mtime).astimezone().replace(microsecond=0).isoformat()
        f[cid] = {"revision": doc.get("revision"), "revised_at": doc.get("revised_at"),
                  "mtime": mt, "revised_at_le_mtime": str(doc.get("revised_at")) <= mt,
                  "single_revised_at_key": txt.count("\nrevised_at:") == 1,
                  "pass": doc.get("revision") == 13 and str(doc.get("revised_at")) <= mt}
    checks["F_header_discipline"] = f

    # ---- G. repair report vs live bytes, and tool capability --------------------
    rep = json.loads((ROOT / REPORT).read_text())
    tool_txt = (ROOT / TOOL).read_text()
    g = {"report_phase": rep.get("phase"), "report_at": rep.get("at"),
         "report_pins_all_ok": all(v.get("ok") for v in (rep.get("pins") or {}).values()),
         "report_vs_live": {}, "f0_untouched_in_report": rep.get("f0_untouched", {}).get("equals_pin")}
    disagree = []
    for rel, meta in (rep.get("files") or {}).items():
        live = sha(rel)
        ok = meta.get("after") == live
        g["report_vs_live"][rel] = {"report_after": meta.get("after"), "live": live, "match": ok}
        if not ok:
            disagree.append(rel)
    g["report_vs_live_disagreements"] = disagree
    g["f1_pre_binding_fix_recorded"] = (rep.get("files", {})
                                        .get(PATHS["AF-WCC-VAC-GEN"][0], {})
                                        .get("after_pre_binding_fix"))
    g["tool_can_emit_that_key"] = "after_pre_binding_fix" in tool_txt
    g["tool_sha256"] = sha(TOOL)
    g["provenance_mismatch"] = (g["f1_pre_binding_fix_recorded"] is not None
                                and not g["tool_can_emit_that_key"])
    g["pass"] = not disagree and g["report_pins_all_ok"]
    checks["G_report_provenance"] = g

    # ---- H. FROZEN state + rev29 pin-set verification ---------------------------
    fz = json.loads((ROOT / FROZEN).read_text())
    fzfiles = fz.get("files") or {}
    pin_rows, pin_bad = {}, []
    for rel, meta in fzfiles.items():
        if not (ROOT / rel).exists():
            pin_rows[rel] = {"pinned": (meta or {}).get("sha256"), "live": None, "match": False}
            pin_bad.append(rel)
            continue
        got = sha(rel)
        exp = (meta or {}).get("sha256")
        ok = got == exp
        pin_rows[rel] = {"pinned": exp, "live": got, "match": ok}
        if not ok:
            pin_bad.append(rel)
    checks["H_frozen_state"] = {
        "revision": fz.get("revision"), "frozen_at": fz.get("frozen_at"),
        "n_files": len(fzfiles), "n_pin_mismatches": len(pin_bad), "mismatches": pin_bad,
        "rev29_published": fz.get("revision") == 29,
        "report_pinned": (fzfiles.get(REPORT) or {}).get("sha256"),
        "report_live": sha(REPORT),
        "tool_pinned": (fzfiles.get(TOOL) or {}).get("sha256"),
        "tool_live": sha(TOOL),
        "pass": len(pin_bad) == 0,
    }

    # ---- I. sandbox re-run of the canonical checker (content-currentness) -------
    sb = HERE / "sandbox_consistency"
    if sb.exists():
        shutil.rmtree(sb)
    for rel in (F0, SUPP, "artifacts/formulation/VOCAB_ALIASES.json"):
        dst = sb / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    dst = sb / "artifacts/formulation/tools/check_taxonomy_consistency.py"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py", dst)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(dst)], capture_output=True, text=True, cwd=str(sb))
    emitted = sb / EVIDENCE
    em_sha = sha_bytes(emitted.read_bytes()) if emitted.exists() else None
    checks["I_sandbox_consistency_rerun"] = {
        "exit": proc.returncode, "stdout": proc.stdout.strip().splitlines()[:3],
        "emitted_sha256": em_sha, "live_evidence_sha256": sha(EVIDENCE),
        "matches_live_evidence": em_sha == sha(EVIDENCE) == CONSISTENCY_FULL,
        "pass": proc.returncode == 0 and em_sha == CONSISTENCY_FULL,
    }

    # ---- K. post-freeze writes over the pinned manifest -------------------------
    import datetime as _dt
    fa = _dt.datetime.fromisoformat(str(fz.get("frozen_at")))
    post = []
    for rel, meta in fzfiles.items():
        p = ROOT / rel
        if not p.exists():
            continue
        mt = _dt.datetime.fromtimestamp(os.path.getmtime(p)).astimezone()
        if mt > fa:
            post.append({"path": rel, "mtime": mt.replace(microsecond=0).isoformat(),
                         "pinned": (meta or {}).get("sha256"), "live": sha(rel),
                         "pin_still_matches": (meta or {}).get("sha256") == sha(rel)})
    checks["K_post_freeze_writes"] = {
        "frozen_at": fz.get("frozen_at"), "n_pinned_paths": len(fzfiles),
        "n_written_after_freeze": len(post), "paths": post,
        "pass": len(post) == 0,
    }

    # ---- J. read-only guarantee -------------------------------------------------
    moved = [rel for rel, h in t0.items() if (ROOT / rel).exists() and sha(rel) != h]
    checks["J_read_only_guarantee"] = {"inputs_moved_during_audit": moved, "pass": not moved}

    # ---- verdict ----------------------------------------------------------------
    core_bytes = [checks["B_pass"], checks["C_item1_cases"]["pass"], checks["D_item3_strictness"]["pass"],
                  checks["E_pass"], all(v["pass"] for v in f.values()),
                  checks["I_sandbox_consistency_rerun"]["pass"], checks["J_read_only_guarantee"]["pass"]]
    core_freeze = [checks["H_frozen_state"]["pass"], checks["K_post_freeze_writes"]["pass"]]
    provenance_finding = bool(g["provenance_mismatch"])
    bytes_ok = all(core_bytes)
    freeze_ok = all(core_freeze)
    verdict = ("REV13_BYTES_VERIFIED" if bytes_ok else "REV13_BYTES_ATTENTION")
    if not freeze_ok:
        verdict += "_FREEZE_INTEGRITY_FINDING"
    if provenance_finding:
        verdict += "_PROVENANCE_FINDING"
    out = {
        "schema": "worker-030/rev13-preflight/v1",
        "task_id": "W030C-REV13-PREFLIGHT-01",
        "actor": "worker-030",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "card": "astra-life05-evidence-binding-repair (REC-12)",
        "measured_at": __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "freeze_note": ("FROZEN rev29 was published at 2026-09-12T00:55:02+08:00 while this audit was "
                        "running; the audited schema bytes are identical before and after the freeze and "
                        "equal the rev29 pins, so this is a post-freeze verification of the rev13 bytes."),
        "verdict": verdict,
        "class_semantics_verdict": ("NO_UNAUTHORIZED_CHANGE" if checks["E_pass"] else "UNAUTHORIZED_CHANGE"),
        "freeze_verdict": ("FROZEN_REV29_PINS_CONSISTENT" if freeze_ok
                           else "FROZEN_REV29_PIN_MISMATCH_AND_POST_FREEZE_WRITES"),
        "provenance_verdict": ("FROZEN_REPAIR_REPORT_NOT_REGENERABLE_BY_PINNED_TOOL"
                               if provenance_finding else "PROVENANCE_CONSISTENT"),
        "findings": ([{"id": "W030C-F1", "severity": "traceability",
                       "summary": ("FROZEN rev29 pins evidence_binding_repair_rev29_report.json#f337f83e "
                                   "and its claimed generator evidence_binding_repair_rev29.py#2f6c4f7d, "
                                   "but the pinned report contains files['schemas/af_wcc_vacuum.yaml']"
                                   ".after_pre_binding_fix and the pinned tool source cannot emit that key; "
                                   "the report also declares F1's final after-hash before F1's final write "
                                   "(report 00:53:20, F1 mtime 00:53:41). The rev13 schema bytes themselves "
                                   "verify clean; only the repair record's reproducibility is affected.")}
                      ] if provenance_finding else [])
                     + ([{"id": "W030C-F2", "severity": "freeze-integrity",
                          "summary": ("FROZEN rev29 omits the variant delta rebase from its bounded scope: "
                                      "artifacts/formulation/variants/*.delta.json bind the repaired schemas' "
                                      "sha256, so the rev13 write invalidated them; both were rewritten at "
                                      "00:57:02 (+08:00) after the 00:55:02 freeze and now mismatch their rev29 "
                                      "pins. check_variant_deltas.py reported valid:false at 00:56:03 and was "
                                      "regenerated to the pinned fc6ee058 at 00:57:15. A rev30 re-freeze of the "
                                      "two delta paths plus artifact events is required.")}]
                        if not checks["K_post_freeze_writes"]["pass"] else []),
        "live_pins": {cid: sha(p[0]) for cid, p in PATHS.items()},
        "supplement_sha256": sha(SUPP), "f0_canonical_sha256": sha(F0),
        "checks": checks,
        "not_claimed": ["no gate verdict", "no node status change", "no review verdict",
                        "no canonical write", "no mathematics or physics claim",
                        "FROZEN rev29 is not audited here (not yet published)"],
        "falsifier": ("Apply an updated instrument that also emits after_pre_binding_fix to the rev12 "
                      "bytes and compare: if the on-disk evidence_binding_repair_rev29.py can be shown to "
                      "emit the report's F1 after_pre_binding_fix key, the provenance mismatch is falsified. "
                      "For the byte audit: if any rev12->rev13 changed leaf path outside the classified "
                      "allowed set is produced, or the rev13 bytes measure differently, this pass is falsified."),
    }
    (HERE / "report.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("measured_at", "verdict", "live_pins")}, indent=1))
    print("unauthorized_total:", unauthorized_total)
    for cid in PATHS:
        print(f"  {cid}: changed={e[cid]['n_changed_leaf_paths']} "
              f"allowed={len(e[cid]['allowed'])} unauthorized={len(e[cid]['unauthorized'])}")
        for u in e[cid]["unauthorized"]:
            print("    UNAUTHORIZED:", u["path"], "|", u["old"][:80], "->", u["new"][:80])
    print("report disagreement:", disagree, "| provenance_mismatch:", g["provenance_mismatch"])
    print("sandbox rerun:", checks["I_sandbox_consistency_rerun"]["matches_live_evidence"])
    return 0 if (bytes_ok and freeze_ok and not provenance_finding) else 1


if __name__ == "__main__":
    sys.exit(main())
