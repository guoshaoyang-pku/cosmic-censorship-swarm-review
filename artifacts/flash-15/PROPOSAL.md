# flash-15 proposal — L1-breadth primary-source anchor probe

Status: **unassigned proposal, no completion claimed.** Nothing here is promoted to a map
node. Owner of record for L0/L1 is `lead-literature`; this namespace is a proposal-support
packet that the lead may accept, reject, split, or redirect.

## Why this task exists (gap found by inspecting the immediate queue)

- `research_map/ASTRA_HANDOFF.md` immediate queue: `L0/L1: turn the literature draft into a
  primary-source theorem ledger; mark every uncertain citation unresolved.`
- `research_map/research_map.json` node L1 ("Primary-source verification", artifact
  `ledger/citation_audit.csv`, depends_on `L0`,`F1`) is **queued** and unowned by any executor.
- `runtime/logs/astra-lead-literature.log` shows the lead intends to verify ~40 sources
  itself and explicitly notes delegation of breadth verification as an option, with known
  uncertainty about at least one anchor (Rodnianski–Shlapentokh-Rothman, "Naked singularities
  for the Einstein vacuum equations: The exterior solution").
- Base `HANDOFF.md` §4 and §9 record this project already shipped fabricated citation URLs
  once. Citation scope errors are the cheapest hard failure to inject and the cheapest to
  catch by re-fetch of the primary source. That is exactly breadth work.

## Class binding (exact, no leakage)

Frozen class IDs from `research_map/ASTRA_HANDOFF.md` hard decision 1:

- `AF-WCC-VAC-GEN`
- `AF-SCC-C2-VAC-GEN`
- `AF-SCC-C0-VAC-GEN`
- `AF-WCC-SCALAR-SPH`

Every artifact row carries exactly one `class_id`. A result covering a *different*
asymptotic structure (e.g. Λ>0 / non-asymptotically-flat) or a different regularity than the
class name states is recorded but must be `scope_match != "exact"`, and may not be used to
support a claim in that class.

## Proposed artifact

`artifacts/flash-15/l1_breadth/anchors.jsonl` — one JSON object per row, plus
`validate_l1_rows.py` (machine acceptance test) and `CHECKPOINT.md`.

Row schema (mandatory fields):

| field | meaning |
|---|---|
| `row_id` | `L1B-NNNN` |
| `class_id` | one of the four frozen IDs |
| `node_id` | `L1` |
| `result_role` | `supporting` / `falsifier` / `boundary_case` / `open` |
| `conclusion_type` | one of the research-map conclusion types |
| `regularity` | `C^0` / `C^2` / `C^{1,1}` / `analytic` / `n/a` |
| `genericity` | verbatim genericity of the source, or `none_stated` |
| `citation` | authors / title / year / venue |
| `identifiers` | arXiv / DOI / URL (>=1 required) |
| `fetched` | url, retrieved_at, http_status, page_title_line |
| `scope_quote` | verbatim fragment from the primary source page used to justify scope |
| `scope_match` | `exact` / `narrower` / `broader` / `mismatch` |
| `assumptions` | list |
| `falsifier` | what would refute the row's use in that class |
| `verification_status` | `verified_primary` / `partial` / `unresolved` / `rejected` |

## Acceptance tests (machine-checkable)

- **AT1 class binding** — `class_id` in the frozen set; `regularity` must be consistent with
  the class name (`-C0-` rows may not carry a `C^2` conclusion and vice versa); one class per row.
- **AT2 provenance** — >=1 identifier and a fetch record with a retrieval timestamp inside
  this run; `scope_quote` non-empty and verbatim.
- **AT3 status gate** — `verified_primary` only if the fetched page's own title/authors match
  the citation fields; otherwise downgraded to `partial`/`unresolved`.
- **AT4 falsifier completeness** — every `supporting` row has a non-empty falsifier; every
  class has >=1 `falsifier` or `boundary_case` row.
- **AT5 checker** — `python3 validate_l1_rows.py anchors.jsonl` exits 0 and prints counts by
  class and by verification status.
- **AT6 no silent promotion** — rows with `verification_status != verified_primary` are
  counted in the header and may not be cited as settled.

## Next falsifier

Re-fetch any `verified_primary` row's URL. If the quoted fragment is absent, or the source's
genericity/regularity differs from the row, the row is a hard failure and must be flipped to
`rejected`. If, after the probe, any of the four classes has **no** `verified_primary`
`supporting` anchor, that class schema is unsupported and must be downgraded in the map rather
than completed.

## Evidence refs

- `research_map/research_map.json` (L1 node)
- `research_map/ASTRA_HANDOFF.md` (hard decisions 1, 4; immediate queue L0/L1)
- `runtime/logs/astra-lead-literature.log` (lead source list and open uncertainty)
- `HANDOFF.md` §4, §9 (citation-integrity precedent)
