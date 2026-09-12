# W081-N0-PINSPLIT-ADJ-01 — N0 stop-rule item (2): F0-pin split adjudication

**Worker:** worker-081 · **Class:** `AF-WCC-SCALAR-SPH` · **Node:** N0 · **Gate:** G-NUM
**Review verdict:** revise 3.5 · **Disposition:** `ITEM2_OPEN_PIN_SPLIT_CONFIRMED`
**Materiality:** `BINDING_IS_METADATA_NOT_ORDER_DEPENDENT`
**Remedy:** `BYTE_PRESERVING_ADDENDUM_RECOMMENDED`

Worker evidence only. This is not a gate verdict, not a node transition, and no canonical
artifact was edited.

## Question

N0 stop-rule item (2), from card `astra-life04-n0-stoprule`, reads: *"re-bind the class binding
to declared F0 rev5 `0abb9ed8a961`."* At the same post-stoprule hashes, two N0 reviews disagree:

| review | actor | item (2) | basis |
|---|---|---|---|
| `reviews/N0-review-final-verify.json` | astra-lead-audit | **closed** | rev3 `class_binding` names rev5 |
| `reviews/N0-review-worker-042.json` | worker-042 | **open** (HF-042-N0-1) | protocol of record still cites `66bf917b`/`565a6e50`; no single binding hash |

Since G-NUM needs an N0 accept that leaves no stop-rule item open, the disagreement is
decision-critical. This task adjudicates it mechanically, at pinned hashes, and prices the two
possible remedies.

## Method (deterministic, stdlib-only)

`adjudicate_pin_split.py` reads each input once, pins its sha256, and re-hashes the seven
canonical inputs after the run (drift control K7).

1. **Citation census** — every F0/taxonomy pin claim across the N0 evidence chain and its
   context documents, with document, line/JSON pointer, family, and classification against the
   live taxonomy bytes.
2. **Materiality** — structural test: the certification and raw 4-rung study contain no
   taxonomy string; taxonomy strings in the closure artifact occur only under documentation
   pointers (`/class_binding`, `/stop_rule_closures`, `exists::` checks), never under
   `/certification_basis` or `/order_claim`; the generator's taxonomy-derived variables
   (`f0_text`, `f0_sha`, `F0_REV5_SHA`) appear only in definitions, `check()` assertions and the
   serialized binding record.
3. **Authority-carrier search** — scan of map findings/gates/lock, the lifecycle-05 decisions
   and the accepted event stream for an authority record naming one N0 class-binding carrier.
4. **Remedy cost** — enumerate review verdicts bound to the protocol hash (target or
   `reviewed_sha256`), then compute the hash of a sandbox protocol copy with the stale pins
   replaced, versus the addendum path.
5. **Proposal checker** — the proposed addendum must pass six checks; three mutated variants
   (wrong binding sha, stale binding sha, carrier that does not name the binding) must be
   rejected.

## Results (pins at run time)

```
F0 taxonomy (live)                       0abb9ed8a961
numerics/CONVERGENCE_PROTOCOL.md         1e6cdf04d7a2
numerics/results/flat_wave_convergence_rev3.json   da7c36071995
numerics/protocol/n0_fixed_dt_certification.json   1677822ceb9c
numerics/protocol/fixed_replication_verdict.json   dcad962324e3
reviews/N0-review-final-verify.json      18a0c0d0e77f
reviews/N0-review-worker-042.json        def37cffb7db
```

**The split is real.** In the N0 evidence chain, the protocol of record carries *stale* pins only
(`66bf917bd368` at line 7; `66bf917b`/`565a6e50` at line 159) and never the current hash, while
the rev3 closure artifact and the builder carry `0abb9ed8a961`. A fourth document,
`numerics/protocol/fixed_replication_verdict.json`, still pins the superseded `66bf917b…` and
declares `binding_status: PROVISIONAL`.

**The binding is metadata, not order-dependent.** The certified order numbers live in the
certification and 4-rung study, neither of which references the taxonomy; rev3's taxonomy
strings are documentation pointers only; the builder reads the taxonomy solely to assert
`revision: 5`, the class id, and the recorded hash.

**No single binding carrier exists.** 0 authority records name one; 5 near-misses name both
hashes without asserting a carrier. REC-15 explicitly declines controller self-adjudication of
the neighbouring protocol contest, and no map field names a class-binding carrier for N0.

**Remedy cost is asymmetric.** Six review records are bound to `1e6cdf04d7a2` (3 accepts,
3 revise; 4 distinct reviewers, incl. this worker's withdrawn accept and later adj2 accept). A
protocol rewrite moves the hash (`1e6cdf04d7a2` → `d3cbbff72eed` in the sandbox) and therefore
voids or re-opens all of them; a byte-preserving addendum leaves the protocol hash unchanged.

## Proposed remedy (proposal only — not applied)

`proposed/n0_class_binding_addendum.json` names `research_map/formulation_taxonomy.yaml`
`#0abb9ed8a961` (rev5) as the class binding of record, names
`numerics/results/flat_wave_convergence_rev3.json#da7c36071995` as the carrier of stop-rule
item (2), and supersedes the protocol's stale *class-binding pin citation only* while leaving
its bytes, rules and bound verdicts in force. Checker: 6/6 pass; all three mutants rejected.
Adoption requires the controller or a group lead; this file binds nothing by itself.

## Checks and controls

11/11 machine checks pass, 7/7 controls pass (determinism, stale/current negatives, no
canonical write, zero-carrier positive control, mutant controls, hash drift clean).

## Falsifier

Discharged if the controller/lead publishes an authority record naming one N0 class-binding
carrier at `0abb9ed8a961`, or re-issues the protocol at a new hash with all bound verdicts
re-run. Falsified if any pinned hash here moves, if the live taxonomy is not `0abb9ed8a961`, if
the checker accepts any mutated addendum variant, or if a measurement shows the order claim
depends on taxonomy content.

## Non-claims

Not a gate verdict; no N0 status change; no canonical edit; `numerics_lock` untouched, no
solver, N1 stays queued; binds only to the measured hashes.
