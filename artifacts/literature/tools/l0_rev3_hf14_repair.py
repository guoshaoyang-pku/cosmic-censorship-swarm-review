#!/usr/bin/env python3
"""L0 rev 3 -- bounded, strictly claim-lowering repair closing A0 HF-14.

What this does
--------------
A0 `evaluation_rubric.yaml:244-252` defines

    HF-14 self_certified_acceptance (critical):
      "a ledger or claim record sets status=accepted / validation_status=passed /
       supports_claim=true with no independent reviewer verdict field and no artifact hash"

The detector text explicitly names "a ledger ... record", so it fires on
`ledger/theorems.jsonl`. At the frozen revision ce42d205e761, 50 of 62 rows set
BOTH `status=accepted` AND `supports_claim=true`, and 0 rows carry any
reviewer/verdict field.  HF-14 therefore fires, and its severity is critical:
no L0 verdict at that hash can be accepted while it stands.

This repair removes the *self-certification*, not the *content*:

  * status "accepted"  -> "included_unreviewed"   (50 rows)
        Honest value: the row is admitted to the ledger inventory on the
        author's assessment; it is not an accepted claim.  The evidence-strength
        distinction the old "accepted" carried is already recoverable from the
        untouched `evidence_level` + `verification_status` fields, so nothing is
        lost.  The 11 `provisional` and 1 `rejected` rows are left alone.
  * supports_claim true -> null (+ `supports_claim_basis`)  (50 rows)
        The author's content-level assertion is preserved verbatim in
        `supports_claim_basis`; the unqualified boolean that reads as an
        acceptance is withdrawn because no independent reviewer made it.
  * every row gains `review_status` = "not_independently_reviewed" and
    `acceptance_authority` naming the author and the fact that this is a
    self-assessment.  This is the *missing element* HF-14 names -- recorded
    truthfully as absent rather than fabricated.

Safety properties
-----------------
1. STRICTLY CLAIM-LOWERING.  No field is added or changed in a direction that
   increases what the ledger asserts.  Every edit either withdraws an assertion
   or records a limitation.  A repair with this property cannot inflate.
2. CONTENT-PRESERVING.  No `statement_exact`, `assumptions`, `class_ids`,
   `regularity`, `topology`, `genericity`, `falsifiers`, `unresolved`,
   `source_ids`, `conclusion_type` or `verification_status` value is touched.
   The script asserts this by diffing every untouched key against the input.
3. NO DETECTOR GAMING.  Field names are not renamed to dodge a detector; the
   semantic claim itself is lowered.  `conclusion_type` is deliberately NOT
   renamed -- `research_map/class_separation.py` reads it as an assertion
   surface, so a unilateral rename would silently weaken A1 coverage (see
   `L0-rev3-adjudication` sec. 4).
4. IDEMPOTENT.  Re-running on an already-repaired file is a no-op.

Out of scope (recorded as blockers, not fixed here): HF-02 dual-class rows,
28 unbound rows, HF-03 `source_meta`, L1 `exact_locator`, paywalled primaries.

Usage:
    python3 artifacts/literature/tools/l0_rev3_hf14_repair.py            # dry run
    python3 artifacts/literature/tools/l0_rev3_hf14_repair.py --apply
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "theorems.jsonl"

REVIEW_STATUS = "not_independently_reviewed"
AUTHORITY = ("astra-lead-literature (ledger author; author self-assessment, "
             "not a reviewer verdict)")
SUPPORTS_BASIS = ("author asserts the cited source supports this row's bound "
                  "class; not adjudicated by an independent reviewer")
BASE_NOTE = ("included_unreviewed = admitted to the ledger inventory on author "
             "assessment; no independent reviewer verdict binds to this row")

# Keys that carry mathematical content and must be byte-preserved.
FROZEN_CONTENT_KEYS = (
    "statement_exact", "assumptions", "class_ids", "regularity", "topology",
    "genericity", "falsifiers", "unresolved", "source_ids", "conclusion_type",
    "verification_status", "label", "theorem_id", "evidence_level",
    "scope_caveats", "does_not_imply", "entry_kind", "informs_classes",
    "ledger_tags", "next_action",
)

NEW_KEYS = ("review_status", "acceptance_authority", "supports_claim_basis",
            "status_note")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    rows = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def repair_row(row):
    """Return (new_row, changed_keys). Pure function; no I/O."""
    new = dict(row)  # preserves insertion order; new keys appended at end
    changed = []

    if new.get("status") == "accepted":
        new["status"] = "included_unreviewed"
        new["status_note"] = BASE_NOTE
        changed.append("status")

    if new.get("supports_claim") is True:
        new["supports_claim"] = None
        new["supports_claim_basis"] = SUPPORTS_BASIS
        changed.append("supports_claim")

    if new.get("review_status") != REVIEW_STATUS:
        new["review_status"] = REVIEW_STATUS
        changed.append("review_status")
    if new.get("acceptance_authority") != AUTHORITY:
        new["acceptance_authority"] = AUTHORITY
        changed.append("acceptance_authority")

    return new, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write the repaired ledger (default: dry run)")
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args()

    path = Path(args.ledger)
    before_sha = sha256(path)
    rows = load(path)

    # --- pre-conditions -----------------------------------------------------
    accepted = [r for r in rows if r.get("status") == "accepted"]
    sc_true = [r for r in rows if r.get("supports_claim") is True]
    orphan_sc = [r for r in sc_true if r.get("status") != "accepted"]
    reviewers = [r for r in rows if "reviewer" in r or "verdict" in r]
    vstat = [r for r in rows if "validation_status" in r]

    print(f"ledger      : {path}")
    print(f"sha256      : {before_sha}")
    print(f"rows        : {len(rows)}")
    print(f"status=accepted          : {len(accepted)}")
    print(f"supports_claim=true      : {len(sc_true)}")
    print(f"  ^ not status=accepted  : {len(orphan_sc)}")
    print(f"rows with reviewer/verdict field : {len(reviewers)}")
    print(f"rows with validation_status      : {len(vstat)}")
    print(f"=> HF-14 fires on {len(accepted)} rows (critical)")
    if len(accepted) == 0 and all(r.get("review_status") == REVIEW_STATUS for r in rows):
        print("\nalready repaired: no-op.")
        return 0

    # --- repair -------------------------------------------------------------
    new_rows, per_row_changed = [], []
    for r in rows:
        nr, ch = repair_row(r)
        new_rows.append(nr)
        per_row_changed.append(ch)

    # --- invariant 2: content preservation ---------------------------------
    violations = []
    for old, new in zip(rows, new_rows):
        for k in FROZEN_CONTENT_KEYS:
            if old.get(k) != new.get(k):
                violations.append((old.get("theorem_id"), k))
        for k in old:
            if k in ("status", "supports_claim"):
                continue
            if old.get(k) != new.get(k):
                violations.append((old.get("theorem_id"), k))
    if violations:
        print(f"\nABORT: content-preservation violated on {len(violations)} "
              f"key(s): {violations[:5]}", file=sys.stderr)
        return 2

    # --- invariant 1: strictly claim-lowering ------------------------------
    bad = []
    for old, new in zip(rows, new_rows):
        if old.get("status") == "accepted" and new.get("status") != "included_unreviewed":
            bad.append(old.get("theorem_id"))
        if old.get("supports_claim") is True and new.get("supports_claim") is not None:
            bad.append(old.get("theorem_id"))
    if bad:
        print(f"\nABORT: claim-lowering violated: {bad[:5]}", file=sys.stderr)
        return 2

    # --- post-conditions ----------------------------------------------------
    assert len(new_rows) == len(rows), "row count changed"
    assert not [r for r in new_rows if r.get("status") == "accepted"]
    assert not [r for r in new_rows if r.get("supports_claim") is True]
    assert all(r.get("review_status") == REVIEW_STATUS for r in new_rows)
    assert all(r.get("acceptance_authority") == AUTHORITY for r in new_rows)

    out = "".join(json.dumps(r) + "\n" for r in new_rows)

    print(f"\nrows changing status          : {sum('status' in c for c in per_row_changed)}")
    print(f"rows changing supports_claim  : {sum('supports_claim' in c for c in per_row_changed)}")
    print(f"rows gaining review_status    : {sum('review_status' in c for c in per_row_changed)}")
    print("post-conditions               : OK (0 accepted, 0 supports_claim=true, "
          f"{len(new_rows)} review_status)")

    if not args.apply:
        print("\nDRY RUN -- pass --apply to write.")
        return 0

    path.write_text(out)
    after_sha = sha256(path)
    print(f"\nwrote {path}")
    print(f"new sha256: {after_sha}")
    (ROOT / "artifacts" / "literature" / "reviews"
     / "L0-rev3-hf14-repair.json").write_text(json.dumps({
         "tool": "artifacts/literature/tools/l0_rev3_hf14_repair.py",
         "before_sha256": before_sha,
         "after_sha256": after_sha,
         "rows": len(new_rows),
         "hf14_rows_closed": len(accepted),
         "supports_claim_withdrawn": len(sc_true),
         "content_preserved": True,
         "claim_lowering": True,
     }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
