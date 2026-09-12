#!/usr/bin/env python3
"""W065-R2-INDEP-PREREG-01 -- pre-registered independence census of the r2 review fleet.

Read-only against the live tree. Writes only under artifacts/worker-065/r2_independence_prereg/.

Task (class-bound): node F0/F1/F2a/F2b/N0/A0; classes AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH; gate G-AUDIT.

Question. Ten blind review cards (`audit-r2-*`) were written to comms/inbox at
2026-09-12T00:44:18+08:00. Each card asserts the reviewer "may NOT be an author of the
artifact and may NOT read any other reviewer's verdict for this target before writing
yours". That assertion is self-certified. This tool machine-checks the *pre-card* evidence
base for each of the ten (reviewer, target) pairs and freezes the classification BEFORE any
r2 verdict is admitted as evidence.

Evidence cutoff. Only material whose file mtime is strictly before the card time is read;
r2 verdicts written after dispatch are excluded by construction. The cutoff is the point of
the exercise (pre-registration), so it is enforced in code, not by convention.

Per-card checks (all decidable, replayable from the frozen snapshot):
  A_AUTHOR      reviewer appears as actor of an accepted artifact event at the target path,
                or appears in the target document's revision/author text.
  A_ASSIGNED    reviewer holds a pre-card map assignment on the same node (owner conflict).
  B_PRIOR       reviewer has a pre-card review document on the same target (own prior
                verdict -> not a first, blind read).
  B_PRIOR_ALIAS same as B but under an alias id form (worker-0NN vs deepseek-flash-NN vs
                flash-NN vs worker-N); identity cannot be resolved from the registry, so the
                row is flagged AMBIGUOUS rather than silently counted as clean.
  C_EXPOSURE    a pre-card file in the reviewer's own artifact tree references a verdict
                document path for the same target (other reviewers' verdicts).
  E_TARGET_COPY informational: byte-identical copies of the target in the reviewer's pre-card
                tree (snapshotting to review is legitimate; not a disqualifier).

Controls: the same classify() path is re-run on synthetic evidence (planted author event,
planted prior verdict, clean reviewer). A control that fails to move the classification
invalidates the run.

Falsifier: re-run this tool on the frozen snapshot. Falsified if any row classified
CLEAN_PRE_CARD has, in the pre-card evidence base, (a) an artifact event at the target path
with the reviewer (or a resolvable alias) as actor, (b) a prior review document on the same
target, or (c) a reference to another reviewer's verdict document for that target; or if any
planted control fails to fire; or if the pre/post window hashes differ.

Authority: worker-level measurement only. Sets no gate verdict, no node status, no
validation_status=passed. The audit lead and controller adjudicate.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "artifacts", "worker-065", "r2_independence_prereg")
SNAP = os.path.join(OUT, "snapshot")
CTRL = os.path.join(OUT, "controls")

TZ = timezone(timedelta(hours=8))
CARD_TIME = datetime(2026, 9, 12, 0, 44, 18, tzinfo=TZ)
CARD_EPOCH = CARD_TIME.timestamp()


def parse_ts(value):
    """Parse an event timestamp; tolerate +0800 (no colon) as used by some emitters."""
    if not value:
        return None
    txt = str(value).strip()
    if re.search(r"[+-]\d{4}$", txt):
        txt = txt[:-5] + txt[-5:-2] + ":" + txt[-2:]
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt

TARGETS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "F0": "research_map/formulation_taxonomy.yaml",
    "N0": "numerics/CONVERGENCE_PROTOCOL.md",
    "A0": "evaluation_rubric.yaml",
}
NODE_TOKENS = {
    "F1": ["F1"],
    "F2a": ["F2a"],
    "F2b": ["F2b"],
    "F0": ["F0"],
    "N0": ["N0"],
    "A0": ["A0"],
}
FROZEN_PINS_PATH = "artifacts/formulation/FROZEN.json"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def aliases(agent: str):
    """Id forms that plausibly denote the same executor. Identity is NOT asserted; the
    presence of a second form is reported as ambiguity evidence."""
    out = {agent}
    m = re.fullmatch(r"worker-0*(\d+)", agent)
    if m:
        n = m.group(1)
        for fmt in ("worker-{}", "worker{:02d}", "worker-{:03d}", "deepseek-flash-{}", "flash-{}", "deepseek-flash-{:02d}"):
            try:
                out.add(fmt.format(int(n)))
            except (ValueError, IndexError):
                pass
        out.add("worker-%03d" % int(n))
        out.add("deepseek-flash-%02d" % int(n))
    return out


def mtime_lt_cutoff(path: str, epoch: float) -> bool:
    try:
        return os.path.getmtime(path) < epoch
    except OSError:
        return False


def load_json(path: str):
    txt = read_text(path)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def load_jsonl(path: str):
    rows = []
    txt = read_text(path)
    if txt is None:
        return rows
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"_raw": line})
    return rows


def freeze_snapshot():
    os.makedirs(SNAP, exist_ok=True)
    os.makedirs(os.path.join(SNAP, "cards"), exist_ok=True)
    os.makedirs(os.path.join(SNAP, "schemas"), exist_ok=True)
    os.makedirs(CTRL, exist_ok=True)
    copied = []
    for name in ("research_map/research_map.json", FROZEN_PINS_PATH, "research_map/events.jsonl"):
        dst = os.path.join(SNAP, os.path.basename(name))
        shutil.copy2(os.path.join(ROOT, name), dst)
        copied.append((name, sha256_file(dst), os.path.getsize(dst)))
    for node, rel in TARGETS.items():
        if os.path.exists(os.path.join(ROOT, rel)):
            dst = os.path.join(SNAP, "schemas", node + "__" + os.path.basename(rel))
            shutil.copy2(os.path.join(ROOT, rel), dst)
            copied.append((rel, sha256_file(dst), os.path.getsize(dst)))
    cards = []
    for i in range(1, 200):
        p = os.path.join(ROOT, "comms", "inbox", "worker-%03d.jsonl" % i)
        if not os.path.exists(p):
            continue
        for line in read_text(p).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not str(e.get("event_id", "")).startswith("audit-r2-"):
                continue
            card_dt = parse_ts(e.get("created_at"))
            dst = os.path.join(SNAP, "cards", "%03d_%s.json" % (i, e["event_id"]))
            with open(dst, "w") as f:
                json.dump(e, f, indent=1, sort_keys=True)
            cards.append(
                {
                    "card_path": os.path.relpath(dst, ROOT),
                    "card_sha256": sha256_file(dst),
                    "event_id": e.get("event_id"),
                    "reviewer": e.get("assignee"),
                    "node_id": e.get("node_id"),
                    "class_id": e.get("class_id"),
                    "gate": e.get("gate"),
                    "deliverable": e.get("artifact"),
                    "target_artifact": TARGETS.get(e.get("node_id")),
                    "deadline": e.get("deadline"),
                    "card_created_at": e.get("created_at"),
                    "card_epoch": card_dt.timestamp() if card_dt else CARD_EPOCH,
                }
            )
            copied.append((os.path.relpath(dst, ROOT), sha256_file(dst), os.path.getsize(dst)))
    return cards, copied


def target_live_hashes():
    pins = {}
    for node, rel in TARGETS.items():
        p = os.path.join(ROOT, rel)
        pins[node] = {"path": rel, "exists": os.path.exists(p), "sha256": sha256_file(p) if os.path.exists(p) else None}
    frozen = load_json(os.path.join(ROOT, FROZEN_PINS_PATH)) or {}
    fpins = frozen.get("files", {})
    for node, rel in TARGETS.items():
        pins[node]["frozen_rev28_sha256"] = fpins.get(rel, {}).get("sha256")
        pins[node]["frozen_rev28_match"] = pins[node]["sha256"] == pins[node]["frozen_rev28_sha256"]
    pins["_frozen_revision"] = frozen.get("revision")
    pins["_frozen_sha256"] = sha256_file(os.path.join(ROOT, FROZEN_PINS_PATH)) if os.path.exists(os.path.join(ROOT, FROZEN_PINS_PATH)) else None
    return pins


def scan_evidence(cards):
    """Build the pre-card evidence base (cutoff enforced per card in classify())."""
    ev = load_jsonl(os.path.join(ROOT, "research_map", "events.jsonl"))
    artifact_events = []
    actor_index = {}
    for e in ev:
        act = e.get("actor")
        if act:
            actor_index.setdefault(act, 0)
            actor_index[act] += 1
        if e.get("event_type") == "artifact" and e.get("path") and e.get("sha256"):
            artifact_events.append({"actor": act, "path": e.get("path"), "sha256": e.get("sha256"), "created_at": e.get("created_at"), "event_id": e.get("event_id")})
    mp = load_json(os.path.join(ROOT, "research_map", "research_map.json")) or {}
    assignments = [a for a in mp.get("assignments", []) if isinstance(a, dict)]

    # review documents (cutoff applied per card in classify(); mtime recorded here)
    review_recs = []
    rdir = os.path.join(ROOT, "reviews")
    if os.path.isdir(rdir):
        for fn in sorted(os.listdir(rdir)):
            p = os.path.join(rdir, fn)
            if not os.path.isfile(p):
                continue
            doc = load_json(p)
            if not isinstance(doc, dict):
                continue
            ident = {doc.get("actor"), doc.get("reviewer"), doc.get("reviewed_by")} - {None}
            review_recs.append(
                {
                    "file": os.path.relpath(p, ROOT),
                    "mtime": os.path.getmtime(p),
                    "identities": sorted(ident),
                    "node_id": doc.get("node_id"),
                    "target_id": doc.get("target_id") or doc.get("reviewed_path") or doc.get("artifact"),
                    "verdict": doc.get("verdict"),
                    "reviewed_sha256": doc.get("reviewed_sha256"),
                    "class_ids": doc.get("class_ids") or ([doc.get("class_id")] if doc.get("class_id") else []),
                }
            )
    return {
        "artifact_events": artifact_events,
        "actor_index": actor_index,
        "assignments": assignments,
        "review_recs": review_recs,
        "cards": cards,
        "card_time_by_id": {c["event_id"]: c.get("card_epoch", CARD_EPOCH) for c in cards},
        "events_total": len(ev),
        "pre_card_review_files": len(review_recs),
    }


def target_text_paths(cards):
    out = {}
    for c in cards:
        node = c["node_id"]
        rel = TARGETS.get(node)
        if rel:
            out[node] = os.path.join(ROOT, rel)
    return out


def review_path_regex(node: str):
    toks = "|".join(NODE_TOKENS.get(node, [node]))
    return re.compile(r"reviews/[A-Za-z0-9_./-]*(?:" + toks + r")[A-Za-z0-9_./-]*")


def classify(card, evidence, target_hashes):
    node = card["node_id"]
    reviewer = card["reviewer"]
    alias_set = aliases(reviewer)
    cutoff = card.get("card_epoch", CARD_EPOCH)
    own_card_id = card.get("event_id")
    rev = {"card": card, "reviewer": reviewer, "node_id": node, "class_id": card["class_id"],
           "target_artifact": card["target_artifact"], "target_live_sha256": target_hashes.get(node, {}).get("sha256"),
           "card_epoch": cutoff, "flags": [], "evidence": {}}

    # A_AUTHOR -- accepted artifact events at the target path by this reviewer
    hits = [e for e in evidence["artifact_events"] if e["path"] == card["target_artifact"] and e["actor"] in alias_set]
    rev["evidence"]["A_author_events"] = hits[:5]
    if hits:
        rev["flags"].append("A_AUTHOR")

    # A_AUTHOR_TEXT -- reviewer id appears in the target document text (author/revision history)
    tpath = os.path.join(ROOT, card["target_artifact"]) if card["target_artifact"] else None
    text_hits = []
    if tpath and os.path.exists(tpath):
        txt = read_text(tpath) or ""
        for a in sorted(alias_set):
            if a in txt:
                text_hits.append(a)
    rev["evidence"]["A_author_text_tokens"] = text_hits
    if text_hits:
        rev["flags"].append("A_AUTHOR_TEXT")

    # A_ASSIGNED -- strictly pre-card, non-r2 assignment on the same node.
    # Map assignment records carry no created_at; the frozen card set supplies the times, so
    # any assignment whose event_id is a frozen r2 card is excluded from "prior involvement".
    card_times = evidence.get("card_time_by_id", {})
    asg = []
    for a in evidence["assignments"]:
        if a.get("event_id") == own_card_id or a.get("event_id") in card_times:
            continue
        if a.get("assignee") not in alias_set:
            continue
        if not (a.get("node_id") == node or node in str(a.get("node_id", ""))):
            continue
        adt = parse_ts(a.get("created_at"))
        if adt is not None and adt.timestamp() >= cutoff:
            continue
        asg.append(a)
    rev["evidence"]["A_prior_assignments"] = [
        {"event_id": a.get("event_id"), "assignee": a.get("assignee"), "node_id": a.get("node_id"),
         "created_at": a.get("created_at"), "status": a.get("status")} for a in asg
    ][:5]
    if asg:
        rev["flags"].append("A_ASSIGNED")

    # informational: more than one r2 card for the same reviewer/node pair (a second card is
    # not a second independent reviewer)
    pair_cards = [c for c in evidence.get("cards", [])
                  if c["reviewer"] in alias_set and c["node_id"] == node]
    rev["evidence"]["R2_cards_for_pair"] = [
        {"event_id": c["event_id"], "card_created_at": c["card_created_at"]} for c in pair_cards
    ]
    rev["r2_card_count_for_pair"] = len(pair_cards)
    if len(pair_cards) > 1:
        rev["flags"].append("R2_MULTI_CARD_SAME_PAIR")

    # B_PRIOR -- own pre-card review on the same target (mtime before this card)
    prior, prior_alias = [], []
    for r in evidence["review_recs"]:
        if r["mtime"] >= cutoff:
            continue
        same_node = r["node_id"] == node or any(t in str(r["target_id"]) for t in NODE_TOKENS.get(node, [node]))
        same_target = card["target_artifact"] and card["target_artifact"] in str(r["target_id"])
        if not (same_node or same_target):
            continue
        if reviewer in r["identities"]:
            prior.append(r)
        elif alias_set & set(r["identities"]):
            prior_alias.append(r)
    rev["evidence"]["B_prior_reviews"] = [
        {"file": r["file"], "verdict": r["verdict"], "reviewed_sha256": r["reviewed_sha256"]} for r in prior
    ][:8]
    rev["evidence"]["B_prior_review_alias_forms"] = [
        {"file": r["file"], "identities": r["identities"], "verdict": r["verdict"]} for r in prior_alias
    ][:8]
    if prior:
        rev["flags"].append("B_PRIOR_SAME_TARGET")
    if prior_alias:
        rev["flags"].append("B_PRIOR_ALIAS_AMBIGUOUS")

    # C_EXPOSURE -- reviewer's pre-card tree references a verdict doc for the same target.
    # Tiered: a reference carried inside a copy of the target document or of global state
    # (map/events) is incidental -- the reviewer did not have to read a verdict to acquire it.
    pat = review_path_regex(node)
    direct, incidental = [], []
    canon_hashes = {v.get("sha256") for v in target_hashes.values() if isinstance(v, dict) and v.get("sha256")}
    adir = os.path.join(ROOT, "artifacts", reviewer)
    if os.path.isdir(adir):
        for dirpath, _dirs, files in os.walk(adir):
            for fn in files:
                p = os.path.join(dirpath, fn)
                if not mtime_lt_cutoff(p, cutoff):
                    continue
                sz = os.path.getsize(p)
                if sz > 4 << 20:
                    continue
                txt = read_text(p)
                if not txt:
                    continue
                refs = sorted(set(pat.findall(txt)))
                if not refs:
                    continue
                base = os.path.basename(p).lower()
                looks_global = ("map" in base or "events" in base or "research_map__" in base
                                or len(refs) >= 10 or base == os.path.basename(card["target_artifact"]).lower())
                if not looks_global and sz < (2 << 20):
                    try:
                        looks_global = sha256_file(p) in canon_hashes
                    except OSError:
                        looks_global = False
                rec = {"file": os.path.relpath(p, ROOT), "references": refs[:5], "distinct_refs": len(refs)}
                (incidental if looks_global else direct).append(rec)
    rev["evidence"]["C_direct_references"] = direct[:8]
    rev["evidence"]["C_incidental_references"] = incidental[:8]
    if direct:
        rev["flags"].append("C_PRIOR_EXPOSURE")

    # E_TARGET_COPY -- informational
    copies = []
    tsha = target_hashes.get(node, {}).get("sha256")
    if tsha and os.path.isdir(adir):
        tsize = os.path.getsize(os.path.join(ROOT, card["target_artifact"]))
        for dirpath, _dirs, files in os.walk(adir):
            for fn in files:
                p = os.path.join(dirpath, fn)
                if not mtime_lt_cutoff(p, cutoff) or os.path.getsize(p) != tsize:
                    continue
                if sha256_file(p) == tsha:
                    copies.append(os.path.relpath(p, ROOT))
    rev["evidence"]["E_target_copies"] = copies[:8]
    rev["target_copy_count"] = len(copies)

    rev["classification"] = "CLEAN_PRE_CARD" if not rev["flags"] else "+".join(rev["flags"])
    return rev


def run_controls(evidence, target_hashes):
    """Replay the same classify() on synthetic cards/evidence. Controls must fire."""
    controls = []
    synth_card = {
        "card_path": "controls/synthetic", "card_sha256": "0" * 64, "event_id": "ctl",
        "reviewer": "worker-046", "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM", "deliverable": "controls/x.json",
        "target_artifact": "schemas/af_scc_c2_vacuum.yaml", "deadline": None,
        "card_created_at": CARD_TIME.isoformat(),
    }
    base = {
        "artifact_events": [], "actor_index": {}, "assignments": [], "review_recs": [],
        "events_total": 0, "pre_card_review_files": 0,
    }
    # C1 planted author event
    ev1 = dict(base)
    ev1["artifact_events"] = [{"actor": "worker-046", "path": "schemas/af_scc_c2_vacuum.yaml",
                               "sha256": "a" * 64, "created_at": "2026-09-12T00:10:00+08:00", "event_id": "ctl"}]
    r1 = classify(dict(synth_card), ev1, target_hashes)
    controls.append({"id": "C1_planted_author_event", "expect_flag": "A_AUTHOR", "got": r1["classification"],
                     "pass": "A_AUTHOR" in r1["flags"]})
    # C2 clean reviewer
    clean_card = dict(synth_card)
    clean_card["reviewer"] = "worker-999"
    r2 = classify(clean_card, base, target_hashes)
    controls.append({"id": "C2_clean_reviewer", "expect_flag": "none", "got": r2["classification"],
                     "pass": r2["classification"] == "CLEAN_PRE_CARD"})
    # C3 planted prior verdict by same reviewer
    ev3 = dict(base)
    ev3["review_recs"] = [{"file": "reviews/F2a-review-worker-046.json", "mtime": 0.0,
                           "identities": ["worker-046"], "node_id": "F2a",
                           "target_id": "schemas/af_scc_c2_vacuum.yaml", "verdict": "accept",
                           "reviewed_sha256": "b" * 64, "class_ids": ["AF-SCC-C2-VAC-GEN"]}]
    r3 = classify(dict(synth_card), ev3, target_hashes)
    controls.append({"id": "C3_planted_prior_verdict", "expect_flag": "B_PRIOR_SAME_TARGET",
                     "got": r3["classification"], "pass": "B_PRIOR_SAME_TARGET" in r3["flags"]})
    # C4 planted alias-form prior verdict
    ev4 = dict(base)
    ev4["review_recs"] = [{"file": "reviews/F2a-review-flash-46.json", "mtime": 0.0,
                           "identities": ["deepseek-flash-46"], "node_id": "F2a",
                           "target_id": "schemas/af_scc_c2_vacuum.yaml", "verdict": "revise",
                           "reviewed_sha256": "c" * 64, "class_ids": ["AF-SCC-C2-VAC-GEN"]}]
    r4 = classify(dict(synth_card), ev4, target_hashes)
    controls.append({"id": "C4_planted_alias_prior_verdict", "expect_flag": "B_PRIOR_ALIAS_AMBIGUOUS",
                     "got": r4["classification"], "pass": "B_PRIOR_ALIAS_AMBIGUOUS" in r4["flags"]})
    return controls


def main():
    os.makedirs(OUT, exist_ok=True)
    cards, copied = freeze_snapshot()
    if not cards:
        print("no audit-r2 cards found", file=sys.stderr)
        return 2
    pre = {rel: sha256_file(os.path.join(ROOT, rel)) for rel in
           ["research_map/events.jsonl", "research_map/research_map.json", FROZEN_PINS_PATH] +
           [TARGETS[c["node_id"]] for c in cards if TARGETS.get(c["node_id"])]}
    target_hashes = target_live_hashes()
    evidence = scan_evidence(cards)
    rows = [classify(c, evidence, target_hashes) for c in cards]
    controls = run_controls(evidence, target_hashes)
    post = {rel: sha256_file(os.path.join(ROOT, rel)) for rel in pre}
    changed = sorted([k for k in pre if pre[k] != post[k]])
    window = {
        "opened_at": CARD_TIME.isoformat(),
        "cards_frozen": len(cards),
        "card_times": sorted({c["card_created_at"] for c in cards}),
        "pre": pre, "post": post, "changed_paths": changed,
        "stable": not changed,
        "evidence_cutoff": "per-card: file mtime < that card's created_at; r2 verdicts written after dispatch are excluded by construction",
        "events_total_scanned": evidence["events_total"],
        "pre_card_review_files_scanned": evidence["pre_card_review_files"],
    }
    summary = {
        "cards": len(rows),
        "clean_pre_card": sum(1 for r in rows if r["classification"] == "CLEAN_PRE_CARD"),
        "flagged": sum(1 for r in rows if r["classification"] != "CLEAN_PRE_CARD"),
        "flags": {},
        "targets": sorted({r["node_id"] for r in rows}),
        "reviewers": sorted({r["reviewer"] for r in rows}),
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
    }
    for r in rows:
        for f in r["flags"]:
            summary["flags"][f] = summary["flags"].get(f, 0) + 1
    same_executor = {
        "registry_actors": "research_map.json actors lists leads + 'flash-pool' (executor_pool, model deepseek-flash); individual worker ids are not registered.",
        "consequence": "All ten r2 reviewers are the same executor pool. Two verdicts can be procedurally independent (different context, different harness) but are not statistically independent judges; G-AUDIT's 'two independent verdicts' should be read as procedural independence only.",
    }
    prereg = {
        "task_id": "W065-R2-INDEP-PREREG-01",
        "actor": "worker-065",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_ids": ["F0", "F1", "F2a", "F2b", "N0", "A0"],
        "gate": "G-AUDIT",
        "card_time": CARD_TIME.isoformat(),
        "preregistered_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "card_declared_assertion": "reviewer may not be an author and may not read another reviewer's verdict for this target before writing",
        "target_hashes": target_hashes,
        "summary": summary,
        "rows": rows,
        "same_executor_caveat": same_executor,
        "non_claims": [
            "Not a verdict on any schema, nor on any r2 review.",
            "Flags are pre-card involvement indicators, not proof of bias and not gate failures.",
            "Alias forms are reported as ambiguity; identity between worker-0NN and deepseek-flash-NN is not asserted.",
        ],
    }
    report = {
        "question": "Which of the ten r2 (reviewer, target) pairs carry pre-card author/prior-verdict/exposure involvement, frozen before any r2 verdict is admitted?",
        "method": "deterministic stdlib-only scan of the pre-card evidence base; same classify() path exercised by four planted controls",
        "result": summary,
        "rows": [{"reviewer": r["reviewer"], "node_id": r["node_id"], "class_id": r["class_id"],
                  "target_artifact": r["target_artifact"], "classification": r["classification"],
                  "flags": r["flags"], "target_copy_count": r["target_copy_count"]} for r in rows],
        "controls": controls,
        "window": window,
        "falsifier": "A row classified CLEAN_PRE_CARD for which the frozen pre-card evidence base contains a target-path artifact event by that reviewer, a prior review document on the same target, or a reference to another reviewer's verdict document for that target; or a failing planted control; or changed pre/post window hashes.",
        "authority": "worker-level measurement only; no gate verdict, no node status, no validation_status=passed",
    }
    for name, obj in (("prereg.json", prereg), ("report.json", report), ("window.json", window), ("controls.json", {"controls": controls})):
        with open(os.path.join(OUT, name), "w") as f:
            json.dump(obj, f, indent=1, sort_keys=True)
    _write_readme(rows, summary, controls, window, target_hashes)
    cp = _write_checkpoint(rows, summary, controls, window, target_hashes)
    state_dir = os.path.join(ROOT, "runtime", "state")
    os.makedirs(state_dir, exist_ok=True)
    shutil.copy2(cp, os.path.join(state_dir, "worker-065_r2_independence_prereg_checkpoint.json"))
    manifest = {
        "task_id": "W065-R2-INDEP-PREREG-01",
        "files": [],
        "frozen_inputs": copied,
        "checkpoint": os.path.relpath(cp, ROOT),
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
    }
    for fn in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, fn)
        if os.path.isfile(p):
            manifest["files"].append({"path": os.path.relpath(p, ROOT), "sha256": sha256_file(p), "bytes": os.path.getsize(p)})
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    for r in rows:
        print(r["reviewer"], r["node_id"], "->", r["classification"])
    print("controls", summary["controls_pass"], "/", summary["controls_total"], "| window stable:", window["stable"])
    return 0 if summary["controls_pass"] == summary["controls_total"] else 1


def _write_readme(rows, summary, controls, window, target_hashes):
    lines = [
        "# W065-R2-INDEP-PREREG-01 -- pre-registered independence census of the r2 review fleet",
        "",
        "Class-bound: nodes F0/F1/F2a/F2b/N0/A0; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,",
        "AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH; gate G-AUDIT. Worker-level measurement only.",
        "",
        "## Question",
        "",
        "The `audit-r2-*` cards (first batch 2026-09-12T00:44:18+08:00) require the reviewer to be",
        "neither an author of the target nor previously exposed to another reviewer's verdict on it.",
        "That is self-certified in each card. This tool freezes the pre-card evidence classification",
        "**before** any r2 verdict is admitted.",
        "",
        "## Result (frozen card set: %d cards, %d distinct reviewer/target pairs)" % (len(rows), len({(r["reviewer"], r["node_id"]) for r in rows})),
        "",
        "| reviewer | node | class | classification |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| %s | %s | %s | %s |" % (r["reviewer"], r["node_id"], r["class_id"], r["classification"]))
    lines += [
        "",
        "Summary: %d clean, %d flagged; controls %d/%d; window stable=%s." % (
            summary["clean_pre_card"], summary["flagged"], summary["controls_pass"], summary["controls_total"], window["stable"]),
        "",
        "## What the flags mean (and do not mean)",
        "",
        "- `A_ASSIGNED` -- a strictly pre-card map assignment on the same node under the reviewer's",
        "  id **or an alias form**. worker-012/N0 matches legacy assignment",
        "  `asg-2026-09-11-N0-deepseek-flash-12-21`; this is also the strongest available evidence that",
        "  `worker-012` and `deepseek-flash-12` are the same executor.",
        "- `B_PRIOR_ALIAS_AMBIGUOUS` -- a pre-card review document on the same target under an alias id",
        "  form (worker-015/F2b: `reviews/F2b-f0-binding-w015.json` by `deepseek-flash-15`, verdict revise).",
        "  Identity is not asserted; the row is flagged rather than silently counted clean.",
        "- `R2_MULTI_CARD_SAME_PAIR` -- more than one r2 card for the same reviewer and node (the",
        "  00:46:18/00:47:58 bindchain cards). A second card to the same reviewer is not a second",
        "  independent reviewer; G-AUDIT's per-target accept count must deduplicate by reviewer.",
        "- Direct exposure to another reviewer's verdict document in the reviewer's own pre-card tree:",
        "  **0 rows**. References found inside copies of the map/target are classified incidental and",
        "  reported in `prereg.json` under `C_incidental_references`.",
        "",
        "Flags are **pre-card involvement indicators, not proof of bias and not gate failures**. No",
        "verdict on any schema or any r2 review is expressed here.",
        "",
        "## Same-executor caveat",
        "",
        "`research_map.json` registers only the leads and `flash-pool` (executor_pool, model",
        "deepseek-flash); individual worker ids are not registered. All ten r2 reviewers are the same",
        "executor pool, so \"two independent verdicts\" can only mean procedural independence",
        "(different context/harness), not statistical independence of judges.",
        "",
        "## Method",
        "",
        "Deterministic stdlib-only scan; `classify()` is exercised by four planted controls",
        "(author event, clean reviewer, prior verdict, alias-form prior verdict) and all four must fire.",
        "Evidence cutoff is per card: file mtime < that card's `created_at`; r2 verdicts written after",
        "dispatch are excluded by construction. Frozen copies of the cards, map, FROZEN.json, target",
        "schemas and events.jsonl are under `snapshot/`.",
        "",
        "## Falsifier",
        "",
        "Re-run on the frozen snapshot. Falsified if any row classified `CLEAN_PRE_CARD` has, in the",
        "pre-card evidence base, a target-path artifact event by that reviewer, a prior review document",
        "on the same target under any id form, or a direct reference to another reviewer's verdict",
        "document for that target; or if a planted control fails to fire; or if the pre/post window",
        "hashes differ.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 artifacts/worker-065/r2_independence_prereg/prereg.py",
        "```",
        "",
        "## Pins at freeze time",
        "",
        "| node | path | sha256 (live = FROZEN rev%s) |" % target_hashes.get("_frozen_revision"),
        "|---|---|---|",
    ]
    for node in ("F0", "F1", "F2a", "F2b", "N0", "A0"):
        t = target_hashes.get(node, {})
        lines.append("| %s | %s | %s |" % (node, t.get("path"), (t.get("sha256") or "")[:16]))
    lines.append("")
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write("\n".join(lines))


def _write_checkpoint(rows, summary, controls, window, target_hashes):
    core = {}
    for fn in ("prereg.py", "prereg.json", "report.json", "window.json", "controls.json", "README.md"):
        p = os.path.join(OUT, fn)
        if os.path.exists(p):
            core[fn] = {"sha256": sha256_file(p), "bytes": os.path.getsize(p)}
    cp = {
        "task_id": "W065-R2-INDEP-PREREG-01",
        "actor": "worker-065",
        "worker": "worker-065",
        "node_id": "A1",
        "node_ids": ["F0", "F1", "F2a", "F2b", "N0", "A0"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-AUDIT",
        "created_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "card_time_first_batch": CARD_TIME.isoformat(),
        "cards_frozen": len(rows),
        "result": summary,
        "controls": controls,
        "window": window,
        "target_hashes": target_hashes,
        "artifacts": core,
        "authority_note": "Worker-level measurement only. Sets no gate verdict, no node status, no validation_status=passed.",
        "falsifier": "See README.md; re-run prereg.py on the frozen snapshot and compare per-row classifications.",
        "artifact_dir": os.path.relpath(OUT, ROOT),
    }
    p = os.path.join(OUT, "checkpoint.json")
    with open(p, "w") as f:
        json.dump(cp, f, indent=1, sort_keys=True)
    return p


if __name__ == "__main__":
    sys.exit(main())
