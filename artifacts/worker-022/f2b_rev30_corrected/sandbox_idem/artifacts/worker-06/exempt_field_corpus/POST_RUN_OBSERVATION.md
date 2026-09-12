# FORM-EXEMPT-09 post-run observation — canonical freeze drift (worker-06)

Observed at `2026-09-12T00:09:21+08:00`, after the FORM-EXEMPT-09 measurement completed.

## Observation (not a blocker)

`artifacts/formulation/tools/verify_frozen.py` now reports **6 drift problems**, and the binding
manifest still records the **rev18** hashes while the files on disk were rewritten:

| file | FROZEN rev19 records (rev18 hashes) | disk at 00:09 | mtime |
|---|---|---|---|
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `bdb23f76b895` | `a8d899d2941f` | 00:08:58 |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `e9fcefe6e595` | `8dae50da1ab5` | 00:09:02 |
| `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | `f962c117ba11` | `b65fcc0f0118` | 00:08:37 |
| `artifacts/formulation/formulation_taxonomy.yaml` | `a7ccffa882eb` | `01e7f841643c` | — |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `0ab7c6914689` | `9e335e9ba1bf` | — |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `497aac5ec088` | `1d3e2ad55546` | — |

`FROZEN.json` itself is `da6a0ee9f2f6a5f6…`, revision 19, `frozen_at 2026-09-12T00:04:48`.

## Why the FORM-EXEMPT-09 numbers are unaffected

- `make_corpus.py` asserted each base file's on-disk sha256 against the rev18 prefixes at generation
  time (`bdb23f76b895` C0, `e9fcefe6e595` C2, `f962c117ba11` WCC); `verify_frozen.py` reported
  33 files / 0 problems at `00:05`. The fixture files embed those exact bases and their hashes are
  frozen in `manifest.json` (`0627216b…`), verified by the runner before measuring.
- Both stages ran on the fixture copies, so the later schema edits do not enter the measurement.
- The report's numbers are therefore claims **about the rev18 base hashes only**, exactly as recorded
  in `manifest.json`; they are not claims about the current disk schemas.

## Consequence

The `FROZEN` manifest and the disk schemas must be re-synced by the owner (lead-formulation) before
any new review/gate binds to rev19. A re-measurement on the new disk hashes requires a **new**
pre-registered corpus; this corpus stays frozen and must not be re-tuned.

Evidence refs: `artifacts/formulation/FROZEN.json#da6a0ee9f2f6`, `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#a8d899d2941f`,
`runtime/state/w06_checkpoint_5.json`, `artifacts/worker-06/exempt_field_corpus/manifest.json#0627216b6b27`.
