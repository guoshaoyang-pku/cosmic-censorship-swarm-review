# ERRATUM — W064-SEMCT-REBASE-01 scope wording (bytecode cache)

The report and README of `W064-SEMCT-REBASE-01` say *"no canonical artifact was modified"* /
*"No canonical artifact was modified"*. Those sentences are corrected as follows:

> No canonical file's **content** was modified. Loading the canonical
> `schemas/semantic_contract_tests/run_contract_tests.py` as a module (phase P5 of
> `semct_rebase_audit.py`) wrote a transient bytecode cache
> `schemas/semantic_contract_tests/__pycache__/run_contract_tests.cpython-310.pyc`
> (10301 bytes, 2026-09-12T00:35). It was removed at 00:45 and no canonical artifact changed:
> `manifest.json` `b2e8bd17892b`, `observed_verdicts.json` `c6b81c9c957b`,
> `run_contract_tests.py` `3be197c3729c`, controls `a6ad2638dc99` / `7b910cf34e64` /
> `687fd6971304`, and the 32-fixture corpus are byte-identical to the snapshot pins in
> `report.json#snapshot`.

The same correction applies to the identical sentence in the worker's prior task
`W064-SEMCT-REBIND-01` (already covered by `artifacts/worker-064/semct_rebind/ERRATUM.md`).

*Falsifier:* any canonical suite file differing from the hashes above, or any file remaining under
`schemas/semantic_contract_tests/__pycache__/`, falsifies this erratum.

Numbers, findings and falsifiers in `report.json` and `rebase_patch.json` are unaffected; their
sha256 values do not change.
