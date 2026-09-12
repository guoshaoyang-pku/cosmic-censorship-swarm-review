# W097-F2B-ACCEPT-SUFFICIENCY-01 — F2b rev13 accept-evidence sufficiency audit

- **worker**: worker-097 · **node**: F2b · **class**: `AF-SCC-C0-VAC-GEN` · **gate**: G-FORM
- **question**: at frozen F2b `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (FROZEN rev29
  `815e08079aefbc`), do the accept verdicts recorded at that hash dispose of the two live
  self-contradictions that revise verdicts at the same hash flag?
- **answer**: **INSUFFICIENT** — both carriers are confirmed `INCONSISTENT` from primary
  bytes, and none of the three accepts at the hash disposes of either one. Two of the three
  explicitly exclude the carrier blocks from what they check; the third uses the carrier
  field but never inspects its contested text.
- **not claimed**: no accept/revise/reject verdict on F2b, no gate verdict, no node status,
  no validation promotion, no write outside this artifact directory.

## Primary derivation (line-pinned, from `b2ab6acb2bbe`)

The artifact's own chain, line 239:

> `extension_class_containment: "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2 …"`

so `E_C2` is the **innermost / smallest** extension set. The F2a sibling (line 237) and the
F0 companion supplement (line 145) state the same containment in the other notation:
`E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`.

| carrier | line | text (abridged) | verdict |
|---|---|---|---|
| **HF-246** | 246 | `forbidden_transfers[0].reason`: “C2 is a **strictly larger** extension class, so C2-inextendibility is strictly weaker” | **INCONSISTENT** — C2's extension set is the smallest; the row's conclusion is right, its premise is inverted |
| **HF-152** | 152 | `must_not_conflate[0]`: “… **No containment with C2 or C0 is asserted here** …” | **INCONSISTENT** — the same file asserts that containment at lines 239/242 |

## Accept coverage at the same hash (`b2ab6acb2bbe`)

Classifier: a carrier counts as covered only at `DISPOSED` (explicit line citation,
verbatim contested content, or field + judgment in one statement). `EXCLUDED-FROM-CHECK`
means the carrier is named but explicitly excluded from the check's scope.

| accept | full schema verdict | HF-152 | HF-246 | witness |
|---|---|---|---|---|
| worker-071 `F2b-review-rev13-worker-071.json` | true | EXCLUDED-FROM-CHECK | NONE | instrument line: `# blocks (anti_scope, forbidden_*, must_not_conflate, …) are excluded by design` |
| worker-072 `F2b-review-worker-072-rev29.json` | (field absent) | NONE | EXCLUDED-FROM-CHECK | instrument regex: `non_goals$|forbidden_strengthenings$|…|forbidden_transfers$|` |
| worker-090 `F2b-rev13-full-090.json` | true | NONE | MENTION-ONLY | check C04 reads only `forbidden_transfers[…]["from"]`; `reason` never inspected |

All three reviewed `b2ab6acb2bbe` and were blind/disclosed as recorded. The point is not that
they are worthless — worker-071 records a real major class-distinguishability finding
(`conclusion.statement_formal` identical to F2a) — but that **none of them is evidence about
the contested clauses**. The revise side, by contrast, is recognised by the same classifier
as `DISPOSED` for the carriers it cites (HF-246: workers 017/018/053/066/075/097; HF-152:
workers 017/018/066/097).

## Controls (all passed, `controls_ok: true`)

C1 synthetic disposition → both DISPOSED · C2 worker-097 revise `REVIEW.json` → both
DISPOSED · C3 no-token verdict → both NONE · C4 sandbox `strictly larger`→`strictly smaller`
flips HF-246 to CONSISTENT · C5 sandbox deletion of the line-152 denial flips HF-152 to
CONSISTENT · C6 all pins re-measured after the run, no drift (verified additionally by
`SHA256SUMS.txt` re-check at checkpoint time).

## What a sufficient disposition would look like

An accept at `b2ab6acb2bbe` (or a successor hash) that explicitly cites the carrier
field/line and records a judgment on its content — e.g. “line 246 `reason` read as …, found
consistent because …” or “line 152 denial found non-live/repaired” — or an owner repair of
both lines followed by a fresh hash-bound review. A `reason`-blind `forbidden_transfers`
presence check, or a scan that excludes `must_not_conflate` / `forbidden_transfers` by
design, cannot discharge either carrier.

## Falsifier

An accept verdict recorded at `b2ab6acb2bbe` whose artifact or cited instrument contains a
hash-bound disposition of line 152 or line 246; or a byte-level re-derivation showing line
239 is not a containment assertion; or a measurement of the F2b artifact differing from
`b2ab6acb2bbe` at read time.

## Reproduction

```bash
python3 artifacts/worker-097/f2b_accept_sufficiency/check_accept_sufficiency.py \
        artifacts/worker-097/f2b_accept_sufficiency/report.json
```

Stdlib only; does not import `research_map/class_separation.py` or any other agent's checker.
Raw run output: `run_output.txt`; machine record: `report.json`; pinned copies: `pins/`
(with the instrument/verdict snapshots the coverage scan read).
