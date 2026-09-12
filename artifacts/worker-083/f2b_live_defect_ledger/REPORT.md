# W083 F2b live defect ledger — W083-F2B-REV13-LIVE-DEFECT-LEDGER-01

Verdict (worker-level): **3 blocking defect classes + 1 binding defect reproduced at live F2b
rev13 `b2ab6acb` under FROZEN rev29 `815e0807`**; a minimal two-line text repair is validated in
sandbox only. No gate verdict, node status, or canonical write.

## Blocking
1. **D1** `implication_ledger.forbidden_transfers[0].reason` (:246) — "C2 is a strictly larger
   extension class" contradicts the file's own chain at :239.
2. **D2** `regularity.must_not_conflate[0]` (:152) — live "No containment with C2 or C0 is
   asserted here" against :239/:242-243/:272 and the corrected C2 sibling.
3. **D3** `conclusion_type` (:211) — token outside F0's declared allowed vocabulary; **the
   same conflict is present on F2a**, which currently carries 3 live accepts (new here).

## Non-blocking
- **D4** semantic-escape corpus base `1bb78ce9` != live `b2ab6acb` (reproduces worker-075 SF).

## Checks
| id | kind | result | observed |
|---|---|---|---|
| P-pin-af_scc_c0_vacuum.yaml | pin | PASS | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| P-pin-af_scc_c0_vacuum.yaml | pin | PASS | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| P-pin-af_scc_c2_vacuum.yaml | pin | PASS | e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe |
| P-pin-af_wcc_vacuum.yaml | pin | PASS | d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d |
| P-pin-formulation_taxonomy.yaml | pin | PASS | 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3 |
| P-pin-taxonomy_consistency.json | pin | PASS | 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b |
| P-pin-FROZEN.json | pin | PASS | 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 |
| P-pin-VOCAB_ALIASES.json | pin | PASS | 46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba |
| P-pin-semantic_escape_rebased.json | pin | PASS | 7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292 |
| P-pin-check_class_schema.py | pin | PASS | 000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff |
| P-mirror-identical | pin | PASS | b2ab6acb2bbe7f86==b2ab6acb2bbe7f86 |
| P-frozen-rev29-pins-c0 | pin | PASS | rev=29 pin=b2ab6acb2bbe7f86 |
| P-f0-binding | binding | PASS | f0=0abb9ed8a96135c9 ev=9e335e9ba1bfcf77 |
| D1-chain-present | defect | PASS | [239] |
| D1-inverted-premise-live | defect | PASS | [{'line': 246, 'text': '- {from: "no proper future C2 extension", to: "this clas |
| D1-directional-consistency | defect | PASS | text says larger |
| D2-denial-live | defect | PASS | [{'line': 152, 'text': '- "H2_loc (locally square-integrable curvature) is a dis |
| D2-sibling-corrected | cross-check | PASS | sibling live denials=0 |
| D3-extraction-path | defect | PASS | {'F1': 1, 'F2a': 1, 'F2b': 1} |
| D3-vocab-conflict-set | defect | PASS | ['F2a:scc_c2_future_inextendibility', 'F2b:scc_c0_future_inextendibility'] |
| D3-sibling-F2a-same-conflict | cross-check | PASS | True |
| D3-adjudication-open | defect | PASS | {'F0_C0': 'strong_cosmic_censorship_C0', 'VOCAB_ALIASES_canonical_C0': 'scc_c0_f |
| D4-corpus-base-stale | binding | PASS | base=1bb78ce9b3572cda live=b2ab6acb2bbe7f86 |
| S-no-other-carrier | sweep | PASS | {'inverted': [], 'denial': []} |
| S-F1-clean | sweep | PASS | {'inverted': 0, 'denial': 0} |
| S-F2a-clean | sweep | PASS | {'inverted': 0, 'denial': 0} |
| R1-minimal-edit-set | repair | PASS | [152, 246] |
| R1-yaml-valid | repair | PASS | True |
| R1-binding-unchanged | repair | PASS | {'class_id': True, 'f0_binding': True} |
| R1-carriers-closed | repair | PASS | {'inverted': 0, 'denial': 0} |
| R1-canonical-gate-blindness-note | repair | PASS | {'candidate_exit': 0, 'live_exit': 0, 'candidate_tail': 'ang/workdir/ai4math-swa |
| C-controls | control | PASS | 7/7 |
| SNAP-af_scc_c0_vacuum.yaml | snapshot | PASS | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| SNAP-af_scc_c0_vacuum.yaml | snapshot | PASS | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| SNAP-af_scc_c2_vacuum.yaml | snapshot | PASS | e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe |
| SNAP-af_wcc_vacuum.yaml | snapshot | PASS | d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d |
| SNAP-formulation_taxonomy.yaml | snapshot | PASS | 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3 |
| SNAP-taxonomy_consistency.json | snapshot | PASS | 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b |
| SNAP-FROZEN.json | snapshot | PASS | 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 |
| SNAP-VOCAB_ALIASES.json | snapshot | PASS | 46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba |
| SNAP-semantic_escape_rebased.json | snapshot | PASS | 7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292 |
| SNAP-check_class_schema.py | snapshot | PASS | 000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff |
| P-stability-pre-post | pin | PASS | stable |

## Controls
| id | expected | observed | result |
|---|---|---|---|
| C1-live-noop | 1 | 1 | ok |
| C1b-live-noop | 1 | 1 | ok |
| C2-revert-246 | 1 | 1 | ok |
| C3-revert-152 | 1 | 1 | ok |
| C4-mention-only | 0 | 0 | ok |
| C5-foreign-weakness | 0 | 0 | ok |
| C6-chain-assertion | 0 | 0 | ok |

## Candidate (not applied)
`candidate/af_scc_c0_vacuum.yaml` sha256 `1315427fbc92ed118982f20998066fd21c1714714213dc70b04023da74be3275`; edited lines [152, 246]; changes only
`strictly larger -> strictly smaller` and replaces the denial with the sibling's nested-extension
correction. D3 is deliberately not applied (gate-owner adjudication). The canonical structural
gate exits 0 on both the defective live file and the candidate — blind to these carriers
(consistent with worker-017 N17-R13-01).

## Falsifier
Re-run this instrument at the cited pins: falsified if any check FAILs, if either carrier is absent
or scoped at the live bytes, if an extension-set reading exists in which E_C2 strictly contains
E_C0, if the F2a token is inside the F0 allowed vocabulary, if a third carrier exists, if any
control departs from its tabled value, or if any pinned input moved during the run.
