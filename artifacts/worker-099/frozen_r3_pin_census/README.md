# worker-099 — G-FORM rev29 independent pin census (incarnation 7)

Bounded class-bound task taken at 2026-09-12T01:06:38+08:00 (no assignment card existed in
`comms/inbox/worker-099.jsonl`; self-selected from the open G-FORM r3 verification need, chosen to
avoid duplicating the four tasks already delivered by worker-099 incarnations 1–6).

- node: `F1/F2`; gate: `G-FORM`
- classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- artifact: `pin_census.json` (sha256 in `pin_census.json.sha256`)
- instrument: `run_pin_census.py` (stdlib only, re-hashes bytes itself; does **not** call the
  formulation author's `verify_frozen.py`)
- reproduce: `python3 artifacts/worker-099/frozen_r3_pin_census/run_pin_census.py` (~20 s)

## What it measures

At two instants separated by a 15 s gap, for every one of the 50 files declared in
`artifacts/formulation/FROZEN.json` (rev29, self-sha `815e08079aefbc…`):

1. **pin fidelity** — measured sha256 and byte count vs the declaration, plus FROZEN self-hash,
   the three dual schema mirrors, and the two declared taxonomy prefixes (`0abb9ed8a961`,
   `d7419b4e8963`);
2. **quiescence** — did the bytes *and* the mtime move across the gap;
3. **class binding** — occurrence census of the four frozen class IDs across the frozen schema
   mirrors, both taxonomy copies, KEY_MANIFEST and VARIANT_REGISTRY, with the exact lines of every
   literal `C0 or C2` / `C2 or C0` occurrence.

## Result (three census runs)

| run | first instant | pin verdict | quiescence |
|---|---|---|---|
| 1 | 01:08:05 | PASS | WRITER_ACTIVE |
| 2 | 01:08:55 | PASS | QUIESCENT |
| 3 | 01:09:32 | PASS | WRITER_ACTIVE |

- **W099-PC-01 (pin fidelity PASS).** 50/50 files matched declared sha256 and bytes at every run;
  FROZEN self-hash `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`; 3/3 dual
  mirrors byte-equal; both taxonomy prefixes matched.
- **W099-PC-02 (frozen set not quiescent).** `artifacts/formulation/evidence/taxonomy_consistency.json`
  (declared `9e335e9ba1bf…`, 495 bytes) was rewritten with **byte-identical** content at
  **01:08:20.982** and again at **01:09:34.236**, both inside the r3 window; 2 of 3 census windows
  caught the mtime move. Source-level candidate writer:
  `artifacts/formulation/tools/check_taxonomy_consistency.py:79` (writes exactly that path); process
  identity is not proven by this census. No declared pin was violated — reviewers must bind sha256,
  never path or mtime.
- **W099-PC-03 (CF-26 secondary observation).** `research_map/class_separation.py` measured
  `e36b0d644ca7…` at ~01:07:50 and back at `a8c04fc31e4a…` with mtime **01:08:14.862** — a further
  write inside the open REC-22 freeze round, restoring the adjudication's applied-canonical bytes.
  No announcing event for that transition was observed by this worker as of 01:10.
- **W099-PC-04 (class binding).** No composite regularity class definition found: all 10 literal
  `C0 or C2` / `C2 or C0` occurrences are inside prohibition/quotation contexts (lines listed in
  `class_binding.schema_co_mention`). Each of the four frozen class IDs appears in both taxonomy
  copies, both schema mirrors, KEY_MANIFEST and VARIANT_REGISTRY.
- **W099-PC-05 (scope).** This is not a schema-content verdict; the census tests pins, quiescence
  and binding only.

## Falsifier

Re-running `run_pin_census.py` against the same FROZEN rev29 declarations returns a measured sha256
or byte count differing from a declaration, a FROZEN self-hash that no longer starts with
`815e08079aefbc`, a broken dual mirror, a taxonomy hash outside its declared prefix, or bytes that
change across the gap — any of those voids this census.
