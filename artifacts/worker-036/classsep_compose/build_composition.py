#!/usr/bin/env python3
"""W036-CLASSSEP-COMPOSE-01 build step — mechanically compose the two staged
class-separation candidates, on the pinned base and on the live-rebased base.

Bounded, class-bound worker step (worker-036, node A1, gate G-AUDIT/G-CLASSBIND).
Primary class binding: AF-SCC-C0-VAC-GEN (class-separation / HF-02 surface).

Two composition windows, because the live canonical moved mid-lifecycle:
  base_c0 = research_map/class_separation.py at c266dbceca87 (pinned study base)
  base_c1 = research_map/class_separation.py at a8c04fc31e4a (live base observed 2026-09-12T00:52+08:00;
            adds a CF-16 metalinguistic-quotation exemption in _scan_composite)

Patches (both staged, unapplied, both authored against base_c0):
  P  prose-precision  proposed/class_separation.py  e2d24b927ee8  (worker-16, R2-2/R2-3)
  R  container-recall artifacts/worker-036/...     1bc87c9542ed  (worker-036, R5)

The rebase window applies each patch's *delta from its authoring base* to base_c1 with a
line-level 3-way merge, and separately records what a naive 2-way re-diff of the patch file
against base_c1 would do (it reverts the new base's own edit, which is a measured hazard).

Outputs (all under snapshots/):
  class_separation.composed.c0.py / c0_prose_only.py / c0_container_only.py
  class_separation.composed_inert_r5.py / composed_overfire_r5.py
  class_separation.c1_composed.py / c1_prose_only.py / c1_container_only.py
  class_separation.c1_composed_inert_r5.py / c1_composed_overfire_r5.py
  candidate_build.json

No canonical file is written.  No gate verdict, no node status.
"""
from __future__ import annotations

import datetime
import difflib
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshots"

PIN_C0 = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_C1 = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
PIN_P = "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819"
PIN_R = "1bc87c9542ed329334258ad3d87996fe87fc80a1b81c53a255130a1846d1ed49"

R5_THRESHOLD = "if len(known) >= 2:"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def changed_blocks(a: list, b: list):
    """[(i1, i2, replacement_lines)] for every non-equal opcode of a->b."""
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(i1, i2, b[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def apply_blocks(a: list, blocks: list) -> list:
    """Apply disjoint blocks (coordinates in `a`).  Order-independent by construction:
    descending application never disturbs lower coordinates."""
    out = list(a)
    for i1, i2, rep in sorted(blocks, key=lambda x: x[0], reverse=True):
        out[i1:i2] = rep
    return out


def apply_blocks_asc(a: list, blocks: list) -> list:
    out = list(a)
    drift = 0
    for i1, i2, rep in sorted(blocks, key=lambda x: x[0]):
        out[i1 + drift:i2 + drift] = rep
        drift += len(rep) - (i2 - i1)
    return out


def changed_content(a: list, b: list):
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            removed += a[i1:i2]
        if tag in ("replace", "insert"):
            added += b[j1:j2]
    return Counter(removed), Counter(added)


def rebase_blocks(old_base: list, new_base: list, blocks: list):
    """3-way rebase of delta `blocks` (authored on old_base) onto new_base.
    Returns (translated_blocks, conflicts)."""
    sm = difflib.SequenceMatcher(a=old_base, b=new_base, autojunk=False)
    pos, changed = {}, []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pos[i1 + k] = j1 + k
        else:
            changed.append((i1, i2))

    def span(i1, i2):
        return (i1, i1 + 1) if i1 == i2 else (i1, i2)

    def overlap(i1, i2):
        b1, b2 = span(i1, i2)
        for c1, c2 in changed:
            q1, q2 = span(c1, c2)
            if b1 < q2 and q1 < b2:
                return [c1, c2]
        return None

    translated, conflicts = [], []
    for i1, i2, rep in blocks:
        ov = overlap(i1, i2)
        if ov is not None:
            conflicts.append({"old_span": [i1, i2], "new_base_changed_span": ov, "reason": "delta overlaps new-base edit"})
            continue
        if i1 == i2:  # pure insertion
            if i1 > 0 and (i1 - 1) in pos and i1 in pos and pos[i1] == pos[i1 - 1] + 1:
                j = pos[i1]
            elif i1 == 0 and 0 in pos:
                j = pos[0]
            elif i1 == len(old_base) and (i1 - 1) in pos:
                j = pos[i1 - 1] + 1
            else:
                conflicts.append({"old_span": [i1, i2], "reason": "insertion anchors not uniquely mapped"})
                continue
            translated.append((j, j, rep))
        else:  # replacement / deletion
            if i1 in pos and (i2 in pos or i2 == len(old_base)):
                j1 = pos[i1]
                j2 = pos[i2] if i2 in pos else len(new_base)
                if new_base[j1:j2] == old_base[i1:i2]:
                    translated.append((j1, j2, rep))
                else:
                    conflicts.append({"old_span": [i1, i2], "reason": "replaced lines changed in new base"})
            else:
                conflicts.append({"old_span": [i1, i2], "reason": "replacement anchors not uniquely mapped"})
    return translated, conflicts


def compose_window(label: str, base_path: Path, base_pin: str, patch_specs: list, out_names: dict,
                   authoring_base_lines: list) -> dict:
    """patch_specs: [(name, patch_path, pin, authored_against_this_base: bool)]."""
    base_text = base_path.read_text()
    base_lines = base_text.splitlines(keepends=True)
    base_sha = sha256_file(base_path)
    assert base_sha == base_pin, f"{label} base pin mismatch: {base_sha}"

    patch_recs, all_blocks = {}, []
    for name, path, pin, authored_here in patch_specs:
        text = path.read_text()
        sha = sha256_file(path)
        assert sha == pin, f"{label}/{name} pin mismatch: {sha}"
        lines = text.splitlines(keepends=True)
        authored_base = base_lines if authored_here else authoring_base_lines
        delta = changed_blocks(authored_base, lines)
        if authored_here:
            translated, rebase_conflicts = list(delta), []
            naive = None
        else:
            translated, rebase_conflicts = rebase_blocks(authored_base, base_lines, delta)
            naive_blocks = changed_blocks(base_lines, lines)
            naive_text = "".join(apply_blocks(base_lines, naive_blocks))
            rem_naive, _ = changed_content(base_lines, naive_text.splitlines(keepends=True))
            naive = {
                "sha256": sha256_bytes(naive_text.encode()),
                "hunks": len(naive_blocks),
                "reverts_new_base_lines": sum(rem_naive.values()),
                "reverted_lines": [l for l in rem_naive.elements()],
                "equals_rebased": naive_text == "",
            }
        patch_recs[name] = {
            "path": str(path.relative_to(HERE)),
            "sha256": sha,
            "authoring_hunks": len(delta),
            "hunks": [{"span": [i1, i2], "replacement_lines": rep} for i1, i2, rep in translated],
            "hunk_count": len(translated),
            "added_lines": sum(len(rep) for _, _, rep in translated),
            "removed_lines": sum(i2 - i1 for i1, i2, _ in translated),
            "rebased": not authored_here,
            "rebase_conflicts": rebase_conflicts,
            "_blocks": translated,
            "_naive": naive,
        }
        all_blocks += translated

    conflicts = []
    names = list(patch_recs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for bi, pb in enumerate(patch_recs[names[i]]["_blocks"]):
                for bj, rb in enumerate(patch_recs[names[j]]["_blocks"]):
                    b1, b2 = (pb[0], pb[0] + 1) if pb[0] == pb[1] else (pb[0], pb[1])
                    q1, q2 = (rb[0], rb[0] + 1) if rb[0] == rb[1] else (rb[0], rb[1])
                    if b1 < q2 and q1 < b2:
                        conflicts.append({"a": names[i], "b": names[j], "a_span": [pb[0], pb[1]], "b_span": [rb[0], rb[1]]})

    composed_text = "".join(apply_blocks(base_lines, all_blocks))
    composed_lines = composed_text.splitlines(keepends=True)
    inv = changed_blocks(composed_lines, base_lines)
    reversed_text = "".join(apply_blocks(composed_lines, inv))

    def union_check():
        rem_pr, add_pr = changed_content(base_lines, composed_lines)
        rem_u, add_u = Counter(), Counter()
        for name in patch_recs:
            single = "".join(apply_blocks(base_lines, patch_recs[name]["_blocks"]))
            r_, a_ = changed_content(base_lines, single.splitlines(keepends=True))
            rem_u += r_
            add_u += a_
        return rem_pr, add_pr, rem_u, add_u

    rem_pr, add_pr, rem_u, add_u = union_check()
    union_ok = rem_pr == rem_u and add_pr == add_u

    sha = sha256_bytes(composed_text.encode())
    out = {
        "label": label,
        "base": {"path": str(base_path.relative_to(HERE)), "sha256": base_sha},
        "patches": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in patch_recs.items()},
        "hunk_counts": {k: v["hunk_count"] for k, v in patch_recs.items()},
        "disjoint": not conflicts,
        "conflicts": conflicts,
        "composed": {
            "sha256": sha,
            "snapshot_file": out_names["composed"],
            "snapshot_path": f"artifacts/worker-036/classsep_compose/snapshots/{out_names['composed']}",
            "line_count": len(composed_lines),
            "reverse_apply_equals_base": reversed_text == base_text,
            "ascending_apply_equals_descending": compose_asc_ok(base_lines, all_blocks, composed_text),
            "delta_equals_union_of_patch_deltas": union_ok,
            "union_detail": {
                "removed_composed": sum(rem_pr.values()), "removed_union": sum(rem_u.values()),
                "added_composed": sum(add_pr.values()), "added_union": sum(add_u.values()),
                "removed_multiset_equal": rem_pr == rem_u, "added_multiset_equal": add_pr == add_u,
            },
        },
        "naive_reapply_hazard": {k: v["_naive"] for k, v in patch_recs.items() if v["_naive"] is not None},
    }
    (SNAP / out_names["composed"]).write_text(composed_text)
    for name in patch_recs:
        single = "".join(apply_blocks(base_lines, patch_recs[name]["_blocks"]))
        (SNAP / out_names[f"{name}_only"]).write_text(single)
        out[f"{name}_only_sha256"] = sha256_bytes(single.encode())

    n_thresh = composed_text.count(R5_THRESHOLD)
    inert_text = composed_text.replace(R5_THRESHOLD, "if len(known) >= 99:")
    over_text = composed_text.replace(R5_THRESHOLD, "if len(known) >= 1:")
    (SNAP / out_names["inert"]).write_text(inert_text)
    (SNAP / out_names["overfire"]).write_text(over_text)
    out["controls"] = {
        "r5_threshold_occurrences": n_thresh,
        "inert_r5": {"snapshot": out_names["inert"], "sha256": sha256_bytes(inert_text.encode()),
                     "edited": inert_text != composed_text},
        "overfire_r5": {"snapshot": out_names["overfire"], "sha256": sha256_bytes(over_text.encode()),
                        "edited": over_text != composed_text},
    }
    out["ok"] = (not conflicts) and all(not v["rebase_conflicts"] for v in patch_recs.values()) \
        and reversed_text == base_text and out["composed"]["ascending_apply_equals_descending"] \
        and union_ok and n_thresh == 1 and inert_text != composed_text and over_text != composed_text
    return out


def compose_asc_ok(base_lines: list, blocks: list, composed_text: str) -> bool:
    return "".join(apply_blocks_asc(base_lines, blocks)) == composed_text


def main() -> int:
    c0 = SNAP / "class_separation.canonical.c266dbceca87.py"
    c1 = SNAP / "class_separation.canonical.a8c04fc31e4a.py"
    p = SNAP / "class_separation.prose.e2d24b927ee8.py"
    r = SNAP / "class_separation.container.1bc87c9542ed.py"
    c0_lines = c0.read_text().splitlines(keepends=True)

    specs_here = [("prose", p, PIN_P, True), ("container", r, PIN_R, True)]
    specs_rebased = [("prose", p, PIN_P, False), ("container", r, PIN_R, False)]

    w0 = compose_window("base_c0", c0, PIN_C0, specs_here, {
        "composed": "class_separation.composed.c0.py",
        "prose_only": "class_separation.c0_prose_only.py",
        "container_only": "class_separation.c0_container_only.py",
        "inert": "class_separation.composed_inert_r5.py",
        "overfire": "class_separation.composed_overfire_r5.py",
    }, c0_lines)
    w1 = compose_window("base_c1", c1, PIN_C1, specs_rebased, {
        "composed": "class_separation.c1_composed.py",
        "prose_only": "class_separation.c1_prose_only.py",
        "container_only": "class_separation.c1_container_only.py",
        "inert": "class_separation.c1_composed_inert_r5.py",
        "overfire": "class_separation.c1_composed_overfire_r5.py",
    }, c0_lines)

    build = {
        "task_id": "W036-CLASSSEP-COMPOSE-01",
        "actor": "worker-036",
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "A1",
        "gate": "G-AUDIT/G-CLASSBIND",
        "authority": "Worker build record only. No canonical file written, no gate verdict, no node status.",
        "inputs": {
            "canonical_c0": {"path": "research_map/class_separation.py", "sha256": PIN_C0,
                             "note": "pinned study base (bytes at lifecycle start)"},
            "canonical_c1": {"path": "research_map/class_separation.py", "sha256": PIN_C1,
                             "note": "live base observed 2026-09-12T00:52+08:00: CF-16 metalinguistic-quotation exemption added in _scan_composite"},
            "prose_patch": {"path": "proposed/class_separation.py", "sha256": PIN_P,
                            "owner": "worker-16 (CANDIDATE-PATCH.md)", "authored_against": PIN_C0},
            "container_patch": {"path": "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py",
                                "sha256": PIN_R, "owner": "worker-036 (W036-CLASSSEP-DISJ-RULE-01)",
                                "authored_against": PIN_C0},
        },
        "windows": {"base_c0": w0, "base_c1": w1},
        "primary_window": "base_c0",
        "rebase_window": "base_c1",
        # backward-compatible aliases (primary window)
        "disjoint": w0["disjoint"],
        "conflicts": w0["conflicts"],
        "hunk_counts": w0["hunk_counts"],
        "composed": w0["composed"],
        "controls": w0["controls"],
    }
    (HERE / "candidate_build.json").write_text(json.dumps(build, indent=1) + "\n")
    print(json.dumps({k: {"ok": v["ok"], "disjoint": v["disjoint"], "hunks": v["hunk_counts"],
                          "composed_sha": v["composed"]["sha256"][:12],
                          "reverse": v["composed"]["reverse_apply_equals_base"],
                          "delta_union": v["composed"]["delta_equals_union_of_patch_deltas"],
                          "rebase_conflicts": {n: len(p_["rebase_conflicts"]) for n, p_ in v["patches"].items()},
                          "naive_reverts_new_base_lines": {n: p_["reverts_new_base_lines"]
                                                           for n, p_ in v.get("naive_reapply_hazard", {}).items()}}
                      for k, v in build["windows"].items()}, indent=1))
    return 0 if all(v["ok"] for v in build["windows"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
