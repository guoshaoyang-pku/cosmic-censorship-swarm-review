#!/usr/bin/env python3
"""W074-R3-VERDICT-INDEPENDENCE-CENSUS-01.

Read-only deterministic census of the G-FORM r3 verdict round (card
astra-life05-verify-gform-r3) over the three class-bound targets:

    F1  AF-WCC-VAC-GEN   schemas/af_wcc_vacuum.yaml      d9cebb9404b2...
    F2a AF-SCC-C2-VAC-GEN schemas/af_scc_c2_vacuum.yaml  e9a27996dfd3...
    F2b AF-SCC-C0-VAC-GEN schemas/af_scc_c0_vacuum.yaml  b2ab6acb2bbe...

Question measured: does the verdict set at a pinned instant meet the card's own
binding criteria -- two independent non-author reviewers per class, at one live
hash per class, with findings that are not copies of one another?

Authority limits: measurement only. No gate verdict, no node status, no
validation_status promotion. Writes only inside this directory.

Usage:
    python3 r3_independence_census.py --run
    python3 r3_independence_census.py --selftest
"""

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

LIVE = {
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml",
           "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml",
            "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml",
            "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
}
SUPERSEDED = {
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda5976f0d12b2c05d7c8a1c69e05c5a49a93c26f7f2ac0d81a6f5b",
}
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
REVIEW_DIR = "reviews"
OUT_REPORT = os.path.join(HERE, "report.json")
OUT_RAW = os.path.join(HERE, "raw")
OUT_SELFTEST = os.path.join(HERE, "selftest.json")

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
AGENT_ID = re.compile(r"\b(?:worker|flash|deepseek-flash|astra)[- ]?[0-9a-z]+\b")
FIND_KEYS = ("finding", "detail", "axis", "one_line", "summary", "description", "note")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def norm_text(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip()


def tokens(s):
    return norm_text(s).split()


def shingles(toks, k=5):
    if len(toks) < k:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def seq_sim(a, b, cap=3000):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a[:cap], b[:cap]).ratio()


def read_json(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return json.load(fh)


def flatten_strings(obj, out, depth=0):
    """Collect all string leaves; bounded depth to stay deterministic."""
    if depth > 8:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            flatten_strings(v, out, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            flatten_strings(v, out, depth + 1)


def extract_findings(d):
    """Findings text plus list of discrete block strings."""
    blocks = []
    blob = []
    for key in ("findings", "hard_failures", "soft_findings", "checks",
                "acceptance_checks", "score_rationale", "one_line"):
        v = d.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            blocks.append(v)
            blob.append(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    if tokens(item):
                        blocks.append(item)
                    blob.append(item)
                elif isinstance(item, dict):
                    sub = []
                    flatten_strings(item, sub)
                    txt = " ".join(sub)
                    if tokens(txt):
                        blocks.append(txt)
                    blob.append(txt)
    return " ".join(blob), blocks


def normalize_verdict(v):
    if isinstance(v, dict):
        v = v.get("verdict") or v.get("value") or "unknown"
    if not isinstance(v, str):
        return "unknown"
    v = v.strip().lower()
    for pref in ("accept", "revise", "reject", "inconclusive", "kill"):
        if v.startswith(pref):
            return pref
    return v or "unknown"


def target_of(d, text):
    """Classify a review file to F1/F2a/F2b, or None."""
    for key in ("target_id", "node_id"):
        v = d.get(key)
        if isinstance(v, str):
            for t in LIVE:
                if re.search(r"\b" + t + r"\b", v):
                    return t
    tgt = d.get("target")
    if isinstance(tgt, dict):
        p = str(tgt.get("path", ""))
        for t, (_, path, _) in LIVE.items():
            if p == path:
                return t
    if isinstance(tgt, str):
        p = tgt
        for t, (_, path, _) in LIVE.items():
            if p == path:
                return t
    hits = set()
    for t, (_, _, h) in LIVE.items():
        if h in text:
            hits.add(t)
    for t, h in SUPERSEDED.items():
        if h in text:
            hits.add(t)
    if len(hits) == 1:
        return hits.pop()
    if len(hits) > 1:
        # multi-target file: prefer explicit class_id mapping
        cid = d.get("class_id") or ""
        if isinstance(cid, str):
            for t, (c, _, _) in LIVE.items():
                if c in cid:
                    return t
    return None


def author_sets():
    """Author/owner sets for the three live schemas (conservative)."""
    out = {}
    for t, (cid, path, _) in LIVE.items():
        authors = set()
        mentions = set()
        try:
            txt = open(os.path.join(ROOT, path), "r", encoding="utf-8", errors="replace").read()
        except OSError:
            out[t] = (authors, mentions)
            continue
        for m in re.finditer(r"(?m)^\s*(?:authored_by|owner)\s*:\s*[\"']?([^\"'\n#]+)", txt):
            authors.add(m.group(1).strip())
        i = txt.find("revision_history")
        if i >= 0:
            for m in AGENT_ID.finditer(txt[i:i + 12000]):
                mentions.add(m.group(0).replace(" ", "-"))
        out[t] = (authors, mentions)
    return out


def collect_review_files():
    rdir = os.path.join(ROOT, REVIEW_DIR)
    names = []
    for name in sorted(os.listdir(rdir)):
        if name.endswith(".json") or name.endswith(".jsonl"):
            p = os.path.join(rdir, name)
            if os.path.isfile(p):
                names.append(p)
    return names


def frame_measure(paths):
    frame = {}
    for p in paths:
        st = os.stat(p)
        frame[os.path.relpath(p, ROOT)] = {
            "sha256": sha256_file(p),
            "bytes": st.st_size,
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
        }
    return frame


def parse_reviews(live_pins, superseded):
    aset = author_sets()
    per_class = {t: [] for t in LIVE}
    considered = []
    for path in collect_review_files():
        try:
            text = open(path, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        try:
            d = json.loads(text)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        t = target_of(d, text)
        if t is None:
            continue
        considered.append(os.path.relpath(path, ROOT))
        reviewer = d.get("reviewer") or d.get("actor") or "unknown"
        if isinstance(reviewer, dict):
            reviewer = reviewer.get("id", "unknown")
        hashes = set(HEX64.findall(text))
        live_h = live_pins[t]
        at_live = live_h in hashes
        stale_only = (not at_live) and (superseded[t] in hashes)
        findings_text, blocks = extract_findings(d)
        decl = d.get("independence") if isinstance(d.get("independence"), dict) else {}
        declared_author = d.get("reviewer_is_author")
        if declared_author is None:
            declared_author = decl.get("is_artifact_author")
        in_author_set = reviewer in aset.get(t, (set(), set()))[0]
        per_class[t].append({
            "file": os.path.relpath(path, ROOT),
            "file_sha256": sha256_file(path),
            "reviewer": reviewer,
            "verdict": normalize_verdict(d.get("verdict", d.get("event_type"))),
            "score": d.get("score"),
            "created_at": d.get("created_at") or d.get("reviewed_at"),
            "at_live_pin": at_live,
            "stale_only": stale_only,
            "declared_author": declared_author,
            "reviewer_in_author_set": in_author_set,
            "contributor_mention": reviewer in aset.get(t, (set(), set()))[1],
            "findings_text": findings_text,
            "blocks": blocks,
            "assignment_ids": d.get("assignment_event_ids") or d.get("assignment_ids")
                              or d.get("assignment_event_id") or d.get("assignment_ids"),
        })
    return per_class, considered, aset


def _parse_iso(x):
    if not isinstance(x, str) or not x:
        return None
    try:
        return datetime.datetime.fromisoformat(x.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def census_class(entries, class_id, live_pin, superseded_pin, target_mtime=None,
                 link_jac=0.30, link_blocks=3):
    live = [e for e in entries if e["at_live_pin"]]
    stale = [e for e in entries if e["stale_only"]]
    accepts = [e for e in live if e["verdict"] == "accept"]
    non_author_accepts = [e for e in accepts if not e["reviewer_in_author_set"]]
    distinct_live = sorted({e["reviewer"] for e in live})
    distinct_non_author_live = sorted({e["reviewer"] for e in live
                                       if not e["reviewer_in_author_set"]})

    # pairwise similarity over distinct reviewers at the live pin (union of their verdicts)
    by_reviewer = {}
    for e in live:
        r = by_reviewer.setdefault(e["reviewer"], {"full": [], "blocks": [], "verdicts": []})
        r["full"].append(e["findings_text"])
        r["blocks"].extend(e["blocks"])
        r["verdicts"].append(e["verdict"])
    reviewers = sorted(by_reviewer)
    pairs = []
    sims = {}
    for i, a in enumerate(reviewers):
        for b in reviewers[i + 1:]:
            ta = tokens(" ".join(by_reviewer[a]["full"]))
            tb = tokens(" ".join(by_reviewer[b]["full"]))
            jac = jaccard(shingles(ta), shingles(tb))
            seq = seq_sim(" ".join(by_reviewer[a]["full"]), " ".join(by_reviewer[b]["full"]))
            ba = {norm_text(x) for x in by_reviewer[a]["blocks"] if len(tokens(x)) >= 12}
            bb = {norm_text(x) for x in by_reviewer[b]["blocks"] if len(tokens(x)) >= 12}
            shared = sorted(ba & bb)
            linked = (jac >= link_jac) or (len(shared) >= link_blocks)
            pairs.append({"a": a, "b": b, "jaccard5": round(jac, 4), "seq": round(seq, 4),
                          "shared_blocks": len(shared), "linked": linked})
            sims[(a, b)] = linked

    # Kish ESS over distinct live reviewers (all verdicts) and over non-author accepts
    def ess(ids, link_fn):
        parent = {x: x for x in ids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if link_fn(a, b):
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[ra] = rb
        from collections import Counter
        sizes = Counter(find(x) for x in ids)
        n = len(ids)
        return round((n * n) / float(sum(s * s for s in sizes.values())), 3) if n else 0.0

    def linked_pair(a, b):
        return sims.get((a, b), sims.get((b, a), False))

    max_j = max([p["jaccard5"] for p in pairs], default=0.0)
    max_s = max([p["seq"] for p in pairs], default=0.0)
    temporal_flags = []
    if target_mtime is not None:
        for e in live:
            t = _parse_iso(e["created_at"])
            if t is not None and t < target_mtime:
                temporal_flags.append({"file": e["file"], "reviewer": e["reviewer"],
                                       "created_at": e["created_at"],
                                       "target_mtime": target_mtime.isoformat()})
    # assignment-id collisions across distinct reviewers at the live pin
    by_assign = {}
    for e in live:
        aids = e.get("assignment_ids")
        if isinstance(aids, str):
            aids = [aids]
        for a in (aids or []):
            by_assign.setdefault(str(a), set()).add(e["reviewer"])
    assign_collisions = {a: sorted(rs) for a, rs in by_assign.items() if len(rs) > 1}

    ess_all = ess(distinct_live, linked_pair)
    accept_ids = sorted({e["reviewer"] for e in non_author_accepts})
    ess_accepts = ess(accept_ids, linked_pair)
    hash_agreement = all(e["at_live_pin"] for e in live) if live else False  # at_live == live pin cited in file
    if accept_ids and ess_accepts >= 2:
        coverage = "COVERED"
    elif accept_ids and ess_accepts >= 1:
        coverage = "PARTIAL"
    elif len(distinct_non_author_live) >= 2:
        coverage = "REVIEWED_NO_ACCEPT"
    elif distinct_non_author_live:
        coverage = "PARTIAL_NO_ACCEPT"
    else:
        coverage = "GAP"
    return {
        "class_id": class_id,
        "live_pin": live_pin,
        "superseded_pin": superseded_pin,
        "entries_total": len(entries),
        "entries_at_live_pin": len(live),
        "entries_stale_only": len(stale),
        "verdict_histogram_at_live": {v: sum(1 for e in live if e["verdict"] == v)
                                      for v in sorted({e["verdict"] for e in live})},
        "stale_files": [e["file"] for e in stale],
        "distinct_reviewers_at_live": distinct_live,
        "distinct_non_author_reviewers_at_live": distinct_non_author_live,
        "reviewers_in_author_set": sorted({e["reviewer"] for e in live if e["reviewer_in_author_set"]}),
        "contributor_mentions": sorted({e["reviewer"] for e in entries if e["contributor_mention"]}),
        "accepts_at_live": [{"reviewer": e["reviewer"], "file": e["file"],
                             "non_author": not e["reviewer_in_author_set"]} for e in accepts],
        "non_author_accept_reviewers": accept_ids,
        "pairwise": pairs,
        "max_pairwise_jaccard5": max_j,
        "max_pairwise_seq": max_s,
        "temporal_flags_live_hash_cited_before_target_mtime": temporal_flags,
        "assignment_id_collisions": assign_collisions,
        "kish_ess_all_live_reviewers": ess_all,
        "kish_ess_non_author_accepts": ess_accepts,
        "hash_agreement_all_true": bool(hash_agreement),
        "coverage": coverage,
        "link_rule": "linked if jaccard5(findings) >= %.2f OR shared identical finding blocks >= %d" % (link_jac, link_blocks),
    }


def measure(live_pins=None, frozen_pin=None, tag=""):
    live_pins = live_pins or {t: v[2] for t, v in LIVE.items()}
    frozen_pin = frozen_pin or FROZEN_PIN
    per_class, considered, authors = parse_reviews(live_pins, SUPERSEDED)
    review_paths = [os.path.join(ROOT, p) for p in considered]
    frame0 = frame_measure(review_paths)
    classes = {}
    for t, (cid, path, _) in LIVE.items():
        mt = datetime.datetime.fromtimestamp(os.stat(os.path.join(ROOT, path)).st_mtime).astimezone()
        classes[t] = census_class(per_class[t], cid, live_pins[t], SUPERSEDED[t], target_mtime=mt)
    # live-target frame
    targets = {}
    for t, (cid, path, _) in LIVE.items():
        p = os.path.join(ROOT, path)
        targets[path] = {"sha256": sha256_file(p), "matches_live_pin": sha256_file(p) == live_pins[t]}
    frozen = {}
    fp = os.path.join(ROOT, FROZEN_PATH)
    if os.path.exists(fp):
        fh = sha256_file(fp)
        frozen = {"path": FROZEN_PATH, "sha256": fh, "matches_pin": fh == frozen_pin,
                  "revision": read_json(fp).get("revision")}
    frame1 = frame_measure(review_paths)
    moved = sorted(set(frame0) | set(frame1))
    moved = [p for p in moved if frame0.get(p, {}).get("sha256") != frame1.get(p, {}).get("sha256")]
    report = {
        "task_id": "W074-R3-VERDICT-INDEPENDENCE-CENSUS-01",
        "worker": "worker-074",
        "created_at": datetime.datetime.now().astimezone().isoformat(),
        "tag": tag,
        "class_binding": {t: LIVE[t][0] for t in LIVE},
        "gate": "G-FORM",
        "nodes": ["F1", "F2a", "F2b"],
        "live_pins": live_pins,
        "frozen": frozen,
        "targets": targets,
        "author_sets": {t: sorted(authors.get(t, (set(), set()))[0]) for t in LIVE},
        "review_files_considered": considered,
        "classes": classes,
        "frame_t0": frame0,
        "frame_t1": frame1,
        "moved_during_run": moved,
        "limits": [
            "measurement only: no gate verdict, no node status, no validation_status promotion",
            "verdict text similarity is a proxy for independence, not a proof of copying; shared "
            "schemas/templates lower similarity legitimately and copied prose inside different "
            "templates raises it",
            "author sets are conservative (authored_by + owner); revision-note mentions are reported "
            "separately and not used to rule a reviewer an author",
            "coverage counts only verdict files present at the measured instant",
            "a verdict counts at the live pin only if the measured live sha256 appears in the file; "
            "temporal flags list live-pin files whose declared created_at precedes the target mtime",
        ],
        "falsifier": ("FALSIFIED IF: (a) any class shows >=2 non-author accepts at the live pin "
                      "whose pairwise findings jaccard5 < %.2f, no shared identical finding blocks "
                      "(>=%d), and no review-level template reuse, so the measured ESS is wrong; or "
                      "(b) a reviewer counted non-author is shown in the target schema's authored_by/"
                      "owner metadata; or (c) a file counted at the live pin is shown not to cite the "
                      "measured live sha256; or (d) re-running the census on the frozen frame "
                      "reproduces a different verdict set." % (0.30, 3)),
    }
    return report


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.write("\n")


def cmd_run(_args):
    os.makedirs(OUT_RAW, exist_ok=True)
    t0 = datetime.datetime.now().astimezone().isoformat()
    report = measure(tag="live")
    t1 = datetime.datetime.now().astimezone().isoformat()
    report["measurement_instant_t0"] = t0
    report["measurement_instant_t1"] = t1
    write_json(OUT_REPORT, report)
    write_json(os.path.join(OUT_RAW, "frame_t0.json"), report["frame_t0"])
    write_json(os.path.join(OUT_RAW, "frame_t1.json"), report["frame_t1"])
    print(json.dumps({t: report["classes"][t]["coverage"] for t in LIVE}, indent=1))
    for t in LIVE:
        c = report["classes"][t]
        print(t, "at_live", c["entries_at_live_pin"], "accepts", len(c["accepts_at_live"]),
              "non_author_accepts", c["non_author_accept_reviewers"],
              "ESS_accepts", c["kish_ess_non_author_accepts"], "->", c["coverage"])
    print("moved_during_run:", report["moved_during_run"])
    return 0


def selftest():
    """Negative controls on synthetic review sets; same functions as the live run."""
    import tempfile
    checks = []
    tmp = tempfile.mkdtemp(prefix="w074selftest_", dir=HERE)

    def mk(name, reviewer, target_path, pin, findings, verdict="accept", author_note=False):
        d = {"reviewer": reviewer, "target": {"path": target_path, "pin_sha256": pin},
             "verdict": verdict, "findings": findings, "reviewed_sha256": pin,
             "class_id": {"schemas/af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN"}.get(target_path, "")}
        if author_note:
            d["independence"] = {"is_artifact_author": True}
        p = os.path.join(tmp, name)
        write_json(p, d)
        return p

    # control 1: identical findings from two reviewers -> link, ESS collapses to 1
    f = ["The quantifier prefix is exact and the class id is single. " * 3]
    a = mk("c1a.json", "worker-900", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], f)
    b = mk("c1b.json", "worker-901", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], f)
    ea = parse_synthetic([a, b], "F1")
    c = census_class(ea, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "identical_findings_two_reviewers",
                   "expected": "linked pair and ESS == 1.0",
                   "observed": {"ess": c["kish_ess_all_live_reviewers"],
                                "linked": [p["linked"] for p in c["pairwise"]]},
                   "pass": c["kish_ess_all_live_reviewers"] == 1.0 and any(p["linked"] for p in c["pairwise"])})

    # control 2: disjoint findings -> no link, ESS == 2
    f2 = ["Topology and data class are typed; the visibility predicate is equivalent. " * 3]
    cpath = mk("c2a.json", "worker-902", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], f2)
    dpath = mk("c2b.json", "worker-903", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2],
               ["The topology slot names a manifold category; the genericity axis is comeager. " * 3])
    ec = parse_synthetic([cpath, dpath], "F1")
    c2 = census_class(ec, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "disjoint_findings_two_reviewers",
                   "expected": "no linked pair and ESS == 2.0",
                   "observed": {"ess": c2["kish_ess_all_live_reviewers"],
                                "linked": [p["linked"] for p in c2["pairwise"]]},
                   "pass": c2["kish_ess_all_live_reviewers"] == 2.0 and not any(p["linked"] for p in c2["pairwise"])})

    # control 3: stale pin only -> counted stale, not at live pin
    epath = mk("c3.json", "worker-904", "schemas/af_wcc_vacuum.yaml", SUPERSEDED["F1"], f2)
    e3 = parse_synthetic([epath], "F1")
    c3 = census_class(e3, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "stale_pin_verdict",
                   "expected": "entries_at_live_pin == 0 and entries_stale_only == 1",
                   "observed": {"at_live": c3["entries_at_live_pin"], "stale": c3["entries_stale_only"]},
                   "pass": c3["entries_at_live_pin"] == 0 and c3["entries_stale_only"] == 1})

    # control 4: author reviewer -> not counted as non-author accept
    fpath = mk("c4.json", "astra-lead-formulation", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], f2)
    e4 = parse_synthetic([fpath], "F1")
    c4 = census_class(e4, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "author_reviewer_excluded",
                   "expected": "reviewer_in_author_set true and zero non-author accepts",
                   "observed": {"in_author_set": c4["reviewers_in_author_set"],
                                "non_author_accepts": c4["non_author_accept_reviewers"]},
                   "pass": "astra-lead-formulation" in c4["reviewers_in_author_set"]
                           and c4["non_author_accept_reviewers"] == []})

    # control 5: near-duplicate with light edits -> link via jaccard or shared blocks
    base = ["Clause (a) binds the topology; clause (b) binds the data class; clause (c) is the falsifier. " * 4]
    near = [base[0].replace("clause (c)", "clause c")]
    g = mk("c5a.json", "worker-905", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], base)
    h = mk("c5b.json", "worker-906", "schemas/af_wcc_vacuum.yaml", LIVE["F1"][2], near)
    e5 = parse_synthetic([g, h], "F1")
    c5 = census_class(e5, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "near_duplicate_light_edit",
                   "expected": "pair linked",
                   "observed": c5["pairwise"],
                   "pass": any(p["linked"] for p in c5["pairwise"])})

    # control 6: tampered live hash -> not at live pin
    ipath = mk("c6.json", "worker-907", "schemas/af_wcc_vacuum.yaml",
               "0" * 64, ["A genuinely independent looking verdict. " * 4])
    e6 = parse_synthetic([ipath], "F1")
    c6 = census_class(e6, LIVE["F1"][0], LIVE["F1"][2], SUPERSEDED["F1"])
    checks.append({"control": "tampered_hash_not_at_live_pin",
                   "expected": "entries_at_live_pin == 0 and stale_only == 0",
                   "observed": {"at_live": c6["entries_at_live_pin"], "stale": c6["entries_stale_only"]},
                   "pass": c6["entries_at_live_pin"] == 0 and c6["entries_stale_only"] == 0})

    out = {"task_id": "W074-R3-VERDICT-INDEPENDENCE-CENSUS-01", "controls": checks,
           "pass": sum(1 for c in checks if c["pass"]), "total": len(checks)}
    write_json(OUT_SELFTEST, out)
    print(json.dumps(out, indent=1))
    return 0 if out["pass"] == out["total"] else 1


def parse_synthetic(paths, t):
    """Parse explicit file lists with the live parser (test fixture bypass)."""
    aset = author_sets()
    authors, mentions = aset[t]
    entries = []
    for path in paths:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        d = json.loads(text)
        reviewer = d.get("reviewer") or d.get("actor") or "unknown"
        hashes = set(HEX64.findall(text))
        at_live = LIVE[t][2] in hashes
        stale_only = (not at_live) and (SUPERSEDED[t] in hashes)
        findings_text, blocks = extract_findings(d)
        decl = d.get("independence") if isinstance(d.get("independence"), dict) else {}
        da = d.get("reviewer_is_author")
        if da is None:
            da = decl.get("is_artifact_author")
        entries.append({
            "file": os.path.relpath(path, ROOT), "file_sha256": sha256_file(path),
            "reviewer": reviewer, "verdict": normalize_verdict(d.get("verdict")),
            "score": d.get("score"), "created_at": d.get("created_at"),
            "at_live_pin": at_live, "stale_only": stale_only, "declared_author": da,
            "reviewer_in_author_set": reviewer in authors,
            "contributor_mention": reviewer in mentions,
            "findings_text": findings_text, "blocks": blocks, "assignment_ids": None,
        })
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
