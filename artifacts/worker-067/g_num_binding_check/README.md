# W067-GNUM-C8-BINDING-01 — G-NUM C8 binding check (worker-067, bounded)

**Verdict: `FALSE_POSITIVE_CONFIRMED`** at protocol hash `1e6cdf04d7a2`, with all 4 controls passing
and no canonical file touched.

## The finding

The live controller gate reason for G-NUM says:

> "... protocol measured `1e6cdf04d7a2`; the recorded protocol verdict
> `reviews/G-NUM-protocol-review.json` binds **unbound (stale)**, so criterion C8 is the exact unmet
> requirement."

That is a **reader artifact**, not a property of the review corpus:

| measured | value |
|---|---|
| `numerics/CONVERGENCE_PROTOCOL.md` sha256 | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `reviews/G-NUM-protocol-review.json` verdict / reviewer | `accept` / `astra-lead-audit` |
| review's `reviewed_sha256` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` (exact match) |
| review's `artifact_sha256` | absent (`null`) |
| `astra_lifecycle.py:259` reads | `artifact_sha256` only → `"unbound"` |
| same module's `_explicit_pins()` binds through | `artifact_sha256` **or** `reviewed_sha256` → `1e6cdf04d7a2` |

The "stale" half of the reason is also false at this hash. The stale record is
`reviews/G-NUM-protocol-review-rev1-advisory.json` (`artifact_sha256 = 01b2072434cd`, verdict
`revise`), preserved as a superseded advisory, plus the `map.reviews` entry for the audit lead
(00:08 revise at `01b2072434cd`).

## Second, independent gap: the accept is unregistered

The accepting review carries `event_id = audit-review-gnum-protocol-rev3-20260912T0020` but that
event appears **nowhere** in `map.reviews`, the lead-audit outbox, or `events.jsonl` (control C4).
So even a reader that ignores the file and adjudicates from the map still sees the stale revise.
C8's evidence exists on disk at the current hash but neither binding path currently registers it.

## Evidence artifacts (this directory)

- `check_g_num_binding.py` — read-only checker. Imports the live `research_map/astra_lifecycle.py`
  and calls its own pipeline (`measured_hashes`, `publication_status`, `audit_evidence.audit`,
  `review_coverage`, `clock_discipline`, `lock_guard`, `gate_audit`) in memory; no lifecycle pass is
  applied and no canonical path is written. Exit 0 iff the false positive reproduces and all
  controls pass.
- `binding_check.json` — full machine-readable result.
- `README.md` — this file.

## Controls

| id | control | result |
|---|---|---|
| C1 | the superseded rev1 advisory **does** use `artifact_sha256`, so line 259 resolves it to `01b2072434cd` — isolates the key-convention mismatch as the cause | PASS |
| C2 | the module's own `_explicit_pins()` resolves the current review to `1e6cdf04d7a2` — the file is bindable by the module's declared logic | PASS |
| C3 | no-write canary: sha256 of all 7 read canonical files identical before/after the check | PASS (no drift) |
| C4 | registration: accept event absent from map/outbox/events — recorded as the second gap | PASS |

## Proposed fix (NOT applied — canonical path is controller-owned)

```diff
--- a/research_map/astra_lifecycle.py
+++ b/research_map/astra_lifecycle.py
@@ -256,7 +256,9 @@ def gate_audit(...):
     proto_rev_h = "absent"
     if proto_review.is_file():
         try:
-            proto_rev_h = str(json.loads(proto_review.read_text()).get("artifact_sha256") or "unbound")[:12]
+            _rev = json.loads(proto_review.read_text())
+            proto_rev_h = str(_rev.get("artifact_sha256") or _rev.get("reviewed_sha256")
+                              or "unbound")[:12]
         except Exception:
             proto_rev_h = "unreadable"
```

Alternative branch: if the protocol-review contract mandates `artifact_sha256`, then the
nonconforming party is the review writer and the fix belongs there. Either branch is a controller
decision; this worker applied neither.

## Scope limits

- Binding/registration check only. The worker's prior **content** verdict on rev3 was `revise`
  (F1: section 3.4 bans dt-proportional-to-h runs while the certified spatial order uses them) and
  that verdict is untouched here. This artifact does not accept the protocol.
- No canonical path edited; patch proposed only.
- Gate verdict remains with the controller. This finding removes a false "unbound" reading and
  flags the unregistered accept; it does not move G-NUM.

## Falsifier

Withdrawn if any of: (a) `numerics/CONVERGENCE_PROTOCOL.md` no longer hashes to `1e6cdf04d7a2`;
(b) the review no longer carries `reviewed_sha256` equal to the measured protocol hash or its
verdict ceases to be `accept`; (c) the gate reason no longer contains `binds unbound`;
(d) the review contract mandates `artifact_sha256`, making the review file the nonconforming party
(patch branch flips to the writer).
