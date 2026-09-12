# W027-F0-EVIDENCE-WRITER-FIX-01 — F0/G-FORM consistency-evidence writer fix

- **Worker:** worker-027 (bounded execution worker; breadth executor)
- **Classes:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b)
- **Node / gate:** `F0` / `G-FORM` (evidence chain consumed by the three rev12 schemas)
- **Task:** no inbox card existed for worker-027; self-assigned from the immediate queue
  (G-FORM/G-F0 binding chain), bounded and class-bound.
- **Artifacts:** `verify_writer_fix.py` (instrument), `report.json` (measurement),
  `proposed_patch.diff` (proposed writer patch, **not applied**), `snapshots/` (pinned inputs).

## Question

The three rev12 class schemas declare
`consistency_evidence_sha256 = 675a99d0d25b…` against
`artifacts/formulation/evidence/taxonomy_consistency.json`. Peers (worker-086, worker-053,
worker-094, worker-082, worker-041) reported the mismatch and the writer conflict. This task
asks the next question: **is the mismatch a one-off edit, and does a minimal writer patch close
it durably?**

## Measured result (2026-09-12T00:41+08:00, all inputs pinned)

| item | value |
|---|---|
| declared pin in F1/F2a/F2b (`consistency_evidence_sha256`) | `675a99d0d25b…` |
| live file at the declared path | `9e335e9ba1bf…` (495 B) |
| pin resolves at declared path? | **no** (all three schemas) |
| declared F0 pin `0abb9ed8a961…` vs measured canonical taxonomy | resolves (true) |
| declared revision source (preserved) | `artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json` (728 B) |
| declared revision == live + 3 appended fields | **true** (`map_taxonomy_sha256`, `lead_contract_sha256`, `measured_at`) |

**W027-F1 (major, CONFIRMED):** the declared pin resolves nowhere at its declared path.
**W027-F2 (major, CONFIRMED):** the live document is strictly weaker than the declared revision
— the declared revision is exactly the live bytes plus the three pin/timestamp fields, so
re-pinning the schemas to the live hash would bind a document with no input-tree pins and
re-open the rev12 finding (e) that the repair claimed to close.

**W027-F3 (major, CONFIRMED, root cause reproduced):** in a private tree the canonical writer
`artifacts/formulation/tools/check_taxonomy_consistency.py` produces bytes **byte-identical to
the live canonical document** (`9e335e9b…`), twice. Any repair that edits only the JSON instance
is reverted by the next canonical consistency run; the writer itself emits no input pins.

## Proposed fix (validated in isolation, NOT applied)

`proposed_patch.diff` appends exactly two fields before the write:

```diff
+import hashlib as _hl
+def _sha256_file(_p):
+    return _hl.sha256(_p.read_bytes()).hexdigest()
+rep["map_taxonomy_sha256"] = _sha256_file(ROOT/"research_map/formulation_taxonomy.yaml")
+rep["lead_contract_sha256"] = _sha256_file(ROOT/"artifacts/formulation/formulation_taxonomy.yaml")
```

Measured in an isolated copy of the writer's closure:

| check | result |
|---|---|
| V1 writer deterministic across two runs | **true** (`0058692bf244…` twice) |
| V1 output pins equal measured inputs | **true** (`0abb9ed8a961…`, `d7419b4e8963…`) |
| V1 output == declared revision minus `measured_at` | **true** (byte-identical) |
| semantic mutation (`family: "WCC"` → `"SCC"`) changes output and breaks consistency | **true** (exit 1, 1 error, pin changes) |
| clock-stamped variant V2 idempotent | **false** — rejected design |

**W027-F4 (major, PROPOSED_NOT_APPLIED):** V1 is the minimal durable fix: self-pinning and
idempotent, and it exactly reproduces the frozen declared revision modulo its clock field.
Adoption is the tool owner's decision; it moves the evidence hash **once** and therefore requires
a coordinated re-pin of the evidence path and the three `f0_binding` values.

**W027-F5 (info, negative control):** a wall-clock `measured_at` inside the hashed document makes
every run a new revision (`2026-09-12T00:42:48.220054+08:00` vs `…48.374447+08:00`, different
sha256). Timestamps belong in a sidecar or outside the pinned bytes.

**W027-F6 (info, source reading):** the frozen declared revision lacks the `binding_rule` field
that the on-disk repair tool `close_findings_rev27.py` writes, so the declared pin has no
reproducible producer on disk; replaying that tool would move the pin again.

## Controls

9/9 pass: unpatched determinism and byte-identity to live, declared-revision reconstruction,
V1 determinism, V1 pins, V1 == declared-minus-clock, mutation sensitivity, clock negative
control, and isolation (canonical evidence path and every pinned input unchanged after the run).
No canonical file, review, map or controller tool was written by this task;
`report.json` records start/end hashes proving it.

## Falsifier (pre-registered)

FALSIFIED if (a) the live canonical path already carries the declared `675a99d0…` bytes, or the
three schemas declare the live evidence sha at re-measurement; or (b) the declared revision is
not reconstructible as the live bytes plus the three appended fields; or (c) the unpatched
writer's two isolated runs are not byte-identical to each other or not byte-identical to the live
canonical document; or (d) the V1-patched writer's two isolated runs are not byte-identical; or
(e) the V1 output does not carry `map_taxonomy_sha256` / `lead_contract_sha256` equal to the
measured input hashes; or (f) the V1 output is not byte-identical to the declared revision minus
`measured_at`; or (g) the semantic-mutation control leaves the patched output unchanged or still
consistent; or (h) the clock-stamped V2 variant's two runs are identical; or (i) any pinned input
or the live evidence path drifts during the run (exit 2/5). Any pinned-sha mismatch voids the
measurement rather than falsifying it.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-027/f0_evidence_writer_fix/verify_writer_fix.py
# exit 0 = PIN_UNRESOLVED_AT_DECLARED_PATH_AND_FIX_VALIDATED
# exit 2 = input drift | 3 = already fixed | 4 = fix not validated | 5 = moving target
```

## Non-claims

Not a gate verdict (worker events cannot set pending/pass/fail or node done); does not modify any
canonical artifact, review, map or controller tool; the patch is **not** applied; does not
adjudicate taxonomy content, physics or the merits of any review; the pin mismatch itself was
first reported by peers — the new contribution here is the independent reproduction of the
writer-level root cause and the isolated validation of the minimal fix.
