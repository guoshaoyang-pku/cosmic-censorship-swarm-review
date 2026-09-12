#!/usr/bin/env python3
"""Worker-024: build the minimal F2b rev29 -> rev30 repair candidate.

Task:  F2b blocking carriers W018-R13-F2B-B1 (line 152 false containment denial)
       and W018-R13-F2B-B2 (line 246 inverted extension-class premise),
       independently reproduced by worker-075 as HF-075-F2b-LARGER.

Read-only with respect to canonical artifacts: reads
artifacts/formulation/schemas/af_scc_c0_vacuum.yaml at its frozen rev29 bytes and
writes CANDIDATE_schemas_af_scc_c0_vacuum.yaml plus repair.patch next to this
script. The canonical file is never opened for writing.

Run from the repo root:
    python3 artifacts/worker-024/f2b_rev29_repair/build_candidate.py
Exit 0 on success; non-zero if the frozen source hash or either carrier moved.
"""
import difflib
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC_REL = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SRC = ROOT / SRC_REL
SRC_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"

DIR = Path(__file__).resolve().parent
CAND = DIR / "CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
PATCH = DIR / "repair.patch"

OLD_152 = (
    '    - "H2_loc (locally square-integrable curvature) is a distinct regularity-axis value '
    'phrased in terms of CURVATURE, not metric differentiability. No containment with C2 or C0 '
    "is asserted here; the informal phrase 'strictly between' is not used and must not be cited "
    '(worker-16 F2b-16-02 accepted)."'
)
NEW_152 = (
    '    - "H2_loc (locally square-integrable curvature) is a distinct regularity-axis value '
    'phrased in terms of CURVATURE, not metric differentiability, and H2LOC is a registered '
    'VARIANT of this class (parent_class AF-SCC-C0-VAC-GEN, variant_id H2LOC in '
    'VARIANT_REGISTRY.json), not a separate class token. The extension SETS are nevertheless '
    'nested exactly as recorded in implication_ledger: E_C2 subset of E_{C^1,1} subset of '
    'E_H2loc subset of E_C0, so H2_loc is not incomparable with C2 or C0. The informal phrase '
    "'strictly between' is not used and must not be cited (worker-16 F2b-16-02 accepted; false "
    'denial repaired per W018-R13-F2B-B1)."'
)

OLD_246 = (
    '    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly '
    'larger extension class, so C2-inextendibility is strictly weaker"}'
)
NEW_246 = (
    '    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly '
    'stronger regularity requirement (E_C2 is the SMALLEST extension set: E_C2 subset of '
    'E_{C^1,1} subset of E_H2loc subset of E_C0), so C2-inextendibility is strictly weaker and '
    'this converse transfer is forbidden [W018-R13-F2B-B2 repaired]"}'
)


def main() -> int:
    raw = SRC.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SRC_SHA:
        print(f"FAIL source moved: {sha} != {SRC_SHA}")
        return 2
    lines = raw.decode("utf-8").splitlines(keepends=True)
    if len(lines) != 300 and len(lines) < 246:
        print(f"FAIL unexpected line count {len(lines)}")
        return 2
    hits152 = [i for i, l in enumerate(lines) if l.rstrip("\n") == OLD_152]
    hits246 = [i for i, l in enumerate(lines) if l.rstrip("\n") == OLD_246]
    if hits152 != [151] or hits246 != [245]:
        print(f"FAIL carriers moved: line152 hits={[i+1 for i in hits152]} line246 hits={[i+1 for i in hits246]}")
        return 2
    lines[151] = NEW_152 + "\n"
    lines[245] = NEW_246 + "\n"
    new_text = "".join(lines)
    CAND.write_text(new_text)

    diff = difflib.unified_diff(
        raw.decode("utf-8").splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=SRC_REL,
        tofile=f"artifacts/worker-024/f2b_rev29_repair/{CAND.name}",
        n=3,
    )
    PATCH.write_text("".join(diff))

    cand_sha = hashlib.sha256(CAND.read_bytes()).hexdigest()
    print(f"source      sha256 {sha}")
    print(f"candidate   sha256 {cand_sha}")
    print(f"candidate   path   {CAND.relative_to(ROOT)}")
    print(f"patch       path   {PATCH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
