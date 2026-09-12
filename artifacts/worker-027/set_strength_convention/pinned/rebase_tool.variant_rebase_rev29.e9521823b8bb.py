#!/usr/bin/env python3
"""astra-life05-evidence-binding-repair, downstream step: variant re-base to the rev13 bases.

Why this is part of the same bounded repair and not a new scope:

  * The card's expected information gain is "the rev13 schema set [as] hash-bound gate evidence
    instead of a self-contradictory binding chain". check_variant_deltas.py FAILS after the rev13
    publication ("SET/CH: base hash drift"), because both deltas pin their base by sha256 and the
    SET delta's 'from' string is the rev12 visibility.definition text that item 3 corrected.
  * The standard publish flow already rebases deltas when a base moves (FROZEN rev28_delta:
    "variant deltas rebased to the rev12 base hashes"); this is the same mechanical step.
  * The only non-mechanical edit is the SET strength direction, which is the same assertion-direction
    correction as carded item 3 (worker-076 W076-GFORM-STRICTNESS-RECONCILE-06 T2/T3/T4). The
    registry entry that describes the same variant is corrected identically.

No class id, hypothesis, conclusion predicate, genericity or axis semantics is changed. The F0
canonical taxonomy and its supplement (which carry the same inverted note at :200 and :176) are
NOT touched: they need a controller decision (blocker L-FORM-03).

Fail-closed: base hashes and the exact 'from' strings are asserted before writing.

Usage: python3 artifacts/formulation/tools/variant_rebase_rev29.py --dry-run|--apply
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SET_D = ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CH_D = ROOT / "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"
REG = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
F1 = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F2B = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
REPORT = ROOT / "artifacts/formulation/evidence/variant_rebase_rev29_report.json"

PIN_F1 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
PIN_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
OLD_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
OLD_F2B = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"

STRENGTH_OLD = "strictly stronger than AF-WCC-VAC-GEN"
STRENGTH_NEW = ("strictly weaker than AF-WCC-VAC-GEN (the parent's single-q tail predicate entails "
                "the union reading; the converse fails on the omega-chain witness, "
                "W076-GFORM-STRICTNESS-RECONCILE-06 T4)")
TO_OLD = ("This is the SET-based reading of the F0 taxonomy: it is implied by, and strictly stronger "
          "than, the single-q tail predicate.")
TO_NEW = ("This is the SET-based reading of the F0 taxonomy: it is implied by the single-q tail "
          "predicate and is therefore strictly weaker than it (T2: tail => set, 0 violations; T3/T4: "
          "the readings coincide when I+ is finite or gamma has a causal maximum and are separated by "
          "the omega-chain otherwise). [rev13: direction corrected from 'strictly stronger']")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sub_once(t: str, old: str, new: str, what: str) -> str:
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"ASSERT FAIL [{what}]: expected 1 occurrence, found {n}")
    return t.replace(old, new)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=None)
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        ap.error("pass --dry-run or --apply")
    now = a.at or dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    for p, want in ((F1, PIN_F1), (F2B, PIN_F2B)):
        got = sha(p)
        if got != want:
            raise SystemExit(f"ASSERT FAIL [base]: {p.name} {got[:12]} != {want[:12]}")

    rep = {"at": now, "phase": "apply" if a.apply else "dry-run", "files": {}}
    f1_text = F1.read_text()
    m = f1_text.index("  definition: \"a future-inextendible causal geodesic")
    end = f1_text.index("\"\n", m)
    new_vis = f1_text[m + len('  definition: "'):end]
    rep["new_visibility_definition_prefix"] = new_vis[:80]

    # ---- SET delta
    d = json.loads(SET_D.read_text())
    assert d["base"]["sha256"] == OLD_F1, "SET base pin unexpected"
    old_from = d["changes"][1]["from"]
    if not old_from.startswith("a future-inextendible causal geodesic gamma: [0,T) -> M with T < infinity in affine parameter is visible from I+ iff"):
        raise SystemExit("ASSERT FAIL [SET from]: unexpected rev12 text")
    d["base"]["sha256"] = PIN_F1
    d["base"]["revision"] = 13
    d["strength"] = STRENGTH_NEW
    d["changes"][1]["from"] = new_vis
    d["changes"][1]["to"] = sub_once(d["changes"][1]["to"], TO_OLD, TO_NEW, "SET to-direction")
    d["rebased_at"] = now
    d["rebind_note"] = ("astra-life05-evidence-binding-repair rev29: base moved cce9c60146d6->d9cebb9404b2 "
                        "(rev 12->13); 'from' string refreshed against the new frozen base and the SET "
                        "strength direction corrected from 'strictly stronger' to 'strictly weaker' "
                        "(assertion direction only; W076-GFORM-STRICTNESS-RECONCILE-06).")
    if "artifacts/worker-076/gform_strictness_reconcile/probe_result.json" not in d["evidence_refs"]:
        d["evidence_refs"].append("artifacts/worker-076/gform_strictness_reconcile/probe_result.json")
    set_bytes = (json.dumps(d, indent=2) + "\n").encode()
    rep["files"]["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"] = {
        "before": sha(SET_D), "after": hashlib.sha256(set_bytes).hexdigest(), "changed": True}

    # ---- CH delta (mechanical re-base only; its 'strictly WEAKER' direction was already correct)
    c = json.loads(CH_D.read_text())
    assert c["base"]["sha256"] == OLD_F2B, "CH base pin unexpected"
    c["base"]["sha256"] = PIN_F2B
    c["base"]["revision"] = 13
    c["rebased_at"] = now
    c["rebind_note"] = ("astra-life05-evidence-binding-repair rev29: base moved 55d0a1ea9bda->b2ab6acb2bbe "
                        "(rev 12->13); no 'from' string changed (the rev13 edits touch only the header and "
                        "f0_binding of the base). Strength direction checked correct and unchanged.")
    ch_bytes = (json.dumps(c, indent=2) + "\n").encode()
    rep["files"]["artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"] = {
        "before": sha(CH_D), "after": hashlib.sha256(ch_bytes).hexdigest(), "changed": True}

    # ---- registry: same SET strength direction. Patched as TEXT (the registry keeps short lists
    # inline, so a json.dumps round-trip would reformat unrelated lines).
    reg_text = REG.read_text()
    reg_old = ('"strength": "strictly STRONGER than AF-WCC-VAC-GEN: gamma not contained in the union '
               'J^-(I+) implies no single past J^-(q) contains a tail of gamma, but not conversely"')
    reg_new = ('"strength": "' + STRENGTH_NEW + ': gamma not contained in the union J^-(I+) implies '
               'no single past J^-(q) contains a tail of gamma, but not conversely [rev13 direction '
               'corrected from \'strictly STRONGER\']"')
    reg_text = sub_once(reg_text, reg_old, reg_new, "registry SET strength")
    reg = json.loads(reg_text)
    n_set = sum(1 for e in reg.get("variants", [])
                if e.get("variant_id") == "SET" and e.get("parent_class") == "AF-WCC-VAC-GEN"
                and "strictly weaker" in e.get("strength", "").lower())
    if n_set != 1:
        raise SystemExit(f"ASSERT FAIL [registry]: SET strength not corrected ({n_set})")
    reg_bytes = reg_text.encode()
    rep["files"]["artifacts/formulation/VARIANT_REGISTRY.json"] = {
        "before": sha(REG), "after": hashlib.sha256(reg_bytes).hexdigest(), "changed": True}

    if a.apply:
        SET_D.write_bytes(set_bytes)
        CH_D.write_bytes(ch_bytes)
        REG.write_bytes(reg_bytes)
        REPORT.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
