#!/usr/bin/env python3
"""Generate REVIEW.md for W070-L1-LOCATOR-LIVE-02 from report.json (no network)."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("/data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-070/l1_locator_live02")


def main() -> int:
    r = json.loads((OUT / "report.json").read_text(encoding="utf-8"))
    a = r["aggregate"]
    vc = a["verdict_counts"]
    rows = r["census"]
    lines = []
    A = lines.append
    A("# W070-L1-LOCATOR-LIVE-02 — live re-resolution of the `arxiv-api-query` locator family")
    A("")
    A(f"- **Task**: {r['task_id']} (node {r['node_id']}, gate {r['gate']}, group literature)")
    A(f"- **Question**: {r['question']}")
    A(f"- **Ledger pin**: `ledger/citation_audit.csv` sha256 `{r['pins']['ledger/citation_audit.csv']}`")
    A(f"- **Frame**: `frame.json` sha256 `{r['pins']['frame.json']}` — written and hashed before the first live fetch")
    A(f"- **Instrument**: `run_live070.py` sha256 `{r['pins']['runner']}` (revision {r['revision']})")
    A(f"- **Status**: `{r['status']}`; corpus_valid={r['corpus_valid']}; ledger drift={r['inputs']['ledger/citation_audit.csv']['drift']}")
    A(f"- **Created**: {r['created_at']} → {r['finished_at']}")
    A("")
    A("## Result")
    A("")
    A(f"{a['rows_in_family']} rows in the family, one fetch each of the URL as recorded:")
    A("")
    A("| verdict | rows | meaning |")
    A("|---|---:|---|")
    A(f"| TOP_HIT_MATCH | {vc.get('TOP_HIT_MATCH', 0)} | claimed `arxiv_id` is entry rank 1 |")
    A(f"| HIT_IN_PAGE_NOT_TOP | {vc.get('HIT_IN_PAGE_NOT_TOP', 0)} | claimed id present at rank 2–10 |")
    A(f"| NOT_IN_RETURNED_PAGE | {vc.get('NOT_IN_RETURNED_PAGE', 0)} | claimed id absent from the returned page |")
    A(f"| FETCH_FAILED / PARSE_ERROR | {vc.get('FETCH_FAILED', 0)} / {vc.get('PARSE_ERROR', 0)} | no usable body |")
    A("")
    A(f"As-recorded re-resolution rate to the claimed work at rank 1: **{a['top_hit_count']}/{a['rows_in_family']} "
      f"= {a['as_recorded_reresolution_rate']}**. Top-hit rows: {', '.join(a['top_hit_rows'])}.")
    A("")
    A(f"Of {a['distinct_locators']} distinct locator strings, {a['duplicate_locator_groups']} are shared by "
      f"{a['rows_sharing_a_locator']} of the {a['rows_in_family']} rows (max {a['max_rows_per_locator']} rows on one query). "
      "A query shared by k rows cannot be the exact locator of more than one of them.")
    A("")
    A("### Per class (rows may carry more than one tag)")
    A("")
    A("| class | rows | top | non-top | not in page |")
    A("|---|---:|---:|---:|---:|")
    for cls, d in sorted(a["per_class"].items()):
        v = d["verdicts"]
        A(f"| {cls} | {d['rows']} | {v.get('TOP_HIT_MATCH', 0)} | {v.get('HIT_IN_PAGE_NOT_TOP', 0)} | {v.get('NOT_IN_RETURNED_PAGE', 0)} |")
    A("")
    A("### Rows that do not re-resolve to the claimed work at rank 1 as recorded")
    A("")
    A("| row | id | class | rank | hits | verdict |")
    A("|---|---|---|---:|---:|---|")
    for x in rows:
        if x["verdict"] == "TOP_HIT_MATCH":
            continue
        rank = x["target_rank"] if x["target_rank"] is not None else "—"
        A(f"| {x['row']} | {x['citation_id']} | {x['class_mapping']} | {rank} | {x['n_hits']} | {x['verdict']} |")
    A("")
    A("## Findings")
    A("")
    for h in r["hard_failures"]:
        A(f"- **{h['kind']}** ({h['severity']}): {h['finding']}")
    A("")
    A("## Controls (all must pass)")
    A("")
    c = r["controls"]
    A(f"- offline Atom parser rank fixture: {'PASS' if c['parser_fixture']['pass'] else 'FAIL'}")
    for pc in c["positive_live_recorded_title"]:
        A(f"- live positive `{pc['name']}` (target {pc['target_arxiv_id']}): {'PASS' if pc['pass'] else 'FAIL'} "
          f"(n_hits={pc['n_hits']}, ids={pc['entry_ids']})")
    A(f"- live negative nonsense query: {'PASS' if c['negative_live_nonsense']['pass'] else 'FAIL'} "
      f"(n_hits={c['negative_live_nonsense']['n_hits']})")
    ic = c["idempotence_refetch"]
    A(f"- idempotence refetch SRC-005: {'PASS' if ic['pass'] else 'FAIL'} ({ic['first_verdict']} vs {ic['refetch_verdict']})")
    A(f"- predecessor TOP_HIT_MATCH row SRC-006 still top: {'PASS' if c['predecessor_top_hit_row']['pass'] else 'FAIL'}")
    A(f"- classification agreement vs predecessor census: "
      f"{c['classification_agreement_vs_predecessor']['agree']}/{c['classification_agreement_vs_predecessor']['rows']}")
    A("")
    A("Re-execution of the predecessor's three live rows (verdict names normalized): "
      + "; ".join(f"{k}: {v['predecessor']} → {v['this_run']} ({'agree' if v['agree'] else 'DISAGREE'})"
                  for k, v in a["reexecution_agreement_predecessor_live_rows"].items()))
    A("")
    A("## Limits and authority")
    A("")
    A("- One fetch per row at one ledger hash; arXiv ranking can change over time, so a rank is a measurement at the "
      "recorded time, not a permanent property. The falsifier covers re-runs.")
    A("- No ledger edit was made; the literature lead owns `ledger/citation_audit.csv`.")
    A("- Worker evidence only: no gate verdict, no node completion, no `validation_status=passed`, no mathematical claim.")
    A("")
    A("## Falsifier")
    A("")
    A(r["falsifier"])
    A("")
    A("## Raw evidence")
    A("")
    A(f"- `raw/` holds the {len(list((OUT / 'raw').glob('*.xml')))} fetched response bodies, one per row, hashed in `report.json`.")
    A(f"- `frame.json` + `frame.sha256.txt`: pre-registered frame and registration time.")
    if r.get("supersedes"):
        A(f"- `superseded/report.rev1-reexec-name-defect.json` sha256 `{r['supersedes']['sha256']}`: {r['supersedes']['defect']}.")
    (OUT / "REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT / "REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
