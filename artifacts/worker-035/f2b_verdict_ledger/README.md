# W035-F2B-VERDICT-LEDGER-01 (worker-035, read-only)

Node F2b / class AF-SCC-C0-VAC-GEN / gate G-FORM. Answers REC-39 / CF-31: why the F2b
coverage count moved (0/2/3/4/5/7) and which records actually bind the live pin
`schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` (FROZEN `815e08079aef`).

## Mechanism (measured, not inferred)

`reviews/F2b-review-worker-072-rev29.json` was **rewritten in place**: the current revise-3.0
bytes (`7487f310d208`) declare
`supersedes_sha256 = 7487f310d208...` and `supersedes_verdict = accept`. The prior accept bytes
are not preserved on disk. Any count taken before that rewrite sees one more accept than a
count taken after; nothing else moved. Entry pin == exit pin, no drift (control K6).

## Count-rule table (all reproducible from ledger.json)

| rule | count | matches |
|---|---:|---|
| R-C bound accept records + ghosts from supersede fields | 7 | pre-supersession scan |
| R-K full-schema accepts ever bound (live + ghost) | 4 | controller scan "4 full accepts" |
| R-E live bound full-schema accepts | 3 | post-supersession "fresh 3" |
| R-J R-E restricted to non-lead reviewers | 2 | "2 independent full-schema accepts" (worker-071, worker-090) |
| R-A on-disk bound accepts | 6 | current disk |
| R-H all records declaring the pin (any verdict) | 26 | binding population |
| R-I corpus rows scanned | 137 | F2b-identified review files |

The formulation lead's "0 accept / 7 revise" per-file census is **not reproduced** by any rule
derivable from bytes alone; its filter/scoping is not stated in the bytes. Recorded as a
non-claim, not as a refutation.

## Controls
- K1-worker-072-accept-reconstructed-as-ghost: PASS — ghost accept rows for worker-072=1, old_sha=['7487f310d208']
- K2-worker-090-live-bound-accept: PASS — worker-090 bound accept rows=1
- K3-offpin-synthetic-not-bound: PASS — synthetic 0*64 binds pin=False
- K4-bound-implies-pin-hash: PASS — checked=6
- K5-ghost-bytes-absent: PASS — worker-072 old bytes still on disk=[False]
- K6-pin-stable: PASS — entry=b2ab6acb2bbe exit=b2ab6acb2bbe

## Falsifiers
- an on-disk bound accept whose declared sha256 does not appear in its own current bytes
- a ghost record reconstructed from a supersede event whose old hash still exists on disk unchanged
- a live bound accept missing from this ledger that a same-pin re-scan finds
- a count-rule row not reproducible from ledger.json alone
- pin drift between entry and exit measurement

## Authority
Worker measurement only. No canonical path written; no node status, validation_status or gate
verdict set or moved. Independence column = in-record declaration; `author_lineage_candidate`
is advisory. Reproduce: `python3 instrument.py --out .` (reads only; exit 2 on pin drift).
