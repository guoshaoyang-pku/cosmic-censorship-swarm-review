#!/usr/bin/env python3
"""W024-SET-STRENGTH-REPAIR-01 build step (deterministic, read-only on canonical paths).

Produces unfrozen candidates for the three FROZEN rev29 members that carry the
SET strength-direction defect measured by worker-094 (F0V-SETDIR-03/04/CHECKER)
and confirmed by astra-lead-formulation lifecycle-07 (measurement_6):

  artifacts/formulation/VARIANT_REGISTRY.json          (strength at line 57)
  artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json (strength at line 11)
  artifacts/formulation/tools/check_variant_registry.py (SET clause at lines 89-91)

No canonical file is written. Every replacement is a literal, exact string
substitution; bytes outside the three sites are preserved.
"""
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-024/set_strength_repair"
OUT.mkdir(parents=True, exist_ok=True)

REG = "artifacts/formulation/VARIANT_REGISTRY.json"
DEL = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CHK = "artifacts/formulation/tools/check_variant_registry.py"

STRENGTH_LIVE = (
    '"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent\'s single-q tail predicate '
    "entails the union reading; the converse fails on the omega-chain witness, "
    'W076-GFORM-STRICTNESS-RECONCILE-06 T4)'
)
STRENGTH_REG_LIVE = STRENGTH_LIVE + (
    ': gamma not contained in the union J^-(I+) implies no single past J^-(q) contains a tail of '
    'gamma, but not conversely [rev13 direction corrected from \'strictly STRONGER\']",'
)
STRENGTH_DEL_LIVE = STRENGTH_LIVE + '",'

# One level-qualified label, byte-identical in both artifacts so the two
# declarations cannot drift apart. The positive assertions sit OUTSIDE any
# bracket note, so a note-stripping assertion-aware checker sees them.
STRENGTH_FIXED = (
    '"strength": "strictly STRONGER than AF-WCC-VAC-GEN as a class statement '
    "(not-S entails not-P: gamma not contained in the union J^-(I+) implies no single past J^-(q) "
    "contains a tail of gamma, but not conversely), while the SET predicate S is strictly WEAKER "
    "than the parent's single-q tail predicate P (P entails S; the converse fails on the omega-chain "
    "witness, W076-GFORM-STRICTNESS-RECONCILE-06 T4) [rev14 level correction: the prior label "
    "applied the predicate-level direction to the class subject, and check_variant_registry.py "
    'matched only this bracket provenance note]",'
)

CHECK_LIVE = '''setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
if "STRONGER" not in setv.get("strength", ""):
    errs.append("variant SET must be marked stronger than its parent")
'''
CHECK_FIXED = '''setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
set_strength = setv.get("strength", "")
while "[" in set_strength and "]" in set_strength:  # strip provenance notes before asserting
    set_strength = set_strength[:set_strength.index("[")] + set_strength[set_strength.index("]") + 1:]
if "STRONGER than AF-WCC-VAC-GEN" not in set_strength:
    errs.append("variant SET must be marked class-level stronger than its parent")
if "class statement" not in set_strength:
    errs.append("variant SET strength must be level-qualified as a class statement")
if "WEAKER than the parent's single-q tail predicate" not in set_strength:
    errs.append("variant SET strength must record the predicate-level weakening")
'''

EDITS = [
    (REG, "CANDIDATE_VARIANT_REGISTRY.json", STRENGTH_REG_LIVE, STRENGTH_FIXED, 1),
    (DEL, "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json", STRENGTH_DEL_LIVE, STRENGTH_FIXED, 1),
    (CHK, "CANDIDATE_check_variant_registry.py", CHECK_LIVE, CHECK_FIXED, 1),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    entry, cand_info, problems = {}, {}, []
    for src, dst, old, new, expect in EDITS:
        sb = (ROOT / src).read_bytes()
        text = sb.decode("utf-8")
        n = text.count(old)
        if n != expect:
            problems.append(f"{src}: expected {expect} occurrence(s) of the target site, found {n}")
            continue
        nb = text.replace(old, new).encode("utf-8")
        (OUT / dst).write_bytes(nb)
        entry[src] = {"sha256": sha(sb), "bytes": len(sb)}
        cand_info[dst] = {
            "source": src, "sha256": sha(nb), "bytes": len(nb),
            "changed_bytes": len(nb) - len(sb),
        }
    if problems:
        print("BUILD FAIL")
        for p in problems:
            print("  " + p)
        return 1

    # unified diffs with canonical-path labels, one patch per target plus a combined patch
    for src, dst, _, _, _ in EDITS:
        patch = subprocess.run(
            ["diff", "-u", "--label", f"a/{src}", "--label", f"b/{src}",
             str(ROOT / src), str(OUT / dst)],
            capture_output=True, text=True,
        )
        if patch.returncode != 1 or not patch.stdout:
            problems.append(f"{src}: diff produced rc={patch.returncode}, {len(patch.stdout)} bytes")
            continue
        single = OUT / (Path(dst).name + ".patch")
        single.write_text(patch.stdout)
        cand_info[dst]["patch"] = single.name
        cand_info[dst]["patch_sha256"] = sha(single.read_bytes())
    if problems:
        print("BUILD FAIL")
        for p in problems:
            print("  " + p)
        return 1

    combined = []
    for _, dst, _, _, _ in EDITS:
        combined.append((OUT / (Path(dst).name + ".patch")).read_text())
    (OUT / "repair.patch").write_text("".join(combined))
    cand_info["repair.patch"] = {"sha256": sha((OUT / "repair.patch").read_bytes())}

    (OUT / "entry_hashes.json").write_text(json.dumps({
        "role": "entry pins measured before the build (canonical bytes)",
        "canonical": entry,
        "candidate": cand_info,
    }, indent=2, sort_keys=True) + "\n")

    print("BUILD OK")
    for src, v in entry.items():
        print(f"  live {v['sha256'][:12]}  {src}")
    for dst, v in cand_info.items():
        if isinstance(v, dict) and "sha256" in v:
            print(f"  cand {v['sha256'][:12]}  {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
