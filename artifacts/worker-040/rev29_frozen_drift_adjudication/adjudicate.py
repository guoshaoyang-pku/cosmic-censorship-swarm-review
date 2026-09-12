#!/usr/bin/env python3
"""W040-FROZEN-REV29-DRIFT-07 -- independent, read-only adjudication of the FROZEN rev29
manifest rewrite that landed inside the G-FORM r3 review window (CF-27).

Question (class-bound: AF-WCC-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN; node F1,F2a,F2b;
gate G-FORM): FROZEN rev29 moved 3d9e3d77fd87 -> 815e08079aef at frozen_at 00:57:26 with the
revision number held at 29.  What moved (bytes, not just hashes), was it declared, does it change
class-relevant assertions, is the owner's "check_variant_registry VALID" claim reproducible as a
semantic check, and which reviewer verdicts are pinned to which manifest?

Read-only on the canonical tree.  The two variant checkers are executed only inside a sandbox copy
because check_variant_deltas.py writes an evidence file into its ROOT.

Run:  python3 artifacts/worker-040/rev29_frozen_drift_adjudication/adjudicate.py
Outputs: measurements.json, controls.json, report.json, entry_hashes.json (in this directory).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
PIN = TASK / "pinned"
TZ = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    return json.loads(p.read_text())


# ---------------------------------------------------------------- pinned inputs
A_MANIFEST = PIN / "FROZEN.rev29.3d9e3d77fd87.json"
A_MANIFEST_2 = PIN / "FROZEN.rev29.3d9e3d77.secondsource.json"
B_MANIFEST = PIN / "FROZEN.rev29.815e08079aef.json"
WCC_OLD = PIN / "AF-WCC-VAC-GEN.variant-SET.delta.45b9b6a8d192.json"
WCC_NEW = PIN / "AF-WCC-VAC-GEN.variant-SET.delta.64b8d6394a04.json"
C0_OLD = PIN / "AF-SCC-C0-VAC-GEN.variant-CH.delta.c28795b0fdfc.json"
C0_NEW = PIN / "AF-SCC-C0-VAC-GEN.variant-CH.delta.7c165a9063c6.json"
REG_OLD = PIN / "VARIANT_REGISTRY.5eb42f9a384a.json"
REG_NEW = PIN / "VARIANT_REGISTRY.6bac9adea19e.json"
CHECK_REG = PIN / "check_variant_registry.c471da4b7be9.py"
CHECK_DELTA = PIN / "check_variant_deltas.d33d8f57f4dd.py"
REBASE_TOOL = PIN / "variant_rebase_rev29.e9521823b8bb.py"
REBASE_REPORT = PIN / "variant_rebase_rev29_report.json"

EXPECTED = {
    A_MANIFEST: "3d9e3d77fd87",
    A_MANIFEST_2: "3d9e3d77fd87",
    B_MANIFEST: "815e08079aef",
    WCC_OLD: "45b9b6a8d192",
    WCC_NEW: "64b8d6394a04",
    C0_OLD: "c28795b0fdfc",
    C0_NEW: "7c165a9063c6",
    REG_OLD: "5eb42f9a384a",
    REG_NEW: "6bac9adea19e",
    CHECK_REG: "c471da4b7be9",
    CHECK_DELTA: "d33d8f57f4dd",
    REBASE_TOOL: "e9521823b8bb",
    REBASE_REPORT: "f97c95a39de7",
}

WATCHED_LIVE = [
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json",
    "artifacts/formulation/evidence/variant_rebase_rev29_report.json",
    "artifacts/formulation/tools/regenerate_frozen.py",
    "artifacts/formulation/tools/variant_rebase_rev29.py",
    "artifacts/formulation/tools/check_variant_registry.py",
    "artifacts/formulation/tools/check_variant_deltas.py",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]


def leaf_diff(a, b, path=""):
    """Recursive structural diff -> list of (path, kind, old, new)."""
    out = []
    if type(a) is not type(b):
        return [(path, "TYPE", a, b)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + "/" + k, "ADDED", None, b[k]))
            elif k not in b:
                out.append((path + "/" + k, "REMOVED", a[k], None))
            else:
                out += leaf_diff(a[k], b[k], path + "/" + k)
    elif isinstance(a, list):
        if a != b:
            if len(a) != len(b):
                out.append((path, "LISTLEN", len(a), len(b)))
            for i in range(min(len(a), len(b))):
                if a[i] != b[i]:
                    out += leaf_diff(a[i], b[i], f"{path}[{i}]")
    elif a != b:
        out.append((path, "CHANGED", a, b))
    return out


def main() -> int:
    # entry measurement of the live tree
    entry = {p: (sha256(ROOT / p) if (ROOT / p).exists() else None) for p in WATCHED_LIVE}
    checks = {}
    controls = []

    def control(cid, desc, passed, evidence):
        controls.append({"id": cid, "description": desc, "passed": bool(passed), "evidence": evidence})
        return passed

    # ---- P1: pin verification -------------------------------------------------
    pins = {}
    pin_ok = True
    for p, want in EXPECTED.items():
        got = sha256(p)
        pins[str(p.relative_to(TASK))] = {"want_prefix": want, "sha256": got, "matches": got.startswith(want)}
        pin_ok &= got.startswith(want)
    control("K1-pin-hashes", "every pinned input hashes to its recorded prefix", pin_ok,
            {k: v["matches"] for k, v in pins.items()})

    A, A2, B = load(A_MANIFEST), load(A_MANIFEST_2), load(B_MANIFEST)
    dual_source_equal = A_MANIFEST.read_bytes() == A_MANIFEST_2.read_bytes()
    control("K2-dual-source-A", "two independent A-era snapshots (worker-007 preflight, worker-074 landing guard) are byte-identical",
            dual_source_equal, {"worker007": sha256(A_MANIFEST)[:16], "worker074": sha256(A_MANIFEST_2)[:16]})

    # ---- P2: path-level delta A -> B -----------------------------------------
    fa, fb = A["files"], B["files"]
    added = sorted(set(fb) - set(fa))
    removed = sorted(set(fa) - set(fb))
    modified = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    changed_paths = sorted(set(added) | set(removed) | set(modified))
    live_match = {}
    for k in changed_paths:
        live = sha256(ROOT / k) if (ROOT / k).exists() else None
        live_match[k] = {"live": live, "B": fb.get(k, {}).get("sha256"), "live_matches_B": live == fb.get(k, {}).get("sha256")}
    control("K3-live-matches-B", "all changed/added paths on disk equal the B manifest entry",
            all(v["live_matches_B"] for v in live_match.values()) and not removed,
            {"changed": len(changed_paths), "removed": len(removed)})

    # unchanged class schemas across A, B and live
    schema_paths = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
    schema_stable = all(fa.get(s, {}).get("sha256") == fb.get(s, {}).get("sha256") == sha256(ROOT / s) for s in schema_paths)
    control("K4-schemas-stable", "F1/F2a/F2b schema bytes are identical in A, B and live (drift is outside the class schemas)",
            schema_stable, {s: sha256(ROOT / s)[:12] for s in schema_paths})

    # ---- P3: content-level diff ----------------------------------------------
    content = {}
    wcc_old, wcc_new = load(WCC_OLD), load(WCC_NEW)
    c0_old, c0_new = load(C0_OLD), load(C0_NEW)
    reg_old, reg_new = load(REG_OLD), load(REG_NEW)
    content["AF-WCC-VAC-GEN.variant-SET.delta.json"] = leaf_diff(wcc_old, wcc_new)
    content["AF-SCC-C0-VAC-GEN.variant-CH.delta.json"] = leaf_diff(c0_old, c0_new)
    content["VARIANT_REGISTRY.json"] = leaf_diff(reg_old, reg_new)

    def set_strength(reg):
        for v in reg.get("variants", []):
            if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
                return v.get("strength")
        return None

    wcc_strength_old, wcc_strength_new = wcc_old.get("strength"), wcc_new.get("strength")
    reg_strength_old, reg_strength_new = set_strength(reg_old), set_strength(reg_new)
    semantic_flip = (
        "strictly stronger" in wcc_strength_old.lower() and "strictly weaker" in wcc_strength_new.lower()
    )
    control("K5-direction-flip-is-semantic", "the WCC SET strength assertion reversed direction (stronger -> weaker) in both the delta and the registry",
            semantic_flip and "STRONGER" in reg_strength_old and "weaker" in reg_strength_new,
            {"delta_old": wcc_strength_old[:80], "delta_new": wcc_strength_new[:80]})

    # ---- P4: revision discipline ---------------------------------------------
    rev_same = A.get("revision") == B.get("revision") == 29
    frozen_at = {"A": A.get("frozen_at"), "B": B.get("frozen_at")}
    # search accepted stream + owner outbox for a STRUCTURAL revision-30 declaration targeting FROZEN.
    # Free-text mentions ("unless a rev30 is issued") are informational only, not a bump.
    bump_hits = []
    freetext_mentions = 0

    def structural_rev30(node):
        hits = []
        if isinstance(node, dict):
            rev = node.get("revision")
            if rev == 30 and ("FROZEN" in str(node.get("path", "")) or node.get("artifact_type") in {"frozen_manifest", "freeze_manifest"}):
                hits.append(node.get("event_id") or node.get("path"))
            if "FROZEN" in str(node.get("supersedes", "")) and "30" in str(node.get("supersedes", "")):
                hits.append(node.get("event_id"))
            for v in node.values():
                hits += structural_rev30(v)
        elif isinstance(node, list):
            for v in node:
                hits += structural_rev30(v)
        return hits

    for src in ["research_map/events.jsonl", "comms/outbox/astra-lead-formulation.jsonl"]:
        sp = ROOT / src
        if not sp.exists():
            continue
        for i, line in enumerate(sp.read_text(errors="replace").splitlines(), 1):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            hits = structural_rev30(ev)
            if hits:
                bump_hits.append({"source": src, "line": i, "hits": hits})
            if re.search(r"rev30|revision 30", line):
                freetext_mentions += 1
    control("K6-same-revision", "revision held at 29 across A->B and no structural rev-30 / supersedes declaration for FROZEN exists in the accepted stream or owner outbox",
            rev_same and not bump_hits,
            {"revision_A": A.get("revision"), "revision_B": B.get("revision"),
             "structural_bump_hits": len(bump_hits), "free_text_mentions_only": freetext_mentions})

    # announcement events for the changed paths / the B manifest itself
    owner_lines = []
    op = ROOT / "comms/outbox/astra-lead-formulation.jsonl"
    if op.exists():
        for line in op.read_text(errors="replace").splitlines():
            try:
                owner_lines.append(json.loads(line))
            except Exception:
                continue
    announcements = {}
    for k in changed_paths:
        h = (fb.get(k) or {}).get("sha256")
        evs = [e for e in owner_lines if e.get("path") == k and e.get("sha256") == h]
        announcements[k] = {
            "declared": bool(evs),
            "event_id": evs[0].get("event_id") if evs else None,
            "created_at": evs[0].get("created_at") if evs else None,
        }
    manifest_ev = [e for e in owner_lines if e.get("path") == "artifacts/formulation/FROZEN.json" and e.get("sha256") == sha256(B_MANIFEST)]
    manifest_ev = manifest_ev[0] if manifest_ev else None
    all_declared = all(v["declared"] for v in announcements.values()) and manifest_ev is not None
    order_ok = bool(manifest_ev) and all(
        (v["created_at"] or "") >= B.get("frozen_at", "") for v in announcements.values() if v["created_at"]
    )
    control("K7-declared-but-after-manifest",
            "every changed path is announced with the B hash, but all those events postdate the B frozen_at (manifest re-written before its changed content was declared)",
            all_declared and order_ok,
            {"manifest_publish_event": (manifest_ev or {}).get("event_id"),
             "manifest_event_created_at": (manifest_ev or {}).get("created_at"),
             "B_frozen_at": B.get("frozen_at")})

    # ---- P5: reviewer pin reconciliation -------------------------------------
    pin_re = {"A": "3d9e3d77", "B": "815e08079aef"}
    review_rows = []
    rdir = ROOT / "reviews"
    NARRATIVE = {"findings", "notes", "text", "summary", "statement", "description", "risk", "claim"}

    def structured_hash_keys(node, prefix=""):
        out = []
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and k not in NARRATIVE:
                    for tag, h in pin_re.items():
                        if h in v:
                            out.append(f"{prefix}/{k}={tag}")
                out += structured_hash_keys(v, f"{prefix}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                out += structured_hash_keys(v, f"{prefix}[{i}]")
        return out

    if rdir.exists():
        for f in sorted(rdir.glob("*.json")):
            raw = f.read_text(errors="replace")
            pins_here = [k for k, h in pin_re.items() if h in raw]
            if not pins_here:
                continue
            try:
                d = json.loads(raw)
            except Exception:
                d = {}
            review_rows.append({
                "file": str(f.relative_to(ROOT)),
                "reviewer": d.get("reviewer"),
                "target_id": (d.get("target_id") or "")[:90],
                "verdict": d.get("verdict"),
                "score": d.get("score"),
                "created_at": d.get("created_at") or d.get("timestamp"),
                "pins": pins_here,
                "structured_pin_keys": structured_hash_keys(d),
                "mtime": datetime.fromtimestamp(f.stat().st_mtime, TZ).replace(microsecond=0).isoformat(),
            })
    a_pinned = [r for r in review_rows if "A" in r["pins"] and (r["created_at"] or "") >= "2026-09-12T00:53:00"]
    b_pinned = [r for r in review_rows if "B" in r["pins"] and (r["created_at"] or "") >= "2026-09-12T00:53:00"]
    structured_A = [r for r in a_pinned if any(k.endswith("=A") for k in r["structured_pin_keys"])]
    control("K8-a-pinned-verdicts-exist",
            "at least one r3-window review verdict carries a STRUCTURED reviewed_sha256 binding to the pre-drift A manifest while later verdicts cite B",
            len(structured_A) > 0 and len(b_pinned) > 0,
            {"A_citing": len(a_pinned), "A_structured_binding": len(structured_A), "B_citing": len(b_pinned),
             "example": structured_A[0]["file"] if structured_A else None,
             "example_keys": structured_A[0]["structured_pin_keys"] if structured_A else None})

    # ---- P6: checker integrity ------------------------------------------------
    reg_check_src = CHECK_REG.read_text()
    predicate = 'if "STRONGER" not in setv.get("strength", ""):'
    predicate_present = predicate in reg_check_src
    live_set_strength = reg_strength_new or ""
    note = re.findall(r"\[[^\]]*STRONGER[^\]]*\]", live_set_strength)
    passes_with_note = "STRONGER" in live_set_strength
    stripped = re.sub(r"\[[^\]]*STRONGER[^\]]*\]", "", live_set_strength)
    passes_without_note = "STRONGER" in stripped
    control("K9-checker-predicate", "the registry checker's only SET-direction test is a substring test for STRONGER; it passes only because the corrected entry quotes the old direction in a note",
            predicate_present and passes_with_note and not passes_without_note,
            {"predicate": predicate, "note_found": note[:1], "passes_with_note": passes_with_note, "passes_after_note_removal": passes_without_note})

    # run both checkers in a sandbox copy (they write into their ROOT)
    sb = TASK / "sandbox"
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "schemas").mkdir(parents=True)
    (sb / "artifacts/formulation/variants").mkdir(parents=True)
    (sb / "artifacts/formulation/schemas").mkdir(parents=True)
    (sb / "artifacts/formulation/tools").mkdir(parents=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True)
    for s in schema_paths:
        shutil.copy2(ROOT / s, sb / s)
    for s in (ROOT / "artifacts/formulation/schemas").glob("*.yaml"):
        shutil.copy2(s, sb / "artifacts/formulation/schemas" / s.name)
    shutil.copy2(ROOT / "artifacts/formulation/FROZEN.json", sb / "artifacts/formulation/FROZEN.json")
    shutil.copy2(ROOT / "artifacts/formulation/VARIANT_REGISTRY.json", sb / "artifacts/formulation/VARIANT_REGISTRY.json")
    for v in (ROOT / "artifacts/formulation/variants").glob("*.delta.json"):
        shutil.copy2(v, sb / "artifacts/formulation/variants" / v.name)
    shutil.copy2(CHECK_DELTA, sb / "artifacts/formulation/tools/check_variant_deltas.py")
    shutil.copy2(CHECK_REG, sb / "artifacts/formulation/tools/check_variant_registry.py")
    runs = {}
    for name in ["check_variant_deltas", "check_variant_registry"]:
        r = subprocess.run([sys.executable, str(sb / f"artifacts/formulation/tools/{name}.py")],
                           capture_output=True, text=True, timeout=120)
        runs[name] = {"exit": r.returncode, "stdout": r.stdout.strip()[:400], "stderr": r.stderr.strip()[:200]}
    control("K10-checkers-pass-on-current-bytes",
            "sandboxed rerun reproduces the owner's VALID claims on the current bytes",
            all(v["exit"] == 0 for v in runs.values()), runs)

    # mutation: remove the mention note from the sandbox registry and rerun the registry checker
    mut = sb / "artifacts/formulation/VARIANT_REGISTRY.json"
    mut_text = mut.read_text()
    mut_stripped = re.sub(r"\[[^\]]*STRONGER[^\]]*\]", "", mut_text)
    mut.write_text(mut_stripped)
    rm = subprocess.run([sys.executable, str(sb / "artifacts/formulation/tools/check_variant_registry.py")],
                        capture_output=True, text=True, timeout=120)
    control("K11-note-removal-mutation",
            "deleting only the bracketed 'corrected from STRONGER' note turns the registry checker INVALID (proves the pass was a metalinguistic mention, not a direction check)",
            rm.returncode != 0, {"exit": rm.returncode, "stdout": rm.stdout.strip()[:300]})
    # restore sandbox file for reproducibility
    mut.write_text(mut_text)

    # self-diff control
    control("K12-self-diff-zero", "diffing B against itself yields zero changed paths",
            len([k for k in set(fb) if fb[k] != fb[k]]) == 0, {})

    # ---- exit measurement / drift --------------------------------------------
    exit_ = {p: (sha256(ROOT / p) if (ROOT / p).exists() else None) for p in WATCHED_LIVE}
    drift = {p: {"entry": entry[p], "exit": exit_[p]} for p in WATCHED_LIVE if entry[p] != exit_[p]}
    control("K13-entry-equals-exit", "no watched live input drifted during the adjudication", not drift, {"drift": drift})

    # ---- assemble measurements / report ---------------------------------------
    findings = [
        {
            "id": "W040-DRIFT-07a",
            "severity": "major",
            "statement": ("FROZEN rev29 was re-written in place at frozen_at 2026-09-12T00:57:26+08:00 "
                          "(3d9e3d77fd87 -> 815e08079aef) with the revision number held at 29 and with 7 bound "
                          "paths moved: 5 modified and 2 added. The A-era manifest (worker-007 preflight, "
                          "reproduced byte-for-byte by worker-074's landing-guard snapshot) and the live B "
                          "manifest are both hash-verified here."),
            "evidence": ["pinned/FROZEN.rev29.3d9e3d77fd87.json", "pinned/FROZEN.rev29.3d9e3d77.secondsource.json",
                         "pinned/FROZEN.rev29.815e08079aef.json"],
        },
        {
            "id": "W040-DRIFT-07b",
            "severity": "major",
            "statement": ("The move is not meta-document drift: it flips a class-relevant assertion. "
                          "AF-WCC-VAC-GEN variant SET strength changed from 'strictly stronger than AF-WCC-VAC-GEN' "
                          "to 'strictly weaker than ... (omega-chain witness, W076-GFORM-STRICTNESS-RECONCILE-06 T4)' "
                          "in both artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json and "
                          "artifacts/formulation/VARIANT_REGISTRY.json. The C0 CH delta change is a mechanical "
                          "base re-pin (rev12->rev13) plus a note; the registry's SET flip is the only semantic write."),
            "evidence": ["measurements.json#content_diff"],
        },
        {
            "id": "W040-DRIFT-07c",
            "severity": "major",
            "statement": ("Order of operations inverted relative to the manifest's own change_protocol: the B "
                          "manifest was written at 00:57:26 and the first artifact event declaring any of the "
                          "changed/added paths carries created_at 00:57:43; the manifest-publish event "
                          "lead-form-20260912T005743-06 is also 00:57:43. change_protocol requires the artifact "
                          "event with the new sha256, a revision bump, and re-run gate tests for canonical-artifact "
                          "changes; revision stayed 29 and no rev-30/supersedes event exists."),
            "evidence": ["measurements.json#announcements"],
        },
        {
            "id": "W040-DRIFT-07d",
            "severity": "major",
            "statement": ("Reviewer verdicts are split across two manifests with the same revision label. In the "
                          "G-FORM r3 window several verdicts cite A=3d9e3d77 and at least one carries a structured "
                          "binding: reviews/F1-review-worker-018.json has "
                          "reviewed_sha256['artifacts/formulation/FROZEN.json']=3d9e3d77fd87 with verdict revise at "
                          "00:57:00, 26 s before B was written; worker-017 (F2a accept) and worker-001 (F2b accept) "
                          "record the supersession in their re-anchor text, and later verdicts cite B=815e08079aef. "
                          "Because change_protocol says 'reviewers bind to the sha256 below, never to the path alone', "
                          "an A-bound verdict cannot be counted at B; and because the revision was not bumped, no "
                          "revision label distinguishes them."),
            "evidence": ["measurements.json#reviewer_pins", "reviews/F1-review-worker-018.json"],
        },
        {
            "id": "W040-DRIFT-07e",
            "severity": "major",
            "statement": ("Checker integrity: the owner's claim 'check_variant_registry VALID' reproduces (exit 0) but "
                          "is vacuous for the assertion it is cited for. check_variant_registry.py's only SET-direction "
                          "test is `if \"STRONGER\" not in setv.get(\"strength\", \"\")`; the corrected registry entry "
                          "passes only because it quotes the old wrong direction in the bracketed note "
                          "\"[rev13 direction corrected from 'strictly STRONGER']\". Removing that note alone makes the "
                          "checker INVALID. This is the CF-16 metalinguistic-mention false-positive family: a mention of "
                          "the wrong direction satisfies the direction check. check_variant_deltas.py does not test "
                          "direction at all (base hash / path / from-match / no-op / falsifier only)."),
            "evidence": ["pinned/check_variant_registry.c471da4b7be9.py", "controls.json#K9", "controls.json#K11"],
        },
        {
            "id": "W040-DRIFT-07f",
            "severity": "info",
            "statement": ("Credit: the rewrite is not stealth. The owner announced it (lead-form-20260912T005743-06 "
                          "and -09..-13, all created_at 00:57:43), and workers 001, 019, 029, 085, 089 and 066 recorded "
                          "the manifest churn in their reviews. The manifest's own rev29_delta was extended with a "
                          "'Downstream: ...' sentence documenting the re-base. The finding is discipline and evidence "
                          "reuse, not concealment."),
            "evidence": ["comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T005743-06"],
        },
    ]
    verdict = {
        "verdict": "revise",
        "score": 2.5,
        "target_id": "artifacts/formulation/FROZEN.json#815e08079aef",
        "summary": ("The B rewrite repairs real residuals (L-FORM-03 direction in the SET variant delta/registry, "
                    "rev13 base re-pins) and all seven changed paths are announced and live-consistent, but it holds "
                    "revision 29, postdates its own declarations, and leaves A-bound r3 verdicts unreconciled. "
                    "Recommended: publish it as rev30 (revision + revised_at bump, fresh artifact event) and require "
                    "the r3 reviewers to re-pin at B; separately repair the registry checker's SET-direction test."),
    }
    claim = {
        "statement": ("The G-FORM r3 verdicts bound to FROZEN rev29 3d9e3d77fd87 are not reusable at the live "
                      "rev29 815e08079aef: the same revision label covers two manifests whose bound variant artifacts "
                      "assert opposite SET-strength directions. Closing G-FORM needs a controller decision: bump to "
                      "rev30 and re-pin the reviews, or record an explicit same-revision exception with the exact "
                      "changed-path list and force a re-pin."),
        "conclusion_type": "open_problem",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
    }
    falsifier = (
        "Falsified if (i) either A or B snapshot fails its recorded sha256, or the two independent A snapshots differ; "
        "(ii) any changed path's live bytes equal the A hash rather than the B hash; (iii) a revision-bump or "
        "supersedes event for FROZEN rev30 exists in research_map/events.jsonl or the owner outbox; (iv) the SET "
        "strength strings in A and B assert the same direction (i.e. the change is not semantic); (v) removing the "
        "bracketed 'corrected from STRONGER' note from VARIANT_REGISTRY.json still leaves check_variant_registry.py "
        "VALID (i.e. the pass was a real direction check); or (vi) every r3-window review verdict cites B, leaving no "
        "A-bound verdict to reconcile."
    )

    measurements = {
        "task_id": "W040-FROZEN-REV29-DRIFT-07",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "measured_at": now(),
        "pins": pins,
        "manifest_A": {"sha256": sha256(A_MANIFEST), "revision": A.get("revision"), "frozen_at": A.get("frozen_at"), "file_count": len(fa)},
        "manifest_B": {"sha256": sha256(B_MANIFEST), "revision": B.get("revision"), "frozen_at": B.get("frozen_at"), "file_count": len(fb)},
        "path_delta": {"added": added, "removed": removed, "modified": modified, "changed_count": len(changed_paths)},
        "live_match": live_match,
        "schemas_stable": schema_stable,
        "content_diff": {k: [{"path": p, "kind": kind, "old": o, "new": n} for p, kind, o, n in v]
                         for k, v in content.items()},
        "set_strength": {"delta_old": wcc_strength_old, "delta_new": wcc_strength_new,
                         "registry_old": reg_strength_old, "registry_new": reg_strength_new},
        "revision_discipline": {"revision_A": A.get("revision"), "revision_B": B.get("revision"),
                                "frozen_at_A": A.get("frozen_at"), "frozen_at_B": B.get("frozen_at"),
                                "rev30_or_supersedes_hits": bump_hits},
        "announcements": announcements,
        "manifest_publish_event": {"event_id": (manifest_ev or {}).get("event_id"),
                                   "created_at": (manifest_ev or {}).get("created_at"),
                                   "sha256": (manifest_ev or {}).get("sha256")},
        "reviewer_pins": {"window_start": "2026-09-12T00:53:00+08:00",
                          "A_citing_count": len(a_pinned), "A_structured_binding_count": len(structured_A),
                          "B_citing_count": len(b_pinned),
                          "A_citing": a_pinned, "B_citing": b_pinned},
        "checker_runs": runs,
        "checker_mutation_after_note_removal": {"exit": rm.returncode, "stdout": rm.stdout.strip()[:300]},
        "drift_watched": drift,
        "verdict": verdict,
        "claim": claim,
        "falsifier": falsifier,
        "findings": findings,
    }
    (TASK / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")
    (TASK / "controls.json").write_text(json.dumps({"controls": controls,
                                                    "passed": sum(1 for c in controls if c["passed"]),
                                                    "total": len(controls)}, indent=2) + "\n")
    report = {
        "task_id": "W040-FROZEN-REV29-DRIFT-07",
        "class_id": claim["class_id"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "created_at": now(),
        "verdict": verdict,
        "claim": claim,
        "falsifier": falsifier,
        "findings": findings,
        "recommended_disposition": [
            "1. Re-publish FROZEN as rev30 with a revision/revised_at bump and a fresh artifact event; do not let two manifest identities share the label rev29.",
            "2. Require the G-FORM r3 reviewers to re-pin at the new manifest hash; the three class schema bytes are unchanged, so this is a re-bind of the manifest pin, not a re-review of class content.",
            "3. Repair check_variant_registry.py: test the asserted direction semantically (e.g. require 'strictly weaker' for SET and forbid the direction token from appearing only inside a bracketed note), and add the note-removal mutation as a permanent control.",
            "4. Record whether 'valid' checker output is evidence for a semantic assertion or only for structural well-formedness; CURRENT: the SET-direction VALID is structural only.",
        ],
        "prior_observations_credited": [
            "CF-27 (controller): binding document moved inside the r3 review window under the same revision number",
            "worker-029 F-W029-F1-05, worker-019 rev13 preflight, worker-085, worker-089, worker-001, worker-066: recorded FROZEN churn 3d9e3d77 -> 815e08079aef",
        ],
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    entry_hashes = {"task_id": report["task_id"], "created_at": report["created_at"], "entry": entry, "exit": exit_, "drift": drift}
    (TASK / "entry_hashes.json").write_text(json.dumps(entry_hashes, indent=2) + "\n")

    print(json.dumps({"controls_passed": f"{sum(1 for c in controls if c['passed'])}/{len(controls)}",
                      "changed_paths": len(changed_paths), "A_bound_reviews": len(a_pinned), "B_bound_reviews": len(b_pinned),
                      "checkers": {k: v["exit"] for k, v in runs.items()},
                      "note_removal_exit": rm.returncode, "drift": len(drift)}, indent=1))
    return 0 if all(c["passed"] for c in controls) else 1


if __name__ == "__main__":
    sys.exit(main())
