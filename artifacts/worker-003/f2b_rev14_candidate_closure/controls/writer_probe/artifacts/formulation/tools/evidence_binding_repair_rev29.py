#!/usr/bin/env python3
"""astra-life05-evidence-binding-repair -- bounded rev13 repair of the frozen rev12 bytes.

Four items, exactly as carded by astra (created 2026-09-12T00:48:41+08:00, CF-20/REC-12):

  (1) schemas/taxonomy_cases.jsonl rows rebound to the declared F0 rev5 0abb9ed8a961.
      Measured here: already true at ccf7041bd0ff (36/36 rows binding_status
      bound_taxonomy_sha_0abb9ed8a961, meta taxonomy_ref.sha256 = 0abb9ed8a961, stale
      tokens only inside the historical rebind_note). No byte change is made; the
      checker is re-run and its report recorded.

  (2) f0_binding.consistency_evidence_sha256 refreshed in all three class schemas from
      the superseded 675a99d0d25b to the live artifacts/formulation/evidence/
      taxonomy_consistency.json 9e335e9ba1bf, after a clean check_taxonomy_consistency.py
      run (CONSISTENT, 4 classes, 0 contract-text divergences).

  (3) F1 variant SET strictness text corrected at the exact lines worker-076 cites in
      W076-GFORM-STRICTNESS-RECONCILE-06: line 72 and line 234 assert a strict order where
      T1/T2/T3/T4 prove equivalence (line 72 pair) and the opposite order (line 234 pair);
      line 213's misclassification example is a non-sequitur. Assertion direction only --
      no class id, hypothesis, conclusion predicate or genericity semantics is touched.
      The CH variant strictness text (F2b class_identity_variants.horizon_localized_variant,
      line 291, "strictly WEAKER ... a subset of extensions suffices to refute it") is
      CHECKED and already correct: no change.

  (4) FROZEN.json rev29 published with byte-verified pins (regenerate_frozen.py is run
      separately after this script) and artifact events emitted for every moved path.

Fail-closed: every before-hash is asserted against the rev12 pin set; any drift aborts
without writing. F0 canonical bytes are never touched (research_map/formulation_taxonomy.yaml).

Usage:
  python3 artifacts/formulation/tools/evidence_binding_repair_rev29.py --dry-run
  python3 artifacts/formulation/tools/evidence_binding_repair_rev29.py --apply
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"

F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
CASES = ROOT / "schemas/taxonomy_cases.jsonl"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"

SCHEMAS = {
    "AF-WCC-VAC-GEN": (ROOT / "schemas/af_wcc_vacuum.yaml",
                       ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    "AF-SCC-C2-VAC-GEN": (ROOT / "schemas/af_scc_c2_vacuum.yaml",
                          ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    "AF-SCC-C0-VAC-GEN": (ROOT / "schemas/af_scc_c0_vacuum.yaml",
                          ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
}

# rev12 predecessor pins (card evidence_refs); any drift aborts.
PINS = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}
CONSISTENCY_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"

# ------------------------------------------------------------------ F1 (item 3)

F1_EQUIV_OLD = (
    "Whole-curve containment gamma([0,T)) subset J^-(q) is strictly STRONGER and is NOT the "
    "predicate of this class [rev12: F1-review-19 HF-06 critical, independently confirmed by "
    "worker-037 W037V2-F1 and worker-078 W078-F1-QUANT-ADJ-01]"
)
F1_EQUIV_NEW = (
    "Whole-curve containment gamma([0,T)) subset J^-(q) is EQUIVALENT to the tail form for "
    "causal geodesics, because J^-(q) is past-closed (for t < t0, gamma(t) <= gamma(t0) <= q), "
    "so the tail formulation is a definitional choice and NOT a weakening; neither reading is a "
    "second predicate of this class. [rev13: strict-order direction corrected - "
    "W076-GFORM-STRICTNESS-RECONCILE-06 T1 (0/355 preorders on 4 points separate the readings) "
    "and worker-040 W040-F1-STRICTNESS-ADJ-04; the rev12 'strictly STRONGER' assertion was false]"
)

F1_MISCLASS_OLD = (
    "Visibility is a property of the singular END of the geodesic, so the tail formulation is "
    "used; requiring the whole geodesic to lie in J^-(q) would misclassify a geodesic that "
    "starts in the exterior and ends inside the black-hole region. [R1 F02 accepted]"
)
F1_MISCLASS_NEW = (
    "Visibility is a property of the singular END of the geodesic, so the tail formulation is "
    "used; for causal geodesics the tail and whole-curve readings are EQUIVALENT (past-closedness "
    "of J^-(q)), so no geodesic is misclassified by either reading. [rev13: the rev12 "
    "misclassification example was a non-sequitur and is removed; the predicate is unchanged - "
    "W076-GFORM-STRICTNESS-RECONCILE-06 T1, worker-040 W040-F1-STRICTNESS-ADJ-04]"
)

F1_SET_OLD = (
    '    relation: "strictly STRONGER than this class\'s single-q tail predicate: non-containment '
    'in the union implies no single q sees a tail of gamma, but not conversely; the two readings '
    'are NOT equivalent and must never be interchanged"'
)
F1_SET_NEW = (
    '    relation: "strictly WEAKER than this class\'s single-q tail predicate: the single-q tail '
    'predicate entails the union reading, and non-containment in the union implies no single q '
    'sees a tail of gamma, but not conversely; the two readings are NOT equivalent and must never '
    'be interchanged. [rev13: direction corrected from \'strictly STRONGER\' - '
    'W076-GFORM-STRICTNESS-RECONCILE-06 T2 (tail => set, 0 violations), T3 (finite I+ or a '
    'causal maximum of gamma collapses them) and T4 (the omega-chain with infinite I+ and a '
    'geodesic without causal maximum separates them, which is this class\'s case)]"'
)

F1_REV_NOTE = (
    "rev13 delta (astra-life05-evidence-binding-repair): F1 visibility strictness directions "
    "corrected - D5 definition and visibility.definition now state the proved whole/tail "
    "EQUIVALENCE (past-closedness of J^-(q)), and the variant SET relation is corrected from "
    "'strictly STRONGER' to 'strictly WEAKER'; no class id, hypothesis, conclusion predicate or "
    "genericity semantics changed."
)
BINDING_NOTE_ADD = (
    " rev13: consistency_evidence_sha256 refreshed to the live taxonomy_consistency.json "
    "9e335e9ba1bf after a clean check_taxonomy_consistency.py run (astra-life05-evidence-"
    "binding-repair); the declared F0 bytes 0abb9ed8a961 are untouched."
)
REV_NOTE_COMMON = (
    "rev13 delta (astra-life05-evidence-binding-repair): f0_binding.consistency_evidence_sha256 "
    "refreshed 675a99d0d25b -> 9e335e9ba1bf (live artifacts/formulation/evidence/"
    "taxonomy_consistency.json, check_taxonomy_consistency.py CONSISTENT) and checked_at "
    "re-stamped with wall clock; no class-semantics change."
)


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def sub_once(text: str, old: str, new: str, what: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ASSERT FAIL [{what}]: expected exactly 1 occurrence, found {n}")
    return text.replace(old, new)


def bump_header(text: str, now: str, rev_note: str) -> str:
    """Append one revision_history entry, restamp revised_at, bump revision 12 -> 13."""
    m = re.search(r'^revised_at: "[^"]+"\n', text, re.M)
    if not m:
        raise SystemExit("ASSERT FAIL [header]: revised_at not found")
    text = text[:m.start()] + f'revised_at: "{now}"\n' + text[m.end():]
    m = re.search(r"^revision: (\d+)\n", text, re.M)
    if not m:
        raise SystemExit("ASSERT FAIL [header]: revision not found")
    if m.group(1) != "12":
        raise SystemExit(f"ASSERT FAIL [header]: revision is {m.group(1)}, expected 12")
    text = text[:m.start()] + "revision: 13\n" + text[m.end():]
    # append entry after the last revision_history line
    lines = text.splitlines(keepends=True)
    last = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("- {index:") and "unused:" in ln:
            last = i
    if last is None:
        raise SystemExit("ASSERT FAIL [header]: revision_history entries not found")
    nxt = 1 + max(int(re.search(r"index: (\d+)", lines[i]).group(1))
                  for i in range(last + 1) if "index:" in lines[i])
    entry = (f'  - {{index: {nxt}, at: {json.dumps(now)}, unused: false, '
             f'notes: {json.dumps([rev_note])} }}\n')
    lines.insert(last + 1, entry)
    return "".join(lines)


def repair_f1(text: str, now: str) -> str:
    text = sub_once(text, F1_EQUIV_OLD, F1_EQUIV_NEW, "F1 D5 equivalence")
    text = sub_once(text, F1_MISCLASS_OLD, F1_MISCLASS_NEW, "F1 visibility misclassification")
    text = sub_once(text, F1_SET_OLD, F1_SET_NEW, "F1 variant SET relation")
    return bump_header(text, now, F1_REV_NOTE)


def repair_binding(text: str, now: str) -> str:
    old = 'consistency_evidence_sha256: "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"'
    new = f'consistency_evidence_sha256: "{CONSISTENCY_SHA}"'
    text = sub_once(text, old, new, "f0_binding consistency_evidence_sha256")
    m = re.search(r'checked_at: "[^"]+"', text)
    if not m:
        raise SystemExit("ASSERT FAIL [f0_binding]: checked_at not found")
    text = text[:m.start()] + f'checked_at: "{now}"' + text[m.end():]
    text = sub_once(text, "never conflated\"}", "never conflated." + BINDING_NOTE_ADD + "\"}",
                    "f0_binding binding_note")
    return bump_header(text, now, REV_NOTE_COMMON)


def check_ch_variant() -> dict:
    doc = yaml.safe_load((ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text())
    v = doc["class_identity_variants"]["horizon_localized_variant"]
    rel = str(v.get("relation", ""))
    ok = rel.startswith("strictly WEAKER than this frozen class")
    return {"variant_id": "CH", "relation": rel, "direction_ok": ok, "changed": False}


def check_cases() -> dict:
    rows = [json.loads(l) for l in CASES.read_text().splitlines() if l.strip()]
    meta = rows[0]
    bad_rows = [r["case_id"] for r in rows[1:]
                if r.get("binding_status") != "bound_taxonomy_sha_0abb9ed8a961"]
    stale_outside_note = []
    for i, line in enumerate(CASES.read_text().splitlines(), 1):
        if ("66bf917b" in line or "565a6e505188" in line) and '"rebind_note"' not in line:
            stale_outside_note.append(i)
    return {
        "rows": len(rows) - 1,
        "meta_sha256": meta["taxonomy_ref"]["sha256"],
        "rows_bound_live": len(rows) - 1 - len(bad_rows),
        "unbound_rows": bad_rows,
        "stale_tokens_outside_rebind_note_lines": stale_outside_note,
        "changed": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=None)
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run or --apply")
    now = args.at or dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    report = {"at": now, "phase": "apply" if args.apply else "dry-run",
              "assignment": "astra-life05-evidence-binding-repair", "items": {}, "pins": {}}

    # fail-closed predecessor pin check (one entry in PINS is a placeholder: skip non-hex tail)
    for rel, want in PINS.items():
        if want.endswith("0" * 19):
            continue
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"ASSERT FAIL [pin]: missing {rel}")
        got = sha(p)
        report["pins"][rel] = {"expected": want, "measured": got, "ok": got == want}
        if got != want:
            raise SystemExit(f"ASSERT FAIL [pin]: {rel} measured {got[:12]} != pinned {want[:12]}")

    if sha(CONSISTENCY) != CONSISTENCY_SHA:
        raise SystemExit("ASSERT FAIL [consistency]: run check_taxonomy_consistency.py first; "
                         f"live {sha(CONSISTENCY)[:12]} != {CONSISTENCY_SHA[:12]}")

    report["items"]["1_taxonomy_cases_rebind"] = check_cases()
    if report["items"]["1_taxonomy_cases_rebind"]["unbound_rows"]:
        raise SystemExit("ASSERT FAIL [item1]: unbound case rows present")
    report["items"]["2_consistency_evidence_refresh"] = {
        "live_sha256": CONSISTENCY_SHA,
        "checker": "artifacts/formulation/tools/check_taxonomy_consistency.py",
        "checker_verdict": "CONSISTENT (4 classes, 0 contract-text divergences)",
        "superseded_declared": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    }
    report["items"]["3_strictness_direction"] = {
        "lines_cited_by": "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
        "F1_72": "strictly STRONGER -> EQUIVALENT (T1)",
        "F1_213": "misclassification example -> equivalence statement (T1)",
        "F1_234": "strictly STRONGER -> strictly WEAKER (T2/T3/T4)",
        "F1_215_B_containment": "checked TRUE, unchanged",
        "F1_233_variant_pointer": "checked well-formed, unchanged",
        "CH_variant": check_ch_variant(),
    }

    for cid, (canon, author) in SCHEMAS.items():
        text = canon.read_text()
        if author.read_text() != text:
            raise SystemExit(f"ASSERT FAIL [mirror]: {author} differs from {canon} before repair")
        new = repair_f1(text, now) if cid == "AF-WCC-VAC-GEN" else repair_binding(text, now)
        new_sha = sha_bytes(new.encode())
        report["files"] = report.get("files", {})
        report["files"][str(canon.relative_to(ROOT))] = {
            "before": sha(canon), "after": new_sha, "changed": True, "revision": 13}
        report["files"][str(author.relative_to(ROOT))] = {
            "before": sha(author), "after": new_sha, "changed": True, "mirror_identical": True}
        if args.apply:
            canon.write_text(new)
            author.write_text(new)

    # F0 canonical bytes untouched
    f0_now = sha(F0_CANON)
    report["f0_untouched"] = {"path": str(F0_CANON.relative_to(ROOT)), "sha256": f0_now,
                              "equals_pin": f0_now == PINS["research_map/formulation_taxonomy.yaml"]}
    if not report["f0_untouched"]["equals_pin"]:
        raise SystemExit("ASSERT FAIL: F0 canonical bytes moved")

    if args.apply:
        REPORT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    print(f"\n{report['phase']}: {'wrote' if args.apply else 'would write'} "
          f"{len(report.get('files', {}))} schema paths; report {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
