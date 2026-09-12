# W058-F2B-ACCEPT-DISPOSITION-06

Bounded, class-bound artifact-consistency audit taken by worker-058 at 2026-09-12 ~01:15 +08:00.
No assignment card existed in `comms/inbox/worker-058.jsonl` (relaunched slot), so this is the
successor task the immediate queue implied: G-FORM's F2b coverage is now nominally met at the
live pin by full-schema ACCEPTs, while same-pin REVISE verdicts still record two live hard
carriers. The audit measures whether the accepts dispose of those carriers.

## Class binding

- node `F2b`, class `AF-SCC-C0-VAC-GEN` (sibling `AF-SCC-C2-VAC-GEN` referenced only as pin)
- gate context `G-FORM`; this report is **not** a gate verdict and moves no node status.

## Pins measured (all three stable before/during/after the run)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` (rev29) |

## Result

**Verdict: `CONFLICT_UNRESOLVED_NO_DISPOSITION`.**

- 17 F2b verdicts bind the live C0 pin by a declared pin field or an explicit measured-target
  statement; 97 F2b-related files bind older pins and are excluded (listed in the report).
- 5 are ACCEPTs with `hard_failures=[]`: worker-001, worker-090, worker-052, worker-071,
  worker-072. None of them mentions, let alone disposes of, the two live hard carriers.
- The same pin carries 12 non-accepts, including hard records on:
  - **H1** `regularity.must_not_conflate[0]` line 152, "No containment with C2 or C0 is asserted
    here", recorded hard by worker-035, worker-066, worker-017, worker-018;
  - **H2** `implication_ledger.forbidden_transfers[0].reason` line 246, "C2 is a strictly larger
    extension class", recorded hard by worker-053, worker-075, worker-018;
  - **M1** `conclusion.forbidden_weakenings` line 235, "replacing future by two-sided direction",
    live but recorded only as minor (worker-058 rounds 2-4) and not re-recorded at this pin.
- `disposed_by_accepts` is empty for all three carriers, and no accept carries a hard record for
  them (`accepts_with_hard_record: []`).

So the accept set and the hard-finding set are in unresolved conflict at the same bytes: the
accepts do not discharge H1/H2, and the revise side does not withdraw them. Consuming "F2b >= 2
accepts" as gate coverage without an explicit disposition decision is unsupported by these
bytes; that decision (plus blindness/independence) belongs to the audit lead.

## Falsifier

A reader shows (a) an accepting verdict at the bound pin that explicitly disposes of H1 or H2 in
bytes this classifier missed, (b) that a listed hard carrier is absent from the bound C0 bytes,
or (c) that a listed hard record is not present in the cited review at its measured hash. Any of
these refutes the corresponding row.

## Deliverables

| file | sha256 |
|---|---|
| `check_accept_disposition.py` | `27d43c9e643614db99634134752c56104835d2e8ece75e23afe91c36c913e2f3` |
| `disposition_report.json` | `b50246161d4bdbd000d72df17bb3813061ef106d54c9281167661bed0f55a38e` |
| `sensitivity_selftest.json` | `59f445c3a8d42a0ffe25d53962add6933b4cd10c6689bbc8e11ff4dd47632979` |
| `checkpoint.json` | see checkpoint / status event |

Sensitivity: 6/6 calibrated synthetic controls pass, including an accept that disposes of H2
(flips to `PARTIAL_DISPOSITION`), an accept carrying a hard H2 record
(`ACCEPT_CONTRADICTS_OWN_HARD_RECORD`), a repaired corpus (`CARRIERS_ABSENT_REPAIRED`), a
stale-pin exclusion, and a no-revise control. Reproduce:

```bash
python3 artifacts/worker-058/f2b_accept_disposition/check_accept_disposition.py --root .
```

## Boundary

Lexical, hash-bound measurement of verdict and schema bytes only. A review can examine a carrier
without using its phrase; such a review is recorded as "no mention", not as "no examination".
No mathematical truth, citation support, node completion, `validation_status`, independence
adjudication or gate verdict is claimed. Canonical paths were read-only; nothing outside
`artifacts/worker-058/` was written.
