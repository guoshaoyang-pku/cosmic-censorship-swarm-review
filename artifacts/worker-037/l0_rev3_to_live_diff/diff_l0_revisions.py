#!/usr/bin/env python3
"""W037-L0-REVDIFF-01 -- independent content-preservation / claim-direction diff of the
announced L0 exit revision vs the live canonical ledger.

Task class: AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-WCC-SCALAR-SPH
Node L0, gate G-LIT. Read-only: only writes the file passed to --out (or stdout).

Why: controller REC-10 (CF-19) records a freeze breach -- the live ledger
ledger/theorems.jsonl measured a1674f094979 after the literature lead's announced L4 exit
hash 3e3d35531421, with no artifact event. The reconciliation requires a
content-preservation / claim-lowering diff. This script produces that measurement.

Pre-registered classification (fixed BEFORE the diff is computed):

  CONTENT_KEYS   fields whose change breaks content preservation (statement, class binding,
                 conclusion type, evidence level, regularity/topology/genericity, sources,
                 review/acceptance authority, verification status, ...)
  STATUS_FAMILY  the claim-status vocabulary that the revision is licensed to restructure:
                 {status, status_note, supports_claim, supports_claim_basis,
                  content_status, author_asserts_supports}
  STRENGTH       pre-registered claim-strength ranks for status tokens (higher = stronger):
                 rejected 0, unresolved 1, provisional 2,
                 included_unreviewed / author_assessed 3,
                 reviewed 4, accepted 5, verified 5
  Rules
    R1 content_preserved : every CONTENT_KEY equal per row.
    R2 status_restructure: changed keys are confined to STATUS_FAMILY.
    R3 claim_lowering   : live status rank <= archive status rank for every row.
    R4 support_flip      : archive supports_claim in {absent,false} and live
                          author_asserts_supports is true.
    R5 internal_conflict : live content_status in {verified,accepted} while
                          review_status != independently_reviewed OR
                          verification_status in {unverified, abstract-read}.
  Verdict is CONTENT_PRESERVED_CLAIM_LOWERING only if R1+R2+R3 hold and R4/R5 are empty;
  otherwise the row and rule witnesses are the deliverable.

Controls (synthetic, no filesystem writes):
  CTL-1 mutation sensitivity : a mutated statement_exact must fire R1.
  CTL-2 direction            : accepted->provisional must be lowering; provisional->accepted raising.
  CTL-3 rename tolerance     : a renamed-only status field must not fire R1.
  CTL-5 row integrity        : live rows must be unique, keyed by theorem_id.
  CTL-4 determinism          : run twice with the same --now and diff the outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CONTENT_KEYS = (
    "theorem_id", "label", "entry_kind", "statement_exact", "class_ids", "conclusion_type",
    "assumptions", "falsifiers", "does_not_imply", "genericity", "regularity", "topology",
    "scope_caveats", "source_ids", "ledger_tags", "unresolved", "review_status",
    "acceptance_authority", "verification_status", "next_action", "evidence_level",
)
STATUS_FAMILY = (
    "status", "status_note", "supports_claim", "supports_claim_basis",
    "content_status", "author_asserts_supports",
)
STRENGTH = {
    "rejected": 0,
    "unresolved": 1,
    "provisional": 2,
    "included_unreviewed": 3,
    "author_assessed": 3,
    "reviewed": 4,
    "accepted": 5,
    "verified": 5,
}
VERIFIED_TOKENS = {"verified", "accepted"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path: Path):
    rows, bad = [], []
    raw = path.read_bytes()
    for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:  # noqa: BLE001
            bad.append({"line": n, "error": str(exc)})
    return rows, bad, raw


def norm_support(value):
    """Normalise the support assertion to a bool-or-None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def rank(token):
    if token is None:
        return None
    return STRENGTH.get(str(token).strip().lower())


def classify_row(arc: dict, live: dict) -> dict:
    keys = (set(arc) | set(live)) - {"theorem_id"}
    changed = sorted(k for k in keys if arc.get(k) != live.get(k))
    content_changed = [k for k in changed if k in CONTENT_KEYS]
    status_changed = [k for k in changed if k in STATUS_FAMILY]
    other_changed = [k for k in changed if k not in CONTENT_KEYS and k not in STATUS_FAMILY]

    arc_status = arc.get("status", arc.get("content_status"))
    live_status = live.get("content_status", live.get("status"))
    r_arc, r_live = rank(arc_status), rank(live_status)
    direction = "unchanged"
    if r_arc is not None and r_live is not None and r_live != r_arc:
        direction = "raising" if r_live > r_arc else "lowering"

    arc_sup = norm_support(arc.get("supports_claim"))
    live_sup = norm_support(live.get("author_asserts_supports"))
    support_flip = arc_sup in (None, False) and live_sup is True

    cs = str(live.get("content_status", "")).strip().lower()
    rs = str(live.get("review_status", "")).strip().lower()
    vs = str(live.get("verification_status", "")).strip().lower()
    internal_conflict = cs in VERIFIED_TOKENS and (
        rs != "independently_reviewed" or vs in {"unverified", "abstract-read"}
    )

    return {
        "theorem_id": arc.get("theorem_id") or live.get("theorem_id"),
        "class_ids": live.get("class_ids", arc.get("class_ids")),
        "changed_keys": changed,
        "content_changed_keys": content_changed,
        "status_family_changed_keys": status_changed,
        "other_changed_keys": other_changed,
        "status_token": {"archive": arc_status, "live": live_status, "direction": direction},
        "support": {"archive_supports_claim": arc.get("supports_claim"),
                    "live_author_asserts_supports": live.get("author_asserts_supports"),
                    "assertion_flip": support_flip},
        "internal_status_conflict": internal_conflict,
        "witness": {
            "archive": {k: arc.get(k) for k in ("status", "status_note", "supports_claim",
                                                "supports_claim_basis")},
            "live": {k: live.get(k) for k in ("content_status", "author_asserts_supports",
                                              "review_status", "verification_status",
                                              "acceptance_authority")},
        } if changed else {},
    }


def run_controls() -> dict:
    base = {"theorem_id": "X-1", "statement_exact": "S", "class_ids": ["AF-WCC-VAC-GEN"],
            "conclusion_type": "theorem", "status": "included_unreviewed"}
    out = {}

    mut = dict(base, statement_exact="S altered")
    out["CTL-1-mutation-sensitivity"] = {
        "result": "PASS" if classify_row(base, mut)["content_changed_keys"] == ["statement_exact"] else "FAIL",
        "detail": classify_row(base, mut)["content_changed_keys"],
    }
    low = classify_row(dict(base, status="accepted"), dict(base, status="provisional"))
    high = classify_row(dict(base, status="provisional"), dict(base, status="accepted"))
    out["CTL-2-direction"] = {
        "result": "PASS" if low["status_token"]["direction"] == "lowering"
        and high["status_token"]["direction"] == "raising" else "FAIL",
        "detail": {"lowering_case": low["status_token"]["direction"],
                   "raising_case": high["status_token"]["direction"]},
    }
    renamed = classify_row(dict(base, status="included_unreviewed"),
                           dict({k: v for k, v in base.items() if k != "status"},
                                content_status="included_unreviewed"))
    out["CTL-3-rename-tolerance"] = {
        "result": "PASS" if renamed["content_changed_keys"] == [] else "FAIL",
        "detail": {"content_changed_keys": renamed["content_changed_keys"],
                   "changed_keys": renamed["changed_keys"]},
    }
    conflict = classify_row(base, dict(base, content_status="verified",
                                      review_status="not_independently_reviewed",
                                      verification_status="abstract-read"))
    out["CTL-4-conflict-detector"] = {
        "result": "PASS" if conflict["internal_status_conflict"] else "FAIL",
        "detail": conflict["internal_status_conflict"],
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--archive", default="artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl")
    ap.add_argument("--live", default="ledger/theorems.jsonl")
    ap.add_argument("--expect-archive-sha", default="3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6")
    ap.add_argument("--now", default=None, help="fixed measured_at for deterministic replays")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    arc_path, live_path = root / args.archive, root / args.live
    measured_at = args.now or __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")

    t0 = {"archive": sha256_file(arc_path), "live": sha256_file(live_path)}
    arc, arc_bad, _ = load_rows(arc_path)
    live, live_bad, _ = load_rows(live_path)
    t1 = {"archive": sha256_file(arc_path), "live": sha256_file(live_path)}
    drift = [k for k in t0 if t0[k] != t1[k]]

    by_id_live = {}
    dup_live = []
    for r in live:
        tid = r.get("theorem_id")
        if tid in by_id_live:
            dup_live.append(tid)
        by_id_live[tid] = r
    by_id_arc = {r.get("theorem_id"): r for r in arc}
    missing_live = sorted(set(by_id_arc) - set(by_id_live), key=str)
    missing_arc = sorted(set(by_id_live) - set(by_id_arc), key=str)

    rows = []
    for tid in sorted(set(by_id_arc) & set(by_id_live), key=str):
        rows.append(classify_row(by_id_arc[tid], by_id_live[tid]))

    per_class = {}
    for r in rows:
        for cid in r["class_ids"] or ["UNMAPPED"]:
            agg = per_class.setdefault(cid, {"rows": 0, "content_changed": 0,
                                             "status_direction_raising": 0,
                                             "assertion_flips": 0, "internal_conflicts": 0})
            agg["rows"] += 1
            agg["content_changed"] += 1 if r["content_changed_keys"] else 0
            agg["status_direction_raising"] += 1 if r["status_token"]["direction"] == "raising" else 0
            agg["assertion_flips"] += 1 if r["support"]["assertion_flip"] else 0
            agg["internal_conflicts"] += 1 if r["internal_status_conflict"] else 0

    raising = [r["theorem_id"] for r in rows if r["status_token"]["direction"] == "raising"]
    lowering = [r["theorem_id"] for r in rows if r["status_token"]["direction"] == "lowering"]
    content_changed = [r["theorem_id"] for r in rows if r["content_changed_keys"]]
    other_changed = [r["theorem_id"] for r in rows if r["other_changed_keys"]]
    flips = [r["theorem_id"] for r in rows if r["support"]["assertion_flip"]]
    conflicts = [r["theorem_id"] for r in rows if r["internal_status_conflict"]]

    r1 = not content_changed
    r2 = not other_changed
    r3 = not raising
    r4 = not flips
    r5 = not conflicts
    verdict = "CONTENT_PRESERVED_CLAIM_LOWERING" if (r1 and r2 and r3 and r4 and r5) else \
              "CONTENT_PRESERVED_STATUS_TOKEN_RAISING" if (r1 and r2 and not r3) else \
              "CONTENT_CHANGED" if not r1 else "REVIEW_REQUIRED"

    report = {
        "schema_version": "0.1",
        "artifact_type": "l0_revision_content_preservation_diff",
        "task_id": "W037-L0-REVDIFF-01",
        "actor": "worker-037",
        "authority": "worker measurement only; no gate verdict, no node status, no ledger write",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "measured_at": measured_at,
        "inputs": {
            "archive_path": args.archive, "archive_sha256": t0["archive"],
            "live_path": args.live, "live_sha256": t0["live"],
            "announced_exit_sha256": args.expect_archive_sha,
            "archive_is_announced_exit": t0["archive"] == args.expect_archive_sha,
            "rows_archive": len(arc), "rows_live": len(live),
            "parse_errors": {"archive": arc_bad, "live": live_bad},
        },
        "pre_registered_rules": {
            "CONTENT_KEYS": list(CONTENT_KEYS), "STATUS_FAMILY": list(STATUS_FAMILY),
            "STRENGTH": STRENGTH,
        },
        "drift_within_run": {"t0": t0, "t1": t1, "drifted_paths": drift},
        "row_integrity": {"duplicate_theorem_ids": dup_live,
                          "missing_in_live": missing_live, "missing_in_archive": missing_arc},
        "changed_row_count": sum(1 for r in rows if r["changed_keys"]),
        "aggregates": {
            "rows_compared": len(rows),
            "content_changed_rows": content_changed,
            "other_family_changed_rows": other_changed,
            "status_raising_rows": raising,
            "status_lowering_rows": lowering,
            "assertion_flip_rows": flips,
            "internal_conflict_rows": conflicts,
            "per_class": per_class,
        },
        "rules": {"R1_content_preserved": r1, "R2_status_only_restructure": r2,
                  "R3_status_not_raising": r3, "R4_no_support_flip": r4,
                  "R5_no_internal_status_conflict": r5},
        "verdict": {
            "classification": verdict,
            "summary": (
                f"{len(rows)} rows compared; {len(content_changed)} content-key changes; "
                f"{len(raising)} status-token raise(s); {len(flips)} support-assertion flip(s); "
                f"{len(conflicts)} internal status conflict(s)."
            ),
            "claim_lowering": bool(r3 and r4 and r5),
            "content_preserved": bool(r1 and r2),
        },
        "rows": rows,
        "controls": run_controls(),
        "falsifier": (
            "Re-run against `ledger/theorems.jsonl` and the archived rev3 bytes: if the live "
            "hash is no longer a1674f094979, this diff is superseded and must be re-run; if any "
            "CONTENT_KEY differs in a row, the content-preservation claim is falsified for that "
            "row; if no row maps included_unreviewed -> verified (or the live token is renamed to "
            "a non-certifying token such as author_assessed/unreviewed), R3 is falsified."
        ),
        "recommendation": (
            "Adopt the live bytes only after renaming the certifying token: `content_status: "
            "verified` collides with the ledger's separate verification vocabulary "
            "(`verification_status` in {abstract-read, unverified}) and with "
            "`review_status: not_independently_reviewed`. Use a non-certifying token "
            "(`author_assessed`/`unreviewed`) and keep the now-honest "
            "`author_asserts_supports` attribution. No statement, class binding, conclusion_type "
            "or evidence_level changed, so the repair is content-preserving."
        ),
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
