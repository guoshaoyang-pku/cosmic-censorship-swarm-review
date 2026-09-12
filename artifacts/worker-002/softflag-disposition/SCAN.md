# AF-SOFTFLAG-DISPOSITION-02 — class-separation soft-flag disposition (F0/F1)

**Worker:** `worker-002` (bounded execution worker, one class-bound task)
**Final measurement:** `2026-09-12T00:19:55+08:00` (single instant; every hash measured together)
**Nodes / classes:** `F0` (taxonomy) and `F1` (`AF-WCC-VAC-GEN`), covering all four frozen
class ids (`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`)
**Verdict (current revision):** `CURRENT_REVISION_CLEAN__PRIOR_REVISION_FLAGS_DISPOSED_AS_FALSE_POSITIVES`
**Prior revision (frozen evidence):** `ALL_SOFT_FLAGS_DISPOSED_AS_FALSE_POSITIVES` (3/3 false
positives, `superseded/disposition-rev-0fcc6a19.json`, `a082e47591f5…`)

**This is not a schema review verdict, not a gate proposal, and it cannot move a gate.**
The `00:11:13` lifecycle left three un-disposed `CLASSSEP-SOFT: unknown class token` findings
(G-F0's unmet list names the two F0 ones). This task reproduces them, dispositions all three as
checker false positives, and records that the formulation lead's `00:18:26–00:18:37` rewrite
removed the flag-generating references — three re-measurements since then report **0 detector
findings of any kind on all four canonical artifacts**.

## 1. Headline

| revision | measured | detector findings on F0/F1/F2a/F2b | flags |
|---|---|---:|---:|
| `0fcc6a1928fd` (F0) / `68392dd82050` (F1) | 00:18:15 | 2 + 1 | 3, all false positives (frozen evidence below) |
| `276009f4f63db` / `16128b62fe08` | 00:18:51 | 0 | 0 |
| `276009f4f63db` / `9a8bd4c96800` | 00:19:34 | 0 | 0 |
| `276009f4f63db` / `9a8bd4c96800` (final) | 00:19:55 | 0 | 0 |

The machine-readable series is `revision_watch.jsonl` (`9ff02c66dd4a…`); the first three lines
include two post-hoc records labelled as such, because the churn happened while this task ran.
**Implication:** the soft-flag criterion that G-F0/G-AUDIT cite is discharged at the current
revision, but the checker mechanism that produced the flags is unchanged and latent — any future
variant reference of the same form will re-flag.

## 2. The three flags (frozen prior revision)

The detector's `KNOWN_CLASSES` holds only the four frozen ids, and its body-text extractor
matches exactly four hyphen segments
(`AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+`). Both properties cause false positives on
legitimate variant references.

| flag | artifact | token reported | cause | verdict |
|---|---|---|---|---|
| `SOFTFLAG-F0-01` | F0 canonical, line 88 | `AF-WCC-VAC-GEN-SET` | registered variant (`parent_class=AF-WCC-VAC-GEN`, `variant_id=SET`); occurrence is a quoted `.delta.json` path | **FALSE POSITIVE** |
| `SOFTFLAG-F0-02` | F0 canonical, line 103 | `AF-SCC-C0-CH-VAC` | detector **prefix truncation**: the file contains `AF-SCC-C0-CH-VAC-GEN` (registered variant `parent_class=AF-SCC-C0-VAC-GEN`, `variant_id=CH`); the reported string does not occur literally | **FALSE POSITIVE** |
| `SOFTFLAG-F1-03` | F1, line 243 | `AF-WCC-VAC-GEN-SET` | registered variant inside a path reference on a `note:` that *prohibits* binding that variant as a class | **FALSE POSITIVE** |

Resolution rule (machine-checked, no lexical guessing): a token is a registered variant iff
deleting one hyphen-delimited occurrence of `-<variant_id>` leaves a frozen `parent_class`.
This covers both naming forms in use — `PARENT-SET` and the infix `AF-SCC-C0-CH-VAC-GEN`.
Bindings come from the canonical taxonomy `variants:` block **and** `VARIANT_REGISTRY.json`;
the two agree on both variants, and both delta files exist and declare the same
`(parent_class, variant_id)`:

- `artifacts/formulation/variants/AF-WCC-VAC-GEN-SET.delta.json` — `2187d411bf25…`, binds `true`
- `artifacts/formulation/variants/AF-SCC-C0-CH-VAC-GEN.delta.json` — `80b54ccea568…`, binds `true`

The registry also carries five variants with no delta-file references (`H2LOC`, `LIP`,
`DISTRIBUTIONAL`, `L2CONN` on `AF-SCC-C0-VAC-GEN`; `TWOSIDED` on `AF-SCC-C2-VAC-GEN`); none
occurs in a frozen canonical artifact. Recorded in `token_census.json` for the next checker
revision.

## 3. Current revision — hash-pinned inputs and census

| artifact | sha256 | bytes |
|---|---|---:|
| `research_map/formulation_taxonomy.yaml` (F0, canonical) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` | 35145 |
| `schemas/af_wcc_vacuum.yaml` (F1) | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` | 33642 |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` | 28268 |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` | 33276 |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` | 10609 |
| `research_map/class_separation.py` (detector) | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` | 11152 |
| `research_map/research_map.json` (map at scan time) | `4d8291c9a9ae44558a4dea49106b525ed7b5c8a2b25cc003a5a754ddb3507306` | 840553 |

Class-field census (`class_id` / `class_ids` values walked and resolved):

| scope | class-field values | violations | findings |
|---|---:|---:|---:|
| F0 canonical | 1 | 0 | 0 |
| F1 | 6 | 0 | 0 |
| F2a | 6 | 0 | 0 |
| F2b | 8 | 0 | 0 |
| map | 235 | 0 | 1 hard (O1) |

Every maximal `AF-*` token in the four canonical artifacts resolves to a frozen class, a family
abbreviation (`AF-WCC`, `AF-SCC`), or a registered variant. **No variant id occurs in any
`class_id`/`class_ids` field.** The 17 map entries reported as anomalies are the literal string
`"class_ids"` left in `_normalized.class_id` by the map's event normalizer — a normalization
artifact, not a class token. (Map hash is a moving target: the controller applies events
continuously; O1 was created after the `00:11:13` lifecycle.)

## 4. Controls (7/7 pass — the disposition does not weaken real detection)

| control | purpose | result |
|---|---|---|
| C1 | an unregistered variant-like token stays `unresolved` and is flagged | pass |
| C2 | detector extractor truncates `AF-SCC-C0-CH-VAC-GEN` to `AF-SCC-C0-CH-VAC` | pass |
| C3 | the SET verdict depends on the explicit `(parent_class, variant_id)` binding, not on regex | pass |
| C4 | a bare composite (`class_id: "C0 or C2"`) is still caught | pass |
| C5 | falsifier path: a variant token in a `class_id` field is treated as a genuine violation | pass (reachable) |
| C6 | text route vs dict route on a full-class-id composite (finding G2) | pass |
| C7 | text route on a 3-segment AF- token (finding G3) | pass |

## 5. Secondary findings — checker, not artifacts

- **G2 (minor, class-bound).** `findings_for_text` does **not** flag
  `class_id: AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN`; the dict/map route
  (`findings` → `_scan_class_ids`) does. `audit_evidence.py` scans artifacts with the text
  route only, so a full-class-id composite in an artifact is currently invisible to the
  lifecycle audit.
- **G3 (minor, class-bound).** The body-text unknown-token scan requires exactly four hyphen
  segments, so a short `AF-` token in prose (`AF-WCC-BAD`) is not reported; the field-level
  `_scan_class_ids` path still catches it in a `class_id`/`class_ids` value.

## 6. Observations not disposed here (require controller / lead adjudication)

- **O1 (major, live hard route).** `findings_for_map` flags `claims[36].statement`
  (`flash02-opencase-claim-0010b-20260912T0015`) as *"composite C0/C2 asserted as one class"* —
  a **hard** finding for `audit_evidence.py`. The claim text describes two **split**
  dispositions ("the 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new
  class"); `_scan_composite`'s prose branch tests `_MERGE_ASSERT` before `_PROHIBIT`/`_SPLIT`
  and only exempts a negation immediately before the assertion, so the descriptive use of
  "merge" is flagged. Candidate false positive; not disposed by this worker.
- **O2 (major, authoring tree).** The authoring F0 mirror
  (`artifacts/formulation/formulation_taxonomy.yaml`, `c8e979a1eb48…`) emits **three hard
  composite flags** on its `composite_regularity_ban` clause — a sentence that *prohibits*
  `'C0 or C2'`. Same branch-order weakness as O1. `audit_evidence.py` does not scan the
  authoring tree, but it is a frozen pin that must be published byte-identically before
  verdicts bind; publishing it as-is would inject three hard failures.
- **F0 dual-tree divergence remains open** at the final instant: canonical `276009f4f63db` vs
  authoring `c8e979a1eb48`. F1/F2a/F2b mirrors are aligned. Out of scope here; recorded by the
  A1 audit.

## 7. Falsifier

Reject the disposition of the prior-revision flags if any of the following holds:

1. any maximal `AF-*` token in the flagged revision resolves as neither a frozen class, nor a
   family abbreviation, nor a registered variant with `parent_class` among the four frozen ids;
2. any variant token appears as a `class_id` / `class_ids` value;
3. a reported token occurs literally as a standalone class-like identifier rather than as a
   path/registry reference — `SOFTFLAG-F0-02` is specifically falsified by showing the literal
   string `AF-SCC-C0-CH-VAC` anywhere in F0's canonical artifact;
4. the exact-token extraction is shown to drop a genuine unknown token the detector would catch.

Any of (1)–(3) makes the corresponding flag genuine leakage instead of a false positive. The
current-revision cleanliness claim is falsified by re-running the instrument and obtaining any
`CLASSSEP` finding at the pins in §3; the revision watch makes the churn auditable.

**What this is not:** not a review verdict on F0/F1, not a claim that the four classes are
semantically disjoint, and not a disposition of O1/O2. A worker event cannot set
`status=done`, `validation_status=passed`, or any gate verdict.

## 8. Artifacts and reproduce

| file | sha256 |
|---|---|
| `disposition.json` | `792341cb579d404f2f78dd0e0d986d75b0993b68095a127da9e4b60e58dfcde4` |
| `token_census.json` | `9c38693dd1dc14583260002b242f287c25ccbedff474bf8fcd17768bec52d765` |
| `controls.json` | `4cabf1b590cc925d50600f94c99cdd184ca452b14523fd3006143263e6704fa3` |
| `revision_watch.jsonl` | `9ff02c66dd4a58803c896cd4471e12bef4bf8bf06c63132fbff1378977d5b7af` |
| `scan_softflags.py` | `7e8c752986d0443030201d3fba6f0e3ba6c2e6e1eee8d7553a7ba8ccd80bef24` |
| `superseded/disposition-rev-0fcc6a19.json` | `a082e47591f5e14e746da5a273db26ac05a35d9418410dd736ac1cc6650b868c` |
| `manifest.json` | (hashes the files above; does not hash itself) |

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-002/softflag-disposition/scan_softflags.py
```

The scanner re-measures its own inputs (never trusts stored hashes), is read-only with respect
to every canonical artifact, and writes only inside `artifacts/worker-002/softflag-disposition/`.
