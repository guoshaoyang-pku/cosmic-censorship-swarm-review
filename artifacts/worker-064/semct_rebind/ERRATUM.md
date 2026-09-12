# ERRATUM — W064-SEMCT-REBIND-01

**Corrects one overbroad sentence in this bundle's `README.md`.** No measurement, number,
hash, verdict, or falsifier in `report.json` changes.

## What the README says

> No canonical artifact was modified; the shared suite directory was never written to.

## What was measured

- The first clause is **true**: `schemas/semantic_contract_tests/manifest.json`
  (`b2e8bd17892b6c5e`), `observed_verdicts.json` (`c6b81c9c957b9e49`), `run_contract_tests.py`
  (`3be197c3729cebb5`) and all 35 fixture files kept their exact bytes across this audit; the
  audit's own runs wrote only inside `artifacts/worker-064/semct_rebind/`.
- The second clause is **false as stated**: loading the runner with
  `importlib.util.spec_from_file_location(...).exec_module()` at `00:27` caused CPython to write
  `schemas/semantic_contract_tests/__pycache__/run_contract_tests.cpython-310.pyc` (10,301 bytes).
  That cache file was deleted at `00:29`; the directory listing and all canonical hashes were
  re-measured after deletion and are identical to the pre-audit values.
- It was **not** a content write: imports write bytecode caches unconditionally
  (`sys.dont_write_bytecode` was not set). Loading the runner was necessary to redirect
  `MANIFEST`/`OBSERVED`/`HERE`/`REPO` without touching the canonical runner.

## Corrected wording

> No canonical artifact was modified. The only write that reached the shared suite directory was
> a transient CPython bytecode cache (`__pycache__/run_contract_tests.cpython-310.pyc`) created by
> importing the runner; it was removed after the audit and every canonical hash is unchanged.

## Erratum falsifier

Re-measure `sha256(schemas/semantic_contract_tests/manifest.json)`, `.../observed_verdicts.json`,
`.../run_contract_tests.py` and the 35 fixture files against the values recorded in
`report.json#fixture_integrity`; any difference, or any file remaining under
`schemas/semantic_contract_tests/__pycache__/`, falsifies this erratum.
