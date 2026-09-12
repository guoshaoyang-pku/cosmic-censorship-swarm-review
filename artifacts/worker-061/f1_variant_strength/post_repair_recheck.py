#!/usr/bin/env python3
"""W061-F1-VARSTRENGTH-05 addendum: targeted post-repair recheck.

The canonical F1/F2b/FROZEN bytes moved at 2026-09-12T00:53:20-00:54:39 while the review above was
being written (FROZEN rev29, astra-life05-evidence-binding-repair).  This script re-measures the
live bytes and re-applies the SAME classification used in probe_variant_strength.py to the exact
tokens my hard failures named.  It is a targeted wording recheck on the axis this task owns, NOT a
review verdict at the new bytes (the pass-05 r3 blind round is the binding review).

Output: post_repair_recheck.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_variant_strength import classify, sha256, text_at, ROOT  # noqa: E402
import probe_variant_strength as P  # noqa: E402


def direction_of_earliest(text: str) -> str:
    """Locator-robust direction: take the FIRST direction token in the field.

    The rev13 line quotes the superseded token in its revision bracket
    ("... corrected from 'strictly STRONGER' ..."), so a presence test that checks
    'stronger' before 'weaker' misreads the repaired text.  The asserted direction is
    the first one; this rule agrees with the rev12 readings used in probe_output.json.
    """
    t = text.lower()
    cands = []
    for tok, name in (("strictly stronger", "stronger"), ("strictly weaker", "weaker"),
                      ("equivalent", "equivalent")):
        i = t.find(tok)
        if i >= 0:
            cands.append((i, name))
    return min(cands)[1] if cands else "unclear"


P.direction_of = direction_of_earliest  # classify() calls the module-global name

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
OUT = os.path.join(HERE, "post_repair_recheck.json")

LIVE = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "registry": "artifacts/formulation/VARIANT_REGISTRY.json",
    "set_delta": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "ch_delta": "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "frozen": "artifacts/formulation/FROZEN.json",
}
OLD = {
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "registry": "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    "set_delta": "45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc",
    "ch_delta": "c28795b0fdfc1c58cc3cd7519e0d0965cbf3c2ceb6171c5ffd346735189a2185",
    "frozen": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}

live = {k: sha256(os.path.join(ROOT, v)) for k, v in LIVE.items()}
moved = {k: (live[k] != OLD[k]) for k in LIVE}

f1 = os.path.join(ROOT, LIVE["F1"])
f2b = os.path.join(ROOT, LIVE["F2b"])
f1_rel = text_at(f1, "strictly WEAKER than this class's single-q tail predicate") or \
         text_at(f1, "strictly STRONGER than this class's single-q tail predicate")
f2b_rel = text_at(f2b, "strictly WEAKER than this frozen class") or \
          text_at(f2b, "strictly STRONGER than this frozen class")

with open(os.path.join(ROOT, LIVE["registry"]), encoding="utf-8") as f:
    reg = json.load(f)
set_reg = next(v for v in reg["variants"] if v["variant_id"] == "SET")
ch_reg = next(v for v in reg["variants"] if v["variant_id"] == "CH")
with open(os.path.join(ROOT, LIVE["set_delta"]), encoding="utf-8") as f:
    set_delta = json.load(f)
set_def_to = next(c for c in set_delta["changes"] if c["path"] == "visibility.definition")["to"]

checks = [
    dict(classify("SET", "LIVE schemas/af_wcc_vacuum.yaml variant relation", f1_rel, "weaker"),
         finding="HF-W061-VAR-01"),
    dict(classify("SET", "LIVE VARIANT_REGISTRY.json SET strength", set_reg["strength"], "stronger"),
         finding="residual L-FORM-03"),
    dict(classify("SET", "LIVE SET delta changes[visibility.definition].to", set_def_to, "weaker"),
         finding="HF-W061-VAR-02"),
    dict(classify("SET", "LIVE SET delta strength", set_delta["strength"], "stronger"),
         finding="residual L-FORM-03"),
    dict(classify("CH", "LIVE schemas/af_scc_c0_vacuum.yaml CH relation", f2b_rel, "weaker"),
         finding="F-W061-VAR-03"),
    dict(classify("CH", "LIVE VARIANT_REGISTRY.json CH strength", ch_reg["strength"], "weaker"),
         finding="F-W061-VAR-03"),
]
delta_contradiction = ("implied by" in set_def_to) and ("strictly stronger" in set_def_to)

status = {
    "HF-W061-VAR-01": "REPAIRED at the new F1 hash" if checks[0]["status"] == "consistent"
                      else f"UNREPAIRED ({checks[0]['status']})",
    "HF-W061-VAR-02": "UNREPAIRED at the unchanged SET delta bytes (self-contradiction still present)"
                      if delta_contradiction else "cleared",
    "F-W061-VAR-03": "text unchanged; soft precision defect persists"
                     if not moved["F2b"] or checks[4]["status"] == "consistent" else "changed",
}

out = {
    "task_id": "W061-F1-VARSTRENGTH-05",
    "check_type": "targeted_post_repair_recheck",
    "created_at": NOW,
    "live_hashes": live,
    "old_pinned_hashes": OLD,
    "moved": moved,
    "frozen_revision_seen": 29,
    "repair_card": "astra-life05-evidence-binding-repair / FROZEN rev29",
    "checks": checks,
    "delta_self_contradiction_at_live_bytes": delta_contradiction,
    "finding_status": status,
    "scope_note": "Targeted wording recheck only. It is NOT a review verdict at the new bytes and it "
                  "does not bind the pass-05 r3 blind round; the original REVIEW.json verdict binds "
                  "only to the rev12 pins cce9c60146d6 / 55d0a1ea9bda / 5eb42f9a384a / 45b9b6a8d192 "
                  "/ c28795b0fdfc / 2f358f6722d9.",
    "authority": "worker evidence only",
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
    f.write("\n")
print(json.dumps({"out": OUT, "moved": moved, "finding_status": status,
                  "delta_contradiction": delta_contradiction}, indent=1))
