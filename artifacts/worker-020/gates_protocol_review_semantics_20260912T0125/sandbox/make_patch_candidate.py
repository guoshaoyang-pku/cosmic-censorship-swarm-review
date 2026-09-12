#!/usr/bin/env python3
"""Generate the unapplied drop-in patch candidate for B-N0-R2-2.

Writes (sandbox only, never numerics/gates.py):
  sandbox/gates_protocol_review_v2.py   standalone recommended semantics
  sandbox/gates_patched.py              pinned gates.py with _protocol_review replaced
  sandbox/gates_py_protocol_review.patch  unified diff, unapplied
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent

V2_BLOCK = '''PROTOCOL_DOCUMENT_TARGETS = (
    "numerics/CONVERGENCE_PROTOCOL.md",
    "G-NUM-protocol",
)


def _targets_protocol_document(target: str) -> bool:
    """Protocol-document target matcher (path, G-NUM-protocol, with #/@ pins).

    Symmetric with the citation parser: it accepts every naming convention that
    ``_review_cited_hashes`` supports.  N0-node verdicts are deliberately not
    matched here; an N0 node review is scored by the N0 node, not by the
    protocol document.
    """
    t = target.strip()
    for cand in PROTOCOL_DOCUMENT_TARGETS:
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def _protocol_review(events: list[dict], protocol_sha: str | None = None) -> dict:
    """Independent review state of the protocol document (recommended v2).

    Changes vs rev ``fcd1d70991b6``:
      (1) SCOPE: only protocol-document-targeted verdicts are scored here.
          ``N0``-targeted verdicts are returned separately as
          ``node_scope_reviews`` and no longer contest the protocol document.
      (2) SUPERSESSION: at one protocol hash the operative verdict of each
          reviewer is the latest by ``created_at``; an earlier verdict by the
          same reviewer is reported under ``superseded_reviews`` and does not
          count.  An exact ``created_at`` tie is fail-closed: a dissent
          supersedes an accept, never the reverse.
      (3) A verdict binds only if it cites a hash prefix-matching the protocol
          currently on disk (unchanged from rev fcd1d70991b6).

    Accepts and dissents are deduplicated by event_id across the accepted
    stream and the outbox/inbox copies of the same event.
    """
    rows: list[dict] = []
    advisory: list[dict] = []
    node_scope: list[dict] = []
    seen: set[str] = set()
    target = (protocol_sha or "").lower()
    for e in events:
        if e.get("event_type") != "review":
            continue
        verdict = e.get("verdict")
        if verdict not in ("accept", "revise", "reject"):
            continue
        tgt = str(e.get("target_id", ""))
        is_doc = _targets_protocol_document(tgt)
        is_node = _targets_protocol(tgt)
        if not (is_doc or is_node):
            continue
        if e.get("reviewer") == PROTOCOL_REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        cited = _review_cited_hashes(e)
        binds = bool(target) and any(
            target.startswith(c) or c.startswith(target) for c in cited
        )
        row = {"event_id": eid, "reviewer": e.get("reviewer"), "verdict": verdict,
               "target_id": tgt, "created_at": e.get("created_at"), "cited": cited}
        if not binds:
            advisory.append(row)
            continue
        if not is_doc:
            node_scope.append(row)
            continue
        rows.append(row)

    # (2) latest verdict per reviewer at this hash; fail-closed on exact ties.
    latest: dict[str, dict] = {}
    for row in rows:
        rev = str(row.get("reviewer"))
        cur = latest.get(rev)
        if cur is None:
            latest[rev] = row
            continue
        k_new = (str(row.get("created_at") or "")[:19], row["event_id"])
        k_cur = (str(cur.get("created_at") or "")[:19], cur["event_id"])
        if k_new > k_cur:
            latest[rev] = row
        elif k_new == k_cur and row["verdict"] != "accept" and cur["verdict"] == "accept":
            latest[rev] = row
    keep = {id(r) for r in latest.values()}
    superseded = [r for r in rows if id(r) not in keep]
    rows = [r for r in rows if id(r) in keep]

    accepts = [r["event_id"] for r in rows if r["verdict"] == "accept"]
    dissents = [{"event_id": r["event_id"], "verdict": r["verdict"],
                 "reviewer": r["reviewer"]} for r in rows if r["verdict"] != "accept"]
    return {
        "reviewed": bool(accepts),
        "accepting_reviews": accepts,
        "dissenting_reviews": dissents,
        "contest": bool(dissents),
        "advisory_reviews_at_other_hashes": [
            {"event_id": r["event_id"], "verdict": r["verdict"], "cited": r["cited"],
             "reviewer": r["reviewer"]} for r in advisory
        ],
        "superseded_reviews": [
            {"event_id": r["event_id"], "verdict": r["verdict"], "reviewer": r["reviewer"]}
            for r in superseded
        ],
        "node_scope_reviews": [
            {"event_id": r["event_id"], "verdict": r["verdict"], "reviewer": r["reviewer"]}
            for r in node_scope
        ],
        "protocol_sha256_measured": protocol_sha,
        "reviewed_protocol_sha256": protocol_sha if accepts else None,
        "semantics": "document-scope + per-reviewer supersession (B-N0-R2-2 candidate)",
    }
'''


def main() -> int:
    manifest = json.loads((TASK / "pinned" / "manifest.json").read_text())
    src = (TASK / "pinned" / manifest["files"]["numerics/gates.py"]["copy"]).read_text()
    start = src.index("def _protocol_review(")
    end = src.index("\n\ndef evaluate(")
    patched = src[:start] + V2_BLOCK + src[end:]

    (TASK / "sandbox" / "gates_protocol_review_v2.py").write_text(
        '"""Recommended drop-in semantics for numerics/gates.py::_protocol_review.\n\n'
        "Standalone copy of the patched function; see gates_py_protocol_review.patch.\n"
        '"""\n\n' + V2_BLOCK
    )
    (TASK / "sandbox" / "gates_patched.py").write_text(patched)
    diff = difflib.unified_diff(
        src.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile="a/numerics/gates.py", tofile="b/numerics/gates.py",
    )
    (TASK / "sandbox" / "gates_py_protocol_review.patch").write_text("".join(diff))
    print("patch lines:", sum(1 for _ in (TASK / "sandbox" / "gates_py_protocol_review.patch").open()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
