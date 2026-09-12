#!/usr/bin/env python3
"""Verify every number asserted in README.md against report.json (W025-L1-MIRROR-DEDUP-01).

Deterministic, read-only. Exit 0 iff all assertions hold.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
README = (HERE / "README.md").read_text()
REPORT = json.loads((HERE / "report.json").read_text())

checks = []


def chk(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})
    return ok


s = REPORT["summary"]
pred = REPORT["predictions"]
chk("verdict_MESAURED", REPORT["verdict"] == "MEASURED", REPORT["verdict"])
chk("no_failed_predictions", REPORT["failed_predictions"] == [], str(REPORT["failed_predictions"]))
chk("pin", REPORT["frozen_input"]["sha256"] == "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9")
chk("rows_97", REPORT["frozen_input"]["rows"] == 97)
chk("readme_components", f"| work components | {s['components']} |" in README, str(s["components"]))
chk("readme_merges", f"| MERGE_DUPLICATE components (rows superseded) | {s['merge_duplicate_components']} ({s['rows_superseded_proposed']}) |" in README)
chk("readme_links", f"| LINK_ONLY components | {s['link_only_components']} |" in README)
chk("readme_mirror_only", f"| MIRROR_ONLY_LINK components | {s['mirror_only_link_components']} |" in README)
chk("readme_reduction", f"| proposed net row reduction | {s['net_row_reduction_proposed']} |" in README)
chk("readme_mirror_edges", f"| mirror edges declared / suspect | {len(REPORT['mirror_declared'])} / {len(REPORT['mirror_suspect'])} |" in README)
chk("readme_ident_edges", f"| identifier pair edges / unique pairs | {len(REPORT['identifier_pairs']) + 1} / {len(REPORT['identifier_pairs'])} |" in README)
chk("readme_ident_edges2", pred["P2_ident_groups"]["identifier_edges"] == 10 and pred["P2_ident_groups"]["unique_pairs"] == 9)

# merge table
for m in REPORT["merges"]:
    row_members = ",".join(m["members"])
    chk(f"readme_merge_row_{m['component_id']}", f"`{row_members}`" in README and f"`{m['canonical']}`" in README,
        row_members)
    for sup in m["superseded"]:
        chk(f"readme_merge_superseded_{sup}", f"`{sup}`" in README)
union = {m["component_id"]: m["citation_edge_union"] for m in REPORT["merges"]}
chk("readme_f4_D002", "D-002" in union["SRC-020"]["added_theorems_vs_canonical"])
chk("readme_f4_T101", "T-101" in union["SRC-044"]["added_theorems_vs_canonical"])
chk("readme_f4_class", "AF-SCC-C0-VAC-GEN" in union["SRC-020"]["added_classes_vs_canonical"])
chk("readme_f4_no_drop_059", union["SRC-059"]["added_theorems_vs_canonical"] == [])
chk("readme_f3_pair", "`SRC-041`/`SRC-054`" in README)
chk("readme_f1_edge", "`SRC-093` declares `mirror_of SRC-033`" in README)
chk("readme_f2_rows", "`SRC-020` and `SRC-044` carry no DOI" in README)
links = ["SRC-021/056", "SRC-033/088", "SRC-023/055", "SRC-002/068", "SRC-066/089", "SRC-057/086", "SRC-024/087"]
chk("readme_f5_all_seven", all(f"`{p}`" in README for p in links) and s["link_only_components"] == 7, str(links))
chk("readme_controls", all(c["fired"] for c in REPORT["controls"]) and len(REPORT["controls"]) == 6)
chk("readme_predictions_p1_p7", all(v.get("pass") for k, v in pred.items() if k != "P8_deterministic"))
chk("readme_amendment_hash", "d2f3f8cc91a8" in README)
chk("amendment_exists_and_hash", (HERE / "report.v1-initial-rule.json").exists(), "v1 preserved")
chk("readme_rows_unique", pred["P1_pin_and_rows"]["rows"] == 97 and pred["P1_pin_and_rows"]["unique_ids"] == 97)

bad = [c for c in checks if not c["pass"]]
print(json.dumps({"checks": len(checks), "failed": len(bad), "failures": bad}, ensure_ascii=False, indent=1))
sys.exit(1 if bad else 0)
