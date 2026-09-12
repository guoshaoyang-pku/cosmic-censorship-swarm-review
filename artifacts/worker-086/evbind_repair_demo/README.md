# W086-GFORM-R2-DURABILITY-01 — R2 restore durability + non-writing guard candidate

Bounded class-bound worker task, worker-086. Gate **G-FORM**; nodes **F1/F2a/F2b**;
classes **AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN**.

## Question

Worker-092 adjudicated the rev12 evidence-binding collision (HF-086-R1) as repair path **R2**
(restore the declared evidence bytes `675a99d0` at the canonical path) and recorded that R2 is
durable *only if the standalone checker stops writing the canonical path*. This task measures
that durability leg and produces the minimal guard candidate the owner needs to apply.

## Result — 12/12 checks pass

Verdict: `R2_DURABLE_WITH_NOWRITE_GUARD__RESIDUAL_FROZEN_REPIN_AND_OWNER_APPLY_REQUIRED`

All runs happen in `sandbox/`, a byte copy of the four checker inputs plus the pinned checker and
the guarded candidate. The live tree is measured before and after (10 pins, C10) and is not written.

| check | measurement |
|---|---|
| C0 | declared `675a99d0` is byte-exactly the live lean document + 3 pin fields (`map_taxonomy_sha256`, `lead_contract_sha256`, `measured_at`) |
| C3 | **control**: the pinned unguarded checker, run once on the restored sandbox, rewrites the path to `9e335e9b` — R2 alone is *not* durable, exactly as worker-092 recorded |
| C5/C6 | guarded checker (default) run twice: path stays `675a99d0`; guard note reports the sandbox on-disk hash (ROOT sentinel) |
| C7 | guard does not silence detection: a mutated taxonomy gives `INCONSISTENT`, rc 1, path unchanged |
| C8 | `--write` opt-in still regenerates the computed document — the guard is not a dead end |
| C11 | residual: FROZEN rev28 pins the evidence path at `9e335e9b`, so R2+guard alone does **not** make declared == disk == freeze |

## Guard candidate

`guard.patch` applies two exact literal replacements to the pinned checker
(`de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd`):

1. add `hashlib` to the import line;
2. replace the unconditional `out.write_text(...)` with an explicit `--write` gate, defaulting to
   no write plus a one-line NOTE carrying the computed and on-disk hashes.

Candidate: `check_taxonomy_consistency.guarded.py`
sha256 `cde1a165a2f02b6db8bf2fdffe97c421444450dab820b8aeace4bee90debee8f`.
Consistency checking and the exit code are unchanged.

## Owner repair sequence (not applied here)

1. stage `artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json`
   at `artifacts/formulation/evidence/taxonomy_consistency.json`;
2. apply `guard.patch` to the canonical checker (new tool hash);
3. publish a FROZEN revision re-pinning the evidence path at `675a99d0` and the guarded tool hash.

Until step 3, condition *declared == disk == freeze at one instant* does not hold.

## Falsifier

The repair fails if, after the owner stages steps 1–3: (a) one guarded-checker run leaves the
canonical evidence path at any hash other than `675a99d0`; (b) any schema or F0 taxonomy hash
changes; (c) the unguarded pinned checker no longer rewrites a sandbox copy to `9e335e9b`
(control dead); or (d) FROZEN still pins `9e335e9b` at the canonical evidence path.

## Incident disclosure (probe development run #1)

The first development run executed the guarded candidate from this directory rather than from a
sandbox `tools/` mirror, so `Path(__file__).parents[3]` resolved to the repository root and the C8
`--write` control rewrote `artifacts/formulation/evidence/taxonomy_consistency.json` with
**byte-identical** content. Measured sha256 before/after is `9e335e9b`; all 10 live pins are
identical; the file mtime moved to `2026-09-12 00:47:25.106985689 +0800`. The corrected probe
installs the candidate inside the sandbox and C5 asserts the sandbox on-disk sentinel; this report
is the corrected run. The incident is recorded in `report.json → incident_log`.

## Files

- `probe_r2_durability.py` — deterministic fail-closed probe (rerun with `python3`)
- `guard_build.py` — guard builder (hash-checked input, exact replacements, diff)
- `guard.patch`, `check_taxonomy_consistency.guarded.py` — candidate
- `report.json`, `PINS.json`, `MANIFEST.sha256` — measured evidence
- `sandbox/` — rerunnable mirror; ends in the repaired fixpoint

## Non-claims

No canonical write by the corrected run; no schema edit; no FROZEN edit; no decision between
repair paths R1/R2/R3; `close_findings_rev27.py --apply` (second writer) not exercised; no gate
verdict, node completion or `validation_status=passed`.
