#!/usr/bin/env python3
"""worker-030 sibling re-check for the F2b review addendum.

The F2b review JSON cited sibling pins measured at 00:18:28; schemas/af_scc_c2_vacuum.yaml
and schemas/af_wcc_vacuum.yaml were republished at 00:19:14, before the audit run at
00:21:17. This read-only instrument re-verifies the two sibling-separation checks that the
F2b verdict depends on, against the *current* sibling content, and pins the measured hashes
so the addendum can cite them.

Exit 0 = both sibling checks hold on the current content; 1 = at least one fails.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F2B = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"
WCC = "schemas/af_wcc_vacuum.yaml"
OUT = os.path.join(ROOT, "artifacts/worker-030/f2b_sibling_recheck.json")
CLASS_ID = "AF-SCC-C0-VAC-GEN"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    c2 = yaml.safe_load(open(os.path.join(ROOT, C2), encoding="utf-8"))
    wcc = yaml.safe_load(open(os.path.join(ROOT, WCC), encoding="utf-8"))
    f2b = yaml.safe_load(open(os.path.join(ROOT, F2B), encoding="utf-8"))

    c2_ok = (
        c2.get("class_id") == "AF-SCC-C2-VAC-GEN"
        and c2.get("sibling_disjoint_from") == CLASS_ID
        and (c2.get("regularity") or {}).get("extension_regularity") == "C2"
        and (c2.get("conclusion") or {}).get("conclusion_type")
        != (f2b.get("conclusion") or {}).get("conclusion_type")
    )
    wcc_ok = (
        wcc.get("class_id") == "AF-WCC-VAC-GEN"
        and (wcc.get("i_plus") or {}).get("in_conclusion") is True
        and (wcc.get("visibility") or {}).get("role") == "conclusion"
    )
    payload = {
        "instrument": "artifacts/worker-030/f2b_sibling_recheck.py",
        "generated_at": _dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "why": "sibling pins in reviews/F2b-review-030.json were measured at 00:18:28 and superseded at 00:19:14, before the 00:21:17 audit run",
        "pins": {
            F2B: sha256_of(os.path.join(ROOT, F2B)),
            C2: sha256_of(os.path.join(ROOT, C2)),
            WCC: sha256_of(os.path.join(ROOT, WCC)),
        },
        "checks": [
            {
                "id": "CLASS-05",
                "status": "PASS" if c2_ok else "FAIL",
                "detail": (
                    f"{C2}: class_id={c2.get('class_id')!r} "
                    f"sibling_disjoint_from={c2.get('sibling_disjoint_from')!r} "
                    f"extension_regularity={(c2.get('regularity') or {}).get('extension_regularity')!r} "
                    f"conclusion_type={(c2.get('conclusion') or {}).get('conclusion_type')!r}"
                ),
            },
            {
                "id": "CLASS-07",
                "status": "PASS" if wcc_ok else "FAIL",
                "detail": (
                    f"{WCC}: class_id={wcc.get('class_id')!r} "
                    f"i_plus.in_conclusion={(wcc.get('i_plus') or {}).get('in_conclusion')!r} "
                    f"visibility.role={(wcc.get('visibility') or {}).get('role')!r}"
                ),
            },
        ],
        "counts": {"pass": int(c2_ok) + int(wcc_ok), "fail": int(not c2_ok) + int(not wcc_ok)},
        "falsifier": "A change to either sibling that breaks the disjointness/role predicates above, or a change to the pinned sibling hashes in this file, voids the addendum's re-check; the F2b verdict itself remains bound to sha256 1bb78ce9b3572cda of schemas/af_scc_c0_vacuum.yaml only.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(json.dumps(payload, indent=1))
    return 1 if payload["counts"]["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
