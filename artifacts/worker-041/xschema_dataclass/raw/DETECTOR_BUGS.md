# W041-XSCHEMA-DATACLASS-01 — detector-bug audit trail

The instrument was run three times before the reported run. Each failure below was a
detector false positive, not an artifact finding; all were fixed before the report was
accepted. Iteration order:

| run | report sha256 (first 12) | result | disposition |
|---|---|---|---|
| draft1 | `12f823ea7057` | 3 FAIL (X3/X4/X5) | crude whole-block numeric-multiset rule + whole-block C0/C2 merge scan; exact JSON overwritten during iteration, bug classes recorded below |
| draft2 | `fe0c4e2cf13a` | 1 FAIL (X5) | retained here as `report.draft2.json` |
| draft3 | `8b92118429ff` | 0 FAIL | retained here as `report.run_c_predeterminism.json` |
| reported | `dcbadf62b9ca` | 0 FAIL | `../xschema_report.json` (cited in the outbox events) |

## False positives found

1. **Whole-block numeric multiset** flagged 14 "class-differentiating" differences.
   They were class-axis fields (extension_regularity `none`/`C2`/`C0`, extension_topology,
   `must_not_conflate` warnings) plus identifier digits (`l1`, timestamps). Fixed by
   restricting the must-be-identical check to the 13 pre-registered SHARED_CORE paths and
   classifying the rest as class-axis / editorial.
2. **Whole-block C0/C2 merge scan** flagged F2b because its `must_not_conflate` text names
   C2 in order to forbid conflation — the controller's CF-16 metalinguistic-mention
   pattern. Fixed by scanning assertion fields only.
3. **Substring token match** flagged `sobolev_variant.status` because `ric` matched inside
   `numeric`. Fixed with word-boundary token matching.

Controls in the accepted run: an in-memory exponent mutation and a decay-rate mutation are
both flagged; a wording-only change is not (X6 PASS).
