# W001-F2B-VERDICT-RECONCILIATION-01 — F2b verdict reconciliation at FROZEN rev29

Worker: worker-001. Class: AF-SCC-C0-VAC-GEN (node F2b, gate G-FORM).
Report: `report.json#sha256:efee91e8ad14` (full hash below). Corpus digest:
`f7858ba3332b` over 225 review files.

## Verdict

**F2B_OBJECTIONS_OPEN_NOT_REBUTTED** — reason codes: OBJ-F2B-C1, OBJ-F2B-C2, OBJ-F2B-D1, OBJ-F2B-D2.

At the pinned bytes the two normative containment carriers named across the F2b corpus
are mechanically live: C1 `regularity.must_not_conflate[0]` line
152 denies containment while the same file's chain asserts it;
C2 `implication_ledger.forbidden_transfers[0].reason` line
246 calls C2 "strictly larger" while the same file makes
E_C2 the innermost set. Declared-hash layer: D1 sidecar and D2 entry_hashes are live stale;
D3 aggregator is re-pinned at the measured bytes. The cross-artifact vocabulary item is
contested and not adjudicated here.

## Verdict census (both rules declared)

| rule | full accepts | full revises | scoped revises |
|---|---|---|---|
| R1 live controller advisory | 3 (worker-052, worker-071, worker-090) | 4 | 0 |
| R2 declared wider closed | 3 (worker-052, worker-071, worker-090) | 7 | 4 |

The R1/R2 gap is the instrument point: reviews that target the pin with the protocol's
recommended `path#sha256` form (worker-018, worker-029, worker-053, worker-066) or omit
`target_id` (worker-035) are not bound by the live advisory scan even though their
`reviewed_sha256`/`artifact_sha256` is exactly the pin. Binding remains the audit lead's call.

## Rebuttal

No full-schema accept in the snapshot cites either carrier defect sentence
(`rebuttal_scan`); the one accept that mentions `must_not_conflate` (worker-052) lists the
slot as a positive check without engaging line
152. The 4 full accepts therefore do not close C1/C2.

## Repair coverage

The worker-001 candidate `REPAIR_CANDIDATE.yaml#sha256:90ede5c9516b` (author = this
worker; not independent) clears both carriers under the same oracle, changed base lines
[152, 246]; it does not address D1/D2. Independent verification of
other circulating candidates is `reviews/F2b-repair-candidate-verify-worker-029.json`.

## Controls

17/17 controls pass, including a live-instrument agreement check against
`research_map/astra_lifecycle.py#sha256:548329414083` on the
same snapshot bytes (203 reviews compared).

## Falsifiers

See `report.json` `falsifiers`. Any pin move exits 3; any control departure exits 4; a later
review write is a new corpus revision, not a falsifier.
