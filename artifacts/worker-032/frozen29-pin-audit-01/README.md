# W032-FROZEN29-LIVE-PIN-AUDIT-01

Bounded class-bound task taken by slot `worker-032` (no inbox card existed for the slot;
self-selected from the live G-FORM critical path). Read-only; no canonical, manifest, schema,
ledger or claim was written.

## Question

At the frame in which F1/F2a/F2b reviewers are being asked to bind
`artifacts/formulation/FROZEN.json#815e08079aef` **plus each per-file pin** (CF-27 moving-target
rule), do all 50 rev29 pins still match the live bytes, are the three class schemas byte-identical
to their authoring mirrors, and do the bytes hold still across a second measurement?

## Pinned frame

| object | value |
|---|---|
| manifest | `artifacts/formulation/FROZEN.json` sha256 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` (revision 29, frozen_at 2026-09-12T00:57:26+08:00, 50 pins) |
| classes | `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` |
| node / gate | F1;F2a;F2b / G-FORM |
| gate pins cross-checked | F0 `0abb9ed8a961`, F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe` |

## Method

`audit_frozen_pins.py` (deterministic, stdlib only, read-only):

1. parses the manifest, checks revision 29 / 50 pins / no duplicate paths / manifest not a member
   of its own files map;
2. measures every pin (`exists`, sha256, bytes, mtime_ns) against its declaration;
3. compares each of the three class schemas between `schemas/` and
   `artifacts/formulation/schemas/` for byte identity (FROZEN `path_policy`);
4. repeats (2) after a fixed interval and reports any hash/bytes/mtime change (CF-27);
5. records the live F0/F1/F2a/F2b prefixes against the pass-07 map pins as a reference;
6. runs three controls before the live measurement and aborts on control failure.

Verdict rule (pre-registered before measurement): PASS iff all 50 pins match **and** the three
mirror pairs are byte-identical **and** nothing changes between T1 and T2; FAIL on any pin/mirror
mismatch; MOVING_TARGET if the manifest or any pin changes inside the window; ERROR if a control
fails or the manifest is unreadable.

## Result (T1 01:12:33, T2 01:13:18 +08:00)

**PASS** — 50/50 pins matched; 3/3 mirror pairs byte-identical; 0 changes between T1 and T2
(manifest stable at `815e08079aef`, 24805 B); F0/F1/F2a/F2b prefixes all matched; controls
K2/K3/K4 pass (`report.json.controls`). No pin mismatch was found, so no offender list exists.

## Falsifier

Falsified if any of the 50 declared pins does not match the live bytes, or any canonical/mirror
class-schema pair is not byte-identical, or any pin changes inside the T1→T2 window, or the
report's counts are not reproducible by re-running the tool at
`artifacts/formulation/FROZEN.json#815e08079aef`.

## Limits

- One repository snapshot and one 45 s stability window; not a continuous watch.
- A PASS binds only the measured hashes at the recorded instants; it is not a G-FORM verdict and
  moves no gate. Reviewer independence and verdict-count questions are outside this task.
- The manifest is authored by the formulation lead; this audit is non-author but does not
  adjudicate the content of the pinned artifacts.

## Reproduction

```bash
python3 artifacts/worker-032/frozen29-pin-audit-01/audit_frozen_pins.py \
        --interval 45 --out /tmp/w032-report.json
```

Exit 0 = PASS, 1 = FAIL/MOVING_TARGET, 2 = ERROR.
