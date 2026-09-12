#!/usr/bin/env python3
"""Stage the F0 rev4 revision-record patch (worker-01 / deepseek-flash-01).

Semantics-preserving: records the already-applied astra-classscope-02 amendment as a numbered
revision (F0R-01), replaces the prose `wcc_text_sha256_before` with the real pre-amendment
artifact hash (F0R-02), and separates the observed amendment mtime from the lead supplement's
declared time (F0R-04).  No class text, axis, disjointness row, transfer rule or guard is touched.

Reads : research_map/formulation_taxonomy.yaml        (must equal --expect-before sha256)
Writes: artifacts/worker-01/f0_rev4_candidate.yaml    (staged, NOT the canonical path)
        artifacts/worker-01/f0_rev4.diff              (unified diff of the exact edits)

Exit 0 = all five replacements applied exactly once and the candidate parses as YAML.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CANON = ROOT / "research_map" / "formulation_taxonomy.yaml"
CAND = ROOT / "artifacts" / "worker-01" / "f0_rev4_candidate.yaml"
DIFF = ROOT / "artifacts" / "worker-01" / "f0_rev4.diff"

PRE_AMENDMENT_SHA = "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"

REV4_NOTE = """revision_note_rev4: >-
  rev4 records the astra-classscope-02 amendment of 2026-09-12 as a numbered revision. The
  amendment itself (single-q tail visibility in the AF-WCC-VAC-GEN conclusion; variants SET and
  CH registered parent-keyed; explicit comeager quantifier in the vacuum class conclusions) had
  landed in place at 00:07:07 while the revision field still read 3 and written_at read 23:34, so
  no revision number existed that a review or gate verdict could bind to (finding F0R-01). rev4
  makes no further semantic change: it bumps the revision, corrects the supersedes block to carry
  the real pre-amendment artifact hash instead of prose (F0R-02), and separates the observed
  amendment time (00:07:07) from the lead supplement's declared rev8 time (00:15) in the
  class_scope_adjudication block (F0R-04). Applying agent: set written_at to the observed write
  time of the applied bytes. The sha256 of rev4 is recorded in the publishing event, not in this
  file, because a file cannot carry its own hash.
"""

TIMESTAMP_PROVENANCE = """timestamp_provenance: >-
  created_at is the original draft time. written_at is the observed wall-clock CST of the last
  content write (this rev4 staging); the applying agent must update it to the apply time. The
  class_scope_adjudication block keeps decided_at (observed amendment mtime 00:07:07) separate
  from declared_at_in_lead_supplement (00:15, declared by the lead supplement only, not observed).
  Review finding 10 stands: a declared time must never be read as an observed one.
"""

SUPERSEDES = """  supersedes:
    artifact_sha256_before: "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"
    wcc_text_before_excerpt: "every future-inextendible causal geodesic contained in J-(I+) is complete (SET-based reading)"
    wcc_text_after: "single-q tail predicate; see the AF-WCC-VAC-GEN conclusion text"
    note: >-
      artifact_sha256_before is the pre-amendment declared-F0 artifact hash as carried by F1's
      f0_binding (schemas/f1_falsifier_tests.jsonl, probe F1-AMB-21) and by the flash-02 rebind
      note. The earlier wcc_text_sha256_before value held prose, not a hash, and did not match
      its key name (finding F0R-02).
"""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_edits(written_at: str):
    """The exact (name, old, new) replacements; shared with the delta builder for the
    reverse-apply control (reverse the edits on the candidate -> canonical bytes)."""
    return [
        (
            "E1 written_at",
            'written_at: "2026-09-11T23:34:00+08:00"',
            f'written_at: "{written_at}"',
        ),
        (
            "E2 revision bump + rev4 note",
            "revision: 3\nrevision_note_rev3: >-",
            "revision: 4\n" + REV4_NOTE + "revision_note_rev3: >-",
        ),
        (
            "E3 timestamp_provenance",
            'timestamp_provenance: "created_at and written_at are observed wall-clock CST at write time; '
            'no content timestamp runs ahead of the filesystem (review finding 10)."',
            TIMESTAMP_PROVENANCE.rstrip("\n"),
        ),
        (
            "E4 supersedes block",
            '  supersedes:\n    wcc_text_sha256_before: "set-based reading \'every future-inextendible '
            'causal geodesic contained in J-(I+) is complete\'"',
            SUPERSEDES.rstrip("\n"),
        ),
        (
            "E5 decided_at split",
            '  decided_at: "2026-09-12T00:15:00+08:00"',
            '  decided_at: "2026-09-12T00:07:07+08:00"\n'
            '  declared_at_in_lead_supplement: "2026-09-12T00:15:00+08:00 (lead rev8; declared, not observed)"',
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--written-at", required=True, help="observed CST timestamp for written_at")
    ap.add_argument("--expect-before", default=None, help="expected sha256 of the canonical file")
    args = ap.parse_args()

    raw = CANON.read_text()
    before = sha256_bytes(raw.encode())
    if args.expect_before and before != args.expect_before:
        print(f"REFUSING: canonical sha256 {before} != expected {args.expect_before}")
        return 2

    edits = build_edits(args.written_at)

    out = raw
    for name, old, new in edits:
        n = out.count(old)
        if n != 1:
            print(f"REFUSING: {name}: expected exactly 1 occurrence, found {n}")
            return 3
        out = out.replace(old, new)
        print(f"applied {name}")

    tax = yaml.safe_load(out)
    assert tax["revision"] == 4, tax["revision"]
    assert tax["class_ids"] == [
        "AF-WCC-VAC-GEN",
        "AF-SCC-C2-VAC-GEN",
        "AF-SCC-C0-VAC-GEN",
        "AF-WCC-SCALAR-SPH",
    ]
    assert tax["claims_theorem_status"] is False
    assert tax["class_scope_adjudication"]["supersedes"]["artifact_sha256_before"] == PRE_AMENDMENT_SHA

    CAND.write_bytes(out.encode())
    after = sha256_bytes(out.encode())
    diff = "".join(
        difflib.unified_diff(
            raw.splitlines(keepends=True),
            out.splitlines(keepends=True),
            fromfile="a/research_map/formulation_taxonomy.yaml",
            tofile="b/artifacts/worker-01/f0_rev4_candidate.yaml",
        )
    )
    DIFF.write_text(diff)
    print(f"canonical_sha256_before = {before}")
    print(f"candidate_sha256        = {after}")
    print(f"candidate_bytes         = {len(out.encode())}")
    print(f"yaml_parses             = True")
    return 0


if __name__ == "__main__":
    sys.exit(main())
