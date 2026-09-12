# Proposed patches — W027-F0-COMPANION-CONSUMER-ALIGN-01

**Status: NOT APPLIED.** All three targets are audit-lead-owned. This worker does not edit another
agent's tools. The predicate-level effect of each change is what was executed and controlled in
`verify_companion_consumers.py` (CTRL-5..CTRL-10); the source diffs below are hand-derived from the
hard-pinned sources and have **not** been applied or run as source edits.

Pinned targets (hard pins, unchanged for the whole run):

| target | sha256 |
|---|---|
| `artifacts/audit/final_gate_verify.py` | `db68655cda2d88b4e0f353f4305f47bf48f3c6708d165b8061138ae5cd298c5b` |
| `artifacts/audit/a1_rebind_coverage.py` | `6fd6ac9b580c8d242a77d789c7be6b5d59891cd6fdd7c483438ee4fbc12c7d05` |
| `artifacts/audit/emit_final_verdicts.py` | `08dbd19157c66d97d3993c18623c97446982f9e3b0975027eaab5225c87e8dc0` |

---

## P1 — `artifacts/audit/final_gate_verify.py`: companion-aware F0 row

Anchor: the `HASH-F0-mirror` `add(...)` call after the hash-matrix loop.

```diff
-    add("HASH-F0-mirror", "fail" if not matrix["F0"]["mirror_equal"] else "pass",
-        f"F0 canonical {matrix['F0']['canonical_sha256'][:12]} vs authoring "
-        f"{matrix['F0']['authoring_sha256'][:12]}; FROZEN rev{fz.get('revision')} declares them distinct "
-        f"logical artifacts (f0_mirror_adjudication_request)",
-        ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"])
+    # F0 is a companion pair (astra-life04 REC-3 / CF-17): byte-identity is not required;
+    # each path must resolve to its own FROZEN pin instead.
+    f0 = matrix["F0"]
+    f0_canon_pin = fz_files.get("research_map/formulation_taxonomy.yaml", {}).get("sha256")
+    f0_auth_pin = fz_files.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256")
+    add("HASH-F0-companion",
+        "pass" if (f0["canonical_sha256"] == f0_canon_pin
+                   and f0["authoring_sha256"] == f0_auth_pin) else "fail",
+        f"companion pair (REC-3): canonical "
+        f"{'pinned' if f0['canonical_sha256'] == f0_canon_pin else 'UNPINNED'}, supplement "
+        f"{'pinned' if f0['authoring_sha256'] == f0_auth_pin else 'UNPINNED'}",
+        ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"])
```

Why the shipped row cannot simply be deleted: the F0 matrix entry keeps
`frozen_match = h == pin` with `pin = fz_files.get(auth) or fz_files.get(canon)`, i.e. it compares the
**canonical** hash to the **authoring** pin, so it is `False` by construction for any companion pair.
The replacement checks each path against its own pin.

Acceptance: on the current revision `HASH-F0-companion = pass`; the `HASH-F1/F2a/F2b-pin` rows are
bit-identical to before (executed at predicate level: CTRL-6); a simulated F1 divergence still fails
`HASH-F1-pin` (CTRL-7).

---

## P2 — `artifacts/audit/a1_rebind_coverage.py`: un-invert the mirror rule

Two hunks. Hunk A adds per-path pins to the measurement record; Hunk B replaces the F0 blocker and
adds a real mirror-divergence blocker.

```diff
@@ meas[t] construction (canonical/authoring block)
             "frozen_pin": pin,
             "frozen_match": (h == pin) if (h and pin) else None,
+            "frozen_pin_canonical": fz_files.get(path, {}).get("sha256") if path else None,
+            "frozen_pin_authoring": fz_files.get(apath, {}).get("sha256") if apath else None,
         }
```

```diff
     for t in ("F1", "F2a", "F2b"):
-        if meas[t]["mirror_equal"] and not meas[t]["frozen_match"]:
+        if not meas[t]["mirror_equal"]:
+            blockers.append({
+                "target": t,
+                "blocker": "dual_tree_mirror_divergence",
+                "measured_sha256": meas[t]["canonical_sha256"],
+                "detail": (f"canonical {meas[t]['canonical_sha256'][:12]} != authoring "
+                           f"{meas[t]['authoring_sha256'][:12]}; mirror pairs must be byte-identical"),
+            })
+        elif not meas[t]["frozen_match"]:
             blockers.append({
                 "target": t,
                 "blocker": "canonical_beyond_frozen_pin",
                 ...
             })
-    if meas["F0"]["mirror_equal"] is False:
+    f0 = meas["F0"]
+    if not (f0["canonical_sha256"] == f0["frozen_pin_canonical"]
+            and f0["authoring_sha256"] == f0["frozen_pin_authoring"]):
         blockers.append({
             "target": "F0",
-            "blocker": "canonical_authoring_divergence",
+            "blocker": "companion_pair_unpinned",
             "measured_sha256": meas["F0"]["canonical_sha256"],
-            "detail": (f"canonical {meas['F0']['canonical_sha256'][:12]} != authoring "
-                       f"{meas['F0']['authoring_sha256'][:12]} (FROZEN rev{fz.get('revision')} pin); mirror-equality policy breached"),
+            "detail": ("F0 is a REC-3 companion pair: each path must be pinned; byte-identity is "
+                       "not required"),
         })
```

Acceptance: the F0 `canonical_authoring_divergence` blocker disappears; a simulated F1 divergence
produces a `dual_tree_mirror_divergence` blocker (executed at predicate level: CTRL-9/10).

---

## P3 — `artifacts/audit/emit_final_verdicts.py`: retire the REC-1/REC-2 wording

Anchor: the `AUD-B2` blocker entry (avoid re-introducing rev-era hardcoded hashes; take them from the
existing matrix).

```diff
-            {"id": "AUD-B2", "node": "F0/G-F0", "description": "F0 canonical 0abb9ed8 != authoring d7419b4e; FROZEN rev27 keeps two logical artifacts; REC-1/REC-2 adjudication still open, so no F0 verdict can bind byte-identically.", "needed_to_unblock": "controller adjudication (REC-1 is now low-risk: class_contract_pointer targets canonical #classes)"},
+            {"id": "AUD-B2", "node": "F0/G-F0", "description": "F0 is a REC-3 companion pair (CF-17): canonical and supplement are separate pinned logical artifacts and byte-identity is not required; reviewers bind the canonical hash and verify the supplement consistency evidence.", "needed_to_unblock": "none (adjudicated); the operative requirement is each path pinned in FROZEN"},
```

Same sentence-level correction applies to the `G-F0` blockers list in the same file
(`"canonical/authoring split unadjudicated (REC-1/REC-2 open)"`) and to
`reviews/G-F0-final-verify.json` (a published verdict artifact — owner decision, listed here only
for completeness).

Acceptance: no gate-surface artifact generated by this emitter records REC-1/REC-2 as open.

---

## Out of scope / not proposed

* `research_map/astra_lifecycle_02..05_events.py` are historical event emitters. Their text records
  the ruling in force when they were written; editing them would rewrite history, not fix a detector.
* The canonical auditor (`research_map/audit_evidence.py`) and controller publication logic
  (`research_map/astra_lifecycle.py`) are already REC-3-aware and need no change.
* The audit lead's newest r2 tools (`artifacts/audit/audit_r2_verdicts.py`,
  `runtime/bin/dispatch_audit_r2.py`) are already REC-3-aware.
