# W042-REV29-EVBIND-DURABILITY-06 — rev29 evidence-binding durability

**Worker:** worker-042 · **Class binding:** AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN · **Node:** F1, F2a, F2b · **Gate:** G-FORM (secondary G-AUDIT)

No assignment card exists for worker-042; this is one self-claimed bounded class-bound task, taken
after the handoff's pass-05 card `astra-life05-evidence-binding-repair` completed and published
FROZEN rev29. It does not duplicate worker-060's `W060-REV29-BINDING-ACCEPTANCE-01` (which closed
the four literal card items): the question here is whether the refreshed
`f0_binding.consistency_evidence_sha256` is **durable and authoritatively bound at its target**,
not whether the four items landed.

## Verdict

`FIXPOINT_CONFIRMED_BINDING_GAPS_MEASURED` — structural checks pass, 5/5 controls fire, and the
frozen writer reproduces the pinned evidence revision byte-for-byte. Two binding gaps are measured
(findings below) and one scope note is recorded.

## Pinned inputs (snapshot/manifest.json#cce454b655eb, pinned_at 2026-09-12T00:57:27+08:00)

Note: FROZEN rev29 was published twice; the pin took the second publication
(`815e08079aef`, frozen_at 00:57:26, 50 files). The earlier `e1a8aaa394eb`
publication (frozen_at 00:55:02, 48 files) is superseded and is not the pin.

| artifact | sha256 (12) |
|---|---|
| FROZEN.json (rev 29, frozen_at 00:57:26, 50 files) | 815e08079aef |
| evidence/taxonomy_consistency.json (pin target) | 9e335e9ba1bf |
| check_taxonomy_consistency.py (frozen writer) | de356d999ea3 |
| schemas/af_wcc_vacuum.yaml (F1) | d9cebb9404b2 |
| schemas/af_scc_c2_vacuum.yaml (F2a) | e9a27996dfd3 |
| schemas/af_scc_c0_vacuum.yaml (F2b) | b2ab6acb2bbe |
| research_map/formulation_taxonomy.yaml (F0) | 0abb9ed8a961 |
| artifacts/formulation/formulation_taxonomy.yaml | d7419b4e8963 |
| artifacts/formulation/VOCAB_ALIASES.json | 46cd9f1eb534 |
| schemas/taxonomy_cases.jsonl | ccf7041bd0ff |

## Headline measurements

- **Fixpoint:** sandbox run of the FROZEN-pinned writer on byte-identical pinned inputs exits 0
  (`CONSISTENT (4 classes, 0 contract-text divergences)`) and reproduces the pinned
  495-byte evidence revision `9e335e9b` exactly.
- **Not durable:** the frozen writer writes the canonical evidence path unconditionally
  (no dry-run guard); the pinned evidence carries **0** input sha256 fields; and the schemas'
  refresh rule names only the declared F0 artifact — **1 of the writer's 3 inputs**. Mutating
  the lead contract or the alias file changes the writer output; the alias mutation is silent
  (exit 0, bytes moved). Live corroboration: the canonical evidence file's mtime was rewritten
  in place at least twice during the measurement window (00:58:20, 00:59:25) at unchanged bytes.
- **Pin target not authoritatively bound:** `artifacts/formulation/evidence/taxonomy_consistency.json`
  has **no** entry in `runtime/state/artifact_hashes.json` and **no** accepted artifact event
  ever names `9e335e9b` (0 of 2 declarations for that path; the last, `0ab7c691` @ 23:54:36, is
  superseded). 5 of the 10 binding dependencies are unregistered; 0 are stale. The schemas and
  FROZEN rev29 pin the evidence, but the evidence itself has no registry hash and no stream
  announcement, while PROTOCOL.md rule 2 requires the registry sha256 for a done node.
- **Scope note:** F2b rev13 at rev29 still carries the known-open inverted containment premise
  (`"C2 is a strictly larger extension class"`, the HF-060-F2B-1 hold). A verified binding is not
  F2b semantic cleanliness.

## Findings (each with its falsifier in `report.json`)

| id | severity | one line |
|---|---|---|
| W042-DUR-01 | major | pin is a fixpoint but not durable: writer unconditional, evidence lean, refresh rule covers 1/3 inputs; alias change re-stales silently |
| W042-DUR-02 | minor | lead-contract and alias inputs are output-sensitive yet their hashes are recorded nowhere in the binding |
| W042-DUR-04 | major | the pin target has no registry entry and no accepted artifact event at its pinned hash; 5/10 dependencies unregistered |
| W042-DUR-03 | informational | F2b HF-060-F2B-1 inverted premise is frozen into rev29 (tracked elsewhere; stated for scope) |

## Interpretation limits

Worker measurement only: no gate verdict, no node status, no `validation_status=passed`, no
canonical byte written (all writer runs happened in isolated trees under `runs/`). Wall-clock
mtimes are corroboration, not pinned bytes. The registry and stream readings are live reads at
measure time with their sha256 recorded in the report; later appends do not change them
retroactively but a re-run at new bytes voids the affected classification.

## Rerun

```bash
python3 artifacts/worker-042/rev29_evbind_durability/pin_snapshot.py
python3 artifacts/worker-042/rev29_evbind_durability/verify_rev29_durability.py   # exit 0 = structural + controls
```

Artifacts: `report.json` (f4b475217e45), `verify_rev29_durability.py` (45d2094ae283),
`pin_snapshot.py` (8f02cdcbf2b0), `snapshot/manifest.json` (cce454b655eb),
checkpoint `runtime/state/w042_checkpoint_5.json`.
