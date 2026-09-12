# W008-F2B-LINE152-DIRECTION-01 — line-152 replacement-clause direction adjudication

Worker: worker-008 (deepseek-flash-08 slot 008). Class: AF-SCC-C0-VAC-GEN (node F2b, gate G-FORM).
Scope: worker lifecycle only. No node done, no gate verdict, no canonical write, no validation_status=passed.

## Live dispute decided
worker-023 (W023-F2B-DIR-REVIEW-01) reported that the standing F2b rev29 repair
(worker-066 candidate `84b5d3fa29a6`, worker-044 composed `48cadb72e507`) *introduces* a false
entailment in `regularity.must_not_conflate[0]`: "so H2_loc-inextendibility ENTAILS this class's
conclusion". worker-036 (`24/24 candidate checks`) and worker-066 reported the same candidate
defect-free. This run independently adjudicates the dispute at the pinned bytes.

## Oracle (from the documents themselves)
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` declares
`extension_class_containment: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`, i.e.
size ranks {C0:3, H2loc:2, C^1,1:1, C2:0}; `forbidden_weakenings[2]` says
"H2_loc-inextendibility is weaker and entails the C2 sibling, **not this class**"; `subsumption_note`
says "C0 => H2loc => C2, **never the reverse**". Rule used: S_X entails S_Y iff size(X) >= size(Y).
For the clause's claim S_H2loc => S_C0: size(H2loc)=2 < size(C0)=3, so the claim is false.

## Result (2026-09-12T01:12:04+08:00)
| artifact | sha256 | finding |
|---|---|---|
| canonical C0 (live) | b2ab6acb2bbe | denial (`:152`) + inverted size premise (`:246`) — the two known defects |
| worker-066 / prior-008 candidate | 84b5d3fa29a6 | **entailment_direction_inverted** at `regularity.must_not_conflate[0]` |
| worker-044 composed rev14 | 48cadb72e507 | **entailment_direction_inverted** (same clause, byte-identical) |
| worker-024 2-line repair | 679ab7bc8746 | clean |
| worker-023 direction-corrected | 9ab32ee39d00 | clean |

Verdict: **W023_CONFIRMED: standing repair rewrites line 152 into a false H2loc=>C0 entailment; direction-corrected variant is clean**. Controls 6/6 pass (A canonical denial, B re-injected entailment,
C valid C2 direction, D attributed-quote guard, E re-injected size inversion, F empty R06 slot).
Instrument: `adjudicate_line152_direction.py` (fail-closed: exit 2 on any pin move, exit 3 on
unclassifiable carrier). Evidence: `evidence/report.json`, `evidence/pins.json`.

## Falsifier
Exhibit a reading of the pinned C0 document under which E_C0 is not the largest extension set while its own extension_class_containment/forbidden_weakenings/subsumption_note say 'C0 => H2loc => C2, never the reverse'; or show candidate 9ab32ee3 (or my detector) fails on the pins. Any pin move voids the run (exit 2); an unclassifiable carrier exits 3.

## Provenance note
`84b5d3fa` is also this slot's predecessor candidate (W008-FORMSEP04-CANDIDATE-VALIDATION-01);
this run corrects it: its containment-defect repair is right in substance but its replacement
sentence states the C0 entailment backwards. Any landing must use a direction-corrected clause
(e.g. `9ab32ee3` / `679ab7bc` or equivalent) and a gate predicate that certifies entailment
direction, since R06 passes direction-reversed text.
