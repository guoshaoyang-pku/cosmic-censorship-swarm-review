# W092-EVBIND-01 — consistency-evidence binding regression (F1/F2a/F2b, G-FORM)

Worker: `worker-092` (bounded execution worker, instance `worker-092-20260912T003714-968807`).
Mode: **measurement only** — no gate verdict, no node status, no live artifact modified.
Instrument: `check_evbind.py` (deterministic, fail-closed, exit 0 iff every expectation holds).
Result hash: see `manifest.json` / `report.json`.

## Question

The three rev12 class schemas declare

```
f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48
```

while the canonical path `artifacts/formulation/evidence/taxonomy_consistency.json` measures
`9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b`. Recorded review falsifiers
offer two repairs: re-stamp the schemas to the live hash, or restore the declared bytes. This
bundle determines which revision is *bound* and what each repair costs.

## Finding — the serialized live document is the regression, not the committed revision

The declared document survives byte-exactly at worker-086's pinned copy
(`artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json`), and it carries
the input-tree binding that the live document has lost:

| field | declared 675a99d0 | live 9e335e9b |
|---|---|---|
| `map_taxonomy_sha256` | `0abb9ed8…` == live F0 rev5 | **absent** |
| `lead_contract_sha256` | `d7419b4e…` == live lead contract == FROZEN rev28 pin | **absent** |
| `measured_at` | `2026-09-12T00:32:02+08:00` | **absent** |
| semantic payload (`consistent`, `errors`, `contract_divergences`, `classes_compared`) | `true`, `[]`, `[]`, 4 classes | identical |

Mechanism, measured not inferred: `artifacts/formulation/tools/check_taxonomy_consistency.py`
(FROZEN-pinned `de356d99…`) writes the canonical evidence path as a side effect of *checking*
(source: `out = ROOT/artifacts/…/taxonomy_consistency.json; out.write_text(...)`), and its output
schema contains none of the three binding fields. The augmenting step that adds them lives in
`close_findings_rev27.py` (`0234cd3c…`). A staged replay of the pinned checker on the pinned live
inputs reproduces the live document **byte-for-byte** (`9e335e9b…`), and a negative control (one
class family mutated) correctly exits 1 / `consistent=false`, so the replay PASS is meaningful.
Any execution of the checker therefore silently reverts the evidence document to the unbound form.

## Repair adjudication (advisory)

| option | closes mismatch | keeps F0/lead-contract binding | schema bytes change | verdicts retired | durable |
|---|---|---|---|---|---|
| **R1** re-stamp schemas to live `9e335e9b` | yes | **no** | yes (all 3) | 6 review files (2 accept, 3 revise, 1 null) | no |
| **R2** restore declared `675a99d0` bytes + bump only the FROZEN evidence pin | yes | yes | **no** | none | only with a writer guard |
| **R3** make the checker emit the two digests, drop wall-clock `measured_at`, re-stamp schemas | yes | yes | yes (all 3) | 6 review files | yes |

**Recommendation:** R2 + writer guard (the checker must stop writing the canonical gate-bound path
directly, e.g. write a `.candidate` and publish via the augmenting step), unless the owner intends
to re-open the rev12 verdicts, in which case R3. R1 is rejected: it discards the only document that
binds F0 rev5 and the lead contract, forces a FROZEN bump and re-review of all three schemas, and
leaves the destructive writer in place.

The declared bytes are recoverable and hash-verified in the pinned copy above; the schema citations
then resolve with **zero schema-byte change**, so the reviews bound to `cce9c601…` / `5476a3f2…` /
`55d0a1ea…` are not retired by R2.

## Falsifiers

Re-run `python3 artifacts/worker-092/evbind/check_evbind.py`. The finding is falsified if any of:

1. the canonical evidence path carries bytes whose sha256 is `675a99d0…` (mismatch closed);
2. the pinned checker's staged output differs from the live evidence document (mechanism refuted);
3. a schema declares a different consistency hash, or its `declared_f0_sha256` differs from the live
   F0 rev5 hash;
4. the declared document's `map_taxonomy_sha256` / `lead_contract_sha256` do not match the live F0
   and lead-contract bytes (binding refuted);
5. re-stamping the schemas is shown to leave their sha256 values unchanged (retirement cost refuted).

The checker exits non-zero on any byte drift and records entry==exit hashes for every live input.

## Contents

- `check_evbind.py` — instrument; all writes confined to `stage/`.
- `report.json` — measured checks, census, adjudication.
- `acceptance_run.log` — stdout of the accepted run (exit 0).
- `manifest.json` — sha256 of every bundle file.
- `pinned/` — byte copies of every measured input plus both evidence revisions.
