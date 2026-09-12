#!/usr/bin/env python3
"""Rev 3 source-of-truth repair: separate the CONTENT axis from the REVIEW axis.

Why this exists
---------------
`ledger/theorems.jsonl` is a BUILD PRODUCT of `artifacts/literature/theorems/batch-*.jsonl`
(see `build_literature.py`). Patching the product alone is not durable: the next build
reverts it, and the builder's own validator would fail closed on the new vocabulary.

The defect (A0 HF-14, `evaluation_rubric.yaml:244-252`) is a collision between two axes
that the old single `status` field conflated:

  * CONTENT  -- does the row meet the content bar (verified, non-metadata source whose
                quote entails the statement)?  This is what `status: accepted` meant.
  * REVIEW   -- has an independent reviewer accepted the row?  No row has ever had this,
                and `status: accepted` was read by A0 as asserting it.

Measured at `ce42d205e761`: 50 rows `status=accepted` and 60 rows `supports_claim=true`,
with 0 reviewer/verdict fields -- and A0's own audit tool reports HF-14 `critical` at the
corpus level over 15 ledger files. Collapsing the tiers is NOT lossless: `preprint +
abstract-read` and `peer-reviewed + abstract-read` both occur in the `accepted` AND the
`provisional` tier, so the tiers carry information that `evidence_level` does not recover.

Fix: give each axis its own key.
  status: "accepted"            -> content_status: "verified"
  status: "provisional"         -> content_status: "provisional"
  status: "rejected"            -> content_status: "rejected"
  supports_claim: <bool>        -> author_asserts_supports: <bool>

Neither new key can be read as a review verdict, and `review_status` (emitted by the
builder on every row, always "not_independently_reviewed" until a real verdict exists)
records the review axis truthfully as absent. No content value is touched.

Usage:
    python3 artifacts/literature/tools/rev3_axis_split.py            # dry run
    python3 artifacts/literature/tools/rev3_axis_split.py --apply
"""
import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATTERN = str(ROOT / "artifacts" / "literature" / "theorems" / "batch-*.jsonl")

STATUS_MAP = {"accepted": "verified", "provisional": "provisional",
              "unresolved": "unresolved", "rejected": "rejected"}

# Keys whose values carry content and must not move.
CONTENT_KEYS = ("statement_exact", "assumptions", "class_ids", "regularity", "topology",
                "genericity", "falsifiers", "unresolved", "source_ids", "conclusion_type",
                "label", "theorem_id", "entry_kind", "scope_caveats", "does_not_imply",
                "ledger_tags", "next_action", "genericity")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def convert(d):
    """Return (new_dict, changed) preserving key order; renamed keys stay in place."""
    out, changed = {}, []
    for k, v in d.items():
        if k == "status":
            out["content_status"] = STATUS_MAP.get(v, v)
            changed.append(f"status->content_status:{v}->{out['content_status']}")
        elif k == "supports_claim":
            out["author_asserts_supports"] = v
            changed.append(f"supports_claim->author_asserts_supports:{v}")
        else:
            out[k] = v
    return out, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(PATTERN))
    total_rows = total_changed = 0
    before, after = {}, {}
    for f in files:
        lines = [l for l in Path(f).read_text().splitlines() if l.strip()]
        if not lines:
            continue
        before[f] = sha(f)
        new_lines, nch = [], 0
        for l in lines:
            d = json.loads(l)
            nd, ch = convert(d)
            # content-preservation guard
            for k in CONTENT_KEYS:
                if d.get(k) != nd.get(k):
                    print(f"ABORT: content key {k} changed in {f}", file=sys.stderr)
                    return 2
            if ch:
                nch += 1
            new_lines.append(json.dumps(nd, ensure_ascii=False))
        total_rows += len(lines)
        total_changed += nch
        if args.apply and nch:
            Path(f).write_text("".join(x + "\n" for x in new_lines))
            after[f] = sha(f)
        print(f"{Path(f).name:<16} rows={len(lines):<4} changed={nch:<4}"
              + (f" sha {before[f][:12]} -> {after.get(f,'(dry)')[:12]}" if nch else ""))

    print(f"\ntotal rows={total_rows} changed={total_changed}")
    if not args.apply:
        print("DRY RUN -- pass --apply to write.")
        return 0
    Path(ROOT / "artifacts" / "literature" / "reviews"
         / "rev3-axis-split.json").write_text(json.dumps({
             "tool": "artifacts/literature/tools/rev3_axis_split.py",
             "files": {Path(k).name: {"before": before[k], "after": after.get(k)}
                       for k in before},
             "rows": total_rows, "rows_changed": total_changed,
             "status_map": STATUS_MAP,
             "content_preserved": True,
         }, indent=2) + "\n")
    print("wrote artifacts/literature/reviews/rev3-axis-split.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
